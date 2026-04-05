/**
 * Render a tiny inline SVG sparkline from an array of monthly price values.
 * Returns an SVG string, or empty string if fewer than 2 data points.
 */
export function sparklineSVG(history, width = 120, height = 32) {
  const vals = (history || []).filter(v => v != null && v > 0)
  if (vals.length < 2) return ''

  const min = Math.min(...vals)
  const max = Math.max(...vals)
  const range = max - min || 1

  const pts = vals.map((v, i) => {
    const x = (i / (vals.length - 1)) * width
    const y = height - ((v - min) / range) * (height - 4) - 2
    return `${x.toFixed(1)},${y.toFixed(1)}`
  })

  const trend = vals[vals.length - 1] >= vals[0] ? '#4ade80' : '#f87171'

  return `<svg width="${width}" height="${height}" viewBox="0 0 ${width} ${height}"
    xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
    <polyline
      points="${pts.join(' ')}"
      fill="none"
      stroke="${trend}"
      stroke-width="1.5"
      stroke-linejoin="round"
      stroke-linecap="round"
    />
  </svg>`
}
