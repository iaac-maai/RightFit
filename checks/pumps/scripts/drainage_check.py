"""Stormwater / drainage pump check on real curves (CTE DB-HS5).

    python scripts/drainage_check.py --area 200 --zone B --isohyet 60 --lift 4 --submitted "DOC7(T)"

1. CALCULATES inflow = area x rainfall intensity (HS5 App. B), each pump >= 125% of inflow
   (HS5 4.6.2.1), head = lift + losses (4.6.2.2), sump useful volume from HS5 eq. (4.2)
   (unit as read by Luca: 300 s of pump flow; see rule HS5-SUMP)
2. PREDICTS the submitted pump's flow at that head and, if it is too small, how long the
   sump takes to overflow with one pump and with both pumps running
3. SUGGESTS pumps from data/curves_drainage_pumps.csv, ranked by power
Thresholds come from rules/rules.json.
"""
import argparse, csv, json, sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from rules import param, cite  # noqa: E402

D = Path(__file__).parent.parent / "data"
LOSS_M = 1.5          # pipe losses pump -> discharge: engineer's assumption, replace with calc


def intensity(zone, isohyet):
    for r in csv.DictReader(open(D / "cte_hs5_rainfall_intensity.csv")):
        if r["zone"] == zone:
            return float(r[f"isohyet_{isohyet}"])
    raise SystemExit("zone A or B; isohyet 10..120 in steps of 10")


def curves():
    c, meta = defaultdict(list), {}
    for r in csv.DictReader(open(D / "curves_drainage_pumps.csv")):
        c[r["set_model"]].append((float(r["q_m3h"]), float(r["h_m"]))); meta[r["set_model"]] = r
    return {k: sorted(v) for k, v in c.items()}, meta


def flow_at(curve, head):
    for (q1, h1), (q2, h2) in zip(curve, curve[1:]):
        if h2 <= head <= h1 and h1 != h2:
            return q1 + (q2 - q1) * (h1 - head) / (h1 - h2)
    return None if head > curve[0][1] else curve[-1][0]


def overflow_min(sump_m3, inflow, pumping):
    return None if pumping >= inflow else round(sump_m3 / (inflow - pumping) * 60, 0)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--area", type=float, required=True)
    ap.add_argument("--zone", default="B"); ap.add_argument("--isohyet", type=int, default=60)
    ap.add_argument("--lift", type=float, required=True)
    ap.add_argument("--sump-m3", type=float, help="actual useful sump volume; default = HS5 minimum for the required pump")
    ap.add_argument("--submitted"); ap.add_argument("-k", type=int, default=3)
    a = ap.parse_args()
    i = intensity(a.zone, a.isohyet)
    inflow = a.area * i / 1000
    q_req = param("HS5-PUMP-FLOW", "flow_factor") * inflow
    sump_req = param("HS5-SUMP", "useful_volume_s_of_pump_flow") * q_req / 3600       # m3
    sump = a.sump_m3 or sump_req
    need = dict(rain_mm_h=i, inflow_m3h=round(inflow, 1), required_flow_each_m3h=round(q_req, 1),
                required_head_m=a.lift + LOSS_M, sump_min_m3=round(sump_req, 2), sump_used_m3=round(sump, 2),
                rules=[cite("HS5-RAIN"), cite("HS5-PUMP-FLOW"), cite("HS5-SUMP") + " - unit interpreted"])
    cv, meta = curves()

    def judge(name):
        q = flow_at(cv[name], need["required_head_m"])
        r = dict(model=name, kw=meta[name]["p2_kw_each"], flow_at_head_m3h=None if q is None else round(q, 1),
                 source=f"{meta[name]['source_file']} p{meta[name]['page']}", issues=[])
        if q is None or q < q_req:
            r["issues"].append(f"undersized: {0 if q is None else round(q, 1)} < {round(q_req, 1)} m3/h each ({cite('HS5-PUMP-FLOW')})")
            q = q or 0
            r["overflow_after_min"] = {"one_pump": overflow_min(sump, inflow, q),
                                       "both_pumps": overflow_min(sump, inflow, 2 * q)}
        r["verdict"] = "fits" if not r["issues"] else "does not fit"
        return r

    out = {"1_need": need}
    if a.submitted:
        out["2_judge"] = judge(a.submitted) if a.submitted in cv else f"{a.submitted} not in catalogue"
    fits = sorted((r for n in cv for r in [judge(n)] if r["verdict"] == "fits"), key=lambda r: float(r["kw"] or 99))
    out["3_suggest"] = {"install": f"{param('HS5-PUMP-STATION', 'min_pumps')} identical pumps, alternating ({cite('HS5-PUMP-STATION')})",
                        "options": fits[:a.k]}
    print(json.dumps(out, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
