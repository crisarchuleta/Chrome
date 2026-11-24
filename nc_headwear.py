"""Fitted head pieces for the MakeHuman heads: combat / night-ops helmet, durags, ski masks, knight's great helm and
goggles. Every piece is built from the head it sits on (same idea as build_cap in nc_garments.py): cut the head
skin along a hem line, lift it off the skin, smooth it into fabric or a hard shell and keep it outside the head
with the collider, so nothing pokes through on any of the ten bodies.

Front is -y, the character's left is +x, z is up. k = body height / 1.78 m."""
import numpy as np
import bpy
from scipy.spatial import cKDTree
import nc_garments as NG
from nc_garments import (clip, keep_big, edges_of, vnormals, laplace, make_object, material, make_tube, merge_parts,
                         boundary_loops, subdivide, head_frame, _bodydata_eyes, _extend_loop)


# ------------------------------------------------------------------------------------------------ head landmarks
class Head:
    def __init__(self, b):
        k = b.k
        self.b, self.k = b, k
        self.hm, self.top, self.eye_z, self.c = head_frame(b)
        H = b.co[self.hm]
        self.H, self.HN = H, b.N[self.hm]
        c = self.c
        self.Rh = np.hypot(H[:, 0] - c[0], H[:, 1] - c[1]).max()
        eyes = _bodydata_eyes(b)
        if eyes:
            self.eyes = [np.array(e) for e in eyes]
            self.eye_z = float((eyes[0][2] + eyes[1][2]) / 2)
        else:
            self.eyes = [np.array([c[0] + s * 0.03 * k, c[1] - 0.08 * k, self.eye_z]) for s in (1, -1)]
        ez = self.eye_z
        mid = H[np.abs(H[:, 0] - c[0]) < 0.008 * k]
        fm = mid[mid[:, 1] < c[1] - 0.02 * k]
        m = fm[(fm[:, 2] < ez - 0.06 * k) & (fm[:, 2] > ez - 0.105 * k)]
        self.mouth_z = float(m[np.argmin(m[:, 1]), 2]) if len(m) else ez - 0.08 * k
        ch = fm[fm[:, 1] < c[1] - 0.05 * k]
        self.chin_z = float(ch[:, 2].min()) if len(ch) else ez - 0.13 * k
        self.chin_y = float(ch[np.argmin(ch[:, 2]), 1]) if len(ch) else c[1] - 0.08 * k
        self.bottom = float(H[:, 2].min())
        self.tree = cKDTree(H)

    def front(self, P):  # +1 forehead .. -1 back of the head
        return np.clip((self.c[1] - P[:, 1]) / self.Rh, -1, 1)

    def ang(self, P):  # 0 straight ahead, +-pi at the back, + towards the character's left (+x)
        ph = np.arctan2(P[:, 1] - self.c[1], P[:, 0] - self.c[0])
        return np.angle(np.exp(1j * (ph + np.pi / 2)))

    def faces(self, sub=1):
        b = self.b
        F = [f for f in b.faces if all(self.hm[v] for v in f)]
        P = b.co
        used = sorted({v for f in F for v in f})
        remap = -np.ones(len(P), int); remap[used] = np.arange(len(used))
        P = P[used]; F = [[int(remap[v]) for v in f] for f in F]
        for _ in range(sub):
            P, F, _ = subdivide(P, F, {})
        return P, F

    def radius_at(self, phi, z, dz=0.009):
        """Largest head radius around the head centre at angle phi (0 = front) and height z (per-bin max)."""
        k, c, H = self.k, self.c, self.H
        s = H[np.abs(H[:, 2] - z) < dz * k]
        if len(s) == 0:
            return np.full(np.shape(phi), 0.06 * k)
        a = self.ang(s); r = np.hypot(s[:, 0] - c[0], s[:, 1] - c[1])
        bins = np.linspace(-np.pi, np.pi, 73)
        idx = np.clip(np.digitize(a, bins) - 1, 0, 71)
        rb = np.zeros(72)
        for i in range(72):
            if (idx == i).any():
                rb[i] = r[idx == i].max()
        for i in range(72):  # fill empty bins from their neighbours
            if rb[i] == 0:
                rb[i] = max(rb[(i - 1) % 72], rb[(i + 1) % 72])
        rb = np.maximum(rb, np.roll(rb, 1)); rb = np.maximum(rb, np.roll(rb, -1))
        ctr = (bins[:-1] + bins[1:]) / 2
        return np.interp(np.angle(np.exp(1j * np.asarray(phi))), np.r_[ctr - 2 * np.pi, ctr, ctr + 2 * np.pi], np.r_[rb, rb, rb])

    def at(self, phi, z, r):
        phi = np.asarray(phi); z = np.broadcast_to(z, np.shape(phi)); r = np.broadcast_to(r, np.shape(phi))
        return np.stack([self.c[0] + np.sin(phi) * r, self.c[1] - np.cos(phi) * r, z], axis=-1)


def _shell(o, P, F, off, rounds, gap, smooth=5):
    P, F, _ = keep_big(P, F, {}, frac=0.5)
    E = edges_of(F)
    X = P + vnormals(P, F) * off
    for _ in range(rounds):
        X = laplace(X, E, smooth, taubin=True)
        X = o.col.push(X, gap)
    return X, F, E


