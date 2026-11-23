"""compose.py: builds the Neon Coast tattoo library (original, PG designs) as transparent PNG canvases + catalog json.
python compose.py [outdir] [id-filter]
Arm/leg/hand items get an L and R texture (positions mirrored so the front of the piece faces forward on both sides;
lettering is never mirrored). Every canvas keeps a transparent border because the game clamps UVs to the edge."""
import sys, json, os, math
sys.path.insert(0, "/tmp/claude-0/ink")
import numpy as np
from PIL import Image
from inkcore import *
from motifs import *
from motifs2 import *

OUT = sys.argv[1] if len(sys.argv) > 1 else "/tmp/claude-0/ink/lib"
FILT = sys.argv[2].split(",") if len(sys.argv) > 2 else None
os.makedirs(OUT, exist_ok=True)
os.makedirs(OUT + "/svg", exist_ok=True)

CANV = {"Arm": (768, 1024, 1.0), "Leg": (640, 1024, 0.65), "Hand": (512, 1024, 2.4), "Neck": (1024, 384, 1.25), "Face": (768, 1024, 2.1)}
# safe word list: every word on any tattoo comes from here
WORDS = ["Familia", "Lealtad", "Respeto", "Bendecido", "Fe", "Amor", "Mama", "Papa", "Vida", "Loyalty", "Blessed",
         "Faith", "Respect", "Family", "Hope", "Love", "Sueños", "Costa", "Smile Now", "Cry Later", "Esperanza", "Corazón"]
BL = "UnifrakturMaguntia"   # old english
SC = "MrDafoe"             # script


class Ctx:
    def __init__(self, canvas, side):
        self.W, self.H, _ = CANV[canvas]
        self.side = side
        self.canvas = canvas
        self.ms = []

    def X(self, x):
        return x if self.side != "R" else self.W - x

    def put(self, m, x, y, size=None, rot=0.0, mirror=True, s=None):
        """place motif centred at (x, y) (left-side coordinates) with its larger dimension = size px"""
        g = m.sil()
        if s is None:
            b = g.bounds
            s = size / max(b[2] - b[0], b[3] - b[1])
            cx, cy = (b[0] + b[2]) / 2, (b[1] + b[3]) / 2
        else:
            cx = cy = 0
        fl = self.side == "R" and mirror
        r = -rot if self.side == "R" else rot
        if self.canvas == "Hand":   # the hand canvas shows flipped top-to-bottom on a hanging hand: pre-flip each piece
            r += 180
            fl = not fl
        # centre the motif's bbox on the target point
        ox, oy = -cx * s * (-1 if fl else 1), -cy * s
        ca, sa = math.cos(math.radians(r)), math.sin(math.radians(r))
        px, py = ox * ca - oy * sa, ox * sa + oy * ca
        self.ms.append(m.place(self.X(x) + px, y + py, s, r, fl))
        return self

    def raw(self, m):
        self.ms.append(m)
        return self


# ------------------------------------------------------------------ sleeve filler
def smoke_bg(c, rng, y0, y1, op=0.42, x0=24, x1=None):
    x1 = x1 or c.W - 24
    m = Motif()
    g = box(x0, y0, x1, y1)
    sm = smoke_fill(rng, g, m.defs, op=op, sd=30, blobs=int((x1 - x0) * (y1 - y0) / 7000))
    # soft top/bottom edges so the shading never ends on a hard line
    lid, mid = uid("l"), uid("m")
    f = min(70, (y1 - y0) * 0.2) / (y1 - y0)
    m.defs.append(f'<linearGradient id="{lid}" gradientUnits="userSpaceOnUse" x1="0" y1="{y0}" x2="0" y2="{y1}">'
                  f'<stop offset="0" stop-color="#000"/><stop offset="{f:.3f}" stop-color="#fff"/>'
                  f'<stop offset="{1 - f:.3f}" stop-color="#fff"/><stop offset="1" stop-color="#000"/></linearGradient>'
                  f'<mask id="{mid}" maskUnits="userSpaceOnUse" x="-5000" y="-5000" width="10000" height="10000">'
                  f'<rect x="-5000" y="-5000" width="10000" height="10000" fill="url(#{lid})"/></mask>')
    m.add(f'<g mask="url(#{mid})">{sm}</g>', None)
    c.raw(m)


def clouds(c, rng, spots, w=330):
    for (x, y, ww) in spots:
        c.put(cloud(rng, w=700, h=250), x, y, ww or w, rot=rng.uniform(-8, 8))


def sky_rays(c, rng, x, y, R=420, op=0.3, start=-90, spread=140):
    m = rays(rng, n=9, R=R, spread=spread, op=op, center=(c.X(x), y), start=start if c.side != "R" else 180 - start)
    c.raw(m)


