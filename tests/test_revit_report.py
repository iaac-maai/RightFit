"""The room and pump set tables at the top of the Check Pump report (rf_report in the Revit add-in).
The room and the set are made up."""
import os
import sys

LIB = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "revit", "RightFit.extension", "lib")
if LIB not in sys.path:
    sys.path.insert(0, LIB)

import rf_report  # noqa: E402  (plain Python, no Revit inside)

ROOM = {"name": "B-01", "kind": "room", "height": 3000,
        "outline": [[-1000, -2000], [3000, -2000], [3000, 1000], [-1000, 1000]],
        "doors": [{"name": "door B1", "width": 900, "height": 2100}],
        "obstacles": [{"name": "tank (Plumbing Fixtures)", "box": [0, 0, 1000, 500, 0, 1500]}],
        "pipes": []}
SET = {"id": "a", "maker": "Maker", "model": "Booster XB", "submitted": True, "L": 1000.4, "W": 600, "H": 800,
       "kg": 120, "pumps": 2, "p2_each": None, "standby": "fail", "source": "sheet.pdf p.2", "status": "extracted"}


def text(rows):
    return " | ".join("{}: {}".format(a, b) for a, b in rows)


def test_floor_size_of_a_rectangle_whichever_way_it_is_turned():
    assert rf_report.floor_size(ROOM["outline"]) == (4000, 3000, 12)
    turned = [[0, 0], [2121.32, 2121.32], [0, 4242.64], [-2121.32, 2121.32]]  # a 3000 x 3000 square at 45°
    length, width, area = rf_report.floor_size(turned)
    assert round(length) == 3000 and round(width) == 3000 and round(area) == 9


def test_room_table_gives_every_dimension_and_what_is_in_it():
    t = text(rf_report.room_rows(ROOM, "standard", {"front": 800, "sides": 600, "back": 0, "top": 500},
                                 {"name": "C1", "rating_a": 25, "status": "verified"}))
    for part in ["Length: 4 000 mm", "Width: 3 000 mm", "Height: 3 000 mm", "Floor area: 12.00 m²", "Volume: 36.0 m³",
                 "door B1: 900 mm wide x 2100 mm high", "tank (Plumbing Fixtures): 1000 x 500 x 1500 mm",
                 "none drawn in the model", "front 800 mm", "C1", "25.0 A"]:
        assert part in t


def test_pump_table_gives_every_value_and_never_fills_a_missing_one():
    t = text(rf_report.pump_rows(SET, dict(SET, L=1210)))
    for part in ["Booster XB", "the submitted set", "1 000 x 600 x 800 mm", "Size on the data sheet: 1 210",
                 "120.0 kg", "Number of pumps: 2", "no (fail)", "sheet.pdf p.2", "extracted"]:
        assert part in t
    assert "Motor power, each pump: <span style='color:#888'>not given" in t


def test_summary_box_names_room_and_set_with_their_sizes():
    html = rf_report.summary_html(ROOM, SET)
    assert "B-01" in html and "4.00 x 3.00 m floor, 3.00 m high" in html
    assert "Maker Booster XB" in html and "1000 x 600 x 800 mm, 120 kg, 2 pumps" in html


def test_missing_room_outline_gives_not_given():
    t = text(rf_report.room_rows({"name": "X", "height": None, "outline": []}))
    assert "Length: <span" in t and "none found" in t
