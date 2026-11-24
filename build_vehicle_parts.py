# Neon Coast vehicles: every swappable part, sized to the vehicle being built (exec'd by build_vehicles.py, which
# provides the spec globals W, L0, L1, ZB, BELT, NOSE, HOOD, TAIL, A0, A1, B, Q, C0, C1, ROOF, WX, WY_F, WY_R, WR, TW,
# REAR, BED, FLAV, DOORS and the helpers). Each variant is a set of pieces whose kind is registered with
# opt(slot, variant, mat); the game shows the variant the player picked and colours each piece by its mat (same mats
# as the lowrider: Chrome, Body, Dark, Glass, Head, Tail, Light, Seat, SeatTrim, Wood, Dash, Neon, Carpet).
# Variant ids reuse the lowrider's where they mean the same thing, so one tuning menu covers every vehicle.
TRUCKISH = FLAV in ("truck", "suv")
SMOOTH = S.get("smooth", False)                   # rounded modern nose / tail (see make_stations)
BZ0 = ZB + 0.05                                   # bumper zone
BZ1 = ZB + (0.75 if TRUCKISH else 0.55)
NOSE_FACE = L0 + 0.02
TAIL_FACE = L1 - 0.02
REAR_TOP = (TAIL if REAR in ("trunk", "hatch") else BELT) - 0.2
HX = W - 1.05                                      # headlight centre |x|
FLOOR = ZB + 0.3
SY = (A0 + B) / 2 + 0.9                            # front seat y
GAUGE = ((W * 0.42, A0 + 0.82, BELT - 0.28), 16.0)
STEER = (Vector((W * 0.42, A0 + 1.25, BELT - 0.2)), Vector((0, 1, 0.45)).normalized())   # the game turns the wheel on this


def kind(slot, variant, mat):
    return opt(slot, variant, mat)


# ================================================================================================ exterior
def front_bumpers():
    S = "FrontBumper"
    y0, y1 = L0 - 0.28, L0 + 0.35
    x = W - 0.3
    if SMOOTH:  # the rounded nose is narrower at the tip: the bumper follows it
        y0, y1, x = L0 - 0.12, L0 + 0.45, W * 0.88 - 0.2
    sbox(kind(S, "Stock", "Body"), -x, y0, BZ0, x, y1, BZ1, bev=0.12)
    sbox(kind(S, "Stock", "Dark"), -x + 0.6, y0 - 0.02, BZ0 + 0.08, x - 0.6, y0 + 0.1, BZ0 + 0.22)
    sbox(kind(S, "Sport", "Body"), -x, y0 - 0.05, BZ0 + 0.08, x, y1, BZ1, bev=0.14)
    sbox(kind(S, "Sport", "Dark"), -x - 0.05, y0 - 0.25, BZ0 - 0.02, x + 0.05, y0 + 0.4, BZ0 + 0.08)       # splitter
    for s in (-1, 1):
        sbox(kind(S, "Sport", "Dark"), s * (x - 0.9), y0 - 0.07, BZ0 + 0.2, s * (x - 0.25), y0 + 0.05, BZ1 - 0.15)
    sbox(kind(S, "Classic", "Chrome"), -x - 0.05, y0, BZ0 + 0.1, x + 0.05, y1 - 0.1, BZ1, bev=0.14)
    if TRUCKISH:
        k = kind(S, "Tube", "Chrome")
        sbox(kind(S, "Tube", "Body"), -x, y0 + 0.1, BZ0, x, y1, BZ1, bev=0.1)
        for z in (BZ1 + 0.15, BZ1 + 0.75):
            sbeam(k, (-(x - 0.6), y0 - 0.25, z), (x - 0.6, y0 - 0.25, z), 0.14, 0.14)
        for s in (-1, 1):
            sbeam(k, (s * (x - 0.9), y0 - 0.25, BZ0 + 0.2), (s * (x - 0.9), y0 - 0.25, BZ1 + 0.85), 0.14, 0.14)
            for z in (BZ0 + 0.3, BZ1 - 0.1):                                             # brackets back to the bumper
                sbeam(k, (s * (x - 0.9), y0 - 0.3, z), (s * (x - 0.9), y0 + 0.2, z), 0.12, 0.12)
        k = kind(S, "Bull", "Dark")
        sbox(k, -x - 0.1, y0 - 0.15, BZ0, x + 0.1, y1, BZ1 + 0.05, bev=0.06)
        for s in (-1, 1):
            sbeam(k, (s * 0.7, y0 - 0.3, BZ0 + 0.3), (s * 0.7, y0 - 0.3, BZ1 + 1.1), 0.18, 0.18)
            sbeam(k, (s * 0.7, y0 - 0.3, BZ1 + 1.1), (s * (x - 0.3), y0 + 0.2, BZ1 + 0.9), 0.16, 0.16)
        sbeam(k, (-0.7, y0 - 0.3, BZ1 + 1.1), (0.7, y0 - 0.3, BZ1 + 1.1), 0.18, 0.18)
        for s in (-1, 1):
            scyl(kind(S, "Bull", "Light"), (s * 0.35, y0 - 0.38, BZ1 + 0.7), (s * 0.35, y0 - 0.3, BZ1 + 0.7), 0.16, seg=14)


def rear_bumpers():
    S = "RearBumper"
    y0, y1 = L1 - 0.35, L1 + 0.28
    x = W - 0.3
    if SMOOTH:
        y0, y1, x = L1 - 0.45, L1 + 0.12, W * 0.9 - 0.25
    sbox(kind(S, "Stock", "Body"), -x, y0, BZ0, x, y1, BZ1, bev=0.12)
    sbox(kind(S, "Sport", "Body"), -x, y0, BZ0 + 0.1, x, y1, BZ1, bev=0.12)
    for i in range(7):                                                                    # diffuser fins
        xx = -1.5 + i * 0.5
        sbox(kind(S, "Sport", "Dark"), xx - 0.03, y0, BZ0 - 0.02, xx + 0.03, y1 + 0.05, BZ0 + 0.25)
    sbox(kind(S, "Sport", "Dark"), -1.7, y0, BZ0 - 0.04, 1.7, y1, BZ0 + 0.1)
    sbox(kind(S, "Classic", "Chrome"), -x - 0.05, y0 + 0.1, BZ0 + 0.1, x + 0.05, y1, BZ1, bev=0.14)
    if TRUCKISH:
        sbox(kind(S, "Tube", "Body"), -x, y0, BZ0, x, y1 - 0.1, BZ1, bev=0.1)
        sbox(kind(S, "Tube", "Chrome"), -x - 0.05, y1 - 0.15, BZ0 + 0.1, x + 0.05, y1 + 0.05, BZ1 - 0.05, bev=0.05)
        sbox(kind(S, "Tube", "Dark"), -0.25, y1, BZ0 + 0.15, 0.25, y1 + 0.35, BZ0 + 0.4)                          # hitch


