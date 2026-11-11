"""The second batch of real packages (data/raw/P03 to P51) as data for the page classifier.

Each file takes its type from its own name and from the attachment list of its form, with the fixed rules below, so no
AI labels these pages. A quarter of the MAFs of each discipline is held back for the locked test.

Run from the repository root:  python -m model.batch2
File names can carry project names, so the list it writes stays in data/raw/models/, outside Git. Only counts go in Git.
"""
import csv
import hashlib
import random
import re
from collections import Counter, defaultdict
from math import ceil
from pathlib import Path

import xlrd

from ingest.maf_form import _find, _text
from model.page_classifier import normalize

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data/raw"
OUT = RAW / "models/batch2_files.csv"
LOCKED = ROOT / "eval/page_classifier/test_labels.csv"
LEFT_OUT = {"P10"}   # a turned-down revision of P02, which is in the locked test
SEED = 2026
TEST_SHARE = 0.25

# Checked on the name or label with accents and punctuation removed. "certificat de conformitate" stays a certificate.
TYPE_WORDS = {
    "certificate": r"certific|agrement|\baviz\b|autorizatie|\bapproval\b",
    "declaration": r"declarat|deklarac|\bdop\b|^dc\b|\bdoc\b|^ce\b",
    "manual": r"manual|instructiun|instruction|\bghid\b|\bguide\b",
    "data_sheet": r"fis[ae] tehnic|\bft\b|\bf t\b|datasheet|data sheet|\bsheet\b|ficha tecnica|\bspec\b",
}


def stated_type(text):
    """The document type a file name or a form label states, or None if it states none or several."""
    words = re.sub(r"[^a-z0-9]+", " ", normalize(text)).strip()
    found = [kind for kind, pattern in TYPE_WORDS.items() if re.search(pattern, words)]
    return found[0] if len(found) == 1 else None


def listed_attachments(xls):
    """What the form says is attached: (label, pages) for each line of its list."""
    sheet = xlrd.open_workbook(xls).sheet_by_index(0)
    first, _ = _find(sheet, "Tip atasament", col=1)
    end, _ = _find(sheet, "Mostra transmisa", col=1)
    lines = []
    for r in range(first + 1, end):
        if _text(sheet, r, 1):
            pages = _text(sheet, r, 7)
            lines.append((_text(sheet, r, 1), int(float(pages)) if re.fullmatch(r"\d+(\.0)?", pages) else None))
    return lines


def label_files(files, attached):
    """The type of each PDF of one package, {name: (type, 'name' or 'form')}. files: (name, pages); attached: the form's
    (label, pages). A file whose name says nothing takes the form's label only when its page count points to one line."""
    labels = {}
    unnamed = [pages for name, pages in files if stated_type(name) is None]
    for name, pages in files:
        kind = stated_type(name)
        same = [label for label, n in attached if n == pages]
        said = stated_type(same[0]) if len(same) == 1 else None
        if kind and (said is None or said == kind):
            labels[name] = (kind, "name")
        elif not kind and said and unnamed.count(pages) == 1:
            labels[name] = (said, "form")
    return labels


def split(rows, seed=SEED):
    """Which side each MAF code is on, {code: (side, group)}. Revisions of one MAF share a code, and MAFs that share an
    identical file form one group, so the locked test never holds a document the model trained on."""
    parent = {r["code"]: r["code"] for r in rows}

    def root(code):
        while parent[code] != code:
            code = parent[code]
        return code

    first_with = {}
    for r in rows:
        parent[root(r["code"])] = root(first_with.setdefault(r["sha"], r["code"]))
    discipline = defaultdict(set)
    for r in rows:
        discipline[r["discipline"]].add(root(r["code"]))
    rng = random.Random(seed)
    test = set()
    for name in sorted(discipline):
        groups = sorted(discipline[name])
        rng.shuffle(groups)
        if len(groups) > 1:
            test.update(groups[:ceil(len(groups) * TEST_SHARE)])
    return {code: ("test" if root(code) in test else "train", root(code)) for code in parent}


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def locked_hashes():
    """The files of the first locked test: a copy of one of them must not reach training."""
    return {sha256(ROOT / f) for f in {r["file"] for r in csv.DictReader(open(LOCKED, newline=""))}}


def build():
    """One row per labelled PDF: where it is, its type, how we know it, and which side of the split it is on."""
    packages = {r["package"]: r for r in csv.DictReader(open(RAW / "batch2_inventory.csv", encoding="utf-8-sig"))}
    files = defaultdict(list)
    for r in csv.DictReader(open(RAW / "batch2_files.csv", encoding="utf-8-sig")):
        files[r["package"]].append(r)
    locked = locked_hashes()
    rows = []
    for pkg, info in sorted(packages.items()):
        if pkg in LEFT_OUT:
            continue
        pdfs = [(f["file"], int(f["pages"] or 0)) for f in files[pkg] if f["file"].lower().endswith(".pdf")]
        forms = [f["file"] for f in files[pkg] if f["file"].lower().endswith(".xls")]
        try:
            attached = listed_attachments(RAW / pkg / forms[0]) if forms else []
        except (ValueError, IndexError, xlrd.XLRDError):   # a form laid out differently: file names still count
            attached = []
        for name, (kind, how) in label_files(pdfs, attached).items():
            sha = sha256(RAW / pkg / name)
            if sha not in locked:
                rows.append({"package": pkg, "code": info["code"], "discipline": info["discipline"], "file": name,
                             "pages": dict(pdfs)[name], "label": kind, "how": how, "sha": sha})
    sides = split(rows)
    seen = set()
    kept = []
    for r in rows:   # an identical file in a second revision is one document, not two
        if r["sha"] not in seen:
            seen.add(r["sha"])
            kept.append({**r, "side": sides[r["code"]][0], "group": sides[r["code"]][1]})
    return kept


if __name__ == "__main__":
    rows = build()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    for side in ("train", "test"):
        part = [r for r in rows if r["side"] == side]
        pages = Counter()
        for r in part:
            pages[r["label"]] += r["pages"]
        print(f"{side}: {len(part)} documents from {len({r['group'] for r in part})} MAF groups, "
              f"{sum(pages.values())} pages: " + ", ".join(f"{k} {v}" for k, v in sorted(pages.items())))
    print("Labelled from the name:", sum(r["how"] == "name" for r in rows), "from the form:", sum(r["how"] == "form" for r in rows))
    print(f"Written to {OUT.relative_to(ROOT)}")
