"""Detailed clay kit for Shape Chicago's street scenes (Learn illustrations, the lot exhibit, Progress art).
Builds on kit.py, but makes boxes, cylinders and spheres straight from mesh data (no bpy.ops), so scenes with
thousands of parts build in seconds. Import this BEFORE icons/icons4 so their helpers pick up the fast versions.
Buildings face -y; (x, y0) is the middle of the front wall at the ground. Real sizes in meters (a city lot is 7.6 x 38).
No words or logos on anything."""
import os, sys, math, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy, bmesh
import kit
from kit import mat, hexrgb, PAL

def _m(m): return m if not isinstance(m, str) else mat(m)

def _obj(me, name, m, bevel, smooth=False):
    o = bpy.data.objects.new(name, me); bpy.context.scene.collection.objects.link(o)
    if bevel:
        mod = o.modifiers.new("bev", "BEVEL"); mod.width = bevel; mod.segments = 2; mod.limit_method = "ANGLE"
    o.data.materials.append(_m(m))
    if smooth:
        for p in me.polygons: p.use_smooth = True
    return o

def box(x, y, z, w, d, h, m, bevel=0.06, rot=0.0, name="box"):
    c, s = math.cos(rot), math.sin(rot); w, d, h = abs(w), abs(d), abs(h)
    vs = [(x + dx * c - dy * s, y + dx * s + dy * c, z + dz) for dz in (0, h) for dx, dy in ((-w / 2, -d / 2), (w / 2, -d / 2), (w / 2, d / 2), (-w / 2, d / 2))]
    me = bpy.data.meshes.new(name)
    me.from_pydata(vs, [], [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]); me.update()
    return _obj(me, name, m, bevel)

def cyl(x, y, z, r, h, m, verts=24, bevel=0.03, r2=None):
    me = bpy.data.meshes.new("cyl"); bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=verts, radius1=r, radius2=r if r2 is None else r2, depth=h)
    bm.to_mesh(me); bm.free()
    o = _obj(me, "cyl", m, bevel, smooth=True); o.location = (x, y, z + h / 2)
    return o

def sphere(x, y, z, r, m, sub=3, sx=1, sy=1, sz=1):
    me = bpy.data.meshes.new("sph"); bm = bmesh.new()
    bmesh.ops.create_icosphere(bm, subdivisions=sub, radius=r)
    bm.to_mesh(me); bm.free()
    o = _obj(me, "sph", m, 0, smooth=True); o.location = (x, y, z); o.scale = (sx, sy, sz)
    return o

kit.box, kit.cyl, kit.sphere = box, cyl, sphere            # kit's own builders (flat, el_track, crane...) now use the fast ones
from kit import *                                            # noqa: E402  (rig, render, shadow_catcher, el_track, crane, reset...)
from icons import pitched                                    # noqa: E402
from icons4 import pane, bay, bay_side_windows, hip          # noqa: E402

GRASS = "#b5cf9c"; ASPHALT = "#c3c8c6"; DARK = "#2a2e36"

def prism(pts, z, h, m, bevel=0.03):
    """An upright prism over a polygon (list of (x, y), counter-clockwise)."""
    me = bpy.data.meshes.new("prism"); n = len(pts)
    vs = [(px, py, z) for px, py in pts] + [(px, py, z + h) for px, py in pts]
    fs = [tuple(reversed(range(n))), tuple(range(n, 2 * n))] + [(i, (i + 1) % n, n + (i + 1) % n, n + i) for i in range(n)]
    me.from_pydata(vs, [], fs); me.update()
    return _obj(me, "prism", m, bevel)

def gable(x, y, z, w, d, h, m, over=0.3):
    """A gable roof with its ridge running front to back (along y), so the gable end faces the street."""
    w2, d2 = w / 2 + over, d / 2 + over
    vs = [(x - w2, y - d2, z), (x + w2, y - d2, z), (x + w2, y + d2, z), (x - w2, y + d2, z), (x, y - d2, z + h), (x, y + d2, z + h)]
    me = bpy.data.meshes.new("gable"); me.from_pydata(vs, [], [(0, 1, 4), (1, 2, 5, 4), (2, 3, 5), (3, 0, 4, 5), (0, 3, 2, 1)]); me.update()
    return _obj(me, "gable", m, 0.04)

# ---------- ground ----------
def slab(w, d, x=0, y=0, thick=0.9):
    box(x, y, -0.35 - thick, w, d, thick, mat("earth", rough=0.95), bevel=0.4)
    box(x, y, -0.35, w, d, 0.35, mat("ground", rough=0.9), bevel=0.3)

def street_base(w=88, d=30, yards=True, alley=True):
    """A block face seen from across the street: street, curb, parkway, sidewalk, front yards, room for buildings, alley."""
    slab(w, d); f = -d / 2; W = w - 0.5
    box(0, f + 3.0, 0, W, 5.6, 0.05, mat(ASPHALT, rough=0.9), bevel=0.02)                 # the street
    for k in range(int(W / 5)): box(-W / 2 + 2.6 + k * 5, f + 0.7, 0.05, 2.2, 0.16, 0.02, "white", bevel=0)   # center line dashes
    box(0, f + 5.95, 0, W, 0.3, 0.2, mat("curb", rough=0.8), bevel=0.04)
    box(0, f + 7.0, 0, W, 1.8, 0.14, mat(GRASS, rough=0.95), bevel=0.04)                  # parkway
    box(0, f + 9.1, 0, W, 2.4, 0.16, mat("curb", rough=0.85), bevel=0.03)                 # sidewalk
    for k in range(int(W / 1.8)): box(-W / 2 + 0.9 + k * 1.8, f + 9.1, 0.16, 0.03, 2.4, 0.005, mat("#dfe2dc", rough=0.9), bevel=0)
    if yards: box(0, (f + 10.3 + d / 2 - 2.4) / 2, 0, W, d / 2 - 2.4 - f - 10.3, 0.1, mat(GRASS, rough=0.95), bevel=0.04)   # yards, front and back
    if alley: box(0, d / 2 - 1.3, 0, W, 2.2, 0.05, mat("alley", rough=0.9), bevel=0.02)
    return f + 13.5                                                                        # y of the building line

