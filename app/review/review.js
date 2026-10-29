'use strict';
// RightFit review page. Every result, number and comment comes from the server (app/review_server.py), which
// runs the deterministic checks. This page only shows them and sends back what the reviewer decides.

const $ = (sel, root = document) => root.querySelector(sel);
const esc = (s) => String(s ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const pad = (n) => String(n).padStart(2, '0');
const dmy = (iso) => (iso ? iso.split('-').reverse().join('.') : 'not set');
const openLink = (d, page, label) => `<a class="link open" href="/doc/${encodeURIComponent(state.pkg)}/${d.no}${page ? `#page=${encodeURIComponent(page)}` : ''}"
  target="_blank" rel="noopener"><svg aria-hidden="true"><use href="#i-open"/></svg>${esc(label || (page ? `Open p. ${page}` : 'Open the PDF'))}</a>`;
const breakable = (name) => esc(name).replace(/([_=@])/g, '$1<wbr>');
const plural = (n, word) => `${word}${n === 1 ? '' : 's'}`;
const VERDICT = { flag: 'Problem', unclear: 'Question', pass: 'OK', info: 'Info' };
const DECISION = { accepted: 'Add to my answer', rejected: 'Not relevant', suggested: 'Not decided' };
const STATUS_RULE = {
  A: 'Every check passed or is only for information.',
  B: 'Nothing sends the package back, but there is at least one problem or open question.',
  C: 'A product has no data sheet that names it, or a blocking checklist item is missing.',
};
const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)');

const state = { packages: [], pkg: null, location: 'RO', review: null, delivery: null, view: null, tab: 'findings',
  sel: null, staged: new Map(), reasonFor: null, error: null, drawn: null };

// "Not a problem" marks stay in this browser, per package, like a draft, and travel with every request.
const memory = {};
function dismissed() {
  try { return JSON.parse(localStorage.getItem(`rightfit.dismissed.${state.pkg}`)) || {}; } catch { return memory[state.pkg] || {}; }
}
function setDismissed(map) {
  memory[state.pkg] = map;
  try { localStorage.setItem(`rightfit.dismissed.${state.pkg}`, JSON.stringify(map)); } catch { /* private window */ }
}

// ------------------------------------------------------------------ talking to the server
async function api(path, body) {
  let res;
  try {
    res = await fetch(path, body ? { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) } : undefined);
  } catch {
    throw new Error('The review server is not answering. Start it from the repository folder with: python app/review_server.py');
  }
  const data = await res.json().catch(() => ({}));
  if (!res.ok || data.error) throw new Error(data.error || `The server answered ${res.status}.`);
  return data;
}

async function refresh(path = '/api/review', extra = {}) {
  document.body.classList.add('busy');
  let ok = true;
  try {
    state.view = await api(path, { package: state.pkg, location: state.location, review: state.review,
      delivery: state.delivery, dismissed: dismissed(), ...extra });
    state.error = null;
    state.review = state.view.review;
    state.delivery = state.view.delivery;
  } catch (e) {
    state.error = e.message;
    ok = false;
  }
  document.body.classList.remove('busy');
  render();
  return ok;
}

// ------------------------------------------------------------------ small helpers over the view
const results = () => state.view?.results || [];
const byDelta = (a, b) => (a.delta ?? 999) - (b.delta ?? 999);
const findings = () => results().filter((r) => !r.dismissed && (r.verdict === 'flag' || r.verdict === 'unclear')).sort(byDelta);
const itemName = (id) => state.view.items.find((i) => i.id === id)?.name || 'Package';
const docOf = (file) => state.view.documents.find((d) => d.file === file);
const aiLabel = (f) => f.delta ?? `A${state.view.ai_findings.indexOf(f) + 1}`;
const selKey = () => (state.sel ? JSON.stringify(state.sel) : '');

function parseSource(s) {
  const m = /^(.*), p\. (\S+)$/.exec(s);
  return m ? { file: m[1], page: m[2] } : { file: s, page: null };
}
function pointsAt(r, file) {
  return r.doc === file || r.sources.some((s) => parseSource(s).file === file);
}
function sourceLabel(r) {
  if (r.doc_no) return pad(r.doc_no);
  if (r.sources.length) {
    const { file, page } = parseSource(r.sources[0]);
    const d = docOf(file);
    const name = d ? pad(d.no) : file.toLowerCase().endsWith('.xls') ? 'Form' : file;
    return page ? `${name} · p. ${page}` : name;
  }
  return r.rules[0]?.id || 'Package';
}
function linkify(text) {
  return esc(text).replace(/https?:\/\/[^\s)<]+/g, (url) => `<a href="${url}" target="_blank" rel="noopener">${url}</a>`);
}
function delta(label, kind = '', size = '') {
  return `<span class="delta ${kind} ${size}" aria-hidden="true">${esc(label)}</span>`;
}
function firstSelection() {
  const fs = findings();
  const f = fs.find((r) => r.doc || r.evidence.length) || fs[0];
  if (f) return { type: 'result', key: f.key };
  const ai = state.view?.ai_findings?.[0];
  return ai ? { type: 'ai', id: ai.id } : null;
}

// ------------------------------------------------------------------ rendering
function render() {
  $('#packages').innerHTML = state.packages.map((p) => `<a href="#${esc(p.id)}" ${p.id === state.pkg ? 'aria-current="page"' : ''}>`
    + `${esc(p.id)}<span class="pname">&nbsp;· ${esc(p.items[0])}${p.items.length > 1 ? ` +${p.items.length - 1}` : ''}</span></a>`).join('');
  $('#meta').textContent = state.view ? `MAF ${state.view.form.form_no} · rev ${state.view.form.revision} · `
    + `${state.location === 'ES' ? 'Spain' : 'Romania'} · review ${dmy(state.review)} · delivery ${dmy(state.delivery)}` : '';
  if (!state.view) {
    $('#center').innerHTML = state.error ? errorBox() : '<p class="empty">Loading the package…</p>';
    return;
  }
  renderRail();
  renderCenter();
  renderDetail();
}

function errorBox() {
  return `<div class="error" role="alert"><p>${esc(state.error)}</p>
    <p style="margin-top:10px"><button class="btn" data-action="retry">Try again</button></p></div>`;
}

function renderRail() {
  const v = state.view;
  const most = Math.max(...v.documents.map((d) => d.pages));
  const pages = v.documents.reduce((a, d) => a + d.pages, 0);
  const marks = (d) => {
    const all = [
      ...findings().filter((r) => r.delta && pointsAt(r, d.file)).map((r) => delta(r.delta, r.verdict === 'flag' ? '' : 'q', 'sm')),
      ...v.ai_findings.filter((f) => f.status !== 'rejected' && f.evidence.some((e) => e.source === d.file)).map((f) => delta(aiLabel(f), 'ai', 'sm')),
    ];
    return all.slice(0, 4).join('') + (all.length > 4 ? `<span class="more">+${all.length - 4}</span>` : '');
  };
  $('#rail').innerHTML = `
    <h2>Package ${esc(v.package)}</h2>
    <p class="sub">MAF ${esc(v.form.form_no)} · rev ${esc(v.form.revision)} · ${v.documents.length} attachments · ${pages} pages</p>
    <div class="context" role="group" aria-label="Location and dates">
      <label for="location">Location</label><select id="location">${[['RO', 'Romania'], ['ES', 'Spain']].map(([k, n]) => `<option value="${k}" ${state.location === k ? 'selected' : ''}>${n}</option>`).join('')}</select>
      <label for="review">Review date</label><input type="date" id="review" value="${esc(state.review || '')}">
      <label for="delivery">Expected delivery</label><input type="date" id="delivery" value="${esc(state.delivery || '')}">
    </div>
    <h3>Products</h3>
    <ul class="products">${v.items.map((i) => `<li>${esc(i.name)}<span>${esc(i.brand)} · ${esc(i.model)}</span></li>`).join('')}</ul>
    <h3>Attachments</h3>
    <ul class="docs">${v.documents.map((d) => `<li><button class="doc" data-action="open-doc" data-file="${esc(d.file)}"
        ${state.sel?.type === 'doc' && state.sel.file === d.file ? 'aria-current="true"' : ''}>
        <span class="no">${pad(d.no)}</span>
        <span><span class="file">${breakable(d.file)}</span><span class="kind">${esc(d.type)} · ${d.pages} ${plural(d.pages, 'page')}</span>
        <span class="extent" style="width:${Math.max(2, (d.pages / most) * 100)}%"></span></span>
        <span class="marks">${marks(d)}</span></button></li>`).join('')}</ul>
    ${v.notes.length ? `<div class="notes"><h3>Reading notes</h3>${v.notes.map((n) => `<p>${esc(n)}</p>`).join('')}</div>` : ''}`;
}

function renderCenter() {
  const v = state.view;
  const c = v.counts;
  const letter = v.status.letter;
  const fs = findings();
  const tab = (id, label, count) => `<button class="tab" role="tab" id="tab-${id}" aria-selected="${state.tab === id}"
    aria-controls="panel" tabindex="${state.tab === id ? 0 : -1}" data-action="tab" data-tab="${id}">${label}<span class="count">${count}</span></button>`;
  const panel = state.tab === 'readings' ? readingsPanel() : state.tab === 'answer' ? answerPanel() : findingsPanel(fs);
  $('#center').innerHTML = `
    ${state.error ? errorBox() : ''}
    <button class="btn rail-toggle" data-action="toggle-rail"><svg><use href="#i-list"/></svg>Attachments and products</button>
    <section class="status" aria-label="Draft answer">
      <div class="status-top"><span class="letter ${letter}">${letter}</span><h1>${esc(v.status.label)}</h1></div>
        <div class="counts">
          <span><b>${c.problems}</b>${plural(c.problems, 'problem')}</span>
          <span><b>${c.questions}</b>${plural(c.questions, 'question')}</span>
          <span><b>${c.passed}</b>passed</span>
          <span><b>${c.would_pass}</b>would pass</span>
          <span><b>${c.to_confirm} / ${c.readings}</b>to confirm</span>
          ${c.ai_to_decide ? `<span><b>${c.ai_to_decide}</b>AI ${plural(c.ai_to_decide, 'suggestion')} to decide</span>` : ''}
        </div>
    </section>
    <details class="why"><summary>Why ${letter}?</summary><p style="margin-top:8px">${STATUS_RULE[letter]}</p><ul>${whyList()}</ul></details>
    ${c.to_confirm ? `<p class="hold-line">This draft rests on what the AI read. A check only counts as passed once you confirm the values behind it; ${c.would_pass} would pass now.</p>` : ''}
    <div class="tabs" role="tablist" aria-label="Review steps">
      ${tab('findings', '1 · Findings', fs.length)}${tab('readings', '2 · <span class="long">Confirm </span>readings', c.to_confirm)}${tab('answer', '3 · Answer<span class="long"> to send</span>', v.answer.lines.length)}
    </div>
    <div role="tabpanel" id="panel" aria-labelledby="tab-${state.tab}">${panel}</div>`;
}

function whyList() {
  const v = state.view;
  if (v.status.letter === 'C') return v.status.reasons.map((r) => `<li>${esc(r)}</li>`).join('');
  const counts = new Map();
  findings().forEach((r) => {
    const k = `${VERDICT[r.verdict]} · ${r.check_name}`;
    counts.set(k, (counts.get(k) || 0) + 1);
  });
  const added = v.ai_findings.filter((f) => f.status === 'accepted').length;
  if (added) counts.set('AI suggestion you added to the answer', added);
  return [...counts].map(([k, n]) => `<li>${esc(k)}: ${n}</li>`).join('');
}

function findingsPanel(fs) {
  const v = state.view;
  const problems = fs.filter((r) => r.verdict === 'flag');
  const questions = fs.filter((r) => r.verdict === 'unclear');
  const off = results().filter((r) => r.dismissed);
  const passed = results().filter((r) => !r.dismissed && (r.verdict === 'pass' || r.verdict === 'info'));
  const head = (b, d) => `<div class="rows-head" aria-hidden="true"><span>No.</span><span>${b}</span><span>Product</span><span>${d}</span></div>`;
  const list = (rs) => `${head('Finding', 'Source')}<ol class="rows">${rs.map(resultRow).join('')}</ol>`;
  return `
    ${fs.length ? '' : '<p class="empty">No findings. Every check passed or is only for information.</p>'}
    ${problems.length ? `<section class="group"><h2>Problems <span class="hint">found by the rules; each one is a comment in the answer</span></h2>${list(problems)}</section>` : ''}
    ${questions.length ? `<section class="group"><h2>Questions <span class="hint">for the contractor, or settled once you confirm the readings</span></h2>${list(questions)}</section>` : ''}
    <section class="group ai"><h2>AI suggestions <span class="hint">a second AI reviewer read the whole package; no rule checks these, so you decide</span></h2>
      ${v.ai_findings.length ? `${head('Suggestion', 'Decision')}<ol class="rows">${v.ai_findings.map(aiRow).join('')}</ol>` : '<p class="empty">The second AI reviewer has not run on this package yet.</p>'}</section>
    ${off.length ? `<section class="group"><h2>Marked not a problem <span class="hint">kept in this browser only; download the list in step 3</span></h2>${list(off)}</section>` : ''}
    <details class="group passed"><summary>Checks that pass or would pass, and information (${passed.length})</summary>
      <table><thead><tr><th>Check</th><th>About</th><th>Result</th><th>Why</th></tr></thead><tbody>
      ${passed.map((r) => `<tr><td>${esc(r.check_name)}</td><td>${esc(r.item ? itemName(r.item) : r.doc || 'Package')}</td>
        <td>${esc(VERDICT[r.verdict])}${r.confirmed ? '' : ' (reading not confirmed)'}</td><td>${linkify(r.reason)}</td></tr>`).join('')}
      </tbody></table></details>`;
}

function resultRow(r) {
  const current = state.sel?.type === 'result' && state.sel.key === r.key;
  return `<li><button class="row ${r.dismissed ? 'off' : ''}" data-action="select-result" data-key="${esc(r.key)}" ${current ? 'aria-current="true"' : ''}>
    ${r.dismissed ? delta('', 'ok') : delta(r.delta ?? '', r.verdict === 'flag' ? '' : 'q')}
    <span class="what"><b>${esc(r.check_name)}</b><span>${esc(r.dismissed ? `Not a problem: ${r.dismissed}` : r.comment || r.reason)}</span></span>
    <span class="prod">${esc(r.item ? itemName(r.item) : 'Package')}</span>
    <span class="src">${esc(sourceLabel(r))}</span></button></li>`;
}

function aiRow(f) {
  const current = state.sel?.type === 'ai' && state.sel.id === f.id;
  const decided = { suggested: 'Not decided', accepted: 'In my answer', rejected: 'Not relevant' }[f.status];
  return `<li><button class="row ai ${f.status === 'rejected' ? 'off' : ''}" data-action="select-ai" data-id="${esc(f.id)}" ${current ? 'aria-current="true"' : ''}>
    ${delta(aiLabel(f), 'ai')}
    <span class="what"><b>${esc(f.title)}</b><span>${esc(f.finding)}</span></span>
    <span class="prod">${esc(f.items.map(itemName).join(', '))}</span>
    <span class="src"><span class="tag">${esc(decided)}</span></span></button></li>`;
}

function readingsPanel() {
  const v = state.view;
  const box = (key, target, status) => {
    const now = state.staged.has(key) ? state.staged.get(key).verified : status === 'verified';
    return `<input type="checkbox" class="check" data-stage="${esc(key)}" data-target="${esc(JSON.stringify(target))}"
      data-was="${status === 'verified'}" ${now ? 'checked' : ''} aria-label="Correct">`;
  };
  const staged = (key) => (state.staged.has(key) ? 'class="staged"' : '');
  const products = v.items.map((i) => `
    <section class="group"><h2>${esc(i.name)} <span class="hint">${esc(i.brand)} · ${esc(i.model)}</span></h2>
    <table class="rtable"><thead><tr><th>Correct?</th><th>What</th><th>Value</th><th>Quote from the document</th><th>Source</th></tr></thead><tbody>
    ${i.values.map((x) => {
      const key = `value|${i.id}|${x.key}`;
      const by = x.status === 'verified' ? `<span class="conf">confirmed by ${esc(x.checked_by || 'the reviewer')}${x.verified_on ? ` · ${dmy(x.verified_on)}` : ''}</span>` : '';
      const doc = x.source ? docOf(x.source) : null;
      return `<tr ${staged(key)}><td>${box(key, { kind: 'value', item: i.id, key: x.key }, x.status)}</td><td>${esc(x.what)}${by}</td>
        <td class="v">${x.value == null || x.value === '' ? '<span class="muted">not found</span>' : `${esc(x.value)}${x.unit ? ` ${esc(x.unit)}` : ''}`}</td>
        <td class="q">${x.quote ? `“${esc(x.quote)}”` : '<span class="muted">no quote</span>'}</td>
        <td class="v">${x.source ? refLink(`${x.source}, p. ${x.page}`) : '<span class="muted">none</span>'}${doc ? `<br>${openLink(doc, x.page, 'Open')}` : ''}</td></tr>`;
    }).join('')}</tbody></table></section>`).join('');
  const docs = `<section class="group"><h2>Attachments <span class="hint">what each document is, as the AI read it</span></h2>
    <table class="rtable"><thead><tr><th>Correct?</th><th>No</th><th>Document</th><th>What it is</th><th>Listed in the form as</th><th>Covers</th><th>Valid until</th></tr></thead><tbody>
    ${v.documents.map((d) => {
      const key = `document|${d.file}`;
      return `<tr ${staged(key)}><td>${box(key, { kind: 'document', file: d.file }, d.status)}</td><td class="v">${pad(d.no)}</td><td>${breakable(d.file)}</td>
        <td>${esc(d.type)}</td><td>${esc(d.listed_as || 'not listed')}</td><td class="q">${esc(d.covers.join('; '))}</td><td class="v">${esc(d.valid_until || '')}</td></tr>`;
    }).join('')}</tbody></table></section>`;
  const pairs = v.documents.flatMap((d) => d.matches.map((m) => ({ d, m })));
  const matches = pairs.length ? `<section class="group"><h2>Which document covers which product <span class="hint">matched by the AI; a range is enough for a declaration, not for a data sheet</span></h2>
    <table class="rtable"><thead><tr><th>Correct?</th><th>Document</th><th>Product</th><th>How</th><th>Page</th><th>Quote</th></tr></thead><tbody>
    ${pairs.map(({ d, m }) => {
      const key = `match|${d.file}|${m.item}`;
      return `<tr ${staged(key)}><td>${box(key, { kind: 'match', file: d.file, item: m.item }, m.status)}</td><td>${pad(d.no)}</td><td>${esc(itemName(m.item))}</td>
        <td>${esc(m.kind)}</td><td class="v">${esc(m.page ?? '')}</td><td class="q">${m.quote ? `“${esc(m.quote)}”` : ''}</td></tr>`;
    }).join('')}</tbody></table></section>` : '';
  const n = state.staged.size;
  return `<p class="lead">Tick each line you have checked against the document. Unticked lines stay as the AI read them, and every check that rests on them stays a question.</p>
    ${products}${docs}${matches}
    <div class="savebar"><button class="btn primary" data-action="save" ${n ? '' : 'disabled'}>Save what I confirmed${n ? ` (${n})` : ''}</button>
      ${n ? '<button class="link" data-action="discard">Discard the ticks</button>' : ''}
      <span class="note">Saved as ${esc('Luca')}, with today's date, into the package file. The checks then run again.</span></div>`;
}

