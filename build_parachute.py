# Neon Coast parachute (ram-air canopy like the ones in modern shooters) + backpack, Blender headless:
#   blender --background --factory-startup --python build_parachute.py
# Canopy: 9-cell rectangular ram-air wing, 20 studs span, 7.6 chord, arched (anhedral) so the tips sit lower,
# a real airfoil section with open intake mouths at the leading edge, stabiliser flaps at the tips, alternating
# black / neon pink cells with a teal centre cell, 40 suspension lines down to four risers, brake lines to the
# toggles, a slider on the lines. Origin = the harness point (between the jumper's shoulders, on the back);
# the jumper faces -Y, the canopy flies toward -Y. Pack: container, pilot-chute handle, shoulder straps.
# Out: Parachute.glb (Canopy at x = 0, ParachutePack at x = 40), parachute.json, previews/Parachute_*.png
import sys, json, os, math
sys.path.insert(0, r"C:\Users\Crisa\Documents\NeonCoast_Blender")
import importlib, nc_kit, nc_extra, nc_detail
importlib.reload(nc_kit)
importlib.reload(nc_extra)
importlib.reload(nc_detail)
from nc_extra import *
from nc_detail import beam
import bpy
from mathutils import Vector

reset()
nc_kit.COLORS.update({"CanopyA": (0.07, 0.07, 0.09), "CanopyB": (1.0, 0.22, 0.62), "CanopyC": (0.10, 0.85, 0.85),
                      "Lines": (0.88, 0.88, 0.84), "Risers": (0.10, 0.10, 0.12), "Slider": (0.20, 0.20, 0.22),
                      "PackBody": (0.14, 0.15, 0.17), "PackTrim": (1.0, 0.22, 0.62), "Strap": (0.08, 0.08, 0.09), "Handle": (0.95, 0.75, 0.10)})

SPAN, CHORD, H0, DROP = 20.0, 7.6, 15.0, 2.6
NCELL = 9


def arc_z(x):
    return H0 - DROP * (x / (SPAN / 2)) ** 2


def rib_frame(x):
    """rib plane at span position x: chord direction (along -Y is forward) and the outward normal of the arc"""
    dzdx = -2 * DROP * x / (SPAN / 2) ** 2
    n = Vector((-dzdx, 0.0, 1.0)).normalized()
    return n


def airfoil(t):
    """upper / lower offsets (studs) at chord fraction t (0 = leading edge): 16% thick, flat-bottomed, cambered"""
    yt = 5 * 0.16 * (0.2969 * math.sqrt(t) - 0.126 * t - 0.3516 * t * t + 0.2843 * t ** 3 - 0.1015 * t ** 4) * CHORD
    camber = 0.035 * CHORD * 4 * t * (1 - t)
    return camber + yt, camber - 0.35 * yt


STATIONS = [0.0, 0.02, 0.06, 0.12, 0.22, 0.35, 0.5, 0.65, 0.8, 0.92, 1.0]


def rib_ring(x):
    n = rib_frame(x)
    c = Vector((x, 0.0, arc_z(x)))
    pts = []
    for t in STATIONS:                                    # upper surface, front to back
        u, _ = airfoil(t)
        y = -CHORD / 2 + CHORD * t
        pts.append(c + Vector((0, y, 0)) + n * u)
    for t in reversed(STATIONS[1:-1]):                   # lower surface, back to front
        _, l = airfoil(t)
        y = -CHORD / 2 + CHORD * t
        pts.append(c + Vector((0, y, 0)) + n * l)
    return pts


