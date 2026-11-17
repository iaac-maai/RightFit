# data: the tables and the readings

What the checks read, and what the AI read from the two example packages.

| Path | What it is |
|---|---|
| `maf/rules.csv` | every rule: country, clause, a short quote, source, status (read on the official text or not) and the dates it applies between |
| `maf/checklist.csv` | the reviewers' checklist, built from the comments on 80 past forms |
| `maf/family_documents.csv` | which documents each product family needs, in each country |
| `maf/consultant_rules.csv` | the consultant's own rules, added on the Rules screen |
| `maf/library.json` | documents found on the makers' own websites |
| `maf/packages.csv` | the files of P01 and P02: pages, text layer, language |
| `maf/extracted/` | what the AI read from P01 and P02, value by value, each with its file, page, quote and status |
| `maf/reference/` | Luca's own review of P01 and P02, written before he saw RightFit's |
| `space/rules.csv` | the rules of the fit check in Revit |

Two folders stay on the laptops and never go into this public repository, because they hold names and prices: `raw/` (the original forms and PDFs, the BOQs, the trained models) and `projects/` (one folder per project).
