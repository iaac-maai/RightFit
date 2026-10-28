"""RightFit MAF checker: a draft review of a material approval form. The reviewer decides.

Run from the repository root:  streamlit run app/maf_app.py
"""
import json
import sys
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from checks.maf.checks import context, run_all  # noqa: E402
from checks.maf.status import LABELS, draft_status  # noqa: E402
from explain.maf_comments import comment  # noqa: E402

EXTRACTED = ROOT / "data/maf/extracted"
# shortcut: one reviewer name for every verification; add a login when more reviewers use the app.
REVIEWER = "Luca"
GROUPS = {"D": "Documents", "V": "Values", "E": "Ecodesign", "C": "Checklist", "R": "Location reminders"}

st.set_page_config(page_title="RightFit · MAF checker", layout="wide")


def save(pkg):
    (EXTRACTED / f"{pkg['package']}.json").write_text(json.dumps(pkg, ensure_ascii=False, indent=2) + "\n")


def set_verified(entry, verified):
    """Mark a value or document verified by the reviewer, or put it back to what the reader left."""
    if verified == (entry["status"] == "verified"):
        return
    has_value = entry.get("value") not in (None, "") if "value" in entry else True
    entry["status"] = "verified" if verified else ("extracted" if has_value else "unclear")
    entry["checked_by"] = REVIEWER if verified else None
    entry["verified_on"] = date.today().isoformat() if verified else None


def key(r):
    return "|".join(str(x) for x in (r["check"], r["item"], r["doc"], ",".join(r["rules"]), r["code"]))


# ---------------------------------------------------------------- settings
names = sorted(p.stem for p in EXTRACTED.glob("*.json"))
pkg = json.loads((EXTRACTED / f"{st.sidebar.selectbox('Package', names)}.json").read_text())
form = pkg["form"]
location = st.sidebar.radio("Location", ["RO", "ES"], horizontal=True)
form_date = date.fromisoformat(form["date"])
review = st.sidebar.date_input("Review date", form_date)
delivery = st.sidebar.date_input("Delivery date", form_date + timedelta(weeks=form["delivery_weeks"] or 0),
                                 help=f"Form: {form['delivery_raw']}")
overrides = st.session_state.setdefault("overrides", {})

results = run_all(pkg, context(location, review, delivery))
item_names = {i["id"]: f"{i['id']} {i['model']}" for i in pkg["items"]}

# ---------------------------------------------------------------- header
st.title(f"MAF {form['form_no']} rev {form['revision']} · {', '.join(i['name'] for i in pkg['items'])}")
st.caption(f"Form date {form['date']} · sample sent: {form['sample_sent']} · signers (roles): "
           f"{', '.join(form['signers'])} · discipline, works group and BOQ line as written on the form: "
           f"{form['discipline']} / {form['works_group']} / {form['boq_ref']}")
status_box = st.container(border=True)

# ---------------------------------------------------------------- documents and values
st.subheader("Documents")
st.caption("Read by the AI reader (AI output). Document types and values stay 'extracted' until the reviewer "
           "verifies them; checks pass or flag only on verified inputs. Quotes stay in the language of the source "
           "document.")
with st.form("verify"):
    docs = pd.DataFrame([{"verified": d["status"] == "verified", "file": d["file"], "type found": d["doc_type"],
                          "listed as": d["listed_as"] or "(not listed)", "covers": ", ".join(d["covers"]),
                          "valid until": d["valid_until"] or "", "pages": d["pages"], "method": d["method"],
                          "notes": d["notes"] or ""} for d in pkg["documents"]])
    docs_edit = st.data_editor(docs, hide_index=True, disabled=list(docs.columns[1:]), key=f"docs_{pkg['package']}")

    st.subheader("Values per item")
    value_edits = {}
    for item in pkg["items"]:
        st.markdown(f"**{item_names[item['id']]}** · {item['name']} · {item['family']} · {item['brand']}")
        rows = pd.DataFrame([{"verified": x["status"] == "verified", "value name": k,
                              "value": "" if x["value"] is None else str(x["value"]), "unit": x["unit"] or "",
                              "source": x["source"] or "", "page": str(x["page"] or ""), "quote": x["quote"] or "",
                              "status": x["status"], "note": x["note"] or ""} for k, x in item["values"].items()])
        value_edits[item["id"]] = st.data_editor(rows, hide_index=True, disabled=list(rows.columns[1:]),
                                                 key=f"values_{item['id']}")
    if st.form_submit_button(f"Save verifications (checked_by {REVIEWER})"):
        for d, verified in zip(pkg["documents"], docs_edit["verified"]):
            set_verified(d, bool(verified))
        for item in pkg["items"]:
            for k, verified in zip(item["values"], value_edits[item["id"]]["verified"]):
                set_verified(item["values"][k], bool(verified))
        save(pkg)
        st.rerun()

