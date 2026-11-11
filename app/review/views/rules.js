// The rules RightFit checks, each with where it comes from and how far it has been verified.
import { $, api, esc } from '../lib.js';

const STATUS = {
  verified_official: 'Read in the official journal',
  verified_secondary: 'Read in a copy, to check on the official text',
  to_confirm: 'To confirm on the official text',
  practice: "Reviewers' practice",
  engineer_input: "Set by the team's engineer",
  guidance: "Manufacturer's recommendation",
};
let location = 'RO';

async function draw() {
  const box = $('#rule-table');
  let rules;
  try {
    rules = await api(`/api/rules?location=${location}`);
  } catch (e) {
    if (box.isConnected) box.innerHTML = `<p class="error" role="alert">${esc(e.message)}</p>`;
    return;
  }
  if (!box.isConnected) return;   // the reviewer has already gone to another screen
  box.innerHTML = `<table><thead><tr><th>What it asks</th><th>Source</th><th>Applies to</th><th>Where it stands</th></tr></thead><tbody>
    ${rules.map((r) => `<tr><td>${esc(r.requirement)}</td><td>${r.source_url ? `<a href="${esc(r.source_url)}" target="_blank" rel="noopener">${esc(r.code)}</a>` : esc(r.code)}${r.clause ? `, ${esc(r.clause)}` : ''}</td>
      <td>${esc(r.applies_to.replace(/;/g, ', ').replace(/_/g, ' '))}</td><td>${esc(STATUS[r.status] || r.status)}</td></tr>`).join('')}</tbody></table>`;
}

export function render(root) {
  root.innerHTML = `<div class="screen"><div class="screen-head"><h1>Rules</h1><p>A rule that has not been read in the official text is not presented as a legal requirement.</p></div>
    <div class="tools"><select id="country" aria-label="Country"><option value="RO" ${location === 'RO' ? 'selected' : ''}>Romania</option><option value="ES" ${location === 'ES' ? 'selected' : ''}>Spain</option></select></div>
    <div id="rule-table"><p class="empty">Loading…</p></div></div>`;
  $('#country').addEventListener('change', (ev) => { location = ev.target.value; draw(); });
  draw();
}
