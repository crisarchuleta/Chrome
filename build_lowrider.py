# Neon Coast lowrider + "Low & Slow Kustoms" shop, Blender headless:
#   blender --background --factory-startup --python build_lowrider.py
# The car: an original long, low two-door hardtop in the classic lowrider style (no real make or model). Swept body
# lofted from cross sections, tubbed wheel wells, wraparound chrome bumpers, quad headlights, triple round
# taillights, a pillarless greenhouse with wide sail panels, white tuck-and-roll interior with a chain steering
# wheel, an opening trunk lid over a chrome pump-and-battery setup and a continental kit.
# Paint: the body's paintable skin is split into UV-mapped panels (both sides, hood, trunk lid, roof) whose UVs
# match the vinyl images from make_lowrider_vinyls.py exactly, so artwork prints flush in the paint like real
# vinyl / airbrush (transparent pixels show the candy colour). LowriderVinyls.glb carries every vinyl image on a
# copy of its panel: importing it into Studio uploads the images, and NCLowriderKit.Prepare records their ids.
# The wheel: "Classic Wire 100-Spoke" (generic name, no brand): 100 cross-laced spokes in three rows, chrome
# dish and lip, two-bar knock-off spinner, low-profile tyre with a thin whitewall. Built once; the game clones it.
# The shop: a two-bay custom garage with a neon sign, a paint turntable in bay 1 and a hop pit with a height
# board in bay 2 (markers in the data).
# Units: 1 Blender unit = 1 stud. The car's front faces -Y, its origin is on the ground at the centre between the
# axles; wheels sit at ride height. Car-local Roblox frame used by the game: forward = -Z, (X, Y, Z) = (-x, z, y).
# Run make_lowrider_vinyls.py first (it writes lowrider_vinyls/*.png).
# Out: Lowrider.glb (car pieces Lowrider_*, wheel pieces LowriderWheel_* at x = 30), LowriderVinyls.glb,
#      LowSlowShop.glb, lowrider.json, NCLowriderData.lua (game data), previews/Lowrider_*.png
import sys, json, os, math
HERE = os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else r"C:\Users\Crisa\Documents\NeonCoast_Blender"
sys.path.insert(0, HERE)
sys.path.insert(0, r"C:\Users\Crisa\Documents\NeonCoast_Blender")
import importlib, nc_kit, nc_extra
importlib.reload(nc_kit)
importlib.reload(nc_extra)
from nc_kit import House, lin, COLORS
from nc_extra import setup_render, render_views
import bpy, bmesh
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree

OUT = os.environ.get("NC_OUT", nc_kit.OUT)
PREV = os.path.join(OUT, "previews")
os.makedirs(PREV, exist_ok=True)
nc_extra.PREV = PREV
nc_kit.reset()

COLORS.update({
    # car (the game recolours Body / art / spokes from the player's look; these are the defaults)
    "Body": (0.55, 0.03, 0.08), "Chrome": (0.86, 0.87, 0.90), "Glass": (0.30, 0.38, 0.44), "Interior": (0.95, 0.93, 0.88),
    "Tuck": (0.88, 0.85, 0.80), "Dash": (0.12, 0.12, 0.13), "Carpet": (0.45, 0.04, 0.08), "Headlight": (1.0, 0.97, 0.86),
    "Taillight": (0.85, 0.05, 0.05), "Grille": (0.08, 0.08, 0.09), "Seam": (0.05, 0.05, 0.05), "Under": (0.06, 0.06, 0.07),
    "Pinstripe": (0.97, 0.80, 0.25), "Flames": (1.0, 0.55, 0.05), "FlamesEdge": (1.0, 0.85, 0.15), "Patterns": (0.97, 0.80, 0.25),
    "Patterns2": (0.10, 0.80, 0.85), "MuralSky": (1.0, 0.45, 0.30), "MuralSun": (1.0, 0.85, 0.25), "MuralSea": (0.10, 0.65, 0.75),
    "MuralPalm": (0.07, 0.05, 0.10), "Lid": (0.55, 0.03, 0.08), "Pump": (0.86, 0.87, 0.90), "Battery": (0.10, 0.10, 0.11),
    "BatteryCap": (0.85, 0.10, 0.10), "TrunkFloor": (0.80, 0.82, 0.86), "ContBody": (0.55, 0.03, 0.08), "ContChrome": (0.86, 0.87, 0.90),
    "SteeringWheel": (0.86, 0.87, 0.90),
    # wheel
    "Tire": (0.07, 0.07, 0.08), "Whitewall": (0.96, 0.96, 0.94), "Rim": (0.86, 0.87, 0.90), "Spokes": (0.86, 0.87, 0.90),
    "Hub": (0.86, 0.87, 0.90),
    # shop
    "ShopFloor": (0.42, 0.42, 0.44), "Neon": (1.0, 0.25, 0.65), "Neon2": (0.15, 0.95, 0.95), "SignBack": (0.06, 0.06, 0.08),
    "Turntable": (0.75, 0.75, 0.78), "HopPit": (0.95, 0.80, 0.10), "HopBoard": (0.96, 0.96, 0.94), "HopTick": (0.08, 0.08, 0.09),
    "Bench": (0.55, 0.10, 0.12), "Tools": (0.70, 0.71, 0.74), "Mural": (0.98, 0.55, 0.30),
})

# ------------------------------------------------------------------ shared mesh helpers (object kit, join + export, data)
exec(compile(open(os.path.join(HERE, "nc_car_kit.py")).read(), "nc_car_kit.py", "exec"), globals())


# ------------------------------------------------------------------ car dimensions
W = 3.82                     # body half width
WR = 1.17                    # wheel radius (24.4 in at 1.15 studs per foot)
WX = 3.18                    # wheel centre |x|
WY_F, WY_R = -6.2, 5.6       # axle positions (wheelbase 11.8)
ARCH = 1.42
ZB, BELT, TOP = 0.75, 2.62, 2.80
# roof height: raised 0.55 (QA 2026-11-24) so a seated 6.6-stud player clears the headliner; the car is 4.55 ft
# tall (a stock 60s hardtop is ~4.6 ft). SEAT_DROP lowers the seats to sit on the floor like the real bench.
ROOF_Z, ROOF_RAISE, SEAT_DROP = 5.17, 0.55, 0.2


