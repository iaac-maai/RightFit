# -*- coding: utf-8 -*-
"""Where things are, and the add-in's settings.

The add-in lives in the repository at revit/RightFit.extension, so the repository is two folders up.
The checks themselves are in checks/space/space_checks.py; we put that folder on Python's path so Revit's
Python 2.7 (IronPython) can import the same file our tests run on Python 3.
"""
from __future__ import division
import io
import json
import os
import sys

EXT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO = os.path.dirname(os.path.dirname(EXT))
CHECKS = os.path.join(REPO, "checks", "space")
if CHECKS not in sys.path:
    sys.path.append(CHECKS)

import space_checks  # noqa: E402  (the deterministic checks, no Revit inside)

# Per-person settings, outside the repository: which projects folder and project, which service space.
HOME = os.path.join(os.environ.get("APPDATA") or os.path.expanduser("~"), "RightFit")
SETTINGS = os.path.join(HOME, "settings.json")
STATE = os.path.join(HOME, "state.json")

DEFAULTS = {
    "projects_dir": os.path.join(REPO, "data", "projects"),  # git-ignored
    "project": "",
    "service": "standard",
}


def _read(path, default):
    try:
        with io.open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return dict(default)


def _write(path, data):
    if not os.path.isdir(HOME):
        os.makedirs(HOME)
    text = u"" + json.dumps(data, indent=2)  # build the text first, so a failure never empties the file
    with io.open(path, "w", encoding="utf-8") as f:
        f.write(text)


def settings():
    s = dict(DEFAULTS)
    s.update(_read(SETTINGS, {}))
    return s


def save_settings(s):
    _write(SETTINGS, s)


def state():
    """What the last button did: which pump, which candidate is shown."""
    return _read(STATE, {"pump": None, "index": -1})


def save_state(st):
    _write(STATE, st)
