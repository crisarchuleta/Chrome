# Neon Coast downtown test block (the city realism check, like build_street.py for the suburbs):
#   blender --background --factory-startup --python build_cityblock.py        (NC_QA=only -> checks, no renders)
# A divided avenue (4 lanes + a landscaped median) crossing a 2-lane street with parallel parking, 14-stud
# sidewalks with royal palms in tree grates, cobra-head street lights, mast-arm traffic signals, ladder crosswalks,
# stop bars and lane paint; the Art Deco hotel, the two mid-rises and the office tower on the corners.
# Renders previews/CityBlock_*.png, including a night shot where the neon glows.
import sys, json, os, math, random
sys.path.insert(0, r"C:\Users\Crisa\Documents\NeonCoast_Blender")
import importlib, nc_kit, nc_extra, nc_detail
importlib.reload(nc_kit)
importlib.reload(nc_extra)
importlib.reload(nc_detail)
from nc_extra import *
import bpy

reset()
random.seed(11)
D = r"C:\Users\Crisa\Documents\NeonCoast_Blender"
city_meta = json.load(open(os.path.join(D, "city.json")))
props_meta = json.load(open(os.path.join(D, "props.json")))
INST = [0]


def import_glb(name):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=os.path.join(D, name + ".glb"))
    objs = [o for o in bpy.data.objects if o not in before and o.type == "MESH"]
    for o in objs:
        o.hide_render = True
        o.hide_set(True)
    return objs


def place(objs, x, y, rot=0.0, offset_x=0.0, z=0.0, kind="prop", label=None):
    INST[0] += 1
    tag = f"{label or objs[0].name.split('_')[0]}#{INST[0]}"
    c, s = math.cos(rot), math.sin(rot)
    for o in objs:
        n = o.copy()
        bpy.context.scene.collection.objects.link(n)
        t = o.matrix_world.translation
        e = o.matrix_world.to_euler("XYZ")
        lx, ly = t.x - offset_x, t.y
        n.location = (x + lx * c - ly * s, y + lx * s + ly * c, t.z + z)
        n.rotation_mode = "XYZ"
        n.rotation_euler = (e.x, e.y, e.z + rot)
        n.hide_render = False
        n.hide_set(False)
        n["style"] = "City"
        n["inst"] = tag
        n["qa"] = kind
    return tag


MATS = {}


def mat(name, rgb):
    if name not in MATS:
        m = bpy.data.materials.new(name)
        m.diffuse_color = (*nc_kit.lin(rgb), 1)
        MATS[name] = m
    return MATS[name]


