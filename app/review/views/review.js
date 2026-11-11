// One package in three steps: go through the problems, confirm what the AI read, send the answer. Every result, number
// and comment comes from the server (app/review_server.py), which runs the deterministic checks. This screen only
// shows them beside the documents and sends back what the reviewer decides.
import { $, api, breakable, csv, dmy, download, esc, icon, linkify, pad, plural, store, toast } from '../lib.js';

const STEPS = ['problems', 'readings', 'answer'];
const MAKER = "the manufacturer's copy";
const STATUS_RULE = {
  A: 'Every check passed or is only for information.',
  B: 'Nothing sends the package back, but there is at least one problem or open question.',
  C: 'A product has no data sheet that names it, or a blocking checklist item is missing.',
};
const RULE_STATUS = {
  verified_official: 'read in the official journal',
  verified_secondary: 'read in a copy of the text, still to check on the official one',
  to_confirm: 'still to confirm on the official text',
  practice: "reviewers' practice",
  engineer_input: "a value set by the team's engineer",
  guidance: "a manufacturer's recommendation",
  checklist: "from past reviewers' comments",
};

const S = { root: null, active: false, pkg: null, view: null, error: null, step: 'problems', location: 'RO', review: null, delivery: null,
  sel: null, reasonFor: null, doc: null, page: 1, big: false, shown: '', readAt: null, groupOpen: new Map(), inked: new Set(), marksRun: 0 };

// ------------------------------------------------------------------ what stays in this browser, per package
const dismissed = () => store.read(`rightfit.dismissed.${S.pkg}`, {});
const seen = () => new Set(store.read(`rightfit.seen.${S.pkg}`, []));
function markSeen(id) {
  const s = seen();
  s.add(id);
  store.write(`rightfit.seen.${S.pkg}`, [...s]);
}

async function refresh(path = '/api/review', extra = {}) {
  try {
    S.view = await api(path, { package: S.pkg, location: S.location, review: S.review, delivery: S.delivery, dismissed: dismissed(), ...extra });
    S.error = null;
    S.review = S.view.review;
    S.delivery = S.view.delivery;
    return true;
  } catch (e) {
    S.error = e.message;
    return false;
  }
}

// ------------------------------------------------------------------ the list: everything to go through, product by product
const docOf = (file) => S.view.documents.find((d) => d.file === file);
const currentDoc = () => S.view.documents.find((d) => d.no === S.doc) || null;
const isOpenResult = (r) => r.dismissed || r.verdict === 'flag' || r.verdict === 'unclear';

function groups() {
  const v = S.view;
  const rank = (r) => (r.dismissed ? 2 : r.verdict === 'flag' ? 0 : 1);
  const results = v.results.filter(isOpenResult).sort((a, b) => rank(a) - rank(b) || (a.delta ?? 999) - (b.delta ?? 999));
  const of = (id) => results.filter((r) => (r.item ?? 'package') === id).map((r) => ({ kind: 'result', id: r.key, r }));
  return [...v.items.map((i) => ({ id: i.id, name: i.name, model: i.model, rows: of(i.id) })),
    { id: 'package', name: 'Whole package', model: '', rows: of('package') },
    { id: 'ai', name: 'Suggested by the AI reviewer', model: '', rows: v.ai_findings.map((f) => ({ kind: 'ai', id: `ai:${f.id}`, f })) },
  ].filter((g) => g.rows.length);
}
const flat = () => groups().flatMap((g) => g.rows);
const current = () => flat().find((x) => x.id === S.sel) || null;
function isDone(row, was = seen()) {
  return row.kind === 'ai' ? row.f.status !== 'suggested' : Boolean(row.r.dismissed) || was.has(row.id);
}

function parseSource(s) {
  const m = /^(.*), p\. (\S+)$/.exec(s);
  return m ? { file: m[1], page: m[2] } : { file: s, page: null };
}

// The page a problem points to: its first reading on a PDF, the document it is about, or its first source.
function ownPlace(row) {
  if (row.kind === 'ai') {
    const e = row.f.evidence.find((x) => docOf(x.source));
    return e ? { no: docOf(e.source).no, page: Number(e.page) || 1 } : null;
  }
  const r = row.r;
  const e = r.evidence.find((x) => docOf(x.source));
  if (e) return { no: docOf(e.source).no, page: Number(e.page) || 1 };
  if (r.doc && docOf(r.doc)) return { no: docOf(r.doc).no, page: 1 };
  for (const s of r.sources) {
    const { file, page } = parseSource(s);
    if (docOf(file)) return { no: docOf(file).no, page: Number(page) || 1 };
  }
  return null;
}

// A problem with no page of its own still opens a real page: the data sheet of its product.
function placeOf(row) {
  const own = ownPlace(row);
  if (own) return own;
  const docs = S.view.documents;
  const item = row.kind === 'ai' ? row.f.items?.[0] : row.r.item;
  const d = docs.find((x) => x.type === 'data sheet' && x.matches.some((m) => m.item === item)) || docs.find((x) => x.type === 'data sheet') || docs[0];
  return d ? { no: d.no, page: Number(d.matches.find((m) => m.item === item)?.page) || 1 } : null;
}

