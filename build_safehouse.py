# Neon Coast: the player's SAFE HOUSE (the most detailed house), built in Blender headless:
#   blender --background --factory-startup --python build_safehouse.py
# Matches the Studio SafeHouse: pivot (2186, 0, -2210). Blender coords = (-x, z, y) of the Roblox local
# frame, so the front faces -Y here, the garage wing is on -X (the left as you face the house), and after
# import the model turns 180 degrees about up to line up with the SafeHouse pivot.
# Kept from the Studio version on purpose: the stone lower story / sided upper story, the front window the
# intro camera flies through (Roblox local (17, 7.9, -20) -> Blender (-17, -20, 7.9)), the garage door
# centred at Roblox local x = 44, the keypad by the garage corner.
import sys, json, os
sys.path.insert(0, r"C:\Users\Crisa\Documents\NeonCoast_Blender")
import importlib, nc_kit, nc_extra
importlib.reload(nc_kit)
importlib.reload(nc_extra)
from nc_extra import *

reset()
H = House("SafeHouse")
F = 1.4           # first floor
S1 = 13.4         # top of the stone story
F2 = 14.4         # second floor
TOP = 25.4        # top of the walls
xL, xR, yF, yB = -27.45, 27.45, -19.45, 19.45            # wall centrelines; outer faces at x = +-28, y = +-20
gxL, gyF, gyB = -59.45, -17.45, 19.45                     # garage wing (shares the house's left wall)
GF, GTOP = 0.4, 14.4
DW, DH = 3.4, 8.8                                         # each front door leaf

# ---------------------------------------------------------------- slabs, floors, stairs
H.p("Foundation").box(xL - 1.0, yF - 1.0, 0, xR + 1.0, yB + 1.0, F - 0.4)
H.col(xL - 1.0, yF - 1.0, 0, xR + 1.0, yB + 1.0, F - 0.4, "floor")
H.slab("Floor", xL, yF, xR, yB, F - 0.4, F)
H.slab("Foundation", gxL - T_OUT, gyF - T_OUT, xL, gyB + T_OUT, 0, GF)
run = 19.5
sx0, sx1 = xR - T_IN - 5.4, xR - T_IN - 0.3
sy = yB - T_IN - 0.6 - run
H.stairs(sx0, sx1, sy, run, F, F2, 13)
hole = [(sx0 - 0.3, sy, sx1 + 0.3, sy + run)]
H.slab("Floor", xL, yF, xR, yB, F2 - 1.0, F2, holes=hole)
H.slab("Ceiling", xL, yF, xR, yB, F2 - 1.3, F2 - 1.0, tag=None, holes=hole)
# guard rail along the stairwell, open for the last 5 studs so you can step off at the top (it used to run the
# whole length and the upstairs couldn't be reached)
H.p("Trim").box(sx0 - 0.55, sy, F2, sx0 - 0.3, sy + run - 5.0, F2 + 3.4)
H.col(sx0 - 0.55, sy, F2, sx0 - 0.3, sy + run - 5.0, F2 + 3.4, "rail")
H.p("Trim").box(sx0 - 0.8, sy + run - 5.25, F2, sx0 - 0.3, sy + run - 5.0, F2 + 3.6)      # newel post
H.slab("Ceiling", xL, yF, xR, yB, TOP - 0.45, TOP, tag="ceiling")
H.slab("Ceiling", gxL, gyF, xL, gyB, GTOP - 0.45, GTOP, tag="ceiling")

# ---------------------------------------------------------------- openings
W1 = (F + 3.2, F + 10.0)          # ground-floor window band (contains the intro camera's height 7.9)
W2 = (F2 + 2.6, F2 + 8.6)
entry = (-5.7, 5.7, F, F + 10.5)  # double doors + sidelights + transom
front1 = [entry, (-21.0, -13.0, W1[0], W1[1]), (13.0, 21.0, W1[0], W1[1])]
front2 = [(-3.6, 3.6, F2, F2 + DH), (-21.0, -14.0, W2[0], W2[1]), (14.0, 21.0, W2[0], W2[1]), (-10.4, -7.6, W2[0] + 1.5, W2[1]), (7.6, 10.4, W2[0] + 1.5, W2[1])]
back1 = [(-4.6, 4.6, F, F + DH), (-21.0, -15.0, W1[0] + 1.0, W1[1]), (10.0, 16.0, W1[0] + 1.0, W1[1])]
back2 = [(-21.0, -15.0, W2[0], W2[1]), (-7.0, -1.0, W2[0], W2[1]), (8.0, 14.0, W2[0], W2[1])]
right1 = [(-12.0, -6.0, W1[0], W1[1]), (2.0, 8.0, W1[0], W1[1])]
right2 = [(-12.0, -6.0, W2[0], W2[1]), (8.0, 13.0, W2[0], W2[1])]
left1 = [(-6.0, -1.8, F, F + DH)]                      # into the garage
left2 = []                                             # the garage roof covers this wall up to ~22 studs: no windows

