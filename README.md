# RightFit

RightFit checks a material approval form (MAF) for MEP equipment before the consultant signs it. It reads the documents attached to the form and checks them against the law in force, the project's bill of quantities (BOQ), a checklist built from past reviewers' comments and the consultant's own rules. Then it drafts the answer, with the page behind every finding. The reviewer decides and signs.

AI reads, rules decide, a person signs.

IAAC MaAI01 · Operable Futures · 2026–27 · Sahil Khan, Jeff El Khoury, Luca Obejdeanu

![RightFit at work: a material approval form and its PDFs come in, a violet line reads the data sheet and marks the product number, the duty point and the BMS module, the findings appear one by one with their page, a red B stamp lands, approved as noted, and a person signs](docs/images/hero.svg)

## The problem

On the last project Luca worked on, 80 MEP approval forms went through review. 22 came back with notes or for resubmission, and 17 needed at least one revision (one of them needed six). A form usually came back after about 12 days. After the last reviewer had answered, it still sat for a median of 7 days before anyone sent it back to the contractor.

8 of those 22 returns were plain gaps in the package: a data sheet for a whole range with nothing marked, a technical approval past its date, pump panels without the BMS module. Someone has to find these by reading every PDF, and they are exactly the kind of thing a computer can point at.

## What it does

A project holds its MAF packages and its BOQ. For each package RightFit:

- reads the form (.xls) and every attachment, and keeps each value with its file, page, a short quote and a status. A value stays `extracted` until a person confirms it;
- checks the documents: the ones the law asks for, whether a declaration names the product, whether a certificate is still valid on the review date and at delivery, the approval for contact with drinking water where a pump needs one, and whether each attachment is what the form says it is;
- checks the values: the duty point, the pressure rating, the liquid temperature and the ecodesign limits of air handling units;
- checks the reviewers' checklist, the consultant's own rules and what the product's BOQ line asks for;
- follows the law in force on the review date. In Romania that is Law 10/1995 until 24 Aug 2026 and the construction Code (Law 169/2026) from 25 Aug 2026;
- on a resubmission, shows what changed since the previous revision of the form: the same files (renamed or not), the files that changed, and the new and removed ones;
- drafts the answer, A (approved), B (approved as noted) or C (revise and resubmit), with one comment per issue.

A check passes only on confirmed values. Until then it shows what the result would be.

```mermaid
flowchart LR
    A["MAF package<br/>form and PDFs"] --> B["AI reads<br/>each value with its file,<br/>page and a short quote"]
    B --> C["The reviewer confirms<br/>what the AI read"]
    C --> D["Rules check<br/>law · checklist · BOQ ·<br/>consultant's rules"]
    D --> E["Draft answer<br/>A · B · C, one comment<br/>per issue, with its page"]
    E --> F["The reviewer<br/>decides and signs"]
    classDef ai fill:#ece9fb,stroke:#6250d6,color:#1b1446
    classDef rule fill:#e3efe8,stroke:#1e5a3c,color:#0f2e1f
    classDef person fill:#fdeee4,stroke:#eb6834,color:#3d1a09
    class B ai
    class D,E rule
    class A,C,F person
```

The reviewer works in three steps. First the problems, each one beside its page with the quoted line marked. Then confirming what the AI read: violet with a dashed line is what the AI read, black with a solid line is what a person confirmed. Last, the answer, ready to copy.

![RightFit in six screens: the problems of a pump package beside their pages, why the draft answer is B, confirming what the AI read, the answer ready to copy, an air handling unit at its fourth revision, and what changed since the third](docs/images/tour.gif)

The same application keeps a project's rules and shows what changed between revisions. The pump tools from the midterm, booster sizing and the standby test, are screens of it too.

