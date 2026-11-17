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
| `families/` | the makers' Revit families (.rfa), named `<id>.rfa` or listed in `families.json` | |

The makers publish their families for free (an account is needed): Grundfos on MEPcontent and the Grundfos
Product Center, Wilo in its BIM/CAD catalogue, DAB and Lowara on BIMobject. They stay on our laptops and are
not added to Git.

Then in Revit: RightFit > Settings > Project, and pick it.

## Use

| Button | What it does |
|---|---|
| Check Pump | Click the pump set. RightFit finds its Room (or MEP Space, also in a linked model), reads the room's outline and height, its doors, everything else in it, the pipes that end at the pump and the pump's circuit. It checks the set where it stands (S1-S6) and lists how each candidate would do there. |
| Next Option | Shows the next candidate in the pump's place. It uses the maker's family when it is in `families/`, otherwise a stand-in drawn from the catalogue sizes. The pump is only hidden in the RightFit 3D view. |
| Swap | Replaces the set in the model with the chosen candidate. It places the maker's family, or changes the type when the pump's own family holds the model. It keeps the mark and comments, writes RightFit's verdict into the element (*RightFit verdict*, *RightFit set*, *RightFit checked on*), and draws what changed: pipe ends that no longer meet the set, and clashes (K1-K3). **Ctrl+Z undoes the whole swap.** It refuses to replace a real family with a stand-in. |
| Clear | Removes RightFit's drawing and shows the pump again. |
| Settings | Projects folder, project, service space. |
| Test Room | Builds the room described in `project.json` in an empty model: walls, a Room, a door, the fixed equipment as boxes and the pump set. Use it to try RightFit before the project's model is available. |

Colours: green would pass, amber flag, red FAIL. The service space is translucent teal, and clashes are red
when they block and amber when they need a look. Until a person confirms the data sheet values, a verdict is
what the check would say. Rules marked `to_confirm` wait for Luca.

## Not checked yet

Pipe routes beyond the pump, the circuit's cable and breaker (K2 sends them back to the electrical engineer),
the structure under the set, noise, and anything not drawn in the model.
