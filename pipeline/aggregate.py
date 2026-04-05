"""
aggregate.py — Filter PPD CSVs to Greater Manchester postcodes, aggregate by
postcode district × property type, and emit public/prices.json.

Usage:
    python aggregate.py [--rawdir ./raw] [--out ../public/prices.json]
                        [--min-sales 20] [--exclude-new-builds]
                        [--exclude-category-b]

Output JSON structure:
    {
      "generated": "2025-01-15",
      "window": "2022-01-01 to 2025-01-01",
      "districts": {
        "M20": {
          "all":      { "median": 340000, "count": 412, "delta12m": 2.1, "history": [...36 monthly medians] },
          "flat":     { "median": 215000, "count": 180, "delta12m": 1.4, "history": [...] },
          "terraced": { "median": 355000, "count": 120, "delta12m": 3.0, "history": [...] },
          "semi":     { "median": 460000, "count":  80, "delta12m": 2.5, "history": [...] },
          "detached": { "median": 670000, "count":  32, "delta12m": 1.8, "history": [...] }
        },
        ...
      }
    }
"""
import argparse
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

# Greater Manchester postcode area prefixes we care about.
# WA bleed into Warrington/Cheshire — we keep the districts that fall within
# the GM boundary: WA3 (Leigh area), WA11, WA12 (St Helens fringe), WA14, WA15 (Altrincham/Sale).
GM_PREFIXES = {"M", "SK", "OL", "BL", "WN"}

# WA districts that are genuinely in or adjacent to GM
GM_WA_DISTRICTS = {"WA3", "WA11", "WA12", "WA14", "WA15"}

# PPD property type codes → our names
PTYPE_MAP = {
    "D": "detached",
    "S": "semi",
    "T": "terraced",
    "F": "flat",
}

PPD_COLUMNS = [
    "transaction_id", "price", "date", "postcode", "property_type",
    "new_build", "duration", "paon", "saon", "street", "locality",
    "town", "district_name", "county", "ppd_category", "record_status",
]


def load_raw(rawdir: Path) -> pd.DataFrame:
    """Load all CSV files in rawdir into a single DataFrame."""
    csvs = sorted(rawdir.glob("pp-*.csv"))
    if not csvs:
        print(f"Error: no pp-*.csv files found in {rawdir}", file=sys.stderr)
        sys.exit(1)

    parts = []
    for csv in csvs:
        print(f"  Reading {csv.name} …", end=" ", flush=True)
        df = pd.read_csv(
            csv,
            header=None,
            names=PPD_COLUMNS,
            usecols=["price", "date", "postcode", "property_type", "new_build",
                     "duration", "ppd_category", "record_status"],
            dtype={"price": "int32", "postcode": "str", "property_type": "str",
                   "new_build": "str", "ppd_category": "str", "record_status": "str"},
            parse_dates=["date"],
            low_memory=True,
        )
        print(f"{len(df):,} rows")
        parts.append(df)

    return pd.concat(parts, ignore_index=True)


def extract_district(postcode: pd.Series) -> pd.Series:
    """'M20 2LN' → 'M20', 'SK4 1AB' → 'SK4'."""
    return postcode.str.strip().str.split().str[0].str.upper()


def filter_gm(df: pd.DataFrame) -> pd.DataFrame:
    """Keep only rows in Greater Manchester postcode districts."""
    df = df.copy()
    df["district"] = extract_district(df["postcode"])
    df["area"] = df["district"].str.extract(r"^([A-Z]+)")

    mask = (
        df["area"].isin(GM_PREFIXES) |
        df["district"].isin(GM_WA_DISTRICTS)
    )
    filtered = df[mask].copy()
    print(f"  GM filter: {len(df):,} → {len(filtered):,} rows")
    return filtered


def apply_filters(df: pd.DataFrame, exclude_new_builds: bool, exclude_cat_b: bool) -> pd.DataFrame:
    n0 = len(df)

    # Remove deletions/corrections — keep only additions
    df = df[df["record_status"] == "A"]

    if exclude_cat_b:
        df = df[df["ppd_category"] == "A"]

    if exclude_new_builds:
        df = df[df["new_build"] != "Y"]

    # Drop rows with unknown/other property type
    df = df[df["property_type"].isin(PTYPE_MAP.keys())]

    # Drop null postcodes
    df = df[df["postcode"].notna() & (df["postcode"].str.strip() != "")]

    # Sanity-check prices
    df = df[(df["price"] > 10_000) & (df["price"] < 10_000_000)]

    print(f"  Post-filter: {n0:,} → {len(df):,} rows")
    return df


