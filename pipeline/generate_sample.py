"""
generate_sample.py — Produce a realistic sample public/prices.json for development
and demo purposes, without needing to download the full 900MB PPD dataset.

Medians are based on approximate 2022–2024 Land Registry / Zoopla data.
Run with:  python generate_sample.py [--out ../public/prices.json]
"""
import argparse
import json
import math
import random
from datetime import datetime, date
from pathlib import Path

random.seed(42)

# Each entry: district, flat, terraced, semi, detached, all_median
# Prices in £000s.  None = very rare / statistically unreliable for that type.
# Sources: LR PPD aggregates, Rightmove/Zoopla area guides (approx 2022–2024)
DISTRICTS = [
    # (district, flat,  terr,  semi,  detached, delta12m_approx)
    # ── Central Manchester ──────────────────────────────────────────
    ("M1",   230,  None,  None,  None,   1.2),
    ("M2",   295,  None,  None,  None,   0.8),
    ("M3",   245,  None,  None,  None,   1.5),
    ("M4",   210,  240,   None,  None,   2.1),
    ("M5",   195,  220,   280,   None,   1.8),
    ("M6",   145,  165,   215,   290,    0.5),
    ("M7",   None, 145,   190,   260,    0.3),
    ("M8",   None, 125,   170,   None,  -0.5),
    ("M9",   None, 145,   180,   None,   0.7),
    # ── Inner south / south ─────────────────────────────────────────
    ("M11",  None, 155,   210,   None,   1.0),
    ("M12",  None, 150,   195,   None,   0.8),
    ("M13",  185,  220,   265,   None,   1.4),
    ("M14",  180,  275,   360,   None,   2.2),
    ("M15",  210,  240,   None,  None,   1.6),
    ("M16",  200,  295,   385,   None,   2.5),
    ("M18",  None, 165,   210,   None,   0.6),
    ("M19",  195,  280,   370,   490,    2.8),
    ("M20",  220,  350,   455,   660,    3.1),
    ("M21",  215,  330,   430,   620,    2.9),
    ("M22",  155,  215,   270,   385,    1.5),
    ("M23",  145,  195,   255,   360,    1.2),
    # ── North Manchester ────────────────────────────────────────────
    ("M25",  None, 170,   220,   310,    0.9),
    ("M26",  None, 155,   200,   290,    0.7),
    ("M27",  None, 165,   215,   295,    1.0),
    ("M28",  None, 195,   260,   380,    1.8),
    ("M29",  None, 175,   230,   320,    1.1),
    ("M30",  155,  195,   250,   345,    1.4),
    # ── West / Trafford ─────────────────────────────────────────────
    ("M32",  160,  215,   275,   375,    1.3),
    ("M33",  185,  270,   345,   480,    2.2),
    ("M41",  165,  230,   295,   410,    1.7),
    ("M44",  None, 185,   240,   335,    1.0),
    # ── East Manchester ─────────────────────────────────────────────
    ("M34",  None, 175,   230,   330,    1.2),
    ("M35",  None, 160,   210,   300,    0.8),
    ("M38",  None, 150,   195,   275,    0.6),
    ("M40",  None, 155,   200,   None,   0.5),
    ("M43",  None, 160,   210,   290,    0.7),
    ("M45",  None, 190,   245,   355,    1.3),
    ("M46",  None, 160,   205,   285,    0.8),
    # ── Stockport ───────────────────────────────────────────────────
    ("SK1",  145,  185,   250,   375,    1.5),
    ("SK2",  160,  205,   270,   400,    1.8),
    ("SK3",  150,  190,   255,   385,    1.6),
    ("SK4",  165,  225,   310,   450,    2.4),
    ("SK5",  None, 200,   265,   385,    1.7),
    ("SK6",  155,  230,   305,   445,    2.1),
    ("SK7",  185,  280,   385,   545,    2.6),
    ("SK8",  175,  265,   370,   530,    2.5),
    ("SK9",  190,  295,   410,   590,    2.8),
    ("SK10", 165,  250,   345,   495,    2.0),
    ("SK14", None, 195,   250,   360,    1.3),
    ("SK15", None, 175,   230,   335,    1.1),
    ("SK16", None, 165,   215,   310,    0.9),
    # ── Oldham ──────────────────────────────────────────────────────
    ("OL1",  None, 105,   145,   220,    0.2),
    ("OL2",  None, 120,   165,   250,    0.5),
    ("OL4",  None, 115,   155,   235,    0.3),
    ("OL6",  None, 125,   170,   255,    0.4),
    ("OL8",  None, 110,   150,   225,    0.1),
    ("OL9",  None, 115,   155,   230,    0.3),
    ("OL10", None, 120,   160,   240,    0.4),
    ("OL11", None, 115,   155,   230,    0.2),
    ("OL12", None, 125,   165,   245,    0.6),
    ("OL16", None, 130,   175,   260,    0.7),
    # ── Bolton ──────────────────────────────────────────────────────
    ("BL1",  None, 110,   155,   240,    0.4),
    ("BL2",  None, 115,   160,   245,    0.5),
    ("BL3",  None, 100,   140,   215,    0.1),
    ("BL4",  None, 105,   150,   225,    0.3),
    ("BL5",  None, 120,   165,   255,    0.7),
    ("BL6",  None, 130,   180,   275,    0.8),
    ("BL7",  None, 145,   200,   300,    1.0),
    ("BL8",  None, 120,   165,   250,    0.6),
    ("BL9",  None, 115,   160,   240,    0.5),
    # ── Wigan ───────────────────────────────────────────────────────
    ("WN1",  None, 105,   145,   215,    0.3),
    ("WN2",  None, 110,   150,   225,    0.4),
    ("WN3",  None, 100,   140,   210,    0.1),
    ("WN4",  None, 115,   155,   235,    0.5),
    ("WN5",  None, 110,   150,   220,    0.3),
    ("WN6",  None, 120,   165,   250,    0.7),
    ("WN7",  None, 115,   155,   235,    0.5),
    # ── WA (GM fringe) ──────────────────────────────────────────────
    ("WA3",  None, 150,   200,   295,    1.1),
    ("WA14", 170,  250,   335,   490,    2.3),
    ("WA15", 175,  255,   345,   500,    2.4),
]

