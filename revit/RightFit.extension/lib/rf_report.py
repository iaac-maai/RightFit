# -*- coding: utf-8 -*-
"""What the report says about the room and the pump set, laid out so it can't be missed: a summary box at
the top, then a table for the room and a table for the set. Plain Python with no Revit inside, so the tests
run it on Python 3 and Revit runs it on IronPython 2.7.

Values come only from the model and candidates.json. A value neither gives is shown as "not given", never
filled in."""
from __future__ import division
import math

NOT_GIVEN = u"<span style='color:#888'>not given</span>"
STATUS_COLOUR = {"verified": "#1a7f37", "model": "#1a7f37", "extracted": "#b35900", "unclear": "#888"}


def _n(v, unit=u"", digits=0):
    """A number with its unit, or 'not given'."""
    if v is None or v == u"":
        return NOT_GIVEN
    try:
        f = float(v)
    except (TypeError, ValueError):
        return u"{}".format(v)
    txt = u"{:,.{}f}".format(f, digits).replace(u",", u" ")
    return txt + (u" " + unit if unit else u"")


def _yes_no(v, yes=u"yes", no=u"no"):
    if v is None or v == u"":
        return NOT_GIVEN
    if isinstance(v, bool):
        return yes if v else no
    return {"pass": u"yes (pass)", "fail": u"<b style='color:#c62828'>no (fail)</b>"}.get(v, u"{}".format(v))


def _status(st):
    st = st or u"extracted"
    note = {"extracted": u" — read from the documents, not yet checked by a person",
            "verified": u" — checked by a person against the source",
            "model": u" — from the Revit model"}.get(st, u"")
    return u"<b style='color:{}'>{}</b>{}".format(STATUS_COLOUR.get(st, "black"), st, note)


def floor_size(outline):
    """Length, width (mm) and area (m2) of a floor outline given as [[x, y], ...] in mm. Length and width are
    the sides of the smallest rectangle around the outline, so a rectangular room gives its own sides
    whichever way it is turned; length is the longer side."""
    pts = [(float(p[0]), float(p[1])) for p in outline or []]
    if len(pts) < 3:
        return None, None, None
    area = 0.0
    for i in range(len(pts)):
        x1, y1 = pts[i]
        x2, y2 = pts[(i + 1) % len(pts)]
        area += x1 * y2 - x2 * y1
    area = abs(area) / 2 / 1e6
    best = None
    for i in range(len(pts)):
        x1, y1 = pts[i]
        x2, y2 = pts[(i + 1) % len(pts)]
        if (x1, y1) == (x2, y2):
            continue
        a = math.atan2(y2 - y1, x2 - x1)
        c, s = math.cos(a), math.sin(a)
        us = [x * c + y * s for x, y in pts]
        vs = [-x * s + y * c for x, y in pts]
        du, dv = max(us) - min(us), max(vs) - min(vs)
        if best is None or du * dv < best[0] * best[1] - 1e-6:
            best = (du, dv)
    length, width = max(best), min(best)
    return length, width, area


def _box_size(box):
    """L x W x H of a box [x0, y0, x1, y1, z0, z1] in mm, as text."""
    try:
        return u"{:.0f} x {:.0f} x {:.0f} mm".format(abs(box[2] - box[0]), abs(box[3] - box[1]),
                                                    abs(box[5] - box[4]))
    except (TypeError, IndexError):
        return NOT_GIVEN


def room_rows(room, service_name=None, service=None, circuit=None):
    """Rows [what, value] for the room table. The first row (the room) is the table's header bar."""
    length, width, area = floor_size(room.get("outline"))
    h = room.get("height")
    rows = [
        [u"Room", u"<b>{}</b> ({})".format(room.get("name") or u"unnamed", room.get("kind") or u"room")],
        [u"Length", _n(length, u"mm")],
        [u"Width", _n(width, u"mm")],
        [u"Height", _n(h, u"mm")],
        [u"Floor area", _n(area, u"m²", 2)],
        [u"Volume", _n(area * h / 1000 if area is not None and h else None, u"m³", 1)],
    ]
    doors = room.get("doors") or []
    rows.append([u"Doors ({})".format(len(doors)),
                 u"<br>".join(u"{}: {:.0f} mm wide x {:.0f} mm high".format(d.get("name", u"door"), d["width"],
                                                                          d["height"]) for d in doors)
                 or u"<b style='color:#c62828'>none found</b>"])
    things = room.get("obstacles") or []
    rows.append([u"Things in the room ({})".format(len(things)),
                 u"<br>".join(u"{}: {}".format(o.get("name", u"?"), _box_size(o.get("box"))) for o in things)
                 or u"nothing else"])
    pipes = room.get("pipes") or []
    rows.append([u"Pipe ends at the pump ({})".format(len(pipes)),
                 u"<br>".join(u"{}{}".format(p.get("name", u"a pipe"), u" ({})".format(p["role"]) if p.get("role")
                                             else u"") for p in pipes) or u"none drawn in the model"])
    if service:
        rows.append([u"Service space kept around the set",
                     u"<b>{}</b>: front {}, sides {}, back {}, top {}".format(
                         service_name or u"", _n(service.get("front"), u"mm"), _n(service.get("sides"), u"mm"),
                         _n(service.get("back"), u"mm"), _n(service.get("top"), u"mm"))])
    if circuit:
        rows.append([u"Electrical circuit",
                     u"{} · {} · {}".format(circuit.get("name") or NOT_GIVEN, _n(circuit.get("rating_a"), u"A", 1),
                                           _status(circuit.get("status")))])
    return rows


