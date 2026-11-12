# RightFit

RightFit helps the person who signs a material approval form (MAF) for MEP equipment, most often the consultant, check it before signing. It reads the documents attached to the form, checks them against EU and national rules and against a checklist we built from past reviewers' comments, and drafts the answer with a page reference for every finding. The reviewer still decides and signs.

IAAC MaAI01 · Operable Futures · 2026–27 · Sahil Khan, Jeff El Khoury, Luca Obejdeanu

On 5 Nov 2026 the team agreed to move the project from choosing kitchen hoods to reviewing MAFs. The hood version stays in the Git history.

## Why we changed direction

On the last project Luca worked on, 80 MEP approval forms went through review. 22 came back with notes or for resubmission, and 17 needed at least one revision (one of them needed six). A form usually came back after about 12 days. After the last reviewer had answered, it still sat for a median of 7 days before anyone sent it back to the contractor.

8 of those 22 returns were plain gaps in the package: a data sheet for a whole range with nothing marked, a technical approval past its date, pump panels without the BMS module. Someone has to find these by reading every PDF, and they are exactly the kind of thing a computer can point at.

## What it does now

The prototype has two real packages: a set of Grundfos pumps (P01) and an air handling unit with its outdoor units (P02, already at revision 4). For each one it:

- reads the form (.xls) and lists every attachment with its pages and language;
- keeps each value it reads with the file, page, a short quote and a status. Values stay `extracted` until one of us checks them and marks them `verified`;
- checks the documents (are the right ones there, does the declaration name the product, is the certificate still valid, is each attachment what the form says it is), the duty point, the pressure rating, the ecodesign limits for air handling units, and the reviewers' checklist;
- proposes a status (A, B or C) with its reasons and one comment per issue.

A check only passes or flags on verified values. Until then it shows `unclear` and what the result would be.

## Running it

```
pip install -r requirements.txt
brew install tesseract           # OCR for scanned pages when a pump package is added (macOS)
pytest
python app/review_server.py      # the application: http://127.0.0.1:8520
python app/mcp_server.py         # the checks as MCP tools; an agent starts it from .mcp.json
```

The app works on one project at a time, picked in the left rail. Each project is a folder in `data/projects/` (not in Git): its packages, their original files and its BOQs. To share projects, point the app at a shared folder, for example on Google Drive: `python app/review_server.py --projects "<the shared folder>"`. With no project, the app shows P01 and P02 from `data/maf/extracted/`, which is in Git; their original PDFs and forms stay on our laptops in `data/raw/`.

The AI parts (a rule typed in words, what a BOQ line asks) use the Claude command line (`claude`) installed and signed in on the laptop.

## Where things are

| To see | Open |
|---|---|
| the feature in detail | [`spec/features/maf_checker.md`](spec/features/maf_checker.md) |
| the problem, scope and principles | [`spec/constitution/mission.md`](spec/constitution/mission.md) |
| milestones and who does what | [`spec/constitution/roadmap.md`](spec/constitution/roadmap.md) |
| tools and architecture | [`spec/constitution/tech_stack.md`](spec/constitution/tech_stack.md) |
| how to work in this repository | [`AGENTS.md`](AGENTS.md) |
| the problem broken into tasks | [`docs/problem_segmentation.md`](docs/problem_segmentation.md) |
| the data we have and need | [`docs/data_map.md`](docs/data_map.md) |
| what the old register tells us | [`docs/maf_register_findings.md`](docs/maf_register_findings.md) |
| the rules and where they come from | [`docs/maf_rules.md`](docs/maf_rules.md), [`docs/jurisdictions.md`](docs/jurisdictions.md) |
| decisions so far | [`docs/decisions.md`](docs/decisions.md) |

## A few rules

Nothing confidential goes into Git: no client, project, company or personal names, no prices, no original PDFs. Manufacturer names and model codes are fine. Every technical value needs a source, and when we can't find one the value stays `unclear`. Decisions go in `docs/decisions.md` so they don't get lost in chat.
