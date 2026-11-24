"""make_vehicle_sounds.py: synthesises every vehicle sound for Neon Coast from scratch (numpy only), so nothing is
copied from another game or library. Writes sounds/<name>.ogg (and a WAV preview copy with NC_WAV=1).

  python3 make_vehicle_sounds.py            (needs numpy + ffmpeg on PATH)

Engines come as three seamless loops per engine type, recorded at a low / mid / high rpm; the game crossfades
between them and nudges the pitch in between (NCCarLife). Loops are built circularly (every filter runs in the
frequency domain over the whole loop) so they repeat without a click.
"""
import os
import subprocess
import numpy as np

SR = 44100
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(os.environ.get("NC_OUT", HERE), "sounds")
os.makedirs(OUT, exist_ok=True)
rng = np.random.default_rng(7)


# ------------------------------------------------------------------ helpers
def band(x, lo, hi, soft=0.15):
    """circular band-pass in the frequency domain (smooth edges)"""
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x), 1 / SR)
    g = np.ones_like(f)
    if lo > 0:
        g *= 1 / (1 + np.exp(-(f - lo) / max(lo * soft, 1)))
    if hi < SR / 2:
        g *= 1 / (1 + np.exp((f - hi) / max(hi * soft, 1)))
    return np.fft.irfft(X * g, len(x))


def tilt(x, db_per_oct):
    X = np.fft.rfft(x)
    f = np.maximum(np.fft.rfftfreq(len(x), 1 / SR), 20)
    return np.fft.irfft(X * (f / 1000) ** (db_per_oct / 6.02), len(x))


def conv_circ(x, k):
    n = len(x)
    kk = np.zeros(n)
    kk[:min(len(k), n)] = k[:n]
    return np.fft.irfft(np.fft.rfft(x) * np.fft.rfft(kk), n)


def norm(x, peak=0.89):
    return x / (np.max(np.abs(x)) + 1e-9) * peak


def env(n, a, d, s_level, r, total):
    """ADSR envelope in seconds"""
    t = np.arange(total) / SR
    e = np.ones(total) * s_level
    e[t < a] = t[t < a] / max(a, 1e-4)
    m = (t >= a) & (t < a + d)
    e[m] = 1 - (1 - s_level) * (t[m] - a) / max(d, 1e-4)
    rel = t > (total / SR - r)
    e[rel] *= np.clip((total / SR - t[rel]) / max(r, 1e-4), 0, 1)
    return e


def save(name, x, loop=False):
    x = norm(x)
    if not loop:  # tiny fades so one-shots never click
        f = min(len(x) // 4, int(0.004 * SR))
        x[:f] *= np.linspace(0, 1, f)
        x[-f:] *= np.linspace(1, 0, f)
    pcm = (np.clip(x, -1, 1) * 32767).astype("<i2")
    wav = os.path.join(OUT, name + ".wav")
    with open(wav, "wb") as fh:
        n = len(pcm) * 2
        fh.write(b"RIFF" + (36 + n).to_bytes(4, "little") + b"WAVEfmt " + (16).to_bytes(4, "little"))
        fh.write((1).to_bytes(2, "little") + (1).to_bytes(2, "little") + SR.to_bytes(4, "little"))
        fh.write((SR * 2).to_bytes(4, "little") + (2).to_bytes(2, "little") + (16).to_bytes(2, "little"))
        fh.write(b"data" + n.to_bytes(4, "little") + pcm.tobytes())
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", wav, "-c:a", "libvorbis", "-q:a", "6",
                    os.path.join(OUT, name + ".ogg")], check=True)
    if not os.environ.get("NC_WAV"):
        os.remove(wav)
    print("wrote", name, f"{len(x) / SR:.2f}s")


