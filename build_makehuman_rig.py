# Neon Coast: rig the MakeHuman bodies for Roblox. THE character model of the game (decided 2026-11-23).
#   blender --background --python build_makehuman_rig.py            (needs no add-on; reads NeonCoast_MakeHuman.blend)
#   env: NC_OUT (folder, default the PC folder), NC_BODIES=Male_Average,Female_Average (only some)
#
# In:  NeonCoast_MakeHuman.blend from build_makehuman.py: ten MakeHuman bodies (Male/Female x Skinny, Average,
#      Athletic, Muscular, Heavy), each already wearing the permanent base layer from nc_baselayer.py (white tank top,
#      dark boxer shorts, locked NC_Modesty shape key).
# Out: NC_Body_<Gender>_<Build>.fbx  - one per body: 15 skinned R15 MeshParts named <Part>_Geo + the armature
#      NeonCoast_MakeHumanRig.blend - all ten rigged bodies (+ <Body>_Whole: the unsplit weighted mesh, for garments)
#      NCBodyData.lua               - per body: height, HipHeight, the attachments Character Studio and tools use
#      AssembleMakeHumanBodies.lua  - Studio command bar: finishes the imported bodies and files them in ServerStorage
#      makehuman_rig.json           - stats (triangles per part, weights check)
#
# The rig is the SAME 55-bone skeleton as build_human.py (same names, parents and axes): the 15 standard R15 joints
# (so Humanoid, tools, seats, ragdoll and every script keep working) and 40 extra NC_ bones: mid-spine, upper neck,
# collarbones, forearm twist, 3 bones in every finger and thumb, and toes. So NCAnimationsHuman.lua plays on these
# bodies unchanged, and anything that worked on the old human works here.
#
# Steps for each body:
#   1. take the body with the modesty shape key baked in and the tank top + shorts, in studs (3.77 studs a metre)
#   2. skin it with heat weights on a temporary rig whose bones run along the limbs (garments copy the weights of
#      the skin under them, so they move exactly with it)
#   3. re-pose MakeHuman's A-pose into the rest pose the animations were made for: arms hanging 7 degrees out,
#      elbows straight, palms facing the thighs, fingers straight, legs straight under the hips
#   4. delete the skin that the tank top and shorts fully cover (nothing is under the clothes, and nothing can poke
#      through), and join the base layer into the body for good: it can't be taken off
#   5. split into the 15 R15 pieces by weight (seams share weights, so they never open) and cap every cut
# NO NUDITY: the base layer is part of the body mesh itself. NCLookBuilder also paints torso/hips/thighs as clothes.
import bpy, bmesh, math, json, os, sys
import numpy as np
from mathutils import Vector, Matrix
from mathutils.kdtree import KDTree

OUT = os.environ.get("NC_OUT", r"C:\Users\Crisa\Documents\NeonCoast_Blender")
PREV = os.path.join(OUT, "previews")
os.makedirs(PREV, exist_ok=True)
SRC = os.environ.get("NC_MH_BLEND", os.path.join(OUT, "NeonCoast_MakeHuman.blend"))
ONLY = [s for s in os.environ.get("NC_BODIES", "").split(",") if s]
sys.path.insert(0, OUT)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import nc_baselayer as NB

SPM = 6.6 / 1.75          # studs per metre (the world scale every Neon Coast model uses)
D2R = math.pi / 180
ABD = 7 * D2R             # rest pose: arms hang 7 degrees out from the body (as build_human.py)

bpy.ops.wm.open_mainfile(filepath=SRC)
# ribbed-knit tank texture: write the PNGs next to the FBX files and point the tank material at them, so the
# FBX export copies them (Roblox: colour map on the mesh; the normal map is for a SurfaceAppearance)
for _im_name, _p in NB.write_rib_pngs(OUT).items():
    _im = bpy.data.images.get(_im_name)
    if _im is not None:
        if _im.packed_file:
            _im.unpack(method="REMOVE")
        _im.filepath = _p
        _im.reload()
scene = bpy.context.scene
SOURCES = [o for o in bpy.data.objects if o.type == "MESH" and o.get("nc_base_layer") == "tanktop+shorts"]
if ONLY:
    SOURCES = [o for o in SOURCES if o.name in ONLY]
assert SOURCES, "no MakeHuman bodies with the base layer in " + SRC
for o in list(bpy.data.objects):          # start a clean scene: the sources stay as data until used
    if o not in SOURCES and not (o.parent in SOURCES):
        bpy.data.objects.remove(o, do_unlink=True)

# ------------------------------------------------------------------------------------------------ the skeleton
SIDES = (("Right", "R", "r", -1), ("Left", "L", "l", 1))      # (Roblox side, suffix, MakeHuman side, Blender x sign)
FINGERS = {"Thumb": 1, "Index": 2, "Middle": 3, "Ring": 4, "Pinky": 5}
PARENT = {"HumanoidRootNode": "Root", "LowerTorso": "HumanoidRootNode", "UpperTorso": "LowerTorso", "Head": "UpperTorso",
          "NC_SpineMid": "LowerTorso", "NC_NeckMid": "UpperTorso"}
for side, s, m, bx in SIDES:
    PARENT.update({side + "UpperArm": "UpperTorso", side + "LowerArm": side + "UpperArm", side + "Hand": side + "LowerArm",
                   side + "UpperLeg": "LowerTorso", side + "LowerLeg": side + "UpperLeg", side + "Foot": side + "LowerLeg",
                   "NC_Clavicle" + s: "UpperTorso", "NC_Twist" + s: side + "LowerArm", "NC_Toes" + s: side + "Foot"})
    for f in FINGERS:
        PARENT[f"NC_{f}{s}1"] = side + "Hand"
        PARENT[f"NC_{f}{s}2"] = f"NC_{f}{s}1"
        PARENT[f"NC_{f}{s}3"] = f"NC_{f}{s}2"
BONES = ["Root"] + list(PARENT)
JOINT_OF_PART = {"LowerTorso": "Root", "UpperTorso": "Waist", "Head": "Neck"}
for side, s, m, bx in SIDES:
    JOINT_OF_PART.update({side + "UpperArm": side + "Shoulder", side + "LowerArm": side + "Elbow", side + "Hand": side + "Wrist",
                          side + "UpperLeg": side + "Hip", side + "LowerLeg": side + "Knee", side + "Foot": side + "Ankle"})
R15_PARTS = list(JOINT_OF_PART)
PART_OF_BONE = {}
for b in BONES:
    p = b
    while p not in JOINT_OF_PART and p in PARENT:
        p = PARENT[p]
    PART_OF_BONE[b] = p if p in JOINT_OF_PART else None
PART_OF_BONE["NC_SpineMid"] = "UpperTorso"
PART_OF_BONE["NC_NeckMid"] = "Head"
DEFORM = [b for b in BONES if b not in ("Root", "HumanoidRootNode")]

# face bones (children of Head) for the face shape sliders: where they sit and how far each reaches come from
# build_heads.py (heads.json, measured on each gender's Average head, fitted to every body by its eyes). Only the
# export rig has them, and they only take weight from the Head, so no other bone, part or attachment changes.
FACE = None
for _p in (os.path.join(OUT, "heads.json"), os.path.join(os.path.dirname(os.path.abspath(__file__)), "heads.json")):
    if os.path.exists(_p):
        with open(_p) as _f:
            FACE = json.load(_f)
        break
