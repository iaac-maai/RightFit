"""The engine of RightFit online (web/engine/): one request from the site, answered with the laptop's own code
(app/review_core.py, checks/maf). The site keeps the project's data and sends what one review needs: a package's
readings, the reviewer's decisions on its findings, the BOQ lines found for it, the project's rule tables and, when a
person changed something, that one change. The engine applies the change the way the laptop's app does, runs the
checks and sends everything back. It keeps nothing between requests and reads no file.

A change is one of:
  {"op": "confirm", "targets": [...]}                  ticks on readings, as on the laptop's Readings step
  {"op": "decide", "id": ..., "status": ..., "note"}   a decision on an AI suggestion
  {"op": "decisions", "decisions": {key: ...}}         findings kept in the answer, or marked not a problem
  {"op": "new_rule", "rule": {...}}                    a consultant's rule written by hand on the Rules page
  {"op": "rule_active", "rule_id": ..., "active": b}   a consultant's rule switched on or off
"""
from app.review_core import confirm, decide, decide_findings, new_consultant_rule, review

PACKAGE_CHANGES = {"confirm", "decide", "decisions"}
RULE_CHANGES = {"new_rule", "rule_active"}


def handle(body):
    """Apply the change, if any, then review the package, if one was sent. Raises KeyError, ValueError or
    StopIteration on a request that does not fit, and the site shows the message."""
    data = body["tables"]
    who = " ".join(str(body.get("reviewer") or "").split())[:80] or "a reviewer"
    change = body.get("change") or {}
    op = change.get("op")
    if op is not None and op not in PACKAGE_CHANGES | RULE_CHANGES:
        raise ValueError(f"unknown change {op!r}")
    out = {}
    if op == "new_rule":
        data["consultant"].append(new_consultant_rule(change["rule"], data["consultant"]))
    elif op == "rule_active":
        rule = next(r for r in data["consultant"] if r["rule_id"] == change["rule_id"])
        rule["active"] = "yes" if change["active"] else "no"
    if op in RULE_CHANGES:
        out["consultant"] = data["consultant"]
    if "pkg" not in body:
        if op in PACKAGE_CHANGES:
            raise ValueError("a change to a package needs the package")
        return out
    pkg, decisions = body["pkg"], body.get("decisions") or {}
    if op == "confirm":
        confirm(pkg, change["targets"], who)
    elif op == "decide":
        decide(pkg, change["id"], change["status"], change.get("note"), who)
    elif op == "decisions":
        decide_findings(decisions, change["decisions"], who)
    dismissed = {k: d["reason"] for k, d in decisions.items() if d["decision"] == "dismissed"}
    view = review(pkg, body.get("location") or "RO", None, None, dismissed, body.get("boq"), data)
    return {**out, "pkg": pkg, "decisions": decisions, "view": {**view, "decisions": decisions}}
