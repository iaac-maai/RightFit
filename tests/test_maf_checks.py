"""One or more hand-written cases per MAF check (spec section 6). Cases to be approved by Luca."""
from datetime import date

from checks.maf import checks as c
from checks.maf.rules import CHAINS, active_ids, tables
from maf_cases import DECL, PUMP, SHEET, ctx, doc, item, pkg, v


def only(results, check=None):
    results = [r for r in results if check is None or r["check"] == check]
    assert len(results) == 1, results
    return results[0]


# ---------------------------------------------------------------- shared rules

def test_covers_matches_model_or_range_and_ignores_other_products():
    assert c.covers(SHEET, PUMP)
    assert c.covers(DECL, PUMP)  # "Unilift AP" is the range
    assert not c.covers(doc("x", "eu_declaration_of_conformity", ["SL1", "SLV"]), PUMP)


def test_pass_on_extracted_values_is_unclear_until_verified():
    r = c.result("V1", "pass", "ok", [v(1, status="extracted")])
    assert (r["result"], r["would_be"]) == ("unclear", "pass")
    assert c.result("V1", "pass", "ok", [v(1)])["result"] == "pass"


def test_location_chain_and_rule_dates():
    rules, _, _ = tables()
    assert CHAINS["ES"] == ["EU", "ES", "ANY"]
    # Machinery Directive until 19 Jan 2027, Machinery Regulation from 20 Jan 2027.
    assert active_ids("EU-MACH-DOC;EU-MACH-REG", rules, date(2027, 1, 19)) == ["EU-MACH-DOC"]
    assert active_ids("EU-MACH-DOC;EU-MACH-REG", rules, date(2027, 1, 20)) == ["EU-MACH-REG"]
    # Romania: Law 10/1995 until 24 Aug 2026, the construction Code (Law 169/2026) from 25 Aug 2026.
    assert active_ids("RO-L10-11-3;RO-L169-378-3", rules, date(2026, 8, 24)) == ["RO-L10-11-3"]
    assert active_ids("RO-L10-25-F;RO-L169-452-3-G", rules, date(2026, 8, 25)) == ["RO-L169-452-3-G"]


# ---------------------------------------------------------------- D

def test_d1_missing_data_sheet_blocks_and_missing_declaration_does_not():
    results = c.d1_required_documents(pkg([PUMP], [DECL]), ctx())
    sheet = next(r for r in results if r["params"].get("doc_type") == "data_sheet")
    assert (sheet["result"], sheet["blocking"]) == ("flag", True)
    results = c.d1_required_documents(pkg([PUMP], [SHEET]), ctx())
    decl = next(r for r in results if r["params"].get("doc_type") == "eu_declaration_of_conformity")
    assert (decl["result"], decl["blocking"]) == ("flag", False)


def test_d1_passes_when_both_documents_name_the_item():
    assert {r["result"] for r in c.d1_required_documents(pkg([PUMP], [SHEET, DECL]), ctx())} == {"pass"}


def test_d2_flags_a_declaration_for_other_products_and_names_items_without_one():
    booster = item("I2", "pump", "Hydro Multi-E 2 CME 15-2", "Hydro Multi-E")
    wrong = doc("slv.pdf", "eu_declaration_of_conformity", ["SL1", "SLV"])
    results = c.d2_declarations_match(pkg([PUMP, booster], [wrong, DECL]), ctx())
    flagged = next(r for r in results if r["doc"] == "slv.pdf")
    assert flagged["result"] == "flag" and flagged["params"]["items"] == "Hydro Multi-E 2 CME 15-2"
    assert next(r for r in results if r["doc"] == "doc.pdf")["result"] == "pass"


def test_d3_expired_renew_before_delivery_valid_and_no_date():
    docs = [doc("old.pdf", "product_certificate", [], valid_until="2026-03-01"),
            doc("soon.pdf", "product_certificate", [], valid_until="2026-03-31"),
            doc("ok.pdf", "product_certificate", [], valid_until="2026-09-30"),
            doc("decl.pdf", "eu_declaration_of_conformity", [])]
    by_doc = {r["doc"]: r for r in c.d3_in_date(pkg([], docs), ctx())}
    assert by_doc["old.pdf"]["code"] == "D3.expired" and by_doc["old.pdf"]["result"] == "flag"
    assert by_doc["soon.pdf"]["code"] == "D3.renew" and by_doc["soon.pdf"]["result"] == "flag"
    assert by_doc["ok.pdf"]["result"] == "pass"
    assert by_doc["decl.pdf"]["result"] == "info"