TYPE_KEYS = ["flat", "terraced", "semi", "detached"]
TYPE_COLS = {
    "flat":     1,
    "terraced": 2,
    "semi":     3,
    "detached": 4,
}

# Rough sale count weights by type (relative)
COUNT_WEIGHTS = {"flat": 1.2, "terraced": 1.8, "semi": 1.5, "detached": 0.8}

# Base total transaction counts per 3 years (rough, scaled by district size)
BASE_COUNTS = {
    "M1": 500, "M2": 150, "M3": 300, "M4": 450, "M5": 350,
    "M6": 280, "M7": 190, "M8": 160, "M9": 175,
    "M11": 220, "M12": 200, "M13": 280, "M14": 320, "M15": 250,
    "M16": 290, "M18": 185, "M19": 310, "M20": 420, "M21": 380,
    "M22": 310, "M23": 285,
    "M25": 220, "M26": 195, "M27": 230, "M28": 265, "M29": 210,
    "M30": 245, "M32": 270, "M33": 350, "M41": 290, "M44": 210,
    "M34": 245, "M35": 215, "M38": 170, "M40": 200, "M43": 185,
    "M45": 215, "M46": 190,
    "SK1": 220, "SK2": 240, "SK3": 200, "SK4": 310, "SK5": 260,
    "SK6": 280, "SK7": 250, "SK8": 260, "SK9": 220, "SK10": 240,
    "SK14": 195, "SK15": 185, "SK16": 175,
    "OL1": 210, "OL2": 235, "OL4": 195, "OL6": 205, "OL8": 190,
    "OL9": 200, "OL10": 215, "OL11": 205, "OL12": 195, "OL16": 220,
    "BL1": 240, "BL2": 225, "BL3": 210, "BL4": 195, "BL5": 215,
    "BL6": 185, "BL7": 170, "BL8": 205, "BL9": 215,
    "WN1": 200, "WN2": 195, "WN3": 185, "WN4": 205, "WN5": 195,
    "WN6": 185, "WN7": 195,
    "WA3": 175, "WA14": 230, "WA15": 240,
}


def make_history(median_k: float, delta12m: float, months: int = 36) -> list:
    """Synthesise 36 monthly medians with realistic noise around the trend."""
    if median_k is None:
        return []

    # Work backwards from current median
    annual_rate = delta12m / 100
    monthly_rate = (1 + annual_rate) ** (1 / 12) - 1

    values = []
    current = median_k * 1000
    for i in range(months):
        noise = random.gauss(0, current * 0.012)
        values.insert(0, max(50000, round(current + noise, -2)))
        current /= (1 + monthly_rate)

    return values


def compute_all_median(row: dict) -> int | None:
    """Weighted average of available type medians as proxy for 'all' median."""
    types_present = [(k, row[k]) for k in TYPE_KEYS if row[k] is not None]
    if not types_present:
        return None
    # weight by count
    total_count = sum(COUNT_WEIGHTS[k] for k, _ in types_present)
    weighted = sum(v * COUNT_WEIGHTS[k] / total_count for k, v in types_present)
    return round(weighted * 1000, -3)


def build_district(row: tuple) -> tuple:
    district, flat_k, terr_k, semi_k, det_k, delta = row
    prices = {
        "flat":     flat_k,
        "terraced": terr_k,
        "semi":     semi_k,
        "detached": det_k,
    }

    base_count = BASE_COUNTS.get(district, 200)
    total_weight = sum(COUNT_WEIGHTS[k] for k in TYPE_KEYS if prices[k] is not None)

    entry = {}

    # Per-type
    for k in TYPE_KEYS:
        pk = prices[k]
        if pk is None:
            continue
        type_count = round(base_count * COUNT_WEIGHTS[k] / total_weight)
        if type_count < 20:
            continue
        # Add slight per-type trend variation
        type_delta = delta + random.gauss(0, 0.4)
        entry[k] = {
            "median":   pk * 1000,
            "count":    type_count,
            "delta12m": round(type_delta, 2),
            "history":  make_history(pk, type_delta),
        }

    if not entry:
        return district, None

    # All-types combined
    all_median = compute_all_median(prices)
    if all_median is None:
        return district, None

    all_count = base_count
    entry["all"] = {
        "median":   all_median,
        "count":    all_count,
        "delta12m": round(delta, 2),
        "history":  make_history(all_median / 1000, delta),
    }

    return district, entry


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="../public/prices.json")
    args = parser.parse_args()

    outpath = Path(args.out)
    outpath.parent.mkdir(parents=True, exist_ok=True)

    districts = {}
    for row in DISTRICTS:
        district, entry = build_district(row)
        if entry:
            districts[district] = entry

    output = {
        "generated": "2024-11-01",
        "window": "2022-01-01 to 2024-11-01",
        "note": "SAMPLE DATA for development/demo — not real Land Registry figures",
        "districts": districts,
    }

    with open(outpath, "w") as f:
        json.dump(output, f, separators=(",", ":"))

    size_kb = outpath.stat().st_size / 1024
    print(f"Written {len(districts)} districts to {outpath} ({size_kb:.1f} KB)")


if __name__ == "__main__":
    main()
