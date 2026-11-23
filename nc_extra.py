# nc_extra: more building helpers on top of nc_kit (siding, gable roofs, columns, railings, lanterns,
# export with metadata, preview renders). Import with:  from nc_extra import *
import os
import bpy
from nc_kit import *          # noqa: F401,F403  (Piece, House, T_OUT, T_IN, COLORS, OUT, PREV, reset, ...)
import nc_kit

nc_kit.COLORS.update({
    "Stone": (0.60, 0.56, 0.50), "Siding": (0.76, 0.85, 0.87), "Brick": (0.62, 0.32, 0.24), "Awning": (0.12, 0.55, 0.62),
    "Sign": (0.10, 0.10, 0.13), "Tile": (0.86, 0.85, 0.81), "Deck": (0.56, 0.40, 0.27), "Gutter": (0.95, 0.95, 0.95),
})


def lap_boards(H, axis, fixed, outward, a0, a1, z0, z1, openings=(), kind="Siding", board=0.9):
    """Lap siding shadow lines: a drip strip at the bottom of every board, broken around openings."""
    face = fixed + outward * T_OUT
    z = z0
    while z < z1 - 0.05:
        zt = min(z1, z + board)
        cuts = sorted((o[0], o[1]) for o in openings if o[2] < zt and o[3] > z)
        cur = a0
        for (u0, u1) in cuts:
            if u0 > cur:
                H.uvd(kind, axis, cur, u0, z, z + 0.24, face, face + outward * 0.16)
            cur = max(cur, u1)
        if cur < a1:
            H.uvd(kind, axis, cur, a1, z, z + 0.24, face, face + outward * 0.16)
        z = zt


def _extrude(H, kind, verts2d, mk, a0, a1):
    n = len(verts2d)
    v = [mk(p, a0) for p in verts2d] + [mk(p, a1) for p in verts2d]
    f = [tuple(range(n)), tuple(range(2 * n - 1, n - 1, -1))]
    for i in range(n):
        j = (i + 1) % n
        f.append((i, j, n + j, n + i))
    H.p(kind).solid(v, f)


def prism_x(H, kind, pts_yz, x0, x1):
    _extrude(H, kind, pts_yz, lambda p, x: (x, p[0], p[1]), x0, x1)


def prism_y(H, kind, pts_xz, y0, y1):
    _extrude(H, kind, pts_xz, lambda p, y: (p[0], y, p[1]), y0, y1)


def _slope(H, kind, top_a, top_b, low_a, low_b, t):
    v = [top_a, top_b, low_b, low_a,
         (top_a[0], top_a[1], top_a[2] - t), (top_b[0], top_b[1], top_b[2] - t),
         (low_b[0], low_b[1], low_b[2] - t), (low_a[0], low_a[1], low_a[2] - t)]
    H.p(kind).solid(v, [(0, 1, 2, 3), (7, 6, 5, 4), (0, 4, 5, 1), (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0)])


