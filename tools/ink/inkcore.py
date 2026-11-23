"""inkcore.py: tiny vector toolkit for tattoo art. Parts are (svg, silhouette); later parts hide earlier ones (masks),
so outlines never show through shapes in front of them. Everything is drawn in one ink colour with varying opacity
(black & grey shading) plus optional colour fills, then rasterised in Chromium (rast.js) to transparent PNGs."""
import math, json, os, subprocess
import numpy as np
from shapely.geometry import Point, Polygon, LineString, MultiPolygon, box, GeometryCollection
from shapely.ops import unary_union
from shapely import affinity

INK = "#0f1215"
_uid = [0]


def uid(p="g"):
    _uid[0] += 1
    return f"{p}{_uid[0]}"


def f2(x):
    return f"{x:.1f}"


# ---------------------------------------------------------------- geometry helpers
def bez(p0, p1, p2, p3, n=24):
    t = np.linspace(0, 1, n)[:, None]
    p0, p1, p2, p3 = map(np.asarray, (p0, p1, p2, p3))
    return (1 - t) ** 3 * p0 + 3 * (1 - t) ** 2 * t * p1 + 3 * (1 - t) * t ** 2 * p2 + t ** 3 * p3


def path_pts(segs):
    """segs: list of cubic segments [(p0,p1,p2,p3), ...] -> polyline points"""
    out = []
    for s in segs:
        b = bez(*s)
        out.extend(b if not out else b[1:])
    return np.array(out)


def d_poly(pts, close=True):
    pts = np.asarray(pts)
    s = "M" + " L".join(f"{f2(x)},{f2(y)}" for x, y in pts)
    return s + (" Z" if close else "")


def d_geom(g):
    """shapely (multi)polygon -> svg path d (with holes, evenodd)"""
    if g is None or g.is_empty:
        return ""
    if isinstance(g, (MultiPolygon, GeometryCollection)):
        return " ".join(d_geom(x) for x in g.geoms if not x.is_empty and x.geom_type in ("Polygon", "MultiPolygon"))
    if g.geom_type != "Polygon":
        return ""
    s = d_poly(np.array(g.exterior.coords)[:-1])
    for r in g.interiors:
        s += " " + d_poly(np.array(r.coords)[:-1])
    return s


def poly(pts):
    p = Polygon(pts)
    return p if p.is_valid else p.buffer(0)


def stroke_geom(pts, w, cap="round"):
    return LineString(pts).buffer(w / 2, cap_style={"round": 1, "flat": 2, "square": 3}[cap], join_style=1)


def taper_stroke(pts, w0, w1, wmid=None):
    """polygon of a stroke whose width goes w0 -> (wmid) -> w1 along pts (brush taper)"""
    pts = np.asarray(pts, float)
    n = len(pts)
    t = np.linspace(0, 1, n)
    if wmid is None:
        w = w0 + (w1 - w0) * t
    else:
        w = np.where(t < 0.5, w0 + (wmid - w0) * t * 2, wmid + (w1 - wmid) * (t - 0.5) * 2)
    d = np.gradient(pts, axis=0)
    d /= np.maximum(np.linalg.norm(d, axis=1, keepdims=True), 1e-9)
    nrm = np.c_[-d[:, 1], d[:, 0]]
    L = pts + nrm * (w / 2)[:, None]
    R = pts - nrm * (w / 2)[:, None]
    return poly(np.vstack([L, R[::-1]]))


# ---------------------------------------------------------------- parts
class Part:
    def __init__(self, svg, sil=None):
        self.svg = svg
        self.sil = sil


class Motif:
    """ordered parts (back to front) + defs. place() returns a new Motif transformed."""

    def __init__(self, parts=None, defs=None):
        self.parts = parts or []
        self.defs = defs or []

    def add(self, svg, sil=None):
        self.parts.append(Part(svg, sil))
        return self

    def extend(self, m):
        self.parts += m.parts
        self.defs += m.defs
        return self

    def sil(self):
        gs = [p.sil for p in self.parts if p.sil is not None and not p.sil.is_empty]
        return unary_union(gs) if gs else None

    def place(self, x=0, y=0, s=1.0, rot=0.0, flip=False):
        tr = f"translate({f2(x)},{f2(y)}) rotate({f2(rot)}) scale({s * (-1 if flip else 1):.4f},{s:.4f})"
        out = Motif(defs=list(self.defs))
        for p in self.parts:
            g = None
            if p.sil is not None:
                g = affinity.scale(p.sil, s * (-1 if flip else 1), s, origin=(0, 0))
                g = affinity.rotate(g, rot, origin=(0, 0))
                g = affinity.translate(g, x, y)
            out.parts.append(Part(f'<g transform="{tr}">{p.svg}</g>', g))
        return out