FACE_BONES = sorted({b for g in (FACE or {}).values() for b in g.get("bones", {})})
for _b in FACE_BONES:
    PART_OF_BONE[_b] = "Head"

COLOURS = {"Skin": (0.78, 0.58, 0.45, 1), "NC_BaseLayer_TankTop": NB.SHIRT_RGBA, "NC_BaseLayer_Shorts": NB.SHORTS_RGBA}


def material(name):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.diffuse_color = COLOURS.get(name, (0.8, 0.8, 0.8, 1))
    m.use_nodes = True
    bsdf = m.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = m.diffuse_color
        bsdf.inputs["Roughness"].default_value = 0.6 if name == "Skin" else 0.9
    return m


def activate(ob):
    bpy.ops.object.select_all(action="DESELECT")
    ob.select_set(True)
    bpy.context.view_layer.objects.active = ob


def tri_count(ob):
    ob.data.calc_loop_triangles()
    return len(ob.data.loop_triangles)


def link(ob):
    scene.collection.objects.link(ob)
    return ob


# ------------------------------------------------------------------------------------------------ 1. meshes in studs
def take_body(src):
    co = NB._eval_coords(src)                  # with NC_Modesty (locked at 1) mixed in, no helper mask
    G = NB._groups(src)
    JM = {k[6:]: Vector(co[v].mean(0)) * SPM for k, v in G.items() if k.startswith("joint-")}
    keep = np.zeros(len(co), bool)
    keep[G["body"]] = True
    eyes = {}
    for m in ("l", "r"):
        idx = G.get(f"helper-{m}-eye")
        if idx is not None and len(idx):
            pts = co[idx] * SPM
            eyes[m] = (Vector(pts.mean(0)), float(np.linalg.norm(pts - pts.mean(0), axis=1).mean()))
    bm = bmesh.new()
    bm.from_mesh(src.data)
    for name in list(bm.verts.layers.shape.keys()):
        bm.verts.layers.shape.remove(bm.verts.layers.shape[name])
    dl = bm.verts.layers.deform.active
    if dl:
        bm.verts.layers.deform.remove(dl)
    bm.verts.ensure_lookup_table()
    for v in bm.verts:
        v.co = Vector(co[v.index]) * SPM
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not keep[v.index]], context="VERTS")
    me = bpy.data.meshes.new(src.name + "_Body")
    bm.to_mesh(me)
    bm.free()
    me.materials.clear()
    me.materials.append(material("Skin"))
    for p in me.polygons:
        p.use_smooth = True
        p.material_index = 0
    body = link(bpy.data.objects.new(src.name + "_Body", me))
    garments = []
    dg = bpy.context.evaluated_depsgraph_get()
    for ch in src.children:
        if not ch.get("nc_base_layer"):
            continue
        gm = bpy.data.meshes.new_from_object(ch.evaluated_get(dg))      # solidify applied; coords = body local space
        gm.transform(Matrix.Scale(SPM, 4))
        g = link(bpy.data.objects.new(ch.name, gm))
        g["nc_base_layer"] = True
        garments.append(g)
    return body, garments, JM, eyes


# ------------------------------------------------------------------------------------------------ 2. joints + weights
def joints_from(JM):
    P = {}
    P["LowerTorso"] = JM["pelvis"].copy()
    P["HumanoidRootNode"] = JM["pelvis"] + Vector((0, 0, 0.15))
    P["UpperTorso"] = JM["spine-3"].copy()
    P["NC_SpineMid"] = (JM["spine-2"] + JM["spine-1"]) / 2
    P["Head"] = JM["neck"].copy()
    P["NC_NeckMid"] = (JM["neck"] + JM["head"]) / 2
    P["_HeadTop"] = JM["head-2"].copy()
    P["_Head"] = JM["head"].copy()
    for side, s, m, bx in SIDES:
        P["NC_Clavicle" + s] = JM[m + "-clavicle"].copy()
        P[side + "UpperArm"] = JM[m + "-shoulder"].copy()
        P[side + "LowerArm"] = JM[m + "-elbow"].copy()
        P[side + "Hand"] = JM[m + "-hand"].copy()
        P["NC_Twist" + s] = P[side + "LowerArm"].lerp(P[side + "Hand"], 0.55)
        P[side + "UpperLeg"] = JM[m + "-upper-leg"].copy()
        P[side + "LowerLeg"] = JM[m + "-knee"].copy()
        P[side + "Foot"] = JM[m + "-ankle"].copy()
        P["NC_Toes" + s] = JM[m + "-toe-3-1"].copy()
        P["_ToeTip" + s] = JM[m + "-toe-3-4"].copy()
        P["_Heel" + s] = Vector((JM[m + "-ankle"].x, JM[m + "-ankle"].y + 0.25, 0.0))
        for f, n in FINGERS.items():
            for k in (1, 2, 3):
                P[f"NC_{f}{s}{k}"] = JM[f"{m}-finger-{n}-{k}"].copy()
            P[f"_{f}{s}Tip"] = JM[f"{m}-finger-{n}-4"].copy()
    return P


def segments(P):
    """head/tail of every deform bone along its limb (what heat weighting needs)"""
    S = {"LowerTorso": (P["LowerTorso"] - Vector((0, 0, 0.3)), P["NC_SpineMid"].lerp(P["UpperTorso"], 0.5)),
         "NC_SpineMid": (P["NC_SpineMid"].lerp(P["UpperTorso"], 0.5), P["NC_SpineMid"] + Vector((0, 0, 0.2))),
         "UpperTorso": (P["NC_SpineMid"] + Vector((0, 0, 0.2)), P["Head"]),
         "NC_NeckMid": (P["Head"], P["_Head"]), "Head": (P["_Head"], P["_HeadTop"])}
    for side, s, m, bx in SIDES:
        S["NC_Clavicle" + s] = (P["NC_Clavicle" + s], P["NC_Clavicle" + s].lerp(P[side + "UpperArm"], 0.85))
        S[side + "UpperArm"] = (P[side + "UpperArm"], P[side + "LowerArm"])
        S[side + "LowerArm"] = (P[side + "LowerArm"], P["NC_Twist" + s])
        S["NC_Twist" + s] = (P["NC_Twist" + s], P[side + "Hand"])
        S[side + "Hand"] = (P[side + "Hand"], P[f"NC_Middle{s}1"])
        S[side + "UpperLeg"] = (P[side + "UpperLeg"], P[side + "LowerLeg"])
        S[side + "LowerLeg"] = (P[side + "LowerLeg"], P[side + "Foot"])
        S[side + "Foot"] = (P[side + "Foot"], P["NC_Toes" + s])
        S["NC_Toes" + s] = (P["NC_Toes" + s], P["_ToeTip" + s])
        for f in FINGERS:
            S[f"NC_{f}{s}1"] = (P[f"NC_{f}{s}1"], P[f"NC_{f}{s}2"])
            S[f"NC_{f}{s}2"] = (P[f"NC_{f}{s}2"], P[f"NC_{f}{s}3"])
            S[f"NC_{f}{s}3"] = (P[f"NC_{f}{s}3"], P[f"_{f}{s}Tip"])
    return S


