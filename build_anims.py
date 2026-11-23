# Neon Coast movement animations, authored in Blender on a rig that matches the Roblox R15 body joint for joint.
#   blender --background --factory-startup --python build_anims.py
# Every bone sits on its Roblox joint, points straight up with zero roll, so a bone's local axes ARE the Roblox
# joint's axes (X right, Y up, Z back) and a pose bone's rotation/location IS the Motor6D.Transform Roblox wants.
# Rotation mode ZYX = CFrame.Angles(x, y, z). Conventions (Roblox): +X lifts arms and thighs forward and bends
# elbows, knees bend negative, +X tips the head/torso back, +Y turns left, +Z tips the right arm out.
# Gaits are built from how people actually move: the stance foot is planted and rolls heel to toe while the body
# travels over it (leg IK keeps it on the ground), the swing foot loops forward, the pelvis bobs, sways, turns
# and drops on the swing side, the chest counter-rotates, arms swing against the legs, the head stays level.
# Out: NCAnimations.lua (data the game plays on every player), NeonCoastAnimations.rbxmx (the same clips as
# KeyframeSequences, if you ever want to publish them as Roblox animations), NeonCoast_Animations.blend (to edit),
# anims.json (stats), previews/Movement_Animations.mp4 + previews/Anim_*.png.
import bpy, bmesh, math, json, os, sys, subprocess, shutil
from mathutils import Vector, Matrix

OUT = r"C:\Users\Crisa\Documents\NeonCoast_Blender"
PREV = os.path.join(OUT, "previews")
FPS = 30
L1, L2 = 1.0, 0.7          # hip->knee, knee->ankle (this rig: hip joint 2.0 above the ground, ankle 0.3)
HIP_Y = 2.0
D2R = math.pi / 180

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.render.fps = FPS


def rb(v):
    """Roblox (x, y, z) -> Blender (x, -z, y)"""
    return Vector((v[0], -v[2], v[1]))


# ------------------------------------------------------------------------------------------------ the R15 body
PARTS = {  # Roblox coordinates (centre, size); HumanoidRootPart centre 3.0 above the ground (HipHeight 2)
    "LowerTorso": ((0, 2.2, 0), (2, 0.4, 1), "Shirt"),
    "UpperTorso": ((0, 3.2, 0), (2, 1.6, 1), "Shirt"),
    "Head": ((0, 4.6, 0), (1.15, 1.2, 1.15), "Skin"),
}
for s, sx in (("Right", 1), ("Left", -1)):
    PARTS[s + "UpperArm"] = ((1.5 * sx, 3.37, 0), (1, 1.17, 1), "Shirt")
    PARTS[s + "LowerArm"] = ((1.5 * sx, 2.62, 0), (0.95, 0.95, 0.95), "Skin")
    PARTS[s + "Hand"] = ((1.5 * sx, 2.0, 0), (0.85, 0.4, 0.85), "Skin")
    PARTS[s + "UpperLeg"] = ((0.5 * sx, 1.5, 0), (1, 1.1, 1), "Pants")
    PARTS[s + "LowerLeg"] = ((0.5 * sx, 0.67, 0), (0.95, 0.85, 0.95), "Pants")
    PARTS[s + "Foot"] = ((0.5 * sx, 0.15, -0.12), (1, 0.3, 1.15), "Shoes")

JOINTS = [("Root", "HumanoidRootPart", "LowerTorso", (0, 2.0, 0)), ("Waist", "LowerTorso", "UpperTorso", (0, 2.4, 0)),
          ("Neck", "UpperTorso", "Head", (0, 4.0, 0))]
