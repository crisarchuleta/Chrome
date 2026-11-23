import sys, glob
from PIL import Image
files = sys.argv[2:]
th = 300
ims = []
for f in files:
    im = Image.open(f).convert("RGBA")
    s = th / im.height
    im = im.resize((int(im.width * s), th), Image.LANCZOS)
    bg = Image.new("RGBA", im.size, (196, 146, 112, 255)); bg.alpha_composite(im); ims.append(bg)
W = 1800
rows, row, x = [], [], 0
for im in ims:
    if x + im.width > W and row: rows.append(row); row, x = [], 0
    row.append(im); x += im.width + 6
rows.append(row)
out = Image.new("RGB", (W, len(rows) * (th + 6)), (40, 40, 40))
for r, row in enumerate(rows):
    x = 0
    for im in row: out.paste(im.convert("RGB"), (x, r * (th + 6))); x += im.width + 6
out.save(sys.argv[1])
