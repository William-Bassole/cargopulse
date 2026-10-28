"""Illustrative output used when API keys are missing. Not real news."""

from __future__ import annotations

from routes import KNOWN_CHOKEPOINTS, PORTS

SAMPLE_VOYAGE = {
    "commodity": "Crude oil",
    "origin": "Ras Tanura (Saudi Arabia)",
    "destination": "Rotterdam (Netherlands)",
}

_SEGMENTS = [
    ("Ras Tanura (Saudi Arabia)", "load", "low",
     "Sample: loading programme reported as running normally.",
     "No expected effect on the load window.", ["S1"]),
    ("Strait of Hormuz", "chokepoint", "medium",
     "Sample: elevated naval activity reported; transits continue.",
     "War-risk insurance premium may rise; no transit delay reported.", ["S2"]),
    ("Bab el-Mandeb / Red Sea", "chokepoint", "high",
     "Sample: several operators still avoid the Red Sea and reroute via the Cape.",
     "Rerouting adds roughly 10-14 days and extra bunker cost.", ["S3", "S4"]),
    ("Suez Canal", "chokepoint", "medium",
     "Sample: transit volumes remain below normal levels.",
     "Only relevant if the vessel does not reroute.", ["S4"]),
    ("Strait of Gibraltar", "chokepoint", "insufficient",
     "No relevant recent reporting found.", "", []),
    ("English Channel", "chokepoint", "low",
     "Sample: seasonal storms forecast, normal traffic.", "Minor weather delay possible.", ["S5"]),
    ("Rotterdam (Netherlands)", "discharge", "medium",
     "Sample: berth congestion at the crude terminals.",
     "1-2 days waiting time, demurrage exposure on arrival.", ["S6"]),
]


def sample_result() -> dict:
    segments, sources = [], {}
    for i, (name, kind, risk, finding, impact, ids) in enumerate(_SEGMENTS):
        lat, lon = (PORTS[name][1:] if name in PORTS else KNOWN_CHOKEPOINTS[name][:2])
        segments.append({"name": name, "kind": kind, "lat": lat, "lon": lon, "risk": risk,
                         "finding": finding, "voyage_impact": impact, "source_ids": ids})
        for sid in ids:
            sources.setdefault(sid, {
                "id": sid, "segment": name,
                "title": f"Illustrative source {sid} ({name})",
                "url": "https://example.com/",
                "content": "Placeholder text. Add API keys to see real, recent sources.",
                "published_date": "",
            })
    brief = {
        "overall_risk": "high",
        "headline": "Sample: Red Sea routing is the main risk to this voyage; "
                    "decide routing before laycan.",
        "segments": segments,
        "pre_laycan_checks": [
            "Confirm with the owner whether the vessel transits the Red Sea or goes via the Cape.",
            "Check current war-risk premium quotes for Hormuz and the Red Sea.",
            "Ask the Rotterdam agent for the latest berth line-up.",
        ],
        "uncertainties": ["Illustrative data only: no live sources were consulted."],
    }
    return {"brief": brief, "sources": sources, "route_method": "table",
            "model": "sample (no API call)"}
