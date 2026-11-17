# -*- coding: utf-8 -*-
"""Reading the Revit model: the pump, its room, the room's doors, what else stands in it, the pipes at the
pump and its circuit. Nothing here changes the model.

Everything is handed to the checks in millimetres, in the pump's own frame (see checks/space/space_checks.py):
x along the set, y towards its front, z above the room's floor, the set's middle at the origin.
Revit works in feet, so every length goes through mm() or ft().
"""
from __future__ import division
import math

from Autodesk.Revit.DB import (BuiltInCategory, BuiltInParameter, ElementId, ElementMulticategoryFilter,
                               BoundingBoxIntersectsFilter, FamilyInstance, FilteredElementCollector,
                               GeometryInstance, Mesh, Options, Outline, RevitLinkInstance, Solid,
                               SpatialElementBoundaryOptions, Transform, ViewDetailLevel, XYZ, DirectShape, Curve)
from Autodesk.Revit.DB.Plumbing import Pipe
from System.Collections.Generic import List

import rf_setup  # noqa: F401  (puts checks/space on the path first)
import space_checks

PUMP_CATEGORIES = (BuiltInCategory.OST_MechanicalEquipment, BuiltInCategory.OST_GenericModel,
                   BuiltInCategory.OST_PlumbingFixtures, BuiltInCategory.OST_SpecialityEquipment)

# What can stand in the way of a pump set (spec section 3).
OBSTACLE_CATEGORIES = [BuiltInCategory.OST_MechanicalEquipment, BuiltInCategory.OST_PlumbingFixtures,
                       BuiltInCategory.OST_ElectricalEquipment, BuiltInCategory.OST_GenericModel,
                       BuiltInCategory.OST_SpecialityEquipment, BuiltInCategory.OST_PipeCurves,
                       BuiltInCategory.OST_PipeFitting, BuiltInCategory.OST_PipeAccessory,
                       BuiltInCategory.OST_DuctCurves, BuiltInCategory.OST_DuctFitting,
                       BuiltInCategory.OST_CableTray, BuiltInCategory.OST_Conduit,
                       BuiltInCategory.OST_StructuralColumns, BuiltInCategory.OST_StructuralFraming,
                       BuiltInCategory.OST_Columns]


def name_of(el):
    """An element's name. Revit types (FamilySymbol, WallType...) hide .Name from IronPython, so read it
    through the base Element class."""
    if el is None:
        return u""
    try:
        from Autodesk.Revit.DB import Element
        return Element.Name.GetValue(el) or u""
    except Exception:
        return getattr(el, "Name", u"") or u""


def eid(element_id):
    """An element id as a number. Revit 2024 renamed IntegerValue to Value; this works with both."""
    try:
        return int(element_id.Value)  # a plain Python number, so it can be saved as JSON
    except AttributeError:
        return int(element_id.IntegerValue)


def mm(feet):
    return feet * 304.8


def ft(millimetres):
    return millimetres / 304.8


def category_of(el):
    try:
        return el.Category.Name
    except Exception:
        return u""


def names_of(el, doc):
    """Everything the element is called: family, type, Model and Manufacturer, mark, comments."""
    out = [name_of(el)]
    t = doc.GetElement(el.GetTypeId())
    if t is not None:
        out.append(name_of(t))
        try:
            out.append(t.FamilyName)
        except Exception:
            pass
        for bip in (BuiltInParameter.ALL_MODEL_MODEL, BuiltInParameter.ALL_MODEL_MANUFACTURER,
                    BuiltInParameter.ALL_MODEL_TYPE_COMMENTS):
            p = t.get_Parameter(bip)
            if p is not None and p.AsString():
                out.append(p.AsString())
    for bip in (BuiltInParameter.ALL_MODEL_MARK, BuiltInParameter.ALL_MODEL_INSTANCE_COMMENTS):
        p = el.get_Parameter(bip)
        if p is not None and p.AsString():
            out.append(p.AsString())
    return [n for n in out if n]


# ---------------------------------------------------------------- the pump's own frame

