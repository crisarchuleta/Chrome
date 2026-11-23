# nc_detail: small realism details shared by every house script (on top of nc_kit / nc_extra).
import math
import bmesh
from mathutils import Vector, Matrix
import nc_kit
from nc_kit import T_OUT, T_IN
from nc_extra import lantern, downspout

nc_kit.COLORS.update({"Screen": (0.25, 0.27, 0.28), "Mulch": (0.30, 0.20, 0.13), "Edging": (0.72, 0.70, 0.66), "Lamp": (1.0, 0.95, 0.80)})


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
    """Barrel caps along the four hips of a House.hip_roof called with the same numbers."""
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


def coach_lights(H, x0, x1, y_face, z):
    """A coach light each side of a garage door on a wall that faces -Y."""
    lantern(H, x0 - 1.4, y_face, z, facing=-1)
    lantern(H, x1 + 1.4, y_face, z, facing=-1)


def ac_unit(H, x, y):
    H.p("Foundation").box(x - 2.2, y - 2.2, 0, x + 2.2, y + 2.2, 0.35)
    H.p("Metal").box(x - 1.7, y - 1.7, 0.35, x + 1.7, y + 1.7, 3.2)
    H.p("Trim").box(x - 1.75, y - 1.75, 3.2, x + 1.75, y + 1.75, 3.35)
    H.p("Screen").box(x - 1.2, y - 1.2, 3.35, x + 1.2, y + 1.2, 3.4)
    H.col(x - 1.7, y - 1.7, 0, x + 1.7, y + 1.7, 3.35, "ac")
    H.notes.setdefault("ac", []).append([x, y, 2.0])


def meter(H, x_face, y, outward=-1):
    """Electric meter + disconnect on a side wall (wall at x = x_face, facing outward along X)."""
    def xs(p, q):
        return sorted((x_face + outward * p, x_face + outward * q))
    a, b = xs(0, 0.45)
    H.p("Metal").box(a, y - 0.55, 4.2, b, y + 0.55, 5.8)
    a, b = xs(0.45, 0.5)
    H.p("Glass").box(a, y - 0.35, 5.0, b, y + 0.35, 5.6)
    a, b = xs(0, 0.35)
    H.p("Metal").box(a, y + 1.0, 4.4, b, y + 1.9, 5.4)              # disconnect
    H.p("Metal").box(a, y - 0.12, 0.2, b, y + 0.12, 4.2)            # conduit down to the ground


def sconce(H, x, y_face, z):
    """Modern up/down wall light on a -Y facing wall."""
    H.p("Metal").box(x - 0.3, y_face - 0.5, z - 0.8, x + 0.3, y_face, z + 0.8)
    H.p("Lamp").box(x - 0.2, y_face - 0.45, z + 0.8, x + 0.2, y_face - 0.05, z + 0.85)
    H.p("Lamp").box(x - 0.2, y_face - 0.45, z - 0.85, x + 0.2, y_face - 0.05, z - 0.8)
    H.notes.setdefault("lights", []).append([x, y_face - 0.6, z])


def house_number(H, x, y_face, z, w=2.4):
    H.p("Metal").box(x - w / 2, y_face - 0.12, z - 0.45, x + w / 2, y_face, z + 0.45)
    H.notes["houseNumber"] = [x, y_face - 0.13, z]


def foundation_bed(H, x0, x1, y_face, depth=4.0, lip=0.75):
    """Mulch bed with a stone edge along a -Y facing wall (shrubs go in it). It starts at the foundation's face,
    `lip` in front of the wall (the foundation sticks out past the siding), so the mulch doesn't run into it."""
    y1 = y_face - lip
    H.p("Mulch").box(x0, y1 - depth, 0.0, x1, y1, 0.18)
    H.p("Edging").box(x0, y1 - depth - 0.35, 0.0, x1, y1 - depth, 0.4)
    H.notes.setdefault("beds", []).append({"min": [x0, y1 - depth], "max": [x1, y1]})


def gutters(H, x0, y0, x1, y1, zb, over, pitch=0.36, front_gaps=()):
    """K-style gutters along the front and back eaves of a hip roof (same numbers as the House.hip_roof call).
    front_gaps: x ranges where a lower roof (a porch) meets the eave, so the gutter stops either side of it."""
    ex0, ex1 = x0 - over, x1 + over
    z = zb - 0.25 - 0.55
    for (yy, s) in ((y0 - over, -1), (y1 + over, 1)):
        a, b = sorted((yy + s * 0.15, yy + s * 0.85))
        spans = [(ex0, ex1)]
        if s < 0:
            for (g0, g1) in front_gaps:
                spans = [p for (u0, u1) in spans for p in ((u0, min(u1, g0)), (max(u0, g1), u1)) if p[1] - p[0] > 0.3]
        for (u0, u1) in spans:
            H.p("Gutter").box(u0, a, z - 0.55, u1, b, z + 0.05)
            for u in (u0, u1):                                   # end caps
                H.p("Gutter").box(u - 0.05 if u == u0 else u - 0.0, a, z - 0.55, u + 0.0 if u == u0 else u + 0.05, b, z + 0.1)


