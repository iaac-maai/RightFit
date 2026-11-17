# model: our own models

The models the team trained from scratch. Each one is compared with a plain rule in `eval/`.

| File | What it is |
|---|---|
| `page_classifier.py` | the page classifier: what kind of document a PDF page is (declaration, data sheet, certificate, manual or other) |
| `train_pages.py` | trains it |
| `evaluate_pages.py` | scores it once on a locked set |
| `batch2.py` | the labels of the second batch, taken from file names and forms |
| `family_rows.py` | the product rows of the forms, split so that the test rows stay locked |
| `family_classifier.py` | the family model, and the family's words it is compared with |

The trained models stay on the laptop, in `data/raw/models/`.
