"""What changed between two revisions of one MAF? No AI here, and nothing is changed: it only reports.

Each attachment of the new revision is paired with the attachment of the previous revision that it continues:
- the same file, byte for byte, whatever its name is now: unchanged;
- otherwise the closest attachment by its text (TF-IDF on groups of 3 to 5 letters, cosine similarity) or, when
  either file is a scan with no text, by the look of its first pages (small grey thumbnails, correlation):
  changed, with how many of its pages still carry exactly the same text;
- nothing close enough: new. An attachment of the previous revision that nothing continues: removed.
Pairs are one to one, the closest first. It is the similarity search of the AI Methods hackathon (16 Nov 2026:
code every item once, then look for the nearest code), with codes that need no training.

Run from the repository root:  python3 -m ingest.revisions P02   (finds the previous revision by the form number)
                          or:  python3 -m ingest.revisions P10 P02   (previous revision first)
"""
import hashlib
import sys
from pathlib import Path

import pymupdf

RAW = Path(__file__).resolve().parent.parent / "data" / "raw"
FORMS = {".xls", ".xlsx"}   # the form itself changes with every revision, so it is read, not compared
TEXT_MIN = 200              # a file with fewer characters of text than this is treated as a scan
SAME_TEXT = 0.5             # text similarity from which two attachments count as one document in two versions
SAME_LOOK = 0.8             # the same for the look of the pages, used when a file has no text
LOOK_PAGES = 3              # first pages compared by look
THUMB = 32                  # thumbnail side, in pixels


def attachments(folder):
    """The package's attachments: every file except the form and hidden files, by name."""
    return sorted(f for f in Path(folder).iterdir()
                  if f.is_file() and not f.name.startswith(".") and f.suffix.lower() not in FORMS)


def thumbnails(doc):
    """The first pages as small grey images in one vector of ink (paper is 0), so blank space weighs nothing."""
    import numpy as np
    vec = np.zeros((LOOK_PAGES, THUMB, THUMB))
    for i, page in enumerate(doc):
        if i == LOOK_PAGES:
            break
        zoom = THUMB / max(page.rect.width, page.rect.height)
        pix = page.get_pixmap(matrix=pymupdf.Matrix(zoom, zoom), colorspace=pymupdf.csGRAY, alpha=False)
        img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.stride)[:THUMB, :min(pix.width, THUMB)]
        vec[i, :img.shape[0], :img.shape[1]] = 255.0 - img
    return vec.ravel()


def read(path):
    """What is compared of one attachment: the digest of its bytes, its text page by page and its look (PDFs only)."""
    item = {"name": path.name, "digest": hashlib.sha256(path.read_bytes()).hexdigest(), "pages": [], "look": None}
    if path.suffix.lower() == ".pdf":
        with pymupdf.open(path) as doc:
            item["pages"] = [" ".join(page.get_text().split()) for page in doc]
            item["look"] = thumbnails(doc)
    item["text"] = " ".join(item["pages"])
    return item


def correlation(a, b):
    """How alike two looks are, from -1 to 1; 0 when either page is blank."""
    import numpy as np
    a, b = a - a.mean(), b - b.mean()
    norm = float(np.linalg.norm(a) * np.linalg.norm(b))
    return float(a @ b) / norm if norm else 0.0


def similarities(old, new):
    """Every (similarity, how, new name, old name) for two PDFs, by text when both have text, else by look."""
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
    has_text = lambda d: len(d["text"]) >= TEXT_MIN
    texts = [d for d in old + new if has_text(d)]
    sim = {}
    if texts:
        matrix = TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5)).fit_transform([d["text"] for d in texts])
        scores = cosine_similarity(matrix)
        sim = {(a["name"], id(a), b["name"], id(b)): float(scores[i, j])
               for i, a in enumerate(texts) for j, b in enumerate(texts)}
    pairs = []
    for n in new:
        for o in old:
            if n["look"] is None or o["look"] is None:
                continue                                   # not a PDF: only the same file counts
            if has_text(n) and has_text(o):
                pairs.append((sim[(n["name"], id(n), o["name"], id(o))], "text", n["name"], o["name"]))
            else:
                pairs.append((correlation(n["look"], o["look"]), "look", n["name"], o["name"]))
    return pairs


