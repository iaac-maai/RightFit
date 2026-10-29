"""RightFit review page for the PoC: a small web server that uses only the standard library.

Run from the repository root:  python app/review_server.py   then open http://127.0.0.1:8520

The page itself is in app/review/. It asks this server for the review of a package. The server runs
the same deterministic checks as the Streamlit page and saves the reviewer's confirmations and decisions
into the package files, as the Streamlit page does. It only listens on this computer (127.0.0.1).
"""
import argparse
import json
import re
import sys
from datetime import date, timedelta
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from checks.maf.checks import DOC_LABELS, context, run_all  # noqa: E402
from checks.maf.status import LABELS, draft_status  # noqa: E402
from explain.maf_comments import comment  # noqa: E402

PAGE = Path(__file__).with_name("review")
RAW = ROOT / "data/raw"   # the original PDFs, on the laptop only (git-ignored)
# shortcut: one reviewer name for every confirmation, as in app/maf_app.py; add a login when more reviewers use it.
REVIEWER = "Luca"
# shortcut: the same labels as app/maf_app.py; move both into one module if the two pages keep growing.
CHECK_NAMES = {"D1": "Required documents", "D2": "Declaration matches the products", "D3": "Certificate in date",
               "D4": "Attachment is what the form says", "V1": "Duty point", "V2": "Pressure rating",
               "E1": "Ecodesign", "C": "Reviewers' checklist", "R": "Delivery reminder"}
VALUE_NAMES = {"used_for": "Used for (form)", "duty_flow": "Required flow (form)", "duty_head": "Required head (form)",
               "duty_airflow_supply": "Required supply airflow (form)",
               "duty_airflow_extract": "Required extract airflow (form)", "flow": "Flow at the duty point",
               "head": "Head at the duty point", "power": "Motor power", "max_pressure": "Max working pressure",
               "controller_included": "Controller or panel included", "bms_included": "BMS module included",
               "bms_protocol": "BMS protocols", "hrs_type": "Heat recovery type",
               "hrs_efficiency": "Heat recovery efficiency", "sfp_int": "SFPint", "sfp_int_limit": "SFPint limit",
               "gwp": "GWP", "seer": "SEER", "scop": "SCOP", "dx_refrigerant": "DX coil refrigerant"}
DECISIONS = ("suggested", "accepted", "rejected")


def value_name(key):
    return VALUE_NAMES.get(key, key.replace("_", " ").capitalize())


def key_of(r):
    """A stable name for one check result, the same one the Streamlit page uses."""
    return "|".join(str(x) for x in (r["check"], r["item"], r["doc"], ",".join(r["rules"]), r["code"]))


