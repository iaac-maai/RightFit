# -*- coding: utf-8 -*-
"""What the fit check buttons call for RightFit online (spec/features/revit_link.md, section 6): get the project's data
before a check, send the check after it. Nothing here may stop a check: when the site, the network or .NET fails, the
check goes on with the last copy, or with the project folder, and the report says so."""
import rf_online_core as core
import rf_setup


def _online():
    online = core.linked_project(rf_setup.settings())
    return online if online and core.link().get("token") else None


def refresh():
    """Get the project's pump sets and settings from the site. Returns a line for the report, or None when this project
    folder is not linked."""
    online = _online()
    if not online:
        return None
    try:
        import rf_online
        a = rf_online.get_data(online["id"])
        if not a.get("candidates"):
            return u"RightFit online has no pump sets for {} yet: using the project folder's. Send them with RightFit › Online.".format(online["name"])
        return u"Pump sets from RightFit online ({}), sent there on {}.".format(online["name"], (a.get("sentAt") or u"")[:10])
    except Exception as e:
        kept = core.cached(online["id"], u"chosen.json") or {}
        when = (kept.get("gotAt") or u"")[:16].replace(u"T", u" ")
        why = u"can't be reached" if type(e).__name__ == "Offline" else u"answered: {}".format(e)
        return u"RightFit online {}; using {}.".format(why, u"the copy from " + when if when else u"the project folder's pump sets")


def send(out, doc, g, res, action):
    """Send the check, and print what happened at the end of the report."""
    if not _online():
        return
    try:
        import rf_online
        rf_online.after_check(out, doc, g, res, action)
    except Exception as e:
        out.print_md(u"*Not sent to RightFit online: {}*".format(e))
