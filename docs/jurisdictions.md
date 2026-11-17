# Rules by project location

The check engine is the same in every country. What changes with the project's location is the set of rules it reads. Product data does not change, and the EU product rules are the same in every member state.

## Layers
A project collects its rules from layers, from the most general to the most specific:
1. EU: product rules (declarations of conformity, construction products, ecodesign). Same for every EU country.
2. Country: national rules (Romania: Law 10/1995 until 24 Aug 2026, then the construction Code, Law 169/2026; Order 275/2012 and I9-2022 for water; the site supervisor's practice. Spain: CTE and RITE; RD 487/2022 and RD 3/2023 for water).
3. Region and city, where they exist (Catalonia, Barcelona). None is needed for the MAF checks in v0.1.
4. Project, the most specific layer: the BOQ (check Q), the consultant's own rules (check P) and the pressure and water temperatures the reviewer types in. The written specification is not read yet.

Ids follow ISO 3166: EU, RO, ES, ES-CT (Catalonia), ES-CT-BCN (Barcelona). Practice and engineer inputs use ANY, or the country when the practice is national (RO-PRACTICE-DELIVERY).

## One rule, one row (data/maf/rules.csv)
rule_id, jurisdiction, topic, check, code, clause, requirement, param, operator, value, unit, applies_to, valid_from, valid_to, quote, source_url, status, verified_on, notes.
- topic groups the rules that answer the same question, whatever the country: doc.eu_declaration_of_conformity, doc.reception_control, ahu.hrs_efficiency;
- applies_to: the product families (pump, ahu, outdoor_unit, dx_kit, fire_damper and the others named in data/maf/family_documents.csv) or all;
- valid_from and valid_to: the window in which that version applies; the project date picks the version (the Machinery Directive until 19 Jan 2027, the Machinery Regulation from 20 Jan 2027; in Romania Law 10/1995 until 24 Aug 2026, the construction Code from 25 Aug 2026);
- status: verified_official (read on the official text), verified_secondary (read in a copy), to_confirm, practice (from past reviewers), engineer_input.

## How the engine resolves the rules for a project
1. Build the location chain: RO gives EU, RO, ANY; ES-CT-BCN gives EU, ES, ES-CT, ES-CT-BCN, ANY.
2. Keep the rules of that chain whose applies_to includes the item's family and whose dates cover the project date.
3. Inside one topic every rule applies at once; for limits the strictest value wins. The result lists every rule that took part, not only the winner.
4. A topic with no rule in the chain makes its check Unclear, with the note "no rule for this location". Never borrow a rule from another country.
5. The status travels with the rule: to_confirm, practice and engineer_input are shown next to the verdict.

## Adding a country
1. The topics are the same for every country, because the checks are the same. That gives the list of questions to answer.
2. For each topic, find the national rule. The AI does the first pass: it reads the official texts and proposes a row with clause and quote. An engineer who works under that code checks it against the official text before its status becomes verified_official. This is where the human in the loop sits.
3. Topics with no national rule stay empty and their checks show Unclear.
4. A few packages from that country with known answers test the pack before anyone uses it.

## Keeping the rules current
Each row keeps its source and the date it was last checked (verified_on). On 16 Nov 2026 every legal rule was read again by hand on its official source. Since 17 Nov the rule watch (`python3 -m ingest.rule_watch`, or the MCP tool `watch_rules`; roadmap MAF-10) asks each source when the act last changed: the Publications Office gives an EU act's consolidated versions and its end of validity, the BOE open data service the date a consolidated text was last updated and any repeal, and legislatie.just.ro the consolidated forms of a Romanian act. The rows of harmonised standards are watched through Implementing Decision (EU) 2019/451, which cites, replaces and withdraws them. A version dated after verified_on, or an end of validity the row does not have, comes back as a change with its date. The watch never changes a row or its status: Luca reads the act again and decides. It runs by hand for now; no schedule is set.

## In the MAF checker
Locations RO (the packages are Romanian) and ES (the provisional testing context of the constitution; ES-CT-BCN behaves as ES for the MAF checks). The same package runs under both, and the page shows which rules change.
