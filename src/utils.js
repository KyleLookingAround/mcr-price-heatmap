export function formatPrice(val) {
  if (val == null) return 'N/A';
  if (val >= 1_000_000) return `£${(val / 1_000_000).toFixed(2)}m`;
  if (val >= 1_000)     return `£${Math.round(val / 1_000)}k`;
  return `£${val}`;
}

export function trendArrow(delta) {
  if (delta == null) return { arrow: '—', label: 'N/A', cls: 'flat' };
  const pct = (delta * 100).toFixed(1);
  if (delta > 0.005)  return { arrow: '↑', label: `+${pct}%`, cls: 'up' };
  if (delta < -0.005) return { arrow: '↓', label: `${pct}%`,  cls: 'down' };
  return { arrow: '→', label: `${pct}%`, cls: 'flat' };
}

export function rightmoveUrl(district) {
  // Rightmove uses URL-encoded postcode search
  const encoded = encodeURIComponent(district);
  return `https://www.rightmove.co.uk/property-for-sale/search.html?searchLocation=${encoded}&useLocationIdentifier=true&locationIdentifier=POSTCODE%5E${encoded}`;
}
