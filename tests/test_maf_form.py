"""The form reader on the real P01 form. The originals are local only, so this test skips without them."""
from pathlib import Path

import pytest

from ingest.maf_form import read_form

ROOT = Path(__file__).resolve().parents[1]
FORM = ROOT / "data/raw/P01/MAF_IS_015_Pompe si grup pompare sanitare.xls"

pytestmark = pytest.mark.skipif(not FORM.exists(), reason="data/raw/ is local only")


def test_reads_the_p01_form_fields():
    form = read_form(FORM)
    assert (form["form_no"], form["revision"], form["date"]) == ("IS 015", 0, "2026-03-16")
    assert form["delivery_weeks"] == 3 and form["sample_sent"] == "No"
    assert len(form["attachments_listed"]) == 6 and len(form["used_for_raw"]) == 4
    assert form["signers"][:2] == ["subcontractor", "general contractor"]


def test_keeps_roles_only():
    text = str(read_form(FORM)).lower()
    names = [n.strip().lower() for n in (ROOT / "data/raw/NAMES.txt").read_text().splitlines()
             if n.strip() and not n.startswith("#")]
    assert not [n for n in names if n in text]



def test_keeps_a_product_row_with_no_model():
    # P23, not P51: P51 is in the locked chatbot test set
    form_file = next((ROOT / "data/raw/P23").glob("*.xls"), None)
    if form_file is None:
        pytest.skip("the P23 form is local only")
    rows = read_form(form_file)["items_raw"]
    assert len(rows) == 1 and rows[0]["model"] == "" and rows[0]["name"] == "Cablu FTP CAT 6A"