function showPlace(place) {
  S.doc = place ? place.no : null;
  S.page = place ? place.page : 1;
}

function pickFirst() {
  const was = seen();
  const all = flat();
  // Inside the first product still open, start on a problem that has its own page to show.
  const rows = groups().find((g) => g.rows.some((x) => !isDone(x, was)))?.rows || [];
  S.sel = (rows.find((x) => !isDone(x, was) && ownPlace(x)) || all.find((x) => !isDone(x, was)) || all[0])?.id ?? null;
  const row = current();
  showPlace(row ? placeOf(row) : null);
}

// ------------------------------------------------------------------ drawing
export async function render(root, [pkg, step]) {
  S.root = root;
  S.active = true;
  const wanted = STEPS.includes(step) ? step : 'problems';
  if (pkg !== S.pkg || !S.view) {
    Object.assign(S, { pkg, view: null, review: null, delivery: null, location: 'RO', sel: null, reasonFor: null, doc: null, page: 1, readAt: null });
    S.groupOpen = new Map();
    root.innerHTML = '<p class="empty">Loading the package…</p>';
    await refresh();
    if (S.pkg !== pkg) return;
    if (!S.view) { drawError(); return; }
    pickFirst();
  }
  S.step = wanted;
  if (S.step === 'readings') { if (!S.readAt) firstReadingPage(); showPlace(S.readAt); }
  if (S.step === 'problems') { const row = current(); if (row) showPlace(placeOf(row)); }
  S.root.innerHTML = `<div class="review"><div class="head" id="head"></div><nav class="steps" id="steps" aria-label="Review steps"></nav>
    <div class="work"><section class="list" id="left" aria-label="Review"></section><section class="doc" id="right" aria-label="Document"></section></div></div>`;
  const el = S.root.firstElementChild;
  el.addEventListener('click', onClick);
  el.addEventListener('change', onChange);
  S.shown = '';
  drawAll();
}

export function leave() { S.active = false; }

function drawError() {
  S.root.innerHTML = `<div class="screen"><p class="error" role="alert">${esc(S.error)}</p>
    <p style="margin-top:10px"><a class="btn" href="#/packages">Back to the packages</a></p></div>`;
}

function drawAll() {
  drawHead();
  drawSteps();
  drawLeft();
  drawRight();
}

function drawHead() {
  const v = S.view;
  const c = v.counts;
  const letter = v.status.letter;
  const pages = v.documents.reduce((a, d) => a + d.pages, 0);
  const n = v.items.length;
  $('#head').innerHTML = `
    <div class="fld"><span class="lab">Form</span><span class="typed">MAF ${esc(v.form.form_no)} rev ${esc(v.form.revision)}</span></div>
    <div class="fld"><span class="lab">Package</span><span class="typed">${n} ${plural(n, 'product')}, ${v.documents.length + 1} files, ${pages} pages</span></div>
    <div class="fld"><span class="lab">Draft answer</span><div class="ans"><i class="letter ${letter}">${letter}</i><b>${esc(v.status.label)}</b></div></div>
    <details class="whyb"><summary>Why ${letter}?</summary><div class="pop"><p>${STATUS_RULE[letter]}</p><ul>${whyList()}</ul></div></details>
    <div class="prog">${progress(c)}</div>`;
}

function progress(c) {
  if (S.step === 'readings') {
    const done = c.readings - c.to_confirm;
    return `<b>${done} of ${c.readings} confirmed</b><div class="track" style="width:240px;margin-left:auto"><div class="fill" style="width:${(done / (c.readings || 1)) * 100}%"></div></div>`;
  }
  if (S.step === 'answer') return `<b>${S.view.answer.lines.length} ${plural(S.view.answer.lines.length, 'comment')} in the answer</b>`;
  const was = seen();
  const all = flat();
  const ticks = all.map((x) => `<u class="${isDone(x, was) ? 'd' : x.id === S.sel ? 'c' : ''}"></u>`).join('');
  return `<b>${all.filter((x) => isDone(x, was)).length} of ${all.length} looked at</b><div class="ticks">${ticks}</div>`;
}

function whyList() {
  const v = S.view;
  if (v.status.letter === 'C') return v.status.reasons.map((r) => `<li>${esc(r)}</li>`).join('');
  const counts = new Map();
  v.results.filter((r) => !r.dismissed && (r.verdict === 'flag' || r.verdict === 'unclear')).forEach((r) => {
    const k = `${r.verdict === 'flag' ? 'Problem' : 'Question'}: ${r.title}`;
    counts.set(k, (counts.get(k) || 0) + 1);
  });
  const added = v.ai_findings.filter((f) => f.status === 'accepted').length;
  if (added) counts.set('AI suggestion you added to the answer', added);
  return [...counts].map(([k, n]) => `<li>${esc(k)}${n > 1 ? ` (${n})` : ''}</li>`).join('');
}