def _smooth_loop(X, loop, iters=6, col=None, gap=0.0):
    X = X.copy(); L = np.asarray(loop)
    for _ in range(iters):
        p = X[L]
        X[L] = 0.5 * p + 0.25 * (np.roll(p, 1, 0) + np.roll(p, -1, 0))
        if col is not None:
            X[L] = col.push(X[L], gap)
    return X


def _orient_out(V, F, centre):
    F = [list(f) for f in F]
    fc = np.array([V[f].mean(0) for f in F])
    fn = np.cross(V[[f[1] for f in F]] - V[[f[0] for f in F]], V[[f[2] for f in F]] - V[[f[0] for f in F]])
    if np.mean(np.einsum("ij,ij->i", fn, fc - centre)) < 0:
        F = [f[::-1] for f in F]
    return F


def _patch(X, F, sel, off):
    """Faces whose vertices are all selected, copied and lifted along the normals (raised panels, bands, rails)."""
    N = vnormals(X, F)
    Fs = [f for f in F if all(sel[v] for v in f)]
    used = sorted({v for f in Fs for v in f})
    if not used:
        return None
    remap = -np.ones(len(X), int); remap[used] = np.arange(len(used))
    return X[used] + N[used] * off, [[int(remap[v]) for v in f] for f in Fs]


def _taut(col, pts, gap, iters=120, n=80):
    """A strap or seam pulled tight over the surface: start from a polyline outside the head, then repeatedly
    shorten it (smoothing) and push it back out of the collider. It bridges creases like a real strap."""
    pts = np.asarray(pts, float)
    d = np.r_[0, np.cumsum(np.linalg.norm(np.diff(pts, axis=0), axis=1))]
    t = np.linspace(0, d[-1], n)
    Q = np.stack([np.interp(t, d, pts[:, i]) for i in range(3)], 1)
    _, j = col.tree.query(Q[1:-1])
    Q[1:-1] = col.P[j] + col.N[j] * gap
    for _ in range(iters):
        Q[1:-1] = 0.5 * Q[1:-1] + 0.25 * (Q[:-2] + Q[2:])
        Q[1:-1] = col.push(Q[1:-1], gap)
    return Q


def _ribbon(Q, Nref, width):
    """Flat strap along a path, lying on the surface whose normals are given by Nref (n,3)."""
    T = np.gradient(Q, axis=0); T /= np.linalg.norm(T, axis=1, keepdims=True) + 1e-12
    B = np.cross(T, Nref); B /= np.linalg.norm(B, axis=1, keepdims=True) + 1e-12
    w = np.broadcast_to(np.asarray(width, float), (len(Q),))[:, None]
    V = np.vstack([Q - B * w / 2, Q + B * w / 2])
    n = len(Q)
    F = [[i, i + 1, n + i + 1, n + i] for i in range(n - 1)]
    return V, F


def _surf_normals(col, Q):
    d, j = col.tree.query(Q)
    return col.N[j]


def _blob(centre, radii, n=10, m=16, noise=0.0, seed=0):
    rng = np.random.default_rng(seed)
    V = []
    for i in range(n + 1):
        th = np.pi * i / n - np.pi / 2
        for j in range(m):
            ph = 2 * np.pi * j / m
            d = np.array([np.cos(th) * np.cos(ph), np.cos(th) * np.sin(ph), np.sin(th)])
            V.append(centre + d * radii * (1 + noise * (rng.random() - 0.5)))
    F = [[i * m + j, i * m + (j + 1) % m, (i + 1) * m + (j + 1) % m, (i + 1) * m + j] for i in range(n) for j in range(m)]
    return np.array(V), F


def _mat(name, rgb, rough=0.85, metal=0.0, sheen=0.0):
    m = material(name, tuple(rgb[:3]) + (1,), rough=rough)
    bs = m.node_tree.nodes.get("Principled BSDF")
    for key, val in (("Metallic", metal), ("Sheen Weight", sheen)):
        try:
            bs.inputs[key].default_value = val
        except Exception:
            pass
    return m


def _add_collider(o, X, F, centre, gap):
    N = vnormals(X, F)
    flip = np.einsum("ij,ij->i", N, X - centre) < 0
    N[flip] *= -1
    o.col.add(X + N * gap, N); o.col_noarm.add(X + N * gap, N)


def _col_of(X, F, centre):
    col = NG.Collider(); col.dmax = 1e9
    N = vnormals(X, F)
    flip = np.einsum("ij,ij->i", N, X - centre) < 0
    N[flip] *= -1
    col.add(X, N)
    return col


