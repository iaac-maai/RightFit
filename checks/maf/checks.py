"""Deterministic MAF checks (spec/features/maf_checker.md, section 6). No AI here.

Each check returns result dicts:
  check     D1, D2, D3, D4, V1, V2, E1, C or R
  item/doc  what the result is about
  result    pass, flag, unclear or info (what the reviewer sees)
  would_be  the verdict on the values as they are, before anyone verified them
  reason    plain-language reason; rules: the rule or checklist ids behind it
  code, params   used by explain/ to write the draft comment
  blocking  True when a flag here makes the draft status C
"""
import re
from datetime import date

from checks.maf.rules import CHAINS, active_ids, documents_for, for_family, rules_for, tables

DECL = "eu_declaration_of_conformity"
MAF_STAGES = ("maf", "maf_and_delivery")
DOC_LABELS = {
    "data_sheet": "data sheet",
    DECL: "EU declaration of conformity",
    "declaration_of_performance": "declaration of performance",
    "product_certificate": "product certificate",
    "other_certificate": "other certificate",
    "selection_report": "selection report",
    "declaration_quality_certificate_guarantee": "declaration of performance or conformity, quality certificate "
                                                 "and guarantee",
    "reception_documents": "reception documents (supply documents, guarantee, conformity and CE marking)",
    "manufacturer_guarantee_and_conformity": "manufacturer's guarantee and conformity documents",
}


def context(location, review_date, delivery_date, requirements=None, data=None):
    """Everything a check needs besides the package. data = (rules, family_docs, checklist) for tests."""
    rules, family_docs, checklist = data or tables()
    return {"location": location, "review_date": review_date, "delivery_date": delivery_date,
            "requirements": requirements or {}, "rules": rules, "family_docs": family_docs,
            "checklist": checklist}


def result(check, verdict, reason, inputs=(), item=None, doc=None, rules=(), code=None, params=None,
           blocking=False):
    r = {"check": check, "item": item, "doc": doc, "result": verdict, "would_be": verdict, "reason": reason,
         "rules": list(rules), "code": code, "params": params or {}, "blocking": blocking}
    # AGENTS.md rule 3: pass or flag only on verified inputs; otherwise unclear until someone verifies.
    if verdict in ("pass", "flag") and any(i.get("status") != "verified" for i in inputs):
        r["result"] = "unclear"
    return r


# ---------------------------------------------------------------- helpers

def norm(text):
    return re.sub(r"[^A-Z0-9]", "", str(text).upper())


def covers(doc, item):
    """True when a document names the item: one of its covers sits inside the item's model or range."""
    names = [norm(item["model"])] + ([norm(item["range"])] if item.get("range") else [])
    return any(c and any(c in n for n in names) for c in map(norm, doc.get("covers", [])))


def val(item, key):
    return item["values"].get(key) or {"value": None, "unit": None, "status": "unclear", "note": "not recorded"}


def has(v):
    return v["value"] not in (None, "")


def fmt(v):
    text = f"{v['value']} {v['unit'] or ''}".strip()
    return f"{text} ({v['source']}, p. {v['page']})" if v.get("source") else text


def label(doc_type):
    return DOC_LABELS.get(doc_type, doc_type.replace("_", " "))


# ---------------------------------------------------------------- D: documents

def d1_required_documents(pkg, ctx):
    """Every document the family needs at MAF stage is present and names the item."""
    out = []
    for item in pkg["items"]:
        for row in documents_for(ctx["family_docs"], ctx["location"], item["family"], MAF_STAGES):
            ids = active_ids(row["rule_id"], ctx["rules"], ctx["review_date"])
            if not ids:
                continue
            found = [d for d in pkg["documents"] if d["doc_type"] == row["document"] and covers(d, item)]
            # A missing data sheet sends the MAF back (C); a missing declaration is a note (B), as in the register.
            blocking = row["document"] == "data_sheet"
            if found:
                out.append(result("D1", "pass", f"{label(row['document'])}: {', '.join(d['file'] for d in found)}",
                                  found, item=item["id"], rules=ids, blocking=blocking))
            else:
                out.append(result("D1", "flag", f"no {label(row['document'])} names {item['model']}",
                                  pkg["documents"], item=item["id"], rules=ids, code="D1.missing",
                                  params={"item": item["model"], "doc_type": row["document"]}, blocking=blocking))
    return out