function drawSteps() {
  const c = S.view.counts;
  const ai = S.view.ai_findings.length;
  const link = (id, label, extra) => `<a href="#/p/${esc(S.pkg)}/${id}" ${S.step === id ? 'aria-current="page"' : ''}>${label}${extra ? `<small>${extra}</small>` : ''}</a>`;
  $('#steps').innerHTML = link('problems', '1 Problems', `${c.problems} ${plural(c.problems, 'problem')}, ${c.questions} ${plural(c.questions, 'question')}${ai ? `, ${ai} AI` : ''}`)
    + link('readings', '2 Confirm readings', c.to_confirm ? `${c.to_confirm} left` : 'all done') + link('answer', '3 Answer');
}

function drawLeft() {
  const el = $('#left');
  const top = el.scrollTop;
  el.innerHTML = S.step === 'readings' ? readingsList() : S.step === 'answer' ? answerSheet() : problemsList();
  el.scrollTop = top;
  S.inked = new Set();
}

// ------------------------------------------------------------------ step 1, the problems
function problemsList() {
  const c = S.view.counts;
  const was = seen();
  const hold = c.to_confirm ? `<p class="hold">Nothing counts until you confirm it. ${c.to_confirm} ${plural(c.to_confirm, 'reading')} are still as the AI left them, so these are what the checks would say.</p>` : '';
  const body = groups().map((g) => {
    const left = g.rows.filter((x) => !isDone(x, was)).length;
    const open = S.groupOpen.has(g.id) ? S.groupOpen.get(g.id) : left > 0 || g.rows.some((x) => x.id === S.sel);
    const state = left === 0 ? `${g.rows.length} looked at` : left === g.rows.length ? `${left} left` : `${g.rows.length - left} looked at, ${left} left`;
    return `<button class="g" data-act="group" data-id="${esc(g.id)}" aria-expanded="${open}"><span>${esc(g.name)}${g.model ? `<span class="typed">${esc(g.model)}</span>` : ''}</span><small>${state}</small></button>
      ${open ? g.rows.map((x) => (x.id === S.sel ? `<div class="sel" id="current">${x.kind === 'ai' ? openAi(x.f) : openResult(x)}</div>` : rowLine(x, was))).join('') : ''}`;
  }).join('');
  return `${hold}${body || '<p class="empty">No problems. Every check passed or is only for information.</p>'}${passedTable()}`;
}

function rowLine(x, was) {
  const done = isDone(x, was);
  const off = x.kind === 'ai' ? x.f.status === 'rejected' : Boolean(x.r.dismissed);
  const title = x.kind === 'ai' ? x.f.title : x.r.title;
  const tag = x.kind === 'ai' ? `<span class="tag ai">${{ suggested: 'AI, not decided', accepted: 'AI, in my answer', rejected: 'AI, not relevant' }[x.f.status]}</span>`
    : x.r.dismissed ? '<span class="tag">Not a problem</span>' : x.r.verdict === 'unclear' ? '<span class="tag q">Question</span>' : '';
  return `<button class="r ${off ? 'off' : ''}" data-act="select" data-id="${esc(x.id)}"><span class="box ${done ? 'y' : ''}">${done ? icon('check') : ''}</span><span class="t">${esc(title)}</span>${tag}</button>`;
}

function shown(value, unit) {
  if (value === true) return 'yes';
  if (value === false) return 'no';
  return `${value}${unit ? ` ${unit}` : ''}`;
}

function typed(value, unit, ok, key) {
  if (value == null || value === '') return '<span class="typed none">not found</span>';
  const text = shown(value, unit);
  const inking = S.inked.has(key);
  return `<span class="typed"><span class="${ok ? 'co' : 'un'}${inking ? ' inking' : ''}"${inking ? ` data-text="${esc(text)}"` : ''}>${esc(text)}</span></span>`;
}

function tick(target, key, ok, label) {
  return `<input type="checkbox" data-target="${esc(JSON.stringify(target))}" data-key="${esc(key)}" ${ok ? 'checked' : ''} aria-label="${esc(label)}" title="Correct">`;
}

function pageLink(file, page) {
  if (!docOf(file)) return '<span class="goto">form</span>';
  return `<button class="link goto" data-act="goto" data-no="${docOf(file).no}" data-page="${esc(page ?? 1)}">p. ${esc(page ?? 1)}</button>`;
}

function plainReason(text) {
  return text.replace(/^CL-\d+\s+/, '').replace(/\s*\(register [^)]*\)/g, '').replace(/([a-z])_([a-z])/g, '$1 $2');
}

