# Dev QA script (paths point at the cloud build folders). Usage: python -I garment_qa.py <Body> cat:<id>[,<id>]
# Env: QA_MARK=<tag> exports a GLB with red markers on flagged skin; QA_POSEGLB=<tag> exports the walk pose; QA_SINK=<k> self-test.
"""Stretch + overlap check. Usage: qa.py <Body> <look|cat:id,id>
Builds the look, skins it to the rig, then for every garment reports
 - stretch: edge length change between rest and a walk pose (evaluated with all modifiers)
 - body overlap: vertices inside the body skin (rest and pose)
 - layer overlap: vertices of a later layer inside an earlier one (rest)."""
import bpy, sys, numpy as np, math, json, collections
sys.path.insert(0, "/tmp/claude-0/base"); sys.path.insert(0, "/tmp/claude-0/garm")
import nc_garments as NG, looks
from scipy.spatial import cKDTree
from mathutils import Euler
bpy.ops.wm.open_mainfile(filepath="/tmp/claude-0/garm/rig_tank.blend")
name, look = sys.argv[-2], sys.argv[-1]
w = bpy.data.objects[name + "_Whole"]; a = bpy.data.objects["NC_" + name]
b = NG.RigBody(w, a); o = NG.Outfit(b); k = b.k
if look.startswith("cat:"):
    import catalog_map as CM
    CM.build_items(o, look[4:].split(","))
else:
    looks.LOOKS[look](o)
import os
if os.environ.get("QA_SINK"):  # detector self-test: sink every garment into the body
    for ob in o.objs:
        me = ob.data; me.calc_normals() if hasattr(me, "calc_normals") else None
        for v in me.vertices: v.co = v.co - v.normal * float(os.environ["QA_SINK"]) * k
NG.skin_to_rig(o)
_M = np.array(w.matrix_world)
def JW(jn): return np.array([(_M @ np.r_[b.J[x], 1])[:3] for x in jn])

def evald(ob):
    dg = bpy.context.evaluated_depsgraph_get()
    ev = ob.evaluated_get(dg); me = ev.to_mesh()
    V = np.array([v.co[:] for v in me.vertices]); Nn = np.array([v.normal[:] for v in me.vertices])
    E = np.array([e.vertices[:] for e in me.edges]) if len(me.edges) else np.zeros((0, 2), int)
    M = np.array(ob.matrix_world)
    V = (M @ np.c_[V, np.ones(len(V))].T).T[:, :3]; Nn = (M[:3, :3] @ Nn.T).T
    Nn /= np.linalg.norm(Nn, axis=1, keepdims=True) + 1e-12
    ev.to_mesh_clear()
    return V, Nn, E

def body_depth(V, BV, BN, tree):
    d, j = tree.query(V)
    return np.einsum("ij,ij->i", V - BV[j], BN[j]), d

def snapshot():
    BV, BN, _ = evald(w); tree = cKDTree(BV)
    out = {}
    for ob in o.objs:
        V, Nn, E = evald(ob)
        dep, d = body_depth(V, BV, BN, tree)
        out[ob.name] = (V, Nn, E, dep, d)
    return out

def tank_exposure(key="TankTop"):
    """% of base-layer tank vertices that can be seen: a ray out along the tank normal hits no garment and no skin"""
    from mathutils.bvhtree import BVHTree
    from mathutils import Vector
    dg = bpy.context.evaluated_depsgraph_get()
    ev = w.evaluated_get(dg); me = ev.to_mesh()
    M = np.array(w.matrix_world)
    V = np.array([v.co[:] for v in me.vertices]); V = (M @ np.c_[V, np.ones(len(V))].T).T[:, :3]
    tank_mats = [i for i, m in enumerate(w.data.materials) if m and key in m.name]
    tankv = np.zeros(len(V), bool)
    Fs, Ftank = [], []
    for p in me.polygons:
        Fs.append(list(p.vertices))
        if p.material_index in tank_mats:
            tankv[list(p.vertices)] = True
    Nn = b.N[cKDTree(b.co).query(V)[1]] if np.allclose(V[:50], b.whole_co[:50], atol=1e-4) else vnormals_np(V, Fs)
    ev.to_mesh_clear()
    headv = np.asarray(b.whole_reg == "Head")
    allV, allF, off = [V], [f for f in Fs if not headv[f].all() and not tankv[f].all()], len(V)
    for ob in o.objs:
        Vg, _, _ = evald(ob)
        eg = ob.evaluated_get(dg); mg = eg.to_mesh()
        allF += [[x + off for x in p.vertices] for p in mg.polygons]
        eg.to_mesh_clear()
        allV.append(Vg); off += len(Vg)
    AV = np.vstack(allV)
    tree = BVHTree.FromPolygons([Vector(x) for x in AV], allF, all_triangles=False)
    idx = np.where(tankv)[0]
    exp = np.zeros(len(idx), bool)
    for n_, i in enumerate(idx):
        p0 = Vector(V[i] + Nn[i] * 0.003 * k)
        hit = tree.ray_cast(p0, Vector(Nn[i]), 2.0)
        exp[n_] = hit[0] is None
    where = {}
    if exp.any():
        jn = list(b.J.keys()); JP = JW(jn)
        _, j = cKDTree(JP).query(V[idx[exp]])
        u_, c_ = np.unique(np.array(jn)[j], return_counts=True)
        where = dict(zip(u_.tolist(), c_.tolist()))
    return round(100 * float(exp.mean()), 2) if len(idx) else -1, where

