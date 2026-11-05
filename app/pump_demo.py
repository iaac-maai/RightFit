"""The pump demo of the PoC: package check, booster sizing and standby test, as in the team's recording.

The package check and the standby test read the uploaded files themselves:
- the text of every page, with OCR for scanned pages (Tesseract);
- the pumps from their data sheets (the kit's extract_datasheet field patterns);
- the products each declaration names;
- the Q-H curves from the data sheet's vector drawing (the kit's digitize_grundfos_curve).
The rules and their scope come from the dataset kit in checks/pumps/ (rules/rules.json); booster sizing
uses its 289 Lowara sets with their catalogue curves. Nothing is read from earlier results.
"""
import hashlib
import io
import re
import shutil
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace

import pymupdf
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
KIT = ROOT / "checks/pumps"
sys.path.insert(0, str(KIT / "scripts"))
import booster_check as booster  # noqa: E402
import digitize_grundfos_curve as digitize  # noqa: E402
import extract_datasheet  # noqa: E402
from product_rules_check import IE, norm, required_ie  # noqa: E402
from rules import RULES, applies, cite, param  # noqa: E402

UPLOADS = {}   # token -> {"name", "data"}: the uploaded files, in memory for this server run only
TEXTS = {}     # (token, page) -> (text, how it was read: "text", "ocr" or "scan")
READERS = {}
OCR = shutil.which("tesseract") is not None
CURVES = ["1 pump running", "2 pumps running", "3 pumps running", "4 pumps running"]
PUMP_TYPE = {"MS-H": "multistage", "MS-V": "multistage", "submersible_drainage": "submersible",
             "submersible_wastewater": "submersible"}
# shortcut: only the English sentence of the declaration is parsed; Grundfos prints it in every declaration (GB).
# Other makers' wording needs its own pattern here.
DECLARES = re.compile(r"declare under our sole responsibility that the products?\s+(.+?),?\s+to which", re.I | re.S)


def keep(name, data):
    """Hold an uploaded file in memory so its pages can be read one at a time."""
    token = hashlib.sha256(data).hexdigest()[:16]
    UPLOADS[token] = {"name": name, "data": data}
    while sum(len(u["data"]) for u in UPLOADS.values()) > 300_000_000:
        UPLOADS.pop(next(iter(UPLOADS)))
    return token


def page_count(data):
    """Pages of a PDF, or None when the file is not a PDF (the .xls form, a text note)."""
    if b"%PDF-" not in data[:1024]:   # pymupdf would open a text file as a document of its own
        return None
    try:
        return pymupdf.open(stream=data, filetype="pdf").page_count
    except Exception:
        return None


def read_page(token, page):
    """The text of one page (1, 2, ...): its text layer, or OCR when the page is a scan."""
    key = (token, page)
    if key not in TEXTS:
        data = UPLOADS[token]["data"]
        doc = pymupdf.open(stream=data, filetype="pdf")
        if not 1 <= page <= doc.page_count:
            raise IndexError(f"page {page} is outside the file")
        try:
            if token not in READERS:
                READERS[token] = PdfReader(io.BytesIO(data))
            text = READERS[token].pages[page - 1].extract_text() or ""
        except Exception:   # a damaged file pypdf cannot parse: pymupdf reads what it can repair
            text = doc[page - 1].get_text()
        how = "text"
        if len(text.strip()) < 20:
            how = "scan"
            if OCR:
                import pytesseract
                from PIL import Image
                pix = doc[page - 1].get_pixmap(dpi=300)
                text = pytesseract.image_to_string(Image.frombytes("RGB", (pix.width, pix.height), pix.samples), lang="eng")
                how = "ocr"
        TEXTS[key] = (text, how)
    return TEXTS[key]


def classify(text):
    low = text.lower()
    if re.search(r"nr\. produs|product no", low) and re.search(r"cant\. descriere|qty\. description", low):
        return "data sheet"
    if re.search(r"declaration of conformity|declara[tţț]ie de conformitate|declaraci[oó]n de conformidad", low):
        return "declaration"
    return "other" if text.strip() else "unreadable"


