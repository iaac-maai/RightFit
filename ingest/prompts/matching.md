# Matching documents to products: instructions

The AI follows these instructions to decide which submitted products each document covers. Today the AI reader runs them offline and writes the result into `data/maf/extracted/<package>.json`, as `matches` on each document. The checks then use these matches instead of comparing text.

## For each document and each submitted product, decide one of:
- `exact model`: the document names the submitted model, product number or configuration (spaces, dots, dashes and case don't matter: "DPK.15.80.30.5.0D" is "DPK15803050D");
- `range table row`: the document is a table for several models and the submitted model has its own row or column;
- `range`: the document names only the range or series the model belongs to ("Unilift AP" for "Unilift AP12.50.11.3"); fine for a declaration, not enough for a data sheet;
- `related`: the document is about the product but doesn't cover it (a certificate for the selection software, a report for another unit);
- nothing: the document doesn't cover the product. Write no match.

## Rules
- Each match gives the page and a quote of at most 15 words that shows the name, in the document's language.
- A range counts only if the document's own text puts the model in it. Don't use general knowledge of the manufacturer's ranges.
- Watch for near misses: a different voltage, size or variant letter is a different model ("AVW-54HJFHH2" is not "AVW-54HKFHH2").
- Never quote a client, project, company or person name.
- Every match starts as `extracted`; the reviewer confirms it in the app.

## What to return
On each document:

```json
"matches": [
  {"item": "P01-3", "kind": "range", "page": 1, "quote": "the products Unilift AP, APB, KP",
   "status": "extracted", "checked_by": null}
]
```
