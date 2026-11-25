# camera-ray poke check: orthographic rays from 16 views; flags rays whose first hit is skin while the same ray
# Usage: python -I camvis.py <Body> <id>[,<id>]   (dev paths: cloud build folders; compare against renders)
# hits garment right behind it (within 4 cm) -> skin visible through / in front of cloth that should cover it
import bpy, sys, numpy as np
sys.path.insert(0, "/tmp/claude-0/base"); sys.path.insert(0, "/tmp/claude-0/garm")
import nc_garments as NG, catalog_map as CM
from mathutils.bvhtree import BVHTree
from mathutils import Vector
bpy.ops.wm.open_mainfile(filepath="/tmp/claude-0/garm/rig_tank.blend")
name, ids = sys.argv[-2], sys.argv[-1].split(",")
w = bpy.data.objects[name + "_Whole"]; a = bpy.data.objects["NC_" + name]
b = NG.RigBody(w, a); k = b.k; o = NG.Outfit(b); CM.build_items(o, ids)
NG.skin_to_rig(o)
dg = bpy.context.evaluated_depsgraph_get()
def bvh(obs):
    V, F, off = [], [], 0
    for ob in obs:
        ev = ob.evaluated_get(dg); me = ev.to_mesh(); M = np.array(ob.matrix_world)
        X = np.array([v.co[:] for v in me.vertices]); X = (M @ np.c_[X, np.ones(len(X))].T).T[:, :3]
        V.append(X); F += [[i + off for i in p.vertices] for p in me.polygons]; off += len(X); ev.to_mesh_clear()
    V = np.vstack(V); return BVHTree.FromPolygons([Vector(x) for x in V], F), V
skins = [w] + [x for x in bpy.data.objects if x.type == "MESH" and x.name.startswith(name + "_") and x.name.endswith("_Geo") and x.visible_get()]
BT, BV = bvh([w]); GT, GV = bvh(o.objs)
lo, hi = GV.min(0), GV.max(0); c = (lo + hi) / 2; R = np.linalg.norm(hi - lo)
step = 0.006 * k; bad = []; tot = 0
for el in (-0.3, 0.0, 0.35):
    for az in np.linspace(0, 2 * np.pi, 16, endpoint=False):
        d = np.array([np.cos(az) * np.cos(el), np.sin(az) * np.cos(el), np.sin(el)]); d = -d
        u = np.cross(d, [0, 0, 1]); u /= np.linalg.norm(u); v = np.cross(u, d)
        for s in np.arange(-R / 2, R / 2, step):
            for t in np.arange(-R / 2, R / 2, step):
                p = c + u * s + v * t - d * R
                hb = BT.ray_cast(Vector(p), Vector(d), 2 * R)
                if hb[0] is None: continue
                hg = GT.ray_cast(Vector(p), Vector(d), 2 * R)
                if hg[0] is None: continue
                tot += 1
                if hb[3] < hg[3] - 0.002 * k and hg[3] - hb[3] < 0.04 * k:
                    bad.append(np.array(hb[0]))
bad = np.array(bad)
print("CAMVIS", name, ",".join(ids), "rays_on_cloth", tot, "skin_in_front", len(bad))
if len(bad):
    jn = list(b.J.keys()); M = np.array(w.matrix_world); JP = np.array([(M @ np.r_[b.J[x], 1])[:3] for x in jn])
    from scipy.spatial import cKDTree
    _, jj = cKDTree(JP).query(bad); u_, c_ = np.unique(np.array(jn)[jj], return_counts=True)
    print("  where", dict(zip(u_.tolist(), c_.tolist())), "z_k", np.round(np.percentile((bad[:, 2] - BV[:, 2].min()) / k, [5, 50, 95]), 3).tolist())
    np.save(f"/tmp/claude-0/garm/qa/camvis_{name}.npy", bad)
