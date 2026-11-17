"""Tests for ingest/revisions.py: what changed between two revisions of one MAF.

The packages here are small PDFs made by the test, so nothing from the laptop is needed.
"""
import shutil

import pymupdf

from ingest import revisions
from ingest.revisions import compare, previous_revision

PUMP = ("The circulation pump delivers 15 m3/h at 50 m head with a 4 kW motor on 400 V. "
        "Its casing is cast iron, its impeller stainless steel and its seal a mechanical seal. ") * 4
DOC = ("We declare under our sole responsibility that the product named below conforms to the machinery "
       "directive and to the low voltage directive, signed for and on behalf of the manufacturer. ") * 4
CABLE = ("Halogen free cable with copper conductors, insulation of cross linked polyethylene and a sheath "
         "that keeps its function for thirty minutes in a fire, tested to the standard. ") * 4
LIGHT = ("The luminaire gives 4000 lumen at 840 colour, with an emergency module that lasts three hours "
         "and a housing rated IP66 for the sports hall. ") * 4


def pdf(path, pages=(), boxes=()):
    """A PDF with one page per text, or one page of black boxes when there is no text (a stand-in for a scan)."""
    doc = pymupdf.open()
    for text in pages:
        doc.new_page().insert_textbox(pymupdf.Rect(50, 50, 550, 800), text, fontsize=10)
    if boxes:
        page = doc.new_page()
        for box in boxes:
            page.draw_rect(pymupdf.Rect(*box), color=None, fill=(0, 0, 0))
    doc.save(path)
    return path


SCAN = [(60, 60, 540, 140), (60, 200, 300, 420), (330, 200, 540, 420), (60, 480, 540, 760)]


def packages(tmp_path):
    old, new = tmp_path / "P10", tmp_path / "P02"
    old.mkdir()
    new.mkdir()
    pdf(old / "declaration.pdf", [DOC])
    pdf(old / "pump sheet rev1.pdf", [PUMP, PUMP + " Curves on the next pages."])
    pdf(old / "kit.pdf", boxes=SCAN)
    pdf(old / "cable.pdf", [CABLE])
    (old / "MAF form rev03.xls").write_bytes(b"the form")
    shutil.copy(old / "declaration.pdf", new / "declaration renamed.pdf")
    pdf(new / "pump sheet 2026.pdf", [PUMP, PUMP + " Curves for the new duty point."])
    pdf(new / "kit.pdf", boxes=SCAN + [(400, 60, 540, 100)])
    pdf(new / "luminaire.pdf", [LIGHT])
    (new / "MAF form rev04.xls").write_bytes(b"the form, again")
    return old, new


def test_each_attachment_is_unchanged_changed_new_or_removed(tmp_path):
    old, new = packages(tmp_path)
    rows = {r["file"] or r["previous"]: r for r in compare(old, new)}
    assert rows["declaration renamed.pdf"]["status"] == "unchanged" and rows["declaration renamed.pdf"]["renamed"]
    assert rows["declaration renamed.pdf"]["previous"] == "declaration.pdf"
    pump = rows["pump sheet 2026.pdf"]
    assert (pump["status"], pump["previous"], pump["how"]) == ("changed", "pump sheet rev1.pdf", "text")
    assert (pump["same_pages"], pump["pages"]) == (1, 2)          # the first page kept its text, the second did not
    kit = rows["kit.pdf"]
    assert (kit["status"], kit["previous"], kit["how"]) == ("changed", "kit.pdf", "look")
    assert rows["luminaire.pdf"]["status"] == "new" and rows["luminaire.pdf"]["previous"] is None
    assert rows["cable.pdf"]["status"] == "removed" and rows["cable.pdf"]["file"] is None
    assert not any("MAF form" in name for name in rows)            # the form is read, never compared


def test_pairs_are_one_to_one(tmp_path):
    old, new = tmp_path / "old", tmp_path / "new"
    old.mkdir()
    new.mkdir()
    pdf(old / "sheet.pdf", [PUMP])
    pdf(new / "sheet a.pdf", [PUMP + " Variant A."])
    pdf(new / "sheet b.pdf", [PUMP + " Variant B, a little longer than A."])
    rows = compare(old, new)
    assert sorted(r["status"] for r in rows) == ["changed", "new"]


def test_the_previous_revision_is_the_highest_lower_one_of_the_same_form(tmp_path, monkeypatch):
    forms = {"P02": ("IV 004", 4), "P10": ("IV 004", 3), "P11": ("IV 004", 1), "P12": ("IE 022", 3),
             "P13": ("IV 004", 5), "P14": None}
    for name in forms:
        (tmp_path / name).mkdir()
    monkeypatch.setattr(revisions, "form_of", lambda folder: forms[folder.name])
    assert previous_revision(tmp_path / "P02").name == "P10"
    assert previous_revision(tmp_path / "P11") is None              # the first revision has nothing before it
    assert previous_revision(tmp_path / "P14") is None              # a form the reader cannot read