| What changed since the last revision | The consultant's own rules | Booster sizing |
|---|---|---|
| ![The list of files of revision 4 against revision 3: unchanged, renamed, changed, new and removed](docs/images/since.png) | ![The Rules screen: rules the consultant typed in words or wrote by hand, switched on or off](docs/images/rules.png) | ![The peak flow and head a building needs, the suggested set's curve and the sets that fit](docs/images/booster.png) |

## Where AI is used

The checks are plain Python with no AI in them, so the same package always gives the same result and every result names its rule. AI does the reading, and each AI part is measured against the plain way of doing the same job.

| Job | Done by | Compared with | Result so far |
|---|---|---|---|
| What kind of document each PDF page is | Our own classifier, trained from scratch | Keyword search | 62 % of pages right against 35 %, on 184 locked pages of real packages |
| Which product family a form's row belongs to | Our second classifier, trained from scratch on 21 rows | The family's words (keyword rule) | 28 of 37 locked rows right, against 35 for the words: the words win until there are more labelled rows |
| Which products each document covers | AI matching | Text matching | The same answer on all 51 pairs; the AI also says how a document covers a product |
| Reading values from the documents | AI reader | A person | Not measured yet: 1 of 116 values confirmed so far |
| Turning a rule typed in words, or a BOQ line, into items to check | AI, labelled as AI output | | Not measured; the reviewer sees each item before it counts |
| The whole review | RightFit | General AI chatbots | The protocol was written before any run (`eval/chatbot_baseline/`); no run yet |

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/images/models-dark.svg">
  <img alt="Our own models against the plain way, scored once on locked data. Page type, 184 pages: our model 62 %, keywords 35 %. Product family, 37 rows: our model 76 % (28 of 37), family words 95 % (35 of 37)" src="docs/images/models.svg">
</picture>

More in [`spec/constitution/mission.md`](spec/constitution/mission.md) §8 and in [`eval/`](eval/).

## Running it

Tested with Python 3.14 on macOS.

```
pip install -r requirements.txt
brew install tesseract           # OCR for scanned pages when a pump package is added (macOS)
pytest
python app/review_server.py      # the application: http://127.0.0.1:8520
python app/mcp_server.py         # the checks as MCP tools; an agent starts it from .mcp.json
python -m ingest.rule_watch      # has the act behind each legal rule changed since it was read?
```

The app works on one project at a time, picked in the left rail. Each project is a folder in `data/projects/` (not in Git): its packages, their original files and its BOQs. To share projects, point the app at a shared folder, for example on Google Drive: `python app/review_server.py --projects "<the shared folder>"`. With no project, the app shows P01 and P02 from `data/maf/extracted/`, which is in Git; their original PDFs and forms stay on our laptops in `data/raw/`. Each person starts it with their own name, `python app/review_server.py --reviewer "Jeff"`, which is kept next to every confirmation and decision (Luca when no name is given). The app answers only its own page, so another site open in the same browser can neither read the packages nor confirm or decide anything.

The AI parts (a rule typed in words, what a BOQ line asks) use the Claude command line (`claude`) installed and signed in on the laptop.

## For agents

`app/mcp_server.py` gives any agent that speaks MCP six read-only tools: list the packages, review one, list the rules with their status, classify a package's pages, compare a package with the previous revision of its form, and ask the official sources whether the act behind each legal rule changed since it was read. No tool can confirm a reading or approve a package; that stays with the reviewer. The project's `.mcp.json` tells the agent how to start it, and `.codex/config.toml` does the same for a second agent client.

## The fit check in Revit

Jeff's part, merged on 17 Nov 2026: `revit/` and `checks/space/`, with its spec in `spec/features/revit_fit_check.md`. The MAF review checks what a product is; the fit check shows where it goes. It runs inside the project's own Revit model through pyRevit, a free add-in that runs Python in Revit, on the Windows computer that has Revit.

The architect clicks the pump set in the model. RightFit finds the room it stands in, also in a linked model, and reads the room's outline and height, its doors, everything else standing in it, the pipes that end at the pump and the pump's circuit. It checks the set where it stands and lists how each alternative from the data sheets would do in the same place:

| Check | Question | Rule and its status |
|---|---|---|
| S1 | Does the set stand inside the room and under its ceiling? | I9-2022 art. 19.2, to confirm |
| S2 | Does it hit anything drawn in the model, the door swings included? | I9-2022 art. 19.2, to confirm |
| S3 | Is the service space around it free? | the consultant's own figures for the project; there is no legal one |
| S4 | Does it go through a door of the room, standing, on its narrow side? | I9-2022 art. 17.11, to confirm |
| S5 | Can one pump alone carry the duty, as the standby test found? | I9-2022 art. 6.56, confirmed by Luca |
| S6 | Is there an approval for contact with drinking water? | Order MS 275/2012, read on the official text |

```mermaid
flowchart LR
    A["Click the pump<br/>in the Revit model"] --> B["RightFit reads its room<br/>doors, contents,<br/>pipes, circuit"]
    B --> C["S1 to S6<br/>fits the room, clashes,<br/>service space, door,<br/>standby, drinking water"]
    C --> D["Next Option<br/>each alternative<br/>in its place"]
    D --> E["Swap, once you confirm<br/>Ctrl+Z puts it back"]
    E --> F["K1 to K3<br/>pipes, circuit, weight"]
    classDef rule fill:#e3efe8,stroke:#1e5a3c,color:#0f2e1f
    classDef person fill:#fdeee4,stroke:#eb6834,color:#3d1a09
    class B,C,F rule
    class A,D,E person
```

Next Option shows each alternative in the pump's place as a preview: the maker's Revit family or 3D DWG when the project has it, otherwise a stand-in drawn from the catalogue sizes. Swap puts the chosen alternative into the model once the architect confirms it. It keeps the mark and comments, writes RightFit's verdict into the element and shows what the swap changes: pipe ends that no longer meet the set (K1), more motor power on the circuit, which goes back to the electrical engineer (K2), and the change in weight, which goes to the structural engineer (K3). Ctrl+Z undoes the whole swap.

The checks are the same plain Python file the tests run, with no AI and no network. A value read from the model counts as the design's own; a value from a data sheet stays `extracted` until a person confirms it, and until then a verdict is what the check would say. Every result names its rule and the rule's status, and the report says that RightFit does not certify. The project's own data (the alternatives, the service space, the makers' files) stays in `data/projects/<project>/revit/`, outside Git.

