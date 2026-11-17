# -*- coding: utf-8 -*-
"""What RightFit draws: a candidate in the pump's place (the maker's family, or a stand-in built from the
catalogue sizes), its service space, the clashes, and a 3D view cropped to the room.

Everything RightFit draws is named "RF ..." (DirectShapes) or carries the comment "RF preview" (families),
so Clear can remove it and the model reader can ignore it.
"""
from __future__ import division
import math
import os

import clr
from Autodesk.Revit.DB import (Arc, BoundingBoxXYZ, BuiltInCategory, BuiltInParameter, Color, CurveLoop,
                               DirectShape, DisplayStyle, ElementId, ElementTransformUtils, Family,
                               FamilyInstance, FillPatternElement, FilteredElementCollector, GeometryCreationUtilities,
                               GeometryObject, Level, Line, OverrideGraphicSettings, Transform, View3D,
                               ViewFamily, ViewFamilyType, ViewOrientation3D, Wall, XYZ)
from Autodesk.Revit.DB.Structure import StructuralType
from System import Int64
from System.Collections.Generic import List

from rf_model import corners, eid, ft, geometry_points, local_box, mm, name_of

VIEW3D = "RightFit 3D"
PREVIEW = u"RF preview"
COLOURS = {"FAIL": (207, 58, 46), "flag": (201, 138, 18), "would pass": (29, 138, 91), "pass": (29, 138, 91)}
TEAL = (30, 158, 143)
PART_RGB = {"frame": (70, 74, 80), "pump": (175, 180, 186), "motor": (40, 90, 160), "pipe": (150, 156, 164),
            "panel": (225, 225, 220)}


# ---------------------------------------------------------------- solids in the pump's frame

def box_solid(frame, b):
    """A box given in the frame (mm) as a Revit solid, turned with the frame."""
    x0, y0, x1, y1, z0, z1 = b
    z1 = max(z1, z0 + 10)
    pts = [frame.world(x0, y0, z0), frame.world(x1, y0, z0), frame.world(x1, y1, z0), frame.world(x0, y1, z0)]
    loop = CurveLoop()
    for i in range(4):
        loop.Append(Line.CreateBound(pts[i], pts[(i + 1) % 4]))
    loops = List[CurveLoop]()
    loops.Add(loop)
    return GeometryCreationUtilities.CreateExtrusionGeometry(loops, XYZ.BasisZ, ft(z1 - z0))


def cylinder_solid(frame, centre, r, length, axis):
    """A cylinder in the frame: centre of its start face (mm), radius, length, axis 'x', 'y' or 'z'."""
    c = frame.world(*centre)
    d = frame.vector(axis)
    a = frame.vector({"x": "y", "y": "z", "z": "x"}[axis])
    b = d.CrossProduct(a)
    loop = CurveLoop()
    loop.Append(Arc.Create(c, ft(r), 0, math.pi, a, b))
    loop.Append(Arc.Create(c, ft(r), math.pi, 2 * math.pi, a, b))
    loops = List[CurveLoop]()
    loops.Add(loop)
    return GeometryCreationUtilities.CreateExtrusionGeometry(loops, d, ft(length))


def stand_in(s, body):
    """A booster set built from the catalogue sizes, for when the maker's family is missing: a base frame,
    one upright pump with its motor per pump, suction and discharge manifolds and a control panel.
    It shows the set's size and layout, not its real shape; the report says so."""
    x0, y0, x1, y1, z0, z1 = body
    L, W, H = x1 - x0, y1 - y0, z1 - z0
    n = max(1, int(s.get("pumps") or 2))
    parts = {"frame": [], "pump": [], "motor": [], "pipe": [], "panel": []}
    fh = min(80.0, H * 0.1)
    # the frame's rails run along both long sides, so the stand-in fills the catalogue's L x W x H
    parts["frame"].append(("box", [x0, y0, x1, y0 + 60, z0, z0 + fh]))
    parts["frame"].append(("box", [x0, y1 - 60, x1, y1, z0, z0 + fh]))
    panel = min(220.0, L * 0.18)
    parts["panel"].append(("box", [x1 - panel, y0 + W * 0.25, x1, y1 - W * 0.25, z0 + H * 0.35, z1]))
    parts["frame"].append(("box", [x1 - panel * 0.6, y0 + W * 0.45, x1 - panel * 0.3, y1 - W * 0.45, z0 + fh,
                                   z0 + H * 0.35]))
    usable = L - panel - 60
    pitch = usable / n
    r = max(40.0, min(pitch * 0.26, W * 0.17))
    py = y0 + W * 0.42  # pumps a little behind the middle, manifolds at the back
    hyd, mot = (H - fh) * 0.5, (H - fh) * 0.42
    for i in range(n):
        px = x0 + 30 + pitch * (i + 0.5)
        parts["pump"].append(("cyl", (px, py, z0 + fh), r, hyd, "z"))
        parts["motor"].append(("cyl", (px, py, z0 + fh + hyd), r * 1.3, mot, "z"))
        parts["motor"].append(("cyl", (px, py, z0 + fh + hyd + mot), r * 1.1, (H - fh) - hyd - mot, "z"))
    for dn, z in ((s.get("dn_in") or 65, z0 + fh + hyd * 0.2), (s.get("dn_out") or s.get("dn_in") or 65,
                                                              z0 + fh + hyd * 0.85)):
        rr = float(dn) * 0.57
        ys = y0 + rr  # the manifolds run along the back edge
        parts["pipe"].append(("cyl", (x0, ys, z), rr, usable + 30, "x"))
        for i in range(n):
            parts["pipe"].append(("cyl", (x0 + 30 + pitch * (i + 0.5), ys, z), rr * 0.7, py - ys, "y"))
    return parts


