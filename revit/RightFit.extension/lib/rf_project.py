# -*- coding: utf-8 -*-
"""The project's own data, from data/projects/<project>/revit/ (git-ignored, never in the repository):

  candidates.json   the submitted set and its alternatives, each value with its source and status
  project.json      the service space presets, the circuit when the model has none, a test room
  families/         the makers' Revit families (.rfa); families.json says which file is which set

Templates with the fields and no values are in revit/templates/.
"""
from __future__ import division
import io
import json
import os

import rf_setup


def folder(s=None):
    s = s or rf_setup.settings()
    if not s.get("project"):
        return None
    return os.path.join(s["projects_dir"], s["project"], "revit")


def projects(s=None):
    """Project folders that have a revit/ folder."""
    s = s or rf_setup.settings()
    root = s["projects_dir"]
    if not os.path.isdir(root):
        return []
    return sorted(p for p in os.listdir(root) if os.path.isdir(os.path.join(root, p, "revit")))


def _json(name, default):
    f = folder()
    path = os.path.join(f, name) if f else None
    if not path or not os.path.exists(path):
        return default
    with io.open(path, encoding="utf-8") as fh:
        return json.load(fh)


def candidates():
    return _json("candidates.json", {"sets": []}).get("sets", [])


def project():
    return _json("project.json", {})


def service():
    """The consultant's service space for this project (mm), from project.json."""
    p = project()
    presets = p.get("service", {})
    name = rf_setup.settings().get("service", "standard")
    return name, presets.get(name, {})


def family_file(s):
    """The maker's model of a set (a Revit family .rfa or a 3D drawing .dwg) and how to place it:
    the families.json entry, else families/<id>.rfa or families/<id>.dwg."""
    f = folder()
    sid = s.get("id")
    if not f or not sid:  # a set that is not in the candidates list has no maker file
        return None, {}
    fam_dir = os.path.join(f, "families")
    entry = {}
    try:
        with io.open(os.path.join(fam_dir, "families.json"), encoding="utf-8") as fh:
            entry = json.load(fh).get(sid) or {}
    except Exception:
        pass
    names = [entry["file"]] if entry.get("file") else [sid + ".rfa", sid + ".dwg"]
    for n in names:  # a Revit family, or the maker's 3D drawing
        path = os.path.join(fam_dir, n)
        if os.path.exists(path):
            return path, entry
    return None, entry


def _norm(text):
    return u"".join(ch for ch in (text or u"").lower() if ch.isalnum())


def match(names, sets=None):
    """The candidate a model element is: the first set whose model code appears in the element's names
    (family, type, Model parameter, comments)."""
    sets = sets if sets is not None else candidates()
    joined = _norm(u" ".join(n for n in names if n))
    best = None
    for s in sets:
        code = _norm(s.get("model"))
        if code and code in joined and (best is None or len(code) > len(_norm(best["model"]))):
            best = s
    if best is None:
        subs = [s for s in sets if s.get("in_model")]
        best = subs[0] if subs else None
    return best
