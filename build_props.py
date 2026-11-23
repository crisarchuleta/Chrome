# Neon Coast street + yard props from real references (Florida subdivision), in studs (~1.15 per foot):
# curbside mailbox (box ~4 studs up), cobra-head street light on a concrete pole (~34), HOA post-top light (~15),
# fire hydrant, sabal palm (~46, 1.3 trunk), royal palm (~68, smooth grey trunk + green crownshaft), queen palm
# (~34, slender), shrub, hedge, vinyl privacy fence panel, trash + recycling carts, stop sign, street-name sign,
# utility pedestal, curb storm drain. One GLB (StreetProps.glb); every prop sits at its own X offset, listed in
# props.json, with its meshes named <Prop>_<Material>.
import sys, json, os, math, random
sys.path.insert(0, r"C:\Users\Crisa\Documents\NeonCoast_Blender")
import importlib, nc_kit, nc_extra
importlib.reload(nc_kit)
importlib.reload(nc_extra)
from nc_extra import *
import bpy, bmesh
from mathutils import Vector, Matrix

reset()
random.seed(7)
nc_kit.COLORS.update({
    "Flag": (0.85, 0.12, 0.10), "Hydrant": (0.95, 0.80, 0.10), "Frond": (0.30, 0.52, 0.20), "Crownshaft": (0.42, 0.62, 0.30),
    "PalmTrunk": (0.55, 0.48, 0.38), "RoyalTrunk": (0.72, 0.72, 0.70), "Bush": (0.25, 0.48, 0.22), "Fence": (0.96, 0.96, 0.94), "Gate": (0.94, 0.94, 0.92),
    "BinBody": (0.22, 0.24, 0.26), "RecycleBody": (0.15, 0.35, 0.65), "SignRed": (0.80, 0.08, 0.08), "SignGreen": (0.05, 0.40, 0.20),
    "Lamp": (1.0, 0.95, 0.80), "Concrete": (0.70, 0.70, 0.68), "Grate": (0.15, 0.15, 0.15), "Utility": (0.25, 0.42, 0.30),
})


def beam(H, kind, p0, p1, w, h, up=(0, 0, 1)):
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


def cyl(H, kind, x, y, z0, z1, r0, r1=None, sides=8):
    r1 = r0 if r1 is None else r1
    v = []
    for z, r in ((z0, r0), (z1, r1)):
        for k in range(sides):
            a = 2 * math.pi * k / sides
            v.append((x + r * math.cos(a), y + r * math.sin(a), z))
    f = [tuple(range(sides - 1, -1, -1)), tuple(range(sides, 2 * sides))]
    for k in range(sides):
        j = (k + 1) % sides
        f.append((k, j, sides + j, sides + k))
    H.p(kind).solid(v, f)


def blob(H, kind, c, r, sub=1):
    m = Matrix.Translation(c) @ Matrix.Diagonal((r[0], r[1], r[2], 1))
    bmesh.ops.create_icosphere(H.p(kind).bm, subdivisions=sub, radius=1.0, matrix=m)


PROPS = []


def prop(fn):
    PROPS.append(fn)
    return fn


@prop
def Mailbox():
    H = House("Mailbox")
    H.p("Fence").box(-0.25, -0.25, 0, 0.25, 0.25, 4.6)
    H.p("Fence").box(-0.25, -1.4, 3.6, 0.25, 0.25, 4.0)
    H.p("Metal").box(-0.45, -1.9, 4.0, 0.45, 0.4, 4.9)
    beam(H, "Metal", (0, -1.9, 4.9), (0, 0.4, 4.9), 0.9, 0.5)
    H.p("Flag").box(0.46, -0.6, 4.6, 0.52, -0.2, 5.6)
    H.col(-0.45, -1.9, 0, 0.45, 0.4, 5.2, "prop")
    return H


@prop
def StreetLight():
    H = House("StreetLight")
    H.p("Concrete").box(-1.0, -1.0, 0, 1.0, 1.0, 0.6)
    cyl(H, "Concrete", 0, 0, 0.6, 33.0, 0.75, 0.42)
    beam(H, "Metal", (0, 0, 31.5), (0, -8.0, 32.6), 0.35, 0.35)
    H.p("Metal").box(-0.7, -10.2, 32.0, 0.7, -7.6, 32.9)
    H.p("Lamp").box(-0.55, -10.0, 31.85, 0.55, -7.8, 32.0)
    H.notes["light"] = [0.0, -8.9, 31.7]
    H.col(-0.8, -0.8, 0, 0.8, 0.8, 33.0, "pole")
    return H


