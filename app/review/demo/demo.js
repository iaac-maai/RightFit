'use strict';
// RightFit pump demo. The server (app/pump_demo.py) reads the uploaded files and runs the dataset kit's
// deterministic checks on what they say; this page uploads the files and shows the results.

const $ = (sel, root = document) => root.querySelector(sel);
const esc = (s) => String(s ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const fmt = (n, d = 1) => (n == null ? 'n/a' : Number(n).toFixed(d));
const PKG = 'P01';   // the pump package kept on this laptop, for the "use the package already on this laptop" link
const state = { entries: [], analysis: null, standbyShown: null, busy: false };
const TITLES = { check: 'Package check', booster: 'Size the booster', standby: 'Standby test' };

async function api(path, body, headers) {
  let res;
  try {
    res = await fetch(path, { method: 'POST', headers: headers || { 'Content-Type': 'application/json' },
      body: headers ? body : JSON.stringify(body || {}) });
  } catch {
    throw new Error('The RightFit server is not answering. Start it with: python app/review_server.py');
  }
  const data = await res.json().catch(() => ({}));
  if (!res.ok || data.error) throw new Error(data.error || `The server answered ${res.status}.`);
  return data;
}

// Display names as the data sheets print them: drop the order code after the product name, soften all-caps names.
const shortName = (model) => model.replace(/\s+U\d\s+[A-Z](-[A-Z])+$/, '').replace(/\b([A-Z])([A-Z]{3,})\b/g, (_, a, b) => a + b.toLowerCase());
const kindOf = (p) => (p.category === 'booster_set' ? 'booster set'
  : (p.pump_type || '').startsWith('submersible_') ? p.pump_type.split('_')[1] : p.category.replace('_', ' '));

// ------------------------------------------------------------------ tabs
const TABS = ['check', 'booster', 'standby'];
function show(tab) {
  document.querySelectorAll('[role="tab"]').forEach((b) => {
    const on = b.dataset.tab === tab;
    b.setAttribute('aria-selected', on);
    b.tabIndex = on ? 0 : -1;
  });
  document.querySelectorAll('.view').forEach((v) => { v.hidden = v.id !== tab; });
  document.title = `RightFit · ${TITLES[tab]}`;
  if (tab === 'standby') renderStandby();
  history.replaceState(null, '', `#${tab}`);
}
document.querySelector('.tabs').addEventListener('click', (ev) => {
  const b = ev.target.closest('[role="tab"]');
  if (b) show(b.dataset.tab);
});
document.querySelector('.tabs').addEventListener('keydown', (ev) => {
  if (!['ArrowRight', 'ArrowLeft'].includes(ev.key)) return;
  const now = TABS.indexOf(document.querySelector('[role="tab"][aria-selected="true"]').dataset.tab);
  const next = TABS[(now + (ev.key === 'ArrowRight' ? 1 : 2)) % 3];
  show(next);
  $(`#tab-${next}`).focus();
});

// ------------------------------------------------------------------ 1 · package check
// The package is every file added so far. Files added later are read on their own, then the whole package is checked again.
function pkgBar(n) {
  return `<div class="pkg"><p class="cap">${n} file${n === 1 ? '' : 's'} in this package</p>
    <button class="add" type="button" data-pick>+ Add documents</button></div>`;
}

function failed(e) {
  if (state.analysis) renderCheck(state.analysis);   // keep the last result on screen
  else $('#check-main').insertAdjacentHTML('afterbegin', pkgBar(state.entries.length));
  $('.pkg').insertAdjacentHTML('afterend', `<p class="error" role="alert">${esc(e.message)}</p>`);
}

function listFiles() {
  $('#viewer').hidden = true;
  $('#check-main').innerHTML = `<ul class="files" id="flist"></ul>
    <div class="progress" id="progress" hidden><p class="label"><span class="spin" aria-hidden="true"></span><span id="plabel">Reading the package</span></p>
      <div class="track"><div class="fill" id="pfill"></div></div></div>`;
  state.entries.forEach(addFile);   // the files already in the package stay listed
}

function addFile(e, i) {
  $('#flist').insertAdjacentHTML('beforeend', `<li id="f${i}" style="animation-delay:${i * 60}ms">
    <span class="pdf">${e.pages == null ? 'FILE' : 'PDF'}</span><span class="name">${esc(e.name)}</span>
    <span class="pages">${e.pages == null ? 'not a PDF' : `${e.pages} pages${e.ocr ? ' · OCR' : ''}`}</span>
    <span class="bar-in"${e.done ? ' style="width:100%"' : ''}></span></li>`);
}

function include(e) {   // a file joins the package once, however often it is added
  if (state.entries.some((x) => x.token === e.token)) return;
  addFile(e, state.entries.length);
  state.entries.push(e);
}

// Every page is read on the server as the counter moves: its text, or OCR when the page is a scan.
async function readPages(entries) {
  const total = entries.reduce((a, e) => a + (e.pages || 0), 0);
  let done = 0;
  $('#progress').hidden = false;
  $('#plabel').textContent = `Reading page 0 of ${total}`;
  for (const e of entries) {
    const row = $(`#f${state.entries.indexOf(e)}`);
    for (let p = 1; p <= (e.pages || 0); p++) {
      $('#plabel').textContent = `Reading page ${done + 1} of ${total}${e.ocr ? ' · OCR of a scanned page' : ''}`;
      const r = await api('/api/extract', { token: e.token, page: p });
      e.ocr = e.ocr || r.read === 'ocr';
      done += 1;
      $('.bar-in', row).style.width = `${(p / e.pages) * 100}%`;
      $('#pfill').style.width = `${(done / total) * 100}%`;
    }
    if (e.ocr) $('.pages', row).textContent = `${e.pages} pages · OCR`;
    e.done = true;
  }
  $('#plabel').textContent = `Read ${done} pages · matching pumps to declarations`;
}

async function addToPackage(adding) {
  if (state.busy) return;
  state.busy = true;
  try {
    listFiles();
    await adding();
    await readPages(state.entries.filter((e) => !e.done));
    const c = await api('/api/analyse', { tokens: state.entries.map((e) => e.token) });
    $('#progress').classList.add('done');
    state.analysis = c;
    state.standbyShown = null;
    renderCheck(c);
  } catch (e) {
    failed(e);
  } finally {
    state.busy = false;
  }
}

async function upload(fileList) {
  const files = [...fileList];
  if (files.length) await addToPackage(async () => {
    for (const f of files) include(await api('/api/upload', f, { 'X-File-Name': encodeURIComponent(f.name) }));
  });
}

function useLocal() {   // the original files on this laptop, as if they were uploaded
  return addToPackage(async () => (await api('/api/load-local', { package: PKG })).forEach(include));
}

function chip(rule) {
  if (!rule) return '';
  const title = rule.detail ? ` title="${esc(rule.detail)}"` : '';
  if (rule.verdict === 'pass') return `<span class="chip pass"${title}>${rule.label ? `${rule.file ? 'Named' : 'Pass'} · ${esc(rule.label)}` : 'Pass'}</span>`;
  if (rule.verdict === 'fail') return `<span class="chip fail"${title}>${rule.label ? `Fail · ${esc(rule.label)}` : 'Not found'}</span>`;
  if (rule.verdict === 'n/a') return `<span class="chip na"${title}>N/A · ${esc(rule.label)}</span>`;
  return `<span class="chip unknown"${title}>? · ${esc(rule.label)}</span>`;
}

function renderCheck(c) {
  $('#check-title').textContent = c.form ? `MAF ${c.form} · pump package` : 'Pump package';
  const head = pkgBar(c.files.length);
  if (!c.pumps.length) {
    $('#check-main').innerHTML = `${head}<p class="note">No pump data sheet was found among these files, so there is nothing to check against the declarations.</p>`;
    return;
  }
  const ok = !c.missing;
  const count = (n, label, i, bad) => `<div class="count${bad ? ' bad' : ''}" style="animation-delay:${200 + i * 90}ms"><b>${n}</b><span>${label}</span></div>`;
  const also = [
    ...c.unused.map((d) => `<p class="also"><b>Also:</b> the ${esc(d.names.join(', '))} declaration in the package names <b>no submitted pump</b>${d.read === 'OCR' ? ' (read by OCR from a scan)' : ''}.</p>`),
    ...c.unread.map((d) => `<p class="also"><b>Not read:</b> ${esc(d.file || d.name)}${d.names ? ' names no products RightFit can find' : ' has no text, even by OCR'}. Check it by eye.</p>`),
  ].join('');
  $('#check-main').innerHTML = `${head}
    <div class="banner ${ok ? 'ok' : 'return'}"><b>${ok ? 'Pass' : 'Return'}</b>
      <span>${ok ? 'every pump has a declaration that names it' : `${c.missing} of ${c.pumps.length} pumps have no declaration that names them`}</span></div>
    <div class="counts">${count(c.pages, 'pages read', 0)}${count(c.pumps.length, 'pumps found', 1)}${count(c.declarations.length, 'declarations', 2)}${count(c.missing, 'pumps not covered', 3, c.missing > 0)}</div>
    <p class="rule" title="${esc(c.rule.quote)}">Rule ${esc(c.rule.id)} · ${esc(c.rule.source)}: ${esc(c.rule.rule)}</p>
    <table class="pumps"><thead><tr><th>Pump</th><th>Declaration</th><th>Efficiency (MEI)</th><th>Motor (IE)</th></tr></thead>
    <tbody>${c.pumps.map((p, i) => `<tr tabindex="0" data-i="${i}" aria-selected="false" style="animation-delay:${600 + i * 160}ms">
      <td><span class="model" title="${esc(p.model)}">${esc(shortName(p.model))}</span><span class="sub">${esc(kindOf(p))} · data sheet p1</span></td>
      <td>${chip(p.rules['CE-01'])}</td><td>${chip(p.rules['PUMP-MEI'])}</td><td>${chip(p.rules['MOTOR-IE'])}</td></tr>`).join('')}</tbody></table>
    ${also}
    <p class="note">N/A = the EU efficiency rules do not apply to this pump type, so the form is not returned for them.</p>`;
  $('#viewer-body').innerHTML = '<p class="empty">Select a pump to open<br>its source page</p>';
  $('#viewer').hidden = false;
}

function selectPump(i) {
  const c = state.analysis;
  const p = c.pumps[i];
  document.querySelectorAll('.pumps tbody tr').forEach((tr) => tr.setAttribute('aria-selected', tr.dataset.i === String(i)));
  const ce = p.rules['CE-01'];
  const decl = ce.verdict === 'pass' ? c.declarations.find((d) => d.file === ce.file) : null;
  const token = decl ? decl.token : p.token;
  const page = decl ? decl.page || 1 : 1;
  const file = decl ? decl.file : p.source_file;
  $('#viewer-body').innerHTML = `<div><div class="doc-head"><p class="head">${esc(file)} · p${page}</p>
    <p class="say ${decl ? 'pass' : 'fail'}">${decl ? `Names: ${esc(decl.names.join(', '))}` : 'No declaration in the package names this model'}</p></div>
    <iframe title="${esc(file)}, page ${page}" src="/upload/${token}#page=${page}&toolbar=0&navpanes=0&view=FitH"></iframe>
    <a class="open" href="/upload/${token}#page=${page}" target="_blank" rel="noopener">Open the PDF in a new tab</a></div>`;
}

$('#check-main').addEventListener('click', (ev) => {
  const tr = ev.target.closest('.pumps tbody tr');
  if (tr) selectPump(Number(tr.dataset.i));
  if (ev.target.closest('[data-pick]')) $('#files').click();
});
$('#check-main').addEventListener('keydown', (ev) => {
  const tr = ev.target.closest('.pumps tbody tr');
  if (tr && (ev.key === 'Enter' || ev.key === ' ')) { ev.preventDefault(); selectPump(Number(tr.dataset.i)); }
});
$('#files').addEventListener('change', (ev) => { upload(ev.target.files); ev.target.value = ''; });   // so the same file can be picked again
$('#local').addEventListener('click', useLocal);
// Files can be dropped anywhere on this step, before or after the first upload.
const zone = $('#check');
const target = () => $('#drop') || $('#check-main');
['dragenter', 'dragover'].forEach((t) => zone.addEventListener(t, (ev) => { ev.preventDefault(); if (!state.busy) target().classList.add('over'); }));
['dragleave', 'drop'].forEach((t) => zone.addEventListener(t, () => target().classList.remove('over')));
zone.addEventListener('drop', (ev) => { ev.preventDefault(); upload(ev.dataTransfer.files); });
['dragover', 'drop'].forEach((t) => window.addEventListener(t, (ev) => ev.preventDefault()));   // a file dropped beside the page must not replace it

// ------------------------------------------------------------------ charts drawn from the real curve points
function chart({ xMax, yMin = 0, yMax, xStep, yStep, xLabel, yLabel, series = [], points = [], guides = [], label }) {
  const W = 640, H = 430, L = 62, R = 26, T = 20, B = 56;
  const X = (x) => L + (x / xMax) * (W - L - R);
  const Y = (y) => T + (1 - (y - yMin) / (yMax - yMin)) * (H - T - B);
  let g = '';
  for (let x = 0; x <= xMax + 1e-9; x += xStep) {
    g += `<line x1="${X(x)}" x2="${X(x)}" y1="${T}" y2="${H - B}" stroke="#E7E0D3"/>`
      + `<text x="${X(x)}" y="${H - B + 26}" text-anchor="middle" font-size="16">${+x.toFixed(1)}</text>`;
  }
  for (let y = yMin; y <= yMax + 1e-9; y += yStep) {
    g += `<line x1="${L}" x2="${W - R}" y1="${Y(y)}" y2="${Y(y)}" stroke="#E7E0D3"/>`
      + `<text x="${L - 14}" y="${Y(y) + 5}" text-anchor="end" font-size="16">${+y.toFixed(1)}</text>`;
  }
  g += `<text class="ax" x="${(L + W - R) / 2}" y="${H - 6}" text-anchor="middle">${esc(xLabel)}</text>`
    + `<text class="ax" transform="translate(18 ${(T + H - B) / 2}) rotate(-90)" text-anchor="middle">${esc(yLabel)}</text>`;
  const path = (pts) => pts.filter(([x, y]) => x <= xMax && y >= yMin).map(([x, y], i) => `${i ? 'L' : 'M'}${X(x).toFixed(1)} ${Y(y).toFixed(1)}`).join(' ');
  guides.forEach((d) => {
    g += `<line class="pop" style="animation-delay:${d.delay || 0}ms" x1="${X(d.x1)}" y1="${Y(d.y1)}" x2="${X(d.x2)}" y2="${Y(d.y2)}" stroke="${d.color}" stroke-width="2" stroke-dasharray="6 6"/>`;
  });
  series.forEach((s) => {
    g += `<path class="draw" style="animation-delay:${s.delay || 0}ms" pathLength="1" d="${path(s.pts)}" fill="none" stroke="${s.color}" stroke-width="3.5" stroke-linejoin="round" stroke-linecap="round"/>`;
    if (s.label) {
      const [x, y] = s.at;
      g += `<text class="pop" style="animation-delay:${(s.delay || 0) + 600}ms" x="${X(x)}" y="${Y(y)}" fill="${s.color}" font-size="18" font-weight="600" text-anchor="${s.anchor || 'start'}">${esc(s.label)}</text>`;
    }
  });
  points.forEach((p) => {
    let tip = '';
    if (p.tip) {   // a label that shows on hover, like the recording
      const w = p.tip.length * 8.6 + 20;
      const tx = Math.min(X(p.x) + 12, W - R - w);
      tip = `<g class="tip"><rect x="${tx}" y="${Y(p.y) - 38}" width="${w}" height="28" rx="3" fill="${p.tipColor || '#0A1E2A'}"/>`
        + `<text x="${tx + 10}" y="${Y(p.y) - 19}" fill="#fff" font-size="15" font-weight="600">${esc(p.tip)}</text></g>`;
    }
    g += `<g class="pt pop" tabindex="0" style="animation-delay:${p.delay || 0}ms"><circle cx="${X(p.x)}" cy="${Y(p.y)}" r="${p.r || 7}" fill="${p.color}" stroke="#FBF9F3" stroke-width="2"/>`
      + `<circle cx="${X(p.x)}" cy="${Y(p.y)}" r="16" fill="transparent"/>${tip}</g>`;
    if (p.label) g += `<text class="pop" style="animation-delay:${p.delay || 0}ms" x="${X(p.x) + (p.dx || 0)}" y="${Y(p.y) + (p.dy || 0)}" fill="${p.text || '#14222C'}" font-size="17" font-weight="600" text-anchor="${p.anchor || 'start'}">${esc(p.label)}</text>`;
  });
  return `<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="${esc(label)}">${g}</svg>`;
}
const ceilTo = (v, s) => Math.ceil(v / s) * s;

// ------------------------------------------------------------------ 2 · size the booster
const form = $('#booster-form');
form.supply.addEventListener('change', () => { $('.mains', form).hidden = form.supply.value !== 'mains'; });
api('/api/pumps/sets').then((sets) => {
  $('#sets').innerHTML = sets.map((s) => `<option value="${esc(s.model)}" label="${esc(`${s.maker} · ${s.pumps} pumps · ${fmt(s.kw)} kW`)}">`).join('');
}).catch(() => {});

function verdictBanner(s, n) {
  const at = `${fmt(s.head_at_need_m, 0)} m available at ${fmt(n.peak_flow_m3h)} m³/h, ${fmt(n.required_head_m)} m needed`;
  if (s.verdict === 'fits') return `<div class="banner ok slim" style="animation-delay:500ms"><b>${esc(s.model)}: fits</b><span>${at}</span></div>`;
  const issue = s.issues[0] || '';
  return `<div class="banner return slim" style="animation-delay:500ms"><b>${esc(s.model)}: ${esc(issue.split(':')[0])}</b>
    <span>${s.head_at_need_m == null ? esc(issue) : at}${s.issues.length > 1 ? `; ${esc(s.issues.slice(1).join('; '))}` : ''}</span></div>`;
}

function renderBooster(r, flats) {
  const n = r.need;
  const s = r.submitted;
  $('#b-result').innerHTML = `
    <p class="step">1 · Calculates the need</p>
    <div class="stats"><div class="stat"><b>${fmt(n.peak_flow_m3h)}</b><span>m³/h peak flow</span></div>
      <div class="stat" style="animation-delay:120ms"><b>${fmt(n.required_head_m)}</b><span>m head</span></div></div>
    <p class="explain">${flats} flats, mixer taps · ${fmt(n.geometric_height_m)} m height + ${fmt(n.losses_m)} m losses + ${fmt(n.residual_m, 0)} m at the tap${n.mains_subtracted_m ? ` − ${fmt(n.mains_subtracted_m)} m from the mains` : ''}</p>
    <p class="cite">${esc(r.rules.join(' · '))} · DIN 1988-300</p>
    ${s ? `<p class="step">2 · Predicts from the real curve</p>${verdictBanner(s, n)}` : ''}
    ${r.unknown_submitted ? `<p class="step">2 · Predicts from the real curve</p><p class="error">That set is not one of the ${r.sets} Lowara sets. Check the model name.</p>` : ''}`;
  const sug = r.suggest[0];
  const shown = Object.values(r.curves).flat();
  const lead = r.curves[s ? s.model : sug?.model] || shown;   // frame the chart on the submitted set's own range
  const xMax = Math.max(10, ceilTo(Math.max(...lead.map(([q]) => q), n.peak_flow_m3h * 2), 5));
  const yMax = ceilTo(Math.max(...shown.map(([, h]) => h), n.required_head_m), 25);
  const series = [];
  if (s) series.push({ pts: r.curves[s.model], color: '#F15946', label: `${s.model} (submitted)`, delay: 300,
    at: [r.curves[s.model][0][0] + xMax * 0.02, r.curves[s.model][0][1] + yMax * 0.01] });
  if (sug) {
    const c = r.curves[sug.model].filter(([q]) => q <= xMax);
    series.push({ pts: c, color: '#1FA6A2', label: `${sug.model} (suggested)`, delay: 1200, at: [xMax * 0.99, c[c.length - 1][1] - yMax * 0.09], anchor: 'end' });
  }
  const points = [{ x: n.peak_flow_m3h, y: n.required_head_m, color: '#0A1E2A', delay: 100,
    label: `need ${fmt(n.peak_flow_m3h)} m³/h · ${fmt(n.required_head_m)} m`, dx: -14, dy: 34, anchor: 'middle',
    tip: `Need · ${fmt(n.peak_flow_m3h)} m³/h · ${fmt(n.required_head_m)} m` }];
  const guides = [];
  if (s && s.head_at_need_m != null) {
    points.unshift({ x: n.peak_flow_m3h, y: s.head_at_need_m, color: '#F15946', r: 6, delay: 900, tip: `${s.model} · ${fmt(s.head_at_need_m)} m`, tipColor: '#C93B29' });
    guides.push({ x1: n.peak_flow_m3h, y1: n.required_head_m, x2: n.peak_flow_m3h, y2: s.head_at_need_m, color: '#F15946', delay: 900 });
  }
  $('#b-chart').hidden = false;
  $('#b-chart').innerHTML = chart({ xMax, yMax, xStep: 5, yStep: 25, xLabel: 'Flow Q (m³/h)', yLabel: 'Head H (m)', series, points, guides,
    label: 'Pump curves of the submitted and suggested sets against the need' });
  const q = fmt(n.peak_flow_m3h);
  $('#b-suggest').innerHTML = `<div class="suggest"><p class="step">3 · Suggests from ${r.sets} Lowara booster sets · lowest power first</p>
    ${r.suggest.length ? `<table><thead><tr><th>Set</th><th>Power</th><th>Head at ${q} m³/h</th><th>With one pump out</th><th>Verdict</th></tr></thead>
    <tbody>${r.suggest.map((x, i) => `<tr style="animation-delay:${1500 + i * 150}ms"><td><b>${esc(x.model)}</b> · ${x.pumps} pumps</td><td>${fmt(x.kw_total)} kW</td>
      <td>${fmt(x.head_at_need_m)} m</td><td>${fmt(x.head_one_pump_out_m)} m</td><td><span class="chip pass">Fits · standby OK</span></td></tr>`).join('')}</tbody></table>`
    : '<p class="note">Nothing in the catalogue fits this building.</p>'}
    <p class="foot">Example building · curves from the Lowara GHV catalogue · an engineer confirms the choice</p></div>`;
}

form.addEventListener('submit', async (ev) => {
  ev.preventDefault();
  const err = $('#booster-error');
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

// ------------------------------------------------------------------ 3 · standby test, on the uploaded package
function renderStandby() {
  const a = state.analysis;
  const r = a && a.standby;
  if (state.standbyShown === r && r) return;
  state.standbyShown = r;
  $('#s-verdict').innerHTML = '';
  if (!r) {
    $('#s-lede').textContent = 'The booster set of the package, with the duty from its own data sheet';
    $('#s-grid').innerHTML = `<p class="note">${a ? 'The uploaded package has no booster set data sheet with a duty point.'
      : 'Upload the package in step 1 first: the standby test reads the booster set\'s curve from its data sheet.'}</p>`;
    return;
  }
  if (r.error) { $('#s-grid').innerHTML = `<p class="error">${esc(r.error)}</p>`; return; }
  const less = r.pumps - 1;
  $('#s-lede').textContent = `${shortName(r.model)} from the package · duty ${fmt(r.duty_flow, 0)} m³/h at ${fmt(r.duty_head, 0)} m`;
  const all = [...r.all, ...(r.less || [])];
  const xMax = ceilTo(Math.max(...all.map(([q]) => q)), 10);
  const yMin = Math.max(0, Math.floor(Math.min(...all.map(([, h]) => h)) / 5) * 5 - 5);
  const yMax = ceilTo(Math.max(...all.map(([, h]) => h)) + 1, 5);
  const at = (c, f, dx, dy) => [c[Math.floor(c.length * f)][0] + dx, c[Math.floor(c.length * f)][1] + dy];
  const series = [{ pts: r.all, color: '#0A1E2A', label: `${r.pumps} pumps`, at: at(r.all, 0.7, 1, 1.5), delay: 200 }];
  if (r.less) series.push({ pts: r.less, color: '#1FA6A2', label: `${less} pump${less === 1 ? '' : 's'} alone`, at: at(r.less, 0.78, 1.5, 0), delay: 900 });
  const points = [{ x: r.duty_flow, y: r.duty_head, color: '#F15946', delay: 1600, tip: `Duty · ${fmt(r.duty_flow)} m³/h · ${fmt(r.duty_head)} m` }];
  if (r.head_less != null) points.push({ x: r.duty_flow, y: r.head_less, color: '#1FA6A2', r: 6, delay: 1800, tip: `${less} pump${less === 1 ? '' : 's'} alone · ${fmt(r.duty_flow)} m³/h · ${fmt(r.head_less)} m`, tipColor: '#137C79' });
  const svg = chart({ xMax, yMin, yMax, xStep: 10, yStep: 5, xLabel: 'Flow Q (m³/h)', yLabel: 'Head H (m)', label: 'The set with all pumps and with one pump out, against the duty point',
    series, points, guides: [{ x1: r.duty_flow, y1: yMin, x2: r.duty_flow, y2: r.head_all ?? r.head_less ?? r.duty_head, color: '#9A958B', delay: 1500 }] });
  $('#s-grid').innerHTML = `
    <figure class="sheet"><p class="cap">${esc(r.file)} · page ${r.page}</p>
      <iframe title="${esc(r.file)}, page ${r.page}" src="/upload/${r.token}#page=${r.page}&toolbar=0&navpanes=0&view=FitH"></iframe></figure>
    <figure class="chart"><p class="cap">Curves read from the PDF's vector drawing · ${r.points} points</p>${svg}</figure>
    <div class="s-stats"><div class="stat red" style="animation-delay:1900ms"><b>${fmt(r.duty_head, 0)}</b><span>m needed at duty</span></div>
      <div class="stat" style="animation-delay:2150ms"><b>${fmt(r.head_less)}</b><span>m from ${less} pump${less === 1 ? '' : 's'} alone</span></div>
      <div class="stat" style="animation-delay:2400ms"><b>${fmt(r.margin_m)}</b><span>m margin</span></div></div>`;
  $('#s-verdict').innerHTML = r.standby
    ? `<div class="banner ok" style="animation-delay:2800ms"><b>Real standby</b><span>${less} pump${less === 1 ? '' : 's'} alone meet${less === 1 ? 's' : ''} the duty, with ${r.margin_pct < 5 ? 'only ' : ''}${fmt(r.margin_pct)}% to spare</span></div>`
    : `<div class="banner return" style="animation-delay:2800ms"><b>No real standby</b><span>with one pump out the set gives ${fmt(r.head_less)} m, ${fmt(-r.margin_m)} m short of the duty</span></div>`;
}

show(TABS.includes(location.hash.slice(1)) ? location.hash.slice(1) : 'check');
