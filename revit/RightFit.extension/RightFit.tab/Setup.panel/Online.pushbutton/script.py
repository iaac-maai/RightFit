# -*- coding: utf-8 -*-
"""Link this computer and this project folder to RightFit online (spec/features/revit_link.md): Revit then gets the
project's pump sets from the site and sends each check there. Revit never sees a password: it shows a code that you
approve on the site."""
__title__ = "Online"
import io
import json
import os

from pyrevit import forms, script

import rf_online_core as core
import rf_project
import rf_setup

try:
    import rf_online
except Exception as e:  # .NET not reachable: say so rather than fail without a word
    forms.alert(u"RightFit online can't start here: {}".format(e), exitscript=True)

s = rf_setup.settings()
lk = core.link()
online = core.linked_project(s)
user = lk.get("user") or {}
waiting = len(core.waiting())
# one short line: the switch window shows a single line of message
status = u"{} · {} → {}{}".format(
    u"Linked as {}".format(user.get("name", u"")) if lk.get("token") else u"This computer is not linked",
    s.get("project") or u"no project folder", online["name"] if online else u"no online project",
    u" · {} check(s) waiting".format(waiting) if waiting else u"")

if not lk.get("token"):
    options = ["Connect this computer"]
else:
    options = ["Link this project folder", "Send project data", "Get project data", "Send waiting checks",
               "Open the Fit check page", "Disconnect this computer"]
choice = forms.CommandSwitchWindow.show(options, message=status)
if not choice:
    script.exit()


def fail(e):
    forms.alert(u"{}".format(e), exitscript=True)


if choice == "Connect this computer":
    try:
        a = rf_online.start_link()
    except rf_online.Offline as e:
        fail(u"RightFit online can't be reached ({}). Check the internet and try again.".format(e))
    except Exception as e:
        fail(u"RightFit online did not start a link. It answered: {}\n\nIf it asks to sign in, the site doesn't have the Revit "
             u"link yet: it needs the update deployed (web/README.md).".format(e))
    rf_online.open_page(a["url"])
    forms.alert(u"Your code:   {}\n\nRightFit online is opening in your browser. Sign in if it asks, check that it shows "
                u"this code and this computer ({}), and click Approve.\n\nThen click OK here.".format(a["userCode"], rf_online.computer()),
                title="RightFit: link this computer")
    state, msg = rf_online.finish_link(a["deviceCode"], wait_s=30, interval_s=a.get("interval", 3))
    forms.alert(msg + (u"\n\nNow: RightFit › Online › Link this project folder." if state == "approved" else u""))

elif choice == "Link this project folder":
    if not s.get("project"):
        fail(u"Pick the project folder first: RightFit › Settings › Project.")
    try:
        me = rf_online.me()
    except Exception as e:
        fail(e)
    projects = me.get("projects") or []
    if not projects:
        fail(u"You are in no project on RightFit online whose forms you see. Ask the consultant for an invitation.")
    names = [u"{}{}".format(p["name"], u"  (locked)" if p.get("locked") else u"") for p in projects] + [u"Not linked"]
    pick = forms.SelectFromList.show(names, title=u"RightFit: the online project for {}".format(s["project"]), multiselect=False)
    if not pick:
        script.exit()
    p = projects[names.index(pick)] if pick != u"Not linked" else None
    core.set_linked_project(s, p["id"] if p else None, p["name"] if p else None)
    rf_setup.save_settings(s)
    if p:
        try:
            a = rf_online.get_data(p["id"])
            got = u"{} pump sets from the site.".format(len((a.get("candidates") or {}).get("sets", []))) if a.get("candidates") \
                else u"The site has no pump sets for it yet: send them with Send project data."
        except Exception as e:
            got = u"Could not get its data yet: {}".format(e)
        forms.alert(u"{} is linked to {}.\n{}\n\nEvery Check Pump, Next Option and Swap now goes to its Fit check page.".format(
            s["project"], p["name"], got))

elif choice == "Send project data":
    if not online:
        fail(u"Link this project folder first.")
    f = rf_project.folder()
    files = {}
    for name in (u"candidates.json", u"project.json"):
        path = os.path.join(f, name) if f else u""
        if os.path.exists(path):
            with io.open(path, encoding="utf-8") as fh:
                files[name] = json.load(fh)
    if u"candidates.json" not in files:
        fail(u"No candidates.json in {}.".format(f))
    n = len(files[u"candidates.json"].get("sets", []))
    if not forms.alert(u"Send {} pump sets and the project's fit check settings from\n{}\nto {}?\n\nThey replace what the site "
                       u"has, for everyone in the project.".format(n, f, online["name"]), yes=True, no=True):
        script.exit()
    try:
        rf_online.send_data(online["id"], files[u"candidates.json"], files.get(u"project.json", {}))
        rf_online.get_data(online["id"])
    except Exception as e:
        fail(e)
    forms.alert(u"Sent: {} pump sets are on {}'s Fit check page.".format(n, online["name"]))

elif choice == "Get project data":
    if not online:
        fail(u"Link this project folder first.")
    try:
        a = rf_online.get_data(online["id"])
    except Exception as e:
        fail(e)
    line = core.chosen_text(a.get("chosen"))
    forms.alert(u"{} pump sets from {}.{}".format(len((a.get("candidates") or {}).get("sets", [])), online["name"],
                                                    u"\n" + line.replace(u"<b>", u"").replace(u"</b>", u"") if line else u""))

elif choice == "Send waiting checks":
    try:
        sent, left = rf_online.send_waiting()
    except Exception as e:
        fail(e)
    forms.alert(u"Sent {} check(s); {} still waiting.".format(sent, left))

elif choice == "Open the Fit check page":
    rf_online.open_page(lk["url"].rstrip(u"/") + (u"/p/{}/fitcheck".format(online["id"]) if online else u"/"))

elif choice == "Disconnect this computer":
    if forms.alert(u"Forget this computer's link? Unlink it on the site too (a project's Fit check page) to stop it there.",
                   yes=True, no=True):
        rf_online.disconnect()
