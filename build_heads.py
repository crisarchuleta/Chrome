# Neon Coast heads: realistic, changeable faces and hair for the MakeHuman bodies.
#   blender --background --python build_heads.py          (no add-on; reads NeonCoast_MakeHuman.blend)
#   env: NC_OUT (folder), NC_RENDER=0 (skip the preview renders)
#
# The ten bodies share two heads (one per gender; the builds only move the head up or down a little), so every
# piece here is made once per gender, measured from the point between the eyes, and fits all five builds.
#
# Out: NC_Head_Male.fbx / NC_Head_Female.fbx  - every hair style (+ its under-cap version and its soft hairline
#                                                fade), brows, lash lines, lips and stubble, as separate meshes
#      NCHeadData.lua                         - where each piece sits (offset from the eyes' midpoint, Roblox axes),
#                                                its kind, and the face bones' landmarks
#      previews/Head_*.png                    - every style, front, three-quarter and back, next to each other
#
# Hair is grown from the scalp, not stuck on top of it: MakeHuman's own scalp region sets a natural hairline, the
# hair is thickest on top and thins out to nothing at the hairline (so it comes out of the skin, no helmet edge),
# a separate see-through band in the hair colour softens the hairline the way short hair shows skin through it,
# and the surface is combed: grooves that run the way the hair grows, out from the crown or away from a part.
# Locs, twists, buns, ponytails and long hair are real strands and tubes that hang and clear the head and shoulders.
import bpy, bmesh, math, json, os, sys, random
import numpy as np
from mathutils import Vector, Matrix
from mathutils.kdtree import KDTree
from mathutils.bvhtree import BVHTree

OUT = os.environ.get("NC_OUT", r"C:\Users\Crisa\Documents\NeonCoast_Blender")
PREV = os.path.join(OUT, "previews")
os.makedirs(PREV, exist_ok=True)
SRC = os.environ.get("NC_MH_BLEND", os.path.join(OUT, "NeonCoast_MakeHuman.blend"))
RENDER = os.environ.get("NC_RENDER", "1") != "0"
sys.path.insert(0, OUT)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import nc_baselayer as NB

SPM = 6.6 / 1.75
bpy.ops.wm.open_mainfile(filepath=SRC)
scene = bpy.context.scene


def link(ob):
    scene.collection.objects.link(ob)
    return ob


def smoothstep(a, b, x):
    t = np.clip((x - a) / (b - a), 0.0, 1.0)
    return t * t * (3 - 2 * t)


def mesh_object(name, verts, faces):
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(v) for v in verts], [], [list(f) for f in faces])
    me.validate()
    me.update()
    for p in me.polygons:
        p.use_smooth = True
    return link(bpy.data.objects.new(name, me))


# ------------------------------------------------------------------------------------------------ the head surface
class Head:
    def __init__(self, gender):
        src = bpy.data.objects[f"{gender}_Average"]
        co = NB._eval_coords(src) * SPM
        G = NB._groups(src)
        self.gender = gender
        J = {k[6:]: co[v].mean(0) for k, v in G.items() if k.startswith("joint-")}
        self.J = J
        body = np.zeros(len(co), bool)
        body[G["body"]] = True
        neck_z = J["neck"][2]
        keep = body & (co[:, 2] > neck_z - 0.25)
        idx = np.where(keep)[0]
        remap = -np.ones(len(co), int)
        remap[idx] = np.arange(len(idx))
        faces = [[remap[v] for v in p.vertices] for p in src.data.polygons if all(keep[v] for v in p.vertices)]
        self.co = co[idx]
        self.faces = faces
        self.mask = {}
        for g in ("scalp", "lips", "ears", "Left", "Right"):
            m = np.zeros(len(co), bool)
            if g in G:
                m[G[g]] = True
            self.mask[g] = m[idx]
        self.eyeL, self.eyeR = J["l-eye"], J["r-eye"]       # (MakeHuman left = +X in Blender)
        self.anchor = (self.eyeL + self.eyeR) / 2
        self.obj = mesh_object(f"HeadRef_{gender}", self.co, faces)
        self.obj.data.materials.append(material("Skin", (0.80, 0.60, 0.47, 1)))
        self.bvh = BVHTree.FromPolygons([tuple(v) for v in self.co], faces)
        me = self.obj.data
        self.normals = np.array([v.normal[:] for v in me.vertices])
        # landmarks
        c = self.co
        self.top = c[:, 2].max()
        self.ear_z = c[self.mask["ears"], 2].mean() if self.mask["ears"].any() else J["l-eye"][2] - 0.1
        front = c[(np.abs(c[:, 0]) < 0.03)]
        band = front[np.abs(front[:, 2] - (self.anchor[2] - 0.17)) < 0.08]
        self.nose_tip = band[np.argmin(band[:, 1])]
        lips = c[self.mask["lips"]]
        self.lips = lips
        self.mouth = lips.mean(0)
        self.mouth_l = lips[np.argmax(lips[:, 0])]
        self.mouth_r = lips[np.argmin(lips[:, 0])]
        chin_band = front[(front[:, 2] < self.mouth[2] - 0.08) & (front[:, 2] > neck_z)]
        self.chin = chin_band[np.argmin(chin_band[:, 1])] if len(chin_band) else self.mouth - np.array([0, 0, 0.2])
        self.centre = np.array([0.0, (c[:, 1].min() + c[:, 1].max()) / 2, self.ear_z + 0.1])
        self.R = float(np.median(np.linalg.norm(c[c[:, 2] > self.anchor[2]] - self.centre, axis=1)))

    def nearest(self, p):
        loc, nrm, fi, d = self.bvh.find_nearest(Vector(p))
        return np.array(loc), np.array(nrm), fi, d


MATS = {}


def material(name, rgba):
    if name in MATS:
        return MATS[name]
    m = bpy.data.materials.new(name)
    m.diffuse_color = rgba
    m.use_nodes = True
    b = m.node_tree.nodes.get("Principled BSDF")
    b.inputs["Base Color"].default_value = rgba
    b.inputs["Roughness"].default_value = 0.55
    MATS[name] = m
    return m


