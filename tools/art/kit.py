"""Shared Blender kit for Shape Chicago's illustrations: materials in the Shape palette, beveled boxes, buildings with
window bands, trees, the elevated L, a camera and light rig. Run the scene scripts with Blender's Python module (bpy 5.0):
    python tools/art/render.py hero      (see render.py)
Everything is built from code so the pictures can be re-rendered at any size."""
import bpy, math, random
from mathutils import Vector

PAL = {
    "ground": "#ecede6", "street": "#d3d7d0", "curb": "#f7f8f5", "alley": "#e6e8e2", "base": "#d9ddd5", "earth": "#b9b2a4",
    "lake": "#7fb3d1", "lake2": "#bcd8e8",
    "brick": "#b86b4f", "brick2": "#a65a42", "buff": "#d9c3a0", "grey": "#c9c4ba", "stone": "#e8e2d6", "roof": "#7d7a74",
    "navy": "#2b5da0", "navy2": "#1d4580", "ink": "#1a1d21", "flag": "#41b6e6", "star": "#e4002b", "white": "#ffffff",
    "glass": "#a9d2ea", "glassdk": "#4f7fb3", "steel": "#2d3238", "tree": "#7fa36b", "tree2": "#6b9159", "trunk": "#7a5d48",
    "lt3": "#a9d8f2", "lt6": "#41b6e6", "mid": "#2b5da0", "hi": "#1b3768", "gold": "#e8b04a", "green": "#2e9d57",
}

def hexrgb(h, a=1.0):
    h = h.lstrip("#"); r, g, b = (int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))
    lin = lambda c: c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    return (lin(r), lin(g), lin(b), a)

_mats = {}
def mat(name, rough=0.75, metal=0.0, emit=0.0, alpha=1.0, spec=0.35):
    key = (name, rough, metal, emit, alpha)
    if key in _mats: return _mats[key]
    col = PAL.get(name, name)
    m = bpy.data.materials.new(f"{name}_{len(_mats)}"); m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = hexrgb(col)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    if "Specular IOR Level" in b.inputs: b.inputs["Specular IOR Level"].default_value = spec
    if emit:
        b.inputs["Emission Color"].default_value = hexrgb(col); b.inputs["Emission Strength"].default_value = emit
    if alpha < 1:
        b.inputs["Alpha"].default_value = alpha
    _mats[key] = m
    return m

def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    _mats.clear()

def box(x, y, z, w, d, h, m, bevel=0.06, rot=0.0, name="box"):
    """Box with its base centered at (x, y, z), size w (x) × d (y) × h (z)."""
    bpy.ops.mesh.primitive_cube_add(size=1, location=(x, y, z + h / 2), rotation=(0, 0, rot))
    o = bpy.context.object; o.name = name; o.scale = (w, d, h)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    if bevel:
        mod = o.modifiers.new("bev", "BEVEL"); mod.width = bevel; mod.segments = 2; mod.limit_method = "ANGLE"
    o.data.materials.append(m if not isinstance(m, str) else mat(m))
    for p in o.data.polygons: p.use_smooth = False
    return o

def cyl(x, y, z, r, h, m, verts=24, bevel=0.03, r2=None):
    if r2 is None:
        bpy.ops.mesh.primitive_cylinder_add(vertices=verts, radius=r, depth=h, location=(x, y, z + h / 2))
    else:
        bpy.ops.mesh.primitive_cone_add(vertices=verts, radius1=r, radius2=r2, depth=h, location=(x, y, z + h / 2))
    o = bpy.context.object
    if bevel:
        mod = o.modifiers.new("bev", "BEVEL"); mod.width = bevel; mod.segments = 2; mod.limit_method = "ANGLE"
    o.data.materials.append(m if not isinstance(m, str) else mat(m))
    bpy.ops.object.shade_smooth()
    return o

def sphere(x, y, z, r, m, sub=3, sx=1, sy=1, sz=1):
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=sub, radius=r, location=(x, y, z))
    o = bpy.context.object; o.scale = (sx, sy, sz)
    o.data.materials.append(m if not isinstance(m, str) else mat(m)); bpy.ops.object.shade_smooth()
    return o

