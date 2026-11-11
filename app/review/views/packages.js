// Every package: the ones RightFit has read open for review, the others wait until the reader has been through them.
import { $, api, esc, plural } from '../lib.js';

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
    ${shown.length ? '' : '<p class="empty">No package matches.</p>'}`;
}

export async function render(root) {
  root.innerHTML = `<div class="screen"><div class="screen-head"><h1>Packages</h1><a class="btn p" href="#/add">Add a package</a></div>
    <div class="tools"><input type="search" id="find" placeholder="Find a form or a product" aria-label="Find a form or a product" value="${esc(filter.text)}"><select id="discipline" aria-label="Discipline"></select></div>
    <div id="tables"><p class="empty">Loading…</p></div></div>`;
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
}