class Frame(object):
    """The pump's frame: origin (feet, world) at the set's middle in plan on the room's floor,
    x along the set, y towards its front. local() and world() convert, in millimetres."""

    def __init__(self, origin, xdir, floor_z):
        self.x = XYZ(xdir.X, xdir.Y, 0).Normalize()
        self.y = XYZ(-self.x.Y, self.x.X, 0)  # 90 degrees to the left of x
        self.origin = XYZ(origin.X, origin.Y, floor_z)

    def local(self, p):
        d = p - self.origin
        return [mm(d.DotProduct(self.x)), mm(d.DotProduct(self.y)), mm(d.Z)]

    def world(self, x, y, z):
        return self.origin + self.x.Multiply(ft(x)) + self.y.Multiply(ft(y)) + XYZ(0, 0, ft(z))

    def vector(self, v):
        """A local direction ('x', 'y', 'z' or a 3-list) as a world vector."""
        if v == "x":
            return self.x
        if v == "y":
            return self.y
        if v == "z":
            return XYZ.BasisZ
        return self.x.Multiply(v[0]) + self.y.Multiply(v[1]) + XYZ.BasisZ.Multiply(v[2])

    def angle(self):
        """The frame's turn from the world x axis, in radians."""
        return math.atan2(self.x.Y, self.x.X)


def geometry_points(el, transform=None):
    """Points on an element's real geometry (solid edges, meshes, curves), in world feet."""
    opt = Options()
    opt.DetailLevel = ViewDetailLevel.Fine
    pts = []

    def walk(geo, tr):
        if geo is None:
            return
        for g in geo:
            if isinstance(g, GeometryInstance):
                walk(g.GetInstanceGeometry(), tr)
            elif isinstance(g, Solid):
                if g.Volume > 0:
                    for e in g.Edges:
                        for p in e.Tessellate():
                            pts.append(tr.OfPoint(p) if tr else p)
            elif isinstance(g, Mesh):
                for p in g.Vertices:
                    pts.append(tr.OfPoint(p) if tr else p)
    walk(el.get_Geometry(opt), transform)
    if not pts:  # nothing solid: fall back on the element's box
        bb = el.get_BoundingBox(None)
        if bb is not None:
            pts = corners(bb.Min, bb.Max, transform)
    return pts


def corners(a, b, tr=None):
    out = []
    for x in (a.X, b.X):
        for y in (a.Y, b.Y):
            for z in (a.Z, b.Z):
                p = XYZ(x, y, z)
                out.append(tr.OfPoint(p) if tr else p)
    return out


def local_box(points, frame):
    """The box around points, in the frame (mm)."""
    loc = [frame.local(p) for p in points]
    xs, ys, zs = [p[0] for p in loc], [p[1] for p in loc], [p[2] for p in loc]
    return [min(xs), min(ys), max(xs), max(ys), min(zs), max(zs)]


def pump_axes(el, doc):
    """x and front direction of the pump in the world. A family gives its own; a RightFit stand-in (a
    DirectShape) keeps them in its comments as 'front:+X', since a DirectShape has no placement."""
    if isinstance(el, FamilyInstance):
        t = el.GetTransform()
        return t.BasisX, t.Origin
    note = el.get_Parameter(BuiltInParameter.ALL_MODEL_INSTANCE_COMMENTS)
    note = note.AsString() if note is not None and note.AsString() else u""
    front = {"front:+X": XYZ.BasisX, "front:-X": XYZ.BasisX.Negate(), "front:-Y": XYZ.BasisY.Negate()}
    for k, v in front.items():
        if k in note:
            return XYZ(v.Y, -v.X, 0), None  # x is front turned 90 degrees clockwise, so y = front
    return XYZ.BasisX, None


# ---------------------------------------------------------------- the room

class RoomInfo(object):
    """The room (or MEP space) a point stands in, with the document it lives in and the transform from that
    document to the host model (a linked architectural model has its own coordinates)."""

    def __init__(self, room, rdoc, tr, kind):
        self.room, self.doc, self.tr, self.kind = room, rdoc, tr, kind
        bb = room.get_BoundingBox(None)
        pts = corners(bb.Min, bb.Max, tr)
        self.floor_z = min(p.Z for p in pts)
        self.top_z = max(p.Z for p in pts)
        if self.top_z - self.floor_z < 0.3:  # Revit hasn't computed the room's volume: use its own height
            try:
                self.top_z = self.floor_z + room.UnboundedHeight
            except Exception:
                pass
        number = getattr(room, "Number", None) or u""
        p = room.get_Parameter(BuiltInParameter.ROOM_NAME)
        label = p.AsString() if p is not None and p.AsString() else u""
        self.name = u"{} {}".format(number, label).strip()

    def world_box(self):
        bb = self.room.get_BoundingBox(None)
        pts = corners(bb.Min, bb.Max, self.tr)
        return (XYZ(min(p.X for p in pts), min(p.Y for p in pts), min(p.Z for p in pts)),
                XYZ(max(p.X for p in pts), max(p.Y for p in pts), max(p.Z for p in pts)))


