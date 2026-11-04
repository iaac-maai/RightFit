"""The pump demo reproduces the midterm deck: booster sizing on the Lowara catalogue, and, on the laptop that
holds the package's own readings (checks/pumps/data/raw, git-ignored), the declaration check and the standby test."""
import json
from pathlib import Path

import pytest

from app import pump_demo

ROOT = Path(__file__).resolve().parents[1]
P01 = json.loads((ROOT / "data/maf/extracted/P01.json").read_text())
HAS_RAW = (pump_demo.RAW / "curves_package_IS15.csv").exists()


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


def test_renamed_files_still_identify_the_package():
    packages = {"P01": P01}
    assert pump_demo.identify(["Q=1ls@H=10mCA_96001652_UNILIFT_AP12400.pdf"], packages) == "P01"
    assert pump_demo.identify(["holiday.pdf"], packages) is None


@pytest.mark.skipif(not HAS_RAW, reason="the package's own readings are only on Luca's laptop")
def test_two_of_four_pumps_have_no_declaration():
    c = pump_demo.package_check(P01)
    assert c["missing"] == 2 and len(c["pumps"]) == 4 and c["pages"] == 34
    assert [d["names"] for d in c["unused_declarations"]] == [["SL1", "SLV"]]


@pytest.mark.skipif(not HAS_RAW, reason="the package's own readings are only on Luca's laptop")
def test_one_pump_alone_holds_the_duty_with_a_thin_margin():
    s = pump_demo.standby_view(P01)
    assert (s["head_one"], s["margin_m"], s["margin_pct"], s["points"]) == (51.3, 1.3, 2.6, 84)
    assert s["standby"]
