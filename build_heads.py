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
import bpy, bmesh, math, json, os, re, sys, random, zlib
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
import nc_haircards as HC

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


# ------------------------------------------------------------------------------------------------ UVs + textures
# Roblox: each hair / brow / stubble piece gets a SurfaceAppearance (AlphaMode Transparency, tinted by its Color)
# from one shared greyscale texture. U runs across the edge (0 = the very edge, 1 = full coverage), so the
# hairline is made of single strands that thin out onto the skin instead of a hard rim; V runs along the edge.
UVS = {}                      # object name -> (u, v) per vertex
EDGE_TILES = 9                # texture repeats round the head (whole number, so the seam at the back is invisible)


def set_uv(ob, u, v, period=None):
    me = ob.data
    uvl = me.uv_layers.new(name="UVMap")
    loops = np.array([l.vertex_index for l in me.loops])
    # (well inside the texture: the image wraps, so a sample at the very edge blends in the opposite column, and the
    #  bare-skin edge of the shell printed a dotted line of full-hair texels)
    uu = np.clip(np.asarray(u, float)[loops], 0.015, 0.985)
    vv = np.asarray(v, float)[loops].copy()
    if period:
        for poly in me.polygons:
            idx = np.arange(poly.loop_start, poly.loop_start + poly.loop_total)
            if vv[idx].max() - vv[idx].min() > period / 2:
                lo = vv[idx] < vv[idx].mean()
                vv[idx[lo]] += period
    uvl.data.foreach_set("uv", np.stack([uu, vv], 1).ravel())


def edge_v(H, V):
    """V along the hairline: round the head (whole tiles) plus a little height, so a vertical edge still varies"""
    a = np.arctan2(V[:, 0] - H.centre[0], V[:, 1] - H.centre[1])
    return a / (2 * np.pi) * EDGE_TILES + (V[:, 2] - H.anchor[2]) * 2.2


def _save_png(name, rgba):
    n_y, n_x = rgba.shape[:2]
    im = bpy.data.images.get(name) or bpy.data.images.new(name, n_x, n_y, alpha=True)
    im.pixels.foreach_set(np.clip(rgba, 0, 1).astype(np.float32).ravel())
    d = os.path.join(OUT, "textures_heads")
    os.makedirs(d, exist_ok=True)
    im.filepath_raw = os.path.join(d, name + ".png")
    im.file_format = "PNG"
    im.save()
    return im


