import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import { initMortgageCalc } from './mortgage.js';
import { drawSparkline } from './sparkline.js';
import { formatPrice, trendArrow, rightmoveUrl } from './utils.js';

// ── State ─────────────────────────────────────────────────────────────────────
const state = {
  budget: parseInt(localStorage.getItem('budget') || '300000', 10),
  propType: localStorage.getItem('propType') || 'all',
  prices: null,
  geojson: null,
  layer: null,
};

// ── Map setup ─────────────────────────────────────────────────────────────────
const map = L.map('map', {
  center: [53.48, -2.24],
  zoom: 10,
  zoomControl: true,
  attributionControl: true,
});

L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_matter/{z}/{x}/{y}{r}.png', {
  attribution: '&copy; OpenStreetMap contributors &copy; CARTO',
  subdomains: 'abcd',
  maxZoom: 19,
}).addTo(map);

// ── Colour logic ──────────────────────────────────────────────────────────────
function getBand(median, budget) {
  if (median == null) return 'grey';
  const ratio = median / budget;
  if (ratio <= 0.95) return 'green';
  if (ratio <= 1.15) return 'amber';
  return 'red';
}

const BAND_STYLE = {
  green: { fillColor: 'rgba(34,197,94,0.45)',   color: '#22c55e', weight: 1.5 },
  amber: { fillColor: 'rgba(245,158,11,0.45)',  color: '#f59e0b', weight: 1.5 },
  red:   { fillColor: 'rgba(239,68,68,0.45)',   color: '#ef4444', weight: 1.5 },
  grey:  { fillColor: 'rgba(107,114,128,0.25)', color: '#6b7280', weight: 1 },
};

function styleFeature(feature) {
  const district = feature.properties.name;
  const data = getDistrictData(district);
  const band = data ? getBand(data.median, state.budget) : 'grey';
  return { ...BAND_STYLE[band], fillOpacity: 1 };
}

function getDistrictData(district) {
  if (!state.prices) return null;
  const row = state.prices[district];
  if (!row) return null;
  if (state.propType === 'all') return row.all ?? null;
  return row[state.propType] ?? null;
}

// ── GeoJSON layer ─────────────────────────────────────────────────────────────
function buildLayer() {
  if (state.layer) {
    state.layer.remove();
    state.layer = null;
  }
  if (!state.geojson) return;

  state.layer = L.geoJSON(state.geojson, {
    style: styleFeature,
    onEachFeature(feature, layer) {
      layer.on({
        mouseover(e) {
          const l = e.target;
          l.setStyle({ weight: 3, fillOpacity: 0.75 });
          l.bringToFront();
        },
        mouseout(e) {
          state.layer.resetStyle(e.target);
        },
        click(e) {
          map.fitBounds(e.target.getBounds(), { maxZoom: 13 });
          showPopup(feature, e.target.getBounds().getCenter());
        },
      });
    },
  }).addTo(map);
}

function recolour() {
  if (!state.layer) return;
  state.layer.setStyle(styleFeature);
}

// ── Popup ─────────────────────────────────────────────────────────────────────
function showPopup(feature, latlng) {
  const district = feature.properties.name;
  const data = getDistrictData(district);

  let content;
  if (!data) {
    content = `
      <div class="popup-inner">
        <h3>${district}</h3>
        <p class="popup-label">Insufficient data</p>
      </div>`;
  } else {
    const trend = trendArrow(data.delta12m);
    const sparkId = `spark-${district.replace(/\s/g, '')}`;
    content = `
      <div class="popup-inner">
        <h3>${district}</h3>
        <p class="popup-label">${feature.properties.label || ''}</p>
        <div class="popup-stat">
          <span>Median price</span>
          <strong>${formatPrice(data.median)}</strong>
        </div>
        <div class="popup-stat">
          <span>Sales (3y)</span>
          <strong>${data.count.toLocaleString()}</strong>
        </div>
        <div class="popup-stat">
          <span>12-month change</span>
          <strong class="popup-trend ${trend.cls}">${trend.arrow} ${trend.label}</strong>
        </div>
        <div class="popup-sparkline">
          <canvas id="${sparkId}" class="sparkline-canvas" width="220" height="40"></canvas>
        </div>
        <div class="popup-actions">
          <a href="${rightmoveUrl(district)}" target="_blank" rel="noopener noreferrer">
            Search on Rightmove →
          </a>
        </div>
      </div>`;
  }

  const popup = L.popup({ maxWidth: 260, className: 'heatmap-popup' })
    .setLatLng(latlng)
    .setContent(content)
    .openOn(map);

  // draw sparkline after popup is in DOM
  if (data?.monthly) {
    popup.once('add', () => {
      const sparkId = `spark-${district.replace(/\s/g, '')}`;
      const canvas = document.getElementById(sparkId);
      if (canvas) drawSparkline(canvas, data.monthly);
    });
    // leaflet fires 'add' synchronously in some versions; also try immediately
    requestAnimationFrame(() => {
      const sparkId = `spark-${district.replace(/\s/g, '')}`;
      const canvas = document.getElementById(sparkId);
      if (canvas && !canvas.dataset.drawn) drawSparkline(canvas, data.monthly);
    });
  }
}