# ------------------------------------------------------------------------------------------------ fine scalp mesh
def fine_surface(H, zmin, levels=2):
    """the head above zmin, subdivided smooth and snapped back onto the real head, with per-vertex scalp value"""
    c = H.co
    keepf = [f for f in H.faces if all(c[v][2] > zmin for v in f)]
    used = sorted({v for f in keepf for v in f})
    rm = {v: i for i, v in enumerate(used)}
    ob = mesh_object("tmp_fine", c[used], [[rm[v] for v in f] for f in keepf])
    # scalp value on the coarse mesh, smoothed so the hairline is a clean curve, not MakeHuman's zigzag
    s = H.mask["scalp"][used].astype(float)
    edges = np.array([e.vertices[:] for e in ob.data.edges])
    for _ in range(6):
        acc = np.zeros(len(s)); deg = np.zeros(len(s))
        np.add.at(acc, edges[:, 0], s[edges[:, 1]]); np.add.at(acc, edges[:, 1], s[edges[:, 0]])
        np.add.at(deg, edges[:, 0], 1); np.add.at(deg, edges[:, 1], 1)
        s = 0.5 * s + 0.5 * acc / np.maximum(deg, 1)
    attr = ob.data.attributes.new("scalp", "FLOAT", "POINT")
    attr.data.foreach_set("value", s)
    md = ob.modifiers.new("S", "SUBSURF")
    md.levels = levels
    md.render_levels = levels
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(ob.evaluated_get(dg), preserve_all_data_layers=True, depsgraph=dg)
    bpy.data.objects.remove(ob, do_unlink=True)
    V = np.array([v.co[:] for v in me.vertices])
    S = np.zeros(len(V))
    me.attributes["scalp"].data.foreach_get("value", S)
    F = [list(p.vertices) for p in me.polygons]
    for i in range(len(V)):                                     # back onto the real head surface
        V[i] = H.nearest(V[i])[0]
    tmp = mesh_object("tmp_n", V, F)
    N = np.array([v.normal[:] for v in tmp.data.vertices])
    bpy.data.objects.remove(tmp, do_unlink=True)
    bpy.data.meshes.remove(me)
    return V, F, S, N


def signed_hairline(V, F, S, iso=0.5):
    """signed distance (studs) along the head to the hairline: + inside the hair, - on the skin"""
    pts = []
    E = set()
    for f in F:
        for a, b in zip(f, f[1:] + f[:1]):
            E.add((min(a, b), max(a, b)))
    for a, b in E:
        sa, sb = S[a] - iso, S[b] - iso
        if sa * sb < 0:
            t = sa / (sa - sb)
            pts.append(V[a] + (V[b] - V[a]) * t)
    kd = KDTree(len(pts))
    for i, p in enumerate(pts):
        kd.insert(p, i)
    kd.balance()
    d = np.array([kd.find(v)[2] for v in V])
    return np.where(S >= iso, d, -d)


# ------------------------------------------------------------------------------------------------ noise helpers
rng = np.random.default_rng(7)
WAVES = rng.normal(size=(24, 3))
PHASE = rng.uniform(0, 6.283, 24)


def noise(P, scale):
    """smooth value noise in -1..1 from a sum of random waves"""
    P = np.asarray(P) * scale
    out = np.zeros(len(P))
    for k in range(24):
        out += np.sin(P @ WAVES[k] + PHASE[k])
    return out / 4.9


# ------------------------------------------------------------------------------------------------ shells
def clip(V, F, f, *fields):
    """cut the mesh along f = 0 and keep f >= 0, so edges are smooth curves, not stair-steps of whole faces.
    fields (per-vertex arrays) are interpolated onto the new edge vertices."""
    V = [np.asarray(v) for v in V]
    flds = [list(x) for x in fields]
    cache = {}
    out = []
    for face in F:
        poly = []
        n = len(face)
        for k in range(n):
            a, b = face[k], face[(k + 1) % n]
            if f[a] >= 0:
                poly.append(a)
            if (f[a] >= 0) != (f[b] >= 0):
                key = (min(a, b), max(a, b))
                if key not in cache:
                    t = f[a] / (f[a] - f[b])
                    V.append(V[a] + (V[b] - V[a]) * t)
                    for fl in flds:
                        fl.append(fl[a] + (fl[b] - fl[a]) * t)
                    cache[key] = len(V) - 1
                poly.append(cache[key])
        if len(poly) >= 3:
            out.append(poly)
    used = sorted({v for f2 in out for v in f2})
    rm = {v: i for i, v in enumerate(used)}
    Vn = np.array([V[v] for v in used])
    return (Vn, [[rm[v] for v in f2] for f2 in out]) + tuple(np.array([fl[v] for v in used]) for fl in flds)


def shell(name, V, F, N, T, field=None, lift=0.004):
    """hair as a single outer surface: head + normal * T. Its edge (field = 0, default the T = 0 line) is cut
    smooth and sits right on the skin, so the hair comes out of the head instead of ending in a step. No inner
    wall: nothing ever looks at it from inside the head."""
    if field is None:
        field = T - 1e-4
    Vc, Fc, Nc, Tc = clip(V, F, field, N, T)
    Nc = Nc / np.maximum(np.linalg.norm(Nc, axis=1), 1e-9)[:, None]
    return mesh_object(name, Vc + Nc * (np.maximum(Tc, 0)[:, None] + lift), Fc)


def tube(points, radii, sides=8, twist=0.0, bumps=0.0, bump_freq=6.0):
    """vertices and faces of a tube along points (closed at both ends)"""
    P = [Vector(p) for p in points]
    verts, faces = [], []
    prev_n = None
    for i, p in enumerate(P):
        t = (P[min(i + 1, len(P) - 1)] - P[max(i - 1, 0)]).normalized()
        if prev_n is None:
            a = Vector((0, 0, 1)) if abs(t.z) < 0.9 else Vector((1, 0, 0))
            nrm = t.cross(a).normalized()
        else:
            nrm = (prev_n - t * prev_n.dot(t)).normalized()
        prev_n = nrm
        bi = t.cross(nrm)
        r = radii[i] * (1 + bumps * math.sin(i * bump_freq * 0.5))
        for k in range(sides):
            a = 2 * math.pi * k / sides + twist * i
            verts.append(p + (nrm * math.cos(a) + bi * math.sin(a)) * r)
    for i in range(len(P) - 1):
        for k in range(sides):
            a, b = i * sides + k, i * sides + (k + 1) % sides
            faces.append([a, b, b + sides, a + sides])
    c0 = len(verts)
    verts.append(P[0])
    verts.append(P[-1])
    for k in range(sides):
        faces.append([c0, (k + 1) % sides, k])
        last = (len(P) - 1) * sides
        faces.append([c0 + 1, last + k, last + (k + 1) % sides])
    return verts, faces


