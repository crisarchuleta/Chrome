# Neon Coast: Palmgrove house kit (Ranch, TwoStory, Modern), built in Blender headless:
#   blender --background --factory-startup --python build_houses.py
# Units: 1 Blender unit = 1 Roblox stud. Ground at z = 0, the front faces -Y, the garage is on +X.
# Every house is enterable (two-layer walls round real openings, floors, ceilings, stairs); rooms are empty.
# Writes Ranch.glb, TwoStory.glb, Modern.glb, houses.json (colliders, doors, sizes) and previews/.
import sys, json, os, math
sys.path.insert(0, r"C:\Users\Crisa\Documents\NeonCoast_Blender")
import importlib, nc_kit
importlib.reload(nc_kit)
from nc_kit import *
import nc_extra, nc_detail
importlib.reload(nc_extra)
importlib.reload(nc_detail)
from nc_detail import *
import bpy

reset()

# ------------------------------------------------------------------ the styles
FLOOR = 1.2      # finished floor height above the lot
STORY = 12.0     # floor to ceiling
DOOR_W, DOOR_H = 4.6, 8.4
WIN_SILL, WIN_H = 3.4, 5.4
nc_kit.COLORS.update({"Patio": (0.78, 0.77, 0.74)})


def back_patio(H, sx0, sx1, y0, px0, px1, depth=9.5):
    """Back stoop at the doors (two even risers from the patio up to the floor) and a broom-finish concrete patio
    out to depth, level with the pool decks the street puts behind it (deck top 0.35)."""
    stoop_top = (0.35 + FLOOR) / 2
    H.slab("Foundation", sx0, y0, sx1, y0 + 3.0, 0, stoop_top, tag="stoop")
    H.slab("Patio", px0, y0, px1, y0 + depth, 0, 0.35, tag="patio", holes=[(sx0, y0, sx1, y0 + 3.0)])


