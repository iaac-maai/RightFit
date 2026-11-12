// Every package: the ones RightFit has read open for review, the others wait until the reader has been through them.
import { $, api, esc, plural, toast } from '../lib.js';

let all = [];
const filter = { discipline: '', text: '' };

const matches = (p) => (!filter.discipline || p.discipline === filter.discipline)
  && (!filter.text || `${p.id} ${p.form_no} ${p.items.join(' ')}`.toLowerCase().includes(filter.text));

function readRow(p) {
  return `<tr class="go" data-href="#/p/${esc(p.id)}"><td><a href="#/p/${esc(p.id)}">MAF ${esc(p.form_no)}</a></td><td class="typed">rev ${esc(p.revision)}</td>
    <td>${esc(p.items.join(', '))}</td><td>${esc(p.discipline)}</td><td class="num">${p.files}</td><td class="num">${p.pages}</td>
    <td><div class="state"><i class="letter sm ${p.letter}">${p.letter}</i><div>${esc(p.label)}<small>${p.problems} ${plural(p.problems, 'problem')}, ${p.questions} ${plural(p.questions, 'question')}, ${p.readings - p.to_confirm} of ${p.readings} confirmed</small></div></div></td></tr>`;
}

function waitRow(p) {
  return `<tr class="wait"><td>MAF ${esc(p.form_no)}</td><td class="typed">rev ${esc(p.revision)}</td><td>${esc(p.items.join(', '))}</td><td>${esc(p.discipline)}</td>
    <td class="num">${p.files || ''}</td><td class="num">${p.pages || ''}</td><td>${p.files ? 'Not read yet' : 'Files incomplete'}</td></tr>`;
}

const head = (last) => `<colgroup><col style="width:120px"><col style="width:84px"><col><col style="width:110px"><col style="width:64px"><col style="width:64px"><col style="width:270px"></colgroup><thead><tr><th>Form</th><th>Revision</th><th>Products</th><th>Discipline</th><th class="num">Files</th><th class="num">Pages</th><th>${last}</th></tr></thead>`;

function drawTables() {
  const shown = all.filter(matches);
  const ready = shown.filter((p) => p.letter);
  const waiting = shown.filter((p) => !p.letter);
  $('#tables').innerHTML = `${ready.length ? `<h2 class="section-h">Ready to review<small>${ready.length}</small></h2><table class="pk">${head('Draft answer')}<tbody>${ready.map(readRow).join('')}</tbody></table>` : ''}
    ${waiting.length ? `<details class="waiting" ${filter.text || filter.discipline ? 'open' : ''}><summary class="section-h">Not read yet<small>${waiting.length}</small></summary><table class="pk">${head('State')}<tbody>${waiting.map(waitRow).join('')}</tbody></table></details>` : ''}
    ${shown.length ? '' : all.length ? '<p class="empty">No package matches.</p>' : '<p class="empty">No packages in this project yet. <a href="#/add">Add a package</a>, then save it in the project, and add the project\'s BOQs below.</p>'}`;
}

// The project's bills of quantities. RightFit finds each product's line in them and checks what the line asks.
async function drawBoq(files) {
  const box = $('#boq');
  if (!box?.isConnected) return;
  box.innerHTML = `<h2 class="section-h">Bills of quantities<small>${files.length}</small></h2>
    <p class="note">RightFit finds each product's line in the BOQ and checks what that line asks for. Prices stay on this laptop and are never read.</p>
    <ul class="boq-files">${files.map((f) => `<li><b>${esc(f.file)}</b> <span class="sub">${f.lines} lines</span></li>`).join('') || '<li class="empty">No BOQ yet.</li>'}</ul>
    <label class="btn">Add a BOQ (Excel)<input type="file" id="boq-file" accept=".xlsx,.xls" hidden></label>`;
  $('#boq-file').addEventListener('change', async (ev) => {
    const file = ev.target.files[0];
    if (!file) return;
    try {
      await api('/api/boq', await file.arrayBuffer(), { 'X-File-Name': encodeURIComponent(file.name), 'Content-Type': 'application/octet-stream' });
      toast(`${file.name} added. Open a package to see its BOQ lines.`);
      drawBoq(await api('/api/boq'));
    } catch (e) { toast(e.message); }
  });
}

export async function render(root) {
  root.innerHTML = `<div class="screen"><div class="screen-head"><h1>Packages</h1><a class="btn p" href="#/add">Add a package</a></div>
    <div class="tools"><input type="search" id="find" placeholder="Find a form or a product" aria-label="Find a form or a product" value="${esc(filter.text)}"><select id="discipline" aria-label="Discipline"></select></div>
    <div id="tables"><p class="empty">Loading…</p></div><section id="boq"></section></div>`;
  const el = root.firstElementChild;
  el.addEventListener('click', (ev) => {
    const tr = ev.target.closest('tr.go');
    if (tr && !ev.target.closest('a')) window.location.hash = tr.dataset.href;
  });
  el.addEventListener('input', (ev) => {
    if (ev.target.id === 'find') { filter.text = ev.target.value.trim().toLowerCase(); drawTables(); }
  });
  el.addEventListener('change', (ev) => {
    if (ev.target.id === 'discipline') { filter.discipline = ev.target.value; drawTables(); }
  });
  let listing;
  try {
    listing = await api('/api/packages');
  } catch (e) {
    if (el.isConnected) $('#tables').innerHTML = `<p class="error" role="alert">${esc(e.message)}</p>`;
    return;
  }
  if (!el.isConnected) return;   // the reviewer has already gone to another screen
  all = listing;
  const kinds = [...new Set(all.map((p) => p.discipline))].sort();
  $('#discipline').innerHTML = `<option value="">All disciplines</option>${kinds.map((k) => `<option ${k === filter.discipline ? 'selected' : ''}>${esc(k)}</option>`).join('')}`;
  drawTables();
  api('/api/boq').then(drawBoq).catch(() => {});
}
