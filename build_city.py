# Neon Coast downtown buildings (from real Miami references: Ocean Drive Art Deco hotels, mixed-use mid-rises,
# Brickell glass towers), Blender headless:
#   blender --background --factory-startup --python build_city.py
# 1 unit = 1 stud, about 1.15 studs per foot. Front faces -Y, origin at the middle of the footprint, ground z = 0.
# Exteriors first: real two-layer walls round real openings, floor slabs behind every window so the glass reads
# right, enterable ground floors; upper-floor interiors come later. Neon pieces (Neon*) glow in the game at night.
# Out: <Style>.glb per building, city.json (colliders, doors, notes), previews/City_*.png
import sys, json, os, math
sys.path.insert(0, r"C:\Users\Crisa\Documents\NeonCoast_Blender")
import importlib, nc_kit, nc_extra, nc_detail
importlib.reload(nc_kit)
importlib.reload(nc_extra)
importlib.reload(nc_detail)
from nc_extra import *
from nc_detail import beam
import bpy

reset()
nc_kit.COLORS.update({
    "DecoWall": (0.70, 0.90, 0.82), "DecoAccent": (0.98, 0.96, 0.90), "DecoCoral": (0.96, 0.56, 0.52),
    "Terrazzo": (0.88, 0.85, 0.80), "Sign": (0.10, 0.10, 0.13), "Wood": (0.42, 0.30, 0.20),
    "NeonPink": (1.0, 0.25, 0.65), "NeonBlue": (0.20, 0.80, 1.0), "NeonRed": (1.0, 0.15, 0.15), "NeonGreen": (0.3, 1.0, 0.45),
    "Brick": (0.62, 0.32, 0.24), "Stucco": (0.95, 0.86, 0.70), "Awning": (0.12, 0.55, 0.62), "AwningB": (0.85, 0.25, 0.25),
    "Stone": (0.78, 0.76, 0.72), "DarkGlass": (0.10, 0.16, 0.22), "Concrete": (0.70, 0.70, 0.68), "Metal": (0.30, 0.31, 0.33),
    "Louver": (0.55, 0.57, 0.58), "Glass": (0.45, 0.65, 0.80),
    "Hazard": (0.95, 0.80, 0.10), "Pack": (0.16, 0.18, 0.22),
})

# ------------------------------------------------------------------ helpers
FONT = {   # neon tube strokes on a 2 x 3 grid
    "A": [[(0, 0), (0, 3), (2, 3), (2, 0)], [(0, 1.5), (2, 1.5)]],
    "C": [[(2, 0), (0, 0), (0, 3), (2, 3)]],
    "E": [[(2, 0), (0, 0), (0, 3), (2, 3)], [(0, 1.5), (1.5, 1.5)]],
    "F": [[(0, 0), (0, 3), (2, 3)], [(0, 1.5), (1.5, 1.5)]],
    "H": [[(0, 0), (0, 3)], [(2, 0), (2, 3)], [(0, 1.5), (2, 1.5)]],
    "I": [[(1, 0), (1, 3)], [(0.4, 0), (1.6, 0)], [(0.4, 3), (1.6, 3)]],
    "L": [[(0, 3), (0, 0), (2, 0)]],
    "N": [[(0, 0), (0, 3), (2, 0), (2, 3)]],
    "O": [[(0, 0), (2, 0), (2, 3), (0, 3), (0, 0)]],
    "P": [[(0, 0), (0, 3), (2, 3), (2, 1.5), (0, 1.5)]],
    "R": [[(0, 0), (0, 3), (2, 3), (2, 1.6), (0, 1.6)], [(0.9, 1.6), (2, 0)]],
    "S": [[(2, 3), (0, 3), (0, 1.5), (2, 1.5), (2, 0), (0, 0)]],
    "T": [[(0, 3), (2, 3)], [(1, 3), (1, 0)]],
    "V": [[(0, 3), (1, 0), (2, 3)]],
    "Y": [[(0, 3), (1, 1.6), (2, 3)], [(1, 1.6), (1, 0)]],
    "Z": [[(0, 3), (2, 3), (0, 0), (2, 0)]],
    "B": [[(0, 0), (0, 3), (1.6, 3), (2, 2.6), (2, 1.9), (1.6, 1.5), (0, 1.5)], [(1.6, 1.5), (2, 1.1), (2, 0.4), (1.6, 0), (0, 0)]],
    "K": [[(0, 0), (0, 3)], [(2, 3), (0, 1.4), (2, 0)]],
    "M": [[(0, 0), (0, 3), (1, 1.6), (2, 3), (2, 0)]],
    "U": [[(0, 3), (0, 0), (2, 0), (2, 3)]],
    " ": [],
}


def neon_text(H, kind, text, cu, v0, face, outward, height, axis="x", vertical=False, standoff=0.45, tube=0.32):
    """Neon tube letters on a facade. axis "x": the facade runs along X at y = face (outward -1 = facing -Y).
    cu = centre along the facade, v0 = bottom (horizontal text) or top (vertical text) height."""
    sc = height / 3.0
    adv = 2.8 * sc
    d = face + outward * standoff
    flip = -outward if axis == "x" else outward      # so the text reads left-to-right from outside

    def P(u, v):
        return (u, d, v) if axis == "x" else (d, u, v)
    n = len(text)
    for k, ch in enumerate(text):
        if vertical:
            u0, vb = cu - sc, v0 - (k + 1) * height - k * 0.35 * height
        else:
            u0, vb = cu - flip * ((n * adv - 0.8 * sc) / 2) + flip * k * adv, v0
        for stroke in FONT.get(ch, []):
            pts = [P(u0 + flip * a * sc, vb + b * sc) for (a, b) in stroke]
            for p0, p1 in zip(pts, pts[1:]):
                beam(H, kind, p0, p1, tube, tube)
                # a glass standoff clip at the middle of every tube, back to the sign board (real neon is mounted
                # this way, and it keeps the letters attached)
                mu = ((p0[0] + p1[0]) / 2, (p0[1] + p1[1]) / 2, (p0[2] + p1[2]) / 2)
                if axis == "x":
                    a_, b_ = sorted((face, mu[1]))
                    H.p("Metal").box(mu[0] - 0.06, a_, mu[2] - 0.06, mu[0] + 0.06, b_, mu[2] + 0.06)
                else:
                    a_, b_ = sorted((face, mu[0]))
                    H.p("Metal").box(a_, mu[1] - 0.06, mu[2] - 0.06, b_, mu[1] + 0.06, mu[2] + 0.06)
            for p in pts:                              # rounded-ish joints
                H.p(kind).box(p[0] - tube / 2, p[1] - tube / 2, p[2] - tube / 2, p[0] + tube / 2, p[1] + tube / 2, p[2] + tube / 2)


