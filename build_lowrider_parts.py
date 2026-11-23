# Neon Coast lowrider: every swappable part, run from build_lowrider.py (it shares that script's helpers).
# Each part variant is a set of pieces whose kind is registered with opt(slot, variant, mat); the game shows the
# variant the player picked and colours each piece by its mat:
#   Chrome  -> the slot's trim finish (chrome / gold / black chrome / body colour / satin black)
#   Body    -> the paint          Dark -> black trim     Glass -> glass      Light -> lamp colour
#   Seat / SeatTrim -> seat material + colour / stitching    Wood -> wood     Gauge -> live speedometer face
#   Dash -> dash colour     Neon -> underglow / accent colour     Fur -> fuzzy dice     Rubber -> tyre
# Car pieces: front = -Y, origin on the ground between the axles (same frame as build_lowrider.py).
OPT_INFO = {}


def opt(slot, variant, mat):
    kind = f"Opt{slot}{variant}{mat}"
    OPT_INFO[kind] = {"slot": slot, "variant": variant, "mat": mat}
    return kind


def wopt(slot, variant, mat):
    kind = f"{slot}{variant}{mat}"
    WHEEL_INFO[kind] = {"slot": slot, "variant": variant, "mat": mat}
    return kind


WHEEL_INFO = {}
COLORS.update({"Dark": (0.05, 0.05, 0.06), "Light": (1.0, 0.97, 0.86), "Seat": (0.95, 0.93, 0.88), "SeatTrim": (0.85, 0.82, 0.78),
               "Wood": (0.42, 0.22, 0.1), "Gauge": (0.02, 0.02, 0.03), "Neon": (0.9, 0.2, 0.8), "Fur": (0.95, 0.95, 0.95),
               "Rubber": (0.07, 0.07, 0.08), "Top": (0.04, 0.04, 0.045), "Spokes": (0.86, 0.87, 0.90), "Dish": (0.86, 0.87, 0.90), "Band": (0.96, 0.96, 0.94)})


COLORS.update({"Head": (1.0, 0.97, 0.86), "Tail": (0.85, 0.05, 0.05)})


def mat_color(kind):
    info = OPT_INFO.get(kind) or WHEEL_INFO.get(kind)
    if info:
        m = info["mat"]
        return {"Chrome": "Chrome", "Body": "Body", "Dash": "Dash", "Hub": "Chrome", "Rim": "Chrome"}.get(m, m)
    base = kind.split("__")[0]                            # pieces moved onto a door keep their material
    if base in ("HoodInner", "DoorJambL", "DoorJambR"):
        return "Body"
    return {"RoofGlass": "Glass", "RoofBody": "Body", "RoofChrome": "Chrome"}.get(base, base)


# ================================================================================================ exterior
def front_bumpers():
    S = "FrontBumper"
    y0, y1 = -10.75, -10.28
    # Classic: full-width chrome bar, wraparounds, two guards
    k = opt(S, "Classic", "Chrome")
    box(k, -3.7, y0, 0.92, 3.7, y1, 1.52, bev=0.16)
    for s in (-1, 1):
        beam(k, (s * 3.55, (y0 + y1) / 2, 1.22), (s * 3.84, (y0 + y1) / 2 + 1.25, 1.22), 0.5, 0.56)
        box(k, s * 1.6 - 0.18, y0 - 0.12, 0.98, s * 1.6 + 0.18, y1, 1.62, bev=0.08)
    # Bullet: heavier bar with big bullet guards
    k = opt(S, "Bullet", "Chrome")
    box(k, -3.75, y0 - 0.05, 0.88, 3.75, y1, 1.58, bev=0.2)
    for s in (-1, 1):
        beam(k, (s * 3.6, (y0 + y1) / 2, 1.23), (s * 3.86, (y0 + y1) / 2 + 1.3, 1.23), 0.55, 0.62)
        cyl(k, (s * 1.5, y0 - 0.05, 1.23), (s * 1.5, y0 - 0.75, 1.23), 0.26, seg=20, r2=0.06)
    # Shaved: body-colour roll pan with a thin chrome lip
    box(opt(S, "Shaved", "Body"), -3.65, y0 + 0.1, 0.95, 3.65, y1, 1.5, bev=0.18)
    box(opt(S, "Shaved", "Chrome"), -3.4, y0 + 0.06, 1.18, 3.4, y0 + 0.12, 1.24)
    # Tube: tubular push bar
    k = opt(S, "Tube", "Chrome")
    cyl(k, (-3.4, y0 - 0.1, 1.25), (3.4, y0 - 0.1, 1.25), 0.12, seg=14)
    cyl(k, (-3.0, y0 - 0.1, 0.95), (3.0, y0 - 0.1, 0.95), 0.1, seg=14)
    for s in (-1, 1):
        cyl(k, (s * 3.4, y0 - 0.1, 1.25), (s * 3.4, y1, 1.25), 0.12, seg=14)
        cyl(k, (s * 1.3, y0 - 0.1, 0.95), (s * 1.3, y0 - 0.1, 1.25), 0.08, seg=10)
    # Split: two halves with a plate frame in the middle
    k = opt(S, "Split", "Chrome")
    for s in (-1, 1):
        box(k, s * 0.75, y0, 0.95, s * 3.7, y1, 1.5, bev=0.15)
        beam(k, (s * 3.55, (y0 + y1) / 2, 1.22), (s * 3.84, (y0 + y1) / 2 + 1.25, 1.22), 0.5, 0.52)
    box(opt(S, "Split", "Dark"), -0.72, y0 + 0.08, 0.98, 0.72, y1, 1.45)


def rear_bumpers():
    S = "RearBumper"
    y0, y1 = 10.32, 10.8
    k = opt(S, "Classic", "Chrome")
    box(k, -3.7, y0, 0.92, 3.7, y1, 1.52, bev=0.16)
    for s in (-1, 1):
        beam(k, (s * 3.55, (y0 + y1) / 2, 1.22), (s * 3.84, (y0 + y1) / 2 - 1.25, 1.22), 0.5, 0.56)
        box(k, s * 1.6 - 0.18, y0, 0.98, s * 1.6 + 0.18, y1 + 0.12, 1.62, bev=0.08)
    k = opt(S, "Bullet", "Chrome")
    box(k, -3.75, y0, 0.88, 3.75, y1 + 0.05, 1.58, bev=0.2)
    for s in (-1, 1):
        beam(k, (s * 3.6, (y0 + y1) / 2, 1.23), (s * 3.86, (y0 + y1) / 2 - 1.3, 1.23), 0.55, 0.62)
        cyl(k, (s * 1.5, y1 + 0.05, 1.23), (s * 1.5, y1 + 0.75, 1.23), 0.26, seg=20, r2=0.06)
    box(opt(S, "Shaved", "Body"), -3.65, y0, 0.95, 3.65, y1 - 0.1, 1.5, bev=0.18)
    box(opt(S, "Shaved", "Chrome"), -3.4, y1 - 0.12, 1.18, 3.4, y1 - 0.06, 1.24)
    k = opt(S, "Tube", "Chrome")
    cyl(k, (-3.4, y1 + 0.1, 1.25), (3.4, y1 + 0.1, 1.25), 0.12, seg=14)
    for s in (-1, 1):
        cyl(k, (s * 3.4, y1 + 0.1, 1.25), (s * 3.4, y0, 1.25), 0.12, seg=14)


