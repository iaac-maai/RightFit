# Feature spec: MAF checker for MEP equipment (proposal)

Status: proposal by Luca, 28 Oct 2026, on branch maf-checker. Pending Sahil and Jeff. Nothing here changes main or the constitution until the team agrees (see docs/decisions.md).

## 1. What it does
RightFit checks a material approval form (MAF; in Romania "fișă pentru transmitere și aprobare materiale") for MEP equipment before the reviewer signs it. It reads every attached document, checks it against the law, the project's requirements and a checklist written from reviewers' past comments, and drafts a review that points to the page behind each finding. AI reads, rules decide, a person signs.

- user: the reviewer who signs the MAF, most often the consultant (also the site supervisor or the designer); the contractor can run the same check before sending;
- first families: pumps and air handling units, because we hold two complete real packages for them;
- not in this feature: visual search, product suggestions, doors, the space check.

## 2. How it fits the constitution
Unchanged: the data rule (value, unit, source, page, status, checked_by), deterministic checks in checks/ with no AI, results as pass, flag or unclear with sources, humans decide, nothing confidential in Git, decisions in docs/decisions.md, Python, pytest, Streamlit.

Changed if the team agrees: the first use case becomes the MAF review of MEP equipment instead of hood selection; the user becomes the reviewer instead of the interior designer; FEAT-02 and FEAT-03 (visual and keyword search) are not needed for it.

## 3. Inputs

### The MAF form
Romanian standard form, one per package, old .xls (read with xlrd in ingest/). Stored under "form" in the extracted JSON, with roles only, never company or person names.

| Form field | JSON field | P01 example |
|---|---|---|
| Formular Nr, Revizia Nr, Data | form_no, revision, date | IS 015, 0, 2026-03-16 |
| Disciplina, Grupa lucrari | discipline, works_group | INSTALATII SANITARE, ALIMENTARE CU APA |
| Denumirea, Producator / Brand, Model, Origine | items[]: name, family, brand, model, origin | Grup pompare apa menajera, pump, Grundfos, Hydro Multi-E 2 CME 15-2 U2 A-A-A-A-A |
| Pozitie in BOQ | boq_ref | IS06 |
| A se folosi la | items[].used_for, items[].duty (flow, head, units, duty and standby) | booster set: 1 duty + 1 standby, Q=15 m³/h, H=50 mCA |
| Detalii livrare | delivery_weeks | 3 |
| Atasamente (tip, nr pagini) | attachments_listed[]: label, pages | Declaratie de conformitate SLV1, 1 |
| Mostra transmisa | sample_sent | No |
| STATUS | status_scale | Aprobat; Aprobat conform notatii; Revizie si retransmitere; Neaprobat; Se solicita mostra |
| Signature boxes | signers (roles only) | subcontractor, general contractor, specialist designer, general designer, site supervisor, project manager, LEED consultant, client |

### Packages
| id | form | items | attachments |
|---|---|---|---|
| P01 | IS 015 rev 0 | water booster set Hydro Multi-E 2 CME 15-2 (1 duty + 1 standby, 15 m³/h at 50 mCA); stormwater pumps DPK.15.80.30.5.0D (P1/P2, 38 m³/h at 15 mCA); drainage pumps Unilift AP12.50.11.3 (3 l/s at 10 mCA) and AP12.40.06.3 (1 l/s at 10 mCA) | 4 data sheets, 2 declarations |
| P02 | IV 004 rev 4 | AHUs FläktGroup CAIRplus 9000 m³/h and 7000 m³/h with DX coil; 2 outdoor units Hisense AVW-54HKFHH2; AHU kit HZX-6BEJ | AHU data sheet, outdoor unit data sheet, 2 Hisense declarations, AHU kit sheet, TÜV certificate, Eurovent certificate, 2 DX simulation reports (+6 °C, -15 °C) |

Originals in data/raw/P01 and data/raw/P02: git-ignored, never committed. Families: pump, ahu, outdoor_unit, dx_kit.

### Project settings
location (RO or ES), review date, delivery date (form date + delivery weeks unless given), requirements from the specification or BOQ when available.

## 4. Reading (ingest/)
Claude Code reads each attachment and writes data/maf/extracted/<package>.json.