def ranch():
    H = House("Ranch")
    # main body (centerline rectangle) and the garage wing on +X, set back from the street
    xL, xR, yF, yB = -35.0, 10.0, -17.0, 17.0
    gx0, gx1, gy0, gy1 = 10.0, 34.0, -12.5, 14.0
    top = FLOOR + STORY
    gtop = 0.4 + 11.0
    # foundation, porch slab and steps
    H.p("Foundation").box(xL - 1.3, yF - 1.3, 0, xR + 0.6, yB + 1.3, FLOOR - 0.35)
    H.col(xL - 1.3, yF - 1.3, 0, xR + 0.6, yB + 1.3, FLOOR - 0.35, "floor")
    H.slab("Floor", xL, yF, xR, yB, FLOOR - 0.35, FLOOR)
    H.slab("Foundation", gx0, gy0, gx1, gy1, 0, 0.4)
    H.slab("Foundation", -19.5, yF - 6.5, -3.5, yF - 1.3, 0, FLOOR - 0.35, tag="porch")
    H.slab("Foundation", -14.0, yF - 8.0, -9.0, yF - 6.5, 0, (FLOOR - 0.35) / 2, tag="step")
    # walls
    front_ops = [(-11.3 - DOOR_W / 2, -11.3 + DOOR_W / 2, FLOOR, FLOOR + DOOR_H)]
    wins_front = [(-31.0, -25.0), (-24.0, -18.0), (0.0, 6.5)]
    for (a, b) in wins_front:
        front_ops.append((a, b, FLOOR + WIN_SILL, FLOOR + WIN_SILL + WIN_H))
    H.wall("x", yF, -1, xL - T_OUT, xR, FLOOR, top, front_ops)
    back_ops = [(-28.0, -19.0, FLOOR, FLOOR + DOOR_H), (-12.0, -6.0, FLOOR + WIN_SILL, FLOOR + WIN_SILL + WIN_H), (1.0, 6.0, FLOOR + WIN_SILL + 1.2, FLOOR + WIN_SILL + WIN_H)]
    H.wall("x", yB, 1, xL - T_OUT, xR, FLOOR, top, back_ops)
    left_ops = [(-8.0, -2.0, FLOOR + WIN_SILL, FLOOR + WIN_SILL + WIN_H), (4.0, 10.0, FLOOR + WIN_SILL, FLOOR + WIN_SILL + WIN_H)]
    H.wall("y", xL, -1, yF + T_IN, yB - T_IN, FLOOR, top, left_ops)
    # the house-garage wall with an inside door
    H.wall("y", xR, 1, yF + T_IN, yB - T_IN, FLOOR, top, [(-2.0, -2.0 + 4.2, FLOOR, FLOOR + DOOR_H)])
    H.notes["innerDoor"] = {"x": xR, "y": [-2.0, 2.2]}
    # garage
    H.wall("x", gy1, 1, xR + T_IN, gx1 + T_OUT, 0.4, gtop, [(22.0, 26.0, 0.4 + WIN_SILL, 0.4 + WIN_SILL + 4.0)])
    H.wall("y", gx1, 1, gy0 + T_IN, gy1 - T_IN, 0.4, gtop, [(-4.0, 4.0, 0.4 + WIN_SILL, 0.4 + WIN_SILL + 4.0)])
    # (the garage door sits in the front garage wall)
    H.pieces.pop("noop", None)
    # rebuild the garage front with its opening
    H.colliders = [c for c in H.colliders]
    # windows, doors, garage door
    for (a, b) in wins_front:
        H.window("x", yF, -1, a, b, FLOOR + WIN_SILL, FLOOR + WIN_SILL + WIN_H, shutters=True)
    H.window("x", yB, 1, -12.0, -6.0, FLOOR + WIN_SILL, FLOOR + WIN_SILL + WIN_H)
    H.window("x", yB, 1, 1.0, 6.0, FLOOR + WIN_SILL + 1.2, FLOOR + WIN_SILL + WIN_H)
    H.window("x", gy1, 1, 22.0, 26.0, 0.4 + WIN_SILL, 0.4 + WIN_SILL + 4.0)
    H.window("y", xL, -1, -8.0, -2.0, FLOOR + WIN_SILL, FLOOR + WIN_SILL + WIN_H)
    H.window("y", xL, -1, 4.0, 10.0, FLOOR + WIN_SILL, FLOOR + WIN_SILL + WIN_H)
    H.window("y", gx1, 1, -4.0, 4.0, 0.4 + WIN_SILL, 0.4 + WIN_SILL + 4.0)
    H.door("x", yF, -1, -11.3 - DOOR_W / 2, -11.3 + DOOR_W / 2, FLOOR, FLOOR + DOOR_H)
    H.door("x", yB, 1, -28.0, -23.5, FLOOR, FLOOR + DOOR_H, kind="back")
    H.door("x", yB, 1, -23.5, -19.0, FLOOR, FLOOR + DOOR_H, hinge_at_u0=False, kind="back")
    back_patio(H, -29.5, -17.5, yB + 1.3, -33.0, -8.0)
    H.door("y", xR, 1, -2.0, 2.2, FLOOR, FLOOR + DOOR_H, glass=False, kind="inner")
    # ceilings
    H.slab("Ceiling", xL, yF, xR, yB, top - 0.45, top, tag="ceiling")
    H.slab("Ceiling", xR, gy0, gx1, gy1, gtop - 0.45, gtop, tag="ceiling")
    # roofs
    ridge = H.hip_roof(xL - T_OUT, yF - T_OUT, xR + T_OUT, yB + T_OUT, top, 0.36, 2.2)
    H.hip_roof(xR, gy0 - T_OUT, gx1 + T_OUT, gy1 + T_OUT, gtop, 0.36, 2.0)
    # porch: columns + shed roof
    for x in (-18.5, -4.5):
        H.column(x, yF - 5.6, FLOOR - 0.35, FLOOR + STORY - 1.6)
    H.shed_roof(-20.0, yF - 6.6, -3.0, yF - T_OUT, FLOOR + STORY - 0.4, FLOOR + STORY - 1.6)
    H.p("Trim").box(-20.0, yF - 6.6, FLOOR + STORY - 2.2, -3.0, yF - 6.1, FLOOR + STORY - 1.5)
    # porch light and house number plate
    H.p("Metal").box(-8.3, yF - T_OUT - 0.4, FLOOR + 6.5, -7.7, yF - T_OUT, FLOOR + 7.6)
    # chimney on the left side
    H.p("WallsOut").box(xL - T_OUT - 2.8, -3.0, 0, xL - T_OUT, 1.5, ridge + 2.5)
    H.col(xL - T_OUT - 2.8, -3.0, 0, xL - T_OUT, 1.5, ridge + 2.5, "chimney")
    H.p("Trim").box(xL - T_OUT - 3.1, -3.3, ridge + 2.5, xL - T_OUT + 0.3, 1.8, ridge + 3.1)
    H.p("Metal").box(xL - T_OUT - 2.0, -2.0, ridge + 3.1, xL - T_OUT - 0.8, 0.5, ridge + 3.9)
    # corner boards + water table trim band
    for (x, y) in ((xL - T_OUT, yF - T_OUT), (xR, yF - T_OUT), (xL - T_OUT, yB + T_OUT), (xR, yB + T_OUT)):
        H.p("Trim").box(x - 0.25, y - 0.25, FLOOR - 0.35, x + 0.5, y + 0.25, top)
    H.p("Trim").box(xL - T_OUT - 0.2, yF - T_OUT - 0.25, FLOOR - 0.45, xR, yF - T_OUT, FLOOR + 0.2)
    # realism details (references: Florida subdivision homes)
    hip_caps(H, xL - T_OUT, yF - T_OUT, xR + T_OUT, yB + T_OUT, top, 0.36, 2.2)
    hip_caps(H, xR, gy0 - T_OUT, gx1 + T_OUT, gy1 + T_OUT, gtop, 0.36, 2.0)
    gutters(H, xL - T_OUT, yF - T_OUT, xR + T_OUT, yB + T_OUT, top, 2.2, front_gaps=[(-20.3, -2.7)])   # porch roof
    gutters(H, xR, gy0 - T_OUT, gx1 + T_OUT, gy1 + T_OUT, gtop, 2.0)
    fz = FLOOR - 0.35
    wall_downspouts(H, [(xL - T_OUT, yF - T_OUT, -1, -1, top, 2.2, fz), (xL - T_OUT, yB + T_OUT, -1, 1, top, 2.2, fz),
                        (gx1 + T_OUT, gy0 - T_OUT, 1, -1, gtop, 2.0, 0.0), (gx1 + T_OUT, gy1 + T_OUT, 1, 1, gtop, 2.0, 0.0)])
    coach_lights(H, 13.0, 31.0, gy0 - T_OUT, 6.6)
    ac_unit(H, xL - T_OUT - 3.6, 9.0)
    meter(H, xL - T_OUT, -9.0, -1)
    house_number(H, -15.6, yF - T_OUT, FLOOR + 8.8)
    foundation_bed(H, xL - T_OUT, -19.5, yF - T_OUT)
    foundation_bed(H, -3.5, xR, yF - T_OUT)
    return H


