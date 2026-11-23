# Turns the Blender export metadata (houses.json, safehouse.json, civic.json) into Roblox Luau:
#   BuildingKitData.lua  - colliders, doors, garage doors and markers per building, in Roblox-local studs
#   NeonCoastBuildingKit.rbxmx - BuildingKit (installer) + BuildingKitData + BuildingDoors (server script),
#                                ready to drop into ServerStorage / ServerScriptService
# Run with any Python 3 (or blender --background --python make_kit_data.py).
# Axis mapping (glTF default export, Y up): Roblox local (X, Y, Z) = Blender (x, z, -y).
import json, os

HERE = r"C:\Users\Crisa\Documents\NeonCoast_Blender"
SOURCES = ["houses.json", "florida.json", "safehouse.json", "civic.json", "city.json"]


def conv_pt(p):
    x, y, z = p
    return [round(x, 3), round(z, 3), round(-y, 3)]


def conv_box(mn, mx):
    a, b = conv_pt(mn), conv_pt(mx)
    return [min(a[0], b[0]), min(a[1], b[1]), min(a[2], b[2]), max(a[0], b[0]), max(a[1], b[1]), max(a[2], b[2])]


def lua(v, ind=""):
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (int, float)):
        return repr(round(v, 3)) if isinstance(v, float) else str(v)
    if isinstance(v, str):
        return json.dumps(v)
    if isinstance(v, list):
        if all(isinstance(x, (int, float, str)) and not isinstance(x, bool) for x in v):
            return "{" + ", ".join(lua(x) for x in v) + "}"
        return "{\n" + "".join(ind + "\t" + lua(x, ind + "\t") + ",\n" for x in v) + ind + "}"
    if isinstance(v, dict):
        items = []
        for k in sorted(v):
            key = k if k.isidentifier() else "[" + json.dumps(k) + "]"
            items.append(ind + "\t" + key + " = " + lua(v[k], ind + "\t") + ",\n")
        return "{\n" + "".join(items) + ind + "}"
    if v is None:
        return "nil"
    raise TypeError(type(v))