@prop
def PostLight():
    H = House("PostLight")
    cyl(H, "Metal", 0, 0, 0, 1.2, 0.7, 0.5)
    cyl(H, "Metal", 0, 0, 1.2, 13.0, 0.25, 0.2)
    cyl(H, "Metal", 0, 0, 13.0, 13.5, 0.55, 0.55)
    blob(H, "Lamp", (0, 0, 14.6), (0.9, 0.9, 1.2))
    cyl(H, "Metal", 0, 0, 15.6, 16.2, 0.7, 0.15)
    H.notes["light"] = [0.0, 0.0, 14.6]
    H.col(-0.4, -0.4, 0, 0.4, 0.4, 15.0, "pole")
    return H


@prop
def Hydrant():
    H = House("Hydrant")
    cyl(H, "Hydrant", 0, 0, 0, 0.3, 0.75)
    cyl(H, "Hydrant", 0, 0, 0.3, 2.3, 0.5)
    cyl(H, "Hydrant", 0, 0, 2.3, 2.6, 0.6)
    blob(H, "Hydrant", (0, 0, 2.7), (0.55, 0.55, 0.4))
    for (dx, dy) in ((0.7, 0), (-0.7, 0), (0, -0.75)):
        beam(H, "Hydrant", (0, 0, 1.6), (dx, dy, 1.6), 0.4, 0.4)
        H.p("Metal").box(dx * 1.05 - 0.12, dy * 1.05 - 0.12, 1.45, dx * 1.05 + 0.12, dy * 1.05 + 0.12, 1.75)
    H.col(-0.6, -0.6, 0, 0.6, 0.6, 3.0, "prop")
    return H


def palm_trunk(H, kind, height, r0, r1, lean, rings=False):
    segs = 10
    pts = []
    for k in range(segs + 1):
        t = k / segs
        pts.append(Vector((lean[0] * t * t * height, lean[1] * t * t * height, t * height)))
    for k in range(segs):
        t = k / segs
        r = r0 + (r1 - r0) * t
        a, b = pts[k], pts[k + 1]
        cyl(H, kind, a.x, a.y, a.z, b.z, r, r0 + (r1 - r0) * (k + 1) / segs, sides=8)
        if rings:
            for j in range(3):
                z = a.z + (b.z - a.z) * (j + 0.5) / 3
                cyl(H, kind, a.x, a.y, z - 0.12, z + 0.12, r * 1.12, r * 1.12, sides=8)
    return pts[-1]


def feather_frond(H, top, yaw, length, droop, leaflet, kind="Frond", rise=0.35):
    """Arching feather frond: a spine that rises then droops, broad overlapping leaflets in a shallow V."""
    segs = 8
    prev = Vector(top)
    d = Vector((math.cos(yaw), math.sin(yaw), 0))
    side = Vector((-d.y, d.x, 0))
    for k in range(1, segs + 1):
        t = k / segs
        p = Vector(top) + d * (length * t) + Vector((0, 0, length * (rise * t - droop * t * t)))
        beam(H, kind, prev, p, 0.28, 0.12)
        mid = (prev + p) / 2
        along = (p - prev).normalized()
        l = leaflet * (1.0 - 0.6 * abs(t - 0.35))
        for s in (-1, 1):
            tip = mid + side * s * l + Vector((0, 0, -0.35 * l)) + along * 0.9
            beam(H, kind, mid, tip, 1.25, 0.06, up=tuple(along))
        prev = p


def fan_frond(H, top, yaw, length, kind="Frond", lift=0.12):
    """Costapalmate fan (sabal): a petiole, then a fan of stiff segments that folds down at the tips."""
    d = Vector((math.cos(yaw), math.sin(yaw), 0))
    side = Vector((-d.y, d.x, 0))
    stem = Vector(top) + d * (length * 0.42) + Vector((0, 0, length * lift))
    beam(H, kind, Vector(top), stem, 0.25, 0.15)
    for k in range(13):
        a = -1.25 + 2.5 * k / 12
        tip = stem + (d * math.cos(a) + side * math.sin(a)) * (length * 0.62) + Vector((0, 0, length * (lift * 0.6 - 0.22 * (abs(a) + 0.25))))
        beam(H, kind, stem, tip, 0.85, 0.07, up=tuple(d))


