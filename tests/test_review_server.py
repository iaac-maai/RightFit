"""The PoC review page's server: the view it builds from the checks, and the reviewer's changes."""
import copy
import json
from pathlib import Path

import pymupdf

from app.review_server import confirm, decide, find_marks, original, package_list, page_png, review
from explain.maf_comments import comment, title

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


def sheet(tmp_path):
    """A one-page PDF where a label and its value are two separate pieces of text, as on the data sheets."""
    doc = pymupdf.open()
    page = doc.new_page()
    page.insert_text((60, 100), "Rated power - P2:")
    page.insert_text((300, 100), "1.2 kW")
    page.insert_text((60, 140), "Rated power - P1:")
    page.insert_text((300, 140), "1.9 kW")
    path = tmp_path / "sheet.pdf"
    doc.save(path)
    return path


def test_a_label_and_its_value_are_marked_as_one_line(tmp_path):
    marks = find_marks(sheet(tmp_path), 1, ["Rated power - P2: 1.2 kW", "Rated power - P1: 1.9 kW", "Motor speed: 2785 rpm"])
    (x, y, w, _), = marks[0]
    assert x < 15 and w > 40 and y < 15   # from the label across to the value, on the first line only
    assert marks[1][0][1] > y   # the second quote is on the second line
    assert marks[2] == []   # a quote that is not on the page gets no mark


def test_a_page_is_an_image_and_a_missing_page_is_nothing(tmp_path):
    path = sheet(tmp_path)
    assert page_png(path, 1).startswith(b"\x89PNG")
    assert page_png(path, 2) is None and page_png(b"not a pdf", 1) is None


def test_the_package_list_never_carries_the_zip_name(tmp_path):
    (tmp_path / "batch2_inventory.csv").write_text(
        "package,code,revision,discipline,product,files,pdf_pages,pdfs_without_text,zip\n"
        "P02,IV 004,4,HVAC,air handling unit,0,0,0,secret.zip\nP03,IS 013,0,plumbing,pipe insulation,3,17,0,secret.zip\n")
    data = Path(__file__).resolve().parents[1] / "data/maf/extracted"
    listing = package_list(data, tmp_path)
    assert "secret" not in json.dumps(listing)
    assert [p["id"] for p in listing] == ["P01", "P02", "P03"]   # P02 is read, so its inventory row does not repeat it
    assert listing[1]["letter"] == "B" and listing[2]["letter"] is None and listing[2]["discipline"] == "Plumbing"


def test_findings_have_a_short_title_and_plain_words():
    r = {"code": "C.CL-12", "params": {"item": "UNILIFT", "missing": "starting_method"}, "result": "flag", "would_be": "flag"}
    assert title(r) == "Starting method not stated"
    assert comment(r) == "Please complete the electrical data for UNILIFT: starting method."
    assert all(x["title"] for x in review(fresh())["results"])


def test_a_dismissed_problem_keeps_its_title():
    p = next(r for r in review(fresh())["results"] if r["verdict"] == "flag" and r["title"] != r["check_name"])
    after = next(r for r in review(fresh(), dismissed={p["key"]: "ok"})["results"] if r["key"] == p["key"])
    assert after["title"] == p["title"]
