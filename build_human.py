# Neon Coast human body: a realistic, skinned adult with real joints, built in Blender for Roblox.
#   blender --background --factory-startup --python build_human.py        (NC_HUMAN_RENDER=0 skips the previews)
# The body: 6.6 studs tall (a 1.75 m adult at this world's ~3.77 studs per metre), anatomical proportions, modelled
# as a smooth skin over a skeleton (pelvis, waist, ribcage, chest, neck, shoulders, upper arms, forearms, palms and
# five fingers each, thighs, knees, calves, ankles, heels, arches, toes) plus a sculpted head.
# The rig: the 15 standard Roblox R15 joints (so Humanoid, tools, seats and ragdolls all keep working) and 38 more
# real joints as extra bones: a mid-spine, an upper neck, both collarbones, forearm twist, three bones in every
# finger and thumb, and the toes. Collarbones lift and swing the shoulder joint itself (the arm rises with it).
# Out: NeonCoastHuman.fbx (+ .glb): 15 meshes named <Part>_Geo, skinned (4 influences max), an armature
#      Root > HumanoidRootNode > LowerTorso ...; NeonCoast_Human.blend; NCAnimationsHuman.lua (all 18 moves redone
#      for this body and its extra joints); AssembleHumanBody.lua (Studio command-bar setup after import);
#      human.json (stats); previews/Human_*.png and previews/Human_Animations.mp4.
import bpy, bmesh, math, json, os, sys, shutil
from mathutils import Vector, Matrix, Euler
from mathutils.kdtree import KDTree

OUT = r"C:\Users\Crisa\Documents\NeonCoast_Blender"
PREV = os.path.join(OUT, "previews")
sys.path.insert(0, OUT)
import importlib, nc_anim as NA
importlib.reload(NA)
FPS = 30
D2R = math.pi / 180

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.render.fps = FPS


def rb(v):
    """Roblox (x, y, z) -> Blender: the body faces -Y in Blender (which the importer turns to face -Z in Roblox),
    so its right side is Blender -X: Blender = (-x, z, y)"""
    return Vector((-v[0], v[2], v[1]))


def V(*a):
    return Vector(a)


# ------------------------------------------------------------------------------------------------ proportions
H = 6.6
ABD = 7 * D2R                              # arms hang 7 degrees out from the body in the rest pose
HRP_Y = 3.7
J = {  # joint centres, Roblox coordinates (X right, Y up, Z back), ground at y = 0
    "HumanoidRootNode": V(0, HRP_Y, 0), "LowerTorso": V(0, 3.55, 0.02), "UpperTorso": V(0, 4.30, 0.05),
    "Head": V(0, 5.62, 0.06),
    "NC_SpineMid": V(0, 4.72, 0.06), "NC_NeckMid": V(0, 5.84, 0.05),
}
SIDES = (("Right", "R", 1), ("Left", "L", -1))
for side, s, sx in SIDES:
    arm_dir = V(sx * math.sin(ABD), -math.cos(ABD), 0)
    lat = V(sx * math.cos(ABD), sx * math.sin(ABD), 0)     # out from the body, square to the arm
    sh = V(sx * 0.86, 5.33, 0.03)
    el = sh + arm_dir * 1.21
    wr = el + arm_dir * 0.96
    J[side + "UpperArm"], J[side + "LowerArm"], J[side + "Hand"] = sh, el, wr
    J["NC_Clavicle" + s] = V(sx * 0.15, 5.47, -0.08)
    J["NC_Twist" + s] = el + (wr - el) * 0.55
    J[side + "UpperLeg"], J[side + "LowerLeg"], J[side + "Foot"] = V(sx * 0.36, 3.45, 0.0), V(sx * 0.37, 1.88, -0.02), V(sx * 0.37, 0.28, 0.05)
    J["NC_Toes" + s] = V(sx * 0.37, 0.08, -0.48)

    def hand(u, v, w, _wr=wr, _a=arm_dir, _l=lat):
        return _wr + _a * u + V(0, 0, v) + _l * w
    FING = {"Index": (-0.12, (0.14, 0.09, 0.07)), "Middle": (-0.04, (0.15, 0.10, 0.07)),
            "Ring": (0.04, (0.14, 0.09, 0.07)), "Pinky": (0.115, (0.11, 0.07, 0.06))}
    for f, (vv, ls) in FING.items():
        u = 0.42
        for k in range(3):
            J[f"NC_{f}{s}{k + 1}"] = hand(u, vv, 0.0)
            u += ls[k]
        J[f"NC_{f}{s}Tip"] = hand(u, vv, 0.0)
    for k, (u, vv, w) in enumerate(((0.10, -0.13, -0.03), (0.24, -0.21, -0.07), (0.33, -0.25, -0.08), (0.40, -0.28, -0.08))):
        J[f"NC_Thumb{s}{k + 1}" if k < 3 else f"NC_Thumb{s}Tip"] = hand(u, vv, w)    # (w < 0: on the body side)
    J["_palm" + s] = hand(0.22, 0.0, 0.0)

# parents (the FBX hierarchy): R15 chain as Roblox expects; every extra bone is a leaf branch off an R15 bone
PARENT = {"HumanoidRootNode": "Root", "LowerTorso": "HumanoidRootNode", "UpperTorso": "LowerTorso", "Head": "UpperTorso",
          "NC_SpineMid": "LowerTorso", "NC_NeckMid": "UpperTorso"}
for side, s, sx in SIDES:
    PARENT.update({side + "UpperArm": "UpperTorso", side + "LowerArm": side + "UpperArm", side + "Hand": side + "LowerArm",
                   side + "UpperLeg": "LowerTorso", side + "LowerLeg": side + "UpperLeg", side + "Foot": side + "LowerLeg",
                   "NC_Clavicle" + s: "UpperTorso", "NC_Twist" + s: side + "LowerArm", "NC_Toes" + s: side + "Foot"})
    for f in ("Thumb", "Index", "Middle", "Ring", "Pinky"):
        PARENT[f"NC_{f}{s}1"] = side + "Hand"
        PARENT[f"NC_{f}{s}2"] = f"NC_{f}{s}1"
        PARENT[f"NC_{f}{s}3"] = f"NC_{f}{s}2"
BONES = ["Root"] + [b for b in PARENT]
JOINT_OF_PART = {"LowerTorso": "Root", "UpperTorso": "Waist", "Head": "Neck"}
for side, s, sx in SIDES:
    JOINT_OF_PART.update({side + "UpperArm": side + "Shoulder", side + "LowerArm": side + "Elbow", side + "Hand": side + "Wrist",
                          side + "UpperLeg": side + "Hip", side + "LowerLeg": side + "Knee", side + "Foot": side + "Ankle"})
