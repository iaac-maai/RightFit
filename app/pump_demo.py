"""The pump demo of the PoC, as in the midterm video: package check, booster sizing and standby test.

Every number comes from the dataset kit in checks/pumps/: rules quoted from the CTE and EU law
(rules/rules.json), 289 Lowara booster sets with their catalogue curves, and the package's own
readings and Grundfos curve in checks/pumps/data/raw/ (confidential, git-ignored, on the laptop only).
"""
import csv
import hashlib
import io
import re
import sys
from pathlib import Path
from types import SimpleNamespace

from pypdf import PdfReader

KIT = Path(__file__).resolve().parents[1] / "checks/pumps"
RAW = KIT / "data/raw"
sys.path.insert(0, str(KIT / "scripts"))
import booster_check as booster  # noqa: E402
import product_rules_check as product_rules  # noqa: E402
from rules import RULES, cite  # noqa: E402

PUMP_TYPE = {"MS-H": "multistage", "MS-V": "multistage", "submersible_drainage": "submersible",
             "submersible_wastewater": "submersible"}
UPLOADS = {}   # token -> bytes of an uploaded file, in memory for this server run only
STANDBY_MODEL = "Hydro Multi-E 2 CME 15-2"


def package_files(pkg):
    return {d["file"] for d in pkg["documents"]} | {pkg["form"]["source"]}


def _keys(name):
    """A file name reduced to what survives renaming: its letters and digits, and its product numbers."""
    flat = re.sub(r"[^a-z0-9]", "", name.lower())
    return {flat} | set(re.findall(r"\d{6,}", name))


def identify(names, packages):
    """The package whose files were uploaded: the one sharing most files (same name or product number), or None."""
    score = {k: sum(bool(_keys(n) & set().union(*map(_keys, package_files(p)))) for n in names) for k, p in packages.items()}
    best = max(score, key=score.get, default=None)
    return best if best and score[best] else None


def keep(data):
    """Hold an uploaded file in memory so its pages can be read one file at a time."""
    token = hashlib.sha256(data).hexdigest()[:16]
    UPLOADS[token] = data
    while sum(map(len, UPLOADS.values())) > 300_000_000:
        UPLOADS.pop(next(iter(UPLOADS)))
    return token


def read_pages(data, page=None):
    """Read the text of one page (1, 2, ...) or of every page of a PDF; returns the page count and characters read."""
    reader = PdfReader(io.BytesIO(data))
    pages = reader.pages if page is None else [reader.pages[int(page) - 1]] if int(page) >= 1 else []
    if page is not None and not pages:
        raise IndexError("page numbers start at 1")
    return len(reader.pages), sum(len(p.extract_text() or "") for p in pages)


def booster_sets():
    """The catalogue sets for the input list: model, maker, pumps and total power."""
    _, meta = booster.catalogue()
    return [{"model": m, "maker": r["maker"], "pumps": int(r["n_pumps"]),
             "kw": round(float(r["p2_kw_each"]) * int(r["n_pumps"]), 1)} for m, r in sorted(meta.items())]


def page_count(data):
    """Pages of an uploaded PDF, or None when the file is not a PDF (the .xls form, for example)."""
    try:
        return len(PdfReader(io.BytesIO(data)).pages)
    except Exception:
        return None


def short_reason(rule, detail, pump_type):
    if rule == "PUMP-MEI":
        return PUMP_TYPE.get(pump_type, pump_type or "out of scope")
    return "PM motor" if "permanent_magnet" in (detail or "") else detail


def package_check(pkg):
    """CE-01 (a declaration names the pump), PUMP-MEI and MOTOR-IE for each pump, only where each rule applies."""
    doc_no = {d["file"]: n for n, d in enumerate(pkg["documents"], 1)}
    declarations = list(csv.DictReader(open(RAW / "declarations_package_IS15.csv")))
    pumps = []
    for p, results in product_rules.evaluate(RAW / "products_package_IS15.csv", RAW / "declarations_package_IS15.csv"):
        rules = {}
        for rule, verdict, detail, decl in results:
            rules[rule] = {"verdict": verdict, "detail": detail,
                           "label": detail if rule == "CE-01" else short_reason(rule, detail, p.get("pump_type")),
                           "doc": doc_no.get(decl)}
        kind = ("booster set" if p["category"] == "booster_set" else p["pump_type"].split("_", 1)[1]
                if (p.get("pump_type") or "").startswith("submersible_") else p["category"].replace("_", " "))
        pumps.append({"model": p["model"], "category": kind,
                      "datasheet": doc_no.get(p["source_file"]), "datasheet_file": p["source_file"], "rules": rules})
    named = {r["rules"]["CE-01"]["detail"] for r in pumps if r["rules"].get("CE-01", {}).get("verdict") == "pass"}
    unused = [{"file": d["file"], "doc": doc_no.get(d["file"]), "names": d["declared_products"].split(";")}
              for d in declarations if not set(d["declared_products"].split(";")) & named]
    missing = sum(r["rules"].get("CE-01", {}).get("verdict") == "fail" for r in pumps)
    return {"form": pkg["form"]["form_no"], "pumps": pumps, "missing": missing, "unused_declarations": unused,
            "declarations": [{"file": d["file"], "doc": doc_no.get(d["file"]), "names": d["declared_products"].split(";"),
                              "source": d["text_source"]} for d in declarations],
            "pages": sum(d["pages"] for d in pkg["documents"]),
            "documents": [{"no": n, "file": d["file"], "pages": d["pages"]} for n, d in enumerate(pkg["documents"], 1)],
            "rule": {"id": "CE-01", "source": RULES["CE-01"]["source"].split(" (")[0], "rule": RULES["CE-01"]["rule"],
                     "quote": RULES["CE-01"]["quote"]}}


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
            "sets": len(curves), "models": sorted(curves), "curves": {m: curves[m] for m in shown},
            "catalogue": meta[next(iter(meta))]["source_url"], "rules": [cite("HS4-HEAD"), cite("HS4-PMIN")]}


def standby_view(pkg, model=STANDBY_MODEL):
    """Does one pump alone still give the duty? Curves read from the Grundfos data sheet's vector drawing."""
    item = next(i for i in pkg["items"] if i["model"].startswith(model))
    q, h = item["values"]["duty_flow"]["value"], item["values"]["duty_head"]["value"]
    n = booster.need(SimpleNamespace(duty_flow=q, duty_head=h))
    pc = booster.package_curves(model)
    r = booster.judge(model, pc["2 pumps running"], 2, n, 0.0, one_out_curve=pc["1 pump running"])
    one = r["head_one_pump_out_m"]
    rows = [row for row in csv.DictReader(open(RAW / "curves_package_IS15.csv")) if row["model"] == model]
    doc_no = {d["file"]: n for n, d in enumerate(pkg["documents"], 1)}
    return {"model": model, "duty_flow": q, "duty_head": h, "duty_source": item["values"]["duty_flow"]["source"],
            "two": pc["2 pumps running"], "one": pc["1 pump running"], "points": len(rows),
            "head_two": r["head_at_need_m"], "head_one": one,
            "margin_m": None if one is None else round(one - h, 1),
            "margin_pct": None if one is None else round(100 * (one - h) / h, 1),
            "standby": one is not None and one >= h,
            "datasheet": doc_no.get(rows[0]["source_file"]), "page": int(rows[0]["page"])}
