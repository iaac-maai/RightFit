"""RightFit, the application: a small web server that uses only the standard library.

Run from the repository root:  python app/review_server.py   then open http://127.0.0.1:8520

The screens are in app/review/. They ask this server for the review of a package. The server runs the
deterministic checks, saves the reviewer's confirmations and decisions on AI suggestions into the package files,
and keeps the decisions on findings (kept in the answer, or not a problem) in the project folder.
It only listens on this computer (127.0.0.1).
"""
import argparse
import csv
import json
import os
import re
import sys
import threading
import traceback
from datetime import date
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

import pymupdf

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from checks.maf.checks import DOC_LABELS, KINDS  # noqa: E402
from checks.maf.rules import CHAINS, load  # noqa: E402
from app import ai, pump_demo  # noqa: E402
from app import review_core as core  # noqa: E402
from app.review_core import (CHECK_NAMES, CONSULTANT, CONSULTANT_FIELDS, DECISIONS, FINDINGS, VALUE_NAMES,  # noqa: E402,F401
                             key_of, new_consultant_rule, review, rule_info, value_name)
from ingest.boq import find_line, read_boq, sheets_for  # noqa: E402

PAGE = Path(__file__).with_name("review")
RAW = ROOT / "data/raw"   # the original PDFs, on the laptop only (git-ignored)
# shortcut: one reviewer name for every confirmation; add a login when more reviewers use it.
REVIEWER = "Luca"   # kept next to every confirmation and decision; --reviewer "Name" when someone else reviews
LOCAL = {"127.0.0.1", "localhost"}   # the only hosts the app answers (local_request)
DISCIPLINES = {"IS": "Plumbing", "IT": "Heating", "IV": "HVAC", "IE": "Electrical", "ICS": "Low current"}












def write_consultant_rules(rows):
    tmp = CONSULTANT.with_name(CONSULTANT.name + ".tmp")   # written whole, then put in place, as in save()
    with open(tmp, "w", newline="", encoding="utf-8") as f:   # CRLF, like the other tables
        w = csv.DictWriter(f, fieldnames=CONSULTANT_FIELDS, lineterminator="\r\n")
        w.writeheader()
        w.writerows(rows)
    os.replace(tmp, CONSULTANT)


def consultant_screen():
    """What the Rules screen needs to list the consultant's rules and offer a form for a new one."""
    return {"rules": load(CONSULTANT.name), "kinds": list(KINDS), "doc_types": DOC_LABELS, "values": VALUE_NAMES,
            "families": sorted({f for r in load("family_documents.csv") for f in r["family"].split(";")} - {"all"})}


def rules_for_location(location):
    """The rules RightFit checks for a location: EU rules, the country's rules and reviewers' practice."""
    return [{k: r[k] for k in ("rule_id", "jurisdiction", "code", "clause", "requirement", "applies_to", "source_url",
                               "status", "verified_on", "valid_from", "valid_to")}
            for r in load("rules.csv") if r["jurisdiction"] in CHAINS[location]]


# The project's BOQ files (spec section 6, check Q). They hold prices: data/raw is git-ignored, prices are never read.
BOQ_DIR = RAW / "boq"
_boq_lines = {}

# Projects (spec section 6, "Projects"): one folder each, git-ignored; --projects can point at a shared Drive folder.
PROJECTS = ROOT / "data/projects"
EXAMPLES = {"id": "", "name": "Examples (P01, P02)", "location": "RO", "packages": ROOT / "data/maf/extracted",
            "originals": RAW, "boq": BOQ_DIR}


FOLDERS = {"packages": "packages", "originals": "packages", "boq": "boq"}   # a package's files sit beside its reading


def projects():
    """Every project folder with a project.json; a path in it may point elsewhere, relative to the folder."""
    out = []
    for f in sorted(PROJECTS.glob("*/project.json")) if PROJECTS.exists() else []:
        p = json.loads(f.read_text())
        out.append({"id": f.parent.name, "name": p["name"], "location": p.get("location", "RO"), "folder": f.parent,
                    "online": p.get("online"),   # where the project is online, written by web/scripts/import_project.py
                    **{k: (f.parent / p.get(k, FOLDERS[k])).resolve() for k in FOLDERS}})
    return out


