# -*- coding: utf-8 -*-
"""The fit check: does a pump set fit the room it stands in, and what changes when it is swapped
(spec/features/revit_fit_check.md, section 4). Plain geometry and arithmetic, no AI.

This file runs in two places: in our tests (Python 3) and inside Revit, where pyRevit runs Python 2.7
(IronPython). So it uses no f-strings and nothing outside the standard library.

Everything is in millimetres, in the pump's own frame, which the Revit add-in builds:
  x  along the set's length (its manifolds)
  y  towards the set's front (the side its controls face)
  z  height above the room's floor
  the origin is the middle of the set in plan.
A box is [x0, y0, x1, y1, z0, z1].

Each check returns results shaped like checks/maf/checks.py:
  check      S1-S6 (the set in its room) or K1-K3 (what a swap changes)
  result     pass, flag, unclear or info (what the reviewer sees)
  would_be   the verdict on the values as they are, before anyone verified them
  reason     plain-language reason
  rules      the rule ids behind it (data/space/rules.csv)
  blocking   True when a flag here means the set cannot go there as drawn
  boxes      where to draw it in the model (clashes, the part outside the room)
"""
from __future__ import division

import csv
import io
import math
import os

HERE = os.path.dirname(os.path.abspath(__file__))
RULES = os.path.join(HERE, "..", "..", "data", "space", "rules.csv")

# Values read from the Revit model are the design itself, so they count as confirmed (spec section 2).
CONFIRMED = ("verified", "model")
PIPE_REACH = 300  # mm: a pipe whose end is this close to the set is taken as connected to it (spec section 3)


def load_rules(path=None):
    """The fit check's rules by id, with their status (to_confirm until Luca approves them)."""
    with io.open(path or RULES, encoding="utf-8") as f:
        return dict((r["rule_id"], r) for r in csv.DictReader(f))


def result(check, verdict, reason, inputs=(), rules=(), blocking=False, boxes=()):
    """One result. AGENTS.md rule 3: pass or flag only when every input is confirmed, otherwise unclear."""
    r = {"check": check, "result": verdict, "would_be": verdict, "reason": reason, "rules": list(rules),
         "blocking": blocking, "boxes": [list(b) for b in boxes]}
    if verdict in ("pass", "flag") and any(s not in CONFIRMED for s in inputs):
        r["result"] = "unclear"
    return r


# ---------------------------------------------------------------- geometry

def overlap(a, b):
    """The box two boxes share, or None. Touching faces (under 1 mm) don't count."""
    r = [max(a[0], b[0]), max(a[1], b[1]), min(a[2], b[2]), min(a[3], b[3]), max(a[4], b[4]), min(a[5], b[5])]
    if r[2] - r[0] > 1 and r[3] - r[1] > 1 and r[5] - r[4] > 1:
        return r
    return None


def depth(box):
    """How far one thing goes into another: the thinnest side of the shared box."""
    return min(box[2] - box[0], box[3] - box[1], box[5] - box[4])


def point_in_outline(x, y, outline, tol=1.0):
    """True when the point is inside the room's outline or on its edge (ray casting)."""
    n = len(outline)
    for i in range(n):  # on an edge counts as inside
        (ax, ay), (bx, by) = outline[i], outline[(i + 1) % n]
        if _dist_to_segment(x, y, ax, ay, bx, by) <= tol:
            return True
    inside = False
    for i in range(n):
        (ax, ay), (bx, by) = outline[i], outline[(i + 1) % n]
        if (ay > y) != (by > y):
            cross = ax + (y - ay) * (bx - ax) / (by - ay)
            if x < cross:
                inside = not inside
    return inside


def _dist_to_segment(x, y, ax, ay, bx, by):
    dx, dy = bx - ax, by - ay
    t = 0.0 if dx == dy == 0 else max(0.0, min(1.0, ((x - ax) * dx + (y - ay) * dy) / (dx * dx + dy * dy)))
    return math.hypot(x - (ax + t * dx), y - (ay + t * dy))


def inside_outline(box, outline):
    """True when the box's plan stands inside the outline: its four corners are in, and no corner of the
    room (a column, a notch) pokes into it."""
    x0, y0, x1, y1 = box[0], box[1], box[2], box[3]
    if not all(point_in_outline(x, y, outline) for x, y in ((x0, y0), (x1, y0), (x1, y1), (x0, y1))):
        return False
    return not any(x0 + 1 < x < x1 - 1 and y0 + 1 < y < y1 - 1 for x, y in outline)


