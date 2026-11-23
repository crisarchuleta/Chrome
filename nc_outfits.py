# Reference outfits for the 3D garment maker (nc_garments.py), styled after the SevenM / Tha Bronx 3 / realistic
# hood screenshots. Each look builds outer layers last: shoes, then pants, then the top, then accessories.
import nc_garments as NG
BLACK = (0.03, 0.03, 0.035)

def sevenm(o):  # black oversized hoodie, black stacked jeans, white sneakers, gold chain, black gloves, shades
    NG.build_sneakers(o, "Sneaker", color=(0.95, 0.95, 0.94), sole=(0.8, 0.8, 0.78), accent=(0.75, 0.75, 0.74), lace=(0.9, 0.9, 0.9))
    NG.build_pants(o, "Jeans", color=(0.035, 0.035, 0.04))
    NG.build_top(o, "Hoodie", color=BLACK, accent=(0.028, 0.028, 0.032))
    NG.build_chain(o, "Chain")
    NG.build_gloves(o, "Gloves")
    NG.build_shades(o, "Shades")

def pinkcamo(o):
    NG.build_sneakers(o, "Sneaker", color=(0.05, 0.05, 0.05), sole=(0.95, 0.95, 0.95), accent=(0.05, 0.05, 0.05))
    NG.build_pants(o, "Jeans", color=(0.05, 0.05, 0.06))
    NG.build_top(o, "ZipHoodie", color=(1, 1, 1), accent=(0.95, 0.55, 0.7), camo_pal=[(0.96, 0.62, 0.75), (0.86, 0.38, 0.56), (0.99, 0.84, 0.9), (0.62, 0.22, 0.38)],
                 zip_front=True, pocket=False)
    NG.build_chain(o, "Chain", gold=False)
    NG.build_cap(o, "Cap", color=(0.03, 0.03, 0.035))

LOOKS = {"sevenm": sevenm, "pinkcamo": pinkcamo}

def tee_cargo(o):
    NG.build_sneakers(o, "Sneaker", color=(0.92, 0.9, 0.86), accent=(0.55, 0.4, 0.25), sole=(0.85, 0.75, 0.55))
    NG.build_pants(o, "Cargo", fit="cargo", color=(0.24, 0.26, 0.17), cargo=True)
    NG.build_top(o, "Tee", kind="tee", sleeve="short", color=(0.93, 0.93, 0.91), hood=False, pocket=False, rib=False, ease=0.07, sleeve_ease=0.3, thick=0.003)
    NG.build_chain(o, "Chain", pendant=False, droop=0.08)
    NG.build_cap(o, "Beanie", kind="beanie", color=(0.08, 0.09, 0.12))

def puffer_sweats(o):
    NG.build_sneakers(o, "HighTop", high=True, color=(0.08, 0.08, 0.09), sole=(0.9, 0.9, 0.88), accent=(0.75, 0.12, 0.15))
    NG.build_pants(o, "Sweats", fit="sweat", color=(0.42, 0.43, 0.45), cuffed=True, stack=False)
    NG.build_top(o, "Puffer", kind="puffer", puffer=True, color=(0.05, 0.05, 0.06), accent=(0.04, 0.04, 0.05), hood=False, pocket=False, zip_front=True, ease=0.12, sleeve_ease=0.25, length=0.0)
    NG.build_shades(o, "Shades")

LOOKS.update({"tee_cargo": tee_cargo, "puffer_sweats": puffer_sweats})
