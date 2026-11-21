"""Copies the engine's Python into build/ before Wrangler bundles it: entry.py, and from the repository the laptop's
review code (app/engine.py, app/review_core.py, app/booster.py), the checks (checks/maf) and the booster sizing's
scripts and data (checks/pumps). build/ is not kept in Git."""
import shutil
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OUT = HERE / "build"

shutil.rmtree(OUT, ignore_errors=True)
PUMPS = ROOT / "checks/pumps"   # the booster set sizing: its two scripts, the catalogue and the rules, all in Git
FILES = [HERE / "entry.py", ROOT / "app/engine.py", ROOT / "app/review_core.py", ROOT / "app/booster.py",
         *sorted((ROOT / "checks/maf").glob("*.py")), PUMPS / "scripts/booster_check.py", PUMPS / "scripts/rules.py",
         PUMPS / "data/curves_booster_sets.csv", PUMPS / "data/cte_hs4_fixture_flows.csv", PUMPS / "rules/rules.json"]
for source in FILES:
    target = OUT / source.relative_to(HERE if source.parent == HERE else ROOT)
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)
for package in ("app", "checks", "checks/maf"):   # plain packages, so the imports work the same everywhere
    (OUT / package / "__init__.py").touch()
print(f"engine: {sum(1 for _ in OUT.rglob('*.py'))} Python files and {sum(1 for f in OUT.rglob('*') if f.suffix in ('.csv', '.json'))} data files in build/")