def windows(x, y, z, w, d, h, floors, face="-y", glass="glass", inset=0.05, band=0.55, cols=None, frame=None):
    """Window openings on one face of a box: a grid of slightly proud glass panes (cols per floor) or a ribbon band."""
    fh = h / floors
    for f in range(floors):
        zz = z + f * fh + fh * 0.28
        hh = fh * band
        if cols:
            along = w if face in ("-y", "+y") else d
            pw = along / cols
            for c in range(cols):
                off = -along / 2 + pw * (c + 0.5)
                ww = pw * 0.56
                if face == "-y": box(x + off, y - d / 2 - inset / 2, zz, ww, inset, hh, glass, bevel=0.01)
                if face == "+y": box(x + off, y + d / 2 + inset / 2, zz, ww, inset, hh, glass, bevel=0.01)
                if face == "-x": box(x - w / 2 - inset / 2, y + off, zz, inset, ww, hh, glass, bevel=0.01)
                if face == "+x": box(x + w / 2 + inset / 2, y + off, zz, inset, ww, hh, glass, bevel=0.01)
        else:
            if face == "-y": box(x, y - d / 2 - inset / 2, zz, w * 0.9, inset, hh, glass, bevel=0.01)
            if face == "+y": box(x, y + d / 2 + inset / 2, zz, w * 0.9, inset, hh, glass, bevel=0.01)
            if face == "-x": box(x - w / 2 - inset / 2, y, zz, inset, d * 0.9, hh, glass, bevel=0.01)
            if face == "+x": box(x + w / 2 + inset / 2, y, zz, inset, d * 0.9, hh, glass, bevel=0.01)

def flat(x, y, z, w, d, floors, wall, faces=("-y",), fh=3.2, cols=2, parapet=True, cornice=None, glass="glass", bay=True):
    """A Chicago two- or three-flat facing -y: masonry box, a front bay, a cornice, punched windows, a stoop."""
    h = floors * fh + 0.6
    box(x, y, z, w, d, h, wall, bevel=0.05)
    box(x, y, z + h, w + 0.25, d + 0.1, 0.45, cornice or "stone", bevel=0.05)
    box(x, y, z + h + 0.02, w - 0.5, d - 0.5, 0.45, mat("#8e8b86", rough=0.95), bevel=0.02)   # tar roof inside the parapet
    box(x + w * 0.25, y + d * 0.3, z + h, 0.7, 0.7, 1.5, wall, bevel=0.04)                     # chimney
    if bay:   # the bay that marks a Chicago greystone or brick two-flat
        bw = w * 0.42; bx = x - w * 0.22
        box(bx, y - d / 2 - 0.55, z + 0.6, bw, 1.1, floors * fh - 0.2, wall, bevel=0.05)
        box(bx, y - d / 2 - 0.55, z + 0.4 + floors * fh, bw + 0.2, 1.3, 0.3, cornice or "stone", bevel=0.03)
        for f in range(floors):
            zz = z + 0.6 + f * fh + fh * 0.25
            box(bx, y - d / 2 - 1.12, zz, bw * 0.62, 0.06, fh * 0.55, glass, bevel=0.01)
            for side in (-1, 1):
                box(bx + side * bw / 2 + side * 0.03, y - d / 2 - 0.55, zz, 0.06, 0.6, fh * 0.55, glass, bevel=0.01)
        for f in range(floors):
            zz = z + 0.6 + f * fh + fh * 0.25
            box(x + w * 0.27, y - d / 2 - 0.03, zz, w * 0.22, 0.06, fh * 0.55, glass, bevel=0.01)
    for f in faces:
        if f == "-y" and bay: continue
        windows(x, y, z + 0.6, w, d, floors * fh, floors, face=f, glass=glass, cols=cols if f in ("-y", "+y") else max(2, int(d / 3.4)))
    box(x + w * 0.27, y - d / 2 - 0.9, z, 1.5, 1.8, 0.7, "stone", bevel=0.03)   # stoop
    return h

def tower(x, y, z, w, d, floors, wall, glass="glassdk", fh=3.1, crown=True, faces=("-y", "-x", "+x")):
    h = floors * fh
    box(x, y, z, w, d, h, wall, bevel=0.08)
    for f in faces: windows(x, y, z, w, d, h, floors, face=f, glass=glass, band=0.5)
    if crown: box(x, y, z + h, w * 0.6, d * 0.5, 1.6, wall, bevel=0.05)
    return h

