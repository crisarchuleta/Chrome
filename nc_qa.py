# nc_qa: placement checks for the Neon Coast test street (run from build_street.py with NC_QA=1, or NC_QA=only to
# skip the renders). Uses the real meshes (with the ground's pool holes applied), not boxes:
#   floating  - a placed prop whose bottom is above whatever is under it (sampled at its centre and 4 corners)
#   sunk      - a prop buried in what it stands on (deeper than a quarter stud; palms and posts are set in the ground
#               at 0 so they show up only if something they stand on is higher)
#   uneven    - half on one surface, half on another (e.g. a bin hanging off a curb)
#   clips     - two placed things whose surfaces pass through each other (props, houses, pools, the floaty)
#   house     - inside each house style: details (lights, meters, shutters, downspouts, AC, beds) crossing a window,
#               door or garage door, and windows / doors / shutters pushing through a roof
# Writes a JSON report and prints a summary.
import bpy, json, math
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree

DETAIL = {"Metal", "Gutter", "Shutter", "Lamp", "Mulch", "Edging", "Screen", "Foundation", "Pavers", "Deck",
          "Lattice", "Awning", "Accent", "Patio"}             # (Stone / Brick are wall skins: they meet the glass edges)
SOFT = {"Water", "Mulch"}                        # things may sit in water or be planted in mulch
# a lantern's / meter's own glass and the metal frames of the Modern glass walls are built into each other on purpose
INTENDED = {("Metal", "Glass")}
OPENING = {"Glass", "Sash", "Door", "DoorGlass", "GarageDoor", "GarageGlass", "DoorKnob"}
ROOFS = {"Roof", "MetalRoof"}
THROUGH_ROOF = {"Glass", "Sash", "Door", "DoorGlass", "Shutter"}


def kind_of(name):
    base = name.split(".")[0]
    k = base.split("_", 1)[1] if "_" in base else base
    return k.rstrip("0123456789")


def world_mesh(ob, dz=0.0):
    dg = bpy.context.evaluated_depsgraph_get()
    eo = ob.evaluated_get(dg)
    me = eo.to_mesh()
    mw = ob.matrix_world
    verts = [mw @ v.co + Vector((0, 0, dz)) for v in me.vertices]
    polys = [tuple(p.vertices) for p in me.polygons]
    eo.to_mesh_clear()
    return verts, polys


def bounds(verts):
    xs, ys, zs = [v.x for v in verts], [v.y for v in verts], [v.z for v in verts]
    return Vector((min(xs), min(ys), min(zs))), Vector((max(xs), max(ys), max(zs)))


def overlap_box(a0, a1, b0, b1, pad=0.0):
    return all(a0[i] <= b1[i] + pad and b0[i] <= a1[i] + pad for i in range(3))


def r3(v):
    return [round(v[0], 2), round(v[1], 2), round(v[2], 2)]