# ---------------------------------------------------------------- drawing

class Painter(object):
    """Draws in the model and colours what it draws in the given views."""

    def __init__(self, doc, frame, views):
        self.doc, self.frame, self.views = doc, frame, [v for v in views if v is not None]
        self.solid = None
        for f in FilteredElementCollector(doc).OfClass(FillPatternElement):
            if f.GetFillPattern().IsSolidFill:
                self.solid = f.Id
                break

    def paint(self, el, rgb, transparency=0, lines_only=False):
        o = OverrideGraphicSettings()
        col = Color(*rgb)
        o.SetProjectionLineColor(col)
        if not lines_only:
            o.SetSurfaceForegroundPatternColor(col)
            o.SetCutForegroundPatternColor(col)
            if self.solid:
                o.SetSurfaceForegroundPatternId(self.solid)
                o.SetCutForegroundPatternId(self.solid)
            o.SetSurfaceTransparency(transparency)
        for v in self.views:
            try:
                v.SetElementOverrides(el.Id, o)
            except Exception:
                pass

    def shape(self, solids, name, rgb, transparency=0, category=BuiltInCategory.OST_GenericModel):
        ds = DirectShape.CreateElement(self.doc, ElementId(category))
        geo = List[GeometryObject]()
        for s in solids:
            geo.Add(s)
        ds.SetShape(geo)
        ds.SetName(name)
        self.paint(ds, rgb, transparency)
        return ds

    def boxes(self, boxes, name, rgb, transparency=0):
        if boxes:
            return self.shape([box_solid(self.frame, b) for b in boxes], name, rgb, transparency)

    def stand_in(self, s, body, name_prefix="RF ", category=BuiltInCategory.OST_GenericModel):
        """The stand-in set, one DirectShape per kind of part so each keeps its colour."""
        made = []
        for part, prims in stand_in(s, body).items():
            solids = []
            for p in prims:
                if p[0] == "box":
                    solids.append(box_solid(self.frame, p[1]))
                else:
                    solids.append(cylinder_solid(self.frame, p[1], p[2], p[3], p[4]))
            if solids:
                made.append(self.shape(solids, u"{}{} {}".format(name_prefix, s.get("model", u""), part),
                                       PART_RGB[part], 0, category))
        return made


def _stand_in_solids(painter, s, body):
    solids = []
    for part, prims in stand_in(s, body).items():
        for p in prims:
            if p[0] == "box":
                solids.append(box_solid(painter.frame, p[1]))
            else:
                solids.append(cylinder_solid(painter.frame, p[1], p[2], p[3], p[4]))
    return solids


Painter.stand_in_single = lambda self, s, body, prefix, category: self.shape(
    _stand_in_solids(self, s, body), u"{}{} {}".format(prefix, s.get("maker", u""), s.get("model", u"")),
    PART_RGB["motor"], 0, category)


def drawn(doc):
    """Everything RightFit drew: its DirectShapes and its preview families."""
    out = [e for e in FilteredElementCollector(doc).OfClass(DirectShape) if name_of(e).startswith(u"RF ")]
    for e in FilteredElementCollector(doc).OfClass(FamilyInstance):
        p = e.get_Parameter(BuiltInParameter.ALL_MODEL_INSTANCE_COMMENTS)
        if p is not None and (p.AsString() or u"").startswith(PREVIEW):
            out.append(e)
    return out


def clear(doc, unhide=()):
    """Remove what RightFit drew, and show again the pump a preview hid in the RightFit 3D view.
    Run inside a transaction."""
    n = 0
    for e in drawn(doc):
        doc.Delete(e.Id)
        n += 1
    ids = List[ElementId]()
    for i in unhide:
        el = doc.GetElement(ElementId(Int64(i)))  # Int64: Revit 2026 has several ElementId(number) forms
        if el is not None:
            ids.Add(el.Id)
    for v in FilteredElementCollector(doc).OfClass(View3D):
        if v.Name == VIEW3D and ids.Count:
            try:
                v.UnhideElements(ids)
            except Exception:
                pass
    return n


# ---------------------------------------------------------------- the maker's family