def tree(x, y, z, s=1.0, m="tree"):
    cyl(x, y, z, 0.18 * s, 2.0 * s, "trunk", verts=8, bevel=0)
    sphere(x, y, z + 2.8 * s, 1.5 * s, m, sub=2, sz=1.05)

def car(x, y, z, rot, m):
    o = box(x, y, z + 0.25, 4.0, 1.8, 0.75, m, bevel=0.22, rot=rot)
    box(x - 0.3 * math.cos(rot), y - 0.3 * math.sin(rot), z + 0.95, 2.1, 1.6, 0.6, "glassdk", bevel=0.18, rot=rot)
    return o

def el_track(pts, z=7.0, m="steel", train=None, train_at=0.4, cars=4, stripe="star"):
    """The elevated L: a steel deck on bents along a polyline, with an optional train (silver cars, colored stripe)."""
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        L = math.hypot(x1 - x0, y1 - y0); ang = math.atan2(y1 - y0, x1 - x0)
        box((x0 + x1) / 2, (y0 + y1) / 2, z, L + 0.4, 5.2, 0.9, m, bevel=0.06, rot=ang)                 # deck
        for side in (-2.4, 2.4):
            box((x0 + x1) / 2 - side * math.sin(ang), (y0 + y1) / 2 + side * math.cos(ang), z + 0.9, L + 0.4, 0.25, 0.7, m, bevel=0.03, rot=ang)   # girders
        n = max(1, int(L / 9))
        for i in range(n + 1):
            t = i / n; bx, by = x0 + (x1 - x0) * t, y0 + (y1 - y0) * t
            for side in (-2.1, 2.1):
                box(bx - side * math.sin(ang), by + side * math.cos(ang), 0, 0.45, 0.45, z, m, bevel=0.03)
            box(bx, by, z - 0.6, 0.5, 5.0, 0.6, m, bevel=0.03, rot=ang)                               # cross beam
    if train:
        # cars along the first segment
        (x0, y0), (x1, y1) = pts[0], pts[1]
        L = math.hypot(x1 - x0, y1 - y0); ang = math.atan2(y1 - y0, x1 - x0); ux, uy = (x1 - x0) / L, (y1 - y0) / L
        start = L * train_at
        for c in range(cars):
            s = start + c * 15.6
            cx, cy = x0 + ux * (s + 7.4), y0 + uy * (s + 7.4)
            box(cx, cy, z + 1.0, 14.8, 2.8, 3.3, mat("#d7dbe0", rough=0.35, metal=0.4), bevel=0.35, rot=ang)
            box(cx - 1.42 * math.sin(ang) * 1.0, cy + 1.42 * math.cos(ang) * -1.0, z + 2.15, 14.82, 0.05, 0.28, stripe, bevel=0.01, rot=ang)
            box(cx + 1.42 * math.sin(ang), cy - 1.42 * math.cos(ang) * -1.0 * -1, z + 2.15, 14.82, 0.05, 0.28, stripe, bevel=0.01, rot=ang)
            for k in range(-2, 3):
                wx, wy = cx + ux * k * 2.8, cy + uy * k * 2.8
                box(wx + 1.43 * math.sin(ang), wy - 1.43 * math.cos(ang), z + 2.5, 1.6, 0.05, 1.0, "glassdk", bevel=0.01, rot=ang)

def crane(x, y, z, h, jib, ang=0.0, m="star", hook_box=None):
    """Tower crane: a lattice-ish mast (a slim box with cross bars), a jib, a counterweight and a cable with a load."""
    box(x, y, z, 1.2, 1.2, h, m, bevel=0.04)
    for k in range(int(h / 2.4)):
        box(x, y, z + k * 2.4 + 1.2, 1.3, 1.3, 0.12, "white", bevel=0)
    ca, sa = math.cos(ang), math.sin(ang)
    back = 7.5                                                                                               # the short back arm
    box(x + ca * (jib - 4 - back) / 2, y + sa * (jib - 4 - back) / 2, z + h, jib - 4 + back, 0.9, 0.9, m, bevel=0.04, rot=ang)
    box(x - ca * (back - 1.4), y - sa * (back - 1.4), z + h + 0.9, 2.4, 1.6, 1.3, mat("grey", rough=0.7), bevel=0.05, rot=ang)   # counterweight, on the arm
    box(x, y, z + h + 0.9, 1.0, 1.0, 2.4, m, bevel=0.04)                                                     # cab/peak
    hx, hy = x + ca * (jib - 7), y + sa * (jib - 7)
    if hook_box:
        cz = hook_box[2]
        cyl(hx, hy, cz + hook_box[3], 0.05, z + h - cz - hook_box[3], "ink", verts=6, bevel=0)
        return hx, hy
    return hx, hy

