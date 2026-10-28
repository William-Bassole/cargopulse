"""Static maritime knowledge: ports, chokepoints and the chokepoints a voyage crosses.

The table is deliberately small and hand-curated. When a voyage is not covered,
the agent asks Nemotron to pick chokepoints from KNOWN_CHOKEPOINTS only.
"""

from __future__ import annotations

# port -> (region, lat, lon)
PORTS: dict[str, tuple[str, float, float]] = {
    "Primorsk (Russia)": ("baltic", 60.35, 28.61),
    "Gdansk (Poland)": ("baltic", 54.40, 18.67),
    "Rotterdam (Netherlands)": ("nw_europe", 51.95, 4.14),
    "Antwerp (Belgium)": ("nw_europe", 51.28, 4.30),
    "Novorossiysk (Russia)": ("black_sea", 44.72, 37.79),
    "Constanta (Romania)": ("black_sea", 44.17, 28.65),
    "Odesa (Ukraine)": ("black_sea", 46.49, 30.74),
    "Trieste (Italy)": ("mediterranean", 45.65, 13.77),
    "Ras Tanura (Saudi Arabia)": ("persian_gulf", 26.64, 50.16),
    "Fujairah (UAE)": ("gulf_of_oman", 25.12, 56.36),
    "Ras Laffan (Qatar)": ("persian_gulf", 25.91, 51.58),
    "Jamnagar (India)": ("india_west", 22.47, 69.75),
    "Singapore": ("se_asia", 1.26, 103.84),
    "Ningbo (China)": ("east_asia", 29.94, 121.88),
    "Yokohama (Japan)": ("east_asia", 35.45, 139.66),
    "Houston (USA)": ("us_gulf", 29.73, -95.02),
    "Sabine Pass (USA)": ("us_gulf", 29.73, -93.87),
    "Santos (Brazil)": ("brazil", -23.96, -46.30),
    "Bonny (Nigeria)": ("west_africa", 4.43, 7.16),
    "Port Hedland (Australia)": ("australia", -20.31, 118.58),
    "Antofagasta (Chile)": ("chile", -23.65, -70.40),
}

# chokepoint -> (lat, lon, search hint)
KNOWN_CHOKEPOINTS: dict[str, tuple[float, float, str]] = {
    "Danish Straits": (55.6, 12.7, "Danish Straits Baltic tanker shipping"),
    "English Channel": (50.5, -0.5, "English Channel shipping"),
    "Strait of Gibraltar": (35.95, -5.6, "Strait of Gibraltar shipping"),
    "Bosphorus": (41.12, 29.07, "Bosphorus Turkish Straits tanker transit"),
    "Suez Canal": (30.6, 32.33, "Suez Canal transit shipping"),
    "Bab el-Mandeb / Red Sea": (12.6, 43.3, "Red Sea Bab el-Mandeb shipping attacks"),
    "Strait of Hormuz": (26.57, 56.25, "Strait of Hormuz tanker shipping"),
    "Strait of Malacca": (2.5, 101.4, "Strait of Malacca shipping"),
    "Cape of Good Hope": (-34.4, 18.5, "Cape of Good Hope rerouting shipping weather"),
    "Panama Canal": (9.08, -79.68, "Panama Canal transit restrictions"),
    "Taiwan Strait": (24.5, 119.5, "Taiwan Strait shipping"),
    "Lombok / Makassar Strait": (-8.7, 115.7, "Lombok Strait shipping"),
}

