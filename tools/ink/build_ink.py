"""build_ink.py: tattoo layers for the rigged MakeHuman bodies.

Every tattoo spot gets a thin skin-hugging copy of that body part's skin (lifted ~1 mm, same bone weights, so it bends
exactly with the skin) with its own clean UVs. A tattoo is then just a transparent PNG printed on that copy (MeshPart
TextureID in Roblox), so it sits flush like the car vinyls: no raised geometry, no stretching.

Canvases (identical on every body, so one PNG fits all ten):
  Arm   768x1024  shoulder joint (top) -> wrist (bottom); x = distance around the arm, centred on the outside of the arm,
                  isotropic, scaled by the arm length. Upper arm and forearm are separate meshes on the same canvas,
                  so a full sleeve is one picture and half sleeves / forearm pieces mix freely.
  Leg   640x1024  hip joint -> ankle, centred on the outside of the leg (only skin below the shorts is printed).
  Hand  512x1024  back of the hand, wrist (bottom) -> fingertips (top), planar.
  Neck  1024x384  around the neck, centred on the throat, chin line (top) -> collar (bottom).
  Face  768x1024  front of the face, planar.

Run: python build_ink.py <rig.blend> <outdir>   (bpy 5.x as a module, or blender -b -P build_ink.py -- ...)
Out:  NC_Ink_<Body>.fbx (armature + Ink_<Spot> meshes), ink_canvas.json, and NC_InkPreview_<Body>.glb helpers.
"""
import bpy, sys, os, json, math
import numpy as np

args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
SRC = args[0] if args else "/tmp/claude-0/garm/rig_tank.blend"
OUT = args[1] if len(args) > 1 else "/tmp/claude-0/ink/out"
ONLY = args[2].split(",") if len(args) > 2 else None
os.makedirs(OUT, exist_ok=True)

BODIES = [f"{g}_{b}" for g in ("Male", "Female") for b in ("Skinny", "Average", "Athletic", "Muscular", "Heavy")]
LIFT = 0.0011          # metres off the skin (scaled to studs per body)
CANVAS = {"Arm": (768, 1024, 0.75), "Leg": (640, 1024, 0.625), "Hand": (512, 1024), "Neck": (1024, 384), "Face": (768, 1024)}
# physical spans (metres on a 1.78 m body) for the planar / neck canvases
HAND_W, HAND_H = 0.115, 0.23
NECK_W, NECK_H = 0.44, 0.165
NECK_TOP = 0.05       # canvas top above the chin line (fraction of k)
FACE_W, FACE_H = 0.19, 0.2533


def joints(arm):
    b = arm.data.bones
    h = lambda n: np.array(b[n].head_local[:])
    t = lambda n: np.array(b[n].tail_local[:])
    J = {"head": h("Head"), "neck_mid": h("NC_NeckMid") if "NC_NeckMid" in b else h("Head")}
    for S in ("Left", "Right"):
        s = S[0]
        J[s + "sh"] = h(S + "UpperArm"); J[s + "el"] = h(S + "LowerArm"); J[s + "wr"] = h(S + "Hand")
        J[s + "tip"] = t(f"NC_Middle{s.upper()}3") if f"NC_Middle{s.upper()}3" in b else t(S + "Hand")
        J[s + "hip"] = h(S + "UpperLeg"); J[s + "kn"] = h(S + "LowerLeg"); J[s + "an"] = h(S + "Foot")
    return J


def mesh_arrays(ob):
    me = ob.data
    V = np.array([v.co[:] for v in me.vertices])
    N = np.array([v.normal[:] for v in me.vertices])
    return me, V, N