function openResult(x) {
  const r = x.r;
  const d = r.doc ? docOf(r.doc) : null;
  const docLine = d ? `<div class="f"><span class="lab">Read as</span><span class="typed"><span class="${d.status === 'verified' ? 'co' : 'un'}">${esc(d.type)}${d.covers.length ? `, covers ${esc(d.covers.join('; '))}` : ''}</span></span>
    ${pageLink(d.file, 1)}${tick({ kind: 'document', file: d.file }, `doc|${d.file}`, d.status === 'verified', `${d.file} is read correctly`)}</div>` : '';
  const lines = r.evidence.map((e) => `<div class="f"><span class="lab">${esc(e.what)}</span>${typed(e.value, e.unit, e.status === 'verified', `${e.item}|${e.key}`)}${pageLink(e.source, e.page)}
    ${tick({ kind: 'value', item: e.item, key: e.key }, `${e.item}|${e.key}`, e.status === 'verified', `${e.what} is correct`)}</div>`).join('');
  const rules = r.rules.map((u) => `<dt>Rule</dt><dd>${esc(u.text)}${u.source ? ` (${esc(u.source)})` : ''}; ${RULE_STATUS[u.status] || esc(u.status.replace(/_/g, ' '))}.${u.url ? ` <a href="${esc(u.url)}" target="_blank" rel="noopener">Open the text</a>` : ''}</dd>`).join('');
  const why = `<details class="why"><summary>Why this was raised</summary><p>${linkify(plainReason(r.reason), MAKER)}</p>${rules ? `<dl>${rules}</dl>` : ''}</details>`;
  let actions;
  if (r.dismissed) {
    actions = `<p class="gone">You marked this as not a problem: ${esc(r.dismissed)}. It is left out of the answer.</p>
      <div class="btns"><button class="btn" data-act="undismiss">Put it back in the answer</button><button class="btn nx" data-act="next">Next ${icon('next')}</button></div>`;
  } else if (S.reasonFor === x.id) {
    actions = `<div class="reason-box"><label for="reason">Why is it not a problem? The reason goes into the export, not into the answer.</label>
      <textarea id="reason" placeholder="For example: agreed with the client at the site meeting"></textarea>
      <div class="btns"><button class="btn p" data-act="dismiss">Mark as not a problem</button><button class="link" data-act="cancel-reason">Cancel</button></div></div>`;
  } else {
    actions = `<div class="btns"><button class="btn p" data-act="keep" aria-label="Keep in the answer"><span>Keep<span class="more"> in the answer</span></span></button><button class="btn" data-act="ask-reason">Not a problem</button>
      <button class="btn nx" data-act="next">Next ${icon('next')}</button></div>`;
  }
  return `<h2>${esc(r.title)}</h2><p class="say">${linkify(r.comment || plainReason(r.reason), MAKER)}</p>${docLine}${lines}${actions}${why}`;
}

function openAi(f) {
  const lines = f.evidence.map((e) => `<div class="f"><span class="lab">Quoted by the AI</span><span class="typed"><span class="un">${esc(e.quote)}</span></span>${pageLink(e.source, e.page)}<span></span></div>`).join('');
  const options = [['accepted', 'Add to my answer'], ['rejected', 'Not relevant'], ['suggested', 'Decide later']];
  return `<h2>${esc(f.title)}</h2><p class="say">${esc(f.finding)}</p>${lines}
    <p class="f-note" style="padding-top:8px">AI suggestion. No rule checks this and it changes no check result. It goes into the answer only if you add it.</p>
    <div class="f-note">Comment it would add: ${esc(f.suggested_comment)}</div>
    <div class="btns"><div class="seg" role="radiogroup" aria-label="Your decision">${options.map(([s, t]) => `<button role="radio" aria-checked="${f.status === s}" data-act="decide" data-id="${esc(f.id)}" data-status="${s}">${t}</button>`).join('')}</div>
      <button class="btn nx" data-act="next">Next ${icon('next')}</button></div>
    ${f.status === 'rejected' ? `<div class="reason-box"><label for="ai-note">Why is it not relevant?</label><textarea id="ai-note" data-note="${esc(f.id)}">${esc(f.note || '')}</textarea></div>` : ''}`;
}

function passedTable() {
  const v = S.view;
  const passed = v.results.filter((r) => !r.dismissed && (r.verdict === 'pass' || r.verdict === 'info'));
  const name = (id) => v.items.find((i) => i.id === id)?.name;
  const word = (r) => (r.verdict === 'info' ? 'Information' : r.confirmed ? 'Passed' : 'Would pass');
  return `<details class="passed"><summary>What passed or is only for information (${passed.length})</summary>
    <table><thead><tr><th>Check</th><th>About</th><th>Result</th><th>Why</th></tr></thead><tbody>
    ${passed.map((r) => `<tr><td>${esc(r.check_name)}</td><td>${esc(name(r.item) || r.doc || 'Package')}</td><td>${word(r)}</td><td>${linkify(plainReason(r.reason), MAKER)}</td></tr>`).join('')}
    </tbody></table></details>`;
}

