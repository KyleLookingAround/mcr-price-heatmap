#!/usr/bin/env python3
"""
Land Registry PPD → prices.json
--------------------------------
Downloads the last 3 years of Price Paid Data, filters to Greater Manchester
postcode districts, aggregates by district × property type, and emits
public/prices.json for the heatmap.

Usage:
    python3 pipeline/build_prices.py

Output: public/prices.json
"""

import csv
import gzip
import io
import json
import os
import re
import sys
import urllib.request
from collections import defaultdict
from pathlib import Path
from statistics import median

# ── Config ────────────────────────────────────────────────────────────────────

# GM postcode prefixes. WA and SK bleed into Cheshire — we filter to known
# GM districts explicitly in GM_DISTRICTS below.
GM_PREFIXES = {"M", "SK", "OL", "BL", "WN", "WA"}

# Postcode districts considered Greater Manchester (not Cheshire).
# Anything not in this set but matching a GM prefix gets dropped.
GM_DISTRICTS = {
    # Manchester
    "M1","M2","M3","M4","M5","M6","M7","M8","M9",
    "M11","M12","M13","M14","M15","M16","M17","M18","M19",
    "M20","M21","M22","M23","M24","M25","M26","M27","M28","M29",
    "M30","M31","M32","M33","M34","M35","M38","M40","M41","M43","M44","M45","M46",
    # Oldham
    "OL1","OL2","OL3","OL4","OL5","OL6","OL7","OL8","OL9","OL10","OL11","OL12","OL16",
    # Bury / Bolton
    "BL0","BL1","BL2","BL3","BL4","BL5","BL6","BL7","BL8","BL9",
    # Wigan
    "WN1","WN2","WN3","WN4","WN5","WN6","WN7","WN8",
    # Stockport (GM part only; SK8/10+ are Cheshire East)
    "SK1","SK2","SK3","SK4","SK5","SK6","SK7","SK8",
    # Salford / Trafford overlap already covered by M-prefix
    # Warrington — not in GM; excluded
}

# PPD columns (fixed schema — no header in the file)
# https://www.gov.uk/guidance/about-the-price-paid-data
COL_PRICE      = 1
COL_DATE       = 2
COL_POSTCODE   = 3
COL_PROP_TYPE  = 4   # D=detached, S=semi, T=terraced, F=flat/maisonette, O=other
COL_NEW_BUILD  = 5   # Y=new build, N=established
COL_DURATION   = 6   # F=freehold, L=leasehold
COL_CATEGORY   = 13  # A=standard, B=additional (repossessions, non-market)

MIN_SALES = 20  # drop districts with fewer sales than this

YEARS = [2022, 2023, 2024]

BASE_URL = "http://prod.publicdata.landregistry.gov.uk.s3-website-eu-west-1.amazonaws.com"

# ── Helpers ───────────────────────────────────────────────────────────────────

def postcode_district(postcode: str) -> str | None:
    """Extract district (e.g. 'M20') from a full postcode."""
    pc = postcode.strip().upper().replace(" ", "")
    m = re.match(r'^([A-Z]{1,2}\d{1,2}[A-Z]?)', pc)
    return m.group(1) if m else None


def download_ppd_year(year: int) -> bytes:
    url = f"{BASE_URL}/pp-{year}.csv"
    print(f"  Downloading {url} ...", flush=True)
    req = urllib.request.Request(url, headers={"User-Agent": "mcr-heatmap/1.0"})
    with urllib.request.urlopen(req, timeout=120) as r:
        data = r.read()
    print(f"    → {len(data) / 1e6:.1f} MB", flush=True)
    return data


# ── Core ──────────────────────────────────────────────────────────────────────

def parse_year(raw_bytes: bytes, records: dict):
    """Parse one year's CSV bytes into records dict (mutates in place)."""
    text = raw_bytes.decode("utf-8", errors="replace")
    reader = csv.reader(io.StringIO(text))
    skipped = included = 0
    for row in reader:
        if len(row) < 14:
            skipped += 1
            continue

        # Drop PPD category B (repossessions, non-standard market sales)
        if row[COL_CATEGORY].strip().upper() == "B":
            skipped += 1
            continue

        # Drop new builds (inflate medians in regenerating areas)
        if row[COL_NEW_BUILD].strip().upper() == "Y":
            skipped += 1
            continue

        # Property type filter — O=other (commercial etc)
        prop_type = row[COL_PROP_TYPE].strip().upper()
        if prop_type not in ("D", "S", "T", "F"):
            skipped += 1
            continue

        postcode = row[COL_POSTCODE].strip()
        district = postcode_district(postcode)
        if not district or district not in GM_DISTRICTS:
            skipped += 1
            continue

        try:
            price = int(row[COL_PRICE].strip())
            date_str = row[COL_DATE].strip()[:7]  # "YYYY-MM"
        except (ValueError, IndexError):
            skipped += 1
            continue

        if price < 10_000 or price > 10_000_000:
            skipped += 1
            continue

        records[district][prop_type].append((date_str, price))
        records[district]["all"].append((date_str, price))
        included += 1

    print(f"    included={included:,}  skipped={skipped:,}")