for s, sx in (("Right", 1), ("Left", -1)):
    JOINTS += [(s + "Shoulder", "UpperTorso", s + "UpperArm", (1.0 * sx, 3.76, 0)),
               (s + "Elbow", s + "UpperArm", s + "LowerArm", (1.5 * sx, 3.0, 0)),
               (s + "Wrist", s + "LowerArm", s + "Hand", (1.5 * sx, 2.2, 0)),
               (s + "Hip", "LowerTorso", s + "UpperLeg", (0.5 * sx, 2.0, 0)),
               (s + "Knee", s + "UpperLeg", s + "LowerLeg", (0.5 * sx, 1.0, 0)),
               (s + "Ankle", s + "LowerLeg", s + "Foot", (0.5 * sx, 0.3, 0))]
JOINT_OF_PART = {j[2]: j[0] for j in JOINTS}
PART_OF_JOINT = {j[0]: j[2] for j in JOINTS}
PARENT_OF_PART = {j[2]: j[1] for j in JOINTS}

COL = {"Skin": (0.93, 0.76, 0.60), "Shirt": (0.10, 0.62, 0.66), "Pants": (0.16, 0.20, 0.30), "Shoes": (0.12, 0.12, 0.13),
       "Face": (0.08, 0.08, 0.09), "GroundA": (0.42, 0.44, 0.46), "GroundB": (0.50, 0.52, 0.54), "Fence": (0.85, 0.85, 0.80),
       "Wall": (0.78, 0.70, 0.60)}
MATS = {}


def mat(name):
    if name not in MATS:
        m = bpy.data.materials.new(name)
        c = COL[name]
        m.diffuse_color = (c[0], c[1], c[2], 1)
        MATS[name] = m
    return MATS[name]


def box_obj(name, size, colour, at=Vector((0, 0, 0))):
    me = bpy.data.meshes.new(name)
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts:
        v.co = Vector((v.co.x * size[0], v.co.y * size[1], v.co.z * size[2]))
    bm.to_mesh(me)
    bm.free()
    me.materials.append(mat(colour))
    ob = bpy.data.objects.new(name, me)
    scene.collection.objects.link(ob)
    ob.location = at
    return ob


arm_data = bpy.data.armatures.new("R15")
arm = bpy.data.objects.new("R15", arm_data)
scene.collection.objects.link(arm)
bpy.context.view_layer.objects.active = arm
bpy.ops.object.mode_set(mode="EDIT")
eb = arm_data.edit_bones
root_b = eb.new("HumanoidRootPart")
root_b.head = rb((0, 3.0, 0))
root_b.tail = root_b.head + Vector((0, 0, 0.3))
root_b.roll = 0
for (jn, p0, p1, pos) in JOINTS:
    b = eb.new(p1)
    b.head = rb(pos)
    b.tail = b.head + Vector((0, 0, 0.25))   # straight up, roll 0: local axes = Roblox joint axes
    b.roll = 0
for (jn, p0, p1, pos) in JOINTS:
    eb[p1].parent = eb[p0]
    eb[p1].use_connect = False
bpy.ops.object.mode_set(mode="POSE")
for pb in arm.pose.bones:
    pb.rotation_mode = "ZYX"
bpy.ops.object.mode_set(mode="OBJECT")
bpy.context.view_layer.update()

# blocky body pieces riding their bones, plus a face so you can see which way it's looking
SIZES_B = {}
for part, (c, size, colour) in PARTS.items():
    sz = Vector((size[0], size[2], size[1]))           # Roblox (x, y, z) size -> Blender (x, z-depth, y-height)
    ob = box_obj("Body_" + part, sz, colour)
    ob.parent = arm
    ob.parent_type = "BONE"
    ob.parent_bone = part
    bpy.context.view_layer.update()
    ob.matrix_world = Matrix.Translation(rb(c))
face = box_obj("Body_Face", Vector((0.7, 0.06, 0.18)), "Face")
face.parent = arm
face.parent_type = "BONE"
face.parent_bone = "Head"
bpy.context.view_layer.update()
face.matrix_world = Matrix.Translation(rb((0, 4.72, -0.6)))
bpy.context.view_layer.update()


