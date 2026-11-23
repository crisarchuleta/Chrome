# nc_walk: walk-around renders of each house on the test street (four corners, a bit above fence height),
# composed into one 2 x 2 sheet per style: previews/Walk_<Style>.png. Plus any extra close-up views.
import os, math
import bpy
import numpy as np
from mathutils import Vector
from nc_kit import PREV


def _shot(scene, cam, loc, tgt, path, w, h):
    scene.render.resolution_x, scene.render.resolution_y = w, h
    cam.location = loc
    cam.rotation_euler = (Vector(tgt) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
    scene.render.filepath = path
    bpy.ops.render.render(write_still=True)


def _sheet(paths, out, w, h):
    img = np.zeros((h * 2, w * 2, 4), dtype=np.float32)
    for k, p in enumerate(paths):
        im = bpy.data.images.load(p)
        px = np.array(im.pixels[:], dtype=np.float32).reshape(h, w, 4)
        r, c = 1 - k // 2, k % 2                 # Blender images start at the bottom row
        img[r * h:(r + 1) * h, c * w:(c + 1) * w] = px
        bpy.data.images.remove(im)
    o = bpy.data.images.new("sheet", w * 2, h * 2, alpha=True)
    o.pixels = img.ravel().tolist()
    o.filepath_raw = out
    o.file_format = "PNG"
    o.save()
    bpy.data.images.remove(o)
    for p in paths:
        os.remove(p)


def walkaround(scene, cam, houses, meta, w=800, h=450):
    """houses: [(style, x, y, rot)] - the first placement of each style is shot."""
    for ob in scene.objects:
        if ob.type == "MESH" and ob.get("style") == "Street":
            ob.hide_render = False
    done = set()
    for (style, x, y, rot) in houses:
        if style in done:
            continue
        done.add(style)
        e = meta[style]["extents_studs"]
        cx, cy = (e["x"][0] + e["x"][1]) / 2, (e["y"][0] + e["y"][1]) / 2
        R = max(e["x"][1] - e["x"][0], e["y"][1] - e["y"][0]) / 2 + 26
        c, s = math.cos(rot), math.sin(rot)
        world = lambda lx, ly, z: (x + lx * c - ly * s, y + lx * s + ly * c, z)
        tgt = world(cx, cy, 7.0)
        paths = []
        for k, (fx, fy) in enumerate(((-0.8, -1.0), (0.8, -1.0), (-0.8, 1.0), (0.8, 1.0))):
            p = os.path.join(PREV, f"_walk_{style}_{k}.png")
            _shot(scene, cam, world(cx + fx * R, cy + fy * R, 13.0), tgt, p, w, h)
            paths.append(p)
        _sheet(paths, os.path.join(PREV, f"Walk_{style}.png"), w, h)


def closeups(scene, cam, shots, w=1280, h=720):
    """shots: {name: (loc, target)} in world coordinates -> previews/Close_<name>.png"""
    for name, (loc, tgt) in shots.items():
        _shot(scene, cam, loc, tgt, os.path.join(PREV, f"Close_{name}.png"), w, h)
