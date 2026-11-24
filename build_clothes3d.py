# Game export of the 3D catalog clothes (Top / Outer / Bottom) for the ten MakeHuman bodies.
#
#   python -I build_clothes3d.py <rig.blend> <out_dir> [ids,comma,separated | all] [bodies,comma,separated | all]
#
# One FBX per body and item: NC_Cloth_<Body>__<itemId>.fbx with the body's armature (same bone names and axes as
# NC_Body_<Body>.fbx) and the item as skinned meshes, already game-ready (decimated to the budget, patterns cut on
# the low-poly mesh). Each colour is its own mesh object, named
#     <itemId>__<role>__<key>__<n>
# where key says which catalog colour it takes at run time: c1, c2, mix (half way), or fix (keep the colour baked
# in the FBX, e.g. camo patches and zip teeth). NCClothes3D.lua reads those names; AssembleClothes3D.lua files the
# imported meshes under ReplicatedStorage.NC_Clothes3D.<Body>.<itemId>. A clothes3d_index.json lists every file.
import bpy, sys, os, json, time
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import nc_garments as NG
import nc_catalog3d as CM

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
RIG = argv[0] if argv else os.path.join(HERE, "NeonCoast_MakeHumanRig.blend")
OUT = argv[1] if len(argv) > 1 else os.path.join(HERE, "clothes3d")
WANT = argv[2] if len(argv) > 2 else "all"
BODIES = argv[3] if len(argv) > 3 else "all"
ALL_BODIES = ["Male_Skinny", "Male_Average", "Male_Athletic", "Male_Muscular", "Male_Heavy",
              "Female_Skinny", "Female_Average", "Female_Athletic", "Female_Muscular", "Female_Heavy"]
bodies = ALL_BODIES if BODIES == "all" else BODIES.split(",")
items = {it["id"]: it for it in CM.load(os.path.join(HERE, "NCLookCatalog.lua"))}
ids = [i for i, it in items.items() if it["slot"] in ("Top", "Outer", "Bottom")] if WANT == "all" else WANT.split(",")
os.makedirs(OUT, exist_ok=True)


def colour_key(rgb, it):
    c1 = np.array(it["c1"][:3]); c2 = np.array((it["c2"] or it["c1"])[:3]); rgb = np.array(rgb[:3])
    for key, ref in (("c1", c1), ("c2", c2), ("mix", 0.5 * c1 + 0.5 * c2)):
        if np.abs(rgb - ref).max() < 0.02:
            return key
    return "fix"


def split_by_material(ob, it, n0=0):
    """Apply the decimation, then one object per colour (Roblox gives each MeshPart one colour)."""
    for m in list(ob.modifiers):
        if m.type == "DECIMATE":
            with bpy.context.temp_override(object=ob, active_object=ob):
                bpy.ops.object.modifier_apply(modifier=m.name)
    used = sorted({p.material_index for p in ob.data.polygons})
    out = []
    for mi in used:
        me = ob.data.copy()
        import bmesh
        bm = bmesh.new(); bm.from_mesh(me)
        bmesh.ops.delete(bm, geom=[f for f in bm.faces if f.material_index != mi], context="FACES")
        bm.to_mesh(me); bm.free()
        mat = ob.data.materials[mi]
        for p in me.polygons:
            p.material_index = 0
        me.materials.clear(); me.materials.append(mat)
        role = mat.name[len(it["id"]) + 1:] if mat.name.startswith(it["id"] + "_") else mat.name
        nm = f'{it["id"]}__{role}__{colour_key(mat.diffuse_color, it)}__{n0 + len(out) + 1}'
        part = bpy.data.objects.new(nm, me)
        for c in ob.users_collection:
            c.objects.link(part)
        for m in ob.modifiers:
            if m.type == "ARMATURE":
                a = part.modifiers.new("Armature", "ARMATURE"); a.object = m.object
            # no Solidify in the game copy: it doubles the triangles and adds a rim at every colour border; the
            # installer sets DoubleSided on the MeshParts instead, so the inside of a sleeve still renders
        part.matrix_world = ob.matrix_world.copy()
        out.append(part)
    return out


index = {}
t0 = time.time()
for body in bodies:
    bpy.ops.wm.open_mainfile(filepath=RIG)
    for ob in list(bpy.data.objects):
        if ob.type in ("MESH", "ARMATURE") and not (ob.name.startswith(body + "_") or ob.name == "NC_" + body):
            bpy.data.objects.remove(ob, do_unlink=True)
    whole = bpy.data.objects[body + "_Whole"]; arm = bpy.data.objects["NC_" + body]
    b = NG.RigBody(whole, arm)
    for i in ids:
        it = items.get(i)
        if not it:
            continue
        o = NG.Outfit(b)
        if not CM.build_item(o, it):
            continue
        NG.skin_to_rig(o)
        parts = []
        for ob in o.objs:
            NG.game_ready(ob)
            parts += split_by_material(ob, it, len(parts))
        for ob in parts:  # parent to the armature, keep where they are
            mw = ob.matrix_world.copy(); ob.parent = arm; ob.matrix_world = mw
        for ob in bpy.data.objects:
            ob.select_set(False)
        arm.select_set(True)
        for ob in parts:
            ob.select_set(True)
        bpy.context.view_layer.objects.active = arm
        fn = f"NC_Cloth_{body}__{i}.fbx"
        bpy.ops.export_scene.fbx(filepath=os.path.join(OUT, fn), use_selection=True, use_mesh_modifiers=True,
                                 object_types={"ARMATURE", "MESH"}, apply_scale_options="FBX_SCALE_UNITS",
                                 add_leaf_bones=False, bake_anim=False, primary_bone_axis="Y", secondary_bone_axis="X",
                                 mesh_smooth_type="FACE")
        dg = bpy.context.evaluated_depsgraph_get()
        tris = 0
        for ob in parts:
            me = ob.evaluated_get(dg).to_mesh(); tris += sum(len(p.vertices) - 2 for p in me.polygons); ob.evaluated_get(dg).to_mesh_clear()
        index.setdefault(body, {})[i] = dict(file=fn, parts=[ob.name for ob in parts], tris=tris,
                                              bytes=os.path.getsize(os.path.join(OUT, fn)))
        for ob in parts + o.objs:
            bpy.data.objects.remove(ob, do_unlink=True)
        print("CLOTH", body, i, "parts", len(parts), "tris", tris, "%.0fs" % (time.time() - t0), flush=True)
    json.dump(index, open(os.path.join(OUT, "clothes3d_index.json"), "w"), indent=1)
print("DONE", sum(len(v) for v in index.values()), "files")