def stars_scatter(c, rng, box_, n=6, R=(10, 22), nautical=False):
    x0, y0, x1, y1 = box_
    for _ in range(n):
        c.put(sparkle(rng, R=100) if rng.random() < 0.6 else star(rng, R=100, nautical=nautical), rng.uniform(x0, x1), rng.uniform(y0, y1), rng.uniform(*R) * 2)


# ------------------------------------------------------------------ the library
ITEMS = []


def item(id_, name, area, zone, colour, tags=()):
    def deco(fn):
        ITEMS.append(dict(id=id_, name=name, area=area, zone=zone, colour=colour, tags=list(tags), fn=fn))
        return fn
    return deco


C = True  # colour flag shorthand

# ======================= FULL SLEEVES (shoulder to wrist) =======================
@item("sl_rosas_nubes", "Rosas y Nubes", "Arm", "full", False, ["chicano", "sleeve"])
def _(c, rng):
    smoke_bg(c, rng, 30, 990)
    sky_rays(c, rng, 384, 470, R=520, op=0.28)
    clouds(c, rng, [(160, 120, 320), (600, 140, 300), (150, 520, 300), (620, 600, 300), (260, 950, 340), (560, 960, 300)])
    c.put(rose_with_leaves(rng, leaves=2), 330, 250, 330, rot=-10)
    c.put(rose(rng), 450, 470, 170, rot=20)
    c.put(rose_with_leaves(rng, leaves=2), 370, 740, 300, rot=15)
    stars_scatter(c, rng, (520, 330, 700, 450), 3)


@item("sl_reloj_rosa", "Reloj y Rosa", "Arm", "full", False, ["chicano", "sleeve"])
def _(c, rng):
    smoke_bg(c, rng, 30, 990)
    clouds(c, rng, [(560, 110, 320), (160, 480, 300), (600, 520, 280), (380, 960, 360)])
    c.put(clock(rng), 360, 240, 330, mirror=False)
    c.put(rosary(rng, L=900), 300, 640, 640, rot=8)
    c.put(rose_with_leaves(rng, leaves=2), 420, 760, 290, rot=-12)
    sky_rays(c, rng, 384, 520, R=450, op=0.25)


@item("sl_smile_cry", "Smile Now Cry Later", "Arm", "full", False, ["chicano", "sleeve", "script"])
def _(c, rng):
    smoke_bg(c, rng, 30, 990)
    clouds(c, rng, [(170, 90, 300), (600, 110, 300), (190, 600, 280), (590, 640, 280)])
    c.put(drama_masks(rng), 384, 270, 360)
    c.put(banner(rng, "Smile Now", w=620, h=110), 384, 500, 270, mirror=False)
    c.put(rose_with_leaves(rng, leaves=2), 384, 720, 260, rot=-8)
    c.put(banner(rng, "Cry Later", w=620, h=110), 384, 905, 260, mirror=False)


@item("sl_suerte", "Suerte", "Arm", "full", False, ["chicano", "sleeve"])
def _(c, rng):
    smoke_bg(c, rng, 30, 990)
    sky_rays(c, rng, 384, 300, R=420, op=0.3, spread=360)
    clouds(c, rng, [(160, 470, 300), (610, 470, 300), (240, 960, 330), (560, 960, 300)])
    c.put(dice(rng), 384, 240, 320)
    c.put(cards(rng), 384, 700, 320)
    stars_scatter(c, rng, (120, 60, 650, 420), 6)


@item("sl_costa", "Costa Sunset", "Arm", "full", True, ["colour", "sleeve", "cali"])
def _(c, rng):
    smoke_bg(c, rng, 30, 990, op=0.32)
    c.put(palm_sunset(rng, color=True), 384, 250, 380)
    c.put(skyline(rng, color=True), 384, 560, 420)
    c.put(lowrider_car(rng, color=TEAL), 384, 800, 400)
    clouds(c, rng, [(380, 960, 380)])


@item("sl_koi", "Koi y Olas", "Arm", "full", True, ["colour", "sleeve", "japanese"])
def _(c, rng):
    w = band_pattern(rng, "waves", 720, 120)
    for y in (90, 470, 960):
        c.raw(w.place(24, y, 1.0))
    smoke_bg(c, rng, 30, 990, op=0.25)
    c.put(koi(rng, color=ORANGE), 360, 250, 360, rot=-15)
    c.put(lotus(rng, color=True), 400, 520, 240)
    c.put(koi(rng, color=RED), 380, 770, 330, rot=160)
    c.put(cherry_branch(rng, color=True), 560, 640, 260, rot=60)


