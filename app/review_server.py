"""RightFit, the application: a small web server that uses only the standard library.

Run from the repository root:  python app/review_server.py   then open http://127.0.0.1:8520

The screens are in app/review/. They ask this server for the review of a package. The server runs the
deterministic checks and saves the reviewer's confirmations and decisions into the package files.
It only listens on this computer (127.0.0.1).
"""
import argparse
import csv
import json
import re
import sys
import traceback
from datetime import date, timedelta
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

import pymupdf

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from checks.maf.checks import DOC_LABELS, context, run_all  # noqa: E402
from checks.maf.rules import CHAINS, load, tables  # noqa: E402
from checks.maf.status import LABELS, draft_status  # noqa: E402
from explain.maf_comments import comment, title  # noqa: E402
from app import pump_demo  # noqa: E402

PAGE = Path(__file__).with_name("review")
RAW = ROOT / "data/raw"   # the original PDFs, on the laptop only (git-ignored)
# shortcut: one reviewer name for every confirmation; add a login when more reviewers use it.
REVIEWER = "Luca"
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
DISCIPLINES = {"IS": "Plumbing", "IT": "Heating", "IV": "HVAC", "IE": "Electrical", "ICS": "Low current"}


def value_name(key):
    return VALUE_NAMES.get(key, key.replace("_", " ").capitalize())


def key_of(r):
    """A stable name for one check result: the reviewer's decision on it is saved under this name."""
    return "|".join(str(x) for x in (r["check"], r["item"], r["doc"], ",".join(r["rules"]), r["code"]))


def rule_info(rule_id, status, rules, checklist):
    """One rule or checklist item in plain fields, for the reviewer who asks what a finding rests on."""
    if rule_id in rules:
        r = rules[rule_id]
        return {"id": rule_id, "status": status, "text": r["requirement"], "source": " ".join(x for x in (r["code"], r["clause"]) if x),
                "url": r["source_url"]}
    item = checklist.get(rule_id, {})
    return {"id": rule_id, "status": status, "text": item.get("item", ""), "source": "Past reviewers' comments", "url": ""}


def rules_for_location(location):
    """The rules RightFit checks for a location: EU rules, the country's rules and reviewers' practice."""
    return [{k: r[k] for k in ("rule_id", "jurisdiction", "code", "clause", "requirement", "applies_to", "source_url",
                               "status", "verified_on")}
            for r in load("rules.csv") if r["jurisdiction"] in CHAINS[location]]


