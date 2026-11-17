# tests: the checks of the checks

Run them all with `pytest` from the repository's root; it takes under a minute.

- one file per part: `test_maf_checks.py` for the checks, `test_review_server.py` for the application, `test_mcp_server.py` for the agent tools, `test_space_checks.py` for the fit check in Revit, and so on;
- `maf_cases.py` holds the small made-up packages the tests share;
- `rule_watch/` holds saved answers of the official sources, so the rule watch is tested without the internet;
- a few tests need the original packages, which stay on the laptops; elsewhere they are skipped.
