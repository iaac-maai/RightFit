"""The fit check (spec/features/revit_fit_check.md). A made-up plant room, 5000 x 4000 mm and 2800 mm high,
in the pump's own frame: the set's middle is the origin, x along its length, y towards its front.
The cases are hand written; Luca approves them with the rules in data/space/rules.csv."""
import pytest

from checks.space import space_checks as sc

# Room from x -2000 to 3000 and y -1500 to 2500 (the set stands off-centre).
ROOM = {
    "name": "test room",
    "outline": [[-2000, -1500], [3000, -1500], [3000, 2500], [-2000, 2500]],
    "height": 2800,
    "doors": [{"name": "door 1", "width": 900, "height": 2100, "swing": [1500, 1600, 2400, 2500, 0, 2100]}],
    "obstacles": [{"name": "tank", "category": "Plumbing Fixtures", "box": [-2000, -1500, -1500, 0, 0, 2000]}],
}
SERVICE = {"front": 800, "sides": 600, "top": 500}


def pump_set(**kw):
    s = {"maker": "Maker", "model": "Set A", "L": 1200, "W": 700, "H": 900, "kg": 150, "pumps": 2,
         "p2_each": 4.0, "p2_needed": 3.2, "standby": "pass", "dn_in": 65, "dn_out": 50, "dw_approval": True,
         "status": "verified"}
    s.update(kw)
    return s


def by_check(res):
    return dict((r["check"], r) for r in res["results"])


def test_a_set_with_room_to_spare_passes_every_check_on_verified_values():
    res = sc.fit(pump_set(), ROOM, SERVICE, base_z=100)
    assert [r["result"] for r in res["results"]] == ["pass"] * 6
    assert res["verdict"]["verdict"] == "pass"


def test_unverified_data_sheet_values_say_what_the_result_would_be():
    res = sc.fit(pump_set(status="extracted"), ROOM, SERVICE, base_z=100)
    s1 = by_check(res)["S1"]
    assert (s1["result"], s1["would_be"]) == ("unclear", "pass")
    assert res["verdict"]["verdict"] == "would pass" and not res["verdict"]["confirmed"]


def test_a_set_past_the_wall_or_ceiling_fails_s1():
    wide = by_check(sc.fit(pump_set(L=4400), ROOM, SERVICE))["S1"]
    assert wide["would_be"] == "flag" and wide["blocking"] and "walls" in wide["reason"]
    tall = by_check(sc.fit(pump_set(H=2900), ROOM, {}, base_z=0))["S1"]
    assert "100 mm taller" in tall["reason"]


def test_a_room_corner_poking_into_the_set_counts_as_outside():
    l_room = dict(ROOM, outline=[[-2000, -1500], [3000, -1500], [3000, 2500], [0, 2500], [0, 200], [-2000, 200]])
    assert not sc.inside_outline([-500, -350, 500, 350, 0, 900], l_room["outline"])
    assert sc.inside_outline([100, -350, 900, 350, 0, 900], l_room["outline"])


def test_hitting_the_tank_is_a_blocking_clash_with_its_depth():
    res = sc.fit(pump_set(L=3200), ROOM, {}, base_z=100)  # x from -1600: 100 mm into the tank
    s2 = by_check(res)["S2"]
    assert s2["would_be"] == "flag" and s2["blocking"]
    assert s2["reason"] == "hits tank by 100 mm" and len(s2["boxes"]) == 1
    assert res["verdict"]["verdict"] == "FAIL"


def test_service_space_flags_the_ceiling_walls_and_door_swing_without_blocking():
    res = sc.fit(pump_set(), ROOM, {"front": 2500, "sides": 600, "top": 1900}, base_z=100)
    s3 = by_check(res)["S3"]
    assert s3["would_be"] == "flag" and not s3["blocking"]
    assert "the ceiling cuts the space above the motors by 100 mm" in s3["reason"]
    assert "a wall is in the front space" in s3["reason"]
    swing = by_check(sc.fit(pump_set(L=4000), ROOM, {"front": 1500}, base_z=100))["S3"]
    assert "door 1 (door swing) is in the front space by 250 mm" in swing["reason"]
    assert res["verdict"]["verdict"] == "flag"


def test_no_service_space_set_is_information_only():
    assert by_check(sc.fit(pump_set(), ROOM, {}))["S3"]["result"] == "info"


