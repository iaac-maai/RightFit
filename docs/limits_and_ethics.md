# Limits and ethics check

For the IAAC deliverable of 10 Dec 2026 (issue #17). Written on 27 Nov 2026 from what the repository records on that day; every point names the file it rests on. Draft until Luca has read and approved it.

It answers six questions: who uses RightFit, who carries the risk, who owns the data, where bias can come from, who is responsible, and what RightFit does not check. The points that the repository does not settle are in section 7, each with a proposed answer.

## In short

- RightFit drafts a review; a person signs it. Nothing in the product, the terms or the code moves the signer's responsibility to the tool (`mission.md` §9, `web/legal/terms.md` clause 5).
- The evidence is thin and comes from one place: 50 packages from one building project in Romania, a checklist from the register of one earlier project, and one reviewer, Luca, who also wrote the checklist, labels the data and judges the results (`mission.md` §9, `roadmap.md` §7).
- Almost nothing read by the AI has been confirmed yet: 1 of 116 values and 2 of 15 documents of P01 and P02 (`AGENTS.md`, current status). Every check result that rests on the rest is a "would be" result.
- On those unconfirmed readings the draft and the reviewer disagree widely. RightFit's own review, run on 27 Nov 2026 (the `review_package` tool of `app/mcp_server.py`), drafts B for P01 with 20 problems and 6 questions, and B for P02 with 4 problems and 12 questions. Check Q's share of them (7 problems for P01, 1 for P02, and every question) needs the project's BOQ, which is on the laptop only, so these counts cannot be repeated from Git alone. Luca would give both A and flag nothing (`data/maf/reference/`). The more likely harm today is a form sent back without need, not a bad product let through.
- The operator of RightFit online is not named yet, and its legal documents have not been read by a lawyer (`docs/legal/README.md`).

## 1. Who uses RightFit

| Who | What they do with it | Where | Evidence |
|---|---|---|---|
| The reviewer who signs the form: most often the consultant, also the site supervisor and the designer | reads the draft, confirms the readings, keeps or dismisses each finding, decides the answer | RightFit online | `mission.md` §2, `spec/features/maf_checker.md` §1 |
| The client | a member of the project, invited by the consultant; also signs the form | RightFit online | `mission.md` §1, `web/legal/terms.md` clause 4.2 |
| The contractor and its subcontractors | add packages, see the answer; can run the same check before sending | RightFit online | `mission.md` §2, `spec/features/rightfit_online.md` §4 |
| The architect or the MEP designer in Revit | checks a pump set in its room and tries its alternatives | Revit, linked to RightFit online | `spec/features/revit_fit_check.md`, `spec/features/revit_link.md` |
| The team that runs RightFit (Management) | sees every account and project, puts things right; every change is logged | RightFit online, Google sign-in only | `spec/features/rightfit_online.md` §9, `web/legal/terms.md` clause 16 |
| An AI agent | calls six read-only tools over MCP | the laptop | `app/mcp_server.py`, `tech_stack.md` §1 |
| People who answer the practice survey | give their own estimates of how the work goes today, anonymously | `/survey` | `spec/features/survey.md` §2 |

Manufacturers do not use RightFit, but their documents are what it judges (`mission.md` §2). The people named or signing inside the documents (makers' staff, the project's parties) never use it either, but their names and signatures pass through it (`web/legal/data-processing.md`, Annex I).

The terms limit the service to professionals of 18 or over, acting in their trade (`web/legal/terms.md` clause 3.1).

## 2. Who carries the risk

RightFit can go wrong in two directions, and each lands on someone different.

| Error | Who it hurts | What RightFit does about it | What is left |
|---|---|---|---|
| A **false pass**: a document or value is missing or wrong and RightFit says nothing | whoever relies on the equipment: the client, the people in the building; the families include drinking water pumps, fire dampers, fire detection and voice alarm equipment | a check passes only on values a person confirmed; anything else is `unclear`, with the result it would give (`mission.md` §5 rules 2 and 3); every result says what was and was not checked | the confirmation is only as careful as the person who clicks it; a reviewer who trusts the draft may stop reading what it passed |
| A **false flag**: RightFit asks for something that is not needed | the contractor, who waits and sends again (on the earlier project a form took a median of about 12 days to come back, `mission.md` §1); the client, who pays for the time; the manufacturer, whose product looks worse than it is | every finding names its rule and source, and the reviewer can dismiss it; the consultant's own rules show as the consultant's (`CR-`), not as the law (`app/mcp_server.py`) | on P01 and P02 the draft raised 24 problems where Luca raised none (see "In short"). Until the readings are confirmed and the comparison is repeated, we cannot say how many of them are real |
| A wrong legal statement: a rule out of date | the reviewer who cites it | each rule keeps its source, status and the dates it applies between; the rule watch asks the official source whether the act changed (`docs/jurisdictions.md`, `ingest/rule_watch.py`) | Romania's Law 10/1995 stopped applying on 25 Aug 2026, and we found out on 12 Nov (`mission.md` §7, `docs/jurisdictions.md`); how often the watch runs and who reads it is open |
| A leak of project data | the project's parties, and the people named in the documents | originals stay out of Git; the repository keeps values, quotes of at most 15 words and counts (`tech_stack.md` §4); the site checks membership and role on every request (`web/legal/data-processing.md`, Annex II) | the repository is public, so a name slipping into a commit is published at once; each commit is scanned against a local names list before it is pushed (`docs/workflow.md` §6) |

The person who signs carries the professional risk. The terms exclude the provider's liability for "a decision taken, a form signed, a product ordered or a design approved on the basis of Output" and cap the rest at 100 euros while the service is free, except what the law does not allow to be excluded, such as gross negligence, fraud, death or personal injury (`web/legal/terms.md` clauses 12.1 to 12.3). That is fair only as long as RightFit is honest about what it did not check (section 6), labels every AI output as AI, and never says "compliant".

## 3. Who owns the data

| Data | Owner | Where it is | Who can see it | Evidence |
|---|---|---|---|---|
| The packages: forms and attached documents | the project's parties; the documents' content is the manufacturers' | the laptop (`data/raw/`, `data/projects/`, git-ignored) and the project's private storage online since 20 Nov 2026, because the parties agreed to it | the members of that project, and Management; the team's own project also needs the team password | `mission.md` §9, `spec/features/rightfit_online.md` §9 and §11 |
| The register of 80 past forms | the earlier project's parties; Luca keeps an anonymised copy | the laptop only | the team, as counts in `docs/maf_register_findings.md` | `mission.md` §1 |
| The project's BOQ | the project's parties | the laptop; online without prices | members of the project | `tech_stack.md` §2, `AGENTS.md` |
| The readings: values with file, page and a short quote | follow the package they come from | `data/maf/extracted/` (public, no names) and the project online | anyone for the two public packages; members for the rest | `tech_stack.md` §4 |
| Luca's reference answers | Luca | `data/maf/reference/` | public | `data/maf/reference/` |
| The record of products that come back across a consultant's projects | the consultant's organisation, which instructs it | RightFit online | the consultant's own people in its other projects; never a contractor or subcontractor of another project; a document never leaves its project | `web/legal/data-processing.md` clause 1.4, `spec/features/knowledge_graph.md` |
| Our two trained models | the team | a private repository on Hugging Face, because the words they learned can carry names from the forms | the team | `README.md`, `spec/features/rightfit_online.md` §3 |
| Accounts, roles, invitations, the activity log | the operator, as controller | RightFit online (Cloudflare D1) | the person, the members their role allows, Management | `web/legal/privacy.md`, `docs/legal/records_of_processing.md` |
| Survey answers | the team | RightFit online; only the day, the version and the answers | sums for anyone signed in; comments for admins | `spec/features/survey.md` §2 |

Where the data travels to an AI model, and when it was agreed:

- The AI reader on Luca's laptop sends the pages of a package to its provider. P01 and P02 were read that way, and on 27 Nov 2026 Luca agreed that the remaining packages may be sent too; the 25 test set packages of the second batch were read the same day (`mission.md` §9, `docs/decisions.md`, 27 Nov 2026).
- The laptop app asks an online model two small things: to turn a rule the consultant types into a row, and to list what a BOQ line asks for, from the line's description alone. Prices are never read (`mission.md` §9, `app/ai.py`).
- RightFit online itself calls no AI model: its Worker talks only to its own checks engine and to Google for sign-in (`web/worker/`, `web/engine/`).

The terms promise that customer content is not used to train AI models (`web/legal/terms.md` clause 6.2). The second version of our page classifier, built on 11 Nov 2026, was trained on 117 documents of the second batch's real packages (50 more were held back as its locked test), from their copies on the laptop (`eval/page_classifier/results_2026-11-11.md`). These are the same packages that may now be kept online, so where the copy came from does not settle it: the repository does not record that the parties' agreement covers training. Section 7 asks Luca.

## 4. Where bias can come from

| Source | Why it matters | What we do | What is left | Evidence |
|---|---|---|---|---|
| All 50 packages come from one project, and the checklist from the register of one earlier project, both in Romania | a comment that was common there may be rare elsewhere; a maker common there is over-represented in training | we say so with every result; the checklist is never tested on the register it came from | packages from other projects need the owning company's permission [O] | `mission.md` §6 and §9, `roadmap.md` §7 |
| One reviewer writes the checklist, approves the rules, labels the data, writes the reference answers and judges the results | his habits become the tool's, and he grades his own work | reference answers written before the tool's output is seen, and never used for tuning; the chatbot test will have him judge findings with the source hidden | that test has not run yet, so no finding has been judged blind so far; no second reviewer yet [O] | `mission.md` §5 rule 7, `eval/chatbot_baseline/protocol.md` |
| The register is of returns that happened, not of returns that should have happened | the checklist learns what one team chose to write down | each checklist item names the register rows it comes from (for example CL-08: R59, R52) | the causes of the 22 returns are a first reading, still to be confirmed by Luca | `data/maf/checklist.csv`, `docs/maf_register_findings.md` |
| Training data of our models: public documents of a few large manufacturers and two certification schemes, and real packages of one project | a small maker's data sheet that looks different may be classified worse | each model is scored once on a locked set against the plain way (keywords, family words), and we keep the result whichever way it goes | not measured by maker; 32 of the family model's 37 locked rows are "other", and the family words beat it (35 against 28) | `eval/page_classifier/training_sources.csv`, `eval/family_classifier/results_2026-11-17.md` |
| Scanned pages without a text layer (34 of the 300 PDFs we hold) | they are read from the page image, so a maker who sends scans may get more `unclear` results | they are marked for a closer look | not measured | `mission.md` §7 and §8 |
| Methods tuned on the cases they are shown on | the BOQ matching was designed on its 24 cases, the revision comparison's thresholds on its only pair | each result says so ("not a test yet") | a test on unseen cases | `eval/boq_matching/`, `eval/revisions/results_2026-11-17.md` |
| The consultant's own rules | a consultant can write a preference, such as a brand list, into a check | they are labelled as the consultant's (`CR-`), never as the law | a preference of the client can be legitimate (P02 was turned down at revisions 0 to 3 over the brand), so RightFit shows it rather than judges it | `data/maf/consultant_rules.csv`, `mission.md` §1 |
| The draft itself (automation bias) | a long draft may be sent as it is, and a short one may stop the reviewer reading | nothing passes before a person confirms its readings; each result says what was checked and what was not | the time comparison (3 Dec) measures Luca's time checking the draft, not whether he read less | `mission.md` §5 and §6 |
| Survey answers | the people who answer chose to; they are estimates | shown as "as reported by N people", never as a measurement or a saving | who answered depends on who got the link | `spec/features/survey.md` §1 and §4 |

## 5. Who is responsible

| For what | Who | Evidence |
|---|---|---|
| The answer on the form and the signature | the reviewer who signs; RightFit never certifies | `mission.md` §9, `web/legal/terms.md` clauses 5.1 and 5.3 |
| That a package may be put into a project and shared with its members | the member who uploads it, and the customer organisation | `web/legal/terms.md` clause 6.3, `web/legal/data-processing.md` clause 2.4 |
| Running the service, keeping data safe, telling customers of a breach within 48 hours | the operator, **not yet named**: Luca, the team, or IAAC with its agreement; commercial use needs IAAC's written agreement | `docs/legal/README.md`, `web/legal/data-processing.md` clause 8 |
| Each engineering rule in `checks/` and each rule's status | Luca approves them; a legal rule is `verified_official` only once read on the official text; the fit check's rules were approved on 26 Nov 2026 | `AGENTS.md`, `data/maf/rules.csv`, `data/space/rules.csv` |
| Each confirmed reading | the person who confirmed it, recorded with the date (`checked_by`) | `tech_stack.md` §4 |
| Each part of the software | the person who owns it (integration and validation: Sahil; the fit check: Jeff; rules and verification: Luca) | `AGENTS.md`, team and ownership |
| Whether the legal documents hold | a lawyer qualified in Spanish and EU data protection law, before anyone outside the team signs up; they are drafts until then | `docs/legal/README.md` |

Two legal classifications are the team's own reading and have not been checked by a lawyer: that RightFit is not meant for any high-risk use under the AI Act (`web/legal/terms.md` clause 5.4), and that no data protection impact assessment is needed for now (`docs/legal/dpia_screening.md`, which lists when to look again).

## 6. What RightFit does not check

What it checks is in `spec/features/maf_checker.md` §6 (D1 to D4, V1 to V3, E1, H1, C, P, Q, R). It does not check:

1. **The installation.** It checks what the documents say; a correct data sheet does not mean a correct installation (`mission.md` §7).
2. **Values the manufacturer does not publish.** They stay missing, and RightFit asks for them (`mission.md` §7).
3. **The returns no document check can catch.** On the earlier project's register, 9 of the 22 returns were coordination with the architecture (4), a design not approved yet (3), a sample asked for (1) and a site condition (1); 5 more are caught only if the requirement is written down. About a third of the returns are caught for sure, and at best six in ten (`docs/maf_register_findings.md`).
4. **What the client wants but nobody wrote down,** such as the brand list that turned P02 down at revisions 0 to 3 (`mission.md` §1).
5. **Whether a document is genuine.** No check asks the issuing body whether a certificate or a declaration is real; D2 checks that a declaration names the product, D3 that a document is in date.
6. **The families without rules:** valves, tanks and heat exchangers (waiting on the pressure equipment rules), pipes and meters, doors; and in the second batch, the electrical declaration of fire detection equipment, cable trays and conduits, fire resistant cables and door hardware (`mission.md` §4, `spec/features/maf_checker.md` §12).
7. **Green certification values** (LEED, BREEAM, VERDE): not in any family's checklist yet [O] (`mission.md` §4).
8. **Laws other than the EU's, Romania's and Spain's,** and a change in the law after a rule was last read: the rule watch only reports, and a person reads the act again. From 20 Jan 2027 a machinery declaration may be only a link in the instructions; D1 does not look for one yet (`spec/features/maf_checker.md` §12).
9. **Whether equipment fits its room,** except a pump set in Revit with the fit check's rules (`mission.md` §4, `spec/features/revit_fit_check.md`).
10. **Prices and commercial terms.** Prices are never read (`mission.md` §9).
11. **Its own AI readings.** How well the AI reads a package is not measured yet: 1 of 116 values confirmed (`mission.md` §8). The AI suggestions and the page classifier are hints, labelled as AI, never checks (`mission.md` §5 rule 4, `tech_stack.md` §3).

## 7. Open points for Luca

Each with a proposed answer.

1. **Training on real packages.** Does the parties' agreement recorded in `mission.md` §9 cover training our own models on these packages, as the page classifier was on 11 Nov? *Proposed:* ask the parties, and if they agree, record it in `mission.md` §9 and `docs/decisions.md` and name it in clause 6.2 of the terms as the one exception, for the team's own models kept private (a change to `web/legal/`, so it waits for Luca). If they do not, train the model again without those packages.
2. **The AI reader's provider.** The pages it reads go to an online provider, which is not in the sub-processors of the data processing agreement, because the reading happens on the laptop and not in the service. *Proposed:* record it in `docs/legal/records_of_processing.md`, with the provider's own terms on keeping and training on what it receives; when reading moves online, add the provider to Annex III (a change to `web/legal/`, so it waits for Luca).
3. **The chatbot test** (issue #12) sends packages to two general chatbots. *Proposed:* the answer of 27 Nov covers it, in the chats that keep no memory that the protocol asks for; record it in issue #12.
4. **Who may use RightFit online until the operator is named and a lawyer has read the documents.** *Proposed:* the team and the test users it invites, and nobody else; say so in the 10 Dec deliverable.
5. **A second reviewer.** *Proposed:* a practitioner outside the team judges the findings of the 5 timed packages with the source hidden, as the chatbot protocol does.

## 8. When to look at this again

- when Luca has confirmed the readings of P01 and P02, and when the comparison on unseen packages (3 Dec) is done: sections 2 and 4 get the new numbers, good or bad;
- when a package from another project, or a second reviewer, comes in: section 4;
- when the operator is named or a lawyer has read the documents: section 5;
- when reading packages moves online, or the AI starts to read names or signatures: sections 3 and 5, and the impact assessment screening (`docs/legal/dpia_screening.md`);
- when anyone outside the team signs up.
