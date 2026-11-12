# Tech Stack — RightFit

Full version for 12 Nov 2026, built on the MAF direction the team agreed on 5 Nov 2026. Open questions are marked [O].

## 1. Tools

We work in Python, with Git and GitHub (`iaac-maai/RightFit`, private), VS Code and Markdown, as agreed for the hood version. For the MAF checker we have installed and used:

| Tool | What we use it for |
|---|---|
| xlrd | Reading the MAF form, which comes as an old .xls file (`ingest/maf_form.py`) |
| pytest | Tests for every check (`tests/`) |
| The Claude command line (`claude -p`, Haiku, no tools) | The AI the application asks: a rule typed in words, what a BOQ line asks (`app/ai.py`) |
| Python's standard library (`http.server`), with plain HTML, CSS and JavaScript | The application (`app/review_server.py`, `app/review/`), which runs only on the laptop |
| pypdf and PyMuPDF (`pymupdf`) | The text of each PDF page, page images, marking quoted lines on the page, and pump curves from a data sheet's vector drawing |
| Tesseract with `pytesseract` | OCR of scanned pages when a pump package is added |
| scikit-learn | Our own page classifier (`model/`), trained from scratch and compared with a keyword search |
| An AI agent that reads PDFs | Reading the attachments, as text or as page images, into values with page and quote. A person verifies every value before a check can pass on it |
| The official MCP Python SDK (`mcp`) | The MCP server (`app/mcp_server.py`): four read-only tools an agent can call to list the packages, review one, list the rules with their status and classify a package's pages; `.mcp.json` tells the agent how to start it |

The hood version also planned SigLIP/CLIP image matching, a BM25 keyword baseline and a vision model for tagging finishes. The MAF review doesn't need any of them.

## 2. Data sources

| Source | What for | Where it stands |
|---|---|---|
| The two MAF packages (form and attachments) | Everything the checks read | Held; originals in `data/raw/`, outside Git |
| 48 more packages from the same project (285 PDFs, 1,296 pages) | Training and locked testing of our own models; the evaluation on unseen packages | Held since 6 Nov, in `data/raw/`, outside Git; listed in the app, not read yet |
| The register of 80 MAFs from Luca's last project | Evidence for the problem, and the source of the checklist | Held; anonymised, outside Git; counts in `docs/maf_register_findings.md` |
| EU texts on EUR-Lex (machinery, low voltage, construction products, ecodesign of ventilation units) | Rules for documents and ecodesign | Partly read; several rows still "to confirm" |
| Romanian law (Law 10/1995 until 24 Aug 2026, then the construction Code, Law 169/2026) and Spanish CTE and RITE | National rules and delivery reminders | The Romanian articles read on legislatie.just.ro on 12 Nov; the Spanish ones on secondary sites, [O] the BOE |
| Manufacturer data sheets and declarations | Values per product | Only those inside the packages |

The full list is in `docs/data_map.md`.

## 3. How the pieces fit

```text
MAF form (.xls) + attachments (PDF)
        |
        v
ingest/      the form is read in Python, roles only;     -> data/maf/extracted/<package>.json
             the attachments are read by the AI agent       every value: source, page, quote, status
        |
        v  (a person verifies the values in the app)
checks/maf/  plain Python, no AI, rules from data/maf/   -> pass / flag / unclear / info per check
        |
        v
explain/     comments filled from templates              -> one sentence per issue
        |
        v
app/         the application                             -> draft status, overrides, exports
             the same checks as MCP tools                -> any agent that speaks MCP (read only)

model/       our page classifier                         -> what kind of document each page is; a hint, labelled as AI
```

Nothing in `checks/` may import or call an AI model.

## 4. Data rule

Every value is stored as:

| Field | Meaning |
|---|---|
| `value` | The number or text, or empty if it wasn't found |
| `unit` | m³/h, l/s, m, bar, kW, %, Pa... |
| `source` | The file it was read from |
| `page` | The page in that file |
| `quote` | At most 15 words from the page, never a name |
| `status` | `extracted`, `verified` or `unclear` |
| `checked_by` | Who verified it |
| `note` | Where we looked, when the value is missing |

We settled the format question from the hood version: one JSON file per package in `data/maf/extracted/`. The rules, the documents each family needs and the checklist are CSV files in `data/maf/`, so that someone who doesn't program can edit them.

## 5. Repository

```text
RightFit/
|-- AGENTS.md, README.md, requirements.txt, pytest.ini
|-- spec/
|   |-- constitution/      mission, roadmap, tech stack
|   `-- features/          maf_checker.md
|-- docs/                  problem tree, data map, decisions, register findings, rules
|-- data/
|   |-- raw/               original packages and register (git-ignored)
|   `-- maf/               rules, checklist, inventory, extracted/, reference/
|-- ingest/                form reader
|-- checks/maf/            the checks and the draft status
|-- checks/pumps/          pump rules, booster sizing and the standby test
|-- explain/               comment templates
|-- model/                 our page classifier
|-- eval/                  labels, sources and results of every comparison with a baseline
|-- app/                   the application (review/) and the MCP server
`-- tests/                 tests
```

We create a folder only when work in it starts.

## 6. Open questions [O]

- The Python version and environment manager. We have tested with Python 3.14 so far.
- Which model reads the packages, what it costs, and whether real packages may be sent to it. The manufacturer documents are public; the forms and the project headers on some pages are not.
- Where the application runs for the final demo, on a laptop or hosted.
- Which agent the team uses with the MCP server.

## 7. Dependencies

We keep them few. Each new one goes in `docs/decisions.md` with the reason, and we pin exact versions once we have chosen the environment.

Changes to this file are recorded in `docs/decisions.md`.