LAST_ERRORS = []


def find_room(doc, point):
    """The room or space at a point: the host model first, then each linked model."""
    try:
        r = doc.GetRoomAtPoint(point)
        if r is not None:
            return RoomInfo(r, doc, Transform.Identity, "room")
    except Exception:
        pass
    try:
        s = doc.GetSpaceAtPoint(point)
        if s is not None:
            return RoomInfo(s, doc, Transform.Identity, "space")
    except Exception:
        pass
    # GetRoomAtPoint can miss a room whose height Revit hasn't worked out yet: ask each room directly
    for kind, cat in (("room", BuiltInCategory.OST_Rooms), ("space", BuiltInCategory.OST_MEPSpaces)):
        for r in FilteredElementCollector(doc).OfCategory(cat).WhereElementIsNotElementType():
            try:
                if r.Area > 0 and _in_plan_outline(r, point):
                    return RoomInfo(r, doc, Transform.Identity, kind)
            except Exception as ex:
                LAST_ERRORS.append(u"{}: {}".format(kind, ex))
    for li in FilteredElementCollector(doc).OfClass(RevitLinkInstance):
        ldoc = li.GetLinkDocument()
        if ldoc is None:
            continue
        tr = li.GetTotalTransform()
        p = tr.Inverse.OfPoint(point)
        try:
            r = ldoc.GetRoomAtPoint(p)
        except Exception:
            r = None
        if r is not None:
            return RoomInfo(r, ldoc, tr, "room in a linked model")
    return None


def _in_plan_outline(room, point):
    """True when the point stands inside the room's boundary in plan, between its floor and top."""
    bb = room.get_BoundingBox(None)
    if bb is not None and bb.Max.Z - bb.Min.Z > 0.5 and not (bb.Min.Z - 0.01 <= point.Z <= bb.Max.Z + 0.01):
        return False
    for loop in room.GetBoundarySegments(SpatialElementBoundaryOptions()):
        pts = []
        for seg in loop:
            for p in list(seg.GetCurve().Tessellate())[:-1]:
                pts.append([p.X, p.Y])
        if len(pts) >= 3 and space_checks.point_in_outline(point.X, point.Y, pts, tol=0.001):
            return True
    return False


def outline(info, frame):
    """The room's outer boundary in the frame (mm), from the room's own boundary (finish faces)."""
    loops = info.room.GetBoundarySegments(SpatialElementBoundaryOptions())
    best = []
    for loop in loops:
        pts = []
        for seg in loop:
            for p in list(seg.GetCurve().Tessellate())[:-1]:
                q = frame.local(info.tr.OfPoint(p))
                pts.append([q[0], q[1]])
        if len(pts) > len(best) and _area(pts) > _area(best):
            best = pts
    return best


def _area(pts):
    if len(pts) < 3:
        return 0.0
    return abs(sum(pts[i][0] * pts[(i + 1) % len(pts)][1] - pts[(i + 1) % len(pts)][0] * pts[i][1]
                   for i in range(len(pts)))) / 2


def _param_mm(el, *bips):
    for bip in bips:
        p = el.get_Parameter(bip)
        if p is not None and p.HasValue and p.AsDouble() > 0:
            return mm(p.AsDouble())
    return None