def cwin(H, axis, fixed, outward, u0, u1, v0, v1, mullions=0, transom=None, frame="Trim", glass="Glass", sill=True, collide=True):
    """Fixed city window (no opening sash): frame, sill, one pane, optional vertical mullions and a transom bar."""
    face = fixed + outward * T_OUT
    fw = 0.4
    d0, d1 = sorted((fixed - outward * 0.1, face + outward * 0.3))   # the frame wraps the glass edge out to the face
    if axis == "x":
        box = lambda a, b, c, e, p, q: H.p(frame).box(a, p, c, b, q, e)
        gbox = lambda a, b, c, e, p, q: H.p(glass).box(a, p, c, b, q, e)
    else:
        box = lambda a, b, c, e, p, q: H.p(frame).box(p, a, c, q, b, e)
        gbox = lambda a, b, c, e, p, q: H.p(glass).box(p, a, c, q, b, e)
    box(u0 - fw, u1 + fw, v1, v1 + fw, d0, d1)
    box(u0 - fw, u0, v0, v1, d0, d1)
    box(u1, u1 + fw, v0, v1, d0, d1)
    if sill:
        s0, s1 = sorted((face, face + outward * 0.6))
        box(u0 - fw - 0.3, u1 + fw + 0.3, v0 - 0.4, v0, s0, s1)
    else:
        box(u0 - fw, u1 + fw, v0 - fw, v0, d0, d1)
    gbox(u0, u1, v0, v1, fixed - 0.06, fixed + 0.06)
    if collide:
        if axis == "x":
            H.col(u0, fixed - 0.06, v0, u1, fixed + 0.06, v1, "glass")
        else:
            H.col(fixed - 0.06, u0, v0, fixed + 0.06, u1, v1, "glass")
    m0, m1 = sorted((fixed + outward * 0.06, fixed + outward * 0.22))
    for k in range(1, mullions + 1):
        u = u0 + (u1 - u0) * k / (mullions + 1)
        box(u - 0.1, u + 0.1, v0, v1, m0, m1)
    if transom:
        box(u0, u1, transom - 0.1, transom + 0.1, m0, m1)


def roof_unit(H, x, y, z, w=4.0, d=3.0):
    H.p("Metal").box(x - w / 2, y - d / 2, z, x + w / 2, y + d / 2, z + 3.0)
    H.p("Louver").box(x - w / 2 + 0.3, y - d / 2 - 0.05, z + 0.5, x + w / 2 - 0.3, y - d / 2, z + 2.6)
    H.p("Metal").box(x - 0.8, y - 0.8, z + 3.0, x + 0.8, y + 0.8, z + 3.3)
    H.col(x - w / 2, y - d / 2, z, x + w / 2, y + d / 2, z + 3.0, "roofunit")


def floors(H, xL, xR, yF, yB, levels, roof, holes=None):
    """Floor slab + ceiling under it at every upper level, the roof slab on top (everything inside the walls).
    holes: {level: [rects]} for stairwells; holes["roof"] cuts the roof (and its ceiling)."""
    holes = holes or {}
    for z in levels:
        hz = holes.get(z, [])
        H.slab("Floor", xL, yF, xR, yB, z - 0.9, z, holes=hz)
        H.slab("Ceiling", xL, yF, xR, yB, z - 1.2, z - 0.9, tag=None, holes=hz)
    hr = holes.get("roof", [])
    H.slab("Ceiling", xL, yF, xR, yB, roof - 0.45, roof, tag="ceiling", holes=hr)
    H.slab("Roof", xL - T_OUT, yF - T_OUT, xR + T_OUT, yB + T_OUT, roof, roof + 0.7, tag="roof", holes=hr)


def stair_core(H, x0, y0, levels, w=4.4, gap=0.6, landing=4.4, max_rise=0.72, tread=1.15, max_len=None,
               kind="Concrete", rail="Metal", own_landings=False, rails=True):
    """Switchback stairs from levels[0] to levels[-1], the way real stairwells are built: from each floor's landing
    flight A climbs +Y in one lane to a mid landing, flight B climbs back -Y in the other lane to the next floor's
    landing; floors taller than 16 studs get two switchbacks (with a landing between). Even risers <= max_rise,
    12 in treads (squeezed to fit max_len if given). A divider wall between the lanes, sloped handrails, guard
    rails round the stairwell at every floor (rails=False inside an enclosed core). own_landings: build the floor
    landings too (when the floor slabs have the whole core cut out). Returns {level: hole rect} for the slabs."""
    xA0, xA1 = x0, x0 + w
    xB0, xB1 = x0 + w + gap, x0 + 2 * w + gap
    ys = y0 + landing
    runs = {}
    for za, zb in zip(levels, levels[1:]):
        h = zb - za
        cycles = max(1, math.ceil(h / 16.0))
        hc = h / cycles
        fr = hc / 2
        n = math.ceil(fr / max_rise)
        rise = fr / n
        tr = tread if not max_len else min(tread, (max_len - 2 * landing) / n)
        run = n * tr
        runs[(za, zb)] = run
        for c in range(cycles):
            zc = za + c * hc
            for k in range(n):                                    # flight A
                top = zc + (k + 1) * rise
                H.p(kind).box(xA0, ys + k * tr, top - 0.9, xA1, ys + (k + 1) * tr, top)
                H.col(xA0, ys + k * tr, top - 0.9, xA1, ys + (k + 1) * tr, top, "stairs")
            zm = zc + fr
            H.p(kind).box(xA0, ys + run, zm - 0.9, xB1, ys + run + landing, zm)     # mid landing
            H.col(xA0, ys + run, zm - 0.9, xB1, ys + run + landing, zm, "landing")
            for k in range(n):                                    # flight B
                top = zm + (k + 1) * rise
                ya = ys + run - (k + 1) * tr
                H.p(kind).box(xB0, ya, top - 0.9, xB1, ya + tr, top)
                H.col(xB0, ya, top - 0.9, xB1, ya + tr, top, "stairs")
            if c < cycles - 1 or own_landings:                   # landing at the top of this switchback
                H.p(kind).box(xA0, y0, zc + hc - 0.9, xB1, ys, zc + hc)
                H.col(xA0, y0, zc + hc - 0.9, xB1, ys, zc + hc, "landing")
            # handrails up the open sides of both flights
            beam(H, rail, (xA0 + 0.1, ys, zc + 3.0), (xA0 + 0.1, ys + run, zm + 3.0), 0.12, 0.12)
            beam(H, rail, (xB1 - 0.1, ys + run, zm + 3.0), (xB1 - 0.1, ys, zc + hc + 3.0), 0.12, 0.12)
        H.p(kind).box(xA1, ys, za, xB0, ys + run, zb)                                # divider between the lanes
        H.col(xA1, ys, za, xB0, ys + run, zb, "stairwall")
    holes = {}
    for i, z in enumerate(levels[1:], start=1):
        r_in = runs[(levels[i - 1], z)]
        r_out = runs.get((z, levels[i + 1]), 0.0) if i + 1 < len(levels) else 0.0
        far = ys + max(r_in, r_out) + landing
        holes[z] = (xA0, ys, xB1, far)
        if rails:                                                 # guard rails round the opening
            railing(H, xA0 - 0.25, ys, xA0 - 0.25, far, z, height=3.4, spacing=0.8, kind=rail)
            railing(H, xB1 + 0.25, ys, xB1 + 0.25, far, z, height=3.4, spacing=0.8, kind=rail)
            railing(H, xA0 - 0.25, far + 0.25, xB1 + 0.25, far + 0.25, z, height=3.4, spacing=0.8, kind=rail)
    return holes


def parapet(H, xL, xR, yF, yB, z0, h, kind="WallsOut", cap="Trim"):
    o = T_OUT
    for (a0, b0, a1, b1) in ((xL - o, yF - o, xR + o, yF - o + 0.7), (xL - o, yB + o - 0.7, xR + o, yB + o),
                             (xL - o, yF - o + 0.7, xL - o + 0.7, yB + o - 0.7), (xR + o - 0.7, yF - o + 0.7, xR + o, yB + o - 0.7)):
        H.p(kind).box(a0, b0, z0, a1, b1, z0 + h)
        H.p(cap).box(a0 - 0.1, b0 - 0.1, z0 + h, a1 + 0.1, b1 + 0.1, z0 + h + 0.3)
        H.col(a0, b0, z0, a1, b1, z0 + h, "parapet")


