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
    # P01's readings are all confirmed by now, so one is put back to what the AI left before the tick
    pkg = copy.deepcopy(P01)
    item = pkg["items"][0]
    key = next(k for k, v in item["values"].items() if v["value"] not in (None, ""))
    item["values"][key].update(status="extracted", checked_by=None, verified_on=None)
    before = ask(pkg=pkg)["view"]["counts"]["to_confirm"]
    out = ask({"op": "confirm", "targets": [{"kind": "value", "item": item["id"], "key": key, "verified": True}]}, pkg=pkg)
    entry = next(i for i in out["pkg"]["items"] if i["id"] == item["id"])["values"][key]
    assert (entry["status"], entry["checked_by"]) == ("verified", "Ana Test")
    assert out["view"]["counts"]["to_confirm"] == before - 1


def test_a_reading_confirmed_from_another_package_keeps_where_and_loses_it_when_unticked():
    pkg = copy.deepcopy(P01)
    doc = pkg["documents"][0]
    doc.update(status="extracted", checked_by=None, verified_on=None)   # P01's documents are all confirmed by now
    where = "this project, P09 (MAF IS 015 rev 0), confirmed by Ana on 2026-11-11"
    out = ask({"op": "confirm", "targets": [{"kind": "document", "file": doc["file"], "verified": True, "from": where}]}, pkg=pkg)
    shown = next(d for d in out["view"]["documents"] if d["file"] == doc["file"])
    assert (shown["status"], shown["checked_by"], shown["confirmed_in"]) == ("verified", "Ana Test", where)
    again = ask({"op": "confirm", "targets": [{"kind": "document", "file": doc["file"], "verified": False}]}, pkg=out["pkg"])
    assert next(d for d in again["pkg"]["documents"] if d["file"] == doc["file"]).get("confirmed_in") is None


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


def test_the_dates_sent_with_the_request_date_the_review():
    out = handle(copy.deepcopy({"pkg": P01, "tables": TABLES, "review": "2026-12-01", "delivery": "2027-02-01"}))["view"]
    assert (out["review"], out["delivery"]) == ("2026-12-01", "2027-02-01")
    with pytest.raises(ValueError, match="2026-03-16"):
        handle(copy.deepcopy({"pkg": P01, "tables": TABLES, "review": "1 Dec"}))


def test_the_booster_sizing_is_the_laptops():
    from app.booster import booster_view
    assert handle({"tool": "booster", "args": {"flats": 40, "floors": 10, "submitted": "GHV20/5SV16"}}) == booster_view(40, 10, "GHV20/5SV16")
    assert len(handle({"tool": "booster_sets"})["sets"]) > 100