def d2_declarations_match(pkg, ctx):
    """Each declaration names at least one submitted item; name the items left without one."""
    need = [i for i in pkg["items"] if any(r["document"] == DECL for r in
                                           documents_for(ctx["family_docs"], ctx["location"], i["family"], MAF_STAGES))]
    decls = [d for d in pkg["documents"] if d["doc_type"] == DECL]
    without = [i["model"] for i in need if not any(covers(d, i) for d in decls)]
    ids = active_ids("EU-MACH-DOC;EU-MACH-REG;EU-LVD-DOC", ctx["rules"], ctx["review_date"])
    out = []
    for d in decls:
        named = [i["model"] for i in pkg["items"] if covers(d, i)]
        if named:
            out.append(result("D2", "pass", f"{d['file']} names {', '.join(named)}", [d], doc=d["file"], rules=ids))
            continue
        reason = f"{d['file']} names {', '.join(d['covers'])}, none of the submitted items"
        if without:
            reason += f"; items without a declaration: {', '.join(without)}"
        out.append(result("D2", "flag", reason, [d], doc=d["file"], rules=ids,
                          code="D2.no_match" if without else "D2.extra",
                          params={"covers": ", ".join(d["covers"]), "items": ", ".join(without)}))
    return out


DATED_TYPES = {DECL, "declaration_of_performance", "product_certificate", "other_certificate"}


def d3_in_date(pkg, ctx):
    """Certificates are valid on the review date and at delivery."""
    review, delivery = ctx["review_date"], ctx["delivery_date"]
    out = []
    for d in pkg["documents"]:
        if not d["valid_until"]:
            if d["doc_type"] in DATED_TYPES:
                out.append(result("D3", "info", f"{d['file']}: no expiry date printed", doc=d["file"], rules=["CL-02"]))
            continue
        until = date.fromisoformat(d["valid_until"])
        params = {"file": d["file"], "doc_type": d["doc_type"], "date": until.strftime("%d.%m.%Y")}
        if until < review:
            out.append(result("D3", "flag", f"{d['file']} expired on {until}, before the review date {review}",
                              [d], doc=d["file"], rules=["CL-02"], code="D3.expired", params=params))
        elif until < delivery:
            out.append(result("D3", "flag", f"{d['file']} is valid until {until}, before the delivery date "
                                            f"{delivery}: renew before delivery",
                              [d], doc=d["file"], rules=["CL-02"], code="D3.renew", params=params))
        else:
            out.append(result("D3", "pass", f"{d['file']} is valid until {until}", [d], doc=d["file"], rules=["CL-02"]))
    return out


# Words in the form's attachment labels and the document type they announce.
LABEL_TYPES = ((" ft ", "data_sheet"), ("fisa tehnica", "data_sheet"), ("declara", DECL),
               ("raport", "selection_report"), ("certificat", "product_certificate"),
               ("tuv", "product_certificate"), ("eurovent", "product_certificate"))


def expected_type(attachment_label):
    text = f" {attachment_label.lower()} "
    return next((t for word, t in LABEL_TYPES if word in text), None)