def ranch_garage_front(H):
    # garage front wall with the big door opening (+X wing)
    gx0, gx1, gy0 = 10.0, 34.0, -12.5
    gtop = 0.4 + 11.0
    ops = [(13.0, 31.0, 0.4, 0.4 + 9.0)]
    H.wall("x", gy0, -1, gx0 + T_IN, gx1 + T_OUT, 0.4, gtop, ops)
    H.garage_door("x", gy0, -1, 13.0, 31.0, 0.4, 0.4 + 9.0)


def two_story():
    H = House("TwoStory")
    xL, xR, yF, yB = -32.0, 8.0, -18.0, 17.5
    gx1, gy0, gy1 = 32.0, -14.0, 14.5
    f2 = FLOOR + STORY + 1.0
    top = f2 + STORY
    gtop = 0.4 + 11.0
    H.p("Foundation").box(xL - 1.3, yF - 1.3, 0, xR + 0.6, yB + 1.3, FLOOR - 0.35)
    H.col(xL - 1.3, yF - 1.3, 0, xR + 0.6, yB + 1.3, FLOOR - 0.35, "floor")
    H.slab("Floor", xL, yF, xR, yB, FLOOR - 0.35, FLOOR)
    H.slab("Foundation", xR, gy0, gx1, gy1, 0, 0.4)
    H.slab("Foundation", -21.0, yF - 7.0, -5.0, yF - 1.3, 0, FLOOR - 0.35, tag="porch")
    H.slab("Foundation", -15.5, yF - 8.5, -10.5, yF - 7.0, 0, (FLOOR - 0.35) / 2, tag="step")
    # stairs along the left wall inside, going toward +Y; stairwell hole in the upper floor
    sx0, sx1 = xL + T_IN, xL + T_IN + 4.8
    run = 19.5
    sy = yB - T_IN - run - 1.0
    H.stairs(sx0 + 0.4, sx1, sy, run, FLOOR, f2, 13)
    H.slab("Floor", xL, yF, xR, yB, f2 - 1.0, f2, holes=[(sx0, sy, sx1 + 0.2, sy + run)])
    H.slab("Ceiling", xL, yF, xR, yB, f2 - 1.3, f2 - 1.0, tag=None, holes=[(sx0, sy, sx1 + 0.2, sy + run)])
    # stairwell guard rail on the landing edge, stopping 5 studs short of the top so you can step off the stairs
    # (it used to run the full length and boxed you in at the top: the upstairs was unreachable)
    H.p("Trim").box(sx1 + 0.2, sy, f2, sx1 + 0.45, sy + run - 5.0, f2 + 3.4)
    H.col(sx1 + 0.2, sy, f2, sx1 + 0.45, sy + run - 5.0, f2 + 3.4, "rail")
    H.p("Trim").box(sx1 + 0.2, sy + run - 5.25, f2, sx1 + 0.7, sy + run - 5.0, f2 + 3.6)      # newel post
    # walls, ground floor
    door_c = -13.0
    g_wins = [(-28.5, -22.5), (-3.5, 2.5)]
    ops = [(door_c - DOOR_W / 2, door_c + DOOR_W / 2, FLOOR, FLOOR + DOOR_H)] + [(a, b, FLOOR + WIN_SILL, FLOOR + WIN_SILL + WIN_H) for (a, b) in g_wins]
    u_wins = [(-28.5, -22.5), (-16.0, -10.0), (-3.5, 2.5)]
    ops += [(a, b, f2 + WIN_SILL, f2 + WIN_SILL + WIN_H) for (a, b) in u_wins]
    H.wall("x", yF, -1, xL - T_OUT, xR + T_OUT, FLOOR, top, ops)
    back = [(-26.0, -17.0, FLOOR, FLOOR + DOOR_H), (-8.0, -2.0, FLOOR + WIN_SILL, FLOOR + WIN_SILL + WIN_H),
            (-26.0, -20.0, f2 + WIN_SILL, f2 + WIN_SILL + WIN_H), (-12.0, -6.0, f2 + WIN_SILL, f2 + WIN_SILL + WIN_H), (0.0, 5.0, f2 + WIN_SILL, f2 + WIN_SILL + WIN_H)]
    H.wall("x", yB, 1, xL - T_OUT, xR + T_OUT, FLOOR, top, back)
    left = [(-10.0, -4.0, FLOOR + WIN_SILL, FLOOR + WIN_SILL + WIN_H), (-10.0, -4.0, f2 + WIN_SILL, f2 + WIN_SILL + WIN_H), (4.0, 9.0, f2 + WIN_SILL, f2 + WIN_SILL + WIN_H)]
    H.wall("y", xL, -1, yF + T_IN, yB - T_IN, FLOOR, top, left)
    right = [(-3.0, -3.0 + 4.2, FLOOR, FLOOR + DOOR_H), (-9.0, -3.0, f2 + WIN_SILL, f2 + WIN_SILL + WIN_H), (4.0, 10.0, f2 + WIN_SILL, f2 + WIN_SILL + WIN_H)]
    H.wall("y", xR, 1, yF + T_IN, yB - T_IN, FLOOR, top, right)
    # garage
    H.wall("x", gy0, -1, xR + T_OUT, gx1 + T_OUT, 0.4, gtop, [(11.0, 29.0, 0.4, 9.4)])
    H.garage_door("x", gy0, -1, 11.0, 29.0, 0.4, 9.4)
    H.wall("x", gy1, 1, xR + T_OUT, gx1 + T_OUT, 0.4, gtop, [(18.0, 22.0, 0.4 + WIN_SILL, 0.4 + WIN_SILL + 4.0)])
    H.wall("y", gx1, 1, gy0 + T_IN, gy1 - T_IN, 0.4, gtop, [(-3.0, 3.0, 0.4 + WIN_SILL, 0.4 + WIN_SILL + 4.0)])
    # openings dressed
    for (a, b) in g_wins:
        H.window("x", yF, -1, a, b, FLOOR + WIN_SILL, FLOOR + WIN_SILL + WIN_H, shutters=True, arch=True)
    for (a, b) in u_wins:
        H.window("x", yF, -1, a, b, f2 + WIN_SILL, f2 + WIN_SILL + WIN_H, shutters=True)
    H.window("x", yB, 1, -8.0, -2.0, FLOOR + WIN_SILL, FLOOR + WIN_SILL + WIN_H)
    for (a, b) in ((-26.0, -20.0), (-12.0, -6.0), (0.0, 5.0)):
        H.window("x", yB, 1, a, b, f2 + WIN_SILL, f2 + WIN_SILL + WIN_H)
    H.window("y", xL, -1, -10.0, -4.0, FLOOR + WIN_SILL, FLOOR + WIN_SILL + WIN_H)
    H.window("y", xL, -1, -10.0, -4.0, f2 + WIN_SILL, f2 + WIN_SILL + WIN_H)
    H.window("y", xL, -1, 4.0, 9.0, f2 + WIN_SILL, f2 + WIN_SILL + WIN_H)
    H.window("y", xR, 1, -9.0, -3.0, f2 + WIN_SILL, f2 + WIN_SILL + WIN_H)
    H.window("y", xR, 1, 4.0, 10.0, f2 + WIN_SILL, f2 + WIN_SILL + WIN_H)
    H.window("x", gy1, 1, 18.0, 22.0, 0.4 + WIN_SILL, 0.4 + WIN_SILL + 4.0)
    H.window("y", gx1, 1, -3.0, 3.0, 0.4 + WIN_SILL, 0.4 + WIN_SILL + 4.0)
    H.door("x", yF, -1, door_c - DOOR_W / 2, door_c + DOOR_W / 2, FLOOR, FLOOR + DOOR_H)
    H.door("x", yB, 1, -26.0, -21.5, FLOOR, FLOOR + DOOR_H, kind="back")
    H.door("x", yB, 1, -21.5, -17.0, FLOOR, FLOOR + DOOR_H, hinge_at_u0=False, kind="back")
    back_patio(H, -27.5, -15.5, yB + 1.3, -31.0, -6.0)
    H.door("y", xR, 1, -3.0, 1.2, FLOOR, FLOOR + DOOR_H, glass=False, kind="inner")
    # floor band between stories, corner boards
    H.p("Trim").box(xL - T_OUT - 0.25, yF - T_OUT - 0.3, f2 - 1.1, xR + T_OUT + 0.25, yF - T_OUT, f2 - 0.3)
    H.p("Trim").box(xL - T_OUT - 0.3, yF - T_OUT, f2 - 1.1, xL - T_OUT, yB + T_OUT, f2 - 0.3)
    H.p("Trim").box(xR + T_OUT, yF - T_OUT, f2 - 1.1, xR + T_OUT + 0.3, yB + T_OUT, f2 - 0.3)
    H.p("Trim").box(xL - T_OUT - 0.25, yB + T_OUT, f2 - 1.1, xR + T_OUT + 0.25, yB + T_OUT + 0.3, f2 - 0.3)
    for (x, y) in ((xL - T_OUT, yF - T_OUT), (xR + T_OUT, yF - T_OUT), (xL - T_OUT, yB + T_OUT), (xR + T_OUT, yB + T_OUT)):
        H.p("Trim").box(x - 0.3, y - 0.3, FLOOR - 0.35, x + 0.3, y + 0.3, top)
    # ceilings and roofs
    H.slab("Ceiling", xL, yF, xR, yB, top - 0.45, top, tag="ceiling")
    H.slab("Ceiling", xR, gy0, gx1, gy1, gtop - 0.45, gtop, tag="ceiling")
    ridge = H.hip_roof(xL - T_OUT, yF - T_OUT, xR + T_OUT, yB + T_OUT, top, 0.38, 2.3)
    H.hip_roof(xR + T_OUT, gy0 - T_OUT, gx1 + T_OUT, gy1 + T_OUT, gtop, 0.38, 2.0)
    # two-story entry portico: tall columns and a hipped porch roof
    for x in (-20.0, -6.0):
        H.column(x, yF - 6.0, FLOOR - 0.35, FLOOR + STORY - 1.2, r=0.7)
    H.p("Trim").box(-21.0, yF - 7.0, FLOOR + STORY - 1.9, -5.0, yF - T_OUT, FLOOR + STORY - 1.2)
    H.hip_roof(-21.0, yF - 7.0, -5.0, yF - T_OUT, FLOOR + STORY - 1.2, 0.45, 0.5)
    H.p("Metal").box(-10.1, yF - T_OUT - 0.4, FLOOR + 6.6, -9.5, yF - T_OUT, FLOOR + 7.7)
    # chimney
    H.p("WallsOut").box(xL - T_OUT - 3.0, 2.0, 0, xL - T_OUT, 6.5, ridge + 2.5)
    H.col(xL - T_OUT - 3.0, 2.0, 0, xL - T_OUT, 6.5, ridge + 2.5, "chimney")
    H.p("Trim").box(xL - T_OUT - 3.3, 1.7, ridge + 2.5, xL - T_OUT + 0.3, 6.8, ridge + 3.1)
    H.p("Metal").box(xL - T_OUT - 2.2, 3.0, ridge + 3.1, xL - T_OUT - 0.8, 5.5, ridge + 3.9)
    # realism details
    hip_caps(H, xL - T_OUT, yF - T_OUT, xR + T_OUT, yB + T_OUT, top, 0.38, 2.3)
    hip_caps(H, xR + T_OUT, gy0 - T_OUT, gx1 + T_OUT, gy1 + T_OUT, gtop, 0.38, 2.0)
    hip_caps(H, -21.0, yF - 7.0, -5.0, yF - T_OUT, FLOOR + STORY - 1.2, 0.45, 0.5)
    gutters(H, xL - T_OUT, yF - T_OUT, xR + T_OUT, yB + T_OUT, top, 2.3)
    gutters(H, xR + T_OUT, gy0 - T_OUT, gx1 + T_OUT, gy1 + T_OUT, gtop, 2.0)
    fz = FLOOR - 0.35
    wall_downspouts(H, [(xL - T_OUT, yF - T_OUT, -1, -1, top, 2.3, fz, 0.9, True), (xR + T_OUT, yB + T_OUT, 1, 1, top, 2.3, fz),
                        (gx1 + T_OUT, gy0 - T_OUT, 1, -1, gtop, 2.0, 0.0), (gx1 + T_OUT, gy1 + T_OUT, 1, 1, gtop, 2.0, 0.0)])
    coach_lights(H, 11.0, 29.0, gy0 - T_OUT, 6.6)
    ac_unit(H, gx1 + T_OUT + 3.6, 6.0)
    meter(H, gx1 + T_OUT, -6.0, 1)
    house_number(H, -18.4, yF - T_OUT, FLOOR + 8.9)
    foundation_bed(H, xL - T_OUT, -21.0, yF - T_OUT)
    foundation_bed(H, -5.0, xR + T_OUT, yF - T_OUT)
    return H


