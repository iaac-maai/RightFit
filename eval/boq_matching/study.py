"""Study: how should RightFit find a product's BOQ line? Compares the current rule, reading the position from the form,
text similarity, and positions plus similarity, on batch 2 forms outside the frozen test set."""
import csv, json, re, sys, time, warnings
from pathlib import Path
warnings.filterwarnings("ignore")
sys.path.insert(0, ".")
from ingest.boq import read_boq, find_line, sheets_for
from ingest.maf_form import read_form
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

lines = read_boq(next(Path("data/raw/boq").glob("*.xlsx")))
# section of each line (E02 has ICS01, ICS02... headings; others A, B...)
section = None
for ln in lines:
    nr = str(ln["nr"] or "").strip()
    if re.fullmatch(r"[A-Z]{1,4}\d{0,3}", nr) and not nr.isdigit():
        section = nr
    ln["section"] = section
def num(x):
    try: return int(float(str(x).strip()))
    except ValueError: return None

def parse_ref(ref):
    """(sheet code, [(section or None, position)]) from a form's BOQ reference."""
    ref = ref or ""
    out = [(m.group(1), m.group(2), int(m.group(3))) for m in re.finditer(r"\b([A-Z]{1,2}\d{2})\.([A-Z]{2,4}\d{2})\.(\d{1,3})\b", ref)]
    if out:
        return out
    code = re.match(r"\s*([A-Za-z]{1,2}\d{2})", ref)
    if not code:
        return []
    rest = ref[code.end():]
    nums = []
    for a, b in re.findall(r"(\d+)\s*-\s*(\d+)", rest):
        nums += list(range(int(a), int(b) + 1))
    rest = re.sub(r"\d+\s*-\s*\d+", " ", rest)
    nums += [int(n) for n in re.findall(r"\b(\d{1,3})\b", rest)]
    return [(code.group(1).upper(), None, n) for n in nums]

def by_position(ref):
    hits = []
    for sheet, sec, pos in parse_ref(ref):
        for ln in lines:
            if not ln["sheet"].replace(" ", "").upper().startswith(sheet.upper()):
                continue
            nr = str(ln["nr"] or "").strip()
            if sec is not None:   # numbered like ICS01.01 inside the sheet
                head, _, n = nr.partition(".")
                if head == sec and num(n) == pos:
                    hits.append(ln)
            elif num(nr) == pos:
                hits.append(ln)
    return hits

vec = TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), lowercase=True).fit([ln["text"] for ln in lines])
L = vec.transform([ln["text"] for ln in lines])
def by_text(query, pool=None):
    idx = [i for i, ln in enumerate(lines) if pool is None or ln in pool]
    if not idx: return None, 0.0
    s = cosine_similarity(vec.transform([query]), L[idx]).ravel()
    best = s.argmax()
    return lines[idx[best]], float(s[best])

test = {r["package"] for r in csv.DictReader(open("eval/chatbot_baseline/test_set.csv", newline="", encoding="utf-8"))}
inv = list(csv.DictReader(open("data/raw/batch2_inventory.csv", newline="", encoding="utf-8")))
cases = []
# P01: the BOQ reference names only the sheet; the right rows were found by duty and checked by hand on 12 Nov
p01 = json.loads(Path("data/maf/extracted/P01.json").read_text())
truth01 = {"P01-1": 22, "P01-2": 23, "P01-3": 31, "P01-4": 32}
for it in p01["items"]:
    cases.append({"pkg": "P01", "ref": p01["form"]["boq_ref"], "query": f'{it["name"]} {it["model"]} {it["values"]["used_for"]["quote"]}',
                  "item": it, "truth": {("IS06 Echipamente", truth01[it["id"]])}})
for r in inv:
    p = r["package"]
    if p in test or p == "P10":
        continue
    forms = [f for f in Path("data/raw", p).glob("*") if f.suffix.lower() in (".xls", ".xlsx") and not f.name.startswith("~$")]
    try:
        fm = read_form(forms[0])
    except Exception:
        continue
    gold = by_position(fm["boq_ref"])
    for it in fm.get("items_raw", []):
        q = " ".join(str(it.get(k, "")) for k in ("name", "brand", "model"))
        cases.append({"pkg": p, "ref": fm["boq_ref"], "query": q, "item": None,
                      "truth": {(g["sheet"], g["row"]) for g in gold}})
cases = [c for c in cases if c["truth"]]
res = {"current rule": 0, "position from the form": 0, "text, whole BOQ": 0, "text, in the form's sheet": 0, "position, then text": 0}
t0 = time.time()
rows = []
for c in cases:
    got = {}
    got["current rule"] = find_line(lines, c["ref"], c["item"]) if c["item"] else None
    pos = by_position(c["ref"])
    got["position from the form"] = pos[0] if len(pos) == 1 else None   # only an unambiguous position counts
    got["text, whole BOQ"], s1 = by_text(c["query"])
    got["text, in the form's sheet"], s2 = by_text(c["query"], sheets_for(lines, c["ref"]) or None)
    got["position, then text"] = by_text(c["query"], pos)[0] if pos else got["text, in the form's sheet"]
    row = {"pkg": c["pkg"], "query": c["query"][:45]}
    for k, ln in got.items():
        ok = bool(ln) and (ln["sheet"], ln["row"]) in c["truth"]
        res[k] += ok
        row[k] = "ok" if ok else ("none" if not ln else "wrong")
    row["score"] = round(s2, 2)
    rows.append(row)
print(f"{len(cases)} cases, {time.time() - t0:.2f} s for all methods")
for k, v in res.items():
    print(f"  {k:28s} {v}/{len(cases)}")
print()
for r in rows:
    print(r)
