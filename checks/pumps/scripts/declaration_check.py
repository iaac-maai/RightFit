"""Rule CE-01 on a package: does every submitted product have a declaration that names it?

    python scripts/declaration_check.py data/products_package_IS15.csv data/declarations_package_IS15.csv

Matches each product's model to the product families named in the declarations
(e.g. 'UNILIFT AP12.50.11.3' is covered by 'Unilift AP'). Prints one line per product and
the package verdict: this is round 1 of the studio review, done by the tool.
"""
import csv, re, sys


def norm(s):
    return re.sub(r"[^a-z0-9]", "", s.lower())


def main(products_csv, decl_csv):
    decls = list(csv.DictReader(open(decl_csv)))
    families = [(norm(f), f, d["file"]) for d in decls for f in d["declared_products"].split(";")]
    used, missing = set(), []
    for p in csv.DictReader(open(products_csv)):
        m = norm(p["model"])
        hits = [(f, file) for nf, f, file in families if m.startswith(nf)]
        if hits:
            used.add(hits[0][1])
            print(f"covered   {p['model']:<40} by '{hits[0][0]}' in {hits[0][1]}")
        else:
            missing.append(p["model"])
            print(f"MISSING   {p['model']:<40} no declaration names this product")
    for d in decls:
        if d["file"] not in used:
            print(f"UNUSED    {d['file']:<40} names {d['declared_products']}: no submitted product")
    print("\nverdict:", "RETURN" if missing else "documents complete",
          f"({len(missing)} product(s) without a declaration; rule CE-01)")


if __name__ == "__main__":
    main(*sys.argv[1:3])