def lawn(x, y, w, d, col=GRASS): box(x, y, 0, w, d, 0.1, mat(col, rough=0.95), bevel=0.04)
def paved(x, y, w, d, col="curb", h=0.13): box(x, y, 0, w, d, h, mat(col, rough=0.85), bevel=0.03)

# ---------- props ----------
def tree(x, y, s=1.0, z=0.1, seed=None):
    r = random.Random(seed if seed is not None else int(x * 31 + y * 17))
    cyl(x, y, z, 0.16 * s, 2.4 * s, "trunk", verts=8, bevel=0)
    g = [mat(c, rough=0.9) for c in ("#7fa36b", "#6b9159", "#8db27a")]
    sphere(x, y, z + 3.4 * s, 1.55 * s, g[0], sub=2, sz=1.05)
    for k in range(3):
        a = r.random() * 6.28
        sphere(x + math.cos(a) * 0.9 * s, y + math.sin(a) * 0.9 * s, z + (2.9 + r.random() * 1.2) * s, (0.85 + r.random() * 0.3) * s, g[1 + k % 2], sub=2)

def shrub(x, y, s=1.0): sphere(x, y, 0.4 * s, 0.6 * s, mat("#6b9159", rough=0.9), sub=2, sz=0.75)

def lamp(x, y, h=6.5):
    cyl(x, y, 0.1, 0.09, h, "steel", verts=8, bevel=0); cyl(x, y, 0.1, 0.2, 0.5, "steel", verts=8, bevel=0.02)
    box(x, y - 0.9, h, 0.12, 1.9, 0.1, "steel", bevel=0.02); box(x, y - 1.7, h - 0.12, 0.34, 0.6, 0.14, mat("#fff4d6", rough=0.4, emit=0.8), bevel=0.03)

def hydrant(x, y):
    cyl(x, y, 0.1, 0.16, 0.6, "star", verts=10, bevel=0.03); sphere(x, y, 0.72, 0.17, "star", sub=2)

PS = [1.0]   # people are drawn a little larger than life in the wide scenes, so they read at banner size
def person(x, y, col=None, h=1.0, z=0.14, skin=None):
    h *= PS[0]
    r = random.Random(int(x * 97 + y * 13))
    col = col or r.choice(["navy", "star", "gold", "#5f7d8c", "green", "#8a5a36", "#7a5ea8", "#e07a3f"])
    skin = skin or r.choice(["#e8c9a8", "#c99b77", "#8d5b3e", "#f1d6ba", "#a9764f"])
    cyl(x, y, z, 0.2 * h, 0.75 * h, mat(DARK, rough=0.7), verts=10, bevel=0.04, r2=0.17 * h)           # legs
    cyl(x, y, z + 0.72 * h, 0.27 * h, 0.72 * h, mat(col, rough=0.65), verts=10, bevel=0.06, r2=0.2 * h)  # coat
    sphere(x, y, z + 1.66 * h, 0.21 * h, mat(skin, rough=0.6), sub=2)

def crowd(x0, x1, y0, y1, n, h=1.0, seed=2, z=0.14):
    r = random.Random(seed)
    for _ in range(n): person(x0 + r.random() * (x1 - x0), y0 + r.random() * (y1 - y0), h=h, z=z)

def car(x, y, col="#5f7d8c", z=0.05, flip=False, L=4.3):
    s = -1 if flip else 1
    box(x, y, z + 0.28, L, 1.8, 0.62, mat(col, rough=0.35, spec=0.6), bevel=0.2)
    box(x - s * 0.25, y, z + 0.86, L * 0.52, 1.6, 0.56, mat("#4f6f8f", rough=0.15, spec=0.7), bevel=0.2)
    for dx in (-L * 0.3, L * 0.3):
        for dy in (-0.86, 0.86):
            o = cyl(x + dx, y + dy, z, 0.33, 0.22, mat("#1f2227", rough=0.8), verts=14, bevel=0.03); o.location = (x + dx, y + dy, z + 0.33); o.rotation_euler = (math.pi / 2, 0, 0)
    box(x + s * L / 2, y, z + 0.5, 0.06, 1.3, 0.16, mat("#fff4d6", rough=0.3, emit=0.6), bevel=0.02)

def cars(x0, x1, y, seed=1, gap=6.4, skip=0.25):
    r = random.Random(seed); cols = ["#5f7d8c", "#c9ced3", "#2b5da0", "#8f3b34", "#3d434b", "#e8e4d8", "#6b8f71", "#d7a13b"]
    x = x0
    while x < x1:
        if r.random() > skip: car(x, y, r.choice(cols), flip=r.random() < 0.15)
        x += gap + r.random() * 1.2

