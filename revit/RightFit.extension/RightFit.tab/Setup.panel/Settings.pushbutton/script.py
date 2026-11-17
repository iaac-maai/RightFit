# -*- coding: utf-8 -*-
"""Pick the projects folder, the project and the service space."""
__title__ = "Settings"
from pyrevit import forms, script

import rf_project
import rf_setup

s = rf_setup.settings()
choice = forms.CommandSwitchWindow.show(["Project", "Service space", "Projects folder"],
                                        message="Projects folder: {}\nProject: {}\nService space: {}".format(
                                            s["projects_dir"], s["project"] or "(none)", s["service"]))
if choice == "Projects folder":
    folder = forms.pick_folder(title="The folder that holds the project folders")
    if folder:
        s["projects_dir"], s["project"] = folder, ""
elif choice == "Project":
    names = rf_project.projects(s)
    if not names:
        forms.alert("No project in {} has a revit folder. See revit/README.md.".format(s["projects_dir"]),
                    exitscript=True)
    pick = forms.SelectFromList.show(names, title="RightFit: project", multiselect=False)
    if pick:
        s["project"] = pick
elif choice == "Service space":
    rf_setup.save_settings(s)
    presets = sorted(rf_project.project().get("service", {}).keys())
    if not presets:
        forms.alert("This project's project.json sets no service space.", exitscript=True)
    pick = forms.CommandSwitchWindow.show(presets, message="Service space around the set")
    if pick:
        s["service"] = pick
else:
    script.exit()
rf_setup.save_settings(s)
