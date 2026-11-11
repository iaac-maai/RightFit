# Mission — RightFit

Full version for 12 Nov 2026, built on the MAF direction the team agreed on 5 Nov 2026. Open questions are marked [O].

## 1. Problem

Before MEP equipment is ordered, the contractor sends a material approval form (MAF; in Romania, "fișă pentru transmitere și aprobare materiale") with the data sheets, declarations and certificates behind it. Several people sign the same form: the site supervisor, the designer, one or two consultants, the client. Each of them opens the same PDFs, often in three or four languages, and looks for much the same things. Is this the model on the form? Does the declaration name it? Is the certificate still valid? Does the pump reach the duty point?

If something is missing, the form goes back and comes in again. Luca keeps the register of the last project he worked on (80 MEP forms, anonymised, outside Git; details in `docs/maf_register_findings.md`):

- 66 forms got an answer: 44 approved, 17 approved with notes, 5 sent back for resubmission. 14 have no status.
- 17 forms needed at least one revision, and one of them needed six.
- A form usually came back after about 12 days (median). Once the last reviewer had answered, it still waited a median of 7 days before it went back to the contractor.
- 8 of the 22 returns were gaps in the package: a data sheet for a whole range with nothing marked, a technical approval past its date, pump panels without the BMS module.

The second package in the prototype, an air handling unit with outdoor units, is at revision 4. Revisions 0 to 3 weren't turned down for anything technical: the client wanted FläktGroup and accepted only its own house brands. No document check would have caught that, unless the client's brand list had been written down as a requirement.

The hood version quoted "16 of 79 forms sent back" from the v1 research. We now use the register, which is the copy we can actually open: 22 returns out of 80.

The contractor waits, sends again and sometimes orders late. Reviewers read the same documents again at each revision. The client pays for the time.

## 2. Users

The main user is whoever signs the MAF, and most of the time that is the consultant. Site supervisors and designers sign too. A contractor can run the same check before sending, to catch the obvious gaps first.

Manufacturers don't use the tool, but the result depends on how clear their documents are. When a value is missing from them, RightFit says so and asks for it.

[O] Who would pay for this. For now it is only a question; we would need to talk to reviewers and contractors.

## 3. In one line

AI reads, rules decide, a person signs.

## 4. Scope

The prototype covers MEP equipment at the MAF stage of Design & Pre-Construction, after the design is done and before anything is ordered. We start with pumps and air handling units (with their outdoor units and DX kits), because those are the two complete packages we hold.

It runs for Romania, where the packages come from, and for Spain, the provisional testing context of the course. EU product rules are the same for both. Luca checks which national rules apply; until a rule is verified on the official text, nothing in RightFit is presented as regulatory compliance, and every rule shows its status next to the result.

Out of scope: choosing products, visual search, finishes, checking whether equipment physically fits in the room, and approving anything on the reviewer's behalf.

[O] Doors. Luca would like them in, but they are on hold since 29 Oct until we know how.

[O] The next families. Fire dampers and valves would bring in the construction products regulation; pipes and meters are frequent in the register.

[O] Which LEED, BREEAM or VERDE values belong in each family's checklist (Sahil or Jeff).

## 5. Principles

These apply to every spec, line of code, test and presentation.

1. We don't invent data. No value, result or legal statement comes from "typical" figures or from memory.
2. Every value keeps its source file, page and status: `extracted` (read by the AI and not checked), `verified` (checked by one of us) or `unclear` (missing or ambiguous).
3. A check passes or flags only on verified values. Anything else shows as `unclear`, together with the result it would give.
4. AI and engineering stay apart. The AI reads documents; the checks in `checks/` are plain Python with no model, and no model can change their result. Anything predictive is labelled as a prediction and never shown as a check.
5. Comments are filled in from templates with checked values. A language model may rephrase them but never add a value.
6. The reviewer decides and signs. Every result says what was checked and what wasn't.
7. Reference answers are written before anyone sees the tool's output, and they are never used to tune it. We report every result, including the bad ones.
8. No client, project, company or personal names, no prices and no original documents in Git. Manufacturer names and model codes are fine.
9. Small tested steps, few dependencies.
10. Decisions go in `docs/decisions.md`. The principles change only if all three of us agree.

