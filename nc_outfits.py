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

def capshades(o):  # matches the person's cap + shades + hoodie reference sheet
    NG.build_top(o, "Hoodie", color=(0.22, 0.22, 0.23), accent=(0.2, 0.2, 0.21))
    NG.build_cap(o, "Cap", color=(0.25, 0.25, 0.26))
    NG.build_shades(o, "Shades")

LOOKS["capshades"] = capshades

def hoodup(o):  # cap first, then the hood pulled up over it
    NG.build_cap(o, "Cap", color=(0.25, 0.25, 0.26))
    NG.build_top(o, "Hoodie", color=(0.22, 0.22, 0.23), accent=(0.2, 0.2, 0.21), hood="up")
    NG.build_shades(o, "Shades")

LOOKS["hoodup"] = hoodup

def chains(o):  # chain reference: tee + cap + shades + choker and rope stack
    NG.build_top(o, "Tee", kind="tee", sleeve="short", color=(0.22, 0.22, 0.23), hood=False, pocket=False, rib=False, ease=0.07, sleeve_ease=0.3, thick=0.003)
    NG.build_chain_stack(o)
    NG.build_cap(o, "Cap", color=(0.25, 0.25, 0.26))
    NG.build_shades(o, "Shades")

LOOKS["chains"] = chains

def shoes_test(o, style="court_high"):
    NG.build_shoe(o, "Shoe", style=style, color=(0.9, 0.9, 0.88), accent=(0.55, 0.08, 0.1), sole=(0.95, 0.95, 0.93), lace=(0.95, 0.95, 0.95))

for _st in ("court_high", "retro_bball", "skate_low", "slip_on", "canvas_high", "runner_retro"):
    LOOKS["shoe_" + _st] = (lambda st: (lambda o: shoes_test(o, st)))(_st)
