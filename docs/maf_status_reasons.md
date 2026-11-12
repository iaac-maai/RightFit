# Why a MAF gets A, B or C

The tool proposes a status; the reviewer decides. These are the written rules behind the proposal (spec section 7), and every reason that can move a package away from A. Luca confirms or changes them.

- C, revise and resubmit: a product has no data sheet that names it, or a checklist item marked as blocking is missing.
- B, approved as noted: no reason for C, but at least one problem or one open question.
- A, approved: every check passed or is only for information.
- "Not approved" and "Sample requested" are never proposed. Only the reviewer chooses them.

Every reason below stays in the draft until the reviewer marks it as not a problem, with a note, on the review page.

## Reasons for C

| Reason | Check | Why it sends the package back | What the contractor does |
|---|---|---|---|
| No data sheet names the submitted model | D1 | Without it the reviewer can't check the product at all. In the register a data sheet for a whole range, with nothing marked, was returned (R01). | Send the data sheet of the exact model, or mark it in the range table |
| A blocking checklist item is missing | C | The checklist marks two items as blocking, both from returns in the register: fixed points for vertical and horizontal pipe runs (CL-06, R11, R12) and the defrost design for heated roof drains (CL-07, R68). Neither applies to pumps or AHUs. | Add the missing design or detail |

## Reasons for B

| Reason | Check | Why it counts | What the contractor does |
|---|---|---|---|
| No EU declaration of conformity names the product | D1 | Machinery comes with a declaration that names it: Directive 2006/42/EC, replaced by Regulation (EU) 2023/1230 from 20 Jan 2027, and the Low Voltage Directive 2014/35/EU. Both rules are still "to confirm" on EUR-Lex. It is B, not C, because in the register forms without declarations were approved with a reminder for delivery (three of them). It stays B until the reviewer approves it by hand. | Attach the declaration, or make sure it comes with the delivery |
| The data sheet covers only the range; the model isn't marked | C, CL-01 | A data sheet for a whole range with nothing marked was returned in the register (R01). It counts as a data sheet, so it isn't C. | Mark the offered model on the data sheet |
| A declaration names none of the submitted products | D2 | Same rules. A declaration for other products doesn't cover these ones; P01's SL1/SLV declaration is an example. | Replace it with the declaration for the submitted models |
| A certificate has expired, or expires before delivery | D3 | Checklist CL-02; a technical approval past its date was returned in the register (R04). | Send the current version, or the renewed one at delivery |
| An attachment isn't what the form says | D4 | The form has to describe the package. P02 lists "TUV CTA" as the AHU's certificate, but the file certifies the selection software. | Correct the form or attach the announced document |
| The duty point on the data sheet is below the form | V1 | No tolerance: the designer already built the margins into the duty, and the site orders what the design states (Luca, ENG-DUTY-TOL). | Select a product that meets the duty |
| The pressure rating is below the requirement | V2 | Checklist CL-05, from R10. Only runs when the project gives a required pressure. | Select a product with a higher rating |
| The liquid temperature range doesn't cover the project's | V3 | Asked for by a practising MEP consultant (`ANY-PRACTICE-LIQUID-TEMP`). Runs when the project gives the water temperature, and for hot water pumps against the law: 60 °C in Romania (I9-2022 art. 23.7), 70 °C in Spain (RD 487/2022). | Select a pump for that temperature |
| No approval for contact with drinking water | H1 | Booster sets and hot water pumps carry drinking water (Luca). Romania: a sanitary approval or notification from the INSP commission, Order 275/2012. Spain: the manufacturer's declaración responsable, RD 3/2023. EU: from 31 Dec 2026 an EU declaration of conformity, Regulation (EU) 2024/370 art. 2(5). | Attach the approval, or the EU declaration from 31 Dec 2026 |
| An ecodesign limit isn't met | E1 | Regulation (EU) 1253/2014, Annex III, for ventilation units: heat recovery at least 73 % (68 % for run around coils), SFPint at most its limit, a filter warning. Read on a secondary source so far. [O] Luca: should this be C, since such a unit may not be sold in the EU? | Select a compliant unit or correct the data sheet |
| BMS communication not stated as included | C, CL-08 | Pump panels without the BMS module were returned in the register (R59), and meters had to be compatible with the BMS (R52). | Confirm that the module is in the supply, not optional |
| A rule of the consultant's own isn't met (for example no control panel, or another brand) | P | Not the law: preferences the consultant adds on the Rules screen, each with its effect (B, C or information). The control panel rule (CR-01 to CR-03) is Luca's of 28 Oct 2026; on 12 Nov he said it is a consultants' preference, not in any normative. | Meet the preference, or answer why not |
| Electrical data missing (voltage, power, starting method) | C, CL-12 | A reviewer asked for the starting method of jet fans (R34). | Complete the electrical data |
| The form doesn't say where the product is used | C, CL-03 | R09; the reviewer also asked for the designer's written opinion. | Fill in "A se folosi la" |
| Not every component of the BOQ line is submitted | C, CL-04 | R31, R66. With no BOQ line given, this stays an open question. | Confirm that the accessories are included |
| The BOQ line asks for something the submittal doesn't show | Q | The project's BOQ line for the product (found by the form's BOQ code and the duty, or the positions the form names). An AI lists what the line asks, with the exact words; each is checked like a consultant's rule. Unconfirmed until the reviewer looks, like any AI reading. | Show it in the submittal, or explain why not |
| A value the AI read isn't confirmed yet | any | A check can't pass on a value nobody has checked (principle 3). | Nothing; the reviewer confirms the reading |
| A value isn't in the documents | any | The tool never guesses a missing value. | Send the value, or the document that has it |
| An AI suggestion you added to your answer | AI | The second AI reviewer only proposes; once you add a suggestion it is your note, so the package can't be A. | Answer the comment |

## Information only, no effect on the status

- What the location asks for at delivery (R): in Romania the declaration of performance or conformity, the quality certificate and the guarantee; in Spain the reception documents of CTE Part I art. 7.2 and, for thermal installations, RITE art. 20.
- A declaration without an expiry date (D3).
- A document in the package that the form doesn't list (D4).
- A booster set without a control panel (consultant's rule CR-03).
- The pressure rating when the project gives no requirement (V2).
- The liquid temperature range when the project gives no temperature (V3).

## What no check looks at

Coordination with the architecture, whether the MEP design is approved, a sample request, the client's brand preferences (the reason P02 went through four revisions), and whether the equipment fits on site.