def make_armature(name, heads, segs=None):
    """segs given: bones along the limbs (weighting). Otherwise the export rig: every bone straight up and rolled
    half round so its local axes are Roblox's axes, exactly as build_human.py (the animations depend on it)."""
    ad = bpy.data.armatures.new(name)
    ob = link(bpy.data.objects.new(name, ad))
    activate(ob)
    bpy.ops.object.mode_set(mode="EDIT")
    eb = ad.edit_bones
    for b in BONES:
        e = eb.new(b)
        hd = Vector((0, 0, 0)) if b == "Root" else heads[b]
        if segs and b in segs:
            e.head, e.tail = segs[b]
            e.roll = 0
        else:
            e.head = hd
            e.tail = hd + Vector((0, 0, 0.25))
            e.roll = math.pi
        e.use_deform = b in DEFORM
    for b, p in PARENT.items():
        eb[b].parent = eb[p]
        eb[b].use_connect = False
    bpy.ops.object.mode_set(mode="OBJECT")
    return ob


def seg_dist(p, a, b):
    ab = b - a
    t = max(0.0, min(1.0, (p - a).dot(ab) / max(ab.length_squared, 1e-9)))
    return (a + ab * t - p).length


def weights_of(ob):
    names = {g.index: g.name for g in ob.vertex_groups}
    W = [dict() for _ in ob.data.vertices]
    for v in ob.data.vertices:
        for ge in v.groups:
            if ge.weight > 1e-4:
                W[v.index][names[ge.group]] = ge.weight
    return W


def skin(body, garments, P):
    S = segments(P)
    warm = make_armature("WeightRig", P, S)
    activate(body)
    warm.select_set(True)
    bpy.context.view_layer.objects.active = warm
    bpy.ops.object.parent_set(type="ARMATURE_AUTO")
    W = weights_of(body)
    have = {b: 0 for b in DEFORM}
    for w in W:
        for b, x in w.items():
            if x > 0.01 and b in have:
                have[b] += 1
    missing = [b for b in DEFORM if have[b] < 3]
    for b in missing:                       # any bone the heat solver missed gets envelope weights on its segment
        g = body.vertex_groups.get(b) or body.vertex_groups.new(name=b)
        a, e = S[b]
        rad = 0.09 if any(f in b for f in FINGERS) else 0.3
        for v in body.data.vertices:
            d = seg_dist(v.co, a, e)
            if d < rad:
                g.add([v.index], (1 - d / rad) ** 2, "ADD")
    activate(body)
    bpy.ops.object.vertex_group_limit_total(group_select_mode="ALL", limit=4)
    bpy.ops.object.vertex_group_normalize_all(group_select_mode="ALL", lock_active=False)
    W = weights_of(body)
    # garments: each vertex copies the skin straight under it (they were made from that skin)
    kd = KDTree(len(body.data.vertices))
    for v in body.data.vertices:
        kd.insert(v.co, v.index)
    kd.balance()
    for g in garments:
        for b in DEFORM:
            g.vertex_groups.new(name=b)
        gi = {vg.name: vg.index for vg in g.vertex_groups}
        for v in g.data.vertices:
            near = kd.find_n(v.co, 3)
            acc = {}
            tot = 0.0
            for co, i, d in near:
                k = 1.0 / max(d, 1e-4)
                tot += k
                for b, x in W[i].items():
                    acc[b] = acc.get(b, 0.0) + x * k
            for b, x in acc.items():
                g.vertex_groups[gi[b]].add([v.index], x / tot, "REPLACE")
        g.parent = warm
        mod = g.modifiers.new("Armature", "ARMATURE")
        mod.object = warm
        activate(g)
        bpy.ops.object.vertex_group_limit_total(group_select_mode="ALL", limit=4)
        bpy.ops.object.vertex_group_normalize_all(group_select_mode="ALL", lock_active=False)
    return warm, missing


# ------------------------------------------------------------------------------------------------ 3. re-pose
def repose(warm, objs, P):
    """MakeHuman's A-pose -> the animation rest pose. Moves the bones, bakes the meshes, returns the new joints."""
    activate(warm)
    bpy.ops.object.mode_set(mode="POSE")
    pbs = warm.pose.bones
    rest = {b.name: b.matrix_local.copy() for b in warm.data.bones}
    report = {}

    def rot_world(bname, R):
        pb = pbs[bname]
        M = pb.matrix.copy()
        hd = M.translation.copy()
        pb.matrix = Matrix.Translation(hd) @ R.to_4x4() @ Matrix.Translation(-hd) @ M
        bpy.context.view_layer.update()

    def posed(b, p):
        """where the rest-pose point p (carried by bone b) is now"""
        return pbs[b].matrix @ rest[b].inverted() @ p

    for side, s, m, bx in SIDES:
        arm = Vector((bx * math.sin(ABD), 0, -math.cos(ABD)))
        # upper arm down to 7 degrees out, then the elbow straight
        sh, el = P[side + "UpperArm"], P[side + "LowerArm"]
        d = (el - sh).normalized()
        report[side + "ArmDrop"] = round(math.degrees(d.angle(arm)), 1)
        rot_world(side + "UpperArm", d.rotation_difference(arm).to_matrix())
        el2, wr2 = posed(side + "UpperArm", el), posed(side + "LowerArm", P[side + "Hand"])
        d = (wr2 - el2).normalized()
        report[side + "ElbowStraighten"] = round(math.degrees(d.angle(arm)), 1)
        rot_world(side + "LowerArm", d.rotation_difference(arm).to_matrix())
        # palm faces the thigh (index knuckle forward of the pinky knuckle): twist spread over forearm and wrist
        i1 = posed(side + "Hand", P[f"NC_Index{s}1"])
        p1 = posed(side + "Hand", P[f"NC_Pinky{s}1"])
        across = (i1 - p1)
        across -= arm * across.dot(arm)
        want = Vector((0, -1, 0)) - arm * Vector((0, -1, 0)).dot(arm)
        ang = across.normalized().angle(want.normalized())
        if across.normalized().cross(want.normalized()).dot(arm) < 0:
            ang = -ang
        report[side + "Twist"] = round(math.degrees(ang), 1)
        for b, share in ((side + "LowerArm", 0.3), ("NC_Twist" + s, 0.4), (side + "Hand", 0.3)):
            rot_world(b, Matrix.Rotation(ang * share, 3, arm))
        # hand in line with the forearm (no wrist bend), then every finger straight out along its own knuckle line
        wr = posed("NC_Twist" + s, P[side + "Hand"])
        mid = posed(side + "Hand", P[f"NC_Middle{s}1"])
        d = (mid - wr).normalized()
        hand_dir = (d - arm * 0).normalized()
        flat = d - d.dot(Vector((0, 1, 0))) * Vector((0, 1, 0))      # keep the palm's sideways set, remove fwd/back bend
        rot_world(side + "Hand", d.rotation_difference(arm.lerp(flat.normalized(), 0.3).normalized()).to_matrix())
        wr = posed("NC_Twist" + s, P[side + "Hand"])
        for f in ("Index", "Middle", "Ring", "Pinky"):
            knuckle = posed(side + "Hand", P[f"NC_{f}{s}1"])
            line = (knuckle - wr).normalized()
            pts = [P[f"NC_{f}{s}1"], P[f"NC_{f}{s}2"], P[f"NC_{f}{s}3"], P[f"_{f}{s}Tip"]]
            for k in (1, 2, 3):
                b = f"NC_{f}{s}{k}"
                a = posed(PARENT[b], pts[k - 1])
                e = posed(b, pts[k])
                rot_world(b, (e - a).normalized().rotation_difference(line).to_matrix())
        # legs straight down under the hips (front view), keeping their natural forward/back line
        hip, ank = P[side + "UpperLeg"], P[side + "Foot"]
        v = ank - hip
        v.y = 0
        report[side + "LegStraighten"] = round(math.degrees(v.angle(Vector((0, 0, -1)))), 1)
        rot_world(side + "UpperLeg", v.normalized().rotation_difference(Vector((0, 0, -1))).to_matrix())
        # feet flat again
        an = posed(side + "LowerLeg", P[side + "Foot"])
        toe = posed(side + "Foot", P["NC_Toes" + s])
        d = toe - an
        flat = Vector((0, d.y, d.z + (an.z - P[side + "Foot"].z)))
        rot_world(side + "Foot", d.normalized().rotation_difference(flat.normalized()).to_matrix())

    # new joint positions: each joint rides on the bone that carries it
    carrier = {b: PARENT[b] for b in PARENT}
    carrier.update({"LowerTorso": "LowerTorso", "HumanoidRootNode": "LowerTorso", "_Head": "Head", "_HeadTop": "Head"})
    for side, s, m, bx in SIDES:
        carrier["_ToeTip" + s] = "NC_Toes" + s
        carrier["_Heel" + s] = side + "Foot"
        for f in FINGERS:
            carrier[f"_{f}{s}Tip"] = f"NC_{f}{s}3"
    Q = {}
    for k, p in P.items():
        b = carrier.get(k, "LowerTorso")
        if b in ("Root", "HumanoidRootNode"):
            b = "LowerTorso"
        Q[k] = posed(b, p)
    bpy.ops.object.mode_set(mode="OBJECT")
    for ob in objs:
        activate(ob)
        for md in list(ob.modifiers):
            if md.type == "ARMATURE":
                bpy.ops.object.modifier_apply(modifier=md.name)
            else:
                bpy.ops.object.modifier_apply(modifier=md.name)
        ob.parent = None
    bpy.data.objects.remove(warm, do_unlink=True)
    return Q, report


