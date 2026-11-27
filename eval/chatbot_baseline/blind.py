"""Chatbot baseline (MAF-20, issue #12): one blind list of findings for Luca to judge, then the scores.

The protocol is eval/chatbot_baseline/protocol.md. The chatbots' answers and everything built from them stay on
the laptop in data/raw/chatbot_baseline/ (git-ignored, like the packages); only results.md goes into Git.

Files in data/raw/chatbot_baseline/:
  P01_bot1_run1.txt ...  each chatbot answer as it came, one file per run (bot1 is Claude.ai, bot2 is ChatGPT)
  findings.csv           every single finding: package, source, group, what, file, page, quote, by_hand
                         source is rightfit or bot1_run1, bot2_run2 ...; findings of one package that say the
                         same thing share a group; what is cut to 25 words, never rewritten; by_hand is yes or no
                         when a person checked the page and quote by hand, else empty
  answers.csv            each chatbot run's answer: package, source, letter (A, B or C)
  judge.csv              written by `judge`: one row per group, shuffled, no source; Luca writes in the mark
                         column real, not or ? (can't tell)

From the repository root:
  python3 -m eval.chatbot_baseline.blind rightfit   puts RightFit's findings for P01 and P02 into findings.csv
  python3 -m eval.chatbot_baseline.blind judge      writes judge.csv
  python3 -m eval.chatbot_baseline.blind score      checks pages and quotes, reads the marks, prints the tables
"""
import csv
import json
import random
import sys
import unicodedata
from pathlib import Path

import pymupdf

from app.review_core import review
from eval.reference_answers.compare import REFERENCE, reference_letter

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw"
RUNS = RAW / "chatbot_baseline"
EXTRACTED = ROOT / "data" / "maf" / "extracted"
PACKAGES = ("P01", "P02")
BOTS = {"bot1": "Claude.ai", "bot2": "ChatGPT"}
FIELDS = ["package", "source", "group", "what", "file", "page", "quote", "by_hand"]
JUDGE_FIELDS = ["id", "package", "what", "file", "page", "quote", "mark"]
MARKS = {"real": "real", "not": "not", "?": "can't tell"}
SEED = 12   # fixed, so the same findings always give the same list and the same ids


def cut(text, words=25):
    """The protocol's form: at most 25 words, cut and never rewritten."""
    return " ".join(str(text).split()[:words])


def rightfit_findings(package, location="RO"):
    """The problems RightFit's review page shows for a package: the checks only, not the AI suggestions."""
    pkg = json.loads((EXTRACTED / f"{package}.json").read_text())
    rows = []
    for r in review(pkg, location)["results"]:
        if r["verdict"] != "flag":
            continue
        file, _, page = (r["sources"][0] if r["sources"] else "").partition(", p. ")
        what = r["title"] + (f" ({r['product']})" if r["product"] else "") + f": {r['reason']}"
        rows.append({"package": package, "source": "rightfit", "group": "", "what": cut(what),
                     "file": file, "page": page, "quote": "", "by_hand": ""})
    return rows


def groups(findings):
    """Each finding's group, as (package, group); a finding with no group is a group of its own."""
    return [(f["package"], f["group"] or f"alone-{i}") for i, f in enumerate(findings)]


def judge_list(findings, seed=SEED):
    """One row per group of findings that say the same thing, shuffled, with the source hidden. The wording
    shown is one member's, picked at random, so which source wrote it is not given away by the order."""
    rng = random.Random(seed)
    members = {}
    for g, f in zip(groups(findings), findings):
        members.setdefault(g, []).append(f)
    order = list(members)
    rng.shuffle(order)
    rows, ids = [], {}
    for n, g in enumerate(order, 1):
        shown = rng.choice(members[g])
        ids[g] = f"F{n:03d}"
        rows.append({"id": ids[g], "package": g[0], "what": shown["what"], "file": shown["file"] or "no file given",
                     "page": shown["page"] or "no page given", "quote": shown["quote"], "mark": ""})
    return rows, ids


def plain(text):
    """Text for comparing a quote with a page: no accents (ş and ș alike), lower case, single spaces."""
    text = "".join(c for c in unicodedata.normalize("NFKD", text) if not unicodedata.combining(c))
    return " ".join(text.lower().split())


def page_and_quote(f, raw=RAW):
    """True when the quote is on the page given, False when it is not or the file or page does not exist,
    None when a script cannot tell: no page or quote given, the .xls form, or a scan with no text."""
    if f.get("by_hand") in ("yes", "no"):
        return f["by_hand"] == "yes"
    if not f["page"]:
        return None
    path = raw / f["package"] / f["file"]
    if not path.is_file():
        return False
    if path.suffix.lower() != ".pdf":
        return None
    with pymupdf.open(path) as doc:
        page = int(f["page"]) if f["page"].isdigit() else 0
        if not 1 <= page <= doc.page_count:
            return False
        text = doc[page - 1].get_text(sort=True)
    if not f["quote"] or not text.strip():
        return None
    return plain(f["quote"]) in plain(text)