class Builder:
    """collects verts/faces of several pieces into one mesh"""
    def __init__(self):
        self.v, self.f = [], []

    def add(self, verts, faces):
        o = len(self.v)
        self.v += [tuple(x) for x in verts]
        self.f += [[i + o for i in f] for f in faces]

    def add_obj(self, ob):
        me = ob.data
        self.add([v.co[:] for v in me.vertices], [list(p.vertices) for p in me.polygons])
        bpy.data.objects.remove(ob, do_unlink=True)

    def make(self, name):
        return mesh_object(name, self.v, self.f)


def push_out(H, p, clear, extra=None):
    """keep a point at least `clear` outside the head (and outside extra bodies)"""
    loc, nrm, fi, d = H.nearest(p)
    q = Vector(p)
    v = q - Vector(loc)
    if v.dot(Vector(nrm)) < clear:
        q = Vector(loc) + Vector(nrm) * clear
    if extra is not None:
        loc, nrm, fi, d = extra.find_nearest(q)
        if loc is not None and (q - loc).dot(nrm) < clear:
            q = loc + nrm * clear
    return np.array(q)


def strand(H, root, direction, length, step=0.04, gravity=0.18, clear=0.03, stiff=0.85, extra=None, wobble=0.0, seed=0):
    """a hanging strand from root: starts along direction, falls under gravity, slides over the head"""
    pts = [np.array(root)]
    d = np.array(direction, float)
    d /= np.linalg.norm(d)
    n = max(3, int(length / step))
    r = random.Random(seed)
    for i in range(n):
        d = stiff * d + (1 - stiff) * np.array([0, 0, -1.0]) * (1 + gravity * i)
        if wobble:
            d += np.array([r.uniform(-1, 1), r.uniform(-1, 1), 0]) * wobble
        d /= np.linalg.norm(d)
        p = pts[-1] + d * step
        p = push_out(H, p, clear, extra)
        d = p - pts[-1]
        if np.linalg.norm(d) > 1e-6:
            d = d / np.linalg.norm(d)
        pts.append(p)
    return pts


# ------------------------------------------------------------------------------------------------ hair styles
def head_frame(H, V):
    """per-vertex helpers in head space: height above the ears, side-ness, front/back, crown angle"""
    c = H.centre
    rel = V - c
    up = rel[:, 2]
    side = np.abs(rel[:, 0])
    back = rel[:, 1]                      # + = back of the head (the face looks along -Y)
    crown = np.array([0.0, c[1] + 0.22 * H.R, H.top - 0.06])
    return rel, up, side, back, crown


def combed(V, N, origin, freq, amp, T, axis_mode="radial", along=None):
    """grooves that run away from origin (a crown or a part line): strands, not a smooth cap"""
    rel = V - origin
    if axis_mode == "radial":
        ang = np.arctan2(rel[:, 0], rel[:, 1])
        g = np.sin(ang * freq + noise(V, 6.0) * 1.3)
    else:                                 # lines parallel to `along` (e.g. combed back)
        perp = np.cross(N, along)
        u = np.einsum("ij,ij->i", rel, perp)
        g = np.sin(u * freq + noise(V, 5.0) * 1.2)
    g = 0.5 + 0.5 * g
    return T * (1 - amp + amp * g) + amp * 0.35 * T * noise(V, 14.0)


def style_short(H, V, F, S, N, d, p):
    """short and medium cuts on the scalp: buzz, crop, fade, side part, curly top"""
    rel, up, side, back, crown = head_frame(H, V)
    R = H.R
    front = smoothstep(0.15 * H.R, 0.7 * H.R, -(V[:, 1] - H.centre[1])) * smoothstep(-0.2 * H.R, 0.3 * H.R, V[:, 2] - H.anchor[2])
    hl = d + p.get("hairline", 0.0) - FRONT_RAISE * front   # forehead hairline up where a real one sits
    feather = p.get("feather", 0.06)
    cover = smoothstep(0.0, feather * (1 + 1.2 * front), hl)
    top_w = smoothstep(p.get("top_from", 0.15) * R, 0.6 * R, up)   # 0 below the temples, 1 on top
    T = p["side"] + (p["top"] - p["side"]) * top_w
    if p.get("puff"):                                    # a round cloud of curls around the head
        c = H.centre + np.array([0, 0.3 * R, 0.3 * R])
        rr = np.array(p["puff"]) * R
        q = (V - c) / rr
        nq = np.linalg.norm(q, axis=1)
        dist = np.linalg.norm(V - c, axis=1)
        T = np.maximum(0.03, dist / np.maximum(nq, 1e-6) - dist)
    if "fade_z" in p:                                    # skin fade: sides and back thin to nothing below a line
        fz = H.ear_z + p["fade_z"]
        T = T * smoothstep(fz - 0.10, fz + 0.06, V[:, 2] + 0.03 * noise(V, 9))
    if p.get("front_lift"):                              # a little more height at the front (the crop in the reference)
        T += p["front_lift"] * smoothstep(0.0, 0.5 * R, -back) * top_w
    if p.get("part") is not None:                        # side part: a combed line, hair swept away from it
        px = p["part"] * R
        dist = np.abs(rel[:, 0] - px)
        T *= 1 - 0.75 * np.exp(-(dist / 0.025) ** 2) * top_w * (rel[:, 1] < 0.35 * R)
        T += p.get("sweep", 0.0) * top_w * smoothstep(0.0, 0.5 * R, -(rel[:, 0] - px) * np.sign(p["part"]))
        T = combed(V, N, np.array([px, 0, 0]), 0, p.get("groove", 0.25), T, "lines", np.array([0, 1.0, 0]))
    elif p.get("curls"):
        bumps = np.zeros(len(V))
        r2 = random.Random(3)
        top_pts = V[(up > 0.1 * R) & (hl > 0.04)]
        for _ in range(p["curls"]):
            q = top_pts[r2.randrange(len(top_pts))]
            bumps += np.exp(-np.sum((V - q) ** 2, 1) / (p.get("curl_r", 0.05) ** 2))
        k = p.get("curl_amp", 0.5)
        T = T * (1 - k / 2 + k * np.clip(bumps, 0, 1.2)) + 0.012 * noise(V, 22)
    else:
        T = combed(V, N, crown, p.get("freq", 26), p.get("groove", 0.3), T)
    T = np.maximum(T, 0) * cover
    return T, hl


