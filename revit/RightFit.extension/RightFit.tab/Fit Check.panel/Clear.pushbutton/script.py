# -*- coding: utf-8 -*-
"""Remove what RightFit drew (previews, service space, clashes) and show the pump again."""
__title__ = "Clear"
from pyrevit import forms, revit

from Autodesk.Revit.DB import Transaction
import rf_draw
import rf_setup

doc = revit.doc
st = rf_setup.state()
t = Transaction(doc, "RightFit: clear")
t.Start()
n = rf_draw.clear(doc, st.get("hidden", []))
t.Commit()
st["hidden"] = []
rf_setup.save_state(st)
forms.alert("Removed {} RightFit drawing(s).".format(n))