# (origin_region, destination_region) -> ordered chokepoints (one direction; reverse is derived)
ROUTES: dict[tuple[str, str], list[str]] = {
    ("baltic", "nw_europe"): ["Danish Straits"],
    ("baltic", "mediterranean"): ["Danish Straits", "English Channel", "Strait of Gibraltar"],
    ("baltic", "india_west"): ["Danish Straits", "English Channel", "Strait of Gibraltar",
                               "Suez Canal", "Bab el-Mandeb / Red Sea"],
    ("black_sea", "nw_europe"): ["Bosphorus", "Strait of Gibraltar", "English Channel"],
    ("black_sea", "mediterranean"): ["Bosphorus"],
    ("black_sea", "east_asia"): ["Bosphorus", "Suez Canal", "Bab el-Mandeb / Red Sea",
                                 "Strait of Malacca"],
    ("black_sea", "india_west"): ["Bosphorus", "Suez Canal", "Bab el-Mandeb / Red Sea"],
    ("persian_gulf", "nw_europe"): ["Strait of Hormuz", "Bab el-Mandeb / Red Sea",
                                    "Suez Canal", "Strait of Gibraltar", "English Channel"],
    ("persian_gulf", "mediterranean"): ["Strait of Hormuz", "Bab el-Mandeb / Red Sea", "Suez Canal"],
    ("persian_gulf", "india_west"): ["Strait of Hormuz"],
    ("persian_gulf", "se_asia"): ["Strait of Hormuz"],
    ("persian_gulf", "east_asia"): ["Strait of Hormuz", "Strait of Malacca"],
    ("gulf_of_oman", "east_asia"): ["Strait of Malacca"],
    ("gulf_of_oman", "nw_europe"): ["Bab el-Mandeb / Red Sea", "Suez Canal",
                                    "Strait of Gibraltar", "English Channel"],
    ("us_gulf", "nw_europe"): ["English Channel"],
    ("us_gulf", "mediterranean"): ["Strait of Gibraltar"],
    ("us_gulf", "east_asia"): ["Panama Canal"],
    ("us_gulf", "brazil"): [],
    ("brazil", "east_asia"): ["Cape of Good Hope", "Strait of Malacca"],
    ("brazil", "nw_europe"): [],
    ("west_africa", "nw_europe"): ["English Channel"],
    ("west_africa", "india_west"): ["Cape of Good Hope"],
    ("west_africa", "east_asia"): ["Cape of Good Hope", "Strait of Malacca"],
    ("australia", "east_asia"): ["Lombok / Makassar Strait"],
    ("chile", "east_asia"): [],
    ("chile", "nw_europe"): ["Panama Canal", "English Channel"],
    ("se_asia", "east_asia"): ["Taiwan Strait"],
    ("nw_europe", "east_asia"): ["English Channel", "Strait of Gibraltar", "Suez Canal",
                                 "Bab el-Mandeb / Red Sea", "Strait of Malacca"],
    ("nw_europe", "se_asia"): ["English Channel", "Strait of Gibraltar", "Suez Canal",
                               "Bab el-Mandeb / Red Sea"],
    ("mediterranean", "east_asia"): ["Suez Canal", "Bab el-Mandeb / Red Sea", "Strait of Malacca"],
    ("mediterranean", "india_west"): ["Suez Canal", "Bab el-Mandeb / Red Sea"],
    ("us_gulf", "india_west"): ["Strait of Gibraltar", "Suez Canal", "Bab el-Mandeb / Red Sea"],
    ("persian_gulf", "us_gulf"): ["Strait of Hormuz", "Cape of Good Hope"],
    ("australia", "nw_europe"): ["Cape of Good Hope", "English Channel"],
    ("brazil", "mediterranean"): ["Strait of Gibraltar"],
    ("india_west", "nw_europe"): ["Bab el-Mandeb / Red Sea", "Suez Canal",
                                  "Strait of Gibraltar", "English Channel"],
}

COMMODITIES = [
    "Crude oil",
    "Diesel / gasoil",
    "LNG",
    "Wheat",
    "Copper concentrate",
    "Iron ore",
]


def lookup_chokepoints(origin: str, destination: str) -> list[str] | None:
    """Return ordered chokepoints for a voyage, or None if the table does not cover it."""
    o_region = PORTS[origin][0]
    d_region = PORTS[destination][0]
    if o_region == d_region:
        return []
    if (o_region, d_region) in ROUTES:
        return list(ROUTES[(o_region, d_region)])
    if (d_region, o_region) in ROUTES:
        return list(reversed(ROUTES[(d_region, o_region)]))
    return None
