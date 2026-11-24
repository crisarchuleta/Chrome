# Neon Coast vehicles on the lowrider's customization system, Blender headless, one vehicle per run:
#   NC_VEHICLE=Ironclad blender --background --factory-startup --python build_vehicles.py
# Every vehicle is built from a spec (SPECS below) by one shared builder:
#   - a body lofted from cross sections, tubbed wheel wells, an open cabin, an engine bay
#   - opening panels on hinges: 2 or 4 doors, the hood, the rear (trunk lid, hatch, liftgate or tailgate) and a gas
#     door. Door glass, mirrors and door cards ride on their door (pieces named <kind>__DoorL etc.)
#   - every swappable part (bumpers, grille, hood, spoiler, skirts, mirrors, exhaust, lights, roof, seats, door cards,
#     dash, steering, shifter, headliner, underglow, bed) as Opt<Slot><Variant><Mat> pieces, sized to the vehicle
#   - the lowrider's wheel designs (every rim, knock-off, tyre, whitewall) plus off-road tyres, scaled to the vehicle
#   - paint panels UV-mapped to the same vinyl images as the lowrider, so every vinyl works on every vehicle
# All names are original (no real makes or models). Same frames as build_lowrider.py: 1 unit = 1 stud, front = -Y,
# origin on the ground between the axles; car-local Roblox frame (X, Y, Z) = (-x, z, y).
# Out (NC_OUT): <id>.glb (pieces <id>_*, wheel <id>Wheel_*), <id>Vinyls.glb, NCVehicleData_<id>.lua,
#      previews/<id>_*.png
import sys, json, os, math
HERE = os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else r"C:\Users\Crisa\Documents\NeonCoast_Blender"
sys.path.insert(0, HERE)
import importlib, nc_kit, nc_extra
from nc_kit import lin, COLORS
from nc_extra import setup_render
import bpy, bmesh
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree

OUT = os.environ.get("NC_OUT", nc_kit.OUT)
PREV = os.path.join(OUT, "previews")
os.makedirs(PREV, exist_ok=True)
nc_kit.reset()

COLORS.update({
    "Body": (0.55, 0.03, 0.08), "Chrome": (0.86, 0.87, 0.90), "Glass": (0.30, 0.38, 0.44), "Dash": (0.12, 0.12, 0.13),
    "Carpet": (0.10, 0.10, 0.11), "Seam": (0.05, 0.05, 0.05), "Under": (0.06, 0.06, 0.07), "Lid": (0.55, 0.03, 0.08),
    "Dark": (0.05, 0.05, 0.06), "Light": (1.0, 0.97, 0.86), "Head": (1.0, 0.97, 0.86), "Tail": (0.85, 0.05, 0.05),
    "Seat": (0.12, 0.12, 0.13), "SeatTrim": (0.25, 0.25, 0.27), "Wood": (0.42, 0.22, 0.1), "Gauge": (0.02, 0.02, 0.03),
    "Neon": (0.9, 0.2, 0.8), "Rubber": (0.07, 0.07, 0.08), "Spokes": (0.86, 0.87, 0.90), "Dish": (0.86, 0.87, 0.90),
    "Band": (0.96, 0.96, 0.94), "Rim": (0.86, 0.87, 0.90), "Hub": (0.86, 0.87, 0.90), "Top": (0.04, 0.04, 0.045),
    "PoliceRed": (1.0, 0.05, 0.05), "PoliceBlue": (0.05, 0.2, 1.0),
})

# ------------------------------------------------------------------ the vehicles
# W half width, L0/L1 nose/tail y, WB wheelbase, WR wheel radius, WX wheel centre |x|, TW tyre width, ZB rocker,
# BELT belt line, NOSE/HOOD hood height at the nose/cowl, TAIL rear deck height, CROWN deck crown,
# cab: A0/A1 windshield base/top y, C0/C1 roof rear / rear glass base y, ROOF roof z, TUCK glass inset at the roof,
# B door pillar y, Q rear door end (4 doors), rear: trunk / hatch / liftgate / tailgate, BED pickup bed y range.
SPECS = {
    "Ironclad": dict(name="Ironclad SS", flavour="muscle", W=3.7, L0=-10.6, L1=9.6, WB=11.4, WR=1.22, WX=3.0, TW=0.85,
                     ZB=0.85, BELT=2.85, NOSE=2.6, HOOD=3.0, TAIL=3.0, CROWN=0.08,
                     A0=-2.3, A1=-0.3, C0=2.7, C1=5.0, ROOF=4.6, TUCK=0.5, B=1.9, doors=2, rear="trunk",
                     paint=(0.75, 0.32, 0.02)),
    "IronhornTRX": dict(name="Ironhorn TRX", flavour="truck", W=3.9, L0=-11.0, L1=11.2, WB=13.6, WR=1.6, WX=3.15, TW=1.15,
                        ZB=1.55, BELT=4.0, NOSE=3.85, HOOD=4.05, TAIL=4.0, CROWN=0.04,
                        A0=-3.0, A1=-1.2, C0=2.3, C1=2.5, ROOF=6.3, TUCK=0.35, B=0.9, Q=2.3, doors=4, rear="tailgate",
                        BED=(2.9, 11.0), paint=(0.08, 0.1, 0.12)),
    "KestrelGT": dict(name="Kestrel GT", flavour="sports", W=3.75, L0=-9.6, L1=8.9, WB=10.6, WR=1.12, WX=3.05, TW=0.95,
                      ZB=0.6, BELT=2.48, NOSE=1.95, HOOD=2.62, TAIL=2.72, CROWN=0.12,
                      A0=-2.6, A1=-0.2, C0=1.6, C1=5.6, ROOF=3.98, TUCK=0.7, B=1.4, doors=2, rear="hatch",
                      paint=(0.02, 0.25, 0.75)),
    "Dunewalker": dict(name="Dunewalker", flavour="suv", W=3.9, L0=-9.8, L1=9.4, WB=12.0, WR=1.55, WX=3.15, TW=1.1,
                       ZB=1.5, BELT=3.85, NOSE=3.65, HOOD=3.9, TAIL=3.85, CROWN=0.04,
                       A0=-3.6, A1=-1.9, C0=9.0, C1=9.15, ROOF=6.4, TUCK=0.3, B=-0.1, Q=3.4, doors=4, rear="liftgate",
                       paint=(0.36, 0.42, 0.28)),
    # the rest of the city's lineup, rebuilt under their existing names (ServerStorage.CarTemplates)
    "VantorStrada": dict(name="Vantor Strada", flavour="muscle", W=3.6, L0=-9.8, L1=9.4, WB=11.2, WR=1.12, WX=2.95, TW=0.8,
                         ZB=0.8, BELT=2.8, NOSE=2.45, HOOD=2.85, TAIL=2.85, CROWN=0.07,
                         A0=-2.6, A1=-0.6, C0=3.0, C1=4.9, ROOF=4.6, TUCK=0.5, B=0.75, Q=3.0, doors=4, rear="trunk",
                         stock={"Hood": "", "Rim": "Split", "Exhaust": ""}, paint=(0.55, 0.57, 0.6)),
    "AurexHalcyon": dict(name="Aurex Halcyon", flavour="muscle", W=3.75, L0=-10.6, L1=10.2, WB=12.4, WR=1.18, WX=3.05, TW=0.85,
                         ZB=0.8, BELT=2.95, NOSE=2.6, HOOD=3.0, TAIL=3.0, CROWN=0.07,
                         A0=-2.8, A1=-0.7, C0=3.6, C1=5.6, ROOF=4.8, TUCK=0.45, B=0.9, Q=3.5, doors=4, rear="trunk",
                         stock={"Hood": "", "Grille": "Billet", "Rim": "Star", "Seats": "Rolls", "Dash": "Wood"}, paint=(0.06, 0.06, 0.08)),
    "KazumiK2": dict(name="Kazumi K2", flavour="sports", W=3.3, L0=-7.2, L1=6.6, WB=9.0, WR=1.0, WX=2.7, TW=0.7,
                     ZB=0.7, BELT=2.75, NOSE=2.2, HOOD=2.75, TAIL=2.95, CROWN=0.08,
                     A0=-2.9, A1=-0.9, C0=4.6, C1=5.6, ROOF=4.7, TUCK=0.4, B=0.6, Q=2.9, doors=4, rear="hatch",
                     stock={"Grille": "Eggcrate", "Headlights": "Square", "Spoiler": "", "Seats": "Buckets",
                            "Dash": "Classic", "Exhaust": "Dual", "Rim": "Steelie"}, paint=(0.9, 0.75, 0.1)),
    "KazeRS8": dict(name="Kaze RS8", flavour="sports", W=3.7, L0=-9.2, L1=8.6, WB=10.4, WR=1.1, WX=3.0, TW=0.95,
                    ZB=0.6, BELT=2.5, NOSE=1.9, HOOD=2.6, TAIL=2.8, CROWN=0.1,
                    A0=-2.2, A1=0.0, C0=2.2, C1=5.2, ROOF=4.0, TUCK=0.65, B=1.6, doors=2, rear="trunk",
                    stock={"Rim": "Mesh", "Spoiler": "Wing"}, paint=(0.75, 0.05, 0.05)),
    "HayatoTypeZ": dict(name="Hayato Type Z", flavour="sports", W=3.6, L0=-9.0, L1=8.4, WB=10.2, WR=1.08, WX=2.95, TW=0.9,
                        ZB=0.6, BELT=2.45, NOSE=1.85, HOOD=2.5, TAIL=2.6, CROWN=0.1,
                        A0=-1.9, A1=0.3, C0=2.0, C1=6.0, ROOF=3.9, TUCK=0.6, B=1.7, doors=2, rear="hatch",
                        stock={"Rim": "Turbine", "Headlights": "Quad"}, paint=(0.92, 0.92, 0.9)),
    "NorrbyDL84": dict(name="Norrby DL84", flavour="muscle", W=3.55, L0=-9.6, L1=9.4, WB=11.0, WR=1.08, WX=2.9, TW=0.78,
                       ZB=0.8, BELT=2.85, NOSE=2.6, HOOD=2.85, TAIL=2.9, CROWN=0.02,
                       A0=-2.5, A1=-1.0, C0=3.2, C1=4.4, ROOF=4.85, TUCK=0.25, B=0.7, Q=2.9, doors=4, rear="trunk",
                       stock={"Hood": "", "Exhaust": "", "Headlights": "Square", "Steering": "Sport"}, paint=(0.12, 0.3, 0.55)),
    "PoliceCruiser": dict(name="Police Cruiser", flavour="muscle", W=3.65, L0=-10.0, L1=9.8, WB=11.6, WR=1.12, WX=3.0, TW=0.85,
                          ZB=0.85, BELT=2.9, NOSE=2.65, HOOD=2.95, TAIL=2.95, CROWN=0.03,
                          A0=-2.6, A1=-1.0, C0=3.3, C1=4.6, ROOF=4.85, TUCK=0.3, B=0.75, Q=3.0, doors=4, rear="trunk",
                          police=True, stock={"Hood": "", "Exhaust": "", "Steering": "Sport"}, paint=(0.04, 0.04, 0.05)),
    "MarloweDeville61": dict(name="Marlowe 61", flavour="muscle", W=3.85, L0=-11.2, L1=11.0, WB=12.6, WR=1.15, WX=3.15, TW=0.8,
                             ZB=0.8, BELT=2.7, NOSE=2.5, HOOD=2.85, TAIL=2.9, CROWN=0.06,
                             A0=-2.4, A1=-0.6, C0=3.0, C1=5.2, ROOF=4.5, TUCK=0.5, B=2.0, doors=2, rear="trunk",
                             fins=True, stock={"Hood": "", "Rim": "Wire100", "KO": "Bar2", "Band": "ClassicThin", "Seats": "Rolls", "Doors": "Rolls", "Steering": "Chain"},
                             paint=(0.55, 0.85, 0.82)),
    "DusterRidge54": dict(name="Duster Ridge 54", flavour="truck", W=3.6, L0=-9.6, L1=9.6, WB=11.4, WR=1.3, WX=2.85, TW=0.8,
                          ZB=1.2, BELT=3.6, NOSE=3.3, HOOD=3.75, TAIL=3.6, CROWN=0.1,
                          A0=-2.4, A1=-1.3, C0=1.0, C1=1.2, ROOF=5.6, TUCK=0.3, B=1.15, doors=2, rear="tailgate",
                          BED=(1.6, 9.4), stock={"Grille": "Bars", "Headlights": "Dual", "Rim": "Steelie", "Tire": "Classic"}, paint=(0.75, 0.2, 0.12)),
    "ShorelineSix": dict(name="Shoreline Six", flavour="suv", W=3.85, L0=-9.2, L1=10.0, WB=12.4, WR=1.25, WX=3.15, TW=0.85,
                         ZB=1.1, BELT=3.6, NOSE=3.2, HOOD=3.6, TAIL=3.6, CROWN=0.05,
                         A0=-4.2, A1=-2.6, C0=9.6, C1=9.75, ROOF=6.9, TUCK=0.2, B=-1.0, Q=2.6, doors=4, rear="liftgate",
                         paint=(0.25, 0.65, 0.75)),
    "ArmoredTruck": dict(name="Coast Patrol Armored Truck", flavour="suv", W=4.1, L0=-10.0, L1=11.0, WB=13.0, WR=1.5, WX=3.3, TW=1.0,
                         ZB=1.6, BELT=4.1, NOSE=3.9, HOOD=4.2, TAIL=4.1, CROWN=0.03,
                         A0=-4.0, A1=-2.8, C0=10.6, C1=10.75, ROOF=7.6, TUCK=0.1, B=-1.3, doors=2, rear="liftgate",
                         blind=True, police=True, stock={"Top": "", "FrontBumper": "Bull"}, paint=(0.2, 0.22, 0.24)),
    # open-top utility cart: no doors (open sides), canopy on posts, a small tipping bed with a tailgate
    "GeneralsCart": dict(name="Generals Cart", flavour="truck", W=2.9, L0=-6.0, L1=6.4, WB=8.4, WR=0.85, WX=2.3, TW=0.7,
                         ZB=0.75, BELT=2.7, NOSE=2.45, HOOD=2.7, TAIL=2.7, CROWN=0.05,
                         A0=-3.0, A1=-2.5, C0=2.8, C1=2.85, ROOF=5.7, TUCK=0.1, B=1.0, doors=0, rear="tailgate",
                         BED=(2.95, 6.4), opentop=True,
                         stock={"FrontBumper": "Stock", "RearBumper": "Stock", "Grille": "Mesh", "Headlights": "Square", "Seats": "Rolls",
                                "Rim": "Steelie", "Tire": "Classic", "Skirts": ""}, paint=(0.12, 0.36, 0.22)),
    # electric liftback sedan (original design, proportions taken from a reference photo of a real full-size electric
    # sedan; no badges or brand details): drawn at real size (no FIT): 16.3 ft long, 6.4 ft wide, 4.7 ft tall,
    # 9.7 ft wheelbase. Low rounded nose with a closed face and a low intake, raked windshield, strong tumblehome,
    # long glass roof into a liftback, big multi-spoke wheels, no exhaust; a front trunk where the engine would be and
    # a charge port where the gas door would be
    "VireoE": dict(name="Vireo E", flavour="sports", W=3.8, L0=-9.6, L1=9.15, WB=11.17, WR=1.33, WX=3.18, TW=1.0,
                   ZB=0.62, BELT=3.4, NOSE=2.95, HOOD=3.8, TAIL=4.0, CROWN=0.02, HCROWN=-0.42,
                   A0=-3.6, A1=-0.1, C0=3.8, C1=7.9, ROOF=5.35, TUCK=0.75, B=1.0, Q=3.9, doors=4, rear="hatch",
                   electric=True, LEAN=0.1, LONGGLASS=True, PLAN=True, NOSEDROP=1.25, FLEAN=0.08, GH_IN=0.06, GH_N=2.3, QWIN=(2.5, 1.9), DLO=dict(tip=5.9, kick=10.0), SQUARE=1.0, WS_BACK=1.4, FUEL_DY=-0.25, FUEL_DZ=-0.2, SKYLIGHT=dict(front=0.15, rear=0.07, width=0.9), lowpro=0.24, smooth=True, rim_dark=True, RIM_TWIN=True,
                   stock={"Exhaust": "", "Spoiler": "", "Rim": "Split", "KO": "", "Top": "", "Seats": "Buckets", "Grille": "", "FrontBumper": "", "RearBumper": "",
                                         "Dash": "Digital", "Steering": "Sport"}, paint=(0.025, 0.025, 0.03)),
}
# ------------------------------------------------------------------ real-world proportions (vehicle QA, 2026-11-24)
# The specs above were drawn a little squat. Against real cars of each class (at the world's 1.15 studs per foot, the
# player is 6.6 studs tall) they came out 10-20% too low, so a seated player's head went through the roof, and most
# wheels were 2-3 inches small. FIT scales each spec: vs = every height (rocker, belt, hood, deck, roof), ws = wheel
# radius, ls = every length (overhangs, wheelbase, pillars, bed), plus any keys to set outright. The roof is then raised
# further if needed so a seated player clears the headliner (see fit_headroom below).
FIT = {
    "Ironclad": dict(vs=1.10, ls=0.96),
    "IronhornTRX": dict(vs=1.14),
    "KestrelGT": dict(vs=1.20, ws=1.13, ls=0.94),
    "Dunewalker": dict(vs=1.09),
    "VantorStrada": dict(vs=1.18, ws=1.13),
    "AurexHalcyon": dict(vs=1.13, ws=1.12),
    "KazumiK2": dict(vs=1.16, ws=1.12, ls=1.10),
    "KazeRS8": dict(vs=1.22, ws=1.15),
    "HayatoTypeZ": dict(vs=1.21, ws=1.13),
    "NorrbyDL84": dict(vs=1.10, ws=1.09, set=dict(W=3.35, WX=2.75, WB=10.4)),
    "PoliceCruiser": dict(vs=1.06, ws=1.13),
    "MarloweDeville61": dict(vs=1.15, ws=1.15),
    "DusterRidge54": dict(vs=1.22),
    "ArmoredTruck": dict(vs=1.28, ws=1.21, ls=1.15, set=dict(W=4.4, WX=3.55, TW=1.15)),
    "GeneralsCart": dict(ws=1.12, set=dict(W=2.7, WX=2.15, WB=7.8, ROOF=6.9)),
}
VERT = ("ZB", "BELT", "NOSE", "HOOD", "TAIL", "ROOF")
LONG = ("L0", "L1", "WB", "A0", "A1", "C0", "C1", "B", "Q")
for vid, f in FIT.items():
    sp = SPECS[vid]
    for k in VERT:
        sp[k] = round(sp[k] * f.get("vs", 1.0), 3)
    sp["WR"] = round(sp["WR"] * f.get("ws", 1.0), 3)
    for k in LONG:
        if k in sp:
            sp[k] = round(sp[k] * f.get("ls", 1.0), 3)
    if "BED" in sp:
        sp["BED"] = tuple(round(v * f.get("ls", 1.0), 3) for v in sp["BED"])
    sp.update(f.get("set", {}))