def current_project():
    """The project the reviewer picked last; the examples when there is no project yet. The examples have no folder
    of their own, so the reviewer's decisions on them are kept in the projects folder itself."""
    every = projects()
    mark = PROJECTS / ".current"
    chosen = mark.read_text().strip() if mark.exists() else ""
    return next((p for p in every if p["id"] == chosen), every[0] if every else {**EXAMPLES, "folder": PROJECTS})


def new_project(name, location, root=None):
    """A project folder from a name typed in the app; the folder name is made from it, the name stays as typed."""
    root = root or PROJECTS
    name = " ".join(str(name).split())[:80]
    if not name or location not in CHAINS:
        raise ValueError("a project needs a name and a country (RO or ES)")
    base = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-") or "project"
    slug, n = base, 2
    while (root / slug).exists():
        slug, n = f"{base}-{n}", n + 1
    for sub in ("packages", "boq"):
        (root / slug / sub).mkdir(parents=True)
    (root / slug / "project.json").write_text(json.dumps({"name": name, "location": location,
                                                            "created": date.today().isoformat()}, indent=2) + "\n")
    return slug


def boq_files(folder=None):
    folder = folder or BOQ_DIR
    return sorted(p for p in folder.glob("*.xls*") if not p.name.startswith("~$")) if folder.exists() else []


def boq_links(pkg, read=True, folder=None):
    """For each item, the BOQ line it answers and what that line asks (AI, cached); None when there is no BOQ."""
    folder = folder or BOQ_DIR
    files = boq_files(folder)
    if not files:
        return None
    lines = []
    for f in files:
        stamp = (f, f.stat().st_mtime)
        if stamp not in _boq_lines:
            _boq_lines[stamp] = read_boq(f)
        lines += _boq_lines[stamp]
    if not sheets_for(lines, pkg["form"].get("boq_ref")):   # the BOQ of another project, or the form gives no code
        return None
    found = {i["id"]: find_line(lines, pkg["form"].get("boq_ref"), i, pkg["form"]) for i in pkg["items"]}
    readings = sorted({k for i in pkg["items"] for k in i["values"]})
    try:
        asks = ai.boq_requirements([ln["text"] for ln in found.values() if ln], readings, folder / "asks.json", read)
    except (RuntimeError, OSError, ValueError):   # no AI now: the lines show as not read yet
        asks = ai.boq_requirements([ln["text"] for ln in found.values() if ln], readings, folder / "asks.json", False)
    return {k: {**ln, "requirements": (asks.get(ln["text"]) or {}).get("requirements"), "status": "extracted"}
            for k, ln in found.items() if ln}










WRITE_LOCK = threading.Lock()   # one change to a package or decisions file at a time, so two quick clicks never undo each other


# The reviewer's ticks and decisions, under the name this laptop's app was started with (--reviewer)
def set_verified(entry, verified):
    core.set_verified(entry, verified, REVIEWER)


def confirm(pkg, targets):
    core.confirm(pkg, targets, REVIEWER)


def decide(pkg, finding_id, status, note=None):
    core.decide(pkg, finding_id, status, note, REVIEWER)


def decide_findings(decisions, changes):
    core.decide_findings(decisions, changes, REVIEWER)


def decisions_file(folder, name):
    """The reviewer's decisions on one package's findings. They sit in the project folder, which is git-ignored, and
    never in the package file: the package files of P01 and P02 are in the public repository."""
    return folder / "decisions" / f"{name}.json"


def read_decisions(path):
    return json.loads(path.read_text()) if path.exists() else {}




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


def package_list(data, raw=RAW, boq=None, location="RO"):
    """Every package the application knows: those RightFit has read, then those on this laptop still to be read.
    boq is the project's BOQ folder, so the counts match the review page (only BOQ lines already read)."""
    out = []
    for path in sorted(data.glob("P*.json")):
        pkg = json.loads(path.read_text())
        v = review(pkg, location, boq=boq_links(pkg, read=False, folder=boq) if boq else None)
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
    listed = {p["id"] for p in out}
    for folder in sorted(raw.glob("P*")) if raw.exists() else []:   # a package saved into the project, not read yet
        files = [f for f in folder.iterdir() if f.is_file() and not f.name.startswith(".")] if folder.is_dir() else []
        if re.fullmatch(r"P\d+", folder.name) and folder.name not in listed and files:
            out.append({"id": folder.name, "form_no": folder.name, "revision": 0, "discipline": "", "letter": None,
                        "items": [f"{len(files)} files, not read yet"], "files": len(files), "pages": None})
    return out