def test_d4_label_types():
    assert c.expected_type("FT DPK15803050D") == "data_sheet"
    assert c.expected_type("FISA TEHNICA CTA") == "data_sheet"
    assert c.expected_type("Declaratie conformitate HISENSE") == "eu_declaration_of_conformity"
    assert c.expected_type("TUV CTA") == "product_certificate"
    assert c.expected_type("RAPORT DE SIMULARE -15grC") == "selection_report"
    assert c.expected_type("Software") is None


def test_d4_missing_attachment_wrong_type_and_unlisted_document():
    tuv = doc("tuv.pdf", "other_certificate", [], listed_as="TUV CTA")
    extra = doc("extra.pdf", "eu_declaration_of_conformity", [])
    results = c.d4_documents_as_listed(pkg([], [SHEET, tuv, extra], ["FT UNILIFT_AP1250113", "TUV CTA", "Raport"]),
                                       ctx())
    codes = {r["code"]: r["result"] for r in results if r["code"]}
    assert codes == {"D4.type": "flag", "D4.not_found": "flag"}
    assert next(r for r in results if r["doc"] == "extra.pdf")["result"] == "info"
    assert next(r for r in results if r["doc"] == "ft.pdf")["result"] == "pass"


# ---------------------------------------------------------------- V and E

def test_v1_converts_units_and_compares_exactly():
    assert only(c.v1_duty_point(pkg([PUMP], []), ctx()))["result"] == "pass"
    pump = item("I3", "pump", "P", duty_flow=v(38, "m3/h"), duty_head=v(15, "m"),
                flow=v(10.4, "l/s"), head=v(14.9, "m"))  # 10.4 l/s = 37.44 m3/h
    r = only(c.v1_duty_point(pkg([pump], []), ctx()))
    assert (r["result"], r["code"]) == ("flag", "V1.below") and "flow" in r["reason"] and "head" in r["reason"]


def test_v1_uses_the_engineer_tolerance_once_set():
    rules, family_docs, checklist = tables()
    rules["ENG-DUTY-TOL"] = {**rules["ENG-DUTY-TOL"], "value": "5"}
    pump = item("I4", "pump", "P", duty_flow=v(10, "m3/h"), flow=v(9.6, "m3/h"))
    context = c.context("RO", date(2026, 3, 16), date(2026, 4, 6), data=(rules, family_docs, checklist))
    assert only(c.v1_duty_point(pkg([pump], []), context))["result"] == "pass"


def test_v1_missing_duty_point_is_unclear():
    pump = item("I5", "pump", "P", duty_flow=v(10, "m3/h"))
    assert only(c.v1_duty_point(pkg([pump], []), ctx()))["result"] == "unclear"


def test_v2_info_without_requirement_and_flag_below_it():
    pump = item("I6", "pump", "P", max_pressure=v(5.7, "bar"))
    assert only(c.v2_pressure(pkg([pump], []), ctx()))["result"] == "info"
    assert only(c.v2_pressure(pkg([pump], []), ctx(pressure_bar=6)))["result"] == "flag"


def test_v3_info_without_project_temperature_then_pass_or_flag():
    pump = item("I7", "pump", "P", application=v("booster"), liquid_temp_range=v("5 .. 60", "°C"))
    assert only(c.v3_liquid_temperature(pkg([pump], []), ctx()))["result"] == "info"
    assert only(c.v3_liquid_temperature(pkg([pump], []), ctx(liquid_temp_c={"booster": (10, 25)})))["result"] == "pass"
    r = only(c.v3_liquid_temperature(pkg([pump], []), ctx(liquid_temp_c={"booster": (10, 70)})))
    assert (r["result"], r["code"]) == ("flag", "V3.outside")


def test_v3_reads_signs_and_says_unclear_when_the_range_cannot_be_read():
    assert c.temp_range(v("-10 .. +120", "°C")) == (-10.0, 120.0)
    pump = item("I8", "pump", "P", application=v("booster"), liquid_temp_range=v("see the manual", "°C"))
    r = only(c.v3_liquid_temperature(pkg([pump], []), ctx(liquid_temp_c={"booster": (10, 25)})))
    assert (r["result"], r["code"]) == ("unclear", "V3.missing")