def grilles():
    S = "Grille"
    gw = HX - 0.62
    z0, z1 = BZ1 + 0.06, NOSE - 0.25
    if FLAV == "sports":
        z0, z1 = BZ0 + 0.12, BZ1 - 0.08                                                   # low intake
    y = NOSE_FACE - 0.04 if FLAV != "sports" else L0 - 0.36       # the sports intake sits in the bumper face
    for v in ("Bars", "Mesh", "Billet", "Eggcrate"):
        sbox(kind(S, v, "Dark"), -gw, y, z0, gw, y + 0.06, z1)
        sbox(kind(S, v, "Chrome"), -gw - 0.07, y - 0.04, z1 - 0.06, gw + 0.07, y + 0.04, z1 + 0.02)    # surround top
        sbox(kind(S, v, "Chrome"), -gw - 0.07, y - 0.04, z0 - 0.02, gw + 0.07, y + 0.04, z0 + 0.06)
    n = int((z1 - z0) / 0.16)
    for i in range(1, n):
        z = z0 + i * (z1 - z0) / n
        sbox(kind(S, "Bars", "Chrome"), -gw, y - 0.06, z - 0.025, gw, y, z + 0.025)
    for i in range(int(gw * 2 / 0.3)):
        xx = -gw + 0.15 + i * 0.3
        sbox(kind(S, "Billet", "Chrome"), xx - 0.03, y - 0.06, z0, xx + 0.03, y, z1)
    span = z1 - z0
    for i in range(-12, 13):                                                                # diamond mesh
        if abs(i * 0.3) + span > gw:
            continue
        sbeam(kind(S, "Mesh", "Chrome"), (i * 0.3 - (z1 - z0), y - 0.03, z0), (i * 0.3, y - 0.03, z1), 0.03, 0.03, up=(0, -1, 0))
        sbeam(kind(S, "Mesh", "Chrome"), (i * 0.3 + (z1 - z0), y - 0.03, z0), (i * 0.3, y - 0.03, z1), 0.03, 0.03, up=(0, -1, 0))
    for i in range(int(gw * 2 / 0.45) + 1):
        xx = -gw + i * (2 * gw) / int(gw * 2 / 0.45)
        sbox(kind(S, "Eggcrate", "Chrome"), xx - 0.03, y - 0.08, z0, xx + 0.03, y, z1)
    for i in range(1, 3):
        z = z0 + i * (z1 - z0) / 3
        sbox(kind(S, "Eggcrate", "Chrome"), -gw, y - 0.08, z - 0.03, gw, y, z + 0.03)


def headlights():
    S = "Headlights"
    z0, z1 = BZ1 + 0.1, NOSE - 0.2
    zc = (z0 + z1) / 2
    y = NOSE_FACE
    for s in (-1, 1):
        x = s * HX
        sbox(kind(S, "Square", "Chrome"), x - 0.5, y - 0.05, zc - 0.28, x + 0.5, y + 0.08, zc + 0.28, bev=0.03)
        sbox(kind(S, "Square", "Head"), x - 0.44, y - 0.08, zc - 0.22, x + 0.44, y, zc + 0.22)
        for dx in (-0.25, 0.25):
            scyl(kind(S, "Dual", "Chrome"), (x + dx, y + 0.08, zc), (x + dx, y - 0.05, zc), 0.24, seg=20)
            scyl(kind(S, "Dual", "Head"), (x + dx, y - 0.05, zc), (x + dx, y - 0.09, zc), 0.19, seg=20)
        if SMOOTH:  # the reference's lamps: big swept units on the nose corners, cast from the front so they wrap
            yc = L0 - 2.0
            q = lambda pts, g=0.0: [(s * (a * W + g * (1 if a > 0.6 else -1)), yc, b + g * (1 if k in (0, 1) else -1)) for k, (a, b) in enumerate(pts)]
            # a swept teardrop: low pointed inner tip, the top edge curving up the fender to a rounded outer end
            def ztop(u):
                return 2.15 + 0.17 * min(1.0, u / 0.12) ** 0.5 + 0.56 * u ** 1.5 - 0.12 * max(0.0, (u - 0.88) / 0.12) ** 2
            def zbot(u):
                return 2.14 + 0.1 * u + 0.36 * max(0.0, (u - 0.7) / 0.3) ** 2
            xu = lambda u: 0.45 + 0.47 * u
            def strip(kd, f0, f1, g, out, inn, u0=0.0, u1=1.0, n=16):
                for k in range(n):
                    a, b = u0 + (u1 - u0) * k / n, u0 + (u1 - u0) * (k + 1) / n
                    xa, xb_ = s * (xu(a) * W - (g if k == 0 else 0)), s * (xu(b) * W + (g if k == n - 1 else 0))
                    decal(kd, (xa, yc, f1(a) + g), (xb_, yc, f1(b) + g), (xb_, yc, f0(b) - g), (xa, yc, f0(a) - g), (0, 1, 0),
                          nu=3, nv=3, out=out, inn=inn)
            strip(kind(S, "Slim", "Dark"), zbot, ztop, 0.05, 0.02, 0.06)                       # housing
            strip(kind(S, "Slim", "Chrome"), zbot, ztop, 0.0, 0.04, 0.02)                      # the lamp's reflector
            strip(kind(S, "Slim", "Head"), lambda u: ztop(u) - 0.075, lambda u: ztop(u) - 0.025, 0.0, 0.055, 0.0,
                  u0=0.04, u1=0.9)                                                             # LED strip (lights up)
        else:
            sbox(kind(S, "Slim", "Dark"), x - 0.55, y - 0.05, z1 - 0.3, x + 0.55, y + 0.08, z1 - 0.06, bev=0.03)
            sbox(kind(S, "Slim", "Head"), x - 0.5, y - 0.08, z1 - 0.2, x + 0.5, y, z1 - 0.12)
        for dx in (-0.25, 0.25):
            scyl(kind(S, "Quad", "Chrome"), (x + dx, y + 0.08, zc + 0.12), (x + dx, y - 0.05, zc + 0.12), 0.18, seg=16)
            scyl(kind(S, "Quad", "Head"), (x + dx, y - 0.05, zc + 0.12), (x + dx, y - 0.09, zc + 0.12), 0.14, seg=16)
        scyl(kind(S, "Quad", "Light"), (x, y + 0.02, zc - 0.25), (x, y - 0.06, zc - 0.25), 0.1, seg=12)


