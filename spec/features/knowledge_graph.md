# Feature spec: the knowledge graph of products that come back (MAF-36)

Status: 26 Nov 2026. Luca asked for it and answered the questions the same day (section 10). First kinds: cables, pipes, valves and boilers. The first part of MAF-36a is built: the product lines read from the forms, the register of the previous project and the BOQ (`ingest/products.py`, `ingest/graph.py`, with tests), drawn for admins on the Inside RightFit page (section 7). The page for the consultant comes next.

## 1. What it does

Some products come back from one project to the next: pipes and fittings, cables, insulation, valves, cable trays and conduits, radiators, perhaps boilers. For those, RightFit keeps what it learned in one project for the next: which product line was submitted, by which producer, in which form, with which documents, what the answer was, and which lines of the BOQ it covered. When the same product line comes back, the consultant sees that history beside the new package.

Pumps and air handling units are left out. The same unit with the same duty point almost never comes back in another project, so there is little to reuse (Luca, 26 Nov 2026). Boilers and valves are in (Luca, the same day).

## 2. Why

- the register of Luca's previous project holds 80 forms: 12 are pipes, 9 fittings, 7 valves and 2 insulation, from 7 pipe brands and 7 valve brands;
- the current project has 4 cable packages (two fire resistant E30 PH30, one NHXH, one FTP cat 6a), 2 insulation packages, a cable tray, a flexible conduit and junction boxes;
- a product line answered once, with documents still in date, need not be read and checked from nothing;
- one form covers a range, for example 30 diameters of one pipe, so the BOQ register (MAF-34) has to know which lines a product line covers.

## 3. The graph

A product line is the node everything hangs on. It is a producer, a kind (pipe, fitting, cable, insulation, valve, tray, conduit, radiator, boiler), a series or type designation (for example PPR PN20, NHXH E30, FTP cat 6a) and the range of sizes submitted (diameters, cross-sections, thicknesses).

| Node | What it holds |
|---|---|
| product line | producer, kind, designation, size range |
| project | as in RightFit online |
| form | number and revision, in a project |
| document | a fingerprint (SHA-256 of the file, and of its text), its kind, issuer, issue date, valid until |
| BOQ line | as `boq_line` online, never the price |

| Edge | Meaning |
|---|---|
| form submits product line | with the sizes submitted |
| form was answered | A, B or C, when and by which role: from the review online, or from the register |
| document supports product line | a declaration of performance, a technical approval or a certificate, found in a form |
| BOQ line asks for product line | same kind and designation, size within the range |
| form revises form | the chain of revisions |

What makes two descriptions the same product line, by kind (Luca, 26 Nov 2026):

| Kind | Same product line when these agree | Range |
|---|---|---|
| pipe | producer, material, pressure class, standard, and the use: drinking water or not; the series only when given | the diameters: a pipe data sheet usually lists many |
| cable | producer, type designation (NHXH, JE-H(St)H ...), fire behaviour (E30, E90, PH30, PH120, FE180), CPR reaction class, standard | the cross-sections or pairs: a catalogue page or data sheet usually lists many (NHXH in P20 lists about 24); some producers add one sheet per construction (P19), and a data cable has one construction (P23) |
| valve | producer, type (ball, gate, check, balancing ...), connection (thread, union, flange), pressure class, use | the nominal diameters |
| boiler | producer, series and fuel | the output powers of the series |

A part that a description does not give stays unknown, and two lines that differ only by an unknown part are a near match, shown as a question. A product line whose main part (a pipe's material, a cable's type, a valve's type, a boiler's series) is not given is never linked to anything.

An air damper (clapetă) is not a valve: a clapetă counts as a valve only when it holds water back (de reținere, de sens). PE written alone is the material only in capitals, since a lower-case "pe" is the Romanian "on"; a black pipe (țeavă neagră) is steel, and Zn is galvanised steel.

The graph is kept as tables in D1, next to the project's data. No graph database is needed: the nodes and edges are rows.

## 4. How it is filled, with no AI and no cost

