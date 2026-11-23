import json, sys, itertools
cat = json.load(open("lib/ink_catalog.json"))["items"]
L = "/tmp/claude-0/ink/lib/"
by = lambda a, z=None: [i for i in cat if i["area"] == a and (z is None or i["zone"] == z)]
full, up, lo = by("Arm", "full"), by("Arm", "upper"), by("Arm", "lower")
armslots = [("full", f, None) for f in full] + [("pair", u, l) for u, l in itertools.zip_longest(up, lo)]
legs = by("Leg"); hands = by("Hand"); neck = by("Neck"); face = by("Face")
n = (len(armslots) + 1) // 2
looks = []
for k in range(n):
    m, names = {}, []
    for side, idx in (("Left", 2 * k), ("Right", 2 * k + 1)):
        if idx >= len(armslots): continue
        kind, a, b = armslots[idx]; S = side[0]
        if kind == "full":
            m[f"Ink_{side}UpperArm"] = m[f"Ink_{side}LowerArm"] = L + a["files"][S]; names.append(f"{side}: {a['id']}")
        else:
            if a: m[f"Ink_{side}UpperArm"] = L + a["files"][S]; names.append(f"{side}U: {a['id']}")
            if b: m[f"Ink_{side}LowerArm"] = L + b["files"][S]; names.append(f"{side}L: {b['id']}")
    for side, lst, j in (("Left", legs, 2 * k), ("Right", legs, 2 * k + 1)):
        if j < len(lst):
            it = lst[j]; S = side[0]
            m[f"Ink_{side}LowerLeg"] = L + it["files"][S]
            if it["zone"] == "full": m[f"Ink_{side}UpperLeg"] = L + it["files"][S]
            names.append(f"{side}Leg: {it['id']}")
    for side, j in (("Left", 2 * k), ("Right", 2 * k + 1)):
        if j < len(hands): m[f"Ink_{side}Hand"] = L + hands[j]["files"][side[0]]; names.append(f"{side}Hand: {hands[j]['id']}")
    if k < len(neck): m["Ink_NeckHead"] = m["Ink_NeckUpperTorso"] = L + neck[k]["files"]["C"]; names.append("Neck: " + neck[k]["id"])
    if k < len(face): m["Ink_Face"] = L + face[k]["files"]["C"]; names.append("Face: " + face[k]["id"])
    looks.append({"map": m, "names": names})
json.dump(looks, open("review/looks.json", "w"), indent=0)
print(len(looks))