function answerKinds() {
  const kinds = {};
  results().forEach((r) => { if (r.delta && !kinds[r.delta]) kinds[r.delta] = r.verdict === 'flag' ? '' : 'q'; });
  state.view.ai_findings.forEach((f) => { if (f.delta) kinds[f.delta] = 'ai'; });
  return kinds;
}

function answerPanel() {
  const v = state.view;
  const kinds = answerKinds();
  return `<article class="letter-sheet" aria-label="Answer to send">
      <p class="head">MAF ${esc(v.form.form_no)} rev ${esc(v.form.revision)}: ${esc(v.status.label)} (${v.status.letter})</p>
      ${v.answer.lines.length ? `<ol>${v.answer.lines.map((line, i) => `<li>${delta(i + 1, kinds[i + 1] || '')}<span>${linkify(line)}</span></li>`).join('')}</ol>`
        : '<p class="empty">No comments.</p>'}
      <p class="sign">Drafted by RightFit from the checks and your decisions. You check it and you sign it; the tool certifies nothing.</p>
    </article>
    <div class="exports">
      <button class="btn primary" data-action="copy"><svg><use href="#i-copy"/></svg>Copy the answer</button>
      <button class="btn" data-action="dl-answer"><svg><use href="#i-down"/></svg>Download the answer</button>
      <button class="btn" data-action="dl-values"><svg><use href="#i-down"/></svg>Download confirmed values</button>
      <button class="btn" data-action="dl-off"><svg><use href="#i-down"/></svg>Download what I marked not a problem</button>
    </div>`;
}

