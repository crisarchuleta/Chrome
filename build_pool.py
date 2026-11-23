# Neon Coast backyard pool + unicorn floaty, Blender headless:
#   blender --background --factory-startup --python build_pool.py
# Out: Pool.glb (props lined up along X: BackyardPool at 0, UnicornFloaty at 80), pool.json (colliders, water box,
# diving board hinge, lights, floaty sizes), previews/Pool_*.png.
#
# BackyardPool, from real residential diving-pool references, at 1.15 studs per foot:
#   16 x 36 ft (18.4 x 41.4 studs), shallow end 3'6" with entry steps and a handrail, a slope down to an 8'6"
#   diving well, a stainless ladder, an 8 ft springboard on a stand at the deep end (tip 3.5 ft out over the water,
#   ~2 ft above it), waterline tile, bullnose coping, a paver deck with a soldier border, two underwater lights,
#   skimmer, returns, main drains, depth markers on the deck.
# Origin: middle of the deck's house-side edge, deck top at z = 0.35, the pool runs along X with the deep end at +X,
# away from the house is +Y. The basin goes below ground (the game cuts the ground / terrain there).
import sys, json, os, math
sys.path.insert(0, r"C:\Users\Crisa\Documents\NeonCoast_Blender")
import importlib, nc_kit, nc_extra
importlib.reload(nc_kit)
importlib.reload(nc_extra)
from nc_extra import *
import bpy
from mathutils import Vector, Matrix

reset()
nc_kit.COLORS.update({
    "Pavers": (0.84, 0.76, 0.63), "PaverBorder": (0.70, 0.60, 0.48), "Coping": (0.90, 0.86, 0.78),
    "PoolPlaster": (0.80, 0.92, 0.97), "PoolTile": (0.12, 0.42, 0.62), "Water": (0.25, 0.65, 0.85),
    "Rail": (0.86, 0.87, 0.89), "Stand": (0.86, 0.83, 0.75), "Board": (0.93, 0.95, 0.97), "BoardTread": (0.80, 0.72, 0.55),
    "Lamp": (1.0, 0.95, 0.80), "Grate": (0.15, 0.16, 0.18), "Plaque": (0.96, 0.96, 0.95), "Marker": (0.10, 0.20, 0.45),
    "Metal": (0.18, 0.18, 0.20), "Rock": (0.62, 0.58, 0.52),
    # unicorn floaty
    "Vinyl": (0.97, 0.96, 0.98), "FloatPink": (1.0, 0.70, 0.82), "Eye": (0.06, 0.05, 0.08), "Horn": (1.0, 0.80, 0.35),
    "ManePink": (1.0, 0.52, 0.74), "ManeOrange": (1.0, 0.68, 0.38), "ManeYellow": (1.0, 0.90, 0.42),
    "ManeMint": (0.52, 0.90, 0.70), "ManeSky": (0.48, 0.74, 1.0), "ManeLavender": (0.72, 0.58, 0.96),
})
FT = 1.15


# ------------------------------------------------------------------ shape helpers
def tube(H, kind, pts, radii, sides=10, caps=True):
    """A round tube along a polyline (rails, the unicorn's neck). radii: one number or one per point."""
    P = [Vector(p) for p in pts]
    n = len(P)
    if isinstance(radii, (int, float)):
        radii = [radii] * n
    verts, faces = [], []
    prev_x = None
    for i in range(n):
        if i == 0:
            t = P[1] - P[0]
        elif i == n - 1:
            t = P[-1] - P[-2]
        else:
            t = (P[i + 1] - P[i]).normalized() + (P[i] - P[i - 1]).normalized()
        t.normalize()
        if prev_x is None:
            ref = Vector((0, 0, 1)) if abs(t.z) < 0.9 else Vector((1, 0, 0))
            x = ref.cross(t).normalized()
        else:
            x = (prev_x - t * prev_x.dot(t)).normalized()
        y = t.cross(x)
        prev_x = x
        for k in range(sides):
            a = 2 * math.pi * k / sides
            verts.append(tuple(P[i] + (x * math.cos(a) + y * math.sin(a)) * radii[i]))
    for i in range(n - 1):
        for k in range(sides):
            j = (k + 1) % sides
            faces.append((i * sides + k, i * sides + j, (i + 1) * sides + j, (i + 1) * sides + k))
    if caps:
        faces.append(tuple(range(sides - 1, -1, -1)))
        faces.append(tuple(range((n - 1) * sides, n * sides)))
    H.p(kind).solid(verts, faces)


