# -*- coding: utf-8 -*-
"""The Revit link's plain part (spec/features/revit_link.md): what a check sends to RightFit online, the checks waiting
on this computer, the copy of the project's data, and which online project a project folder is linked to. No Revit and
no network here, so the tests run it on Python 3; rf_online.py does the talking, with .NET, inside Revit.

Kept outside the repository, in %APPDATA%\\RightFit:
  online.json            the site's address, this computer's token, who it acts for
  outbox\\<time>.json      checks that could not be sent yet, sent with the next one
  online\\<project>\\       the project's data as the site last gave it (candidates.json, project.json, chosen.json)
"""
from __future__ import division
import datetime
import io
import json
import os

import rf_report

SITE = u"https://rightfit.hackathon-team6-cubicasa-app.workers.dev"


def home():
    return os.path.join(os.environ.get("APPDATA") or os.path.expanduser("~"), "RightFit")


def _read(path, default):
    try:
        with io.open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def _write(path, data):
    folder = os.path.dirname(path)
    if not os.path.isdir(folder):
        os.makedirs(folder)
    text = u"" + json.dumps(data, indent=2, ensure_ascii=False)  # the text first, so a failure never empties the file
    tmp = path + u".tmp"
    with io.open(tmp, "w", encoding="utf-8") as f:
        f.write(text)
    if os.path.exists(path):
        os.remove(path)
    os.rename(tmp, path)


# ---------------------------------------------------------------- this computer's link

def link(base=None):
    """The site's address, the token and who it acts for; token is None until Connect."""
    data = {"url": SITE, "token": None, "user": None}
    data.update(_read(os.path.join(base or home(), "online.json"), {}))
    return data


def save_link(data, base=None):
    _write(os.path.join(base or home(), "online.json"), data)


def forget_link(base=None):
    data = link(base)
    data.update({"token": None, "user": None})
    save_link(data, base)


# ---------------------------------------------------------------- the project folder and its online project

def linked_project(settings):
    """The online project ({"id", "name"}) linked to the project folder open in Settings, or None."""
    return (settings.get("online_projects") or {}).get(settings.get("project") or u"")


def set_linked_project(settings, online_id, online_name):
    links = dict(settings.get("online_projects") or {})
    if online_id:
        links[settings.get("project") or u""] = {"id": online_id, "name": online_name}
    else:
        links.pop(settings.get("project") or u"", None)
    settings["online_projects"] = links
    return settings


def cache_dir(online_id, base=None):
    return os.path.join(base or home(), "online", online_id)


def save_cache(online_id, answer, base=None):
    """Keep what the site gave: the pump sets, the settings, the reviewers' choice. A file the site doesn't have yet is
    left out, so the project folder's own file is used for it."""
    d = cache_dir(online_id, base)
    for name, key in ((u"candidates.json", "candidates"), (u"project.json", "project")):
        path = os.path.join(d, name)
        if answer.get(key) is not None:
            _write(path, answer[key])
        elif os.path.exists(path):
            os.remove(path)
    _write(os.path.join(d, u"chosen.json"), {"chosen": answer.get("chosen"), "sentAt": answer.get("sentAt"),
                                              "gotAt": datetime.datetime.now().isoformat()})


def cached(online_id, name, base=None):
    """A file from the site's last answer, or None."""
    path = os.path.join(cache_dir(online_id, base), name)
    return _read(path, None) if os.path.exists(path) else None


# ---------------------------------------------------------------- a check, as it travels

def _rules_text(rule_ids, rules):
    return [u"{} ({})".format(i, rules[i]["status"]) if i in rules else i for i in rule_ids]


def run_payload(action, room, res, rules, model_file=u"", ran_at=None, candidates=None, computer=u""):
    """What one Check Pump, Next Option or Swap sends: the room, the set, the verdict and every result with its rules.
    The drawing boxes stay in Revit. room is g["room"], res what rf_app.preview or swap returned, rules load_rules()."""
    s = res["set"]
    length, width, area = rf_report.floor_size(room.get("outline"))
    keep = ("id", "maker", "model", "submitted", "L", "W", "H", "kg", "pumps", "p2_each", "p2_needed", "standby",
            "dn_in", "dn_out", "dw_approval", "source", "status", "shape")
    out = {
        "action": action,
        "set": dict((k, s.get(k)) for k in keep if s.get(k) is not None),
        "room": {
            "name": room.get("name"), "kind": room.get("kind"), "length": length, "width": width, "height": room.get("height"),
            "area": area,
            "doors": [{"name": d.get("name"), "width": d.get("width"), "height": d.get("height")} for d in room.get("doors") or []],
            "things": [{"name": o.get("name"), "box": o.get("box")} for o in room.get("obstacles") or []],
            "pipes": [{"name": p.get("name"), "dn": p.get("dn"), "role": p.get("role")} for p in room.get("pipes") or []],
        },
        "verdict": {"verdict": res["verdict"]["verdict"], "confirmed": bool(res["verdict"].get("confirmed"))},
        "results": [{"check": r["check"], "result": r["result"], "would_be": r["would_be"], "reason": r["reason"],
                     "rules": _rules_text(r.get("rules") or [], rules), "blocking": bool(r.get("blocking"))}
                    for r in res["results"]],
        "model_file": model_file or u"",
        "ran_at": ran_at or datetime.datetime.now().replace(microsecond=0).isoformat(),
        "computer": computer or u"",
    }
    if candidates is not None:
        out["candidates"] = candidates
    return out


# ---------------------------------------------------------------- checks waiting on this computer

def outbox_dir(base=None):
    return os.path.join(base or home(), "outbox")


def keep_for_later(project_id, payload, base=None):
    """A check the site could not take now: kept with its project, sent with the next one. Returns the file."""
    d = outbox_dir(base)
    name = datetime.datetime.now().strftime("%Y%m%d-%H%M%S-%f") + u".json"
    path = os.path.join(d, name)
    _write(path, {"project": project_id, "payload": payload})
    return path


def waiting(base=None):
    """The checks waiting, oldest first: [(path, project id, payload)]."""
    d = outbox_dir(base)
    if not os.path.isdir(d):
        return []
    out = []
    for name in sorted(os.listdir(d)):
        if not name.endswith(u".json"):
            continue
        item = _read(os.path.join(d, name), None)
        if item and item.get("project") and item.get("payload"):
            out.append((os.path.join(d, name), item["project"], item["payload"]))
    return out


def done(path):
    try:
        os.remove(path)
    except OSError:
        pass


# ---------------------------------------------------------------- what the report says

def chosen_text(chosen):
    """The reviewers' choice, as a line for the report, or None."""
    if not chosen or not chosen.get("setLabel"):
        return None
    who = chosen.get("chosenBy") or u"a reviewer"
    when = (chosen.get("chosenAt") or u"")[:10]
    note = u': "{}"'.format(chosen["note"]) if chosen.get("note") else u""
    return u"The reviewers chose <b>{}</b> ({}, {}){}".format(chosen["setLabel"], who, when, note)