def d4_documents_as_listed(pkg, ctx):
    """Each listed attachment exists and is the kind of document its label says."""
    out = []
    for a in pkg["form"]["attachments_listed"]:
        docs = [d for d in pkg["documents"] if d["listed_as"] == a["label"]]
        if not docs:
            out.append(result("D4", "flag", f"'{a['label']}' is listed in the form but not in the package",
                              pkg["documents"], code="D4.not_found", params={"label": a["label"]}))
        expected = expected_type(a["label"])
        for d in docs:
            if expected is None:
                out.append(result("D4", "unclear", f"label '{a['label']}' not recognised; check {d['file']} by hand",
                                  doc=d["file"]))
            elif d["doc_type"] == expected:
                out.append(result("D4", "pass", f"{d['file']}: {label(d['doc_type'])}, as listed", [d],
                                  doc=d["file"]))
            else:
                out.append(result("D4", "flag", f"'{a['label']}' announces a {label(expected)}; {d['file']} "
                                                f"is in fact: {label(d['doc_type'])}", [d], doc=d["file"], code="D4.type",
                                  params={"label": a["label"], "file": d["file"], "doc_type": d["doc_type"]}))
    for d in pkg["documents"]:
        if not d["listed_as"]:
            out.append(result("D4", "info", f"{d['file']} is in the package but not listed in the form", doc=d["file"]))
    return out


# ---------------------------------------------------------------- V and E: values

# (what the form asks, what the data sheet gives)
DUTY_PAIRS = (("duty_flow", "flow"), ("duty_head", "head"),
              ("duty_airflow_supply", "airflow_supply"), ("duty_airflow_extract", "airflow_extract"))
TO_BASE = {"m3/h": 1.0, "l/s": 3.6, "m": 1.0}  # flows to m3/h, heads in m


def tolerance(ctx):
    """ENG-DUTY-TOL in %, as a fraction. Empty until Luca sets it, so the comparison is exact."""
    rule = ctx["rules"].get("ENG-DUTY-TOL")
    return float(rule["value"]) / 100 if rule and rule["value"] else 0.0


def v1_duty_point(pkg, ctx):
    """The data sheet's duty point meets the form's duty."""
    tol, out = tolerance(ctx), []
    for item in pkg["items"]:
        ok, short, missing, inputs = [], [], [], []
        for need_key, got_key in DUTY_PAIRS:
            need, got = val(item, need_key), val(item, got_key)
            if not has(need):
                continue
            inputs += [need, got]
            if not has(got) or got["unit"] not in TO_BASE or need["unit"] not in TO_BASE:
                missing.append(got_key)
                continue
            text = f"{got_key} {fmt(got)} for {fmt(need)}"
            enough = got["value"] * TO_BASE[got["unit"]] >= need["value"] * TO_BASE[need["unit"]] * (1 - tol)
            (ok if enough else short).append(text)
        if not inputs:
            continue
        params = {"item": item["model"], "got": "; ".join(short), "req": ""}
        if missing:
            out.append(result("V1", "unclear", f"not found in the data sheet: {', '.join(missing)}", item=item["id"],
                              rules=["ENG-DUTY-TOL"], code="V1.missing", params=params))
        elif short:
            out.append(result("V1", "flag", f"below the form's duty: {'; '.join(short)}", inputs, item=item["id"],
                              rules=["ENG-DUTY-TOL"], code="V1.below", params=params))
        else:
            out.append(result("V1", "pass", f"meets the form's duty: {'; '.join(ok)}", inputs, item=item["id"],
                              rules=["ENG-DUTY-TOL"]))
    return out


def v2_pressure(pkg, ctx):
    """Maximum working pressure at least the required pressure (bar), when a requirement is given."""
    need, out = ctx["requirements"].get("pressure_bar"), []
    for item in pkg["items"]:
        if item["family"] != "pump":
            continue
        pn = val(item, "max_pressure")
        params = {"item": item["model"], "got": fmt(pn), "req": f"{need} bar"}
        if need is None:
            seen = fmt(pn) if has(pn) else "not found"
            out.append(result("V2", "info", f"no requirement given; data sheet: {seen}", item=item["id"],
                              rules=["CL-05"]))
        elif not has(pn):
            out.append(result("V2", "unclear", f"maximum working pressure not found ({pn['note']})", item=item["id"],
                              rules=["CL-05"], code="V2.missing", params=params))
        else:
            verdict = "pass" if pn["value"] >= need else "flag"
            out.append(result("V2", verdict, f"{fmt(pn)} for {need} bar required", [pn], item=item["id"],
                              rules=["CL-05"], code="V2.below", params=params))
    return out


