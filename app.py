"""CargoPulse - voyage disruption brief for commodity trading operations."""

from __future__ import annotations

import html
import math
from datetime import date, timedelta

import pydeck as pdk
import streamlit as st

from agent import Voyage, get_secret, run_pipeline
from routes import COMMODITIES, PORTS
from sample_data import SAMPLE_VOYAGE, sample_result

st.set_page_config(page_title="CargoPulse", page_icon="🚢", layout="wide")

RISK_COLORS = {
    "low": ("#1f9d55", [31, 157, 85]),
    "medium": ("#d9822b", [217, 130, 43]),
    "high": ("#d64545", [214, 69, 69]),
    "insufficient": ("#8a94a6", [138, 148, 166]),
}

st.markdown(
    """
    <style>
      .block-container {padding-top: 2rem; max-width: 1200px;}
      .cp-badge {display:inline-block; padding:2px 10px; border-radius:999px;
                 color:white; font-size:0.78rem; font-weight:600; text-transform:uppercase;
                 letter-spacing:0.03em;}
      .cp-card {border:1px solid rgba(128,128,128,0.25); border-radius:10px;
                padding:14px 16px; margin-bottom:10px;}
      .cp-kind {opacity:0.6; font-size:0.8rem; margin-left:6px;}
      .cp-src {font-size:0.85rem; opacity:0.85;}
      .cp-headline {font-size:1.15rem; font-weight:600; margin:0.3rem 0 0.8rem;}
    </style>
    """,
    unsafe_allow_html=True,
)


def badge(risk: str) -> str:
    color = RISK_COLORS.get(risk, RISK_COLORS["insufficient"])[0]
    return f'<span class="cp-badge" style="background:{color}">{html.escape(risk)}</span>'


keys_ready = bool(get_secret("NEBIUS_API_KEY") and get_secret("TAVILY_API_KEY"))

# ------------------------------------------------------------------- header
st.title("🚢 CargoPulse")
st.caption(
    "Voyage disruption brief for commodity trading operations. Enter a cargo, "
    "CargoPulse maps the chokepoints it will cross, searches recent news for each "
    "one and has NVIDIA Nemotron rate the risk to your laycan, with sources."
)

# ------------------------------------------------------------------- inputs
port_names = list(PORTS)
with st.form("voyage_form"):
    c1, c2, c3 = st.columns([1, 1.3, 1.3])
    commodity = c1.selectbox("Commodity", COMMODITIES, index=COMMODITIES.index(SAMPLE_VOYAGE["commodity"]))
    origin = c2.selectbox("Load port", port_names, index=port_names.index(SAMPLE_VOYAGE["origin"]))
    destination = c3.selectbox("Discharge port", port_names,
                               index=port_names.index(SAMPLE_VOYAGE["destination"]))
    c4, c5, c6 = st.columns([1, 1, 1.3])
    laycan_start = c4.date_input("Laycan start", date.today() + timedelta(days=10))
    laycan_end = c5.date_input("Laycan end", date.today() + timedelta(days=12))
    use_sample = c6.toggle("Sample mode (no API calls)", value=not keys_ready,
                           disabled=not keys_ready,
                           help="Shows illustrative data. Live mode needs NEBIUS_API_KEY and TAVILY_API_KEY.")
    submitted = st.form_submit_button("Generate voyage brief", type="primary", use_container_width=True)

if submitted:
    if origin == destination:
        st.error("Load and discharge ports must be different.")
        st.stop()
    if laycan_end < laycan_start:
        st.error("Laycan end must be after laycan start.")
        st.stop()
    voyage = Voyage(commodity, origin, destination, laycan_start, laycan_end)
    if use_sample or not keys_ready:
        st.session_state["result"] = sample_result()
        st.session_state["voyage"] = Voyage(**SAMPLE_VOYAGE, laycan_start=laycan_start,
                                             laycan_end=laycan_end)
    else:
        try:
            with st.status("Running the CargoPulse agent", expanded=True) as status:
                result = run_pipeline(voyage, progress=lambda m: status.write(f"• {m}"))
                status.update(label="Brief ready", state="complete", expanded=False)
            st.session_state["result"] = result
            st.session_state["voyage"] = voyage
        except Exception as exc:
            st.error(f"The live run failed: {exc}. Check your API keys and model ID, "
                     "or switch on sample mode.")
            st.stop()