@prop
def SabalPalm():
    H = House("SabalPalm")
    top = palm_trunk(H, "PalmTrunk", 44.0, 0.75, 0.65, (0.03, 0.02), rings=True)
    for k in range(20):                                   # a round crown: fronds pointing up, out and down
        yaw = 2 * math.pi * k / 20 * 2.4 + random.uniform(-0.15, 0.15)
        tilt = top + Vector((0, 0, random.uniform(-1.0, 0.8)))
        fan_frond(H, tilt, yaw, random.uniform(9.0, 11.5), lift=random.choice((0.55, 0.3, 0.1, -0.15)))
    for k in range(6):                                    # old brown fronds hanging under the crown
        yaw = 2 * math.pi * k / 6 + 0.3
        d = Vector((math.cos(yaw), math.sin(yaw), 0))
        beam(H, "PalmTrunk", top + Vector((0, 0, -0.8)), top + d * 2.2 + Vector((0, 0, -6.5)), 0.9, 0.12)
    H.col(-0.7, -0.7, 0, 0.7, 0.7, 40.0, "trunk")
    return H


@prop
def RoyalPalm():
    H = House("RoyalPalm")
    top = palm_trunk(H, "RoyalTrunk", 58.0, 1.35, 0.95, (0.0, 0.0))
    cyl(H, "RoyalTrunk", top.x, top.y, 2.0, 4.5, 1.6, 1.35)          # the swollen base of a royal
    cyl(H, "Crownshaft", top.x, top.y, top.z, top.z + 8.0, 1.0, 0.8)
    crown = top + Vector((0, 0, 8.0))
    for k in range(15):
        yaw = 2 * math.pi * k / 15 * 2.4 + random.uniform(-0.1, 0.1)
        rise = random.choice((1.0, 0.7, 0.45, 0.25))       # young fronds stand up, old ones arch out and down
        feather_frond(H, crown, yaw, random.uniform(12.0, 14.0), random.uniform(0.75, 1.0) * (0.6 + rise * 0.5), 3.4, rise=rise)
    H.col(-1.3, -1.3, 0, 1.3, 1.3, 60.0, "trunk")
    return H


@prop
def QueenPalm():
    H = House("QueenPalm")
    top = palm_trunk(H, "RoyalTrunk", 30.0, 0.7, 0.55, (0.06, -0.03), rings=True)
    for k in range(13):
        yaw = 2 * math.pi * k / 13 * 2.4 + random.uniform(-0.2, 0.2)
        rise = random.choice((0.9, 0.55, 0.35))
        feather_frond(H, top, yaw, random.uniform(9.0, 11.0), random.uniform(1.0, 1.25) * (0.7 + rise * 0.4), 2.8, rise=rise)
    H.col(-0.7, -0.7, 0, 0.7, 0.7, 28.0, "trunk")
    return H


@prop
def Shrub():
    H = House("Shrub")
    for (c, r) in (((0, 0, 1.6), (2.0, 2.0, 1.7)), ((1.2, 0.6, 1.2), (1.4, 1.4, 1.2)), ((-1.1, -0.5, 1.1), (1.3, 1.3, 1.1))):
        blob(H, "Bush", c, r)
    H.col(-2.0, -2.0, 0, 2.0, 2.0, 3.0, "bush")
    return H


@prop
def Hedge():
    H = House("Hedge")
    for k in range(6):
        blob(H, "Bush", (-6.5 + k * 2.6, random.uniform(-0.2, 0.2), 2.0), (1.9, 1.6, 2.1))
    H.p("Bush").box(-7.5, -1.2, 0, 7.5, 1.2, 3.2)
    H.col(-8.0, -1.3, 0, 8.0, 1.3, 3.6, "hedge")
    return H


@prop
def FencePanel():
    # one post (at -X); panels go every 9.2 studs so the next panel's post closes this one (no doubled posts),
    # and a FencePost caps the end of a run
    H = House("FencePanel")
    for x in (-4.6,):
        H.p("Fence").box(x - 0.3, -0.3, 0, x + 0.3, 0.3, 7.6)
        H.p("Fence").box(x - 0.4, -0.4, 7.6, x + 0.4, 0.4, 7.9)
    H.p("Fence").box(-4.3, -0.1, 0.3, 4.3, 0.1, 7.0)
    for z in (0.3, 6.8):
        H.p("Fence").box(-4.3, -0.2, z, 4.3, 0.2, z + 0.4)
    for k in range(1, 8):
        x = -4.3 + 8.6 * k / 8
        H.p("Fence").box(x - 0.04, -0.12, 0.7, x + 0.04, 0.12, 6.8)
    H.col(-4.9, -0.3, 0, 4.3, 0.3, 7.6, "fence")
    return H