def declared(pages):
    """The products a declaration names, and the page that names them."""
    for number, (text, _) in enumerate(pages, 1):
        m = DECLARES.search(text)
        if m:
            items = [i.strip() for i in re.split(r",|\band\b", re.sub(r"\s+", " ", m.group(1))) if i.strip()]
            brand = items[0].split()[0] if " " in items[0] else ""   # "Unilift AP, APB, KP": APB and KP are Unilift too
            return [items[0]] + [i if " " in i or not brand else f"{brand} {i}" for i in items[1:]], number
    return [], None


def scope(row, text):
    """Classify a pump for the rules' scope from the words of its own data sheet. To confirm with Luca."""
    low = text.lower()
    sub = "submersib" in low
    row["submersible"] = sub
    row["category"] = ("booster_set" if row.get("model", "").startswith("Hydro") or "grupul de pompare" in low or "booster" in low
                       else "drainage_pump" if re.search(r"drenaj|drainage|ape uzate|wastewater|sewage", low) else "pump")
    row["pump_type"] = (("submersible_wastewater" if re.search(r"ape uzate|wastewater|sewage", low) else "submersible_drainage")
                        if sub else "MS-H" if re.search(r"\bCME\b", text) else None)   # Grundfos CME: horizontal multistage
    row["motor_type"] = "permanent_magnet" if re.search(r"magne\w* permanen|permanent[- ]magnet", low) else None
    row["speed"] = "variable" if re.search(r"convertizor de frecven|frequency converter", low) else "fixed"
    return row


def rules_for(p, families):
    """CE-01, PUMP-MEI and MOTOR-IE for one pump, each only where it applies; '?' only when it cannot be decided."""
    out = {}
    hit = next(((f, file) for nf, f, file in families if norm(p.get("model", "")).startswith(nf)), None)
    out["CE-01"] = {"verdict": "pass" if hit else "fail", "label": hit[0] if hit else None, "file": hit[1] if hit else None,
                    "detail": f"named as {hit[0]} in {hit[1]}" if hit else "no declaration in the package names this model"}
    mei = p.get("mei")
    mei_ok = mei not in (None, "") and float(mei) >= param("PUMP-MEI", "mei_min")
    s = applies("PUMP-MEI", p)
    if s is False:
        out["PUMP-MEI"] = {"verdict": "n/a", "label": PUMP_TYPE.get(p["pump_type"], p["pump_type"]),
                           "detail": f"{p['pump_type']} is not one of {RULES['PUMP-MEI']['applies_to']['pump_type']}"}
    elif s or mei_ok:
        out["PUMP-MEI"] = {"verdict": "pass" if mei_ok else "fail", "label": f"MEI {mei or 'not stated'}",
                           "detail": f"MEI {mei or 'not stated'}, minimum {param('PUMP-MEI', 'mei_min')}"}
    else:
        out["PUMP-MEI"] = {"verdict": "?", "label": "pump type not stated", "detail": "the data sheet does not say the pump type"}
    req = required_ie(float(p.get("p2_kw") or 0))
    have = p.get("ie_class") or ""
    ie_ok = bool(req) and IE.get(have, 0) >= IE[req]
    if p.get("submersible"):
        out["MOTOR-IE"] = {"verdict": "n/a", "label": "submersible", "detail": "submersible motors are outside the rule"}
    elif p.get("motor_type") == "permanent_magnet":
        out["MOTOR-IE"] = {"verdict": "n/a", "label": "PM motor", "detail": "permanent-magnet motor, not induction"}
    elif ie_ok:
        out["MOTOR-IE"] = {"verdict": "pass", "label": have, "detail": f"{have} meets {req} for {p.get('p2_kw')} kW, whatever the motor type"}
    elif req:
        out["MOTOR-IE"] = {"verdict": "?", "label": "motor type not stated", "detail": f"has {have or 'no class'}, {req} needed if induction"}
    else:
        out["MOTOR-IE"] = {"verdict": "?", "label": "power not stated", "detail": "the data sheet states no motor power in the rule's bands"}
    return out