# ------------------------------------------------------------------ engines
# cyl: cylinders (4-stroke: cyl/2 firings per rev); pattern: relative timing of each cylinder in one cycle
# (uneven = burble); res: exhaust resonances (Hz, decay s); noise: intake / mechanical hiss level; grit: drive
ENGINES = {
    "v8": dict(cyl=8, pattern=[0, 0.09, 0.25, 0.36, 0.5, 0.6, 0.75, 0.86], amp=[1, .75, .95, .7, 1, .8, .9, .72],
               res=[(70, .05), (140, .03), (420, .012)], noise=0.10, grit=2.2, rpm=(900, 2800, 5600), lp=3800),
    "truck": dict(cyl=8, pattern=[0, 0.1, 0.25, 0.37, 0.5, 0.61, 0.75, 0.87], amp=[1, .7, .9, .75, 1, .78, .92, .7],
                  res=[(55, .07), (110, .04), (330, .015)], noise=0.12, grit=2.6, rpm=(750, 2300, 4600), lp=3000),
    "i4": dict(cyl=4, pattern=[0, .25, .5, .75], amp=[1, .93, .97, .9],
               res=[(160, .02), (520, .008), (1400, .004)], noise=0.22, grit=3.0, rpm=(1000, 4000, 8000), lp=7000),
    "diesel": dict(cyl=6, pattern=[0, 1 / 6, 2 / 6, 3 / 6, 4 / 6, 5 / 6], amp=[1, .9, .95, .92, 1, .9],
                   res=[(48, .06), (95, .04), (2500, .002)], noise=0.18, grit=2.0, rpm=(700, 1800, 3200), lp=5000, knock=0.55),
    "single": dict(cyl=1, pattern=[0], amp=[1], res=[(90, .03), (300, .012), (900, .005)], noise=0.15, grit=3.4,
                   rpm=(1500, 5000, 9500), lp=6000),
    "sport4": dict(cyl=4, pattern=[0, .25, .5, .75], amp=[1, .95, .97, .93],
                   res=[(210, .016), (700, .006), (1800, .003)], noise=0.2, grit=2.6, rpm=(1500, 7000, 13000), lp=9000),
}


def engine_loop(spec, rpm, secs=1.6, load=1.0):
    cycle = 120.0 / rpm  # seconds per 4-stroke cycle (2 revs)
    ncyc = max(1, round(secs / cycle))
    secs = ncyc * cycle
    n = int(round(secs * SR))
    imp = np.zeros(n)
    for c in range(ncyc):
        for off, a in zip(spec["pattern"], spec["amp"]):
            t = (c + off) * cycle
            i = int(round(t * SR)) % n
            imp[i] += a * (1 + 0.12 * rng.standard_normal())
    # exhaust pulse: decaying resonances + a noise burst
    klen = int(0.12 * SR)
    t = np.arange(klen) / SR
    k = np.zeros(klen)
    for f0, dec in spec["res"]:
        k += np.sin(2 * np.pi * f0 * t) * np.exp(-t / dec) * (1 + 0.0 * f0)
    k += 0.5 * rng.standard_normal(klen) * np.exp(-t / 0.006)
    x = conv_circ(imp, k)
    if spec.get("knock"):  # diesel clatter: sharp ticks on each firing
        tick = rng.standard_normal(int(0.004 * SR)) * np.exp(-np.arange(int(0.004 * SR)) / (0.0008 * SR))
        x += spec["knock"] * band(conv_circ(imp, tick), 1500, 7000)
    # mechanical / intake noise, pulsing with the firing
    nz = band(rng.standard_normal(n), 300, spec["lp"])
    fire = np.convolve(np.tile(imp, 3), np.hanning(int(0.01 * SR)), "same")[n:2 * n]
    x = norm(x, 1) + spec["noise"] * norm(nz, 1) * (0.5 + 0.5 * norm(fire, 1))
    x = np.tanh(spec["grit"] * load * x)
    x = band(x, 28, spec["lp"])
    return x


ENGINE_MAP = {}
for name, spec in ENGINES.items():
    for tag, rpm in zip(("low", "mid", "high"), spec["rpm"]):
        save(f"engine_{name}_{tag}", engine_loop(spec, rpm), loop=True)

