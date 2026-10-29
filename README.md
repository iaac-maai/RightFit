# RightFit

RightFit helps the person who signs a material approval form (MAF) for MEP equipment, most often the consultant, check it before signing. It reads the documents attached to the form, checks them against EU and national rules and against a checklist we built from past reviewers' comments, and drafts the answer with a page reference for every finding. The reviewer still decides and signs.

IAAC MaAI01 · Operable Futures · 2026–27 · Sahil Khan, Jeff El Khoury, Luca Obejdeanu

This is the `maf-checker` branch. It is Luca's proposal to move the project from choosing kitchen hoods to reviewing MAFs, and Sahil and Jeff have not agreed to it yet. `main` still has the hood version.

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
pytest
python app/review_server.py      # the PoC review page: http://127.0.0.1:8520
streamlit run app/maf_app.py     # the first review page, in Streamlit
```

The app works from `data/maf/extracted/`, which is in Git. The original PDFs and forms stay on our laptops in `data/raw/`.

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