def aggregate(records: dict) -> dict:
    """
    For each district × type, compute:
      - median price (overall)
      - sale count
      - 12-month delta (last 12m median vs prior 12m median)
      - monthly medians array (oldest → newest, 36 entries)
    """
    from datetime import date

    today = date.today()
    all_months = sorted({
        f"{y}-{m:02d}"
        for y in range(today.year - 3, today.year + 1)
        for m in range(1, 13)
        if f"{y}-{m:02d}" <= today.strftime("%Y-%m")
    })[-36:]

    result = {}

    for district, types in records.items():
        result[district] = {}
        for prop_type, sales in types.items():
            if len(sales) < MIN_SALES:
                continue

            # Group by month
            by_month: dict[str, list[int]] = defaultdict(list)
            for date_str, price in sales:
                by_month[date_str].append(price)

            # Median per month (only months that have data)
            monthly_with_dates = {
                m: median(prices)
                for m, prices in by_month.items()
                if prices
            }

            # Fill monthly array for sparkline (None where no data)
            monthly_values = []
            for m in all_months:
                monthly_values.append(monthly_with_dates.get(m))

            # Forward-fill gaps for sparkline display
            last = None
            filled = []
            for v in monthly_values:
                if v is not None:
                    last = v
                filled.append(last)
            # If all None, skip
            if all(v is None for v in filled):
                continue

            # Overall median
            all_prices = [p for _, p in sales]
            med = round(median(all_prices))

            # 12-month delta: compare last 12 months vs prior 12 months
            sorted_months = sorted(monthly_with_dates.keys())
            recent = sorted_months[-12:] if len(sorted_months) >= 12 else sorted_months
            prior  = sorted_months[-24:-12] if len(sorted_months) >= 24 else []

            delta = None
            if recent and prior:
                recent_med = median([monthly_with_dates[m] for m in recent])
                prior_med  = median([monthly_with_dates[m] for m in prior])
                if prior_med:
                    delta = round((recent_med - prior_med) / prior_med, 4)

            result[district][prop_type] = {
                "median":  med,
                "count":   len(all_prices),
                "delta12m": delta,
                "monthly": [round(v) if v is not None else None for v in filled],
            }

    return result


# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    out_dir = Path(__file__).parent.parent / "public"
    out_dir.mkdir(exist_ok=True)
    out_path = out_dir / "prices.json"

    cache_dir = Path(__file__).parent / ".cache"
    cache_dir.mkdir(exist_ok=True)

    records: dict[str, dict[str, list]] = defaultdict(
        lambda: defaultdict(list)
    )

    for year in YEARS:
        cache_file = cache_dir / f"pp-{year}.csv"
        if cache_file.exists():
            print(f"Using cached pp-{year}.csv ({cache_file.stat().st_size / 1e6:.1f} MB)")
            raw = cache_file.read_bytes()
        else:
            try:
                raw = download_ppd_year(year)
                cache_file.write_bytes(raw)
            except Exception as e:
                print(f"  WARNING: could not download {year}: {e}", file=sys.stderr)
                continue

        print(f"Parsing {year}...")
        parse_year(raw, records)

    print(f"\nDistricts found: {len(records)}")

    print("Aggregating...")
    result = aggregate(records)

    print(f"Districts with sufficient data: {len(result)}")

    out_path.write_text(json.dumps(result, separators=(",", ":")))
    size_kb = out_path.stat().st_size / 1024
    print(f"\nWrote {out_path} ({size_kb:.1f} KB)")

    # Summary
    sample = list(result.items())[:5]
    for district, types in sample:
        med = types.get("all", {}).get("median")
        cnt = types.get("all", {}).get("count")
        print(f"  {district}: £{med:,} ({cnt} sales)")


if __name__ == "__main__":
    main()
