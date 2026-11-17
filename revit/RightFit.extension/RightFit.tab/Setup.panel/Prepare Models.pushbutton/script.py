# -*- coding: utf-8 -*-
"""Save the shape of every maker's Revit family (.rfa) once, so that Next Option draws it from the saved shape
and never loads the family into the project (loading them left Revit busy for minutes). Nothing is kept in the
model: each family is loaded, measured and saved, then the change is undone."""
__title__ = "Prepare\nModels"
import os

from Autodesk.Revit.DB import BuiltInCategory, Transaction, XYZ
from pyrevit import revit, script

import rf_draw
import rf_model
import rf_project

doc = revit.doc
out = script.get_output()
out.print_md(u"## Prepare the makers' models")
done = 0
for s in rf_project.candidates():
    path, entry = rf_project.family_file(s)
    if not path or not path.lower().endswith(".rfa"):
        continue
    saved = rf_draw.shape_path(path, entry)
    label = u"{} {}".format(s.get("maker", u""), s.get("model", u""))
    if os.path.exists(saved):
        out.print_md(u"- {}: already saved".format(label))
        continue
    t = Transaction(doc, u"RightFit: prepare " + label)
    rf_draw.accept_warnings(t)
    t.Start()
    try:
        frame = rf_model.Frame(XYZ(0, 0, 0), XYZ.BasisX, 0)
        el, b, what = rf_draw.place_model(doc, path, entry, frame, s, 0, rf_draw.lowest_level(doc),
                                          rf_draw.view3d(doc), u"RF prepare", BuiltInCategory.OST_GenericModel,
                                          as_shape=True)
        if os.path.exists(saved):
            done += 1
            out.print_md(u"- {}: saved ({:.0f} x {:.0f} x {:.0f} mm)".format(label, b[2] - b[0], b[3] - b[1], b[5] - b[4]))
        else:
            out.print_md(u"- {}: **not saved** ({})".format(label, what or u"no shape"))
    except Exception as err:
        out.print_md(u"- {}: **not saved** ({})".format(label, err))
    t.RollBack()  # keep nothing in the model
out.print_md(u"{} shape(s) saved. Next Option now draws these sets without loading their families.".format(done))
