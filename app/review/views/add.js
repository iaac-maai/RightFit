// Add a package: the server (app/pump_demo.py) reads the uploaded files page by page and runs the pump checks on what
// they say. The package is every file added so far: files added later are read on their own, then all of it is checked again.
import { $, api, esc, icon, plural, shortName } from '../lib.js';

const LOCAL = 'P01';   // the pump package kept on this laptop
const state = { entries: [], analysis: null, busy: false, waiting: [], refused: [] };
export const analysis = () => state.analysis;
let el = null;   // one element for the life of the page, so a reading goes on while the reviewer looks at another screen

const START = `<div class="drop" id="drop">${icon('up')}<b>Drop the MAF package here</b><button class="btn p" type="button" data-pick>Upload package</button></div>
  <p class="aside"><button class="link" id="local" type="button">Or use the pump package already on this laptop</button></p>`;
const kindOf = (p) => (p.category === 'booster_set' ? 'booster set'
  : (p.pump_type || '').startsWith('submersible_') ? p.pump_type.split('_')[1] : p.category.replace('_', ' '));

function pkgBar(n) {   // the package so far, the button that adds to it, and the files the server refused this time
  return `<div class="pkg"><b>${n} ${plural(n, 'file')} in this package</b><button class="btn" type="button" data-pick>Add documents</button></div>`
    + state.refused.map((r) => `<p class="error" role="alert">${esc(r.name)} was not added. ${esc(r.message)}</p>`).join('');
}

function failed(e) {
  if (e.status === 410) {   // the server was restarted and no longer has the files: the package starts over
    state.entries = [];
    state.analysis = null;
    $('#check-title', el).textContent = 'Add a package';
  }
  const main = $('#check-main', el);
  if (state.analysis) renderCheck(state.analysis);   // keep the last result on screen
  else if (!state.entries.length) main.innerHTML = START;
  else main.insertAdjacentHTML('afterbegin', pkgBar(state.entries.length));
  ($('.pkg', el) || $('#drop', el)).insertAdjacentHTML('afterend', `<p class="error" role="alert">${esc(e.message)}</p>`);
}

function listFiles() {
  $('#viewer', el).hidden = true;
  $('#check-main', el).innerHTML = `<ul class="files" id="flist"></ul>
    <div class="progress" id="progress" hidden><p class="label"><span class="spin" aria-hidden="true"></span><span id="plabel">Reading the package</span></p>
      <div class="track"><div class="fill" id="pfill"></div></div></div>`;
  state.entries.forEach(addFile);   // the files already in the package stay listed
}

function addFile(e, i) {
  $('#flist', el).insertAdjacentHTML('beforeend', `<li id="f${i}"><span class="name">${esc(e.name)}</span>
    <span class="pages">${e.pages == null ? 'not a PDF' : `${e.pages} ${plural(e.pages, 'page')}${e.ocr ? ', OCR' : ''}`}</span>
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
  $('#progress', el).hidden = false;
  $('#plabel', el).textContent = `Reading page 0 of ${total}`;
  for (const e of entries) {
    const row = $(`#f${state.entries.indexOf(e)}`, el);
    try {
      for (let p = 1; p <= (e.pages || 0); p++) {
        $('#plabel', el).textContent = `Reading page ${done + 1} of ${total}${e.ocr ? ', OCR of a scanned page' : ''}`;
        const r = await api('/api/extract', { token: e.token, page: p });
        e.ocr = e.ocr || r.read === 'ocr';
        done += 1;
        $('.bar-in', row).style.width = `${(p / e.pages) * 100}%`;
        $('#pfill', el).style.width = `${(done / total) * 100}%`;
      }
      if (e.ocr) $('.pages', row).textContent = `${e.pages} pages, OCR`;
    } catch (err) {
      if (!err.status) throw err;   // the server is not answering: stop here
      $('.pages', row).textContent = 'not read';   // a locked or damaged file: the check lists it and goes on
    }
    e.done = true;
  }
  $('#plabel', el).textContent = `Read ${done} pages, matching pumps to declarations`;
}