def story(axis, fixed, outward, a0, a1, ops1, ops2):
    H.wall(axis, fixed, outward, a0, a1, F, F2, ops1, outer_kind="Stone")
    H.wall(axis, fixed, outward, a0, a1, F2, TOP, ops2, outer_kind="Siding")
    lap_boards(H, axis, fixed, outward, a0, a1, F2 + 0.2, TOP - 0.3, ops2)

story("x", yF, -1, xL - T_OUT, xR + T_OUT, front1, front2)
story("x", yB, 1, xL - T_OUT, xR + T_OUT, back1, back2)
story("y", xR, 1, yF + T_IN, yB - T_IN, right1, right2)
story("y", xL, -1, yF + T_IN, yB - T_IN, left1, left2)

# ---------------------------------------------------------------- dressing the openings
def craftsman(axis, fixed, outward, u0, u1, v0, v1, shutters=True):
    H.window(axis, fixed, outward, u0, u1, v0, v1, shutters=shutters, mullions=False)
    split = v0 + (v1 - v0) * 0.66          # 3-over-1: bars only in the top sash (the intro camera passes below)
    m0, m1 = fixed + outward * 0.06, fixed + outward * 0.22
    H.uvd("Trim", axis, u0, u1, split - 0.14, split + 0.14, m0, m1)
    for k in (1, 2):
        u = u0 + (u1 - u0) * k / 3
        H.uvd("Trim", axis, u - 0.1, u + 0.1, split, v1, m0, m1)

for (a, b, v0, v1) in front1[1:]:
    craftsman("x", yF, -1, a, b, v0, v1)
for (a, b, v0, v1) in front2[1:]:
    craftsman("x", yF, -1, a, b, v0, v1, shutters=(b - a) > 4)
for (a, b, v0, v1) in back1[1:] + back2:
    craftsman("x", yB, 1, a, b, v0, v1, shutters=False)
for (a, b, v0, v1) in right1 + right2:
    craftsman("y", xR, 1, a, b, v0, v1, shutters=False)
for (a, b, v0, v1) in left2:
    craftsman("y", xL, -1, a, b, v0, v1, shutters=False)

# front entry: two leaves, sidelights, transom, a deep frame
H.door("x", yF, -1, -DW, 0.0, F, F + DH)
H.door("x", yF, -1, 0.0, DW, F, F + DH, hinge_at_u0=False)
for (a, b) in ((-5.7, -DW - 0.55), (DW + 0.55, 5.7)):
    H.uvd("Glass", "x", a, b, F + 0.8, F + DH, yF - 0.06, yF + 0.06)
    H.col(a, yF - 0.06, F, b, yF + 0.06, F + DH, "glass")
    H.uvd("Trim", "x", a, b, F, F + 0.8, yF - T_OUT - 0.2, yF + 0.2)
H.uvd("Glass", "x", -5.7, 5.7, F + DH + 0.55, F + 10.5, yF - 0.06, yF + 0.06)
H.col(-5.7, yF - 0.06, F + DH, 5.7, yF + 0.06, F + 10.5, "glass")
H.uvd("Trim", "x", -5.7, 5.7, F + DH, F + DH + 0.55, yF - T_OUT - 0.35, yF + 0.2)
H.uvd("Trim", "x", -6.6, 6.6, F + 10.5, F + 11.4, yF - T_OUT - 0.6, yF - T_OUT)       # head
H.uvd("Trim", "x", -6.6, -5.7, F, F + 10.5, yF - T_OUT - 0.6, yF - T_OUT)
H.uvd("Trim", "x", 5.7, 6.6, F, F + 10.5, yF - T_OUT - 0.6, yF - T_OUT)
lantern(H, -8.2, yF - T_OUT, F + 7.0)
lantern(H, 8.2, yF - T_OUT, F + 7.0)
H.p("Metal").box(-1.1, yF - T_OUT - 0.25, F + 11.6, 1.1, yF - T_OUT, F + 12.4)       # house number plate
H.notes["houseNumber"] = [0.0, yF - T_OUT - 0.25, F + 12.0]
# balcony french doors (upstairs) and the back french doors
H.door("x", yF, -1, -3.6, 0.0, F2, F2 + DH, kind="balcony")
H.door("x", yF, -1, 0.0, 3.6, F2, F2 + DH, hinge_at_u0=False, kind="balcony")
H.door("x", yB, 1, -4.6, 0.0, F, F + DH, kind="back")
H.door("x", yB, 1, 0.0, 4.6, F, F + DH, hinge_at_u0=False, kind="back")
H.door("y", xL, -1, -6.0, -1.8, F, F + DH, glass=False, kind="inner")

