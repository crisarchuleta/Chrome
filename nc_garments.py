import collections
# Neon Coast garment maker for the MakeHuman (MPFB) bodies.
# Builds real 3D clothes that are sized to each body: the garment starts as the body's own (modesty-smoothed) surface,
# cut along clean hem lines, subdivided, then loosened with per-region "drape" envelopes (boxy tops hang straight from
# the chest, baggy pants hang from the hips and stack at the ankles), extended past the body where cloth hangs free
# (hoodie hems, pant legs over the shoes), smoothed, and pushed outside the body and every layer underneath.
# Everything stays on top of the permanent base layer (white tank + shorts + NC_Modesty key): NO NUDITY, EVER.
# Pure bpy + numpy + scipy. Original designs only: no brands, logos or real-world likenesses.
import bpy
import os
import numpy as np
from scipy.spatial import cKDTree
import nc_baselayer as BL

REF_H = 1.78
DEBUG = False  # tuned on a 1.78 m body; every size below scales with body height


# ----------------------------------------------------------------------------------------------- body analysis
class Body:
    def __init__(self, obj):
        self.obj = obj
        co = BL._eval_coords(obj)  # includes the NC_Modesty shape key (always 1)
        G = BL._groups(obj)
        body, lab, tpar, J = BL._labels(co, G)
        nv = len(co)
        inb = np.zeros(nv, bool); inb[body] = True
        reg = np.full(nv, "X", dtype=object); reg[body] = lab
        self.co, self.G, self.J, self.reg, self.inb = co, G, J, reg, inb
        self.faces = [list(p.vertices) for p in obj.data.polygons if all(inb[v] for v in p.vertices)]
        self.N = BL._normals(co, self.faces, nv)
        self.H = co[body, 2].max() - co[body, 2].min()
        self.k = self.H / REF_H
        self.floor = co[body, 2].min()
        self.cx = (J["l-shoulder"][0] + J["r-shoulder"][0]) / 2
        tor = body[(lab == "Torso")]
        self.yc = co[tor, 1].mean()
        self.female = obj.name.startswith("Female")
        self.tree = cKDTree(co[body])
        self.body_idx = body
        # crotch height: lowest torso point near the centre line
        mid = tor[np.abs(co[tor, 0] - self.cx) < 0.02 * self.k]
        self.crotch_z = co[mid, 2].min() if len(mid) else J["pelvis"][2] - 0.08 * self.k

    def side(self, p):
        return np.where(p[:, 0] > self.cx, "l", "r")


REGION_OF_BONE = {"LowerTorso": "Torso", "UpperTorso": "Torso", "NC_SpineMid": "Torso", "NC_ClavicleL": "Torso", "NC_ClavicleR": "Torso",
                  "Head": "Head", "NC_NeckMid": "Head", "LeftUpperArm": "UArm", "RightUpperArm": "UArm", "NC_TwistL": "LArm",
                  "NC_TwistR": "LArm", "LeftLowerArm": "LArm", "RightLowerArm": "LArm", "LeftHand": "Hand", "RightHand": "Hand",
                  "LeftUpperLeg": "ULeg", "RightUpperLeg": "ULeg", "LeftLowerLeg": "LLeg", "RightLowerLeg": "LLeg",
                  "LeftFoot": "Foot", "RightFoot": "Foot", "NC_ToesL": "Foot", "NC_ToesR": "Foot"}


ARM_OUT_DEG = 18.0


class RigBody(Body):
    """The rigged R15 body (<Body>_Whole, rest pose, studs). Its surface already includes the base layer, so clothes are
    built straight on top of it. The skin, tank and shorts are fused into one clean watertight shell with a voxel
    remesh (no seams where the base layer meets the skin). Regions come from the bone weights, joints from the bones."""
    def __init__(self, whole, arm, voxel=0.03, exclude_arms=False):
        self.obj = whole
        me = whole.data
        cw = np.array([v.co[:] for v in me.vertices])
        names = {g.index: g.name for g in whole.vertex_groups}
        regw = np.full(len(cw), "X", dtype=object)
        for v in me.vertices:
            best, bw = None, 0
            for g in v.groups:
                if g.weight > bw:
                    best, bw = names[g.group], g.weight
            if best is not None:
                nm = REGION_OF_BONE.get(best)
                if nm is None:
                    nm = "Hand" if any(t in best for t in ("Thumb", "Index", "Middle", "Ring", "Pinky")) else "Torso"
                regw[v.index] = nm
        bones = arm.data.bones
        h = lambda n: np.array(bones[n].head_local[:])
        J = {"neck": h("Head"), "pelvis": h("LowerTorso"), "head": h("Head")}
        for s_, S in (("l", "Left"), ("r", "Right")):
            J[s_ + "-shoulder"] = h(S + "UpperArm"); J[s_ + "-elbow"] = h(S + "LowerArm"); J[s_ + "-hand"] = h(S + "Hand")
            J[s_ + "-upper-leg"] = h(S + "UpperLeg"); J[s_ + "-knee"] = h(S + "LowerLeg"); J[s_ + "-ankle"] = h(S + "Foot")
        # fused shell
        tmp = bpy.data.objects.new("_nc_vox", me.copy())
        bpy.context.scene.collection.objects.link(tmp)
        tmp.matrix_world = whole.matrix_world.copy()
        for mod in list(tmp.modifiers):
            tmp.modifiers.remove(mod)
        disp = None
        if exclude_arms:  # lower-body shell: swing the arms far out so the hands can't fuse to the hips
            armv = np.isin(regw, ["LArm", "Hand"]) | ((regw == "UArm") & (cw[:, 2] < J["l-shoulder"][2] - 0.1 * (cw[:, 2].max() - cw[:, 2].min()) / REF_H * 0 - 0.4))
            moved = cw.copy()
            moved[armv, 0] += np.sign(moved[armv, 0]) * 3.0
            moved[armv, 2] += 1.5
            if LEG_OUT_DEG > 0:
                # spread the legs before fusing too: touching thighs fused into a web between the legs, and the
                # pants inherited it (a membrane that stretched 30x when the legs parted). Undone after the remesh.
                wl = {"l": np.zeros(len(cw)), "r": np.zeros(len(cw))}
                for v in me.vertices:
                    for g in v.groups:
                        gn = names[g.group]
                        if gn in ("LeftUpperLeg", "LeftLowerLeg", "LeftFoot", "NC_ToesL"): wl["l"][v.index] += g.weight
                        if gn in ("RightUpperLeg", "RightLowerLeg", "RightFoot", "NC_ToesR"): wl["r"][v.index] += g.weight
                ldisp = np.zeros_like(cw)
                for sd, sg in (("l", 1.0), ("r", -1.0)):
                    S_ = J[sd + "-upper-leg"]; th = np.radians(LEG_OUT_DEG) * sg
                    c_, s_ = np.cos(th), np.sin(th)
                    q = cw - S_
                    rot = np.c_[c_ * q[:, 0] - s_ * q[:, 2], q[:, 1], s_ * q[:, 0] + c_ * q[:, 2]] + S_
                    ldisp += (rot - cw) * np.clip(wl[sd], 0, 1)[:, None]
                ldisp[armv] = 0
                moved = moved + ldisp
                disp = ldisp
            tmp.data.vertices.foreach_set("co", moved.ravel())
            tmp.data.update()
        if not exclude_arms:
            disp = None
        if not exclude_arms:
            # lift the arms out sideways (like posing them) before fusing, so an arm resting on the side never fuses
            # to the body: sleeves stay their own tubes. The shell is put back to the rest pose afterwards.
            wsum = {"l": np.zeros(len(cw)), "r": np.zeros(len(cw))}
            for v in me.vertices:
                for g in v.groups:
                    gn = names[g.group]
                    sd = "l" if gn.startswith("Left") or gn.endswith("L") else "r" if gn.startswith("Right") or gn.endswith("R") else None
                    if sd and (REGION_OF_BONE.get(gn) in ("UArm", "LArm", "Hand") or any(t in gn for t in ("Thumb", "Index", "Middle", "Ring", "Pinky"))):
                        wsum[sd][v.index] += g.weight
            moved = cw.copy()
            for sd, sg in (("l", 1.0), ("r", -1.0)):
                S_ = J[sd + "-shoulder"]; th = np.radians(ARM_OUT_DEG) * sg
                c_, s_ = np.cos(th), np.sin(th)
                q = cw - S_
                rot = np.c_[c_ * q[:, 0] - s_ * q[:, 2], q[:, 1], s_ * q[:, 0] + c_ * q[:, 2]] + S_
                wv = np.clip(wsum[sd], 0, 1)[:, None]
                moved += (rot - cw) * wv
            disp = moved - cw
            tmp.data.vertices.foreach_set("co", moved.ravel())
            tmp.data.update()
        rm = tmp.modifiers.new("R", "REMESH"); rm.mode = "VOXEL"; rm.voxel_size = voxel; rm.adaptivity = 0.0
        dg = bpy.context.evaluated_depsgraph_get(); ev = tmp.evaluated_get(dg); mm = ev.to_mesh()
        co = np.array([v.co[:] for v in mm.vertices])
        faces = [list(p.vertices) for p in mm.polygons]
        ev.to_mesh_clear()
        bpy.data.meshes.remove(tmp.data)
        # keep the outer shell only (largest piece)
        lab = components(len(co), faces)
        main = np.bincount(lab).argmax()
        keep = lab == main
        idx = -np.ones(len(co), int); idx[keep] = np.arange(keep.sum())
        faces = [[int(idx[v]) for v in f] for f in faces if keep[f[0]]]
        co = co[keep]
        co_lift = co.copy()
        if disp is not None:  # back to the rest pose (inverse of the lift, from the nearest lifted body vertices)
            dd, jj = cKDTree(cw + disp).query(co, k=4)
            ww = 1 / np.maximum(dd, 1e-6); ww /= ww.sum(1, keepdims=True)
            co = co - np.einsum("nk,nkd->nd", ww, disp[jj])
        okw = regw != "X"
        if disp is not None:  # label in the lifted pose, where sleeve and side are apart
            _, j = cKDTree((cw + disp)[okw]).query(co_lift)
        else:
            _, j = cKDTree(cw[okw]).query(co)
        reg = regw[okw][j]
        if exclude_arms:
            okw = okw & ~np.isin(regw, ["Hand", "LArm", "UArm"])
            keep_ = np.abs(co[:, 0]) < np.abs(J["l-shoulder"][0]) + 0.6  # drop the swung-out arms
            fk = [f for f in faces if keep_[f].all()]
            used_ = np.zeros(len(co), bool)
            for f in fk:
                used_[f] = True
            idx2 = -np.ones(len(co), int); idx2[used_] = np.arange(used_.sum())
            faces = [[int(idx2[v]) for v in f] for f in fk]
            co = co[used_]
            _, j = cKDTree(cw[okw]).query(co)
            reg = regw[okw][j]
            self.reg = reg
        self.whole_co = cw
        self.whole_reg = regw
        # (lifted pose: where a resting hand and the hip are apart; skin weights for the shell are looked up there)
        self.co_lift = co_lift if disp is not None and not exclude_arms else None
        self.whole_lift = (cw + disp) if disp is not None else None
        self.whole_faces = [list(p.vertices) for p in me.polygons if p.material_index == 0]
        # base-layer tank: every garment that covers the chest must hide it completely (person's rule, 2026-11-23)
        tmi = [i for i, m_ in enumerate(me.materials) if m_ and "TankTop" in m_.name]
        tv = np.zeros(len(cw), bool)
        for p in me.polygons:
            if p.material_index in tmi:
                tv[list(p.vertices)] = True
        # dense samples on the tank faces, so distances to it are smooth (clean hem lines, no holes)
        smp = []
        for p in me.polygons:
            if p.material_index in tmi:
                vs = cw[list(p.vertices)]
                for i_ in range(1, len(vs) - 1):
                    tri = vs[[0, i_, i_ + 1]]
                    for (u_, v_) in ((1/3, 1/3), (0.1, 0.1), (0.8, 0.1), (0.1, 0.8), (0.45, 0.1), (0.1, 0.45), (0.45, 0.45)):
                        smp.append(tri[0] + u_ * (tri[1] - tri[0]) + v_ * (tri[2] - tri[0]))
        self.tank_co = np.vstack([cw[tv], np.array(smp)]) if smp else cw[tv]
        self.co, self.G, self.J, self.reg = co, {}, J, reg
        self.tank = (cKDTree(self.tank_co).query(co)[0] < 1.5 * voxel) if len(self.tank_co) else np.zeros(len(co), bool)
        self.inb = np.ones(len(co), bool)
        self.faces = faces
        self.N = vnormals(co, faces)
        body = np.arange(len(co))
        self.body_idx = body
        self.H = co[:, 2].max() - co[:, 2].min()
        self.k = self.H / REF_H
        self.floor = co[:, 2].min()
        self.cx = (J["l-shoulder"][0] + J["r-shoulder"][0]) / 2
        tor = body[reg == "Torso"]
        self.yc = co[tor, 1].mean()
        self.female = whole.name.startswith("Female")
        mid = tor[np.abs(co[tor, 0] - self.cx) < 0.02 * self.k]
        self.crotch_z = co[mid, 2].min() if len(mid) else J["pelvis"][2] - 0.08 * self.k
        self.arm = arm
        print("rigbody", whole.name, len(co), "verts")


def smoothstep(a, b, x):
    t = np.clip((x - a) / (b - a), 0, 1)
    return t * t * (3 - 2 * t)


# ----------------------------------------------------------------------------------------------- mesh helpers
def clip(P, faces, f, attrs):
    """Cut a polygon mesh along the zero line of a per-vertex field f (keeps f <= 0). New vertices are placed
    exactly on the iso-line, so hems come out as clean curves instead of stair steps. attrs: per-vertex arrays."""
    newp = [p for p in P]
    src = list(range(len(P)))
    cache, out = {}, []

    def cut(a, b):
        key = (min(a, b), max(a, b))
        if key not in cache:
            w = f[a] / (f[a] - f[b])
            cache[key] = len(newp)
            newp.append(P[a] + (P[b] - P[a]) * w)
            src.append(a if f[a] <= 0 else b)
        return cache[key]

    for poly in faces:
        fv = [f[v] for v in poly]
        if max(fv) <= 0:
            out.append(list(poly)); continue
        if min(fv) > 0:
            continue
        res = []
        n = len(poly)
        for i in range(n):
            a, b = poly[i], poly[(i + 1) % n]
            if f[a] <= 0:
                res.append(a)
            if (f[a] <= 0) != (f[b] <= 0):
                res.append(cut(a, b))
        if len(res) >= 3:
            out.append(res)
    newp = np.array(newp)
    src = np.array(src)
    used = sorted({v for p in out for v in p})
    remap = -np.ones(len(newp), int); remap[used] = np.arange(len(used))
    faces2 = [[int(remap[v]) for v in p] for p in out]
    return newp[used], faces2, {k: np.asarray(a)[src[used]] for k, a in attrs.items()}


def components(nv, faces):
    par = np.arange(nv)
    def root(x):
        while par[x] != x:
            par[x] = par[par[x]]; x = par[x]
        return x
    for f in faces:
        r0 = root(f[0])
        for v in f[1:]:
            r1 = root(v)
            if r1 != r0:
                par[r1] = r0
    return np.array([root(i) for i in range(nv)])


def keep_big(P, faces, attrs, frac=0.05):
    lab = components(len(P), faces)
    fl = np.array([lab[f[0]] for f in faces])
    ids, cnt = np.unique(fl, return_counts=True)
    keep = set(ids[cnt >= frac * cnt.max()])
    faces = [f for f, l in zip(faces, fl) if l in keep]
    used = sorted({v for f in faces for v in f})
    remap = -np.ones(len(P), int); remap[used] = np.arange(len(used))
    return P[used], [[int(remap[v]) for v in f] for f in faces], {k: a[used] for k, a in attrs.items()}


def subdivide(P, faces, attrs):
    """One linear Catmull-Clark-topology split: every n-gon becomes n quads (keeps positions on the surface)."""
    P = list(P)
    src = list(range(len(P)))
    emid = {}
    out = []
    def mid(a, b):
        key = (min(a, b), max(a, b))
        if key not in emid:
            emid[key] = len(P); P.append((P[a] + P[b]) / 2); src.append(a)
        return emid[key]
    for f in faces:
        n = len(f)
        c = len(P); P.append(np.mean([P[v] for v in f], axis=0)); src.append(f[0])
        ms = [mid(f[i], f[(i + 1) % n]) for i in range(n)]
        for i in range(n):
            out.append([f[i], ms[i], c, ms[i - 1]])
    src = np.array(src)
    return np.array(P), out, {k: a[src] for k, a in attrs.items()}


def edges_of(faces):
    e = set()
    for f in faces:
        for a, b in zip(f, f[1:] + f[:1]):
            e.add((min(a, b), max(a, b)))
    return np.array(sorted(e))


def boundary_loops(faces):
    cnt = {}
    for f in faces:
        for a, b in zip(f, f[1:] + f[:1]):
            k = (min(a, b), max(a, b))
            cnt[k] = cnt.get(k, 0) + 1
    # directed boundary edges keep the face winding so loops come out consistently oriented
    nxt = {}
    for f in faces:
        for a, b in zip(f, f[1:] + f[:1]):
            if cnt[(min(a, b), max(a, b))] == 1:
                nxt[a] = b
    loops, seen = [], set()
    for s in list(nxt):
        if s in seen:
            continue
        loop, v = [], s
        while v not in seen and v in nxt:
            seen.add(v); loop.append(v); v = nxt[v]
        if len(loop) > 2:
            loops.append(loop)
    return loops


def zipper(co, A, B):
    """Bridge two nearby boundary loops with a strip of triangles (walks both, always taking the shorter step)."""
    A = list(A); B = list(B)
    tB = cKDTree(co[B])
    _, jj = tB.query(co[A])
    steps = np.diff(jj)
    steps = (steps + len(B) // 2) % len(B) - len(B) // 2
    if np.sum(steps) < 0:
        B = B[::-1]
        _, jj = cKDTree(co[B]).query(co[A])
    j0 = int(jj[0])
    B = B[j0:] + B[:j0]
    n, m = len(A), len(B)
    i = j = 0
    tris = []
    while i < n or j < m:
        a, a2 = A[i % n], A[(i + 1) % n]
        b, b2 = B[j % m], B[(j + 1) % m]
        if j >= m or (i < n and np.linalg.norm(co[a2] - co[b]) <= np.linalg.norm(co[a] - co[b2])):
            tris.append([a, a2, b]); i += 1
        else:
            tris.append([a, b2, b]); j += 1
    return tris


def vnormals(P, faces):
    n = np.zeros_like(P)
    bylen = {}
    for f in faces:
        bylen.setdefault(len(f), []).append(f)
    for L, fs in bylen.items():
        Fa = np.array(fs)
        fnrm = np.zeros((len(Fa), 3))
        for i in range(1, L - 1):
            fnrm += np.cross(P[Fa[:, i]] - P[Fa[:, 0]], P[Fa[:, i + 1]] - P[Fa[:, 0]])
        for c in range(L):
            np.add.at(n, Fa[:, c], fnrm)
    return n / np.maximum(np.linalg.norm(n, axis=1), 1e-12)[:, None]


def laplace(X, E, iters, mask=None, lam=0.5, taubin=False):
    import scipy.sparse as sp
    nv = len(X)
    if len(E) == 0:
        return X.copy()
    A = sp.coo_matrix((np.ones(2 * len(E)), (np.r_[E[:, 0], E[:, 1]], np.r_[E[:, 1], E[:, 0]])), shape=(nv, nv)).tocsr()
    deg = np.asarray(A.sum(1)).ravel()
    X = X.copy()
    m = deg > 0 if mask is None else (deg > 0) & mask
    inv = 1 / np.maximum(deg, 1)
    for _ in range(iters):
        for l in ((lam, -lam - 0.03) if taubin else (lam,)):
            avg = (A @ X) * inv[:, None]
            X[m] += l * (avg[m] - X[m])
    return X


class Collider:
    """Keeps garments outside the body and the layers underneath (nearest-point + normal test)."""
    def __init__(self):
        self.P = np.zeros((0, 3)); self.N = np.zeros((0, 3)); self.tree = None

    def add(self, P, N):
        self.P = np.vstack([self.P, P]); self.N = np.vstack([self.N, N]); self.tree = cKDTree(self.P)

    dmax = 0.06

    def push(self, X, gap, k=6):
        if self.tree is None:
            return X
        d, j = self.tree.query(X, k=k)
        X = X.copy()
        for c in range(k):
            jj = j[:, c]
            depth = np.einsum("ij,ij->i", X - self.P[jj], self.N[jj])
            m = (depth < gap) & (d[:, c] < self.dmax)
            X[m] += (gap - depth[m])[:, None] * self.N[jj[m]]
        return X


# ----------------------------------------------------------------------------------------------- parametrisation
def arm_param(b, P):
    """s along shoulder->hand (0..1), radial vector, side for every point."""
    s = np.zeros(len(P)); rad = np.zeros_like(P); R = np.zeros(len(P))
    sd = b.side(P)
    for side in ("l", "r"):
        m = sd == side
        A, Bh = b.J[side + "-shoulder"], b.J[side + "-hand"]
        d = Bh - A; L = np.linalg.norm(d); d /= L
        q = P[m] - A
        t = q @ d
        s[m] = t / L
        rv = q - t[:, None] * d
        R[m] = np.linalg.norm(rv, axis=1)
        rad[m] = rv / np.maximum(R[m], 1e-9)[:, None]
    return s, rad, R


def leg_param(b, P):
    s = np.zeros(len(P)); rad = np.zeros_like(P); R = np.zeros(len(P))
    sd = b.side(P)
    for side in ("l", "r"):
        m = sd == side
        A, Bk = b.J[side + "-upper-leg"], b.J[side + "-ankle"]
        d = Bk - A; L = np.linalg.norm(d); d /= L
        q = P[m] - A
        t = q @ d
        s[m] = t / L
        rv = q - t[:, None] * d
        R[m] = np.linalg.norm(rv, axis=1)
        rad[m] = rv / np.maximum(R[m], 1e-9)[:, None]
    return s, rad, R


def torso_cyl(b, P):
    dx, dy = P[:, 0] - b.cx, P[:, 1] - b.yc
    return np.arctan2(dy, dx), np.hypot(dx, dy)


def drape_envelope(b, P, sel, z_top, ease, add, hang_from, nb=72, flare=0.0):
    """Cylindrical envelope around the torso axis. Above hang_from it follows the body (bin max x ease), below it the
    cloth hangs: the radius never shrinks going down (boxy fit). Returns new radius per point (only lifts)."""
    th, r = torso_cyl(b, P)
    at_ = getattr(b, "armish_tree", None)
    if at_ is not None:  # posed build: the side stretched out under a raised arm must not set the hang radius
        d_, _ = at_.query(P)
        sel = sel & (d_ > 0.03 * b.k)
    dz = 0.012 * b.k
    z0 = P[sel, 2].min() - dz
    nz = int((z_top - z0) / dz) + 2
    zi = np.clip(((P[:, 2] - z0) / dz).astype(int), 0, nz - 1)
    ti = ((th + np.pi) / (2 * np.pi) * nb).astype(int) % nb
    E = np.full(nz * nb, -np.inf)
    ii = np.where(sel)[0]
    np.maximum.at(E, zi[ii] * nb + ti[ii], r[ii])
    E = E.reshape(nz, nb)
    E[np.isinf(E)] = np.nan
    # fill gaps (along theta first, then z)
    for z in range(nz):
        row = E[z]
        ok = ~np.isnan(row)
        if ok.sum() >= 3:
            xs = np.arange(nb)
            E[z] = np.interp(xs, xs[ok], row[ok], period=nb)
    for t in range(nb):
        col = E[:, t]
        ok = ~np.isnan(col)
        if ok.any():
            E[:, t] = np.interp(np.arange(nz), np.where(ok)[0], col[ok])
    # smooth around and along
    ker = np.array([1, 2, 3, 2, 1.0]); ker /= ker.sum()
    for _ in range(2):
        E = sum(np.roll(E, s - 2, axis=1) * ker[s] for s in range(5))
        Ep = np.pad(E, ((1, 1), (0, 0)), mode="edge")
        E = 0.25 * Ep[:-2] + 0.5 * Ep[1:-1] + 0.25 * Ep[2:]
    E = E * (1 + ease) + add
    hz = int((hang_from - z0) / dz)
    for z in range(min(hz, nz - 1) - 1, -1, -1):
        E[z] = np.maximum(E[z], E[z + 1] * (1 + flare))
    # bilinear lookup (nearest-bin lookups leave a faint grid on the cloth)
    zf = np.clip((P[:, 2] - z0) / dz - 0.5, 0, nz - 1.001)
    tf = ((th + np.pi) / (2 * np.pi) * nb - 0.5) % nb
    z_i = np.floor(zf).astype(int); t_i = np.floor(tf).astype(int)
    fz = zf - z_i; ft = tf - t_i
    t2 = (t_i + 1) % nb; z2 = np.minimum(z_i + 1, nz - 1)
    val = (E[z_i, t_i] * (1 - fz) * (1 - ft) + E[z2, t_i] * fz * (1 - ft) + E[z_i, t2] * (1 - fz) * ft + E[z2, t2] * fz * ft)
    return np.maximum(r, val), th


# ----------------------------------------------------------------------------------------------- materials
def material(name, rgba, vcol=False, rough=0.9):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.diffuse_color = rgba
    m.use_nodes = True
    nt = m.node_tree
    bsdf = nt.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = rgba
    bsdf.inputs["Roughness"].default_value = rough
    if vcol:
        ca = nt.nodes.get("NC_Col") or nt.nodes.new("ShaderNodeVertexColor")
        ca.name = "NC_Col"; ca.layer_name = "Col"
        nt.links.new(ca.outputs["Color"], bsdf.inputs["Base Color"])
    return m


def make_object(b, name, P, faces, mats, mat_idx=None, vcol=None, thick=0.003, smooth=True, subsurf=1, arm_flag=None):
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(x) for x in P], [], faces)
    me.update()
    if arm_flag is not None:  # which vertices belong to sleeves (they may take arm/hand bone weights)
        at = me.attributes.new("nc_arm", "INT", "POINT")
        at.data.foreach_set("value", np.asarray(arm_flag, dtype=np.int32))
    for p in me.polygons:
        p.use_smooth = smooth
    if mat_idx is not None:
        me.polygons.foreach_set("material_index", np.asarray(mat_idx, dtype=np.int32))
    if vcol is not None:
        attr = me.color_attributes.new("Col", "BYTE_COLOR", "POINT")
        c = np.ones((len(P), 4)); c[:, :3] = vcol
        attr.data.foreach_set("color", c.ravel())
    ob = bpy.data.objects.new(name, me)
    for m in mats:
        ob.data.materials.append(m)
    if subsurf:
        ss = ob.modifiers.new("Smooth", "SUBSURF"); ss.levels = subsurf; ss.render_levels = subsurf
    if thick:
        so = ob.modifiers.new("Thickness", "SOLIDIFY"); so.thickness = thick; so.offset = 1.0
    for c in b.obj.users_collection:
        c.objects.link(ob)
    ob.parent = b.obj
    ob.matrix_parent_inverse = b.obj.matrix_world.inverted()
    ob.matrix_world = b.obj.matrix_world.copy()
    ob["nc_garment"] = True
    return ob


# ----------------------------------------------------------------------------------------------- noise / prints
def _hash(ix, iy, iz, seed):
    h = (ix * 73856093) ^ (iy * 19349663) ^ (iz * 83492791) ^ (seed * 2654435761)
    h = (h ^ (h >> 13)) * 1274126177
    return ((h ^ (h >> 16)) & 0xFFFF) / 65535.0


def value_noise(P, scale, seed=0):
    X = P / scale
    i = np.floor(X).astype(np.int64); f = X - i
    f = f * f * (3 - 2 * f)
    out = 0
    for dx in (0, 1):
        for dy in (0, 1):
            for dz in (0, 1):
                w = (f[:, 0] if dx else 1 - f[:, 0]) * (f[:, 1] if dy else 1 - f[:, 1]) * (f[:, 2] if dz else 1 - f[:, 2])
                out = out + w * _hash(i[:, 0] + dx, i[:, 1] + dy, i[:, 2] + dz, seed)
    return out


