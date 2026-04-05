# CLAUDE.md — MCR Price Heatmap

AI assistant guide for the **Manchester House Price Heatmap** project.

---

## Project Overview

An interactive single-page web app that visualises resale house prices across Greater Manchester postcode districts, colour-coded against a user-defined budget. Hosted on GitHub Pages at `kylelookingaround.github.io/mcr-price-heatmap/`.

Key user features:
- Budget slider/input with affordability colour bands (green/amber/red)
- Property type filter (All / Flat / Terraced / Semi / Detached)
- Mortgage calculator (deposit, term, interest rate)
- Clickable district popups with median price, trend arrow, and 36-month sparkline
- "Zoom to affordable" button to focus on green districts
- Budget and property type preferences persisted in `localStorage`

---

## Repository Structure

```
mcr-price-heatmap/
├── src/                    # Frontend source — vanilla JS ES modules
│   ├── main.js             # Entry point: fetch data, wire up map + controls
│   ├── map.js              # Leaflet map init, GeoJSON layer, styling, recolour
│   ├── controls.js         # Sidebar UI, budget input, property type, mortgage calc
│   ├── colours.js          # Colour band constants and getBand() logic
│   ├── popup.js            # District popup HTML builder
│   ├── sparkline.js        # SVG sparkline chart renderer
│   ├── style.css           # Dark theme, responsive layout (CSS custom properties)
│   └── *.test.js           # Vitest unit tests (one per module)
│
├── pipeline/               # Python ETL — data fetch → aggregate → JSON
│   ├── aggregate.py        # Main pipeline: filter, group, compute medians/history
│   ├── fetch_ppd.py        # Download HM Land Registry Price Paid Data CSVs
│   ├── fetch_boundaries.py # Download & simplify ONS postcode district boundaries
│   ├── generate_sample.py  # Produce realistic sample data (no 900 MB download needed)
│   ├── requirements.txt    # Python dependencies
│   └── tests/
│       ├── conftest.py
│       └── test_aggregate.py
│
├── public/
│   ├── prices.json         # Price data consumed by the frontend
│   └── gm-districts.geojson # GM postcode district boundaries (simplified GeoJSON)
│
├── index.html              # Single HTML page (sidebar + #map container)
├── vite.config.js          # Vite config (base: /mcr-price-heatmap/, port 3000)
├── vitest.config.js        # Vitest config (jsdom environment, src/**/*.test.js)
└── package.json            # Scripts: dev, build, preview, test, test:watch
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Vanilla JavaScript (ES modules), no framework |
| Map | Leaflet 1.9.4 |
| Bundler | Vite 5.4 |
| Frontend tests | Vitest 4 + jsdom |
| Data pipeline | Python 3 + pandas / numpy |
| Pipeline tests | pytest 8 |
| Deployment | GitHub Pages (gh-pages branch) |

There is no TypeScript, no React/Vue/Angular, and no CSS preprocessor. Keep it that way unless explicitly asked to migrate.

---

## Development Commands

### Frontend

```bash
npm install          # Install dependencies
npm run dev          # Dev server at http://localhost:3000
npm run build        # Production build → dist/
npm run preview      # Preview production build locally
npm run test         # Run Vitest tests once
npm run test:watch   # Vitest watch mode
```

### Python Pipeline

```bash
cd pipeline
pip install -r requirements.txt          # Core deps
pip install geopandas shapely            # Optional — for boundary simplification

python generate_sample.py                # Generate public/prices.json (dev, no download)
python fetch_ppd.py --years 3 --outdir ./raw   # Download 900 MB raw CSVs
python fetch_boundaries.py --out ../public/gm-districts.geojson
python aggregate.py --rawdir ./raw --out ../public/prices.json