# floor band between the stories, corner boards, water table
H.p("Trim").box(xL - T_OUT - 0.35, yF - T_OUT - 0.4, S1 - 0.2, xR + T_OUT + 0.35, yB + T_OUT + 0.4, F2 + 0.2)
for (x, y) in ((xL - T_OUT, yF - T_OUT), (xR + T_OUT, yF - T_OUT), (xL - T_OUT, yB + T_OUT), (xR + T_OUT, yB + T_OUT)):
    H.p("Trim").box(x - 0.35, y - 0.35, F2, x + 0.35, y + 0.35, TOP)
    H.p("Stone").box(x - 0.6, y - 0.6, F - 0.4, x + 0.6, y + 0.6, S1 - 0.2)          # stone quoins
H.p("Stone").box(xL - T_OUT - 0.3, yF - T_OUT - 0.3, F - 0.4, xR + T_OUT + 0.3, yF - T_OUT, F + 0.5)  # water table

# ---------------------------------------------------------------- porch with the balcony on top
py0, py1 = -31.0, yF - T_OUT
px0, px1 = -19.5, 19.5
H.slab("Foundation", px0, py0, px1, py1, 0, F - 0.4, tag="porch")
H.p("Deck").box(px0 + 0.3, py0 + 0.3, F - 0.4, px1 - 0.3, py1, F - 0.25)
for (k, h) in ((0, 0.75), (1, 0.38)):
    yy = py0 - 1.6 * (k + 1)
    H.slab("Foundation", -5.5, yy, 5.5, yy + 1.6, 0, h * (F - 0.4) / 0.75 * 0.75 if k else (F - 0.4) * 0.66, tag="step")
for x in (-17.8, -6.4, 6.4, 17.8):
    craftsman_column(H, x, py0 + 1.6, F - 0.25, S1)
H.p("Trim").box(px0, py0 + 0.3, S1 - 1.4, px1, py0 + 2.6, S1)                       # beam
H.p("Deck").box(px0, py0, S1, px1, py1, F2)                                          # balcony floor / porch ceiling
H.col(px0, py0, S1, px1, py1, F2, "balcony")
railing(H, px0 + 0.4, py0 + 0.5, px1 - 0.4, py0 + 0.5, F2)
railing(H, px0 + 0.5, py0 + 0.5, px0 + 0.5, py1, F2)
railing(H, px1 - 0.5, py0 + 0.5, px1 - 0.5, py1, F2)
railing(H, px0 + 1.0, py0 + 1.6, -7.7, py0 + 1.6, F - 0.25, height=3.0)
railing(H, 7.7, py0 + 1.6, px1 - 1.0, py0 + 1.6, F - 0.25, height=3.0)

# ---------------------------------------------------------------- garage wing
gops_front = [(-53.0, -35.0, GF, GF + 10.0)]
gops_side = [(1.5, 5.7, GF, GF + DH), (10.0, 15.0, GF + 5.4, GF + 9.4)]
gops_back = [(-50.0, -44.0, GF + 5.4, GF + 9.4)]
def gwall(axis, fixed, outward, a0, a1, ops):
    H.wall(axis, fixed, outward, a0, a1, GF, GF + 5.0, ops, outer_kind="Stone")
    H.wall(axis, fixed, outward, a0, a1, GF + 5.0, GTOP, ops, outer_kind="Siding")
    lap_boards(H, axis, fixed, outward, a0, a1, GF + 5.3, GTOP - 0.3, ops)
gwall("x", gyF, -1, gxL - T_OUT, xL - T_IN, gops_front)
gwall("x", gyB, 1, gxL - T_OUT, xL - T_IN, gops_back)
gwall("y", gxL, -1, gyF + T_IN, gyB - T_IN, gops_side)
H.garage_door("x", gyF, -1, -53.0, -35.0, GF, GF + 10.0)
H.door("y", gxL, -1, 1.5, 5.7, GF, GF + DH, kind="garageSide")
H.window("y", gxL, -1, 10.0, 15.0, GF + 5.4, GF + 9.4)
H.window("x", gyB, 1, -50.0, -44.0, GF + 5.4, GF + 9.4)
H.p("Trim").box(gxL - T_OUT - 0.3, gyF - T_OUT - 0.3, GF + 4.8, xL - T_OUT, gyB + T_OUT + 0.3, GF + 5.4)
for x in (-55.2, -32.8):
    lantern(H, x, gyF - T_OUT, GF + 9.0)
