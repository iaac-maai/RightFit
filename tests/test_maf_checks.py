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


# ---------------------------------------------------------------- C and R

def checklist_row(results, cl_id):
    return next(r for r in results if r["rules"] == [cl_id])


def test_checklist_bms_not_included_flags_and_panel_is_left_to_luca():
    pump = item("I7", "pump", "P", bms_included=v(False), controller_included=v(None))
    results = c.c_checklist(pkg([pump], []), ctx())
    assert checklist_row(results, "CL-08")["result"] == "flag"
    assert checklist_row(results, "CL-09")["result"] == "unclear"


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
    assert [r["rules"] for r in es] == [["ES-CTE-7-2"], ["ES-RITE-20"]]
    assert "Unilift" not in es[1]["reason"]  # RITE is for thermal installations only


def test_run_all_attaches_the_rule_status():
    results = c.run_all(pkg([PUMP], [SHEET, DECL]), ctx())
    d1 = next(r for r in results if r["check"] == "D1" and "EU-LVD-DOC" in r["rules"])
    assert d1["rule_status"]["EU-LVD-DOC"] == "to_confirm"
