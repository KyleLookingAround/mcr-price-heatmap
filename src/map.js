import L from 'leaflet'
import { getBand, bandStyle } from './colours.js'
import { buildPopup } from './popup.js'

// Fix Leaflet's marker icon paths when bundled with Vite
import markerIcon from 'leaflet/dist/images/marker-icon.png'
import markerIcon2x from 'leaflet/dist/images/marker-icon-2x.png'
import markerShadow from 'leaflet/dist/images/marker-shadow.png'
delete L.Icon.Default.prototype._getIconUrl
L.Icon.Default.mergeOptions({ iconUrl: markerIcon, iconRetinaUrl: markerIcon2x, shadowUrl: markerShadow })

const GM_CENTER = [53.48, -2.24]
const GM_ZOOM = 10

let mapInstance = null
let geojsonLayer = null
let pricesData = null
let currentBudget = 300000
let currentType = 'all'

export function initMap() {
  mapInstance = L.map('map', {
    center: GM_CENTER,
    zoom: GM_ZOOM,
    zoomControl: true,
  })

  L.tileLayer('https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png', {
    attribution: '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors © <a href="https://carto.com/">CARTO</a>',
    subdomains: 'abcd',
    maxZoom: 19,
  }).addTo(mapInstance)

  return mapInstance
}

export function loadData(prices, geojson) {
  pricesData = prices

  geojsonLayer = L.geoJSON(geojson, {
    style: feature => styleFeature(feature),
    onEachFeature: (feature, layer) => {
      layer.on({
        mouseover: e => highlightFeature(e),
        mouseout: e => resetHighlight(e),
        click: e => onDistrictClick(e, feature, layer),
      })
    },
  }).addTo(mapInstance)
}

export function getDistrict(feature) {
  // ONS GeoJSON uses 'postcodes' or 'name' — normalise
  return (
    feature.properties.name ||
    feature.properties.postcodes ||
    feature.properties.PostDist ||
    ''
  ).toUpperCase().trim()
}

function getMedian(district) {
  if (!pricesData?.districts?.[district]) return null
  const d = pricesData.districts[district]
  return d[currentType]?.median ?? d.all?.median ?? null
}

function styleFeature(feature) {
  const district = getDistrict(feature)
  const median = getMedian(district)
  const band = getBand(median, currentBudget)
  return bandStyle(band)
}

function highlightFeature(e) {
  const layer = e.target
  layer.setStyle({ weight: 2.5, fillOpacity: 0.85 })
  layer.bringToFront()
}

function resetHighlight(e) {
  geojsonLayer.resetStyle(e.target)
}

function onDistrictClick(e, feature, layer) {
  const district = getDistrict(feature)
  const data = pricesData?.districts?.[district]

  const content = data
    ? buildPopup(district, data, currentType, currentBudget)
    : `<div class="popup-content"><strong>${district}</strong><p>No price data available.</p></div>`

  layer.bindPopup(content, { maxWidth: 280 }).openPopup(e.latlng)
}

export function recolour(budget, propType) {
  currentBudget = budget
  currentType = propType
  if (geojsonLayer) {
    geojsonLayer.setStyle(feature => styleFeature(feature))
  }
}

/**
 * Fit map bounds to districts in the 'green' (affordable) band.
 */
export function fitToAffordable(budget, propType) {
  if (!geojsonLayer) return
  currentBudget = budget
  currentType = propType

  const affordableLayers = []
  geojsonLayer.eachLayer(layer => {
    const district = getDistrict(layer.feature)
    const median = getMedian(district)
    const band = getBand(median, budget)
    if (band === 'green') affordableLayers.push(layer)
  })

  if (affordableLayers.length === 0) {
    alert('No districts are affordable at this budget for the selected property type.')
    return
  }

  const group = L.featureGroup(affordableLayers)
  mapInstance.fitBounds(group.getBounds(), { padding: [20, 20] })
}