PART_OF_JOINT = {v: k for k, v in JOINT_OF_PART.items()}
R15_PARTS = list(JOINT_OF_PART.keys())
EXTRA = [b for b in BONES if b.startswith("NC_")]
PART_OF_BONE = {}
for b in BONES:
    p = b
    while p not in JOINT_OF_PART and p in PARENT:
        p = PARENT[p]
    PART_OF_BONE[b] = p if p in JOINT_OF_PART else None
PART_OF_BONE["NC_SpineMid"] = "UpperTorso"      # (the mid-back band belongs with the chest piece)
PART_OF_BONE["NC_NeckMid"] = "Head"             # (the neck belongs with the head piece, as in R15)

# ------------------------------------------------------------------------------------------------ materials
COL = {"Skin": (0.80, 0.60, 0.46), "Shirt": (0.13, 0.42, 0.55), "Pants": (0.17, 0.20, 0.27), "Shoes": (0.10, 0.10, 0.11),
       "GroundA": (0.42, 0.44, 0.46), "GroundB": (0.50, 0.52, 0.54), "Fence": (0.85, 0.85, 0.80), "Wall": (0.78, 0.70, 0.60),
       "Ink": (0.08, 0.08, 0.09)}
PART_MAT = {"Head": "Skin", "UpperTorso": "Shirt", "LowerTorso": "Pants"}
for side, s, sx in SIDES:
    PART_MAT.update({side + "UpperArm": "Shirt", side + "LowerArm": "Skin", side + "Hand": "Skin", side + "UpperLeg": "Pants",
                     side + "LowerLeg": "Pants", side + "Foot": "Shoes"})
MATS = {}


def mat(name):
    if name not in MATS:
        m = bpy.data.materials.new(name)
        c = COL[name]
        m.diffuse_color = (c[0], c[1], c[2], 1)
        MATS[name] = m
    return MATS[name]


def activate(ob):
    bpy.ops.object.select_all(action="DESELECT")
    ob.select_set(True)
    bpy.context.view_layer.objects.active = ob


def apply_all(ob):
    activate(ob)
    for m in list(ob.modifiers):
        bpy.ops.object.modifier_apply(modifier=m.name)


def tri_count(ob):
    ob.data.calc_loop_triangles()
    return len(ob.data.loop_triangles)


# ------------------------------------------------------------------------------------------------ the body skin
SK = []   # (key, roblox position, radius across, radius front-back)
EDGES = []


def node(key, pos, rx, rz, parent=None):
    k = 1.0 if key.startswith("F") else (1.22 if key.startswith("L") and key[1:2] in "6789" or key.startswith("L10") else 1.35)
    SK.append((key, pos, rx * k, rz * k))
    if parent:
        EDGES.append((parent, key))


node("T0", V(0, 3.28, 0.03), 0.40, 0.33)
node("T1", V(0, 3.58, 0.05), 0.62, 0.45, "T0")       # hips and seat
node("T2", V(0, 3.98, 0.04), 0.58, 0.40, "T1")       # top of the pelvis
node("T3", V(0, 4.32, 0.05), 0.50, 0.35, "T2")       # waist
node("T4", V(0, 4.78, 0.04), 0.58, 0.41, "T3")       # lower ribs
node("T5", V(0, 5.15, 0.00), 0.63, 0.46, "T4")       # chest
node("T6", V(0, 5.42, 0.04), 0.55, 0.38, "T5")       # top of the chest
node("T7", V(0, 5.62, 0.07), 0.20, 0.20, "T6")       # base of the neck
node("T8", V(0, 5.85, 0.05), 0.18, 0.18, "T7")
node("T9", V(0, 6.00, 0.03), 0.17, 0.17, "T8")
for side, s, sx in SIDES:
    sh, el, wr = J[side + "UpperArm"], J[side + "LowerArm"], J[side + "Hand"]
    node("A0" + s, V(sx * 0.70, 5.42, 0.04), 0.26, 0.26, "T6")          # top of the shoulder (deltoid)
    node("A1" + s, V(sx * 0.88, 5.28, 0.03), 0.25, 0.26, "A0" + s)
    node("A2" + s, sh + (el - sh) * 0.45, 0.21, 0.22, "A1" + s)          # biceps
    node("A3" + s, el, 0.16, 0.17, "A2" + s)                             # elbow
    node("A4" + s, el + (wr - el) * 0.22, 0.19, 0.18, "A3" + s)          # forearm muscle
    node("A5" + s, wr, 0.09, 0.12, "A4" + s)                             # wrist (wider front to back)
    node("A6" + s, J["_palm" + s], 0.07, 0.17, "A5" + s)                 # palm: thin, broad
    for f in ("Index", "Middle", "Ring", "Pinky"):
        r0 = 0.041 if f != "Pinky" else 0.035
        prev = "A6" + s
        for k, key in enumerate((f"NC_{f}{s}1", f"NC_{f}{s}2", f"NC_{f}{s}3", f"NC_{f}{s}Tip")):
            node("F" + key, J[key], r0 * (1 - 0.1 * k), r0 * (1 - 0.1 * k), prev)
            prev = "F" + key
    prev = "A5" + s
    for k, key in enumerate((f"NC_Thumb{s}1", f"NC_Thumb{s}2", f"NC_Thumb{s}3", f"NC_Thumb{s}Tip")):
        node("F" + key, J[key], 0.058 - 0.006 * k, 0.05 - 0.005 * k, prev)
        prev = "F" + key
    hip = J[side + "UpperLeg"]
    node("L0" + s, V(sx * 0.36, 3.42, 0.02), 0.36, 0.40, "T1")           # top of the thigh
    node("L1" + s, V(sx * 0.37, 2.75, -0.02), 0.30, 0.32, "L0" + s)
    node("L2" + s, V(sx * 0.37, 2.12, -0.02), 0.21, 0.22, "L1" + s)
    node("L3" + s, V(sx * 0.37, 1.88, -0.03), 0.19, 0.20, "L2" + s)      # knee
    node("L4" + s, V(sx * 0.37, 1.42, 0.05), 0.21, 0.23, "L3" + s)       # calf
    node("L5" + s, V(sx * 0.37, 0.78, 0.04), 0.13, 0.13, "L4" + s)
    node("L6" + s, V(sx * 0.37, 0.30, 0.05), 0.11, 0.12, "L5" + s)       # ankle
    node("L7" + s, V(sx * 0.37, 0.13, 0.25), 0.11, 0.11, "L6" + s)       # heel
    node("L8" + s, V(sx * 0.37, 0.14, -0.18), 0.15, 0.12, "L6" + s)      # arch
    node("L9" + s, V(sx * 0.37, 0.09, -0.50), 0.16, 0.085, "L8" + s)     # ball of the foot
    node("L10" + s, V(sx * 0.37, 0.08, -0.72), 0.13, 0.065, "L9" + s)    # toes

