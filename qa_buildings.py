# House-level checks (details over openings, through roofs, gutters/downspouts, loose pieces) for the models that
# aren't on the test street: the safe house, the plaza shop, the school, the pool and the floaty, home props.
#   blender --background --factory-startup --python qa_buildings.py      -> qa_buildings.json
import sys, os, json, importlib
sys.path.insert(0, r"C:\Users\Crisa\Documents\NeonCoast_Blender")
import bpy
import nc_qa
importlib.reload(nc_qa)

D = r"C:\Users\Crisa\Documents\NeonCoast_Blender"
bpy.ops.wm.read_factory_settings(use_empty=True)
for glb in ("SafeHouse", "Shop", "SchoolMain", "SchoolWing", "Pool", "HomeProps", "DecoHotel", "MidRiseBrick", "MidRiseStucco", "OfficeTower"):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=os.path.join(D, glb + ".glb"))
    for o in bpy.data.objects:
        if o not in before and o.type == "MESH":
            style = o.name.split("_")[0]
            o["qa"] = "house"
            o["inst"] = f"{style}#1"
nc_qa.run(os.path.join(D, "qa_buildings.json"))