@prop
def FenceGate():
    """Walk gate for a privacy fence: a 4 ft leaf on a hinge post, matching FencePanel's style. It closes against
    the next panel's post (that's its latch post), so it spans 5.2 studs, -2.9..2.3. The leaf (Gate) is its own
    piece so the game can swing it (hinge note)."""
    H = House("FenceGate")
    for x in (-2.6,):
        H.p("Fence").box(x - 0.3, -0.3, 0, x + 0.3, 0.3, 7.6)
        H.p("Fence").box(x - 0.4, -0.4, 7.6, x + 0.4, 0.4, 7.9)
    a, b = -2.25, 2.2                          # leaf, with a small swing gap at both posts
    H.p("Gate").box(a, -0.1, 0.4, b, 0.1, 7.0)
    for z in (0.5, 3.6, 6.6):
        H.p("Gate").box(a, -0.22, z, b, -0.1, z + 0.35)
    H.p("Gate").solid([(a + 0.2, -0.22, 0.85), (a + 0.6, -0.22, 0.85), (b - 0.2, -0.22, 3.6), (b - 0.6, -0.22, 3.6),
                       (a + 0.2, -0.12, 0.85), (a + 0.6, -0.12, 0.85), (b - 0.2, -0.12, 3.6), (b - 0.6, -0.12, 3.6)],
                      [(0, 1, 2, 3), (7, 6, 5, 4), (0, 4, 5, 1), (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0)])      # diagonal brace
    for z in (1.4, 5.6):                                                                                   # strap hinges
        H.p("Metal").box(-2.3, -0.24, z, -1.3, -0.1, z + 0.18)
    H.p("Metal").box(1.7, -0.3, 3.9, 2.3, -0.1, 4.3)                                                       # latch
    H.col(-2.9, -0.3, 0, -2.3, 0.3, 7.6, "fence")
    H.col(a, -0.1, 0.4, b, 0.1, 7.0, "gate")
    H.notes["hinge"] = [-2.3, 0.0, 0.4]
    H.notes["leaf"] = {"min": [a, -0.22, 0.4], "max": [b, 0.1, 7.0]}
    return H


@prop
def FencePost():
    H = House("FencePost")
    H.p("Fence").box(-0.3, -0.3, 0, 0.3, 0.3, 7.6)
    H.p("Fence").box(-0.4, -0.4, 7.6, 0.4, 0.4, 7.9)
    H.col(-0.3, -0.3, 0, 0.3, 0.3, 7.6, "fence")
    return H


def cart(H, body):
    H.p(body).box(-1.2, -1.2, 0.5, 1.2, 1.2, 4.2)
    H.p(body).box(-1.35, -1.35, 4.2, 1.35, 1.45, 4.5)
    beam(H, "Metal", (-1.1, 1.45, 4.0), (1.1, 1.45, 4.0), 0.2, 0.2)
    for x in (-1.0, 1.0):
        beam(H, "Grate", (x, 1.1, 0.5), (x + (0.3 if x > 0 else -0.3), 1.1, 0.5), 1.0, 1.0)
    H.col(-1.35, -1.35, 0, 1.35, 1.45, 4.5, "bin")


@prop
def TrashBin():
    H = House("TrashBin")
    cart(H, "BinBody")
    return H


@prop
def RecycleBin():
    H = House("RecycleBin")
    cart(H, "RecycleBody")
    return H


@prop
def StopSign():
    H = House("StopSign")
    H.p("Metal").box(-0.12, -0.12, 0, 0.12, 0.12, 9.6)
    pts = [(1.25 * math.cos(math.pi / 8 + k * math.pi / 4), 8.0 + 1.25 * math.sin(math.pi / 8 + k * math.pi / 4)) for k in range(8)]
    prism_y(H, "SignRed", pts, -0.22, -0.12)
    H.notes["signFace"] = {"centre": [0.0, -0.23, 8.0], "size": 2.5}
    H.col(-0.15, -0.15, 0, 0.15, 0.15, 9.4, "pole")
    return H


@prop
def StreetSign():
    H = House("StreetSign")
    H.p("Metal").box(-0.12, -0.12, 0, 0.12, 0.12, 11.2)
    H.p("SignGreen").box(-2.6, -0.06, 10.0, 2.6, 0.06, 10.9)
    H.p("SignGreen").box(-0.06, -2.6, 10.95, 0.06, 2.6, 11.85)
    H.notes["signFace"] = {"blades": [[0.0, -0.07, 10.45], [0.07, 0.0, 11.4]]}
    H.col(-0.15, -0.15, 0, 0.15, 0.15, 11.0, "pole")
    return H


@prop
def UtilityBox():
    H = House("UtilityBox")
    H.p("Utility").box(-1.0, -0.8, 0, 1.0, 0.8, 3.4)
    beam(H, "Utility", (-1.05, 0, 3.4), (1.05, 0, 3.4), 1.0, 0.6)
    H.col(-1.0, -0.8, 0, 1.0, 0.8, 3.7, "prop")
    return H