def liner(x0, x1, wy):
    """wheel well back wall: an arch-sized disc cut flat at the rocker so none of it shows under the car"""
    bm = bmesh.new()
    pts = [(wy + ARCH * math.cos(2 * math.pi * i / 32), max(WR + ARCH * math.sin(2 * math.pi * i / 32), ZB - 0.02)) for i in range(32)]
    v0 = [bm.verts.new((x0, y, z)) for y, z in pts]
    v1 = [bm.verts.new((x1, y, z)) for y, z in pts]
    bm.faces.new(v0)
    bm.faces.new(list(reversed(v1)))
    for k in range(32):
        bm.faces.new((v0[k], v0[(k + 1) % 32], v1[(k + 1) % 32], v1[k]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return new_obj(bm, "Under")


def ztop(x, top, crown, w):
    t = min(1.0, abs(x) / (0.93 * w))
    return top + crown * (1 - t * t)


def section(w, zb, belt, top, crown):
    half = [(0.0, zb), (w * 0.86, zb), (w * 0.965, zb + 0.18), (w, zb + 0.55), (w, belt - 0.32), (w * 0.99, belt - 0.1),
            (w * 0.965, belt + 0.03)]
    for k in range(5):                                    # the crowned deck from the edge to the centre line
        x = w * 0.93 * (1 - k / 5)
        half.append((x, ztop(x, top, crown, w) - (0.04 if k == 0 else 0.0)))
    half.append((0.0, top + crown))
    ring_ = half + [(-x, z) for (x, z) in reversed(half[1:-1])]
    return ring_


STATIONS = [  # y, half width, rocker, belt, deck, crown
    (-10.35, 3.50, 1.00, 2.20, 2.30, 0.00),
    (-10.15, 3.68, 0.84, 2.38, 2.52, 0.03),
    (-9.6, 3.79, 0.76, 2.52, 2.66, 0.06),
    (-8.0, W, ZB, 2.58, 2.74, 0.08),
    (-4.0, W, ZB, BELT, 2.78, 0.09),
    (-2.6, W, ZB, BELT, TOP, 0.09),
    (4.6, W, ZB, BELT, TOP, 0.08),
    (6.0, W, ZB, 2.64, 2.82, 0.06),
    (9.4, 3.80, 0.76, 2.64, 2.82, 0.04),
    (10.1, 3.70, 0.84, 2.58, 2.74, 0.02),
    (10.45, 3.52, 0.98, 2.42, 2.52, 0.00),
]


def deck_z(x, y):
    """height of the hood / trunk deck at (x, y), interpolated between stations"""
    for a, b in zip(STATIONS, STATIONS[1:]):
        if a[0] <= y <= b[0]:
            t = (y - a[0]) / (b[0] - a[0])
            v = [a[i] + (b[i] - a[i]) * t for i in range(6)]
            return ztop(x, v[4], v[5], v[1])
    return TOP


def dense_stations(step=0.6):
    out = []
    for a, b in zip(STATIONS, STATIONS[1:]):
        n = max(1, int(math.ceil((b[0] - a[0]) / step)))
        for k in range(n):
            t = k / n
            out.append(tuple(a[i] + (b[i] - a[i]) * t for i in range(6)))
    out.append(STATIONS[-1])
    return out


def loft_body():
    bm = bmesh.new()
    rings = []
    for (y, w, zb, belt, top, crown) in dense_stations():
        rings.append([bm.verts.new((x, y, z)) for (x, z) in section(w, zb, belt, top, crown)])
    n = len(rings[0])
    for A, B in zip(rings, rings[1:]):
        for i in range(n):
            j = (i + 1) % n
            bm.faces.new((A[i], A[j], B[j], B[i]))
    bm.faces.new(list(reversed(rings[0])))
    bm.faces.new(rings[-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    # a little more resolution along the length so art projection and the arch cuts stay clean
    return new_obj(bm, "Body", smooth=35.0)


def build_car():
    body = loft_body()
    body["loft"] = True
    door_src = body.data.copy()                           # the uncut skin: the doors are cut from it
    # wheel tubs: short cylinders from each side (not through the car, so the wells are closed boxes)
    cutters = bpy.data.collections.new("Cutters")
    bpy.context.scene.collection.children.link(cutters)

    def cutter_cyl(p0, p1, r):
        p0, p1 = Vector(p0), Vector(p1)
        bm = bmesh.new()
        m = Matrix.Translation((p0 + p1) / 2) @ axis_rot(p1 - p0).to_4x4()
        bmesh.ops.create_cone(bm, cap_ends=True, segments=40, radius1=r, radius2=r, depth=(p1 - p0).length, matrix=m)
        me = bpy.data.meshes.new("cut")
        bm.to_mesh(me)
        bm.free()
        ob = bpy.data.objects.new("cut", me)
        cutters.objects.link(ob)
        return ob

    def cutter_box(x0, y0, z0, x1, y1, z1):
        bm = bmesh.new()
        m = Matrix.Translation(((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2)) @ Matrix.Diagonal((x1 - x0, y1 - y0, z1 - z0, 1))
        bmesh.ops.create_cube(bm, size=1.0, matrix=m)
        me = bpy.data.meshes.new("cutb")
        bm.to_mesh(me)
        bm.free()
        ob = bpy.data.objects.new("cutb", me)
        cutters.objects.link(ob)
        return ob

    for wy in (WY_F, WY_R):
        for s in (-1, 1):
            cutter_cyl((s * (WX - 0.75), wy, WR), (s * (W + 0.8), wy, WR), ARCH)
    cutter_box(-3.2, 6.0, 1.25, 3.2, 9.85, 3.5)           # trunk opening (the lid is its own piece)
    cutter_box(-3.3, -2.58, 1.02, 3.3, 5.3, 3.6)          # open cabin (seats, dash, carpet show through the glass)
    for s in (-1, 1):                                     # door openings (the doors are their own hinged pieces)
        xa, xb = sorted((s * 3.25, s * (W + 0.6)))
        cutter_box(xa, DOOR_Y0 - 0.03, DOOR_Z0 - 0.03, xb, DOOR_Y1 + 0.03, 3.6)
    cutters.hide_render = True
    m = body.modifiers.new("arch", "BOOLEAN")
    m.operation, m.operand_type, m.collection, m.solver = "DIFFERENCE", "COLLECTION", cutters, "EXACT"
    bake(body)
    for ob in list(cutters.objects):
        bpy.data.objects.remove(ob)
    bpy.data.collections.remove(cutters)
    # trunk tub lining (narrowed between the rear wheel houses, which are hollow humps over the tyres)
    HX = WX - 0.34 - 0.25                                 # wheel house inner wall (just inboard of the tyre)
    HTOP = WR + ARCH + 0.06
    ya, yb = WY_R - ARCH - 0.05, WY_R + ARCH + 0.05       # the rear arch's y range

    def floor_split(kind, xh, y0, y1, z0, z1):
        for (a, b, x) in ((y0, min(y1, ya), xh), (max(y0, ya), min(y1, yb), min(xh, HX)), (max(y0, yb), y1, xh)):
            if b > a:
                box(kind, -x, a, z0, x, b, z1)

    def houses(kind, xh, y0, y1, z0):
        a, b = max(y0, ya), min(y1, yb)
        if b <= a:
            return
        for s in (-1, 1):
            box(kind, s * (HX - 0.06), a, z0 - 0.02, s * HX, b, HTOP)          # inner wall
            box(kind, s * (HX - 0.06), a, HTOP - 0.06, s * xh, b, HTOP)        # top
            for ye in (a, b):
                if y0 + 0.01 < ye < y1 - 0.01:
                    box(kind, s * (HX - 0.06), ye - 0.03, z0 - 0.02, s * xh, ye + 0.03, HTOP)

    floor_split("TrunkFloor", 3.15, 6.05, 9.8, 1.25, 1.32)
    houses("Under", 3.15, 6.05, 9.8, 1.25)
    for s in (-1, 1):
        box("Under", s * 3.15, yb, 1.25, s * 3.22, 9.8, 2.6)                    # side walls behind the arch
    box("Under", -HX, 6.0, 1.25, HX, 6.07, 2.6)                                 # front wall, between the houses
    box("Under", -3.2, 9.78, 1.25, 3.2, 9.85, 2.6)
    # wheel-well liners (dark) so the tub reads as a well, not body colour
    for wy in (WY_F, WY_R):
        for s in (-1, 1):
            liner(s * (WX - 0.74), s * (WX - 0.70), wy)

    # ---- greenhouse
    zb = 2.84
    xs_b, xs_t = 3.42, 2.92                              # glass line at the belt / roof (tumblehome)

    def gx(z):
        return xs_b + (xs_t - xs_b) * (z - zb) / (ROOF - 0.06 - zb)
    yA0, yA1 = -2.75, -0.85                               # windshield base / top
    yC0, yC1 = 3.3, 5.35                                  # rear glass top / base
    ROOF = ROOF_Z
    cube("PanelRoof", Vector((0, (yA1 + yC0) / 2, ROOF + 0.07)), (2 * xs_t + 0.16, yC0 - yA1 + 0.2, 0.16), 0.07)
    # windshield + rear glass
    prism("Glass", [(-3.2, yA0, zb), (3.2, yA0, zb), (xs_t - 0.08, yA1, ROOF), (-(xs_t - 0.08), yA1, ROOF)],
          [(-3.2, yA0 + 0.06, zb - 0.04), (3.2, yA0 + 0.06, zb - 0.04), (xs_t - 0.08, yA1 + 0.06, ROOF - 0.04), (-(xs_t - 0.08), yA1 + 0.06, ROOF - 0.04)])
    prism("RoofGlass", [(-(xs_t - 0.08), yC0, ROOF), (xs_t - 0.08, yC0, ROOF), (3.25, yC1, zb), (-3.25, yC1, zb)],
          [(-(xs_t - 0.08), yC0 - 0.06, ROOF - 0.04), (xs_t - 0.08, yC0 - 0.06, ROOF - 0.04), (3.25, yC1 - 0.06, zb - 0.04), (-3.25, yC1 - 0.06, zb - 0.04)])
    for s in (-1, 1):
        # A pillars (chrome) and the windshield / rear-glass reveal mouldings
        beam("Chrome", (s * 3.24, yA0, zb), (s * xs_t, yA1, ROOF), 0.16, 0.16)
        beam("RoofChrome", (s * xs_t, yC0, ROOF), (s * 3.28, yC1, zb), 0.12, 0.12)
        # side glass, frameless hardtop window
        ys = [(yA0 + 0.3, zb), (yA1 + 0.05, ROOF - 0.08), (2.1, ROOF - 0.08), (2.3, zb)]
        outer = [(s * gx(z), y, z) for (y, z) in ys]
        inner = [(s * (gx(z) - 0.05), y, z) for (y, z) in ys]
        prism("RoofGlass", outer, inner)
        # sail panel (wide C pillar) in body colour
        ys = [(2.1, ROOF - 0.02), (yC0 + 0.05, ROOF - 0.02), (yC1, zb - 0.02), (2.3, zb - 0.02)]
        outer = [(s * (gx(z) + 0.03), y, z) for (y, z) in ys]
        inner = [(s * min(gx(z) - 0.12, 3.25 - (y - 2.3) * 0.0), y, z) for (y, z) in ys]
        prism("RoofBody", outer, inner)
        # chrome drip rail along the roof edge and the belt moulding under the glass
        beam("RoofChrome", (s * (xs_t + 0.05), yA1, ROOF + 0.02), (s * (xs_t + 0.05), yC0, ROOF + 0.02), 0.07, 0.07)
        beam("Chrome", (s * (gx(zb) + 0.05), yA0 + 0.2, zb + 0.02), (s * (gx(zb) + 0.05), yC1 - 0.3, zb + 0.02), 0.08, 0.06)

    # ---- lights and side trim (bumpers, grille, mirrors etc. are swappable parts: build_lowrider_parts.py)
    for s in (-1, 1):
        box("Chrome", s * 0.9, 10.44, 1.62, s * 3.4, 10.5, 1.66)            # rear cove trim
        # door seams + handle (lights, side trim, door panels are swappable parts)
        for y in (DOOR_Y0 - 0.015, DOOR_Y1 + 0.015):      # dark shut lines in the door gaps
            box("Seam", s * (W - 0.25), y - 0.012, DOOR_Z0 - 0.03, s * (W - 0.01), y + 0.012, 2.8)
        box("Chrome", s * (W + 0.03) - 0.04, 1.6, 2.38, s * (W + 0.03) + 0.04, 2.15, 2.46, bev=0.02)
    # ---- interior shell: carpet, door cards, steering column (seats, dash, wheel, shifter are parts)
    floor_split("Carpet", 3.2, -2.6, 5.6, 0.95, 1.05)
    houses("Carpet", 3.2, -2.6, 5.3, 0.97)
    cyl("Dash", (1.55, -2.3, 2.45), (1.55, -1.75, 2.85), 0.06, seg=10)               # column
    # ---- trunk lid (hinged at its front edge); the trunk setups are parts
    lid = bmesh.new()
    nx, ny = 12, 10
    top, bot = [], []
    for j in range(ny + 1):
        y = 6.03 + (9.82 - 6.03) * j / ny
        rt, rb = [], []
        for i in range(nx + 1):
            x = -3.18 + 6.36 * i / nx
            z = deck_z(x, y)
            rt.append(lid.verts.new((x, y, z + 0.005)))
            rb.append(lid.verts.new((x, y, z - 0.09)))
        top.append(rt)
        bot.append(rb)
    for j in range(ny):
        for i in range(nx):
            lid.faces.new((top[j][i], top[j][i + 1], top[j + 1][i + 1], top[j + 1][i]))
            lid.faces.new((bot[j][i], bot[j + 1][i], bot[j + 1][i + 1], bot[j][i + 1]))
    for i in range(nx):
        lid.faces.new((top[0][i], bot[0][i], bot[0][i + 1], top[0][i + 1]))
        lid.faces.new((top[ny][i], top[ny][i + 1], bot[ny][i + 1], bot[ny][i]))
    for j in range(ny):
        lid.faces.new((top[j][0], top[j + 1][0], bot[j + 1][0], bot[j][0]))
        lid.faces.new((top[j][nx], bot[j][nx], bot[j + 1][nx], top[j + 1][nx]))
    bmesh.ops.recalc_face_normals(lid, faces=lid.faces[:])
    new_obj(lid, "Lid", smooth=30.0)
    build_doors(door_src)
    bpy.data.meshes.remove(door_src)
    build_engine_bay()
    build_fuel_door()


# ------------------------------------------------------------------ hinged panels: doors, hood, trunk lid, gas door
# Every opening panel is its own piece on a hinge so the game can swing it (Car.Hinges in the data). Pivots and axes
# are in this Blender frame here and in the car frame in the data; Open is the angle (degrees) it swings to.
DOOR_Y0, DOOR_Y1, DOOR_Z0 = -2.59, 2.32, 1.25             # door front / rear edge, bottom edge
FUEL = (7.4, 8.0, 1.45, 1.95)                            # gas door y0, y1, z0, z1 (car's left rear quarter)
HINGES = {
    "DoorL": {"pivot": (W - 0.02, DOOR_Y0, 2.0), "axis": (0, 0, 1), "open": -64, "kind": "door"},
    "DoorR": {"pivot": (-(W - 0.02), DOOR_Y0, 2.0), "axis": (0, 0, 1), "open": 64, "kind": "door"},
    "Hood": {"pivot": (0.0, -2.62, deck_z(0, -2.62)), "axis": (1, 0, 0), "open": -52, "kind": "hood"},
    "Lid": {"pivot": (0.0, 6.03, deck_z(0, 6.03)), "axis": (1, 0, 0), "open": 62, "kind": "trunk"},
    "Fuel": {"pivot": (3.845, FUEL[0], 1.7), "axis": (0, 0, 1), "open": -80, "kind": "fuel"},
}
HINGE_OF = {"Lid": "Lid", "PanelHood": "Hood", "HoodInner": "Hood", "PanelFuel": "Fuel"}
HINGE_SLOTS = {"Hood": "Hood", "Ornament": "Hood", "Spoiler": "Lid"}    # swappable parts that ride a panel


def build_doors(src):
    for s in (1, -1):
        side = "L" if s > 0 else "R"
        bm = bmesh.new()
        bm.from_mesh(src)
        for co, no in (((0, DOOR_Y0, 0), (0, 1, 0)), ((0, DOOR_Y1, 0), (0, 1, 0)), ((0, 0, DOOR_Z0), (0, 0, 1)), ((s * 3.3, 0, 0), (1, 0, 0))):
            bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], plane_co=co, plane_no=no)
        drop = []
        for f in bm.faces:
            c = f.calc_center_median()
            if not (DOOR_Y0 < c.y < DOOR_Y1 and c.z > DOOR_Z0 and s * c.x > 3.3):
                drop.append(f)
        bmesh.ops.delete(bm, geom=drop, context="FACES")
        jamb = shell(bm, 0.12)
        new_obj(jamb, "DoorJamb" + side, smooth=35.0)
        new_obj(bm, "PanelDoor" + side, smooth=35.0)
        HINGE_OF["PanelDoor" + side] = HINGE_OF["DoorJamb" + side] = "Door" + side


def build_engine_bay():
    """inner fenders, firewall, radiator and a chrome-dressed V8 under the hood"""
    box("Under", -2.4, -10.05, 1.18, 2.4, -2.7, 1.24)                         # bay floor
    for s in (-1, 1):
        box("Under", s * 2.3, -9.9, 1.2, s * 2.38, -2.7, 2.6)                # inner fender aprons (hide the wheel tubs)
        box("Under", s * 2.3, -9.4, 2.54, s * 3.45, -2.7, 2.58)              # inner fender tops
    box("Under", -2.4, -2.76, 1.2, 2.4, -2.68, 2.7)                           # firewall
    box("Dark", -2.4, -9.95, 1.3, 2.4, -9.75, 2.55)                           # radiator
    for i in range(12):
        x = -2.2 + i * 0.4
        box("Chrome", x - 0.02, -9.74, 1.4, x + 0.02, -9.72, 2.45)
    box("Dark", -0.9, -8.2, 1.25, 0.9, -4.6, 1.95, bev=0.06)                 # block
    for s in (-1, 1):
        box("Chrome", s * 0.55, -8.0, 1.95, s * 1.15, -4.8, 2.2, bev=0.06)  # valve covers on the two banks
        for k in range(4):                                                    # headers down the sides
            y = -7.6 + k * 0.85
            beam("Chrome", (s * 0.9, y, 1.7), (s * 1.5, y + 0.25, 1.45), 0.11, 0.11)
            beam("Chrome", (s * 1.5, y + 0.25, 1.45), (s * 1.55, y + 0.3, 1.25), 0.11, 0.11)
    cyl("Chrome", (0, -6.4, 2.2), (0, -6.4, 2.28), 0.18, seg=12)              # carb neck
    cyl("Chrome", (0, -6.4, 2.28), (0, -6.4, 2.5), 0.62, seg=28, bev=0.04)    # air cleaner
    cyl("Dark", (0, -6.4, 2.5), (0, -6.4, 2.53), 0.08, seg=10)
    box("Dark", 1.6, -4.4, 1.25, 2.2, -3.4, 1.9, bev=0.04)                   # battery
    cyl("Chrome", (-1.8, -3.5, 1.3), (-1.8, -3.5, 2.1), 0.3, seg=18)          # brake booster


def build_fuel_door():
    y0, y1, z0, z1 = FUEL
    box("Under", 3.80, y0 + 0.06, z0 + 0.06, 3.818, y1 - 0.06, z1 - 0.06)       # recess
    cyl("Chrome", (3.818, (y0 + y1) / 2, (z0 + z1) / 2), (3.83, (y0 + y1) / 2, (z0 + z1) / 2), 0.15, seg=16)   # cap
    box("PanelFuel", 3.834, y0, z0, 3.852, y1, z1, bev=0.03)


def door_rule(kind):
    """which pieces of a kind ride a door: (min |x|, min z, max z), or None"""
    info = OPT_INFO.get(kind)
    if info:
        if info["slot"] == "Doors":
            return 2.95, 1.0, 3.2
        if info["slot"] in ("SideTrim", "Mirrors"):
            return 3.3, DOOR_Z0, 3.8
        return None
    if kind == "RoofGlass":
        return 2.8, 2.8, 4.7
    if kind == "Chrome":
        return 3.3, DOOR_Z0, 3.0
    return None


WINDOWS = {}


def split_onto_doors():
    """move the bits of trim, glass, mirrors and door cards that sit on a door onto that door"""
    for ob in list(OBJS):
        if ob.get("style") != "Lowrider" or "__" in ob["kind"]:
            continue
        rule = door_rule(ob["kind"])
        if not rule:
            continue
        xmin, zmin, zmax = rule
        bake(ob)
        me = ob.data
        me.transform(ob.matrix_world)
        ob.matrix_world = Matrix.Identity(4)
        bm = bmesh.new()
        bm.from_mesh(me)
        if not any(DOOR_Y0 < v.co.y < DOOR_Y1 and abs(v.co.x) > xmin for v in bm.verts):
            bm.free()
            continue
        for y in (DOOR_Y0, DOOR_Y1):
            bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], plane_co=(0, y, 0), plane_no=(0, 1, 0))
        bm.faces.index_update()
        bm.to_mesh(me)                                    # mesh polygon i == bm face i from here on
        moved = set()
        for s in (1, -1):
            sel = set()
            for f in bm.faces:
                c = f.calc_center_median()
                if DOOR_Y0 < c.y < DOOR_Y1 and s * c.x > xmin and zmin < c.z < zmax:
                    sel.add(f.index)
            if not sel:
                continue
            part = bmesh.new()
            part.from_mesh(me)
            part.faces.ensure_lookup_table()
            bmesh.ops.delete(part, geom=[f for f in part.faces if f.index not in sel], context="FACES")
            hinge = "Door" + ("L" if s > 0 else "R")
            kind = ob["kind"] + "__" + hinge
            if ob["kind"] == "RoofGlass":
                # door glass is its own piece so it can roll down into the door (Kit.SetWindow)
                kind = "RoofGlass__Win" + hinge
                zs = [v.co.z for v in part.verts]
                WINDOWS[hinge] = {"piece": kind, "drop": max(0.0, min(max(zs) - min(zs) + 0.02, min(zs) - DOOR_Z0 - 0.12))}
            if kind in OPT_INFO or ob["kind"] in OPT_INFO:
                OPT_INFO[kind] = dict(OPT_INFO[ob["kind"]], hinge=hinge)
            else:
                HINGE_OF[kind] = hinge
            new_obj(part, kind, style="Lowrider", smooth=ob.get("smooth", 0.0))
            moved |= sel
        bm.faces.ensure_lookup_table()
        bmesh.ops.delete(bm, geom=[f for f in bm.faces if f.index in moved], context="FACES")
        bm.to_mesh(me)
        bm.free()
    for k, v in OPT_INFO.items():
        if v["slot"] in HINGE_SLOTS and "hinge" not in v:
            v["hinge"] = HINGE_SLOTS[v["slot"]]


# ------------------------------------------------------------------ paint panels (UV-mapped for the vinyls)
PANELS = {  # Blender stud bounds of each vinyl image; must match PANELS in make_lowrider_vinyls.py
    "side": ((-10.5, 10.5), (0.65, 2.95)),    # y (front -> rear = image left -> right), z (top of image = up)
    "hood": ((-3.85, 3.85), (-10.4, -2.7)),   # x (car's left = image left), y (front = image top)
    "trunk": ((-3.2, 3.2), (6.0, 9.85)),
    "roof": ((-3.1, 3.1), (-0.85, 3.4)),
}
PANEL_OF = {"PanelSideL": "side", "PanelSideR": "side", "PanelHood": "hood", "Lid": "trunk", "PanelRoof": "roof",
            "PanelDoorL": "side", "PanelDoorR": "side", "PanelFuel": "side"}
SOURCE_OF = {"side": "PanelSideL", "hood": "PanelHood", "trunk": "Lid", "roof": "PanelRoof"}


def panel_uv(panel, co):
    (a0, a1), (b0, b1) = PANELS[panel]
    if panel == "side":
        return ((co.y - a0) / (a1 - a0), (co.z - b0) / (b1 - b0))
    return ((a1 - co.x) / (a1 - a0), 1 - (co.y - b0) / (b1 - b0))


def set_uv(ob, panel):
    bake(ob)
    me = ob.data
    for layer in list(me.uv_layers):
        me.uv_layers.remove(layer)
    uv = me.uv_layers.new(name="UVMap")
    for poly in me.polygons:
        for li in poly.loop_indices:
            co = ob.matrix_world @ me.vertices[me.loops[li].vertex_index].co
            uv.data[li].uv = panel_uv(panel, co)
    ob["uv"] = True


def split_panels():
    """cut the lofted body's skin into the paint panels: both sides, the hood; lid and roof are already pieces"""
    body = [o for o in OBJS if o.get("loft")][0]
    bake(body)
    regions = {}
    for f in body.data.polygons:
        c, n = f.center, f.normal
        if abs(n.x) > 0.5 and abs(c.x) > W - 0.35:
            r = "PanelSideL" if c.x > 0 else "PanelSideR"
        elif n.z > 0.5 and -10.45 < c.y < -2.62:
            r = "PanelHood"
        else:
            r = "Body"
        regions.setdefault(r, set()).add(f.index)
    moved = set()
    for r, idx in regions.items():
        if r == "Body":
            continue
        bm = bmesh.new()
        bm.from_mesh(body.data)
        bm.faces.ensure_lookup_table()
        bmesh.ops.delete(bm, geom=[f for f in bm.faces if f.index not in idx], context="FACES")
        set_uv(new_obj(bm, r, smooth=35.0), PANEL_OF[r])
        moved |= idx
    bm = bmesh.new()
    bm.from_mesh(body.data)
    bm.faces.ensure_lookup_table()
    bmesh.ops.delete(bm, geom=[f for f in bm.faces if f.index in moved], context="FACES")
    bm.to_mesh(body.data)
    bm.free()
    for o in list(OBJS):
        if o["kind"] in ("Lid", "PanelRoof", "PanelDoorL", "PanelDoorR", "PanelFuel"):
            set_uv(o, PANEL_OF[o["kind"]])
        if o["kind"] == "PanelHood":                      # the hood's underside, so it looks solid when it's up
            bm = bmesh.new()
            bm.from_mesh(o.data)
            bm.transform(o.matrix_world)
            new_obj(shell(bm, 0.08), "HoodInner", smooth=35.0)
            bm.free()


def vinyl_dir():
    for d in (os.path.join(OUT, "lowrider_vinyls"), os.path.join(HERE, "lowrider_vinyls")):
        if os.path.isdir(d):
            return d
    return None


def vinyl_files():
    """{livery: {panel: path}} from lowrider_vinyls/<livery>_<panel>.png"""
    out = {}
    d = vinyl_dir()
    if not d:
        print("NEONCOAST_WARN no lowrider_vinyls folder: run make_lowrider_vinyls.py first")
        return out
    for fn in sorted(os.listdir(d)):
        if fn.endswith(".png") and "_" in fn:
            liv, pan = fn[:-4].rsplit("_", 1)
            if pan in PANELS:
                out.setdefault(liv, {})[pan] = os.path.join(d, fn)
    return out


def build_wheel(ox):
    st = "LowriderWheel"
    c = Vector((ox, 0, 0))
    X = Vector((1, 0, 0))
    # low-profile tyre (a closed ring section) with a thin whitewall band on the outer sidewall
    revolve("Tire", c, [(0.7, -0.3), (0.98, -0.34), (1.1, -0.31), (WR, -0.2), (WR, 0.2), (1.1, 0.31), (0.98, 0.34), (0.7, 0.3), (0.7, -0.3)], style=st)
    revolve("Whitewall", c, [(0.86, 0.338), (0.97, 0.343)], style=st)
    # open rim barrel, chrome lip and dish, dark back plate so you can't see through the spokes
    revolve("Rim", c, [(0.7, -0.29), (0.66, -0.25), (0.66, 0.2), (0.7, 0.22), (0.75, 0.27), (0.7, 0.3), (0.6, 0.26), (0.55, 0.2)], style=st)
    cyl("Tire", c - X * 0.3, c - X * 0.26, 0.67, seg=40, style=st)
    # 100 spokes, cross-laced in three rows from the hub flanges to the rim
    rows = [(40, 0.30, 0.16, 0.18, 0.56), (30, 0.12, 0.15, 0.02, 0.63), (30, -0.12, 0.15, -0.16, 0.64)]
    for (n, hx, hr, rx, rr) in rows:
        for k in range(n):
            a = 2 * math.pi * k / n
            cross = 0.42 if k % 2 == 0 else -0.42
            p0 = c + Vector((hx, hr * math.cos(a), hr * math.sin(a)))
            p1 = c + Vector((rx, rr * math.cos(a + cross), rr * math.sin(a + cross)))
            beam("Spokes", p0, p1, 0.026, 0.026, up=(1, 0, 0), style=st)
    cyl("Hub", c - X * 0.15, c + X * 0.34, 0.17, seg=24, style=st)
    cyl("Hub", c + X * 0.34, c + X * 0.46, 0.2, seg=24, style=st, r2=0.12)
    for s in (-1, 1):                                                          # two-bar knock-off
        beam("Hub", c + Vector((0.44, 0, 0)), c + Vector((0.5, s * 0.42, s * 0.05)), 0.07, 0.12, up=(1, 0, 0), style=st)
        cyl("Hub", c + Vector((0.47, s * 0.42, s * 0.05)) - X * 0.04, c + Vector((0.47, s * 0.42, s * 0.05)) + X * 0.05, 0.06, seg=10, style=st)


# ------------------------------------------------------------------ the shop: Low & Slow Kustoms
def text_mesh(kind, txt, x, y, z, size, style, depth=0.25, face_y=-1):
    cu = bpy.data.curves.new("txt", "FONT")
    cu.body = txt
    cu.size = size
    cu.extrude = depth / 2
    cu.align_x = "CENTER"
    ob = bpy.data.objects.new("txt", cu)
    bpy.context.scene.collection.objects.link(ob)
    ob.rotation_euler = (math.pi / 2, 0, 0 if face_y < 0 else math.pi)
    ob.location = (x, y, z)
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(ob.evaluated_get(dg))
    me.transform(ob.matrix_world)
    bpy.data.objects.remove(ob)
    bpy.data.curves.remove(cu)
    obm = bpy.data.objects.new(kind, me)
    bpy.context.scene.collection.objects.link(obm)
    obm["kind"], obm["style"], obm["smooth"] = kind, style, 0.0
    OBJS.append(obm)
    return obm


def build_shop():
    H = House("LowSlowShop")
    X0, X1, Y0, Y1, HGT = -27.0, 27.0, -19.0, 19.0, 19.0
    T = 1.0
    doors = [(-23.0, -6.0, 0.0, 12.5), (6.0, 23.0, 0.0, 12.5)]
    H.wall("x", Y0, -1, X0, X1, 0, HGT, openings=doors + [(-2.2, 2.2, 0, 8.0)])   # front: two bays + walk-in door
    H.wall("x", Y1, 1, X0, X1, 0, HGT, openings=[(-14, -8, 6, 11), (8, 14, 6, 11)])
    H.wall("y", X0, -1, Y0, Y1, 0, HGT, openings=[(-6, 6, 6, 11)])
    H.wall("y", X1, 1, Y0, Y1, 0, HGT)
    H.p("Foundation").box(X0 - 0.6, Y0 - 0.6, -0.6, X1 + 0.6, Y1 + 0.6, 0.0)
    H.p("ShopFloor").box(X0, Y0, 0.0, X1, Y1, 0.1)
    H.col(X0, Y0, -0.6, X1, Y1, 0.1, "floor")
    H.p("Roof").box(X0 - 0.6, Y0 - 0.6, HGT, X1 + 0.6, Y1 + 0.6, HGT + 0.8)          # flat roof + parapet
    H.col(X0 - 0.6, Y0 - 0.6, HGT, X1 + 0.6, Y1 + 0.6, HGT + 0.8, "roof")
    H.p("Ceiling").box(X0, Y0, HGT - 0.3, X1, Y1, HGT)
    for (a0, b0, a1, b1) in ((X0 - 0.6, Y0 - 0.6, X1 + 0.6, Y0), (X0 - 0.6, Y1, X1 + 0.6, Y1 + 0.6), (X0 - 0.6, Y0, X0, Y1), (X1, Y0, X1 + 0.6, Y1)):
        H.p("Trim").box(a0, b0, HGT + 0.8, a1, b1, HGT + 2.4)
    # sign band over the doors, neon lettering, neon outline
    H.p("SignBack").box(-20, Y0 - 1.4, 13.6, 20, Y0 - 0.55, 18.2)
    H.col(-20, Y0 - 1.4, 13.6, 20, Y0 - 0.55, 18.2)
    for z in (13.75, 18.05):
        H.p("Neon2").box(-19.8, Y0 - 1.5, z - 0.1, 19.8, Y0 - 1.4, z + 0.1)
    for x in (-19.8, 19.8):
        H.p("Neon2").box(x - 0.1, Y0 - 1.5, 13.75, x + 0.1, Y0 - 1.4, 18.05)
    # bay 1: paint turntable; bay 2: hop pit with a height board on the back wall
    H.p("Turntable").box(-21.0, -12.0, 0.1, -8.0, 4.0, 0.2)
    H.p("HopPit").box(8.0, -12.0, 0.1, 21.0, 4.0, 0.14)
    H.p("ShopFloor").box(8.6, -11.4, 0.1, 20.4, 3.4, 0.16)
    H.p("HopBoard").box(10.0, Y1 - T - 0.2, 0.5, 19.0, Y1 - T, 13.0)
    for k in range(0, 25):
        z = 0.5 + k * 0.5
        w = 2.4 if k % 2 == 0 else 1.2
        H.p("HopTick").box(14.5 - w / 2, Y1 - T - 0.3, z - 0.05, 14.5 + w / 2, Y1 - T - 0.2, z + 0.05)
    # work bench, tool wall, tyre stacks, a mural on the side wall (sunset band)
    H.p("Bench").box(X1 - T - 3.0, -6.0, 0.1, X1 - T, 6.0, 3.6)
    H.col(X1 - T - 3.0, -6.0, 0.1, X1 - T, 6.0, 3.6)
    H.p("Tools").box(X1 - T - 0.25, -5.5, 5.0, X1 - T, 5.5, 9.0)
    for (tx, ty) in ((X0 + T + 1.6, 12.0), (X0 + T + 1.6, 15.2)):
        for k in range(4):
            H.p("Tire").box(tx - 1.2, ty - 1.2, 0.1 + k * 0.7, tx + 1.2, ty + 1.2, 0.1 + k * 0.7 + 0.62)
        H.col(tx - 1.2, ty - 1.2, 0.1, tx + 1.2, ty + 1.2, 2.9)
    H.p("Mural").box(X0 + T, -14.0, 9.0, X0 + T + 0.12, 10.0, 15.0)
    H.p("Neon").box(X0 + T + 0.12, -14.0, 11.9, X0 + T + 0.2, 10.0, 12.1)
    # ceiling strip lights
    for x in (-14.5, 14.5):
        for y in (-12, 0, 12):
            H.p("Neon2").box(x - 4, y - 0.3, HGT - 0.5, x + 4, y + 0.3, HGT - 0.3)
    H.notes.update({
        "bay1": [-14.5, -4.0, 0.2], "bay2": [14.5, -4.0, 0.14], "turntable": [-14.5, -4.0, 0.2],
        "hopPit": {"min": [8.0, -12.0, 0.0], "max": [21.0, 4.0, 8.0]}, "hopBoardBase": [14.5, Y1 - T - 0.3, 0.5],
        "custom": {"min": [-21.0, -12.0, 0.0], "max": [-8.0, 4.0, 8.0]}, "counter": [X1 - T - 1.5, 0.0, 3.6],
        "front": [0.0, Y0 - 2.0, 0.0], "spawn": [-14.5, Y0 - 14.0, 0.2], "size": [X1 - X0, Y1 - Y0, HGT],
    })
    objs, tris = H.build()
    for ob in objs:
        ob["style"], ob["kind"], ob["smooth"] = "LowSlowShop", ob.name.split("_", 1)[1], 0.0
    # neon lettering (the shop's own name, original)
    t1 = text_mesh("Neon", "LOW & SLOW", 0, Y0 - 1.5, 15.9, 2.4, "LowSlowShop")
    t2 = text_mesh("Neon2", "KUSTOMS", 0, Y0 - 1.5, 14.1, 1.5, "LowSlowShop")
    return H, objs + [t1, t2]


exec(compile(open(os.path.join(HERE, "build_lowrider_parts.py")).read(), "build_lowrider_parts.py", "exec"), globals())
build_car()
build_options()
split_onto_doors()
split_panels()
car, car_tris = join_style("Lowrider", "Lowrider")
# every vinyl image on a copy of its panel: importing this GLB in Studio uploads the images
VINYLS = vinyl_files()
vinyl_objs = []
by_kind = {ob.name.split("_", 1)[1]: ob for ob in car}
for liv, panels in sorted(VINYLS.items()):
    for pan, path in sorted(panels.items()):
        src = by_kind[SOURCE_OF[pan]]
        cp = src.copy()
        cp.data = src.data.copy()
        cp.name = f"Livery_{liv}_{pan}"
        cp.data.name = cp.name
        cp.data.materials.clear()
        cp.data.materials.append(image_mat(cp.name, path))
        bpy.context.scene.collection.objects.link(cp)
        vinyl_objs.append(cp)
if vinyl_objs:
    export(vinyl_objs, "LowriderVinyls.glb")
for ob in vinyl_objs:
    bpy.data.objects.remove(ob)
WHEEL_X = 30.0
build_wheel_options(WHEEL_X)
wheel, wheel_tris = join_style("LowriderWheel", "LowriderWheel")
export(car + wheel, "Lowrider.glb")
H, shop_objs = build_shop()
shop, shop_tris = join_style("LowSlowShop", "LowSlowShop")
export(shop, "LowSlowShop.glb")

car_ext, wheel_ext, shop_ext = extents(car), extents(wheel), extents(shop)
meta = {
    "Lowrider": {"pieces": sorted(car_tris), "triangles": car_tris, "extents_studs": car_ext,
                 "wheels": {"FL": [WX, WY_F, WR], "FR": [-WX, WY_F, WR], "RL": [WX, WY_R, WR], "RR": [-WX, WY_R, WR]},
                 "wheelRadius": WR, "lidHinge": [0.0, 6.03, deck_z(0, 6.03)], "bodyHalfWidth": W, "rocker": ZB, "deck": TOP, "roof": 4.78},
    "LowriderWheel": {"pieces": sorted(wheel_tris), "triangles": wheel_tris, "extents_studs": wheel_ext, "centre": [WHEEL_X, 0.0, 0.0]},
    "LowSlowShop": {"pieces": sorted(shop_tris), "triangles": shop_tris, "extents_studs": shop_ext, "notes": H.notes, "colliders": H.colliders},
}
with open(os.path.join(OUT, "lowrider.json"), "w") as f:
    json.dump(meta, f)


# ------------------------------------------------------------------ game data (NCLowriderData.lua)
cmn, cmx = imp_ext(car_ext)
wmn, wmx = imp_ext(wheel_ext)
smn, smx = imp_ext(shop_ext)
sn = H.notes
data = {
    "Car": {
        "ImportMin": cmn, "ImportMax": cmx, "Pieces": sorted(k.split("_", 1)[1] for k in car_tris),
        "Wheels": {k: car_pt(v) for k, v in meta["Lowrider"]["wheels"].items()}, "WheelRadius": WR,
        "LidHinge": car_pt(meta["Lowrider"]["lidHinge"]),
        # opening panels: Pivot / Axis in the car frame, Open = degrees it swings to; HingeOf = piece -> its hinge
        "Hinges": {k: {"Pivot": car_pt(h["pivot"]), "Axis": car_pt(h["axis"]), "Open": h["open"], "Kind": h["kind"]} for k, h in HINGES.items()},
        "HingeOf": {k: v for k, v in HINGE_OF.items() if f"Lowrider_{k}" in car_tris},
        # collision hull boxes in the car frame: lower body, greenhouse
        "Hull": [car_box((-W, -10.8, ZB), (W, 10.85, TOP)), car_box((-3.1, -2.6, TOP), (3.1, 5.2, 4.75))],
        "Seats": {"Driver": car_pt((1.55, 0.35, 1.75 - SEAT_DROP - 0.2)), "Passenger": car_pt((-1.55, 0.35, 1.75 - SEAT_DROP - 0.2)),
                  "RearL": car_pt((1.55, 3.3, 1.75 - SEAT_DROP - 0.2)), "RearR": car_pt((-1.55, 3.3, 1.75 - SEAT_DROP - 0.2))},
        "FrontBumper": car_pt((0, -10.75, 1.22)), "RearBumper": car_pt((0, 10.8, 1.22)),
        # which panel each paint piece prints, and which vinyl images exist per livery
        "PanelOf": PANEL_OF, "Vinyls": {liv: sorted(p) for liv, p in VINYLS.items()},
        # swappable parts: piece kind -> {slot, variant, mat}; Options = slot -> its variants
        "OptInfo": {k: v for k, v in OPT_INFO.items() if f"Lowrider_{k}" in car_tris},
        "Options": options_of(OPT_INFO, car_tris, "Lowrider_"),
        # the dash gauge face (live speedometer) and the club plaque in the rear window
        "Gauge": {"Centre": car_pt((1.55, -2.30, 2.62)), "Size": [1.6, 0.418], "Tilt": 16.7},
        "Windows": {k: {"Piece": w["piece"], "Drop": round(w["drop"], 3), "Dir": [0, -1, 0]} for k, w in WINDOWS.items()},
        "Steer": {"Centre": car_pt((1.55, -1.7, 2.92)), "Axis": [0.0, round(0.83 / math.hypot(0.55, 0.83), 4), round(0.55 / math.hypot(0.55, 0.83), 4)]},
        "Plaque": {"Centre": car_pt((0.0, 4.68, 3.35)), "Size": [2.0, 0.6]},
    },
    "Wheel": {"ImportMin": wmn, "ImportMax": wmx, "Centre": imp_pt((WHEEL_X, 0, 0)),
              "Pieces": sorted(k.split("_", 1)[1] for k in wheel_tris),
              "OptInfo": {k: v for k, v in WHEEL_INFO.items() if f"LowriderWheel_{k}" in wheel_tris},
              "Options": options_of(WHEEL_INFO, wheel_tris, "LowriderWheel_")},
    "Shop": {
        "ImportMin": smn, "ImportMax": smx, "Pieces": sorted(k.split("_", 1)[1] for k in shop_tris),
        "Colliders": [car_box(c["min"], c["max"]) for c in H.colliders],
        "Bay1": car_pt(sn["bay1"]), "Bay2": car_pt(sn["bay2"]), "Turntable": car_pt(sn["turntable"]),
        "HopPit": car_box(sn["hopPit"]["min"], sn["hopPit"]["max"]), "Custom": car_box(sn["custom"]["min"], sn["custom"]["max"]),
        "HopBoardBase": car_pt(sn["hopBoardBase"]), "Counter": car_pt(sn["counter"]), "Spawn": car_pt(sn["spawn"]),
        "Size": sn["size"],
    },
}
with open(os.path.join(OUT, "NCLowriderData.lua"), "w") as f:
    f.write("-- NCLowriderData (ModuleScript, ReplicatedStorage). GENERATED by build_lowrider.py: do not edit by hand.\n")
    f.write("-- Car / shop positions are in the model's own Roblox frame: front = -Z (LookVector), X = right, Y = up,\n")
    f.write("-- origin on the ground at the centre (car: between the axles at ride height). ImportMin/Max are the GLB's\n")
    f.write("-- bounds in the import frame (glTF Y-up), used by NCLowriderKit.Prepare to line the uploaded meshes up.\n")
    f.write("return " + lua(data) + "\n")

# ------------------------------------------------------------------ previews
scene, cam = setup_render()
scene.render.resolution_x, scene.render.resolution_y = 1400, 820
if os.environ.get("NC_PREVIEW_ENGINE", "").upper() == "CYCLES":      # machines without a GPU: render on the CPU
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = int(os.environ.get("NC_SAMPLES", "24"))
    scene.cycles.use_denoising = False
    scene.world.use_nodes = True
    bg = scene.world.node_tree.nodes.get("Background")
    if bg:
        bg.inputs["Color"].default_value = (0.55, 0.65, 0.8, 1)
        bg.inputs["Strength"].default_value = 0.9
    sun = bpy.data.objects.new("Sun", bpy.data.lights.new("Sun", "SUN"))
    sun.data.energy = 4.0
    sun.rotation_euler = (math.radians(50), 0, math.radians(30))
    scene.collection.objects.link(sun)
    gp = bpy.data.meshes.new("Ground")
    gbm = bmesh.new()
    bmesh.ops.create_grid(gbm, x_segments=1, y_segments=1, size=400)
    gbm.to_mesh(gp)
    gbm.free()
    g = bpy.data.objects.new("Ground", gp)
    g["style"] = "Lowrider"
    gm = bpy.data.materials.new("Ground")
    gm.diffuse_color = (0.25, 0.25, 0.27, 1)
    gp.materials.append(gm)
    scene.collection.objects.link(g)
scene.display.shading.light = "STUDIO"
scene.display.shading.show_specular_highlight = True
for ob in shop:
    ob.location.x += 200
for (wx, wy) in ((WX, WY_F), (-WX, WY_F), (WX, WY_R), (-WX, WY_R)):      # preview-only wheels on the car
    for ob in wheel:
        d = ob.copy()
        d["style"] = "Lowrider"
        d["pkind"] = ob["pkind"]
        scene.collection.objects.link(d)
        d.matrix_world = Matrix.Translation((wx, wy, WR)) @ Matrix.Rotation(0 if wx > 0 else math.pi, 4, "Z") @ Matrix.Translation((-WHEEL_X, 0, 0))
PAINT = lin(COLORS["Body"])
plain = {}
BASE_BUILD = {"FrontBumper": "Classic", "RearBumper": "Classic", "Grille": "Bars", "Hood": "Spear", "Mirrors": "Bullet",
              "Seats": "Rolls", "Steering": "Chain", "Dash": "Classic", "Shifter": "Column", "Trunk": "Street",
              "Rim": "Wire100", "KO": "Bar2", "Tire": "Classic", "Band": "ClassicThin",
              "Headlights": "Quad", "Taillights": "Triple", "SideTrim": "Classic", "Doors": "Rolls", "Headliner": "Plain", "Pedals": "Stock"}


def part_visible(ob, build):
    k = ob.get("pkind", "")
    info = OPT_INFO.get(k) or WHEEL_INFO.get(k)
    return info is None or build.get(info["slot"]) == info["variant"]


def show_livery(liv, build=None, paint=None):
    """print a livery's vinyls over the paint on the preview car, showing only the parts in the build"""
    b = dict(BASE_BUILD, **(build or {}))
    pc = lin(paint) if paint else PAINT
    for ob in scene.objects:
        if ob.type != "MESH":
            continue
        ob.hide_render = ob.get("style") != "Lowrider" or not part_visible(ob, b)
        if b.get("Top") == "Down" and ob.get("pkind") in ("RoofGlass", "RoofBody", "RoofChrome", "PanelRoof"):
            ob.hide_render = True
        kind = ob.get("pkind", "")
        if kind in PANEL_OF or (paint and OPT_INFO.get(kind, {}).get("mat") == "Body") or (paint and kind in ("Body", "RoofBody", "HoodInner", "DoorJambL", "DoorJambR")):
            plain.setdefault(ob.name, ob.data.materials[0])
            path = VINYLS.get(liv, {}).get(PANEL_OF.get(kind, ""))
            if path:
                ob.data.materials[0] = image_mat(f"prev_{liv}_{kind}_{len(plain)}", path, pc)
            elif paint:
                m = plain[ob.name].copy()
                m.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (*pc, 1)
                ob.data.materials[0] = m
            else:
                ob.data.materials[0] = plain[ob.name]
        elif ob.name in plain:
            ob.data.materials[0] = plain[ob.name]


def shot(name, loc, tgt):
    cam.location = loc
    cam.rotation_euler = (Vector(tgt) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
    scene.render.filepath = os.path.join(PREV, f"Lowrider_{name}.png")
    bpy.ops.render.render(write_still=True)


show_livery("flames")
shot("flames_front34", (-17, -24, 7.5), (0, -1.5, 1.8))
shot("flames_side", (26, 0.5, 3.2), (0, 0.5, 2.0))
show_livery("showcar", {"Taillights": "Stacked", "FrontBumper": "Bullet", "RearBumper": "Bullet", "Grille": "Waterfall", "Ornament": "Wings", "Skirts": "Fender",
                        "Visor": "Chrome", "Continental": "Kit", "Trunk": "Show", "Rim": "Wire72", "KO": "Bar3", "Band": "ClassicWide"})
shot("showcar_front34", (-20, -16, 9), (0, 0.5, 1.8))
shot("showcar_rear34", (15, 25, 8.5), (0, 2.5, 1.8))
show_livery("purple_lace", {"Hood": "Louvers", "Spoiler": "Ducktail"}, paint=(0.25, 0.05, 0.4))
shot("purple_lace_top", (8, -14, 22), (0, 0.5, 1.5))
show_livery("lightning", {"Headlights": "Square", "Taillights": "Bar", "SideTrim": "", "FrontBumper": "Tube", "RearBumper": "Tube", "Grille": "Mesh", "Hood": "Scoop", "Spoiler": "Wing", "Skirts": "Rocker",
                     "Mirrors": "Rect", "Exhaust": "Side", "Glow": "On", "Rim": "Turbine", "KO": "Cap", "Tire": "Balloon", "Band": ""},
            paint=(0.02, 0.15, 0.55))
shot("street_front34", (-17, -24, 7.5), (0, -1.5, 1.8))
show_livery("retro_waves", {"Headlights": "Frenched", "SideTrim": "Belt", "FrontBumper": "Shaved", "RearBumper": "Shaved", "Grille": "Billet", "Hood": "Cowl", "Spoiler": "Fins",
                     "Mirrors": "Stem", "Ornament": "Sun", "Exhaust": "Turndown", "Rim": "Steelie", "KO": "", "Tire": "Skinny", "Band": "SkinnyDouble"},
            paint=(0.6, 0.85, 0.75))
shot("retro_front34", (-17, -24, 7.5), (0, -1.5, 1.8))
show_livery("tropical", {"Taillights": "Twin", "SideTrim": "Wide", "Skirts": "Fender", "Continental": "Kit", "RearBumper": "Bullet", "Rim": "Star", "KO": "Cap"}, paint=(0.02, 0.45, 0.5))
shot("tropical_rear34", (15, 25, 8.5), (0, 2.5, 1.8))
show_livery("scallops", {"Headlights": "Hooded", "SideTrim": "Sweep", "Grille": "Eggcrate", "Hood": "", "Ornament": "Comet", "Visor": "Body", "Rim": "Split"}, paint=(0.05, 0.05, 0.07))
shot("scallops_front34", (-17, -24, 7.5), (0, -1.5, 1.8))
show_livery("roses", {"SideTrim": "Double", "Rim": "Mesh", "KO": "Bar3"}, paint=(0.9, 0.85, 0.75))
shot("roses_side", (26, 0.5, 3.2), (0, 0.5, 2.0))
show_livery("flames_teal", {"Headlights": "Dual", "Top": "Down", "Doors": "Diamond", "Audio": "Neon", "Seats": "Diamond", "Steering": "Wood", "Dash": "Wood", "Grille": "Waterfall",
                            "Skirts": "Fender", "Rim": "Wire72", "KO": "Bar3", "Band": "ClassicWide"}, paint=(0.04, 0.05, 0.3))
shot("convertible_front34", (-17, -22, 9.5), (0, -0.5, 1.8))
show_livery("pinstripe", {"Taillights": "Oval", "Top": "Landau", "Ornament": "Wings", "Visor": "Chrome", "Mirrors": "Dual", "Rim": "Wire100", "Band": "ClassicDouble"},
            paint=(0.12, 0.02, 0.04))
shot("landau_rear34", (15, 25, 8.5), (0, 2.5, 1.8))
show_livery("none")
shot("clean_side", (26, 0.5, 3.2), (0, 0.5, 2.0))


def pose_hinges(frac, only=None, win=0.0):
    """swing every opening panel (and the parts riding on it) frac of the way open, like the game does"""
    for ob in scene.objects:
        k = ob.get("pkind")
        h = HINGE_OF.get(k) or (OPT_INFO.get(k) or {}).get("hinge")
        if not h or (only and h not in only):
            continue
        hg = HINGES[h]
        p = Vector(hg["pivot"])
        w = WINDOWS.get(h)
        down = Matrix.Translation((0, 0, -w["drop"] * win)) if w and k == w["piece"] else Matrix.Identity(4)
        ob.matrix_world = Matrix.Translation(p) @ Matrix.Rotation(math.radians(hg["open"] * frac), 4, Vector(hg["axis"])) @ Matrix.Translation(-p) @ down


show_livery("none")
pose_hinges(0.0, win=0.5)
shot("windows_half", (20, -6, 4.8), (0, 0, 2.6))
pose_hinges(0.0, win=1.0)
shot("windows_down", (26, 0.5, 4.2), (0, 0.5, 2.0))
pose_hinges(0.0)


show_livery("flames", {"Trunk": "Show", "Doors": "Diamond", "Seats": "Diamond"})
pose_hinges(1.0)
shot("open_front34", (-19, -22, 9), (0, -2.0, 1.8))
shot("open_rear34", (17, 24, 9), (0, 2.5, 1.8))
shot("open_top", (12, -16, 24), (0, -1.0, 1.5))
pose_hinges(0.0)
# interiors: looking down into the cabin
for (nm, b) in (("interior_classic", {"Seats": "Rolls", "Steering": "Chain", "Dash": "Classic", "Shifter": "Chain", "Dice": "On", "Headliner": ""}),
                ("interior_show", {"Seats": "Diamond", "Doors": "Diamond", "Steering": "Wood", "Dash": "Wood", "Shifter": "Crystal", "Plaque": "Chain", "Audio": "Speakers", "Headliner": ""}),
                ("interior_sport", {"Seats": "Buckets", "Doors": "Smooth", "Steering": "Sport", "Dash": "Digital", "Shifter": "THandle", "Audio": "Neon", "Headliner": ""}),
                ("interior_channel", {"Seats": "Channel", "Doors": "Channel", "Steering": "Banjo", "Dash": "Billet", "Shifter": "WoodKnob", "Headliner": ""}),
                ("interior_pillow", {"Seats": "Pillow", "Doors": "WoodInsert", "Steering": "Mini", "Dash": "Wood", "Shifter": "Chain", "Pedals": "Chain", "Headliner": ""})):
    show_livery("none", b)
    for ob in scene.objects:
        if ob.get("pkind") in ("PanelRoof", "Glass", "RoofGlass", "RoofBody", "RoofChrome", "Body"):
            ob.hide_render = True
    shot(nm, (6, -9, 13), (0.3, 0.6, 1.8))
# wheel line-up: every rim design with a different knock-off / tyre / whitewall
for ob in scene.objects:
    if ob.type == "MESH":
        ob.hide_render = True
lineup = []
combos = [("Wire100", "Bar2", "Classic", "ClassicThin"), ("Wire72", "Bar3", "Classic", "ClassicWide"), ("Star", "Cap", "Balloon", ""),
          ("Steelie", "", "Skinny", "SkinnyDouble"), ("Disc", "Cap", "Classic", "ClassicWide"), ("Turbine", "Cap", "Balloon", "BalloonThin"),
          ("Split", "Bar2", "Classic", ""), ("Mesh", "Bar3", "Classic", "ClassicDouble")]
for i, (r, ko, t, bd) in enumerate(combos):
    b = {"Rim": r, "KO": ko, "Tire": t, "Band": bd}
    for ob in wheel:
        if part_visible(ob, b):
            d = ob.copy()
            scene.collection.objects.link(d)
            d.hide_render = False
            d.matrix_world = Matrix.Translation((0, (i % 4) * 2.8, -(i // 4) * 2.8)) @ ob.matrix_world
            lineup.append(d)
shot("wheels_lineup", (WHEEL_X + 14, 4.2, -1.4), (WHEEL_X, 4.2, -1.4))
for d in lineup:
    bpy.data.objects.remove(d)
for ob in scene.objects:
    if ob.type == "MESH":
        ob.hide_render = ob.get("style") != "LowriderWheel" or not part_visible(ob, BASE_BUILD)
shot("wheel", (WHEEL_X + 4.2, -1.2, 0.6), (WHEEL_X, 0, 0))
for ob in shop:
    ob.location.x -= 200
for ob in car + wheel:
    ob.hide_render = True
render_views(scene, cam, ["LowSlowShop"], {"shop": ((-55, -70, 32), (0, 0, 8)), "shop_inside": ((0, -16, 9), (0, 18, 4))}, "LowSlowShop")
print("NEONCOAST_DONE", json.dumps({"car": sum(car_tris.values()), "wheel": sum(wheel_tris.values()), "shop": sum(shop_tris.values())}))