def camo(P, palette, scale, seed=1):
    n = value_noise(P, scale, seed) * 0.65 + value_noise(P, scale * 0.45, seed + 7) * 0.35
    n2 = value_noise(P, scale * 0.8, seed + 3)
    col = np.tile(np.array(palette[0], float), (len(P), 1))
    col[n > 0.5] = palette[1]
    col[(n2 > 0.62)] = palette[2]
    if len(palette) > 3:
        col[(n < 0.33)] = palette[3]
    return col


# ----------------------------------------------------------------------------------------------- builders
TORSOISH = ("Torso", "ULeg", "LLeg", "Foot")
ARMS = ("UArm", "LArm")


def _isin(reg, names):
    return np.isin(reg, list(names))


def under_jacket_points(b, X):
    """True where a top is hidden by any jacket worn over it: everything but the centre-front strip an open jacket
    shows and the neckline. Those parts ("-under") are left off in game under a jacket, together with the sleeves,
    so a top can never poke through a jacket however the two bend."""
    X = np.asarray(X)
    front = (X[:, 1] < b.yc) & (np.abs(X[:, 0] - b.cx) < 0.075 * b.k)
    neck = X[:, 2] > b.J["neck"][2] - 0.07 * b.k
    return ~(front | neck)


def arm_points(b, X):
    """True where a garment point lies over the arm (nearest body vertex is upper arm, forearm or hand). A top's
    sleeve faces (all corners over the arm) are its "-arm" parts, hidden in game under a jacket; jackets are built
    over the under-layer with exactly those points left out, so the two agree."""
    if getattr(b, "_armtree", None) is None:
        bi = b.body_idx
        b._armtree = (cKDTree(b.co[bi]), _isin(b.reg[bi], ARMS + ("Hand",)))
    t, m = b._armtree
    _, j = t.query(np.asarray(X))
    return m[j]


def _start(b, f, sub=0, smooth=2):
    P, F, A = clip(b.co, b.faces, f, {"reg": b.reg})
    P, F, A = keep_big(P, F, A)
    # pinholes (a few cells where the cut field flickers, e.g. arm resting on the side): close them
    loops = boundary_loops(F)
    # larger holes high on the chest/shoulder (heavy builds: armpit fold) are holes too, never real openings
    zsh = min(b.J["l-shoulder"][2], b.J["r-shoulder"][2])
    def _hole(l):
        if len(l) <= 24:
            return True
        c_ = P[l].mean(0); per_ = sum(np.linalg.norm(P[l[i]] - P[l[i - 1]]) for i in range(len(l))) / b.k
        nk_ = np.linalg.norm(c_ - b.J["neck"]) / b.k
        return len(l) <= 60 and per_ < 0.25 and zsh - 0.2 * b.k < c_[2] < zsh + 0.1 * b.k and nk_ > 0.08
    small = [l for l in loops if _hole(l)]
    if small:
        P = list(P); F = list(F); A = {kk: list(vv) for kk, vv in A.items()}
        bt_ = cKDTree(b.co)
        for l in small:
            c = len(P); m_ = np.mean([P[i] for i in l], axis=0)
            m_ = b.co[bt_.query(m_)[1]]  # the cap sits on the body surface, not sunk inside it
            P.append(m_)
            for kk in A:
                A[kk].append(A[kk][l[0]])
            a0, a1 = l[0], l[1]  # orient the fan opposite to the face that already uses edge a0-a1
            fwd = any(f_[(t + 1) % len(f_)] == a1 and f_[t] == a0 for f_ in F if a0 in f_ and a1 in f_ for t in range(len(f_)))
            for i in range(len(l)):
                F.append([l[(i + 1) % len(l)], l[i], c] if fwd else [l[i], l[(i + 1) % len(l)], c])
        P = np.array(P); A = {kk: np.array(vv, dtype=object) for kk, vv in A.items()}
    if smooth:  # iron out the steps where the base layer meets the skin
        P = laplace(P, edges_of(F), smooth, taubin=True)
    if DEBUG:
        for l in boundary_loops(F):
            print("  garment loop", len(l), np.round(P[l].mean(0), 2))
    for _ in range(sub):
        P, F, A = subdivide(P, F, A)
    return P, F, A["reg"]



def _extend_loop(X, F, loop, axis_c, rings, reg, regname):
    """Extrude an open hem loop as extra rings. rings: list of functions(i_ring) -> (n,3) positions."""
    X = list(X); F = list(F); reg = list(reg)
    prev = list(loop)
    n = len(loop)
    for pts in rings:
        cur = list(range(len(X), len(X) + n))
        X.extend(pts); reg.extend([regname] * n)
        for i in range(n):
            a, nx = prev[i], prev[(i + 1) % n]
            F.append([nx, a, cur[i], cur[(i + 1) % n]])
        prev = cur
    return np.array(X), F, np.array(reg, dtype=object), prev


class Outfit:
    def __init__(self, b):
        self.b = b
        self.col = Collider()
        self.col.dmax = 0.09 * b.k
        bi = b.body_idx
        self.col.add(b.co[bi], b.N[bi])
        self.col_noarm = Collider(); self.col_noarm.dmax = self.col.dmax
        na = bi[~np.isin(b.reg[bi], ["Hand", "LArm", "UArm"])]
        self.col_noarm.add(b.co[na], b.N[na])
        self.objs = []
        self.top = None  # (X, N) of the outer top, for chains / strings
        self._low = None

    @property
    def low(self):
        """Same body without arms (for pants, skirts and shoes: hands resting on the hips can't fuse into them)."""
        if self._low is None and getattr(self.b, "low_body", None) is not None:
            self._low = self.b.low_body
        if self._low is None:
            if isinstance(self.b, RigBody):
                self._low = RigBody(self.b.obj, self.b.arm, exclude_arms=True)
            else:
                self._low = self.b
        return self._low

    def layer(self, X, F, thick):
        N = vnormals(X, F)
        self.col.add(X + N * thick, N)
        self.col_noarm.add(X + N * thick, N)
        return N


def _tank_field(b, front_open=False, margin=0.014):
    tc = getattr(b, "tank_co", None)
    if tc is None or not len(tc):
        return None
    d, _ = cKDTree(tc).query(b.co)
    g = d - margin * b.k
    if front_open:
        g = np.where(b.co[:, 1] > b.J["neck"][1] - 0.02 * b.k, g, 1.0)
    return np.where(_isin(b.reg, ("Head",)) & (b.co[:, 2] > b.J["neck"][2]), 1.0, g)


def _cover_tank(b, f, front_open=False, margin=0.014, armzone=None):
    """Never cut the garment where it would leave the base-layer tank showing: keep everything on or within
    `margin` of the tank (necklines and armholes end up at least as high and as narrow as the tank's).
    armzone (sleeveless tops): there the armhole simply follows the tank's own armhole, offset by the margin."""
    tc = getattr(b, "tank_co", None)
    if tc is None or not len(tc):
        return f
    if armzone is not None:
        g = _tank_field(b, front_open, margin)
        f = f.copy()
        f[armzone] = g[armzone]
        return f
    d, _ = cKDTree(tc).query(b.co)
    g = d - margin * b.k                     # smooth: negative on the tank and within the margin around it
    if front_open:  # open jackets: only the back and shoulders (the front is meant to show what is under)
        g = np.where(b.co[:, 1] > b.J["neck"][1] - 0.02 * b.k, g, 1.0)
    g = np.where(_isin(b.reg, ("Head",)) & (b.co[:, 2] > b.J["neck"][2]), 1.0, g)
    return np.minimum(f, g)




def _dbg(tag, X, F):
    import os
    d = os.environ.get("NC_DBG")
    if d:
        np.savez(os.path.join(d, tag + ".npz"), X=np.asarray(X), F=np.asarray([list(f)[:3] for f in F] + [[f[0], f[2], f[3]] for f in F if len(f) == 4]))


def _chk(tag, b, X, R):
    if not os.environ.get("NC_DBG2"):
        return
    am = _isin(R, ARMS); sa, rd, Ra = arm_param(b, X)
    m = am & (sa > 0.45) & (sa < 0.9)
    print("CHK", tag, "arm verts", am.sum(), "fore", m.sum(), "R>0.3", (m & (Ra > 0.3)).sum(), "Rmax %.2f" % (Ra[m].max() if m.any() else 0), flush=True)


def hip_cut_z(b, P, hip_cut):
    """Height above which a bottom's cloth is its "-hip" part (hidden under a long 3D top). It rises over the centre
    front and back (the fly / seat): there the top's hem lifts with the thighs and the base shorts showed between."""
    c = np.clip(1 - np.abs(P[:, 0] - b.cx) / (HIP_CUT_CW * b.k), 0, 1)
    c = c * c * (3 - 2 * c)
    return b.J["l-upper-leg"][2] + (hip_cut + HIP_CUT_CENTRE * c) * b.k


def _sleeve_flag(b, X, R):
    """Sleeve vertices (they skin to their arm only): arm-region cloth, plus any cloth past the shoulder whose nearest
    body point is on the arm (a few vertices labelled torso on the female forearm turned into flaps)."""
    s_, _, _ = arm_param(b, X)
    bi = b.body_idx; am = _isin(b.reg[bi], ARMS + ("Hand",))
    d_, _ = cKDTree(b.co[bi][am]).query(X)
    extra = arm_points(b, X) & (s_ > 0.2) & (d_ < 0.035 * b.k) & ~_isin(R, ("Hem", "Collar"))  # (not the hem by the hand)
    fl = _isin(R, ARMS) | extra  # (not R == "Hand": hip cloth beside a resting hand is labelled Hand)
    if SLEEVE_OFF_TANK and len(getattr(b, "tank_co", [])):
        # cloth at the sleeve root lying over the tank (the side of the chest under the armpit) is body panel: as
        # sleeve it left with the arm and the tank showed through the armpit when the arm went up
        dt_, _ = cKDTree(b.tank_co).query(X)
        fl &= ~((s_ < 0.25) & (dt_ < d_) & (dt_ < 0.04 * b.k))
    return fl


def build_top(o, name, kind="hoodie", sleeve="long", length=0.0, ease=0.08, sleeve_ease=0.13, color=(0.05, 0.05, 0.055),
              accent=None, camo_pal=None, print_fn=None, hood=True, pocket=True, zip_front=False, puffer=False,
              rib=True, thick=0.004, collar=None, neck_drop=0.0, front_open=False, flare=0.012, band=None):
    b = o.b; k = b.k; J = b.J; P0 = b.co; reg = b.reg
    if collar is None:
        collar = "stand" if puffer else "rib"
    neck_z = J["neck"][2]
    s_end = {"long": 0.96, "short": 0.40, "elbow": 0.55, "none": 0.03}[sleeve]
    # 1. cut the body surface
    z_clip = max(b.crotch_z + 0.045 * k, J["pelvis"][2] - 0.03 * k)
    f = np.ones(len(P0))
    s, _, _ = arm_param(b, P0)
    tor = _isin(reg, TORSOISH)
    f[tor] = z_clip - P0[tor, 2]
    front = np.clip((J["neck"][1] - P0[:, 1]) / (0.07 * k), 0, 1)
    zc = neck_z - ((0.02 + 0.05 * front) if kind == "tee" else (0.012 + 0.035 * front)) * k
    if collar in ("stand", "turtle", "shirt"):
        zc = neck_z - (0.004 + 0.02 * front) * k
    if neck_drop:
        zc = zc - neck_drop * k * np.clip(1 - np.abs(P0[:, 0] - b.cx) / (0.08 * k), 0, 1) * front
    # neck hole: a ring around the neck (works for sloped female shoulders too) plus the front scoop
    hm_ = (reg == "Head") & (P0[:, 2] > neck_z) & (P0[:, 2] < neck_z + 0.03 * k)
    yn = P0[hm_, 1].mean() if hm_.any() else J["neck"][1]
    dn = np.hypot(P0[:, 0] - b.cx, (P0[:, 1] - yn) * 1.08)
    Rn = np.median(np.hypot(P0[hm_, 0] - b.cx, (P0[hm_, 1] - yn) * 1.08)) if hm_.any() else 0.06 * k
    margin = {"rib": 0.016 + (0.008 if kind == "tee" else 0.0), "stand": 0.008, "turtle": 0.004, "shirt": 0.008, "lapel": 0.012, "none": 0.022}.get(collar, 0.016) * k
    margin = margin + (0.014 if kind == "tee" else 0.008) * k * front ** 1.5
    if neck_drop:
        margin = margin + neck_drop * k * 0.5 * front
    # the ring may reach down to the shoulders at the sides and back, but at the front it stops at the scoop depth
    # (otherwise the cylinder eats into the upper chest when the neck joint sits behind the chest)
    floor_z = (neck_z - 0.16 * k) * (1 - front) + (zc - 0.012 * k) * front
    # the ring narrows below the base of the neck (a cone), so on high sloped trapezius muscles the neckline stays
    # snug at the neck instead of opening wide across the tops of the shoulders
    cone = 1.2 * np.maximum(0.0, (neck_z - 0.035 * k) - P0[:, 2]) * (1 - front)
    ring = np.where(P0[:, 2] > floor_z, Rn + margin - dn - cone, -1.0)
    zc2 = zc - 0.05 * k  # only very deep cuts come from the plane now
    plane = P0[:, 2] - np.maximum(zc2, zc + 0.012 * k)
    # the plane only shapes the neckline near the neck: high trapezius muscles out at the shoulders stay covered
    plane = np.where(dn < Rn + margin + 0.035 * k, plane, np.minimum(plane, -0.001))
    f[tor] = np.maximum(f[tor], np.maximum(ring[tor], plane[tor]))
    arm = _isin(reg, ARMS)
    f[arm] = s[arm] - s_end if s_end > 0 else 1.0
    near_all = np.zeros(len(P0), bool)
    if sleeve == "none":
        # armholes follow the base-layer tank's own armhole, offset outward by a margin, so the garment always
        # sits over the tank's edge (clean curve, and the tank can't show)
        zone = arm.copy()
        for side in ("l", "r"):
            zone |= (b.side(P0) == side) & (s > -0.12) & ~(reg == "Head") & (P0[:, 2] > J[side + "-shoulder"][2] - 0.16 * k)
        near_all = zone
    f2 = _cover_tank(b, f, front_open)
    if sleeve == "none":
        g_ = _tank_field(b, front_open, 0.03)
        f = np.where(near_all, g_ if g_ is not None else f, f2)
    else:
        f = f2
    P, F, R = _start(b, f)
    _chk('start', b, P, R)
    if sleeve == "none":  # no sleeves: any arm-labelled cloth left is the armhole edge of the body panel
        R = np.where(_isin(R, ARMS), "Torso", R).astype(object)
    E = edges_of(F)
    Nb = vnormals(P, F)
    off = 0.010 * k + (0.012 * k if puffer else 0)
    X0 = P + Nb * off
    X = X0.copy()
    isarm = _isin(R, ARMS)
    # 2. torso: boxy drape from the chest down, follows the shoulders above
    chest_z = J["l-shoulder"][2] - 0.10 * k
    rnew, th = drape_envelope(b, X0, ~isarm, neck_z, ease, 0.004 * k, chest_z, flare=0.0015)
    _, r = torso_cyl(b, X0)
    wt = (1 - smoothstep(chest_z + 0.03 * k, chest_z + 0.11 * k, X0[:, 2])) * (~isarm)
    if sleeve == "none":  # armholes hug the body (a lifted edge would let you see under it)
        lp_ = [l for l in boundary_loops(F) if np.abs(P[l, 0] - b.cx).mean() > 0.06 * k and P[l, 2].mean() > chest_z - 0.1 * k]
        if lp_:
            dA, _ = cKDTree(P[np.concatenate(lp_)]).query(P)
            wt = wt * smoothstep(0.0, 0.07 * k, dA)
    scale = np.where(r > 1e-6, (r + (rnew - r) * wt) / np.maximum(r, 1e-6), 1)
    X[:, 0] = b.cx + (X0[:, 0] - b.cx) * scale
    X[:, 1] = b.yc + (X0[:, 1] - b.yc) * scale
    # 3. sleeves: round, loose tubes that narrow gently to the cuff
    if s_end > 0:
        sa, rad, Ra = arm_param(b, X0)
        for side in ("l", "r"):
            m = isarm & (b.side(X0) == side)
            if not m.any():
                continue
            def p95(lo, hi):
                q = Ra[m & (sa > lo) & (sa < hi)]
                return np.percentile(q, 95) if len(q) else Ra[m].max()
            r_up, r_lo, r_wr = p95(0.12, 0.35), p95(0.55, 0.8), p95(0.85, 1.0)
            ss = sa[m]
            if sleeve == "long":
                Rt = np.interp(ss, [0, 0.3, 0.8, s_end], [r_up * (1 + sleeve_ease), r_up * (1 + sleeve_ease),
                                                          r_lo * (1 + sleeve_ease * 1.3), r_wr * (1 + sleeve_ease * 1.3)])
                if rib:  # gathered rib cuff
                    g = smoothstep(s_end - 0.07, s_end - 0.02, ss)
                    Rt = Rt * (1 - g) + (r_wr + 0.006 * k) * g
                # sleeves bunch above the cuff
                phi = np.arctan2(rad[m][:, 2], rad[m][:, 0] * (1 if side == "l" else -1))
                bunch = np.sin(2 * np.pi * ss / 0.055 + 1.3 * np.sin(2 * phi + ss * 9)) * smoothstep(0.62, 0.86, ss) * (1 - smoothstep(s_end - 0.08, s_end - 0.04, ss))
                Rt = Rt * (1 + 0.07 * bunch)
            else:
                Rt = r_up * (1 + sleeve_ease) * (1 + 0.12 * ss / max(s_end, 1e-3))
            if puffer:
                Rt = Rt * (1 + 0.06 * np.abs(np.sin(np.pi * ss / 0.11)) ** 0.6)
            if SLEEVE_ROOT_EASE > 0 and sleeve == "long":  # (a short sleeve ballooned into a ring)
                # room at the armpit (like a real armhole): with a skin-tight sleeve root the arm skin or the tank
                # showed through whenever the arm swung forward or across
                Rt = Rt * (1 + SLEEVE_ROOT_EASE * (1 - smoothstep(0.12, 0.42, ss)))
            Rn = np.maximum(Ra[m], Rt)
            w = smoothstep(0.02, 0.2, ss)
            A_ = J[side + "-shoulder"]; d = J[side + "-hand"] - A_; L = np.linalg.norm(d); d /= L
            axis = A_ + (ss * L)[:, None] * d
            X[m] = X0[m] + w[:, None] * (axis + rad[m] * Rn[:, None] - X0[m])
    if puffer:  # horizontal baffles on the body
        th_, r_ = torso_cyl(b, X)
        z0 = X[:, 2].min()
        q = 1 + 0.05 * np.abs(np.sin(np.pi * (X[:, 2] - z0) / (0.085 * k))) ** 0.6 - 0.03
        q = np.where(isarm, 1, q)
        X[:, 0] = b.cx + (X[:, 0] - b.cx) * q
        X[:, 1] = b.yc + (X[:, 1] - b.yc) * q
    # 4. smooth the displacement so the regions blend, then keep it off the body
    D = laplace(X - X0, E, 40)
    X = X0 + D
    X = laplace(X, E, 8, taubin=True)
    X = o.col.push(X, 0.006 * k)
    _dbg('s4', X, F); _chk('s4', b, X, R)
    # 5. hem: hang straight down past the hips, finishing in a rib band
    loops = boundary_loops(F)
    lz = [X[l, 2].mean() for l in loops]
    neck_loop = loops[int(np.argmax(lz))]
    nonarm = [l for l in loops if not isarm[l].mean() > 0.5]
    waist = min(nonarm, key=lambda l: X[l, 2].mean())
    z_hem = J["pelvis"][2] - (0.13 + length) * k if kind != "tee" else J["pelvis"][2] - (0.11 + length) * k
    if puffer:
        z_hem = J["pelvis"][2] - (0.09 + length) * k
    drop = X[waist, 2].mean() - z_hem
    nr = max(2, int(drop / (0.012 * k)))
    base = X[waist].copy()
    rings = []
    for i in range(1, nr + 1):
        t = i / nr
        pts = base.copy()
        pts[:, 2] -= drop * t
        sc = 1.0 + (flare + HEM_FLARE_ADD) * t  # cloth falls slightly outward
        if rib and kind != "tee":
            sc *= 1 - 0.07 * smoothstep(1 - 0.055 * k / max(drop, 1e-3) - 0.25, 1.0, t)
        pts[:, 0] = b.cx + (pts[:, 0] - b.cx) * sc
        pts[:, 1] = b.yc + (pts[:, 1] - b.yc) * sc
        rings.append(pts)
    X, F, R, last = _extend_loop(X, F, waist, None, rings, R, "Hem")
    _dbg('s5', X, F); _chk('s5', b, X, R)
    isarm = _isin(R, ARMS)
    E = edges_of(F)
    X = laplace(X, E, 3, taubin=True)
    if REHANG_TOP: X = rehang(b, X, F, ~isarm, chest_z)
    _dbg('s6', X, F); _chk('s6', b, X, R)
    # collar: rib band (tee / hoodie), stand collar (puffer, track), turtleneck, shirt collar, lapel
    nl = neck_loop
    c = X[nl].mean(0)
    L0 = X[nl].copy()
    outd = L0[:, :2] - c[:2]; outd /= np.maximum(np.linalg.norm(outd, axis=1), 1e-9)[:, None]
    prof = {"rib": [(0.006, -0.0005), (0.012, -0.001)],
            "stand": [(0.02, -0.002), (0.04, -0.003), (0.06, -0.003), (0.064, 0.0)],
            "turtle": [(0.03, -0.002), (0.06, -0.003), (0.085, -0.002), (0.09, 0.002)],
            "shirt": [(0.012, -0.002), (0.024, -0.001), (0.026, 0.006), (0.01, 0.014), (-0.004, 0.018)],
            "lapel": LAPEL_PROF,
            "none": []}[collar]
    col_rings = []
    tup = None
    if collar == "rib" and o.col.tree is not None:
        # a rib collar lies along the body: on sloped (muscular) shoulders straight up would dig into the skin
        _, jn_ = o.col.tree.query(L0)
        nn_ = o.col.N[jn_]
        tup = np.array([0, 0, 1.0]) - nn_[:, 2:3] * nn_
        tup /= np.maximum(np.linalg.norm(tup, axis=1, keepdims=True), 1e-9)
    for dz, dr in prof:
        pts = L0.copy()
        if tup is not None:
            pts += tup * dz * k
        else:
            pts[:, 2] += dz * k
        pts[:, :2] += outd * dr * k
        col_rings.append(pts)
    if col_rings:
        X, F, R, _ = _extend_loop(X, F, nl, None, col_rings, R, "Collar")
    E = edges_of(F)
    X = laplace(X, E, 2, taubin=True)
    X = o.col.push(X, 0.006 * k)
    if kind == "jacket" and len(o.objs) > 0:
        # over other clothes: smooth-then-push a few times so the sleeve bridges an under-layer's hem step (a tee's
        # short sleeve) instead of tracing a ledge round the arm
        armv_ = _isin(R, ARMS)
        for _ in range(6):
            X = laplace(X, E, 3, mask=armv_)
            X = o.col.push(X, 0.006 * k)
    if FOLD_LIFT and collar in ("lapel", "shirt") and col_rings:
        # the turned-down part of a fold-over collar lay at the same height off the body as the panel under it:
        # the two surfaces fought through each other (a crinkled ruffle). Keep the fold a layer above the panel.
        cm_ = _isin(R, ("Collar",))
        r0 = np.linalg.norm(L0[:, :2] - c[:2], axis=1).mean()
        fold = cm_ & (np.linalg.norm(X[:, :2] - c[:2], axis=1) > r0 + 0.015 * k)
        if fold.any():
            X[fold] = o.col.push(X[fold], (0.006 + FOLD_LIFT) * k)
    if TORSO_SMOOTH and kind == "jacket":
        # the push round the shoulder blades left small star-shaped pinches on a jacket's back: smooth the body
        # panel (not the collar or sleeves) against the body a few times
        tm_ = ~_isin(R, ARMS + ("Collar",))
        for _ in range(TORSO_SMOOTH):
            X = laplace(X, E, 2, mask=tm_)
            X = o.col.push(X, 0.006 * k)
    if COLLAR_SMOOTH and collar in ("lapel", "shirt") and col_rings:
        # a fold-over collar's outer edge lands on the sloping shoulder: the push crumpled it into a ruffle.
        # Smooth the collar (and the cloth just under it) against the body a few times.
        cm_ = _isin(R, ("Collar",))
        if cm_.any():
            d_, _ = cKDTree(X[cm_]).query(X)
            cm_ = cm_ | (d_ < 0.02 * k)
            for _ in range(COLLAR_SMOOTH):
                X = laplace(X, E, 3, mask=cm_)
                X = o.col.push(X, 0.006 * k)
    _dbg('collar', X, F); _chk('collar', b, X, R)
    if UNDERARM_SMOOTH:
        # the body panel under a hanging arm: pushing it off the arm crumpled it into flakes, hidden at rest but torn
        # open as soon as the arm moves. Smooth it against the body only (the sleeve covers it at rest).
        bi = b.body_idx; am_ = _isin(b.reg[bi], ARMS + ("Hand",))
        if am_.any():
            d_, _ = cKDTree(b.co[bi][am_]).query(X)
            near = ~_isin(R, ARMS) & (d_ < 0.06 * k) & (X[:, 2] < J["l-shoulder"][2] - 0.16 * k)
            if near.any():
                for _ in range(20):
                    X = laplace(X, E, 3, mask=near)
                    X[near] = o.col_noarm.push(X[near], 0.006 * k)  # (the panel only: pushing the sleeves off the
                    # torso without the arm made the shoulders boxy)
    if front_open:  # open front (overshirts, coats): split the centre front, leave the collar ends apart
        neck_pts = X[nl].copy()
        # worn open: the fronts hang ~7 cm apart below the chest (a hairline slit read as a zip), closing up to the
        # collar; 0.0075k (not 0.006k) so the cut never sits exactly on a mesh column (that left bridges)
        hw_ = 0.0075 * k + 0.028 * k * np.clip((neck_z - 0.06 * k - X[:, 2]) / (0.14 * k), 0, 1)
        fo = np.where(X[:, 1] < b.yc, hw_ - np.abs(X[:, 0] - b.cx), -1.0)
        X, F, A_ = clip(X, F, fo, {"reg": R})
        R = A_["reg"]
        X, F, A_ = keep_big(X, F, {"reg": R}, frac=0.3)
        R = A_["reg"]
        _, nl_ = cKDTree(X).query(neck_pts)
        nl = list(nl_)
        hood = False; pocket = False
    if hasattr(b, "whole_co") and not getattr(b, "no_liner", False):
        X, F, R = _crevice_liner(b, X, F, R)
    # 6. colours: main / accent (rib, zip) / print or camo through vertex colours
    if ARMPIT_HUG > 0 and sleeve != "none" and o.col.tree is not None:
        # the armpit hugs the skin (small offset, no bridging web): it then moves exactly like the skin under it (with
        # ARMPIT_BODY weights), so swinging the arm forward can't open a gap where the arm skin shows
        fa = np.zeros(len(X))
        for sd in ("l", "r"):
            Js = J[sd + "-shoulder"]
            dd = np.linalg.norm(X - Js, axis=1)
            t_ = 1 - np.clip((dd - ARMPIT_R0 * k) / ((ARMPIT_R1 - ARMPIT_R0) * k), 0, 1)
            fa = np.maximum(fa, t_ * t_ * (3 - 2 * t_) * (X[:, 2] < Js[2] - 0.01 * k))
        fa *= ARMPIT_HUG
        if (fa > 0).any():
            _, jn = o.col.tree.query(X)
            T = o.col.P[jn] + o.col.N[jn] * (0.006 * k)
            X = X + fa[:, None] * (T - X)
            E_ = edges_of(F)
            X = laplace(X, E_, 3, mask=fa > 0.01)
            X = o.col.push(X, 0.005 * k)
    _dbg('preobj', X, F); _chk('pre-obj', b, X, R)
    reg_out = R
    nf = len(F)
    fc = np.array([X[f].mean(0) for f in F])
    fr = np.array([reg_out[f[0]] for f in F])
    mi = np.zeros(nf, int)
    acc = accent or color
    if rib:
        hem_band = fc[:, 2] < z_hem + 0.05 * k
        mi[hem_band & (fr == "Hem")] = 1
        mi[fr == "Collar"] = 1
        if sleeve == "long":
            fs, _, _ = arm_param(b, fc)
            mi[_isin(fr, ARMS) & (fs > s_end - 0.05)] = 1
    if zip_front:
        mi[(np.abs(fc[:, 0] - b.cx) < 0.006 * k) & (fc[:, 1] < b.yc)] = 2
    vcol = None
    if camo_pal is not None:
        vcol = camo(X, camo_pal, 0.07 * k)
    elif print_fn is not None or band is not None:
        vcol = np.tile(np.array(color[:3]), (len(X), 1))
        if print_fn is not None:
            print_fn(o.b, X, vcol)
        if band is not None:
            bz = J["l-shoulder"][2] - 0.13 * k
            inb_ = (np.abs(X[:, 2] - bz) < 0.025 * k) & ~_isin(R, ARMS)
            vcol[inb_] = band[:3]
    mats = [material(name + "_Main", tuple(color[:3]) + (1,), vcol=vcol is not None),
            material(name + "_Rib", tuple(acc[:3]) + (1,)),
            material(name + "_Zip", (0.08, 0.08, 0.09, 1), rough=0.4)]
    if vcol is not None and camo_pal is not None:
        # rib bands keep a solid colour
        pass
    ob = make_object(b, b.obj.name + "_" + name, X, F, mats, mi, vcol, thick=thick, arm_flag=_sleeve_flag(b, X, R))
    o.objs.append(ob)
    N = o.layer(X, F, thick)
    o.top = (X, N, F, nl, z_hem)
    if hood == "up":
        o.objs.append(build_hood_up(o, name, X, N, nl, color, vcol is not None and camo_pal, camo_pal))
    elif hood:
        o.objs.append(build_hood(o, name, X, N, nl, color, vcol is not None and camo_pal, camo_pal))
    if pocket:
        o.objs.append(build_pocket(o, name, X, F, z_hem, color, camo_pal))
    if hood and not zip_front:
        o.objs.extend(build_strings(o, name, X, N, nl, acc))
    if zip_front:
        zp = make_box(b, b.obj.name + "_" + name + "_ZipPull", X, N, nl, (0.6, 0.6, 0.62))
        if zp:
            o.objs.append(zp)
    return ob