def taillights():
    S = "Taillights"
    y = TAIL_FACE
    corner = REAR in ("liftgate", "tailgate")
    if corner:                                                                              # tall corner lamps
        z0, z1 = BZ1 + 0.1, BELT - 0.15
        for s in (-1, 1):
            x = s * (W - 0.38)
            sbox(kind(S, "Bar", "Tail"), x - 0.15, y - 0.04, z0, x + 0.15, y + 0.08, z1)
            sbox(kind(S, "Twin", "Tail"), x - 0.15, y - 0.04, z1 - 0.7, x + 0.15, y + 0.08, z1)
            sbox(kind(S, "Twin", "Tail"), x - 0.15, y - 0.04, z0, x + 0.15, y + 0.08, z0 + 0.5)
            sbox(kind(S, "Twin", "Light"), x - 0.15, y - 0.04, z0 + 0.55, x + 0.15, y + 0.08, z1 - 0.75)
            for i in range(4):
                zz = z0 + 0.1 + i * (z1 - z0 - 0.2) / 3
                scyl(kind(S, "Stacked", "Tail"), (x, y - 0.04, zz), (x, y + 0.1, zz), 0.13, seg=14)
            sbox(kind(S, "Slim", "Dark"), x - 0.16, y - 0.03, z0, x + 0.16, y + 0.08, z1)
            sbox(kind(S, "Slim", "Tail"), x - 0.1, y + 0.08, z1 - 0.9, x + 0.1, y + 0.11, z1 - 0.1)
        sbox(kind(S, "Slim", "Tail"), -(W - 0.7), y + 0.06, BELT + 0.05, W - 0.7, y + 0.1, BELT + 0.12) if REAR == "liftgate" else None
        return
    z0, z1 = max(BZ1 + 0.08, REAR_TOP - 0.55), REAR_TOP - 0.05
    xo = (min(W, station_w(y - 0.1)) if SMOOTH else W) - 0.5      # a rounded tail is narrower at the rear face
    if SMOOTH and globals()["S"].get("TDROP"):
        # a tail that rolls down at the end: the add-on lamps sit on the face under the deck lip, set into the skin
        zt_ = TAIL - 0.45 - 0.1 * globals()["S"]["TDROP"]
        z0, z1 = zt_ - 0.5, zt_ + 0.05
        hits = []
        for xx in (0.0, xo * 0.5, xo):
            for zz in (z0, z1):
                loc_, _, _, _ = body_bvh().ray_cast(Vector((xx, L1 + 3, zz)), Vector((0, -1, 0)), 8.0)
                if loc_:
                    hits.append(loc_.y)
        if hits:
            y = min(hits) + 0.02
    zc = (z0 + z1) / 2
    sbox(kind(S, "Bar", "Tail"), -xo, y - 0.04, z0 + 0.08, xo, y + 0.08, z1 - 0.08)
    for s in (-1, 1):
        for dx in (0.0, 0.62):
            scyl(kind(S, "Twin", "Tail"), (s * (xo - 0.3 - dx), y - 0.04, zc), (s * (xo - 0.3 - dx), y + 0.08, zc), 0.22, seg=18)
        sbox(kind(S, "Stacked", "Tail"), s * (xo - 1.0), y - 0.04, zc + 0.02, s * xo, y + 0.08, z1 - 0.04)
        sbox(kind(S, "Stacked", "Light"), s * (xo - 1.0), y - 0.04, z0 + 0.04, s * xo, y + 0.08, zc - 0.02)
        if SMOOTH:  # the reference's lamps: wide units under the deck lip, cast from behind so they wrap the corners
            yb, zt = L1 + 1.5, TAIL - 0.45 - 0.1 * globals()["S"].get("TDROP", 0.0)
            TL = [(0.36, zt - 0.25), (0.895, zt - 0.36), (0.895, zt + 0.12), (0.36, zt + 0.04)]
            q = lambda g: [(s * (a * W + g * (0.4 if a > 0.6 else -1)), yb, b + g * (1 if k in (2, 3) else -1)) for k, (a, b) in enumerate(TL)]
            decal(kind(S, "Slim", "Dark"), *q(0.05), (0, -1, 0), nu=12, nv=3, out=0.02, inn=0.06)
            decal(kind(S, "Slim", "Tail"), *q(0.0), (0, -1, 0), nu=12, nv=3, out=0.04, inn=0.03)
            # bumper reflectors low on the corners
            R = [(0.62, ZB + 0.72), (0.86, ZB + 0.72), (0.86, ZB + 0.82), (0.62, ZB + 0.82)]
            decal(kind(S, "Slim", "Tail"), *[(s * a * W, yb, b) for a, b in R], (0, -1, 0), nu=6, nv=1, out=0.03, inn=0.02)
            if s == 1:                                 # plate recess on the hatch and a dark diffuser under the bumper
                if not globals()["S"].get("TDROP"):        # (the Vireo: no plate panel)
                  decal("Dark", (-0.78, yb, zt - 1.05), (0.78, yb, zt - 1.05), (0.78, yb, zt - 0.42), (-0.78, yb, zt - 0.42), (0, -1, 0),
                      nu=8, nv=3, out=0.012, inn=0.05)
                pass
            if s == 1:                                 # a chrome strip across the hatch between the lamps
                decal(kind(S, "Slim", "Chrome"), (-0.37 * W, yb, zt - 0.05), (0.37 * W, yb, zt - 0.05), (0.37 * W, yb, zt + 0.01),
                      (-0.37 * W, yb, zt + 0.01), (0, -1, 0), nu=16, nv=1, out=0.03, inn=0.02)
        else:
            sbox(kind(S, "Slim", "Dark"), s * (xo - 1.3), y - 0.03, zc - 0.12, s * xo, y + 0.08, zc + 0.12)
            sbox(kind(S, "Slim", "Tail"), s * (xo - 1.25), y + 0.08, zc - 0.05, s * (xo - 0.05), y + 0.11, zc + 0.05)


def hoods():
    S = "Hood"
    ym = (L0 + A0) / 2
    yl = A0 - L0
    z = lambda x, y: deck_z(x, y)
    if SMOOTH:
        # curved hood: each option is a skin grown off the hood itself (flat prisms float off or cut through it)
        def bump(k, x0, x1, y0, y1, h, nu=10, nv=12, sink=0.035):
            O, I = [], []
            for j in range(nv + 1):
                v = j / nv
                y = y0 + (y1 - y0) * v
                ro, ri = [], []
                for i in range(nu + 1):
                    u = i / nu
                    x = x0 + (x1 - x0) * u
                    zs = z(abs(x), y)
                    ro.append(Vector((x, y, zs + h(u, v))))
                    ri.append(Vector((x, y, zs - sink)))
                O.append(ro)
                I.append(ri)
            return solid_grid(k, O, I, [(j, i) for j in range(nv) for i in range(nu)], smooth=50.0)
        edge = lambda u: max(0.0, 1 - abs(2 * u - 1) ** 6)
        y0, y1 = ym - yl * 0.12, ym + yl * 0.2
        bump(kind(S, "Scoop", "Body"), -0.85, 0.85, y0, y1, lambda u, v: 0.02 + 0.4 * (1 - v) ** 1.3 * edge(u))
        sbox(kind(S, "Scoop", "Dark"), -0.62, y0 - 0.03, z(0, y0) + 0.04, 0.62, y0 + 0.03, z(0, y0) + 0.36)
        y0, y1 = ym - yl * 0.05, A0 - 0.15
        bump(kind(S, "Cowl", "Body"), -1.0, 1.0, y0, y1, lambda u, v: 0.02 + 0.28 * v ** 1.2 * edge(u))
        for s in (-1, 1):
            xc = s * W * 0.42
            bump(kind(S, "Vents", "Body"), xc - 0.65, xc + 0.65, ym - 0.75, ym + 0.75, lambda u, v: 0.025, nu=6, nv=6)
            for i in range(5):
                y = ym - 0.6 + i * 0.3
                bump(kind(S, "Vents", "Dark"), xc - 0.55, xc + 0.55, y - 0.05, y + 0.05, lambda u, v: 0.045, nu=6, nv=1)
        return
    # Scoop: a raised intake with a dark mouth
    y0, y1 = ym - yl * 0.12, ym + yl * 0.2
    sprism(kind(S, "Scoop", "Body"), [(-0.75, y0, z(0, y0) + 0.42), (0.75, y0, z(0, y0) + 0.42), (0.85, y1, z(0, y1) + 0.02), (-0.85, y1, z(0, y1) + 0.02)],
           [(-0.75, y0, z(0, y0) - 0.05), (0.75, y0, z(0, y0) - 0.05), (0.85, y1, z(0, y1) - 0.05), (-0.85, y1, z(0, y1) - 0.05)])
    sbox(kind(S, "Scoop", "Dark"), -0.65, y0 - 0.03, z(0, y0) + 0.05, 0.65, y0 + 0.05, z(0, y0) + 0.35)
    # Cowl: a long low bulge up to the windshield
    y0, y1 = ym - yl * 0.05, A0 - 0.15
    sprism(kind(S, "Cowl", "Body"), [(-0.9, y0, z(0, y0) + 0.02), (0.9, y0, z(0, y0) + 0.02), (1.0, y1, z(0, y1) + 0.3), (-1.0, y1, z(0, y1) + 0.3)],
           [(-0.9, y0, z(0, y0) - 0.05), (0.9, y0, z(0, y0) - 0.05), (1.0, y1, z(0, y1) - 0.05), (-1.0, y1, z(0, y1) - 0.05)])
    # Vents: two dark heat extractors
    for s in (-1, 1):
        xc = s * W * 0.42
        for i in range(5):
            y = ym - 0.6 + i * 0.3
            sbox(kind(S, "Vents", "Dark"), xc - 0.55, y - 0.05, z(xc, y) - 0.02, xc + 0.55, y + 0.05, z(xc, y) + 0.06)
        sbox(kind(S, "Vents", "Body"), xc - 0.65, ym - 0.75, z(xc, ym) - 0.02, xc + 0.65, ym + 0.75, z(xc, ym) + 0.02)


