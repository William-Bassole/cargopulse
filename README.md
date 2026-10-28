# CargoPulse

**Voyage disruption brief for commodity trading operations.**

You tell CargoPulse about a cargo: the commodity, the load port, the discharge port and the laycan. It works out which chokepoints the vessel will cross, searches recent news on every segment of the trip, and asks NVIDIA Nemotron to rate the risk to *this* voyage, segment by segment. Every finding points back to a source you can open.

Built for the Nebius x NVIDIA Global AI Hackathon 2026, Best Apps and Agents track.

> Live demo: `<your Streamlit URL>` · Video: `<your YouTube link>`

## The problem

Geneva is one of the world's biggest commodity trading hubs. On the operations side of a trading desk, someone has to answer a simple question before every fixture: *is anything on this route likely to delay the cargo or cost us demurrage?*

Today that means opening a dozen news tabs, checking each strait and port by hand, and writing a short note for the trader. Generic news search does not know that a Ras Tanura to Rotterdam cargo goes through Hormuz, the Red Sea, Suez, Gibraltar and the Channel, so the analyst has to do that mapping in their head.

## What it does

1. **Plans the route.** A curated table maps the voyage to its chokepoints in sailing order. If the voyage is not in the table, Nemotron picks the chokepoints, but only from a fixed list of known straits and canals, so it cannot make one up.
2. **Searches each segment.** One Tavily news search per segment (load port, every chokepoint, discharge port), run in parallel, limited to the last 14 days.
3. **Writes the brief.** Nemotron receives the numbered sources and returns, for each segment, a risk level (low / medium / high / insufficient), what the sources say, the likely effect on transit time or demurrage, and the source IDs behind it. It also lists what to check before laycan and what the sources do not establish.
4. **Checks the model's work.** The app drops any source ID the model invents and downgrades any claim without a source to "insufficient". No source, no rating.

The result is one page: a schematic route map coloured by risk, a card per segment, a pre-laycan checklist and the full source list.

CargoPulse does not forecast prices or recommend trades. It is an operational monitoring tool built on public information.

## How NVIDIA Nemotron and Nebius Token Factory are used

All model calls go to **Nebius Token Factory** through its OpenAI-compatible API (`https://api.tokenfactory.nebius.com/v1/`), at runtime, on every brief.

| Step | Model | Why |
|---|---|---|
| Route planning fallback | Nemotron (default `nvidia/nemotron-3-super-120b-a12b`) | Choose chokepoints for voyages outside the curated table, constrained to a fixed list |
| Voyage brief | Same model | Read up to ~25 sources across segments and produce a structured, source-cited JSON brief |

The model ID is a setting (`NEBIUS_MODEL`), so you can switch to Nemotron 3 Nano for speed or Nemotron 3 Ultra for harder reasoning without touching the code. Token Factory made it possible to try several Nemotron sizes in minutes with the same client code.

**Tavily** provides the real-time search: one `topic="news"` call per segment, every run.

## Run it locally

```bash
git clone https://github.com/William-Bassole/cargopulse.git
cd cargopulse
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp .streamlit/secrets.toml.example .streamlit/secrets.toml
# then paste your Token Factory and Tavily keys into .streamlit/secrets.toml

python check_keys.py      # lists your NVIDIA models and tests both keys
streamlit run app.py
```

Without keys the app starts in **sample mode**, which shows clearly labelled illustrative data and makes no API calls.

## Deploy

On [Streamlit Community Cloud](https://share.streamlit.io): new app, point it at this repo and `app.py`, then paste the contents of `secrets.toml` into *App settings → Secrets*.

## Project structure

```
app.py            Streamlit interface
agent.py          Route planning, Tavily search, Nemotron brief, validation
routes.py         Ports, chokepoints and the curated route table
sample_data.py    Illustrative output for sample mode
check_keys.py     Sanity check for API keys and available models
```

## Limits

- The route map is schematic: straight lines between waypoints, not a sailing track.
- The route table covers common trades; other voyages rely on Nemotron's choice from the known chokepoint list.
- Quality depends on what Tavily finds in recent news. When nothing relevant comes back, CargoPulse says "insufficient" instead of guessing.

## License

MIT, see [LICENSE](LICENSE).
