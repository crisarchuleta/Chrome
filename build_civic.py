# Neon Coast: Palmgrove Plaza shop module and Palmgrove Elementary, built in Blender headless:
#   blender --background --factory-startup --python build_civic.py
# Front faces -Y in Blender (+Z in Roblox after the default glTF import, which is how both face in Studio).
# Shop: one 130 x 70 module, used five times along the plaza (colours set per shop in Studio).
# School: origin = centre of the main building (Studio 2770, -3700). The classroom wing sits at Blender
# (-150, +160) = Studio (2620, -3860), joined to the main building by a covered walkway.
import sys, json, os
sys.path.insert(0, r"C:\Users\Crisa\Documents\NeonCoast_Blender")
import importlib, nc_kit, nc_extra
importlib.reload(nc_kit)
importlib.reload(nc_extra)
from nc_extra import *

reset()
meta = {}


# ---------------------------------------------------------------- plaza shop
def shop():
    H = House("Shop")
    F, TOP, PAR = 0.8, 18.0, 22.0
    xL, xR, yF, yB = -64.45, 64.45, -34.45, 34.45
    H.slab("Foundation", xL - 1.0, yF - 1.0, xR + 1.0, yB + 1.0, 0, F - 0.3)
    H.slab("Tile", xL, yF, xR, yB, F - 0.3, F, tag=None)
    store = [(-60.0, -12.0, F + 0.8, 13.4), (12.0, 60.0, F + 0.8, 13.4)]
    entry = (-6.0, 6.0, F, F + 11.2)
    H.wall("x", yF, -1, xL - T_OUT, xR + T_OUT, F, TOP, store + [entry])
    back = [(-50.0, -45.4, F, F + 8.6), (20.0, 34.0, F, F + 12.0), (-30.0, -24.0, F + 6.0, F + 10.0)]
    H.wall("x", yB, 1, xL - T_OUT, xR + T_OUT, F, TOP, back)
    H.wall("y", xL, -1, yF + T_IN, yB - T_IN, F, TOP, [])
    H.wall("y", xR, 1, yF + T_IN, yB - T_IN, F, TOP, [])
    # storefront glass: aluminium mullions every ~8 studs, kick plates
    for (a, b, v0, v1) in store:
        H.uvd("Glass", "x", a, b, v0, v1, yF - 0.06, yF + 0.06)
        H.col(a, yF - 0.06, F, b, yF + 0.06, v1, "glass")
        n = max(1, round((b - a) / 8))
        for k in range(n + 1):
            u = a + (b - a) * k / n
            H.uvd("Metal", "x", u - 0.2, u + 0.2, v0, v1, yF - T_OUT - 0.15, yF + 0.15)
        H.uvd("Metal", "x", a, b, F, v0, yF - T_OUT - 0.15, yF + 0.15)
        H.uvd("Metal", "x", a, b, v1 - 0.2, v1 + 0.2, yF - T_OUT - 0.15, yF + 0.15)
    H.door("x", yF, -1, -4.4, 0.0, F, F + 8.8)
    H.door("x", yF, -1, 0.0, 4.4, F, F + 8.8, hinge_at_u0=False)
    for (a, b) in ((-6.0, -4.95), (4.95, 6.0)):
        H.uvd("Glass", "x", a, b, F + 0.4, F + 8.8, yF - 0.06, yF + 0.06)
        H.col(a, yF - 0.06, F, b, yF + 0.06, F + 8.8, "glass")
    H.uvd("Glass", "x", -6.0, 6.0, F + 9.35, F + 11.2, yF - 0.06, yF + 0.06)
    H.col(-6.0, yF - 0.06, F + 8.8, 6.0, yF + 0.06, F + 11.2, "glass")
    H.uvd("Metal", "x", -6.0, 6.0, F + 8.8, F + 9.35, yF - T_OUT - 0.2, yF + 0.2)
    # sign band (the shop name goes on it in Studio) and the awning
    H.p("Sign").box(-63.0, yF - T_OUT - 0.9, 14.2, 63.0, yF - T_OUT, 18.6)
    H.notes["signFace"] = {"min": [-63.0, 14.2], "max": [63.0, 18.6], "y": yF - T_OUT - 0.9}
    H.shed_roof(-62.0, yF - 9.5, 62.0, yF - T_OUT, 13.9, 12.2, kind="Awning")
    for k in range(13):                                   # awning valance scallops
        x = -62.0 + k * (124.0 / 13)
        H.p("Awning").box(x + 0.4, yF - 9.7, 11.2, x + 124.0 / 13 - 0.4, yF - 9.4, 12.2)
    H.col(-62.0, yF - 9.5, 11.7, 62.0, yF - T_OUT, 13.9, "awning")
    # back: service door, loading door, window
    H.door("x", yB, 1, -50.0, -45.4, F, F + 8.6, glass=False, kind="service")
    H.garage_door("x", yB, 1, 20.0, 34.0, F, F + 12.0)
    H.window("x", yB, 1, -30.0, -24.0, F + 6.0, F + 10.0, mullions=False)
    H.slab("Foundation", 18.0, yB + T_OUT, 36.0, yB + 9.0, 0, F + 3.2, tag="dock")      # loading dock
    # side pilasters + base course
    for side in (xL - T_OUT, xR + T_OUT):
        s = -1 if side < 0 else 1
        for k in range(5):
            y = yF + 4.0 + k * (yB - yF - 8.0) / 4
            H.p("Trim").box(min(side, side + s * 0.6), y - 1.0, F, max(side, side + s * 0.6), y + 1.0, PAR)
    H.p("Trim").box(xL - T_OUT - 0.3, yF - T_OUT - 0.3, F - 0.3, xR + T_OUT + 0.3, yF - T_OUT, F + 0.8)
    # flat roof, parapet, coping, rooftop units, hatch
    H.slab("Ceiling", xL, yF, xR, yB, TOP - 0.6, TOP, tag="ceiling")
    H.p("Roof").box(xL - T_OUT, yF - T_OUT, TOP, xR + T_OUT, yB + T_OUT, TOP + 0.6)
    H.col(xL - T_OUT, yF - T_OUT, TOP, xR + T_OUT, yB + T_OUT, TOP + 0.6, "roof")
    for (x0, y0, x1, y1) in ((xL - T_OUT, yF - T_OUT, xR + T_OUT, yF - T_OUT + 0.8), (xL - T_OUT, yB + T_OUT - 0.8, xR + T_OUT, yB + T_OUT),
                             (xL - T_OUT, yF - T_OUT, xL - T_OUT + 0.8, yB + T_OUT), (xR + T_OUT - 0.8, yF - T_OUT, xR + T_OUT, yB + T_OUT)):
        H.p("WallsOut").box(x0, y0, TOP + 0.6, x1, y1, PAR)
        H.p("Trim").box(x0 - 0.15, y0 - 0.15, PAR, x1 + 0.15, y1 + 0.15, PAR + 0.35)
        H.col(x0, y0, TOP + 0.6, x1, y1, PAR, "parapet")
    for (x, y) in ((-35.0, 8.0), (0.0, 12.0), (35.0, 8.0)):
        H.p("Metal").box(x - 4.0, y - 3.0, TOP + 0.6, x + 4.0, y + 3.0, TOP + 4.2)
        H.p("Trim").box(x - 2.0, y - 2.0, TOP + 4.2, x + 2.0, y + 2.0, TOP + 4.5)
        H.col(x - 4.0, y - 3.0, TOP + 0.6, x + 4.0, y + 3.0, TOP + 4.2, "ac")
    H.p("Metal").box(48.0, 20.0, TOP + 0.6, 52.0, 24.0, TOP + 1.8)
    return H