// ------------------------------------------------------------------ the detail panel and its evidence
const PLACEHOLDER = '<p class="placeholder">Select a finding, an AI suggestion or an attachment to see its evidence.</p>';

function renderDetail() {
  const s = state.sel;
  let html = PLACEHOLDER;
  if (s?.type === 'result') html = resultDetail(results().find((r) => r.key === s.key));
  else if (s?.type === 'ai') html = aiDetail(state.view.ai_findings.find((f) => f.id === s.id));
  else if (s?.type === 'doc') html = docDetail(docOf(s.file), s.page);
  $('#detail').innerHTML = `<button class="btn close" data-action="close-sheet" aria-label="Close the details"><svg><use href="#i-close"/></svg></button>${html}`;
  const animate = state.drawn !== selKey();
  state.drawn = selKey();
  drawClouds(animate);
}

function sheet({ quote, reading, file, page, note, ai = false, verbatim = true, pin }) {
  const d = file ? docOf(file) : null;
  const where = d
    ? `<button class="link" data-action="open-doc" data-file="${esc(file)}" ${page ? `data-page="${esc(page)}"` : ''}><span class="num">${pad(d.no)}</span> · ${esc(file)}${page ? `, p. ${esc(page)}` : ''}</button>`
    : `<span>${esc(file || '')}${page ? `, p. ${esc(page)}` : ''}</span>`;
  return `<div class="sheet ${ai ? 'ai' : ''}">
      ${reading ? `<p class="reading">${esc(reading)}</p>` : ''}
      <span class="q-wrap" ${quote ? 'data-cloud' : ''}>${verbatim ? `<q>${esc(quote || 'no quote')}</q>` : `<span>${esc(quote)}</span>`}
        ${pin != null && quote ? `<span class="pin">${delta(pin, ai ? 'ai' : '')}</span>` : ''}</span>
      <p class="where">${where}${d ? openLink(d, page) : ''}<span>${esc(note)}</span></p></div>`;
}