def no_rule(check, item, what):
    return result(check, "unclear", f"no rule for this location ({what})", item=item["id"])


def missing_value(check, item, what, v):
    return result(check, "unclear", f"{what} not found ({v.get('note') or 'no note'})", item=item["id"],
                  code=f"{check}.missing", params={"item": item["model"], "what": what})


def e1_ecodesign(pkg, ctx):
    """Ecodesign of ventilation units, Regulation (EU) 1253/2014: heat recovery, SFPint, filter warning."""
    out = []
    for item in pkg["items"]:
        if item["family"] != "ahu":
            continue

        def rules(topic):
            return rules_for(ctx["rules"], ctx["location"], "ahu", topic, ctx["review_date"])

        kind, eff = val(item, "hrs_type"), val(item, "hrs_efficiency")
        run_around = has(kind) and "run around" in str(kind["value"]).lower()
        # Run around coils have their own, lower limit (rule ids ending in -RAC).
        hrs = [r for r in rules("ahu.hrs_efficiency") if r["rule_id"].endswith("-RAC") == run_around]
        if not hrs:
            out.append(no_rule("E1", item, "heat recovery"))
        elif not has(eff):
            out.append(missing_value("E1", item, "heat recovery efficiency", eff))
        else:
            limit = max(float(r["value"]) for r in hrs)  # the strictest value wins
            out.append(result("E1", "pass" if eff["value"] >= limit else "flag",
                              f"heat recovery {fmt(eff)}, at least {limit:g} % required", [eff, kind],
                              item=item["id"], rules=[r["rule_id"] for r in hrs], code="E1.hrs",
                              params={"item": item["model"], "got": eff["value"], "req": f"{limit:g}"}))

        sfp, limit = val(item, "sfp_int"), val(item, "sfp_int_limit")
        sfp_rules = rules("ahu.sfp_int")
        if not sfp_rules:
            out.append(no_rule("E1", item, "SFPint"))
        elif not (has(sfp) and has(limit)):
            out.append(missing_value("E1", item, "SFPint and SFPint_limit", sfp if not has(sfp) else limit))
        else:
            out.append(result("E1", "pass" if sfp["value"] <= limit["value"] else "flag",
                              f"SFPint {fmt(sfp)}, limit {fmt(limit)}", [sfp, limit], item=item["id"],
                              rules=[r["rule_id"] for r in sfp_rules], code="E1.sfp",
                              params={"item": item["model"], "got": sfp["value"], "req": limit["value"]}))

        warning, fw_rules = val(item, "filter_warning"), rules("ahu.filter_warning")
        if not fw_rules:
            out.append(no_rule("E1", item, "filter warning"))
        elif not has(warning):
            out.append(missing_value("E1", item, "filter warning", warning))
        else:
            out.append(result("E1", "pass" if warning["value"] is True else "flag",
                              f"filter warning: {fmt(warning)}", [warning], item=item["id"],
                              rules=[r["rule_id"] for r in fw_rules], code="E1.filter",
                              params={"item": item["model"]}))
    return out


# ---------------------------------------------------------------- C: checklist

def _cl01(item, pkg, ctx):
    sheets = [d for d in pkg["documents"] if d["doc_type"] == "data_sheet" and covers(d, item)]
    if sheets:
        return "pass", f"named in {sheets[0]['file']}", sheets, {}
    return "missing", "no data sheet names the model", pkg["documents"], {}


def _cl03(item, pkg, ctx):
    used = val(item, "used_for")
    return ("pass", used["value"], [used], {}) if has(used) else ("missing", "not filled in the form", [used], {})


def _cl04(item, pkg, ctx):
    if not ctx["requirements"].get("boq"):
        return "unclear", "no BOQ line given", [], {}
    return "unclear", "BOQ comparison not built yet; check by hand", [], {}


def _cl08(item, pkg, ctx):
    included, protocol = val(item, "bms_included"), val(item, "bms_protocol")
    if included["value"] is True:
        return "pass", f"included: {fmt(protocol)}", [included], {}
    seen = f"{protocol['value']}; " if has(protocol) else ""
    return "missing", f"{seen}not stated as included ({included.get('note') or 'no note'})", [included], {}