DS_W, DS_D = 0.4, 0.32                          # a 3 x 4 in downspout at 1.15 studs per foot


def _kickout(H, dx, cy, sy, base):
    """Bottom of a downspout: a kick-out elbow over the foundation ledge and a splash block on the ground."""
    b0 = max(base, 0.12)                       # on the ground it sits on the splash block, not in it
    a, b = sorted((cy, cy + sy * 1.2))
    H.p("Gutter").box(dx - DS_W / 2, a, b0, dx + DS_W / 2, b, b0 + 0.35)
    a, b = sorted((cy + sy * 0.95, cy + sy * 2.35))
    H.p("Foundation").box(dx - 0.6, a, 0.0, dx + 0.6, b, 0.12)
    return b0


def wall_downspouts(H, corners, standoff=0.0):
    """Downspouts the way they're really hung: from the end of the eave gutter a gooseneck back to the wall, down
    the wall strapped to it (just in from the corner, clear of the corner boards), a kick-out at the bottom and a
    splash block. corners: (cx, cy, sx, sy, zb, over, base[, inset]) = the outside corner of the wall faces, which
    way is out in x and y, the eave height and overhang given to gutters(), what it stands on (foundation top or 0),
    and how far in from the corner it runs (default 0.9)."""
    for c in corners:
        cx, cy, sx, sy, zb, over, base = c[:7]
        inset = c[7] if len(c) > 7 else 0.9
        on_side = len(c) > 8 and c[8]
        # standoff: strapped out past a belly band / water table instead of running through it
        cx, cy = (cx + sx * standoff, cy) if on_side else (cx, cy + sy * standoff)
        gb = zb - 0.25 - 0.55 - 0.55            # gutter bottom (gutters() hangs it there)
        gy = cy + sy * (over + 0.5)             # under the gutter's middle
        if on_side:
            # the front/back wall is busy (shutters to the corner): drop from the gutter's end, run back along the
            # side wall's line and in to it, then down the side wall
            ox, wy_ = cx + sx * 0.55, cy - sy * inset
            H.p("Gutter").box(ox - 0.18, gy - 0.18, gb - 0.6, ox + 0.18, gy + 0.18, gb + 0.05)
            a, b = sorted((gy, wy_))
            H.p("Gutter").box(ox - 0.18, a - 0.18, gb - 0.6, ox + 0.18, b + 0.18, gb - 0.25)
            a, b = sorted((cx, ox))
            H.p("Gutter").box(a, wy_ - 0.18, gb - 0.6, b, wy_ + 0.18, gb - 0.25)
            b0 = max(base, 0.12)
            a, b = sorted((cx, cx + sx * 1.2))
            H.p("Gutter").box(a, wy_ - DS_W / 2, b0, b, wy_ + DS_W / 2, b0 + 0.35)
            a, b = sorted((cx + sx * 0.95, cx + sx * 2.35))
            H.p("Foundation").box(a, wy_ - 0.6, 0.0, b, wy_ + 0.6, 0.12)
            a, b = sorted((cx, cx + sx * DS_D))
            H.p("Gutter").box(a, wy_ - DS_W / 2, b0, b, wy_ + DS_W / 2, gb - 0.25)
            continue
        dx = cx - sx * inset
        H.p("Gutter").box(dx - 0.18, gy - 0.18, gb - 0.6, dx + 0.18, gy + 0.18, gb + 0.05)   # outlet
        a, b = sorted((cy, gy + sy * 0.18))
        H.p("Gutter").box(dx - 0.18, a, gb - 0.6, dx + 0.18, b, gb - 0.25)                   # gooseneck
        b0 = _kickout(H, dx, cy, sy, base)
        a, b = sorted((cy, cy + sy * DS_D))
        H.p("Gutter").box(dx - DS_W / 2, a, b0, dx + DS_W / 2, b, gb - 0.25)                 # down the wall


def scupper_downspouts(H, corners):
    """Flat roofs: a scupper through the parapet into a collector head, then the downspout down the wall.
    corners: (cx, cy, sx, sy, z_scupper, base)."""
    for (cx, cy, sx, sy, zs, base) in corners:
        dx = cx - sx * 0.9
        a, b = sorted((cy, cy + sy * 0.8))
        H.p("Metal").box(dx - 0.4, a, zs, dx + 0.4, b, zs + 0.4)                              # scupper
        a, b = sorted((cy, cy + sy * 0.9))
        H.p("Metal").box(dx - 0.45, a, zs - 1.0, dx + 0.45, b, zs)                           # collector head
        b0 = _kickout(H, dx, cy, sy, base)
        a, b = sorted((cy, cy + sy * DS_D))
        H.p("Gutter").box(dx - DS_W / 2, a, b0, dx + DS_W / 2, b, zs - 1.0)


def corner_downspouts(H, pts, z1):
    for (x, y) in pts:
        downspout(H, x, y, 0.15, z1)
        H.p("Foundation").box(x - 0.7, y - 0.7, 0.0, x + 0.7, y + 0.7, 0.12)  # splash block
