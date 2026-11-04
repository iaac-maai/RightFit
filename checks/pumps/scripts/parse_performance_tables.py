"""Parse manufacturer 'hydraulic performance tables' (flow vs head per model) into curve data.

Works on catalogues whose tables have a header row 'm3/h 0 1,4 2,4 ...' and model rows
'MODEL  [N x] kW  [HP] [MEI]  H0 H1 ...' (Lowara/Xylem GHV, e-SV, e-SH, DOMO, DOC ...).
Head values are matched to flow columns by their x position, so blank cells stay blank.
Pages without a table are skipped quickly (PyMuPDF text search first).

    python scripts/parse_performance_tables.py catalogue.pdf --category booster_set \
        --maker Lowara --source-url URL -o data/curves.csv

Long format, one row per model and flow point:
    maker,category,series,model,n_pumps,p2_kw_each,mei,q_m3h,h_m,pumps_running_note,page,source_file,source_url
"""
import argparse, csv, gc, re
from pathlib import Path
import pdfplumber, pymupdf

NUM = re.compile(r"^\d+(?:,\d+)?$")
MODELISH = re.compile(r"^[A-Z]{1,6}\(?M?\)?\d|^\d+SV")
FIELDS = ["maker", "category", "series", "model", "n_pumps", "p2_kw_each", "mei", "q_m3h", "h_m",
          "pumps_running_note", "page", "source_file", "source_url"]


def num(s):
    return float(s.replace(",", "."))


def cx(w):
    return (w["x0"] + w["x1"]) / 2


def cluster_lines(words, tol=3):
    lines = []
    for w in sorted(words, key=lambda w: w["top"]):
        if lines and abs(lines[-1][0] - w["top"]) <= tol:
            lines[-1][1].append(w)
        else:
            lines.append([w["top"], [w]])
    return [sorted(ws, key=lambda w: w["x0"]) for _, ws in lines]


def parse_page(page, pageno):
    page = page.dedupe_chars()
    text = page.extract_text() or ""
    note = re.search(r"refers to performance with (\d+) pumps? running", text)
    running = note.group(1) if note else ""
    out, header, series, kw_x = [], None, "", None
    for ws in cluster_lines(page.extract_words()):
        texts = [w["text"] for w in ws]
        joined = " ".join(texts)
        if re.search(r"ELECTRICAL DATA|DONN[EÉ]ES [EÉ]LECTRIQUES|DATI ELETTRICI", joined, re.I):
            header, kw_x = None, None          # electrical tables are not curves
            continue
        if "kW" in texts and not MODELISH.match(texts[0]):
            kw_x = cx(ws[texts.index("kW")])
        if re.search(r"SERIES", joined, re.I) and "TABLE" not in joined.upper() and len(texts) <= 8:
            series = re.sub(r"(?i)booster", "BOOSTER", joined).replace("SEriES", "SERIES")
        if "m3/h" in texts or "m³/h" in texts:
            i = texts.index("m3/h") if "m3/h" in texts else texts.index("m³/h")
            cols = [(cx(w), num(w["text"])) for w in ws[i + 1:] if NUM.match(w["text"])]
            if len(cols) >= 4:
                header = cols
            continue
        if not header or NUM.match(texts[0]) or not re.search(r"\d", " ".join(texts[:2])):
            continue
        first_col = header[0][0]
        # model name = leading tokens left of the numbers
        k = 0
        if kw_x:   # model name = everything left of the kW column (keeps 'DL(M) 80-DLF(M) 80')
            while k < len(ws) and cx(ws[k]) < kw_x - 20:
                k += 1
        else:
            while k < len(ws) and not NUM.match(ws[k]["text"]) and cx(ws[k]) < first_col - 40:
                k += 1
        model = " ".join(texts[:k]) or texts[0]
        attrs = [w for w in ws[k:] if cx(w) < first_col - 12]
        vals = [w for w in ws[k:] if cx(w) >= first_col - 12 and NUM.match(w["text"])]
        if len(vals) < 3:
            continue
        a = [w["text"] for w in attrs]
        n_pumps, p2, mei = "1", "", ""
        if "x" in a:
            j = a.index("x"); n_pumps = a[j - 1]; p2 = num(a[j + 1]) if j + 1 < len(a) else ""; rest = a[j + 2:]
        else:
            nums = [t for t in a if NUM.match(t)]
            p2 = num(nums[0]) if nums else ""; rest = nums[1:]
        if text.find("MEI") >= 0:
            for t in rest:
                if NUM.match(t) and 0.1 <= num(t) <= 1.0:
                    mei = num(t)
        pts = []
        for w in vals:
            q = min(header, key=lambda c: abs(c[0] - cx(w)))
            if abs(q[0] - cx(w)) <= 14:
                pts.append((q[1], num(w["text"])))
        # a pump curve falls as flow rises: drop rows that are not curves (spec tables, typos)
        falls = sum(1 for (_, h1), (_, h2) in zip(pts, pts[1:]) if h2 <= h1 + 0.3)
        if len(pts) < 3 or falls < 0.85 * (len(pts) - 1):
            continue
        for q, h in pts:
            out.append(dict(series=series, model=model, n_pumps=n_pumps, p2_kw_each=p2, mei=mei,
                            q_m3h=q, h_m=h, pumps_running_note=running, page=pageno))
    return out


def table_pages(path):
    doc = pymupdf.open(path)
    pages = [i for i, p in enumerate(doc) if re.search(r"m3/h|m³/h", p.get_text())
             and re.search(r"TOTAL HEAD|PREVALENZA|HAUTEUR", p.get_text(), re.I)]
    doc.close()
    return pages


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pdf")
    ap.add_argument("--maker", default="")
    ap.add_argument("--category", default="")
    ap.add_argument("--source-url", default="")
    ap.add_argument("-o", "--out", default="data/curves.csv")
    a = ap.parse_args()
    rows = []
    for i in table_pages(a.pdf):
        with pdfplumber.open(a.pdf, pages=[i + 1]) as pdf:
            for r in parse_page(pdf.pages[0], i + 1):
                r.update(maker=a.maker, category=a.category, source_file=Path(a.pdf).name, source_url=a.source_url)
                rows.append(r)
        gc.collect()
    out = Path(a.out); out.parent.mkdir(parents=True, exist_ok=True)
    new = not out.exists()
    with open(out, "a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        if new:
            w.writeheader()
        w.writerows(rows)
    models = {(r["series"], r["model"]) for r in rows}
    print(f"{Path(a.pdf).name}: {len(models)} models, {len(rows)} curve points -> {out}")


if __name__ == "__main__":
    main()