def grilles():
    S = "Grille"
    yb, yf = -10.42, -10.47
    x0, x1, z0, z1 = -2.2, 2.2, 1.66, 2.15
    for v in ("Bars", "Eggcrate", "Waterfall", "Mesh", "Billet"):
        box(opt(S, v, "Dark"), -2.25, yb, 1.62, 2.25, -10.2, 2.18)
        k = opt(S, v, "Chrome")
        box(k, -2.35, -10.5, 2.15, 2.35, -10.36, 2.25, bev=0.03)
        box(k, -2.35, -10.5, 1.55, 2.35, -10.36, 1.65, bev=0.03)
        if v == "Bars":
            for i in range(5):
                z = 1.68 + i * 0.115
                box(k, x0, yf, z, x1, -10.4, z + 0.05)
            for i in range(-4, 5):
                box(k, i * 0.48 - 0.025, -10.48, z0, i * 0.48 + 0.025, -10.4, z1)
        elif v == "Eggcrate":
            for i in range(4):
                z = z0 + (z1 - z0) * (i + 0.5) / 4
                box(k, x0, yf - 0.02, z - 0.03, x1, -10.4, z + 0.03)
            for i in range(-6, 7):
                box(k, i * 0.34 - 0.03, yf - 0.02, z0, i * 0.34 + 0.03, -10.4, z1)
        elif v == "Waterfall":
            for i in range(-14, 15):
                x = i * 0.15
                box(k, x - 0.025, yf - 0.03, z0, x + 0.025, -10.4, z1)
            box(k, -0.06, yf - 0.06, z0, 0.06, -10.4, z1)
        elif v == "Mesh":
            n = 20
            for i in range(n + 1):
                t = i / n
                beam(k, (x0 + (x1 - x0) * t, yf, z0), (min(x1, x0 + (x1 - x0) * t + 0.5), yf, z1), 0.02, 0.02, up=(0, -1, 0))
                beam(k, (x0 + (x1 - x0) * t, yf - 0.01, z0), (max(x0, x0 + (x1 - x0) * t - 0.5), yf - 0.01, z1), 0.02, 0.02, up=(0, -1, 0))
        else:  # Billet: three fat polished bars
            for i in range(3):
                z = z0 + 0.06 + i * 0.16
                box(k, x0, yf - 0.05, z, x1, -10.4, z + 0.09, bev=0.03)


def hoods():
    S = "Hood"
    k = opt(S, "Spear", "Chrome")
    beam(k, (0, -10.1, deck_z(0, -10.1) + 0.03), (0, -6.5, deck_z(0, -6.5) + 0.03), 0.05, 0.05)
    # Louvers: three rows of punched louvres each side
    for s in (-1, 1):
        for row in range(3):
            for i in range(5):
                x = s * (0.8 + row * 0.75)
                y = -8.6 + i * 0.55
                z = deck_z(x, y)
                box(opt(S, "Louvers", "Dark"), x - 0.28, y, z - 0.01, x + 0.28, y + 0.06, z + 0.07)
                box(opt(S, "Louvers", "Body"), x - 0.3, y - 0.18, z, x + 0.3, y, z + 0.06)
    # Cowl: raised centre bulge
    pts_o, pts_i = [], []
    k = opt(S, "Cowl", "Body")
    for j in range(9):
        y = -9.4 + j * 0.8
        h = 0.18 * math.sin(math.pi * min(1, j / 7.5))
        beam(k, (-0.9, y, deck_z(0, y) + h / 2), (0.9, y, deck_z(0, y) + h / 2), 0.8, max(h, 0.02), up=(0, 0, 1))
    # Scoop: forward-facing scoop with a dark mouth
    k = opt(S, "Scoop", "Body")
    z = deck_z(0, -5.5)
    box(k, -0.9, -6.6, z - 0.02, 0.9, -4.4, z + 0.32, bev=0.12)
    box(opt(S, "Scoop", "Dark"), -0.75, -6.66, z + 0.05, 0.75, -6.5, z + 0.27)
    box(opt(S, "Scoop", "Chrome"), -0.78, -6.7, z + 0.02, 0.78, -6.62, z + 0.05)


def spoilers():
    S = "Spoiler"
    z = deck_z(0, 9.6)
    k = opt(S, "Ducktail", "Body")
    prism(k, [(-3.0, 9.2, z), (3.0, 9.2, z), (3.0, 9.82, z + 0.28), (-3.0, 9.82, z + 0.28)],
          [(-3.0, 9.2, z - 0.05), (3.0, 9.2, z - 0.05), (3.0, 9.82, z - 0.05), (-3.0, 9.82, z - 0.05)])
    k = opt(S, "Wing", "Body")
    box(k, -3.0, 9.0, z + 0.7, 3.0, 9.75, z + 0.82, bev=0.04)
    for s in (-1, 1):
        box(opt(S, "Wing", "Chrome"), s * 2.2 - 0.06, 9.3, z, s * 2.2 + 0.06, 9.5, z + 0.72)
        box(k, s * 3.0 - 0.04, 8.95, z + 0.55, s * 3.0 + 0.04, 9.8, z + 0.95)
    # Fins: tall tail fins on the rear fenders
    for s in (-1, 1):
        x = s * (W - 0.2)
        prism(opt(S, "Fins", "Body"), [(x - 0.05, 7.4, 2.75), (x - 0.05, 10.4, 2.6), (x - 0.05, 10.3, 3.45)],
              [(x + 0.05, 7.4, 2.75), (x + 0.05, 10.4, 2.6), (x + 0.05, 10.3, 3.45)])
        cyl(opt(S, "Fins", "Light"), (x, 10.25, 3.0), (x, 10.45, 3.0), 0.12, seg=14)


def skirts():
    S = "Skirts"
    for s in (-1, 1):
        # Rocker: body-colour rocker extension with a chrome strip
        box(opt(S, "Rocker", "Body"), s * (W - 0.15), WY_F + ARCH + 0.15, 0.62, s * (W + 0.08), WY_R - ARCH - 0.15, 0.95, bev=0.05)
        box(opt(S, "Rocker", "Chrome"), s * (W + 0.07), WY_F + ARCH + 0.2, 0.88, s * (W + 0.1), WY_R - ARCH - 0.2, 0.93)
        # Wide chrome plates
        box(opt(S, "Chrome", "Chrome"), s * (W - 0.05), WY_F + ARCH + 0.15, 0.7, s * (W + 0.06), WY_R - ARCH - 0.15, 1.22, bev=0.03)
        # Fender skirts over the rear wheels (classic lowrider)
        k = opt(S, "Fender", "Body")
        pts = []
        for i in range(17):
            a = math.pi * i / 16
            pts.append((WY_R + math.cos(a) * (ARCH + 0.02), WR + math.sin(a) * (ARCH + 0.02)))
        pts = [(WY_R + ARCH + 0.02, 0.85)] + pts + [(WY_R - ARCH - 0.02, 0.85)]
        xo, xi = s * (W + 0.03), s * (W - 0.08)
        prism(k, [(xo, y, z) for (y, z) in pts], [(xi, y, z) for (y, z) in pts])
        beam(opt(S, "Fender", "Chrome"), (s * (W + 0.05), WY_R - ARCH, 1.0), (s * (W + 0.05), WY_R + ARCH, 1.0), 0.03, 0.08)


