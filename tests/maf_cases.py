"""Small hand-written packages for the MAF tests. Every value is verified unless a test says otherwise."""
from datetime import date

from checks.maf.checks import context


def v(value, unit=None, status="verified"):
    return {"value": value, "unit": unit, "source": "sheet.pdf", "page": 1, "quote": "", "status": status,
            "checked_by": "Luca" if status == "verified" else None, "note": None}


def doc(file, doc_type, covers, listed_as=None, valid_until=None, status="verified"):
    return {"file": file, "doc_type": doc_type, "covers": covers, "listed_as": listed_as,
            "valid_until": valid_until, "status": status}


def item(id, family, model, range=None, **values):
    return {"id": id, "name": id, "family": family, "brand": "x", "model": model, "range": range,
            "values": values}


def pkg(items, documents, attachments=()):
    return {"package": "T", "form": {"attachments_listed": [{"label": a, "pages": 1} for a in attachments]},
            "items": items, "documents": documents}


def ctx(location="RO", review=date(2026, 3, 16), delivery=date(2026, 4, 6), **requirements):
    return context(location, review, delivery, requirements)


PUMP = item("I1", "pump", "UNILIFT_AP1250113", "Unilift AP", duty_flow=v(3, "l/s"), duty_head=v(10, "m"),
            flow=v(3.39, "l/s"), head=v(12.8, "m"))
SHEET = doc("ft.pdf", "data_sheet", ["UNILIFT AP12.50.11.3"], listed_as="FT UNILIFT_AP1250113")
DECL = doc("doc.pdf", "eu_declaration_of_conformity", ["Unilift AP", "Unilift APB", "Unilift KP"],
           listed_as="Declaratie de conformitate Unilift AP")
