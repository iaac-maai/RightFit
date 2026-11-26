# RightFit tech stack

Full version for 12 Nov 2026, brought up to date on 16 Nov 2026. It is built on the MAF direction the team agreed on 5 Nov 2026. Open questions are marked [O].

## 1. Tools

We work in Python, with Git and GitHub (`iaac-maai/RightFit`, a public repository), VS Code and Markdown, as agreed for the hood version. For the MAF checker we have installed and used:

| Tool | What we use it for |
|---|---|
| xlrd and openpyxl | Reading the MAF form, which comes as an old .xls file (`ingest/maf_form.py`), and the project's BOQ, .xls or .xlsx (`ingest/boq.py`) |
| pytest | Tests for every check (`tests/`) |
| The Claude command line (`claude -p`, Haiku, no tools) | The AI the application asks: a rule typed in words, what a BOQ line asks (`app/ai.py`) |
| Python's standard library (`http.server`), with plain HTML, CSS and JavaScript | The application (`app/review_server.py`, `app/review/`), which runs only on the laptop |
| pypdf and PyMuPDF (`pymupdf`) | The text of each PDF page, page images, marking quoted lines on the page, and pump curves from a data sheet's vector drawing |
| Tesseract with `pytesseract` | OCR of scanned pages when a pump package is added |
| scikit-learn | Our own page classifier (`model/`), trained from scratch and compared with a keyword search; also the text similarity that picks a product's BOQ line among the positions the form names |
| An AI agent that reads PDFs | Reading the attachments, as text or as page images, into values with page and quote. A person verifies every value before a check can pass on it |
| Revit 2026 with pyRevit (free, open source) | The fit check in the project's Revit model (`revit/`): pyRevit runs our Python inside Revit, on the Windows computer that has Revit; the checks it calls are `checks/space/`, also run by the tests |
| The official MCP Python SDK (`mcp`) | The MCP server (`app/mcp_server.py`): six read-only tools an agent can call to list the packages, review one, list the rules with their status, classify a package's pages, compare a package with the previous revision of its form and ask the official sources whether the act behind each legal rule changed; `.mcp.json` tells the agent how to start it, and `.codex/config.toml` does the same for a second agent client |
| Cloudflare Workers, D1 and R2, with Wrangler | RightFit online (`web/`, `spec/features/rightfit_online.md`): the Worker serves the page and answers the API, D1 keeps the accounts, projects, members and invitations, R2 the package files; free plan, on Luca's account |
| React, with Vite and TypeScript | The page of RightFit online |
| Better Auth | Sign-in to RightFit online, with Google or with an email and a password; sessions in D1 |
| Cloudflare Python Workers | The engine of RightFit online (MAF-33, since 21 Nov 2026): the laptop's own review code (`app/engine.py`, `app/review_core.py`, `checks/maf/`) in a Worker that only the site's Worker calls; standard library only, no package to install |
| Render | Kept for later: a server for reading new packages online (OCR, the AI, our models), which a Worker cannot run |

The hood version also planned SigLIP/CLIP image matching, a BM25 keyword baseline and a vision model for tagging finishes. The MAF review doesn't need any of them.

## 2. Data sources

| Source | What for | Where it stands |
|---|---|---|
| The two MAF packages (form and attachments) | Everything the checks read | Held; originals in `data/raw/`, outside Git |
| 48 more packages from the same project (285 PDFs, 1,296 pages) | Training and locked testing of our own models; the evaluation on unseen packages | Held since 6 Nov, in `data/raw/`, outside Git; listed in the app, not read yet |
| The register of 80 MAFs from Luca's last project | Evidence for the problem, and the source of the checklist | Held; anonymised, outside Git; counts in `docs/maf_register_findings.md` |
| EU texts (machinery, low voltage, construction products, ecodesign of ventilation units, drinking water) | Rules for documents and ecodesign | Every rule read on the official text by 16 Nov, through the Publications Office, because EUR-Lex no longer answers scripts |
| Romanian law (Law 10/1995 until 24 Aug 2026, then the construction Code, Law 169/2026) and Spanish CTE and RITE | National rules and delivery reminders | The Romanian articles read on legislatie.just.ro on 12 and 16 Nov; the Spanish ones on the BOE open data service on 16 Nov |
| Manufacturer data sheets and declarations | Values per product | Only those inside the packages |
| The project's BOQ (Excel) | What each product's line asks for (check Q) | Held for the project of P01 and P02; outside Git, because it holds prices, which are never read |
| The consultant's own rules | Check P | In Git (`data/maf/consultant_rules.csv`), five example rules |

