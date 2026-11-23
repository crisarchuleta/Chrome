# Neon Coast: Florida-style houses from real references (stucco + tile, shallow wide-eaved hip roofs, screened
# pool cages, Mediterranean two-stories, raised Key West cottages). Run headless:
#   blender --background --factory-startup --python build_florida.py
# Scale: about 1.15 studs per real foot (12-stud stories, 8.4-stud doors, an 18 x 9 two-car garage door).
import sys, json, os, math
sys.path.insert(0, r"C:\Users\Crisa\Documents\NeonCoast_Blender")
import importlib, nc_kit, nc_extra
importlib.reload(nc_kit)
importlib.reload(nc_extra)
from nc_extra import *
import bmesh
from mathutils import Vector, Matrix

reset()
nc_kit.COLORS.update({"Screen": (0.25, 0.27, 0.28), "Water": (0.25, 0.65, 0.85), "PoolTile": (0.55, 0.80, 0.90),
                      "Pavers": (0.80, 0.72, 0.60), "MetalRoof": (0.80, 0.82, 0.83), "Lattice": (0.95, 0.95, 0.93)})


def beam(H, kind, p0, p1, w, h, up=(0, 0, 1)):
    """Box from p0 to p1 with a w x h cross-section (w across, h roughly up)."""
    a, b = Vector(p0), Vector(p1)
    d = b - a
    if d.length < 1e-4:
        return
    z = d.normalized()
    x = Vector(up).cross(z)
    if x.length < 1e-4:
        x = Vector((1, 0, 0)).cross(z)
    x.normalize()
    y = z.cross(x)
    m = Matrix((x, y, z)).transposed().to_4x4()
    m.translation = (a + b) / 2
    bmesh.ops.create_cube(H.p(kind).bm, size=1.0, matrix=m @ Matrix.Diagonal((w, h, d.length, 1)))


def hip_caps(H, x0, y0, x1, y1, zb, pitch, over, kind="Roof"):
    """Barrel caps along the four hips of a hip roof built by House.hip_roof with the same numbers."""
    x0, y0, x1, y1 = x0 - over, y0 - over, x1 + over, y1 + over
    zb2 = zb - 0.25
    w, d = x1 - x0, y1 - y0
    if w >= d:
        h = d / 2 * pitch
        r0, r1, yc = x0 + d / 2, x1 - d / 2, (y0 + y1) / 2
        hips = [((x0, y0), (r0, yc)), ((x0, y1), (r0, yc)), ((x1, y0), (r1, yc)), ((x1, y1), (r1, yc))]
    else:
        h = w / 2 * pitch
        r0, r1, xc = y0 + w / 2, y1 - w / 2, (x0 + x1) / 2
        hips = [((x0, y0), (xc, r0)), ((x1, y0), (xc, r0)), ((x0, y1), (xc, r1)), ((x1, y1), (xc, r1))]
    for (a, b) in hips:
        beam(H, kind, (a[0], a[1], zb2 + 0.15), (b[0], b[1], zb2 + h + 0.15), 0.7, 0.45)


def bahama(H, axis, fixed, outward, u0, u1, v1):
    """Top-hinged louvered Bahama shutter propped out over a window (classic Florida)."""
    face = fixed + outward * T_OUT
    um = (u0 + u1) / 2
    w = u1 - u0 + 0.8
    if axis == "x":
        top = (um, face + outward * 0.15, v1 + 0.4)
        bot = (um, face + outward * 2.3, v1 - 3.6)
        beam(H, "Shutter", top, bot, w, 0.22)
        for k in range(1, 7):
            t = k / 7
            p = (um, top[1] + (bot[1] - top[1]) * t + outward * 0.12, top[2] + (bot[2] - top[2]) * t)
            q = (p[0] + 0.01, p[1], p[2])
            beam(H, "Shutter", (um - w / 2 + 0.2, p[1], p[2]), (um + w / 2 - 0.2, p[1], p[2]), 0.25, 0.12)
        for s in (-1, 1):
            beam(H, "Metal", (um + s * (w / 2 - 0.4), face, v1 - 2.6), (um + s * (w / 2 - 0.4), bot[1], bot[2] + 0.3), 0.12, 0.12)
    else:
        top = (face + outward * 0.15, um, v1 + 0.4)
        bot = (face + outward * 2.3, um, v1 - 3.6)
        beam(H, "Shutter", top, bot, w, 0.22, up=(0, 0, 1))
        for k in range(1, 7):
            t = k / 7
            x = top[0] + (bot[0] - top[0]) * t + outward * 0.12
            z = top[2] + (bot[2] - top[2]) * t
            beam(H, "Shutter", (x, um - w / 2 + 0.2, z), (x, um + w / 2 - 0.2, z), 0.25, 0.12)