idx = {k: i for i, (k, *_r) in enumerate(SK)}
me = bpy.data.meshes.new("BodySkel")
me.from_pydata([tuple(rb(p)) for (_k, p, _a, _b) in SK], [(idx[a], idx[b]) for a, b in EDGES], [])
body = bpy.data.objects.new("Body", me)
scene.collection.objects.link(body)
skin = body.modifiers.new("Skin", "SKIN")
skin.use_smooth_shade = True
skin.branch_smoothing = 0.35
for i, (_k, _p, rx, rz) in enumerate(SK):
    me.skin_vertices[0].data[i].radius = (rx, rz)
me.skin_vertices[0].data[idx["T1"]].use_root = True
sub = body.modifiers.new("Sub", "SUBSURF")
sub.levels = sub.render_levels = 2
apply_all(body)
target_body_tris = 10500
t0 = tri_count(body)
# spend the triangles on the body's shape, not the fingers: hands decimate harder
keep = body.vertex_groups.new(name="Keep")
for v in body.data.vertices:
    pr = Vector((-v.co.x, v.co.z, v.co.y))
    keep.add([v.index], 0.0 if (abs(pr.x) > 1.02 and pr.y < 3.28) else 1.0, "REPLACE")
dec = body.modifiers.new("Dec", "DECIMATE")
dec.ratio = min(1.0, target_body_tris / max(1, t0))
dec.vertex_group = "Keep"
dec.invert_vertex_group = True   # (weighted vertices are the ones that get decimated)
dec.vertex_group_factor = 6.0
apply_all(body)
body.vertex_groups.remove(body.vertex_groups["Keep"])
for poly in body.data.polygons:
    poly.use_smooth = True

# ------------------------------------------------------------------------------------------------ the head
bpy.ops.mesh.primitive_uv_sphere_add(segments=40, ring_count=26, radius=1.0)
headob = bpy.context.active_object
headob.name = "HeadShell"
HC = V(0, 6.18, -0.04)


def gauss(a, b):
    return math.exp(-(a * a + b * b))


for v in headob.data.vertices:
    # Blender sphere coords -> Roblox direction (x, y, z) with front = -z
    d = Vector((-v.co.x, v.co.z, v.co.y)).normalized()
    x, y, z = d.x * 0.30, d.y * 0.42, d.z * 0.37
    front = max(0.0, -d.z)
    if d.y < -0.2:                                             # narrower jaw, firm chin
        k = min(1.0, (-d.y - 0.2) / 0.6)
        x *= 1 - 0.28 * k * k
        z *= 1 - 0.12 * k
        if d.z < 0 and d.y < -0.55:
            z -= 0.03 * front
    if d.z > 0 and d.y > -0.25:                                # rounder back of the skull
        z *= 1.06
    z -= 0.12 * front ** 4 * gauss(d.x / 0.12, (d.y + 0.12) / 0.19)           # nose
    z -= 0.03 * front ** 2 * gauss(0, (d.y - 0.2) / 0.07) * (1 if abs(d.x) < 0.55 else 0.4)   # brow
    z += 0.045 * front ** 2 * gauss((abs(d.x) - 0.33) / 0.12, (d.y - 0.05) / 0.08)          # eye sockets
    z -= 0.018 * front ** 2 * gauss((abs(d.x) - 0.55) / 0.15, (d.y + 0.05) / 0.12)           # cheekbones
    z -= 0.02 * front ** 3 * gauss(d.x / 0.22, (d.y + 0.43) / 0.05)                          # lips
    z += 0.012 * front ** 3 * gauss(d.x / 0.18, (d.y + 0.47) / 0.02)                         # mouth line
    side_ = abs(d.x)
    x += math.copysign(0.045, d.x) * side_ ** 8 * gauss(d.y / 0.2, (d.z - 0.04) / 0.16)    # ears
    p = HC + V(x, y, z)
    v.co = rb(p)
for poly in headob.data.polygons:
    poly.use_smooth = True

# ------------------------------------------------------------------------------------------------ skin weights
# a temporary armature whose bones run along the limbs (what automatic weights needs), then the real one
SEG_END = {"LowerTorso": V(0, 4.45, 0.05), "NC_SpineMid": V(0, 4.98, 0.05), "UpperTorso": V(0, 5.6, 0.05),
           "NC_NeckMid": V(0, 6.0, 0.04), "Head": V(0, 6.6, 0.0)}
SEG_START = {"LowerTorso": V(0, 3.30, 0.03), "NC_SpineMid": V(0, 4.45, 0.05), "UpperTorso": V(0, 4.98, 0.05),
             "NC_NeckMid": V(0, 5.70, 0.06), "Head": V(0, 6.0, 0.04)}
for side, s, sx in SIDES:
    SEG_START["NC_Clavicle" + s], SEG_END["NC_Clavicle" + s] = J["NC_Clavicle" + s], V(sx * 0.80, 5.47, 0.02)
    SEG_END[side + "UpperArm"] = J[side + "LowerArm"]
    SEG_END[side + "LowerArm"] = J["NC_Twist" + s]
    SEG_END["NC_Twist" + s] = J[side + "Hand"]
    SEG_END[side + "Hand"] = J["_palm" + s] + (J["_palm" + s] - J[side + "Hand"]) * 0.7
    SEG_END[side + "UpperLeg"] = J[side + "LowerLeg"]
    SEG_END[side + "LowerLeg"] = J[side + "Foot"]
    SEG_END[side + "Foot"] = J["NC_Toes" + s]
    SEG_END["NC_Toes" + s] = V(sx * 0.37, 0.07, -0.76)
    for f in ("Thumb", "Index", "Middle", "Ring", "Pinky"):
        SEG_END[f"NC_{f}{s}1"], SEG_END[f"NC_{f}{s}2"], SEG_END[f"NC_{f}{s}3"] = J[f"NC_{f}{s}2"], J[f"NC_{f}{s}3"], J[f"NC_{f}{s}Tip"]