def same_pages(new, old):
    """How many pages of the new version carry exactly the text of a page of the old one."""
    before = {p for p in old["pages"] if p}
    return sum(1 for p in new["pages"] if p and p in before)


def compare(previous, current):
    """One row per attachment of the current revision, then one per removed attachment of the previous one."""
    old = [read(f) for f in attachments(previous)]
    new = [read(f) for f in attachments(current)]
    pair, how, score = {}, {}, {}
    taken = set()
    for n in new:                                         # 1. the same file, whatever its name
        o = next((o for o in old if o["digest"] == n["digest"] and o["name"] not in taken), None)
        if o:
            pair[n["name"]], how[n["name"]], score[n["name"]] = o["name"], "same file", 1.0
            taken.add(o["name"])
    rest_old = [o for o in old if o["name"] not in taken]
    rest_new = [n for n in new if n["name"] not in pair]
    for s, way, nn, on in sorted(similarities(rest_old, rest_new), key=lambda p: -p[0]):   # 2. closest first
        if nn in pair or on in taken or s < (SAME_TEXT if way == "text" else SAME_LOOK):
            continue
        pair[nn], how[nn], score[nn] = on, way, s
        taken.add(on)
    by_name = {d["name"]: d for d in old}
    rows = []
    for n in new:
        o = pair.get(n["name"])
        row = {"file": n["name"], "previous": o, "how": how.get(n["name"]),
               "similarity": round(score[n["name"]], 2) if o else None,
               "status": "new" if o is None else "unchanged" if how[n["name"]] == "same file" else "changed"}
        if row["status"] == "unchanged" and o != n["name"]:
            row["renamed"] = True                        # same bytes under a new name: worth a look by the reviewer
        if row["status"] == "changed" and row["how"] == "text":
            row["same_pages"] = same_pages(n, by_name[o])
            row["pages"] = len(n["pages"])
        rows.append(row)
    rows += [{"file": None, "previous": o["name"], "how": None, "similarity": None, "status": "removed"}
             for o in old if o["name"] not in taken]
    return rows


def form_of(folder):
    """The form number and revision of a package, read from its form; None when it has no readable form."""
    from ingest.maf_form import read_form
    form = next((f for f in Path(folder).iterdir() if f.suffix.lower() in FORMS and not f.name.startswith(".")), None)
    try:
        info = read_form(form) if form else None
    except Exception:                                      # some forms of the second batch stop the reader
        return None
    return (info["form_no"], info["revision"]) if info and info.get("form_no") and info.get("revision") is not None else None


def previous_revision(folder):
    """The package next to this one with the same form number and the highest lower revision, or None."""
    me = form_of(folder)
    if not me:
        return None
    best = None
    for other in Path(folder).parent.iterdir():
        if other.is_dir() and other != Path(folder):
            it = form_of(other)
            if it and it[0] == me[0] and it[1] < me[1] and (best is None or it[1] > best[1]):
                best = (other, it[1])
    return best[0] if best else None


def main(args):
    current = Path(args[-1]) if Path(args[-1]).is_dir() else RAW / args[-1]
    previous = (Path(args[0]) if Path(args[0]).is_dir() else RAW / args[0]) if len(args) == 2 else previous_revision(current)
    if previous is None:
        print(f"{current.name}: no previous revision found next to it")
        return
    print(f"{previous.name} -> {current.name}")
    for r in compare(previous, current):
        if r["status"] == "removed":
            print(f"  removed    {r['previous']}")
        elif r["status"] == "new":
            print(f"  new        {r['file']}")
        elif r["status"] == "unchanged":
            print(f"  unchanged  {r['file']}" + (f"  (renamed; was {r['previous']})" if r.get("renamed") else ""))
        else:
            pages = f"; {r['same_pages']} of {r['pages']} pages with the same text" if "same_pages" in r else ""
            print(f"  changed    {r['file']}  <-  {r['previous']}  ({r['how']} similarity {r['similarity']}{pages})")


if __name__ == "__main__":
    main(sys.argv[1:])