SEAT_H = {"sports": 0.4}                    # cushion top above the floor (low-slung cars sit lower)
SEATED = 3.45                               # cushion to crown of a seated 6.6-stud player


def fit_headroom(sp):
    """raise the roof (and pull a coupe's roof line back over its rear seat) until a seated player clears it"""
    floor = sp["ZB"] + 0.3
    need = floor + SEAT_H.get(sp["flavour"], 0.55) + SEATED + 0.2      # + headliner and roof skin
    if not sp.get("opentop"):
        sp["ROOF"] = round(max(sp["ROOF"], need), 3)
    if sp.get("doors") == 2 and not sp.get("BED") and sp["flavour"] == "muscle":   # 2-door with a rear bench
        sy = (sp["A0"] + sp["B"]) / 2 + 0.9
        ry = sy + 2.5
        if sp["C0"] < ry + 0.45:
            sp["C0"] = round(ry + 0.45, 3)
            sp["C1"] = round(max(sp["C1"], sp["C0"] + 1.4), 3)


for sp in SPECS.values():
    fit_headroom(sp)

VID = os.environ.get("NC_VEHICLE", "Ironclad")
S = SPECS[VID]
SEATH = SEAT_H.get(S["flavour"], 0.55)
PREFIX = VID
for k, v in S.items():
    globals()[k] = v
WY_F, WY_R = -WB / 2, WB / 2
ARCH = min(WR + 0.3, BELT - 0.12 - WR)                  # the arch stays under the belt line
assert ARCH >= WR + 0.1, "wheel too big for the body: raise BELT or shrink WR"
FLAV = S["flavour"]
COLORS["Body"] = COLORS["Lid"] = S["paint"]
BED = S.get("BED")
Q = S.get("Q")
OPEN = S.get("opentop", False)                              # no doors: open sides, a canopy on posts

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
    if base == "HoodInner" or base.startswith("DoorJamb"):
        return "Body"
    return {"RoofGlass": "Glass", "RoofBody": "Body", "RoofChrome": "Chrome"}.get(base, base)


# ------------------------------------------------------------------ body
def ztop(x, top, crown, w):
    t = min(1.0, abs(x) / (0.93 * w))
    return top + crown * (1 - t * t)


def section(w, zb, belt, top, crown, lean=0.0):
    top = max(top, belt + 0.06)
    sh = min(0.3, (belt - zb) * 0.2)
    if S.get("smooth"):  # modern body: a gently barrelled side and a rounder shoulder
        mid = zb + 0.45 + (belt - sh - zb - 0.45) * 0.45
        # lean > 0 (the rear quarters) tucks the upper side in more: the reference's haunches narrow toward the deck
        r_ = S.get("SQUARE", 0.0)                         # 0 = round, 1 = the reference's crisper corners
        half = [(0.0, zb), (w * (0.84 + 0.1 * r_), zb), (w * (0.94 + 0.05 * r_), zb + 0.1 - 0.04 * r_),
                (w * (0.98 + 0.02 * r_), zb + 0.32 - 0.12 * r_), (w, mid), (w * (0.985 + 0.007 * r_ - 0.6 * lean), belt - sh),
                (w * (0.95 + 0.028 * r_ - 0.85 * lean), belt - sh * 0.3), (w * (0.9 + 0.035 * r_ - lean), belt + 0.03)]
        # a tall deck (the tail) leans in above the belt, like the reference's rear three-quarter
        shrink = 1 - 0.12 * min(1.0, max(0.0, (top - belt) / 0.6))
        for k in range(5):
            x = w * (0.89 + 0.035 * r_ - lean) * shrink * (1 - k / 5)
            half.append((x, ztop(x, top, crown, w) - (0.03 if k == 0 else 0.0)))
        half.append((0.0, top + crown))
        return half + [(-x, z) for (x, z) in reversed(half[1:-1])]
    else:
        half = [(0.0, zb), (w * 0.86, zb), (w * 0.965, zb + 0.15), (w, zb + 0.45), (w, belt - sh), (w * 0.99, belt - sh * 0.35),
                (w * 0.965, belt + 0.02)]
    for k in range(5):
        x = w * 0.93 * (1 - k / 5)
        half.append((x, ztop(x, top, crown, w) - (0.03 if k == 0 else 0.0)))
    half.append((0.0, top + crown))
    return half + [(-x, z) for (x, z) in reversed(half[1:-1])]


# plan half width as a fraction of W, against the distance from the nose / the tail (measured off the reference's
# top-view photo, 2026-11-24): the real car's nose and tail corners are much rounder than a formula's
PLAN_FRONT = [(0.0, 0.2), (0.075, 0.26), (0.375, 0.51), (0.67, 0.64), (0.97, 0.74), (1.27, 0.81), (1.8, 0.9), (2.47, 0.96),
              (2.77, 0.98), (3.07, 1.0)]
PLAN_REAR = [(0.0, 0.3), (0.1, 0.36), (0.4, 0.55), (0.7, 0.67), (1.0, 0.75), (1.3, 0.84), (1.6, 0.875), (1.9, 0.9), (2.2, 0.92),
             (2.5, 0.947), (2.8, 0.967), (3.2, 0.99)]


def plan_frac(tab, d):
    if d <= tab[0][0]:
        return tab[0][1]
    for (d0, f0), (d1, f1) in zip(tab, tab[1:]):
        if d <= d1:
            t = (d - d0) / (d1 - d0)
            return f0 + (f1 - f0) * (t * t * (3 - 2 * t) * 0.5 + t * 0.5)
    return 1.0


def make_stations():
    """y, half width, rocker, belt, deck, crown from the nose to the tail"""
    nb = NOSE - 0.25
    if S.get("smooth"):
        # a modern nose: the hood falls in one convex curve from the cowl to a low nose cone that rolls under, the
        # fenders stand above the hood (HCROWN < 0 dips the middle), and the plan rounds off over the first 2.4 studs
        hc = S.get("HCROWN", CROWN)
        ye = A0 - 0.6
        st = []
        for i in range(19):
            u = (i / 18) ** 1.5
            y = L0 + (ye - L0) * u
            d = y - L0
            e = 1 - (1 - min(1.0, d / 3.0)) ** 2.2            # plan: a broad round nose (half width 0.5W at the tip)
            pf = plan_frac(PLAN_FRONT, d) if S.get("PLAN") else 0.5 + 0.5 * e
            f = math.sqrt(max(0.0, 1 - (1 - min(1.0, d / 1.2)) ** 2))
            v = (y - L0) / (A0 - L0)
            top = NOSE + (HOOD - NOSE) * (1 - (1 - v) ** 2) - S.get("NOSEDROP", 0.6) * (1 - f)
            bl = top - 0.07 - (0.4 if S.get("NOSEDROP") else 0.55) * (1 - f)
            if S.get("SQUARE"):                           # the fender crest eases down into the door's belt (no step at the cowl)
                g = min(1.0, max(0.0, (y - (A0 - 3.0)) / 2.4))
                bl = min(bl, bl + (BELT + 0.04 - bl) * g * g * (3 - 2 * g)) if bl > BELT else bl
            st.append((y, W * pf, ZB + 0.1 * (1 - e), bl, top, hc * f))
        st.append((A0, W, ZB, BELT, HOOD + 0.06, hc * 0.5))
    else:
        st = [(L0, W - 0.5, ZB + 0.35, nb - 0.2, nb - 0.12, 0.0), (L0 + 0.2, W - 0.22, ZB + 0.15, nb, NOSE - 0.05, CROWN * 0.4),
              (L0 + 0.8, W - 0.05, ZB, nb + 0.05, NOSE + (HOOD - NOSE) * 0.1, CROWN), (A0 - 0.6, W, ZB, BELT - 0.1, HOOD - 0.02, CROWN),
              (A0, W, ZB, BELT, HOOD, CROWN)]
    # over the front wheel the fender has to clear the arch (low wedge noses would otherwise dip under it)
    yf = WY_F - ARCH - 0.3
    for i in range(len(st) - 1):
        a, b = st[i], st[i + 1]
        if a[0] + 0.3 < yf < b[0] - 0.3 and not S.get("smooth"):
            t = (yf - a[0]) / (b[0] - a[0])
            lerp = lambda k: a[k] + (b[k] - a[k]) * t
            belt = max(lerp(3), WR + ARCH + 0.14)
            st.insert(i + 1, (yf, lerp(1) if S.get("smooth") else W, ZB, belt, max(lerp(4), belt + 0.06), CROWN))
            break
    # (smooth noses: a station already over the arch is lifted the same way)
    if S.get("smooth"):
        def lift(y, bl, tp):
            dy = abs(y - WY_F)
            need = WR + math.sqrt(max(0.0, (ARCH + 0.08) ** 2 - dy * dy)) + 0.1
            bl2 = max(bl, need)
            return bl2, max(tp, bl2 + 0.06)
        st = [(y, w, zb, *lift(y, bl, tp), cr) for (y, w, zb, bl, tp, cr) in st]
    cab_end = C1 if REAR != "liftgate" else L1 - 0.8
    st.append(((A0 + cab_end) / 2, W, ZB, BELT, BELT + 0.1, CROWN * 0.6))
    if REAR in ("trunk", "hatch"):
        st += [(C1, W, ZB, BELT, TAIL - 0.04, CROWN), (L1 - 0.8, W - 0.03, ZB, BELT - 0.05, TAIL, CROWN)]
    else:
        st += [(L1 - 0.8, W - 0.02, ZB, BELT, BELT + 0.06, CROWN)]
    tb = (TAIL if REAR in ("trunk", "hatch") else BELT) - 0.2
    if S.get("smooth"):  # a rounded tail with a small lip
        y0 = L1 - (3.2 if S.get("PLAN") else 2.4) if S.get("LONGGLASS") else max(C1 + 0.25, L1 - 2.4)   # the plan rounds off over the last 2.4 studs
        while st[-1][0] > y0 - 0.05:
            st.pop()
        st.append((y0, W - 0.03, ZB, BELT - 0.05, TAIL, CROWN))
        nt = 12 if S.get("PLAN") else 7
        for i in range(1, nt + 1):
            u = i / nt
            e = math.sqrt(max(0.0, 1 - u ** 2))
            ep = 1 - u ** 2.2                                 # plan rounds sooner than the profile
            yy = y0 + (L1 - y0) * u
            pw = W * plan_frac(PLAN_REAR, L1 - yy) if S.get("PLAN") else W * (0.64 + 0.36 * ep)
            st.append((yy, pw - 0.03, ZB + 0.25 * (1 - e), tb + 0.15 - 0.5 * (1 - e),
                       TAIL - 0.4 * (1 - e) ** 1.5, CROWN * e))
        return st
    st += [(L1 - 0.2, W - 0.2, ZB + 0.12, tb, tb + 0.12, CROWN * 0.4), (L1, W - 0.45, ZB + 0.3, tb - 0.15, tb - 0.05, 0.0)]
    return st


REAR = S["rear"]
STATIONS = make_stations()


def deck_z(x, y):
    for a, b in zip(STATIONS, STATIONS[1:]):
        if a[0] <= y <= b[0]:
            t = (y - a[0]) / (b[0] - a[0])
            v = [a[i] + (b[i] - a[i]) * t for i in range(6)]
            return ztop(x, v[4], v[5], v[1])
    return STATIONS[-1][4]


def station_w(y):
    for a, b in zip(STATIONS, STATIONS[1:]):
        if a[0] <= y <= b[0]:
            return a[1] + (b[1] - a[1]) * (y - a[0]) / (b[0] - a[0])
    return W


def belt_at(y):
    for a, b in zip(STATIONS, STATIONS[1:]):
        if a[0] <= y <= b[0]:
            t = (y - a[0]) / (b[0] - a[0])
            return a[3] + (b[3] - a[3]) * t
    return BELT


def lean_at(y):
    """how much the upper side tucks in (rear quarters of a smooth body)"""
    if not (S.get("smooth") and Q):
        return 0.0
    c_ = min(1.0, max(0.0, (y - Q) / 2.5))
    f_ = min(1.0, max(0.0, (A0 + 0.5 - y) / 2.5))          # the front fenders round off over the top too
    return S.get("LEAN", 0.1) * c_ * c_ * (3 - 2 * c_) + S.get("FLEAN", 0.0) * f_ * f_ * (3 - 2 * f_)


def top_w(y):
    """half width where the deck's top surface ends (section(): the shoulder rolls down from there)"""
    for a, b in zip(STATIONS, STATIONS[1:]):
        if a[0] <= y <= b[0]:
            t = (y - a[0]) / (b[0] - a[0])
            w, belt, top = (a[k] + (b[k] - a[k]) * t for k in (1, 3, 4))
            break
    else:
        w, belt, top = STATIONS[-1][1], STATIONS[-1][3], STATIONS[-1][4]
    shrink = 1 - 0.12 * min(1.0, max(0.0, (top - belt) / 0.6)) if S.get("smooth") else 1.0
    return w * ((0.89 if S.get("smooth") else 0.93) - lean_at(y)) * shrink


