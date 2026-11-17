"""The rows for the family classifier: the families are check D1's, and the split never lets a chatbot test package, or a
row repeated from the locked side, reach training."""
from model.family_rows import assign, families


def row(package, code, name, model=""):
    return {"package": package, "code": code, "name": name, "model": model, "discipline": "low current"}


def test_the_families_are_check_d1s_then_other():
    found = families()
    assert len(found) == 14 and list(found)[-1] == "other"
    assert found["fire_detection_panel"] == "EN 54-2" and found["cable"] == "EN 50575" and found["pump"] == ""


def test_a_held_package_and_every_maf_that_repeats_its_row_stay_out_of_training():
    rows = [row(f"P{n}", f"ICS {n}", f"product {n}") for n in range(10, 30)] + [row("P40", "ICS 40", " Product  12")]
    sides = assign(rows, {}, held={"P12"})
    assert sides["ICS 12"][0] == "test"
    assert sides["ICS 40"] == sides["ICS 12"]   # the same name, once case and spaces are set aside


def test_revisions_shared_files_and_shared_models_stay_on_one_side():
    rows = [row("P14", "IE 33", "a"), row("P15", "IE 33", "b"), row("P20", "ICS 20", "c"), row("P21", "ICS 21", "d"),
            row("P31", "ICS 32", "e", "LM32-F200"), row("P42", "ICS 43", "f", "lm32-f200")]
    sides = assign(rows, {"P20": ["size:1"], "P21": ["size:1"]}, held=set())
    assert sides["ICS 20"][1] == sides["ICS 21"][1] and sides["ICS 32"][1] == sides["ICS 43"][1]
    assert sides["ICS 20"][1] != sides["ICS 32"][1]
    assert {side for side, _ in sides.values()} == {"train"}   # no random share: only the held packages are locked