def make_box(b, name, X, N, nl, rgba):
    k = b.k
    c = X[nl]
    i = np.argmin(c[:, 1])
    p = c[i] + N[nl[i]] * 0.006 * k - np.array([0, 0, 0.03 * k])
    me = bpy.data.meshes.new(name)
    w, h, d = 0.008 * k, 0.022 * k, 0.003 * k
    v = [(p[0] + x * w, p[1] - d + y * d, p[2] + z * h) for x in (-1, 1) for y in (-1, 1) for z in (-1, 1)]
    fcs = [[0, 1, 3, 2], [4, 6, 7, 5], [0, 4, 5, 1], [2, 3, 7, 6], [0, 2, 6, 4], [1, 5, 7, 3]]
    me.from_pydata(v, [], fcs); me.update()
    ob = bpy.data.objects.new(name, me)
    ob.data.materials.append(material("NC_Metal", rgba + (1,), rough=0.3))
    for col in b.obj.users_collection:
        col.objects.link(ob)
    ob.parent = b.obj; ob.matrix_parent_inverse = b.obj.matrix_world.inverted(); ob.matrix_world = b.obj.matrix_world.copy()
    return ob


def build_hood_up(o, name, X, N, nl, color, use_camo, pal):
    """A hood pulled up over the head (and over a cap if one was built first): grows from the hoodie neckline,
    follows the skull with a loose fabric gap and a soft peak at the back, and leaves an oval face opening whose
    sides come down into the neckline V. The cap brim sticks out through the opening."""
    b = o.b; k = b.k
    hm, top, eye_z, c = head_frame(b)
    eyes = _bodydata_eyes(b)
    ez = (eyes[0][2] + eyes[1][2]) / 2 if eyes else eye_z
    C = np.array([c[0], c[1] + 0.008 * k, ez - 0.01 * k])
    pts = b.co[hm]
    cp = o.col.P
    near = (cp[:, 2] > ez - 0.05 * k) & (np.hypot(cp[:, 0] - C[0], cp[:, 1] - C[1]) < 0.16 * k)
    pts = np.vstack([pts, cp[near]])
    R = pts - C; rn = np.linalg.norm(R, axis=1); U = R / rn[:, None]
    nth, nph = 72, 30
    ths = np.linspace(-np.pi, np.pi, nth, endpoint=False)
    phs = np.radians(np.linspace(-38, 86, nph))
    D = np.stack([np.cos(phs)[:, None] * np.cos(ths)[None], np.cos(phs)[:, None] * np.sin(ths)[None],
                  np.sin(phs)[:, None] * np.ones_like(ths)[None]], -1)  # (nph, nth, 3)
    dots = D.reshape(-1, 3) @ U.T
    cone = dots > np.cos(np.radians(9))
    rr = np.where(cone, rn[None], 0).max(1).reshape(nph, nth)
    rr = np.where(rr > 0, rr, np.nan)
    for _ in range(6):  # fill directions with no points from their neighbours
        m = np.isnan(rr)
        if not m.any():
            break
        nb = np.nanmean(np.stack([np.roll(rr, 1, 1), np.roll(rr, -1, 1), np.roll(rr, 1, 0), np.roll(rr, -1, 0)]), 0)
        rr[m] = nb[m]
    rr = np.where(np.isnan(rr), np.nanmedian(rr), rr)
    back = np.clip(np.sin(ths), 0, 1)[None]  # +y is the back of the head
    up = np.clip(np.sin(phs), 0, 1)[:, None]
    clr = (0.016 + 0.016 * up + 0.034 * back * np.exp(-((phs[:, None] - np.radians(25)) / np.radians(45)) ** 2)
           + 0.016 * back * np.exp(-((phs[:, None] - np.radians(58)) / np.radians(20)) ** 2)) * k
    raw = rr.copy()
    for _ in range(12):  # smooth the skull envelope so the fabric bridges ears and hairline
        rr = np.maximum(rr, 0.5 * rr + 0.125 * (np.roll(rr, 1, 1) + np.roll(rr, -1, 1)) +
                        0.125 * (np.vstack([rr[:1], rr[:-1]]) + np.vstack([rr[1:], rr[-1:]])))
    rr = np.maximum(rr, raw) + clr
    V_up = C + D * rr[..., None]
    # lower rings: blend from the lowest skull ring down to the hoodie neckline
    L = X[nl]; Lc = L.mean(0)
    phL = np.arctan2(L[:, 1] - Lc[1], L[:, 0] - Lc[0])
    order = np.argsort(phL)
    neck_ring = np.stack([np.interp(ths, phL[order], L[order, j], period=2 * np.pi) for j in range(3)], 1)
    neck_ring -= np.stack([np.cos(ths), np.sin(ths), np.zeros_like(ths)], 1) * 0.002 * k  # tucks inside the neckline
    low = []
    for t in np.linspace(0, 1, 7)[:-1]:
        bul = np.sin(np.pi * t) ** 0.7 * (0.026 + 0.01 * np.clip(np.sin(ths), 0, 1)) * k
        ring = neck_ring * (1 - t) + V_up[0] * t
        ring += np.stack([np.cos(ths), np.sin(ths), np.zeros_like(ths)], 1) * bul[:, None]
        low.append(ring)
    rings = low + list(V_up)
    V = np.vstack(rings + [rings[-1].mean(0) + np.array([0, 0, 0.004 * k])])
    nr = len(rings); pole = len(V) - 1
    F = [[i * nth + j, i * nth + (j + 1) % nth, (i + 1) * nth + (j + 1) % nth, (i + 1) * nth + j] for i in range(nr - 1) for j in range(nth)]
    F += [[(nr - 1) * nth + j, (nr - 1) * nth + (j + 1) % nth, pole] for j in range(nth)]
    E = edges_of(F)
    V = laplace(V, E, 10, taubin=True)
    # face opening
    th_v = np.arctan2(V[:, 1] - C[1], V[:, 0] - C[0])
    dth = np.abs(np.angle(np.exp(1j * (th_v + np.pi / 2))))
    z_mid, z_top = ez - 0.02 * k, ez + 0.085 * k
    zn = Lc[2]
    w = np.radians(46) - np.radians(38) * np.clip((z_mid - V[:, 2]) / (z_mid - zn), 0, 1) ** 0.8
    f = 1 - (dth / w) ** 2 - (np.clip(V[:, 2] - z_mid, 0, None) / (z_top - z_mid)) ** 2
    Pq, Fq, _ = clip(V, F, f, {})
    Pq, Fq, _ = keep_big(Pq, Fq, {}, frac=0.5)
    E = edges_of(Fq)
    # the skull envelope already clears the head and cap; only keep the lower hood off the shoulders and hoodie
    # (ear backs and cap edges have inward-facing normals that would dent the fabric)
    lowc = Collider(); mk = o.col.P[:, 2] < ez - 0.07 * k
    lowc.add(o.col.P[mk], o.col.N[mk])
    for _ in range(3):
        Pq = lowc.push(Pq, 0.004 * k)
        Pq = laplace(Pq, E, 2, taubin=True)
    Pq = lowc.push(Pq, 0.004 * k)
    # soft rolled edge round the face opening
    loops = boundary_loops(Fq)
    lp = max(loops, key=lambda l: np.ptp(Pq[l, 2]) if len(l) > 3 else 0)
    Rg = np.array(["Hood"] * len(Pq), dtype=object)
    base = Pq[lp]
    inward = np.array([C[0], C[1] + 0.04 * k, base[:, 2].mean()]) - base
    inward[:, 2] = 0; inward /= np.linalg.norm(inward, axis=1, keepdims=True) + 1e-9
    Pq, Fq, Rg, _ = _extend_loop(Pq, Fq, lp, None, [base - inward * 0.004 * k, base + inward * 0.006 * k], Rg, "Hem")
    vcol = camo(Pq, pal, 0.07 * k) if use_camo else None
    ob = make_object(b, b.obj.name + "_" + name + "_Hood", Pq, Fq, [material(name + "_Main", tuple(color[:3]) + (1,), vcol=vcol is not None)],
                     None, vcol, thick=0.004 * k, subsurf=1)
    o.layer(Pq, Fq, 0.004 * k)
    return ob


def build_hood(o, name, X, N, nl, color, use_camo, pal):
    """A lowered hood: a soft roll around the neckline that is thin at the front and drapes down the upper back."""
    b = o.b; k = b.k
    L = X[nl]
    c = L.mean(0)
    phi = np.arctan2(L[:, 1] - c[1], L[:, 0] - c[0])
    back = np.clip((np.sin(phi) + 0.25) / 1.25, 0, 1) ** 1.4  # +y is the back
    ra = (0.014 + 0.036 * back) * k
    rz = (0.014 + 0.075 * back) * k
    up = (0.006 + 0.012 * back) * k
    dn = (0.0 + 0.05 * back) * k
    out = np.stack([np.cos(phi), np.sin(phi), np.zeros_like(phi)], 1)
    M = 14
    a = np.linspace(0, 2 * np.pi, M, endpoint=False)
    V = []
    for i in range(len(L)):
        cen = L[i] + out[i] * ra[i] * 0.9 + np.array([0, 0, up[i] - dn[i]])
        for aj in a:
            V.append(cen + out[i] * np.cos(aj) * ra[i] + np.array([0, 0, 1.0]) * np.sin(aj) * (rz[i] if np.sin(aj) < 0 else rz[i] * 0.45 + up[i]))
    V = np.array(V)
    n = len(L)
    F = []
    for i in range(n):
        for j in range(M):
            i2, j2 = (i + 1) % n, (j + 1) % M
            F.append([i * M + j, i2 * M + j, i2 * M + j2, i * M + j2])
    E = edges_of(F)
    V = laplace(V, E, 6, taubin=True)
    for _ in range(3):
        V = o.col.push(V, 0.004 * k)
        V = laplace(V, E, 2, taubin=True)
    V = o.col.push(V, 0.004 * k)
    vcol = camo(V, pal, 0.07 * k) if use_camo else None
    ob = make_object(b, b.obj.name + "_" + name + "_Hood", V, F, [material(name + "_Main", tuple(color[:3]) + (1,), vcol=vcol is not None)], None, vcol, thick=0, subsurf=1)
    o.layer(V, F, 0.002)
    return ob


def build_pocket(o, name, X, F, z_hem, color, pal):
    b = o.b; k = b.k
    z0, z1 = z_hem + 0.07 * k, z_hem + 0.2 * k
    w = lambda z: 0.095 * k - 0.03 * k * np.clip((z - z0) / (z1 - z0), 0, 1)
    f = np.maximum.reduce([np.abs(X[:, 0] - b.cx) - w(X[:, 2]), z0 - X[:, 2], X[:, 2] - z1, X[:, 1] - b.yc])
    P, Fp, _ = clip(X, F, f, {})
    P, Fp, _ = keep_big(P, Fp, {})
    N = vnormals(P, Fp)
    P = P + N * 0.004 * k
    vcol = camo(P, pal, 0.07 * k) if pal is not None else None
    ob = make_object(b, b.obj.name + "_" + name + "_Pocket", P, Fp, [material(name + "_Main", tuple(color[:3]) + (1,), vcol=vcol is not None)], None, vcol, thick=0.002, subsurf=1)
    o.layer(P, Fp, 0.002)
    return ob


def tube(points, radius, seg=8):
    P = np.asarray(points)
    V, F = [], []
    n = len(P)
    for i in range(n):
        t = P[min(i + 1, n - 1)] - P[max(i - 1, 0)]; t /= np.linalg.norm(t) + 1e-12
        u = np.cross(t, [0.3, 0.2, 1.0]); u /= np.linalg.norm(u); v = np.cross(t, u)
        r = radius[i] if np.ndim(radius) else radius
        for j in range(seg):
            a = 2 * np.pi * j / seg
            V.append(P[i] + r * (np.cos(a) * u + np.sin(a) * v))
    for i in range(n - 1):
        for j in range(seg):
            j2 = (j + 1) % seg
            F.append([i * seg + j, i * seg + j2, (i + 1) * seg + j2, (i + 1) * seg + j])
    F.append(list(range(seg))[::-1]); F.append([(n - 1) * seg + j for j in range(seg)])
    return np.array(V), F


def surface_path(o, X, N, start, length, step, gap):
    """Let a string fall down the front of a garment from start."""
    tree = cKDTree(X)
    pts = [start]
    p = start.copy()
    for _ in range(int(length / step)):
        p = p + np.array([0, 0, -step])
        d, j = tree.query(p, k=6)
        best = j[np.argmin(np.abs(X[j, 2] - p[2]) + np.abs(X[j, 0] - p[0]))]
        q = X[best] + N[best] * gap
        p = np.array([p[0] * 0.7 + q[0] * 0.3, min(p[1], q[1]) if p[1] > q[1] else q[1], p[2]])
        p[1] = q[1]
        pts.append(p.copy())
    pts = np.array(pts)
    for _ in range(3):
        pts[1:-1] = 0.25 * pts[:-2] + 0.5 * pts[1:-1] + 0.25 * pts[2:]
    return pts


def build_strings(o, name, X, N, nl, rgba):
    b = o.b; k = b.k
    L = X[nl]
    c = L.mean(0)
    out = []
    for sgn in (-1, 1):
        sx = b.cx + sgn * 0.035 * k
        cand = np.argsort(np.abs(L[:, 0] - sx) + 3 * np.maximum(L[:, 1] - c[1], 0))[0]
        st = L[cand] + np.array([0, -0.012 * k, -0.004 * k])
        path = surface_path(o, X, N, st, (0.17 + 0.03 * (sgn > 0)) * k, 0.0045 * k, 0.012 * k)  # lie on the fabric (a jacket over it must clear them)
        rr = np.full(len(path), 0.0032 * k); rr[-3:] = 0.0042 * k
        V, F = tube(path, rr, 8)
        ob = make_object(b, b.obj.name + "_" + name + "_String" + ("L" if sgn > 0 else "R"), V, F,
                         [material(name + "_String", tuple(rgba[:3]) + (1,), rough=0.7)], None, None, thick=0, subsurf=0)
        out.append(ob)
    return out


def _crevice_liner(b, X, F, R, gap=0.045, lift=0.0045):
    """Heavy builds: where an arm rests against the side, the gap between arm and body is only a centimetre or two
    and no draped panel fits in it. Line the base-layer tank in that crevice with a skin-tight strip of the
    garment's own fabric (joined to the garment), so the tank can never show between arm and shirt."""
    me = b.obj.data; k = b.k
    cw = b.whole_co; reg = np.asarray(b.whole_reg)
    tmi = [i for i, m_ in enumerate(me.materials) if m_ and "TankTop" in m_.name]
    if not tmi:
        return X, F, R
    am = np.isin(reg, ["UArm", "LArm", "Hand"])
    if not am.any():
        return X, F, R
    tf = [list(p.vertices) for p in me.polygons if p.material_index in tmi]
    tv = np.unique(np.concatenate(tf))
    da, _ = cKDTree(cw[am]).query(cw[tv])
    near = np.zeros(len(cw), bool)
    sh_z = min(b.J["l-shoulder"][2], b.J["r-shoulder"][2])
    shx = abs(b.J["l-shoulder"][0] - b.cx)
    near[tv] = (da < gap * k) | (np.abs(cw[tv, 0] - b.cx) > 0.55 * shx)   # the crevice and the whole flank / strap edge
    sel = [f for f in tf if near[f].all()]
    if len(sel) < 3:
        return X, F, R
    # grow by one ring so the strip tucks under the garment's own side panel
    used = np.zeros(len(cw), bool)
    for f in sel:
        used[f] = True
    sel = [f for f in tf if used[f].any()]
    vid = np.unique(np.concatenate(sel))
    remap = -np.ones(len(cw), int); remap[vid] = np.arange(len(vid))
    Fl = [[int(remap[v]) for v in f] for f in sel]
    Pl = cw[vid]
    Nw_ = np.array([v.normal[:] for v in me.vertices])[vid]   # the body's own normals (outward)
    Nl = vnormals(Pl, Fl)
    Nl = np.where((np.einsum("ij,ij->i", Nl, Nw_) < 0)[:, None], -Nl, Nl)
    Pl = Pl + Nw_ * lift * k
    off = len(X)
    X = np.vstack([X, Pl])
    F = list(F) + [[v + off for v in f] for f in Fl]
    R = np.concatenate([np.asarray(R, dtype=object), np.array(["Torso"] * len(Pl), dtype=object)])
    return X, F, R


def rehang(b, X, F, sel, hang_from, ease=0.0):
    """Final straight fall: below hang_from the cloth radius never shrinks going down (removes ledges)."""
    rnew, _ = drape_envelope(b, X, sel, X[sel, 2].max(), ease, 0.0, hang_from, flare=0.0005)
    _, r = torso_cyl(b, X)
    w = sel & (X[:, 2] < hang_from)
    sc = np.where(w & (r > 1e-6), rnew / np.maximum(r, 1e-6), 1)
    if REHANG_BLEND:
        # ease in below hang_from: a hard start creased the back into star-shaped pinches over the shoulder blades
        sc = 1 + (sc - 1) * smoothstep(0.0, 1.0, (hang_from - X[:, 2]) / (REHANG_BLEND * b.k))
    X = X.copy()
    X[:, 0] = b.cx + (X[:, 0] - b.cx) * sc
    X[:, 1] = b.yc + (X[:, 1] - b.yc) * sc
    return X


def _leg_falloff(b, X, z_top, slope=0.1, nb_z=80, nb_p=32):
    """Cloth below a bump (the base-shorts hem, a thick thigh) falls away gradually instead of printing a ridge:
    per leg and angle, the radius from the leg axis may shrink by at most `slope` per unit height going down."""
    k = b.k; X = X.copy()
    for side in ("l", "r"):
        A_ = b.J[side + "-upper-leg"]; B_ = b.J[side + "-ankle"]
        m = (b.side(X) == side) & (X[:, 2] < z_top) & (X[:, 2] > B_[2])
        if m.sum() < 50:
            continue
        d = B_ - A_; L = np.linalg.norm(d); d /= L
        t = np.clip((X[m] - A_) @ d, 0, L)
        ax = A_ + t[:, None] * d
        rv = X[m] - ax; r = np.linalg.norm(rv, axis=1)
        ph = np.arctan2(rv[:, 1], rv[:, 0])
        zt = (z_top - X[m, 2])
        bi = np.clip((zt / (z_top - B_[2]) * nb_z).astype(int), 0, nb_z - 1)
        bj = ((ph + np.pi) / (2 * np.pi) * nb_p).astype(int) % nb_p
        G = np.zeros((nb_z, nb_p)); np.maximum.at(G, (bi, bj), r)
        dz = (z_top - B_[2]) / nb_z
        for i in range(1, nb_z):
            G[i] = np.maximum(G[i], G[i - 1] - slope * dz)
        for _ in range(2):
            G = np.maximum(G, 0.5 * G + 0.25 * (np.roll(G, 1, 1) + np.roll(G, -1, 1)))
        # interpolate in z so the envelope has no steps between bins
        fz = zt / (z_top - B_[2]) * nb_z - 0.5
        i0 = np.clip(np.floor(fz).astype(int), 0, nb_z - 1); i1 = np.clip(i0 + 1, 0, nb_z - 1); u = np.clip(fz - i0, 0, 1)
        env = G[i0, bj] * (1 - u) + G[i1, bj] * u
        rn = np.minimum(np.maximum(r, env), r + 0.012 * k)  # only evens out small bumps
        sg = 1.0 if side == "l" else -1.0
        inner = np.clip((rv[:, 0] * sg / np.maximum(r, 1e-9) + 0.5) / 0.4, 0, 1)  # leave the inseam alone
        rn = r + (rn - r) * inner
        X[m] = ax + rv * (rn / np.maximum(r, 1e-9))[:, None]
    return X



def _hand_clear(o, X, F, radius=0.07, cloth=0.004):
    """Rest pose: the hands hang against the hips. Pull the cloth in under each hand (a smooth press, never
    below the body) so the hand rests ON the pants / skirt instead of vanishing into them. Measured on curvy
    builds the whole hand sat inside the cloth (Female_Heavy, 2026-11-24)."""
    b = o.b
    if not hasattr(b, "whole_co"):
        return X
    k = b.k; cw = np.asarray(b.whole_co); rg = np.asarray(b.whole_reg)
    H = cw[rg == "Hand"]
    bm = np.isin(rg, ("Torso", "ULeg", "LLeg"))
    if not len(H) or not bm.any():
        return X
    nw = np.array([v.normal[:] for v in b.obj.data.vertices])
    if len(nw) != len(cw):
        return X
    Bv, Bn = cw[bm], nw[bm]
    tb = cKDTree(Bv)
    _, jh = tb.query(H); gap_h = np.einsum("ij,ij->i", H - Bv[jh], Bn[jh])
    dh, ih = cKDTree(H).query(X)
    wt = smoothstep(0.0, 1.0, np.clip(1.0 - dh / (radius * k), 0, 1))
    if not (wt > 0).any():
        return X
    _, jb = tb.query(X); nb = Bn[jb]
    off = np.einsum("ij,ij->i", X - Bv[jb], nb)
    target = np.maximum(gap_h[ih] - (cloth + 0.003) * k, 0.004 * k)
    delta = wt * np.maximum(0.0, off - target)
    E = np.array(edges_of(F))
    for _ in range(4):  # smooth press, not a hand-shaped imprint
        acc = np.zeros(len(X)); cnt = np.zeros(len(X))
        np.add.at(acc, E[:, 0], delta[E[:, 1]]); np.add.at(acc, E[:, 1], delta[E[:, 0]])
        np.add.at(cnt, E[:, 0], 1); np.add.at(cnt, E[:, 1], 1)
        delta = np.maximum(delta, 0.5 * delta + 0.5 * acc / np.maximum(cnt, 1))
    delta = np.minimum(delta, np.maximum(off - 0.004 * k, 0))
    return X - nb * delta[:, None]

def build_pants(o, name, fit="baggy", color=(0.06, 0.065, 0.075), accent=None, stack=True, cuffed=False,
                cargo=False, camo_pal=None, thick=0.004, shorts=False):
    b = o.low; k = b.k; J = b.J; P0 = b.co; reg = b.reg
    pel = J["pelvis"][2]
    front = np.clip((b.yc - P0[:, 1]) / (0.08 * k), 0, 1)
    # the waistband must sit over the top of the base-layer shorts (top at pelvis + 0.10..0.12k on every body)
    z_waist = pel + (0.132 - 0.006 * front) * k
    knee = (J["l-knee"][2] + J["r-knee"][2]) / 2
    ank = (J["l-ankle"][2] + J["r-ankle"][2]) / 2
    z_cut = (knee - 0.02 * k) if shorts else ank + 0.09 * k
    f = np.ones(len(P0))
    m = _isin(reg, ("Torso", "ULeg", "LLeg"))
    f[m] = np.maximum(P0[m, 2] - z_waist[m], z_cut - P0[m, 2])
    P, F, R = _start(b, f)
    E = edges_of(F)
    Nb = vnormals(P, F)
    X0 = P + Nb * 0.009 * k
    X = X0.copy()
    # seat and hips: smooth envelope around the torso axis, hanging from the hip bones
    tor = R == "Torso"
    hip_z = pel - 0.03 * k
    rnew, _ = drape_envelope(b, X0, tor, z_waist.max(), 0.015 if fit != "slim" else 0.005, 0.002 * k, hip_z)
    _, r = torso_cyl(b, X0)
    sc = np.where(tor & (r > 1e-6), rnew / np.maximum(r, 1e-6), 1)
    X[:, 0] = b.cx + (X0[:, 0] - b.cx) * sc
    X[:, 1] = b.yc + (X0[:, 1] - b.yc) * sc
    # legs: round tubes, from the thigh down to a wide opening (baggy) or a gathered cuff (joggers)
    sl, rad, Rl = leg_param(b, X0)
    legs = ~tor | (X0[:, 2] < b.crotch_z + 0.03 * k)
    hem_r = {"baggy": 0.084, "straight": 0.07, "slim": 0.05, "cargo": 0.085, "sweat": 0.075}[fit] * k
    ease = {"baggy": 0.09, "straight": 0.05, "slim": 0.02, "cargo": 0.09, "sweat": 0.08}[fit]
    s_cut = {}
    for side in ("l", "r"):
        mm = legs & (b.side(X0) == side)
        q = Rl[mm & (sl > 0.08) & (sl < 0.22)]
        r_th = np.percentile(q, 92) if len(q) else Rl[mm].max()
        ss = sl[mm]
        # the top of each leg flares out to meet the seat so there is no step at the crotch line
        Rt = np.interp(ss, [0, 0.1, 0.3, 1.0], [r_th * (1 + ease * 1.6), r_th * (1 + ease * 1.25), r_th * (1 + ease) * 0.97,
                                                max(hem_r, r_th * 0.55)])
        if cuffed:
            qa = Rl[mm & (sl > 0.85)]
            r_an = np.percentile(qa, 90) if len(qa) else hem_r * 0.6
            g = smoothstep(0.86, 0.94, ss)
            Rt = Rt * (1 - g) + (r_an + 0.008 * k) * g
            Rt = Rt * (1 + 0.06 * np.sin(2 * np.pi * ss / 0.05 + 2 * np.arctan2(rad[mm][:, 1], rad[mm][:, 0])) * smoothstep(0.55, 0.75, ss) * (1 - g))
        Rn = np.maximum(Rl[mm], Rt)
        w = smoothstep(0.0, 0.14, ss)
        A_ = J[side + "-upper-leg"]; d = J[side + "-ankle"] - A_; L = np.linalg.norm(d); d /= L
        axis = A_ + (ss * L)[:, None] * d
        Xb = X[mm].copy()  # seat envelope where the leg starts (avoids a tight band at the crotch line)
        X[mm] = Xb + w[:, None] * (axis + rad[mm] * Rn[:, None] - Xb)
    # inner legs never cross the centre line
    gap = 0.008 * k
    for sgn, side in ((1, "l"), (-1, "r")):
        mm = legs & (b.side(X0) == side)
        bad = mm & ((X[:, 0] - b.cx) * sgn < gap)
        X[bad, 0] = b.cx + sgn * gap
    D = laplace(X - X0, E, 45)
    X = X0 + D
    X = laplace(X, E, 6, taubin=True)
    X = _leg_falloff(b, X, b.crotch_z - 0.02 * k)
    X = o.col_noarm.push(X, 0.006 * k)
    # pant legs: hang straight down past the cut and stack on top of the shoes
    loops = boundary_loops(F)
    waist = max(loops, key=lambda l: X[l, 2].mean())
    leg_loops = [l for l in loops if l is not waist]
    leg_loops = sorted(leg_loops, key=lambda l: X[l, 2].mean())[:2]
    z_end = (b.floor + (0.045 if not cuffed else 0.1) * k) if not shorts else z_cut
    for ll in leg_loops:
        if shorts:
            break
        base = X[ll].copy()
        c = base.mean(0)
        phi = np.arctan2(base[:, 1] - c[1], base[:, 0] - c[0])
        r0 = np.hypot(base[:, 0] - c[0], base[:, 1] - c[1])
        drop = c[2] - z_end
        nr = max(2, int(drop / (0.01 * k)))
        rings = []
        for i in range(1, nr + 1):
            t = i / nr
            z = base[:, 2] - drop * t
            if cuffed:
                rr = r0 * (1 - 0.05 * t)
            else:
                rr = r0 + (max(hem_r, r0.mean()) - r0) * smoothstep(0, 0.6, t)
            pts = np.stack([c[0] + np.cos(phi) * rr, c[1] + np.sin(phi) * rr, z], 1)
            rings.append(pts)
        X, F, R, _ = _extend_loop(X, F, ll, None, rings, R, "PantHem")
    E = edges_of(F)
    tor = R == "Torso"
    # stacked folds around the lower legs (rings that wobble around the leg)
    if stack and not cuffed and not shorts:
        for side in ("l", "r"):
            mm = (~tor) & (b.side(X) == side)
            A_ = J[side + "-upper-leg"]; Bk = J[side + "-ankle"]
            cxy = np.array([Bk[0], Bk[1]])
            zz = X[mm, 2]
            ph = np.arctan2(X[mm, 1] - cxy[1], X[mm, 0] - cxy[0])
            amp = 0.07 * smoothstep(knee - 0.05 * k, ank + 0.02 * k, zz)[:] * 1.0
            amp = 0.05 * (1 - smoothstep(b.floor + 0.08 * k, b.floor + 0.3 * k, zz))
            seed = 1.7 if side == "l" else 0.4
            wobble = 2.2 * np.sin(ph * 2 + seed) + 1.1 * np.sin(ph * 3 + 2 * seed) + 0.8 * np.sin(ph * 5 + zz * 9 / k)
            wave = np.sin(2 * np.pi * zz / (0.05 * k) + wobble)
            wave = np.sign(wave) * np.abs(wave) ** 0.7
            q = 1 + amp * wave
            X[mm, 0] = cxy[0] + (X[mm, 0] - cxy[0]) * q
            X[mm, 1] = cxy[1] + (X[mm, 1] - cxy[1]) * q
    X = laplace(X, E, 2, taubin=True)
    X = o.col_noarm.push(X, 0.006 * k)
    X = laplace(X, E, 1, taubin=True)
    X = o.col_noarm.push(X, 0.005 * k)
    X = _hand_clear(o, X, F, cloth=thick)
    # waistband accent faces
    fc = np.array([X[f].mean(0) for f in F])
    mi = np.zeros(len(F), int)
    # a real waistband is a ~4 cm strip at the top (everything above the pelvis made a 13 cm band since the
    # waist went up over the base shorts, and plaid / camo stopped at the hips)
    front_f = np.clip((b.yc - fc[:, 1]) / (0.08 * k), 0, 1)
    mi[fc[:, 2] > pel + (0.132 - 0.006 * front_f - 0.042) * k] = 1
    vcol = camo(X, camo_pal, 0.07 * k) if camo_pal is not None else None
    mats = [material(name + "_Main", tuple(color[:3]) + (1,), vcol=vcol is not None),
            material(name + "_Band", tuple((accent or color)[:3]) + (1,))]
    ob = make_object(b, b.obj.name + "_" + name, X, F, mats, mi, vcol, thick=thick)
    o.objs.append(ob)
    N = o.layer(X, F, thick)
    if cargo:
        for side, sgn in (("l", 1), ("r", -1)):
            zc_ = knee + 0.13 * k
            f2 = np.maximum.reduce([np.abs(X[:, 2] - zc_) - 0.075 * k, -(X[:, 0] - J[side + "-knee"][0]) * sgn - 0.0 * k,
                                    np.abs(X[:, 1] - J[side + "-knee"][1]) - 0.06 * k, (~(b.side(X) == side)).astype(float)])
            Pp, Fp, _ = clip(X, F, f2, {})
            if len(Fp) < 4:
                continue
            Pp, Fp, _ = keep_big(Pp, Fp, {})
            Np = vnormals(Pp, Fp)
            Pp = Pp + Np * 0.006 * k
            o.objs.append(make_object(b, b.obj.name + "_" + name + "_Cargo" + side.upper(), Pp, Fp,
                                      [material(name + "_Main", tuple(color[:3]) + (1,), vcol=vcol is not None)], None,
                                      camo(Pp, camo_pal, 0.07 * k) if camo_pal is not None else None, thick=0.003))
    return ob


