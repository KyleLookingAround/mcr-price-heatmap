# Greater Manchester Property Price Heatmap

Interactive choropleth map of median residential sale prices across Greater Manchester
postcode districts, with budget-relative colouring, property type filtering, and a
mortgage calculator.

## Live demo

Deployed to GitHub Pages: [kylelookingaround.github.io/mcr-price-heatmap](https://kylelookingaround.github.io/mcr-price-heatmap)

## Stack

- **Frontend:** Vite + vanilla JS + Leaflet
- **Data:** Land Registry Price Paid Data (2022–2024) + ONS postcode district boundaries
- **Deployment:** GitHub Pages (static, zero server)

## Running locally

```bash
npm install
npm run dev        # → http://localhost:5173
```

## Regenerating data

See [pipeline/README.md](pipeline/README.md).

```bash
python3 pipeline/fetch_geojson.py   # boundaries (fast, ~10s)
python3 pipeline/build_prices.py    # price data (slow, downloads ~900MB)
```

The `public/` directory ships with pre-built data so you can run `npm run dev` without
running the pipeline.

## Features

- Budget slider and number input with debounced map recolouring
- Three affordability bands: green (≤95%), amber (95–115%), red (>115%) of budget
- Property type toggle: All / Detached / Semi / Terraced / Flat
- Click popup: median, sale count, 12-month change arrow, 36-month sparkline
- "Show affordable" — fits map bounds to green districts only
- Mortgage calculator: deposit + term + rate → monthly payment + max purchase price
- Budget and property type saved to localStorage

## Data decisions

- **New builds excluded** — resale market only; new builds inflate medians in regenerating areas (Ancoats, NOMA)
- **PPD category B excluded** — repossessions and non-market transfers
- **Districts with <20 sales** shown in grey (insufficient data for a reliable median)
- **WA postcodes excluded** — Warrington is not a GM authority
- **SK1–SK8 only** — Stockport borough; SK9+ are Cheshire East

## Deployment

```bash
npm run build
# push dist/ to gh-pages branch, or use GitHub Actions
```
