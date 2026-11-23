# Neon Coast garment maker for the MakeHuman (MPFB) bodies.
# Builds real 3D clothes that are sized to each body: the garment starts as the body's own (modesty-smoothed) surface,
# cut along clean hem lines, subdivided, then loosened with per-region "drape" envelopes (boxy tops hang straight from
# the chest, baggy pants hang from the hips and stack at the ankles), extended past the body where cloth hangs free
# (hoodie hems, pant legs over the shoes), smoothed, and pushed outside the body and every layer underneath.
# Everything stays on top of the permanent base layer (white tank + shorts + NC_Modesty key): NO NUDITY, EVER.
# Pure bpy + numpy + scipy. Original designs only: no brands, logos or real-world likenesses.
import bpy
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
        if exclude_arms:  # lower-body shell: swing the arms far out so the hands can't fuse to the hips
            armv = np.isin(regw, ["LArm", "Hand"]) | ((regw == "UArm") & (cw[:, 2] < J["l-shoulder"][2] - 0.1 * (cw[:, 2].max() - cw[:, 2].min()) / REF_H * 0 - 0.4))
            moved = cw.copy()
            moved[armv, 0] += np.sign(moved[armv, 0]) * 3.0
            moved[armv, 2] += 1.5
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
        okw = regw != "X"
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
        self.whole_faces = [list(p.vertices) for p in me.polygons if p.material_index == 0]
        self.co, self.G, self.J, self.reg = co, {}, J, reg
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