def rig(ortho_scale, target=(0, 0, 0), elev=35, azim=-45, dist=200, sun=(52, -38), sun_e=3.2, world="#eef3f8", world_e=0.85):
    cam_data = bpy.data.cameras.new("cam"); cam_data.type = "ORTHO"; cam_data.ortho_scale = ortho_scale
    cam = bpy.data.objects.new("cam", cam_data); bpy.context.scene.collection.objects.link(cam)
    el, az = math.radians(elev), math.radians(azim)
    cam.location = Vector(target) + Vector((dist * math.cos(el) * math.cos(az), dist * math.cos(el) * math.sin(az), dist * math.sin(el)))
    d = Vector(target) - cam.location; cam.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    bpy.context.scene.camera = cam
    sd = bpy.data.lights.new("sun", "SUN"); sd.energy = sun_e; sd.angle = math.radians(6); sd.color = (1.0, 0.96, 0.9)
    so = bpy.data.objects.new("sun", sd); bpy.context.scene.collection.objects.link(so)
    so.rotation_euler = (math.radians(90 - sun[0]), 0, math.radians(sun[1] + 90))
    w = bpy.data.worlds.new("w"); w.use_nodes = True
    bg = w.node_tree.nodes["Background"]; bg.inputs[0].default_value = hexrgb(world); bg.inputs[1].default_value = world_e
    bpy.context.scene.world = w
    return cam

def shadow_catcher(z=0, size=600):
    bpy.ops.mesh.primitive_plane_add(size=size, location=(0, 0, z))
    o = bpy.context.object; o.is_shadow_catcher = True
    return o

def render(path, w, h, samples=64, transparent=True):
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"; sc.cycles.device = "CPU"; sc.cycles.samples = samples
    sc.cycles.use_denoising = True
    try: sc.cycles.denoiser = "OPENIMAGEDENOISE"
    except Exception: pass
    sc.cycles.max_bounces = 6; sc.cycles.diffuse_bounces = 3; sc.cycles.glossy_bounces = 2; sc.cycles.transmission_bounces = 2
    sc.render.resolution_x = w; sc.render.resolution_y = h; sc.render.resolution_percentage = 100
    sc.render.film_transparent = transparent
    sc.view_settings.view_transform = "AgX"; sc.view_settings.look = "AgX - Medium High Contrast"
    sc.view_settings.exposure = 0.15
    sc.render.image_settings.file_format = "PNG"; sc.render.image_settings.color_mode = "RGBA" if transparent else "RGB"
    sc.render.filepath = path
    bpy.ops.render.render(write_still=True)

def ribbon(pts, width, thick, z, m, name="ribbon"):
    """A smooth deck along a polyline: one mesh, so curved structures have no seams."""
    import bmesh
    me = bpy.data.meshes.new(name); bm = bmesh.new()
    rows = []
    for i, (x, y) in enumerate(pts):
        a = pts[max(0, i - 1)]; b = pts[min(len(pts) - 1, i + 1)]
        tx, ty = b[0] - a[0], b[1] - a[1]; L = math.hypot(tx, ty) or 1; nx, ny = -ty / L * width / 2, tx / L * width / 2
        rows.append([bm.verts.new((x + nx, y + ny, z)), bm.verts.new((x - nx, y - ny, z)), bm.verts.new((x - nx, y - ny, z + thick)), bm.verts.new((x + nx, y + ny, z + thick))])
    for r0, r1 in zip(rows, rows[1:]):
        for k in range(4): bm.faces.new((r0[k], r1[k], r1[(k + 1) % 4], r0[(k + 1) % 4]))
    bm.faces.new(list(reversed(rows[0]))); bm.faces.new(rows[-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); bpy.context.scene.collection.objects.link(o)
    o.data.materials.append(m if not isinstance(m, str) else mat(m))
    mod = o.modifiers.new("bev", "BEVEL"); mod.width = 0.06; mod.segments = 2; mod.limit_method = "ANGLE"
    return o
