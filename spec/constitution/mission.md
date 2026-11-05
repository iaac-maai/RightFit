# Mission — RightFit

Draft for the MAF checker, 28 Oct 2026; the team agreed to it on 5 Nov 2026, and the full version is due on 12 Nov. Open questions are marked [O].

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
- Two packages make a demonstration, not an evaluation. [O] More packages from Luca's practice, anonymised.

Changes to this file are recorded in `docs/decisions.md`.
