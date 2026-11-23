# nc_car_kit: the mesh helpers every Neon Coast vehicle build shares (lowrider, build_vehicles.py). Exec'd into
# the build script's globals: exec(compile(open(os.path.join(HERE, "nc_car_kit.py")).read(), "nc_car_kit.py", "exec"), globals())
# Needs from the caller: bpy, bmesh, math, os, json, Vector, Matrix, COLORS, lin, OUT, and mat_color (the parts file).
# ------------------------------------------------------------------ object kit (objects joined per material at the end)
OBJS = []


def new_obj(bm, kind, style="Lowrider", smooth=0.0):
    me = bpy.data.meshes.new(kind)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(kind, me)
    bpy.context.scene.collection.objects.link(ob)
    ob["kind"], ob["style"], ob["smooth"] = kind, style, smooth
    OBJS.append(ob)
    return ob


def bevel(ob, w, seg=2):
    m = ob.modifiers.new("bev", "BEVEL")
    m.width, m.segments, m.limit_method = w, seg, "ANGLE"
    return ob


def cube(kind, c, s, bev=0.0, style="Lowrider", rot=None, seg=2):
    bm = bmesh.new()
    m = Matrix.Translation(c) @ (rot.to_4x4() if rot else Matrix.Identity(4)) @ Matrix.Diagonal((*s, 1))
    bmesh.ops.create_cube(bm, size=1.0, matrix=m)
    ob = new_obj(bm, kind, style)
    if bev:
        bevel(ob, bev, seg)
    return ob


def box(kind, x0, y0, z0, x1, y1, z1, bev=0.0, style="Lowrider"):
    return cube(kind, Vector(((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2)), (abs(x1 - x0), abs(y1 - y0), abs(z1 - z0)), bev, style)


def axis_rot(d):
    return Vector((0, 0, 1)).rotation_difference(Vector(d).normalized()).to_matrix()


def cyl(kind, p0, p1, r, seg=24, bev=0.0, style="Lowrider", r2=None, smooth=40.0):
    p0, p1 = Vector(p0), Vector(p1)
    d = p1 - p0
    bm = bmesh.new()
    m = Matrix.Translation((p0 + p1) / 2) @ axis_rot(d).to_4x4()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=seg, radius1=r, radius2=r if r2 is None else r2, depth=d.length, matrix=m)
    ob = new_obj(bm, kind, style, smooth)
    if bev:
        bevel(ob, bev, 2)
    return ob


