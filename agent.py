"""CargoPulse agent: plan the voyage, search each segment with Tavily, brief with Nemotron.

Pipeline
  1. plan_route      -> ordered segments (load port, chokepoints, discharge port)
                        from a curated table, or Nemotron picks chokepoints from a
                        fixed list when the voyage is not covered.
  2. search_segments -> one Tavily news search per segment, run in parallel.
  3. write_brief     -> one Nemotron call on Nebius Token Factory that rates each
                        segment strictly from the numbered sources it was given.
"""

from __future__ import annotations

import json
import os
import re
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import date

from routes import KNOWN_CHOKEPOINTS, PORTS, lookup_chokepoints

DEFAULT_BASE_URL = "https://api.tokenfactory.nebius.com/v1/"
DEFAULT_MODEL = "nvidia/nemotron-3-super-120b-a12b"
RISK_LEVELS = ("low", "medium", "high", "insufficient")


def get_secret(name: str, default: str | None = None) -> str | None:
    """Read a setting from env vars first, then Streamlit secrets."""
    value = os.environ.get(name)
    if value:
        return value
    try:
        import streamlit as st

        return st.secrets.get(name, default)  # type: ignore[no-any-return]
    except Exception:
        return default


@dataclass
class Segment:
    name: str
    kind: str  # "load", "chokepoint", "discharge"
    lat: float
    lon: float
    query: str
    sources: list[dict] = field(default_factory=list)


@dataclass
class Voyage:
    commodity: str
    origin: str
    destination: str
    laycan_start: date
    laycan_end: date


# --------------------------------------------------------------------------- LLM


def _client():
    from openai import OpenAI

    return OpenAI(
        base_url=get_secret("NEBIUS_BASE_URL", DEFAULT_BASE_URL),
        api_key=get_secret("NEBIUS_API_KEY"),
        timeout=90,
    )


def _model() -> str:
    return get_secret("NEBIUS_MODEL", DEFAULT_MODEL) or DEFAULT_MODEL


def _chat_json(system: str, user: str, max_tokens: int = 2500) -> dict:
    """Call Nemotron and parse a JSON object out of the answer."""
    response = _client().chat.completions.create(
        model=_model(),
        temperature=0.2,
        max_tokens=max_tokens,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    )
    text = response.choices[0].message.content or ""
    return extract_json(text)


def extract_json(text: str) -> dict:
    """Strip reasoning blocks / code fences and return the first JSON object."""
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)
    text = re.sub(r"```(?:json)?", "", text)
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError("The model did not return JSON.")
    return json.loads(text[start : end + 1])


# ---------------------------------------------------------------------- step 1


def plan_route(voyage: Voyage) -> tuple[list[Segment], str]:
    """Return ordered segments and how the route was planned ("table" or "nemotron")."""
    chokepoints = lookup_chokepoints(voyage.origin, voyage.destination)
    method = "table"
    if chokepoints is None:
        method = "nemotron"
        chokepoints = _plan_with_nemotron(voyage)

    segments = [_port_segment(voyage.origin, "load", voyage.commodity)]
    for cp in chokepoints:
        lat, lon, hint = KNOWN_CHOKEPOINTS[cp]
        segments.append(Segment(cp, "chokepoint", lat, lon, f"{hint} disruption"))
    segments.append(_port_segment(voyage.destination, "discharge", voyage.commodity))
    return segments, method


def _port_segment(port: str, kind: str, commodity: str) -> Segment:
    _, lat, lon = PORTS[port]
    city = port.split(" (")[0]
    return Segment(port, kind, lat, lon,
                   f"{city} port congestion strike weather {commodity} shipping")


def _plan_with_nemotron(voyage: Voyage) -> list[str]:
    allowed = list(KNOWN_CHOKEPOINTS)
    data = _chat_json(
        system=(
            "You are a maritime chartering analyst. Choose the chokepoints a "
            "laden vessel would normally transit on the most common commercial "
            "route. Answer with JSON only: {\"chokepoints\": [...]} in sailing "
            "order, using ONLY names from the allowed list. Use [] if none."
        ),
        user=(
            f"Load port: {voyage.origin}\nDischarge port: {voyage.destination}\n"
            f"Commodity: {voyage.commodity}\nAllowed chokepoints: {allowed}"
        ),
        max_tokens=600,
    )
    return [c for c in data.get("chokepoints", []) if c in KNOWN_CHOKEPOINTS]


# ---------------------------------------------------------------------- step 2


def search_segments(segments: list[Segment], days: int = 14, per_segment: int = 3) -> None:
    """Fill each segment's sources with recent Tavily news results (in parallel)."""
    from tavily import TavilyClient

    client = TavilyClient(api_key=get_secret("TAVILY_API_KEY"))

    def run(seg: Segment) -> list[dict]:
        try:
            res = client.search(
                query=seg.query,
                topic="news",
                days=days,
                max_results=per_segment,
                search_depth="basic",
            )
        except Exception as exc:  # one failed segment must not break the brief
            return [{"error": str(exc)}]
        return [
            {
                "title": r.get("title", "Untitled"),
                "url": r.get("url", ""),
                "content": (r.get("content") or "")[:600],
                "published_date": r.get("published_date", ""),
            }
            for r in res.get("results", [])
        ]

    with ThreadPoolExecutor(max_workers=6) as pool:
        for seg, sources in zip(segments, pool.map(run, segments)):
            seg.sources = [s for s in sources if "error" not in s]