data = {}
for src in SOURCES:
    path = os.path.join(HERE, src)
    if not os.path.exists(path):
        continue
    with open(path) as f:
        meta = json.load(f)
    for style, m in meta.items():
        ext = m["extents_studs"]
        mn = conv_pt([ext["x"][0], ext["y"][0], ext["z"][0]])
        mx = conv_pt([ext["x"][1], ext["y"][1], ext["z"][1]])
        doors = []
        for d in m["doors"]:
            u0, v0 = d["min"]
            u1, v1 = d["max"]
            fixed = d["fixed"]
            if d["axis"] == "x":
                bmin, bmax = [u0, fixed - 0.2, v0], [u1, fixed + 0.2, v1]
                outward = [0, 0, -d["outward"]]          # Blender +-Y -> Roblox -+Z
            else:
                bmin, bmax = [fixed - 0.2, u0, v0], [fixed + 0.2, u1, v1]
                outward = [d["outward"], 0, 0]
            doors.append({
                "Kind": d["kind"], "Hinge": conv_pt(d["hinge"]), "Box": conv_box(bmin, bmax), "Outward": outward,
                "Width": d["width"], "Height": d["height"], "HingeAtStart": d["hingeAtStart"], "Pieces": d.get("pieces", []),
            })
        garages = []
        for g in m["notes"].get("garage", []):
            u0, v0 = g["min"]
            u1, v1 = g["max"]
            fixed = g["fixed"]
            if g["axis"] == "x":
                bmin, bmax = [u0, fixed - 0.4, v0], [u1, fixed + 0.4, v1]
            else:
                bmin, bmax = [fixed - 0.4, u0, v0], [fixed + 0.4, u1, v1]
            garages.append({"Box": conv_box(bmin, bmax), "Pieces": g.get("pieces", [])})
        windows = []
        for w in m.get("windows", []):
            u0, v0 = w["min"]
            u1, v1 = w["max"]
            fixed = w["fixed"]
            if w["axis"] == "x":
                bmin, bmax = [u0, fixed - 0.06, v0], [u1, fixed + 0.06, v1]
            else:
                bmin, bmax = [fixed - 0.06, u0, v0], [fixed + 0.06, u1, v1]
            inward = [0, 0, w["outward"]] if w["axis"] == "x" else [-w["outward"], 0, 0]
            windows.append({"Box": conv_box(bmin, bmax), "Inward": inward, "Slide": round((v1 - v0) * 0.85, 3), "Pieces": w.get("pieces", [])})
        # a ceiling light over every ceiling slab big enough to be a room (and under upper floors), grid on big ones
        lights = []
        for c in m["colliders"]:
            tag = c.get("tag")
            mn, mx = c["min"], c["max"]
            area = (mx[0] - mn[0]) * (mx[1] - mn[1])
            if (tag == "ceiling" or (tag == "floor" and mn[2] > 6.0)) and area > 150:
                nx, ny = max(1, round((mx[0] - mn[0]) / 40)), max(1, round((mx[1] - mn[1]) / 40))
                for i in range(nx):
                    for j in range(ny):
                        x = mn[0] + (mx[0] - mn[0]) * (i + 0.5) / nx
                        y = mn[1] + (mx[1] - mn[1]) * (j + 0.5) / ny
                        lights.append(conv_pt([x, y, mn[2] - 0.35]))
        notes = {}
        for k, v in m["notes"].items():
            if k in ("garage",):
                continue
            if k == "pool" and isinstance(v, dict):          # swimmable water box (the Florida ranch's caged pool)
                b = conv_box(v["min"], v["max"])
                notes[k] = {"Min": b[:3], "Max": b[3:]}
            elif k == "elevator" and isinstance(v, dict):    # the office tower's express car (Elevator script)
                sh = conv_box(v["shaft"]["min"], v["shaft"]["max"])
                (cx0, cy0), (cx1, cy1) = v["car"]["min"], v["car"]["max"]
                dy0, dy1 = v["door"]["y"]
                notes[k] = {
                    "ShaftMin": sh[:3], "ShaftMax": sh[3:],
                    "CarMin": [round(cx0, 3), 0, round(-cy1, 3)], "CarMax": [round(cx1, 3), 0, round(-cy0, 3)],
                    "Stop0": round(v["stops"][0], 3), "Stop1": round(v["stops"][1], 3),
                    "DoorX": round(v["door"]["x"], 3), "DoorZ0": round(-dy1, 3), "DoorZ1": round(-dy0, 3), "DoorH": round(v["door"]["h"], 3),
                    "Call0": conv_pt(v["call"][0]), "Call1": conv_pt(v["call"][1]),
                }
            elif isinstance(v, list) and v and isinstance(v[0], list) and len(v[0]) == 3:
                notes[k] = [conv_pt(p) for p in v]
            elif isinstance(v, list) and len(v) == 3 and all(isinstance(x, (int, float)) for x in v):
                notes[k] = conv_pt(v)
            else:
                notes[k] = v
        data[style] = {
            "Pieces": [p for p in m["pieces"]],
            "Extents": {"Min": mn and [min(mn[i], mx[i]) for i in range(3)], "Max": [max(mn[i], mx[i]) for i in range(3)]},
            "Colliders": [conv_box(c["min"], c["max"]) + [c.get("tag", "wall")] for c in m["colliders"]],
            "Doors": doors,
            "Garages": garages,
            "Windows": windows,
            "CeilingLights": lights,
            "Notes": notes,
            "Triangles": m["triangles"],
        }

hp_path = os.path.join(HERE, "homeprops.json")
if os.path.exists(hp_path):
    hp = {}
    for name, m in json.load(open(hp_path)).items():
        e = {"OffsetX": m["offsetX"], "Tags": m.get("tags", [])}
        if m.get("screenFace"):
            e["ScreenFace"] = m["screenFace"]
        if "spout" in m.get("notes", {}):
            e["Spout"] = conv_pt(m["notes"]["spout"])
        hp[name] = e
    data["_HomeProps"] = hp

pr_path = os.path.join(HERE, "props.json")
if os.path.exists(pr_path):
    ct = json.load(open(pr_path)).get("HalfCourt", {}).get("notes", {}).get("court")
    if ct:
        # points relative to the court's top centre (Kit.PrepareHalfCourt's Root, -Z toward the hoop)
        data["_HalfCourt"] = {
            "Rim": conv_pt(ct["rimRel"]), "BallSpawn": conv_pt(ct["ballSpawnRel"]), "Board": conv_pt(ct["boardRel"]),
            "BoardSize": [round(v, 3) for v in ct.get("boardSize", [6.9, 4.025, 0.15])],   # already Roblox X, Y, Z
            "RimRadius": round(ct["rimRadius"], 4), "ThreeRadius": round(ct["threeRadius"], 3),
            "Size": [round(ct["size"][0], 3), round(ct["size"][1], 3)],
        }

