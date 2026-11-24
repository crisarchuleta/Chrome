"""motifs2.py: more original, PG tattoo motifs."""
import math
import numpy as np
from inkcore import *
from motifs import *


def _shade_fill(m, d, geom, light=(-0.4, -0.5), dark=0.85, color=None, color2=None, op_ink=None):
    """fill a shape with a body-shading gradient: light toward `light`, dark on the far side"""
    minx, miny, maxx, maxy = geom.bounds
    cx, cy = (minx + maxx) / 2, (miny + maxy) / 2
    r = max(maxx - minx, maxy - miny) * 0.75
    gdef, gurl = radial(cx + light[0] * r, cy + light[1] * r, r * 1.6, [(0, 0.0), (0.35, 0.05), (0.75, dark * 0.6), (1, dark)])
    m.defs.append(gdef)
    svg = ""
    if color:
        if color2:
            cdef, curl = radial(cx + light[0] * r, cy + light[1] * r, r * 1.6, [(0, 1, color2), (1, 1, color)])
            m.defs.append(cdef)
            svg += fill(d, curl, 0.92)
        else:
            svg += fill(d, color, 0.9)
    svg += fill(d, gurl, op_ink if op_ink is not None else (1.0 if not color else 0.55))
    return svg


# ================================================================ clock
def clock(rng, R=230, color=None):
    m = Motif()
    outer = Point(0, 0).buffer(R, 96)
    svg = _shade_fill(m, d_geom(outer), outer, dark=0.9, color=GOLD if color else None, color2=GOLD2 if color else None)
    svg += line(d_geom(outer), 6)
    face = Point(0, 0).buffer(R * 0.84, 96)
    gdef, gurl = radial(-R * 0.3, -R * 0.3, R * 1.2, [(0, 0.0), (0.6, 0.05), (1, 0.55)])
    m.defs.append(gdef)
    svg += fill(d_geom(face), gurl, 1.0) + line(d_geom(face), 4)
    numer = ["XII", "I", "II", "III", "IIII", "V", "VI", "VII", "VIII", "IX", "X", "XI"]
    for i, nm in enumerate(numer):
        a = math.radians(-90 + i * 30)
        x, y = R * 0.68 * math.cos(a), R * 0.68 * math.sin(a)
        svg += text(nm, x, y + R * 0.05, R * 0.15, "CinzelDecorative", extra=f'transform="rotate({i * 30} {f2(x)} {f2(y)})" font-weight="700"')
    for i in range(60):
        a = math.radians(i * 6)
        r1 = R * (0.8 if i % 5 else 0.77)
        svg += line(f"M{f2(r1 * math.cos(a))},{f2(r1 * math.sin(a))} L{f2(R * 0.83 * math.cos(a))},{f2(R * 0.83 * math.sin(a))}", 2.2 if i % 5 else 3.5)
    hh, mm = rng.integers(1, 12), rng.integers(0, 12) * 5
    for ang, Ln, wd in ((hh * 30 + mm * 0.5, 0.42, 9), (mm * 6, 0.62, 6)):
        a = math.radians(ang - 90)
        tip = (R * Ln * math.cos(a), R * Ln * math.sin(a))
        nrm = (-math.sin(a) * wd, math.cos(a) * wd)
        hp = [(-R * 0.08 * math.cos(a), -R * 0.08 * math.sin(a)), (tip[0] * 0.55 + nrm[0], tip[1] * 0.55 + nrm[1]), tip, (tip[0] * 0.55 - nrm[0], tip[1] * 0.55 - nrm[1])]
        svg += fill(d_poly(hp), INK, 0.95)
    svg += fill(d_geom(Point(0, 0).buffer(R * 0.05)), INK)
    cr = box(-R * 0.1, -R * 1.17, R * 0.1, -R * 0.98)
    ring = Point(0, -R * 1.27).buffer(R * 0.13).difference(Point(0, -R * 1.27).buffer(R * 0.07))
    top = unary_union([cr, ring])
    svg2 = _shade_fill(m, d_geom(top), top, color=GOLD if color else None) + line(d_geom(cr), 4) + line(d_geom(Point(0, -R * 1.27).buffer(R * 0.13)), 4) + line(d_geom(Point(0, -R * 1.27).buffer(R * 0.07)), 4)
    m.add(svg2, top)
    m.add(svg, outer)
    return m


# ================================================================ rosary
def rosary(rng, L=900, beads=26, sway=120, cross=True, color=None):
    m = Motif()
    t = np.linspace(0, 1, beads)
    x = sway * np.sin(t * math.pi * 1.3 + rng.uniform(0, 1)) * (1 - t * 0.3)
    y = -L / 2 + L * t
    for i in range(1, beads):
        m.add(line(f"M{f2(x[i - 1])},{f2(y[i - 1])} L{f2(x[i])},{f2(y[i])}", 3, 0.95), None)
    for i in range(beads):
        r = 16 if i % 10 else 22
        c = Point(x[i], y[i]).buffer(r, 32)
        svg = _shade_fill(m, d_geom(c), c, dark=0.95, color=color) + line(d_geom(c), 3.5)
        m.add(svg, c)
    if cross:
        cx, cy = x[-1], y[-1] + 95
        a, b_ = 22, 85
        cr = unary_union([box(cx - a, cy - b_ * 0.9, cx + a, cy + b_ * 1.25), box(cx - b_ * 0.62, cy - b_ * 0.45, cx + b_ * 0.62, cy - b_ * 0.45 + 2 * a)])
        svg = _shade_fill(m, d_geom(cr), cr, dark=0.95, color=GOLD if color else None) + line(d_geom(cr), 4.5)
        m.add(line(f"M{f2(x[-1])},{f2(y[-1])} L{f2(cx)},{f2(cy - b_ * 0.9)}", 3), None)
        m.add(svg, cr)
    return m