def doors(info, frame):
    """The room's doors: clear width and height, and the square their leaf sweeps on the room's side."""
    out = []
    rid = eid(info.room.Id)
    poly = outline(info, frame)
    phases = info.doc.Phases
    phase = phases.get_Item(phases.Size - 1) if phases.Size else None
    for d in FilteredElementCollector(info.doc).OfCategory(BuiltInCategory.OST_Doors) \
            .WhereElementIsNotElementType():
        if not isinstance(d, FamilyInstance):
            continue
        ids = []
        for getter in ("get_FromRoom", "get_ToRoom"):  # FromRoom/ToRoom take the phase in IronPython
            try:
                r = getattr(d, getter)(phase)
                if r is not None:
                    ids.append(eid(r.Id))
            except Exception:
                pass
        p = d.Location.Point if hasattr(d.Location, "Point") else None
        if p is None:
            continue
        near = _near_outline(frame.local(info.tr.OfPoint(p)), poly)
        if rid not in ids and not near:
            continue
        w = _param_mm(d, BuiltInParameter.DOOR_WIDTH, BuiltInParameter.FAMILY_WIDTH_PARAM) or \
            _param_mm(d.Symbol, BuiltInParameter.DOOR_WIDTH, BuiltInParameter.FAMILY_WIDTH_PARAM)
        h = _param_mm(d, BuiltInParameter.DOOR_HEIGHT, BuiltInParameter.FAMILY_HEIGHT_PARAM) or \
            _param_mm(d.Symbol, BuiltInParameter.DOOR_HEIGHT, BuiltInParameter.FAMILY_HEIGHT_PARAM)
        if not w or not h:
            continue
        # Which side is the room: step half a metre along the door's facing and ask the room.
        f = d.FacingOrientation
        ahead = frame.local(info.tr.OfPoint(p + f.Multiply(ft(500))))
        inward = f if space_checks.point_in_outline(ahead[0], ahead[1], poly) else f.Negate()
        hand = d.HandOrientation
        sweep = [p + hand.Multiply(ft(w / 2)), p - hand.Multiply(ft(w / 2)),
                 p + hand.Multiply(ft(w / 2)) + inward.Multiply(ft(w)),
                 p - hand.Multiply(ft(w / 2)) + inward.Multiply(ft(w))]
        loc = [frame.local(info.tr.OfPoint(q)) for q in sweep]
        swing = [min(q[0] for q in loc), min(q[1] for q in loc), max(q[0] for q in loc), max(q[1] for q in loc),
                 0, h]
        mark = d.get_Parameter(BuiltInParameter.ALL_MODEL_MARK)
        name = u"door {}".format(mark.AsString()) if mark is not None and mark.AsString() else u"the door"
        out.append({"name": name, "width": w, "height": h, "swing": swing, "id": eid(d.Id)})
    return out


def _near_outline(p, poly, tol=400):
    n = len(poly)
    return any(space_checks._dist_to_segment(p[0], p[1], poly[i][0], poly[i][1], poly[(i + 1) % n][0],
                                             poly[(i + 1) % n][1]) <= tol for i in range(n))


def _docs_with_transforms(doc):
    yield doc, Transform.Identity
    for li in FilteredElementCollector(doc).OfClass(RevitLinkInstance):
        ldoc = li.GetLinkDocument()
        if ldoc is not None:
            yield ldoc, li.GetTotalTransform()


def contents(doc, info, frame, skip_ids, pipe_ends_near=None):
    """Everything in the room that could be in the way, as boxes in the frame. Pipes that end at the pump are
    left out here: they belong to the pump and are checked in K1."""
    lo, hi = info.world_box()
    out = []
    cats = List[BuiltInCategory]()
    for c in OBSTACLE_CATEGORIES:
        cats.Add(c)
    for d, tr in _docs_with_transforms(doc):
        inv = tr.Inverse
        a, b = inv.OfPoint(lo), inv.OfPoint(hi)
        box = Outline(XYZ(min(a.X, b.X), min(a.Y, b.Y), min(a.Z, b.Z)), XYZ(max(a.X, b.X), max(a.Y, b.Y), max(a.Z, b.Z)))
        col = FilteredElementCollector(d).WherePasses(ElementMulticategoryFilter(cats)) \
            .WherePasses(BoundingBoxIntersectsFilter(box)).WhereElementIsNotElementType()
        for el in col:
            if d is doc and eid(el.Id) in skip_ids:
                continue
            if isinstance(el, DirectShape) and name_of(el).startswith(u"RF "):
                continue  # RightFit's own drawing
            note = el.get_Parameter(BuiltInParameter.ALL_MODEL_INSTANCE_COMMENTS)
            if note is not None and (note.AsString() or u"").startswith(u"RF preview"):
                continue  # RightFit's preview of a candidate
            bb = el.get_BoundingBox(None)
            if bb is None:
                continue
            lb = local_box(corners(bb.Min, bb.Max, tr), frame)
            name = name_of(el) or category_of(el)
            if pipe_ends_near and isinstance(el, Pipe) and eid(el.Id) in pipe_ends_near:
                continue
            out.append({"name": u"{} ({})".format(name, category_of(el)) if name != category_of(el) else name,
                        "category": category_of(el), "box": lb, "id": eid(el.Id)})
    return out


