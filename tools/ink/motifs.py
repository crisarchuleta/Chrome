"""motifs.py: original tattoo motifs, all PG (no weapons, no gang signs or numbers, no bad words).
Each returns a Motif in local units (roughly -500..500 around the origin)."""
import math
import numpy as np
from inkcore import *

RED = "#b0142b"; RED2 = "#e0455a"; GOLD = "#d9a21b"; GOLD2 = "#f2cf5b"; TEAL = "#1d8a8a"; BLUE = "#1f5fbf"
PINK = "#e46a9a"; PINK2 = "#f7b6cf"; ORANGE = "#ef6a1a"; YEL = "#f5c518"; GREEN = "#2f7d3a"; GREEN2 = "#5fae4c"
PURPLE = "#6a3fb5"; SKYB = "#58b8e8"


def rot(pts, a, c=(0, 0)):
    a = math.radians(a)
    R = np.array([[math.cos(a), -math.sin(a)], [math.sin(a), math.cos(a)]])
    return (np.asarray(pts) - c) @ R.T + c


# ================================================================ rose
def petal_pts(L, W, base_w=0.25, notch=0.0, lean=0.0):
    """petal pointing up (-y) from the origin: a rounded lobe, optional notch at the tip"""
    segs = [((-W * base_w, 0), (-W * 1.05, -L * 0.25), (-W * (0.95 - lean), -L * 0.92), (-W * 0.25 + lean * W, -L * (1 - notch * 0.4)))]
    segs.append(((-W * 0.25 + lean * W, -L * (1 - notch * 0.4)), (-W * 0.1, -L * (1.02 - notch)), (W * 0.1, -L * (1.02 - notch)), (W * 0.25 + lean * W, -L * (1 - notch * 0.4))))
    segs.append(((W * 0.25 + lean * W, -L * (1 - notch * 0.4)), (W * (0.95 + lean), -L * 0.92), (W * 1.05, -L * 0.25), (W * base_w, 0)))
    return path_pts(segs)


def rose(rng, color=None, size=1.0, open_=1.0):
    """classic top-view tattoo rose: outer, middle and inner petal rings, curled rims, spiral bud.
    color=None -> black & grey; otherwise petals take that colour under the ink shading."""
    m = Motif()
    defs = m.defs
    hi = color or None
    rings = [(5, 95, 300 * open_, 210, 0), (5, 55, 215 * open_, 165, 36), (4, 25, 140, 120, 10)]
    a0 = rng.uniform(0, 360)
    for ri, (n, r0, L, W, off) in enumerate(rings):
        for i in range(n):
            ang = a0 + off + i * 360 / n + rng.uniform(-8, 8)
            Lp = L * rng.uniform(0.9, 1.08); Wp = W * rng.uniform(0.88, 1.08)
            pts = petal_pts(Lp, Wp, notch=rng.uniform(0.0, 0.08), lean=rng.uniform(-0.12, 0.12))
            pts = pts + np.array([0, -r0 * 0.35])
            pts = rot(pts, ang)
            pg = poly(pts)
            d = d_poly(pts)
            # shading: dark at the base (near the centre), fading out toward the rim; rim stays skin (highlight)
            gdef, gurl = radial(0, 0, r0 * 0.35 + Lp, [(0, 0.97), (0.42, 0.85), (0.7, 0.42), (0.86, 0.1), (0.95, 0.0)])
            defs.append(gdef)
            svg = ""
            if color:
                cdef, curl = radial(0, 0, r0 * 0.35 + Lp, [(0, 1, color), (0.8, 0.95, color), (1, 0.85, RED2 if color == RED else color)])
                defs.append(cdef)
                svg += fill(d, curl, 0.92)
            svg += fill(d, gurl, 0.9 if not color else 0.55)
            # curled rim: a second line just inside the tip and a little dark pocket under it
            tip = rot(np.array([[0, -r0 * 0.35 - Lp * 0.86]]), ang)[0]
            curl_pts = rot(np.array([[-Wp * 0.62, -r0 * 0.35 - Lp * 0.78], [0, -r0 * 0.35 - Lp * 0.9], [Wp * 0.62, -r0 * 0.35 - Lp * 0.78]]), ang)
            cd = f"M{f2(curl_pts[0][0])},{f2(curl_pts[0][1])} Q{f2(curl_pts[1][0])},{f2(curl_pts[1][1])} {f2(curl_pts[2][0])},{f2(curl_pts[2][1])}"
            svg += line(cd, 3.2, 0.9)
            svg += line(d, 5.2)
            # the petal casts a soft shadow onto the petals behind it
            behind = [p_.sil for p_ in m.parts if p_.sil is not None]
            if behind:
                bu = unary_union(behind)
                shadow = soft(line(d, 34, 0.75), 9, defs)
                svg = clip_to(shadow, bu.difference(pg), defs) + svg
            m.add(svg, pg)
    # bud: a spiral of three tight curls
    bud = Motif()
    for j, (rr, aa, sc) in enumerate([(0, 0, 1.0), (14, 120, 0.72), (8, 250, 0.5)]):
        c = rot(np.array([[0, -rr]]), a0 + aa)[0]
        pts = petal_pts(95 * sc, 78 * sc, base_w=0.6)
        pts = rot(pts + np.array([0, 40 * sc]), a0 + aa + 180) + c
        pg = poly(pts)
        gdef, gurl = radial(c[0], c[1], 80 * sc, [(0, 0.95), (0.5, 0.7), (1, 0.1)])
        defs.append(gdef)
        svg = (fill(d_poly(pts), "url(#)" if False else (color or INK), 0.9) if color else "") + fill(d_poly(pts), gurl, 0.85) + line(d_poly(pts), 4.6)
        m.add(svg, pg)
    m.add(fill(d_geom(Point(0, 0).buffer(16)), INK, 0.95), Point(0, 0).buffer(16))
    return m.place(s=size) if size != 1 else m


