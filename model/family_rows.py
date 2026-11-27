"""The product rows of the second batch's forms (P03 to P51), for a classifier that names the product family of a row, and
the page where a person picks the family of every row.

Run from the repository root:  python -m model.family_rows
Row texts can carry project names, so the list and the page stay in data/raw/models/, outside Git. Only counts go in Git.
Nothing on the page is filled in beforehand, by a model or by word rules: the person picks every family.
"""
import csv
import json
import re
from collections import Counter, defaultdict

import xlrd

from ingest.maf_form import _find, _text
from model.batch2 import RAW, ROOT, split

OUT = RAW / "models/family_rows.csv"
PAGE = RAW / "models/family_check/index.html"
NAMES = {"ahu": "Air handling unit", "dx_kit": "DX kit"}


def families():
    """The families of check D1 (data/maf/family_documents.csv), each with the harmonised standard it names, then other."""
    found = {}
    for r in csv.DictReader(open(ROOT / "data/maf/family_documents.csv", newline="", encoding="utf-8-sig")):
        standard = re.search(r"EU-HEN-([\d-]+)", r["rule_id"])
        for family in r["family"].split(";"):
            if family != "all":
                found.setdefault(family, "")
                if standard:
                    found[family] = "EN " + standard.group(1)
    return {**found, "other": ""}


def form_rows(xls):
    """The product rows of a form, from the columns read_form uses. read_form stops on some batch 2 headers (a date typed
    as a number, a revision written REV00), so the rows are read here directly."""
    sheet = xlrd.open_workbook(xls).sheet_by_index(0)
    header, _ = _find(sheet, "Producator / Brand", col=9)
    end, _ = _find(sheet, "Pozitie in BOQ", col=1)
    rows = [{"name": _text(sheet, r, 4), "brand": _text(sheet, r, 9), "model": _text(sheet, r, 11)}
            for r in range(header + 1, end)]
    return [r for r in rows if r["name"] or r["model"]]


def plain(text):
    return " ".join(text.lower().split())


def assign(rows, files, held):
    """Which side each MAF code is on, {code: (side, group)}. The groups are those of model.batch2.split: the revisions
    of one MAF and MAFs that share an identical file (files: {package: [one key per file]}) stay together, and here the
    same product name or model joins MAFs too, so the locked rows never repeat a row the model trained on. A group is
    locked when it holds a package in held. No random quarter is added (Luca, 17 Nov 2026): the chatbot test set is
    already a random draw by MAF, and the training side has few rows."""
    keys = [{"code": r["code"], "discipline": r["discipline"], "sha": key}
            for r in rows
            for key in files.get(r["package"], []) + [f"name:{plain(r['name'])}", f"model:{plain(r['model'])}"]
            if key not in ("name:", "model:")]
    groups = {code: group for code, (_, group) in split(keys).items()}
    locked = {groups[r["code"]] for r in rows if r["package"] in held}
    return {code: ("test" if group in locked else "train", group) for code, group in groups.items()}


def build():
    """One row per product row of every form, with its package's MAF code, discipline and side of the split."""
    packages = {r["package"]: r for r in csv.DictReader(open(RAW / "batch2_inventory.csv", encoding="utf-8-sig"))
                if "P03" <= r["package"] <= "P51"}
    files = defaultdict(list)
    for r in csv.DictReader(open(RAW / "batch2_files.csv", encoding="utf-8-sig")):
        files[r["package"]].append(r["file"])
    # The chatbot comparison runs RightFit on these packages, so no model of ours may train on them.
    held = {r["package"] for r in csv.DictReader(open(ROOT / "eval/chatbot_baseline/test_set.csv", newline=""))}
    rows = []
    for pkg, info in sorted(packages.items()):
        items = [item for f in files[pkg] if f.lower().endswith(".xls") for item in form_rows(RAW / pkg / f)]
        rows += [{"row_id": f"{pkg}-{n}", "package": pkg, "code": info["code"], "revision": info["revision"],
                  "discipline": info["discipline"], **item} for n, item in enumerate(items, 1)]
    # shortcut: a PDF's size in bytes stands in for its hash, because iCloud has evicted most package files and reading
    # them hangs; identical files always have the same size, so this can only join more MAFs, never fewer. Hash them with
    # model.batch2.sha256 once the files are back on disk. Forms are left out: one template gives them equal sizes.
    same = {pkg: [f"size:{(RAW / pkg / f).stat().st_size}" for f in files[pkg] if f.lower().endswith(".pdf")]
            for pkg in packages}
    sides = assign(rows, same, held)
    return [{**r, "side": sides[r["code"]][0], "group": sides[r["code"]][1]} for r in rows]


def page(rows):
    """The check page: each distinct row once, a list of families, and Save, which downloads the picks as a CSV."""
    cards = {}
    for r in rows:
        key = (plain(r["name"]), plain(r["brand"]), plain(r["model"]))
        card = cards.setdefault(key, {k: r[k] for k in ("name", "brand", "model", "discipline")} | {"rows": []})
        card["rows"].append([r["row_id"], r["package"]])
    choices = [[f, NAMES.get(f, f.replace("_", " ").capitalize()) + (f" ({std})" if std else "")]
               for f, std in families().items()] + [["unsure", "Not sure"]]
    data = json.dumps(list(cards.values()), ensure_ascii=False).replace("</", "<\\/")
    return TEMPLATE.replace("__CARDS__", data).replace("__FAMILIES__", json.dumps(choices))


