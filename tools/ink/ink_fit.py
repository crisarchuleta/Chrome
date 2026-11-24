# ink_fit.py <NeonCoast_Ink.blend from build_ink.py> <NeonCoast_MakeHumanRig.blend the game bodies came from> <out.json>
# Measures where each ink layer sits on its R15 body part (centre offset and size as fractions of the part size,
# Roblox axes) for Ink.FIT in NCInk.lua, plus the part sizes for Ink.PART_SIZE. Use the SAME rig blend the bodies in
# Studio were imported from: the parts' split (and so their size and centre) changes between rig builds.
import bpy, sys, numpy as np, json
ink_blend, rig_blend, out_path = sys.argv[-3:]


def bbox(ob):
    me = ob.data; co = np.empty(len(me.vertices) * 3); me.vertices.foreach_get("co", co); co = co.reshape(-1, 3)
    M = np.array(ob.matrix_world); co = co @ M[:3, :3].T + M[:3, 3]
    return co.min(0), co.max(0)


PART = {"NeckHead": "Head", "NeckUpperTorso": "UpperTorso", "Face": "Head"}
bpy.ops.wm.open_mainfile(filepath=ink_blend)
layers = {}
for ob in bpy.data.objects:
    if "__Ink_" in ob.name and ob.type == "MESH":
        body, layer = ob.name.split("__")
        layers.setdefault(body, {})[layer] = bbox(ob)
bpy.ops.wm.open_mainfile(filepath=rig_blend)
fit, sizes = {}, {}
for body, ls in layers.items():
    for layer, (a0, a1) in ls.items():
        pname = PART.get(layer[4:], layer[4:])
        g = bpy.data.objects.get(f"{body}_{pname}_Geo")
        if g is None:
            print("missing", body, pname); continue
        b0, b1 = bbox(g)
        sb = b1 - b0
        d = ((a0 + a1) / 2 - (b0 + b1) / 2) / sb; s = (a1 - a0) / sb
        # Blender (x, y, z) -> Roblox (-x, z, y); sizes have no sign
        fit.setdefault(body, {})[layer] = [round(-d[0], 5), round(d[2], 5), round(d[1], 5), round(s[0], 5), round(s[2], 5), round(s[1], 5)]
        sizes.setdefault(body, {})[pname] = [round(sb[0], 4), round(sb[2], 4), round(sb[1], 4)]
json.dump({"fit": fit, "sizes": sizes}, open(out_path, "w"), indent=1)
print(len(fit), "bodies")
