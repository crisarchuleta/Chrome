# boundary-loop audit: every open edge loop of every garment piece, with size and nearest joint
import bpy, sys, numpy as np, collections
sys.path.insert(0, "/tmp/claude-0/base"); sys.path.insert(0, "/tmp/claude-0/garm")
import nc_garments as NG, catalog_map as CM
from scipy.spatial import cKDTree
bpy.ops.wm.open_mainfile(filepath="/tmp/claude-0/garm/rig_tank.blend")
name, ids = sys.argv[-2], sys.argv[-1].split(",")
w = bpy.data.objects[name + "_Whole"]; a = bpy.data.objects["NC_" + name]
b = NG.RigBody(w, a); k = b.k
OK = ("neck", "hand", "wrist", "elbow", "pelvis", "hip", "ankle", "knee", "foot", "toe", "head")
jn = list(b.J.keys()); JP = np.array([b.J[x] for x in jn])
for i in ids:
    o = NG.Outfit(b); CM.build_items(o, [i])
    for ob in o.objs:
        me = ob.data; V = np.array([v.co[:] for v in me.vertices])
        V = (np.array(ob.matrix_world) @ np.c_[V, np.ones(len(V))].T).T[:, :3]
        V = (np.array(w.matrix_world.inverted()) @ np.c_[V, np.ones(len(V))].T).T[:, :3]
        ec = collections.Counter()
        for p in me.polygons:
            vs = list(p.vertices)
            for x, y in zip(vs, vs[1:] + vs[:1]): ec[(min(x, y), max(x, y))] += 1
        adj = collections.defaultdict(list)
        for (x, y), c in ec.items():
            if c == 1: adj[x].append(y); adj[y].append(x)
        seen = set(); loops = []
        for s in adj:
            if s in seen: continue
            comp = []; st = [s]
            while st:
                u = st.pop()
                if u in seen: continue
                seen.add(u); comp.append(u); st += adj[u]
            loops.append(comp)
        if i.startswith("top_") and loops and "Hood" not in ob.name and len(loops) >= 2 and not any(t in ob.name for t in ("_Legs", "_Skirt")):
            # neckline: loop with the highest mean z; how far it opens out from the neck and how low it drops
            nl = max(loops, key=lambda l: V[l, 2].mean())
            nz = b.J["neck"][2]
            hm = (b.reg == "Head") & (b.co[:, 2] > nz) & (b.co[:, 2] < nz + 0.03 * k)
            yn = b.co[hm, 1].mean(); Rn = np.median(np.hypot(b.co[hm, 0] - b.cx, b.co[hm, 1] - yn))
            dn = np.hypot(V[nl, 0] - b.cx, V[nl, 1] - yn)
            back = V[nl, 1] > yn
            print("NECK" + ("_WIDE" if (dn.max() - Rn) / k > 0.08 else ""), name, i, ob.name.split("_Whole_")[-1], "max_open_k", round(float((dn.max() - Rn) / k), 3),
                  "side_drop_k", round(float((nz - V[nl][np.abs(V[nl, 0] - b.cx) > 0.6 * Rn, 2].min()) / k), 3) if (np.abs(V[nl, 0] - b.cx) > 0.6 * Rn).any() else None)
        for l in loops:
            P = V[l]; c = P.mean(0)
            per = sum(np.linalg.norm(V[x] - V[y]) for x in l for y in adj[x] if y > x) / k
            j = jn[int(cKDTree(JP).query(c)[1])]
            bad = not any(t in j for t in OK)
            if (bad and per < 1.0) or per < 0.12:
                print("HOLE" if bad else "SMALL", name, i, ob.name.replace(name + "_Whole_", ""), "n", len(l), "perim_k", round(per, 3), "near", j, "z_k", round((c[2] - b.floor) / k, 3))
    for ob in o.objs: bpy.data.objects.remove(ob, do_unlink=True)
print("DONE", name)
