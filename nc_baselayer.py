# Neon Coast modesty base layer for MakeHuman (MPFB) bodies. NO NUDITY, EVER (Roblox rules; the account was banned
# before). Every body gets, permanently:
#   1. an "NC_Modesty" shape key (value 1, locked on) that smooths away all anatomy under the clothes, so even a
#      missing or broken garment can never show anything;
#   2. a thin, skin-tight white tank top and boxer shorts made from the body's own surface, parented to the body.
#      Both are fully opaque (Roblox modesty layers must be opaque).
# Pure bpy + numpy (no add-on needed). build_makehuman.py calls add_base_layer(h, female) for every human.
import bpy
import numpy as np

SHIRT_RGBA = (0.86, 0.86, 0.84, 1.0)   # white tank top (matches NCLookBuilder.BASE_LAYER.Torso)
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
    """Taubin smoothing (a shrink step then an inflate step), so smoothed areas keep their volume and shape."""
    deg = np.bincount(edges.ravel(), minlength=nv).astype(float)
    out = co.copy()
    for it in range(int(iters.max()) if len(iters) else 0):
        m = (iters > it) & (deg > 0)
        for lam in (0.5, -0.53):
            acc = np.zeros_like(out)
            np.add.at(acc, edges[:, 0], out[edges[:, 1]])
            np.add.at(acc, edges[:, 1], out[edges[:, 0]])
            avg = acc / np.maximum(deg, 1)[:, None]
            out[m] += lam * (avg[m] - out[m])
    return out


def _smooth_plain(co, edges, iters, nv):
    deg = np.bincount(edges.ravel(), minlength=nv).astype(float)
    out = co.copy()
    for it in range(int(iters.max()) if len(iters) else 0):
        m = (iters > it) & (deg > 0)
        acc = np.zeros_like(out)
        np.add.at(acc, edges[:, 0], out[edges[:, 1]])
        np.add.at(acc, edges[:, 1], out[edges[:, 0]])
        out[m] += 0.5 * (acc[m] / np.maximum(deg, 1)[m][:, None] - out[m])
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


RIB_TILE_M = 0.01  # one texture tile = 1 cm x 1 cm (4 ribs), so the knit is the same size on every body


def _rib_pixels(n=64):
    """Tiling ribbed-knit colour + normal maps (vertical 1x1 rib, 4 ribs a tile) as float RGB arrays, row 0 = bottom."""
    x = (np.arange(n) + 0.5) / n
    ph = np.sin(2 * np.pi * 4 * x)                      # rib profile across the tile
    hgt = np.sign(ph) * np.abs(ph) ** 0.6
    y = (np.arange(n) + 0.5) / n
    knit = 0.04 * np.cos(2 * np.pi * 16 * y)[:, None] * (np.abs(ph)[None, :])  # faint stitch rows along each rib
    shade = 0.96 + 0.04 * hgt[None, :] + 0.5 * knit
    col = np.clip(np.repeat(shade[:, :, None], 3, 2) * np.array(SHIRT_RGBA[:3]), 0, 1)
    dh = np.gradient(np.tile(hgt, (n, 1)) * 0.6 + knit * 2, axis=1)
    nrm = np.stack([-dh * 0.8, np.zeros_like(dh), np.ones_like(dh)], 2)
    nrm /= np.linalg.norm(nrm, axis=2, keepdims=True)
    return {"NC_TankRib_Color": col, "NC_TankRib_Normal": nrm * 0.5 + 0.5}


def write_rib_pngs(folder):
    """Write the rib maps as PNG files (raw values, no view transform) for FBX export / Roblox SurfaceAppearance."""
    import os
    paths = {}
    for name, arr in _rib_pixels().items():
        n = arr.shape[0]
        im = bpy.data.images.new(name + "_out", n, n, alpha=False, float_buffer=False)
        if name.endswith("Normal"):
            im.colorspace_settings.name = "Non-Color"
        im.pixels.foreach_set(np.concatenate([arr, np.ones((n, n, 1))], 2).astype(np.float32).ravel())
        im.filepath_raw = os.path.join(folder, name + ".png")
        im.file_format = "PNG"
        im.save()
        bpy.data.images.remove(im)
        paths[name] = os.path.join(folder, name + ".png")
    return paths


