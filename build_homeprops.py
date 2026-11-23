# Neon Coast interactive home furniture (for the safe house and any interior), Blender headless:
#   blender --background --factory-startup --python build_homeprops.py
# Every prop faces -Y (its front), origin at the floor (the ceiling fan: origin at the ceiling). Pieces are named
# <Prop>_<Role>; the roles the game scripts look for: Blades (spins), Bulb (glows), Screen (the TV picture),
# DoorL / DoorR (swing open), plus a Spout point for the sink. One GLB, props spaced along X (homeprops.json).
import sys, json, os, math
sys.path.insert(0, r"C:\Users\Crisa\Documents\NeonCoast_Blender")
import importlib, nc_kit, nc_extra, nc_detail
importlib.reload(nc_kit)
importlib.reload(nc_extra)
importlib.reload(nc_detail)
from nc_extra import *
from nc_detail import beam
import bpy

reset()
nc_kit.COLORS.update({
    "Body": (0.85, 0.82, 0.76), "Blades": (0.45, 0.30, 0.18), "Bulb": (0.98, 0.95, 0.85), "Screen": (0.05, 0.05, 0.07),
    "Frame": (0.08, 0.08, 0.09), "DoorL": (0.62, 0.45, 0.30), "DoorR": (0.62, 0.45, 0.30), "Counter": (0.90, 0.88, 0.84),
    "Basin": (0.70, 0.72, 0.74), "Faucet": (0.80, 0.80, 0.82), "Shade": (0.95, 0.92, 0.84), "Cabinet": (0.30, 0.42, 0.50),
    "Wood": (0.42, 0.30, 0.20), "Metal": (0.18, 0.18, 0.20),
})


def cyl(H, kind, x, y, z0, z1, r0, r1=None, sides=12):
    r1 = r0 if r1 is None else r1
    v = []
    for z, r in ((z0, r0), (z1, r1)):
        for k in range(sides):
            a = 2 * math.pi * k / sides
            v.append((x + r * math.cos(a), y + r * math.sin(a), z))
    f = [tuple(range(sides - 1, -1, -1)), tuple(range(sides, 2 * sides))]
    for k in range(sides):
        j = (k + 1) % sides
        f.append((k, j, sides + j, sides + k))
    H.p(kind).solid(v, f)


PROPS = []


def prop(fn):
    PROPS.append(fn)
    return fn


@prop
def CeilingFan():
    H = House("CeilingFan")
    cyl(H, "Body", 0, 0, -0.35, 0.0, 0.7, 0.6)                  # canopy at the ceiling
    cyl(H, "Body", 0, 0, -2.2, -0.35, 0.12)                     # downrod
    cyl(H, "Body", 0, 0, -3.2, -2.2, 0.9, 0.75)                  # motor
    for k in range(4):                                           # 4 blades: symmetric, so it spins true
        a = k * math.pi / 2
        d = (math.cos(a), math.sin(a))
        beam(H, "Blades", (d[0] * 0.6, d[1] * 0.6, -2.95), (d[0] * 1.4, d[1] * 1.4, -2.95), 0.5, 0.12)
        beam(H, "Blades", (d[0] * 1.3, d[1] * 1.3, -3.0), (d[0] * 5.6, d[1] * 5.6, -3.15), 1.3, 0.1, up=(0, 0, 1))
    cyl(H, "Body", 0, 0, -3.5, -3.2, 0.75, 0.75)
    cyl(H, "Bulb", 0, 0, -4.1, -3.5, 0.75, 0.35)                 # light bowl
    return H, {"tags": ["NC_Fan", "NC_Light"], "origin": "ceiling"}


@prop
def FloorLamp():
    H = House("FloorLamp")
    cyl(H, "Metal", 0, 0, 0, 0.25, 1.0)
    cyl(H, "Metal", 0, 0, 0.25, 6.6, 0.1)
    cyl(H, "Bulb", 0, 0, 6.4, 7.0, 0.3)
    cyl(H, "Shade", 0, 0, 6.2, 8.0, 1.3, 0.9, sides=16)
    return H, {"tags": ["NC_Light"]}


@prop
def TV():
    H = House("TV")
    H.p("Wood").box(-4.2, -0.9, 0, 4.2, 0.9, 2.2)               # media console
    for x in (-2.1, 2.1):
        H.p("Frame").box(x - 1.9, -0.92, 0.3, x + 1.9, -0.9, 1.9)
    H.p("Metal").box(-1.0, -0.3, 2.2, 1.0, 0.3, 2.35)            # stand foot
    H.p("Metal").box(-0.2, -0.05, 2.35, 0.2, 0.15, 3.2)
    H.p("Frame").box(-3.5, -0.15, 3.0, 3.5, 0.15, 7.0)           # 65" class panel
    H.p("Screen").box(-3.38, -0.18, 3.12, 3.38, -0.15, 6.88)
    H.col(-4.2, -0.9, 0, 4.2, 0.9, 7.0, "furniture")
    return H, {"tags": ["NC_TV"], "screenFace": "Back"}


