# ingest: reading the documents

Turning files into data the checks can use. All of it is plain Python, except `prompts/`, which holds what the AI is told.

| File | What it reads |
|---|---|
| `maf_form.py` | the MAF form (.xls): number, revision, products, requirements, attachments |
| `boq.py` | a bill of quantities (Excel), and the line each product answers; the prices are never read |
| `revisions.py` | what changed between two revisions of a form |
| `rule_watch.py` | whether the act behind a rule changed, asked of the official sources of the EU, Spain and Romania |
| `prompts/` | the instructions given to the AI: matching documents to products, a second review, a rule typed in words, what a BOQ line asks |