def fade_band(name, V, F, N, hl, T, p, width=0.06):
    """the soft hairline: a thin see-through layer in the hair colour around the edge of the solid hair (and over
    the whole faded part of a fade), the way skin shows through short hair at the hairline"""
    feather = p.get("feather", 0.06)
    field = np.minimum(hl + width, (feather + 0.03) - hl)
    if "fade_z" in p:
        field = np.maximum(field, np.minimum(hl, 0.02 - T))     # the faded sides: shadow where the hair is gone
    return shell(name, V, F, N, np.zeros(len(V)), field=field, lift=0.002)


FRONT_RAISE = 0.11


def cap_version(H, V, T, p):
    """under a hat: everything above the cap line pressed flat (the hat covers it), the rest unchanged"""
    rel = V - H.centre
    capline = H.anchor[2] + 0.28 + 0.25 * np.clip(rel[:, 1] / H.R, -1, 1) * 0.6
    T2 = T.copy()
    over = V[:, 2] > capline - 0.04
    T2[over] = np.minimum(T2[over], 0.012)
    return T2


def build_styles(H):
    """every hair style for this head -> {name: {"hair": obj, "fade": obj|None, "cap": obj, "kind": ...}}"""
    V, F, S, N = fine_surface(H, H.ear_z - 0.45, levels=2)
    d = signed_hairline(V, F, S)
    out = {}
    male = H.gender == "Male"

    def add_short(key, label, p, extras=None):
        T, hl = style_short(H, V, F, S, N, d, p)
        edge = np.minimum(hl / p.get("feather", 0.06), (T - 0.003) / 0.01)
        hair = shell(f"Hair_{key}", V, F, N, T, field=edge)
        if extras:
            b = Builder()
            b.add_obj(hair)
            extras(b, T)
            hair = b.make(f"Hair_{key}")
        Tc = cap_version(H, V, T, p)
        cap = shell(f"Hair_{key}_Cap", V, F, N, Tc, field=np.minimum(hl / p.get("feather", 0.06), (Tc - 0.003) / 0.01))
        if extras and p.get("cap_extras", True):
            b = Builder()
            b.add_obj(cap)
            extras(b, T, capped=True)
            cap = b.make(f"Hair_{key}_Cap")
        fade = fade_band(f"Hair_{key}_Fade", V, F, N, hl, T, p)
        out[key] = {"label": label, "hair": hair, "cap": cap, "fade": fade}

    if male:
        add_short("Buzz", "Buzz Cut", dict(top=0.016, side=0.012, feather=0.05, groove=0.15, freq=40))
        add_short("Crop", "Short Crop", dict(top=0.06, side=0.02, front_lift=0.025, feather=0.08, groove=0.2, freq=44))
        add_short("TaperFade", "Low Taper Fade", dict(top=0.09, side=0.02, fade_z=0.02, feather=0.06, groove=0.3, freq=26))
        add_short("HighFade", "High Skin Fade", dict(top=0.10, side=0.02, fade_z=0.22, feather=0.06, groove=0.3, freq=24))
        add_short("SidePart", "Side Part", dict(top=0.10, side=0.025, part=0.32, sweep=0.03, feather=0.07, groove=0.28))
        add_short("CurlyTop", "Curly Top", dict(top=0.12, side=0.018, fade_z=0.05, curls=70, curl_r=0.055, feather=0.06))
    else:
        add_short("Pixie", "Pixie Cut", dict(top=0.07, side=0.03, part=0.25, sweep=0.03, feather=0.06, groove=0.28))

    # --- locs / twists: a short base, then real strands that hang (the front ones fall over the eyes)
    def locs_extras(length, n_front, n_all, radius, front_len):
        def ex(b, T, capped=False):
            r2 = random.Random(11)
            cand = np.where((T > 0.012))[0]
            r2.shuffle(cand)
            rel = V - H.centre
            chosen = []
            for i in cand:
                if all(np.linalg.norm(V[i] - V[j]) > 0.075 for j in chosen):
                    chosen.append(i)
                if len(chosen) >= n_all:
                    break
            for k, i in enumerate(chosen):
                root = V[i] + N[i] * (T[i] * 0.6)
                if capped and V[i][2] > H.anchor[2] + 0.2:
                    continue
                is_front = rel[i][1] < -0.25 * H.R and rel[i][2] > 0.1
                L = front_len if is_front else length
                L *= 0.85 + 0.3 * r2.random()
                crown = np.array([0.0, H.centre[1] + 0.15 * H.R, H.top])
                flow = V[i] - crown
                flow -= N[i] * np.dot(flow, N[i])
                flow /= max(np.linalg.norm(flow), 1e-9)
                dir0 = flow * 0.85 + N[i] * 0.2
                pts = strand(H, root, dir0, L, step=0.035, gravity=0.06, clear=radius * 1.25, stiff=0.88,
                             wobble=0.05, seed=k, extra=SHOULDERS[H.gender])
                rad = [radius * (1.0 - 0.35 * (j / len(pts)) ** 2) for j in range(len(pts))]
                vv, ff = tube(pts, rad, sides=7, twist=0.6, bumps=0.08, bump_freq=5.0)
                b.add(vv, ff)
        return ex

    base = dict(top=0.03, side=0.02, feather=0.05, groove=0.2, freq=34)
    if male:
        add_short("Locs", "Shoulder Locs", base, locs_extras(1.1, 12, 70, 0.034, 0.75))
        add_short("Twists", "Short Twists Over Eyes", dict(base, fade_z=0.05), locs_extras(0.45, 14, 85, 0.03, 0.5))
    else:
        add_short("Locs", "Long Locs", base, locs_extras(1.8, 10, 80, 0.032, 0.8))

    # --- women: slick centre part with a low bun (the reference), ponytail, long straight, bob
    if not male:
        slick = dict(top=0.035, side=0.028, part=0.0, sweep=0.0, feather=0.05, groove=0.35)
        nape = np.array([0.0, H.centre[1] + 0.9 * H.R, H.ear_z - 0.12])

        def bun(b, T, capped=False):
            c = nape + np.array([0, 0.08, 0])
            bm = bmesh.new()
            bmesh.ops.create_uvsphere(bm, u_segments=28, v_segments=18, radius=0.15)
            for v in bm.verts:
                a = math.atan2(v.co.x, v.co.z)
                v.co.y *= 0.72
                v.co *= 1 + 0.06 * math.sin(a * 9 + v.co.y * 40)       # twisted, wrapped look
                v.co += Vector(c)
            vv = [v.co[:] for v in bm.verts]
            ff = [[v.index for v in f.verts] for f in bm.faces]
            bm.free()
            b.add(vv, ff)

        add_short("LowBun", "Slick Low Bun", dict(slick, part=0.0), bun)

        def ponytail(b, T, capped=False):
            root = np.array([0.0, H.centre[1] + 0.85 * H.R, H.anchor[2] + 0.12])
            pts = strand(H, root, [0, 1.0, 0.2], 1.3, step=0.04, gravity=0.25, clear=0.07, stiff=0.75,
                         extra=SHOULDERS[H.gender])
            rad = [0.075 * (1 - 0.6 * (j / len(pts)) ** 1.5) + 0.01 for j in range(len(pts))]
            vv, ff = tube(pts, rad, sides=14, twist=0.15, bumps=0.04)
            b.add(vv, ff)
            vv, ff = tube([root - np.array([0, 0.02, 0]), root + np.array([0, 0.05, 0])], [0.06, 0.06], sides=14)
            b.add(vv, ff)                                              # the hair tie
        add_short("Ponytail", "High Ponytail", dict(slick, part=None), ponytail)

        def curtain(length, flare, curl):
            def ex(b, T, capped=False):
                # one continuous sheet of hair from the scalp past the ears, draped over the back and shoulders.
                # Each column falls straight down from the widest point above it (like real hair over a head and
                # shoulders): radius from the head's vertical axis = running max of the head/body outline + a gap.
                cols, rows = 72, max(10, int(length / 0.03))
                axis = np.array([0.0, H.centre[1]])
                z0 = H.top - 0.01
                body = SHOULDERS[H.gender]
                neck_z = H.J["neck"][2]
                shoulder_z = neck_z - 0.06        # the sides end just above the shoulders and fall behind them

                def outline(a, z):
                    d = np.array([math.sin(a), math.cos(a), 0.0])
                    o = Vector((axis[0] + d[0] * 3, axis[1] + d[1] * 3, z))
                    best = 0.0
                    if abs(a) < math.radians(60):              # the back and the back of the shoulders
                        hit = body.ray_cast(o, Vector(-d), 3.0)
                        if hit[0] is not None:
                            best = 3.0 - hit[3]
                    return max(best, outline_head(a, z))

                def outline_head(a, z):
                    # the head reference still has MakeHuman's A-pose shoulders; only use it above the neck
                    z = max(z, neck_z)
                    d = np.array([math.sin(a), math.cos(a), 0.0])
                    hit = H.bvh.ray_cast(Vector((axis[0] + d[0] * 3, axis[1] + d[1] * 3, z)), Vector(-d), 3.0)
                    return 3.0 - hit[3] if hit[0] is not None else 0.0

                R = np.zeros((cols, rows + 1))
                angs = [math.radians(-110 + 220 * k / (cols - 1)) for k in range(cols)]
                def col_len(a):
                    side = smoothstep(math.radians(28), math.radians(55), abs(a))
                    return length * (1 - side) + min(length, z0 - shoulder_z) * side

                for k, a in enumerate(angs):
                    run = 0.0
                    for j in range(rows + 1):
                        z = z0 - col_len(a) * j / rows
                        run = max(run, outline(a, z))
                        R[k, j] = run
                head_r = np.array([[outline_head(a, z0 - col_len(a) * j / rows) for j in range(rows + 1)] for a in angs])
                R = np.minimum(R, np.maximum.accumulate(head_r, axis=1) + 0.2)   # lies on the back, no shawl
                # hair widens gradually towards a bump below it (the ears), instead of stepping out at it
                for k, a in enumerate(angs):
                    dz = col_len(a) / rows
                    r = R[k].copy()
                    for j in range(rows + 1):
                        below = r[j:] - 0.7 * dz * np.arange(rows + 1 - j)
                        R[k, j] = below.max()
                for _ in range(3):                                     # smooth across the columns
                    R[1:-1] = 0.25 * R[:-2] + 0.5 * R[1:-1] + 0.25 * R[2:]
                jj = np.arange(rows + 1)[None, :] / rows
                R = R + 0.045 + flare * 0.12 * jj ** 1.5
                if curl:
                    R -= 0.06 * smoothstep(0.75, 1.0, jj)
                G = np.zeros((cols, rows + 1, 3))
                for k, a in enumerate(angs):
                    G[k, :, 0] = axis[0] + math.sin(a) * R[k]
                    G[k, :, 1] = axis[1] + math.cos(a) * R[k]
                    G[k, :, 2] = z0 - col_len(a) * jj[0] * (0.975 + 0.015 * math.sin(k * 0.55) + 0.01 * math.sin(k * 1.7 + 0.4))
                outn = np.zeros_like(G)
                for k, a in enumerate(angs):
                    outn[k, :, 0], outn[k, :, 1] = math.sin(a), math.cos(a)
                k_idx = np.arange(cols)[:, None]
                groove = 0.01 * np.sin(k_idx * 2.1) + 0.007 * np.sin(k_idx * 5.3 + 1.0)
                taper = np.linspace(1.0, 0.45, rows + 1)[None, :]
                outer = G + outn * ((groove + 0.03) * taper)[..., None]
                inner = G - outn * 0.008
                nv = cols * (rows + 1)
                verts = list(map(tuple, outer.reshape(-1, 3))) + list(map(tuple, inner.reshape(-1, 3)))
                faces = []
                idx = lambda c, r: c * (rows + 1) + r
                for c2 in range(cols - 1):
                    for r in range(rows):
                        q = [idx(c2, r), idx(c2, r + 1), idx(c2 + 1, r + 1), idx(c2 + 1, r)]
                        faces.append(q)
                        faces.append([v + nv for v in reversed(q)])
                for r in range(rows):
                    for c2, flip in ((0, False), (cols - 1, True)):
                        q = [idx(c2, r), idx(c2, r) + nv, idx(c2, r + 1) + nv, idx(c2, r + 1)]
                        faces.append(q[::-1] if flip else q)
                for c2 in range(cols - 1):
                    q = [idx(c2, rows), idx(c2, rows) + nv, idx(c2 + 1, rows) + nv, idx(c2 + 1, rows)]
                    faces.append(q[::-1])
                b.add(verts, faces)
            return ex
        add_short("LongStraight", "Long Straight", dict(slick, top=0.05, side=0.04, groove=0.3),
                  curtain(1.9, 0.25, False))
        add_short("Bob", "Chin Bob", dict(slick, top=0.06, side=0.045, part=0.2, groove=0.3), curtain(1.0, 0.45, True))
    return out, (V, F, S, N, d)