// ------------------------------------------------------------------ step 2, confirm what the AI read, page by page
function allValues() {
  return S.view.items.flatMap((i) => i.values.map((x) => ({ ...x, item: i.id, product: i.name })));
}

function readingPages() {
  const v = S.view;
  const hasValue = (x) => x.value != null && x.value !== '';
  const values = allValues();
  const pages = v.documents.map((d) => {
    const here = values.filter((x) => x.source === d.file && hasValue(x));
    const numbers = [...new Set([...here.map((x) => Number(x.page)), ...d.matches.map((m) => Number(m.page)).filter(Boolean)])].sort((a, b) => a - b);
    return { d, pages: numbers.map((p) => ({ page: p, values: here.filter((x) => Number(x.page) === p), matches: d.matches.filter((m) => Number(m.page) === p) })),
      loose: d.matches.filter((m) => !m.page) };
  });
  const form = values.filter((x) => hasValue(x) && !docOf(x.source));
  const missing = values.filter((x) => !hasValue(x));
  return { pages, form, missing };
}

function firstReadingPage() {
  const { pages } = readingPages();
  const open = (p) => p.values.some((x) => x.status !== 'verified') || p.matches.some((m) => m.status !== 'verified');
  for (const g of pages) {
    const p = g.pages.find(open);
    if (p) { S.readAt = { no: g.d.no, page: p.page }; return; }
  }
  const g = pages.find((x) => x.pages.length);
  S.readAt = g ? { no: g.d.no, page: g.pages[0].page } : null;
}

function valueLine(x) {
  const key = `${x.item}|${x.key}`;
  const ok = x.status === 'verified';
  const by = ok ? `<span class="by">${esc(x.checked_by || 'reviewer')}${x.verified_on ? `, ${dmy(x.verified_on)}` : ''}</span>` : '';
  return `<div class="v">${tick({ kind: 'value', item: x.item, key: x.key }, key, ok, `${x.what} is correct`)}
    <span>${esc(x.what)}<small>${esc(x.product)}</small></span><span>${typed(x.value, x.unit, ok, key)}${by}</span></div>`;
}

function matchLine(d, m) {
  const key = `match|${d.file}|${m.item}`;
  const name = S.view.items.find((i) => i.id === m.item)?.name || 'Package';
  return `<div class="v">${tick({ kind: 'match', file: d.file, item: m.item }, key, m.status === 'verified', `This document covers ${name}`)}
    <span>Covers this product<small>${esc(name)}</small></span><span class="typed"><span class="${m.status === 'verified' ? 'co' : 'un'}">${esc(m.kind)}</span></span></div>`;
}

function readingsList() {
  const c = S.view.counts;
  const { pages, form, missing } = readingPages();
  const at = S.readAt;
  const lead = `<p class="hold">Check each line against the page on the right and tick it. Unticked lines stay as the AI read them, and every check that rests on them stays a question.</p>`;
  const docs = pages.map((g) => {
    const d = g.d;
    const docTick = `<div class="v">${tick({ kind: 'document', file: d.file }, `doc|${d.file}`, d.status === 'verified', `${d.file} is what it says`)}
      <span>What this document is<small>Listed in the form as ${esc(d.listed_as || 'not listed')}</small></span><span class="typed"><span class="${d.status === 'verified' ? 'co' : 'un'}">${esc(d.type)}</span></span></div>`;
    const body = g.pages.map((p) => {
      const on = at && at.no === d.no && at.page === p.page;
      const lines = [...p.values.map(valueLine), ...p.matches.map((m) => matchLine(d, m))];
      const open = p.values.filter((x) => x.status !== 'verified').length + p.matches.filter((m) => m.status !== 'verified').length;
      return `<div class="pgh ${on ? 'on' : ''}"><button class="link" data-act="read-page" data-no="${d.no}" data-page="${p.page}">Page ${p.page}</button>
        ${open > 1 ? `<button class="link all" data-act="confirm-page" data-no="${d.no}" data-page="${p.page}">Confirm all ${open} on this page</button>` : ''}</div>${lines.join('')}`;
    }).join('');
    return `<div class="dg"><b>${pad(d.no)} · ${breakable(d.file)}</b><span>${esc(d.type)} · ${d.pages} ${plural(d.pages, 'page')}</span></div>${docTick}${g.loose.map((m) => matchLine(d, m)).join('')}${body}`;
  }).join('');
  const fromForm = form.length ? `<div class="dg"><b>From the form</b><span>The MAF form is a spreadsheet, so it has no page to show</span></div>${form.map(valueLine).join('')}` : '';
  const notFound = missing.length ? `<div class="dg"><b>Not found in the documents</b><span>Tick when you agree the package does not state it</span></div>${missing.map(valueLine).join('')}` : '';
  return `${c.to_confirm ? lead : ''}${docs}${fromForm}${notFound}`;
}