def coach_light(H, x, y, z):
    lantern(H, x, y, z, facing=-1)


def ac_unit(H, x, y, facing="x"):
    H.p("Foundation").box(x - 2.2, y - 2.2, 0, x + 2.2, y + 2.2, 0.35)
    H.p("Metal").box(x - 1.7, y - 1.7, 0.35, x + 1.7, y + 1.7, 3.2)
    H.p("Trim").box(x - 1.75, y - 1.75, 3.2, x + 1.75, y + 1.75, 3.35)
    H.p("Screen").box(x - 1.2, y - 1.2, 3.35, x + 1.2, y + 1.2, 3.4)
    H.col(x - 1.7, y - 1.7, 0, x + 1.7, y + 1.7, 3.35, "ac")


def pool_cage(H, x0, y0, x1, y1, deck_z, h=12.0, door_at=None):
    """Screened pool enclosure: paver deck, a pool, aluminium frame, screen panels, a screen roof."""
    px0, py0, px1, py1 = x0 + 7.0, y0 + 9.0, x1 - 7.0, y1 - 6.0
    H.slab("Pavers", x0, y0, x1, y1, deck_z - 0.3, deck_z, tag="deck", holes=[(px0, py0, px1, py1)])
    H.p("PoolTile").box(px0, py0, deck_z - 5.0, px1, py1, deck_z - 4.6)
    for (a0, b0, a1, b1) in ((px0, py0, px1, py0 + 0.4), (px0, py1 - 0.4, px1, py1), (px0, py0, px0 + 0.4, py1), (px1 - 0.4, py0, px1, py1)):
        H.p("PoolTile").box(a0, b0, deck_z - 5.0, a1, b1, deck_z - 0.3)
    H.p("Trim").box(px0 - 0.6, py0 - 0.6, deck_z - 0.3, px1 + 0.6, py0, deck_z + 0.1)          # coping
    H.p("Trim").box(px0 - 0.6, py1, deck_z - 0.3, px1 + 0.6, py1 + 0.6, deck_z + 0.1)
    H.p("Trim").box(px0 - 0.6, py0, deck_z - 0.3, px0, py1, deck_z + 0.1)
    H.p("Trim").box(px1, py0, deck_z - 0.3, px1 + 0.6, py1, deck_z + 0.1)
    H.p("Water").box(px0 + 0.4, py0 + 0.4, deck_z - 4.6, px1 - 0.4, py1 - 0.4, deck_z - 0.7)
    H.notes["pool"] = {"min": [px0 + 0.4, py0 + 0.4, deck_z - 4.6], "max": [px1 - 0.4, py1 - 0.4, deck_z - 0.7]}
    top = deck_z + h
    peak = top + 4.5
    step = 6.0
    # posts and screen walls on the three open sides (the house closes the fourth)
    sides = [((x0, y1), (x1, y1)), ((x0, y0), (x0, y1)), ((x1, y0), (x1, y1))]
    for (a, b) in sides:
        L = math.hypot(b[0] - a[0], b[1] - a[1])
        n = max(1, round(L / step))
        for k in range(n + 1):
            t = k / n
            x, y = a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t
            H.p("Trim").box(x - 0.3, y - 0.3, deck_z, x + 0.3, y + 0.3, top)
        for k in range(n):
            t0, t1 = k / n, (k + 1) / n
            xa, ya = a[0] + (b[0] - a[0]) * t0, a[1] + (b[1] - a[1]) * t0
            xb, yb = a[0] + (b[0] - a[0]) * t1, a[1] + (b[1] - a[1]) * t1
            if door_at and abs((xa + xb) / 2 - door_at[0]) < 3.1 and abs((ya + yb) / 2 - door_at[1]) < 3.1:
                H.p("Trim").box(min(xa, xb) - 0.15, min(ya, yb) - 0.15, deck_z + 8.0, max(xa, xb) + 0.15, max(ya, yb) + 0.15, deck_z + 8.3)
                H.p("Screen").box(min(xa, xb), min(ya, yb) - 0.03, deck_z + 8.3, max(xa, xb), max(ya, yb) + 0.03, top) if ya == yb else \
                    H.p("Screen").box(min(xa, xb) - 0.03, min(ya, yb), deck_z + 8.3, max(xa, xb) + 0.03, max(ya, yb), top)
                continue
            if ya == yb:
                H.p("Screen").box(min(xa, xb), ya - 0.03, deck_z, max(xa, xb), ya + 0.03, top)
                H.p("Trim").box(min(xa, xb), ya - 0.18, deck_z + 3.0, max(xa, xb), ya + 0.18, deck_z + 3.3)    # kick rail
                H.col(min(xa, xb), ya - 0.1, deck_z, max(xa, xb), ya + 0.1, top, "screen")
            else:
                H.p("Screen").box(xa - 0.03, min(ya, yb), deck_z, xa + 0.03, max(ya, yb), top)
                H.p("Trim").box(xa - 0.18, min(ya, yb), deck_z + 3.0, xa + 0.18, max(ya, yb), deck_z + 3.3)
                H.col(xa - 0.1, min(ya, yb), deck_z, xa + 0.1, max(ya, yb), top, "screen")
    H.p("Trim").box(x0 - 0.35, y1 - 0.35, top - 0.5, x1 + 0.35, y1 + 0.35, top)
    H.p("Trim").box(x0 - 0.35, y0, top - 0.5, x0 + 0.35, y1, top)
    H.p("Trim").box(x1 - 0.35, y0, top - 0.5, x1 + 0.35, y1, top)
    # mansard-style screen roof rising to a flat centre panel
    ix0, iy0, ix1, iy1 = x0 + 6.0, y0 + 4.0, x1 - 6.0, y1 - 6.0
    for (a, b) in (((x0, y1), (ix0, iy1)), ((x1, y1), (ix1, iy1)), ((x0, y0), (ix0, iy0)), ((x1, y0), (ix1, iy0))):
        beam(H, "Trim", (a[0], a[1], top), (b[0], b[1], peak), 0.4, 0.4)
    H.p("Trim").box(ix0 - 0.2, iy0 - 0.2, peak - 0.3, ix1 + 0.2, iy1 + 0.2, peak)
    H.p("Screen").box(ix0, iy0, peak - 0.35, ix1, iy1, peak - 0.3)
    H.p("Screen").solid([(x0, y1, top), (x1, y1, top), (ix1, iy1, peak), (ix0, iy1, peak)], [(0, 1, 2, 3), (3, 2, 1, 0)])
    H.p("Screen").solid([(x0, y0, top), (x0, y1, top), (ix0, iy1, peak), (ix0, iy0, peak)], [(0, 1, 2, 3), (3, 2, 1, 0)])
    H.p("Screen").solid([(x1, y1, top), (x1, y0, top), (ix1, iy0, peak), (ix1, iy1, peak)], [(0, 1, 2, 3), (3, 2, 1, 0)])
    for k in range(1, 6):
        x = x0 + (x1 - x0) * k / 6
        beam(H, "Trim", (x, y1, top), (min(max(x, ix0), ix1), iy1, peak), 0.25, 0.25)