def make_history(grp: pd.DataFrame, months: int = 36) -> list:
    """Build a list of monthly medians (oldest → newest), None for missing months."""
    end = grp["date"].max().to_period("M")
    start = end - (months - 1)

    grp = grp.copy()
    grp["period"] = grp["date"].dt.to_period("M")

    monthly = (
        grp.groupby("period")["price"]
        .median()
        .reindex(pd.period_range(start, end, freq="M"))
    )
    return [int(v) if not np.isnan(v) else None for v in monthly]


def compute_delta12m(grp: pd.DataFrame, ref_date: pd.Timestamp) -> float | None:
    """Percentage change in median price: (last 12m) vs (prior 12m)."""
    cutoff = ref_date - timedelta(days=365)
    cutoff2 = ref_date - timedelta(days=730)

    recent = grp[grp["date"] >= cutoff]["price"]
    prior  = grp[(grp["date"] >= cutoff2) & (grp["date"] < cutoff)]["price"]

    if len(recent) < 5 or len(prior) < 5:
        return None

    pct = (recent.median() - prior.median()) / prior.median() * 100
    return round(float(pct), 2)


def aggregate_group(grp: pd.DataFrame, ref_date: pd.Timestamp, min_sales: int) -> dict | None:
    if len(grp) < min_sales:
        return None
    return {
        "median":    int(grp["price"].median()),
        "count":     len(grp),
        "delta12m":  compute_delta12m(grp, ref_date),
        "history":   make_history(grp),
    }


def build_output(df: pd.DataFrame, min_sales: int) -> dict:
    ref_date = df["date"].max()
    df["ptype_name"] = df["property_type"].map(PTYPE_MAP)

    result = {}
    for district, dgrp in df.groupby("district"):
        entry = {}

        # All types combined
        agg_all = aggregate_group(dgrp, ref_date, min_sales)
        if agg_all is None:
            continue  # not enough data even for "all"
        entry["all"] = agg_all

        # Per property type
        for ptype_name, tgrp in dgrp.groupby("ptype_name"):
            agg = aggregate_group(tgrp, ref_date, min_sales // 3)  # lower threshold per type
            if agg:
                entry[ptype_name] = agg

        result[district] = entry

    return result


def main():
    parser = argparse.ArgumentParser(description="Aggregate PPD data into prices.json")
    parser.add_argument("--rawdir", default="./raw", help="Directory containing pp-*.csv files")
    parser.add_argument("--out", default="../public/prices.json", help="Output JSON path")
    parser.add_argument("--min-sales", type=int, default=20, help="Minimum sales for a district to be included")
    parser.add_argument("--exclude-new-builds", action="store_true", default=True, help="Exclude new build transactions")
    parser.add_argument("--include-new-builds", dest="exclude_new_builds", action="store_false")
    parser.add_argument("--exclude-category-b", action="store_true", default=True, help="Exclude PPD category B (repossessions etc.)")
    parser.add_argument("--include-category-b", dest="exclude_category_b", action="store_false")
    args = parser.parse_args()

    rawdir = Path(args.rawdir)
    outpath = Path(args.out)
    outpath.parent.mkdir(parents=True, exist_ok=True)

    print("Loading raw data …")
    df = load_raw(rawdir)

    print("Filtering to GM …")
    df = filter_gm(df)

    print("Applying quality filters …")
    df = apply_filters(df, args.exclude_new_builds, args.exclude_category_b)

    print("Aggregating …")
    districts = build_output(df, args.min_sales)

    window_start = df["date"].min().strftime("%Y-%m-%d")
    window_end   = df["date"].max().strftime("%Y-%m-%d")

    output = {
        "generated": datetime.now().strftime("%Y-%m-%d"),
        "window":    f"{window_start} to {window_end}",
        "districts": districts,
    }

    print(f"Writing {len(districts)} districts to {outpath} …")
    with open(outpath, "w") as f:
        json.dump(output, f, separators=(",", ":"))

    size_kb = outpath.stat().st_size / 1024
    print(f"Done. {outpath} ({size_kb:.1f} KB)")


if __name__ == "__main__":
    main()
