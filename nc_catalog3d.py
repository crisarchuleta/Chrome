"""Maps NCLookCatalog clothing items (Top / Outer / Bottom / Shoes) to the 3D garment maker, so every catalog
piece gets a fitted mesh on every body. Colours come from the item's default c1 / c2."""
import re
import numpy as np
import nc_garments as NG

LINE = re.compile(r'^\s*I\("([a-z0-9_]+)",\s*"(Top|Outer|Bottom|Shoes|Head|Mask|Face)",\s*"((?:[^"\\]|\\.)*)",\s*\d+,\s*"([a-z]+)",\s*(\{[^}]*\}|nil),\s*([^,]+),\s*"(#[0-9A-Fa-f]{6})"(?:,\s*([^,]+),\s*"(#[0-9A-Fa-f]{6})")?')


def hexc(h):
    h = h.lstrip("#")
    srgb = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return tuple(c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in srgb)


def parse_params(t):
    out = {}
    if not t or t == "nil":
        return out
    for k, v in re.findall(r'(\w+)\s*=\s*("[^"]*"|[\w.]+)', t):
        if v.startswith('"'):
            out[k] = v[1:-1]
        elif v in ("true", "false"):
            out[k] = v == "true"
        else:
            try:
                out[k] = float(v)
            except ValueError:
                out[k] = v
    return out


def load(path):
    items = []
    for line in open(path, encoding="utf-8"):
        m = LINE.match(line)
        if m:
            id_, slot, name, fam, pp, _, c1, _, c2 = m.groups()
            items.append(dict(id=id_, slot=slot, name=name, fam=fam, p=parse_params(pp), c1=hexc(c1), c2=hexc(c2) if c2 else None))
    return items


CAMO = [(0.33, 0.36, 0.22), (0.18, 0.2, 0.12), (0.5, 0.45, 0.32), (0.1, 0.1, 0.07)]


SHOE_MAP = {  # catalog id -> (SHOE_STYLES key, extra args)
    "shoe_white_low": ("court_low", {}),
    "shoe_black_low": ("court_low", {"white_sole": False}),
    "shoe_chunky": ("runner_retro", {}),
    "shoe_slim_runner": ("runner_retro", {}),
    "shoe_hightop": ("court_high", {}),
    "shoe_hightop_bw": ("court_high", {}),
    "shoe_classic": ("runner_retro", {}),
    "shoe_skate": ("skate_low", {}),
    "shoe_runner": ("runner_retro", {}),
    "shoe_platform": ("canvas_high", {}),
    "shoe_emo_platform": ("combat_platform", {"white_sole": False}),
    "shoe_emo_knee_canvas": ("canvas_knee", {}),
    "shoe_emo_canvas_low": ("canvas_low", {}),
}


def _plaid_zones(b, co, per=0.08, skirt=False):
    """(axis point, axis dir, e1, e2, band count, selector) for each tube a plaid wraps: each leg below the
    crotch, and the hips / body above it."""
    k = b.k; J = b.J; zc = b.crotch_z + 0.02 * k
    zones = []
    if skirt:
        zc = -1e9  # a skirt is one tube round the body
    def frame(d):
        d = d / np.linalg.norm(d); e1 = np.array([1.0, 0, 0]) - d[0] * d; e1 /= np.linalg.norm(e1)
        return d, e1, np.cross(d, e1)
    for sd, sg in ((() if skirt else (("l", 1), ("r", -1)))):
        # plumb axis through the hip joint and ankle midpoint: planes stay vertical, so the bands hang straight and
        # never fan into Vs over the seat the way planes through the slanted thigh axis did
        A_ = 0.5 * (np.array(J[sd + "-upper-leg"]) + np.array(J[sd + "-ankle"])); d, e1, e2 = frame(np.array([0, 0, 1.0]))
        m = (co[:, 2] < zc) & ((co[:, 0] - b.cx) * sg > 0)
        if m.sum() < 10:
            continue
        q = co[m] - A_; q = q - np.outer(q @ d, d); r = np.percentile(np.linalg.norm(q, axis=1), 80)
        N_ = max(8, 2 * int(round(np.pi * r / (per * k))))
        # each leg's bands carry on up its own half of the seat to the waist, so they meet only at the centre
        # front/back seam like sewn plaid trousers (a separate hip tube left a mismatched ring at the crotch line)
        zones.append((A_, d, e1, e2, N_, (lambda c, sg=sg: (c[0] - b.cx) * sg > 0)))
    if zones:
        return zones
    A_ = np.array([b.cx, b.yc, J["pelvis"][2]]); d, e1, e2 = frame(np.array([0, 0, 1.0]))
    m = co[:, 2] >= zc
    if m.sum() >= 10:
        q = co[m] - A_; q[:, 2] = 0; r = np.percentile(np.linalg.norm(q, axis=1), 80)
        N_ = max(8, 2 * int(round(np.pi * r / (per * k))))
        zones.append((A_, d, e1, e2, N_, (lambda c: c[2] >= zc)))
    return zones


