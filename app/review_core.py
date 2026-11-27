"""The review of one package as RightFit shows it: the checks run on the package's readings, each result named and
explained, the draft answer, and the reviewer's ticks and decisions applied to the readings. Plain Python on top of
checks/maf, with no files and no web in it, so the laptop's app (app/review_server.py) and the engine of RightFit
online (web/engine/) run the very same code.
"""
import re
from datetime import date, timedelta

from checks.maf.checks import DOC_LABELS, KINDS, context, run_all
from checks.maf.comments import comment, title
from checks.maf.rules import DATA, load, tables
from checks.maf.status import LABELS, draft_status

CHECK_NAMES = {"D1": "Required documents", "D2": "Declaration matches the products", "D3": "Certificate in date",
               "D4": "Attachment is what the form says", "V1": "Duty point", "V2": "Pressure rating", "V3": "Liquid temperature",
               "E1": "Ecodesign", "H1": "Drinking water approval", "C": "Reviewers' checklist", "P": "Consultant's rules", "Q": "BOQ line", "R": "Delivery reminder"}


VALUE_NAMES = {"used_for": "Used for (form)", "duty_flow": "Required flow (form)", "duty_head": "Required head (form)",
               "duty_airflow_supply": "Required supply airflow (form)",
               "duty_airflow_extract": "Required extract airflow (form)", "flow": "Flow at the duty point",
               "head": "Head at the duty point", "power": "Motor power", "max_pressure": "Max working pressure",
               "controller_included": "Controller or panel included", "bms_included": "BMS module included",
               "bms_protocol": "BMS protocols", "hrs_type": "Heat recovery type",
               "hrs_efficiency": "Heat recovery efficiency", "sfp_int": "SFPint", "sfp_int_limit": "SFPint limit",
               "gwp": "GWP", "seer": "SEER", "scop": "SCOP", "dx_refrigerant": "DX coil refrigerant"}


DECISIONS = ("suggested", "accepted", "rejected")


def value_name(key):
    return VALUE_NAMES.get(key, key.replace("_", " ").capitalize())


def key_of(r):
    """A stable name for one check result: the reviewer's decision on it is saved under this name."""
    key = "|".join(str(x) for x in (r["check"], r["item"], r["doc"], ",".join(r["rules"]), r["code"]))
    return f"{key}|{r['params']['text']}" if r["code"] == "Q.rule" else key   # one BOQ line asks several things


def rule_info(rule_id, status, rules, checklist, consultant=None):
    """One rule or checklist item in plain fields, for the reviewer who asks what a finding rests on."""
    if consultant and rule_id in consultant:
        return {"id": rule_id, "status": "consultant", "text": consultant[rule_id]["text"],
                "source": "The consultant's own rule, not a legal requirement", "url": ""}
    if rule_id in rules:
        r = rules[rule_id]
        return {"id": rule_id, "status": status, "text": r["requirement"], "source": " ".join(x for x in (r["code"], r["clause"]) if x),
                "url": r["source_url"]}
    item = checklist.get(rule_id, {})
    return {"id": rule_id, "status": status, "text": item.get("item", ""), "source": "Past reviewers' comments", "url": ""}


# The consultant's own rules (spec section 6, check P). The Rules screen adds them and switches them on or off.
CONSULTANT = DATA / "consultant_rules.csv"
CONSULTANT_FIELDS = ["rule_id", "family", "application", "kind", "field", "operator", "value", "unit", "effect", "text",
                     "source", "added_on", "active"]


WORDS = re.compile(r"[a-z0-9_]+([;|][a-z0-9_]+)*")


def new_consultant_rule(body, rows, today=None):
    """A rule typed on the Rules screen, checked field by field before it is written; raises ValueError."""
    clean = {k: " ".join(str(body.get(k) or "").split()) for k in CONSULTANT_FIELDS}
    kind, family = clean["kind"], clean["family"].lower() or "all"
    if kind not in KINDS:
        raise ValueError(f"kind must be one of {', '.join(KINDS)}")
    if clean["effect"] not in ("B", "C", "info"):
        raise ValueError("effect must be B, C or info")
    if not WORDS.fullmatch(family) or (clean["application"] and not WORDS.fullmatch(clean["application"].lower())):
        raise ValueError("family and application are words like pump or circulation;stormwater")
    if not 3 <= len(clean["text"]) <= 200:
        raise ValueError("say in a few words what the rule asks (3 to 200 characters)")
    if kind in ("value", "document", "included") and not WORDS.fullmatch(clean["field"]):
        raise ValueError("say which reading or document the rule looks at")
    if kind == "brand" and not clean["value"]:
        raise ValueError("give the accepted brands, separated by ;")
    if kind == "value":
        if clean["operator"] not in (">=", "<=", "="):
            raise ValueError("operator must be >=, <= or =")
        if clean["operator"] != "=":
            try:
                float(clean["value"])
            except ValueError:
                raise ValueError("the limit must be a number, for example 16") from None
    # Only the fields the kind uses are kept, so a rule reads the way it works.
    used = {"brand": ("value",), "value": ("field", "operator", "value", "unit"), "document": ("field",),
            "included": ("field",), "reminder": ()}[kind]
    clean.update({k: "" for k in ("field", "operator", "value", "unit") if k not in used})
    numbers = [int(r["rule_id"][3:]) for r in rows if r["rule_id"][3:].isdigit()]
    return {**clean, "family": family, "application": clean["application"].lower(),
            "rule_id": f"CR-{max(numbers, default=0) + 1:02d}", "source": clean["source"] or "added on the Rules screen",
            "added_on": (today or date.today()).isoformat(), "active": "yes"}


