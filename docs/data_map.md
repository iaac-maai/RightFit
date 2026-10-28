# Data Map — RightFit

Version 0.1 (draft) · 28 Oct 2026 · IAAC deliverable, 29 Oct 2026

Tags: **[C]** agreed in team discussion; formal approval of this v0.1 draft is pending · **[P]** proposed, awaiting approval · **[O]** open question

Availability:
- **Held**: the team has it now
- **Public, not collected**: exists publicly, not yet gathered
- **Planned**: will be created by the team during the project
- **Unknown**: existence or completeness not yet checked

No dataset below has been collected or cleaned unless marked **Held**.

## 1. Datasets

| ID | Dataset | Source | Owner | Format | Availability | Access and restrictions | Known gaps / missing fields | Intended use |
|---|---|---|---|---|---|---|---|---|
| DS1 | Hood product images | Manufacturer websites and catalogues | Jeff | JPG / PNG | Public, not collected | Copyrighted; stored locally in `data/raw/`, never in Git or published | Inconsistent viewpoints, backgrounds and lighting across brands | Image search (D1), attribute tagging (C4) |
| DS2 | Product names and descriptions | Manufacturer websites and catalogues | Jeff | Web text | Public, not collected | Keep source URLs | Inconsistent terms for finish, style and mounting | Text search, keyword baseline (D4) |
| DS3 | Technical data sheets | Manufacturer websites | Luca | PDF | Public, not collected | Stored locally; extracted values + page references in Git | Format differs per brand; some MEP values may be absent | Technical values for checks (E1–E8) |
| DS4 | Installation manuals | Manufacturer websites | Luca | PDF | Unknown: availability per brand to be audited | Stored locally | May or may not state duct diameter, required void, mounting heights, duct length limits | Installation values for checks (E2–E5) |
| DS5 | EPREL energy-label records | EU EPREL public product pages | Luca | Web page | Public, not collected | Free to view per model; bulk API access requires a formal application | No dimensions, duct diameter or mounting data | Cross-check airflow, noise, efficiency (C5, E8) |
| DS6 | Engineering standards | Official publications | Luca (Sahil supports) | PDF | Public, not collected | Cite clause and edition | [O] which standards apply; Spain provisional | Basis for check rules (E6, E7) |
| DS7 | v1 MEP approval forms (79) | Team's v1 research, Bucharest residential tower | Luca | [O] to confirm | Held | Confidential; stays outside Git; only anonymised counts and patterns may be committed | Covers one project only | Problem evidence; examples of interior/MEP conflicts |
| DS8 | Past project records (interiors and MEP) | Team members' past projects | All | [O] mixed (drawings, PDFs, notes) | Held, extent to be confirmed | Confidential; anonymise before use; no client names or prices | Which projects and how much data, not yet listed | Real rooms for design briefs; conflict counts |
| DS9 | Room descriptions | Created by the team | Sahil, Luca | Structured file (format [O]) | Planned | Anonymised | Schema not yet defined | Inputs B1–B4 for checks |
| DS10 | Design briefs (20–30) | Created from DS8 and team scenarios | Jeff, Luca | Structured file | Planned | Split into `eval/dev/` and locked `eval/test/` before any tuning | Not yet written | Evaluation against baselines (G5) |
| DS11 | Look-relevance judgements | Jeff; outside designers if available | Jeff | Spreadsheet / CSV | Planned | Blind: judges do not see which system produced a result | Outside judges not yet recruited | Look relevance metric |
| DS12 | MEP-correctness judgements | Luca | Luca | Spreadsheet / CSV | Planned | Recorded with reason per product | Not yet started | MEP correctness metric |
| DS13 | Designer picks and rejections | Logged by the tool | Sahil | Log file | Planned | No personal data; test-brief sessions excluded from learning | Not yet generated | Re-ranking (G2), optional learning-to-rank (G3) |
| DS14 | Designer interviews (3–5) | Interviews by the team | Sahil | Notes | Planned | Consent required; anonymised | Interviewees not yet identified | Problem evidence; baseline time estimates |
| DS15 | Timed trials | Run by the team | Sahil | Spreadsheet / CSV | Planned | Anonymised | Not yet run | Time-to-shortlist metric |

## 2. Hood catalogue fields

Every value is stored with `value`, `unit`, `source`, `page`, `status` and `checked_by`, as set out in `spec/constitution/tech_stack.md`.

"Expected source" is where we *expect* to find each field. The manual audit (P1 in the roadmap) will confirm or correct this. Only the EPREL fields are already confirmed from public EPREL pages.

| Field | Needed for | Expected source | Confirmed? |
|---|---|---|---|
| Brand, model, product URL | Identification | DS2 | Expected |
| Product type / mounting (wall, island, integrated, ceiling, downdraft) | Search, E1 | DS2, DS3 | Expected |
| Width, height, depth | Search filters, E5 | DS3 | Expected |
| Colour and finish | Search, C4 | DS1, DS2 | Expected |
| Operating modes (ducted, recirculating) | E6 | DS3, DS4 | Expected |
| Duct outlet diameter | E2 | DS3, DS4 | To be audited |
| Required ceiling void (ceiling-flush hoods) | E3 | DS4 | To be audited |
| Maximum duct length or bends | E4 | DS4 | To be audited; may often be missing |
| Minimum height above hob | Installation information | DS4 | To be audited |
| Motor position (internal, remote) | Information | DS3, DS4 | To be audited |
| Airflow at min, max and boost speed | E7, E8 | DS5 (EPREL), DS3 | EPREL publishes these fields |
| A-weighted sound power at min, max and boost | E8 | DS5 (EPREL), DS3 | EPREL publishes these fields |
| Energy and efficiency classes | E8 | DS5 (EPREL) | EPREL publishes these fields |
| EPREL registration number, GTIN | Linking to EPREL | DS5 | Where available |

**Note on airflow [P]:** declared airflow figures describe standard test conditions. Whether they apply to a specific duct installation is for Luca to judge. Checks will not treat them as installed performance.

## 3. Summary

**Held now:** DS7 (v1 approval forms), DS8 (past project records, extent to be confirmed).

**Public, not yet collected:** DS1–DS3, DS5, DS6.

**Unknown, audit first:** DS4 (installation manuals). This is the main data risk, because most engineering checks depend on it.

**Planned, created by the team:** DS9–DS15.

## 4. Next data actions [P]

1. Luca audits about 10 installation manuals and reports which fields from section 2 are published.
2. Jeff selects 5–10 manufacturers and starts the seed catalogue (about 50 hoods).
3. Luca confirms which engineering standards apply to the provisional Spanish context.
4. The team lists which past projects (DS8) can be used and how they will be anonymised.

## 5. Change log

| Date | Change | Agreed by |
|---|---|---|
| 28 Oct 2026 | v0.1 draft created | pending: Sahil, Jeff, Luca |