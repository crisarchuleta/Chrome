# Hand vertices that end up inside a garment at the rest pose. Usage: python -I handsink.py <Body> <id>[,<id>] (dev paths)
# hand vertices that end up INSIDE a garment (fingers sunk into pants/skirt) at the rest pose
import bpy, sys, numpy as np
sys.path.insert(0, "/tmp/claude-0/base"); sys.path.insert(0, "/tmp/claude-0/garm")
import nc_garments as NG, catalog_map as CM
from mathutils.bvhtree import BVHTree
from mathutils import Vector
bpy.ops.wm.open_mainfile(filepath="/tmp/claude-0/garm/rig_tank.blend")
name, ids = sys.argv[-2], sys.argv[-1].split(",")
w = bpy.data.objects[name + "_Whole"]; a = bpy.data.objects["NC_" + name]
b = NG.RigBody(w, a); k = b.k; o = NG.Outfit(b); CM.build_items(o, ids); NG.skin_to_rig(o)
dg = bpy.context.evaluated_depsgraph_get()
def ev(ob):
    e = ob.evaluated_get(dg); me = e.to_mesh(); M = np.array(ob.matrix_world)
    X = np.array([v.co[:] for v in me.vertices]); X = (M @ np.c_[X, np.ones(len(X))].T).T[:, :3]
    F = [list(p.vertices) for p in me.polygons]; e.to_mesh_clear(); return X, F
BV, _ = ev(w); reg = np.asarray(b.whole_reg)
hand = np.isin(reg, ["LHand", "RHand", "Hand"]) if reg.dtype.kind in "UO" else None
print("regs", sorted(set(reg.tolist()))[:20])
for ob in o.objs:
    for m in ob.modifiers:
        if m.type == "SOLIDIFY": m.show_viewport = False
    dg = bpy.context.evaluated_depsgraph_get()
    X, F = ev(ob); t = BVHTree.FromPolygons([Vector(x) for x in X], F)
    H = BV[hand]; n_in = 0; depth = []
    for p in H:
        loc, nrm, fi, d = t.find_nearest(Vector(p), 0.05 * k)
        if loc is None: continue
        s = np.dot(p - np.array(loc), np.array(nrm))
        if s < -0.001 * k: n_in += 1; depth.append(-s / k)
    print("HANDSINK", name, ob.name.split("_Whole_")[-1], "hand verts inside", n_in, "of", len(H), "max depth_k", round(max(depth), 4) if depth else 0)
