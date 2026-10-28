# Tech Stack — RightFit

Version 0.1 (draft) · 28 Oct 2026 · Full version due 12 Nov 2026

Tags: **[C]** agreed in team discussion; formal approval of this v0.1 draft is pending · **[P]** proposed, awaiting approval · **[O]** open question

Nothing listed as [P] is installed or tested yet. Each choice is confirmed only after a small test in this repository.

## 1. Confirmed tools [C]

| Tool | Use |
|---|---|
| Python | Main programming language |
| Git + GitHub (`iaac-maai/RightFit`, private) | Version control and collaboration |
| VS Code | Editor |
| Markdown | Documentation and specifications |

## 2. Proposed components [P]

| Component | Candidate | Why | Alternative |
|---|---|---|---|
| Image/text matching | Pretrained SigLIP or CLIP model, used as-is (no training) | Matches words and images to product photos without hand-written rules | Keyword search only |
| Similarity search | NumPy (small catalogue); FAISS if needed | A few hundred products fit easily in memory | A vector database (likely unnecessary at this size) |
| Keyword baseline | BM25 (e.g. `rank_bm25`) | Standard non-AI comparison | Simple text matching |
| PDF reading | `pdfplumber` or PyMuPDF | Extract text and tables from data sheets with page numbers | Manual entry |
| Data-sheet extraction | A language model returning values with page citations, checked by a person | Data sheets are formatted differently by each manufacturer | Manual entry only |
| Attribute tagging | A vision-language model (colour, finish, mounting type), confirmed by Jeff | Avoids tagging hundreds of images by hand | Manual tagging |
| Engineering checks | Plain Python functions | Must be exact, explainable and testable | none (no AI allowed here) |
| Interface | Streamlit | Simple, Python-only, already known by Luca | Gradio |
| Tests | pytest | Standard and simple | `unittest` |
| MCP | Official MCP Python SDK | Expose search and checks as tools to AI agents | none decided |

## 3. Data sources

| Source | Use | Status |
|---|---|---|
| Manufacturer catalogues and product images | Visual and text search | [C] planned, not yet collected |
| Manufacturer data sheets | Airflow, dimensions, noise, power | [C] planned, not yet collected |
| Installation manuals | Duct diameter, mounting heights, required voids, duct length limits | [P] availability to be audited |
| EPREL (EU energy label registry), public product pages | Cross-check of airflow, noise and efficiency values | [P] to be tested |
| Engineering standards for the testing context | Requirements the checks apply | [O] Spain provisional; Luca to confirm which standards apply |
| Team's past projects, anonymised | Real rooms and conflicts for test briefs | [C] planned; anonymisation required |
| v1 data: 79 MEP approval forms | Evidence of interior/MEP conflicts | [C] held; confidential; stays outside Git |
| Designer picks and rejections in the tool | Re-ranking | [C] created during testing |

Full details are in `docs/data_map.md`.

## 4. Architecture [P]

```text
Designer input (text or image + room description)
        |
        v
1. Retrieval (AI)            search/   -> ranked candidates with similarity scores
        |
        v
2. Engineering checks        checks/   -> pass / flag / unclear per check, with sources
   (deterministic, no AI)
        |
        v
3. Explanation (template)    explain/  -> trade-offs built only from verified values
        |
        v
4. Interface                 app/      -> results; AI output and checks shown separately
```

**Boundary rule [C]:** no code in `checks/` may import or call an AI model.

## 5. Data rule [C]

Every technical value is stored with:

| Field | Meaning |
|---|---|
| `value` | The number or text, or empty if missing |
| `unit` | e.g. m³/h, mm, dB(A) |
| `source` | URL or file name |
| `page` | Page number in the source, if applicable |
| `status` | `verified`, `extracted` or `unclear` |
| `checked_by` | Team member who verified it, if verified |

The exact file format (CSV, JSON or JSONL) is [O].

## 6. Planned repository structure [P]

```text
RightFit/
|-- AGENTS.md
|-- README.md
|-- spec/
|   |-- constitution/     mission, roadmap, tech stack
|   `-- features/         one specification per feature
|-- docs/                 segmentation tree, data map, decisions
|-- data/
|   |-- raw/              images and PDFs (git-ignored)
|   `-- catalogue/        catalogue files with sourced values
|-- ingest/               data-sheet and EPREL extraction
|-- search/               AI retrieval and keyword baseline
|-- checks/               deterministic MEP checks
|-- explain/              templated explanations
|-- app/                  interface
|-- eval/
|   |-- dev/              development briefs
|   |-- test/             locked test briefs
|   `-- results/          dated evaluation results
`-- tests/                automated tests
```

Folders are created only when work in them starts.

## 7. Open technical questions [O]

- Python version and environment manager (conda or venv).
- Which language model provider for extraction, its cost, and whether data may be sent to it.
- Whether a laptop CPU is fast enough for SigLIP/CLIP on the full catalogue (to be measured, not assumed).
- Licences of the chosen pretrained models.
- Catalogue file format.
- Where the interface runs for the final demo (local or hosted).

## 8. Dependency policy [C]

- Use the fewest dependencies possible.
- Each new dependency is recorded in `docs/decisions.md` with the reason.
- Exact versions are pinned once the environment is chosen.

## 9. Change log

| Date | Change | Agreed by |
|---|---|---|
| 28 Oct 2026 | v0.1 draft created | pending: Sahil, Jeff, Luca |