def mirrors():
    S = "Mirrors"
    for v, sides in (("Bullet", (1,)), ("Dual", (1, -1)), ("Rect", (1, -1)), ("Stem", (1, -1))):
        k = opt(S, v, "Chrome")
        for s in sides:
            x = s * 3.55
            if v in ("Bullet", "Dual"):
                cyl(k, (x, -2.25, 2.85), (x, -2.25, 3.1), 0.04, seg=8)
                cyl(k, (x, -2.35, 3.18), (x, -2.05, 3.18), 0.17, seg=16, bev=0.03)
                cyl(k, (x, -2.5, 3.18), (x, -2.35, 3.18), 0.17, seg=16, r2=0.05)
            elif v == "Rect":
                cyl(k, (x, -2.25, 2.85), (x, -2.25, 3.05), 0.04, seg=8)
                box(k, x - 0.06, -2.3, 3.0, x + 0.06, -2.1, 3.35, bev=0.03)
                box(opt(S, v, "Glass"), x - 0.07, -2.13, 3.04, x + 0.07, -2.09, 3.31)
            else:
                beam(k, (x, -2.25, 2.85), (x + s * 0.25, -2.25, 3.45), 0.04, 0.04)
                cyl(k, (x + s * 0.25, -2.32, 3.55), (x + s * 0.25, -2.18, 3.55), 0.2, seg=20, bev=0.03)


def ornaments():
    S = "Ornament"
    y, z = -9.7, deck_z(0, -9.7)
    k = opt(S, "Sun", "Chrome")
    cyl(k, (0, y, z), (0, y, z + 0.18), 0.05, seg=8)
    cyl(k, (0, y - 0.03, z + 0.4), (0, y + 0.03, z + 0.4), 0.18, seg=20)
    for i in range(10):
        a = 2 * math.pi * i / 10
        beam(k, (0, y, z + 0.4), (math.cos(a) * 0.32, y, z + 0.4 + math.sin(a) * 0.32), 0.04, 0.04, up=(0, 1, 0))
    k = opt(S, "Wings", "Chrome")
    cyl(k, (0, y, z), (0, y, z + 0.2), 0.05, seg=8)
    for s in (-1, 1):
        prism(k, [(0, y - 0.1, z + 0.2), (s * 0.7, y + 0.35, z + 0.45), (s * 0.55, y + 0.35, z + 0.25)],
              [(0, y - 0.1, z + 0.17), (s * 0.7, y + 0.35, z + 0.42), (s * 0.55, y + 0.35, z + 0.22)])
    k = opt(S, "Comet", "Chrome")
    cyl(k, (0, y - 0.2, z + 0.25), (0, y - 0.2, z + 0.25), 0.1, seg=12)
    cyl(k, (0, y, z), (0, y, z + 0.12), 0.04, seg=8)
    cyl(k, (0, y - 0.25, z + 0.22), (0, y + 0.55, z + 0.12), 0.1, seg=12, r2=0.01)


def exhausts():
    S = "Exhaust"
    for s in (-1, 1):
        cyl(opt(S, "Dual", "Chrome"), (s * 1.0, 10.2, 0.8), (s * 1.0, 10.95, 0.8), 0.13, seg=16, r2=0.15)
        cyl(opt(S, "Dual", "Dark"), (s * 1.0, 10.94, 0.8), (s * 1.0, 10.97, 0.8), 0.11, seg=16)
        cyl(opt(S, "Side", "Chrome"), (s * (W + 0.15), -3.8, 0.75), (s * (W + 0.15), 3.4, 0.75), 0.12, seg=16)
        cyl(opt(S, "Side", "Dark"), (s * (W + 0.15), 3.4, 0.75), (s * (W + 0.15), 3.42, 0.75), 0.1, seg=16)
        beam(opt(S, "Turndown", "Chrome"), (s * 3.2, 9.6, 0.7), (s * 3.5, 9.9, 0.45), 0.2, 0.2)


def visors():
    S = "Visor"
    z, y = 4.62, -0.9
    for v, m in (("Chrome", "Chrome"), ("Body", "Body")):
        k = opt(S, v, m)
        prism(k, [(-2.95, y, z + 0.02), (2.95, y, z + 0.02), (3.05, y - 0.9, z - 0.15), (-3.05, y - 0.9, z - 0.15)],
              [(-2.95, y, z - 0.03), (2.95, y, z - 0.03), (3.05, y - 0.9, z - 0.2), (-3.05, y - 0.9, z - 0.2)])
        for s in (-1, 1):
            box(k, s * 2.6 - 0.04, y - 0.85, z - 0.2, s * 2.6 + 0.04, y - 0.1, z - 0.05)


def underglow():
    k = opt("Glow", "On", "Neon")
    for s in (-1, 1):
        box(k, s * 3.2 - 0.05, -8.5, 0.68, s * 3.2 + 0.05, 8.5, 0.72)
    box(k, -2.8, -9.9, 0.68, 2.8, -9.8, 0.72)
    box(k, -2.8, 9.8, 0.68, 2.8, 9.9, 0.72)


def tops():
    """roof: vinyl tops (landau = rear half) and the convertible (game hides the hardtop roof, rear + side glass)"""
    S = "Top"
    ROOF, xs_t, yA1, yC0, yC1, zb, xs_b = 4.62, 2.92, -0.85, 3.3, 5.35, 2.84, 3.42

    def gx(z):
        return xs_b + (xs_t - xs_b) * (z - zb) / (4.56 - zb)
    # Vinyl: grained top over the whole roof, Landau: rear half + chrome S-bars on the sail panels
    for v, y0 in (("Vinyl", yA1 - 0.08), ("Landau", 1.2)):
        y1 = yC0 + 0.12
        cube(opt(S, v, "Top"), Vector((0, (y0 + y1) / 2, ROOF + 0.08)), (2 * xs_t + 0.24, y1 - y0, 0.2), 0.09)
        box(opt(S, v, "Chrome"), -xs_t - 0.08, y0 - 0.03, ROOF + 0.06, xs_t + 0.08, y0 + 0.03, ROOF + 0.17)
    for s in (-1, 1):
        k = opt(S, "Landau", "Chrome")
        pts = [(2.75, 4.25), (3.25, 4.15), (3.6, 3.85), (3.85, 3.62), (4.25, 3.5), (4.6, 3.3)]
        for (ya, za), (yb, zb2) in zip(pts, pts[1:]):
            beam(k, (s * (gx(za) + 0.06 + (ya - 2.3) * 0.0), ya, za), (s * (gx(zb2) + 0.06), yb, zb2), 0.08, 0.05)
    # Down: folded top under a boot behind the rear seat + a chrome windshield header
    k = opt(S, "Down", "Top")
    box(k, -3.05, 4.25, 2.7, 3.05, 5.55, 3.15, bev=0.18)
    box(opt(S, "Down", "Chrome"), -3.1, 5.5, 2.72, 3.1, 5.62, 2.86)
    box(opt(S, "Down", "Chrome"), -(xs_t - 0.05), yA1 - 0.08, ROOF - 0.1, xs_t - 0.05, yA1 + 0.1, ROOF + 0.04, bev=0.03)