@prop
def Closet():
    H = House("Closet")
    H.p("Wood").box(-3.6, -1.2, 0, 3.6, 1.2, 0.3)
    H.p("Body").box(-3.6, -1.1, 0.3, -3.3, 1.2, 9.0)
    H.p("Body").box(3.3, -1.1, 0.3, 3.6, 1.2, 9.0)
    H.p("Body").box(-3.6, 0.9, 0.3, 3.6, 1.2, 9.0)
    H.p("Body").box(-3.6, -1.1, 8.7, 3.6, 1.2, 9.2)
    H.p("Body").box(-3.3, -1.0, 0.3, 3.3, 0.9, 0.5)
    H.p("Metal").box(-3.3, 0.3, 7.6, 3.3, 0.4, 7.7)              # hanging rod
    for x in (-2.4, -1.6, -0.8, 0.6, 1.4, 2.2):                  # shirts on hangers hooked over the rod
        H.p("Cabinet").box(x - 0.35, 0.05, 4.6, x + 0.35, 0.65, 7.35)
        H.p("Metal").box(x - 0.04, 0.28, 7.3, x + 0.04, 0.42, 7.8)
    for (name, a, b, hx) in (("DoorL", -3.3, -0.02, -0.6), ("DoorR", 0.02, 3.3, 0.6)):
        H.p(name).box(a, -1.2, 0.5, b, -1.05, 8.7)
        H.p(name).box(a + 0.3, -1.28, 1.0, b - 0.3, -1.2, 4.4)   # panels
        H.p(name).box(a + 0.3, -1.28, 4.9, b - 0.3, -1.2, 8.2)
        H.p(name).box(hx - 0.06, -1.42, 4.0, hx + 0.06, -1.28, 5.4)   # pull
    H.col(-3.6, -1.2, 0, 3.6, 1.2, 9.2, "furniture")
    return H, {"tags": ["NC_Closet"]}


@prop
def KitchenSink():
    H = House("KitchenSink")
    H.p("Cabinet").box(-3.0, -1.4, 0.3, 3.0, 1.4, 3.4)
    H.p("Wood").box(-3.0, -1.3, 0, 3.0, 1.4, 0.3)
    for x in (-1.5, 1.5):
        H.p("Frame").box(x - 1.35, -1.42, 0.6, x + 1.35, -1.4, 3.1)
        H.p("Faucet").box(x - 0.3, -1.55, 2.6, x + 0.3, -1.42, 2.7)
    # countertop with the basin cut in (four strips round the hole), steel basin under it
    H.p("Counter").box(-3.2, -1.6, 3.4, 3.2, -0.9, 3.7)
    H.p("Counter").box(-3.2, 0.9, 3.4, 3.2, 1.5, 3.7)
    H.p("Counter").box(-3.2, -0.9, 3.4, -1.6, 0.9, 3.7)
    H.p("Counter").box(1.6, -0.9, 3.4, 3.2, 0.9, 3.7)
    H.p("Basin").box(-1.6, -0.9, 2.3, 1.6, 0.9, 2.45)
    for (a0, b0, a1, b1) in ((-1.6, -0.9, 1.6, -0.8), (-1.6, 0.8, 1.6, 0.9), (-1.6, -0.9, -1.5, 0.9), (1.5, -0.9, 1.6, 0.9)):
        H.p("Basin").box(a0, b0, 2.3, a1, b1, 3.4)
    # gooseneck faucet
    cyl(H, "Faucet", 0, 1.15, 3.7, 4.0, 0.3)
    cyl(H, "Faucet", 0, 1.15, 4.0, 5.4, 0.12)
    beam(H, "Faucet", (0, 1.15, 5.4), (0, 0.7, 5.9), 0.24, 0.24)
    beam(H, "Faucet", (0, 0.7, 5.9), (0, 0.15, 5.6), 0.24, 0.24)
    beam(H, "Faucet", (0, 0.15, 5.6), (0, 0.1, 5.0), 0.22, 0.22)
    beam(H, "Faucet", (0.05, 1.15, 4.6), (0.9, 1.15, 4.75), 0.14, 0.14)   # handle, out of the faucet body
    H.notes["spout"] = [0.0, 0.1, 4.95]
    H.col(-3.2, -1.6, 0, 3.2, 1.5, 3.7, "furniture")
    return H, {"tags": ["NC_Sink"]}


@prop
def CarPanel():
    H = House("CarPanel")
    H.p("Frame").box(-1.2, -0.2, 4.0, 1.2, 0.0, 5.7)
    H.p("Screen").box(-1.0, -0.23, 4.2, 1.0, -0.2, 5.5)
    H.p("Metal").box(-0.5, -0.25, 3.7, 0.5, 0.0, 4.0)             # tray right under the frame
    return H, {"tags": ["NC_CarPanel"], "screenFace": "Back"}


meta = {}
x = 0.0
for ob in list(bpy.context.scene.objects):
    ob.select_set(False)
for fn in PROPS:
    H, info = fn()
    objs, tris = H.build()
    for ob in objs:
        ob.location.x += x
        ob["style"] = "HomeProps"
        ob.select_set(True)
    meta[H.style] = {"offsetX": x, "pieces": sorted(tris.keys()), "triangles": tris, "colliders": H.colliders, "notes": H.notes, **info}
    x += 16.0
bpy.ops.export_scene.gltf(filepath=os.path.join(OUT, "HomeProps.glb"), export_format="GLB", use_selection=True, export_apply=True, export_yup=True)
with open(os.path.join(OUT, "homeprops.json"), "w") as f:
    json.dump(meta, f)
scene, cam = setup_render()
render_views(scene, cam, ["HomeProps"], {"front": ((x * 0.45, -40, 9), (x * 0.45, 0, 4)), "above": ((x * 0.45, -28, 26), (x * 0.45, 0, 0))}, "HomeProps")
print("NEONCOAST_DONE", json.dumps({k: sum(v["triangles"].values()) for k, v in meta.items()}))
