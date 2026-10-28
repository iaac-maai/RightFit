"""The extracted MAF packages follow the data rule (spec section 4) and keep names out of Git (section 11)."""
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PACKAGES = sorted((ROOT / "data/maf/extracted").glob("*.json"))
FAMILIES = {"pump", "ahu", "outdoor_unit", "dx_kit"}
# Document types listed in the spec, section 4.
DOC_TYPES = {"data_sheet", "eu_declaration_of_conformity", "declaration_of_performance", "product_certificate",
             "other_certificate", "selection_report", "manual", "other"}


def values(pkg):
    return [(item["id"], key, value) for item in pkg["items"] for key, value in item["values"].items()]


@pytest.mark.parametrize("path", PACKAGES, ids=lambda p: p.stem)
def test_every_value_has_a_source_status_and_short_quote(path):
    pkg = json.loads(path.read_text())
    for item_id, key, value in values(pkg):
        where = f"{item_id}.{key}"
        assert value["status"] in ("extracted", "verified", "unclear"), where
        if value["value"] in (None, ""):
            assert value["status"] == "unclear" and value["note"], f"{where}: say where it was looked for"
        else:
            assert value["source"] and value["page"], where
            assert len(value["quote"].split()) <= 15, f"{where}: quote longer than 15 words"
        if value["status"] == "verified":
            assert value["checked_by"], where


@pytest.mark.parametrize("path", PACKAGES, ids=lambda p: p.stem)
def test_documents_and_items_use_known_types(path):
    pkg = json.loads(path.read_text())
    assert {i["family"] for i in pkg["items"]} <= FAMILIES
    assert {d["doc_type"] for d in pkg["documents"]} <= DOC_TYPES


def test_no_name_from_the_local_names_list():
    names_file = ROOT / "data/raw/NAMES.txt"
    if not names_file.exists():
        pytest.skip("data/raw/NAMES.txt is local only")
    names = [n.strip().lower() for n in names_file.read_text().splitlines() if n.strip() and not n.startswith("#")]
    for path in PACKAGES:
        text = path.read_text().lower()
        assert not [n for n in names if n in text], path.name


def test_library_entries_keep_link_page_short_quote_and_status():
    lib = json.loads((ROOT / "data/maf/library.json").read_text())
    for e in lib["documents"]:
        assert e["url"].startswith("https://") and e["page"] and e["found_on"], e["title"]
        assert len(e["quote"].split()) <= 15, e["title"]
        assert e["status"] in ("extracted", "verified") and e["doc_type"] in DOC_TYPES
        assert e["local_file"].startswith("data/raw/"), "copies stay outside Git"


@pytest.mark.parametrize("path", PACKAGES, ids=lambda p: p.stem)
def test_ai_findings_rest_on_cited_pages(path):
    pkg = json.loads(path.read_text())
    findings = pkg.get("ai_findings", [])
    items = {i["id"] for i in pkg["items"]}
    assert len({f["id"] for f in findings}) == len(findings)
    for f in findings:
        assert f["kind"] in ("problem", "question") and f["status"] in ("suggested", "accepted", "rejected")
        assert set(f["items"]) <= items and f["evidence"] and f["suggested_comment"], f["id"]
        for e in f["evidence"]:
            assert e["source"] and e["page"] and len(e["quote"].split()) <= 15, f["id"]
