# -*- coding: utf-8 -*-
"""Click the pump set in the model: RightFit reads its room and checks the set where it stands, then
lists how every candidate would do in the same place. The model is not changed (only RightFit's drawing)."""
__title__ = "Check\nPump"
from pyrevit import forms, revit, script

import rf_app
import rf_online_pull
import rf_project
import rf_setup

doc, uidoc = revit.doc, revit.uidoc
if not rf_setup.settings().get("project"):
    forms.alert("Pick the project first (RightFit > Settings).", exitscript=True)
pulled = rf_online_pull.refresh()  # the project's pump sets from RightFit online, when this project is linked
rf_app.clear_drawing(doc)  # show the real pump again before asking for it
if not rf_app.pumps_in(doc):
    forms.alert("RightFit found no pump set in this model: no Mechanical Equipment, Plumbing, Generic Model "
                "or Specialty Equipment element whose name says it is a pump or matches a set in "
                "candidates.json. Place the pump set (or click Test Room) and try again.", exitscript=True)
try:
    pump = rf_app.pick_pump(uidoc)
except Exception:
    script.exit()
g = rf_app.gather(doc, pump)
if g["room"] is None:
    from Autodesk.Revit.DB import BuiltInCategory, FilteredElementCollector
    rooms = [r for r in FilteredElementCollector(doc).OfCategory(BuiltInCategory.OST_Rooms).WhereElementIsNotElementType()]
    p = g["sit"].probe
    forms.alert("No Room or Space found where this pump stands, in this model or its links. "
                "Place a Room (Architecture > Room) around it and try again.\n\n"
                "Looked at ({:.0f}, {:.0f}, {:.0f}) mm; rooms in the model: {}".format(
                    p.X * 304.8, p.Y * 304.8, p.Z * 304.8,
                    ", ".join("{} ({:.1f} m2)".format(r.Number, r.Area * 0.0929) for r in rooms) or "none")
                + "\n" + " | ".join(__import__("rf_model").LAST_ERRORS[:3]),
                exitscript=True)
st = rf_setup.state()
st.update({"pump": pump.UniqueId, "index": -1})
rf_setup.save_state(st)
res = rf_app.preview(doc, uidoc, g, g["current"])
out = script.get_output()
rf_app.report(out, g, res, u"The set in the model: " + (u"{} {}".format(g["current"].get("maker", u""),
                                                                         g["current"].get("model", u""))).strip())
if pulled:
    out.print_md(u"*" + pulled + u"*")
if g["sets"]:
    rf_app.candidates_table(out, g)
else:
    out.print_md(u"*No candidates.json in this project's revit folder, so there are no alternatives to compare.*")
rf_online_pull.send(out, doc, g, res, "check")