// ── Fit to affordable ─────────────────────────────────────────────────────────
function fitAffordable() {
  if (!state.layer || !state.prices) return;
  const bounds = L.latLngBounds([]);
  state.layer.eachLayer((layer) => {
    const district = layer.feature.properties.name;
    const data = getDistrictData(district);
    const band = data ? getBand(data.median, state.budget) : 'grey';
    if (band === 'green') bounds.extend(layer.getBounds());
  });
  if (bounds.isValid()) map.fitBounds(bounds, { padding: [20, 20] });
}

// ── Controls ──────────────────────────────────────────────────────────────────
const budgetInput  = document.getElementById('budget-input');
const budgetSlider = document.getElementById('budget-slider');

function setBudget(val) {
  const v = Math.max(50000, Math.min(2000000, Number(val)));
  state.budget = v;
  budgetInput.value  = v;
  budgetSlider.value = v;
  localStorage.setItem('budget', v);
  scheduleRecolour();
  updateMortgage();
}

budgetInput.value  = state.budget;
budgetSlider.value = state.budget;

let recolourTimer = null;
function scheduleRecolour() {
  clearTimeout(recolourTimer);
  recolourTimer = setTimeout(recolour, 50);
}

budgetInput.addEventListener('input',  (e) => setBudget(e.target.value));
budgetSlider.addEventListener('input', (e) => setBudget(e.target.value));

document.getElementById('prop-type-toggle').addEventListener('click', (e) => {
  const btn = e.target.closest('.type-btn');
  if (!btn) return;
  document.querySelectorAll('.type-btn').forEach((b) => b.classList.remove('active'));
  btn.classList.add('active');
  state.propType = btn.dataset.type;
  localStorage.setItem('propType', state.propType);
  recolour();
});

// Restore saved prop type button state
document.querySelectorAll('.type-btn').forEach((b) => {
  if (b.dataset.type === state.propType) b.classList.add('active');
  else b.classList.remove('active');
});

document.getElementById('fit-affordable').addEventListener('click', fitAffordable);

// ── Mortgage calculator ───────────────────────────────────────────────────────
function updateMortgage() {
  const deposit = parseFloat(document.getElementById('deposit').value) || 0;
  const term    = parseFloat(document.getElementById('term').value)    || 25;
  const rate    = parseFloat(document.getElementById('rate').value)    || 4.5;
  const maxBudget = calcMaxBudget(deposit, term, rate);
  const result = document.getElementById('mortgage-result');
  result.innerHTML = `
    <div>Monthly repayment on <strong>${formatPrice(state.budget)}</strong></div>
    <div>${formatPrice(monthlyPayment(state.budget - deposit, rate, term))}/mo</div>
    <div style="margin-top:6px;font-size:11px;color:#64748b">Max purchase with your deposit:</div>
    <div class="mortgage-budget">${formatPrice(maxBudget + deposit)}</div>
  `;
}

function monthlyPayment(principal, annualRate, years) {
  if (principal <= 0) return 0;
  const r = annualRate / 100 / 12;
  const n = years * 12;
  if (r === 0) return principal / n;
  return principal * r * Math.pow(1 + r, n) / (Math.pow(1 + r, n) - 1);
}

function calcMaxBudget(deposit, years, annualRate) {
  // Approx max loan assuming max monthly = 35% of typical GM salary (~£35k)
  const maxMonthly = 35000 * 0.35 / 12;
  const r = annualRate / 100 / 12;
  const n = years * 12;
  if (r === 0) return maxMonthly * n;
  return maxMonthly * (Math.pow(1 + r, n) - 1) / (r * Math.pow(1 + r, n));
}

initMortgageCalc(updateMortgage);
updateMortgage();

// ── Data loading ──────────────────────────────────────────────────────────────
async function loadData() {
  const [pricesRes, geojsonRes] = await Promise.all([
    fetch('/prices.json'),
    fetch('/gm-districts.geojson'),
  ]);

  if (!pricesRes.ok) throw new Error(`prices.json: ${pricesRes.status}`);
  if (!geojsonRes.ok) throw new Error(`gm-districts.geojson: ${geojsonRes.status}`);

  state.prices = await pricesRes.json();
  state.geojson = await geojsonRes.json();
  buildLayer();
}

loadData().catch((err) => {
  console.warn('Failed to load data:', err);
  // Show placeholder GeoJSON if data files not yet generated
  fetch('/gm-districts.geojson')
    .then((r) => r.ok ? r.json() : null)
    .then((gj) => {
      if (gj) { state.geojson = gj; buildLayer(); }
    })
    .catch(() => {});
});
