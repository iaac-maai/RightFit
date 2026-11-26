# Feature spec: the fit check in Revit

Status: proposed by Jeff on 17 Nov 2026, from the instructor's comment after the midterm. To agree with Sahil and Luca (see docs/decisions.md). Luca approves every engineering rule before a result built on it counts.

## 1. What it does
The MAF checker reads what a product *is*. The fit check shows where it *goes*: inside the project's own Revit model it finds the pump the form is about, checks that it fits its room, and lets the architect try the alternatives and see what each one changes in the space before anyone signs.

- user: the architect (and the MEP designer) working in the project's Revit model; the reviewer sees the same results;
- first family: booster sets, because P01 holds one (Hydro Multi-E 2 CME 15-2) with real alternatives;
- runs inside Revit 2026 through pyRevit (a free add-in that runs Python in Revit);
- not in this feature: rerouting pipes or redesigning the circuit, structural design of the plinth, finding the best spot in the room, clashes against linked models' MEP elements, a whole-project scan. Those are later features.

## 2. How it fits the constitution
Unchanged: checks are deterministic Python with no AI (`checks/space/`); every value has a source and a status; a check passes only on verified inputs, otherwise it says what the result would be; every result names its rule and the rule's status; humans decide, and the tool never moves anything without the architect pressing the button; nothing confidential in Git.

What is new: the Revit model is a source. A value read from the model (the room outline, a door width, a pipe size) has the source `model` and counts as the design's own value. The candidate pump sets come from data sheets, so their values are `extracted` until a person confirms them.

## 3. Inputs

### From the Revit model (read by the add-in, never typed)
| Value | Where it comes from in Revit |
|---|---|
| The pump in question | the element the architect clicks (mechanical equipment, or a generic model) |
| Its position and turn | the element's own placement; its real size from its geometry |
| The room | the Room (or MEP Space) at the pump's position, in the model or in a linked model |
| The room's outline and height | the room's boundary and its computed height |
| The doors of the room | doors whose from- or to-room is this room: width, height, position, which side they open to |
| What else is in the room | every model element whose box touches the room: equipment, pipes, ducts, cable trays, columns, beams, generic models |
| The pipes at the pump | pipes with an end within 300 mm of the pump: their size (DN) and where they end |
| The pump's circuit | the electrical circuit the pump is connected to: breaker rating, voltage, load |

### From the project folder (`data/projects/<project>/revit/`, git-ignored)
| File | What it holds |
|---|---|
| `candidates.json` | the submitted set and its alternatives: maker, model, size (L × W × H mm), weight, number of pumps, motor power each, power one pump needs at the duty, standby verdict, suction and discharge DN, drinking water approval, each with its source and status |
| `project.json` | the service space the consultant asks for, and anything the model doesn't hold yet: the circuit when the model has none, the room for a test build |
| `families/` | the makers' models, one per candidate: a Revit family (.rfa) from the makers' BIM pages, or a 3D DWG where the maker offers no family (Grundfos); `families.json` maps names, types, up axis and notes, and Prepare Models saves each family's shape (`.shape.json`) so previews never load the family |

A template with the fields and no values is in `revit/templates/`.

## 4. The checks (`checks/space/space_checks.py`)
Each returns results in the same form as `checks/maf/`: check, result (pass, flag, unclear, info), would_be, reason, rules. All sizes in mm.

| Check | Question | Rule | Rule status |
|---|---|---|---|
| S1 | Does the set stand inside the room, below its ceiling? | I9-2022 art. 19.2 (the equipment meets the design's dimensions) | to confirm (Luca) |
| S2 | Does the set hit anything in the model? | I9-2022 art. 19.2 | to confirm |
| S3 | Is the service space around it free (front, sides, back, above)? | the consultant's service space (there is no legal figure; Luca, 12 Nov: "good manner positioning") | consultant's preference |
| S4 | Can it be brought in and taken out through a door of the room? | I9-2022 art. 17.11 | to confirm |
| S5 | Can one pump alone carry the duty? | I9-2022 art. 6.56; the standby test (MAF-19) | verified (Luca) |
| S6 | Is there an approval for contact with drinking water? | Order 275/2012 (`RO-OMS275-DW`), as H1 | verified_official |

The swap adds the knock-on checks, comparing the new set with the one in the model:

| Check | Question | Rule |
|---|---|---|
| K1 | Do the pipes at the pump still meet it? Size (a smaller connection needs a reducer) and where they end (inside the new set, or short of it) | the design's pipe sizes |
| K2 | Is the pump's circuit still enough? The new motor power against the circuit's breaker and load | I7-2011 (to confirm); never passes: the circuit is re-checked by the electrical engineer when the load grows |
| K3 | Weight on the plinth and the slab: the change, and the 25 cm gap of art. 18.7 | I9-2022 art. 18.7 (to confirm); unclear until the structure is checked |

The verdict of a set is the worst of its results: FAIL when something blocks it (a clash, outside the room, no standby, does not fit through any door), flag when the reviewer has to look, would pass otherwise.

## 5. In Revit
A RightFit tab with six buttons:

1. **Check pump**: click the pump in the model (only an element whose names say it is a pump, or that matches a candidate, can be clicked); RightFit reads its room and checks the set in it, and the candidates one by one, without changing the model.
2. **Next option**: shows the next candidate in the pump's place, as a preview.
3. **Swap**: puts the chosen candidate in the pump's place: the maker's family when it is in `families/`, or a type of the same family that names the model. It keeps the mark and comments, writes RightFit's verdict into the element, and draws what the swap changes (pipe ends that no longer meet it, the circuit, the weight). One Undo in Revit puts everything back.
4. **Clear**: removes what RightFit drew.
5. **Settings**: the projects folder, the project and the service space.
6. **Test room**: builds the room `project.json` describes in an empty model (walls, a Room, a door, the fixed equipment as boxes, the set), to try RightFit before the project's model is at hand.

The preview draws the set in the verdict colour (green would pass, amber flag, red FAIL), its service space in translucent teal, and clashes in red or amber, in a 3D view cropped to the room.

## 6. Tests
`tests/test_space_checks.py`: hand-written cases for every check, on a made-up room; Luca approves the cases with the rules. The Revit part cannot run in CI; it is tested by hand in Revit 2026 and each test session is written up in `eval/revit/`.

## 7. Open questions [O]
- Luca: the I9-2022 articles 17.11, 18.7 and 19.2 for these checks; K2's wording.
- Which service space to use by default. Luca has no rule; the consultant sets it per project.
- Who owns the families folder when the makers' licences don't allow sharing the .rfa files.