def bus(x, y, stripe="navy", L=12.2, z=0.05, body="#f4f5f6", flip=False):
    """A city bus running along x, front at +x. No words; the stripe color tells the agencies apart."""
    s = -1 if flip else 1
    box(x, y, z + 0.4, L, 2.55, 2.75, mat(body, rough=0.35, spec=0.5), bevel=0.3)
    for side in (-1, 1):
        box(x - s * 0.3, y + side * 1.28, z + 1.55, L - 1.6, 0.05, 1.0, mat("#3f5f82", rough=0.15, spec=0.7), bevel=0.01)       # windows
        box(x, y + side * 1.285, z + 0.95, L - 0.3, 0.04, 0.3, stripe, bevel=0.01)
        for k in range(int((L - 1.6) / 1.5)): box(x - s * 0.3 - (L - 1.6) / 2 + k * 1.5, y + side * 1.3, z + 1.55, 0.07, 0.04, 1.0, mat(body, rough=0.4), bevel=0)
        for dx in (L * 0.32, -L * 0.3):
            o = cyl(x + s * dx, y + side * 1.18, z, 0.5, 0.3, mat("#1f2227", rough=0.8), verts=16, bevel=0.03); o.location = (x + s * dx, y + side * 1.18, z + 0.5); o.rotation_euler = (math.pi / 2, 0, 0)
    for dx in (L * 0.42, -L * 0.05): box(x + s * dx, y - 1.3, z + 0.55, 1.0, 0.05, 2.1, mat("#2c4868", rough=0.2, spec=0.7), bevel=0.01)  # doors, curb side
    box(x + s * (L / 2 + 0.01), y, z + 1.4, 0.05, 2.2, 1.25, mat("#3f5f82", rough=0.15, spec=0.7), bevel=0.02)                     # windshield
    box(x + s * (L / 2 + 0.01), y, z + 2.72, 0.05, 1.9, 0.3, mat("#f3b23c", rough=0.4, emit=0.9), bevel=0.01)                      # lit sign (blank)
    box(x - s * 1.0, y, z + 3.15, 3.0, 1.6, 0.3, mat("#dfe2e5", rough=0.5), bevel=0.08)                                           # roof unit

def lcar(x, y, z=0.0, stripe="star", L=14.6, body="#d7dbe0"):
    """One L car along x: silver body, window band, two doors a side, colored stripe, roof gear, trucks."""
    box(x, y, z + 0.55, L, 2.8, 3.1, mat(body, rough=0.32, metal=0.35), bevel=0.3)
    for side in (-1, 1):
        yy = y + side * 1.41
        for k in range(-3, 4):
            if abs(k) == 2: box(x + k * 1.85, yy, z + 0.75, 1.25, 0.05, 2.35, mat("#bfc5cc", rough=0.3, metal=0.4), bevel=0.01); box(x + k * 1.85, yy + side * 0.01, z + 1.9, 0.9, 0.05, 0.95, "glassdk", bevel=0.01)
            else: box(x + k * 1.85, yy, z + 1.85, 1.35, 0.05, 1.05, "glassdk", bevel=0.01)
        box(x, yy, z + 1.35, L - 0.2, 0.04, 0.22, stripe, bevel=0)
    for e in (-1, 1): box(x + e * (L / 2 + 0.01), y, z + 1.7, 0.05, 1.6, 1.3, "glassdk", bevel=0.02)
    box(x, y, z + 3.65, L * 0.5, 1.7, 0.22, mat("#c4c9cf", rough=0.5), bevel=0.06)
    for dx in (-L * 0.32, L * 0.32): box(x + dx, y, z + 0.12, 2.6, 2.3, 0.5, mat("#2d3238", rough=0.7), bevel=0.06)

def ltrain(x, y, z=0.0, cars=2, stripe="star"):
    for k in range(cars): lcar(x + k * 15.3, y, z, stripe)

def commuter(x, y, z=0.0, cars=2, stripe="#e07a3f"):
    """A bi-level commuter train along x: taller steel cars with two rows of windows, a diesel engine at +x."""
    for k in range(cars):
        cx = x + k * 19.5
        box(cx, y, z + 0.6, 18.8, 3.0, 4.3, mat("#b9bfc6", rough=0.35, metal=0.4), bevel=0.25)
        for side in (-1, 1):
            for row in (1.4, 3.3): box(cx, y + side * 1.51, z + row, 16.5, 0.05, 0.8, "glassdk", bevel=0.01)
            box(cx, y + side * 1.515, z + 2.55, 18.8, 0.04, 0.3, stripe, bevel=0)
        for dx in (-6.5, 6.5): box(cx + dx, y, z + 0.12, 2.8, 2.4, 0.55, mat("#2d3238", rough=0.7), bevel=0.06)
    ex = x + cars * 19.5 - 1.2
    box(ex, y, z + 0.6, 16.0, 3.0, 3.9, mat("#3d434b", rough=0.4, metal=0.3), bevel=0.3)
    box(ex + 8.01, y, z + 2.9, 0.05, 2.3, 1.0, "glassdk", bevel=0.02); box(ex, y - 1.515, z + 2.2, 16.0, 0.04, 0.4, stripe, bevel=0); box(ex, y + 1.515, z + 2.2, 16.0, 0.04, 0.4, stripe, bevel=0)
    for dx in (-5.0, 5.0): box(ex + dx, y, z + 0.12, 3.0, 2.4, 0.55, mat("#2d3238", rough=0.7), bevel=0.06)

