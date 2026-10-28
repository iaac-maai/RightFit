# Problem Segmentation Tree — RightFit

Version 0.1 (draft) · 28 Oct 2026 · IAAC deliverable, 29 Oct 2026

Tags: **[C]** agreed in team discussion; formal approval of this v0.1 draft is pending · **[P]** proposed, awaiting approval · **[O]** open question

Task types: **Human** (a person decides or provides input) · **AI** (perception or interpretation by a pretrained model) · **Rule** (deterministic engineering check, no AI) · **Data** (collection, storage, software plumbing)

## 1. Tree

```text
L0  Visible products are chosen by look; their MEP consequences
    are discovered late, when changes are expensive.
 |
 |-- L1  Interior product selection in design development (LOD 200-300)
 |    |
 |    `-- L2  Prototype scope [C]: choosing a kitchen extraction hood
 |         |
 |         |-- A. Capture design intent
 |         |-- B. Describe the room and MEP context
 |         |-- C. Build the product catalogue
 |         |-- D. Find candidate products
 |         |-- E. Check MEP fit
 |         |-- F. Explain and decide
 |         `-- G. Learn and evaluate
 |
 `-- L1  Other product families (lights, grilles, radiators,
         sanitaryware) -- future work, out of prototype scope [C]
```

## 2. Atomic tasks

### A. Capture design intent

| ID | Atomic task | Type | Owner | Notes |
|---|---|---|---|---|
| A1 | Write a text description of the desired product | Human | Designer | e.g. "slim, hidden, matte black" |
| A2 | Provide a reference image | Human | Designer | Optional |
| A3 | Identify visual attributes from words or image (colour, finish, form, how visible it is) | AI | Search module | Designer can correct [P] |
| A4 | State non-visual client rules (e.g. "made in Europe") | Human | Designer | Confirmed by a person, as in v1 |

### B. Describe the room and MEP context

| ID | Atomic task | Type | Owner | Notes |
|---|---|---|---|---|
| B1 | Ceiling height and available ceiling void | Human | Designer | Room input schema to be defined [P] |
| B2 | Kitchen layout (wall, island, open-plan or enclosed) | Human | Designer | |
| B3 | Hob type and width | Human | Designer | |
| B4 | Duct exit option (façade, shaft, none) and distance | Human | Designer / Luca | |
| B5 | Identify which engineering standards apply | Human | Luca | [O] Spain provisional, not yet validated |

### C. Build the product catalogue

| ID | Atomic task | Type | Owner | Notes |
|---|---|---|---|---|
| C1 | Collect product images and catalogue descriptions | Data | Jeff | Images stay outside Git |
| C2 | Collect data sheets and installation manuals | Data | Luca | Availability of MEP values to be audited [P] |
| C3 | Extract technical values with page citations | AI + Human | Sahil / Luca | Every value checked before `verified` |
| C4 | Tag visual attributes for each product | AI + Human | Jeff | Jeff confirms tags |
| C5 | Cross-check values against EPREL where available | Data | Luca | [P] |
| C6 | Mark missing values as `unclear` | Rule | Sahil | Never guessed |

### D. Find candidate products

| ID | Atomic task | Type | Owner | Notes |
|---|---|---|---|---|
| D1 | Convert product images and texts into embeddings | AI | Sahil | Pretrained model, no training |
| D2 | Convert the designer's query into an embedding | AI | Sahil | |
| D3 | Rank products by similarity | AI | Sahil | Scores labelled as AI output |
| D4 | Keyword search on the same catalogue | Rule | Sahil | Baseline for comparison |

### E. Check MEP fit

All rules are specified and approved by Luca before implementation. No thresholds are set until he provides them with sources.

**Note:** E1–E7 are engineering rules approved by Luca. C6, E8 and E9 are data-integrity rules owned by Sahil and contain no engineering thresholds.

| ID | Atomic task | Type | Owner | Notes |
|---|---|---|---|---|
| E1 | Mounting type compatible with the kitchen layout | Rule | Luca | |
| E2 | Duct diameter and resulting bulkhead depth | Rule | Luca | |
| E3 | Required ceiling void vs. available void | Rule | Luca | Mainly ceiling-flush hoods |
| E4 | Duct route length vs. manufacturer's stated maximum | Rule | Luca | Only if manuals publish it |
| E5 | Hood width vs. hob width | Rule | Luca | Basis to be specified by Luca |
| E6 | Whether recirculation is acceptable in this room | Rule | Luca | [O] depends on applicable standards |
| E7 | Required airflow for the room | Rule | Luca | [O] source of the rule to be defined |
| E8 | Show noise and efficiency values as information, not as pass/fail | Data | Sahil | From data sheets or EPREL |
| E9 | Return `unclear` when any input is not `verified` | Rule | Sahil | Principle 3 of the mission |

### F. Explain and decide

| ID | Atomic task | Type | Owner | Notes |
|---|---|---|---|---|
| F1 | Explain each candidate's trade-offs from verified values | Rule | Sahil | Template; a language model may only rephrase [P] |
| F2 | State what was checked and what was not | Rule | Sahil | |
| F3 | Select or reject candidates | Human | Designer | |
| F4 | Engineering sign-off | Human | MEP engineer | The tool never certifies |

### G. Learn and evaluate

| ID | Atomic task | Type | Owner | Notes |
|---|---|---|---|---|
| G1 | Record picks and rejections | Data | Sahil | |
| G2 | Re-rank within a session from picks | AI | Sahil | [P] |
| G3 | Learning-to-rank across sessions | AI | Sahil | [O] stretch; needs non-test data |
| G4 | Predict installation or approval concerns | AI | Team | [O] exploratory; never shown as a check |
| G5 | Compare against keyword and manual baselines | Data + Human | All | Locked test set, blind judging |

## 3. Where AI is and is not used

- **AI:** A3, C3 (with human check), C4 (with human check), D1–D3, G2–G4.
- **Rules:** C6, D4, E1–E7, E9, F1–F2. No AI model may produce or override these results.
- **Humans:** intent, room input, standards, design choice, engineering sign-off.

## 4. Smallest demonstrable path [P]

For the 12 Nov milestone: **A1/A2 → D1–D3 (with D4 as baseline) → one rule from E2 or E3**, on a seed catalogue (C1–C2 for about 50 hoods), with automated tests.

## 5. Change log

| Date | Change | Agreed by |
|---|---|---|
| 28 Oct 2026 | v0.1 draft created | pending: Sahil, Jeff, Luca |