@item("sl_muertos", "Dia de Muertos", "Arm", "full", True, ["colour", "sleeve", "chicano"])
def _(c, rng):
    smoke_bg(c, rng, 30, 990, op=0.36)
    clouds(c, rng, [(170, 520, 280), (600, 540, 280)])
    c.put(sugar_skull(rng, color=True), 384, 260, 330)
    c.put(rose_with_leaves(rng, color=RED, leaves=2), 330, 700, 280, rot=-15)
    c.put(rose(rng, color=ORANGE), 470, 870, 170, rot=25)
    c.put(rose(rng, color=PINK), 250, 900, 140, rot=-30)


@item("sl_sol_luna", "Sol y Luna", "Arm", "full", False, ["sleeve", "geometric"])
def _(c, rng):
    smoke_bg(c, rng, 30, 990, op=0.35)
    c.put(sun_disc(rng), 384, 250, 340)
    c.put(mandala(rng), 384, 520, 190)
    c.put(moon_stars(rng), 384, 770, 300)
    stars_scatter(c, rng, (140, 600, 640, 980), 7)


@item("sl_lowrider", "Lowrider Life", "Arm", "full", False, ["chicano", "sleeve", "cars"])
def _(c, rng):
    smoke_bg(c, rng, 30, 990)
    sky_rays(c, rng, 384, 420, R=480, op=0.3)
    c.put(skyline(rng), 384, 300, 440)
    c.put(wire_wheel_m(), 384, 140, 200)
    c.put(lowrider_car(rng), 384, 620, 440)
    c.put(banner(rng, "Costa", w=560, h=110), 384, 820, 240, mirror=False)
    clouds(c, rng, [(240, 960, 320), (560, 960, 300)])


@item("sl_corona", "Corona y Rosario", "Arm", "full", False, ["chicano", "sleeve", "faith"])
def _(c, rng):
    smoke_bg(c, rng, 30, 990)
    sky_rays(c, rng, 384, 260, R=420, op=0.32, spread=360)
    c.put(crown(rng), 384, 170, 280)
    c.put(cross(rng, rays_=False), 384, 380, 200)
    c.put(rosary(rng, L=900), 384, 700, 560, rot=-4)
    c.put(script("Bendecido", 150, BL, flourish=False), 384, 900, 250, mirror=False)
    clouds(c, rng, [(170, 560, 280), (600, 580, 280)])


@item("sl_jardin", "Jardin de Mariposas", "Arm", "full", True, ["colour", "sleeve", "flowers"])
def _(c, rng):
    c.put(cherry_branch(rng, color=True), 384, 300, 560, rot=80)
    c.put(lotus(rng, color=True), 384, 540, 240)
    c.put(butterfly(rng, color=True), 300, 170, 200, rot=-15)
    c.put(butterfly(rng, color=True), 470, 760, 180, rot=20)
    c.put(rose_with_leaves(rng, color=PINK, leaves=2), 360, 880, 220, rot=10)


@item("sl_nautico", "Nautico", "Arm", "full", False, ["sleeve", "traditional"])
def _(c, rng):
    w = band_pattern(rng, "waves", 720, 120)
    smoke_bg(c, rng, 30, 990, op=0.3)
    c.raw(w.place(24, 500, 1.0))
    c.put(compass(rng), 384, 250, 320)
    c.put(swallow(rng), 220, 420, 150, rot=10)
    c.put(anchor(rng), 384, 760, 330)
    c.put(banner(rng, "Hope", w=520, h=110), 384, 950, 220, mirror=False)


# helpers that wrap function motifs
def wire_wheel_m():
    m = Motif()
    m.add(wire_wheel(0, 0, 100), Point(0, 0).buffer(100))
    return m


# ======================= HALF SLEEVES (upper arm) =======================
@item("hs_rosas", "Rosas Half Sleeve", "Arm", "upper", False, ["chicano", "half"])
def _(c, rng):
    smoke_bg(c, rng, 30, 470)
    clouds(c, rng, [(170, 400, 280), (600, 420, 280)])
    c.put(rose_with_leaves(rng, leaves=2), 340, 220, 320, rot=-10)
    c.put(rose(rng), 480, 380, 150, rot=30)


@item("hs_reloj", "Reloj Half Sleeve", "Arm", "upper", False, ["chicano", "half"])
def _(c, rng):
    smoke_bg(c, rng, 30, 470)
    sky_rays(c, rng, 384, 260, R=360, op=0.3, spread=360)
    c.put(clock(rng), 384, 250, 300, mirror=False)
    clouds(c, rng, [(200, 420, 260), (580, 420, 260)])