# ================================================================ masks (smile now, cry later)
def drama_mask(rng, happy=True, s=1.0, color=None):
    m = Motif()
    W, H = 190 * s, 250 * s
    face = path_pts([((0, -H), (W * 1.1, -H), (W * 1.05, H * 0.2), (0, H)), ((0, H), (-W * 1.05, H * 0.2), (-W * 1.1, -H), (0, -H))])
    fg = poly(face)
    svg = _shade_fill(m, d_poly(face), fg, light=(-0.3, -0.6), dark=0.8, color=color)
    eyes = []
    for sgn in (-1, 1):
        ex, ey = sgn * W * 0.42, -H * 0.18
        tilt = (1 if happy else -1) * sgn * 14
        e = affinity.rotate(affinity.scale(Point(ex, ey).buffer(W * 0.24), 1, 0.55 if happy else 0.62), tilt)
        e = e.difference(Point(ex, ey + (1 if happy else -1) * W * 0.22).buffer(W * 0.2))
        eyes.append(e)
        brow_y = ey - W * (0.3 if happy else 0.26)
        svg += line(f"M{f2(ex - sgn * W * 0.28)},{f2(brow_y + (8 if happy else -14) * s)} Q{f2(ex)},{f2(brow_y - (16 if happy else -6) * s)} {f2(ex + sgn * W * 0.3)},{f2(brow_y + (8 if happy else 18) * s)}", 5)
    for e in eyes:
        svg += fill(d_geom(e), INK, 0.97)
    my = H * 0.42
    if happy:
        mouth = path_pts([((-W * 0.55, my - H * 0.1), (-W * 0.3, my + H * 0.32), (W * 0.3, my + H * 0.32), (W * 0.55, my - H * 0.1)), ((W * 0.55, my - H * 0.1), (W * 0.2, my + H * 0.08), (-W * 0.2, my + H * 0.08), (-W * 0.55, my - H * 0.1))])
    else:
        mouth = path_pts([((-W * 0.5, my + H * 0.18), (-W * 0.3, my - H * 0.16), (W * 0.3, my - H * 0.16), (W * 0.5, my + H * 0.18)), ((W * 0.5, my + H * 0.18), (W * 0.2, my + H * 0.02), (-W * 0.2, my + H * 0.02), (-W * 0.5, my + H * 0.18))])
    svg += fill(d_poly(mouth), INK, 0.97)
    svg += line(d_poly(face), 5.5)
    m.add(svg, fg)
    return m


def drama_masks(rng, color=None):
    m = Motif()
    m.extend(drama_mask(rng, False, color=PURPLE if color else None).place(120, 40, 0.95, 14))
    m.extend(drama_mask(rng, True, color=GOLD if color else None).place(-110, -20, 1.0, -12))
    return m


# ================================================================ dice, cards
def die(rng, s=120, color=None):
    m = Motif()
    top = np.array([(0, -s), (s * 0.95, -s * 0.5), (0, 0), (-s * 0.95, -s * 0.5)])
    left = np.array([(-s * 0.95, -s * 0.5), (0, 0), (0, s * 1.05), (-s * 0.95, s * 0.55)])
    right = np.array([(0, 0), (s * 0.95, -s * 0.5), (s * 0.95, s * 0.55), (0, s * 1.05)])
    svg = ""
    for face, op in ((top, 0.08), (left, 0.45), (right, 0.8)):
        if color:
            svg += fill(d_poly(face), color, 0.9)
        svg += fill(d_poly(face), INK, op * (0.6 if color else 1)) + line(d_poly(face), 5)
    pips = {1: [(0, 0)], 2: [(-0.5, -0.5), (0.5, 0.5)], 3: [(-0.5, -0.5), (0, 0), (0.5, 0.5)], 4: [(-0.5, -0.5), (0.5, -0.5), (-0.5, 0.5), (0.5, 0.5)],
            5: [(-0.5, -0.5), (0.5, -0.5), (0, 0), (-0.5, 0.5), (0.5, 0.5)], 6: [(-0.5, -0.5), (0.5, -0.5), (-0.5, 0), (0.5, 0), (-0.5, 0.5), (0.5, 0.5)]}
    vals = [int(rng.integers(1, 7)) for _ in range(3)]
    frames = [(np.array([0, -s * 0.5]), np.array([s * 0.95, 0.5 * s]) * 0.5, np.array([-s * 0.95, 0.5 * s]) * 0.5),
              (np.array([-s * 0.475, s * 0.275]), np.array([s * 0.95, 0.5 * s]) * 0.5, np.array([0, s * 1.05]) * 0.5),
              (np.array([s * 0.475, s * 0.275]), np.array([s * 0.95, -0.5 * s]) * 0.5, np.array([0, s * 1.05]) * 0.5)]
    for v, (o, ux, uy), solid in zip(vals, frames, (True, False, False)):
        for (a, b_) in pips[v]:
            p = o + ux * a * 0.95 + uy * b_ * 0.95
            e = affinity.scale(Point(p[0], p[1]).buffer(s * 0.11), 1, 0.7)
            svg += fill(d_geom(e), INK, 0.97) if solid else line(d_geom(e), 3)
    m.add(svg, poly([(0, -s), (s * 0.95, -s * 0.5), (s * 0.95, s * 0.55), (0, s * 1.05), (-s * 0.95, s * 0.55), (-s * 0.95, -s * 0.5)]))
    return m


def dice(rng, color=None):
    m = Motif()
    m.extend(die(rng, 120, color=RED if color else None).place(-120, 0, 1, -8))
    m.extend(die(rng, 105, color=RED if color else None).place(115, 50, 1, 12))
    return m


def card(rng, suit="spade", s=1.0, color=None):
    m = Motif()
    W, H = 150 * s, 220 * s
    rect = box(-W, -H, W, H).buffer(-18 * s).buffer(18 * s)
    svg = fill(d_geom(rect), INK, 0.06) + line(d_geom(rect), 5)
    col = RED if (color and suit == "heart") else INK
    sp = heart_pts(70 * s) * (np.array([1, -1]) if suit == "spade" else 1)
    svg += fill(d_poly(sp), col, 0.95)
    if suit == "spade":
        svg += fill(d_poly([(0, 40 * s), (-30 * s, 110 * s), (30 * s, 110 * s)]), INK, 0.95)
    svg += text("A", -W + 40 * s, -H + 80 * s, 70 * s, "CinzelDecorative", col=col, extra='font-weight="700"')
    svg += text("A", W - 40 * s, H - 30 * s, 70 * s, "CinzelDecorative", col=col, extra=f'font-weight="700" transform="rotate(180 {f2(W - 40 * s)} {f2(H - 55 * s)})"')
    m.add(svg, rect)
    return m


def cards(rng, color=None):
    m = Motif()
    m.extend(card(rng, "heart", color=color).place(-70, 10, 1, -14))
    m.extend(card(rng, "spade", color=color).place(70, 0, 1, 12))
    return m


