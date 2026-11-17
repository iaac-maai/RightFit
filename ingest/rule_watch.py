"""Rule watch (roadmap MAF-10): has the act behind a legal rule changed since a person last read it? No AI here.

For each legal rule in data/maf/rules.csv, the act is found from the rule's source link and its official source is
asked for the act's latest version and any end of validity. The answer is compared with the rule's verified_on:
- EU: the Publications Office, through the Cellar notice of the act (consolidated versions, in force, end of validity);
- ES: the BOE open data service (the date the consolidated text was last updated, and any repeal);
- RO: legislatie.just.ro, the Portal Legislativ (the dates of the act's consolidated forms).

Run from the repository root:  python3 -m ingest.rule_watch
It only reads: rules.csv is never changed. A changed act is reported, and a person reads it again and decides.
"""
import re
import urllib.request
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta

from checks.maf.rules import load

NOT_LAW = ("practice", "engineer_input")   # statuses of rules that come from reviewers or the team, not from an act
# A harmonised standard is cited, replaced or withdrawn under the construction products regulation by Implementing
# Decision (EU) 2019/451 (docs/maf_rules.md), so that act is the one watched for the standards' rules.
STANDARDS = ("EU", "32019D0451")
CLIENT = "RightFit-rule-watch (IAAC student project)"


def act_of(rule):
    """The act behind a rule, from its source link: ("EU", CELEX), ("ES", BOE id or ELI link) or ("RO", portal id).
    None when the rule has no link that names an act."""
    url = rule["source_url"]
    if rule["topic"] == "doc.harmonised_standard":
        return STANDARDS
    if m := re.search(r"eur-lex\.europa\.eu/eli/([a-z_]+)/(\d{4})/(\d+)", url):
        kind = {"dir": "L", "reg": "R", "dec": "D"}.get(m[1].split("_")[0])   # reg_del is a regulation too
        if kind:
            return "EU", f"3{m[2]}{kind}{int(m[3]):04d}"
    if m := re.search(r"CELEX:[03](\d{4}[A-Z]\d{4})", url):   # a consolidated version names its act
        return "EU", "3" + m[1]
    if m := re.search(r"boe\.es/.*\bid=(BOE-A-\d{4}-\d+)", url):
        return "ES", m[1]
    if "boe.es/eli/" in url:
        return "ES", url
    if m := re.search(r"legislatie\.just\.ro/Public/DetaliiDocument(?:Afis)?/(\d+)", url):
        return "RO", m[1]
    return None


# --- Online: the only part that leaves the laptop ---

def get(url, accept):
    request = urllib.request.Request(url, headers={"User-Agent": CLIENT, "Accept": accept})
    with urllib.request.urlopen(request, timeout=120) as answer:
        return answer.read().decode("utf-8")


def ask(act):
    """The official source's answer about one act, as text."""
    where, name = act
    if where == "EU":
        return get(f"https://publications.europa.eu/resource/celex/{name}", "application/xml;notice=object")
    if where == "ES":
        if name.startswith("http"):   # an ELI link: the BOE page names the act's id
            found = re.search(r'rel="canonical" href="[^"]*id=(BOE-A-\d{4}-\d+)', get(name, "text/html"))
            if not found:
                raise LookupError(f"the BOE page {name} names no act")
            name = found[1]
        return get(f"https://www.boe.es/datosabiertos/api/legislacion-consolidada/id/{name}/metadatos",
                   "application/xml")
    return get(f"https://legislatie.just.ro/Public/DetaliiDocument/{name}", "text/html")


def try_ask(act):
    try:
        return ask(act)
    except Exception as e:   # one source down must not stop the others; its rules come back not_checked
        return e


# --- Offline: reading the answers and comparing them with the rules ---

def iso(text):
    """A BOE date, 20251218T213452Z or 20230102, as 2025-12-18."""
    return f"{text[:4]}-{text[4:6]}-{text[6:8]}"