// ------------------------------------------------------------------ step 3, the answer
function answerSheet() {
  const v = S.view;
  return `<article class="letter-sheet" aria-label="Answer to send"><div class="lh"><h2>MAF ${esc(v.form.form_no)} rev ${esc(v.form.revision)}: ${esc(v.status.label)} (${v.status.letter})</h2><button class="btn p" data-act="copy">${icon('copy')}Copy the answer</button></div>
      ${v.answer.lines.length ? `<ol>${v.answer.lines.map((line) => `<li>${linkify(line)}</li>`).join('')}</ol>` : '<p class="empty">No comments.</p>'}
      <p class="sign">Drafted by RightFit from the checks and your decisions. You check it and you sign it; the tool certifies nothing.</p></article>
    <div class="exports"><button class="btn" data-act="dl-answer">${icon('save')}Download the answer</button>
      <button class="btn" data-act="dl-values">${icon('save')}Confirmed values</button><button class="btn" data-act="dl-off">${icon('save')}What I marked not a problem</button></div>`;
}

function checkedCard() {
  const v = S.view;
  const c = v.counts;
  const place = S.location === 'ES' ? 'Spain' : 'Romania';
  const open = [...new Set(v.results.filter((r) => r.verdict === 'unclear').map((r) => plainReason(r.reason)))];
  const used = new Map(v.results.flatMap((r) => r.rules).map((u) => [u.id, u.status]));
  const legal = [...used.values()].filter((s) => ['verified_official', 'verified_secondary', 'to_confirm'].includes(s));
  const official = legal.filter((s) => s === 'verified_official').length;
  return `<div class="card"><h2>What RightFit checked</h2>
    <p>The documents, the values and the reviewers' checklist, against EU rules and the rules for ${place}. ${official} of the ${legal.length} legal rules used here ${official === 1 ? 'was' : 'were'} read in the official text, so this is not a statement of compliance. <a href="#/rules">See the rules</a></p>
    <p>Certificates were checked for ${dmy(S.review)}, the review date, and for ${dmy(S.delivery)}, the expected delivery.</p>
    <h3>The result</h3><ul><li>${c.passed} passed on values you confirmed</li><li>${c.would_pass} would pass once you confirm the readings</li><li>${c.problems} ${plural(c.problems, 'problem')}</li><li>${c.questions} ${plural(c.questions, 'question')}</li></ul>
    ${open.length ? `<h3>What it could not check</h3><ul>${open.map((t) => `<li>${esc(t)}</li>`).join('')}</ul>` : ''}
    <details><summary>Change the country or the dates</summary>
      <p style="margin-top:8px">The country decides which national rules apply. The dates decide whether a certificate is still valid at the review and at delivery.</p>
      <label>Country<select id="location">${[['RO', 'Romania'], ['ES', 'Spain']].map(([k, n]) => `<option value="${k}" ${S.location === k ? 'selected' : ''}>${n}</option>`).join('')}</select></label>
      <label>Review date<input type="date" id="review" value="${esc(S.review || '')}"></label>
      <label>Expected delivery<input type="date" id="delivery" value="${esc(S.delivery || '')}"></label></details></div>`;
}

// ------------------------------------------------------------------ the document beside the work
function noDocCard() {
  return `<div class="card"><p>${current() ? 'This package has no documents to show.' : 'Pick a problem to see its page.'}</p></div>`;
}

// One line above the page when a problem has no page of its own: what the form says, or where the missing document is.
function noPageNote(row) {
  const evidence = row.kind === 'ai' ? row.f.evidence : row.r.evidence;
  const quotes = [...new Map(evidence.filter((e) => e.quote).map((e) => [e.quote, e])).values()];
  if (quotes.length) {
    return `From the form, a spreadsheet with no page to show: ${quotes.map((e) => `<span class="typed"><span class="${e.status === 'verified' ? 'co' : 'un'}">${esc(e.quote)}</span></span>`).join('; ')}`;
  }
  const url = /https?:\/\/[^\s)]+/.exec(row.kind === 'ai' ? row.f.finding : row.r.reason)?.[0];
  return `No page in this package shows this, so the product's data sheet is open.${url ? ` <a href="${esc(url)}" target="_blank" rel="noopener">Open the manufacturer's copy</a>` : ''}`;
}

