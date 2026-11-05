"""Draft status (spec section 7) and draft comments (spec section 8)."""
from checks.maf.checks import result
from checks.maf.status import draft_status
from explain.maf_comments import comment
from maf_cases import v


def test_status_c_when_a_blocking_result_flags():
    results = [result("D1", "flag", "no data sheet", blocking=True), result("D3", "pass", "ok")]
    assert draft_status(results)[0] == "C"


def test_status_b_on_any_flag_or_unclear_and_a_when_all_pass_or_info():
    assert draft_status([result("D2", "flag", "x"), result("R", "info", "y")])[0] == "B"
    assert draft_status([result("V1", "unclear", "x")])[0] == "B"
    assert draft_status([result("V1", "pass", "x"), result("R", "info", "y")]) == ("A", ["every check is pass or info"])


def test_status_once_verified_uses_the_would_be_verdict():
    results = [result("D1", "flag", "no data sheet", [v(None, status="extracted")], blocking=True)]
    assert draft_status(results)[0] == "B"
    assert draft_status(results, "would_be")[0] == "C"


def test_comment_d2_matches_the_spec_example():
    r = result("D2", "flag", "x", code="D2.no_match", params={"covers": "SL1, SLV", "items": "Hydro Multi-E"})
    assert comment(r) == ("The declaration of conformity attached for SL1, SLV matches no product in the MAF; "
                          "please attach the declarations for Hydro Multi-E.")


def test_no_comment_for_a_pass_waiting_for_verification_but_one_for_a_flag():
    waiting_pass = result("V1", "pass", "x", [v(1, status="extracted")], code="V1.below", params={"item": "P", "got": ""})
    assert comment(waiting_pass) is None
    waiting_flag = result("D1", "flag", "x", [v(1, status="extracted")], code="D1.missing",
                          params={"item": "DPK", "doc_type": "eu_declaration_of_conformity"})
    assert comment(waiting_flag) == "The EU declaration of conformity for DPK is missing; please attach it."


def test_no_comment_without_a_template():
    assert comment(result("E1", "unclear", "no rule for this location")) is None


def test_an_accepted_ai_suggestion_makes_an_a_into_a_b():
    results = [result("V1", "pass", "x"), result("R", "info", "y")]
    assert draft_status(results, accepted=["Refrigerant differs"]) == (
        "B", ["AI suggestion added to the answer: Refrigerant differs"])
    blocking = [result("D1", "flag", "no data sheet", blocking=True)]
    assert draft_status(blocking, accepted=["x"])[0] == "C"
