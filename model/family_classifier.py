"""Family classifier: the product family of a row of a MAF form, so check D1 knows which documents the product needs.

Two ways to answer, compared on the same locked rows:
- family_words: the non-AI way, fixed words on the row's name;
- a model we train from scratch on the training rows: letter groups (TF-IDF) and a logistic regression, as for the page
  classifier. No pretrained weights; everything it knows comes from our rows.

Run from the repository root, after  python -m model.family_rows:
    python -m model.family_classifier          cross-validation on the training rows, then saves the model
    python -m model.family_classifier score    once per model version, on the locked rows
The labels are Luca's (data/raw/models/family_labels.csv), picked with nothing filled in beforehand; rows he marked
unsure are left out of both. The rows, the labels and the model stay in data/raw/models/, outside Git.
"""
import csv
import re
import sys
from collections import Counter

import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import LeaveOneGroupOut, cross_val_predict
from sklearn.pipeline import make_pipeline

from model.batch2 import RAW
from model.family_rows import OUT as ROWS, families
from model.page_classifier import normalize

LABELS = RAW / "models/family_labels.csv"
MODEL_PATH = RAW / "models/family_classifier.joblib"

# Each family's own name in Romanian and English, its usual synonyms and its standard, checked on the name with accents
# and punctuation removed. Romanian names start with what the product is, so when two families' words are there the one
# that comes first wins ("unitate exterioara pentru kit DX" is an outdoor unit). A cable's name starts with the word:
# trays, conduits and boxes "for cables" are not cables.
FAMILY_WORDS = {
    "pump": r"\bpomp(a|e|ei|are|aj)\b|\bpumps?\b",
    "ahu": r"\bcentral\w* (de )?tratare (a )?aer|\bcta\b|\bair handling|\bahu\b",
    "outdoor_unit": r"\bunitat\w* exterioar|\boutdoor units?\b",
    "dx_kit": r"\bkit\w* (de )?(dx|detenta directa)\b|\bdx kits?\b",
    "fire_damper": r"\bclapet\w* (de )?(antifoc|incendiu)|\bfire dampers?\b|\ben 15650\b",
    "radiator": r"\bradiator|\bcalorifer|\ben 442\b",
    "elastomeric_insulation": r"\bizolati\w* elastomer|\belastomeric insulation|\ben 14304\b",
    "fire_detection_panel": r"\bcentral\w* (de )?(detectie|semnalizare|avertizare) (a )?incendi"
                            r"|\bfire (detection|alarm) (control )?panel|\ben 54 2\b",
    "fire_alarm_power_supply": r"(\bsurs\w* (de )?alimentare|\balimentator|\bpower supply)\b.*\b(en 54|incendi|evacuare|alarm)"
                               r"|\ben 54 4\b",
    "voice_alarm_control": r"\bevacuare vocal|\balarmare vocal|\bvoice (alarm|evacuation)|\ben 54 16\b",
    "visual_alarm_device": r"\b(semnaliz|alarm)\w* optic|\bbeacon|\bvisual alarm|\ben 54 23\b",
    "voice_alarm_loudspeaker": r"\bdifuzo|\bloudspeaker|\ben 54 24\b",
    "cable": r"^cablu|^cables?\b|\ben 50575\b",
}

# Model variants, compared only by cross-validation on the training rows: which fields of the row it reads, and the
# length of the letter groups. The first is the simplest and wins a tie.
VARIANTS = {
    "name, letter groups of 2 to 4": (("name",), (2, 4)),
    "name, brand and model, letter groups of 2 to 4": (("name", "brand", "model"), (2, 4)),
    "name, letter groups of 3 to 5": (("name",), (3, 5)),
}


def family_words(name):
    """The non-AI method: the family whose words come first in the row's name, other when no family's words are there."""
    words = re.sub(r"[^a-z0-9]+", " ", normalize(name)).strip()
    found = [(m.start(), i, family) for i, (family, pattern) in enumerate(FAMILY_WORDS.items())
             if (m := re.search(pattern, words))]
    return min(found)[2] if found else "other"