- forms: `ingest/maf_form.py` reads each form's products (description, producer, type) for the 51 packages, and the register of the previous project gives description, brand and answers for its 80 forms;
- documents: a fingerprint of every file; its kind from the form's list of attachments, or from our page classifier, labelled as AI;
- BOQ lines: `ingest/boq.py`, as now, never the prices;
- normalisers, one per kind: plain rules that pull the designation and the sizes out of a description, such as `DN 20-110`, `Ø20x2.8`, `3x2.5 mm²`, `E30 PH30`, `cat 6a` or a thickness of `13 mm`; each rule has tests on made-up descriptions and is written with Luca;
- matching: two descriptions are the same product line when producer, kind and designation agree once normalised, by rules Luca approves. There is no fuzzy guess for a match that counts: a near match is shown as a question for a person.

## 5. Who sees it

What the graph holds is the consultant's knowledge, not a project's. It is shown to the consultant's own people across their projects, never to a contractor or subcontractor of another project. A document stays in its project: the graph keeps its fingerprint and what was decided, and opens the document only for a member of that project. A manufacturer's declaration of performance, which the CPR obliges it to publish, can be linked from its public source. Version 2026-11-26 of the data processing agreement (clause 1.4), of the privacy policy and of the terms says so (Luca, 26 Nov 2026). A project counts across projects only once a consultant of it has accepted that version or a later one; a project opened before keeps the version it accepted until then.

## 6. What it shows

- on a package: this product line was answered B in another project, form IS 013 rev 1, on a date; its declaration of performance is the same file (same fingerprint) and still in date at delivery;
- an earlier approval lowers what is checked again (Luca, 26 Nov 2026): the readings confirmed on the same file in an approved form count as confirmed here, marked with where they were confirmed, while the documents are still checked for the new review and delivery dates;
- in the BOQ register (MAF-34): for each chapter, the BOQ lines covered by a product line already approved, by kind, designation and size range, and the lines still without a form;
- per producer: forms, returns and their causes, from the register and from the reviews online.

## 7. The page for admins: inside RightFit

Luca asked on 26 Nov 2026 for a page, for admins only, that shows how RightFit and all its tools work, the way the hackathon app's Look inside explained its network with the network's own numbers. It sits in Management:

- the path of a package, step by step (files, pages, readings, checks, draft answer, the reviewer, the answer), with the real numbers of a package the admin picks;
- the tools: the checks engine, the checks with their rules, our two models with their scores, booster sizing, the revision comparison, the rule watch, the tools for agents;
- the knowledge graph drawn: product lines in the middle, the forms of each project around them, the BOQ lines they cover, the documents that support them.

Management itself still never opens a project's data: the page shows a project only to an admin who is a member of it, with the team password for a locked project, exactly as the project's own pages do.

## 8. Phases

| ID | What | Done when |
|---|---|---|
| MAF-36a | The inventory: product lines from the 51 forms, the register and the BOQ, with the normalisers for cables and pipes first; a page online for the consultant | each kind's normaliser has tests, and the page lists the product lines with their forms, answers and BOQ lines |
| MAF-36b | Documents by fingerprint across projects, and confirmed readings offered for reuse | the same file in two packages is recognised, and a reuse needs a person's confirmation |
| MAF-36c | The BOQ register (MAF-34) on top of the graph | each BOQ line shows the approved product line that covers it, or none |


## 9. Tests

The normalisers on made-up descriptions (never a real company or project name), the matching rules, and who sees what: a consultant sees the graph across their own projects; a contractor or subcontractor never sees another project's history.

## 10. Questions, answered by Luca on 26 Nov 2026

1. Pipes: producer, material, pressure class, standard and use (drinking water or not), the series not necessarily; a data sheet usually lists many diameters.
2. Cables: studied on our own sheets; the proposal in section 3 waits for his check.
3. An earlier approval may lower what is checked again.
4. Boilers are in; valves too.
5. Yes: clause 1.4 of the data processing agreement, with the privacy policy and the terms, all version 2026-11-26.
6. Yes: cables and pipes first, with valves and boilers.