def body_x(y, z):
    """half width of the body's outer skin at (y, z): the section's side, below the deck top"""
    for a, b in zip(STATIONS, STATIONS[1:]):
        if a[0] <= y <= b[0]:
            t = (y - a[0]) / (b[0] - a[0])
            v = [a[k] + (b[k] - a[k]) * t for k in range(6)]
            break
    else:
        v = list(STATIONS[0] if y < STATIONS[0][0] else STATIONS[-1])
    sec = section(v[1], v[2], v[3], v[4], v[5], lean_at(y))
    half = sec[:len(sec) // 2 + 1]                     # nose of the ring: (0, zb) .. side .. (0, top)
    best = None
    for (x0, z0), (x1, z1) in zip(half, half[1:]):
        if min(z0, z1) <= z <= max(z0, z1) and z1 != z0:
            x = x0 + (x1 - x0) * (z - z0) / (z1 - z0)
            best = x if best is None else max(best, x)
    return best if best is not None else v[1]


SMOOTH_ANGLE = 60.0 if S.get("smooth") else 35.0   # modern bodies are all curves: shade them smooth


def loft_body():
    bm = bmesh.new()
    rings = []
    dense = []
    for a, b in zip(STATIONS, STATIONS[1:]):
        n = max(1, int(math.ceil((b[0] - a[0]) / 0.5)))
        for k in range(n):
            t = k / n
            dense.append(tuple(a[i] + (b[i] - a[i]) * t for i in range(6)))
    dense.append(STATIONS[-1])
    for (y, w, zb, belt, top, crown) in dense:
        lean = lean_at(y)
        rings.append([bm.verts.new((x, y, z)) for (x, z) in section(w, zb, belt, top, crown, lean)])
    n = len(rings[0])
    for A, B in zip(rings, rings[1:]):
        for i in range(n):
            j = (i + 1) % n
            bm.faces.new((A[i], A[j], B[j], B[i]))
    bm.faces.new(list(reversed(rings[0])))
    bm.faces.new(rings[-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return new_obj(bm, "Body", style=PREFIX, smooth=SMOOTH_ANGLE)


def sbox(kind, *a, **k):
    k.setdefault("style", PREFIX)
    return box(kind, *a, **k)


def scyl(kind, *a, **k):
    k.setdefault("style", PREFIX)
    return cyl(kind, *a, **k)


def sbeam(kind, *a, **k):
    k.setdefault("style", PREFIX)
    return beam(kind, *a, **k)


def sprism(kind, outer, inner):
    return prism(kind, outer, inner, style=PREFIX)


# doors: name, side (+1 = car's left, x > 0), front y, rear y
DOOR_Z0 = ZB + 0.45
DOORS = []
for s in (1, -1):
    sd = "L" if s > 0 else "R"
    if S["doors"] >= 2:
        DOORS.append(("Door" + sd, s, A0 + 0.12, B - 0.03))
    if S["doors"] == 4:
        DOORS.append(("DoorR" + sd, s, B + 0.1, Q))
FUEL_Y = (WY_R + ARCH + 0.35, WY_R + ARCH + 0.95)
FUEL_Y = (FUEL_Y[0] + S.get("FUEL_DY", 0.0), FUEL_Y[1] + S.get("FUEL_DY", 0.0))
FUEL_Z = (belt_at(FUEL_Y[0]) - 0.95, belt_at(FUEL_Y[0]) - 0.4)
FUEL_Z = (FUEL_Z[0] + S.get("FUEL_DZ", 0.0), FUEL_Z[1] + S.get("FUEL_DZ", 0.0))
if FLAV == "sports":
    FUEL_Z = (FUEL_Z[0] - 0.1, FUEL_Z[1] - 0.1)
HINGES, HINGE_OF = {}, {"PanelHood": "Hood", "HoodInner": "Hood", "Lid": "Lid", "PanelFuel": "Fuel", "LidInner": "Lid"}
HINGE_SLOTS = {"Hood": "Hood", "Spoiler": "Lid"}
for (nm, s, y0, y1) in DOORS:
    HINGES[nm] = {"pivot": (s * (W - 0.02), y0, (DOOR_Z0 + BELT) / 2), "axis": (0, 0, 1), "open": -s * 66, "kind": "door"}
HINGES["Hood"] = {"pivot": (0.0, A0 - 0.05, deck_z(0, A0 - 0.05)), "axis": (1, 0, 0), "open": -55 if FLAV != "sports" else -50, "kind": "hood"}
HINGES["Fuel"] = {"pivot": (W + 0.03, FUEL_Y[0], sum(FUEL_Z) / 2), "axis": (0, 0, 1), "open": -80,
                  "kind": "charge" if S.get("electric") else "fuel"}


def cutters_and_body():
    body = loft_body()
    body["loft"] = True
    src = body.data.copy()
    col = bpy.data.collections.new("Cutters")
    bpy.context.scene.collection.children.link(col)

    def cut_box(x0, y0, z0, x1, y1, z1):
        bm = bmesh.new()
        x0, x1 = sorted((x0, x1))
        m = Matrix.Translation(((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2)) @ Matrix.Diagonal((x1 - x0, y1 - y0, z1 - z0, 1))
        bmesh.ops.create_cube(bm, size=1.0, matrix=m)
        me = bpy.data.meshes.new("cut")
        bm.to_mesh(me)
        bm.free()
        ob = bpy.data.objects.new("cut", me)
        col.objects.link(ob)

    def cut_cyl(p0, p1, r):
        p0, p1 = Vector(p0), Vector(p1)
        bm = bmesh.new()
        m = Matrix.Translation((p0 + p1) / 2) @ axis_rot(p1 - p0).to_4x4()
        bmesh.ops.create_cone(bm, cap_ends=True, segments=40, radius1=r, radius2=r, depth=(p1 - p0).length, matrix=m)
        me = bpy.data.meshes.new("cut")
        bm.to_mesh(me)
        bm.free()
        ob = bpy.data.objects.new("cut", me)
        col.objects.link(ob)

    tub = WX - TW / 2 - 0.2
    for wy in (WY_F, WY_R):
        for s in (-1, 1):
            cut_cyl((s * tub, wy, WR), (s * (W + 0.8), wy, WR), ARCH)
    floor = ZB + 0.3
    xin = W - 0.45
    cab_end = BED[0] - 0.25 if BED else (L1 - 0.5 if REAR == "liftgate" else C1 - 0.1)
    def cut_plan(ring, z0):
        """a cutter from a half-width profile [(x, y), ...] (mirrored), from z0 up"""
        plan = [(x, y) for x, y in ring] + [(-x, y) for x, y in reversed(ring)]
        bm = bmesh.new()
        lo = [bm.verts.new((x, y, z0)) for x, y in plan]
        hi = [bm.verts.new((x, y, 20.0)) for x, y in plan]
        bm.faces.new(lo)
        bm.faces.new(list(reversed(hi)))
        n = len(plan)
        for k in range(n):
            bm.faces.new((lo[k], lo[(k + 1) % n], hi[(k + 1) % n], hi[k]))
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
        me = bpy.data.meshes.new("cut")
        bm.to_mesh(me)
        bm.free()
        col.objects.link(bpy.data.objects.new("cut", me))

    if S.get("smooth") and not BED:
        # the canopy narrows toward the tail: the cabin opening narrows under it, or the deck shows holes
        ys_ = [A0 + 0.05 + (cab_end - A0 - 0.05) * k / 24 for k in range(25)]
        cut_plan([(min(xin, gh_xb(y) - 0.12), y) for y in ys_], floor)
    else:
        cut_box(-xin, A0 + 0.05, floor, xin, cab_end, 20)                      # open cabin (+ cargo bay)
    if OPEN:                                                                  # open sides, step-in height
        for s in (-1, 1):
            cut_box(s * (xin - 0.05), A0 + 0.3, ZB + 0.55, s * (W + 0.6), cab_end - 0.05, 20)
    for (nm, s, y0, y1) in DOORS:                                             # door openings
        cut_box(s * (xin - 0.05), y0 - 0.03, DOOR_Z0 - 0.03, s * (W + 0.6), y1 + 0.03, 20)
    if REAR in ("trunk", "hatch") and S.get("smooth"):
        # a rounded tail: the opening follows the plan, or it would cut through the side walls at the corners
        ysl = [C1 + 0.15 + (L1 - 0.6 - C1) * k / 12 for k in range(13)]
        ring = [(min(min(W, station_w(y)) - 0.55, top_w(y) - 0.04 if S.get("smooth") else W), y) for y in ysl]
        plan = [(x, y) for x, y in ring] + [(-x, y) for x, y in reversed(ring)]
        bm = bmesh.new()
        lo = [bm.verts.new((x, y, TAIL - 0.9)) for x, y in plan]
        hi = [bm.verts.new((x, y, 20.0)) for x, y in plan]
        bm.faces.new(lo)
        bm.faces.new(list(reversed(hi)))
        n = len(plan)
        for k in range(n):
            bm.faces.new((lo[k], lo[(k + 1) % n], hi[(k + 1) % n], hi[k]))
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
        me = bpy.data.meshes.new("cut")
        bm.to_mesh(me)
        bm.free()
        col.objects.link(bpy.data.objects.new("cut", me))
    elif REAR in ("trunk", "hatch"):
        cut_box(-(W - 0.55), C1 + 0.15, TAIL - 0.9, W - 0.55, L1 - 0.45, 20)
    elif REAR == "liftgate":
        cut_box(-(W - 0.55), L1 - 0.6, ZB + 0.75, W - 0.55, L1 + 1.0, 20)
    if BED:
        bf = ZB + 0.75
        cut_box(-(W - 0.3), BED[0], bf, W - 0.3, BED[1] - 0.3, 20)
        cut_box(-(W - 0.32), BED[1] - 0.35, bf, W - 0.32, L1 + 1.0, 20)
    col.hide_render = True
    m = body.modifiers.new("cut", "BOOLEAN")
    m.operation, m.operand_type, m.collection, m.solver = "DIFFERENCE", "COLLECTION", col, "EXACT"
    bake(body)
    for ob in list(col.objects):
        bpy.data.objects.remove(ob)
    bpy.data.collections.remove(col)
    # linings: wheel wells, cabin floor, trunk tub, bed
    for wy in (WY_F, WY_R):
        for s in (-1, 1):
            liner(s * (tub + 0.01), s * (tub + 0.05), wy)
            if S.get("smooth"):
                arch_tunnel(s, tub, wy)
    if S.get("smooth"):                                   # slices: the floor narrows with a rounded tail
        ya_, yb_ = A0 + 0.1, cab_end - 0.05
        n_ = max(1, int((yb_ - ya_) / 0.4))
        for i_ in range(n_):
            y0_, y1_ = ya_ + (yb_ - ya_) * i_ / n_, ya_ + (yb_ - ya_) * (i_ + 1) / n_
            xh_ = min(xin, body_x(y0_, floor) - 0.1, body_x(y1_, floor) - 0.1)
            flat_floor("Carpet", xh_, y0_, y1_, floor - 0.02, floor + 0.06)
    else:
        flat_floor("Carpet", xin, A0 + 0.1, cab_end - 0.05, floor - 0.02, floor + 0.06)
    wheel_houses("Under" if S.get("smooth") else "Carpet", xin, A0 + 0.05, cab_end, floor)   # seen through the arches
    if OPEN:                                                                  # rubber edge trim round the step-in + a sill plate
        for s in (-1, 1):
            xa, xb_ = s * (xin - 0.06), s * (W + 0.015)
            for ya in (A0 + 0.3, cab_end - 0.05):
                sbox("Under", xa, ya - 0.025, ZB + 0.53, xb_, ya + 0.025, belt_at(ya) + 0.02)
            sbox("Chrome", xa, A0 + 0.3, ZB + 0.53, xb_, cab_end - 0.05, ZB + 0.57)
        sbox("Carpet", -(xin - 0.01), cab_end - 0.03, floor, xin - 0.01, cab_end + 0.005, belt_at(cab_end) - 0.06)   # bulkhead lining
    if REAR in ("trunk", "hatch"):
        tz = TAIL - 0.95
        if S.get("smooth"):                               # a rounded tail: the floor narrows with the plan
            ya, yb = C1 + 0.15, L1 - 0.45
            nsl = 10
            for k in range(nsl):
                y0s, y1s = ya + (yb - ya) * k / nsl, ya + (yb - ya) * (k + 1) / nsl
                flat_floor("Under", min(W, station_w(y1s)) - 0.65, y0s, y1s, tz, tz + 0.05)
        else:
            flat_floor("Under", W - 0.6, C1 + 0.15, L1 - 0.45, tz, tz + 0.05)
        wheel_houses("Under", W - 0.6, C1 + 0.15, L1 - 0.45, tz)
    if BED:
        bf = ZB + 0.75
        flat_floor("Dark", W - 0.3, BED[0], L1 - 0.35, bf - 0.05, bf + 0.02)
        wheel_houses("Dark", W - 0.3, BED[0], L1 - 0.35, bf)
        for i in range(7):                                                     # bed floor ribs (between the humps)
            x = -(W - 0.6) + i * (2 * (W - 0.6)) / 6
            if abs(x) < house_x() - 0.1:
                sbox("Dark", x - 0.06, BED[0] + 0.1, bf + 0.02, x + 0.06, L1 - 0.4, bf + 0.06)
    return src


# ---- wheel wells inside the body: floors stop at the wheel houses, which are hollow humps over each tyre
def house_x():
    return WX - TW / 2 - 0.25                     # inner wall of a wheel house (just inboard of the tyre)


def house_top():
    return WR + ARCH + 0.1                         # over the arch, so the tyre has the arch's room to move


def arches_in(y0, y1):
    """the wheel arches whose y-range [wy - ARCH, wy + ARCH] overlaps y0..y1"""
    return [wy for wy in (WY_F, WY_R) if wy + ARCH + 0.05 > y0 and wy - ARCH - 0.05 < y1]


def flat_floor(kind, xh, y0, y1, z0, z1):
    """a floor xh wide each side, narrowed to between the wheel houses where it passes over a wheel"""
    if y1 <= y0:
        return
    cuts = sorted((max(y0, wy - ARCH - 0.05), min(y1, wy + ARCH + 0.05)) for wy in arches_in(y0, y1))
    y = y0
    for a, b in cuts:
        if a > y:
            sbox(kind, -xh, y, z0, xh, a, z1)
        if z0 < house_top():
            sbox(kind, -min(xh, house_x()), a, z0, min(xh, house_x()), b, z1)
        else:
            sbox(kind, -xh, a, z0, xh, b, z1)
        y = b
    if y < y1:
        sbox(kind, -xh, y, z0, xh, y1, z1)


def wheel_houses(kind, xh, y0, y1, z0):
    """hollow humps (inner wall, top, end walls) over every tyre whose arch passes under this floor"""
    top = house_top()
    if z0 >= top - 0.05:
        return
    hx = house_x()
    for wy in arches_in(y0, y1):
        a, b = max(y0, wy - ARCH - 0.05), min(y1, wy + ARCH + 0.05)
        def lim(y, x):                                    # a rounded/tucked tail: stay inside the skin
            if not S.get("smooth"):
                return x
            return min(x, min(body_x(y, z0 + (top - z0) * k / 4) for k in range(5)) - 0.08)
        for s in (-1, 1):
            xt = lim(a, lim(b, xh))
            hx_ = min(hx, xt)
            sbox(kind, s * (hx_ - 0.06), a, z0 - 0.02, s * hx_, b, top)             # inner wall
            sbox(kind, s * (hx_ - 0.06), a, top - 0.06, s * xt, b, top)              # top
            for ye in (a, b):
                if y0 + 0.01 < ye < y1 - 0.01:                                     # end walls inside the floor
                    sbox(kind, s * (hx_ - 0.06), ye - 0.03, z0 - 0.02, s * lim(ye, xh), ye + 0.03, top)


def liner(x0, x1, wy):
    """the wheel well's back wall: a disc the size of the arch, cut flat at the rocker so none of it shows under the car"""
    bm = bmesh.new()
    pts = []
    for i in range(32):
        a = 2 * math.pi * i / 32
        pts.append((wy + ARCH * math.cos(a), max(WR + ARCH * math.sin(a), ZB - 0.02)))
    vs0 = [bm.verts.new((x0, y, z)) for y, z in pts]
    vs1 = [bm.verts.new((x1, y, z)) for y, z in pts]
    bm.faces.new(vs0)
    bm.faces.new(list(reversed(vs1)))
    for k in range(32):
        bm.faces.new((vs0[k], vs0[(k + 1) % 32], vs1[(k + 1) % 32], vs1[k]))
    bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=1e-4)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    new_obj(bm, "Under", style=PREFIX)


def arch_tunnel(s, x_in, wy):
    """the wheel arch's ceiling, lined dark from the well's back wall out to the skin (the cut body shows otherwise)"""
    bm = bmesh.new()
    n = 24
    r0, r1 = ARCH + 0.045, ARCH + 0.005                    # just outside the cut, so a bumped tyre clears it
    rows = []
    for k in range(n + 1):
        a = math.pi * k / n
        c = math.sin(a)
        if WR + ARCH * c < ZB:
            continue
        yy_ = wy + ARCH * math.cos(a)
        xo = min(W, station_w(yy_), body_x(yy_, WR + ARCH * c) if S.get("smooth") else W) - (0.1 if S.get("SQUARE") else 0.03)   # inside the skin
        rows.append([bm.verts.new((s * x, wy + r * math.cos(a), max(ZB - 0.02, WR + r * c)))
                     for x in (x_in, xo) for r in (r0, r1)])
    for A, B in zip(rows, rows[1:]):
        bm.faces.new((A[0], A[2], B[2], B[0]))          # outer face (toward the tyre)
        bm.faces.new((A[1], B[1], B[3], A[3]))          # inner face
        bm.faces.new((A[0], B[0], B[1], A[1]))          # inboard edge
        bm.faces.new((A[2], A[3], B[3], B[2]))          # outboard edge
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    new_obj(bm, "Under", style=PREFIX)


def hinge_panel_shell(bm, kind, t, hinge):
    new_obj(shell(bm, t), kind, style=PREFIX, smooth=SMOOTH_ANGLE)
    HINGE_OF[kind] = hinge


def build_doors(src):
    for (nm, s, y0, y1) in DOORS:
        bm = bmesh.new()
        bm.from_mesh(src)
        xin = W - 0.5
        for co, no in (((0, y0, 0), (0, 1, 0)), ((0, y1, 0), (0, 1, 0)), ((0, 0, DOOR_Z0), (0, 0, 1)), ((s * xin, 0, 0), (1, 0, 0))):
            bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], plane_co=co, plane_no=no)
        drop = [f for f in bm.faces if not (y0 < f.calc_center_median().y < y1 and f.calc_center_median().z > DOOR_Z0 and s * f.calc_center_median().x > xin)]
        bmesh.ops.delete(bm, geom=drop, context="FACES")
        sd = nm[4:]
        new_obj(shell(bm, 0.12), "DoorJamb" + sd, style=PREFIX, smooth=SMOOTH_ANGLE)
        new_obj(bm, "PanelDoor" + sd, style=PREFIX, smooth=SMOOTH_ANGLE)
        HINGE_OF["PanelDoor" + sd] = HINGE_OF["DoorJamb" + sd] = nm
        for yy in (y0 - 0.015, y1 + 0.015) if not S.get("smooth") else ():     # shut lines (smooth: smooth_details)
            sbox("Seam", s * (W - 0.25), yy - 0.012, DOOR_Z0 - 0.03, s * (W - 0.01), yy + 0.012, belt_at(yy) + 0.05)
        sbox("Chrome", s * (W + 0.02) - 0.04, y1 - 0.75, BELT - 0.42, s * (W + 0.02) + 0.04, y1 - 0.3, BELT - 0.34, bev=0.02)   # handle


# ------------------------------------------------------------------ greenhouse
def gx(z):
    zb = BELT + 0.05
    return (W - 0.32) - TUCK * (z - zb) / (ROOF - zb)


def greenhouse():
    zb = BELT + 0.05
    xt = gx(ROOF)
    roof_rear = C0 if not OPEN else BED[0] - 0.05
    sbox("PanelRoof", -xt - 0.08, A1 - 0.1, ROOF, xt + 0.08, roof_rear + 0.1, ROOF + 0.14, bev=0.06)
    xb = gx(zb)
    sprism("Glass", [(-xb, A0, zb), (xb, A0, zb), (xt - 0.06, A1, ROOF), (-(xt - 0.06), A1, ROOF)],
           [(-xb, A0 + 0.06, zb - 0.04), (xb, A0 + 0.06, zb - 0.04), (xt - 0.06, A1 + 0.06, ROOF - 0.04), (-(xt - 0.06), A1 + 0.06, ROOF - 0.04)])
    # rear glass: on the body (trunk), on the hatch / liftgate (Lid), or the cab's back window (pickup)
    if OPEN:                                              # canopy: windshield, A posts, rear posts, no side or back glass
        for s in (-1, 1):
            sbeam("RoofBody", (s * xb, A0, zb), (s * xt, A1, ROOF), 0.16, 0.16)
            sbeam("RoofBody", (s * (xt + 0.04), A1, ROOF + 0.02), (s * (xt + 0.04), roof_rear, ROOF + 0.02), 0.08, 0.12)
            sbeam("RoofBody", (s * xb, BED[0] - 0.15, zb - 0.1), (s * xt, BED[0] - 0.15, ROOF), 0.16, 0.16)
        sbeam("RoofBody", (-xb, BED[0] - 0.15, zb + 1.1), (xb, BED[0] - 0.15, zb + 1.1), 0.1, 0.1)   # grab bar
        return
    if REAR == "trunk" or BED:
        k = "RoofGlass"
        y_top, y_bot = (C0, C1) if not BED else (C0, C1)
        sprism(k, [(-(xt - 0.06), y_top, ROOF), (xt - 0.06, y_top, ROOF), (xb, y_bot, zb), (-xb, y_bot, zb)],
               [(-(xt - 0.06), y_top - 0.06, ROOF - 0.04), (xt - 0.06, y_top - 0.06, ROOF - 0.04), (xb, y_bot - 0.06, zb - 0.04), (-xb, y_bot - 0.06, zb - 0.04)])
    for s in (-1, 1):
        sbeam("RoofBody", (s * xb, A0, zb), (s * xt, A1, ROOF), 0.18, 0.18)                        # A pillar
        sbeam("RoofBody", (s * (xt + 0.04), A1, ROOF + 0.02), (s * (xt + 0.04), roof_rear, ROOF + 0.02), 0.08, 0.12)  # roof rail
        # windows between the pillars: front door, rear door (4 doors), quarter
        def win(pts, quarter=False):
            blind = quarter and S.get("blind")                # panel van / armoured body: no rear side glass
            outer = [(s * gx(z), y, z) for (y, z) in pts]
            inner = [(s * (gx(z) - (0.14 if blind else 0.05)), y, z) for (y, z) in pts]
            sprism("RoofBody" if blind else "RoofGlass", outer, inner)
        ya = lambda z: A0 + (A1 - A0) * (z - zb) / (ROOF - zb)
        top = ROOF - 0.08
        win([(ya(zb + 0.03) + 0.3, zb), (ya(top) + 0.08, top), (B - 0.12, top), (B - 0.12, zb)])
        sbeam("RoofBody", (s * gx(zb), B, zb), (s * gx(ROOF), B, ROOF), 0.12, 0.26)                 # B pillar
        if S["doors"] == 4:
            win([(B + 0.14, zb), (B + 0.14, top), (Q - 0.1, top), (Q - 0.1, zb)])
            last = Q
            sbeam("RoofBody", (s * gx(zb), Q + 0.02, zb), (s * gx(ROOF), Q + 0.02, ROOF), 0.12, 0.22)
        else:
            last = B
        if REAR == "trunk" or REAR == "hatch":
            # quarter window up to the C pillar line, then a body-colour sail
            yc = lambda z: C1 + (C0 - C1) * (z - zb) / (ROOF - zb)
            if yc(top) - last > 0.6:
                win([(last + 0.15, zb), (last + 0.15, top), (yc(top) - 0.25, top), (yc(zb + 0.4) - 0.3, zb + 0.4), (yc(zb + 0.4) - 0.3, zb)])
            sbeam("RoofBody", (s * gx(ROOF), C0, ROOF), (s * gx(zb), C1, zb), 0.16, 0.3)
        elif REAR == "liftgate":
            win([(last + 0.15, zb), (last + 0.15, top), (C0 - 0.2, top), (C0 - 0.2, zb)], quarter=True)
            sbeam("RoofBody", (s * gx(zb), C0, zb), (s * gx(ROOF), C0, ROOF), 0.16, 0.3)             # D pillar
        elif BED:
            sbeam("RoofBody", (s * gx(zb), C1, zb), (s * gx(ROOF), C0, ROOF), 0.16, 0.24)


# ------------------------------------------------------------------ smooth greenhouse (modern bodies)
# One curved canopy instead of flat panels on posts: the roofline is a smooth curve from the windshield base over a
# crown near the B pillar down the liftback to the deck, and every cross-section is a superellipse (rounded top,
# tumblehome sides). The canopy grid is then cut by angle and position into windshield, roof, hatch glass, pillars,
# side glass and a chrome window surround.
GH_P = 2 / S.get("GH_N", 3.4)                                   # superellipse exponent (2/n)


def solid_grid(kind, O, I, cells, smooth=30.0):
    """a closed piece from two matching grids (outer, inner) over the given (j, i) cells"""
    bm = bmesh.new()
    vo, vi = {}, {}

    def vert(j, i):
        if (j, i) not in vo:
            vo[(j, i)] = bm.verts.new(O[j][i])
            vi[(j, i)] = bm.verts.new(I[j][i])
        return vo[(j, i)], vi[(j, i)]
    cells = set(cells)
    for (j, i) in cells:
        q = [(j, i), (j, i + 1), (j + 1, i + 1), (j + 1, i)]
        o = [vert(*k)[0] for k in q]
        n = [vert(*k)[1] for k in q]
        bm.faces.new(o)
        bm.faces.new(list(reversed(n)))
        for a, b, nb in ((0, 1, (j - 1, i)), (1, 2, (j, i + 1)), (2, 3, (j + 1, i)), (3, 0, (j, i - 1))):
            if nb not in cells:
                bm.faces.new((o[b], o[a], n[a], n[b]))
    bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=1e-6)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return new_obj(bm, kind, style=PREFIX, smooth=smooth)