function resultDetail(r) {
  if (!r) return PLACEHOLDER;
  const tone = r.dismissed ? '' : r.verdict === 'flag' ? 'r' : r.verdict === 'unclear' ? 'q' : '';
  const d = r.doc ? docOf(r.doc) : null;
  const pin = r.dismissed ? null : r.delta;
  const sheets = [];
  if (d) {
    const read = r.check === 'D2' ? `Covers ${d.covers.join('; ')}` : r.check === 'D3' ? `Valid until ${d.valid_until || 'not stated'}`
      : r.check === 'D4' ? `Read as: ${d.type}. Listed in the form as "${d.listed_as || 'not listed'}".` : `Read as: ${d.type}`;
    sheets.push(sheet({ quote: read, file: d.file, verbatim: false, pin, note: d.status === 'verified' ? 'confirmed' : 'what the AI read, not yet confirmed' }));
  }
  r.evidence.forEach((e) => sheets.push(sheet({ quote: e.quote, file: e.source, page: e.page, pin,
    reading: `${e.what}: ${e.value ?? 'not found'}${e.unit ? ` ${e.unit}` : ''}`,
    note: e.status === 'verified' ? 'confirmed' : 'read by the AI, not yet confirmed' })));
  return `
    <header class="d-head">${r.dismissed ? delta('', 'ok', 'big') : delta(r.delta ?? '', r.verdict === 'flag' ? '' : 'q', 'big')}
      <div><h2>${esc(r.check_name)}</h2>
      <p class="subline"><b class="${tone}">${esc(r.dismissed ? 'Not a problem' : VERDICT[r.verdict])}</b> · ${esc(r.product || 'The whole package')}</p></div></header>
    ${r.comment ? `<p class="comment">${linkify(r.comment)}</p><p class="answer-ref">Comment ${r.delta} in the answer.</p>` : ''}
    ${r.dismissed ? `<p class="dismissed-note">You marked this as not a problem: ${esc(r.dismissed)}. It is left out of the answer.</p>` : ''}
    ${sheets.length ? `<section class="evidence"><h3>Evidence</h3>${sheets.join('')}</section>` : ''}
    <dl class="facts"><dt>Why</dt><dd>${linkify(r.reason)}</dd>
      ${r.sources.length ? `<dt>Look at</dt><dd class="refs">${r.sources.map(refLink).join('')}</dd>` : ''}
      ${r.rules.length ? `<dt>Rule</dt><dd>${r.rules.map((x) => `${esc(x.id)} (${esc(x.status.replace(/_/g, ' '))})`).join(', ')}</dd>` : ''}</dl>
    ${!r.confirmed && !r.dismissed ? '<p class="hold-note">Read by the AI and not yet confirmed. This stays a question until you confirm the readings behind it in step 2.</p>' : ''}
    ${resultActions(r)}`;
}

