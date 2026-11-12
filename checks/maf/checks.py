"""Deterministic MAF checks (spec/features/maf_checker.md, section 6). No AI here.

Each check returns result dicts:
  check     D1, D2, D3, D4, V1, V2, V3, E1, H1, C, P, Q or R
  item/doc  what the result is about
  result    pass, flag, unclear or info (what the reviewer sees)
  would_be  the verdict on the values as they are, before anyone verified them
  reason    plain-language reason; rules: the rule or checklist ids behind it
  code, params   used by explain/ to write the draft comment
  blocking  True when a flag here makes the draft status C
"""
import re
from datetime import date

from checks.maf.rules import CHAINS, active_ids, documents_for, for_family, library, load, rules_for, tables

DECL = "eu_declaration_of_conformity"
MAF_STAGES = ("maf", "maf_and_delivery")
DOC_LABELS = {
    "data_sheet": "data sheet",
    DECL: "EU declaration of conformity",
    "declaration_of_performance": "declaration of performance",
    "product_certificate": "product certificate",
    "other_certificate": "other certificate",
    "selection_report": "selection report",
    "drinking_water_approval": "approval for contact with drinking water",
    "declaration_quality_certificate_guarantee": "declaration of performance or conformity, quality certificate "
                                                 "and guarantee",
    "reception_documents": "reception documents (supply documents, guarantee, conformity and CE marking)",
    "manufacturer_guarantee_and_conformity": "manufacturer's guarantee and conformity documents",
}


def context(location, review_date, delivery_date, requirements=None, data=None, lib=None, consultant=None):
    """Everything a check needs besides the package. data = (rules, family_docs, checklist), lib and consultant
    (the consultant's rules) for tests."""
    rules, family_docs, checklist = data or tables()
    return {"location": location, "review_date": review_date, "delivery_date": delivery_date,
            "requirements": requirements or {}, "rules": rules, "family_docs": family_docs,
            "checklist": checklist, "library": lib if lib is not None else library(),
            "consultant": consultant if consultant is not None else load("consultant_rules.csv")}


def result(check, verdict, reason, inputs=(), item=None, doc=None, rules=(), code=None, params=None,
           blocking=False):
    r = {"check": check, "item": item, "doc": doc, "result": verdict, "would_be": verdict, "reason": reason,
         "rules": list(rules), "code": code, "params": params or {}, "blocking": blocking,
         # Where the reviewer can look: pages of the values used, or the documents when there are only a few.
         "sources": sorted({f"{i['source']}, p. {i['page']}" for i in inputs if i.get("source")}
                           | ({i["file"] for i in inputs if "file" in i} if len(inputs) <= 3 else set()))}
    # AGENTS.md rule 3: pass or flag only on verified inputs; otherwise unclear until someone verifies.
    if verdict in ("pass", "flag") and any(i.get("status") != "verified" for i in inputs):
        r["result"] = "unclear"
    return r


# ---------------------------------------------------------------- helpers

def norm(text):
    return re.sub(r"[^A-Z0-9]", "", str(text).upper())


# How a document can cover a product (ingest/prompts/matching.md). "related" is not covering.
COVERING = ("exact model", "range table row", "range")
MARKED = ("exact model", "range table row")


def matches(doc, item):
    """How the document covers the item, as the AI matched it and the reviewer confirms it.

    Documents the AI hasn't matched yet (library entries, new packages) fall back to comparing text:
    one of the document's covers sits inside the item's model or range.
    """
    if "matches" in doc:
        return [m for m in doc["matches"] if m["item"] == item["id"] and m["kind"] in COVERING]
    names = [norm(item["model"])] + ([norm(item["range"])] if item.get("range") else [])
    if any(c and any(c in n for n in names) for c in map(norm, doc.get("covers", []))):
        return [{"item": item["id"], "kind": "exact model", "status": doc.get("status", "extracted")}]
    return []


def covers(doc, item):
    return bool(matches(doc, item))


