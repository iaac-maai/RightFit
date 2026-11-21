"""Booster set sizing, as the Booster sizing screen shows it: the need of a building (DIN 1988-300 flow, CTE HS4
head), the submitted set judged on its real curve, and the catalogue sets that fit, lowest power first. Plain Python
on the dataset kit in checks/pumps, with no PDF reading, so the laptop's app (app/pump_demo.py) and the engine of
RightFit online (web/engine/) run the same code.
"""
import sys
from pathlib import Path
from types import SimpleNamespace

KIT = Path(__file__).resolve().parents[1] / "checks/pumps"
sys.path.insert(0, str(KIT / "scripts"))
import booster_check as booster  # noqa: E402
from rules import cite  # noqa: E402


def booster_sets():
    """The catalogue sets for the input list: model, maker, pumps and total power."""
    _, meta = booster.catalogue()
    return [{"model": m, "maker": r["maker"], "pumps": int(r["n_pumps"]),
             "kw": round(float(r["p2_kw_each"]) * int(r["n_pumps"]), 1)} for m, r in sorted(meta.items())]

def booster_view(flats, floors, submitted=None, mains_m=0.0, k=3):
    """1 calculates the need (DIN 1988-300 flow, CTE HS4 head), 2 judges the submitted set on its real curve,
    3 suggests the sets that fit from the Lowara catalogue, lowest power first."""
    if not (1 <= flats <= 500 and 1 <= floors <= 60 and 0 <= mains_m <= 100):
        raise ValueError("flats 1-500, floors 1-60 and mains pressure 0-100 m")
    n = booster.need(SimpleNamespace(flats=flats, floors=floors, method="din", mains_m=mains_m, suction_m=0.0,
                                     duty_flow=None, duty_head=None))
    curves, meta = booster.catalogue()

    def judged(model):
        m = meta[model]
        return booster.judge(model, curves[model], int(m["n_pumps"]), n, mains_m,
                             round(float(m["p2_kw_each"]) * int(m["n_pumps"]), 2), m["mei"])

    fits = sorted((r for r in map(judged, curves) if r["verdict"] == "fits"),
                  key=lambda r: (r["kw_total"], r["head_at_need_m"]))[:k]
    sub = judged(submitted) if submitted in curves else None
    shown = [m for m in [submitted, *(r["model"] for r in fits[:1])] if m in curves]
    return {"need": n, "submitted": sub, "unknown_submitted": bool(submitted) and sub is None, "suggest": fits,
            "sets": len(curves), "curves": {m: curves[m] for m in shown},
            "catalogue": meta[next(iter(meta))]["source_url"], "rules": [cite("HS4-HEAD"), cite("HS4-PMIN")]}
