# Problem Segmentation Tree — RightFit

IAAC deliverable, 29 Oct 2026. MAF version on branch `maf-checker`; the hood version is on `main` and the team chooses which one to hand in. Open questions are marked [O].

We split the work by who does each step. "Human" means one of us or a reviewer decides. "AI" means a model reads or interprets, and a person checks what it read. "Rule" is a fixed check in plain Python. "Data" is collecting, storing and moving files.

## 1. Tree

```text
L0  MEP approval forms go back and forth. Each reviewer reads the same
    documents again, and missing items are found late.
 |
 |-- L1  MAF review of MEP equipment, Design & Pre-Construction
 |    |
 |    `-- L2  Prototype: pumps and air handling units (P01, P02)
 |         |
 |         |-- 1. Receive the package
 |         |-- 2. Read the documents
 |         |-- 3. Set the context
 |         |-- 4. Check the documents
 |         |-- 5. Check the values
 |         |-- 6. Draft the answer
 |         `-- 7. Decide and evaluate
 |
 `-- L1  Other families (fire dampers and valves, pipes, meters): later
```

The check codes in the last column (D1, V1, C...) are the ones in `spec/features/maf_checker.md`.

## 2. Tasks

### 1. Receive the package

| ID | Task | Type | Who | Status |
|---|---|---|---|---|
| 1.1 | Fill in the form and attach the documents | Human | Contractor | Outside the tool |
| 1.2 | Read the form fields: number, revision, items, duty, attachments, signer roles | Rule | `ingest/maf_form.py` | Done |
| 1.3 | Keep the originals on our laptops, outside Git | Data | Luca | Done (`data/raw/`) |

### 2. Read the documents

| ID | Task | Type | Who | Status |
|---|---|---|---|---|
| 2.1 | List every file with pages, text layer and language | Data | AI reader | Done (`data/maf/packages.csv`) |
| 2.2 | Say what each document is and which products it covers, and how (exact model, range table, range), never from the file name | AI + Human | AI reader, Luca checks | Read and matched, not verified |
| 2.3 | Read the values each family needs, with page and a short quote | AI + Human | AI reader, Luca checks | Read, not verified |
| 2.4 | Mark a value that isn't there as `unclear`, with where we looked | Rule | AI reader | Done |
| 2.5 | Verify each value in the app | Human | Luca | Not started |

### 3. Set the context

| ID | Task | Type | Who | Status |
|---|---|---|---|---|
| 3.1 | Choose the location (RO or ES), which picks the rules | Human | Reviewer | Done in the app |
| 3.2 | Review date and delivery date (form date plus lead time, unless given) | Human | Reviewer | Done in the app |
| 3.3 | Project requirements from the specification or BOQ | Human | Reviewer | [O] none for P01 and P02 |
| 3.4 | Write each rule with clause, source and status | AI + Human | AI first pass, Luca verifies | Partly; several rules "to confirm" |

### 4. Check the documents

| ID | Task | Type | Check | Status |
|---|---|---|---|---|
| 4.1 | Each item has the documents its family needs | Rule | D1 | Done |
| 4.2 | Each declaration names at least one submitted item | Rule | D2 | Done |
| 4.3 | Certificates are valid on the review date and at delivery | Rule | D3 | Done |
| 4.4 | Each attachment is what the form says it is | Rule | D4 | Done |

### 5. Check the values

| ID | Task | Type | Check | Status |
|---|---|---|---|---|
| 5.1 | The data sheet's duty point meets the form, with no tolerance | Rule | V1 | Done |
| 5.2 | Pressure rating against the required pressure | Rule | V2 | Done; no requirement given yet |
| 5.3 | Ecodesign of air handling units: heat recovery, SFPint, filter warning | Rule | E1 | Done |
| 5.4 | The reviewers' checklist for the family | Rule | C | Done |
| 5.5 | What the location asks for at delivery, as a reminder | Rule | R | Done |
| 5.6 | Issues no rule covers, proposed with page evidence and decided by the reviewer | AI + Human | Second AI reviewer | First run on P01 and P02 |

### 6. Draft the answer

| ID | Task | Type | Who | Status |
|---|---|---|---|---|
| 6.1 | Propose A, B or C with the reasons | Rule | `checks/maf/status.py` | Done; [O] Luca confirms the rules |
| 6.2 | One comment per issue, from templates | Rule | `explain/` | Done |
| 6.3 | Say what was checked and what wasn't | Rule | App | Done |
| 6.4 | Override a result, with a note | Human | Reviewer | Done in the app |
| 6.5 | Sign, and choose the status (including Neaprobat or a sample request) | Human | Reviewer | Outside the tool |

### 7. Decide and evaluate

| ID | Task | Type | Who | Status |
|---|---|---|---|---|
| 7.1 | Write the reference answer before seeing the tool's output | Human | Luca | Done for P01 and P02 |
| 7.2 | Count found by both, found only by the tool, missed by the tool | Data + Human | Sahil, Luca | First pass, on unverified values |
| 7.3 | Time to review by hand against time to check the draft | Human | Luca | By hand done (10 min, 3 h); with the tool not yet |
| 7.4 | Turn new reviewer comments into checklist items | Human | Luca | [O] |

## 3. Where the AI is

The AI reads the attachments (2.2, 2.3), makes a first pass at the rules (3.4) and, as a second reviewer, proposes issues no rule covers (5.6). A person checks all of it. Everything in groups 4 to 6 is fixed rules and templates, and no model can change their result. People choose the location and dates, set the requirements, verify values, override, and sign.

## 4. What runs today

Both packages go through every check, for Romania and for Spain. Because nobody has verified a value yet, every pass and flag still shows as `unclear` together with the result it would give. The next step is 2.5, then 7.2 again on verified values.