# ------------------------------------------------------------------------------------------------------- durag
def build_durag(o, name, color=(0.01, 0.01, 0.01), velvet=False):
    """Skin-tight durag: crown cut from the forehead, over the tops of the ears, down to the nape; a centre seam
    over the top, the tie band along the edge, the knot at the nape and the tail flap with both tie ends."""
    b = o.b; k = b.k; h = Head(b)
    ez, c = h.eye_z, h.c
    P, F = h.faces(sub=1)
    fr = h.front(P)
    zl = ez + k * np.interp(fr, [-1, -0.62, -0.32, 0.0, 1], [-0.112, -0.085, 0.028, 0.036, 0.05])
    P, F, _ = clip(P, F, zl - P[:, 2], {})
    X, F, E = _shell(o, P, F, 0.0045 * k, 3, 0.004 * k, smooth=3)
    rough = 0.95 if velvet else 0.45
    m_main = _mat(name + "_Main", color, rough=rough, sheen=0.0)
    m_dark = _mat(name + "_Seam", np.array(color[:3]) * 0.7, rough=rough)
    ll = max(boundary_loops(F), key=len)
    X = _smooth_loop(X, ll, 8, o.col, 0.004 * k)
    # rolled hem
    base = X[ll].copy(); N = vnormals(X, F)
    X, F, R, _ = _extend_loop(X, F, ll, None, [base - N[ll] * 0.003 * k + np.array([0, 0, 0.002 * k])], np.array(["M"] * len(X), dtype=object), "Hem")
    out = [make_object(b, f"{b.obj.name}_{name}", X, F, [m_main], None, None, thick=0.0015 * k, subsurf=1)]
    centre = np.array([c[0], c[1], ez])
    col = _col_of(X[:len(R)], F, centre)
    nhead = len(base)
    # tie band: the strip along the edge where the ties wrap round (raised 1.5 mm)
    parts = []
    hem = base + N[ll] * 0.0012 * k
    for _ in range(4):
        hem = 0.5 * hem + 0.25 * (np.roll(hem, 1, 0) + np.roll(hem, -1, 0))
    Vt, Ft = make_tube(hem, 0.0032 * k, nseg=8, closed=True)  # the tie band rolled along the edge
    parts.append((Vt, Ft, 0))
    # centre seam over the top, forehead to nape
    fpt = base[np.argmax(h.front(base) - 3 * np.abs(base[:, 0] - c[0]) / k)]
    bpt = base[np.argmin(h.front(base) + 3 * np.abs(base[:, 0] - c[0]) / k)]
    arc = [fpt, np.array([c[0], c[1] - 0.04 * k, h.top + 0.06 * k]), np.array([c[0], c[1] + 0.06 * k, h.top + 0.04 * k]), bpt]
    Q = _taut(col, arc, 0.0012 * k, iters=150)
    Vt, Ft = make_tube(Q[2:-2], 0.0016 * k, nseg=6)
    parts.append((Vt, Ft, 0))
    # knot at the nape
    nape = bpt.copy()
    Nn = np.array([0, 1.0, -0.2]); Nn /= np.linalg.norm(Nn)
    kc = nape + Nn * 0.009 * k + np.array([0, 0, 0.004 * k])
    Vk, Fk = _blob(kc, np.array([0.02, 0.011, 0.013]) * k, noise=0.25, seed=3)
    parts.append((Vk, Fk, 0))
    # tail flap + two tie ends hanging down the back of the neck, standing a little off the body
    def hang(x0, width0, width1, length, extra, seed):
        rows = 12
        Q = np.array([kc + np.array([x0 * t * 0.6, 0.0, -length * t]) for t in np.linspace(0, 1, rows)])
        for _ in range(40):
            Q[1:] = o.col.push(Q[1:], 0.006 * k + extra)
            Q[1:-1] = 0.5 * Q[1:-1] + 0.25 * (Q[:-2] + Q[2:])
        Q[1:] = o.col.push(Q[1:], 0.006 * k + extra)
        out_n = np.zeros_like(Q); out_n[:, 1] = 1.0
        w = np.linspace(width0, width1, rows)
        V, Fr = _ribbon(Q, out_n, w)
        V += np.random.default_rng(seed).normal(0, 0.0004 * k, V.shape)
        return V, Fr
    Vt, Ftl = hang(0.0, 0.07 * k, 0.062 * k, 0.15 * k, 0.004 * k, 1)
    parts.append((Vt, _orient_out(Vt, Ftl, centre + np.array([0, -0.2 * k, 0])), 0))
    for x0, L, ex, sd in ((0.035 * k, 0.17 * k, 0.009 * k, 2), (-0.03 * k, 0.14 * k, 0.011 * k, 4)):
        Vt, Ftl = hang(x0, 0.024 * k, 0.02 * k, L, ex, sd)
        parts.append((Vt, _orient_out(Vt, Ftl, centre + np.array([0, -0.2 * k, 0])), 1))
    Vd, Fd, md = merge_parts(parts)
    out.append(make_object(b, f"{b.obj.name}_{name}_Ties", Vd, Fd, [m_main, m_dark], md, None, thick=0.0012 * k, subsurf=1))
    o.objs.extend(out)
    _add_collider(o, X, F, centre, 0.003 * k)
    return out[0]