# ------------------------------------------------------------------ Art Deco hotel (Ocean Drive)
def deco_hotel():
    """Four-story Art Deco hotel: mint stucco, a central pylon with a vertical neon CORAL sign and a stepped
    crown, eyebrow sunshades over every window band (neon under them), corner fins, a terrazzo front terrace up
    a few steps, a deep entrance canopy with HOTEL in neon, storefront lobby glass, a fire escape on the side,
    speed lines on the parapet, rooftop units and a stair penthouse."""
    H = House("DecoHotel")
    xL, xR, yF, yB = -34.45, 34.45, -24.45, 24.45
    F, G, S = 0.8, 15.0, 12.0
    L = [F, F + G, F + G + S, F + G + 2 * S]
    ROOF = F + G + 3 * S
    fo = yF - T_OUT                                   # front face
    H.p("Foundation").box(xL - 0.6, yF - 0.6, 0, xR + 0.6, yB + 0.6, F - 0.35)
    H.col(xL - 0.6, yF - 0.6, 0, xR + 0.6, yB + 0.6, F - 0.35, "floor")
    H.slab("Terrazzo", xL, yF, xR, yB, F - 0.35, F)
    # the stairs: lobby to every floor and up into the roof penthouse (back-left corner)
    RZ = ROOF + 0.7
    st = stair_core(H, -32.0, 1.5, L + [RZ])
    hz = {z: [r] for z, r in st.items() if z != RZ}
    hz["roof"] = [st[RZ]]
    floors(H, xL, xR, yF, yB, L[1:], ROOF, hz)
    # terrace across the front, up three steps in the middle, low pastel walls along its edge
    ty0 = fo - 11.0
    H.slab("Terrazzo", xL - T_OUT - 1.0, ty0, xR + T_OUT + 1.0, fo, 0, F, tag="porch")
    for k in range(3):
        H.slab("Terrazzo", -6.0, ty0 - 1.2 * (k + 1), 6.0, ty0 - 1.2 * k, 0, F * (2 - k) / 3 + 0.01, tag="step")
    for (a, b) in ((xL - T_OUT - 1.0, -6.0), (6.0, xR + T_OUT + 1.0)):
        H.p("DecoWall").box(a, ty0, F, b, ty0 + 0.8, F + 2.6)
        H.p("DecoAccent").box(a - 0.1, ty0 - 0.1, F + 2.6, b + 0.1, ty0 + 0.9, F + 2.9)
        H.col(a, ty0, F, b, ty0 + 0.8, F + 2.9, "terracewall")
    # walls
    front = [(-4.6, 4.6, F, F + 10.5), (-30.0, -9.0, F + 1.2, F + 11.0), (9.0, 30.0, F + 1.2, F + 11.0)]
    wins_x = [(-31.0, -25.5), (-22.0, -16.5), (-13.0, -9.0), (9.0, 13.0), (16.5, 22.0), (25.5, 31.0)]
    for n in (1, 2, 3):
        front += [(a, b, L[n] + 2.6, L[n] + 9.2) for (a, b) in wins_x]
    back = [(-3.0, 1.6, F, F + 8.4)] + [(a, b, L[n] + 2.6, L[n] + 9.2) for n in (1, 2, 3) for (a, b) in wins_x]
    side_y = [(-18.0, -12.0), (-6.0, 0.0), (6.0, 12.0), (16.0, 21.0)]
    side = [(a, b, F + 3.0, F + 10.0) for (a, b) in side_y[1:3]] + [(a, b, L[n] + 2.6, L[n] + 9.2) for n in (1, 2, 3) for (a, b) in side_y]
    side_r = [(a, b, F + 3.0, F + 10.0) for (a, b) in side_y[1:3]] + [(a, b, L[n] + 2.6, L[n] + 9.2) for n in (1, 2, 3) for (a, b) in side_y if (a, b) != (-6.0, 0.0)]
    side_r += [(-5.0, -1.0, L[n], L[n] + 8.0) for n in (1, 2, 3)]                       # doors onto the fire escape
    H.wall("x", yF, -1, xL - T_OUT, xR + T_OUT, F, ROOF, front, outer_kind="DecoWall")
    H.wall("x", yB, 1, xL - T_OUT, xR + T_OUT, F, ROOF, back, outer_kind="DecoWall")
    H.wall("y", xL, -1, yF + T_IN, yB - T_IN, F, ROOF, side, outer_kind="DecoWall")
    H.wall("y", xR, 1, yF + T_IN, yB - T_IN, F, ROOF, side_r, outer_kind="DecoWall")
    for (a, b, v0, v1) in front[1:3]:                                                     # lobby storefronts
        cwin(H, "x", yF, -1, a, b, v0, v1, mullions=3, transom=v1 - 2.4, sill=False)
    for (a, b, v0, v1) in front[3:]:
        cwin(H, "x", yF, -1, a, b, v0, v1, mullions=1 if b - a > 5 else 0, transom=v0 + (v1 - v0) * 0.62)
    for (a, b, v0, v1) in back[1:]:
        cwin(H, "x", yB, 1, a, b, v0, v1, mullions=1 if b - a > 5 else 0)
    for (a, b, v0, v1) in side:
        cwin(H, "y", xL, -1, a, b, v0, v1, mullions=1)
    for (a, b, v0, v1) in side_r[:-3]:
        cwin(H, "y", xR, 1, a, b, v0, v1, mullions=1)
    H.door("x", yF, -1, -4.6, 0.0, F, F + 9.2)
    H.door("x", yF, -1, 0.0, 4.6, F, F + 9.2, hinge_at_u0=False)
    H.uvd("Glass", "x", -4.6, 4.6, F + 9.2 + 0.3, F + 10.5, yF - 0.06, yF + 0.06)       # transom over the doors
    H.door("x", yB, 1, -3.0, 1.6, F, F + 8.4, glass=False, kind="back")
    for n in (1, 2, 3):
        H.door("y", xR, 1, -5.0, -1.0, L[n], L[n] + 8.0, kind="fireescape")
    # eyebrow sunshades over every window band, neon pink tucked under the front ones; storefront eyebrows
    for n in (1, 2, 3):
        z = L[n] + 9.9
        for (a, b) in ((-32.0, -8.0), (8.0, 32.0)):
            H.p("DecoAccent").box(a, fo - 2.4, z, b, fo, z + 0.35)
            H.p("NeonPink").box(a + 0.2, fo - 2.3, z - 0.12, b - 0.2, fo - 2.1, z)
        for (sx, s) in ((xL - T_OUT, -1), (xR + T_OUT, 1)):
            a, b = sorted((sx, sx + s * 2.0))
            spans = [(-19.5, 22.0)] if s < 0 else [(-19.5, -10.0), (5.0, 22.0)]        # clear of the fire escape
            for (y0_, y1_) in spans:
                H.p("DecoAccent").box(a, y0_, z, b, y1_, z + 0.35)
    for (a, b) in ((-31.0, -9.0), (9.0, 31.0)):
        H.p("DecoAccent").box(a, fo - 4.0, F + 11.6, b, fo, F + 12.1)
        H.p("NeonBlue").box(a + 0.2, fo - 3.9, F + 11.48, b - 0.2, fo - 3.7, F + 11.6)
    # corner fins (coral) and speed lines along the parapet
    for x in (xL - T_OUT, xR + T_OUT):
        s = -1 if x < 0 else 1
        a, b = sorted((x, x + s * 0.7))
        H.p("DecoCoral").box(a, fo - 1.6, F, b, fo + 2.0, ROOF + 4.5)
        H.col(a, fo - 1.6, F, b, fo + 2.0, ROOF + 4.5, "fin")
    parapet(H, xL, xR, yF, yB, ROOF + 0.7, 3.6, kind="DecoWall", cap="DecoAccent")
    for k in range(3):
        z = ROOF + 1.2 + k * 0.9
        H.p("DecoAccent").box(xL - T_OUT + 0.7, fo - 0.25, z, xR + T_OUT - 0.7, fo, z + 0.25)
    # the pylon: from the canopy to a stepped crown, the vertical neon CORAL on a dark sign plate
    py0, py1 = fo - 2.5, fo
    H.p("DecoAccent").box(-7.0, py0, F + 12.1, 7.0, py1, 70.0)
    H.col(-7.0, py0, F + 12.1, 7.0, py1, 70.0, "pylon")
    for (w, z0, z1) in ((5.5, 70.0, 73.5), (4.0, 73.5, 76.5), (2.5, 76.5, 79.0)):
        H.p("DecoAccent").box(-w, py0 + 0.3, z0, w, py1 + 2.0, z1)
    H.p("Metal").box(-0.25, py0 + 1.0, 79.0, 0.25, py0 + 1.5, 88.0)                      # spire
    H.p("DecoCoral").box(-7.05, py0 - 0.05, 30.0, -5.6, py1, 31.0)
    H.p("DecoCoral").box(5.6, py0 - 0.05, 30.0, 7.05, py1, 31.0)
    H.p("Sign").box(-4.2, py0 - 0.25, 38.0, 4.2, py0, 69.0)
    neon_text(H, "NeonPink", "CORAL", 0.0, 68.0, py0 - 0.25, -1, 4.6, vertical=True)
    for x in (-6.6, 6.6):
        H.p("NeonBlue").box(x - 0.15, py0 - 0.3, 17.0, x + 0.15, py0, 69.5)
    # entrance canopy with HOTEL standing on its front edge, two steel hangers back to the pylon
    cy0 = fo - 9.5
    H.p("DecoAccent").box(-9.0, cy0, F + 11.2, 9.0, py0, F + 12.1)
    H.col(-9.0, cy0, F + 11.2, 9.0, py0, F + 12.1, "canopy")
    H.p("NeonBlue").box(-9.0, cy0 - 0.1, F + 11.2, 9.0, cy0, F + 11.5)
    neon_text(H, "NeonPink", "HOTEL", 0.0, F + 12.1 + 0.16, cy0 + 0.6, -1, 2.4)          # standing on the canopy
    for x in (-8.5, 8.5):                                                                 # clear of the letters
        beam(H, "Metal", (x, cy0 + 0.6, F + 12.1), (x * 0.8, py0, F + 17.5), 0.18, 0.18)
    # fire escape on the right side: landings at every upper floor, stairs between, a drop ladder
    # (steep 60-degree stairs along the outer strip; the inner strip is the walkway past the doors; each landing
    # has the opening where the stair from below arrives)
    fx0 = xR + T_OUT
    sx0_, sx1_ = fx0 + 2.0, fx0 + 3.4
    for n in (1, 2, 3):
        pieces = [(fx0, -9.0, fx0 + 2.0, 4.0), (fx0 + 2.0, -1.6, fx0 + 3.8, 4.0)] if n > 1 else [(fx0, -9.0, fx0 + 3.8, 4.0)]
        if n > 1:
            pieces.append((fx0 + 3.4, -9.0, fx0 + 3.8, -1.6))
        for (a0, b0, a1, b1) in pieces:
            H.p("Metal").box(a0, b0, L[n] - 0.25, a1, b1, L[n])
            H.col(a0, b0, L[n] - 0.25, a1, b1, L[n], "fireescape")
        railing(H, fx0 + 3.6, -9.0, fx0 + 3.6, 4.0, L[n], height=3.2, spacing=0.9, kind="Metal")
        for y in (-9.0, 4.0):
            H.p("Metal").box(fx0, y - 0.1, L[n], fx0 + 3.8, y + 0.1, L[n] + 3.2)
        H.p("Metal").box(fx0, -9.0, L[n] - 1.0, fx0 + 0.35, 4.0, L[n] - 0.25)            # bracket rail on the wall
    for n in (1, 2):
        ya, yb_ = -1.6, -8.6
        for x in (sx0_ + 0.1, sx1_ - 0.1):
            beam(H, "Metal", (x, ya, L[n]), (x, yb_, L[n + 1]), 0.15, 0.35)
        for k in range(1, 16):
            t = k / 16
            y, z = ya + (yb_ - ya) * t, L[n] + (L[n + 1] - L[n]) * t
            H.p("Metal").box(sx0_ + 0.2, y - 0.25, z - 0.08, sx1_ - 0.2, y + 0.25, z)
    for x in (fx0 + 1.0, fx0 + 2.2):
        H.p("Metal").box(x - 0.08, 3.0, L[1] - 7.0, x + 0.08, 3.16, L[1] - 0.25)
    for k in range(9):
        H.p("Metal").box(fx0 + 1.0, 3.0, L[1] - 6.6 + k * 0.75, fx0 + 2.2, 3.16, L[1] - 6.5 + k * 0.75)
    # lobby: reception desk and two round columns (seen through the storefront glass)
    H.p("Wood").box(-8.0, 12.0, F, 8.0, 15.0, F + 3.8)
    H.p("Terrazzo").box(-8.3, 11.7, F + 3.8, 8.3, 15.3, F + 4.1)
    H.col(-8.0, 12.0, F, 8.0, 15.0, F + 4.1, "furniture")
    for x in (-14.0, 14.0):
        H.column(x, 0.0, F, L[1] - 1.2, r=0.9, kind="DecoAccent")
    # roof: the stair penthouse round the top of the stairs with a door out onto the roof, rooftop units
    pz0, pz1 = RZ, ROOF + 10.0
    for (axis, fixed, o, a0, a1, ops) in (("y", -33.0, -1, 0.5 + T_IN, 23.2 - T_IN, []),
                                          ("y", -21.6, 1, 0.5 + T_IN, 23.2 - T_IN, [(1.7, 5.9, pz0, pz0 + 8.4)]),
                                          ("x", 0.5, -1, -33.0 - T_OUT, -21.6 + T_OUT, []), ("x", 23.2, 1, -33.0 - T_OUT, -21.6 + T_OUT, [])):
        H.wall(axis, fixed, o, a0, a1, pz0, pz1, ops, outer_kind="DecoWall")
    H.door("y", -21.6, 1, 1.7, 5.9, pz0, pz0 + 8.4, glass=False, kind="roof")
    H.p("Roof").box(-33.0 - T_OUT, 0.5 - T_OUT, pz1, -21.6 + T_OUT, 23.2 + T_OUT, pz1 + 0.6)
    H.col(-33.0 - T_OUT, 0.5 - T_OUT, pz1, -21.6 + T_OUT, 23.2 + T_OUT, pz1 + 0.6, "roof")
    H.p("DecoAccent").box(-33.0 - T_OUT - 0.2, 0.5 - T_OUT - 0.2, pz1 + 0.6, -21.6 + T_OUT + 0.2, 23.2 + T_OUT + 0.2, pz1 + 0.9)
    for (x, y) in ((10.0, 12.0), (18.0, 12.0), (14.0, 4.0)):
        roof_unit(H, x, y, ROOF + 0.7)
    H.notes["lights"] = [[-16.0, cy0 + 2.0, F + 10.5], [16.0, cy0 + 2.0, F + 10.5]]
    H.notes["neon"] = {"sign": [0.0, py0 - 0.6, 53.0], "color": "pink"}
    return H


