# -*- coding: utf-8 -*-
"""What RightFit draws: a candidate in the pump's place (the maker's family, or a stand-in built from the
catalogue sizes), its service space, the clashes, and a 3D view cropped to the room.

Everything RightFit draws is named "RF ..." (DirectShapes) or carries the comment "RF preview" (families),
so Clear can remove it and the model reader can ignore it.
"""
from __future__ import division
import io
import json
import math
import os

import clr
from Autodesk.Revit.DB import (Arc, BoundingBoxXYZ, BuiltInCategory, BuiltInParameter, Color, CurveLoop,
                               DirectShape, DisplayStyle, ElementId, ElementTransformUtils, Family,
                               FamilyInstance, FillPatternElement, FilteredElementCollector, GeometryCreationUtilities,
                               GeometryObject, Level, Line, OverrideGraphicSettings, Transform, View3D,
                               ViewFamily, ViewFamilyType, ViewOrientation3D, Wall, XYZ)
from Autodesk.Revit.DB import (FailureProcessingResult, FailureSeverity, IFailuresPreprocessor)
from Autodesk.Revit.DB import FamilySymbol, ImportInstance, SolidUtils
from Autodesk.Revit.DB import DWGImportOptions, GeometryInstance, ImportPlacement, ImportUnit, Mesh, Options, Solid
from Autodesk.Revit.DB import (TessellatedFace, TessellatedShapeBuilder, TessellatedShapeBuilderFallback,
                               TessellatedShapeBuilderTarget)
from Autodesk.Revit.DB import ViewDetailLevel
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

def _norm(text):
    return u"".join(ch for ch in (text or u"").lower() if ch.isalnum())


def load_symbol(doc, path, type_name=None, type_contains=None):
    """Load a family file once (or find it already loaded) and return the type to place. A family with a type
    catalogue (a .txt beside the .rfa) loads only the type asked for; a family that holds its types inside is
    searched for type_name, or for a type whose name contains type_contains."""
    stem = os.path.splitext(os.path.basename(path))[0]
    fam = None
    for f in FilteredElementCollector(doc).OfClass(Family):
        if name_of(f) == stem:
            fam = f
            break
    if fam is None and os.path.exists(os.path.splitext(path)[0] + ".txt"):
        # a family with a type catalogue: load only the one type. Loading the whole family would load every
        # type in the catalogue (slow, and Revit may ask which ones), so without a type name we stop here.
        if not type_name:
            return None
        ref = clr.Reference[FamilySymbol]()
        try:
            if doc.LoadFamilySymbol(path, type_name, ref):
                sym = ref.Value
                if not sym.IsActive:
                    sym.Activate()
                    doc.Regenerate()
                return sym
        except Exception:
            pass
        for f in FilteredElementCollector(doc).OfClass(Family):  # loaded before, by another type
            if name_of(f) == stem:
                fam = f
                break
        if fam is None:
            return None
    if fam is None:
        ref = clr.Reference[Family]()
        if doc.LoadFamily(path, ref):
            fam = ref.Value
    if fam is None:
        for f in FilteredElementCollector(doc).OfClass(Family):
            if name_of(f) == stem:
                fam = f
    if fam is None:
        return None
    syms = [doc.GetElement(i) for i in fam.GetFamilySymbolIds()]
    sym = None
    for s in syms:
        if type_name and _norm(name_of(s)) == _norm(type_name):
            sym = s
    if sym is None and type_contains:
        for s in syms:
            if _norm(type_contains) in _norm(name_of(s)):
                sym = s
                break
    sym = sym or (syms[0] if syms else None)
    if sym is not None and not sym.IsActive:
        sym.Activate()
        doc.Regenerate()
    return sym


def fit_element(doc, el, frame, s, base_z, extra_turn=0, current=None):
    """Turn an element so its long side runs along the frame's x like the catalogue, put its middle on the
    frame's origin and stand it at base_z. Returns its measured box in the frame (mm)."""
    axis = Line.CreateBound(frame.origin, frame.origin + XYZ.BasisZ)
    if current is None:
        current = math.atan2(el.GetTransform().BasisX.Y, el.GetTransform().BasisX.X)
    turn = frame.angle() - current + math.radians(extra_turn)
    if abs(turn) > 1e-6:
        ElementTransformUtils.RotateElement(doc, el.Id, axis, turn)
        doc.Regenerate()
    b = local_box(geometry_points(el), frame)
    if ((b[2] - b[0]) < (b[3] - b[1])) != (s["L"] < s["W"]):  # long side the wrong way: a quarter turn
        ElementTransformUtils.RotateElement(doc, el.Id, axis, math.pi / 2)
        doc.Regenerate()
        b = local_box(geometry_points(el), frame)
    move = frame.vector([-(b[0] + b[2]) / 2 / 304.8, -(b[1] + b[3]) / 2 / 304.8, (base_z - b[4]) / 304.8])
    ElementTransformUtils.MoveElement(doc, el.Id, move)
    doc.Regenerate()
    return local_box(geometry_points(el), frame)