def make_armature(name, along_limbs):
    ad = bpy.data.armatures.new(name)
    ob = bpy.data.objects.new(name, ad)
    scene.collection.objects.link(ob)
    activate(ob)
    bpy.ops.object.mode_set(mode="EDIT")
    eb = ad.edit_bones
    for b in BONES:
        e = eb.new(b)
        head = V(0, 0, 0) if b == "Root" else J[b]
        if along_limbs and b in SEG_END:
            h, t = SEG_START.get(b, head), SEG_END[b]
            e.head, e.tail = rb(h), rb(t)
            e.roll = 0
        else:
            e.head = rb(head)
            e.tail = rb(head) + Vector((0, 0, 0.25))        # straight up, rolled half round: local axes = Roblox axes
            e.roll = math.pi
        e.use_deform = b not in ("Root", "HumanoidRootNode")
    for b, p in PARENT.items():
        eb[b].parent = eb[p]
        eb[b].use_connect = False
    bpy.ops.object.mode_set(mode="OBJECT")
    return ob


warm = make_armature("WeightRig", True)
bpy.ops.object.select_all(action="DESELECT")
body.select_set(True)
warm.select_set(True)
bpy.context.view_layer.objects.active = warm
bpy.ops.object.parent_set(type="ARMATURE_AUTO")

# any bone the heat solver missed gets envelope weights from its segment (so no joint is left without skin)
groups = {g.index: g.name for g in body.vertex_groups}
have = {name: 0 for name in groups.values()}
for v in body.data.vertices:
    for ge in v.groups:
        if ge.weight > 0.01:
            have[groups[ge.group]] += 1
missing = [b for b in BONES if b not in ("Root", "HumanoidRootNode") and have.get(b, 0) < 3]


def seg_dist(p, a, b):
    ab = b - a
    t = max(0.0, min(1.0, (p - a).dot(ab) / max(ab.length_squared, 1e-9)))
    return (a + ab * t - p).length


if missing:
    for b in missing:
        g = body.vertex_groups.get(b) or body.vertex_groups.new(name=b)
        a, e = SEG_START.get(b, J[b]), SEG_END.get(b, J[b] + V(0, 0.2, 0))
        rad = 0.09 if b.startswith("NC_") and any(f in b for f in ("Thumb", "Index", "Middle", "Ring", "Pinky")) else 0.25
        for v in body.data.vertices:
            pr = Vector((-v.co.x, v.co.z, v.co.y))
            d = seg_dist(pr, a, e)
            if d < rad:
                g.add([v.index], (1 - d / rad) ** 2, "ADD")
# head shell: Head, easing into the upper neck at the bottom
hg = headob.vertex_groups.new(name="Head")
ng = headob.vertex_groups.new(name="NC_NeckMid")
for v in headob.data.vertices:
    y = v.co.z
    w = min(1.0, max(0.0, (y - 5.78) / 0.2))
    hg.add([v.index], w, "REPLACE")
    if w < 1:
        ng.add([v.index], 1 - w, "REPLACE")
# swap the weighting rig for the real one, join the head on, tidy the weights
activate(body)
for m in list(body.modifiers):
    body.modifiers.remove(m)
body.parent = None
bpy.data.objects.remove(warm, do_unlink=True)
rig = make_armature("Armature", False)
bpy.ops.object.select_all(action="DESELECT")
headob.select_set(True)
body.select_set(True)
bpy.context.view_layer.objects.active = body
bpy.ops.object.join()
activate(body)
bpy.ops.object.vertex_group_limit_total(group_select_mode="ALL", limit=4)
bpy.ops.object.vertex_group_normalize_all(group_select_mode="ALL", lock_active=False)
bpy.ops.object.vertex_group_clean(group_select_mode="ALL", limit=0.01)
bpy.ops.object.vertex_group_normalize_all(group_select_mode="ALL", lock_active=False)

# ------------------------------------------------------------------------------------------------ 15 body pieces
bm_full = bmesh.new()
bm_full.from_mesh(body.data)
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
bm_full.faces.ensure_lookup_table()
for _it in range(4):                                     # tidy ragged borders between pieces
    newp = dict(face_part)
    for f in bm_full.faces:
        nb = [face_part[o.index] for e in f.edges for o in e.link_faces if o is not f]
        if nb:
            best = max(set(nb), key=nb.count)
            if best != face_part[f.index] and nb.count(best) * 2 > len(nb):
                newp[f.index] = best
    face_part = newp
PIECES = {}
tri_total = 0
for part in R15_PARTS:
    bm = bm_full.copy()
    bm.faces.ensure_lookup_table()
    drop = [f for f in bm.faces if face_part[f.index] != part]
    bmesh.ops.delete(bm, geom=drop, context="FACES")
    bnd = [e for e in bm.edges if e.is_boundary]
    if bnd:
        res = bmesh.ops.holes_fill(bm, edges=bnd, sides=0)          # cap the cut: every piece is watertight
        pk = bmesh.ops.poke(bm, faces=res["faces"], center_mode="MEAN")   # ...fanned from the middle, so it stays inside
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
    m = bpy.data.meshes.new(part + "_Geo")
    bm.to_mesh(m)
    bm.free()
    ob = bpy.data.objects.new(part + "_Geo", m)
    scene.collection.objects.link(ob)
    for gi in sorted(gname):
        ob.vertex_groups.new(name=gname[gi])
    m.materials.append(mat(PART_MAT[part]))
    for poly in m.polygons:
        poly.use_smooth = True
    # normals from the whole body, so the seams between pieces don't show
    ns = []
    for v in m.vertices:
        co, i, dist = kd.find(v.co)
        ns.append(full_normals[i])
    try:
        m.normals_split_custom_set_from_vertices(ns)
    except Exception:
        pass
    ob.parent = rig
    mod = ob.modifiers.new("Armature", "ARMATURE")
    mod.object = rig
    PIECES[part] = ob
    tri_total += tri_count(ob)
bm_full.free()
bpy.data.objects.remove(body, do_unlink=True)


# ------------------------------------------------------------------------------------------------ the extra joints
def mat_xyz(r):
    """CFrame.Angles(x, y, z) as a 3x3 (degrees in)"""
    return (Euler((0, 0, r[2] * D2R)).to_matrix(), Euler((0, r[1] * D2R, 0)).to_matrix(), Euler((r[0] * D2R, 0, 0)).to_matrix())


def rot(r):
    mz, my, mx = mat_xyz(r)
    return mx @ my @ mz


