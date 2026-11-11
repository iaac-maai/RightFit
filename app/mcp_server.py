"""RightFit as an MCP server: its checks as tools that an AI agent can call.

Run from the repository root:  python3 app/mcp_server.py
An agent that speaks MCP starts it by itself, as the project's .mcp.json tells it to, and talks to it over
standard input and output. Every tool only reads: none of them changes a package, confirms a reading or
approves anything. Confirming what the AI read stays a person's job, on the review page.
"""
import json
import re
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from mcp.server import MCPServer  # noqa: E402
from mcp.server.mcpserver.exceptions import ToolError  # noqa: E402
from mcp.types import ToolAnnotations  # noqa: E402

from checks.maf.rules import CHAINS  # noqa: E402

# The PDF and machine learning libraries are imported inside the tools: they take seconds to load, and an agent gives up
# on a server that does not answer at once.
DATA = ROOT / "data/maf/extracted"
RAW = ROOT / "data/raw"   # the original packages, on the laptop only (git-ignored)
MODEL = RAW / "models/page_classifier.joblib"
READ_ONLY = ToolAnnotations(readOnlyHint=True)
RESULT_FIELDS = ("check", "check_name", "product", "doc", "verdict", "confirmed", "reason", "sources", "rules",
                 "blocking", "evidence")

server = MCPServer("RightFit", instructions=(
    "RightFit drafts the review of material approval forms (MAFs) for MEP equipment. Its checks are fixed "
    "Python rules, not AI. A result with confirmed false is what the check would say once a person confirms "
    "the readings it uses, so never present it as a finding of compliance. Every rule carries its source and "
    "status, and only verified_official means it was read in the official journal. RightFit never approves a "
    "package: the reviewer decides. Quote file and page exactly as RightFit gives them."))


def package_file(name):
    """The readings of one package; the name comes from the agent, so only names like P01 are accepted."""
    path = DATA / f"{name}.json"
    if not re.fullmatch(r"P\d+", name) or not path.exists():
        raise ToolError(f"No readings for {name!r}. Packages RightFit has read: "
                        f"{', '.join(p.stem for p in sorted(DATA.glob('P*.json')))}.")
    return json.loads(path.read_text())


def check_location(location):
    if location not in CHAINS:
        raise ToolError(f"location must be one of {', '.join(CHAINS)}")


@server.tool(annotations=READ_ONLY)
def list_packages() -> dict:
    """The MAF packages RightFit has read, with their form, products, documents and how many readings a person
    has confirmed, and the package folders on this laptop that are not read yet (classify_pages works on those)."""
    read = []
    for path in sorted(DATA.glob("P*.json")):
        pkg = json.loads(path.read_text())
        readings = [x for i in pkg["items"] for x in i["values"].values()]
        read.append({"package": pkg["package"], "form": f"{pkg['form']['form_no']} rev {pkg['form']['revision']}",
                     "products": [f"{i['name']} ({i['model']})" for i in pkg["items"]],
                     "documents": len(pkg["documents"]),
                     "readings_confirmed": f"{sum(x['status'] == 'verified' for x in readings)} of {len(readings)}"})
    folders = sorted(p.name for p in RAW.glob("P*") if re.fullmatch(r"P\d+", p.name) and p.is_dir()) if RAW.exists() else []
    return {"read": read, "on_this_laptop_not_read": [f for f in folders if not (DATA / f"{f}.json").exists()]}


@server.tool(annotations=READ_ONLY)
def review_package(package: str, location: str = "RO", review_date: str | None = None) -> dict:
    """Run RightFit's checks on one package and return its draft answer (A approved, B approved with comments,
    C revise and resubmit), the problems and the open questions, each with file, page and rules.

    location is RO (Romania) or ES (Spain). review_date (YYYY-MM-DD) defaults to the form's date; the delivery
    date follows from the form's lead time. Passed checks are only counted, to keep the answer short."""
    from app.review_server import review
    check_location(location)
    try:
        day = date.fromisoformat(review_date) if review_date else None
    except ValueError:
        raise ToolError("review_date must look like 2026-11-12") from None
    v = review(package_file(package), location, day)
    pick = lambda verdict: [{k: r[k] for k in RESULT_FIELDS} for r in v["results"] if r["verdict"] == verdict]  # noqa: E731
    return {"package": v["package"], "location": location, "review_date": v["review"], "delivery_date": v["delivery"],
            "form": v["form"], "draft_answer": v["status"], "counts": v["counts"],
            "problems": pick("flag"), "questions": pick("unclear"),
            "documents": [{k: d[k] for k in ("no", "file", "type", "listed_as", "status")} for d in v["documents"]],
            "answer_text": v["answer"]["text"]}


@server.tool(annotations=READ_ONLY)
def list_rules(location: str = "RO") -> dict:
    """The rules RightFit checks for a location (EU rules, the country's rules and reviewers' practice), each with
    its legal source, clause and status: verified_official (read in the official journal), verified_secondary
    (read in a copy, to check), to_confirm, practice or engineer_input (a value set by the team's engineer)."""
    from app.review_server import rules_for_location
    check_location(location)
    return {"location": location, "rules": rules_for_location(location)}


_model = None


@server.tool(annotations=READ_ONLY)
def classify_pages(package: str) -> dict:
    """What kind of document each PDF page of a package folder on this laptop is (declaration, data_sheet,
    certificate, manual or other), by RightFit's own page classifier and by a keyword search, side by side.
    The classifier is AI output: a small model the team trained (TF-IDF and logistic regression on 443 public
    pages). On the locked test it got 25% of package pages right, against 27% for the keyword search, so use
    its labels as hints. A page without a text layer (a scan) is 'other' for both."""
    global _model
    from model.page_classifier import MIN_TEXT, keyword_baseline, normalize, pdf_pages, predict
    folder = RAW / package
    if not re.fullmatch(r"P\d+", package) or not folder.is_dir():
        raise ToolError(f"No package folder {package!r} on this laptop.")
    if not MODEL.exists():
        raise ToolError("The page classifier is not trained on this laptop: run python -m model.train_pages")
    if _model is None:
        import joblib
        _model = joblib.load(MODEL)
    pages, unread = [], []
    for path in sorted(p for p in folder.iterdir() if p.suffix.lower() == ".pdf"):
        try:
            pages += pdf_pages(path)
        except Exception:   # a damaged or locked PDF is listed, the rest of the package is still classified
            unread.append(path.name)
    labels = predict(_model, [p["text"] for p in pages])
    return {"package": package, "classifier": "RightFit page classifier v1 (AI output)",
            "pages": [{"file": Path(p["file"]).name, "page": p["page"], "classifier": label,
                       "keywords": keyword_baseline(p["text"]), "has_text": len(normalize(p["text"])) >= MIN_TEXT}
                      for p, label in zip(pages, labels)],
            "not_read": unread}


if __name__ == "__main__":
    server.run()