@item("hs_calavera", "Calavera Color", "Arm", "upper", True, ["colour", "half", "chicano"])
def _(c, rng):
    smoke_bg(c, rng, 30, 470, op=0.3)
    c.put(sugar_skull(rng, color=True), 384, 230, 300)
    c.put(rose(rng, color=RED), 230, 400, 140, rot=-20)
    c.put(rose(rng, color=ORANGE), 540, 400, 130, rot=20)


@item("hs_mandala", "Mandala Half Sleeve", "Arm", "upper", False, ["geometric", "half"])
def _(c, rng):
    c.put(mandala(rng), 384, 240, 330)
    c.raw(band_pattern(rng, "geo", 720, 60).place(24, 445, 1.0))


@item("hs_koi", "Koi Half Sleeve", "Arm", "upper", True, ["colour", "half", "japanese"])
def _(c, rng):
    c.raw(band_pattern(rng, "waves", 720, 120).place(24, 420, 1.0))
    c.put(koi(rng, color=ORANGE), 384, 230, 330, rot=-20)


@item("hs_mascaras", "Mascaras Half Sleeve", "Arm", "upper", False, ["chicano", "half"])
def _(c, rng):
    smoke_bg(c, rng, 30, 470)
    c.put(drama_masks(rng), 384, 230, 320)
    c.put(banner(rng, "Vida", w=500, h=110), 384, 420, 220, mirror=False)


@item("hs_palmas", "Palm Sunset Color", "Arm", "upper", True, ["colour", "half", "cali"])
def _(c, rng):
    c.put(palm_sunset(rng, color=True), 384, 250, 340)


@item("hs_mariposas", "Mariposas Color", "Arm", "upper", True, ["colour", "half"])
def _(c, rng):
    c.put(butterfly(rng, color=True), 340, 170, 200, rot=-12)
    c.put(butterfly(rng, color=True), 470, 340, 150, rot=18)
    c.put(rose(rng, color=PINK), 260, 380, 130)


@item("hs_brujula", "Brujula y Rosa", "Arm", "upper", False, ["traditional", "half"])
def _(c, rng):
    c.put(compass(rng), 384, 220, 290)
    c.put(rose_with_leaves(rng, leaves=2), 384, 400, 170)


# ======================= FOREARM SLEEVES (elbow to wrist) =======================
@item("fs_rosario", "Rosas y Rosario", "Arm", "lower", False, ["chicano", "forearm-sleeve", "faith"])
def _(c, rng):
    smoke_bg(c, rng, 540, 990)
    c.put(rosary(rng, L=800), 384, 760, 430, rot=6)
    c.put(rose_with_leaves(rng, leaves=2), 380, 700, 260, rot=-10)
    clouds(c, rng, [(200, 950, 280), (580, 950, 260)])


@item("fs_reloj", "Reloj y Nubes", "Arm", "lower", False, ["chicano", "forearm-sleeve"])
def _(c, rng):
    smoke_bg(c, rng, 540, 990)
    clouds(c, rng, [(200, 600, 260), (580, 600, 260), (380, 960, 340)])
    c.put(clock(rng), 384, 760, 280, mirror=False)


@item("fs_carrucha", "Cruiser Forearm", "Arm", "lower", False, ["chicano", "forearm-sleeve", "cars"])
def _(c, rng):
    smoke_bg(c, rng, 540, 990)
    sky_rays(c, rng, 384, 760, R=380, op=0.3)
    c.put(lowrider_car(rng), 384, 760, 400)
    c.put(script("Costa", 130, BL, flourish=False), 384, 600, 220, mirror=False)


@item("fs_suerte", "Dados y Cartas", "Arm", "lower", False, ["chicano", "forearm-sleeve"])
def _(c, rng):
    smoke_bg(c, rng, 540, 990)
    c.put(cards(rng), 384, 680, 250)
    c.put(dice(rng), 384, 880, 210)


@item("fs_koi", "Koi Forearm Color", "Arm", "lower", True, ["colour", "forearm-sleeve", "japanese"])
def _(c, rng):
    c.raw(band_pattern(rng, "waves", 720, 110).place(24, 950, 1.0))
    c.put(koi(rng, color=RED), 384, 740, 320, rot=170)


@item("fs_cerezo", "Cerezo Forearm Color", "Arm", "lower", True, ["colour", "forearm-sleeve", "flowers"])
def _(c, rng):
    c.put(cherry_branch(rng, color=True), 384, 760, 420, rot=75)


@item("fs_ciudad", "Ciudad Forearm", "Arm", "lower", False, ["forearm-sleeve", "cali"])
def _(c, rng):
    sky_rays(c, rng, 384, 760, R=360, op=0.3)
    c.put(skyline(rng), 384, 760, 380)
    clouds(c, rng, [(260, 600, 250), (520, 620, 230)])