def gh_frame():
    zb = BELT + 0.05
    yend = C1 + 0.17
    zend = max(zb + 0.04, deck_z(0, yend) - 0.02)
    pk = A1 + (C0 - A1) * 0.45
    mws = (ROOF + 0.02 - zb) / (A1 - A0)
    mrear = (zend - (ROOF - 0.1)) / (yend - C0)
    z0_ = max(zb, HOOD - 0.05) if S.get("smooth") else zb       # the windshield rises from the cowl (hood height)
    knots = [(A0, z0_, 1.2 * mws), (A1, ROOF + 0.02, 0.35 * mws), (pk, ROOF + 0.14, 0.0), (C0, ROOF - 0.1, 0.8 * mrear),
             (yend, zend, 1.15 * mrear)]
    return zb, yend, knots


GH_ZB, GH_YEND, GH_KNOTS = gh_frame()


def gh_zr(y):
    """roofline (outer skin, centre line)"""
    k = GH_KNOTS
    y = min(max(y, k[0][0]), k[-1][0])
    for (y0, z0, m0), (y1, z1, m1) in zip(k, k[1:]):
        if y <= y1:
            h = y1 - y0
            t = (y - y0) / h
            return ((2 * t ** 3 - 3 * t ** 2 + 1) * z0 + (t ** 3 - 2 * t ** 2 + t) * h * m0 + (-2 * t ** 3 + 3 * t ** 2) * z1
                    + (t ** 3 - t ** 2) * h * m1)
    return k[-1][1]


def gh_xb(y):
    """half width of the canopy at the belt"""
    sm = lambda t: (lambda c: c * c * (3 - 2 * c))(min(1.0, max(0.0, t)))
    front = 0.45 if S.get("smooth") else 0.2
    if S.get("smooth"):                                  # the canopy narrows from the roof's rear into the tail (teardrop)
        t = min(1.0, max(0.0, (y - C0) / (GH_YEND - C0)))
        sq = 0.035 * S.get("SQUARE", 0.0)                # squarer shoulders move the deck edge out; the canopy follows
        xb = W * (0.9 + sq) - S.get("GH_IN", 0.3) - front * (1 - sm((y - A0) / 1.4)) - 1.3 * t ** 1.6
        return min(xb, (0.9 + sq - lean_at(y)) * station_w(y) - 0.06)       # never past the (tucked) shoulder
    return W - 0.3 - 0.2 * (1 - sm((y - A0) / 1.0)) - 0.35 * sm((y - Q) / (GH_YEND - Q))


def gh_pt(y, phi):
    c, s_ = math.cos(phi), math.sin(phi)
    xb, h = gh_xb(y), max(0.0, gh_zr(y) - GH_ZB)
    return Vector((xb * math.copysign(abs(c) ** GH_P, c), y, GH_ZB + h * abs(s_) ** GH_P))


def roof_z(x, y):
    """height of the canopy's outer skin at (x, y)"""
    xb, h = gh_xb(y), max(0.0, gh_zr(y) - GH_ZB)
    u = min(1.0, abs(x) / xb)
    c = u ** (1 / GH_P)
    return GH_ZB + h * math.sqrt(max(0.0, 1 - c * c)) ** GH_P


WS_END = A1 - S.get("WS_BACK", 0.0)                 # where the windshield glass meets the roof panel (top view)
GH_TOP = 46.5 if S.get("DLO") else 36.0             # side glass's top edge (degrees round the canopy section)


def dlo_lo(y):
    """window's lower edge angle: rises toward the rear like the reference's belt kick"""
    d = S.get("DLO", {})
    u = min(1.0, max(0.0, (y - (A0 + 1.0)) / (d.get("tip", 6.3) - A0 - 1.0)))
    return 3.0 + d.get("kick", 9.0) * u ** 1.3


def dlo_hi(y):
    """window's upper edge angle: level along the roof, then sweeping down to meet the lower edge at the tip"""
    d = S.get("DLO", {})
    tip, y0 = d.get("tip", 6.3), d.get("sweep", (Q or B) - 0.8)
    lo = dlo_lo(y)
    if y <= y0:
        return GH_TOP
    g = min(1.0, max(0.0, (tip - y) / (tip - y0)))
    return lo + (GH_TOP - lo) * math.sqrt(max(0.0, 1 - (1 - g) ** 2))


def dlo_front(z):
    """window's front edge (y) at height z: parallel to the windshield pillar"""
    v = min(1.0, max(0.0, (z - GH_ZB) / max(0.1, ROOF - GH_ZB)))
    return A0 + 0.3 + (A1 - A0 - 0.1) * v


A_PILLAR = 0.24                                       # body-coloured pillar between windshield and side glass


def ws_side(t, z):
    """the windshield's side edge (y) at angle t: the A-pillar line, rounding into the roof's front edge on top"""
    return min(dlo_front(z) - 0.12 - A_PILLAR, WS_END + 0.07 * max(0.0, 50 - t))


def dlo_kind(y, t, z):
    if t > 50:
        return "Glass" if y < WS_END else ("PanelRoof" if y < C0 else "RoofGlass__Lid")
    lo, hi = dlo_lo(y), dlo_hi(y)
    yf = dlo_front(z)
    if y < ws_side(t, z) and t >= lo:                     # the windshield wraps down to the A-pillars
        return "Glass"
    if y < yf - 0.12 or hi <= lo + 0.4:
        return "RoofBody"
    if y < yf:
        return "RoofChrome" if lo - 2.6 <= t <= hi + 3.0 else "RoofBody"
    if lo <= t <= hi:
        if B - 0.08 < y < B + 0.1 or (Q and Q - 0.06 < y < Q + 0.07):
            return "RoofBody"
        return "RoofGlass"
    if lo - 2.6 <= t < lo or hi < t <= hi + 3.0:
        return "RoofChrome"
    return "RoofBody"