@prop
def StormDrain():
    H = House("StormDrain")
    H.p("Concrete").box(-3.0, -0.4, -0.2, 3.0, 1.6, 0.9)
    H.p("Grate").box(-2.2, -0.42, 0.1, 2.2, -0.35, 0.5)
    H.p("Grate").box(-2.2, -2.2, -0.05, 2.2, -0.42, 0.02)
    H.col(-3.0, -0.4, -0.2, 3.0, 1.6, 0.9, "curb")
    return H


nc_kit.COLORS.update({"Wood": (0.42, 0.32, 0.22), "Insulator": (0.55, 0.62, 0.55), "Canvas": (0.15, 0.45, 0.60), "Cushion": (0.92, 0.90, 0.84),
                      "Backboard": (0.95, 0.95, 0.95), "Rim": (0.90, 0.35, 0.10), "Pot": (0.70, 0.40, 0.25), "Leaf": (0.20, 0.50, 0.22)})


@prop
def UtilityPole():
    """Florida neighbourhood power pole: treated wood, crossarm, three insulators, a transformer can."""
    H = House("UtilityPole")
    cyl(H, "Wood", 0, 0, 0, 42.0, 0.75, 0.5, sides=10)
    H.p("Wood").box(-5.5, -0.35, 38.0, 5.5, 0.35, 38.8)
    for x in (-4.8, 0.0, 4.8):
        z0 = 38.8 if x else 42.0
        cyl(H, "Insulator", x, 0, z0, z0 + 1.2, 0.3, 0.22)
    beam(H, "Wood", (-0.3, 0, 36.0), (-3.5, 0, 38.0), 0.25, 0.25)
    beam(H, "Wood", (0.3, 0, 36.0), (3.5, 0, 38.0), 0.25, 0.25)
    cyl(H, "Metal", 0.0, -1.5, 30.5, 34.5, 1.1, 1.1, sides=10)
    H.p("Metal").box(-0.25, -0.8, 32.0, 0.25, -0.4, 33.0)
    H.notes["wires"] = [[-4.8, 0.0, 40.0], [0.0, 0.0, 43.2], [4.8, 0.0, 40.0], [0.0, 0.0, 27.0]]
    H.col(-0.75, -0.75, 0, 0.75, 0.75, 42.0, "pole")
    return H


@prop
def BasketballHoop():
    H = House("BasketballHoop")
    H.p("Concrete").box(-1.2, -1.2, 0, 1.2, 1.2, 0.5)
    cyl(H, "Metal", 0, 0, 0.5, 11.0, 0.3, 0.3)
    beam(H, "Metal", (0, 0, 10.5), (0, -2.4, 11.6), 0.25, 0.25)
    H.p("Backboard").box(-2.4, -2.6, 10.2, 2.4, -2.4, 13.5)
    H.p("Rim").box(-0.9, -2.6, 10.6, 0.9, -2.45, 11.8)
    for (a, b) in ((-0.8, -0.8), (0.8, 0.8)):
        beam(H, "Rim", (a, -2.7, 11.0), (b, -4.2, 11.0), 0.08, 0.08)
    beam(H, "Rim", (-0.8, -4.2, 11.0), (0.8, -4.2, 11.0), 0.08, 0.08)
    beam(H, "Rim", (-0.8, -2.7, 11.0), (-0.8, -4.2, 11.0), 0.08, 0.08)
    beam(H, "Rim", (0.8, -2.7, 11.0), (0.8, -4.2, 11.0), 0.08, 0.08)
    H.col(-0.4, -0.4, 0, 0.4, 0.4, 11.0, "pole")
    return H


@prop
def PatioSet():
    H = House("PatioSet")
    cyl(H, "Metal", 0, 0, 0, 3.0, 0.15, 0.15)
    cyl(H, "Metal", 0, 0, 3.0, 3.2, 2.4, 2.4, sides=12)
    cyl(H, "Metal", 0, 0, 3.2, 9.0, 0.1, 0.1)
    cyl(H, "Canvas", 0, 0, 8.4, 9.6, 4.6, 0.3, sides=8)
    for k in range(4):
        a = k * math.pi / 2 + math.pi / 4
        x, y = math.cos(a) * 3.6, math.sin(a) * 3.6
        H.p("Metal").box(x - 0.9, y - 0.9, 1.8, x + 0.9, y + 0.9, 2.0)
        H.p("Cushion").box(x - 0.85, y - 0.85, 2.0, x + 0.85, y + 0.85, 2.35)
        bx, by = math.cos(a) * 4.4, math.sin(a) * 4.4
        beam(H, "Metal", (bx - math.sin(a) * 0.9, by + math.cos(a) * 0.9, 2.0), (bx + math.sin(a) * 0.9, by - math.cos(a) * 0.9, 2.0), 0.2, 0.2)
        H.p("Metal").box(bx - 0.15, by - 0.15, 2.0, bx + 0.15, by + 0.15, 4.0)
        for (dx, dy) in ((0.7, 0.7), (-0.7, 0.7), (0.7, -0.7), (-0.7, -0.7)):
            H.p("Metal").box(x + dx - 0.08, y + dy - 0.08, 0, x + dx + 0.08, y + dy + 0.08, 1.8)
    H.col(-2.4, -2.4, 0, 2.4, 2.4, 3.2, "table")
    return H