# ------------------------------------------------------------------ mixed-use mid-rise
def mid_rise(style, outer, signs, awning="Awning"):
    """Five-story mixed-use block: three storefront bays (glass, recessed doors, transoms, striped awnings, a dark
    sign band with neon shop names), apartments above with paired windows and balconies on the middle bay, a
    stepped cornice, parapet, rooftop units and a stair bulkhead. Party wall on the right for row placement."""
    H = House(style)
    xL, xR, yF, yB = -29.45, 29.45, -21.45, 21.45
    F, G, S = 0.3, 16.0, 12.0
    L = [F, F + G] + [F + G + S * k for k in (1, 2, 3)]
    ROOF = F + G + 4 * S
    fo = yF - T_OUT
    H.p("Foundation").box(xL - 0.4, yF - 0.4, 0, xR + 0.4, yB + 0.4, F)
    H.col(xL - 0.4, yF - 0.4, 0, xR + 0.4, yB + 0.4, F, "floor")
    H.slab("Tile", xL, yF, xR, yB, F - 0.25, F)
    # stairs against the party wall at the back, from the shops up to the roof bulkhead
    RZ = ROOF + 0.7
    st = stair_core(H, 17.9, -2.2, L + [RZ])
    hz = {z: [r] for z, r in st.items() if z != RZ}
    hz["roof"] = [st[RZ]]
    floors(H, xL, xR, yF, yB, L[1:], ROOF, hz)
    bays = [(-28.0, -10.5), (-8.75, 8.75), (10.5, 28.0)]
    front = [(a, b, F, F + 12.0) for (a, b) in bays]
    up_w = []
    for (a, b) in bays:
        c = (a + b) / 2
        up_w += [(c - 7.0, c - 2.0), (c + 2.0, c + 7.0)]
    for n in range(1, 5):
        for (a, b) in up_w:
            mid_bay = -8.75 < a < 8.75
            front.append((a, b, L[n], L[n] + 8.4) if mid_bay else (a, b, L[n] + 2.8, L[n] + 9.0))
    H.wall("x", yF, -1, xL - T_OUT, xR + T_OUT, F, ROOF, front, outer_kind=outer)
    back = [(-3.0, 1.6, F, F + 8.4)] + [(a, b, L[n] + 2.8, L[n] + 9.0) for n in range(1, 5) for (a, b) in up_w]
    H.wall("x", yB, 1, xL - T_OUT, xR + T_OUT, F, ROOF, back, outer_kind=outer)
    side = [(a, b, L[n] + 2.8, L[n] + 9.0) for n in range(1, 5) for (a, b) in ((-14.0, -9.0), (-2.5, 2.5), (9.0, 14.0))]
    H.wall("y", xL, -1, yF + T_IN, yB - T_IN, F, ROOF, side, outer_kind=outer)
    H.wall("y", xR, 1, yF + T_IN, yB - T_IN, F, ROOF, [], outer_kind=outer)            # party wall
    for (a, b, v0, v1) in side:
        cwin(H, "y", xL, -1, a, b, v0, v1, mullions=0, transom=v0 + (v1 - v0) * 0.6)
    for (a, b, v0, v1) in back[1:]:
        cwin(H, "x", yB, 1, a, b, v0, v1, transom=v0 + (v1 - v0) * 0.6)
    H.door("x", yB, 1, -3.0, 1.6, F, F + 8.4, glass=False, kind="back")
    # storefronts: door in the middle of each bay, display glass either side, transom glass over the lot
    for (a, b) in bays:
        c = (a + b) / 2
        H.door("x", yF, -1, c - 2.3, c + 2.3, F, F + 8.8, kind="shop")
        cwin(H, "x", yF, -1, a + 0.3, c - 2.7, F + 1.6, F + 8.8, mullions=1, sill=False)
        cwin(H, "x", yF, -1, c + 2.7, b - 0.3, F + 1.6, F + 8.8, mullions=1, sill=False)
        cwin(H, "x", yF, -1, a + 0.3, b - 0.3, F + 9.4, F + 11.7, mullions=3, sill=False)
        for (u0, u1) in ((a, c - 2.3), (c + 2.3, b)):                                     # bulkheads under the glass
            H.p("Stone").box(u0, fo - 0.3, F, u1, yF + T_IN, F + 1.6)
        # striped awning: alternating strips sloping out from the sign band
        n_ = 8
        for k in range(n_):
            u0, u1 = a + (b - a) * k / n_, a + (b - a) * (k + 1) / n_
            kind = awning if k % 2 == 0 else "DecoAccent"
            H.p(kind).solid([(u0, fo, F + 12.6), (u1, fo, F + 12.6), (u1, fo - 4.5, F + 10.6), (u0, fo - 4.5, F + 10.6),
                             (u0, fo, F + 12.9), (u1, fo, F + 12.9), (u1, fo - 4.5, F + 10.9), (u0, fo - 4.5, F + 10.9)],
                            [(0, 1, 2, 3), (7, 6, 5, 4), (0, 4, 5, 1), (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0)])
        H.p(awning).box(a, fo - 4.6, F + 9.9, b, fo - 4.4, F + 10.9)                      # valance
    # sign band with the neon names, a projecting blade sign on the corner
    H.p("Sign").box(xL - T_OUT, fo - 0.5, F + 12.9, xR + T_OUT, fo, F + 15.6)
    for (a, b), txt, col in zip(bays, signs, ("NeonPink", "NeonBlue", "NeonGreen")):
        neon_text(H, col, txt, (a + b) / 2, F + 13.3, fo - 0.5, -1, 1.9, standoff=0.3, tube=0.26)
    # balconies on the middle bay, floors 2-5
    for n in range(1, 5):
        H.p("Concrete").box(-8.0, fo - 4.0, L[n] - 0.45, 8.0, fo, L[n])
        H.col(-8.0, fo - 4.0, L[n] - 0.45, 8.0, fo, L[n], "balcony")
        railing(H, -7.8, fo - 3.8, 7.8, fo - 3.8, L[n], height=3.4, spacing=0.6, kind="Metal")
        railing(H, -7.8, fo - 3.8, -7.8, fo, L[n], height=3.4, spacing=0.6, kind="Metal")
        railing(H, 7.8, fo - 3.8, 7.8, fo, L[n], height=3.4, spacing=0.6, kind="Metal")
    for n in range(1, 5):
        for (a, b) in up_w:
            if -8.75 < a < 8.75:
                H.door("x", yF, -1, a, b, L[n], L[n] + 8.4, kind="balcony")
            else:
                cwin(H, "x", yF, -1, a, b, L[n] + 2.8, L[n] + 9.0, transom=L[n] + 2.8 + 6.2 * 0.6)
    # floor bands, stepped cornice, parapet; roof
    for n in range(1, 5):
        H.p("Stone").box(xL - T_OUT - 0.2, fo - 0.3, L[n] - 0.6, xR + T_OUT + 0.2, fo, L[n] - 0.1)
    for k, (dz, out) in enumerate(((0.0, 0.5), (0.6, 1.1), (1.2, 1.7))):
        H.p("Stone").box(xL - T_OUT - out, fo - out, ROOF - 1.8 + dz, xR + T_OUT + (out if k < 3 else 0), fo, ROOF - 1.2 + dz)
    parapet(H, xL, xR, yF, yB, ROOF + 0.7, 3.0, kind=outer, cap="Stone")
    # stair bulkhead over the top of the stairs, door out onto the roof
    bz0, bz1 = RZ, ROOF + 10.0
    for (axis, fixed, o, a0, a1, ops) in (("y", 16.9, -1, -3.2 + T_IN, 20.3 - T_IN, [(-2.1, 2.1, bz0, bz0 + 8.4)]),
                                          ("y", 28.3, 1, -3.2 + T_IN, 20.3 - T_IN, []),
                                          ("x", -3.2, -1, 16.9 - T_OUT, 28.3 + T_OUT, []), ("x", 20.3, 1, 16.9 - T_OUT, 28.3 + T_OUT, [])):
        H.wall(axis, fixed, o, a0, a1, bz0, bz1, ops, outer_kind=outer)
    H.door("y", 16.9, -1, -2.1, 2.1, bz0, bz0 + 8.4, glass=False, kind="roof")
    H.p("Roof").box(16.9 - T_OUT, -3.2 - T_OUT, bz1, 28.3 + T_OUT, 20.3 + T_OUT, bz1 + 0.6)
    H.col(16.9 - T_OUT, -3.2 - T_OUT, bz1, 28.3 + T_OUT, 20.3 + T_OUT, bz1 + 0.6, "roof")
    H.p("Stone").box(16.9 - T_OUT - 0.2, -3.2 - T_OUT - 0.2, bz1 + 0.6, 28.3 + T_OUT + 0.2, 20.3 + T_OUT + 0.2, bz1 + 0.9)
    for (x, y) in ((-14.0, 4.0), (-6.0, 4.0), (-14.0, 12.0), (-6.0, 12.0)):
        roof_unit(H, x, y, ROOF + 0.7)
    H.notes["lights"] = [[(a + b) / 2, fo - 3.0, F + 10.0] for (a, b) in bays]
    return H


