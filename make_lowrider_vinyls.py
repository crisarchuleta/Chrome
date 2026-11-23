# Neon Coast lowrider vinyls: draws the paint artwork as real decal images (transparent PNG), one per body panel.
#   python make_lowrider_vinyls.py            (any Python 3 with Pillow: pip install pillow)
# The images are printed onto the car's paint panels through their UVs (build_lowrider.py maps each panel exactly
# to the bounds below), so the art sits flush in the paint like real vinyl or airbrush work. Where an image is
# transparent, the candy paint shows through, so fades and lace blend into whatever colour the car is painted.
# Out: lowrider_vinyls/<livery>_<panel>.png  (+ lowrider_vinyls/sheet.png, a contact sheet to look them over)
# Every design is original and clean: flames, pinstripe scrolls, masking-tape patterns, lace, a sunset with palms.
import os, math, random
from PIL import Image, ImageDraw, ImageFilter, ImageChops

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(os.environ.get("NC_OUT", HERE), "lowrider_vinyls")
os.makedirs(OUT, exist_ok=True)
SS = 2  # supersampling for clean edges

# panel bounds in Blender studs (must match PANELS in build_lowrider.py). Image top / left:
#   side  : u = front (y = y0) -> rear,  v = top of the car (z = z1) -> bottom      (both sides share it, mirrored)
#   hood  : u = car's left (x = +x1) -> right, v = front (y = y0) -> windshield   (as seen standing in front looking back... top = front)
#   trunk : same orientation as the hood (top = towards the cab), roof too
PANELS = {
    "side": {"a": (-10.5, 10.5), "b": (0.65, 2.95), "px": (2048, 224)},
    "hood": {"a": (-3.85, 3.85), "b": (-10.4, -2.7), "px": (1024, 1024)},
    "trunk": {"a": (-3.2, 3.2), "b": (6.0, 9.85), "px": (1024, 616)},
    "roof": {"a": (-3.1, 3.1), "b": (-0.85, 3.4), "px": (1024, 702)},
}

GOLD = (236, 190, 72, 255)
GOLD_DARK = (150, 104, 24, 255)
TEAL = (24, 210, 214, 255)
MAGENTA = (232, 40, 150, 255)
WHITE = (255, 255, 255, 255)


class Canvas:
    """drawing in studs: side -> (y, z), top panels -> (x, y)"""

    def __init__(self, panel):
        self.p = PANELS[panel]
        self.panel = panel
        self.w, self.h = self.p["px"][0] * SS, self.p["px"][1] * SS
        self.img = Image.new("RGBA", (self.w, self.h), (0, 0, 0, 0))

    def px(self, a, b):
        (a0, a1), (b0, b1) = self.p["a"], self.p["b"]
        if self.panel == "side":           # a = y (front -> rear = left -> right), b = z (top = up)
            return ((a - a0) / (a1 - a0) * self.w, (b1 - b) / (b1 - b0) * self.h)
        # top panels: a = x (car's left +x at image left), b = y (front at image top)
        return ((a1 - a) / (a1 - a0) * self.w, (b - b0) / (b1 - b0) * self.h)

    def scale(self):                        # pixels per stud
        (a0, a1) = self.p["a"]
        return self.w / (a1 - a0)

    def layer(self):
        return Image.new("RGBA", (self.w, self.h), (0, 0, 0, 0))

    def over(self, im):
        self.img = Image.alpha_composite(self.img, im)

    def save(self, name):
        im = self.img.resize(self.p["px"], Image.LANCZOS)
        path = os.path.join(OUT, name + ".png")
        im.save(path)
        return path