def _start(b, f, sub=0, smooth=2):
    P, F, A = clip(b.co, b.faces, f, {"reg": b.reg})
    P, F, A = keep_big(P, F, A)
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
    zc = neck_z - (0.012 + (0.05 if kind == "tee" else 0.035) * front) * k
    if collar in ("stand", "turtle", "shirt"):
        zc = neck_z - (0.004 + 0.02 * front) * k
    if neck_drop:
        zc = zc - neck_drop * k * np.clip(1 - np.abs(P0[:, 0] - b.cx) / (0.08 * k), 0, 1) * front
    # neck hole: a ring around the neck (works for sloped female shoulders too) plus the front scoop
    hm_ = (reg == "Head") & (P0[:, 2] > neck_z) & (P0[:, 2] < neck_z + 0.03 * k)
    yn = P0[hm_, 1].mean() if hm_.any() else J["neck"][1]
    dn = np.hypot(P0[:, 0] - b.cx, (P0[:, 1] - yn) * 1.08)
    Rn = np.median(np.hypot(P0[hm_, 0] - b.cx, (P0[hm_, 1] - yn) * 1.08)) if hm_.any() else 0.06 * k
    margin = {"rib": 0.016, "stand": 0.008, "turtle": 0.004, "shirt": 0.008, "lapel": 0.012, "none": 0.022}.get(collar, 0.016) * k
    margin = margin + (0.03 if kind == "tee" else 0.012) * k * front ** 1.5
    if neck_drop:
        margin = margin + neck_drop * k * 0.5 * front
    ring = np.where(P0[:, 2] > neck_z - 0.16 * k, Rn + margin - dn, -1.0)
    zc2 = zc - 0.05 * k  # only very deep cuts come from the plane now
    f[tor] = np.maximum(f[tor], np.maximum(ring[tor], P0[tor, 2] - np.maximum(zc2[tor], zc[tor] + 0.04 * k)))
    arm = _isin(reg, ARMS)
    f[arm] = s[arm] - s_end if s_end > 0 else 1.0
    if sleeve == "none":  # clean round armholes: a cylinder around each upper arm
        _, _, Ra0 = arm_param(b, P0)
        for side in ("l", "r"):
            ms = (b.side(P0) == side) & _isin(reg, ARMS) & (s > 0.1) & (s < 0.3)
            r_up = np.percentile(Ra0[ms], 90) if ms.any() else 0.05 * k
            armpit = J[side + "-shoulder"][2] - 0.085 * k
            near = (b.side(P0) == side) & (s > -0.06) & (s < 0.2) & ~(reg == "Head") & (P0[:, 2] > armpit)
            hole = r_up * 1.35 + 0.01 * k - Ra0
            hole = np.where(s < 0.02, hole - (0.02 - s) * 2.5 * k, hole)  # round the top of the armhole
            f[near] = np.maximum(f[near], hole[near])
            f[near & arm] = np.maximum(f[near & arm], 0.01)
    P, F, R = _start(b, f)
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
        sc = 1.0 + flare * t  # cloth falls slightly outward
        if rib and kind != "tee":
            sc *= 1 - 0.07 * smoothstep(1 - 0.055 * k / max(drop, 1e-3) - 0.25, 1.0, t)
        pts[:, 0] = b.cx + (pts[:, 0] - b.cx) * sc
        pts[:, 1] = b.yc + (pts[:, 1] - b.yc) * sc
        rings.append(pts)
    X, F, R, last = _extend_loop(X, F, waist, None, rings, R, "Hem")
    isarm = _isin(R, ARMS)
    E = edges_of(F)
    X = laplace(X, E, 3, taubin=True)
    X = rehang(b, X, F, ~isarm, chest_z)
    # collar: rib band (tee / hoodie), stand collar (puffer, track), turtleneck, shirt collar, lapel
    nl = neck_loop
    c = X[nl].mean(0)
    L0 = X[nl].copy()
    outd = L0[:, :2] - c[:2]; outd /= np.maximum(np.linalg.norm(outd, axis=1), 1e-9)[:, None]
    prof = {"rib": [(0.006, -0.0005), (0.012, -0.001)],
            "stand": [(0.02, -0.002), (0.04, -0.003), (0.06, -0.003), (0.064, 0.0)],
            "turtle": [(0.03, -0.002), (0.06, -0.003), (0.085, -0.002), (0.09, 0.002)],
            "shirt": [(0.012, -0.002), (0.024, -0.001), (0.026, 0.006), (0.01, 0.014), (-0.004, 0.018)],
            "lapel": [(0.012, -0.001), (0.018, 0.008), (0.0, 0.03), (-0.025, 0.045)],
            "none": []}[collar]
    col_rings = []
    for dz, dr in prof:
        pts = L0.copy()
        pts[:, 2] += dz * k
        pts[:, :2] += outd * dr * k
        col_rings.append(pts)
    if col_rings:
        X, F, R, _ = _extend_loop(X, F, nl, None, col_rings, R, "Collar")
    E = edges_of(F)
    X = laplace(X, E, 2, taubin=True)
    X = o.col.push(X, 0.006 * k)
    if front_open:  # open front (overshirts, coats): split the centre front, leave the collar ends apart
        neck_pts = X[nl].copy()
        fo = np.where(X[:, 1] < b.yc, 0.006 * k - np.abs(X[:, 0] - b.cx), -1.0)
        X, F, A_ = clip(X, F, fo, {"reg": R})
        R = A_["reg"]
        X, F, A_ = keep_big(X, F, {"reg": R}, frac=0.3)
        R = A_["reg"]
        _, nl_ = cKDTree(X).query(neck_pts)
        nl = list(nl_)
        hood = False; pocket = False
    # 6. colours: main / accent (rib, zip) / print or camo through vertex colours
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
    ob = make_object(b, b.obj.name + "_" + name, X, F, mats, mi, vcol, thick=thick, arm_flag=_isin(R, ARMS))
    o.objs.append(ob)
    N = o.layer(X, F, thick)
    o.top = (X, N, F, nl, z_hem)
    if hood:
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
        path = surface_path(o, X, N, st, (0.17 + 0.03 * (sgn > 0)) * k, 0.008 * k, 0.012 * k)
        rr = np.full(len(path), 0.0032 * k); rr[-3:] = 0.0042 * k
        V, F = tube(path, rr, 8)
        ob = make_object(b, b.obj.name + "_" + name + "_String" + ("L" if sgn > 0 else "R"), V, F,
                         [material(name + "_String", tuple(rgba[:3]) + (1,), rough=0.7)], None, None, thick=0, subsurf=0)
        out.append(ob)
    return out


