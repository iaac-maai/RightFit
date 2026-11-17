# -*- coding: utf-8 -*-
"""What the buttons do: check the pump in its room, preview a candidate in its place, swap it in, and
report. The checks themselves are in checks/space/space_checks.py; this file only moves data between Revit
and them, and draws the results."""
from __future__ import division
import datetime
import io
import os

from Autodesk.Revit.DB import (BuiltInCategory, BuiltInParameter, CategorySet, DirectShape, ElementId,
                               ExternalDefinitionCreationOptions, FamilyInstance, FamilySymbol,
                               FilteredElementCollector, Transaction, TransactionGroup)
from Autodesk.Revit.UI.Selection import ISelectionFilter, ObjectType
from System.Collections.Generic import List

import rf_draw
import rf_model
import rf_project
import rf_setup
from rf_model import eid
from space_checks import fit, load_rules, swap as swap_checks, table

PARAMS = [u"RightFit verdict", u"RightFit set", u"RightFit checked on"]
COLOUR_MD = {"FAIL": "red", "flag": "darkorange", "unclear": "gray", "info": "gray", "pass": "green",
             "would pass": "green"}


# ---------------------------------------------------------------- picking the pump

class PumpFilter(ISelectionFilter):
    def AllowElement(self, el):
        try:
            if rf_model.name_of(el).startswith(u"RF "):
                return False  # RightFit's own preview drawing, not a pump
            return el.Category is not None and eid(el.Category.Id) in [int(c) for c in rf_model.PUMP_CATEGORIES]
        except Exception:
            return False

    def AllowReference(self, ref, point):
        return False


def clear_drawing(doc):
    """Remove RightFit's previews and show the pump again, so the architect clicks the real pump."""
    st = rf_setup.state()
    t = Transaction(doc, u"RightFit: clear")
    t.Start()
    rf_draw.clear(doc, st.get("hidden", []))
    t.Commit()
    st["hidden"] = []
    rf_setup.save_state(st)


def pick_pump(uidoc):
    """The selected pump, or ask the architect to click one."""
    doc = uidoc.Document
    for i in uidoc.Selection.GetElementIds():
        el = doc.GetElement(i)
        if PumpFilter().AllowElement(el):
            return el
    ref = uidoc.Selection.PickObject(ObjectType.Element, PumpFilter(), "RightFit: click the pump set")
    return doc.GetElement(ref.ElementId)


def remembered_pump(doc):
    uid = rf_setup.state().get("pump")
    try:
        el = doc.GetElement(uid) if uid else None
    except Exception:
        el = None
    return el if el is not None and el.IsValidObject else None


# ---------------------------------------------------------------- the data the checks need

def gather(doc, pump):
    """The pump's situation, its room as data, the candidates, which candidate is in the model now,
    the project's service space and circuit."""
    sit = rf_model.Situation(doc, pump)
    room = sit.room_data()
    sets = rf_project.candidates()
    now = rf_project.match(sit.names, sets)
    current = dict(now) if now else {"maker": u"", "model": sit.names[0] if sit.names else u"the pump set"}
    current.update(sit.size)  # the size of what is drawn in the model, measured on its geometry
    current["status"] = now.get("status", "extracted") if now else "extracted"
    current["in_model"] = True
    name, service = rf_project.service()
    proj = rf_project.project()
    circuit = rf_model.circuit_of(pump, proj.get("circuit"))
    return {"sit": sit, "room": room, "sets": sets, "current": current, "current_id": now.get("id") if now else None,
            "service_name": name, "service": service, "circuit": circuit}


# ---------------------------------------------------------------- drawing a candidate in the pump's place

def _draw_results(painter, res):
    """Service space in translucent teal, clashes in red (blocking) or amber."""
    for where, z in res["zones"]:
        painter.boxes([z], u"RF service space " + where, rf_draw.TEAL, 80)
    for r in res["results"]:
        if r["boxes"]:
            blocking = r["would_be"] == "flag" and r["blocking"]
            painter.boxes(r["boxes"], u"RF clash " + r["check"], (207, 58, 46) if blocking else (201, 138, 18), 20)


