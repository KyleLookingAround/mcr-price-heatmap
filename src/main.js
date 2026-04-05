import 'leaflet/dist/leaflet.css'
import './style.css'
import { initMap, loadData, recolour, fitToAffordable } from './map.js'
import { initControls } from './controls.js'

const BASE = import.meta.env.BASE_URL

async function fetchJSON(path) {
  const res = await fetch(BASE + path)
  if (!res.ok) throw new Error(`Failed to load ${path}: ${res.status}`)
  return res.json()
}

async function main() {
  const loading = document.getElementById('loading')

  initMap()

  try {
    const [prices, geojson] = await Promise.all([
      fetchJSON('prices.json'),
      fetchJSON('gm-districts.geojson'),
    ])

    loadData(prices, geojson)

    // Show data date in footer
    const dateEl = document.getElementById('data-date')
    if (dateEl && prices.generated) {
      dateEl.textContent = `Data generated: ${prices.generated}`
    }

    const { getBudget, getType } = initControls(
      (budget, propType) => recolour(budget, propType),
      (budget, propType) => fitToAffordable(budget, propType),
    )

    // Initial render with persisted or default values
    recolour(getBudget(), getType())
  } catch (err) {
    console.error(err)
    loading.innerHTML = `<p class="error">Failed to load data.<br><small>${err.message}</small></p>`
    return
  }

  loading.style.display = 'none'
}

main()