@prop
def Lounger():
    H = House("Lounger")
    H.p("Metal").box(-1.0, -3.0, 1.0, 1.0, 1.4, 1.2)
    H.p("Cushion").box(-0.95, -2.95, 1.2, 0.95, 1.4, 1.5)
    beam(H, "Metal", (0, 1.4, 1.3), (0, 3.4, 3.6), 2.0, 0.2)
    beam(H, "Cushion", (0, 1.5, 1.6), (0, 3.3, 3.7), 1.9, 0.3)
    for (x, y) in ((-0.9, -2.8), (0.9, -2.8), (-0.9, 1.2), (0.9, 1.2)):
        H.p("Metal").box(x - 0.08, y - 0.08, 0, x + 0.08, y + 0.08, 1.0)
    H.col(-1.0, -3.0, 0, 1.0, 3.4, 1.6, "furniture")
    return H


@prop
def Grill():
    H = House("Grill")
    H.p("Metal").box(-2.0, -1.0, 0.4, 2.0, 1.0, 3.2)
    H.p("Metal").box(-2.1, -1.1, 3.2, 2.1, 1.1, 3.5)
    beam(H, "Metal", (-1.8, 0.2, 3.5), (1.8, 0.2, 3.5), 2.0, 1.4, up=(0, 1, 0))
    H.p("Trim").box(-1.2, -1.25, 3.0, 1.2, -1.1, 3.15)
    H.p("Metal").box(2.0, -0.9, 3.0, 3.4, 0.9, 3.15)
    for x in (-1.8, 1.8):
        cyl(H, "Grate", x, 0, 0, 0.4, 0.35, 0.35)
    H.col(-2.0, -1.0, 0, 2.0, 1.0, 4.2, "furniture")
    return H


@prop
def RockingChair():
    H = House("RockingChair")
    H.p("Wood").box(-1.0, -1.0, 1.6, 1.0, 1.0, 1.8)
    H.p("Wood").box(-1.0, 0.8, 1.8, 1.0, 1.0, 4.6)
    for k in range(5):
        x = -0.8 + k * 0.4
        H.p("Wood").box(x - 0.08, 0.82, 1.8, x + 0.08, 0.98, 4.4)
    for x in (-1.0, 1.0):
        beam(H, "Wood", (x, -1.2, 0.2), (x, 0.0, 0.0), 0.15, 0.2)
        beam(H, "Wood", (x, 0.0, 0.0), (x, 1.3, 0.25), 0.15, 0.2)
        H.p("Wood").box(x - 0.08, -0.9, 0.1, x + 0.08, -0.7, 2.8)
        H.p("Wood").box(x - 0.08, 0.7, 0.1, x + 0.08, 0.9, 1.6)
        H.p("Wood").box(x - 0.15, -1.0, 2.6, x + 0.15, 0.9, 2.8)
    H.col(-1.0, -1.2, 0, 1.0, 1.3, 4.6, "furniture")
    return H


@prop
def Planter():
    H = House("Planter")
    cyl(H, "Pot", 0, 0, 0, 2.2, 0.9, 1.3, sides=10)
    for k in range(7):
        a = k * 2 * math.pi / 7
        beam(H, "Leaf", (0, 0, 2.0), (math.cos(a) * 1.8, math.sin(a) * 1.8, 4.2 + (k % 2) * 0.8), 0.5, 0.08)
    blob(H, "Leaf", (0, 0, 2.6), (0.9, 0.9, 0.8))
    H.col(-1.3, -1.3, 0, 1.3, 1.3, 2.2, "pot")
    return H


@prop
def PathLight():
    H = House("PathLight")
    cyl(H, "Metal", 0, 0, 0, 1.8, 0.12, 0.12)
    cyl(H, "Lamp", 0, 0, 1.8, 2.2, 0.35, 0.35)
    cyl(H, "Metal", 0, 0, 2.2, 2.45, 0.55, 0.1)
    H.notes["light"] = [0.0, 0.0, 2.0]
    return H