@item("fs_familia", "Familia Forearm", "Arm", "lower", False, ["chicano", "forearm-sleeve", "script"])
def _(c, rng):
    smoke_bg(c, rng, 540, 990, op=0.35)
    c.put(rose_with_leaves(rng, leaves=2), 384, 650, 230)
    c.put(banner(rng, "Familia", w=620, h=110), 384, 850, 260, mirror=False)


# ======================= SINGLE PIECES =======================
FA_SCRIPTS = [("Familia", SC), ("Lealtad", BL), ("Respeto", BL), ("Bendecido", SC), ("Loyalty", BL), ("Blessed", SC),
              ("Faith", SC), ("Mama", BL), ("Esperanza", SC)]
for wd, fnt in FA_SCRIPTS:
    def mk(wd=wd, fnt=fnt):
        def _(c, rng):
            c.put(script(wd, 150, fnt, flourish=(fnt == SC)), 384, 760, min(240, 50 + 30 * len(wd)), mirror=False)
        return _
    item(f"fa_script_{wd.lower()}", f"\"{wd}\" Script", "Arm", "lower", False, ["script", "forearm"])(mk())


@item("fa_rosa", "Rosa Forearm", "Arm", "lower", False, ["forearm", "flowers"])
def _(c, rng):
    c.put(rose_with_leaves(rng, leaves=2), 384, 760, 230)


@item("fa_rosa_roja", "Red Rose Forearm", "Arm", "lower", True, ["colour", "forearm", "flowers"])
def _(c, rng):
    c.put(rose_with_leaves(rng, color=RED, leaves=2), 384, 760, 230)


@item("fa_golondrina", "Golondrina", "Arm", "lower", True, ["colour", "forearm", "traditional"])
def _(c, rng):
    c.put(swallow(rng, color=True), 384, 760, 200, rot=-10)


@item("fa_cruz", "Cruz con Rayos", "Arm", "lower", False, ["forearm", "faith"])
def _(c, rng):
    c.put(cross(rng), 384, 760, 240)


@item("fa_mama", "Mama Heart", "Arm", "lower", True, ["colour", "forearm", "script", "traditional"])
def _(c, rng):
    c.put(heart(rng, color=RED), 384, 740, 170)
    c.put(banner(rng, "Mama", w=480, h=100), 384, 770, 230, mirror=False)


@item("fa_microfono", "Microfono", "Arm", "lower", False, ["forearm", "music"])
def _(c, rng):
    c.put(microphone(rng), 384, 760, 230)
    c.put(music_notes(rng), 470, 640, 110)


@item("fa_reloj_arena", "Reloj de Arena", "Arm", "lower", False, ["forearm"])
def _(c, rng):
    c.put(hourglass(rng), 384, 760, 240)


@item("fa_pluma", "Pluma", "Arm", "lower", False, ["forearm"])
def _(c, rng):
    c.put(feather(rng), 384, 760, 280, rot=20)


@item("fa_ancla", "Ancla", "Arm", "lower", False, ["forearm", "traditional"])
def _(c, rng):
    c.put(anchor(rng), 384, 760, 250)


@item("ua_rosa", "Rosa Upper Arm", "Arm", "upper", False, ["upper-arm", "flowers"])
def _(c, rng):
    c.put(rose_with_leaves(rng, leaves=2), 384, 240, 250)


@item("ua_brujula", "Brujula", "Arm", "upper", False, ["upper-arm", "traditional"])
def _(c, rng):
    c.put(compass(rng), 384, 240, 230)


@item("ua_corona", "Corona", "Arm", "upper", True, ["colour", "upper-arm"])
def _(c, rng):
    c.put(crown(rng, color=True), 384, 230, 220)


@item("ua_golondrinas", "Golondrinas", "Arm", "upper", True, ["colour", "upper-arm", "traditional"])
def _(c, rng):
    c.put(swallow(rng, color=True), 330, 190, 170, rot=-15)
    c.put(swallow(rng, color=True), 450, 330, 140, rot=10)


@item("ua_estrella", "Estrella Nautica", "Arm", "upper", False, ["upper-arm", "traditional"])
def _(c, rng):
    c.put(star(rng, R=200), 384, 230, 200)


@item("ua_amor", "Amor Heart", "Arm", "upper", True, ["colour", "upper-arm", "script"])
def _(c, rng):
    c.put(heart(rng, color=RED), 384, 210, 170)
    c.put(banner(rng, "Amor", w=480, h=100), 384, 240, 250, mirror=False)


@item("ua_luna", "Luna y Estrellas", "Arm", "upper", False, ["upper-arm"])
def _(c, rng):
    c.put(moon_stars(rng), 384, 240, 230)