# ------------------------------------------------------------------ Florida stucco ranch with a pool cage
def florida_ranch():
    H = House("FloridaRanch")
    F, TOP = 1.0, 11.6
    xL, xR, yF, yB = -33.0, 12.0, -16.0, 18.0
    gx1, gyF, gyB = 34.0, -20.0, 14.0
    H.p("Foundation").box(xL - 1.0, yF - 1.0, 0, xR + 0.5, yB + 1.0, F - 0.35)
    H.col(xL - 1.0, yF - 1.0, 0, xR + 0.5, yB + 1.0, F - 0.35, "floor")
    H.slab("Tile", xL, yF, xR, yB, F - 0.35, F)
    H.slab("Foundation", xR, gyF, gx1, gyB, 0, 0.35)
    W = (F + 3.2, F + 8.4)
    front = [(-11.3, -6.7, F, F + 8.4), (-30.0, -24.0, W[0], W[1]), (-21.0, -15.0, W[0], W[1]), (2.0, 8.0, W[0], W[1])]
    H.wall("x", yF, -1, xL - T_OUT, xR, F, TOP, front)
    back = [(-26.0, -14.0, F, F + 8.4), (-6.0, 0.0, W[0] + 1.2, W[1]), (4.0, 9.0, W[0], W[1])]
    H.wall("x", yB, 1, xL - T_OUT, xR, F, TOP, back)
    H.wall("y", xL, -1, yF + T_IN, yB - T_IN, F, TOP, [(-6.0, 0.0, W[0], W[1]), (6.0, 11.0, W[0], W[1])])
    H.wall("y", xR, 1, yF + T_IN, yB - T_IN, F, TOP, [(4.0, 8.2, F, F + 8.4)])
    H.wall("x", gyF, -1, xR - T_OUT, gx1 + T_OUT, 0.35, TOP, [(14.0, 32.0, 0.35, 9.35)])
    H.garage_door("x", gyF, -1, 14.0, 32.0, 0.35, 9.35)
    H.wall("x", gyB, 1, xR + T_IN, gx1 + T_OUT, 0.35, TOP, [])
    H.wall("y", gx1, 1, gyF + T_IN, gyB - T_IN, 0.35, TOP, [(0.0, 4.2, 0.35, 8.75)])
    H.wall("y", xR, -1, gyF + T_IN, yF - T_OUT, 0.35, TOP, [])                    # garage side that sticks out front
    for (a, b, v0, v1) in front[1:]:
        H.window("x", yF, -1, a, b, v0, v1, mullions=True)
        bahama(H, "x", yF, -1, a, b, v1)
    for (a, b, v0, v1) in back[1:]:
        H.window("x", yB, 1, a, b, v0, v1)
    for (a, b) in ((-6.0, 0.0), (6.0, 11.0)):
        H.window("y", xL, -1, a, b, W[0], W[1])
    H.door("x", yF, -1, -11.3, -6.7, F, F + 8.4)
    H.door("x", yB, 1, -26.0, -20.0, F, F + 8.4, kind="slider")
    H.door("x", yB, 1, -20.0, -14.0, F, F + 8.4, hinge_at_u0=False, kind="slider")
    H.door("y", xR, 1, 4.0, 8.2, F, F + 8.4, glass=False, kind="inner")
    H.door("y", gx1, 1, 0.0, 4.2, 0.35, 8.75, glass=False, kind="garageSide")
    # stucco banding: a raised band round the base and the eave line
    H.p("Trim").box(xL - T_OUT - 0.25, yF - T_OUT - 0.25, F - 0.35, gx1 + T_OUT + 0.25, yF - T_OUT, F + 0.4)
    H.p("Trim").box(xL - T_OUT - 0.25, yF - T_OUT - 0.25, TOP - 0.9, xR, yF - T_OUT, TOP - 0.3)
    coach_light(H, 12.6, gyF - T_OUT, 6.8)
    coach_light(H, 33.4, gyF - T_OUT, 6.8)
    # entry portico with two columns and its own little hip roof
    H.slab("Foundation", -15.0, yF - 6.5, -3.0, yF - T_OUT, 0, F - 0.35, tag="porch")
    for x in (-14.0, -4.0):
        H.column(x, yF - 5.6, F - 0.35, TOP - 0.8, r=0.55)
    H.p("Trim").box(-15.0, yF - 6.5, TOP - 1.4, -3.0, yF - T_OUT, TOP - 0.8)
    H.hip_roof(-15.0, yF - 6.5, -3.0, yF - T_OUT, TOP - 0.8, 0.4, 0.4)
    # ceilings, roofs (shallow pitch, wide eaves), hip caps
    H.slab("Ceiling", xL, yF, xR, yB, TOP - 0.45, TOP, tag="ceiling")
    H.slab("Ceiling", xR, gyF, gx1, gyB, TOP - 0.45, TOP, tag="ceiling")
    H.hip_roof(xL - T_OUT, yF - T_OUT, xR + T_OUT, yB + T_OUT, TOP, 0.34, 2.4)
    hip_caps(H, xL - T_OUT, yF - T_OUT, xR + T_OUT, yB + T_OUT, TOP, 0.34, 2.4)
    H.hip_roof(xR, gyF - T_OUT, gx1 + T_OUT, gyB + T_OUT, TOP, 0.34, 2.2)
    hip_caps(H, xR, gyF - T_OUT, gx1 + T_OUT, gyB + T_OUT, TOP, 0.34, 2.2)
    # back: covered lanai under a shed roof, then the screened pool cage
    H.slab("Pavers", -30.0, yB + T_OUT, 8.0, yB + 9.0, 0, F - 0.35, tag="lanai")
    H.shed_roof(-30.0, yB + T_OUT, 8.0, yB + 9.0, TOP - 0.4, TOP - 2.0) if False else None
    pool_cage(H, -31.0, yB + T_OUT, 10.0, yB + 40.0, F - 0.35, h=11.0, door_at=(10.0, yB + 20.0))
    ac_unit(H, xL - T_OUT - 3.5, 6.0)
    H.p("Metal").box(xL - T_OUT - 0.4, -4.0, 4.0, xL - T_OUT, -2.8, 5.6)          # electric meter
    return H


