# Feature spec: MAF checker for MEP equipment

Status: proposed by Luca on 28 Oct 2026, agreed by the team on 5 Nov 2026 (see docs/decisions.md).

## 1. What it does
RightFit checks a material approval form (MAF; in Romania "fișă pentru transmitere și aprobare materiale") for MEP equipment before the reviewer signs it. It reads every attached document, checks it against the law, the project's requirements and a checklist written from reviewers' past comments, and drafts a review that points to the page behind each finding. AI reads, rules decide, a person signs.

- user: the reviewer who signs the MAF, most often the consultant (also the site supervisor or the designer); the contractor can run the same check before sending;
- first families: pumps and air handling units, because we hold two complete real packages for them;
- not in this feature: visual search, product suggestions, doors, the space check.

## 2. How it fits the constitution
Unchanged: the data rule (value, unit, source, page, status, checked_by), deterministic checks in checks/ with no AI, results as pass, flag or unclear with sources, humans decide, nothing confidential in Git, decisions in docs/decisions.md, Python, pytest.

Changed by the team's decision: the first use case becomes the MAF review of MEP equipment instead of hood selection; the user becomes the reviewer instead of the interior designer; FEAT-02 and FEAT-03 (visual and keyword search) are not needed for it.

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

Originals in data/raw/P01 and data/raw/P02: git-ignored, never committed. Families: pump, ahu, outdoor_unit, dx_kit. From the second batch, with document rules only so far (12 Nov 2026): fire_damper, radiator, elastomeric_insulation, fire_detection_panel, visual_alarm_device, voice_alarm_control, voice_alarm_loudspeaker, fire_alarm_power_supply, cable.

### Project settings
location (RO or ES), review date, delivery date (form date + delivery weeks unless given), requirements from the specification or BOQ when available: the required pressure (bar) and, per pump application, the water temperature range the pump must take (°C).

## 4. Reading (ingest/)
An AI reader reads each attachment and writes data/maf/extracted/<package>.json.

Per document: file, pages, text_layer, languages, method (text or page image); doc_type (data_sheet, eu_declaration_of_conformity, declaration_of_performance, product_certificate, other_certificate, selection_report, drinking_water_approval (the Romanian sanitary approval or notification for contact with drinking water, or the EU declaration of conformity under Regulation (EU) 2024/370), manual, other); covers (the ranges or models it names; for declarations, the exact list declared); issuer, issue_date, valid_until; for declarations, the directives, regulations and standards cited; listed_as (the form's attachment label it corresponds to, or null).

Per item: the values in section 5, each as value, unit, source (file), page, quote (at most 15 words, never a name from data/raw/NAMES.txt), status and checked_by. Values read by the AI reader start as extracted. Luca verifies them in the app; verified values get status verified and checked_by Luca. A value not found is empty, with status unclear and a note on where it was looked for. Never guess. File names are never trusted for what a document is.

## 5. Values per family
- pump: application (booster, circulation for heating or cooling, dhw_circulation for hot water recirculation, dhw_charging between the hot water store and its heat exchanger, stormwater, drainage), model, product number, flow and head at the duty point, motor power P2, voltage, starting method, maximum working pressure (PN), liquid temperature range, controller or panel included, BMS communication (protocol; module included or optional), motor efficiency class if given;
- ahu: model, airflow per unit, external static pressure, heat recovery type, heat recovery efficiency (as printed, with its standard), SFPint and SFPint_limit, filter classes (ISO 16890) for supply and extract, filter warning, energy class (Eurovent or RLT) if given, dimensions and weight, sound power (info);
- outdoor_unit: model, cooling and heating capacity, refrigerant, refrigerant charge, GWP if given, SEER and SCOP if given;
- dx_kit: model, compatible outdoor units, control and communication;
- the second batch families (fire_damper, radiator, elastomeric_insulation, fire_detection_panel, visual_alarm_device, voice_alarm_control, voice_alarm_loudspeaker, fire_alarm_power_supply, cable): the model only, for now; their checks look at the documents, not at values.

## 6. Checks (checks/maf/, plain Python, one test each in tests/)
Results: pass, flag, unclear, info. A check passes only on verified values; extracted or missing values give unclear. A check with no requirement to compare against gives info "no requirement given". Rules come from data/maf/rules.csv, resolved by location as in docs/jurisdictions.md.

| id | Check | Logic | Rules |
|---|---|---|---|
| D1 | Required documents | for each item, every document in data/maf/family_documents.csv for its family and the location chain is present (by doc_type and covers); an item whose family has no row in that table gives unclear, so it is never let through unchecked | data/maf/family_documents.csv |
| D2 | Declarations match the items | each declaration covers at least one submitted item; flag a declaration that covers none, and name the items left without one | EU-MACH-DOC, EU-LVD-DOC |
| D3 | Documents in date | valid_until on or after the review date, else flag; on or after the delivery date, else flag "renew before delivery"; no date: info | CL-02 |
| D4 | Documents are what the form says | each attachment's doc_type agrees with the label it is listed as; every listed attachment exists | practice |
| V1 | Duty point | data sheet flow and head at the duty point meet the form's duty, with no tolerance (the designer's margins are already in the duty) | ENG-DUTY-TOL |
| V2 | Pressure rating | PN at least the required pressure; no requirement: info | CL-05 |
| V3 | Liquid temperature | the pump's liquid temperature range covers the project's temperature range for its application; for hot water pumps with no project range, at least the temperature of the location's hot water rule (RO 60 °C, ES 70 °C); otherwise info, with the range from the data sheet | ANY-PRACTICE-LIQUID-TEMP, RO-I9-23-7, ES-RD487-DHW-70 |
| E1 | Ecodesign, ventilation units | heat recovery efficiency against EU-ECO-VU-HRS (or -RAC); SFPint at most SFPint_limit; filter warning present | EU-ECO-VU-* |
| H1 | Drinking water approval | a booster set or a hot water pump (dhw_circulation, dhw_charging) has a document approving it for contact with drinking water that names it; heating and cooling circulation pumps are not asked (Luca, 12 Nov 2026); flag if none; no rule for the location: unclear | RO-OMS275-DW, ES-RD3-DTU-DW (until 30 Dec 2026), EU-DW-DOC (from 31 Dec 2026) |
| C | Checklist | every item of data/maf/checklist.csv for the family, with its source rows as the reason | data/maf/checklist.csv |
| P | Consultant's rules | every active rule in data/maf/consultant_rules.csv for the item's family (and application, when the rule names one); see below | data/maf/consultant_rules.csv |
| Q | BOQ line | for each item, the line of the project's BOQ it answers, and each thing that line asks for, checked against the readings; see below | the BOQ in data/raw/boq/ |
| R | Location reminders | the location's delivery documents (RO: declaration, quality certificate, guarantee; ES: CTE 7.2 and RITE 20) as info | RO-PRACTICE-DELIVERY, ES-CTE-7-2, ES-RITE-20 |