def review(pkg, location="RO", review_date=None, delivery_date=None, dismissed=None):
    """Everything the page shows for one package. dismissed maps a result key to the reviewer's reason."""
    form = pkg["form"]
    review_date = review_date or date.fromisoformat(form["date"])
    delivery_date = delivery_date or review_date + timedelta(weeks=form["delivery_weeks"] or 0)
    dismissed = dismissed or {}
    results = run_all(pkg, context(location, review_date, delivery_date))
    for r in results:
        r["key"] = key_of(r)
        r["title"] = title(r) or CHECK_NAMES[r["check"]]   # before a dismissal turns the result into a pass
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
    rule_table, _, checklist_rows = tables()
    checklist = {row["id"]: row for row in checklist_rows}

    def evidence(r):
        """What the AI read on the pages a result points to, for its product."""
        out = []
        for i in pkg["items"]:
            if r["item"] not in (None, i["id"]):
                continue
            for k, x in i["values"].items():
                if f"{x['source']}, p. {x['page']}" in r["sources"]:
                    out.append({"item": i["id"], "key": k, "what": value_name(k), "value": x["value"], "unit": x["unit"], "source": x["source"],
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
            "key": r["key"], "check": r["check"], "check_name": CHECK_NAMES[r["check"]], "title": r["title"],
            "item": r["item"],
            "product": item_label.get(r["item"]), "doc": r["doc"], "doc_no": doc_no.get(r["doc"]),
            "verdict": r["would_be"], "confirmed": r["result"] == r["would_be"], "reason": r["reason"],
            "sources": r["sources"],
            "rules": [rule_info(i, r["rule_status"].get(i, "checklist"), rule_table, checklist) for i in r["rules"]],
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


def open_pdf(source):
    """A PDF from a path on this laptop, or from the bytes of an upload."""
    return pymupdf.open(source) if isinstance(source, Path) else pymupdf.open(stream=source, filetype="pdf")


def page_png(source, page, dpi=130):
    """One page of a PDF as a PNG for the document pane, or None when the file has no such page or is not a PDF."""
    try:
        doc = open_pdf(source)
    except Exception:   # an upload that is not a PDF, or a damaged file
        return None
    return doc[page - 1].get_pixmap(dpi=dpi).tobytes("png") if 1 <= page <= doc.page_count else None


def locate(page, quote):
    """Where one quote sits on a PDF page. PDF text often splits 'label: value' into two blocks, so a quote that
    is not found whole is looked up as its label with the value on the same line, then by its first words."""
    found = page.search_for(quote)
    if found:
        return found
    label, _, value = quote.partition(":")
    if value.strip():
        for a in page.search_for(label.strip()):
            same_line = [b for b in page.search_for(value.strip()) if abs(b.y0 - a.y0) < 4 and b.x0 >= a.x0]
            if same_line:
                return [a | same_line[0]]
    return page.search_for(" ".join(quote.split()[:4])) if len(quote.split()) > 4 else []


def one_band_per_line(rects):
    """Pieces of one quote that sit on the same line become one band, from the label across to the value."""
    lines = []
    for r in sorted(rects, key=lambda r: (round(r.y0), r.x0)):
        if lines and abs(lines[-1].y0 - r.y0) < 4:
            lines[-1] = lines[-1] | r
        else:
            lines.append(r)
    return lines


def find_marks(source, page, quotes):
    """For each quote, its rectangles on the page in percent of the page; none on a scan, which has no text."""
    doc = open_pdf(source)
    if not 1 <= page <= doc.page_count:
        return [[] for _ in quotes]
    p = doc[page - 1]
    w, h = p.rect.width, p.rect.height
    return [[[round(r.x0 / w * 100, 2), round((r.y0 - 1.5) / h * 100, 2), round(r.width / w * 100, 2), round((r.height + 3) / h * 100, 2)]
             for r in one_band_per_line(locate(p, q))] for q in quotes]


def package_list(data, raw=RAW):
    """Every package the application knows: those RightFit has read, then those on this laptop still to be read."""
    out = []
    for path in sorted(data.glob("P*.json")):
        pkg = json.loads(path.read_text())
        v = review(pkg)
        out.append({"id": path.stem, "form_no": pkg["form"]["form_no"], "revision": pkg["form"]["revision"],
                    "discipline": DISCIPLINES.get(pkg["form"]["form_no"].split()[0], ""), "items": [i["name"] for i in pkg["items"]],
                    "files": len(pkg["documents"]) + 1, "pages": sum(d["pages"] for d in pkg["documents"]),
                    "letter": v["status"]["letter"], "label": v["status"]["label"], "problems": v["counts"]["problems"],
                    "questions": v["counts"]["questions"], "to_confirm": v["counts"]["to_confirm"], "readings": v["counts"]["readings"]})
    read = {p["id"] for p in out}
    inventory = raw / "batch2_inventory.csv"
    if inventory.exists():
        with open(inventory, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):   # the zip column holds company names and never leaves this function
                if row["package"] not in read:
                    out.append({"id": row["package"], "form_no": row["code"], "revision": int(row["revision"]),
                                "discipline": row["discipline"][0].upper() + row["discipline"][1:], "items": [row["product"]],
                                "files": int(row["files"]), "pages": int(row["pdf_pages"]), "letter": None})
    return out


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

    def end_headers(self):
        if self.command == "GET" and self.path.startswith("/page/"):
            self.send_header("Cache-Control", "private, max-age=3600")   # a page of a PDF does not change
        elif self.command == "GET" and not self.path.startswith("/api/"):
            self.send_header("Cache-Control", "no-cache")   # a page changed on this laptop shows at the next reload
        super().end_headers()

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

    def send_png(self, png):
        if png is None:
            body = "That page is not available on this laptop.".encode()
            self.send_response(404)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
        else:
            body = png
            self.send_response(200)
            self.send_header("Content-Type", "image/png")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def packages(self):
        return {p.stem: p for p in sorted(self.data.glob("*.json"))}

    def do_GET(self):
        doc = re.fullmatch(r"/doc/([A-Za-z0-9_-]+)/(\d+)", self.path.split("?")[0])
        if doc:
            return self.send_original(doc.group(1), int(doc.group(2)))
        shown = re.fullmatch(r"/page/([A-Za-z0-9_-]+)/(\d+)/(\d+)\.png", self.path.split("?")[0])
        if shown:   # one page of an attachment; only files listed in the package, as for /doc/
            source = self.packages().get(shown.group(1))
            path = original(shown.group(1), json.loads(source.read_text()), int(shown.group(2))) if source else None
            return self.send_png(page_png(path, int(shown.group(3))) if path else None)
        shown = re.fullmatch(r"/upload/([0-9a-f]{16})/(\d+)\.png", self.path.split("?")[0])
        if shown:   # one page of an upload that is still in memory
            f = pump_demo.UPLOADS.get(shown.group(1))
            return self.send_png(page_png(f["data"], int(shown.group(2))) if f else None)
        up = re.fullmatch(r"/upload/([0-9a-f]{16})", self.path.split("?")[0])
        if up:   # an uploaded file, back to the page that shows it
            f = pump_demo.UPLOADS.get(up.group(1))
            if f is None:
                return self.send_json({"error": "That upload is no longer in memory; upload the package again."}, 404)
            self.send_response(200)
            self.send_header("Content-Type", "application/pdf" if f["data"][:5] == b"%PDF-" else "application/octet-stream")
            self.send_header("Content-Length", str(len(f["data"])))
            self.end_headers()
            return self.wfile.write(f["data"])
        url = urlparse(self.path)
        if url.path == "/api/rules":
            location = parse_qs(url.query).get("location", ["RO"])[0]
            return self.send_json(rules_for_location(location if location in CHAINS else "RO"))
        if url.path != "/api/packages":
            return super().do_GET()
        self.send_json(package_list(self.data))

    def do_POST(self):
        try:
            size = int(self.headers.get("Content-Length", 0))
            if size > 60_000_000:
                return self.send_json({"error": "The file is larger than 60 MB."}, 413)
            raw = self.rfile.read(size)
            if self.path == "/api/upload":   # one file of the package, held in memory for this run only
                name = unquote(self.headers.get("X-File-Name", ""))
                return self.send_json({"name": name, "pages": pump_demo.page_count(raw), "token": pump_demo.keep(name, raw)})
            body = json.loads(raw or b"{}")
            if self.path == "/api/extract":   # read one page of an upload: its text, or OCR on a scan
                text, how = pump_demo.read_page(body["token"], int(body["page"]))
                return self.send_json({"chars": len(text), "read": how})
            if self.path == "/api/analyse":
                if not all(t in pump_demo.UPLOADS for t in body["tokens"]):   # the server was restarted since the upload
                    return self.send_json({"error": "The server was restarted and no longer has these files. "
                                                    "Add the package again."}, 410)
                return self.send_json(pump_demo.analyse(body["tokens"]))
            if self.path == "/api/pumps/sets":
                return self.send_json(pump_demo.booster_sets())
            if self.path == "/api/pumps/booster":
                return self.send_json(pump_demo.booster_view(int(body["flats"]), int(body["floors"]),
                                                             body.get("submitted") or None, float(body.get("mains_m") or 0)))
            path = self.packages().get(body.get("package"))   # only a package that exists, never a free path
            if path is None:
                return self.send_json({"error": "unknown package"}, 404)
            pkg = json.loads(path.read_text())
            if self.path == "/api/marks":   # where the quoted lines sit on one page of an attachment
                source = original(body["package"], pkg, int(body["no"]))
                return self.send_json({"marks": find_marks(source, int(body["page"]), body["quotes"]) if source else []})
            if self.path == "/api/load-local":   # the same files as an upload, taken from the originals on this laptop
                files = [(d["file"], original(body["package"], pkg, n)) for n, d in enumerate(pkg["documents"], 1)]
                form = (RAW / body["package"] / pkg["form"]["source"]).resolve()
                if form.is_relative_to((RAW / body["package"]).resolve()) and form.is_file():
                    files.append((form.name, form))
                return self.send_json([{"name": n, "pages": pump_demo.page_count(f.read_bytes()),
                                        "token": pump_demo.keep(n, f.read_bytes())} for n, f in files if f])
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
        except (KeyError, ValueError, StopIteration, TypeError, IndexError) as e:
            self.send_json({"error": f"{type(e).__name__}: {e}"}, 400)
        except Exception as e:   # an upload no library can read still gets an answer the page can show
            traceback.print_exc()
            self.send_json({"error": f"A file could not be read ({type(e).__name__}). Check it by eye."}, 500)


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