# ------------------------------------------------------------------------------------------------ the moves (shared maths)
sys.path.insert(0, OUT)
import importlib, nc_anim as NA
importlib.reload(NA)
from nc_anim import clamp, smooth
RIG = NA.RIG_R15
GAITS = RIG["gaits"]
STATS = NA.STATS
LOOPS = NA.loops(RIG)
ONESHOT = NA.oneshots(RIG)
BLEND = NA.BLEND

# ------------------------------------------------------------------------------------------------ key it in Blender
from bpy_extras import anim_utils

arm.animation_data_create()
ACTIONS = {}


def key_pose(P, frame):
    for (jn, p0, p1, pos) in JOINTS:
        pb = arm.pose.bones[p1]
        r = P.get(jn, (0, 0, 0))
        pb.rotation_euler = (r[0] * D2R, r[1] * D2R, r[2] * D2R)
        pb.keyframe_insert("rotation_euler", frame=frame)
        if jn == "Root":
            pb.location = P.get("RootPos", (0, 0, 0))
            pb.keyframe_insert("location", frame=frame)


def new_action(name):
    act = bpy.data.actions.new("NC_" + name)
    act.use_fake_user = True
    arm.animation_data.action = act
    return act


def fcurves_of(act):
    slot = arm.animation_data.action_slot
    cb = anim_utils.action_get_channelbag_for_slot(act, slot)
    return list(cb.fcurves) if cb else []


for name, (fn, dur, n) in LOOPS.items():
    act = new_action(name)
    frames = dur * FPS
    for i in range(n + 1):
        key_pose(NA.finalize(RIG, fn((i % n) / n), name, (i % n) / n), i / n * frames)
    for fc in fcurves_of(act):
        fc.modifiers.new("CYCLES")                       # loops wrap seamlessly (cycle-aware handles)
        fc.update()
    ACTIONS[name] = (act, dur, True)
for name, c in ONESHOT.items():
    act = new_action(name)
    frames = c["dur"] * FPS
    for (t, P) in c["keys"]:
        key_pose(NA.finalize(RIG, P, name, t), t * frames)
    for fc in fcurves_of(act):
        fc.update()
    ACTIONS[name] = (act, c["dur"], False)


def use_action(name):
    act = ACTIONS[name][0]
    arm.animation_data.action = act
    if act.slots:
        arm.animation_data.action_slot = act.slots[0]


# ------------------------------------------------------------------------------------------------ export
ANIM_JOINTS = [j[0] for j in JOINTS]


def sample(name, t_norm):
    """evaluated pose (Roblox Transforms) at normalised time: {joint: (qx, qy, qz, qw)}, root translation"""
    act, dur, loop = ACTIONS[name]
    f = t_norm * dur * FPS
    scene.frame_set(int(math.floor(f)), subframe=f - math.floor(f))
    out, pos = {}, (0, 0, 0)
    for jn in ANIM_JOINTS:
        pb = arm.pose.bones[PART_OF_JOINT[jn]]
        q = pb.matrix_basis.to_quaternion()
        out[jn] = (q.x, q.y, q.z, q.w)
        if jn == "Root":
            tr = pb.matrix_basis.translation
            pos = (tr.x, tr.y, tr.z)
    return out, pos


