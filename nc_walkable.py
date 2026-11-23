# nc_walkable: can a player actually walk into every building and onto every floor? Pure Python on the exported
# collider data (houses.json, florida.json, safehouse.json, civic.json, city.json):
#   python nc_walkable.py            -> walkable.json + a summary
# Every collider top is a place to stand if a character fits above it (2 x 2 studs, from 1.5 studs up to 5 studs:
# steps and curbs under 1.5 don't block, walls, glass and railings do). Characters step up at most 1.3 studs and
# can drop down. Door leaves aren't colliders (they swing open) and garage doors open. The flood starts on the
# ground all round the building; every floor slab, stair landing and balcony it never reaches is reported,
# and for the downtown buildings the roof too (that's where you parachute from).
import json, math, os, sys
from collections import deque

HERE = os.path.dirname(os.path.abspath(__file__))
SOURCES = ["houses.json", "florida.json", "safehouse.json", "civic.json", "city.json"]
CELL = 1.0
STEP = 1.3
BODY_HALF = 0.9
BODY_LO, BODY_HI = 1.5, 5.0
PASSABLE = {"garagedoor", "gate"}
FLOORISH = {"floor", "landing", "balcony", "fireescape", "porch", "stoop", "patio", "deck", "loggia", "lanai", "jump"}
CITY = {"DecoHotel", "MidRiseBrick", "MidRiseStucco", "OfficeTower"}


def check(style, m):
    cols = [c for c in m["colliders"] if c["tag"] not in PASSABLE]
    ext = m["extents_studs"]
    # spatial hash of colliders (4-stud buckets) for the body test
    B = 4.0
    buckets = {}
    for idx, c in enumerate(cols):
        for i in range(int(math.floor(c["min"][0] / B)), int(math.floor(c["max"][0] / B)) + 1):
            for j in range(int(math.floor(c["min"][1] / B)), int(math.floor(c["max"][1] / B)) + 1):
                buckets.setdefault((i, j), []).append(idx)

    def body_clear(x, y, z):
        lo, hi = z + BODY_LO, z + BODY_HI
        seen = set()
        for i in range(int(math.floor((x - BODY_HALF) / B)), int(math.floor((x + BODY_HALF) / B)) + 1):
            for j in range(int(math.floor((y - BODY_HALF) / B)), int(math.floor((y + BODY_HALF) / B)) + 1):
                for idx in buckets.get((i, j), ()):
                    if idx in seen:
                        continue
                    seen.add(idx)
                    c = cols[idx]
                    if c["min"][2] < hi and c["max"][2] > lo and c["min"][0] < x + BODY_HALF and c["max"][0] > x - BODY_HALF \
                            and c["min"][1] < y + BODY_HALF and c["max"][1] > y - BODY_HALF:
                        return False
        return True

    # standing cells: (i, j) -> list of (z, collider index or -1 for the ground)
    cells = {}
    margin = 14.0
    gx0, gx1 = ext["x"][0] - margin, ext["x"][1] + margin
    gy0, gy1 = ext["y"][0] - margin, ext["y"][1] + margin
    surfaces = [(-1, gx0, gy0, gx1, gy1, 0.0)] + [(k, c["min"][0], c["min"][1], c["max"][0], c["max"][1], c["max"][2]) for k, c in enumerate(cols)]
    for (k, x0, y0, x1, y1, z) in surfaces:
        if x1 - x0 < 0.6 or y1 - y0 < 0.6:
            continue
        # a body can stand with its middle up to half a stud past an edge, so cells reach a little past the
        # surface (that also bridges the small gaps between a stair and the slab edge, as in the game)
        e = 0.5 if k >= 0 else 0.0
        for i in range(int(math.ceil((x0 - e) / CELL)), int(math.floor((x1 + e) / CELL)) + 1):
            for j in range(int(math.ceil((y0 - e) / CELL)), int(math.floor((y1 + e) / CELL)) + 1):
                x, y = i * CELL, j * CELL
                # the ground only counts outside every collider's footprint at that spot
                if body_clear(x, y, z):
                    cells.setdefault((i, j), []).append((z, k))
    # flood from the ground ring
    start = [((i, j), n) for (i, j), lst in cells.items() for n, (z, k) in enumerate(lst) if k == -1
             and (i * CELL < ext["x"][0] - 6 or i * CELL > ext["x"][1] + 6 or j * CELL < ext["y"][0] - 6 or j * CELL > ext["y"][1] + 6)]
    seen = set(start)
    q = deque(start)
    while q:
        (i, j), n = q.popleft()
        z = cells[(i, j)][n][0]
        for (a, b) in ((i + 1, j), (i - 1, j), (i, j + 1), (i, j - 1)):
            for m2, (z2, k2) in enumerate(cells.get((a, b), ())):
                if z2 - z <= STEP and ((a, b), m2) not in seen:
                    seen.add(((a, b), m2))
                    q.append(((a, b), m2))
    reached = {cells[c][n][1] for (c, n) in seen}
    report = []
    # downtown: the main roof must be reachable (the big one, not the roof on top of the stair penthouse)
    roofs = [k for k, c in enumerate(cols) if c["tag"] == "roof"]
    area = lambda c: (c["max"][0] - c["min"][0]) * (c["max"][1] - c["min"][1])
    main_z = max((cols[k]["max"][2] for k in roofs if area(cols[k]) > 400), default=None) if style in CITY else None
    main_z = min((cols[k]["max"][2] for k in roofs if area(cols[k]) > 400), default=None) if style in CITY else None
    for k, c in enumerate(cols):
        tag = c["tag"]
        want = tag in FLOORISH or (main_z is not None and tag == "roof" and abs(c["max"][2] - main_z) < 0.01)
        if not want or (c["max"][0] - c["min"][0]) * (c["max"][1] - c["min"][1]) < 4.0:
            continue
        if k not in reached:
            # only report surfaces a body could stand on at all
            if any(kk == k for lst in cells.values() for (_, kk) in lst):
                report.append({"tag": tag, "z": round(c["max"][2], 2), "min": [round(v, 1) for v in c["min"][:2]], "max": [round(v, 1) for v in c["max"][:2]]})
    return report, len(cells)


if __name__ == "__main__":
    out = {}
    only = set(sys.argv[1:])
    for src in SOURCES:
        p = os.path.join(HERE, src)
        if not os.path.exists(p):
            continue
        for style, m in json.load(open(p)).items():
            if only and style not in only:
                continue
            rep, ncells = check(style, m)
            out[style] = rep
            levels = sorted({r["z"] for r in rep})
            print(f"WALK {style}: {ncells} standing cells, {len(rep)} unreachable surfaces" + (f" at z {levels[:12]}" if rep else ""))
    json.dump(out, open(os.path.join(HERE, "walkable.json"), "w"), indent=1)