def enclosure_check(report, info, yards, street_y, cell=0.5, gap=1.5):
    """Is every backyard really fenced in? Rasterises everything at walking height (houses' walls and foundations,
    fences, gates shut) onto a grid, closes gaps a person can't fit through (< gap studs), then floods from a point
    in each backyard. Reaching the street side (|y| < street_y) means there's a way out.
    yards: [(label, (x, y))]"""
    from collections import deque
    blockers = [d for d in info.values() if d["kind"] == "house" or d["inst"].split("#")[0] in ("FencePanel", "FencePost", "FenceGate")]
    for side in (1, -1):
        mine = [(lab, p) for (lab, p) in yards if (p[1] > 0) == (side > 0)]
        if not mine:
            continue
        x0, x1 = -10.0, 700.0
        y0, y1 = street_y, max(abs(p[1]) for _, p in mine) + 40.0
        nx, ny = int((x1 - x0) / cell) + 1, int((y1 - y0) / cell) + 1
        grid = bytearray(nx * ny)
        r = int(math.ceil((gap / 2) / cell))
        for d in blockers:
            if d["mx"].z < 0.5 or d["mn"].z > 3.0 or d["mx"].y * side < y0 - 5 or d["mn"].y * side > y1 + 5 and d["mx"].y * side > y1 + 5:
                pass
            for poly in d["p"]:
                vs = [d["v"][k] for k in poly]
                zlo, zhi = min(v.z for v in vs), max(v.z for v in vs)
                if zhi < 0.5 or zlo > 3.0:
                    continue
                ys_ = [v.y * side for v in vs]
                xs_ = [v.x for v in vs]
                i0, i1 = int((min(xs_) - x0) / cell) - r, int((max(xs_) - x0) / cell) + r
                j0, j1 = int((min(ys_) - y0) / cell) - r, int((max(ys_) - y0) / cell) + r
                if i1 < 0 or j1 < 0 or i0 >= nx or j0 >= ny:
                    continue
                for j in range(max(0, j0), min(ny - 1, j1) + 1):
                    row = j * nx
                    for i in range(max(0, i0), min(nx - 1, i1) + 1):
                        grid[row + i] = 1
        for lab, p in mine:
            si, sj = int((p[0] - x0) / cell), int((abs(p[1]) - y0) / cell)
            if grid[sj * nx + si]:
                report["yards"].append({"yard": lab, "problem": "start point is inside something"})
                continue
            seen = bytearray(nx * ny)
            q = deque([(si, sj)])
            seen[sj * nx + si] = 1
            leak = None
            while q:
                i, j = q.popleft()
                if j == 0:
                    leak = (x0 + i * cell, side * (y0 + j * cell))
                    break
                for (a, b) in ((i + 1, j), (i - 1, j), (i, j + 1), (i, j - 1)):
                    if 0 <= a < nx and 0 <= b < ny:
                        k = b * nx + a
                        if not grid[k] and not seen[k]:
                            seen[k] = 1
                            q.append((a, b))
            if leak:
                # walk back is costly; report where the flood got out instead
                report["yards"].append({"yard": lab, "problem": "open to the street", "reached": r3((leak[0], leak[1], 0))})


