"""Shape Chicago icon set: small 3D dioramas on a square tile, one per policy, transit mode and Learn topic.
    python3.11 tools/art/icons.py <name|all> <outdir> [style] [size]
style "clay" = soft daylight like the home page art; "ink" = the same models with drawn outlines and flatter light.
Text is never baked into an icon (labels live in the page, so translations work)."""
import sys, os, math, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy
from kit import *

T = 10.0   # tile size

def tile(top="ground", side="earth", grass=None):
    box(0, 0, -1.1, T, T, 0.8, mat(side, rough=0.95), bevel=0.35)
    box(0, 0, -0.35, T, T, 0.35, mat(top, rough=0.9), bevel=0.25)
    if grass: box(*grass, -0.02, mat("#a7c48f", rough=0.95), bevel=0.05) if False else None

def lawn(x, y, w, d):
    box(x, y, 0, w, d, 0.06, mat("#b5cf9c", rough=0.95), bevel=0.04)

def walk(x, y, w, d):
    box(x, y, 0, w, d, 0.1, mat("curb", rough=0.85), bevel=0.03)

def pitched(x, y, z, w, d, h, m):
    """A gable roof running along x."""
    import bmesh
    me = bpy.data.meshes.new("roof"); bm = bmesh.new()
    p = [(-w / 2, -d / 2, 0), (w / 2, -d / 2, 0), (w / 2, d / 2, 0), (-w / 2, d / 2, 0), (-w / 2, 0, h), (w / 2, 0, h)]
    v = [bm.verts.new((x + a, y + b, z + c)) for a, b, c in p]
    for f in ((0, 1, 5, 4), (3, 4, 5, 2), (0, 4, 3), (1, 2, 5), (0, 3, 2, 1)): bm.faces.new([v[i] for i in f])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new("roof", me); bpy.context.scene.collection.objects.link(o)
    o.data.materials.append(m if not isinstance(m, str) else mat(m)); return o

# ---------- icons ----------
def coach_house():
    tile()
    lawn(0, 0.6, 9.4, 4.2)
    box(0, 4.3, 0, T, 1.4, 0.05, mat("alley", rough=0.9), bevel=0)               # alley at the back
    walk(-1.6, -3.9, 1.0, 2.2)
    flat(-1.2, -2.6, 0, 5.2, 3.6, 2, "brick", fh=2.0, cols=2)                       # the two-flat up front
    # the coach house: garage below, a home above, on the alley
    box(1.6, 3.0, 0, 4.2, 2.6, 1.9, mat("#e4ddcf", rough=0.85), bevel=0.06)
    box(1.6, 1.68, 0.05, 2.6, 0.06, 1.5, mat("#9aa3ad", rough=0.6), bevel=0.01)    # garage door
    box(1.6, 3.0, 1.9, 4.2, 2.6, 1.6, mat("navy", rough=0.7), bevel=0.06)
    for dx in (-1.0, 1.0): box(1.6 + dx, 1.67, 2.25, 0.9, 0.06, 0.9, mat("#ffd98a", rough=0.4, emit=0.6), bevel=0.01)
    pitched(1.6, 3.0, 3.5, 4.5, 2.9, 1.0, mat("roof", rough=0.8))
    tree(3.4, -0.9, 0, s=0.65)

def single_stair():
    tile()
    walk(0, -3.6, 8.6, 1.6)
    # a slim six-flat-ish building; one side opened to show one stair climbing the whole height
    W, D, H = 4.6, 5.2, 7.4
    box(-1.4, 0.6, 0, W, D, H, mat("buff", rough=0.85), bevel=0.06)
    box(-1.4, 0.6, H, W + 0.2, D + 0.2, 0.3, "stone", bevel=0.04)
    for f in range(4):
        for c in (-1, 1): box(-1.4 + c * 1.1, 0.6 - D / 2 - 0.03, 0.5 + f * 1.8, 1.0, 0.06, 1.0, "glass", bevel=0.01)
    # the one stair, cut open on the right side: a zigzag of real steps climbing all four floors
    cx, cy = 2.4, 0.6
    box(cx, cy + 1.45, 0, 2.6, 0.12, H + 0.6, mat("#cfe5f3", rough=0.1, alpha=0.3, spec=0.6), bevel=0.02)
    box(cx + 1.25, cy, 0, 0.12, 3.0, H + 0.6, mat("buff", rough=0.85), bevel=0.02)
    steps = 6; rise = 0.9 / steps
    for f in range(4):
        z0 = f * 1.8
        for k, side in enumerate((-0.62, 0.62)):
            for s_ in range(steps):
                t = s_ / (steps - 1)
                x = cx - 0.95 + 1.9 * t if k == 0 else cx + 0.95 - 1.9 * t
                box(x, cy + side, z0 + k * 0.9 + s_ * rise, 0.36, 1.1, rise + 0.04, mat("navy", rough=0.6), bevel=0.02)
            # landing at the turn
            box(cx + (1.0 if k == 0 else -1.0), cy, z0 + (k + 1) * 0.9 - 0.06, 0.5, 2.4, 0.12, mat("navy2", rough=0.6), bevel=0.02)
    # one person on the stairs, for scale
    cyl(cx - 0.2, cy - 0.62, 1.8 + 0.5, 0.16, 0.55, "star", verts=12, bevel=0.03); sphere(cx - 0.2, cy - 0.62, 1.8 + 1.2, 0.15, "#e8c9a8")

