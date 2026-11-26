"""The Revit link's plain part (rf_online_core in the Revit add-in, spec/features/revit_link.md): the check sent to
RightFit online, the outbox, the project folder's online project and the site's copy. The room and the set are made up."""
import json
import os
import sys

LIB = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "revit", "RightFit.extension", "lib")
if LIB not in sys.path:
    sys.path.insert(0, LIB)

import rf_online_core as core  # noqa: E402  (plain Python, no Revit inside)

ROOM = {"name": "B-01", "kind": "room", "height": 3000,
        "outline": [[-1000, -2000], [3000, -2000], [3000, 1000], [-1000, 1000]],
        "doors": [{"name": "door B1", "width": 900, "height": 2100, "swing": [0, 0, 1, 1, 0, 2100], "id": 7}],
        "obstacles": [{"name": "tank", "box": [0, 0, 1000, 500, 0, 1500], "id": 8}], "pipes": [{"name": "pipe DN80", "dn": 80, "end": [0, 0, 0], "id": 9}]}
RES = {"set": {"id": "a", "maker": "Maker", "model": "Booster XB", "submitted": True, "L": 1000, "W": 600, "H": 800, "status": "verified",
               "zones": "not sent"},
       "verdict": {"verdict": "flag", "confirmed": True},
       "results": [{"check": "S1", "result": "pass", "would_be": "pass", "reason": "inside the room", "rules": ["R-1"], "boxes": [[1, 2]]},
                   {"check": "S3", "result": "flag", "would_be": "flag", "reason": "tank in the front space", "rules": ["R-2"],
                    "blocking": False, "boxes": []}]}
RULES = {"R-1": {"status": "verified"}}


def test_a_check_carries_room_set_verdict_and_results_with_rule_status():
    p = core.run_payload("check", ROOM, RES, RULES, model_file="Project1.rvt", ran_at="2026-11-26T13:00:00", computer="JEK")
    assert p["action"] == "check" and p["model_file"] == "Project1.rvt" and p["computer"] == "JEK"
    assert p["room"]["length"] == 4000 and p["room"]["width"] == 3000 and p["room"]["area"] == 12
    assert p["room"]["doors"] == [{"name": "door B1", "width": 900, "height": 2100}]
    assert p["room"]["things"][0]["name"] == "tank"
    assert p["set"]["model"] == "Booster XB" and "zones" not in p["set"]
    assert p["verdict"] == {"verdict": "flag", "confirmed": True}
    assert p["results"][0]["rules"] == ["R-1 (verified)"] and p["results"][1]["rules"] == ["R-2"]
    assert all("boxes" not in r for r in p["results"])  # the drawing stays in Revit
    json.dumps(p)  # it travels as JSON


def test_checks_wait_in_the_outbox_oldest_first(tmp_path):
    base = str(tmp_path)
    assert core.waiting(base) == []
    first = core.keep_for_later("proj-1", {"n": 1}, base)
    core.keep_for_later("proj-2", {"n": 2}, base)
    items = core.waiting(base)
    assert [(i[1], i[2]["n"]) for i in items] == [("proj-1", 1), ("proj-2", 2)]
    core.done(first)
    assert [i[2]["n"] for i in core.waiting(base)] == [2]


def test_a_project_folder_links_to_one_online_project():
    s = {"project": "IS015"}
    assert core.linked_project(s) is None
    core.set_linked_project(s, "abc", "IS015 online")
    assert core.linked_project(s) == {"id": "abc", "name": "IS015 online"}
    assert core.linked_project({"project": "OTHER", "online_projects": s["online_projects"]}) is None
    core.set_linked_project(s, None, None)
    assert core.linked_project(s) is None


def test_the_sites_copy_is_kept_and_a_missing_file_falls_back(tmp_path):
    base = str(tmp_path)
    core.save_cache("abc", {"candidates": {"sets": [{"id": "a"}]}, "project": None, "chosen": {"setLabel": "X"}}, base)
    assert core.cached("abc", "candidates.json", base) == {"sets": [{"id": "a"}]}
    assert core.cached("abc", "project.json", base) is None  # the project folder's own is used
    assert core.cached("abc", "chosen.json", base)["chosen"] == {"setLabel": "X"}


def test_the_token_is_kept_and_forgotten(tmp_path):
    base = str(tmp_path)
    assert core.link(base)["token"] is None and core.link(base)["url"].startswith("https://")
    core.save_link({"url": core.SITE, "token": "rfr_x", "user": {"name": "Jeff"}}, base)
    assert core.link(base)["token"] == "rfr_x"
    core.forget_link(base)
    assert core.link(base)["token"] is None


def test_the_report_names_the_reviewers_choice():
    assert core.chosen_text(None) is None
    line = core.chosen_text({"setLabel": "DAB KVC", "chosenBy": "Luca", "chosenAt": "2026-11-26T12:00:00Z", "note": "fits"})
    assert "DAB KVC" in line and "Luca" in line and "2026-11-26" in line and '"fits"' in line


def test_sizes_from_the_site_are_decimals_again(tmp_path):
    """The site writes 1210.0 as 1210; Revit's Python 2.7 can't print a whole number with "{:.0f}"."""
    base = str(tmp_path)
    core.save_cache("abc", {"candidates": {"sets": [{"id": "a", "L": 1210, "kg": 149, "pumps": 2, "dn_in": 80, "submitted": True}]}}, base)
    s = core.cached("abc", "candidates.json", base)["sets"][0]
    assert isinstance(s["L"], float) and isinstance(s["kg"], float)
    assert s["pumps"] == 2 and isinstance(s["pumps"], int) and isinstance(s["dn_in"], int) and s["submitted"] is True


def test_a_message_runs_only_on_the_linked_project():
    s = {"project": "IS015"}
    cmd = {"projectId": "abc", "setId": "a"}
    assert "No model" in core.why_not(s, cmd, have_model=False)
    assert "no project folder linked" in core.why_not(s, cmd)
    core.set_linked_project(s, "xyz", "Other project")
    assert "another project" in core.why_not(s, cmd)
    core.set_linked_project(s, "abc", "Sala Nadia")
    assert core.why_not(s, cmd) is None


def test_revit_answers_with_the_set_and_its_results():
    assert core.find_set([{"id": "a"}, {"id": "b", "model": "X"}], "b") == {"id": "b", "model": "X"}
    assert core.find_set([{"id": "a"}], "z") is None
    text = core.shown_text("Maker Booster XB", RES)
    assert text == "Revit shows Maker Booster XB: flag (1 flag, 1 pass)."
    unsure = dict(RES, verdict={"verdict": "flag", "confirmed": False})
    assert "flag (would be)" in core.shown_text("X", unsure)