def test_h1_asks_booster_sets_only_for_a_drinking_water_approval():
    booster = item("I9", "pump", "CME 15-2", application=v("booster"))
    drainage = item("I10", "pump", "AP12", application=v("drainage"))
    r = only(c.h1_drinking_water(pkg([booster, drainage], []), ctx()))
    assert (r["result"], r["code"], r["item"], r["rules"]) == ("flag", "H1.missing", "I9", ["RO-OMS275-DW"])
    approval = doc("aviz.pdf", "drinking_water_approval", ["CME 15-2"])
    assert only(c.h1_drinking_water(pkg([booster], [approval]), ctx()))["result"] == "pass"


def test_h1_adds_the_eu_declaration_from_31_dec_2026_and_has_no_rule_for_spain_before():
    booster = item("I11", "pump", "CME 15-2", application=v("booster"))
    r = only(c.h1_drinking_water(pkg([booster], []), ctx(review=date(2026, 12, 31))))
    assert set(r["rules"]) == {"RO-OMS275-DW", "EU-DW-DOC"}
    # Spain: the manufacturer's responsible declaration until 30 Dec 2026, then the EU declaration.
    assert only(c.h1_drinking_water(pkg([booster], []), ctx("ES")))["rules"] == ["ES-RD3-DTU-DW"]
    assert only(c.h1_drinking_water(pkg([booster], []), ctx("ES", review=date(2026, 12, 31))))["rules"] == ["EU-DW-DOC"]


def test_h1_asks_hot_water_pumps_but_not_heating_circulation_pumps():
    hot = item("I12", "pump", "COMFORT", application=v("dhw_circulation"))
    heating = item("I13", "pump", "MAGNA", application=v("circulation"))
    assert [r["item"] for r in c.h1_drinking_water(pkg([hot, heating], []), ctx())] == ["I12"]


def test_v3_hot_water_pumps_must_take_the_temperature_the_law_sets():
    pump = item("I14", "pump", "P", application=v("dhw_circulation"), liquid_temp_range=v("2 .. 55", "°C"))
    r = only(c.v3_liquid_temperature(pkg([pump], []), ctx()))  # Romania, I9-2022 art. 23.7: 60 °C
    assert (r["result"], r["rules"]) == ("flag", ["RO-I9-23-7"])
    pump["values"]["liquid_temp_range"] = v("2 .. 95", "°C")
    assert only(c.v3_liquid_temperature(pkg([pump], []), ctx("ES")))["result"] == "pass"  # Spain asks 70 °C


def ahu(**values):
    base = dict(hrs_type=v("rotary heat exchanger"), hrs_efficiency=v(76, "%"), sfp_int=v(868, "W/(m3/s)"),
                sfp_int_limit=v(890, "W/(m3/s)"), filter_warning=v(True))
    return item("A1", "ahu", "Z096096GBVA", "CAIRplus", **{**base, **values})


def test_e1_passes_the_p02_values():
    assert [r["result"] for r in c.e1_ecodesign(pkg([ahu()], []), ctx())] == ["pass", "pass", "pass"]


def test_e1_heat_recovery_limit_depends_on_the_type():
    assert c.e1_ecodesign(pkg([ahu(hrs_efficiency=v(70, "%"))], []), ctx())[0]["result"] == "flag"
    run_around = ahu(hrs_type=v("run around coil"), hrs_efficiency=v(70, "%"))
    assert c.e1_ecodesign(pkg([run_around], []), ctx())[0]["result"] == "pass"  # 68 % for run around coils


def test_e1_flags_sfp_over_limit_and_no_filter_warning():
    results = c.e1_ecodesign(pkg([ahu(sfp_int=v(900, "W/(m3/s)"), filter_warning=v(False))], []), ctx())
    assert [r["result"] for r in results] == ["pass", "flag", "flag"]


def test_e1_without_a_rule_for_the_location_is_unclear():
    rules, family_docs, checklist = tables()
    rules = {k: r for k, r in rules.items() if not k.startswith("EU-ECO")}
    context = c.context("ES", date(2026, 3, 16), date(2026, 4, 6), data=(rules, family_docs, checklist))
    results = c.e1_ecodesign(pkg([ahu()], []), context)
    assert {r["result"] for r in results} == {"unclear"} and "no rule" in results[0]["reason"]