# ================================================================ birds, fish, flowers
def swallow(rng, color=None):
    """traditional swallow in flight: forked tail, swept wings with feather tips"""
    m = Motif()
    c1, c2 = (BLUE, SKYB) if color else (None, None)
    # far wing (behind the body)
    wf = path_pts([((10, -20), (90, -150), (230, -230), (360, -250)), ((360, -250), (300, -190), (290, -160), (250, -140)),
                   ((250, -140), (220, -110), (180, -60), (40, 30))])
    g = poly(wf)
    sv = _shade_fill(m, d_poly(wf), g, light=(-0.6, 0.5), dark=0.95, color=c1, color2=c2)
    for k_ in range(4):
        t = 0.45 + k_ * 0.12
        p = wf[int(len(wf) * t)]
        sv += clip_to(line(f"M{f2(p[0])},{f2(p[1])} l-70,70", 3, 0.85), g, m.defs)
    sv += line(d_poly(wf), 5)
    m.add(sv, g)
    body = path_pts([((-150, -40), (-120, -95), (-40, -100), (20, -50)), ((20, -50), (120, 30), (220, 120), (330, 230)),
                     ((330, 230), (260, 205), (230, 190), (200, 175)), ((200, 175), (230, 230), (250, 300), (230, 330)),
                     ((230, 330), (180, 260), (120, 150), (40, 80)), ((40, 80), (-40, 50), (-120, 30), (-150, -40))])
    bg = poly(body)
    sv = _shade_fill(m, d_poly(body), bg, light=(-0.4, -0.6), dark=0.9, color=c1, color2=c2)
    belly = bg.intersection(Point(-40, 60).buffer(120))
    sv += fill(d_geom(belly), "#fff", 0.0) + (fill(d_geom(belly), "#f2e4cc", 0.0))
    if color:
        sv += fill(d_geom(Point(-110, -10).buffer(42).intersection(bg)), RED, 0.9)
    sv += fill(d_geom(Point(-105, -60).buffer(11)), INK)
    sv += fill(d_poly([(-148, -55), (-205, -42), (-150, -25)]), INK, 0.95)
    sv += line(d_poly(body), 5)
    m.add(sv, bg)
    # near wing (in front)
    wn = path_pts([((-20, 0), (-60, -140), (-120, -260), (-60, -360)), ((-60, -360), (-30, -290), (0, -270), (10, -250)),
                   ((10, -250), (30, -200), (60, -120), (60, 20))])
    g = poly(wn)
    sv = _shade_fill(m, d_poly(wn), g, light=(0.3, 0.6), dark=0.95, color=c1, color2=c2)
    for k_ in range(4):
        p = wn[int(len(wn) * (0.42 + k_ * 0.12))]
        sv += clip_to(line(f"M{f2(p[0])},{f2(p[1])} l70,50", 3, 0.85), g, m.defs)
    sv += line(d_poly(wn), 5)
    m.add(sv, g)
    return m


def lotus(rng, color=None):
    m = Motif()
    col = PINK if color else None
    for ring, (n, L, W, spread, y0) in enumerate([(7, 280, 80, 150, 30), (5, 240, 85, 100, 20), (3, 200, 80, 50, 10)]):
        for i in range(n):
            ang = -spread / 2 + spread * i / max(n - 1, 1)
            pts = rot(petal_pts(L, W, base_w=0.2, notch=0.0), ang) + np.array([0, y0])
            g = poly(pts)
            gdef, gurl = linear(0, y0, 0, y0 - L, [(0, 0.95), (0.5, 0.35), (0.8, 0.0)])
            m.defs.append(gdef)
            svg = (fill(d_poly(pts), col, 0.9) if col else "") + fill(d_poly(pts), gurl, 1 if not col else 0.5)
            svg += line(f"M0,{f2(y0)} L{f2(math.sin(math.radians(ang)) * L * 0.7)},{f2(y0 - math.cos(math.radians(ang)) * L * 0.7)}", 2.5, 0.6)
            svg += line(d_poly(pts), 5)
            m.add(svg, g)
    m.add(line("M-330,60 Q-160,35 0,60 T330,60", 4), None)
    return m


def koi(rng, color=None):
    """koi fish curving through water, scale pattern, flowing fins"""
    m = Motif()
    t = np.linspace(0, 1, 60)
    spine = np.c_[200 * np.sin(t * 2.2 + 0.3) - 90, -360 + 640 * t]
    wdt = 95 * np.sin(np.clip(t, 0, 1) * math.pi) ** 0.7 * (1 - 0.65 * t) + 6
    d = np.gradient(spine, axis=0); d /= np.linalg.norm(d, axis=1, keepdims=True)
    nrm = np.c_[-d[:, 1], d[:, 0]]
    L_ = spine + nrm * wdt[:, None]; R_ = spine - nrm * wdt[:, None]
    body = poly(np.vstack([L_, R_[::-1]]))
    main = ORANGE if color else None
    tp = spine[-1]
    tail = poly(path_pts([((tp[0], tp[1] - 20), (tp[0] - 160, tp[1] + 60), (tp[0] - 200, tp[1] + 200), (tp[0] - 60, tp[1] + 170)),
                          ((tp[0] - 60, tp[1] + 170), (tp[0], tp[1] + 120), (tp[0] + 40, tp[1] + 160), (tp[0] + 140, tp[1] + 220)),
                          ((tp[0] + 140, tp[1] + 220), (tp[0] + 150, tp[1] + 80), (tp[0] + 60, tp[1] + 20), (tp[0], tp[1] - 20))]))
    fins = []
    for (ti, sgn) in ((0.22, 1), (0.22, -1), (0.5, 1)):
        i = int(ti * 59)
        base = spine[i] + nrm[i] * wdt[i] * sgn * 0.9
        f = poly(path_pts([((base[0], base[1] - 30), (base[0] + sgn * nrm[i][0] * 150, base[1] + sgn * nrm[i][1] * 150 + 20),
                            (base[0] + sgn * nrm[i][0] * 120 + 40, base[1] + 130), (base[0], base[1] + 40))]))
        fins.append(f)
    for g in [tail] + fins:
        svg = (fill(d_geom(g), main, 0.8) if main else "") + fill(d_geom(g), INK, 0.28 if not main else 0.12)
        b0 = np.array(g.centroid.coords[0])
        for k_ in range(6):
            svg += clip_to(line(f"M{f2(b0[0] - 60 + k_ * 20)},{f2(b0[1] - 80)} Q{f2(b0[0] + k_ * 15)},{f2(b0[1])} {f2(b0[0] - 40 + k_ * 30)},{f2(b0[1] + 140)}", 2.5, 0.7), g, m.defs)
        svg += line(d_geom(g), 4.5)
        m.add(svg, g)
    svg = ""
    if main:
        svg += fill(d_geom(body), main, 0.9)
        for _ in range(3):
            i = rng.integers(10, 50)
            blob = Point(spine[i][0] + rng.uniform(-30, 30), spine[i][1]).buffer(rng.uniform(35, 60))
            svg += clip_to(fill(d_geom(blob), RED, 0.85), body, m.defs)
    gdef, gurl = linear(-200, 0, 200, 0, [(0, 0.75), (0.5, 0.1), (1, 0.75)])
    m.defs.append(gdef)
    svg += clip_to(fill(d_geom(body), gurl, 0.65 if not main else 0.35), body, m.defs)
    sc = ""
    for i in range(12, 56, 3):
        for jj in np.linspace(-0.8, 0.8, 5):
            p = spine[i] + nrm[i] * wdt[i] * jj
            sc += line(f"M{f2(p[0] - 14)},{f2(p[1])} Q{f2(p[0])},{f2(p[1] + 18)} {f2(p[0] + 14)},{f2(p[1])}", 2.4, 0.85)
    svg += clip_to(sc, body.buffer(-6), m.defs)
    hp = spine[2]
    svg += fill(d_geom(Point(hp[0] + 35, hp[1] + 20).buffer(13)), INK)
    svg += line(f"M{f2(hp[0] - 50)},{f2(hp[1] + 10)} q-60,-20 -90,10", 3) + line(f"M{f2(hp[0] + 50)},{f2(hp[1] + 30)} q50,-10 80,30", 3)
    svg += line(d_geom(body), 5)
    m.add(svg, body)
    for _ in range(4):
        x0, y0 = rng.uniform(-300, 250), rng.uniform(-300, 350)
        m.parts.insert(0, Part(line(f"M{f2(x0)},{f2(y0)} q60,-40 120,0 t120,0 q-20,-60 -70,-50", 4, 0.9), None))
    return m