def headlights():
    S = "Headlights"
    yb, yf, z = -10.2, -10.47, 1.92
    for s in (-1, 1):
        # Quad: four round lamps in chrome rings (the original look)
        for x in (2.62, 3.18):
            cyl(opt(S, "Quad", "Head"), (s * x, yb, z), (s * x, yf, z), 0.24, seg=20, bev=0.03)
            ring(opt(S, "Quad", "Chrome"), (s * x, yf + 0.03, z), (0, 1, 0), 0.23, 0.31, 0.08, seg=24)
        # Dual: one big round lamp each side
        cyl(opt(S, "Dual", "Head"), (s * 2.9, yb, z), (s * 2.9, yf, z), 0.34, seg=24, bev=0.04)
        ring(opt(S, "Dual", "Chrome"), (s * 2.9, yf + 0.03, z), (0, 1, 0), 0.33, 0.43, 0.09, seg=28)
        # Square: rectangular quads in one chrome bezel
        for x in (2.62, 3.18):
            box(opt(S, "Square", "Head"), s * x - 0.24, yf, z - 0.2, s * x + 0.24, yb, z + 0.2, bev=0.04)
        box(opt(S, "Square", "Chrome"), s * 2.9 - 0.62, yf + 0.02, z - 0.27, s * 2.9 + 0.62, yf + 0.06, z - 0.21)
        box(opt(S, "Square", "Chrome"), s * 2.9 - 0.62, yf + 0.02, z + 0.21, s * 2.9 + 0.62, yf + 0.06, z + 0.27)
        # Frenched: lamps set back in body-colour tunnels
        for x in (2.62, 3.18):
            cyl(opt(S, "Frenched", "Head"), (s * x, yb + 0.1, z), (s * x, yb - 0.08, z), 0.22, seg=20)
            cyl(opt(S, "Frenched", "Body"), (s * x, yb, z), (s * x, yf - 0.06, z), 0.3, seg=24, r2=0.29)
            cyl(opt(S, "Frenched", "Dark"), (s * x, yf - 0.06, z), (s * x, yf - 0.065, z), 0.24, seg=20)
        # Hooded: quads under body-colour eyebrows
        for x in (2.62, 3.18):
            cyl(opt(S, "Hooded", "Head"), (s * x, yb, z), (s * x, yf, z), 0.24, seg=20, bev=0.03)
            ring(opt(S, "Hooded", "Chrome"), (s * x, yf + 0.03, z), (0, 1, 0), 0.23, 0.3, 0.06, seg=24)
        prism(opt(S, "Hooded", "Body"), [(s * 2.25, yf + 0.05, z + 0.3), (s * 3.55, yf + 0.05, z + 0.3), (s * 3.55, yf - 0.32, z + 0.22), (s * 2.25, yf - 0.32, z + 0.22)],
              [(s * 2.25, yf + 0.05, z + 0.38), (s * 3.55, yf + 0.05, z + 0.38), (s * 3.55, yf - 0.32, z + 0.3), (s * 2.25, yf - 0.32, z + 0.3)])


def taillights():
    S = "Taillights"
    yb, yf, z = 10.25, 10.55, 1.98
    for s in (-1, 1):
        for x in (1.55, 2.3, 3.02):                      # Triple round (original)
            cyl(opt(S, "Triple", "Tail"), (s * x, yb, z), (s * x, yf, z), 0.23, seg=20, bev=0.03)
            ring(opt(S, "Triple", "Chrome"), (s * x, yf - 0.03, z), (0, 1, 0), 0.22, 0.29, 0.08, seg=24)
        for x in (1.9, 2.85):                            # Twin big rounds
            cyl(opt(S, "Twin", "Tail"), (s * x, yb, z), (s * x, yf, z), 0.3, seg=24, bev=0.04)
            ring(opt(S, "Twin", "Chrome"), (s * x, yf - 0.03, z), (0, 1, 0), 0.29, 0.37, 0.08, seg=28)
        box(opt(S, "Oval", "Tail"), s * 1.4, yb, z - 0.17, s * 3.3, yf, z + 0.17, bev=0.15)   # Oval pods
        box(opt(S, "Oval", "Chrome"), s * 1.32, yf - 0.06, z - 0.23, s * 3.38, yf - 0.02, z + 0.23, bev=0.18)
        for zz in (1.72, 2.22):                          # Stacked pairs at the corners
            cyl(opt(S, "Stacked", "Tail"), (s * 3.0, yb, zz), (s * 3.0, yf, zz), 0.2, seg=20, bev=0.03)
            ring(opt(S, "Stacked", "Chrome"), (s * 3.0, yf - 0.03, zz), (0, 1, 0), 0.19, 0.26, 0.07, seg=24)
    box(opt(S, "Bar", "Tail"), -3.35, yb, z - 0.12, 3.35, yf, z + 0.12)                     # full-width bar
    box(opt(S, "Bar", "Chrome"), -3.42, yf - 0.05, z - 0.17, 3.42, yf - 0.01, z - 0.12)
    box(opt(S, "Bar", "Chrome"), -3.42, yf - 0.05, z + 0.12, 3.42, yf - 0.01, z + 0.17)


def side_trim():
    S = "SideTrim"
    a0, a1 = WY_F + ARCH + 0.25, WY_R - ARCH - 0.25
    for s in (-1, 1):
        x = s * (W + 0.02)
        k = opt(S, "Classic", "Chrome")                  # spear between the arches + fender spears + rocker moulding
        beam(k, (x, a0, 2.12), (x, a1, 2.12), 0.06, 0.07)
        beam(k, (x, WY_F - ARCH - 0.2, 2.12), (s * (W - 0.02), -9.9, 2.12), 0.06, 0.07)
        beam(k, (x, WY_R + ARCH + 0.2, 2.12), (s * (W - 0.02), 10.0, 2.12), 0.06, 0.07)
        beam(k, (s * (W * 0.975 + 0.02), WY_F + ARCH + 0.2, 0.98), (s * (W * 0.975 + 0.02), WY_R - ARCH - 0.2, 0.98), 0.05, 0.12)
        k = opt(S, "Belt", "Chrome")                     # one long strip on the belt line, nose to tail
        beam(k, (s * (W - 0.01), -10.0, 2.64), (s * (W - 0.01), 10.1, 2.64), 0.07, 0.08)
        k = opt(S, "Double", "Chrome")                   # two parallel spears + rocker moulding
        for z in (2.12, 1.6):
            beam(k, (x, a0, z), (x, a1, z), 0.05, 0.06)
        beam(k, (s * (W * 0.975 + 0.02), WY_F + ARCH + 0.2, 0.98), (s * (W * 0.975 + 0.02), WY_R - ARCH - 0.2, 0.98), 0.05, 0.12)
        k = opt(S, "Sweep", "Chrome")                    # a spear sweeping down from the front fender
        beam(k, (x, a0, 2.45), (x, a1, 1.45), 0.06, 0.08)
        beam(k, (x, WY_F - ARCH - 0.2, 2.45), (s * (W - 0.02), -9.9, 2.45), 0.05, 0.07)
        k = opt(S, "Wide", "Chrome")                     # wide brushed rocker panel + spear
        box(k, s * (W - 0.02), a0, 0.82, s * (W + 0.04), a1, 1.18, bev=0.02)
        beam(k, (x, a0, 2.12), (x, a1, 2.12), 0.06, 0.07)


