"""The BOQ reader on a small hand-made workbook (real BOQs hold prices and stay out of Git)."""
import openpyxl

from ingest.boq import duties, find_line, positions, read_boq


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
    fire = book.create_sheet("E02")
    fire.append(["Nr.", "DENUMIRE MATERIAL", "U.M.", "Cant."])
    fire.append(["ICS01", "INSTALATIE DETECTIE INCENDIU", None, None])
    fire.append(["ICS01.01", "Centrala detectie incendiu adresabila cu 2 bucle", "buc.", 1])
    fire.append(["ICS01.02", "Detector optic de fum adresabil, soclu", "buc.", 41])
    book.save(path)


def item(name="", model="", **values):
    return {"name": name, "brand": "", "model": model, "values": values}


def test_reads_lines_without_prices(tmp_path):
    make(tmp_path / "boq.xlsx")
    lines = read_boq(tmp_path / "boq.xlsx")
    assert [(ln["sheet"], ln["row"]) for ln in lines][:3] == [("IS06 Echipamente", 5), ("IS06 Echipamente", 6), ("T01", 2)]
    assert lines[0]["text"].startswith("Grup de pompare apa potabila / Q=15") and lines[0]["qty"] == 1
    assert "9999" not in str(lines)   # prices are never read
    assert duties(lines[2]["text"]) == [(10.8, 3.0)]


def test_finds_the_line_by_position_then_text_then_duty(tmp_path):
    make(tmp_path / "boq.xlsx")
    lines = read_boq(tmp_path / "boq.xlsx")
    # one position named: that line
    hit = find_line(lines, "E02.ICS01.01", item("Centrala de detectie incendiu"))
    assert (hit["nr"], hit["how"]) == ("ICS01.01", "position")
    assert [ln["nr"] for ln in positions(lines, "T01 pozitia 2 si 4")] == [2, 4]
    # two positions named: the closer text chooses
    ahu = find_line(lines, "T01 pozitia 2 si 4", item("Centrala tratare aer", "Z096096GBVA"))
    unit = find_line(lines, "T01 pozitia 2 si 4", item("Unitate exterioara pentru baterie in detenta"))
    assert (ahu["nr"], ahu["how"], unit["nr"]) == (2, "position and text", 4)
    # the form's own words win over a translated name
    form = {"items_raw": [{"name": "Centrala Tratare Aer", "brand": "FLAKT", "model": "Z096096GBVA 9000"}]}
    assert find_line(lines, "T01 pozitia 2 si 4", item("Air handling unit", "Z096096GBVA / A096096GBVA"), form)["nr"] == 2
    # no position: the duty, in the sheet the form names
    drainage = item(duty_flow={"value": 3, "unit": "l/s"}, duty_head={"value": 10, "unit": "m"})
    assert (find_line(lines, "IS06-Echipamente", drainage)["row"], find_line(lines, "IS06", drainage)["how"]) == (6, "duty")
    # nothing else: the closest text, marked as such; with no words at all, no line
    assert find_line(lines, "IS06", item("Grup de pompare apa potabila"))["how"] == "text"
    assert find_line(lines, "IS06", item()) is None