def dlo_greenhouse(ys, phis, O, N, nj, ni):
    """the canopy cut into its pieces along the reference's window outline: cells the outline crosses are split
    along it (no stair steps)"""
    ang = [math.degrees(min(p, math.pi - p)) for p in phis]
    bounds = [lambda y, t, z: t - dlo_lo(y), lambda y, t, z: t - (dlo_lo(y) - 2.6), lambda y, t, z: t - dlo_hi(y),
              lambda y, t, z: t - (dlo_hi(y) + 3.0), lambda y, t, z: y - dlo_front(z), lambda y, t, z: y - (dlo_front(z) - 0.12),
              lambda y, t, z: y - WS_END, lambda y, t, z: y - (B - 0.08), lambda y, t, z: y - (B + 0.1),
              lambda y, t, z: y - ws_side(t, z)]
    if Q:
        bounds += [lambda y, t, z: y - (Q - 0.06), lambda y, t, z: y - (Q + 0.07)]
    thick = {"Glass": 0.05, "RoofGlass": 0.05, "RoofGlass__Lid": 0.05, "PanelRoof": 0.1, "RoofBody": 0.08, "RoofChrome": 0.06}
    groups, polys = {}, []
    for j in range(nj - 1):
        for i in range(ni - 1):
            q = [(j, i), (j, i + 1), (j + 1, i + 1), (j + 1, i)]
            yc = (ys[j] + ys[j + 1]) / 2
            tc = (ang[i] + ang[i + 1]) / 2
            zc = sum(O[a][b].z for a, b in q) / 4
            kinds = {dlo_kind(ys[a] + (yc - ys[a]) * 0.02, ang[b] + (tc - ang[b]) * 0.02, O[a][b].z) for a, b in q}
            if len(kinds) == 1:
                groups.setdefault(dlo_kind(yc, tc, zc), []).append((j, i))
                continue
            # clip the cell by every outline it crosses in turn (corners where two outlines meet stay clean)
            cell = [[(O[a][b], N[a][b], ys[a], ang[b]) for a, b in q]]
            for fb in bounds:
                nxt = []
                for poly in cell:
                    f = [fb(y_, t_, p_.z) for (p_, n_, y_, t_) in poly]
                    if not (min(f) < 0 < max(f)):
                        nxt.append(poly)
                        continue
                    for sgn in (-1, 1):
                        out_ = []
                        for m in range(len(poly)):
                            v0, v1 = poly[m], poly[(m + 1) % len(poly)]
                            f0, f1 = f[m], f[(m + 1) % len(poly)]
                            if f0 * sgn >= 0:
                                out_.append(v0)
                            if (f0 < 0) != (f1 < 0):
                                u = f0 / (f0 - f1)
                                out_.append((v0[0].lerp(v1[0], u), v0[1].lerp(v1[1], u).normalized(),
                                             v0[2] + (v1[2] - v0[2]) * u, v0[3] + (v1[3] - v0[3]) * u))
                        if len(out_) >= 3:
                            nxt.append(out_)
                cell = nxt
            for poly in cell:
                cy = sum(v[2] for v in poly) / len(poly)
                ct = sum(v[3] for v in poly) / len(poly)
                cz = sum(v[0].z for v in poly) / len(poly)
                polys.append((dlo_kind(cy, ct, cz), [v[0] for v in poly], [v[1] for v in poly]))
            done = True
            if not done:
                groups.setdefault(dlo_kind(yc, tc, zc), []).append((j, i))
    for k, cells in groups.items():
        t = thick[k]
        I = [[O[j][i] - N[j][i] * t for i in range(ni)] for j in range(nj)]
        solid_grid(k, O, I, cells, smooth=40.0 if k != "RoofChrome" else 20.0)
    for k, pts, nrm in polys:
        sprism(k, [tuple(p) for p in pts], [tuple(p - n * thick[k]) for p, n in zip(pts, nrm)])
    HINGE_OF["RoofGlass__Lid"] = "Lid"


def greenhouse_smooth():
    ys = [A0 + i * 0.1 for i in range(int((GH_YEND - A0) / 0.1) + 1)]
    keys = [A0, A0 + 0.9, A1, B - 0.1, B + 0.14, C0, GH_YEND]
    for (nm, s_, y0, y1) in DOORS:
        keys += [y0, y1]
    if Q:
        keys += [Q - 0.1, Q + 0.12]
    keys = [k for k in keys if A0 <= k <= GH_YEND]
    ys = sorted(set(keys) | {y for y in ys if min(abs(y - k) for k in keys) > 0.035})
    # side angles (deg): chrome sill | side glass | chrome | rail | roof / windshield / hatch glass
    th = [0, 3, 11.25, 19.5, 27.75, 36, 39, 42.5, 46] + [46 + i * 5.5 for i in range(1, 9)]
    if S.get("DLO"):                                      # finer bands: the window outline is cut along its own curve
        th = [0, 1.5, 3, 5, 7, 9, 11, 13, 15, 18, 22, 26, 30, 34, 38, 41, 44, 47, 50] + [50 + i * 5 for i in range(1, 9)]
    phis = [math.radians(t) for t in th] + [math.radians(180 - t) for t in reversed(th[:-1])]
    O = [[gh_pt(y, ph) for ph in phis] for y in ys]
    nj, ni = len(ys), len(phis)
    qa_, qb_ = S.get("QWIN", (1.55, 1.1))                 # the quarter window's rear edge: its foot, and its lean
    q_end = lambda z: (Q if Q else B) + qa_ - qb_ * (z - GH_ZB) / (ROOF - GH_ZB)
    N = []
    for j in range(nj):
        row = []
        for i in range(ni):
            dy = O[min(j + 1, nj - 1)][i] - O[max(j - 1, 0)][i]
            dp = O[j][min(i + 1, ni - 1)] - O[j][max(i - 1, 0)]
            n = dp.cross(dy)
            if n.length < 1e-6:
                n = Vector((0, 0, 1))
            n.normalize()
            if n.dot(O[j][i] - Vector((0, O[j][i].y, GH_ZB - 1.0))) < 0:
                n = -n
            row.append(n)
        N.append(row)

    if S.get("DLO"):
        return dlo_greenhouse(ys, phis, O, N, nj, ni)

    def kind_of(yc, t, zc):
        if t > 46:
            return "Glass" if yc < A1 else ("PanelRoof" if yc < C0 else "RoofGlass__Lid")
        if t > 39:
            return "RoofBody"
        dlo = A0 + 0.9 < yc < q_end(zc)
        if t > 36 or t < 3:
            return "RoofChrome" if dlo else "RoofBody"
        if not dlo or B - 0.1 < yc < B + 0.14 or (Q and Q - 0.1 < yc < Q + 0.12):
            return "RoofBody"
        return "RoofGlass"
    thick = {"Glass": 0.05, "RoofGlass": 0.05, "RoofGlass__Lid": 0.05, "PanelRoof": 0.1, "RoofBody": 0.08, "RoofChrome": 0.06}
    groups, cut = {}, []
    for j in range(nj - 1):
        for i in range(ni - 1):
            ph = (phis[i] + phis[i + 1]) / 2
            t = math.degrees(min(ph, math.pi - ph))
            yc = (ys[j] + ys[j + 1]) / 2
            zc = (O[j][i].z + O[j + 1][i + 1].z) / 2
            if t <= 39:
                # the quarter window's rear edge slants across the grid: cut that cell along the line itself
                q = [(j, i), (j, i + 1), (j + 1, i + 1), (j + 1, i)]
                f = [O[a][b].y - q_end(O[a][b].z) for a, b in q]
                if min(f) < 0 < max(f):
                    kf, kb = kind_of(q_end(zc) - 0.02, t, zc), kind_of(q_end(zc) + 0.02, t, zc)
                    if kf != kb:
                        cut.append((q, f, kf, kb))
                        continue
            groups.setdefault(kind_of(yc, t, zc), []).append((j, i))
    for k, cells in groups.items():
        t = thick[k]
        I = [[O[j][i] - N[j][i] * t for i in range(ni)] for j in range(nj)]
        solid_grid(k, O, I, cells, smooth=40.0 if k != "RoofChrome" else 20.0)
    for q, f, kf, kb in cut:                               # each cut cell: the part before the line, the part after
        P = [O[a][b] for a, b in q]
        Nn = [N[a][b] for a, b in q]
        for kk, sgn in ((kf, -1), (kb, 1)):
            outer, inner = [], []
            for m in range(4):
                p0, p1, f0, f1 = P[m], P[(m + 1) % 4], f[m], f[(m + 1) % 4]
                n0, n1 = Nn[m], Nn[(m + 1) % 4]
                if f0 * sgn >= 0:
                    outer.append(p0)
                    inner.append(p0 - n0 * thick[kk])
                if (f0 < 0) != (f1 < 0):
                    u = f0 / (f0 - f1)
                    pc, nc = p0.lerp(p1, u), n0.lerp(n1, u).normalized()
                    outer.append(pc)
                    inner.append(pc - nc * thick[kk])
            if len(outer) >= 3:
                sprism(kk, [tuple(v) for v in outer], [tuple(v) for v in inner])
    HINGE_OF["RoofGlass__Lid"] = "Lid"


# ------------------------------------------------------------------ hood, rear opening, gas door, engine bay
def build_rear():
    xw = W - 0.57
    if REAR in ("trunk", "hatch"):
        lid = bmesh.new()
        nx, ny = 12, 10
        y0, y1 = C1 + 0.17, L1 - 0.47
        top, bot = [], []
        for j in range(ny + 1):
            y = y0 + (y1 - y0) * j / ny
            rt, rb = [], []
            xr = min(xw, station_w(y) - 0.57, top_w(y) - 0.06) if S.get("smooth") else xw     # stays on the deck's top
            for i in range(nx + 1):
                x = -xr + 2 * xr * i / nx
                z = deck_z(x, y)
                rt.append(lid.verts.new((x, y, z + 0.005)))
                rb.append(lid.verts.new((x, y, z - 0.09)))
            top.append(rt)
            bot.append(rb)
        for j in range(ny):
            for i in range(nx):
                lid.faces.new((top[j][i], top[j][i + 1], top[j + 1][i + 1], top[j + 1][i]))
                lid.faces.new((bot[j][i], bot[j + 1][i], bot[j + 1][i + 1], bot[j][i + 1]))
        for i in range(nx):
            lid.faces.new((top[0][i], bot[0][i], bot[0][i + 1], top[0][i + 1]))
            lid.faces.new((top[ny][i], top[ny][i + 1], bot[ny][i + 1], bot[ny][i]))
        for j in range(ny):
            lid.faces.new((top[j][0], top[j + 1][0], bot[j + 1][0], bot[j][0]))
            lid.faces.new((top[j][nx], bot[j][nx], bot[j + 1][nx], top[j + 1][nx]))
        bmesh.ops.recalc_face_normals(lid, faces=lid.faces[:])
        new_obj(lid, "Lid", style=PREFIX, smooth=30.0)
        if REAR == "trunk":
            HINGES["Lid"] = {"pivot": (0.0, y0, deck_z(0, y0)), "axis": (1, 0, 0), "open": 60, "kind": "trunk"}
        else:
            # hatch: the rear glass rides on the lid, hinged at the roof
            zb, xt = BELT + 0.05, gx(ROOF)
            xb = gx(zb)
            k = "RoofGlass__Lid"
            HINGE_OF[k] = "Lid"
            if S.get("smooth"):                           # the hatch glass is part of the curved canopy
                HINGES["Lid"] = {"pivot": (0.0, C0, gh_zr(C0)), "axis": (1, 0, 0), "open": 48, "kind": "hatch"}
                return
            sprism(k, [(-(xt - 0.06), C0, ROOF), (xt - 0.06, C0, ROOF), (xb - 0.1, y0, deck_z(0, y0) + 0.02), (-(xb - 0.1), y0, deck_z(0, y0) + 0.02)],
                   [(-(xt - 0.06), C0 - 0.06, ROOF - 0.04), (xt - 0.06, C0 - 0.06, ROOF - 0.04), (xb - 0.1, y0 - 0.06, deck_z(0, y0) - 0.03), (-(xb - 0.1), y0 - 0.06, deck_z(0, y0) - 0.03)])
            HINGES["Lid"] = {"pivot": (0.0, C0, ROOF), "axis": (1, 0, 0), "open": 48, "kind": "hatch"}
    elif REAR == "liftgate":
        z0, z1 = ZB + 0.78, BELT + 0.1
        yb = L1 - 0.05
        sbox("Lid", -xw, yb - 0.16, z0, xw, yb, z1, bev=0.04)
        sbox("Chrome__Lid", -0.6, yb - 0.02, z1 - 0.65, 0.6, yb + 0.03, z1 - 0.55)
        HINGE_OF["Chrome__Lid"] = "Lid"
        zb, xt = BELT + 0.05, gx(ROOF)
        k = "RoofGlass__Lid"
        HINGE_OF[k] = "Lid"
        sprism(k, [(-(xt - 0.1), C0 + 0.15, ROOF - 0.05), (xt - 0.1, C0 + 0.15, ROOF - 0.05), (xw, yb - 0.08, z1 + 0.05), (-xw, yb - 0.08, z1 + 0.05)],
               [(-(xt - 0.1), C0 + 0.09, ROOF - 0.09), (xt - 0.1, C0 + 0.09, ROOF - 0.09), (xw, yb - 0.14, z1 + 0.02), (-xw, yb - 0.14, z1 + 0.02)])
        sbox("Lid", -(xt + 0.05), C0 - 0.05, ROOF - 0.1, xt + 0.05, C0 + 0.35, ROOF + 0.12, bev=0.04)   # gate header
        HINGES["Lid"] = {"pivot": (0.0, C0 + 0.1, ROOF + 0.05), "axis": (1, 0, 0), "open": 78, "kind": "liftgate"}
    elif REAR == "tailgate":
        bf = ZB + 0.75
        yb = L1 - 0.08
        sbox("Lid", -(W - 0.35), yb - 0.18, bf, W - 0.35, yb, BELT - 0.02, bev=0.04)
        sbox("Chrome__Lid", -0.5, yb - 0.02, BELT - 0.5, 0.5, yb + 0.03, BELT - 0.35)
        HINGE_OF["Chrome__Lid"] = "Lid"
        HINGES["Lid"] = {"pivot": (0.0, yb - 0.09, bf), "axis": (1, 0, 0), "open": -88, "kind": "tailgate"}


def build_fuel_door():
    y0, y1 = FUEL_Y
    z0, z1 = FUEL_Z
    W = min(globals()["W"], body_x((y0 + y1) / 2, (z0 + z1) / 2) - 0.05) if S.get("smooth") else globals()["W"]   # under the cast flap
    if S.get("smooth"):
        # a rounded tail: the flap and its port are placed on the skin's own normal once the body exists
        HINGES["Fuel"]["pivot"] = (W + 0.03, y0, (z0 + z1) / 2)
        return
    sbox("Under", W - 0.04, y0 + 0.06, z0 + 0.06, W - 0.005, y1 - 0.06, z1 - 0.06)
    c = (W - 0.005, (y0 + y1) / 2, (z0 + z1) / 2)
    if S.get("electric"):                                  # charge port: a socket with two pins
        scyl("Dark", c, (W + 0.012, c[1], c[2]), 0.17, seg=16)
        for dz in (-0.05, 0.05):
            scyl("Chrome", (W, c[1], c[2] + dz), (W + 0.02, c[1], c[2] + dz), 0.03, seg=8)
    else:
        scyl("Chrome", c, (W + 0.01, c[1], c[2]), 0.15, seg=16)
    if S.get("smooth"):
        # a rounded tail: the flap is cast onto the curving quarter panel, and the port sits in the skin there
        HINGES["Fuel"]["pivot"] = (W + 0.03, y0, (z0 + z1) / 2)
        return
    sbox("PanelFuel", W + 0.015, y0, z0, W + 0.035, y1, z1, bev=0.03)


def build_fuel_door_smooth():
    """after the body exists (decals cast onto it): the charge flap and its port on the curved quarter"""
    y0, y1 = FUEL_Y
    z0, z1 = FUEL_Z
    yc, zc = (y0 + y1) / 2, (z0 + z1) / 2
    loc, n, _, _ = body_bvh().ray_cast(Vector((W + 3, yc, zc)), Vector((-1, 0, 0)), 8.0)
    if loc is None:
        return
    n = Vector(n).normalized()
    if n.x < 0:
        n = -n
    t1 = Vector((0, 0, 1)).cross(n).normalized()          # along the skin, horizontal
    if t1.y < 0:
        t1 = -t1
    t2 = n.cross(t1).normalized()
    if t2.z < 0:
        t2 = -t2
    hw, hh = (y1 - y0) / 2, (z1 - z0) / 2
    P = lambda a, b, o: loc + n * o + t1 * a + t2 * b
    decal("PanelFuel", P(-hw, -hh, 1), P(hw, -hh, 1), P(hw, hh, 1), P(-hw, hh, 1), -n, nu=4, nv=4, out=0.025, inn=0.0)
    # the port under the flap, sunk into the skin along its normal
    decal("Under", P(-hw + 0.06, -hh + 0.06, 1), P(hw - 0.06, -hh + 0.06, 1), P(hw - 0.06, hh - 0.06, 1), P(-hw + 0.06, hh - 0.06, 1), -n,
          nu=3, nv=3, out=0.004, inn=0.05)
    c = loc + n * 0.0
    if S.get("electric"):
        scyl("Dark", c - n * 0.02, c + n * 0.012, 0.17, seg=16)
        for dz in (-0.05, 0.05):
            scyl("Chrome", c + t2 * dz - n * 0.01, c + t2 * dz + n * 0.018, 0.03, seg=8)
    HINGES["Fuel"]["pivot"] = tuple(loc + n * 0.03 - t1 * hw)