pytest tests/                            # Run pipeline unit tests
```

> For development, always use `generate_sample.py` rather than downloading real data.

---

## Architecture & Key Conventions

### Frontend Module Responsibilities

Each module exports a small set of focused functions. There is no global mutable state aside from the Leaflet map instance (held in `map.js`).

| Module | Exports / Responsibility |
|---|---|
| `main.js` | `init()` — orchestrates parallel data fetch and wires everything together |
| `map.js` | `initMap()`, `loadData()`, `recolour()`, `fitToAffordable()`, `getDistrict()` |
| `controls.js` | `initControls()`, `calcMortgagePayment()`, `loadPrefs()` |
| `colours.js` | `BANDS` constant, `getBand(median, budget)`, `bandStyle(band)` |
| `popup.js` | `buildPopup(district, data, propType, budget)` |
| `sparkline.js` | `sparklineSVG(history, width, height)` |

### Colour Band Logic (`colours.js`)

Bands are determined by `median / budget` ratio:

| Band | Condition | Meaning |
|---|---|---|
| `green` | ratio ≤ 0.95 | Affordable |
| `amber` | 0.95 < ratio ≤ 1.15 | Stretch |
| `red` | ratio > 1.15 | Over budget |
| `grey` | null / 0 / NaN | No data |

### `prices.json` Schema

```json
{
  "generated": "2025-01-15",
  "window": "2022-01-01 to 2025-01-01",
  "districts": {
    "M20": {
      "all":       { "median": 340000, "count": 412, "delta12m": 2.1, "history": [/* 36 monthly values or null */] },
      "flat":      { "median": 215000, "count": 180, "delta12m": 1.4, "history": [...] },
      "terraced":  { "median": 285000, "count": 95,  "delta12m": 0.8, "history": [...] },
      "semi":      { "median": 370000, "count": 89,  "delta12m": 3.2, "history": [...] },
      "detached":  { "median": 510000, "count": 48,  "delta12m": 1.9, "history": [...] }
    }
  }
}
```

- `history` — 36 monthly median values (oldest first); individual entries may be `null` for sparse months
- `delta12m` — percentage change over the last 12 months (can be negative)
- `count` — number of transactions used in the median

### GeoJSON Property Normalisation (`map.js:getDistrict()`)

GeoJSON features may encode the district code under different property names. The lookup priority is:

1. `feature.properties.name`
2. `feature.properties.postcodes`
3. `feature.properties.PostDist`

Values are uppercased and whitespace-trimmed.

### Pipeline Filtering Rules (`aggregate.py`)

- **Geography**: Greater Manchester postcodes — M, SK, OL, BL, WN, and a subset of WA (WA3, WA11, WA12, WA14, WA15 only). The WA restriction avoids Warrington/Cheshire bleed.
- **New builds excluded by default** — they inflate medians in regeneration areas (Ancoats, NOMA).
- **PPD category B excluded by default** — repossessions and non-standard transactions.
- **Minimum sales threshold**: ≥20 for `all` types; ≥7 per individual type. Districts below threshold are omitted entirely.

---

## Testing

### Frontend Tests (Vitest)

Tests live alongside source files (`src/*.test.js`). Each test file corresponds to its module.

Key patterns:
- Leaflet is fully mocked in `map.test.js` via `vi.mock('leaflet')`
- PNG imports (marker icons) are stubbed
- jsdom provides a DOM environment; tests avoid relying on real browser APIs beyond what jsdom supplies

Coverage areas:
- `colours.test.js` — all four bands, boundary values at exactly 95% and 115%
- `controls.test.js` — `calcMortgagePayment()` including zero-rate edge case, `loadPrefs()` localStorage parsing
- `map.test.js` — `getDistrict()` property priority, case normalisation
- `popup.test.js` — HTML structure, Rightmove URL encoding, property type label mapping
- `sparkline.test.js` — SVG output, rising/falling colour, minimum data points (≥2 required)

### Python Tests (pytest)

```
pipeline/tests/test_aggregate.py
```

Covers: `extract_district()`, `filter_gm()`, `apply_filters()`, `make_history()`, `compute_delta12m()`, `aggregate_group()`, `build_output()`.

Uses `make_df()` fixture helper to create minimal DataFrames per test.

---

## Deployment

The app deploys to GitHub Pages from the `gh-pages` branch.

- Vite `base` is set to `/mcr-price-heatmap/` in `vite.config.js` — do not change this
- `public/` files are copied to `dist/` verbatim by Vite
- `dist/` is git-ignored; deployment copies it to the `gh-pages` branch

---

## What's Intentionally Absent

- No TypeScript — the project uses plain JS; do not add `.ts` files or `tsconfig.json` unless migrating the whole codebase
- No ESLint / Prettier configs — formatting is manual; do not add linter config files
- No CSS preprocessor (no Sass/Less) — use CSS custom properties
- No state management library — UI state is ephemeral JS variables + `localStorage`
- No backend / API server — entirely static; data is pre-built JSON

---

## Planned Features (Not Yet Implemented)

From `README.md`:
- Commute overlay — travel times from each district to Piccadilly (Google Distance Matrix API)
- Sector-level zoom (e.g. M20 2) as a drill-down layer
- Ofsted / school overlay (requires spatial join — ward boundaries don't align with postcode districts)

Do not implement these unless explicitly requested.