def door_panels():
    S = "Doors"
    for s in (-1, 1):
        for v in ("Rolls", "Diamond", "Smooth", "WoodInsert", "Channel"):
            box(opt(S, v, "Seat"), s * 3.3 - 0.1, -2.4, 1.05, s * 3.3 + 0.1, 5.0, 2.75)
        xi = s * 3.18
        for k in range(6):                                # tuck-and-roll
            z = 1.3 + k * 0.22
            box(opt(S, "Rolls", "SeatTrim"), xi - 0.03, -2.2, z, xi + 0.03, 4.8, z + 0.06)
        for i in range(12):                               # diamond buttons
            for j in range(4):
                y = -2.0 + i * 0.58 + (0.29 if j % 2 else 0)
                cyl(opt(S, "Diamond", "SeatTrim"), (xi + s * 0.02, y, 1.45 + j * 0.3), (xi - s * 0.03, y, 1.45 + j * 0.3), 0.04, seg=6)
        box(opt(S, "Smooth", "Chrome"), xi - 0.03, -2.2, 2.2, xi + 0.03, 4.8, 2.26)          # smooth + chrome strip + armrest
        box(opt(S, "Smooth", "SeatTrim"), xi - s * 0.15, -0.6, 1.75, xi + s * 0.02, 1.6, 1.95, bev=0.05)
        box(opt(S, "WoodInsert", "Wood"), xi - 0.03, -2.0, 1.95, xi + 0.03, 4.6, 2.45)        # wood band
        box(opt(S, "WoodInsert", "Chrome"), xi - 0.035, -2.0, 1.9, xi + 0.035, 4.6, 1.94)
        for i in range(10):                               # wide vertical channels
            y = -2.1 + i * 0.7
            box(opt(S, "Channel", "SeatTrim"), xi - 0.03, y, 1.25, xi + 0.03, y + 0.06, 2.6)


def headliner():
    S = "Headliner"
    z = 4.44
    for v in ("Plain", "Diamond", "Pleated", "Stars"):
        box(opt(S, v, "Seat"), -2.85, -0.7, z, 2.85, 3.2, z + 0.06)
    for i in range(9):
        for j in range(6):
            x = -2.4 + i * 0.6 + (0.3 if j % 2 else 0)
            cyl(opt(S, "Diamond", "SeatTrim"), (x, -0.4 + j * 0.62, z - 0.02), (x, -0.4 + j * 0.62, z + 0.01), 0.04, seg=6)
    for i in range(12):
        x = -2.6 + i * 0.47
        box(opt(S, "Pleated", "SeatTrim"), x - 0.03, -0.6, z - 0.03, x + 0.03, 3.1, z)
    import random as _r
    rnd = _r.Random(7)
    for i in range(60):                                   # fibre-optic star ceiling
        x, y = rnd.uniform(-2.7, 2.7), rnd.uniform(-0.6, 3.1)
        cube(opt(S, "Stars", "Neon"), Vector((x, y, z - 0.01)), (0.035, 0.035, 0.02))


def audio():
    S = "Audio"
    for s in (-1, 1):
        x, y, z = s * 1.9, 4.75, 3.02
        for v in ("Speakers", "Neon"):
            box(opt(S, v, "Dark"), x - 0.55, y - 0.3, z - 0.06, x + 0.55, y + 0.3, z + 0.04, bev=0.04)
            ring(opt(S, v, "Chrome"), (x, y, z + 0.05), (0, 0, 1), 0.2, 0.26, 0.04, seg=24)
        ring(opt(S, "Neon", "Neon"), (x, y, z + 0.06), (0, 0, 1), 0.27, 0.32, 0.03, seg=24)
    box(opt(S, "Speakers", "Dark"), -0.6, 4.45, 2.96, 0.6, 5.05, 3.06)   # centre tweeter bar
    box(opt(S, "Neon", "Dark"), -0.6, 4.45, 2.96, 0.6, 5.05, 3.06)


def pedals():
    S = "Pedals"
    for v, m in (("Stock", "Dark"), ("Billet", "Chrome"), ("Chain", "Chrome")):
        k = opt(S, v, m)
        box(k, 1.0, -2.45, 1.25, 1.35, -2.38, 1.55, bev=0.02)           # brake
        box(k, 1.65, -2.45, 1.2, 1.85, -2.38, 1.6, bev=0.02)            # gas
    for i in range(5):
        torus(opt("Pedals", "Chain", "Chrome"), (1.75, -2.36, 1.24 + i * 0.09), (0, 0, 1) if i % 2 else (1, 0, 0), 0.04, 0.012, seg=8, seg2=4)


def continental():
    S = "Continental"
    k = opt(S, "Kit", "Chrome")
    for s in (-1, 1):
        box(k, s * 1.2 - 0.12, 10.75, 1.0, s * 1.2 + 0.12, 11.9, 1.25, bev=0.05)
    box(k, -1.5, 11.7, 0.95, 1.5, 12.0, 1.35, bev=0.1)
    ring(k, (0, 11.87, 2.05), (0, 1, 0), 0.95, 1.1, 0.08, seg=40)
    cyl(k, (0, 11.85, 2.05), (0, 11.98, 2.05), 0.3, seg=20, bev=0.05)
    box(k, -0.12, 11.05, 1.25, 0.12, 11.4, 1.9)
    cyl(opt(S, "Kit", "Body"), (0, 11.25, 2.05), (0, 11.85, 2.05), 1.12, seg=36, bev=0.18)