def _base(painter, res, base_z):
    """A thin pad under the set in the verdict colour (the plinth, when the set stands on one)."""
    b = res["body"]
    top = max(base_z, 15)
    painter.boxes([[b[0] - 40, b[1] - 40, b[2] + 40, b[3] + 40, 0, top]], u"RF verdict pad",
                  rf_draw.COLOURS[res["verdict"]["verdict"]])


def preview(doc, uidoc, g, s, shape_note=None):
    """Show set s in the pump's place without touching the pump: the maker's family when we have it,
    otherwise the stand-in. Returns the checks' results."""
    sit, room = g["sit"], g["room"]
    st = rf_setup.state()
    t = Transaction(doc, u"RightFit: preview " + s.get("model", u""))
    t.Start()
    rf_draw.clear(doc, st.get("hidden", []))
    v3 = rf_draw.view3d(doc)
    painter = rf_draw.Painter(doc, sit.frame, [v3])
    is_current = s is g["current"] or (s.get("id") is not None and s.get("id") == g["current_id"])
    s = dict(s)
    path, entry = rf_project.family_file(s)
    inst = None
    if is_current:
        s.update(sit.size)
        s["shape"] = u"the set in the model, measured on its geometry"
    elif path:
        sym = rf_draw.load_symbol(doc, path, entry.get("type"))
        if sym is not None:
            inst, b = rf_draw.place_family(doc, sym, sit.frame, s, sit.base_z, _level(doc, sit.pump),
                                           float(entry.get("rotate", 0)))
            inst.get_Parameter(BuiltInParameter.ALL_MODEL_INSTANCE_COMMENTS).Set(rf_draw.PREVIEW)
            s["L"], s["W"], s["H"] = b[2] - b[0], b[3] - b[1], b[5] - b[4]
            s["shape"] = u"the maker's Revit family: " + os.path.basename(path)
    if not is_current and inst is None:
        s["shape"] = u"a stand-in drawn from the catalogue sizes (add the maker's .rfa to the project's families " \
                     u"folder to see the real set)"
    res = fit(s, room, g["service"], sit.base_z)
    if not is_current:
        ids = List[ElementId]()
        ids.Add(sit.pump.Id)
        try:
            v3.HideElements(ids)
            st["hidden"] = [eid(sit.pump.Id)]
        except Exception:
            pass
        if inst is not None:
            painter.paint(inst, rf_draw.COLOURS[res["verdict"]["verdict"]], lines_only=True)
        else:
            painter.stand_in(s, res["body"])
    _base(painter, res, sit.base_z)
    _draw_results(painter, res)
    rf_draw.frame_view(doc, v3, sit.frame, room["outline"], room["height"],
                       rf_draw.walls_near(doc, sit.frame, room["outline"]))
    t.Commit()
    rf_setup.save_state(st)
    show_view(uidoc, v3)
    return res


def _level(doc, pump):
    """The pump's own level, so a new set goes on the same floor; the lowest level when it has none."""
    try:
        lvl = doc.GetElement(pump.LevelId)
        if lvl is not None:
            return lvl
    except Exception:
        pass
    return rf_draw.lowest_level(doc)


def show_view(uidoc, v3):
    try:
        uidoc.ActiveView = v3
        for uv in uidoc.GetOpenUIViews():
            if eid(uv.ViewId) == eid(v3.Id):
                uv.ZoomToFit()
    except Exception:
        pass


# ---------------------------------------------------------------- the swap