def modern():
    H = House("Modern")
    # main volume, a taller clerestory block over the living room, garage box on +X
    xL, xR, yF, yB = -29.0, 9.0, -16.0, 18.0
    gx1, gy0, gy1 = 29.0, -19.0, 12.0
    top = FLOOR + STORY
    gtop = 0.4 + 11.0
    H.p("Foundation").box(xL - 0.8, yF - 0.8, 0, xR + 0.8, yB + 0.8, FLOOR - 0.35)
    H.col(xL - 0.8, yF - 0.8, 0, xR + 0.8, yB + 0.8, FLOOR - 0.35, "floor")
    H.slab("Floor", xL, yF, xR, yB, FLOOR - 0.35, FLOOR)
    H.slab("Foundation", xR, gy0, gx1, gy1, 0, 0.4)
    H.slab("Foundation", -9.0, yF - 6.0, 2.0, yF - 0.8, 0, FLOOR - 0.35, tag="porch")
    # front: a floor-to-ceiling glass wall on the left, the door, a solid wood-clad block
    glass_wall = (-27.0, -12.0, FLOOR + 0.6, top - 1.2)
    door_c = -6.0
    ops = [glass_wall, (door_c - DOOR_W / 2, door_c + DOOR_W / 2, FLOOR, FLOOR + DOOR_H + 0.6)]
    H.wall("x", yF, -1, xL - T_OUT, xR + T_OUT, FLOOR, top, ops)
    back = [(-25.0, -10.0, FLOOR, FLOOR + DOOR_H + 0.6), (-4.0, 4.0, FLOOR + WIN_SILL, FLOOR + WIN_SILL + WIN_H)]
    H.wall("x", yB, 1, xL - T_OUT, xR + T_OUT, FLOOR, top, back)
    H.wall("y", xL, -1, yF + T_IN, yB - T_IN, FLOOR, top, [(-6.0, 6.0, FLOOR + WIN_SILL + 1.5, FLOOR + WIN_SILL + 4.5)])
    H.wall("y", xR, 1, yF + T_IN, yB - T_IN, FLOOR, top, [(2.0, 6.2, FLOOR, FLOOR + DOOR_H)])
    # glazing (big panes with slim black frames)
    a, b, v0, v1 = glass_wall
    H.uvd("Glass", "x", a, b, v0, v1, yF - 0.06, yF + 0.06)
    H.col(a, yF - 0.06, v0, b, yF + 0.06, v1, "glass")
    for k in range(4):
        x = a + (b - a) * k / 3
        H.uvd("Metal", "x", x - 0.18, x + 0.18, v0, v1, yF - T_OUT - 0.1, yF + 0.1)
    for z in (v0, v1):
        H.uvd("Metal", "x", a, b, z - 0.18, z + 0.18, yF - T_OUT - 0.1, yF + 0.1)
    # back glass wall: a pair of glass doors out to the patio on the left, fixed panes on the right
    a, b, v0, v1 = back[0]
    dm = -17.5
    H.uvd("Glass", "x", dm, b, v0, v1, yB - 0.06, yB + 0.06)
    H.col(dm, yB - 0.06, v0, b, yB + 0.06, v1, "glass")
    for k in range(3):
        x = dm + (b - dm) * k / 2
        H.uvd("Metal", "x", x - 0.18, x + 0.18, v0, v1, yB - 0.1, yB + T_OUT + 0.1)
    H.uvd("Metal", "x", a, b, v1 - 0.18, v1 + 0.18, yB - 0.1, yB + T_OUT + 0.1)
    H.door("x", yB, 1, a, (a + dm) / 2, FLOOR, v1 - 0.2, kind="back")
    H.door("x", yB, 1, (a + dm) / 2, dm - 0.2, FLOOR, v1 - 0.2, hinge_at_u0=False, kind="back")
    back_patio(H, a - 1.5, dm + 1.5, yB + 0.8, -27.0, -6.0)
    H.window("x", yB, 1, -4.0, 4.0, FLOOR + WIN_SILL, FLOOR + WIN_SILL + WIN_H, mullions=False)
    H.window("y", xL, -1, -6.0, 6.0, FLOOR + WIN_SILL + 1.5, FLOOR + WIN_SILL + 4.5, mullions=False)
    H.door("x", yF, -1, door_c - DOOR_W / 2, door_c + DOOR_W / 2, FLOOR, FLOOR + DOOR_H + 0.6, glass=False)
    H.door("y", xR, 1, 2.0, 6.2, FLOOR, FLOOR + DOOR_H, glass=False, kind="inner")
    # wood cladding on the right part of the front and a vertical slat screen
    H.p("Accent").box(-2.5, yF - T_OUT - 0.35, FLOOR, xR + T_OUT, yF - T_OUT, top)
    for k in range(9):
        x = -1.8 + k * 1.3
        H.p("Accent").box(x, yF - T_OUT - 0.75, FLOOR + 0.5, x + 0.5, yF - T_OUT - 0.35, top - 0.5)
    # flat roof with parapet + coping; clerestory block over the living room
    H.slab("Ceiling", xL, yF, xR, yB, top - 0.45, top, tag="ceiling")
    H.p("Roof").box(xL - T_OUT, yF - T_OUT, top, xR + T_OUT, yB + T_OUT, top + 0.6)
    H.col(xL - T_OUT, yF - T_OUT, top, xR + T_OUT, yB + T_OUT, top + 0.6, "roof")
    for (x0, y0, x1, y1) in ((xL - T_OUT, yF - T_OUT, xR + T_OUT, yF - T_OUT + 0.7), (xL - T_OUT, yB + T_OUT - 0.7, xR + T_OUT, yB + T_OUT),
                             (xL - T_OUT, yF - T_OUT, xL - T_OUT + 0.7, yB + T_OUT), (xR + T_OUT - 0.7, yF - T_OUT, xR + T_OUT, yB + T_OUT)):
        H.p("WallsOut").box(x0, y0, top + 0.6, x1, y1, top + 2.4)
        H.p("Trim").box(x0 - 0.1, y0 - 0.1, top + 2.4, x1 + 0.1, y1 + 0.1, top + 2.7)
        H.col(x0, y0, top + 0.6, x1, y1, top + 2.4, "parapet")
    cx0, cx1, cy0, cy1 = -24.0, -8.0, -10.0, 10.0
    ctop = top + 6.5
    H.wall("x", cy0, -1, cx0 - T_OUT, cx1 + T_OUT, top + 0.6, ctop, [(cx0 + 1.0, cx1 - 1.0, top + 1.6, ctop - 1.2)], collide=False)
    H.wall("x", cy1, 1, cx0 - T_OUT, cx1 + T_OUT, top + 0.6, ctop, [], collide=False)
    H.wall("y", cx0, -1, cy0 + T_IN, cy1 - T_IN, top + 0.6, ctop, [], collide=False)
    H.wall("y", cx1, 1, cy0 + T_IN, cy1 - T_IN, top + 0.6, ctop, [], collide=False)
    H.uvd("Glass", "x", cx0 + 1.0, cx1 - 1.0, top + 1.6, ctop - 1.2, cy0 - 0.06, cy0 + 0.06)
    H.p("Roof").box(cx0 - T_OUT - 1.5, cy0 - T_OUT - 1.5, ctop, cx1 + T_OUT + 1.5, cy1 + T_OUT + 1.0, ctop + 0.7)
    H.p("Trim").box(cx0 - T_OUT - 1.6, cy0 - T_OUT - 1.6, ctop + 0.7, cx1 + T_OUT + 1.6, cy1 + T_OUT + 1.1, ctop + 0.95)
    H.col(cx0 - T_OUT, cy0 - T_OUT, top + 0.6, cx1 + T_OUT, cy1 + T_OUT, ctop + 0.7, "clerestory")
    # garage box
    H.wall("x", gy0, -1, xR + T_OUT, gx1 + T_OUT, 0.4, gtop, [(12.0, 27.0, 0.4, 9.4)])
    H.garage_door("x", gy0, -1, 12.0, 27.0, 0.4, 9.4)
    H.wall("x", gy1, 1, xR + T_OUT, gx1 + T_OUT, 0.4, gtop, [])
    H.wall("y", gx1, 1, gy0 + T_IN, gy1 - T_IN, 0.4, gtop, [(-6.0, 0.0, 0.4 + 6.0, 0.4 + 8.5)])
    H.window("y", gx1, 1, -6.0, 0.0, 0.4 + 6.0, 0.4 + 8.5, mullions=False)
    H.slab("Ceiling", xR, gy0, gx1, gy1, gtop - 0.45, gtop, tag="ceiling")
    H.p("Roof").box(xR + T_OUT, gy0 - T_OUT, gtop, gx1 + T_OUT, gy1 + T_OUT, gtop + 0.6)
    H.col(xR + T_OUT, gy0 - T_OUT, gtop, gx1 + T_OUT, gy1 + T_OUT, gtop + 0.6, "roof")
    H.p("Trim").box(xR + T_OUT - 0.1, gy0 - T_OUT - 0.1, gtop + 0.6, gx1 + T_OUT + 0.1, gy1 + T_OUT + 0.1, gtop + 0.9)
    # cantilevered entry canopy + planter
    H.p("Roof").box(-11.0, yF - 7.0, FLOOR + DOOR_H + 1.6, 3.0, yF - T_OUT, FLOOR + DOOR_H + 2.3)
    H.p("Metal").box(-11.0, yF - 7.1, FLOOR + DOOR_H + 1.5, 3.0, yF - 6.9, FLOOR + DOOR_H + 2.35)
    H.col(-11.0, yF - 7.0, FLOOR + DOOR_H + 1.6, 3.0, yF - T_OUT, FLOOR + DOOR_H + 2.3, "canopy")
    H.p("Foundation").box(-27.5, yF - 4.5, 0, -12.5, yF - 1.5, 2.0)
    H.col(-27.5, yF - 4.5, 0, -12.5, yF - 1.5, 2.0, "planter")
    H.p("Accent").box(-27.2, yF - 4.2, 2.0, -12.8, yF - 1.8, 2.25)
    # realism details: modern up/down sconces, numbers on the cladding, scupper downspouts, AC, meter, bed
    sconce(H, 10.6, gy0 - T_OUT, 6.6)
    sconce(H, 28.4, gy0 - T_OUT, 6.6)
    sconce(H, -10.2, yF - T_OUT, FLOOR + 6.6)
    house_number(H, 4.0, yF - T_OUT - 0.76, FLOOR + 9.5, w=3.2)
    scupper_downspouts(H, [(xL - T_OUT, yF - T_OUT, -1, -1, top + 0.7, FLOOR - 0.35), (xL - T_OUT, yB + T_OUT, -1, 1, top + 0.7, FLOOR - 0.35),
                           (gx1 + T_OUT, gy1 + T_OUT, 1, 1, gtop + 0.1, 0.0)])
    ac_unit(H, xL - T_OUT - 3.6, 8.0)
    meter(H, xL - T_OUT, -10.5, -1)
    foundation_bed(H, -2.5, xR + T_OUT, yF - T_OUT - 0.76, depth=3.5, lip=0.0)
    return H


