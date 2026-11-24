"""Maps NCLookCatalog clothing items (Top / Outer / Bottom / Shoes) to the 3D garment maker, so every catalog
piece gets a fitted mesh on every body. Colours come from the item's default c1 / c2."""
import re
import nc_garments as NG

LINE = re.compile(r'^\s*I\("([a-z0-9_]+)",\s*"(Top|Outer|Bottom|Shoes)",\s*"((?:[^"\\]|\\.)*)",\s*\d+,\s*"([a-z]+)",\s*(\{[^}]*\}|nil),\s*([^,]+),\s*"(#[0-9A-Fa-f]{6})"(?:,\s*([^,]+),\s*"(#[0-9A-Fa-f]{6})")?')


def hexc(h):
    h = h.lstrip("#")
    srgb = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return tuple(c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in srgb)


def parse_params(t):
    out = {}
    if not t or t == "nil":
        return out
    for k, v in re.findall(r'(\w+)\s*=\s*("[^"]*"|[\w.]+)', t):
        if v.startswith('"'):
            out[k] = v[1:-1]
        elif v in ("true", "false"):
            out[k] = v == "true"
        else:
            try:
                out[k] = float(v)
            except ValueError:
                out[k] = v
    return out


def load(path):
    items = []
    for line in open(path, encoding="utf-8"):
        m = LINE.match(line)
        if m:
            id_, slot, name, fam, pp, _, c1, _, c2 = m.groups()
            items.append(dict(id=id_, slot=slot, name=name, fam=fam, p=parse_params(pp), c1=hexc(c1), c2=hexc(c2) if c2 else None))
    return items


CAMO = [(0.33, 0.36, 0.22), (0.18, 0.2, 0.12), (0.5, 0.45, 0.32), (0.1, 0.1, 0.07)]


SHOE_MAP = {  # catalog id -> (SHOE_STYLES key, extra args)
    "shoe_white_low": ("court_low", {}),
    "shoe_black_low": ("court_low", {"white_sole": False}),
    "shoe_chunky": ("runner_retro", {}),
    "shoe_slim_runner": ("runner_retro", {}),
    "shoe_hightop": ("court_high", {}),
    "shoe_hightop_bw": ("court_high", {}),
    "shoe_classic": ("runner_retro", {}),
    "shoe_skate": ("skate_low", {}),
    "shoe_runner": ("runner_retro", {}),
    "shoe_platform": ("canvas_high", {}),
}


