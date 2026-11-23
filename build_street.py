# Neon Coast: a test street that uses the exported GLBs (so it also checks they survived export), laid out like
# a real Florida subdivision (references: ~5-6 ft sidewalks, ~6 ft planting strip, 10-12 ft lanes, 18-20 ft
# double driveways, curbside mailboxes, royal palms along the street, sabal/queen palms in yards).
# Renders previews/Street_*.png. Not exported: this is the realism check, the game layout is done in Studio.
import sys, json, os, math, random
sys.path.insert(0, r"C:\Users\Crisa\Documents\NeonCoast_Blender")
import importlib, nc_kit, nc_extra
importlib.reload(nc_kit)
importlib.reload(nc_extra)
from nc_extra import *
import bpy

reset()
random.seed(3)
D = r"C:\Users\Crisa\Documents\NeonCoast_Blender"
meta = {}
for f in ("houses.json", "florida.json", "safehouse.json"):
    with open(os.path.join(D, f)) as fh:
        meta.update(json.load(fh))
props_meta = json.load(open(os.path.join(D, "props.json")))


def import_glb(name):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=os.path.join(D, name + ".glb"))
    objs = [o for o in bpy.data.objects if o not in before and o.type == "MESH"]
    for o in objs:
        o.hide_render = True
        o.hide_set(True)
    return objs


INST = [0]


def place(objs, x, y, rot=0.0, offset_x=0.0, z=0.0, kind="prop", label=None, sx=1.0):
    """Copy a set of imported meshes to (x, y, z) turned by rot. Every copy is tagged with an instance id and a QA
    kind (prop / house / pool / floaty / court) so nc_qa can check floating and clipping per placed thing.
    sx stretches the prop along its own X (fence panels sized to fit a run exactly)."""
    INST[0] += 1
    tag = f"{label or (objs[0].name.split('_')[0] if objs else '?')}#{INST[0]}"
    c, s = math.cos(rot), math.sin(rot)
    for o in objs:
        n = o.copy()
        bpy.context.scene.collection.objects.link(n)
        t = o.matrix_world.translation
        e = o.matrix_world.to_euler("XYZ")
        lx, ly, lz = t.x - offset_x, t.y, t.z
        n.location = (x + lx * c - ly * s, y + lx * s + ly * c, lz + z)
        n.rotation_mode = "XYZ"
        n.rotation_euler = (e.x, e.y, e.z + rot)
        if sx != 1.0:
            n.scale = (o.scale.x * sx, o.scale.y, o.scale.z)
        n.hide_render = False
        n.hide_set(False)
        n["style"] = "Street"
        n["inst"] = tag
        n["qa"] = kind
    return tag


def mat(name, rgb):
    m = bpy.data.materials.new(name)
    m.diffuse_color = (*nc_kit.lin(rgb), 1)
    return m