# ------------------------------------------------------------------ glass office tower
def office_tower():
    """Brickell-style office tower, enterable top to bottom: a stone-clad 3-story podium with a double-height glass
    lobby (reception desk, a parachute kiosk), a 15-story curtain-wall tower (glass, mullions every 5 studs, dark
    spandrels at every slab), and a concrete core with the free stairs (switchbacks lobby to roof, a door onto
    every floor) and an express elevator shaft (lobby <-> roof; the game runs the car and charges for the ride).
    On top: the crown is a mechanical room you walk out of onto a roof deck with a glass guard rail, a steel
    BASE-jump platform out over the street, a blue LED edge, a mast with a red aircraft light."""
    H = House("OfficeTower")
    xL, xR, yF, yB = -44.45, 44.45, -34.45, 34.45
    F = 0.4
    P = [F, F + 22.0, F + 36.0]
    PROOF = F + 50.0
    fo = yF - T_OUT
    tx0, tx1, ty0, ty1 = -30.0, 30.0, -25.0, 25.0
    T0, FL, NF = PROOF + 0.7, 14.0, 15
    TOP = T0 + FL * NF
    RZ = TOP + 0.8                                            # the roof deck surface
    CORE = (-12.05, -11.05, 12.05, 11.05)                     # core walls' outer faces
    tower_levels = [T0 + FL * k for k in range(1, NF)]       # floors 2..15 (floor 1 is the podium roof, T0)
    levels = P + [T0] + tower_levels + [RZ]
    # ---- the free stairs in the west half of the core (enclosed: no guard rails, own landings everywhere)
    stair_core(H, -11.0, -10.0, levels, max_len=20.0, own_landings=True, rails=False)
    # ---- podium
    H.p("Foundation").box(xL - 0.5, yF - 0.5, 0, xR + 0.5, yB + 0.5, F)
    H.col(xL - 0.5, yF - 0.5, 0, xR + 0.5, yB + 0.5, F, "floor")
    H.slab("Stone", xL, yF, xR, yB, F - 0.3, F)
    ribbons = [(xL + 2.0, xR - 2.0, P[n] + 3.0, P[n] + 11.0) for n in (1, 2)]
    H.wall("x", yF, -1, xL - T_OUT, xR + T_OUT, F, PROOF, [(-30.0, 30.0, F, F + 20.0)] + ribbons, outer_kind="Stone")
    H.wall("x", yB, 1, xL - T_OUT, xR + T_OUT, F, PROOF, [(-3.0, 1.6, F, F + 8.4)] + ribbons, outer_kind="Stone")
    sribs = [(yF + 2.0, yB - 2.0, P[n] + 3.0, P[n] + 11.0) for n in (1, 2)]
    H.wall("y", xL, -1, yF + T_IN, yB - T_IN, F, PROOF, sribs, outer_kind="Stone")
    H.wall("y", xR, 1, yF + T_IN, yB - T_IN, F, PROOF, sribs, outer_kind="Stone")
    H.door("x", yB, 1, -3.0, 1.6, F, F + 8.4, glass=False, kind="back")
    for n in (1, 2):
        H.slab("Floor", xL, yF, xR, yB, P[n] - 0.9, P[n], holes=[CORE])
        H.slab("Ceiling", xL, yF, xR, yB, P[n] - 1.2, P[n] - 0.9, tag=None, holes=[CORE])
    H.slab("Roof", xL - T_OUT, yF - T_OUT, xR + T_OUT, yB + T_OUT, PROOF, PROOF + 0.7, tag="roof", holes=[CORE])
    parapet(H, xL, xR, yF, yB, PROOF + 0.7, 3.4, kind="Stone", cap="Metal")
    cwin(H, "x", yF, -1, -30.0, -5.0, F + 0.4, F + 20.0, mullions=4, transom=F + 10.0, frame="Metal", sill=False)
    cwin(H, "x", yF, -1, 5.0, 30.0, F + 0.4, F + 20.0, mullions=4, transom=F + 10.0, frame="Metal", sill=False)
    cwin(H, "x", yF, -1, -5.0, 5.0, F + 10.0, F + 20.0, mullions=1, frame="Metal", sill=False)
    for (a, b, v0, v1) in ribbons:
        cwin(H, "x", yF, -1, a, b, v0, v1, mullions=16, frame="Metal", sill=False)
        cwin(H, "x", yB, 1, a, b, v0, v1, mullions=16, frame="Metal", sill=False)
    for (a, b, v0, v1) in sribs:
        cwin(H, "y", xL, -1, a, b, v0, v1, mullions=12, frame="Metal", sill=False)
        cwin(H, "y", xR, 1, a, b, v0, v1, mullions=12, frame="Metal", sill=False)
    H.door("x", yF, -1, -4.6, 0.0, F, F + 9.6)
    H.door("x", yF, -1, 0.0, 4.6, F, F + 9.6, hinge_at_u0=False)
    H.p("Metal").box(-20.0, fo - 12.0, F + 13.0, 20.0, fo, F + 13.8)                      # canopy
    H.col(-20.0, fo - 12.0, F + 13.0, 20.0, fo, F + 13.8, "canopy")
    for x in (-18.0, 18.0):
        H.p("Metal").box(x - 0.3, fo - 11.0, F, x + 0.3, fo - 10.0, F + 13.0)
        H.col(x - 0.3, fo - 11.0, F, x + 0.3, fo - 10.0, F + 13.0, "post")
    H.p("NeonBlue").box(-20.0, fo - 12.1, F + 13.0, 20.0, fo - 12.0, F + 13.8)
    # lobby: reception desk facing the doors, the parachute kiosk by the elevator
    H.p("Wood").box(-9.0, -22.0, F, 9.0, -19.0, F + 3.8)
    H.p("Stone").box(-9.3, -22.3, F + 3.8, 9.3, -18.7, F + 4.1)
    H.col(-9.0, -22.0, F, 9.0, -19.0, F + 4.1, "furniture")
    kx, ky = 24.0, -8.0
    H.p("Wood").box(kx - 3.0, ky - 1.2, F, kx + 3.0, ky + 1.2, F + 3.6)                       # kiosk counter
    H.p("Stone").box(kx - 3.2, ky - 1.4, F + 3.6, kx + 3.2, ky + 1.4, F + 3.9)
    H.p("Metal").box(kx - 3.0, ky + 1.2, F, kx + 3.0, ky + 1.6, F + 9.0)                      # display wall
    H.p("Sign").box(kx - 3.0, ky + 0.9, F + 6.2, kx + 3.0, ky + 1.2, F + 8.6)
    neon_text(H, "NeonRed", "SKY", kx, F + 6.5, ky + 0.9, -1, 1.8, standoff=0.3, tube=0.24)
    for (px, pz) in ((kx - 1.8, F + 4.3), (kx, F + 4.3), (kx + 1.8, F + 4.3)):                 # parachute packs on pegs
        H.p("Pack").box(px - 0.6, ky + 0.85, pz, px + 0.6, ky + 1.2, pz + 1.6)
        H.p("Metal").box(px - 0.1, ky + 1.0, pz + 1.6, px + 0.1, ky + 1.2, pz + 1.8)
    H.col(kx - 3.0, ky - 1.2, F, kx + 3.0, ky + 1.6, F + 3.9, "furniture")
    # ---- tower floors (podium roof is floor 1), all with the core cut out
    for z in tower_levels:
        H.slab("Concrete", tx0 + 0.8, ty0 + 0.8, tx1 - 0.8, ty1 - 0.8, z - 0.9, z, tag="floor", holes=[CORE])
    # ---- the core: concrete walls lobby to crown, a stair door on every floor (west), elevator doors (east) at
    # the lobby and the roof only; a wall between the stairs and the shaft
    stair_doors = [(-9.8, -6.2, z, z + 8.6) for z in levels]
    lift_doors = [(-3.0, 3.0, F, F + 9.0), (-3.0, 3.0, RZ, RZ + 9.0)]
    CZ1 = TOP + 14.0
    H.wall("y", -11.5, -1, -10.05, 10.05, F, CZ1, stair_doors, outer_kind="Concrete", inner_kind="Concrete")
    H.wall("y", 11.5, 1, -10.05, 10.05, F, CZ1, lift_doors, outer_kind="Concrete", inner_kind="Concrete")
    H.wall("x", -10.5, -1, -12.05, 12.05, F, CZ1, [], outer_kind="Concrete", inner_kind="Concrete")
    H.wall("x", 10.5, 1, -12.05, 12.05, F, CZ1, [], outer_kind="Concrete", inner_kind="Concrete")
    H.p("Concrete").box(-1.5, -10.05, F, -0.9, 10.05, CZ1)                                    # stair | shaft
    H.col(-1.5, -10.05, F, -0.9, 10.05, CZ1, "core")
    for z in (F, RZ):                                                                           # sills at the stops
        H.p("Metal").box(11.05, -3.0, z - 0.2, 12.05, 3.0, z)
        H.col(11.05, -3.0, z - 0.2, 12.05, 3.0, z, "sill")
    for z in (F, RZ):                                                                           # call panels on the core
        H.p("Metal").box(12.05, -5.7, z + 3.8, 12.3, -4.7, z + 5.4)
        H.p("NeonBlue").box(12.3, -5.35, z + 4.75, 12.36, -5.05, z + 5.05)
    H.p("Concrete").box(-0.9, -10.05, F - 0.4, 11.05, 10.05, F)                                # shaft pit floor
    H.notes["elevator"] = {"shaft": {"min": [-0.9, -10.05, F], "max": [11.05, 10.05, CZ1]},
                           "car": {"min": [0.6, -4.6], "max": [10.4, 4.6]}, "stops": [F, RZ],
                           "door": {"x": 12.05, "y": [-3.0, 3.0], "h": 9.0},
                           "call": [[12.45, -5.2, F + 4.6], [12.45, -5.2, RZ + 4.6]]}
    H.notes["parachuteShop"] = [[kx, ky - 1.6, F + 3.0], [-18.0, -17.0 + T_IN + 1.9, RZ + 3.0]]
    # ---- curtain wall on all four sides of the tower
    for (axis, fixed, a0, a1, o) in (("x", ty0, tx0, tx1, -1), ("x", ty1, tx0, tx1, 1), ("y", tx0, ty0, ty1, -1), ("y", tx1, ty0, ty1, 1)):
        def bx(kind, u0, u1, v0, v1, d0, d1):
            lo, hi = sorted((fixed + o * d0, fixed + o * d1))
            if axis == "x":
                H.p(kind).box(u0, lo, v0, u1, hi, v1)
            else:
                H.p(kind).box(lo, u0, v0, hi, u1, v1)
        bx("Glass", a0, a1, T0, TOP, -0.08, 0.08)
        if axis == "x":
            H.col(a0, fixed - 0.1, T0, a1, fixed + 0.1, TOP, "curtainwall")
        else:
            H.col(fixed - 0.1, a0, T0, fixed + 0.1, a1, TOP, "curtainwall")
        n_m = int(round((a1 - a0) / 5.0))
        for m in range(n_m + 1):
            u = a0 + (a1 - a0) * m / n_m
            w = 0.6 if m in (0, n_m) else 0.25
            bx("Metal", u - w, u + w, T0, TOP, 0.08, 0.6 if m in (0, n_m) else 0.45)
        for k in range(NF + 1):
            z = T0 + FL * k
            bx("DarkGlass", a0, a1, z - 1.0, z + 0.4, 0.08, 0.2)
    # ---- roof deck, glass guard rail with a gap for the BASE-jump platform on the north side, LED edge
    H.slab("Metal", tx0 - 0.6, ty0 - 0.6, tx1 + 0.6, ty1 + 0.6, TOP, RZ, tag="roof", holes=[CORE])
    gx0, gx1 = -4.4, 4.4
    for (a0, b0, a1, b1) in ((tx0 - 0.6, ty0 - 0.6, tx1 + 0.6, ty0 - 0.3), (tx0 - 0.6, ty0 - 0.3, tx0 - 0.3, ty1 + 0.6),
                             (tx1 + 0.3, ty0 - 0.3, tx1 + 0.6, ty1 + 0.6), (tx0 - 0.3, ty1 + 0.3, gx0, ty1 + 0.6), (gx1, ty1 + 0.3, tx1 + 0.3, ty1 + 0.6)):
        H.p("Glass").box(a0, b0, RZ, a1, b1, RZ + 3.6)
        H.p("Metal").box(a0 - 0.08, b0 - 0.08, RZ + 3.6, a1 + 0.08, b1 + 0.08, RZ + 3.9)
        H.col(a0, b0, RZ, a1, b1, RZ + 3.9, "guard")
    for (a0, b0, a1, b1) in ((tx0 - 0.6, ty0 - 0.7, tx1 + 0.6, ty0 - 0.6), (tx0 - 0.6, ty1 + 0.6, tx1 + 0.6, ty1 + 0.7),
                             (tx0 - 0.7, ty0 - 0.6, tx0 - 0.6, ty1 + 0.6), (tx1 + 0.6, ty0 - 0.6, tx1 + 0.7, ty1 + 0.6)):
        H.p("NeonBlue").box(a0, b0, TOP + 0.3, a1, b1, TOP + 0.7)
    # the BASE-jump platform: grated steel deck cantilevered 9 studs out over the street, side rails, open end,
    # hazard-striped lip and two diagonal struts back to the curtain wall
    jy0, jy1 = ty1 + 0.6, ty1 + 9.6
    H.p("Metal").box(gx0, jy0, RZ - 0.5, gx1, jy1, RZ)
    H.col(gx0, jy0, RZ - 0.5, gx1, jy1, RZ, "jump")
    for k in range(9):
        H.p("Hazard" if k % 2 == 0 else "Sign").box(gx0 + k * (gx1 - gx0) / 9, jy1 - 0.4, RZ - 0.5, gx0 + (k + 1) * (gx1 - gx0) / 9, jy1, RZ + 0.05)
    railing(H, gx0 + 0.15, jy0, gx0 + 0.15, jy1 - 0.4, RZ, height=3.6, spacing=0.8, kind="Metal")
    railing(H, gx1 - 0.15, jy0, gx1 - 0.15, jy1 - 0.4, RZ, height=3.6, spacing=0.8, kind="Metal")
    for x in (gx0 + 0.6, gx1 - 0.6):
        H.p("Metal").box(x - 0.5, ty1 + 0.08, RZ - 7.8, x + 0.5, ty1 + 0.7, RZ - 6.2)            # anchor plate on the wall
        beam(H, "Metal", (x, ty1 + 0.62, RZ - 7.0), (x, jy1 - 1.0, RZ - 0.5), 0.4, 0.4)
    H.notes["baseJump"] = [0.0, jy1 - 1.5, RZ]
    # ---- the crown: a mechanical room over the core, doors east and west onto the deck, louvers on the long
    # faces, roof, mast and aircraft light
    cx0, cx1, cy0, cy1 = -22.0, 22.0, -17.0, 17.0
    crown_doors = [(-3.0, 3.0, RZ, RZ + 9.0)]
    H.wall("y", cx0, -1, cy0 + T_IN, cy1 - T_IN, RZ, CZ1, crown_doors, outer_kind="Concrete")
    H.wall("y", cx1, 1, cy0 + T_IN, cy1 - T_IN, RZ, CZ1, crown_doors, outer_kind="Concrete")
    H.wall("x", cy0, -1, cx0 - T_OUT, cx1 + T_OUT, RZ, CZ1, [], outer_kind="Concrete")
    H.wall("x", cy1, 1, cx0 - T_OUT, cx1 + T_OUT, RZ, CZ1, [], outer_kind="Concrete")
    for x, hinge in ((cx0, True), (cx1, False)):
        H.door("y", x, -1 if x < 0 else 1, -3.0, 0.0, RZ, RZ + 9.0, glass=False, kind="roof")
        H.door("y", x, -1 if x < 0 else 1, 0.0, 3.0, RZ, RZ + 9.0, glass=False, hinge_at_u0=False, kind="roof")
    for k in range(12):
        z = RZ + 1.0 + k * 1.0
        H.p("Louver").box(cx0 + 3.0, cy0 - T_OUT - 0.35, z, cx1 - 3.0, cy0 - T_OUT, z + 0.35)
        H.p("Louver").box(cx0 + 3.0, cy1 + T_OUT, z, cx1 - 3.0, cy1 + T_OUT + 0.35, z + 0.35)
    H.p("Metal").box(cx0 - 0.6, cy0 - 0.6, CZ1, cx1 + 0.6, cy1 + 0.6, CZ1 + 0.6)
    H.col(cx0 - 0.6, cy0 - 0.6, CZ1, cx1 + 0.6, cy1 + 0.6, CZ1 + 0.6, "roof")
    H.p("Metal").box(-0.6, -0.6, CZ1 + 0.6, 0.6, 0.6, CZ1 + 26.0)
    H.p("NeonRed").box(-0.8, -0.8, CZ1 + 26.0, 0.8, 0.8, CZ1 + 27.2)
    for (x, y) in ((-16.0, 12.0), (16.0, 12.0)):
        roof_unit(H, x, y, RZ)
    # the roof gear locker (second parachute kiosk): steel counter on the crown's south wall, packs on pegs, sign
    lx, ly = -18.0, cy0 + T_IN
    H.p("Metal").box(lx - 2.6, ly, RZ, lx + 2.6, ly + 1.0, RZ + 3.4)
    H.p("Stone").box(lx - 2.7, ly, RZ + 3.4, lx + 2.7, ly + 1.2, RZ + 3.6)
    H.col(lx - 2.6, ly, RZ, lx + 2.6, ly + 1.2, RZ + 3.6, "furniture")
    H.p("Metal").box(lx - 2.6, ly, RZ + 3.6, lx + 2.6, ly + 0.3, RZ + 9.0)
    for px in (lx - 1.6, lx, lx + 1.6):
        H.p("Pack").box(px - 0.6, ly + 0.3, RZ + 4.0, px + 0.6, ly + 0.65, RZ + 5.6)
        H.p("Metal").box(px - 0.1, ly + 0.3, RZ + 5.6, px + 0.1, ly + 0.5, RZ + 5.8)
    H.p("Sign").box(lx - 2.4, ly + 0.3, RZ + 6.6, lx + 2.4, ly + 0.45, RZ + 8.6)
    neon_text(H, "NeonBlue", "SKY", lx, RZ + 6.9, ly + 0.45, 1, 1.4, standoff=0.25, tube=0.2)
    H.notes["aircraftLight"] = [0.0, 0.0, CZ1 + 26.6]
    H.notes["lights"] = [[-12.0, fo - 6.0, F + 12.5], [12.0, fo - 6.0, F + 12.5]]
    return H