def rehang(b, X, F, sel, hang_from, ease=0.0):
    """Final straight fall: below hang_from the cloth radius never shrinks going down (removes ledges)."""
    rnew, _ = drape_envelope(b, X, sel, X[sel, 2].max(), ease, 0.0, hang_from, flare=0.0005)
    _, r = torso_cyl(b, X)
    w = sel & (X[:, 2] < hang_from)
    sc = np.where(w & (r > 1e-6), rnew / np.maximum(r, 1e-6), 1)
    X = X.copy()
    X[:, 0] = b.cx + (X[:, 0] - b.cx) * sc
    X[:, 1] = b.yc + (X[:, 1] - b.yc) * sc
    return X


def build_pants(o, name, fit="baggy", color=(0.06, 0.065, 0.075), accent=None, stack=True, cuffed=False,
                cargo=False, camo_pal=None, thick=0.004, shorts=False):
    b = o.low; k = b.k; J = b.J; P0 = b.co; reg = b.reg
    pel = J["pelvis"][2]
    front = np.clip((b.yc - P0[:, 1]) / (0.08 * k), 0, 1)
    z_waist = pel + (0.035 - 0.02 * front) * k
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
        Rt = np.interp(ss, [0, 0.25, 1.0], [r_th * (1 + ease), r_th * (1 + ease) * 0.97, max(hem_r, r_th * 0.55)])
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
        X[mm] = X0[mm] + w[:, None] * (axis + rad[mm] * Rn[:, None] - X0[mm])
    # inner legs never cross the centre line
    gap = 0.008 * k
    for sgn, side in ((1, "l"), (-1, "r")):
        mm = legs & (b.side(X0) == side)
        bad = mm & ((X[:, 0] - b.cx) * sgn < gap)
        X[bad, 0] = b.cx + sgn * gap
    D = laplace(X - X0, E, 20)
    X = X0 + D
    X = laplace(X, E, 4, taubin=True)
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
    # waistband accent faces
    fc = np.array([X[f].mean(0) for f in F])
    mi = np.zeros(len(F), int)
    zw = np.interp(fc[:, 0], [b.cx - 1, b.cx + 1], [0, 0])
    mi[fc[:, 2] > pel + 0.0 * k] = 1
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


