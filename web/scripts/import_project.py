"""Put the current RightFit project from this laptop into RightFit online (spec/features/rightfit_online.md, section 11):
its MAF packages, the original files of each, RightFit's review of the packages already read with their readings and
decisions, the rule tables, and the BOQ lines without the prices. Files go to the private R2 bucket, rows to the D1
database; the project is locked, so its data opens only with the team password as well. The reviewers change the
reviews online from then on, so an import again keeps what was confirmed, decided or changed online, unless
--replace-online-work. Nothing it reads or writes goes into Git.

Run from the repository root:
  python3 web/scripts/import_project.py --owner <email of the consultant's account online> --remote
  python3 web/scripts/import_project.py --project-id <id> --remote     # import again into the same project
Without --remote it fills the laptop's copy (the local D1 and R2 that `npm run dev` uses), to try it first.
"""
import argparse
import copy
import json
import re
import subprocess
import sys
import tempfile
import time
import uuid
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WEB = ROOT / "web"
sys.path.insert(0, str(ROOT))

DPA_VERSION = "2026-11-26"  # the data processing agreement in web/legal/, as in web/worker/index.ts
BUCKET = "rightfit-files"
SITE = "https://rightfit.hackathon-team6-cubicasa-app.workers.dev"   # RightFit online, where the laptop's app links
TYPES = {"pdf": "application/pdf", "xls": "application/vnd.ms-excel", "jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png",
         "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"}


def sql(value):
    """A value written into SQL: text quoted (a quote doubled), numbers as they are, nothing as NULL."""
    if value is None:
        return "NULL"
    if isinstance(value, bool):
        return "1" if value else "0"
    if isinstance(value, (int, float)):
        return repr(value)
    return "'" + str(value).replace("'", "''") + "'"


class WranglerError(Exception):
    pass


def wrangler(args, where, stdin=None, tries=1):
    """Run wrangler on the live Cloudflare (remote) or on the laptop's copy (local); a failed run is tried again,
    a few seconds later, up to `tries` times, because a lost connection is often only a moment's."""
    flag = "--remote" if where == "remote" else "--local"
    for attempt in range(1, tries + 1):
        run = subprocess.run(["npx", "wrangler", *args, flag], cwd=WEB, input=stdin, text=True, capture_output=True)
        if not run.returncode:
            return run.stdout
        if attempt < tries:
            time.sleep(3 * attempt)
    raise WranglerError(f"wrangler {' '.join(args[:3])} failed:\n{run.stderr[-1500:]}")


def online(key, where):
    """An object already in the bucket, read as JSON, or None when there is none. Any other failure stops the import,
    so a lost connection is never taken for "nothing online" and never leads to overwriting what was done online."""
    try:
        out = wrangler(["r2", "object", "get", f"{BUCKET}/{key}", "--pipe"], where)
    except WranglerError as err:
        if re.search(r"does not exist|not found|NoSuchKey", str(err), re.I):
            return None
        raise
    return json.loads(out[out.index("{"):])


def query(statement, where):
    out = wrangler(["d1", "execute", "rightfit-db", "--json", "--command", statement], where)
    return json.loads(out[out.index("["):])[0]["results"]


