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
    assert comment(r) == ("Declarația de conformitate atașată pentru SL1, SLV nu corespunde niciunui produs din MAF; "
                          "vă rugăm atașați declarațiile pentru Hydro Multi-E.")
    assert comment(r, "en").startswith("The declaration of conformity attached for SL1, SLV")


def test_no_comment_for_a_pass_waiting_for_verification_but_one_for_a_flag():
    waiting_pass = result("V1", "pass", "x", [v(1, status="extracted")], code="V1.below", params={"item": "P", "got": ""})
    assert comment(waiting_pass) is None
    waiting_flag = result("D1", "flag", "x", [v(1, status="extracted")], code="D1.missing",
                          params={"item": "DPK", "doc_type": "eu_declaration_of_conformity"})
    assert comment(waiting_flag) == "Lipsește declarația de conformitate UE pentru DPK; vă rugăm atașați documentul."


def test_no_comment_without_a_template():
    assert comment(result("E1", "unclear", "no rule for this location")) is None