def butterfly(rng, color=None):
    m = Motif()
    up = path_pts([((0, -10), (60, -160), (260, -260), (300, -160)), ((300, -160), (320, -60), (200, 20), (10, 10))])
    lo = path_pts([((10, 10), (180, 40), (250, 160), (170, 230)), ((170, 230), (100, 280), (30, 150), (0, 30))])
    c1, c2 = (BLUE, SKYB) if color == "blue" else ((ORANGE, YEL) if color else (None, None))
    for sgn in (-1, 1):
        for wg in (up, lo):
            pts = wg * np.array([sgn, 1])
            g = poly(pts)
            svg = _shade_fill(m, d_poly(pts), g, light=(-sgn * 0.6, 0.2), dark=0.9, color=c1, color2=c2)
            cx_, cy_ = g.centroid.coords[0]
            veins = ""
            for k_ in range(3):
                veins += line(f"M0,0 Q{f2(cx_ * 0.6)},{f2(cy_ * 0.4 + k_ * 30)} {f2(cx_ * (1.3 - k_ * 0.2))},{f2(cy_ * 1.2 - 20 + k_ * 40)}", 2.4, 0.8)
            svg += clip_to(veins, g, m.defs)
            spot = Point(cx_ * 1.25, cy_ * 1.1).buffer(26).intersection(g)
            svg += line(d_geom(spot), 3)
            svg += line(d_poly(pts), 5)
            m.add(svg, g)
    bodyg = affinity.scale(Point(0, 40).buffer(26), 0.6, 4.2)
    m.add(fill(d_geom(bodyg), INK, 0.95) + line("M-8,-60 Q-40,-140 -70,-160", 3.5) + line("M8,-60 Q40,-140 70,-160", 3.5), bodyg)
    return m


def cherry_branch(rng, L=800, color=True):
    m = Motif()
    t = np.linspace(0, 1, 50)
    br = np.c_[-L / 2 + L * t, 60 * np.sin(t * 5) - 40 * t]
    m.add(fill(d_geom(taper_stroke(br, 34, 8)), INK, 0.92), taper_stroke(br, 34, 8))
    for i in range(7):
        p = br[int(5 + i * 6.5)]
        s_ = rng.uniform(0.9, 1.3)
        fl = Motif()
        for k_ in range(5):
            pts = rot(petal_pts(70 * s_, 42 * s_, base_w=0.15, notch=0.12), k_ * 72)
            g = poly(pts)
            svg = (fill(d_poly(pts), PINK2, 0.9) if color else "") + fill(d_poly(pts), INK, 0.12 if color else 0.22) + line(d_poly(pts), 3.5)
            fl.add(svg, g)
        fl.add(fill(d_geom(Point(0, 0).buffer(10 * s_)), PINK if color else INK, 0.95), None)
        m.extend(fl.place(p[0] + rng.uniform(-20, 20), p[1] + rng.uniform(-70, 40), 1, rng.uniform(0, 72)))
    return m


# ================================================================ coast / city / car
def palm(x0, y0, h, lean, rng):
    t = np.linspace(0, 1, 30)
    trunk = np.c_[x0 + lean * t ** 1.6, y0 - h * t]
    m = Motif()
    tg = taper_stroke(trunk, 30, 14)
    svg = fill(d_geom(tg), INK, 0.97)
    for k_ in range(int(h / 60), int(h / 60) + 1):
        pass
    top = trunk[-1]
    for k_ in range(7):
        a = math.radians(-170 + k_ * 26 + rng.uniform(-6, 6))
        Lf = rng.uniform(120, 170)
        tip = top + np.array([math.cos(a), math.sin(a)]) * Lf + np.array([0, Lf * 0.35])
        mid = top + np.array([math.cos(a), math.sin(a)]) * Lf * 0.55 + np.array([0, -12])
        fr = path_pts([(top, mid, mid, tip)])
        svg += fill(d_geom(taper_stroke(fr, 26, 2, 34)), INK, 0.97)
    m.add(svg, tg)
    return m


def palm_sunset(rng, R=280, color=True):
    m = Motif()
    disc = Point(0, 0).buffer(R, 96)
    if color:
        gdef, gurl = linear(0, -R, 0, R * 0.3, [(0, 1, PURPLE), (0.45, 1, PINK), (1, 1, ORANGE)])
        m.defs.append(gdef)
        sky = fill(d_geom(disc), gurl, 0.85)
    else:
        gdef, gurl = linear(0, -R, 0, R * 0.3, [(0, 0.6), (1, 0.05)])
        m.defs.append(gdef)
        sky = fill(d_geom(disc), gurl, 1)
    sun = Point(0, R * 0.15).buffer(R * 0.45, 64)
    stripes = unary_union([box(-R, R * 0.15 - R * 0.02 + k_ * R * 0.09, R, R * 0.15 + k_ * R * 0.09 + R * (0.012 * k_)) for k_ in range(5)])
    sun = sun.difference(stripes).intersection(box(-R, -R, R, R * 0.33))
    sky += fill(d_geom(sun), YEL, 0.95) if color else line(d_geom(sun), 3)
    sea = disc.intersection(box(-R, R * 0.33, R, R))
    sky += fill(d_geom(sea), BLUE if color else INK, 0.8 if color else 0.55)
    for k_ in range(4):
        y = R * 0.42 + k_ * R * 0.12
        sky += clip_to(line(f"M{f2(-R)},{f2(y)} q40,-14 80,0 t80,0 t80,0 t80,0 t80,0 t80,0 t80,0", 3, 0.7, "#fff" if color else INK), disc, m.defs)
    m.add(clip_to(sky, disc, m.defs), disc)
    for (x0, h, lean) in ((-R * 0.55, R * 1.05, 60), (R * 0.45, R * 0.85, -50), (-R * 0.25, R * 0.6, 30)):
        p = palm(x0, R * 0.36, h, lean, rng)
        m.add(clip_to(p.parts[0].svg, disc, m.defs), p.parts[0].sil.intersection(disc))
    m.add(line(d_geom(disc), 6) + line(d_geom(Point(0, 0).buffer(R + 16, 96)), 3), None)
    return m