def spoilers():
    S = "Spoiler"
    if REAR == "tailgate":
        return
    if REAR == "liftgate":
        y0 = C0 + 0.25
        sbox(kind(S, "Roof", "Body"), -(gx(ROOF) - 0.05), y0, ROOF + 0.05, gx(ROOF) - 0.05, y0 + 0.55, ROOF + 0.18, bev=0.05)
        sbox(kind(S, "Roof", "Tail"), -0.5, y0 + 0.5, ROOF + 0.08, 0.5, y0 + 0.57, ROOF + 0.15)
        sbox(kind(S, "Wing", "Dark"), -(gx(ROOF) + 0.05), y0 + 0.1, ROOF + 0.25, gx(ROOF) + 0.05, y0 + 0.8, ROOF + 0.33)
        for s in (-1, 1):
            sbox(kind(S, "Wing", "Dark"), s * 1.2 - 0.05, y0, ROOF + 0.1, s * 1.2 + 0.05, y0 + 0.3, ROOF + 0.27)
        return
    ye = L1 - 0.6
    ze = deck_z(0, ye)
    xw = W - 0.7
    zs = ze                                          # upright foot
    if SMOOTH:                                       # a tucked tail: stay on the deck's top, feet sunk into its curve
        xw = min(xw, top_w(ye) + 0.15)
        zs = ze - 0.25
    sprism(kind(S, "Ducktail", "Body"), [(-xw, ye - 0.6, ze + 0.02), (xw, ye - 0.6, ze + 0.02), (xw, ye + 0.08, ze + 0.28), (-xw, ye + 0.08, ze + 0.28)],
           [(-xw, ye - 0.6, ze - 0.04), (xw, ye - 0.6, ze - 0.04), (xw, ye + 0.08, ze - 0.04), (-xw, ye + 0.08, ze - 0.04)])
    for v, h, depth, mat in (("Wing", 0.55, 0.7, "Body"), ("GT", 1.1, 1.0, "Dark")):
        for s in (-1, 1):
            sbox(kind(S, v, mat), s * (xw - 0.6) - 0.06, ye - 0.3, zs, s * (xw - 0.6) + 0.06, ye, ze + h)
        sbox(kind(S, v, mat), -xw - 0.1, ye - depth + 0.2, ze + h, xw + 0.1, ye + 0.2, ze + h + 0.1, bev=0.03)
        if v == "GT":
            for s in (-1, 1):
                sbox(kind(S, v, mat), s * (xw + 0.1) - 0.03, ye - depth + 0.1, ze + h - 0.2, s * (xw + 0.1) + 0.03, ye + 0.3, ze + h + 0.3)


def skirts():
    S = "Skirts"
    a0, a1 = WY_F + ARCH + 0.1, WY_R - ARCH - 0.1
    for s in (-1, 1):
        sbox(kind(S, "Rocker", "Body"), s * (W - 0.05), a0, ZB - 0.12, s * (W + 0.12), a1, ZB + 0.3, bev=0.05)
        if TRUCKISH:
            sbox(kind(S, "Steps", "Dark"), s * (W - 0.05), a0 + 0.1, ZB - 0.35, s * (W + 0.55), a1 - 0.1, ZB - 0.22, bev=0.03)
            for i in range(3):
                y = a0 + 0.6 + i * (a1 - a0 - 1.2) / 2
                sbox(kind(S, "Steps", "Chrome"), s * (W + 0.05), y - 0.4, ZB - 0.21, s * (W + 0.5), y + 0.4, ZB - 0.18)


def mirrors():
    S = "Mirrors"
    y = A0 + 0.55 if not OPEN else A0 + 0.12                    # open cart: on the cowl, ahead of the step-in
    z = BELT + 0.3
    if SMOOTH:                                   # a modern mirror: on the door glass's front corner, inside the body's width
        y, z = A0 + 0.75, BELT + 0.55
    for s in (-1, 1):
        x = s * (W + 0.05)
        if SMOOTH:
            x = s * (gh_xb(y) + 0.02)
            # the reference's shell: a teardrop swelling outboard, on a short thick foot from the door's front corner
            sbeam(kind(S, "Sport", "Body"), (s * (gh_xb(y) - 0.08), y + 0.1, BELT + 0.06), (x + s * 0.2, y + 0.04, z - 0.06), 0.16, 0.2)
            scyl(kind(S, "Sport", "Body"), (x + s * 0.03, y, z), (x + s * 0.12, y, z), 0.13, seg=20, r2=0.2)
            scyl(kind(S, "Sport", "Body"), (x + s * 0.12, y, z), (x + s * 0.44, y, z), 0.2, seg=20, r2=0.24)
            scyl(kind(S, "Sport", "Body"), (x + s * 0.44, y, z), (x + s * 0.6, y, z), 0.24, seg=20, r2=0.19)
            scyl(kind(S, "Sport", "Body"), (x + s * 0.6, y, z), (x + s * 0.66, y, z), 0.19, seg=20, r2=0.1)
            sbox(kind(S, "Sport", "Glass"), x + s * 0.18, y + 0.14, z - 0.13, x + s * 0.56, y + 0.245, z + 0.13)
            sbox(kind(S, "Rect", "Body"), x, y - 0.1, z - 0.2, x + s * 0.62, y + 0.14, z + 0.2, bev=0.06)
            sbox(kind(S, "Rect", "Glass"), x + s * 0.05, y + 0.14, z - 0.15, x + s * 0.57, y + 0.16, z + 0.15)
            continue
        sbeam(kind(S, "Rect", "Dark"), (s * (W - 0.1), y, BELT + 0.08), (x + s * 0.15, y, z), 0.12, 0.08)
        sbox(kind(S, "Rect", "Body"), x + s * 0.05, y - 0.08, z - 0.22, x + s * 0.65, y + 0.16, z + 0.22, bev=0.05)
        sbox(kind(S, "Rect", "Glass"), x + s * 0.1, y + 0.16, z - 0.17, x + s * 0.6, y + 0.18, z + 0.17)
        sbeam(kind(S, "Sport", "Body"), (s * (W - 0.1), y + 0.1, BELT + 0.08), (x + s * 0.2, y + 0.05, z), 0.06, 0.1)
        scyl(kind(S, "Sport", "Body"), (x + s * 0.35, y - 0.12, z), (x + s * 0.35, y + 0.12, z), 0.2, seg=16, r2=0.16)
        scyl(kind(S, "Sport", "Glass"), (x + s * 0.35, y + 0.12, z), (x + s * 0.35, y + 0.14, z), 0.16, seg=16)