function refLink(source) {
  const { file, page } = parseSource(source);
  const d = docOf(file);
  if (!d) return `<span>${file.toLowerCase().endsWith('.xls') ? 'Form' : esc(file)}${page ? ` · p. ${esc(page)}` : ''}</span>`;
  return `<button class="link" data-action="open-doc" data-file="${esc(file)}" ${page ? `data-page="${esc(page)}"` : ''}>${pad(d.no)}${page ? ` · p. ${esc(page)}` : ''}</button>`;
}

function resultActions(r) {
  if (r.dismissed) return `<div class="actions"><button class="btn" data-action="undismiss" data-key="${esc(r.key)}">Put it back in the answer</button></div>`;
  if (r.verdict !== 'flag' && r.verdict !== 'unclear') return '';
  if (state.reasonFor !== r.key) return `<div class="actions"><button class="btn" data-action="ask-reason" data-key="${esc(r.key)}">Not a problem…</button></div>`;
  return `<div class="ask"><label for="reason" class="answer-ref">Why is it not a problem? The reason goes into the export, not into the answer. It is kept in this browser only, so download the list in step 3 before you change computers.</label>
    <textarea id="reason" class="reason" placeholder="For example: agreed with the client at the site meeting"></textarea>
    <div class="actions"><button class="btn primary" data-action="dismiss" data-key="${esc(r.key)}">Mark as not a problem</button>
    <button class="link" data-action="cancel-reason">Cancel</button></div></div>`;
}