CURL = {  # (knuckle, middle, tip, thumb) curl in degrees for each move
    "Idle": (15, 25, 15, 15), "TiredIdle": (20, 30, 20, 15), "Walk": (18, 28, 16, 15), "Jog": (45, 65, 40, 30),
    "Sprint": (25, 35, 20, 20), "Fall": (-5, 10, 5, 0), "JumpUp": (10, 20, 10, 10), "Land": (20, 30, 20, 15),
    "LandHard": (15, 20, 15, 10), "Stumble": (5, 15, 10, 5), "Roll": (60, 80, 50, 40), "Vault": (20, 30, 20, 15),
    "Mantle": (10, 12, 10, 8), "Climb": (20, 30, 20, 15), "GetUp": (12, 20, 12, 10), "Bump": (-5, 10, 5, 0),
    "Skid": (15, 25, 15, 12), "Pivot": (15, 25, 15, 12),
}
CLAV = {}
for side, s, sx in SIDES:
    CLAV[side] = (J["NC_Clavicle" + s], J[side + "UpperArm"])


def human_extras(R, out, P, clip, t):
    # spine and neck share the bend: the mid-back follows half the waist, the upper neck half the head
    wx, wy, wz = P.get("Waist", (0, 0, 0))
    out["NC_SpineMid"] = (0.5 * wx, 0.5 * wy, 0.5 * wz)
    nx, ny, nz = P.get("Neck", (0, 0, 0))
    out["NC_NeckMid"] = (0.45 * nx, 0.45 * ny, 0.45 * nz)
    for side, s, sx in SIDES:
        # collarbones: the shoulder blade does about a third of any arm raise past 30 degrees and the collarbone
        # swings forward as the arm reaches forward; the whole shoulder joint rides along
        ax, ay, az = P.get(side + "Shoulder", (0, 0, 0))
        d = rot((ax, ay, az)) @ Vector((0, -1, 0))
        elev = math.degrees(math.acos(max(-1.0, min(1.0, -d.y))))
        lift = min(35.0, max(0.0, elev - 30.0) / 3.0)
        prot = max(-12.0, min(18.0, ax * 0.15))
        cr = (0, sx * prot, sx * lift)
        out["NC_Clavicle" + s] = cr
        sc, shj = CLAV[side]
        moved = sc + rot(cr) @ (shj - sc)
        dv = moved - shj
        out[side + "ShoulderPos"] = (dv.x, dv.y, dv.z)
        # forearm twist: half the wrist's turn
        out["NC_Twist" + s] = (0, 0.5 * P.get(side + "Wrist", (0, 0, 0))[1], 0)
        # fingers: how each move holds the hands
        k1, k2, k3, th = CURL.get(clip, (15, 25, 15, 15))
        if clip == "Climb":
            g = NA.smooth((t - 0.18) / 0.08) * (1 - NA.smooth((t - 0.8) / 0.08))
            k1, k2, k3, th = k1 + 45 * g, k2 + 55 * g, k3 + 35 * g, th + 30 * g          # gripping the edge
        if clip == "Vault" and side == "Right":
            g = NA.smooth((t - 0.15) / 0.08) * (1 - NA.smooth((t - 0.62) / 0.08))
            k1, k2, k3 = k1 * (1 - g), k2 * (1 - g), k3 * (1 - g)                           # hand flat on the top
        spread = {"Index": -6, "Middle": -2, "Ring": 2, "Pinky": 6} if clip in ("Fall", "Bump") else {}
        for f in ("Index", "Middle", "Ring", "Pinky"):
            out[f"NC_{f}{s}1"] = (spread.get(f, 0), 0, -sx * k1)
            out[f"NC_{f}{s}2"] = (0, 0, -sx * k2)
            out[f"NC_{f}{s}3"] = (0, 0, -sx * k3)
        out[f"NC_Thumb{s}1"] = (-0.3 * th, sx * 0.6 * th, -sx * 0.4 * th)
        out[f"NC_Thumb{s}2"] = (0, 0, -sx * 0.6 * th)
        out[f"NC_Thumb{s}3"] = (0, 0, -sx * 0.5 * th)
        # toes stay on the ground as the heel lifts, and lift a little in the swing
        p = P.get("_pitch" + side)
        toe = 0.0
        if p is not None:
            toe = -p * 0.85 if p < 0 else 0.0
            if P.get("_stance" + side) is False:
                toe = max(0.0, toe * 0.3) + 6
        out["NC_Toes" + s] = (toe, 0, 0)


GAITS_H = {
    "Walk": dict(v=5.0, T=1.0, stance=0.62, c=0.12, drop=0.20, bob=0.07, run=False, heel=12, toe_off=32, rollS=0.62,
                 toe_rise=0.50, lift=0.42, skew=1.0, hk=1.0, pelvisX=-1, yaw=5, proll=3, lat=0.08, lean=-3, thorax=7,
                 arm_mean=2, arm_amp=18, e0=14, eamp=10, shZ=6),
    "Jog": dict(v=16.0, T=0.68, stance=0.30, c=0.20, drop=0.38, bob=0.16, run=True, heel=4, toe_off=38, rollS=0.45,
                toe_rise=0.42, lift=1.25, skew=0.6, hk=0.6, pelvisX=-4, yaw=7, proll=4, lat=0.06, lean=-7, thorax=10,
                arm_mean=6, arm_amp=32, e0=85, eamp=8, shZ=10),
    "Sprint": dict(v=25.0, T=0.56, stance=0.23, c=0.10, drop=0.45, bob=0.15, run=True, heel=-6, toe_off=42, rollS=0.35,
                   toe_rise=0.50, lift=1.90, skew=0.55, hk=0.6, pelvisX=-6, yaw=8, proll=3, lat=0.05, lean=-13, thorax=12,
                   arm_mean=8, arm_amp=55, e0=92, eamp=22, shZ=8),
}
RIG = dict(L1=J["RightUpperLeg"].y - J["RightLowerLeg"].y, L2=J["RightLowerLeg"].y - J["RightFoot"].y, hipY=J["RightUpperLeg"].y,
           ankY=J["RightFoot"].y, heelLift=0.08, S=J["RightUpperLeg"].y / 2.0, shZ0=7, gaits=GAITS_H, extras=human_extras)
LOOPS = NA.loops(RIG)
ONESHOT = NA.oneshots(RIG)

# ------------------------------------------------------------------------------------------------ export the body
for part, ob in PIECES.items():
    ob["NC_Body"] = "Human"
bpy.ops.object.select_all(action="DESELECT")
rig.select_set(True)
for ob in PIECES.values():
    ob.select_set(True)
bpy.context.view_layer.objects.active = rig
bpy.ops.export_scene.fbx(filepath=os.path.join(OUT, "NeonCoastHuman.fbx"), use_selection=True, object_types={"ARMATURE", "MESH"},
                         apply_scale_options="FBX_SCALE_UNITS", add_leaf_bones=False, bake_anim=False, use_custom_props=True,
                         primary_bone_axis="Y", secondary_bone_axis="X", mesh_smooth_type="OFF", path_mode="COPY")
