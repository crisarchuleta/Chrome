# Neon Coast modesty base layer for MakeHuman (MPFB) bodies. NO NUDITY, EVER (Roblox rules; the account was banned
# before). Every body gets, permanently:
#   1. an "NC_Modesty" shape key (value 1, locked on) that smooths away all anatomy under the clothes, so even a
#      missing or broken garment can never show anything;
#   2. a fitted undershirt and boxer shorts made from the body's own surface, parented to the body.
# Pure bpy + numpy (no add-on needed). build_makehuman.py calls add_base_layer(h, female) for every human.
import bpy
import numpy as np

SHIRT_RGBA = (0.23, 0.235, 0.26, 1.0)   # matches NCLookBuilder.BASE_LAYER (undershirt)
SHORTS_RGBA = (0.15, 0.157, 0.18, 1.0)  # matches NCLookBuilder.BASE_LAYER (shorts)


def _groups(obj):
    names = {g.index: g.name for g in obj.vertex_groups}
    out = {}
    for v in obj.data.vertices:
        for g in v.groups:
            if g.weight > 0.01:
                out.setdefault(names[g.group], []).append(v.index)
    return {k: np.array(v) for k, v in out.items()}


def _eval_coords(obj):
    shown = [m.show_viewport for m in obj.modifiers]
    for m in obj.modifiers:
        m.show_viewport = False
    dg = bpy.context.evaluated_depsgraph_get()
    ev = obj.evaluated_get(dg)
    me = ev.to_mesh()
    co = np.array([v.co[:] for v in me.vertices])
    ev.to_mesh_clear()
    for m, s in zip(obj.modifiers, shown):
        m.show_viewport = s
    return co


def _labels(co, G):
    """R15-style region for every body vertex, from MakeHuman's joint helper cubes (Blender axes, Z up)."""
    body = G["body"]
    J = {k[6:]: co[v].mean(0) for k, v in G.items() if k.startswith("joint-")}
    H = co[body, 2].max() - co[body, 2].min()
    k = H / 6.6  # radii below were tuned in studs on a 6.6-stud body
    segs = []
    for s in ("l", "r"):
        segs += [("UArm", J[s + "-shoulder"], J[s + "-elbow"], 0.22), ("LArm", J[s + "-elbow"], J[s + "-hand"], 0.2),
                 ("Hand", J[s + "-hand"], J[s + "-finger-3-4"], 0.18), ("ULeg", J[s + "-upper-leg"], J[s + "-knee"], 0.36),
                 ("LLeg", J[s + "-knee"], J[s + "-ankle"], 0.26), ("Foot", J[s + "-ankle"], J[s + "-toe-3-1"], 0.2),
                 ("Torso", J[s + "-clavicle"], J[s + "-shoulder"], 0.42)]
    segs += [("Torso", J["pelvis"], J["neck"], 0.62), ("Head", J["neck"], J.get("head-2", J["head"]), 0.5)]
    P = co[body]
    best = np.full(len(P), 1e9)
    lab = np.empty(len(P), dtype=object)
    tpar = np.zeros(len(P))
    for name, a, b, rad in segs:
        ab = b - a
        t = np.clip(((P - a) @ ab) / (ab @ ab), 0, 1)
        d = np.linalg.norm(P - (a + t[:, None] * ab), axis=1) / (rad * k)
        m = d < best
        best[m], lab[m], tpar[m] = d[m], name, t[m]
    lab[P[:, 2] > J["neck"][2]] = "Head"
    return body, lab, tpar, J


def _smooth(co, edges, iters, nv):
    deg = np.bincount(edges.ravel(), minlength=nv).astype(float)
    out = co.copy()
    for it in range(int(iters.max()) if len(iters) else 0):
        acc = np.zeros_like(out)
        np.add.at(acc, edges[:, 0], out[edges[:, 1]])
        np.add.at(acc, edges[:, 1], out[edges[:, 0]])
        avg = acc / np.maximum(deg, 1)[:, None]
        m = (iters > it) & (deg > 0)
        out[m] += 0.5 * (avg[m] - out[m])
    return out


def _normals(co, faces, nv):
    n = np.zeros((nv, 3))
    for f in faces:
        if len(f) >= 3:
            n[f] += np.cross(co[f[1]] - co[f[0]], co[f[2]] - co[f[0]])
    return n / np.maximum(np.linalg.norm(n, axis=1), 1e-12)[:, None]


def _material(name, rgba):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.diffuse_color = rgba
    m.use_nodes = True
    bsdf = m.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = rgba
        bsdf.inputs["Roughness"].default_value = 0.85
    return m