def bend(a, b, c, r, segs=4):
    """Points rounding the corner at b between a and c with radius r (for rails)."""
    a, b, c = Vector(a), Vector(b), Vector(c)
    d1, d2 = (a - b).normalized(), (c - b).normalized()
    p1, p2 = b + d1 * r, b + d2 * r
    out = []
    for k in range(segs + 1):
        t = k / segs
        out.append(tuple((1 - t) ** 2 * p1 + 2 * (1 - t) * t * b + t * t * p2))   # quadratic Bezier
    return out


def ellipsoid(H, kind, c, rx, ry, rz, nu=14, nv=9, rot=None):
    c = Vector(c)
    rot = rot or Matrix.Identity(3)
    verts, faces = [], []
    for j in range(1, nv):
        phi = math.pi * j / nv
        for i in range(nu):
            th = 2 * math.pi * i / nu
            verts.append(tuple(c + rot @ Vector((rx * math.sin(phi) * math.cos(th), ry * math.sin(phi) * math.sin(th), rz * math.cos(phi)))))
    rings = nv - 1
    top = len(verts)
    verts.append(tuple(c + rot @ Vector((0, 0, rz))))
    bot = len(verts)
    verts.append(tuple(c + rot @ Vector((0, 0, -rz))))
    for j in range(rings - 1):
        for i in range(nu):
            k = (i + 1) % nu
            faces.append((j * nu + i, j * nu + k, (j + 1) * nu + k, (j + 1) * nu + i))
    for i in range(nu):
        k = (i + 1) % nu
        faces.append((top, k, i))
        faces.append((bot, (rings - 1) * nu + i, (rings - 1) * nu + k))
    H.p(kind).solid(verts, faces)


def torus(H, kind, c, R, r, nu=36, nv=14):
    verts, faces = [], []
    for i in range(nu):
        th = 2 * math.pi * i / nu
        for j in range(nv):
            ph = 2 * math.pi * j / nv
            verts.append((c[0] + (R + r * math.cos(ph)) * math.cos(th), c[1] + (R + r * math.cos(ph)) * math.sin(th), c[2] + r * math.sin(ph)))
    for i in range(nu):
        i2 = (i + 1) % nu
        for j in range(nv):
            j2 = (j + 1) % nv
            faces.append((i * nv + j, i2 * nv + j, i2 * nv + j2, i * nv + j2))
    H.p(kind).solid(verts, faces)


def disc(H, kind, c, normal, r, t, sides=16):
    """A flat round disc (lights, skimmer lid, drain) centred at c, facing normal, thickness t."""
    nrm = Vector(normal).normalized()
    ref = Vector((0, 0, 1)) if abs(nrm.z) < 0.9 else Vector((1, 0, 0))
    x = ref.cross(nrm).normalized()
    y = nrm.cross(x)
    c = Vector(c)
    verts = []
    for s in (0.0, t):
        for k in range(sides):
            a = 2 * math.pi * k / sides
            verts.append(tuple(c + nrm * s + (x * math.cos(a) + y * math.sin(a)) * r))
    faces = [tuple(range(sides - 1, -1, -1)), tuple(range(sides, 2 * sides))]
    for k in range(sides):
        j = (k + 1) % sides
        faces.append((k, j, sides + j, sides + k))
    H.p(kind).solid(verts, faces)


def horn(H, kind, base, tip, r0, sides=8, rings=9, twist=2.2):
    """Twisted unicorn horn: a star-section cone that turns as it rises, so the ridges spiral."""
    base, tip = Vector(base), Vector(tip)
    ax = tip - base
    L = ax.length
    t = ax.normalized()
    ref = Vector((1, 0, 0)) if abs(t.x) < 0.9 else Vector((0, 1, 0))
    x = ref.cross(t).normalized()
    y = t.cross(x)
    verts, faces = [], []
    for k in range(rings):
        s = k / rings
        r = r0 * (1 - s)
        for i in range(sides):
            a = 2 * math.pi * i / sides + twist * 2 * math.pi * s
            rr = r * (1.0 if i % 2 == 0 else 0.78)
            verts.append(tuple(base + t * L * s + (x * math.cos(a) + y * math.sin(a)) * rr))
    tipi = len(verts)
    verts.append(tuple(tip))
    faces.append(tuple(range(sides - 1, -1, -1)))
    for k in range(rings - 1):
        for i in range(sides):
            j = (i + 1) % sides
            faces.append((k * sides + i, k * sides + j, (k + 1) * sides + j, (k + 1) * sides + i))
    last = (rings - 1) * sides
    for i in range(sides):
        faces.append((last + i, last + (i + 1) % sides, tipi))
    H.p(kind).solid(verts, faces)