def score(findings, judge, answers, raw=RAW):
    """For each package and source: findings, real problems, not problems, can't tell, real out of all the real
    problems any source found, wrong pages or quotes, and the answer. judge must be the list judge_list made
    from these same findings, with Luca's marks in it."""
    rows, ids = judge_list(findings)
    marks = {j["id"]: j for j in judge}
    for r in rows:   # the marks belong to this exact list, or the scores would be wrong
        j = marks.get(r["id"])
        if not j or j["what"] != r["what"]:
            raise ValueError(f"{r['id']}: findings.csv changed after judge.csv was written; write judge.csv again")
        if j["mark"].strip() not in MARKS:
            raise ValueError(f"{r['id']}: mark is {j['mark']!r}, it must be real, not or ?")
    mark = {g: MARKS[marks[i]["mark"].strip()] for g, i in ids.items()}
    letters = {(a["package"], a["source"]): a["letter"].strip() for a in answers}
    out = []
    for package in sorted({f["package"] for f in findings}):
        found = {}
        for g, f in zip(groups(findings), findings):
            if f["package"] == package:
                found.setdefault(f["source"], {"groups": set(), "checks": []})
                found[f["source"]]["groups"].add(g)
                found[f["source"]]["checks"].append(page_and_quote(f, raw))
        real = {g for g, m in mark.items() if g[0] == package and m == "real"}
        for source, s in sorted(found.items()):
            out.append({"package": package, "source": source, "findings": len(s["checks"]),
                        "real": sum(mark[g] == "real" for g in s["groups"]),
                        "not": sum(mark[g] == "not" for g in s["groups"]),
                        "cant_tell": sum(mark[g] == "can't tell" for g in s["groups"]),
                        "of_all_real": len(real),
                        "wrong_page_or_quote": s["checks"].count(False),
                        "not_checked": s["checks"].count(None),
                        "letter": letters.get((package, source), ""), "groups": s["groups"]})
    return out


def run_differences(rows):
    """For each chatbot and package: findings in both runs, in one run only, and whether the answer is the same."""
    by = {(r["package"], r["source"]): r for r in rows}
    out = []
    for package in sorted({r["package"] for r in rows}):
        for bot in BOTS:
            a, b = by.get((package, f"{bot}_run1")), by.get((package, f"{bot}_run2"))
            if a and b:
                out.append({"package": package, "bot": BOTS[bot], "both": len(a["groups"] & b["groups"]),
                            "one_only": len(a["groups"] ^ b["groups"]), "same_answer": a["letter"] == b["letter"]})
    return out


def read(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def write(path, rows, fields):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fields)
        w.writeheader()
        w.writerows(rows)


def name(source):
    return "RightFit" if source == "rightfit" else f"{BOTS[source[:4]]} run {source[-1]}"


def main(step):
    findings_csv = RUNS / "findings.csv"
    if step == "rightfit":   # RightFit's rows are written again; every other row is kept as it is
        kept = [f for f in read(findings_csv) if f["source"] != "rightfit"] if findings_csv.exists() else []
        write(findings_csv, kept + [f for p in PACKAGES for f in rightfit_findings(p)], FIELDS)
    elif step == "judge":
        rows, _ = judge_list(read(findings_csv))
        write(RUNS / "judge.csv", rows, JUDGE_FIELDS)
        print(f"{len(rows)} findings to judge in {RUNS / 'judge.csv'}")
    elif step == "score":
        answers = read(RUNS / "answers.csv") + [
            {"package": p, "source": "rightfit",
             "letter": review(json.loads((EXTRACTED / f"{p}.json").read_text()), "RO")["status"]["letter"]} for p in PACKAGES]
        findings = read(findings_csv)
        rows = score(findings, read(RUNS / "judge.csv"), answers)
        luca = {p: reference_letter((REFERENCE / f"{p}.md").read_text()) for p in PACKAGES}
        print("| Package | Source | Findings | Real | Not a problem | Can't tell | Real of all real found | "
              "Wrong page or quote | Page or quote not checkable | Answer | Luca |\n|---|---|---|---|---|---|---|---|---|---|---|")
        for r in rows:
            print(f"| {r['package']} | {name(r['source'])} | {r['findings']} | {r['real']} | {r['not']} | {r['cant_tell']} | "
                  f"{r['real']} of {r['of_all_real']} | {r['wrong_page_or_quote']} | {r['not_checked']} | {r['letter']} | {luca.get(r['package'], '')} |")
        print("\n| Package | Chatbot | Same finding in both runs | In one run only | Same answer |\n|---|---|---|---|---|")
        for d in run_differences(rows):
            print(f"| {d['package']} | {d['bot']} | {d['both']} | {d['one_only']} | {'yes' if d['same_answer'] else 'no'} |")
        hand = [f for f in findings if f["page"] and page_and_quote(f) is not True and not f["by_hand"]]
        print(f"\nTo check by hand (write yes or no in by_hand): {len(hand)}")
        for f in hand:
            print(f"  {f['package']} {f['source']} {f['file']} p. {f['page']}: {f['quote']!r}")
    else:
        sys.exit("usage: python3 -m eval.chatbot_baseline.blind rightfit | judge | score")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "")