## 6. How we will know it works

For each package Luca first writes his own review: what he would flag, the status he would give, and how long it took. Then we run the tool and count three things: what both found, what only the tool found (and whether it was real), and what the tool missed. We also compare the draft status with his, and his time by hand with his time checking the tool's draft.

We don't set targets before we have these first numbers. If the draft doesn't save Luca time on new packages, or misses things he thinks matter, we will say so and change course.

The checklist comes from the register's comments, so we never evaluate it on the register; that would only show it can repeat itself. A first reading of the register suggests the checks could have caught 8 of the 22 returns for certain, and up to 13 if the specification states every value.

## 7. Known limits

- RightFit checks what the documents say. A correct data sheet doesn't mean a correct installation.
- A value the manufacturer doesn't publish stays missing.
- Scanned PDFs without a text layer are read from the page image and need a closer look.
- Some returns no check can catch: coordination with the architecture, a design that isn't approved yet, a reviewer asking for a sample.
- A rule is only as current as its last check, so each one keeps its source and the date it was checked.
- Two packages make a demonstration, not an evaluation. 48 more packages from the same project are on the laptop and not read yet. [O] Packages from other projects.

## 8. Why AI, and why not a general chatbot

Reading is the part rules can't do. The packages come from dozens of manufacturers, in several languages, and no two data sheets look alike. The 50 packages we hold have about 1,400 PDF pages, and 34 of the 300 PDFs have no text layer at all. On the pages of the two packages we have tested, a keyword search named the right kind of document only 27 % of the time.

Deciding is the part AI has to stay out of. The person who signs must be able to defend each comment, so the same package has to give the same result every time and each result has to name its rule. That is why the checks are plain Python.

Every AI part is measured against the plain way of doing the same job, and the results stay in the repository whichever way they go.

| AI part | Compared with | Result so far |
|---|---|---|
| Our page classifier, trained from scratch | Keyword search | First version, on real package pages: 25 % right against 27 %. On manuals with declarations inside: 87 % against 45 %. It didn't beat the keywords on real packages. The second version also trains on real packages: on 184 locked pages of the second batch it gets 62 % right against 35 %, and finds 69 % of the data sheet pages against 9 % |
| AI matching of documents to products | Text matching | The same answer on all 51 pairs. So far the AI only adds how a document covers a product |
| AI reading of packages into values | A person reading them | Not measured yet: 1 of 116 values has been confirmed |
| The whole review | Luca by hand, and general chatbots | By hand: about 10 minutes for P01 (figures only) and 3 hours for P02. Chatbots: the protocol is written (`eval/chatbot_baseline/protocol.md`), no run yet |

At the midterm on 6 Nov the jury's main comment was that RightFit has to differ clearly from any general AI chatbot. A chatbot can read a PDF and give an opinion. RightFit differs in how the result is built:

- the same package gets the same result on every run, and the protocol above measures how much a chatbot's runs differ;
- every result names its rule, the rule's source and whether anyone has read the official text;
- nothing passes until a person has confirmed the reading behind it, and the confirmation records who and when;
- each finding opens next to the real page, with the quoted line marked where the page has a text layer;
- the checklist comes from what reviewers wrote on 80 real forms, which a chatbot has not seen;
- an agent can call the checks through MCP, so a chatbot can use RightFit's rules instead of replacing them.

If the chatbots find as much as RightFit at the same quality, we will say so and change course.

## 9. Responsibility and data

The person who signs the form carries the responsibility, and RightFit doesn't take any of it away. It drafts, says what it checked and what it couldn't, and never certifies.

The packages, the forms and the register belong to the project's parties. The originals stay on our laptops, outside Git, and the repository keeps only values, short quotes and counts. Anything we get from other practitioners needs the permission of the company that owns it. [O] Whether real packages may be sent to an online model: the manufacturer documents are public, the forms and the project headers on some pages are not.

All 50 packages come from one project, and the checklist comes from a register Luca kept. He is also the one who judges the results, so a comment that was common there may be rare elsewhere. We reduce this by writing the reference answers before seeing the tool's output and by hiding the source when findings are judged. [O] A second reviewer, and packages from other projects.

Changes to this file are recorded in `docs/decisions.md`.