def pump_rows(s, catalogue=None):
    """Rows [what, value] for the pump set table. s is the set as checked (its sizes may be measured in the
    model); catalogue is the same set as in candidates.json, for the data sheet's sizes. The first row (the
    set's name) is the table's header bar."""
    cat = catalogue or {}
    rows = [
        [u"Pump set", u"{} {}".format(s.get("maker") or u"", s.get("model") or u"").strip() or NOT_GIVEN],
        [u"Maker", u"<b>{}</b>".format(s.get("maker")) if s.get("maker") else NOT_GIVEN],
        [u"Model", u"<b>{}</b>".format(s.get("model")) if s.get("model") else NOT_GIVEN],
        [u"Submitted or alternative", u"the submitted set" if s.get("submitted") else u"an alternative"
            if cat else u"not in the candidates list"],
        [u"Size (length x depth x height)", u"<b>{} x {} x {}</b>".format(_n(s.get("L")), _n(s.get("W")),
                                                                        _n(s.get("H"), u"mm"))],
    ]
    if cat and any(cat.get(k) is not None and s.get(k) is not None and abs(float(cat[k]) - float(s[k])) >= 1
                   for k in ("L", "W", "H")):
        rows.append([u"Size on the data sheet", u"{} x {} x {}".format(_n(cat.get("L")), _n(cat.get("W")),
                                                                      _n(cat.get("H"), u"mm"))])
    rows += [
        [u"Weight", _n(s.get("kg"), u"kg", 1)],
        [u"Number of pumps", _n(s.get("pumps"))],
        [u"Motor power, each pump", _n(s.get("p2_each"), u"kW", 2)],
        [u"Power the duty needs", _n(s.get("p2_needed"), u"kW", 3)],
        [u"One pump carries the duty alone (standby)", _yes_no(s.get("standby"))],
        [u"Inlet / outlet pipe size", u"DN {} / DN {}".format(_n(s.get("dn_in")), _n(s.get("dn_out")))],
        [u"Drinking-water approval in the package", _yes_no(s.get("dw_approval"))],
        [u"Data from", s.get("source") or u"the model"],
        [u"Status of these values", _status(s.get("status"))],
    ]
    if s.get("shape"):
        rows.append([u"Shape in the model", s["shape"]])
    return rows


def summary_html(room, s):
    """A highlighted box at the top of the report: the room's and the set's main sizes in large type."""
    length, width, area = floor_size(room.get("outline"))
    def m(v):
        return u"{:.2f}".format(v / 1000) if v else u"?"
    room_txt = u"Room <b>{}</b>: {} x {} m floor, {} m high{}".format(
        room.get("name") or u"", m(length), m(width), m(room.get("height")),
        u" ({:.1f} m²)".format(area) if area else u"")
    pump_txt = u"Pump set <b>{} {}</b>: {} x {} x {} mm, {} kg, {} pumps".format(
        s.get("maker", u""), s.get("model", u""),
        *[u"{:.0f}".format(s[k]) if s.get(k) is not None else u"?" for k in ("L", "W", "H")]
        + [u"{:g}".format(s["kg"]) if s.get("kg") is not None else u"?",
           s.get("pumps") if s.get("pumps") is not None else u"?"])
    style = (u"border:2px solid #1565c0;background:#e3f2fd;border-radius:6px;padding:10px 14px;"
             u"margin:8px 0;font-size:15px;line-height:1.6;color:#0d2a4a")
    return u"<div style='{}'>{}<br>{}</div>".format(style, room_txt, pump_txt)