EXPORT = {}
for name, (act, dur, loop) in ACTIONS.items():
    use_action(name)
    n = LOOPS[name][2] if loop else max(2, int(round(dur * FPS)) + 1)
    qs = {jn: [] for jn in ANIM_JOINTS}
    ps = []
    prev = {}
    for i in range(n):
        t = i / n if loop else i / (n - 1)
        o, p = sample(name, t)
        for jn in ANIM_JOINTS:
            q = o[jn]
            if jn in prev and sum(a * b for a, b in zip(q, prev[jn])) < 0:
                q = tuple(-c for c in q)                 # keep neighbouring quaternions on the same side (clean slerp)
            prev[jn] = q
            qs[jn].extend(round(c, 4) for c in q)
        ps.extend(round(c, 4) for c in p)
    e = {"dur": round(dur, 4), "loop": loop, "n": n, "q": qs, "p": ps}
    if name in GAITS:
        g = GAITS[name]
        e["speed"], e["stride"] = g["v"], round(g["v"] * g["T"], 4)   # studs travelled per cycle: no foot sliding
    if name in BLEND:
        e["blendIn"], e["blendOut"] = BLEND[name]
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
        if all(isinstance(x, (int, float)) for x in v):
            return "{" + ",".join(lua(x) for x in v) + "}"
        return "{" + ",".join(lua(x, ind) for x in v) + "}"
    if isinstance(v, dict):
        items = []
        for k in sorted(v):
            key = k if k.isidentifier() else "[" + json.dumps(k) + "]"
            items.append(ind + "\t" + key + " = " + lua(v[k], ind + "\t") + ",\n")
        return "{\n" + "".join(items) + ind + "}"
    raise TypeError(type(v))


src = ("-- NCAnimations: generated by build_anims.py from NeonCoast_Animations.blend. Do not hand-edit; re-run it.\n"
       "-- Per clip: dur (s), loop, n samples (evenly spaced over the loop, or start..end for one-shots), q = per joint\n"
       "-- (Motor6D name) flat quaternions qx,qy,qz,qw per sample (= Motor6D.Transform rotation), p = Root translation\n"
       "-- x,y,z per sample. Gaits also carry speed and stride (studs per cycle: play at speed/stride cycles per second\n"
       "-- and the feet don't slide). blendIn/blendOut: fractions of a one-shot to fade in and out over.\n"
       "return " + lua({"fps": FPS, "clips": EXPORT}) + "\n")
with open(os.path.join(OUT, "NCAnimations.lua"), "w", encoding="utf-8") as f:
    f.write(src)


# KeyframeSequences (for the Animation Editor / publishing, if ever wanted)
def cf_xml(q, p=(0, 0, 0)):
    from mathutils import Quaternion
    m = Quaternion((q[3], q[0], q[1], q[2])).to_matrix()
    vals = [p[0], p[1], p[2]] + [m[r][c] for r in range(3) for c in range(3)]
    tags = ["X", "Y", "Z", "R00", "R01", "R02", "R10", "R11", "R12", "R20", "R21", "R22"]
    return "".join(f"<{t}>{v:.5f}</{t}>" for t, v in zip(tags, vals))


CHILDREN = {}
for (jn, p0, p1, pos) in JOINTS:
    CHILDREN.setdefault(p0, []).append(p1)
ref = [0]


def rid():
    ref[0] += 1
    return f"RBXA{ref[0]}"


def pose_xml(part, k, e):
    jn = JOINT_OF_PART.get(part)
    if jn:
        q = e["q"][jn][4 * k:4 * k + 4]
        p = e["p"][3 * k:3 * k + 3] if jn == "Root" else (0, 0, 0)
    else:
        q, p = (0, 0, 0, 1), (0, 0, 0)
    kids = "".join(pose_xml(c, k, e) for c in CHILDREN.get(part, []))
    return (f'<Item class="Pose" referent="{rid()}"><Properties><string name="Name">{part}</string>'
            f'<CoordinateFrame name="CFrame">{cf_xml(q, p)}</CoordinateFrame><float name="Weight">1</float>'
            f'<token name="EasingStyle">0</token><token name="EasingDirection">0</token></Properties>{kids}</Item>')