def vnormals_np(P, faces):
    n = np.zeros_like(P)
    for f in faces:
        if len(f) >= 3:
            n[f] += np.cross(P[f[1]] - P[f[0]], P[f[2]] - P[f[0]])
    return n / np.maximum(np.linalg.norm(n, axis=1), 1e-12)[:, None]

def coverage_gaps():
    """Shoes / boots: % of foot and covered lower-leg skin with no garment along its normal within 3 cm (skin
    showing through a gap between pieces). Zone = feet, plus lower leg below the top of the shoe pieces."""
    from mathutils.bvhtree import BVHTree
    from mathutils import Vector
    shoe = [ob for ob in o.objs if "_shoe_" in ob.name]
    if not shoe:
        return None
    dg = bpy.context.evaluated_depsgraph_get()
    allV, allF, off = [], [], 0
    ztop = -1e9
    for ob in shoe:
        Vg, _, _ = evald(ob)
        eg = ob.evaluated_get(dg); mg = eg.to_mesh()
        allF += [[x + off for x in p.vertices] for p in mg.polygons]; eg.to_mesh_clear()
        allV.append(Vg); off += len(Vg); ztop = max(ztop, Vg[:, 2].max())
    AV = np.vstack(allV)
    tree = BVHTree.FromPolygons([Vector(x) for x in AV], allF, all_triangles=False)
    M_ = np.array(w.matrix_world)
    BW = (M_[:3, :3] @ np.asarray(b.co).T).T + M_[:3, 3]
    BNW = (M_[:3, :3] @ np.asarray(b.N).T).T
    BNW /= np.linalg.norm(BNW, axis=1, keepdims=True) + 1e-12
    reg = np.asarray(b.reg)
    flw = BW[:, 2].min()
    zone = (reg == "Foot") | ((reg == "LLeg") & (BW[:, 2] < ztop - 0.03 * k))
    zone &= BW[:, 2] > flw + 0.004 * k  # soles: skip the very bottom
    idx = np.where(zone)[0]
    gap = np.zeros(len(idx), bool)
    for n_, i in enumerate(idx):
        nn = BNW[i]
        hit = tree.ray_cast(Vector(BW[i] + nn * 0.0005 * k), Vector(nn), 0.08 * k)
        gap[n_] = hit[0] is None
    where = {}
    if gap.any():
        P_ = BW[idx[gap]]; jn_ = list(b.J.keys())
        ankw = np.array([BW[np.argmin(np.linalg.norm(b.co - b.J[s_ + "-ankle"], axis=1))] for s_ in "lr"])
        dy = np.array([p_[1] - ankw[np.argmin(np.abs(ankw[:, 0] - p_[0]))][1] for p_ in P_]) / k
        where = {"n": int(gap.sum()), "z_over_floor_k": np.round(np.percentile((P_[:, 2] - flw) / k, [5, 50, 95]), 3).tolist(),
                 "dy_from_ankle_k(+back)": np.round(np.percentile(dy, [5, 50, 95]), 3).tolist()}
    return round(100 * float(gap.mean()), 2), where