def build_frunk():
    """electric: a carpeted front trunk under the hood instead of an engine"""
    ap = WX - TW / 2 - 0.3
    fl = ZB + 0.55
    y0, y1 = L0 + 0.8, A0 - 0.15
    top = min(deck_z(0, y0), deck_z(0, y1)) - 0.2
    if S.get("smooth"):
        # the hood opening is wider than the tub and its skin curves, so the tub is a liner swept under the whole
        # opening: floor, walls up to just under the hood, and gutters out to the hood's edges (no gaps to the
        # ground or the cabin with the hood open)
        uz = lambda x, y: deck_z(abs(x), y) - 0.12
        xo = lambda y: min(0.8 * station_w(y), W - 0.12)
        def sect(y):
            e = xo(y)
            a = min(ap, e - 0.08)                           # the rounded nose: the tub narrows with it
            return [(-e, uz(e, y)), (-a, uz(a, y)), (-a, fl), (a, fl), (a, uz(a, y)), (e, uz(e, y))]
        n = 16
        ys = [y0 + (y1 - y0) * j / n for j in range(n + 1)]
        O, I = [], []
        for y in ys:
            sc = sect(y)
            O.append([Vector((x, y, z)) for x, z in sc])
            I.append([Vector((x + (0.04 if x > 0 else -0.04) * (1 if abs(x) <= ap + 1e-6 else 0), y,
                              z - (0.04 if (abs(x) > ap + 1e-6 or z <= fl + 1e-6) else 0))) for x, z in sc])
        solid_grid("Under", O, I, [(j, i) for j in range(n) for i in range(5)], smooth=40.0)
        m = 14
        for yy, dy in ((y0, -0.05), (y1, 0.05)):      # front wall and firewall, shaped to the hood above them
            e = xo(yy)
            xs = [-e + 2 * e * i / m for i in range(m + 1)]
            bot = lambda x: fl - 0.05                       # full height: no slit beside the tub walls
            O = [[Vector((x, yy, bot(x))) for x in xs], [Vector((x, yy, uz(x, yy) + 0.02)) for x in xs]]
            I = [[v + Vector((0, dy, 0)) for v in row] for row in O]
            solid_grid("Under", O, I, [(0, i) for i in range(m)], smooth=40.0)
    else:
        sbox("Under", -ap, y0, fl - 0.05, ap, y1, fl)
        for s in (-1, 1):
            sbox("Under", s * (ap - 0.05), y0, fl, s * ap, y1, top)
        for yy in (y0, y1 - 0.05):
            sbox("Under", -ap, yy, fl, ap, yy + 0.05, top)
    if S.get("smooth"):                                    # carpet in slices that follow the narrowing tub
        ns_ = 8
        for k in range(ns_):
            ya_, yb_ = y0 + 0.06 + (y1 - y0 - 0.12) * k / ns_, y0 + 0.06 + (y1 - y0 - 0.12) * (k + 1) / ns_
            xc = min(ap, xo(ya_) - 0.08, xo(yb_) - 0.08) - 0.06
            sbox("Carpet", -xc, ya_, fl, xc, yb_, fl + 0.03)
    else:
        sbox("Carpet", -(ap - 0.06), y0 + 0.06, fl, ap - 0.06, y1 - 0.06, fl + 0.04)
    if not S.get("smooth"):
        sbox("Dark", -0.5, y1 - 0.4, fl + 0.04, 0.5, y1 - 0.08, fl + 0.3, bev=0.04)      # charger bag


def build_engine_bay():
    ap = WX - TW / 2 - 0.3
    fl = ZB + 0.4
    y0, y1 = L0 + 0.7, A0 - 0.12
    top = min(deck_z(0, y0), deck_z(0, y1)) - 0.25
    sbox("Under", -ap, y0, fl - 0.04, ap, y1, fl)
    for s in (-1, 1):
        sbox("Under", s * (ap - 0.05), y0, fl, s * ap, y1, top)
    sbox("Under", -ap, y1 - 0.06, fl, ap, y1, top)
    sbox("Dark", -(ap - 0.3), y0 + 0.05, fl + 0.1, ap - 0.3, y0 + 0.25, top - 0.1)              # radiator
    cy = (y0 + y1) / 2
    eh = min(1.0, top - fl - 0.35)
    sbox("Dark", -0.9, cy - 1.6, fl + 0.05, 0.9, cy + 1.6, fl + eh, bev=0.06)                    # engine
    for s in (-1, 1):
        sbox("Chrome", s * 0.5, cy - 1.4, fl + eh, s * 1.1, cy + 1.4, fl + eh + 0.22, bev=0.06)
    scyl("Chrome", (0, cy, fl + eh), (0, cy, fl + eh + 0.25), 0.55, seg=24, bev=0.04)
    sbox("Dark", ap - 0.85, y1 - 1.2, fl, ap - 0.2, y1 - 0.3, fl + 0.6, bev=0.04)              # battery


WINDOWS = {}


def split_onto_doors():
    """trim, glass, mirrors and door cards that sit on a door move onto that door"""
    def rule(kind):
        info = OPT_INFO.get(kind)
        if info:
            if info["slot"] == "Doors":
                return W - 0.85, ZB + 0.2, BELT + 0.3
            if info["slot"] in ("Mirrors",):
                return W - 0.4, DOOR_Z0, ROOF
            return None
        if kind == "RoofGlass":
            return W - 0.32 - TUCK - 0.2, BELT, ROOF
        if kind == "RoofChrome":                          # window surround + door trim strips ride on the doors
            return W - 0.32 - TUCK - 0.2, DOOR_Z0 - 0.1, ROOF
        return None
    for ob in list(OBJS):
        if ob.get("style") != PREFIX or "__" in ob["kind"]:
            continue
        r = rule(ob["kind"])
        if not r:
            continue
        xmin, zmin, zmax = r
        bake(ob)
        me = ob.data
        me.transform(ob.matrix_world)
        ob.matrix_world = Matrix.Identity(4)
        bm = bmesh.new()
        bm.from_mesh(me)
        for (nm, s, y0, y1) in DOORS:
            for y in (y0, y1):
                bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], plane_co=(0, y, 0), plane_no=(0, 1, 0))
        bm.faces.index_update()
        bm.to_mesh(me)
        moved = set()
        for (nm, s, y0, y1) in DOORS:
            sel = set()
            for f in bm.faces:
                c = f.calc_center_median()
                if f.index not in moved and y0 < c.y < y1 and s * c.x > xmin and zmin < c.z < zmax:
                    sel.add(f.index)
            if not sel:
                continue
            part = bmesh.new()
            part.from_mesh(me)
            part.faces.ensure_lookup_table()
            bmesh.ops.delete(part, geom=[f for f in part.faces if f.index not in sel], context="FACES")
            kind = ob["kind"] + "__" + nm
            if ob["kind"] == "RoofGlass":
                # door glass is its own piece so it can roll down into the door (Kit.SetWindow)
                kind = "RoofGlass__Win" + nm
                # the glass can come in several objects (cut cells), so the span covers all of them
                zs = [v.co.z for v in part.verts]
                lo, hi = min(zs), max(zs)
                if nm in WINDOWS:
                    lo, hi = min(lo, WINDOWS[nm]["lo"]), max(hi, WINDOWS[nm]["hi"])
                WINDOWS[nm] = {"piece": kind, "lo": lo, "hi": hi,
                               "drop": max(0.0, min(hi - lo + 0.02, lo - DOOR_Z0 - 0.12))}
            if ob["kind"] in OPT_INFO:
                OPT_INFO[kind] = dict(OPT_INFO[ob["kind"]], hinge=nm)
            else:
                HINGE_OF[kind] = nm
            new_obj(part, kind, style=PREFIX, smooth=ob.get("smooth", 0.0))
            moved |= sel
        bm.faces.ensure_lookup_table()
        bmesh.ops.delete(bm, geom=[f for f in bm.faces if f.index in moved], context="FACES")
        bm.to_mesh(me)
        bm.free()
    for k, v in OPT_INFO.items():
        if v["slot"] in HINGE_SLOTS and "hinge" not in v and HINGE_SLOTS[v["slot"]] in HINGES:
            v["hinge"] = HINGE_SLOTS[v["slot"]]


# ------------------------------------------------------------------ pieces that hug the body (smooth bodies)
_BVH = []


def body_bvh():
    """a ray-cast tree of the outer skin: body, door skins, lids"""
    if _BVH:
        return _BVH[0]
    bm = bmesh.new()
    for ob in OBJS:
        if ob.get("loft") or ob["kind"].startswith("PanelDoor") or ob["kind"] in ("Lid", "PanelHood", "PanelRoof"):
            bake(ob)
            me = ob.data.copy()
            me.transform(ob.matrix_world)
            bm.from_mesh(me)
            bpy.data.meshes.remove(me)
    _BVH.extend([BVHTree.FromBMesh(bm), bm])
    return _BVH[0]


def decal(kind, c00, c10, c11, c01, d, nu=10, nv=3, out=0.03, inn=0.03, smooth=30.0, bridge=False):
    """a thin piece over the body: the quad c00 c10 c11 c01 is cast along d onto the skin and thickened along its
    normal (out above the skin, inn below it)"""
    tree = body_bvh()
    d = Vector(d).normalized()
    c00, c10, c11, c01 = Vector(c00), Vector(c10), Vector(c11), Vector(c01)
    O, I, miss = [], [], set()
    for j in range(nv + 1):
        v = j / nv
        ro, ri = [], []
        for i in range(nu + 1):
            u = i / nu
            p = (c00 * (1 - u) + c10 * u) * (1 - v) + (c01 * (1 - u) + c11 * u) * v
            loc, n, _, _ = tree.ray_cast(p - d * 4.0, d, 12.0)
            if loc is None:                                # off the edge of the skin: those cells are left out
                loc, n = p, -d
                miss.add((j, i))
            n = Vector(n)
            if n.dot(d) > 0:
                n = -n
            ro.append(loc + n * out)
            ri.append(loc - n * inn)
        O.append(ro)
        I.append(ri)
    if bridge:
        # a ray that fell through a panel gap (shut line) between two good hits: take the neighbours' average
        for j in range(nv + 1):
            for i in range(1, nu):
                a, b = (j, i - 1), (j, i + 1)
                if a in miss or b in miss:
                    continue
                mid = (O[j][i - 1] + O[j][i + 1]) / 2
                if (j, i) in miss or (O[j][i] - mid).length > 0.15:
                    O[j][i] = mid
                    I[j][i] = (I[j][i - 1] + I[j][i + 1]) / 2
                    miss.discard((j, i))
    cells = [(j, i) for j in range(nv) for i in range(nu)
             if not ({(j, i), (j + 1, i), (j, i + 1), (j + 1, i + 1)} & miss)]
    # a hit far off the plane of its neighbours (a ray that slipped past an edge onto another surface) is dropped too
    def far(a, b):
        return (O[a[0]][a[1]] - O[b[0]][b[1]]).length
    step = max((Vector(c10) - Vector(c00)).length / nu, (Vector(c01) - Vector(c00)).length / nv, 0.02)
    cells = [(j, i) for (j, i) in cells if max(far((j, i), (j, i + 1)), far((j, i), (j + 1, i)), far((j + 1, i + 1), (j, i + 1)),
                                               far((j + 1, i + 1), (j + 1, i))) < step * 4.0]
    return solid_grid(kind, O, I, cells, smooth) if cells else None


def skylight():
    """the reference's top view: a framed two-pane glass roof inset in the body-coloured roof panel, with small
    rounded corners and a thin bar across the middle"""
    sk = S["SKYLIGHT"]
    pts = []
    for ob in OBJS:
        if ob["kind"] == "PanelRoof":
            bake(ob)
            pts += [ob.matrix_world @ v.co for v in ob.data.vertices]
    if not pts:
        return
    ya, yb = WS_END + (C0 - WS_END) * sk.get("front", 0.13), C0 - (C0 - WS_END) * sk.get("rear", 0.08)

    def roof_hw(y):
        near = [abs(p.x) for p in pts if abs(p.y - y) < 0.25]
        return max(near) if near else 0.0

    def rrect(kind, y0, y1, frac, r, out, inn):
        n = 24
        for k in range(n):
            u0, u1 = y0 + (y1 - y0) * k / n, y0 + (y1 - y0) * (k + 1) / n
            hw = []
            for u in (u0, u1):
                d = min(u - y0, y1 - u)
                c = r - math.sqrt(max(0.0, r * r - (r - d) ** 2)) if d < r else 0.0
                hw.append(max(0.02, frac * hw_min - c))
            decal(kind, (-hw[0], u0, 9), (hw[0], u0, 9), (hw[1], u1, 9), (-hw[1], u1, 9), (0, 0, -1),
                  nu=12, nv=1, out=out, inn=inn)

    hw_min = min(roof_hw(ya + (yb - ya) * k / 10) for k in range(11))   # straight sides, inside the panel everywhere
    fr = sk.get("width", 0.8)
    n0 = len(OBJS)
    rrect("Dark", ya, yb, fr + 0.04, 0.4, 0.008, 0.05)                         # rubber frame
    frame = OBJS[n0:]
    ym = (ya + yb) / 2
    # the front pane opens: it tilts up at the back and slides back over the rear pane (hinge "Sunroof" with a slide),
    # uncovering a hole cut through the roof panel, the frame and the headliner (cut_sunroof, once everything exists)
    rrect("Glass__Sunroof", ya + 0.07, ym - 0.03, fr, 0.33, 0.016, 0.02)       # front pane
    rrect("Glass", ym + 0.03, yb - 0.07, fr, 0.33, 0.016, 0.02)                # rear pane
    HINGE_OF["Glass__Sunroof"] = "Sunroof"
    loc, _, _, _ = body_bvh().ray_cast(Vector((0, ya + 0.07, 9)), Vector((0, 0, -1)), 12.0)
    zf = loc.z if loc else ROOF
    HINGES["Sunroof"] = {"pivot": (0.0, ya + 0.07, zf + 0.02), "axis": (1, 0, 0), "open": 2.5, "kind": "sunroof",
                         "slide": (0.0, (ym - ya - 0.1) * 0.92, 0.1)}
    SUNROOF_HOLE.update(y0=ya + 0.13, y1=ym - 0.09, x=fr * hw_min - 0.08, frame=frame)


SUNROOF_HOLE = {}


def cut_sunroof():
    """the opening under the sliding pane: cut through the roof panel, the sunroof frame and every headliner"""
    if not SUNROOF_HOLE:
        return
    h = SUNROOF_HOLE
    targets = [ob for ob in OBJS if ob["kind"] == "PanelRoof" or ob["kind"].startswith("OptHeadliner")] + list(h["frame"])
    for ob in targets:
        if ob.name not in bpy.data.objects:
            continue
        bake(ob)
        me = ob.data
        me.transform(ob.matrix_world)
        ob.matrix_world = Matrix.Identity(4)
        bm = bmesh.new()
        bm.from_mesh(me)
        for co, no in (((0, h["y0"], 0), (0, 1, 0)), ((0, h["y1"], 0), (0, 1, 0)), ((h["x"], 0, 0), (1, 0, 0)), ((-h["x"], 0, 0), (1, 0, 0))):
            bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], plane_co=co, plane_no=no)
        dead = [f for f in bm.faces if (lambda c: h["y0"] < c.y < h["y1"] and abs(c.x) < h["x"])(f.calc_center_median())]
        bmesh.ops.delete(bm, geom=dead, context="FACES")
        bm.to_mesh(me)
        bm.free()