def ensure_parameters(doc):
    """RightFit's three text parameters on mechanical equipment and generic models, from a shared parameter
    file kept beside the settings. Returns False when Revit refuses (the swap still works)."""
    app = doc.Application
    path = os.path.join(rf_setup.HOME, u"RightFit_shared_parameters.txt")
    if not os.path.isdir(rf_setup.HOME):
        os.makedirs(rf_setup.HOME)
    if not os.path.exists(path):
        io.open(path, "w", encoding="utf-8").close()
    old = app.SharedParametersFilename
    try:
        app.SharedParametersFilename = path
        dfile = app.OpenSharedParameterFile()
        group = dfile.Groups.get_Item(u"RightFit") or dfile.Groups.Create(u"RightFit")
        cats = CategorySet()
        for c in (BuiltInCategory.OST_MechanicalEquipment, BuiltInCategory.OST_GenericModel):
            cats.Insert(doc.Settings.Categories.get_Item(c))
        from Autodesk.Revit.DB import SpecTypeId, GroupTypeId
        for name in PARAMS:
            d = group.Definitions.get_Item(name)
            if d is None:
                d = group.Definitions.Create(ExternalDefinitionCreationOptions(name, SpecTypeId.String.Text))
            if not doc.ParameterBindings.Contains(d):
                doc.ParameterBindings.Insert(d, app.Create.NewInstanceBinding(cats), GroupTypeId.General)
        return True
    except Exception:
        return False
    finally:
        if old:
            app.SharedParametersFilename = old


def _set_text(el, name, value):
    p = el.LookupParameter(name)
    if p is not None and not p.IsReadOnly:
        p.Set(value)


def _type_for(doc, pump, s):
    """A type of the pump's own family that names the candidate's model, if the family holds the range."""
    if not isinstance(pump, FamilyInstance):
        return None
    code = rf_project._norm(s.get("model"))
    fam = pump.Symbol.Family
    for i in fam.GetFamilySymbolIds():
        sym = doc.GetElement(i)
        names = rf_model.names_of(sym, doc) + [rf_model.name_of(sym)]
        if code and code in rf_project._norm(u" ".join(names)):
            return sym
    return None


def swap(doc, uidoc, g, s):
    """Put set s in the pump's place. One Undo in Revit puts everything back (a transaction group).
    Returns (results, message)."""
    sit, room = g["sit"], g["room"]
    old = sit.pump
    path, entry = rf_project.family_file(s)
    same_family_type = _type_for(doc, old, s)
    stand_in_ok = isinstance(old, DirectShape)  # a RightFit test room's stand-in may become another stand-in
    if not (path or same_family_type or stand_in_ok):
        return None, (u"No Revit family for {} {}: add the maker's .rfa to the project's families folder. "
                      u"RightFit doesn't replace a real family with a stand-in.".format(s["maker"], s["model"]))
    pipes = list(room.get("pipes", []))
    st = rf_setup.state()
    tg = TransactionGroup(doc, u"RightFit: swap to {} {}".format(s["maker"], s["model"]))
    tg.Start()
    t = Transaction(doc, u"RightFit: place the new set")
    t.Start()
    rf_draw.clear(doc, st.get("hidden", []))
    st["hidden"] = []
    params_ok = ensure_parameters(doc)
    new_s = dict(s)
    mark = old.get_Parameter(BuiltInParameter.ALL_MODEL_MARK)
    mark = mark.AsString() if mark is not None else None
    note = old.get_Parameter(BuiltInParameter.ALL_MODEL_INSTANCE_COMMENTS)
    note = note.AsString() if note is not None else None
    painter = rf_draw.Painter(doc, sit.frame, [rf_draw.view3d(doc)])
    if same_family_type is not None and not path:
        if not same_family_type.IsActive:
            same_family_type.Activate()
        old.ChangeTypeId(same_family_type.Id)
        doc.Regenerate()
        new = old
        b = rf_model.local_box(rf_model.geometry_points(new), sit.frame)
        how = u"changed the type to " + rf_model.name_of(same_family_type)
    elif path:
        sym = rf_draw.load_symbol(doc, path, entry.get("type"))
        new, b = rf_draw.place_family(doc, sym, sit.frame, s, sit.base_z, _level(doc, sit.pump),
                                      float(entry.get("rotate", 0)))
        how = u"placed the maker's family " + os.path.basename(path)
    else:
        body, _ = rf_model.space_checks.body_and_zones(s, {}, sit.base_z)
        new, b = painter.stand_in_single(s, body, u"RFT pump - ", BuiltInCategory.OST_MechanicalEquipment), body
        how = u"placed a stand-in (test room)"
    new_s["L"], new_s["W"], new_s["H"] = b[2] - b[0], b[3] - b[1], b[5] - b[4]
    res = swap_checks(new_s, g["current"], room, g["service"], pipes, g["circuit"], sit.base_z, sit.size)
    if new is not old:
        if mark and not isinstance(new, DirectShape):
            p = new.get_Parameter(BuiltInParameter.ALL_MODEL_MARK)
            if p is not None and not p.IsReadOnly:
                p.Set(mark)
        p = new.get_Parameter(BuiltInParameter.ALL_MODEL_INSTANCE_COMMENTS)
        if p is not None and not p.IsReadOnly:
            p.Set(note or u"")
        doc.Delete(old.Id)
    if params_ok:
        _set_text(new, PARAMS[0], res["verdict"]["verdict"] + (u"" if res["verdict"]["confirmed"]
                                                               else u" (on unconfirmed values)"))
        _set_text(new, PARAMS[1], u"{} {}".format(s["maker"], s["model"]))
        _set_text(new, PARAMS[2], datetime.date.today().isoformat())
    _draw_results(painter, res)
    t.Commit()
    tg.Assimilate()
    st["pump"] = new.UniqueId
    st["index"] = -1
    rf_setup.save_state(st)
    msg = how + (u"" if params_ok else u"; RightFit's parameters could not be added, so the verdict is not "
                                       u"written into the element")
    return res, msg