def bus_lane():
    tile(top="street")
    for y in (-4.2, 4.2): walk(0, y, T, 1.6)
    box(0, -1.9, 0, T, 2.6, 0.03, mat("#c0392b", rough=0.8), bevel=0)               # red lane
    for i in range(3): box(-3.6 + i * 3.6, 1.0, 0.03, 1.8, 0.14, 0.01, "white", bevel=0)
    # the bus
    bx, by = -0.6, -1.9
    box(bx, by, 0.35, 7.0, 2.2, 2.3, mat("#f4f5f6", rough=0.35, metal=0.2), bevel=0.3)
    box(bx, by - 1.11, 1.45, 6.4, 0.05, 0.75, "glassdk", bevel=0.01)
    box(bx + 3.51, by, 1.2, 0.05, 1.9, 1.2, "glassdk", bevel=0.01)
    box(bx, by - 1.12, 0.75, 6.8, 0.04, 0.22, "navy", bevel=0.01)
    box(bx, by - 1.12, 1.0, 6.8, 0.04, 0.1, "star", bevel=0.01)
    for wx in (-2.3, 2.1):
        for wy in (-1.0, 1.0):
            o = cyl(bx + wx, by + wy, 0.0, 0.45, 0.35, mat("ink", rough=0.6), verts=16, bevel=0.02)
            o.rotation_euler = (math.radians(90), 0, 0); o.location.z = 0.45
    # a car stuck in the next lane
    car(2.6, 1.9, 0, 0.0, mat("#9aa3ad", rough=0.4, metal=0.3))

def office_conversion():
    tile()
    walk(0, -3.8, T, 1.6)
    W, D = 5.4, 5.0
    floors = 9; fh = 0.95
    box(0, 0.4, 0, W, D, floors * fh, mat("#8fa3b5", rough=0.3, metal=0.2), bevel=0.08)
    for f in range(floors):
        z = 0.2 + f * fh
        homes = f < 6
        for face, ox, oy, w_, d_ in (("-y", 0, 0.4 - D / 2 - 0.03, W * 0.92, 0.06), ("-x", -W / 2 - 0.03, 0.4, 0.06, D * 0.92)):
            if not homes:
                box(ox, oy, z, w_, d_, fh * 0.62, "glassdk", bevel=0.01)
            else:
                n = 3
                for k in range(n):
                    t = -0.5 + (k + 0.5) / n
                    lit = (f * 3 + k) % 4 != 1
                    gm = mat("#ffd98a", rough=0.4, emit=0.8) if lit else mat("glassdk")
                    if face == "-y": box(ox + t * w_ , oy, z, w_ / n * 0.62, d_, fh * 0.6, gm, bevel=0.01)
                    else: box(ox, oy + t * d_, z, d_ if False else 0.06, d_ / n * 0.62, fh * 0.6, gm, bevel=0.01)
        if homes and f % 2 == 0:   # balconies with plants on the converted floors
            box(-1.2, 0.4 - D / 2 - 0.35, z - 0.2, 1.4, 0.7, 0.08, "white", bevel=0.02)
            sphere(-1.6, 0.4 - D / 2 - 0.45, z + 0.05, 0.22, "tree", sub=2)
    box(0, 0.4, floors * fh, W * 0.5, D * 0.4, 0.6, mat("#8fa3b5", rough=0.3, metal=0.2), bevel=0.05)
    # a crane arm dropping a sofa onto a balcony? keep it calm: a small star flag on the roof
    tree(3.6, -2.4, 0, s=0.5)