# ------------------------------------------------------------------ Mediterranean two-story
def mediterranean():
    H = House("Mediterranean")
    F, F2, TOP = 1.2, 14.2, 26.2
    xL, xR, yF, yB = -30.0, 10.0, -17.0, 18.0
    gx1, gyF, gyB = 36.0, -15.0, 16.0
    H.p("Foundation").box(xL - 1.0, yF - 1.0, 0, xR + 0.5, yB + 1.0, F - 0.35)
    H.col(xL - 1.0, yF - 1.0, 0, xR + 0.5, yB + 1.0, F - 0.35, "floor")
    H.slab("Tile", xL, yF, xR, yB, F - 0.35, F)
    H.slab("Foundation", xR, gyF, gx1, gyB, 0, 0.35)
    run = 19.5
    sx0, sx1 = xR - T_IN - 5.4, xR - T_IN - 0.4
    sy = yB - T_IN - 0.6 - run
    H.stairs(sx0, sx1, sy, run, F, F2, 13)
    hole = [(sx0 - 0.3, sy, sx1 + 0.3, sy + run)]
    H.slab("Floor", xL, yF, xR, yB, F2 - 1.0, F2, holes=hole)
    H.slab("Ceiling", xL, yF, xR, yB, F2 - 1.3, F2 - 1.0, tag=None, holes=hole)
    H.slab("Ceiling", xL, yF, xR, yB, TOP - 0.45, TOP, tag="ceiling")
    H.slab("Ceiling", xR, gyF, gx1, gyB, 12.0 - 0.45, 12.0, tag="ceiling")
    W1, W2 = (F + 3.0, F + 9.6), (F2 + 2.6, F2 + 8.6)
    f1 = [(-12.4, -7.6, F, F + 9.0), (-27.0, -21.0, W1[0], W1[1]), (0.0, 6.0, W1[0], W1[1])]
    f2 = [(-27.0, -21.0, W2[0], W2[1]), (-13.0, -7.0, W2[0], W2[1]), (0.0, 6.0, W2[0], W2[1])]
    H.wall("x", yF, -1, xL - T_OUT, xR + T_OUT, F, F2, f1)
    H.wall("x", yF, -1, xL - T_OUT, xR + T_OUT, F2, TOP, f2)
    b1 = [(-22.0, -10.0, F, F + 8.6), (0.0, 6.0, W1[0], W1[1])]
    b2 = [(-24.0, -18.0, W2[0], W2[1]), (-12.0, -6.0, W2[0], W2[1]), (0.0, 6.0, W2[0], W2[1])]
    H.wall("x", yB, 1, xL - T_OUT, xR + T_OUT, F, F2, b1)
    H.wall("x", yB, 1, xL - T_OUT, xR + T_OUT, F2, TOP, b2)
    s1 = [(-6.0, 0.0, W1[0], W1[1])]
    s2 = [(-6.0, 0.0, W2[0], W2[1]), (6.0, 11.0, W2[0], W2[1])]
    for (x, o, ex1, ex2) in ((xL, -1, s1, s2), (xR, 1, [(-4.0, 0.2, F, F + 8.4)], s2)):
        H.wall("y", x, o, yF + T_IN, yB - T_IN, F, F2, ex1)
        H.wall("y", x, o, yF + T_IN, yB - T_IN, F2, TOP, ex2)
    for (a, b, v0, v1) in f1[1:]:
        H.window("x", yF, -1, a, b, v0, v1, arch=True)
    for (a, b, v0, v1) in f2:
        H.window("x", yF, -1, a, b, v0, v1)
    for (a, b, v0, v1) in b1[1:] + b2:
        H.window("x", yB, 1, a, b, v0, v1)
    for (a, b, v0, v1) in s1 + s2:
        H.window("y", xL, -1, a, b, v0, v1)
    for (a, b, v0, v1) in s2:
        H.window("y", xR, 1, a, b, v0, v1)
    # juliet balcony (wrought iron) under the middle upstairs window
    railing(H, -13.6, yF - T_OUT - 1.4, -6.4, yF - T_OUT - 1.4, F2 + 1.0, height=2.6, spacing=0.6, kind="Metal")
    H.p("Trim").box(-14.0, yF - T_OUT - 1.8, F2 + 0.4, -6.0, yF - T_OUT, F2 + 1.0)
    # two-story entry tower with an arched opening and its own hip roof above the main eave
    ty0 = yF - T_OUT - 5.0
    for (a, b) in ((-16.0, -13.4), (-6.6, -4.0)):
        H.p("WallsOut").box(a, ty0, F, b, yF - T_OUT, TOP + 3.0)
        H.col(a, ty0, F, b, yF - T_OUT, TOP + 3.0, "tower")
    # upper tower wall with a real window opening (the window used to be stuck on the outside of a solid wall)
    wx0, wx1, wz0, wz1 = -11.2, -8.8, F + 15.5, F + 20.0
    H.p("WallsOut").box(-13.4, ty0, F + 12.0, -6.6, yF - T_OUT, wz0)
    H.p("WallsOut").box(-13.4, ty0, wz1, -6.6, yF - T_OUT, TOP + 3.0)
    H.p("WallsOut").box(-13.4, ty0, wz0, wx0, yF - T_OUT, wz1)
    H.p("WallsOut").box(wx1, ty0, wz0, -6.6, yF - T_OUT, wz1)
    H.p("WallsIn").box(wx0, ty0 + 1.0, wz0, wx1, yF - T_OUT, wz1)          # the tower room behind the glass
    for k in range(8):                                     # the arch: stepped voussoirs in trim
        t0, t1 = k / 8, (k + 1) / 8
        a0, a1 = -13.4 + 6.8 * t0, -13.4 + 6.8 * t1
        hh = math.sin((t0 + t1) / 2 * math.pi) * 2.4
        H.p("Trim").box(a0, ty0 - 0.3, F + 12.0 - 2.4 + hh - 0.6, a1, ty0 + 0.3, F + 12.0 - 2.4 + hh + 0.2)
        H.p("WallsOut").box(a0, ty0, F + 12.0 - 2.4 + hh, a1, yF - T_OUT, F + 12.0)
    H.window("x", ty0 + T_OUT, -1, wx0, wx1, wz0, wz1, mullions=False)       # set in the wall, flush outside
    H.hip_roof(-16.0, ty0, -4.0, yF - T_OUT, TOP + 3.0, 0.5, 1.2)
    hip_caps(H, -16.0, ty0, -4.0, yF - T_OUT, TOP + 3.0, 0.5, 1.2)
    H.slab("Pavers", -17.0, ty0 - 4.0, -3.0, yF - T_OUT, 0, F - 0.35, tag="porch")
    H.door("x", yF, -1, -12.4, -10.0, F, F + 9.0)
    H.door("x", yF, -1, -10.0, -7.6, F, F + 9.0, hinge_at_u0=False)
    lantern(H, -14.6, ty0, F + 7.5)
    lantern(H, -5.4, ty0, F + 7.5)
    H.door("x", yB, 1, -22.0, -16.0, F, F + 8.6, kind="slider")
    H.door("x", yB, 1, -16.0, -10.0, F, F + 8.6, hinge_at_u0=False, kind="slider")
    H.door("y", xR, 1, -4.0, 0.2, F, F + 8.4, glass=False, kind="inner")
    # floor-line band, quoins
    H.p("Trim").box(xL - T_OUT - 0.3, yF - T_OUT - 0.3, F2 - 1.2, xR + T_OUT + 0.3, yB + T_OUT + 0.3, F2 - 0.4)
    for (x, y) in ((xL - T_OUT, yF - T_OUT), (xR + T_OUT, yF - T_OUT), (xL - T_OUT, yB + T_OUT), (xR + T_OUT, yB + T_OUT)):
        for k in range(10):
            z = F + k * 2.5
            s = 0.6 if k % 2 == 0 else 0.4
            H.p("Trim").box(x - s, y - s, z, x + s, y + s, z + 1.2)
    # garage: two single doors, coach lights
    H.wall("x", gyF, -1, xR + T_OUT, gx1 + T_OUT, 0.35, 12.0, [(13.0, 22.0, 0.35, 8.85), (25.0, 34.0, 0.35, 8.85)])
    H.garage_door("x", gyF, -1, 13.0, 22.0, 0.35, 8.85)
    H.garage_door("x", gyF, -1, 25.0, 34.0, 0.35, 8.85)
    H.wall("x", gyB, 1, xR + T_OUT, gx1 + T_OUT, 0.35, 12.0, [])
    H.wall("y", gx1, 1, gyF + T_IN, gyB - T_IN, 0.35, 12.0, [(2.0, 6.2, 0.35, 8.75)])
    H.door("y", gx1, 1, 2.0, 6.2, 0.35, 8.75, glass=False, kind="garageSide")
    for x in (11.8, 23.5, 35.2):
        coach_light(H, x, gyF - T_OUT, 6.5)
    # roofs
    H.hip_roof(xL - T_OUT, yF - T_OUT, xR + T_OUT, yB + T_OUT, TOP, 0.4, 2.4)
    hip_caps(H, xL - T_OUT, yF - T_OUT, xR + T_OUT, yB + T_OUT, TOP, 0.4, 2.4)
    H.hip_roof(xR + T_OUT, gyF - T_OUT, gx1 + T_OUT, gyB + T_OUT, 12.0, 0.4, 2.0)
    hip_caps(H, xR + T_OUT, gyF - T_OUT, gx1 + T_OUT, gyB + T_OUT, 12.0, 0.4, 2.0)
    # back loggia: three arches on columns under a tile shed roof
    H.slab("Pavers", -28.0, yB + T_OUT, 8.0, yB + 10.0, 0, F - 0.35, tag="loggia")
    for x in (-27.0, -15.0, -3.0, 7.0):
        H.column(x, yB + 9.2, F - 0.35, F + 10.5, r=0.7)
    H.p("WallsOut").box(-28.0, yB + 8.4, F + 10.5, 8.0, yB + 10.0, F + 12.3)
    H.shed_roof(-28.5, yB + 10.5, 8.5, yB + T_OUT, F + 14.0, F + 12.3)
    ac_unit(H, gx1 + T_OUT + 3.5, 8.0)
    return H