function drawRight() {
  const el = $('#right');
  if (S.step === 'answer') { S.shown = 'answer'; el.innerHTML = checkedCard(); return; }
  const d = currentDoc();
  if (!d) { S.shown = ''; el.innerHTML = noDocCard(); return; }
  const key = `${d.no}|${S.page}|${S.big}`;
  if (S.shown !== key) {
    S.shown = key;
    el.innerHTML = `<div class="dh"><select id="doc-pick" aria-label="Document">${S.view.documents.map((x) => `<option value="${x.no}" ${x.no === d.no ? 'selected' : ''}>${pad(x.no)} · ${esc(x.type)} · ${esc(x.file)}</option>`).join('')}</select>
        <span class="pg"><button class="mini" data-act="page" data-by="-1" ${S.page <= 1 ? 'disabled' : ''} aria-label="Previous page">${icon('left')}</button>Page ${S.page} of ${d.pages}
          <button class="mini" data-act="page" data-by="1" ${S.page >= d.pages ? 'disabled' : ''} aria-label="Next page">${icon('right')}</button>
          <button class="mini" data-act="zoom" aria-pressed="${S.big}" aria-label="Zoom the page">${icon('zoom')}</button>
          <a class="mini" href="/doc/${encodeURIComponent(S.pkg)}/${d.no}#page=${S.page}" target="_blank" rel="noopener">${icon('open')}Open PDF</a></span></div>
      <div class="doc-scroll" id="doc-scroll"><p class="scan plain" id="nopage" hidden></p><p class="scan" id="scan" hidden></p><div class="page ${S.big ? 'big' : ''}"><img src="/page/${encodeURIComponent(S.pkg)}/${d.no}/${S.page}.png" alt="Page ${S.page} of ${esc(d.file)}"><div id="marks"></div></div></div>`;
  }
  const row = S.step === 'problems' ? current() : null;
  const note = $('#nopage');
  note.hidden = !row || Boolean(ownPlace(row));
  if (!note.hidden) note.innerHTML = noPageNote(row);
  loadMarks(d);
}

function marksWanted(d) {
  const samePage = (x) => String(x.page) === String(S.page) && x.quote;
  if (S.step === 'readings') {
    return [...allValues().filter((x) => x.source === d.file && samePage(x)).map((x) => ({ quote: x.quote, ok: x.status === 'verified' })),
      ...d.matches.filter(samePage).map((m) => ({ quote: m.quote, ok: m.status === 'verified' }))];
  }
  const row = current();
  if (!row) return [];
  return (row.kind === 'ai' ? row.f.evidence : row.r.evidence).filter((e) => e.source === d.file && samePage(e))
    .map((e) => ({ quote: e.quote, ok: e.status === 'verified' }));
}

// Draws the marks over the page. A slower answer for a page the reviewer has already left is ignored.
async function loadMarks(d) {
  const wanted = marksWanted(d);
  const run = ++S.marksRun;
  const box = $('#marks');
  const scan = $('#scan');
  if (!wanted.length) { box.innerHTML = ''; scan.hidden = true; return; }
  let marks;
  try {
    ({ marks } = await api('/api/marks', { package: S.pkg, no: d.no, page: S.page, quotes: wanted.map((w) => w.quote) }));
  } catch { return; }
  if (run !== S.marksRun || !$('#marks')) return;
  box.innerHTML = marks.flatMap((rects, i) => rects.map(([x, y, w, h]) => `<i class="m ${wanted[i].ok ? 'ok' : ''}" style="left:${x}%;top:${y}%;width:${w}%;height:${h}%"></i>`)).join('');
  const none = wanted.filter((_, i) => !marks[i].length);
  scan.hidden = !none.length;
  if (none.length) scan.textContent = `${marks.some((m) => m.length) ? 'Some lines could not be marked' : 'This page is a scan, so the line cannot be marked'}. Look for: ${none.map((w) => `"${w.quote}"`).join('; ')}`;
  const first = box.querySelector('.m');
  const scroller = $('#doc-scroll');
  if (first && scroller && window.matchMedia('(min-width: 761px)').matches) {
    await $('.page img', scroller).decode().catch(() => {});
    const mark = first.getBoundingClientRect();
    const pane = scroller.getBoundingClientRect();
    scroller.scrollTo({ top: scroller.scrollTop + mark.top - pane.top - pane.height * 0.32, left: scroller.scrollLeft + mark.left - pane.left - 16 });
  }
}

// ------------------------------------------------------------------ what the reviewer does
function select(id) {
  S.sel = id;
  S.reasonFor = null;
  const row = current();
  showPlace(row ? placeOf(row) : null);
  drawHead();
  drawLeft();
  drawRight();
  $('#current')?.scrollIntoView({ block: 'center' });
}

function advance() {
  const was = seen();
  const all = flat();
  const at = all.findIndex((x) => x.id === S.sel);
  const next = [...all.slice(at + 1), ...all.slice(0, Math.max(at, 0))].find((x) => !isDone(x, was));
  if (next) { select(next.id); return; }
  drawHead();
  drawLeft();
  toast('Everything has been looked at. Next: confirm the readings.');
}

async function confirmTargets(targets, keys) {
  if (!(await refresh('/api/confirm', { targets }))) { toast(S.error); drawLeft(); return; }
  S.inked = new Set(keys);
  drawHead();
  drawSteps();
  drawLeft();
  const d = currentDoc();
  if (d && S.step !== 'answer') loadMarks(d);
}

