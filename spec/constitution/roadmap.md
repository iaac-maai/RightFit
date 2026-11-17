# RightFit roadmap

Full version for 12 Nov 2026, brought up to date on 16 Nov 2026. It is built on the MAF direction the team agreed on 5 Nov 2026. Open questions are marked [O].

## 1. IAAC milestones

| Date | What IAAC asks for |
|---|---|
| 29 Oct 2026 | Problem segmentation tree, data mapping, repository setup, initial agent test |
| 5 Nov 2026 | Midterm submission |
| 6 Nov 2026 | Midterm presentation |
| 12 Nov 2026 | Full SDD constitution, first feature with tests, first MCP connection attempt. Target: we can argue why AI is needed, and a first feature can be measured against the baseline |
| Between 12 and 26 Nov | Hackathon week, no studio. Target: a beta version |
| 26 Nov 2026 | Full plan and build harness, MCP connectors to all mapped sources, next features from the roadmap |
| 3 Dec 2026 | Features and tests, comparison against the non-AI method, problem and data map refined |
| 10 Dec 2026 | Physical or digital proof of concept; limits and ethics check (data ownership, bias, responsibility) |
| 14 Dec 2026 | Interface, testing in realistic conditions, narrative draft |
| 17 Dec 2026 | Final presentation |

## 2. Where we are on 16 Nov

We have the feature spec, the rules and checklist tables, two packages read into JSON, the checks with 107 tests, one application for the whole review, the checks as MCP tools, and Luca's reference answers for both packages. Since 12 Nov the application works per project, reads the project's BOQ, takes the consultant's own rules, follows the law in force on the review date, and checks the drinking water approval and the liquid temperature of pumps. Luca has also set two engineering inputs: no tolerance on the duty point, and the control panel for pumps as a consultant's rule, not a legal one. The midterm on 6 Nov showed the pump workflow, and the jury's main comment was that RightFit has to differ clearly from a general chatbot.

What's missing is Luca's check of what the AI read (1 of 116 values and 2 of 15 documents so far), so every result is what a check would say once its readings are confirmed, and the comparison with his answers is still on unverified values. All 28 legal rules have been read on the official text, the last nine on 16 Nov; the other four are practice or an engineer's input. 48 more packages from the same project came in on 6 Nov; the app lists them and none is read yet. The chatbot test has its protocol and a frozen test set, and no run.

## 3. Phases

By 29 Oct we handed in the repository, `AGENTS.md`, the constitution draft, the problem tree, the data map and the first agent test. They describe the MAF review; the hood versions stay in the Git history.

The midterm on 5 and 6 Nov showed the pump workflow on real files: package check, booster sizing and standby test. The plan was for Luca to verify the extracted values before it. That didn't happen, and it moves to the next phase, with the draft status rules and the reading of the Romanian law and the Spanish RITE article on the official journals.

By 12 Nov: the full constitution, the feature spec, and a first feature with tests that can be measured against a baseline, which is the page classifier against a keyword search (MAF-16): 62 % of locked real package pages right, against 35 %. The first MCP connection is done: the checks are tools an agent can call (`app/mcp_server.py`), and an agent connects to it through `.mcp.json`. [O] The team confirms which agent.

From 13 to 26 Nov, with the hackathon week in the middle. Done by 16 Nov: the BOQ reader with check Q, the consultant's rules, projects, the Romanian rules under the new construction Code, document rules for nine families of the second batch, and every legal rule read on its official text. Still to do: Luca verifies the values of P01 and P02 in the app and we compare the tool with his reference answers again, writing the result in the repository, good or bad. We run the chatbot baseline (MAF-20), and once Luca has answered the three questions on set A labels, the second page classifier is scored on the first test sets. We read the first packages of the second batch with page citations, and a person checks them before any check uses them. By 26 Nov we also need the full plan and build harness and MCP connectors to the mapped sources. The first one was built on 17 Nov: the rule watch asks the official law sources (the Publications Office, the BOE, legislatie.just.ro) about every legal rule (MAF-10). [O] Whether the manufacturer documents library comes next.

From 27 Nov to 10 Dec we evaluate on packages we did not use while building: findings against the reference, draft status against the reviewer's, time by hand against time with the tool, and RightFit against the non-AI method (3 Dec). On 10 Dec comes the limits and ethics check. [O] A second reviewer outside the team.