try:
    bpy.ops.export_scene.gltf(filepath=os.path.join(OUT, "NeonCoastHuman.glb"), export_format="GLB", use_selection=True,
                              export_skins=True, export_animations=False)
except Exception as ex:
    print("GLB export skipped:", ex)

# ------------------------------------------------------------------------------------------------ the moves on this body
from bpy_extras import anim_utils

rig.animation_data_create()
for pb in rig.pose.bones:
    pb.rotation_mode = "ZYX"
ACTIONS = {}
TRANSLATED = ("Root", "RightShoulder", "LeftShoulder")


def key_pose(P, frame):
    for b in BONES:
        if b in ("Root", "HumanoidRootNode"):
            continue
        pb = rig.pose.bones[b]
        name = JOINT_OF_PART.get(b, b)
        r = P.get(name, (0, 0, 0))
        pb.rotation_euler = (r[0] * D2R, r[1] * D2R, r[2] * D2R)
        pb.keyframe_insert("rotation_euler", frame=frame)
        if name in TRANSLATED:
            pb.location = P.get(name + "Pos", (0, 0, 0))
            pb.keyframe_insert("location", frame=frame)


def fcurves_of(act):
    cb = anim_utils.action_get_channelbag_for_slot(act, rig.animation_data.action_slot)
    return list(cb.fcurves) if cb else []


for name, (fn, dur, n) in LOOPS.items():
    act = bpy.data.actions.new("NCH_" + name)
    act.use_fake_user = True
    rig.animation_data.action = act
    frames = dur * FPS
    for i in range(n + 1):
        key_pose(NA.finalize(RIG, fn((i % n) / n), name, (i % n) / n), i / n * frames)
    for fc in fcurves_of(act):
        fc.modifiers.new("CYCLES")
        fc.update()
    ACTIONS[name] = (act, dur, True)
for name, c in ONESHOT.items():
    act = bpy.data.actions.new("NCH_" + name)
    act.use_fake_user = True
    rig.animation_data.action = act
    frames = c["dur"] * FPS
    for (t, P) in c["keys"]:
        key_pose(NA.finalize(RIG, P, name, t), t * frames)
    for fc in fcurves_of(act):
        fc.update()
    ACTIONS[name] = (act, c["dur"], False)


def use_action(name):
    act = ACTIONS[name][0]
    rig.animation_data.action = act
    if act.slots:
        rig.animation_data.action_slot = act.slots[0]


EXPORT_BONES = [b for b in BONES if b not in ("Root", "HumanoidRootNode")]
EXPORT = {}
for name, (act, dur, loop) in ACTIONS.items():
    use_action(name)
    n = LOOPS[name][2] if loop else max(2, int(round(dur * FPS)) + 1)
    qs = {JOINT_OF_PART.get(b, b): [] for b in EXPORT_BONES}
    ts = {jn: [] for jn in TRANSLATED}
    prev = {}
    for i in range(n):
        tn = i / n if loop else i / (n - 1)
        f = tn * dur * FPS
        scene.frame_set(int(math.floor(f)), subframe=f - math.floor(f))
        for b in EXPORT_BONES:
            jn = JOINT_OF_PART.get(b, b)
            mb = rig.pose.bones[b].matrix_basis
            q = mb.to_quaternion()
            q = (q.x, q.y, q.z, q.w)
            if jn in prev and sum(a * c for a, c in zip(q, prev[jn])) < 0:
                q = tuple(-c for c in q)
            prev[jn] = q
            qs[jn].extend(round(c, 4) for c in q)
            if jn in ts:
                tr = mb.translation
                ts[jn].extend(round(c, 4) for c in (tr.x, tr.y, tr.z))
    e = {"dur": round(dur, 4), "loop": loop, "n": n, "q": qs, "t": ts, "p": ts["Root"]}
    if name in GAITS_H:
        e["speed"], e["stride"] = GAITS_H[name]["v"], round(GAITS_H[name]["v"] * GAITS_H[name]["T"], 4)
    if name in NA.BLEND:
        e["blendIn"], e["blendOut"] = NA.BLEND[name]
    EXPORT[name] = e


def lua(v, ind=""):
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (int, float)):
        r = round(v, 4)
        return repr(int(r)) if float(r).is_integer() else repr(r)
    if isinstance(v, str):
        return json.dumps(v)
    if isinstance(v, list):
        return "{" + ",".join(lua(x, ind) for x in v) + "}"
    if isinstance(v, dict):
        items = []
        for k in sorted(v):
            key = k if k.isidentifier() else "[" + json.dumps(k) + "]"
            items.append(ind + "\t" + key + " = " + lua(v[k], ind + "\t") + ",\n")
        return "{\n" + "".join(items) + ind + "}"
    raise TypeError(type(v))


src = ("-- NCAnimationsHuman: generated by build_human.py from NeonCoast_Human.blend. Do not hand-edit; re-run it.\n"
       "-- The same 18 moves as NCAnimations, made for the real human body: q = per joint (Motor6D name for the 15\n"
       "-- body joints, Bone name for the NC_ extra joints) flat quaternions per sample; t = translations for the joints\n"
       "-- that move (Root, and both shoulders, which ride on the collarbones).\n"
       "return " + lua({"fps": FPS, "body": "Human", "clips": EXPORT}) + "\n")
with open(os.path.join(OUT, "NCAnimationsHuman.lua"), "w", encoding="utf-8") as f:
    f.write(src)

# ------------------------------------------------------------------------------------------------ Studio setup helper
ATT = [  # (part, attachment name, roblox position): the standard R15 attachments, so tools and accessories fit
    ("Head", "HatAttachment", V(0, 6.62, -0.02)), ("Head", "HairAttachment", V(0, 6.58, 0.0)),
    ("Head", "FaceFrontAttachment", V(0, 6.2, -0.42)), ("Head", "FaceCenterAttachment", V(0, 6.2, -0.04)),
    ("UpperTorso", "NeckAttachment", V(0, 5.62, 0.06)), ("UpperTorso", "BodyFrontAttachment", V(0, 5.0, -0.45)),
    ("UpperTorso", "BodyBackAttachment", V(0, 5.0, 0.48)), ("UpperTorso", "LeftCollarAttachment", V(-0.45, 5.5, 0.04)),
    ("UpperTorso", "RightCollarAttachment", V(0.45, 5.5, 0.04)), ("LowerTorso", "WaistCenterAttachment", V(0, 4.2, 0.05)),
    ("LowerTorso", "WaistFrontAttachment", V(0, 4.2, -0.38)), ("LowerTorso", "WaistBackAttachment", V(0, 4.2, 0.42)),
]
for side, s, sx in SIDES:
    pal = J["_palm" + s]
    ATT += [(side + "Hand", side + "GripAttachment", pal + V(0, -0.1, 0)),
            (side + "UpperArm", side + "ShoulderAttachment", J[side + "UpperArm"] + V(0, 0.18, 0)),
            (side + "Foot", side + "FootAttachment", V(sx * 0.37, 0.0, -0.1))]


