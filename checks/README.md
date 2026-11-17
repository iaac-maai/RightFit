# checks: the rules, in plain Python

Every check RightFit runs. There is no AI in here: the same package always gives the same result, and every result names its rule. Every function has a test in `tests/`, and every engineering rule is approved by Luca.

| Folder | What it checks |
|---|---|
| `maf/` | a material approval form and its documents: `checks.py` (D1 to D4, V1 to V3, E1, H1, C, P, Q, R), `rules.py` (which rules apply in a country on a date), `status.py` (A, B or C), `comments.py` (one comment per issue, filled from templates) |
| `pumps/` | the pump kit: rules and catalogue data for booster sets and drainage pumps, and the scripts behind booster sizing and the standby test; it has its own README |
| `space/` | the fit check in Revit: does a pump set fit its room, and what a swap changes; `revit/` calls it |

The tables these checks read are in `data/`.