def leaf(rng, L=260, W=95, color=None):
    """serrated leaf pointing up from the origin with midrib and veins"""
    m = Motif()
    left = path_pts([((0, 0), (-W * 0.9, -L * 0.2), (-W * 1.0, -L * 0.7), (0, -L))])
    right = path_pts([((0, -L), (W * 1.0, -L * 0.7), (W * 0.9, -L * 0.2), (0, 0))])
    pts = np.vstack([left, right[1:]])
    # small serration
    n = len(pts)
    t = np.linspace(0, 1, n)
    c = pts.mean(0)
    nrm = pts - c
    nrm /= np.maximum(np.linalg.norm(nrm, axis=1, keepdims=True), 1e-9)
    pts = pts + nrm * (np.abs(np.sin(t * math.pi * 14)) * 7)[:, None] * (np.sin(t * math.pi) > 0.15)[:, None]
    d = d_poly(pts)
    gdef, gurl = linear(-W, 0, W, 0, [(0, 0.15), (0.45, 0.85), (0.5, 0.95), (0.55, 0.3), (1, 0.05)])
    m.defs.append(gdef)
    svg = ""
    if color:
        svg += fill(d, color, 0.85)
    svg += fill(d, gurl, 0.8 if not color else 0.45)
    veins = line(f"M0,{-4} Q{f2(W * 0.08)},{f2(-L * 0.5)} 0,{f2(-L * 0.97)}", 3.4)
    for k_ in range(1, 6):
        y = -L * k_ / 6.5
        for sgn in (-1, 1):
            veins += line(f"M0,{f2(y)} Q{f2(sgn * W * 0.35)},{f2(y - L * 0.05)} {f2(sgn * W * 0.62)},{f2(y - L * 0.12)}", 2.2, 0.8)
    svg += clip_to(veins, poly(pts).buffer(-4), m.defs)
    svg += line(d, 4.6)
    m.add(svg, poly(pts))
    return m


