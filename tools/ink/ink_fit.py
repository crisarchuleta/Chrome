# ink_fit.py <NeonCoast_Ink.blend from build_ink.py> <out.json>: measures where each ink layer sits on its R15 body part
# (centre offset and size as fractions of the part size, Roblox axes) for the Ink.FIT table in NCInk.lua.
import bpy, sys, numpy as np, json
bpy.ops.wm.open_mainfile(filepath=sys.argv[-2])
def bbox(ob):
    me = ob.data; co = np.empty(len(me.vertices) * 3); me.vertices.foreach_get("co", co); co = co.reshape(-1, 3)
    M = np.array(ob.matrix_world); co = co @ M[:3, :3].T + M[:3, 3]
    return co.min(0), co.max(0)
out = {}
for ob in bpy.data.objects:
    if "__Ink_" not in ob.name or ob.type != "MESH": continue
    body, layer = ob.name.split("__")
    pname = layer[4:]
    pname = {"NeckHead": "Head", "NeckUpperTorso": "UpperTorso", "Face": "Head"}.get(pname, pname)
    g = bpy.data.objects.get(f"{body}_{pname}_Geo")
    if g is None: print("missing", body, pname); continue
    a0, a1 = bbox(ob); b0, b1 = bbox(g)
    ca, cb = (a0 + a1) / 2, (b0 + b1) / 2; sb = b1 - b0; sa = a1 - a0
    d = (ca - cb) / sb; s = sa / sb
    # Blender (x, y, z) -> Roblox (-x, z, y); sizes have no sign
    out.setdefault(body, {})[layer] = [round(-d[0], 5), round(d[2], 5), round(d[1], 5), round(s[0], 5), round(s[2], 5), round(s[1], 5)]
# the R15 part sizes the fit was measured on (Roblox axes), so the game can warn when a body part differs
sizes = {}
for body in out:
    for pname in ("Head", "UpperTorso", "LeftUpperArm", "LeftLowerArm", "LeftHand", "LeftUpperLeg", "LeftLowerLeg",
                  "RightUpperArm", "RightLowerArm", "RightHand", "RightUpperLeg", "RightLowerLeg"):
        g = bpy.data.objects.get(f"{body}_{pname}_Geo")
        if g:
            b0, b1 = bbox(g); sb = b1 - b0
            sizes.setdefault(body, {})[pname] = [round(sb[0], 4), round(sb[2], 4), round(sb[1], 4)]
out = {"fit": out, "sizes": sizes}
json.dump(out, open(sys.argv[-1], "w"), indent=1)
print(len(out['fit']))
