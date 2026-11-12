# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Stack

Plain HTML, CSS and JavaScript, served by a small Python script that uses only the standard library. The checks stay in Python (`checks/maf/`) and the page asks them for results. Chosen by Luca on 29 Oct 2026. It runs on Luca's laptop for the PoC. Nothing is hosted.

## Users

The primary user is the MEP consultant who reviews and signs a material approval form (MAF) that the contractor submitted. Luca confirmed this user ("most often the consultant"). They sit at a desk with the form (an old .xls file) and its PDF attachments, and must send back one status with comments:

- A, Approved;
- B, Approved as noted;
- C, Revise and resubmit.

Luca is an MEP engineer, not a programmer. He confirms what the AI read and judges the results. The IAAC mentors evaluate the PoC.

## Product Purpose

RightFit checks an MAF for MEP equipment before the reviewer signs it. It does three things:

- reads the attachments;
- checks them against EU and national rules and against a checklist built from past reviewers' comments;
- drafts the answer, with a page reference for every finding.

Success means the reviewer finds the real gaps without reading every PDF line by line, and sends a correct answer. Examples of real gaps:

- a declaration of conformity that is missing or covers the wrong products;
- a data sheet for a whole range with nothing marked;
- a pump panel without its BMS module.

The evidence for the problem comes from Luca's last project. Of 80 MEP approval forms, 22 came back with notes or for resubmission, and 8 of those 22 were plain gaps in the package. A form usually came back after about 12 days.

## Positioning

- Every finding points to a file, a page and a short quote.
- Nothing counts as passed until a person confirms the value behind it. Until then it is a question, shown with the result it would have.
- The checks are deterministic rules kept apart from the AI, and AI output is always labelled as AI.
- When a document is missing, RightFit points to the copy the manufacturer publishes.

## Operating Context

- **The package.** A package is the MAF form plus its attachments: data sheets, declarations of conformity, certificates and selection reports, in Romanian and English. The originals stay on the laptop in `data/raw/`. What the AI read is in `data/maf/extracted/`.
- **The review.** The reviewer reads the draft answer and its reasons, then works in this order:
  1. goes through the problems found;
  2. decides on each AI suggestion;
  3. confirms what the AI read;
  4. copies or downloads the answer to send.
- **Exports:**
  - the answer text;
  - the confirmed values, for the certification consultant and the O&M file;
  - the findings marked "not a problem", with their reasons.
- **Location.** The checks run for Romania (RO) on the real packages. Spain (ES) is the provisional context of the constitution. EU product rules apply to both.

## Capabilities and Constraints

- **Packages.** Two real packages:
  - P01, Grundfos pumps;
  - P02, a FläktGroup air handling unit with Hisense outdoor units and a DX kit, at revision 4.
- **Checks:**
  - D1–D4, the documents;
  - V1–V3, the duty point, the pressure rating and the liquid temperature;
  - E1, ecodesign;
  - H1, the approval for contact with drinking water;
  - C, the reviewers' checklist;
  - P, the consultant's own rules, typed in words on the Rules screen;
  - Q, what the product's line in the project's BOQ asks for;
  - R, the delivery reminder.

  They produce pass, flag, unclear or info, and a draft status A, B or C with its reasons.
- **AI.** A second AI reviewer proposes findings with page evidence, and the reviewer accepts or rejects each one. The AI also matches documents to products.
- **Reviewer actions:**
  - mark a finding "not a problem", with a reason;
  - decide on AI suggestions;
  - confirm readings, which records who checked them.
- **MCP.** Four read-only tools let an agent list the packages, review one, list the rules and classify a package's pages. Confirming a reading stays on the page.
- **Constraints:**
  - the interface is in English;
  - no data is invented;
  - every value carries a value, unit, source, page, a quote of at most 15 words, and a status;
  - checks pass only on confirmed values;
  - the tool never certifies;
  - no client, project, company or personal names and no prices go into Git. Manufacturer names and model codes are fine.
- **Undecided or later:**
  - adding a package of any family. Today the page reads an added pump package on the spot; the other families are read offline;
  - reading the 49 packages of the second batch, which the Packages screen lists as not read yet.

## Brand Commitments

The product is called RightFit. It has no logo or visual identity yet. The voice is plain, short English that a non-programmer engineer can read. The status labels use the trade's own words: Approved, Approved as noted, Revise and resubmit.

## Evidence on Hand

| What | Where |
|---|---|
| Readings of the two packages | `data/maf/extracted/P01.json`, `P02.json` |
| Luca's reference answers | `data/maf/reference/` |
| Manufacturer documents found online | `data/maf/library.json` |
| Counts from the register of 80 MAFs | `docs/maf_register_findings.md` |
| Results of the first own model, the page classifier | `eval/page_classifier/results_2026-10-29.md` |

Absent, and not to be invented:

- measured time savings;
- user quotes;
- customers;
- verified values, beyond the single one Luca confirmed in P02.

## Product Principles

1. The reviewer decides. The tool drafts and never certifies.
2. Show the evidence: every finding comes with its file, page and quote.
3. What the AI read stays a question until a person confirms it.
4. Rules and AI stay apart, and AI output is labelled.
5. Nothing confidential leaves the laptop or enters Git.