def smooth_details():
    """the fixed details of a smooth modern body: lower intake, fog-lamp slats, rear diffuser, door trim"""
    yF, yR = L0 - 1.0, L1 + 1.0
    if S.get("PLAN"):
        # the reference's lower front: a wide mouth whose top edge dips gently toward the sides, side intakes that rise
        # outward holding a small round fog lamp and two chrome blades, and a shallow chrome wing under the nose (no badge)
        n_ = 24
        for k in range(n_):
            a, b = -0.63 + 1.26 * k / n_, -0.63 + 1.26 * (k + 1) / n_
            zt = lambda u: ZB + 0.66 - 0.1 * (abs(u) / 0.63) ** 2
            decal("Dark", (a * W, yF, ZB + 0.26), (b * W, yF, ZB + 0.26), (b * W, yF, zt(b)), (a * W, yF, zt(a)), (0, 1, 0),
                  nu=3, nv=3, out=0.02, inn=0.05)
        for s_ in (-1, 1):
            x0, x1 = s_ * W * 0.6, s_ * W * 0.88
            decal("Dark", (x0, yF, ZB + 0.26), (x1, yF, ZB + 0.46), (x1, yF, ZB + 0.98), (x0, yF, ZB + 0.84), (0, 1, 0), nu=10, nv=5,
                  out=0.015, inn=0.05)
            for dz in (0.0, 0.11):                       # two chrome blades along the intake's top
                za0, za1 = ZB + 0.66 + dz, ZB + 0.78 + dz
                decal("Chrome", (x0, yF, za0), (s_ * W * 0.82, yF, za1), (s_ * W * 0.82, yF, za1 + 0.035), (x0, yF, za0 + 0.035),
                      (0, 1, 0), nu=6, nv=1, out=0.035, inn=0.02)
            xf = s_ * W * 0.8                            # fog lamp
            decal("Chrome", (xf - 0.15, yF, ZB + 0.45), (xf + 0.15, yF, ZB + 0.45), (xf + 0.15, yF, ZB + 0.66), (xf - 0.15, yF, ZB + 0.66),
                  (0, 1, 0), nu=3, nv=3, out=0.035, inn=0.02)
            decal("Head", (xf - 0.1, yF, ZB + 0.49), (xf + 0.1, yF, ZB + 0.49), (xf + 0.1, yF, ZB + 0.62), (xf - 0.1, yF, ZB + 0.62),
                  (0, 1, 0), nu=2, nv=2, out=0.05, inn=0.0)
            m_ = 8                                       # nose wing: from the lamp's inner tip in a shallow arc to the middle
            for k in range(m_):
                ua, ub = k / m_, (k + 1) / m_
                zw = lambda u: 2.04 + 0.12 * u ** 1.6
                xa, xb_ = s_ * W * 0.44 * ua, s_ * W * 0.44 * ub
                decal("Chrome", (xa, yF, zw(ua) - 0.03), (xb_, yF, zw(ub) - 0.03), (xb_, yF, zw(ub) + 0.01), (xa, yF, zw(ua) + 0.01),
                      (0, 1, 0), nu=2, nv=1, out=0.035, inn=0.02)
    else:
        decal("Dark", (-W * 0.55, yF, ZB + 0.3), (W * 0.55, yF, ZB + 0.3), (W * 0.55, yF, ZB + 0.85), (-W * 0.55, yF, ZB + 0.85),
              (0, 1, 0), nu=16, nv=3, out=0.02, inn=0.05)
        for s_ in (-1, 1):
            x0, x1 = s_ * W * 0.56, s_ * W * 0.8
            decal("Dark", (x0, yF, ZB + 0.4), (x1, yF, ZB + 0.4), (x1, yF, ZB + 0.78), (x0, yF, ZB + 0.78), (0, 1, 0), nu=6, nv=3,
                  out=0.015, inn=0.05)
            for k in range(3):
                z = ZB + 0.48 + k * 0.11
                decal("Chrome", (x0, yF, z), (x1, yF, z), (x1, yF, z + 0.035), (x0, yF, z + 0.035), (0, 1, 0), nu=6, nv=1,
                      out=0.035, inn=0.02)
    for s_ in (-1, 1):
        # chrome strip low along the doors
        xs = s_ * (W + 1.0)
        y0, y1 = WY_F + ARCH + 0.2, WY_R - ARCH - 0.2
        decal("RoofChrome", (xs, y0, DOOR_Z0 + 0.14), (xs, y1, DOOR_Z0 + 0.14), (xs, y1, DOOR_Z0 + 0.19), (xs, y0, DOOR_Z0 + 0.19),
              (-s_, 0, 0), nu=60, nv=1, out=0.025, inn=0.02)
    decal("Dark", (-W * 0.5, yR, ZB + 0.3), (W * 0.5, yR, ZB + 0.3), (W * 0.5, yR, ZB + 0.6), (-W * 0.5, yR, ZB + 0.6),
          (0, -1, 0), nu=14, nv=3, out=0.03, inn=0.05)
    if S.get("PLAN"):          # the reference's rear: the hatch's shut line over the bumper, across the tail
        zc_ = ZB + 1.45
        decal("Seam", (-W * 0.6, yR, zc_ - 0.012), (W * 0.6, yR, zc_ - 0.012), (W * 0.6, yR, zc_ + 0.012), (-W * 0.6, yR, zc_ + 0.012),
              (0, -1, 0), nu=48, nv=1, out=0.014, inn=0.05, bridge=True)
    # door shut lines, following the barrelled side (a straight box poked out above the shoulder)
    for (nm, s_, y0, y1) in DOORS:
        xs = s_ * (W + 1.0)
        for yy in (y0 - 0.015, y1 + 0.015):
            z0, z1 = DOOR_Z0 - 0.03, belt_at(yy) + 0.02
            decal("Seam", (xs, yy - 0.012, z0), (xs, yy + 0.012, z0), (xs, yy + 0.012, z1), (xs, yy - 0.012, z1), (-s_, 0, 0),
                  nu=1, nv=12, out=0.006, inn=0.05)
    if S.get("SKYLIGHT"):
        skylight()
    # hood shut lines: along the fender peaks' inner edge and across behind the nose cone
    y0h, y1h = L0 + 0.95, A0 - 0.1
    hx = lambda y: 0.744 * station_w(y)
    if S.get("PLAN"):                                    # the reference: lines from the pillars forward to the lamps' tops
        y0h = L0 + 1.0
        hx = lambda y: W * (0.5 + 0.28 * min(1.0, max(0.0, (y - y0h) / (y1h - y0h))) ** 0.8)
    n = 10
    for k in range(n):
        ya, yb = y0h + (y1h - y0h) * k / n, y0h + (y1h - y0h) * (k + 1) / n
        for s_ in (-1, 1):
            xa, xb_ = s_ * hx(ya), s_ * hx(yb)
            decal("Seam", (xa - 0.012, ya, 9), (xa + 0.012, ya, 9), (xb_ + 0.012, yb, 9), (xb_ - 0.012, yb, 9), (0, 0, -1),
                  nu=1, nv=2, out=0.006, inn=0.05)
    if not S.get("PLAN"):                                # (the reference's hood ends hidden under the windshield)
        decal("Seam", (-hx(y1h), y1h - 0.012, 9), (hx(y1h), y1h - 0.012, 9), (hx(y1h), y1h + 0.012, 9), (-hx(y1h), y1h + 0.012, 9),
              (0, 0, -1), nu=24, nv=1, out=0.006, inn=0.05)
    decal("Seam", (-hx(y0h), y0h - 0.012, 9), (hx(y0h), y0h - 0.012, 9), (hx(y0h), y0h + 0.012, 9), (-hx(y0h), y0h + 0.012, 9),
          (0, 0, -1), nu=24, nv=1, out=0.006, inn=0.05)
    # hatch: a body-colour sill on the lid under the glass's lower edge, so the opened hatch has no gap
    if REAR == "hatch":
        yb = GH_YEND
        xw = gh_xb(yb) * 0.8 - 0.02                       # as wide as the hatch glass, so no step at its corners
        decal("Lid", (-xw, yb - 0.22, 9), (xw, yb - 0.22, 9), (xw, yb + 0.12, 9), (-xw, yb + 0.12, 9), (0, 0, -1), nu=16, nv=3,
              out=0.03, inn=0.04)


exec(compile(open(os.path.join(HERE, "build_vehicle_parts.py")).read(), "build_vehicle_parts.py", "exec"), globals())


# ------------------------------------------------------------------ paint panels
PANELS = {
    "side": ("yz", (L0 - 0.1, L1 + 0.1), (ZB - 0.1, BELT + 0.35)),
    "hood": ("xy", (-W - 0.05, W + 0.05), (L0 - 0.1, A0)),
    "roof": ("xy", (-gx(ROOF) - 0.1, gx(ROOF) + 0.1), (A1 - 0.1, C0 + 0.1)),
}
if REAR in ("trunk", "hatch"):
    PANELS["trunk"] = ("xy", (-W + 0.5, W - 0.5), (C1, L1 - 0.4))
else:
    PANELS["trunk"] = ("xz", (-W + 0.3, W - 0.3), (ZB + 0.7, BELT + 0.1))
PANEL_OF = {"PanelSideL": "side", "PanelSideR": "side", "PanelHood": "hood", "Lid": "trunk", "PanelRoof": "roof", "PanelFuel": "side"}
for (nm, s, y0, y1) in DOORS:
    PANEL_OF["PanelDoor" + nm[4:]] = "side"
SOURCE_OF = {"side": "PanelSideL", "hood": "PanelHood", "trunk": "Lid", "roof": "PanelRoof"}


def panel_uv(panel, co):
    ax, (a0, a1), (b0, b1) = PANELS[panel]
    if ax == "yz":
        return ((co.y - a0) / (a1 - a0), (co.z - b0) / (b1 - b0))
    if ax == "xz":
        return ((a1 - co.x) / (a1 - a0), (co.z - b0) / (b1 - b0))
    return ((a1 - co.x) / (a1 - a0), 1 - (co.y - b0) / (b1 - b0))


def set_uv(ob, panel):
    bake(ob)
    me = ob.data
    for layer in list(me.uv_layers):
        me.uv_layers.remove(layer)
    uv = me.uv_layers.new(name="UVMap")
    for poly in me.polygons:
        for li in poly.loop_indices:
            uv.data[li].uv = panel_uv(panel, ob.matrix_world @ me.vertices[me.loops[li].vertex_index].co)
    ob["uv"] = True


def split_panels():
    body = [o for o in OBJS if o.get("loft")][0]
    bake(body)
    ySF, ySR = L0 + 1.9, L1 - 1.6                        # smooth: the side prints end on clean cuts, not on facets
    if S.get("smooth"):
        bm = bmesh.new()
        bm.from_mesh(body.data)
        for yc in (ySF, ySR):
            g = bm.verts[:] + bm.edges[:] + bm.faces[:]
            bmesh.ops.bisect_plane(bm, geom=g, plane_co=(0, yc, 0), plane_no=(0, 1, 0), dist=1e-4)
        bm.to_mesh(body.data)
        bm.free()
    if S.get("smooth"):                                    # remember the uncut body's shading for the seams
        me = body.data
        for poly in me.polygons:
            poly.use_smooth = True
        me.set_sharp_from_angle(angle=math.radians(SMOOTH_ANGLE))
        for lp, cn in zip(me.loops, me.corner_normals):
            k = nkey(me.vertices[lp.vertex_index].co)
            lst = SMOOTH_REF.setdefault(k, [])
            v = Vector(cn.vector)
            if all(v.dot(u) < 0.999 for u in lst):
                lst.append(v)
    regions = {}
    for f in body.data.polygons:
        c, n = f.center, f.normal
        if abs(n.x) > 0.5 and abs(c.x) > W - 0.35 and (not S.get("smooth") or ySF < c.y < ySR):
            r = "PanelSideL" if c.x > 0 else "PanelSideR"
        elif S.get("smooth") and n.z > 0.3 and L0 + 0.95 < c.y < A0 - 0.08 and abs(c.x) < 0.75 * station_w(c.y):
            r = "PanelHood"                               # the hood: between the fender peaks, behind the nose cone
        elif not S.get("smooth") and n.z > 0.5 and L0 + 0.8 < c.y < A0 - 0.08 and abs(c.x) < W - 0.2:   # not the nose lip
            r = "PanelHood"
        else:
            r = "Body"
        regions.setdefault(r, set()).add(f.index)
    moved = set()
    for r, idx in regions.items():
        if r == "Body":
            continue
        bm = bmesh.new()
        bm.from_mesh(body.data)
        bm.faces.ensure_lookup_table()
        bmesh.ops.delete(bm, geom=[f for f in bm.faces if f.index not in idx], context="FACES")
        ob = new_obj(bm, r, style=PREFIX, smooth=SMOOTH_ANGLE)
        set_uv(ob, PANEL_OF[r])
        moved |= idx
        if r == "PanelHood":
            hb = bmesh.new()
            hb.from_mesh(ob.data)
            new_obj(shell(hb, 0.08), "HoodInner", style=PREFIX, smooth=SMOOTH_ANGLE)
            hb.free()
    bm = bmesh.new()
    bm.from_mesh(body.data)
    bm.faces.ensure_lookup_table()
    bmesh.ops.delete(bm, geom=[f for f in bm.faces if f.index in moved], context="FACES")
    bm.to_mesh(body.data)
    bm.free()
    for o in list(OBJS):
        if o["kind"] in PANEL_OF and o["kind"] not in regions:
            set_uv(o, PANEL_OF[o["kind"]])


# ------------------------------------------------------------------ build
src = cutters_and_body()
build_doors(src)
bpy.data.meshes.remove(src)
greenhouse_smooth() if S.get("smooth") else greenhouse()
build_rear()
build_fuel_door()
if S.get("electric"):
    build_frunk()
else:
    build_engine_bay()
build_parts()
if S.get("smooth"):
    smooth_details()
    build_fuel_door_smooth()
if S.get("fins"):                                         # 60s tail fins along the rear fenders
    for s_ in (-1, 1):
        y0, y1 = C1 + 0.4, L1 - 0.15
        x = s_ * (W - 0.15)
        sprism("Body", [(x, y0, deck_z(x, y0) - 0.02), (x, y1, deck_z(x, y1) + 0.55), (x, y1, deck_z(x, y1) - 0.05)],
               [(x - s_ * 0.16, y0, deck_z(x, y0) - 0.02), (x - s_ * 0.16, y1, deck_z(x, y1) + 0.55), (x - s_ * 0.16, y1, deck_z(x, y1) - 0.05)])
        scyl("Tail", (x - s_ * 0.08, y1 - 0.02, deck_z(x, y1) + 0.3), (x - s_ * 0.08, y1 + 0.06, deck_z(x, y1) + 0.3), 0.1, seg=12)
if S.get("police"):                                       # roof light bar + push bar (not for sale, fixed)
    xt = gx(ROOF)
    yl = (A1 + C0) / 2 - 0.4 if REAR != "liftgate" else A1 + 0.6
    sbox("Dark", -(xt - 0.3), yl - 0.25, ROOF + 0.14, xt - 0.3, yl + 0.25, ROOF + 0.24)
    sbox("PoliceRed", 0.1, yl - 0.22, ROOF + 0.24, xt - 0.35, yl + 0.22, ROOF + 0.46, bev=0.04)
    sbox("PoliceBlue", -(xt - 0.35), yl - 0.22, ROOF + 0.24, -0.1, yl + 0.22, ROOF + 0.46, bev=0.04)
    if not BED and REAR != "liftgate":
        for s_ in (-1, 1):
            sbeam("Dark", (s_ * 0.9, L0 - 0.6, ZB + 0.2), (s_ * 0.9, L0 - 0.6, NOSE - 0.1), 0.14, 0.14)
        sbeam("Dark", (-0.9, L0 - 0.6, NOSE - 0.15), (0.9, L0 - 0.6, NOSE - 0.15), 0.14, 0.14)
        sbeam("Dark", (-0.9, L0 - 0.6, ZB + 0.6), (0.9, L0 - 0.6, ZB + 0.6), 0.14, 0.14)
cut_sunroof()
split_onto_doors()
split_panels()
car, car_tris = join_style(PREFIX, PREFIX)

# vinyls: the lowrider's images, printed on this vehicle's panels
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

# wheel: every lowrider rim / knock-off / tyre design + off-road tyres, scaled to this vehicle
WHEEL_X = 30.0
build_wheels(WHEEL_X)
wheel, wheel_tris = join_style("LowriderWheel", PREFIX + "Wheel")
export(car + wheel, f"{PREFIX}.glb")

# ------------------------------------------------------------------ game data
car_ext, wheel_ext = extents(car), extents(wheel)
cmn, cmx = imp_ext(car_ext)
wmn, wmx = imp_ext(wheel_ext)
seat_z = ZB + 0.3 + SEATH - 0.2                  # the Seat part (0.4 thick) is flush with the cushion top
sy = (A0 + B) / 2 + 0.9
seats = {"Driver": car_pt((W * 0.42, sy, seat_z)), "Passenger": car_pt((-W * 0.42, sy, seat_z))}
sy = SY
seats = {"Driver": car_pt((W * 0.42, sy, seat_z)), "Passenger": car_pt((-W * 0.42, sy, seat_z))}
if S_REAR_Y():
    ry = S_REAR_Y()
    seats["RearL"], seats["RearR"] = car_pt((W * 0.42, ry, seat_z)), car_pt((-W * 0.42, ry, seat_z))