@item("ua_mascaras", "Mascaras", "Arm", "upper", False, ["upper-arm", "chicano"])
def _(c, rng):
    c.put(drama_masks(rng), 384, 240, 250)


# ======================= BANDS =======================
for kind, nm in (("tribal", "Tribal"), ("geo", "Geometric"), ("chain", "Chain"), ("thorns", "Thorns"), ("rope", "Rope"), ("waves", "Waves")):
    for zone, y, h in (("upper", 400, 80), ("lower", 900, 70)):
        def mk(kind=kind, y=y, h=h):
            def _(c, rng):
                c.raw(band_pattern(rng, kind, 720, h).place(24, y, 1.0))
            return _
        item(f"band_{kind}_{zone}", f"{nm} Band ({'Upper Arm' if zone == 'upper' else 'Wrist'})", "Arm", zone, False, ["band"])(mk())

# ======================= HANDS (back of the hand) =======================
HY = 770


@item("hd_rosa", "Rosa Hand", "Hand", "hand", False, ["hand", "flowers"])
def _(c, rng):
    c.put(rose(rng), 256, HY, 300)


@item("hd_rosa_roja", "Red Rose Hand", "Hand", "hand", True, ["colour", "hand", "flowers"])
def _(c, rng):
    c.put(rose(rng, color=RED), 256, HY, 300)


@item("hd_estrella", "Estrella Hand", "Hand", "hand", False, ["hand"])
def _(c, rng):
    c.put(star(rng, R=200), 256, HY, 280)


@item("hd_destello", "Destello Hand", "Hand", "hand", False, ["hand"])
def _(c, rng):
    c.put(sparkle(rng, R=120), 256, HY, 260)
    c.put(sparkle(rng, R=120), 350, HY - 150, 90)


@item("hd_corazon", "Corazon Hand", "Hand", "hand", True, ["colour", "hand"])
def _(c, rng):
    c.put(heart(rng, color=RED), 256, HY, 260)


@item("hd_cruz", "Cruz Hand", "Hand", "hand", False, ["hand", "faith"])
def _(c, rng):
    c.put(cross(rng), 256, HY, 330)


@item("hd_corona", "Corona Hand", "Hand", "hand", True, ["colour", "hand"])
def _(c, rng):
    c.put(crown(rng, color=True), 256, HY, 280)


@item("hd_golondrina", "Golondrina Hand", "Hand", "hand", True, ["colour", "hand", "traditional"])
def _(c, rng):
    c.put(swallow(rng, color=True), 256, HY, 290, rot=-10)


@item("hd_mandala", "Mandala Hand", "Hand", "hand", False, ["hand", "geometric"])
def _(c, rng):
    c.put(mandala(rng), 256, HY, 300)


@item("hd_loto", "Loto Hand", "Hand", "hand", True, ["colour", "hand", "flowers"])
def _(c, rng):
    c.put(lotus(rng, color=True), 256, HY, 300)


for wd in ("Fe", "Amor", "Vida"):
    def mk(wd=wd):
        def _(c, rng):
            c.put(script(wd, 150, BL, flourish=False), 256, HY, 110 + 50 * len(wd), mirror=False)
        return _
    item(f"hd_script_{wd.lower()}", f"\"{wd}\" Hand", "Hand", "hand", False, ["hand", "script"])(mk())

# ======================= NECK (character's left is on the right of the canvas) =======================
NY = 300


@item("nk_familia", "\"Familia\" Throat", "Neck", "neck", False, ["neck", "script", "chicano"])
def _(c, rng):
    c.put(script("Familia", 150, BL, flourish=False), 512, NY, 270, mirror=False)


@item("nk_bendecido", "\"Bendecido\" Throat", "Neck", "neck", False, ["neck", "script"])
def _(c, rng):
    c.put(script("Bendecido", 150, SC, flourish=True), 512, NY, 250, mirror=False)


@item("nk_rosa_lado", "Rosa Side Neck", "Neck", "neck", False, ["neck", "flowers"])
def _(c, rng):
    c.put(rose_with_leaves(rng, leaves=2), 760, 200, 190, rot=10)


@item("nk_rosa_roja", "Red Rose Side Neck", "Neck", "neck", True, ["colour", "neck", "flowers"])
def _(c, rng):
    c.put(rose_with_leaves(rng, color=RED, leaves=2), 760, 200, 190, rot=10)


@item("nk_estrellas", "Estrellas Behind Ear", "Neck", "neck", False, ["neck"])
def _(c, rng):
    for (x, y, s) in ((800, 110, 60), (845, 175, 44), (795, 225, 34)):
        c.put(star(rng, R=100, nautical=True), x, y, s)