def apply_pattern(o, n0, kind, c1, c2, arms_only=False, name=""):
    """Stripes / plaid / chest band as face materials on the garments built since o.objs[n0]. The mesh is cut
    exactly along the pattern lines (bmesh bisect), so the colour edges are straight and crisp; each colour
    becomes its own MeshPart in Roblox. Only the main fabric changes (ribs, zips, trims keep theirs).
    The uncut mesh is kept (ob["nc_precut"]) so the game export can decimate FIRST and cut the pattern on the
    low-poly mesh: decimating a cut mesh shreds the stripes into shards."""
    import json
    b = o.b
    for ob in o.objs[n0:]:
        me = ob.data
        if not me.materials or "_Main" not in me.materials[0].name:
            continue
        pre = me.copy(); pre.name = me.name + "_precut"; pre.use_fake_user = True
        ob["nc_precut"] = pre.name
        if kind == "camo" and not me.color_attributes.get("Col"):
            continue
        cj = [list(map(float, c[:3])) for c in c1] if kind == "camo" else list(map(float, c1[:3]))
        ob["nc_pattern"] = json.dumps(dict(kind=kind, c1=cj, c2=list(map(float, c2[:3])), arms_only=bool(arms_only),
                                           skirt="skirt" in ob.name.lower(),
                                           b=dict(k=float(b.k), cx=float(b.cx), yc=float(b.yc), crotch_z=float(b.crotch_z),
                                                  J={j: list(map(float, v)) for j, v in b.J.items()})))
        _pattern_mesh(b, me, kind, c1, c2, arms_only, "skirt" in ob.name.lower())


def _iso_cut(bm, field, level):
    """Split the bmesh along the iso-line field(co) == level (edge splits + face splits keep every layer)."""
    import bmesh
    bm.verts.ensure_lookup_table()
    val = {v: float(x) - level for v, x in zip(bm.verts, field(np.array([v.co[:] for v in bm.verts])))}
    on = set()
    for e in list(bm.edges):
        a, c = e.verts
        va, vc = val[a], val[c]
        if va * vc < 0:
            fac = va / (va - vc)
            ne, nv = bmesh.utils.edge_split(e, a, fac)
            val[nv] = 0.0; on.add(nv)
        elif va == 0:
            on.add(a)
        elif vc == 0:
            on.add(c)
    todo = list(bm.faces)
    while todo:
        f = todo.pop()
        if not f.is_valid:
            continue
        vs = list(f.verts); n = len(vs)
        idx = [i for i, v in enumerate(vs) if v in on]
        if len(idx) < 2:
            continue
        done = False
        for x in range(len(idx)):
            i, j = idx[x], idx[(x + 1) % len(idx)]
            if (j - i) % n in (0, 1, n - 1):
                continue
            # the vertices strictly between i and j (going forward) must sit on one side
            mid = [val.get(vs[(i + t) % n], 0.0) for t in range(1, (j - i) % n)]
            if mid and (all(m > 0 for m in mid) or all(m < 0 for m in mid)):
                try:
                    res = bmesh.utils.face_split(f, vs[i], vs[j])
                except ValueError:
                    continue
                todo += [f, res[0]]; done = True
                break
        if not done:
            continue


