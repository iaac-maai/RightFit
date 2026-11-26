# Feature spec: the knowledge graph of products that come back (MAF-36)

Status: draft, 26 Nov 2026. Luca asked for it the same day; the open questions in section 9 wait for him.

## 1. What it does

Some products come back from one project to the next: pipes and fittings, cables, insulation, valves, cable trays and conduits, radiators, perhaps boilers. For those, RightFit keeps what it learned in one project for the next: which product line was submitted, by which producer, in which form, with which documents, what the answer was, and which lines of the BOQ it covered. When the same product line comes back, the consultant sees that history beside the new package.

Pumps and air handling units are left out. The same unit with the same duty point almost never comes back in another project, so there is little to reuse (Luca, 26 Nov 2026).

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

The graph is kept as tables in D1, next to the project's data. No graph database is needed: the nodes and edges are rows.

## 4. How it is filled, with no AI and no cost

- forms: `ingest/maf_form.py` reads each form's products (description, producer, type) for the 51 packages, and the register of the previous project gives description, brand and answers for its 80 forms;
- documents: a fingerprint of every file; its kind from the form's list of attachments, or from our page classifier, labelled as AI;
- BOQ lines: `ingest/boq.py`, as now, never the prices;
- normalisers, one per kind: plain rules that pull the designation and the sizes out of a description, such as `DN 20-110`, `Ø20x2.8`, `3x2.5 mm²`, `E30 PH30`, `cat 6a` or a thickness of `13 mm`; each rule has tests on made-up descriptions and is written with Luca;
- matching: two descriptions are the same product line when producer, kind and designation agree once normalised, by rules Luca approves. There is no fuzzy guess for a match that counts: a near match is shown as a question for a person.

## 5. Who sees it

What the graph holds is the consultant's knowledge, not a project's. It is shown to the consultant's own people across their projects, never to a contractor or subcontractor of another project. A document stays in its project: the graph keeps its fingerprint and what was decided, and opens the document only for a member of that project. A manufacturer's declaration of performance, which the CPR obliges it to publish, can be linked from its public source. The data processing agreement says a project's data is processed for that project, so using it across the consultant's projects needs a line in the agreement and in the privacy policy [O].

## 6. What it shows

- on a package: this product line was answered B in another project, form IS 013 rev 1, on a date; its declaration of performance is the same file (same fingerprint) and still in date at delivery; the readings confirmed then are offered for reuse, and a person confirms them;
- in the BOQ register (MAF-34): for each chapter, the BOQ lines covered by a product line already approved, by kind, designation and size range, and the lines still without a form;
- per producer: forms, returns and their causes, from the register and from the reviews online.

## 7. Phases

| ID | What | Done when |
|---|---|---|
| MAF-36a | The inventory: product lines from the 51 forms, the register and the BOQ, with the normalisers for cables and pipes first; a page online for the consultant | each kind's normaliser has tests, and the page lists the product lines with their forms, answers and BOQ lines |
| MAF-36b | Documents by fingerprint across projects, and confirmed readings offered for reuse | the same file in two packages is recognised, and a reuse needs a person's confirmation |
| MAF-36c | The BOQ register (MAF-34) on top of the graph | each BOQ line shows the approved product line that covers it, or none |

Boilers come in if Luca says so.

## 8. Tests

The normalisers on made-up descriptions (never a real company or project name), the matching rules, and who sees what: a consultant sees the graph across their own projects; a contractor or subcontractor never sees another project's history.

## 9. Open questions [O]

1. Pipes: what makes two pipes the same product line? Producer, material and series or pressure class, and the standard? Are the diameters one range?
2. Cables: producer and designation, with the fire class (E30, PH30) and the CPR reaction class? Are the cross-sections one range?
3. Does an earlier approval only show as a hint, or may it lower what has to be checked again?
4. Boilers: in or out?
5. A line in the data processing agreement and the privacy policy for using a project's data across the consultant's projects.
6. Which kinds first: cables and pipes?
