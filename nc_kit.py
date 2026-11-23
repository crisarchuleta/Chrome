# nc_kit: shared Blender building kit for Neon Coast (walls with real openings, windows, doors, roofs, colliders).
#   blender --background --factory-startup --python build_houses.py
# Units: 1 Blender unit = 1 Roblox stud. Ground at z = 0, the front of every house faces -Y,
# the garage is always on the +X side (the asymmetric feature used to check orientation after import).
# Every house is enterable: walls are real two-layer walls (stucco outside, plaster inside) built
# around true door and window openings, with floors, ceilings and (two-story) stairs. Rooms are empty
# on purpose: exteriors first.
# Output per style: <Style>.glb (one mesh per material piece), plus houses.json (exact collision
# boxes, door hinges, sizes, triangle counts) and preview renders in previews/.
import bpy, bmesh, json, math, os

OUT = r"C:\Users\Crisa\Documents\NeonCoast_Blender"
PREV = os.path.join(OUT, "previews")
os.makedirs(PREV, exist_ok=True)
UV_TILE = 8.0          # one material tile per 8 studs
T_OUT, T_IN = 0.55, 0.45   # wall layers (studs): stucco skin + plaster skin = 1 stud wall

def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)

COLORS = {
    "WallsOut": (0.93, 0.80, 0.62), "WallsIn": (0.95, 0.94, 0.90), "Trim": (0.97, 0.97, 0.95),
    "Roof": (0.66, 0.31, 0.20), "Floor": (0.55, 0.38, 0.24), "Foundation": (0.62, 0.62, 0.60),
    "Ceiling": (0.97, 0.97, 0.95), "Glass": (0.55, 0.78, 0.92), "Door": (0.40, 0.22, 0.13),
    "GarageDoor": (0.93, 0.93, 0.91), "Accent": (0.52, 0.34, 0.20), "Metal": (0.18, 0.18, 0.20),
    "Shutter": (0.20, 0.38, 0.42), "DoorGlass": (0.55, 0.78, 0.92), "DoorKnob": (0.18, 0.18, 0.20),
    "GarageGlass": (0.55, 0.78, 0.92), "Sash": (0.55, 0.78, 0.92),
}


def lin(c):
    return tuple(((x + 0.055) / 1.055) ** 2.4 if x > 0.04045 else x / 12.92 for x in c)