def skyline(rng, w=700, h=300, color=False):
    m = Motif()
    x = -w / 2
    bl = []
    while x < w / 2:
        bw = rng.uniform(40, 90); bh = rng.uniform(0.3, 1.0) * h
        bl.append(box(x, -bh, x + bw, 0))
        if rng.random() < 0.3:
            bl.append(box(x + bw * 0.4, -bh - 50, x + bw * 0.5, -bh))
        x += bw + rng.uniform(-6, 4)
    g = unary_union(bl).intersection(box(-w / 2, -h * 1.5, w / 2, 0))
    win = []
    for b in bl:
        minx, miny, maxx, maxy = b.bounds
        if maxx - minx < 30:
            continue
        for yy in np.arange(miny + 14, maxy - 10, 24):
            for xx in np.arange(minx + 9, maxx - 12, 18):
                if rng.random() < 0.55:
                    win.append(box(xx, yy, xx + 8, yy + 12))
    gw = g.difference(unary_union(win)) if win else g
    svg = fill(d_geom(gw), INK, 0.95)
    if color and win:
        svg += fill(d_geom(unary_union(win).intersection(g)), YEL, 0.85)
    svg += line(f"M{f2(-w / 2)},0 L{f2(w / 2)},0", 4)
    for k_ in range(5):
        svg += line(f"M{f2(rng.uniform(-w / 2, 0))},{f2(16 + k_ * 14)} l{f2(rng.uniform(80, 300))},0", 3, 0.55)
    m.add(svg, g)
    return m


def wire_wheel(cx, cy, r, spokes=36):
    s = fill(d_geom(Point(cx, cy).buffer(r).difference(Point(cx, cy).buffer(r * 0.72))), INK, 0.95) + line(d_geom(Point(cx, cy).buffer(r)), 5)
    for i in range(spokes):
        a = 2 * math.pi * i / spokes
        a2 = a + 0.35
        s += line(f"M{f2(cx + r * 0.16 * math.cos(a))},{f2(cy + r * 0.16 * math.sin(a))} L{f2(cx + r * 0.7 * math.cos(a2))},{f2(cy + r * 0.7 * math.sin(a2))}", 1.6, 0.9)
    s += line(d_geom(Point(cx, cy).buffer(r * 0.6)), 2.5, 0.6)  # whitewall edge
    s += fill(d_geom(Point(cx, cy).buffer(r * 0.17)), INK) + line(d_geom(Point(cx, cy).buffer(r * 0.72)), 2.5)
    return s


def lowrider_car(rng, color=None):
    """original long, low cruiser in side view on wire wheels"""
    m = Motif()
    body = path_pts([((-420, 10), (-430, -40), (-400, -60), (-300, -62)), ((-300, -62), (-200, -66), (-160, -130), (-60, -132)),
                     ((-60, -132), (60, -134), (110, -100), (160, -66)), ((160, -66), (300, -62), (420, -60), (430, -20)),
                     ((430, -20), (436, 10), (420, 20), (380, 20)), ((380, 20), (200, 22), (-200, 22), (-420, 10))])
    bg = poly(body)
    wells = unary_union([Point(-250, 22).buffer(74), Point(260, 22).buffer(74)])
    bodyc = bg.difference(wells)
    svg = _shade_fill(m, d_geom(bodyc), bodyc, light=(0, -0.8), dark=0.9, color=color, color2="#ffffff" if color else None)
    win = poly(path_pts([((-170, -70), (-140, -122), (-60, -124), (-20, -122)), ((-20, -122), (-20, -100), (-20, -80), (-20, -70)), ((-20, -70), (-80, -70), (-130, -70), (-170, -70))]))
    win2 = poly(path_pts([((0, -122), (60, -124), (90, -98), (130, -70)), ((130, -70), (80, -70), (30, -70), (0, -70))]))
    svg += fill(d_geom(win), INK, 0.85) + fill(d_geom(win2), INK, 0.85)
    svg += line("M-420,-20 L425,-24", 3, 0.9)
    svg += line("M-400,-10 Q0,-6 400,-14", 2, 0.6)
    svg += line("M-110,-40 l40,0", 4)  # door handle
    svg += line(d_geom(bodyc), 5)
    m.add(svg, bodyc)
    for (cx, cy) in ((-250, 22), (260, 22)):
        m.add(wire_wheel(cx, cy, 62), Point(cx, cy).buffer(62))
    m.parts.insert(0, Part(line("M-470,86 L480,86", 4, 0.8), None))
    return m


# ================================================================ symbols
def crown(rng, color=None):
    m = Motif()
    pts = [(-200, 80), (-220, -90), (-120, 0), (-60, -140), (0, -30), (60, -140), (120, 0), (220, -90), (200, 80)]
    g = poly(pts)
    band = box(-200, 40, 200, 110)
    svg = _shade_fill(m, d_poly(pts), g, color=GOLD if color else None, color2=GOLD2 if color else None) + line(d_poly(pts), 5)
    svg += _shade_fill(m, d_geom(band), band, color=GOLD if color else None, color2=GOLD2 if color else None) + line(d_geom(band), 5)
    for x in (-120, 0, 120):
        j = Point(x, 75).buffer(18)
        svg += fill(d_geom(j), RED if color else INK, 0.95) + line(d_geom(j), 3)
    for (x, y) in ((-220, -90), (-60, -140), (60, -140), (220, -90)):
        b = Point(x, y - 14).buffer(16)
        svg += fill(d_geom(b), INK, 0.2) + line(d_geom(b), 3.5)
    m.add(svg, unary_union([g, band]))
    return m