def load_symbol(doc, path, type_name=None):
    """Load a family file once (or find it already loaded) and return its type to place."""
    stem = os.path.splitext(os.path.basename(path))[0]
    fam = None
    for f in FilteredElementCollector(doc).OfClass(Family):
        if name_of(f) == stem:
            fam = f
            break
    if fam is None:
        ref = clr.Reference[Family]()
        if doc.LoadFamily(path, ref):
            fam = ref.Value
    if fam is None:
        return None
    syms = [doc.GetElement(i) for i in fam.GetFamilySymbolIds()]
    sym = None
    for s in syms:
        if type_name and name_of(s) == type_name:
            sym = s
    sym = sym or syms[0]
    if not sym.IsActive:
        sym.Activate()
        doc.Regenerate()
    return sym


def place_family(doc, sym, frame, s, base_z, level, extra_turn=0):
    """Place a family in the frame: turned so its long side runs along the frame's x like the catalogue,
    its middle on the frame's origin, standing at base_z. Returns the instance and its measured box."""
    try:
        inst = doc.Create.NewFamilyInstance(frame.origin, sym, level, StructuralType.NonStructural)
    except Exception:
        inst = doc.Create.NewFamilyInstance(frame.origin, sym, StructuralType.NonStructural)
    doc.Regenerate()
    axis = Line.CreateBound(frame.origin, frame.origin + XYZ.BasisZ)
    current = math.atan2(inst.GetTransform().BasisX.Y, inst.GetTransform().BasisX.X)
    turn = frame.angle() - current + math.radians(extra_turn)
    if abs(turn) > 1e-6:
        ElementTransformUtils.RotateElement(doc, inst.Id, axis, turn)
        doc.Regenerate()
    b = local_box(geometry_points(inst), frame)
    if ((b[2] - b[0]) < (b[3] - b[1])) != (s["L"] < s["W"]):  # long side the wrong way: a quarter turn
        ElementTransformUtils.RotateElement(doc, inst.Id, axis, math.pi / 2)
        doc.Regenerate()
        b = local_box(geometry_points(inst), frame)
    move = frame.vector([-(b[0] + b[2]) / 2 / 304.8, -(b[1] + b[3]) / 2 / 304.8, (base_z - b[4]) / 304.8])
    ElementTransformUtils.MoveElement(doc, inst.Id, move)
    doc.Regenerate()
    return inst, local_box(geometry_points(inst), frame)


def lowest_level(doc):
    return sorted(FilteredElementCollector(doc).OfClass(Level), key=lambda l: l.Elevation)[0]


# ---------------------------------------------------------------- the 3D view

def view3d(doc):
    for v in FilteredElementCollector(doc).OfClass(View3D):
        if not v.IsTemplate and v.Name == VIEW3D:
            return v
    vft = [t for t in FilteredElementCollector(doc).OfClass(ViewFamilyType)
           if t.ViewFamily == ViewFamily.ThreeDimensional][0]
    v = View3D.CreateIsometric(doc, vft.Id)
    v.Name = VIEW3D
    return v


def frame_view(doc, v, frame, outline_pts, height, ghost_ids=()):
    """Crop the view to the room (a section box turned with the pump), shade it, and look at the set's front
    from above and to the right. Walls of the room go see-through so the set stays visible."""
    xs = [p[0] for p in outline_pts] or [-3000, 3000]
    ys = [p[1] for p in outline_pts] or [-3000, 3000]
    m = 400
    bb = BoundingBoxXYZ()
    t = Transform.Identity
    t.Origin = frame.origin
    t.BasisX, t.BasisY, t.BasisZ = frame.x, frame.y, XYZ.BasisZ
    bb.Transform = t
    bb.Min = XYZ(ft(min(xs) - m), ft(min(ys) - m), ft(-50))
    bb.Max = XYZ(ft(max(xs) + m), ft(max(ys) + m), ft(height + 300))
    v.SetSectionBox(bb)
    v.IsSectionBoxActive = True
    v.DisplayStyle = DisplayStyle.ShadingWithEdges
    span = max(max(xs) - min(xs), max(ys) - min(ys), 3000)
    target = frame.world((min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2, 600)
    eye = frame.world(span * 0.9, max(ys) + span * 1.2, span * 1.3)
    fwd = (target - eye).Normalize()
    right = fwd.CrossProduct(XYZ.BasisZ).Normalize()
    up = right.CrossProduct(fwd).Normalize()
    v.SetOrientation(ViewOrientation3D(eye, up, fwd))
    try:
        v.AreAnnotationCategoriesHidden = True
    except Exception:
        pass
    o = OverrideGraphicSettings()
    o.SetSurfaceTransparency(65)
    for i in ghost_ids:
        try:
            v.SetElementOverrides(i, o)
        except Exception:
            pass


def walls_near(doc, frame, outline_pts):
    """Walls of the host model around the room, to see through them."""
    out = []
    if not outline_pts:
        return out
    xs, ys = [p[0] for p in outline_pts], [p[1] for p in outline_pts]
    for w in FilteredElementCollector(doc).OfClass(Wall):
        bb = w.get_BoundingBox(None)
        if bb is None:
            continue
        b = local_box(corners(bb.Min, bb.Max), frame)
        if b[2] > min(xs) - 500 and b[0] < max(xs) + 500 and b[3] > min(ys) - 500 and b[1] < max(ys) + 500:
            out.append(w.Id)
    return out
