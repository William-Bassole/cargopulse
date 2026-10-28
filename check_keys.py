"""Run this first: checks both API keys and lists the NVIDIA models your key can use.

    python check_keys.py
"""

import tomllib
from pathlib import Path

from openai import OpenAI
from tavily import TavilyClient

cfg = tomllib.loads(Path(".streamlit/secrets.toml").read_text())
client = OpenAI(base_url=cfg.get("NEBIUS_BASE_URL", "https://api.tokenfactory.nebius.com/v1/"),
                api_key=cfg["NEBIUS_API_KEY"])

nvidia = sorted(m.id for m in client.models.list().data if m.id.lower().startswith("nvidia/"))
print("NVIDIA models available on your Token Factory key:")
for m in nvidia:
    print("  ", m)

model = cfg.get("NEBIUS_MODEL", "nvidia/nemotron-3-super-120b-a12b")
print(f"\nTesting {model} ...")
r = client.chat.completions.create(model=model, max_tokens=50,
                                   messages=[{"role": "user", "content": "Reply with: ok"}])
print("Nemotron says:", (r.choices[0].message.content or "").strip()[:200])

res = TavilyClient(api_key=cfg["TAVILY_API_KEY"]).search("Strait of Hormuz shipping", topic="news",
                                                         max_results=2)
print("Tavily OK:", [x["title"] for x in res.get("results", [])])