# ------------------------------------------------------------------------------------------------ 4. base layer for good
def bake_base_layer(body, garments):
    """delete skin the garments fully cover (one vertex ring of overlap kept at every hem), join them in."""
    kd = KDTree(sum(len(g.data.vertices) for g in garments))
    n = 0
    for g in garments:
        for v in g.data.vertices:
            kd.insert(v.co, n)
            n += 1
    kd.balance()
    me = body.data
    bm = bmesh.new()
    bm.from_mesh(me)
    bm.verts.ensure_lookup_table()
    cov = np.array([kd.find(v.co)[2] < 0.07 for v in bm.verts])
    deep = cov.copy()
    for v in bm.verts:                      # erode: keep a ring of skin under every hem
        if cov[v.index] and not all(cov[e.other_vert(v).index] for e in v.link_edges):
            deep[v.index] = False
    deep2 = deep.copy()
    for v in bm.verts:
        if deep[v.index] and not all(deep[e.other_vert(v).index] for e in v.link_edges):
            deep2[v.index] = False
    drop = [f for f in bm.faces if all(deep2[v.index] for v in f.verts)]
    removed = len(drop)
    bmesh.ops.delete(bm, geom=drop, context="FACES_ONLY")
    loose = [v for v in bm.verts if not v.link_faces]
    bmesh.ops.delete(bm, geom=loose, context="VERTS")
    bm.to_mesh(me)
    bm.free()
    for g in garments:
        g.data.materials.clear()
    activate(body)
    for g in garments:  # the tank keeps its UVs and ribbed-knit material from nc_baselayer
        mname = "NC_BaseLayer_TankTop" if "TankTop" in g.name else "NC_BaseLayer_Shorts"
        g.data.materials.append(material(mname))
        for p in g.data.polygons:
            p.use_smooth = True
        g.select_set(True)
    bpy.context.view_layer.objects.active = body
    bpy.ops.object.join()
    activate(body)
    bpy.ops.object.vertex_group_limit_total(group_select_mode="ALL", limit=4)
    bpy.ops.object.vertex_group_normalize_all(group_select_mode="ALL", lock_active=False)
    bpy.ops.object.vertex_group_clean(group_select_mode="ALL", limit=0.01)
    bpy.ops.object.vertex_group_normalize_all(group_select_mode="ALL", lock_active=False)
    return removed


# ------------------------------------------------------------------------------------------------ 4b. face bones
def face_marks(name, eyes):
    """{bone: (head position, reach)} for this body, or {} without heads.json"""
    gender = name.split("_")[0]
    if not FACE or gender not in FACE or not ("l" in eyes and "r" in eyes):
        return {}
    d = FACE[gender]
    A = (eyes["l"][0] + eyes["r"][0]) / 2
    k = (eyes["l"][0] - eyes["r"][0]).length / d["eyeSpan"]
    out = {}
    for b, x in d["bones"].items():
        r = x["at"]                                    # Roblox axes from the eyes' midpoint -> Blender
        out[b] = (A + Vector((-r[0], r[2], r[1])) * k, x["reach"] * k)
    return out


def face_weights(body, FB):
    """each face bone takes a smooth share of the Head's weight around it (at most two face bones per vertex)"""
    for b in FB:
        body.vertex_groups.new(name=b)
    names = {g.index: g.name for g in body.vertex_groups}
    gi = {g.name: g.index for g in body.vertex_groups}
    head = body.vertex_groups["Head"]
    moved = 0
    for v in body.data.vertices:
        w = {names[ge.group]: ge.weight for ge in v.groups}
        hw = w.get("Head", 0.0)
        if hw < 0.05:
            continue
        cand = []
        for b, (p, r) in FB.items():
            d = (v.co - p).length
            if d < r:
                cand.append(((1 - (d / r) ** 2) ** 2, b))
        if not cand:
            continue
        cand.sort(reverse=True)
        cand = cand[:2]
        tot = sum(c for c, _ in cand)
        share = min(0.95, tot) * hw
        for c, b in cand:
            body.vertex_groups[gi[b]].add([v.index], share * c / tot, "REPLACE")
        head.add([v.index], hw - share, "REPLACE")
        moved += 1
    activate(body)
    bpy.ops.object.vertex_group_limit_total(group_select_mode="ALL", limit=4)
    bpy.ops.object.vertex_group_normalize_all(group_select_mode="ALL", lock_active=False)
    return moved


def add_face_bones(rig, FB):
    """the export rig's face bones: straight up and rolled half round like every other bone (Roblox axes)"""
    activate(rig)
    bpy.ops.object.mode_set(mode="EDIT")
    eb = rig.data.edit_bones
    for b, (p, r) in FB.items():
        e = eb.new(b)
        e.head = p
        e.tail = p + Vector((0, 0, 0.08))
        e.roll = math.pi
        e.parent = eb["Head"]
        e.use_connect = False
        e.use_deform = True
    bpy.ops.object.mode_set(mode="OBJECT")