async function addToPackage(adding) {
  if (state.busy) return;
  state.busy = true;
  state.refused = [];
  try {
    listFiles();
    await adding();
    await readPages(state.entries.filter((e) => !e.done));
    const c = await api('/api/analyse', { tokens: state.entries.map((e) => e.token) });
    $('#progress', el).classList.add('done');
    state.analysis = c;
    renderCheck(c);
  } catch (e) {
    failed(e);
  } finally {
    state.busy = false;
    if (state.waiting.length) upload(state.waiting.splice(0));   // files dropped while this package was being read
  }
}

async function upload(fileList) {
  const files = [...fileList];
  if (!files.length) return;
  if (state.busy) {   // still reading: these files are added as soon as it ends
    state.waiting.push(...files);
    $('#flist', el)?.insertAdjacentHTML('afterend', `<p class="note">${esc(files.map((f) => f.name).join(', '))}: added when this reading ends.</p>`);
    return;
  }
  await addToPackage(async () => {
    for (const f of files) {
      try {
        include(await api('/api/upload', f, { 'X-File-Name': encodeURIComponent(f.name) }));
      } catch (err) {
        if (!err.status) throw err;   // the server is not answering: stop here
        state.refused.push({ name: f.name, message: err.message });   // e.g. larger than 60 MB; the other files go on
      }
    }
  });
}

function useLocal() {   // the original files on this laptop, as if they were uploaded
  return addToPackage(async () => (await api('/api/load-local', { package: LOCAL })).forEach(include));
}

function chip(rule) {
  if (!rule) return '';
  const title = rule.detail ? ` title="${esc(rule.detail)}"` : '';
  if (rule.verdict === 'pass') return `<span class="chip pass"${title}>${rule.label ? `${rule.file ? 'Named' : 'Pass'}: ${esc(rule.label)}` : 'Pass'}</span>`;
  if (rule.verdict === 'fail') return `<span class="chip fail"${title}>${rule.label ? `Fail: ${esc(rule.label)}` : 'Not found'}</span>`;
  if (rule.verdict === 'n/a') return `<span class="chip na"${title}>Does not apply: ${esc(rule.label)}</span>`;
  return `<span class="chip unknown"${title}>Unknown: ${esc(rule.label)}</span>`;
}

function renderCheck(c) {
  $('#check-title', el).textContent = c.form ? `MAF ${c.form}, pump package` : 'Pump package';
  const head = pkgBar(c.files.length);
  const unread = c.unread.map((d) => `<p class="also"><b>Not read:</b> ${esc(d.file || d.name)} ${d.names ? 'names no products RightFit can find'
    : esc(d.reason || 'has no text, even by OCR')}. Check it by eye.</p>`).join('');
  const main = $('#check-main', el);
  if (!c.pumps.length) {
    main.innerHTML = `${head}<p class="note">No pump data sheet was found among these files, so there is nothing to check against the declarations.</p>${unread}`;
    return;
  }
  const ok = !c.missing;
  const field = (n, label, bad) => `<div><span class="lab">${label}</span><span class="typed${bad ? ' bad' : ''}">${n}</span></div>`;
  const also = c.unused.map((d) => `<p class="also"><b>Also:</b> the ${esc(d.names.join(', '))} declaration in the package names <b>no submitted pump</b>${d.read === 'OCR' ? ' (read by OCR from a scan)' : ''}.</p>`).join('') + unread;
  main.innerHTML = `${head}
    <div class="banner ${ok ? 'ok' : 'return'}"><b>${ok ? 'Pass' : 'Return'}</b>
      <span>${ok ? 'every pump has a declaration that names it' : `${c.missing} of ${c.pumps.length} pumps have no declaration that names them`}</span></div>
    <div class="fields">${field(c.pages, 'Pages read')}${field(c.pumps.length, 'Pumps found')}${field(c.declarations.length, 'Declarations')}${field(c.missing, 'Pumps not covered', c.missing > 0)}</div>
    <p class="rule-note" title="${esc(c.rule.quote)}">${esc(c.rule.id)}, ${esc(c.rule.source)}: ${esc(c.rule.rule)}</p>
    <table class="pumps"><thead><tr><th>Pump</th><th>Declaration</th><th>Efficiency (MEI)</th><th>Motor (IE)</th></tr></thead>
    <tbody>${c.pumps.map((p, i) => `<tr tabindex="0" data-i="${i}" aria-selected="false">
      <td><span class="model" title="${esc(p.model)}">${esc(shortName(p.model))}</span><span class="sub">${esc(kindOf(p))}, data sheet p. 1</span></td>
      <td>${chip(p.rules['CE-01'])}</td><td>${chip(p.rules['PUMP-MEI'])}</td><td>${chip(p.rules['MOTOR-IE'])}</td></tr>`).join('')}</tbody></table>
    ${also}
    <p class="note">"Does not apply" means the EU efficiency rules do not cover this pump type, so the form is not returned for them.</p>`;
  $('#viewer-body', el).innerHTML = '<p class="blank">Select a pump to see its source page</p>';
  $('#viewer', el).hidden = false;
}