def canopy():
    H = House("Canopy")
    ribs = [-SPAN / 2 + SPAN * i / NCELL for i in range(NCELL + 1)]
    for i in range(NCELL):
        kind = "CanopyC" if i == NCELL // 2 else ("CanopyB" if i % 2 == 0 else "CanopyA")
        r0, r1 = rib_ring(ribs[i] + 0.02), rib_ring(ribs[i + 1] - 0.02)
        m = len(r0)
        verts = [tuple(p) for p in r0 + r1]
        faces = []
        for k in range(m):
            j = (k + 1) % m
            if k == m - 1:                               # leave the nose open: the ram-air intake mouth
                continue
            faces.append((k, j, m + j, m + k))
        faces.append(tuple(range(m - 1, -1, -1)))        # rib walls (the cells are closed at their sides)
        faces.append(tuple(range(m, 2 * m)))
        H.p(kind).solid(verts, faces)
    # stabiliser flaps hanging under the tips
    for s in (-1, 1):
        x = s * SPAN / 2
        z = arc_z(x)
        H.p("CanopyA").solid([(x, -CHORD * 0.35, z - 0.2), (x, CHORD * 0.4, z - 0.2), (x + s * 0.05, 0.0, z - 3.2),
                              (x + s * 0.12, -CHORD * 0.35, z - 0.2), (x + s * 0.12, CHORD * 0.4, z - 0.2), (x + s * 0.17, 0.0, z - 3.2)],
                             [(0, 1, 2), (5, 4, 3), (0, 3, 4, 1), (1, 4, 5, 2), (2, 5, 3, 0)])
    # suspension lines: four rows (A-D) under every rib to the front / rear risers on that side
    risers = {(-1, -1): Vector((-0.9, -0.35, 3.2)), (-1, 1): Vector((-0.9, 0.35, 3.2)), (1, -1): Vector((0.9, -0.35, 3.2)), (1, 1): Vector((0.9, 0.35, 3.2))}
    for x in ribs:
        n = rib_frame(x)
        c = Vector((x, 0.0, arc_z(x)))
        side = -1 if x < 0 else 1
        for t in (0.12, 0.35, 0.6, 0.85):
            _, l = airfoil(t)
            p = c + Vector((0, -CHORD / 2 + CHORD * t, 0)) + n * l
            r = risers[(side, -1 if t < 0.5 else 1)]
            beam(H, "Lines", tuple(p), tuple(r), 0.06, 0.06)
    for s in (-1, 1):                                    # brake lines from the trailing edge to the toggles
        for x in (s * 7.8, s * 10.0):
            p = Vector((x, CHORD / 2, arc_z(x)))
            beam(H, "Lines", tuple(p), (s * 0.95, 0.5, 2.9), 0.05, 0.05)
    H.p("Slider").box(-1.1, -0.9, 4.6, 1.1, 0.9, 4.7)    # slider down on the risers
    for s in (-1, 1):                                    # risers from the connector links to the harness
        for d in (-1, 1):
            beam(H, "Risers", (s * 0.9, d * 0.35, 3.2), (s * 0.7, d * 0.2 + 0.25, 0.2), 0.28, 0.07)
        H.p("Handle").box(s * 0.95 - 0.12, 0.45, 2.75, s * 0.95 + 0.12, 0.6, 3.05)   # toggles
    H.notes["harness"] = [0.0, 0.0, 0.0]
    H.notes["span"] = SPAN
    H.notes["height"] = H0
    return H


def pack():
    H = House("ParachutePack")
    # worn on the back: the jumper faces -Y, so the container sits at +Y behind the shoulders
    H.p("PackBody").box(-0.85, 0.05, -1.2, 0.85, 0.75, 0.9)
    H.p("PackBody").box(-0.75, 0.75, -1.0, 0.75, 0.9, 0.7)            # the bulging flap
    H.p("PackTrim").box(-0.86, 0.3, 0.9, 0.86, 0.6, 0.98)              # neon top seam
    H.p("PackTrim").box(-0.86, 0.3, -1.28, 0.86, 0.6, -1.2)
    H.p("Handle").box(0.35, 0.9, -1.15, 0.65, 1.05, -0.85)              # pilot-chute handle (bottom of container)
    for s in (-1, 1):                                                     # shoulder straps over to the chest
        beam(H, "Strap", (s * 0.6, 0.05, 0.9), (s * 0.6, -0.6, 1.15), 0.32, 0.08)
        beam(H, "Strap", (s * 0.6, -0.6, 1.15), (s * 0.6, -1.1, 0.3), 0.32, 0.08)
        beam(H, "Strap", (s * 0.6, -1.1, 0.3), (s * 0.6, -1.0, -1.0), 0.32, 0.08)
    H.p("Strap").box(-0.65, -1.18, -0.05, 0.65, -1.06, 0.12)             # chest strap
    H.p("Handle").box(-0.18, -1.22, -0.12, 0.18, -1.08, 0.18)            # buckle
    H.notes["mount"] = [0.0, 0.0, 0.0]
    return H


meta = {}
x = 0.0
for ob in list(bpy.context.scene.objects):
    ob.select_set(False)
for fn, spacing in ((canopy, 40.0), (pack, 10.0)):
    H = fn()
    objs, tris = H.build()
    for ob in objs:
        if H.style == "Canopy" and "Canopy" in ob.name:
            for poly in ob.data.polygons:
                poly.use_smooth = True
        ob.location.x += x
        ob["style"] = "ParachuteProps"
        ob.select_set(True)
    co = [v.co for ob in objs for v in ob.data.vertices]
    ext = {"x": [min(c.x for c in co), max(c.x for c in co)], "y": [min(c.y for c in co), max(c.y for c in co)], "z": [min(c.z for c in co), max(c.z for c in co)]}
    meta[H.style] = {"offsetX": x, "pieces": sorted(tris.keys()), "triangles": tris, "notes": H.notes, "extents_studs": ext}
    x += spacing
bpy.ops.export_scene.gltf(filepath=os.path.join(OUT, "Parachute.glb"), export_format="GLB", use_selection=True, export_apply=True, export_yup=True)
with open(os.path.join(OUT, "parachute.json"), "w") as f:
    json.dump(meta, f)
scene, cam = setup_render()
render_views(scene, cam, ["ParachuteProps"], {
    "canopy": ((-26, -30, 4), (0, 0, 10)),
    "below": ((6, -14, -4), (0, 0, 12)),
    "pack": ((40 - 3.5, 4.5, 1.6), (40, 0.4, 0)),
}, "Parachute")
print("NEONCOAST_DONE", json.dumps({k: sum(v["triangles"].values()) for k, v in meta.items()}))