def build_chain(o, name, gold=True, droop=0.11, link=0.0085, thick=0.0042, pendant=True):
    b = o.b; k = b.k
    if o.top is None:
        return []
    X, N, F, nl, _ = o.top
    L = X[nl]
    c = L.mean(0)
    phi = np.arctan2(L[:, 1] - c[1], L[:, 0] - c[0])
    order = np.argsort(phi)
    phi = phi[order]; L = L[order]
    # resample evenly around the neck, sitting a little lower than the collar
    ph = np.linspace(-np.pi, np.pi, 200, endpoint=False)
    rx = np.interp(ph, phi, L[:, 0] - c[0], period=2 * np.pi)
    ry = np.interp(ph, phi, L[:, 1] - c[1], period=2 * np.pi)
    zz = np.interp(ph, phi, L[:, 2], period=2 * np.pi)
    front = np.clip(-np.sin(ph), 0, 1) ** 2  # -y is the front
    path = np.stack([c[0] + rx * 1.15, c[1] + ry * 1.15, zz - 0.012 * k - droop * k * front], 1)
    tree = cKDTree(X)
    for _ in range(4):  # lay it onto the garment
        d, j = tree.query(path)
        q = X[j] + N[j] * (thick * k * 1.6)
        path = path * 0.3 + q * 0.7
        path = np.vstack([path[-1:], path, path[:1]])
        path = 0.25 * path[:-2] + 0.5 * path[1:-1] + 0.25 * path[2:]
    # cuban-style links: alternating flat ovals along the path
    seg = np.linalg.norm(np.diff(np.vstack([path, path[:1]]), axis=0), axis=1)
    cum = np.concatenate([[0], np.cumsum(seg)])
    total = cum[-1]
    nlink = int(total / (link * k))
    V, Fc = [], []
    for i in range(nlink):
        t = i * total / nlink
        p = np.array([np.interp(t, cum, np.append(path[:, a], path[0, a])) for a in range(3)])
        t2 = ((i + 1) % nlink) * total / nlink if i + 1 < nlink else total
        p2 = np.array([np.interp(t2 % total, cum, np.append(path[:, a], path[0, a])) for a in range(3)])
        tg = p2 - p; tg /= np.linalg.norm(tg) + 1e-12
        _, j = tree.query(p)
        nrm = N[j] - (N[j] @ tg) * tg; nrm /= np.linalg.norm(nrm) + 1e-12
        sd = np.cross(tg, nrm)
        ax2 = sd if i % 2 == 0 else (sd * 0.5 + nrm * 0.87)
        R1, R2 = 0.75 * link * k, thick * k * 0.5
        base = len(V)
        nu, nv = 12, 6
        for a in range(nu):
            A = 2 * np.pi * a / nu
            cen = p + (np.cos(A) * tg * R1 + np.sin(A) * ax2 * R1 * 0.62)
            rd = np.cos(A) * tg + np.sin(A) * ax2; rd /= np.linalg.norm(rd)
            up = np.cross(rd, np.cross(tg, ax2))
            up /= np.linalg.norm(up) + 1e-12
            for bb in range(nv):
                B = 2 * np.pi * bb / nv
                V.append(cen + R2 * (np.cos(B) * rd + np.sin(B) * up))
        for a in range(nu):
            for bb in range(nv):
                a2, b2 = (a + 1) % nu, (bb + 1) % nv
                Fc.append([base + a * nv + bb, base + a2 * nv + bb, base + a2 * nv + b2, base + a * nv + b2])
    out = []
    col = (1.0, 0.77, 0.34) if gold else (0.85, 0.86, 0.9)
    met = material("NC_Chain_" + ("Gold" if gold else "Silver"), col + (1,), rough=0.22)
    met.node_tree.nodes["Principled BSDF"].inputs["Metallic"].default_value = 1.0
    out.append(make_object(b, b.obj.name + "_" + name, np.array(V), Fc, [met], None, None, thick=0, subsurf=0))
    if pendant:
        # an original round "sun" medallion: a domed disc with an iced rim
        i = int(np.argmin(path[:, 1] + 0 * path[:, 2]))
        i = int(np.argmin(path[:, 2]))
        p = path[i]
        _, j = tree.query(p)
        n = N[j]
        r = 0.028 * k
        p = p + n * 0.006 * k - np.array([0, 0, r * 0.95])
        u = np.cross(n, [0, 0, 1.0]); u /= np.linalg.norm(u); v = np.cross(n, u)
        Vp, Fp = [], []
        nr, na = 5, 28
        Vp.append(p + n * 0.006 * k)
        for ri in range(1, nr + 1):
            rr = r * ri / nr
            h = 0.006 * k * (1 - (ri / nr) ** 2) + 0.002 * k
            for a in range(na):
                A = 2 * np.pi * a / na
                bump = 0.0015 * k * (ri == nr) * (a % 2)
                Vp.append(p + (u * np.cos(A) + v * np.sin(A)) * rr + n * (h + bump))
        for a in range(na):
            Fp.append([0, 1 + a, 1 + (a + 1) % na])
        Vp_ = np.array(Vp)
        if np.cross(Vp_[1] - Vp_[0], Vp_[2] - Vp_[0]) @ n < 0:
            flip = True
        else:
            flip = False
        for ri in range(nr - 1):
            for a in range(na):
                a2 = (a + 1) % na
                Fp.append([1 + ri * na + a, 1 + (ri + 1) * na + a, 1 + (ri + 1) * na + a2, 1 + ri * na + a2])
        if flip:
            Fp = [f[::-1] for f in Fp]
        out.append(make_object(b, b.obj.name + "_" + name + "_Pendant", np.array(Vp), Fp, [met], None, None, thick=0.004 * k / k, subsurf=1))
    o.objs.extend(out)
    return out


def head_frame(b):
    k = b.k
    hm = b.reg == "Head"
    top = b.co[hm, 2].max()
    eye_z = top - 0.118 * k
    hc = b.co[hm & (b.co[:, 2] > eye_z - 0.02 * k)]
    c = np.array([hc[:, 0].mean(), hc[:, 1].mean() + 0.01 * k])
    return hm, top, eye_z, c