def track(x0, x1, y, z=0.0, gauge=1.5, bed=True):
    L = x1 - x0; cx = (x0 + x1) / 2
    if bed: box(cx, y, z, L, 3.4, 0.14, mat("#b7b2a8", rough=0.95), bevel=0.05)
    for k in range(int(L / 1.1)): box(x0 + 0.55 + k * 1.1, y, z + 0.14, 0.28, 2.6, 0.1, mat("#7a5d48", rough=0.9), bevel=0.01)
    for side in (-1, 1): box(cx, y + side * gauge / 2, z + 0.24, L, 0.1, 0.14, mat("steel", rough=0.4, metal=0.5), bevel=0.01)

def fence(x0, y0, x1, y1, h=1.1, col="ink", step=0.9):
    L = math.hypot(x1 - x0, y1 - y0); n = max(1, int(L / step)); ang = math.atan2(y1 - y0, x1 - x0)
    for k in range(n + 1):
        t = k / n; box(x0 + (x1 - x0) * t, y0 + (y1 - y0) * t, 0, 0.07, 0.07, h, col, bevel=0)
    box((x0 + x1) / 2, (y0 + y1) / 2, h - 0.12, L, 0.05, 0.06, col, bevel=0, rot=ang)

def board_fence(x0, y0, x1, y1, h=1.7, col="#b89a78"):
    L = math.hypot(x1 - x0, y1 - y0); ang = math.atan2(y1 - y0, x1 - x0)
    box((x0 + x1) / 2, (y0 + y1) / 2, 0, L, 0.1, h, mat(col, rough=0.9), bevel=0.02, rot=ang)

def coins(x, y, n, col="gold", r=1.5, z=0.1):
    m = mat(col, rough=0.35, metal=0.55); rim = mat(col, rough=0.5, metal=0.3)
    rnd = random.Random(int(x * 7 + n))
    for k in range(n):
        ox, oy = (rnd.random() - 0.5) * 0.14, (rnd.random() - 0.5) * 0.14
        cyl(x + ox, y + oy, z + k * 0.5, r, 0.44, m, verts=28, bevel=0.05)
        cyl(x + ox, y + oy, z + k * 0.5 + 0.44, r * 0.78, 0.02, rim, verts=28, bevel=0)

def garage(x, y, w=6.0, d=6.2, col="#e4ddcf", door="-y"):
    box(x, y, 0, w, d, 2.7, mat(col, rough=0.85), bevel=0.05)
    hip(x, y, 2.7, w + 0.5, d + 0.5, 1.1, mat("#6f6b66", rough=0.9))
    yy = y - d / 2 - 0.03 if door == "-y" else y + d / 2 + 0.03
    box(x, yy, 0.05, w * 0.72, 0.06, 2.1, mat("#f1f2f0", rough=0.6), bevel=0.01)
    for k in range(1, 4): box(x, yy - (0.035 if door == "-y" else -0.035), 0.05 + k * 0.52, w * 0.72, 0.02, 0.03, mat("#c9ccc8", rough=0.6), bevel=0)

def porch_stack(x, y, w, floors, fh, z0=1.0, d=2.6, col="#9c7b5c"):
    """The wooden back porches of a Chicago flat building: posts, a deck per floor, rails, and a zigzag stair."""
    m = mat(col, rough=0.9)
    for sx in (-w / 2 + 0.1, w / 2 - 0.1):
        for sy in (-d / 2 + 0.1, d / 2 - 0.1): box(x + sx, y + sy, 0, 0.16, 0.16, z0 + floors * fh + 1.0, m, bevel=0.01)
    for f in range(floors + 1):
        z = z0 + f * fh
        if f < floors:
            box(x, y, z - 0.12, w, d, 0.12, m, bevel=0.01)
            box(x, y + d / 2 - 0.08, z + 0.95, w, 0.06, 0.07, m, bevel=0); box(x + w / 2 - 0.08, y, z + 0.95, 0.06, d, 0.07, m, bevel=0)
            for k in range(int(w / 0.45)): box(x - w / 2 + 0.25 + k * 0.45, y + d / 2 - 0.08, z, 0.04, 0.04, 0.95, m, bevel=0)
        n = 8; top = z; bot = (z0 + (f - 1) * fh) if f > 0 else 0
        for k in range(n):                                                         # one flight below each deck, alternating direction
            t = (k + 0.5) / n; sx = (-1 if f % 2 else 1) * (t - 0.5) * (w - 1.2)
            box(x + sx, y - d / 2 + 0.45, bot + (top - bot) * t - 0.1, (w - 1.2) / n + 0.02, 0.8, 0.08, m, bevel=0)
    box(x, y, z0 + floors * fh + 1.0, w + 0.3, d + 0.3, 0.12, mat("#6f6b66", rough=0.9), bevel=0.02)   # porch roof

def mailboxes(x, y, n, col="navy"):
    w = n * 0.42 + 0.2
    for sx in (-w / 2 + 0.1, w / 2 - 0.1): box(x + sx, y, 0, 0.07, 0.07, 1.0, "steel", bevel=0)
    box(x, y, 0.95, w, 0.1, 0.06, "steel", bevel=0)
    for k in range(n): box(x - w / 2 + 0.31 + k * 0.42, y, 1.0, 0.32, 0.42, 0.36, mat(col, rough=0.5), bevel=0.08)