### Consultant's rules (check P)
Rules the consultant adds on top of the law and the checklist: preferences, not requirements, and the answer says so ("the consultant asks"). Luca, 12 Nov 2026: a control panel for pumps is such a preference, not in any normative; other examples are "pumps only Grundfos" or "balancing valves only IMI or Danfoss".

One row per rule in data/maf/consultant_rules.csv: rule_id (CR-01, CR-02...), family ("all" or families separated by ";"), application (optional, pump applications separated by ";"), kind, field, operator, value, unit, effect, text (what the reviewer reads), source, added_on, active (yes or no). Five kinds:
- brand: the item's brand is one of the brands in value ("Grundfos" or "IMI;Danfoss");
- value: the reading in field compares with value by operator (>=, <= or =), in the same unit; no reading, or another unit: unclear;
- document: the package has a document of type field that names the item;
- included: one of the readings in field ("controller_included|float_switch") is yes;
- reminder: always info, for what the reviewer checks by hand.

Effect when a rule is not met: B (a comment), C (revise and resubmit, blocking) or info. The consultant adds a rule and switches it on or off on the Rules screen; the rules apply to every package. Shortcut: one set of rules for every project and consultant; per project sets come when a second project needs different ones. The consultant can also type a rule in words ("pumps only from Grundfos"): an AI turns it into a row, shown as a sentence labelled AI, and nothing is saved until the consultant saves it. The AI is Claude, through the Claude command line on the laptop (no tools, structured answer); without it the consultant fills the form by hand.

### The BOQ (check Q)
The project's bill of quantities, an Excel file (.xlsx or .xls), sits in data/raw/boq/ (git-ignored: it holds prices). The reader (ingest/boq.py, no AI) finds the header row of each sheet (number, description, unit, quantity; producer and standards when the sheet has them) and keeps every line with a description; prices are never read.

- which line: the sheets whose name starts with the form's BOQ code (P01: IS06), then the line whose flow and head (Q=..., H=...) equal the item's duty; no line found: unclear; no BOQ at all: no Q result, and CL-04 says so;
- what the line asks: an AI reads the line once and lists what it asks for, each as a consultant-style rule (included, brand, value, reminder) with the exact words it comes from; a reference model or "or equivalent" is a reminder, not a brand rule; the list is cached in data/raw/boq/ and labelled AI;
- the motor power in a BOQ is the designer's estimate, not a limit (Luca, 12 Nov 2026): shown as information;
- the check is deterministic: each thing asked is checked like a consultant's rule, from the readings; the BOQ line is AI output, so a result stays unclear until the reviewer confirms it ("would be" otherwise).