def number_sources(segments: list[Segment]) -> dict[str, dict]:
    """Give every source a stable ID (S1, S2...) and remember its segment."""
    catalog: dict[str, dict] = {}
    n = 1
    for seg in segments:
        for src in seg.sources:
            src["id"] = f"S{n}"
            src["segment"] = seg.name
            catalog[src["id"]] = src
            n += 1
    return catalog


# ---------------------------------------------------------------------- step 3

BRIEF_SYSTEM = """You are CargoPulse, an assistant for operations analysts at a \
physical commodity trading company. You assess logistics disruption risk for one \
voyage, segment by segment, using ONLY the numbered sources provided.

Rules:
- Every finding must cite source IDs from the list (e.g. ["S3"]). Never invent sources.
- If a segment has no relevant source, set risk to "insufficient" and say so.
- Risk scale: low, medium, high, insufficient. Rate the impact on THIS voyage and laycan.
- Think like operations: transit delays, rerouting, port congestion, berth waits,
  demurrage exposure, insurance (war risk) premiums, sanctions or inspection holds.
- No price forecasts, no trading or investment recommendations.
- Answer with a single JSON object and nothing else."""

BRIEF_SCHEMA = """{
  "overall_risk": "low|medium|high|insufficient",
  "headline": "one sentence for the trader",
  "segments": [
    {"name": "<segment name exactly as given>",
     "risk": "low|medium|high|insufficient",
     "finding": "what the sources say, 1-2 sentences",
     "voyage_impact": "possible effect on transit time, demurrage or cost",
     "source_ids": ["S1"]}
  ],
  "pre_laycan_checks": ["concrete thing to verify before loading", "..."],
  "uncertainties": ["what the sources do not establish", "..."]
}"""


def write_brief(voyage: Voyage, segments: list[Segment], catalog: dict[str, dict]) -> dict:
    lines = []
    for seg in segments:
        lines.append(f"\n## Segment: {seg.name} ({seg.kind})")
        if not seg.sources:
            lines.append("(no sources found)")
        for src in seg.sources:
            lines.append(
                f"[{src['id']}] {src['title']} ({src.get('published_date') or 'date n/a'})\n"
                f"{src['content']}"
            )
    user = (
        f"Voyage: {voyage.commodity} from {voyage.origin} to {voyage.destination}\n"
        f"Laycan: {voyage.laycan_start:%d %b %Y} - {voyage.laycan_end:%d %b %Y}\n"
        f"Today: {date.today():%d %b %Y}\n"
        f"Segments in sailing order: {[s.name for s in segments]}\n"
        f"\nSources:{''.join(chr(10) + l for l in lines)}\n\n"
        f"Return JSON matching this schema:\n{BRIEF_SCHEMA}"
    )
    brief = _chat_json(BRIEF_SYSTEM, user)
    return validate_brief(brief, segments, catalog)


def validate_brief(brief: dict, segments: list[Segment], catalog: dict[str, dict]) -> dict:
    """Drop invented source IDs and downgrade unsupported claims to 'insufficient'."""
    by_name = {s.get("name"): s for s in brief.get("segments", []) if isinstance(s, dict)}
    clean = []
    for seg in segments:
        item = by_name.get(seg.name, {})
        ids = [i for i in item.get("source_ids", []) if i in catalog]
        risk = str(item.get("risk", "insufficient")).lower()
        if risk not in RISK_LEVELS or (not ids and risk != "insufficient"):
            risk = "insufficient"
        clean.append(
            {
                "name": seg.name,
                "kind": seg.kind,
                "lat": seg.lat,
                "lon": seg.lon,
                "risk": risk,
                "finding": item.get("finding") or "No relevant recent reporting found.",
                "voyage_impact": item.get("voyage_impact") or "",
                "source_ids": ids,
            }
        )
    overall = str(brief.get("overall_risk", "insufficient")).lower()
    brief["overall_risk"] = overall if overall in RISK_LEVELS else "insufficient"
    brief["segments"] = clean
    brief.setdefault("headline", "")
    brief.setdefault("pre_laycan_checks", [])
    brief.setdefault("uncertainties", [])
    return brief


def run_pipeline(voyage: Voyage, progress=None) -> dict:
    """Full live run. `progress(step_label)` is an optional UI callback."""
    say = progress or (lambda _msg: None)
    say("Planning the route")
    segments, method = plan_route(voyage)
    say(f"Searching recent news on {len(segments)} segments with Tavily")
    search_segments(segments)
    catalog = number_sources(segments)
    say(f"Nemotron is reading {len(catalog)} sources")
    brief = write_brief(voyage, segments, catalog)
    return {"brief": brief, "sources": catalog, "route_method": method, "model": _model()}