def place_family(doc, sym, frame, s, base_z, level, extra_turn=0):
    """Place a family in the frame (see fit_element). Returns the instance and its measured box."""
    try:
        inst = doc.Create.NewFamilyInstance(frame.origin, sym, level, StructuralType.NonStructural)
    except Exception:
        inst = doc.Create.NewFamilyInstance(frame.origin, sym, StructuralType.NonStructural)
    doc.Regenerate()
    return inst, fit_element(doc, inst, frame, s, base_z, extra_turn)


class _AcceptWarnings(IFailuresPreprocessor):
    """Let Revit go on past warnings (such as 'cannot import some of the geometry'): the parts it could read
    are kept, and the report compares the result with the catalogue size."""
    def PreprocessFailures(self, accessor):
        for f in list(accessor.GetFailureMessages()):
            if f.GetSeverity() == FailureSeverity.Warning:
                accessor.DeleteWarning(f)
        return FailureProcessingResult.Continue


def accept_warnings(transaction):
    opts = transaction.GetFailureHandlingOptions()
    opts.SetFailuresPreprocessor(_AcceptWarnings())
    transaction.SetFailureHandlingOptions(opts)


def _upright(points, s, up=None):
    """Which of the drawing's axes is the set's length, width and height: the order that best matches the
    catalogue's L x W x H (makers draw 'up' along different axes). Returns a transform that stands it up."""
    from itertools import permutations
    ext = [max(p[i] for p in points) - min(p[i] for p in points) for i in range(3)]
    want = [s.get("L"), s.get("W"), s.get("H")]
    if not points or not all(want):
        return Transform.Identity, ext
    orders = [o for o in permutations(range(3)) if up is None or o[2] == up]  # families.json can name "up"
    best = min(orders, key=lambda o: sum(abs(ext[o[k]] - want[k]) / want[k] for k in range(3)))
    axes = [XYZ.BasisX, XYZ.BasisY, XYZ.BasisZ]
    ex, ez = axes[best[0]], axes[best[2]]  # the drawing's length axis becomes x, its height axis becomes z
    ey = ez.CrossProduct(ex)
    t = Transform.Identity
    t.BasisX = XYZ(ex.X, ey.X, ez.X)
    t.BasisY = XYZ(ex.Y, ey.Y, ez.Y)
    t.BasisZ = XYZ(ex.Z, ey.Z, ez.Z)
    return t, ext


def _triangles(g):
    """The triangles of a solid's faces or of a mesh, as lists of three points."""
    tris = []
    meshes = [g] if isinstance(g, Mesh) else []
    if isinstance(g, Solid):
        for f in g.Faces:
            try:
                m = f.Triangulate()
            except Exception:
                m = None
            if m is not None:  # some faces in maker drawings cannot be triangulated
                meshes.append(m)
    for m in meshes:
        for i in range(m.NumTriangles):
            tr = m.get_Triangle(i)
            tris.append([tr.get_Vertex(0), tr.get_Vertex(1), tr.get_Vertex(2)])
    return tris


def _rebuild(g):
    """A shape Revit refuses as it is (common in maker drawings: open or self-touching surfaces) rebuilt
    from its triangles; Revit keeps it as a solid when it closes, otherwise as a mesh."""
    b = TessellatedShapeBuilder()
    b.Target = TessellatedShapeBuilderTarget.AnyGeometry
    b.Fallback = TessellatedShapeBuilderFallback.Mesh
    b.OpenConnectedFaceSet(False)
    n = 0
    for a, c, d in _triangles(g):
        if a.DistanceTo(c) < 1e-6 or c.DistanceTo(d) < 1e-6 or a.DistanceTo(d) < 1e-6:
            continue  # a triangle with no area
        pts = List[XYZ]()
        for p in (a, c, d):
            pts.Add(p)
        try:
            b.AddFace(TessellatedFace(pts, ElementId.InvalidElementId))
            n += 1
        except Exception:
            pass
    b.CloseConnectedFaceSet()
    if not n:
        return []
    b.Build()
    return list(b.GetBuildResult().GetGeometricalObjects())


