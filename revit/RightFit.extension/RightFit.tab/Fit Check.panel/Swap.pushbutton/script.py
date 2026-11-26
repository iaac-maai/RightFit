# -*- coding: utf-8 -*-
"""Put a candidate in the pump's place: the maker's family, or a type of the same family that names the
model. RightFit writes its verdict into the new element and draws what the swap changes. Ctrl+Z undoes the
whole swap at once."""
__title__ = "Swap"
from pyrevit import forms, revit, script

import rf_app
import rf_online_pull
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
names = [u"{:2d}  {} {}{}".format(i + 1, s["maker"], s["model"], u"  (submitted)" if s.get("submitted") else u"")
         for i, s in enumerate(g["sets"])]
shown = rf_setup.state().get("index", -1)
if 0 <= shown < len(names):  # the option on screen goes first
    names = [names[shown]] + names[:shown] + names[shown + 1:]
pick = forms.SelectFromList.show(names, title="RightFit: swap the set in the model for...", button_name="Swap",
                                 multiselect=False)
if not pick:
    script.exit()
s = g["sets"][int(pick.split()[0]) - 1]
if not forms.alert(u"Replace {} with {} {}?\n\nCtrl+Z puts the old set back.".format(
        (u"{} {}".format(g["current"].get("maker", u""), g["current"].get("model", u""))).strip(), s["maker"],
        s["model"]), yes=True, no=True):
    script.exit()
res, msg = rf_app.swap(doc, uidoc, g, s)
if res is None:
    forms.alert(msg, exitscript=True)
out = script.get_output()
rf_app.report(out, g, res, u"Swapped to {} {}".format(s["maker"], s["model"]), u"RightFit " + msg + u".")
rf_online_pull.send(out, doc, g, res, "swap")