# electric (golf cart / utility): motor whine with a little gear noise, one loop (pitch follows speed)
n = int(1.0 * SR)
t = np.arange(n) / SR
x = sum(np.sin(2 * np.pi * f * t) * a for f, a in ((220, 1), (440, .35), (660, .15), (1320, .08)))
x += 0.15 * band(rng.standard_normal(n), 2000, 6000)
save("engine_electric", x, loop=True)
# electric car: a smooth motor hum under a soft inverter whine (pitch follows speed in game), seamless
n = int(2.0 * SR)
t = np.arange(n) / SR
x = 0.8 * np.sin(2 * np.pi * 110 * t) + 0.35 * np.sin(2 * np.pi * 220.5 * t) + 0.25 * np.sin(2 * np.pi * 330 * t)
x += 0.22 * np.sin(2 * np.pi * 880 * t) * (0.8 + 0.2 * np.sin(2 * np.pi * 1.5 * t)) + 0.1 * np.sin(2 * np.pi * 1760.5 * t)
x += 0.12 * band(rng.standard_normal(n), 400, 3000)
save("engine_ev", x, loop=True)

# ------------------------------------------------------------------ tyres
n = int(1.2 * SR)
t = np.arange(n) / SR
sq = band(rng.standard_normal(n), 900, 3200, 0.08)
wob = 1 + 0.35 * np.sin(2 * np.pi * (1 / 1.2) * 7 * t)  # integer cycles over the loop
tone = sum(np.sin(2 * np.pi * f * t + rng.uniform(0, 6)) * a for f, a in ((1250, .5), (1875, .25), (2500, .15)))
save("tyre_squeal", (sq * 1.0 + tone * 0.6) * wob, loop=True)
# burnout roar: broadband scrub
save("tyre_scrub", band(rng.standard_normal(n), 150, 2500) * (1 + 0.2 * np.sin(2 * np.pi * 5 / 1.2 * t)), loop=True)

# ------------------------------------------------------------------ horns
def horn(f1, f2, secs=1.0):
    n = int(secs * SR)
    t = np.arange(n) / SR
    x = np.zeros(n)
    for f in (f1, f2):
        f = round(f * secs) / secs  # whole cycles: seamless loop
        ph = 2 * np.pi * f * t
        x += sum(np.sin(ph * h) / h for h in range(1, 12))  # bright buzzy tone
    return band(np.tanh(1.8 * x), 250, 4500)


save("horn_car", horn(420, 528), loop=True)
save("horn_truck", horn(210, 262), loop=True)
save("horn_bike", horn(560, 700), loop=True)

# ------------------------------------------------------------------ sirens (Coast Patrol): wail + yelp, seamless
def siren(lo, hi, period, secs, shape):
    n = int(secs * SR)
    t = np.arange(n) / SR
    ph = (t / period) % 1
    if shape == "wail":
        m = 0.5 - 0.5 * np.cos(2 * np.pi * ph)
    else:
        m = np.where(ph < 0.5, ph * 2, 2 - ph * 2)
    f = lo + (hi - lo) * m
    cyc = np.sum(f) / SR
    f = f * (round(cyc) / cyc)  # a whole number of cycles over the loop: no click at the seam
    phase = 2 * np.pi * (np.cumsum(f) - f[0]) / SR
    x = np.sin(phase) + 0.3 * np.sin(2 * phase) + 0.12 * np.sin(3 * phase)
    return band(np.tanh(1.5 * x), 300, 5000)


save("siren_wail", siren(620, 1420, 4.0, 8.0, "wail"), loop=True)
save("siren_yelp", siren(700, 1500, 0.3, 2.4, "yelp"), loop=True)
n = int(0.9 * SR)
save("siren_airhorn", horn(180, 225, 0.9)[:n] * env(n, .01, .1, .9, .15, n))

