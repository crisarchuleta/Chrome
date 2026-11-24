"""Hair cards for the MakeHuman heads (build_heads.py).

Realistic game hair is not a solid shape: it is many thin flat strips ("cards"), each carrying a texture of fine
single hairs with soft alpha, a normal map (so light runs along the strands) and a roughness map. This module makes

  * the strand texture atlas  textures_heads/NC_HairCard_{Color,Normal,Rough}.png
    columns (U, left to right) are card kinds; V runs along the hair from the root (v = 0) to the tips (v = 1):
      0 STRAIGHT_DENSE  a full clump of straight hair (inner layers)
      1 STRAIGHT_WISPY  a thinner clump with loose flyaways (outer layers, edges)
      2 WAVY            the same with a soft S wave
      3 COILY           tight coils (curly tops, afro textures)
    the colour map is greyscale (Roblox tints it with SurfaceAppearance.Color), so one atlas serves every colour.

Pure numpy: it can be imported by build_heads.py (inside Blender) or run on its own to look at the atlas:
    python3 nc_haircards.py out_dir
"""
import math
import os
import sys

import numpy as np

ATLAS = 1024
KINDS = ["STRAIGHT_DENSE", "STRAIGHT_WISPY", "WAVY", "COILY"]
NK = len(KINDS)


def kind_u(kind):
    """the U range of a card kind in the atlas (a small margin so mip filtering doesn't bleed between columns)"""
    k = KINDS.index(kind)
    w = 1.0 / NK
    return k * w + 0.012, (k + 1) * w - 0.012


def _smooth(x, k):
    """a moving average (edges held), so random drifts bend smoothly instead of zigzagging pixel to pixel"""
    pad = np.r_[np.full(k, x[0]), x, np.full(k, x[-1])]
    return np.convolve(pad, np.ones(k) / k, "same")[k:-k]


def _strand_paths(rng, kind, n, H, W):
    """centre-line x (pixels, per row) of each strand in one column, its width, shade, start/end rows"""
    out = []
    rows = np.arange(H)
    v = rows / (H - 1)
    # real hair lies in clumps: strands share their clump's drift and wave, so the card isn't an even comb
    nclump = {"STRAIGHT_DENSE": 9, "STRAIGHT_WISPY": 6, "WAVY": 7, "COILY": 10}[kind]
    cx = rng.beta(2.0, 2.0, nclump) * 0.8 + 0.1
    cdrift = [_smooth(np.cumsum(rng.normal(0, 0.35, H)), 80) for _ in range(nclump)]
    cph = rng.uniform(0, 2 * math.pi, nclump)
    for i in range(n):
        c = rng.integers(nclump)
        # (denser in the middle of the card, so its long edges are soft single hairs, never a straight line)
        x0 = np.clip(cx[c] + rng.normal(0, 0.09), 0.03, 0.97) * W
        # strands converge slightly towards the tips (a clump), wisps drift out
        conv = rng.uniform(0.0, 0.18)
        x = x0 + (W / 2 - x0) * conv * v ** 1.5
        x = x + (cdrift[c] - np.linspace(0, cdrift[c][-1], H)) * 0.6
        if kind == "WAVY":
            ph, amp, fr = cph[c] + rng.normal(0, 0.3), rng.uniform(0.03, 0.05) * W, 2.5
            x = x + amp * np.sin(2 * math.pi * fr * v + ph) * (0.4 + 0.6 * v)
        elif kind == "COILY":
            # a coil seen from the side: a tight zigzag whose phase the whole clump shares
            ph, amp, fr = cph[c] + rng.normal(0, 0.5), rng.uniform(0.025, 0.05) * W, rng.uniform(11, 13)
            x = x + amp * np.sin(2 * math.pi * fr * v + ph)
        # a gentle random drift so no two are parallel
        drift = _smooth(np.cumsum(rng.normal(0, 0.25, H)), 60)
        drift -= np.linspace(0, drift[-1], H)
        x = x + drift * (0.4 if kind != "COILY" else 0.8)
        if kind == "STRAIGHT_WISPY" and rng.random() < 0.25:            # flyaways leave the clump
            x = x + (rng.choice([-1, 1]) * rng.uniform(0.05, 0.2) * W) * v ** 2
        width = rng.uniform(1.0, 2.1) * (W / 256)
        shade = rng.uniform(0.62, 1.0)
        v_end = rng.uniform(0.55, 1.0) if kind != "STRAIGHT_DENSE" else rng.uniform(0.75, 1.0)
        v_start = rng.uniform(0.0, 0.08)
        out.append((x, width, shade, v_start, v_end))
    return out