def trunks():
    S = "Trunk"
    # Street: two chrome pumps, six batteries
    for y in (6.9, 8.2):
        cyl(opt(S, "Street", "Chrome"), (-2.4, y, 1.75), (1.0, y, 1.75), 0.3, seg=20, bev=0.04)
        cyl(opt(S, "Street", "Dark"), (1.0, y, 1.75), (2.0, y, 1.75), 0.34, seg=20)
        for x in (-2.0, -1.0, 0.0):
            cyl(opt(S, "Street", "Chrome"), (x, y, 2.05), (x, y, 2.45), 0.12, seg=12)
    for i in range(6):
        x = -2.75 + i * 1.1
        box(opt(S, "Street", "Dark"), x, 9.0, 1.32, x + 0.9, 9.7, 2.0, bev=0.03)
    # Show: four upright pumps in a row, mirror floor, 10 batteries in a rack
    for i in range(4):
        x = -2.4 + i * 1.6
        k = opt(S, "Show", "Chrome")
        cyl(k, (x, 7.3, 1.34), (x, 7.3, 2.5), 0.28, seg=20, bev=0.04)
        cyl(k, (x, 7.3, 2.5), (x, 7.3, 2.62), 0.18, seg=16)
        cyl(opt(S, "Show", "Dark"), (x, 6.6, 1.34), (x, 6.6, 2.2), 0.3, seg=20)
        beam(k, (x, 7.3, 1.6), (x, 8.7, 1.4), 0.07, 0.07)
    box(opt(S, "Show", "Glass"), -3.1, 6.1, 1.33, 3.1, 9.75, 1.35)
    for i in range(10):
        x = -2.85 + (i % 5) * 1.15
        y = 8.85 + (i // 5) * 0.45
        box(opt(S, "Show", "Neon"), x, y, 1.35, x + 0.95, y + 0.38, 2.0, bev=0.02)


# ================================================================================================ interior
def seat_bench(v, tuck):
    k, t = opt("Seats", v, "Seat"), opt("Seats", v, "SeatTrim")
    for yb, depth in ((-0.4, 1.7), (2.6, 1.6)):
        box(k, -3.05, yb, 1.05, 3.05, yb + depth, 1.75, bev=0.12)
        box(k, -3.05, yb + depth - 0.35, 1.75, 3.05, yb + depth, 3.3, bev=0.12)
        if tuck == "rolls":
            for i in range(9):
                x = -2.7 + i * 0.675
                box(t, x - 0.05, yb + depth - 0.42, 1.85, x + 0.05, yb + depth - 0.3, 3.2)
                box(t, x - 0.05, yb + 0.1, 1.74, x + 0.05, yb + depth - 0.4, 1.8)
        elif tuck == "diamond":
            for i in range(10):
                for j in range(4):
                    x = -2.75 + i * 0.6 + (0.3 if j % 2 else 0)
                    z = 1.95 + j * 0.33
                    cyl(t, (x, yb + depth - 0.4, z), (x, yb + depth - 0.34, z), 0.05, seg=6)
            for i in range(9):
                x = -2.7 + i * 0.675
                box(t, x - 0.03, yb + 0.1, 1.74, x + 0.03, yb + depth - 0.4, 1.78)
        elif tuck == "channel":  # wide vertical channels, piped
            for i in range(7):
                x = -2.6 + i * 0.86
                box(t, x - 0.04, yb + depth - 0.42, 1.85, x + 0.04, yb + depth - 0.3, 3.25)
                box(t, x - 0.04, yb + 0.05, 1.74, x + 0.04, yb + depth - 0.4, 1.8)
        elif tuck == "pillow":  # puffy horizontal pillows across the back
            for j in range(4):
                z = 1.98 + j * 0.34
                cyl(k, (-2.95, yb + depth - 0.38, z), (2.95, yb + depth - 0.38, z), 0.15, seg=12)
                box(t, -3.0, yb + depth - 0.4, z + 0.15, 3.0, yb + depth - 0.33, z + 0.18)
        else:  # split: two halves and a centre armrest
            box(t, -0.25, yb + 0.3, 1.75, 0.25, yb + depth - 0.4, 2.15, bev=0.08)
            for s in (-1, 1):
                for j in range(5):
                    z = 1.95 + j * 0.25
                    box(t, s * 0.4, yb + depth - 0.41, z, s * 2.9, yb + depth - 0.34, z + 0.04)


def seat_buckets():
    k, t = opt("Seats", "Buckets", "Seat"), opt("Seats", "Buckets", "SeatTrim")
    for s in (-1, 1):
        x = s * 1.55
        box(k, x - 1.05, -0.4, 1.05, x + 1.05, 1.3, 1.8, bev=0.15)
        box(k, x - 1.0, 0.95, 1.8, x + 1.0, 1.35, 3.5, bev=0.18)
        box(k, x - 0.55, 1.0, 3.5, x + 0.55, 1.3, 3.9, bev=0.1)                  # headrest
        for j in range(6):
            z = 1.95 + j * 0.24
            box(t, x - 0.75, 0.9, z, x + 0.75, 0.96, z + 0.05)
        box(t, x - 1.07, -0.35, 1.7, x - 0.95, 1.25, 1.85)                       # bolsters
        box(t, x + 0.95, -0.35, 1.7, x + 1.07, 1.25, 1.85)
    box(k, -0.35, -0.6, 1.05, 0.35, 1.0, 1.9, bev=0.1)                          # console
    box(k, -3.05, 2.6, 1.05, 3.05, 4.2, 1.75, bev=0.12)                         # rear bench
    box(k, -3.05, 3.85, 1.75, 3.05, 4.2, 3.3, bev=0.12)


def steering():
    S = "Steering"
    c = Vector((1.55, -1.7, 2.92))
    n = Vector((0, 0.55, 0.83)).normalized()
    u = n.cross(Vector((1, 0, 0))).normalized()
    v = n.cross(u)

    def on(r, a):
        return c + (u * math.cos(a) + v * math.sin(a)) * r
    # Chain: chrome chain-link rim
    k = opt(S, "Chain", "Chrome")
    torus(k, c, n, 0.52, 0.05, seg=24, seg2=6)
    for i in range(24):
        a = 2 * math.pi * i / 24
        torus(k, on(0.52, a), u * math.cos(a + math.pi / 2) + v * math.sin(a + math.pi / 2), 0.07, 0.022, seg=8, seg2=4)
    for a in (0, 2 * math.pi / 3, 4 * math.pi / 3):
        beam(k, c, on(0.5, a), 0.05, 0.03, up=tuple(n))
    # Wood: wood rim, polished spokes
    torus(opt(S, "Wood", "Wood"), c, n, 0.55, 0.07, seg=32, seg2=8)
    for a in (math.pi / 2, math.pi * 7 / 6, math.pi * 11 / 6):
        beam(opt(S, "Wood", "Chrome"), c, on(0.52, a), 0.12, 0.03, up=tuple(n))
    # Sport: thick dark three-spoke
    torus(opt(S, "Sport", "Dash"), c, n, 0.48, 0.08, seg=32, seg2=8)
    for a in (0, math.pi, math.pi * 3 / 2):
        beam(opt(S, "Sport", "Chrome"), c, on(0.45, a), 0.16, 0.04, up=tuple(n))
    # Banjo: thin rim, wire spokes
    torus(opt(S, "Banjo", "Seat"), c, n, 0.6, 0.045, seg=32, seg2=6)
    for i in range(12):
        beam(opt(S, "Banjo", "Chrome"), c, on(0.58, 2 * math.pi * i / 12), 0.015, 0.015, up=tuple(n))
    # Mini: small chrome chain wheel for show cars
    k = opt(S, "Mini", "Chrome")
    torus(k, c, n, 0.33, 0.045, seg=20, seg2=6)
    for i in range(16):
        a = 2 * math.pi * i / 16
        torus(k, on(0.33, a), u * math.cos(a + math.pi / 2) + v * math.sin(a + math.pi / 2), 0.055, 0.018, seg=8, seg2=4)
    for name in ("Chain", "Wood", "Sport", "Banjo", "Mini"):
        cyl(opt(S, name, "Chrome"), c - n * 0.02, c + n * 0.08, 0.12, seg=16)   # horn button


def dashes():
    S = "Dash"
    for v in ("Classic", "Wood", "Billet", "Digital"):
        box(opt(S, v, "Dash"), -3.25, -2.9, 2.2, 3.25, -2.25, 2.86, bev=0.1)
        # gauge face in front of the driver: the game draws the live speedometer on it
        prism(opt(S, v, "Gauge"), [(0.75, -2.24, 2.42), (2.35, -2.24, 2.42), (2.35, -2.36, 2.82), (0.75, -2.36, 2.82)],
              [(0.75, -2.28, 2.42), (2.35, -2.28, 2.42), (2.35, -2.4, 2.82), (0.75, -2.4, 2.82)])
    box(opt(S, "Classic", "Chrome"), -3.0, -2.27, 2.45, 3.0, -2.2, 2.5)
    box(opt(S, "Classic", "Chrome"), -1.8, -2.27, 2.3, -0.4, -2.2, 2.62)           # radio
    box(opt(S, "Wood", "Wood"), -3.1, -2.27, 2.3, 0.6, -2.18, 2.75)
    box(opt(S, "Wood", "Wood"), 2.45, -2.27, 2.3, 3.1, -2.18, 2.75)
    for i in range(6):
        box(opt(S, "Billet", "Chrome"), -3.0 + i * 0.6, -2.27, 2.28, -2.75 + i * 0.6, -2.18, 2.8, bev=0.02)
    box(opt(S, "Digital", "Neon"), -3.1, -2.27, 2.84, 3.1, -2.2, 2.88)
    box(opt(S, "Digital", "Gauge"), -2.6, -2.27, 2.35, -0.3, -2.21, 2.72)


def shifters():
    S = "Shifter"
    base = Vector((0.3, -1.4, 1.05))
    cyl(opt(S, "Column", "Chrome"), (1.3, -2.0, 2.6), (0.85, -1.9, 2.75), 0.03, seg=8)
    cyl(opt(S, "Column", "Chrome"), (0.85, -1.9, 2.75), (0.8, -1.9, 2.76), 0.06, seg=10)
    for v in ("Chain", "Crystal", "WoodKnob", "THandle"):
        cyl(opt(S, v, "Dark"), base, base + Vector((0, 0, 0.12)), 0.22, seg=16)        # boot
    k = opt(S, "Chain", "Chrome")
    for i in range(9):                                                                  # chain-link stick
        z = 1.15 + i * 0.12
        torus(k, (0.3, -1.4, z), (1, 0, 0) if i % 2 else (0, 1, 0), 0.05, 0.015, seg=10, seg2=4)
    cyl(k, (0.3, -1.4, 2.25), (0.3, -1.4, 2.4), 0.09, seg=12)
    cyl(opt(S, "Crystal", "Chrome"), base, base + Vector((0, 0, 1.0)), 0.03, seg=8)
    cyl(opt(S, "Crystal", "Glass"), base + Vector((0, 0, 1.0)), base + Vector((0, 0, 1.32)), 0.16, seg=16, bev=0.06)
    cyl(opt(S, "WoodKnob", "Chrome"), base, base + Vector((0, 0, 0.95)), 0.03, seg=8)
    cyl(opt(S, "WoodKnob", "Wood"), base + Vector((0, 0, 0.95)), base + Vector((0, 0, 1.2)), 0.13, seg=16, bev=0.05)
    k = opt(S, "THandle", "Chrome")
    cyl(k, base, base + Vector((0, 0, 0.9)), 0.03, seg=8)
    cyl(k, base + Vector((-0.25, 0, 0.95)), base + Vector((0.25, 0, 0.95)), 0.06, seg=10)


def extras():
    # fuzzy dice from the rear-view mirror
    k = opt("Dice", "On", "Fur")
    box(opt("Dice", "On", "Dark"), -0.02, -0.98, 4.05, 0.02, -0.94, 4.5)
    for (x, z) in ((-0.18, 3.85), (0.16, 3.75)):
        cube(k, Vector((x, -0.96, z)), (0.26, 0.26, 0.26), 0.06, rot=Matrix.Rotation(0.4 if x < 0 else -0.3, 3, "Z"))
    # car club plaque in the rear window (shows generic text the game draws on it)
    k = opt("Plaque", "Chain", "Chrome")
    for i in range(14):
        a = 2 * math.pi * i / 14
        x, z = math.cos(a) * 1.1, 3.35 + math.sin(a) * 0.4
        torus(k, (x, 4.6, z), (0, 1, 0), 0.07, 0.022, seg=8, seg2=4)
    box(opt("Plaque", "Chain", "Gauge"), -1.0, 4.62, 3.05, 1.0, 4.66, 3.65)
    # rear-view mirror (always there)
    box("Chrome", -0.4, -0.98, 4.38, 0.4, -0.9, 4.55, bev=0.02)


# ================================================================================================ wheels
def wheel_rims(ox):
    st = "LowriderWheel"
    c = Vector((ox, 0, 0))
    X = Vector((1, 0, 0))
    D = {}
    designs = ("Wire100", "Wire72", "Star", "Steelie", "Disc", "Turbine", "Split", "Mesh")
    for d in designs:
        revolve(wopt("Rim", d, "Rim"), c, [(0.7, -0.29), (0.66, -0.25), (0.66, 0.2), (0.7, 0.22), (0.75, 0.27), (0.7, 0.3), (0.6, 0.26), (0.55, 0.2)], style=st)
        cyl(wopt("Rim", d, "Dark"), c - X * 0.3, c - X * 0.26, 0.67, seg=40, style=st)
    # wire wheels (100 and 72 spokes, cross-laced)
    for d, rows, w in (("Wire100", [(40, 0.30, 0.16, 0.18, 0.56), (30, 0.12, 0.15, 0.02, 0.63), (30, -0.12, 0.15, -0.16, 0.64)], 0.026),
                       ("Wire72", [(36, 0.28, 0.16, 0.15, 0.58), (36, -0.1, 0.15, -0.14, 0.64)], 0.034)):
        ring(wopt("Rim", d, "Dish"), c + X * 0.18, X, 0.52, 0.62, 0.06, seg=48, style=st)
        for (n, hx, hr, rx, rr) in rows:
            for i in range(n):
                a = 2 * math.pi * i / n
                cross = 0.42 if i % 2 == 0 else -0.42
                beam(wopt("Rim", d, "Spokes"), c + Vector((hx, hr * math.cos(a), hr * math.sin(a))),
                     c + Vector((rx, rr * math.cos(a + cross), rr * math.sin(a + cross))), w, w, up=(1, 0, 0), style=st)
        cyl(wopt("Rim", d, "Spokes"), c - X * 0.15, c + X * 0.32, 0.17, seg=24, style=st)
    # Star: five flat spokes
    cyl(wopt("Rim", "Star", "Spokes"), c + X * 0.1, c + X * 0.24, 0.24, seg=24, style=st)
    for i in range(5):
        a = 2 * math.pi * i / 5
        beam(wopt("Rim", "Star", "Spokes"), c + Vector((0.2, 0.15 * math.cos(a), 0.15 * math.sin(a))),
             c + Vector((0.16, 0.62 * math.cos(a), 0.62 * math.sin(a))), 0.22, 0.08, up=(1, 0, 0), style=st)
    ring(wopt("Rim", "Star", "Dish"), c + X * 0.16, X, 0.58, 0.66, 0.05, seg=48, style=st)
    # Steelie: painted steel face with holes and a small chrome dog-dish cap
    revolve(wopt("Rim", "Steelie", "Dish"), c, [(0.66, 0.18), (0.5, 0.2), (0.4, 0.14), (0.25, 0.16), (0.0, 0.16)], style=st)
    for i in range(6):
        a = 2 * math.pi * i / 6
        cyl(wopt("Rim", "Steelie", "Dark"), c + Vector((0.17, 0.45 * math.cos(a), 0.45 * math.sin(a))),
            c + Vector((0.22, 0.45 * math.cos(a), 0.45 * math.sin(a))), 0.06, seg=10, style=st)
    revolve(wopt("Rim", "Steelie", "Spokes"), c, [(0.34, 0.16), (0.3, 0.26), (0.15, 0.31), (0.0, 0.32)], style=st)
    # Disc: smooth moon disc
    revolve(wopt("Rim", "Disc", "Spokes"), c, [(0.68, 0.24), (0.5, 0.3), (0.25, 0.34), (0.0, 0.35)], style=st)
    # Turbine: angled fan blades
    revolve(wopt("Rim", "Turbine", "Dish"), c, [(0.66, 0.16), (0.2, 0.18), (0.0, 0.18)], style=st)
    for i in range(12):
        a = 2 * math.pi * i / 12
        p0 = c + Vector((0.2, 0.22 * math.cos(a), 0.22 * math.sin(a)))
        p1 = c + Vector((0.22, 0.6 * math.cos(a + 0.3), 0.6 * math.sin(a + 0.3)))
        beam(wopt("Rim", "Turbine", "Spokes"), p0, p1, 0.06, 0.12, up=(1, 0, 0), style=st)
    cyl(wopt("Rim", "Turbine", "Spokes"), c + X * 0.18, c + X * 0.3, 0.22, seg=24, style=st)
    # Split: ten split spokes (pairs)
    cyl(wopt("Rim", "Split", "Spokes"), c + X * 0.12, c + X * 0.26, 0.22, seg=24, style=st)
    for i in range(10):
        a = 2 * math.pi * i / 10
        for off in (-0.07, 0.07):
            beam(wopt("Rim", "Split", "Spokes"), c + Vector((0.2, 0.18 * math.cos(a), 0.18 * math.sin(a))),
                 c + Vector((0.18, 0.62 * math.cos(a + off * 1.5), 0.62 * math.sin(a + off * 1.5))), 0.06, 0.06, up=(1, 0, 0), style=st)
    ring(wopt("Rim", "Split", "Dish"), c + X * 0.17, X, 0.58, 0.66, 0.05, seg=48, style=st)
    # Mesh: cross-hatched face
    ring(wopt("Rim", "Mesh", "Dish"), c + X * 0.17, X, 0.56, 0.66, 0.05, seg=48, style=st)
    for i in range(16):
        a = 2 * math.pi * i / 16
        for sgn in (-1, 1):
            beam(wopt("Rim", "Mesh", "Spokes"), c + Vector((0.2, 0.15 * math.cos(a), 0.15 * math.sin(a))),
                 c + Vector((0.18, 0.58 * math.cos(a + sgn * 0.8), 0.58 * math.sin(a + sgn * 0.8))), 0.035, 0.035, up=(1, 0, 0), style=st)
    cyl(wopt("Rim", "Mesh", "Spokes"), c + X * 0.12, c + X * 0.28, 0.17, seg=24, style=st)
    return designs


def wheel_knockoffs(ox):
    st = "LowriderWheel"
    c = Vector((ox, 0, 0))
    X = Vector((1, 0, 0))
    for v in ("Bar2", "Bar3", "Cap"):
        cyl(wopt("KO", v, "Hub"), c + X * 0.32, c + X * 0.44, 0.2, seg=24, style=st, r2=0.12)
    for s in (-1, 1):
        beam(wopt("KO", "Bar2", "Hub"), c + Vector((0.42, 0, 0)), c + Vector((0.48, s * 0.42, s * 0.05)), 0.07, 0.12, up=(1, 0, 0), style=st)
    for i in range(3):
        a = 2 * math.pi * i / 3 + 0.3
        beam(wopt("KO", "Bar3", "Hub"), c + Vector((0.42, 0, 0)), c + Vector((0.47, 0.36 * math.cos(a), 0.36 * math.sin(a))), 0.06, 0.1, up=(1, 0, 0), style=st)
    revolve(wopt("KO", "Cap", "Hub"), c, [(0.22, 0.4), (0.16, 0.48), (0.0, 0.52)], style=st)


def wheel_tyres(ox):
    st = "LowriderWheel"
    c = Vector((ox, 0, 0))
    # profiles: Classic, Balloon (fatter, rounder), Skinny (narrow, old-school)
    for (p, hw, sh) in (("Classic", 0.34, 0.2), ("Balloon", 0.4, 0.12), ("Skinny", 0.28, 0.22)):
        revolve(wopt("Tire", p, "Rubber"), c, [(0.7, -hw + 0.04), (0.98, -hw), (1.1, -hw + 0.03), (WR, -sh), (WR, sh), (1.1, hw - 0.03), (0.98, hw), (0.7, hw - 0.04), (0.7, -hw + 0.04)], style=st)
        x = hw + 0.003
        revolve(wopt("Band", p + "Thin", "Band"), c, [(0.86, x), (0.97, x + 0.005)], style=st)
        revolve(wopt("Band", p + "Wide", "Band"), c, [(0.76, x - 0.005), (1.03, x + 0.005)], style=st)
        revolve(wopt("Band", p + "Double", "Band"), c, [(0.8, x), (0.86, x + 0.003)], style=st)
        revolve(wopt("Band", p + "Double", "Band"), c, [(0.92, x + 0.004), (0.98, x + 0.006)], style=st)


def build_options():
    front_bumpers()
    rear_bumpers()
    grilles()
    hoods()
    spoilers()
    skirts()
    mirrors()
    ornaments()
    exhausts()
    visors()
    tops()
    underglow()
    continental()
    trunks()
    seat_bench("Rolls", "rolls")
    seat_bench("Diamond", "diamond")
    seat_bench("SplitBench", "split")
    seat_bench("Channel", "channel")
    seat_bench("Pillow", "pillow")
    headlights()
    taillights()
    side_trim()
    door_panels()
    headliner()
    audio()
    pedals()
    seat_buckets()
    steering()
    dashes()
    shifters()
    extras()


def build_wheel_options(ox):
    wheel_rims(ox)
    wheel_knockoffs(ox)
    wheel_tyres(ox)
