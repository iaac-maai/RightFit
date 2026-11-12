// The rules RightFit checks. The consultant's own rules come first: typed in words, proposed by the AI as a plain
// sentence, saved only when the consultant says so. The rules of the law follow, each with its source.
import { $, api, dmy, esc, toast } from '../lib.js';

const STATUS = {
  verified_official: 'Read in the official journal',
  verified_secondary: 'Read in a copy, to check on the official text',
  to_confirm: 'To confirm on the official text',
  practice: "Reviewers' practice",
  engineer_input: "Set by the team's engineer",
  guidance: "Manufacturer's recommendation",
};
const EXAMPLES = ['Pumps only from Grundfos', 'Balancing valves only from IMI or Danfoss', 'Circulation pumps come with a control panel',
  'Pumps rated at least PN 16', 'Every product comes with a warranty certificate'];
const EFFECTS = { B: 'a comment (B)', C: 'revise and resubmit (C)', info: 'information only' };
const OPS = { '>=': 'at least', '<=': 'at most', '=': '' };
const FAMILIES = { all: 'Every product', pump: 'Pumps', ahu: 'Air handling units', outdoor_unit: 'Outdoor units', dx_kit: 'DX kits' };
let location = 'RO';
let info = null;     // the consultant's rules and the words the form needs
let proposal = null; // the AI's proposal, not saved yet

const today = new Date().toISOString().slice(0, 10);
const when = (r) => (r.valid_to ? `until ${dmy(r.valid_to)}` : r.valid_from > today ? `from ${dmy(r.valid_from)}` : '');
const words = (s) => (s || '').replace(/;/g, ', ').replace(/\|/g, ' or ').replace(/_/g, ' ');
const reading = (k) => k.split('|').map((x) => (info?.values[x] || words(x)).replace(/ \((form|data sheet)\)$/, '').replace(/\s*included$/i, '')).join(' or ');

// A rule as one sentence: who it applies to, what it checks, what happens if it is not met.
function sentence(r) {
  const who = FAMILIES[r.family] || words(r.family).replace(/^./, (c) => c.toUpperCase());
  const use = r.application ? ` used for ${words(r.application)}` : '';
  const what = {
    brand: `the brand is ${(r.value || '').split(';').map((b) => b.trim()).filter(Boolean).join(' or ')}`,
    value: `${reading(r.field || '')} is ${OPS[r.operator] ?? ''} ${r.value} ${r.unit}`.replace(/\s+/g, ' '),
    document: `a ${info?.doc_types[r.field] || words(r.field)} is attached`,
    included: `${reading(r.field || '').toLowerCase()} is included`,
    reminder: `check by hand: ${r.text}`,
  }[r.kind] || r.text;
  return `<b>${esc(who)}</b>${esc(use)}: ${esc(what)}. <span class="sub">If not: ${esc(EFFECTS[r.effect] || r.effect)}.</span>`;
}

function drawLaw(rules) {
  $('#law-table').innerHTML = `<table><thead><tr><th>What it asks</th><th>Source</th><th>Applies to</th><th>Where it stands</th></tr></thead><tbody>
    ${rules.map((r) => `<tr><td>${esc(r.requirement)}</td><td>${r.source_url ? `<a href="${esc(r.source_url)}" target="_blank" rel="noopener">${esc(r.code)}</a>` : esc(r.code)}${r.clause ? `, ${esc(r.clause)}` : ''}${when(r) ? `<span class="sub">Applies ${when(r)}</span>` : ''}</td>
      <td>${esc(words(r.applies_to))}</td><td>${esc(STATUS[r.status] || r.status)}</td></tr>`).join('')}</tbody></table>`;
}

async function law() {
  try { drawLaw(await api(`/api/rules?location=${location}`)); } catch (e) { $('#law-table').innerHTML = `<p class="error" role="alert">${esc(e.message)}</p>`; }
}

function drawMine() {
  const list = $('#my-rules');
  if (!list?.isConnected) return;
  list.innerHTML = info.rules.length ? info.rules.map((r) => `<li class="${r.active === 'yes' ? '' : 'off'}">
      <label class="switch"><input type="checkbox" data-rule="${esc(r.rule_id)}" ${r.active === 'yes' ? 'checked' : ''}><span aria-hidden="true"></span><span class="sr">Rule ${esc(r.rule_id)} on</span></label>
      <div>${sentence(r)}<span class="sub">${esc(r.rule_id)} · ${esc(r.source)}</span></div></li>`).join('')
    : '<li class="empty">No rules of your own yet. Write one above.</li>';
}

function drawProposal() {
  const box = $('#proposal');
  box.hidden = !proposal;
  if (!proposal) return;
  box.innerHTML = `<span class="tag ai">AI proposal, check it before you save it</span>
    <p class="said">${sentence(proposal)}</p>
    <div class="btns"><button class="btn p" id="save">Save rule</button><button class="btn" id="change">Change it</button><button class="btn" id="drop">Discard</button></div>`;
  $('#save').onclick = () => save(proposal);
  $('#change').onclick = () => { fillForm(proposal); $('#by-hand').open = true; $('#by-hand').scrollIntoView({ behavior: 'smooth', block: 'center' }); };
  $('#drop').onclick = () => { proposal = null; drawProposal(); };
}

async function propose(text) {
  const words = text.trim();
  if (words.length < 3) return;
  const go = $('#go');
  go.disabled = true;
  go.innerHTML = '<i class="spin"></i> Reading your rule…';
  try {
    proposal = (await api('/api/consultant-rules/draft', { words })).rule;
    drawProposal();
  } catch (e) {
    toast(e.message);
    $('#by-hand').open = true;
  } finally {
    go.disabled = false;
    go.textContent = 'Turn into a rule';
  }
}

