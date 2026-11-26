"""The rules that read a product line out of a form row, a register row or a BOQ line (ingest/products.py). The texts
are made up in the way the real forms and BOQs are written; no real company or project name."""
from ingest.products import covers, describe, kind_of, producer_of, same_line


def test_the_kind_comes_first_and_a_conduit_or_insulation_is_not_a_pipe():
    assert kind_of("Izolatie elastomerica la teava de alimentare cu apa") == "insulation"
    assert kind_of("Tub de protectie halogen free Ф20mm, inclusiv sarma de tragere") == "conduit"
    assert kind_of("Tuburi PVC-KG Ø110mm, inclusiv sarma de tragere") == "conduit"   # a pipe used to pull cables
    assert kind_of("Vana de sectionare Dn 25") == "valve"
    assert kind_of("Cazan mural în condensare pentru încălzire") == "boiler"
    assert kind_of("Cablu alimentare din cupru tip N2XH 3x1.5 mmp") == "cable"
    assert kind_of("Țeavă PP-R PN20 pentru apă rece") == "pipe"
    assert kind_of("Pompa de drenaj") is None


def test_a_cable_gives_its_type_fire_behaviour_cpr_class_and_sections():
    c = describe("Cablu NHXH FE180 E90 PH120 B2ca s1a d1 a1, 3x1,5 mmp si 5x2,5 mmp", "Kabelwerk Nord SRL")
    assert (c["kind"], c["designation"], c["fire"], c["cpr"]) == ("cable", "NHXH", "E90 PH120 FE180", "B2ca-s1a,d1,a1")
    assert c["sizes"] == ["3x1.5", "5x2.5"] and c["producer"] == "kabelwerk nord"
    assert describe("Cablu JEH(ST) 1X2X1,5mmp")["designation"] == "JE-H(St)H"
    assert describe("Cablu JEH(ST) 1X2X1,5mmp")["sizes"] == ["1x2x1.5"]
    data = describe("Cablu F/FTP cat 6a 23 AWG LSZH")
    assert (data["designation"], data["sizes"]) == ("F/FTP cat 6a", ["23 AWG"])


def test_a_pipe_gives_its_material_pressure_class_standard_use_and_diameters():
    p = describe("Teava PP-R PN20 SR EN ISO 15874-2 pentru apa rece si calda menajera, diametrul 20, 25, 32", "Tubex")
    assert (p["material"], p["pressure"], p["standard"], p["use"]) == ("PP-R", "PN20", "SR EN ISO 15874-2", "drinking water")
    assert p["sizes"] == ["20", "25", "32"]
    sewer = describe("Teava PVC pentru canalizare Ø110")
    assert (sewer["material"], sewer["use"], sewer["sizes"]) == ("PVC", "not drinking water", ["110"])


def test_a_valve_gives_its_type_connection_pressure_class_and_diameters():
    v = describe("Robinet sfera cu olandez PN25, diametrul 15,20, 25, 32, 40", "Valvia")
    assert (v["type"], v["connection"], v["pressure"], v["sizes"]) == ("ball", "union", "PN25", ["15", "20", "25", "32", "40"])


def test_a_boiler_gives_its_series_fuel_and_powers():
    b = describe("Cazan mural in condensare pe gaz, Calorix 200-W, 26 kW", "Calorix")
    assert (b["series"], b["fuel"], b["sizes"]) == ("calorix 200-w", "gas", ["26 kW"])


def test_a_producer_loses_or_similar_and_its_company_form():
    assert producer_of("Kabelwerk sau similar") == "kabelwerk"
    assert producer_of("Tubex S.R.L.") == "tubex"


def test_the_same_product_line_only_when_every_known_part_agrees():
    a = describe("Teava PP-R PN20 SR EN ISO 15874-2 apa rece, diametrul 20, 25", "Tubex")
    b = describe("Teava PP-R PN20 SR EN ISO 15874-2 apa rece, diametrul 32, 40", "Tubex")
    assert same_line(a, b) == "same"   # other diameters: the same line, a wider range
    assert same_line(a, describe("Teava PP-R PN20 apa rece, diametrul 20", "Tubex")) == "near"   # no standard given
    assert same_line(a, describe("Teava PP-R PN16 SR EN ISO 15874-2 apa rece", "Tubex")) is None
    assert same_line(a, describe("Robinet sfera PN20", "Tubex")) is None


def test_a_product_line_covers_a_boq_line_of_its_kind_type_and_size():
    line = describe("Cablu NHXH E90 PH120, 3x1,5 mmp, 3x2,5 mmp", "Kabelwerk")
    assert covers(line, describe("Cablu NHXH E90 PH120 3x2,5 mmp", "Altkabel sau similar")) == "covers"
    assert covers(line, describe("Cablu NHXH E90 PH120 5x6 mmp")) is None   # a section outside the range
    assert covers(line, describe("Cablu N2XH 3x1,5 mmp")) is None   # another type
    assert covers(line, describe("Cablu NHXH 3x1,5 mmp")) == "near"   # the fire behaviour is not given
    assert covers(describe("Cablu 3x1,5 mmp", "Kabelwerk"), describe("Cablu NHXH 3x1,5 mmp")) is None   # no type: no link


def test_two_lines_of_unknown_type_are_never_linked():
    assert same_line(describe("Teava", "Tubex"), describe("Teava PP-R PN20", "Tubex")) is None


def test_an_air_damper_is_not_a_valve_but_a_check_valve_for_water_is():
    assert kind_of("Clapete anti-foc circulare si rectangulare") == "damper"
    assert kind_of("Servomotor clapeta motorizata") == "damper"
    assert kind_of("Clapeta de retinere cu arc, filet, DN 25") == "valve"
    assert describe("Clapeta de retinere cu arc, filet, DN 25")["type"] == "check"


def test_black_and_zn_pipes_are_steel_and_pe_counts_only_in_capitals():
    assert describe("Teava neagra pentru incalzire")["material"] == "steel"
    assert describe("Teava Zn pentru instalatia de stingere")["material"] == "galvanised steel"
    assert describe("Teava + fitinguri PE gama SDR 11")["material"] == "PE"
    assert describe("Teava montata pe perete")["material"] is None   # "pe" is the Romanian "on"
