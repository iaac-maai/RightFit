"""Run the product rules on a products file, only where each rule applies (rules.json applies_to).

    python scripts/product_rules_check.py data/products_package_IS15.csv data/declarations_package_IS15.csv

Out-of-scope rules are reported as 'n/a' with the reason, so a form is never returned for a
requirement that doesn't apply (Luca, point 5).
"""
import csv, re, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from rules import RULES, param, applies, cite  # noqa: E402

IE = {"IE1": 1, "IE2": 2, "IE3": 3, "IE4": 4, "IE5": 5}


def norm(s):
    return re.sub(r"[^a-z0-9]", "", s.lower())


def required_ie(kw):
    for lo, hi, cls in param("MOTOR-IE", "bands"):
        if lo <= kw <= hi:
            a, b = param("MOTOR-IE", "ie4_band_from_2023")
            return "IE4" if a <= kw <= b else cls
    return None


def evaluate(products_csv, decl_csv=None):
    """Each product with its rule results [(rule, verdict, detail, declaration file)]; verdict is pass, fail, n/a or ?."""
    fams = []
    if decl_csv:
        fams = [(norm(f), f, d["file"]) for d in csv.DictReader(open(decl_csv)) for f in d["declared_products"].split(";")]
    out = []
    for p in csv.DictReader(open(products_csv)):
        p = {k: (v == "True" if v in ("True", "False") else v) for k, v in p.items()}
        res = []
        # CE-01
        if decl_csv and applies("CE-01", p) is not False:
            hit = next(((f, file) for nf, f, file in fams if norm(p["model"]).startswith(nf)), None)
            res.append(("CE-01", "pass" if hit else "fail", hit[0] if hit else None, hit[1] if hit else None))
        # PUMP-MEI
        s = applies("PUMP-MEI", p)
        if s is False:
            res.append(("PUMP-MEI", "n/a", f"{p.get('pump_type')} is not one of {RULES['PUMP-MEI']['applies_to']['pump_type']}", None))
        elif s is None:
            res.append(("PUMP-MEI", "?", "pump_type unknown, classify the pump first", None))
        else:
            ok = p.get("mei") not in (None, "") and float(p["mei"]) >= param("PUMP-MEI", "mei_min")
            res.append(("PUMP-MEI", "pass" if ok else "fail", f"mei={p.get('mei') or 'not stated'}", None))
        # MOTOR-IE
        s = applies("MOTOR-IE", p)
        if s is False:
            why = "submersible" if p.get("submersible") is True else f"{p.get('motor_type')} motor, not induction"
            res.append(("MOTOR-IE", "n/a", why, None))
        elif s is None:
            res.append(("MOTOR-IE", "?", "motor type unknown", None))
        else:
            req = required_ie(float(p.get("p2_kw") or 0)); have = p.get("ie_class") or ""
            ok = bool(req) and IE.get(have, 0) >= IE[req]
            res.append(("MOTOR-IE", "pass" if ok else "fail", f"has {have or 'not stated'}, needs {req}", None))
        out.append((p, res))
    return out


def main(products_csv, decl_csv=None):
    returns = 0
    for p, res in evaluate(products_csv, decl_csv):
        print(f"\n{p['model']}  ({p.get('pump_type')}, motor {p.get('motor_type')})")
        for rule, verdict, detail, _ in res:
            returns += verdict == "fail"
            if rule == "CE-01":
                print(f"  {verdict.upper()}  CE-01 declaration names it" + (f" ('{detail}')" if detail else "") + f"  [{cite('CE-01')}]")
            elif verdict in ("n/a", "?"):
                print(f"  {verdict:<5} {rule}: {detail}")
            else:
                print(f"  {verdict.upper()}  {rule} {detail}  [{cite(rule)}]")
    print(f"\nverdict: {'RETURN' if returns else 'no product-rule failures'} ({returns} failure(s))")


if __name__ == "__main__":
    main(*sys.argv[1:3])