# ---------- buildings ----------
def bungalow(x, y0, brick="#a65a42", D=11.0, flip=False, roofc="#6f6b66"):
    """A Chicago bungalow: brick over a raised stone base, hipped roof, front dormer, a row of windows, side stair."""
    W = 6.4; cy = y0 + D / 2; s = -1 if flip else 1
    bm_, stone, roof = mat(brick, rough=0.85), mat("#e8e2d6", rough=0.7), mat(roofc, rough=0.9)
    box(x, cy, 0, W, D, 0.9, stone, bevel=0.04); box(x, cy, 0.9, W, D, 2.9, bm_, bevel=0.05)
    box(x, y0 - 0.02, 1.5, W + 0.04, 0.06, 0.14, stone, bevel=0.01)
    hip(x, cy, 3.8, W + 0.9, D + 0.9, 2.1, roof)
    box(x - s * 0.2, y0 + 0.75, 3.6, 2.7, 2.1, 1.6, mat("#eef0f1", rough=0.6), bevel=0.05); pitched(x - s * 0.2, y0 + 0.75, 5.2, 3.1, 2.4, 0.9, roof)
    for dx in (-0.75, 0.35): pane(x - s * 0.2 + dx, y0 - 0.31, 4.0, 0.7, 0.9)
    for dx in (-2.3, -1.4, -0.5): pane(x + s * dx, y0 - 0.01, 1.7, 0.72, 1.4)
    box(x + s * 1.9, y0 - 0.02, 0.9, 1.5, 0.1, 2.3, stone, bevel=0.02); box(x + s * 1.9, y0 - 0.09, 0.95, 1.0, 0.06, 1.95, mat("#5b3a26", rough=0.5), bevel=0.01)
    for k in range(4): box(x + s * 1.9, y0 - 0.4 - k * 0.32, 0.9 - (k + 1) * 0.22, 1.5, 0.34, 0.22, stone, bevel=0.01)
    for sx in (1.0, 2.8): box(x + s * sx, y0 - 0.85, 0, 0.3, 1.5, 1.0, bm_, bevel=0.03)
    for c in range(int((D - 2) / 2.6)): pane(x + W / 2 + 0.01, y0 + 1.6 + c * 2.6, 1.7, 0.9, 1.3, face="+x")
    box(x - s * 2.2, y0 + D * 0.7, 3.6, 0.6, 0.6, 2.6, bm_, bevel=0.03)
    shrub(x - s * 1.4, y0 - 0.7); shrub(x - s * 2.5, y0 - 0.6, 0.85)
    return 5.9

def flats(x, y0, floors=3, wall="#d8d0bd", W=6.4, D=14.0, flip=False, FH=3.1, trim="#efe9dc", brick_side=None, porch=False):
    """A Chicago two- or three-flat: stone or brick front, a full-height angled bay, belt courses, cornice with a stepped
    parapet, a stoop with an iron rail; plain brick side walls with windows."""
    s = -1 if flip else 1; cy = y0 + D / 2; H = floors * FH
    front, tr = mat(wall, rough=0.8), mat(trim, rough=0.7); side = mat(brick_side or wall, rough=0.85)
    box(x, cy, 0, W, D, 1.0, mat("#c9c0aa", rough=0.85), bevel=0.04)
    box(x, cy + 0.2, 1.0, W, D - 0.4, H, side, bevel=0.04); box(x, y0 + 0.25, 1.0, W, 0.5, H, front, bevel=0.03)
    bx = x - s * 1.35
    bay(bx, y0, 1.0, 3.2, H + 0.4, 1.0, front); bay_side_windows(bx, y0, 1.7, 3.2, 1.0, 1.6, floors, FH)
    for f in range(floors):
        z = 1.0 + f * FH + 0.7
        pane(bx, y0 - 1.01, z, 0.85, 1.6); pane(x + s * 1.75, y0 - 0.01, z, 0.85, 1.6)
        box(x, y0 - 0.05, z - 0.22, W + 0.04, 0.14, 0.12, tr, bevel=0)
        for c in range(int((D - 2.5) / 2.8)): pane(x + W / 2 + 0.01, y0 + 1.8 + c * 2.8, z, 0.95, 1.5, face="+x")
    box(x, cy, 1.0 + H, W + 0.35, D + 0.2, 0.5, tr, bevel=0.05)
    box(x - s * 0.2, y0 + 0.25, 1.5 + H, 2.4, 0.45, 0.7, tr, bevel=0.04); box(x - s * 0.2, y0 + 0.25, 2.2 + H, 1.1, 0.45, 0.35, tr, bevel=0.04)
    box(x, cy + 0.3, 1.05 + H, W - 0.6, D - 1.2, 0.47, mat("#8e8b86", rough=0.95), bevel=0.02)
    dx = x + s * 1.75
    box(dx, y0 - 0.06, 1.0, 1.4, 0.12, 2.5, tr, bevel=0.02); box(dx, y0 - 0.13, 1.05, 0.95, 0.06, 2.1, mat("#5b3a26", rough=0.6), bevel=0.01)
    for k in range(4): box(dx, y0 - 0.42 - k * 0.34, 1.0 - (k + 1) * 0.25, 1.5, 0.36, 0.25, tr, bevel=0.01)
    for sx in (-0.75, 0.75):
        for k in range(4): box(dx + sx, y0 - 0.42 - k * 0.34, 1.0 - (k + 1) * 0.25, 0.05, 0.05, 1.0, "ink", bevel=0)
    box(x + s * 2.6, cy + D * 0.2, 1.0 + H, 0.7, 0.7, 1.6, side, bevel=0.04)
    if porch: porch_stack(x, y0 + D + 1.3, W - 0.6, floors, FH)
    return 1.0 + H + 0.5

