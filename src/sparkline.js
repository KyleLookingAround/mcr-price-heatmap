/**
 * Draws a simple line sparkline on a canvas element.
 * @param {HTMLCanvasElement} canvas
 * @param {number[]} values - array of monthly median prices (oldest → newest)
 */
export function drawSparkline(canvas, values) {
  if (!values || values.length < 2) return;
  canvas.dataset.drawn = '1';

  const dpr    = window.devicePixelRatio || 1;
  const W      = canvas.offsetWidth  || 220;
  const H      = canvas.offsetHeight || 40;
  canvas.width  = W * dpr;
  canvas.height = H * dpr;

  const ctx = canvas.getContext('2d');
  ctx.scale(dpr, dpr);

  const min  = Math.min(...values);
  const max  = Math.max(...values);
  const span = max - min || 1;
  const pad  = 4;

  const x = (i) => pad + (i / (values.length - 1)) * (W - pad * 2);
  const y = (v) => H - pad - ((v - min) / span) * (H - pad * 2);

  // Gradient fill
  const grad = ctx.createLinearGradient(0, 0, 0, H);
  grad.addColorStop(0, 'rgba(99,102,241,0.4)');
  grad.addColorStop(1, 'rgba(99,102,241,0)');

  ctx.beginPath();
  ctx.moveTo(x(0), y(values[0]));
  for (let i = 1; i < values.length; i++) {
    ctx.lineTo(x(i), y(values[i]));
  }
  ctx.lineTo(x(values.length - 1), H);
  ctx.lineTo(x(0), H);
  ctx.closePath();
  ctx.fillStyle = grad;
  ctx.fill();

  // Line
  ctx.beginPath();
  ctx.moveTo(x(0), y(values[0]));
  for (let i = 1; i < values.length; i++) {
    ctx.lineTo(x(i), y(values[i]));
  }
  ctx.strokeStyle = '#6366f1';
  ctx.lineWidth   = 1.5;
  ctx.lineJoin    = 'round';
  ctx.stroke();

  // Dot at latest value
  const lx = x(values.length - 1);
  const ly = y(values[values.length - 1]);
  ctx.beginPath();
  ctx.arc(lx, ly, 3, 0, Math.PI * 2);
  ctx.fillStyle = '#818cf8';
  ctx.fill();
}
