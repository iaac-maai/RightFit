"""Load the MAF rule tables (data/maf/*.csv) and pick the rows for a location, family and date.

How rules are picked is described in docs/jurisdictions.md.
"""
import csv
import json
from datetime import date
from pathlib import Path

DATA = Path(__file__).resolve().parents[2] / "data" / "maf"

# Location chain: the layers a project collects rules from. ANY holds practice and engineer inputs.
CHAINS = {"RO": ["EU", "RO", "ANY"], "ES": ["EU", "ES", "ANY"]}


def load(name):
    with open(DATA / name, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def library():
    """Manufacturer documents found on official sites (MAF-11), or an empty library."""
    path = DATA / "library.json"
    return json.loads(path.read_text()) if path.exists() else {"documents": [], "not_found": []}


def tables():
    """All three tables at once: rules by id, family documents, checklist."""
    return {r["rule_id"]: r for r in load("rules.csv")}, load("family_documents.csv"), load("checklist.csv")


def for_family(cell, family):
    """True when a table cell like 'pump;ahu' or 'all' includes the family."""
    names = cell.split(";")
    return "all" in names or family in names


def in_force(rule, on):
    """A rule applies on a date when the date sits inside its valid_from / valid_to window."""
    if rule["valid_from"] and date.fromisoformat(rule["valid_from"]) > on:
        return False
    return not (rule["valid_to"] and date.fromisoformat(rule["valid_to"]) < on)


def active_ids(ids, rules, on):
    """The rule ids from a 'A;B;C' cell that are in force on the date."""
    return [i for i in ids.split(";") if i in rules and in_force(rules[i], on)]


def rules_for(rules, location, family, topic, on):
    """Rules of one topic for a family, in the location chain and in force on the date."""
    chain = CHAINS[location]
    return [r for r in rules.values() if r["topic"] == topic and r["jurisdiction"] in chain
            and for_family(r["applies_to"], family) and in_force(r, on)]


def documents_for(family_docs, location, family, when):
    """Rows of family_documents.csv that a family needs in the location, at the given stages."""
    chain = CHAINS[location]
    return [d for d in family_docs
            if d["jurisdiction"] in chain and d["when"] in when and for_family(d["family"], family)]
