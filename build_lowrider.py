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

# ------------------------------------------------------------------ object kit (objects joined per material at the end)
OBJS = []


def new_obj(bm, kind, style="Lowrider", smooth=0.0):
    me = bpy.data.meshes.new(kind)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(kind, me)
    bpy.context.scene.collection.objects.link(ob)
    ob["kind"], ob["style"], ob["smooth"] = kind, style, smooth
    OBJS.append(ob)
    return ob


def bevel(ob, w, seg=2):
    m = ob.modifiers.new("bev", "BEVEL")
    m.width, m.segments, m.limit_method = w, seg, "ANGLE"
    return ob


def cube(kind, c, s, bev=0.0, style="Lowrider", rot=None, seg=2):
    bm = bmesh.new()
    m = Matrix.Translation(c) @ (rot.to_4x4() if rot else Matrix.Identity(4)) @ Matrix.Diagonal((*s, 1))
    bmesh.ops.create_cube(bm, size=1.0, matrix=m)
    ob = new_obj(bm, kind, style)
    if bev:
        bevel(ob, bev, seg)
    return ob


def box(kind, x0, y0, z0, x1, y1, z1, bev=0.0, style="Lowrider"):
    return cube(kind, Vector(((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2)), (abs(x1 - x0), abs(y1 - y0), abs(z1 - z0)), bev, style)


def axis_rot(d):
    return Vector((0, 0, 1)).rotation_difference(Vector(d).normalized()).to_matrix()


def cyl(kind, p0, p1, r, seg=24, bev=0.0, style="Lowrider", r2=None, smooth=40.0):
    p0, p1 = Vector(p0), Vector(p1)
    d = p1 - p0
    bm = bmesh.new()
    m = Matrix.Translation((p0 + p1) / 2) @ axis_rot(d).to_4x4()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=seg, radius1=r, radius2=r if r2 is None else r2, depth=d.length, matrix=m)
    ob = new_obj(bm, kind, style, smooth)
    if bev:
        bevel(ob, bev, 2)
    return ob


