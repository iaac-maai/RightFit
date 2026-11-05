"""The PoC review page's server: the view it builds from the checks, and the reviewer's changes."""
import copy
import json
from pathlib import Path

from app.review_server import confirm, decide, original, review

P02 = json.loads((Path(__file__).resolve().parents[1] / "data/maf/extracted/P02.json").read_text())


def fresh():
    return copy.deepcopy(P02)


def test_every_comment_in_the_answer_has_its_delta_on_a_result():
    v = review(fresh())
    assert v["status"]["letter"] == "B"
    assert v["answer"]["text"].startswith("MAF IV 004 rev 4: Approved as noted (B)")
    deltas = {r["delta"] for r in v["results"] if r["delta"]}
    assert deltas == set(range(1, len(v["answer"]["lines"]) + 1))


def test_a_dismissed_problem_counts_as_ok_and_leaves_the_answer():
    v = review(fresh())
    problem = next(r for r in v["results"] if r["verdict"] == "flag")
    v2 = review(fresh(), dismissed={problem["key"]: "accepted by the client"})
    after = next(r for r in v2["results"] if r["key"] == problem["key"])
    assert after["verdict"] == "pass" and after["dismissed"] == "accepted by the client" and after["delta"] is None
    assert v2["counts"]["problems"] == v["counts"]["problems"] - 1
    assert problem["comment"] not in v2["answer"]["lines"]


def test_confirming_and_deciding_change_the_package():
    pkg = fresh()
    item = pkg["items"][0]
    key = next(iter(item["values"]))
    confirm(pkg, [{"kind": "value", "item": item["id"], "key": key, "verified": True}])
    assert item["values"][key]["status"] == "verified" and item["values"][key]["checked_by"] == "Luca"
    decide(pkg, "P02-AI1", "accepted")
    v = review(pkg)
    assert v["answer"]["lines"][-1].startswith("The DX coil is selected for R32")
    assert next(f for f in v["ai_findings"] if f["id"] == "P02-AI1")["delta"] == len(v["answer"]["lines"])


def test_unknown_decisions_and_targets_are_refused():
    pkg = fresh()
    for bad in (lambda: decide(pkg, "P02-AI1", "maybe"), lambda: confirm(pkg, [{"kind": "price"}])):
        try:
            bad()
        except ValueError:
            continue
        raise AssertionError("accepted a bad input")


def test_passes_count_only_on_confirmed_readings():
    v = review(fresh())
    assert v["counts"]["passed"] < v["counts"]["would_pass"]   # almost nothing in P02 is confirmed yet
    problem = next(r for r in v["results"] if r["verdict"] == "flag")
    v2 = review(fresh(), dismissed={problem["key"]: "ok"})
    assert v2["counts"]["passed"] == v["counts"]["passed"] and v2["counts"]["dismissed"] == 1


def test_the_answer_lists_problems_before_questions():
    v = review(fresh())
    problems = [r["delta"] for r in v["results"] if r["verdict"] == "flag" and r["delta"]]
    questions = [r["delta"] for r in v["results"] if r["verdict"] == "unclear" and r["delta"]]
    assert max(problems) < min(questions)


def test_originals_are_served_only_from_the_package_folder(tmp_path):
    pkg = {"documents": [{"file": "sheet.pdf"}, {"file": "../outside.pdf"}, {"file": "missing.pdf"}]}
    (tmp_path / "P09").mkdir()
    (tmp_path / "P09" / "sheet.pdf").write_bytes(b"%PDF-1.4")
    (tmp_path / "outside.pdf").write_bytes(b"%PDF-1.4")
    assert original("P09", pkg, 1, raw=tmp_path) == (tmp_path / "P09" / "sheet.pdf").resolve()
    assert original("P09", pkg, 2, raw=tmp_path) is None
    assert original("P09", pkg, 3, raw=tmp_path) is None
    assert original("P09", pkg, 0, raw=tmp_path) is None and original("P09", pkg, 4, raw=tmp_path) is None