def build_item(o, it):
    """Returns True when the item has a 3D garment."""
    f, p, c1 = it["fam"], it["p"], it["c1"]
    c2 = it["c2"] or c1
    nm = it["id"]
    camo = CAMO if p.get("camo") else None
    if f == "tee":
        sl = {"tank": "none", "long": "long"}.get(p.get("sleeve"), "short")
        NG.build_top(o, nm, kind="tee", sleeve=sl, color=c1, accent=c2, hood=False, pocket=False, rib=sl == "long",
                     ease=0.06, sleeve_ease=0.28 if sl == "short" else 0.12, thick=0.003,
                     band=c2 if (p.get("stripe") or p.get("text")) else None, neck_drop=0.05 if sl == "none" else 0)
    elif f == "hoodie":
        NG.build_top(o, nm, color=(1, 1, 1) if camo else c1, accent=c2 if not camo else (0.2, 0.22, 0.14), camo_pal=camo,
                     zip_front=bool(p.get("zip")), pocket=not p.get("zip"), band=c2 if p.get("text") or p.get("puff") else None)
    elif f == "sweater":
        coll = "turtle" if p.get("turtle") else ("stand" if p.get("qzip") else "rib")
        NG.build_top(o, nm, kind="sweater", color=c1, accent=c1, hood=False, pocket=False, collar=coll,
                     neck_drop=0.07 if p.get("vneck") else 0, ease=0.07 if not p.get("chunky") else 0.1, length=-0.02,
                     zip_front=bool(p.get("qzip")))
    elif f in ("shirt", "polo"):
        sl = "short" if (p.get("sleeve") == "tee" or f == "polo") else "long"
        NG.build_top(o, nm, kind="tee", sleeve=sl, color=c1, accent=c2, hood=False, pocket=False, rib=False,
                     collar="shirt", ease=0.05, sleeve_ease=0.1 if sl == "long" else 0.2, thick=0.003, front_open=bool(p.get("open")) and it["slot"] == "Outer",
                     zip_front=not (p.get("open") and it["slot"] == "Outer"), length=-0.01,
                     neck_drop=0.03 if p.get("open") else 0)  # Top-slot shirts stay closed so the tank never shows
    elif f == "jersey":
        sl = {"tee": "short", "long": "long"}.get(p.get("sleeve"), "none")
        NG.build_top(o, nm, kind="tee", sleeve=sl, color=c1, accent=c2, hood=False, pocket=False, rib=True,
                     ease=0.12, sleeve_ease=0.3, thick=0.003, neck_drop=0.04, band=c2, length=0.02)
    elif f == "croptop":
        NG.build_top(o, nm, kind="tee", sleeve="short", color=c1, accent=c2, hood=False, pocket=False, rib=False,
                     ease=0.0, sleeve_ease=0.08, thick=0.003, length=-0.17)
    elif f in ("jumpsuit",):
        NG.build_pants(o, nm + "_Legs", fit="straight", color=c1, accent=c1, stack=False)
        NG.build_top(o, nm, kind="tee", sleeve="short" if p.get("shortSleeve") else "long", color=c1, accent=c2, hood=False,
                     pocket=False, rib=False, collar="shirt", zip_front=True, ease=0.05, length=-0.04)
    elif f in ("robe", "labcoat"):
        L = p.get("len", 1.4) if f == "robe" else 1.3
        NG.build_top(o, nm, kind="coat", color=c1, accent=c2, hood=bool(p.get("hood")), pocket=False, rib=False,
                     collar="lapel" if f == "labcoat" else "rib", length=0.25 * L, front_open=(f == "labcoat"), flare=0.08)
    elif f == "dress":
        NG.build_skirt(o, nm + "_Skirt", length=min(0.75, 0.2 + 0.3 * p.get("len", 1.2)), flare=0.18, color=c1)
        NG.build_top(o, nm, kind="tee", sleeve="short" if p.get("sleeve") else "none", color=c1, accent=c1, hood=False,
                     pocket=False, rib=False, ease=0.0, sleeve_ease=0.05, length=-0.08, collar="none", neck_drop=0.04)
    elif f == "jacket":
        coll = {"stand": "stand", "lapel": "lapel", "rib": "rib", "hood": "rib", "funnel": "turtle", "fur": "lapel"}.get(p.get("collar"), "rib")
        is_open = p.get("open", True) if p.get("collar") == "lapel" else False
        L = p.get("long")
        NG.build_top(o, nm, kind="jacket", sleeve="none" if p.get("vest") else "long", color=(1, 1, 1) if camo else c1, accent=c2,
                     camo_pal=camo, hood=p.get("collar") == "hood", pocket=False, rib=bool(p.get("cuffs")) or p.get("collar") == "rib",
                     puffer=bool(p.get("puffer")), collar=coll, zip_front=bool(p.get("zip")) and not is_open,
                     front_open=is_open, ease=0.1, sleeve_ease=0.16, length=(0.3 * (L - 1) + 0.12) if L else -0.02,
                     flare=0.03 if L else 0.012, band=c2 if p.get("stripes") else None, thick=0.005)
    elif f == "blazer":
        NG.build_top(o, nm, kind="jacket", color=c1, accent=c2, hood=False, pocket=False, rib=False, collar="lapel",
                     front_open=True, ease=0.05, sleeve_ease=0.08, length=0.02, thick=0.005)
    elif f == "vest":
        NG.build_top(o, nm, kind="jacket", sleeve="none", color=c1, accent=c2, hood=False, pocket=False, rib=False,
                     collar="none", neck_drop=0.08 if p.get("suit") else 0.02, ease=0.03 if p.get("suit") else 0.1, length=-0.05, thick=0.006)
    elif f == "pants":
        fit = "cargo" if p.get("cargo") else "sweat" if p.get("cuff") else "baggy" if (p.get("stack") or p.get("wide")) else "straight"
        if "Slim" in it["name"] or "Fitted" in it["name"]:
            fit = "slim"
        NG.build_pants(o, nm, fit=fit, color=c1, accent=c2 if p.get("stripe") else c1, stack=bool(p.get("stack")),
                       cuffed=bool(p.get("cuff")), cargo=bool(p.get("cargo")))
    elif f == "shorts":
        NG.build_pants(o, nm, fit="baggy", color=c1, accent=c1, stack=False, shorts=True)
    elif f == "leggings":
        NG.build_pants(o, nm, fit="slim", color=c1, accent=c1, stack=False)
    elif f == "overalls":
        NG.build_pants(o, nm, fit="straight", color=c1, accent=c1, stack=False)
    elif f == "skirt":
        NG.build_skirt(o, nm, length=0.3, flare=0.22, color=c1, pleats=12 if "Pleat" in it["name"] else 0)
    elif f == "shoes" and it["id"] in SHOE_MAP:
        # sneakers use the reference-matched shoe maker (build_shoe), fitted to each body's own foot
        st, kw = SHOE_MAP[it["id"]]
        NG.build_shoe(o, nm, style=st, color=c1, accent=c2 if c2 != c1 else None,
                      sole=hexc("#F5F5F2") if kw.get("white_sole", True) else c1, **{k: v for k, v in kw.items() if k != "white_sole"})
    elif f == "shoes":
        nmn = it["name"].lower()
        high = any(w in nmn for w in ("high", "boot", "timb", "combat"))
        NG.build_sneakers(o, nm, high=high, color=c1, sole=(0.92, 0.92, 0.9) if "boot" not in nmn else (0.12, 0.1, 0.08),
                          accent=c2, chunky=1.3 if "chunky" in nmn or "platform" in nmn else 1.0)
    else:
        return False
    return True
