"""Score a page classifier on the locked test pages (eval/page_classifier/test_labels.csv).

Run from the repository root:  python -m model.evaluate_pages [model] [sets, for example C]
It needs the originals in data/raw/, which stay on the laptop. Naming the sets scores only those, so a set whose labels
are not confirmed yet is not used up.
"""
import csv
import sys
from collections import Counter
from datetime import date
from pathlib import Path

from model.page_classifier import CLASSES, MIN_TEXT, keyword_baseline, normalize, pdf_pages

ROOT = Path(__file__).resolve().parents[1]
LABELS = ROOT / "eval/page_classifier/test_labels.csv"
# The locked pages of the second batch, once Luca has confirmed their labels. File names can carry project names, so
# this list stays outside Git.
BATCH2_LABELS = ROOT / "data/raw/models/batch2_test_labels.csv"


def test_pages():
    """The labelled test pages with their text, read from the local originals."""
    rows = list(csv.DictReader(open(LABELS, newline="")))
    if BATCH2_LABELS.exists():
        rows += list(csv.DictReader(open(BATCH2_LABELS, newline="", encoding="utf-8")))
    texts = {}
    for path in {r["file"] for r in rows}:
        for p in pdf_pages(ROOT / path):
            texts[(path, p["page"])] = p["text"]
    return [{**r, "page": int(r["page"]), "text": texts[(r["file"], int(r["page"]))]} for r in rows]


def scores(truth, guess):
    """Accuracy, and per class: how many pages of that class were found (recall) and how many guesses were right."""
    out = {"pages": len(truth), "accuracy": sum(t == g for t, g in zip(truth, guess)) / len(truth)}
    f1s = []
    for cls in CLASSES:
        tp = sum(t == g == cls for t, g in zip(truth, guess))
        n_true, n_guess = truth.count(cls), guess.count(cls)
        recall = tp / n_true if n_true else None
        precision = tp / n_guess if n_guess else None
        out[cls] = (recall, precision, n_true)
        if n_true:
            f1s.append(2 * tp / (n_true + n_guess))
    out["macro_f1"] = sum(f1s) / len(f1s)
    return out


def report(name, pages, guess):
    lines = [f"### {name}"]
    for subset in sorted({p["set"] for p in pages}):
        idx = [i for i, p in enumerate(pages) if p["set"] == subset]
        readable = [i for i in idx if len(normalize(pages[i]["text"])) >= MIN_TEXT or pages[i]["label"] == "other"]
        s = scores([pages[i]["label"] for i in idx], [guess[i] for i in idx])
        lines.append(f"Set {subset}: {s['pages']} pages ({len(idx) - len(readable)} scanned without text), "
                     f"accuracy {s['accuracy']:.0%}, macro F1 {s['macro_f1']:.2f}")
        for cls in CLASSES:
            recall, precision, n = s[cls]
            if n:
                lines.append(f"- {cls}: found {recall:.0%} of {n} pages"
                             + (f", right {precision:.0%} of the time" if precision is not None else ""))
    confusions = Counter((p["label"], g) for p, g in zip(pages, guess) if p["label"] != g)
    lines.append("Most frequent mistakes (true -> guessed): "
                 + "; ".join(f"{t} -> {g}: {n}" for (t, g), n in confusions.most_common(5)))
    return "\n".join(lines)


if __name__ == "__main__":
    pages = test_pages()
    if len(sys.argv) > 2:
        pages = [p for p in pages if p["set"] in sys.argv[2].split(",")]
    text = report("Keyword baseline (non-AI)", pages, [keyword_baseline(p["text"]) for p in pages])
    model_path = Path(sys.argv[1]) if len(sys.argv) > 1 else None
    if model_path:
        import joblib
        from model.page_classifier import predict
        text += "\n\n" + report("Our model", pages, predict(joblib.load(model_path), [p["text"] for p in pages]))
    print(f"Run on {date.today()}\n\n{text}")