# ---------------------------------------------------------------- school, main building
def school_main():
    H = House("SchoolMain")
    F, S, F2, TOP, PAR = 1.2, 13.0, 15.2, 28.2, 31.0
    xL, xR, yF, yB = -129.45, 129.45, -34.45, 34.45
    H.slab("Foundation", xL - 1.0, yF - 1.0, xR + 1.0, yB + 1.0, 0, F - 0.35)
    H.slab("Tile", xL, yF, xR, yB, F - 0.35, F)
    run = 18.2
    holes = []
    for (sx0, sx1) in ((xL + T_IN + 0.3, xL + T_IN + 5.8), (xR - T_IN - 5.8, xR - T_IN - 0.3)):
        sy = -run / 2
        H.stairs(sx0, sx1, sy, run, F, F2, 14)
        holes.append((sx0 - 0.3, sy, sx1 + 0.3, sy + run))
    H.slab("Tile", xL, yF, xR, yB, F2 - 1.0, F2, holes=holes)
    H.slab("Ceiling", xL, yF, xR, yB, F2 - 1.3, F2 - 1.0, tag=None, holes=holes)
    H.slab("Ceiling", xL, yF, xR, yB, TOP - 0.6, TOP, tag="ceiling")
    cols = [x for x in range(-122, 123, 13) if abs(x + 3) > 17]      # window columns, skipping the entry
    w1 = [(x - 3.0, x + 3.0, F + 3.0, F + 10.0) for x in cols]
    w2 = [(x - 3.0, x + 3.0, F2 + 2.5, F2 + 9.5) for x in cols]
    entry = [(-12.0, -3.2, F, F + 11.5), (3.2, 12.0, F, F + 11.5)]
    H.wall("x", yF, -1, xL - T_OUT, xR + T_OUT, F, F2, w1 + entry, outer_kind="Brick")
    H.wall("x", yF, -1, xL - T_OUT, xR + T_OUT, F2, TOP, w2 + [(-12.0, 12.0, F2 + 2.5, F2 + 9.5)])
    backdoor = [(-5.0, 5.0, F, F + 9.0)]
    w1b = [o for o in w1 if abs((o[0] + o[1]) / 2) > 9] + [(-15.0, -9.0, F + 3.0, F + 10.0), (9.0, 15.0, F + 3.0, F + 10.0)]
    H.wall("x", yB, 1, xL - T_OUT, xR + T_OUT, F, F2, w1b + backdoor, outer_kind="Brick")
    H.wall("x", yB, 1, xL - T_OUT, xR + T_OUT, F2, TOP, w2 + [(-12.0, 12.0, F2 + 2.5, F2 + 9.5)])
    sidew1 = [(y - 3.0, y + 3.0, F + 3.0, F + 10.0) for y in (-20.0, 20.0)]
    sidew2 = [(y - 3.0, y + 3.0, F2 + 2.5, F2 + 9.5) for y in (-20.0, 20.0)]
    for (x, o) in ((xL, -1), (xR, 1)):
        H.wall("y", x, o, yF + T_IN, yB - T_IN, F, F2, sidew1 + [(-3.0, 3.0, F, F + 8.8)], outer_kind="Brick")
        H.wall("y", x, o, yF + T_IN, yB - T_IN, F2, TOP, sidew2)
        H.door("y", x, o, -3.0, 3.0, F, F + 8.8, kind="side")
        for (a, b, v0, v1) in sidew1 + sidew2:
            H.window("y", x, o, a, b, v0, v1)

    def schoolwin(axis, fixed, outward, a, b, v0, v1):
        H.window(axis, fixed, outward, a, b, v0, v1, mullions=False)
        m0, m1 = fixed + outward * 0.06, fixed + outward * 0.22
        H.uvd("Trim", axis, (a + b) / 2 - 0.12, (a + b) / 2 + 0.12, v0, v1, m0, m1)
        H.uvd("Trim", axis, a, b, v0 + (v1 - v0) * 0.38 - 0.12, v0 + (v1 - v0) * 0.38 + 0.12, m0, m1)
    for (a, b, v0, v1) in w1 + w2 + [(-12.0, 12.0, F2 + 2.5, F2 + 9.5)]:
        schoolwin("x", yF, -1, a, b, v0, v1)
    for (a, b, v0, v1) in w1b + w2 + [(-12.0, 12.0, F2 + 2.5, F2 + 9.5)]:
        schoolwin("x", yB, 1, a, b, v0, v1)
    for (a0, a1) in ((-12.0, -3.2), (3.2, 12.0)):
        m = (a0 + a1) / 2
        H.door("x", yF, -1, a0, m, F, F + 9.0)
        H.door("x", yF, -1, m, a1, F, F + 9.0, hinge_at_u0=False)
        H.uvd("Glass", "x", a0, a1, F + 9.55, F + 11.5, yF - 0.06, yF + 0.06)
        H.col(a0, yF - 0.06, F + 9.0, a1, yF + 0.06, F + 11.5, "glass")
        H.uvd("Metal", "x", a0, a1, F + 9.0, F + 9.55, yF - T_OUT - 0.2, yF + 0.2)
    H.door("x", yB, 1, -5.0, 0.0, F, F + 9.0, kind="back")
    H.door("x", yB, 1, 0.0, 5.0, F, F + 9.0, hinge_at_u0=False, kind="back")
    # brick/stucco band, parapet with coping, roof
    H.p("Trim").box(xL - T_OUT - 0.3, yF - T_OUT - 0.35, F2 - 1.2, xR + T_OUT + 0.3, yB + T_OUT + 0.35, F2 - 0.4)
    H.p("Roof").box(xL - T_OUT, yF - T_OUT, TOP, xR + T_OUT, yB + T_OUT, TOP + 0.6)
    H.col(xL - T_OUT, yF - T_OUT, TOP, xR + T_OUT, yB + T_OUT, TOP + 0.6, "roof")
    for (x0, y0, x1, y1) in ((xL - T_OUT, yF - T_OUT, xR + T_OUT, yF - T_OUT + 0.8), (xL - T_OUT, yB + T_OUT - 0.8, xR + T_OUT, yB + T_OUT),
                             (xL - T_OUT, yF - T_OUT, xL - T_OUT + 0.8, yB + T_OUT), (xR + T_OUT - 0.8, yF - T_OUT, xR + T_OUT, yB + T_OUT)):
        H.p("WallsOut").box(x0, y0, TOP + 0.6, x1, y1, PAR)
        H.p("Trim").box(x0 - 0.15, y0 - 0.15, PAR, x1 + 0.15, y1 + 0.15, PAR + 0.4)
        H.col(x0, y0, TOP + 0.6, x1, y1, PAR, "parapet")
    # entry tower with the school sign band, canopy on four columns
    ty0 = yF - T_OUT - 6.0
    H.p("WallsOut").box(-18.0, ty0, F2 + 10.0, 18.0, yF - T_OUT, 38.0)
    H.p("WallsOut").box(-18.0, ty0, F, -14.0, yF - T_OUT, F2 + 10.0)
    H.p("WallsOut").box(14.0, ty0, F, 18.0, yF - T_OUT, F2 + 10.0)
    H.col(-18.0, ty0, F, -14.0, yF - T_OUT, F2 + 10.0, "tower")
    H.col(14.0, ty0, F, 18.0, yF - T_OUT, F2 + 10.0, "tower")
    H.p("Trim").box(-18.4, ty0 - 0.4, 38.0, 18.4, yF - T_OUT, 38.6)
    H.p("Sign").box(-14.0, ty0 - 0.6, 30.0, 14.0, ty0, 35.0)
    H.notes["signFace"] = {"min": [-14.0, 30.0], "max": [14.0, 35.0], "y": ty0 - 0.6}
    cy0 = ty0 - 10.0
    H.p("Roof").box(-16.0, cy0, F + 12.6, 16.0, ty0, F + 13.4)
    H.p("Trim").box(-16.2, cy0 - 0.2, F + 12.0, 16.2, cy0 + 0.3, F + 13.5)
    H.col(-16.0, cy0, F + 12.6, 16.0, ty0, F + 13.4, "canopy")
    for x in (-14.5, -5.0, 5.0, 14.5):
        H.column(x, cy0 + 1.0, 0.0, F + 12.0, r=0.6)
    H.slab("Foundation", -20.0, cy0 - 2.0, 20.0, yF - T_OUT, 0, F - 0.35, tag="porch")
    # flagpole
    H.p("Foundation").box(36.0, -64.0, 0, 40.0, -60.0, 1.0)
    H.p("Metal").box(37.8, -62.2, 1.0, 38.2, -61.8, 42.0)
    H.p("Metal").box(37.6, -62.4, 42.0, 38.4, -61.6, 42.8)
    H.notes["flag"] = [38.0, -62.0, 40.0]
    # covered walkway to the classroom wing
    H.slab("Foundation", -152.0, yB + T_OUT, -140.0, 60.0 - T_OUT, 0, F - 0.35, tag="walkway")
    H.p("Roof").box(-153.0, yB + T_OUT, F + 11.0, -139.0, 60.0 - T_OUT, F + 11.7)
    H.col(-153.0, yB + T_OUT, F + 11.0, -139.0, 60.0 - T_OUT, F + 11.7, "walkway")
    for y in (40.0, 47.5, 55.0):
        for x in (-151.5, -140.5):
            H.column(x, y, 0.0, F + 11.0, r=0.4)
    return H