def body_and_zones(size, service, base_z):
    """The set's box and its service spaces, the set centred on the origin, standing at base_z."""
    L, W, H = float(size["L"]), float(size["W"]), float(size["H"])
    x0, x1, y0, y1 = -L / 2, L / 2, -W / 2, W / 2
    z0, z1 = base_z, base_z + H
    body = [x0, y0, x1, y1, z0, z1]
    zones = []
    if service.get("front"):
        zones.append(("front", [x0, y1, x1, y1 + service["front"], 0, z1]))
    if service.get("back"):
        zones.append(("back", [x0, y0 - service["back"], x1, y0, 0, z1]))
    if service.get("sides"):
        zones.append(("left side", [x0 - service["sides"], y0, x0, y1, 0, z1]))
        zones.append(("right side", [x1, y0, x1 + service["sides"], y1, 0, z1]))
    if service.get("top"):
        zones.append(("above the motors", [x0, y0, x1, y1, z1, z1 + service["top"]]))
    return body, zones


def box_gap(point, box):
    """Distance from a point to a box: 0 on or inside it."""
    dx = max(box[0] - point[0], 0, point[0] - box[2])
    dy = max(box[1] - point[1], 0, point[1] - box[3])
    dz = max(box[4] - point[2], 0, point[2] - box[5])
    return math.sqrt(dx * dx + dy * dy + dz * dz)


def box_inside_depth(point, box):
    """How far a point is inside a box (0 when outside)."""
    if box_gap(point, box) > 0:
        return 0.0
    return min(point[0] - box[0], box[2] - point[0], point[1] - box[1], box[3] - point[1],
               point[2] - box[4], box[5] - point[2])


def _mm(v):
    return int(round(v))


def _name(s):
    return u"{} {}".format(s.get("maker", ""), s.get("model", "")).strip()


# ---------------------------------------------------------------- S1-S6: the set in its room

def s1_inside_room(body, room, status):
    """S1: the set stands inside the room's outline and under its height."""
    rules = ["RO-I9-19-2"]
    if not inside_outline(body, room["outline"]):
        return result("S1", "flag", u"the set runs past the room's walls", [status, "model"], rules, True, [body])
    if body[5] > room["height"]:
        return result("S1", "flag", u"the set is {} mm taller than the room ({} mm)".format(
            _mm(body[5] - room["height"]), _mm(room["height"])), [status, "model"], rules, True, [body])
    return result("S1", "pass", u"inside the room, {} mm under its ceiling".format(_mm(room["height"] - body[5])),
                  [status, "model"], rules)


def s2_clashes(body, room, status):
    """S2: the set hits nothing in the model (equipment, pipes, ducts, columns, door leaves)."""
    hits = []
    for o in room.get("obstacles", []) + [dict(d, box=d["swing"], name=d["name"] + " (door swing)")
                                         for d in room.get("doors", []) if d.get("swing")]:
        r = overlap(body, o["box"])
        if r:
            hits.append((o["name"], r))
    if hits:
        text = u"; ".join(u"hits {} by {} mm".format(n, _mm(depth(r))) for n, r in hits)
        return result("S2", "flag", text, [status, "model"], ["RO-I9-19-2"], True, [r for _, r in hits])
    return result("S2", "pass", u"hits nothing in the model", [status, "model"], ["RO-I9-19-2"])


def s3_service_space(body, zones, room, status):
    """S3: the consultant's service space around the set is free and inside the room."""
    found, boxes = [], []
    things = room.get("obstacles", []) + [dict(d, box=d["swing"], name=d["name"] + " (door swing)")
                                          for d in room.get("doors", []) if d.get("swing")]
    for where, z in zones:
        if where == "above the motors":
            if z[5] > room["height"]:
                cut = [z[0], z[1], z[2], z[3], room["height"], z[5]]
                found.append(u"the ceiling cuts the space above the motors by {} mm".format(_mm(z[5] - room["height"])))
                boxes.append(cut)
        elif not inside_outline(z, room["outline"]):
            found.append(u"a wall is in the {} space".format(where))
            boxes.append(z)
        for o in things:
            r = overlap(z, o["box"])
            if r:
                found.append(u"{} is in the {} space by {} mm".format(o["name"], where, _mm(depth(r))))
                boxes.append(r)
    if not zones:
        return result("S3", "info", u"no service space set for this project", [], ["ANY-SPACE-SERVICE"])
    if found:
        return result("S3", "flag", u"; ".join(found), [status, "model"], ["ANY-SPACE-SERVICE"], False, boxes)
    return result("S3", "pass", u"the service space is free", [status, "model"], ["ANY-SPACE-SERVICE"])


