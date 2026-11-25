"""build_swatches.py <libdir> <out.glb>: every tattoo PNG on its own plane (Swatch_<file>) so Studio uploads them."""
import bpy, sys, os, glob
a = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
lib, out = a[0], a[1]
bpy.ops.wm.read_factory_settings(use_empty=True)
files = sorted(glob.glob(os.path.join(lib, "*.png")))
for i, f in enumerate(files):
    stem = os.path.basename(f)[:-4]
    img = bpy.data.images.load(f)
    w, h = img.size
    sx, sy = w / 1024 * 2, h / 1024 * 2
    me = bpy.data.meshes.new("Swatch_" + stem)
    me.from_pydata([(-sx / 2, 0, -sy / 2), (sx / 2, 0, -sy / 2), (sx / 2, 0, sy / 2), (-sx / 2, 0, sy / 2)], [], [[0, 1, 2, 3]])
    uv = me.uv_layers.new(name="UVMap")
    for li, c in zip(range(4), [(0, 0), (1, 0), (1, 1), (0, 1)]):
        uv.data[li].uv = c
    ob = bpy.data.objects.new("Swatch_" + stem, me)
    bpy.context.scene.collection.objects.link(ob)
    ob.location = ((i % 20) * 2.2, 0, -(i // 20) * 2.2)
    mt = bpy.data.materials.new("Ink_" + stem); mt.use_nodes = True
    nt = mt.node_tree; bs = nt.nodes["Principled BSDF"]
    tx = nt.nodes.new("ShaderNodeTexImage"); tx.image = img
    nt.links.new(tx.outputs["Color"], bs.inputs["Base Color"]); nt.links.new(tx.outputs["Alpha"], bs.inputs["Alpha"])
    me.materials.append(mt)
bpy.ops.export_scene.gltf(filepath=out, export_format="GLB")
print("SWATCHES", len(files))
