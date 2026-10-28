# MAF register findings (earlier project, anonymised)

The register itself stays outside Git, as docs/data_map.md says for the approval forms. This file keeps only counts and short anonymised examples. Row ids (R01 to R80) refer to Luca's local anonymised copy, where client, consultants and contractor are replaced by roles and brands by [brand].

## Numbers
- 80 MAFs, all MEP; 66 answered: A 44, B 17, C 5; 14 without a status;
- 17 MAFs needed at least one revision; the most, six (DHW storage tanks);
- sending to answer: median 12 days counting from the form date when the sending date is missing (69 MAFs), 13.5 days with the sending date only (68 MAFs); longest 163 days;
- four reviewer columns: site supervisor (17 answers, median 4 days), designer (19, median 1), consultant 1 (49, median 3), consultant 2 (13, median 7); consultant 1 answered last most often (37 times);
- median 7 days between the last reviewer's answer and the return to the contractor (54 MAFs): the wait is in routing and consolidation, not in reading;
- 31 MAFs carry a comment; six carry the site supervisor's standard reminder about delivery documents, and three of those were still approved.

## The 22 returns (B and C) by cause
A first reading; Luca confirms or corrects it.

| Cause | Count | Rows | Example | Catchable by a check |
|---|---|---|---|---|
| incomplete package | 8 | R01, R04, R09, R11, R31, R59, R66, R68 | a data sheet for a whole range with nothing marked; a technical approval past its date; pump control panels without the BMS module | yes |
| technical condition | 4 | R06, R07, R22, R76 | PP drainage pipe "not sound isolated" for horizontal runs in apartments | partly, if the requirement is stated |
| coordination with architecture | 4 | R05, R08, R50, R51 | hydrant cabinet approved only together with the lobby glass door detail | no |
| coordination with the BMS | 1 | R52 | meters must be compatible with the BMS | partly |
| MEP design not approved yet | 3 | R49, R55, R57 | no approved MEP design, so the status may change | no |
| sample requested | 1 | R56 | a reviewer asks for a sample | no |
| site condition | 1 | R30 | installation manuals must be respected | no |

So a check catches about a third of the returns for sure, and at best six in ten if the specification states every value.

The checklist in data/maf/checklist.csv comes from these comments, so testing it on this register would be circular. It is tested on new packages (P01, P02).

## Open with Luca
- confirm the causes above;
- why P02 (form IV 004) needed four revisions, and what the reviewers said on revisions 0 to 3;
- the status P01 (form IS 015, revision 0) received, and the comments;
- which roles sit behind consultant 1 and consultant 2.