def s4_through_a_door(size, room, status):
    """S4: the set can be brought in and taken out through at least one door of the room (I9 17.11).
    It goes through on its narrower side, standing up."""
    doors = room.get("doors", [])
    if not doors:
        return result("S4", "unclear", u"no door of this room found in the model", [], ["RO-I9-17-11"])
    narrow = min(size["L"], size["W"])
    fits = [d for d in doors if narrow <= d["width"] and size["H"] <= d["height"]]
    widest = max(doors, key=lambda d: d["width"])
    if fits:
        d = max(fits, key=lambda d: d["width"])
        return result("S4", "pass", u"goes through {} ({} x {} mm) on its {} mm side, {} mm high".format(
            d["name"], _mm(d["width"]), _mm(d["height"]), _mm(narrow), _mm(size["H"])), [status, "model"],
            ["RO-I9-17-11"])
    return result("S4", "flag", u"too big for every door: {} mm wide and {} mm high, the widest door is {} x {} mm"
                  .format(_mm(narrow), _mm(size["H"]), _mm(widest["width"]), _mm(widest["height"])),
                  [status, "model"], ["RO-I9-17-11"], True)


def s5_standby(s, status):
    """S5: one pump alone carries the duty, from the standby test (MAF-19) as stored with the set."""
    if s.get("standby") == "pass":
        return result("S5", "pass", u"one pump carries the duty: it needs {} kW, each motor gives {} kW".format(
            s.get("p2_needed"), s.get("p2_each")), [status], ["RO-I9-6-56"])
    if s.get("standby") == "fail":
        return result("S5", "flag", u"one pump needs {} kW at the duty but each motor gives {} kW: both must run, "
                      u"so there is no real standby".format(s.get("p2_needed"), s.get("p2_each")), [status],
                      ["RO-I9-6-56"], True)
    return result("S5", "unclear", u"no power at the duty point for one pump: read it on the curve", [],
                  ["RO-I9-6-56"])


def s6_drinking_water(s, status):
    """S6: an approval for contact with drinking water is in the package (as H1 in the MAF check)."""
    if s.get("dw_approval") is True:
        return result("S6", "pass", u"approved for drinking water", [status], ["RO-OMS275-DW"])
    if s.get("dw_approval") is False:
        return result("S6", "flag", u"no approval for contact with drinking water in the package", [status],
                      ["RO-OMS275-DW"])
    return result("S6", "unclear", u"not known whether the set is approved for drinking water", [],
                  ["RO-OMS275-DW"])


def fit(s, room, service, base_z=0.0):
    """All S checks for one set in the room. s holds the set's size, data and their status."""
    status = s.get("status", "extracted")
    body, zones = body_and_zones(s, service, base_z)
    rows = [s1_inside_room(body, room, status), s2_clashes(body, room, status),
            s3_service_space(body, zones, room, status), s4_through_a_door(s, room, status),
            s5_standby(s, status), s6_drinking_water(s, status)]
    return {"set": s, "body": body, "zones": zones, "results": rows, "verdict": verdict(rows)}


# ---------------------------------------------------------------- K1-K3: what a swap changes

def k1_pipes(new, old_body, new_body, pipes, status):
    """K1: the pipes that end at the set in the model still meet the new one, at a size it takes."""
    if not pipes:
        return [result("K1", "unclear", u"no pipe ends at the set in the model", [], [])]
    out = []
    for p in pipes:
        role = p.get("role")
        dns = [new.get("dn_in")] if role == "suction" else [new.get("dn_out")] if role == "discharge" \
            else [new.get("dn_in"), new.get("dn_out")]
        dns = [d for d in dns if d]
        notes, boxes, worst = [], [], "pass"
        if not dns:
            notes.append(u"the new set's connection size is not known")
            worst = "unclear"
        elif p.get("dn") and p["dn"] != min(dns, key=lambda d: abs(d - p["dn"])):
            near = min(dns, key=lambda d: abs(d - p["dn"]))
            notes.append(u"DN{} pipe on a DN{} connection: a reducer is needed".format(_mm(p["dn"]), _mm(near)))
            worst = "flag"
        inside = box_inside_depth(p["end"], new_body)
        before, after = box_gap(p["end"], old_body), box_gap(p["end"], new_body)
        if inside > 1:
            notes.append(u"its end is now {} mm inside the new set".format(_mm(inside)))
            boxes.append([p["end"][0] - 50, p["end"][1] - 50, p["end"][0] + 50, p["end"][1] + 50,
                          p["end"][2] - 50, p["end"][2] + 50])
            worst = "flag"
        elif after > before + 50:
            notes.append(u"its end is now {} mm short of the set ({} mm before)".format(_mm(after), _mm(before)))
            worst = "flag"
        text = u"{}: {}".format(p["name"], u"; ".join(notes) if notes else u"still meets the set, same size")
        out.append(result("K1", worst, text, [status, "model"], [], False, boxes))
    return out


