"""
fetch_boundaries.py — Download ONS postcode district GeoJSON, filter to GM,
and simplify to a small file suitable for the web app.

Requirements (in addition to requirements.txt):
    pip install geopandas shapely requests tqdm

The ONS Open Geography Portal hosts postcode district boundaries as a GeoJSON
feature service. We pull the full England + Wales set (~20MB), filter to our
GM districts, simplify geometry, and write public/gm-districts.geojson.

Usage:
    python fetch_boundaries.py [--out ../public/gm-districts.geojson]
                               [--tolerance 0.001]

Tolerance is in degrees (~100m at UK latitudes). 0.001 gives good balance
of accuracy vs file size. Use 0.0005 if you want slightly more detail.

Alternative: if you'd rather use mapshaper manually, download the shapefile
from https://geoportal.statistics.gov.uk/datasets/ons::postcode-districts-december-2023-boundaries-uk-bgc/explore
and run:
    mapshaper postcode-districts.shp -filter "name.match(/^(M|SK|OL|BL|WN|WA3|WA1[12]|WA1[45])/)" \\
              -simplify 5% -o format=geojson gm-districts.geojson
"""
import argparse
import json
import re
import sys
from pathlib import Path

import requests
from tqdm import tqdm

# ONS ArcGIS REST service for Postcode Districts (Dec 2023)
# Returns GeoJSON in EPSG:4326
ONS_SERVICE_URL = (
    "https://services1.arcgis.com/ESMARspQHYMw9BZ9/arcgis/rest/services/"
    "Postcode_Districts_December_2023_Boundaries_UK_BGC/FeatureServer/0/query"
)

GM_PREFIXES = re.compile(r"^(M\d|SK\d|OL\d|BL\d|WN\d|WA3|WA11|WA12|WA14|WA15)")

# Batch size for ArcGIS paging (max 2000 per request)
BATCH = 2000


def fetch_all_features(tolerance_degrees: float) -> list:
    """Page through the ONS service and return all GM features."""
    features = []
    offset = 0

    print("Fetching postcode district boundaries from ONS …")
    while True:
        params = {
            "where": "1=1",
            "outFields": "PostDist,PostCode",
            "returnGeometry": "true",
            "outSR": "4326",
            "f": "geojson",
            "resultOffset": offset,
            "resultRecordCount": BATCH,
        }
        r = requests.get(ONS_SERVICE_URL, params=params, timeout=60)
        r.raise_for_status()
        data = r.json()
        batch = data.get("features", [])
        if not batch:
            break

        for feat in batch:
            name = (
                feat["properties"].get("PostDist") or
                feat["properties"].get("PostCode") or ""
            ).upper().strip()
            feat["properties"]["name"] = name
            if GM_PREFIXES.match(name):
                features.append(feat)

        print(f"  Fetched {offset + len(batch):,} districts total, {len(features)} GM so far …")
        offset += len(batch)

        if len(batch) < BATCH:
            break  # last page

    return features


def simplify_geometry(feature: dict, tolerance: float) -> dict:
    """Simplify feature geometry using Shapely (Douglas-Peucker)."""
    try:
        from shapely.geometry import shape, mapping
        geom = shape(feature["geometry"])
        simplified = geom.simplify(tolerance, preserve_topology=True)
        feature = dict(feature)
        feature["geometry"] = mapping(simplified)
    except ImportError:
        pass  # shapely not installed — return as-is
    return feature


def main():
    parser = argparse.ArgumentParser(description="Fetch and simplify GM district boundaries")
    parser.add_argument("--out", default="../public/gm-districts.geojson")
    parser.add_argument("--tolerance", type=float, default=0.001,
                        help="Simplification tolerance in degrees (default 0.001 ≈ 100m)")
    args = parser.parse_args()

    outpath = Path(args.out)
    outpath.parent.mkdir(parents=True, exist_ok=True)

    try:
        features = fetch_all_features(args.tolerance)
    except requests.RequestException as e:
        print(f"Error fetching from ONS: {e}", file=sys.stderr)
        sys.exit(1)

    if not features:
        print("No GM features found — check ONS service URL.", file=sys.stderr)
        sys.exit(1)

    print(f"Simplifying {len(features)} features (tolerance={args.tolerance}) …")
    features = [simplify_geometry(f, args.tolerance) for f in tqdm(features)]

    geojson = {
        "type": "FeatureCollection",
        "features": features,
    }

    with open(outpath, "w") as f:
        json.dump(geojson, f, separators=(",", ":"))

    size_kb = outpath.stat().st_size / 1024
    print(f"Written {outpath}  ({size_kb:.1f} KB, {len(features)} districts)")


if __name__ == "__main__":
    main()