# ------------------------------------------------------------------------------------------------ face pieces
def onto_face(H, p, lift):
    """the face straight behind p (looking along +Y, the way the face points), lifted off the skin. Falls back to
    the nearest point (never the nose tip: p is moved close to the face first)."""
    q = np.array(p, float)
    hit = H.bvh.ray_cast(Vector((q[0], q[1] - 0.5, q[2])), Vector((0, 1, 0)), 1.5)
    if hit[0] is not None:
        loc, nrm = np.array(hit[0]), np.array(hit[1])
    else:
        loc, nrm, fi, d = H.nearest(q)
    return loc + nrm * lift


def strip(H, centre_pts, widths, lift, depth=0.004):
    """a thin ribbon lying on the face along centre_pts (each with its width), with a little thickness"""
    n = len(centre_pts)
    top, bot = [], []
    for i, (c, w) in enumerate(zip(centre_pts, widths)):
        a = centre_pts[min(i + 1, n - 1)] - centre_pts[max(i - 1, 0)]
        loc, nrm, fi, d = H.nearest(c)
        side = np.cross(nrm, a)
        side /= max(np.linalg.norm(side), 1e-9)
        if side[2] < 0:
            side = -side
        top.append(onto_face(H, c + side * w * 0.45, lift))
        bot.append(onto_face(H, c - side * w * 0.55, lift))
    verts = top + bot
    faces = [[i, n + i, n + i + 1, i + 1] for i in range(n - 1)]
    under = [onto_face(H, v, lift - depth) for v in verts]
    faces2 = [[f[3] + 2 * n, f[2] + 2 * n, f[1] + 2 * n, f[0] + 2 * n] for f in faces]
    # close the long edges so it reads as a solid from the side
    rim = [[i, i + 1, 2 * n + i + 1, 2 * n + i] for i in range(n - 1)] + \
          [[n + i + 1, n + i, 3 * n + i, 3 * n + i + 1] for i in range(n - 1)]
    return verts + under, faces + faces2 + rim