def poke_visible(tag):
    """Skin that shows THROUGH a garment: skin vertex just outside a garment surface it should be under
    (same facing, within 2 cm, away from the garment's open edges) whose outward ray hits no garment."""
    from mathutils.bvhtree import BVHTree
    from mathutils import Vector
    dg = bpy.context.evaluated_depsgraph_get()
    BV, BN, _ = evald(w)
    allV, allN, allF, bnd, own, off = [], [], [], [], [], 0
    for oi, ob in enumerate(o.objs):
        Vg, Ng, _ = evald(ob)
        eg = ob.evaluated_get(dg); mg = eg.to_mesh()
        F = [list(p.vertices) for p in mg.polygons]
        from collections import Counter
        ec = Counter()
        for f in F:
            for a_, b_ in zip(f, f[1:] + f[:1]):
                ec[(min(a_, b_), max(a_, b_))] += 1
        bv = np.zeros(len(Vg), bool)
        for (a_, b_), c in ec.items():
            if c == 1: bv[a_] = bv[b_] = True
        eg.to_mesh_clear()
        allF += [[x + off for x in f] for f in F]; allV.append(Vg); allN.append(Ng); bnd.append(bv)
        own += [oi] * len(Vg); off += len(Vg)
    if not allV: return {}
    AV = np.vstack(allV); AN = np.vstack(allN); AB = np.concatenate(bnd); own = np.array(own)
    tree = BVHTree.FromPolygons([Vector(x) for x in AV], allF, all_triangles=False)
    gt = cKDTree(AV); bt = cKDTree(AV[AB]) if AB.any() else None
    d, j = gt.query(BV)
    out_ = np.einsum("ij,ij->i", BV - AV[j], AN[j])
    facing = np.einsum("ij,ij->i", BN, AN[j])
    cand = (d < 0.02 * k) & (out_ > 0.0015 * k) & (facing > 0.3)
    # only skin in body regions this garment actually covers (hands resting on pants are not poke-through)
    breg = np.asarray(b.whole_reg) if len(b.whole_reg) == len(BV) else None
    if breg is not None:  # garment regions from its own bone weights
        covered = {}
        for oi, ob in enumerate(o.objs):
            gn = [g.name for g in ob.vertex_groups]; cnt = collections.Counter()
            for v in ob.data.vertices:
                if len(v.groups):
                    g = max(v.groups, key=lambda g_: g_.weight); cnt[NG.REGION_OF_BONE.get(gn[g.group], "X")] += 1
            tot = max(sum(cnt.values()), 1)
            covered[oi] = {r_ for r_, c_ in cnt.items() if c_ > 0.03 * tot}
        cand &= np.array([breg[i] in covered[own[j[i]]] for i in range(len(BV))])
    if bt is not None:
        db, _ = bt.query(BV); cand &= db > 0.025 * k
    res = {}
    for i in np.where(cand)[0]:
        hit = tree.ray_cast(Vector(BV[i] + BN[i] * 0.0005 * k), Vector(BN[i]), 0.15 * k)
        # true poke-through: the garment lies right beneath this skin (sunk into the body), nothing outside it
        under_ = tree.ray_cast(Vector(BV[i]), Vector(-BN[i]), 0.025 * k)
        if hit[0] is None and under_[0] is not None:
            nm = o.objs[own[j[i]]].name.replace(name + "_", "")
            res.setdefault(nm, []).append(i)
    rep = {}
    jn = list(b.J.keys()); JP = JW(jn)
    for nm, ids in res.items():
        _, jj = cKDTree(JP).query(BV[ids])
        u_, c_ = np.unique(np.array(jn)[jj], return_counts=True)
        rep[nm] = {"_pts": BV[ids], "n": len(ids), "where": dict(zip(u_.tolist(), c_.tolist())),
                   "z_k": np.round(np.percentile((BV[ids, 2] - BV[:, 2].min()) / k, [5, 50, 95]), 3).tolist()}
    for nm, r_ in rep.items():
        print("POKE", tag, name, look[:40], nm, {k_: v_ for k_, v_ in r_.items() if k_ != "_pts"})
    return rep

tank_rest = tank_exposure()
if any(x in look for x in ("bot_", "pants", "skirt")):
    print("SHORTS", name, look[:40], "exposed% rest", *tank_exposure("Shorts"))
gaps = coverage_gaps()
if gaps is not None:
    print("GAPS", name, look[:40], "uncovered%", gaps[0], gaps[1])