# ------------------------------------------------------------------------------------------------ 5. 15 R15 pieces
def split(body, rig, prefix):
    bm_full = bmesh.new()
    bm_full.from_mesh(body.data)
    loose = [v for v in bm_full.verts if not v.link_faces]      # (stray points would bloat every part's bounds)
    bmesh.ops.delete(bm_full, geom=loose, context="VERTS")
    bm_full.normal_update()
    full_normals = [v.normal.copy() for v in bm_full.verts]
    kd = KDTree(len(bm_full.verts))
    for v in bm_full.verts:
        kd.insert(v.co, v.index)
    kd.balance()
    gname = {g.index: g.name for g in body.vertex_groups}
    dl = bm_full.verts.layers.deform.active
    face_part = {}
    for f in bm_full.faces:
        score = {}
        for v in f.verts:
            for gi, w in v[dl].items():
                p = PART_OF_BONE.get(gname.get(gi))
                if p:
                    score[p] = score.get(p, 0) + w
        face_part[f.index] = max(score, key=score.get) if score else "UpperTorso"
    # the mesh's own openings (eyes) stay open: only the cuts between pieces get capped
    def ekey(e):
        a, b = (tuple(round(c, 5) for c in v.co) for v in e.verts)
        return (a, b) if a < b else (b, a)
    own_open = {ekey(e) for e in bm_full.edges if e.is_boundary}
    bm_full.faces.ensure_lookup_table()
    for _it in range(4):
        newp = dict(face_part)
        for f in bm_full.faces:
            nb = [face_part[o.index] for e in f.edges for o in e.link_faces if o is not f]
            if nb:
                best = max(set(nb), key=nb.count)
                if best != face_part[f.index] and nb.count(best) * 2 > len(nb):
                    newp[f.index] = best
        face_part = newp
    # clean edges where they matter for colouring by part: the whole tank top is UpperTorso and the whole shorts
    # LowerTorso (their hems are the lines between torso, arms and thighs), and the neck goes with the Head
    mat_names = [m.name if m else "" for m in body.data.materials]
    neck_z = rig.data.bones["Head"].head_local.z
    for f in bm_full.faces:
        mn = mat_names[f.material_index] if f.material_index < len(mat_names) else ""
        if "TankTop" in mn:
            face_part[f.index] = "UpperTorso"
        elif "Shorts" in mn:
            face_part[f.index] = "LowerTorso"
        elif face_part[f.index] == "UpperTorso":
            c = f.calc_center_median()
            if c.z > neck_z - 0.15 and abs(c.x) < 0.22:
                face_part[f.index] = "Head"
    # skin between limb parts: straight cuts across the limb at each joint (shoulder side, elbow, wrist, knee,
    # ankle), so a sleeve or trouser leg coloured by part ends in a clean line
    J = {b.name: b.head_local.copy() for b in rig.data.bones}
    for side, s, m, bx in SIDES:
        for chain in (("UpperArm", "LowerArm", "Hand"), ("UpperLeg", "LowerLeg", "Foot")):
            names = [side + c for c in chain]
            a, b_, c_ = (J[n] for n in names)
            d1 = (b_ - a).normalized()
            d2 = (c_ - b_).normalized()
            arm = chain[0] == "UpperArm"
            for f in bm_full.faces:
                cur = face_part[f.index]
                mn = mat_names[f.material_index] if f.material_index < len(mat_names) else ""
                if "BaseLayer" in mn:
                    continue
                cen = f.calc_center_median()
                if cur in names:
                    if (cen - b_).dot(d1) < 0:
                        new = names[0]
                    elif (cen - c_).dot(d2) < 0:
                        new = names[1]
                    else:
                        new = names[2]
                    face_part[f.index] = new
                cur = face_part[f.index]
                # the shoulder: a sleeve seam, a plane through the shoulder joint tilted 45 degrees (over the top of
                # the shoulder, down through the armpit)
                if arm and cur in ("UpperTorso", names[0]) and cen.x * bx > 0 and cen.z > a.z - 0.6:
                    seam = Vector((bx * 0.7071, 0, -0.7071))
                    face_part[f.index] = names[0] if (cen - a).dot(seam) > 0 else "UpperTorso"
    pieces = {}
    for part in R15_PARTS:
        bm = bm_full.copy()
        bm.faces.ensure_lookup_table()
        bmesh.ops.delete(bm, geom=[f for f in bm.faces if face_part[f.index] != part], context="FACES")
        bnd = [e for e in bm.edges if e.is_boundary and ekey(e) not in own_open]
        if bnd:
            res = bmesh.ops.holes_fill(bm, edges=bnd, sides=0)
            pk = bmesh.ops.poke(bm, faces=res["faces"], center_mode="MEAN")
            dlp = bm.verts.layers.deform.active
            for cv in pk["verts"]:
                nb = [e.other_vert(cv) for e in cv.link_edges if e.other_vert(cv) not in pk["verts"]]
                acc = {}
                for v in nb:
                    for gi, w in v[dlp].items():
                        acc[gi] = acc.get(gi, 0.0) + w / max(1, len(nb))
                top = sorted(acc.items(), key=lambda kv: -kv[1])[:4]
                tot = sum(w for _g, w in top) or 1.0
                cv[dlp].clear()
                for gi, w in top:
                    cv[dlp][gi] = w / tot
        bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context="VERTS")   # no stray points
        m = bpy.data.meshes.new(prefix + part + "_Geo")
        bm.to_mesh(m)
        bm.free()
        ob = link(bpy.data.objects.new(prefix + part + "_Geo", m))
        for gi in sorted(gname):
            ob.vertex_groups.new(name=gname[gi])
        for mt in body.data.materials:
            m.materials.append(mt)
        for poly in m.polygons:
            poly.use_smooth = True
        ns = [full_normals[kd.find(v.co)[1]] for v in m.vertices]
        try:
            m.normals_split_custom_set_from_vertices(ns)
        except Exception:
            pass
        ob.parent = rig
        mod = ob.modifiers.new("Armature", "ARMATURE")
        mod.object = rig
        ob["NC_Body"] = prefix.rstrip("_")
        pieces[part] = ob
    bm_full.free()
    bpy.data.objects.remove(body, do_unlink=True)
    return pieces


# ------------------------------------------------------------------------------------------------ 5b. one texture a part
TEX_DIR = os.path.join(OUT, "textures")


def _emit_material(name, colour=None, image=None, uv=None):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    em = nt.nodes.new("ShaderNodeEmission")
    nt.links.new(em.outputs[0], out.inputs["Surface"])
    if image is not None:
        tx = nt.nodes.new("ShaderNodeTexImage")
        tx.image = image
        tx.interpolation = "Cubic"
        uvn = nt.nodes.new("ShaderNodeUVMap")
        uvn.uv_map = uv
        nt.links.new(uvn.outputs[0], tx.inputs["Vector"])
        nt.links.new(tx.outputs["Color"], em.inputs["Color"])
    else:
        em.inputs["Color"].default_value = colour
    return m


def _rib_image_of(mat):
    if mat and mat.use_nodes:
        for n in mat.node_tree.nodes:
            if n.type == "TEX_IMAGE" and n.image and "Rib_Color" in n.image.name:
                return n.image
    return None