def v3(p):
    return "Vector3.new(%.3f, %.3f, %.3f)" % (p.x, p.y, p.z)


assemble = ("-- AssembleHumanBody (generated by build_human.py): run once in Studio's command bar after importing\n"
            "-- NeonCoastHuman.fbx with the 3D Importer (rig: R15). Select the imported model, paste this, press Enter.\n"
            "-- It finishes the character: Humanoid settings, the root part, standard attachments (tools, hats), the NC_Body\n"
            "-- tag the movement scripts look for, and puts it in StarterPlayer as StarterCharacter so everyone spawns as it.\n"
            "local model = game:GetService(\"Selection\"):Get()[1]\n"
            "assert(model and model:IsA(\"Model\"), \"Select the imported NeonCoastHuman model first\")\n"
            "local REST_HRP_Y = %.3f -- root part centre above the ground in the rest pose\n" % HRP_Y +
            "local HIP_HEIGHT = %.3f\n" % (HRP_Y - 1.0) +
            "local ATT = {\n" + "".join("\t{ \"%s\", \"%s\", %s },\n" % (p, n, v3(pos)) for (p, n, pos) in ATT) + "}\n" +
            """local need = { "HumanoidRootPart", "LowerTorso", "UpperTorso", "Head", "LeftUpperArm", "LeftLowerArm", "LeftHand",
	"RightUpperArm", "RightLowerArm", "RightHand", "LeftUpperLeg", "LeftLowerLeg", "LeftFoot", "RightUpperLeg", "RightLowerLeg", "RightFoot" }
for _, n in need do
	if not model:FindFirstChild(n) then
		warn("AssembleHumanBody: missing " .. n .. " (import with the R15 rig option)")
	end
end
local hrp = model:FindFirstChild("HumanoidRootPart")
assert(hrp, "no HumanoidRootPart: import with the R15 rig option")
hrp.Size, hrp.Transparency, hrp.CanCollide = Vector3.new(2, 2, 1), 1, true
model.PrimaryPart = hrp
local hum = model:FindFirstChildOfClass("Humanoid") or Instance.new("Humanoid")
hum.Parent = model
hum.RigType = Enum.HumanoidRigType.R15
pcall(function() hum.AutomaticScalingEnabled = false end)
hum.HipHeight = HIP_HEIGHT
-- the ground point under the root part in the rest pose, facing the model's way
local origin = hrp.CFrame * CFrame.new(0, -REST_HRP_Y, 0)
for _, a in ATT do
	local part = model:FindFirstChild(a[1])
	if part and not part:FindFirstChild(a[2]) then
		local at = Instance.new("Attachment")
		at.Name = a[2]
		at.WorldCFrame = origin * CFrame.new(a[3])
		at.Parent = part
	end
end
for _, d in model:GetDescendants() do
	if d:IsA("MeshPart") and d ~= hrp then
		d.CanCollide = d.Name == "UpperTorso" or d.Name == "LowerTorso" or d.Name == "Head"
		pcall(function() d.CollisionFidelity = Enum.CollisionFidelity.Box end)
		d.Anchored = false
	end
end
hrp.Anchored = false
model:SetAttribute("NC_Body", "Human")
model.Name = "StarterCharacter"
model.Parent = game:GetService("StarterPlayer")
print("AssembleHumanBody: done. StarterPlayer.StarterCharacter is the Neon Coast human body (" .. #model:GetDescendants() .. " parts and joints).")
""")
with open(os.path.join(OUT, "AssembleHumanBody.lua"), "w", encoding="utf-8") as f:
    f.write(assemble)

stats = {"tris_total": tri_total, "tris": {p: tri_count(o) for p, o in PIECES.items()}, "bones": len(BONES),
         "extra_bones": len(EXTRA), "missing_heat_bones": missing, "height": H, "hipHeight": HRP_Y - 1.0,
         "reach_over_studs": {k: round(v, 3) for k, v in NA.STATS["over"].items()}, "lua_chars": len(src),
         "strides": {k: EXPORT[k].get("stride") for k in ("Walk", "Jog", "Sprint")}}
with open(os.path.join(OUT, "human.json"), "w") as f:
    json.dump(stats, f, indent=1)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "NeonCoast_Human.blend"))
print("NEONCOAST_HUMAN", json.dumps(stats))