The full list is in `docs/data_map.md`.

## 3. How the pieces fit

```text
MAF form (.xls) + attachments (PDF)                      the project's BOQ (.xlsx or .xls)
        |                                                        |
        v                                                        v
ingest/      the form is read in Python, roles only;     the lines are read in Python, never the prices;
             the attachments are read by the AI agent    an AI lists what a product's line asks for
             -> data/maf/extracted/<package>.json: every value with source, page, quote, status
        |
        v  (a person verifies the values in the app)
checks/maf/  plain Python, no AI; rules from data/maf/:  -> pass / flag / unclear / info per check
             the law by date, the reviewers' checklist,
             the consultant's own rules, the BOQ line
        |
        v
checks/maf/comments.py  comments filled from templates   -> one sentence per issue
        |
        v
app/         the application, one project at a time      -> draft status, overrides, exports
             the same checks as MCP tools                -> any agent that speaks MCP (read only)

model/       our page and family classifiers             -> what kind of document each page is; a hint, labelled as AI
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
|-- AGENTS.md, README.md, PRODUCT.md, DESIGN.md, requirements.txt, pytest.ini
|-- .mcp.json, .codex/     how an agent starts the MCP server
|-- spec/
|   |-- constitution/      mission, roadmap, tech stack
|   `-- features/          maf_checker.md
|-- docs/                  problem tree, data map, decisions, workflow, register findings, rules
|-- data/
|   |-- raw/               original packages, BOQ and register (git-ignored)
|   |-- projects/          one folder per project: packages, originals, BOQs (git-ignored)
|   |-- maf/               rules, checklist, consultant's rules, inventory, extracted/, reference/
|   `-- space/             the fit check's rules
|-- ingest/                form reader, BOQ reader, rule watch, revision comparison, the instructions given to the AI (prompts/)
|-- checks/maf/            the checks, the draft status and the comment templates
|-- checks/pumps/          pump rules, booster sizing and the standby test
|-- checks/space/          the fit check: the set in its room, and what a swap changes
|-- revit/                 the Revit add-in (pyRevit) and the templates of its project files
|-- model/                 our page classifier and family classifier
|-- eval/                  labels, sources and results of every comparison with a baseline
|-- app/                   the application (review/), the MCP server, the AI helper
`-- tests/                 tests
```

Each top folder has a short README that says what is in it. We create a folder only when work in it starts.

## 6. Open questions [O]

- The Python version and environment manager. We have tested with Python 3.14 so far.
- Which model reads the packages, what it costs, and whether real packages may be sent to it. The manufacturer documents are public; the forms and the project headers on some pages are not. What already goes to an online model is in `mission.md` §9.
- Answered on 20 Nov 2026, where the application runs: both. The review app stays on the laptop, and RightFit online, the project space where the parties meet, runs on Cloudflare, with the checks on Cloudflare as well since 21 Nov 2026, in a Python Worker (`spec/features/rightfit_online.md`).
- Which agent the team uses with the MCP server.

## 7. Dependencies

We keep them few. Each new one goes in `docs/decisions.md` with the reason, and we pin exact versions once we have chosen the environment.

Changes to this file are recorded in `docs/decisions.md`.
