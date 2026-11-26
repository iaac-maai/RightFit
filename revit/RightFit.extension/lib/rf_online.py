# -*- coding: utf-8 -*-
"""The Revit link's talking part (spec/features/revit_link.md): linking this computer, getting the project's data from
RightFit online, sending each check, with its picture. HTTP through .NET, as pyRevit's Python 2.7 has no reliable HTTPS
of its own; no new dependency. Everything that can be tested without Revit is in rf_online_core.py."""
from __future__ import division
import base64
import io
import json
import os
import tempfile
import time

import clr
clr.AddReference("System")
from System import Environment, Uri
from System.Diagnostics import Process
from System.IO import StreamReader
from System.Net import HttpWebRequest, ServicePointManager, SecurityProtocolType, WebException
from System.Text import Encoding

import rf_online_core as core
import rf_setup
from space_checks import load_rules, table

ServicePointManager.SecurityProtocol = ServicePointManager.SecurityProtocol | SecurityProtocolType.Tls12


class Offline(Exception):
    """The site could not be reached (no internet, or it did not answer in time)."""


def computer():
    try:
        return Environment.MachineName
    except Exception:
        return u"A computer with Revit"


def call(method, path, body=None, token=None, timeout_s=12):
    """One request to the site. Returns (status, answer as a dict). Raises Offline when it can't be reached."""
    lk = core.link()
    req = HttpWebRequest.Create(Uri(lk["url"].rstrip(u"/") + path))
    req.Method = method
    req.Timeout = int(timeout_s * 1000)
    req.ReadWriteTimeout = int(timeout_s * 1000)
    req.Accept = "application/json"
    req.UserAgent = "RightFit-Revit/1"
    if token:
        req.Headers.Add("Authorization", "Bearer " + token)
    if body is not None:
        data = Encoding.UTF8.GetBytes(json.dumps(body, ensure_ascii=False))
        req.ContentType = "application/json; charset=utf-8"
        req.ContentLength = data.Length
        stream = req.GetRequestStream()
        stream.Write(data, 0, data.Length)
        stream.Close()
    try:
        resp = req.GetResponse()
    except WebException as e:
        resp = e.Response
        if resp is None:
            raise Offline(str(e.Message))
    try:
        status = int(resp.StatusCode)
        text = StreamReader(resp.GetResponseStream(), Encoding.UTF8).ReadToEnd()
    finally:
        resp.Close()
    try:
        return status, json.loads(text) if text else {}
    except ValueError:
        return status, {"error": u"The site answered something RightFit can't read ({}).".format(status)}


def token():
    return core.link().get("token")


def linked():
    return bool(token())


# ---------------------------------------------------------------- linking this computer (device sign-in)

def start_link():
    """Ask for a link. Returns the site's answer: userCode, deviceCode, url, expiresIn, interval."""
    status, a = call("POST", "/api/revit/link/start", {"computer": computer()})
    if status != 201:
        raise Exception(a.get("error") or u"The site refused to start a link ({}).".format(status))
    return a


def open_page(url):
    try:
        Process.Start(url)
    except Exception:
        pass


def finish_link(device_code, wait_s=30, interval_s=3):
    """Ask whether the link was approved, for up to wait_s. Returns (state, message); keeps the token when approved."""
    deadline = time.time() + wait_s
    while True:
        status, a = call("POST", "/api/revit/link/poll", {"deviceCode": device_code})
        if status == 200 and a.get("token"):
            lk = core.link()
            lk.update({"token": a["token"], "user": a.get("user"), "computer": computer()})
            core.save_link(lk)
            u = a.get("user") or {}
            return "approved", u"Linked to RightFit online as {} ({}).".format(u.get("name", u""), u.get("email", u""))
        if status != 202:
            return a.get("state") or "error", a.get("error") or u"The site answered {}.".format(status)
        if time.time() >= deadline:
            return "pending", u"Not approved yet. Approve the code on the site, then click Connect again."
        time.sleep(interval_s)


def disconnect():
    core.forget_link()


def me():
    status, a = call("GET", "/api/revit/me", token=token())
    if status == 401:
        core.forget_link()
    if status != 200:
        raise Exception(a.get("error") or u"The site answered {}.".format(status))
    return a


# ---------------------------------------------------------------- the project's data

def get_data(online_id):
    """The project's pump sets, settings and the reviewers' choice from the site, kept as this computer's copy."""
    status, a = call("GET", "/api/revit/projects/{}/fitcheck".format(online_id), token=token(), timeout_s=8)
    if status != 200:
        raise Exception(a.get("error") or u"The site answered {}.".format(status))
    core.save_cache(online_id, a)
    return a