# ---------------------------------------------------------------- the report

def report(out, g, res, title, note=None):
    rules = load_rules()
    s = res["set"]
    out.print_md(u"## {}".format(title))
    room = g["room"]
    out.print_md(u"Room **{}** ({}) · height {:.0f} mm · {} door(s) · {} things in the room · {} pipe end(s) at "
                 u"the pump · service space **{}**".format(room["name"], room["kind"], room["height"],
                                                           len(room["doors"]), len(room["obstacles"]),
                                                           len(room["pipes"]), g["service_name"]))
    out.print_md(u"{:.0f} x {:.0f} x {:.0f} mm · {} kg · {} pumps · data from: {} ({})".format(
        s["L"], s["W"], s["H"], s.get("kg", u"?"), s.get("pumps", u"?"), s.get("source", u"the model"),
        s.get("status", "extracted")))
    if s.get("shape"):
        out.print_md(u"Shape in the model: *{}*".format(s["shape"]))
    if note:
        out.print_md(note)
    v = res["verdict"]
    out.print_md(u"### Verdict: <span style='color:{}'>{}</span>{}".format(
        COLOUR_MD.get(v["verdict"], "black"), v["verdict"],
        u"" if v["confirmed"] else u" — on values not yet confirmed: it is what the check would say"))
    rows = []
    for r in res["results"]:
        shown = r["result"] if r["result"] == r["would_be"] else u"{} (would be {})".format(r["result"], r["would_be"])
        rule_txt = u", ".join(u"{} ({})".format(i, rules[i]["status"]) if i in rules else i for i in r["rules"])
        rows.append([u"<span style='color:{}'>{}</span>".format(COLOUR_MD.get(r["would_be"], "black"), shown),
                     r["check"], r["reason"], rule_txt])
    out.print_table(rows, columns=["Result", "Check", "Finding", "Rule (status)"])
    out.print_md(u"*RightFit does not certify. Rules marked to_confirm wait for the engineer's approval. "
                 u"Not checked: pipe routes beyond the pump, the structure, noise, anything not drawn in the model.*")


def candidates_table(out, g):
    rows = table(g["sets"], g["room"], g["service"], g["sit"].base_z)
    out.print_md(u"### All candidates in this room (service space {})".format(g["service_name"]))
    out.print_table(rows, columns=["#", "Verdict", "Set", "L x W x H mm (catalogue)", "Blocking", "To look at"])