TEMPLATE = """<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Product families</title>
<style>
:root { --rail:#0E3B2E; --ground:#E7F0E8; --band:#DCE9DF; --line:#C5D6CA; --ink:#15191A; --ink2:#3D4A42; }
* { box-sizing:border-box; } body { margin:0; background:var(--ground); color:var(--ink); font:15px/1.45 -apple-system,BlinkMacSystemFont,"Helvetica Neue",Arial,sans-serif; }
header { position:sticky; top:0; z-index:5; background:var(--rail); color:#fff; padding:14px 22px; display:flex; flex-wrap:wrap; gap:8px 18px; align-items:center; }
header h1 { font-size:18px; margin:0; } header span { color:#DCE9DF; } header button { margin-left:auto; font:inherit; font-weight:600; padding:9px 14px; border:0; border-radius:4px; background:#fff; color:var(--rail); cursor:pointer; }
main { padding:18px 22px 60px; max-width:1500px; margin:0 auto; } .lead { max-width:820px; margin:0 0 16px; color:var(--ink2); }
.wrap { overflow-x:auto; } table { width:100%; border-collapse:collapse; background:#fff; border:1px solid var(--line); }
th, td { text-align:left; vertical-align:top; padding:8px 10px; border-bottom:1px solid var(--line); } th { font-size:13px; color:var(--ink2); background:#F6F9F6; }
td.m { white-space:pre-line; overflow-wrap:anywhere; font-size:13.5px; } td small { color:var(--ink2); } tr.done { background:var(--band); }
select, input { font:inherit; padding:6px; width:100%; min-width:200px; }
</style></head><body>
<header><h1>Name the product family of each row</h1><span id="count"></span><button id="save">Save my labels</button></header>
<main><p class="lead">Each row is a product line copied from a real form of the second batch. Pick the family of the product. A product in none of the families is Other. If a row names several products, pick the main one and write the others in the note; if you cannot tell, pick Not sure. Nothing is filled in beforehand. Your picks stay in this browser if you close the page. When you are done, press Save my labels: the file family_labels.csv goes to your Downloads.</p>
<div class="wrap"><table><thead><tr><th>Product</th><th>Brand</th><th>Model</th><th>Package</th><th>Family</th><th>Note</th></tr></thead><tbody></tbody></table></div></main>
<script>
const CARDS = __CARDS__;
const FAMILIES = __FAMILIES__;
const KEY = 'rightfit.family_check_v1';
let saved = {}; try { saved = JSON.parse(localStorage.getItem(KEY)) || {}; } catch {}
const esc = (s) => String(s).replace(/[&<>"']/g, (c) => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const pick = (c) => saved[c.rows[0][0]] || {};
function count() { document.getElementById('count').textContent = `${CARDS.filter((c) => pick(c).family).length} of ${CARDS.length} rows picked`; }
document.querySelector('tbody').innerHTML = CARDS.map((c) => { const s = pick(c);
  return `<tr data-id="${esc(c.rows[0][0])}" class="${s.family ? 'done' : ''}"><td>${esc(c.name)}</td><td class="m">${esc(c.brand)}</td><td class="m">${esc(c.model)}</td><td>${esc([...new Set(c.rows.map((r) => r[1]))].join(', '))}<br><small>${esc(c.discipline)}</small></td><td><select aria-label="Family of this product"><option value="">Pick a family</option>${FAMILIES.map(([v, n]) => `<option value="${v}" ${s.family === v ? 'selected' : ''}>${esc(n)}</option>`).join('')}</select></td><td><input aria-label="Note on this row" value="${esc(s.note || '')}"></td></tr>`; }).join('');
count();
document.querySelector('tbody').addEventListener('input', (e) => { const tr = e.target.closest('tr'); const s = saved[tr.dataset.id] = saved[tr.dataset.id] || {};
  s[e.target.tagName === 'SELECT' ? 'family' : 'note'] = e.target.value; tr.classList.toggle('done', !!s.family);
  try { localStorage.setItem(KEY, JSON.stringify(saved)); } catch {} count(); });
document.getElementById('save').addEventListener('click', () => {
  const cell = (v) => /[",\\r\\n]/.test(v) ? `"${v.replace(/"/g, '""')}"` : v;
  const lines = CARDS.flatMap((c) => { const s = pick(c); return c.rows.map(([id, pkg]) => [id, pkg, s.family || '', s.note || '', s.family ? 'Luca' : ''].map((v) => cell(String(v))).join(',')); });
  const text = ['row_id,package,family,note,labelled_by', ...lines].join('\\n') + '\\n';
  const a = document.createElement('a'); a.href = URL.createObjectURL(new Blob([text], { type: 'text/csv' })); a.download = 'family_labels.csv'; a.click();
});
</script></body></html>
"""


if __name__ == "__main__":
    rows = build()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    PAGE.parent.mkdir(parents=True, exist_ok=True)
    PAGE.write_text(page(rows), encoding="utf-8")
    distinct = len({(plain(r["name"]), plain(r["brand"]), plain(r["model"])) for r in rows})
    print(f"{len(rows)} rows from {len({r['package'] for r in rows})} forms, {distinct} distinct rows on the page")
    for side in ("train", "test"):
        part = [r for r in rows if r["side"] == side]
        print(f"{side}: {len(part)} rows, {len({r['package'] for r in part})} packages, {len({r['group'] for r in part})} "
              f"MAF groups; by discipline: " + ", ".join(f"{k} {v}" for k, v in sorted(Counter(r['discipline'] for r in part).items())))
    print(f"Written to {OUT.relative_to(ROOT)} and {PAGE.relative_to(ROOT)}")
