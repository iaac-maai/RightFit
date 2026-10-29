"""Page classifier: what kind of document each PDF page is.

Two ways to answer, compared on the same locked test pages (eval/page_classifier/):
- keyword_baseline: the non-AI way, the words a reviewer would search for;
- a model we train from scratch on public manufacturer PDFs: character and word n-grams (TF-IDF) and a
  logistic regression. No pretrained weights; everything it knows comes from our training pages.
"""
import re
import unicodedata
from pathlib import Path

import pypdf
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import FeatureUnion, make_pipeline

CLASSES = ("declaration", "data_sheet", "certificate", "manual", "other")
MIN_TEXT = 80  # a page with less text than this is a cover, a blank page or a scan without a text layer


def pdf_pages(path):
    """One dict per page: file, page number (from 1) and its text layer ('' for scanned pages)."""
    reader = pypdf.PdfReader(str(path))
    return [{"file": str(path), "page": i, "text": (p.extract_text() or "").strip()}
            for i, p in enumerate(reader.pages, 1)]


def normalize(text):
    """Lower case, no diacritics, single spaces: 'Declaraţie' and 'declaratie' become the same word."""
    text = unicodedata.normalize("NFKD", text.lower())
    return re.sub(r"\s+", " ", "".join(c for c in text if not unicodedata.combining(c))).strip()


# The words a reviewer would search for, in the languages of our packages, checked in this order.
KEYWORDS = {
    "declaration": ["declaration of conformity", "declaratie de conformitate", "konformitatserklarung",
                    "declaracion de conformidad", "dichiarazione di conformita", "declaration de conformite",
                    "declaration of performance", "declaratia de performanta", "leistungserklarung",
                    "declare under our sole responsibility", "declaram pe propria raspundere",
                    "erklaren in alleiniger verantwortung", "declara bajo su exclusiva responsabilidad"],
    "certificate": ["certificate", "certificat", "zertifikat", "certificado", "certificato"],
    "manual": ["installation and operating instructions", "instructiuni de instalare", "operating instructions",
               "betriebsanleitung", "instrucciones de instalacion", "istruzioni di installazione",
               "notice d'installation", "safety instructions", "operating guide", "installation guide"],
    "data_sheet": ["data sheet", "datasheet", "fisa tehnica", "datenblatt", "ficha tecnica", "technical data",
                   "date tehnice", "date electrice", "technische daten", "datos tecnicos", "dati tecnici",
                   "product number", "product code", "nr. produs", "cod produs", "artikelnummer", "q [m", "h [m]"],
}


def keyword_baseline(text):
    """The non-AI method: the first keyword group found on the page decides."""
    text = normalize(text)
    if len(text) < MIN_TEXT:
        return "other"
    return next((cls for cls, words in KEYWORDS.items() if any(w in text for w in words)), "other")


def build_model():
    """Untrained model: letter groups of 3 to 5 (robust to six languages and odd PDF spacing) plus word pairs."""
    features = FeatureUnion([
        ("chars", TfidfVectorizer(preprocessor=normalize, analyzer="char_wb", ngram_range=(3, 5), min_df=2,
                                  sublinear_tf=True, max_features=200_000)),
        ("words", TfidfVectorizer(preprocessor=normalize, ngram_range=(1, 2), min_df=2, sublinear_tf=True)),
    ])
    return make_pipeline(features, LogisticRegression(max_iter=3000, class_weight="balanced"))


def predict(model, texts):
    """Pages without enough text are 'other' for the model too, as for the baseline: neither can read a scan."""
    out = list(model.predict([t or " " for t in texts]))
    return [label if len(normalize(t)) >= MIN_TEXT else "other" for t, label in zip(texts, out)]


def load_pages(paths):
    return [page for path in paths for page in pdf_pages(Path(path))]