def build_shoes(o, name, high=False, color=(0.95, 0.95, 0.94), sole=(0.97, 0.97, 0.95), accent=(0.1, 0.1, 0.12),
                lace=None, chunky=1.0):
    b = o.b; k = b.k; J = b.J; P0 = b.co; reg = b.reg
    ank = (J["l-ankle"][2] + J["r-ankle"][2]) / 2
    z_col = ank + (0.075 if high else 0.025) * k
    f = np.ones(len(P0))
    m = _isin(reg, ("Foot", "LLeg"))
    f[m] = P0[m, 2] - z_col
    P, F, R = _start(b, f)
    E = edges_of(F)
    X = P + vnormals(P, F) * 0.012 * k
    # no toes: smooth the whole shoe into a clean last, then keep it off the foot
    for _ in range(12):
        X = laplace(X, E, 5)
        X = o.col.push(X, 0.016 * k)
    X = laplace(X, E, 3, taubin=True)
    # flat outsole with a slight flare
    fl = b.floor
    sole_h = 0.03 * k * chunky
    for side in ("l", "r"):
        mm = b.side(X) == side
        c = np.array([J[side + "-ankle"][0], X[mm, 1].mean()])
        low = mm & (X[:, 2] < fl + sole_h)
        fac = 1 + 0.06 * (1 - (X[low, 2] - fl) / sole_h)
        X[low, 0] = c[0] + (X[low, 0] - c[0]) * fac
        X[low, 1] = c[1] + (X[low, 1] - c[1]) * fac
    X[:, 2] = np.maximum(X[:, 2], fl - 0.006 * k)
    bottom = X[:, 2] < fl + 0.004 * k
    X[bottom, 2] = fl - 0.006 * k
    # padded collar
    loops = boundary_loops(F)
    for ll in loops:
        base = X[ll].copy(); c = base.mean(0)
        rings = []
        for t, (dz, sc) in enumerate(((0.006, 1.03), (0.008, 0.97), (0.002, 0.9))):
            pts = base.copy(); pts[:, 2] += dz * k
            pts[:, :2] = c[:2] + (pts[:, :2] - c[:2]) * sc
            rings.append(pts)
        X, F, R, _ = _extend_loop(X, F, ll, None, rings, R, "Collar")
    fc = np.array([X[f].mean(0) for f in F])
    fn = np.array([np.cross(X[f[1]] - X[f[0]], X[f[2]] - X[f[0]]) for f in F])
    fn /= np.maximum(np.linalg.norm(fn, axis=1), 1e-12)[:, None]
    mi = np.zeros(len(F), int)
    mi[fc[:, 2] < fl + sole_h] = 1
    for side in ("l", "r"):
        mm = b.side(fc) == side
        ax = J[side + "-ankle"]
        # lace panel on top of the forefoot
        lp = mm & (fn[:, 2] > 0.45) & (np.abs(fc[:, 0] - ax[0]) < 0.022 * k) & (fc[:, 1] < ax[1] - 0.01 * k) & (fc[:, 1] > ax[1] - 0.11 * k)
        mi[lp] = 3
        # side panel accent (a plain original stripe, no brand marks)
        sp = mm & (np.abs(fn[:, 2]) < 0.5) & (fc[:, 2] > fl + sole_h + 0.006 * k) & (fc[:, 2] < fl + sole_h + 0.03 * k) & (fc[:, 1] > ax[1] - 0.09 * k) & (fc[:, 1] < ax[1] + 0.02 * k)
        mi[sp & (mi == 0)] = 2
    mi[np.array([R[f[0]] == "Collar" for f in F])] = 2
    mats = [material(name + "_Upper", tuple(color[:3]) + (1,), rough=0.6), material(name + "_Sole", tuple(sole[:3]) + (1,), rough=0.8),
            material(name + "_Accent", tuple(accent[:3]) + (1,), rough=0.6), material(name + "_Laces", tuple((lace or color)[:3]) + (1,), rough=0.9)]
    ob = make_object(b, b.obj.name + "_" + name, X, F, mats, mi, None, thick=0.003)
    o.objs.append(ob)
    o.layer(X, F, 0.003)
    return ob


def build_sneakers(o, name, high=False, color=(0.95, 0.95, 0.94), sole=(0.97, 0.97, 0.95), accent=(0.1, 0.1, 0.12),
                   lace=None, chunky=1.0, nu=34, na=28):
    """Clean lofted sneaker per foot: slices along the foot give the width and height, a rounded box section gives
    the shape (flat outsole, round toe box, padded heel), so no toes ever show."""
    b = o.low; k = b.k; J = b.J
    fl = b.floor
    sole_h = 0.028 * k * chunky
    allV, allF, allM = [], [], []
    for side in ("l", "r"):
        ank = J[side + "-ankle"]
        m = (b.reg == "Foot") & (b.side(b.co) == side)
        m |= (b.reg == "LLeg") & (b.side(b.co) == side) & (b.co[:, 2] < ank[2] + 0.02 * k)
        Pf = b.co[m]
        # foot direction from the heel to the toes (PCA in the ground plane, pointing to -y)
        xy = Pf[:, :2] - Pf[:, :2].mean(0)
        _, _, vt = np.linalg.svd(xy, full_matrices=False)
        d = vt[0] if vt[0][1] < 0 else -vt[0]
        lat = np.array([-d[1], d[0]])
        c0 = Pf[:, :2].mean(0)
        u = (Pf[:, :2] - c0) @ d
        v = (Pf[:, :2] - c0) @ lat
        u0, u1 = u.min() - 0.012 * k, u.max() + 0.018 * k
        us = np.linspace(u0, u1, nu)
        W, T, V0 = np.zeros(nu), np.zeros(nu), np.zeros(nu)
        z_top_max = ank[2] + (0.07 if high else 0.0) * k
        for i, uu in enumerate(us):
            sl = np.abs(u - uu) < 0.02 * k
            if sl.sum() < 3:
                W[i] = np.nan; continue
            vv = v[sl]; zz = Pf[sl, 2]
            W[i] = (vv.max() - vv.min()) / 2 + 0.014 * k
            V0[i] = (vv.max() + vv.min()) / 2
            T[i] = min(zz.max(), z_top_max) + 0.014 * k
        ok = ~np.isnan(W)
        W = np.interp(us, us[ok], W[ok]); T = np.interp(us, us[ok], T[ok]); V0 = np.interp(us, us[ok], V0[ok])
        for _ in range(3):
            W[1:-1] = 0.25 * W[:-2] + 0.5 * W[1:-1] + 0.25 * W[2:]
            T[1:-1] = 0.25 * T[:-2] + 0.5 * T[1:-1] + 0.25 * T[2:]
            V0[1:-1] = 0.25 * V0[:-2] + 0.5 * V0[1:-1] + 0.25 * V0[2:]
        # rounded toe and heel in plan and side view
        tq = 2 * (us - u0) / (u1 - u0) - 1
        rnd = (1 - np.abs(tq) ** 5) ** (1 / 5)
        rtoe = (1 - np.clip((us - (u1 - 0.05 * k)) / (0.05 * k), 0, 1) ** 2) ** 0.5
        T = np.maximum(fl + sole_h + 0.02 * k, fl + (T - fl) * np.where(tq > 0, (0.55 + 0.45 * rtoe), 1.0))
        W = W * rnd ** 0.8 + 0.002 * k
        if high:
            T = np.maximum(T, np.where(tq < 0.1, z_top_max + 0.012 * k, T))
        a = np.linspace(0, 2 * np.pi, na, endpoint=False)
        base = len(allV)
        for i in range(nu):
            spring = 0.014 * k * np.clip((tq[i] - 0.55) / 0.45, 0, 1) ** 2   # toe spring
            zb = fl - 0.004 * k + spring
            hz = (T[i] - zb) / 2 * (0.25 + 0.75 * rnd[i] ** 0.6)  # ends round off in height too
            zc = zb + hz
            for aj in a:
                ca, sa = np.cos(aj), np.sin(aj)
                p = 2.6 if sa > 0 else 6.0   # flat bottom, rounded top
                vv = W[i] * np.sign(ca) * np.abs(ca) ** (2 / p)
                zz = zc + hz * np.sign(sa) * np.abs(sa) ** (2 / p)
                if zz < fl + sole_h + spring:
                    vv *= 1.05
                xy = c0 + d * us[i] + lat * (V0[i] + vv)
                allV.append([xy[0], xy[1], zz])
        for i in range(nu - 1):
            for j in range(na):
                j2 = (j + 1) % na
                allF.append([base + i * na + j, base + i * na + j2, base + (i + 1) * na + j2, base + (i + 1) * na + j])
        # end caps
        for i, rev in ((0, True), (nu - 1, False)):
            cidx = len(allV)
            allV.append(np.mean([allV[base + i * na + j] for j in range(na)], axis=0).tolist())
            for j in range(na):
                j2 = (j + 1) % na
                tri = [base + i * na + j, base + i * na + j2, cidx]
                allF.append(tri[::-1] if not rev else tri)
    X = np.array(allV, float)
    F = allF
    # make the outside normals face out
    N = vnormals(X, F)
    E = edges_of(F)
    X = laplace(X, E, 2, taubin=True)
    fc = np.array([X[f].mean(0) for f in F])
    fn = np.array([np.cross(X[f[1]] - X[f[0]], X[f[2]] - X[f[0]]) for f in F])
    fn /= np.maximum(np.linalg.norm(fn, axis=1), 1e-12)[:, None]
    # winding check: normals should point away from each shoe's centre
    cen = np.array([X[b.side(X) == s].mean(0) for s in ("l", "r")])
    sc = np.where(b.side(fc)[:, None] == "l", cen[0], cen[1])
    if np.mean(np.einsum("ij,ij->i", fn, fc - sc)) < 0:
        F = [f[::-1] for f in F]; fn = -fn
    mi = np.zeros(len(F), int)
    mi[fc[:, 2] < fl + sole_h] = 1
    for side in ("l", "r"):
        mm = b.side(fc) == side
        ax = J[side + "-ankle"]
        lp = mm & (fn[:, 2] > 0.55) & (np.abs(fc[:, 0] - ax[0]) < 0.02 * k) & (fc[:, 1] < ax[1] - 0.03 * k) & (fc[:, 1] > ax[1] - 0.13 * k)
        mi[lp] = 3
        heel = mm & (fc[:, 1] > ax[1] + 0.01 * k) & (fc[:, 2] > fl + sole_h)
        mi[heel & (mi == 0)] = 2
    mats = [material(name + "_Upper", tuple(color[:3]) + (1,), rough=0.6), material(name + "_Sole", tuple(sole[:3]) + (1,), rough=0.8),
            material(name + "_Accent", tuple(accent[:3]) + (1,), rough=0.6), material(name + "_Laces", tuple((lace or color)[:3]) + (1,), rough=0.9)]
    ob = make_object(b, b.obj.name + "_" + name, X, F, mats, mi, None, thick=0, subsurf=1)
    o.objs.append(ob)
    o.layer(X, F, 0.0)
    return ob


# ----------------------------------------------------------------------------------------------- accessories
def build_gloves(o, name, color=(0.03, 0.03, 0.035)):
    b = o.b; k = b.k
    P0 = b.whole_co; reg = b.whole_reg
    s, _, _ = arm_param(b, P0)
    f = np.ones(len(P0))
    m = np.isin(reg, ["Hand", "LArm"])
    f[m] = 0.9 - s[m]
    P, F, _ = clip(P0, b.whole_faces, f, {})
    P, F, _ = keep_big(P, F, {}, frac=0.2)
    E = edges_of(F)
    N = vnormals(P, F)
    X = P + N * 0.006 * k
    X = laplace(X, E, 2, taubin=True)
    # a short cuff
    for ll in boundary_loops(F):
        c = X[ll].mean(0)
        sa = arm_param(b, c[None])[0][0]
        side = b.side(c[None])[0]
        A_ = b.J[side + "-shoulder"]; d = b.J[side + "-hand"] - A_; d /= np.linalg.norm(d)
        rings = []
        for t, sc in ((0.004, 1.06), (0.012, 1.06)):
            pts = X[ll].copy() - d * t * k
            pts = c - d * t * k + (pts - (c - d * t * k)) * sc
            rings.append(pts)
        X, F, _, _ = _extend_loop(X, F, ll, None, rings, np.array(["G"] * len(X), dtype=object), "G")
    ob = make_object(b, b.obj.name + "_" + name, X, F, [material(name, tuple(color[:3]) + (1,), rough=0.55)], None, None, thick=0.002, subsurf=1)
    o.objs.append(ob)
    return ob


def _neck_path(o, drop, spread=1.0, gap=0.006, n=72, iters=500):
    """A closed chain path found by a small hanging-chain simulation: a loop slightly longer than the collar
    (by about 2 x drop) is dropped around the neck and settles under gravity on whatever is underneath (body,
    tops, hood), so it rests on the shoulders and upper back and hangs in a natural U at the front."""
    b = o.b; k = b.k
    if o.top is not None:
        X, N, F, nl, _ = o.top
        L = X[nl]
    else:
        zN = b.J["neck"][2] - 0.035 * k
        m = (np.abs(b.co[:, 2] - zN) < 0.006 * k) & np.isin(b.reg, ["Head", "Torso"])
        L = b.co[m]
        L = L[np.hypot(L[:, 0] - L[:, 0].mean(), L[:, 1] - L[:, 1].mean()) < 0.09 * k]
    c = L.mean(0)
    phi = np.arctan2(L[:, 1] - c[1], L[:, 0] - c[0])
    order = np.argsort(phi); phi = phi[order]; L = L[order]
    ph = np.linspace(-np.pi, np.pi, n, endpoint=False)
    rad = np.hypot(L[:, 0] - c[0], L[:, 1] - c[1])
    rr = np.interp(ph, phi, rad, period=2 * np.pi)
    for _ in range(20):
        rr = 0.5 * rr + 0.25 * (np.roll(rr, 1) + np.roll(rr, -1))
    ring = np.stack([np.cos(ph) * rr, np.sin(ph) * rr], 1)
    perim = np.linalg.norm(np.roll(ring, -1, 0) - ring, axis=1).sum()
    length = perim * spread + 2.0 * drop * k + 0.01 * k
    scale = length / perim
    z0 = L[:, 2].max() + 0.03 * k  # start in free air above the shoulders, around the neck
    P = np.c_[c[0] + ring[:, 0] * scale, c[1] + ring[:, 1] * scale, np.full(n, z0)]
    l0 = length / n
    g = 0.0008 * k
    CP, CN, tree = o.col.P, o.col.N, o.col.tree

    def collide(P):
        d, j = tree.query(P, k=4)
        for cc in range(4):
            jj = j[:, cc]
            depth = np.einsum("ij,ij->i", P - CP[jj], CN[jj])
            m = (depth < gap * k) & (depth > -0.02 * k) & (d[:, cc] < 0.03 * k)
            P[m] += (gap * k - depth[m])[:, None] * CN[jj[m]]
        return P

    for it in range(iters):
        P[:, 2] -= g
        P = collide(P)
        for _ in range(40):  # inextensible links (Gauss-Seidel on even then odd segments, closed loop)
            for par in (0, 1):
                i0 = np.arange(par, n - (n % 2 if par else 0), 2)
                i1 = (i0 + 1) % n
                d = P[i1] - P[i0]
                ln = np.linalg.norm(d, axis=1, keepdims=True) + 1e-12
                corr = 0.5 * (ln - l0) / ln * d
                P[i0] += corr; P[i1] -= corr
    P = collide(P)
    for _ in range(3):  # resample finer and smooth for the link builders
        P = np.repeat(P, 2, 0); P[1::2] = 0.5 * (P[1::2] + np.roll(P, -2, 0)[1::2])
        P = 0.5 * P + 0.25 * (np.roll(P, 1, 0) + np.roll(P, -1, 0))
    P = collide(P)
    return P


def _resample_closed(path, step):
    seg = np.linalg.norm(np.roll(path, -1, 0) - path, axis=1)
    cum = np.concatenate([[0], np.cumsum(seg)]); total = cum[-1]
    m = max(8, int(round(total / step)))
    t = np.linspace(0, total, m, endpoint=False)
    P = np.stack([np.interp(t, cum, np.append(path[:, a], path[0, a])) for a in range(3)], 1)
    T = np.roll(P, -1, 0) - np.roll(P, 1, 0); T /= np.linalg.norm(T, axis=1, keepdims=True)
    return P, T


def _surface_normals(o, P):
    d, j = o.col.tree.query(P)
    return o.col.N[j]


def build_chain(o, name, style="cuban", gold=True, droop=0.11, link=0.0085, thick=0.0042, pendant=True,
                color=None, iced=False):
    """Neck chains that rest on the layers under them. style: cuban (flat interlocking twisted ovals), rope (two
    twisted strands), tennis (a row of set stones), box, figaro. pendant: True/'medallion', 'cross' or False."""
    b = o.b; k = b.k
    out = []
    col = color or ((1.0, 0.77, 0.34) if gold else (0.85, 0.86, 0.9))
    if iced:
        col = tuple(0.55 * np.array(col[:3]) + 0.45 * np.array((0.93, 0.97, 1.0)))
    met = material(f"NC_Chain_{name}", tuple(col[:3]) + (1,), rough=0.24)
    met.node_tree.nodes["Principled BSDF"].inputs["Metallic"].default_value = 1.0
    w = link * k  # link width
    path = _neck_path(o, droop, gap=(thick * 0.6 + 0.002))
    parts = []
    if style == "rope":
        P, T = _resample_closed(path, w * 0.12)
        Nn = _surface_normals(o, P)
        U = Nn - np.einsum("ij,ij->i", Nn, T)[:, None] * T; U /= np.linalg.norm(U, axis=1, keepdims=True)
        W_ = np.cross(T, U)
        seg = np.linalg.norm(np.roll(P, -1, 0) - P, axis=1); s_ = np.concatenate([[0], np.cumsum(seg)[:-1]])
        pitch = w * 1.6
        total = s_[-1] + seg[-1]
        turns = max(1, int(round(total / pitch)))
        for strand in range(2):
            ang = 2 * np.pi * turns * s_ / total + np.pi * strand
            Q = P + (np.cos(ang)[:, None] * U + np.sin(ang)[:, None] * W_) * w * 0.24
            Vt, Ft = make_tube(Q, w * 0.27, nseg=8, closed=True)
            parts.append((Vt, Ft, 0))
    elif style == "tennis":
        P, T = _resample_closed(path, w * 1.05)
        Nn = _surface_normals(o, P)
        for i in range(len(P)):
            u = np.cross(Nn[i], T[i]); u /= np.linalg.norm(u) + 1e-9
            ring = [P[i] + 0.45 * w * (np.cos(q) * T[i] + np.sin(q) * u) for q in np.linspace(0, 2 * np.pi, 10, endpoint=False)]
            ring = np.array(ring)
            V = np.vstack([ring - Nn[i] * 0.15 * w, ring + Nn[i] * 0.2 * w, [P[i] + Nn[i] * 0.42 * w]])
            F = [[j, (j + 1) % 10, 10 + (j + 1) % 10, 10 + j] for j in range(10)] + [[10 + j, 10 + (j + 1) % 10, 20] for j in range(10)]
            parts.append((V, F, 0))
    else:  # cuban / box / figaro: interlocking flat links
        P, T = _resample_closed(path, w * 0.5)
        Nn = _surface_normals(o, P)
        nu, nv = 14, 6
        for i in range(len(P)):
            nrm = Nn[i] - (Nn[i] @ T[i]) * T[i]; nrm /= np.linalg.norm(nrm) + 1e-12
            sd = np.cross(T[i], nrm)
            tw = 0.3 if i % 2 == 0 else -0.3  # alternating twist gives the cuban pattern
            ax2 = sd * np.cos(tw) + nrm * np.sin(tw)
            longl = style == "figaro" and i % 4 == 3
            R1 = (0.62 if not longl else 1.0) * w
            R2 = (0.4 if style != "box" else 0.36) * w
            wire = (0.23 if style == "cuban" else 0.13) * w
            pw = 2.2 if style != "box" else 5.0
            base = []
            for a_ in range(nu):
                A = 2 * np.pi * a_ / nu
                ca, sa = np.cos(A), np.sin(A)
                cxy = (np.sign(ca) * np.abs(ca) ** (2 / pw), np.sign(sa) * np.abs(sa) ** (2 / pw))
                cen = P[i] + cxy[0] * T[i] * R1 + cxy[1] * ax2 * R2
                rd = cxy[0] * T[i] * R1 + cxy[1] * ax2 * R2; rd /= np.linalg.norm(rd) + 1e-12
                upv = np.cross(rd, np.cross(T[i], ax2)); upv /= np.linalg.norm(upv) + 1e-12
                for bb in range(nv):
                    B = 2 * np.pi * bb / nv
                    base.append(cen + wire * (np.cos(B) * rd + np.sin(B) * upv * 0.8))
            F = [[a_ * nv + (bb + 1) % nv, ((a_ + 1) % nu) * nv + (bb + 1) % nv, ((a_ + 1) % nu) * nv + bb, a_ * nv + bb]
                 for a_ in range(nu) for bb in range(nv)]
            parts.append((np.array(base), F, 0))
    V, F, mi = merge_parts(parts)
    out.append(make_object(b, b.obj.name + "_" + name, V, F, [met], None, None, thick=0, subsurf=0))
    if pendant:
        out.append(_build_pendant(o, name, path, met, "cross" if pendant == "cross" else "medallion", w))
    o.objs.extend(out)
    return out