The last week, 11 to 17 Dec, is for testing in realistic conditions, writing up the results (the negative ones too), the Lean Canvas, the pitch, the demo and the IAAC blog post.

## 4. Features

The hood features (image search, keyword baseline, re-ranking from a designer's picks) are not needed for this use case, so the list below replaces them. The IDs are new to avoid mixing them up with the FEAT numbers on `main`.

| ID | Feature | How it works | Status |
|---|---|---|---|
| MAF-01 | Reading a package into sourced values | The AI reads; a person verifies each value | Done for P01 and P02; 1 of 116 values confirmed so far |
| MAF-02 | Reading the form (.xls), roles only | Plain Python | Done |
| MAF-03 | Document checks D1–D4 | Rules | Done, tested; since 12 Nov D1 also knows the documents of nine families of the second batch |
| MAF-04 | Value checks V1, V2, V3 and ecodesign E1 | Rules | Done, tested; no tolerance on the duty point (Luca) |
| MAF-05 | Reviewers' checklist (C) and delivery reminders by location (R) | Rules | Done, tested |
| MAF-06 | Draft status and draft comments | Written rules and templates | Done; the status rules wait for Luca |
| MAF-07 | Review application | Standard library server, plain HTML, CSS and JavaScript | New version 11 Nov: one application for the packages, the review, confirming readings and the answer; it replaces the Streamlit page and the midterm page. Since 12 Nov also the Rules screen, the projects and the BOQ files |
| MAF-08 | Comparison with the reference answers | A small script and a table | First pass done on unverified values |
| MAF-09 | MCP server with the checks | Integration: the official MCP Python SDK; five read-only tools (list the packages, review one, list the rules, classify pages, watch the rules' sources) | First version 10 Nov, tested over stdio; each person approves the server once in their agent |
| MAF-10 | Rule watch: asks the official source of every legal rule whether its act changed since the rule was read | Plain Python against the Publications Office, the BOE and legislatie.just.ro; a fifth read-only MCP tool (`watch_rules`) | Built 17 Nov (`ingest/rule_watch.py`). Run on 17 Nov: all 28 legal rules unchanged. It only reports: a person reads a changed act again and decides. [O] How often it runs and who reads the report |
| MAF-11 | Manufacturer documents library. When a package lacks a document (a declaration, a data sheet for the exact model, a certificate, a manual), the AI looks for it on the manufacturer's official site (Grundfos, Wilo, FläktGroup, Hisense, Danfoss, Siemens and so on) and records the models it covers, the directives or standards, the date and the link. A person confirms each entry once, and later projects reuse it. The review then says whether the document exists and was only left out | AI searches and reads; a rule compares | Started 29 Oct in `data/maf/library.json`: Grundfos publishes the two declarations missing from P01 (the Hydro Multi-E one dates from 2011); FläktGroup doesn't publish one for CAIRplus |
| MAF-15 | AI matching of documents to products: for each document, which submitted products it covers and how (exact model, row in a range table, range only, related), with page and quote; the checks use these matches and the reviewer confirms them | AI matches, a person confirms | Done for P01 and P02; agrees with the old text matching on all 51 document-product pairs and adds how each document covers the product; instructions in `ingest/prompts/matching.md` |
| MAF-14 | Second AI reviewer: proposes issues no rule covers, each with page evidence, in its own tab; the reviewer adds a suggestion to the answer or marks it not relevant | AI proposes, a person decides | First run on P01 (3 suggestions) and P02 (5); instructions in `ingest/prompts/second_reviewer.md` |
| MAF-12 | Certification dossier for BREEAM, LEED or VERDE, built from the confirmed values, with what is still missing for each credit (the outdoor units' GWP, for one) | AI drafts from confirmed values | Idea; [O] which credits, with Sahil or Jeff |
| MAF-13 | Add a package in the app. The form is read on the spot; the attachments go to the AI reader, which returns values with page and quote for the reviewer to confirm | AI reads, a person confirms | Pumps only since the midterm: the text, the declarations and the curves are read on the spot with fixed patterns and OCR. A package added this way can be saved into the project (12 Nov). Other families and the AI reader after the PoC; [O] which model, its cost, and whether real packages may be sent to it |
| MAF-16 | Page classifier: what kind of document each PDF page is | Our own model, trained from scratch, against a keyword search | First version 29 Oct: 25 % right against 27 % on real package pages, 87 % against 45 % on manuals (`eval/page_classifier/`). Second version 11 Nov, also trained on the second batch: 62 % right against 35 % on 184 locked pages of real packages. Its score on the first test sets waits for Luca's three answers on set A |
| MAF-17 | Pump package check on added files: the declaration, and MEI and IE class where they apply | Fixed patterns and OCR read the files; rules decide | Done for the midterm, tested; Luca still has to confirm three inferences about which rules apply to a pump |
| MAF-18 | Booster sizing: peak flow (DIN 1988-300), head (CTE DB-HS4), 289 Lowara sets | Rules | Done, tested |
| MAF-19 | Standby test: does the set meet its duty with one pump out | The curve is read from the data sheet's vector drawing; rules decide | Done, tested |
| MAF-20 | Chatbot baseline: the same packages go to general chatbots, and findings are judged with the source hidden | Comparison | Protocol written 10 Nov and tightened on 13 Nov, with a frozen test set of 21 unseen packages for accuracy and 5 for time (`eval/chatbot_baseline/`); no run yet |
| MAF-21 | Drinking water approval for booster sets and hot water pumps (H1), and the hot water temperature in V3 | Rules | Done 12 Nov, tested; asked for by a practising MEP consultant |
| MAF-22 | The consultant's own rules (check P), added on the Rules screen by hand or typed in words | Rules decide; an AI turns the words into a rule, which the consultant saves or not | Done 12 Nov, tested |
| MAF-23 | The project's BOQ (check Q): reading it, finding a product's line, checking what the line asks | Plain Python reads and matches; an AI lists what a line asks; rules check it | Done 12 and 13 Nov, tested. The way a line is found was chosen in a study on 24 products (`eval/boq_matching/`) |
| MAF-24 | Projects: each one keeps its packages, their original files and its BOQs in a folder that can be shared | Plain Python | Done 12 Nov, tested |
| MAF-25 | The law in force on the review date: each rule has the dates it applies between | Rules | Done 12 Nov for Romania (Law 10/1995, then the construction Code) and for the machinery rules |
| MAF-26 | What changed since the previous revision of a form: each attachment unchanged, changed, new or removed | Plain Python: file digests, then text similarity (TF-IDF), or the look of the pages for a scan; the similarity search of the AI Methods hackathon, with no trained model | Built 17 Nov (`ingest/revisions.py`, the review page, a sixth MCP tool `compare_revisions`); shown on P10 to P02 only, as the other two pairs are in the frozen chatbot test set |

A feature is done when it has a spec, passing tests and a review against the spec.

## 5. Who does what

| Person | Leads | Checks |
|---|---|---|
| Sahil | Integration, AI reading, documentation, evaluation | That the work matches the constitution |
| Jeff | [O] To agree with Jeff. The spec leaves two things open that fit his side: sustainability values for the checklist (LEED, BREEAM, VERDE) and the items the architect has to see (CL-10) | The design side of the checklist |
| Luca | Rules and checklist, reference answers, verifying the values the AI read | Engineering correctness |

All three of us share the research, testing and presentation.

## 6. Testing

Every check has unit tests with hand written cases, which Luca approves. Data tests make sure every value has a source, page and status, quotes stay short, and no name from the local names list ends up in Git. Reference answers are written before the tool's output is seen, live in `data/maf/reference/`, and are never used for tuning. And since the checklist was built from the register, we never evaluate it on the register. Each AI part is compared with the plain way of doing the same job, as listed in `mission.md` §8.

## 7. Risks

| Risk | What we do about it |
|---|---|
| Two packages are very few | 48 more from the same project are on the laptop, not read yet; results stay a demonstration until they are |
| All packages come from one project | We say so with every result; packages from other practitioners need the owning company's permission [O] |
| The AI misreads or misses a value | Every value starts as `extracted`, with page and quote; checks wait for a person to verify it |
| A rule goes out of date | Each rule carries its source, its status and the date it was read. By 16 Nov all 28 legal rules were read on the official text. One of them had been repealed three months earlier without anyone noticing (Law 10/1995), so since 17 Nov the rule watch (MAF-10) asks each rule's official source whether its act changed. [O] How often it runs |
| A general chatbot finds as much as RightFit | We measure it (MAF-20), keep the result whichever way it goes, and change course if it does |
| Luca built the checklist and is also the only reviewer | He writes the reference before seeing the tool; [O] a second reviewer |
| Scanned PDFs without text | They are read from the page image and marked for a closer check |

Changes to this file are recorded in `docs/decisions.md`.