items = []
for name, e in EXPORT.items():
    kfs = []
    for k in range(e["n"]):
        t = (k / e["n"] if e["loop"] else k / (e["n"] - 1)) * e["dur"]
        kfs.append(f'<Item class="Keyframe" referent="{rid()}"><Properties><string name="Name">Keyframe</string>'
                   f'<float name="Time">{t:.4f}</float></Properties>{pose_xml("HumanoidRootPart", k, e)}</Item>')
    if e["loop"]:  # close the loop with a copy of the first pose at the end
        kfs.append(f'<Item class="Keyframe" referent="{rid()}"><Properties><string name="Name">Keyframe</string>'
                   f'<float name="Time">{e["dur"]:.4f}</float></Properties>{pose_xml("HumanoidRootPart", 0, e)}</Item>')
    prio = 0 if name in ("Idle", "TiredIdle") else (1 if name in GAITS or name == "Fall" else 2)
    items.append(f'<Item class="KeyframeSequence" referent="{rid()}"><Properties><string name="Name">NC_{name}</string>'
                 f'<bool name="Loop">{"true" if e["loop"] else "false"}</bool><token name="Priority">{prio}</token></Properties>'
                 + "".join(kfs) + "</Item>")
with open(os.path.join(OUT, "NeonCoastAnimations.rbxmx"), "w", encoding="utf-8") as f:
    f.write('<roblox version="4"><Item class="Folder" referent="RBXA0"><Properties><string name="Name">NeonCoastAnimations</string>'
            '</Properties>' + "".join(items) + "</Item></roblox>")

stats = {"reach_over_studs": {k: round(v, 3) for k, v in STATS["over"].items()},
         "clips": {k: {"dur": e["dur"], "samples": e["n"], "loop": e["loop"], "stride": e.get("stride")} for k, e in EXPORT.items()},
         "lua_chars": len(src)}
with open(os.path.join(OUT, "anims.json"), "w") as f:
    json.dump(stats, f, indent=1)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "NeonCoast_Animations.blend"))
print("NEONCOAST_ANIMS", json.dumps(stats))

