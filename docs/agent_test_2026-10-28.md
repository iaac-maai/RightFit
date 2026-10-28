# Initial Agent Test — RightFit

## 1. Test

- Date: 28 Oct 2026
- Agent: Claude Code version 2.1.312, plan mode
- Purpose: initial agent test for the IAAC deliverable of 29 Oct 2026

## 2. Prompt used

```text
This is an initial agent test for our IAAC project. Do not modify any files and do not run any git commands.

Read AGENTS.md, all files in spec/constitution/, and all files in docs/. Then report:

1. The project's scope in 3 sentences.
2. The rules you must follow when working in this repository.
3. Three things you must never do here.
4. Every open question [O] you found.
5. Any inconsistencies or contradictions between the files, and any file that is referenced but does not exist.

Answer only from what is written in the files. If something is unclear, say so instead of guessing.
```

## 3. Result summary

The agent read the files and stated the scope, rules and prohibitions correctly. It changed no project files.

## 4. Inconsistencies found and how they were resolved

| # | Finding | Resolution |
|---|---|---|
| 1 | Jurisdiction: `AGENTS.md` said Spain (CTE) or Romania; all other files say Spain provisional | `AGENTS.md` rewritten: Spain provisional, Luca validates standards, no mention of Romania |
| 2 | Other product families: "Undecided [O]" in `mission.md`, "out of scope [C]" in `problem_segmentation.md` | Moved to "Out of scope [C]" as future work in `mission.md` |
| 3 | Items tagged [C] "confirmed by the team" in unapproved v0.1 drafts | [C] redefined in all five files as "agreed in team discussion; formal approval of this v0.1 draft is pending" |
| 4 | Language model in explanations: `AGENTS.md` said templated; segmentation task F1 allows a language model to rephrase | `AGENTS.md` rewritten: explanations are built by template from verified values; a language model may only rephrase them, never add values |
| 5 | ID clash: roadmap features F1–F10 and segmentation tasks F1–F4 | Roadmap features renamed FEAT-01 to FEAT-10 |
| 6 | Rule ownership: Luca approves rules in `checks/`, but C6, E8 and E9 are assigned to Sahil | Note added to `problem_segmentation.md` section E: E1–E7 are engineering rules approved by Luca; C6, E8 and E9 are data-integrity rules owned by Sahil with no engineering thresholds |
| 7 | Extracted values: `AGENTS.md` did not say that checks pass only on verified inputs | `AGENTS.md` rewritten: checks only pass on verified inputs; extracted, missing or unclear inputs produce `unclear` |
| 8 | Wording differences in role descriptions | Accepted, no change |
| 9 | Milestones: `AGENTS.md` left out the 29 Oct deliverable | `AGENTS.md` rewritten: all five IAAC milestones listed |
| 10 | Name: "Right Fit" in `AGENTS.md`, "RightFit" elsewhere | `AGENTS.md` rewritten: "RightFit" throughout |
| 11 | Open decisions list in `AGENTS.md` incomplete | `AGENTS.md` rewritten: points to the [O] items in the constitution instead of keeping its own list |

## 5. Referenced files and unclear items

| Finding | Resolution |
|---|---|
| `docs/concept-v2.pdf` referenced but missing | Reference removed from `AGENTS.md` |
| `docs/decisions.md` referenced but missing | `docs/decisions.md` created |
| `specs/` in `AGENTS.md` vs `spec/` in the repository | `AGENTS.md` rewritten to use `spec/constitution/` and `spec/features/` |
| `tech_stack.md` said v1 approval forms stay outside Git "if confidential" | `tech_stack.md` now states they are confidential and stay outside Git |
| 12 Nov demo path depends on E2 or E3, which need installation manuals (DS4) of unknown availability | Known risk, no change (already listed in `roadmap.md`) |
| `README.md` reported as missing | Agent error (see section 6) |

## 6. Agent error

The agent reported `README.md` as missing, although it exists in the repository root.