class Piece:
    def __init__(self, style, kind):
        self.style, self.kind = style, kind
        self.bm = bmesh.new()

    def box(self, x0, y0, z0, x1, y1, z1):
        x0, x1 = min(x0, x1), max(x0, x1)
        y0, y1 = min(y0, y1), max(y0, y1)
        z0, z1 = min(z0, z1), max(z0, z1)
        if x1 - x0 < 1e-4 or y1 - y0 < 1e-4 or z1 - z0 < 1e-4:
            return
        from mathutils import Matrix
        m = Matrix.Translation(((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2)) @ Matrix.Diagonal((x1 - x0, y1 - y0, z1 - z0, 1))
        bmesh.ops.create_cube(self.bm, size=1.0, matrix=m)

    def solid(self, verts, faces):
        vs = [self.bm.verts.new(v) for v in verts]
        made = []
        for f in faces:
            try:
                made.append(self.bm.faces.new([vs[i] for i in f]))
            except ValueError:
                pass
        bmesh.ops.recalc_face_normals(self.bm, faces=made)

    def finish(self):
        bm = self.bm
        if len(bm.faces) == 0:
            bm.free()
            return None
        bm.normal_update()
        uv = bm.loops.layers.uv.new("UVMap")
        for f in bm.faces:
            n = f.normal
            ax = max(range(3), key=lambda i: abs(n[i]))
            for l in f.loops:
                co = l.vert.co
                if ax == 2:
                    u, v = co.x, co.y
                elif ax == 0:
                    u, v = co.y, co.z
                else:
                    u, v = co.x, co.z
                l[uv].uv = (u / UV_TILE, v / UV_TILE)
        name = f"{self.style}_{self.kind}"
        me = bpy.data.meshes.new(name)
        bm.to_mesh(me)
        bm.free()
        ob = bpy.data.objects.new(name, me)
        bpy.context.scene.collection.objects.link(ob)
        mat = bpy.data.materials.new(name)
        col = lin(COLORS.get(self.kind.rstrip("0123456789"), (0.8, 0.8, 0.8)))   # Door3 -> Door colour
        mat.diffuse_color = (*col, 1)
        try:
            mat.use_nodes = True
        except Exception:
            pass
        if mat.node_tree:
            b = mat.node_tree.nodes.get("Principled BSDF")
            if b:
                b.inputs["Base Color"].default_value = (*col, 1)
                b.inputs["Roughness"].default_value = 0.8
        me.materials.append(mat)
        return ob


class House:
    def __init__(self, style):
        self.style = style
        self.pieces = {}
        self.colliders = []
        self.doors = []
        self.windows = []
        self.notes = {}

    def p(self, kind):
        if kind not in self.pieces:
            self.pieces[kind] = Piece(self.style, kind)
        return self.pieces[kind]

    def col(self, x0, y0, z0, x1, y1, z1, tag="wall"):
        self.colliders.append({"min": [min(x0, x1), min(y0, y1), min(z0, z1)], "max": [max(x0, x1), max(y0, y1), max(z0, z1)], "tag": tag})

    # (u, v, depth) on a wall -> world box. axis "x": wall runs along X at y = depth; "y": along Y at x = depth
    def uvd(self, kind, axis, u0, u1, v0, v1, d0, d1):
        if axis == "x":
            self.p(kind).box(u0, d0, v0, u1, d1, v1)
        else:
            self.p(kind).box(d0, u0, v0, d1, u1, v1)

    def wall(self, axis, fixed, outward, a0, a1, z0, z1, openings=(), collide=True, inner_kind="WallsIn", outer_kind="WallsOut"):
        # slice the wall at every opening edge; in each slice, stack solid pieces around the
        # openings that cover it (handles windows stacked above each other on two stories)
        segs = []
        cuts = sorted(set([a0, a1] + [u for o in openings for u in (o[0], o[1]) if a0 < u < a1]))
        for i in range(len(cuts) - 1):
            b0, b1 = cuts[i], cuts[i + 1]
            if b1 - b0 < 1e-3:
                continue
            mid = (b0 + b1) / 2
            holes = sorted((o[2], o[3]) for o in openings if o[0] < mid < o[1])
            z = z0
            for (h0, h1) in holes:
                if h0 > z:
                    segs.append((b0, b1, z, h0))
                z = max(z, h1)
            if z < z1:
                segs.append((b0, b1, z, z1))
        for (b0, b1, c0, c1) in segs:
            if b1 - b0 < 1e-3 or c1 - c0 < 1e-3:
                continue
            self.uvd(outer_kind, axis, b0, b1, c0, c1, fixed, fixed + outward * T_OUT)
            self.uvd(inner_kind, axis, b0, b1, c0, c1, fixed - outward * T_IN, fixed)
            if collide:
                if axis == "x":
                    self.col(b0, fixed - outward * T_IN, c0, b1, fixed + outward * T_OUT, c1)
                else:
                    self.col(fixed - outward * T_IN, b0, c0, fixed + outward * T_OUT, b1, c1)
        # reveals: the opening's sides, sill and head get the outer finish so no skin edge shows
        for (u0, u1, v0, v1) in openings:
            # clipped to this wall's height band, so a wall built as stone + siding bands gets each edge once
            c0, c1 = max(v0, z0), min(v1, z1)
            if c1 - c0 < 1e-3:
                continue
            d0, d1 = fixed - outward * T_IN, fixed + outward * T_OUT
            self.uvd("Trim", axis, u0, u0 + 0.12, c0, c1, d0, d1)
            self.uvd("Trim", axis, u1 - 0.12, u1, c0, c1, d0, d1)
            if z0 <= v1 - 0.12 and v1 <= z1:
                self.uvd("Trim", axis, u0, u1, v1 - 0.12, v1, d0, d1)

    def window(self, axis, fixed, outward, u0, u1, v0, v1, shutters=False, mullions=True, arch=False):
        face = fixed + outward * T_OUT
        fw, dp = 0.45, 0.35
        out = lambda a, b: (face + outward * a, face + outward * b)
        d0, d1 = out(0, dp)
        self.uvd("Trim", axis, u0 - fw, u1 + fw, v1, v1 + fw, d0, d1)               # head
        self.uvd("Trim", axis, u0 - fw, u0, v0, v1, d0, d1)                          # jambs
        self.uvd("Trim", axis, u1, u1 + fw, v0, v1, d0, d1)
        s0, s1 = out(0, 0.65)
        self.uvd("Trim", axis, u0 - fw - 0.35, u1 + fw + 0.35, v0 - 0.45, v0, s0, s1)  # sill
        g0, g1 = fixed - 0.06, fixed + 0.06
        # single-hung: the top pane is fixed, the bottom sash is its own piece just inside it and slides up
        vm = (v0 + v1) / 2
        sash = f"Sash{len(self.windows) + 1}"
        self.uvd("Glass", axis, u0, u1, vm, v1, g0, g1)
        sc = fixed - outward * 0.2
        self.uvd(sash, axis, u0, u1, v0, vm + 0.15, sc - 0.05, sc + 0.05)
        self.windows.append({"axis": axis, "fixed": sc, "outward": outward, "min": [u0, v0], "max": [u1, vm + 0.15], "pieces": [sash]})
        if axis == "x":
            self.col(u0, g0, v0, u1, g1, v1, "glass")
        else:
            self.col(g0, u0, v0, g1, u1, v1, "glass")
        if mullions:
            m0, m1 = fixed + outward * 0.06, fixed + outward * 0.2
            um, vm = (u0 + u1) / 2, (v0 + v1) / 2
            self.uvd("Trim", axis, um - 0.12, um + 0.12, v0, v1, m0, m1)
            self.uvd("Trim", axis, u0, u1, vm - 0.12, vm + 0.12, m0, m1)
        if shutters:
            w = min(2.6, (u1 - u0) * 0.5)
            h0, h1 = out(0.05, 0.3)
            for (a, b) in ((u0 - fw - 0.25 - w, u0 - fw - 0.25), (u1 + fw + 0.25, u1 + fw + 0.25 + w)):
                self.uvd("Shutter", axis, a, b, v0, v1, h0, h1)
                for k in range(1, 6):   # louver lines
                    z = v0 + (v1 - v0) * k / 6
                    l0, l1 = out(0.3, 0.38)
                    self.uvd("Shutter", axis, a + 0.2, b - 0.2, z - 0.08, z + 0.08, l0, l1)
        if arch:   # a keystone-and-arch head (Spanish style), stepped
            for k in range(7):
                t0, t1 = k / 7, (k + 1) / 7
                a0 = u0 - fw + (u1 - u0 + 2 * fw) * t0
                a1 = u0 - fw + (u1 - u0 + 2 * fw) * t1
                mid = (t0 + t1) / 2
                h = math.sin(mid * math.pi) * 1.4
                self.uvd("Trim", axis, a0, a1, v1 + fw, v1 + fw + h + 0.35, d0, d1)

    def door(self, axis, fixed, outward, u0, u1, v0, v1, hinge_at_u0=True, glass=True, kind="front"):
        face = fixed + outward * T_OUT
        fw = 0.55
        d0, d1 = face, face + outward * 0.4
        self.uvd("Trim", axis, u0 - fw, u1 + fw, v1, v1 + fw, d0, d1)
        self.uvd("Trim", axis, u0 - fw, u0, v0, v1, d0, d1)
        self.uvd("Trim", axis, u1, u1 + fw, v0, v1, d0, d1)
        # every leaf is its own set of pieces (wood, glass, knob) so Studio can swing it on its hinge
        n = len(self.doors) + 1
        wood, pane, knob = f"Door{n}", f"DoorGlass{n}", f"DoorKnob{n}"
        t = 0.35
        s0, s1 = fixed - t / 2, fixed + t / 2
        gap = 0.06
        self.uvd(wood, axis, u0 + gap, u1 - gap, v0 + gap, v1 - gap, s0, s1)
        for side in (1, -1):
            p0 = fixed + side * t / 2
            p1 = p0 + side * 0.08
            w = u1 - u0
            for (a, b, c, e) in ((0.18, 0.45, 0.08, 0.42), (0.55, 0.82, 0.08, 0.42), (0.18, 0.45, 0.52, 0.86), (0.55, 0.82, 0.52, 0.86)):
                if glass and c > 0.5:
                    continue
                self.uvd(wood, axis, u0 + w * a, u0 + w * b, v0 + (v1 - v0) * c, v0 + (v1 - v0) * e, p0, p1)
            kx = (u1 - 0.55) if hinge_at_u0 else (u0 + 0.55)
            self.uvd(knob, axis, kx - 0.15, kx + 0.15, v0 + 3.4, v0 + 3.75, p0, p0 + side * 0.32)
        if glass:
            self.uvd(pane, axis, u0 + (u1 - u0) * 0.18, u0 + (u1 - u0) * 0.82, v0 + (v1 - v0) * 0.55, v0 + (v1 - v0) * 0.88, s0 - 0.01, s1 + 0.01)
        hx = u0 if hinge_at_u0 else u1
        if axis == "x":
            hinge = [hx, fixed, v0]
        else:
            hinge = [fixed, hx, v0]
        self.doors.append({"kind": kind, "axis": axis, "hinge": hinge, "outward": outward, "width": u1 - u0, "height": v1 - v0, "hingeAtStart": hinge_at_u0,
                           "min": [u0, v0], "max": [u1, v1], "fixed": fixed, "pieces": [wood, pane, knob] if glass else [wood, knob]})

    def garage_door(self, axis, fixed, outward, u0, u1, v0, v1):
        face = fixed + outward * T_OUT
        fw = 0.6
        d0, d1 = face, face + outward * 0.4
        self.uvd("Trim", axis, u0 - fw, u1 + fw, v1, v1 + fw, d0, d1)
        self.uvd("Trim", axis, u0 - fw, u0, v0, v1, d0, d1)
        self.uvd("Trim", axis, u1, u1 + fw, v0, v1, d0, d1)
        gi = len(self.notes.get("garage", [])) + 1
        body, pane = f"GarageDoor{gi}", f"GarageGlass{gi}"      # their own pieces: the door rolls up in Studio
        g0, g1 = fixed + outward * 0.05, fixed + outward * 0.35
        self.uvd(body, axis, u0 + 0.05, u1 - 0.05, v0 + 0.02, v1 - 0.02, g0, g1)
        n = 4
        for k in range(1, n):                      # sections
            z = v0 + (v1 - v0) * k / n
            self.uvd(body, axis, u0 + 0.1, u1 - 0.1, z - 0.07, z + 0.07, g1, g1 + outward * 0.08)
        for k in range(4):                         # window row in the top section
            w = (u1 - u0 - 1.2) / 4
            a = u0 + 0.6 + k * w + 0.25
            self.uvd(pane, axis, a, a + w - 0.5, v1 - (v1 - v0) / n + 0.45, v1 - 0.45, g1 - 0.01, g1 + outward * 0.03)
        if axis == "x":
            self.col(u0, g0, v0, u1, g1, v1, "garagedoor")
        else:
            self.col(g0, u0, v0, g1, u1, v1, "garagedoor")
        self.notes.setdefault("garage", []).append({"axis": axis, "fixed": fixed, "outward": outward, "min": [u0, v0], "max": [u1, v1], "pieces": [body, pane]})

    def slab(self, kind, x0, y0, x1, y1, z0, z1, tag="floor", holes=()):
        rects = [(x0, y0, x1, y1)]
        for (hx0, hy0, hx1, hy1) in holes:   # cut rectangular holes (stairwells)
            nxt = []
            for (a0, b0, a1, b1) in rects:
                if hx1 <= a0 or hx0 >= a1 or hy1 <= b0 or hy0 >= b1:
                    nxt.append((a0, b0, a1, b1))
                    continue
                if hx0 > a0:
                    nxt.append((a0, b0, hx0, b1))
                if hx1 < a1:
                    nxt.append((hx1, b0, a1, b1))
                if hy0 > b0:
                    nxt.append((max(a0, hx0), b0, min(a1, hx1), hy0))
                if hy1 < b1:
                    nxt.append((max(a0, hx0), hy1, min(a1, hx1), b1))
            rects = nxt
        for (a0, b0, a1, b1) in rects:
            self.p(kind).box(a0, b0, z0, a1, b1, z1)
            if tag:
                self.col(a0, b0, z0, a1, b1, z1, tag)

    def hip_roof(self, x0, y0, x1, y1, zb, pitch, over, kind="Roof", ridge_kind="Trim"):
        x0, y0, x1, y1 = x0 - over, y0 - over, x1 + over, y1 + over
        w, d = x1 - x0, y1 - y0
        zb2 = zb - 0.25
        if w >= d:
            h = d / 2 * pitch
            r0, r1 = x0 + d / 2, x1 - d / 2
            yc = (y0 + y1) / 2
            v = [(x0, y0, zb2), (x1, y0, zb2), (x1, y1, zb2), (x0, y1, zb2), (r0, yc, zb2 + h), (r1, yc, zb2 + h)]
            f = [(0, 1, 5, 4), (1, 2, 5), (2, 3, 4, 5), (3, 0, 4), (3, 2, 1, 0)]
            ridge = (r0, yc, r1, yc)
        else:
            h = w / 2 * pitch
            r0, r1 = y0 + w / 2, y1 - w / 2
            xc = (x0 + x1) / 2
            v = [(x0, y0, zb2), (x1, y0, zb2), (x1, y1, zb2), (x0, y1, zb2), (xc, r0, zb2 + h), (xc, r1, zb2 + h)]
            f = [(0, 1, 4), (1, 2, 5, 4), (2, 3, 5), (3, 0, 4, 5), (3, 2, 1, 0)]
            ridge = (xc, r0, xc, r1)
        self.p(kind).solid(v, f)
        # tile courses: thin horizontal bands so the slope reads as rows of tile from far away
        # fascia boards round the eaves
        fz0, fz1 = zb2 - 0.55, zb2 + 0.05
        self.p("Trim").box(x0 - 0.15, y0 - 0.15, fz0, x1 + 0.15, y0 + 0.2, fz1)
        self.p("Trim").box(x0 - 0.15, y1 - 0.2, fz0, x1 + 0.15, y1 + 0.15, fz1)
        self.p("Trim").box(x0 - 0.15, y0, fz0, x0 + 0.2, y1, fz1)
        self.p("Trim").box(x1 - 0.2, y0, fz0, x1 + 0.15, y1, fz1)
        a, b, c, e = ridge
        if abs(c - a) + abs(e - b) > 0.1:
            self.p(kind).box(min(a, c) - 0.3, min(b, e) - 0.35, zb2 + h - 0.15, max(a, c) + 0.3, max(b, e) + 0.35, zb2 + h + 0.35)
        return zb2 + h

    def shed_roof(self, x0, y0, x1, y1, z_high, z_low, kind="Roof"):
        # slopes down toward -Y (the street side)
        t = 0.5
        v = [(x0, y0, z_low), (x1, y0, z_low), (x1, y1, z_high), (x0, y1, z_high),
             (x0, y0, z_low - t), (x1, y0, z_low - t), (x1, y1, z_high - t), (x0, y1, z_high - t)]
        f = [(0, 1, 2, 3), (7, 6, 5, 4), (0, 4, 5, 1), (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0)]
        self.p(kind).solid(v, f)

    def column(self, x, y, z0, z1, r=0.55, kind="Trim"):
        self.p(kind).box(x - r - 0.25, y - r - 0.25, z0, x + r + 0.25, y + r + 0.25, z0 + 0.6)   # base
        self.p(kind).box(x - r, y - r, z0 + 0.6, x + r, y + r, z1 - 0.6)
        self.p(kind).box(x - r - 0.25, y - r - 0.25, z1 - 0.6, x + r + 0.25, y + r + 0.25, z1)   # capital
        self.col(x - r, y - r, z0, x + r, y + r, z1, "column")

    def stairs(self, x0, x1, y_start, run, z0, z1, steps, kind="Floor"):
        rise = (z1 - z0) / steps
        tread = run / steps
        for k in range(steps):
            ya = y_start + k * tread
            top = z0 + rise * (k + 1)
            self.p(kind).box(x0, ya, z0, x1, ya + tread, top)
            self.col(x0, ya, z0, x1, ya + tread, top, "stairs")
        # rail
        for k in range(steps + 1):
            ya = y_start + k * tread
            top = z0 + rise * min(k + 1, steps)
            self.p("Trim").box(x0 - 0.25, ya - 0.1, top, x0 - 0.05, ya + 0.1, top + 3.2)
        self.p("Trim").solid(
            [(x0 - 0.3, y_start, z0 + rise + 3.2), (x0 - 0.0, y_start, z0 + rise + 3.2), (x0 - 0.0, y_start + run, z1 + 3.2), (x0 - 0.3, y_start + run, z1 + 3.2),
             (x0 - 0.3, y_start, z0 + rise + 3.5), (x0 - 0.0, y_start, z0 + rise + 3.5), (x0 - 0.0, y_start + run, z1 + 3.5), (x0 - 0.3, y_start + run, z1 + 3.5)],
            [(0, 1, 2, 3), (7, 6, 5, 4), (0, 4, 5, 1), (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0)])

    def build(self):
        objs = []
        tris = {}
        for kind, pc in self.pieces.items():
            ob = pc.finish()
            if ob:
                objs.append(ob)
                me = ob.data
                me.calc_loop_triangles()
                tris[ob.name] = len(me.loop_triangles)
        return objs, tris