def pipes_at(doc, pump, frame, body):
    """Pipes in the host model with an end within reach of the set: their size, where they end, and whether
    they feed it (suction) or leave it (discharge) when they are connected to one of its connectors."""
    roles = {}
    try:
        for c in pump.MEPModel.ConnectorManager.Connectors:
            for other in c.AllRefs:
                role = u"suction" if str(c.Direction) == "In" else u"discharge" if str(c.Direction) == "Out" else None
                roles[eid(other.Owner.Id)] = role
    except Exception:
        pass
    lo = frame.world(body[0] - 2000, body[1] - 2000, body[4] - 2000)
    hi = frame.world(body[2] + 2000, body[3] + 2000, body[5] + 2000)
    box = Outline(XYZ(min(lo.X, hi.X), min(lo.Y, hi.Y), min(lo.Z, hi.Z)), XYZ(max(lo.X, hi.X), max(lo.Y, hi.Y),
                                                                              max(lo.Z, hi.Z)))
    out = []
    for p in FilteredElementCollector(doc).OfClass(Pipe).WherePasses(BoundingBoxIntersectsFilter(box)):
        crv = p.Location.Curve
        for end in (crv.GetEndPoint(0), crv.GetEndPoint(1)):
            e = frame.local(end)
            if space_checks.box_gap(e, body) <= space_checks.PIPE_REACH:
                dn = _param_mm(p, BuiltInParameter.RBS_PIPE_DIAMETER_PARAM)
                out.append({"name": u"pipe DN{}".format(int(round(dn))) if dn else u"a pipe",
                            "dn": int(round(dn)) if dn else None, "end": e, "role": roles.get(eid(p.Id)),
                            "id": eid(p.Id)})
    return out


def circuit_of(pump, fallback=None):
    """The electrical circuit the pump is on, from the model; else the one project.json names."""
    try:
        systems = list(pump.MEPModel.GetElectricalSystems())
    except Exception:
        systems = []
    for s in systems:
        rating = None
        try:
            rating = round(s.Rating, 1)
        except Exception:
            pass
        name = name_of(s) or s.CircuitNumber
        return {"name": name, "rating_a": rating, "source": "model", "status": "model"}
    return fallback


# ---------------------------------------------------------------- everything at once

class Situation(object):
    """The pump in question and its room, as the checks need them."""

    def __init__(self, doc, pump):
        self.doc, self.pump = doc, pump
        xdir, origin = pump_axes(pump, doc)
        pts = geometry_points(pump)
        temp = Frame(pts[0], xdir, 0)
        lb = local_box(pts, temp)
        mid = temp.world((lb[0] + lb[2]) / 2, (lb[1] + lb[3]) / 2, 0)
        probe = temp.world((lb[0] + lb[2]) / 2, (lb[1] + lb[3]) / 2, lb[4] + 300)
        self.probe = probe
        self.room = find_room(doc, probe)
        floor = self.room.floor_z if self.room else temp.world(0, 0, lb[4]).Z
        self.frame = Frame(mid, xdir, floor)
        self.body = local_box(pts, self.frame)  # the set now in the model, measured on its geometry
        self.size = {"L": self.body[2] - self.body[0], "W": self.body[3] - self.body[1],
                     "H": self.body[5] - self.body[4]}
        self.base_z = self.body[4]
        self.names = names_of(pump, doc)

    def room_data(self):
        """The room as the checks want it."""
        if self.room is None:
            return None
        pipes = pipes_at(self.doc, self.pump, self.frame, self.body)
        return {
            "name": self.room.name,
            "kind": self.room.kind,
            "outline": outline(self.room, self.frame),
            "height": mm(self.room.top_z - self.room.floor_z),
            "doors": doors(self.room, self.frame),
            "obstacles": contents(self.doc, self.room, self.frame, [eid(self.pump.Id)],
                                  set(p["id"] for p in pipes)),
            "pipes": pipes,
        }
