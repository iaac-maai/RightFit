"""Read a Romanian material approval form (MAF, old .xls) into a plain dict.

Only roles are kept, never company or person names: the header block
(client, project, designer...) and the supplier rows are never read, and
the signature boxes keep only the role before the colon.
"""
import re
import sys
from datetime import datetime

import xlrd

# Signature box labels on the form, mapped to the role names used in the spec.
ROLES = {
    "SUBCONTRACTOR": "subcontractor",
    "ANTREPENOR GENERAL": "general contractor",
    "PROIECTANT SPECIALITATE": "specialist designer",
    "PROIECTANT GENERAL": "general designer",
    "DIRIGINTE SANTIER": "site supervisor",
    "MANAGER PROIECT": "project manager",
    "CONSULTANT LEED": "LEED consultant",
    "BENEFICIAR": "client",
}


def _text(sheet, r, c):
    value = sheet.cell_value(r, c)
    if isinstance(value, float) and value.is_integer():
        value = int(value)
    return str(value).strip()


def _find(sheet, label, col=None):
    """Row and column of the first cell whose text starts with label."""
    for r in range(sheet.nrows):
        for c in range(sheet.ncols) if col is None else [col]:
            if _text(sheet, r, c).lower().startswith(label.lower()):
                return r, c
    raise ValueError(f"label not found on the form: {label}")


def read_form(path):
    sheet = xlrd.open_workbook(path).sheet_by_index(0)

    def right_of(label):
        r, c = _find(sheet, label, col=11)
        return _text(sheet, r, c + 1)

    form = {
        "form_no": right_of("Formular Nr"),
        "revision": int(right_of("Revizia Nr")),
        "date": datetime.strptime(right_of("Data"), "%d.%m.%Y").date().isoformat(),
        "discipline": right_of("Disciplina"),
        "works_group": right_of("Grupa Lucrari"),
    }

    # Item rows sit between the "Producator / Brand" header and "Pozitie in BOQ".
    header, _ = _find(sheet, "Producator / Brand", col=9)
    boq, _ = _find(sheet, "Pozitie in BOQ", col=1)
    form["items_raw"] = [
        {"name": _text(sheet, r, 4), "brand": _text(sheet, r, 9),
         "model": _text(sheet, r, 11), "origin": _text(sheet, r, 13)}
        for r in range(header + 1, boq) if _text(sheet, r, 11)
    ]
    form["boq_ref"] = _text(sheet, boq, 4).rstrip(" :")

    r, _ = _find(sheet, "Detalii livrare", col=1)
    manufacture = _text(sheet, r + 1, 4)
    form["delivery_raw"] = manufacture
    # The longest lead time in weeks ("3 saptamani", "9 saptamani de la aprobare MAF ...").
    weeks = [int(n) for n in re.findall(r"(\d+)\s*s[aă]pt[aă]m[aâ]ni", manufacture)]
    form["delivery_weeks"] = max(weeks) if weeks else None

    r, _ = _find(sheet, "A se folosi la", col=0)
    end, _ = _find(sheet, "Conditii Depozitare", col=0)
    form["used_for_raw"] = [_text(sheet, i, 1) for i in range(r, end) if _text(sheet, i, 1)]

    r, _ = _find(sheet, "Tip atasament", col=1)
    end, _ = _find(sheet, "Mostra transmisa", col=1)
    form["attachments_listed"] = [
        {"label": _text(sheet, i, 1), "pages": int(_text(sheet, i, 7) or 0) or None}
        for i in range(r + 1, end) if _text(sheet, i, 1)
    ]
    # The X sits under "No" (column 5) or "Yes" (column 7) on the row below.
    form["sample_sent"] = "No" if _text(sheet, end + 1, 5) else "Yes" if _text(sheet, end + 1, 7) else None

    r, c = _find(sheet, "STATUS", col=11)
    form["status_scale"] = [_text(sheet, i, c + 1) for i in range(r + 1, r + 6)]

    form["signers"] = []
    for i in range(r, sheet.nrows):
        for j in range(sheet.ncols):
            role = ROLES.get(_text(sheet, i, j).split(":")[0].strip())
            if role:
                form["signers"].append(role)
    return form


if __name__ == "__main__":
    import json
    print(json.dumps(read_form(sys.argv[1]), ensure_ascii=False, indent=2))