def review(pkg, location="RO", review_date=None, delivery_date=None, dismissed=None, boq=None, data=None):
    """Everything the page shows for one package. dismissed maps a result key to the reviewer's reason;
    boq is what boq_links found (None: the BOQ is left out). data holds the rule tables when they do not come from
    data/maf: rules, family_documents and checklist as rows, library, and consultant (the consultant's rules)."""
    form = pkg["form"]
    review_date = review_date or date.fromisoformat(form["date"])
    delivery_date = delivery_date or review_date + timedelta(weeks=form["delivery_weeks"] or 0)
    dismissed = dismissed or {}
    given = {} if data is None else {
        "data": ({r["rule_id"]: r for r in data["rules"]}, data["family_documents"], data["checklist"]),
        "lib": data["library"], "consultant": data["consultant"]}
    results = run_all(pkg if boq is None else {**pkg, "boq": boq}, context(location, review_date, delivery_date, **given))
    for r in results:
        r["key"] = key_of(r)
        r["title"] = title(r) or CHECK_NAMES[r["check"]]   # before a dismissal turns the result into a pass
        if r["key"] in dismissed:
            # A finding the reviewer marked "not a problem" counts as OK from here on, with the reason kept.
            r["result"] = r["would_be"] = "pass"
            r["dismissed"] = dismissed[r["key"]] or "no reason given"

    ai = pkg.get("ai_findings", [])
    accepted = [f for f in ai if f["status"] == "accepted"]
    letter, reasons = draft_status(results, "would_be", [f["title"] for f in accepted])
    comments = [comment(r) for r in results]
    rank = {"flag": 0, "unclear": 1}
    ordered = sorted(zip(results, comments), key=lambda rc: rank.get(rc[0]["would_be"], 2))   # stable: check order inside
    lines = list(dict.fromkeys([c for _, c in ordered if c] + [f["suggested_comment"] for f in accepted]))
    number = {line: n for n, line in enumerate(lines, 1)}   # the comment number in the answer, shown as a delta
    items = {i["id"]: i for i in pkg["items"]}
    item_label = {i["id"]: f"{i['name']} ({i['model'] or 'no model on the form'})" for i in pkg["items"]}
    rule_table, _, checklist_rows = given["data"] if given else tables()
    checklist = {row["id"]: row for row in checklist_rows}
    consultant = {row["rule_id"]: row for row in (data["consultant"] if given else load(CONSULTANT.name))}

    def evidence(r):
        """What the AI read on the pages a result points to, for its product."""
        out = []
        for i in pkg["items"]:
            if r["item"] not in (None, i["id"]):
                continue
            for k, x in i["values"].items():
                if f"{x['source']}, p. {x['page']}" in r["sources"]:
                    out.append({"item": i["id"], "key": k, "what": value_name(k), "value": x["value"], "unit": x["unit"], "source": x["source"],
                                "page": x["page"], "quote": x["quote"], "status": x["status"]})
        return out

    docs = []
    for n, d in enumerate(pkg["documents"], 1):
        docs.append({"no": n, "file": d["file"], "type": DOC_LABELS.get(d["doc_type"], d["doc_type"]),
                     "listed_as": d["listed_as"], "covers": d["covers"], "issuer": d["issuer"],
                     "issue_date": d["issue_date"], "valid_until": d["valid_until"], "pages": d["pages"],
                     "method": d["method"], "languages": d["languages"], "status": d["status"], "notes": d["notes"],
                     "checked_by": d.get("checked_by"), "confirmed_in": d.get("confirmed_in"),
                     "matches": [{"item": m["item"], "product": item_label.get(m["item"], m["item"]), "kind": m["kind"],
                                  "page": m["page"], "quote": m["quote"], "status": m["status"]}
                                 for m in d.get("matches", [])]})
    doc_no = {d["file"]: d["no"] for d in docs}

    out_results = []
    for r, c in zip(results, comments):
        out_results.append({
            "key": r["key"], "check": r["check"], "check_name": CHECK_NAMES[r["check"]], "title": r["title"],
            "item": r["item"],
            "product": item_label.get(r["item"]), "doc": r["doc"], "doc_no": doc_no.get(r["doc"]),
            "verdict": r["would_be"], "confirmed": r["result"] == r["would_be"], "reason": r["reason"],
            "sources": r["sources"],
            "rules": [rule_info(i, r["rule_status"].get(i, "checklist"), rule_table, checklist, consultant)
                      for i in r["rules"]],
            "blocking": r["blocking"], "comment": c, "delta": number.get(c), "dismissed": r.get("dismissed"),
            "evidence": evidence(r)})

    readings = ([x for i in pkg["items"] for x in i["values"].values()] + pkg["documents"]
                + [m for d in pkg["documents"] for m in d.get("matches", [])])
    return {
        "package": pkg["package"], "location": location, "review": review_date.isoformat(),
        "delivery": delivery_date.isoformat(),
        "form": {k: form.get(k) for k in ("form_no", "revision", "date", "delivery_raw", "boq_ref")},
        "status": {"letter": letter, "label": LABELS[letter], "reasons": reasons},
        "counts": {"problems": sum(r["verdict"] == "flag" for r in out_results),
                   "questions": sum(r["verdict"] == "unclear" for r in out_results),
                   "passed": sum(r["result"] == "pass" and not r.get("dismissed") for r in results),
                   "would_pass": sum(r["would_be"] == "pass" and r["result"] != "pass" and not r.get("dismissed")
                                     for r in results),
                   "dismissed": sum(bool(r.get("dismissed")) for r in results),
                   "to_confirm": sum(x["status"] != "verified" for x in readings), "readings": len(readings),
                   "ai_to_decide": sum(f["status"] == "suggested" for f in ai)},
        "items": [{"id": i["id"], "name": i["name"], "brand": i["brand"], "model": i["model"],
                   "values": [{"key": k, "what": value_name(k), **x} for k, x in i["values"].items()]}
                  for i in items.values()],
        "documents": docs,
        "results": out_results,
        "ai_findings": [{**f, "products": [item_label.get(i, i) for i in f["items"]],
                         "delta": number.get(f["suggested_comment"]) if f["status"] == "accepted" else None}
                        for f in ai],
        "notes": pkg.get("notes_for_reviewer", []),
        "answer": {"lines": lines, "text": f"MAF {form['form_no']} rev {form['revision']}: {LABELS[letter]} ({letter})\n\n"
                   + ("\n".join(f"{n}. {line}" for n, line in enumerate(lines, 1)) or "No comments.")},
    }


