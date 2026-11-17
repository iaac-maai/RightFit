# -*- coding: utf-8 -*-
"""Build the test room described in the project's project.json, to try RightFit in an empty model."""
__title__ = "Test\nRoom"
from pyrevit import forms, revit, script

import rf_project
import rf_testroom

room = rf_project.project().get("test_room")
if not room:
    forms.alert("This project's project.json has no test_room.", exitscript=True)
notes = rf_testroom.build(revit.doc, room)
out = script.get_output()
out.print_md(u"## Test room {} built".format(room.get("name", u"")))
out.print_md(u"From: {}".format(room.get("source", u"project.json")))
for n in notes:
    out.print_md(u"- " + n)
out.print_md(u"Now click **Check Pump** and pick the pump set.")
