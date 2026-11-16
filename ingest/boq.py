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


def _num(x):
    try:
        return int(float(str(x).strip()))
    except ValueError:
        return None


def positions(lines, boq_ref):
    """The lines at the positions a form names: `E02.ICS01.01` (sheet, section, number) or `T03 pozitia 2 si 4`,
    `IS01 ... pozitiile 08-11` (sheet code, then numbers or ranges)."""
    ref = boq_ref or ""
    named = [(s, sec, int(n)) for s, sec, n in re.findall(r"\b([A-Z]{1,2}\d{2})\.([A-Z]{2,4}\d{2})\.(\d{1,3})\b", ref)]
    if not named:
        code = re.match(r"\s*([A-Za-z]{1,2}\d{2})", ref)
        if not code:
            return []
        rest = ref[code.end():]
        nums = [n for a, b in re.findall(r"(\d+)\s*-\s*(\d+)", rest) for n in range(int(a), int(b) + 1)]
        nums += [int(n) for n in re.findall(r"\b(\d{1,3})\b", re.sub(r"\d+\s*-\s*\d+", " ", rest))]
        named = [(code.group(1).upper(), None, n) for n in nums]
    out = []
    for sheet, sec, n in named:
        for ln in lines:
            if not ln["sheet"].replace(" ", "").upper().startswith(sheet.upper()):
                continue
            head, _, tail = str(ln["nr"] or "").strip().partition(".")
            if (sec is None and _num(ln["nr"]) == n) or (sec is not None and head == sec and _num(tail) == n):
                out.append(ln)
    return out


_vectors = {}


def most_similar(lines, query, pool):
    """The line of pool whose text is closest to the query (TF-IDF on character n-grams, cosine), with the score.
    eval/boq_matching/results_2026-11-13.md: alone it confuses close products, after the form's positions it is right."""
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
    key = hash(tuple(ln["text"] for ln in lines))
    if key not in _vectors:
        vec = TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5)).fit([ln["text"] for ln in lines])
        _vectors[key] = vec
    vec = _vectors[key]
    scores = cosine_similarity(vec.transform([query]), vec.transform([ln["text"] for ln in pool])).ravel()
    best = int(scores.argmax())
    return pool[best], round(float(scores[best]), 2)


def _code(text):
    return re.sub(r"[^A-Z0-9]", "", str(text).upper())


def form_words(item, form):
    """The form's own words for an item: the row of the form's product list whose model holds the item's model.
    They are in the BOQ's language; the item's name may have been translated when the package was read."""
    rows = (form or {}).get("items_raw") or []
    models = [_code(m) for m in re.split(r"[/;,]", str(item.get("model") or "")) if len(_code(m)) >= 4]
    row = next((r for r in rows if any(m in _code(r.get("model")) for m in models)), None)
    return " ".join(str(row.get(k) or "") for k in ("name", "brand", "model")) if row else None


def find_line(lines, boq_ref, item, form=None):
    """The BOQ line an item answers, and how it was found: the position the form names; several positions, then the
    one whose text is closest to the item; the item's duty in the form's sheet; else the closest text in that sheet.
    Text alone is the weakest way, so its line says so (`how` is "text")."""
    found = positions(lines, boq_ref)
    used_for = item["values"].get("used_for") or {}
    query = form_words(item, form) or " ".join(str(x) for x in (
        item.get("name"), item.get("brand"), item.get("model"), used_for.get("value"), used_for.get("quote")) if x)
    if len(found) == 1:
        return {**found[0], "how": "position"}
    if found and query:
        ln, score = most_similar(lines, query, found)
        return {**ln, "how": "position and text", "score": score}
    pool = sheets_for(lines, boq_ref) or lines
    flow, head = (item["values"].get(k) or {} for k in ("duty_flow", "duty_head"))
    if flow.get("value") is not None and head.get("value") is not None and flow.get("unit") in ("m3/h", "l/s"):
        want = (flow["value"] * (3.6 if flow["unit"] == "l/s" else 1.0), head["value"])
        close = lambda a, b: abs(a - b) <= 0.01 * max(abs(b), 1e-9)  # noqa: E731
        hit = next((ln for ln in pool if any(close(q, want[0]) and close(h, want[1]) for q, h in duties(ln["text"]))), None)
        if hit:
            return {**hit, "how": "duty"}
    if not query:
        return None
    ln, score = most_similar(lines, query, pool)
    return {**ln, "how": "text", "score": score}
