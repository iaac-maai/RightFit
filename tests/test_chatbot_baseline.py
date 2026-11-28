import pymupdf
import pytest

from eval.chatbot_baseline.blind import bot_findings, cut, from_answer, judge_list, page_and_quote, rightfit_findings, run_differences, score


def finding(source, group="", what="x", file="", page="", quote="", package="P01"):
    return {"package": package, "source": source, "group": group, "what": what, "file": file, "page": page,
            "quote": quote, "by_hand": ""}


def test_cut_keeps_the_first_25_words_and_rewrites_nothing():
    text = " ".join(f"w{i}" for i in range(40))
    assert cut(text) == " ".join(f"w{i}" for i in range(25))
    assert cut("short  text") == "short text"


def test_rightfit_findings_are_the_flags_of_the_review_page():
    rows = rightfit_findings("P01")
    assert len(rows) == 13 and {r["source"] for r in rows} == {"rightfit"}
    assert all(len(r["what"].split()) <= 25 for r in rows)


def test_judge_list_merges_groups_and_hides_the_source():
    findings = [finding("rightfit", "g1", "no declaration"), finding("bot1_run1", "g1", "declaration missing"),
                finding("bot2_run1", what="pump too small", page="3")]
    rows, ids = judge_list(findings)
    assert len(rows) == 2 and "source" not in rows[0]
    assert {r["page"] for r in rows} == {"no page given", "3"}
    assert judge_list(findings) == (rows, ids)   # the same findings give the same list


def test_page_and_quote_reads_the_page_text(tmp_path):
    (tmp_path / "P01").mkdir()
    doc = pymupdf.open()
    doc.new_page().insert_text((72, 72), "Protectie termica: extern")
    doc.save(tmp_path / "P01" / "sheet.pdf")
    on = finding("bot1_run1", file="sheet.pdf", page="1", quote="Protecţie termică: extern")   # ţ and ă as typed
    assert page_and_quote(on, tmp_path) is True
    assert page_and_quote({**on, "quote": "Protecţie termică: intern"}, tmp_path) is False
    assert page_and_quote({**on, "page": "2"}, tmp_path) is False
    assert page_and_quote({**on, "file": "missing.pdf"}, tmp_path) is False
    assert page_and_quote({**on, "page": ""}, tmp_path) is None
    assert page_and_quote({**on, "by_hand": "yes", "page": "2"}, tmp_path) is True


def test_score_counts_marks_per_source_and_compares_the_runs():
    findings = [finding("rightfit", "g1"), finding("bot1_run1", "g1"), finding("bot1_run1", what="y"),
                finding("bot1_run2", what="z")]
    judge, ids = judge_list(findings)
    marks = {("P01", "g1"): "real", ("P01", "alone-2"): "not", ("P01", "alone-3"): "?"}
    for r in judge:
        r["mark"] = next(m for g, m in marks.items() if ids[g] == r["id"])
    answers = [{"package": "P01", "source": "bot1_run1", "letter": "B"},
               {"package": "P01", "source": "bot1_run2", "letter": "C"}]
    rows = {r["source"]: r for r in score(findings, judge, answers)}
    assert (rows["rightfit"]["real"], rows["rightfit"]["of_all_real"]) == (1, 1)
    assert (rows["bot1_run1"]["real"], rows["bot1_run1"]["not"], rows["bot1_run2"]["cant_tell"]) == (1, 1, 1)
    assert run_differences(list(rows.values())) == [
        {"package": "P01", "bot": "Claude.ai", "both": 0, "one_only": 3, "same_answer": False}]


def test_score_refuses_marks_that_belong_to_another_list():
    findings = [finding("rightfit", what="a")]
    judge, _ = judge_list(findings)
    judge[0]["mark"] = "real"
    with pytest.raises(ValueError, match="changed"):
        score([finding("rightfit", what="b")], judge, [])
    judge[0]["mark"] = "maybe"
    with pytest.raises(ValueError, match="must be"):
        score(findings, judge, [])


def test_from_answer_keeps_the_chatbots_words_up_to_the_end_of_the_cell():
    text = "|1|Form|**No BOQ** item numbers given.|rule|\n2. **Wrong** `DoC` attached\nmore\n|2|x|No BOQ again|"
    assert from_answer(text, "No BOQ") == "No BOQ item numbers given."
    assert from_answer(text, "No BOQ #2") == "No BOQ again"
    assert from_answer(text, "Wrong") == "Wrong DoC attached"
    with pytest.raises(ValueError):
        from_answer(text, "missing")


def test_bot_findings_reads_the_answer_and_groups_rightfit(tmp_path):
    (tmp_path / "P01_bot1_run1.txt").write_text("|1|No declaration for the set.|")
    split = [{"package": "P01", "source": "bot1_run1", "group": "doc", "anchor": "No declaration", "file": "f.pdf",
              "page": "1", "quote": "q", "by_hand": ""},
             {"package": "P01", "source": "rightfit", "group": "doc", "anchor": "No EU", "file": "", "page": "",
              "quote": "", "by_hand": ""}]
    rows = bot_findings(split, [finding("rightfit", what="No EU declaration")], tmp_path)
    assert [(r["source"], r["group"], r["what"]) for r in rows] == [
        ("rightfit", "doc", "No EU declaration"), ("bot1_run1", "doc", "No declaration for the set.")]