def standby(p):
    """Does one pump fewer still give the duty? The curves are read from the data sheet's vector drawing."""
    doc = pymupdf.open(stream=UPLOADS[p["token"]]["data"], filetype="pdf")
    for number, page in enumerate(doc, 1):
        try:
            found = digitize.curves(page)
        except Exception:   # a page without a chart has no axes to calibrate
            continue
        if found:
            break
    else:
        return {"error": f"No pump curve found in the drawing of {p['source_file']}."}
    curves = {CURVES[i]: c[::max(1, len(c) // 40)] + [c[-1]] for i, c in enumerate(found[:4])}
    pumps = len(curves)
    q, h = float(p["flow_m3h"]), float(p["head_m"])
    n = booster.need(SimpleNamespace(duty_flow=q, duty_head=h))
    full, less = curves[CURVES[pumps - 1]], curves[CURVES[pumps - 2]] if pumps > 1 else None
    r = booster.judge(p["model"], full, pumps, n, 0.0, one_out_curve=less)
    one = r["head_one_pump_out_m"]
    return {"model": p["model"], "file": p["source_file"], "token": p["token"], "page": number, "pumps": pumps,
            "duty_flow": q, "duty_head": h, "all": full, "less": less, "points": sum(map(len, curves.values())),
            "head_all": r["head_at_need_m"], "head_less": one,
            "margin_m": None if one is None else round(one - h, 1),
            "margin_pct": None if one is None else round(100 * (one - h) / h, 1),
            "standby": one is not None and one >= h}


def form_number(name, data):
    """The form number, when the MAF form (.xls) is among the uploads."""
    from ingest.maf_form import read_form
    with tempfile.NamedTemporaryFile(suffix=Path(name).suffix) as f:
        f.write(data)
        f.flush()
        try:
            return read_form(f.name)["form_no"]
        except Exception:
            return None


def analyse(tokens):
    """Read every uploaded file and run the product rules on what they say."""
    files, pumps, decls, form = [], [], [], None
    for token in tokens:
        up = UPLOADS.get(token)
        if up is None:
            raise KeyError("an upload is no longer in memory; upload the package again")
        n = page_count(up["data"])
        if n is None:
            number = form_number(up["name"], up["data"]) if up["name"].lower().endswith(".xls") else None
            form = number or form
            files.append({"name": up["name"], "token": token, "pages": None, "kind": "form" if number else "not a PDF"})
            continue
        pages = [read_page(token, number) for number in range(1, n + 1)]
        text = "\n".join(t for t, _ in pages)
        hows = {h for _, h in pages}
        kind = classify(text)
        files.append({"name": up["name"], "token": token, "pages": n, "kind": kind,
                      "read": "OCR" if "ocr" in hows else "scan, not read" if hows == {"scan"} else "text"})
        if kind == "data sheet":
            row = scope(extract_datasheet.fields(text, up["name"]), text)
            row["token"] = token
            pumps.append(row)
        elif kind == "declaration":
            names, page = declared(pages)
            decls.append({"file": up["name"], "token": token, "names": names, "page": page,
                          "read": "OCR" if "ocr" in hows else "text"})
    families = [(norm(f), f, d["file"]) for d in decls for f in d["names"]]
    for p in pumps:
        p["rules"] = rules_for(p, families)
    named = {p["rules"]["CE-01"]["label"] for p in pumps if p["rules"]["CE-01"]["verdict"] == "pass"}
    booster_set = next((p for p in pumps if p["category"] == "booster_set" and p.get("flow_m3h") and p.get("head_m")), None)
    return {"form": form, "files": files, "pages": sum(f["pages"] or 0 for f in files), "pumps": pumps,
            "declarations": decls, "missing": sum(p["rules"]["CE-01"]["verdict"] == "fail" for p in pumps),
            "unused": [d for d in decls if d["names"] and not set(d["names"]) & named],
            "unread": [d for d in decls if not d["names"]] + [f for f in files if f["kind"] == "unreadable"],
            "rule": {"id": "CE-01", "source": RULES["CE-01"]["source"].split(" (")[0], "rule": RULES["CE-01"]["rule"],
                     "quote": RULES["CE-01"]["quote"]},
            "standby": standby(booster_set) if booster_set else None}


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
