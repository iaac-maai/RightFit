# v2: Luca's review (2 Nov 2026)

| # | Luca's point | Done | Result |
|---|---|---|---|
| - | rules.json with EUR-Lex / BOE quotes | used Luca's file as the base | CE-01, MOTOR-IE, LEG-01, PUMP-MEI confirmed; HS5-SUMP unit marked "interpreted" |
| 1 | mains pressure assumes direct suction | `--mains-m` default 0 (break tank, from `HS4-HEAD.params`); `--suction-m` for Ha | 40 flats: 45.6 m, not 20.6 |
| 2 | simultaneity | DIN now counts cold + hot VR for mixers; `--method une` uses CTE Table 2.1 flows | DIN 7.2 m3/h. UNE gives 11.9 m3/h with cold + hot through the booster (Luca's 10-11 looks like cold only, 10.6). UNE constants still unverified |
| 3 | 500 kPa flag on variable-speed sets | variable speed: no failure, only "if the controller fails at full speed: ..." as info | GHV20/5SV16 still "oversized", no PMAX failure |
| 4 | 8 min overflow | sump from HS5 eq. 4.2 (300 s of pump flow); overflow time with 1 and with 2 pumps | DOC7 on a 2 m3 sump: 8 min one pump, 31 min both |
| 5 | MEI / IE need applies_to | `applies_to` on every rule; `product_rules_check.py`; scope fields `pump_type`, `motor_type`, `submersible`, `speed` | all 4 package pumps: MEI and IE "n/a" with the reason; only CE-01 returns the form |
| 6 | broken drainage rows | parser stops at electrical tables and reads model names up to the kW column | DOC / DOC 7VX rows gone; DL(M) 80-DLF(M) 80, DL 105 - DLF105, DL(M) 109, DL 125, DLV(M) 100, DLV 115, DN(M) 110/115/120 restored with correct kW (checked against p45) |
| 7 | thresholds hardcoded | `scripts/rules.py`: param(), applies(), cite(); scripts read rules.json | `merge_rules.py` ready for data/maf/rules.csv, NOT run on the real file (dry run first) |
| + | Hydro Multi-E standby test | `digitize_grundfos_curve.py` reads the curves from the PDF vector drawing | 1 pump at full speed: 51.3 m at 15 m3/h vs 50 m duty. The second pump is a real standby, but with only 1.3 m (2.6%) margin; 2 pumps: 53.0 m |

Package files moved to `data/raw/` and `.gitignore` excludes `data/raw/` and `raw/`.

Still open:
- UNE 149201 constants (paywalled) and which flows the booster carries (cold only, or cold + hot)
- LOSS_FACTOR (25% of height) and OVERSIZE (25%) are engineer's assumptions in code, not rules: move them to a project settings file once pipes are sized
- merging the repo's 16 rules: send rules.csv or run `merge_rules.py` on it