def read_eu(text):
    work = ET.fromstring(text).find("WORK")
    versions = [d for e in work.findall("RESOURCE_LEGAL_CONSOLIDATED_BY_ACT_CONSOLIDATED")
                if (d := e.findtext("EMBEDDED_NOTICE/WORK/WORK_DATE_DOCUMENT/VALUE"))]
    # The latest end of validity is the act's own; 9999-12-31 means it has none. Earlier ones end parts of it.
    end = max((e.findtext("VALUE") or "" for e in work.findall("RESOURCE_LEGAL_DATE_END-OF-VALIDITY")), default="")
    return {"latest": max(versions, default=None), "ends": end if "" < end < "9999" else None,
            "in_force": work.findtext("RESOURCE_LEGAL_IN-FORCE/VALUE") != "false"}


def read_es(text):
    data = ET.fromstring(text).find("data/metadatos")
    repealed = data.findtext("fecha_derogacion")
    # The BOE gives the first day without force; "ends" is the last day the act applies, like a rule's valid_to.
    return {"latest": iso(data.findtext("fecha_actualizacion")),
            "ends": str(date.fromisoformat(iso(repealed)) - timedelta(days=1)) if repealed else None,
            "in_force": data.findtext("vigencia_agotada") != "S"}


def read_ro(text):
    if 'id="id_act"' not in text:   # an error page lists no forms either: never read it as "unchanged"
        raise ValueError("the portal did not send the act's page")
    forms = [f"{y}-{m}-{d}" for d, m, y in re.findall(r"Consolidarea din (\d\d)\.(\d\d)\.(\d{4})", text)]
    return {"latest": max(forms, default=None), "ends": None, "in_force": True}


# Per source: how its act is named in the report, what one of its versions is called, and how its answer is read.
SOURCES = {"EU": ("CELEX ", "consolidated version", read_eu),
           "ES": ("", "update of the consolidated text", read_es),
           "RO": ("legislatie.just.ro ", "consolidated form", read_ro)}


def compare(rule, got, version):
    """(result, date, detail) for one rule against what its source says."""
    seen, until, latest, end = rule["verified_on"], rule["valid_to"], got["latest"], got["ends"]
    # shortcut: a version dated before verified_on but published after it is not seen; the act's next version is.
    if latest and latest > seen:
        return "changed", latest, f"new {version} of {latest}; the rule was read on {seen}"
    if end and not (until and until <= end):
        return "changed", end, f"the act applies until {end}; the rule " + (f"until {until}" if until else "has no end date")
    if not got["in_force"] and not until:
        return "changed", None, "the source says the act is no longer in force; the rule has no end date"
    return "unchanged", latest, f"latest {version} of {latest}" if latest else f"no {version}"


def watch(rules, answers):
    """For each legal rule: unchanged, changed (with the date) or not_checked (with the reason). answers holds each
    act's answer as ask() returns it, or the error when asking failed. Never goes online."""
    out = []
    for rule in rules:
        if rule["status"] in NOT_LAW:
            continue
        act = act_of(rule)
        row = {"rule_id": rule["rule_id"], "act": act and SOURCES[act[0]][0] + act[1], "verified_on": rule["verified_on"]}
        if not act:
            out.append({**row, "result": "not_checked", "date": None, "detail": "the rule has no source link to an act"})
            continue
        _, version, read = SOURCES[act[0]]
        try:
            answer = answers[act]
            if isinstance(answer, Exception):
                raise answer
            got = read(answer)
        except Exception as e:   # no answer, or not the one expected: never "unchanged"
            out.append({**row, "result": "not_checked", "date": None, "detail": f"the source did not answer: {e}"})
            continue
        result, day, detail = compare(rule, got, version)
        out.append({**row, "result": result, "date": day, "detail": detail})
    return out


def run():
    """Ask the source of every legal rule, once per act, and compare. Goes online; takes up to a minute."""
    rules = load("rules.csv")
    acts = {act for r in rules if r["status"] not in NOT_LAW and (act := act_of(r))}
    with ThreadPoolExecutor(8) as pool:
        answers = dict(zip(acts, pool.map(try_ask, acts)))
    return watch(rules, answers)


if __name__ == "__main__":
    for r in run():
        print(f"{r['rule_id']:<20} {r['result']:<12} {r['act'] or '':<28} {r['detail']}")