@item("nk_corona", "Corona Throat", "Neck", "neck", True, ["colour", "neck"])
def _(c, rng):
    c.put(crown(rng, color=True), 512, NY, 150)


@item("nk_mariposas", "Mariposas Side Neck", "Neck", "neck", True, ["colour", "neck"])
def _(c, rng):
    c.put(butterfly(rng, color=True), 790, 205, 105, rot=15)
    c.put(butterfly(rng, color=True), 835, 285, 72, rot=-20)


@item("nk_respeto", "\"Respeto\" Banner Throat", "Neck", "neck", False, ["neck", "script", "chicano"])
def _(c, rng):
    c.put(banner(rng, "Respeto", w=600, h=110), 512, NY, 270, mirror=False)


@item("nk_cruz", "Cruz Side Neck", "Neck", "neck", False, ["neck", "faith"])
def _(c, rng):
    c.put(cross(rng, rays_=False), 760, 200, 150)


# ======================= FACE (small pieces only, nothing on the eye) =======================
EYE_Y, EYE_DX = 672, 105


@item("fc_estrella", "Star Under Eye", "Face", "face", False, ["face"])
def _(c, rng):
    c.put(star(rng, R=100, nautical=False), 384 + EYE_DX + 25, EYE_Y + 80, 70)


@item("fc_destello", "Sparkle Cheek", "Face", "face", False, ["face"])
def _(c, rng):
    c.put(sparkle(rng, R=100), 384 + EYE_DX + 25, EYE_Y + 80, 64)
    c.put(sparkle(rng, R=100), 384 + EYE_DX + 62, EYE_Y + 40, 34)


@item("fc_cruz", "Cross By Eye", "Face", "face", False, ["face", "faith"])
def _(c, rng):
    c.put(cross(rng, rays_=False), 384 + EYE_DX + 55, EYE_Y + 45, 72)


@item("fc_corazon", "Heart Cheek", "Face", "face", True, ["colour", "face"])
def _(c, rng):
    c.put(heart(rng, color=RED), 384 + EYE_DX + 30, EYE_Y + 90, 70)


@item("fc_fe", "\"Fe\" Above Brow", "Face", "face", False, ["face", "script"])
def _(c, rng):
    c.put(script("Fe", 150, BL, flourish=False), 384 + 75, EYE_Y - 78, 62, mirror=False)


@item("fc_rosa", "Rose Cheek", "Face", "face", True, ["colour", "face", "flowers"])
def _(c, rng):
    c.put(rose(rng, color=RED), 384 + EYE_DX + 35, EYE_Y + 95, 72)


@item("fc_estrellas", "Stars By Eye", "Face", "face", False, ["face"])
def _(c, rng):
    for (dx, dy, s) in ((30, 70, 38), (58, 100, 28), (28, 128, 22)):
        c.put(star(rng, R=100, nautical=True), 384 + EYE_DX + dx, EYE_Y + dy, s)


# ======================= LEGS (calf mostly; shorts cover the thigh) =======================
@item("lg_rosas_nubes", "Rosas y Nubes Leg Sleeve", "Leg", "full", False, ["chicano", "sleeve", "leg"])
def _(c, rng):
    smoke_bg(c, rng, 330, 990)
    clouds(c, rng, [(160, 420, 260), (480, 440, 240), (320, 960, 300)])
    c.put(rose_with_leaves(rng, leaves=2), 300, 600, 300, rot=-10)
    c.put(rose(rng), 400, 820, 180, rot=20)


@item("lg_koi", "Koi Leg Sleeve", "Leg", "full", True, ["colour", "sleeve", "leg", "japanese"])
def _(c, rng):
    c.raw(band_pattern(rng, "waves", 600, 100).place(20, 950, 1.0))
    c.raw(band_pattern(rng, "waves", 600, 100).place(20, 420, 1.0))
    c.put(koi(rng, color=ORANGE), 320, 660, 340, rot=-15)


@item("lg_rosa", "Rosa Calf", "Leg", "lower", False, ["leg", "flowers"])
def _(c, rng):
    c.put(rose_with_leaves(rng, leaves=2), 320, 720, 260)


@item("lg_reloj", "Reloj Calf", "Leg", "lower", False, ["leg", "chicano"])
def _(c, rng):
    c.put(clock(rng), 320, 720, 250, mirror=False)


@item("lg_calavera", "Calavera Calf Color", "Leg", "lower", True, ["colour", "leg", "chicano"])
def _(c, rng):
    c.put(sugar_skull(rng, color=True), 320, 720, 250)


@item("lg_brujula", "Brujula Calf", "Leg", "lower", False, ["leg", "traditional"])
def _(c, rng):
    c.put(compass(rng), 320, 720, 240)


