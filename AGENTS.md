# AGENTS.md for RightFit

Instructions for any AI agent and any human contributor working in this repository. Read this file before making changes.

## Read first

1. `spec/constitution/mission.md`: problem, scope, principles
2. `spec/constitution/roadmap.md`: milestones, phases, features
3. `spec/constitution/tech_stack.md`: tools, architecture, data rule, repository structure
4. `spec/features/maf_checker.md`: the MAF checker, the feature we build first

If this file and the constitution disagree, the constitution wins.

## Project

RightFit checks material approval forms (MAFs) for MEP equipment before the reviewer signs them. It reads the attached documents, runs deterministic checks against EU and national rules and a checklist built from past reviewers' comments, and drafts the review with a page reference for each finding. The reviewer decides.

- Course: IAAC MaAI01, Operable Futures (2026–27). AEC phase: Design & Pre-Construction.
- First families: pumps and air handling units (with their outdoor units and DX kits). We hold two complete real packages for them, P01 and P02.
- Luca proposed the MAF review on 28 Oct 2026 and the team agreed to it on 5 Nov 2026. The kitchen hood version stays in the Git history (`main` up to `e155640`).

## Milestones (IAAC)

| Date | Deliverable |
|---|---|
| 29 Oct 2026 | Problem segmentation tree, data mapping, repository setup, initial agent test |
| 5 Nov 2026 | Midterm submission |
| 6 Nov 2026 | Midterm presentation |
| 12 Nov 2026 | Full SDD constitution, first feature with tests, first MCP connection attempt |
| 26 Nov 2026 | Full plan and build harness, MCP connectors to the mapped sources, next features |
| 3 Dec 2026 | Features and tests, comparison against the non-AI method |
| 10 Dec 2026 | Proof of concept; limits and ethics check |
| 14 Dec 2026 | Interface, testing in realistic conditions, narrative draft |
| 17 Dec 2026 | Final presentation |

## Team and ownership

| Person | Owns |
|---|---|
| Sahil | Integration, documentation, AI implementation, validation |
| Jeff | Design requirements; the fit check in Revit (`revit/`, `checks/space/`), merged on 17 Nov 2026 |
| Luca | Rules and checklist, reference answers, verification of extracted values, engineering verification |

Engineering rules in `checks/` must be approved by Luca.

## Testing context

The packages are Romanian, so the checks run for Romania (RO); Spain (ES) stays the provisional testing context of the constitution. EU product rules apply to both. Luca validates which national rules apply, and each rule carries its status in `data/maf/rules.csv`. Until a rule is verified on the official text, no check is presented as regulatory compliance.

## Core rules

1. **Never invent data.** No technical value or regulatory statement is guessed or filled from "typical" values.
2. **Every value has a source** and a status: `verified`, `extracted` or `unclear`.
3. **Checks only `pass` on `verified` inputs.** `extracted`, missing or unclear inputs produce `unclear`.
4. **AI and engineering stay separate.** Code in `checks/` is deterministic Python with no AI models. AI outputs are always labelled as AI output.
5. **Explanations are built by template from verified values.** A language model may only rephrase them, never add values.
6. **Predictions are not warnings.** Predictive output is labelled as a prediction and never shown as a check.
7. **Test data is locked.** Reference answers in `data/maf/reference/` are written before the tool's output is seen and never used for tuning.
8. **Humans decide.** The tool never certifies. Every result states what was and was not checked.
9. **No confidential material, copyrighted files or secrets in Git.** The repository is public.
10. **Decisions and scope changes are recorded in `docs/decisions.md`.**

The full principles are in `spec/constitution/mission.md` §5.

## How to work here (spec-driven development)

1. Read the relevant spec in `spec/features/` before writing code. If none exists, write or propose the spec first.
2. Make small changes. Every function in `checks/` gets tests in `tests/`.
3. Run `pytest` before committing; do not commit failing tests.
4. Prefer the standard library and few dependencies. Justify any new dependency in `docs/decisions.md`.
5. Write plain-language comments; not every teammate is a programmer.
6. If an engineering question is unclear, stop and flag it for Luca instead of assuming.
7. Record shared decisions in repository files, not only in chat.

The repository structure is in `spec/constitution/tech_stack.md` §5.

## Open decisions

Open decisions are the items tagged **[O]** in `spec/constitution/`. This file keeps no separate list.

## Current status (26 Nov 2026)

Two packages read into `data/maf/extracted/`. Of what the AI read, Luca has confirmed 1 of 116 values and 2 of 15 documents; the rest is still `extracted`. Checks, draft status and draft comments built, with 179 tests. All 28 legal rules in `data/maf/rules.csv` were read on the official text, and each rule's dates pick the law in force on the review date. Luca's reference answers are in `data/maf/reference/`; the comparison so far runs on unverified values. RightFit is one app since 21 Nov: the review, confirming readings, the answer, the rules (the law's and the consultant's own), what changed since the previous revision, the pages with their marks and booster sizing are in RightFit online; the laptop app (`app/review_server.py` with `app/review/`) adds and reads a new package (with the standby test) and keeps the BOQ files with their prices, and `web/scripts/import_project.py` puts a package online. The same checks are MCP tools an agent can call (`app/mcp_server.py`). The fit check in Revit (`revit/`, `checks/space/`) checks a pump set in its room in the project's Revit model and previews and swaps its alternatives; its rules in `data/space/rules.csv` wait for Luca. The app and every file are in English. RightFit online (`web/`, spec `spec/features/rightfit_online.md`) is the shared space around it: Google or email sign-in, a role per project, the chain of invitations (consultant, reviewers, contractor, subcontractors), Management for the team that runs it, and the legal documents in `web/legal/`; its rules and the arrangement of a review have 26 tests (`npm test` in `web/`), and it is online at https://rightfit.hackathon-team6-cubicasa-app.workers.dev, with Google sign-in, and the project's own data (packages, files, the laptop's whole review of each read package in its three steps, the rules, BOQ lines without prices) in a locked project that opens with the team password as well. Since 21 Nov the reviewers edit a review online (ticks, decisions, the consultant's rules): each change runs the same checks in a Python Worker on Cloudflare (`web/engine/`, the laptop's code in `app/review_core.py` and `app/engine.py`). Since 26 Nov a knowledge graph keeps the products that come back across projects (pipes, cables, valves, boilers), read by fixed rules from the forms, the previous project's register and the BOQ (`ingest/products.py`, `ingest/graph.py`, spec `spec/features/knowledge_graph.md`); admins see it drawn on the Inside RightFit page in Management, the consultant's people list it on the project's Product lines page, and version 2026-11-26 of the data processing agreement (clause 1.4) allows its use across a consultant's projects.