# 7-segment depth numbers for the deck markers
SEG = {"a": (0, 1, 1, 1), "b": (1, 0.5, 1, 1), "c": (1, 0, 1, 0.5), "d": (0, 0, 1, 0), "e": (0, 0, 0, 0.5), "f": (0, 0.5, 0, 1), "g": (0, 0.5, 1, 0.5)}
DIG = {"0": "abcdef", "1": "bc", "2": "abdeg", "3": "abcdg", "4": "bcfg", "5": "acdfg", "6": "acdefg", "7": "abc", "8": "abcdefg", "9": "abcdfg"}


def depth_marker(H, cx, cy, z, text, up=1):
    """A white tile plaque with dark depth numbers (e.g. 3'6"), lying on the deck, readable facing +Y*up."""
    w, h, t, gap = 0.62, 1.0, 0.13, 0.2
    items = [(ch, w if ch.isdigit() else (0.16 if ch == "'" else 0.36)) for ch in text]
    total = sum(iw for _, iw in items) + gap * (len(items) - 1)
    pw, ph = total + 0.7, h + 0.6
    H.p("Plaque").box(cx - pw / 2, cy - ph / 2, z, cx + pw / 2, cy + ph / 2, z + 0.03)
    zz = z + 0.03

    def seg(u0, v0, u1, v1):
        if up > 0:
            H.p("Marker").box(cx + u0, cy + v0, zz, cx + u1, cy + v1, zz + 0.015)
        else:
            H.p("Marker").box(cx - u1, cy - v1, zz, cx - u0, cy - v0, zz + 0.015)

    u = -total / 2
    for ch, iw in items:
        if ch.isdigit():
            for s in DIG[ch]:
                a0, b0, a1, b1 = SEG[s]
                x0, x1 = u + a0 * (w - t), u + a1 * (w - t) + t
                y0, y1 = -h / 2 + b0 * (h - t), -h / 2 + b1 * (h - t) + t
                seg(x0, y0, x1, y1)
        else:
            seg(u + 0.02, h / 2 - 0.34, u + 0.14, h / 2)
            if ch == '"':
                seg(u + 0.22, h / 2 - 0.34, u + 0.34, h / 2)
        u += iw + gap


