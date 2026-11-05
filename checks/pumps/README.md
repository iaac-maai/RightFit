# RightFit dataset (v2, 2 Nov 2026) - see CHANGES.md for Luca's review fixes

RightFit's own dataset, built from public sources and your own package. No partner firm needed.
Every file says where it came from (`data/SOURCES.csv`), and every rule quotes its clause and page.

## What's in it

| Layer | File | Size | Source |
|---|---|---|---|
| **Rules** | `rules/rules.json` | 17 rules (13 quoted from the CTE with page) | CTE DB-HS, EU regulations |
| | `data/cte_hs4_fixture_flows.csv` | 20 fixtures | CTE HS4 Table 2.1 |
| | `data/cte_hs5_rainfall_intensity.csv` | zones A/B × 12 isohyets | CTE HS5 Table B.1 |
| | `data/cte_hs_rule_sentences.csv` | 579 Spanish rule sentences (HS1–HS5) | CTE, auto-extracted, ready to annotate |
| | `public/codeaccord/annotated_data/` | 862 labelled sentences, 4,329 relations | CODE-ACCORD (CC-BY-4.0) |
| **Products** | `data/curves_booster_sets.csv` | 289 booster sets, 2,582 curve points | Lowara GHV catalogue |
| | `data/curves_drainage_pumps.csv` | 143 drainage pumps, 1,580 curve points | Lowara DOC/DOMO/DL catalogues |
| | `data/products.csv` | 439 products, one row each | the two files above + your package |
| **Your package** | `data/raw/products_package_IS15.csv` | 4 Grundfos pumps | your data sheets |
| | `data/raw/declarations_package_IS15.csv` | 2 declarations (one OCR'd from a scan) | your package |
| | `data/raw/page_labels_package_IS15.csv` | 34 pages labelled | your package (auto, check) |
| **Reviews** | `templates/reviews.csv` | empty | only Luca has the 22 returns |

`public/regulations/ES_CTE_DB-HS.pdf` is the official CTE text the rules quote.

## The checks it runs

```
pip install pdfplumber pymupdf numpy

# round 1, automated: declarations (CE-01) + scoped product rules (MEI, IE only where they apply)
python scripts/product_rules_check.py data/raw/products_package_IS15.csv data/raw/declarations_package_IS15.csv
#  -> RETURN: Hydro Multi-E and DPK have no declaration; MEI and IE are n/a for all 4 pumps

# booster, break tank (default): need 7.2 m3/h (DIN, mixers cold+hot) at 45.6 m
python scripts/booster_check.py --flats 40 --floors 10 --submitted GHV20/5SV16
python scripts/booster_check.py --flats 40 --floors 10 --method une     # 11.9 m3/h, UNE constants unverified
# is the package's second pump a real standby? (curve read from the Grundfos PDF drawing)
python scripts/booster_check.py --duty-flow 15 --duty-head 50 --submitted-curve "Hydro Multi-E 2 CME 15-2" -k 0
#  -> one pump alone gives 51.3 m at 15 m3/h: standby OK, 1.3 m margin

# stormwater: sump sized by HS5 (unit as Luca reads it), overflow time with 1 and 2 pumps
python scripts/drainage_check.py --area 200 --zone B --isohyet 60 --lift 4 --submitted "DOC7(T)"
```

## Scripts

- `parse_performance_tables.py`: turns any catalogue "hydraulic performance table" into curve data. It reads column positions, so blank cells stay blank. Spot-checked against the printed pages.
- `build_catalogue.py`: cleans the curves and rebuilds `products.csv`.
- `extract_datasheet.py`: Grundfos Product Center data sheets (RO/EN) to products.
- `digitize_grundfos_curve.py`: reads Q-H curves from the vector drawing of a Grundfos data sheet.
- `rules.py`: every script reads thresholds and scope from `rules/rules.json`.
- `product_rules_check.py`: runs the product rules only where `applies_to` matches.
- `merge_rules.py`: merges the repo's `data/maf/rules.csv` into `rules.json` (dry run first).
- `get_public_data.sh`: re-downloads the public sources.

## Still to do (team)

1. **Luca:**
   - Confirm the 4 rules marked `verify` (EU texts: EUR-Lex was not reachable from here).
   - Confirm the unit of Qb in the HS5 sump formula.
   - Confirm the DIN 1988-300 simultaneity constants in `booster_check.py`.
2. **Luca:** fill `templates/reviews.csv` with the 22 returned forms. That's the only layer the public web can't give you.
3. **All:** check `page_labels_package_IS15.csv`; the page-type labels are automatic.
4. **Optional:**
   - Add a second maker. Wilo and Grundfos catalogues parse the same way once you have the PDFs.
   - The Lowara e-SH tables are image-encoded and need OCR.
5. If projects are in Romania, add Normativ I9-2022 rules in the same format.

## Rules on use

- Manufacturer catalogue data is for research. Cite the source URL and don't republish the PDFs.
- Package files (`*_package_IS15.csv`) are confidential project data. Keep them out of public repos.
- CODE-ACCORD is CC-BY-4.0. Cite: Hettiarachchi et al., *CODE-ACCORD*, Scientific Data 2025.
