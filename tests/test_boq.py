"""The BOQ reader on a small hand-made workbook (real BOQs hold prices and stay out of Git)."""
import openpyxl

from ingest.boq import duties, find_line, read_boq


def make(path):
    book = openpyxl.Workbook()
    ws = book.active
    ws.title = "IS06 Echipamente"
    ws.append(["Project title"])
    ws.append([])
    ws.append(["Nr. crt.", "DESCRIERE", "UM", "CANTITATE", "Pret unitar", "Total (EUR)"])
    ws.append([None, "material", None, None, "material", "manopera"])
    ws.append([1, "Grup de pompare apa potabila\nQ=15 mc/h; H=50 mCA; 3~400 V\n*tablou electric", "buc.", 1, 9999, 9999])
    ws.append([2, "Electropompa submersibila\n- Q=3 l/s; H=10 mCA", "buc.", 1, 500, 500])
    other = book.create_sheet("T01")
    other.append(["Nr.", "DENUMIRE MATERIAL", "U.M.", "Cant."])
    other.append([1, "Electropompa circulatie Q = 10,8 mc/h; H = 3 mCA", "buc.", 2])
    other.append([2, "02.CTA-Centrala de tratare aer 100% aer proaspat", "buc.", 1])
    other.append([4, "Unitate exterioara pentru baterie in detenta directa CTA", "buc.", 3])
    book.save(path)


def test_reads_lines_without_prices_and_finds_the_line_by_duty(tmp_path):
    make(tmp_path / "boq.xlsx")
    lines = read_boq(tmp_path / "boq.xlsx")
    assert [(ln["sheet"], ln["row"]) for ln in lines][:3] == [("IS06 Echipamente", 5), ("IS06 Echipamente", 6), ("T01", 2)]
    assert lines[0]["text"].startswith("Grup de pompare apa potabila / Q=15") and lines[0]["qty"] == 1
    assert "9999" not in str(lines)   # prices are never read
    assert duties(lines[2]["text"]) == [(10.8, 3.0)]
    drainage = {"family": "pump", "values": {"duty_flow": {"value": 3, "unit": "l/s"}, "duty_head": {"value": 10, "unit": "m"}}}
    assert find_line(lines, "IS06-Echipamente", drainage)["row"] == 6
    assert find_line(lines, "T01", drainage) is None   # its sheet has no such line
    assert find_line(lines, "IS06", {"family": "ahu", "values": {}}) is None
    # a form that names positions: the position whose words fit the family
    assert find_line(lines, "T01 pozitia 2 si 4", {"family": "ahu", "values": {}})["nr"] == 2
    assert find_line(lines, "T01 pozitia 2 si 4", {"family": "outdoor_unit", "values": {}})["nr"] == 4
