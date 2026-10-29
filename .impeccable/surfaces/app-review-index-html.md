---
version: 1
slug: "app-review-index-html"
primary_target: "app/review/index.html"
related_targets: ["app/review/review.css","app/review/review.js"]
---

Mode: Operate. The MEP consultant reviews one MAF package and sends the answer.

Audience and job: the consultant who signs the MAF, Luca as the engineer who confirms readings, and the IAAC mentors at the PoC.

Task:
- read the draft status and its reasons;
- go through the findings and their evidence;
- decide on the AI suggestions;
- confirm what the AI read;
- copy the answer.

Content: the two real packages P01 and P02 from data/maf/extracted, checked by checks/maf through app/review_server.py.

Constraints: the page is in English, runs only locally, invents nothing, labels AI output and never certifies.

Chosen direction: Revision Cloud. The memorable moment is selecting a finding: a red revision cloud draws itself around the quoted text, carrying the finding's delta number, which is also its comment number in the answer.

Decided after the finish review:
- The location and the dates can be changed in the rail and are shown read-only in the top bar. Three inputs did not fit the top bar below 1240px, and the rail keeps them reachable at every width.
- Each reference can open the original PDF at its page, served from data/raw on the laptop only.

Unresolved:
- uploading new packages, which is later;
- keyboard shortcuts beyond the standard controls.

## Direction contract

THESIS: Every finding is a numbered revision delta, with one number in the list, on the clouded quote and in the answer. The page refuses the dashboard of status pills and KPI tiles.

OWN-WORLD:
- a drafting-film white ground and an ink #1D2125 top bar;
- a 1px hairline grid, with line weight instead of grey for hierarchy;
- red markup for rule findings, blue for the AI, green for confirmed and amber hold for unconfirmed;
- DIN lettering for labels and numbers, and a system sans for reading.

STORY: The consultant sees B and why, then opens each delta and its evidence. Every file and page reference jumps to that document. They mark what is not a problem, decide on the blue AI markups, tick readings, and copy a numbered answer.

FIRST VIEWPORT:
- the ink top bar, with the package tabs, the location and the dates;
- a left rail with the attachments, their extent bars and delta markers;
- in the centre, the B status over the revision table;
- on the right, the selected finding with its clouded quote, file, page and actions.

FORM: Revision clouds and delta tags, 4 of 7 on my list; seed:08e59b1476ee23a9.

FINISH: unreviewed and undocumented is unfinished; this build ends with the finish review, the verdict, DESIGN.md, and every shipping raster carrying its provenance