# ------------------------------------------------------------------ the pool
def backyard_pool():
    """Estate (mansion) pool, from luxury residential references, at 1.15 studs per foot:
    24 x 60 ft (27.6 x 69 studs). Sun shelf (baja ledge, 1 ft deep) in the shallow corner with steps down, a raised
    spillover spa (8 x 8 ft, 3 ft deep with a bench) set into the house-side wall, 3'6" shallow end sloping to a
    9 ft diving well, springboard at the deep end, two stainless ladders, a rock waterfall on the far side,
    waterline tile, bullnose coping, a big paver deck with a soldier border, four underwater lights, skimmers,
    returns, main drains, depth markers. Origin: middle of the deck's house-side edge; pool along X, deep end +X."""
    H = House("BackyardPool")
    DZ = 0.35                                   # deck top
    WZ = -0.2                                   # pool water surface
    px0, px1 = -30 * FT, 30 * FT                # 60 ft
    py0, py1 = 8.0, 8.0 + 24 * FT               # 24 ft
    yc = (py0 + py1) / 2
    PROF = [(px0, WZ - 3.5 * FT), (-8.0, WZ - 4.0 * FT), (4.0, WZ - 9.0 * FT), (22.0, WZ - 9.0 * FT), (px1, WZ - 8.0 * FT)]

    def zf(x):
        for (xa, za), (xb, zb) in zip(PROF, PROF[1:]):
            if xa <= x <= xb:
                return za + (zb - za) * (x - xa) / (xb - xa)
        return PROF[-1][1]

    W = 0.6
    zmin = min(z for _, z in PROF)
    # ---- deck, border, coping
    dx0, dy0, dx1, dy1 = -44.0, 0.0, 48.0, 48.0
    B = 0.8
    H.slab("Pavers", dx0 + B, dy0 + B, dx1 - B, dy1 - B, 0.0, DZ, tag="deck", holes=[(px0 - 1.0, py0 - 1.0, px1 + 1.0, py1 + 1.0)])
    for (a0, b0, a1, b1) in ((dx0, dy0, dx1, dy0 + B), (dx0, dy1 - B, dx1, dy1), (dx0, dy0 + B, dx0 + B, dy1 - B), (dx1 - B, dy0 + B, dx1, dy1 - B)):
        H.p("PaverBorder").box(a0, b0, 0.0, a1, b1, DZ)
        H.col(a0, b0, 0.0, a1, b1, DZ, "deck")
    # spa footprint (set into the house-side wall): interior and walls
    sx0, sx1, sy0, sy1 = -15.8, -6.6, py0, py0 + 8 * FT
    SW = 0.6
    cz1 = DZ + 0.07
    copes = [(px0 - 1.0, py1 - 0.15, px1 + 1.0, py1 + 1.0),
             (px0 - 1.0, py0 + 0.15, px0 + 0.15, py1 - 0.15), (px1 - 0.15, py0 + 0.15, px1 + 1.0, py1 - 0.15)]
    for (a0, a1) in ((px0 - 1.0, sx0 - SW), (sx1 + SW, px1 + 1.0)):            # house side, broken by the spa
        copes.append((a0, py0 - 1.0, a1, py0 + 0.15))
    for (a0, b0, a1, b1) in copes:
        H.p("Coping").box(a0, b0, 0.0, a1, b1, cz1)
        H.col(a0, b0, 0.0, a1, b1, cz1, "coping")
    # ---- shell: floor on the profile, long walls cut to it, end walls, plaster; waterline tile
    floor_pts = [(x, z) for x, z in PROF] + [(x, z - 0.5) for x, z in reversed(PROF)]
    prism_y(H, "PoolPlaster", floor_pts, py0, py1)
    wall_pts = [(px0 - W, -0.75), (px1 + W, -0.75), (px1 + W, PROF[-1][1] - 0.5)] + [(x, z - 0.5) for x, z in reversed(PROF)] + [(px0 - W, PROF[0][1] - 0.5)]
    prism_y(H, "PoolPlaster", wall_pts, py0 - W, py0)
    prism_y(H, "PoolPlaster", wall_pts, py1, py1 + W)
    H.p("PoolPlaster").box(px0 - W, py0, PROF[0][1] - 0.5, px0, py1, -0.75)
    H.p("PoolPlaster").box(px1, py0, PROF[-1][1] - 0.5, px1 + W, py1, -0.75)
    for (a0, b0, a1, b1) in ((px0, py0 - 0.2, sx0 - SW, py0 + 0.03), (sx1 + SW, py0 - 0.2, px1, py0 + 0.03), (px0, py1 - 0.03, px1, py1 + 0.2),
                             (px0 - 0.2, py0 + 0.03, px0 + 0.03, py1 - 0.03), (px1 - 0.03, py0 + 0.03, px1 + 0.2, py1 - 0.03)):
        H.p("PoolTile").box(a0, b0, -0.75, a1, b1, 0.0)
    H.col(px0 - W, py0 - W, zmin - 1.0, px1 + W, py0, 0.0, "poolwall")
    H.col(px0 - W, py1, zmin - 1.0, px1 + W, py1 + W, 0.0, "poolwall")
    H.col(px0 - W, py0, zmin - 1.0, px0, py1, 0.0, "poolwall")
    H.col(px1, py0, zmin - 1.0, px1 + W, py1, 0.0, "poolwall")
    H.notes["slopes"] = [{"p0": [xa, za], "p1": [xb, zb], "y0": py0, "y1": py1} for (xa, za), (xb, zb) in zip(PROF, PROF[1:])]
    H.notes["water"] = {"min": [px0, py0, zmin], "max": [px1, py1, WZ]}
    # ---- sun shelf (1 ft of water: in-pool loungers go here), a step along its front, steps down its side
    shx1, shy1 = -22.0, py0 + 12.0
    shelf = WZ - 1.0 * FT
    H.p("PoolPlaster").box(px0, py0, zf(shx1) - 0.1, shx1, shy1, shelf)
    H.col(px0, py0, zf(shx1) - 0.1, shx1, shy1, shelf, "shelf")
    H.notes["shelf"] = {"min": [px0, py0], "max": [shx1, shy1], "top": shelf}
    st1 = WZ - 2.0 * FT
    H.p("PoolPlaster").box(px0, shy1, zf(shx1) - 0.1, shx1, shy1 + 1.15, st1)                 # bench step along the front
    H.col(px0, shy1, zf(shx1) - 0.1, shx1, shy1 + 1.15, st1, "poolstep")
    for k in range(2):                                                                          # steps down the side
        a, b = shx1 + 1.15 * k, shx1 + 1.15 * (k + 1)
        top = WZ - (2.0 + k) * FT
        H.p("PoolPlaster").box(a, py0, zf(b) - 0.1, b, shy1, top)
        H.col(a, py0, zf(b) - 0.1, b, shy1, top, "poolstep")
        H.p("PoolTile").box(b - 0.3, py0, top, b, shy1, top + 0.03)
    H.p("PoolTile").box(shx1 - 0.3, py0, shelf, shx1, shy1, shelf + 0.03)                      # nosing: shelf edges
    H.p("PoolTile").box(px0, shy1 - 0.3, shelf, shx1, shy1, shelf + 0.03)
    H.p("PoolTile").box(px0, shy1 + 1.15 - 0.3, st1, shx1, shy1 + 1.15, st1 + 0.03)
    hx = shx1 + 0.6                                                                             # handrail onto the first step
    a, b, c, d = (hx, py0 - 1.6, DZ), (hx, py0 - 1.6, DZ + 3.0), (hx, py0 + 1.7, DZ + 2.2), (hx, py0 + 1.7, WZ - 2.0 * FT)
    tube(H, "Rail", [a] + bend(a, b, c, 0.8) + bend(b, c, d, 0.8) + [d], 0.16, sides=10)
    # ---- raised spillover spa: walls up from the pool floor to a cap 8 in over the deck, a sheet of water over
    # the notch into the pool, bench round three sides, jets, a light
    SZ = WZ + 0.9                               # spa water, a foot over the pool
    cap = DZ + 0.7
    zfs = min(zf(sx0), zf(sx1)) - 0.5
    for (a0, b0, a1, b1, z0) in ((sx0 - SW, sy0, sx0, sy1 + SW, zfs), (sx1, sy0, sx1 + SW, sy1 + SW, zfs),
                                 (sx0, sy1, sx1, sy1 + SW, zfs), (sx0 - SW, py0 - 1.0, sx1 + SW, sy0, -0.75)):
        H.p("PoolPlaster").box(a0, b0, z0, a1, b1, cap - 0.2)
        H.p("Coping").box(a0 - 0.1, b0 - (0.1 if b0 < sy0 else 0.0), cap - 0.2, a1 + 0.1, b1 + 0.1, cap)
        H.col(a0, b0, z0, a1, b1, cap, "spa")
    nx0, nx1 = -12.6, -9.8                      # the spillover notch and its sheet of water
    H.p("Water").box(nx0, sy1 + SW + 0.02, WZ, nx1, sy1 + SW + 0.08, cap - 0.25)
    sfz = SZ - 3.2 * FT
    H.p("PoolPlaster").box(sx0, sy0, sfz - 0.5, sx1, sy1, sfz)
    H.col(sx0, sy0, sfz - 0.5, sx1, sy1, sfz, "spa")
    bench = SZ - 1.5 * FT
    for (a0, b0, a1, b1) in ((sx0, sy0, sx0 + 1.4, sy1), (sx1 - 1.4, sy0, sx1, sy1), (sx0 + 1.4, sy1 - 1.4, sx1 - 1.4, sy1)):
        H.p("PoolTile").box(a0, b0, sfz, a1, b1, bench)
        H.col(a0, b0, sfz, a1, b1, bench, "spabench")
    for (jx, jy, jn) in ((sx0, sy0 + 3.0, (1, 0, 0)), (sx0, sy0 + 6.5, (1, 0, 0)), (sx1, sy0 + 3.0, (-1, 0, 0)), (sx1, sy0 + 6.5, (-1, 0, 0)),
                         (sx0 + 3.2, sy1, (0, -1, 0)), (sx1 - 3.2, sy1, (0, -1, 0))):
        disc(H, "Grate", (jx, jy, bench + 0.5), jn, 0.14, 0.05)
    disc(H, "Lamp", ((sx0 + sx1) / 2, sy0 + 0.02, sfz + 0.9), (0, 1, 0), 0.35, 0.04)
    H.p("Water").box(sx0 + 0.03, sy0 + 0.03, SZ - 0.06, sx1 - 0.03, sy1 - 0.03, SZ)
    H.notes["spa"] = {"min": [sx0, sy0, sfz], "max": [sx1, sy1, SZ]}
    # ---- rock waterfall on the far deck, a lip stone over the water, a sheet falling into the pool
    import random as _r
    rng = _r.Random(7)
    wfx0, wfx1 = 7.0, 19.0
    rocks = [(wfx0, py1 + 1.0, 0.0, wfx1, py1 + 6.5, 1.6), (wfx0 + 1.0, py1 + 1.2, 1.6, wfx1 - 1.0, py1 + 5.6, 3.0),
             (wfx0 + 2.6, py1 + 1.3, 3.0, wfx1 - 2.8, py1 + 4.6, 3.6), (wfx0 - 1.6, py1 + 2.0, 0.0, wfx0 + 0.4, py1 + 5.0, 2.2),
             (wfx1 - 0.4, py1 + 2.2, 0.0, wfx1 + 1.4, py1 + 5.4, 1.8)]
    for (a0, b0, z0, a1, b1, z1) in rocks:                     # stacked boulders, each a little skewed
        cxr, cyr = (a0 + a1) / 2, (b0 + b1) / 2
        vs = []
        for (u, v, w_) in ((a0, b0, z0), (a1, b0, z0), (a1, b1, z0), (a0, b1, z0), (a0, b0, z1), (a1, b0, z1), (a1, b1, z1), (a0, b1, z1)):
            j = 0.0 if w_ == z0 else 0.35
            vs.append((u + rng.uniform(-j, j), v + rng.uniform(-j, j), w_ + (rng.uniform(-0.2, 0.15) if w_ == z1 else 0.0)))
        H.p("Rock").solid(vs, [(3, 2, 1, 0), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)])
        H.col(a0, b0, z0, a1, b1, z1, "rock")
    lip_z = 3.0
    H.p("Rock").box(11.0, py1 - 0.9, lip_z, 15.0, py1 + 2.6, lip_z + 0.45)                    # lip stone over the coping
    H.p("Water").box(11.4, py1 - 0.9, WZ, 14.6, py1 - 0.82, lip_z)                            # the falling sheet
    H.notes["waterfall"] = {"pos": [13.0, py1 - 0.86, WZ], "top": lip_z}
    # ---- two stainless ladders in the diving well, one on each long wall
    for (wy_, s) in ((py0, 1), (py1, -1)):
        for lx in (24.0, 26.0):
            a, b, c, d, e = (lx, wy_ - s * 1.7, DZ), (lx, wy_ - s * 1.7, DZ + 2.4), (lx, wy_ + s * 0.45, DZ + 2.4), (lx, wy_ + s * 0.45, WZ - 3.6), (lx, wy_, WZ - 3.9)
            tube(H, "Rail", [a] + bend(a, b, c, 0.6) + bend(b, c, d, 0.6) + bend(c, d, e, 0.25, 2) + [e], 0.15, sides=10)
        for k in range(3):
            z = WZ - 0.9 - k * 1.05
            a0, a1 = sorted((wy_ + s * 0.1, wy_ + s * 0.75))
            H.p("Rail").box(24.0, a0, z - 0.12, 26.0, a1, z)
    # ---- springboard at the deep end
    tip_x = px1 - 3.5 * FT
    back_x = tip_x + 8 * FT
    bt = DZ + 1.5
    bw = 1.75 * FT
    H.p("Board").box(tip_x, yc - bw / 2, bt - 0.25, back_x, yc + bw / 2, bt)
    H.p("BoardTread").box(tip_x + 0.2, yc - bw / 2 + 0.18, bt, back_x - 1.4, yc + bw / 2 - 0.18, bt + 0.03)
    H.col(tip_x, yc - bw / 2, bt - 0.25, back_x, yc + bw / 2, bt, "board")
    bx0, bx1 = px1 + 1.2, back_x + 0.4
    H.p("Stand").box(bx0, yc - 1.3, DZ, bx1, yc + 1.3, DZ + 0.15)
    for s in (-1, 1):
        y_a, y_b = sorted((yc + s * 1.05, yc + s * 1.25))
        prism_y(H, "Stand", [(bx0 + 0.2, DZ + 0.15), (bx1 - 0.2, DZ + 0.15), (bx1 - 0.6, bt - 0.25), (bx0 + 0.9, bt - 0.25)], y_a, y_b)
    H.p("Metal").box(bx0 + 1.0, yc - 1.25, bt - 0.45, bx0 + 1.5, yc + 1.25, bt - 0.25)
    H.p("Metal").box(bx1 - 1.0, yc - 1.25, bt - 0.45, bx1 - 0.6, yc + 1.25, bt - 0.25)
    H.col(bx0, yc - 1.3, DZ, bx1, yc + 1.3, bt - 0.25, "stand")
    H.notes["board"] = {"hinge": [bx1 - 0.8, yc, bt - 0.25], "tip": [tip_x, yc, bt], "length": back_x - tip_x, "width": bw,
                        "top": bt, "pieces": ["Board", "BoardTread"]}
    # ---- lights, skimmers, returns, drains, depth markers, the water
    lights = []
    for lx in (-22.0, -6.0, 4.0, 21.0):
        lz = WZ - 1.8
        disc(H, "Rail", (lx, py1, lz), (0, -1, 0), 0.7, 0.06)
        disc(H, "Lamp", (lx, py1 - 0.06, lz), (0, -1, 0), 0.55, 0.04)
        lights.append({"pos": [lx, py1 - 0.3, lz], "dir": [0, -1, 0]})
    H.notes["poolLights"] = lights
    for skx in (2.0, 18.0):
        H.p("Grate").box(skx - 0.8, py0 - 0.04, -0.62, skx + 0.8, py0 + 0.06, -0.08)
        disc(H, "Coping", (skx, py0 - 2.4, DZ), (0, 0, 1), 0.65, 0.04)
    for (rx, ry, rn) in ((-2.0, py0, (0, 1, 0)), (12.0, py0, (0, 1, 0)), (-14.0, py1, (0, -1, 0)), (30.0, py1, (0, -1, 0)), (px0, yc + 6.0, (1, 0, 0))):
        disc(H, "Grate", (rx, ry, WZ - 1.3), rn, 0.18, 0.06)
    for dyy in (-1.6, 1.6):
        H.p("Grate").box(13.0 - 0.6, yc + dyy - 0.6, zf(13.0), 13.0 + 0.6, yc + dyy + 0.6, zf(13.0) + 0.04)
    for (mx, txt) in ((px0 + 15.5, "3'6\""), (-2.0, "5'"), (13.0, "9'")):
        if not (sx0 - SW - 2.5 < mx < sx1 + SW + 2.5):
            depth_marker(H, mx, py0 - 2.4, DZ, txt, up=1)
        if not (wfx0 - 2.5 < mx < wfx1 + 2.5):
            depth_marker(H, mx, py1 + 2.4, DZ, txt, up=-1)
    H.p("Water").box(px0 + 0.03, py0 + 0.03, WZ - 0.06, px1 - 0.03, py1 - 0.03, WZ)
    H.notes["deck"] = {"min": [dx0, dy0, 0.0], "max": [dx1, dy1, DZ]}
    H.notes["cut"] = {"min": [px0 - W, py0 - W - 0.4, zmin - 1.0], "max": [px1 + W, py1 + W, 0.0]}
    return H