def sixflat(x, y0, wall="#d4a55c", W=13.0, D=13.0, FH=3.1, floors=3):
    """A Chicago six-flat on a double lot: two bays, arched stone entry with a balcony over it, limestone belts."""
    brick, stone = mat(wall, rough=0.85), mat("#ece4d2", rough=0.7); cy = y0 + D / 2; H = floors * FH
    box(x, cy, 0, W, D, 1.0, stone, bevel=0.04); box(x, cy, 1.0, W, D, H, brick, bevel=0.04)
    for sx in (-4.2, 4.2):
        bay(x + sx, y0, 1.0, 3.6, H, 1.0, brick); bay_side_windows(x + sx, y0, 1.7, 3.6, 1.0, 1.6, floors, FH)
    for f in range(floors):
        z = 1.0 + f * FH + 0.7
        for sx in (-4.2, 4.2): pane(x + sx, y0 - 1.01, z, 0.9, 1.6)
        for sx in (-1.5, 1.5): pane(x + sx, y0 - 0.01, z, 0.75, 1.6)
        box(x, y0 - 0.04, z - 0.25, W + 0.04, 0.12, 0.14, stone, bevel=0)
        for c in range(int((D - 2.5) / 2.8)): pane(x + W / 2 + 0.01, y0 + 1.8 + c * 2.8, z, 0.95, 1.5, face="+x")
    box(x, y0 - 0.1, 1.0, 2.2, 0.2, 2.9, stone, bevel=0.03)
    o = cyl(x, y0 - 0.14, 2.9, 0.62, 0.05, mat(DARK, rough=0.5), verts=24, bevel=0); o.location = (x, y0 - 0.14, 3.1); o.rotation_euler = (math.pi / 2, 0, 0)
    box(x, y0 - 0.16, 1.05, 1.2, 0.06, 2.05, mat(DARK, rough=0.5), bevel=0.01)
    box(x, y0 - 0.45, 1.0 + FH + 0.5, 2.4, 0.8, 0.18, stone, bevel=0.03)
    for k in range(8): box(x - 1.05 + k * 0.3, y0 - 0.8, 1.0 + FH + 0.68, 0.08, 0.08, 0.5, stone, bevel=0)
    box(x, cy, 1.0 + H, W + 0.4, D + 0.3, 0.5, stone, bevel=0.05); box(x, cy, 1.05 + H, W - 0.6, D - 0.6, 0.47, mat("#8e8b86", rough=0.95), bevel=0.02)
    for k in range(3): box(x, y0 - 0.5 - k * 0.34, 1.0 - (k + 1) * 0.33, 2.2, 0.36, 0.33, stone, bevel=0.01)
    return 1.0 + H + 0.5

def cottage(x, y0, col="#8fa9b8", D=9.0, flip=False):
    """A frame worker's cottage: gable to the street, siding, a porch with posts."""
    W = 6.0; s = -1 if flip else 1; cy = y0 + D / 2; wall = mat(col, rough=0.8); white = mat("#f3f1ea", rough=0.7)
    box(x, cy, 0, W, D, 0.7, mat("#c9c0aa", rough=0.85), bevel=0.03); box(x, cy, 0.7, W, D, 5.2, wall, bevel=0.04)
    for k in range(13): box(x, y0 - 0.01, 0.9 + k * 0.4, W, 0.03, 0.03, mat("#ffffff", rough=0.8, alpha=1), bevel=0)          # siding lines
    gable(x, cy, 5.9, W, D, 2.4, mat("#5f5b57", rough=0.9))
    tri = bpy.data.meshes.new("tri"); tri.from_pydata([(x - W / 2, y0 - 0.02, 5.9), (x + W / 2, y0 - 0.02, 5.9), (x, y0 - 0.02, 8.1)], [], [(0, 1, 2)]); _obj(tri, "tri", wall, 0)
    pane(x, y0 - 0.03, 6.3, 0.8, 0.9)
    for dx in (-1.6, 0.0): pane(x + s * dx, y0 - 0.01, 3.6, 0.8, 1.5)
    pane(x - s * 1.5, y0 - 0.01, 1.3, 0.9, 1.5)
    box(x + s * 1.5, y0 - 0.06, 0.7, 1.0, 0.06, 2.1, mat("#8f3b34", rough=0.6), bevel=0.01)
    box(x, y0 - 1.0, 0, W, 2.0, 0.7, white, bevel=0.03); box(x, y0 - 1.0, 3.0, W + 0.3, 2.3, 0.18, mat("#5f5b57", rough=0.9), bevel=0.03)
    for sx in (-W / 2 + 0.2, 0, W / 2 - 0.2): box(x + sx, y0 - 1.85, 0.7, 0.16, 0.16, 2.3, white, bevel=0.01)
    for k in range(3): box(x + s * 1.5, y0 - 2.2 - k * 0.3, 0.7 - (k + 1) * 0.23, 1.4, 0.32, 0.23, white, bevel=0.01)
    for c in range(3): pane(x + W / 2 + 0.01, y0 + 1.6 + c * 2.6, 1.5, 0.9, 1.4, face="+x"); pane(x + W / 2 + 0.01, y0 + 1.6 + c * 2.6, 3.9, 0.9, 1.3, face="+x")
    return 8.3

