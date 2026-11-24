# Neon Coast bikes on the lowrider's customization system, Blender headless, one bike per run:
#   NC_BIKE=SportBike NC_PREVIEW_ENGINE=CYCLES blender --background --factory-startup --python build_bikes.py
# Same frames and outputs as build_vehicles.py (1 unit = 1 stud, front = -Y, origin on the ground between the axles;
# car-local Roblox frame (X, Y, Z) = (-x, z, y)), so the same Kit, menu, saves and vinyls work:
#   - frame, fork, swingarm and engine; a lofted tank (its sides and top are vinyl panels)
#   - hinged pieces: the seat lifts (storage tray under it) and the gas cap flips open
#   - swappable parts: handlebars, front fender, fairing / number plate, seat, headlight, taillight, exhaust,
#     underglow, plus every lowrider rim / knock-off / tyre (and off-road tyres) scaled to a bike wheel
#   - data: Car.Bike = true and only FL (front) / RL (rear) wheels; the driving script balances and leans it
# Out (NC_OUT): <id>.glb, <id>Vinyls.glb, NCVehicleData_<id>.lua, previews/<id>_*.png
import sys, json, os, math, re
HERE = os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else r"C:\Users\Crisa\Documents\NeonCoast_Blender"
sys.path.insert(0, HERE)
import nc_kit, nc_extra
from nc_kit import lin, COLORS
from nc_extra import setup_render
import bpy, bmesh
from mathutils import Vector, Matrix

OUT = os.environ.get("NC_OUT", nc_kit.OUT)
PREV = os.path.join(OUT, "previews")
os.makedirs(PREV, exist_ok=True)
nc_kit.reset()
COLORS = dict(COLORS)
COLORS.update({"Frame": (0.06, 0.06, 0.07), "Engine": (0.18, 0.18, 0.2), "Dark": (0.05, 0.05, 0.06), "Seat": (0.12, 0.12, 0.13),
               "SeatTrim": (0.25, 0.25, 0.27), "Glass": (0.30, 0.38, 0.44), "Chrome": (0.86, 0.87, 0.90), "Light": (1.0, 0.97, 0.86),
               "Tail": (0.85, 0.05, 0.05), "Neon": (0.9, 0.2, 0.8), "Under": (0.06, 0.06, 0.07), "Rubber": (0.07, 0.07, 0.08),
               "Spokes": (0.86, 0.87, 0.90), "Dish": (0.86, 0.87, 0.90), "Band": (0.96, 0.96, 0.94), "Rim": (0.86, 0.87, 0.90),
               "Hub": (0.86, 0.87, 0.90), "Gauge": (0.02, 0.02, 0.03)})

# WB wheelbase, WR wheel radius, TW tyre width, RAKE fork angle from vertical (deg), LF fork length (axle to top clamp),
# SEAT (y0, y1, z top), PILLION optional (y0, y1, z top), TANK (y0, y1, z top, half width), ENG (y0, y1, z0, z1),
# PIVOT swingarm pivot (y, z), TAILZ top of the tail / rear fender at its end, TAILY its end y
SPECS = {
    "DirtBike": dict(name="Dirt Bike", flavour="dirt", WB=6.0, WR=1.4, TW=0.5, RAKE=25.0, LF=3.5,
                     SEAT=(-0.85, 2.1, 4.05), TANK=(-1.35, -0.55, 4.45, 0.62), ENG=(-1.35, 0.45, 1.35, 2.95), PIVOT=(0.6, 2.05),
                     TAILY=3.85, TAILZ=3.8, paint=(0.95, 0.42, 0.04),
                     stock={"Bars": "Moto", "Fender": "High", "Fairing": "Plate", "Seats": "Racing", "Headlights": "Square",
                            "Taillights": "Slim", "Exhaust": "Side", "Rim": "Wire100", "KO": "", "Tire": "Offroad"}),
    "SportBike": dict(name="Sport Bike", flavour="sport", WB=5.6, WR=1.25, TW=0.62, RAKE=24.0, LF=3.05,
                      SEAT=(-0.35, 1.0, 3.4), PILLION=(1.0, 2.05, 3.8), TANK=(-1.45, -0.3, 4.0, 0.72), ENG=(-1.5, 0.5, 0.95, 2.65),
                      PIVOT=(0.55, 1.75), TAILY=3.05, TAILZ=3.95, paint=(0.05, 0.25, 0.75),
                      stock={"Bars": "Clip", "Fender": "Low", "Fairing": "Race", "Seats": "Racing", "Headlights": "Dual",
                             "Taillights": "Slim", "Exhaust": "Dual", "Rim": "Split", "KO": "", "Tire": "Classic"}),
}
VID = os.environ.get("NC_BIKE", "SportBike")
S = SPECS[VID]
PREFIX = VID
for k, v in S.items():
    if k not in ("name", "stock", "paint"):
        globals()[k] = v
PILLION = S.get("PILLION")
FLAV = S["flavour"]
COLORS["Body"] = COLORS["Lid"] = S["paint"]
WY_F, WY_R = -WB / 2, WB / 2
W = 0.75                                                   # half width of the paintwork (vinyl panel mapping)
L0, L1 = WY_F - WR - 0.15, max(WY_R + WR, TAILY) + 0.1
ra = math.radians(RAKE)
RK = Vector((0, math.sin(ra), math.cos(ra)))              # up the fork, toward the rider
AX_F = Vector((0, WY_F, WR))
TOP = AX_F + RK * LF                                      # top clamp
HEAD0 = TOP - RK * 1.0                                    # bottom of the head tube
SY0, SY1, SZ = SEAT
TY0, TY1, TZ, THW = TANK

