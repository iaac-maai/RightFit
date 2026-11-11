---
version: 1
slug: "app-review-index-html"
primary_target: "app/review/index.html"
related_targets: ["app/review/app.css","app/review/app.js"]
---

Mode: Operate. One application: the MEP consultant picks a package, goes through its problems beside the documents, confirms what the AI read and sends the answer. Used at a desk, on real packages, for long stretches.

Audience and job: the consultant who signs the MAF, Luca as the engineer who confirms readings, and the IAAC mentors at the PoC.

Task:
- see the draft answer and how much remains;
- go through the problems product by product, with the real page open beside each one;
- decide on the AI suggestions;
- confirm what the AI read;
- copy the answer.

Content: the packages in data/maf/extracted, checked by checks/maf through app/review_server.py, the packages on the laptop that are not read yet, adding a package with live reading, booster sizing, the standby test and the rules. One application replaces the old review page, the midterm demo and the Streamlit page.

Constraints: the page is in English, runs only locally, invents nothing, labels AI output and never certifies. Location and dates stay out of the first view: one plain sentence says what was checked, and the change control sits with it in the Answer step. Each view is its own file, so a new tool is one file and one line in the router.

Chosen direction: Triplicate. The memorable moment is confirming a reading: it re-inks from carbon violet to black.

Unresolved:
- OCR positions, so a line can be marked on a scanned page;
- reading the packages that are not read yet.

## Direction contract

THESIS: One application where every problem sits beside the exact line on the real page, and the ink says what a person has confirmed. It refuses the three-column desk of codes, counts and markup symbols.

OWN-WORLD: the approval form in triplicate. A bottle-green #0E3B2E rail, a pale form-green #E7F0E8 ground, white sheets, printed labels in small capitals, values typed in bold Courier. Carbon violet #4A32B8 with a dashed underline for everything the AI read and nobody confirmed; black with a solid underline once a person has. Red only for problems, ochre only for questions.

STORY: The consultant opens a package, sees the draft answer and what remains, goes through the problems product by product with the page open beside them, confirms readings by re-inking them, and copies the answer.

FIRST VIEWPORT: a 196px green rail with Packages, Add a package, Booster sizing, Standby test and Rules. A head row with the form number, the package, the draft answer letter and ticks for what remains. Tabs 1 Problems, 2 Confirm readings, 3 Answer. On the left a white sheet of problems grouped by product, one open at a time with its sentence, its readings and Keep, Not a problem, Next. On the right the real PDF page at a fixed scale with the quoted lines marked. Signature: confirming a reading re-inks it left to right from carbon violet to black, on the sheet and on the page.

FORM: The transmittal form in triplicate, 7 of 7 on my list; seed:77465a8b5c51392b.

FINISH: unreviewed and undocumented is unfinished; this build ends with the finish review, the verdict, DESIGN.md, and every shipping raster carrying its provenance
