// The review, the rules and the booster sizing are done in RightFit online since 21 Nov 2026 (one app, not two: Luca).
// This screen sends the reviewer there, to the same package or page of the project online. The laptop's own screens
// stay in the code and open with /here at the end of the address, only for when the site cannot be reached.
import { esc } from '../lib.js';

const SITE = 'https://rightfit.hackathon-team6-cubicasa-app.workers.dev';
const WHAT = { packages: 'the packages', p: 'the review of this package', rules: 'the rules', booster: 'the booster sizing' };

export function render(root, [key, ...args], online) {
  const base = online?.project ? `${online.site || SITE}/p/${online.project}` : SITE;
  const path = { packages: '/packages', p: args[0] ? `/packages/${args[0]}` : '/packages', rules: '/rules', booster: '/booster' }[key] ?? '';
  const target = online?.project ? `${base}${path}` : base;
  const here = `#/${[key, ...args, 'here'].join('/')}`;
  root.innerHTML = `<div class="screen"><div class="screen-head"><h1>This is in RightFit online now</h1>
      <p>RightFit is one app: ${esc(WHAT[key] || 'this screen')} ${key === 'p' || key === 'booster' ? 'is' : 'are'} on the site, where the whole team ticks the readings and decides, and the checks run with this same code. On this laptop you add a new package, which then goes online.</p></div>
    <p><a class="btn p" href="${esc(target)}" target="_blank" rel="noopener">Open ${esc(WHAT[key] || 'RightFit online')} online</a></p>
    ${online?.project ? '' : '<p class="note" style="margin-top:12px">This project has not been put online yet, so the link opens the site\'s list of projects.</p>'}
    <p class="note" style="margin-top:18px">Only if the site cannot be reached: <a href="${esc(here)}">open the copy on this laptop</a>. What is ticked or decided there stays on this laptop.</p></div>`;
}
