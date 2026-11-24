"""preview_ink.py <blend> <Body> <map.json> <out.glb>: body + ink layers with PNGs, for three.js previews.
map.json: {"Ink_LeftUpperArm": "/path.png", ...}"""
import bpy, sys, json
a = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
blend, name, mp, out = a[:4]
bpy.ops.wm.open_mainfile(filepath=blend)
M = json.load(open(mp))
for o in bpy.data.objects: o.select_set(False)
geo = [o for o in bpy.data.objects if o.name.startswith(name + "_") and o.name.endswith("_Geo")]
for g in geo:
    g.hide_set(False); g.hide_viewport = False; g.select_set(True)
w = geo[0]
mats = {}
for spot, png in M.items():
    ob = bpy.data.objects.get(f"{name}__{spot}")
    if ob is None or not png: continue
    if png not in mats:
        mt = bpy.data.materials.new("Ink_" + spot); mt.use_nodes = True
        nt = mt.node_tree; bsdf = nt.nodes["Principled BSDF"]
        im = nt.nodes.new("ShaderNodeTexImage"); im.image = bpy.data.images.load(png); im.extension = "CLIP"
        nt.links.new(im.outputs["Color"], bsdf.inputs["Base Color"]); nt.links.new(im.outputs["Alpha"], bsdf.inputs["Alpha"])
        bsdf.inputs["Roughness"].default_value = 0.6
        try: mt.blend_method = "BLEND"
        except Exception: pass
        mt.surface_render_method = "BLENDED" if hasattr(mt, "surface_render_method") else None
        mats[png] = mt
    ob.data.materials.clear(); ob.data.materials.append(mats[png]); ob.select_set(True)
bpy.context.view_layer.objects.active = w
bpy.ops.export_scene.gltf(filepath=out, use_selection=True, export_apply=True, export_yup=True)