def flat(name, x0, y0, x1, y1, z0, z1, rgb, kind="surface"):
    x0, x1 = sorted((x0, x1))
    y0, y1 = sorted((y0, y1))
    bpy.ops.mesh.primitive_cube_add(size=1, location=((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2))
    o = bpy.context.active_object
    o.scale = (x1 - x0, y1 - y0, z1 - z0)
    o.data.materials.append(mat(name, rgb))
    o["style"] = "City"
    o["qa"] = kind
    INST[0] += 1
    o["inst"] = f"{name}#{INST[0]}"
    o.name = name
    return o


# ---------------------------------------------------------------- streets
EXT = 260.0
AW, MED, SW = 24.0, 8.0, 14.0            # avenue: 24 each way (2 lanes), an 8-stud median; 14-stud sidewalks
CW = 18.0                                # cross street: 9 each way (lane) + 8 parking each side
A_HALF = AW + MED / 2                    # 28: avenue curb line
C_HALF = CW / 2 + 8.0                    # 17: cross street curb line (lane + parking)
ASPH, CONC, CURB = (0.20, 0.20, 0.21), (0.80, 0.79, 0.76), (0.72, 0.71, 0.68)
flat("Ground", -EXT - 40, -EXT - 40, EXT + 40, EXT + 40, -0.6, 0.0, (0.40, 0.42, 0.40))
flat("Avenue", -EXT, -A_HALF, EXT, A_HALF, 0.0, 0.05, ASPH)
flat("Cross", -C_HALF, -EXT, C_HALF, EXT, 0.0, 0.05, ASPH)
for s in (-1, 1):
    # median (raised, planted) except through the intersection
    for (a, b) in ((-EXT, -C_HALF - 6.0), (C_HALF + 6.0, EXT)):
        flat("MedianCurb", a, -MED / 2, b, MED / 2, 0.0, 0.55, CURB) if s > 0 else None
        flat("MedianGrass", a + 0.6, -MED / 2 + 0.6, b - 0.6, MED / 2 - 0.6, 0.55, 0.65, (0.30, 0.50, 0.24)) if s > 0 else None
    # sidewalks with curbs, corner by corner (they wrap the four blocks)
    for t in (-1, 1):
        x0, x1 = sorted((t * C_HALF, t * EXT))
        y0, y1 = sorted((s * A_HALF, s * EXT))
        flat("Sidewalk", x0, y0, x1, y1, 0.0, 0.32, CONC)
for s in (-1, 1):                        # paint: lane lines, double yellow, stop bars, ladder crosswalks
    WHITE, YEL = (0.95, 0.95, 0.93), (0.95, 0.80, 0.20)
    for (a, b) in ((-EXT, -C_HALF - 14.0), (C_HALF + 14.0, EXT)):
        x = a
        while x + 6 < b:
            flat("LaneDash", x, s * (MED / 2 + AW / 2) - 0.2, x + 6.0, s * (MED / 2 + AW / 2) + 0.2, 0.05, 0.07, WHITE)
            x += 18.0
    for (a, b) in ((-EXT, -A_HALF - 14.0), (A_HALF + 14.0, EXT)):
        for off in (-0.45, 0.45):
            flat("CenterLine", off - 0.15, a, off + 0.15, b, 0.05, 0.07, YEL)
    # stop bars on the inbound (right-hand) lanes of each approach
    flat("StopBar", s * (C_HALF + 12.6), s * (MED / 2), s * (C_HALF + 13.4), s * A_HALF, 0.05, 0.07, WHITE)
    flat("StopBar", -s * C_HALF, s * (A_HALF + 12.6), 0.0, s * (A_HALF + 13.4), 0.05, 0.07, WHITE)
    for k in range(int((2 * A_HALF) // 3)):
        y = -A_HALF + 0.5 + k * 3.0
        flat("Crosswalk", s * (C_HALF + 2.0) - 4.0, y, s * (C_HALF + 2.0) + 4.0, y + 1.6, 0.05, 0.07, WHITE)
    for k in range(int((2 * C_HALF) // 3)):
        x = -C_HALF + 0.5 + k * 3.0
        flat("Crosswalk", x, s * (A_HALF + 2.0) - 4.0, x + 1.6, s * (A_HALF + 2.0) + 4.0, 0.05, 0.07, WHITE)
    for (a, b) in ((-EXT, -A_HALF - 14.0), (A_HALF + 14.0, EXT)):  # parking stall ticks on the cross street
        y = a
        while y < b:
            flat("ParkLine", s * (C_HALF - 8.0) - 0.15, y, s * (C_HALF - 8.0) + 0.15, y + 1.5, 0.05, 0.07, WHITE)
            y += 24.0

# ---------------------------------------------------------------- traffic signals (mast arms on the four corners)
SIG = {"Pole": (0.25, 0.26, 0.28), "Head": (0.12, 0.12, 0.12), "Red": (0.9, 0.1, 0.1), "Amber": (0.95, 0.7, 0.1), "Green": (0.1, 0.85, 0.3)}


def signal(cx, cy, arm_dir, arm_len):
    """Mast-arm signal: pole on the corner, an arm reaching over the lanes, two 3-light heads hanging from it,
    a pedestrian signal on the pole."""
    INST[0] += 1
    tag = f"Signal#{INST[0]}"
    objs = []

    def b(name, x0, y0, z0, x1, y1, z1, col):
        o = flat(name, min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1), z0, z1, SIG[col], kind="prop")
        o["inst"] = tag
        objs.append(o)
    b("SigPole", cx - 0.5, cy - 0.5, 0.32, cx + 0.5, cy + 0.5, 22.0, "Pole")
    ax, ay = arm_dir
    ex, ey = cx + ax * arm_len, cy + ay * arm_len
    b("SigArm", min(cx, ex) - 0.25 * (ay != 0), min(cy, ey) - 0.25 * (ax != 0), 20.6,
      max(cx, ex) + 0.25 * (ay != 0), max(cy, ey) + 0.25 * (ax != 0), 21.2, "Pole")
    for f in (0.55, 0.9):
        hx, hy = cx + ax * arm_len * f, cy + ay * arm_len * f
        b("SigHead", hx - 0.6, hy - 0.6, 16.6, hx + 0.6, hy + 0.6, 20.6, "Head")
        face = (-ay, ax)                          # lights face the oncoming traffic
        for k, col in enumerate(("Red", "Amber", "Green")):
            z = 19.9 - k * 1.2
            px, py = hx + face[0] * 0.62, hy + face[1] * 0.62
            b("SigLamp", px - 0.35, py - 0.35, z - 0.35, px + 0.35, py + 0.35, z + 0.35, col)
    b("SigPed", cx + 0.5, cy - 0.5, 9.0, cx + 1.6, cy + 0.5, 11.0, "Head")
    return tag


signal(C_HALF + 2.0, A_HALF + 2.0, (0, -1), 20.0)
signal(-C_HALF - 2.0, -A_HALF - 2.0, (0, 1), 20.0)
signal(-C_HALF - 2.0, A_HALF + 2.0, (1, 0), 14.0)
signal(C_HALF + 2.0, -A_HALF - 2.0, (-1, 0), 14.0)

# ---------------------------------------------------------------- buildings
bld = {n: import_glb(n) for n in ("DecoHotel", "MidRiseBrick", "MidRiseStucco", "OfficeTower")}


def front_y(style):
    """distance from the origin to the furthest front element (terrace steps, canopy posts) along -Y"""
    return -city_meta[style]["extents_studs"]["y"][0]


# (corner buildings put their windowed side to the cross street; the hotel's fire escape gets an alley)
W0 = C_HALF + SW + 2.0
LOTS = [  # (style, x, side): side +1 = north of the avenue facing it (-Y), -1 = south facing +Y
    ("DecoHotel", W0 + 36.0, 1), ("MidRiseBrick", W0 + 36.0 + 39.0 + 10.0 + 29.8, 1),
    ("MidRiseStucco", W0 + 36.0 + 39.0 + 10.0 + 59.6 + 10.0 + 29.8, 1), ("OfficeTower", -(W0 + 46.0), 1),
    ("DecoHotel", W0 + 36.0, -1), ("MidRiseStucco", W0 + 36.0 + 35.0 + 10.0 + 29.8, -1),
    ("MidRiseBrick", -(W0 + 29.8), -1), ("MidRiseStucco", -(W0 + 59.6 + 10.0 + 29.8), -1),
]
FACE = A_HALF + SW                       # building line: the back of the sidewalk
PLACED = []
for (style, x, side) in LOTS:
    if style == "DecoHotel":
        y = FACE + front_y(style) - 0.4      # terrace steps at the building line
    elif style == "OfficeTower":
        y = FACE + 35.0                      # podium on the line, canopy over the sidewalk
    else:
        y = FACE + 22.0                      # storefronts on the line, awnings over the sidewalk
    rot = 0.0 if side > 0 else math.pi
    place(bld[style], x, side * y, rot, z=0.32, kind="house", label=style)
    PLACED.append((style, x, side * y, rot))

# ---------------------------------------------------------------- street furniture
props_objs = import_glb("StreetProps")
props = {}
for o in props_objs:
    props.setdefault(o.name.split("_")[0], []).append(o)
P = lambda name, x, y, r=0.0, z=0.32: place(props[name], x, y, r, props_meta[name]["offsetX"], z)
for s in (-1, 1):
    for t in (-1, 1):
        x = t * (C_HALF + 12.0)
        while abs(x) < EXT - 10:
            # sabal palm in a tree grate (an open frame round the trunk) at the curb edge: its crown stays over
            # the sidewalk, clear of balconies and facades; skipped under the office tower's entrance canopy
            gy = s * (A_HALF + 2.0)                                             # grate right at the curb
            balcony = any(st.startswith("MidRise") and (py_ > 0) == (s > 0) and abs(x - px_) < 13.0 for (st, px_, py_, _) in PLACED)
            if not (s > 0 and -101.0 < x < -57.0) and not balcony:
                for (a0, b0, a1, b1) in ((x - 2.0, gy - 2.0, x + 2.0, gy - 1.4), (x - 2.0, gy + 1.4, x + 2.0, gy + 2.0),
                                         (x - 2.0, gy - 1.4, x - 1.4, gy + 1.4), (x + 1.4, gy - 1.4, x + 2.0, gy + 1.4)):
                    o = flat("TreeGrate", a0, b0, a1, b1, 0.32, 0.36, (0.15, 0.15, 0.16), kind="prop")
                    o["inst"] = f"TreeGrate@{round(x)},{round(gy)}"
                P("QueenPalm", x, gy, 0.35 + (abs(x) * 0.0) + (0.0 if s > 0 else math.pi), 0.32)   # a frond gap faces the building
            x += t * 36.0
        for k, x in enumerate((t * (C_HALF + 30.0), t * (C_HALF + 102.0), t * (C_HALF + 174.0))):   # between the palms
            P("StreetLight", x, s * (A_HALF + 1.5), 0.0 if s > 0 else math.pi)
    P("Hydrant", 83.0 * s, s * (A_HALF + 1.6))
    P("TrashBin", -50.0 * s, s * (A_HALF + 11.0))
for (x, y) in ((40.0, 0.0), (90.0, 0.0), (140.0, 0.0), (190.0, 0.0), (-60.0, 0.0), (-110.0, 0.0), (-160.0, 0.0)):
    P("RoyalPalm", x, y, random.uniform(0, 6.28), 0.65)                 # royal palms down the median, Miami style

if os.environ.get("NC_QA"):
    import nc_qa
    importlib.reload(nc_qa)
    nc_qa.run(os.path.join(D, "qa_cityblock.json"))
    if os.environ.get("NC_QA") == "only":
        print("NEONCOAST_DONE qa")
        raise SystemExit

scene, cam = setup_render()
scene.render.resolution_x, scene.render.resolution_y = 1600, 900
render_views(scene, cam, ["City"], {
    "street": ((-8, -24, 6.5), (120, 40, 26)),
    "corner": ((-48, -60, 14), (40, 60, 30)),
    "aerial": ((-160, -260, 230), (40, 40, 20)),
    "tower": ((40, -50, 6), (-70, 60, 90)),
}, "CityBlock")

# night: emissive neon and signal lamps in EEVEE (if this Blender can run it headless)
try:
    scene.render.engine = "BLENDER_EEVEE_NEXT" if "BLENDER_EEVEE_NEXT" in bpy.types.RenderSettings.bl_rna.properties["engine"].enum_items.keys() else "BLENDER_EEVEE"
    for m in bpy.data.materials:
        m.use_nodes = True
        bsdf = m.node_tree.nodes.get("Principled BSDF")
        if not bsdf:
            continue
        base = m.diffuse_color
        glow = any(k in m.name for k in ("Neon", "Lamp", "SigLamp", "Red", "Amber", "Green"))
        if m.name.endswith("_Glass"):                      # lit rooms behind the windows
            bsdf.inputs["Emission Color"].default_value = (1.0, 0.82, 0.55, 1)
            bsdf.inputs["Emission Strength"].default_value = 1.2
        if glow:
            bsdf.inputs["Emission Color"].default_value = (base[0], base[1], base[2], 1)
            bsdf.inputs["Emission Strength"].default_value = 18.0
        else:
            bsdf.inputs["Base Color"].default_value = (base[0], base[1], base[2], 1)
    scene.world.use_nodes = True
    bg = scene.world.node_tree.nodes.get("Background")
    if bg:
        bg.inputs["Color"].default_value = (0.01, 0.015, 0.04, 1)
        bg.inputs["Strength"].default_value = 1.0
    sun = bpy.data.lights.new("Moon", "SUN")
    sun.energy = 0.25
    sun.color = (0.6, 0.7, 1.0)
    so = bpy.data.objects.new("Moon", sun)
    so.rotation_euler = (math.radians(60), 0, math.radians(30))
    scene.collection.objects.link(so)
    try:
        scene.eevee.use_bloom = True
    except Exception:
        pass
    render_views(scene, cam, ["City"], {"night": ((-10, -20, 10), (69, 53, 42)), "night_shops": ((96, 20, 6), (172, 44, 12))}, "CityBlock")
except Exception as ex:
    print("NIGHT_RENDER_SKIPPED", ex)
print("NEONCOAST_DONE cityblock")