def import_drawing(doc, path, view, name, category, s=None, units="mm", up=None):
    """Bring a maker's 3D DWG into the model as one DirectShape with the drawing's real solids, standing up,
    then remove the imported DWG itself. Maker drawings are in millimetres even when the file says otherwise
    (the Grundfos file says inches); families.json can set "units" for one that isn't."""
    opt = DWGImportOptions()
    opt.ThisViewOnly = False
    opt.Placement = ImportPlacement.Origin
    opt.Unit = {"mm": ImportUnit.Millimeter, "cm": ImportUnit.Centimeter, "m": ImportUnit.Meter,
                "inch": ImportUnit.Inch, "auto": ImportUnit.Default}.get(units, ImportUnit.Millimeter)
    before = set(eid(e.Id) for e in FilteredElementCollector(doc).OfClass(ImportInstance))
    ref = clr.Reference[ElementId]()
    doc.Import(path, opt, view, ref)
    doc.Regenerate()
    new = [e for e in FilteredElementCollector(doc).OfClass(ImportInstance) if eid(e.Id) not in before]
    if not new:
        raise Exception(u"Revit could not import " + os.path.basename(path))
    imp = new[0]
    pieces = []

    def walk(geo):
        for g in geo:
            if isinstance(g, GeometryInstance):
                walk(g.GetInstanceGeometry())
            elif isinstance(g, Solid) and g.Faces.Size > 0:  # closed solids and open shells
                pieces.append(g)
            elif isinstance(g, Mesh) and g.NumTriangles > 0:
                pieces.append(g)
    walk(imp.get_Geometry(Options()))
    pts = []
    for g in pieces:
        if isinstance(g, Solid):
            for e in g.Edges:
                for q in e.Tessellate():
                    pts.append([mm(q.X), mm(q.Y), mm(q.Z)])
        else:
            for q in g.Vertices:
                pts.append([mm(q.X), mm(q.Y), mm(q.Z)])
    turn, _ = _upright(pts, s or {}, {"x": 0, "y": 1, "z": 2}.get((up or u"").lower()))
    ds = DirectShape.CreateElement(doc, ElementId(category))
    good = List[GeometryObject]()
    why = []
    for g in pieces:
        g2 = SolidUtils.CreateTransformed(g, turn) if isinstance(g, Solid) else g.get_Transformed(turn)
        one = List[GeometryObject]()
        one.Add(g2)
        try:
            ok = ds.IsValidShape(one)
        except Exception:
            ok = False
        if ok:
            good.Add(g2)
        else:
            try:
                for r in _rebuild(g2):
                    good.Add(r)
            except Exception as err:
                why.append(u"{}".format(err))
    if good.Count:
        ds.SetShape(good)
        ds.SetName(name)
    try:
        imp.Pinned = False  # an import placed at the origin comes pinned
        doc.Delete(imp.Id)  # the DirectShape now holds the geometry
    except Exception:
        pass
    if not good.Count:  # nothing Revit can hold as a shape: say so, and leave nothing behind
        doc.Delete(ds.Id)
        found = u", ".join(u"{} {}".format(type(g).__name__, (g.Faces.Size if isinstance(g, Solid) else g.NumTriangles))
                           for g in pieces[:5])
        raise Exception(u"Revit read no usable 3D shapes from {} ({} pieces found: {}; {} triangles; {})".format(
            os.path.basename(path), len(pieces), found, sum(len(_triangles(g)) for g in pieces[:5]),
            u"; ".join(why[:2])))
    doc.Regenerate()
    return ds


def family_as_shape(doc, inst, name, category):
    """Copy a placed family's solids into one DirectShape and delete the family instance. Used for previews:
    a maker's MEP family (with pipe connectors and many detailed solids) left in the model made Revit 2026
    stop responding on the next redraw or command, while DirectShapes draw quickly. Returns the DirectShape,
    or None (and leaves the instance) when no shape could be copied."""
    opt = Options()
    opt.DetailLevel = ViewDetailLevel.Fine
    pieces = []

    def walk(geo):
        if geo is None:
            return
        for g in geo:
            if isinstance(g, GeometryInstance):
                walk(g.GetInstanceGeometry())  # already in model coordinates
            elif isinstance(g, Solid) and g.Faces.Size > 0:
                pieces.append(g)
            elif isinstance(g, Mesh) and g.NumTriangles > 0:
                pieces.append(g)
    walk(inst.get_Geometry(opt))
    ds = DirectShape.CreateElement(doc, ElementId(category))
    good = List[GeometryObject]()
    for g in pieces:
        one = List[GeometryObject]()
        one.Add(g)
        try:
            ok = ds.IsValidShape(one)
        except Exception:
            ok = False
        if ok:
            good.Add(g)
        else:
            try:
                for r in _rebuild(g):
                    good.Add(r)
            except Exception:
                pass
    if not good.Count:
        doc.Delete(ds.Id)
        return None
    ds.SetShape(good)
    ds.SetName(name)
    doc.Delete(inst.Id)
    doc.Regenerate()
    return ds


# ---------------------------------------------------------------- saved shapes of maker families
# Loading a maker's .rfa into the project left Revit 2026 busy for minutes after the command ended (seen in the
# journal with the DAB and Wilo families). So the first time a family is shown, its shape is saved beside the
# .rfa as "<file>.<type>.shape.json" (triangles in mm, in the pump's frame); later previews draw it from there
# and never load the family again. "Prepare Models" (Setup panel) saves them all at once.

