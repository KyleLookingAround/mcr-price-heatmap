# Data Pipeline

Two scripts that produce the static assets consumed by the map.

## Prerequisites

```
pip3 install -r requirements.txt   # none — stdlib only
npm install -g mapshaper            # optional, for better GeoJSON simplification
```

## 1. GeoJSON boundaries

```bash
python3 pipeline/fetch_geojson.py
```

Downloads ONS postcode district polygons for Greater Manchester (M, OL, BL, WN, SK prefixes),
filters to the 80 districts that fall within GM, and simplifies to ~38KB via mapshaper.

Output: `public/gm-districts.geojson`

## 2. Price data

```bash
python3 pipeline/build_prices.py
```

Downloads Land Registry Price Paid Data (PPD) for 2022–2024 from
`prod.publicdata.landregistry.gov.uk`. Files are cached in `pipeline/.cache/`
so subsequent runs are fast (~300MB per year on first run).

Filters:
- GM postcode districts only (see `GM_DISTRICTS` in the script)
- PPD category A only (drops repossessions and non-market transfers)
- Established (not new build) resale market
- Property types D/S/T/F only (no commercial/other)
- Minimum 20 sales per district per type

Output: `public/prices.json` — keyed by district, with `all` + per-type breakdowns,
each containing `median`, `count`, `delta12m`, and `monthly` (36-month sparkline array).

## WA and SK boundary decisions

- **SK1–SK8** are included (Stockport borough). SK9 and above are Cheshire East.
- **WA** postcodes (Warrington) are excluded — Warrington is not a GM authority.

## Re-running after new PPD releases

Land Registry releases monthly updates. To update:
1. Delete `pipeline/.cache/pp-2024.csv` (or whichever year changed)
2. Re-run `build_prices.py`
