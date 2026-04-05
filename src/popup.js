import { sparklineSVG } from './sparkline.js'

const fmt = new Intl.NumberFormat('en-GB', { style: 'currency', currency: 'GBP', maximumFractionDigits: 0 })
const fmtK = v => v >= 1000 ? `£${(v / 1000).toFixed(0)}k` : fmt.format(v)

function trendArrow(delta12m) {
  if (delta12m == null) return ''
  if (delta12m > 2) return `<span class="trend up" title="${delta12m.toFixed(1)}% over 12m">▲ ${delta12m.toFixed(1)}%</span>`
  if (delta12m < -2) return `<span class="trend down" title="${delta12m.toFixed(1)}% over 12m">▼ ${Math.abs(delta12m).toFixed(1)}%</span>`
  return `<span class="trend flat" title="${delta12m.toFixed(1)}% over 12m">→ ${delta12m.toFixed(1)}%</span>`
}

/**
 * Build the HTML content for a district popup.
 * @param {string} district  — e.g. "M20"
 * @param {object} data      — district data from prices.json
 * @param {string} propType  — selected property type key
 * @param {number} budget    — user's current budget
 */
export function buildPopup(district, data, propType, budget) {
  const typeData = data[propType] || data.all
  const median = typeData?.median
  const count = typeData?.count
  const delta = typeData?.delta12m
  const history = typeData?.history || data.all?.history

  const medianStr = median ? fmt.format(median) : 'No data'
  const countStr = count ? `${count} sales` : '—'
  const spark = sparklineSVG(history)

  const pctOfBudget = median ? ((median / budget) * 100).toFixed(0) : null
  const pctLabel = pctOfBudget
    ? `<span class="pct-label">${pctOfBudget}% of your budget</span>`
    : ''

  const rmUrl = `https://www.rightmove.co.uk/property-for-sale/find.html?searchType=SALE&locationIdentifier=POSTCODE%5E${district}&maxPrice=${Math.round(budget)}`

  const typeLabelMap = {
    all: 'All types', flat: 'Flats', terraced: 'Terraced',
    semi: 'Semi-detached', detached: 'Detached',
  }
  const typeLabel = typeLabelMap[propType] || propType

  return `
    <div class="popup-content">
      <div class="popup-header">
        <strong class="district-code">${district}</strong>
        <span class="type-label">${typeLabel}</span>
      </div>
      <table class="popup-stats">
        <tr>
          <td>Median price</td>
          <td><strong>${medianStr}</strong> ${pctLabel}</td>
        </tr>
        <tr>
          <td>Sales (3yr)</td>
          <td>${countStr}</td>
        </tr>
        <tr>
          <td>12m trend</td>
          <td>${trendArrow(delta)}</td>
        </tr>
      </table>
      ${spark ? `<div class="popup-spark">${spark}<span class="spark-label">36-month price trend</span></div>` : ''}
      <a class="rightmove-link" href="${rmUrl}" target="_blank" rel="noopener">
        Search on Rightmove →
      </a>
    </div>
  `
}
