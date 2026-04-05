# Manchester House Price Heatmap

Interactive heatmap of resale house prices across Greater Manchester postcode districts, colour-coded against your budget.

**Live demo:** https://kylelookingaround.github.io/mcr-price-heatmap/

---

## What it does

- Shows median resale prices by postcode district (M, SK, OL, BL, WN, WA)
- Colours districts green / amber / red relative to your budget (≤95% / 95–115% / >115%)
- Property type filter — flat / terraced / semi / detached
- 12-month trend arrow and 36-month sparkline per district
- Rightmove search link per district
- Mortgage calculator: deposit + term + rate → monthly payment
- Zoom to affordable areas button
- Budget + property type persisted in localStorage

---

## Stack

- **Frontend:** Vite + vanilla JS + [Leaflet](https://leafletjs.com/)
- **Boundaries:** ONS postcode district GeoJSON, simplified with RDP (~55 KB)
- **Data pipeline:** Python (pandas) against HM Land Registry Price Paid Data
- **Deployment:** GitHub Pages (static, sub-500 KB on the wire)

---

## Getting started (dev)

```bash
npm install
npm run dev
```

Opens at http://localhost:3000. The `public/` folder ships with:
- `prices.json` — **sample data** for development (realistic but not real LR figures)
- `gm-districts.geojson` — simplified GM postcode district boundaries

---

## Generating real data

### 1. Download boundaries (one-time)

```bash
cd pipeline
pip install -r requirements.txt geopandas shapely
python fetch_boundaries.py --out ../public/gm-districts.geojson
```

Or use [mapshaper](https://mapshaper.org/) with the ONS shapefile (see script comments).

### 2. Download Price Paid Data

```bash
python fetch_ppd.py --years 3 --outdir ./raw
```

Downloads ~900 MB of Land Registry CSVs (last 3 years). They're excluded from git via `.gitignore`.

### 3. Aggregate

```bash
python aggregate.py --rawdir ./raw --out ../public/prices.json
```

Filters to GM postcodes, strips new builds and PPD category B (repossessions), aggregates by district × property type, emits `prices.json`.

Options:
```
--min-sales 20          # minimum sales threshold (default 20)
--include-new-builds    # override the default new-build exclusion
--include-category-b    # include repossession transactions
```

---

## Deployment (GitHub Pages)

```bash
npm run build
# Push dist/ contents to gh-pages branch, or use GitHub Actions
```

The `vite.config.js` base is already set to `/mcr-price-heatmap/`.

---

## Data notes

- **New builds excluded** by default — they inflate medians in regenerating areas (Ancoats, NOMA)
- **WA postcodes:** only WA3, WA11, WA12, WA14, WA15 — the rest bleed into Warrington/Cheshire
- **Minimum 20 sales** per district for "all types"; ~7 per individual type — below this the median is noise
- **Leasehold flats** can skew low (ground rent, short leases) — no direct fix in PPD, but filtering new builds helps
- Districts with fewer than 20 total sales are omitted from the map

---

## Roadmap

- [ ] Commute overlay — travel times from each district to Piccadilly (Google Distance Matrix, one-time bake)
- [ ] Sector-level zoom (M20 2 etc.) as a drill-down layer
- [ ] Ofsted / school overlay (requires spatial join — ward boundaries don't match postcode districts)