def render_parts(parts, defs, hide_with_later=True):
    """svg body for parts: each part masked by the union of later parts' silhouettes that overlap it."""
    body = []
    sils = [p.sil for p in parts]
    for i, p in enumerate(parts):
        later = [s for s in sils[i + 1:] if s is not None and not s.is_empty]
        if hide_with_later and later:
            lu = unary_union(later)
            # quick reject: does it overlap this part at all?
            if p.sil is not None and not p.sil.is_empty and not lu.intersects(p.sil.buffer(12)):
                body.append(p.svg)
                continue
            mid = uid("m")
            defs.append(f'<mask id="{mid}" maskUnits="userSpaceOnUse" x="-5000" y="-5000" width="10000" height="10000">'
                        f'<rect x="-5000" y="-5000" width="10000" height="10000" fill="#fff"/>'
                        f'<path d="{d_geom(lu.buffer(1.5))}" fill="#000" fill-rule="evenodd"/></mask>')
            body.append(f'<g mask="url(#{mid})">{p.svg}</g>')
        else:
            body.append(p.svg)
    return "".join(body)


def flatten(m):
    """bake a motif into one part (internal occlusion resolved), keeping its outer silhouette"""
    defs = list(m.defs)
    svg = render_parts(m.parts, defs)
    out = Motif([Part(svg, m.sil())], defs)
    return out


def document(motifs, W, H, extra_defs=None, post=""):
    """motifs back to front -> full svg string"""
    parts, defs = [], list(extra_defs or [])
    for m in motifs:
        mf = flatten(m)
        parts += mf.parts
        defs += mf.defs
    body = render_parts(parts, defs)
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">'
            f'<defs>{"".join(defs)}</defs>{body}{post}</svg>')


# ---------------------------------------------------------------- paint helpers
def radial(cx, cy, r, stops, fx=None, fy=None):
    """stops: [(offset, opacity[, colour])] -> (defs, url)"""
    gid = uid("r")
    st = "".join(f'<stop offset="{t[0]}" stop-color="{t[2] if len(t) > 2 else INK}" stop-opacity="{t[1]}"/>' for t in stops)
    fxy = f' fx="{f2(fx)}" fy="{f2(fy)}"' if fx is not None else ""
    return (f'<radialGradient id="{gid}" gradientUnits="userSpaceOnUse" cx="{f2(cx)}" cy="{f2(cy)}" r="{f2(r)}"{fxy}>{st}</radialGradient>', f"url(#{gid})")


def linear(x1, y1, x2, y2, stops):
    gid = uid("l")
    st = "".join(f'<stop offset="{s[0]}" stop-color="{s[2] if len(s) > 2 else INK}" stop-opacity="{s[1]}"/>' for s in stops)
    return (f'<linearGradient id="{gid}" gradientUnits="userSpaceOnUse" x1="{f2(x1)}" y1="{f2(y1)}" x2="{f2(x2)}" y2="{f2(y2)}">{st}</linearGradient>', f"url(#{gid})")


def blur(sd):
    fid = uid("f")
    return (f'<filter id="{fid}" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="{sd}"/></filter>', f"url(#{fid})")


def fill(d, paint=INK, op=1.0, extra=""):
    return f'<path d="{d}" fill="{paint}" fill-opacity="{op}" fill-rule="evenodd" {extra}/>'


LINE_K = [1.0]   # line widths are physical: set per canvas (texture pixels per 0.54 mm)


def line(d, w=5, op=1.0, col=INK, extra=""):
    """outline with a constant physical width whatever the motif's scale (a tattoo needle doesn't scale)"""
    return (f'<path d="{d}" fill="none" stroke="{col}" stroke-width="{w * 0.5 * LINE_K[0]:.2f}" stroke-opacity="{op}" '
            f'stroke-linecap="round" stroke-linejoin="round" vector-effect="non-scaling-stroke" {extra}/>')


def clip_to(svg, geom, defs):
    cid = uid("c")
    defs.append(f'<clipPath id="{cid}"><path d="{d_geom(geom)}" fill-rule="evenodd"/></clipPath>')
    return f'<g clip-path="url(#{cid})">{svg}</g>'


def soft(svg, sd, defs):
    fdef, furl = blur(sd)
    defs.append(fdef)
    return f'<g filter="{furl}">{svg}</g>'


def text(s, x, y, size, font="UnifrakturMaguntia", anchor="middle", op=1.0, col=INK, extra=""):
    return (f'<text x="{f2(x)}" y="{f2(y)}" font-family="{font}" font-size="{f2(size)}" text-anchor="{anchor}" '
            f'fill="{col}" fill-opacity="{op}" {extra}>{s}</text>')


def rasterise(jobs):
    jf = "/tmp/claude-0/ink/jobs.json"
    json.dump(jobs, open(jf, "w"))
    subprocess.run(["node", "/tmp/claude-0/ink/rast.js", jf], check=True)