meta = {}
builders = [deco_hotel, lambda: mid_rise("MidRiseBrick", "Brick", ["CAFE", "TACOS", "VINYL"]),
            lambda: mid_rise("MidRiseStucco", "Stucco", ["PIZZA", "BOOKS", "SALON"], awning="AwningB"), office_tower]
for fn in builders:
    reset()
    H = fn()
    meta[H.style] = export_house(H)
    scene, cam = setup_render()
    scene.render.resolution_x, scene.render.resolution_y = 1280, 900
    e = meta[H.style]["extents_studs"]
    hgt = e["z"][1]
    render_views(scene, cam, [H.style], {
        "front": ((-0.9 * hgt - 40, -1.3 * hgt - 60, hgt * 0.35 + 10), (0, 0, hgt * 0.42)),
        "street": ((-38, e["y"][0] - 42, 6.0), (6, e["y"][0], hgt * 0.30 if hgt < 120 else 60)),
        "back": ((0.9 * hgt + 40, 1.3 * hgt + 60, hgt * 0.35 + 10), (0, 0, hgt * 0.42)),
    }, "City_" + H.style)
with open(os.path.join(OUT, "city.json"), "w") as f:
    json.dump(meta, f)
print("NEONCOAST_DONE", json.dumps({k: {"max": v["maxTriangles"], "ext": v["extents_studs"]["z"], "colliders": len(v["colliders"])} for k, v in meta.items()}))