def make_overlay(src, name, keep_face, uv_of, lift):
    """copy src (a skinned _Geo part), keep faces where keep_face(poly) is True, lift along normals, set UVs"""
    me0, V, N = mesh_arrays(src)
    polys = [p for p in me0.polygons if keep_face(p)]
    if len(polys) < 3:
        return None
    # UVs per face corner (a face straddling the wrap seam is unwrapped on one side)
    face_uv = []
    for p in polys:
        uvs = np.array([uv_of(V[v] + N[v] * lift) for v in p.vertices])
        if uvs[:, 0].max() - uvs[:, 0].min() > 0.5:
            uvs[uvs[:, 0] < 0.5, 0] += 1.0 * WRAP[0]
        face_uv.append(uvs)
    # drop faces whose UVs span a big part of the canvas (part caps / fans across the cut, never real skin):
    # they would squeeze a whole row of the design into a thin line. Dropping only removes ink, never shows a hole.
    keep = [i for i, uvs in enumerate(face_uv) if np.ptp(uvs[:, 0]) < 0.22 and np.ptp(uvs[:, 1]) < 0.22]
    polys = [polys[i] for i in keep]; face_uv = [face_uv[i] for i in keep]
    if len(polys) < 3:
        return None
    used = sorted({v for p in polys for v in p.vertices})
    remap = {v: i for i, v in enumerate(used)}
    me = bpy.data.meshes.new(name)
    Vn = V[used] + N[used] * lift
    me.from_pydata([tuple(x) for x in Vn], [], [[remap[v] for v in p.vertices] for p in polys])
    me.update()
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    ob.parent = src.parent
    ob.matrix_parent_inverse = src.matrix_parent_inverse.copy()
    ob.matrix_basis = src.matrix_basis.copy()
    # bone weights: identical to the skin underneath
    for g in src.vertex_groups:
        ob.vertex_groups.new(name=g.name)
    gi = {g.index: g.name for g in src.vertex_groups}
    for v in used:
        for g in me0.vertices[v].groups:
            ob.vertex_groups[gi[g.group]].add([remap[v]], g.weight, "REPLACE")
    md = ob.modifiers.new("Armature", "ARMATURE"); md.object = src.parent if src.parent and src.parent.type == "ARMATURE" else [m for m in src.modifiers if m.type == "ARMATURE"][0].object
    # UVs per loop (seams handled per face)
    uvl = me.uv_layers.new(name="UVMap")
    for p, uvs in zip(me.polygons, face_uv):   # from_pydata keeps face order and corner order
        uvs = np.clip(uvs, 0.002, 0.998)   # outside the canvas -> its transparent border (textures repeat in Roblox)
        for li, uv in zip(p.loop_indices, uvs):
            uvl.data[li].uv = (float(uv[0]), float(uv[1]))
    return ob


WRAP = [1.0]


def cyl_frame(a, b_, side_out, view_right, L, Wfrac, Rfun=None):
    """cylindrical canvas along a->b: v 0 at a, 1 at b (scaled by L), u = arc length around / L, centred on side_out."""
    ax = (b_ - a) / np.linalg.norm(b_ - a)
    out = side_out - ax * np.dot(side_out, ax); out /= np.linalg.norm(out)
    rt = np.cross(ax, out)
    if np.dot(rt, view_right) < 0:
        rt = -rt

    def f(p, R=None):
        d = p - a
        t = np.dot(d, ax)
        q = d - ax * t
        r = np.linalg.norm(q) + 1e-9
        th = math.atan2(np.dot(q, rt), np.dot(q, out))
        Rr = Rfun(t / L) if Rfun else r
        u = th * Rr / L
        return u, t / L
    return f, ax, out, rt