def _build_pendant(o, name, path, met, kind, w):
    """An original pendant hanging from the lowest front point: a domed medallion with a raised star and an
    iced rim, or a simple iced cross; each with a bail ring around the chain."""
    b = o.b; k = b.k
    i = int(np.argmin(path[:, 2] + 0.3 * path[:, 1]))
    p = path[i]
    cax = path.mean(0)
    n_ = p - cax; n_[2] = 0; n_ /= np.linalg.norm(n_) + 1e-9  # faces straight out from the chest
    u = np.cross(n_, [0, 0, 1.0]); u /= np.linalg.norm(u); v = np.array([0, 0, 1.0])
    parts = []
    # bail
    bail_c = p - v * 0.006 * k
    ring = [bail_c + 0.0065 * k * (np.cos(q) * v + np.sin(q) * n_) for q in np.linspace(0, 2 * np.pi, 14, endpoint=False)]
    Vt, Ft = make_tube(np.array(ring), 0.0018 * k, nseg=6, closed=True)
    parts.append((Vt, Ft, 0))
    if kind == "cross":
        top = bail_c - v * 0.008 * k
        h, wd, t = 0.05 * k, 0.032 * k, 0.0055 * k
        cen = top - v * h * 0.32
        boxes = [(top - v * h / 2, wd * 0.0 + t, h / 2), (cen, wd / 2, t)]
        for c_, hx, hz in boxes:
            corners = [c_ + sx_ * hx * u + sz_ * hz * v + sy_ * 0.003 * k * n_ for sx_ in (-1, 1) for sz_ in (-1, 1) for sy_ in (-1, 1)]
            Vb = np.array(corners)
            Fb = [[0, 1, 3, 2], [4, 6, 7, 5], [0, 4, 5, 1], [2, 3, 7, 6], [0, 2, 6, 4], [1, 5, 7, 3]]
            parts.append((Vb, Fb, 0))
    else:
        r = 0.026 * k
        cen = bail_c - v * (0.008 * k + r)
        na, nr = 40, 6
        Vp = [cen + n_ * 0.0055 * k]
        for ri in range(1, nr + 1):
            rr = r * ri / nr
            for a_ in range(na):
                A = 2 * np.pi * a_ / na
                star = 1.0
                if ri <= 4:  # raised five-point star in the middle
                    star_r = (0.55 + 0.45 * np.cos(5 * (A - np.pi / 2))) * r * 0.62
                    hgt = 0.0055 * k if rr < star_r else 0.0028 * k
                else:
                    hgt = 0.0035 * k if ri == nr - 1 else 0.0022 * k
                Vp.append(cen + (u * np.cos(A) + v * np.sin(A)) * rr + n_ * hgt)
        Fp = [[0, 1 + a_, 1 + (a_ + 1) % na] for a_ in range(na)]
        for ri in range(nr - 1):
            for a_ in range(na):
                a2 = (a_ + 1) % na
                Fp.append([1 + ri * na + a_, 1 + (ri + 1) * na + a_, 1 + (ri + 1) * na + a2, 1 + ri * na + a2])
        Vp = np.array(Vp)
        fn = np.cross(Vp[Fp[0][1]] - Vp[Fp[0][0]], Vp[Fp[0][2]] - Vp[Fp[0][0]])
        if fn @ n_ < 0:
            Fp = [f[::-1] for f in Fp]
        # back plate so it reads solid from the side
        back = cen - n_ * 0.001 * k
        Vk = [back] + [back + (u * np.cos(A) + v * np.sin(A)) * r for A in np.linspace(0, 2 * np.pi, na, endpoint=False)]
        Fk = [[0, 1 + (a_ + 1) % na, 1 + a_] for a_ in range(na)]
        if np.cross(Vk[Fk[0][1]] - Vk[0], Vk[Fk[0][2]] - Vk[0]) @ n_ > 0:
            Fk = [f[::-1] for f in Fk]
        parts.append((Vp, Fp, 0)); parts.append((np.array(Vk), Fk, 0))
        # rim
        rim = [cen + n_ * 0.0012 * k + (u * np.cos(A) + v * np.sin(A)) * r for A in np.linspace(0, 2 * np.pi, na, endpoint=False)]
        Vt, Ft = make_tube(np.array(rim), 0.0022 * k, nseg=6, closed=True)
        parts.append((Vt, Ft, 0))
    V, F, _ = merge_parts(parts)
    # rest it on the chest: move it out along its facing direction until no vertex is inside a layer
    for _ in range(4):
        d, j = o.col.tree.query(V, k=4)
        depth = np.einsum("ijk,ijk->ij", V[:, None, :] - o.col.P[j], o.col.N[j])
        need = np.where(d < 0.04 * k, 0.002 * k - depth, -1).max()
        if need <= 0:
            break
        V = V + n_ * need
    return make_object(b, b.obj.name + "_" + name + "_Pendant", V, F, [met], None, None, thick=0, subsurf=0)


def build_chain_stack(o, name="Chains", gold=True, iced=True):
    """The reference stack: a thick iced cuban choker plus a longer rope chain with a medallion."""
    out = build_chain(o, name + "_Choker", style="cuban", gold=gold, droop=0.012, link=0.016, thick=0.007, pendant=False, iced=False)
    out += build_chain(o, name + "_Rope", style="rope", gold=gold, droop=0.1, link=0.0075, thick=0.004, pendant=True)
    return out


def _bodydata_eyes(b):
    """Eye centres from NCBodyData.lua (written next to the rig .blend by build_makehuman_rig.py), in Blender axes."""
    import os, re
    path = os.path.join(os.path.dirname(bpy.data.filepath or ""), "NCBodyData.lua")
    if not os.path.exists(path):
        return None
    name = b.obj.name.replace("_Whole", "")
    txt = open(path, encoding="utf-8").read()
    i = txt.find("\t" + name + " = {")
    if i < 0:
        return None
    block = txt[i:txt.find("\n\t},", i)]
    out = []
    for side in ("Left", "Right"):
        m = re.search(r'NC_' + side + r'EyeAttachment", Vector3\.new\(([-\d.]+), ([-\d.]+), ([-\d.]+)\)', block)
        if not m:
            return None
        x, y, z = map(float, m.groups())
        out.append(np.array([-x, z, y]))  # Roblox (x, y, z) -> Blender (-x, z, y)
    return out


def merge_parts(parts):
    """parts: list of (V, F, material_index) -> one (V, F, mat_idx) mesh, so small trims ship as a single object."""
    Vs, Fs, mi, off = [], [], [], 0
    for V, F, m in parts:
        Vs.append(np.asarray(V)); Fs += [[i + off for i in f] for f in F]
        mi += list(m) if hasattr(m, "__len__") else [m] * len(F)
        off += len(V)
    return np.vstack(Vs), Fs, mi


def make_tube(pts, r, nseg=8, closed=False):
    """Round tube along a polyline (parallel-transport frames). r: scalar or per-point radius. Open tubes get
    domed ends. Returns (V, F) for make_object."""
    pts = np.asarray(pts, float)
    r = np.broadcast_to(np.asarray(r, float), (len(pts),))
    if len(pts) > 2:  # drop repeated points (a zero-length step has no direction)
        keep_ = np.r_[True, np.linalg.norm(np.diff(pts, axis=0), axis=1) > 1e-7]
        pts, r = pts[keep_], r[keep_]
    n = len(pts)
    T = np.gradient(pts, axis=0)
    if closed:
        T = np.roll(pts, -1, 0) - np.roll(pts, 1, 0)
    T /= np.linalg.norm(T, axis=1, keepdims=True) + 1e-12
    a = np.array([0, 0, 1.0]) if abs(T[0, 2]) < 0.9 else np.array([1.0, 0, 0])
    U = np.cross(T[0], a); U /= np.linalg.norm(U)
    V = []
    for i in range(n):
        if i:
            U = U - T[i] * np.dot(U, T[i]); U /= np.linalg.norm(U) + 1e-12
        W = np.cross(T[i], U)
        for j in range(nseg):
            t = 2 * np.pi * j / nseg
            V.append(pts[i] + r[i] * (np.cos(t) * U + np.sin(t) * W))
    F = [[i * nseg + j, i * nseg + (j + 1) % nseg, (i + 1) % n * nseg + (j + 1) % nseg, (i + 1) % n * nseg + j]
         for i in range(n if closed else n - 1) for j in range(nseg)]
    if not closed:
        for end, sgn, ring in ((pts[0], -1, 0), (pts[-1], 1, n - 1)):
            ci = len(V); V.append(end + sgn * T[ring] * r[ring] * 0.6)
            for j in range(nseg):
                a_, b_ = ring * nseg + j, ring * nseg + (j + 1) % nseg
                F.append([a_, b_, ci] if sgn < 0 else [b_, a_, ci])
    return np.array(V), F


def head_frame(b):
    k = b.k
    hm = b.reg == "Head"
    top = b.co[hm, 2].max()
    eyes = _bodydata_eyes(b)
    eye_z = eyes[0][2] if eyes else top - 0.118 * k
    hc = b.co[hm & (b.co[:, 2] > eye_z - 0.02 * k)]
    c = np.array([hc[:, 0].mean(), hc[:, 1].mean() + 0.01 * k])
    return hm, top, eye_z, c


def _cap_details(o, name, X, F, c, eye_z, top, zl_back, color, accent, w_open):
    """Six-panel seams (raised piping from the band to the button), stitched eyelets on the side panels,
    and the snapback strap across the back opening."""
    from mathutils.bvhtree import BVHTree
    from mathutils import Vector
    b = o.b; k = b.k
    bvh = BVHTree.FromPolygons([tuple(x) for x in X], [tuple(f) for f in F])
    O = np.array([c[0], c[1], eye_z + 0.005 * k])
    seam_mat = material(name + "_Seam", tuple(np.array(color[:3]) * 0.55) + (1,), rough=0.9)
    hole_mat = material(name + "_Eyelet", (0.01, 0.01, 0.012, 1), rough=0.9)

    def cast(a, phi):
        ph = a - np.pi / 2
        d = np.array([np.cos(ph) * np.cos(phi), np.sin(ph) * np.cos(phi), np.sin(phi)])
        hit, nrm, _, dist = bvh.ray_cast(Vector(O), Vector(d), 0.4 * k)
        if hit is None:
            return None, None
        n_ = np.array(nrm)
        if np.dot(n_, d) < 0:
            n_ = -n_
        return np.array(hit), n_

    out, parts = [], []
    for i in range(6):
        a = np.radians(60 * i)
        if abs(np.angle(np.exp(1j * (a - np.pi)))) < w_open * 1.2:
            # the back seam starts above the opening
            pass
        pts = []
        for phi in np.radians(np.linspace(-10, 88, 56)):
            h, n_ = cast(a, phi)
            if h is None:
                pts = [] if len(pts) < 3 else pts
                continue
            pts.append(h + n_ * (0.0022 * k))
        if len(pts) < 4:
            continue
        pts = np.array(pts)
        zb = eye_z + (0.03 + 0.014 * np.cos(a)) * k + 0.007 * k  # start just above the band (and the brim root)
        pts = pts[pts[:, 2] > zb]
        if len(pts) < 4:
            continue
        for _ in range(3):
            pts[1:-1] = 0.5 * pts[1:-1] + 0.25 * (pts[:-2] + pts[2:])
        Vt, Ft = make_tube(pts, 0.0012 * k, nseg=6)
        parts.append((Vt, Ft, 0))
    # eyelets: one high on each panel
    zt = eye_z + 0.78 * (top - eye_z)
    for i in range(6):
        a = np.radians(30 + 60 * i)
        best = None
        for phi in np.radians(np.linspace(20, 80, 61)):
            h, n_ = cast(a, phi)
            if h is not None and (best is None or abs(h[2] - zt) < abs(best[0][2] - zt)):
                best = (h, n_)
        if best is None or abs(best[0][2] - zt) > 0.012 * k:
            continue
        h, n_ = best
        u = np.cross(n_, [0, 0, 1.0]); u /= np.linalg.norm(u) + 1e-9; v = np.cross(n_, u)
        ring = [h + n_ * 0.0032 * k + 0.0042 * k * (np.cos(t) * u + np.sin(t) * v) for t in np.linspace(0, 2 * np.pi, 12, endpoint=False)]
        Vt, Ft = make_tube(np.array(ring), 0.0011 * k, nseg=5, closed=True)
        Vh = np.vstack([Vt, [h + n_ * 0.0028 * k]]); ci = len(Vh) - 1
        Fh = list(Ft) + [[ci, (j + 1) % 12 * 5, j * 5] for j in range(12)]
        parts.append((Vh, Fh, [0] * len(Ft) + [1] * 12))
    # snapback strap across the bottom of the back opening
    H = b.co[b.reg == "Head"]
    zs = zl_back + 0.013 * k
    band = H[np.abs(H[:, 2] - zs) < 0.012 * k]
    phH = np.arctan2(band[:, 1] - c[1], band[:, 0] - c[0])
    rH = np.hypot(band[:, 0] - c[0], band[:, 1] - c[1])
    angs = np.linspace(np.pi / 2 - w_open * 1.0, np.pi / 2 + w_open * 1.0, 24)  # +Y is the back
    rows = []
    for dz in (-0.0065 * k, 0.0065 * k):
        row = []
        for t in angs:
            m = np.abs(np.angle(np.exp(1j * (phH - t)))) < 0.12
            tuck = np.clip((abs(t - np.pi / 2) / w_open - 0.7) / 0.3, 0, 1)
            rr = (np.median(rH[m]) if m.any() else np.median(rH)) + (0.009 - 0.009 * tuck) * k
            row.append([c[0] + np.cos(t) * rr, c[1] + np.sin(t) * rr, zs + dz])
        rows.append(np.array(row))
    for r_ in rows:
        for _ in range(4):
            r_[1:-1] = 0.5 * r_[1:-1] + 0.25 * (r_[:-2] + r_[2:])
    nS = len(angs); Vs = np.vstack(rows)
    Fs = [[i, nS + i, nS + i + 1, i + 1] for i in range(nS - 1)]
    fc = Vs[np.array(Fs)].mean(1); fn = np.cross(Vs[[f[1] for f in Fs]] - Vs[[f[0] for f in Fs]], Vs[[f[2] for f in Fs]] - Vs[[f[0] for f in Fs]])
    if np.mean(np.einsum("ij,ij->i", fn, fc - np.array([c[0], c[1], zs]))) < 0:
        Fs = [f[::-1] for f in Fs]
    strap_mat = material(name + "_Strap", tuple(np.array((accent or color)[:3]) * 0.8) + (1,), rough=0.6)
    out.append(make_object(b, f"{b.obj.name}_{name}_Strap", Vs, Fs, [strap_mat], None, None, thick=0.004 * k, subsurf=1))
    # snap studs along the strap
    for t in np.linspace(-0.5, 0.5, 5):
        j = int(round((t + 1) / 2 * (nS - 1)))
        p = (rows[0][j] + rows[1][j]) / 2
        n_ = np.array([p[0] - c[0], p[1] - c[1], 0]); n_ /= np.linalg.norm(n_)
        u = np.array([0, 0, 1.0]); v = np.cross(n_, u)
        ring = [p + n_ * 0.0045 * k + 0.0018 * k * (np.cos(q) * u + np.sin(q) * v) for q in np.linspace(0, 2 * np.pi, 8, endpoint=False)]
        Vt, Ft = make_tube(np.array(ring), 0.0009 * k, nseg=4, closed=True)
        parts.append((Vt, Ft, 1))
    Vd, Fd, md = merge_parts(parts)
    out.append(make_object(b, f"{b.obj.name}_{name}_Trim", Vd, Fd, [seam_mat, hole_mat], md, None, thick=0, subsurf=0))
    return out


def build_cap(o, name, kind="fitted", color=(0.04, 0.04, 0.045), accent=None):
    """Fitted cap (snug six-panel crown, structured front, D-shaped front brim, top button) or a cuffed beanie."""
    b = o.b; k = b.k
    hm, top, eye_z, c = head_frame(b)
    P0 = b.co
    Rh = np.hypot(P0[hm, 0] - c[0], P0[hm, 1] - c[1]).max()
    front = np.clip((c[1] - P0[:, 1]) / Rh, -1, 1)  # +1 forehead, -1 back of the head
    if kind == "beanie":
        zl = eye_z + (0.04 + 0.012 * front - 0.0 * np.clip(-front, 0, 1)) * k
    else:
        zl = eye_z + (0.03 + 0.014 * front) * k  # tilted band: high on the forehead, lower at the back
    f = np.ones(len(P0))
    f[hm] = zl[hm] - P0[hm, 2]
    ph0 = np.arctan2(P0[:, 1] - c[1], P0[:, 0] - c[0])
    dback = np.pi - np.abs(np.angle(np.exp(1j * (ph0 + np.pi / 2))))  # 0 at the back of the head
    w_open, h_open = 0.36, 0.042 * k
    if kind != "beanie":  # snapback opening above the strap
        op = 1 - (dback / w_open) ** 2 - ((P0[:, 2] - zl) / h_open) ** 2
        f[hm] = np.maximum(f[hm], op[hm] * 0.05 * k)
    P, F, _ = clip(P0, b.faces, f, {})
    P, F, _ = keep_big(P, F, {}, frac=0.5)
    E = edges_of(F)
    X = P + vnormals(P, F) * 0.008 * k
    for _ in range(5):
        X = laplace(X, E, 5, taubin=True)
        X = o.col.push(X, 0.007 * k)
    up = np.clip((X[:, 2] - eye_z) / (top - eye_z), 0, 1)
    fr = np.clip((c[1] - X[:, 1]) / Rh, 0, 1)
    Nx = vnormals(X, F)
    if kind == "beanie":
        X += Nx * (0.004 * k * up)[:, None]  # a little slouch at the top
        X[:, 2] += 0.006 * k * up ** 3
    else:
        X += Nx * (0.006 * k * fr ** 1.5 * np.sin(np.pi * np.clip(up * 1.1, 0, 1)))[:, None]  # structured front panels
    X = laplace(X, E, 2, taubin=True)
    loops = boundary_loops(F)
    ll = max(loops, key=len)
    ncrown = len(X)
    R = np.array(["Cap"] * len(X), dtype=object)
    extra = []
    if kind == "beanie":  # folded cuff
        base = X[ll].copy(); cc = base.mean(0)
        rings = []
        for dz, sc in ((-0.003, 1.04), (0.028, 1.05), (0.031, 1.0)):
            pts = base.copy(); pts[:, 2] += dz * k
            pts[:, :2] = cc[:2] + (pts[:, :2] - cc[:2]) * sc
            rings.append(pts)
        X, F, R, _ = _extend_loop(X, F, ll, None, rings, R, "Cuff")
    else:
        # sweatband edge: a tiny tuck under so the crown has a finished hem
        base = X[ll].copy(); cc = base.mean(0)
        X, F, R, _ = _extend_loop(X, F, ll, None, [cc + (base - cc) * 0.985 + np.array([0, 0, 0.004 * k])], R, "Band")
        # D-shaped front brim, built as its own piece from the front of the band
        Lp = base
        ph = np.arctan2(Lp[:, 1] - c[1], Lp[:, 0] - c[0])
        ang = np.angle(np.exp(1j * (ph + np.pi / 2)))  # 0 straight ahead
        amax = np.radians(62)
        sel = np.where(np.abs(ang) < amax)[0]
        sel = sel[np.argsort(ang[sel])]
        inner = Lp[sel].copy()
        inner[:, :2] = c[:2] + (inner[:, :2] - c[:2]) * 0.985  # tuck the brim root under the crown edge
        inner[:, 2] -= 0.002 * k
        for _ in range(6):  # even out the root line so the brim edge is clean
            inner[1:-1] = 0.5 * inner[1:-1] + 0.25 * (inner[:-2] + inner[2:])
        u = ang[sel] / amax
        Lb = 0.078 * k
        d2 = inner[:, :2] - c[:2]; d2 /= np.linalg.norm(d2, axis=1, keepdims=True)
        dirs = 0.25 * d2 + 0.75 * np.array([0.0, -1.0]); dirs /= np.linalg.norm(dirs, axis=1, keepdims=True)
        reach = Lb * np.clip(1 - np.abs(u) ** 2.2, 0, 1) ** 0.6
        rows = []
        for t in np.linspace(0, 1, 6):
            row = inner.copy()
            row[:, :2] += dirs * (reach * t)[:, None]
            row[:, 2] -= reach * t * (0.2 + 0.4 * u ** 2) + 0.01 * k * t ** 2 * (1 - u ** 2)  # tilt down, curved sides
            rows.append(row)
        nb_ = len(sel)
        Vb = np.vstack(rows)
        Fb = [[r * nb_ + i, r * nb_ + i + 1, (r + 1) * nb_ + i + 1, (r + 1) * nb_ + i] for r in range(len(rows) - 1) for i in range(nb_ - 1)]
        fcb = Vb[np.array(Fb)].mean(1)
        fnb = np.cross(Vb[[f[1] for f in Fb]] - Vb[[f[0] for f in Fb]], Vb[[f[2] for f in Fb]] - Vb[[f[0] for f in Fb]])
        if fnb[:, 2].mean() < 0:
            Fb = [f[::-1] for f in Fb]
        mb = material(name + "_Brim", tuple((accent or color)[:3]) + (1,), rough=0.8)
        extra.append(make_object(b, b.obj.name + "_" + name + "_Brim", Vb, Fb, [mb], None, None, thick=0.007 * k, subsurf=1))
        # top button
        tp = X[np.argmax(X[:, 2])] + np.array([0, 0, 0.002 * k])
        Vt, Ft = [], []
        for i in range(5):
            for j in range(10):
                th_ = np.pi / 2 * i / 4; ph_ = 2 * np.pi * j / 10
                Vt.append(tp + 0.009 * k * np.array([np.cos(th_) * np.cos(ph_), np.cos(th_) * np.sin(ph_), 0.5 * np.sin(th_)]))
        Ft = [[i * 10 + j, i * 10 + (j + 1) % 10, (i + 1) * 10 + (j + 1) % 10, (i + 1) * 10 + j] for i in range(4) for j in range(10)]
        extra.append(make_object(b, b.obj.name + "_" + name + "_Button", np.array(Vt), Ft, [material(name + "_Main", tuple(color[:3]) + (1,), rough=0.85)], None, None, thick=0, subsurf=1))
        extra.extend(_cap_details(o, name, X, F, c, eye_z, top, zl_back=eye_z + 0.016 * k, color=color, accent=accent,
                                  w_open=w_open))
    mi = np.array([1 if all(R[v] in ("Cuff", "Band") for v in f) else 0 for f in F])
    mats = [material(name + "_Main", tuple(color[:3]) + (1,), rough=0.85), material(name + "_Accent", tuple((accent or color)[:3]) + (1,), rough=0.85)]
    ob = make_object(b, b.obj.name + "_" + name, X, F, mats, mi, None, thick=0.004, subsurf=1)
    o.objs.append(ob)
    o.objs.extend(extra)
    # collider for later layers (hood up): crown only, normals forced to face away from the head
    Xc = X[:ncrown]; Nc = vnormals(X, F)[:ncrown]
    flip = np.einsum("ij,ij->i", Nc, Xc - np.array([c[0], c[1], eye_z])) < 0
    Nc[flip] *= -1
    o.col.add(Xc + Nc * 0.004 * k, Nc); o.col_noarm.add(Xc + Nc * 0.004 * k, Nc)
    return ob


def build_shades(o, name, lens=(0.03, 0.035, 0.035), frame=(0.018, 0.018, 0.02)):
    """Classic thick-rim sunglasses (squared lenses, heavier brow line, keyhole bridge), sized to the head's
    width at the temples and the eye spacing from NCBodyData, pushed clear of the brow, cheeks and nose, with
    straight temple arms back to the ears that hook down behind them."""
    b = o.b; k = b.k
    hm, top, eye_z, c = head_frame(b)
    H = b.co[hm]
    eyes = _bodydata_eyes(b)
    ez = (eyes[0][2] + eyes[1][2]) / 2 if eyes else eye_z
    cx = (eyes[0][0] + eyes[1][0]) / 2 if eyes else c[0]
    zt = ez + 0.012 * k
    band = H[(np.abs(H[:, 2] - zt) < 0.01 * k) & (H[:, 1] < c[1])]
    hw = np.abs(band[:, 0] - cx).max()
    lw, lh, rs, rt, rb, gap = 0.0255, 0.0185, 0.0045, 0.0068, 0.0038, 0.0105
    lc = gap + rs + lw
    half = lc + lw + rs
    sx = float(np.clip((hw + 0.003 * k) / (half * k), 0.88, 1.2)) * k
    sz = k * float(np.sqrt(sx / k))
    n = 56
    th = np.linspace(0, 2 * np.pi, n, endpoint=False)
    cu, sv = np.cos(th), np.sin(th)
    p = np.where(sv > 0, 5.0, 2.7)  # flat brow line on top, rounder lower corners
    u = lw * np.sign(cu) * np.abs(cu) ** (2 / p)
    v = lh * np.sign(sv) * np.abs(sv) ** (2 / p)
    ft = (1 - v / lh) / 2
    u = u * (1 - 0.14 * ft) + 0.0025 * ft  # trapezoid: narrower at the bottom
    v = v + 0.14 * lh * np.clip(u / lw, 0, 1) ** 2 * np.clip(v / lh, 0, 1)  # outer top corner lifts
    # outer rim outline: offset along the 2D outward normal, heavier on top
    du_, dv_ = np.gradient(np.r_[u[-1], u, u[0]])[1:-1], np.gradient(np.r_[v[-1], v, v[0]])[1:-1]
    nu, nv = dv_, -du_
    ln = np.hypot(nu, nv) + 1e-12; nu /= ln; nv /= ln
    if np.mean(nu * u + nv * v) < 0:
        nu, nv = -nu, -nv
    wid = rs + (rt - rs) * np.clip(sv, 0, 1) ** 2 + (rb - rs) * np.clip(-sv, 0, 1) ** 2
    uo, vo = u + nu * wid, v + nv * wid

    def place(U, Vv, side):  # U measured outward from the lens centre
        X = cx + side * (lc + U) * sx
        Z = ez + 0.002 * k + Vv * sz
        r = np.clip(np.abs(X - cx) / (half * sx), 0, 1.2)
        Y = 0.011 * k * r ** 2.4 - (Z - ez) * 0.14
        return np.c_[X, Y, Z]

    rims, lenses = [], []
    for side in (-1, 1):
        A, B = place(u, v, side), place(uo, vo, side)
        rims.append((A, B, side))
        cen = place(np.array([0.0]), np.array([0.0]), side)[0]
        lenses.append((A, cen, side))
    # bridge: an arched bar between the two rims' inner tops
    bx = np.linspace(-1, 1, 14)
    bu = (lc - lw * 0.8) * bx
    bridge = []
    for zz in (lh * 0.52 + 0.0045 * (1 - bx ** 2), np.full_like(bx, lh + rt * 0.85)):  # keyhole arch below, flat brow line on top
        Xb = cx + bu * sx; Zb = ez + 0.002 * k + zz * sz
        Yb = -(Zb - ez) * 0.14 + 0.011 * k * np.clip(np.abs(Xb - cx) / (half * sx), 0, 1) ** 2.4
        bridge.append(np.c_[Xb, Yb, Zb])
    allp = np.vstack([np.vstack([A, B]) for A, B, _ in rims] + bridge)
    # push the whole front forward until every point clears the face (lens/rim clearance 4.5 mm)
    tree2 = cKDTree(H[:, [0, 2]])
    need = -np.inf
    for q in allp:
        idx = tree2.query_ball_point([q[0], q[2]], 0.007 * k)
        if idx:
            need = max(need, q[1] - (H[idx, 1].min() - 0.0045 * k))
    y0 = -need if np.isfinite(need) else c[1] - 0.1 * k
    sh = np.array([0, y0, 0])

    def ring_faces(nn, side, base=0):
        F = [[base + i, base + (i + 1) % nn, base + nn + (i + 1) % nn, base + nn + i] for i in range(nn)]
        return F

    m_f = material(name + "_Frame", tuple(frame[:3]) + (1,), rough=0.42)
    m_l = material(name + "_Lens", tuple(lens[:3]) + (1,), rough=0.05)
    try:
        m_l.node_tree.nodes["Principled BSDF"].inputs["Metallic"].default_value = 0.35
    except Exception:
        pass

    def facing(V, F, want):  # orient faces so their normals point along `want`
        fn = np.cross(V[[f[1] for f in F]] - V[[f[0] for f in F]], V[[f[2] for f in F]] - V[[f[0] for f in F]])
        return F if np.mean(fn @ want) >= 0 else [f[::-1] for f in F]

    fwd = np.array([0, -1.0, 0])
    parts = []
    for A, B, side in rims:
        V = np.vstack([A, B]) + sh
        parts.append((V, facing(V, ring_faces(n, side), fwd), 0))
    Vb = np.vstack(bridge) + sh
    Fb = [[i, i + 1, 14 + i + 1, 14 + i] for i in range(13)]
    parts.append((Vb, facing(Vb, Fb, fwd), 0))
    Vf, Ff, mf = merge_parts(parts)
    out = [make_object(b, b.obj.name + "_" + name, Vf, Ff, [m_f], None, None, thick=0.0055 * k, subsurf=0)]
    bv = out[0].modifiers.new("Bevel", "BEVEL"); bv.width = 0.0011 * k; bv.segments = 2; bv.harden_normals = False
    out[0].modifiers.new("Smooth", "WEIGHTED_NORMAL").keep_sharp = True
    lparts = []
    for A, cen, side in lenses:
        A2 = A + sh + np.array([0, 0.0025 * k, 0])  # lenses sit inside the rim, a little behind its face
        V = np.vstack([A2, cen + sh + np.array([0, 0.0015 * k, 0])])
        F = [[i, (i + 1) % n, n] for i in range(n)]
        lparts.append((V, facing(V, F, fwd), 0))
    Vl, Fl, ml = merge_parts(lparts)
    out.append(make_object(b, b.obj.name + "_" + name + "_Lenses", Vl, Fl, [m_l], None, None, thick=0.0015 * k, subsurf=0))
    # temple arms
    side_pts = H[np.abs(H[:, 2] - zt) < 0.009 * k]
    ear = H[(H[:, 2] > ez - 0.045 * k) & (H[:, 2] < ez + 0.012 * k)]
    for side in (-1, 1):
        x_out = cx + side * (half - 0.0025) * sx
        z0 = ez + 0.002 * k + lh * 0.5 * sz
        y_start = (0.011 * k * 1.0 - (z0 - ez) * 0.14) + y0 + 0.006 * k
        es = ear[(ear[:, 0] - cx) * side > 0]
        top_ear = es[np.argsort(-np.abs(es[:, 0] - cx))[:40]]
        y_ear = top_ear[:, 1].mean()
        z_ear = top_ear[:, 2].max() - 0.001 * k  # the arm rests on the root of the ear
        ys = np.linspace(y_start, y_ear + 0.012 * k, 26)
        path, xm = [], abs(x_out - cx)
        for yy in ys:
            m = (np.abs(side_pts[:, 1] - yy) < 0.006 * k) & ((side_pts[:, 0] - cx) * side > 0)
            if m.any():
                xm = max(xm, np.abs(side_pts[m, 0] - cx).max() + 0.0035 * k)
            path.append([cx + side * xm, yy, z0 + (min(z_ear, z0) - z0) * (yy - y_start) / (ys[-1] - y_start)])
        path = np.array(path)
        # hook down behind the ear
        for t in np.linspace(0.15, 1, 7):
            ang = t * np.radians(55)
            r_ = 0.03 * k
            path = np.vstack([path, [cx + side * (xm - 0.004 * k * t), ys[-1] + r_ * np.sin(ang), path[25, 2] - r_ * (1 - np.cos(ang))]])
        for _ in range(2):
            path[1:-1] = 0.5 * path[1:-1] + 0.25 * (path[:-2] + path[2:])
        T = np.gradient(path, axis=0); T /= np.linalg.norm(T, axis=1, keepdims=True)
        outv = np.array([side, 0, 0.0])
        Up = np.cross(outv, T) * side; Up /= np.linalg.norm(Up, axis=1, keepdims=True)
        Up *= np.sign(Up[:, 2:3] + 1e-9)
        s_ = np.linspace(0, 1, len(path))
        hgt = (0.0105 - 0.004 * s_) * k
        Vt = np.vstack([path + Up * (hgt / 2)[:, None], path - Up * (hgt / 2)[:, None]])
        m_ = len(path)
        Ft = [[i, i + 1, m_ + i + 1, m_ + i] for i in range(m_ - 1)]
        Ft = facing(Vt, Ft, outv)
        out.append(make_object(b, b.obj.name + "_" + name + ("_TempleL" if side > 0 else "_TempleR"), Vt, Ft, [m_f], None, None,
                               thick=0.0038 * k, subsurf=1))
    o.objs.extend(out)
    return out