function aiDetail(f) {
  if (!f) return PLACEHOLDER;
  return `
    <header class="d-head">${delta(aiLabel(f), 'ai', 'big')}<div><h2>${esc(f.title)}</h2>
      <p class="subline"><b class="ai">AI suggestion</b> · ${f.kind === 'problem' ? 'Problem' : 'Question'} · ${esc(f.items.map(itemName).join(', '))}</p></div></header>
    <p class="comment">${esc(f.finding)}</p>
    <section class="evidence"><h3>What the AI points to</h3>
      ${f.evidence.map((e) => sheet({ quote: e.quote, file: e.source, page: e.page, ai: true, pin: aiLabel(f), note: 'quoted by the AI reviewer' })).join('')}</section>
    <dl class="facts"><dt>Comment</dt><dd>${esc(f.suggested_comment)}</dd></dl>
    <p class="hold-note">No rule checks this, and it changes no check result. It goes into the answer only if you add it.</p>
    <div class="actions"><div class="seg" role="radiogroup" aria-label="Your decision">
      ${['accepted', 'rejected', 'suggested'].map((s) => `<button role="radio" aria-checked="${f.status === s}" data-action="decide" data-id="${esc(f.id)}" data-status="${s}">${DECISION[s]}</button>`).join('')}
    </div></div>
    ${f.status === 'accepted' ? `<p class="answer-ref">Comment ${f.delta} in the answer.</p>` : ''}
    ${f.status === 'rejected' ? `<label for="ai-note" class="answer-ref" style="display:block;margin-top:14px">Why is it not relevant?</label>
      <textarea id="ai-note" class="reason" data-note="${esc(f.id)}">${esc(f.note || '')}</textarea>` : ''}`;
}

