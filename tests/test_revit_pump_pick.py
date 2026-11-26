"""Check Pump lets the architect click only a pump set (rf_project.is_pump in the Revit add-in).
The element names are made up; each list is what rf_model.names_of reads from an element:
its name, type, family, Model and Manufacturer, mark and comments."""
import os
import sys

LIB = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "revit", "RightFit.extension", "lib")
if LIB not in sys.path:
    sys.path.insert(0, LIB)

import rf_project  # noqa: E402  (plain Python, no Revit inside)

SETS = [{"id": "set-a", "maker": "Maker", "model": "Booster XB 15-2"},
        {"id": "set-b", "maker": "Other", "model": "2 NX 20/4"}]


def test_test_room_pump_can_be_picked():
    assert rf_project.is_pump([u"RFT pump - Maker Booster XB 15-2", u"RFT pump front:+Y"], SETS)
    assert rf_project.is_pump([u"Type 1", u"Family 1", u"P-01", u"RFT pump"], SETS)  # a family instance


def test_test_room_tank_pit_and_vessel_cannot_be_picked():
    assert not rf_project.is_pump([u"RFT Drinking-water tank 10 m3"], SETS)
    assert not rf_project.is_pump([u"RFT Drainage pit 1x1x1 m"], SETS)
    assert not rf_project.is_pump([u"RFT Pressure vessel 500 L"], SETS)


def test_rightfit_drawings_cannot_be_picked():
    assert not rf_project.is_pump([u"RF preview - Maker Booster XB 15-2"], SETS)
    assert not rf_project.is_pump([u"RF verdict pad"], SETS)


def test_a_known_set_can_be_picked_by_its_model_code():
    assert rf_project.is_pump([u"Standard", u"Equipment", u"booster xb 15 2"], SETS)
    assert rf_project.is_pump([u"Unit", u"Skid", u"2NX20/4"], SETS)


def test_a_pump_word_is_enough():
    assert rf_project.is_pump([u"Type A", u"M_Pump - Centrifugal"], SETS)
    assert rf_project.is_pump([u"Grupo", u"Bomba de presion"], [])
    assert rf_project.is_pump([u"Hydro Multi-E 3", u"Booster set"], [])


def test_other_equipment_cannot_be_picked():
    assert not rf_project.is_pump([u"Water heater 300 L", u"Storage tank"], SETS)
    assert not rf_project.is_pump([u"Expansion vessel 50 L"], SETS)
    assert not rf_project.is_pump([], SETS)