def texture_pieces(pieces, name):
    """Roblox gives each MeshPart one texture, so every part gets its own: skin-only parts get none (just the Skin
    material, so NCLookBuilder tints them); a part the tank top or shorts reach gets a colour map baked on a fresh
    UV: rib knit on the tank, the shorts' colour on the shorts, and alpha 0 on skin, so the part's own colour (the
    skin tone) shows through there (Overlay)."""
    os.makedirs(TEX_DIR, exist_ok=True)
    scene.render.engine = "CYCLES"
    scene.cycles.samples = 1
    scene.cycles.device = "CPU"
    scene.render.bake.margin = 4
    skin = material("Skin")
    made = {}
    for part, ob in pieces.items():
        me = ob.data
        used = {p.material_index for p in me.polygons}
        mats = list(me.materials)
        clothes = [i for i in used if mats[i] and mats[i].name.startswith("NC_BaseLayer")]
        rib_uv = me.uv_layers.get("UVMap")
        if not clothes:
            for uvl in list(me.uv_layers):
                me.uv_layers.remove(uvl)
            me.materials.clear()
            me.materials.append(skin)
            for p in me.polygons:
                p.material_index = 0
            continue
        mat_idx = np.empty(len(me.polygons), np.int32)
        me.polygons.foreach_get("material_index", mat_idx)        # (clearing the slots resets these)
        res = 1024 if part in ("UpperTorso", "LowerTorso") else 512
        # a fresh UV just for this part's texture
        bake_uv = me.uv_layers.new(name="NC_Bake")
        me.uv_layers.active = bake_uv
        activate(ob)
        bpy.ops.object.mode_set(mode="EDIT")
        bpy.ops.mesh.select_all(action="SELECT")
        bpy.ops.uv.smart_project(angle_limit=math.radians(60), island_margin=0.004, scale_to_bounds=True)
        bpy.ops.object.mode_set(mode="OBJECT")
        me.uv_layers["NC_Bake"].active_render = True              # (edit mode reallocates the layers: by name)
        me.uv_layers.active = me.uv_layers["NC_Bake"]             # (the bake writes through the active UV)
        rib_uv = me.uv_layers.get("UVMap")
        target = bpy.data.images.new(f"NC_{name}_{part}_Base", res, res, alpha=True)
        planes = {}
        for pass_name in ("colour", "alpha"):
            tmp = []
            for i, mt in enumerate(mats):
                rib = _rib_image_of(mt)
                is_cloth = mt is not None and mt.name.startswith("NC_BaseLayer")
                if pass_name == "alpha":
                    tm = _emit_material("_bk", (1, 1, 1, 1) if is_cloth else (0, 0, 0, 1))
                elif rib is not None and rib_uv is not None:
                    tm = _emit_material("_bk", image=rib, uv=rib_uv.name)
                else:
                    tm = _emit_material("_bk", tuple(mt.diffuse_color) if (mt and is_cloth) else (0, 0, 0, 1))
                tn = tm.node_tree.nodes.new("ShaderNodeTexImage")       # the bake target (active node)
                tn.image = target
                tm.node_tree.nodes.active = tn
                tmp.append(tm)
            me.materials.clear()
            for tm in tmp:
                me.materials.append(tm)
            me.polygons.foreach_set("material_index", mat_idx)
            activate(ob)
            me.update()
            bpy.context.view_layer.update()
            bpy.ops.object.bake(type="EMIT", margin=4, use_clear=True)
            px = np.empty(res * res * 4, np.float32)
            target.pixels.foreach_get(px)
            planes[pass_name] = px.reshape(res, res, 4)
            me.materials.clear()
            for mt in mats:
                me.materials.append(mt)
            me.polygons.foreach_set("material_index", mat_idx)
            for tm in tmp:
                bpy.data.materials.remove(tm)
        rgba = planes["colour"].copy()
        rgba[..., 3] = planes["alpha"][..., 0]
        target.pixels.foreach_set(rgba.ravel())
        path = os.path.join(TEX_DIR, target.name + ".png")
        target.filepath_raw = path
        target.file_format = "PNG"
        target.save()
        # the part's one material: that map on that UV (the only UV left), skin colour underneath
        if rib_uv is not None:
            me.uv_layers.remove(me.uv_layers["UVMap"])
        fm = bpy.data.materials.new(f"NC_{name}_{part}_Base")
        fm.use_nodes = True
        bsdf = fm.node_tree.nodes.get("Principled BSDF")
        tx = fm.node_tree.nodes.new("ShaderNodeTexImage")
        tx.image = target
        fm.node_tree.links.new(tx.outputs["Color"], bsdf.inputs["Base Color"])
        fm.node_tree.links.new(tx.outputs["Alpha"], bsdf.inputs["Alpha"])
        fm.diffuse_color = COLOURS["Skin"]
        me.materials.clear()
        me.materials.append(fm)
        for p in me.polygons:
            p.material_index = 0
        made[part] = res
    return made


# ------------------------------------------------------------------------------------------------ Roblox numbers
def rbx(p):
    """Blender (studs) -> Roblox: the body faces -Y in Blender and -Z in Roblox; its right side is Blender -X"""
    return (-p.x, p.z, p.y)


def roblox_data(Q, pieces, eyes):
    allv = [v.co for ob in pieces.values() for v in ob.data.vertices]
    zs = [v.z for v in allv]
    height = max(zs) - min(zs)
    hrp_y = Q["HumanoidRootNode"].z
    head = pieces["Head"]
    hv = [v.co for v in head.data.vertices]
    eye_z = sum(e[0].z for e in eyes.values()) / max(1, len(eyes)) if eyes else Q["_Head"].z + 0.15
    band = [v for v in hv if abs(v.z - eye_z) < 0.12]
    front_y = min(v.y for v in band)
    back_y = max(v.y for v in band)
    half_w = max(abs(v.x) for v in band)
    centre = Vector((0, (front_y + back_y) / 2, eye_z))
    ut = [v.co for v in pieces["UpperTorso"].data.vertices]
    chest_z = Q["Head"].z - 0.62 * (Q["Head"].z - Q["UpperTorso"].z)
    chest = [v for v in ut if abs(v.z - chest_z) < 0.1 and abs(v.x) < 0.25]
    lt = [v.co for v in pieces["LowerTorso"].data.vertices]
    waist_z = Q["LowerTorso"].z + 0.05
    waist = [v for v in lt if abs(v.z - waist_z) < 0.1 and abs(v.x) < 0.25]
    A = {
        ("Head", "HatAttachment"): Vector((0, centre.y, max(v.z for v in hv) + 0.02)),
        ("Head", "HairAttachment"): Vector((0, centre.y, max(v.z for v in hv) - 0.02)),
        ("Head", "FaceCenterAttachment"): centre,
        ("Head", "FaceFrontAttachment"): Vector((0, front_y, eye_z)),
        ("UpperTorso", "NeckAttachment"): Q["Head"],
        ("UpperTorso", "BodyFrontAttachment"): Vector((0, min(v.y for v in chest), chest_z)),
        ("UpperTorso", "BodyBackAttachment"): Vector((0, max(v.y for v in chest), chest_z)),
        ("LowerTorso", "WaistCenterAttachment"): Vector((0, Q["LowerTorso"].y, waist_z)),
        ("LowerTorso", "WaistFrontAttachment"): Vector((0, min(v.y for v in waist), waist_z)),
        ("LowerTorso", "WaistBackAttachment"): Vector((0, max(v.y for v in waist), waist_z)),
    }
    for side, s, m, bx in SIDES:
        sh = Q[side + "UpperArm"]
        A[("UpperTorso", side + "CollarAttachment")] = Q["NC_Clavicle" + s].lerp(sh, 0.6)
        A[(side + "UpperArm", side + "ShoulderAttachment")] = sh + Vector((0, 0, 0.18))
        # grip: in the middle of the closed hand, a little past the knuckles
        A[(side + "Hand", side + "GripAttachment")] = Q[side + "Hand"].lerp(Q[f"NC_Middle{s}1"], 0.85)
        A[(side + "Foot", side + "FootAttachment")] = Vector((Q[side + "Foot"].x, Q[side + "Foot"].y - 0.3, 0))
        if m in eyes:
            A[("Head", "NC_" + side + "EyeAttachment")] = eyes[m][0]
    o = Vector((Q["HumanoidRootNode"].x, Q["HumanoidRootNode"].y, 0))   # measured from the ground under the root part
    return {
        "height": round(height, 3), "hrpY": round(hrp_y, 3), "hipHeight": round(hrp_y - 1.0, 3),
        "eyeRadius": round(sum(e[1] for e in eyes.values()) / max(1, len(eyes)), 3) if eyes else 0.11,
        "headRadius": round((centre.y - front_y), 3), "headHalfWidth": round(half_w, 3),
        "attachments": [(part, name, [round(c, 3) for c in rbx(p - o)]) for (part, name), p in A.items()],
        "joints": {b: [round(c, 3) for c in rbx(Q[b] - o)] for b in PARENT},
    }