styles = []
h = ranch()
ranch_garage_front(h)
styles.append(h)
styles.append(two_story())
styles.append(modern())

meta = {}
for H in styles:
    for ob in list(bpy.context.scene.objects):
        ob.select_set(False)
    objs, tris = H.build()
    for ob in objs:
        ob.select_set(True)
    xs = [v.co.x for ob in objs for v in ob.data.vertices]
    ys = [v.co.y for ob in objs for v in ob.data.vertices]
    zs = [v.co.z for ob in objs for v in ob.data.vertices]
    path = os.path.join(OUT, H.style + ".glb")
    bpy.ops.export_scene.gltf(filepath=path, export_format="GLB", use_selection=True, export_apply=True, export_yup=True)
    meta[H.style] = {
        "glb": path,
        "pieces": sorted(tris.keys()),
        "triangles": tris,
        "extents_studs": {"x": [min(xs), max(xs)], "y": [min(ys), max(ys)], "z": [min(zs), max(zs)]},
        "colliders": H.colliders,
        "doors": H.doors,
        "windows": H.windows,
        "notes": H.notes,
        "frontFaces": "-Y (Blender)",
        "garageSide": "+X",
    }
    # hide this style before the next one is built (renders below re-show each style alone)
    for ob in objs:
        ob["style"] = H.style