def bez(p0, p1, p2, p3=None, n=24):
    pts = []
    for k in range(n + 1):
        t = k / n
        if p3 is None:
            x = (1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * p1[0] + t * t * p2[0]
            y = (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * p1[1] + t * t * p2[1]
        else:
            x = (1 - t) ** 3 * p0[0] + 3 * (1 - t) ** 2 * t * p1[0] + 3 * (1 - t) * t * t * p2[0] + t ** 3 * p3[0]
            y = (1 - t) ** 3 * p0[1] + 3 * (1 - t) ** 2 * t * p1[1] + 3 * (1 - t) * t * t * p2[1] + t ** 3 * p3[1]
        pts.append((x, y))
    return pts


def stroke(cv, pts, width_studs, color, im=None):
    d = ImageDraw.Draw(im if im is not None else cv.img)
    w = max(1, int(width_studs * cv.scale()))
    P = [cv.px(*p) for p in pts]
    d.line(P, fill=color, width=w, joint="curve")
    r = w / 2
    for q in (P[0], P[-1]):
        d.ellipse((q[0] - r, q[1] - r, q[0] + r, q[1] + r), fill=color)


def pinstripe(cv, pts, color=GOLD, w=0.04, shadow=True):
    """a hand-pulled pinstripe: a thin line with a fine darker edge"""
    if shadow:
        stroke(cv, pts, w * 1.7, (0, 0, 0, 90))
    stroke(cv, pts, w, color)


def mirror_x(pts):
    return [(-x, y) for (x, y) in pts]


def scroll(cx, cy, r, turns=1.4, sx=1, sy=1, n=60):
    """a spiral curl, the basic pinstriper's stroke"""
    out = []
    for k in range(n + 1):
        t = k / n
        a = t * turns * 2 * math.pi
        rr = r * (1 - 0.82 * t)
        out.append((cx + sx * rr * math.cos(a), cy + sy * rr * math.sin(a)))
    return out


# --------------------------------------------------------------------------------------------- flames
def flame_mask(cv, root_pts, licks):
    """root_pts: polygon of the solid root (studs); licks: curved tapered tongues, either
    (base_a, base_b, ctrl, tip) or (base_a, base_b, ctrl1, ctrl2, tip) for an S-shaped lick"""
    m = Image.new("L", (cv.w, cv.h), 0)
    d = ImageDraw.Draw(m)
    d.polygon([cv.px(*p) for p in root_pts], fill=255)
    for lk in licks:
        if len(lk) == 4:
            ba, bb, c, tip = lk
            side1 = bez(ba, c, tip, n=30)
            cb = (c[0] + (bb[0] - ba[0]) * 0.35, c[1] + (bb[1] - ba[1]) * 0.35)
            side2 = bez(tip, cb, bb, n=30)
        else:
            ba, bb, c1, c2, tip = lk
            off = ((bb[0] - ba[0]), (bb[1] - ba[1]))
            side1 = bez(ba, c1, c2, tip, n=40)
            side2 = bez(tip, (c2[0] + off[0] * 0.3, c2[1] + off[1] * 0.3), (c1[0] + off[0] * 0.75, c1[1] + off[1] * 0.75), bb, n=40)
        d.polygon([cv.px(*p) for p in side1 + side2], fill=255)
    return m.filter(ImageFilter.GaussianBlur(SS * 0.6)).point(lambda v: 255 if v > 127 else 0)


def gradient_fill(cv, mask, stops, axis_from, axis_to):
    """colour the mask with a gradient running from point axis_from to axis_to (studs)"""
    x0, y0 = cv.px(*axis_from)
    x1, y1 = cv.px(*axis_to)
    dx, dy = x1 - x0, y1 - y0
    L2 = dx * dx + dy * dy
    g = Image.new("RGBA", (cv.w, cv.h))
    # build on a small grid and scale up (fast)
    sw, sh = max(2, cv.w // 8), max(2, cv.h // 8)
    small = Image.new("RGBA", (sw, sh))
    px = small.load()
    for j in range(sh):
        for i in range(sw):
            X, Y = i * cv.w / sw, j * cv.h / sh
            t = max(0.0, min(1.0, ((X - x0) * dx + (Y - y0) * dy) / L2))
            for k in range(len(stops) - 1):
                if stops[k][0] <= t <= stops[k + 1][0]:
                    a, b = stops[k], stops[k + 1]
                    u = (t - a[0]) / max(1e-6, b[0] - a[0])
                    px[i, j] = tuple(int(a[1][c] + (b[1][c] - a[1][c]) * u) for c in range(4))
                    break
    g = small.resize((cv.w, cv.h), Image.BILINEAR)
    out = Image.new("RGBA", (cv.w, cv.h), (0, 0, 0, 0))
    out.paste(g, (0, 0), mask)
    return out


def outline(cv, mask, w_studs, color):
    w = max(3, int(w_studs * cv.scale()) | 1)
    grown = mask.filter(ImageFilter.MaxFilter(w))
    ring = ImageChops.subtract(grown, mask)
    out = Image.new("RGBA", (cv.w, cv.h), (0, 0, 0, 0))
    out.paste(Image.new("RGBA", (cv.w, cv.h), color), (0, 0), ring)
    return out


def flames_side(cv, stops, edge):
    # a solid root over the front fender, then wavy tongues licking back along the door
    root = [(-10.5, 2.8), (-8.9, 2.8), (-8.2, 2.5), (-8.0, 2.0), (-8.3, 1.5), (-8.9, 1.15), (-10.5, 1.1)]
    licks = [
        ((-9.2, 2.8), (-8.4, 2.55), (-6.6, 3.0), (-4.2, 2.35), (-1.2, 2.75)),
        ((-8.4, 2.55), (-8.05, 2.2), (-6.2, 2.75), (-3.4, 1.95), (0.9, 2.3)),
        ((-8.05, 2.2), (-8.05, 1.85), (-6.0, 2.35), (-3.8, 1.6), (-0.6, 1.95)),
        ((-8.1, 1.85), (-8.3, 1.5), (-6.4, 1.95), (-4.6, 1.25), (-2.2, 1.55)),
        ((-8.4, 1.5), (-9.0, 1.15), (-7.2, 1.45), (-5.8, 1.0), (-4.0, 1.2)),
    ]
    m = flame_mask(cv, root, licks)
    cv.over(outline(cv, m, 0.06, edge))
    cv.over(gradient_fill(cv, m, stops, (-10.5, 2.0), (0.9, 2.0)))


def flames_hood(cv, stops, edge):
    root = [(3.85, -10.4), (-3.85, -10.4), (-3.85, -9.3), (3.85, -9.3)]
    licks = []
    for s in (-1, 1):
        licks += [
            ((s * 3.85, -9.5), (s * 2.9, -9.4), (s * 4.0, -8.0), (s * 2.9, -6.0), (s * 3.4, -4.0)),
            ((s * 2.9, -9.4), (s * 1.9, -9.4), (s * 3.0, -7.6), (s * 1.6, -5.4), (s * 2.3, -3.1)),
            ((s * 1.9, -9.4), (s * 0.9, -9.4), (s * 2.0, -8.0), (s * 0.8, -6.6), (s * 1.3, -4.8)),
            ((s * 0.9, -9.4), (s * 0.0, -9.4), (s * 1.0, -8.3), (s * 0.1, -7.4), (s * 0.4, -6.2)),
        ]
    m = flame_mask(cv, root, licks)
    cv.over(outline(cv, m, 0.06, edge))
    cv.over(gradient_fill(cv, m, stops, (0, -10.4), (0, -3.2)))


HOT = [(0.0, (255, 246, 160, 255)), (0.25, (255, 200, 40, 255)), (0.6, (255, 110, 10, 255)), (1.0, (205, 20, 10, 255))]
COLD = [(0.0, (240, 255, 255, 255)), (0.3, (90, 235, 240, 255)), (0.7, (20, 120, 230, 255)), (1.0, (70, 20, 160, 255))]


# --------------------------------------------------------------------------------------------- lace + patterns
def lace(cv, region_mask, color, cell=0.42, alpha=150):
    """procedural lace: rosettes of petals and rings on a grid, clipped to region_mask"""
    im = cv.layer()
    d = ImageDraw.Draw(im)
    s = cv.scale()
    c = cell * s
    lw = max(1, int(0.022 * s))
    col = color[:3] + (alpha,)
    y = 0.0
    row = 0
    while y < cv.h + c:
        x = (c / 2) if row % 2 else 0.0
        while x < cv.w + c:
            r = c * 0.42
            d.ellipse((x - r, y - r, x + r, y + r), outline=col, width=lw)
            r2 = c * 0.16
            d.ellipse((x - r2, y - r2, x + r2, y + r2), outline=col, width=lw)
            for k in range(8):
                a = k * math.pi / 4
                px, py = x + math.cos(a) * r * 0.62, y + math.sin(a) * r * 0.62
                pr = c * 0.11
                d.ellipse((px - pr, py - pr, px + pr, py + pr), outline=col, width=lw)
            x += c
        y += c * 0.87
        row += 1
    out = cv.layer()
    out.paste(im, (0, 0), ImageChops.multiply(region_mask, im.getchannel("A")))
    return out


def rect_mask(cv, a0, b0, a1, b1, radius=0.12):
    m = Image.new("L", (cv.w, cv.h), 0)
    p0, p1 = cv.px(a0, b0), cv.px(a1, b1)
    box = (min(p0[0], p1[0]), min(p0[1], p1[1]), max(p0[0], p1[0]), max(p0[1], p1[1]))
    ImageDraw.Draw(m).rounded_rectangle(box, radius=int(radius * cv.scale()), fill=255)
    return m


def fade(cv, mask, c0, c1, a_from, a_to):
    return gradient_fill(cv, mask, [(0, c0), (1, c1)], a_from, a_to)


def tape_frame(cv, a0, b0, a1, b1, color=GOLD, w=0.035, radius=0.12):
    m = rect_mask(cv, a0, b0, a1, b1, radius)
    cv.over(outline(cv, m, w, color))


def diamonds(cv, a0, a1, bc, n, half_h, color, half_w=None):
    d = ImageDraw.Draw(cv.img)
    step = (a1 - a0) / n
    hw = half_w or step * 0.32
    for k in range(n):
        ac = a0 + step * (k + 0.5)
        pts = [cv.px(ac - hw, bc), cv.px(ac, bc + half_h), cv.px(ac + hw, bc), cv.px(ac, bc - half_h)]
        d.polygon(pts, fill=color)
        inner = [cv.px(ac - hw * 0.45, bc), cv.px(ac, bc + half_h * 0.45), cv.px(ac + hw * 0.45, bc), cv.px(ac, bc - half_h * 0.45)]
        d.polygon(inner, fill=GOLD)


def patterns_side(cv, scheme):
    c0, c1, lacecol, dia = scheme
    # the long panel between the wheels, under the side spear
    a0, a1, b0, b1 = -4.5, 3.9, 1.3, 2.02
    m = rect_mask(cv, a0, b0, a1, b1, 0.1)
    cv.over(fade(cv, m, c0, c1, (a0, 1.6), (a1, 1.6)))
    cv.over(lace(cv, m, lacecol, cell=0.34))
    diamonds(cv, a0 + 0.3, a1 - 0.3, (b0 + b1) / 2, 7, 0.27, dia)
    tape_frame(cv, a0, b0, a1, b1)
    tape_frame(cv, a0 - 0.12, b0 - 0.12, a1 + 0.12, b1 + 0.12, w=0.025)
    # fender spears front and rear above the spear line
    for (s0, s1) in ((-10.1, -8.0), (8.0, 10.1)):
        m2 = rect_mask(cv, s0, 2.28, s1, 2.5, 0.1)
        cv.over(fade(cv, m2, c0, c1, (s0, 2.4), (s1, 2.4)))
        tape_frame(cv, s0, 2.28, s1, 2.5, w=0.025)
    pinstripe(cv, [(-4.4, 2.32), (3.8, 2.32)], w=0.03)


def patterns_top(cv, scheme, a0, b0, a1, b1, n=3):
    c0, c1, lacecol, dia = scheme
    m = rect_mask(cv, a0, b0, a1, b1, 0.3)
    cv.over(fade(cv, m, c1, c0, (0, b0), (0, b1)))
    cv.over(lace(cv, m, lacecol, cell=0.5))
    tape_frame(cv, a0, b0, a1, b1, radius=0.3)
    tape_frame(cv, a0 + 0.15, b0 + 0.15, a1 - 0.15, b1 - 0.15, w=0.025, radius=0.22)
    d = ImageDraw.Draw(cv.img)
    for k in range(n):                     # a row of diamonds down the middle
        bc = b0 + (b1 - b0) * (k + 0.5) / n
        hw, hh = 0.32, (b1 - b0) / n * 0.32
        d.polygon([cv.px(0 - hw, bc), cv.px(0, bc - hh), cv.px(0 + hw, bc), cv.px(0, bc + hh)], fill=dia)
        d.polygon([cv.px(-hw * 0.4, bc), cv.px(0, bc - hh * 0.4), cv.px(hw * 0.4, bc), cv.px(0, bc + hh * 0.4)], fill=GOLD)


# --------------------------------------------------------------------------------------------- pinstripe sets
def pin_hood(cv, color=GOLD):
    """a centre spear with mirrored branches ending in curls (open strokes only)"""
    pinstripe(cv, [(0, -9.9), (0, -4.0)], color)
    d = ImageDraw.Draw(cv.img)
    for (yc, hh) in ((-9.9, 0.22), (-4.0, 0.3)):                      # diamond tips on the spear
        d.polygon([cv.px(-0.12, yc), cv.px(0, yc - hh), cv.px(0.12, yc), cv.px(0, yc + hh)], fill=color)
    for s in (-1, 1):
        # branch 1: short, near the grille, curls back
        pinstripe(cv, bez((0, -9.3), (s * 0.7, -9.5), (s * 1.3, -9.2), (s * 1.45, -8.7)), color)
        pinstripe(cv, scroll(s * 1.2, -8.55, 0.28, 1.3, sx=s, sy=-1), color)
        # branch 2: long sweep out towards the fenders
        pinstripe(cv, bez((0, -8.0), (s * 1.2, -8.4), (s * 2.6, -8.0), (s * 2.9, -6.9)), color)
        pinstripe(cv, scroll(s * 2.55, -6.7, 0.38, 1.35, sx=s, sy=-1), color)
        # branch 3: dips back in with a teardrop curl
        pinstripe(cv, bez((0, -6.6), (s * 0.9, -6.9), (s * 1.8, -6.3), (s * 1.7, -5.3)), color)
        pinstripe(cv, scroll(s * 1.4, -5.2, 0.3, 1.3, sx=s, sy=-1), color)
        # branch 4: small flick by the cowl
        pinstripe(cv, bez((0, -4.9), (s * 0.6, -4.9), (s * 1.0, -4.5), (s * 0.95, -4.0)), color)
        pinstripe(cv, scroll(s * 0.75, -3.95, 0.2, 1.2, sx=s, sy=-1), color)
        # loose accent flicks
        pinstripe(cv, bez((s * 3.1, -9.6), (s * 3.4, -9.0), (s * 3.2, -8.5)), color, w=0.03)
        pinstripe(cv, bez((s * 2.4, -4.6), (s * 2.9, -4.2), (s * 3.3, -4.3)), color, w=0.03)


def pin_side(cv, color=GOLD):
    pinstripe(cv, [(-9.7, 2.36), (9.6, 2.36)], color, w=0.03)
    pinstripe(cv, [(-9.4, 2.27), (9.3, 2.27)], color, w=0.022)
    pinstripe(cv, scroll(-9.75, 2.5, 0.16, 1.2, sx=-1), color, w=0.03)
    pinstripe(cv, scroll(9.65, 2.5, 0.16, 1.2), color, w=0.03)


def pin_trunk(cv, color=GOLD):
    for s in (-1, 1):
        pinstripe(cv, bez((s * 0.1, 9.6), (s * 2.4, 9.7), (s * 2.9, 8.2), (s * 2.0, 7.6)), color)
        pinstripe(cv, scroll(s * 2.2, 8.2, 0.45, 1.3, sx=s), color)
        pinstripe(cv, bez((s * 0.1, 6.3), (s * 1.6, 6.1), (s * 2.0, 7.0), (s * 1.2, 7.3)), color)
    pinstripe(cv, [(0, 6.4), (0, 7.0)], color)


def pin_roof(cv, color=GOLD):
    for sx in (-1, 1):
        for sy in (-1, 1):
            cx, cy = sx * 2.5, 1.27 + sy * 1.65
            pinstripe(cv, bez((cx, cy), (cx - sx * 0.9, cy), (cx - sx * 1.2, cy - sy * 0.6)), color)
            pinstripe(cv, scroll(cx - sx * 0.35, cy - sy * 0.35, 0.28, 1.2, sx=-sx, sy=-sy), color)


# --------------------------------------------------------------------------------------------- mural
def mural_trunk(cv):
    cx, cy, rx, ry = 0.0, 7.92, 2.75, 1.62
    m = Image.new("L", (cv.w, cv.h), 0)
    p0, p1 = cv.px(cx + rx, cy - ry), cv.px(cx - rx, cy + ry)
    ImageDraw.Draw(m).ellipse((min(p0[0], p1[0]), min(p0[1], p1[1]), max(p0[0], p1[0]), max(p0[1], p1[1])), fill=255)
    # sky: top of the oval (towards the cab) is the high sky
    cv.over(gradient_fill(cv, m, [(0, (60, 20, 110, 255)), (0.35, (200, 40, 130, 255)), (0.62, (255, 120, 60, 255)), (0.75, (255, 200, 80, 255)), (1.0, (255, 200, 80, 255))], (0, cy - ry), (0, cy + 0.5)))
    horizon = cy + 0.45
    # sun with stripe cuts
    sun = cv.layer()
    d = ImageDraw.Draw(sun)
    sr = 0.95
    a, b = cv.px(sr, horizon - sr), cv.px(-sr, horizon + sr)
    d.ellipse((min(a[0], b[0]), min(a[1], b[1]), max(a[0], b[0]), max(a[1], b[1])), fill=(255, 226, 90, 255))
    for k in range(5):
        y = horizon - 0.08 - k * 0.17
        hh = 0.03 + 0.012 * (4 - k)
        q0, q1 = cv.px(sr + 0.1, y - hh), cv.px(-sr - 0.1, y + hh)
        d.rectangle((min(q0[0], q1[0]), min(q0[1], q1[1]), max(q0[0], q1[0]), max(q0[1], q1[1])), fill=(0, 0, 0, 0))
    hcut = Image.new("L", (cv.w, cv.h), 0)
    h0, h1 = cv.px(cx + rx, cy - ry), cv.px(cx - rx, horizon)
    ImageDraw.Draw(hcut).rectangle((min(h0[0], h1[0]), min(h0[1], h1[1]), max(h0[0], h1[0]), max(h0[1], h1[1])), fill=255)
    clip = ImageChops.multiply(ImageChops.multiply(m, hcut), sun.getchannel("A"))
    s2 = cv.layer()
    s2.paste(sun, (0, 0), clip)
    cv.over(s2)
    # sea below the horizon with light streaks
    sea = Image.new("L", (cv.w, cv.h), 0)
    s0, s1 = cv.px(cx + rx, horizon), cv.px(cx - rx, cy + ry)
    ImageDraw.Draw(sea).rectangle((min(s0[0], s1[0]), min(s0[1], s1[1]), max(s0[0], s1[0]), max(s0[1], s1[1])), fill=255)
    sea = ImageChops.multiply(sea, m)
    cv.over(gradient_fill(cv, sea, [(0, (20, 170, 200, 255)), (1, (10, 60, 120, 255))], (0, horizon), (0, cy + ry)))
    for k in range(6):
        y = horizon + 0.12 + k * 0.2
        w = 0.9 - k * 0.1
        stroke(cv, [(-w, y), (w, y)], 0.05, (255, 210, 120, 200))
    # palms (silhouettes), kept inside the frame
    PALM = (24, 12, 30, 255)
    base_img = cv.img
    cv.img = cv.layer()
    for (bx, lean, h) in ((-1.75, 0.5, 2.0), (1.95, -0.45, 1.7)):
        base = (bx, cy + ry - 0.15)
        top = (bx + lean, base[1] - h)
        trunk = bez(base, (bx + lean * 0.2, base[1] - h * 0.5), top, n=20)
        for k in range(len(trunk) - 1):
            w = 0.16 - 0.08 * k / len(trunk)
            stroke(cv, [trunk[k], trunk[k + 1]], w, PALM)
        for k in range(7):
            ang = math.pi * (-0.05 + k * 0.18)
            tip = (top[0] + 1.0 * math.cos(ang + math.pi), top[1] - 0.55 * math.sin(ang) + 0.35)
            mid = ((top[0] + tip[0]) / 2, top[1] - 0.35)
            fr = bez(top, mid, tip, n=16)
            for j in range(len(fr) - 1):
                w = 0.13 * (1 - j / len(fr)) + 0.02
                stroke(cv, [fr[j], fr[j + 1]], w, PALM)
    palms = cv.img
    cv.img = base_img
    clipped = cv.layer()
    clipped.paste(palms, (0, 0), ImageChops.multiply(m, palms.getchannel("A")))
    cv.over(clipped)
    # double gold frame + scrolls at the ends
    cv.over(outline(cv, m, 0.06, GOLD))
    big = Image.new("L", (cv.w, cv.h), 0)
    q0, q1 = cv.px(cx + rx + 0.14, cy - ry - 0.14), cv.px(cx - rx - 0.14, cy + ry + 0.14)
    ImageDraw.Draw(big).ellipse((min(q0[0], q1[0]), min(q0[1], q1[1]), max(q0[0], q1[0]), max(q0[1], q1[1])), fill=255)
    cv.over(outline(cv, big, 0.03, GOLD))
    for s in (-1, 1):
        pinstripe(cv, scroll(s * (rx + 0.25), cy, 0.22, 1.25, sx=s), GOLD, w=0.035)


# --------------------------------------------------------------------------------------------- liveries
PATTERNS_GOLD = ((232, 40, 150, 230), (232, 40, 150, 0), (255, 255, 255, 255), TEAL)
PATTERNS_PURPLE = ((110, 30, 190, 240), (255, 80, 200, 0), (255, 220, 250, 255), (255, 80, 200, 255))


def make():
    made = {}

    def emit(livery, panel, fn):
        cv = Canvas(panel)
        fn(cv)
        made.setdefault(livery, {})[panel] = cv.save(f"{livery}_{panel}")

    emit("pinstripe", "hood", pin_hood)
    emit("pinstripe", "side", pin_side)
    emit("pinstripe", "trunk", pin_trunk)
    emit("pinstripe", "roof", pin_roof)

    emit("flames", "hood", lambda cv: flames_hood(cv, HOT, (40, 110, 255, 255)))
    emit("flames", "side", lambda cv: (flames_side(cv, HOT, (40, 110, 255, 255)), pinstripe(cv, [(4.6, 2.36), (9.6, 2.36)], w=0.03)))
    emit("flames", "trunk", lambda cv: pin_trunk(cv, (40, 110, 255, 255)))

    emit("flames_teal", "hood", lambda cv: flames_hood(cv, COLD, (190, 60, 255, 255)))
    emit("flames_teal", "side", lambda cv: flames_side(cv, COLD, (190, 60, 255, 255)))
    emit("flames_teal", "trunk", lambda cv: pin_trunk(cv, (190, 60, 255, 255)))

    emit("patterns", "side", lambda cv: patterns_side(cv, PATTERNS_GOLD))
    emit("patterns", "hood", lambda cv: patterns_top(cv, PATTERNS_GOLD, -1.4, -9.8, 1.4, -3.4, 4))
    emit("patterns", "trunk", lambda cv: patterns_top(cv, PATTERNS_GOLD, -2.6, 6.35, 2.6, 9.5, 2))
    emit("patterns", "roof", lambda cv: patterns_top(cv, PATTERNS_GOLD, -2.7, -0.5, 2.7, 3.05, 3))

    emit("mural", "trunk", mural_trunk)
    emit("mural", "hood", pin_hood)
    emit("mural", "side", pin_side)

    emit("showcar", "side", lambda cv: patterns_side(cv, PATTERNS_GOLD))
    emit("showcar", "hood", lambda cv: (patterns_top(cv, PATTERNS_GOLD, -0.9, -9.8, 0.9, -3.4, 4), pin_hood(cv)))
    emit("showcar", "trunk", mural_trunk)
    emit("showcar", "roof", lambda cv: patterns_top(cv, PATTERNS_GOLD, -2.7, -0.5, 2.7, 3.05, 3))

    emit("purple_lace", "side", lambda cv: patterns_side(cv, PATTERNS_PURPLE))
    emit("purple_lace", "hood", lambda cv: (patterns_top(cv, PATTERNS_PURPLE, -0.9, -9.8, 0.9, -3.4, 4), pin_hood(cv)))
    emit("purple_lace", "trunk", lambda cv: patterns_top(cv, PATTERNS_PURPLE, -2.6, 6.35, 2.6, 9.5, 2))
    emit("purple_lace", "roof", lambda cv: patterns_top(cv, PATTERNS_PURPLE, -2.7, -0.5, 2.7, 3.05, 3))

    # contact sheet over a candy red, to look them over
    rows = []
    for liv, panels in made.items():
        for pan, path in panels.items():
            rows.append((liv, pan, path))
    W = 1024
    tiles = []
    for liv, pan, path in rows:
        im = Image.open(path)
        sc = W / im.width if pan == "side" else 320 / im.height
        im = im.resize((int(im.width * sc), int(im.height * sc)))
        bg = Image.new("RGBA", im.size, (150, 8, 24, 255))
        tiles.append(Image.alpha_composite(bg, im))
    H = sum(t.height + 8 for t in tiles)
    sheet = Image.new("RGBA", (W, H), (30, 30, 34, 255))
    y = 0
    for t in tiles:
        sheet.paste(t, (0, y))
        y += t.height + 8
    sheet.convert("RGB").save(os.path.join(OUT, "sheet.png"))
    return made


if __name__ == "__main__":
    m = make()
    print("NEONCOAST_VINYLS", sum(len(v) for v in m.values()), "images in", OUT)