def face_pieces(H):
    """brows (5 styles), lash lines, lips, stubble (2): thin layers that follow the face"""
    c = H.co
    out = {}
    eyes = {"L": H.eyeL, "R": H.eyeR}
    BROWS = {  # (inner width, peak width, tail width, arch, length, gap from the middle, lift)
        "Natural": (0.034, 0.03, 0.012, 0.022, 0.20, 0.055, 0.0),
        "Thick": (0.046, 0.042, 0.018, 0.018, 0.21, 0.05, 0.0),
        "Arched": (0.03, 0.024, 0.008, 0.042, 0.195, 0.06, 0.008),
        "Straight": (0.036, 0.032, 0.014, 0.006, 0.20, 0.052, -0.004),
        "Thin": (0.02, 0.016, 0.006, 0.03, 0.19, 0.06, 0.008),
    }
    for name, (w_in, w_pk, w_tail, arch, length, gap, lift) in BROWS.items():
        b = Builder()
        for s, sx in (("L", 1), ("R", -1)):
            e = eyes[s]
            n = 16
            pts, ws = [], []
            for i in range(n):
                t = i / (n - 1)
                x = sx * (gap + length * t)
                rise = arch * math.sin(math.pi * min(1.0, t / 0.7) * 0.5) if t < 0.7 else arch * (1 - 1.6 * (t - 0.7))
                z = e[2] + 0.1 + lift + rise
                pts.append(onto_face(H, np.array([x, e[1] - 0.3, z]), 0.0))
                w = w_in + (w_pk - w_in) * min(1, t / 0.6) if t < 0.6 else w_pk + (w_tail - w_pk) * (t - 0.6) / 0.4
                ws.append((1.15 if H.gender == "Male" else 0.85) * w * (0.55 + 0.45 * min(1.0, t * 6)))           # soft inner start
            vv, ff = strip(H, pts, ws, 0.005)
            b.add(vv, ff)
        out["Brows_" + name] = b.make("Brows_" + name)
    # lash lines: a fine dark line along each upper lid
    b = Builder()
    for s, sx in (("L", 1), ("R", -1)):
        e = eyes[s]
        pts = []
        for i in range(12):
            t = i / 11
            x = e[0] + sx * (-0.05 + 0.105 * t)
            z = e[2] + 0.004 + 0.024 * math.sin(math.pi * (0.1 + 0.8 * t))
            pts.append(onto_face(H, np.array([x, e[1] - 0.3, z]), 0.003))
        vv, ff = tube(pts, [0.0045 * (0.4 + 0.6 * math.sin(math.pi * j / 11)) for j in range(12)], sides=5)
        b.add(vv, ff)
    out["LashLine"] = b.make("LashLine")
    # lips: MakeHuman's lip region as a skin-tight layer (Character Studio tints it from the skin tone)
    m = H.mask["lips"]
    fs = [f for f in H.faces if all(m[v] for v in f)]
    used = sorted({v for f in fs for v in f})
    rm = {v: i for i, v in enumerate(used)}
    N = H.normals
    out["Lips"] = mesh_object("Lips", c[used] + N[used] * 0.002, [[rm[v] for v in f] for f in fs])
    if H.gender != "Male":
        return out
    # stubble / beard shadow: jaw, chin, upper lip and the top of the neck, with soft, natural edges
    V, F, S, Nf = fine_surface(H, H.J["neck"][2] - 0.3, levels=1)
    rel = V - H.centre
    kd = KDTree(len(H.lips))
    for i, p in enumerate(H.lips):
        kd.insert(p, i)
    kd.balance()
    lipd = np.array([kd.find(v)[2] for v in V])
    for name, up, down in (("Stubble", 0.0, 0.0), ("StubbleHeavy", 0.035, 0.06)):
        # the beard line: under the nose in the middle (the moustache), down to just above the mouth corners, then
        # up the cheek to the sideburns; never over the nose or the upper cheeks
        ax = np.abs(V[:, 0] - H.anchor[0])
        nose_bottom = H.nose_tip[2] - 0.035
        centre = np.where(ax < 0.075, nose_bottom, nose_bottom - (ax - 0.075) * 1.2)
        side = H.mouth[2] + 0.035 + np.clip(ax - 0.11, 0, None) / max(0.85 * H.R - 0.11, 1e-3) * \
            (H.ear_z + 0.02 - H.mouth[2] - 0.035)
        cheek = (np.maximum(centre, side) + up) - V[:, 2]                                   # below the beard line
        neck = V[:, 2] - (H.chin[2] - 0.11 - down) + 0.008 * noise(V, 24)                    # above the neckline
        front = 0.3 * H.R - rel[:, 1]                                                        # in front of the ears
        lips = lipd - 0.012
        sideburn = np.where(rel[:, 1] > -0.1 * H.R, (H.ear_z + 0.05 + up) - V[:, 2], 1.0)
        field = np.minimum.reduce([cheek + 0.01 * noise(V, 30), neck, front, lips, sideburn])
        out[name] = shell(name, V, F, Nf, np.zeros(len(V)), field=field, lift=0.0025)
    return out