function docDetail(d, page) {
  if (!d) return PLACEHOLDER;
  const v = state.view;
  const onPage = page ? v.items.flatMap((i) => i.values.filter((x) => x.source === d.file && String(x.page) === String(page)).map((x) => ({ ...x, product: i.name }))) : [];
  const pointing = findings().filter((r) => r.delta && pointsAt(r, d.file));
  return `
    <header class="d-head"><span class="no-big">${pad(d.no)}</span><div><h2>${breakable(d.file)}</h2>
      <p class="subline">${esc(d.type)} · ${d.pages} ${plural(d.pages, 'page')}${page ? ` · opened at p. ${esc(page)}` : ''}</p>
      <p class="subline">${openLink(d, page, page ? `Open the PDF at p. ${page}` : 'Open the PDF')}</p></div></header>
    ${page ? `<section class="evidence"><h3>What the AI read on p. ${esc(page)}</h3>
      ${onPage.length ? onPage.map((x) => sheet({ quote: x.quote, file: d.file, page, reading: `${x.product} · ${x.what}: ${x.value ?? 'not found'}${x.unit ? ` ${x.unit}` : ''}`,
        note: x.status === 'verified' ? 'confirmed' : 'read by the AI, not yet confirmed' })).join('') : '<p class="empty">No values were read from this page.</p>'}</section>` : ''}
    <dl class="facts">
      <dt>Listed as</dt><dd>${esc(d.listed_as || 'not listed in the form')}</dd>
      <dt>Covers</dt><dd>${esc(d.covers.join('; ') || 'not stated')}</dd>
      <dt>Issued by</dt><dd>${esc(d.issuer || 'not stated')}</dd>
      <dt>Issued on</dt><dd class="num">${esc(d.issue_date || 'not stated')}</dd>
      <dt>Valid until</dt><dd class="num">${esc(d.valid_until || 'not stated')}</dd>
      <dt>Languages</dt><dd>${esc((d.languages || []).join(', '))}</dd>
      <dt>Read from</dt><dd>${esc(d.method)}</dd>
      <dt>Status</dt><dd>${d.status === 'verified' ? 'Confirmed' : 'Read by the AI, not yet confirmed'}</dd>
      ${d.notes ? `<dt>Notes</dt><dd>${esc(d.notes)}</dd>` : ''}
    </dl>
    ${d.matches.length ? `<section class="evidence"><h3>Products it covers</h3>${d.matches.map((m) => sheet({ quote: m.quote, file: d.file, page: m.page,
      reading: `${itemName(m.item)} · ${m.kind}`, note: m.status === 'verified' ? 'confirmed' : 'matched by the AI, not yet confirmed' })).join('')}</section>` : ''}
    ${pointing.length ? `<section class="evidence"><h3>Findings on this document</h3><div class="refs" style="margin-top:8px">
      ${pointing.map((r) => `<button class="link" data-action="select-result" data-key="${esc(r.key)}">Comment ${r.delta} · ${esc(r.check_name)}</button>`).join('')}</div></section>` : ''}`;
}

// The signature move: a revision cloud draws itself around each quote, the way a checker marks a drawing.
function cloudPath(w, h, r = 10) {
  const nx = Math.max(2, Math.round(w / (2 * r)));
  const ny = Math.max(1, Math.round(h / (2 * r)));
  const sx = w / nx;
  const sy = h / ny;
  let d = 'M0 0';
  for (let i = 0; i < nx; i++) d += ` a${sx / 2} ${sx / 2} 0 0 1 ${sx} 0`;
  for (let i = 0; i < ny; i++) d += ` a${sy / 2} ${sy / 2} 0 0 1 0 ${sy}`;
  for (let i = 0; i < nx; i++) d += ` a${sx / 2} ${sx / 2} 0 0 1 ${-sx} 0`;
  for (let i = 0; i < ny; i++) d += ` a${sy / 2} ${sy / 2} 0 0 1 0 ${-sy}`;
  return `${d} Z`;
}

function drawClouds(animate) {
  document.querySelectorAll('#detail [data-cloud]').forEach((wrap, i) => {
    const w = wrap.offsetWidth;
    const h = wrap.offsetHeight;
    if (!w || !h) return;
    const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    svg.setAttribute('class', 'cloud');
    svg.setAttribute('width', w);
    svg.setAttribute('height', h);
    svg.setAttribute('viewBox', `0 0 ${w} ${h}`);
    svg.setAttribute('aria-hidden', 'true');
    const path = document.createElementNS(svg.namespaceURI, 'path');
    path.setAttribute('d', cloudPath(w, h));
    svg.appendChild(path);
    wrap.prepend(svg);
    if (!animate || reduceMotion.matches) return;
    const len = path.getTotalLength();
    path.style.strokeDasharray = `${len}`;
    path.style.strokeDashoffset = `${len}`;
    svg.classList.add('drawn');
    path.style.transitionDelay = `${i * 140}ms`;
    requestAnimationFrame(() => requestAnimationFrame(() => { path.style.strokeDashoffset = '0'; }));
  });
}

// ------------------------------------------------------------------ exports
const cell = (v) => { const s = String(v ?? ''); return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s; };
const csv = (rows) => `${rows.map((r) => r.map(cell).join(',')).join('\n')}\n`;
function download(name, text) {
  const a = document.createElement('a');
  a.href = URL.createObjectURL(new Blob([text], { type: name.endsWith('.csv') ? 'text/csv' : 'text/plain' }));
  a.download = name;
  a.click();
  setTimeout(() => URL.revokeObjectURL(a.href), 2000);
}
function confirmedCsv() {
  return csv([['item', 'value', 'reading', 'unit', 'file', 'page'], ...state.view.items.flatMap((i) => i.values
    .filter((x) => x.status === 'verified').map((x) => [`${i.name} (${i.model})`, x.what, x.value, x.unit, x.source, x.page]))]);
}
function offCsv() {
  return csv([['check', 'about', 'why'], ...results().filter((r) => r.dismissed).map((r) => [r.check, r.product || r.doc || 'package', r.dismissed])]);
}

let toastTimer;
function toast(message) {
  const t = $('#toast');
  t.textContent = message;
  t.classList.add('on');
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => t.classList.remove('on'), 2800);
}

// ------------------------------------------------------------------ what the reviewer does
function markSelection() {
  document.querySelectorAll('.row, .doc').forEach((b) => {
    const s = state.sel;
    const on = s && ((s.type === 'result' && b.dataset.key === s.key) || (s.type === 'ai' && b.dataset.id === s.id)
      || (s.type === 'doc' && b.classList.contains('doc') && b.dataset.file === s.file));
    if (on) b.setAttribute('aria-current', 'true'); else b.removeAttribute('aria-current');
  });
}