def _column(rng, kind, H, W):
    """rasterise one card kind: coverage, shade, normal-x (across the strand) for an H x W column"""
    cov = np.zeros((H, W))
    col = np.zeros((H, W))
    nx = np.zeros((H, W))
    n = {"STRAIGHT_DENSE": 340, "STRAIGHT_WISPY": 170, "WAVY": 260, "COILY": 300}[kind]
    xs = np.arange(W)[None, :]
    v = (np.arange(H) / (H - 1))[:, None]
    for x, width, shade, v0, v1 in _strand_paths(rng, kind, n, H, W):
        d = (xs - x[:, None]) / width                                   # signed distance across the strand
        prof = np.clip(1 - np.abs(d), 0, 1)                             # 1 in the middle, 0 at its edge
        # the hair tapers to a point at its tip and starts a little in from the root
        taper = np.clip((v1 - v) / 0.18, 0, 1) * np.clip((v - v0) / 0.03, 0, 1)
        a = np.clip(prof * 1.6, 0, 1) * taper
        root_dark = 0.82 + 0.18 * np.clip(v / 0.3, 0, 1)                # roots a touch darker
        over = a * (1 - cov)                                            # strands in front cover those behind
        col += over * shade * root_dark
        nx += over * np.clip(d, -1, 1)
        cov += over
    with np.errstate(invalid="ignore", divide="ignore"):
        col = np.where(cov > 1e-4, col / np.maximum(cov, 1e-4), 0.8)
        nx = np.where(cov > 1e-4, nx / np.maximum(cov, 1e-4), 0.0)
    # alpha: fully opaque where the hair is dense, soft single hairs at the edges and tips
    alpha = np.clip(cov * 1.15, 0, 1)
    return alpha, col, nx


def make_atlas(out_dir, seed=21):
    rng = np.random.default_rng(seed)
    H = ATLAS
    W = ATLAS // NK
    alpha = np.zeros((H, ATLAS))
    col = np.zeros((H, ATLAS))
    nx = np.zeros((H, ATLAS))
    for k, kind in enumerate(KINDS):
        a, c, x = _column(rng, kind, H, W)
        # keep the margins empty (kind_u leaves them out)
        m = int(0.012 * ATLAS)
        a[:, :m] = 0
        a[:, -m:] = 0
        alpha[:, k * W:(k + 1) * W] = a
        col[:, k * W:(k + 1) * W] = c
        nx[:, k * W:(k + 1) * W] = x
    # tangent-space normal: each strand is a little cylinder, so its normal turns across its width
    ang = nx * math.radians(55)
    N = np.dstack([np.sin(ang), np.zeros_like(ang), np.cos(ang)])
    # fine lengthwise ridges break up the highlight like real hair
    ridge = 0.08 * np.sin(np.arange(H)[:, None] * 0.0 + np.arange(ATLAS)[None, :] * 2.1)
    N[:, :, 0] += ridge
    N /= np.linalg.norm(N, axis=2, keepdims=True)
    rough = 0.42 + 0.18 * (1 - col) + 0.05 * rng.random((H, ATLAS))
    os.makedirs(out_dir, exist_ok=True)
    maps = {
        "NC_HairCard_Color": np.dstack([col, col, col, alpha]),
        "NC_HairCard_Normal": np.dstack([N * 0.5 + 0.5, np.ones((H, ATLAS))]),
        "NC_HairCard_Rough": np.dstack([rough, rough, rough, np.ones((H, ATLAS))]),
    }
    return maps


def save_png(path, rgba):
    """rows top-to-bottom as stored; V = 0 (roots) is the BOTTOM row in UV space, so flip for the file"""
    from PIL import Image
    img = (np.clip(rgba[::-1], 0, 1) * 255 + 0.5).astype(np.uint8)
    Image.fromarray(img, "RGBA").save(path)


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else "."
    for name, m in make_atlas(out).items():
        save_png(os.path.join(out, name + ".png"), m)
    print("wrote atlas to", out)