def page_count(path):
    if path.suffix.lower() != ".pdf":
        return None
    import pymupdf
    try:
        with pymupdf.open(path) as doc:
            return doc.page_count
    except Exception:
        return None


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--owner", help="the email of the consultant's account online, who opens the project")
    ap.add_argument("--project-id", help="import again into this project instead of opening a new one")
    ap.add_argument("--remote", action="store_true", help="the live database and bucket (otherwise the laptop's copy)")
    ap.add_argument("--no-files", action="store_true", help="rows and reviews only, without uploading the packages' files again")
    ap.add_argument("--workers", type=int, help="files uploaded at once: 4 online by default; 1 on the laptop, where "
                                                "several local wranglers at once lose their connection")
    ap.add_argument("--pages", action="store_true",
                    help="upload the page images of the read packages, as an import with the files does")
    ap.add_argument("--replace-online-work", action="store_true",
                    help="write the laptop's readings, decisions and consultant's rules over what was confirmed, decided "
                         "or changed online (without it, what is online stays as it is)")
    args = ap.parse_args()
    where = "remote" if args.remote else "local"
    if not args.project_id and not args.owner:
        sys.exit("Give --owner (to open a new project) or --project-id (to import again).")

    from app.review_server import (boq_files, boq_links, consultant_screen, current_project, decisions_file, find_marks,
                                   original, package_list, page_png, read_decisions, review, revisions)
    from checks.maf.rules import library, load
    from ingest.boq import read_boq

    project = current_project()   # the project the review app has open: its name, packages, originals and BOQ folder
    name, country = project["name"], project.get("location") or "RO"
    now = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")

    # The project online
    statements = []
    if args.project_id:
        pid = args.project_id
        if not query(f"SELECT id FROM project WHERE id = {sql(pid)}", where):
            sys.exit(f"No project {pid} online.")
    else:
        found = query(f'SELECT id FROM "user" WHERE lower(email) = lower({sql(args.owner)})', where)
        if not found:
            sys.exit(f"No account online for {args.owner}: sign in once on the site first.")
        owner, pid = found[0]["id"], str(uuid.uuid4())
        statements += [
            "INSERT INTO project (id, name, country, created_by, created_at, dpa_version, dpa_accepted_by, dpa_accepted_at, locked) "
            f"VALUES ({sql(pid)}, {sql(name)}, {sql(country)}, {sql(owner)}, {sql(now)}, {sql(DPA_VERSION)}, {sql(owner)}, {sql(now)}, 1);",
            "INSERT INTO member (id, project_id, user_id, role, company, invited_by, joined_at) "
            f"VALUES ({sql(str(uuid.uuid4()))}, {sql(pid)}, {sql(owner)}, 'consultant', '', NULL, {sql(now)});",
            f"INSERT INTO event (at, actor, project_id, action, detail) VALUES ({sql(now)}, {sql(owner)}, {sql(pid)}, 'project.opened', "
            f"{sql(json.dumps({'dpa': DPA_VERSION, 'imported': True}))});",
        ]
    # A package added on the site (worker/upload.ts) stays as it is: an import replaces only what came from the laptop
    added_online = {r["code"] for r in query(f"SELECT code FROM package WHERE project_id = {sql(pid)} AND uploaded_by IS NOT NULL",
                                             where)} if args.project_id else set()
    statements += [
        f"DELETE FROM package_file WHERE project_id = {sql(pid)} AND code NOT IN "
        f"(SELECT code FROM package WHERE project_id = {sql(pid)} AND uploaded_by IS NOT NULL);",
        f"DELETE FROM package WHERE project_id = {sql(pid)} AND uploaded_by IS NULL;",
        f"DELETE FROM boq_line WHERE project_id = {sql(pid)};",
    ]
    statements.append(f"UPDATE project SET locked = 1 WHERE id = {sql(pid)};")

    # The rule tables the checks use (data/maf), with the consultant's own rules. Once the rules can change online, the
    # consultant's rules online stay as they are, unless --replace-online-work.
    screen = consultant_screen()
    tables = {"rules": load("rules.csv"), "family_documents": load("family_documents.csv"), "checklist": load("checklist.csv"),
              "library": library(), "consultant": screen["rules"],
              "names": {k: screen[k] for k in ("doc_types", "values", "kinds", "families")}}
    again = bool(args.project_id) and not args.replace_online_work
    before = online(f"projects/{pid}/tables.json", where) if again else None
    if before is not None:
        tables["consultant"] = before["consultant"]

    # The packages, and RightFit's review of those already read: the whole page the laptop shows (every check, what
    # passed, the readings, the AI's suggestions, the answer). With it go the package's readings, the BOQ lines found
    # for it and the reviewer's decisions (its state), which the reviewers change online from then on: a package whose
    # state is already online keeps it, unless --replace-online-work. BOQ lines are only those already read
    # (read=False): the import never asks the AI anything.
    packages = package_list(Path(project["packages"]), Path(project["originals"]), Path(project["boq"]), country)
    if added_online & {p["id"] for p in packages}:
        print(f"  left out, as packages added on the site have the same code: {', '.join(sorted(added_online & {p['id'] for p in packages}))}")
        packages = [p for p in packages if p["id"] not in added_online]
    states, reviews, kept = {}, {}, []
    for p in packages:
        if p.get("letter"):
            view = online(f"projects/{pid}/reviews/{p['id']}.json", where) if again and online(
                f"projects/{pid}/state/{p['id']}.json", where) is not None else None
            if view is not None:
                kept.append(p["id"])
            else:
                pkg = json.loads((Path(project["packages"]) / f"{p['id']}.json").read_text())
                boq = boq_links(pkg, read=False, folder=Path(project["boq"]))
                decisions = read_decisions(decisions_file(Path(project["folder"]), p["id"]))
                dismissed = {k: d["reason"] for k, d in decisions.items() if d["decision"] == "dismissed"}
                states[p["id"]] = {"pkg": pkg, "boq": boq, "decisions": decisions}
                view = {**review(copy.deepcopy(pkg), country, None, None, dismissed, boq, tables), "decisions": decisions}
                reviews[p["id"]] = view
            c = view["counts"]   # the list online shows the same letter and counts as the page
            p.update(letter=view["status"]["letter"], label=view["status"]["label"], problems=c["problems"],
                     questions=c["questions"], to_confirm=c["to_confirm"], readings=c["readings"])
        statements.append(
            "INSERT INTO package (project_id, code, form_no, revision, discipline, items, files, pages, letter, label, problems, "
            "questions, to_confirm, readings, reviewed_at, imported_at) VALUES ("
            + ", ".join(sql(v) for v in (pid, p["id"], p["form_no"], int(p.get("revision") or 0), p.get("discipline", ""),
                                         json.dumps(p.get("items", []), ensure_ascii=False), p.get("files", 0), p.get("pages"),
                                         p.get("letter"), p.get("label"), p.get("problems"), p.get("questions"),
                                         p.get("to_confirm"), p.get("readings"), now if p.get("letter") else None, now))
            + ");")

    # What only the laptop can read from the original PDFs, for the package's page online: the comparison with the
    # previous revision of the form, where each quoted line sits on its page (the yellow marks), and, with the files
    # or --pages, every page of the attachments as an image to draw the marks on.
    extras, images = {}, []
    for p in packages:
        if not p.get("letter"):
            continue
        pkg = json.loads((Path(project["packages"]) / f"{p['id']}.json").read_text())
        quoted = defaultdict(set)   # (file, page) -> the quotes on it
        places = [(x["source"], x.get("page"), x.get("quote")) for i in pkg["items"] for x in i["values"].values()]
        places += [(d["file"], m.get("page"), m.get("quote")) for d in pkg["documents"] for m in d.get("matches", [])]
        places += [(e["source"], e.get("page"), e.get("quote")) for f in pkg.get("ai_findings", []) for e in f.get("evidence", [])]
        for file, page, quote in places:
            if quote and str(page or "").isdigit():
                quoted[(file, int(page))].add(quote)
        marks = {}
        for n, d in enumerate(pkg["documents"], 1):
            path = original(p["id"], pkg, n, Path(project["originals"]))
            if not path or path.suffix.lower() != ".pdf":
                continue
            for (file, page), quotes in sorted(quoted.items()):
                if file == d["file"]:
                    quotes = sorted(quotes)
                    marks.setdefault(file, {})[str(page)] = dict(zip(quotes, find_marks(path, page, quotes)))
            if not args.no_files or args.pages:
                images += [(f"projects/{pid}/pages/{p['id']}/{n}/{page}.png", path, page) for page in range(1, d["pages"] + 1)]
        extras[p["id"]] = {"revisions": revisions(p["id"], project["originals"]), "marks": marks}

    # The knowledge graph (MAF-36): the product lines that come back from one project to the next, from the forms, the
    # register of the previous project (on this laptop only) and the BOQ; no AI. Admins who are members see it drawn.
    from ingest.graph import build as build_graph
    graph = build_graph(project["originals"], ROOT / "data/raw/register/register.xlsx", boq_files(Path(project["boq"])))

    # The original files of each package (reading a file brings it back from iCloud first)
    uploads = []
    for p in packages:
        folder = Path(project["originals"]) / p["id"]
        if not re.fullmatch(r"P\d+", p["id"]) or not folder.is_dir():
            continue
        for f in sorted(folder.iterdir()):
            if not f.is_file() or f.name.startswith(".") or "/" in f.name or ".." in f.name:
                continue
            f.read_bytes()
            statements.append(
                "INSERT INTO package_file (project_id, code, name, size, pages) VALUES ("
                + ", ".join(sql(v) for v in (pid, p["id"], f.name, f.stat().st_size, page_count(f))) + ");")
            uploads.append((f"projects/{pid}/packages/{p['id']}/{f.name}", f))

    # The BOQ lines, never the prices: read_boq takes only the text, unit, quantity, producer and standards
    lines = 0
    for boq in boq_files(Path(project["boq"])):
        for ln in read_boq(boq):
            lines += 1
            statements.append(
                "INSERT OR REPLACE INTO boq_line (project_id, file, sheet, row, nr, text, unit, qty, producer, standards) VALUES ("
                + ", ".join(sql(v if v is None or isinstance(v, (int, float)) else str(v))
                            for v in (pid, ln["file"], ln["sheet"], ln["row"], ln["nr"], ln["text"], ln["unit"], ln["qty"],
                                      ln["producer"], ln["standards"])) + ");")
    statements.append(
        f"INSERT INTO event (at, actor, project_id, action, detail) VALUES ({sql(now)}, NULL, {sql(pid)}, 'project.imported', "
        f"{sql(json.dumps({'packages': len(packages), 'files': len(uploads), 'boqLines': lines}))});")

    work = Path(tempfile.mkdtemp(prefix="rightfit-import-"))   # outside the repository; deleted at the end
    try:
        if args.no_files:
            uploads = []   # the packages' files are already in the bucket
        # The files and page images already sent online, by name and size, are not sent again (a record kept in the
        # project folder, which Git never sees)
        record_file = Path(project["folder"]) / "online_files.json" if where == "remote" and project.get("id") else None
        sent = json.loads(record_file.read_text()) if record_file and record_file.exists() else {}
        uploads = [(k, f) for k, f in uploads if sent.get(k) != f.stat().st_size]
        images = [(k, pdf, page) for k, pdf, page in images if k not in sent]
        once = {k: f.stat().st_size for k, f in uploads} | {k: 0 for k, _, _ in images}
        for key, value in [("tables.json", tables), ("graph.json", graph), *((f"reviews/{c}.json", v) for c, v in reviews.items()),
                           *((f"state/{c}.json", v) for c, v in states.items()), *((f"extra/{c}.json", v) for c, v in extras.items())]:
            path = work / key.replace("/", "-")
            path.write_text(json.dumps(value, ensure_ascii=False))
            uploads.append((f"projects/{pid}/{key}", path))
        for n, (key, pdf, page) in enumerate(images):   # every page as a PNG, drawn as on the laptop's document pane
            png = page_png(pdf, page)
            if png:
                path = work / f"page-{n}.png"
                path.write_bytes(png)
                uploads.append((key, path))

        def put(item):
            key, path = item
            kind = TYPES.get(path.suffix.lower().lstrip("."), "application/json" if path.suffix == ".json" else "application/octet-stream")
            wrangler(["r2", "object", "put", f"{BUCKET}/{key}", "--file", str(path), "--content-type", kind], where, tries=3)
            return key

        workers = args.workers or (4 if where == "remote" else 1)
        with ThreadPoolExecutor(max_workers=workers) as pool:
            for n, _ in enumerate(pool.map(put, uploads), 1):
                if n % 25 == 0 or n == len(uploads):
                    print(f"  {n} of {len(uploads)} files in the bucket", flush=True)
        rows = work / "import.sql"
        rows.write_text("\n".join(statements) + "\n")
        wrangler(["d1", "execute", "rightfit-db", "--file", str(rows), "--yes"], where)
        if record_file:
            record_file.write_text(json.dumps({**sent, **once}, indent=1))
    finally:
        for f in work.iterdir():
            f.unlink()
        work.rmdir()
    if where == "remote" and project.get("folder") and (Path(project["folder"]) / "project.json").exists():
        settings = Path(project["folder"]) / "project.json"   # git-ignored, as the whole project folder
        kept_settings = json.loads(settings.read_text())
        settings.write_text(json.dumps({**kept_settings, "online": {"site": SITE, "project": pid}}, indent=2) + "\n")
    print(f"Imported into project {pid} ({where}): {len(packages)} packages, {len(reviews)} reviews from the laptop"
          + (f", {len(kept)} kept as changed online ({', '.join(kept)})" if kept else "")
          + f", {len(images)} page images, {len(uploads)} files, {lines} BOQ lines, a graph of "
          + f"{sum(graph['summary']['product_lines'].values())} product lines. The project is locked: it opens with the team password.")


if __name__ == "__main__":
    try:
        main()
    except WranglerError as err:   # nothing is half done: the rows are written only after every file is in the bucket
        sys.exit(f"Stopped, and the database was not changed. {err}")