# ------------------------------------------------------------------ the unicorn floaty
def unicorn_floaty():
    """Giant ride-on unicorn ring (about 6.5 ft across): fat white ring with a 3 ft hole you can drop through,
    an arched neck and head with a gold twisted horn, rainbow mane and tail. Origin: ring centre, ring in XY,
    head toward -Y."""
    H = House("UnicornFloaty")
    R, r = 2.7, 1.0
    torus(H, "Vinyl", (0, 0, 0), R, r)
    disc(H, "Vinyl", (1.9, 1.9, 0.62), (0.45, 0.45, 0.77), 0.14, 0.12, sides=8)       # valve
    # neck rising out of the front of the ring, leaning back a touch, then the head reaching forward
    neck = [(0, -R, 0.2), (0, -R - 0.15, 1.2), (0, -R - 0.1, 2.2), (0, -R + 0.1, 3.1), (0, -R + 0.05, 3.8)]
    tube(H, "Vinyl", neck, [0.95, 0.85, 0.75, 0.7, 0.68], sides=14)
    pitch = Matrix.Rotation(math.radians(-14), 3, "X")
    ellipsoid(H, "Vinyl", (0, -R - 0.75, 4.15), 0.72, 1.2, 0.8, rot=pitch)               # head
    ellipsoid(H, "Vinyl", (0, -R - 1.75, 3.85), 0.56, 0.62, 0.52)                       # muzzle
    for s in (-1, 1):
        ellipsoid(H, "FloatPink", (s * 0.58, -R - 1.25, 3.9), 0.1, 0.32, 0.22, nu=10, nv=6)   # cheeks
        ellipsoid(H, "Eye", (s * 0.2, -R - 2.33, 3.95), 0.07, 0.05, 0.09, nu=8, nv=5)        # nostrils
        ellipsoid(H, "Eye", (s * 0.66, -R - 0.75, 4.42), 0.07, 0.24, 0.3, nu=10, nv=6)       # eyes
        for k in range(3):                                                               # lashes
            a = math.radians(55 + k * 30)
            e0 = Vector((s * 0.7, -R - 0.75 + math.cos(a) * 0.22, 4.42 + math.sin(a) * 0.28))
            from nc_detail import beam
            beam(H, "Eye", tuple(e0), tuple(e0 + Vector((s * 0.12, math.cos(a) * 0.12, math.sin(a) * 0.14))), 0.04, 0.04)
        # ears: pointed, white outside and pink inside, tilted out
        tilt = Matrix.Rotation(math.radians(s * 20), 3, "Y")
        ellipsoid(H, "Vinyl", (s * 0.4, -R - 0.25, 4.95), 0.18, 0.12, 0.42, nu=10, nv=6, rot=tilt)
        ellipsoid(H, "FloatPink", (s * 0.4, -R - 0.36, 4.95), 0.1, 0.04, 0.3, nu=10, nv=6, rot=tilt)
    horn(H, "Horn", (0, -R - 1.05, 4.75), (0, -R - 1.55, 6.25), 0.27)
    # rainbow mane down the back of the neck + forelock, rainbow tail fanned up at the back of the ring
    mane = ["ManePink", "ManeOrange", "ManeYellow", "ManeMint", "ManeSky", "ManeLavender", "ManePink"]
    for k, kind in enumerate(mane):
        t = k / (len(mane) - 1)
        z = 1.5 + t * 3.4
        y = -R + 0.75 + 0.15 * math.sin(t * math.pi)
        tiltx = Matrix.Rotation(math.radians(-30 + t * 50), 3, "X")
        ellipsoid(H, kind, (0, y, z), 0.24, 0.55, 0.42, nu=10, nv=7, rot=tiltx)
    ellipsoid(H, "ManeSky", (0, -R - 0.6, 4.95), 0.2, 0.32, 0.22, nu=10, nv=6)
    ellipsoid(H, "ManeLavender", (0, -R - 0.3, 5.0), 0.2, 0.3, 0.24, nu=10, nv=6)
    tail = [("ManeLavender", 30), ("ManeSky", 15), ("ManeMint", 0), ("ManeYellow", -15), ("ManePink", -30)]
    for kind, ang in tail:
        # each lobe rooted in the top of the ring at the back, sweeping up and back (35 degrees), fanned sideways
        a = math.radians(ang)
        rot = Matrix.Rotation(a, 3, "Z") @ Matrix.Rotation(math.radians(35), 3, "X")
        root = Vector((math.sin(a) * 0.35, R + 0.1, 0.82))
        c = root + rot @ Vector((0, 0.85, 0))
        ellipsoid(H, kind, tuple(c), 0.22, 0.85, 0.42, nu=10, nv=7, rot=rot)
    H.notes["floaty"] = {"ringRadius": R, "tubeRadius": r, "holeRadius": R - r,
                         "neck": {"min": [-0.9, -R - 2.4, 0.0], "max": [0.9, -R + 1.1, 6.3]}}
    return H