def build_cap(o, name, kind="fitted", color=(0.04, 0.04, 0.045), accent=None):
    b = o.b; k = b.k
    hm, top, eye_z, c = head_frame(b)
    P0 = b.co
    front = np.clip((c[1] - P0[:, 1]) / (0.06 * k), -1, 1)
    if kind == "beanie":
        zl = eye_z + (0.035 - 0.05 * np.clip(-front, 0, 1) + 0.0 * front) * k
    else:
        zl = eye_z + (0.045 - 0.035 * np.clip(-front, 0, 1)) * k
    f = np.ones(len(P0))
    f[hm] = zl[hm] - P0[hm, 2]
    P, F, _ = clip(P0, b.faces, f, {})
    P, F, _ = keep_big(P, F, {}, frac=0.5)
    E = edges_of(F)
    X = P + vnormals(P, F) * (0.012 if kind != "beanie" else 0.01) * k
    for _ in range(4):
        X = laplace(X, E, 6, taubin=True)
        X = o.col.push(X, 0.01 * k)
    if kind == "beanie":
        X[:, 2] += 0.01 * k * np.clip((X[:, 2] - eye_z) / (top - eye_z), 0, 1) ** 2
    loops = boundary_loops(F)
    ll = max(loops, key=len)
    R = np.array(["Cap"] * len(X), dtype=object)
    if kind == "beanie":  # folded cuff
        base = X[ll].copy(); cc = base.mean(0)
        rings = []
        for dz, sc in ((-0.004, 1.05), (0.03, 1.06), (0.034, 1.03)):
            pts = base.copy(); pts[:, 2] += dz * k
            pts[:, :2] = cc[:2] + (pts[:, :2] - cc[:2]) * sc
            rings.append(pts)
        X, F, R, _ = _extend_loop(X, F, ll, None, rings, R, "Cuff")
        brim = None
    else:
        # brim out the front
        Lp = X[ll]
        ph = np.arctan2(Lp[:, 1] - c[1], Lp[:, 0] - c[0])
        fr = np.clip((np.cos(ph + np.pi / 2) - 0.55) / 0.45, 0, 1) ** 0.5  # 1 straight ahead (-y), none at the sides
        dirs = np.stack([np.cos(ph), np.sin(ph), np.zeros_like(ph)], 1)
        rings = []
        for t in (0.35, 0.7, 1.0):
            ln = 0.075 * k * (fr ** 0.8) * t
            pts = Lp + dirs * ln[:, None] + np.array([0, 0, -0.012 * k]) * (t ** 2) * fr[:, None] ** 1.0
            pts[:, 2] -= 0.006 * k * (1 - (np.abs(np.sin(ph + np.pi / 2)))) * t
            rings.append(pts)
        X, F, R, _ = _extend_loop(X, F, ll, None, rings, R, "Brim")
    fc = np.array([X[f].mean(0) for f in F])
    mi = np.array([1 if R[f[0]] in ("Brim", "Cuff") and R[f[1]] in ("Brim", "Cuff") else 0 for f in F])
    mats = [material(name + "_Main", tuple(color[:3]) + (1,), rough=0.85), material(name + "_Accent", tuple((accent or color)[:3]) + (1,), rough=0.85)]
    ob = make_object(b, b.obj.name + "_" + name, X, F, mats, mi, None, thick=0.004, subsurf=1)
    o.objs.append(ob)
    o.layer(X, F, 0.004)
    return ob


