# -*- coding: utf-8 -*-
"""A test room built from project.json, for trying RightFit without the project's own model: walls, a Revit
Room, a door, the fixed equipment as plain boxes, any pipes the file lists, and the pump set in the model
(the maker's family, or a stand-in). Every value comes from the file, which says where it comes from.

Everything it builds is named "RFT ..." so it can be told apart from the project's own elements."""
from __future__ import division

from Autodesk.Revit.DB import (BuiltInCategory, BuiltInParameter, ElementTypeGroup, FamilySymbol,
                               FilteredElementCollector, Level, Line, Transaction, UV, Wall, XYZ)
from Autodesk.Revit.DB.Plumbing import Pipe, PipeType, PipingSystemType
from Autodesk.Revit.DB.Structure import StructuralType

import rf_draw
import rf_model
import rf_project
from rf_model import ft

CATEGORIES = {"PlumbingFixtures": BuiltInCategory.OST_PlumbingFixtures,
              "MechanicalEquipment": BuiltInCategory.OST_MechanicalEquipment,
              "GenericModel": BuiltInCategory.OST_GenericModel}


class _WorldFrame(object):
    """The world itself as a frame, so rf_draw can build boxes in room coordinates (mm)."""

    def __init__(self):
        self.origin = XYZ(0, 0, 0)
        self.x, self.y = XYZ.BasisX, XYZ.BasisY

    def world(self, x, y, z):
        return XYZ(ft(x), ft(y), ft(z))

    def vector(self, v):
        return rf_model.Frame(XYZ(0, 0, 0), XYZ.BasisX, 0).vector(v)


def build(doc, tr_room):
    """Build the test room. Returns a list of notes for the report (what could not be built)."""
    notes = []
    lvl = sorted(FilteredElementCollector(doc).OfClass(Level), key=lambda l: l.Elevation)[0]
    X, Y, H = tr_room["x"], tr_room["y"], tr_room["height"]
    t2 = tr_room.get("wall", 200) / 2
    t = Transaction(doc, u"RightFit: build the test room")
    rf_draw.accept_warnings(t)
    t.Start()
    try:
        _build(doc, tr_room, t, lvl, notes)
    except Exception:
        if t.HasStarted() and not t.HasEnded():
            t.RollBack()
        raise
    return notes


def _remove_old(doc, name):
    """Delete a test room built before, so building again replaces it instead of doubling it."""
    from Autodesk.Revit.DB import DirectShape, FamilyInstance, SpatialElement
    old = []
    for e in FilteredElementCollector(doc).OfClass(DirectShape):
        if rf_model.name_of(e).startswith(u"RFT ") or rf_model.name_of(e).startswith(u"RF "):
            old.append(e.Id)
    for cls in (Wall, FamilyInstance, DirectShape):
        for e in FilteredElementCollector(doc).OfClass(cls):
            p = e.get_Parameter(BuiltInParameter.ALL_MODEL_INSTANCE_COMMENTS)
            note = (p.AsString() or u"") if p is not None else u""
            if note.startswith(u"RFT") or note.startswith(u"front:"):  # front: marks older stand-in pumps
                old.append(e.Id)
    for e in FilteredElementCollector(doc).OfClass(SpatialElement):
        p = e.get_Parameter(BuiltInParameter.ALL_MODEL_INSTANCE_COMMENTS)
        n = e.get_Parameter(BuiltInParameter.ROOM_NAME)
        if (p is not None and (p.AsString() or u"") == u"RFT room") or (n is not None and n.AsString() == name):
            old.append(e.Id)
    from Autodesk.Revit.DB import ImportInstance
    import os
    fam = os.path.join(rf_project.folder() or u"", u"families")
    ours = set(n.lower() for n in os.listdir(fam)) if os.path.isdir(fam) else set()
    for e in FilteredElementCollector(doc).OfClass(ImportInstance):  # our maker drawings left by an earlier try
        try:
            if e.Category is not None and e.Category.Name.lower() in ours:
                e.Pinned = False
                old.append(e.Id)
        except Exception:
            pass
    for i in old:
        try:
            doc.Delete(i)
        except Exception:
            pass  # already gone with its host
    return len(old)


