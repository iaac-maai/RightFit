# RightFit data map

IAAC deliverable, 29 Oct 2026, brought up to date on 16 Nov 2026. MAF version, which the team agreed to on 5 Nov 2026; the hood version stays in the Git history. Open questions are marked [O].

Unlike the hood version, which started from data we still had to collect, the MAF version starts from data Luca already holds: a register of 80 forms and two complete packages. The weak spots are different. We have read very few packages, and almost nothing the AI read has been checked by a person yet.

## 1. Datasets

| ID | Dataset | Source | Owner | Format | Where it stands | Restrictions | Used for |
|---|---|---|---|---|---|---|---|
| DS1 | MAF packages P01 (pumps) and P02 (air handling unit) | Luca's last project | Luca | .xls form + 15 PDFs | Held | Originals in `data/raw/`, never in Git; only values and short quotes are committed | Everything the checks read |
| DS2 | Register of 80 MEP forms | Luca's last project | Luca | .xlsx | Held, anonymised | Outside Git; only counts and short anonymised examples in `docs/maf_register_findings.md` | Evidence for the problem; source of the checklist |
| DS3 | Rules, and the documents each family needs | EU, Romanian and Spanish texts | Luca (AI first pass) | CSV (`data/maf/rules.csv`, `family_documents.csv`) | In Git: 32 rules, of which the 28 legal ones were read on the official text | Each rule keeps its source, quote, status, the date it was checked and the dates it applies between | D1–D3, V3, E1, H1, R |
| DS4 | Legal texts | The EU Publications Office (EUR-Lex no longer answers scripts), legislatie.just.ro, the BOE open data service | Luca | Web pages, PDF | Read for every rule in DS3, last on 16 Nov | Cite clause and edition | The basis of DS3 |
| DS5 | Reviewers' checklist | Built from the comments in DS2 | Luca | CSV (`data/maf/checklist.csv`) | In Git, 11 items | Never evaluated on DS2, which it came from | Check C |
| DS6 | Package inventory | DS1 | AI reader | CSV (`data/maf/packages.csv`) | In Git | File names only | Check D4 |
| DS7 | Extracted values | DS1, read by the AI | Luca verifies | JSON (`data/maf/extracted/`) | In Git; 95 of 116 values and all 15 documents confirmed, 21 values not stated | Roles only, quotes of 15 words at most, no names | All checks |
| DS8 | Reference answers | Luca, before seeing the tool | Luca | Text (`data/maf/reference/`) | Written for P01 and P02 | Never used for tuning | Evaluation |
| DS9 | Review times, by hand and with the tool | Luca | Luca | In DS8 for now | By hand: about 10 min (P01, figures only) and 3 h (P02) | | Evaluation |
| DS10 | Overrides and approved values | Exported by the app | Reviewer | CSV | Created when used | Stay local unless anonymised | O&M file, certification consultant |
| DS11 | More packages | The same project as DS1 | Luca | As DS1 | Held since 6 Nov: 48 packages, 285 PDFs, 1,296 pages, 31 PDFs without text; none read yet. Three quarters of them trained the second page classifier, and 26 are set aside for the chatbot test. [O] Packages from other projects | As DS1 | Training and locked testing of our models; evaluation on unseen packages |
| DS13 | Manufacturer documents library | Official manufacturer sites, found by the AI | Luca confirms | JSON (`data/maf/library.json`) + copies in `data/raw/library/` | Started: 2 Grundfos declarations, 1 FläktGroup search without result | Links and short quotes only in Git; copies stay local | D1: a missing document the manufacturer publishes |
| DS12 | Interviews with reviewers and contractors | Us | Sahil | Notes | One practising consultant answered on 12 Nov and asked for two checks, V3 and H1. [O] The questionnaire for the others is drafted, not sent | Consent, anonymised | Problem evidence, who would pay |
| DS14 | The project's BOQ | The project of DS1 | Luca | Excel (.xlsx, .xls) | Held; in the project's boq folder, outside Git | It holds prices, which are never read; only the description, unit, quantity, producer and standards columns are | Check Q |
| DS15 | The consultant's own rules | Typed by the consultant on the Rules screen | The consultant | CSV (`data/maf/consultant_rules.csv`) | In Git, five example rules | A rule typed in words is turned into a row by an AI and saved only if the consultant agrees | Check P |
| DS16 | Test set for the chatbot comparison | Drawn at random from DS11 before any of it was read | Luca | CSV (`eval/chatbot_baseline/test_set.csv`) | In Git: 21 packages for accuracy, 5 for time | Package ids only; frozen | Evaluation |

The hood version listed "79 MEP approval forms" from the v1 research. We use DS2 instead, because it is the copy we can open.

## 2. What the two packages actually contain

The hood version planned an audit of installation manuals to see which values manufacturers publish. Reading P01 and P02 was the same exercise for MAF packages. Here is what we found in the documents, before anyone has verified it.

Documents: 15 PDFs. Three have no text layer and were read from the page image: the SL1/SLV declaration, the Hisense outdoor unit sheet and the AHU kit sheet. Each package has one declaration that names none of the submitted products. P02's "TÜV" attachment certifies the selection software, not the unit.

Pumps (4 in P01):

| Value | Found | Note |
|---|---|---|
| Model, product number, duty point (flow and head) | 4 of 4 | |
| Motor power, voltage, liquid temperature range | 4 of 4 | |
| Starting method | 2 of 4 | Not on the two drainage pump sheets |
| Maximum working pressure | 2 of 4 | The drainage pump sheets give a maximum depth instead |
| Controller or panel included | 1 of 4 | The stormwater sheet shows a panel wiring diagram, without saying it is supplied |
| BMS communication included | 0 of 4 | The booster set lists protocols as "available" |
| Motor efficiency class | 1 of 4 | |

Air handling unit (P02): every value the spec asks for is on the 30-page data sheet, including the ecodesign figures (heat recovery 76 % against 73 %, SFPint 868 against a limit of 890). The sound power is printed per fan and per opening, and we haven't mapped it to supply and extract yet.

Outdoor units (P02): capacities, refrigerant, charge, SEER and SCOP are on a range table; the GWP isn't given. The DX kit sheet doesn't name the outdoor unit it works with; only the selection report pairs them.

One thing the documents say that no check covers yet: the AHU's DX coil is selected for R32, while the outdoor units and both selection reports use R410A.

## 3. Summary

We hold DS1 and DS2, and we have created DS3, DS5, DS6, DS7 and DS8. The times with the tool (DS9) need Luca to check a draft, and an evaluation needs DS11.

The main risk isn't missing data anymore. It is that two packages are too few to say how well the tool works, and that the 25 packages of the second batch are not confirmed yet.

## 4. Next steps

1. Luca verifies the values in the app, so the comparison with DS8 runs on checked values.
2. We read the first packages of DS11, and a person checks them before any check uses them.
3. Done on 16 Nov: every legal rule read on the official text. Next comes a scheduled check that tells us when a source changes.
4. [O] Sahil or Jeff propose the LEED, BREEAM or VERDE values for the checklist.
