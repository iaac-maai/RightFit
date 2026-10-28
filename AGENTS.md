# AGENTS.md — RightFit

Instructions for any AI agent (Claude, ChatGPT/Codex, Copilot) and any human contributor working in this repository. Read this file before making changes.

## Read first

1. `spec/constitution/mission.md` — problem, scope, principles
2. `spec/constitution/roadmap.md` — milestones, phases, features
3. `spec/constitution/tech_stack.md` — tools, architecture, data rule, repository structure
4. `spec/features/maf_checker.md` — the MAF checker, the feature this branch builds

If this file and the constitution disagree, the constitution wins.

## Project

On this branch (`maf-checker`) RightFit checks material approval forms (MAFs) for MEP equipment before the reviewer signs them. It reads the attached documents, runs deterministic checks against EU and national rules and a checklist built from past reviewers' comments, and drafts the review with a page reference for each finding. The reviewer decides.

- Course: IAAC MaAI01, Operable Futures (2026–27). AEC phase: Design & Pre-Construction.
- First families: pumps and air handling units (with their outdoor units and DX kits). We hold two complete real packages for them, P01 and P02.
- This is Luca's proposal, not yet agreed by Sahil and Jeff. `main` keeps the kitchen hood version.

## Milestones (IAAC)

| Date | Deliverable |
|---|---|
| 29 Oct 2026 | Problem segmentation tree, data mapping, repository setup, initial agent test |
| 5 Nov 2026 | Midterm submission |
| 6 Nov 2026 | Midterm presentation |
| 12 Nov 2026 | Full SDD constitution, first feature with tests, first MCP connection attempt |
| 17 Dec 2026 | Final presentation |

## Team and ownership

| Person | Owns |
|---|---|
| Sahil | Integration, documentation, AI implementation, validation |
| Jeff | Design requirements; his part in the MAF version is still to agree with him [O] |
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
9. **No confidential material, copyrighted files or secrets in Git.**
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

The planned repository structure is in `spec/constitution/tech_stack.md` §6.

## Open decisions

Open decisions are the items tagged **[O]** in `spec/constitution/`. This file keeps no separate list.

## Current status (28 Oct 2026, branch maf-checker)

Two packages read into `data/maf/extracted/`; all values still `extracted`, none verified. Checks, draft status, draft comments and the Streamlit page built, with tests. Luca's reference answers are in `data/maf/reference/`; the comparison so far runs on unverified values. The app and every file are in English.