# ----------------------------------------------------------------------------------------------- skinning
RIGID_HEAD = ("_Cap", "Beanie", "Shades", "Mask", "Durag", "_Hat", "Glasses", "_hat_", "_eye_")  # hats/eyewear ride the head


def skin_to_rig(o):
    """Give every garment the body's bone weights (inverse-distance blend of the nearest body vertices) and an
    Armature modifier first in the stack, so the clothes move with the R15 rig and its animations."""
    b = o.b
    whole, arm = b.obj, b.arm
    me = whole.data
    cw = b.whole_co
    names = [g.name for g in whole.vertex_groups]
    W = np.zeros((len(cw), len(names)), np.float32)
    for v in me.vertices:
        for g in v.groups:
            W[v.index, g.group] = g.weight
    tree = cKDTree(cw)
    armish = np.isin(b.whole_reg, ["Hand", "LArm", "UArm"])
    legish = np.isin(b.whole_reg, ["ULeg", "LLeg", "Foot"])
    wside = np.where(cw[:, 0] > b.cx, "l", "r")
    trees_na = {}
    for sd in ("l", "r"):
        idx_ = np.where(~armish & (b.whole_reg != "X") & ~(legish & (wside != sd)))[0]
        trees_na[sd] = (idx_, cKDTree(cw[idx_]))
    # sleeves only follow their own arm (plus the shoulder cap of the torso), never the hips or the other arm
    trees_arm = {}
    shz = b.J["l-shoulder"][2] - 0.06 * b.k
    for sd in ("l", "r"):
        idx_ = np.where((armish & (wside == sd)) | ((b.whole_reg == "Torso") & (cw[:, 2] > shz) & (wside == sd)))[0]
        trees_arm[sd] = (idx_, cKDTree(cw[idx_]))
    import scipy.sparse as sp
    leg_cols = [names.index(g) for g in names if g in ("LeftUpperLeg", "RightUpperLeg", "LeftLowerLeg", "RightLowerLeg",
                                                         "LeftFoot", "RightFoot", "NC_ToesL", "NC_ToesR")]
    lt = names.index("LowerTorso")
    upper_cut = b.J["l-shoulder"][2] - 0.15 * b.k
    for ob in o.objs:
        P = np.array([v.co[:] for v in ob.data.vertices])
        P = (np.array(ob.matrix_world) @ np.c_[P, np.ones(len(P))].T).T[:, :3]
        P = (np.array(whole.matrix_world.inverted()) @ np.c_[P, np.ones(len(P))].T).T[:, :3]
        d, j = tree.query(P, k=6)
        if "Gloves" not in ob.name:
            flag = np.zeros(len(P), bool)
            if "nc_arm" in ob.data.attributes:
                fl_ = np.zeros(len(P), np.int32); ob.data.attributes["nc_arm"].data.foreach_get("value", fl_); flag = fl_ > 0
            nonarm = ~flag
            gside = np.where(P[:, 0] > b.cx, "l", "r")
            for sd in ("l", "r"):
                mm = nonarm & (gside == sd)
                if mm.any():
                    idx_, tr_ = trees_na[sd]
                    d2, j2 = tr_.query(P[mm], k=6)
                    d[mm] = d2; j[mm] = idx_[j2]
                mm = flag & (gside == sd)
                if mm.any():
                    idx_, tr_ = trees_arm[sd]
                    d2, j2 = tr_.query(P[mm], k=6)
                    d[mm] = d2; j[mm] = idx_[j2]
        w = 1 / np.maximum(d, 1e-4) ** 2
        w /= w.sum(1, keepdims=True)
        Wg = np.einsum("nk,nkg->ng", w, W[j])
        Wg /= np.maximum(Wg.sum(1, keepdims=True), 1e-9)
        if DRAPE_UP != 0 and "Gloves" not in ob.name and P[:, 2].max() > upper_cut and \
                not any(t in ob.name for t in ("_Hood", "_String", "_ZipPull")):
            # cloth hanging clear of the body (under the bust, over the belly) hangs from the body above it:
            # weighted by the skin it merely hovered over, the bust swung down through it when the upper body bent
            gap = d[:, 0]
            dm = nonarm & (gap > DRAPE_D0 * b.k) & (P[:, 2] < b.J["l-shoulder"][2] - 0.1 * b.k)
            if dm.any():
                Q = P[dm].copy(); Q[:, 2] += DRAPE_UP * gap[dm]
                gs_ = gside[dm]; dq = np.zeros((dm.sum(), 6)); jq = np.zeros((dm.sum(), 6), int)
                for sd in ("l", "r"):
                    ms_ = gs_ == sd
                    if ms_.any():
                        idx_, tr_ = trees_na[sd]; d3, j3 = tr_.query(Q[ms_], k=6); dq[ms_] = d3; jq[ms_] = idx_[j3]
                wq = 1 / np.maximum(dq, 1e-4) ** 2; wq /= wq.sum(1, keepdims=True)
                Wq = np.einsum("nk,nkg->ng", wq, W[jq]); Wq /= np.maximum(Wq.sum(1, keepdims=True), 1e-9)
                t_ = np.clip((gap[dm] - DRAPE_D0 * b.k) / (DRAPE_D1 * b.k - DRAPE_D0 * b.k), 0, 1)
                t_ = (t_ * t_ * (3 - 2 * t_))[:, None]
                Wg[dm] = (1 - t_) * Wg[dm] + t_ * Wq
        if "Gloves" not in ob.name:
            # body skin at the hips can carry arm weights where the hand rests on it (MakeHuman weight bleed):
            # garment cloth that is not a sleeve never follows the arm below the shoulder
            arm_cols = [names.index(g) for g in names if g in ("LeftUpperArm", "RightUpperArm", "LeftLowerArm", "RightLowerArm",
                                                               "NC_TwistL", "NC_TwistR", "LeftHand", "RightHand")]
            # (faded in below the armpit: a hard cut at the armpit tore the side seam off the sleeve when arms rise)
            fz = np.clip((b.J["l-shoulder"][2] - ARMCUT_Z0 * b.k - P[:, 2]) / (ARMCUT_W * b.k), 0, 1)
            am = nonarm & (fz > 0)
            if am.any() and arm_cols:
                Wg[np.ix_(am, arm_cols)] *= (1 - fz[am])[:, None]
                rs = Wg[am].sum(1)
                Wg[am] = np.where(rs[:, None] > 1e-6, Wg[am] / np.maximum(rs, 1e-9)[:, None], 0)
                Wg[am & (Wg.sum(1) < 1e-6), lt] = 1.0
            # crotch / seat seam: a garment vertex on the centre line must not snap fully to one leg (the two
            # sides would tear apart when one leg swings). Blend left- and right-side weights across a band.
            skirt = "skirt" in ob.name.lower() and "Leggings" not in ob.name and "Tights" not in ob.name
            band = (0.16 if skirt else CROTCH_BAND) * b.k   # a skirt is one panel: blend across its whole front and back
            bm = nonarm & (np.abs(P[:, 0] - b.cx) < band) & (P[:, 2] > (-1e9 if skirt else b.crotch_z - 0.2 * b.k)) & \
                 (P[:, 2] < b.crotch_z + 0.25 * b.k)
            if bm.any():
                WS = []
                for sd in ("l", "r"):
                    idx_, tr_ = trees_na[sd]
                    d2, j2 = tr_.query(P[bm], k=6)
                    w2 = 1 / np.maximum(d2, 1e-4) ** 2; w2 /= w2.sum(1, keepdims=True)
                    WS.append(np.einsum("nk,nkg->ng", w2, W[idx_[j2]]))
                s_ = np.clip(0.5 + (P[bm, 0] - b.cx) / (2 * band), 0, 1)
                s_ = s_ * s_ * (3 - 2 * s_)
                Wb = s_[:, None] * WS[0] + (1 - s_)[:, None] * WS[1]
                # right on the seam the cloth hangs from the pelvis; leg influence grows away from it
                t_ = np.clip(np.abs(P[bm, 0] - b.cx) / band, 0, 1); f_ = 0.3 + 0.7 * t_ * t_ * (3 - 2 * t_)
                if skirt: f_ = np.maximum(f_, SKIRT_LEG)  # the panel over a thigh goes forward with it (leggings poked through)
                lw = Wb[:, leg_cols].sum(1)
                Wb[:, leg_cols] *= f_[:, None]; Wb[:, lt] += lw * (1 - f_)
                Wb /= np.maximum(Wb.sum(1, keepdims=True), 1e-9)
                gz = np.clip((P[bm, 2] - (b.crotch_z - 0.2 * b.k)) / (0.08 * b.k), 0, 1)[:, None]  # fade down the inseam
                if skirt: gz[:] = 1.0
                Wg[bm] = gz * Wb + (1 - gz) * Wg[bm]
        if "skirt" in ob.name.lower() and "Leggings" not in ob.name and "Tights" not in ob.name and \
                "LeftUpperLeg" in names and "RightUpperLeg" in names:
            # a skirt is a cone off the hips: waistband on the pelvis, everything from the crotch down on the thighs
            # (the body's blended hip weights let a striding thigh push through the panel in front of it)
            zt = P[:, 2].max()
            t = np.clip((zt - P[:, 2]) / max(zt - b.crotch_z, 1e-6), 0, 1); t = t * t * (3 - 2 * t)
            sl = np.clip(0.5 + (P[:, 0] - b.cx) / (0.1 * b.k), 0, 1); sl = sl * sl * (3 - 2 * sl)
            Wr = np.zeros_like(Wg)
            Wr[:, lt] = 1 - t
            Wr[:, names.index("LeftUpperLeg")] = t * sl
            Wr[:, names.index("RightUpperLeg")] = t * (1 - sl)
            # (SKIRT_BACK_BODY > 0: the back follows the seat skin instead. Tried at 1: sitting, the back hung down
            # through the seat like a curtain, worse than the lap ring the thigh weights give)
            db, jb = tree.query(P, k=6)
            wb = 1 / np.maximum(db, 1e-4) ** 2; wb /= wb.sum(1, keepdims=True)
            Wb = np.einsum("nk,nkg->ng", wb, W[jb])
            acols = [names.index(g) for g in names if any(x in g for x in ("Arm", "Hand", "Twist", "Thumb", "Index",
                     "Middle", "Ring", "Pinky"))]
            Wb[:, acols] = 0; Wb[Wb.sum(1) < 1e-6, lt] = 1.0
            Wb /= np.maximum(Wb.sum(1, keepdims=True), 1e-9)
            fr = np.clip((b.yc + 0.03 * b.k - P[:, 1]) / (0.1 * b.k), 0, 1); fr = fr * fr * (3 - 2 * fr)
            fr = 1 - SKIRT_BACK_BODY * (1 - fr)
            Wg[:] = fr[:, None] * Wr + (1 - fr)[:, None] * Wb
        if "Gloves" not in ob.name and "nc_arm" in ob.data.attributes and flag.any():
            # a sleeve never follows the hand or fingers: a turning wrist tore the cuff off the forearm
            hcols = [names.index(g) for g in names if g in ("LeftHand", "RightHand") or g.startswith(
                     ("NC_Thumb", "NC_Index", "NC_Middle", "NC_Ring", "NC_Pinky"))]
            for sd, la in (("l", "LeftLowerArm"), ("r", "RightLowerArm")):
                if la in names and hcols:
                    mm = flag & (np.where(P[:, 0] > b.cx, "l", "r") == sd)
                    hw = Wg[np.ix_(mm, hcols)].sum(1)
                    Wg[np.ix_(mm, hcols)] = 0
                    Wg[mm, names.index(la)] += hw
        if any(t in ob.name for t in RIGID_HEAD):  # caps, beanies, shades, masks move as one piece with the head
            Wg[:] = 0; Wg[:, names.index("Head")] = 1.0
        else:
            if P[:, 2].max() > upper_cut or any(t in ob.name for t in ("_Pocket", "_String", "_Hood", "_ZipPull")):
                # tops never follow the thighs: hand leg influence over to the lower torso
                Wg[:, lt] += Wg[:, leg_cols].sum(1); Wg[:, leg_cols] = 0
            elif WAIST_TORSO > 0 and "Shoes" not in ob.name:
                # a bottom's waistband moves with the pelvis only: seated, the thighs' share dragged the front
                # waist down into the belly and the base layer showed above it
                tz = np.clip((P[:, 2] - (b.J["l-upper-leg"][2] + WAIST_Z0 * b.k)) / (WAIST_RAMP * b.k), 0, 1)
                tz = WAIST_TORSO * tz * tz * (3 - 2 * tz)
                lw = Wg[:, leg_cols].sum(1) * tz
                Wg[:, leg_cols] *= (1 - tz)[:, None]; Wg[:, lt] += lw
            # diffuse the weights over the garment surface so bone transitions are wide and the cloth
            # stretches evenly instead of tearing at a seam line (armpits, crotch, neck)
            Ed = np.array([e.vertices[:] for e in ob.data.edges])
            if len(Ed):
                A = sp.coo_matrix((np.ones(2 * len(Ed)), (np.r_[Ed[:, 0], Ed[:, 1]], np.r_[Ed[:, 1], Ed[:, 0]])),
                                  shape=(len(P), len(P))).tocsr()
                deg = np.asarray(A.sum(1)).ravel(); deg[deg == 0] = 1
                upper = P[:, 2].max() > upper_cut
                its = 0 if "Gloves" in ob.name else (TOP_DIFFUSE if upper or ("skirt" in ob.name.lower() and "Leggings" not in ob.name) else PANTS_DIFFUSE)  # pants: keep the two legs apart
                fz_ = np.ones(len(P), bool)
                if SLEEVE_DIFFUSE is not None and "nc_arm" in ob.data.attributes:
                    # forearm sleeve keeps the body's own elbow transition (smearing it along the sleeve pinched the
                    # elbow into hanging flaps when the arm bends)
                    sa_, _, _ = arm_param(b, P)
                    fz_ = ~(flag & (sa_ > 0.35))
                for it_ in range(its):
                    Wn = 0.5 * Wg + 0.5 * (A @ Wg) / deg[:, None]
                    Wg = np.where(fz_[:, None] | (it_ < (SLEEVE_DIFFUSE or 0)), Wn, Wg)
                Wg /= np.maximum(Wg.sum(1, keepdims=True), 1e-9)
            if ARMPIT_BODY > 0 and upper and "Gloves" not in ob.name and \
                    not any(t in ob.name for t in ("_Hood", "_String", "_ZipPull", "_Pocket")):
                # the armpit: cloth moves exactly like the skin right under it (the skin there bulges out when the
                # arm rises; faded / smoothed cloth weights lagged and the tank showed through a hole)
                fa = np.zeros(len(P))
                for sd in ("l", "r"):
                    Js = b.J[sd + "-shoulder"]
                    dd = np.linalg.norm(P - Js, axis=1)
                    t_ = 1 - np.clip((dd - ARMPIT_R0 * b.k) / ((ARMPIT_R1 - ARMPIT_R0) * b.k), 0, 1)
                    t_ = t_ * t_ * (3 - 2 * t_) * ((P[:, 2] < Js[2] + 0.02 * b.k) | (not ARMPIT_ZCUT))
                    fa = np.maximum(fa, t_)
                fa *= ARMPIT_BODY
                if (fa > 0).any():
                    db, jb = tree.query(P, k=6)
                    wb = 1 / np.maximum(db, 1e-4) ** 2; wb /= wb.sum(1, keepdims=True)
                    Wb = np.einsum("nk,nkg->ng", wb, W[jb])
                    hc_ = [names.index(g) for g in names if g in ("LeftHand", "RightHand") or g.startswith(
                           ("NC_Thumb", "NC_Index", "NC_Middle", "NC_Ring", "NC_Pinky"))]
                    Wb[:, hc_] = 0
                    Wb /= np.maximum(Wb.sum(1, keepdims=True), 1e-9)
                    Wg = (1 - fa)[:, None] * Wg + fa[:, None] * Wb
            if SHOULDER_SHARPEN > 1 and upper and "Gloves" not in ob.name and \
                    not any(t in ob.name for t in ("_Hood", "_String", "_ZipPull", "_Pocket")):
                # blending two far-apart bone rotations shrinks the cloth's offset from the skin (linear blend
                # skinning collapse) and the shoulder skin came through with the arms overhead: sharpen the blend
                fa = np.zeros(len(P))
                for sd in ("l", "r"):
                    dd = np.linalg.norm(P - b.J[sd + "-shoulder"], axis=1)
                    t_ = 1 - np.clip((dd - SHOULDER_R0 * b.k) / ((SHOULDER_R1 - SHOULDER_R0) * b.k), 0, 1)
                    fa = np.maximum(fa, t_ * t_ * (3 - 2 * t_))
                if (fa > 0).any():
                    Ws = Wg ** SHOULDER_SHARPEN; Ws /= np.maximum(Ws.sum(1, keepdims=True), 1e-9)
                    Wg = (1 - fa)[:, None] * Wg + fa[:, None] * Ws
            if HEM_LEG > 0 and upper and "LeftUpperLeg" in names and \
                    not any(t in ob.name for t in ("_Hood", "_String", "_ZipPull", "_Pocket")):
                # a long hem moves with the body right under it (as the trousers there do), not with the waist:
                # a striding or lifted thigh cut straight through a hem that hung from the pelvis
                hz = b.J["l-upper-leg"][2]
                th = HEM_LEG * np.clip((hz + HEM_Z0 * b.k - P[:, 2]) / (HEM_RAMP * b.k), 0, 1)
                th = th * th * (3 - 2 * th)
                if HEM_LEG_BACK < 1:
                    # the back hem hangs from the pelvis: on the thigh weights it swung out behind the seat when sitting
                    bk_ = np.clip((P[:, 1] - b.yc) / (0.12 * b.k), 0, 1); bk_ = bk_ * bk_ * (3 - 2 * bk_)
                    th = th * (1 - (1 - HEM_LEG_BACK) * bk_)
                if "nc_arm" in ob.data.attributes:
                    th = th * ~flag
                if (th > 0).any():
                    db, jb = tree.query(P, k=6)
                    wb = 1 / np.maximum(db, 1e-4) ** 2; wb /= wb.sum(1, keepdims=True)
                    Wb = np.einsum("nk,nkg->ng", wb, W[jb])
                    acols = [names.index(g) for g in names if g in ("LeftUpperArm", "RightUpperArm", "LeftLowerArm",
                             "RightLowerArm", "NC_TwistL", "NC_TwistR", "LeftHand", "RightHand") or g.startswith(
                             ("NC_Thumb", "NC_Index", "NC_Middle", "NC_Ring", "NC_Pinky"))]
                    Wb[:, acols] = 0  # (the hip skin under a resting hand carries hand weights)
                    Wb[Wb.sum(1) < 1e-6, lt] = 1.0
                    Wb /= np.maximum(Wb.sum(1, keepdims=True), 1e-9)
                    Wg = (1 - th)[:, None] * Wg + th[:, None] * Wb
        if os.environ.get("NC_DBG2"):
            lac = [names.index(g) for g in ("LeftLowerArm", "RightLowerArm") if g in names]
            la = Wg[:, lac].sum(1) > 0.5
            ai = np.where(armish)[0]; da, _ = cKDTree(cw[ai]).query(P)
            bad_ = la & (da > 0.06 * b.k)
            print("DBG2", ob.name[-20:], "lowerarm verts", la.sum(), "far from arm", bad_.sum(), "flag", flag[bad_].sum() if "Gloves" not in ob.name else -1, flush=True)
            sa2, rd2, Ra2 = arm_param(b, P); sb, _, Rb = arm_param(b, cw[ai])
            for lo in np.arange(0, 1.0, 0.1):
                mc = flag & (sa2 >= lo) & (sa2 < lo + 0.1); mb = (sb >= lo) & (sb < lo + 0.1)
                if mc.any() and mb.any():
                    print("   s%.1f cloth R p50/p95/max %.3f %.3f %.3f  body R p95/max %.3f %.3f  far %d  far-dirz %.2f" % (lo, np.median(Ra2[mc]), np.percentile(Ra2[mc], 95), Ra2[mc].max(), np.percentile(Rb[mb], 95), Rb[mb].max(), (bad_ & mc).sum(), rd2[bad_ & mc, 2].mean() if (bad_ & mc).any() else 0), flush=True)
            np.save("/tmp/claude-0/render/dbg2_%s.npy" % ob.name[-10:], np.c_[np.where(bad_)[0], P[bad_]])
        if HIP_SHARPEN > 1 and P[:, 2].max() < upper_cut and "skirt" not in ob.name.lower() and \
                "LeftUpperLeg" in names:
            # pants at the hip joints / crotch: a flexed thigh blends two far-apart rotations and the cloth's
            # offset collapsed (the base shorts came through at the crotch when sitting or jumping)
            fa = np.zeros(len(P))
            for sd in ("l", "r"):
                dd = np.linalg.norm(P - b.J[sd + "-upper-leg"], axis=1)
                t_ = 1 - np.clip((dd - HIP_R0 * b.k) / ((HIP_R1 - HIP_R0) * b.k), 0, 1)
                fa = np.maximum(fa, t_ * t_ * (3 - 2 * t_))
            if (fa > 0).any():
                Ws = Wg ** HIP_SHARPEN; Ws /= np.maximum(Ws.sum(1, keepdims=True), 1e-9)
                Wg = (1 - fa)[:, None] * Wg + fa[:, None] * Ws
        for gi, gname in enumerate(names):
            col = Wg[:, gi]
            idx = np.where(col > 0.01)[0]
            if not len(idx):
                continue
            vg = ob.vertex_groups.new(name=gname)
            for i in idx:
                vg.add([int(i)], float(col[i]), "REPLACE")
        mod = ob.modifiers.new("Armature", "ARMATURE")
        mod.object = arm
        while ob.modifiers[0] != mod:
            bpy.context.view_layer.objects.active = ob
            with bpy.context.temp_override(object=ob):
                bpy.ops.object.modifier_move_up(modifier=mod.name)
        # parent to the armature like the body (keeps world placement)
        mw = ob.matrix_world.copy()
        ob.parent = arm
        ob.matrix_world = mw


def build_skirt(o, name, length=0.45, flare=0.25, color=(0.1, 0.1, 0.12), accent=None, pleats=0, thick=0.003):
    """A skirt (or the lower half of a dress) that HANGS from the waist like cloth: a waistband ring, then rings
    whose radius never gets smaller going down (the fabric drapes over the hips and seat, it never follows the
    crotch or the buttock crease), then the flare to the hem. Pleats are knife folds round the hem."""
    b = o.low; k = b.k; J = b.J; P0 = b.co; reg = b.reg
    pel = J["pelvis"][2]
    z_waist = pel + 0.132 * k  # over the top of the base-layer shorts (pelvis + 0.10..0.12k)
    cx, cy = b.cx, b.yc
    na = 120
    phi = np.linspace(-np.pi, np.pi, na, endpoint=False)
    body = np.vstack([P0[_isin(reg, ("Torso", "ULeg"))], o.col_noarm.P])  # the body plus layers already on (leggings)
    body = body[np.hypot(body[:, 0] - cx, body[:, 1] - cy) < 0.3 * k]
    ab = np.arctan2(body[:, 1] - cy, body[:, 0] - cx)
    rb = np.hypot(body[:, 0] - cx, body[:, 1] - cy)
    drop = length * (z_waist - b.floor)
    z_hem = z_waist - drop
    nz = max(12, int(drop / (0.01 * k)))
    zs = np.linspace(z_waist, z_hem, nz)
    ease = 0.009 * k
    rings = []
    rprev = None
    z_flare0 = None
    for zi, z in enumerate(zs):
        sel = np.abs(body[:, 2] - z) < 0.008 * k
        r = np.zeros(na)
        if sel.any():
            idx = np.clip(((ab[sel] + np.pi) / (2 * np.pi) * na).astype(int), 0, na - 1)
            np.maximum.at(r, idx, rb[sel])
        for _ in range(2):  # fill empty bins (the gap between the legs) from the neighbours
            r = np.maximum(r, 0.5 * (np.roll(r, 1) + np.roll(r, -1)) * (r == 0))
        r = r + ease
        rs = r.copy()
        for _ in range(8):  # cloth bridges the dips: smooth, but never inside the body
            rs = np.maximum(r, 0.5 * rs + 0.25 * (np.roll(rs, 1) + np.roll(rs, -1)))
        r = rs
        if rprev is not None:
            r = np.maximum(r, rprev)  # never tucks back in
        rprev = r
        rings.append(r)
    rings = np.array(rings)
    # flare: below the fullest point the skirt opens out toward the hem
    full = int(np.argmax(zs < pel - 0.02 * k))  # flare opens below the seat
    for zi in range(nz):
        t = max(0.0, (zi - full) / max(nz - 1 - full, 1))
        rr = rings[zi] * (1 + flare * t ** 1.3)
        if pleats:
            saw = (phi * pleats / (2 * np.pi)) % 1.0
            rr = rr * (1 + 0.03 * t * (saw - 0.5))
        rings[zi] = rr
    X = np.array([[cx + np.cos(phi) * rings[zi], cy + np.sin(phi) * rings[zi], np.full(na, zs[zi])] for zi in range(nz)])
    X = X.transpose(0, 2, 1).reshape(-1, 3)
    F = [[zi * na + j, zi * na + (j + 1) % na, (zi + 1) * na + (j + 1) % na, (zi + 1) * na + j] for zi in range(nz - 1) for j in range(na)]
    fc = X[np.array(F)].mean(1)
    fn = np.cross(X[[f[1] for f in F]] - X[[f[0] for f in F]], X[[f[2] for f in F]] - X[[f[0] for f in F]])
    if np.mean(np.einsum("ij,ij->i", fn, fc - np.array([cx, cy, fc[:, 2].mean()]))) < 0:
        F = [f[::-1] for f in F]
    X = _hand_clear(o, X, F, radius=0.1, cloth=thick)
    X = o.col_noarm.push(X, 0.004 * k)  # never pressed in under the leggings / shorts below
    mi = np.array([1 if X[f[0], 2] > z_waist - 0.03 * k and X[f[2], 2] > z_waist - 0.031 * k else 0 for f in F])
    acc = accent or color
    mats = [material(name + "_Main", tuple(color[:3]) + (1,)), material(name + "_Band", tuple(acc[:3]) + (1,))]
    ob = make_object(b, b.obj.name + "_" + name, X, F, mats, mi, None, thick=thick)
    o.objs.append(ob)
    o.layer(X, F, thick)
    return ob