def test_d1_asks_a_fire_damper_for_a_declaration_of_performance():
    damper = item("I1", "fire_damper", "FD-200")
    sheet = doc("ft.pdf", "data_sheet", ["FD-200"])
    flagged = [r for r in c.d1_required_documents(pkg([damper], [sheet]), ctx()) if r["result"] == "flag"]
    assert [r["rules"] for r in flagged] == [["EU-CPR-DOP", "EU-HEN-15650"]]
    assert "declaration of performance" in flagged[0]["reason"] and not flagged[0]["blocking"]
    dop = doc("dop.pdf", "declaration_of_performance", ["FD-200"])
    assert {r["result"] for r in c.d1_required_documents(pkg([damper], [sheet, dop]), ctx())} == {"pass"}


def test_d1_says_so_when_a_family_has_no_documents_listed():
    results = c.d1_required_documents(pkg([item("I1", "door_closer", "X1")], []), ctx())
    assert [r["result"] for r in results] == ["unclear"] and "door_closer" in results[0]["reason"]


def test_every_rule_named_for_a_family_exists_and_covers_it():
    rules, family_docs, _ = tables()
    for r in family_docs:
        for rule_id in r["rule_id"].split(";"):
            assert rule_id in rules, f"{r['family']}: {rule_id} is not in rules.csv"
            if rules[rule_id]["applies_to"] != "all":
                assert set(r["family"].split(";")) <= set(rules[rule_id]["applies_to"].split(";")), (r["family"], rule_id)


# ---------------------------------------------------------------- C and R

def checklist_row(results, cl_id):
    return next(r for r in results if r["rules"] == [cl_id])


def test_checklist_bms_not_included_flags():
    pump = item("I7", "pump", "P", bms_included=v(False))
    assert checklist_row(c.c_checklist(pkg([pump], []), ctx()), "CL-08")["result"] == "flag"


def panel_result(application, **values):
    pump = item("P", "pump", "P", application=v(application), controller_included=v(None), **values)
    panel_rules = [r for r in c.load("consultant_rules.csv") if r["rule_id"] in ("CR-01", "CR-02", "CR-03")]
    context = c.context("RO", date(2026, 3, 16), date(2026, 4, 6), consultant=panel_rules)
    return c.p_consultant_rules(pkg([pump], []), context)


def test_control_panel_is_a_consultant_rule_by_pump_application():
    # Luca: a preference, not a requirement (12 Nov 2026); his rule of 28 Oct is now CR-01 to CR-03.
    assert [(r["result"], r["rules"]) for r in panel_result("stormwater")] == [("flag", ["CR-01"])]
    assert panel_result("circulation")[0]["result"] == "flag"
    assert panel_result("booster")[0]["result"] == "info"
    assert panel_result("drainage", float_switch=v(None))[0]["result"] == "flag"
    assert panel_result("drainage", float_switch=v(True))[0]["result"] == "pass"
    assert panel_result("dhw_circulation") == []   # no consultant rule for it


def rule(kind, field="", value="", effect="B", operator="", unit="", family="all", application="", active="yes"):
    return {"rule_id": "CR-T", "family": family, "application": application, "kind": kind, "field": field,
            "operator": operator, "value": value, "unit": unit, "effect": effect, "text": "t", "source": "",
            "added_on": "", "active": active}


def consultant(rules, items, docs=()):
    context = c.context("RO", date(2026, 3, 16), date(2026, 4, 6), consultant=rules)
    return c.p_consultant_rules(pkg(items, list(docs)), context)


def test_consultant_brand_rule_and_its_effect():
    pump = item("B1", "pump", "CME", brand="Wilo")
    pump["brand"] = "Wilo"
    assert only(consultant([rule("brand", value="Grundfos", effect="C")], [pump]))["blocking"] is True
    assert only(consultant([rule("brand", value="Grundfos;Wilo")], [pump]))["result"] == "pass"
    assert consultant([rule("brand", value="Grundfos", active="no")], [pump]) == []
    assert consultant([rule("brand", value="Grundfos", family="ahu")], [pump]) == []


def test_consultant_value_document_and_reminder_rules():
    pump = item("B2", "pump", "CME", max_pressure=v(10, "bar"), motor_efficiency_class=v("IE3"))
    assert only(consultant([rule("value", "max_pressure", "16", operator=">=", unit="bar")], [pump]))["result"] == "flag"
    assert only(consultant([rule("value", "max_pressure", "10", operator=">=", unit="bar")], [pump]))["result"] == "pass"
    assert only(consultant([rule("value", "max_pressure", "10", operator=">=", unit="MPa")], [pump]))["result"] == "unclear"
    assert only(consultant([rule("value", "motor_efficiency_class", "ie3", operator="=")], [pump]))["result"] == "pass"
    warranty = doc("w.pdf", "warranty", ["CME"])
    assert only(consultant([rule("document", "warranty")], [pump], [warranty]))["result"] == "pass"
    assert only(consultant([rule("document", "warranty")], [pump]))["result"] == "flag"
    assert only(consultant([rule("reminder")], [pump]))["result"] == "info"