def _build(doc, tr_room, t, lvl, notes):
    if _remove_old(doc, tr_room.get("name", u"Test room")):
        notes.append(u"replaced the test room built before")
        doc.Regenerate()
    X, Y, H = tr_room["x"], tr_room["y"], tr_room["height"]
    t2 = tr_room.get("wall", 200) / 2
    wtype = doc.GetDefaultElementTypeId(ElementTypeGroup.WallType)
    walls = {}
    segs = {"south": ((-t2, -t2), (X + t2, -t2)), "east": ((X + t2, -t2), (X + t2, Y + t2)),
            "north": ((X + t2, Y + t2), (-t2, Y + t2)), "west": ((-t2, Y + t2), (-t2, -t2))}
    for side, (a, b) in segs.items():
        ln = Line.CreateBound(XYZ(ft(a[0]), ft(a[1]), 0), XYZ(ft(b[0]), ft(b[1]), 0))
        w = Wall.Create(doc, ln, wtype, lvl.Id, ft(H), 0.0, False, False)
        w.get_Parameter(BuiltInParameter.ALL_MODEL_INSTANCE_COMMENTS).Set(u"RFT wall " + side)
        walls[side] = w
    doc.Regenerate()
    room = doc.Create.NewRoom(lvl, UV(ft(X / 2), ft(Y / 2)))
    room.Name = tr_room.get("name", u"Test room")
    room.get_Parameter(BuiltInParameter.ALL_MODEL_INSTANCE_COMMENTS).Set(u"RFT room")
    try:
        room.get_Parameter(BuiltInParameter.ROOM_UPPER_OFFSET).Set(ft(H))
    except Exception:
        notes.append(u"could not set the room's height; check its upper limit")

    d = tr_room.get("door")
    if d:
        syms = [s for s in FilteredElementCollector(doc).OfClass(FamilySymbol).OfCategory(BuiltInCategory.OST_Doors)]
        if not syms:
            notes.append(u"no door family is loaded in this model, so the room has no door: load one "
                         u"(Insert > Load Family > Doors) and build again")
        else:
            sym = syms[0]
            name = u"RFT {} x {}".format(d["width"], d["height"])
            mine = [s for s in syms if rf_model.name_of(s) == name]
            sym = mine[0] if mine else sym.Duplicate(name)
            for bip in (BuiltInParameter.DOOR_WIDTH, BuiltInParameter.FAMILY_WIDTH_PARAM):
                p = sym.get_Parameter(bip)
                if p is not None and not p.IsReadOnly:
                    p.Set(ft(d["width"]))
                    break
            for bip in (BuiltInParameter.DOOR_HEIGHT, BuiltInParameter.FAMILY_HEIGHT_PARAM):
                p = sym.get_Parameter(bip)
                if p is not None and not p.IsReadOnly:
                    p.Set(ft(d["height"]))
                    break
            if not sym.IsActive:
                sym.Activate()
            mid = (d["from"] + d["to"]) / 2
            at = {"east": XYZ(ft(X + t2), ft(mid), 0), "west": XYZ(ft(-t2), ft(mid), 0),
                  "north": XYZ(ft(mid), ft(Y + t2), 0), "south": XYZ(ft(mid), ft(-t2), 0)}[d["wall"]]
            door = doc.Create.NewFamilyInstance(at, sym, walls[d["wall"]], lvl, StructuralType.NonStructural)
            door.get_Parameter(BuiltInParameter.ALL_MODEL_MARK).Set(d.get("mark", u"D1"))

    painter = rf_draw.Painter(doc, _WorldFrame(), [])
    for f in tr_room.get("fixed", []):
        box = list(f["box"]) + list(f["z"])
        painter.shape([rf_draw.box_solid(painter.frame, box)], u"RFT " + f["name"], (150, 156, 164), 0,
                      CATEGORIES.get(f.get("category"), BuiltInCategory.OST_GenericModel))

    for p in tr_room.get("pipes", []):
        systems = list(FilteredElementCollector(doc).OfClass(PipingSystemType))
        types = list(FilteredElementCollector(doc).OfClass(PipeType))
        if not systems or not types:
            notes.append(u"no pipe types in this model, so the pipes were not drawn")
            break
        pipe = Pipe.Create(doc, systems[0].Id, types[0].Id, lvl.Id, XYZ(*[ft(v) for v in p["from"]]),
                           XYZ(*[ft(v) for v in p["to"]]))
        pipe.get_Parameter(BuiltInParameter.RBS_PIPE_DIAMETER_PARAM).Set(ft(p["dn"]))

    pump = tr_room.get("pump")
    if pump:
        sets = rf_project.candidates()
        s = [c for c in sets if c.get("id") == pump.get("set")] or [c for c in sets if c.get("submitted")]
        if not s:
            notes.append(u"no candidate set to put in the room")
        else:
            s = s[0]
            front = pump.get("front", "+Y")
            xdir = {"+Y": XYZ.BasisX, "-Y": XYZ.BasisX.Negate(), "+X": XYZ.BasisY.Negate(),
                    "-X": XYZ.BasisY}[front]
            frame = rf_model.Frame(XYZ(ft(pump["centre"][0]), ft(pump["centre"][1]), 0), xdir, 0)
            base = pump.get("base_z", 0)
            path, entry = rf_project.family_file(s)
            inst = None
            if path:
                inst, _, what = rf_draw.place_model(doc, path, entry, frame, s, base, lvl, rf_draw.view3d(doc),
                                                    u"RFT pump - {} {}".format(s["maker"], s["model"]),
                                                    BuiltInCategory.OST_MechanicalEquipment)
                if inst is None:
                    notes.append(u"the maker's file could not be used (" + (what or u"") + u"), so a stand-in is drawn")
                elif isinstance(inst, rf_draw.DirectShape):
                    inst.get_Parameter(BuiltInParameter.ALL_MODEL_INSTANCE_COMMENTS).Set(u"RFT pump front:" + front)
                else:
                    inst.get_Parameter(BuiltInParameter.ALL_MODEL_MARK).Set(u"P-01")
                    inst.get_Parameter(BuiltInParameter.ALL_MODEL_INSTANCE_COMMENTS).Set(u"RFT pump")
                if inst is not None:
                    notes.append(u"the pump is " + what)
            if inst is None:
                body = [-s["L"] / 2, -s["W"] / 2, s["L"] / 2, s["W"] / 2, base, base + s["H"]]
                ds = rf_draw.Painter(doc, frame, []).stand_in_single(s, body, u"RFT pump - ",
                                                                      BuiltInCategory.OST_MechanicalEquipment)
                ds.get_Parameter(BuiltInParameter.ALL_MODEL_INSTANCE_COMMENTS).Set(u"RFT pump front:" + front)
                notes.append(u"the pump is a stand-in from the catalogue sizes: add the maker's .rfa to see it")
    t.Commit()