def compass(rng, R=260, color=None):
    m = Motif()
    ring = Point(0, 0).buffer(R).difference(Point(0, 0).buffer(R * 0.86))
    svg = fill(d_geom(ring), INK, 0.25) + line(d_geom(Point(0, 0).buffer(R)), 5) + line(d_geom(Point(0, 0).buffer(R * 0.86)), 3)
    for i in range(72):
        a = math.radians(i * 5)
        svg += line(f"M{f2(R * 0.86 * math.cos(a))},{f2(R * 0.86 * math.sin(a))} L{f2(R * (0.93 if i % 2 else 0.98) * math.cos(a))},{f2(R * (0.93 if i % 2 else 0.98) * math.sin(a))}", 2)
    m.add(svg, Point(0, 0).buffer(R))
    for big, n, off in ((False, 4, 45), (True, 4, 0)):
        L = R * (0.82 if big else 0.55)
        for i in range(n):
            a = math.radians(off + i * 90 - 90)
            tip = (L * math.cos(a), L * math.sin(a))
            w_ = L * 0.16
            l_ = (w_ * math.cos(a - math.pi / 2), w_ * math.sin(a - math.pi / 2))
            half1 = [(0, 0), tip, l_]
            g = poly([(0, 0), l_, tip, (-l_[0], -l_[1])])
            sv = fill(d_poly(half1), (RED if (color and i == 0 and big) else INK), 0.95) + line(d_poly([tip, l_, (0, 0), (-l_[0], -l_[1]), tip]), 4)
            m.add(sv, g)
    m.add(text("N", 0, -R * 0.98 - 14, R * 0.2, "CinzelDecorative", extra='font-weight="700"'), None)
    return m


def anchor(rng, color=None):
    m = Motif()
    shaft = box(-18, -260, 18, 210)
    ringg = Point(0, -300).buffer(48).difference(Point(0, -300).buffer(26))
    bar = box(-130, -200, 130, -168)
    t = np.linspace(-1, 1, 40)
    arc = np.c_[230 * t, 230 - 110 * (1 - t ** 2)]
    arcg = taper_stroke(arc, 30, 30, 44)
    flukes = []
    for sgn in (-1, 1):  # barbed tips at the arc ends, pointing up and out
        e = arc[0] if sgn < 0 else arc[-1]
        flukes.append(poly([(e[0] - sgn * 30, e[1] + 10), (e[0] + sgn * 40, e[1] - 95), (e[0] + sgn * 30, e[1] + 25)]))
    g = unary_union([shaft, ringg, bar, arcg] + flukes)
    svg = _shade_fill(m, d_geom(g), g, light=(-0.5, 0), dark=0.85, color=color) + line(d_geom(g), 4.5)
    m.add(svg, g)
    rope = np.c_[55 * np.sin(np.linspace(0, 5 * math.pi, 80)), np.linspace(-250, 170, 80)]
    rg = taper_stroke(rope, 16, 16)
    m.add(fill(d_geom(rg), INK, 0.35) + line(d_geom(rg), 3.5), rg)
    return m


def feather(rng, L=600, color=None):
    m = Motif()
    t = np.linspace(0, 1, 60)
    quill = np.c_[40 * np.sin(t * 2.5), L / 2 - L * t]
    wv = 90 * np.sin(np.clip(t * 1.05, 0, 1) * math.pi) ** 0.6
    vane = [quill + np.c_[sgn * wv, -wv * 0.3] for sgn in (-1, 1)]
    g = poly(np.vstack([vane[0][8:], vane[1][8:][::-1]]))
    svg = (fill(d_geom(g), color, 0.85) if color else "")
    barbs = ""
    for i in range(8, 58):
        for sgn in (-1, 1):
            p = quill[i]
            barbs += line(f"M{f2(p[0])},{f2(p[1])} Q{f2(p[0] + sgn * wv[i] * 0.5)},{f2(p[1] - 8)} {f2(p[0] + sgn * wv[i])},{f2(p[1] - wv[i] * 0.3)}", 1.8, 0.8)
    svg += clip_to(barbs, g, m.defs)
    gdef, gurl = linear(-100, 0, 100, 0, [(0, 0.7), (0.5, 0.05), (1, 0.7)])
    m.defs.append(gdef)
    svg += fill(d_geom(g), gurl, 0.7) + line(d_geom(g), 4) + line(d_poly(quill, close=False), 6)
    m.add(svg, g.union(LineString(quill).buffer(4)))
    return m


def sugar_skull(rng, color=None):
    """Day of the Dead style decorated skull (festive, flowers for eyes)"""
    m = Motif()
    cran = path_pts([((0, -260), (190, -260), (230, -60), (170, 40)), ((170, 40), (160, 120), (110, 150), (90, 230)),
                     ((90, 230), (40, 260), (-40, 260), (-90, 230)), ((-90, 230), (-110, 150), (-160, 120), (-170, 40)), ((-170, 40), (-230, -60), (-190, -260), (0, -260))])
    g = poly(cran)
    svg = _shade_fill(m, d_poly(cran), g, light=(0, -0.5), dark=0.55)
    for sgn in (-1, 1):
        ex, ey = sgn * 85, -10
        sock = Point(ex, ey).buffer(68)
        petals = unary_union([poly(rot(petal_pts(56, 24, base_w=0.2), k_ * 45) + np.array([ex, ey])) for k_ in range(8)])
        if color:
            svg += fill(d_geom(sock), INK, 0.92)
            svg += fill(d_geom(petals), PINK if sgn < 0 else TEAL, 0.95)
            for k_ in range(8):
                svg += line(d_poly(rot(petal_pts(56, 24, base_w=0.2), k_ * 45) + np.array([ex, ey])), 2.6)
        else:  # dark socket with the flower left as bare skin
            svg += fill(d_geom(sock.difference(petals.buffer(-1))), INK, 0.92)
            for k_ in range(8):
                svg += line(d_poly(rot(petal_pts(56, 24, base_w=0.2), k_ * 45) + np.array([ex, ey])), 2.2, 0.9)
        svg += fill(d_geom(Point(ex, ey).buffer(14)), YEL if color else INK, 0.95)
    nh = heart_pts(30) * np.array([1, -1]) + np.array([0, 90])
    svg += fill(d_poly(nh), INK, 0.95)
    svg += line("M-95,165 Q0,215 95,165", 4.5)
    for x in np.linspace(-80, 80, 9):
        y = 165 + 50 * (1 - (x / 95) ** 2) * 0.5 + 2
        svg += line(f"M{f2(x)},{f2(y - 16)} L{f2(x)},{f2(y + 16)}", 3.5)
    for k_ in range(6):
        pts = rot(petal_pts(60, 26, base_w=0.2), k_ * 60) + np.array([0, -165])
        svg += fill(d_poly(pts), (ORANGE if color else INK), 0.85 if color else 0.25) + line(d_poly(pts), 3)
    svg += fill(d_geom(Point(0, -165).buffer(15)), INK)
    for (x, y) in ((-150, -60), (150, -60), (-120, 60), (120, 60), (-60, -110), (60, -110)):
        svg += fill(d_geom(Point(x, y).buffer(8)), INK)
    svg += line("M-150,90 q20,25 50,10 M150,90 q-20,25 -50,10", 3.5)
    svg += line(d_poly(cran), 5.5)
    m.add(svg, g)
    return m