def exhausts():
    S = "Exhaust"
    y = L1 + 0.25
    z = BZ0 + 0.18
    for s in (-1, 1):
        scyl(kind(S, "Dual", "Chrome"), (s * 1.2, y - 0.5, z), (s * 1.2, y, z), 0.14, seg=16)
        for dx in (0.95, 1.4):
            scyl(kind(S, "Quad", "Chrome"), (s * dx, y - 0.5, z), (s * dx, y, z), 0.12, seg=14)
        if not TRUCKISH:
            scyl(kind(S, "Side", "Chrome"), (s * (W + 0.15), WY_F + ARCH + 0.3, ZB + 0.08), (s * (W + 0.15), WY_R - ARCH - 0.3, ZB + 0.08), 0.12, seg=14)
        elif BED:
            scyl(kind(S, "Side", "Chrome"), (s * (W - 0.3), BED[0] + 0.25, BELT - 0.3), (s * (W - 0.3), BED[0] + 0.25, ROOF + 0.6), 0.14, seg=14)   # stacks


def tops():
    S = "Top"
    xt = gx(ROOF)
    yr0, yr1 = A1 + 0.2, C0 - 0.2
    if SMOOTH:  # glass panel / light bar following the curved roof
        ya, yb = yr0 + 0.25, yr0 + 0.35 + min(2.4, (yr1 - yr0) * 0.5)
        for mat, g, out in (("Dark", 0.03, 0.02), ("Glass", 0.0, 0.035)):
            xa = xt * 0.56 + g
            decal(kind(S, "Sunroof", mat), (-xa, ya - g, 9), (xa, ya - g, 9), (xa, yb + g, 9), (-xa, yb + g, 9), (0, 0, -1), nu=8, nv=8,
                  out=out, inn=0.0)
        zl = roof_z(xt - 0.2, A1 + 0.3)
        sbox(kind(S, "Lightbar", "Dark"), -(xt - 0.2), A1 + 0.05, zl, xt - 0.2, A1 + 0.3, zl + 0.26, bev=0.03)
        for i in range(6):
            x = -(xt - 0.5) + i * (2 * (xt - 0.5)) / 5
            sbox(kind(S, "Lightbar", "Light"), x - 0.18, A1 + 0.02, zl + 0.04, x + 0.18, A1 + 0.05, zl + 0.22)
        return
    sbox(kind(S, "Sunroof", "Glass"), -xt * 0.55, yr0 + 0.3, ROOF + 0.13, xt * 0.55, yr0 + 0.3 + min(2.4, (yr1 - yr0) * 0.5), ROOF + 0.16)
    sbox(kind(S, "Sunroof", "Dark"), -xt * 0.58, yr0 + 0.25, ROOF + 0.12, xt * 0.58, yr0 + 0.35 + min(2.4, (yr1 - yr0) * 0.5), ROOF + 0.14)
    if TRUCKISH:
        for s in (-1, 1):
            sbox(kind(S, "Rack", "Dark"), s * (xt - 0.15) - 0.06, yr0, ROOF + 0.14, s * (xt - 0.15) + 0.06, yr1, ROOF + 0.3)
        n = max(2, int((yr1 - yr0) / 1.2))
        for i in range(n + 1):
            y = yr0 + i * (yr1 - yr0) / n
            sbox(kind(S, "Rack", "Dark"), -(xt - 0.15), y - 0.05, ROOF + 0.3, xt - 0.15, y + 0.05, ROOF + 0.38)
    sbox(kind(S, "Lightbar", "Dark"), -(xt - 0.2), A1 + 0.05, ROOF + 0.16, xt - 0.2, A1 + 0.3, ROOF + 0.42, bev=0.03)
    for i in range(6):
        x = -(xt - 0.5) + i * (2 * (xt - 0.5)) / 5
        sbox(kind(S, "Lightbar", "Light"), x - 0.18, A1 + 0.02, ROOF + 0.2, x + 0.18, A1 + 0.05, ROOF + 0.38)


def underglow():
    for s in (-1, 1):
        sbox(kind("Glow", "On", "Neon"), s * (W - 0.6), WY_F, ZB - 0.05, s * (W - 0.5), WY_R, ZB)
    sbox(kind("Glow", "On", "Neon"), -(W - 0.8), L0 + 0.6, ZB - 0.05, W - 0.8, L0 + 0.7, ZB)
    sbox(kind("Glow", "On", "Neon"), -(W - 0.8), L1 - 0.7, ZB - 0.05, W - 0.8, L1 - 0.6, ZB)


def beds():
    if not BED:
        return
    S = "Bed"
    bf = ZB + 0.75
    y0, y1 = BED[0], L1 - 0.3
    sbox(kind(S, "Cover", "Dark"), -(W - 0.1), y0 - 0.05, BELT + 0.02, W - 0.1, y1 + 0.1, BELT + 0.1, bev=0.03)
    k = kind(S, "Rollbar", "Chrome")
    for s in (-1, 1):
        sbeam(k, (s * (W - 0.35), y0 + 0.4, BELT), (s * (W - 0.6), y0 + 0.4, ROOF - 0.2), 0.16, 0.16)
        sbeam(k, (s * (W - 0.6), y0 + 0.4, ROOF - 0.2), (s * (W - 0.35), y0 + 1.6, BELT), 0.14, 0.14)
        scyl(kind(S, "Rollbar", "Light"), (s * 0.8, y0 + 0.3, ROOF - 0.05), (s * 0.8, y0 + 0.2, ROOF - 0.05), 0.18, seg=14)
    sbeam(k, (-(W - 0.6), y0 + 0.4, ROOF - 0.2), (W - 0.6, y0 + 0.4, ROOF - 0.2), 0.16, 0.16)
    k = kind(S, "Rack", "Dark")
    for s in (-1, 1):
        for y in (y0 + 0.3, y1 - 0.3):
            sbox(k, s * (W - 0.3) - 0.07, y - 0.07, BELT, s * (W - 0.3) + 0.07, y + 0.07, ROOF + 0.2)
        sbox(k, s * (W - 0.3) - 0.07, y0 + 0.3, ROOF + 0.15, s * (W - 0.3) + 0.07, y1 - 0.3, ROOF + 0.25)
    for y in (y0 + 0.3, (y0 + y1) / 2, y1 - 0.3):
        sbox(k, -(W - 0.3), y - 0.07, ROOF + 0.15, W - 0.3, y + 0.07, ROOF + 0.25)


