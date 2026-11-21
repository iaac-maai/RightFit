"""Put the current RightFit project from this laptop into RightFit online (spec/features/rightfit_online.md, section 11):
its MAF packages, the original files of each, RightFit's draft review of the packages already read, and the BOQ lines
without the prices. Files go to the private R2 bucket, rows to the D1 database; the project is locked, so its data
opens only with the team password as well. Nothing it reads or writes goes into Git.

Run from the repository root:
  python3 web/scripts/import_project.py --owner <email of the consultant's account online> --remote
  python3 web/scripts/import_project.py --project-id <id> --remote     # import again into the same project
Without --remote it fills the laptop's copy (the local D1 and R2 that `npm run dev` uses), to try it first.
"""
import argparse
import json
import re
import subprocess
import sys
import tempfile
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WEB = ROOT / "web"
sys.path.insert(0, str(ROOT))

DPA_VERSION = "2026-11-20"  # the data processing agreement in web/legal/, as in web/worker/index.ts
BUCKET = "rightfit-files"
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
    args = ap.parse_args()
    where = "remote" if args.remote else "local"
    if not args.project_id and not args.owner:
        sys.exit("Give --owner (to open a new project) or --project-id (to import again).")

    from app.review_server import (boq_files, boq_links, consultant_screen, current_project, decisions_file,
                                   package_list, read_decisions, review, rules_for_location)
    from checks.maf.rules import load
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
    statements += [f"DELETE FROM {t} WHERE project_id = {sql(pid)};" for t in ("package_file", "package", "boq_line")]
    statements.append(f"UPDATE project SET locked = 1 WHERE id = {sql(pid)};")

    # The packages, and RightFit's draft review of those already read: the whole page the laptop shows (every check,
    # what passed, the readings, the AI's suggestions, the answer), with the reviewer's decisions taken on the laptop.
    # BOQ lines are only those already read (read=False): the import never asks the AI anything.
    packages = package_list(Path(project["packages"]), Path(project["originals"]), Path(project["boq"]), country)
    reviews = {}
    for p in packages:
        if p.get("letter"):
            pkg = json.loads((Path(project["packages"]) / f"{p['id']}.json").read_text())
            decisions = read_decisions(decisions_file(Path(project["folder"]), p["id"]))
            dismissed = {k: d["reason"] for k, d in decisions.items() if d["decision"] == "dismissed"}
            view = review(pkg, country, None, None, dismissed, boq_links(pkg, read=False, folder=Path(project["boq"])))
            reviews[p["id"]] = {**view, "decisions": decisions}
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

    # The rules the checks use for the project's country, shown on the project's Rules page
    rules = {"location": country, "law": rules_for_location(country), "checklist": load("checklist.csv"),
             "mine": consultant_screen()}

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
        for code, view in reviews.items():   # the reviews and the rules always go, as they change with every import
            path = work / f"{code}.json"
            path.write_text(json.dumps(view, ensure_ascii=False))
            uploads.append((f"projects/{pid}/reviews/{code}.json", path))
        path = work / "rules.json"
        path.write_text(json.dumps(rules, ensure_ascii=False))
        uploads.append((f"projects/{pid}/rules.json", path))

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
    finally:
        for f in work.iterdir():
            f.unlink()
        work.rmdir()
    print(f"Imported into project {pid} ({where}): {len(packages)} packages, {len(reviews)} with RightFit's draft, "
          f"{len(uploads)} files, {lines} BOQ lines. The project is locked: it opens with the team password.")


if __name__ == "__main__":
    try:
        main()
    except WranglerError as err:   # nothing is half done: the rows are written only after every file is in the bucket
        sys.exit(f"Stopped, and the database was not changed. {err}")