function select(sel) {
  state.sel = sel;
  state.reasonFor = null;
  markSelection();
  renderDetail();
  document.body.classList.add('sheet-open');
}

async function switchTo(id) {
  if (!state.packages.some((p) => p.id === id) || id === state.pkg) return;
  Object.assign(state, { pkg: id, review: null, delivery: null, sel: null, tab: 'findings', reasonFor: null, drawn: null });
  state.staged.clear();
  await refresh();
  state.sel = firstSelection();
  render();
}

document.addEventListener('click', async (ev) => {
  const el = ev.target.closest('[data-action]');
  if (!el) return;
  const a = el.dataset.action;
  if (a === 'select-result') select({ type: 'result', key: el.dataset.key });
  else if (a === 'select-ai') select({ type: 'ai', id: el.dataset.id });
  else if (a === 'open-doc') select({ type: 'doc', file: el.dataset.file, page: el.dataset.page || null });
  else if (a === 'tab') { state.tab = el.dataset.tab; renderCenter(); $(`#tab-${state.tab}`)?.focus(); }
  else if (a === 'ask-reason') { state.reasonFor = el.dataset.key; renderDetail(); $('#reason')?.focus(); }
  else if (a === 'cancel-reason') { state.reasonFor = null; renderDetail(); }
  else if (a === 'dismiss') {
    setDismissed({ ...dismissed(), [el.dataset.key]: $('#reason').value.trim() || 'no reason given' });
    state.reasonFor = null;
    if (await refresh()) toast('Marked as not a problem. It is out of the answer.');
  } else if (a === 'undismiss') {
    const map = { ...dismissed() };
    delete map[el.dataset.key];
    setDismissed(map);
    if (await refresh()) toast('Back in the answer.');
  } else if (a === 'decide') {
    const status = el.dataset.status;
    if (await refresh('/api/decide', { id: el.dataset.id, status })) {
      toast({ accepted: 'Added to your answer.', rejected: 'Marked not relevant.', suggested: 'Back to not decided.' }[status]);
    }
  } else if (a === 'save') {
    const targets = [...state.staged.values()].map(({ target, verified }) => ({ ...target, verified }));
    if (await refresh('/api/confirm', { targets })) {
      state.staged.clear();
      renderCenter();
      toast('Saved. The checks ran again on what you confirmed.');
    }
  } else if (a === 'discard') { state.staged.clear(); renderCenter(); }
  else if (a === 'copy') {
    try { await navigator.clipboard.writeText(state.view.answer.text); toast('Answer copied.'); } catch { toast('Could not copy here. Use Download the answer.'); }
  } else if (a === 'dl-answer') download(`${state.pkg}_answer.txt`, state.view.answer.text);
  else if (a === 'dl-values') download(`${state.pkg}_confirmed_values.csv`, confirmedCsv());
  else if (a === 'dl-off') download(`${state.pkg}_not_a_problem.csv`, offCsv());
  else if (a === 'toggle-rail') document.body.classList.toggle('rail-open');
  else if (a === 'close-sheet') document.body.classList.remove('sheet-open');
  else if (a === 'retry') init();
});

document.addEventListener('change', async (ev) => {
  const t = ev.target;
  if (t.dataset.stage) {
    const was = t.dataset.was === 'true';
    if (t.checked === was) state.staged.delete(t.dataset.stage);
    else state.staged.set(t.dataset.stage, { target: JSON.parse(t.dataset.target), verified: t.checked });
    const scroll = $('#center').scrollTop;
    renderCenter();
    $('#center').scrollTop = scroll;
  } else if (t.dataset.note) {
    if (await refresh('/api/decide', { id: t.dataset.note, status: 'rejected', note: t.value.trim() })) toast('Reason saved.');
  } else if (t.id === 'location') { state.location = t.value; await refresh(); }
  else if (t.id === 'review' || t.id === 'delivery') { state[t.id] = t.value || null; await refresh(); }
});

document.addEventListener('keydown', (ev) => {
  if (ev.key === 'Escape') document.body.classList.remove('sheet-open');
  if (!ev.target.closest('[role="tab"]') || !['ArrowRight', 'ArrowLeft'].includes(ev.key)) return;
  const order = ['findings', 'readings', 'answer'];
  state.tab = order[(order.indexOf(state.tab) + (ev.key === 'ArrowRight' ? 1 : 2)) % 3];
  renderCenter();
  $(`#tab-${state.tab}`).focus();
  ev.preventDefault();
});

window.addEventListener('hashchange', () => switchTo(window.location.hash.slice(1)));

async function init() {
  try {
    state.packages = await api('/api/packages');
  } catch (e) {
    state.error = e.message;
    render();
    return;
  }
  const wanted = window.location.hash.slice(1);
  state.pkg = state.packages.some((p) => p.id === wanted) ? wanted : state.packages[0]?.id;
  await refresh();
  state.sel = firstSelection();
  render();
}
init();