def midrise(x, y0, W=18.0, floors=5, D=13.0, panel="#d7dadd", accent=("#2f86c9", "#f0a43a", "#f2c53d", "#41b6e6"), shop=True, FH=3.0, seed=5,
            balconies=True, col2=None, aff=0.0):
    """A new mid-rise: storefront glass with awnings at the street, paneled floors above with colored window accents,
    balconies, a parapet and roof gear."""
    r = random.Random(seed); cy = y0 + D / 2; g0 = 4.2 if shop else 0.6
    pm, dark = mat(panel, rough=0.6), mat("#4a4f57", rough=0.6)
    box(x, cy, 0, W, D, g0, dark, bevel=0.04)
    if shop:
        n = max(2, int(W / 4.5))
        for c in range(n):
            cx = x - W / 2 + W * (c + 0.5) / n; ww = W / n - 0.9
            box(cx, y0 - 0.03, 0.35, ww, 0.06, 2.9, mat("#9fc7e2", rough=0.1, spec=0.6), bevel=0.01)
            box(cx, y0 - 0.5, 3.35, ww + 0.2, 1.0, 0.14, mat(accent[c % len(accent)], rough=0.6), bevel=0.03)                    # awning
        box(x, y0 - 0.06, 0.35, 1.3, 0.06, 2.6, mat(DARK, rough=0.4), bevel=0.01)
    else:                                                                                   # a plain front door under a small canopy
        dx = x + W * 0.25
        box(dx, y0 - 0.05, 0.1, 1.2, 0.08, 2.3, mat("#9fc7e2", rough=0.1, spec=0.6), bevel=0.01); box(dx, y0 - 0.6, 2.55, 1.9, 1.2, 0.14, mat(accent[0], rough=0.6), bevel=0.03)
    box(x, cy, g0, W, D, floors * FH, pm, bevel=0.04)
    if col2: box(x + W * 0.3, cy - 0.15, g0, W * 0.4 + 0.02, D + 0.3, floors * FH + 0.01, mat(col2, rough=0.6), bevel=0.04)
    n = max(3, int(W / 2.5))
    for f in range(floors):
        z = g0 + f * FH + 0.7
        for c in range(n):
            cx = x - W / 2 + W * (c + 0.5) / n
            green = r.random() < aff                                                          # an affordable home: a lit green window
            pane(cx, y0 - (0.16 if col2 and cx > x + W * 0.1 else 0.0), z, 0.62, 1.7, frame="#1e8a47" if green else DARK, fw=0.16 if green else 0.05,
                 glass=mat("#57d68a", rough=0.3, emit=1.6) if green else "glassdk")
            if green: box(cx, y0 - 0.5, z - 0.3, 1.5, 1.0, 0.14, mat("#2e9d57", rough=0.6), bevel=0.03)
            if not aff and r.random() < 0.4: box(cx + 0.9, y0 - (0.2 if col2 and cx > x + W * 0.1 else 0.04), z, 0.35, 0.06, 1.7, mat(r.choice(accent), rough=0.5), bevel=0.01)
            if balconies and c % 3 == 1 and f > 0 and not (col2 and cx > x + W * 0.1):
                box(cx, y0 - 0.6, z - 0.25, 2.0, 1.2, 0.12, mat("#eef0f1", rough=0.6), bevel=0.02)
                box(cx, y0 - 1.17, z - 0.13, 2.0, 0.05, 0.95, mat("#9fc7e2", rough=0.1, alpha=0.55, spec=0.6), bevel=0)
        for c in range(max(2, int(D / 3.2))): pane(x + W / 2 + 0.01, y0 + 1.6 + c * 3.2, z, 0.9, 1.7, face="+x", frame=DARK, fw=0.05)
    top = g0 + floors * FH
    box(x, cy, top, W + 0.2, D + 0.2, 0.45, mat("#eef0f1", rough=0.6), bevel=0.04); box(x, cy, top + 0.05, W - 0.6, D - 0.6, 0.42, mat("#8e8b86", rough=0.95), bevel=0.02)
    box(x - W * 0.2, cy + 1.0, top + 0.45, 3.0, 3.0, 1.9, mat("#b9bcbf", rough=0.7), bevel=0.05)                                     # elevator overrun
    for k in range(2 if W >= 10 else 1): box(x + W * 0.15 + k * 2.0, cy, top + 0.45, 1.4, 1.4, 0.9, mat("#c9ced3", rough=0.5, metal=0.3), bevel=0.08)
    return top + 0.45

def glass_tower(x, y0, W=14.0, D=12.0, floors=16, FH=3.0, glass="#6f93b5", frame="#2d3238", podium=2):
    cy = y0 + D / 2; g, fr = mat(glass, rough=0.12, spec=0.7), mat(frame, rough=0.45, metal=0.3)
    if podium: box(x, cy, 0, W + 4, D + 2, podium * 4.0, mat("#c9c4ba", rough=0.7), bevel=0.06); box(x, y0 - 1.03, 0.4, W + 2.6, 0.06, 3.0, mat("#9fc7e2", rough=0.1, spec=0.6), bevel=0.01)
    z0 = podium * 4.0; H = floors * FH
    box(x, cy, z0, W, D, H, g, bevel=0.04)
    for k in range(int(W / 1.75) + 1): box(x - W / 2 + k * W / int(W / 1.75), y0 - 0.04, z0, 0.07, 0.1, H, fr, bevel=0)
    for k in range(int(D / 1.75) + 1): box(x + W / 2 + 0.04, y0 + k * D / int(D / 1.75), z0, 0.1, 0.07, H, fr, bevel=0)
    for f in range(floors + 1):
        box(x, y0 - 0.03, z0 + f * FH - 0.06, W + 0.04, 0.08, 0.12, fr, bevel=0); box(x + W / 2 + 0.03, cy, z0 + f * FH - 0.06, 0.08, D + 0.04, 0.12, fr, bevel=0)
    box(x, cy, z0 + H, W - 3, D - 3, 1.8, fr, bevel=0.05)
    return z0 + H + 1.8

