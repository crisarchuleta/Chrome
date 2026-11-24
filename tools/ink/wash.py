"""wash.py <in libdir> <out libdir>: lighten the black-and-grey wash so it reads as grey on skin in Roblox.

The library PNGs keep black RGB and do all shading in alpha. In game the mid-alpha black read as near-solid black, so
thin ink now fades faster (alpha^1.8, solid linework above 0.9 untouched) and turns charcoal grey instead of black.
Coloured ink is left alone. Re-run build_swatches.py on the output afterwards."""
import sys, os, glob
import numpy as np
from PIL import Image

def wash(im):
    a = im.astype(float); al = a[..., 3] / 255; rgb = a[..., :3]
    dark = rgb.max(-1) < 60
    al2 = np.where(dark, np.where(al > 0.9, al, al ** 1.8 * 0.9 / 0.9 ** 1.8), al)
    al2 = np.minimum(al2, al)
    t = np.clip((al2 - 0.15) / 0.7, 0, 1)[..., None]
    grey = np.array([78, 80, 86.]) * (1 - t) + np.array([20, 20, 24.]) * t
    rgb2 = np.where(dark[..., None], grey, rgb)
    return np.dstack([rgb2, al2 * 255]).clip(0, 255).astype(np.uint8)

if __name__ == "__main__":
    src, dst = sys.argv[1], sys.argv[2]
    os.makedirs(dst, exist_ok=True)
    for f in sorted(glob.glob(os.path.join(src, "*.png"))):
        Image.fromarray(wash(np.asarray(Image.open(f).convert("RGBA")))).save(os.path.join(dst, os.path.basename(f)))
