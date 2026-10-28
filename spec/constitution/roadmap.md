# Roadmap — RightFit

Draft for the MAF proposal on branch `maf-checker`, 28 Oct 2026. Sahil and Jeff have not agreed to it yet. Open questions are marked [O].

## 1. IAAC milestones

| Date | What IAAC asks for |
|---|---|
| 29 Oct 2026 | Problem segmentation tree, data mapping, repository setup, initial agent test |
| 5 Nov 2026 | Midterm submission |
| 6 Nov 2026 | Midterm presentation |
| 12 Nov 2026 | Full SDD constitution, first feature with tests, first MCP connection attempt |
| 17 Dec 2026 | Final presentation |

## 2. Where we are on 28 Oct

On this branch we have the feature spec, the rules and checklist tables, both packages read into JSON, the checks with their tests, a first Streamlit page, and Luca's reference answers for both packages. Luca has also set two engineering inputs: no tolerance on the duty point, and which pump groups need a control panel. What's missing is his check of the extracted values, so the first comparison with his answers (in `agent/LOG.md`, local) is still on unverified values.

## 3. Phases

By 29 Oct we hand in the repository, `AGENTS.md`, the constitution draft, the problem tree, the data map and the first agent test. The hood version of these is on `main`; this branch rewrites them for the MAF review, and the team chooses which version to hand in.

Before the midterm on 5 Nov, Luca verifies the extracted values in the app. We compare the tool with his reference answers again and write the result in the repository, good or bad. Luca also confirms the draft status rules, and we check the Romanian law and the Spanish RITE article on the official journals instead of the secondary sites we used so far. At the midterm we demo both packages with that comparison.

By 12 Nov we need the full constitution, the feature spec approved and a first MCP connection: the checks exposed as tools an agent can call. [O] Which agent client we connect.

From 13 to 26 Nov we add more packages from Luca's practice, anonymised, and one new family (fire dampers or valves). New packages are read with page citations and checked by a person before any check uses them.

From 27 Nov to 10 Dec we evaluate on packages we did not use while building: findings against the reference, draft status against the reviewer's, time by hand against time with the tool. [O] A second reviewer outside the team.

The last week, 11 to 17 Dec, is for writing up the results (the negative ones too), the pitch, the demo and the IAAC blog post.

## 4. Features

The hood features (image search, keyword baseline, re-ranking from a designer's picks) are not needed for this use case, so the list below replaces them. The IDs are new to avoid mixing them up with the FEAT numbers on `main`.

| ID | Feature | How it works | Status |
|---|---|---|---|
| MAF-01 | Reading a package into sourced values | The AI reads; a person verifies each value | Done for P01 and P02; nothing verified yet |
| MAF-02 | Reading the form (.xls), roles only | Plain Python | Done |
| MAF-03 | Document checks D1–D4 | Rules | Done, tested |
| MAF-04 | Value checks V1, V2 and ecodesign E1 | Rules | Done, tested; no tolerance on the duty point (Luca) |
| MAF-05 | Reviewers' checklist (C) and delivery reminders by location (R) | Rules | Done, tested |
| MAF-06 | Draft status and draft comments | Written rules and templates | Done; the status rules wait for Luca |
| MAF-07 | Review page | Streamlit | First version done |
| MAF-08 | Comparison with the reference answers | A small script and a table | First pass done on unverified values |
| MAF-09 | MCP server with the checks | Integration | Planned for 12 Nov |
| MAF-10 | Rule watch: a rule goes back to "to confirm" when its source changes | Scheduled check | Idea only [O] |
| MAF-11 | Manufacturer documents library. When a package lacks a document (a declaration, a data sheet for the exact model, a certificate, a manual), the AI looks for it on the manufacturer's official site (Grundfos, Wilo, FläktGroup, Hisense, Danfoss, Siemens and so on) and records the models it covers, the directives or standards, the date and the link. A person confirms each entry once, and later projects reuse it. The review then says whether the document exists and was only left out | AI searches and reads; a rule compares | Started 29 Oct in `data/maf/library.json`: Grundfos publishes the two declarations missing from P01 (the Hydro Multi-E one dates from 2011); FläktGroup doesn't publish one for CAIRplus |
| MAF-15 | AI matching of documents to products: for each document, which submitted products it covers and how (exact model, row in a range table, range only, related), with page and quote; the checks use these matches and the reviewer confirms them | AI matches, a person confirms | Done for P01 and P02; agrees with the old text matching on all 51 document-product pairs and adds how each document covers the product; instructions in `ingest/prompts/matching.md` |
| MAF-14 | Second AI reviewer: proposes issues no rule covers, each with page evidence, in its own tab; the reviewer adds a suggestion to the answer or marks it not relevant | AI proposes, a person decides | First run on P01 (3 suggestions) and P02 (5); instructions in `ingest/prompts/second_reviewer.md` |
| MAF-12 | Certification dossier for BREEAM, LEED or VERDE, built from the confirmed values, with what is still missing for each credit (the outdoor units' GWP, for one) | AI drafts from confirmed values | Idea; [O] which credits, with Sahil or Jeff |
| MAF-13 | Upload a package in the app. The form is read on the spot; the attachments go to the AI reader, which returns values with page and quote for the reviewer to confirm | AI reads, a person confirms | After the PoC; [O] which model, its cost, and whether real packages may be sent to it |

A feature is done when it has a spec, passing tests and a review against the spec.

## 5. Who does what

| Person | Leads | Checks |
|---|---|---|
| Sahil | Integration, AI reading, documentation, evaluation | That the work matches the constitution |
| Jeff | [O] To agree with Jeff. The spec leaves two things open that fit his side: sustainability values for the checklist (LEED, BREEAM, VERDE) and the items the architect has to see (CL-10) | The design side of the checklist |
| Luca | Rules and checklist, reference answers, verifying the values the AI read | Engineering correctness |

All three of us share the research, testing and presentation.

## 6. Testing

Every check has unit tests with hand written cases, which Luca approves. Data tests make sure every value has a source, page and status, quotes stay short, and no name from the local names list ends up in Git. Reference answers are written before the tool's output is seen, live in `data/maf/reference/`, and are never used for tuning. And since the checklist was built from the register, we never evaluate it on the register.

## 7. Risks

| Risk | What we do about it |
|---|---|
| Two packages are very few | Ask for more from Luca's practice, anonymised, and present results as a demonstration until then |
| The AI misreads or misses a value | Every value starts as `extracted`, with page and quote; checks wait for a person to verify it |
| Some rules were read on secondary sites | Each rule carries its status; the official texts are checked before the midterm |
| Luca built the checklist and is also the only reviewer | He writes the reference before seeing the tool; [O] a second reviewer |
| The team keeps the hood version | `main` stays as it is; this branch remains a proposal |
| Scanned PDFs without text | They are read from the page image and marked for a closer check |

Changes to this file are recorded in `docs/decisions.md`.