def build_shades(o, name, lens=(0.02, 0.02, 0.025), frame=(0.03, 0.03, 0.035)):
    """Wraparound shades: a smooth shield following the brow line, cut into two rounded lenses and a bridge,
    with thin temple arms that follow the side of the head back to the ears."""
    b = o.b; k = b.k
    hm, top, eye_z, c = head_frame(b)
    H = b.co[hm]
    th = np.arctan2(H[:, 1] - c[1], H[:, 0] - c[0])
    r = np.hypot(H[:, 0] - c[0], H[:, 1] - c[1])
    span = 1.25
    phs = np.linspace(-np.pi / 2 - span, -np.pi / 2 + span, 72)
    zs = np.linspace(eye_z - 0.026 * k, eye_z + 0.02 * k, 14)
    Rg = np.full((len(zs), len(phs)), np.nan)
    for i, z in enumerate(zs):
        sel = np.abs(H[:, 2] - z) < 0.01 * k
        for j, p in enumerate(phs):
            s2 = sel & (np.abs(np.angle(np.exp(1j * (th - p)))) < 0.06)
            if s2.any():
                Rg[i, j] = r[s2].max()
    Rg = np.where(np.isnan(Rg), np.nanmax(Rg), Rg)
    x = phs + np.pi / 2
    Rm = Rg.max(0)
    cf = np.polyfit(x, Rm, 4)
    Rm = np.maximum(np.polyval(cf, x), Rm)
    Rm = np.polyval(np.polyfit(x, Rm, 4), x) + 0.012 * k
    V = []
    for i, z in enumerate(zs):
        for j, p in enumerate(phs):
            rr = Rm[j] + 0.004 * k * ((z - eye_z) / (0.02 * k))  # slight forward tilt at the top
            V.append([c[0] + np.cos(p) * rr, c[1] + np.sin(p) * rr, z])
    V = np.array(V)
    nz, nph = len(zs), len(phs)
    F = [[i * nph + j, i * nph + j + 1, (i + 1) * nph + j + 1, (i + 1) * nph + j] for i in range(nz - 1) for j in range(nph - 1)]
    # lens outline: two rounded shapes either side of a bridge, measured along the wrap
    arc = x * Rm.mean()
    uu = np.tile(arc, nz); vv = np.repeat(zs - eye_z, nph)
    ax_ = np.abs(uu)
    lc, lw, lh = 0.032 * k, 0.027 * k, 0.018 * k
    du = (ax_ - lc) / lw
    dv = (vv + 0.002 * k + 0.004 * k * np.clip(du, 0, 1)) / lh
    lensf = (np.abs(du) ** 3 + np.abs(dv) ** 3) ** (1 / 3) - 1
    bridge = np.maximum(ax_ - 0.012 * k, np.abs(vv - 0.012 * k) - 0.004 * k) / (0.01 * k)
    fld = np.minimum(lensf, bridge)
    Vc, Fc, _ = clip(V, F, fld, {})
    fc = np.array([Vc[f].mean(0) for f in Fc]); fn = np.array([np.cross(Vc[f[1]] - Vc[f[0]], Vc[f[2]] - Vc[f[0]]) for f in Fc])
    if np.mean(np.einsum("ij,ij->i", fn, fc - np.array([c[0], c[1], eye_z]))) < 0:
        Fc = [f[::-1] for f in Fc]
    # frame rim faces (close to the outline) get the frame material
    fl2 = np.minimum(lensf, bridge)
    m_l = material(name + "_Lens", tuple(lens[:3]) + (1,), rough=0.06)
    m_l.node_tree.nodes["Principled BSDF"].inputs["Metallic"].default_value = 0.7
    m_f = material(name + "_Frame", tuple(frame[:3]) + (1,), rough=0.35)
    ob = make_object(b, b.obj.name + "_" + name, Vc, Fc, [m_l, m_f], None, None, thick=0.003, subsurf=1)
    out = [ob]
    # temple arms: from the outer lens edge, along the side of the head to the ear
    tree = cKDTree(H)
    Nh = b.N[hm]
    for sgn in (-1, 1):
        u_end = sgn * (lc + lw * 0.98)
        j = int(np.argmin(np.abs(arc - u_end)))
        p0 = np.array([c[0] + np.cos(phs[j]) * Rm[j], c[1] + np.sin(phs[j]) * Rm[j], eye_z + 0.006 * k])
        pts = [p0]
        p = p0.copy()
        for t in range(10):
            p = p + np.array([0, 0.012 * k, 0.0])
            d, jj = tree.query(p)
            q = H[jj] + Nh[jj] * 0.006 * k
            p = np.array([q[0], p[1], p0[2] - 0.003 * k * t / 10])
            pts.append(p.copy())
        pts = np.array(pts)
        Vt, Ft = tube(pts, 0.0032 * k, 6)
        out.append(make_object(b, b.obj.name + "_" + name + "_Arm" + ("L" if sgn > 0 else "R"), Vt, Ft, [m_f], None, None, thick=0, subsurf=0))
    o.objs.extend(out)
    return out