exec(compile(open(os.path.join(HERE, "nc_car_kit.py")).read(), "nc_car_kit.py", "exec"), globals())
OPT_INFO, WHEEL_INFO = {}, {}


def opt(slot, variant, mat):
    kind = f"Opt{slot}{variant}{mat}"
    OPT_INFO[kind] = {"slot": slot, "variant": variant, "mat": mat}
    return kind


def mat_color(kind):
    info = OPT_INFO.get(kind) or WHEEL_INFO.get(kind)
    if info:
        m = info["mat"]
        return {"Hub": "Chrome", "Rim": "Chrome"}.get(m, m)
    base = kind.split("__")[0]
    return {"FuelCap": "Chrome", "SeatPan": "Dark"}.get(base, base)


def sbox(kind, *a, **k):
    k.setdefault("style", PREFIX)
    return box(kind, *a, **k)


def scyl(kind, *a, **k):
    k.setdefault("style", PREFIX)
    return cyl(kind, *a, **k)


def sbeam(kind, *a, **k):
    k.setdefault("style", PREFIX)
    return beam(kind, *a, **k)


def tube(kind, pts, r, seg=12):
    """a bent tube through pts (joints get a ball so bends look welded)"""
    for a, b in zip(pts, pts[1:]):
        scyl(kind, a, b, r, seg=seg)
    for p in pts[1:-1]:
        bm = bmesh.new()
        bmesh.ops.create_uvsphere(bm, u_segments=seg, v_segments=6, radius=r, matrix=Matrix.Translation(p))
        new_obj(bm, kind, style=PREFIX, smooth=40.0)