meta = {}
x = 0.0
for ob in list(bpy.context.scene.objects):
    ob.select_set(False)
for fn, spacing in ((backyard_pool, 80.0), (unicorn_floaty, 20.0)):
    H = fn()
    objs, tris = H.build()
    for ob in objs:
        if H.style == "UnicornFloaty":          # inflatable: smooth normals (the pool stays crisp)
            for poly in ob.data.polygons:
                poly.use_smooth = True
        ob.location.x += x
        ob["style"] = "PoolProps"
        ob.select_set(True)
    co = [v.co for ob in objs for v in ob.data.vertices]
    ext = {"x": [min(c.x for c in co), max(c.x for c in co)], "y": [min(c.y for c in co), max(c.y for c in co)], "z": [min(c.z for c in co), max(c.z for c in co)]}
    meta[H.style] = {"offsetX": x, "pieces": sorted(tris.keys()), "triangles": tris, "colliders": H.colliders, "notes": H.notes, "extents_studs": ext}
    x += spacing
bpy.ops.export_scene.gltf(filepath=os.path.join(OUT, "Pool.glb"), export_format="GLB", use_selection=True, export_apply=True, export_yup=True)
with open(os.path.join(OUT, "pool.json"), "w") as f:
    json.dump(meta, f)

# previews: a floaty copy bobbing in the pool, see-through water
for ob in list(bpy.context.scene.objects):
    if ob.name.startswith("UnicornFloaty_"):
        n = ob.copy()
        bpy.context.scene.collection.objects.link(n)
        n.location = (8.0, 24.0, -0.2 + 0.45)
        n.rotation_euler = (0, 0, math.radians(25))
        n["style"] = "PoolScene"
    elif ob.name.startswith("BackyardPool_"):
        ob["style"] = "PoolScene"
for m in bpy.data.materials:
    if m.name.endswith("_Water"):
        m.diffuse_color = (*m.diffuse_color[:3], 0.45)
        for attr, val in (("surface_render_method", "BLENDED"), ("blend_method", "BLEND")):
            try:
                setattr(m, attr, val)
            except Exception:
                pass
scene, cam = setup_render()
scene.display.shading.show_xray = False
render_views(scene, cam, ["PoolScene"], {
    "overview": ((-70, -40, 48), (2, 22, -3)),
    "board": ((-30, 2.5, 6.0), (30, 22, 1.5)),
    "deep": ((50, -8, 12), (16, 26, -4)),
    "spa": ((-22, 0.5, 7.0), (-11, 14, 0.0)),
    "waterfall": ((2, 14, 5.5), (13, 37, 2.0)),
}, "Pool")
render_views(scene, cam, ["PoolProps"], {"floaty_solo": ((80 - 9, -9, 6.5), (80, 0, 2.2))}, "Pool")
print("NEONCOAST_DONE", json.dumps({k: sum(v["triangles"].values()) for k, v in meta.items()}))
