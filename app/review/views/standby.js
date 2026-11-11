// Standby test: can the booster set of the uploaded package meet its duty with one pump out? Reads the package added
// on the Add a package screen.
import { esc, fmt, plural, shortName } from '../lib.js';
import { chart, ceilTo, COLOR } from '../charts.js';
import { analysis } from './add.js';

export function render(root) {
  const a = analysis();
  const r = a && a.standby;
  const head = (lede) => `<div class="screen-head"><h1>Standby test</h1><p>${lede}</p></div>`;
  if (!r || r.error) {
    root.innerHTML = `<div class="screen">${head('Is the second pump really a standby?')}
      ${r?.error ? `<p class="error" role="alert">${esc(r.error)}</p>`
    : `<p class="note">${a ? 'The package has no booster set data sheet with a duty point.' : 'This test reads the booster set\'s curve from a package added on the Add a package screen, not from the packages in the list.'}</p>
         ${a ? '' : '<p style="margin-top:12px"><a class="btn p" href="#/add">Add a package</a></p>'}`}</div>`;
    return;
  }
  const less = r.pumps - 1;
  const all = [...r.all, ...(r.less || [])];
  const xMax = ceilTo(Math.max(...all.map(([q]) => q)), 10);
  const yMin = Math.max(0, Math.floor(Math.min(...all.map(([, h]) => h)) / 5) * 5 - 5);
  const yMax = ceilTo(Math.max(...all.map(([, h]) => h)) + 1, 5);
  const at = (c, f, dx, dy) => [c[Math.floor(c.length * f)][0] + dx, c[Math.floor(c.length * f)][1] + dy];
  const series = [{ pts: r.all, color: COLOR.ink, label: `${r.pumps} pumps`, at: at(r.all, 0.7, 1, 1.5) }];
  if (r.less) series.push({ pts: r.less, color: COLOR.green, label: `${less} ${plural(less, 'pump')} alone`, at: at(r.less, 0.78, 1.5, 0) });
  const points = [{ x: r.duty_flow, y: r.duty_head, color: COLOR.red, tip: `Duty: ${fmt(r.duty_flow)} m³/h, ${fmt(r.duty_head)} m`, tipColor: COLOR.red }];
  if (r.head_less != null) points.push({ x: r.duty_flow, y: r.head_less, color: COLOR.green, r: 6, tip: `${less} ${plural(less, 'pump')} alone: ${fmt(r.duty_flow)} m³/h, ${fmt(r.head_less)} m`, tipColor: COLOR.green });
  const svg = chart({ xMax, yMin, yMax, xStep: 10, yStep: 5, xLabel: 'Flow Q (m³/h)', yLabel: 'Head H (m)', label: 'The set with all pumps and with one pump out, against the duty point',
    series, points, guides: [{ x1: r.duty_flow, y1: yMin, x2: r.duty_flow, y2: r.head_all ?? r.head_less ?? r.duty_head, color: COLOR.quiet }] });
  const verdict = r.standby
    ? `<div class="banner ok"><b>Real standby</b><span>${less} ${plural(less, 'pump')} alone meet${less === 1 ? 's' : ''} the duty, with ${r.margin_pct < 5 ? 'only ' : ''}${fmt(r.margin_pct)}% to spare</span></div>`
    : `<div class="banner return"><b>No real standby</b><span>with one pump out the set gives ${fmt(r.head_less)} m, ${fmt(-r.margin_m)} m short of the duty</span></div>`;
  root.innerHTML = `<div class="screen">${head(`${esc(shortName(r.model))} from the package, duty ${fmt(r.duty_flow, 0)} m³/h at ${fmt(r.duty_head, 0)} m`)}
    <div class="s-grid">
      <figure class="sheet"><p class="cap">${esc(r.file)}, page ${r.page}</p><img src="/upload/${r.token}/${r.page}.png" alt="Page ${r.page} of ${esc(r.file)}"></figure>
      <figure class="chart"><p class="cap">Curves read from the PDF's vector drawing, ${r.points} points</p>${svg}</figure>
      <div class="stats three"><div><span class="lab">Needed at duty</span><span class="typed bad">${fmt(r.duty_head, 0)}</span>m</div>
        <div><span class="lab">From ${less} ${plural(less, 'pump')} alone</span><span class="typed">${fmt(r.head_less)}</span>m</div>
        <div><span class="lab">Margin</span><span class="typed">${fmt(r.margin_m)}</span>m</div></div>
    </div>
    <div id="s-verdict">${verdict}</div></div>`;
}