# ----------------------------------------------------------------------------------------------- game export
PATTERN_HOOK = None  # set by nc_catalog3d: re-cuts a pattern on the decimated mesh
PANTS_DIFFUSE = 8
UNDERARM_SMOOTH = True
ARMCUT_Z0 = 0.18  # body cloth loses arm weights from this far below the shoulder joint (k) ...
TOP_DIFFUSE = 10
SLEEVE_DIFFUSE = 2  # diffusion steps on the forearm sleeve (None: same as the rest of the top)
WAIST_TORSO = 0.0  # bottoms: share of leg weight moved to the pelvis at the waistband
WAIST_Z0 = 0.06    # ... starting this far above the hip joint (k)
WAIST_RAMP = 0.08  # ... full this much higher (k)
HEM_LEG_BACK = 1.0  # share of HEM_LEG kept at the back of a top's hem
HEM_LEG = 1.0  # share of body weights a top's hem takes near the hip joint (a lifted or striding thigh cut through it)
HEM_Z0 = 0.0   # the blend starts at the hip joint height ...
HEM_RAMP = 0.08  # ... and is full this far below it (k)
ARMCUT_W = 0.14  # ... fading out over this height
SKIRT_LEG = 0.85
SKIRT_BACK_BODY = 0.0
CROTCH_BAND = 0.0  # pants crotch L/R weight blend half-width (k). 0: the cloth follows the body exactly there; any
# blend (it hung the seam from the pelvis) let the base shorts show through the inner thigh when running
GAME_TRIS = {"Chain": 6000, "Gloves": 3000, "default": 7000, "small": 1500}


def limit_influences(ob, n=4):
    """Roblox skins with at most 4 bones a vertex: keep the 4 strongest and renormalise here, so the game bends
    exactly like the preview instead of the importer dropping weights its own way."""
    vgs = ob.vertex_groups
    for g in list(vgs):  # helper groups (decimation guards) are not bones: they must not take a share of the weight
        if g.name.startswith("NC_MatBorder"):
            vgs.remove(g)
    if not len(vgs):
        return
    drop = {}
    for v in ob.data.vertices:
        gs = sorted(((g.weight, g.group) for g in v.groups if g.weight > 0), reverse=True)
        keep = gs[:n]; tot = sum(w for w, _ in keep)
        for w, gi in gs[n:]:
            drop.setdefault(gi, []).append(v.index)
        for g in v.groups:
            if g.weight <= 0:
                drop.setdefault(g.group, []).append(v.index)
        if tot > 0:
            for w, gi in keep:
                vgs[gi].add([v.index], w / tot, "REPLACE")
    for gi, idx in drop.items():
        vgs[gi].remove(idx)


def game_ready(ob):
    """Roblox-friendly copy settings: no subdivision, decimated to a tri budget (the Solidify still adds the
    inside of the cloth). Call before an FBX export with use_mesh_modifiers=True."""
    tris = sum(len(p.vertices) - 2 for p in ob.data.polygons)
    key = next((k for k in GAME_TRIS if k in ob.name), None)
    budget = GAME_TRIS.get(key) if key else (GAME_TRIS["small"] if tris < 4000 else GAME_TRIS["default"])
    for m in list(ob.modifiers):
        if m.type == "SUBSURF":
            ob.modifiers.remove(m)
    # patterned garments (stripes / plaid / chest band): decimate the uncut mesh, then cut the pattern again
    if "nc_pattern" in ob and PATTERN_HOOK is not None and tris > budget:
        kind = __import__("json").loads(ob["nc_pattern"]).get("kind")
        if PATTERN_HOOK(ob, int(budget * {"plaid": 0.3, "stripes": 0.5, "camo": 0.35}.get(kind, 0.8))):
            for m in list(ob.modifiers):
                if m.type == "SUBSURF":
                    ob.modifiers.remove(m)
            return ob  # the pattern cut is the final mesh: no second decimation across the new colour edges
    # other colour borders (ribs, zips): the decimation must not collapse across them, or edges turn into shards
    me = ob.data
    used = {p.material_index for p in me.polygons}
    vg = None
    if len(used) > 1:
        vm = collections.defaultdict(set)
        for p in me.polygons:
            for v in p.vertices:
                vm[v].add(p.material_index)
        border = [v for v, ms in vm.items() if len(ms) > 1]
        if border:
            vg = ob.vertex_groups.get("NC_MatBorder") or ob.vertex_groups.new(name="NC_MatBorder")
            vg.add(border, 1.0, "REPLACE")
    if tris > budget:
        d = ob.modifiers.new("GameDecimate", "DECIMATE")
        d.ratio = budget / tris
        if vg is not None:
            d.vertex_group = vg.name; d.invert_vertex_group = True; d.vertex_group_factor = 1000.0
        # keep the armature first, decimate before the thickness
        while ob.modifiers.find(d.name) > 1:
            with bpy.context.temp_override(object=ob):
                bpy.ops.object.modifier_move_up(modifier=d.name)
    return ob


# ----------------------------------------------------------------------------------------------- shoes (v2)
# Original, logo-free shoe styles. The construction follows real sneakers: a separate sole unit (cupsole,
# vulcanised or wedge), an upper lofted around the foot with a cut collar and throat, a padded collar roll,
# a tongue, eyelets and criss-cross laces, and overlay panels coloured on the upper.
SHOE_STYLES = {
    # basketball high-top: tall padded collar, cupsole, toe cap, heel counter and eyestay overlays
    "court_high": dict(collar=0.075, sole=0.026, kind="cup", laces=7, toe=True, heel=True, eyestay=True, tongue_up=0.02),
    # court low-top: same cupsole and overlays as the high-top, collar just under the ankle bone
    "court_low": dict(collar=0.014, sole=0.026, kind="cup", laces=6, toe=True, heel=True, eyestay=True, tongue_up=0.016),
    # retro basketball mid: thick cupsole with a cushion window, cracked-texture overlays on toe and heel
    "retro_bball": dict(collar=0.048, sole=0.034, kind="cup", laces=6, toe=True, heel=True, eyestay=True, crackle=True,
                        window=True, tongue_up=0.032),
    # skate low-top: flat vulcanised sole with a foxing line, toe cap, our own wave side stripe
    "skate_low": dict(collar=0.012, sole=0.022, kind="vulc", laces=6, toe=True, heel=True, stripe=True, tongue_up=0.012),
    # slip-on: low vulcanised, elastic side gores, no laces
    "slip_on": dict(collar=0.002, sole=0.022, kind="vulc", laces=0, gores=True, tongue_up=0.0),
    # canvas high-top: rubber toe cap and foxing stripe on a vulcanised sole, metal eyelets
    "canvas_high": dict(collar=0.085, sole=0.024, kind="vulc", laces=8, rubber_toe=True, tongue_up=0.012),
    # platform combat boot: tall laced shaft to mid-calf on a thick lug platform, toe cap and heel counter
    "combat_platform": dict(collar=0.02, shaft=0.17, sole=0.055, kind="cup", laces=11, toe=True, tongue_up=0.0),
    # knee-high canvas sneaker: canvas high-top whose laced shaft runs up to just under the knee
    "canvas_knee": dict(collar=0.02, shaft=0.36, sole=0.026, kind="vulc", laces=20, rubber_toe=True, tongue_up=0.008),
    # canvas low-top: vulcanised sole, rubber toe cap and foxing stripe, metal eyelets
    "canvas_low": dict(collar=0.012, sole=0.024, kind="vulc", laces=6, rubber_toe=True, tongue_up=0.012),
    # retro runner: wedge midsole, slimmer toe, mudguard and heel overlays
    "runner_retro": dict(collar=0.008, sole=0.03, kind="wedge", laces=6, heel=True, mudguard=True, pointy=True,
                         tongue_up=0.014),
}


def _crackle(P, scale, seed=7):
    """0..1 'crack line' strength from a Voronoi pattern (1 on the cracks)."""
    rng = np.random.default_rng(seed)
    lo, hi = P.min(0) - scale, P.max(0) + scale
    n = int(np.prod((hi - lo) / scale)) + 8
    S = lo + rng.random((min(n, 20000), 3)) * (hi - lo)
    d, _ = cKDTree(S).query(P, k=2)
    gap = (d[:, 1] - d[:, 0]) / scale
    return np.clip(1 - gap / 0.16, 0, 1)