def _rib_image():
    """The rib maps as images packed into the .blend."""
    out = {}
    for name, arr in _rib_pixels().items():
        n = arr.shape[0]
        im = bpy.data.images.get(name) or bpy.data.images.new(name, n, n, alpha=False)
        if name.endswith("Normal"):
            im.colorspace_settings.name = "Non-Color"
        im.pixels.foreach_set(np.concatenate([arr, np.ones((n, n, 1))], 2).astype(np.float32).ravel())
        im.pack()
        out[name] = im
    return out


def _rib_material(name, rgba):
    m = _material(name, rgba)
    ims = _rib_image()
    nt = m.node_tree
    bsdf = nt.nodes.get("Principled BSDF")
    tc = nt.nodes.new("ShaderNodeTexImage"); tc.image = ims["NC_TankRib_Color"]
    tn = nt.nodes.new("ShaderNodeTexImage"); tn.image = ims["NC_TankRib_Normal"]
    nm = nt.nodes.new("ShaderNodeNormalMap"); nm.inputs["Strength"].default_value = 0.5
    nt.links.new(tc.outputs["Color"], bsdf.inputs["Base Color"])
    # the normal map is packed for Roblox SurfaceAppearance (NormalMap) but not linked here: Blender's FBX/glTF
    # exporters and Roblox import only the colour map reliably
    nt.links.new(tn.outputs["Color"], nm.inputs["Color"])
    m["nc_rib_tile_m"] = RIB_TILE_M
    return m


def _rib_uvs(mesh, V, cx, cy):
    """Cylindrical UVs in real size: U runs round the body (ribs stay vertical), V runs up; 1 UV unit = 1 tile."""
    ang = np.arctan2(V[:, 0] - cx, -(V[:, 1] - cy))            # 0 at the front centre, seam at the back
    r = np.hypot(V[:, 0] - cx, V[:, 1] - cy)
    rm = np.median(r)
    u = ang * rm / RIB_TILE_M
    v = (V[:, 2] - V[:, 2].min()) / RIB_TILE_M
    uv = mesh.uv_layers.new(name="UVMap")
    loops = np.array([l.vertex_index for l in mesh.loops])
    uu, vv = u[loops].copy(), v[loops]
    # no wrap across the back seam: keep each face on one side
    for p in mesh.polygons:
        idx = list(range(p.loop_start, p.loop_start + p.loop_total))
        a = ang[loops[idx]]
        if a.max() - a.min() > np.pi:
            for i in idx:
                if ang[loops[i]] < 0:
                    uu[i] += 2 * np.pi * rm / RIB_TILE_M
    uv.data.foreach_set("uv", np.stack([uu, vv], 1).ravel())