result = st.session_state.get("result")
if not result:
    st.info("Pick a voyage and click **Generate voyage brief**.")
    st.stop()

brief, sources, voyage = result["brief"], result["sources"], st.session_state["voyage"]
segments = brief["segments"]

if result["model"].startswith("sample"):
    st.warning("Sample mode: illustrative data, not real news. Add API keys for a live brief.")

# ------------------------------------------------------------------- summary
st.divider()
st.markdown(
    f"**{html.escape(voyage.commodity)}** · {html.escape(voyage.origin)} → "
    f"{html.escape(voyage.destination)} · laycan {voyage.laycan_start:%d %b} – "
    f"{voyage.laycan_end:%d %b %Y} &nbsp; {badge(brief['overall_risk'])}",
    unsafe_allow_html=True,
)
if brief.get("headline"):
    st.markdown(f'<div class="cp-headline">{html.escape(brief["headline"])}</div>',
                unsafe_allow_html=True)

# ------------------------------------------------------------------- map
points = [
    {"name": s["name"], "risk": s["risk"], "lon": s["lon"], "lat": s["lat"],
     "color": RISK_COLORS[s["risk"]][1]}
    for s in segments
]
path = [{"path": [[p["lon"], p["lat"]] for p in points]}]
lats, lons = [p["lat"] for p in points], [p["lon"] for p in points]
mid_lat, mid_lon = (min(lats) + max(lats)) / 2, (min(lons) + max(lons)) / 2
# Zoom so the whole route fits: wider span -> lower zoom.
span = max(max(lats) - min(lats), (max(lons) - min(lons)) * 0.6, 5)
zoom = max(1.0, min(6.0, math.log2(360 / span) - 1.1))
st.pydeck_chart(
    pdk.Deck(
        map_style=pdk.map_styles.CARTO_LIGHT,
        initial_view_state=pdk.ViewState(latitude=mid_lat, longitude=mid_lon, zoom=zoom),
        layers=[
            pdk.Layer("PathLayer", path, get_path="path", get_color=[90, 120, 200],
                      width_min_pixels=2, get_width=3),
            pdk.Layer("ScatterplotLayer", points, get_position="[lon, lat]",
                      get_fill_color="color", get_radius=120000, radius_min_pixels=7,
                      pickable=True),
        ],
        tooltip={"text": "{name}\nrisk: {risk}"},
    ),
    height=440,
)
st.caption("Schematic route: straight lines between waypoints, not a sailing track.")

# ------------------------------------------------------------------- segments
left, right = st.columns([1.6, 1])
with left:
    st.subheader("Segment by segment")
    for s in segments:
        refs = ", ".join(s["source_ids"]) if s["source_ids"] else "no source"
        impact = (f'<div style="margin-top:6px"><b>Voyage impact:</b> '
                  f'{html.escape(s["voyage_impact"])}</div>') if s["voyage_impact"] else ""
        st.markdown(
            f'<div class="cp-card">{badge(s["risk"])} <b>{html.escape(s["name"])}</b>'
            f'<span class="cp-kind">{s["kind"]}</span>'
            f'<div style="margin-top:8px">{html.escape(s["finding"])}</div>{impact}'
            f'<div class="cp-src" style="margin-top:6px">Sources: {refs}</div></div>',
            unsafe_allow_html=True,
        )

with right:
    st.subheader("Check before laycan")
    for item in brief.get("pre_laycan_checks", []):
        st.markdown(f"☐ {item}")
    if brief.get("uncertainties"):
        st.subheader("What we don't know")
        for u in brief["uncertainties"]:
            st.markdown(f"- {u}")

# ------------------------------------------------------------------- sources
st.subheader(f"Sources ({len(sources)})")
if not sources:
    st.write("No recent sources were found for this voyage.")
for sid, src in sources.items():
    with st.expander(f"[{sid}] {src['title']} · {src['segment']}"):
        if src.get("published_date"):
            st.caption(src["published_date"])
        st.write(src["content"])
        if src.get("url"):
            st.markdown(f"[Open source]({src['url']})")

# ------------------------------------------------------------------- footer
st.divider()
route_note = ("curated route table" if result["route_method"] == "table"
              else "chokepoints selected by Nemotron")
st.caption(
    f"Route: {route_note} · Model: {result['model']} on Nebius Token Factory · "
    "Search: Tavily. Public information for operational monitoring only. "
    "Not financial advice and not a trading recommendation."
)
