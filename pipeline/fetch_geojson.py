#!/usr/bin/env python3
"""
Fetch ONS postcode district boundaries for Greater Manchester and simplify.

The raw ONS file is ~20MB; this script fetches just the GM districts and
writes a simplified ~100KB GeoJSON to public/gm-districts.geojson.

Simplification is done with the Visvalingam-Whyatt algorithm via the
`mapshaper` npm tool (installed globally or locally) if available,
otherwise falls back to a basic coordinate rounding approach.

Usage:
    python3 pipeline/fetch_geojson.py

Requires: urllib (stdlib only for download)
Optional: mapshaper (npm install -g mapshaper) for proper simplification
"""

import json
import os
import subprocess
import sys
import tempfile
import urllib.request
import zipfile
from pathlib import Path
from io import BytesIO

# GM districts (must match build_prices.py)
GM_DISTRICTS = {
    "M1","M2","M3","M4","M5","M6","M7","M8","M9",
    "M11","M12","M13","M14","M15","M16","M17","M18","M19",
    "M20","M21","M22","M23","M24","M25","M26","M27","M28","M29",
    "M30","M31","M32","M33","M34","M35","M38","M40","M41","M43","M44","M45","M46",
    "OL1","OL2","OL3","OL4","OL5","OL6","OL7","OL8","OL9","OL10","OL11","OL12","OL16",
    "BL0","BL1","BL2","BL3","BL4","BL5","BL6","BL7","BL8","BL9",
    "WN1","WN2","WN3","WN4","WN5","WN6","WN7","WN8",
    "SK1","SK2","SK3","SK4","SK5","SK6","SK7","SK8",
}

# ONS Open Geography — Postcode Districts (December 2022) Boundaries GB BFC
# ~20MB zipped shapefile; we download and filter in-place
ONS_GEOJSON_URL = (
    "https://services1.arcgis.com/ESMARspQHYMw9BZ9/arcgis/rest/services/"
    "Postcode_Districts_December_2022_Boundaries_GB_BFC/FeatureServer/0/"
    "query?where=1%3D1&outFields=PCDIS%2CPCDISNM&outSR=4326&f=geojson"
    "&resultOffset=0&resultRecordCount=3000"
)

# Alternative: ONS bulk download (more reliable)
ONS_BULK_URL = (
    "https://open-geography-portalx-ons.hub.arcgis.com/api/download/v1/items/"
    "8f6b96b51d9d4bc38bca37c3149e5748/geojson?redirect=true&layers=0"
)


def simplify_coords(coords, precision=4):
    """Round coordinates to reduce file size (basic simplification fallback)."""
    if isinstance(coords[0], (int, float)):
        return [round(c, precision) for c in coords]
    return [simplify_coords(ring, precision) for ring in coords]


def simplify_geojson(geojson_str: str, precision: int = 4) -> str:
    """Simplify by rounding coordinates (fallback when mapshaper unavailable)."""
    gj = json.loads(geojson_str)
    for feature in gj.get("features", []):
        geom = feature.get("geometry", {})
        if geom:
            geom["coordinates"] = simplify_coords(geom["coordinates"], precision)
    return json.dumps(gj, separators=(",", ":"))


def try_mapshaper(input_path: Path, output_path: Path) -> bool:
    """Try to simplify with mapshaper; returns True on success."""
    for cmd in ["mapshaper", "./node_modules/.bin/mapshaper"]:
        try:
            result = subprocess.run(
                [cmd, str(input_path),
                 "-simplify", "dp", "10%", "keep-shapes",
                 "-o", str(output_path), "format=geojson"],
                capture_output=True, text=True, timeout=60
            )
            if result.returncode == 0:
                print(f"  Simplified with mapshaper: {output_path.stat().st_size / 1024:.1f} KB")
                return True
            else:
                print(f"  mapshaper error: {result.stderr.strip()}")
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass
    return False


def fetch_gm_geojson() -> dict:
    """
    Fetch postcode district GeoJSON from ONS and filter to GM districts.
    Falls back to trying multiple URLs.
    """
    urls = [
        # Primary: ArcGIS feature service (paginated, but GM is <200 features)
        (
            "https://services1.arcgis.com/ESMARspQHYMw9BZ9/arcgis/rest/services/"
            "Postcode_Districts_December_2022_Boundaries_GB_BFC/FeatureServer/0/"
            "query?where=PCDIS+LIKE+'M%25'+OR+PCDIS+LIKE+'SK%25'+OR+PCDIS+LIKE+'OL%25'"
            "+OR+PCDIS+LIKE+'BL%25'+OR+PCDIS+LIKE+'WN%25'"
            "&outFields=PCDIS&outSR=4326&f=geojson&resultRecordCount=500"
        ),
    ]

    for url in urls:
        print(f"  Fetching: {url[:80]}...")
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "mcr-heatmap/1.0"})
            with urllib.request.urlopen(req, timeout=60) as r:
                data = r.read()
            gj = json.loads(data)
            features = gj.get("features", [])
            print(f"  Got {len(features)} features")
            if features:
                return gj
        except Exception as e:
            print(f"  Failed: {e}", file=sys.stderr)

    return None


def main():
    out_dir = Path(__file__).parent.parent / "public"
    out_dir.mkdir(exist_ok=True)
    out_path = out_dir / "gm-districts.geojson"

    print("Fetching ONS postcode district boundaries...")
    gj = fetch_gm_geojson()

    if gj is None:
        print(
            "ERROR: Could not fetch GeoJSON. Please download manually:\n"
            "  https://geoportal.statistics.gov.uk/datasets/postcode-districts-december-2022-boundaries-gb-bfc\n"
            "  Filter to GM districts and save as public/gm-districts.geojson",
            file=sys.stderr,
        )
        sys.exit(1)

    # Filter to GM districts and normalise properties
    features = []
    for feature in gj.get("features", []):
        props = feature.get("properties", {})
        # Field name varies by API version
        district = (
            props.get("PCDIS") or
            props.get("pcd_district") or
            props.get("name") or ""
        ).strip().upper()
        if district in GM_DISTRICTS:
            feature["properties"] = {
                "name": district,
                "label": props.get("PCDISNM", district),
            }
            features.append(feature)

    print(f"  GM districts matched: {len(features)}")

    filtered = {"type": "FeatureCollection", "features": features}
    raw_str = json.dumps(filtered, separators=(",", ":"))

    # Try mapshaper first; fall back to coordinate rounding
    with tempfile.NamedTemporaryFile(suffix=".geojson", mode="w", delete=False) as tmp:
        tmp.write(raw_str)
        tmp_path = Path(tmp.name)

    simplified_path = tmp_path.with_suffix(".simplified.geojson")
    if try_mapshaper(tmp_path, simplified_path):
        out_path.write_bytes(simplified_path.read_bytes())
    else:
        print("  Falling back to coordinate rounding (precision=4)...")
        simplified_str = simplify_geojson(raw_str, precision=4)
        out_path.write_text(simplified_str)

    # Cleanup
    tmp_path.unlink(missing_ok=True)
    simplified_path.unlink(missing_ok=True)

    size_kb = out_path.stat().st_size / 1024
    print(f"Wrote {out_path} ({size_kb:.1f} KB)")
    if size_kb > 300:
        print(
            f"  WARNING: File is {size_kb:.0f} KB — install mapshaper for better simplification:\n"
            "  npm install -g mapshaper && python3 pipeline/fetch_geojson.py"
        )


if __name__ == "__main__":
    main()
