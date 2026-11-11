// RightFit, one application. Every screen is a file in views/ that exports render(root, args) and, if it needs it,
// leave(). To add a screen: write the file, then add one line to ROUTES and one link to the rail in index.html.
import { $ } from './lib.js';
import * as packages from './views/packages.js';
import * as review from './views/review.js';
import * as add from './views/add.js';
import * as booster from './views/booster.js';
import * as standby from './views/standby.js';
import * as rules from './views/rules.js';

const ROUTES = { packages, p: review, add, booster, standby, rules };
const TITLES = { packages: 'Packages', p: 'Review', add: 'Add a package', booster: 'Booster sizing', standby: 'Standby test', rules: 'Rules' };
let current = null;

function route() {
  const [name, ...args] = window.location.hash.replace(/^#\/?/, '').split('/');
  const key = ROUTES[name] ? name : 'packages';
  document.querySelectorAll('[data-nav]').forEach((a) => {
    if (a.dataset.nav.split(' ').includes(key)) a.setAttribute('aria-current', 'page');
    else a.removeAttribute('aria-current');
  });
  document.title = `RightFit · ${TITLES[key]}`;
  if (current !== ROUTES[key]) current?.leave?.();
  current = ROUTES[key];
  current.render($('#app'), args);
}

window.addEventListener('hashchange', route);
// A file dropped beside a drop zone must not replace the application.
['dragover', 'drop'].forEach((t) => window.addEventListener(t, (ev) => ev.preventDefault()));
route();