function selectPump(i) {
  const c = state.analysis;
  const p = c.pumps[i];
  el.querySelectorAll('.pumps tbody tr').forEach((tr) => tr.setAttribute('aria-selected', tr.dataset.i === String(i)));
  const ce = p.rules['CE-01'];
  const decl = ce.verdict === 'pass' ? c.declarations.find((d) => d.file === ce.file) : null;
  const token = decl ? decl.token : p.token;
  const page = decl ? decl.page || 1 : 1;
  const file = decl ? decl.file : p.source_file;
  $('#viewer-body', el).innerHTML = `<div><p class="head-l">${esc(file)}, p. ${page}</p>
    <p class="say ${decl ? 'pass' : 'fail'}">${decl ? `Names: ${esc(decl.names.join(', '))}` : 'No declaration in the package names this model'}</p>
    <img src="/upload/${token}/${page}.png" alt="Page ${page} of ${esc(file)}">
    <a class="open" href="/upload/${token}#page=${page}" target="_blank" rel="noopener">${icon('open')}Open the PDF</a></div>`;
}

function build() {
  el = document.createElement('div');
  el.className = 'screen';
  el.id = 'check';
  el.innerHTML = `<div class="screen-head"><h1 id="check-title">Add a package</h1><p>Does every submitted pump have a declaration of conformity that names it? For now this reading covers pumps.</p></div>
    <input type="file" id="files" multiple hidden>
    <div class="split"><div id="check-main">${START}</div>
      <aside class="viewer" id="viewer" hidden><div class="viewer-body" id="viewer-body"></div></aside></div>`;
  const main = $('#check-main', el);
  main.addEventListener('click', (ev) => {
    const tr = ev.target.closest('.pumps tbody tr');
    if (tr) selectPump(Number(tr.dataset.i));
    if (ev.target.closest('[data-pick]')) $('#files', el).click();
    if (ev.target.closest('#local')) useLocal();
  });
  main.addEventListener('keydown', (ev) => {
    const tr = ev.target.closest('.pumps tbody tr');
    if (tr && (ev.key === 'Enter' || ev.key === ' ')) { ev.preventDefault(); selectPump(Number(tr.dataset.i)); }
  });
  $('#files', el).addEventListener('change', (ev) => { upload(ev.target.files); ev.target.value = ''; });   // so the same file can be picked again
  // Files can be dropped anywhere on this screen, before or after the first upload.
  const target = () => $('#drop', el) || main;
  ['dragenter', 'dragover'].forEach((t) => el.addEventListener(t, (ev) => { ev.preventDefault(); target().classList.add('over'); }));
  ['dragleave', 'drop'].forEach((t) => el.addEventListener(t, () => target().classList.remove('over')));
  el.addEventListener('drop', (ev) => { ev.preventDefault(); upload(ev.dataTransfer.files); });
}

export function render(root) {
  if (!el) build();
  root.replaceChildren(el);
}