def add_base_layer(obj, female=False):
    for ch in list(obj.children):
        if ch.get("nc_base_layer"):
            bpy.data.objects.remove(ch, do_unlink=True)
    co = _eval_coords(obj)
    G = _groups(obj)
    nv = len(co)
    body, lab, tpar, J = _labels(co, G)
    in_body = np.zeros(nv, bool)
    in_body[body] = True
    region = np.empty(nv, dtype=object)
    region[body] = lab
    t = np.zeros(nv)
    t[body] = tpar
    me = obj.data
    edges = np.array([e.vertices[:] for e in me.edges])
    edges = edges[in_body[edges[:, 0]] & in_body[edges[:, 1]]]
    faces = [list(p.vertices) for p in me.polygons if all(in_body[v] for v in p.vertices)]

    pelvis_z, neck_z = J["pelvis"][2], J["neck"][2]
    torso = (region == "Torso")
    shirt = torso & (co[:, 2] > pelvis_z + 0.06 * (neck_z - pelvis_z))
    shirt |= (region == "UArm") & (t < 0.38)               # short cap sleeves
    shorts = torso & (co[:, 2] <= pelvis_z + 0.16 * (neck_z - pelvis_z))
    shorts |= (region == "ULeg") & (t < 0.5)               # boxer shorts to mid-thigh
    covered = shirt | shorts

    # 1. modesty shape key: smooth away anatomy everywhere under the clothes (hard on the groin and chest detail)
    iters = np.zeros(nv)
    iters[covered] = 6
    near_groin = shorts & ((region == "Torso") | (t < 0.3))
    iters[near_groin] = 70
    for gname, n in (("genitals", 90), ("nipple", 40), ("nippleTip", 40)):
        if gname in G:
            iters[G[gname]] = np.maximum(iters[G[gname]], n)
    if not female:
        iters[torso & (co[:, 2] > pelvis_z + 0.5 * (neck_z - pelvis_z))] = np.maximum(iters[torso & (co[:, 2] > pelvis_z + 0.5 * (neck_z - pelvis_z))], 14)
    S = _smooth(co, edges, iters, nv)
    S[~in_body] = co[~in_body]
    if not me.shape_keys:
        obj.shape_key_add(name="Basis")
    key = me.shape_keys.key_blocks.get("NC_Modesty") or obj.shape_key_add(name="NC_Modesty", from_mix=False)
    basis = me.shape_keys.reference_key
    base = np.array([d.co[:] for d in basis.data])
    delta = S - co
    for i, d in enumerate(key.data):
        d.co = base[i] + delta[i]
    key.value = 1.0
    key.slider_min = 1.0  # cannot be dialled off
    key.mute = False

    # 2. garments from the smoothed surface, pushed out so the body can never poke through
    N = _normals(S, faces, nv)
    made = []
    for gname, mask, off, rgba in (("Undershirt", shirt, 0.010, SHIRT_RGBA), ("Shorts", shorts, 0.014, SHORTS_RGBA)):
        fs = [f for f in faces if sum(mask[v] for v in f) * 2 >= len(f)]  # half or more inside: no gaps at hems
        used = sorted({v for f in fs for v in f})
        remap = {v: i for i, v in enumerate(used)}
        V = np.array([S[v] + N[v] * off for v in used])
        # even out the hems: relax the open edges (neck, sleeves, waist, legs) along themselves
        cnt = {}
        for f in fs:
            for a, b in zip(f, f[1:] + f[:1]):
                e = (min(a, b), max(a, b))
                cnt[e] = cnt.get(e, 0) + 1
        bnd = np.array([[remap[a], remap[b]] for (a, b), c in cnt.items() if c == 1])
        if len(bnd):
            for _ in range(25):
                acc = np.zeros_like(V); deg = np.zeros(len(V))
                np.add.at(acc, bnd[:, 0], V[bnd[:, 1]]); np.add.at(acc, bnd[:, 1], V[bnd[:, 0]])
                np.add.at(deg, bnd[:, 0], 1); np.add.at(deg, bnd[:, 1], 1)
                m = deg > 0
                V[m] += 0.5 * (acc[m] / deg[m][:, None] - V[m])
        verts = [tuple(x) for x in V]
        gm = bpy.data.meshes.new(obj.name + "_" + gname)
        gm.from_pydata(verts, [], [[remap[v] for v in f] for f in fs])
        gm.update()
        for p in gm.polygons:
            p.use_smooth = True
        go = bpy.data.objects.new(obj.name + "_" + gname, gm)
        go["nc_base_layer"] = True
        go.data.materials.append(_material("NC_BaseLayer_" + gname, rgba))
        sol = go.modifiers.new("Thickness", "SOLIDIFY")
        sol.thickness = 0.004
        sol.offset = 1.0
        for c in obj.users_collection:
            c.objects.link(go)
        go.parent = obj
        go.matrix_parent_inverse = obj.matrix_world.inverted()
        go.matrix_world = obj.matrix_world.copy()
        made.append(go)
    obj["nc_base_layer"] = "undershirt+shorts"
    return made
