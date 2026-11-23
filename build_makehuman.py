# Neon Coast bodies from MakeHuman (MPFB 2 add-on for Blender): realistic adult men and women in the five fitness
# builds the game uses (Skinny, Average, Athletic, Muscular, Heavy), made from MakeHuman's own body shape sliders
# (gender, age, muscle, weight, height, proportions). MakeHuman output is CC0: free to use and sell in the game.
# Every body is dressed by nc_baselayer.py (undershirt + boxer shorts + NC_Modesty shape key): no nude body is ever saved.
#   blender --background --python build_makehuman.py        (NOT --factory-startup: that would switch the add-on off)
# Out: previews/MakeHuman_lineup_front.png, _threequarter.png, _faces.png; NeonCoast_MakeHuman.blend
import bpy, os, sys, math
from mathutils import Vector

OUT = r"C:\Users\Crisa\Documents\NeonCoast_Blender"
PREV = os.path.join(OUT, "previews")
os.makedirs(PREV, exist_ok=True)

sys.path.insert(0, OUT)
import nc_baselayer  # NO NUDITY: permanent undershirt + shorts and a modesty shape key on every body
from bl_ext.user_default.mpfb.services.humanservice import HumanService
from bl_ext.user_default.mpfb.services.targetservice import TargetService

bpy.ops.wm.read_homefile(use_empty=True)
scene = bpy.context.scene

BUILDS = {  # MakeHuman macro sliders (0..1) for each fitness build
    "Skinny": dict(muscle=0.30, weight=0.12),
    "Average": dict(muscle=0.50, weight=0.50),
    "Athletic": dict(muscle=0.78, weight=0.36),
    "Muscular": dict(muscle=1.00, weight=0.62),
    "Heavy": dict(muscle=0.42, weight=1.00),
}
GENDERS = {"Male": 1.0, "Female": 0.0}
SKIN = {"Male": (0.78, 0.58, 0.45, 1), "Female": (0.86, 0.66, 0.54, 1)}

humans = []
x = 0.0
for g_name, g in GENDERS.items():
    for b_name, b in BUILDS.items():
        macro = TargetService.get_default_macro_info_dict()
        macro["gender"] = g
        macro["age"] = 0.5            # about 25
        macro["height"] = 0.55 if g > 0.5 else 0.45
        macro["proportions"] = 0.6
        macro["muscle"] = b["muscle"]
        macro["weight"] = b["weight"]
        h = HumanService.create_human(macro_detail_dict=macro)
        h.name = f"{g_name}_{b_name}"
        h.location.x = x
        mat = bpy.data.materials.new(h.name + "_Skin")
        mat.diffuse_color = SKIN[g_name]
        h.data.materials.clear()
        h.data.materials.append(mat)
        for poly in h.data.polygons:
            poly.use_smooth = True
        nc_baselayer.add_base_layer(h, female=g < 0.5)
        humans.append(h)
        x += 0.75
    x += 0.6
print("NEONCOAST_MH", [h.name for h in humans], [round(h.dimensions.z, 3) for h in humans])

# ------------------------------------------------------------------------------------------------ previews
scene.render.engine = "BLENDER_WORKBENCH"
scene.display.shading.light = "STUDIO"
scene.display.shading.color_type = "MATERIAL"
scene.display.shading.show_shadows = True
scene.display.shading.show_cavity = True
scene.display.shading.cavity_type = "BOTH"
scene.render.resolution_x, scene.render.resolution_y = 1920, 820
world = bpy.data.worlds.new("W")
world.color = (0.62, 0.74, 0.86)
scene.world = world
bpy.ops.mesh.primitive_plane_add(size=40, location=(x / 2, 0, 0))
cam_d = bpy.data.cameras.new("Cam")
cam_d.lens = 40
cam = bpy.data.objects.new("Cam", cam_d)
scene.collection.objects.link(cam)
scene.camera = cam
mid = (x - 0.6) / 2


def shot(name, loc, tgt, res=None):
    if res:
        scene.render.resolution_x, scene.render.resolution_y = res
    cam.location = loc
    cam.rotation_euler = (Vector(tgt) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
    scene.render.filepath = os.path.join(PREV, f"MakeHuman_{name}.png")
    bpy.ops.render.render(write_still=True)


shot("lineup_front", (mid, -9.5, 1.0), (mid, 0, 0.9))
shot("lineup_threequarter", (mid - 4.5, -8.0, 1.6), (mid, 0, 0.85))
# faces: the average man and woman up close
male = bpy.data.objects["Male_Average"]
female = bpy.data.objects["Female_Average"]
shot("face_male", (male.location.x + 0.25, -0.75, 1.68), (male.location.x, 0, 1.62), (1000, 1000))
shot("face_female", (female.location.x + 0.25, -0.75, 1.58), (female.location.x, 0, 1.52), (1000, 1000))
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "NeonCoast_MakeHuman.blend"))
print("NEONCOAST_MH_DONE")