def send_data(online_id, candidates, project):
    status, a = call("POST", "/api/revit/projects/{}/fitcheck/data".format(online_id),
                     {"candidates": candidates, "project": project}, token=token(), timeout_s=20)
    if status != 200:
        raise Exception(a.get("error") or u"The site answered {}.".format(status))
    return a


# ---------------------------------------------------------------- checks

def picture(doc, view, width=1400):
    """The RightFit 3D view as a PNG, in base64, or None (a check goes without its picture rather than not at all)."""
    try:
        from Autodesk.Revit.DB import (ElementId, ExportRange, ImageExportOptions, ImageFileType, ImageResolution,
                                       ZoomFitType)
        from System.Collections.Generic import List
        folder = tempfile.mkdtemp(prefix="rightfit-")
        opts = ImageExportOptions()
        opts.ExportRange = ExportRange.SetOfViews
        ids = List[ElementId]()
        ids.Add(view.Id)
        opts.SetViewsAndSheets(ids)
        opts.FilePath = os.path.join(folder, "check")
        opts.ZoomType = ZoomFitType.FitToPage
        opts.PixelSize = width
        opts.HLRandWFViewsFileType = ImageFileType.PNG
        opts.ShadowViewsFileType = ImageFileType.PNG
        opts.ImageResolution = ImageResolution.DPI_150
        doc.ExportImage(opts)
        pngs = [os.path.join(folder, n) for n in os.listdir(folder) if n.lower().endswith(".png")]
        if not pngs:
            return None
        with io.open(pngs[0], "rb") as f:
            data = f.read()
        for p in pngs:
            os.remove(p)
        os.rmdir(folder)
        return base64.b64encode(data).decode("ascii") if len(data) <= 2 * 1024 * 1024 else None
    except Exception:
        return None


def _send(online_id, payload):
    status, a = call("POST", "/api/revit/projects/{}/runs".format(online_id), payload, token=token(), timeout_s=20)
    return status, a


def send_waiting():
    """Send the checks kept on this computer, oldest first. Returns (sent, still waiting)."""
    sent = 0
    items = core.waiting()
    for path, online_id, payload in items:
        try:
            status, a = _send(online_id, payload)
        except Offline:
            break
        if status == 201 or status in (400, 403, 404, 413):  # taken, or never will be: either way it leaves the outbox
            core.done(path)
            sent += 1 if status == 201 else 0
        else:
            break
    return sent, len(core.waiting())


def rightfit_view(doc):
    """The RightFit 3D view the preview drew in, or None."""
    from Autodesk.Revit.DB import FilteredElementCollector, View3D
    import rf_draw
    for v in FilteredElementCollector(doc).OfClass(View3D):
        if not v.IsTemplate and v.Name == rf_draw.VIEW3D:
            return v
    return None


def after_check(out, doc, g, res, action, view=None):
    """Send one check to the project's online space, when this project folder is linked, and say so in the report;
    show the set the reviewers chose. Never stops the check: without the site, the check waits on this computer."""
    online = core.linked_project(rf_setup.settings())
    if not online or not linked():
        return
    rules = load_rules()
    cands = None
    if action == "check" and g.get("sets"):
        try:
            cands = [[u"{}".format(c) for c in row] for row in table(g["sets"], g["room"], g["service"], g["sit"].base_z)]
        except Exception:
            cands = None
    payload = core.run_payload(action, g["room"], res, rules, model_file=doc.Title, candidates=cands, computer=computer())
    view = view or rightfit_view(doc)
    img = picture(doc, view) if view is not None else None
    if img:
        payload["image"] = img
    note, chosen = u"", None
    try:
        send_waiting()
        status, a = _send(online["id"], payload)
        if status == 201:
            note = u"Sent to RightFit online, project <b>{}</b>.".format(online["name"])
            chosen = a.get("chosen")
        elif status == 401:
            core.forget_link()
            note = u"Not sent: this computer is no longer linked. RightFit › Online › Connect this computer."
        else:
            note = u"Not sent: {}".format(a.get("error") or status)
    except Offline:
        payload.pop("image", None)  # the outbox keeps the check, not the picture
        core.keep_for_later(online["id"], payload)
        note = u"RightFit online can't be reached: the check is kept on this computer and sent with the next one."
        chosen = (core.cached(online["id"], u"chosen.json") or {}).get("chosen")
    line = core.chosen_text(chosen)
    style = (u"border:2px solid #2e7d32;background:#edf7ee;border-radius:6px;padding:8px 12px;margin:8px 0;"
             u"font-size:14px;line-height:1.6;color:#1b3a1e")
    out.print_html(u"<div style='{}'>{}{}</div>".format(style, note, u"<br>" + line if line else u""))
