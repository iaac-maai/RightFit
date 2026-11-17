"""The rule watch (MAF-10), on small answers saved from the three official sources. Nothing here goes online."""
from pathlib import Path

import pytest

from checks.maf.rules import load
from ingest.rule_watch import NOT_LAW, act_of, read_es, read_eu, read_ro, watch

SAVED = Path(__file__).parent / "rule_watch"   # real answers of 17 Nov 2026, cut to what the watch reads


def saved(name):
    return (SAVED / name).read_text()


def rule(url, **fields):
    return {"rule_id": "X", "topic": "", "source_url": url, "status": "verified_official",
            "verified_on": "2026-11-16", "valid_to": "", **fields}


MACHINERY = rule("https://eur-lex.europa.eu/eli/dir/2006/42/oj", valid_to="2027-01-19")
REPEALED = rule("https://www.boe.es/buscar/act.php?id=BOE-A-2003-14408")   # RD 865/2003
NEVER_AMENDED = rule("https://legislatie.just.ro/Public/DetaliiDocument/262281")   # I9-2022
ANSWERS = {("EU", "32006L0042"): saved("eu_32006L0042.xml"), ("ES", "BOE-A-2003-14408"): saved("es_BOE-A-2003-14408.xml"),
           ("RO", "262281"): saved("ro_262281.html")}


def results(*rules, answers=ANSWERS):
    return [(r["result"], r["date"]) for r in watch(rules, answers)]


@pytest.mark.parametrize("url, act", [
    ("https://eur-lex.europa.eu/eli/dir/2006/42/oj", ("EU", "32006L0042")),
    ("https://eur-lex.europa.eu/eli/reg_del/2024/370/oj", ("EU", "32024R0370")),
    ("https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:02011R0305-20260529", ("EU", "32011R0305")),
    ("https://www.boe.es/buscar/act.php?id=BOE-A-2006-5515", ("ES", "BOE-A-2006-5515")),
    ("https://www.boe.es/eli/es/rd/2023/01/10/3", ("ES", "https://www.boe.es/eli/es/rd/2023/01/10/3")),
    ("https://legislatie.just.ro/Public/DetaliiDocumentAfis/313329", ("RO", "313329")),
    ("", None),
])
def test_the_act_comes_from_the_rule_source_link(url, act):
    assert act_of(rule(url)) == act


def test_a_harmonised_standard_is_watched_through_the_decision_that_lists_them():
    hen = rule("https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=uriserv:OJ.C_.2018.092.01.0139.01.ENG",
               topic="doc.harmonised_standard")
    assert act_of(hen) == ("EU", "32019D0451")


def test_every_legal_rule_with_a_source_link_names_an_act():
    assert all(act_of(r) for r in load("rules.csv") if r["status"] not in NOT_LAW and r["source_url"])


def test_reading_the_saved_answers():
    assert read_eu(saved("eu_32006L0042.xml")) == {"latest": "2026-05-30", "ends": "2027-01-19", "in_force": True}
    assert read_es(saved("es_BOE-A-2006-5515.xml")) == {"latest": "2025-12-18", "ends": None, "in_force": True}
    # Repealed from 2 Jan 2023 (the BOE's date), so it applied until 1 Jan 2023, the way valid_to counts.
    assert read_es(saved("es_BOE-A-2003-14408.xml")) == {"latest": "2025-12-18", "ends": "2023-01-01", "in_force": False}
    assert read_ro(saved("ro_307735.html"))["latest"] == "2026-08-25"
    assert read_ro(saved("ro_262281.html"))["latest"] is None


def test_a_version_after_the_day_the_rule_was_read_is_a_change():
    assert results(MACHINERY) == [("unchanged", "2026-05-30")]
    assert results({**MACHINERY, "verified_on": "2026-05-01"}) == [("changed", "2026-05-30")]
    assert results(NEVER_AMENDED) == [("unchanged", None)]


def test_an_end_the_rule_does_not_have_is_a_change():
    assert results({**MACHINERY, "valid_to": ""}) == [("changed", "2027-01-19")]
    assert results({**MACHINERY, "valid_to": "2027-06-30"}) == [("changed", "2027-01-19")]
    assert results(REPEALED) == [("changed", "2023-01-01")]
    assert results({**REPEALED, "valid_to": "2023-01-01"}) == [("unchanged", "2025-12-18")]


def test_no_answer_or_a_wrong_page_is_never_read_as_unchanged():
    error_page = '<html><head><title>Object moved</title></head><body><a href="/Error">here</a></body></html>'
    for answers in ({("RO", "262281"): error_page}, {("RO", "262281"): OSError("timed out")}, {}):
        assert results(NEVER_AMENDED, answers=answers) == [("not_checked", None)]
    assert "timed out" in watch([NEVER_AMENDED], {("RO", "262281"): OSError("timed out")})[0]["detail"]
    assert results(rule("")) == [("not_checked", None)]


def test_rules_from_practice_are_not_asked_about():
    assert watch([rule("", status="practice"), rule("", status="engineer_input")], {}) == []