def gable_roof(H, x0, y0, x1, y1, zb, pitch, over, ridge="x", kind="Roof", end_kind="Siding", t=0.55, ends=(True, True), gutters=True):
    """Gable roof over the wall rectangle x0..x1, y0..y1 (outer faces), eaves at zb. Returns the ridge height."""
    if ridge == "x":
        yc = (y0 + y1) / 2
        hw = (yc - y0) * pitch
        zt, ze = zb + hw, zb - over * pitch
        ex0, ex1 = x0 - over, x1 + over
        _slope(H, kind, (ex0, yc, zt), (ex1, yc, zt), (ex0, y0 - over, ze), (ex1, y0 - over, ze), t)
        _slope(H, kind, (ex1, yc, zt), (ex0, yc, zt), (ex1, y1 + over, ze), (ex0, y1 + over, ze), t)
        for (x, on, a, b) in ((x0, ends[0], x0 - 0.5, x0 + 0.05), (x1, ends[1], x1 - 0.05, x1 + 0.5)):
            if on:
                prism_x(H, end_kind, [(y0, zb), (y1, zb), (yc, zt - t)], a, b)
                vx0, vx1 = (x0 - 0.75, x0 - 0.45) if x == x0 else (x1 + 0.45, x1 + 0.75)
                H.p("Trim").box(vx0, yc - 1.4, zt - hw * 0.55, vx1, yc + 1.4, zt - hw * 0.25)
        for (yy, s) in ((y0 - over, -1), (y1 + over, 1)):
            H.p("Trim").box(ex0, yy - 0.2, ze - 0.7, ex1, yy + 0.2, ze - 0.05)
            if gutters:
                H.p("Gutter").box(ex0, yy + s * 0.2, ze - 0.95, ex1, yy + s * 0.8, ze - 0.35)
        H.p(kind).box(ex0, yc - 0.45, zt - 0.2, ex1, yc + 0.45, zt + 0.3)
    else:
        xc = (x0 + x1) / 2
        hw = (xc - x0) * pitch
        zt, ze = zb + hw, zb - over * pitch
        ey0, ey1 = y0 - over, y1 + over
        _slope(H, kind, (xc, ey1, zt), (xc, ey0, zt), (x0 - over, ey1, ze), (x0 - over, ey0, ze), t)
        _slope(H, kind, (xc, ey0, zt), (xc, ey1, zt), (x1 + over, ey0, ze), (x1 + over, ey1, ze), t)
        for (y, on, a, b) in ((y0, ends[0], y0 - 0.5, y0 + 0.05), (y1, ends[1], y1 - 0.05, y1 + 0.5)):
            if on:
                prism_y(H, end_kind, [(x0, zb), (x1, zb), (xc, zt - t)], a, b)
        for (xx, s) in ((x0 - over, -1), (x1 + over, 1)):
            H.p("Trim").box(xx - 0.2, ey0, ze - 0.7, xx + 0.2, ey1, ze - 0.05)
            if gutters:
                H.p("Gutter").box(xx + s * 0.2, ey0, ze - 0.95, xx + s * 0.8, ey1, ze - 0.35)
        H.p(kind).box(xc - 0.45, ey0, zt - 0.2, xc + 0.45, ey1, zt + 0.3)
    return zt


def frustum(H, kind, x, y, z0, z1, rb, rt):
    v = [(x - rb, y - rb, z0), (x + rb, y - rb, z0), (x + rb, y + rb, z0), (x - rb, y + rb, z0),
         (x - rt, y - rt, z1), (x + rt, y - rt, z1), (x + rt, y + rt, z1), (x - rt, y + rt, z1)]
    H.p(kind).solid(v, [(3, 2, 1, 0), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)])


def craftsman_column(H, x, y, z0, z1, ped_h=4.0):
    """Stone pedestal with a tapered white column on top (craftsman porch)."""
    H.p("Stone").box(x - 1.3, y - 1.3, z0, x + 1.3, y + 1.3, z0 + ped_h)
    H.p("Trim").box(x - 1.45, y - 1.45, z0 + ped_h, x + 1.45, y + 1.45, z0 + ped_h + 0.35)
    frustum(H, "Trim", x, y, z0 + ped_h + 0.35, z1 - 0.7, 0.85, 0.55)
    H.p("Trim").box(x - 0.95, y - 0.95, z1 - 0.7, x + 0.95, y + 0.95, z1)
    H.col(x - 1.3, y - 1.3, z0, x + 1.3, y + 1.3, z1, "column")


