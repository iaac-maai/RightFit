// Booster sizing: what the building needs, whether the submitted set does it, and what fits. Calculated on the server.
import { $, api, esc, fmt } from '../lib.js';
import { chart, ceilTo, COLOR } from '../charts.js';

let el = null;   // kept for the life of the page, so the figures stay when the reviewer comes back

function verdictBanner(s, n) {
  const at = `${fmt(s.head_at_need_m, 0)} m available at ${fmt(n.peak_flow_m3h)} m³/h, ${fmt(n.required_head_m)} m needed`;
  if (s.verdict === 'fits') return `<div class="banner ok"><b>${esc(s.model)} fits</b><span>${at}</span></div>`;
  const issue = s.issues[0] || '';
  return `<div class="banner return"><b>${esc(s.model)}: ${esc(issue.split(':')[0])}</b>
    <span>${s.head_at_need_m == null ? esc(issue) : at}${s.issues.length > 1 ? `; ${esc(s.issues.slice(1).join('; '))}` : ''}</span></div>`;
}

function renderBooster(r, flats) {
  const n = r.need;
  const s = r.submitted;
  $('#b-result', el).innerHTML = `
    <p class="step-h">What the building needs</p>
    <div class="stats"><div><span class="lab">Peak flow</span><span class="typed">${fmt(n.peak_flow_m3h)}</span>m³/h</div><div><span class="lab">Head</span><span class="typed">${fmt(n.required_head_m)}</span>m</div></div>
    <p class="explain">${flats} flats, mixer taps: ${fmt(n.geometric_height_m)} m height + ${fmt(n.losses_m)} m losses + ${fmt(n.residual_m, 0)} m at the tap${n.mains_subtracted_m ? ` − ${fmt(n.mains_subtracted_m)} m from the mains` : ''}</p>
    <p class="cite">${esc(r.rules.join(', '))}, DIN 1988-300</p>
    ${s ? `<p class="step-h">The submitted set, on its real curve</p>${verdictBanner(s, n)}` : ''}
    ${r.unknown_submitted ? `<p class="step-h">The submitted set</p><p class="error">That set is not one of the ${r.sets} Lowara sets. Check the model name.</p>` : ''}`;
  const sug = r.suggest[0];
  const shown = Object.values(r.curves).flat();
  const lead = r.curves[s ? s.model : sug?.model] || shown;   // frame the chart on the submitted set's own range
  const xMax = Math.max(10, ceilTo(Math.max(...lead.map(([q]) => q), n.peak_flow_m3h * 2), 5));
  const yMax = ceilTo(Math.max(...shown.map(([, h]) => h), n.required_head_m), 25);
  const series = [];
  if (s) series.push({ pts: r.curves[s.model], color: COLOR.red, label: `${s.model} (submitted)`, at: [r.curves[s.model][0][0] + xMax * 0.02, r.curves[s.model][0][1] + yMax * 0.01] });
  if (sug) {
    const c = r.curves[sug.model].filter(([q]) => q <= xMax);
    series.push({ pts: c, color: COLOR.green, label: `${sug.model} (suggested)`, at: [xMax * 0.99, c[c.length - 1][1] - yMax * 0.09], anchor: 'end' });
  }
  const points = [{ x: n.peak_flow_m3h, y: n.required_head_m, color: COLOR.ink, label: `need ${fmt(n.peak_flow_m3h)} m³/h, ${fmt(n.required_head_m)} m`, dx: -14, dy: 34, anchor: 'middle',
    tip: `Need: ${fmt(n.peak_flow_m3h)} m³/h, ${fmt(n.required_head_m)} m` }];
  const guides = [];
  if (s && s.head_at_need_m != null) {
    points.unshift({ x: n.peak_flow_m3h, y: s.head_at_need_m, color: COLOR.red, r: 6, tip: `${s.model}: ${fmt(s.head_at_need_m)} m`, tipColor: COLOR.red });
    guides.push({ x1: n.peak_flow_m3h, y1: n.required_head_m, x2: n.peak_flow_m3h, y2: s.head_at_need_m, color: COLOR.red });
  }
  $('#b-chart', el).hidden = false;
  $('#b-chart', el).innerHTML = chart({ xMax, yMax, xStep: 5, yStep: 25, xLabel: 'Flow Q (m³/h)', yLabel: 'Head H (m)', series, points, guides,
    label: 'Pump curves of the submitted and suggested sets against the need' });
  const q = fmt(n.peak_flow_m3h);
  $('#b-suggest', el).innerHTML = `<div class="suggest"><p class="step-h">What fits, from ${r.sets} Lowara booster sets, lowest power first</p>
    ${r.suggest.length ? `<table><thead><tr><th>Set</th><th>Power</th><th>Head at ${q} m³/h</th><th>With one pump out</th><th>Verdict</th></tr></thead>
    <tbody>${r.suggest.map((x) => `<tr><td><b>${esc(x.model)}</b>, ${x.pumps} pumps</td><td class="typed">${fmt(x.kw_total)} kW</td>
      <td class="typed">${fmt(x.head_at_need_m)} m</td><td class="typed">${fmt(x.head_one_pump_out_m)} m</td><td><span class="chip pass">Fits, standby OK</span></td></tr>`).join('')}</tbody></table>`
    : '<p class="note">Nothing in the catalogue fits this building.</p>'}
    <p class="note">Curves from the Lowara GHV catalogue. An engineer confirms the choice.</p></div>`;
}