def ring(kind, center, axis, r0, r1, t, seg=40, style="Lowrider"):
    """flat annulus of thickness t, axis = its normal"""
    bm = bmesh.new()
    rot = axis_rot(axis)
    c = Vector(center)
    n = Vector(axis).normalized()
    rings = []
    for (r, off) in ((r0, -t / 2), (r1, -t / 2), (r1, t / 2), (r0, t / 2)):
        vs = []
        for i in range(seg):
            a = 2 * math.pi * i / seg
            vs.append(bm.verts.new(c + rot @ Vector((r * math.cos(a), r * math.sin(a), 0)) + n * off))
        rings.append(vs)
    for k in range(4):
        A, B = rings[k], rings[(k + 1) % 4]
        for i in range(seg):
            j = (i + 1) % seg
            bm.faces.new((A[i], A[j], B[j], B[i]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return new_obj(bm, kind, style, 40.0)


def beam(kind, p0, p1, w, h, up=(0, 0, 1), style="Lowrider"):
    p0, p1 = Vector(p0), Vector(p1)
    f = (p1 - p0)
    L = f.length
    f.normalize()
    u = Vector(up)
    s = f.cross(u)
    if s.length < 1e-4:
        s = f.cross(Vector((1, 0, 0)))
    s.normalize()
    u = s.cross(f)
    rot = Matrix((s, f, u)).transposed()
    return cube(kind, (p0 + p1) / 2, (w, L, h), 0.0, style, rot)


def torus(kind, c, axis, R, r, seg=32, seg2=8, style="Lowrider"):
    bm = bmesh.new()
    rot = axis_rot(axis)
    c = Vector(c)
    grid = []
    for i in range(seg):
        a = 2 * math.pi * i / seg
        ca, sa = math.cos(a), math.sin(a)
        rowv = []
        for j in range(seg2):
            b = 2 * math.pi * j / seg2
            p = Vector(((R + r * math.cos(b)) * ca, (R + r * math.cos(b)) * sa, r * math.sin(b)))
            rowv.append(bm.verts.new(c + rot @ p))
        grid.append(rowv)
    for i in range(seg):
        for j in range(seg2):
            a, b = grid[i][j], grid[(i + 1) % seg][j]
            cc, d = grid[(i + 1) % seg][(j + 1) % seg2], grid[i][(j + 1) % seg2]
            bm.faces.new((a, b, cc, d))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return new_obj(bm, kind, style, 60.0)


def prism(kind, outer, inner, style="Lowrider"):
    """closed solid from two matching quads/polygons (outer face, inner face)"""
    bm = bmesh.new()
    o = [bm.verts.new(v) for v in outer]
    i = [bm.verts.new(v) for v in inner]
    n = len(o)
    bm.faces.new(o)
    bm.faces.new(list(reversed(i)))
    for k in range(n):
        bm.faces.new((o[k], o[(k + 1) % n], i[(k + 1) % n], i[k]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return new_obj(bm, kind, style)


def bake(ob):
    """apply every modifier (bevel, boolean)"""
    if not ob.modifiers:
        return ob
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(ob.evaluated_get(dg))
    old = ob.data
    ob.modifiers.clear()
    ob.data = me
    bpy.data.meshes.remove(old)
    return ob


# ------------------------------------------------------------------ car dimensions
W = 3.82                     # body half width
WR = 1.17                    # wheel radius (24.4 in at 1.15 studs per foot)
WX = 3.18                    # wheel centre |x|
WY_F, WY_R = -6.2, 5.6       # axle positions (wheelbase 11.8)
ARCH = 1.42
ZB, BELT, TOP = 0.75, 2.62, 2.80


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
    cutters.hide_render = True
    m = body.modifiers.new("arch", "BOOLEAN")
    m.operation, m.operand_type, m.collection, m.solver = "DIFFERENCE", "COLLECTION", cutters, "EXACT"
    bake(body)
    for ob in list(cutters.objects):
        bpy.data.objects.remove(ob)
    bpy.data.collections.remove(cutters)
    # trunk tub lining
    box("TrunkFloor", -3.15, 6.05, 1.25, 3.15, 9.8, 1.32)
    for s in (-1, 1):
        box("Under", s * 3.15, 6.05, 1.25, s * 3.22, 9.8, 2.6)
    box("Under", -3.2, 6.0, 1.25, 3.2, 6.07, 2.6)
    box("Under", -3.2, 9.78, 1.25, 3.2, 9.85, 2.6)
    # wheel-well liners (dark) so the tub reads as a well, not body colour
    for wy in (WY_F, WY_R):
        for s in (-1, 1):
            cyl("Under", (s * (WX - 0.74), wy, WR), (s * (WX - 0.70), wy, WR), ARCH, seg=32)

    # ---- greenhouse
    zb = 2.84
    xs_b, xs_t = 3.42, 2.92                              # glass line at the belt / roof (tumblehome)

    def gx(z):
        return xs_b + (xs_t - xs_b) * (z - zb) / (4.56 - zb)
    yA0, yA1 = -2.75, -0.85                               # windshield base / top
    yC0, yC1 = 3.3, 5.35                                  # rear glass top / base
    ROOF = 4.62
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
        for x in (2.62, 3.18):
            cyl("Headlight", (s * x, -10.2, 1.92), (s * x, -10.47, 1.92), 0.24, seg=20, bev=0.03)
            ring("Chrome", (s * x, -10.44, 1.92), (0, 1, 0), 0.23, 0.31, 0.08, seg=24)
        for x in (1.55, 2.3, 3.02):                                        # triple round taillights
            cyl("Taillight", (s * x, 10.25, 1.98), (s * x, 10.55, 1.98), 0.23, seg=20, bev=0.03)
            ring("Chrome", (s * x, 10.52, 1.98), (0, 1, 0), 0.22, 0.29, 0.08, seg=24)
        box("Chrome", s * 0.9, 10.44, 1.62, s * 3.4, 10.5, 1.66)            # rear cove trim
        # side spear (between the arches), rocker moulding, door seams, handle, mirror
        beam("Chrome", (s * (W + 0.02), WY_F + ARCH + 0.25, 2.12), (s * (W + 0.02), WY_R - ARCH - 0.25, 2.12), 0.06, 0.07)
        beam("Chrome", (s * (W + 0.02), WY_F - ARCH - 0.2, 2.12), (s * (W - 0.02), -9.9, 2.12), 0.06, 0.07)
        beam("Chrome", (s * (W + 0.02), WY_R + ARCH + 0.2, 2.12), (s * (W - 0.02), 10.0, 2.12), 0.06, 0.07)
        beam("Chrome", (s * (W * 0.975 + 0.02), WY_F + ARCH + 0.2, 0.98), (s * (W * 0.975 + 0.02), WY_R - ARCH - 0.2, 0.98), 0.05, 0.12)
        for y in (-2.65, 2.35):
            box("Seam", s * W - 0.02, y - 0.015, 0.95, s * W + 0.02, y + 0.015, 2.6)
        box("Chrome", s * (W + 0.03) - 0.04, 1.6, 2.38, s * (W + 0.03) + 0.04, 2.15, 2.46, bev=0.02)
    # ---- interior shell: carpet, door cards, steering column (seats, dash, wheel, shifter are parts)
    box("Carpet", -3.2, -2.6, 0.95, 3.2, 5.6, 1.05)
    for s in (-1, 1):
        box("Interior", s * 3.3 - 0.1, -2.4, 1.05, s * 3.3 + 0.1, 5.0, 2.75)           # door cards
        for k in range(6):
            z = 1.3 + k * 0.22
            box("Tuck", s * 3.18 - 0.03, -2.2, z, s * 3.18 + 0.03, 4.8, z + 0.06)
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


# ------------------------------------------------------------------ paint panels (UV-mapped for the vinyls)
PANELS = {  # Blender stud bounds of each vinyl image; must match PANELS in make_lowrider_vinyls.py
    "side": ((-10.5, 10.5), (0.65, 2.95)),    # y (front -> rear = image left -> right), z (top of image = up)
    "hood": ((-3.85, 3.85), (-10.4, -2.7)),   # x (car's left = image left), y (front = image top)
    "trunk": ((-3.2, 3.2), (6.0, 9.85)),
    "roof": ((-3.1, 3.1), (-0.85, 3.4)),
}
PANEL_OF = {"PanelSideL": "side", "PanelSideR": "side", "PanelHood": "hood", "Lid": "trunk", "PanelRoof": "roof"}
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
        if o["kind"] in ("Lid", "PanelRoof"):
            set_uv(o, PANEL_OF[o["kind"]])


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


def image_mat(name, path, base=None):
    """material with a vinyl image: alone (alpha blended), or printed over a base paint colour (previews)"""
    mat = bpy.data.materials.new(name)
    try:
        mat.use_nodes = True
    except Exception:
        pass
    nt = mat.node_tree
    b = nt.nodes.get("Principled BSDF")
    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.image = bpy.data.images.load(path, check_existing=True)
    if base is None:
        nt.links.new(tex.outputs["Color"], b.inputs["Base Color"])
        nt.links.new(tex.outputs["Alpha"], b.inputs["Alpha"])
        try:
            mat.blend_method = "BLEND"
        except Exception:
            pass
    else:
        mix = nt.nodes.new("ShaderNodeMix")
        mix.data_type = "RGBA"
        nt.links.new(tex.outputs["Alpha"], mix.inputs[0])
        mix.inputs[6].default_value = (*base, 1)
        nt.links.new(tex.outputs["Color"], mix.inputs[7])
        nt.links.new(mix.outputs[2], b.inputs["Base Color"])
        b.inputs["Coat Weight"].default_value = 1.0
        b.inputs["Roughness"].default_value = 0.3
    return mat


# ------------------------------------------------------------------ the wheel
def revolve(kind, c, profile, seg=48, style="Lowrider", smooth=50.0):
    """surface of revolution around the X axis through c; profile = [(radius, x offset), ...] (open)"""
    bm = bmesh.new()
    c = Vector(c)
    rings = []
    for i in range(seg):
        a = 2 * math.pi * i / seg
        rings.append([bm.verts.new(c + Vector((x, r * math.cos(a), r * math.sin(a)))) for (r, x) in profile])
    for i in range(seg):
        A, B = rings[i], rings[(i + 1) % seg]
        for k in range(len(profile) - 1):
            bm.faces.new((A[k], A[k + 1], B[k + 1], B[k]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return new_obj(bm, kind, style, smooth)


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


# ------------------------------------------------------------------ join + export
def join_style(style, prefix):
    """join every object of a style per material kind -> <prefix>_<Kind> (one mesh per material)"""
    groups = {}
    for ob in list(bpy.context.scene.objects):
        if ob.type == "MESH" and ob.get("style") == style:
            groups.setdefault(ob["kind"], []).append(ob)
    out, tris = [], {}
    for kind, obs in sorted(groups.items()):
        bm = bmesh.new()
        smooth = max(o.get("smooth", 0.0) for o in obs)
        custom_uv = any(o.get("uv") for o in obs)
        for ob in obs:
            bake(ob)
            me = ob.data.copy()
            me.transform(ob.matrix_world)
            bm.from_mesh(me)
            bpy.data.meshes.remove(me)
        for ob in obs:
            if ob in OBJS:
                OBJS.remove(ob)
            bpy.data.objects.remove(ob)
        bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=1e-5)
        name = f"{prefix}_{kind}"
        me = bpy.data.meshes.new(name)
        bm.to_mesh(me)
        bm.free()
        # box-projected UVs (1 tile per 8 studs) so imported meshes take materials cleanly; paint panels keep
        # their vinyl UVs
        uv = None if custom_uv else me.uv_layers.new(name="UVMap")
        for poly in (me.polygons if uv else []):
            n = poly.normal
            ax = max(range(3), key=lambda i: abs(n[i]))
            for li in poly.loop_indices:
                co = me.vertices[me.loops[li].vertex_index].co
                u, v = (co.x, co.y) if ax == 2 else ((co.y, co.z) if ax == 0 else (co.x, co.z))
                uv.data[li].uv = (u / 8.0, v / 8.0)
        if smooth > 0:
            for poly in me.polygons:
                poly.use_smooth = True
            try:
                me.set_sharp_from_angle(angle=math.radians(smooth))
            except Exception:
                pass
        ob = bpy.data.objects.new(name, me)
        bpy.context.scene.collection.objects.link(ob)
        ob["style"] = style
        ob["pkind"] = kind
        mat = bpy.data.materials.new(name)
        ck = "Body" if kind.startswith("Panel") else mat_color(kind)
        col = lin(COLORS.get(ck, (0.8, 0.8, 0.8)))
        mat.diffuse_color = (*col, 1)
        mat.metallic = 0.9 if ck in ("Chrome", "Rim", "Spokes", "Hub", "Dish", "Pump", "ContChrome", "SteeringWheel") else 0.0
        paint = ck in ("Body", "Lid", "ContBody") or kind.startswith("Panel")
        if ck == "Top":
            mat.roughness = 0.9
        mat.roughness = 0.15 if mat.metallic > 0.5 else (0.3 if paint else 0.7)
        try:
            mat.use_nodes = True
        except Exception:
            pass
        if mat.node_tree:
            b = mat.node_tree.nodes.get("Principled BSDF")
            if b:
                b.inputs["Base Color"].default_value = (*col, 1)
                b.inputs["Metallic"].default_value = mat.metallic
                b.inputs["Roughness"].default_value = mat.roughness
                if paint:
                    b.inputs["Coat Weight"].default_value = 1.0          # candy clear coat
                if ck in ("Headlight", "Taillight", "Neon", "Neon2", "Light"):
                    b.inputs["Emission Color"].default_value = (*col, 1)
                    b.inputs["Emission Strength"].default_value = 2.0
                if ck == "Glass":
                    b.inputs["Alpha"].default_value = 0.55
        me.materials.append(mat)
        me.calc_loop_triangles()
        tris[name] = len(me.loop_triangles)
        out.append(ob)
    return out, tris


def extents(objs):
    co = [ob.matrix_world @ v.co for ob in objs for v in ob.data.vertices]
    return {"x": [min(c.x for c in co), max(c.x for c in co)], "y": [min(c.y for c in co), max(c.y for c in co)], "z": [min(c.z for c in co), max(c.z for c in co)]}


def export(objs, fname):
    for ob in bpy.context.scene.objects:
        ob.select_set(False)
    for ob in objs:
        ob.select_set(True)
    bpy.ops.export_scene.gltf(filepath=os.path.join(OUT, fname), export_format="GLB", use_selection=True, export_apply=True, export_yup=True)


exec(compile(open(os.path.join(HERE, "build_lowrider_parts.py")).read(), "build_lowrider_parts.py", "exec"), globals())
build_car()
build_options()
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
def car_pt(p):          # Blender -> car-local Roblox frame (forward = -Z)
    x, y, z = p
    return [round(-x, 3), round(z, 3), round(y, 3)]


def imp_pt(p):          # Blender -> the GLB import frame (glTF Y-up: (x, z, -y))
    x, y, z = p
    return [round(x, 3), round(z, 3), round(-y, 3)]


def imp_ext(e):
    a = imp_pt((e["x"][0], e["y"][0], e["z"][0]))
    b = imp_pt((e["x"][1], e["y"][1], e["z"][1]))
    return [min(a[i], b[i]) for i in range(3)], [max(a[i], b[i]) for i in range(3)]


def car_box(mn, mx):
    a, b = car_pt(mn), car_pt(mx)
    return [min(a[0], b[0]), min(a[1], b[1]), min(a[2], b[2]), max(a[0], b[0]), max(a[1], b[1]), max(a[2], b[2])]


def lua(v, ind=""):
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (int, float)):
        return repr(round(v, 3)) if isinstance(v, float) else str(v)
    if isinstance(v, str):
        return json.dumps(v)
    if isinstance(v, (list, tuple)):
        if all(isinstance(x, (int, float, str)) and not isinstance(x, bool) for x in v):
            return "{" + ", ".join(lua(x) for x in v) + "}"
        return "{\n" + "".join(ind + "\t" + lua(x, ind + "\t") + ",\n" for x in v) + ind + "}"
    if isinstance(v, dict):
        items = []
        for k in sorted(v):
            key = k if k.isidentifier() else "[" + json.dumps(k) + "]"
            items.append(ind + "\t" + key + " = " + lua(v[k], ind + "\t") + ",\n")
        return "{\n" + "".join(items) + ind + "}"
    return "nil"


def options_of(info, tris, prefix):
    out = {}
    for k, v in info.items():
        if prefix + k in tris and v["variant"] not in out.setdefault(v["slot"], []):
            out[v["slot"]].append(v["variant"])
    return out


cmn, cmx = imp_ext(car_ext)
wmn, wmx = imp_ext(wheel_ext)
smn, smx = imp_ext(shop_ext)
sn = H.notes
data = {
    "Car": {
        "ImportMin": cmn, "ImportMax": cmx, "Pieces": sorted(k.split("_", 1)[1] for k in car_tris),
        "Wheels": {k: car_pt(v) for k, v in meta["Lowrider"]["wheels"].items()}, "WheelRadius": WR,
        "LidHinge": car_pt(meta["Lowrider"]["lidHinge"]),
        # collision hull boxes in the car frame: lower body, greenhouse
        "Hull": [car_box((-W, -10.8, ZB), (W, 10.85, TOP)), car_box((-3.1, -2.6, TOP), (3.1, 5.2, 4.75))],
        "Seats": {"Driver": car_pt((1.55, 0.35, 1.75)), "Passenger": car_pt((-1.55, 0.35, 1.75)),
                  "RearL": car_pt((1.55, 3.3, 1.75)), "RearR": car_pt((-1.55, 3.3, 1.75))},
        "FrontBumper": car_pt((0, -10.75, 1.22)), "RearBumper": car_pt((0, 10.8, 1.22)),
        # which panel each paint piece prints, and which vinyl images exist per livery
        "PanelOf": PANEL_OF, "Vinyls": {liv: sorted(p) for liv, p in VINYLS.items()},
        # swappable parts: piece kind -> {slot, variant, mat}; Options = slot -> its variants
        "OptInfo": {k: v for k, v in OPT_INFO.items() if f"Lowrider_{k}" in car_tris},
        "Options": options_of(OPT_INFO, car_tris, "Lowrider_"),
        # the dash gauge face (live speedometer) and the club plaque in the rear window
        "Gauge": {"Centre": car_pt((1.55, -2.30, 2.62)), "Size": [1.6, 0.418], "Tilt": 16.7},
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
              "Rim": "Wire100", "KO": "Bar2", "Tire": "Classic", "Band": "ClassicThin"}


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
        if kind in PANEL_OF or (paint and OPT_INFO.get(kind, {}).get("mat") == "Body") or (paint and kind in ("Body", "RoofBody")):
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
show_livery("showcar", {"FrontBumper": "Bullet", "RearBumper": "Bullet", "Grille": "Waterfall", "Ornament": "Wings", "Skirts": "Fender",
                        "Visor": "Chrome", "Continental": "Kit", "Trunk": "Show", "Rim": "Wire72", "KO": "Bar3", "Band": "ClassicWide"})
shot("showcar_front34", (-20, -16, 9), (0, 0.5, 1.8))
shot("showcar_rear34", (15, 25, 8.5), (0, 2.5, 1.8))
show_livery("purple_lace", {"Hood": "Louvers", "Spoiler": "Ducktail"}, paint=(0.25, 0.05, 0.4))
shot("purple_lace_top", (8, -14, 22), (0, 0.5, 1.5))
show_livery("lightning", {"FrontBumper": "Tube", "RearBumper": "Tube", "Grille": "Mesh", "Hood": "Scoop", "Spoiler": "Wing", "Skirts": "Rocker",
                     "Mirrors": "Rect", "Exhaust": "Side", "Glow": "On", "Rim": "Turbine", "KO": "Cap", "Tire": "Balloon", "Band": ""},
            paint=(0.02, 0.15, 0.55))
shot("street_front34", (-17, -24, 7.5), (0, -1.5, 1.8))
show_livery("retro_waves", {"FrontBumper": "Shaved", "RearBumper": "Shaved", "Grille": "Billet", "Hood": "Cowl", "Spoiler": "Fins",
                     "Mirrors": "Stem", "Ornament": "Sun", "Exhaust": "Turndown", "Rim": "Steelie", "KO": "", "Tire": "Skinny", "Band": "SkinnyDouble"},
            paint=(0.6, 0.85, 0.75))
shot("retro_front34", (-17, -24, 7.5), (0, -1.5, 1.8))
show_livery("tropical", {"Skirts": "Fender", "Continental": "Kit", "RearBumper": "Bullet", "Rim": "Star", "KO": "Cap"}, paint=(0.02, 0.45, 0.5))
shot("tropical_rear34", (15, 25, 8.5), (0, 2.5, 1.8))
show_livery("scallops", {"Grille": "Eggcrate", "Hood": "", "Ornament": "Comet", "Visor": "Body", "Rim": "Split"}, paint=(0.05, 0.05, 0.07))
shot("scallops_front34", (-17, -24, 7.5), (0, -1.5, 1.8))
show_livery("roses", {"Rim": "Mesh", "KO": "Bar3"}, paint=(0.9, 0.85, 0.75))
shot("roses_side", (26, 0.5, 3.2), (0, 0.5, 2.0))
show_livery("flames_teal", {"Top": "Down", "Seats": "Diamond", "Steering": "Wood", "Dash": "Wood", "Grille": "Waterfall",
                            "Skirts": "Fender", "Rim": "Wire72", "KO": "Bar3", "Band": "ClassicWide"}, paint=(0.04, 0.05, 0.3))
shot("convertible_front34", (-17, -22, 9.5), (0, -0.5, 1.8))
show_livery("pinstripe", {"Top": "Landau", "Ornament": "Wings", "Visor": "Chrome", "Mirrors": "Dual", "Rim": "Wire100", "Band": "ClassicDouble"},
            paint=(0.12, 0.02, 0.04))
shot("landau_rear34", (15, 25, 8.5), (0, 2.5, 1.8))
show_livery("none")
shot("clean_side", (26, 0.5, 3.2), (0, 0.5, 2.0))
# interiors: roof hidden, looking down into the cabin
for (nm, b) in (("interior_classic", {"Seats": "Rolls", "Steering": "Chain", "Dash": "Classic", "Shifter": "Chain", "Dice": "On"}),
                ("interior_show", {"Seats": "Diamond", "Steering": "Wood", "Dash": "Wood", "Shifter": "Crystal", "Plaque": "Chain"}),
                ("interior_sport", {"Seats": "Buckets", "Steering": "Sport", "Dash": "Digital", "Shifter": "THandle"})):
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