# ------------------------------------------------------------------------------------------------ previews
RENDER = os.environ.get("NC_HUMAN_RENDER", "1")    # 1 = everything, views = just the body, 0 = nothing
if RENDER in ("1", "views"):
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.display.shading.light = "STUDIO"
    scene.display.shading.color_type = "MATERIAL"
    scene.display.shading.show_shadows = True
    scene.display.shading.show_cavity = True
    scene.render.resolution_x, scene.render.resolution_y = 960, 540
    world = bpy.data.worlds.new("W")
    world.color = (0.62, 0.74, 0.86)
    scene.world = world

    def box(name, size, colour, at):
        m = bpy.data.meshes.new(name)
        b = bmesh.new()
        bmesh.ops.create_cube(b, size=1.0)
        for v in b.verts:
            v.co = Vector((v.co.x * size[0], v.co.y * size[1], v.co.z * size[2]))
        b.to_mesh(m)
        b.free()
        m.materials.append(mat(colour))
        o = bpy.data.objects.new(name, m)
        scene.collection.objects.link(o)
        o.location = at
        return o

    for i in range(-40, 300):
        box(f"G{i}", (12, 1.0, 0.1), "GroundA" if i % 2 else "GroundB", Vector((0, -(i + 0.5), -0.05)))
    cam_d = bpy.data.cameras.new("Cam")
    cam_d.lens = 32
    cam = bpy.data.objects.new("Cam", cam_d)
    scene.collection.objects.link(cam)
    scene.camera = cam
    label_c = bpy.data.curves.new("Label", "FONT")
    label = bpy.data.objects.new("Label", label_c)
    scene.collection.objects.link(label)
    label_c.size = 0.04
    label.parent = cam
    label.location = (-0.54, 0.27, -1.0)
    label_c.materials.append(mat("Ink"))

    # the body: front, side, back, three-quarter, and a close look at a hand
    rig.animation_data.action = None
    for pb in rig.pose.bones:
        pb.rotation_euler = (0, 0, 0)
        pb.location = (0, 0, 0)
    label_c.body = ""
    for vname, loc, tgt in (("front", (0, -14, 3.5), (0, 0, 3.3)), ("side", (14, 0, 3.5), (0, 0, 3.3)),
                            ("back", (0, 14, 3.5), (0, 0, 3.3)), ("threequarter", (-9, -11, 4.6), (0, 0, 3.4)),
                            ("hand", (-3.2, -2.4, 3.1), (-1.15, 0, 2.9)), ("face", (0, -3.6, 6.2), (0, 0, 6.15))):
        cam.location = loc
        cam.rotation_euler = (Vector(tgt) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
        scene.render.filepath = os.path.join(PREV, f"Human_{vname}.png")
        bpy.ops.render.render(write_still=True)

    if RENDER != "1":
        raise SystemExit(0)
    frames_dir = os.path.join(os.environ.get("TEMP", OUT), "nc_human_frames")
    shutil.rmtree(frames_dir, ignore_errors=True)
    os.makedirs(frames_dir, exist_ok=True)
    obstacles = []

    def obstacle(kind):
        for o in obstacles:
            bpy.data.objects.remove(o, do_unlink=True)
        obstacles.clear()
        if kind == "fence":
            obstacles.append(box("Fence", (8, 0.3, 4.0), "Fence", Vector((0, -4.15, 2.0))))
        elif kind == "wall":
            obstacles.append(box("Wall", (8, 3.0, 4.4), "Wall", Vector((0, -5.5, 2.2))))
        elif kind == "tall":
            obstacles.append(box("TallFence", (8, 0.3, 7.6), "Fence", Vector((0, -4.15, 3.8))))

    rootH = HRP_Y

    def path_keys(kind):
        # MovementClient's planned paths for this body (root height scaled), obstacle face 4 studs ahead
        hitD = 4.0
        if kind == "Vault":
            top, depth = 4.0, 0.3
            return [(0, 0, rootH, ""), (0.38, hitD - 0.2, top + 0.52 * rootH, "out"), (0.8, hitD + depth + 0.4, top + 0.48 * rootH, ""),
                    (1.0, hitD + depth + 1.1, top + 0.37 * rootH, "in")]
        if kind == "Mantle":
            top = 4.4
            return [(0, 0, rootH, ""), (0.45, hitD - 0.25, max(top + 0.33 * rootH, rootH), "out"), (1.0, hitD + 1.3, top + rootH, "")]
        top, depth = 7.6, 0.3
        return [(0, 0, rootH, ""), (0.26, hitD - 0.32 * rootH, max(top - 0.97 * rootH, rootH), "out"),
                (0.38, hitD - 0.31 * rootH, max(top - rootH, rootH), ""), (0.72, hitD - 0.3, top + 0.3 * rootH, ""),
                (1.0, hitD + depth + 0.7, top + 0.5 * rootH, "")]

    def path_at(keys, u):
        for i in range(len(keys) - 1):
            k0, k1 = keys[i], keys[i + 1]
            if u <= k1[0] or i == len(keys) - 2:
                sv = NA.clamp((u - k0[0]) / max(k1[0] - k0[0], 1e-3), 0, 1)
                e = (1 - (1 - sv) ** 2) if k1[3] == "out" else (sv * sv if k1[3] == "in" else sv * sv * (3 - 2 * sv))
                return k0[1] + (k1[1] - k0[1]) * sv, k0[2] + (k1[2] - k0[2]) * e
        return keys[-1][1], keys[-1][2]

    SHOW = [("Idle", 1.0, "Idle"), ("Walk", 3, "Walk 5 studs/s"), ("Jog", 3, "Jog 16 studs/s"), ("Sprint", 4, "Sprint 25 studs/s"),
            ("Skid", 1, "Sprint stop"), ("TiredIdle", 2, "Out of breath"), ("JumpUp", 1, "Jump"), ("Fall", 1, "Falling"),
            ("Land", 1, "Soft landing"), ("LandHard", 1, "Hard landing"), ("Roll", 1, "Landing roll"), ("Vault", 1, "Vault a fence"),
            ("Mantle", 1, "Mantle a wall"), ("Climb", 1, "Climb over a fence"), ("GetUp", 1, "Getting up"), ("Bump", 1, "Into a wall"),
            ("Pivot", 1, "Plant and turn")]
    sheet_frames = {}
    idx_f = 0
    for (name, reps, text) in SHOW:
        use_action(name)
        act, dur, loop = ACTIONS[name]
        slow = 1.0 if name in ("Idle", "TiredIdle", "Fall", "Walk") else 2.0
        label_c.body = text + ("  (half speed)" if slow > 1 else "")
        total = int(round(dur * reps * FPS * slow))
        obstacle({"Vault": "fence", "Mantle": "wall", "Climb": "tall"}.get(name))
        pk = path_keys(name) if name in ("Vault", "Mantle", "Climb") else None
        for i in range(total + 1):
            tt = (i / FPS) / slow
            u = (tt / dur) % 1.0 if loop else min(1.0, tt / dur)
            f = u * dur * FPS
            scene.frame_set(int(math.floor(f)), subframe=f - math.floor(f))
            if name in GAITS_H:
                y, z = GAITS_H[name]["v"] * tt, 0.0
            elif name == "Skid":
                y, z = (25 * tt - 20 * tt * tt if tt < 0.625 else 7.8), 0.0
            elif name == "Roll":
                y, z = 14 * tt - 4.5 * tt * tt, 0.0
            elif pk:
                sv, hy = path_at(pk, u)
                y, z = sv, hy - rootH
            else:
                y, z = 0.0, 0.0
            rig.location = (0, -y, z)                      # forward is Blender -Y for this body
            cam.location = (-17.5, -y - 1.2, 3.6 + max(0.0, z) * 0.7)
            cam.rotation_euler = (math.radians(88), 0, math.radians(-90))
            scene.render.filepath = os.path.join(frames_dir, f"f{idx_f:05d}.png")
            bpy.ops.render.render(write_still=True)
            sheet_frames.setdefault(name, []).append(scene.render.filepath)
            idx_f += 1
    with open(os.path.join(frames_dir, "sheets.json"), "w") as f:
        json.dump(sheet_frames, f)
    print("NEONCOAST_FRAMES", idx_f, frames_dir)
