# Decisions — RightFit

| Date | Decision | Reason | Agreed by |
|---|---|---|---|
| 28 Oct 2026 | Repository `iaac-maai/RightFit`, private. | Version control and collaboration; confidential material stays out | Sahil (pending Jeff and Luca) |
| 28 Oct 2026 | Constitution follows the IAAC structure: `spec/constitution/mission.md`, `roadmap.md`, `tech_stack.md`. | Matches the IAAC SDD structure | Sahil (pending Jeff and Luca) |
| 28 Oct 2026 | Principles live in `mission.md`; no fourth constitution file; agent instructions live in `AGENTS.md`. | One place for each kind of rule | Sahil (pending Jeff and Luca) |
| 28 Oct 2026 | Spain is the provisional testing context; Luca validates applicable standards; no check is presented as regulatory compliance until then. | Prototype developed in Barcelona; standards not yet validated | Sahil (pending Jeff and Luca) |
| 28 Oct 2026 | Problem segmentation and data map live in `docs/`, separate from the constitution. | They are IAAC deliverables, not constitution files | Sahil (pending Jeff and Luca) |
| 28 Oct 2026 | First product family: kitchen extraction hoods. | Chosen in Concept v2 (22 Oct); whether lighting or grilles would show the interior/MEP overlap better is an open question for the instructor | Sahil (pending Jeff and Luca) |
| 28 Oct 2026 | Proposal on branch `maf-checker`: the first use case becomes the review of material approval forms for MEP equipment, starting with pumps and AHUs, instead of hood selection; spec in `spec/features/maf_checker.md`. | Mentors' comments; real data held: a register of 80 MAFs and two complete packages; hood rules in Barcelona are simple enough that a checker adds little | Luca, pending Sahil and Jeff |
| 28 Oct 2026 | Dependency `xlrd` on branch `maf-checker`, to read the approval forms (.xls) in `ingest/maf_form.py`; `requirements.txt` lists it with Streamlit, pandas (installed with Streamlit) and pytest, not pinned until the environment is chosen. | The forms are old Excel files that openpyxl cannot read; the spec names xlrd | Luca, pending Sahil and Jeff |
| 28 Oct 2026 | No tolerance on the pump duty point (ENG-DUTY-TOL = 0). Control panels by pump application: required for circulation and stormwater pumps, recommended for booster sets, a float switch is enough for drainage pumps (ENG-PUMP-PANEL, checklist CL-09). | The designer already includes the margins and the site orders what the design states; panel needs from Luca's practice | Luca |