# ------------------------------------------------------------------------------------------------ run every body
RESULTS = {}
RIGS = {}
x_off = 0.0
for src in SOURCES:
    name = src.name                                   # e.g. Male_Average
    body, garments, JM, eyes = take_body(src)
    P = joints_from(JM)
    warm, missing = skin(body, garments, P)
    Q, rep = repose(warm, [body] + garments, P)
    removed = bake_base_layer(body, garments)
    rig = make_armature("NC_" + name, Q)
    rig["NC_Body"] = name
    FB = face_marks(name, eyes)
    if FB:
        add_face_bones(rig, FB)
        face_moved = face_weights(body, FB)
    body.parent = rig
    # keep one whole, weighted copy (not exported): garment tools copy its weights onto new clothes
    whole = body.copy()
    whole.data = body.data.copy()
    whole.name = whole.data.name = name + "_Whole"
    link(whole)
    whole.parent = rig
    wm = whole.modifiers.new("Armature", "ARMATURE")
    wm.object = rig
    whole.hide_render = True
    whole.hide_set(True)
    pieces = split(body, rig, name + "_")
    textured = texture_pieces(pieces, name)
    data = roblox_data(Q, pieces, eyes)
    data["tris"] = {p: tri_count(o) for p, o in pieces.items()}
    data["tris_total"] = sum(data["tris"].values())
    data["heat_missing"] = missing
    data["repose"] = rep
    data["covered_skin_faces_removed"] = removed
    data["face_bones"] = {b: [round(c, 4) for c in rbx(p - Q["Head"])] for b, (p, r) in FB.items()}
    data["face_vertices"] = face_moved if FB else 0
    data["textured_parts"] = sorted(textured)
    RESULTS[name] = data
    # export this body on its own
    bpy.ops.object.select_all(action="DESELECT")
    rig.select_set(True)
    for ob in pieces.values():
        ob.name = ob.name[len(name) + 1:] if ob.name.startswith(name + "_") else ob.name   # FBX wants <Part>_Geo
        ob.select_set(True)
    bpy.context.view_layer.objects.active = rig
    bpy.ops.export_scene.fbx(filepath=os.path.join(OUT, f"NC_Body_{name}.fbx"), use_selection=True,
                             object_types={"ARMATURE", "MESH"}, apply_scale_options="FBX_SCALE_UNITS",
                             add_leaf_bones=False, bake_anim=False, use_custom_props=True, primary_bone_axis="Y",
                             secondary_bone_axis="X", mesh_smooth_type="OFF", path_mode="COPY",
                             embed_textures=True)  # the tank rib texture travels inside the FBX
    for part, ob in pieces.items():                  # names back to unique ones for the next body
        ob.name = f"{name}_{part}_Geo"
    RIGS[name] = (rig, pieces)
    print("NC_MHRIG", name, json.dumps({k: data[k] for k in ("height", "hipHeight", "tris_total", "heat_missing", "repose")}))
    for ch in list(src.children):
        bpy.data.objects.remove(ch, do_unlink=True)
    bpy.data.objects.remove(src, do_unlink=True)

# lay them out in a line for the .blend and previews
order = [n for g in ("Male", "Female") for b in ("Skinny", "Average", "Athletic", "Muscular", "Heavy") if (n := f"{g}_{b}") in RIGS]
x = 0.0
for n in order:
    RIGS[n][0].location.x = x
    x += 3.0
    if n == "Male_Heavy":
        x += 2.0


# ------------------------------------------------------------------------------------------------ Lua out
def lua_v3(c):
    return f"Vector3.new({c[0]:.3f}, {c[1]:.3f}, {c[2]:.3f})"


lines = ["-- NCBodyData (ModuleScript, ReplicatedStorage): generated by build_makehuman_rig.py. Do not hand-edit; re-run it.",
         "-- The rigged MakeHuman bodies (NC_Body_<Gender>_<Build>.fbx): sizes and attachment points in studs, measured",
         "-- from the ground under the root part in the rest pose (Roblox axes: X right, Y up, -Z forward).",
         "local D = {}", "D.BUILDS = { \"Skinny\", \"Average\", \"Athletic\", \"Muscular\", \"Heavy\" }",
         "D.GENDERS = { \"Male\", \"Female\" }",
         "-- fitness builds (NCFitnessConfig.Build) that have no body of their own use the closest one",
         "D.BUILD_ALIAS = { Bulky = \"Muscular\" }", "D.DEFAULT = \"Male_Average\"", "D.bodies = {"]
for n in order:
    d = RESULTS[n]
    lines.append(f"\t{n} = {{")
    lines.append(f"\t\theight = {d['height']}, hrpY = {d['hrpY']}, hipHeight = {d['hipHeight']}, eyeRadius = {d['eyeRadius']},")
    lines.append("\t\tattachments = {")
    for part, an, c in d["attachments"]:
        lines.append(f"\t\t\t{{ \"{part}\", \"{an}\", {lua_v3(c)} }},")
    lines.append("\t\t},")
    lines.append("\t},")
lines += ["}", "", "-- the body id for a gender and a fitness build", "function D.id(gender, build)",
          "\tgender = (gender == \"Female\") and \"Female\" or \"Male\"", "\tbuild = D.BUILD_ALIAS[build] or build",
          "\tlocal id = gender .. \"_\" .. tostring(build)", "\treturn D.bodies[id] and id or (gender .. \"_Average\")", "end",
          "return D", ""]