def build_model(ngrams):
    """Untrained model: letter groups inside words, weighted by TF-IDF, and a logistic regression."""
    return make_pipeline(TfidfVectorizer(preprocessor=normalize, analyzer="char_wb", ngram_range=ngrams, sublinear_tf=True),
                         LogisticRegression(max_iter=3000, class_weight="balanced"))


def text(row, fields):
    return " ".join(row[f] for f in fields)


def labelled(side):
    """The rows of one side with Luca's family; rows he left empty or marked unsure are left out."""
    family = {r["row_id"]: r["family"] for r in csv.DictReader(open(LABELS, newline="", encoding="utf-8"))}
    return [{**r, "family": family[r["row_id"]]} for r in csv.DictReader(open(ROWS, newline="", encoding="utf-8"))
            if r["side"] == side and family.get(r["row_id"]) not in (None, "", "unsure")]


def report(name, truth, guess):
    """Counts, not percentages: with this few rows one row moves a percentage by several points."""
    family_rows = [(t, g) for t, g in zip(truth, guess) if t != "other"]
    lines = [f"{name}: {sum(t == g for t, g in zip(truth, guess))} of {len(truth)} rows right; "
             f"rows of a family (not other): {sum(t == g for t, g in family_rows)} of {len(family_rows)} right"]
    for family in families():
        n, said = truth.count(family), guess.count(family)
        if n or said:
            lines.append(f"- {family}: found {sum(t == g == family for t, g in zip(truth, guess))} of {n}, said {said} times")
    mistakes = Counter((t, g) for t, g in zip(truth, guess) if t != g)
    lines.append("- mistakes (true -> said): " + ("; ".join(f"{t} -> {g}: {n}" for (t, g), n in mistakes.most_common())
                                                   or "none"))
    return "\n".join(lines)


def cross_validate():
    """Each variant, every MAF group of the training rows left out in turn; saves the variant with most family rows
    right (then most rows right), trained on all the training rows."""
    rows = labelled("train")
    truth, groups = [r["family"] for r in rows], [r["group"] for r in rows]
    print(f"{len(rows)} training rows from {len(set(groups))} MAF groups: "
          + ", ".join(f"{k} {v}" for k, v in Counter(truth).most_common()))
    print(report("Family words (non-AI), on the same rows", truth, [family_words(r["name"]) for r in rows]))
    best = None
    for name, (fields, ngrams) in VARIANTS.items():
        guess = list(cross_val_predict(build_model(ngrams), [text(r, fields) for r in rows], truth, groups=groups,
                                       cv=LeaveOneGroupOut()))
        print(report(f"Our model ({name}), each MAF left out in turn", truth, guess))
        key = (sum(t == g != "other" for t, g in zip(truth, guess)), sum(t == g for t, g in zip(truth, guess)))
        if best is None or key > best[0]:
            best = (key, name)
    fields, ngrams = VARIANTS[best[1]]
    joblib.dump({"variant": best[1], "fields": fields, "model": build_model(ngrams).fit([text(r, fields) for r in rows], truth)},
                MODEL_PATH)
    print(f"Saved the variant '{best[1]}' to {MODEL_PATH.name}")


def score():
    """The one score of a model version on the locked rows, against the family words."""
    rows, saved = labelled("test"), joblib.load(MODEL_PATH)
    truth = [r["family"] for r in rows]
    print(f"{len(rows)} locked rows from {len({r['group'] for r in rows})} MAF groups: "
          + ", ".join(f"{k} {v}" for k, v in Counter(truth).most_common()))
    print(report("Family words (non-AI)", truth, [family_words(r["name"]) for r in rows]))
    print(report(f"Our model ({saved['variant']})", truth, list(saved["model"].predict([text(r, saved["fields"]) for r in rows]))))


if __name__ == "__main__":
    score() if sys.argv[1:] == ["score"] else cross_validate()