with open(os.path.join(OUT, "houses.json"), "w") as f:
    json.dump(meta, f)

# ------------------------------------------------------------------ preview renders
scene = bpy.context.scene
scene.render.engine = "BLENDER_WORKBENCH"
scene.display.shading.light = "STUDIO"
scene.display.shading.color_type = "MATERIAL"
scene.display.shading.show_shadows = True
scene.display.shading.show_cavity = True
scene.render.resolution_x, scene.render.resolution_y = 1280, 800
world = bpy.data.worlds.new("W")
world.color = (0.55, 0.72, 0.9)
scene.world = world
cam_data = bpy.data.cameras.new("Cam")
cam_data.lens = 35
cam = bpy.data.objects.new("Cam", cam_data)
scene.collection.objects.link(cam)
scene.camera = cam
from mathutils import Vector


def look(loc, target):
    cam.location = loc
    d = Vector(target) - Vector(loc)
    cam.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()


views = {
    "front34": ((-60, -95, 38), (0, 0, 10)),
    "rear34": ((70, 90, 40), (0, 0, 10)),
    "inside": ((-6, -5, 7.5), (-30, 12, 6)),
}
for H in styles:
    for ob in scene.objects:
        if ob.type == "MESH":
            ob.hide_render = ob.get("style") != H.style
    for vname, (loc, tgt) in views.items():
        look(loc, tgt)
        scene.render.filepath = os.path.join(PREV, f"{H.style}_{vname}.png")
        bpy.ops.render.render(write_still=True)
print("NEONCOAST_DONE", json.dumps({k: {"tris": v["triangles"], "ext": v["extents_studs"]} for k, v in meta.items()}))