def review(pkg, location="RO", review_date=None, delivery_date=None, dismissed=None):
    """Everything the page shows for one package. dismissed maps a result key to the reviewer's reason."""
    form = pkg["form"]
    review_date = review_date or date.fromisoformat(form["date"])
    delivery_date = delivery_date or review_date + timedelta(weeks=form["delivery_weeks"] or 0)
    dismissed = dismissed or {}
    results = run_all(pkg, context(location, review_date, delivery_date))
    for r in results:
        r["key"] = key_of(r)
        if r["key"] in dismissed:
            # A finding the reviewer marked "not a problem" counts as OK from here on, with the reason kept.
            r["result"] = r["would_be"] = "pass"
            r["dismissed"] = dismissed[r["key"]] or "no reason given"

    ai = pkg.get("ai_findings", [])
    accepted = [f for f in ai if f["status"] == "accepted"]
    letter, reasons = draft_status(results, "would_be", [f["title"] for f in accepted])
    comments = [comment(r) for r in results]
    rank = {"flag": 0, "unclear": 1}
    ordered = sorted(zip(results, comments), key=lambda rc: rank.get(rc[0]["would_be"], 2))   # stable: check order inside
    lines = list(dict.fromkeys([c for _, c in ordered if c] + [f["suggested_comment"] for f in accepted]))
    number = {line: n for n, line in enumerate(lines, 1)}   # the comment number in the answer, shown as a delta
    items = {i["id"]: i for i in pkg["items"]}
    item_label = {i["id"]: f"{i['name']} ({i['model']})" for i in pkg["items"]}

    def evidence(r):
        """What the AI read on the pages a result points to, for its product."""
        out = []
        for i in pkg["items"]:
            if r["item"] not in (None, i["id"]):
                continue
            for k, x in i["values"].items():
                if f"{x['source']}, p. {x['page']}" in r["sources"]:
                    out.append({"what": value_name(k), "value": x["value"], "unit": x["unit"], "source": x["source"],
                                "page": x["page"], "quote": x["quote"], "status": x["status"]})
        return out

    docs = []
    for n, d in enumerate(pkg["documents"], 1):
        docs.append({"no": n, "file": d["file"], "type": DOC_LABELS.get(d["doc_type"], d["doc_type"]),
                     "listed_as": d["listed_as"], "covers": d["covers"], "issuer": d["issuer"],
                     "issue_date": d["issue_date"], "valid_until": d["valid_until"], "pages": d["pages"],
                     "method": d["method"], "languages": d["languages"], "status": d["status"], "notes": d["notes"],
                     "matches": [{"item": m["item"], "product": item_label.get(m["item"], m["item"]), "kind": m["kind"],
                                  "page": m["page"], "quote": m["quote"], "status": m["status"]}
                                 for m in d.get("matches", [])]})
    doc_no = {d["file"]: d["no"] for d in docs}

    out_results = []
    for r, c in zip(results, comments):
        out_results.append({
            "key": r["key"], "check": r["check"], "check_name": CHECK_NAMES[r["check"]], "item": r["item"],
            "product": item_label.get(r["item"]), "doc": r["doc"], "doc_no": doc_no.get(r["doc"]),
            "verdict": r["would_be"], "confirmed": r["result"] == r["would_be"], "reason": r["reason"],
            "sources": r["sources"], "rules": [{"id": i, "status": r["rule_status"].get(i, "checklist")} for i in r["rules"]],
            "blocking": r["blocking"], "comment": c, "delta": number.get(c), "dismissed": r.get("dismissed"),
            "evidence": evidence(r)})

    readings = ([x for i in pkg["items"] for x in i["values"].values()] + pkg["documents"]
                + [m for d in pkg["documents"] for m in d.get("matches", [])])
    return {
        "package": pkg["package"], "location": location, "review": review_date.isoformat(),
        "delivery": delivery_date.isoformat(),
        "form": {k: form.get(k) for k in ("form_no", "revision", "date", "delivery_raw", "boq_ref")},
        "status": {"letter": letter, "label": LABELS[letter], "reasons": reasons},
        "counts": {"problems": sum(r["verdict"] == "flag" for r in out_results),
                   "questions": sum(r["verdict"] == "unclear" for r in out_results),
                   "passed": sum(r["result"] == "pass" and not r.get("dismissed") for r in results),
                   "would_pass": sum(r["would_be"] == "pass" and r["result"] != "pass" and not r.get("dismissed")
                                     for r in results),
                   "dismissed": sum(bool(r.get("dismissed")) for r in results),
                   "to_confirm": sum(x["status"] != "verified" for x in readings), "readings": len(readings),
                   "ai_to_decide": sum(f["status"] == "suggested" for f in ai)},
        "items": [{"id": i["id"], "name": i["name"], "brand": i["brand"], "model": i["model"],
                   "values": [{"key": k, "what": value_name(k), **x} for k, x in i["values"].items()]}
                  for i in items.values()],
        "documents": docs,
        "results": out_results,
        "ai_findings": [{**f, "products": [item_label.get(i, i) for i in f["items"]],
                         "delta": number.get(f["suggested_comment"]) if f["status"] == "accepted" else None}
                        for f in ai],
        "notes": pkg.get("notes_for_reviewer", []),
        "answer": {"lines": lines, "text": f"MAF {form['form_no']} rev {form['revision']}: {LABELS[letter]} ({letter})\n\n"
                   + ("\n".join(f"{n}. {line}" for n, line in enumerate(lines, 1)) or "No comments.")},
    }


def set_verified(entry, verified):
    """Mark a value, document or match as confirmed by the reviewer, or put it back to what the AI left."""
    if verified == (entry["status"] == "verified"):
        return
    has_value = entry.get("value") not in (None, "") if "value" in entry else True
    entry["status"] = "verified" if verified else ("extracted" if has_value else "unclear")
    entry["checked_by"] = REVIEWER if verified else None
    entry["verified_on"] = date.today().isoformat() if verified else None