def _camo_mesh(me, pal):
    """Camo as crisp face materials: cut along the iso-lines of the same noise fields NG.camo() thresholds and
    give each patch one of the palette materials (vertex colours blurred into mush in the game export)."""
    import bmesh
    sc = 0.07 * float(me.get("nc_k", 1.0))
    n1 = lambda P: NG.value_noise(P, sc, 1) * 0.65 + NG.value_noise(P, sc * 0.45, 8) * 0.35
    n2 = lambda P: NG.value_noise(P, sc * 0.8, 4)
    bm = bmesh.new(); bm.from_mesh(me)
    for fld, lv in ((n1, 0.5), (n1, 0.33), (n2, 0.62)):
        _iso_cut(bm, fld, lv)
    bm.to_mesh(me); bm.free()
    if me.color_attributes.get("Col"):
        me.color_attributes.remove(me.color_attributes["Col"])
    nm_ = me.materials[0].name
    mats = [NG.material(nm_ + "_C%d" % i, tuple(pal[i][:3]) + (1,)) for i in range(len(pal))]
    me.materials[0] = mats[0]
    base = len(me.materials)
    for m in mats[1:]:
        me.materials.append(m)
    co = np.array([v.co[:] for v in me.vertices])
    # classify by the mean of the corner values: the cuts are linear along edges, so this always agrees with
    # them (the true noise at a big face's centre can disagree and leave spikes after the game decimation)
    va, vb = n1(co), n2(co)
    a = np.array([va[list(p.vertices)].mean() for p in me.polygons]); b2 = np.array([vb[list(p.vertices)].mean() for p in me.polygons])
    mi = np.array([p.material_index for p in me.polygons])
    cat = np.zeros(len(a), int)
    cat[a > 0.5] = 1; cat[b2 > 0.62] = 2
    if len(pal) > 3:
        cat[a < 0.33] = 3
    main = mi == 0
    mi[main & (cat > 0)] = base + cat[main & (cat > 0)] - 1
    me.polygons.foreach_set("material_index", mi.astype(np.int32))