def build_body(name, keep_objs):
    arm = bpy.data.objects["NC_" + name]
    J = joints(arm)
    whole = bpy.data.objects[name + "_Whole"]
    Vw = np.array([v.co[:] for v in whole.data.vertices])
    H = Vw[:, 2].max() - Vw[:, 2].min()
    k = H / 1.78
    lift = LIFT * k
    parts = {o.name[len(name) + 1:-4]: o for o in bpy.data.objects if o.name.startswith(name + "_") and o.name.endswith("_Geo")}
    skin_mi = 0
    made = []
    front = np.array([0, -1.0, 0])
    for S in ("Left", "Right"):
        s = S[0]
        sgn = 1 if J[s + "sh"][0] > 0 else -1
        lateral = np.array([sgn, 0, 0.0])
        # viewer's right when looking at the outside of this limb from outside (z up)
        view_right = np.cross(-lateral, np.array([0, 0, 1.0]))
        # ---- arm: one canvas shoulder joint -> wrist
        La = np.linalg.norm(J[s + "el"] - J[s + "sh"]) + np.linalg.norm(J[s + "wr"] - J[s + "el"])
        W_, H_, Wf = CANVAS["Arm"]
        # radius profile along the arm (from the skin) so u is true arc length at every height
        f0, ax, outv, rt = cyl_frame(J[s + "sh"], J[s + "wr"], lateral + np.array([0, 0, 0.0]), view_right, La, Wf)
        ap = np.vstack([np.array([v.co[:] for v in parts[S + p].data.vertices]) for p in ("UpperArm", "LowerArm")])
        ts = np.array([np.dot(p - J[s + "sh"], ax) / La for p in ap])
        rs = np.array([np.linalg.norm((p - J[s + "sh"]) - ax * np.dot(p - J[s + "sh"], ax)) for p in ap])
        bins = np.linspace(-0.1, 1.1, 25)
        prof = np.array([np.median(rs[(ts >= bins[i]) & (ts < bins[i + 1])]) if ((ts >= bins[i]) & (ts < bins[i + 1])).sum() > 3 else np.nan for i in range(24)])
        mid = (bins[:-1] + bins[1:]) / 2
        ok = ~np.isnan(prof)
        Rfun = lambda t, mid=mid[ok], pr=prof[ok]: float(np.interp(t, mid, pr))
        f, *_ = cyl_frame(J[s + "sh"], J[s + "wr"], lateral, view_right, La, Wf, Rfun)

        def uv_arm(p, f=f, Wf=Wf):
            u, v = f(p)
            return np.array([u / Wf + 0.5, 1.0 - v])
        for p in ("UpperArm", "LowerArm"):
            ob = make_overlay(parts[S + p], f"Ink_{S}{p}", lambda pl: pl.material_index == skin_mi, uv_arm, lift)
            if ob: made.append(ob)
        # ---- leg: hip joint -> ankle (only bare skin below the shorts gets printed)
        Ll = np.linalg.norm(J[s + "kn"] - J[s + "hip"]) + np.linalg.norm(J[s + "an"] - J[s + "kn"])
        W_, H_, Wf = CANVAS["Leg"]
        lp = np.vstack([np.array([v.co[:] for v in parts[S + p].data.vertices]) for p in ("UpperLeg", "LowerLeg")])
        f0, ax, *_ = cyl_frame(J[s + "hip"], J[s + "an"], lateral, view_right, Ll, Wf)
        ts = np.array([np.dot(p - J[s + "hip"], ax) / Ll for p in lp])
        rs = np.array([np.linalg.norm((p - J[s + "hip"]) - ax * np.dot(p - J[s + "hip"], ax)) for p in lp])
        prof = np.array([np.median(rs[(ts >= bins[i]) & (ts < bins[i + 1])]) if ((ts >= bins[i]) & (ts < bins[i + 1])).sum() > 3 else np.nan for i in range(24)])
        ok = ~np.isnan(prof)
        Rl = lambda t, mid=mid[ok], pr=prof[ok]: float(np.interp(t, mid, pr))
        f, *_ = cyl_frame(J[s + "hip"], J[s + "an"], lateral, view_right, Ll, Wf, Rl)

        def uv_leg(p, f=f, Wf=Wf):
            u, v = f(p)
            return np.array([u / Wf + 0.5, 1.0 - v])
        for p in ("UpperLeg", "LowerLeg"):
            ob = make_overlay(parts[S + p], f"Ink_{S}{p}", lambda pl: pl.material_index == skin_mi, uv_leg, lift)
            if ob: made.append(ob)
        # ---- hand: planar on the back of the hand
        wr, tip = J[s + "wr"], J[s + "tip"]
        hx = (tip - wr) / np.linalg.norm(tip - wr)
        hp = parts[S + "Hand"]
        _, Vh, Nh = mesh_arrays(hp)
        # back of the hand normal: the side the knuckles bulge toward (mean normal of the upper half, minus hx part)
        up_guess = np.array([0, 0, 1.0])
        dors = up_guess - hx * np.dot(up_guess, hx)
        nm = Nh[np.dot(Nh, dors) > 0].mean(0); nm -= hx * np.dot(nm, hx); dors = nm / np.linalg.norm(nm)
        side = np.cross(dors, hx)  # across the hand, as seen from above the back of the hand
        if np.dot(side, view_right) < 0 and False:
            side = -side

        def uv_hand(p, wr=wr, hx=hx, side=side):
            d = p - wr
            return np.array([np.dot(d, side) / (HAND_W * k) + 0.5, np.dot(d, hx) / (HAND_H * k) + 0.06])
        Nd = Nh @ dors
        ob = make_overlay(hp, f"Ink_{S}Hand", lambda pl, Nd=Nd: pl.material_index == skin_mi and np.mean([Nd[v] for v in pl.vertices]) > 0.25, uv_hand, lift)
        if ob: made.append(ob)
    # ---- neck: cylinder around the neck, centred on the throat
    head = parts["Head"]
    _, Vh, Nh = mesh_arrays(head)
    nb = J["head"]
    chin_z = nb[2] + 0.075 * k
    neck_c = np.array([nb[0], Vh[(Vh[:, 2] > nb[2] - 0.01 * k) & (Vh[:, 2] < nb[2] + 0.03 * k), 1].mean(), 0.0])

    def uv_neck(p, c=neck_c):
        th = math.atan2(p[0] - c[0], -(p[1] - c[1]))  # 0 at the throat, positive to the character's left
        R = math.hypot(p[0] - c[0], p[1] - c[1])   # true arc length (the neck is not round)
        return np.array([th * R / (NECK_W * k) + 0.5, 1.0 - (top_z - p[2]) / (NECK_H * k)])

    top_z = chin_z + NECK_TOP * k   # canvas top sits under the ears so side-neck pieces have room

    def neck_face(pl, V=None):
        c_ = pl.center
        if pl.material_index != skin_mi:
            return False
        jaw_z = chin_z - 0.05 * k
        if c_[2] < jaw_z:
            return True
        # higher up: under-jaw, sides and back of the neck only (never the chin/jaw front, which belong to the face)
        if c_[2] > top_z or pl.normal[2] > 0.5:
            return False
        if c_[1] < neck_c[1] and abs(c_[0] - neck_c[0]) < 0.06 * k:
            return pl.normal[2] < -0.4 and c_[2] < chin_z - 0.025 * k
        return pl.normal[1] > -0.45
    for src in ("Head", "UpperTorso"):
        ob = make_overlay(parts[src], f"Ink_Neck{src}", neck_face, uv_neck, lift)
        if ob: made.append(ob)
    # ---- face: planar from the front
    eye_z = nb[2] + 0.15 * k

    def uv_face(p):
        return np.array([(p[0] - nb[0]) / (FACE_W * k) + 0.5, (p[2] - chin_z) / (FACE_H * k) + 0.06])
    ob = make_overlay(head, "Ink_Face", lambda pl: pl.material_index == skin_mi and pl.center[2] >= chin_z and pl.normal[1] < -0.35, uv_face, lift)
    if ob: made.append(ob)
    return made, arm, k


