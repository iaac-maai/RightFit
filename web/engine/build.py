"""Copies the engine's Python into build/ before Wrangler bundles it: entry.py, and from the repository the laptop's
review code (app/engine.py, app/review_core.py) and the checks (checks/maf). build/ is not kept in Git."""
import shutil
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OUT = HERE / "build"

shutil.rmtree(OUT, ignore_errors=True)
for source in [HERE / "entry.py", ROOT / "app/engine.py", ROOT / "app/review_core.py", *sorted((ROOT / "checks/maf").glob("*.py"))]:
    target = OUT / source.relative_to(HERE if source.parent == HERE else ROOT)
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)
for package in ("app", "checks", "checks/maf"):   # plain packages, so the imports work the same everywhere
    (OUT / package / "__init__.py").touch()
print(f"engine: {sum(1 for _ in OUT.rglob('*.py'))} Python files in build/")