def _pattern_mesh(b, me, kind, c1, c2, arms_only=False, skirt=False):
    import bmesh
    if kind == "camo":
        me["nc_k"] = float(b.k)
        return _camo_mesh(me, c1)
    k = b.k; J = b.J
    dark = tuple(c2[:3]) + (1,)
    mid = tuple(0.5 * np.array(c1[:3]) + 0.5 * np.array(c2[:3])) + (1,)
    per_s = 0.026 * k
    per_p = 0.08 * k  # ~8 cm tartan repeat (a real one is 8-15 cm; the 5 cm grid alone cost 20k+ triangles in game)
    zsh = J["l-shoulder"][2]
    if True:
        armv = None
        if arms_only and "nc_arm" in me.attributes:
            armv = np.zeros(len(me.vertices), np.int32); me.attributes["nc_arm"].data.foreach_get("value", armv)
        bm = bmesh.new(); bm.from_mesh(me)
        co = np.array([v.co for v in bm.verts])
        z0, z1 = co[:, 2].min(), co[:, 2].max()
        cuts = []
        if kind == "stripes":
            for zc in np.arange(np.floor(z0 / per_s) * per_s, z1 + per_s, per_s):
                cuts.append(((0, 0, float(zc)), (0, 0, 1.0)))
        elif kind == "band":  # solid chest band (band tees): two cuts, straight round the body
            bz = zsh - 0.13 * k
            cuts += [((0, 0, float(bz - 0.025 * k)), (0, 0, 1.0)), ((0, 0, float(bz + 0.025 * k)), (0, 0, 1.0))]
        else:
            for zc in np.arange(np.floor(z0 / per_p) * per_p, z1 + per_p, per_p):
                cuts += [((0, 0, float(zc)), (0, 0, 1.0)), ((0, 0, float(zc + 0.34 * per_p)), (0, 0, 1.0))]
        for pco, pno in cuts:
            geom = bm.verts[:] + bm.edges[:] + bm.faces[:]
            bmesh.ops.bisect_plane(bm, geom=geom, plane_co=pco, plane_no=pno, dist=1e-6)
        if kind == "plaid":
            # vertical bands run AROUND each tube (planes through the leg / body axis), so they stay even all the
            # way round instead of swelling into rings where a flat cut grazes the side of the hip or thigh
            for zone in _plaid_zones(b, co, skirt=skirt):
                A_, d_, e1, e2, N_, sel = zone
                for i_ in range(N_ // 2):
                    for off in (0.0, 0.34):
                        a_ = 2 * np.pi * (i_ + off) / N_
                        rad_ = np.cos(a_) * e1 + np.sin(a_) * e2
                        fs = [f for f in bm.faces if sel(np.array(f.calc_center_median()))]
                        if not fs:
                            continue
                        es = list({e for f in fs for e in f.edges}); vs_ = list({v for f in fs for v in f.verts})
                        bmesh.ops.bisect_plane(bm, geom=vs_ + es + fs, plane_co=tuple(A_), plane_no=tuple(np.cross(d_, rad_)), dist=1e-6)
        nv0 = len(me.vertices)
        bm.to_mesh(me); bm.free()
        if "nc_arm" in me.attributes:  # vertices the cuts added: take the sleeve flag of the edge they split
            fl = np.zeros(len(me.vertices), np.int32); me.attributes["nc_arm"].data.foreach_get("value", fl)
            Ed = np.array([e.vertices[:] for e in me.edges])
            new_ = np.arange(len(fl)) >= nv0
            for _ in range(3):
                for a_, b_ in ((0, 1), (1, 0)):
                    m_ = new_[Ed[:, a_]] & ~new_[Ed[:, b_]]
                    np.maximum.at(fl, Ed[m_, a_], fl[Ed[m_, b_]])
                # new vertices with only new neighbours (cut crossings) follow those neighbours
                m_ = new_[Ed[:, 0]] & new_[Ed[:, 1]]
                np.maximum.at(fl, Ed[m_, 0], fl[Ed[m_, 1]]); np.maximum.at(fl, Ed[m_, 1], fl[Ed[m_, 0]])
            me.attributes["nc_arm"].data.foreach_set("value", fl)
        nm_ = me.materials[0].name
        me.materials.append(NG.material(nm_ + "_P1", mid)); me.materials.append(NG.material(nm_ + "_P2", dark))
        i_mid, i_dark = len(me.materials) - 2, len(me.materials) - 1
        co = np.array([v.co for v in me.vertices])
        zones = _plaid_zones(b, co, skirt=skirt) if kind == "plaid" else []
        if kind == "band" and "nc_arm" in me.attributes:
            armv = np.zeros(len(me.vertices), np.int32); me.attributes["nc_arm"].data.foreach_get("value", armv)
        if arms_only and "nc_arm" in me.attributes:  # bmesh carries the per-vertex arm flag through the cuts
            armv = np.zeros(len(me.vertices), np.int32); me.attributes["nc_arm"].data.foreach_get("value", armv)
        for poly in me.polygons:
            if poly.material_index != 0:
                continue
            vs = list(poly.vertices)
            c = co[vs].mean(0)
            if kind == "band":
                bz = zsh - 0.13 * k
                if abs(c[2] - bz) < 0.025 * k and not (armv is not None and armv[vs].min() > 0):
                    poly.material_index = i_dark
                continue
            if kind == "stripes":
                if arms_only:
                    side_arm = armv is not None and armv[vs].min() > 0
                    if not side_arm or c[2] > zsh - 0.17 * k:
                        continue
                if int(np.floor(c[2] / per_s)) % 2:
                    poly.material_index = i_dark
            else:
                a = False
                for A_, d_, e1, e2, N_, sel in zones:
                    if sel(c):
                        q_ = c - A_; q_ = q_ - (q_ @ d_) * d_
                        a = (np.arctan2(q_ @ e2, q_ @ e1) / (2 * np.pi) * N_) % 1.0 < 0.34
                        break
                bnd = (c[2] / per_p) % 1.0 < 0.34
                if a and bnd:
                    poly.material_index = i_dark
                elif a or bnd:
                    poly.material_index = i_mid


def build_item(o, it):
    """Returns True when the item has a 3D garment."""
    f, p, c1 = it["fam"], it["p"], it["c1"]
    c2 = it["c2"] or c1
    nm = it["id"]
    camo = CAMO if p.get("camo") else None
    n0 = len(o.objs)
    ok = _build_item(o, it, f, p, c1, c2, nm, camo)
    if ok and camo:
        apply_pattern(o, n0, "camo", camo, c2)
    if ok and p.get("stripes") and f == "tee":
        apply_pattern(o, n0, "stripes", c1, c2, arms_only=bool(p.get("layered")))
    if ok and p.get("plaid"):
        apply_pattern(o, n0, "plaid", c1, c2)
    if ok and f == "tee" and (p.get("stripe") or p.get("text")) and not p.get("stripes"):
        apply_pattern(o, n0, "band", c1, c2)
    return ok


def _build_item(o, it, f, p, c1, c2, nm, camo):
    if f == "tee":
        sl = {"tank": "none", "long": "long"}.get(p.get("sleeve"), "short")
        if p.get("layered"):
            sl = "long"
        NG.build_top(o, nm, kind="tee", sleeve=sl, color=c1, accent=c2, hood=False, pocket=False, rib=sl == "long",
                     ease=0.06, sleeve_ease=0.28 if sl == "short" else 0.12, thick=0.003,
                     band=None,
                     neck_drop=0.05 if sl == "none" else 0)
    elif f == "hoodie":
        NG.build_top(o, nm, color=(1, 1, 1) if camo else c1, accent=c2 if not camo else (0.2, 0.22, 0.14), camo_pal=camo,
                     zip_front=bool(p.get("zip")), pocket=not p.get("zip"), band=c2 if p.get("text") or p.get("puff") else None)
    elif f == "sweater":
        coll = "turtle" if p.get("turtle") else ("stand" if p.get("qzip") else "rib")
        NG.build_top(o, nm, kind="sweater", color=c1, accent=c1, hood=False, pocket=False, collar=coll,
                     neck_drop=0.07 if p.get("vneck") else 0, ease=0.07 if not p.get("chunky") else 0.1, length=-0.02,
                     zip_front=bool(p.get("qzip")))
    elif f in ("shirt", "polo"):
        sl = "short" if (p.get("sleeve") == "tee" or f == "polo") else "long"
        NG.build_top(o, nm, kind="tee", sleeve=sl, color=c1, accent=c2, hood=False, pocket=False, rib=False,
                     collar="shirt", ease=0.05, sleeve_ease=0.1 if sl == "long" else 0.2, thick=0.003, front_open=bool(p.get("open")) and it["slot"] == "Outer",
                     zip_front=not (p.get("open") and it["slot"] == "Outer"), length=-0.01,
                     neck_drop=0.03 if p.get("open") else 0)  # Top-slot shirts stay closed so the tank never shows
    elif f == "jersey":
        sl = {"tee": "short", "long": "long"}.get(p.get("sleeve"), "none")
        NG.build_top(o, nm, kind="tee", sleeve=sl, color=c1, accent=c2, hood=False, pocket=False, rib=True,
                     ease=0.12, sleeve_ease=0.3, thick=0.003, neck_drop=0.04, band=c2, length=0.02)
    elif f == "croptop":
        NG.build_top(o, nm, kind="tee", sleeve="short", color=c1, accent=c2, hood=False, pocket=False, rib=False,
                     ease=0.0, sleeve_ease=0.08, thick=0.003, length=-0.17)
    elif f in ("jumpsuit",):
        NG.build_pants(o, nm + "_Legs", fit="straight", color=c1, accent=c1, stack=False)
        NG.build_top(o, nm, kind="tee", sleeve="short" if p.get("shortSleeve") else "long", color=c1, accent=c2, hood=False,
                     pocket=False, rib=False, collar="shirt", zip_front=True, ease=0.05, length=-0.04)
    elif f in ("robe", "labcoat"):
        L = p.get("len", 1.4) if f == "robe" else 1.3
        NG.build_top(o, nm, kind="coat", color=c1, accent=c2, hood=bool(p.get("hood")), pocket=False, rib=False,
                     collar="lapel" if f == "labcoat" else "rib", length=0.25 * L, front_open=(f == "labcoat"), flare=0.08)
    elif f == "dress":
        NG.build_skirt(o, nm + "_Skirt", length=min(0.75, 0.2 + 0.3 * p.get("len", 1.2)), flare=0.18, color=c1)
        NG.build_top(o, nm, kind="tee", sleeve="short" if p.get("sleeve") else "none", color=c1, accent=c1, hood=False,
                     pocket=False, rib=False, ease=0.0, sleeve_ease=0.05, length=-0.08, collar="none", neck_drop=0.04)
    elif f == "jacket":
        coll = {"stand": "stand", "lapel": "lapel", "rib": "rib", "hood": "rib", "funnel": "turtle", "fur": "lapel"}.get(p.get("collar"), "rib")
        is_open = p.get("open", True) if p.get("collar") == "lapel" else False
        L = p.get("long")
        NG.build_top(o, nm, kind="jacket", sleeve="none" if p.get("vest") else "long", color=(1, 1, 1) if camo else c1, accent=c2,
                     camo_pal=camo, hood=p.get("collar") == "hood", pocket=False, rib=bool(p.get("cuffs")) or p.get("collar") == "rib",
                     puffer=bool(p.get("puffer")), collar=coll, zip_front=bool(p.get("zip")) and not is_open,
                     front_open=is_open, ease=0.1, sleeve_ease=0.16, length=(0.3 * (L - 1) + 0.12) if L else -0.02,
                     flare=0.03 if L else 0.012, band=c2 if p.get("stripes") else None, thick=0.005)
    elif f == "blazer":
        NG.build_top(o, nm, kind="jacket", color=c1, accent=c2, hood=False, pocket=False, rib=False, collar="lapel",
                     front_open=True, ease=0.05, sleeve_ease=0.08, length=0.02, thick=0.005)
    elif f == "vest":
        NG.build_top(o, nm, kind="jacket", sleeve="none", color=c1, accent=c2, hood=False, pocket=False, rib=False,
                     collar="none", neck_drop=0.08 if p.get("suit") else 0.02, ease=0.03 if p.get("suit") else 0.1, length=-0.05, thick=0.006)
    elif f == "pants":
        fit = "cargo" if p.get("cargo") else "sweat" if p.get("cuff") else "baggy" if (p.get("stack") or p.get("wide")) else "straight"
        if "Slim" in it["name"] or "Fitted" in it["name"] or p.get("skinny"):
            fit = "slim"
        NG.build_pants(o, nm, fit=fit, color=c1, accent=c2 if p.get("stripe") else c1, stack=bool(p.get("stack")),
                       cuffed=bool(p.get("cuff")), cargo=bool(p.get("cargo")))
    elif f == "shorts":
        NG.build_pants(o, nm, fit="baggy", color=c1, accent=c1, stack=False, shorts=True)
    elif f == "leggings":
        NG.build_pants(o, nm, fit="slim", color=c1, accent=c1, stack=False)
    elif f == "overalls":
        NG.build_pants(o, nm, fit="straight", color=c1, accent=c1, stack=False)
    elif f == "skirt":
        if p.get("tights"):  # opaque leggings under the skirt (built first so the skirt sits over them)
            n1 = len(o.objs)
            NG.build_pants(o, nm + "_Leggings", fit="slim", color=c2, accent=c2, stack=False)
            for ob in o.objs[n1:]:
                if ob.data.materials:
                    ob.data.materials[0].name = ob.data.materials[0].name.replace("_Main", "_Tights")
        NG.build_skirt(o, nm, length=min(0.92, 0.18 + 0.25 * p.get("len", 1.0)), flare=0.22 if p.get("flare") != 0 else 0.03,
                       color=c1, pleats=14 if ("Pleat" in it["name"] or p.get("pleats")) else 0)
    elif f == "shoes" and it["id"] in SHOE_MAP:
        # sneakers use the reference-matched shoe maker (build_shoe), fitted to each body's own foot
        st, kw = SHOE_MAP[it["id"]]
        NG.build_shoe(o, nm, style=st, color=c1, accent=c2 if c2 != c1 else None,
                      sole=hexc("#F5F5F2") if kw.get("white_sole", True) else c1, **{k: v for k, v in kw.items() if k != "white_sole"})
        sh_ = NG.SHOE_STYLES[st].get("shaft")
        if sh_:  # boots / knee-highs: a laced shaft that hugs the leg
            canvas = NG.SHOE_STYLES[st]["kind"] == "vulc"
            NG.build_boot_shaft(o, nm + "_Shaft", height=sh_, color=c1, lace=c1 if not canvas else hexc("#F5F5F2"),
                                trim=hexc("#F5F5F2") if canvas else c1, canvas=canvas,
                                sole=NG.SHOE_STYLES[st]["sole"] * (1.0 if canvas else 1.1))
    elif f == "shoes":
        nmn = it["name"].lower()
        high = any(w in nmn for w in ("high", "boot", "timb", "combat"))
        NG.build_sneakers(o, nm, high=high, color=c1, sole=(0.92, 0.92, 0.9) if "boot" not in nmn else (0.12, 0.1, 0.08),
                          accent=c2, chunky=1.3 if "chunky" in nmn or "platform" in nmn else 1.0)
    else:
        import nc_headwear as HW  # helmets, durags, ski masks, great helm, goggles
        return HW.build_item(o, it, hexc)
    return True


def build_items(o, ids, path="/home/user/Chrome/NCLookCatalog.lua"):
    items = {it["id"]: it for it in load(path)}
    # inner layers first, like the looks: a later piece is pushed out over the earlier ones (pants built after a tee
    # would be pushed out through it at the back waist)
    order = {"Shoes": 0, "Bottom": 1, "Top": 2, "Outer": 3}
    for i in sorted(ids, key=lambda i: order.get(items[i]["slot"], 4)):
        build_item(o, items[i])


def _repattern(ob, target_tris):
    """Game export of a patterned garment: decimate the uncut mesh to the budget, cut the pattern again on the
    low-poly mesh (crisp straight colour edges, few extra triangles) and copy the bone weights over."""
    import bpy, json, types
    from scipy.spatial import cKDTree
    spec = json.loads(ob["nc_pattern"]); pre = bpy.data.meshes.get(ob["nc_precut"])
    if pre is None:
        return False
    bb = spec["b"]; b = types.SimpleNamespace(k=bb["k"], cx=bb["cx"], yc=bb["yc"], crotch_z=bb["crotch_z"],
                                               J={j: np.array(v) for j, v in bb["J"].items()})
    tmp = bpy.data.objects.new("_nc_dec_tmp", pre.copy())
    bpy.context.scene.collection.objects.link(tmp)
    tris = sum(len(p.vertices) - 2 for p in tmp.data.polygons)
    if tris > target_tris:
        d = tmp.modifiers.new("Dec", "DECIMATE"); d.ratio = target_tris / tris
        # keep the narrow trims (zip strip, rib edges) whole: their borders may not collapse
        vm = {}
        for p in tmp.data.polygons:
            for v in p.vertices:
                vm.setdefault(v, set()).add(p.material_index)
        border = [v for v, ms in vm.items() if len(ms) > 1]
        if border:
            vg = tmp.vertex_groups.new(name="NC_MatBorder"); vg.add(border, 1.0, "REPLACE")
            d.vertex_group = vg.name; d.invert_vertex_group = True; d.vertex_group_factor = 1000.0
    low = bpy.data.meshes.new_from_object(tmp.evaluated_get(bpy.context.evaluated_depsgraph_get()))
    old_me = tmp.data; bpy.data.objects.remove(tmp, do_unlink=True); bpy.data.meshes.remove(old_me)
    mi_keep = np.zeros(len(low.polygons), np.int32); low.polygons.foreach_get("material_index", mi_keep)
    if [m.name for m in low.materials] != [m.name for m in pre.materials]:
        low.materials.clear()  # (this resets every face to slot 0, so the indices are put back below)
        for m in pre.materials:
            low.materials.append(m)
        low.polygons.foreach_set("material_index", mi_keep)
    if spec["kind"] == "camo":
        # curved camo edges are cut linearly along each edge: split the long slivers the decimation leaves on flat
        # areas first, or the patches come out as spikes
        import bmesh
        bm = bmesh.new(); bm.from_mesh(low)
        for _ in range(3):
            long_ = [e for e in bm.edges if e.calc_length() > 0.05 * b.k]
            if not long_:
                break
            bmesh.ops.subdivide_edges(bm, edges=long_, cuts=1, use_grid_fill=True)
            bmesh.ops.triangulate(bm, faces=[f for f in bm.faces if len(f.verts) > 4])
        bm.to_mesh(low); bm.free()
    _pattern_mesh(b, low, spec["kind"], spec["c1"], spec["c2"], spec["arms_only"], spec["skirt"])
    # bone weights from the nearest vertex of the full-res skinned mesh
    hi = ob.data
    H = np.array([v.co[:] for v in hi.vertices]); L = np.array([v.co[:] for v in low.vertices])
    _, nn = cKDTree(H).query(L)
    groups = [[(g.group, g.weight) for g in hi.vertices[int(j)].groups] for j in nn]
    names = [g.name for g in ob.vertex_groups]
    ob.data = low  # vertex group names live on the mesh: make them again on the new one
    vgs = [ob.vertex_groups.get(n) or ob.vertex_groups.new(name=n) for n in names]
    for vi, gs in enumerate(groups):
        for gi, wt in gs:
            vgs[gi].add([vi], wt, "REPLACE")
    for p in low.polygons:
        p.use_smooth = True
    return True


NG.PATTERN_HOOK = _repattern
