"""RightFit's draft answer next to Luca's reference answer, for every package that has one (MAF-08).

The reference answers in data/maf/reference/ are only read here, never changed, and never used to tune a check
(AGENTS.md rule 7). Run from the repository root: python3 -m eval.reference_answers.compare
"""
import json
import re
from pathlib import Path

from app.review_core import review

ROOT = Path(__file__).resolve().parents[2]
REFERENCE = ROOT / "data" / "maf" / "reference"
EXTRACTED = ROOT / "data" / "maf" / "extracted"


def reference_letter(text):
    """The letter in the line 'Status Luca would give: Approved (A).'; None if the line is missing."""
    m = re.search(r"Status Luca would give:.*\(([ABC])\)", text)
    return m.group(1) if m else None


def compare(package, location="RO"):
    """One row of the comparison: both answers, the findings behind the draft and how many readings are confirmed."""
    pkg = json.loads((EXTRACTED / f"{package}.json").read_text())
    v = review(pkg, location)
    readings = [x for i in pkg["items"] for x in i["values"].values()]
    flags = [r for r in v["results"] if r["verdict"] == "flag"]
    return {
        "package": package,
        "reference": reference_letter((REFERENCE / f"{package}.md").read_text()),
        "draft": v["status"]["letter"],
        "problems": [f"{r['check']} {r['title']}" + (f" ({r['product']})" if r["product"] else "") for r in flags],
        "questions": v["counts"]["questions"],
        "passed": v["counts"]["passed"],
        "values": {s: sum(x["status"] == s for x in readings) for s in ("verified", "extracted", "unclear")},
        "documents_confirmed": f"{sum(d['status'] == 'verified' for d in pkg['documents'])} of {len(pkg['documents'])}",
        "ai_findings_undecided": v["counts"]["ai_to_decide"],
    }


def main():
    for path in sorted(REFERENCE.glob("P*.md")):
        row = compare(path.stem)
        same = "same" if row["reference"] == row["draft"] else "different"
        print(f"{row['package']}: Luca {row['reference']}, RightFit {row['draft']} ({same}); "
              f"{len(row['problems'])} problems, {row['questions']} questions, {row['passed']} passed; "
              f"values {row['values']}, documents confirmed {row['documents_confirmed']}")
        for p in row["problems"]:
            print("   ", p)


if __name__ == "__main__":
    main()