# --------------------------------------------------------------------------------------------------- ski masks
def build_balaclava(o, name, color=(0.01, 0.01, 0.01), accent=None, style="classic", pom=False):
    """Knit ski mask over the whole head and neck. classic = two eye holes and a mouth hole, open = one face
    opening (brows to under the mouth). Rolled rib edges round every opening, a little bib over the neck base,
    and an optional pom on top."""
    b = o.b; k = b.k; h = Head(b)
    ez, c = h.eye_z, h.c
    P, F = h.faces(sub=1)
    x, y, z = P[:, 0], P[:, 1], P[:, 2]
    frontm = y < c[1] - 0.03 * k
    f = -np.ones(len(P))
    if style == "open":
        top, bot = ez + 0.024 * k, h.mouth_z - 0.03 * k
        zc, hz = (top + bot) / 2, (top - bot) / 2
        e = np.abs((x - c[0]) / (0.052 * k)) ** 3.2 + np.abs((z - zc) / hz) ** 3.2
        f = np.where(frontm, np.maximum(f, 1 - e), f)
    else:
        for eye in h.eyes:
            e = ((x - eye[0]) / (0.025 * k)) ** 2 + ((z - eye[2] - 0.002 * k) / (0.0145 * k)) ** 2
            f = np.where(frontm, np.maximum(f, 1 - e), f)
        e = ((x - c[0]) / (0.025 * k)) ** 2 + ((z - h.mouth_z) / (0.0125 * k)) ** 2
        f = np.where(frontm, np.maximum(f, 1 - e), f)
    P, F, _ = clip(P, F, f, {})
    P, F, _ = keep_big(P, F, {}, frac=0.5)
    E = edges_of(F)
    X = P + vnormals(P, F) * 0.007 * k
    for _ in range(14):  # knit is under tension: it spans the eye sockets, under the nose and the chin/neck crease
        X = laplace(X, E, 3, lam=0.5)
        X = o.col.push(X, 0.0055 * k)
    X = laplace(X, E, 3, taubin=True); X = o.col.push(X, 0.0055 * k)
    for l in boundary_loops(F):
        X = _smooth_loop(X, l, 6, o.col, 0.0055 * k)
    nshell = len(X)
    loops = boundary_loops(F)
    zs = [X[l, 2].mean() for l in loops]
    neck = loops[int(np.argmin(zs))]
    holes = [l for l in loops if l is not neck]
    N = vnormals(X, F)
    R = np.array(["M"] * len(X), dtype=object)
    # rib roll on every opening: the knit turns in towards the skin
    for l in holes:
        base = X[l].copy()
        cen = base.mean(0)
        inward = (cen - base); inward /= np.linalg.norm(inward, axis=1, keepdims=True) + 1e-12
        r1 = base + inward * 0.0018 * k - N[l] * 0.0028 * k
        r2 = base + inward * 0.001 * k - N[l] * 0.0058 * k
        X, F, R, _ = _extend_loop(X, F, l, None, [r1, r2], R, "Rib")
    # bib: the knit continues a little over the neck base and sits on whatever is underneath
    base = X[neck].copy(); cc = base.mean(0)
    rings = []
    for t in (0.33, 0.66, 1.0):
        pts = base.copy(); pts[:, 2] -= 0.05 * k * t
        pts[:, :2] = cc[:2] + (pts[:, :2] - cc[:2]) * (1 + 0.3 * t ** 1.5)
        rings.append(pts)
    X, F, R, last = _extend_loop(X, F, neck, None, rings, R, "Bib")
    bib = np.where(R == "Bib")[0]
    E = edges_of(F)
    for _ in range(6):
        X[bib] = o.col.push(X[bib], 0.005 * k)
        X = laplace(X, E, 2, mask=(R == "Bib"))
    X[bib] = o.col.push(X[bib], 0.005 * k)
    mi = [1 if all(R[v] == "Rib" for v in f) else 0 for f in F]
    acc = accent if (accent is not None and style != "open") else color
    mats = [_mat(name + "_Knit", color, rough=1.0), _mat(name + "_Rib", acc, rough=1.0)]
    ob = make_object(b, f"{b.obj.name}_{name}", X, F, mats, mi, None, thick=0.003 * k, subsurf=1)
    o.objs.append(ob)
    centre = np.array([c[0], c[1], ez])
    if pom:
        tp = X[:nshell][np.argmax(X[:nshell, 2])]
        V, Fp = _blob(tp + np.array([0, 0, 0.024 * k]), np.array([0.03, 0.03, 0.027]) * k, n=12, m=20, noise=0.18, seed=7)
        o.objs.append(make_object(b, f"{b.obj.name}_{name}_Pom", V, Fp, [_mat(name + "_Pom", accent or color, rough=1.0, sheen=1.0)], None, None, thick=0, subsurf=1))
    _add_collider(o, X[:nshell], [f for f in F if max(f) < nshell], centre, 0.003 * k)
    return ob