def set_verified(entry, verified, reviewer):
    """Mark a value, document or match as confirmed by the reviewer, or put it back to what the AI left."""
    if verified == (entry["status"] == "verified"):
        return
    has_value = entry.get("value") not in (None, "") if "value" in entry else True
    entry["status"] = "verified" if verified else ("extracted" if has_value else "unclear")
    entry["checked_by"] = reviewer if verified else None
    entry["verified_on"] = date.today().isoformat() if verified else None
    entry.pop("confirmed_in", None)


def confirm(pkg, targets, reviewer):
    """Apply the reviewer's ticks. Each target names a value (item, key), a document (file) or a match (file, item).
    A target with from was confirmed first on the same file in another package (MAF-36b): the reading keeps where."""
    docs = {d["file"]: d for d in pkg["documents"]}
    items = {i["id"]: i for i in pkg["items"]}
    for t in targets:
        if t["kind"] == "value":
            entry = items[t["item"]]["values"][t["key"]]
        elif t["kind"] == "document":
            entry = docs[t["file"]]
        elif t["kind"] == "match":
            entry = next(m for m in docs[t["file"]].get("matches", []) if m["item"] == t["item"])
        else:
            raise ValueError(f"unknown kind {t['kind']!r}")
        set_verified(entry, bool(t["verified"]), reviewer)
        if t.get("from") and entry["status"] == "verified":
            entry["confirmed_in"] = str(t["from"])[:200]


def decide(pkg, finding_id, status, note, reviewer):
    """Save the reviewer's decision on an AI suggestion: accepted, rejected, or back to suggested."""
    if status not in DECISIONS:
        raise ValueError(f"unknown decision {status!r}")
    finding = next(f for f in pkg["ai_findings"] if f["id"] == finding_id)
    finding["status"] = status
    finding["decided_by"] = None if status == "suggested" else reviewer
    finding["note"] = note or None


FINDINGS = ("kept", "dismissed")   # a finding kept in the answer, or marked not a problem with a reason


def decide_findings(decisions, changes, reviewer):
    """Apply the reviewer's decisions, by result key: {"decision": "kept"}, {"decision": "dismissed", "reason": ...},
    or None to open the finding again. Each decision keeps who took it and when."""
    if not isinstance(changes, dict):
        raise ValueError("decisions map a finding's key to the decision")
    for key, change in changes.items():
        if change is None:
            decisions.pop(key, None)
        elif isinstance(change, dict) and change.get("decision") in FINDINGS:
            reason = " ".join(str(change.get("reason") or "").split())[:500] or None
            decisions[key] = {"decision": change["decision"], "reason": reason, "decided_by": reviewer,
                              "decided_on": date.today().isoformat()}
        else:
            raise ValueError(f"unknown decision {change!r}")