# ------------------------------------------------------------------ Key West cottage (raised, tin roof, porch)
def key_west():
    H = House("KeyWest")
    F, TOP = 3.6, 15.6
    xL, xR, yF, yB = -20.0, 20.0, -14.0, 16.0
    for x in range(-20, 21, 8):                          # piers
        for y in (-22.0, -14.0, 1.0, 16.0):
            H.p("Foundation").box(x - 0.7, y - 0.7, 0, x + 0.7, y + 0.7, F - 0.4)
    for (a0, b0, a1, b1) in ((xL, yF - 0.1, xR, yF + 0.1), (xL, yB - 0.1, xR, yB + 0.1), (xL - 0.1, yF, xL + 0.1, yB), (xR - 0.1, yF, xR + 0.1, yB)):
        H.p("Lattice").box(a0, b0, 0.05, a1, b1, F - 0.4)                   # lattice skirt, ground to the floor framing
    # skirt board round the rim joist (back and sides; the porch covers the front): closes the band between the
    # lattice and the bottom of the siding, stopping just under the door sills
    sb = T_OUT + 0.1
    for (a0, b0, a1, b1) in ((xL - sb, yB + T_OUT, xR + sb, yB + sb),
                             (xL - sb, yF - T_OUT, xL - T_OUT, yB + T_OUT), (xR + T_OUT, yF - T_OUT, xR + sb, yB + T_OUT)):
        H.p("Trim").box(a0, b0, F - 0.6, a1, b1, F - 0.02)
    H.slab("Floor", xL, yF, xR, yB, F - 0.4, F)
    H.col(xL - 0.5, yF - 0.5, 0, xR + 0.5, yB + 0.5, F - 0.4, "floor")
    W = (F + 2.4, F + 9.4)
    front = [(-2.3, 2.3, F, F + 8.6), (-15.0, -10.0, W[0], W[1]), (10.0, 15.0, W[0], W[1])]
    back = [(-2.3, 2.3, F, F + 8.6), (-14.0, -9.0, W[0], W[1]), (9.0, 14.0, W[0], W[1])]
    side = [(-8.0, -3.0, W[0], W[1]), (5.0, 10.0, W[0], W[1])]
    for (axis, fixed, o, a0, a1, ops) in (("x", yF, -1, xL - T_OUT, xR + T_OUT, front), ("x", yB, 1, xL - T_OUT, xR + T_OUT, back),
                                         ("y", xL, -1, yF + T_IN, yB - T_IN, side), ("y", xR, 1, yF + T_IN, yB - T_IN, side)):
        H.wall(axis, fixed, o, a0, a1, F, TOP, ops, outer_kind="Siding")
        lap_boards(H, axis, fixed, o, a0, a1, F + 0.2, TOP - 0.3, ops, board=0.75)
        for (a, b, v0, v1) in ops[1:] if axis == "x" else ops:
            H.window(axis, fixed, o, a, b, v0, v1, shutters=True)
    H.door("x", yF, -1, -2.3, 2.3, F, F + 8.6)
    H.door("x", yB, 1, -2.3, 2.3, F, F + 8.6, kind="back")
    H.slab("Ceiling", xL, yF, xR, yB, TOP - 0.45, TOP, tag="ceiling")
    ridge = gable_roof(H, xL - T_OUT, yF - T_OUT, xR + T_OUT, yB + T_OUT, TOP, 0.75, 1.6, ridge="x", kind="MetalRoof", end_kind="Siding")
    for k in range(25):                                  # standing seams down both slopes
        x = xL - T_OUT - 1.6 + (xR - xL + 2 * T_OUT + 3.2) * k / 24
        yc = (yF + yB) / 2
        for ye in (yF - T_OUT - 1.6, yB + T_OUT + 1.6):
            ze = TOP - 1.6 * 0.75
            beam(H, "MetalRoof", (x, yc, ridge + 0.05), (x, ye, ze + 0.05), 0.12, 0.2)
    # full-width front porch on its own posts with a hipped tin roof, white railings, steps
    py0 = -22.0
    H.slab("Deck", xL - 1.0, py0, xR + 1.0, yF - T_OUT, F - 0.5, F - 0.2, tag="porch")
    for x in (-20.0, -10.0, 10.0, 20.0):
        H.p("Trim").box(x - 0.4, py0 + 0.6, F - 0.2, x + 0.4, py0 + 1.4, TOP - 1.0)
        H.col(x - 0.4, py0 + 0.6, F - 0.2, x + 0.4, py0 + 1.4, TOP - 1.0, "post")
    railing(H, xL - 0.6, py0 + 1.0, -2.6, py0 + 1.0, F - 0.2, height=3.0)
    railing(H, 2.6, py0 + 1.0, xR + 0.6, py0 + 1.0, F - 0.2, height=3.0)
    railing(H, xL - 0.6, py0 + 1.0, xL - 0.6, yF - T_OUT, F - 0.2, height=3.0)
    railing(H, xR + 0.6, py0 + 1.0, xR + 0.6, yF - T_OUT, F - 0.2, height=3.0)
    porch_top = F - 0.2
    rise = porch_top / 5                                 # 4 treads, 5 even risers from the walk up to the porch
    for k in range(4):
        H.slab("Deck", -2.6, py0 - 1.2 * (k + 1), 2.6, py0 - 1.2 * k, 0, porch_top - rise * (k + 1), tag="step")
    H.p("Trim").box(xL - 1.0, py0 + 0.4, TOP - 1.6, xR + 1.0, py0 + 1.6, TOP - 1.0)
    H.shed_roof(xL - 1.6, py0 - 0.8, xR + 1.6, yF - T_OUT, TOP + 0.6, TOP - 1.2, kind="MetalRoof")
    # back door: a landing on two piers and stairs down to the yard (it used to open onto thin air)
    ly0, ly1 = yB + T_OUT + 0.15, yB + T_OUT + 4.5
    H.slab("Deck", -3.6, ly0, 3.6, ly1, porch_top - 0.3, porch_top, tag="landing")
    for x in (-3.0, 3.0):
        H.p("Foundation").box(x - 0.5, ly1 - 1.0, 0, x + 0.5, ly1, porch_top - 0.3)
    for k in range(4):
        H.slab("Deck", -2.6, ly1 + 1.2 * k, 2.6, ly1 + 1.2 * (k + 1), 0, porch_top - rise * (k + 1), tag="step")
    railing(H, -3.4, ly0, -3.4, ly1, porch_top, height=3.0)
    railing(H, 3.4, ly0, 3.4, ly1, porch_top, height=3.0)
    ac_unit(H, xR + T_OUT + 3.0, 6.0)
    return H


meta = {}
for builder in (florida_ranch, mediterranean, key_west):
    H = builder()
    meta[H.style] = export_house(H)
with open(os.path.join(OUT, "florida.json"), "w") as f:
    json.dump(meta, f)
scene, cam = setup_render()
for st in meta:
    render_views(scene, cam, [st], {"front34": ((-60, -100, 42), (0, 2, 9)), "rear34": ((60, 120, 52), (-5, 20, 6))}, st)
print("NEONCOAST_DONE", json.dumps({k: {"max": v["maxTriangles"], "ext": v["extents_studs"], "colliders": len(v["colliders"]), "doors": len(v["doors"])} for k, v in meta.items()}))