def confirm(pkg, targets):
    """Apply the reviewer's ticks. Each target names a value (item, key), a document (file) or a match (file, item)."""
    docs = {d["file"]: d for d in pkg["documents"]}
    items = {i["id"]: i for i in pkg["items"]}
    for t in targets:
        if t["kind"] == "value":
            entry = items[t["item"]]["values"][t["key"]]
        elif t["kind"] == "document":
            entry = docs[t["file"]]
        elif t["kind"] == "match":
            entry = next(m for m in docs[t["file"]].get("matches", []) if m["item"] == t["item"])
        else:
            raise ValueError(f"unknown kind {t['kind']!r}")
        set_verified(entry, bool(t["verified"]))


def decide(pkg, finding_id, status, note=None):
    """Save the reviewer's decision on an AI suggestion: accepted, rejected, or back to suggested."""
    if status not in DECISIONS:
        raise ValueError(f"unknown decision {status!r}")
    finding = next(f for f in pkg["ai_findings"] if f["id"] == finding_id)
    finding["status"] = status
    finding["decided_by"] = None if status == "suggested" else REVIEWER
    finding["note"] = note or None


def original(name, pkg, no, raw=RAW):
    """The original PDF of attachment number `no` (1, 2, ...) of package `name`, or None when it is not on this laptop."""
    docs = pkg["documents"]
    if not 1 <= no <= len(docs):
        return None
    folder = (raw / name).resolve()
    path = (folder / docs[no - 1]["file"]).resolve()
    return path if path.is_relative_to(folder) and path.is_file() else None


def save(path, pkg):
    path.write_text(json.dumps(pkg, ensure_ascii=False, indent=2) + "\n")


def day(text):
    return date.fromisoformat(text) if text else None


class Handler(SimpleHTTPRequestHandler):
    data = ROOT / "data/maf/extracted"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(PAGE), **kwargs)

    def log_message(self, *args):
        pass

    def send_json(self, payload, code=200):
        body = json.dumps(payload, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def send_original(self, name, no):
        """Serve an attachment's original PDF so the reviewer can check the page; only files listed in the package."""
        source = self.packages().get(name)
        path = original(name, json.loads(source.read_text()), no) if source else None
        if path is None:
            body = "The original of this attachment is not on this laptop.".encode()
            self.send_response(404)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
        else:
            body = path.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "application/pdf" if path.suffix.lower() == ".pdf" else "application/octet-stream")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def packages(self):
        return {p.stem: p for p in sorted(self.data.glob("*.json"))}

    def do_GET(self):
        doc = re.fullmatch(r"/doc/([A-Za-z0-9_-]+)/(\d+)", self.path.split("?")[0])
        if doc:
            return self.send_original(doc.group(1), int(doc.group(2)))
        if self.path != "/api/packages":
            return super().do_GET()
        listing = []
        for name, path in self.packages().items():
            pkg = json.loads(path.read_text())
            listing.append({"id": name, "form_no": pkg["form"]["form_no"], "revision": pkg["form"]["revision"],
                            "items": [i["name"] for i in pkg["items"]]})
        self.send_json(listing)

    def do_POST(self):
        try:
            body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
            path = self.packages().get(body.get("package"))   # only a package that exists, never a free path
            if path is None:
                return self.send_json({"error": "unknown package"}, 404)
            pkg = json.loads(path.read_text())
            if self.path == "/api/confirm":
                confirm(pkg, body["targets"])
                save(path, pkg)
            elif self.path == "/api/decide":
                decide(pkg, body["id"], body["status"], body.get("note"))
                save(path, pkg)
            elif self.path != "/api/review":
                return self.send_json({"error": "unknown address"}, 404)
            self.send_json(review(pkg, body.get("location") or "RO", day(body.get("review")),
                                  day(body.get("delivery")), body.get("dismissed")))
        except (KeyError, ValueError, StopIteration, TypeError) as e:
            self.send_json({"error": f"{type(e).__name__}: {e}"}, 400)


def main():
    ap = argparse.ArgumentParser(description="RightFit review page")
    ap.add_argument("--port", type=int, default=8520)
    ap.add_argument("--data", type=Path, default=Handler.data, help="folder with the package files")
    args = ap.parse_args()
    Handler.data = args.data
    server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    print(f"RightFit review page: http://127.0.0.1:{args.port}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