def extents_of(m):
    ext = m["extents_studs"]
    a = conv_pt([ext["x"][0], ext["y"][0], ext["z"][0]])
    b = conv_pt([ext["x"][1], ext["y"][1], ext["z"][1]])
    return {"Min": [min(a[i], b[i]) for i in range(3)], "Max": [max(a[i], b[i]) for i in range(3)]}


def box_of(d):
    b = conv_box(d["min"], d["max"])
    return {"Min": b[:3], "Max": b[3:]}


pl_path = os.path.join(HERE, "pool.json")
if os.path.exists(pl_path):
    import math
    pm = json.load(open(pl_path))
    bp = pm.get("BackyardPool")
    if bp:
        n = bp["notes"]
        slopes = []
        for s in n["slopes"]:
            (xa, za), (xb, zb) = s["p0"], s["p1"]
            L = math.hypot(xb - xa, zb - za)
            ang = math.atan2(zb - za, xb - xa)
            nx, nz = -math.sin(ang), math.cos(ang)            # the floor line's upward normal
            cx, cz = (xa + xb) / 2 - nx * 0.5, (za + zb) / 2 - nz * 0.5   # 1-stud slab under the line
            slopes.append({"Center": conv_pt([cx, (s["y0"] + s["y1"]) / 2, cz]), "Size": [round(L + 0.05, 3), 1.0, round(s["y1"] - s["y0"], 3)],
                           "AngleZ": round(ang, 5)})
        b = n["board"]
        bc = next(c for c in bp["colliders"] if c["tag"] == "board")
        data["_Pool"] = {
            "Extents": extents_of(bp),
            "Colliders": [conv_box(c["min"], c["max"]) + [c["tag"]] for c in bp["colliders"] if c["tag"] != "board"],
            "Slopes": slopes,
            "Water": box_of(n["water"]),
            "Cut": box_of(n["cut"]),
            "Board": {"Hinge": conv_pt(b["hinge"]), "Tip": conv_pt(b["tip"]), "Length": round(b["length"], 3), "Width": round(b["width"], 3),
                      "Pieces": b["pieces"], "Collider": conv_box(bc["min"], bc["max"])},
            "Lights": [{"Pos": conv_pt(l["pos"]), "Dir": conv_pt(l["dir"])} for l in n["poolLights"]],
        }
        if "spa" in n:
            data["_Pool"]["Spa"] = box_of(n["spa"])
        if "waterfall" in n:
            data["_Pool"]["Waterfall"] = {"Pos": conv_pt(n["waterfall"]["pos"]), "Top": n["waterfall"]["top"]}
    fl = pm.get("UnicornFloaty")
    if fl:
        nf = fl["notes"]["floaty"]
        nb = conv_box(nf["neck"]["min"], nf["neck"]["max"])
        data["_Floaty"] = {"Extents": extents_of(fl), "RingRadius": nf["ringRadius"], "TubeRadius": nf["tubeRadius"],
                           "HoleRadius": nf["holeRadius"], "NeckMin": nb[:3], "NeckMax": nb[3:]}

pc_path = os.path.join(HERE, "parachute.json")
if os.path.exists(pc_path):
    pc = json.load(open(pc_path))
    data["_Parachute"] = {k: {"Extents": extents_of(m)} for k, m in pc.items()}
    if "ParachutePack" in data["_Parachute"]:
        # the container's centre (build_parachute.py: x +-0.85, y 0.05..0.75, z -1.2..0.9), from the mount point
        data["_Parachute"]["ParachutePack"]["Center"] = conv_pt([0.0, 0.4, -0.15])

src = ("-- BuildingKitData: generated by make_kit_data.py from the Blender exports. Do not hand-edit; re-run it.\n"
       "-- Roblox-local studs for each building model (origin = the Blender origin, ground at Y = 0; Roblox (X, Y, Z) = Blender (x, z, -y)).\n"
       "-- Colliders: {x0, y0, z0, x1, y1, z1, tag}. Doors: hinge point, the leaf's box, which way is outside, the mesh pieces that swing.\n"
       "return " + lua(data) + "\n")
with open(os.path.join(HERE, "BuildingKitData.lua"), "w", encoding="utf-8") as f:
    f.write(src)


def cdata(s):
    return "<![CDATA[" + s.replace("]]>", "]]]]><![CDATA[>") + "]]>"


def read(name):
    with open(os.path.join(HERE, name), encoding="utf-8") as f:
        return f.read()