def revisions(name, originals):
    """What changed in a package's files since the previous revision of its form (ingest/revisions.py, no AI).
    {"previous": None} when no earlier revision sits next to it, or its original files are not on this laptop."""
    from ingest.revisions import compare, form_of, previous_revision
    folder = Path(originals) / name
    if not re.fullmatch(r"[A-Za-z0-9_-]+", name) or not folder.is_dir():
        return {"previous": None}
    before = previous_revision(folder)
    if before is None:
        return {"previous": None}
    return {"previous": before.name, "revision": form_of(before)[1], "attachments": compare(before, folder)}


def save_package(entries, originals, packages):
    """The files of an upload, kept in a new package folder of the project (P01, P02 ...). Returns its name."""
    taken = [int(p.stem[1:]) for p in packages.glob("P*.json") if p.stem[1:].isdigit()]
    taken += [int(p.name[1:]) for p in originals.glob("P*") if p.name[1:].isdigit()]
    name = f"P{max(taken, default=0) + 1:02d}"
    folder = originals / name
    folder.mkdir(parents=True)
    for file_name, data in entries:
        (folder / Path(file_name).name).write_bytes(data)
    return name


def save(path, pkg):
    """Write a JSON file whole or not at all: it goes to a temporary file first and then takes the old one's place,
    so a full disk or a stop halfway leaves the old file as it was."""
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(pkg, ensure_ascii=False, indent=2) + "\n")
    os.replace(tmp, path)


def day(text):
    return date.fromisoformat(text) if text else None


def local_request(headers):
    """True when a request comes from RightFit's own page on this laptop. A page of another site sends its own Origin,
    and a web name pointed at this laptop shows in Host, so both must be local; a script sends no Origin."""
    host = headers.get("Host") or ""
    origin = headers.get("Origin")
    return urlparse(f"http://{host}").hostname in LOCAL and (origin is None or urlparse(origin).netloc == host)


