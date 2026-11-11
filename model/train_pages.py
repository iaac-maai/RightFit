"""Train the page classifier from scratch on the labelled public PDFs and on the second batch of real packages.

Run from the repository root:  python -m model.batch2   and then   python -m model.train_pages
Score it once, when the test labels are confirmed:  python -m model.evaluate_pages data/raw/models/page_classifier_v2.joblib
The PDFs (data/raw/) and the trained model (data/raw/models/) stay outside Git.
"""
import csv
import random
from collections import defaultdict
from pathlib import Path

import joblib
from sklearn.model_selection import GroupKFold, cross_val_predict

from model.evaluate_pages import scores
from model.page_classifier import CLASSES, MIN_TEXT, build_model, keyword_baseline, normalize, pdf_pages

ROOT = Path(__file__).resolve().parents[1]
TRAINING = ROOT / "data/raw/training"
LABELS = ROOT / "eval/page_classifier/training_labels.csv"
# Data sheets Luca printed from Grundfos Product Center for unrelated pumps: every page with text is a data sheet.
DATASHEETS = TRAINING / "datasheets_ro"
BATCH2 = ROOT / "data/raw/models/batch2_files.csv"   # written by model/batch2.py
MODEL_PATH = ROOT / "data/raw/models/page_classifier_v2.joblib"
CAP = 40  # at most this many pages of one class from one document, so a 200-page manual doesn't drown the rest


def training_set(seed=0):
    """Page texts, their labels, and the document each page comes from."""
    labels = {(r["doc"], int(r["page"])): r["label"] for r in csv.DictReader(open(LABELS, newline=""))}
    grouped = defaultdict(list)
    for doc in sorted({d for d, _ in labels}):
        for p in pdf_pages(TRAINING / doc / f"{doc}.pdf"):
            if (doc, p["page"]) in labels:
                grouped[(doc, labels[(doc, p["page"])])].append(p["text"])
    for path in sorted(DATASHEETS.glob("*.pdf")):
        for p in pdf_pages(path):
            label = "data_sheet" if len(normalize(p["text"])) >= MIN_TEXT else "other"
            grouped[(f"datasheets_ro/{path.stem}", label)].append(p["text"])
    # In cross-validation a whole MAF is left out at once, so revisions of one MAF never grade each other.
    maf_of = {}
    rows = list(csv.DictReader(open(BATCH2, newline="", encoding="utf-8"))) if BATCH2.exists() else []
    for r in (x for x in rows if x["side"] == "train"):
        doc = f"batch2/{r['package']}/{r['file']}"
        maf_of[doc] = f"batch2/{r['group']}"
        try:
            pages = pdf_pages(ROOT / "data/raw" / r["package"] / r["file"])
        except Exception:   # a damaged or locked PDF: the rest of the batch still trains
            continue
        for p in pages:
            if len(normalize(p["text"])) >= MIN_TEXT:   # a scan has no text for this model to learn from
                grouped[(doc, r["label"])].append(p["text"])
    rng = random.Random(seed)
    texts, ys, docs = [], [], []
    for (doc, label), pages in sorted(grouped.items()):
        for text in rng.sample(pages, CAP) if len(pages) > CAP else pages:
            texts.append(text), ys.append(label), docs.append(maf_of.get(doc, doc))
    return texts, ys, docs


def print_scores(name, truth, guess):
    s = scores(truth, guess)
    print(f"{name}: accuracy {s['accuracy']:.0%}, macro F1 {s['macro_f1']:.2f}")
    for cls in CLASSES:
        recall, precision, n = s[cls]
        if n:
            print(f"- {cls}: found {recall:.0%} of {n}" + (f", right {precision:.0%}" if precision is not None else ""))


if __name__ == "__main__":
    texts, ys, docs = training_set()
    print(f"{len(texts)} training pages from {len(set(docs))} documents and MAFs: "
          + ", ".join(f"{c} {ys.count(c)}" for c in CLASSES))
    # Each document is left out in turn, so pages of one document never grade each other.
    guess = list(cross_val_predict(build_model(), texts, ys, groups=docs, cv=GroupKFold(n_splits=5)))
    print_scores("Our model, cross-validation on the training documents", ys, guess)
    print_scores("Keyword search on the same pages", ys, [keyword_baseline(t) for t in texts])
    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(build_model().fit(texts, ys), MODEL_PATH)
    print(f"Saved {MODEL_PATH.relative_to(ROOT)}")
