"""The pump demo reads the uploaded files itself. Booster sizing is checked against the midterm deck; on the laptop
that holds the real package (data/raw/P01, git-ignored), so are the declaration check and the standby test."""
from pathlib import Path

import pymupdf
import pytest

from app import pump_demo

P01 = Path(__file__).resolve().parents[1] / "data/raw/P01"


def test_booster_need_judgement_and_suggestions_match_the_deck():
    v = pump_demo.booster_view(40, 10, "GHV20/5SV16")
    assert (v["need"]["peak_flow_m3h"], v["need"]["required_head_m"]) == (7.2, 45.6)
    assert v["submitted"]["verdict"] == "does not fit" and v["submitted"]["issues"][0].startswith("oversized")
    assert [s["model"] for s in v["suggest"]] == ["GHV30/5SV07", "GHV40/10SV04", "GHV20/15SV04"]
    assert v["sets"] == 289 and v["suggest"][0]["head_one_pump_out_m"] == 48.1


def test_booster_refuses_impossible_buildings_and_flags_unknown_sets():
    with pytest.raises(ValueError):
        pump_demo.booster_view(0, 10)
    assert pump_demo.booster_view(40, 10, "NOT-A-SET")["unknown_submitted"]


def test_files_are_sorted_by_their_own_words():
    assert pump_demo.classify("Nr. produs: 96001652\nCant. Descriere\n1 UNILIFT AP12.40.06.1") == "data sheet"
    assert pump_demo.classify("EU declaration of conformity") == "declaration"
    assert pump_demo.classify("Price list") == "other"
    assert pump_demo.classify("  ") == "unreadable"


def test_a_text_file_is_no_pdf_and_a_damaged_pdf_is_still_read():
    assert pump_demo.page_count(b"# notes\nnot a PDF") is None
    doc = pymupdf.open()
    doc.new_page().insert_text((72, 72), "Nr. produs: 96001652, a page long enough to read")
    data = doc.tobytes()[:-60]   # the end of the file is cut off
    assert pump_demo.page_count(data) == 1
    assert "Nr. produs" in pump_demo.read_page(pump_demo.keep("damaged.pdf", data), 1)[0]


def test_a_locked_pdf_is_listed_as_not_read_and_the_rest_is_still_checked():
    locked, sheet = pymupdf.open(), pymupdf.open()
    locked.new_page().insert_text((72, 72), "EU declaration of conformity, a page long enough to read")
    sheet.new_page().insert_text((72, 72), "Nr. produs: 96001652\nCant. Descriere\n1 UNILIFT AP12.40.06.1\nSubmersible drainage pump")
    c = pump_demo.analyse([
        pump_demo.keep("locked.pdf", locked.tobytes(encryption=pymupdf.PDF_ENCRYPT_AES_256, user_pw="open", owner_pw="x")),
        pump_demo.keep("sheet.pdf", sheet.tobytes())])
    assert [p["model"] for p in c["pumps"]] == ["UNILIFT AP12.40.06.1"] and c["pages"] == 1
    assert [(f["name"], f["reason"]) for f in c["unread"]] == [("locked.pdf", "is locked with a password")]


def test_a_declaration_names_its_products_and_carries_the_brand_on():
    pages = [("cover", "text"),
             ("We declare under our sole responsibility that the products Unilift AP, APB, KP, to which this", "ocr")]
    assert pump_demo.declared(pages) == (["Unilift AP", "Unilift APB", "Unilift KP"], 2)
    assert pump_demo.declared([("no such sentence", "text")]) == ([], None)


def test_rules_apply_only_where_their_scope_says():
    families = [("uniliftap", "Unilift AP", "declaration.pdf")]
    r = pump_demo.rules_for(pump_demo.scope({"model": "UNILIFT AP12.40.06.1", "p2_kw": "0.7"},
                                            "Pompă submersibilă pentru drenaj"), families)
    assert (r["CE-01"]["verdict"], r["CE-01"]["label"]) == ("pass", "Unilift AP")
    assert r["PUMP-MEI"]["verdict"] == r["MOTOR-IE"]["verdict"] == "n/a"
    r = pump_demo.rules_for(pump_demo.scope({"model": "Hydro Multi-E 2 CME5-4", "p2_kw": "1.1", "ie_class": "IE5"},
                                            "Grupul de pompare CME"), families)
    assert [r[k]["verdict"] for k in ("CE-01", "PUMP-MEI", "MOTOR-IE")] == ["fail", "n/a", "pass"]
    r = pump_demo.rules_for(pump_demo.scope({"model": "X1"}, "Pump"), families)
    assert r["PUMP-MEI"]["verdict"] == r["MOTOR-IE"]["verdict"] == "?"
    assert "None" not in r["MOTOR-IE"]["detail"]


@pytest.fixture(scope="module")
def p01():
    if not P01.is_dir():
        pytest.skip("the real package is only on Luca's laptop")
    return pump_demo.analyse([pump_demo.keep(f.name, f.read_bytes()) for f in sorted(P01.iterdir())
                              if not f.name.startswith(".")])


def test_two_of_four_pumps_have_no_declaration(p01):
    assert (p01["form"], p01["pages"], len(p01["pumps"]), p01["missing"]) == ("IS 015", 34, 4, 2)
    if pump_demo.OCR:   # the SL1/SLV declaration is a scan
        assert [d["names"] for d in p01["unused"]] == [["SL1", "SLV"]]


def test_one_pump_alone_holds_the_duty_with_a_thin_margin(p01):
    s = p01["standby"]
    assert (s["page"], s["points"], s["head_less"], s["margin_m"], s["margin_pct"]) == (3, 84, 51.3, 1.3, 2.6)
    assert s["standby"]