def short_term_rentals():
    tile()
    walk(0, -3.9, T, 1.4); walk(0.6, -2.4, 1.2, 1.8)
    flat(-0.4, 1.0, 0, 6.0, 4.4, 3, "grey", fh=1.9, cols=2, cornice="stone")
    # a rolling suitcase at the stoop
    sx, sy = 2.4, -3.3
    box(sx, sy, 0.15, 1.4, 0.8, 1.8, mat("star", rough=0.45), bevel=0.12)
    for dx in (-0.35, 0.35): box(sx + dx, sy, 1.95, 0.07, 0.07, 1.0, "steel", bevel=0)
    box(sx, sy, 2.9, 0.8, 0.1, 0.1, "steel", bevel=0.03)
    box(sx, sy - 0.41, 0.4, 1.0, 0.04, 0.12, "white", bevel=0.01); box(sx, sy - 0.41, 1.4, 1.0, 0.04, 0.12, "white", bevel=0.01)
    for dx in (-0.45, 0.45): sphere(sx + dx, sy, 0.14, 0.15, "ink", sub=2)
    box(sx + 0.72, sy, 0.9, 0.04, 0.5, 0.4, mat("#ffffff", rough=0.6), bevel=0.01)   # luggage tag

def city_lots():
    tile()
    walk(0, -3.9, T, 1.4)
    flat(-3.6, 0.8, 0, 2.6, 5.0, 2, "brick2", fh=2.0, cols=1, bay=False)
    flat(3.6, 0.8, 0, 2.6, 5.0, 3, "buff", fh=1.9, cols=1, bay=False)
    lawn(0, 0.8, 4.4, 5.6)
    # a ghost of the home that could go here
    box(0, 1.0, 0, 3.4, 4.2, 4.6, mat("#bcd3ec", rough=0.2, alpha=0.32), bevel=0.06)
    # a sign with the star, on a post
    box(-1.0, -2.5, 0, 0.1, 0.1, 1.6, "steel", bevel=0)
    box(-1.0, -2.55, 1.4, 1.4, 0.06, 0.9, "navy", bevel=0.03)
    for k in (0, 1):
        bpy.ops.mesh.primitive_cone_add(vertices=3, radius1=0.28, radius2=0, depth=0.04, location=(-1.0, -2.6, 1.85),
                                        rotation=(math.radians(90), math.radians(90 + 180 * k), 0))
        bpy.context.object.data.materials.append(mat("white", rough=0.5))
    tree(1.3, -2.4, 0, s=0.38)

ICONS = {"coach_house": coach_house, "single_stair": single_stair, "bus_lane": bus_lane,
         "office_conversion": office_conversion, "short_term_rentals": short_term_rentals, "city_lots": city_lots}

def ink_style():
    sc = bpy.context.scene
    sc.render.use_freestyle = True
    sc.render.line_thickness_mode = "ABSOLUTE"; sc.render.line_thickness = 1.6
    vl = bpy.context.view_layer; fs = vl.freestyle_settings
    ls = fs.linesets[0] if fs.linesets else fs.linesets.new("ink")
    ls.select_by_visibility = True; ls.select_by_edge_types = True
    ls.select_silhouette = True; ls.select_border = True; ls.select_crease = True
    if ls.linestyle is None: ls.linestyle = bpy.data.linestyles.new("ink")
    ls.linestyle.color = (0.10, 0.11, 0.13); ls.linestyle.thickness = 1.6
    fs.crease_angle = math.radians(140)

def build(name, out, style="clay", size=384):
    reset()
    random.seed(7)
    ICONS[name]()
    world = "#eef3f8"
    rig(17.5, target=(0, 0, 1.3), elev=33, azim=-52, sun=(50, -25), sun_e=3.4 if style == "clay" else 2.2,
        world=world, world_e=0.55 if style == "clay" else 1.1)
    shadow_catcher(z=-1.1)
    if style == "ink": ink_style()
    render(os.path.abspath(out), size, size, samples=40)

if __name__ == "__main__":
    name, outdir = sys.argv[1], sys.argv[2]
    style = sys.argv[3] if len(sys.argv) > 3 else "clay"
    size = int(sys.argv[4]) if len(sys.argv) > 4 else 384
    os.makedirs(outdir, exist_ok=True)
    for n in (ICONS if name == "all" else [name]):
        build(n, os.path.join(outdir, f"{n}.png"), style, size)