# ----------------------------------------------------------------------------------------------- skinning
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
        w = 1 / np.maximum(d, 1e-4) ** 2
        w /= w.sum(1, keepdims=True)
        Wg = np.einsum("nk,nkg->ng", w, W[j])
        Wg /= np.maximum(Wg.sum(1, keepdims=True), 1e-9)
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
    """A skirt (or the lower half of a dress): hip band from the body, then a flared tube to the hem."""
    b = o.low; k = b.k; J = b.J; P0 = b.co; reg = b.reg
    pel = J["pelvis"][2]
    z_waist = pel + 0.05 * k
    z_low = b.crotch_z + 0.05 * k
    f = np.ones(len(P0))
    m = _isin(reg, ("Torso", "ULeg"))
    f[m] = np.maximum(P0[m, 2] - z_waist, z_low - P0[m, 2])
    P, F, R = _start(b, f)
    X = P + vnormals(P, F) * 0.009 * k
    X = o.col_noarm.push(X, 0.006 * k)
    loops = sorted(boundary_loops(F), key=len, reverse=True)[:2]
    low = min(loops, key=lambda l: X[l, 2].mean())
    base = X[low].copy(); c = base.mean(0)
    phi = np.arctan2(base[:, 1] - c[1], base[:, 0] - c[0])
    r0 = np.hypot(base[:, 0] - c[0], base[:, 1] - c[1])
    drop = c[2] - (b.floor + (1 - length) * (c[2] - b.floor))
    nr = max(3, int(drop / (0.012 * k)))
    rings = []
    for i in range(1, nr + 1):
        t = i / nr
        rr = r0 * (1 + flare * t) + 0.004 * k
        if pleats:
            rr = rr * (1 + 0.035 * t * np.sign(np.sin(phi * pleats)) * np.abs(np.sin(phi * pleats)) ** 0.5)
        pts = np.stack([c[0] + np.cos(phi) * rr, c[1] + np.sin(phi) * rr, base[:, 2] - drop * t], 1)
        rings.append(pts)
    X, F, R, _ = _extend_loop(X, F, low, None, rings, R, "Skirt")
    E = edges_of(F)
    X = laplace(X, E, 2, taubin=True)
    X = o.col_noarm.push(X, 0.006 * k)
    vcol = None
    ob = make_object(b, b.obj.name + "_" + name, X, F, [material(name + "_Main", tuple(color[:3]) + (1,))], None, vcol, thick=thick)
    o.objs.append(ob)
    o.layer(X, F, thick)
    return ob


# ----------------------------------------------------------------------------------------------- game export
GAME_TRIS = {"Chain": 6000, "Gloves": 3000, "default": 7000, "small": 1500}


def game_ready(ob):
    """Roblox-friendly copy settings: no subdivision, decimated to a tri budget (the Solidify still adds the
    inside of the cloth). Call before an FBX export with use_mesh_modifiers=True."""
    tris = sum(len(p.vertices) - 2 for p in ob.data.polygons)
    key = next((k for k in GAME_TRIS if k in ob.name), None)
    budget = GAME_TRIS.get(key) if key else (GAME_TRIS["small"] if tris < 4000 else GAME_TRIS["default"])
    for m in list(ob.modifiers):
        if m.type == "SUBSURF":
            ob.modifiers.remove(m)
    if tris > budget:
        d = ob.modifiers.new("GameDecimate", "DECIMATE")
        d.ratio = budget / tris
        # keep the armature first, decimate before the thickness
        while ob.modifiers.find(d.name) > 1:
            with bpy.context.temp_override(object=ob):
                bpy.ops.object.modifier_move_up(modifier=d.name)
    return ob
