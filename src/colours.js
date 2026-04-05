/**
 * Colour bands relative to budget:
 *   green  — median ≤ 95 % of budget (affordable)
 *   amber  — 95–115 % (stretch)
 *   red    — > 115 % (over budget)
 *   grey   — no data / insufficient sales
 */

export const BANDS = {
  green: { fill: '#4ade80', stroke: '#16a34a', label: 'Affordable' },
  amber: { fill: '#fbbf24', stroke: '#d97706', label: 'Stretch' },
  red:   { fill: '#f87171', stroke: '#dc2626', label: 'Over budget' },
  grey:  { fill: '#d1d5db', stroke: '#9ca3af', label: 'No data' },
}

/**
 * @param {number|null} median  — district median price for selected type
 * @param {number}      budget  — user's budget
 * @returns {'green'|'amber'|'red'|'grey'}
 */
export function getBand(median, budget) {
  if (!median || median <= 0) return 'grey'
  const ratio = median / budget
  if (ratio <= 0.95) return 'green'
  if (ratio <= 1.15) return 'amber'
  return 'red'
}

export function bandStyle(band) {
  const b = BANDS[band]
  return {
    fillColor: b.fill,
    color: b.stroke,
    weight: 1,
    fillOpacity: 0.65,
  }
}