# ---------------------------------------------------------------- school, classroom wing
def school_wing():
    H = House("SchoolWing")
    F, TOP, PAR = 1.2, 14.2, 17.0
    xL, xR, yF, yB = -184.45, -115.55, 60.55, 259.45
    H.slab("Foundation", xL - 1.0, yF - 1.0, xR + 1.0, yB + 1.0, 0, F - 0.35)
    H.slab("Tile", xL, yF, xR, yB, F - 0.35, F)
    H.slab("Ceiling", xL, yF, xR, yB, TOP - 0.6, TOP, tag="ceiling")
    rows = [y for y in range(68, 253, 12)]
    w = [(y - 3.0, y + 3.0, F + 3.2, F + 10.0) for y in rows]
    H.wall("y", xL, -1, yF + T_IN, yB - T_IN, F, TOP, w, outer_kind="Brick")
    H.wall("y", xR, 1, yF + T_IN, yB - T_IN, F, TOP, w, outer_kind="Brick")
    ends = [(-155.0, -145.0, F, F + 9.0), (-176.0, -170.0, F + 3.2, F + 10.0), (-130.0, -124.0, F + 3.2, F + 10.0)]
    H.wall("x", yF, -1, xL - T_OUT, xR + T_OUT, F, TOP, ends, outer_kind="Brick")
    H.wall("x", yB, 1, xL - T_OUT, xR + T_OUT, F, TOP, ends, outer_kind="Brick")
    for (a, b, v0, v1) in w:
        H.window("y", xL, -1, a, b, v0, v1)
        H.window("y", xR, 1, a, b, v0, v1)
    for (yy, o) in ((yF, -1), (yB, 1)):
        H.door("x", yy, o, -155.0, -150.0, F, F + 9.0, kind="end")
        H.door("x", yy, o, -150.0, -145.0, F, F + 9.0, hinge_at_u0=False, kind="end")
        for (a, b, v0, v1) in ends[1:]:
            H.window("x", yy, o, a, b, v0, v1)
    H.p("Trim").box(xL - T_OUT - 0.3, yF - T_OUT - 0.3, TOP - 1.0, xR + T_OUT + 0.3, yB + T_OUT + 0.3, TOP - 0.3)
    H.p("Roof").box(xL - T_OUT, yF - T_OUT, TOP, xR + T_OUT, yB + T_OUT, TOP + 0.6)
    H.col(xL - T_OUT, yF - T_OUT, TOP, xR + T_OUT, yB + T_OUT, TOP + 0.6, "roof")
    for (x0, y0, x1, y1) in ((xL - T_OUT, yF - T_OUT, xR + T_OUT, yF - T_OUT + 0.8), (xL - T_OUT, yB + T_OUT - 0.8, xR + T_OUT, yB + T_OUT),
                             (xL - T_OUT, yF - T_OUT, xL - T_OUT + 0.8, yB + T_OUT), (xR + T_OUT - 0.8, yF - T_OUT, xR + T_OUT, yB + T_OUT)):
        H.p("WallsOut").box(x0, y0, TOP + 0.6, x1, y1, PAR)
        H.p("Trim").box(x0 - 0.15, y0 - 0.15, PAR, x1 + 0.15, y1 + 0.15, PAR + 0.4)
        H.col(x0, y0, TOP + 0.6, x1, y1, PAR, "parapet")
    return H


for builder in (shop, school_main, school_wing):
    H = builder()
    meta[H.style] = export_house(H)
with open(os.path.join(OUT, "civic.json"), "w") as f:
    json.dump(meta, f)
scene, cam = setup_render()
render_views(scene, cam, ["Shop"], {"front34": ((-110, -170, 60), (0, 0, 8)), "rear34": ((120, 160, 60), (0, 0, 8)), "storefront": ((-30, -70, 10), (0, -36, 8))}, "Shop")
render_views(scene, cam, ["SchoolMain", "SchoolWing"], {"front34": ((170, -330, 160), (-40, 60, 10)), "entry": ((40, -110, 25), (0, -40, 14)), "rear34": ((-380, 420, 170), (-90, 80, 10))}, "School")
print("NEONCOAST_DONE", json.dumps({k: {"max": v["maxTriangles"], "ext": v["extents_studs"], "colliders": len(v["colliders"])} for k, v in meta.items()}))
