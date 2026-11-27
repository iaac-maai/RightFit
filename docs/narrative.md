# RightFit: the story (draft)

Draft of 27 Nov 2026 for the final presentation on 17 Dec (issue #23). Every number below names the file it comes from. Where a result does not exist yet, the draft says so instead of filling the gap. Luca reads it before it is used.

## 1. The problem

Before MEP equipment is ordered, the contractor sends a material approval form (MAF) with the data sheets, declarations and certificates behind it. Several people sign the same form, and each of them opens the same PDFs, often in three or four languages, looking for much the same things (`spec/constitution/mission.md` §1).

The evidence is the register of the last project Luca worked on, 80 MEP forms (`docs/maf_register_findings.md`):

- 66 forms got an answer: 44 approved, 17 approved with notes, 5 sent back. 17 needed at least one revision, one of them six.
- A form came back after a median of about 12 days. Once the last reviewer had answered, it still waited a median of 7 days before it went back to the contractor: the wait is in routing and consolidation, not only in reading.
- In a first reading of the causes, which Luca has still to confirm, 8 of the 22 returns were gaps in the package that a check can find: a range data sheet with nothing marked, a technical approval past its date, pump panels without the BMS module. At best 13 of 22 if the specification states every value. The other returns (coordination with the architecture, a design not yet approved, a sample) no document check can catch.

One of our two test packages makes the last point on its own. The air handling unit of P02 is at revision 4. Revisions 0 to 3 were not turned down for anything technical: the client wanted one brand of AHU (`data/maf/reference/P02.md`). No document check sees that unless the client's brand list is written down as a requirement.

How the work goes elsewhere is being asked in a public, anonymous practice survey (`spec/features/survey.md`). Its answers are not in the repository yet. **[gap]**

## 2. What RightFit does

In one line: AI reads, rules decide, a person signs (`spec/constitution/mission.md` §3).

1. RightFit reads the package: what each document is, which products it covers, and the values each family needs, each with its file, page and a short quote.
2. Fixed checks in plain Python compare those values with the law in force on the review date, the project's BOQ, a checklist built from the reviewers' comments in the register, and the consultant's own rules (`docs/problem_segmentation.md` §2).
3. It drafts the answer, A, B or C, and one comment per issue from templates, and opens each finding next to its page.
4. The reviewer confirms the readings, overrides what they disagree with, and signs. Nothing passes until a person has confirmed the reading behind it.

Around it: the review online for the whole chain of signers (`spec/features/rightfit_online.md`), the checks as MCP tools any agent can call (`app/mcp_server.py`), a fit check of the pump set in its room in Revit (`revit/`, `checks/space/`), and a graph of the products that come back from one project to the next (`spec/features/knowledge_graph.md`).

## 3. Why AI, and where it is not used

**Reading needs AI.** The packages come from dozens of manufacturers, in several languages, and no two data sheets look alike. The 50 packages we hold have about 1,400 PDF pages, and 34 of their 300 PDFs have no text layer (`spec/constitution/mission.md` §8).

**Deciding does not.** The person who signs must be able to defend each comment, so the same package must give the same result every time and each result must name the check behind it. The checks in `checks/` use no model, and no model can change their result (`AGENTS.md`, core rule 4).

Where the AI is, and who checks it (`docs/problem_segmentation.md` §3):

| AI part | What it does | Who checks it |
|---|---|---|
| AI reader | reads documents into values with page and quote | the reviewer confirms each value |
| Our page classifier, trained from scratch | says what kind of document each page is | measured against keywords (§4) |
| Rule from words, BOQ line | turns a typed rule, or what a BOQ line asks, into items to check | the reviewer sees each item, labelled AI, before it counts |
| Second AI reviewer | proposes issues no rule covers, with page evidence, in its own tab | the reviewer adds a suggestion or marks it not relevant |

**Why not a general chatbot**, the jury's main comment at the midterm (`spec/constitution/mission.md` §8): a chatbot can read a PDF and give an opinion. RightFit gives the same result on every run, names the check behind each result and, for the law, the rule and its source, picks the law by the review date (a review after 25 Aug 2026 cites Romania's new construction Code, not the law it replaced), passes nothing on an unconfirmed reading, and uses a checklist from 80 real forms that no chatbot has seen. Whether that finds more than a chatbot is not measured yet (§4).

## 4. Results

Every AI part is measured against the plain way of doing the same job, and the result stays in the repository whichever way it goes (`eval/README.md`).

### Where the AI beat the plain way

| What | Result | File |
|---|---|---|
| Page classifier v2 against keyword search, 184 locked real pages | 62 % right against 35 %; data sheet pages found 69 % against 9 %; declaration pages 76 % against 58 % | `eval/page_classifier/results_2026-11-11.md` |
| Page classifier v1 on public manuals with declarations inside | 87 % right against 45 % | `eval/page_classifier/results_2026-10-29.md` |

### Where it did not

| What | Result | File |
|---|---|---|
| Page classifier v1 on the pages of P01 and P02 | 25 % right against 27 % for the keywords; data sheet pages 15 % against 20 %. Its training data sheets looked nothing like real ones: the fix was data, which v2 then showed | `eval/page_classifier/results_2026-10-29.md` |
| Page classifier v2, what keywords still do better | certificates 51 % against 89 %; both fail on the one locked installation manual (13 % and 7 %) and on every scanned page | `eval/page_classifier/results_2026-11-11.md` |
| Our family model against the family's words, 37 locked rows | the words win: 35 of 37 against 28; family rows 5 of 5 against 1 of 5. 21 training rows cannot teach 13 families | `eval/family_classifier/results_2026-11-17.md` |
| AI matching of documents to products against text matching | the same answer on all 51 pairs; the AI only adds how a document covers a product | `spec/constitution/mission.md` §8 |