# ------------------------------------------------------------------------------------------------------ helmet
def build_helmet(o, name, color=(0.33, 0.37, 0.2), nvg=False, strap=True):
    """Modern high-cut combat helmet: smooth padded shell clear of the hair, cut high over the ears, rubber edge
    trim, Y-shaped chin strap pulled tight under the jaw. nvg adds side rails, the front shroud and flipped-up
    night-vision goggles."""
    b = o.b; k = b.k; h = Head(b)
    ez, c = h.eye_z, h.c
    P, F = h.faces(sub=0)
    fr = h.front(P)
    zl = ez + k * np.interp(fr, [-1, -0.55, -0.3, -0.05, 0.3, 1], [-0.05, -0.04, 0.026, 0.032, 0.038, 0.05])
    P, F, _ = clip(P, F, zl - P[:, 2], {})
    P, F, _ = subdivide(P, F, {})
    X, F, E = _shell(o, P, F, 0.026 * k, 10, 0.022 * k, smooth=8)
    X = laplace(X, E, 10, taubin=True)
    X = o.col.push(X, 0.02 * k)
    centre = np.array([c[0], c[1], ez])
    m_shell = _mat(name + "_Shell", color, rough=0.72)
    m_dark = _mat(name + "_Trim", (0.02, 0.02, 0.022), rough=0.8)
    out = [make_object(b, f"{b.obj.name}_{name}", X, F, [m_shell], None, None, thick=0.005 * k, subsurf=1)]
    col = _col_of(X, F, centre)
    ll = max(boundary_loops(F), key=len)
    X = _smooth_loop(X, ll, 10, o.col, 0.02 * k)
    rim = X[ll].copy()
    for _ in range(4):
        rim = 0.5 * rim + 0.25 * (np.roll(rim, 1, 0) + np.roll(rim, -1, 0))
    parts = []
    Vt, Ft = make_tube(rim, 0.0055 * k, nseg=8, closed=True)
    parts.append((Vt, Ft, 1))
    if strap:
        # Y strap: in front of and behind the ear, meeting under the ear, then tight under the chin
        def rim_at(frv, side):
            fr_r = h.front(rim)
            cand = np.where(np.sign(rim[:, 0] - c[0]) == side)[0]
            return rim[cand[np.argmin(np.abs(fr_r[cand] - frv))]]
        chin = np.array([c[0], h.chin_y + 0.012 * k, h.chin_z - 0.004 * k])
        js = []
        for side in (1, -1):
            j = h.at(side * np.radians(97), ez - 0.062 * k, h.radius_at(side * np.radians(97), ez - 0.062 * k) + 0.01 * k)
            js.append(j)
            for frv in (0.3, -0.42):
                a = rim_at(frv, side)
                Q = _taut(o.col, [a, (a + j) / 2 + np.array([side * 0.03 * k, 0, 0]), j], 0.0035 * k, iters=120, n=40)
                V, Fr = _ribbon(Q, _surf_normals(o.col, Q), 0.009 * k)
                parts.append((V, Fr, 1))
        Q = _taut(o.col, [js[0], chin + np.array([0.035 * k, 0.0, -0.004 * k]), chin + np.array([0, 0, -0.006 * k]),
                          chin + np.array([-0.035 * k, 0.0, -0.004 * k]), js[1]], 0.0035 * k, iters=200, n=90)
        V, Fr = _ribbon(Q, _surf_normals(o.col, Q), 0.011 * k)
        parts.append((V, Fr, 1))
        for j in js:  # junction slider
            nrm = _surf_normals(o.col, j[None])[0]
            Vb, Fb = _blob(j + nrm * 0.002 * k, np.array([0.009, 0.009, 0.009]) * k, n=6, m=10)
            parts.append((Vb, Fb, 1))
    if nvg:
        up = (X[:, 2] - ez) / (h.top + 0.02 * k - ez)
        fr_x = h.front(X); ax = np.abs(h.ang(X))
        # side rails: a strip just above the rim, temple to behind the ear
        rail = (ax > np.radians(55)) & (ax < np.radians(130)) & (up > 0.24) & (up < 0.36)
        pt = _patch(X, F, rail, 0.0045 * k)
        if pt:
            parts.append((pt[0], pt[1], 1))
        # front shroud
        shroud = (ax < np.radians(17)) & (up > 0.3) & (up < 0.6)
        pt = _patch(X, F, shroud, 0.004 * k)
        if pt:
            parts.append((pt[0], pt[1], 1))
            sc = pt[0].mean(0)
            nrm = sc - centre; nrm /= np.linalg.norm(nrm)
            # flip-up mount arm and the binocular device resting up in front of the helmet
            fwd = np.array([0, -1.0, 0]); upv = np.array([0, 0, 1.0])
            pivot = sc + nrm * 0.016 * k
            Vt, Ft = make_tube(np.array([sc + nrm * 0.004 * k, pivot]), 0.006 * k, nseg=8)
            parts.append((Vt, Ft, 1))
            dirv = 0.5 * fwd + 0.87 * upv  # tubes point up and forward (stowed)
            hb = pivot + fwd * 0.012 * k + upv * 0.006 * k
            Vb, Fb = _blob(hb, np.array([0.03, 0.013, 0.012]) * k, n=6, m=12)
            parts.append((Vb, Fb, 1))
            for s in (1, -1):
                a0 = hb + np.array([s * 0.019 * k, 0, 0]) - dirv * 0.008 * k
                a1 = a0 + dirv * 0.05 * k
                Vt, Ft = make_tube(np.array([a0 + (a1 - a0) * t for t in np.linspace(0, 1, 6)]), np.linspace(0.0115, 0.0135, 6) * k, nseg=14)
                parts.append((Vt, Ft, 1))
                ring = [a1 + 0.0002 * k * dirv + 0.011 * k * (np.cos(t) * np.array([1.0, 0, 0]) + np.sin(t) * np.cross(dirv, [1.0, 0, 0]))
                        for t in np.linspace(0, 2 * np.pi, 14, endpoint=False)]
                Vl = np.vstack([ring, [a1 + dirv * 0.001 * k]]); ci = len(Vl) - 1
                parts.append((Vl, [[i, (i + 1) % 14, ci] for i in range(14)], 2))
        # counterweight pouch at the back
        pouch = (ax > np.radians(150)) & (up > 0.15) & (up < 0.42)
        pt = _patch(X, F, pouch, 0.009 * k)
        if pt:
            parts.append((pt[0], pt[1], 1))
    Vd, Fd, md = merge_parts(parts)
    m_lens = _mat(name + "_Lens", (0.05, 0.25, 0.12), rough=0.05, metal=0.3)
    out.append(make_object(b, f"{b.obj.name}_{name}_Gear", Vd, Fd, [m_shell, m_dark, m_lens], md, None, thick=0, subsurf=1))
    o.objs.extend(out)
    _add_collider(o, X, F, centre, 0.006 * k)
    return out[0]