def with_matches(docs, item):
    """The documents plus their matches for the item: both must be confirmed before a check passes."""
    return docs + [m for d in docs for m in matches(d, item)]


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
        rows = documents_for(ctx["family_docs"], ctx["location"], item["family"], MAF_STAGES)
        if not rows:
            # A family the table does not list yet: say so, rather than let the item through unchecked.
            out.append(result("D1", "unclear", f"no documents are listed yet for the family {item['family']}; "
                              "check its documents by hand", item=item["id"]))
        for row in rows:
            ids = active_ids(row["rule_id"], ctx["rules"], ctx["review_date"])
            if not ids:
                continue
            found = [d for d in pkg["documents"] if d["doc_type"] == row["document"] and covers(d, item)]
            # A missing data sheet sends the MAF back (C); a missing declaration is a note (B), as in the register.
            blocking = row["document"] == "data_sheet"
            if found:
                out.append(result("D1", "pass", f"{label(row['document'])}: {', '.join(d['file'] for d in found)}",
                                  with_matches(found, item), item=item["id"], rules=ids, blocking=blocking))
            else:
                out.append(missing_document(pkg, ctx, item, row["document"], ids, blocking))
    return out


def same_brand(entry, item):
    return norm(entry["brand"]) == norm(item["brand"])


def missing_document(pkg, ctx, item, doc_type, ids, blocking):
    """A required document is not in the package. Say whether the manufacturer publishes it (MAF-11)."""
    reason = f"no {label(doc_type)} names {item['model']}"
    params = {"item": item["model"], "doc_type": doc_type}
    published = [e for e in ctx["library"]["documents"]
                 if e["doc_type"] == doc_type and same_brand(e, item) and covers(e, item)]
    searched = [e for e in ctx["library"]["not_found"]
                if e["doc_type"] == doc_type and same_brand(e, item) and covers(e, item)]
    if published:
        e = published[0]
        reason += f"; the manufacturer publishes one, left out of the package: {e['title']}, p. {e['page']} ({e['url']})"
        if e.get("notes"):
            reason += f". Note: {e['notes']}"
        return result("D1", "flag", reason, pkg["documents"] + published, item=item["id"], rules=ids,
                      code="D1.published", params={**params, "where": e["title"], "url": e["url"]},
                      blocking=blocking)
    if searched:
        reason += f"; not found on the manufacturer's site either (searched {searched[0]['searched_on']})"
    return result("D1", "flag", reason, pkg["documents"], item=item["id"], rules=ids, code="D1.missing",
                  params=params, blocking=blocking)


