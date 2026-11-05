"""Extract pump values from Grundfos Product Center data sheets (Romanian or English) into products.csv rows.

Usage:
    python scripts/extract_datasheet.py path/to/folder_or_pdfs ... -o data/products.csv

Every value keeps the file it came from, so each number can be traced to its page.
Other makers (Wilo, Lowara, DAB) use different labels: add them to LABELS below.
Always have a person check the output before using it (column checked_by).
"""
import argparse, csv, re, sys
from pathlib import Path

# label patterns (RO / EN) -> column. First match wins.
LABELS = {
    "flow_m3h":      [r"Debitul curent calculat", r"Actual calculated flow"],
    "max_flow_m3h":  [r"Debit maxim", r"Maximum flow"],
    "head_m":        [r"Înălţimea de pompare rezultată(?: pentru pompă)?", r"Resulting head of the pump"],
    "max_head_m":    [r"Înălţime de pompare max\.?", r"Max\.? head"],
    "p1_kw":         [r"Intrare putere P1", r"Power input - P1"],
    "p2_kw":         [r"Putere nominală - P2", r"Putere \(P2\) pompă principală", r"Rated power - P2"],
    "voltage":       [r"Tensiune nominală", r"Rated voltage"],
    "current_a":     [r"Curent nominal", r"Rated current"],
    "ie_class":      [r"Clasa de eficiență IE", r"IE Efficiency class"],
    "mei":           [r"MEI", r"Minimum efficiency index"],
    "eei":           [r"EEI"],
    "ip":            [r"Grad de protecţie \(IEC 34-5\)", r"Enclosure class \(IEC 34-5\)"],
    "max_liquid_temp_c": [r"Gama temperaturii lichidului", r"Liquid temperature range"],
}
NUM = r"([0-9]+(?:[.,][0-9]+)?)"


def to_m3h(value, unit):
    v = float(value.replace(",", "."))
    return round(v * 3.6, 2) if unit.strip().startswith("l/s") else v


def extract(pdf_path):
    import pdfplumber
    with pdfplumber.open(pdf_path) as pdf:
        text = "\n".join((p.extract_text() or "") for p in pdf.pages)
    return fields(text, Path(pdf_path).name)


def fields(text, name):
    """The values found in the text of one data sheet, whichever library read it."""
    row = {"source_file": name, "maker": "Grundfos" if "Grundfos" in text else ""}
    m = re.search(r"Nr\. Produs:\s*(\d+)|Product No\.?:\s*(\d+)", text)
    if m:
        row["product_no"] = m.group(1) or m.group(2)
    m = re.search(r"Cant\. Descriere\s*\n\s*\d+\s+(.+)|Qty\. Description\s*\n\s*\d+\s+(.+)", text)
    if m:
        row["model"] = (m.group(1) or m.group(2)).strip()
    for col, pats in LABELS.items():
        for pat in pats:
            if col in ("flow_m3h", "max_flow_m3h"):
                m = re.search(pat + r":\s*" + NUM + r"\s*(m³/h|l/s)", text)
                if m:
                    row[col] = to_m3h(m.group(1), m.group(2)); break
            elif col == "max_liquid_temp_c":
                m = re.search(pat + r":\s*[-0-9.]+\s*\.\.\s*" + NUM, text)
                if m:
                    row[col] = m.group(1); break
            elif col in ("voltage", "ie_class", "ip"):
                m = re.search(pat + r":\s*(.+)", text)
                if m:
                    row[col] = m.group(1).strip(); break
            else:
                m = re.search(pat + r":\s*" + NUM, text)
                if m:
                    row[col] = m.group(1).replace(",", "."); break
    # pump count in a set, e.g. "Hydro Multi-E 2 CME"
    m = re.search(r"Hydro \S+\s+(\d)\s", row.get("model", ""))
    row["pump_count"] = m.group(1) if m else "1"
    return row


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("inputs", nargs="+")
    ap.add_argument("-o", "--out", default="data/products.csv")
    a = ap.parse_args()
    files = []
    for i in a.inputs:
        p = Path(i)
        files += sorted(p.rglob("*.[pP][dD][fF]")) if p.is_dir() else [p]
    files = [f for f in files if not f.name.startswith("._") and "__MACOSX" not in str(f)]
    header = open(Path(__file__).parent.parent / "templates/products.csv").readline().strip().split(",")
    out = Path(a.out); out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=header, extrasaction="ignore")
        w.writeheader()
        for pdf in files:
            r = extract(pdf)
            if r.get("flow_m3h") or r.get("head_m"):
                w.writerow(r)
                print(f"ok   {pdf.name}: {r.get('model','?')}  {r.get('flow_m3h','?')} m3/h @ {r.get('head_m','?')} m")
            else:
                print(f"skip {pdf.name}: no pump values found (declaration or other document?)")
    print("->", out)


if __name__ == "__main__":
    sys.exit(main())