def sun_disc(rng, R=300, color=None):
    """geometric sun disc inspired by Mesoamerican stone calendars (generic rings and rays, no real glyphs)"""
    m = Motif()
    svg = ""
    for r_ in (R, R * 0.86, R * 0.66, R * 0.5, R * 0.3):
        svg += line(d_geom(Point(0, 0).buffer(r_, 96)), 4.5)
    for i in range(40):
        a = 2 * math.pi * i / 40
        p = [(R * 0.88 * math.cos(a), R * 0.88 * math.sin(a)), (R * 0.98 * math.cos(a), R * 0.98 * math.sin(a)),
             (R * 0.98 * math.cos(a + 0.08), R * 0.98 * math.sin(a + 0.08)), (R * 0.88 * math.cos(a + 0.08), R * 0.88 * math.sin(a + 0.08))]
        svg += fill(d_poly(p), INK, 0.92)
    for i in range(8):
        a = 2 * math.pi * i / 8 - math.pi / 2
        p = [(R * 0.52 * math.cos(a - 0.2), R * 0.52 * math.sin(a - 0.2)), (R * 0.84 * math.cos(a), R * 0.84 * math.sin(a)), (R * 0.52 * math.cos(a + 0.2), R * 0.52 * math.sin(a + 0.2))]
        svg += fill(d_poly(p), (TEAL if color else INK), 0.9 if color else 0.85) + line(d_poly(p), 3.5)
    for i in range(20):
        if i % 2:
            a = 2 * math.pi * i / 20
            c = (R * 0.58 * math.cos(a), R * 0.58 * math.sin(a))
            bx = affinity.rotate(box(c[0] - 14, c[1] - 9, c[0] + 14, c[1] + 9), math.degrees(a) + 90, origin=c)
            svg += fill(d_geom(bx), INK, 0.4) + line(d_geom(bx), 2.5)
    for i in range(12):
        a = 2 * math.pi * i / 12
        svg += fill(d_geom(Point(R * 0.4 * math.cos(a), R * 0.4 * math.sin(a)).buffer(12)), INK, 0.9)
    core = Point(0, 0).buffer(R * 0.3, 64)
    gdef, gurl = radial(0, 0, R * 0.3, [(0, 0.1), (0.7, 0.35), (1, 0.9)])
    m.defs.append(gdef)
    svg += (fill(d_geom(core), GOLD, 0.85) if color else "") + fill(d_geom(core), gurl, 1)
    for i in range(4):
        a = math.pi / 4 + i * math.pi / 2
        p = [(0, 0), (R * 0.26 * math.cos(a - 0.3), R * 0.26 * math.sin(a - 0.3)), (R * 0.26 * math.cos(a + 0.3), R * 0.26 * math.sin(a + 0.3))]
        svg += fill(d_poly(p), INK, 0.9)
    m.add(svg, Point(0, 0).buffer(R))
    return m


def mandala(rng, R=300, color=None):
    m = Motif()
    svg = ""
    layers = int(rng.integers(4, 6))
    radii = np.linspace(R * 0.2, R, layers + 1)
    for li in range(layers):
        r0, r1 = radii[li], radii[li + 1]
        n = int(8 + li * 4)
        kind = (li + int(rng.integers(0, 3))) % 3
        for i in range(n):
            a = 360 * i / n
            if kind == 0:
                pts = rot(petal_pts(r1 - r0, (r1 - r0) * 0.35, base_w=0.15) + np.array([0, -r0]), a)
                svg += fill(d_poly(pts), (TEAL if color else INK), (0.7 if color else 0.15 + 0.1 * (li % 2))) + line(d_poly(pts), 2.8)
            elif kind == 1:
                for k_ in range(5):
                    rr = r0 + (r1 - r0) * (k_ + 0.5) / 5
                    aa = math.radians(a + 360 / n / 2)
                    svg += fill(d_geom(Point(rr * math.sin(aa), -rr * math.cos(aa)).buffer(2 + k_ * 0.8)), INK, 0.9)
            else:
                aa, ab = math.radians(a), math.radians(a + 360 / n)
                p = [(r0 * math.sin(aa), -r0 * math.cos(aa)), (r1 * math.sin((aa + ab) / 2), -r1 * math.cos((aa + ab) / 2)), (r0 * math.sin(ab), -r0 * math.cos(ab))]
                svg += fill(d_poly(p), (PURPLE if (color and i % 2) else INK), 0.85 if i % 2 else 0.2) + line(d_poly(p), 2.5)
        svg += line(d_geom(Point(0, 0).buffer(r1, 96)), 2.5)
    svg += fill(d_geom(Point(0, 0).buffer(R * 0.12)), INK, 0.9)
    m.add(svg, Point(0, 0).buffer(R))
    return m


def hourglass(rng, color=None):
    m = Motif()
    glass = path_pts([((-110, -220), (-110, -40), (-12, -20), (-12, 0)), ((-12, 0), (-12, 20), (-110, 40), (-110, 220)), ((-110, 220), (0, 220), (0, 220), (110, 220)),
                      ((110, 220), (110, 40), (12, 20), (12, 0)), ((12, 0), (12, -20), (110, -40), (110, -220)), ((110, -220), (0, -220), (0, -220), (-110, -220))])
    g = poly(glass)
    sand = g.intersection(unary_union([box(-120, -120, 120, -10), box(-120, 150, 120, 230)]))
    svg = fill(d_geom(g), INK, 0.08) + fill(d_geom(sand), GOLD if color else INK, 0.9 if color else 0.6) + line("M0,-10 L0,150", 2.5) + line(d_poly(glass), 4.5)
    caps = unary_union([box(-150, -260, 150, -220), box(-150, 220, 150, 260)])
    posts = unary_union([box(-150, -220, -126, 220), box(126, -220, 150, 220)])
    svg2 = _shade_fill(m, d_geom(caps.union(posts)), caps.union(posts), dark=0.9) + line(d_geom(caps), 4.5) + line(d_geom(posts), 4)
    m.add(svg, g)
    m.add(svg2, caps.union(posts))
    return m


def microphone(rng, color=None):
    m = Motif()
    head = Point(0, -170).buffer(95)
    grill = ""
    for k_ in range(-90, 100, 18):
        grill += line(f"M{k_},-270 L{k_},-70", 2.2, 0.8) + line(f"M-100,{k_ - 170} L100,{k_ - 170}", 2.2, 0.8)
    svg = _shade_fill(m, d_geom(head), head, dark=0.85) + clip_to(grill, head, m.defs) + line(d_geom(head), 5)
    handle = poly([(-55, -80), (55, -80), (32, 260), (-32, 260)])
    band = box(-62, -90, 62, -55)
    svg2 = _shade_fill(m, d_geom(handle), handle, light=(-0.6, 0), dark=0.95, color=color) + line(d_geom(handle), 5)
    svg2 += _shade_fill(m, d_geom(band), band, dark=0.9) + line(d_geom(band), 4)
    m.add(svg2, handle.union(band))
    m.add(svg, head)
    return m