def railing(H, x0, y0, x1, y1, z, height=3.2, spacing=0.75, kind="Trim"):
    """Straight axis-aligned railing from (x0, y0) to (x1, y1), standing on z."""
    if abs(x1 - x0) >= abs(y1 - y0):
        a0, a1, c = min(x0, x1), max(x0, x1), y0
        box = lambda u0, u1, d0, d1, z0, z1: H.p(kind).box(u0, d0, z0, u1, d1, z1)
        H.col(a0, c - 0.25, z, a1, c + 0.25, z + height, "rail")
    else:
        a0, a1, c = min(y0, y1), max(y0, y1), x0
        box = lambda u0, u1, d0, d1, z0, z1: H.p(kind).box(d0, u0, z0, d1, u1, z1)
        H.col(c - 0.25, a0, z, c + 0.25, a1, z + height, "rail")
    box(a0, a1, c - 0.22, c + 0.22, z + height - 0.3, z + height)
    box(a0, a1, c - 0.15, c + 0.15, z + 0.35, z + 0.6)
    n = max(1, int((a1 - a0) / spacing))
    for k in range(n + 1):
        u = a0 + (a1 - a0) * k / n
        box(u - 0.09, u + 0.09, c - 0.09, c + 0.09, z + 0.6, z + height - 0.3)
    for u in (a0, a1):                                   # end posts down to the floor (the rail used to float)
        box(u - 0.15, u + 0.15, c - 0.15, c + 0.15, z, z + height - 0.3)


def lantern(H, x, y, z, facing=-1):
    """A wall lantern on a wall facing -Y (facing=-1) or +Y (facing=1); its back plate sits on the wall face y."""
    lo, hi = sorted((y, y + facing * 0.5))
    H.p("Metal").box(x - 0.35, lo, z - 0.6, x + 0.35, hi, z + 0.9)
    lo, hi = sorted((y + facing * 0.5, y + facing * 1.5))
    H.p("Glass").box(x - 0.5, lo, z - 0.5, x + 0.5, hi, z + 0.7)
    lo, hi = sorted((y + facing * 0.4, y + facing * 1.6))
    H.p("Metal").box(x - 0.65, lo, z + 0.7, x + 0.65, hi, z + 1.0)
    H.notes.setdefault("lights", []).append([x, y + facing * 1.0, z])


def downspout(H, x, y, z0, z1):
    H.p("Gutter").box(x - 0.3, y - 0.3, z0, x + 0.3, y + 0.3, z1)


def export_house(H):
    """Build the pieces, export <style>.glb, and return its metadata (triangles, extents, colliders, doors)."""
    for ob in list(bpy.context.scene.objects):
        ob.select_set(False)
    objs, tris = H.build()
    for ob in objs:
        ob.select_set(True)
        ob["style"] = H.style
    xs = [v.co.x for ob in objs for v in ob.data.vertices]
    ys = [v.co.y for ob in objs for v in ob.data.vertices]
    zs = [v.co.z for ob in objs for v in ob.data.vertices]
    path = os.path.join(OUT, H.style + ".glb")
    bpy.ops.export_scene.gltf(filepath=path, export_format="GLB", use_selection=True, export_apply=True, export_yup=True)
    return {
        "glb": path, "pieces": sorted(tris.keys()), "triangles": tris, "maxTriangles": max(tris.values()),
        "extents_studs": {"x": [min(xs), max(xs)], "y": [min(ys), max(ys)], "z": [min(zs), max(zs)]},
        "colliders": H.colliders, "doors": H.doors, "windows": H.windows, "notes": H.notes, "frontFaces": "-Y (Blender)",
    }


def setup_render():
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.display.shading.light = "STUDIO"
    scene.display.shading.color_type = "MATERIAL"
    scene.display.shading.show_shadows = True
    scene.display.shading.show_cavity = True
    scene.render.resolution_x, scene.render.resolution_y = 1280, 800
    world = bpy.data.worlds.new("W")
    world.color = (0.55, 0.72, 0.9)
    scene.world = world
    cam_data = bpy.data.cameras.new("Cam")
    cam_data.lens = 35
    cam_data.clip_end = 5000
    cam = bpy.data.objects.new("Cam", cam_data)
    scene.collection.objects.link(cam)
    scene.camera = cam
    return scene, cam


def render_views(scene, cam, styles, views, prefix):
    from mathutils import Vector
    for ob in scene.objects:
        if ob.type == "MESH":
            ob.hide_render = ob.get("style") not in styles
    for vname, (loc, tgt) in views.items():
        cam.location = loc
        cam.rotation_euler = (Vector(tgt) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
        scene.render.filepath = os.path.join(PREV, f"{prefix}_{vname}.png")
        bpy.ops.render.render(write_still=True)
