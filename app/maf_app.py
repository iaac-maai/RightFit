"""RightFit MAF review page. Run from the repository root:  streamlit run app/maf_app.py

The page follows the reviewer's work: read the draft answer, go through the problems, confirm what the AI
read, copy the answer. Everything is a draft; the reviewer decides.
"""
import json
import sys
from collections import Counter
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from checks.maf.checks import DOC_LABELS, context, run_all  # noqa: E402
from checks.maf.status import LABELS, draft_status  # noqa: E402
from explain.maf_comments import comment  # noqa: E402

EXTRACTED = ROOT / "data/maf/extracted"
# shortcut: one reviewer name for every confirmation; add a login when more reviewers use the app.
REVIEWER = "Luca"
CHECK_NAMES = {"D1": "Required documents", "D2": "Declaration matches the products", "D3": "Certificate in date",
               "D4": "Attachment is what the form says", "V1": "Duty point", "V2": "Pressure rating",
               "E1": "Ecodesign", "C": "Reviewers' checklist", "R": "Delivery reminder"}
VALUE_NAMES = {"used_for": "Used for (form)", "duty_flow": "Required flow (form)", "duty_head": "Required head (form)",
               "duty_airflow_supply": "Required supply airflow (form)",
               "duty_airflow_extract": "Required extract airflow (form)", "flow": "Flow at the duty point",
               "head": "Head at the duty point", "power": "Motor power", "max_pressure": "Max working pressure",
               "controller_included": "Controller or panel included", "bms_included": "BMS module included",
               "bms_protocol": "BMS protocols", "hrs_type": "Heat recovery type",
               "hrs_efficiency": "Heat recovery efficiency", "sfp_int": "SFPint", "sfp_int_limit": "SFPint limit",
               "gwp": "GWP", "seer": "SEER", "scop": "SCOP", "dx_refrigerant": "DX coil refrigerant"}
VERDICT = {"pass": "OK", "flag": "Problem", "unclear": "Question", "info": "Info"}
DECISIONS = {"suggested": "Not decided", "accepted": "Add to my answer", "rejected": "Not relevant"}
STATUS_RULE = {"A": "Every check passed or is only for information.",
               "B": "Nothing sends the package back, but there is at least one problem or open question.",
               "C": "A product has no data sheet that names it, or a blocking checklist item is missing."}

st.set_page_config(page_title="RightFit · MAF review", layout="wide")


def value_name(key):
    return VALUE_NAMES.get(key, key.replace("_", " ").capitalize())


def key_of(r):
    return "|".join(str(x) for x in (r["check"], r["item"], r["doc"], ",".join(r["rules"]), r["code"]))


def save(pkg):
    (EXTRACTED / f"{pkg['package']}.json").write_text(json.dumps(pkg, ensure_ascii=False, indent=2) + "\n")


def set_verified(entry, verified):
    """Mark a value or document as confirmed by the reviewer, or put it back to what the AI left."""
    if verified == (entry["status"] == "verified"):
        return
    has_value = entry.get("value") not in (None, "") if "value" in entry else True
    entry["status"] = "verified" if verified else ("extracted" if has_value else "unclear")
    entry["checked_by"] = REVIEWER if verified else None
    entry["verified_on"] = date.today().isoformat() if verified else None


def decide(name, finding_id, field, widget_key):
    """Save the reviewer's decision (or note) on an AI suggestion straight into the package file."""
    path = EXTRACTED / f"{name}.json"
    data = json.loads(path.read_text())
    finding = next(f for f in data["ai_findings"] if f["id"] == finding_id)
    value = st.session_state[widget_key]
    if field == "status":
        finding["status"] = {v: k for k, v in DECISIONS.items()}[value]
        finding["decided_by"] = None if finding["status"] == "suggested" else REVIEWER
    else:
        finding["note"] = value or None
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")


# ---------------------------------------------------------------- choose the package
packages = {p.stem: json.loads(p.read_text()) for p in sorted(EXTRACTED.glob("*.json"))}

st.title("MAF review")
st.caption("The AI read the documents, fixed rules checked them, and you decide. Nothing here is approved until "
           "you sign.")
name = st.radio("Which package?", list(packages), horizontal=True, format_func=lambda n: (
    f"{n} · form {packages[n]['form']['form_no']} rev {packages[n]['form']['revision']} · "
    + ", ".join(i["name"] for i in packages[n]["items"])))
pkg, form = packages[name], packages[name]["form"]
form_date = date.fromisoformat(form["date"])

with st.expander("Location and dates"):
    c1, c2, c3 = st.columns(3)
    location = c1.radio("Project location", ["RO", "ES"], horizontal=True,
                        format_func={"RO": "Romania", "ES": "Spain"}.get)
    review = c2.date_input("Review date", form_date)
    delivery = c3.date_input("Expected delivery", form_date + timedelta(weeks=form["delivery_weeks"] or 0),
                             help=f"From the form: {form['delivery_raw']}")