data = {
    "Car": {
        "ImportMin": cmn, "ImportMax": cmx, "Pieces": sorted(k.split("_", 1)[1] for k in car_tris),
        "Wheels": {"FL": car_pt((WX, WY_F, WR)), "FR": car_pt((-WX, WY_F, WR)), "RL": car_pt((WX, WY_R, WR)), "RR": car_pt((-WX, WY_R, WR))},
        "WheelRadius": WR,
        "LidHinge": car_pt(HINGES["Lid"]["pivot"]),
        "Hinges": {k: dict({"Pivot": car_pt(h["pivot"]), "Axis": car_pt(h["axis"]), "Open": h["open"], "Kind": h["kind"]},
                           **({"Slide": car_pt(h["slide"])} if h.get("slide") else {})) for k, h in HINGES.items()},
        "HingeOf": {k: v for k, v in HINGE_OF.items() if f"{PREFIX}_{k}" in car_tris},
        "Hull": [car_box((-W, L0 - 0.2, ZB), (W, L1 + 0.2, BELT + 0.1)), car_box((-gx(BELT), A0 + 0.3, BELT), (gx(BELT), (C1 if not BED else C1), ROOF + 0.1))],
        "Seats": seats,
        "FrontBumper": car_pt((0, L0 - 0.2, ZB + 0.5)), "RearBumper": car_pt((0, L1 + 0.2, ZB + 0.5)),
        "PanelOf": PANEL_OF, "Vinyls": {liv: sorted(p) for liv, p in VINYLS.items()},
        "OptInfo": {k: v for k, v in OPT_INFO.items() if f"{PREFIX}_{k}" in car_tris},
        "Options": options_of(OPT_INFO, car_tris, PREFIX + "_"),
        "Gauge": {"Centre": car_pt(GAUGE[0]), "Size": [1.4, 0.4], "Tilt": GAUGE[1]},
        "Windows": {k: {"Piece": w["piece"], "Drop": round(w["drop"], 3), "Dir": [0, -1, 0]} for k, w in WINDOWS.items()},
        "Steer": {"Centre": car_pt(STEER[0]), "Axis": [round(-STEER[1].x, 4), round(STEER[1].z, 4), round(STEER[1].y, 4)]},
        "Plaque": {"Centre": car_pt((0.0, C1 - 0.3, BELT + 0.5)), "Size": [1.8, 0.5]},
    },
    "Wheel": {"ImportMin": wmn, "ImportMax": wmx, "Centre": imp_pt((WHEEL_X, 0, 0)),
              "Pieces": sorted(k.split("_", 1)[1] for k in wheel_tris),
              "OptInfo": {k: v for k, v in WHEEL_INFO.items() if f"{PREFIX}Wheel_{k}" in wheel_tris},
              "Options": options_of(WHEEL_INFO, wheel_tris, PREFIX + "Wheel_")},
}
with open(os.path.join(OUT, f"NCVehicleData_{VID}.lua"), "w") as f:
    f.write(f"-- NCVehicleData_{VID} (ModuleScript, ReplicatedStorage). GENERATED by build_vehicles.py: do not edit by hand.\n")
    f.write(f"-- {S['name']}: same layout as NCLowriderData.Car / .Wheel (car frame: front = -Z, origin on the ground between the axles).\n")
    f.write("return " + lua(data) + "\n")

# ------------------------------------------------------------------ previews
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
previews = []
for (wx, wy) in ((WX, WY_F), (-WX, WY_F), (WX, WY_R), (-WX, WY_R)):
    for ob in wheel:
        d = ob.copy()
        d["pkind"] = ob["pkind"]
        d["wheelcopy"] = True
        scene.collection.objects.link(d)
        d.matrix_world = Matrix.Translation((wx, wy, WR)) @ Matrix.Rotation(0 if wx > 0 else math.pi, 4, "Z") @ Matrix.Translation((-WHEEL_X, 0, 0))
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
        is_paint = kind in PANEL_OF or kind.split("__")[0] in ("Body", "RoofBody", "HoodInner") or kind.startswith("DoorJamb") or OPT_INFO.get(kind, {}).get("mat") == "Body"
        if is_paint:
            plain.setdefault(ob.name, ob.data.materials[0])
            path = VINYLS.get(liv, {}).get(PANEL_OF.get(kind, "")) if liv else None
            if path:
                ob.data.materials[0] = image_mat(f"prev_{liv}_{kind}_{len(plain)}", path, pc)
            else:
                m = plain[ob.name].copy()
                m.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (*pc, 1)
                ob.data.materials[0] = m


def pose(frac, win=0.0):
    for ob in scene.objects:
        k = ob.get("pkind")
        h = HINGE_OF.get(k) or (OPT_INFO.get(k) or {}).get("hinge")
        if not h or ob.get("wheelcopy"):
            continue
        hg = HINGES[h]
        p = Vector(hg["pivot"])
        w = WINDOWS.get(h)
        down = Matrix.Translation((0, 0, -w["drop"] * win)) if w and k == w["piece"] else Matrix.Identity(4)
        ob.matrix_world = Matrix.Translation(p) @ Matrix.Rotation(math.radians(hg["open"] * frac), 4, Vector(hg["axis"])) @ Matrix.Translation(-p) @ down


def shot(name, loc, tgt):
    cam.location = loc
    cam.rotation_euler = (Vector(tgt) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
    scene.render.filepath = os.path.join(PREV, f"{VID}_{name}.png")
    bpy.ops.render.render(write_still=True)


Lr = max(-L0, L1)
REF_VIEWS = [[0, 3.25], [27, 5.5], [90, 4.5], [208, 4.75], [180, 5.5], [203, 4.75], [270, 4.5], [28, 5.5]]   # the reference sheet's angles
fz = (ROOF * 0.4)
if os.environ.get("NC_REFMASK"):                        # silhouettes for fitting the body to the reference sheet
    show()
    if os.environ.get("NC_SUNOPEN") and "Sunroof" in HINGES:   # preview the sunroof open
        h_ = HINGES["Sunroof"]
        pv_ = Vector(h_["pivot"])
        M_ = Matrix.Translation(Vector(h_["slide"])) @ Matrix.Translation(pv_) @ Matrix.Rotation(math.radians(h_["open"]), 4, "X") @ Matrix.Translation(-pv_)
        for ob_ in scene.objects:
            if ob_.name.endswith("Glass__Sunroof"):
                ob_.matrix_world = M_ @ ob_.matrix_world
    if os.environ.get("NC_PROBE"):                       # which visible pieces have vertices near a point
        px_, py_, pz_, pr_ = map(float, os.environ["NC_PROBE"].split(","))
        for ob_ in scene.objects:
            if ob_.type == "MESH" and not ob_.hide_render:
                mw_ = ob_.matrix_world
                n_ = sum(1 for v_ in ob_.data.vertices if ((mw_ @ v_.co) - Vector((px_, py_, pz_))).length < pr_)
                if n_:
                    cs_ = [mw_ @ v_.co for v_ in ob_.data.vertices if ((mw_ @ v_.co) - Vector((px_, py_, pz_))).length < pr_]
                    print("PROBE", ob_.name, n_, [round(min(c[i] for c in cs_), 2) for i in range(3)], [round(max(c[i] for c in cs_), 2) for i in range(3)])
    g_ = bpy.data.objects.get("Ground")
    if g_:
        g_.hide_render = True
    scene.render.film_transparent = True
    if os.environ.get("NC_REFSHADE"):                    # look like the reference: glossy black paint, black wheels
        bg_ = scene.world.node_tree.nodes.get("Background") if scene.world and scene.world.node_tree else None
        if bg_:
            bg_.inputs["Strength"].default_value *= 0.45
        for ob_ in scene.objects:
            if ob_.type != "MESH" or not ob_.data.materials:
                continue
            pk_ = ob_.get("pkind", "")
            info_ = WHEEL_INFO.get(pk_)
            for m_ in ob_.data.materials:
                b_ = m_.node_tree.nodes.get("Principled BSDF") if m_ and m_.node_tree else None
                if not b_:
                    continue
                if info_ and info_["mat"] in ("Rim", "Spokes", "Dish", "Hub", "Chrome"):
                    b_.inputs["Base Color"].default_value = (0.02, 0.02, 0.022, 1)
                    b_.inputs["Roughness"].default_value = 0.3
                elif pk_ in ("Body", "RoofBody", "Lid") + tuple(PANEL_OF) or pk_.startswith("PanelDoor"):
                    b_.inputs["Roughness"].default_value = 0.12
                    if "Coat Weight" in b_.inputs:
                        b_.inputs["Coat Weight"].default_value = 1.0
                elif pk_.startswith("RoofGlass") or pk_ == "Glass":
                    b_.inputs["Base Color"].default_value = (0.01, 0.012, 0.015, 1)
    if scene.render.engine == "CYCLES":
        scene.cycles.samples = int(os.environ.get("NC_MASKSAMPLES", "2"))
    cam.data.lens = float(os.environ.get("NC_REFLENS", "55"))
    D_ = float(os.environ.get("NC_REFD", "33"))
    H_ = float(os.environ.get("NC_REFH", "4.4"))
    scene.render.resolution_x = scene.render.resolution_y = 600
    VIEWS_ = json.loads(os.environ.get("NC_REFVIEWS", "null")) or REF_VIEWS
    for k, (a, h) in enumerate(VIEWS_):
        ar = math.radians(a)
        tx_, ty_, tz_ = json.loads(os.environ.get("NC_REFT", "null")) or (0, 0, ROOF * 0.42)   # look-at point
        shot(f"mask{k}", (tx_ + D_ * math.sin(ar), ty_ - D_ * math.cos(ar), h), (tx_, ty_, tz_))
    if os.environ.get("NC_REFGRID"):
        scene.render.resolution_x = scene.render.resolution_y = 300
        for a in range(0, 360, 5):
            for h in (2.5, 4.5, 6.5, 8.5):
                ar = math.radians(a)
                shot(f"grid_{a}_{h}", (D_ * math.sin(ar), -D_ * math.cos(ar), h), (0, 0, ROOF * 0.42))
    cam.data.lens = 50
    scene.render.resolution_x, scene.render.resolution_y = 1536, 1024
    cam.location = (0.0, 0.0, 60.0)
    cam.rotation_euler = (0.0, 0.0, math.pi / 2)         # nose (-y) to the left of the frame
    scene.render.filepath = os.path.join(PREV, f"{VID}_masktop.png")
    bpy.ops.render.render(write_still=True)
    raise SystemExit(0)
if S.get("rim_dark"):                                     # previews: the car's stock wheels are black
    for ob in wheel:
        info = WHEEL_INFO.get(ob.get("pkind", ""))
        if info and info["mat"] in ("Rim", "Spokes", "Dish", "Hub", "Chrome"):
            for m in ob.data.materials:
                b_ = m.node_tree.nodes.get("Principled BSDF") if m and m.node_tree else None
                if b_:
                    b_.inputs["Base Color"].default_value = (0.02, 0.02, 0.022, 1)
                    b_.inputs["Roughness"].default_value = 0.3
show()
shot("front34", (-Lr * 1.55, -Lr * 2.1, ROOF * 1.4 + 2), (0, -1.0, fz))
shot("rear34", (Lr * 1.4, Lr * 2.2, ROOF * 1.4 + 2), (0, 1.0, fz))
shot("side", (Lr * 2.6, 0.0, ROOF * 0.6), (0, 0, fz))
if S.get("smooth"):                                      # the reference photo's angle: front left, standing height
    lens = cam.data.lens
    cam.data.lens = 26
    gloss = {}                                           # the photo's car is glossy black: clear-coat the paint
    for ob in scene.objects:
        if ob.type == "MESH" and ob.data.materials and ob.data.materials[0] and ob.get("pkind", "") in ("Body", "RoofBody") + tuple(PANEL_OF):
            m = ob.data.materials[0]
            b_ = m.node_tree.nodes.get("Principled BSDF") if m.node_tree else None
            if b_ and m.name not in gloss:
                gloss[m.name] = (b_, b_.inputs["Roughness"].default_value)
                b_.inputs["Roughness"].default_value = 0.12
                if "Coat Weight" in b_.inputs:
                    b_.inputs["Coat Weight"].default_value = 1.0
    lot = bpy.data.objects.get("Ground")                  # and it stands on dark asphalt under an overcast sky
    lot_m = lot.data.materials[0] if lot and lot.data.materials else None
    lot_old = None
    if lot_m is not None:
        lot_m.use_nodes = True
        lb = lot_m.node_tree.nodes.get("Principled BSDF")
        if lb:
            lot_old = tuple(lb.inputs["Base Color"].default_value)
            lb.inputs["Base Color"].default_value = (0.035, 0.035, 0.038, 1)
    shot("photo", (Lr * 1.05, -Lr * 1.6, 5.8), (Lr * 0.1, -Lr * 0.12, 2.4))
    if os.environ.get("NC_REFSHEET"):                   # the eight studio angles of the reference sheet
        cam.data.lens = 55                               # the sheet's cameras, fitted to its silhouettes (2026-11-24)
        rx, ry = scene.render.resolution_x, scene.render.resolution_y
        scene.render.resolution_x, scene.render.resolution_y = 600, 600
        for k, (a, h) in enumerate(REF_VIEWS):
            ar = math.radians(a)
            d = 33.0
            shot(f"ref{k}", (d * math.sin(ar), -d * math.cos(ar), h), (0, 0, ROOF * 0.42))
        scene.render.resolution_x, scene.render.resolution_y = 1024, 1536
        cam.data.lens = 110
        shot("reftop", (0.0, 0.05, Lr * 7.0), (0, 0, 0))
        scene.render.resolution_x, scene.render.resolution_y = rx, ry
    if lot_old:
        lb.inputs["Base Color"].default_value = lot_old
    for b_, r_ in gloss.values():
        b_.inputs["Roughness"].default_value = r_
        if "Coat Weight" in b_.inputs:
            b_.inputs["Coat Weight"].default_value = 0.0
    cam.data.lens = lens
for i, (nm, b, liv, paint) in enumerate(SHOWCASE):
    show(b, liv, paint)
    shot(nm, (-Lr * 1.55, -Lr * 2.1, ROOF * 1.4 + 2) if i % 2 == 0 else (Lr * 1.4, Lr * 2.2, ROOF * 1.4 + 2), (0, 0, fz))
show()
pose(1.0)
shot("open_front34", (-Lr * 1.7, -Lr * 1.9, ROOF * 1.8 + 3), (0, -1.0, fz))
shot("open_rear34", (Lr * 1.6, Lr * 2.0, ROOF * 1.8 + 3), (0, 1.5, fz))
if os.environ.get("NC_DEBUG_SHOTS"):
    pose(0.0)
    shot("dbg_hood", (-Lr * 0.55, -Lr * 1.15, ROOF * 1.5), (0, L0 + 2.5, BELT - 0.6))
    shot("dbg_cornerA", (W + 3.5, L0 - 3.5, 2.6), (W - 1.0, L0 + 1.0, 1.9))
    shot("dbg_quarter", (W + 6.0, (Q or B) + 1.0, 4.8), (W - 0.6, (Q or B) + 1.0, 4.2))
    shot("dbg_quarter_back", (W + 2.6, L1 + 3.5, 6.0), (W - 0.9, (Q or B) + 1.6, 4.4))
    shot("dbg_door_gap", (10.3, 4.6, 1.72), (3.44, 6.9, 0.57))
    shot("dbg_rwheel", (W + 6.0, WY_R, 1.6), (W, WY_R, 1.4))
    shot("dbg_cornerB", (-W - 3.5, L0 - 3.5, 2.6), (-W + 1.0, L0 + 1.0, 1.9))
    shot("dbg_hood_side", (-Lr * 1.1, -Lr * 0.55, BELT + 0.8), (0, (L0 + A0) / 2, BELT - 0.5))
    HINGES_SAVE = {k: v["open"] for k, v in HINGES.items()}
    for k in HINGES:
        if k != "Hood":
            HINGES[k]["open"] = 0
    pose(1.0)
    shot("dbg_hood_open", (-Lr * 0.8, -Lr * 1.2, ROOF * 1.4), (0, (L0 + A0) / 2, BELT - 0.5))
    for k, v in HINGES_SAVE.items():
        HINGES[k]["open"] = v
    shot("dbg_rear_right", (-Lr * 0.9, Lr * 1.3, ROOF * 0.9), (-W * 0.5, L1 - 1.5, TAIL - 0.6))
    pose(1.0)
    shot("dbg_hatch_open", (Lr * 0.5, Lr * 1.25, ROOF * 1.6), (0, C1, BELT))
pose(0.0)
if WINDOWS:
    pose(0.0, win=0.5)
    shot("windows_half", (Lr * 1.9, -Lr * 0.6, ROOF * 1.0), (0, 0, fz + 0.6))
    pose(0.0, win=1.0)
    shot("windows_down", (Lr * 2.6, 0.0, ROOF * 0.9), (0, 0, fz))
    pose(0.0)
print("NEONCOAST_DONE", json.dumps({"vehicle": VID, "car": sum(car_tris.values()), "wheel": sum(wheel_tris.values()),
                                    "options": data["Car"]["Options"], "wheelOptions": data["Wheel"]["Options"]}))