def ring(kind, center, axis, r0, r1, t, seg=40, style="Lowrider"):
    """flat annulus of thickness t, axis = its normal"""
    bm = bmesh.new()
    rot = axis_rot(axis)
    c = Vector(center)
    n = Vector(axis).normalized()
    rings = []
    for (r, off) in ((r0, -t / 2), (r1, -t / 2), (r1, t / 2), (r0, t / 2)):
        vs = []
        for i in range(seg):
            a = 2 * math.pi * i / seg
            vs.append(bm.verts.new(c + rot @ Vector((r * math.cos(a), r * math.sin(a), 0)) + n * off))
        rings.append(vs)
    for k in range(4):
        A, B = rings[k], rings[(k + 1) % 4]
        for i in range(seg):
            j = (i + 1) % seg
            bm.faces.new((A[i], A[j], B[j], B[i]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return new_obj(bm, kind, style, 40.0)


def beam(kind, p0, p1, w, h, up=(0, 0, 1), style="Lowrider"):
    p0, p1 = Vector(p0), Vector(p1)
    f = (p1 - p0)
    L = f.length
    f.normalize()
    u = Vector(up)
    s = f.cross(u)
    if s.length < 1e-4:
        s = f.cross(Vector((1, 0, 0)))
    s.normalize()
    u = s.cross(f)
    rot = Matrix((s, f, u)).transposed()
    return cube(kind, (p0 + p1) / 2, (w, L, h), 0.0, style, rot)


def torus(kind, c, axis, R, r, seg=32, seg2=8, style="Lowrider"):
    bm = bmesh.new()
    rot = axis_rot(axis)
    c = Vector(c)
    grid = []
    for i in range(seg):
        a = 2 * math.pi * i / seg
        ca, sa = math.cos(a), math.sin(a)
        rowv = []
        for j in range(seg2):
            b = 2 * math.pi * j / seg2
            p = Vector(((R + r * math.cos(b)) * ca, (R + r * math.cos(b)) * sa, r * math.sin(b)))
            rowv.append(bm.verts.new(c + rot @ p))
        grid.append(rowv)
    for i in range(seg):
        for j in range(seg2):
            a, b = grid[i][j], grid[(i + 1) % seg][j]
            cc, d = grid[(i + 1) % seg][(j + 1) % seg2], grid[i][(j + 1) % seg2]
            bm.faces.new((a, b, cc, d))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return new_obj(bm, kind, style, 60.0)


def prism(kind, outer, inner, style="Lowrider"):
    """closed solid from two matching quads/polygons (outer face, inner face)"""
    bm = bmesh.new()
    o = [bm.verts.new(v) for v in outer]
    i = [bm.verts.new(v) for v in inner]
    n = len(o)
    bm.faces.new(o)
    bm.faces.new(list(reversed(i)))
    for k in range(n):
        bm.faces.new((o[k], o[(k + 1) % n], i[(k + 1) % n], i[k]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return new_obj(bm, kind, style)


def bake(ob):
    """apply every modifier (bevel, boolean)"""
    if not ob.modifiers:
        return ob
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(ob.evaluated_get(dg))
    old = ob.data
    ob.modifiers.clear()
    ob.data = me
    bpy.data.meshes.remove(old)
    return ob


def shell(bm, t):
    """the inside skin + edges of a one-sided panel: offset every vertex t inward, flip, and close the rim"""
    bm.normal_update()
    out = bmesh.new()
    vo, vi = {}, {}
    for v in bm.verts:
        vo[v] = out.verts.new(v.co)
        vi[v] = out.verts.new(v.co - v.normal * t)
    for f in bm.faces:
        out.faces.new([vi[v] for v in reversed(f.verts)])
    for f in bm.faces:
        for lp in f.loops:
            if lp.edge.is_boundary:
                a, b = lp.vert, lp.link_loop_next.vert
                out.faces.new((vo[b], vo[a], vi[a], vi[b]))
    return out


def image_mat(name, path, base=None):
    """material with a vinyl image: alone (alpha blended), or printed over a base paint colour (previews)"""
    mat = bpy.data.materials.new(name)
    try:
        mat.use_nodes = True
    except Exception:
        pass
    nt = mat.node_tree
    b = nt.nodes.get("Principled BSDF")
    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.image = bpy.data.images.load(path, check_existing=True)
    if base is None:
        nt.links.new(tex.outputs["Color"], b.inputs["Base Color"])
        nt.links.new(tex.outputs["Alpha"], b.inputs["Alpha"])
        try:
            mat.blend_method = "BLEND"
        except Exception:
            pass
    else:
        mix = nt.nodes.new("ShaderNodeMix")
        mix.data_type = "RGBA"
        nt.links.new(tex.outputs["Alpha"], mix.inputs[0])
        mix.inputs[6].default_value = (*base, 1)
        nt.links.new(tex.outputs["Color"], mix.inputs[7])
        nt.links.new(mix.outputs[2], b.inputs["Base Color"])
        b.inputs["Coat Weight"].default_value = 1.0
        b.inputs["Roughness"].default_value = 0.3
    return mat


# ------------------------------------------------------------------ the wheel
def revolve(kind, c, profile, seg=48, style="Lowrider", smooth=50.0):
    """surface of revolution around the X axis through c; profile = [(radius, x offset), ...] (open)"""
    bm = bmesh.new()
    c = Vector(c)
    rings = []
    for i in range(seg):
        a = 2 * math.pi * i / seg
        rings.append([bm.verts.new(c + Vector((x, r * math.cos(a), r * math.sin(a)))) for (r, x) in profile])
    for i in range(seg):
        A, B = rings[i], rings[(i + 1) % seg]
        for k in range(len(profile) - 1):
            bm.faces.new((A[k], A[k + 1], B[k + 1], B[k]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return new_obj(bm, kind, style, smooth)


# ------------------------------------------------------------------ join + export
def join_style(style, prefix):
    """join every object of a style per material kind -> <prefix>_<Kind> (one mesh per material)"""
    groups = {}
    for ob in list(bpy.context.scene.objects):
        if ob.type == "MESH" and ob.get("style") == style:
            groups.setdefault(ob["kind"], []).append(ob)
    out, tris = [], {}
    for kind, obs in sorted(groups.items()):
        bm = bmesh.new()
        smooth = max(o.get("smooth", 0.0) for o in obs)
        custom_uv = any(o.get("uv") for o in obs)
        for ob in obs:
            bake(ob)
            me = ob.data.copy()
            me.transform(ob.matrix_world)
            bm.from_mesh(me)
            bpy.data.meshes.remove(me)
        for ob in obs:
            if ob in OBJS:
                OBJS.remove(ob)
            bpy.data.objects.remove(ob)
        bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=1e-5)
        name = f"{prefix}_{kind}"
        me = bpy.data.meshes.new(name)
        bm.to_mesh(me)
        bm.free()
        # box-projected UVs (1 tile per 8 studs) so imported meshes take materials cleanly; paint panels keep
        # their vinyl UVs
        uv = None if custom_uv else me.uv_layers.new(name="UVMap")
        for poly in (me.polygons if uv else []):
            n = poly.normal
            ax = max(range(3), key=lambda i: abs(n[i]))
            for li in poly.loop_indices:
                co = me.vertices[me.loops[li].vertex_index].co
                u, v = (co.x, co.y) if ax == 2 else ((co.y, co.z) if ax == 0 else (co.x, co.z))
                uv.data[li].uv = (u / 8.0, v / 8.0)
        if smooth > 0:
            for poly in me.polygons:
                poly.use_smooth = True
            try:
                me.set_sharp_from_angle(angle=math.radians(smooth))
            except Exception:
                pass
        ob = bpy.data.objects.new(name, me)
        bpy.context.scene.collection.objects.link(ob)
        ob["style"] = style
        ob["pkind"] = kind
        mat = bpy.data.materials.new(name)
        ck = "Body" if kind.startswith("Panel") else mat_color(kind)
        col = lin(COLORS.get(ck, (0.8, 0.8, 0.8)))
        mat.diffuse_color = (*col, 1)
        mat.metallic = 0.9 if ck in ("Chrome", "Rim", "Spokes", "Hub", "Dish", "Pump", "ContChrome", "SteeringWheel") else 0.0
        paint = ck in ("Body", "Lid", "ContBody") or kind.startswith("Panel")
        if ck == "Top":
            mat.roughness = 0.9
        mat.roughness = 0.15 if mat.metallic > 0.5 else (0.3 if paint else 0.7)
        try:
            mat.use_nodes = True
        except Exception:
            pass
        if mat.node_tree:
            b = mat.node_tree.nodes.get("Principled BSDF")
            if b:
                b.inputs["Base Color"].default_value = (*col, 1)
                b.inputs["Metallic"].default_value = mat.metallic
                b.inputs["Roughness"].default_value = mat.roughness
                if paint:
                    b.inputs["Coat Weight"].default_value = 1.0          # candy clear coat
                if ck in ("Headlight", "Taillight", "Neon", "Neon2", "Light"):
                    b.inputs["Emission Color"].default_value = (*col, 1)
                    b.inputs["Emission Strength"].default_value = 2.0
                if ck == "Glass":
                    b.inputs["Alpha"].default_value = 0.55
        me.materials.append(mat)
        me.calc_loop_triangles()
        tris[name] = len(me.loop_triangles)
        out.append(ob)
    return out, tris


def extents(objs):
    co = [ob.matrix_world @ v.co for ob in objs for v in ob.data.vertices]
    return {"x": [min(c.x for c in co), max(c.x for c in co)], "y": [min(c.y for c in co), max(c.y for c in co)], "z": [min(c.z for c in co), max(c.z for c in co)]}


def export(objs, fname):
    for ob in bpy.context.scene.objects:
        ob.select_set(False)
    for ob in objs:
        ob.select_set(True)
    bpy.ops.export_scene.gltf(filepath=os.path.join(OUT, fname), export_format="GLB", use_selection=True, export_apply=True, export_yup=True)


def car_pt(p):          # Blender -> car-local Roblox frame (forward = -Z)
    x, y, z = p
    return [round(-x, 3), round(z, 3), round(y, 3)]


def imp_pt(p):          # Blender -> the GLB import frame (glTF Y-up: (x, z, -y))
    x, y, z = p
    return [round(x, 3), round(z, 3), round(-y, 3)]


def imp_ext(e):
    a = imp_pt((e["x"][0], e["y"][0], e["z"][0]))
    b = imp_pt((e["x"][1], e["y"][1], e["z"][1]))
    return [min(a[i], b[i]) for i in range(3)], [max(a[i], b[i]) for i in range(3)]


def car_box(mn, mx):
    a, b = car_pt(mn), car_pt(mx)
    return [min(a[0], b[0]), min(a[1], b[1]), min(a[2], b[2]), max(a[0], b[0]), max(a[1], b[1]), max(a[2], b[2])]


def lua(v, ind=""):
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (int, float)):
        return repr(round(v, 3)) if isinstance(v, float) else str(v)
    if isinstance(v, str):
        return json.dumps(v)
    if isinstance(v, (list, tuple)):
        if all(isinstance(x, (int, float, str)) and not isinstance(x, bool) for x in v):
            return "{" + ", ".join(lua(x) for x in v) + "}"
        return "{\n" + "".join(ind + "\t" + lua(x, ind + "\t") + ",\n" for x in v) + ind + "}"
    if isinstance(v, dict):
        items = []
        for k in sorted(v):
            key = k if k.isidentifier() else "[" + json.dumps(k) + "]"
            items.append(ind + "\t" + key + " = " + lua(v[k], ind + "\t") + ",\n")
        return "{\n" + "".join(items) + ind + "}"
    return "nil"


def options_of(info, tris, prefix):
    out = {}
    for k, v in info.items():
        if prefix + k in tris and v["variant"] not in out.setdefault(v["slot"], []):
            out[v["slot"]].append(v["variant"])
    return out
