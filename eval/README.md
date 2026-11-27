# eval: every comparison with the plain way

Each AI part of RightFit is measured against the way it would be done without AI. A test set is locked before the first score, and each version is scored on it once.

| Folder | What it compares | Result so far |
|---|---|---|
| `page_classifier/` | our page classifier against a keyword search | 62 % of pages right against 35 % (version 2) |
| `family_classifier/` | our family model against the family's words | 28 of 37 rows against 35: the words win |
| `boq_matching/` | ways to find a product's BOQ line | 24 of 24 against 4 for the old rule |
| `revisions/` | what changed between two revisions of a form | the first run, on P10 and P02 |
| `reference_answers/` | RightFit's draft answer against Luca's reference answers | P01 and P02: B against his A for both, on confirmed readings; the gap comes from documents and checklist he did not check by hand |
| `chatbot_baseline/` | RightFit against general AI chatbots | the protocol, the frozen test set and the blind list with its scores (`blind.py`); no run yet |
