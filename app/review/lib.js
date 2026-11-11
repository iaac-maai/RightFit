// Small helpers shared by every screen of the application.

export const $ = (sel, root = document) => root.querySelector(sel);
export const esc = (s) => String(s ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
export const pad = (n) => String(n).padStart(2, '0');
export const dmy = (iso) => (iso ? iso.split('-').reverse().join('.') : 'not set');
export const plural = (n, word) => `${word}${n === 1 ? '' : 's'}`;
export const fmt = (n, d = 1) => (n == null ? 'n/a' : Number(n).toFixed(d));
export const icon = (name) => `<svg class="i" aria-hidden="true"><use href="#i-${name}"/></svg>`;
export const breakable = (name) => esc(name).replace(/([_=@])/g, '$1<wbr>');
export const linkify = (text, name) => esc(text).replace(/https?:\/\/[^\s)<]+/g, (url) => `<a href="${url}" target="_blank" rel="noopener">${name ? esc(name) : url}</a>`);

// Asks the server; a body makes it a POST. An error keeps the server's message and status, so a screen can react to it.
export async function api(path, body, headers) {
  let res;
  try {
    res = await fetch(path, body === undefined ? undefined : { method: 'POST', headers: headers || { 'Content-Type': 'application/json' },
      body: headers ? body : JSON.stringify(body) });
  } catch {
    throw new Error('The RightFit server is not answering. Start it from the repository folder with: python app/review_server.py');
  }
  const data = await res.json().catch(() => ({}));
  if (!res.ok || data.error) throw Object.assign(new Error(data.error || `The server answered ${res.status}.`), { status: res.status });
  return data;
}

// What stays in this browser, like a draft. In a private window it lasts until the page closes.
const memory = {};
export const store = {
  read(key, fallback) {
    try { return JSON.parse(localStorage.getItem(key)) ?? fallback; } catch { return memory[key] ?? fallback; }
  },
  write(key, value) {
    memory[key] = value;
    try { localStorage.setItem(key, JSON.stringify(value)); } catch { /* private window */ }
  },
};

let toastTimer;
export function toast(message) {
  const t = $('#toast');
  t.textContent = message;
  t.classList.add('on');
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => t.classList.remove('on'), 2800);
}

export function download(name, text) {
  const a = document.createElement('a');
  a.href = URL.createObjectURL(new Blob([text], { type: name.endsWith('.csv') ? 'text/csv' : 'text/plain' }));
  a.download = name;
  a.click();
  setTimeout(() => URL.revokeObjectURL(a.href), 2000);
}

const cell = (v) => { const s = String(v ?? ''); return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s; };
export const csv = (rows) => `${rows.map((r) => r.map(cell).join(',')).join('\n')}\n`;

// A file name without the order code after the product name, and without all-capitals words.
export const shortName = (model) => model.replace(/\s+U\d\s+[A-Z](-[A-Z])+$/, '').replace(/\b([A-Z])([A-Z]{3,})\b/g, (_, a, b) => a + b.toLowerCase());