### Plain methods, no AI on either side

| What | Result | File |
|---|---|---|
| Finding a product's BOQ line | the first rule (the pump's duty) found 4 of 24; the position the form names, then text similarity, found 24 of 24. Designed on those 24 cases, so not a test yet | `eval/boq_matching/results_2026-11-13.md` |
| What changed between two revisions | on one pair (P10 to P02), file digests and text similarity paired 6 attachments where names alone paired 3, and found a data sheet whose name changed but whose bytes did not. Thresholds set on that pair | `eval/revisions/results_2026-11-17.md` |

### The review against Luca's reference answers

Luca wrote his answers on 28 Oct, before seeing the tool's checks, but after a short summary of what the AI read, which for P01 named the missing declarations (`data/maf/reference/`). The checks were run on 27 Nov 2026 (`review_package` in `app/mcp_server.py`), with each form's own date as the review date (16 and 19 Mar 2026), so with the law in force then, and on values that are still almost all unconfirmed:

| | Luca | Reality | RightFit would draft |
|---|---|---|---|
| P01, pumps | A, nothing to flag; about 10 minutes, figures only | A | B: 20 problems, 6 questions |
| P02, air handling unit | A, nothing to flag; about 3 hours | revisions 0 to 3 turned down for the brand | B: 4 problems, 12 questions |

What this shows, and what it does not:

- Found by both: nothing, because Luca flagged nothing. Missed by the tool: nothing Luca flagged. The brand reason belongs to revisions 0 to 3, which these runs do not cover.
- Found only by the tool, for example: P01 lacks the EU declarations of two pump sets, which the manufacturer publishes in its manuals (Luca had read this in the summary, so it is not a blind finding); of its two declarations, the one for SL1/SLV names none of the submitted pumps. P02's listed declaration covers residential split units, not the AHU, and the attachment called "TUV CTA" is a different kind of certificate. Whether each of these is a real problem is Luca's to judge, and is not recorded yet. **[gap]**
- About 14 of P01's 20 problems come from the BOQ line, the reviewers' checklist and the consultant's own rules asking for a panel or a BMS module the sheet does not state as included. Pump panels without the BMS module are one of the register's examples of a gap (§1); repeated per pump and per source, they are also the most likely source of noise.
- Nearly every result is "would be": of 116 values in P01 and P02, Luca has confirmed 1 (`AGENTS.md`, current status). The comparison has to be run again on confirmed values.
- The roadmap asks for this comparison to be written down in `eval/`, good or bad (`spec/constitution/roadmap.md` §3). It is not yet. **[gap]**

One issue the documents show and no check covers: P02's DX coil is selected for R32 while the outdoor units and both selection reports use R410A (`docs/data_map.md`).

### Not measured yet

| What | State | File |
|---|---|---|
| RightFit against general chatbots | protocol written before any run, test set of 21 unseen packages frozen, 20 of them readable (one archive is incomplete); no run | `eval/chatbot_baseline/protocol.md`, `spec/constitution/roadmap.md` MAF-01 |
| Time by hand against time with RightFit | 5 separate packages set aside for it, read on 27 Nov; not timed | `eval/chatbot_baseline/protocol.md`, `docs/decisions.md` (27 Nov) |
| The AI reader against a person reading | 1 of 116 values confirmed | `AGENTS.md` |
| The second AI reviewer | first run on P01 (3 suggestions) and P02 (5); none judged | `spec/constitution/roadmap.md`, MAF-14 |
| The fit check in Revit | built, rules approved on 26 Nov; no result against a person's check | `docs/decisions.md` (26 Nov) |

## 5. Limits

- RightFit checks what the documents say. A correct data sheet does not mean a correct installation, and a value the manufacturer does not publish stays missing (`spec/constitution/mission.md` §7).
- Two packages make a demonstration, not an evaluation. All 50 packages come from one project, and the checklist comes from a register Luca kept, so a comment common there may be rare elsewhere (`spec/constitution/mission.md` §9).
- Luca writes the reference answers and also judges the findings. Writing them before seeing the tool's checks and hiding the source while judging reduce this bias, but for P01 and P02 he had seen a summary of what the AI read; a second reviewer from outside the team is planned, not found (`eval/chatbot_baseline/protocol.md`).
- A rule is only as current as its last check: on 12 Nov we found that Romania's Law 10/1995, behind two rules, had been repealed in August (`spec/constitution/mission.md` §7). The rule watch now asks the official sources (`docs/decisions.md`, 17 Nov).
- Scanned pages without text are wrong for both page classifiers (`eval/page_classifier/results_2026-11-11.md`).
- Packages pass through an online AI model to be read: P01 and P02 by an AI agent on Luca's laptop, and since Luca agreed on 27 Nov, the remaining packages too; which model and what it costs are still open (`spec/constitution/mission.md` §9).
- RightFit never certifies. The person who signs carries the responsibility (`spec/constitution/mission.md` §9).

## 6. What would change the story

- If the chatbots find as much as RightFit at the same quality, we say so and change course (`spec/constitution/mission.md` §8).
- If the draft does not save Luca time on new packages, or misses what he thinks matters, we say so (`spec/constitution/mission.md` §6).

## 7. Before 17 Dec

1. Luca confirms the readings of P01 and P02, and the comparison with his reference answers runs again and is written in `eval/`.
2. Luca judges the tool-only findings of P01 and P02: real or not.
3. The chatbot run and the timed review on the test set (3 Dec).
4. The survey's answers, with how many people gave them.