# ---------------------------------------------------------------- run the checks
results = run_all(pkg, context(location, review, delivery))
items = {i["id"]: f"{i['name']} ({i['model']})" for i in pkg["items"]}
for r in results:
    r["key"] = f"dismiss|{name}|{key_of(r)}"
    # A problem the reviewer marked "not a problem" counts as OK from here on, with the reason kept.
    if st.session_state.get(r["key"]):
        r["result"] = r["would_be"] = "pass"
        r["reason"] += f" [not a problem for the reviewer: {st.session_state.get(r['key'] + '|why') or 'no reason'}]"
        r["dismissed"] = True

problems = [r for r in results if r["would_be"] == "flag"]
questions = [r for r in results if r["would_be"] == "unclear"]
dismissed = [r for r in results if r.get("dismissed")]
readings = [x for i in pkg["items"] for x in i["values"].values()] + pkg["documents"]
to_confirm = sum(x["status"] != "verified" for x in readings)
ai_findings = pkg.get("ai_findings", [])
accepted = [f for f in ai_findings if f["status"] == "accepted"]
undecided = sum(f["status"] == "suggested" for f in ai_findings)
letter, status_reasons = draft_status(results, "would_be", [f["title"] for f in accepted])

# ---------------------------------------------------------------- the draft answer
colour = {"A": "green", "B": "orange", "C": "red"}[letter]
with st.container(border=True):
    st.markdown(f"## Draft answer: :{colour}[{letter} · {LABELS[letter]}]")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Problems to fix", len(problems))
    m2.metric("Questions for the contractor", len(questions))
    m3.metric("Checks passed", sum(r["would_be"] == "pass" for r in results))
    m4.metric("Readings to confirm", f"{to_confirm} of {len(readings)}")
    if to_confirm:
        st.caption("This draft rests on what the AI read. Confirm the readings in step 2: a check only counts as "
                   "passed once the values behind it are confirmed.")
    if undecided:
        st.caption(f"{undecided} AI suggestions are waiting for your decision in the AI suggestions tab.")
    with st.expander(f"Why {letter}?"):
        st.write(STATUS_RULE[letter])
        if letter == "C":
            for reason in status_reasons:
                st.markdown(f"- {reason}")
        counts = Counter(f"{VERDICT[r['would_be']]} · {CHECK_NAMES[r['check']]}" for r in problems + questions)
        counts.update({"AI suggestion you added to the answer": len(accepted)} if accepted else {})
        for text, n in counts.items():
            st.markdown(f"- {text}: {n}")
        st.caption("What each reason means and where it comes from: docs/maf_status_reasons.md")

step1, ai_tab, step2, step3, everything = st.tabs([
    "1 · Problems found", f"AI suggestions ({undecided} to decide)" if undecided else "AI suggestions",
    "2 · Confirm what the AI read", "3 · Answer to send", "Everything that was checked"])

# ---------------------------------------------------------------- step 1: problems
with step1:
    if not problems and not questions:
        st.success("No problems and no questions.")
    for item_id in [*items, None]:
        mine = [r for r in problems + questions if r["item"] == item_id]
        if not mine:
            continue
        st.subheader(items.get(item_id, "Documents of the package"))
        for r in mine:
            with st.container(border=True):
                left, right = st.columns([5, 1])
                tag = ":red[**Problem**]" if r["would_be"] == "flag" else ":orange[**Question**]"
                left.markdown(f"{tag} · {CHECK_NAMES[r['check']]}")
                left.markdown(comment(r) or r["reason"])
                rules = ", ".join(f"{i} ({r['rule_status'].get(i, 'checklist')})" for i in r["rules"])
                left.caption(f"Why: {r['reason']}"
                             + (f" · Look at: {'; '.join(r['sources'])}" if r["sources"] else "")
                             + (f" · Rule: {rules}" if rules else ""))
                right.checkbox("Not a problem", key=r["key"])
    if dismissed:
        st.subheader("Marked as not a problem")
        for r in dismissed:
            with st.container(border=True):
                left, right = st.columns([5, 1])
                left.markdown(f"~~{CHECK_NAMES[r['check']]}: {items.get(r['item'], r['doc'] or '')}~~")
                left.text_input("Why is it not a problem?", key=r["key"] + "|why")
                right.checkbox("Not a problem", key=r["key"])