def build_shoe(o, name, style="court_high", color=(0.95, 0.95, 0.94), accent=None, sole=(0.96, 0.96, 0.94),
               outsole=None, lace=None, lining=None, nu=60, na=56):
    S = SHOE_STYLES[style]
    b = o.low; k = b.k; J = b.J
    fl = b.floor
    acc = accent or color
    outsole = outsole or tuple(np.array(sole[:3]) * 0.8)
    lace = lace or color
    lining = lining or (tuple(color[:3]) if S.get("shaft") else tuple(np.array(acc[:3]) * 0.85))
    up_parts, up_cols, sole_parts, lace_parts = [], [], [], []
    for side in ("l", "r"):
        ank = J[side + "-ankle"]
        m = (b.reg == "Foot") & (b.side(b.co) == side)
        m |= (b.reg == "LLeg") & (b.side(b.co) == side) & (b.co[:, 2] < ank[2] + 0.02 * k)
        Pf = b.co[m]
        legm = (b.reg == "LLeg") & (b.side(b.co) == side) & (b.co[:, 2] < ank[2] + max(S["collar"], 0) * k + 0.03 * k)
        Pl = b.co[legm]
        xy = Pf[:, :2] - Pf[:, :2].mean(0)
        _, _, vt = np.linalg.svd(xy, full_matrices=False)
        d = vt[0] if vt[0][1] < 0 else -vt[0]
        lat = np.array([-d[1], d[0]])
        if (lat @ np.array([1.0, 0])) * (1 if side == "l" else -1) < 0:
            lat = -lat  # +lat always points to the outside of the foot
        c0 = Pf[:, :2].mean(0)
        u = (Pf[:, :2] - c0) @ d
        v = (Pf[:, :2] - c0) @ lat
        u0, u1 = u.min() - 0.012 * k, u.max() + (0.024 if S.get("pointy") else 0.018) * k
        us = np.linspace(u0, u1, nu)
        t = (us - u0) / (u1 - u0)  # 0 heel .. 1 toe
        W, T, V0, Zm = np.zeros(nu), np.zeros(nu), np.zeros(nu), np.full(nu, 1e9)
        for i, uu in enumerate(us):
            sl = np.abs(u - uu) < 0.02 * k
            if sl.sum() < 3:
                W[i] = np.nan; continue
            vv = v[sl]; zz = Pf[sl, 2]
            W[i] = (vv.max() - vv.min()) / 2 + 0.012 * k
            V0[i] = (vv.max() + vv.min()) / 2
            T[i] = zz.max() + 0.012 * k
            Zm[i] = zz.min()
        ok = ~np.isnan(W)
        Zm = np.where(Zm > 1e8, np.inf, Zm)
        W = np.interp(us, us[ok], W[ok]); T = np.interp(us, us[ok], T[ok]); V0 = np.interp(us, us[ok], V0[ok])
        for _ in range(4):
            for A in (W, T, V0):
                A[1:-1] = 0.25 * A[:-2] + 0.5 * A[1:-1] + 0.25 * A[2:]
        Wfoot, Tfoot = W.copy(), T.copy()   # foot half-width / top incl. 12 mm margin (never cut into the toes)
        # leg clearance for high collars
        if len(Pl):
            ul = (Pl[:, :2] - c0) @ d; vl = (Pl[:, :2] - c0) @ lat
            for i, uu in enumerate(us):
                sl = np.abs(ul - uu) < 0.015 * k
                if sl.sum() > 3:
                    W[i] = max(W[i], (vl[sl].max() - vl[sl].min()) / 2 + 0.01 * k)
        tq = 2 * t - 1
        pw = 4.0 if S.get("pointy") else 5.0
        rnd = (1 - np.abs(tq) ** pw) ** (1 / pw)
        W = W * np.maximum(np.where(tq > 0, rnd ** (1.0 if S.get("pointy") else 0.75), rnd ** 0.5), 0.5) + 0.002 * k
        W = np.maximum(W, Wfoot - 0.004 * k)
        # sole heights
        kind = S["kind"]
        prof = {"cup": 1.15 - 0.3 * t, "vulc": np.ones(nu), "wedge": 1.55 - 1.0 * t}[kind]
        spring = 0.016 * k * np.clip((t - 0.7) / 0.3, 0, 1) ** 2
        # toe spring only where the toes leave room: the sole bottom never rises above the lowest skin in that slice
        zmin_s = np.minimum.reduce([np.roll(Zm, r) for r in (-2, -1, 0, 1, 2)])
        z_bot = np.minimum(fl + spring, zmin_s - 0.004 * k) - 0.002 * k
        z_bot = np.minimum(z_bot, fl - 0.002 * k + spring)
        z_top = z_bot + S["sole"] * k * prof
        Ws = W * (1.05 if kind != "vulc" else 1.03) + 0.003 * k
        z_col_base = ank[2] + S["collar"] * k

        def P2(i, off):  # plan point of slice i at lateral offset off
            q = c0 + d * us[i] + lat * (V0[i] + off)
            return q

        # ---- sole unit: rings around the footprint outline, lofted bottom -> top
        idx_l = list(range(nu)); idx_r = list(range(nu - 1, -1, -1))
        outline = [(i, +1) for i in idx_l] + [(i, -1) for i in idx_r[1:-1]]
        no = len(outline)
        levels = [(-0.004, 0.0), (0.0, 0.0), (0.0, 0.42 if kind != "vulc" else 0.3), (0.0, 1.0), (-0.004, 1.0)]
        Vs = []
        for inset, hf in levels:
            for (i, sg) in outline:
                q = P2(i, sg * max(Ws[i] + inset * k, 0.001 * k))
                zz = z_bot[i] + (z_top[i] - z_bot[i]) * hf
                Vs.append([q[0], q[1], zz])
        Vs = np.array(Vs)
        Fs, ms = [], []
        for L in range(len(levels) - 1):
            for j in range(no):
                j2 = (j + 1) % no
                Fs.append([L * no + j, L * no + j2, (L + 1) * no + j2, (L + 1) * no + j])
                ms.append(0 if L <= 1 else 1)  # outsole band below the split, midsole above
        cb = len(Vs); Vs = np.vstack([Vs, Vs[:no].mean(0), Vs[-no:].mean(0)])
        for j in range(no):
            j2 = (j + 1) % no
            Fs.append([j2, j, cb]); ms.append(0)
            Fs.append([(len(levels) - 1) * no + j, (len(levels) - 1) * no + j2, cb + 1]); ms.append(1)
        fc = Vs[np.array([f[:3] for f in Fs])].mean(1)
        cen = Vs.mean(0)
        fn = np.cross(Vs[[f[1] for f in Fs]] - Vs[[f[0] for f in Fs]], Vs[[f[2] for f in Fs]] - Vs[[f[0] for f in Fs]])
        if np.mean(np.einsum("ij,ij->i", fn, fc - cen)) < 0:
            Fs = [f[::-1] for f in Fs]
        ms = np.array(ms)
        if kind == "vulc":  # thin foxing line round the sidewall
            hf_f = (fc[:, 2] - np.interp(0, [0], [0]))
            for fi, f in enumerate(Fs):
                pass
        if S.get("window"):  # cushion window on the outer heel
            for fi, f in enumerate(Fs):
                pc = Vs[f].mean(0)
                tt = ((pc[:2] - c0) @ d - u0) / (u1 - u0)
                outer = ((pc[:2] - c0) @ lat) > 0
                if outer and 0.1 < tt < 0.32 and ms[fi] == 1 and len(f) == 4:
                    ms[fi] = 2
        sole_parts.append((Vs, Fs, ms))

        # ---- upper: superellipse sections sitting on the sole, cut at the collar and throat
        Vu, prm = [], []
        a = np.linspace(0, 2 * np.pi, na, endpoint=False)
        T2 = np.maximum(T, z_top + 0.03 * k)
        heelzone = t < 0.42
        if not S.get("shaft"):  # a boot shaft takes over above the ankle
            T2 = np.where(heelzone, np.maximum(T2, z_col_base + 0.03 * k), T2)
        for i in range(nu):
            zb = z_top[i] - 0.004 * k
            hz = (T2[i] - zb) / 2
            # ends round off in height so heel and toe close smoothly
            hz *= max(0.35 + 0.65 * rnd[i] ** 0.5, 0.75)
            hz = max(hz, (Tfoot[i] - 0.004 * k - zb) / 2)
            zc = zb + hz
            for aj in a:
                ca, sa = np.cos(aj), np.sin(aj)
                p = 2.5 if sa > 0 else 8.0
                vv = W[i] * np.sign(ca) * np.abs(ca) ** (2 / p)
                zz = zc + hz * np.sign(sa) * np.abs(sa) ** (2 / p)
                q = P2(i, vv)
                Vu.append([q[0], q[1], zz])
                prm.append([t[i], ca, (zz - zb) / max(T2[i] - zb, 1e-6), vv])
        Vu = np.array(Vu); prm = np.array(prm)
        Fu = [[i * na + j, i * na + (j + 1) % na, (i + 1) * na + (j + 1) % na, (i + 1) * na + j] for i in range(nu - 1) for j in range(na)]
        # domed ends: a few shrinking rings past the last section, then a tiny cap (no pinch at toe or heel)
        for i, rev, sgn in ((0, True, -1), (nu - 1, False, 1)):
            ring = Vu[i * na:(i + 1) * na]; cc = ring.mean(0); prev = list(range(i * na, (i + 1) * na))
            for step, sc in enumerate((0.82, 0.55, 0.25)):
                nr = cc + (ring - cc) * sc
                nr[:, :2] += np.r_[d] * sgn * 0.016 * k * np.sqrt(1 - sc ** 2) / 0.97
                nr[:, 2] = cc[2] + (ring[:, 2] - cc[2]) * sc + (1 - sc) * 0.002 * k
                base = len(Vu); Vu = np.vstack([Vu, nr]); prm = np.vstack([prm, prm[prev]])
                cur = list(range(base, base + na))
                for j in range(na):
                    q = [prev[j], prev[(j + 1) % na], cur[(j + 1) % na], cur[j]]
                    Fu.append(q[::-1] if rev else q)
                prev = cur
            ci = len(Vu); Vu = np.vstack([Vu, Vu[prev].mean(0)]); prm = np.vstack([prm, prm[prev[0]]])
            for j in range(na):
                tri = [prev[j], prev[(j + 1) % na], ci]
                Fu.append(tri[::-1] if rev else tri)
        # collar + throat opening
        tt, latoff, zz = prm[:, 0], prm[:, 3], Vu[:, 2]
        t_th0, t_th1 = (0.4, 0.72) if S["laces"] else (0.4, 0.55)
        zcol = z_col_base + 0.012 * k * np.clip(1 - tt / 0.42, 0, 1) ** 1.5  # heel tab a little higher
        g1 = np.minimum(zz - zcol, t_th0 + 0.02 - tt)
        wth = (0.02 if S["laces"] else 0.03) * k * (1 - 0.35 * np.clip((tt - t_th0) / (t_th1 - t_th0), 0, 1))
        topside = prm[:, 2] > 0.55
        g2 = np.minimum.reduce([wth - np.abs(latoff), tt - t_th0 + 0.04, t_th1 - tt, np.where(topside, 1.0, -1.0) * 0.05 * k])
        g = np.maximum(g1, g2)
        if S.get("shaft"):  # boots: the shaft makes the heel and ankle, the shoe upper keeps the vamp and toe
            g = np.maximum(g, 0.31 - tt)
        Pq, Fq, A = clip(Vu, Fu, g, {"prm": prm})
        Pq, Fq, A = keep_big(Pq, Fq, A, frac=0.5)
        prq = A["prm"]
        E = edges_of(Fq)
        Pq = laplace(Pq, E, 2, taubin=True)
        # clear the foot with a SMOOTH push: the raw push follows every toe and crumples the toe box, so the
        # push offsets are blurred over the shoe surface and re-applied a few rounds (stays clear, stays smooth)
        for _ in range(int(os.environ.get('NC_SHOEPUSH', 4))):
            Dp = o.col.push(Pq, 0.006 * k) - Pq
            mag = np.linalg.norm(Dp, axis=1)
            if mag.max() < 1e-5 * k:
                break
            Dp *= np.clip((0.6 - prq[:, 0]) / 0.15, 0, 1)[:, None]   # toe box is sized from the foot itself; push only the heel/collar
            Ds = laplace(Dp, E, 12, lam=0.6)
            ms_ = np.linalg.norm(Ds, axis=1)
            # keep the blurred direction but never less than the blurred peak around it
            mag = np.linalg.norm(Dp, axis=1)
            Pq = Pq + Ds * (np.maximum(ms_, laplace(mag[:, None], E, 6, lam=0.6)[:, 0] * 1.2) / np.maximum(ms_, 1e-9))[:, None]
        Pq = laplace(Pq, E, 2, taubin=True)
        # overlay panels: the upper is split along each panel outline (exact iso-lines, so edges are crisp)
        # and the panels sit a hair proud of the base like stitched leather overlays
        tt, ca, hn = prq[:, 0], prq[:, 1], prq[:, 2]
        BIG = 1.0
        fz = np.full(len(Pq), BIG)
        if S.get("toe"):
            fz = np.minimum(fz, np.maximum(0.8 - tt, hn - 0.85))
        if S.get("heel"):
            fz = np.minimum(fz, np.maximum(tt - (0.13 + 0.13 * (1 - hn) ** 1.5), hn - 0.78))
        if S.get("eyestay"):
            fz = np.minimum(fz, np.maximum.reduce([0.36 - tt, tt - 0.76, 0.62 - hn]))
        if S.get("mudguard"):
            fz = np.minimum(fz, np.maximum(hn - 0.3, 0.5 - tt))
        if S.get("stripe"):  # our own wave: rises from the toe box toward the heel collar
            hc = 0.22 + 0.5 * smoothstep(0.62, 0.12, tt) + 0.05 * np.sin(tt * 9.0)
            fz = np.minimum(fz, np.maximum.reduce([np.abs(hn - hc) - 0.07, 0.12 - tt, tt - 0.66, 0.35 - np.abs(ca)]))
        if S.get("gores"):
            fz = np.minimum(fz, np.maximum.reduce([np.abs(tt - 0.5) - 0.04, 0.5 - hn, 0.3 - np.abs(ca)]))
        fr = np.full(len(Pq), BIG)  # rubber (sole-coloured) parts of the upper
        if S.get("rubber_toe"):
            fr = np.minimum(np.maximum(0.86 - tt, hn - 0.55), hn - 0.07)
        pieces = []
        A0 = {"prm": prq}
        if (fz < 0).any():
            Po, Fo, Ao = clip(Pq, Fq, fz, A0)
            Pb, Fb, Ab = clip(Pq, Fq, -fz, A0)
            if len(Fo):
                Po = Po + vnormals(Po, Fo) * 0.0015 * k
                pieces.append((Po, Fo, Ao["prm"], "acc"))
        else:
            Pb, Fb, Ab = Pq, Fq, A0
        if (fr < 0).any():
            Pr_, Fr_, Ar = clip(Pb, Fb, fr, {"prm": Ab["prm"]})
            Pb, Fb, Ab = clip(Pb, Fb, -fr, {"prm": Ab["prm"]})
            if len(Fr_):
                pieces.append((Pr_, Fr_, Ar["prm"], "rubber"))
        pieces.insert(0, (Pb, Fb, Ab["prm"], "base"))
        for Pp, Fp, prp, kind_ in pieces:
            if kind_ == "base":
                col = np.tile(np.array(color[:3], float), (len(Pp), 1)); mi_ = 0
            elif kind_ == "acc":
                col = np.tile(np.array(acc[:3], float), (len(Pp), 1)); mi_ = 2
                if S.get("crackle"):
                    cr = _crackle(Pp, 0.016 * k)
                    base_c = np.array([0.74, 0.74, 0.72]) if np.mean(color[:3]) > 0.4 else np.array([0.25, 0.25, 0.27])
                    zt_, zh_ = prp[:, 0], prp[:, 2]
                    cz = (zt_ > 0.75) | (zt_ < 0.3)
                    col[cz] = base_c * (1 - 0.8 * cr[cz, None])
            else:
                col = np.tile(np.array(sole[:3], float), (len(Pp), 1)); mi_ = 3
            up_parts.append((Pp, Fp, mi_)); up_cols.append(col)
        Pq_all = Pq
        # ---- padded collar roll along the opening edge
        loops = boundary_loops(Fq)
        if loops and not S.get("shaft"):  # a boot shaft covers the collar instead
            lp = max(loops, key=len)
            Lp = Pq[lp]
            ltt = prq[lp, 0]
            rr = np.where(ltt < t_th0, 0.0055 * k, 0.003 * k)
            inward = np.array([*(c0 + d * (u0 + (u1 - u0) * 0.3) + lat * V0[nu // 3]), 0.0])
            Lp2 = Lp.copy()
            for _ in range(6):
                Lp2 = 0.5 * Lp2 + 0.25 * (np.roll(Lp2, 1, 0) + np.roll(Lp2, -1, 0))
            for _ in range(6):
                rr = 0.5 * rr + 0.25 * (np.roll(rr, 1) + np.roll(rr, -1))
            Vt, Ft = make_tube(Lp2, rr, nseg=8, closed=True)
            up_parts.append((Vt, Ft, 1)); up_cols.append(np.tile(np.array(lining[:3]), (len(Vt), 1)))

        # ---- tongue (sits under the throat edges, sticks up above the collar at the front)
        if S["laces"] or S.get("tongue_up", 0) > 0:
            rows = []
            tts = np.linspace(t_th1 + 0.02, t_th0 - 0.03, 12)
            for ti, t_ in enumerate(tts):
                i = int(np.clip(round(t_ * (nu - 1)), 0, nu - 1))
                zb = z_top[i] - 0.004 * k
                hz = (T2[i] - zb) / 2 * (0.35 + 0.65 * rnd[i] ** 0.5)
                ztop = zb + 2 * hz - 0.003 * k
                if t_ < t_th0 + 0.02 and not S.get("shaft"):
                    ztop = max(ztop, z_col_base + (S.get("tongue_up", 0.012) * k) * (t_th0 + 0.02 - t_) / 0.05)
                row = []
                for x_ in np.linspace(-1, 1, 9):
                    ww = (wth.max() * 1.35) * x_
                    q = P2(i, ww)
                    row.append([q[0], q[1], ztop - 0.006 * k * x_ ** 2])
                rows.append(row)
            Vt = np.array(rows).reshape(-1, 3)
            Ft = [[r * 9 + c, r * 9 + c + 1, (r + 1) * 9 + c + 1, (r + 1) * 9 + c] for r in range(len(tts) - 1) for c in range(8)]
            fn = np.cross(Vt[Ft[0][1]] - Vt[Ft[0][0]], Vt[Ft[0][2]] - Vt[Ft[0][0]])
            if fn[2] < 0:
                Ft = [f[::-1] for f in Ft]
            # give it thickness by doubling (thin padded tongue)
            Vb_ = Vt - np.array([0, 0, 0.004 * k]); nT = len(Vt)
            Ft2 = Ft + [[x + nT for x in f[::-1]] for f in Ft]
            up_parts.append((np.vstack([Vt, Vb_]), Ft2, 0)); up_cols.append(np.tile(np.array(color[:3]), (2 * nT, 1)))

        # ---- eyelets + laces
        if S["laces"]:
            ne = S["laces"]
            te = np.linspace(t_th0 + 0.03, t_th1 - 0.02, ne)
            pts = {}
            for sg in (-1, 1):
                pts[sg] = []
                for t_ in te:
                    i = int(np.clip(round(t_ * (nu - 1)), 0, nu - 1))
                    zb = z_top[i] - 0.004 * k
                    hz = (T2[i] - zb) / 2 * (0.35 + 0.65 * rnd[i] ** 0.5)
                    wt = (0.02 * k) * (1 - 0.35 * np.clip((t_ - t_th0) / (t_th1 - t_th0), 0, 1)) + 0.006 * k
                    # surface height at that lateral offset
                    ca_ = wt / max(W[i], 1e-6)
                    sa_ = np.sqrt(max(0.0, 1 - ca_ ** 2.5)) if ca_ < 1 else 0
                    zt_ = zb + hz + hz * sa_ ** (2 / 2.5)
                    q = P2(i, sg * wt)
                    pts[sg].append(np.array([q[0], q[1], zt_ + 0.002 * k]))
            for sg in (-1, 1):
                for p_ in pts[sg]:
                    nrm = np.array([0, 0, 1.0])
                    uu_ = np.r_[d, 0]; vv_ = np.cross(nrm, uu_)
                    ring = [p_ + 0.0032 * k * (np.cos(q) * uu_ + np.sin(q) * vv_) for q in np.linspace(0, 2 * np.pi, 8, endpoint=False)]
                    Vt, Ft = make_tube(np.array(ring), 0.0012 * k, nseg=4, closed=True)
                    lace_parts.append((Vt, Ft, 1))
            for i in range(ne - 1):
                for sg in (-1, 1):
                    p0, p1 = pts[sg][i], pts[-sg][i + 1]
                    mid = 0.5 * (p0 + p1) + np.array([0, 0, 0.004 * k])
                    path = np.array([p0, 0.5 * (p0 + mid), mid, 0.5 * (mid + p1), p1])
                    Vt, Ft = make_tube(path, 0.0021 * k, nseg=6)
                    lace_parts.append((Vt, Ft, 0))
            # top bar + short bow loops (boots: the laces carry on up the shaft instead)
            p0, p1 = pts[-1][0], pts[1][0]
            if S.get("shaft"):
                p0 = p1 = None
            if p0 is not None:
                mid = 0.5 * (p0 + p1) + np.array([0, 0, 0.006 * k])
                Vt, Ft = make_tube(np.array([p0, mid, p1]), 0.0021 * k, nseg=6)
                lace_parts.append((Vt, Ft, 0))
            for sg in ((-1, 1) if p0 is not None else ()):
                loop = [mid + np.array([0, 0, 0.002 * k]) + 0.012 * k * (np.cos(q) * sg * np.r_[lat, 0] * 0.9 + np.sin(q) * np.r_[d, 0] * 0.5)
                        + np.array([0, 0, 0.004 * k]) * np.sin(q) for q in np.linspace(0, 2 * np.pi, 10, endpoint=False)]
                loop = np.array(loop) + sg * np.r_[lat, 0] * 0.008 * k
                Vt, Ft = make_tube(loop, 0.0019 * k, nseg=5, closed=True)
                lace_parts.append((Vt, Ft, 0))
    out = []
    Vu, Fu, mu = merge_parts(up_parts)
    vc = np.vstack(up_cols)
    mats_u = [material(name + "_Upper", tuple(color[:3]) + (1,), vcol=True, rough=0.62),
              material(name + "_Lining", tuple(lining[:3]) + (1,), vcol=True, rough=0.8),
              material(name + "_Overlay", tuple(acc[:3]) + (1,), vcol=True, rough=0.55),
              material(name + "_Rubber", tuple(sole[:3]) + (1,), vcol=True, rough=0.8)]
    out.append(make_object(b, b.obj.name + "_" + name, Vu, Fu, mats_u, mu, vc, thick=0.0025 * k, subsurf=1))
    Vs, Fs, ms = merge_parts(sole_parts)
    mats_s = [material(name + "_Outsole", tuple(outsole[:3]) + (1,), rough=0.85), material(name + "_Midsole", tuple(sole[:3]) + (1,), rough=0.7),
              material(name + "_Window", (0.15, 0.17, 0.2, 1), rough=0.1)]
    out.append(make_object(b, b.obj.name + "_" + name + "_Sole", Vs, Fs, mats_s, ms, None, thick=0, subsurf=1))
    if lace_parts:
        Vl, Fl, ml = merge_parts(lace_parts)
        met = material(name + "_Eyelet", (0.75, 0.75, 0.78, 1) if style == "canvas_high" else tuple(np.array(acc[:3]) * 0.9) + (1,), rough=0.3)
        out.append(make_object(b, b.obj.name + "_" + name + "_Laces", Vl, Fl, [material(name + "_Laces", tuple(lace[:3]) + (1,), rough=0.9), met], ml,
                               None, thick=0, subsurf=0))
    o.objs.extend(out)
    for ob_ in out[:2]:
        pass
    o.layer(Vu, Fu, 0.003 * k)
    return out


def build_boot_shaft(o, name, height=0.16, color=(0.04, 0.04, 0.045), lace=None, trim=None, canvas=False, sole=0.026):
    """Tall laced shaft for boots and knee-high sneakers, added over a high-top shoe: a sleeve cut from each lower
    leg (so it hugs the calf instead of standing off it like a box), a front lacing gap with a tongue under it,
    eyelets and criss-cross laces up to the top, and a padded (or folded canvas) collar roll."""
    b = o.low; k = b.k; J = b.J
    lace = lace or color
    trim = trim or color
    out = []
    for side in ("l", "r"):
        ank, knee = J[side + "-ankle"], J[side + "-knee"]
        z0 = ank[2] - 0.004 * k  # starts below the shoe collar so the join is covered
        z1 = min(ank[2] + height * k, knee[2] - 0.05 * k)
        m = (b.reg == "LLeg") & (b.side(b.co) == side)
        m |= (b.reg == "Foot") & (b.side(b.co) == side) & (b.co[:, 1] > ank[1] - 0.075 * k)  # heel and ankle down to the sole
        f = np.ones(len(b.co))
        z_sole = b.floor + sole * k + 0.003 * k
        zlo = z0 - (z0 - z_sole) * np.clip((b.co[:, 1] - (ank[1] - 0.075 * k)) / (0.035 * k), 0, 1)
        f[m] = np.maximum(zlo[m] - b.co[m, 2], b.co[m, 2] - z1)
        P, F, A = _start(b, f)
        X = P + vnormals(P, F) * 0.01 * k
        E = edges_of(F)
        low_ = np.clip((z0 + 0.035 * k - P[:, 2]) / (0.035 * k), 0, 1)  # sits just over the top edge of the shoe upper
        gapz = 0.0085 * k + 0.004 * k * low_
        for _ in range(4):
            X = laplace(X, E, 3, taubin=True)
            X = o.col.push(X, 0.0085 * k)
        X = X + vnormals(X, F) * (gapz - 0.0085 * k)[:, None]
        X = laplace(X, E, 2, taubin=True)
        # leg centre line for the angle round the leg (0 = straight ahead)
        def ctr(z):
            tt = np.clip((z - ank[2]) / (knee[2] - ank[2]), 0, 1)[:, None]
            return ank[None, :2] * (1 - tt) + knee[None, :2] * tt
        def ang(Q):
            cq = ctr(Q[:, 2]); return np.arctan2(Q[:, 0] - cq[:, 0], -(Q[:, 1] - cq[:, 1]))
        # lacing gap down the front
        wgap = 0.012 * k
        cq = ctr(X[:, 2]); rr = np.hypot(X[:, 0] - cq[:, 0], X[:, 1] - cq[:, 1])
        gap = wgap - np.abs(ang(X)) * rr
        Pq, Fq, _ = clip(X, F, gap, {})
        Pq, Fq, _ = keep_big(Pq, Fq, {}, frac=0.5)
        Eq = edges_of(Fq)
        mats = [material(name + "_Main", tuple(color[:3]) + (1,), rough=0.85 if canvas else 0.5),
                material(name + "_Trim", tuple(trim[:3]) + (1,), rough=0.7),
                material(name + "_Lace", tuple(lace[:3]) + (1,), rough=0.8),
                material(name + "_Eyelet", (0.75, 0.75, 0.78, 1), rough=0.3)]
        parts = [(Pq, Fq, 0)]
        # tongue: the gap strip, a little under the shaft
        tong = np.maximum(gap, -1)  # keep where the gap was
        Pt, Ft, _ = clip(X, F, -gap - 0.006 * k, {})
        if len(Ft):
            Pt, Ft, _ = keep_big(Pt, Ft, {}, frac=0.5)
            Pt = Pt - vnormals(Pt, Ft) * 0.0015 * k
            parts.append((Pt, Ft, 0))
        # eyelets and criss-cross laces
        loops = sorted(boundary_loops(Fq), key=len, reverse=True)
        zz = np.arange(z0 + 0.012 * k, z1 - 0.01 * k, 0.021 * k)
        prev = None
        for i, z in enumerate(zz):
            pts = []
            for sg in (1, -1):
                cz = ctr(np.array([z]))[0]
                aa = sg * (wgap * 1.35) / max(np.median(rr), 1e-6)
                q = np.array([[cz[0] + np.sin(aa) * 0.2 * k, cz[1] - np.cos(aa) * 0.2 * k, z]])
                dirv = q[0, :2] - cz; dirv /= np.linalg.norm(dirv)
                # march inward to the shaft surface
                cand = Pq[np.abs(Pq[:, 2] - z) < 0.006 * k]
                if len(cand) == 0:
                    continue
                aq = ang(cand)
                j = np.argmin(np.abs(aq - aa))
                p = cand[j] + np.r_[dirv, 0] * 0.001 * k
                pts.append(p)
                ring = np.array([p + (np.r_[dirv, 0] * 0.0012 * k) + 0.0028 * k * (np.cos(t) * np.array([0, 0, 1.0]) + np.sin(t) * np.r_[-dirv[1], dirv[0], 0])
                                 for t in np.linspace(0, 2 * np.pi, 11)[:-1]])
                Ve, Fe = make_tube(ring, 0.0009 * k, nseg=5, closed=True)
                parts.append((Ve, Fe, 3))
            if len(pts) == 2:
                if prev is not None:
                    for a_, b_ in ((prev[0], pts[1]), (prev[1], pts[0])):
                        mid = (a_ + b_) / 2; cz = ctr(np.array([mid[2]]))[0]
                        dv = mid[:2] - cz; dv /= np.linalg.norm(dv)
                        mid = mid + np.r_[dv, 0] * 0.003 * k
                        Vl, Fl = make_tube(np.array([a_, mid, b_]), 0.0016 * k, nseg=6)
                        parts.append((Vl, Fl, 2))
                prev = pts
        # collar roll round the top
        top = max(loops, key=lambda l: Pq[l, 2].mean())
        tl = Pq[top]
        if len(tl) > 8:
            Vt, Ft2 = make_tube(tl, (0.0045 if not canvas else 0.0035) * k, nseg=8, closed=False)
            parts.append((Vt, Ft2, 1))
        Vd, Fd, md = merge_parts(parts)
        ob = make_object(b, f"{b.obj.name}_{name}_{side.upper()}", Vd, Fd, mats, md, None, thick=0.003 * k, subsurf=1)
        out.append(ob)
        # tuck the shoe upper under the shaft wherever the shaft covers it (no edges poking out at the join)
        for so in o.objs:
            if not so.data.materials or not so.data.materials[0].name.endswith("_Upper"):
                continue
            co = np.array([v.co for v in so.data.vertices])
            if len(co) == 0:
                continue
            sel = (b.side(co) == side) & (co[:, 2] > z_sole - 0.002 * k) & (co[:, 2] < z1) & \
                  (co[:, 1] > ank[1] - 0.06 * k) & (co[:, 2] > np.interp(co[:, 1], [ank[1] - 0.075 * k, ank[1] - 0.04 * k], [z0, z_sole]) - 0.004 * k)
            if not sel.any():
                continue
            _, j = o.col.tree.query(co[sel])
            Pn, Nn = o.col.P[j], o.col.N[j]
            dd = np.einsum("ij,ij->i", co[sel] - Pn, Nn)
            lim = 0.0062 * k
            newc = co[sel] - Nn * np.maximum(dd - lim, 0)[:, None]
            co[sel] = newc
            for vi, c_ in zip(np.where(sel)[0], newc):
                so.data.vertices[vi].co = c_
    o.objs.extend(out)
    return out[0]


# ----------------------------------------------------------------------------------------------- posed build
# Clothes are modelled on the body with the arms raised part way (BUILD_ARM_RAD), where the armpit is open, then put
# back into the rest pose through the inverse of their own skinning. In rest the cloth under the arm folds the way
# the skin does, and when an animation lifts the arms it opens back to the clean modelled shape (building in the rest
# pose crumpled that cloth between arm and side, and raised arms tore it open).
BUILD_ARM_RAD = 0.7
UNPOSE_PUSH = 0.022  # (x k) cloth kept this far off the rest torso in the armpit band after unposing
UNPOSE_PUSH_BODY_ONLY = True
LAPEL_PROF = [(0.012, -0.001), (0.018, 0.008), (0.006, 0.028), (-0.008, 0.04)]  # (dz, dr) x k rings of a lapel collar
FOLD_LIFT = 0.008  # build_top: a fold-over collar's turned-down part sits this much (x k) above the panel
REHANG_BLEND = 0.0  # rehang: the straight fall eases in over this height (x k) below its start
REHANG_TOP = True
TORSO_SMOOTH = 0  # build_top: smooth+push passes over a jacket's body panel
COLLAR_SMOOTH = 0  # build_top: smooth+push passes over a fold-over (lapel/shirt) collar
SLEEVE_PUSH = 0.008  # (x k) sleeves kept this far off the rest arm after unposing
SLEEVE_OFF_TANK = True  # _sleeve_flag: sleeve-root cloth over the tank is body panel
HIP_CUT_CENTRE = 0.08  # hip_cut_z: rise of the cut at the centre front/back (x k)
HIP_CUT_CW = 0.10
SLEEVE_ROOT_EASE = 0.15  # build_top: extra sleeve radius at the root (x)
ARMPIT_HUG = 0.0  # build_top: cloth near the armpit pulled onto the skin
ARMPIT_BODY = 0.0  # cloth near the armpit takes the skin's own weights (see skin_to_rig)
SHOULDER_SHARPEN = 2.0
HIP_SHARPEN = 1.0
HEM_FLARE_ADD = 0.0  # build_top: extra outward fall of a top below the waist
DRAPE_UP = 0.0  # skin_to_rig: a top's cloth hovering this many gaps above... (0 = off)
DRAPE_D0 = 0.015  # gap (k) where the hang-from weights start
DRAPE_D1 = 0.04   # ... and are full
LEG_OUT_DEG = 0.0  # lower-body shell: legs spread this much before the remesh
HIP_R0 = 0.10
HIP_R1 = 0.18
SHOULDER_R0 = 0.10
SHOULDER_R1 = 0.18
ARMPIT_ZCUT = True
ARMPIT_R0 = 0.10
ARMPIT_R1 = 0.17
LIFT_MIN_ARM = 0.9  # (arm-labelled shell points with less arm weight than this at rest take the lifted-pose weights)
LIFT_WEIGHTS = True  # posed_body: shell skin weights looked up in the arms-lifted pose (hand/hip apart)
STRAY_RELABEL = False  # (posed_body: arm shell points that stayed at the hip -> torso; the lifted-pose weights fixed the cause)


def _best_rot(arm, bn, score, ang):
    import bpy
    pb = arm.pose.bones[bn]; pb.rotation_mode = "XYZ"; best = None
    for ax in range(3):
        for sg in (1, -1):
            r = [0, 0, 0]; r[ax] = sg * ang; pb.rotation_euler = r
            bpy.context.view_layer.update(); s = score()
            if best is None or s > best[0]:
                best = (s, tuple(r))
    pb.rotation_euler = best[1]; bpy.context.view_layer.update()


def set_build_pose(arm, on=True):
    import bpy
    for pb in arm.pose.bones:
        pb.rotation_mode = "XYZ"; pb.rotation_euler = (0, 0, 0)
    bpy.context.view_layer.update()
    if on and BUILD_ARM_RAD > 0:
        for s in ("Left", "Right"):
            _best_rot(arm, s + "UpperArm", lambda: (arm.matrix_world @ arm.pose.bones[s + "Hand"].head).z, BUILD_ARM_RAD)


def posed_rig(whole, arm):
    """(whole_p, arm_p): copies of the body and armature with the build pose made their rest pose."""
    import bpy
    set_build_pose(arm, True)
    wp = whole.copy(); wp.data = whole.data.copy(); wp.name = whole.name + "_Posed"
    for c in whole.users_collection:
        c.objects.link(wp)
    if wp.data.shape_keys:  # (a locked shape key blocks applying the armature)
        wp.shape_key_clear()
    for mod in list(wp.modifiers):
        if mod.type == "ARMATURE":
            mod.object = arm
            with bpy.context.temp_override(object=wp, active_object=wp):
                bpy.ops.object.modifier_apply(modifier=mod.name)
        else:
            wp.modifiers.remove(mod)
    ap = arm.copy(); ap.data = arm.data.copy(); ap.name = arm.name + "_Posed"
    for c in arm.users_collection:
        c.objects.link(ap)
    for pb in ap.pose.bones:
        src = arm.pose.bones[pb.name]; pb.rotation_mode = src.rotation_mode; pb.rotation_euler = src.rotation_euler
    bpy.context.view_layer.update()
    for ob in bpy.context.view_layer.objects:
        ob.select_set(False)
    ap.select_set(True); bpy.context.view_layer.objects.active = ap
    bpy.ops.object.mode_set(mode="POSE")
    bpy.ops.pose.armature_apply(selected=False)
    bpy.ops.object.mode_set(mode="OBJECT")
    set_build_pose(arm, False)
    return wp, ap


def unpose(objs, arm, whole=None, rest=None):
    """Put garments modelled in the build pose back into the rest pose of `arm` (inverse linear blend skinning with
    each garment's own weights) and point their Armature modifier at `arm`."""
    import bpy
    from mathutils import Matrix
    set_build_pose(arm, True)
    mw = arm.matrix_world; mwi = mw.inverted()
    D = {pb.name: np.array(mw @ pb.matrix @ pb.bone.matrix_local.inverted() @ mwi) for pb in arm.pose.bones}
    for ob in objs:
        me = ob.data; n = len(me.vertices)
        P = np.array([v.co[:] for v in me.vertices])
        O = np.array(ob.matrix_world); Oi = np.linalg.inv(O)
        Pw = (O @ np.c_[P, np.ones(n)].T).T
        gn = {g.index: g.name for g in ob.vertex_groups}
        Mb = np.zeros((n, 4, 4)); ws = np.zeros(n)
        for v in me.vertices:
            for g in v.groups:
                nm = gn.get(g.group)
                if nm in D and g.weight > 0:
                    Mb[v.index] += g.weight * D[nm]; ws[v.index] += g.weight
        ok = ws > 1e-6
        Mb[ok] /= ws[ok][:, None, None]
        Mb[~ok] = np.eye(4)
        R = np.linalg.solve(Mb, Pw[:, :, None])[:, :, 0]
        if rest is not None and UNPOSE_PUSH:
            # back at rest the armpit closes and the blend pulls the cloth there in through the tank's armhole edge
            # (white patches at the armpits): push it back out of the rest torso, armpit band only
            Wi = np.array(rest.obj.matrix_world.inverted()); Wm = np.array(rest.obj.matrix_world)
            Xr = (Wi @ R.T).T[:, :3]
            if not hasattr(rest, "_col_torso"):
                bi = rest.body_idx; na = bi[~np.isin(rest.reg[bi], ["Hand", "LArm", "UArm"])]
                rest._col_torso = Collider(); rest._col_torso.dmax = 0.05 * rest.k
                rest._col_torso.add(rest.co[na], rest.N[na])
                # (not the tank's own vertices: some of its faces are wound inward and pushed cloth into the body)
            shz = rest.J["l-shoulder"][2]
            band = (Xr[:, 2] < shz - 0.02 * rest.k) & (Xr[:, 2] > shz - 0.36 * rest.k)
            if UNPOSE_PUSH_BODY_ONLY and "nc_arm" in me.attributes:
                # (sleeves left alone: pushed off the torso they went into the arm and the skin showed through)
                fl_ = np.zeros(n, np.int32); me.attributes["nc_arm"].data.foreach_get("value", fl_)
                band &= fl_ == 0
            if SLEEVE_PUSH and "nc_arm" in me.attributes:
                # sleeves: kept off the rest arm the same way (the inner upper sleeve sat on / in the arm skin near the
                # armpit and the skin showed through when the arm swung forward)
                fl2 = np.zeros(n, np.int32); me.attributes["nc_arm"].data.foreach_get("value", fl2)
                sm = fl2 > 0
                if sm.any():
                    if not hasattr(rest, "_col_arm"):
                        bi = rest.body_idx; aa = bi[np.isin(rest.reg[bi], ["LArm", "UArm"])]
                        rest._col_arm = Collider(); rest._col_arm.dmax = 0.05 * rest.k
                        rest._col_arm.add(rest.co[aa], rest.N[aa])
                    Xr[sm] = rest._col_arm.push(Xr[sm], SLEEVE_PUSH * rest.k)
                    R = (Wm @ np.c_[Xr, np.ones(n)].T).T
            if band.any():
                Xp = rest._col_torso.push(Xr[band], UNPOSE_PUSH * rest.k)
                if os.environ.get("NC_DBG2"):
                    mv = np.linalg.norm(Xp - Xr[band], axis=1)
                    print("unpose push", ob.name[-14:], int(band.sum()), "moved", int((mv > 1e-4).sum()), "max/k %.4f" % (mv.max() / rest.k), flush=True)
                Xr[band] = Xp
                R = (Wm @ np.c_[Xr, np.ones(n)].T).T
        L = (Oi @ R.T).T[:, :3]
        me.vertices.foreach_set("co", L.ravel()); me.update()
        for mod in ob.modifiers:
            if mod.type == "ARMATURE":
                mod.object = arm
    set_build_pose(arm, False)


def posed_body(rb, arm, wp, ap):
    """A RigBody `rb` (built in the rest pose) carried into the build pose: its shell deformed by the body's own
    skinning (a voxel remesh of the posed mesh falls apart), joints from the posed armature `ap`, the posed body mesh
    `wp` as its object. The rest body stays on .rest."""
    import copy as _copy
    whole = rb.obj
    names = [g.name for g in whole.vertex_groups]
    W = np.zeros((len(rb.whole_co), len(names)))
    for v in whole.data.vertices:
        for g in v.groups:
            W[v.index, g.group] = g.weight
    set_build_pose(arm, True)
    mw = arm.matrix_world; mwi = mw.inverted()
    D = np.zeros((len(names), 4, 4))
    for gi, nm in enumerate(names):
        pb = arm.pose.bones.get(nm)
        D[gi] = np.array(mw @ pb.matrix @ pb.bone.matrix_local.inverted() @ mwi) if pb else np.eye(4)
    set_build_pose(arm, False)
    O = np.array(whole.matrix_world); Oi = np.linalg.inv(O)
    tree = cKDTree(rb.whole_co)
    acols_ = [gi for gi, nm in enumerate(names) if any(t in nm for t in ("UpperArm", "LowerArm", "Hand", "Twist",
              "Thumb", "Index", "Middle", "Ring", "Pinky"))]
    zcut = rb.J["l-shoulder"][2] - 0.12 * rb.k
    lift_ok = LIFT_WEIGHTS and getattr(rb, "co_lift", None) is not None and len(rb.co_lift) == len(rb.co)
    tree_l = cKDTree(rb.whole_lift) if lift_ok else None
    def deform(X, reg=None, Xl=None):
        if X is None or not len(X):
            return X
        # skin weights from the lifted pose when we have it: in the rest pose the inner forearm's nearest body
        # vertices are on the hip (female A-pose), so the sleeve's inner side stayed at the hip as a flap
        d, j = tree.query(X, k=4)
        w = 1 / np.maximum(d, 1e-5) ** 2; w /= w.sum(1, keepdims=True)
        Wx = np.einsum("nk,nkg->ng", w, W[j])
        if Xl is not None and reg is not None:
            # only where the rest lookup is wrong: arm-labelled shell points that barely follow the arm
            fix = np.isin(np.asarray(reg), ["UArm", "LArm", "Hand"]) & (Wx[:, acols_].sum(1) < LIFT_MIN_ARM)
            if fix.any():
                dl, jl = tree_l.query(Xl[fix], k=4)
                wl = 1 / np.maximum(dl, 1e-5) ** 2; wl /= wl.sum(1, keepdims=True)
                Wx[fix] = np.einsum("nk,nkg->ng", wl, W[jl])
                if os.environ.get("NC_DBG2"):
                    print("posed_body: lifted weights for", int(fix.sum()), "shell points", flush=True)
        if reg is None:
            reg = rb.whole_reg[j[:, 0]]
        # hip skin under a resting hand carries hand weights (MakeHuman bleed): raising the arm dragged the hips out
        bad = ~np.isin(np.asarray(reg), ["UArm", "LArm", "Hand"]) & (X[:, 2] < zcut)
        Wx[np.ix_(bad, acols_)] = 0
        s_ = Wx.sum(1, keepdims=True)
        Wx = np.where(s_ > 1e-6, Wx / np.maximum(s_, 1e-9), 0)
        M = np.einsum("ng,gij->nij", Wx, D); M[s_[:, 0] <= 1e-6] = np.eye(4)
        Xw = (O @ np.c_[X, np.ones(len(X))].T).T
        Y = np.einsum("nij,nj->ni", M, Xw)
        return (Oi @ Y.T).T[:, :3]
    pb_ = _copy.copy(rb)
    pb_.rest = rb
    pb_.co = deform(rb.co, rb.reg, rb.co_lift if lift_ok else None)
    acols = [gi for gi, nm in enumerate(names) if any(t in nm for t in ("UpperArm", "LowerArm", "Hand", "Twist",
             "Thumb", "Index", "Middle", "Ring", "Pinky"))]
    d, j = tree.query(rb.co, k=4)
    w = 1 / np.maximum(d, 1e-5) ** 2; w /= w.sum(1, keepdims=True)
    aw = np.einsum("nk,nk->n", w, W[j][:, :, acols].sum(2))
    pb_.armish_tree = cKDTree(pb_.co[aw > 0.05]) if (aw > 0.05).any() else None
    # the shell bridges a resting hand/forearm and the hip (female A-pose): those shell points are labelled arm but
    # skin to the hip, so in the build pose they stay at the hip, far from the raised arm. Cloth cut from them was
    # a sleeve that hung down to the waist (skinned to the forearm: torn flaps whenever the arm moved). Torso now.
    lab_arm = _isin(rb.reg, ARMS + ("Hand",)) & STRAY_RELABEL
    stray = lab_arm & (aw < 0.5)
    pbJ = dict(rb.J); bones_ = ap.data.bones
    for s_, S in (("l", "Left"), ("r", "Right")):
        pbJ[s_ + "-shoulder"] = np.array(bones_[S + "UpperArm"].head_local[:]); pbJ[s_ + "-hand"] = np.array(bones_[S + "Hand"].head_local[:])
    tmp_ = _copy.copy(rb); tmp_.J = pbJ
    sa_, _, Ra_ = arm_param(tmp_, pb_.co)
    good_ = lab_arm & (aw > 0.9)
    for lo in np.arange(0.0, 1.0, 0.1):
        mb_ = good_ & (sa_ >= lo) & (sa_ < lo + 0.1)
        if mb_.sum() > 10:
            lim_ = 1.4 * np.percentile(Ra_[mb_], 95) + 0.01 * rb.k
            stray |= lab_arm & (sa_ >= lo) & (sa_ < lo + 0.1) & (Ra_ > lim_)
    if stray.any():
        pb_.reg = np.array(rb.reg, dtype=object).copy(); pb_.reg[stray] = "Torso"
        if os.environ.get("NC_DBG2"):
            print("posed_body: relabelled", int(stray.sum()), "of", int(lab_arm.sum()), "arm shell points", flush=True)
    pb_.whole_co = deform(rb.whole_co, rb.whole_reg)
    wp.data.vertices.foreach_set("co", pb_.whole_co.ravel()); wp.data.update()
    pb_.tank_co = deform(rb.tank_co)
    pb_.N = vnormals(pb_.co, pb_.faces)
    bones = ap.data.bones; h = lambda n: np.array(bones[n].head_local[:])
    J = dict(rb.J)
    for s_, S in (("l", "Left"), ("r", "Right")):
        J[s_ + "-shoulder"] = h(S + "UpperArm"); J[s_ + "-elbow"] = h(S + "LowerArm"); J[s_ + "-hand"] = h(S + "Hand")
    pb_.J = J
    if hasattr(rb, "tree"):
        pb_.tree = cKDTree(pb_.co[rb.body_idx])
    pb_.obj = wp; pb_.arm = ap
    pb_.G = {}
    for at in ("_armtree", "_armonly"):
        if hasattr(pb_, at):
            delattr(pb_, at)
    return pb_


def build_bodies(whole, arm):
    """(rest RigBody, posed RigBody) for a posed build; the posed one carries .rest and .low_body."""
    rb = RigBody(whole, arm)
    wp, ap = posed_rig(whole, arm)
    pb = posed_body(rb, arm, wp, ap)
    # the lower-body shell has no arms (they're swung away before the remesh), so the arm pose doesn't change it
    pb.low_body = RigBody(whole, arm, exclude_arms=True)
    wp.hide_set(True)
    return rb, pb