# keypad by the garage corner (the Studio KeypadPoint sits in front of it)
H.p("Metal").box(-59.2, gyF - T_OUT - 0.3, GF + 4.6, -57.8, gyF - T_OUT, GF + 6.6)
H.p("Glass").box(-58.95, gyF - T_OUT - 0.36, GF + 5.5, -58.05, gyF - T_OUT - 0.3, GF + 6.3)
H.notes["keypad"] = [-58.5, gyF - T_OUT - 0.3, GF + 5.6]

# ---------------------------------------------------------------- roofs, dormers, chimney
ridge = gable_roof(H, xL - T_OUT, yF - T_OUT, xR + T_OUT, yB + T_OUT, TOP, 0.55, 2.0, ridge="x", kind="Roof", end_kind="Siding")
gable_roof(H, gxL - T_OUT, gyF - T_OUT, xL - T_OUT, gyB + T_OUT, GTOP, 0.42, 1.6, ridge="x", ends=(True, False))
for cx in (-12.0, 12.0):
    # dormer: front wall with a window sitting on the front slope, its own little gable roof
    dy0, dy1 = -14.0, -4.0
    z0 = TOP + (yF - T_OUT + 20.0 - (yF - T_OUT)) * 0.0
    zf = TOP + (dy0 - (yF - T_OUT)) * 0.55            # roof height where the dormer face sits
    H.p("Siding").box(cx - 3.8, dy0, zf - 1.0, cx + 3.8, dy1, zf + 5.2)
    H.window("x", dy0 + 0.5, -1, cx - 1.8, cx + 1.8, zf + 0.6, zf + 4.2, mullions=True)
    gable_roof(H, cx - 3.8, dy0, cx + 3.8, dy1, zf + 5.2, 0.7, 0.8, ridge="y", ends=(True, False), gutters=False)
H.p("Stone").box(xR + T_OUT, 2.0, 0, xR + T_OUT + 3.4, 7.0, ridge + 2.2)
H.col(xR + T_OUT, 2.0, 0, xR + T_OUT + 3.4, 7.0, ridge + 2.2, "chimney")
H.p("Trim").box(xR + T_OUT - 0.3, 1.7, ridge + 2.2, xR + T_OUT + 3.7, 7.3, ridge + 2.8)
H.p("Metal").box(xR + T_OUT + 1.0, 3.3, ridge + 2.8, xR + T_OUT + 2.4, 5.7, ridge + 3.8)
# downspouts: from the gable gutters (gutter bottom = eave - 0.95, given as zb = eave + 0.4) down the walls, out past
# the belly band; the garage ones too (the front-left one goes on the side wall, clear of the keypad)
import nc_detail
importlib.reload(nc_detail)
ze, gze = TOP - 2.0 * 0.55, GTOP - 1.6 * 0.42
nc_detail.wall_downspouts(H, [(xL - T_OUT, yF - T_OUT, -1, -1, ze + 0.4, 2.0, F - 0.4), (xR + T_OUT, yF - T_OUT, 1, -1, ze + 0.4, 2.0, F - 0.4),
                              (xR + T_OUT, yB + T_OUT, 1, 1, ze + 0.4, 2.0, F - 0.4)], standoff=0.42)
nc_detail.wall_downspouts(H, [(gxL - T_OUT, gyF - T_OUT, -1, -1, gze + 0.4, 1.6, 0.0, 0.9, True), (gxL - T_OUT, gyB + T_OUT, -1, 1, gze + 0.4, 1.6, 0.0)],
                          standoff=0.32)
H.notes["introWindow"] = {"blender": [-17.0, yF - T_OUT, 7.9], "studioLocal": [17.0, 7.9, -20.0], "opening": [-21.0, -13.0, W1[0], W1[1]]}
H.notes["garageDoorCentre"] = [-44.0, gyF - T_OUT, GF + 5.0]

meta = {"SafeHouse": export_house(H)}
with open(os.path.join(OUT, "safehouse.json"), "w") as f:
    json.dump(meta, f)
scene, cam = setup_render()
render_views(scene, cam, ["SafeHouse"], {
    "front34": ((40, -120, 45), (-14, 0, 14)),
    "front": ((-14, -150, 18), (-14, 0, 16)),
    "rear34": ((-80, 110, 50), (-14, 0, 14)),
    "porch": ((-28, -55, 12), (0, -22, 10)),
    "inside": ((-10, 8, 8), (20, -10, 8)),
}, "SafeHouse")
m = meta["SafeHouse"]
print("NEONCOAST_DONE", json.dumps({"tris": m["triangles"], "max": m["maxTriangles"], "ext": m["extents_studs"], "colliders": len(m["colliders"])}))
