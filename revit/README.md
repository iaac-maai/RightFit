# RightFit in Revit

The fit check (`spec/features/revit_fit_check.md`) as a Revit 2026 add-in. Click the pump set in the model.
RightFit reads its room, checks the set where it stands, and shows the alternatives in its place. The
architect can swap one in, and RightFit shows what the swap changes. The checks are the same Python file the
tests run (`checks/space/space_checks.py`), with no AI in them.

## Install (once, on the Windows computer with Revit)

1. Install [pyRevit](https://github.com/pyrevitlabs/pyRevit/releases) (the normal installer, not the admin one).
2. Get this repository on the computer (clone it, or download it as a zip and unzip it).
3. In Revit: pyRevit tab > Settings > Custom Extension Directories > Add folder, and pick the repository's
   `revit` folder. Save Settings and Reload. A **RightFit** tab appears.

## Set up a project (once per project)

The project's data stays out of Git, in `data/projects/<project>/revit/`:

| File | What | Template |
|---|---|---|
| `candidates.json` | the submitted set and its alternatives, from their data sheets | `revit/templates/candidates.json` |
| `project.json` | the consultant's service space; the circuit if the model has none; an optional test room | `revit/templates/project.json` |
| `families/` | the makers' models: a Revit family (`<id>.rfa`) or a 3D DWG (`<id>.dwg`), or any name listed in `families.json` | |

The makers publish their models for free: Grundfos on its Product Center (product page > CAD tab > DWG), Wilo in
its CAD catalogue, DAB and Lowara on BIMobject. A 3D DWG is read in millimetres and stood upright by matching its
sizes to the catalogue's L x W x H (`"units"` in `families.json` overrides the units). A DWG has no pipe or power
connections, so it is used for previews and the test room but never replaces a real Revit family in a project
model. The files stay on our laptops and are not added to Git.

`families.json` maps a candidate's id to its file when the name differs, with optional keys: `type` (the type to
load from a family with a `.txt` type catalogue), `type_contains` (part of the type name), `up` (`x`, `y` or `z`:
the drawing's up axis, when matching sizes is not enough; Grundfos CME drawings use `x`, CR drawings `y`), `units`
and `note` (shown in the report, for a near match or a missing file). An empty `file` means "no file: stand-in".

Loading a maker's Revit family into the project left Revit 2026 busy for minutes after the command ended (seen in
Revit's journal with the DAB and Wilo families). So previews never load them: **Setup > Prepare Models** loads each
`.rfa` once, saves its shape beside it as `<file>.<type>.shape.json` and undoes the load. Next Option, and Swap in
a test room, then draw the set from that saved shape. Run Prepare Models again after adding a family.

Then in Revit: RightFit > Settings > Project, and pick it.

## Use

| Button | What it does |
|---|---|
| Check Pump | Click the pump set. Only a pump set can be clicked: an element whose names (family, type, Model, comments) hold a candidate's model code or a pump word (pump, booster, bomba, pompa...); tanks, pits, vessels and RightFit's own drawings can't. RightFit finds its Room (or MEP Space, also in a linked model), reads the room's outline and height, its doors, everything else in it, the pipes that end at the pump and the pump's circuit. It checks the set where it stands (S1-S6) and lists how each candidate would do there. The report opens with a summary box, then a table of the room (length, width, height, area, volume, doors, what else is in it, pipe ends, service space, circuit) and a table of the set (sizes measured and on the data sheet, weight, pumps, power, standby, pipe sizes, drinking-water approval, source and status); a value the data doesn't give says "not given". |
| Next Option | Shows the next candidate in the pump's place. It uses the maker's model when it is in `families/` (a family from its saved shape, a 3D DWG as it is), otherwise a stand-in drawn from the catalogue sizes, and compares the model's measured size with the catalogue's. The pump is only hidden in the RightFit 3D view. |
| Swap | Replaces the set in the model with the chosen candidate. It places the maker's family (in a test room, its saved shape), or changes the type when the pump's own family holds the model. It keeps the mark and comments, writes RightFit's verdict into the element (*RightFit verdict*, *RightFit set*, *RightFit checked on*), and draws what changed: pipe ends that no longer meet the set, and clashes (K1-K3). **Ctrl+Z undoes the whole swap.** It refuses to replace a real family with a stand-in. |
| Clear | Removes RightFit's drawing and shows the pump again. |
| Settings | Projects folder, project, service space. |
| Prepare Models | Saves the shape of each maker's Revit family in `families/` once, so Next Option never loads the family into the model (see above). Nothing stays in the model. |
| Test Room | Builds the room described in `project.json` in an empty model: walls, a Room, a door, the fixed equipment as boxes and the pump set. Use it to try RightFit before the project's model is available. |

Colours: green would pass, amber flag, red FAIL. The service space is translucent teal, and clashes are red
when they block and amber when they need a look. Until a person confirms the data sheet values, a verdict is
what the check would say. Luca approved the fit check's rules on 26 Nov 2026; a rule added later is marked `to_confirm` until he does.

## Not checked yet

Pipe routes beyond the pump, the circuit's cable and breaker (K2 sends them back to the electrical engineer),
the structure under the set, noise, and anything not drawn in the model.