# ================================================================================================ interior
def seats():
    S = "Seats"
    rear = S_REAR_Y()
    FLOOR = globals()["FLOOR"] + (SEATH - 0.55)       # low-slung cars: the whole seat sits lower
    for v in ("Buckets", "Racing", "Rolls", "Diamond"):
        mat = "Seat"
        for s in (-1, 1):
            x = s * W * 0.42
            w = 0.62 if v in ("Buckets", "Racing") else W * 0.42 + 0.5
            xc = x if v in ("Buckets", "Racing") else s * (W * 0.42 + 0.5) / 2
            if v in ("Rolls", "Diamond") and s < 0:
                continue
            xc = xc if v in ("Buckets", "Racing") else 0.0
            w = w if v in ("Buckets", "Racing") else W - 0.6
            sbox(kind(S, v, mat), xc - w, SY - 0.6, FLOOR + 0.1, xc + w, SY + 0.55, FLOOR + 0.55, bev=0.1)              # cushion
            sbox(kind(S, v, mat), xc - w, SY + 0.45, FLOOR + 0.5, xc + w, SY + 0.75, FLOOR + 1.75, bev=0.1)              # back
            if v == "Racing":
                sbox(kind(S, v, "SeatTrim"), xc - w - 0.08, SY - 0.5, FLOOR + 0.5, xc - w + 0.06, SY + 0.7, FLOOR + 1.3)  # bolsters
                sbox(kind(S, v, "SeatTrim"), xc + w - 0.06, SY - 0.5, FLOOR + 0.5, xc + w + 0.08, SY + 0.7, FLOOR + 1.3)
                sbox(kind(S, v, "SeatTrim"), xc - 0.18, SY + 0.43, FLOOR + 1.3, xc + 0.18, SY + 0.47, FLOOR + 1.7)
            if v == "Buckets":
                sbox(kind(S, v, mat), xc - 0.35, SY + 0.5, FLOOR + 1.8, xc + 0.35, SY + 0.7, FLOOR + 2.15, bev=0.06)    # headrest
            for k in range(5 if v != "Diamond" else 0):
                z = FLOOR + 0.7 + k * 0.2
                sbox(kind(S, v, "SeatTrim"), xc - w + 0.06, SY + 0.43, z, xc + w - 0.06, SY + 0.46, z + 0.04)
            if v == "Diamond":
                for i in range(int(w * 2 / 0.35)):
                    for j in range(4):
                        xx = xc - w + 0.2 + i * 0.35 + (0.17 if j % 2 else 0)
                        scyl(kind(S, v, "SeatTrim"), (xx, SY + 0.42, FLOOR + 0.8 + j * 0.25), (xx, SY + 0.46, FLOOR + 0.8 + j * 0.25), 0.04, seg=6)
        if rear:
            sbox(kind(S, v, mat), -(W - 0.6), rear - 0.55, FLOOR + 0.1, W - 0.6, rear + 0.45, FLOOR + 0.55, bev=0.1)
            sbox(kind(S, v, mat), -(W - 0.6), rear + 0.4, FLOOR + 0.5, W - 0.6, rear + 0.7, FLOOR + 1.65, bev=0.1)
            for k in range(5 if v != "Diamond" else 0):
                z = FLOOR + 0.7 + k * 0.18
                sbox(kind(S, v, "SeatTrim"), -(W - 0.7), rear + 0.38, z, W - 0.7, rear + 0.41, z + 0.04)
    F0 = globals()["FLOOR"]
    sbox(kind(S, "Buckets", "Dash"), -0.35, SY - 1.2, F0, 0.35, SY + 0.4, F0 + 0.6, bev=0.05)                      # console
    sbox(kind(S, "Racing", "Dash"), -0.35, SY - 1.2, F0, 0.35, SY + 0.4, F0 + 0.6, bev=0.05)


def S_REAR_Y():
    if OPEN:                                              # cart: a second bench behind the first
        return SY + 2.0
    if Q:
        return (B + Q) / 2 + 0.55
    if FLAV == "muscle":
        return SY + 2.5
    return None


def door_cards():
    S = "Doors"
    for (nm, s, y0, y1) in DOORS:
        xi = s * (W - 0.55)
        z0, z1 = FLOOR + 0.15, BELT - 0.08
        for v in ("Smooth", "Rolls", "Diamond", "Channel"):
            sbox(kind(S, v, "Seat"), xi - 0.1, y0 + 0.12, z0, xi + 0.1, y1 - 0.12, z1)
        xf = xi - s * 0.11
        sbox(kind(S, "Smooth", "Chrome"), xf - 0.02, y0 + 0.2, z1 - 0.35, xf + 0.02, y1 - 0.2, z1 - 0.3)
        sbox(kind(S, "Smooth", "SeatTrim"), xf - s * 0.15, (y0 + y1) / 2 - 0.5, z0 + 0.6, xf + s * 0.02, (y0 + y1) / 2 + 0.5, z0 + 0.78, bev=0.04)
        for k in range(5):
            z = z0 + 0.25 + k * (z1 - z0 - 0.5) / 4
            sbox(kind(S, "Rolls", "SeatTrim"), xf - 0.02, y0 + 0.25, z, xf + 0.02, y1 - 0.25, z + 0.05)
        nyb = int((y1 - y0 - 0.5) / 0.5)
        for i in range(nyb):
            for j in range(3):
                y = y0 + 0.4 + i * 0.5 + (0.25 if j % 2 else 0)
                scyl(kind(S, "Diamond", "SeatTrim"), (xf + s * 0.01, y, z0 + 0.35 + j * 0.3), (xf - s * 0.02, y, z0 + 0.35 + j * 0.3), 0.04, seg=6)
        for i in range(int((y1 - y0 - 0.4) / 0.55)):
            y = y0 + 0.3 + i * 0.55
            sbox(kind(S, "Channel", "SeatTrim"), xf - 0.02, y, z0 + 0.15, xf + 0.02, y + 0.05, z1 - 0.15)


def dashes():
    S = "Dash"
    y0, y1 = A0 + 0.12, A0 + 0.85
    x = W - 0.5
    z1 = BELT + 0.05
    if SMOOTH:  # the curved canopy comes in at the cowl: keep the dash corners inside it
        x, z1 = W - 0.68, BELT - 0.02
    z0 = z1 - 0.6
    for v in ("Classic", "Digital", "Wood", "Billet"):
        sbox(kind(S, v, "Dash"), -x, y0, z0, x, y1, z1, bev=0.08)
        sbox(kind(S, v, "Dash"), -0.45, y1 - 0.1, FLOOR, 0.45, y1 + 0.3, z0 + 0.1)                  # centre stack
    sbox(kind(S, "Classic", "Chrome"), -x + 0.1, y1, z0 + 0.2, x - 0.1, y1 + 0.03, z0 + 0.26)
    sbox(kind(S, "Digital", "Neon"), -x + 0.3, y1 + 0.005, z0 + 0.3, x - 0.3, y1 + 0.02, z0 + 0.36)
    sbox(kind(S, "Digital", "Gauge"), -0.4, y1 + 0.3, z0 - 0.4, 0.4, y1 + 0.32, z0 + 0.05)
    sbox(kind(S, "Wood", "Wood"), -x + 0.1, y1, z0 + 0.12, x - 0.1, y1 + 0.03, z0 + 0.38)
    for i in range(int(2 * x / 0.25)):
        xx = -x + 0.15 + i * 0.25
        sbox(kind(S, "Billet", "Chrome"), xx - 0.03, y1, z0 + 0.1, xx + 0.03, y1 + 0.03, z0 + 0.45)


