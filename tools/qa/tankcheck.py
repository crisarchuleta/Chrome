"""tankcheck.py <Body> [Top,Outer]: builds every catalog top alone on the body and reports how much of the
base-layer tank can be seen (rays out along the tank normals that hit neither the garment nor arm/torso skin)."""
import bpy, sys, numpy as np, json
import os; sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
import nc_garments as NG, nc_catalog3d as CM
from scipy.spatial import cKDTree
from mathutils.bvhtree import BVHTree
from mathutils import Vector
bpy.ops.wm.open_mainfile(filepath=os.environ.get("NC_RIG", "NeonCoast_MakeHumanRig.blend"))
name = sys.argv[-2]; slots = sys.argv[-1].split(",")
w = bpy.data.objects[name + "_Whole"]; a = bpy.data.objects["NC_" + name]
b = NG.RigBody(w, a); k = b.k
me = w.data
V = np.array([v.co[:] for v in me.vertices])
tmi = [i for i, m in enumerate(me.materials) if m and "TankTop" in m.name]
Fs = [list(p.vertices) for p in me.polygons]
tankf = np.array([p.material_index in tmi for p in me.polygons])
tankv = np.zeros(len(V), bool)
for f, t in zip(Fs, tankf):
    if t: tankv[f] = True
Nn = b.N[cKDTree(b.co).query(V)[1]]  # normals from the watertight shell (the Whole mesh has seams at x=0)
headv = np.asarray(b.whole_reg == "Head")
occF = [f for f, t in zip(Fs, tankf) if not t and not headv[f].all()]
idx = np.where(tankv)[0]
# tank pressed against the arm (heavy bodies, armpits) is hidden by the arm itself: leave it out
armv = np.isin(np.asarray(b.whole_reg), ["UArm", "LArm", "Hand"]) & ~tankv
if armv.any():
    da, _ = cKDTree(V[armv]).query(V[idx])
    idx = idx[da > 0.012 * k]
frontv = V[idx, 1] < b.J["neck"][1] - 0.02 * k
items = [it for it in CM.load(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "NCLookCatalog.lua")) if it["slot"] in slots]
res = {}
for it in items:
    o = NG.Outfit(b)
    try:
        ok = CM.build_item(o, it)
    except Exception as e:
        print("ERR", it["id"], e); continue
    if not ok or not o.objs:
        continue
    allV, allF, off = [V], list(occF), len(V)
    for ob in o.objs:
        Vg = np.array([v.co[:] for v in ob.data.vertices])
        allF += [[x + off for x in p.vertices] for p in ob.data.polygons]
        allV.append(Vg); off += len(Vg)
    tree = BVHTree.FromPolygons([Vector(x) for x in np.vstack(allV)], allF, all_triangles=False)
    exp = np.array([tree.ray_cast(Vector(V[i] + Nn[i] * 0.003 * k), Vector(Nn[i]), 2.0)[0] is None for i in idx])
    where = {}
    if exp.any():
        jn = list(b.J.keys()); JP = np.array([b.J[x] for x in jn])
        _, j = cKDTree(JP).query(V[idx[exp]])
        u_, c_ = np.unique(np.array(jn)[j], return_counts=True); where = dict(zip(u_.tolist(), c_.tolist()))
    pct = 100 * exp.mean(); pct_back = 100 * exp[~frontv].mean()
    res[it["id"]] = dict(fam=it["fam"], exposed=round(pct, 2), exposed_back=round(pct_back, 2), where=where)
    p_ = it["p"]
    is_open = (it["fam"] == "jacket" and p_.get("collar") == "lapel" and p_.get("open", True)) or it["fam"] in ("blazer", "labcoat") \
        or (it["fam"] in ("shirt",) and p_.get("open") and it["slot"] == "Outer")
    flag = "SHOWS" if (pct_back if is_open else pct) > 0.3 else ""
    if is_open: flag += " (open front)"
    print("TANKCHK", name, it["id"], it["fam"], round(pct, 2), round(pct_back, 2), where, flag, flush=True)
    for ob in o.objs:
        bpy.data.objects.remove(ob, do_unlink=True)
json.dump(res, open(f"tankchk_{name}.json", "w"), indent=1)