# ------------------------------------------------------------------ one-shots
def thud(f0, secs, click=0.4, ring=0.0):
    n = int(secs * SR)
    t = np.arange(n) / SR
    x = np.sin(2 * np.pi * f0 * t * (1 - 0.3 * t / secs)) * np.exp(-t / (secs * 0.18))
    x += click * band(rng.standard_normal(n), 1500, 8000) * np.exp(-t / 0.004)
    x += 0.35 * band(rng.standard_normal(n), 200, 1200) * np.exp(-t / 0.03)
    if ring:
        x += ring * np.sin(2 * np.pi * 1800 * t) * np.exp(-t / 0.05)
    return x


save("door_close", thud(70, 0.45, click=0.5))
save("trunk_close", thud(55, 0.55, click=0.35))
save("hood_close", thud(60, 0.5, click=0.4, ring=0.05))
# door open: latch click + a creak of the hinge
n = int(0.5 * SR)
t = np.arange(n) / SR
x = band(rng.standard_normal(n), 2000, 9000) * np.exp(-t / 0.003)
x[int(0.02 * SR):] += 0.6 * band(rng.standard_normal(n - int(0.02 * SR)), 800, 4000) * np.exp(-t[:n - int(0.02 * SR)] / 0.01)
cr = np.sin(2 * np.pi * np.cumsum(500 + 200 * np.sin(2 * np.pi * 3 * t)) / SR) * env(n, .05, .1, .3, .2, n)
save("door_open", x + 0.12 * band(cr, 300, 3000))
# gas door / small panel
save("panel_click", thud(300, 0.18, click=0.8))
# window motor: whine + rumble, seamless
n = int(1.0 * SR)
t = np.arange(n) / SR
save("window_motor", np.sin(2 * np.pi * 180 * t) * 0.5 + 0.25 * np.sin(2 * np.pi * 360 * t) + 0.3 * band(rng.standard_normal(n), 100, 900), loop=True)
# indicator relay: tick and tock
for nm, f0 in (("indicator_tick", 2400), ("indicator_tock", 1900)):
    n = int(0.06 * SR)
    t = np.arange(n) / SR
    save(nm, (np.sin(2 * np.pi * f0 * t) + band(rng.standard_normal(n), 2000, 9000)) * np.exp(-t / 0.006))
# backfire pops (three takes)
for i in range(3):
    n = int(0.35 * SR)
    t = np.arange(n) / SR
    x = band(rng.standard_normal(n), 60, 3000 + 1000 * i) * np.exp(-t / (0.02 + 0.01 * i))
    x += 0.8 * np.sin(2 * np.pi * (55 + 15 * i) * t) * np.exp(-t / 0.05)
    save(f"backfire_{i + 1}", np.tanh(3 * x))
# engine start: starter motor whirr, then it catches into a v8 idle blip
start_n = int(0.8 * SR)
t = np.arange(start_n) / SR
starter = np.sin(2 * np.pi * np.cumsum(90 + 30 * (t / 0.8)) / SR * 3) * (0.6 + 0.4 * np.sin(2 * np.pi * 12 * t) ** 2)
starter = band(np.tanh(2 * starter) + 0.3 * rng.standard_normal(start_n), 80, 3000) * 0.5
catch = engine_loop(ENGINES["v8"], 1800, secs=0.9)
catch *= env(len(catch), .02, .4, .5, .3, len(catch))
save("engine_start", np.concatenate([starter, catch]))
off = engine_loop(ENGINES["v8"], 700, secs=0.6)
save("engine_off", off * np.linspace(1, 0, len(off)) ** 2)
# hydraulics: pump motor (loop), dump (air / fluid release), hop slam
n = int(1.0 * SR)
t = np.arange(n) / SR
save("hyd_pump", np.tanh(2 * (np.sin(2 * np.pi * 120 * t) + 0.5 * np.sin(2 * np.pi * 240 * t))) * 0.6 + 0.4 * band(rng.standard_normal(n), 300, 2500), loop=True)
n = int(0.7 * SR)
t = np.arange(n) / SR
save("hyd_dump", band(rng.standard_normal(n), 1500, 9000) * env(n, .005, .1, .5, .4, n))
save("hyd_hop", thud(45, 0.6, click=0.6, ring=0.15))
print("done")
