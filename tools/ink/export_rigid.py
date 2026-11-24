# export_rigid.py <NeonCoast_Ink.blend> <outdir>: writes NC_Ink_<Body>.fbx with the 13 ink layers as plain rigid
# meshes (no armature, no skin weights). In game each layer is welded to its own R15 part (NCInk.Attach + Ink.FIT),
# which avoids the importer's skinning bug that scattered the ink on skinned layers.
import bpy, sys, os
args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[-2:]
bpy.ops.wm.open_mainfile(filepath=args[0])
out = args[1]; os.makedirs(out, exist_ok=True)
bodies = sorted({o.name.split("__")[0] for o in bpy.data.objects if "__Ink_" in o.name})
for body in bodies:
    made = []
    for o in [o for o in bpy.data.objects if o.name.startswith(body + "__Ink_") and o.type == "MESH"]:
        me = o.data.copy()
        n = bpy.data.objects.new(o.name.split("__")[1], me)
        bpy.context.scene.collection.objects.link(n)
        n.matrix_world = o.matrix_world.copy()
        n.vertex_groups.clear()
        made.append(n)
    for o in bpy.data.objects:
        o.select_set(False)
    for n in made:
        n.select_set(True)
    bpy.context.view_layer.objects.active = made[0]
    bpy.ops.export_scene.fbx(filepath=os.path.join(out, f"NC_Ink_{body}.fbx"), use_selection=True, object_types={"MESH"},
                             apply_scale_options="FBX_SCALE_UNITS", mesh_smooth_type="OFF", use_armature_deform_only=False,
                             add_leaf_bones=False, bake_anim=False)
    for n in made:
        bpy.data.objects.remove(n, do_unlink=True)
    print("rigid", body, len(made), flush=True)