def steering():
    S = "Steering"
    p, ax = STEER                                       # wheel centre + axis toward the driver (rear and up)
    col0 = p - ax * 0.55                                # column on the same axis, so the wheel can turn on it
    for v in ("Sport", "Wood", "Chain"):
        scyl(kind(S, v, "Dash"), col0, p - ax * 0.05, 0.06, seg=10)
    torus(kind(S, "Sport", "Dash"), p, ax, 0.42, 0.05, seg=28, seg2=8, style=PREFIX)
    torus(kind(S, "Wood", "Wood"), p, ax, 0.44, 0.055, seg=28, seg2=8, style=PREFIX)
    torus(kind(S, "Chain", "Chrome"), p, ax, 0.36, 0.045, seg=24, seg2=6, style=PREFIX)
    for i in range(16):
        a = 2 * math.pi * i / 16
        q = p + axis_rot(ax) @ Vector((0.36 * math.cos(a), 0.36 * math.sin(a), 0))
        torus(kind(S, "Chain", "Chrome"), q, axis_rot(ax) @ Vector((-math.sin(a), math.cos(a), 0)), 0.06, 0.015, seg=8, seg2=4, style=PREFIX)
    for v, mat, r in (("Sport", "Dash", 0.42), ("Wood", "Chrome", 0.44), ("Chain", "Chrome", 0.36)):
        for i in range(3):
            a = 2 * math.pi * i / 3 - math.pi / 2
            q = p + axis_rot(ax) @ Vector((r * math.cos(a), r * math.sin(a), 0))
            sbeam(kind(S, v, mat), p, q, 0.06, 0.03, up=tuple(ax))


def shifters():
    S = "Shifter"
    p = Vector((0, SY - 0.9, FLOOR + 0.6))
    for v, mat in (("THandle", "Chrome"), ("WoodKnob", "Wood"), ("Crystal", "Neon"), ("Chain", "Chrome")):
        scyl(kind(S, v, "Chrome"), p, p + Vector((0, 0, 0.5)), 0.03, seg=8)
        # boot + base down to the floor (bench seats have no console under the shifter)
        sbox(kind(S, v, "Dark"), -0.14, p.y - 0.16, FLOOR - 0.02, 0.14, p.y + 0.16, p.z + 0.04, bev=0.03)
    sbeam(kind(S, "THandle", "Dark"), p + Vector((-0.18, 0, 0.52)), p + Vector((0.18, 0, 0.52)), 0.07, 0.07)
    scyl(kind(S, "WoodKnob", "Wood"), p + Vector((0, 0, 0.45)), p + Vector((0, 0, 0.62)), 0.09, seg=14)
    cube(kind(S, "Crystal", "Neon"), p + Vector((0, 0, 0.58)), (0.16, 0.16, 0.16), 0.03, PREFIX)
    for i in range(5):
        torus(kind(S, "Chain", "Chrome"), p + Vector((0, 0, 0.12 + i * 0.09)), (1, 0, 0) if i % 2 else (0, 1, 0), 0.05, 0.015, seg=8, seg2=4, style=PREFIX)


def headliner():
    S = "Headliner"
    if SMOOTH:  # follows the curved roof
        y0, y1 = A1 + 0.2, C0 - 0.2
        xt = min(gh_xb(y0), gh_xb(y1)) * 0.7

        def skin(xa, xb_, off, t, nx=16, ny=14):
            O = [[Vector((xa + (xb_ - xa) * i / nx, y0 + (y1 - y0) * j / ny, 0)) for i in range(nx + 1)] for j in range(ny + 1)]
            for row in O:
                for v in row:
                    v.z = roof_z(v.x, v.y) - off
            return O, [[v - Vector((0, 0, t)) for v in row] for row in O], [(j, i) for j in range(ny) for i in range(nx)]
        O, I, cells = skin(-xt, xt, 0.13, 0.04)
        for v in ("Plain", "Pleated", "Stars"):
            solid_grid(kind(S, v, "Seat"), O, I, cells)
        for i in range(int(2 * xt / 0.45)):
            x = -xt + 0.2 + i * 0.45
            O, I, cells = skin(x - 0.03, x + 0.03, 0.17, 0.03, nx=1)
            solid_grid(kind(S, "Pleated", "SeatTrim"), O, I, cells)
        import random as _r
        rnd = _r.Random(7)
        for i in range(70):
            x, y = rnd.uniform(-xt + 0.1, xt - 0.1), rnd.uniform(y0 + 0.1, y1 - 0.1)
            cube(kind(S, "Stars", "Neon"), Vector((x, y, roof_z(x, y) - 0.18)), (0.035, 0.035, 0.02), 0, PREFIX)
        return
    xt = gx(ROOF) - 0.1
    z = ROOF - 0.05
    y0, y1 = A1 + 0.1, C0 - 0.1
    for v in ("Plain", "Pleated", "Stars"):
        sbox(kind(S, v, "Seat"), -xt, y0, z - 0.04, xt, y1, z)
    for i in range(int(2 * xt / 0.45)):
        x = -xt + 0.2 + i * 0.45
        sbox(kind(S, "Pleated", "SeatTrim"), x - 0.03, y0 + 0.1, z - 0.07, x + 0.03, y1 - 0.1, z - 0.04)
    import random as _r
    rnd = _r.Random(7)
    for i in range(70):
        cube(kind(S, "Stars", "Neon"), Vector((rnd.uniform(-xt + 0.1, xt - 0.1), rnd.uniform(y0 + 0.1, y1 - 0.1), z - 0.05)), (0.035, 0.035, 0.02), 0, PREFIX)


def build_parts():
    front_bumpers()
    rear_bumpers()
    grilles()
    headlights()
    taillights()
    hoods()
    spoilers()
    skirts()
    mirrors()
    exhausts()
    tops()
    underglow()
    beds()
    seats()
    door_cards()
    dashes()
    steering()
    shifters()
    headliner()