def run(out_path, yards=None, street_y=30.0):
    objs = [o for o in bpy.context.scene.objects if o.type == "MESH" and o.get("qa") and not o.hide_get()]
    info = {}
    for o in objs:
        v, p = world_mesh(o)
        if not v or not p:
            continue
        mn, mx = bounds(v)
        info[o.name] = {"ob": o, "kind": o["qa"], "inst": o["inst"], "v": v, "p": p, "mn": mn, "mx": mx,
                        "bvh": BVHTree.FromPolygons(v, p), "mesh": kind_of(o.name)}
    insts = {}
    for name, d in info.items():
        g = insts.setdefault(d["inst"], {"kind": d["kind"], "objs": [], "mn": Vector(d["mn"]), "mx": Vector(d["mx"])})
        g["objs"].append(name)
        g["mn"] = Vector((min(g["mn"].x, d["mn"].x), min(g["mn"].y, d["mn"].y), min(g["mn"].z, d["mn"].z)))
        g["mx"] = Vector((max(g["mx"].x, d["mx"].x), max(g["mx"].y, d["mx"].y), max(g["mx"].z, d["mx"].z)))
    supports = [n for n, d in info.items() if d["kind"] in ("surface", "house", "pool", "court") and d["mesh"] != "Water"]
    report = {"floating": [], "sunk": [], "uneven": [], "clips": [], "house": [], "yards": []}

    # ---------------------------------------------------------------- floating / sunk / uneven
    def support_z(x, y, top):
        best = None
        o = Vector((x, y, top + 1.5))
        for n in supports:
            d = info[n]
            if not (d["mn"].x - 0.01 <= x <= d["mx"].x + 0.01 and d["mn"].y - 0.01 <= y <= d["mx"].y + 0.01):
                continue
            if d["mn"].z > top + 1.5:
                continue
            hit = d["bvh"].ray_cast(o, Vector((0, 0, -1)), 8.0)
            if hit[0] is not None and (best is None or hit[0].z > best[0]):
                best = (hit[0].z, n)
        return best

    FLUSH = {"StormDrain"}                       # curb inlets are built into the curb on purpose
    for tag, g in insts.items():
        if g["kind"] not in ("prop",) or tag.split("#")[0] in FLUSH:
            continue
        mn, mx = g["mn"], g["mx"]
        cx, cy = (mn.x + mx.x) / 2, (mn.y + mx.y) / 2
        w, dpt = mx.x - mn.x, mx.y - mn.y
        # sample the base, not the canopy: use the lowest 0.4 studs of the prop's own vertices
        base_v = [v for n in g["objs"] for v in info[n]["v"] if v.z < mn.z + 0.4]
        bmn, bmx = bounds(base_v)
        bcx, bcy = (bmn.x + bmx.x) / 2, (bmn.y + bmx.y) / 2
        bw, bd = bmx.x - bmn.x, bmx.y - bmn.y
        pts = [(bcx, bcy)]
        if bw > 1.0 or bd > 1.0:
            pts += [(bcx + sx * bw * 0.35, bcy + sy * bd * 0.35) for sx in (-1, 1) for sy in (-1, 1)]
        hits = [support_z(px, py, mn.z) for (px, py) in pts]
        zs = [h[0] for h in hits if h]
        if not zs:
            report["floating"].append({"inst": tag, "at": r3((bcx, bcy, mn.z)), "gap": None, "note": "nothing under it"})
            continue
        gaps = [mn.z - z for z in zs]
        under = hits[0][1] if hits[0] else None
        if gaps[0] > 0.08 or sum(1 for gp in gaps if gp > 0.08) >= 3:
            report["floating"].append({"inst": tag, "at": r3((bcx, bcy, mn.z)), "gap": round(max(gaps), 2), "on": under})
        elif min(gaps) < -0.25:
            report["sunk"].append({"inst": tag, "at": r3((bcx, bcy, mn.z)), "depth": round(-min(gaps), 2), "on": under})
        if len(zs) >= 3 and max(zs) - min(zs) > 0.15:
            report["uneven"].append({"inst": tag, "at": r3((bcx, bcy, mn.z)), "spread": round(max(zs) - min(zs), 2),
                                     "on": sorted({h[1] for h in hits if h})})

    # ---------------------------------------------------------------- clipping between placed things
    lifted = {}

    def lifted_bvh(n):
        # raised 0.03 and shrunk 0.5% about its own base so things that merely touch (standing on a deck, a fence
        # rail meeting the next post) don't count; anything really passing through still does
        if n not in lifted:
            d = info[n]
            g = insts[d["inst"]]
            c = Vector(((g["mn"].x + g["mx"].x) / 2, (g["mn"].y + g["mx"].y) / 2, g["mn"].z))
            lifted[n] = BVHTree.FromPolygons([c + (v - c) * 0.995 + Vector((0, 0, 0.03)) for v in d["v"]], d["p"])
        return lifted[n]

    tags = [t for t, g in insts.items() if g["kind"] in ("prop", "pool", "floaty", "house", "court")]
    done = set()
    for a in tags:
        ga = insts[a]
        if ga["kind"] == "house":
            continue
        for b in tags:
            if a == b or (b, a) in done:
                continue
            gb = insts[b]
            if not overlap_box(ga["mn"], ga["mx"], gb["mn"], gb["mx"]):
                continue
            done.add((a, b))
            hits = 0
            where = None
            for na in ga["objs"]:
                if info[na]["mesh"] in SOFT:
                    continue
                for nb in gb["objs"]:
                    if info[nb]["mesh"] in SOFT or not overlap_box(info[na]["mn"], info[na]["mx"], info[nb]["mn"], info[nb]["mx"]):
                        continue
                    pairs = lifted_bvh(na).overlap(info[nb]["bvh"])
                    if pairs:
                        hits += len(pairs)
                        if where is None:
                            fi = pairs[0][0]
                            vs = [info[na]["v"][k] for k in info[na]["p"][fi]]
                            where = (sum((v for v in vs), Vector()) / len(vs), info[na]["mesh"], info[nb]["mesh"])
            if hits:
                report["clips"].append({"a": a, "b": b, "tris": hits, "at": r3(where[0]), "meshes": [where[1], where[2]]})

    # ---------------------------------------------------------------- inside each house style
    seen = set()
    for tag, g in insts.items():
        if g["kind"] != "house":
            continue
        style = tag.split("#")[0]
        if style in seen:
            continue
        seen.add(style)
        ob0 = info[g["objs"][0]]["ob"]
        loc = ob0.matrix_world.translation.copy()
        rot = ob0.matrix_world.to_euler("XYZ").z
        inv = Matrix.Rotation(-rot, 3, "Z")
        by = {}
        for n in g["objs"]:
            by.setdefault(info[n]["mesh"], []).append(n)
        def test(set_a, set_b, label):
            for ka in set_a:
                for kb in set_b:
                    if ka == kb or (ka, kb) in INTENDED:
                        continue
                    for na in by.get(ka, []):
                        for nb in by.get(kb, []):
                            if not overlap_box(info[na]["mn"], info[na]["mx"], info[nb]["mn"], info[nb]["mx"]):
                                continue
                            pairs = info[na]["bvh"].overlap(info[nb]["bvh"])
                            if pairs:
                                pts = []
                                for fi, _ in pairs[:200]:
                                    vs = [info[na]["v"][k] for k in info[na]["p"][fi]]
                                    c = sum((v for v in vs), Vector()) / len(vs)
                                    pts.append(inv @ (c - loc))
                                # cluster the overlap points so each spot is listed once
                                spots = []
                                for p in pts:
                                    for s in spots:
                                        if (s[0] - p).length < 2.5:
                                            s[1] += 1
                                            break
                                    else:
                                        spots.append([p, 1])
                                for p, cnt in spots:
                                    report["house"].append({"style": style, "check": label, "meshes": [ka, kb],
                                                            "local": r3(p), "tris": cnt})
        test(DETAIL, OPENING, "detail over an opening")
        test(THROUGH_ROOF, ROOFS, "through the roof")
        test({"Gutter"}, {"Shutter", "Glass", "Sash", "Roof", "MetalRoof", "Lattice"}, "downspout / gutter through something")
        # loose pieces: every separate piece of the house must touch something that (eventually) reaches the ground
        isl = []                                   # (mn, mx, mesh)
        for n in g["objs"]:
            d = info[n]
            parent = list(range(len(d["v"])))
            def find(a):
                while parent[a] != a:
                    parent[a] = parent[parent[a]]
                    a = parent[a]
                return a
            for poly in d["p"]:
                r0 = find(poly[0])
                for k in poly[1:]:
                    rk = find(k)
                    if rk != r0:
                        parent[rk] = r0
            groups = {}
            for vi, v in enumerate(d["v"]):
                groups.setdefault(find(vi), []).append(v)
            for vs in groups.values():
                a, b = bounds(vs)
                isl.append((a, b, d["mesh"]))
        order_ = sorted(range(len(isl)), key=lambda i: isl[i][0].x)
        up = list(range(len(isl)))
        def f2(a):
            while up[a] != a:
                up[a] = up[up[a]]
                a = up[a]
            return a
        pad = 0.07                                 # door leaves keep a 0.06 swing clearance on purpose
        for oi, i in enumerate(order_):
            a0, a1, _ = isl[i]
            for j in order_[oi + 1:]:
                b0, b1, _ = isl[j]
                if b0.x > a1.x + pad:
                    break
                if overlap_box(a0, a1, b0, b1, pad):
                    ri, rj = f2(i), f2(j)
                    if ri != rj:
                        up[rj] = ri
        base_z = g["mn"].z                         # the building may stand on a sidewalk, not at z = 0
        # standing on the lawn counts, as does standing on the sidewalk the building sits on
        grounded = {f2(i) for i in range(len(isl)) if isl[i][0].z <= max(base_z, 0.0) + 0.05 or isl[i][0].z <= 0.05}
        comps = {}
        for i in range(len(isl)):
            r = f2(i)
            if r not in grounded:
                comps.setdefault(r, []).append(i)
        for r, members in comps.items():
            mn_ = Vector((min(isl[i][0].x for i in members), min(isl[i][0].y for i in members), min(isl[i][0].z for i in members)))
            mx_ = Vector((max(isl[i][1].x for i in members), max(isl[i][1].y for i in members), max(isl[i][1].z for i in members)))
            c = inv @ ((mn_ + mx_) / 2 - loc)
            report["house"].append({"style": style, "check": "loose piece (touches nothing)", "meshes": sorted({isl[i][2] for i in members}),
                                    "local": r3(c), "tris": len(members)})

    if yards:
        enclosure_check(report, info, yards, street_y)
    with open(out_path, "w") as f:
        json.dump(report, f, indent=1)
    print("NC_QA", json.dumps({k: len(v) for k, v in report.items()}))
    for k in ("floating", "sunk", "uneven", "clips", "house", "yards"):
        for e in report[k][:60]:
            print("NC_QA", k, json.dumps(e))