def test_no_tolerance_on_the_duty_point():
    rules, _, _ = tables()
    assert c.tolerance({"rules": rules}) == 0.0
    pump = item("I11", "pump", "P", duty_flow=v(15, "m3/h"), flow=v(14.99, "m3/h"))
    assert only(c.v1_duty_point(pkg([pump], []), ctx()))["result"] == "flag"


def test_checklist_value_not_found_stays_unclear_until_verified_as_absent():
    r = checklist_row(c.c_checklist(pkg([item("I10", "pump", "P")], []), ctx()), "CL-03")
    assert (r["result"], r["would_be"]) == ("unclear", "flag")


def test_checklist_electrical_data_names_what_is_missing():
    # starting_method verified as absent (Luca confirmed the sheet does not give it)
    pump = item("I8", "pump", "P", voltage=v("3 x 400 V"), power=v(1.2, "kW"), starting_method=v(None))
    r = checklist_row(c.c_checklist(pkg([pump], []), ctx()), "CL-12")
    assert r["result"] == "flag" and r["params"]["missing"] == "starting_method"


def test_checklist_blocking_rows_are_marked_blocking():
    rules, family_docs, checklist = tables()
    checklist = [{**row, "blocking": "yes"} if row["id"] == "CL-03" else row for row in checklist]
    context = c.context("RO", date(2026, 3, 16), date(2026, 4, 6), data=(rules, family_docs, checklist))
    r = checklist_row(c.c_checklist(pkg([item("I9", "pump", "P", used_for=v(None))], []), context), "CL-03")
    assert (r["result"], r["blocking"]) == ("flag", True)


def test_reminders_change_with_the_location():
    items = [PUMP, ahu()]
    ro = c.r_reminders(pkg(items, []), ctx("RO"))
    es = c.r_reminders(pkg(items, []), ctx("ES"))
    assert [r["rules"] for r in ro] == [["RO-L10-11-3", "RO-PRACTICE-DELIVERY"]]
    later = c.r_reminders(pkg(items, []), c.context("RO", date(2026, 12, 17), date(2027, 1, 7)))
    assert [r["rules"] for r in later] == [["RO-L169-378-3", "RO-PRACTICE-DELIVERY"]]  # the Code replaced Law 10/1995
    assert [r["rules"] for r in es] == [["ES-CTE-7-2"], ["ES-RITE-20"]]
    assert "Unilift" not in es[1]["reason"]  # RITE is for thermal installations only


def test_run_all_attaches_the_rule_status():
    results = c.run_all(pkg([PUMP], [SHEET, DECL]), ctx())
    d1 = next(r for r in results if r["check"] == "D1" and "EU-LVD-DOC" in r["rules"])
    assert d1["rule_status"]["EU-LVD-DOC"] == "to_confirm"


# ---------------------------------------------------------------- MAF-11: manufacturer documents library

LIB = {"documents": [{"brand": "Grundfos", "doc_type": "eu_declaration_of_conformity", "title": "DPK safety instructions",
                      "covers": ["DPK"], "url": "https://example.org/dpk.pdf", "page": 11, "status": "extracted",
                      "notes": None}],
       "not_found": [{"brand": "FläktGroup", "doc_type": "eu_declaration_of_conformity", "covers": ["CAIRplus"],
                      "searched_on": "2026-10-29"}]}


def d1_declaration(item_):
    context = c.context("RO", date(2026, 3, 16), date(2026, 4, 6), lib=LIB)
    return next(r for r in c.d1_required_documents(pkg([item_], []), context)
                if r["params"].get("doc_type") == "eu_declaration_of_conformity")


def test_d1_says_when_the_manufacturer_publishes_the_missing_document():
    dpk = item("I12", "pump", "DPK15803050D", "DPK")
    dpk["brand"] = "Grundfos"
    r = d1_declaration(dpk)
    assert (r["would_be"], r["code"]) == ("flag", "D1.published")  # still a problem until it is attached
    assert "https://example.org/dpk.pdf" in r["reason"]