def frame_up(x, y0, W, D, floors, FH=3.2, done=0, col="#d7dadd", seed=3):
    """A building going up: finished floors below (with windows), bare concrete slabs and columns above."""
    cy = y0 + D / 2; conc = mat("#c2c0b8", rough=0.9)
    if done:
        box(x, cy, 0, W, D, done * FH, mat(col, rough=0.6), bevel=0.04)
        n = max(3, int(W / 2.6))
        for f in range(done):
            for c in range(n): pane(x - W / 2 + W * (c + 0.5) / n, y0, f * FH + 0.8, 0.7, 1.6, frame=DARK, fw=0.05)
            for c in range(max(2, int(D / 3.2))): pane(x + W / 2 + 0.01, y0 + 1.6 + c * 3.2, f * FH + 0.8, 0.9, 1.6, face="+x", frame=DARK, fw=0.05)
    nx, ny = max(2, int(W / 4.5)), max(2, int(D / 4.5))
    for f in range(done, floors):
        z = f * FH
        box(x, cy, z, W, D, 0.28, conc, bevel=0.03)
        for i in range(nx + 1):
            for j in range(ny + 1): box(x - W / 2 + 0.3 + i * (W - 0.6) / nx, y0 + 0.3 + j * (D - 0.6) / ny, z + 0.28, 0.4, 0.4, FH - 0.28, conc, bevel=0.02)
        if f < floors - 1:                                                                    # orange safety rail
            box(x, y0 + 0.05, z + 1.2, W, 0.04, 0.05, mat("#e07a3f", rough=0.6), bevel=0); box(x + W / 2 - 0.05, cy, z + 1.2, 0.04, D, 0.05, mat("#e07a3f", rough=0.6), bevel=0)
    box(x, cy, floors * FH, W, D, 0.28, conc, bevel=0.03)
    return floors * FH + 0.3

def el_station(x, y, z=7.0, L=30, col="navy"):
    """An elevated station around a track that runs along x at height z: two side platforms, canopies, stairs to the street."""
    wood = mat("#b89a78", rough=0.9)
    for side in (-1, 1):
        py = y + side * 4.3
        box(x, py, z + 0.9, L, 3.2, 0.3, wood, bevel=0.03)
        for k in range(int(L / 5) + 1):
            px = x - L / 2 + 0.6 + k * (L - 1.2) / int(L / 5)
            box(px, py + side * 1.4, 0, 0.3, 0.3, z + 0.9, "steel", bevel=0.02)
            box(px, py + side * 1.2, z + 1.2, 0.14, 0.14, 3.0, "steel", bevel=0)
        box(x, py + side * 0.3, z + 4.2, L - 4, 3.0, 0.16, mat(col, rough=0.5), bevel=0.04)
        box(x, py + side * 1.55, z + 1.2, L, 0.06, 1.1, mat("#eef0f1", rough=0.6), bevel=0)
    for k in range(14):                                                                      # a stair down to the sidewalk on the street side
        t = k / 13; box(x + L / 2 + 0.6 + t * 7.0, y - 4.3, (z + 0.9) * (1 - t) - 0.1, 0.56, 2.0, 0.12, "steel", bevel=0)
    box(x + L / 2 + 4.2, y - 5.35, 0, 7.6, 0.06, 0.01, "steel", bevel=0)

def star(x, y, z, r=1.0, m="star", thick=0.25, upright=True):
    """Chicago's six-point star as a little solid, standing up facing -y (or flat on the ground)."""
    pts = []
    for k in range(12):
        a = math.pi / 2 + k * math.pi / 6; rr = r if k % 2 == 0 else r * 0.45
        pts.append((math.cos(a) * rr, math.sin(a) * rr))
    me = bpy.data.meshes.new("star"); n = 12
    if upright: vs = [(x + px, y - thick / 2, z + py) for px, py in pts] + [(x + px, y + thick / 2, z + py) for px, py in pts]
    else: vs = [(x + px, y + py, z) for px, py in pts] + [(x + px, y + py, z + thick) for px, py in pts]
    me.from_pydata(vs, [], [tuple(range(n)), tuple(reversed(range(n, 2 * n)))] + [(i, n + i, n + (i + 1) % n, (i + 1) % n) for i in range(n)]); me.update()
    import bmesh as _b
    bm = _b.new(); bm.from_mesh(me); _b.ops.recalc_face_normals(bm, faces=bm.faces); bm.to_mesh(me); bm.free()
    return _obj(me, "star", m, 0.03)

def fit(cam, aspect, margin=1.05):
    from mathutils import Vector
    bpy.context.view_layer.update()
    inv = cam.matrix_world.inverted(); xs, ys = [], []
    for o in bpy.context.scene.objects:
        if o.type != "MESH" or o.is_shadow_catcher: continue
        for c in o.bound_box:
            v = inv @ (o.matrix_world @ Vector(c)); xs.append(v.x); ys.append(v.y)
    w, h = max(xs) - min(xs), max(ys) - min(ys)
    scale = max(w, h * aspect) * margin
    cam.data.ortho_scale = scale; cam.data.shift_x = (max(xs) + min(xs)) / 2 / scale; cam.data.shift_y = (max(ys) + min(ys)) / 2 / scale
    return scale, cam.data.shift_x, cam.data.shift_y
