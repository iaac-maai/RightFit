# Tech Stack — RightFit

Draft for the MAF checker, 28 Oct 2026; the team agreed to it on 5 Nov 2026. Open questions are marked [O].

## 1. Tools

We work in Python, with Git and GitHub (`iaac-maai/RightFit`, private), VS Code and Markdown, as agreed for the hood version. For the MAF checker we have installed and used:

| Tool | What we use it for |
|---|---|
| xlrd | Reading the MAF form, which comes as an old .xls file (`ingest/maf_form.py`) |
| pytest | Tests for every check (`tests/`) |
| Streamlit, with pandas | The first review page (`app/maf_app.py`) |
| Python's standard library (`http.server`), with plain HTML, CSS and JavaScript | The PoC review page (`app/review_server.py`, `app/review/`), which runs only on the laptop |
| An AI agent that reads PDFs | Reading the attachments, as text or as page images, into values with page and quote. A person verifies every value before a check can pass on it |

Still planned: the official MCP Python SDK, to expose the checks as tools an agent can call (12 Nov).

The hood version also planned SigLIP/CLIP image matching, a BM25 keyword baseline and a vision model for tagging finishes. The MAF review doesn't need any of them.

## 2. Data sources

| Source | What for | Where it stands |
|---|---|---|
| The two MAF packages (form and attachments) | Everything the checks read | Held; originals in `data/raw/`, outside Git |
| The register of 80 MAFs from Luca's last project | Evidence for the problem, and the source of the checklist | Held; anonymised, outside Git; counts in `docs/maf_register_findings.md` |
| EU texts on EUR-Lex (machinery, low voltage, construction products, ecodesign of ventilation units) | Rules for documents and ecodesign | Partly read; several rows still "to confirm" |
| Romanian law (Law 10/1995) and Spanish CTE and RITE | National rules and delivery reminders | Read on secondary sites; [O] official journals before the midterm |
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
app/         review pages (Streamlit, and the PoC page)  -> draft status, overrides, exports
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
|-- explain/               comment templates
|-- app/                   Streamlit page, and the PoC review page (review/)
`-- tests/                 tests
```

We create a folder only when work in it starts.

## 6. Open questions [O]

- The Python version and environment manager. We have tested with Python 3.14 so far.
- Which model reads the packages, what it costs, and whether real packages may be sent to it. The manufacturer documents are public; the forms and the project headers on some pages are not.
- Where the page runs for the final demo, on a laptop or hosted.

## 7. Dependencies

We keep them few. Each new one goes in `docs/decisions.md` with the reason, and we pin exact versions once we have chosen the environment.

Changes to this file are recorded in `docs/decisions.md`.
