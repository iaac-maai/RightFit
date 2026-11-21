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

The trained models stay out of Git, because the page classifier keeps the words it learned from real documents, and a few of them are names. They are on the laptop in `data/raw/models/`. The two scored versions, `page_classifier_v2.joblib` and `family_classifier.joblib`, are also in a private repository on Hugging Face, `lucaobejdeanu/rightfit-models`, with a card that explains them and how to load them. That repository must never be made public or moved to an organisation, where every member would see it.
