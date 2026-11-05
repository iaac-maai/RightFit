"""Booster set check on real pump curves: building -> rule -> need -> judge -> suggest.

    # 40 flats, 10 floors, break tank (default: mains pressure is lost, CTE HS4 4.5.2.2.4)
    python scripts/booster_check.py --flats 40 --floors 10
    # direct suction, only where the water company allows it
    python scripts/booster_check.py --flats 40 --floors 10 --mains-m 25
    # judge a set from the catalogue, or the package's own set from its digitised Grundfos curve
    python scripts/booster_check.py --flats 40 --floors 10 --submitted GHV20/5SV16
    python scripts/booster_check.py --duty-flow 15 --duty-head 50 --submitted-curve "Hydro Multi-E 2 CME 15-2"

1. CALCULATES the need: peak flow by DIN 1988-300 (default) or UNE 149201 (--method une),
   head Pb = Ha + Hg + Pc + Pr (CTE HS4 4.5.2.2.4)
2. PREDICTS from the curve: head at the needed flow, top-floor pressure, and whether the
   set still meets the duty with one pump out of service (is the second pump a real standby?)
3. SUGGESTS sets from data/curves_booster_sets.csv, ranked by power
Thresholds come from rules/rules.json (scripts/rules.py), never from this file.
"""
import argparse, csv, json, sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from rules import param, cite  # noqa: E402

D = Path(__file__).parent.parent / "data"

# --- simultaneity methods -------------------------------------------------------------
# DIN 1988-300 Table 2 calculation flows (l/s), constants checked by Luca 2026-11-02.
# Mixer taps draw cold + hot upstream of the heater, so hot VR counts too (Luca, point 2).
DIN_FLAT = {"wc_cistern": (0.13, 0), "basin_mixer": (0.07, 0.07), "shower_mixer": (0.15, 0.15),
            "kitchen_mixer": (0.07, 0.07), "washing_machine": (0.15, 0), "dishwasher": (0.07, 0)}
DIN_A, DIN_B, DIN_C = 1.48, 0.19, 0.94
# UNE 149201 with CTE Table 2.1 flows. CONSTANTS NOT VERIFIED against the standard (paywalled):
# values as commonly cited for dwellings, QT <= 20 l/s: A=0.682 B=0.45 C=-0.14; QT > 20: A=1.7 B=0.21 C=-0.7
UNE_FLAT = {"Inodoro con cisterna": 1, "Lavabo": 1, "Ducha": 1, "Fregadero doméstico": 1,
            "Lavadora doméstica": 1, "Lavavajillas doméstico": 1}
FLOOR_H = 3.0
LOSS_FACTOR = 0.25            # Pc as share of height: engineer's assumption until pipes are sized
OVERSIZE = 0.25               # >25% head above need = oversized: engineer's choice


def peak_flow(flats, method):
    if method == "din":
        total = flats * sum(c + h for c, h in DIN_FLAT.values())
        return max(DIN_A * total ** DIN_B - DIN_C, 0), total
    cte = {r["fixture_es"]: r for r in csv.DictReader(open(D / "cte_hs4_fixture_flows.csv"))}
    per_flat = sum(n * (float(cte[f]["cold_min_ls"]) + float(cte[f]["dhw_min_ls"] or 0)) for f, n in UNE_FLAT.items())
    total = flats * per_flat
    a, b, c = (0.682, 0.45, -0.14) if total <= 20 else (1.7, 0.21, -0.7)
    return max(a * total ** b + c, 0), total


def need(a):
    if a.duty_flow:
        return dict(peak_flow_m3h=a.duty_flow, required_head_m=a.duty_head, geometric_height_m=None,
                    losses_m=None, method="duty point given")
    q, total = peak_flow(a.flats, a.method)
    hg = (a.floors - 1) * FLOOR_H + 1.5
    pc = LOSS_FACTOR * hg
    pr = param("HS4-PMIN", "p_min_tap_m")
    head = a.suction_m + hg + pc + pr - a.mains_m
    return dict(method=a.method.upper() + (" (constants unverified)" if a.method == "une" else ""),
                sum_fixture_flows_ls=round(total, 1), peak_flow_ls=round(q, 2), peak_flow_m3h=round(q * 3.6, 1),
                Ha_m=a.suction_m, geometric_height_m=hg, losses_m=round(pc, 1), residual_m=pr,
                mains_subtracted_m=a.mains_m, required_head_m=round(head, 1),
                rule=cite("HS4-HEAD"))


def interp(curve, q):
    for (q1, h1), (q2, h2) in zip(curve, curve[1:]):
        if q1 <= q <= q2:
            return h1 + (h2 - h1) * (q - q1) / (q2 - q1)
    return curve[0][1] if q <= curve[0][0] else None