def loft(kind, secs, p=3.0, n=20, smooth=40.0):
    """closed loft through superelliptic sections (y, half width, z bottom, z top)"""
    bm = bmesh.new()
    rings = []
    for (y, hw, z0, z1) in secs:
        zc, hh = (z0 + z1) / 2, (z1 - z0) / 2
        ring_ = []
        for i in range(n):
            t = 2 * math.pi * i / n
            c, s_ = math.cos(t), math.sin(t)
            x = hw * math.copysign(abs(c) ** (2 / p), c)
            z = zc + hh * math.copysign(abs(s_) ** (2 / p), s_)
            ring_.append(bm.verts.new((x, y, z)))
        rings.append(ring_)
    for A, B in zip(rings, rings[1:]):
        for i in range(n):
            j = (i + 1) % n
            bm.faces.new((A[i], A[j], B[j], B[i]))
    bm.faces.new(list(reversed(rings[0])))
    bm.faces.new(rings[-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return new_obj(bm, kind, style=PREFIX, smooth=smooth)


def arc_band(kind, cy, cz, r, a0, a1, width, thick, seg=24):
    """a curved fender shell round the axis (x) through (cy, cz); angles from straight up, positive = forward"""
    bm = bmesh.new()
    rows = []
    for i in range(seg + 1):
        a = math.radians(a0 + (a1 - a0) * i / seg)
        row = []
        for (rr, x) in ((r, -width / 2), (r, width / 2), (r + thick, width / 2), (r + thick, -width / 2)):
            row.append(bm.verts.new((x, cy - rr * math.sin(a), cz + rr * math.cos(a))))
        rows.append(row)
    for A, B in zip(rows, rows[1:]):
        for i in range(4):
            j = (i + 1) % 4
            bm.faces.new((A[i], A[j], B[j], B[i]))
    bm.faces.new(list(reversed(rows[0])))
    bm.faces.new(rows[-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return new_obj(bm, kind, style=PREFIX, smooth=40.0)


def lerp3(a, b, t):
    return a + (b - a) * t


# ------------------------------------------------------------------ hinges
HINGES = {
    "Lid": {"pivot": (0.0, SY0 + 0.05, SZ - 0.32), "axis": (1, 0, 0), "open": 55, "kind": "seat"},
}
HINGE_OF = {"SeatPan": "Lid"}
HINGE_SLOTS = {"Seats": "Lid"}
CAP = (0.0, (TY0 + TY1) / 2 - 0.05, TZ + 0.01)
HINGES["Fuel"] = {"pivot": (0.0, CAP[1] - 0.2, CAP[2] + 0.06), "axis": (1, 0, 0), "open": -110, "kind": "cap"}
HINGE_OF["FuelCap"] = "Fuel"


# ------------------------------------------------------------------ the bike itself
def build_frame():
    hy = HEAD0.y
    scyl("Frame", HEAD0, TOP + RK * 0.05, 0.2, seg=16)                                     # head tube
    py, pz = PIVOT
    for s in (-1, 1):
        x = s * 0.42
        # twin spars: head tube -> over the engine -> swingarm pivot
        tube("Frame", [Vector((s * 0.15, hy + 0.15, HEAD0.z + 0.55)), Vector((x, ENG[0] + 0.6, ENG[3] + 0.35)),
                       Vector((x, py - 0.15, pz + 0.75)), Vector((x, py, pz))], 0.12)
        # subframe under the seat
        tube("Frame", [Vector((x * 0.8, py - 0.1, pz + 0.85)), Vector((s * 0.28, TAILY - 0.5, SZ - 0.45))], 0.07)
        tube("Frame", [Vector((x * 0.9, py + 0.1, pz + 0.2)), Vector((s * 0.28, TAILY - 0.9, SZ - 0.55))], 0.06)
        # swingarm to the rear axle
        sbeam("Frame", (x, py, pz), (s * 0.36, WY_R, WR), 0.14, 0.22)
        scyl("Chrome", (s * 0.3, WY_R, WR), (s * 0.48, WY_R, WR), 0.09, seg=12)              # axle nut
        # footpegs
        scyl("Dark", (s * 0.45, py - 0.35, pz - 0.35), (s * 0.85, py - 0.35, pz - 0.35), 0.06, seg=10)
    if FLAV == "dirt":                                                                       # cradle under the engine
        tube("Frame", [Vector((0, hy - 0.05, HEAD0.z - 0.1)), Vector((0, ENG[0] - 0.15, ENG[2] + 0.5)),
                       Vector((0, ENG[0] + 0.3, ENG[2] - 0.12)), Vector((0, py, ENG[2] - 0.12))], 0.1)
    # rear shock
    scyl("Chrome", (0, py + 0.2, pz + 0.95), (0, py + 1.2, pz - 0.05), 0.1, seg=12)
    scyl("Tail", (0, py + 0.35, pz + 0.8), (0, py + 1.0, pz + 0.15), 0.17, seg=14)          # spring
    sbox("Frame", -0.3, py + 0.95, pz - 0.25, 0.3, py + 1.3, pz + 0.05)                     # shock link


def build_fork():
    for s in (-1, 1):
        x = s * 0.4
        lo = Vector((x, AX_F.y, AX_F.z))
        mid = lo + RK * (LF * 0.45)
        hi = Vector((x, TOP.y, TOP.z)) + RK * 0.1
        scyl("Chrome", mid - RK * 0.05, hi, 0.12, seg=14)                                  # stanchions
        scyl("Dark", lo, mid, 0.16, seg=14)                                                 # lowers
        scyl("Chrome", (x, WY_F, WR), (x + s * 0.12, WY_F, WR), 0.09, seg=12)
    for z in (0.05, -0.75):                                                                 # triple clamps
        c = TOP + RK * z
        sbox("Frame", -0.55, c.y - 0.2, c.z - 0.08, 0.55, c.y + 0.2, c.z + 0.08, bev=0.04)
    # brake disc + caliper
    ring("Chrome", (-0.3, WY_F, WR), (1, 0, 0), WR * 0.32, WR * 0.62, 0.04, seg=32, style=PREFIX)
    sbox("Dark", -0.42, WY_F + WR * 0.3, WR + 0.15, -0.28, WY_F + WR * 0.62, WR + 0.5)


def build_engine():
    y0, y1, z0, z1 = ENG
    sbox("Engine", -0.55, y0 + 0.3, z0, 0.55, y1, z0 + (z1 - z0) * 0.55, bev=0.12)          # cases
    for s in (-1, 1):
        scyl("Chrome", (s * 0.55, y1 - 0.55, z0 + 0.45), (s * 0.66, y1 - 0.55, z0 + 0.45), 0.42, seg=24)   # side covers
    cy0, cy1 = y0 + 0.1, y0 + 0.95                                                          # cylinders, leaning forward
    sbox("Engine", -0.42, cy0, z0 + (z1 - z0) * 0.45, 0.42, cy1, z1, bev=0.08)
    for i in range(5):
        z = z0 + (z1 - z0) * (0.55 + i * 0.09)
        sbox("Dark", -0.5, cy0 - 0.05, z, 0.5, cy1 + 0.05, z + 0.04)                        # cooling fins
    if FLAV == "sport":
        sbox("Dark", -0.7, HEAD0.y - 0.05, z0 + 0.6, 0.7, HEAD0.y + 0.15, HEAD0.z - 0.3, bev=0.05)   # radiator
    else:
        for s in (-1, 1):                                                                   # side radiators
            sbox("Dark", s * 0.45, HEAD0.y + 0.15, z1 - 0.9, s * 0.62, HEAD0.y + 0.9, z1 + 0.2, bev=0.03)
    scyl("Chrome", (0.62, y1 - 0.2, z0 + 0.25), (0.62, WY_R - 0.3, WR + 0.05), 0.04, seg=6)  # chain


def build_tank():
    """tank (+ sport side panels): one shell split into vinyl panels -> PanelSideL/R (sides), PanelHood (top)"""
    secs = []
    n = 7
    for i in range(n + 1):
        t = i / n
        y = TY0 + (TY1 - TY0) * t
        top = TZ + 0.05 * math.sin(math.pi * t) - (TZ - SZ - 0.05) * t ** 2.2
        bot = TZ - 1.05 + 0.25 * t
        hw = THW * (0.75 + 0.35 * math.sin(math.pi * min(1.0, t * 1.2)))
        secs.append((y, max(0.3, hw), bot, top))
    ob = loft("Tank", secs, p=3.2)
    if FLAV == "sport":                                                                     # side panels down over the frame
        ps = [(TY0 - 0.35, 0.55, ENG[3] - 0.25, TZ - 0.45), (TY0 + 0.1, 0.7, ENG[3] - 0.45, TZ - 0.2),
              (TY1 - 0.1, 0.72, ENG[3] - 0.4, TZ - 0.4), (SY0 + 0.6, 0.6, ENG[3] - 0.1, SZ - 0.4)]
        loft("Tank", ps, p=3.0)
    # tail: cowl (sport) or a long rear fender with side number plates (dirt)
    if FLAV == "sport":
        y0 = SY0 + 0.4
        ts = [(y0, 0.62, SZ - 0.75, SZ - 0.25), ((y0 + TAILY) / 2, 0.55, SZ - 0.55, TAILZ - 0.25), (TAILY - 0.25, 0.36, SZ - 0.25, TAILZ - 0.05),
              (TAILY, 0.22, SZ, TAILZ - 0.15)]
        loft("Body", ts, p=3.0)
    else:
        ts = [(SY0 + 0.9, 0.38, SZ - 0.5, SZ - 0.36), (SY1, 0.4, SZ - 0.45, SZ - 0.33), (TAILY, 0.3, TAILZ - 0.12, TAILZ)]
        loft("Body", ts, p=4.0)
        for s in (-1, 1):
            sbox("Body", s * 0.36, SY0 + 1.0, SZ - 1.35, s * 0.46, SY1 - 0.3, SZ - 0.4, bev=0.04)
    # seat pan + storage tray (the seat lifts on its hinge)
    sbox("SeatPan", -0.48, SY0 + 0.05, SZ - 0.36, 0.48, (PILLION[1] if PILLION else SY1) - 0.05, SZ - 0.3)
    sbox("Under", -0.4, SY0 + 0.25, SZ - 0.75, 0.4, SY1 - 0.15, SZ - 0.38)
    # gas cap
    scyl("FuelCap", CAP, (CAP[0], CAP[1], CAP[2] + 0.07), 0.2, seg=20)
    scyl("Dark", (CAP[0], CAP[1], CAP[2] - 0.02), (CAP[0], CAP[1], CAP[2] + 0.02), 0.24, seg=20)


# ------------------------------------------------------------------ swappable parts
def bars():
    S = "Bars"
    c = TOP + RK * 0.1
    rx = c + Vector((0, 0, 0))
    # Stock: straight bar on risers; Moto: wide braced bar; Ape: tall hangers; Clip: clip-ons under the top clamp
    for v, (h, w_, back) in {"Stock": (0.45, 1.25, 0.25), "Moto": (0.55, 1.5, 0.35), "Ape": (1.15, 1.1, 0.35)}.items():
        k = opt(S, v, "Chrome" if v != "Moto" else "Dark")
        pts = [Vector((-w_, c.y + back, c.z + h)), Vector((-0.35, c.y + back * 0.4, c.z + h)), Vector((0.35, c.y + back * 0.4, c.z + h)),
               Vector((w_, c.y + back, c.z + h))]
        if v == "Ape":
            pts = [Vector((-w_, c.y + back, c.z + h - 0.2)), Vector((-0.42, c.y, c.z + h)), Vector((-0.38, c.y, c.z + 0.1)),
                   Vector((0.38, c.y, c.z + 0.1)), Vector((0.42, c.y, c.z + h)), Vector((w_, c.y + back, c.z + h - 0.2))]
            tube(k, pts[:3], 0.07)
            tube(k, pts[3:], 0.07)
            scyl(k, pts[2], pts[3], 0.07, seg=10)
        else:
            tube(k, pts, 0.07)
            for s in (-1, 1):
                scyl(k, (s * 0.3, c.y, c.z + 0.05), (s * 0.35, c.y + back * 0.4, c.z + h), 0.07, seg=10)    # risers
            if v == "Moto":
                scyl(k, (-0.5, c.y + back * 0.45, c.z + h + 0.15), (0.5, c.y + back * 0.45, c.z + h + 0.15), 0.05, seg=8)
                sbox(opt(S, v, "Body"), -0.25, c.y + back * 0.3, c.z + h + 0.08, 0.25, c.y + back * 0.6, c.z + h + 0.22, bev=0.04)  # bar pad
        for s in (-1, 1):                                                                   # grips + levers
            g = pts[-1] if s > 0 else pts[0]
            scyl(opt(S, v, "Rubber"), g - Vector((s * 0.4, 0, 0)), g + Vector((s * 0.05, 0, 0)), 0.1, seg=10)
            sbeam(opt(S, v, "Dark"), g - Vector((s * 0.5, -0.05, 0)), g - Vector((s * 0.05, -0.45, 0.05)), 0.05, 0.04)
    k = opt(S, "Clip", "Dark")
    for s in (-1, 1):
        a = Vector((s * 0.42, c.y - 0.05, c.z - 0.55))
        b = a + Vector((s * 0.75, 0.55, -0.05))
        scyl(k, a, b, 0.07, seg=10)
        scyl(opt(S, "Clip", "Rubber"), b - Vector((s * 0.35, 0.25, 0)), b + Vector((s * 0.05, 0.03, 0)), 0.1, seg=10)
        sbeam(k, b - Vector((s * 0.45, 0.2, 0)), b - Vector((s * 0.05, -0.35, 0.05)), 0.05, 0.04)


def fenders():
    S = "Fender"
    # Low: hugs the front tyre, rides on the fork lowers; High: motocross beak under the bars
    k = opt(S, "Low", "Body")
    arc_band(k, WY_F, WR, WR + 0.14, -55, 70, TW + 0.14, 0.05)
    for s in (-1, 1):                                                                       # stays to the fork lowers
        sbeam(opt(S, "Low", "Dark"), (s * 0.36, WY_F - 0.1, WR + 0.55), (s * (TW / 2 + 0.08), WY_F - 0.2, WR + WR + 0.14), 0.05, 0.12)
    k = opt(S, "High", "Body")
    lo = TOP - RK * 0.95
    loft(k, [(lo.y + 0.55, 0.42, lo.z - 0.05, lo.z + 0.06), (lo.y - 0.4, 0.5, lo.z - 0.12, lo.z + 0.02),
             (lo.y - 1.4, 0.4, lo.z - 0.35, lo.z - 0.25), (lo.y - 1.9, 0.18, lo.z - 0.55, lo.z - 0.48)], p=5.0)


def fairings():
    S = "Fairing"
    hd = TOP - RK * 0.45                                                                    # headlight spot
    hy = hd.y - 0.62
    # Race: full nose round the headlights + a tall screen + side panels down to the belly
    k = opt(S, "Race", "Body")
    loft(k, [(hy - 0.04, 0.5, hd.z - 0.26, hd.z + 0.2), (hy + 0.35, 0.62, hd.z - 0.6, hd.z + 0.42), (HEAD0.y + 0.25, 0.8, ENG[2] + 0.75, hd.z + 0.42),
             (TY0 + 0.35, 0.8, ENG[2] + 0.55, TZ - 0.5), (ENG[1] - 0.35, 0.62, ENG[2] + 0.45, ENG[3] - 0.2)], p=2.6)
    sbeam(opt(S, "Race", "Glass"), (0, hy + 0.12, hd.z + 0.4), (0, hy + 0.78, hd.z + 0.95), 0.85, 0.04, up=(0, -0.65, 0.76))
    loft(opt(S, "Race", "Dark"), [(ENG[0] + 0.1, 0.6, ENG[2] - 0.15, ENG[2] + 0.2), (ENG[1] - 0.1, 0.55, ENG[2] - 0.1, ENG[2] + 0.2)], p=3.0)  # belly pan
    # Street: a small cowl round the headlight + flyscreen
    k = opt(S, "Street", "Body")
    loft(k, [(hy + 0.02, 0.5, hd.z - 0.45, hd.z + 0.4), (hy + 0.45, 0.6, hd.z - 0.6, hd.z + 0.5), (hy + 0.75, 0.5, hd.z - 0.45, hd.z + 0.35)], p=3.0)
    sbeam(opt(S, "Street", "Glass"), (0, hy + 0.3, hd.z + 0.45), (0, hy + 0.65, hd.z + 0.85), 0.75, 0.04, up=(0, -0.7, 0.7))
    # Plate: motocross number plate on the fork (white, with a dark number field)
    k = opt(S, "Plate", "Light")
    sbeam(k, (0, hy + 0.25, hd.z - 0.55), (0, hy + 0.05, hd.z + 0.55), 1.05, 0.05, up=(0, -1, 0.3))
    sbeam(opt(S, "Plate", "Dark"), (0, hy + 0.21, hd.z - 0.3), (0, hy + 0.09, hd.z + 0.35), 0.6, 0.03, up=(0, -1, 0.3))


def lights():
    hd = TOP - RK * 0.45
    hy = hd.y - 0.62
    S = "Headlights"
    for s in (-1, 1):                                                                       # Dual: twin round lamps
        scyl(opt(S, "Dual", "Chrome"), (s * 0.24, hy + 0.12, hd.z), (s * 0.24, hy - 0.06, hd.z), 0.2, seg=20)
        scyl(opt(S, "Dual", "Light"), (s * 0.24, hy - 0.06, hd.z), (s * 0.24, hy - 0.09, hd.z), 0.16, seg=20)
    sbox(opt(S, "Slim", "Dark"), -0.5, hy - 0.04, hd.z - 0.12, 0.5, hy + 0.2, hd.z + 0.12, bev=0.04)
    sbox(opt(S, "Slim", "Light"), -0.45, hy - 0.07, hd.z - 0.06, 0.45, hy - 0.03, hd.z + 0.06)
    sbox(opt(S, "Square", "Dark"), -0.38, hy - 0.02, hd.z - 0.32, 0.38, hy + 0.25, hd.z + 0.28, bev=0.05)
    sbox(opt(S, "Square", "Light"), -0.32, hy - 0.06, hd.z - 0.26, 0.32, hy - 0.01, hd.z + 0.22)
    sbox("Frame", -0.25, hy + 0.15, hd.z - 0.12, 0.25, hd.y - 0.1, hd.z + 0.12)            # lamp bracket
    S = "Taillights"
    ty = TAILY + 0.02
    tz = TAILZ - (0.2 if FLAV == "sport" else 0.12)
    sbox(opt(S, "Slim", "Tail"), -0.28, ty - 0.08, tz - 0.05, 0.28, ty + 0.03, tz + 0.05)
    sbox(opt(S, "Bar", "Dark"), -0.32, ty - 0.1, tz - 0.12, 0.32, ty + 0.06, tz + 0.12, bev=0.03)
    sbox(opt(S, "Bar", "Tail"), -0.28, ty + 0.05, tz - 0.08, 0.28, ty + 0.09, tz + 0.08)
    # plate hanger + indicators (fixed)
    pz0 = max(tz - 1.15, 2 * WR + 0.15)                                                     # plate clears the tyre
    sbox("Dark", -0.04, TAILY - 0.4, pz0 + 0.2, 0.04, TAILY - 0.3, tz - 0.1)
    sbox("Dark", -0.42, TAILY - 0.43, pz0 - 0.03, 0.42, TAILY - 0.4, pz0 + 0.45)
    sbox("Light", -0.38, TAILY - 0.45, pz0, 0.38, TAILY - 0.43, pz0 + 0.42)
    gc = TOP + RK * 0.12
    sbox("Dark", -0.32, gc.y - 0.1, gc.z - 0.02, 0.32, gc.y + 0.12, gc.z + 0.16, bev=0.04)  # gauge pod


def exhausts():
    S = "Exhaust"
    py, pz = PIVOT
    y0, y1, z0, z1 = ENG
    hdr = Vector((0, y0 + 0.2, z0 + (z1 - z0) * 0.6))
    # Side: one pipe low down the right side to a can by the rear wheel; Dual: twin cans under the tail
    k = opt(S, "Side", "Chrome")
    if FLAV == "dirt":
        pts = [hdr + Vector((0.3, -0.1, 0)), Vector((0.62, y0 + 0.3, z1 - 0.2)), Vector((0.62, py + 0.2, SZ - 1.0)), Vector((0.6, TAILY - 1.2, SZ - 0.9))]
        tube(k, pts, 0.1)
        scyl(opt(S, "Side", "Dark"), (0.6, TAILY - 2.2, SZ - 1.05), (0.6, TAILY - 0.6, SZ - 0.75), 0.24, seg=16)
    else:
        pts = [hdr + Vector((0.3, -0.1, 0)), Vector((0.45, y0 + 0.1, z0 + 0.2)), Vector((0.62, py, z0 + 0.25)), Vector((0.7, py + 0.6, z0 + 0.45))]
        tube(k, pts, 0.1)
        scyl(opt(S, "Side", "Dark"), (0.72, py + 0.5, z0 + 0.4), (0.72, py + 1.9, z0 + 0.95), 0.25, seg=16)
    k = opt(S, "Dual", "Chrome")
    for s in (-1, 1):
        tube(k, [hdr + Vector((s * 0.2, -0.1, 0)), Vector((s * 0.35, y0 + 0.1, z0 + 0.15)), Vector((s * 0.3, py + 0.2, z0 + 0.25)),
                 Vector((s * 0.3, py + 0.8, SZ - 0.9))], 0.08)
        scyl(opt(S, "Dual", "Dark"), (s * 0.3, py + 0.7, SZ - 0.95), (s * 0.3, TAILY - 0.15, SZ - 0.6), 0.2, seg=16)
        scyl(k, (s * 0.3, TAILY - 0.15, SZ - 0.6), (s * 0.3, TAILY - 0.1, SZ - 0.58), 0.13, seg=14)


def seats():
    S = "Seats"
    y1 = SY1
    for v in ("Racing", "Rolls", "Diamond"):
        k = opt(S, v, "Seat")
        if FLAV == "dirt":
            loft(k, [(SY0, 0.35, SZ - 0.32, SZ - 0.05), (SY0 + 0.4, 0.5, SZ - 0.32, SZ), (y1 - 0.3, 0.45, SZ - 0.32, SZ - 0.04),
                     (y1, 0.3, SZ - 0.32, SZ - 0.12)], p=4.0)
        else:
            loft(k, [(SY0, 0.45, SZ - 0.32, SZ - 0.08), (SY0 + 0.3, 0.6, SZ - 0.32, SZ), (y1 - 0.15, 0.55, SZ - 0.32, SZ - 0.02),
                     (y1, 0.5, SZ - 0.32, SZ + 0.05)], p=4.0)
            p0, p1, pz = PILLION
            loft(k, [(p0, 0.45, SZ - 0.32, pz - 0.05), (p0 + 0.2, 0.48, SZ - 0.3, pz), (p1 - 0.1, 0.38, pz - 0.35, pz - 0.02),
                     (p1, 0.3, pz - 0.3, pz - 0.08)], p=4.0)
    zt = lambda y: SZ + 0.01
    for i in range(6):                                                                      # tuck-and-roll pleats
        y = SY0 + 0.35 + i * (y1 - SY0 - 0.6) / 5
        sbox(opt(S, "Rolls", "SeatTrim"), -0.42, y - 0.03, zt(y) - 0.04, 0.42, y + 0.03, zt(y) + 0.02)
    for i in range(int((y1 - SY0 - 0.5) / 0.3)):                                            # diamond buttons
        for j in range(3):
            y = SY0 + 0.4 + i * 0.3 + (0.15 if j % 2 else 0)
            scyl(opt(S, "Diamond", "SeatTrim"), ((j - 1) * 0.25, y, zt(y) - 0.03), ((j - 1) * 0.25, y, zt(y) + 0.02), 0.04, seg=6)
    for s in (-1, 1):                                                                       # racing: contrast side panels
        sbox(opt(S, "Racing", "SeatTrim"), s * 0.46, SY0 + 0.4, SZ - 0.3, s * 0.5, y1 - 0.3, SZ - 0.12)


def underglow():
    for s in (-1, 1):
        sbox(opt("Glow", "On", "Neon"), s * 0.5, ENG[0], ENG[2] - 0.15, s * 0.58, PIVOT[0] + 0.6, ENG[2] - 0.08)


exec(compile(re.search(r"^def build_wheels\(ox\):.*?(?=^\S)", open(os.path.join(HERE, "build_vehicle_parts.py")).read(), re.S | re.M).group(0),
             "build_vehicle_parts.py:build_wheels", "exec"), globals())

build_frame()
build_fork()
build_engine()
build_tank()
bars()
fenders()
fairings()
lights()
exhausts()
seats()
underglow()
for k, v in OPT_INFO.items():
    if v["slot"] in HINGE_SLOTS:
        v["hinge"] = HINGE_SLOTS[v["slot"]]

# ------------------------------------------------------------------ vinyl panels: tank sides + top
PANELS = {"side": ("yz", (L0 - 0.1, L1 + 0.1), (0.0, TAILZ + 0.6)), "hood": ("xy", (-W - 0.05, W + 0.05), (TY0 - 0.6, SY0 + 0.6))}
PANEL_OF = {"PanelSideL": "side", "PanelSideR": "side", "PanelHood": "hood"}
SOURCE_OF = {"side": "PanelSideL", "hood": "PanelHood"}


def panel_uv(panel, co):
    ax, (a0, a1), (b0, b1) = PANELS[panel]
    if ax == "yz":
        return ((co.y - a0) / (a1 - a0), (co.z - b0) / (b1 - b0))
    return ((a1 - co.x) / (a1 - a0), 1 - (co.y - b0) / (b1 - b0))


def split_tank():
    tanks = [o for o in OBJS if o["kind"] == "Tank"]
    bm = bmesh.new()
    for o in tanks:
        bake(o)
        me = o.data.copy()
        me.transform(o.matrix_world)
        bm.from_mesh(me)
        bpy.data.meshes.remove(me)
        OBJS.remove(o)
        bpy.data.objects.remove(o)
    me = bpy.data.meshes.new("tank")
    bm.to_mesh(me)
    bm.free()
    regions = {}
    for f in me.polygons:
        n = f.normal
        r = "PanelHood" if n.z > 0.75 else ("PanelSideL" if n.x > 0.2 else ("PanelSideR" if n.x < -0.2 else "Body"))
        regions.setdefault(r, set()).add(f.index)
    for r, idx in regions.items():
        b2 = bmesh.new()
        b2.from_mesh(me)
        b2.faces.ensure_lookup_table()
        bmesh.ops.delete(b2, geom=[f for f in b2.faces if f.index not in idx], context="FACES")
        ob = new_obj(b2, r, style=PREFIX, smooth=40.0)
        if r in PANEL_OF:
            bake(ob)
            uv = ob.data.uv_layers.new(name="UVMap")
            for poly in ob.data.polygons:
                for li in poly.loop_indices:
                    uv.data[li].uv = panel_uv(PANEL_OF[r], ob.data.vertices[ob.data.loops[li].vertex_index].co)
            ob["uv"] = True
    bpy.data.meshes.remove(me)


split_tank()
car, car_tris = join_style(PREFIX, PREFIX)

VINYLS = {}
vd = os.path.join(OUT, "lowrider_vinyls") if os.path.isdir(os.path.join(OUT, "lowrider_vinyls")) else os.path.join(HERE, "lowrider_vinyls")
if os.path.isdir(vd):
    for fn in sorted(os.listdir(vd)):
        if fn.endswith(".png") and "_" in fn:
            liv, pan = fn[:-4].rsplit("_", 1)
            if pan in PANELS:
                VINYLS.setdefault(liv, {})[pan] = os.path.join(vd, fn)
by_kind = {ob.name.split("_", 1)[1]: ob for ob in car}
vinyl_objs = []
for liv, panels in sorted(VINYLS.items()):
    for pan, path in sorted(panels.items()):
        srcp = by_kind.get(SOURCE_OF[pan])
        if not srcp:
            continue
        cp = srcp.copy()
        cp.data = srcp.data.copy()
        cp.name = f"{PREFIX}Livery_{liv}_{pan}"
        cp.data.name = cp.name
        cp.data.materials.clear()
        cp.data.materials.append(image_mat(cp.name, path))
        bpy.context.scene.collection.objects.link(cp)
        vinyl_objs.append(cp)
if vinyl_objs:
    export(vinyl_objs, f"{PREFIX}Vinyls.glb")
for ob in vinyl_objs:
    bpy.data.objects.remove(ob)

WHEEL_X = 30.0
build_wheels(WHEEL_X)
wheel, wheel_tris = join_style("LowriderWheel", PREFIX + "Wheel")
export(car + wheel, f"{PREFIX}.glb")

# ------------------------------------------------------------------ game data
car_ext, wheel_ext = extents(car), extents(wheel)
cmn, cmx = imp_ext(car_ext)
wmn, wmx = imp_ext(wheel_ext)
seats_ = {"Driver": car_pt((0.0, SY0 + 0.55, SZ + 0.2))}
if PILLION:
    seats_["Passenger"] = car_pt((0.0, (PILLION[0] + PILLION[1]) / 2, PILLION[2] + 0.2))
gc = TOP + RK * 0.12
data = {
    "Car": {
        "Bike": True,
        "ImportMin": cmn, "ImportMax": cmx, "Pieces": sorted(k.split("_", 1)[1] for k in car_tris),
        "Wheels": {"FL": car_pt((0.0, WY_F, WR)), "RL": car_pt((0.0, WY_R, WR))},
        "WheelRadius": WR,
        "Hinges": {k: {"Pivot": car_pt(h["pivot"]), "Axis": car_pt(h["axis"]), "Open": h["open"], "Kind": h["kind"]} for k, h in HINGES.items()},
        "HingeOf": {k: v for k, v in HINGE_OF.items() if f"{PREFIX}_{k}" in car_tris},
        "Hull": [car_box((-0.6, WY_F - 0.4, WR * 0.6), (0.6, WY_R + 0.4, SZ - 0.3)), car_box((-0.35, SY0, SZ - 0.3), (0.35, SY1, SZ - 0.1))],
        "Seats": seats_,
        "FrontBumper": car_pt((0, L0, WR)), "RearBumper": car_pt((0, L1, WR)),
        "PanelOf": PANEL_OF, "Vinyls": {liv: sorted(p) for liv, p in VINYLS.items()},
        "OptInfo": {k: v for k, v in OPT_INFO.items() if f"{PREFIX}_{k}" in car_tris},
        "Options": options_of(OPT_INFO, car_tris, PREFIX + "_"),
        "Gauge": {"Centre": car_pt((0.0, gc.y, gc.z + 0.165)), "Size": [0.56, 0.2], "Tilt": 80.0},
    },
    "Wheel": {"ImportMin": wmn, "ImportMax": wmx, "Centre": imp_pt((WHEEL_X, 0, 0)),
              "Pieces": sorted(k.split("_", 1)[1] for k in wheel_tris),
              "OptInfo": {k: v for k, v in WHEEL_INFO.items() if f"{PREFIX}Wheel_{k}" in wheel_tris},
              "Options": options_of(WHEEL_INFO, wheel_tris, PREFIX + "Wheel_")},
}
with open(os.path.join(OUT, f"NCVehicleData_{VID}.lua"), "w") as f:
    f.write(f"-- NCVehicleData_{VID} (ModuleScript, ReplicatedStorage). GENERATED by build_bikes.py: do not edit by hand.\n")
    f.write(f"-- {S['name']}: same layout as NCLowriderData.Car / .Wheel; Car.Bike = true (two wheels, FL = front, RL = rear).\n")
    f.write("return " + lua(data) + "\n")

# ------------------------------------------------------------------ previews
BASE_BUILD = dict(S["stock"])
SHOWCASE = {
    "dirt": [("build_trail", {"Fender": "Low", "Fairing": "", "Bars": "Stock", "Rim": "Star", "Headlights": "Dual"}, "tropical", (0.95, 0.95, 0.95)),
             ("build_night", {"Bars": "Ape", "Seats": "Diamond", "Exhaust": "Dual", "Rim": "Turbine", "Tire": "Classic", "Glow": "On", "Fairing": "Street"},
              "lightning", (0.06, 0.02, 0.15))],
    "sport": [("build_street", {"Fairing": "Street", "Bars": "Stock", "Headlights": "Square", "Exhaust": "Side", "Rim": "Star"}, "flames", (0.05, 0.05, 0.06)),
              ("build_show", {"Fairing": "", "Bars": "Ape", "Seats": "Rolls", "Rim": "Wire100", "Glow": "On", "Fender": "High"}, "checker", (0.95, 0.95, 0.95))],
}[FLAV]
scene, cam = setup_render()
scene.render.resolution_x, scene.render.resolution_y = 1400, 820
if os.environ.get("NC_PREVIEW_ENGINE", "").upper() == "CYCLES":
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = int(os.environ.get("NC_SAMPLES", "16"))
    scene.cycles.use_denoising = False
    scene.world.use_nodes = True
    bgn = scene.world.node_tree.nodes.get("Background")
    if bgn:
        bgn.inputs["Color"].default_value = (0.55, 0.65, 0.8, 1)
        bgn.inputs["Strength"].default_value = 0.9
    sun = bpy.data.objects.new("Sun", bpy.data.lights.new("Sun", "SUN"))
    sun.data.energy = 4.0
    sun.rotation_euler = (math.radians(50), 0, math.radians(30))
    scene.collection.objects.link(sun)
    gp = bpy.data.meshes.new("Ground")
    gbm = bmesh.new()
    bmesh.ops.create_grid(gbm, x_segments=1, y_segments=1, size=400)
    gbm.to_mesh(gp)
    gbm.free()
    g = bpy.data.objects.new("Ground", gp)
    gm = bpy.data.materials.new("Ground")
    gm.diffuse_color = (0.25, 0.25, 0.27, 1)
    gp.materials.append(gm)
    scene.collection.objects.link(g)
for wy in (WY_F, WY_R):
    for ob in wheel:
        d = ob.copy()
        d["pkind"] = ob["pkind"]
        d["wheelcopy"] = True
        scene.collection.objects.link(d)
        d.matrix_world = Matrix.Translation((0, wy, WR)) @ Matrix.Translation((-WHEEL_X, 0, 0))
for ob in wheel:
    ob.hide_render = True
plain = {}


def part_visible(ob, build):
    k = ob.get("pkind", "")
    info = OPT_INFO.get(k) or WHEEL_INFO.get(k)
    return info is None or build.get(info["slot"]) == info["variant"]


def show(build=None, liv=None, paint=None):
    b = dict(BASE_BUILD, **(build or {}))
    pc = lin(paint) if paint else lin(S["paint"])
    for ob in scene.objects:
        if ob.type != "MESH" or ob.name == "Ground" or (ob in wheel):
            continue
        ob.hide_render = not part_visible(ob, b)
        kind = ob.get("pkind", "")
        is_paint = kind in PANEL_OF or kind == "Body" or OPT_INFO.get(kind, {}).get("mat") == "Body"
        if is_paint:
            plain.setdefault(ob.name, ob.data.materials[0])
            path = VINYLS.get(liv, {}).get(PANEL_OF.get(kind, "")) if liv else None
            if path:
                ob.data.materials[0] = image_mat(f"prev_{liv}_{kind}_{len(plain)}", path, pc)
            else:
                m = plain[ob.name].copy()
                m.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (*pc, 1)
                ob.data.materials[0] = m


def pose(frac):
    for ob in scene.objects:
        k = ob.get("pkind")
        h = HINGE_OF.get(k) or (OPT_INFO.get(k) or {}).get("hinge")
        if not h or ob.get("wheelcopy"):
            continue
        hg = HINGES[h]
        p = Vector(hg["pivot"])
        ob.matrix_world = Matrix.Translation(p) @ Matrix.Rotation(math.radians(hg["open"] * frac), 4, Vector(hg["axis"])) @ Matrix.Translation(-p)


def shot(name, loc, tgt):
    cam.location = loc
    cam.rotation_euler = (Vector(tgt) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
    scene.render.filepath = os.path.join(PREV, f"{VID}_{name}.png")
    bpy.ops.render.render(write_still=True)


Lr = max(-L0, L1)
fz = SZ * 0.55
show()
shot("front34", (-Lr * 1.7, -Lr * 2.0, SZ * 1.5 + 1), (0, -0.3, fz))
shot("rear34", (Lr * 1.6, Lr * 2.1, SZ * 1.5 + 1), (0, 0.3, fz))
shot("side", (Lr * 3.0, 0.0, SZ * 0.6), (0, 0, fz))
for i, (nm, b, liv, paint) in enumerate(SHOWCASE):
    show(b, liv, paint)
    shot(nm, (-Lr * 1.7, -Lr * 2.0, SZ * 1.5 + 1) if i % 2 == 0 else (Lr * 1.6, Lr * 2.1, SZ * 1.5 + 1), (0, 0, fz))
show()
pose(1.0)
shot("open_rear34", (Lr * 1.5, Lr * 1.9, SZ * 2.0 + 1), (0, 0.5, fz))
pose(0.0)
print("NEONCOAST_DONE", json.dumps({"vehicle": VID, "car": sum(car_tris.values()), "wheel": sum(wheel_tris.values()),
                                    "options": data["Car"]["Options"], "wheelOptions": data["Wheel"]["Options"]}))