async function onClick(ev) {
  const el = ev.target.closest('[data-act]');
  if (!el) return;
  const a = el.dataset.act;
  if (a === 'select') select(el.dataset.id);
  else if (a === 'group') {
    const open = el.getAttribute('aria-expanded') === 'true';
    S.groupOpen.set(el.dataset.id, !open);
    drawLeft();
  } else if (a === 'keep') { markSeen(S.sel); advance(); }
  else if (a === 'next') advance();
  else if (a === 'ask-reason') { S.reasonFor = S.sel; drawLeft(); $('#reason')?.focus(); }
  else if (a === 'cancel-reason') { S.reasonFor = null; drawLeft(); }
  else if (a === 'dismiss') {
    const reason = $('#reason').value.trim() || 'no reason given';
    store.write(`rightfit.dismissed.${S.pkg}`, { ...dismissed(), [S.sel]: reason });
    const at = S.sel;
    S.reasonFor = null;
    if (await refresh()) {
      toast('Marked as not a problem. It is out of the answer.');
      drawSteps();
      if (S.sel === at) advance(); else { drawHead(); drawLeft(); }   // the reviewer has already moved on
    }
  } else if (a === 'undismiss') {
    const map = dismissed();
    delete map[S.sel];
    store.write(`rightfit.dismissed.${S.pkg}`, map);
    if (await refresh()) { toast('Back in the answer.'); drawHead(); drawSteps(); drawLeft(); }
  } else if (a === 'decide') {
    const { status, id } = el.dataset;
    if (await refresh('/api/decide', { id, status })) {
      toast({ accepted: 'Added to your answer.', rejected: 'Marked not relevant.', suggested: 'Back to not decided.' }[status]);
      drawHead();
      drawSteps();
      drawLeft();
    }
  } else if (a === 'goto') { S.doc = Number(el.dataset.no); S.page = Number(el.dataset.page) || 1; drawRight(); }
  else if (a === 'page') { S.page += Number(el.dataset.by); drawRight(); }
  else if (a === 'zoom') { S.big = !S.big; drawRight(); }
  else if (a === 'read-page') {
    S.readAt = { no: Number(el.dataset.no), page: Number(el.dataset.page) };
    showPlace(S.readAt);
    drawLeft();
    drawRight();
  } else if (a === 'confirm-page') {
    const no = Number(el.dataset.no);
    const page = Number(el.dataset.page);
    const d = S.view.documents.find((x) => x.no === no);
    const values = allValues().filter((x) => x.source === d.file && Number(x.page) === page && x.status !== 'verified' && x.value != null && x.value !== '');
    const matches = d.matches.filter((m) => Number(m.page) === page && m.status !== 'verified');
    await confirmTargets([...values.map((x) => ({ kind: 'value', item: x.item, key: x.key, verified: true })),
      ...matches.map((m) => ({ kind: 'match', file: d.file, item: m.item, verified: true }))], values.map((x) => `${x.item}|${x.key}`));
  } else if (a === 'copy') {
    try { await navigator.clipboard.writeText(S.view.answer.text); toast('Answer copied.'); } catch { toast('Could not copy here. Use Download the answer.'); }
  } else if (a === 'dl-answer') download(`${S.pkg}_answer.txt`, S.view.answer.text);
  else if (a === 'dl-values') {
    download(`${S.pkg}_confirmed_values.csv`, csv([['item', 'value', 'reading', 'unit', 'file', 'page'], ...S.view.items.flatMap((i) => i.values
      .filter((x) => x.status === 'verified').map((x) => [`${i.name} (${i.model})`, x.what, x.value, x.unit, x.source, x.page]))]));
  } else if (a === 'dl-off') {
    download(`${S.pkg}_not_a_problem.csv`, csv([['check', 'about', 'why'], ...S.view.results.filter((r) => r.dismissed).map((r) => [r.check, r.product || r.doc || 'package', r.dismissed])]));
  }
}

async function onChange(ev) {
  const t = ev.target;
  if (t.dataset.target) {
    const target = JSON.parse(t.dataset.target);
    await confirmTargets([{ ...target, verified: t.checked }], t.checked ? [t.dataset.key] : []);
  } else if (t.id === 'doc-pick') { S.doc = Number(t.value); S.page = 1; drawRight(); }
  else if (t.dataset.note) {
    if (await refresh('/api/decide', { id: t.dataset.note, status: 'rejected', note: t.value.trim() })) toast('Reason saved.');
  } else if (t.id === 'location' || t.id === 'review' || t.id === 'delivery') {
    S[t.id] = t.value || null;
    if (await refresh()) { S.shown = ''; drawAll(); }
    else toast(S.error);
  }
}

// The arrow keys move through the list while the reviewer's hands are not in a field.
document.addEventListener('keydown', (ev) => {
  if (!S.active || S.step !== 'problems' || !['ArrowDown', 'ArrowUp'].includes(ev.key)) return;
  if (ev.target.closest('input, textarea, select, details')) return;
  const all = flat();
  const at = all.findIndex((x) => x.id === S.sel);
  const next = all[at + (ev.key === 'ArrowDown' ? 1 : -1)];
  if (next) { ev.preventDefault(); select(next.id); }
});