def rose_with_leaves(rng, color=None, leaves=2, size=1.0):
    m = Motif()
    for i in range(leaves):
        ang = rng.uniform(0, 360) if i == 0 else ang + rng.uniform(110, 200)
        lf = leaf(rng, color=GREEN if color else None).place(0, 0, 1.0, ang)
        lf = Motif([Part(p.svg, p.sil) for p in lf.parts], lf.defs)
        # push the leaf out from under the rose
        m.extend(Motif([Part(f'<g transform="translate({f2(260 * math.sin(math.radians(ang)))},{f2(-260 * math.cos(math.radians(ang)))})">{p.svg}</g>',
                             affinity.translate(p.sil, 260 * math.sin(math.radians(ang)), -260 * math.cos(math.radians(ang)))) for p in lf.parts], lf.defs))
    m.extend(rose(rng, color))
    return m.place(s=size) if size != 1 else m


# ================================================================ clouds, rays, smoke (sleeve filler)
def cloud(rng, w=700, h=260, shade=0.75):
    """chicano-style cloud: puffy lobes of varied size over a soft flat base; each lobe outlined, shaded where it
    tucks under the next, and the whole underside sinks into dark shading"""
    m = Motif()
    lobes = []
    n = max(5, int(w / 100))
    base_y = h * 0.28
    for i in range(n):
        t = i / (n - 1)
        x = -w / 2 + w * (0.06 + 0.88 * t) + rng.uniform(-22, 22)
        r = h * (0.24 + 0.4 * math.sin(math.pi * t) ** 0.9) * rng.uniform(0.75, 1.15)
        y = base_y - r * rng.uniform(0.45, 0.85)
        lobes.append((x, y, r))
    order = list(range(n)); rng.shuffle(order)
    base = box(-w / 2 - 10, -h * 2, w / 2 + 10, base_y + h)
    for i in order:
        x, y, r = lobes[i]
        c = Point(x, y).buffer(r, 48).intersection(base)
        if c.is_empty:
            continue
        gdef, gurl = radial(x - r * 0.25, y - r * 0.5, r * 1.35, [(0, 0.0), (0.5, 0.0), (0.8, shade * 0.5), (1.0, shade)])
        m.defs.append(gdef)
        d = d_geom(c)
        # outline the round part only (the flat bottom is drawn once for the whole cloud)
        arc = [(x + r * math.cos(a_), y + r * math.sin(a_)) for a_ in np.linspace(0, 2 * math.pi, 64)]
        arc = [q for q in arc if q[1] < base_y - 1]
        svg = fill(d, gurl, 1.0)
        if len(arc) > 2:
            # keep the arc as one run (start after the gap at the bottom)
            pts_ = np.array([(x + r * math.cos(a_), y + r * math.sin(a_)) for a_ in np.linspace(0, 2 * math.pi, 128)])
            ok = pts_[:, 1] < base_y - 1
            k0 = np.argmin(ok) if not ok.all() else 0
            pts_ = np.roll(pts_, -k0, axis=0); ok = np.roll(ok, -k0)
            svg += line(d_poly(pts_[ok], close=False), 4.4)
        m.add(svg, c)
    un = unary_union([p_.sil for p_ in m.parts])
    gdef, gurl = linear(0, base_y - h * 0.45, 0, base_y, [(0, 0.0), (0.7, shade * 0.8), (1, shade)])
    m.defs.append(gdef)
    m.add(clip_to(fill(d_geom(un), gurl, 1.0), un, m.defs), None)
    # the underside dissolves into smoke instead of ending on a hard line
    mf = flatten(m)
    mid, lid = uid("m"), uid("l")
    mf.defs.append(f'<linearGradient id="{lid}" gradientUnits="userSpaceOnUse" x1="0" y1="{f2(base_y - h * 0.12)}" x2="0" y2="{f2(base_y)}">'
                   f'<stop offset="0" stop-color="#fff"/><stop offset="1" stop-color="#000"/></linearGradient>'
                   f'<mask id="{mid}" maskUnits="userSpaceOnUse" x="-5000" y="-5000" width="10000" height="10000"><rect x="-5000" y="-5000" width="10000" height="10000" fill="url(#{lid})"/></mask>')
    mf.parts[0].svg = f'<g mask="url(#{mid})">{mf.parts[0].svg}</g>'
    mf.parts[0].sil = un.intersection(box(-1e4, -1e4, 1e4, base_y - h * 0.06))
    return mf


