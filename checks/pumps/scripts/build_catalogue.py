"""Clean the parsed curves and build one product per row in data/products.csv.

    python scripts/build_catalogue.py

- fills a missing series name from the model (e.g. GHV20 + 10SV05 -> 'GHV20/10SV')
- names booster sets in full: 'GHV20/3SV05'
- per product: shut-off head, max flow in the table, number of curve points
- appends the pumps extracted from your own package (data/products_package_*.csv)
"""
import csv, glob, re
from collections import OrderedDict
from pathlib import Path

D = Path(__file__).parent.parent / "data"
HEADER = open(D.parent / "templates/products.csv").readline().strip().split(",")


def clean_curves(path):
    rows = list(csv.DictReader(open(path)))
    last_series = ""
    for r in rows:
        s = r["series"].replace(" BOOSTER SETS SERIES", "").replace(" SERIES", "").strip()
        if r["category"] == "booster_set":
            prefix = re.match(r"(\d+)SV", r["model"])
            if not s or "/" not in s:
                s = f"GHV{r['n_pumps']}0/{prefix.group(1)}SV" if prefix else last_series
            r["set_model"] = f"{s.split('/')[0]}/{r['model']}"
        else:
            r["set_model"] = r["model"]
        r["series"] = s; last_series = s
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
    return rows


def products_from_curves(rows):
    by = OrderedDict()
    for r in rows:
        by.setdefault((r["category"], r["set_model"], r["p2_kw_each"]), []).append(r)
    out = []
    for (cat, model, p2), pts in by.items():
        r0 = pts[0]
        qs = [float(p["q_m3h"]) for p in pts]; hs = [float(p["h_m"]) for p in pts]
        out.append({
            "product_no": "", "maker": r0["maker"], "model": model, "family": r0["series"], "category": cat,
            "pump_type": "MS-V" if cat == "booster_set" else "submersible_drainage",
            "speed": "variable" if r0["series"].startswith("GHV") else "fixed",
            "submersible": cat != "booster_set",
            "motor_type": "induction",
            "pump_count": r0["n_pumps"], "flow_m3h": "", "head_m": "",
            "max_flow_m3h": max(qs), "max_head_m": max(hs),
            "p2_kw": round(float(p2) * int(r0["n_pumps"]), 2) if p2 else "",
            "mei": r0["mei"], "source_file": f"{r0['source_file']} p{r0['page']}", "source_url": r0["source_url"],
            "checked_by": "",
        })
    return out


def main():
    rows = []
    for f in [D / "curves_booster_sets.csv", D / "curves_drainage_pumps.csv"]:
        rows += clean_curves(f)
    prods = products_from_curves(rows)
    for f in sorted(glob.glob(str(D / "raw" / "products_package_*.csv"))):
        for r in csv.DictReader(open(f)):
            r["category"] = r.get("category") or ("booster_set" if "Hydro" in r["model"] else "drainage_pump")
            prods.append(r)
    with open(D / "products.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=HEADER, extrasaction="ignore"); w.writeheader(); w.writerows(prods)
    from collections import Counter
    print(Counter(p["category"] for p in prods), "->", D / "products.csv")


if __name__ == "__main__":
    main()