function build() {
  el = document.createElement('div');
  el.className = 'screen';
  el.innerHTML = `<div class="screen-head"><h1>Booster sizing</h1><p>What does this building need, will the submitted set do it, and what fits?</p></div>
    <div class="b-grid">
      <form class="inputs" id="booster-form" novalidate>
        <label><span class="lab">Flats</span><input type="text" name="flats" inputmode="numeric" autocomplete="off" placeholder="e.g. 40"></label>
        <label><span class="lab">Floors</span><input type="text" name="floors" inputmode="numeric" autocomplete="off" placeholder="e.g. 10"></label>
        <label><span class="lab">Supply</span><select name="supply"><option value="" selected disabled>Choose</option><option value="mains">Mains, pressure known</option><option value="tank">Break tank (CTE default)</option></select></label>
        <label class="mains" hidden><span class="lab">Mains pressure, m</span><input type="text" name="mains_m" inputmode="decimal" autocomplete="off" placeholder="e.g. 25"></label>
        <label><span class="lab">Submitted set</span><input type="text" name="submitted" list="sets" autocomplete="off" placeholder="model, e.g. GHV20/…"></label>
        <datalist id="sets"></datalist>
        <div><button class="btn p" type="submit">Check and suggest</button></div>
        <p class="error" id="booster-error" role="alert"></p>
      </form>
      <div class="b-result" id="b-result"></div>
      <figure class="chart" id="b-chart" hidden></figure>
    </div>
    <div id="b-suggest"></div>`;
  const form = $('#booster-form', el);
  form.supply.addEventListener('change', () => { $('.mains', form).hidden = form.supply.value !== 'mains'; });
  api('/api/pumps/sets', {}).then((sets) => {
    $('#sets', el).innerHTML = sets.map((s) => `<option value="${esc(s.model)}" label="${esc(`${s.maker}, ${s.pumps} pumps, ${fmt(s.kw)} kW`)}">`).join('');
  }).catch(() => {});
  form.addEventListener('submit', async (ev) => {
    ev.preventDefault();
    const err = $('#booster-error', el);
    err.textContent = '';
    const flats = parseInt(form.flats.value, 10);
    const floors = parseInt(form.floors.value, 10);
    const mains = form.supply.value === 'mains' ? parseFloat(form.mains_m.value) : 0;
    if (!(flats > 0) || !(floors > 0)) { err.textContent = 'Enter the number of flats and floors.'; return; }
    if (!form.supply.value) { err.textContent = 'Choose the supply.'; return; }
    if (form.supply.value === 'mains' && !(mains > 0)) { err.textContent = 'Enter the mains pressure in metres.'; return; }
    try {
      renderBooster(await api('/api/pumps/booster', { flats, floors, submitted: form.submitted.value.trim(), mains_m: mains }), flats);
    } catch (e) {
      err.textContent = e.message;
    }
  });
}

export function render(root) {
  if (!el) build();
  root.replaceChildren(el);
}