def catalogue():
    c, meta = defaultdict(list), {}
    for r in csv.DictReader(open(D / "curves_booster_sets.csv")):
        c[r["set_model"]].append((float(r["q_m3h"]), float(r["h_m"]))); meta[r["set_model"]] = r
    return {k: sorted(v) for k, v in c.items()}, meta


def package_curves(model):
    c = defaultdict(list)
    for r in csv.DictReader(open(D / "raw" / "curves_package_IS15.csv")):
        if r["model"] == model:
            c[r["curve"]].append((float(r["q_m3h"]), float(r["h_m"])))
    return {k: sorted(v) for k, v in c.items()}


def judge(name, set_curve, pumps, n, mains_m, kw=None, mei=None, variable=True, one_out_curve=None):
    q = n["peak_flow_m3h"]
    h = interp(set_curve, q)
    if one_out_curve is None and pumps > 1:   # catalogue tables give all pumps running: scale flow
        h_out = interp(set_curve, q * pumps / (pumps - 1))
    else:
        h_out = interp(one_out_curve, q) if one_out_curve else None
    r = dict(model=name, pumps=pumps, kw_total=kw, mei=mei, speed="variable" if variable else "fixed",
             head_at_need_m=None if h is None else round(h, 1),
             head_one_pump_out_m=None if h_out is None else round(h_out, 1), issues=[], info=[])
    if h is None:
        r["issues"].append("needed flow is beyond the curve: undersized"); r["verdict"] = "does not fit"; return r
    need_h = n["required_head_m"]
    if h < need_h:
        r["issues"].append(f"undersized: {h:.1f} m at duty < {need_h} m needed ({cite('HS4-PMIN')})")
    if h > need_h * (1 + OVERSIZE):
        r["issues"].append(f"oversized: {h:.0f} m available at duty vs {need_h} m needed")
    if n.get("geometric_height_m") is not None:
        bottom = mains_m + (need_h if variable else set_curve[0][1]) - 1.5
        pmax = param("HS4-PMAX", "p_max_m")
        if variable:
            fault = mains_m + set_curve[0][1] - 1.5
            if fault > pmax:
                r["info"].append(f"only if the controller fails at full speed: ground floor up to {fault:.0f} m")
        elif bottom > pmax:
            r["issues"].append(f"fixed speed: ground floor up to {bottom:.0f} m at low flow > {pmax} m ({cite('HS4-PMAX')})")
    if pumps < param("HS4-SET-TYPE", "min_pumps"):
        r["issues"].append(f"fewer than 2 pumps ({cite('HS4-SET-TYPE')})")
    elif h_out is None or h_out < need_h:
        r["issues"].append("duty not met with one pump out of service: no real standby")
    else:
        r["info"].append(f"standby OK: {h_out - need_h:.1f} m margin with one pump out")
    r["verdict"] = "fits" if not r["issues"] else "does not fit"
    return r


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--flats", type=int); ap.add_argument("--floors", type=int)
    ap.add_argument("--method", choices=["din", "une"], default="din")
    ap.add_argument("--mains-m", type=float, default=param("HS4-HEAD", "default_mains_m"),
                    help="subtract only for direct suction (default 0 = break tank)")
    ap.add_argument("--suction-m", type=float, default=0.0, help="Ha: tank low level below pump (+)")
    ap.add_argument("--duty-flow", type=float); ap.add_argument("--duty-head", type=float)
    ap.add_argument("--submitted"); ap.add_argument("--submitted-curve")
    ap.add_argument("-k", type=int, default=3)
    a = ap.parse_args()
    n = need(a)
    out = {"1_need": n}
    cv, meta = catalogue()
    if a.submitted:
        m = meta[a.submitted]
        out["2_judge"] = judge(a.submitted, cv[a.submitted], int(m["n_pumps"]), n, a.mains_m,
                               round(float(m["p2_kw_each"]) * int(m["n_pumps"]), 2), m["mei"])
    if a.submitted_curve:
        pc = package_curves(a.submitted_curve)
        set_c = pc.get("2 pumps running") or pc["1 pump running"]
        out["2_judge"] = judge(a.submitted_curve, set_c, 2 if "2 pumps running" in pc else 1, n, a.mains_m,
                               one_out_curve=pc.get("1 pump running"))
        out["2_judge"]["source"] = "curve read from the Grundfos data sheet vector drawing (data/raw/curves_package_IS15.csv)"
    fits = [r for k in cv for r in [judge(k, cv[k], int(meta[k]["n_pumps"]), n, a.mains_m,
                                          round(float(meta[k]["p2_kw_each"]) * int(meta[k]["n_pumps"]), 2),
                                          meta[k]["mei"])] if r["verdict"] == "fits"]
    fits.sort(key=lambda r: (r["kw_total"], r["head_at_need_m"]))
    if a.k:
        out["3_suggest"] = fits[:a.k] or "nothing in the catalogue fits"
    print(json.dumps(out, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
