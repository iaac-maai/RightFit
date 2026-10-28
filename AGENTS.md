# AGENTS.md — RightFit

Instructions for any AI agent (Claude, ChatGPT/Codex, Copilot) and any human contributor working in this repository. Read this file before making changes.

## Read first

1. `spec/constitution/mission.md` — problem, scope, principles
2. `spec/constitution/roadmap.md` — milestones, phases, features
3. `spec/constitution/tech_stack.md` — tools, architecture, data rule, repository structure

If this file and the constitution disagree, the constitution wins.

## Project

RightFit is an AI-assisted product selection and MEP coordination tool for architects and interior designers. A designer describes a product (text or reference image); the system finds visually and semantically relevant products, runs deterministic MEP checks against the room's known constraints, and explains trade-offs with source evidence.

- Course: IAAC MaAI01, Operable Futures (2026–27). AEC phase: Design & Pre-Construction.
- First and only product family for the prototype: **kitchen extraction hoods**.

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
| Jeff | Hood catalogue, product images, visual relevance, design requirements |
| Luca | Specifications, airflow, ducting, installation constraints, engineering verification |

Engineering rules in `checks/` must be approved by Luca. Visual relevance judgements belong to Jeff.

## Testing context

Spain is the provisional testing context. Luca must validate which engineering standards apply. Until then, no check is presented as regulatory compliance.

## Core rules

1. **Never invent data.** No technical value or regulatory statement is guessed or filled from "typical" values.
2. **Every value has a source** and a status: `verified`, `extracted` or `unclear`.
3. **Checks only `pass` on `verified` inputs.** `extracted`, missing or unclear inputs produce `unclear`.
4. **AI and engineering stay separate.** Code in `checks/` is deterministic Python with no AI models. AI outputs are always labelled as AI output.
5. **Explanations are built by template from verified values.** A language model may only rephrase them, never add values.
6. **Predictions are not warnings.** Predictive output is labelled as a prediction and never shown as a check.
7. **Test data is locked.** Briefs in `eval/test/` are never used for tuning or preference learning.
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

## Current status (28 Oct 2026)

Repository created. No catalogue data collected, no model trained or tuned, no results.
