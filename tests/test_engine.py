"""The engine of RightFit online (app/engine.py) gives the same review as the laptop's app, and applies a person's
change the same way. It runs on P01, the example package in the repository, with the rule tables of data/maf sent
along as the site sends them."""
import copy
import json
from pathlib import Path

import pytest

from app.engine import handle
from app.review_core import review
from checks.maf.rules import library, load

ROOT = Path(__file__).resolve().parents[1]
P01 = json.loads((ROOT / "data/maf/extracted/P01.json").read_text())
TABLES = {"rules": load("rules.csv"), "family_documents": load("family_documents.csv"), "checklist": load("checklist.csv"),
          "library": library(), "consultant": load("consultant_rules.csv")}


def ask(change=None, decisions=None, pkg=P01):
    return handle(copy.deepcopy({"pkg": pkg, "decisions": decisions or {}, "tables": TABLES, "location": "RO",
                                 "reviewer": "Ana Test", "change": change}))


def test_the_engine_gives_the_laptops_review():
    online, laptop = ask()["view"], review(copy.deepcopy(P01), "RO")
    assert online["status"] == laptop["status"] and online["counts"] == laptop["counts"]
    assert [(r["key"], r["verdict"]) for r in online["results"]] == [(r["key"], r["verdict"]) for r in laptop["results"]]


def test_a_tick_confirms_one_reading_under_the_reviewers_name():
    item = next(i for i in P01["items"] if any(v["status"] != "verified" and v["value"] not in (None, "") for v in i["values"].values()))
    key = next(k for k, v in item["values"].items() if v["status"] != "verified" and v["value"] not in (None, ""))
    before = ask()["view"]["counts"]["to_confirm"]
    out = ask({"op": "confirm", "targets": [{"kind": "value", "item": item["id"], "key": key, "verified": True}]})
    entry = next(i for i in out["pkg"]["items"] if i["id"] == item["id"])["values"][key]
    assert (entry["status"], entry["checked_by"]) == ("verified", "Ana Test")
    assert out["view"]["counts"]["to_confirm"] == before - 1


def test_a_finding_marked_not_a_problem_leaves_the_answer():
    first = next(r for r in ask()["view"]["results"] if r["verdict"] == "flag")
    out = ask({"op": "decisions", "decisions": {first["key"]: {"decision": "dismissed", "reason": "agreed on site"}}})
    after = next(r for r in out["view"]["results"] if r["key"] == first["key"])
    assert after["dismissed"] == "agreed on site" and after["verdict"] == "pass"
    assert first["comment"] not in out["view"]["answer"]["lines"]
    assert out["decisions"][first["key"]]["decided_by"] == "Ana Test"


def test_a_consultants_rule_switched_off_stops_its_findings():
    on = [r for r in ask()["view"]["results"] if r["check"] == "P"]
    rule = on[0]["rules"][0]["id"]
    out = handle(copy.deepcopy({"pkg": P01, "tables": TABLES, "change": {"op": "rule_active", "rule_id": rule, "active": False}}))
    assert next(r for r in out["consultant"] if r["rule_id"] == rule)["active"] == "no"
    assert not any(rule in [u["id"] for u in r["rules"]] for r in out["view"]["results"])


def test_a_change_the_engine_does_not_know_is_refused():
    with pytest.raises(ValueError):
        ask({"op": "approve"})


def test_a_rule_written_by_hand_is_checked_and_numbered_after_the_others():
    rule = {"family": "pump", "kind": "brand", "value": "Grundfos", "effect": "B", "text": "pumps only from Grundfos"}
    out = handle(copy.deepcopy({"tables": TABLES, "change": {"op": "new_rule", "rule": rule}}))
    last = out["consultant"][-1]
    assert (last["rule_id"], last["active"], last["value"]) == (f"CR-{len(TABLES['consultant']) + 1:02d}", "yes", "Grundfos")
    with pytest.raises(ValueError, match="must be a number"):
        handle(copy.deepcopy({"tables": TABLES, "change": {"op": "new_rule", "rule": {
            "kind": "value", "field": "max_pressure", "operator": ">=", "value": "sixteen", "effect": "B", "text": "PN 16"}}}))