def d2_declarations_match(pkg, ctx):
    """Each declaration names at least one submitted item; name the items left without one."""
    need = [i for i in pkg["items"] if any(r["document"] == DECL for r in
                                           documents_for(ctx["family_docs"], ctx["location"], i["family"], MAF_STAGES))]
    decls = [d for d in pkg["documents"] if d["doc_type"] == DECL]
    without = [i["model"] for i in need if not any(covers(d, i) for d in decls)]
    ids = active_ids("EU-MACH-DOC;EU-MACH-REG;EU-LVD-DOC", ctx["rules"], ctx["review_date"])
    out = []
    for d in decls:
        named = [i for i in pkg["items"] if covers(d, i)]
        if named:
            inputs = [d] + [m for i in named for m in matches(d, i)]
            out.append(result("D2", "pass", f"{d['file']} names {', '.join(i['model'] for i in named)}", inputs,
                              doc=d["file"], rules=ids))
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
LABEL_TYPES = (("aviz sanitar", "drinking_water_approval"), (" ft ", "data_sheet"), ("fisa tehnica", "data_sheet"), ("declara", DECL),
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


# "5 .. 60" or "-10 .. +120", as the data sheets print the range.
TEMP_RANGE = re.compile(r"([-+]?\d+(?:[.,]\d+)?)\s*\.\.\s*([-+]?\d+(?:[.,]\d+)?)")


def temp_range(v):
    """(low, high) in °C from a reading like '5 .. 60', or None when it can't be read."""
    m = TEMP_RANGE.search(str(v["value"])) if has(v) and v["unit"] == "°C" else None
    return tuple(float(x.replace(",", ".")) for x in m.groups()) if m else None


# Pumps that move domestic hot water (Luca, 12 Nov 2026): the recirculation pump, and the pump between the hot water
# store and its heat exchanger. They carry drinking water, and the law sets the temperature they must take.
DHW = ("dhw_circulation", "dhw_charging")


def v3_liquid_temperature(pkg, ctx):
    """The pump's liquid temperature range covers the project's range for its application; for hot water pumps
    with no project range, at least the temperature the location's hot water rules ask for."""
    needs, out = ctx["requirements"].get("liquid_temp_c", {}), []
    for item in pkg["items"]:
        if item["family"] != "pump":
            continue
        got, application = val(item, "liquid_temp_range"), val(item, "application")
        need, have = needs.get(application["value"]), temp_range(got)
        rules = ["ANY-PRACTICE-LIQUID-TEMP"]
        if need is None and application["value"] in DHW:
            law = rules_for(ctx["rules"], ctx["location"], item["family"], "value.dhw_temp", ctx["review_date"])
            if law:
                need, rules = (None, max(float(r["value"]) for r in law)), [r["rule_id"] for r in law]
        req = "" if need is None else (f"at least {need[1]:g} °C" if need[0] is None else f"{need[0]} .. {need[1]} °C")
        params = {"item": item["model"], "got": fmt(got), "req": req}
        if need is None:
            seen = fmt(got) if has(got) else "not found"
            out.append(result("V3", "info", f"no project temperature given; data sheet: {seen}", item=item["id"],
                              rules=rules))
        elif have is None:
            out.append(result("V3", "unclear", f"liquid temperature range not found ({got.get('note') or fmt(got)})",
                              item=item["id"], rules=rules, code="V3.missing", params=params))
        else:
            ok = (need[0] is None or have[0] <= need[0]) and have[1] >= need[1]
            out.append(result("V3", "pass" if ok else "flag", f"{fmt(got)} for {req} required", [got, application],
                              item=item["id"], rules=rules, code="V3.outside", params=params))
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
    marked = [(d, m) for d in sheets for m in matches(d, item) if m["kind"] in MARKED]
    if marked:
        d, m = marked[0]
        return "pass", f"{m['kind']} in {d['file']}", [d, m], {}
    if sheets:
        # The register returned a data sheet for a whole range with nothing marked (R01).
        return "missing", f"{sheets[0]['file']} covers only the range; the model is not marked", \
            with_matches(sheets, item), {}
    return "missing", "no data sheet names the model", pkg["documents"], {}


def _cl03(item, pkg, ctx):
    used = val(item, "used_for")
    return ("pass", used["value"], [used], {}) if has(used) else ("missing", "not filled in the form", [used], {})


def _cl04(item, pkg, ctx):
    if (pkg.get("boq") or {}).get(item["id"]):
        return "info", "what the BOQ line asks is checked under Q", [], {}
    if not ctx["requirements"].get("boq"):
        return "unclear", "no BOQ line given", [], {}
    return "unclear", "BOQ comparison not built yet; check by hand", [], {}


def _cl08(item, pkg, ctx):
    included, protocol = val(item, "bms_included"), val(item, "bms_protocol")
    if included["value"] is True:
        return "pass", f"included: {fmt(protocol)}", [included], {}
    seen = f"{protocol['value']}; " if has(protocol) else ""
    return "missing", f"{seen}not stated as included ({included.get('note') or 'no note'})", [included], {}


def _cl12(item, pkg, ctx):
    keys = ("voltage", "power", "starting_method")
    gaps = [k for k in keys if not has(val(item, k))]
    inputs = [val(item, k) for k in keys]
    if gaps:
        return "missing", f"not stated: {', '.join(gaps)}", inputs, {"missing": ", ".join(gaps)}
    return "pass", "; ".join(f"{k} {fmt(val(item, k))}" for k in keys), inputs, {}


CHECKLIST = {"CL-01": _cl01, "CL-02": lambda *a: ("info", "see D3", [], {}), "CL-03": _cl03, "CL-04": _cl04,
             "CL-08": _cl08, "CL-11": lambda *a: ("info", "see R", [], {}), "CL-12": _cl12}


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


# Pumps that need an approval for drinking water (Luca, 12 Nov 2026): booster sets and the hot water pumps.
# Heating and cooling circulation pumps do not.
DRINKING_WATER = ("booster",) + DHW


def h1_drinking_water(pkg, ctx):
    """A pump that carries drinking water has a document approving it for contact with drinking water."""
    out = []
    for item in pkg["items"]:
        application = val(item, "application")
        if application["value"] not in DRINKING_WATER:
            continue
        ids = [r["rule_id"] for r in rules_for(ctx["rules"], ctx["location"], item["family"], "doc.drinking_water",
                                               ctx["review_date"])]
        if not ids:
            out.append(no_rule("H1", item, "approval for contact with drinking water"))
            continue
        # shortcut: one document type for the national approval and the EU declaration; split it when a package
        # holds an EU one (from 31 Dec 2026), so the transition of Regulation (EU) 2024/370 art. 11 can be checked.
        found = [d for d in pkg["documents"] if d["doc_type"] == "drinking_water_approval" and covers(d, item)]
        if found:
            out.append(result("H1", "pass", f"approved for drinking water: {', '.join(d['file'] for d in found)}",
                              with_matches(found, item) + [application], item=item["id"], rules=ids))
        else:
            out.append(result("H1", "flag", f"no approval for contact with drinking water names {item['model']} "
                              f"(it is used as a {application['value']})", [application], item=item["id"], rules=ids,
                              code="H1.missing", params={"item": item["model"]}))
    return out


# ---------------------------------------------------------------- P: the consultant's rules

OPERATORS = {">=": lambda a, b: a >= b, "<=": lambda a, b: a <= b}


def _brand(item, pkg, rule):
    allowed = [norm(b) for b in rule["value"].split(";") if b.strip()]
    ok = any(a in norm(item["brand"]) for a in allowed)
    return ("pass" if ok else "missing"), f"brand {item['brand']}; accepted: {rule['value'].replace(';', ', ')}", []


def _value(item, pkg, rule):
    v = val(item, rule["field"])
    number = isinstance(v["value"], (int, float)) and not isinstance(v["value"], bool)
    if not has(v) or (v["unit"] or "") != rule["unit"] or (rule["operator"] != "=" and not number):
        return "unclear", f"{rule['field'].replace('_', ' ')}: {fmt(v) if has(v) else 'not found'}", []
    # "=" compares text too (a class such as IE3); ">=" and "<=" compare numbers in the rule's unit.
    ok = (norm(v["value"]) == norm(rule["value"]) if rule["operator"] == "=" else
          OPERATORS[rule["operator"]](v["value"], float(rule["value"])))
    return ("pass" if ok else "missing"), f"{fmt(v)}; asked: {rule['operator']} {rule['value']} {rule['unit']}".rstrip(), [v]


def _document(item, pkg, rule):
    found = [d for d in pkg["documents"] if d["doc_type"] == rule["field"] and covers(d, item)]
    if found:
        return "pass", f"{label(rule['field'])}: {', '.join(d['file'] for d in found)}", with_matches(found, item)
    return "missing", f"no {label(rule['field'])} names {item['model']}", pkg["documents"]


def _included(item, pkg, rule):
    if not any(k in item["values"] for k in rule["field"].split("|")):   # a reading the reader never records
        return "unclear", f"no reading of {rule['field'].replace('|', ' or ').replace('_', ' ')}; check by hand", []
    readings = [val(item, k) for k in rule["field"].split("|")]
    yes = [r for r in readings if r["value"] is True]
    if yes:
        return "pass", f"included: {fmt(yes[0])}", yes
    return "missing", "not stated as included", readings


KINDS = {"brand": _brand, "value": _value, "document": _document, "included": _included,
         "reminder": lambda item, pkg, rule: ("info", "check by hand", [])}


def p_consultant_rules(pkg, ctx):
    """The consultant's own rules (data/maf/consultant_rules.csv): preferences on top of the law, never the law."""
    out = []
    for item in pkg["items"]:
        for rule in ctx["consultant"]:
            if rule["active"] != "yes" or not for_family(rule["family"], item["family"]):
                continue
            application = val(item, "application")
            if rule["application"] and application["value"] not in rule["application"].split(";"):
                continue
            verdict, reason, inputs = KINDS[rule["kind"]](item, pkg, rule)
            if verdict == "missing":
                verdict = "info" if rule["effect"] == "info" else "flag"
            inputs += [application] if rule["application"] else []
            out.append(result("P", verdict, f"the consultant asks: {rule['text']}; {reason}", inputs, item=item["id"],
                              rules=[rule["rule_id"]], code="P.rule", params={"item": item["model"], "text": rule["text"]},
                              blocking=rule["effect"] == "C"))
    return out


# ---------------------------------------------------------------- Q: the BOQ line

# Values a BOQ gives as the designer's estimate, not a limit (Luca, 12 Nov 2026: the motor power).
ESTIMATES = ("power",)


def q_boq_lines(pkg, ctx):
    """What the item's BOQ line asks for, each checked like a consultant's rule. The server puts the line in
    pkg["boq"] (ingest/boq.py finds it, an AI lists what it asks); with no BOQ there is nothing to say."""
    links, out = pkg.get("boq"), []
    if links is None:
        return out
    for item in pkg["items"]:
        link = links.get(item["id"])
        if not link:
            out.append(result("Q", "unclear", "no line of the BOQ has this product's duty under the form's BOQ code",
                              item=item["id"], code="Q.none", params={"item": item["model"]}))
            continue
        where = f"BOQ {link['sheet']}, row {link['row']}"
        if link.get("requirements") is None:
            out.append(result("Q", "unclear", f"{where}: what the line asks has not been read yet", item=item["id"],
                              code="Q.unread", params={"item": item["model"], "where": where}))
            continue
        for ask in link["requirements"]:
            # What the AI read in the BOQ line is an input like any reading: unconfirmed until the reviewer looks.
            line = {"value": ask["quote"], "status": link.get("status", "extracted"), "source": link["file"], "page": where}
            verdict, reason, inputs = KINDS[ask["kind"]](item, pkg, ask)
            if verdict == "missing":
                verdict = "flag"
            if ask["kind"] == "value" and ask["field"] in ESTIMATES:
                verdict, reason = "info", f"the designer's estimate, not a limit; {reason}"
            out.append(result("Q", verdict, f"{where} asks: {ask['text']} (\"{ask['quote']}\"); {reason}",
                              inputs + [line], item=item["id"], code="Q.rule",
                              params={"item": item["model"], "text": ask["text"], "where": where}))
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
          v2_pressure, v3_liquid_temperature, e1_ecodesign, h1_drinking_water, c_checklist, p_consultant_rules,
          q_boq_lines, r_reminders)


def run_all(pkg, ctx):
    results = [r for check in CHECKS for r in check(pkg, ctx)]
    for r in results:
        # The status of each rule travels with the verdict (verified_secondary, to_confirm, practice...).
        r["rule_status"] = {i: ctx["rules"][i]["status"] for i in r["rules"] if i in ctx["rules"]}
        r["rule_status"].update({i: "consultant" for i in r["rules"] if r["check"] == "P"})
    return results