# ------------------------------------------------------------------------------------------------ face bones
def face_landmarks(H):
    """where the face bones sit (head space, Blender axes) and how far each one reaches"""
    J = H.J
    c = H.co
    L = {}
    for s, e, sx in (("L", H.eyeL, 1), ("R", H.eyeR, -1)):
        L["NC_FaceEye" + s] = (e, 0.11)
        L["NC_FaceBrow" + s] = (e + np.array([sx * 0.02, -0.03, 0.12]), 0.10)
        L["NC_FaceCheek" + s] = (e + np.array([sx * 0.07, 0.0, -0.13]), 0.13)
        L["NC_FaceNostril" + s] = (H.nose_tip + np.array([sx * 0.05, 0.05, -0.03]), 0.05)
        L["NC_FaceMouth" + s] = (H.mouth_l if sx > 0 else H.mouth_r, 0.06)
        jaw = np.array([sx * 0.26 * H.R / 0.41, H.centre[1] - 0.05, H.mouth[2] - 0.06])
        L["NC_FaceJaw" + s] = (H.nearest(jaw)[0], 0.16)
        ear = c[H.mask["ears"] & ((c[:, 0] > 0) if sx > 0 else (c[:, 0] < 0))]
        if len(ear):
            L["NC_FaceEar" + s] = (ear.mean(0), 0.14)
    L["NC_FaceNose"] = (H.nose_tip - np.array([0, -0.01, 0.01]), 0.07)
    L["NC_FaceNoseBridge"] = (H.anchor + np.array([0, -0.09, -0.02]), 0.06)
    lips = H.lips
    L["NC_FaceLipUpper"] = (lips[lips[:, 2] > H.mouth[2]].mean(0), 0.045)
    L["NC_FaceLipLower"] = (lips[lips[:, 2] <= H.mouth[2]].mean(0), 0.045)
    L["NC_FaceChin"] = (H.chin, 0.11)
    return L


# ------------------------------------------------------------------------------------------------ run
def rbx(p):
    return (-p[0], p[2], p[1])


SHOULDERS = {}
DATA = {}
for gender in ("Male", "Female"):
    H = Head(gender)
    # shoulders and back for long hair to rest on: the rigged body in its rest pose (arms hanging), which has
    # exactly the same head as the MakeHuman source
    rig_blend = os.environ.get("NC_RIG_BLEND", os.path.join(OUT, "NeonCoast_MakeHumanRig.blend"))
    with bpy.data.libraries.load(rig_blend) as (src_lib, dst_lib):
        dst_lib.meshes = [f"{gender}_Average_Whole"]
    me = dst_lib.meshes[0]
    co = np.array([v.co[:] for v in me.vertices])
    fs = [list(p.vertices) for p in me.polygons]
    SHOULDERS[gender] = BVHTree.FromPolygons([tuple(v) for v in co], fs)
    styles, fine = build_styles(H)
    face = face_pieces(H)
    marks = face_landmarks(H)
    A = H.anchor
    pieces = {}
    hair_col = material("Hair", (0.09, 0.06, 0.04, 1))
    fade_col = material("HairFade", (0.09, 0.06, 0.04, 1))
    for key, st in styles.items():
        for kind in ("hair", "cap", "fade"):
            ob = st[kind]
            ob.data.materials.append(fade_col if kind == "fade" else hair_col)
            pieces[ob.name] = (ob, {"hair": "Hair", "cap": "HairCap", "fade": "HairFade"}[kind], key, st["label"])
    for name, ob in face.items():
        kind = name.split("_")[0]
        col = {"Brows": hair_col, "LashLine": material("Lash", (0.03, 0.025, 0.02, 1)),
               "Lips": material("Lip", (0.62, 0.36, 0.33, 1)), "Stubble": material("Stub", (0.09, 0.07, 0.05, 1)),
               "StubbleHeavy": material("Stub", (0.09, 0.07, 0.05, 1))}[kind]
        ob.data.materials.append(col)
        LABELS = {"Brows_Natural": "Natural", "Brows_Thick": "Thick", "Brows_Arched": "Arched",
                  "Brows_Straight": "Straight", "Brows_Thin": "Thin", "LashLine": "Lash Line", "Lips": "Lips",
                  "Stubble": "Stubble", "StubbleHeavy": "Heavy Stubble"}
        pieces[name] = (ob, kind, name.split("_")[-1], LABELS.get(name, name))
    for name, (ob, kind, key, label) in pieces.items():      # Roblox: at most 20,000 triangles per MeshPart
        tris = sum(len(p.vertices) - 2 for p in ob.data.polygons)
        if tris > 18000:
            md = ob.modifiers.new("D", "DECIMATE")
            md.ratio = 17000 / tris
            bpy.context.view_layer.objects.active = ob
            bpy.ops.object.select_all(action="DESELECT")
            ob.select_set(True)
            bpy.ops.object.modifier_apply(modifier=md.name)
    # every piece measured from the eyes' midpoint; Roblox puts a MeshPart's pivot at its bounding-box centre
    info = []
    for name, (ob, kind, key, label) in pieces.items():
        vs = np.array([v.co[:] for v in ob.data.vertices])
        lo, hi = vs.min(0), vs.max(0)
        centre = (lo + hi) / 2
        ob.data.transform(Matrix.Translation(Vector(-A)))
        ob.location = Vector(A)
        info.append({"mesh": name, "kind": kind, "key": key, "label": label,
                     "offset": [round(x, 4) for x in rbx(centre - A)],
                     "size": [round(x, 4) for x in (hi - lo)[[0, 2, 1]]], "tris": sum(len(p.vertices) - 2 for p in ob.data.polygons)})
        ob.name = f"{gender}_{name}"
        ob.data.name = name
    DATA[gender] = {"pieces": info,
                    "bones": {b: {"at": [round(x, 4) for x in rbx(p - A)], "reach": r} for b, (p, r) in marks.items()},
                    "eyeMid": [round(x, 4) for x in rbx(A)],
                    "eyeSpan": float(np.linalg.norm(H.eyeL - H.eyeR))}
    # export (meshes named exactly as Lua looks them up)
    bpy.ops.object.select_all(action="DESELECT")
    for name, (ob, *_r) in pieces.items():
        ob.select_set(True)
    olds = {}
    for name, (ob, *_r) in pieces.items():
        olds[ob] = ob.name
        ob.name = name
    bpy.context.view_layer.objects.active = next(iter(pieces.values()))[0]
    bpy.ops.export_scene.fbx(filepath=os.path.join(OUT, f"NC_Head_{gender}.fbx"), use_selection=True, object_types={"MESH"},
                             apply_scale_options="FBX_SCALE_UNITS", mesh_smooth_type="FACE", path_mode="COPY")
    for ob, n in olds.items():
        ob.name = n
    print("NC_HEAD", gender, len(pieces), "pieces", sum(i["tris"] for i in info), "tris")