# ---------------------------------------------------------------- AI suggestions, kept apart from the rules
with ai_tab:
    if not ai_findings:
        st.info("The second AI reviewer has not run on this package yet.")
    else:
        st.caption("A second AI reviewer read the whole package and proposes these. No rule checks them, and they "
                   "change no check result. Add the ones you agree with to your answer.")
        for f in ai_findings:
            with st.container(border=True):
                st.markdown(f":violet[**AI suggestion**] · {f['kind'].capitalize()} · "
                            f"{', '.join(items.get(i, i) for i in f['items'])}")
                st.markdown(f"**{f['title']}.** {f['finding']}")
                for e in f["evidence"]:
                    st.caption(f"{e['source']}, p. {e['page']}: \"{e['quote']}\"")
                st.markdown(f"Suggested comment: *{f['suggested_comment']}*")
                key = f"ai|{name}|{f['id']}"
                st.radio("Your decision", list(DECISIONS.values()), horizontal=True, key=key,
                         index=list(DECISIONS).index(f["status"]), on_change=decide,
                         args=(name, f["id"], "status", key))
                if f["status"] == "rejected":
                    st.text_input("Why is it not relevant?", value=f["note"] or "", key=key + "|note",
                                  on_change=decide, args=(name, f["id"], "note", key + "|note"))

# ---------------------------------------------------------------- step 2: confirm the reading
with step2:
    st.write("Tick each line you have checked against the document. Unticked lines stay as the AI read them.")
    notes = pkg.get("notes_for_reviewer", [])
    if notes:
        st.markdown("**Reading notes**")
        st.caption("How the AI read the package, for you to check.")
        for note in notes:
            st.markdown(f"- {note}")

    with st.form("confirm"):
        st.markdown("**Documents**")
        docs = pd.DataFrame([{
            "Correct?": d["status"] == "verified", "Document": d["file"],
            "What it is": DOC_LABELS.get(d["doc_type"], d["doc_type"]), "Names": ", ".join(d["covers"]),
            "Listed in the form as": d["listed_as"] or "(not listed)", "Valid until": d["valid_until"] or "",
            "Pages": d["pages"], "Read from": d["method"]} for d in pkg["documents"]])
        docs_edit = st.data_editor(docs, hide_index=True, disabled=list(docs.columns[1:]), key=f"docs_{name}")
        edits = {}
        for item in pkg["items"]:
            st.markdown(f"**{items[item['id']]}**")
            rows = pd.DataFrame([{
                "Correct?": x["status"] == "verified", "What": value_name(k),
                "Value": "not found" if x["value"] in (None, "") else str(x["value"]), "Unit": x["unit"] or "",
                "Page": str(x["page"] or ""), "Quote from the document": x["quote"] or "",
                "File": x["source"] or "", "Note": x["note"] or ""} for k, x in item["values"].items()])
            edits[item["id"]] = st.data_editor(rows, hide_index=True, disabled=list(rows.columns[1:]),
                                               key=f"values_{item['id']}")
        if st.form_submit_button(f"Save what I confirmed (as {REVIEWER})", type="primary"):
            for d, ok in zip(pkg["documents"], docs_edit["Correct?"]):
                set_verified(d, bool(ok))
            for item in pkg["items"]:
                for k, ok in zip(item["values"], edits[item["id"]]["Correct?"]):
                    set_verified(item["values"][k], bool(ok))
            save(pkg)
            st.rerun()

# ---------------------------------------------------------------- step 3: the answer
with step3:
    lines = list(dict.fromkeys([c for c in (comment(r) for r in results) if c]
                               + [f["suggested_comment"] for f in accepted]))
    answer = (f"MAF {form['form_no']} rev {form['revision']}: {LABELS[letter]} ({letter})\n\n"
              + ("\n".join(f"{n}. {line}" for n, line in enumerate(lines, 1)) or "No comments."))
    st.write("Copy the answer with the button in the top right corner of the box, or download it.")
    st.code(answer, language=None, wrap_lines=True)
    c1, c2, c3 = st.columns(3)
    c1.download_button("Download the answer", answer, f"{name}_answer.txt")
    approved = [{"item": items[i["id"]], "value": value_name(k), "reading": x["value"], "unit": x["unit"],
                 "file": x["source"], "page": x["page"]}
                for i in pkg["items"] for k, x in i["values"].items() if x["status"] == "verified"]
    c2.download_button("Download confirmed values", pd.DataFrame(
        approved, columns=["item", "value", "reading", "unit", "file", "page"]).to_csv(index=False),
        f"{name}_approved_values.csv", help="For the certification consultant and the O&M file")
    c3.download_button("Download what I marked as not a problem", pd.DataFrame(
        [{"check": r["check"], "about": items.get(r["item"], r["doc"]),
          "why": st.session_state.get(r["key"] + "|why", "")} for r in dismissed],
        columns=["check", "about", "why"]).to_csv(index=False), f"{name}_overrides.csv")

# ---------------------------------------------------------------- everything
with everything:
    st.caption("Every check the tool ran on this package. It does not check coordination with the architecture, "
               "whether the design is approved, the client's brand preferences, or whether the equipment fits on "
               "site.")
    st.dataframe(pd.DataFrame([{
        "Check": CHECK_NAMES[r["check"]], "About": items.get(r["item"], r["doc"] or "package"),
        "Result": VERDICT[r["would_be"]] + ("" if r["result"] == r["would_be"] else " (reading not confirmed)"),
        "Why": r["reason"], "Rule": ", ".join(r["rules"])} for r in results]), hide_index=True)
