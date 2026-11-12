"""Read a bill of quantities (BOQ) from Excel and find the line a MAF item answers. No AI here.

A BOQ holds prices, so the files stay in data/raw/boq/ (git-ignored) and prices are never read: only the
description, unit, quantity, producer and standards columns.
"""
import re
from pathlib import Path

HEADS = {"nr": r"^nr\b", "text": r"denumire|descriere|description", "unit": r"^u\.?\s?m\.?|^unit|^um\b",
         "qty": r"cant|qty|quantity", "producer": r"producator|supplier|manufacturer", "standards": r"standard"}
FLOW_TO_M3H = {"mc/h": 1.0, "m3/h": 1.0, "m³/h": 1.0, "l/s": 3.6}
DUTY = re.compile(r"Q\s*=\s*([\d.,]+)\s*(mc/h|m3/h|m³/h|l/s)[^H]{0,40}?H\s*=\s*([\d.,]+)", re.I)


def _rows(path):
    """(sheet name, rows as lists) for every sheet of an .xlsx or .xls file."""
    if Path(path).suffix.lower() == ".xls":
        import xlrd
        book = xlrd.open_workbook(path)
        return [(s.name, [[c.value for c in s.row(r)] for r in range(s.nrows)]) for s in book.sheets()]
    import openpyxl
    book = openpyxl.load_workbook(path, read_only=True, data_only=True)
    return [(ws.title, [list(r) for r in ws.iter_rows(values_only=True)]) for ws in book.worksheets]


def _header(rows):
    """Row number and column of each heading, from the first row in the top 40 that names a description and a unit."""
    for n, row in enumerate(rows[:40]):
        cols = {}
        for i, cell in enumerate(row):
            for key, pattern in HEADS.items():
                if key not in cols and re.search(pattern, " ".join(str(cell or "").split()), re.I):
                    cols[key] = i
                    break
        if "text" in cols and ("unit" in cols or "qty" in cols):
            return n, cols
    return None, {}


def read_boq(path):
    """Every line with a description: file, sheet, row (as in Excel), text, unit, quantity, producer, standards."""
    out = []
    for sheet, rows in _rows(path):
        start, cols = _header(rows)
        if start is None:
            continue
        get = lambda row, key: row[cols[key]] if key in cols and cols[key] < len(row) else None  # noqa: E731
        for n, row in enumerate(rows[start + 1:], start + 2):
            text = " / ".join(" ".join(part.split()) for part in str(get(row, "text") or "").splitlines() if part.strip())
            # Sub-headings such as "material", column numbers and totals are not lines.
            if len(text) < 6 or re.fullmatch(r"(?i)material|manopera|total.*", text):
                continue
            out.append({"file": Path(path).name, "sheet": sheet, "row": n, "nr": get(row, "nr"), "text": text,
                        "unit": get(row, "unit"),
                        "qty": get(row, "qty"), "producer": get(row, "producer"), "standards": get(row, "standards")})
    return out


def duties(text):
    """The (flow in m3/h, head in m) pairs a line names, like 'Q=15 mc/h; H=50 mCA'."""
    num = lambda s: float(s.replace(",", "."))  # noqa: E731
    return [(num(q) * FLOW_TO_M3H[u.lower()], num(h)) for q, u, h in DUTY.findall(text)]


def sheets_for(lines, boq_ref):
    """The lines in the sheets named by the form's BOQ code (P01: IS06); none when the BOQ has no such sheet."""
    code = re.match(r"[A-Za-z]+\d+", boq_ref or "")
    return [ln for ln in lines if code and ln["sheet"].replace(" ", "").upper().startswith(code.group(0).upper())]


# Words a BOQ line uses for a family, to pick among the positions a form names (P02: "T03 pozitia 2 si 4").
# shortcut: only the families of P01 and P02; add words as new families get BOQ lines.
FAMILY_WORDS = {"pump": r"pomp", "ahu": r"centrala de tratare|air handling",
                "outdoor_unit": r"unitate exterioar|outdoor unit"}


def find_line(lines, boq_ref, item):
    """The BOQ line an item answers, in the sheets named by the form's BOQ code: the line with the item's duty, or,
    when the form names positions, the position whose words fit the item's family."""
    positions = {p for p in re.findall(r"\d+", re.sub(r"^\s*[A-Za-z]+\d+", "", boq_ref or ""))}
    if positions and item["family"] in FAMILY_WORDS:
        named = [ln for ln in sheets_for(lines, boq_ref) if str(ln["nr"]).split(".")[0] in positions
                 and re.search(FAMILY_WORDS[item["family"]], ln["text"], re.I)]
        if len(named) == 1:
            return named[0]
    flow, head = (item["values"].get(k) or {} for k in ("duty_flow", "duty_head"))
    if flow.get("value") is None or head.get("value") is None or flow.get("unit") not in ("m3/h", "l/s"):
        return None
    want = (flow["value"] * (3.6 if flow["unit"] == "l/s" else 1.0), head["value"])
    pool = sheets_for(lines, boq_ref) or lines
    close = lambda a, b: abs(a - b) <= 0.01 * max(abs(b), 1e-9)  # noqa: E731
    return next((ln for ln in pool if any(close(q, want[0]) and close(h, want[1]) for q, h in duties(ln["text"]))), None)