# What each pump application needs, from Luca on 28 Oct 2026 (rules.csv ENG-PUMP-PANEL).
PANEL_NEED = {"circulation": "panel", "stormwater": "panel", "booster": "recommended", "drainage": "float"}


def _cl09(item, pkg, ctx):
    application, panel = val(item, "application"), val(item, "controller_included")
    need = PANEL_NEED.get(application["value"])
    if need is None:
        return "unclear", f"application '{application['value']}' has no panel rule in ENG-PUMP-PANEL", [], {}
    if panel["value"] is True:
        return "pass", f"controller included: {fmt(panel)}", [application, panel], {}
    if need == "recommended":
        return "info", "booster set: a control panel is recommended, none stated", [], {}
    if need == "float":
        switch = val(item, "float_switch")
        if switch["value"] is True:
            return "pass", f"float switch: {fmt(switch)}", [application, switch], {}
        return "missing", "drainage pump: no float switch or panel stated", [application, panel, switch], \
            {"variant": ".float"}
    return "missing", f"{application['value']} pumps need a control panel; none stated", [application, panel], {}


def _cl12(item, pkg, ctx):
    keys = ("voltage", "power", "starting_method")
    gaps = [k for k in keys if not has(val(item, k))]
    inputs = [val(item, k) for k in keys]
    if gaps:
        return "missing", f"not stated: {', '.join(gaps)}", inputs, {"missing": ", ".join(gaps)}
    return "pass", "; ".join(f"{k} {fmt(val(item, k))}" for k in keys), inputs, {}


CHECKLIST = {"CL-01": _cl01, "CL-02": lambda *a: ("info", "see D3", [], {}), "CL-03": _cl03, "CL-04": _cl04,
             "CL-08": _cl08, "CL-09": _cl09, "CL-11": lambda *a: ("info", "see R", [], {}), "CL-12": _cl12}


def c_checklist(pkg, ctx):
    """Every checklist row for the item's family, with the register rows behind it as the reason."""
    out = []
    for item in pkg["items"]:
        for row in ctx["checklist"]:
            if not for_family(row["family"], item["family"]):
                continue
            check = CHECKLIST.get(row["id"], lambda *a: ("unclear", "no automatic check yet; check by hand", [], {}))
            verdict, reason, inputs, params = check(item, pkg, ctx)
            if verdict == "missing":
                verdict = row["if_missing"].lower()
            code = f"C.{row['id']}{params.pop('variant', '')}"
            out.append(result("C", verdict, f"{row['id']} {row['item']}: {reason} (register {row['source_rows']})",
                              inputs, item=item["id"], rules=[row["id"]], code=code,
                              params={"item": item["model"], **params}, blocking=row["blocking"] == "yes"))
    return out


# ---------------------------------------------------------------- R: location reminders

def r_reminders(pkg, ctx):
    """Documents the location asks for at delivery, shown as info at MAF stage."""
    out = []
    for row in ctx["family_docs"]:
        if row["when"] != "delivery" or row["jurisdiction"] not in CHAINS[ctx["location"]]:
            continue
        models = [i["model"] for i in pkg["items"] if for_family(row["family"], i["family"])]
        if models:
            out.append(result("R", "info", f"at delivery: {label(row['document'])} for {', '.join(models)}",
                              rules=active_ids(row["rule_id"], ctx["rules"], ctx["review_date"])))
    return out


CHECKS = (d1_required_documents, d2_declarations_match, d3_in_date, d4_documents_as_listed, v1_duty_point,
          v2_pressure, e1_ecodesign, c_checklist, r_reminders)


def run_all(pkg, ctx):
    results = [r for check in CHECKS for r in check(pkg, ctx)]
    for r in results:
        # The status of each rule travels with the verdict (verified_secondary, to_confirm, practice...).
        r["rule_status"] = {i: ctx["rules"][i]["status"] for i in r["rules"] if i in ctx["rules"]}
    return results