# ------------------------------------------------------------------------------------------- knight's great helm
def build_knight_helm(o, name, color=(0.66, 0.68, 0.72)):
    """Flat-topped great helm: one closed bucket round the whole head (clear of the ears, nose and hair) resting
    above the shoulders, a central ridge, eye slits either side of a nose bar, a raised cross of reinforcing
    bands with rivets, breathing holes on the lower cheeks and a rolled bottom edge."""
    b = o.b; k = b.k; h = Head(b)
    ez, c, H = h.eye_z, h.c, h.H
    cx, cy = c[0], (H[:, 1].min() + H[:, 1].max()) / 2
    a0 = (H[:, 0].max() - H[:, 0].min()) / 2 + 0.012 * k
    b0 = (H[:, 1].max() - H[:, 1].min()) / 2 + 0.012 * k
    zt = h.top + 0.022 * k
    pe = 2.3

    def rad(ang, z, zb, scale=1.0):
        """Superellipse radius at angle (0 = front) with a front ridge and a slight taper to the top."""
        t = np.clip((z - zb) / (zt - zb), 0, 1)
        s = scale * (1 - 0.07 * t ** 2)
        ca, sa = np.cos(ang), np.sin(ang)
        r = 1 / ((np.abs(sa) / a0) ** pe + (np.abs(ca) / b0) ** pe) ** (1 / pe)
        r *= 1 + 0.07 * np.clip(ca, 0, 1) ** 10
        return r * s

    def pos(ang, z, r):
        ang = np.asarray(ang, float); r = np.broadcast_to(r, ang.shape); z = np.broadcast_to(z, ang.shape)
        return np.stack([cx + np.sin(ang) * r, cy - np.cos(ang) * r, z], -1)

    # rest it just above the shoulders/traps
    body = b.co[~h.hm]
    zb = h.chin_z - 0.04 * k
    for _ in range(3):
        sel = body[(body[:, 2] > zb - 0.03 * k) & (body[:, 2] < zt)]
        an = np.arctan2(sel[:, 0] - cx, -(sel[:, 1] - cy))
        rr = np.hypot(sel[:, 0] - cx, sel[:, 1] - cy)
        inside = rr < rad(an, sel[:, 2], zb) + 0.012 * k
        if inside.any():
            zb = max(zb, sel[inside, 2].max() + 0.012 * k)
    # grow until every head point clears by 2 cm
    an = np.arctan2(H[:, 0] - cx, -(H[:, 1] - cy)); rr = np.hypot(H[:, 0] - cx, H[:, 1] - cy)
    scale = max(0.8, float(np.max((rr + 0.014 * k) / rad(an, H[:, 2], zb))))
    na, nz = 112, 44
    A = np.linspace(-np.pi, np.pi, na, endpoint=False) + np.pi / na
    Zs = np.linspace(zb, zt, nz)
    slit_lo, slit_hi = ez - 0.007 * k, ez + 0.009 * k
    Zs = np.unique(np.sort(np.r_[Zs, slit_lo, slit_hi]))
    nz = len(Zs)
    V = np.vstack([pos(A, z, rad(A, z, zb, scale)) for z in Zs])
    F = []
    for i in range(nz - 1):
        zm = (Zs[i] + Zs[i + 1]) / 2
        for j in range(na):
            am = A[j]
            xo = abs(np.sin(am)) * rad(am, zm, zb, scale)
            if slit_lo < zm < slit_hi and abs(am) < np.radians(72) and xo > 0.012 * k:
                continue  # eye slit (nose bar left in the middle)
            F.append([i * na + j, i * na + (j + 1) % na, (i + 1) * na + (j + 1) % na, (i + 1) * na + j])
    # flat, slightly domed top
    top_ring = np.arange((nz - 1) * na, nz * na)
    rings = []
    for t in (0.75, 0.45, 0.15):
        rings.append(pos(A, zt + 0.012 * k * (1 - t ** 2), rad(A, zt, zb, scale) * t))
    prev = top_ring; V = list(V)
    for pts in rings:
        cur = list(range(len(V), len(V) + na)); V.extend(pts)
        F += [[prev[j], prev[(j + 1) % na], cur[(j + 1) % na], cur[j]] for j in range(na)]
        prev = cur
    ci = len(V); V.append(np.array([cx, cy, zt + 0.012 * k]))
    F += [[prev[j], prev[(j + 1) % na], ci] for j in range(na)]
    V = np.array(V)
    centre = np.array([cx, cy, (zb + zt) / 2])
    F = _orient_out(V, F, centre)
    m_met = _mat(name + "_Steel", color, rough=0.38, metal=0.6)
    m_dark = _mat(name + "_Dark", (0.012, 0.012, 0.014), rough=0.7)
    m_band = _mat(name + "_Band", np.array(color[:3]) * 0.8, rough=0.42, metal=0.6)
    out = [make_object(b, f"{b.obj.name}_{name}", V, F, [m_met], None, None, thick=0.004 * k, subsurf=0)]
    parts = []
    # dark lining visible through the slits
    Vin = np.vstack([pos(A, z, rad(A, z, zb, scale) - 0.006 * k) for z in (slit_lo - 0.01 * k, slit_hi + 0.01 * k)])
    Fin = [[j, (j + 1) % na, na + (j + 1) % na, na + j] for j in range(na) if abs(A[j]) < np.radians(80)]
    parts.append((Vin, _orient_out(Vin, Fin, centre)[::1], 1))

    def band(a_lo, a_hi, z_lo, z_hi, lift, nA=40, nZ=3):
        aa = np.linspace(a_lo, a_hi, nA); zz = np.linspace(z_lo, z_hi, nZ)
        Vb = np.vstack([pos(aa, z, rad(aa, z, zb, scale) + lift) for z in zz])
        Fb = [[i * nA + j, i * nA + j + 1, (i + 1) * nA + j + 1, (i + 1) * nA + j] for i in range(nZ - 1) for j in range(nA - 1)]
        return Vb, _orient_out(Vb, Fb, centre)
    T0 = 0.004 * k  # the shell's solidify thickness grows outwards: every trim sits on top of it
    lift = T0 + 0.0035 * k
    w = 0.011 * k / (rad(0, ez, zb, scale))  # half-width of the vertical band in radians
    parts.append((*band(-np.radians(80), np.radians(80), slit_hi + 0.003 * k, slit_hi + 0.022 * k, lift), 0))   # brow band
    parts.append((*band(-w, w, zb + 0.01 * k, slit_lo, lift, nA=4, nZ=14), 0))                                  # lower nose bar band
    parts.append((*band(-w, w, slit_hi + 0.022 * k, zt - 0.004 * k, lift, nA=4, nZ=10), 0))                    # crown ridge band
    parts.append((*band(-np.pi, np.pi, zb, zb + 0.014 * k, T0 + 0.0025 * k, nA=na + 1, nZ=3), 0))                    # bottom band
    # rivets
    for aa in np.radians(np.arange(-75, 76, 15)):
        p = pos(np.array([aa]), np.array([slit_hi + 0.0125 * k]), rad(np.array([aa]), slit_hi + 0.0125 * k, zb, scale) + lift + 0.001 * k)[0]
        Vr, Fr = _blob(p, np.array([0.0035, 0.0035, 0.0035]) * k, n=5, m=8)
        parts.append((Vr, Fr, 2))
    for aa in np.radians(np.arange(-180, 180, 20)):
        p = pos(np.array([aa]), np.array([zb + 0.007 * k]), rad(np.array([aa]), zb + 0.007 * k, zb, scale) + T0 + 0.0035 * k)[0]
        Vr, Fr = _blob(p, np.array([0.003, 0.003, 0.003]) * k, n=5, m=8)
        parts.append((Vr, Fr, 2))
    # breathing holes: crosses of small dark holes on both lower cheeks
    for side in (1, -1):
        for da, dz in [(0, 0), (1, 0), (-1, 0), (0, 1), (0, -1), (2, 0), (-2, 0), (0, 2), (0, -2)]:
            aa = side * np.radians(38 + 5.5 * da)
            zz = (ez + zb) / 2 - 0.01 * k + 0.011 * k * dz
            r0 = rad(np.array([aa]), zz, zb, scale)[0] + T0 + 0.0006 * k
            p0 = pos(np.array([aa]), np.array([zz]), r0)[0]
            nrm = p0 - np.array([cx, cy, zz]); nrm /= np.linalg.norm(nrm)
            u = np.cross([0, 0, 1.0], nrm); u /= np.linalg.norm(u); v = np.cross(nrm, u)
            ring = [p0 + 0.0028 * k * (np.cos(t) * u + np.sin(t) * v) for t in np.linspace(0, 2 * np.pi, 10, endpoint=False)]
            Vh = np.vstack([ring, [p0]])
            parts.append((Vh, [[(i + 1) % 10, i, 10] for i in range(10)], 1))
    Vd, Fd, md = merge_parts(parts)
    out.append(make_object(b, f"{b.obj.name}_{name}_Trim", Vd, Fd, [m_band, m_dark, m_met], md, None, thick=0, subsurf=0))
    o.objs.extend(out)
    Vc = V[:nz * na]
    o.col.add(Vc, vnormals(V, F)[:nz * na])
    return out[0]