def test_d1_library_needs_the_same_brand():
    other = item("I13", "pump", "DPK-1000", "DPK")
    other["brand"] = "Wilo"
    assert d1_declaration(other)["code"] == "D1.missing"


def test_d1_says_when_the_manufacturer_site_was_searched_without_result():
    ahu = item("I14", "ahu", "Z096096GBVA", "CAIRplus")
    ahu["brand"] = "FläktGroup"
    r = d1_declaration(ahu)
    assert r["code"] == "D1.missing" and "searched 2026-10-29" in r["reason"]


# ---------------------------------------------------------------- AI matching of documents to products

def matched(doc_, item_id, kind, status="verified"):
    return {**doc_, "matches": [{"item": item_id, "kind": kind, "page": 1, "quote": "", "status": status}]}


def test_ai_matches_replace_text_matching():
    # The text would match ("Unilift AP" is the range), but the AI says it is only related.
    assert not c.covers(matched(DECL, "I1", "related"), PUMP)
    assert c.covers(matched(doc("x.pdf", "eu_declaration_of_conformity", []), "I1", "range"), PUMP)
    assert c.covers(SHEET, PUMP)  # no AI matches yet: falls back to the text


def test_a_data_sheet_for_the_range_only_is_flagged_by_the_checklist():
    range_sheet = matched(SHEET, "I1", "range")
    r = checklist_row(c.c_checklist(pkg([PUMP], [range_sheet]), ctx()), "CL-01")
    assert r["result"] == "flag" and "covers only the range" in r["reason"]
    table_sheet = matched(SHEET, "I1", "range table row")
    assert checklist_row(c.c_checklist(pkg([PUMP], [table_sheet]), ctx()), "CL-01")["result"] == "pass"


def test_a_match_waits_for_the_reviewer_like_any_value():
    unconfirmed = matched(SHEET, "I1", "exact model", status="extracted")
    d1 = c.d1_required_documents(pkg([PUMP], [unconfirmed, DECL]), ctx())
    sheet = next(r for r in d1 if "data sheet" in r["reason"])
    assert (sheet["result"], sheet["would_be"]) == ("unclear", "pass")


def test_q_checks_what_the_boq_line_asks_and_stays_silent_without_a_boq():
    pump = item("Q1", "pump", "CME", controller_included=v(True), bms_included=v(None))
    asks = [{"text": "a control panel is included", "kind": "included", "field": "controller_included", "operator": "",
             "value": "", "unit": "", "quote": "tablou electric"},
            {"text": "BMS interface", "kind": "included", "field": "bms_included", "operator": "", "value": "", "unit": "",
             "quote": "interfata BMS"},
            {"text": "reference model Grundfos", "kind": "reminder", "field": "", "operator": "", "value": "", "unit": "",
             "quote": "model de referinta: Grundfos"}]
    link = {"file": "b.xlsx", "sheet": "IS06", "row": 22, "requirements": asks, "status": "verified"}
    results = c.q_boq_lines({**pkg([pump], []), "boq": {"Q1": link}}, ctx())
    assert [r["would_be"] for r in results] == ["pass", "flag", "info"]
    assert c.q_boq_lines(pkg([pump], []), ctx()) == []
    assert only(c.q_boq_lines({**pkg([pump], []), "boq": {}}, ctx()))["code"] == "Q.none"
    unread = only(c.q_boq_lines({**pkg([pump], []), "boq": {"Q1": {**link, "requirements": None}}}, ctx()))
    assert unread["code"] == "Q.unread"
    # what the AI read in the line is unconfirmed by default, so a pass waits for the reviewer
    assert c.q_boq_lines({**pkg([pump], []), "boq": {"Q1": {**link, "status": "extracted"}}}, ctx())[0]["result"] == "unclear"


def test_q_shows_the_boq_motor_power_as_an_estimate():
    pump = item("Q2", "pump", "AP12", power=v(1.2, "kW"))
    ask = {"text": "power is 1.5 kW", "kind": "value", "field": "power", "operator": "=", "value": "1.5", "unit": "kW",
           "quote": "P=1.5 kW"}
    link = {"file": "b.xlsx", "sheet": "IS06", "row": 31, "requirements": [ask], "status": "verified"}
    r = only(c.q_boq_lines({**pkg([pump], []), "boq": {"Q2": link}}, ctx()))
    assert r["result"] == "info" and "estimate" in r["reason"]