def flat(name, x0, y0, x1, y1, z0, z1, m):
    bpy.ops.mesh.primitive_cube_add(size=1, location=((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2))
    o = bpy.context.active_object
    o.scale = (x1 - x0, y1 - y0, z1 - z0)
    o.data.materials.append(m)
    o["style"] = "Street"
    o["qa"] = "surface"
    o["inst"] = name
    o.name = name
    return o


houses = {n: import_glb(n) for n in ("FloridaRanch", "Mediterranean", "KeyWest", "Ranch", "TwoStory", "Modern")}
props_objs = import_glb("StreetProps")
props = {}
for o in props_objs:
    props.setdefault(o.name.split("_")[0], []).append(o)
pool_objs = import_glb("Pool")
pools = {}
for o in pool_objs:
    pools.setdefault(o.name.split("_")[0], []).append(o)
pool_meta = json.load(open(os.path.join(D, "pool.json")))
CUTS = []                                            # boxes to dig out of the ground (in-ground pools)
BACK = 172.0                                         # rear lot line (lots ~125 ft deep: room for the estate pools)
FENCE_STEP = 9.2                                     # panels share a post
FP, FPOST, FGATE = props_meta["FencePanel"]["offsetX"], props_meta["FencePost"]["offsetX"], props_meta["FenceGate"]["offsetX"]
FP_LEN, GATE_LEN = 9.2, 5.2
RETURNS = {}                                         # (side, lot-line index) -> world |y| where return fences meet it
WZ = pool_meta["BackyardPool"]["notes"]["water"]["max"][2]
# backyard pools (house-local origin of the pool's deck edge) and which of them have the unicorn floaty
POOL_AT = {3: (-4.0, 27.8), 4: (-4.0, 28.3), 6: (-2.0, 29.5), 10: (-4.0, 28.3)}   # deck starts where the patio ends
FLOATY_IN = {4, 6}
# front-door pots where fx +- 3.6 would land inside a wall or half off the porch
FRONT_POTS = {"Mediterranean": [(-14.7, -24.5), (-5.3, -24.5)], "Modern": [(-10.6, -19.0), (-1.6, -19.2)]}
PATIO_TABLE_X = {"Ranch": -12.75, "TwoStory": -10.75, "Modern": -11.0}

GRASS, ASPH, CONC, DRIVE = mat("Grass", (0.36, 0.55, 0.25)), mat("Asphalt", (0.22, 0.22, 0.23)), mat("Concrete", (0.78, 0.77, 0.74)), mat("Drive", (0.82, 0.78, 0.70))
L = 760.0
flat("Ground", -80, -420, L + 80, 420, -0.6, 0.0, GRASS)
flat("Road", -80, -15, L + 80, 15, 0.0, 0.05, ASPH)
for s in (-1, 1):
    flat("Curb", -80, s * 15, L + 80, s * 16.2, 0.0, 0.55, CONC)
    flat("Sidewalk", -80, s * 23.2, L + 80, s * 29.2, 0.0, 0.3, CONC)

SUPPORT_TAGS = {"porch", "step", "deck", "lanai", "loggia", "patio", "stoop"}


def support_top(m, lx, ly, r=0.0, zmax=5.0):
    """Height of the porch / stoop / deck a prop of radius r at house-local (lx, ly) stands on (0 = the lawn)."""
    best = 0.0
    for c in m["colliders"]:
        if c["tag"] in SUPPORT_TAGS and c["max"][2] <= zmax:
            if c["min"][0] - 0.01 <= lx - r and lx + r <= c["max"][0] + 0.01 and c["min"][1] - 0.01 <= ly - r and ly + r <= c["max"][1] + 0.01:
                best = max(best, c["max"][2])
    return best


def free_spot(m, lx, ly, r, gx0, gx1, fx):
    """A yard prop of radius r here touches no part of the house, the driveway or the front walk."""
    for c in m["colliders"]:
        if c["min"][2] < 2.0 and c["min"][0] < lx + r - 0.05 and lx - r + 0.05 < c["max"][0] and c["min"][1] < ly + r - 0.05 and ly - r + 0.05 < c["max"][1]:
            return False
    if abs(lx - fx) < 2.2 + r or (gx0 - 1.0 - r < lx < gx1 + 1.0 + r):
        return False
    return True


def fence_run(x0, y0, x1, y1, end_post=True, gate_first=False):
    """A straight privacy-fence run (world coords): panels stretched to fit it exactly, each carrying the post at
    its start; a walk gate first if asked; an end post unless another run's post closes the end."""
    dx, dy = x1 - x0, y1 - y0
    L_ = math.hypot(dx, dy)
    if L_ < 1.0:
        return
    ux, uy = dx / L_, dy / L_
    rot = math.atan2(dy, dx)
    at = 0.0
    if gate_first:                                   # hinge post on the start; the next panel's post is the latch post
        place(props["FenceGate"], x0 + ux * 2.9, y0 + uy * 2.9, rot, FGATE)
        at = GATE_LEN
    span = L_ - at - (0.6 if end_post else 0.0)
    if span > 0.5:
        n = max(1, round(span / FP_LEN))
        step = span / n
        sc = step / FP_LEN
        for k in range(n):
            c_ = at + k * step + 4.9 * sc
            place(props["FencePanel"], x0 + ux * c_, y0 + uy * c_, rot, FP, sx=sc)
    if end_post:
        place(props["FencePost"], x1 - ux * 0.3, y1 - uy * 0.3, rot, FPOST)


GROUND_TAGS = {"wall", "floor", "ceiling", "roof", "parapet", "glass", "stairs", "clerestory", "canopy", "tower", "post", "rail"}


def side_faces(m, y, margin=0.2):
    """Outermost faces of the house (walls and foundation) on its left and right at house-local y."""
    xl, xr = 0.0, 0.0
    for c in m["colliders"]:
        if c["tag"] in ("wall", "floor") and c["min"][2] < 3.0 and c["min"][1] <= y <= c["max"][1]:
            xl, xr = min(xl, c["min"][0]), max(xr, c["max"][0])
    return xl - margin, xr + margin


def return_y(m):
    """Where the backyard fence comes back to the house: well back along the side walls, in a band clear of AC
    units, chimneys, pool pumps, side doors and anything else at ground level between the house and the lot line."""
    yb = max(c["max"][1] for c in m["colliders"] if c["tag"] == "wall")
    doors = [d for d in m["doors"] if d["axis"] == "y"]
    # side-wall windows low enough for the 8 ft fence to cross, widened by their shutters
    wins = [w for w in m.get("windows", []) if w["axis"] == "y" and w["min"][1] < 8.3]

    def clear(y):
        xl, xr = side_faces(m, y)
        for c in m["colliders"]:
            if c["tag"] in GROUND_TAGS or c["min"][2] > 3.0:
                continue
            if c["min"][1] < y + 1.5 and y - 1.5 < c["max"][1] and (c["max"][0] < xl + 0.2 or c["min"][0] > xr - 0.2):
                return False
        for d in doors:
            if d["min"][0] - 1.5 < y < d["max"][0] + 1.5:
                return False
        for w in wins:
            if w["min"][0] - 3.6 < y < w["max"][0] + 3.6:
                return False
        return True

    # the rear third of the side walls first, then right at the back corner, then further forward
    for y in [yb - 4.0 - 0.5 * k for k in range(13)] + [yb - 0.6 - 0.5 * k for k in range(7)] + [yb - 10.5 - 0.5 * k for k in range(12)]:
        if clear(y):
            return y
    return yb - 4.0


order = ["FloridaRanch", "Mediterranean", "KeyWest", "Ranch", "TwoStory", "Modern", "Mediterranean", "FloridaRanch", "TwoStory", "KeyWest", "Modern", "Ranch"]
LOT = 112.0
PLACED = []
for i, style in enumerate(order):
    side = 1 if i % 2 == 0 else -1                    # north lots face -Y (Blender front), south lots turn 180
    k = i // 2
    x = 60.0 + k * LOT
    setback = 72.0
    y = side * setback
    rot = 0.0 if side == 1 else math.pi
    place(houses[style], x, y, rot, kind="house", label=style)
    PLACED.append((style, x, y, rot))
    m = meta[style]
    # driveway from the garage door (or the front door for the cottage) to the street, walkway from the front door
    g = (m["notes"].get("garage") or [None])[0]
    front = next((d for d in m["doors"] if d["kind"] == "front"), m["doors"][0])
    fx = (front["min"][0] + front["max"][0]) / 2
    fy = front["fixed"] - 1.0
    if g:
        gx0, gx1, gy = g["min"][0], g["max"][0], g["fixed"]
    else:
        gx0, gx1, gy = 22.0, 40.0, -16.0
    def wx(lx):
        return x + (lx if side == 1 else -lx)
    def wy(ly):
        return side * (setback - (-ly)) if side == 1 else -(setback + ly)
    ya, yb = sorted((wy(gy), side * 16.2))
    flat("Drive", min(wx(gx0 - 1.0), wx(gx1 + 1.0)), ya, max(wx(gx0 - 1.0), wx(gx1 + 1.0)), yb, 0.0, 0.32, DRIVE)
    ya, yb = sorted((wy(fy), side * 29.2))
    flat("Walk", min(wx(fx - 2.2), wx(fx + 2.2)), ya, max(wx(fx - 2.2), wx(fx + 2.2)), yb, 0.0, 0.31, CONC)
    # yard: mailbox at the curb by the driveway, foundation shrubs in the beds, a yard palm, bins on trash day
    place(props["Mailbox"], wx(gx0 - 4.0), side * 18.0, rot + math.pi, props_meta["Mailbox"]["offsetX"])
    beds = m["notes"].get("beds") or []
    if beds:
        for bd in beds:                                          # shrubs spaced along each mulch bed, centred in it
            bx0, by0 = bd["min"]
            bx1, by1 = bd["max"]
            n_sh = max(1, int((bx1 - bx0) // 6.5))
            for j in range(n_sh):
                sx = bx0 + (bx1 - bx0) * (j + 0.5) / n_sh
                if free_spot(m, sx, (by0 + by1) / 2, 2.0, gx0, gx1, fx):
                    # planted in the mulch (its root ball sits a little under the mulch top, like a real bed)
                    place(props["Shrub"], wx(sx), wy((by0 + by1) / 2), rot, props_meta["Shrub"]["offsetX"], 0.1)
    elif style == "KeyWest":                                     # along the lattice skirt in front of the porch
        for sx in (-17.0, -9.0, 9.0, 17.0):
            place(props["Shrub"], wx(sx), wy(-24.4), rot, props_meta["Shrub"]["offsetX"])
    else:
        for sx in (-30.0, -22.0, -14.0):
            if abs(sx - fx) > 5 and free_spot(m, sx, -21.5, 2.0, gx0, gx1, fx):
                place(props["Shrub"], wx(sx), wy(-21.5), rot, props_meta["Shrub"]["offsetX"])
    # backyard enclosure: a return fence from each side of the house to the lot line, the walk gate on the
    # driveway side right by the house; the lot-line and rear fences are added after all the houses
    yr = return_y(m)
    xl_f, xr_f = side_faces(m, yr)
    fence_run(wx(xl_f), wy(yr), wx(-56.0 + 0.3), wy(yr), end_post=False)
    fence_run(wx(xr_f), wy(yr), wx(56.0 - 0.3), wy(yr), end_post=False, gate_first=True)
    for lx_ in (-56.0, 56.0):
        RETURNS.setdefault((side, round((wx(lx_) - 4.0) / LOT)), []).append(abs(wy(yr)))
    tree = random.choice(["SabalPalm", "QueenPalm", "SabalPalm"])     # far enough in that its crown clears the street palms
    place(props[tree], wx(-38.0 + random.uniform(-3, 3)), wy(-40.0), random.uniform(0, 6.28), props_meta[tree]["offsetX"])
    if k % 2 == 0:
        place(props["TrashBin"], wx(gx1 + 3.0), side * 19.5, rot, props_meta["TrashBin"]["offsetX"])
        place(props["RecycleBin"], wx(gx1 + 6.5), side * 19.5, rot, props_meta["RecycleBin"]["offsetX"])
    P = lambda name, lx, ly, r=0.0, z=0.0: place(props[name], wx(lx), wy(ly), rot + r, props_meta[name]["offsetX"], z)
    # lived-in details: pots by the front door (on the porch / stoop they stand on), path lights along the walk,
    # a hoop on some driveways
    pots = FRONT_POTS.get(style, [(fx - 3.6, fy - 2.2), (fx + 3.6, fy - 2.2)])
    for (px_, py_) in pots:
        P("Planter", px_, py_, 0.0, support_top(m, px_, py_, 1.3))
    walk_len = abs(wy(fy) - side * 29.2)
    for j in range(1, int(walk_len // 9)):
        P("PathLight", fx - 3.2, fy - j * 9.0)
    if i in (1, 4, 8):
        P("BasketballHoop", gx1 + 2.0, gy - 26.0, math.pi)
    def box_cut(lx0, ly0, lx1, ly1, z0, z1):
        xa, xb = sorted((wx(lx0), wx(lx1)))
        ya_, yb_ = sorted((wy(ly0), wy(ly1)))
        CUTS.append((xa, ya_, z0, xb, yb_, z1))
    if style == "FloridaRanch":
        for ly in (34.0, 41.0, 48.0):
            P("Lounger", -28.2, ly, math.pi, 0.65)
        P("PoolPump", -39.0, 22.0, math.pi / 2)
        pb = m["notes"]["pool"]                                  # the caged pool goes below ground too
        box_cut(pb["min"][0] - 0.4, pb["min"][1] - 0.4, pb["max"][0] + 0.4, pb["max"][1] + 0.4, pb["min"][2] - 0.6, 0.05)
    elif style == "KeyWest":
        porch = support_top(m, -12.0, -18.5, 1.5)
        P("RockingChair", -14.0, -18.5, 0.0, porch + 0.1)      # the rockers dip 0.1 below the seat frame
        P("RockingChair", -10.5, -18.5, 0.3, porch + 0.1)
        P("PatioSet", 0.0, 34.0)                                # out in the yard past the back stairs
    elif style == "Mediterranean" and i not in POOL_AT:
        # the back loggia is covered: table out on the lawn past it (an umbrella doesn't go under a roof)
        P("PatioSet", -14.0, 34.0)
        P("Grill", 13.0, 24.0, math.pi)
    elif style in ("TwoStory", "Ranch", "Modern"):
        # on the back patio beside the stoop; umbrella (4.6 radius) clear of the wall, chairs on the slab
        tx = PATIO_TABLE_X[style]
        P("PatioSet", tx, 23.6, 0.0, support_top(m, tx, 23.6, 3.8))
        if i not in POOL_AT:
            P("Grill", 2.0, 30.5, math.pi)
    if i in POOL_AT:
        # in-ground diving pool on its paver deck; loungers along the far side, a table at the shallow end,
        # the grill on the deep-end corner, the floaty in a couple of them
        px, py = POOL_AT[i]
        place(pools["BackyardPool"], wx(px), wy(py), rot, pool_meta["BackyardPool"]["offsetX"], kind="pool")
        cut = pool_meta["BackyardPool"]["notes"]["cut"]
        box_cut(px + cut["min"][0], py + cut["min"][1], px + cut["max"][0], py + cut["max"][1], cut["min"][2], 0.05)
        Q = lambda name, lx, ly, r=0.0, z=0.35: place(props[name], wx(px + lx), wy(py + ly), rot + r, props_meta[name]["offsetX"], z)
        pn = pool_meta["BackyardPool"]["notes"]
        for lx in (-31.0, -25.0, -13.0, -7.0, -1.0):             # a row of loungers on the far deck
            Q("Lounger", lx, 42.0)
        shelf = pn["shelf"]
        for lx in (-31.0, -27.0):                                # in-water loungers on the sun shelf (a foot of water)
            Q("Lounger", lx, 14.0, 0.0, shelf["top"])
        Q("Grill", 43.0, 4.0, math.pi)
        if i in FLOATY_IN:
            place(pools["UnicornFloaty"], wx(px + 8.0), wy(py + 24.0), rot + 0.5, pool_meta["UnicornFloaty"]["offsetX"], WZ + 0.45, kind="floaty")
        for (lx, ly, kind_) in ((-50.0, 92.0, "SabalPalm"), (50.0, 88.0, "QueenPalm")):   # palms in the back corners
            P(kind_, lx, ly, random.uniform(0, 6.28))

# lot-line fences: from where the first return fence meets the line back to the rear fence, split at every return
# so each junction gets a post; then the rear fence along the back lot line with a post on every lot corner
rear_y = BACK - 0.3
for (s, j), ys in RETURNS.items():
    xl = 4.0 + j * LOT
    stops = sorted(set(round(v, 3) for v in ys)) + [rear_y]
    for a, b in zip(stops, stops[1:]):
        fence_run(xl, s * (a - 0.3), xl, s * (b - 0.3), end_post=False)
for s in (-1, 1):
    for j in range(6):
        fence_run(4.0 + j * LOT - 0.3, s * rear_y, 4.0 + (j + 1) * LOT - 0.3, s * rear_y, end_post=False)
    place(props["FencePost"], 4.0 + 6 * LOT, s * rear_y, 0.0, FPOST)

# street trees, lights, hydrant, signs, drains in the planting strip / at the curb
for j in range(8):                                   # about one street tree per lot, on the lot line
    for s in (-1, 1):
        x = 60.0 + 56.0 + j * LOT + (0.0 if s > 0 else -LOT / 2)
        if x > L + 40:                               # the ground ends at L + 80
            continue
        kind = "RoyalPalm" if j == 0 else ("QueenPalm" if (j + (s > 0)) % 2 == 0 else "SabalPalm")
        place(props[kind], x, s * 19.7, random.uniform(0, 6.28), props_meta[kind]["offsetX"])
for j in range(5):
    s = 1 if j % 2 == 0 else -1
    place(props["StreetLight"], 30.0 + j * 170.0, s * 21.5, 0.0 if s > 0 else math.pi, props_meta["StreetLight"]["offsetX"])
place(props["Hydrant"], 236.0, -20.5, 0.0, props_meta["Hydrant"]["offsetX"])   # clear of trash-day bins
place(props["StopSign"], -40.0, 21.0, math.pi, props_meta["StopSign"]["offsetX"])
place(props["StreetSign"], -40.0, 22.5, 0.0, props_meta["StreetSign"]["offsetX"])
for j in range(4):
    place(props["StormDrain"], 120.0 + j * 200.0, 15.6, 0.0, props_meta["StormDrain"]["offsetX"])
place(props["UtilityBox"], 180.0, 31.0, 0.0, props_meta["UtilityBox"]["offsetX"])

# power poles down the back lot lines with sagging wires (as in most Florida subdivisions)
import nc_detail
importlib.reload(nc_detail)
wires = House("StreetWires")
attach = props_meta["UtilityPole"]["notes"]["wires"]
for s in (-1, 1):
    ys = s * (BACK + 6.0)                            # poles in the rear easement, just past the fence
    xs = [60.0 - 56.0 + j * LOT for j in range(8)]
    for x in xs:
        place(props["UtilityPole"], x, ys, 0.0, props_meta["UtilityPole"]["offsetX"])
    for a, b in zip(xs, xs[1:]):
        for (ax, ay, az) in attach:
            p0, p1 = (a + ax, ys + ay, az), (b + ax, ys + ay, az)
            mid = ((p0[0] + p1[0]) / 2, ys + ay, az - 2.2)
            for (q0, q1) in ((p0, mid), (mid, p1)):
                nc_detail.beam(wires, "Metal", q0, q1, 0.09, 0.09)
for ob in wires.build()[0]:
    ob["style"] = "Street"
# road markings at the corner: a stop bar and a ladder crosswalk
WHITE = mat("Paint", (0.95, 0.95, 0.93))
flat("StopBar", -36.0, 0.0, -34.0, 15.0, 0.05, 0.08, WHITE)
for k in range(8):
    y = -14.0 + k * 3.6
    flat("Crosswalk", -50.0, y, -40.0, y + 1.8, 0.05, 0.08, WHITE)

# pocket park past the last north lot: the regulation half court (hoop at the back so balls stay off the road),
# a walk in from the sidewalk, a privacy fence behind the hoop, lights for night games, a picnic table, palms
CX, CY = 735.0, 74.5                                  # court origin: middle of the baseline
place(props["HalfCourt"], CX, CY, 0.0, props_meta["HalfCourt"]["offsetX"])
flat("ParkWalk", CX - 3.0, 29.2, CX + 3.0, CY - 34.5, 0.0, 0.2, CONC)
for j in range(7):
    place(props["FencePanel"], CX - 32.2 + 4.6 + j * FENCE_STEP, CY + 6.0, 0.0, props_meta["FencePanel"]["offsetX"])
place(props["FencePost"], CX - 32.2 + 7 * FENCE_STEP, CY + 6.0, 0.0, props_meta["FencePost"]["offsetX"])
for (lx, ly) in ((-31.0, -36.0), (31.0, -36.0), (-31.0, 3.5), (31.0, 3.5)):
    place(props["PostLight"], CX + lx, CY + ly, 0.0, props_meta["PostLight"]["offsetX"])
place(props["PatioSet"], CX - 44.0, CY - 18.0, 0.0, props_meta["PatioSet"]["offsetX"])
place(props["TrashBin"], CX + 5.0, 32.5, 0.0, props_meta["TrashBin"]["offsetX"])
place(props["SabalPalm"], CX - 44.0, CY - 1.0, 1.3, props_meta["SabalPalm"]["offsetX"])
place(props["QueenPalm"], CX + 44.0, CY - 30.0, 4.1, props_meta["QueenPalm"]["offsetX"])
place(props["QueenPalm"], CX + 45.0, CY - 4.0, 2.2, props_meta["QueenPalm"]["offsetX"])
for sx in (-8.0, 8.0):
    place(props["Planter"], CX + sx, 31.5, 0.0, props_meta["Planter"]["offsetX"])
BALL = mat("Ball", (0.80, 0.36, 0.13))
for (bx, by) in ((2.0, -21.85), (-9.0, -7.0)):          # one on the free-throw line, one rolled into the key
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.45, segments=24, ring_count=12, location=(CX + bx, CY + by, 0.12 + 0.45))
    o = bpy.context.active_object
    o.data.materials.append(BALL)
    bpy.ops.object.shade_smooth()
    o["style"] = "Street"

# dig the in-ground pools out of the lawn
ground = bpy.data.objects["Ground"]
for n_, (x0, y0, z0, x1, y1, z1) in enumerate(CUTS):
    bpy.ops.mesh.primitive_cube_add(size=1, location=((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2))
    cutter = bpy.context.active_object
    cutter.scale = (x1 - x0, y1 - y0, z1 - z0)
    cutter.name = f"PoolCut{n_}"
    cutter.hide_render = True
    cutter.hide_set(True)
    mod = ground.modifiers.new(f"Cut{n_}", "BOOLEAN")
    mod.operation = "DIFFERENCE"
    mod.object = cutter
    try:
        mod.solver = "FAST"
    except Exception:
        pass
if os.environ.get("NC_QA"):
    import nc_qa
    importlib.reload(nc_qa)
    # one point in each backyard, a little in from the rear fence
    yards = [(f"{st}@{round(px_)}", (px_, (1 if py_ > 0 else -1) * (BACK - 8.0))) for (st, px_, py_, rt) in PLACED]
    if os.environ.get("NC_QA_SELFTEST"):                 # a front-yard point must come back as open to the street
        yards.append(("SELFTEST-front-yard", (PLACED[0][1] - 40.0, 50.0)))
    nc_qa.run(os.path.join(D, "qa_street.json"), yards=yards, street_y=30.0)
    if os.environ.get("NC_QA") == "only":
        print("NEONCOAST_DONE qa")
        raise SystemExit

scene, cam = setup_render()
scene.render.resolution_x, scene.render.resolution_y = 1600, 900
render_views(scene, cam, ["Street"], {
    "level": ((-30, -9, 6.5), (260, 12, 14)),
    "sidewalk": ((90, -26, 6.0), (150, 40, 12)),
    "drone": ((-120, -260, 170), (300, 40, 0)),
    "aerial": ((380, -40, 520), (380, 0, 0)),
    "court": ((735, 30.5, 6.2), (735, 76, 9.5)),                  # walking in from the sidewalk
    "court_shooter": ((741, 47, 6.0), (735, 68.5, 11.0)),         # a player's eye from the free-throw line
    "park": ((800, -12, 62), (735, 60, 0)),
    "pools_drone": ((214, 40, 95), (290, 128, 0)),                # backyards with the estate pools and the fences
    "pool_twostory": ((252, 98, 8.0), (300, 124, 0.0)),           # from the patio: sun shelf and spa to the board
    "pool_mediterranean": ((372, 103, 9.0), (402, 125, 0.0)),     # the floaty
    "fences": ((110, 30, 80), (175, 100, 0)),                     # return fences, gates, lot-line fences
    "gate": ((214, 58, 7.0), (205, 84, 4.0)),                     # a walk gate by the house
}, "Street")
if os.environ.get("NC_WALK"):
    import nc_walk
    importlib.reload(nc_walk)
    all_meta = dict(meta)
    nc_walk.walkaround(scene, cam, PLACED, all_meta)
    nc_walk.closeups(scene, cam, {
        "ranch_downspout": ((198, -40, 9), (207.5, -54.5, 8)),
        "twostory_side_downspout": ((238, 44, 10), (251.5, 56, 10)),
        "keywest_back_stairs": ((186, 110, 9), (172, 92, 3)),
        "modern_back_doors": ((606, 116, 7), (598, 91, 5)),
        "mediterranean_tower": ((64, -24, 13), (70, -50, 17)),
        "floridaranch_coach_light": ((65, 41, 7.5), (72.6, 52, 6.8)),
    })
print("NEONCOAST_DONE street")