with st.expander("Reader's notes outside the checks (AI output, for the reviewer to judge)"):
    for note in pkg.get("notes_for_reviewer", []):
        st.markdown(f"- {note}")

# ---------------------------------------------------------------- checks
st.subheader("Checks")
for group, title in GROUPS.items():
    rows = [r for r in results if r["check"][0] == group]
    if not rows:
        continue
    st.markdown(f"**{group} · {title}**")
    table = pd.DataFrame([{
        "key": f"{pkg['package']}|{key(r)}", "check": r["check"],
        "about": item_names.get(r["item"]) or r["doc"] or "package",
        "result": r["result"] if r["result"] == r["would_be"] else f"{r['result']} (would be {r['would_be']})",
        "reason": r["reason"],
        "rules": ", ".join(f"{i} ({r['rule_status'].get(i, 'checklist')})" for i in r["rules"]),
        "override": overrides.get(f"{pkg['package']}|{key(r)}", {}).get("override", ""),
        "note": overrides.get(f"{pkg['package']}|{key(r)}", {}).get("note", ""),
    } for r in rows])
    edited = st.data_editor(
        table, hide_index=True, key=f"checks_{pkg['package']}_{location}_{group}",
        disabled=["check", "about", "result", "reason", "rules"],
        column_config={"key": None, "override": st.column_config.SelectboxColumn(
            options=["", "pass", "flag", "unclear", "info"])})
    for row in edited.itertuples():
        if row.override or row.note:
            overrides[row.key] = {"override": row.override, "note": row.note}
        else:
            overrides.pop(row.key, None)

# Overrides apply after the tables are read, so the status and comments see this run's edits.
for r in results:
    o = overrides.get(f"{pkg['package']}|{key(r)}")
    if o and o["override"]:
        r["result"] = r["would_be"] = o["override"]
        r["reason"] += f" [override: {o['note']}]"

# ---------------------------------------------------------------- draft status (filled at the top)
with status_box:
    now, reasons = draft_status(results)
    later, _ = draft_status(results, "would_be")
    st.markdown(f"### Draft status: {now} · {LABELS[now]}")
    st.caption("Draft, the reviewer decides. 'Not approved' and 'Sample requested' are the reviewer's choice only.")
    if later != now:
        st.warning(f"Once the extracted values are verified as read: {later} · {LABELS[later]}")
    with st.expander(f"Why {now} ({len(reasons)} reasons)"):
        for reason in reasons:
            st.markdown(f"- {reason}")

# ---------------------------------------------------------------- comments and exports
st.subheader("Draft comments")
lines = list(dict.fromkeys(c for c in (comment(r) for r in results) if c))
st.caption("Built from templates and the values above; a language model may only rephrase them.")
st.code("\n".join(f"{n}. {line}" for n, line in enumerate(lines, 1)) or "(no comments)", language=None,
        wrap_lines=True)

st.subheader("Exports")
mine = [{"key": k, **v} for k, v in overrides.items() if k.startswith(f"{pkg['package']}|")]
st.download_button("overrides.csv", pd.DataFrame(mine, columns=["key", "override", "note"]).to_csv(index=False),
                   f"{pkg['package']}_overrides.csv")
approved = [{"item": item_names[i["id"]], "value name": k, "value": x["value"], "unit": x["unit"],
             "source": x["source"], "page": x["page"]}
            for i in pkg["items"] for k, x in i["values"].items() if x["status"] == "verified"]
st.download_button("approved_values.csv",
                   pd.DataFrame(approved, columns=["item", "value name", "value", "unit", "source", "page"])
                   .to_csv(index=False), f"{pkg['package']}_approved_values.csv")
