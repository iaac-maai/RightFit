// Charts drawn from the real curve points, for the booster and standby screens.
import { esc } from './lib.js';

export const COLOR = { ink: '#15191A', red: '#C4311E', green: '#0E3B2E', carbon: '#4A32B8', grid: '#DCE6DE', quiet: '#6B8073' };
export const ceilTo = (v, s) => Math.ceil(v / s) * s;

export function chart({ xMax, yMin = 0, yMax, xStep, yStep, xLabel, yLabel, series = [], points = [], guides = [], label }) {
  const W = 640, H = 430, L = 62, R = 26, T = 20, B = 56;
  const X = (x) => L + (x / xMax) * (W - L - R);
  const Y = (y) => T + (1 - (y - yMin) / (yMax - yMin)) * (H - T - B);
  let g = '';
  for (let x = 0; x <= xMax + 1e-9; x += xStep) {
    g += `<line x1="${X(x)}" x2="${X(x)}" y1="${T}" y2="${H - B}" stroke="${COLOR.grid}"/>`
      + `<text x="${X(x)}" y="${H - B + 26}" text-anchor="middle" font-size="16">${+x.toFixed(1)}</text>`;
  }
  for (let y = yMin; y <= yMax + 1e-9; y += yStep) {
    g += `<line x1="${L}" x2="${W - R}" y1="${Y(y)}" y2="${Y(y)}" stroke="${COLOR.grid}"/>`
      + `<text x="${L - 14}" y="${Y(y) + 5}" text-anchor="end" font-size="16">${+y.toFixed(1)}</text>`;
  }
  g += `<text x="${(L + W - R) / 2}" y="${H - 6}" text-anchor="middle" font-size="15">${esc(xLabel)}</text>`
    + `<text transform="translate(18 ${(T + H - B) / 2}) rotate(-90)" text-anchor="middle" font-size="15">${esc(yLabel)}</text>`;
  const path = (pts) => pts.filter(([x, y]) => x <= xMax && y >= yMin).map(([x, y], i) => `${i ? 'L' : 'M'}${X(x).toFixed(1)} ${Y(y).toFixed(1)}`).join(' ');
  guides.forEach((d) => {
    g += `<line x1="${X(d.x1)}" y1="${Y(d.y1)}" x2="${X(d.x2)}" y2="${Y(d.y2)}" stroke="${d.color}" stroke-width="2" stroke-dasharray="6 6"/>`;
  });
  series.forEach((s) => {
    g += `<path d="${path(s.pts)}" fill="none" stroke="${s.color}" stroke-width="3" stroke-linejoin="round" stroke-linecap="round"/>`;
    if (s.label) {
      const [x, y] = s.at;
      g += `<text x="${X(x)}" y="${Y(y)}" style="fill:${s.color}" font-size="17" font-weight="600" text-anchor="${s.anchor || 'start'}">${esc(s.label)}</text>`;
    }
  });
  points.forEach((p) => {
    let tip = '';
    if (p.tip) {   // a label that shows on hover
      const w = p.tip.length * 8.6 + 20;
      const tx = Math.min(X(p.x) + 12, W - R - w);
      tip = `<g class="tip"><rect x="${tx}" y="${Y(p.y) - 38}" width="${w}" height="28" rx="3" fill="${p.tipColor || COLOR.ink}"/>`
        + `<text x="${tx + 10}" y="${Y(p.y) - 19}" style="fill:#fff" font-size="15" font-weight="600">${esc(p.tip)}</text></g>`;
    }
    g += `<g class="pt" tabindex="0"><circle cx="${X(p.x)}" cy="${Y(p.y)}" r="${p.r || 7}" fill="${p.color}" stroke="#fff" stroke-width="2"/>`
      + `<circle cx="${X(p.x)}" cy="${Y(p.y)}" r="16" fill="transparent"/>${tip}</g>`;
    if (p.label) g += `<text x="${X(p.x) + (p.dx || 0)}" y="${Y(p.y) + (p.dy || 0)}" style="fill:${COLOR.ink}" font-size="16" font-weight="600" text-anchor="${p.anchor || 'start'}">${esc(p.label)}</text>`;
  });
  return `<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="${esc(label)}">${g}</svg>`;
}