class Handler(SimpleHTTPRequestHandler):
    data = None   # --data: one folder of packages instead of the projects (tests and previews)

    def project(self):
        p = current_project()
        return {**EXAMPLES, "packages": self.data, "folder": self.data} if self.data else p

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
        path = original(name, json.loads(source.read_text()), no, self.project()["originals"]) if source else None
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
        return {p.stem: p for p in sorted(self.project()["packages"].glob("*.json"))}

    def do_GET(self):
        if not local_request(self.headers):   # a web name pointed at this laptop may not read the packages either
            return self.send_json({"error": "RightFit only answers its own page."}, 403)
        doc = re.fullmatch(r"/doc/([A-Za-z0-9_-]+)/(\d+)", self.path.split("?")[0])
        if doc:
            return self.send_original(doc.group(1), int(doc.group(2)))
        shown = re.fullmatch(r"/page/([A-Za-z0-9_-]+)/(\d+)/(\d+)\.png", self.path.split("?")[0])
        if shown:   # one page of an attachment; only files listed in the package, as for /doc/
            source = self.packages().get(shown.group(1))
            path = original(shown.group(1), json.loads(source.read_text()), int(shown.group(2)), self.project()["originals"]) if source else None
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
        if url.path == "/api/consultant-rules":
            return self.send_json(consultant_screen())
        if url.path == "/api/boq":
            return self.send_json([{"file": f.name, "lines": len(read_boq(f))} for f in boq_files(self.project()["boq"])])
        if url.path == "/api/projects":
            here = self.project()
            return self.send_json({"current": here["id"], "name": here["name"], "online": here.get("online"),
                                   "projects": [{"id": p["id"], "name": p["name"], "location": p["location"]} for p in projects()]})
        if url.path == "/api/rules":
            location = parse_qs(url.query).get("location", ["RO"])[0]
            return self.send_json(rules_for_location(location if location in CHAINS else "RO"))
        if url.path != "/api/packages":
            return super().do_GET()
        p = self.project()
        self.send_json(package_list(p["packages"], p["originals"], p["boq"], p["location"]))

    def do_POST(self):
        try:
            if not local_request(self.headers):   # another site open in the same browser; the app's own page goes on
                return self.send_json({"error": "RightFit only answers its own page."}, 403)
            size = int(self.headers.get("Content-Length", 0))
            if size > 60_000_000:
                return self.send_json({"error": "The file is larger than 60 MB."}, 413)
            raw = self.rfile.read(size)
            if self.path == "/api/upload":   # one file of the package, held in memory for this run only
                name = unquote(self.headers.get("X-File-Name", ""))
                return self.send_json({"name": name, "pages": pump_demo.page_count(raw), "token": pump_demo.keep(name, raw)})
            if self.path == "/api/boq":   # a BOQ file, kept in data/raw/boq (git-ignored: it holds prices)
                name = Path(unquote(self.headers.get("X-File-Name", ""))).name
                if not re.fullmatch(r"[\w .()&+,-]{1,120}\.xlsx?", name, re.I) or name.startswith("~$"):
                    return self.send_json({"error": "A BOQ is an Excel file (.xlsx or .xls)."}, 400)
                folder = self.project()["boq"]
                folder.mkdir(parents=True, exist_ok=True)
                (folder / name).write_bytes(raw)
                try:
                    lines = read_boq(folder / name)
                except Exception:
                    (folder / name).unlink()
                    return self.send_json({"error": "This file could not be read as a BOQ."}, 400)
                return self.send_json({"file": name, "lines": len(lines)})
            body = json.loads(raw or b"{}")
            if self.path == "/api/extract":   # read one page of an upload: its text, or OCR on a scan
                text, how = pump_demo.read_page(body["token"], int(body["page"]))
                return self.send_json({"chars": len(text), "read": how})
            if self.path == "/api/analyse":
                if not all(t in pump_demo.UPLOADS for t in body["tokens"]):   # the server was restarted since the upload
                    return self.send_json({"error": "The server was restarted and no longer has these files. "
                                                    "Add the package again."}, 410)
                return self.send_json(pump_demo.analyse(body["tokens"]))
            if self.path == "/api/projects":   # a new project, which becomes the one in use
                slug = new_project(body.get("name", ""), body.get("location", "RO"))
                (PROJECTS / ".current").write_text(slug)
                return self.send_json({"current": slug})
            if self.path == "/api/projects/select":
                if body["id"] not in {p["id"] for p in projects()}:
                    return self.send_json({"error": "unknown project"}, 404)
                (PROJECTS / ".current").write_text(body["id"])
                return self.send_json({"current": body["id"]})
            if self.path == "/api/projects/save-package":   # the files of an upload, kept in the project
                if not body["tokens"] or not all(tk in pump_demo.UPLOADS for tk in body["tokens"]):
                    return self.send_json({"error": "The server was restarted and no longer has these files. "
                                                    "Add the package again."}, 410)
                p = self.project()
                name = save_package([(pump_demo.UPLOADS[tk]["name"], pump_demo.UPLOADS[tk]["data"]) for tk in body["tokens"]],
                                    p["originals"], p["packages"])
                return self.send_json({"package": name, "project": p["name"]})
            if self.path == "/api/consultant-rules/draft":   # a rule typed in words: the AI proposes, nothing is saved
                rows = load(CONSULTANT.name)
                info = consultant_screen()
                try:
                    proposal = ai.rule_from_words(" ".join(str(body.get("words", "")).split())[:300], info["families"],
                                                  list(info["values"]), list(info["doc_types"]))
                except RuntimeError as e:
                    return self.send_json({"error": str(e)}, 503)
                return self.send_json({"rule": new_consultant_rule(proposal, rows)})
            if self.path == "/api/consultant-rules":   # a new rule from the Rules screen
                with WRITE_LOCK:   # read, change and write in one go, as for a package
                    rows = load(CONSULTANT.name)
                    write_consultant_rules(rows + [new_consultant_rule(body, rows)])
                return self.send_json(consultant_screen())
            if self.path == "/api/consultant-rules/active":   # switch one rule on or off
                with WRITE_LOCK:
                    rows = load(CONSULTANT.name)
                    row = next(r for r in rows if r["rule_id"] == body["rule_id"])
                    row["active"] = "yes" if body["active"] else "no"
                    write_consultant_rules(rows)
                return self.send_json(consultant_screen())
            if self.path == "/api/pumps/sets":
                return self.send_json(pump_demo.booster_sets())
            if self.path == "/api/pumps/booster":
                return self.send_json(pump_demo.booster_view(int(body["flats"]), int(body["floors"]),
                                                             body.get("submitted") or None, float(body.get("mains_m") or 0)))
            path = self.packages().get(body.get("package"))   # only a package that exists, never a free path
            if path is None:
                return self.send_json({"error": "unknown package"}, 404)
            pkg = json.loads(path.read_text())
            if self.path == "/api/revisions":   # what changed since the previous revision of the form (no AI)
                return self.send_json(revisions(body["package"], self.project()["originals"]))
            if self.path == "/api/marks":   # where the quoted lines sit on one page of an attachment
                source = original(body["package"], pkg, int(body["no"]), self.project()["originals"])
                return self.send_json({"marks": find_marks(source, int(body["page"]), body["quotes"]) if source else []})
            if self.path == "/api/load-local":   # the same files as an upload, taken from the originals on this laptop
                files = [(d["file"], original(body["package"], pkg, n, self.project()["originals"])) for n, d in enumerate(pkg["documents"], 1)]
                raw = self.project()["originals"]
                form = (raw / body["package"] / pkg["form"]["source"]).resolve()
                if form.is_relative_to((raw / body["package"]).resolve()) and form.is_file():
                    files.append((form.name, form))
                return self.send_json([{"name": n, "pages": pump_demo.page_count(f.read_bytes()),
                                        "token": pump_demo.keep(n, f.read_bytes())} for n, f in files if f])
            here = self.project()
            file = decisions_file(here["folder"], path.stem)
            if self.path in ("/api/confirm", "/api/decide"):
                with WRITE_LOCK:   # read, change and write in one go, so a second quick tick never undoes the first
                    pkg = json.loads(path.read_text())
                    if self.path == "/api/confirm":
                        confirm(pkg, body["targets"])
                    else:
                        decide(pkg, body["id"], body["status"], body.get("note"))
                    save(path, pkg)
            elif self.path == "/api/decisions":   # the reviewer's decisions on findings, kept in the project folder
                with WRITE_LOCK:   # read just before writing: a colleague sharing the folder may have decided since
                    decisions = read_decisions(file)
                    decide_findings(decisions, body["decisions"])
                    file.parent.mkdir(parents=True, exist_ok=True)
                    save(file, decisions)
            elif self.path != "/api/review":
                return self.send_json({"error": "unknown address"}, 404)
            decisions = read_decisions(file)
            view = review(pkg, body.get("location") or here["location"], day(body.get("review")), day(body.get("delivery")),
                          {k: d["reason"] for k, d in decisions.items() if d["decision"] == "dismissed"},
                          boq_links(pkg, folder=here["boq"]))
            self.send_json({**view, "decisions": decisions})
        except (KeyError, ValueError, StopIteration, TypeError, IndexError) as e:
            self.send_json({"error": f"{type(e).__name__}: {e}"}, 400)
        except Exception as e:   # an upload no library can read still gets an answer the page can show
            traceback.print_exc()
            self.send_json({"error": f"A file could not be read ({type(e).__name__}). Check it by eye."}, 500)


def main():
    global PROJECTS, REVIEWER
    ap = argparse.ArgumentParser(description="RightFit review page")
    ap.add_argument("--port", type=int, default=8520)
    ap.add_argument("--data", type=Path, help="one folder of package files instead of the projects (tests, previews)")
    ap.add_argument("--projects", type=Path, help="the folder that holds the projects, for example a shared Drive folder")
    ap.add_argument("--reviewer", default=REVIEWER, help="the name kept next to every confirmation and decision")
    args = ap.parse_args()
    Handler.data, PROJECTS, REVIEWER = args.data, args.projects or PROJECTS, args.reviewer
    server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    print(f"RightFit review page: http://127.0.0.1:{args.port}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