def test_the_set_goes_through_the_door_on_its_narrow_side_or_fails_s4():
    assert by_check(sc.fit(pump_set(), ROOM, SERVICE))["S4"]["would_be"] == "pass"
    big = by_check(sc.fit(pump_set(L=1300, W=1000), ROOM, {}))["S4"]
    assert big["would_be"] == "flag" and big["blocking"] and "the widest door is 900 x 2100 mm" in big["reason"]
    assert by_check(sc.fit(pump_set(), dict(ROOM, doors=[]), {}))["S4"]["result"] == "unclear"


def test_no_real_standby_fails_and_an_unknown_one_is_unclear():
    no = by_check(sc.fit(pump_set(standby="fail", p2_needed=3.24, p2_each=2.2), ROOM, {}))["S5"]
    assert no["blocking"] and "3.24 kW" in no["reason"] and "2.2 kW" in no["reason"]
    assert by_check(sc.fit(pump_set(standby=None), ROOM, {}))["S5"]["result"] == "unclear"


def test_drinking_water_approval_missing_is_a_flag_not_a_block():
    s6 = by_check(sc.fit(pump_set(dw_approval=False), ROOM, {}))["S6"]
    assert s6["would_be"] == "flag" and not s6["blocking"]
    assert by_check(sc.fit(pump_set(dw_approval=None), ROOM, {}))["S6"]["result"] == "unclear"


OLD = pump_set()
PIPES = [{"name": "suction DN65", "dn": 65, "role": "suction", "end": [-700, 0, 300]},
         {"name": "discharge DN65", "dn": 65, "role": "discharge", "end": [700, 0, 700]}]


def test_swap_to_a_smaller_set_leaves_pipe_ends_short_and_a_size_change_needs_a_reducer():
    new = pump_set(model="Set B", L=800, W=650, dn_in=50, dn_out=50)
    res = sc.swap(new, OLD, ROOM, SERVICE, PIPES, base_z=100)
    k1 = [r for r in res["results"] if r["check"] == "K1"]
    assert "reducer" in k1[0]["reason"] and "300 mm short" in k1[0]["reason"]
    assert "DN65 pipe on a DN50 connection" in k1[1]["reason"]


def test_swap_to_a_longer_set_puts_the_pipe_end_inside_it():
    res = sc.swap(pump_set(L=1600), OLD, ROOM, SERVICE, PIPES[:1], base_z=100)
    k1 = [r for r in res["results"] if r["check"] == "K1"][0]
    assert "100 mm inside the new set" in k1["reason"] and k1["boxes"]


def test_more_motor_power_sends_the_circuit_back_to_the_electrical_engineer_and_never_passes():
    circuit = {"name": "C1", "rating_a": 25}
    up = [r for r in sc.swap(pump_set(p2_each=5.5), OLD, ROOM, {}, [], circuit)["results"] if r["check"] == "K2"][0]
    assert up["would_be"] == "flag" and "from 8 to 11 kW" in up["reason"] and "25 A" in up["reason"]
    down = [r for r in sc.swap(pump_set(p2_each=2.2), OLD, ROOM, {}, [], circuit)["results"] if r["check"] == "K2"][0]
    assert down["result"] == "info"
    unknown = [r for r in sc.swap(pump_set(p2_each=None), OLD, ROOM, {}, [], None)["results"] if r["check"] == "K2"][0]
    assert unknown["result"] == "unclear"


def test_weight_change_is_reported_but_stays_unclear_for_the_structural_engineer():
    k3 = [r for r in sc.swap(pump_set(kg=195), OLD, ROOM, {}, [])["results"] if r["check"] == "K3"][0]
    assert k3["result"] == "unclear" and "45 kg heavier" in k3["reason"]
    assert "not known" in [r for r in sc.swap(pump_set(kg=None), OLD, ROOM, {})["results"]
                           if r["check"] == "K3"][0]["reason"]


def test_table_lists_every_candidate_with_its_verdict():
    rows = sc.table([pump_set(submitted=True), pump_set(model="Set C", standby="fail")], ROOM, SERVICE, 100)
    assert rows[0][1] == "pass" and rows[0][2].endswith("(submitted)")
    assert rows[1][1] == "FAIL" and rows[1][4] == 1


def test_every_rule_a_check_cites_is_in_the_rules_table():
    rules = sc.load_rules()
    rules.update({"RO-OMS275-DW": {}})  # lives in data/maf/rules.csv, used as in H1
    res = sc.swap(pump_set(), OLD, ROOM, SERVICE, PIPES, {"name": "C1"}, 100)
    for r in res["results"]:
        for rid in r["rules"]:
            assert rid in rules, rid


def test_rule_quotes_stay_short_and_pending_rules_say_so():
    for rid, r in sc.load_rules().items():
        assert len(r["quote"].split()) <= 15, rid
        assert r["status"] in ("verified", "to_confirm", "practice"), rid