@item("lg_palmas", "Palm Sunset Calf", "Leg", "lower", True, ["colour", "leg", "cali"])
def _(c, rng):
    c.put(palm_sunset(rng, color=True), 320, 720, 270)


@item("lg_carro", "Cruiser Calf", "Leg", "lower", False, ["leg", "cars"])
def _(c, rng):
    c.put(lowrider_car(rng), 320, 720, 330)


@item("lg_dados", "Dados Calf", "Leg", "lower", False, ["leg"])
def _(c, rng):
    c.put(dice(rng), 320, 720, 220)


@item("lg_mandala", "Mandala Calf", "Leg", "lower", False, ["leg", "geometric"])
def _(c, rng):
    c.put(mandala(rng), 320, 720, 250)


@item("lg_familia", "\"Familia\" Calf", "Leg", "lower", False, ["leg", "script"])
def _(c, rng):
    c.put(script("Familia", 150, BL, flourish=False), 320, 720, 220, mirror=False)


for kind, nm in (("chain", "Chain"), ("thorns", "Thorns"), ("tribal", "Tribal")):
    def mk(kind=kind):
        def _(c, rng):
            c.raw(band_pattern(rng, kind, 600, 42).place(20, 905, 1.0))
        return _
    item(f"lg_band_{kind}", f"{nm} Ankle Band", "Leg", "lower", False, ["band", "leg"])(mk())


# ------------------------------------------------------------------ build
ZONE_Y = {("Arm", "upper"): (8, 488), ("Arm", "lower"): (530, 1000), ("Arm", "full"): (8, 1000),
          ("Leg", "lower"): (520, 1000), ("Leg", "full"): (300, 1000)}


def finish(png, area, zone, band=False):
    """alpha ramps: transparent border (clamped UVs), soft top fade on sleeves, hard limit to the zone's own mesh"""
    im = np.array(Image.open(png).convert("RGBA")).astype(np.float32)
    H, W = im.shape[:2]
    a = np.ones((H, W), np.float32)
    yy = np.arange(H)[:, None].astype(np.float32)
    xx = np.arange(W)[None, :].astype(np.float32)
    b = 4
    a *= np.clip((xx - b) / 6, 0, 1) * np.clip((W - 1 - b - xx) / 6, 0, 1)
    a *= np.clip((yy - b) / 6, 0, 1) * np.clip((H - 1 - b - yy) / 6, 0, 1)
    if (area, zone) in ZONE_Y:
        y0, y1 = ZONE_Y[(area, zone)]
        a *= np.clip((yy - y0) / (40 if zone == "full" else 18), 0, 1) * np.clip((y1 - yy) / 18, 0, 1)
    if area in ("Arm", "Leg") and not band:
        # open inner limb: the design softens out before the inner seam where the wrap meets itself
        cx = W / 2
        r0, r1 = (235, 320) if area == "Arm" else (200, 285)
        a *= np.clip((r1 - np.abs(xx - cx)) / (r1 - r0), 0, 1) ** 1.5
    im[..., 3] *= a
    Image.fromarray(im.clip(0, 255).astype(np.uint8)).save(png)


def main():
    cat, jobs, post = [], [], []
    for it in ITEMS:
        if FILT and not any(f in it["id"] for f in FILT):
            continue
        W, H, lk = CANV[it["area"]]
        LINE_K[0] = lk
        sides = ["L", "R"] if it["area"] in ("Arm", "Leg", "Hand") else ["C"]
        files = {}
        for sd in sides:
            rng = np.random.default_rng(abs(hash(it["id"])) % (2 ** 32) if False else sum(map(ord, it["id"])) * 7919)
            c = Ctx(it["area"], sd)
            it["fn"](c, rng)
            svg = document(c.ms, W, H)
            fn = f"{it['id']}_{sd}" if sd != "C" else it["id"]
            open(f"{OUT}/svg/{fn}.svg", "w").write(svg)
            jobs.append({"svg": f"{OUT}/svg/{fn}.svg", "png": f"{OUT}/{fn}.png", "w": W, "h": H})
            post.append((f"{OUT}/{fn}.png", it["area"], it["zone"], "band" in it["tags"]))
            files[sd] = f"{fn}.png"
        cat.append({k: it[k] for k in ("id", "name", "area", "zone", "colour", "tags")} | {"files": files})
    rasterise(jobs)
    for p in post:
        finish(*p)
    if not FILT:
        json.dump({"canvas": {k: v[:2] for k, v in CANV.items()}, "words": WORDS, "items": cat}, open(f"{OUT}/ink_catalog.json", "w"), indent=1)
    print("items", len(cat), "pngs", len(jobs))


if __name__ == "__main__":
    main()