@prop
def PoolPump():
    H = House("PoolPump")
    H.p("Concrete").box(-2.5, -1.5, 0, 2.5, 1.5, 0.3)
    cyl(H, "Metal", -1.0, 0, 0.3, 2.0, 0.8, 0.8)
    H.p("Metal").box(0.2, -0.7, 0.3, 2.0, 0.7, 1.6)
    for x in (-1.0, 1.1):
        cyl(H, "Fence", x, 0, 1.6 if x > 0 else 2.0, 3.6, 0.2, 0.2)
    H.col(-2.5, -1.5, 0, 2.5, 1.5, 2.0, "equipment")
    return H


nc_kit.COLORS.update({"Court": (0.25, 0.45, 0.35), "Paint": (0.96, 0.96, 0.94), "KeyPaint": (0.20, 0.35, 0.60), "Net": (0.97, 0.97, 0.97)})


@prop
def HalfCourt():
    """Backyard half court built to real (high-school) dimensions at ~1.15 studs per foot. Baseline on y = 0,
    the court runs toward -Y, the hoop's pole stands behind the baseline. The rim/net here are the looks; the
    game builds an exact physics rim (Basketball script) at the rimCenter note."""
    H = House("HalfCourt")
    FT = 1.15
    hw, depth = 25 * FT, 30 * FT                       # 50 x 30 ft slab
    H.p("Court").box(-hw, -depth, 0.0, hw, 1.5, 0.12)
    H.col(-hw, -depth, 0.0, hw, 1.5, 0.12, "court")
    lw, lz0, lz1 = 2 / 12 * FT, 0.12, 0.15            # 2 in lines
    def line(x0, y0, x1, y1, kind="Paint"):
        H.p(kind).box(min(x0, x1) - lw / 2, min(y0, y1) - lw / 2, lz0, max(x0, x1) + lw / 2, max(y0, y1) + lw / 2, lz1)
    board_y = -4 * FT                                  # backboard face 4 ft in from the baseline
    rim_y = board_y - 15 / 12 * FT                     # rim centre 15 in off the board
    ft_y = board_y - 15 * FT                           # free-throw line 15 ft from the board
    key = 6 * FT                                       # 12 ft key
    H.p("KeyPaint").box(-key, ft_y, lz0 - 0.01, key, 0.0, lz1 - 0.01)
    line(-hw, 0.0, hw, 0.0)                            # baseline
    line(-hw, 0.0, -hw, -depth)
    line(hw, 0.0, hw, -depth)
    line(-key, 0.0, -key, ft_y)
    line(key, 0.0, key, ft_y)
    line(-key, ft_y, key, ft_y)
    r_ft = 6 * FT                                      # free-throw circle, top half
    for k in range(16):
        a0, a1 = math.pi * k / 16, math.pi * (k + 1) / 16
        p0 = (math.cos(a0) * r_ft, ft_y - math.sin(a0) * r_ft, lz0)
        p1 = (math.cos(a1) * r_ft, ft_y - math.sin(a1) * r_ft, lz0)
        beam(H, "Paint", (p0[0], p0[1], (lz0 + lz1) / 2), (p1[0], p1[1], (lz0 + lz1) / 2), lw, lz1 - lz0)
    r3 = 19.75 * FT                                    # three-point arc from the rim centre
    corner_x = r3 * 0.96
    a_start = math.asin(min(1.0, corner_x / r3))
    yc = rim_y - math.cos(a_start) * r3
    line(-corner_x, 0.0, -corner_x, yc)
    line(corner_x, 0.0, corner_x, yc)
    n = 28
    for k in range(n):
        a0 = -a_start + 2 * a_start * k / n
        a1 = -a_start + 2 * a_start * (k + 1) / n
        p0 = (math.sin(a0) * r3, rim_y - math.cos(a0) * r3)
        p1 = (math.sin(a1) * r3, rim_y - math.cos(a1) * r3)
        beam(H, "Paint", (p0[0], p0[1], (lz0 + lz1) / 2), (p1[0], p1[1], (lz0 + lz1) / 2), lw, lz1 - lz0)
    # pole behind the baseline, arm out to the board, 72 x 42 in board, 18 in rim at 10 ft, net
    rim_z = 10 * FT
    H.p("Concrete").box(-1.2, 0.6, 0.0, 1.2, 3.0, 0.4)
    cyl(H, "Metal", 0, 1.8, 0.4, rim_z + 2.4, 0.42, 0.36)
    beam(H, "Metal", (0, 1.8, rim_z + 1.2), (0, board_y + 0.3, rim_z + 1.2), 0.35, 0.35)
    beam(H, "Metal", (0, 1.8, rim_z - 1.0), (0, board_y + 0.3, rim_z + 0.6), 0.25, 0.25)
    bw, bh = 72 / 12 * FT, 42 / 12 * FT
    b_bottom = rim_z - 6 / 12 * FT
    H.p("Backboard").box(-bw / 2, board_y, b_bottom, bw / 2, board_y + 0.15, b_bottom + bh)
    for (x0, z0, x1, z1) in ((-bw / 2, b_bottom, bw / 2, b_bottom + 0.12), (-bw / 2, b_bottom + bh - 0.12, bw / 2, b_bottom + bh),
                             (-bw / 2, b_bottom, -bw / 2 + 0.12, b_bottom + bh), (bw / 2 - 0.12, b_bottom, bw / 2, b_bottom + bh)):
        H.p("Rim").box(x0, board_y - 0.02, z0, x1, board_y, z1)
    sq_w, sq_h = 24 / 12 * FT, 18 / 12 * FT            # shooter's square
    for (x0, z0, x1, z1) in ((-sq_w / 2, b_bottom + 0.6, sq_w / 2, b_bottom + 0.7), (-sq_w / 2, b_bottom + 0.6 + sq_h - 0.1, sq_w / 2, b_bottom + 0.6 + sq_h),
                             (-sq_w / 2, b_bottom + 0.6, -sq_w / 2 + 0.1, b_bottom + 0.6 + sq_h), (sq_w / 2 - 0.1, b_bottom + 0.6, sq_w / 2, b_bottom + 0.6 + sq_h)):
        H.p("Rim").box(x0, board_y - 0.03, z0, x1, board_y, z1)
    r_rim = 9 / 12 * FT
    H.p("Rim").box(-0.25, board_y - 0.5, rim_z - 0.1, 0.25, board_y, rim_z + 0.05)      # bracket
    segs = 16
    for k in range(segs):
        a0, a1 = 2 * math.pi * k / segs, 2 * math.pi * (k + 1) / segs
        p0 = (math.cos(a0) * (r_rim + 0.05), rim_y + math.sin(a0) * (r_rim + 0.05), rim_z)
        p1 = (math.cos(a1) * (r_rim + 0.05), rim_y + math.sin(a1) * (r_rim + 0.05), rim_z)
        beam(H, "Rim", p0, p1, 0.1, 0.1)
        q0 = (math.cos(a0) * r_rim * 0.6, rim_y + math.sin(a0) * r_rim * 0.6, rim_z - 1.7)
        beam(H, "Net", p0, q0, 0.05, 0.05)
        q1 = (math.cos(a1) * r_rim * 0.6, rim_y + math.sin(a1) * r_rim * 0.6, rim_z - 1.7)
        beam(H, "Net", p0, q1, 0.05, 0.05)
    centre = (0.0, -depth / 2 + 0.75, 0.12)
    rel = lambda p: [p[0] - centre[0], p[1] - centre[1], p[2] - centre[2]]
    H.notes["court"] = {"centre": list(centre), "rimRel": rel((0.0, rim_y, rim_z)), "rimRadius": r_rim, "threeRadius": r3,
                        "ballSpawnRel": rel((0.0, ft_y, 1.0)), "boardRel": rel((0.0, board_y + 0.075, b_bottom + bh / 2)),
                        "boardSize": [bw, bh, 0.15], "size": [hw * 2, depth + 1.5]}   # board centre; size = Blender x, z, y
    H.col(-0.4, 1.4, 0, 0.4, 2.2, rim_z + 2.4, "pole")
    return H