def main():
    bpy.ops.wm.open_mainfile(filepath=SRC)
    info = {"canvas": {k_: list(v) for k_, v in CANVAS.items()}, "bodies": {}}
    for name in (ONLY or BODIES):
        made, arm, k = build_body(name, None)
        info["bodies"][name] = {"k": k, "spots": [o.name for o in made]}
        # FBX: armature + ink layers (TextureID set by the game)
        for o in bpy.data.objects:
            o.select_set(False)
        arm.select_set(True)
        for o in made:
            o.select_set(True)
        bpy.context.view_layer.objects.active = arm
        bpy.ops.export_scene.fbx(filepath=os.path.join(OUT, f"NC_Ink_{name}.fbx"), use_selection=True,
                                 object_types={"ARMATURE", "MESH"}, apply_scale_options="FBX_SCALE_UNITS",
                                 add_leaf_bones=False, bake_anim=False, primary_bone_axis="Y", secondary_bone_axis="X",
                                 mesh_smooth_type="OFF")
        # keep the layers in a blend for previews (renamed per body)
        for o in made:
            o.name = f"{name}__{o.name}"
        print("NC_INK", name, len(made), flush=True)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "NeonCoast_Ink.blend"))
    json.dump(info, open(os.path.join(OUT, "ink_canvas.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