async function save(rule) {
  try {
    info = await api('/api/consultant-rules', rule);
    proposal = null;
    drawProposal();
    drawMine();
    $('#words').value = '';
    toast('Saved. It applies to every package from now on.');
  } catch (e) { toast(e.message); }
}

// The same rule by hand, for when there is no AI or the proposal needs changing.
function fieldOptions(kind) {
  if (kind === 'document') return Object.entries(info.doc_types).map(([k, v]) => `<option value="${esc(k)}">${esc(v)}</option>`).join('');
  if (kind === 'included') return ['controller_included', 'bms_included', 'float_switch', 'controller_included|float_switch'].map((k) => `<option value="${k}">${esc(reading(k))}</option>`).join('');
  return Object.entries(info.values).map(([k, v]) => `<option value="${esc(k)}">${esc(v)}</option>`).join('');
}

function showFields() {
  const form = $('#hand');
  const kind = form.kind.value;
  form.querySelectorAll('[data-for]').forEach((el) => { el.hidden = !el.dataset.for.split(' ').includes(kind); });
  const keep = form.field.value;
  form.field.innerHTML = fieldOptions(kind);
  if ([...form.field.options].some((o) => o.value === keep)) form.field.value = keep;
}

function fillForm(r) {
  const form = $('#hand');
  form.kind.value = r.kind;
  showFields();
  for (const k of ['family', 'application', 'field', 'operator', 'value', 'unit', 'effect', 'text']) {
    if (!form[k]) continue;
    if (form[k].tagName === 'SELECT' && r[k] && ![...form[k].options].some((o) => o.value === r[k])) form[k].add(new Option(words(r[k]), r[k]));
    form[k].value = r[k] ?? '';
  }
}

function drawForm() {
  $('#by-hand').innerHTML = `<summary>Write it by hand instead</summary>
    <form id="hand" class="hand">
      <label>Products <select name="family"><option value="all">every product</option>${info.families.map((f) => `<option value="${esc(f)}">${esc(words(f))}</option>`).join('')}</select></label>
      <label>Only when used for <input name="application" placeholder="optional, e.g. circulation"></label>
      <label>What it checks <select name="kind"><option value="brand">the brand</option><option value="value">a value</option><option value="document">a document</option><option value="included">that something is included</option><option value="reminder">something to check by hand</option></select></label>
      <label data-for="value document included">Which <select name="field"></select></label>
      <label data-for="value">Must be <select name="operator"><option value=">=">at least</option><option value="<=">at most</option><option value="=">exactly</option></select></label>
      <label data-for="brand value">${'Value'} <input name="value" placeholder="Grundfos;Wilo or 16"></label>
      <label data-for="value">Unit <input name="unit" placeholder="bar"></label>
      <label>If not met <select name="effect">${Object.entries(EFFECTS).map(([k, v]) => `<option value="${k}">${v}</option>`).join('')}</select></label>
      <label class="wide">In a few words <input name="text" required maxlength="200" placeholder="pumps only from Grundfos"></label>
      <button class="btn p" type="submit">Save rule</button>
    </form>`;
  const form = $('#hand');
  form.kind.addEventListener('change', showFields);
  showFields();
  form.addEventListener('submit', (ev) => { ev.preventDefault(); save(Object.fromEntries(new FormData(form))); });
}

export async function render(root) {
  root.innerHTML = `<div class="screen rules"><div class="screen-head"><h1>Rules</h1>
      <p>RightFit checks the law, the reviewers' checklist and your own rules. Your rules are preferences: the answer says "the consultant asks", never that the law asks.</p></div>
    <section class="rule-add">
      <h2>Add a rule of your own</h2>
      <form id="ask" class="ask"><input id="words" maxlength="300" placeholder="Say it in your own words, e.g. pumps only from Grundfos" aria-label="Your rule in your own words" autocomplete="off">
        <button class="btn p" id="go" type="submit">Turn into a rule</button></form>
      <div class="examples">${EXAMPLES.map((x) => `<button type="button" class="ex">${esc(x)}</button>`).join('')}</div>
      <div id="proposal" class="proposal" hidden aria-live="polite"></div>
      <details id="by-hand"></details>
    </section>
    <h2 class="section-h">Your rules</h2>
    <ul id="my-rules" class="my-rules"><li class="empty">Loading…</li></ul>
    <h2 class="section-h">Rules of the law and the checklist</h2>
    <div class="tools"><select id="country" aria-label="Country"><option value="RO" ${location === 'RO' ? 'selected' : ''}>Romania</option><option value="ES" ${location === 'ES' ? 'selected' : ''}>Spain</option></select>
      <span class="sub">A rule not read in the official text is not presented as a legal requirement.</span></div>
    <div id="law-table"><p class="empty">Loading…</p></div></div>`;
  $('#ask').addEventListener('submit', (ev) => { ev.preventDefault(); propose($('#words').value); });
  root.querySelectorAll('.ex').forEach((b) => b.addEventListener('click', () => { $('#words').value = b.textContent; propose(b.textContent); }));
  $('#country').addEventListener('change', (ev) => { location = ev.target.value; law(); });
  $('#my-rules').addEventListener('change', async (ev) => {
    const cb = ev.target.closest('[data-rule]');
    if (!cb) return;
    try { info = await api('/api/consultant-rules/active', { rule_id: cb.dataset.rule, active: cb.checked }); drawMine(); } catch (e) { toast(e.message); }
  });
  law();
  try {
    info = await api('/api/consultant-rules');
  } catch (e) {
    $('#my-rules').innerHTML = `<li class="error" role="alert">${esc(e.message)}</li>`;
    return;
  }
  if (!root.isConnected) return;
  drawMine();
  drawForm();
}