# build, spread out along X, export one GLB
meta = {}
x = 0.0
for ob in list(bpy.context.scene.objects):
    ob.select_set(False)
for fn in PROPS:
    H = fn()
    objs, tris = H.build()
    for ob in objs:
        ob.location.x += x
        ob["style"] = "StreetProps"
        ob["prop"] = H.style
        ob.select_set(True)
    meta[H.style] = {"offsetX": x, "pieces": sorted(tris.keys()), "triangles": tris, "colliders": H.colliders, "notes": H.notes}
    x += 30.0
path = os.path.join(OUT, "StreetProps.glb")
bpy.ops.export_scene.gltf(filepath=path, export_format="GLB", use_selection=True, export_apply=True, export_yup=True)
with open(os.path.join(OUT, "props.json"), "w") as f:
    json.dump(meta, f)
scene, cam = setup_render()
render_views(scene, cam, ["StreetProps"], {
    "lineup": ((x * 0.45, -200, 45), (x * 0.45, 0, 15)),
    "palms": ((150, -120, 34), (150, 0, 34)),
    "small": ((45, -48, 11), (45, 0, 4)), "court": ((x - 30 - 40, -70, 40), (x - 30, -15, 4)),
}, "Props")
print("NEONCOAST_DONE", json.dumps({k: sum(v["triangles"].values()) for k, v in meta.items()}))