def rays(rng, n=9, R=900, spread=120, w0=0.5, op=0.35, center=(0, 0), start=-90):
    """soft light beams fanning from a point (background shading)"""
    m = Motif()
    svg = ""
    gdef, gurl = radial(center[0], center[1], R, [(0, op), (0.6, op * 0.7), (1, 0)])
    m.defs.append(gdef)
    for i in range(n):
        a = math.radians(start - spread / 2 + spread * (i + 0.5) / n)
        da = math.radians(spread / n * w0 / 2)
        pts = [center, (center[0] + R * math.cos(a - da), center[1] + R * math.sin(a - da)), (center[0] + R * math.cos(a + da), center[1] + R * math.sin(a + da))]
        svg += fill(d_poly(pts), gurl, 1.0)
    m.add(svg, None)
    return m


def smoke_fill(rng, geom, defs, op=0.45, sd=18, blobs=26):
    """soft grey smoke/shadow inside a region (background so a sleeve reads as one piece)"""
    minx, miny, maxx, maxy = geom.bounds
    svg = ""
    for _ in range(blobs):
        x = rng.uniform(minx, maxx); y = rng.uniform(miny, maxy)
        r = rng.uniform(0.06, 0.16) * max(maxx - minx, maxy - miny)
        svg += f'<ellipse cx="{f2(x)}" cy="{f2(y)}" rx="{f2(r)}" ry="{f2(r * rng.uniform(0.5, 1))}" fill="{INK}" fill-opacity="{rng.uniform(op * 0.4, op):.2f}" transform="rotate({rng.uniform(0, 180):.0f} {f2(x)} {f2(y)})"/>'
    return clip_to(soft(svg, sd, defs), geom, defs)


# ================================================================ small icons
def star(rng=None, R=200, r=None, pts=5, nautical=True, color=None, op=0.92):
    r = r or R * 0.42
    m = Motif()
    P = []
    for i in range(pts * 2):
        a = math.radians(-90 + i * 180 / pts)
        rr = R if i % 2 == 0 else r
        P.append((rr * math.cos(a), rr * math.sin(a)))
    P = np.array(P)
    svg = ""
    if color:
        svg += fill(d_poly(P), color, 0.9)
    if nautical:  # every point split in two: one half solid
        for i in range(pts):
            tip = P[2 * i]; nb = P[2 * i + 1]
            svg += fill(d_poly([(0, 0), tip, nb]), INK, op)
            svg += line(f"M0,0 L{f2(tip[0])},{f2(tip[1])}", 3.5)
    svg += line(d_poly(P), 5)
    m.add(svg, poly(P))
    return m


def heart_pts(s=200):
    t = np.linspace(0, 2 * math.pi, 120)
    x = 16 * np.sin(t) ** 3
    y = -(13 * np.cos(t) - 5 * np.cos(2 * t) - 2 * np.cos(3 * t) - np.cos(4 * t))
    return np.c_[x, y] * s / 16


def heart(rng=None, s=200, color=None):
    m = Motif()
    P = heart_pts(s)
    d = d_poly(P)
    gdef, gurl = radial(-s * 0.35, -s * 0.35, s * 1.6, [(0, 0.0), (0.35, 0.05), (0.7, 0.55), (1, 0.95)])
    m.defs.append(gdef)
    svg = ""
    if color:
        cdef, curl = radial(-s * 0.3, -s * 0.3, s * 1.5, [(0, 1, RED2 if color == RED else color), (1, 1, color)])
        m.defs.append(cdef)
        svg += fill(d, curl, 0.92)
    svg += fill(d, gurl, 0.85 if not color else 0.45)
    # little highlight shape
    svg += line(f"M{f2(-s * 0.55)},{f2(-s * 0.35)} Q{f2(-s * 0.5)},{f2(-s * 0.62)} {f2(-s * 0.25)},{f2(-s * 0.62)}", 3, 0.6)
    svg += line(d, 5.5)
    m.add(svg, poly(P))
    return m