# ------------------------------------------------------------------------------------------------ previews
if os.environ.get("NC_ANIM_RENDER", "1") == "1":
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.display.shading.light = "STUDIO"
    scene.display.shading.color_type = "MATERIAL"
    scene.display.shading.show_shadows = True
    scene.display.shading.show_cavity = True
    scene.render.resolution_x, scene.render.resolution_y = 960, 540
    world = bpy.data.worlds.new("W")
    world.color = (0.62, 0.74, 0.86)
    scene.world = world
    for i in range(-30, 260):                               # 1-stud stripes along the run: shows planted feet
        box_obj(f"G{i}", Vector((10, 1.0, 0.1)), "GroundA" if i % 2 else "GroundB", Vector((0, i + 0.5, -0.05)))
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
    label_c.materials.append(mat("Face"))
    frames_dir = os.path.join(os.environ.get("TEMP", OUT), "nc_anim_frames")
    shutil.rmtree(frames_dir, ignore_errors=True)
    os.makedirs(frames_dir, exist_ok=True)
    obstacles = []

    def obstacle(kind):
        for o in obstacles:
            bpy.data.objects.remove(o, do_unlink=True)
        obstacles.clear()
        if kind == "fence":
            obstacles.append(box_obj("Fence", Vector((6, 0.3, 3.2)), "Fence", Vector((0, 3.15, 1.6))))
        elif kind == "wall":
            obstacles.append(box_obj("Wall", Vector((6, 3.0, 3.8)), "Wall", Vector((0, 4.5, 1.9))))
        elif kind == "tall":
            obstacles.append(box_obj("TallFence", Vector((6, 0.3, 6.8)), "Fence", Vector((0, 3.15, 3.4))))

    def path_keys(kind):
        # the same paths MovementClient plans (HRP centre: s along the run, height y); the obstacle face is 3 ahead
        hitD, rootH = 3.0, 3.0
        if kind == "Vault":
            top, depth = 3.2, 0.3
            return [(0, 0, 3.0, ""), (0.38, hitD - 0.2, top + 1.55, "out"), (0.8, hitD + depth + 0.4, top + 1.45, ""), (1.0, hitD + depth + 1.1, top + 1.1, "in")]
        if kind == "Mantle":
            top = 3.8
            return [(0, 0, 3.0, ""), (0.45, hitD - 0.25, top + 1.0, "out"), (1.0, hitD + 1.3, top + rootH, "")]
        top, depth = 6.8, 0.3
        return [(0, 0, 3.0, ""), (0.26, hitD - 0.95, top - 2.9, "out"), (0.38, hitD - 0.92, top - 3.0, ""), (0.72, hitD - 0.3, top + 0.9, ""),
                (1.0, hitD + depth + 0.7, top + 1.5, "")]

    def path_at(keys, u):
        for i in range(len(keys) - 1):
            k0, k1 = keys[i], keys[i + 1]
            if u <= k1[0] or i == len(keys) - 2:
                s = clamp((u - k0[0]) / max(k1[0] - k0[0], 1e-3), 0, 1)
                e = (1 - (1 - s) ** 2) if k1[3] == "out" else (s * s if k1[3] == "in" else s * s * (3 - 2 * s))
                return k0[1] + (k1[1] - k0[1]) * s, k0[2] + (k1[2] - k0[2]) * e
        return keys[-1][1], keys[-1][2]

    SHOW = [("Idle", 1.0, "Idle: breathing, weight shifting"), ("Walk", 3, "Walk 5 studs/s"), ("Jog", 4, "Jog 16 studs/s"),
            ("Sprint", 5, "Sprint 25 studs/s"), ("Skid", 1, "Sprint stop: skid"), ("TiredIdle", 2, "Out of breath"),
            ("JumpUp", 1, "Jump"), ("Fall", 1, "Falling"), ("Land", 1, "Soft landing"), ("LandHard", 1, "Hard landing"),
            ("Roll", 1, "Landing roll"), ("Vault", 1, "Vault a fence"), ("Mantle", 1, "Mantle a wall"), ("Climb", 1, "Climb over a fence"),
            ("GetUp", 1, "Getting up"), ("Bump", 1, "Running into a wall"), ("Pivot", 1, "Plant and turn")]
    idx = 0
    sheet_frames = {}
    for (name, reps, text) in SHOW:
        use_action(name)
        act, dur, loop = ACTIONS[name]
        slow = 1.0 if name in ("Idle", "TiredIdle", "Fall", "Walk") else 2.0          # quick moves shown at half speed
        label_c.body = text + ("  (half speed)" if slow > 1 else "")
        total = int(round(dur * reps * FPS * slow))
        obstacle({"Vault": "fence", "Mantle": "wall", "Climb": "tall"}.get(name))
        pk = path_keys(name) if name in ("Vault", "Mantle", "Climb") else None
        for i in range(total + 1):
            tt = (i / FPS) / slow
            u = (tt / dur) % 1.0 if loop else min(1.0, tt / dur)
            f = u * dur * FPS
            scene.frame_set(int(math.floor(f)), subframe=f - math.floor(f))
            if name in GAITS:
                y, z = GAITS[name]["v"] * tt, 0.0
            elif name == "Skid":
                y, z = 25 * tt - 0.5 * 40 * tt * tt if tt < 0.625 else 7.8, 0.0
            elif name == "Roll":
                y, z = 14 * tt - 4.5 * tt * tt, 0.0
            elif pk:
                s, hy = path_at(pk, u)
                y, z = s, hy - 3.0
            else:
                y, z = 0.0, 0.0
            arm.location = (0, y, z)
            cam.location = (15.0, y + 1.0, 2.8 + max(0.0, z) * 0.7)
            cam.rotation_euler = (math.radians(88), 0, math.radians(90))
            scene.render.filepath = os.path.join(frames_dir, f"f{idx:05d}.png")
            bpy.ops.render.render(write_still=True)
            sheet_frames.setdefault(name, []).append(scene.render.filepath)
            idx += 1
    with open(os.path.join(frames_dir, "sheets.json"), "w") as f:
        json.dump(sheet_frames, f)
    print("NEONCOAST_FRAMES", idx, frames_dir)
