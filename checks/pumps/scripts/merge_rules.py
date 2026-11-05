"""Merge the repo's data/maf/rules.csv into rules/rules.json so there is ONE rule table.

    python scripts/merge_rules.py path/to/data/maf/rules.csv            # dry run: shows what would change
    python scripts/merge_rules.py path/to/data/maf/rules.csv --write

Column names are matched loosely (id/rule_id/code, rule/description/text, source/reference,
product/scope/category, threshold/value/tolerance). Unknown columns are kept under "extra".
Rows whose id already exists are reported as conflicts, never overwritten.
NOT YET RUN ON THE REAL FILE: check the dry-run output before --write.
"""
import csv, json, sys
from pathlib import Path

RULES = Path(__file__).parent.parent / "rules" / "rules.json"
MAP = {"id": ["id", "rule_id", "code", "rule"], "rule": ["description", "rule_text", "text", "requirement", "rule"],
       "source": ["source", "reference", "ref", "standard", "clause"], "product": ["product", "scope", "category", "applies_to"],
       "params": ["threshold", "value", "tolerance", "limit", "params"]}


def pick(row, keys, used):
    for k in keys:
        for col in row:
            if col.strip().lower() == k and col not in used:
                used.add(col); return row[col]
    return ""


def main(path, write=False):
    data = json.load(open(RULES)); have = {r["id"] for r in data["rules"]}
    added, conflicts = [], []
    for row in csv.DictReader(open(path, encoding="utf-8-sig")):
        used = set(); r = {f: pick(row, keys, used) for f, keys in MAP.items()}
        if not r["id"]:
            continue
        r["extra"] = {k: v for k, v in row.items() if k not in used and v}
        r["params"] = {"value": r["params"]} if r["params"] else {}
        r.update(status="from repo rules.csv (not re-checked)", applies_to={}, origin=str(path))
        (conflicts if r["id"] in have else added).append(r)
    print(f"{len(added)} new rules, {len(conflicts)} with an id already in rules.json")
    for r in conflicts: print("  conflict:", r["id"], "-", r["rule"][:70])
    for r in added: print("  new:", r["id"], "-", r["rule"][:70])
    if write:
        data["rules"] += added; json.dump(data, open(RULES, "w"), indent=2, ensure_ascii=False); print("written")


if __name__ == "__main__":
    main(sys.argv[1], "--write" in sys.argv)
