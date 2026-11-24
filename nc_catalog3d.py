"""Maps NCLookCatalog clothing items (Top / Outer / Bottom / Shoes) to the 3D garment maker, so every catalog
piece gets a fitted mesh on every body. Colours come from the item's default c1 / c2."""
import re
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


def apply_pattern(o, n0, kind, c1, c2, arms_only=False, name=""):
    """Stripes / plaid as face materials on the garments built since o.objs[n0]. The mesh is first cut exactly
    along the pattern lines (bmesh bisect), so the colour edges are straight and crisp and survive the game
    decimation; each colour becomes its own MeshPart in Roblox. Only the main fabric changes (ribs, zips, trims
    keep theirs)."""
    import numpy as np
    import bmesh
    b = o.b; k = b.k; J = b.J
    dark = tuple(c2[:3]) + (1,)
    mid = tuple(0.5 * np.array(c1[:3]) + 0.5 * np.array(c2[:3])) + (1,)
    per_s = 0.026 * k
    per_p = 0.05 * k
    zsh = J["l-shoulder"][2]
    for ob in o.objs[n0:]:
        me = ob.data
        if not me.materials or "_Main" not in me.materials[0].name:
            continue
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
        else:
            for zc in np.arange(np.floor(z0 / per_p) * per_p, z1 + per_p, per_p):
                cuts += [((0, 0, float(zc)), (0, 0, 1.0)), ((0, 0, float(zc + 0.34 * per_p)), (0, 0, 1.0))]
            for cx_ in ([J["l-knee"][0], J["r-knee"][0]] if co[:, 2].min() < b.crotch_z else [b.cx]):
                xs0 = np.arange(cx_ - 0.4 * k, cx_ + 0.4 * k, per_p)
                for xc in xs0:  # vertical bands: planes facing the front (they run down the front and back)
                    cuts += [((float(xc), 0, 0), (1.0, 0, 0)), ((float(xc + 0.34 * per_p), 0, 0), (1.0, 0, 0))]
        for pco, pno in cuts:
            geom = bm.verts[:] + bm.edges[:] + bm.faces[:]
            bmesh.ops.bisect_plane(bm, geom=geom, plane_co=pco, plane_no=pno, dist=1e-6)
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
        if arms_only and "nc_arm" in me.attributes:  # bmesh carries the per-vertex arm flag through the cuts
            armv = np.zeros(len(me.vertices), np.int32); me.attributes["nc_arm"].data.foreach_get("value", armv)
        for poly in me.polygons:
            if poly.material_index != 0:
                continue
            vs = list(poly.vertices)
            c = co[vs].mean(0)
            if kind == "stripes":
                if arms_only:
                    side_arm = armv is not None and armv[vs].min() > 0
                    if not side_arm or c[2] > zsh - 0.17 * k:
                        continue
                if int(np.floor(c[2] / per_s)) % 2:
                    poly.material_index = i_dark
            else:
                if c[2] < b.crotch_z + 0.02 * k:
                    cxl = J["l-knee"][0] if c[0] > b.cx else J["r-knee"][0]
                else:
                    cxl = b.cx
                a = ((c[0] - cxl) / per_p) % 1.0 < 0.34
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
    if ok and p.get("stripes") and f == "tee":
        apply_pattern(o, n0, "stripes", c1, c2, arms_only=bool(p.get("layered")))
    if ok and p.get("plaid"):
        apply_pattern(o, n0, "plaid", c1, c2)
    return ok


def _build_item(o, it, f, p, c1, c2, nm, camo):
    if f == "tee":
        sl = {"tank": "none", "long": "long"}.get(p.get("sleeve"), "short")
        if p.get("layered"):
            sl = "long"
        NG.build_top(o, nm, kind="tee", sleeve=sl, color=c1, accent=c2, hood=False, pocket=False, rib=sl == "long",
                     ease=0.06, sleeve_ease=0.28 if sl == "short" else 0.12, thick=0.003,
                     band=c2 if ((p.get("stripe") or p.get("text")) and not p.get("stripes")) else None,
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
    for i in ids:
        build_item(o, items[i])
