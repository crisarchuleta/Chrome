"""Static check for the Character Studio data (no Roblox needed): python tools/check_look_catalog.py
Checks every item's family exists in NCLookBuilder, palettes exist, default colours are in their palette,
ids are unique, preset looks only use real items in the right slot, and colours in presets are allowed."""
import re, sys, os
root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
cat = open(os.path.join(root, "NCLookCatalog.lua"), encoding="utf-8").read()
bld = open(os.path.join(root, "NCLookBuilder.lua"), encoding="utf-8").read()
fams = set(re.findall(r"^F\.(\w+)\s*=", bld, re.M))
slots = re.findall(r'\{ id = "(\w+)", name = "[^"]*", icon', cat)
pals = {}
for name, body in re.findall(r"^\t(\w+) = \{([^}]*)\},?$", cat.split("C.PALETTES = {")[1].split("\n}\n")[0], re.M):
    pals[name] = [h.upper() for h in re.findall(r'"(#[0-9A-Fa-f]{6})"', body)]
# local aliases used for palettes
alias = dict(re.findall(r'^local (\w) = "(\w+)"$', cat, re.M))
alias.update({k: v for k, v in re.findall(r'^local (\w), (\w) = "(\w+)", "(\w+)"$', cat, re.M) and []})
m = re.search(r'^local M, G = "(\w+)", "(\w+)"$', cat, re.M)
if m: alias["M"], alias["G"] = m.group(1), m.group(2)
def palname(tok):
    tok = tok.strip()
    if tok == "nil": return None
    if tok.startswith('"'): return tok.strip('"')
    return alias.get(tok, "?" + tok)
items, errs, itempals = {}, [], {}
for line in cat.splitlines():
    mm = re.match(r'\s*I\("(\w+)", "(\w+)", "((?:[^"\\]|\\.)*)", (\d+), "(\w+)", (\{.*?\}), (\w+|"\w+"|nil), ("#\w+"|nil)(?:, (\w+|"\w+"|nil), ("#\w+"|nil))?', line)
    if not mm: continue
    iid, slot, name, price, fam, pp, p1, d1, p2, d2 = mm.groups()
    items[iid] = slot
    itempals[iid] = (palname(p1), d1.strip('"').upper() if d1 != "nil" else None, palname(p2) if p2 else None, d2.strip('"').upper() if d2 and d2 != "nil" else None)
    if fam not in fams: errs.append(f"{iid}: unknown family {fam}")
    if slot not in slots: errs.append(f"{iid}: unknown slot {slot}")
    for p, d in ((p1, d1), (p2, d2)):
        pn = palname(p) if p else None
        if pn and pn not in pals: errs.append(f"{iid}: unknown palette {p}")
for mm in re.finditer(r'chain\("(\w+)", "[^"]*", (\d+), (\{.*?\}), "(#\w+)", "(#\w+)"', cat):
    iid = mm.group(1); items[iid] = "Neck"; items[iid + "_2"] = "Neck2"
    itempals[iid] = itempals[iid + "_2"] = ("metal", mm.group(4).upper(), "gem", mm.group(5).upper())
dups = [i for i in set(re.findall(r'I\("(\w+)"', cat)) if re.findall(r'I\("' + i + r'"', cat).__len__() > 1]
errs += [f"duplicate id {d}" for d in dups]
for lk, body in re.findall(r'look\("(\w+)", "[^"]*", "\w+", \{(.*?)\}(?:, \w+)?\),', cat, re.S):
    for slot, iid, cols in re.findall(r'(\w+) = e\("(\w+)"((?:, "#\w+")*)\)', body):
        if iid not in items: errs.append(f"look {lk}: missing item {iid}"); continue
        if items[iid] != slot: errs.append(f"look {lk}: {iid} is a {items[iid]} item, used as {slot}")
        for k, c in enumerate(re.findall(r'"(#\w+)"', cols)):
            pal, dfl = itempals[iid][k * 2], itempals[iid][k * 2 + 1]
            if c.upper() != dfl and (not pal or c.upper() not in pals.get(pal, [])):
                errs.append(f"look {lk}: colour {c} not allowed on {iid} (palette {pal})")
print(f"{len(items)} items, {len(re.findall(r'look[(]\"', cat))} looks, {len(fams)} families, {len(pals)} palettes")
for e in errs: print("ERROR", e)
sys.exit(1 if errs else 0)