def music_notes(rng):
    m = Motif()
    svg = ""
    for (x, y, s) in ((-80, 20, 1.0), (70, -40, 0.8)):
        h1 = affinity.rotate(affinity.scale(Point(x, y).buffer(34 * s), 1.3, 0.9), -25)
        svg += fill(d_geom(h1), INK, 0.95) + fill(d_geom(box(x + 34 * s, y - 190 * s, x + 44 * s, y - 5)), INK, 0.95)
        svg += fill(d_geom(taper_stroke(path_pts([((x + 40 * s, y - 190 * s), (x + 90 * s, y - 160 * s), (x + 90 * s, y - 120 * s), (x + 70 * s, y - 80 * s))]), 14 * s, 4 * s)), INK, 0.95)
    m.add(svg, box(-140, -230, 160, 80))
    return m


def cross(rng, color=None, rays_=True):
    m = Motif()
    g = unary_union([box(-26, -180, 26, 220), box(-120, -100, 120, -48)])
    if rays_:
        m.extend(rays(rng, n=12, R=330, spread=360, w0=0.45, op=0.45, start=-90))
    svg = _shade_fill(m, d_geom(g), g, light=(-0.6, -0.4), dark=0.9, color=GOLD if color else None, color2=GOLD2 if color else None) + line(d_geom(g), 5)
    m.add(svg, g)
    return m


def sparkle(rng, R=120, color=None):
    m = Motif()
    P = []
    for i in range(8):
        a = math.radians(i * 45 - 90)
        rr = R if i % 2 == 0 else R * 0.22
        P.append((rr * math.cos(a), rr * math.sin(a)))
    m.add(fill(d_poly(P), color or INK, 0.95), poly(P))
    return m


def moon_stars(rng, color=None):
    m = Motif()
    moon = Point(0, 0).buffer(200, 96).difference(Point(80, -40).buffer(175, 96))
    svg = _shade_fill(m, d_geom(moon), moon, light=(-0.6, 0), dark=0.85, color=YEL if color else None) + line(d_geom(moon), 5)
    m.add(svg, moon)
    for (x, y, s) in ((150, 80, 0.35), (210, -120, 0.25), (60, 190, 0.2)):
        m.extend(star(rng, R=120, nautical=False, color=YEL if color else None).place(x, y, s))
    return m


# ================================================================ bands (wrap around a limb)
def band_pattern(rng, kind, W, h):
    """horizontal band spanning W (the full limb circumference in canvas units), centred on y=0"""
    m = Motif()
    svg = ""
    if kind == "tribal":
        svg += fill(d_geom(box(0, -h * 0.5, W, -h * 0.38)), INK) + fill(d_geom(box(0, h * 0.38, W, h * 0.5)), INK)
        n = max(4, int(W / (h * 1.1)))
        for i in range(n):
            x0 = W * i / n
            sp = path_pts([((x0, -h * 0.36), (x0 + h * 0.5, -h * 0.36), (x0 + h * 0.7, h * 0.1), (x0 + h * 0.95, h * 0.36)), ((x0 + h * 0.95, h * 0.36), (x0 + h * 0.55, h * 0.2), (x0 + h * 0.3, -h * 0.1), (x0, -h * 0.36))])
            svg += fill(d_poly(sp), INK) + fill(d_poly(np.c_[sp[:, 0] + h * 0.45, -sp[:, 1]]), INK)
    elif kind == "geo":
        svg += line(f"M0,{-h / 2} L{W},{-h / 2} M0,{h / 2} L{W},{h / 2}", 6)
        n = max(6, int(W / (h * 0.7)))
        for i in range(n):
            x0, x1 = W * i / n, W * (i + 1) / n
            tri = [(x0, h * 0.42), ((x0 + x1) / 2, -h * 0.42), (x1, h * 0.42)]
            svg += (fill(d_poly(tri), INK, 0.92) if i % 2 else "") + line(d_poly(tri), 3)
    elif kind == "chain":
        n = max(6, int(W / (h * 0.9)))
        for i in range(n):
            x0 = W * (i + 0.5) / n
            lk = affinity.scale(Point(x0, 0).buffer(h * 0.4), 1.35, 0.75)
            ring_ = lk.difference(affinity.scale(Point(x0, 0).buffer(h * 0.25), 1.6, 0.5))
            svg += fill(d_geom(ring_), INK, 0.55 if i % 2 else 0.85) + line(d_geom(lk), 3.5)
    elif kind == "thorns":
        t = np.linspace(0, 1, 200)
        for ph in (0, math.pi):
            vine = np.c_[W * t, h * 0.22 * np.sin(t * W / (h * 1.4) * 2 * math.pi + ph)]
            svg += fill(d_geom(taper_stroke(vine, h * 0.1, h * 0.1)), INK, 0.9)
            for i in range(10, 200, 14):
                p = vine[i]
                svg += fill(d_poly([(p[0] - h * 0.05, p[1]), (p[0], p[1] - h * 0.3 * (1 if (i // 14) % 2 else -1)), (p[0] + h * 0.05, p[1])]), INK, 0.95)
    elif kind == "rope":
        n = max(8, int(W / (h * 0.35)))
        for i in range(n):
            x0 = W * i / n
            seg = poly([(x0, -h * 0.35), (x0 + W / n * 1.1, -h * 0.35), (x0 + W / n * 1.6, h * 0.35), (x0 + W / n * 0.5, h * 0.35)])
            gdef, gurl = linear(x0, -h * 0.35, x0 + W / n, h * 0.35, [(0, 0.85), (0.5, 0.1), (1, 0.85)])
            m.defs.append(gdef)
            svg += fill(d_geom(seg), gurl, 1) + line(d_geom(seg), 2.5)
    elif kind == "waves":
        n = max(4, int(W / (h * 1.2)))
        for i in range(n):
            x0 = W * i / n
            svg += line(f"M{f2(x0)},{f2(h * 0.3)} q{f2(W / n * 0.4)},{f2(-h * 0.9)} {f2(W / n * 0.8)},{f2(-h * 0.2)} q{f2(-W / n * 0.25)},{f2(-h * 0.05)} {f2(-W / n * 0.2)},{f2(h * 0.2)}", 5)
            svg += line(f"M{f2(x0)},{f2(h * 0.45)} q{f2(W / n * 0.5)},{f2(-h * 0.25)} {f2(W / n)},0", 3.5, 0.8)
    m.add(svg, box(0, -h / 2, W, h / 2))
    return m
