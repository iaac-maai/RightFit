# -*- coding: utf-8 -*-
"""From the site to Revit (spec/features/revit_link.md §9): while Revit is open and linked, a background thread asks
RightFit online every few seconds whether a message waits for this person ("Preview in Revit" on the Fit check page).
A message is run through Revit's external event, the only safe way into the model from outside a button, and draws the
set in the pump's place, as Next Option does; Revit then answers the site and sends the check.

Started once per Revit session by the extension's startup.py, and again by Online after linking. Nothing here may stop
Revit: the thread catches everything, and a reload of pyRevit stops the previous thread before starting a new one."""
import threading

import clr
clr.AddReference("System")
from System import AppDomain
from System.Threading import ManualResetEvent

from Autodesk.Revit.UI import ExternalEvent, IExternalEventHandler

import rf_online_core as core
import rf_setup

SLOT = "RightFit.listener.stop"  # where the running thread's stop signal is kept, across pyRevit reloads


class _Quiet(object):
    """A report that prints nothing: a message from the site has no pyRevit window to print into."""
    def print_html(self, *a, **k):
        pass

    def print_md(self, *a, **k):
        pass


def _answer(command, ok, message):
    try:
        import rf_online
        rf_online.call("POST", "/api/revit/commands/{}".format(command["id"]), {"ok": ok, "message": message},
                       token=rf_online.token(), timeout_s=10)
    except Exception:
        pass


def _preview(uiapp, command):
    """Draw the message's set in the pump's place. Returns (ok, message for the site)."""
    import rf_app
    import rf_online
    uidoc = uiapp.ActiveUIDocument
    doc = uidoc.Document if uidoc is not None else None
    settings = rf_setup.settings()
    why = core.why_not(settings, command, have_model=doc is not None)
    if why:
        return False, why
    try:
        rf_online.get_data(command["projectId"])  # the pump sets as the site has them now
    except Exception:
        pass  # the last copy, then the project folder's
    pump = rf_app.remembered_pump(doc)
    if pump is None:
        pumps = rf_app.pumps_in(doc)
        if len(pumps) != 1:
            return False, (u"Revit doesn't know which pump set to use: run Check Pump once in Revit."
                           if pumps else u"Revit found no pump set in the open model.")
        pump = pumps[0]
    g = rf_app.gather(doc, pump)
    if g["room"] is None:
        return False, u"No Room or Space around the pump set in the open model."
    s = core.find_set(g["sets"], command["setId"])
    if s is None:
        return False, u"This pump set is not in Revit's copy of the project's sets: Online › Get project data."
    res = rf_app.preview(doc, uidoc, g, s)
    st = rf_setup.state()
    st.update({"pump": pump.UniqueId, "index": g["sets"].index(s)})
    rf_setup.save_state(st)
    try:
        rf_online.after_check(_Quiet(), doc, g, res, "preview")  # the check, with its picture, back to the page
    except Exception:
        pass
    return True, core.shown_text(u"{} {}".format(s.get("maker", u""), s.get("model", u"")).strip(), res)


class _Handler(IExternalEventHandler):
    def __init__(self):
        self.waiting = []
        self.lock = threading.Lock()

    def put(self, command):
        with self.lock:
            self.waiting.append(command)

    def Execute(self, uiapp):
        while True:
            with self.lock:
                command = self.waiting.pop(0) if self.waiting else None
            if command is None:
                return
            try:
                ok, message = _preview(uiapp, command)
            except Exception as e:
                ok, message = False, u"Revit could not draw it: {}".format(e)
            _answer(command, ok, message)

    def GetName(self):
        return "RightFit online"


def _listen(stop, handler, event):
    """The background thread: ask the site for a message, hand it to Revit, wait, again."""
    import rf_online
    wait_s = 4
    while not stop.WaitOne(int(wait_s * 1000)):
        try:
            if not core.link().get("token") or not core.linked_project(rf_setup.settings()):
                wait_s = 10  # not linked: look again later, in case it gets linked
                continue
            status, a = rf_online.call("GET", "/api/revit/commands", token=rf_online.token(), timeout_s=8)
            wait_s = a.get("interval", 4) if status == 200 else 30
            if status == 200 and a.get("command"):
                handler.put(a["command"])
                event.Raise()
        except BaseException:
            wait_s = 15  # offline, or anything else: never let it reach Revit
        except:  # noqa: E722  (.NET exceptions)
            wait_s = 15


def start():
    """Start listening, on Revit's main thread (an external event can only be made there). A previous listener, from
    before a pyRevit reload, is stopped first. Returns True when a listener runs."""
    try:
        old = AppDomain.CurrentDomain.GetData(SLOT)
        if old is not None:
            old.Set()
        stop = ManualResetEvent(False)
        handler = _Handler()
        event = ExternalEvent.Create(handler)
        t = threading.Thread(target=_listen, args=(stop, handler, event), name="RightFit online")
        t.daemon = True
        t.start()
        AppDomain.CurrentDomain.SetData(SLOT, stop)
        return True
    except Exception:
        return False
