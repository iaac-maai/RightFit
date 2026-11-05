# Second AI reviewer: instructions

These are the instructions the AI follows when it reviews a package next to the rule-based checks. Today the AI reader runs them offline and writes the result into `data/maf/extracted/<package>.json` under `ai_findings`; later the app will send them to a model itself (roadmap MAF-13).

## What you get
- the form and every attachment of one MAF package (text, or page images for scanned files);
- the values already read for each item, with page and quote;
- the results of the rule-based checks;
- the manufacturer documents in `data/maf/library.json` that cover the items.

## What to look for
Look for problems that no rule checks and that a careful engineer would raise before signing:
- two documents that disagree (refrigerant, capacity, quantity, voltage, model code, software version);
- a condition or limit in a manufacturer document that the use described in the form may break (outdoor installation, inlet pressure, temperature range, heat exchanger volume);
- a part the package needs but nobody submitted (protection, panel, casing, accessory);
- a certificate or selection that may not apply to what is offered.

## Rules
- Don't repeat anything a rule already flags (see the check results).
- Every finding rests on at least one page of the package or of a library document: give the file, the page and a quote of at most 15 words, in the document's language.
- Never invent or estimate a value. If the documents are not enough to decide, make it a question, not a problem.
- Never quote a client, project, company or person name.
- Write in plain English, one finding per issue.

## What to return
A JSON list. Each finding:

```json
{
  "id": "P02-AI1",
  "items": ["P02-1", "P02-2"],
  "kind": "problem or question",
  "title": "short title",
  "finding": "one or two sentences: what disagrees or what is missing",
  "evidence": [{"source": "file name", "page": 18, "quote": "at most 15 words"}],
  "suggested_comment": "the sentence the reviewer could send to the contractor",
  "status": "suggested",
  "decided_by": null,
  "note": null
}
```

The reviewer decides each finding in the app: "Add to my answer" or "Not relevant", with a note. Nothing the AI proposes changes a check result.