rest = snapshot()
poke_rest = poke_visible('rest')
if os.environ.get("QA_MARK"):
    mat = bpy.data.materials.new("MarkRed"); mat.diffuse_color = (1, 0, 0, 1)
    mat.use_nodes = True; mat.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (1, 0, 0, 1)
    marks = []
    for nm, r_ in poke_rest.items():
        for pt in r_["_pts"][::max(1, len(r_["_pts"]) // 300)]:
            bpy.ops.mesh.primitive_ico_sphere_add(radius=0.006 * k, subdivisions=1, location=tuple(pt))
            ob_ = bpy.context.active_object; ob_.data.materials.append(mat); marks.append(ob_)
    for ob in bpy.data.objects: ob.select_set(False)
    w.hide_set(False); w.hide_viewport = False; w.select_set(True)
    for ob in o.objs + marks: ob.select_set(True)
    bpy.context.view_layer.objects.active = w
    bpy.ops.export_scene.gltf(filepath=f"/tmp/claude-0/render/c_{name}_{os.environ['QA_MARK']}.glb", use_selection=True, export_apply=True, export_yup=True, export_vertex_color='ACTIVE')
    for ob_ in marks: bpy.data.objects.remove(ob_, do_unlink=True)
pb = a.pose.bones
def rot(n, x=0, y=0, z=0):
    if n in pb:
        pb[n].rotation_mode = 'XYZ'; pb[n].rotation_euler = Euler((math.radians(x), math.radians(y), math.radians(z)))
rot("RightUpperArm", 60, 0, 0); rot("RightLowerArm", 45, 0, 0)
rot("LeftUpperArm", -25, 0, 0); rot("LeftLowerArm", 20, 0, 0)
rot("LeftUpperLeg", 30, 0, 0); rot("LeftLowerLeg", -35, 0, 0)
rot("RightUpperLeg", -15, 0, 0); rot("Head", 0, 0, 20)
bpy.context.view_layer.update()
pose = snapshot()
if os.environ.get("QA_POSEGLB"):
    for ob in bpy.data.objects: ob.select_set(False)
    w.hide_set(False); w.hide_viewport = False; w.select_set(True)
    for ob in o.objs: ob.select_set(True)
    bpy.context.view_layer.objects.active = w
    bpy.ops.export_scene.gltf(filepath=f"/tmp/claude-0/render/c_{name}_{os.environ['QA_POSEGLB']}.glb", use_selection=True, export_apply=True, export_yup=True, export_vertex_color='ACTIVE')
poke_pose = poke_visible('pose')
tank_pose = tank_exposure()
print("TANK", name, look[:30], "exposed% rest", tank_rest[0], tank_rest[1], "pose", tank_pose[0], tank_pose[1])
names = [ob.name for ob in o.objs]
report = []
tol = 0.004 * k
for i, nm in enumerate(names):
    V0, N0, E, dep0, d0 = rest[nm]; V1, N1, _, dep1, d1 = pose[nm]
    short = nm.replace(name + "_", "")
    r = {"item": short}
    if len(E):
        l0 = np.linalg.norm(V0[E[:, 0]] - V0[E[:, 1]], axis=1); l1 = np.linalg.norm(V1[E[:, 0]] - V1[E[:, 1]], axis=1)
        ok = l0 > 1e-6; ratio = l1[ok] / l0[ok]
        r["stretch_p99"] = round(float(np.percentile(ratio, 99)), 3)
        r["stretch_max"] = round(float(ratio.max()), 3)
        r["stretched_edges_pct"] = round(100 * float((ratio > 1.25).mean()), 2)
        r["squashed_edges_pct"] = round(100 * float((ratio < 0.6).mean()), 2)
    near0 = d0 < 0.03 * k; near1 = d1 < 0.03 * k
    r["inside_body_rest_pct"] = round(100 * float(((dep0 < -tol) & near0).mean()), 2)
    r["inside_body_pose_pct"] = round(100 * float(((dep1 < -tol) & near1).mean()), 2)
    # layer overlap at rest vs earlier objects
    worst = 0.0; worst_with = ""
    for jn in names[:i]:
        Vb, Nb, _, _, _ = rest[jn]
        if len(Vb) < 20:
            continue
        tb = cKDTree(Vb); d, j = tb.query(V0)
        dep = np.einsum("ij,ij->i", V0 - Vb[j], Nb[j])
        frac = float(((dep < -tol) & (d < 0.01 * k)).mean())
        if frac > worst:
            worst, worst_with = frac, jn.replace(name + "_", "")
    r["inside_layer_rest_pct"] = round(100 * worst, 2); r["layer"] = worst_with
    flags = []
    if r.get("stretched_edges_pct", 0) > 0.5 or r.get("stretch_p99", 1) > 1.3: flags.append("STRETCH")
    if r["inside_body_rest_pct"] > 0.5 or r["inside_body_pose_pct"] > 1.0: flags.append("BODY")
    if r["inside_layer_rest_pct"] > 0.5: flags.append("LAYER")
    r["flags"] = flags
    insd = (dep0 < -tol) & near0
    if insd.mean() > 0.002:
        jn_ = list(b.J.keys()); JP_ = JW(jn_)
        _, j_ = cKDTree(JP_).query(V0[insd])
        u_, c_ = np.unique(np.array(jn_)[j_], return_counts=True)
        r["inside_where"] = dict(zip(u_.tolist(), c_.tolist()))
        r["inside_depth_k"] = round(float(np.percentile(-dep0[insd], 90) / k), 4)
        r["inside_z_k"] = np.round(np.percentile((V0[insd, 2] - b.floor) / k, [5, 50, 95]), 3).tolist()
    report.append(r)
json.dump(report, open(f"/tmp/claude-0/garm/qa/qa_{name}_{look.replace(':','_').replace(',','+')[:60]}.json", "w"), indent=1)
for r in report:
    if r.get("inside_where"): print("INSIDE", r["item"], r["inside_where"], "depth90_k", r["inside_depth_k"], "z_k", r["inside_z_k"])
    print("QA", name, look[:30], r["item"], r.get("stretch_p99"), r.get("stretched_edges_pct"), r["inside_body_rest_pct"], r["inside_body_pose_pct"], r["inside_layer_rest_pct"], r["layer"], ",".join(r["flags"]))
# where is the stretch? nearest body region of stretched edges
WT = cKDTree(b.whole_co)
for nm in names:
    V0, N0, E, _, _ = rest[nm]; V1 = pose[nm][0]
    if not len(E): continue
    l0 = np.linalg.norm(V0[E[:, 0]] - V0[E[:, 1]], axis=1); l1 = np.linalg.norm(V1[E[:, 0]] - V1[E[:, 1]], axis=1)
    bad = (l1 / np.maximum(l0, 1e-9)) > 1.25
    if bad.mean() > 0.005:
        mid = 0.5 * (V0[E[bad, 0]] + V0[E[bad, 1]])
        jn = list(b.J.keys()); JP = JW(jn)
        _, j = cKDTree(JP).query(mid)
        u, c = np.unique(np.array(jn)[j], return_counts=True)
        print("WHERE", nm.replace(name + "_", ""), dict(zip(u, c)), "zrange", np.round((np.percentile(mid[:, 2], [5, 50, 95])) / k, 3))
BV0, _, BE = evald(w)  # pose is still applied: recompute rest by clearing pose
for pbn in pb: pbn.rotation_euler = Euler((0, 0, 0))
bpy.context.view_layer.update()
BR, _, BE = evald(w)
for n_, (ax, x) in {"RightUpperArm": (0, 60), "RightLowerArm": (0, 45), "LeftUpperArm": (0, -25), "LeftLowerArm": (0, 20), "LeftUpperLeg": (0, 30), "LeftLowerLeg": (0, -35), "RightUpperLeg": (0, -15), "Head": (2, 20)}.items():
    e = [0, 0, 0]; e[ax] = math.radians(x); pb[n_].rotation_euler = Euler(e)
bpy.context.view_layer.update()
BP, _, _ = evald(w)
l0 = np.linalg.norm(BR[BE[:, 0]] - BR[BE[:, 1]], axis=1); l1 = np.linalg.norm(BP[BE[:, 0]] - BP[BE[:, 1]], axis=1)
ratio = l1 / np.maximum(l0, 1e-9)
print("BODYSKIN p99", round(float(np.percentile(ratio, 99)), 3), "pct>1.25", round(100 * float((ratio > 1.25).mean()), 2), "max", round(float(ratio.max()), 2))
