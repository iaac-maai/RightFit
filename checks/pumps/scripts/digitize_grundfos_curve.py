"""Read the Q-H curves of a Grundfos Product Center data sheet straight from its vector drawing.

    python scripts/digitize_grundfos_curve.py datasheet.pdf --page 3 -o data/curves_package_IS15.csv

The axes are calibrated from the printed tick labels (H on the left, Q along the bottom), every
dark-blue curve on the chart is converted to (Q, H) points, and the curves are named by how far
they reach: on a 2-pump set the short curve is one pump at full speed, the long one is both pumps.
"""
import argparse, csv, re
from pathlib import Path
import numpy as np, pymupdf

BLUE = (0.0235, 0.2941, 0.5255)          # Grundfos curve colour


def calibrate(page):
    words = page.get_text("words")
    nums = [w for w in words if re.fullmatch(r"\d+", w[4])]
    h = [(float(w[4]), (w[1] + w[3]) / 2) for w in nums if w[2] < 80 and w[1] < 480]
    q_row = max((w[1] for w in nums if 470 < w[1] < 485), default=None)
    q = [(float(w[4]), (w[0] + w[2]) / 2) for w in nums if abs(w[1] - q_row) < 1 and w[0] > 60]
    return np.polyfit([y for _, y in h], [v for v, _ in h], 1), np.polyfit([x for _, x in q], [v for v, _ in q], 1)


def curves(page):
    ah, aq = calibrate(page)
    out = []
    for dr in page.get_drawings():
        c = dr.get("color")
        if not c or max(abs(a - b) for a, b in zip(c, BLUE)) > 0.02 or (dr.get("width") or 0) < 0.5:
            continue
        pts = []
        for it in dr["items"]:
            if it[0] == "l": pts += [it[1], it[2]]
            elif it[0] == "c": pts += [it[1], it[4]]
        qh = sorted({(round(float(np.polyval(aq, p.x)), 2), round(float(np.polyval(ah, p.y)), 2)) for p in pts})
        if len(qh) > 20 and qh[-1][0] - qh[0][0] > 5 and min(h for _, h in qh) >= 0:
            out.append(qh)
    # keep the distinct full-speed envelopes (highest shut-off head), shortest first
    uniq = {}
    for c in out:
        key = round(c[-1][0])
        if key not in uniq or c[0][1] > uniq[key][0][1]:
            uniq[key] = c
    return [uniq[k] for k in sorted(uniq)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pdf"); ap.add_argument("--page", type=int, default=3)
    ap.add_argument("--model", default=""); ap.add_argument("-o", "--out", default="data/curves_package.csv")
    a = ap.parse_args()
    page = pymupdf.open(a.pdf)[a.page - 1]
    cs = curves(page)
    names = ["1 pump running", "2 pumps running", "3 pumps running", "4 pumps running"]
    out = Path(a.out); new = not out.exists()
    with open(out, "a", newline="") as f:
        w = csv.writer(f)
        if new: w.writerow(["model", "curve", "q_m3h", "h_m", "source_file", "page"])
        for name, c in zip(names, cs):
            step = max(1, len(c) // 40)
            for q, h in c[::step] + [c[-1]]:
                w.writerow([a.model, name, q, h, Path(a.pdf).name, a.page])
            print(f"{name}: Q {c[0][0]:.1f}-{c[-1][0]:.1f} m3/h, H {c[0][1]:.1f}-{c[-1][1]:.1f} m")


if __name__ == "__main__":
    main()
