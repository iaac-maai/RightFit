"""One place for rules: every script reads its thresholds and scope from rules/rules.json.

    from rules import RULES, param, applies
    param("HS4-PMAX", "p_max_m")            -> 50
    applies("PUMP-MEI", {"pump_type": "MS-H"}) -> False (out of scope, so no false return)
"""
import json
from pathlib import Path

_PATH = Path(__file__).parent.parent / "rules" / "rules.json"
RULES = {r["id"]: r for r in json.load(open(_PATH))["rules"]}


def param(rule_id, key):
    return RULES[rule_id]["params"][key]


def cite(rule_id):
    r = RULES[rule_id]
    import re
    src = re.split(r" \(|; |\. ", r["source"])[0]
    return f"{rule_id}: {src}{', p' + str(r['page']) if r.get('page') else ''}"


def applies(rule_id, product):
    """True only if the product matches every applies_to key. Unknown field -> 'unknown' (None)."""
    for key, allowed in RULES[rule_id].get("applies_to", {}).items():
        if key.endswith("_not"):
            if product.get(key[:-4]) in allowed:
                return False
            continue
        value = product.get(key)
        if value in (None, ""):
            return None
        if isinstance(allowed, list) and value not in allowed:
            return False
    return True