def shape_path(path, entry):
    key = _norm(entry.get("type") or entry.get("type_contains") or u"")
    return os.path.splitext(path)[0] + (u"." + key if key else u"") + u".shape.json"


def save_shape(ds, frame, type_name, out_path):
    """Write the triangles of DirectShape ds, in the frame (mm, centred in plan, base at 0)."""
    opt = Options()
    tris = []
    for g in ds.get_Geometry(opt):
        if isinstance(g, (Solid, Mesh)):
            for a, b, c in _triangles(g):
                tris.append([frame.local(a), frame.local(b), frame.local(c)])
    if not tris:
        return False
    xs = [p[0] for t3 in tris for p in t3]
    ys = [p[1] for t3 in tris for p in t3]
    zs = [p[2] for t3 in tris for p in t3]
    cx, cy, z0 = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2, min(zs)
    flat = [[round(p[0] - cx, 1), round(p[1] - cy, 1), round(p[2] - z0, 1)] for t3 in tris for p in t3]
    with io.open(out_path, "w", encoding="utf-8") as fh:
        fh.write(json.dumps({"type": type_name, "points": flat}, ensure_ascii=False))
    return True


def shape_from_file(doc, shape_file, frame, base_z, name, category):
    """Draw a saved shape as a DirectShape in the frame. Returns (DirectShape, type name) or (None, None)."""
    with io.open(shape_file, encoding="utf-8") as fh:
        data = json.load(fh)
    pts = data.get("points", [])
    b = TessellatedShapeBuilder()
    b.Target = TessellatedShapeBuilderTarget.AnyGeometry
    b.Fallback = TessellatedShapeBuilderFallback.Mesh
    b.OpenConnectedFaceSet(False)
    n = 0
    for i in range(0, len(pts) - 2, 3):
        face = List[XYZ]()
        for x, y, z in pts[i:i + 3]:
            face.Add(frame.world(x, y, z + base_z))
        if face[0].DistanceTo(face[1]) < 1e-6 or face[1].DistanceTo(face[2]) < 1e-6 or face[0].DistanceTo(face[2]) < 1e-6:
            continue
        try:
            b.AddFace(TessellatedFace(face, ElementId.InvalidElementId))
            n += 1
        except Exception:
            pass
    b.CloseConnectedFaceSet()
    if not n:
        return None, None
    b.Build()
    ds = DirectShape.CreateElement(doc, ElementId(category))
    ds.SetShape(b.GetBuildResult().GetGeometricalObjects())
    ds.SetName(name)
    doc.Regenerate()
    return ds, data.get("type", u"")


def place_model(doc, path, entry, frame, s, base_z, level, view, name, category, as_shape=False):
    """Place the maker's model of set s: a Revit family (.rfa) or a 3D drawing (.dwg).
    as_shape (previews): draw a family as its shape only, from the saved shape when there is one.
    Returns (element, measured box, what it is in words)."""
    turn = float(entry.get("rotate", 0))
    note = (u" — " + entry["note"]) if entry.get("note") else u""
    saved = shape_path(path, entry)
    if as_shape and path.lower().endswith(".rfa") and os.path.exists(saved):
        ds, type_name = shape_from_file(doc, saved, frame, base_z, name, category)
        if ds is not None:
            return ds, local_box(geometry_points(ds), frame), \
                u"the maker's Revit family: {} ({}), drawn from its saved shape".format(os.path.basename(path), type_name) + note
    if path.lower().endswith(".dwg"):
        try:
            ds = import_drawing(doc, path, view, name, category, s, entry.get("units", "mm"), entry.get("up"))
        except Exception as err:  # the drawing could not be used: the caller draws the stand-in instead
            return None, None, u"{}".format(err)
        return ds, fit_element(doc, ds, frame, s, base_z, turn, current=0.0), \
            u"the maker's 3D drawing: " + os.path.basename(path) + (u" — " + entry["note"] if entry.get("note") else u"")
    sym = load_symbol(doc, path, entry.get("type"), entry.get("type_contains"))
    if sym is None:
        return None, None, u"no matching type in " + os.path.basename(path)
    inst, b = place_family(doc, sym, frame, s, base_z, level, turn)
    if as_shape:  # a preview: keep only the family's shape (see family_as_shape), and save it for next time
        ds = family_as_shape(doc, inst, name, category)
        if ds is not None:
            inst = ds
            b = local_box(geometry_points(ds), frame)
            try:
                save_shape(ds, frame, name_of(sym), saved)
            except Exception:
                pass
    what = u"the maker's Revit family: {} ({})".format(os.path.basename(path), name_of(sym))
    return inst, b, what + (u" — " + entry["note"] if entry.get("note") else u"")


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