def add_base_layer(obj, female=False):
    for ch in list(obj.children):
        if ch.get("nc_base_layer"):
            bpy.data.objects.remove(ch, do_unlink=True)
    if obj.data.shape_keys and "NC_Modesty" in obj.data.shape_keys.key_blocks:
        obj.shape_key_remove(obj.data.shape_keys.key_blocks["NC_Modesty"])  # rebuild from the plain body
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
    H = co[body, 2].max() - co[body, 2].min()
    torso = (region == "Torso")
    # tank top (person's reference photo, 2026-11-23): ribbed knit, high round neck with only a slight dip,
    # wide straps (~5.5 cm), athletic armholes that cut in at the shoulder and end just under the armpit,
    # fitted to the hip
    sh_x = abs(J["l-shoulder"][0] - J["r-shoulder"][0]) / 2
    sh_top = J["l-shoulder"][2] + 0.02 * H
    armpit_z = J["l-shoulder"][2] - (0.035 if female else 0.05) * H   # women: higher armholes, no side gap
    cx = (J["l-shoulder"][0] + J["r-shoulder"][0]) / 2
    rel_x = np.abs(co[:, 0] - cx)
    neck_hw = (0.36 if female else 0.4) * sh_x          # half-width of the neck opening
    strap_out = neck_hw + 0.031 * H                      # ~5.5 cm strap on a 1.78 m body
    side_x = 0.9 * sh_x
    shirt = torso & (co[:, 2] > pelvis_z + 0.06 * (neck_z - pelvis_z))
    # armhole: a smooth curve from the outer strap edge on the shoulder down to the side seam under the arm
    s_ = np.clip((co[:, 2] - armpit_z) / max(sh_top - armpit_z, 1e-6), 0, 1)
    x_edge = side_x - (side_x - strap_out) * (1 - (1 - s_) ** 2.2)
    shirt &= ~((co[:, 2] > armpit_z) & (rel_x > x_edge))
    shirt &= rel_x < side_x                                        # nothing past the sides onto the arms
    front = co[:, 1] < J["neck"][1]
    # high round neck: the back sits at the base of the neck, the front dips only slightly
    rr = np.clip(rel_x / neck_hw, 0, 1)
    dip = np.where(front, 0.02 + 0.016 * np.sqrt(1 - rr ** 2), 0.018 + 0.004 * np.sqrt(1 - rr ** 2)) * H
    shirt &= ~((co[:, 2] > neck_z - dip) & (rel_x < neck_hw))
    shorts = torso & (co[:, 2] <= pelvis_z + 0.16 * (neck_z - pelvis_z))
    shorts |= (region == "ULeg") & (t < 0.5)               # boxer shorts to mid-thigh
    covered = shirt | shorts

    # 1. modesty shape key: smooth away anatomy only where it is (groin, nipples), fading out so the hips keep
    #    their natural shape; Taubin smoothing keeps the volume
    iters = np.zeros(nv)
    iters[covered] = 2

    def spot(group, radius, n):
        if group not in G or not len(G[group]):
            return
        c = co[G[group]].mean(0)
        d = np.linalg.norm(co - c, axis=1)
        w = np.clip(1 - d / radius, 0, 1) * covered
        iters[:] = np.maximum(iters, np.round(w * n))
        iters[G[group]] = np.maximum(iters[G[group]], n)
    spot("genitals", 0.10 * H, 70)
    spots = np.zeros(nv)
    for gname in ("nipple", "nippleTip"):
        if gname not in G:
            continue
        for half in (co[G[gname], 0] > cx, co[G[gname], 0] <= cx):
            idx = G[gname][half]
            if len(idx):
                c = co[idx].mean(0)
                d = np.linalg.norm(co - c, axis=1)
                w = np.clip(1 - d / ((0.06 if female else 0.04) * H), 0, 1) * covered
                spots = np.maximum(spots, np.round(w * (60 if female else 40)))
                # round off the whole chest contour (Taubin keeps the volume, removes any point)
                w2 = np.clip(1.3 - d / ((0.11 if female else 0.07) * H), 0, 1) * covered
                iters[:] = np.maximum(iters, np.round(w2 * (60 if female else 25)))
    S = _smooth(co, edges, iters, nv)
    S = _smooth_plain(S, edges, spots, nv)
    # groin: replace the front with a smooth surface fitted to the hips and thighs around it (like a mannequin)
    if "genitals" in G and len(G["genitals"]):
        c = S[G["genitals"]].mean(0)
        r = 0.06 * H
        d = np.linalg.norm(S - c, axis=1)
        ring = np.where(in_body & (d > r) & (d < 1.7 * r) & (S[:, 1] < c[1] + 0.02 * H))[0]
        inner = np.where(in_body & (d <= r))[0]
        Ng = _normals(S, faces, nv)
        n = Ng[ring].mean(0); n /= np.linalg.norm(n)
        u = np.cross(n, [0, 0, 1.0]); u /= np.linalg.norm(u); v = np.cross(n, u)
        q = S[ring] - c
        a, b, h = q @ u, q @ v, q @ n
        k = np.linalg.lstsq(np.stack([np.ones_like(a), a, b, a * a, a * b, b * b], 1), h, rcond=None)[0]
        q = S[inner] - c
        a, b, h = q @ u, q @ v, q @ n
        hn = np.stack([np.ones_like(a), a, b, a * a, a * b, b * b], 1) @ k
        S[inner] = c + a[:, None] * u + b[:, None] * v + np.minimum(h, hn)[:, None] * n
    # nipples: replace the whole tip with a smooth dome fitted to the skin around it, so no point or bump is left
    faces_all = faces
    if "nipple" in G:
        Nn = _normals(S, faces_all, nv)
        for half in (co[G["nipple"], 0] > cx, co[G["nipple"], 0] <= cx):
            idx = G["nipple"][half]
            if not len(idx):
                continue
            c = S[idx].mean(0)
            r = (0.024 if female else 0.018) * H
            d = np.linalg.norm(S - c, axis=1)
            ring = np.where(in_body & (d > r) & (d < 1.8 * r))[0]
            inner = np.where(in_body & (d <= r))[0]
            n = Nn[ring].mean(0); n /= np.linalg.norm(n)
            u = np.cross(n, [0, 0, 1.0]); u /= np.linalg.norm(u); v = np.cross(n, u)
            def local(P):
                q = P - c
                return q @ u, q @ v, q @ n
            a, b, h = local(S[ring])
            A = np.stack([np.ones_like(a), a, b, a * a, a * b, b * b], 1)
            k = np.linalg.lstsq(A, h, rcond=None)[0]
            a, b, _ = local(S[inner])
            hn = np.stack([np.ones_like(a), a, b, a * a, a * b, b * b], 1) @ k
            S[inner] = c + a[:, None] * u + b[:, None] * v + hn[:, None] * n
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
    for gname, mask, off, thick, rgba in (("TankTop", shirt, 0.0035, 0.0012, SHIRT_RGBA), ("Shorts", shorts, 0.008, 0.003, SHORTS_RGBA)):
        fs = [f for f in faces if sum(mask[v] for v in f) * 2 >= len(f)]  # half or more inside: no gaps at hems
        # keep only the main piece (drop stray scraps, e.g. bits of torso skin under the arm)
        par = {}
        def root(x):
            while par.setdefault(x, x) != x:
                par[x] = par[par[x]]
                x = par[x]
            return x
        for f in fs:
            for v in f[1:]:
                a, b = root(f[0]), root(v)
                if a != b:
                    par[a] = b
        sizes = {}
        for f in fs:
            r0 = root(f[0]); sizes[r0] = sizes.get(r0, 0) + 1
        main = max(sizes, key=sizes.get)
        fs = [f for f in fs if root(f[0]) == main]
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
            surf = S[body] + N[body] * off
            snrm = N[body]
            for _ in range(30):
                acc = np.zeros_like(V); deg = np.zeros(len(V))
                np.add.at(acc, bnd[:, 0], V[bnd[:, 1]]); np.add.at(acc, bnd[:, 1], V[bnd[:, 0]])
                np.add.at(deg, bnd[:, 0], 1); np.add.at(deg, bnd[:, 1], 1)
                m = np.where(deg > 0)[0]
                V[m] += 0.5 * (acc[m] / deg[m][:, None] - V[m])
                # keep the hem on the body: project back onto the offset surface at the nearest point
                for i in m:
                    j = np.argmin(((surf - V[i]) ** 2).sum(1))
                    V[i] -= np.dot(V[i] - surf[j], snrm[j]) * snrm[j]
        verts = [tuple(x) for x in V]
        gm = bpy.data.meshes.new(obj.name + "_" + gname)
        gm.from_pydata(verts, [], [[remap[v] for v in f] for f in fs])
        gm.update()
        for p in gm.polygons:
            p.use_smooth = True
        go = bpy.data.objects.new(obj.name + "_" + gname, gm)
        go["nc_base_layer"] = True
        if gname == "TankTop":
            _rib_uvs(gm, V, cx, J["neck"][1])
            go.data.materials.append(_rib_material("NC_BaseLayer_" + gname, rgba))
        else:
            go.data.materials.append(_material("NC_BaseLayer_" + gname, rgba))
        sol = go.modifiers.new("Thickness", "SOLIDIFY")
        sol.thickness = thick
        sol.offset = 1.0
        for c in obj.users_collection:
            c.objects.link(go)
        go.parent = obj
        go.matrix_parent_inverse = obj.matrix_world.inverted()
        go.matrix_world = obj.matrix_world.copy()
        made.append(go)
    obj["nc_base_layer"] = "tanktop+shorts"
    return made