kit_src = read("BuildingKit.lua")
doors_src = read("BuildingDoors.server.lua")
xml = ('<roblox version="4">'
       '<Item class="Folder" referent="RBX0"><Properties><string name="Name">NeonCoastBuildingKit</string></Properties>'
       '<Item class="ModuleScript" referent="RBX1"><Properties><string name="Name">BuildingKit</string>'
       '<ProtectedString name="Source">' + cdata(kit_src) + '</ProtectedString></Properties>'
       '<Item class="ModuleScript" referent="RBX2"><Properties><string name="Name">BuildingKitData</string>'
       '<ProtectedString name="Source">' + cdata(src) + '</ProtectedString></Properties></Item></Item>'
       '<Item class="Script" referent="RBX3"><Properties><string name="Name">BuildingDoors</string>'
       '<ProtectedString name="Source">' + cdata(doors_src) + '</ProtectedString></Properties></Item>'
       '<Item class="Script" referent="RBX4"><Properties><string name="Name">HouseInteractables</string>'
       '<ProtectedString name="Source">' + cdata(read("HouseInteractables.server.lua")) + '</ProtectedString></Properties></Item>'
       '<Item class="LocalScript" referent="RBX5"><Properties><string name="Name">HouseClient</string>'
       '<ProtectedString name="Source">' + cdata(read("HouseClient.client.lua")) + '</ProtectedString></Properties></Item>'
       '<Item class="Script" referent="RBX6"><Properties><string name="Name">Basketball</string>'
       '<ProtectedString name="Source">' + cdata(read("Basketball.server.lua")) + '</ProtectedString></Properties></Item>'
       '<Item class="LocalScript" referent="RBX7"><Properties><string name="Name">BasketballClient</string>'
       '<ProtectedString name="Source">' + cdata(read("BasketballClient.client.lua")) + '</ProtectedString></Properties></Item>'
       '<Item class="Script" referent="RBX8"><Properties><string name="Name">PoolService</string>'
       '<ProtectedString name="Source">' + cdata(read("PoolService.server.lua")) + '</ProtectedString></Properties></Item>'
       '<Item class="LocalScript" referent="RBX9"><Properties><string name="Name">PoolClient</string>'
       '<ProtectedString name="Source">' + cdata(read("PoolClient.client.lua")) + '</ProtectedString></Properties></Item>'
       '<Item class="ModuleScript" referent="RBX10"><Properties><string name="Name">NCWallet</string>'
       '<ProtectedString name="Source">' + cdata(read("NCWallet.lua")) + '</ProtectedString></Properties></Item>'
       '<Item class="Script" referent="RBX11"><Properties><string name="Name">Elevator</string>'
       '<ProtectedString name="Source">' + cdata(read("Elevator.server.lua")) + '</ProtectedString></Properties></Item>'
       '<Item class="Script" referent="RBX12"><Properties><string name="Name">ParachuteService</string>'
       '<ProtectedString name="Source">' + cdata(read("ParachuteService.server.lua")) + '</ProtectedString></Properties></Item>'
       '<Item class="LocalScript" referent="RBX13"><Properties><string name="Name">ParachuteClient</string>'
       '<ProtectedString name="Source">' + cdata(read("ParachuteClient.client.lua")) + '</ProtectedString></Properties></Item>'
       '<Item class="Script" referent="RBX14"><Properties><string name="Name">MovementService</string>'
       '<ProtectedString name="Source">' + cdata(read("MovementService.server.lua")) + '</ProtectedString></Properties></Item>'
       '<Item class="LocalScript" referent="RBX15"><Properties><string name="Name">MovementClient</string>'
       '<ProtectedString name="Source">' + cdata(read("MovementClient.client.lua")) + '</ProtectedString></Properties></Item>'
       '<Item class="ModuleScript" referent="RBX16"><Properties><string name="Name">NCAnimPlayer</string>'
       '<ProtectedString name="Source">' + cdata(read("NCAnimPlayer.lua")) + '</ProtectedString></Properties></Item>'
       + ('<Item class="ModuleScript" referent="RBX17"><Properties><string name="Name">NCAnimations</string>'
          '<ProtectedString name="Source">' + cdata(read("NCAnimations.lua")) + '</ProtectedString></Properties></Item>'
          if os.path.exists(os.path.join(HERE, "NCAnimations.lua")) else '') +
       '</Item></roblox>')
with open(os.path.join(HERE, "NeonCoastBuildingKit.rbxmx"), "w", encoding="utf-8") as f:
    f.write(xml)
print("styles:", ", ".join(f"{k} ({len(v['Colliders'])} colliders, {len(v['Doors'])} doors)" for k, v in data.items() if not k.startswith('_')))
print("BuildingKitData.lua", len(src), "chars; NeonCoastBuildingKit.rbxmx", len(xml), "chars")
