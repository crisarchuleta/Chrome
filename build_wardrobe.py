# Neon Coast wardrobe builder (Blender 5.x, run headless):
#   blender -b -P build_wardrobe.py -- <rig.blend> <out_dir> [looks...]
# For every rigged MakeHuman body in the rig file (NeonCoast_MakeHumanRig.blend from build_makehuman_rig.py) it
# fits the reference outfits with nc_garments.py, gives the clothes the body's bone weights, and saves one
# NeonCoast_Wardrobe_<Body>.blend per body (each look in its own collection) plus game-ready FBX files
# (decimated, skinned to the R15 rig) for Roblox Studio's 3D importer.
# The permanent base layer (white tank, shorts, NC_Modesty) stays under every outfit: NO NUDITY, EVER.
import bpy, sys, os
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import nc_garments as NG
import nc_outfits as looks

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
RIG = argv[0] if argv else os.path.join(HERE, "NeonCoast_MakeHumanRig.blend")
OUT = argv[1] if len(argv) > 1 else os.path.join(HERE, "wardrobe")
WANT = argv[2:] or list(looks.LOOKS)
BODIES = [x for x in (os.environ.get("NC_BODIES") or "").split(",") if x] or ["Male_Skinny", "Male_Average", "Male_Athletic", "Male_Muscular", "Male_Heavy",
          "Female_Skinny", "Female_Average", "Female_Athletic", "Female_Muscular", "Female_Heavy"]
os.makedirs(os.path.join(OUT, "fbx"), exist_ok=True)

for body in BODIES:
    bpy.ops.wm.open_mainfile(filepath=RIG)
    # keep only this body and its rig
    for ob in list(bpy.data.objects):
        if ob.type in ("MESH", "ARMATURE") and not (ob.name.startswith(body + "_") or ob.name == "NC_" + body):
            bpy.data.objects.remove(ob, do_unlink=True)
    whole = bpy.data.objects[body + "_Whole"]
    arm = bpy.data.objects["NC_" + body]
    b = NG.RigBody(whole, arm)
    for li, look in enumerate(WANT):
        o = NG.Outfit(b)
        looks.LOOKS[look](o)
        NG.skin_to_rig(o)
        col = bpy.data.collections.new("Look_" + look)
        bpy.context.scene.collection.children.link(col)
        for ob in o.objs:
            for c in list(ob.users_collection):
                c.objects.unlink(ob)
            col.objects.link(ob)
        # game-ready FBX: rig + body parts + this look
        for ob in bpy.data.objects:
            ob.select_set(False)
        arm.select_set(True)
        for ob in bpy.data.objects:
            if ob.name.startswith(body + "_") and ob.name.endswith("_Geo"):
                ob.select_set(True)
        saved = []
        for ob in o.objs:
            saved.append([(m.name, m.type) for m in ob.modifiers])
            NG.game_ready(ob)
            ob.select_set(True)
        bpy.ops.export_scene.fbx(filepath=os.path.join(OUT, "fbx", f"NC_{body}_{look}.fbx"), use_selection=True,
                                 use_mesh_modifiers=True, add_leaf_bones=False, object_types={"ARMATURE", "MESH"},
                                 global_scale=1.0, apply_unit_scale=True)
        # back to the full-quality modifiers in the .blend
        for ob in o.objs:
            for m in list(ob.modifiers):
                if m.type == "DECIMATE":
                    ob.modifiers.remove(m)
            if not any(m.type == "SUBSURF" for m in ob.modifiers) and any(t == "SUBSURF" for _, t in saved[o.objs.index(ob)]):
                ss = ob.modifiers.new("Smooth", "SUBSURF"); ss.levels = 1
                while ob.modifiers.find(ss.name) > 1:
                    with bpy.context.temp_override(object=ob):
                        bpy.ops.object.modifier_move_up(modifier=ss.name)
        col.hide_viewport = li > 0
        col.hide_render = li > 0
        print("dressed", body, look, len(o.objs), "pieces", flush=True)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, f"NeonCoast_Wardrobe_{body}.blend"), compress=True)
print("WARDROBE DONE")
