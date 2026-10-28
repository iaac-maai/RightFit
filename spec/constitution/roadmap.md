# Roadmap — RightFit

Version 0.1 (draft) · 28 Oct 2026 · Full version due 12 Nov 2026

Tags: **[C]** agreed in team discussion; formal approval of this v0.1 draft is pending · **[P]** proposed, awaiting approval · **[O]** open question

## 1. Official IAAC milestones [C]

| Date | Required deliverables |
|---|---|
| 29 Oct 2026 | Hierarchical problem segmentation tree, data mapping, repository setup, initial agent test |
| 5 Nov 2026 | Midterm submission |
| 6 Nov 2026 | Midterm presentation |
| 12 Nov 2026 | Full SDD constitution, first feature with tests, first MCP connection attempt |
| 17 Dec 2026 | Final presentation |

## 2. Development phases [P]

**P0 — Foundation (by 29 Oct)**
- Repository, `AGENTS.md`, draft constitution
- `docs/problem_segmentation.md`, `docs/data_map.md`
- Initial agent test: an AI agent reads `AGENTS.md` and the constitution and respects the rules

**P1 — Data and specifications (by 5 Nov)**
- Catalogue schema in which every value has source, page and status
- Seed catalogue of about 50 kitchen hoods from several manufacturers (Jeff)
- Audit of about 10 installation manuals: which MEP values are actually published (Luca)
- Room input schema: what the designer must describe about the room
- Written specifications for the first engineering checks (Luca)
- Engineering standards for the provisional Spanish context identified (Luca) [O]

**P2 — First feature (by 12 Nov)**
- Text/image search over the seed catalogue with a pretrained model
- Keyword search baseline on the same catalogue
- One deterministic check with automated tests
- First MCP connection attempt
- Full constitution

**P3 — Scale and interface (13–26 Nov)**
- Catalogue of 150–300 hoods, if data quality allows
- Data-sheet extraction with page citations, checked by a person
- Further checks approved by Luca
- Simple web interface

**P4 — Evaluation (27 Nov–10 Dec)**
- 20–30 design briefs, split into development and locked test sets
- Comparison against keyword search and manual process
- Blind relevance judging, timed trials

**P5 — Final (11–17 Dec)**
- Results reported honestly, including negative ones
- Pitch, demo, IAAC blog

## 3. Feature list

| ID | Feature | Type | Status |
|---|---|---|---|
| FEAT-01 | Catalogue with sourced values | Data | Planned |
| FEAT-02 | Text and image search | AI | Planned |
| FEAT-03 | Keyword search baseline | Non-AI | Planned |
| FEAT-04 | Engineering checks (e.g. duct size, ceiling void) | Deterministic | Planned, rules not yet specified |
| FEAT-05 | Explanation of trade-offs from verified fields | Template | Planned |
| FEAT-06 | Web interface | UI | Planned |
| FEAT-07 | Re-ranking from a designer's picks within a session | AI | Proposed [P] |
| FEAT-08 | Learning-to-rank across sessions | AI | Stretch, only if enough non-test data [O] |
| FEAT-09 | Prediction of installation or approval concerns | AI | Exploratory, not committed [O] |
| FEAT-10 | MCP server exposing search and checks | Integration | Planned |

No feature is considered done until it has a specification, passing tests and a review against its specification.

## 4. Responsibilities [C]

| Person | Leads | Reviews |
|---|---|---|
| Sahil | Integration, AI implementation, documentation, evaluation | Overall consistency with the constitution |
| Jeff | Catalogue, images, visual relevance, design requirements | Look relevance of results |
| Luca | Technical specifications, MEP checks, installation constraints | Engineering correctness |

All three contribute to research, testing and presentation.

## 5. Testing strategy [P]

- **Unit tests** for every engineering check, using hand-written cases with known answers approved by Luca.
- **Data tests**: every catalogue entry has source and status fields; no value without a source.
- **Retrieval evaluation**: look relevance of the top 5 results, compared with the keyword baseline.
- **Locked test set**: test briefs are never used for development or tuning.
- **Blind judging**: judges do not know which system produced a result.
- **Outside judges**: 2–3 designers outside the team, if available.

## 6. Risks [P]

| Risk | Mitigation |
|---|---|
| Installation manuals lack values the checks need | Audit 10 manuals first; checks return `unclear`; adjust check scope |
| Keyword baseline performs as well as AI search | Include image-reference briefs; report the result honestly |
| Evaluator bias (team judging its own system) | Blind judging, outside designers |
| Engineering standards unconfirmed | Spain provisional; no compliance claims until Luca validates |
| Not enough time for all features | FEAT-01–FEAT-06 and FEAT-10 are core; FEAT-07–FEAT-09 only if time allows |
| Image copyright | Images kept outside Git; not published |

## 7. Change log

| Date | Change | Agreed by |
|---|---|---|
| 28 Oct 2026 | v0.1 draft created | pending: Sahil, Jeff, Luca |