# ------------------------------------------------------------------------------------------------ Lua data
def lv(c):
    return f"Vector3.new({c[0]:.4f}, {c[1]:.4f}, {c[2]:.4f})"


L = ["-- NCHeadData (ModuleScript, ReplicatedStorage): generated by build_heads.py. Do not hand-edit; re-run it.",
     "-- Hair styles and face pieces for the MakeHuman heads (NC_Head_<Gender>.fbx, imported into",
     "-- ReplicatedStorage.NC_HeadAssets.<Gender>). offset = the piece's centre from the point between the eyes (studs,",
     "-- Roblox axes). bones = the face bones' rest positions from the same point, for the face shape sliders.",
     "local D = {}"]
for gender, d in DATA.items():
    L.append(f"D.{gender} = {{")
    L.append("\tpieces = {")
    for i in d["pieces"]:
        L.append(f"\t\t[\"{i['mesh']}\"] = {{ kind = \"{i['kind']}\", key = \"{i['key']}\", label = \"{i['label']}\", "
                 f"offset = {lv(i['offset'])}, size = {lv(i['size'])} }},")
    L.append("\t},")
    L.append("\tbones = {")
    for b, x in d["bones"].items():
        L.append(f"\t\t{b} = {lv(x['at'])},")
    L.append("\t},")
    L.append(f"\teyeSpan = {d['eyeSpan']:.4f},")
    L.append("}")
L.append("return D")
L.append("")
with open(os.path.join(OUT, "NCHeadData.lua"), "w", encoding="utf-8") as f:
    f.write("\n".join(L))
with open(os.path.join(OUT, "heads.json"), "w") as f:
    json.dump(DATA, f, indent=1)
ASSEMBLE = """-- AssembleHeads (generated by build_heads.py): run once in Studio's command bar, after importing
-- NC_Head_Male.fbx and NC_Head_Female.fbx with the 3D Importer. Select both imported models, paste this, press Enter.
-- The pieces go to ReplicatedStorage.NC_HeadAssets.<Gender>, where NCHead (the Character Studio) finds them.
local Selection = game:GetService("Selection")
local RS = game:GetService("ReplicatedStorage")
local root = RS:FindFirstChild("NC_HeadAssets") or Instance.new("Folder")
root.Name = "NC_HeadAssets"
root.Parent = RS
local done = 0
for _, model in ipairs(Selection:Get()) do
\tlocal gender = model.Name:match("NC_Head_(%a+)")
\tif not gender then
\t\twarn("AssembleHeads: keep NC_Head_<Gender> in the name of " .. model.Name)
\t\tcontinue
\tend
\tlocal old = root:FindFirstChild(gender)
\tif old then
\t\told:Destroy()
\tend
\tlocal folder = Instance.new("Folder")
\tfolder.Name = gender
\tfor _, part in ipairs(model:GetDescendants()) do
\t\tif part:IsA("MeshPart") then
\t\t\tpart.Anchored = false
\t\t\tpart.CanCollide, part.CanTouch, part.CanQuery, part.Massless = false, false, false, true
\t\t\tpart.CastShadow = false
\t\t\tpart.DoubleSided = false
\t\t\tpart.TextureID = ""
\t\t\tfor _, ch in ipairs(part:GetChildren()) do
\t\t\t\tif not ch:IsA("Attachment") then
\t\t\t\t\tch:Destroy()
\t\t\t\tend
\t\t\tend
\t\t\tpart.Parent = folder
\t\t\tdone += 1
\t\tend
\tend
\tfolder.Parent = root
\tmodel:Destroy()
end
print("AssembleHeads: " .. done .. " hair and face pieces ready in ReplicatedStorage.NC_HeadAssets")
"""
with open(os.path.join(OUT, "AssembleHeads.lua"), "w", encoding="utf-8") as f:
    f.write(ASSEMBLE)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "NeonCoast_Heads.blend"))
print("NC_HEADS_DONE")