# ----------------------------------------------------------------------------------------------------- goggles
def build_goggles(o, name, frame=(0.01, 0.01, 0.01), lens=(0.8, 0.37, 0.05), up=False):
    """Ski goggles: one wide toric lens with a nose notch, a foam frame that seals against the face, and the
    elastic strap round the head. up=True wears them pushed up on the forehead."""
    b = o.b; k = b.k; h = Head(b)
    ez, c = h.eye_z, h.c
    zc = ez + (0.075 if up else 0.009) * k
    hz = 0.027 * k
    amax = np.radians(74)
    clr = (0.008 if up else 0.022) * k
    nu, nv = 41, 9
    U = np.linspace(-1, 1, nu)

    def v_rng(u):
        e = (1 - np.abs(u) ** 4).clip(0) ** 0.25
        notch = 0 if up else 0.5 * np.exp(-(u / 0.17) ** 2)
        return -e + notch * e, e
    # lens radius per angle: clear of the face (incl. nose / brow) across the lens height, smoothed into a torus
    phis = U * amax
    zz = np.linspace(zc - hz, zc + hz, 7)
    Rc = np.zeros(nu)
    for z in zz:
        r = h.radius_at(phis, z)
        lo, hi = v_rng(U)
        ok = ((z - zc) / hz >= lo - 0.15) & ((z - zc) / hz <= hi + 0.15)
        Rc = np.maximum(Rc, np.where(ok, r, 0))
    for _ in range(30):
        Rc[1:-1] = np.maximum(Rc[1:-1], 0.5 * Rc[1:-1] + 0.25 * (Rc[:-2] + Rc[2:]))
    for _ in range(20):
        Rc[1:-1] = 0.5 * Rc[1:-1] + 0.25 * (Rc[:-2] + Rc[2:])
    tilt = 0.25 if up else 0.08  # lens leans back at the top

    def lens_pt(u, v, extra=0.0):
        phi = u * amax
        r = np.interp(u, U, Rc) + clr + 0.006 * k * (1 - v ** 2) + extra
        z = zc + v * hz
        r = r - tilt * (z - zc)
        return h.at(phi, z, r)
    # lens grid
    G = []
    for u in U:
        lo, hi = v_rng(u)
        G.append([lens_pt(u, lo + (hi - lo) * t) for t in np.linspace(0, 1, nv)])
    G = np.array(G)
    Vl = G.reshape(-1, 3)
    Fl = [[i * nv + j, (i + 1) * nv + j, (i + 1) * nv + j + 1, i * nv + j + 1] for i in range(nu - 1) for j in range(nv - 1)]
    centre = np.array([c[0], c[1], zc])
    Fl = _orient_out(Vl, Fl, centre)
    # outline around the lens (closed): bottom edge left->right, top edge right->left
    outline = np.vstack([G[:, 0], G[::-1, -1]])
    ouv = np.array([[u, v_rng(u)[0]] for u in U] + [[u, v_rng(u)[1]] for u in U[::-1]])
    # front rim: slightly bigger outline, a touch proud of the lens
    cen_uv = np.array([0.0, 0.0])
    rim_out = np.array([lens_pt(np.clip(u * 1.04, -1.04, 1.04), v * 1.0 + np.sign(v) * 0.18, 0.003 * k) for u, v in ouv])
    rim_in = np.array([lens_pt(u, v, 0.0025 * k) for u, v in ouv])
    # foam/side wall back to the face
    face = []
    for p in rim_out:
        phi = h.ang(p[None])[0]
        r_face = h.radius_at(np.array([phi]), p[2])[0] + 0.004 * k
        q = h.at(np.array([phi]), np.array([p[2]]), np.array([r_face]))[0]
        face.append(q)
    face = np.array(face)
    face = o.col.push(face, 0.0035 * k)
    n = len(ouv)
    Vf = np.vstack([rim_in, rim_out, face])
    Ff = [[i, (i + 1) % n, n + (i + 1) % n, n + i] for i in range(n)] + [[n + i, n + (i + 1) % n, 2 * n + (i + 1) % n, 2 * n + i] for i in range(n)]
    Ff = _orient_out(Vf, Ff, centre - np.array([0, 0.05 * k, 0]))
    # strap round the back of the head
    side_pts = [rim_out[np.argmin(ouv[:, 0])], rim_out[np.argmax(ouv[:, 0])]]
    zs = zc + (0.004 if not up else 0.0) * k
    ph = np.linspace(amax * 0.97, 2 * np.pi - amax * 0.97, 60)
    rr = h.radius_at(ph, zs, dz=0.02) + 0.007 * k
    Q = h.at(ph, np.full(len(ph), zs), rr)
    Q = o.col.push(Q, 0.006 * k)
    for _ in range(10):
        Q[1:-1] = 0.5 * Q[1:-1] + 0.25 * (Q[:-2] + Q[2:]); Q = o.col.push(Q, 0.006 * k)
    Q = np.vstack([side_pts[1], Q, side_pts[0]])
    Nq = np.zeros_like(Q); Nq[:, :2] = Q[:, :2] - c; Nq /= np.linalg.norm(Nq, axis=1, keepdims=True)
    Vs, Fs = _ribbon(Q, Nq, 0.034 * k)
    Fs = _orient_out(Vs, Fs, centre)
    m_frame = _mat(name + "_Frame", frame, rough=0.55)
    m_lens = _mat(name + "_Lens", lens, rough=0.06, metal=0.55)
    m_strap = _mat(name + "_Strap", np.array(frame[:3]) * 0.8 + 0.02, rough=0.9)
    out = [make_object(b, f"{b.obj.name}_{name}_Lens", Vl, Fl, [m_lens], None, None, thick=0.0015 * k, subsurf=1),
           make_object(b, f"{b.obj.name}_{name}", Vf, Ff, [m_frame], None, None, thick=0.002 * k, subsurf=1),
           make_object(b, f"{b.obj.name}_{name}_Strap", Vs, Fs, [m_strap], None, None, thick=0.002 * k, subsurf=1)]
    o.objs.extend(out)
    return out[1]


# --------------------------------------------------------------------------------------------- catalog mapping
def build_item(o, it, hexc):
    f, p, c1 = it["fam"], it["p"], it["c1"]
    c2 = it["c2"] or c1
    nm = it["id"]
    if f == "durag":
        build_durag(o, nm, color=c1, velvet=bool(p.get("velvet")))
    elif f == "balaclava":
        build_balaclava(o, nm, color=c1, accent=c2 if c2 != c1 else None, style="open" if p.get("open") else "classic", pom=bool(p.get("pom")))
    elif f == "helmet":
        build_helmet(o, nm, color=c1, nvg=bool(p.get("nvg")), strap=bool(p.get("strap", True)))
    elif f == "knighthelm":
        build_knight_helm(o, nm, color=c1)
    elif f == "goggles":
        build_goggles(o, nm, frame=c1, lens=c2, up=bool(p.get("up")))
    else:
        return False
    return True