What the review of the code on 17 Nov 2026 found:

- the door check takes the door's width parameter, not the clear opening, so a set within a few centimetres of the width passes and may still not get through;
- the circuit check compares the motors' output power, not the power they draw, so a less efficient set with the same motors adds load without a flag;
- every door is taken to open into the room and every obstacle as a box along the model's axes, so a diagonal pipe or a turned set can show a clash that is not there; these are false alarms, never missed clashes;
- a set whose data sheet leaves a size empty stops the check with an error, and Test Room deletes any room named like the test room, so it must not be pressed in the project's model; both are to fix before it is used on the project's model.

It has been tried in Revit 2026 on a test room, not yet on the project's model, and its rules wait for Luca.

## Where we are (17 Nov 2026)

- Two packages are read: P01, a set of Grundfos pumps, and P02, an air handling unit with its outdoor units, already at revision 4. Of what the AI read, 1 of 116 values and 2 of 15 documents are confirmed so far, so most results are still what a check would say.
- 48 more packages from the same project are on our laptops. The app lists them; none is read yet.
- All 28 legal rules in `data/maf/rules.csv` have been read in the official text, the last nine on 16 Nov. The other four are reviewers' practice and one engineer's input, and each rule shows which it is.
- Since 17 Nov the rule watch asks the official sources whether the act behind a rule changed (all 28 unchanged on its first run), the reviewer's decisions are kept in the project folder, a resubmission shows what changed since the previous revision, and our second own model names a product's family from its form row, though the family words still beat it (35 against 28 of 37 rows).
- Jeff's fit check in Revit was merged on 17 Nov; see above.
- All the packages come from one project, so for now the results are a demonstration, not an evaluation.

The project started as a kitchen hood selector. On 5 Nov 2026 the team moved it to MAF review, and the hood version stays in the Git history.

## Where things are

| To see | Open |
|---|---|
| the application | [`app/`](app/): the server `review_server.py` and the screens in `review/` |
| the checks and the draft answer | [`checks/maf/`](checks/maf/) |
| the fit check in Revit | [`revit/`](revit/) and [`checks/space/`](checks/space/) |
| reading the forms and the BOQs | [`ingest/`](ingest/) |
| our models | [`model/`](model/) |
| every comparison with a baseline | [`eval/`](eval/) |
| the feature in detail | [`spec/features/maf_checker.md`](spec/features/maf_checker.md) |
| the problem, scope and principles | [`spec/constitution/mission.md`](spec/constitution/mission.md) |
| milestones and who does what | [`spec/constitution/roadmap.md`](spec/constitution/roadmap.md) |
| tools and architecture | [`spec/constitution/tech_stack.md`](spec/constitution/tech_stack.md) |
| the rules and where they come from | [`docs/maf_rules.md`](docs/maf_rules.md), [`docs/jurisdictions.md`](docs/jurisdictions.md) |
| the data we have and need | [`docs/data_map.md`](docs/data_map.md) |
| what the old register tells us | [`docs/maf_register_findings.md`](docs/maf_register_findings.md) |
| the look of the application | [`DESIGN.md`](DESIGN.md) |
| how to work in this repository | [`AGENTS.md`](AGENTS.md) |
| decisions so far | [`docs/decisions.md`](docs/decisions.md) |

## A few rules

The repository is public, so nothing confidential goes into Git: no client, project, company or personal names, no prices, no original PDFs. Manufacturer names and model codes are fine. Every technical value needs a source, and when we can't find one the value stays `unclear`. Decisions go in `docs/decisions.md` so they don't get lost in chat.