def banner(rng, word, w=620, h=110, font="UnifrakturMaguntia", bend=60, size=None, color=None):
    """ribbon scroll with folded tails and a word on it (word comes from a fixed safe list)"""
    m = Motif()
    size = size or min(h * 0.85, (w - 80) / max(len(word), 1) * 1.7)
    xs = np.linspace(-w / 2, w / 2, 40)
    top = np.c_[xs, -h / 2 + bend * (xs / (w / 2)) ** 2]
    bot = np.c_[xs[::-1], h / 2 + bend * (xs[::-1] / (w / 2)) ** 2]
    band = np.vstack([top, bot])
    # tails behind
    for sgn in (-1, 1):
        x0 = sgn * w / 2
        y0 = bend
        tail = np.array([(x0 - sgn * 40, y0 - h / 2 + 30), (x0 + sgn * 120, y0 - h / 2 + 50), (x0 + sgn * 80, y0 + 10 + 40), (x0 + sgn * 130, y0 + h / 2 + 60), (x0 - sgn * 40, y0 + h / 2 + 30)])
        dt = d_poly(tail)
        svg = (fill(dt, color, 0.85) if color else "") + fill(dt, INK, 0.55 if not color else 0.35) + line(dt, 4.5)
        # fold shadow
        fold = np.array([(x0 - sgn * 40, y0 - h / 2 + 30), (x0, y0 - h / 2 + 10), (x0, y0 + h / 2 + 10), (x0 - sgn * 40, y0 + h / 2 + 30)])
        svg += fill(d_poly(fold), INK, 0.92)
        m.add(svg, poly(tail).union(poly(fold)))
    d = d_poly(band)
    gdef, gurl = linear(0, -h / 2, 0, h / 2 + bend, [(0, 0.0), (0.6, 0.05), (1, 0.45)])
    m.defs.append(gdef)
    pid = uid("p")
    m.defs.append(f'<path id="{pid}" d="M{f2(-w / 2 + 30)},{f2(size * 0.35 + bend * 0.92)} Q0,{f2(size * 0.35 - bend * 1.0)} {f2(w / 2 - 30)},{f2(size * 0.35 + bend * 0.92)}"/>')
    svg = (fill(d, color, 0.85) if color else "") + fill(d, gurl, 1) + line(d, 5)
    svg += (f'<text font-family="{font}" font-size="{f2(size)}" fill="{INK}" text-anchor="middle">'
            f'<textPath href="#{pid}" startOffset="50%">{word}</textPath></text>')
    m.add(svg, poly(band))
    return m


def script(word, size=150, font="MrDafoe", flourish=True, arc=0, op=1.0, w=None):
    """lettering only (script or blackletter); arc>0 curves it upward"""
    m = Motif()
    w = w or size * len(word) * 0.55
    svg = ""
    if arc:
        pid = uid("p")
        m.defs.append(f'<path id="{pid}" d="M{f2(-w / 2)},{f2(arc)} Q0,{f2(-arc)} {f2(w / 2)},{f2(arc)}"/>')
        svg += (f'<text font-family="{font}" font-size="{f2(size)}" fill="{INK}" fill-opacity="{op}" text-anchor="middle">'
                f'<textPath href="#{pid}" startOffset="50%">{word}</textPath></text>')
    else:
        svg += text(word, 0, size * 0.32, size, font, op=op)
    if flourish:
        y = size * 0.55 + (arc * 0.6 if arc else 0)
        svg += line(f"M{f2(-w * 0.42)},{f2(y)} C{f2(-w * 0.1)},{f2(y + size * 0.18)} {f2(w * 0.1)},{f2(y - size * 0.12)} {f2(w * 0.45)},{f2(y + size * 0.02)}", size * 0.035)
    m.add(svg, box(-w / 2, -size * 0.7 - abs(arc), w / 2, size * 0.75 + abs(arc)))
    return m