## 7. Draft status (written rules, not a model; Luca confirms or changes them)
- Revise and resubmit (C): an item has no data sheet, or its data sheet does not show the submitted model, or a checklist item marked blocking is missing;
- Approved as noted (B): no C condition, but at least one flag or unclear; one note per flag or unclear;
- Approved (A): everything pass or info;
- Not approved and Sample requested: only the reviewer chooses them;
- the app always shows "draft, the reviewer decides" and the reason for the status; every reason is explained in docs/maf_status_reasons.md.

A missing declaration stays B until the reviewer approves it by hand (Luca, 29 Oct 2026).

In the earlier register, missing declarations led to a reminder for the delivery, not to a C (three such MAFs were approved). That is why a missing declaration is a flag (B), not a C.

## 8. Draft comments (explain/)
One sentence per flag or unclear, from a template per check, in English, in the tone of the reviewers' past comments. A language model may only rephrase them, never add values. Example for D2: "The declaration of conformity attached for {covers} matches no product in the MAF; please attach the declarations for {items}."

## 9. Interface (app/)
One application over the checks, `app/review_server.py` with `app/review/`, which runs only on the laptop:
- Packages: the packages already read, each with its draft answer and what is left, and the packages not read yet; a search and a discipline filter;
- the review of one package, in three steps (Problems, Confirm readings, Answer), under a header with the form, the draft answer and its reasons, and how much is left;
- Problems: one finding at a time, grouped by product, then the whole package, then the AI suggestions, with the real page open beside it and the quoted line marked; the reviewer keeps it in the answer, marks it "not a problem" with a reason, or goes to the next;
- Confirm readings: document by document and page by page, each reading marked on the page, with a tick that records who confirmed it (checked_by); a page without a text layer says so and lists what to look for on it;
- Answer: the draft with one comment per issue, what was checked and what could not be checked; only here can the country and the dates be changed;
- exports: the answer, the confirmed values (item, value, unit, source, page) for the certification consultant and the O&M file, and the findings marked "not a problem" with their reasons;
- Packages also lists the BOQ files and takes a new one;
- Rules: the consultant's own rules first, in words or by hand, then the rules of the law;
- Add a package, Booster sizing and Standby test: the pump workflow of the midterm, as screens of the same application;
- Rules: every rule for a location, with its source and status.

## 10. Tests and evaluation
- pytest unit tests for every check, with hand written cases approved by Luca;
- a reference answer per package, written by Luca before he sees the tool's output, kept in data/maf/reference/ and never used for tuning;
- comparison: found by both, found only by the tool (real or not), missed by the tool;
- Luca's time to review each package by hand, against his time to check the tool's draft.

### Projects
The reviewer works on one project at a time and picks it in the rail; a new project needs a name and a country. Each project is a folder under data/projects/ (git-ignored, because it holds the client's documents; `--projects` points the application at another folder, such as a shared Google Drive folder):

    <project>/project.json   name, country (RO or ES), created; optional paths for packages, originals and boq
    <project>/packages/      the read packages (<package>.json) and, per package, a folder with its original files
    <project>/boq/           every BOQ of the project, read together, and the cache of what their lines ask

A package uploaded on "Add a package" can be saved into the project; it then shows as not read yet until the reader has been through it. A project's paths can point elsewhere: the project of P01 and P02 uses data/maf/extracted, data/raw and data/raw/boq, where they already are. With no project, the application shows those examples. Shortcut: the consultant's rules stay one set for every project; one set per project comes when a second project needs different ones.

## 11. Data and privacy
- data/raw/ holds the originals and is git-ignored; so does data/projects/;
- a project's name is shown only on this laptop and never written into Git;
- the anonymised register of the earlier project stays outside Git, as docs/data_map.md says for the approval forms; docs/maf_register_findings.md keeps only counts and short anonymised examples, and the row ids (R01 to R80) refer to Luca's local copy;
- no client, project, company or personal names anywhere in Git; manufacturer names and model codes are fine;
- no prices.

## 12. Open questions
- the draft status rules (Luca);
- the duty point tolerance: none (Luca, 28 Oct 2026, ENG-DUTY-TOL);
- which roles sit behind the four reviewer columns of the register (Luca);
- the CTE and RITE articles checked against the BOE (the Romanian articles were read on legislatie.just.ro on 12 Nov 2026);
- which LEED, BREEAM or VERDE values join each family's checklist (Sahil or Jeff);
- V3 and H1 (asked for by a practising MEP consultant on 12 Nov 2026): Luca answered which pumps need a drinking water approval; P01's pumps (booster and drainage) see no high temperatures, so V3 stays info for them; control panels are a consultant's preference (check P), not a requirement.