# ================================================================================================ wheels
def build_wheels(ox):
    """the lowrider's rims / knock-offs / tyres (built at its size in their own namespace) + off-road tyres,
    then everything scaled to this vehicle's wheel"""
    ns = dict(globals())
    exec(compile(open(os.path.join(HERE, "build_lowrider_parts.py")).read(), "build_lowrider_parts.py", "exec"), ns)
    ns["RIM_TWIN"] = S.get("RIM_TWIN")
    ns["WR"] = 1.17
    ns["wheel_rims"](ox)
    ns["wheel_knockoffs"](ox)
    ns["wheel_tyres"](ox)
    WHEEL_INFO.update(ns["WHEEL_INFO"])
    st = "LowriderWheel"
    c = Vector((ox, 0, 0))
    k = ns["wopt"]("Tire", "Offroad", "Rubber")
    WHEEL_INFO[k] = ns["WHEEL_INFO"][k]
    hw = 0.4
    revolve(k, c, [(0.7, -hw + 0.04), (0.95, -hw), (1.08, -hw + 0.02), (1.12, -0.3), (1.12, 0.3), (1.08, hw - 0.02), (0.95, hw), (0.7, hw - 0.04), (0.7, -hw + 0.04)], style=st)
    for i in range(28):
        a = 2 * math.pi * i / 28
        for side in (-1, 1):
            off = 0.05 if (i % 2) else 0.0
            p0 = c + Vector((side * (0.17 + off), 1.145 * math.cos(a), 1.145 * math.sin(a)))
            cube(k, p0, (0.24, 0.2, 0.07), 0.0, st, rot=Matrix.Rotation(a - math.pi / 2, 3, "X"))
            cube(k, c + Vector((side * 0.36, 1.06 * math.cos(a + 0.1), 1.06 * math.sin(a + 0.1))), (0.06, 0.16, 0.14), 0.0, st,
                 rot=Matrix.Rotation(a + 0.1 - math.pi / 2, 3, "X"))
    sr, sw = WR / 1.17, TW / 0.68
    m = Matrix.Translation(c) @ Matrix.Diagonal((sw, sr, sr, 1)) @ Matrix.Translation(-c)
    for ob in list(OBJS):
        if ob.get("style") == st:
            bake(ob)
            ob.data.transform(m)
    # low-profile tyres (a spec's lowpro = how much sidewall is left, e.g. 0.5): the tyre wall shrinks toward the
    # tread and the rims grow to meet it, so the wheel looks like a big modern rim on a thin tyre
    lp = S.get("lowpro")
    if lp:
        rho_in = 0.70 * sr
        f = (WR - (WR - rho_in) * lp) / rho_in
        for ob in list(OBJS):
            if ob.get("style") != st:
                continue
            slot = WHEEL_INFO.get(ob["kind"], {}).get("slot")
            spokes = WHEEL_INFO.get(ob["kind"], {}).get("mat") == "Spokes"
            if slot not in ("Rim", "Tire", "Band"):
                continue
            for v in ob.data.vertices:
                y, z = v.co.y - c.y, v.co.z - c.z
                r = math.hypot(y, z)
                if r < 1e-6:
                    continue
                if slot == "Rim":
                    rb = WR - (WR - rho_in) * lp                         # the tyre bead: nothing pokes through it
                    r2 = min(r * f, rb * (0.93 if spokes else 1.0) - 0.005)  # spokes end inside the barrel
                elif r < WR:
                    r2 = WR - (WR - r) * lp
                else:
                    continue
                v.co.y, v.co.z = c.y + y * r2 / r, c.z + z * r2 / r


# ================================================================================================ previews
BASE_BUILD = {
    "muscle": {"FrontBumper": "Classic", "RearBumper": "Classic", "Grille": "Bars", "Headlights": "Dual", "Taillights": "Bar", "Mirrors": "Rect",
               "Seats": "Buckets", "Doors": "Smooth", "Dash": "Classic", "Steering": "Wood", "Shifter": "THandle", "Headliner": "Plain",
               "Rim": "Steelie", "KO": "Cap", "Tire": "Classic", "Hood": "Scoop", "Exhaust": "Dual"},
    "sports": {"FrontBumper": "Sport", "RearBumper": "Sport", "Grille": "Mesh", "Headlights": "Slim", "Taillights": "Slim", "Mirrors": "Sport",
               "Seats": "Racing", "Doors": "Smooth", "Dash": "Digital", "Steering": "Sport", "Shifter": "THandle", "Headliner": "Plain",
               "Rim": "Split", "KO": "Cap", "Tire": "Classic", "Exhaust": "Quad", "Spoiler": "Ducktail"},
    "truck": {"FrontBumper": "Classic", "RearBumper": "Classic", "Grille": "Billet", "Headlights": "Square", "Taillights": "Bar", "Mirrors": "Rect",
              "Seats": "Buckets", "Doors": "Smooth", "Dash": "Classic", "Steering": "Sport", "Shifter": "THandle", "Headliner": "Plain",
              "Rim": "Star", "KO": "Cap", "Tire": "Offroad", "Skirts": "Steps"},
    "suv": {"FrontBumper": "Stock", "RearBumper": "Stock", "Grille": "Eggcrate", "Headlights": "Square", "Taillights": "Bar", "Mirrors": "Rect",
            "Seats": "Buckets", "Doors": "Smooth", "Dash": "Classic", "Steering": "Sport", "Shifter": "THandle", "Headliner": "Plain",
            "Rim": "Steelie", "KO": "Cap", "Tire": "Offroad", "Top": "Rack"},
}[FLAV]
BASE_BUILD = dict(BASE_BUILD, **S.get("stock", {}))   # a vehicle can change its own stock parts
SHOWCASE = {
    "muscle": [("build_street", {"FrontBumper": "Sport", "RearBumper": "Sport", "Hood": "Cowl", "Spoiler": "Wing", "Rim": "Star", "Exhaust": "Side", "Skirts": "Rocker"}, "stripes", (0.05, 0.05, 0.06)),
               ("build_show", {"Grille": "Billet", "Rim": "Wire100", "KO": "Bar2", "Band": "ClassicThin", "Hood": "", "Glow": "On"}, "flames", (0.55, 0.03, 0.08))],
    "sports": [("build_track", {"Spoiler": "GT", "Hood": "Vents", "Rim": "Mesh", "Skirts": "Rocker", "Top": "Sunroof"}, "checker", (0.95, 0.95, 0.95)),
               ("build_night", {"Spoiler": "Wing", "Grille": "Bars", "Headlights": "Quad", "Rim": "Turbine", "Glow": "On"}, "lightning", (0.06, 0.02, 0.15))],
    "truck": [("build_offroad", {"FrontBumper": "Bull", "RearBumper": "Tube", "Top": "Lightbar", "Bed": "Rollbar", "Rim": "Steelie"}, "tropical", (0.85, 0.85, 0.82)),
              ("build_street", {"FrontBumper": "Stock", "RearBumper": "Stock", "Tire": "Classic", "Rim": "Split", "Bed": "Cover", "Skirts": "Rocker", "Exhaust": "Dual"}, "sunset_fade", (0.05, 0.05, 0.06))],
    "suv": [("build_trail", {"FrontBumper": "Bull", "RearBumper": "Tube", "Top": "Lightbar", "Skirts": "Steps", "Rim": "Star"}, "retro_waves", (0.9, 0.6, 0.15)),
            ("build_city", {"FrontBumper": "Sport", "RearBumper": "Sport", "Tire": "Classic", "Rim": "Mesh", "Spoiler": "Roof", "Top": "Sunroof", "Headlights": "Slim"}, "scallops", (0.05, 0.05, 0.06))],
}[FLAV]
