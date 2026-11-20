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


def wrangler(args, where, stdin=None):
    flag = "--remote" if where == "remote" else "--local"
    run = subprocess.run(["npx", "wrangler", *args, flag], cwd=WEB, input=stdin, text=True, capture_output=True)
    if run.returncode:
        sys.exit(f"wrangler {' '.join(args[:3])} failed:\n{run.stderr[-1500:]}")
    return run.stdout


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
    ap.add_argument("--no-files", action="store_true", help="rows only, without uploading the files again")
    args = ap.parse_args()
    where = "remote" if args.remote else "local"
    if not args.project_id and not args.owner:
        sys.exit("Give --owner (to open a new project) or --project-id (to import again).")

    from app import mcp_server
    from app.review_server import boq_files, current_project, package_list
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

    # The packages, and RightFit's draft review of those already read
    packages = package_list(Path(project["packages"]), Path(project["originals"]), Path(project["boq"]), country)
    reviews = {}
    for p in packages:
        if p.get("letter"):
            reviews[p["id"]] = mcp_server.review_package(p["id"], country)
        statements.append(
            "INSERT INTO package (project_id, code, form_no, revision, discipline, items, files, pages, letter, label, problems, "
            "questions, to_confirm, readings, reviewed_at, imported_at) VALUES ("
            + ", ".join(sql(v) for v in (pid, p["id"], p["form_no"], int(p.get("revision") or 0), p.get("discipline", ""),
                                         json.dumps(p.get("items", []), ensure_ascii=False), p.get("files", 0), p.get("pages"),
                                         p.get("letter"), p.get("label"), p.get("problems"), p.get("questions"),
                                         p.get("to_confirm"), p.get("readings"), now if p.get("letter") else None, now))
            + ");")

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
        if not args.no_files:
            for code, review in reviews.items():
                path = work / f"{code}.json"
                path.write_text(json.dumps(review, ensure_ascii=False))
                uploads.append((f"projects/{pid}/reviews/{code}.json", path))

            def put(item):
                key, path = item
                kind = TYPES.get(path.suffix.lower().lstrip("."), "application/json" if path.suffix == ".json" else "application/octet-stream")
                wrangler(["r2", "object", "put", f"{BUCKET}/{key}", "--file", str(path), "--content-type", kind], where)
                return key

            with ThreadPoolExecutor(max_workers=6) as pool:
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
    main()
