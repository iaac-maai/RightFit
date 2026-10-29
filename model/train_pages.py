"""Train the page classifier from scratch on the labelled public PDFs and save it on the laptop.

Run from the repository root:  python -m model.train_pages
Then score it:                 python -m model.evaluate_pages data/raw/models/page_classifier.joblib
The PDFs (data/raw/training/) and the trained model (data/raw/models/) stay outside Git.
"""
import csv
import random
from collections import defaultdict
from pathlib import Path

import joblib
from sklearn.model_selection import GroupKFold, cross_val_predict

from model.evaluate_pages import scores
from model.page_classifier import CLASSES, build_model, pdf_pages

ROOT = Path(__file__).resolve().parents[1]
TRAINING = ROOT / "data/raw/training"
LABELS = ROOT / "eval/page_classifier/training_labels.csv"
MODEL_PATH = ROOT / "data/raw/models/page_classifier.joblib"
CAP = 40  # at most this many pages of one class from one document, so a 200-page manual doesn't drown the rest


def training_set(seed=0):
    """Page texts, their labels, and the document each page comes from."""
    labels = {(r["doc"], int(r["page"])): r["label"] for r in csv.DictReader(open(LABELS, newline=""))}
    grouped = defaultdict(list)
    for doc in sorted({d for d, _ in labels}):
        for p in pdf_pages(TRAINING / doc / f"{doc}.pdf"):
            if (doc, p["page"]) in labels:
                grouped[(doc, labels[(doc, p["page"])])].append(p["text"])
    rng = random.Random(seed)
    texts, ys, docs = [], [], []
    for (doc, label), pages in sorted(grouped.items()):
        for text in rng.sample(pages, CAP) if len(pages) > CAP else pages:
            texts.append(text), ys.append(label), docs.append(doc)
    return texts, ys, docs


if __name__ == "__main__":
    texts, ys, docs = training_set()
    print(f"{len(texts)} training pages from {len(set(docs))} documents: "
          + ", ".join(f"{c} {ys.count(c)}" for c in CLASSES))
    # Each document is left out in turn, so pages of one document never grade each other.
    guess = list(cross_val_predict(build_model(), texts, ys, groups=docs, cv=GroupKFold(n_splits=5)))
    s = scores(ys, guess)
    print(f"Cross-validation on the training documents: accuracy {s['accuracy']:.0%}, macro F1 {s['macro_f1']:.2f}")
    for cls in CLASSES:
        recall, precision, n = s[cls]
        if n:
            print(f"- {cls}: found {recall:.0%} of {n}" + (f", right {precision:.0%}" if precision is not None else ""))
    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(build_model().fit(texts, ys), MODEL_PATH)
    print(f"Saved {MODEL_PATH.relative_to(ROOT)}")