with open(os.path.join(OUT, "NCBodyData.lua"), "w", encoding="utf-8") as f:
    f.write("\n".join(lines))

assemble = """-- AssembleMakeHumanBodies (generated by build_makehuman_rig.py): run once in Studio's command bar.
-- 1. Import each NC_Body_<Gender>_<Build>.fbx with the 3D Importer (Rig type: R15, keep the default scale).
-- 2. Make sure NCBodyData is in ReplicatedStorage.
-- 3. Select ALL the imported body models, paste this into the command bar, press Enter.
-- Each body gets: Humanoid settings, the root part, the attachments tools, hats and Character Studio use, the
-- NC_Body tags, and is filed as ServerStorage.NC_Bodies.<Gender>_<Build>. NCBodyService swaps players into the
-- right one. The default body (Male_Average) is also copied to StarterPlayer.StarterCharacter.
local RS = game:GetService("ReplicatedStorage")
local SS = game:GetService("ServerStorage")
local D = require(RS:WaitForChild("NCBodyData"))
local folder = SS:FindFirstChild("NC_Bodies") or Instance.new("Folder")
folder.Name = "NC_Bodies"
folder.Parent = SS
local need = { "HumanoidRootPart", "LowerTorso", "UpperTorso", "Head", "LeftUpperArm", "LeftLowerArm", "LeftHand",
\t"RightUpperArm", "RightLowerArm", "RightHand", "LeftUpperLeg", "LeftLowerLeg", "LeftFoot", "RightUpperLeg", "RightLowerLeg", "RightFoot" }
local done = 0
for _, model in game:GetService("Selection"):Get() do
\tif not model:IsA("Model") then
\t\tcontinue
\tend
\tlocal id
\tfor key in D.bodies do
\t\tif string.find(model.Name, key, 1, true) then
\t\t\tid = key
\t\tend
\tend
\tif not id then
\t\twarn("AssembleMakeHumanBodies: can't tell which body " .. model.Name .. " is (keep NC_Body_<Gender>_<Build> in its name)")
\t\tcontinue
\tend
\tlocal B = D.bodies[id]
\tfor _, n in need do
\t\tif not model:FindFirstChild(n, true) then
\t\t\twarn(id .. ": missing " .. n .. " (import with Rig type R15)")
\t\tend
\tend
\tlocal hrp = model:FindFirstChild("HumanoidRootPart")
\tif not hrp then
\t\twarn(id .. ": no HumanoidRootPart, skipped")
\t\tcontinue
\tend
\thrp.Size, hrp.Transparency, hrp.CanCollide = Vector3.new(2, 2, 1), 1, true
\tmodel.PrimaryPart = hrp
\tlocal hum = model:FindFirstChildOfClass("Humanoid") or Instance.new("Humanoid")
\thum.Parent = model
\thum.RigType = Enum.HumanoidRigType.R15
\tpcall(function() hum.AutomaticScalingEnabled = false end)
\t-- the floor is the lowest point of the body's meshes (the importer doesn't put the root part exactly on the
\t-- rig's root bone, so nothing is measured from it vertically)
\tlocal floorY = math.huge
\tfor _, d in model:GetDescendants() do
\t\tif d:IsA("MeshPart") and d ~= hrp then
\t\t\tlocal h = d.Size / 2
\t\t\tfor _, sx in { -1, 1 } do
\t\t\t\tfor _, sy in { -1, 1 } do
\t\t\t\t\tfor _, sz in { -1, 1 } do
\t\t\t\t\t\tfloorY = math.min(floorY, (d.CFrame * Vector3.new(sx * h.X, sy * h.Y, sz * h.Z)).Y)
\t\t\t\t\tend
\t\t\t\tend
\t\t\tend
\t\tend
\tend
\thum.HipHeight = math.max(0.5, hrp.Position.Y - hrp.Size.Y / 2 - floorY)
\tlocal origin = CFrame.new(hrp.Position.X, floorY, hrp.Position.Z) * hrp.CFrame.Rotation
\tfor _, a in B.attachments do
\t\tlocal part = model:FindFirstChild(a[1])
\t\tif part then
\t\t\tlocal at = part:FindFirstChild(a[2]) or Instance.new("Attachment")
\t\t\tat.Name = a[2]
\t\t\tat.Parent = part
\t\t\tat.WorldCFrame = origin * CFrame.new(a[3])
\t\tend
\tend
\tfor _, d in model:GetDescendants() do
\t\tif d:IsA("MeshPart") then
\t\t\t-- one texture a part: the torso parts carry the tank top / shorts map (skin see-through, so the part's
\t\t\t-- colour shows there); every other part is plain skin and must not keep any texture
\t\t\tlocal sa = d:FindFirstChildOfClass("SurfaceAppearance")
\t\t\tif d.Name == "UpperTorso" or d.Name == "LowerTorso" then
\t\t\t\tif sa or d.TextureID ~= "" then
\t\t\t\t\td:SetAttribute("NC_BaseLayer", true)
\t\t\t\t\tif d.TextureID ~= "" then
\t\t\t\t\t\td:SetAttribute("NC_TextureID", d.TextureID)
\t\t\t\t\tend
\t\t\t\t\tif sa then
\t\t\t\t\t\tpcall(function() sa.AlphaMode = Enum.AlphaMode.Overlay end)
\t\t\t\t\tend
\t\t\t\telse
\t\t\t\t\twarn(id .. ": " .. d.Name .. " came in without its base-layer texture (import with textures on)")
\t\t\t\tend
\t\t\telse
\t\t\t\tif sa then
\t\t\t\t\tsa:Destroy()
\t\t\t\tend
\t\t\t\td.TextureID = ""
\t\t\tend
\t\t\td.CanCollide = d.Name == "UpperTorso" or d.Name == "LowerTorso" or d.Name == "Head"
\t\t\tpcall(function() d.CollisionFidelity = Enum.CollisionFidelity.Box end)
\t\t\td.Anchored = false
\t\t\td.Massless = false
\t\tend
\tend
\thrp.Anchored = false
\tmodel:SetAttribute("NC_Body", "Human")
\tmodel:SetAttribute("NC_BodyId", id)
\tmodel.Name = id
\tlocal old = folder:FindFirstChild(id)
\tif old and old ~= model then
\t\told:Destroy()
\tend
\tmodel.Parent = folder
\tif id == D.DEFAULT then
\t\tlocal sp = game:GetService("StarterPlayer")
\t\tlocal prev = sp:FindFirstChild("StarterCharacter")
\t\tif prev then
\t\t\tprev:Destroy()
\t\tend
\t\tlocal c = model:Clone()
\t\tc.Name = "StarterCharacter"
\t\tc.Parent = sp
\tend
\tdone += 1
end
print("AssembleMakeHumanBodies: " .. done .. " bodies ready in ServerStorage.NC_Bodies")
"""
with open(os.path.join(OUT, "AssembleMakeHumanBodies.lua"), "w", encoding="utf-8") as f:
    f.write(assemble)
with open(os.path.join(OUT, "makehuman_rig.json"), "w") as f:
    json.dump(RESULTS, f, indent=1)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "NeonCoast_MakeHumanRig.blend"))
print("NC_MHRIG_DONE", len(RESULTS))
