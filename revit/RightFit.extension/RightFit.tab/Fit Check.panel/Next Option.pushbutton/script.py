# -*- coding: utf-8 -*-
"""Show the next candidate in the pump's place, as a preview: the pump itself is hidden in the RightFit 3D
view, not changed."""
__title__ = "Next\nOption"
from pyrevit import forms, revit, script

import rf_app
import rf_setup

doc, uidoc = revit.doc, revit.uidoc
pump = rf_app.remembered_pump(doc)
if pump is None:  # nothing remembered (or it was undone): ask for the pump
    try:
        pump = rf_app.pick_pump(uidoc)
    except Exception:
        script.exit()
    st = rf_setup.state()
    st.update({"pump": pump.UniqueId, "index": -1})
    rf_setup.save_state(st)
g = rf_app.gather(doc, pump)
if not g["sets"] or g["room"] is None:
    forms.alert("No candidates for this project, or no room at the pump.", exitscript=True)
st = rf_setup.state()
index = (st.get("index", -1) + 1) % len(g["sets"])
s = g["sets"][index]
res = rf_app.preview(doc, uidoc, g, s)
st = rf_setup.state()
st["index"] = index
rf_setup.save_state(st)
rf_app.report(script.get_output(), g, res, u"Option {} of {}: {} {}{}".format(
    index + 1, len(g["sets"]), s["maker"], s["model"], u" (submitted)" if s.get("submitted") else u""))