def k2_circuit(new, old, circuit, status):
    """K2: the motor power on the pump's circuit. Never passes: the electrical engineer re-checks a circuit
    whose load grows (ENG-CIRCUIT-RECHECK, to confirm with Luca)."""
    rules = ["ENG-CIRCUIT-RECHECK"]
    try:
        new_kw = new["pumps"] * new["p2_each"]
        old_kw = old["pumps"] * old["p2_each"]
    except (KeyError, TypeError):
        return result("K2", "unclear", u"the motor power of the old or the new set is not known", [], rules)
    where = u"circuit {}".format(circuit["name"]) if circuit else u"the circuit (none found in the model)"
    if circuit and circuit.get("rating_a"):
        where += u", {} A".format(circuit["rating_a"])
    if new_kw > old_kw:
        return result("K2", "flag", u"motor power goes up from {:g} to {:g} kW on {}: the electrical engineer "
                      u"checks the cable and breaker again".format(old_kw, new_kw, where), [status], rules)
    return result("K2", "info", u"motor power {:g} kW, was {:g} kW, on {}: no more load than designed".format(
        new_kw, old_kw, where), [status], rules)


def k3_weight(new, old, status):
    """K3: the weight on the plinth and slab. Always unclear: the structure and the 25 cm gap of
    I9 18.7 are not in the model."""
    rules = ["RO-I9-18-7"]
    if new.get("kg") is None:
        return result("K3", "unclear", u"the new set's weight is not known: ask the supplier", [], rules)
    if old.get("kg") is None:
        return result("K3", "unclear", u"{:g} kg; the old set's weight is not known".format(new["kg"]), [], rules)
    change = new["kg"] - old["kg"]
    r = result("K3", "info", u"{:g} kg, {:g} kg {} than now: the plinth, its 25 cm gap to the building's foundations "
               u"and the slab are checked by the structural engineer".format(
                   new["kg"], abs(change), u"heavier" if change > 0 else u"lighter"), [status], rules)
    r["result"] = r["would_be"] = "unclear"
    return r


def swap(new, old, room, service, pipes=(), circuit=None, base_z=0.0, old_size=None):
    """Everything the swap of old for new changes: the new set's fit (S1-S6) and the knock-on checks (K1-K3).
    old_size is the size of the set now in the model, measured on its geometry."""
    status = new.get("status", "extracted")
    res = fit(new, room, service, base_z)
    old_body, _ = body_and_zones(old_size or old, {}, base_z)
    rows = k1_pipes(new, old_body, res["body"], list(pipes), status)
    rows += [k2_circuit(new, old, circuit, status), k3_weight(new, old, status)]
    res["results"] = res["results"] + rows
    res["verdict"] = verdict(res["results"])
    return res


# ---------------------------------------------------------------- verdict and table

def verdict(rows):
    """The worst of the results, on the values as they are: FAIL when a blocking flag, flag when anything to
    look at, would pass otherwise. 'confirmed' is False while some result waits for verified inputs."""
    would = [r["would_be"] for r in rows]
    if any(r["would_be"] == "flag" and r["blocking"] for r in rows):
        v = "FAIL"
    elif any(w in ("flag", "unclear") for w in would):
        v = "flag"
    else:
        v = "would pass"
    confirmed = all(r["result"] == r["would_be"] for r in rows)
    if v == "would pass" and confirmed:
        v = "pass"
    return {"verdict": v, "confirmed": confirmed,
            "fails": sum(1 for r in rows if r["would_be"] == "flag" and r["blocking"]),
            "flags": sum(1 for r in rows if r["would_be"] == "unclear" or (r["would_be"] == "flag" and not r["blocking"]))}


def table(sets, room, service, base_z=0.0):
    """One line per candidate: its verdict in this room (S checks only, nothing moved)."""
    out = []
    for i, s in enumerate(sets):
        v = fit(s, room, service, base_z)["verdict"]
        out.append([i + 1, v["verdict"], _name(s) + (u" (submitted)" if s.get("submitted") else u""),
                    u"{:.0f} x {:.0f} x {:.0f}".format(s["L"], s["W"], s["H"]), v["fails"], v["flags"]])
    return out