Per document: file, pages, text_layer, languages, method (text or page image); doc_type (data_sheet, eu_declaration_of_conformity, declaration_of_performance, product_certificate, other_certificate, selection_report, manual, other); covers (the ranges or models it names; for declarations, the exact list declared); issuer, issue_date, valid_until; for declarations, the directives, regulations and standards cited; listed_as (the form's attachment label it corresponds to, or null).

Per item: the values in section 5, each as value, unit, source (file), page, quote (at most 15 words, never a name from data/raw/NAMES.txt), status and checked_by. Values read by Claude Code start as extracted. Luca verifies them in the app; verified values get status verified and checked_by Luca. A value not found is empty, with status unclear and a note on where it was looked for. Never guess. File names are never trusted for what a document is.

## 5. Values per family
- pump: model, product number, flow and head at the duty point, motor power P2, voltage, starting method, maximum working pressure (PN), liquid temperature range, controller or panel included, BMS communication (protocol; module included or optional), motor efficiency class if given;
- ahu: model, airflow per unit, external static pressure, heat recovery type, heat recovery efficiency (as printed, with its standard), SFPint and SFPint_limit, filter classes (ISO 16890) for supply and extract, filter warning, energy class (Eurovent or RLT) if given, dimensions and weight, sound power (info);
- outdoor_unit: model, cooling and heating capacity, refrigerant, refrigerant charge, GWP if given, SEER and SCOP if given;
- dx_kit: model, compatible outdoor units, control and communication.

## 6. Checks (checks/maf/, plain Python, one test each in tests/)
Results: pass, flag, unclear, info. A check passes only on verified values; extracted or missing values give unclear. A check with no requirement to compare against gives info "no requirement given". Rules come from data/maf/rules.csv, resolved by location as in docs/jurisdictions.md.

| id | Check | Logic | Rules |
|---|---|---|---|
| D1 | Required documents | for each item, every document in data/maf/family_documents.csv for its family and the location chain is present (by doc_type and covers) | data/maf/family_documents.csv |
| D2 | Declarations match the items | each declaration covers at least one submitted item; flag a declaration that covers none, and name the items left without one | EU-MACH-DOC, EU-LVD-DOC |
| D3 | Documents in date | valid_until on or after the review date, else flag; on or after the delivery date, else flag "renew before delivery"; no date: info | CL-02 |
| D4 | Documents are what the form says | each attachment's doc_type agrees with the label it is listed as; every listed attachment exists | practice |
| V1 | Duty point | data sheet flow and head at the duty point meet the form's duty, with no tolerance (the designer's margins are already in the duty) | ENG-DUTY-TOL |
| V2 | Pressure rating | PN at least the required pressure; no requirement: info | CL-05 |
| E1 | Ecodesign, ventilation units | heat recovery efficiency against EU-ECO-VU-HRS (or -RAC); SFPint at most SFPint_limit; filter warning present | EU-ECO-VU-* |
| C | Checklist | every item of data/maf/checklist.csv for the family, with its source rows as the reason | data/maf/checklist.csv |
| R | Location reminders | the location's delivery documents (RO: declaration, quality certificate, guarantee; ES: CTE 7.2 and RITE 20) as info | RO-PRACTICE-DELIVERY, ES-CTE-7-2, ES-RITE-20 |

## 7. Draft status (written rules, not a model; Luca confirms or changes them)
- Revizie și retransmitere (C): an item has no data sheet, or its data sheet does not show the submitted model, or a checklist item marked blocking is missing;
- Aprobat conform notații (B): no C condition, but at least one flag or unclear; one note per flag or unclear;
- Aprobat (A): everything pass or info;
- Neaprobat and Se solicită mostră: only the reviewer chooses them;
- the app always shows "draft, the reviewer decides" and the reason for the status.

In the earlier register, missing declarations led to a reminder for the delivery, not to a C (three such MAFs were approved). That is why a missing declaration is a flag (B), not a C.

## 8. Draft comments (explain/)
One sentence per flag or unclear, from a template per check, in English, in the tone of the reviewers' past comments. A language model may only rephrase them, never add values. Example for D2: "The declaration of conformity attached for {covers} matches no product in the MAF; please attach the declarations for {items}."

## 9. Interface (app/, Streamlit)
- package picker (P01, P02), location switch (RO, ES), review date, delivery date;
- header: form fields with roles only; draft status with its reasons;
- documents table: file, type found, listed as, covers, valid until, pages, method;
- values per item with source, page, quote and status; a button to verify each value (checked_by Luca);
- checks grouped D, V, E, C, R, each with result, reason and rule id; override with a note;
- draft comments with a copy button;
- exports: overrides.csv, and approved_values.csv (item, value, unit, source, page) for the certification consultant and the O&M file.

## 10. Tests and evaluation
- pytest unit tests for every check, with hand written cases approved by Luca;
- a reference answer per package, written by Luca before he sees the tool's output, kept in data/maf/reference/ and never used for tuning;
- comparison: found by both, found only by the tool (real or not), missed by the tool;
- Luca's time to review each package by hand, against his time to check the tool's draft.

## 11. Data and privacy
- data/raw/ holds the originals and is git-ignored;
- the anonymised register of the earlier project stays outside Git, as docs/data_map.md says for the approval forms; docs/maf_register_findings.md keeps only counts and short anonymised examples, and the row ids (R01 to R80) refer to Luca's local copy;
- no client, project, company or personal names anywhere in Git; manufacturer names and model codes are fine;
- no prices.

## 12. Open questions
- the draft status rules (Luca);
- the duty point tolerance: none (Luca, 28 Oct 2026, ENG-DUTY-TOL);
- which roles sit behind the four reviewer columns of the register (Luca);
- the Romanian law and the RITE article checked against the official journals;
- which LEED, BREEAM or VERDE values join each family's checklist (Sahil or Jeff);
- the IAAC deliverables of 29 Oct and the midterm still describe hoods: the team decides whether they change.