def make_textures():
    """the shared greyscale maps (rows = V, columns = U)"""
    rng = np.random.default_rng(7)
    T = {}
    # hair edge: 512 strands round one tile; each strand starts at its own point across the edge, so the hairline
    # is a ragged row of single hairs; colour varies strand to strand
    n = 512
    u = (np.arange(n) + 0.5) / n
    strands = 300
    sid = (np.arange(n) * strands // n) % strands
    start = rng.uniform(0.02, 0.6, strands) ** 1.3
    start = 0.5 * start + 0.5 * np.convolve(np.r_[start[-3:], start, start[:3]], np.ones(7) / 7, "same")[3:-3]
    start = np.maximum(start, 0.09)        # (a strand starting right at the edge printed a lone dash on the forehead)
    shade = rng.uniform(0.72, 1.0, strands)
    pos = (np.arange(n) * strands / n) % 1.0                             # across one strand
    core = 1 - np.abs(pos - 0.5) * 2                                      # 1 in the middle of a strand
    st = start[sid][:, None]
    a = np.clip((u[None, :] - st) / 0.16, 0, 1)                           # each strand grows in over a short run
    # near the edge strands are thin and separate but each one is fully opaque: the fade gets thinner (more skin
    # between the hairs), never lighter or browner than the hair colour
    thin = np.clip(core[:, None] * 2.2 + u[None, :] * 1.6, 0, 1)
    alpha = np.clip(a * thin + smoothstep(0.6, 0.85, u)[None, :], 0, 1)
    col = (shade[sid][:, None] * (0.86 + 0.14 * core[:, None])) * np.ones((1, n))
    col = col * (0.92 + 0.08 * np.sin(u[None, :] * 40 + sid[:, None]))
    alpha[:, u < 0.03] = 0.0                                              # (a clear border: no texels at the very edge)
    T["NC_HairEdge"] = np.dstack([col, col, col, alpha])
    # skin fades (hair_ref_1..3): clipper-short hair is not strands but fine dark stubble whose DENSITY falls off down
    # the side of the head; from a step back it reads as an even shadow going from the hair colour to skin. Low U is
    # sparse stubble, it fills in up the fade, and short strands only start near the top where the hair gets longer
    rf = np.random.default_rng(11)                                        # (own seed: brows stay as they were)
    r = rf.random((n, n))
    dens = smoothstep(0.0, 0.62, u) ** 1.25
    dots = (r < dens[None, :]).astype(float)
    dots = np.maximum(dots, np.roll(dots, 1, 1) * 0.85)                  # each hair a tiny dash, down the head
    dots = np.clip(dots + 0.1 * (np.roll(dots, 1, 0) + np.roll(dots, -1, 0)), 0, 1)
    st2 = 0.5 + 0.3 * rf.uniform(0, 1, strands)
    a2 = np.clip((u[None, :] - st2[sid][:, None]) / 0.12, 0, 1) * np.clip(core[:, None] * 2.5, 0, 1)
    falpha = np.clip(np.maximum(dots, a2) + smoothstep(0.6, 0.85, u)[None, :], 0, 1)
    falpha[:, u < 0.08] = 0.0                                             # (np.roll wrapped full-hair dots into column 0)
    fcol = (0.74 + 0.26 * rf.random((n, n))) * (0.9 + 0.1 * smoothstep(0.3, 0.9, u)[None, :])
    # (full hair is one even shade: the crown's UVs barely move, so a speckled column there would print one random
    # light or dark texel over a whole patch of the head)
    fcol = fcol + (0.88 - fcol) * smoothstep(0.8, 0.95, u)[None, :]
    T["NC_HairFade"] = np.dstack([fcol, fcol, fcol, falpha])
    # (stubble maps are made per piece by stubble_texture, from its own coverage)
    # brows: short hairs slanting up towards the tail; U along the brow (inner end 0), V across (0 bottom, 1 top)
    bw, bh = 512, 128
    bu = (np.arange(bw) + 0.5) / bw
    bv = (np.arange(bh) + 0.5) / bh
    UU, VV = np.meshgrid(bu, bv)
    hairs = np.zeros((bh, bw))
    for _ in range(900):
        x0, y0 = rng.uniform(0, 1), rng.uniform(0.05, 0.95)
        ang = math.radians(rng.uniform(12, 35) + 35 * (1 - x0) ** 2)     # inner hairs stand up more
        ln = rng.uniform(0.05, 0.11)
        dx, dy = math.cos(ang) * ln, math.sin(ang) * ln * 4                # (the map is 4x wider than tall)
        t = np.clip(((UU - x0) * dx + (VV - y0) * dy) / (dx * dx + dy * dy), 0, 1)
        dist = np.hypot((UU - x0 - t * dx) * bw, (VV - y0 - t * dy) * bh)
        hairs = np.maximum(hairs, np.clip(1.3 - dist / 1.1, 0, 1) * (0.7 + 0.3 * rng.random()))
    edge = smoothstep(0.0, 0.3, VV) * smoothstep(1.0, 0.65, VV) * smoothstep(0.0, 0.12, UU)
    alpha = np.clip(hairs * edge * 1.2 + 0.35 * edge * smoothstep(0.1, 0.5, VV), 0, 1)
    c = 0.85 + 0.15 * hairs
    T["NC_Brow"] = np.dstack([c, c, c, alpha])
    T.update(HC.make_atlas(OUT))                           # hair cards: strand colour/alpha, normal, roughness
    return {k: _save_png(k, v) for k, v in T.items()}


def card_material(name):
    """hair cards: the strand atlas (greyscale, tinted in Roblox) with its normal and roughness maps"""
    if name in MATS:
        return MATS[name]
    m = tex_material(name, TEX["NC_HairCard_Color"])
    nt = m.node_tree
    b = nt.nodes.get("Principled BSDF")
    nm = nt.nodes.new("ShaderNodeNormalMap")
    tn = nt.nodes.new("ShaderNodeTexImage")
    tn.image = TEX["NC_HairCard_Normal"]
    tn.image.colorspace_settings.name = "Non-Color"
    nt.links.new(tn.outputs["Color"], nm.inputs["Color"])
    nt.links.new(nm.outputs["Normal"], b.inputs["Normal"])
    tr = nt.nodes.new("ShaderNodeTexImage")
    tr.image = TEX["NC_HairCard_Rough"]
    tr.image.colorspace_settings.name = "Non-Color"
    nt.links.new(tr.outputs["Color"], b.inputs["Roughness"])
    return m


def tex_material(name, image):
    """a material whose only texture is this greyscale map (FBX exports it; Roblox tints it)"""
    if name in MATS:
        return MATS[name]
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    b = nt.nodes.get("Principled BSDF")
    tx = nt.nodes.new("ShaderNodeTexImage")
    tx.image = image
    nt.links.new(tx.outputs["Color"], b.inputs["Base Color"])
    nt.links.new(tx.outputs["Alpha"], b.inputs["Alpha"])
    b.inputs["Roughness"].default_value = 0.72
    m["nc_tinted"] = True
    MATS[name] = m
    return m


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


def drop_islands(Fc, nv, min_faces=24):
    """the edge cut leaves tiny islands of hair out on the skin where the hairline noise pokes over zero: they show
    as a dark mark under the hairline. Keep only pieces with a real number of faces."""
    par = list(range(nv))

    def find(a):
        while par[a] != a:
            par[a] = par[par[a]]
            a = par[a]
        return a
    for f in Fc:
        r0 = find(f[0])
        for x in f[1:]:
            r = find(x)
            if r != r0:
                par[r] = r0
    cnt = {}
    roots = [find(f[0]) for f in Fc]
    for r in roots:
        cnt[r] = cnt.get(r, 0) + 1
    return [f for f, r in zip(Fc, roots) if cnt[r] >= min_faces]


def split_cards(ob, limit):
    """split a card object into parts of at most `limit` triangles (cards are quads: 2 tris each), whole cards kept
    together where possible (faces of one card are contiguous). Parts after the first are named <name>_2, _3 ..."""
    me = ob.data
    nf = len(me.polygons)
    per = limit // 2
    if nf <= per:
        return [ob]
    out = [ob]
    bm = bmesh.new()
    bm.from_mesh(me)
    bm.faces.ensure_lookup_table()
    # connected pieces (cards), in order
    seen = set()
    comps = []
    for f in bm.faces:
        if f.index in seen:
            continue
        stack, comp = [f], []
        seen.add(f.index)
        while stack:
            g = stack.pop()
            comp.append(g.index)
            for e in g.edges:
                for h in e.link_faces:
                    if h.index not in seen:
                        seen.add(h.index)
                        stack.append(h)
        comps.append(comp)
    bm.free()
    groups, cur = [], []
    for c in comps:
        if len(cur) + len(c) > per and cur:
            groups.append(cur)
            cur = []
        cur += c
    if cur:
        groups.append(cur)
    base = ob.name
    for gi in range(len(groups) - 1, -1, -1):
        keep = set(groups[gi])
        tgt = ob if gi == 0 else ob.copy()
        if gi > 0:
            tgt.data = ob.data.copy()
            tgt.name = f"{base}_{gi + 1}"
            for c in ob.users_collection:
                c.objects.link(tgt)
        bm = bmesh.new()
        bm.from_mesh(tgt.data)
        bm.faces.ensure_lookup_table()
        bmesh.ops.delete(bm, geom=[f for f in bm.faces if f.index not in keep], context="FACES")
        bm.to_mesh(tgt.data)
        bm.free()
        if gi > 0:
            out.insert(1, tgt)
    return out


def shell(name, V, F, N, T, field=None, lift=0.004, uv=None):
    """hair as a single outer surface: head + normal * T. Its edge (field = 0, default the T = 0 line) is cut
    smooth and sits right on the skin, so the hair comes out of the head instead of ending in a step. No inner
    wall: nothing ever looks at it from inside the head. uv = (u, v) per vertex for the edge texture."""
    if field is None:
        field = T - 1e-4
    if uv is None:
        Vc, Fc, Nc, Tc = clip(V, F, field, N, T)
    else:
        Vc, Fc, Nc, Tc, Uc, Wc = clip(V, F, field, N, T, uv[0], uv[1])
    Nc = Nc / np.maximum(np.linalg.norm(Nc, axis=1), 1e-9)[:, None]
    Fc = drop_islands(Fc, len(Vc))
    ob = mesh_object(name, Vc + Nc * (np.maximum(Tc, 0)[:, None] + lift), Fc)
    if uv is not None:
        UVS[ob.name] = (Uc, Wc)
        set_uv(ob, Uc, Wc, EDGE_TILES)
    return ob


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


def rope(points, radii, turns=30.0, normals=None, flat=1.0, sides=6):
    """a two-strand twist along points: two tubes wound round each other (turns per stud along the path).
    normals + flat < 1: the twist is pressed flat against the scalp (flat twists)"""
    P = [np.array(p, float) for p in points]
    out = []
    L = np.concatenate([[0], np.cumsum([np.linalg.norm(P[i + 1] - P[i]) for i in range(len(P) - 1)])])
    # resample finely so the strands wind smoothly
    n = max(8, int(L[-1] / 0.008))
    ts = np.linspace(0, L[-1], n)
    Q = np.array([np.interp(ts, L, [p[k] for p in P]) for k in range(3)]).T
    R = np.interp(ts, L, radii)
    if normals is not None:
        NN = np.array([np.interp(ts, L, [n_[k] for n_ in normals]) for k in range(3)]).T
    tang = np.gradient(Q, axis=0)
    tang /= np.maximum(np.linalg.norm(tang, axis=1), 1e-9)[:, None]
    ref = np.array([0.0, 0.0, 1.0])
    for s_ in (0.0, math.pi):
        pts, rr = [], []
        prev = None
        for j in range(n):
            t = tang[j]
            a = ref if abs(t @ ref) < 0.9 else np.array([1.0, 0, 0])
            if normals is not None:
                e2 = NN[j] - t * (NN[j] @ t)
                e2 /= max(np.linalg.norm(e2), 1e-9)
                e1 = np.cross(e2, t)
            else:
                e1 = np.cross(t, a) if prev is None else prev - t * (prev @ t)
                e1 /= max(np.linalg.norm(e1), 1e-9)
                prev = e1
                e2 = np.cross(t, e1)
            ang = s_ + ts[j] * turns
            pts.append(Q[j] + (e1 * math.cos(ang) + e2 * math.sin(ang) * flat) * R[j] * 0.38)
            rr.append(R[j] * 0.62)
        out.append(tube(pts, rr, sides=sides))
    return out


class Builder:
    """collects verts/faces of several pieces into one mesh"""
    def __init__(self):
        self.v, self.f, self.u, self.w = [], [], [], []

    def add(self, verts, faces, u=None, w=None):
        o = len(self.v)
        self.v += [tuple(x) for x in verts]
        self.f += [[i + o for i in f] for f in faces]
        k = len(verts)
        self.u += list(u) if u is not None else [0.996] * k      # (strands, locs, sheets: full coverage)
        self.w += list(w) if w is not None else [0.5] * k

    def add_obj(self, ob):
        me = ob.data
        u, w = UVS.pop(ob.name, (None, None))
        self.add([v.co[:] for v in me.vertices], [list(p.vertices) for p in me.polygons], u, w)
        bpy.data.objects.remove(ob, do_unlink=True)

    def make(self, name, uv=True):
        ob = mesh_object(name, self.v, self.f)
        if uv:
            UVS[ob.name] = (np.array(self.u), np.array(self.w))
            set_uv(ob, self.u, self.w, EDGE_TILES)
        return ob


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


def drape(H, root, length, clear, body, step=0.035, seed=0, sway=0.0):
    """a loc that hangs the way real hair does: it lies on the head, falls straight down from the widest point
    above it, and slides off the shoulders to the back or the front instead of piling up on them"""
    r = random.Random(seed)
    clear *= r.uniform(1.0, 1.9)                             # locs stack on each other: some sit higher
    cy = H.centre[1]
    neck_z = H.J["neck"][2]

    def outline(a, z):
        d = np.array([math.sin(a), math.cos(a)])
        best = 0.0
        zh = max(z, neck_z)
        hit = H.bvh.ray_cast(Vector((d[0] * 3, cy + d[1] * 3, zh)), Vector((-d[0], -d[1], 0)), 3.0)
        if hit[0] is not None:
            best = 3.0 - hit[3]
        if z < neck_z + 0.1:
            hit = body.ray_cast(Vector((d[0] * 3, cy + d[1] * 3, z)), Vector((-d[0], -d[1], 0)), 3.0)
            if hit[0] is not None:
                best = max(best, 3.0 - hit[3])
        return best

    a = math.atan2(root[0], root[1] - cy)
    rad = math.hypot(root[0], root[1] - cy)
    z = root[2]
    pts = [np.array(root, float)]
    drift = r.uniform(-1, 1) * sway
    travelled = 0.0
    while travelled < length:
        z_new = z - step * 0.97
        a_new = a + drift * step
        side = math.radians(40) < abs(a_new) < math.radians(140)
        # just off the shoulder, behind it or in front of it (never all gathered at the spine)
        target = math.copysign(math.radians(38) if abs(a_new) < math.pi / 2 else math.radians(142), a_new)
        if z_new < neck_z + 0.2 and side:
            a_new += (target - a_new) * 0.1
        want = outline(a_new, z_new) + clear
        tries = 0
        while side and want > rad + step * 0.8 and z_new < neck_z + 0.1 and tries < 6:
            a_new += (target - a_new) * 0.35                 # blocked by the shoulder: go round it, don't jump out
            want = outline(a_new, z_new) + clear
            tries += 1
        rad_new = max(want, rad - step * 0.35)               # falls straight; only leans in a little
        p = np.array([math.sin(a_new) * rad_new, cy + math.cos(a_new) * rad_new, z_new])
        travelled += np.linalg.norm(p - pts[-1])
        pts.append(p)
        a, rad, z = a_new, rad_new, z_new
    # smooth out any kinks (the root stays put), then keep it outside the head and body
    P = np.array(pts)
    for _ in range(10):
        P[1:-1] = 0.25 * P[:-2] + 0.5 * P[1:-1] + 0.25 * P[2:]
        P[-1] = 0.5 * P[-1] + 0.5 * P[-2] + (P[-2] - P[-3]) * 0.5
    out = []
    if not hasattr(H, "ear_kd"):
        ears = H.co[H.mask["ears"]]
        H.ear_kd = KDTree(len(ears))
        for i, pe in enumerate(ears):
            H.ear_kd.insert(pe, i)
        H.ear_kd.balance()
    for p in P:
        if p[2] > neck_z and H.ear_kd.find(p)[2] < 0.12:
            out.append(p)           # over an ear: the outline already keeps it off (pushing to the ear's nearest
                                    # point would fold it round the rim)
        elif p[2] > neck_z:
            out.append(push_out(H, p, clear * 0.9, body))
        else:                       # (the head reference still has A-pose shoulders: only the body counts down here)
            q = Vector(p)
            loc, nrm, fi, dist = body.find_nearest(q)
            if loc is not None and (q - loc).dot(nrm) < clear * 0.9:
                q = loc + nrm * clear * 0.9
            out.append(np.array(q))
    return out


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
        if extra is not None:
            # on top of a shoulder: hair slides off to the front or the back (whichever side it is already on)
            # instead of piling up sideways along the shoulder
            loc, nrm, fi, dist = extra.find_nearest(Vector(p))
            if loc is not None and dist < clear * 1.6 and nrm.z > 0.35 and p[2] < H.J["neck"][2] - 0.05:
                side = 1.0 if p[1] > loc.y - 0.02 else -1.0
                p = p + np.array([0.0, side * step * 0.9, -step * 0.3])
                p = push_out(H, p, clear, extra)
        d = p - pts[-1]
        if np.linalg.norm(d) > 1e-6:
            d = d / np.linalg.norm(d)
        pts.append(p)
    # once a strand is falling it never turns back up (no hooks where it meets the chest or a shoulder)
    low = None
    for i in range(1, len(pts)):
        if low is None and i > len(pts) * 0.3 and pts[i][2] < pts[i - 1][2]:
            low = pts[i][2]
        if low is not None:
            if pts[i][2] > low:
                pts[i] = np.array([pts[i][0], pts[i][1], low - 0.002])
            low = pts[i][2]
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
    cover = smoothstep(0.0, feather * (1 + 0.6 * front), hl)
    top_w = smoothstep(p.get("top_from", 0.15) * R, p.get("top_to", 0.6) * R, up)   # 0 below the temples, 1 on top
    T = p["side"] + (p["top"] - p["side"]) * top_w
    if p.get("puff"):                                    # a round cloud of curls around the head
        c = H.centre + np.array([0, 0.3 * R, 0.3 * R])
        rr = np.array(p["puff"]) * R
        q = (V - c) / rr
        nq = np.linalg.norm(q, axis=1)
        dist = np.linalg.norm(V - c, axis=1)
        T = np.maximum(0.03, dist / np.maximum(nq, 1e-6) - dist)
    if "fade_z" in p:                                    # skin fade: sides and back thin to nothing below a line
        fz = (p["fade_line"](V) if "fade_line" in p else H.ear_z) + p["fade_z"] + p.get("fade_front", 0.0) * smoothstep(0.0, 0.6 * H.R, -(V[:, 1] - H.centre[1]))
        T = T * smoothstep(fz - 0.10, fz + 0.06, V[:, 2] + 0.03 * noise(V, 9))
    if p.get("front_lift"):                              # a little more height at the front (the crop in the reference)
        T += p["front_lift"] * smoothstep(0.0, 0.5 * R, -back) * top_w
    if p.get("part") is not None:                        # side part: a combed line, hair swept away from it
        px = p["part"] * R
        dist = np.abs(rel[:, 0] - px)
        T *= 1 - 0.4 * np.exp(-(dist / 0.025) ** 2) * top_w * (rel[:, 1] < 0.35 * R)
        T += p.get("sweep", 0.0) * top_w * smoothstep(0.0, 0.5 * R, -(rel[:, 0] - px) * np.sign(p["part"]))
        T = combed(V, N, np.array([px, 0, 0]), 0, p.get("groove", 0.25), T, "lines", np.array([0, 1.0, 0]))
    elif p.get("slickback"):                             # combed straight back from the hairline, no part
        T = combed(V, N, np.array([0.0, 0.0, 0.0]), p.get("freq", 30), p.get("groove", 0.3), T, "lines", np.array([0, 1.0, 0]))
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
    if p.get("texture"):                                 # short textured hair: small tufts all over, not smooth streaks
        tw = smoothstep(0.0, 0.4 * R, up)
        T = T * (1 + p["texture"] * tw * (0.5 * noise(V, 90) + 0.5 * noise(V, 160)))
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


FRONT_RAISE = 0.0


def cap_line(H, P):
    """the lower edge of a cap's band (NCLookBuilder F.cap): 1.3 cm over the brows at the front, just above the ears
    at the sides and low on the back of the head (0.2 head units). In skull radii over the eyes: 0.41 front, 0.11 back.
    Anything thicker than ~0.012 above it comes through the cap, which sits 0.03 head units off the skin."""
    rel = np.atleast_2d(P) - H.centre
    front = np.clip(-rel[:, 1] / H.R, -1, 1) * 0.5 + 0.5
    return H.anchor[2] + H.R * (0.11 + 0.30 * front)


def cap_version(H, V, T, p):
    """under a hat: everything above the cap line pressed flat (the hat covers it), the rest unchanged"""
    rel = V - H.centre
    capline = cap_line(H, V)
    T2 = T.copy()
    over = V[:, 2] > capline - 0.03
    T2[over] = 0.0                       # over the band: only a hair-coloured skin, right on the scalp
    T2[~over] += 0.002                   # (the cap piece sits at lift 0.005, so the hair below keeps its height)
    return T2


def front_hairline(H, V):
    """the hairline across the forehead, the temples and down in front of the ears (sideburns), shaped like a real
    one (references/faces): forehead about 3/4 of the brow-to-nose height, nearly straight across with soft
    temple corners, then straight down in front of the ear. MakeHuman's scalp group recedes far at the temples."""
    male = H.gender == "Male"
    rel = V - H.centre
    a = np.abs(np.arctan2(rel[:, 0], -rel[:, 1]))                  # 0 = straight ahead, pi/2 = the side
    ears = H.co[H.mask["ears"]]
    er = ears - H.centre
    # where the ear joins the head at its front (the ear rim sticks out, so its own angle is too far forward)
    if len(ears):
        ax_ = np.abs(ears[:, 0] - H.anchor[0])
        root = ears[ax_ < np.percentile(ax_, 30)]                    # the part of the ear that joins the head
        front = root[np.argmin(root[:, 1])]
        a_ear = math.atan2(abs(front[0] - H.anchor[0]), -(front[1] - H.centre[1]))
    else:
        a_ear = math.radians(80)
    brow = H.anchor[2] + 0.1
    nose_base = H.nose_tip[2] - 0.035
    hz_c = brow + (0.55 if male else 0.44) * (H.top - brow)            # (measured on the reference turnaround)
    # the temple corner sits above the outer end of the eyebrow; from there the hairline turns down to the sideburn
    tail = np.array([abs(H.eyeL[0] - H.anchor[0]) + 0.085, H.eyeL[1] - H.centre[1]])
    a_brow = math.atan2(tail[0], -tail[1])
    a_t = a_brow + math.radians(4 if male else -18)
    burn = H.ear_z + (0.0 if male else 0.06)                        # how low the sideburn comes
    # (straight across, the middle a touch higher, rounding over into the temples: no dip in the centre like a
    #  widow's peak, which raising only the corners made)
    corner = hz_c + (0.008 if male else 0.0) * (1 - smoothstep(0.0, a_t, a))
    drop = np.clip((a - a_t) / math.radians(14 if male else 42), 0, 1)       # (the temple: nearly straight down)
    # (women: a rounder curve down over the temple to just in front of the ear top, the temple itself covered)
    hz = corner + (burn - corner) * (smoothstep(0.0, 1.0, drop) ** (0.55 if male else 0.8))
    hz += 0.006 * noise(V, 30)                                      # a little irregular, like a real hairline
    w = 0.03
    fill = smoothstep(-w, w, V[:, 2] - hz)
    # how much this hairline replaces the scalp group: all of the face side, fading out just in front of the ear
    wgt = 1.0 - smoothstep(a_ear + math.radians(12), a_ear + math.radians(30), a)   # (on over the ear, hugging it)
    # never onto the ear itself (the sideburn runs down just in front of it)
    kd = KDTree(len(ears))
    for i, pe in enumerate(ears):
        kd.insert(pe, i)
    kd.balance()
    ear_d = np.array([kd.find(v)[2] for v in V])
    fill = fill * smoothstep(0.02, 0.045, ear_d)
    wgt = wgt * (1.0 - smoothstep(0.1 * H.R, 0.25 * H.R, rel[:, 1])) * smoothstep(burn - 0.1, burn - 0.03, V[:, 2])
    if os.environ.get("NC_DEBUG"):
        sel = (np.abs(rel[:, 0]) > 0.8 * np.abs(rel[:, 0]).max()) & (V[:, 2] > H.ear_z) & (V[:, 2] < H.ear_z + 0.25) & (rel[:, 1] < 0)
        print("DBG n", sel.sum(), "a", np.percentile(np.degrees(a[sel]), [5, 50, 95]).round(1), "z-hz", np.percentile((V[:, 2] - hz)[sel], [5, 50, 95]).round(3),
              "fill", np.percentile(fill[sel], [5, 50, 95]).round(2), "wgt", np.percentile(wgt[sel], [5, 50, 95]).round(2), "earz", round(float(H.ear_z), 3), "burn", round(float(burn), 3))
    print("NC_HAIRLINE", H.gender, round(float(np.degrees(a_ear)), 1), round(float(np.degrees(a_t)), 1), round(float(hz_c - brow), 3))
    return fill, wgt, a_ear


def build_styles(H):
    """every hair style for this head -> {name: {"hair": obj, "fade": obj|None, "cap": obj, "kind": ...}}"""
    V, F, S, N = fine_surface(H, H.ear_z - 0.45, levels=2)
    fill, wgt, A_EAR = front_hairline(H, V)
    S0 = S.copy()
    S = S * (1 - wgt) + np.maximum(S * 0.0, fill) * wgt
    if os.environ.get("NC_DEBUG"):
        rr = V - H.centre
        az0 = np.degrees(np.abs(np.arctan2(rr[:, 0], -rr[:, 1])))
        for lo_, hi_ in ((40, 55), (55, 65), (65, 75), (75, 85)):
            sel = (az0 > lo_) & (az0 < hi_) & (V[:, 2] > H.ear_z + 0.05) & (V[:, 2] < H.ear_z + 0.3)
            print("DBG2", lo_, hi_, sel.sum(), "S0", round(float((S0[sel] > 0.5).mean()), 2), "S", round(float((S[sel] > 0.5).mean()), 2),
                  "fill", round(float((fill[sel] > 0.5).mean()), 2), "wgt", round(float(wgt[sel].mean()), 2))
    d = signed_hairline(V, F, S)
    out = {}
    male = H.gender == "Male"

    ev = edge_v(H, V)

    rel_, up_, side_, back_, crown_ = head_frame(H, V)

    def flow_crown(loc, nrm):
        """hair grows away from the crown whorl (behind the top of the head)"""
        return loc - crown_

    def flow_back(loc, nrm):
        """brushed back (and a little up): from the front hairline over the top, down-back on the sides"""
        # behind the crown it is combed down the back (projected onto the scalp, "back and up" would point the
        # back hair up at the crown, standing off the head)
        t = float(np.clip((loc[1] - crown_[1]) / 0.08 + 0.5, 0, 1))
        t = t * t * (3 - 2 * t)
        return (1 - t) * np.array([0.0, 1.0, 0.35]) + t * np.array([0.0, 0.35, -1.0])

    def flow_part(px):
        """combed away from a side part at x = px (head frame), sweeping back as it goes"""
        def f(loc, nrm):
            side = np.sign(loc[0] - (H.centre[0] + px)) or 1.0
            # (the part runs from the hairline to the crown; behind it the hair is simply combed down the back)
            behind = float(np.clip((loc[1] - crown_[1]) / 0.1 + 0.3, 0, 1))
            return (1 - behind) * (np.array([side * 1.0, 0.45, 0.0]) + flow_back(loc, nrm) * 0.3) + behind * flow_back(loc, nrm)
        return f

    FLOWS = {"crown": flow_crown, "back": flow_back}

    def make_cards(key, p, cov, T, fade_top=None, hl_=None):
        cp = p["cards"]
        rng = np.random.default_rng(zlib.crc32(key.encode()))     # (stable: str hash() changes every run)
        flow = flow_part(cp["part"] * H.R) if cp.get("flow") == "part" else FLOWS[cp.get("flow", "crown")]
        tmin, tmax = p["side"], max(p["top"], p["side"] + 1e-4)
        tw = np.clip((T - tmin) / (tmax - tmin), 0, 1)
        builders = {"full": Builder(), "cap": Builder()}
        kdv = KDTree(len(V))
        for ii, vv_ in enumerate(V):
            kdv.insert(vv_, ii)
        kdv.balance()
        vol = np.maximum(T, 0.004)

        # the solid base shell's surface over the scalp (same formula add_short uses after the cards)
        if cp.get("base"):
            tsurf = T * cp["base"] * (0.15 + 0.85 * smoothstep(0.0, cp.get("edge_ramp", 0.07), hl_ if hl_ is not None else 1.0))
        else:
            tsurf = np.minimum(T, 0.003)
        tsurf = np.maximum(tsurf, 0) + 0.007
        floor_at = lambda loc: tsurf[kdv.find(loc)[1]]

        def height_at(frac):
            return lambda loc: vol[kdv.find(loc)[1]] * frac
        relc = V - H.centre
        masks = {
            # the front strip along the hairline, where the hair rises off the forehead (its coverage is still
            # feathering in, so the coverage-weighted layers leave it bare)
            "front": smoothstep(0.35 * H.R, 0.7 * H.R, -relc[:, 1]) * smoothstep(H.anchor[2] + 0.04, H.anchor[2] + 0.12, V[:, 2])
                     * (1 - smoothstep(0.42 * H.R, 0.68 * H.R, np.abs(relc[:, 0]))),   # (not round the temples)
        }
        for layer in cp["layers"]:
            kind, spacing, hfrac, width, lmul, wmin = layer[:6]
            weight = smoothstep(wmin, 1.0, cov)
            if len(layer) > 6:
                weight = weight * masks[layer[6]]
            _roots = sample_roots_(rng, weight, spacing)
            if os.environ.get("NC_DBG"):
                print("NC_DBG", key, layer[6] if len(layer) > 6 else "-", len(_roots), float(weight.max()))
            for root, i in _roots:
                if cov[i] < 0.3 or (V[i][2] < H.ear_z + 0.06 + rng.uniform(0, 0.05) and relc[i, 1] < -0.15 * H.R):
                    continue      # (none right on the bare edge, where one floats as a speck, or on the sideburns in front
                    #  of the ear, which the shell does; a ragged line, so the cards above don't end in a step)
                # (the back of a crop is short: the long top hair is the front and crown, so no bowl-shaped fringe)
                backness = float(smoothstep(-0.1 * H.R, 0.8 * H.R, relc[i, 1]))   # (a long blend: no step at the crown)
                length = (cp["len_side"] + (cp["len_top"] - cp["len_side"]) * tw[i] * (1 - 0.55 * backness)) * lmul * rng.uniform(0.8, 1.15)
                # (shorter towards the fade, so hair combed down the back doesn't hang over the faded skin)
                if not (len(layer) > 6 and layer[6] == "front"):   # (the hairline's own coverage is still feathering)
                    length *= 0.3 + 0.7 * smoothstep(0.5, 1.0, cov[i])
                if cp.get("forward") and hl_ is not None:       # hair combed forward stops about at the hairline
                    length = min(length, max(0.02, 0.9 * hl_[i] + 0.015))
                is_front = len(layer) > 6 and layer[6] == "front"
                if fade_top is not None and not is_front:        # and never down past where the fade begins
                    #  (the hairline layer is combed back off the forehead and kept off the temples by its mask)
                    room = 1.3 * (root[2] - fade_top[i] + 0.08)
                    if room < 0.04:                              # (a stub card there reads as a block at the temple:
                        continue                                 #  the shell and the fade texture carry it)
                    length = min(length, room)
                # keep the card about as long as the strand texture is tall for its width (1:4 in the atlas): a short
                # card as wide as it is long squashes the strands into a brush-shaped block
                if length < 0.045:                               # (a stub reads as a hard-ended block or a speck
                    continue                                     #  on the side: the shell carries the short hair)
                w_i = min(width, length * 0.4)
                segs_i = max(3, int(round(cp.get("segs", 6) * min(1.0, length / (0.6 * cp["len_top"])))))
                vv, ff, uu, ww = HC.grow_card(H, root, flow, length, height_at(hfrac * rng.uniform(0.85, 1.1)), w_i,
                                              segs_i, rng, kind, jitter=cp.get("jitter", 0.35),
                                              lift_curve=lambda s_: min(1.0, s_ / 0.2) ** 0.7 * (1 - 0.35 * s_ * s_),
                                              v0=float(rng.uniform(0.04, 0.14)) if len(layer) > 6 and layer[6] == "front" else 0.0,
                                              floor=floor_at)
                builders["full"].add(vv, ff, uu, ww)
                # under a hat only the band below it shows: a card goes in the cap set only if all of it stays well
                # under the cap line (the same line cap_version uses) and close to the scalp, or it pokes through
                vz = np.array(vv)
                if (vz[:, 2] < cap_line(H, vz) - 0.01).all() and hfrac < 0.95:
                    lo_h = np.array([np.linalg.norm(q - H.nearest(q)[0]) for q in vz]).max()
                    if lo_h < 0.02:
                        builders["cap"].add(vv, ff, uu, ww)
        if cp.get("defer"):                                # (long hair: its hanging strands are added later)
            return builders["full"], builders["cap"]
        mk = lambda b_, n_: b_.make(n_, uv=False) if b_.v else None
        out_ = []
        for nm, b_ in ((f"Hair_{key}_Cards", builders["full"]), (f"Hair_{key}_CapCards", builders["cap"])):
            if not b_.v:
                out_.append(None)
                continue
            ob = b_.make(nm, uv=False)
            uvl = ob.data.uv_layers.new(name="UVMap")
            loops = np.array([l.vertex_index for l in ob.data.loops])
            uvl.data.foreach_set("uv", np.stack([np.array(b_.u)[loops], np.array(b_.w)[loops]], 1).ravel())
            out_.append(ob)
        return out_

    # root candidates: random points over the scalp's triangles (the mesh's own vertices are too sparse for dense
    # cards), each with the index of its nearest vertex for the style's fields
    Fa = np.array([f for f in F if len(f) == 3] + [[f[0], f[2], f[3]] for f in F if len(f) == 4] +
                  [[f[0], f[1], f[2]] for f in F if len(f) == 4])
    _r = np.random.default_rng(5)
    _A = np.linalg.norm(np.cross(V[Fa[:, 1]] - V[Fa[:, 0]], V[Fa[:, 2]] - V[Fa[:, 0]]), axis=1)
    _fi = _r.choice(len(Fa), 60000, p=_A / _A.sum())
    _b = _r.random((60000, 2))
    _flip = _b.sum(1) > 1
    _b[_flip] = 1 - _b[_flip]
    CAND = V[Fa[_fi, 0]] + _b[:, :1] * (V[Fa[_fi, 1]] - V[Fa[_fi, 0]]) + _b[:, 1:] * (V[Fa[_fi, 2]] - V[Fa[_fi, 0]])
    _kd = KDTree(len(V))
    for ii, vv_ in enumerate(V):
        _kd.insert(vv_, ii)
    _kd.balance()
    CAND_I = np.array([_kd.find(c)[1] for c in CAND])

    def sample_roots_(rng, weight, spacing):
        """roots as (point, nearest vertex index) pairs"""
        keep = HC.sample_roots(rng, CAND, weight[CAND_I], spacing)
        return [(CAND[k], CAND_I[k]) for k in keep]

    SHEET_CARDS = {"full": [], "cap": []}     # strand cards laid on a hanging sheet by an extras builder (curtain)

    def cards_obj(name, items):
        if not items:
            return None
        b_ = Builder()
        for vv, ff, uu, ww in items:
            b_.add(vv, ff, uu, ww)
        ob = b_.make(name, uv=False)
        uvl = ob.data.uv_layers.new(name="UVMap")
        loops = np.array([l.vertex_index for l in ob.data.loops])
        uvl.data.foreach_set("uv", np.stack([np.array(b_.u)[loops], np.array(b_.w)[loops]], 1).ravel())
        return ob

    def add_short(key, label, p, extras=None):
        T, hl = style_short(H, V, F, S, N, d, p)
        if p.get("edge_up") is not None:                     # a razor-straight edge-up across the forehead with
            relv_ = V - H.centre                             # square corners above the outer brow ends
            tail = np.array([abs(H.eyeL[0] - H.anchor[0]) + 0.085, H.eyeL[1] - H.centre[1]])
            a_t = math.atan2(tail[0], -tail[1]) + math.radians(4)
            a_v = np.abs(np.arctan2(relv_[:, 0], -relv_[:, 1]))
            # the forehead, plus a square skin notch cut back over the temple (hair_ref_2 M2/M3): the edge-up runs
            # straight back from the forehead, drops straight down, then the short temple hair comes forward below
            front = (relv_[:, 1] < 0) & ((a_v < a_t) | ((a_v < a_t + math.radians(p.get("notch_deg", 7))) &
                                                       (V[:, 2] > p["edge_up"] - p.get("notch_drop", 0.05))))
            hl = np.where(front, V[:, 2] - p["edge_up"], hl)
        # coverage across the hairline (0 at the very edge -> 1 where the hair is full) and, for skin fades,
        # down the faded sides: the texture turns it into single hairs thinning out onto the skin
        feather = p.get("feather", 0.06)
        # round the ears and at the nape the hair thins out over a much wider band (it is cut shorter there, so
        # more and more skin shows), so dark hair blends into the skin instead of ending as a block
        relv = V - H.centre
        az = np.abs(np.arctan2(relv[:, 0], -relv[:, 1]))
        # (only behind the front of the ear: the sideburns in front of it stay full)
        low = smoothstep(H.ear_z + 0.14, H.ear_z - 0.12, V[:, 2]) * smoothstep(A_EAR, A_EAR + math.radians(18), az)
        # temples and sideburns are narrow strips (between the hairline and the ear): a short fade there, or the
        # whole strip would be see-through
        burnz = smoothstep(math.radians(28), math.radians(42), az) * (1 - smoothstep(A_EAR + math.radians(4), A_EAR + math.radians(12), az)) * \
            smoothstep(H.anchor[2] + 0.3, H.anchor[2] + 0.18, V[:, 2])
        cov = np.clip(hl / (feather * (1 + 1.5 * low) * (1 - 0.6 * burnz)), 0, 1)
        field = hl + 0.004                                   # the surface runs just past the edge, flush on the skin
        if p.get("parts_phi") is not None:                   # clean scalp parts between the rows
            phv, rxz = p["parts_angle"](V)
            dpart = np.min(np.abs(phv[:, None] - np.radians(p["parts_phi"])[None, :]), axis=1) * rxz
            # (clean parts only where the rows sit close; lower on the sides the base is left dark)
            on_top = smoothstep(H.anchor[2] + 0.2, H.anchor[2] + 0.3, V[:, 2]) * smoothstep(math.radians(30), math.radians(22), np.abs(phv))
            if p.get("parts_band"):                          # (the parts stop at the short band behind the edge-up)
                on_top = on_top * smoothstep(0.6 * p["parts_band"], p["parts_band"], d)
            cov = np.minimum(cov, 1 - on_top * (1 - smoothstep(0.002, 0.007, dpart)))
        if p.get("hard_part") is not None:                  # a shaved line just under where the rows end
            below = p["hard_part"](V) - V[:, 2]
            behind = smoothstep(-0.6 * H.R, -0.45 * H.R, relv[:, 1])            # (from the temple corner back)
            cov = np.minimum(cov, 1 - behind * (1 - smoothstep(0.004, 0.009, np.abs(below - 0.01))))
        if p.get("parts_y") is not None:                     # a centre part from the hairline to the crown
            dpart = np.abs(relv[:, 0])
            on_top = smoothstep(H.anchor[2] + 0.1, H.anchor[2] + 0.25, V[:, 2]) * (relv[:, 1] < 0.45 * H.R)
            cov = np.minimum(cov, 1 - on_top * (1 - smoothstep(0.004, 0.012, dpart)))
        if "fade_z" in p:
            fz = (p["fade_line"](V) if "fade_line" in p else H.ear_z) + p["fade_z"] + p.get("fade_front", 0.0) * smoothstep(0.0, 0.6 * H.R, -(V[:, 1] - H.centre[1]))
            # (fade_len_front: a shorter fade at the temples, where the reference goes from the corner to skin
            #  within a few cm, while the sides and back fade over a longer stretch)
            fwd = smoothstep(0.0, 0.6 * H.R, -(V[:, 1] - H.centre[1]))
            flen0 = p.get("fade_len", 0.3)
            flen0 = flen0 + (p.get("fade_len_front", flen0) - flen0) * fwd
            fc = smoothstep(fz - flen0, fz + 0.1 * (flen0 / p.get("fade_len", 0.3)), V[:, 2] + 0.03 * noise(V, 9))
            if p.get("hard_part") is not None:               # (the fade starts right under the part: dark there,
                below = p["hard_part"](V) - V[:, 2]          # then a long thinning tail down to skin)
                flen = p["fade_len"] * (1 + 0.4 * smoothstep(0.0, 0.6 * H.R, V[:, 1] - H.centre[1]))   # (longer down the back)
                fc = np.clip(1 - (below - 0.012 + 0.01 * noise(V, 9)) / flen, 0, 1) ** 1.9
            cov = np.minimum(cov, fc)
            field = np.minimum(field, fc - 0.02)
        cards = capcards = None
        if p.get("cards"):
            # hair cards: the scalp layer is a thin painted base (colour under the cards, the fade, the edge-up);
            # the volume is cards of single-hair texture grown along the style's flow
            fade_top = None
            if "fade_z" in p:
                fade_top = (p["fade_line"](V) if "fade_line" in p else np.full(len(V), H.ear_z)) + p["fade_z"]
            cards, capcards = make_cards(key, p, cov, T, fade_top, hl)
            # base > 0 keeps a solid inner layer of the hair (that share of the volume) under the cards: it gives
            # the smooth outline of the cut and nothing shows through, while the cards on its surface give strands
            T = T * p["cards"]["base"] if p["cards"].get("base") else np.minimum(T, 0.003)
            # the solid base thins out over the last couple of cm to the hairline, so the front hair rises off the
            # forehead in cards instead of the base ending in a rolled edge
            T = T * (0.15 + 0.85 * smoothstep(0.0, p["cards"].get("edge_ramp", 0.07), hl))
        hair = shell(f"Hair_{key}", V, F, N, T, field=field, lift=0.007, uv=(cov, ev))
        if extras:
            b = Builder()
            b.add_obj(hair)
            extras(b, T)
            hair = b.make(f"Hair_{key}")
        Tc = cap_version(H, V, T, p)
        # (the hair-coloured skin stays under the whole crown: a cap leaves a small gap between its crown and band at the
        #  back, and bare scalp showed through it)
        # (and only up to just over the band's top: the cap's crown covers the rest, and the layer showed through it)
        cap = shell(f"Hair_{key}_Cap", V, F, N, Tc, field=np.minimum(field, cap_line(H, V) + 0.11 - V[:, 2]), lift=0.005, uv=(cov, ev))
        if extras and p.get("cap_extras", True):
            b = Builder()
            b.add_obj(cap)
            extras(b, T, capped=True)
            cap = b.make(f"Hair_{key}_Cap")
        if p.get("cards", {}).get("defer"):               # scalp cards + the hanging strands, one set
            bf, bc = cards, capcards
            cards = cards_obj(f"Hair_{key}_Cards", [(bf.v, bf.f, bf.u, bf.w)] * bool(bf.v) + SHEET_CARDS["full"])
            capcards = cards_obj(f"Hair_{key}_CapCards", [(bc.v, bc.f, bc.u, bc.w)] * bool(bc.v) + SHEET_CARDS["cap"])
        elif cards is None and SHEET_CARDS["full"]:
            cards = cards_obj(f"Hair_{key}_Cards", SHEET_CARDS["full"])
            capcards = cards_obj(f"Hair_{key}_CapCards", SHEET_CARDS["cap"])
        SHEET_CARDS["full"], SHEET_CARDS["cap"] = [], []
        out[key] = {"label": label, "hair": hair, "cap": cap, "fade": None, "skin_fade": "fade_z" in p,
                    "cards": cards, "capcards": capcards}

    def straight_cards(flow, len_top, len_side, base=0.3, dense=1.0, edge_ramp=0.14):
        """the card layers of a short straight cut (worked out on the TaperFade against hair_ref_1)"""
        k = 1.0 / math.sqrt(dense)
        return dict(flow=flow, base=base, edge_ramp=edge_ramp, len_top=len_top, len_side=len_side, jitter=0.1, segs=6,
                    # (kind, root spacing, height share, width, length x, min coverage[, mask])
                    layers=[("STRAIGHT_DENSE", 0.025 * k, 0.86, 0.04, 1.0, 0.7),                  # on the base
                            ("STRAIGHT_DENSE", 0.022 * k, 0.9, 0.036, 1.0, 0.1, "front"),         # the hairline
                            ("STRAIGHT_DENSE", 0.027 * k, 0.88, 0.036, 1.0, 0.8),                 # the outer shape
                            ("STRAIGHT_DENSE", 0.022 * k, 0.62, 0.03, 0.5, 0.45)])                # short sides/back
    if male:
        add_short("Buzz", "Buzz Cut", dict(top=0.016, side=0.012, feather=0.05, groove=0.06, freq=40))
        add_short("Crop", "Short Crop", dict(top=0.06, side=0.02, front_lift=0.025, feather=0.06, groove=0.03, freq=44,
                                              cards=dict(straight_cards("crown", 0.13, 0.05), forward=True)))
        # textured crop with a mid skin fade (references hair_ref_1): 4-6 cm on top brushed up with a small front lift,
        # the fade thins the same colour out to skin from just above the ear
        add_short("TaperFade", "Textured Crop, Mid Fade", dict(top=0.07, side=0.012, top_from=0.0, top_to=0.9, front_lift=0.04, fade_z=0.3, fade_len=0.26, fade_front=0.06, fade_len_front=0.12,
                                                              feather=0.035, groove=0.03, freq=60, texture=0.0,
                                                              cards=dict(flow="back", base=0.42, len_top=0.3, len_side=0.1, jitter=0.1, segs=6,
                                                                         # (kind, root spacing, height share, width, length x, min coverage)
                                                                         layers=[("STRAIGHT_DENSE", 0.025, 0.86, 0.04, 1.0, 0.7),
                                                                                 ("STRAIGHT_DENSE", 0.022, 0.9, 0.036, 1.0, 0.1, "front"),   # lying on the base
                                                                                 ("STRAIGHT_DENSE", 0.027, 0.88, 0.036, 1.0, 0.8),  # the outer shape
                                                                                 ("STRAIGHT_DENSE", 0.022, 0.62, 0.03, 0.5, 0.45)])))
        add_short("HighFade", "High Skin Fade", dict(top=0.085, side=0.014, top_from=0.1, top_to=0.85, fade_z=0.36, fade_len=0.26,
                                                     fade_front=0.04, fade_len_front=0.12, feather=0.045,
                                                     groove=0.03, freq=24, cards=straight_cards("back", 0.32, 0.1)))
        add_short("SidePart", "Side Part", dict(top=0.10, side=0.025, part=0.32, sweep=0.03, feather=0.07, groove=0.04,
                                                 cards=dict(straight_cards("part", 0.3, 0.07), part=0.32)))
        add_short("CurlyTop", "Curly Top", dict(top=0.12, side=0.018, fade_z=0.05, curls=260, curl_r=0.028, curl_amp=0.25, feather=0.06,
                                                 cards=dict(flow="crown", base=0.5, len_top=0.12, len_side=0.05, jitter=0.6, segs=5,
                                                            layers=[("COILY", 0.022, 0.8, 0.045, 1.0, 0.6),
                                                                    ("COILY", 0.022, 0.95, 0.045, 1.0, 0.75),
                                                                    ("COILY", 0.024, 1.05, 0.04, 0.8, 0.85),
                                                                    ("COILY", 0.02, 0.85, 0.04, 1.0, 0.1, "front"),
                                                                    ("STRAIGHT_DENSE", 0.022, 0.62, 0.03, 0.5, 0.45)])))
    else:
        add_short("Pixie", "Pixie Cut", dict(top=0.07, side=0.03, part=0.25, sweep=0.03, feather=0.06, groove=0.12,
                                              cards=dict(straight_cards("part", 0.24, 0.09), part=0.25)))

    # --- locs / twists: a short base, then real strands that hang (the front ones fall over the eyes)
    def locs_extras(length, n_front, n_all, radius, front_len, end_z=None, part=False, two_strand=False, gap=0.075, clear_k=1.3):
        def ex(b, T, capped=False):
            r2 = random.Random(11)
            ears = H.co[H.mask["ears"]]
            kde = KDTree(len(ears))
            for ii, pe in enumerate(ears):
                kde.insert(pe, ii)
            kde.balance()
            # no roots on the ears, nor straight above them (a loc falling onto the ear kinks round it)
            kxy = KDTree(len(ears))
            for ii, pe in enumerate(ears):
                kxy.insert((pe[0], pe[1], 0.0), ii)
            kxy.balance()
            cand = np.array([i for i in np.where(T > 0.012)[0] if kde.find(V[i])[2] > 0.13
                             and kxy.find((V[i][0], V[i][1], 0.0))[2] > 0.06])
            r2.shuffle(cand)
            rel = V - H.centre
            chosen = []
            for i in cand:
                if all(np.linalg.norm(V[i] - V[j]) > gap for j in chosen):
                    chosen.append(i)
                if len(chosen) >= n_all:
                    break
            if part:                                   # centre part: no roots on it
                chosen = [i for i in chosen if abs(rel[i][0]) > 0.035 or rel[i][1] > 0.45 * H.R]
            for k, i in enumerate(chosen):
                root = V[i] + N[i] * (T[i] * 0.6)
                if capped and V[i][2] > cap_line(H, V[i])[0] - 0.01:
                    continue
                is_front = rel[i][1] < -0.25 * H.R and rel[i][2] > 0.1
                L = front_len if is_front else length
                L *= 0.85 + 0.3 * r2.random()
                if end_z is not None:                  # tips end on one line: brows at the front, ear tops and fade behind
                    fr = smoothstep(0.1 * H.R, 0.55 * H.R, -rel[i][1])
                    ez = end_z + (H.anchor[2] + 0.06 - end_z) * fr
                    if part:                           # the forehead shows in a V under the part (shorter in the middle)
                        ez += 0.16 * fr * (1 - smoothstep(0.08 * H.R, 0.45 * H.R, abs(rel[i][0])))
                    L = max(0.08, (V[i][2] - ez) * 1.12) * (0.85 + 0.3 * r2.random())
                crown = np.array([0.0, H.centre[1] + 0.15 * H.R, H.top])
                flow = V[i] - crown
                flow -= N[i] * np.dot(flow, N[i])
                if np.linalg.norm(flow) < 0.05:                # right at the crown: fall towards the back
                    flow = np.array([0.0, 1.0, -0.3])
                flow /= max(np.linalg.norm(flow), 1e-9)
                dir0 = flow * 0.9 + N[i] * 0.1
                pts = drape(H, root, L, radius * clear_k, SHOULDERS[H.gender], seed=k, sway=0.25)
                # each loc grows out of the scalp: start it inside the base, so no cut end shows at the root
                pts = [V[i] - N[i] * 0.015, V[i] + N[i] * (T[i] * 0.5) + dir0 * 0.02] + list(pts[1:])
                rad = [radius * (1.0 - 0.35 * (j / len(pts)) ** 2) for j in range(len(pts))]
                rad[0] *= 0.8
                if two_strand:
                    for vv, ff in rope(pts, rad):
                        b.add(vv, ff)
                else:
                    vv, ff = tube(pts, rad, sides=7, twist=0.6, bumps=0.08, bump_freq=5.0)
                    b.add(vv, ff)
        return ex

    # rows lie in planes through a front-to-back axis well below the head (under the jaw), so they run nearly
    # parallel over the top like the reference instead of bunching together at the forehead. The axis rises towards
    # the back, so at the back of the head the rows draw together and point down towards the nape (hair_ref_2 M5)
    FT_AXIS = 0.5
    FT_SPAN = 38.0
    FT_TILT = 0.1
    FT_FRONT = 0.3                       # rows start at the edge-up's square temple corners, not down the temples
    ft_o = np.array([0.0, H.centre[1], H.ear_z - FT_AXIS])
    ft_a = np.array([0.0, 1.0, FT_TILT]) / math.hypot(1.0, FT_TILT)
    ft_up = np.array([0.0, 0.0, 1.0]) - ft_a * ft_a[2]
    ft_up /= np.linalg.norm(ft_up)

    def ft_angle(P):
        """each point's angle round the rows' axis (0 straight up) and its distance from the axis"""
        rel = np.atleast_2d(P) - ft_o
        xx, yy = rel[:, 0], rel @ ft_up
        return np.arctan2(xx, yy), np.hypot(xx, yy)

    def ft_dir(ph, th):
        e = np.array([math.sin(ph), 0.0, 0.0]) + math.cos(ph) * ft_up
        return Vector(-math.cos(th) * ft_a + math.sin(th) * e)

    def ft_rows(n_rows):
        """row angles spaced by equal distance OVER THE SCALP (not equal angles: on the sides the head turns away from
        the axis and equal angles leave wide gaps), from just above the fade on one side to the other"""
        grid = np.radians(np.linspace(-85, 85, 341))
        pts = []
        for ph in grid:
            dv = ft_dir(ph, math.pi / 2)
            hit = H.bvh.ray_cast(Vector(ft_o) + dv * 3, -dv, 3.0)
            pts.append(np.array(hit[0]) if hit[0] is not None else np.full(3, np.nan))
        pts = np.array(pts)
        ok = pts[:, 2] > H.ear_z + FT_LOW                                    # (the lowest row, above the ear)
        g, P = grid[ok], pts[ok]
        arc = np.r_[0, np.cumsum(np.linalg.norm(np.diff(P, axis=0), axis=1))]
        pitch = arc[-1] / n_rows
        rows = np.interp(pitch * (np.arange(n_rows) + 0.5), arc, g)
        parts = np.interp(pitch * np.arange(1, n_rows), arc, g)
        return rows, parts, pitch

    FT_CUT = 0.19                         # the hard part, from ear_z (mid-ear) at the back; it rises by FT_FRONT to
    FT_FRONT_PART = 0.14                  # the edge-up's temple corner (hair_ref_2 M3: the rolls stay high on the head)

    def ft_cut(P):
        P = np.atleast_2d(P)
        return H.ear_z + FT_CUT + FT_FRONT_PART * smoothstep(-0.2 * H.R, 0.6 * H.R, -(P[:, 1] - H.centre[1]))

    FT_LOW = 0.21
    FT_BAND = 0.02                       # the strip of short hair between the edge-up line and the twists' ends
    ft_corner = H.anchor[2] + 0.1 + 0.55 * (H.top - H.anchor[2] - 0.1)    # (front_hairline's temple corner height)
    FT_ROWS, FT_PARTS, FT_PITCH = ft_rows(10)

    def flat_twists():
        """two-strand flat twists in rows from the hairline over the crown to the fade (references hair_ref_2): fat
        twists packed side by side (only a thin part between them), knobbed ends at the front hairline. Returns the
        extras builder and a function giving each scalp point's distance from the twists (for the part and fade)"""
        kv = KDTree(len(V))
        for ii, vv_ in enumerate(V):
            kv.insert(vv_, ii)
        kv.balance()
        axis_o = Vector(ft_o)
        rows = []
        for ph in FT_ROWS:
            segs = [[]]
            dref = None
            for th in np.linspace(math.radians(-20), math.radians(220), 240):
                dvec = ft_dir(ph, th)
                hit = H.bvh.ray_cast(axis_o + dvec * 3, -dvec, 3.0)
                if hit[0] is None:
                    continue
                q = np.array(hit[0])
                if dref is None and th >= math.pi / 2:
                    dref = ft_angle(q)[1][0]
                _, idx, _ = kv.find(q)
                if d[idx] < FT_BAND:
                    segs.append([])                             # (only behind the edge-up's short band)
                    continue
                segs[-1].append((q, np.array(hit[1])))
            path = max(segs, key=len)                           # the longest unbroken run
            # both ends trimmed back to the hard part; at the front the twists start at the edge-up's square temple
            # corners, never down the temples
            above = [q[2] > ft_cut(q)[0] + 0.01 and (q[1] - H.centre[1] > -0.35 * H.R or q[2] > ft_corner - 0.01)
                     for q, _ in path]
            if not any(above):
                continue
            k0, k1 = above.index(True), len(above) - above[::-1].index(True)
            path = path[k0:k1]
            if len(path) < 30:                                  # (no stubs where a row only grazes the hair)
                continue
            path = path[::3]
            # each twist is as wide as its row (they touch; as the rows draw together at the back so do the twists)
            _, dist = ft_angle(np.array([q for q, _ in path]))
            rows.append((path, 0.53 * FT_PITCH * np.clip(dist / (dref or dist.max()), 0.75, 1.0)))
        # the hard part runs along the twists' lower edge: per direction round the head, the lowest twist edge,
        # smoothed into one clean line (sides and back; the front is the hairline)
        allq = np.concatenate([[q for q, _ in pth] for pth, _ in rows])
        allr = np.concatenate([rw for _, rw in rows])
        nb = 90
        az = np.arctan2(allq[:, 0] - H.centre[0], allq[:, 1] - H.centre[1])
        bins = ((az + math.pi) / (2 * math.pi) * nb).astype(int) % nb
        zb = np.full(nb, np.nan)
        for k_ in range(nb):
            sel = bins == k_
            if sel.any():
                zb[k_] = np.min(allq[sel, 2] - 0.7 * allr[sel])
        okb = ~np.isnan(zb)
        xb = np.arange(nb)
        zb = np.interp(xb, xb[okb], zb[okb], period=nb)
        zb = np.convolve(np.r_[zb[-5:], zb, zb[:5]], np.ones(11) / 11, "same")[5:-5]

        def twist_line(P):
            P = np.atleast_2d(P)
            a_ = np.arctan2(P[:, 0] - H.centre[0], P[:, 1] - H.centre[1])
            return np.interp((a_ + math.pi) / (2 * math.pi) * nb - 0.5, xb, zb, period=nb)

        def ex(b, T, capped=False):
            for path, rw in rows:
                if capped:                                      # (under a hat: only the band below the crown)
                    keep = [k for k, (q, _) in enumerate(path) if q[2] <= cap_line(H, q)[0] - 0.01]
                    if len(keep) < 4:
                        continue
                    runs = np.split(np.array(keep), np.nonzero(np.diff(keep) > 1)[0] + 1)
                    run = max(runs, key=len)
                    path, rw = [path[k] for k in run], rw[run]
                m = len(path)
                # the front end is a full knob, the back end thins into the fade
                env = [(0.45 + 0.55 * smoothstep(-0.5, 3.0, j)) * (1 - 0.35 * smoothstep(m - 3, m - 1, j)) for j in range(m)]
                rad = [r_ * (0.35 + 0.65 * e_) for r_, e_ in zip(rw, env)]
                # (sitting on top of the short base hair, never sunk under it)
                P = [q + n_ * (0.008 + r_ * (0.1 + 0.45 * e_)) for (q, n_), r_, e_ in zip(path, rw, env)]
                for vv, ff in rope(P, rad, turns=70.0, normals=[n_ for _, n_ in path], flat=0.5, sides=8):
                    b.add(vv, ff)
        return ex, twist_line


    base = dict(top=0.03, side=0.02, feather=0.05, groove=0.2, freq=34)
    if male:
        add_short("Locs", "Shoulder Locs", base, locs_extras(1.1, 12, 70, 0.027, 0.5))
        # hanging two-strand twists from a centre part, ending at the brows, the ear tops and the fade line, with a
        # squared edge-up and a high skin fade (references hair_ref_3)
        add_short("Twists", "Hanging Twists", dict(base, top=0.02, fade_z=0.2, feather=0.025, parts_y=True),
                  locs_extras(0.45, 14, 220, 0.022, 0.3, end_z=H.ear_z + 0.12, part=True, two_strand=True, gap=0.042, clear_k=0.8))
        ft_ex, ft_line = flat_twists()
        add_short("FlatTwists", "Flat Twists", dict(top=0.012, side=0.012, fade_z=-0.03, fade_len=0.27, fade_line=ft_line, hard_part=ft_line, feather=0.01,
                                                    edge_up=ft_corner, parts_band=FT_BAND, groove=0.05, freq=40,
                                                    parts_phi=np.degrees(FT_PARTS), parts_angle=ft_angle),
                  ft_ex)
    else:
        add_short("Locs", "Long Locs", base, locs_extras(1.8, 10, 80, 0.026, 0.38))

    # --- women: slick centre part with a low bun (the reference), ponytail, long straight, bob
    if not male:
        slick = dict(top=0.035, side=0.028, part=0.0, sweep=0.0, feather=0.05, groove=0.35)
        # (the low bun: slicked straight back from a soft rounded hairline, no part, ears showing - hair_ref_1/2)
        slickback = dict(top=0.03, side=0.024, part=None, slickback=True, feather=0.05, groove=0.35, freq=0)
        nape = np.array([0.0, H.centre[1] + 0.9 * H.R, H.ear_z - 0.07])

        def bun(b, T, capped=False):
            c = nape + np.array([0, 0.08, 0])
            bm = bmesh.new()
            bmesh.ops.create_uvsphere(bm, u_segments=28, v_segments=18, radius=0.15)
            for v in bm.verts:
                a = math.atan2(v.co.x, v.co.z)
                v.co.y *= 0.72
                v.co *= 0.9
                v.co += Vector(c)
            vv = [v.co[:] for v in bm.verts]
            ff = [[v.index for v in f.verts] for f in bm.faces]
            bm.free()
            b.add(vv, ff)
            # the hair wound round into the bun: thick strands wrapped round it at different tilts (like the reference)
            r5 = random.Random(9)
            for k in range(8):
                tilt = math.radians(-60 + 120 * k / 7 + r5.uniform(-8, 8))
                spin = r5.uniform(0, math.pi)
                pts, rr = [], []
                for t in np.linspace(0, 2 * math.pi, 64)[:-1]:
                    q = np.array([math.cos(t), 0.0, math.sin(t)]) * 0.125
                    q = np.array([q[0], q[2] * math.sin(tilt), q[2] * math.cos(tilt)])       # tilt the loop
                    q = np.array([q[0] * math.cos(spin) - q[2] * math.sin(spin), q[1], q[0] * math.sin(spin) + q[2] * math.cos(spin)])
                    q[1] *= 0.72
                    pts.append(c + q)
                    rr.append(0.03)
                pts.append(pts[0])
                rr.append(0.03)
                vv, ff = tube(pts, rr, sides=8, twist=0.5, bumps=0.06, bump_freq=10.0)
                b.add(vv, ff)

        add_short("LowBun", "Slick Low Bun", slickback, bun)

        def ponytail(b, T, capped=False):
            root = np.array([0.0, H.centre[1] + 0.85 * H.R, H.anchor[2] + 0.12])
            # out of the tie in a short arc, then it hangs straight down the back of the head, neck and upper back
            # (resting on them, never kinked: drape follows the outline below it)
            arc = strand(H, root, [0, 1.0, 0.25], 0.22, step=0.04, gravity=0.6, clear=0.07, stiff=0.6)
            rest = drape(H, arc[-1], 1.08, 0.045, SHOULDERS[H.gender], step=0.04, seed=4)
            P0 = np.array(list(arc) + list(rest[1:]))
            for _ in range(6):
                P0[1:-1] = 0.25 * P0[:-2] + 0.5 * P0[1:-1] + 0.25 * P0[2:]
            pts = [push_out(H, q, 0.06, SHOULDERS[H.gender]) if q[2] > H.J["neck"][2] else q for q in P0]
            pts[0] = root
            # a bundle of clumps, gathered at the tie and loosening towards the ends, instead of one smooth tube
            P = np.array(pts)
            n = len(P)
            tang = np.gradient(P, axis=0)
            tang /= np.maximum(np.linalg.norm(tang, axis=1), 1e-9)[:, None]
            ref = np.array([1.0, 0.0, 0.0])
            e1 = np.cross(tang, ref)
            e1 /= np.maximum(np.linalg.norm(e1, axis=1), 1e-9)[:, None]
            e2 = np.cross(tang, e1)
            r3 = random.Random(5)
            core = [0.06 * (1 - 0.8 * (j / n) ** 1.6) for j in range(n)]
            vv, ff = tube(pts, [c * 0.8 for c in core], sides=10, twist=0.1)
            b.add(vv, ff)
            for k in range(14):
                a0 = 2 * math.pi * k / 14 + r3.uniform(-0.2, 0.2)
                spin = r3.uniform(1.5, 3.0)
                ln = int(n * r3.uniform(0.82, 1.0))
                q, rr = [], []
                for j in range(ln):
                    t = j / n
                    a = a0 + spin * t
                    spread = core[j] * (0.75 + 0.35 * smoothstep(0.1, 1.0, t))
                    q.append(P[j] + (e1[j] * math.cos(a) + e2[j] * math.sin(a)) * spread)
                    rr.append(0.026 * (1 - 0.85 * (j / ln) ** 1.4) + 0.002)
                vv, ff = tube(q, rr, sides=6, twist=0.4, bumps=0.06)
                b.add(vv, ff)
            vv, ff = tube([root - np.array([0, 0.02, 0]), root + np.array([0, 0.05, 0])], [0.06, 0.06], sides=14)
            b.add(vv, ff)                                              # the hair tie
        add_short("Ponytail", "High Ponytail", dict(slick, part=None), ponytail)

        def curtain(length, flare, curl, part_x=None):
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
                R = R + (0.045 + flare * 0.12 * jj ** 1.5) * smoothstep(0.0, 0.3, jj)   # (tucked under the shell up top: no lid edge)
                if curl:
                    R -= 0.06 * smoothstep(0.75, 1.0, jj)
                # the sheet's two front ends thin onto the head over the last columns, so it ends in a soft edge
                # beside the face instead of a flat plank
                kk_ = np.arange(cols)[:, None]
                fend = smoothstep(0.0, 9.0, np.minimum(kk_, cols - 1 - kk_).astype(float))
                hacc = np.maximum.accumulate(head_r, axis=1) + 0.012
                R = hacc + (R - hacc) * (0.6 + 0.4 * fend)
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
                taper = taper * (0.55 + 0.45 * fend)
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
                # the ends break up into single strands (the edge texture), not a cut slab
                cc, rr = np.meshgrid(np.arange(cols), np.arange(rows + 1), indexing="ij")
                tip = np.clip((rows - rr) / max(rows * 0.2, 1), 0, 1) ** 0.8
                uu = tip.ravel()                                  # (front edges stay solid: hair runs along them)
                ww = (cc / (cols - 1) * 16 + 0.15 * np.sin(rr * 0.3)).ravel()
                b.add(verts, faces, np.r_[uu, uu], np.r_[ww, ww])
                # strand cards: guide strands from roots all over the scalp, combed along the style's flow over the
                # head until they turn down, then falling on the sheet's outer surface (which already drapes over the
                # back and shoulders). Each strand is cut into overlapping ~9 cm cards (one full strand texture each,
                # so tips taper and nothing is stretched or square-cut); ends are uneven. Under a hat, only the parts
                # below the cap line.
                surfR = R + ((groove + 0.03) * taper)                 # the sheet's outer radius (cols x rows+1)
                a_lo, a_hi = math.radians(-110), math.radians(110)

                def sheet_r(a, z):
                    if not (a_lo <= a <= a_hi):
                        return outline_head(a, z) + 0.03
                    kf = (a - a_lo) / (a_hi - a_lo) * (cols - 1)
                    k0 = int(min(cols - 2, kf))
                    t_ = kf - k0
                    out_ = 0.0
                    for kk, wk in ((k0, 1 - t_), (k0 + 1, t_)):
                        jf = (z0 - z) / max(col_len(angs[kk]), 1e-3) * rows
                        jf = min(max(jf, 0.0), rows)
                        out_ += wk * np.interp(jf, np.arange(rows + 1), surfR[kk])
                    return out_

                flow0 = flow_part(part_x * H.R) if part_x is not None else flow_back

                def flow_(loc, nrm):
                    # in front of the ears the hair falls down the side of the face (the front locks), not back
                    a_ = abs(math.atan2(loc[0] - axis[0], loc[1] - axis[1]))
                    k_ = smoothstep(math.radians(70), math.radians(95), a_) * smoothstep(H.anchor[2] + 0.25, H.anchor[2] + 0.05, loc[2])
                    return (1 - k_) * flow0(loc, nrm) + k_ * np.array([0.0, 0.25, -1.0])
                rng_ = np.random.default_rng(zlib.crc32(f"strands{length}{flare}".encode()))
                kdT = KDTree(len(V))
                for ii_, vv_ in enumerate(V):
                    kdT.insert(vv_, ii_)
                kdT.balance()
                wroot = smoothstep(0.004, 0.02, T)
                step_s, step_h = 0.03, 0.05
                for layer_k, (spacing, h_off, wcard) in enumerate(((0.04, 0.010, 0.05), (0.055, 0.020, 0.045))):
                    for root, ri in sample_roots_(rng_, wroot, spacing):
                        total = length * rng_.uniform(0.86, 1.0) * (1.0 if layer_k == 0 else rng_.uniform(0.7, 1.0))
                        pts, outs = [], []
                        p_, L = np.array(root, float), 0.0
                        q = None
                        for _ in range(60):                       # over the head
                            loc, nrm, _f, _d = H.nearest(p_)
                            d = flow_(loc, nrm)
                            d = d - nrm * (d @ nrm)
                            d = d / max(np.linalg.norm(d), 1e-9)
                            q = loc + nrm * (max(T[kdT.find(loc)[1]], 0) + 0.007 + h_off)
                            pts.append(q)
                            outs.append(nrm)
                            if d[2] < -0.8 or loc[2] < H.ear_z + 0.04 or L >= total:
                                break
                            p_ = loc + d * step_s
                            L += step_s
                        n_surf = len(pts)
                        ang = math.atan2(q[0] - axis[0], q[1] - axis[1])
                        r_ = math.hypot(q[0] - axis[0], q[1] - axis[1])
                        z_ = q[2]
                        floor_z = (shoulder_z + rng_.uniform(-0.02, 0.06)) if abs(ang) > math.radians(55) else -9.0
                        kq = int(np.clip((ang - a_lo) / (a_hi - a_lo) * (cols - 1), 0, cols - 1))
                        floor_z = max(floor_z, z0 - col_len(angs[kq]) + rng_.uniform(0.0, 0.08))   # (inside the sheet's cut)
                        while L < total and z_ - step_h > floor_z:   # then down, onto the sheet
                            z_ -= step_h
                            L += step_h
                            tgt = sheet_r(ang, z_) + h_off - 0.004
                            r_ = r_ + float(np.clip(tgt - r_, -0.03, 0.04))
                            pts.append(np.array([axis[0] + math.sin(ang) * r_, axis[1] + math.cos(ang) * r_, z_]))
                            outs.append(np.array([math.sin(ang), math.cos(ang), 0.0]))
                        if len(pts) < 3:
                            continue
                        P_ = np.array(pts)
                        O_ = np.array(outs)
                        tan = np.gradient(P_, axis=0)
                        tan /= np.maximum(np.linalg.norm(tan, axis=1), 1e-9)[:, None]
                        acr = np.cross(tan, O_)
                        acr /= np.maximum(np.linalg.norm(acr, axis=1), 1e-9)[:, None]
                        # arc length along the strand, and overlapping cards ~0.36 long
                        sarc = np.r_[0, np.cumsum(np.linalg.norm(np.diff(P_, axis=0), axis=1))]
                        seg_len = 0.55
                        # (on the head the scalp cards do the combing; strands only from just above where they drop)
                        s0 = max(0.0, sarc[n_surf - 1] - 0.15) - rng_.uniform(0, 0.3) * seg_len
                        s_floor = max(0.0, sarc[n_surf - 1] - 0.15)
                        while s0 < sarc[-1] - 0.05:
                            if s0 + seg_len > sarc[-1]:                    # (the last card ends on the strand tips:
                                s0 = max(s_floor - 0.3 * seg_len, sarc[-1] - seg_len)   # no square-cut end)
                            a_s, e_s = max(s0, s_floor), min(s0 + seg_len, sarc[-1])
                            idx = np.nonzero((sarc >= a_s) & (sarc <= e_s))[0]
                            if len(idx) >= 2:
                                seg_p = P_[idx]
                                if capped:
                                    keep = seg_p[:, 2] < cap_line(H, seg_p) - 0.02
                                    if not keep.all():
                                        if s0 + seg_len >= sarc[-1] - 1e-6:
                                            break
                                        s0 += seg_len * rng_.uniform(0.5, 0.65)
                                        continue
                                hw = wcard * 0.5 * np.clip(0.6 + 0.4 * (sarc[idx] / 0.25), 0.6, 1.0)[:, None]
                                ac = acr[idx]
                                u0, u1 = HC.kind_u("STRAIGHT_DENSE")
                                sp = (u1 - u0) * rng_.uniform(0.9, 1.0)
                                us = u0 + rng_.uniform(0, (u1 - u0) - sp)
                                if rng_.random() < 0.5:
                                    us, sp = us + sp, -sp
                                m = len(idx)
                                vv = list(map(tuple, seg_p - ac * hw)) + list(map(tuple, seg_p + ac * hw))
                                ff = [[j, j + 1, m + j + 1, m + j] for j in range(m - 1)]
                                vcoord = list(np.clip((sarc[idx] - s0) / seg_len * 0.98 + 0.01, 0.01, 0.995))
                                SHEET_CARDS["cap" if capped else "full"].append((vv, ff, [us] * m + [us + sp] * m, vcoord + vcoord))
                            if s0 + seg_len >= sarc[-1] - 1e-6:
                                break
                            s0 += seg_len * rng_.uniform(0.5, 0.65)
            return ex
        add_short("LongStraight", "Long Straight", dict(slick, top=0.05, side=0.04, groove=0.3,
                                                        cards=dict(straight_cards("back", 0.35, 0.25), defer=True)),
                  curtain(1.9, 0.25, False))
        add_short("Bob", "Chin Bob", dict(slick, top=0.06, side=0.045, part=0.2, groove=0.3,
                                          cards=dict(straight_cards("part", 0.3, 0.22), part=0.2, defer=True)),
                  curtain(1.0, 0.45, True, part_x=0.2))
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


def onto_radial(H, p, lift):
    """the skin under p, looking in towards the middle of the head (works on the brow ridge and the temple)"""
    q = np.array(p, float)
    c = np.array([H.anchor[0], H.centre[1], q[2] - 0.05])
    d = q - c
    d /= max(np.linalg.norm(d), 1e-9)
    hit = H.bvh.ray_cast(Vector(c + d * 1.5), Vector(-d), 1.5)
    if hit[0] is not None:
        loc, nrm = np.array(hit[0]), np.array(hit[1])
    else:
        loc, nrm, fi, dd = H.nearest(q)
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


def raster(uv, val, tris, res):
    """paint a per-vertex value into a res x res map through the mesh's UVs (rows = V)"""
    img = np.zeros((res, res))
    P = uv * (res - 1)
    for a, b, c in tris:
        pa, pb, pc = P[a], P[b], P[c]
        x0, y0 = np.floor(np.minimum.reduce([pa, pb, pc])).astype(int)
        x1, y1 = np.ceil(np.maximum.reduce([pa, pb, pc])).astype(int) + 1
        xs, ys = np.meshgrid(np.arange(max(x0, 0), min(x1, res)), np.arange(max(y0, 0), min(y1, res)))
        if xs.size == 0:
            continue
        m = np.array([[pb[0] - pa[0], pc[0] - pa[0]], [pb[1] - pa[1], pc[1] - pa[1]]])
        if abs(np.linalg.det(m)) < 1e-12:
            continue
        l12 = np.linalg.solve(m, np.stack([xs.ravel() - pa[0], ys.ravel() - pa[1]]))
        l0 = 1 - l12.sum(0)
        ok = (l0 > -0.02) & (l12[0] > -0.02) & (l12[1] > -0.02)
        v = l0 * val[a] + l12[0] * val[b] + l12[1] * val[c]
        img[ys.ravel()[ok], xs.ravel()[ok]] = np.maximum(img[ys.ravel()[ok], xs.ravel()[ok]], v[ok])
    return img


def stubble_texture(H, ob, cov, name, dens, res=1024):
    """stubble UVs wrap round the jaw (no stretching), and its own map holds fine speckles whose density follows
    the coverage, so the stubble thins out at every edge instead of stopping at a line"""
    me = ob.data
    co = np.array([v.co[:] for v in me.vertices])
    a = np.arctan2(co[:, 0] - H.anchor[0], -(co[:, 1] - H.centre[1]))         # 0 at the chin, +-pi/2 at the ears
    u = a * H.R
    v = co[:, 2]
    span = max(u.max() - u.min(), v.max() - v.min()) * 1.02
    uu = (u - u.min()) / span + 0.005
    vv = (v - v.min()) / span + 0.005
    loops = np.array([l.vertex_index for l in me.loops])
    uvl = me.uv_layers.get("UVMap") or me.uv_layers.new(name="UVMap")
    uvl.data.foreach_set("uv", np.stack([uu[loops], vv[loops]], 1).ravel())
    me.calc_loop_triangles()
    tris = [tuple(t.vertices) for t in me.loop_triangles]
    c = raster(np.stack([uu, vv], 1), np.clip(cov, 0, 1), tris, res)
    rng = np.random.default_rng(len(name))
    r = rng.random((res, res))
    dots = (r < dens * smoothstep(0.0, 1.0, c) ** 1.3).astype(float)
    dots = np.clip(0.75 * dots + 0.12 * (np.roll(dots, 1, 0) + np.roll(dots, 1, 1)), 0, 1)
    shade = 0.75 + 0.25 * rng.random((res, res))
    TEX["NC_" + name] = _save_png("NC_" + name, np.dstack([shade, shade, shade, dots]))


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
            # the tail stops just past the outer corner of the eye, never out on the temple
            length = min(length, abs(e[0] - H.anchor[0]) + 0.085 - gap)
            n, rows = 18, 4
            verts, us, vs = [], [], []
            for i in range(n):
                t = i / (n - 1)
                x = H.anchor[0] + sx * (gap + length * t)
                rise = arch * math.sin(math.pi * min(1.0, t / 0.7) * 0.5) if t < 0.7 else arch * (1 - 1.6 * (t - 0.7))
                z = e[2] + 0.1 + lift + rise
                w = w_in + (w_pk - w_in) * min(1, t / 0.6) if t < 0.6 else w_pk + (w_tail - w_pk) * (t - 0.6) / 0.4
                # the card is wider than the brow: the texture fades its top and bottom edges to nothing
                w *= (1.15 if H.gender == "Male" else 0.85) * 1.7
                for r in range(rows):
                    v = r / (rows - 1)
                    zz = z + (v - 0.45) * w - 0.004 * t * (1 - v)         # the tail tips down a little
                    verts.append(onto_radial(H, np.array([x, e[1], zz]), 0.0035))
                    us.append(t)
                    vs.append(v)
            faces = []
            for i in range(n - 1):
                for r in range(rows - 1):
                    a = i * rows + r
                    q = [a, a + rows, a + rows + 1, a + 1]
                    faces.append(q if sx > 0 else q[::-1])
            b.add(verts, faces, us, vs)
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
    ears = H.co[H.mask["ears"]]
    kd2 = KDTree(len(ears))
    for i, p in enumerate(ears):
        kd2.insert(p, i)
    kd2.balance()
    eard = np.array([kd2.find(v)[2] for v in V])
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
        lips = lipd - 0.02
        sideburn = np.where(rel[:, 1] > -0.1 * H.R, (H.ear_z + 0.05 + up) - V[:, 2], 1.0)
        field = np.minimum.reduce([cheek + 0.01 * noise(V, 30), neck, front, lips, sideburn])
        field = np.minimum(field, eard - 0.035)                                              # never on the ears
        cov = np.clip(field / (0.05 if name == "Stubble" else 0.04), 0, 1)       # stubble thins out at its edges
        ob = shell(name, V, F, Nf, np.zeros(len(V)), field=field, lift=0.0025, uv=(cov, np.zeros(len(V))))
        stubble_texture(H, ob, UVS.pop(ob.name)[0], name, 0.4 if name == "Stubble" else 0.72)
        out[name] = ob
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
TEX = make_textures()
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
    # without the hanging arms (below the shoulders), so long hair falls down the back and chest, not out over them
    nz = H.J["neck"][2]
    fs = [f for f in fs if not (abs(co[f, 0].mean()) > 0.62 and co[f, 2].mean() < nz - 0.4)]
    SHOULDERS[gender] = BVHTree.FromPolygons([tuple(v) for v in co], fs)
    styles, fine = build_styles(H)
    face = face_pieces(H)
    marks = face_landmarks(H)
    A = H.anchor
    pieces = {}
    hair_col = tex_material("NC_Hair", TEX["NC_HairEdge"])
    fade_col = tex_material("NC_HairFaded", TEX["NC_HairFade"])
    card_col = card_material("NC_HairCard")
    for key, st in styles.items():
        for kind in ("hair", "cap"):
            ob = st[kind]
            ob.data.materials.append(fade_col if st.get("skin_fade") else hair_col)
            pieces[ob.name] = (ob, {"hair": "Hair", "cap": "HairCap"}[kind], key, st["label"])
        for kind in ("cards", "capcards"):
            ob = st.get(kind)
            if ob is not None:
                ob.data.materials.append(card_col)
                knd = {"cards": "HairCards", "capcards": "HairCapCards"}[kind]
                # (Roblox takes 20k triangles a MeshPart: big card sets are split into _2, _3 ... parts instead of
                #  decimated, which collapsed card ends into blunt chunks)
                for ob_ in split_cards(ob, 18000):
                    pieces[ob_.name] = (ob_, knd, key, st["label"])
    for name, ob in face.items():
        kind = name.split("_")[0]
        col = {"Brows": tex_material("NC_Brows", TEX["NC_Brow"]), "LashLine": material("Lash", (0.03, 0.025, 0.02, 1)),
               "Lips": material("Lip", (0.62, 0.36, 0.33, 1)),
               "Stubble": tex_material("NC_Stubble", TEX["NC_Stubble"]),
               "StubbleHeavy": tex_material("NC_StubbleHeavy", TEX["NC_StubbleHeavy"])}[kind]
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
            uvl = ob.data.uv_layers.get("UVMap")
            if uvl is not None and kind in ("Hair", "HairCap"):
                # only the solid hair (twists, locs, full scalp) is thinned: collapsing edges in the see-through edge
                # and fade would drag hairline UVs across whole triangles and leave bald triangles in the fade
                umin = np.ones(len(ob.data.vertices))
                np.minimum.at(umin, np.array([l.vertex_index for l in ob.data.loops]), np.array([d.uv[0] for d in uvl.data]))
                vg = ob.vertex_groups.new(name="NC_Decimate")
                vg.add([int(i) for i in np.nonzero(umin > 0.95)[0]], 1.0, "REPLACE")
                md.vertex_group = vg.name
            bpy.context.view_layer.objects.active = ob
            bpy.ops.object.select_all(action="DESELECT")
            ob.select_set(True)
            bpy.ops.object.modifier_apply(modifier=md.name)
            ob.vertex_groups.clear()
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
    # Studio refuses FBX files over 20 MB, so the hair cards go in their own files (NC_Head_<Gender>_Cards<n>.fbx),
    # a few styles each; AssembleHeads takes any number of these files
    olds = {}
    for name, (ob, *_r) in pieces.items():
        olds[ob] = ob.name
        ob.name = name
    is_card = lambda n: bool(re.search(r"Cards(_\d+)?$", n))
    base = [n for n in pieces if not is_card(n)]
    cards = [n for n in pieces if is_card(n)]
    groups = [("", base)]
    CARD_TRIS_PER_FILE = 60000
    cur, tri_sum = [], 0
    tris_of = {i["mesh"]: i["tris"] for i in info}
    for n in cards:
        if cur and tri_sum + tris_of[n] > CARD_TRIS_PER_FILE:
            groups.append((f"_Cards{len(groups)}", cur))
            cur, tri_sum = [], 0
        cur.append(n)
        tri_sum += tris_of[n]
    if cur:
        groups.append((f"_Cards{len(groups)}", cur))
    for f_ in os.listdir(OUT):                               # (no stale card files from an earlier build)
        if f_.startswith(f"NC_Head_{gender}_Cards") and f_.endswith(".fbx"):
            os.remove(os.path.join(OUT, f_))
    for suffix, names in groups:
        bpy.ops.object.select_all(action="DESELECT")
        for n in names:
            pieces[n][0].select_set(True)
        bpy.context.view_layer.objects.active = pieces[names[0]][0]
        bpy.ops.export_scene.fbx(filepath=os.path.join(OUT, f"NC_Head_{gender}{suffix}.fbx"), use_selection=True,
                                 object_types={"MESH"}, apply_scale_options="FBX_SCALE_UNITS", mesh_smooth_type="FACE",
                                 path_mode="COPY", embed_textures=True)
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
-- NC_Head_Male.fbx, NC_Head_Female.fbx and every NC_Head_<Gender>_Cards<n>.fbx with the 3D Importer. Select all the
-- imported models (or just the ones you re-imported), paste this, press Enter.
-- The pieces go to ReplicatedStorage.NC_HeadAssets.<Gender>, where NCHead (the Character Studio) finds them.
local Selection = game:GetService("Selection")
local RS = game:GetService("ReplicatedStorage")
local root = RS:FindFirstChild("NC_HeadAssets") or Instance.new("Folder")
root.Name = "NC_HeadAssets"
root.Parent = RS
local done = 0
-- hair cards: the strand normal and roughness maps. If the 3D Importer didn't bring them in, upload
-- textures_heads/NC_HairCard_Normal.png and NC_HairCard_Rough.png and paste their rbxassetid:// ids here.
local CARD_NORMAL = ""
local CARD_ROUGH = ""
for _, model in ipairs(Selection:Get()) do
\tlocal gender = model.Name:match("NC_Head_(%a+)")
\tif not gender then
\t\twarn("AssembleHeads: keep NC_Head_<Gender> in the name of " .. model.Name)
\t\tcontinue
\tend
\t-- (the pieces come in several files: NC_Head_<Gender>.fbx and NC_Head_<Gender>_Cards<n>.fbx, so each piece
\t--  replaces its old copy by name and the rest of the folder stays)
\tlocal folder = root:FindFirstChild(gender)
\tif not folder then
\t\tfolder = Instance.new("Folder")
\t\tfolder.Name = gender
\tend
\tfor _, part in ipairs(model:GetDescendants()) do
\t\tif part:IsA("MeshPart") then
\t\t\tpart.Anchored = false
\t\t\tpart.CanCollide, part.CanTouch, part.CanQuery, part.Massless = false, false, false, true
\t\t\tpart.CastShadow = false
\t\t\t-- full detail at every distance: the automatic level of detail swaps in a coarse mesh further away, which
\t\t\t-- showed the hair as a hard-edged cap with no fade
\t\t\tpcall(function()
\t\t\t\tpart.RenderFidelity = Enum.RenderFidelity.Precise
\t\t\tend)
\t\t\t-- hair, brows and stubble keep their greyscale texture as a SurfaceAppearance with soft alpha
\t\t\tlocal sa = part:FindFirstChildOfClass("SurfaceAppearance")
\t\t\tif not sa and part.TextureID ~= "" then
\t\t\t\tsa = Instance.new("SurfaceAppearance")
\t\t\t\tsa.ColorMap = part.TextureID
\t\t\t\tsa.Parent = part
\t\t\tend
\t\t\tpart.TextureID = ""
\t\t\tlocal isCards = part.Name:match("_Cards$") or part.Name:match("_CapCards$") or part.Name:match("_Cards_%d+$") or part.Name:match("_CapCards_%d+$")
\t\t\tif sa then
\t\t\t\tsa.AlphaMode = Enum.AlphaMode.Transparency
\t\t\t\tif isCards then
\t\t\t\t\t-- cards keep the strand normal/roughness so light runs along the hair
\t\t\t\t\tif CARD_NORMAL ~= "" then sa.NormalMap = CARD_NORMAL end
\t\t\t\t\tif CARD_ROUGH ~= "" then sa.RoughnessMap = CARD_ROUGH end
\t\t\t\t\tsa.MetalnessMap = ""
\t\t\t\telse
\t\t\t\t\tsa.NormalMap, sa.RoughnessMap, sa.MetalnessMap = "", "", ""
\t\t\t\tend
\t\t\tend
\t\t\t-- a card is one thin ribbon: seen from behind it must still draw
\t\t\tpart.DoubleSided = isCards and true or false
\t\t\tfor _, ch in ipairs(part:GetChildren()) do
\t\t\t\tif not (ch:IsA("Attachment") or ch == sa) then
\t\t\t\t\tch:Destroy()
\t\t\t\tend
\t\t\tend
\t\t\tlocal prev = folder:FindFirstChild(part.Name)
\t\t\tif prev then
\t\t\t\tprev:Destroy()
\t\t\tend
\t\t\tpart.Parent = folder
\t\t\tdone += 1
\t\tend
\tend
\tfolder.Parent = root
\tmodel:Destroy()
end
-- drop pieces a newer build no longer makes (NCHead would still wear them): anything not listed in NCHeadData
local removed = 0
local okData, data = pcall(function()
\tlocal m = RS:FindFirstChild("NCHeadData")
\treturn m and require(m:Clone())
end)
if okData and data then
\tfor _, folder in ipairs(root:GetChildren()) do
\t\tlocal listed = data[folder.Name] and data[folder.Name].pieces
\t\tif listed then
\t\t\tfor _, part in ipairs(folder:GetChildren()) do
\t\t\t\tif part:IsA("MeshPart") and not listed[part.Name] then
\t\t\t\t\tpart:Destroy()
\t\t\t\t\tremoved += 1
\t\t\t\tend
\t\t\tend
\t\tend
\tend
else
\twarn("AssembleHeads: update ReplicatedStorage.NCHeadData first, then run this again to remove old pieces")
end
print("AssembleHeads: " .. done .. " hair and face pieces ready in ReplicatedStorage.NC_HeadAssets, " .. removed .. " old ones removed")
"""
with open(os.path.join(OUT, "AssembleHeads.lua"), "w", encoding="utf-8") as f:
    f.write(ASSEMBLE)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "NeonCoast_Heads.blend"))
print("NC_HEADS_DONE")
