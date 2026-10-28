# Data Map — RightFit

IAAC deliverable, 29 Oct 2026. MAF version on branch `maf-checker`; the hood version is on `main`. Open questions are marked [O].

Unlike the hood version, which started from data we still had to collect, the MAF version starts from data Luca already holds: a register of 80 forms and two complete packages. The weak spots are different. We have very few packages, and some of the rules were read on secondary sites.

## 1. Datasets

| ID | Dataset | Source | Owner | Format | Where it stands | Restrictions | Used for |
|---|---|---|---|---|---|---|---|
| DS1 | MAF packages P01 (pumps) and P02 (air handling unit) | Luca's last project | Luca | .xls form + 15 PDFs | Held | Originals in `data/raw/`, never in Git; only values and short quotes are committed | Everything the checks read |
| DS2 | Register of 80 MEP forms | Luca's last project | Luca | .xlsx | Held, anonymised | Outside Git; only counts and short anonymised examples in `docs/maf_register_findings.md` | Evidence for the problem; source of the checklist |
| DS3 | Rules, and the documents each family needs | EU, Romanian and Spanish texts | Luca (AI first pass) | CSV (`data/maf/rules.csv`, `family_documents.csv`) | In Git | Each rule keeps its source, quote, status and the date it was checked | D1–D3, E1, R |
| DS4 | Legal texts | EUR-Lex, Monitorul Oficial / legislatie.just.ro, BOE | Luca | Web pages, PDF | Partly read | Cite clause and edition | The basis of DS3 |
| DS5 | Reviewers' checklist | Built from the comments in DS2 | Luca | CSV (`data/maf/checklist.csv`) | In Git, 12 items | Never evaluated on DS2, which it came from | Check C |
| DS6 | Package inventory | DS1 | AI reader | CSV (`data/maf/packages.csv`) | In Git | File names only | Check D4 |
| DS7 | Extracted values | DS1, read by the AI | Luca verifies | JSON (`data/maf/extracted/`) | In Git, nothing verified yet | Roles only, quotes of 15 words at most, no names | All checks |
| DS8 | Reference answers | Luca, before seeing the tool | Luca | Text (`data/maf/reference/`) | Written for P01 and P02 | Never used for tuning | Evaluation |
| DS9 | Review times, by hand and with the tool | Luca | Luca | In DS8 for now | By hand: about 10 min (P01, figures only) and 3 h (P02) | | Evaluation |
| DS10 | Overrides and approved values | Exported by the app | Reviewer | CSV | Created when used | Stay local unless anonymised | O&M file, certification consultant |
| DS11 | More packages | Luca's practice | Luca | As DS1 | [O] which ones, and how we anonymise them | As DS1 | Evaluation on unseen packages |
| DS12 | Interviews with reviewers and contractors | Us | Sahil | Notes | [O] not planned in detail | Consent, anonymised | Problem evidence, who would pay |

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

The main risk isn't missing data anymore. It is that two packages are too few to say how well the tool works, and that every value is still unverified.

## 4. Next steps

1. Luca verifies the values in the app, so the comparison with DS8 runs on checked values.
2. Luca lists further packages he can share once anonymised (DS11).
3. We check the rules on the official texts and update their status in DS3.
4. [O] Sahil or Jeff propose the LEED, BREEAM or VERDE values for the checklist.
