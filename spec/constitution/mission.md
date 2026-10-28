# Mission — RightFit

Version 0.1 (draft) · 28 Oct 2026 · Full version due 12 Nov 2026

Tags: **[C]** agreed in team discussion; formal approval of this v0.1 draft is pending · **[P]** proposed, awaiting approval · **[O]** open question

## 1. Problem

**[C]** Interior architects choose visible products (kitchen hoods, lights, grilles, radiators, sanitaryware) mainly by appearance during design development (roughly LOD 200–300). The MEP engineer reviews the choice later and may find it needs a larger duct, a lower ceiling, a new route, or does not meet requirements. The design is then revised, re-specified and re-submitted, when changes are more expensive.

**Who is affected [C]**
- Interior architect: design compromised late (bulkheads, dropped ceilings, grilles in visible places).
- MEP engineer: reworks layouts to fit choices made without them.
- Client: pays for rework and waits.

**Evidence held [C]**
- From v1 research on one residential tower in Bucharest: 16 of 79 MEP approval forms were sent back.
- A recurring reviewer comment: "visible items need the architect's approval".

**Evidence still to collect [O]**
- Number and stage of design changes caused by MEP conflicts in our past projects.
- Interviews with 3–5 interior designers on how long finding a suitable product takes today.
- Luca's ranked list of the most frequent interior/MEP conflicts in practice.

## 2. Users and stakeholders

| Role | Uses RightFit to | Responsible for | Status |
|---|---|---|---|
| Interior architect | Find products that fit the look and the room | The design choice | [C] primary user |
| MEP engineer | See choices early, review flags | Engineering sign-off | [C] |
| Client | Get fewer late changes | Approving the final selection | [C] |
| Manufacturers | Be found by look, not only keyword | Accuracy of their data | [C] |

**Paying customer [O]:** a hypothesis to test through interviews. No market or revenue claims are made.

## 3. Vision

**[C]** From checking what was submitted to helping choose what gets specified.

## 4. Scope

**In scope [C]**
- One product family: kitchen extraction hoods.
- AEC Phase 1, Design & Pre-Construction, at the product-selection moment.
- Text and reference-image search, deterministic MEP checks, explained trade-offs.

**Out of scope [C]**
- Generating designs.
- Training large models.
- Certifying products or claiming regulatory compliance.
- Other product families (lighting, grilles): future work only.

**Undecided [O]**
- Whether hob-integrated downdraft extractors are included.
- Whether the v1 approval-form check returns as a later phase.
- A predictive feature for installation or approval concerns: exploratory only, not committed.

**Jurisdiction [O]:** Spain is the provisional testing context because the prototype is developed in Barcelona. Luca must validate which engineering standards apply. Until then, no check is presented as verified regulatory compliance.

## 5. Principles

These apply to every specification, line of code, test and presentation.

1. **Evidence first.** No technical value, catalogue datum, test result, AI performance figure or regulatory statement is ever invented or estimated from "typical" values.
2. **Every value is sourced.** Each value records its source (URL or file and page) and a status: `verified` (checked by a team member), `extracted` (read automatically, unchecked) or `unclear` (missing or ambiguous).
3. **Unclear stays unclear.** Missing evidence is shown to the user as `unclear`. Checks only `pass` on `verified` inputs.
4. **AI and engineering are separate.** AI handles perception and interpretation: matching looks, reading inconsistent data sheets, learning preferences. Engineering checks are deterministic, explainable and auditable. No AI model produces or overrides an engineering result.
5. **Predictions are not warnings.** Any predictive output is labelled as a prediction and kept apart from engineering checks.
6. **Humans decide.** The designer chooses, the MEP engineer signs off, the client approves. RightFit never certifies. Every result states what was and was not checked.
7. **Honest validation.** Metrics are fixed before results are seen. Test data is never used for tuning or preference learning. All results are reported, including negative ones. No claim of accuracy without stored results.
8. **Privacy and rights.** No confidential client documents, names, prices or personal data in the repository. Manufacturer images and PDFs stay outside Git.
9. **Simplicity.** Pretrained models, few dependencies, small tested features first.
10. **Shared decisions.** Decisions are recorded in the repository. Principles change only with agreement from all three team members.

## 6. Success metrics

**[P]** From Concept v2. Targets are set only after baselines are measured.

| Metric | How it is measured |
|---|---|
| Look relevance | Of the top 5 results, how many Jeff (and, if possible, outside designers) rate as a good match |
| MEP correctness | Of products passed by the checks, how many Luca confirms work in the room |
| Time to a valid shortlist | Timed, RightFit vs. baseline, same briefs |
| Ranking improvement | Relevance before vs. after learning from picks (if implemented) |

**Baselines [C]:** keyword search on the same catalogue, and a designer's usual manual process.

**Stop criterion [C]:** if RightFit does not beat the keyword baseline on look relevance or MEP correctness on the test set, we report it and reconsider the approach.

## 7. Known limitations

- **[C]** Image search matches appearance, not build quality or durability.
- **[C]** A value missing from manufacturer documents stays missing.
- **[C]** Brands with better catalogues may be found more easily.
- **[C]** Checks cover only kitchen hoods; anything else is flagged for the engineer.
- **[P]** Manufacturer airflow figures may not reflect performance in a real duct installation. Checks only test what the documents support.

## 8. Change log

| Date | Change | Agreed by |
|---|---|---|
| 28 Oct 2026 | v0.1 draft created | pending: Sahil, Jeff, Luca |