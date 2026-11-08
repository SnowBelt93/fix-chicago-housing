"""Illustrations for the Learn page, one per topic, in the icon set's look (clay or ink).
    python3.11 tools/art/learn.py <name|all> <outdir> [style] [width height]
Wide dioramas (3:1). No words in the pictures: the page carries the text, so translations work."""
import sys, os, math, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy
from kit import *
from icons import pitched, ink_style

def base(w=84, d=22):
    box(0, 0, -1.2, w, d, 0.9, mat("earth", rough=0.95), bevel=0.4)
    box(0, 0, -0.35, w, d, 0.35, mat("ground", rough=0.9), bevel=0.3)
    box(0, -d / 2 + 2.6, 0, w - 0.4, 3.0, 0.12, mat("curb", rough=0.85), bevel=0.04)     # sidewalk along the front

def person(x, y, col=None, h=1.0):
    col = col or random.choice(["navy", "star", "gold", "#5f7d8c", "green", "#8a5a36"])
    cyl(x, y, 0.12, 0.28 * h, 1.1 * h, mat(col, rough=0.6), verts=10, bevel=0.05, r2=0.22 * h)
    sphere(x, y, 0.12 + 1.35 * h, 0.24 * h, mat("#e8c9a8", rough=0.6), sub=2)

def bungalow(x, y, w=7, d=10, col="grey"):
    box(x, y, 0, w, d, 3.6, col, bevel=0.06)
    pitched(x, y, 3.6, w + 0.6, d + 0.4, 2.0, mat("roof", rough=0.8))
    windows(x, y, 0.8, w, d, 2.4, 1, face="-y", glass="glass", cols=2, band=0.6)

def block(x, y, w, d, floors, col, fh=3.0):
    m = mat(col, rough=0.6) if not isinstance(col, bpy.types.Material) else col
    box(x, y, 0, w, d, floors * fh, m, bevel=0.08)
    box(x, y, floors * fh, w + 0.3, d + 0.3, 0.3, "white", bevel=0.04)
    for f in range(floors):
        n = max(2, int(w / 2.6))
        for c in range(n):
            box(x - w / 2 + w * (c + 0.5) / n, y - d / 2 - 0.03, 0.6 + f * fh, w / n * 0.55, 0.06, fh * 0.55, "glass", bevel=0.01)

def coins(x, y, n, col="gold"):
    for k in range(n): cyl(x, y, k * 0.62, 1.6, 0.56, mat(col, rough=0.3, metal=0.7), verts=24, bevel=0.04)

def bus(x, y, rot=0.0, L=10):
    c, s = math.cos(rot), math.sin(rot)
    box(x, y, 0.35, L, 2.5, 2.6, mat("#f4f5f6", rough=0.35, metal=0.2), bevel=0.35, rot=rot)
    box(x + 1.27 * s, y - 1.27 * c, 1.5, L - 1, 0.05, 0.85, "glassdk", bevel=0.01, rot=rot)
    box(x + 1.28 * s, y - 1.28 * c, 0.85, L - 0.4, 0.04, 0.22, "navy", bevel=0.01, rot=rot)

def train(x, y, z=0, cars=2, stripe="star", rot=0.0):
    c, s = math.cos(rot), math.sin(rot)
    for k in range(cars):
        cx, cy = x + c * k * 15.2, y + s * k * 15.2
        box(cx, cy, z + 0.3, 14.6, 2.8, 3.3, mat("#d7dbe0", rough=0.35, metal=0.4), bevel=0.35, rot=rot)
        box(cx + 1.42 * s, cy - 1.42 * c, z + 2.0, 13.8, 0.05, 1.0, "glassdk", bevel=0.01, rot=rot)
        box(cx + 1.43 * s, cy - 1.43 * c, z + 1.2, 14.6, 0.05, 0.25, stripe, bevel=0.01, rot=rot)

# ---------- scenes ----------
def zoning():
    base()
    bungalow(-27, 1.5)
    flat(-11, 1.5, 0, 9, 12, 3, "brick", fh=3.0, cols=2, cornice="stone")
    block(6, 1.5, 12, 13, 4, "lt6")
    block(25, 1.5, 15, 14, 6, "mid")
    for xx in (-19, -2, 15): tree(xx, -8.0, 0.1, 0.7)

def illegal():
    base()
    random.seed(3)
    xs = [-33, -18, -3, 12, 27]
    for i, x in enumerate(xs):
        if i in (1, 3): flat(x, 1.5, 0, 10, 12, 3, "brick" if i == 1 else "buff", fh=3.0, cols=2, cornice="stone")
        else: bungalow(x, 1.5, w=8)
    box(xs[1], 1.5, -0.05, 11.6, 13.6, 11.2, mat("star", rough=0.4, alpha=0.18), bevel=0.2)     # the one that couldn't be built today
    for x in (-25, 4, 20): tree(x, -8.0, 0.1, 0.7)

def shortage():
    base()
    random.seed(5)
    block(-22, 2, 16, 13, 5, "lt6")
    crane(-12, 6, 0, 19, 14, ang=math.radians(-160), m=mat("star", rough=0.45))
    for x in (6, 20, 34): bungalow(x, 1.5, w=9)
    for k in range(22): person(-12 + k * 1.75, -9.2 + (k % 2) * 0.5)

def rents():
    base()
    for i, (n, h) in enumerate([(1, 16), (2, 11), (3, 6)]):
        x0 = -30 + i * 26
        for j in range(n): block(x0 - 4 + j * 6.5, 3, 5.5, 9, 3 + j, ["buff", "lt6", "mid"][j % 3])
        coins(x0 + 8, -7.5, h)

def prerogative():
    base()
    random.seed(9)
    bungalow(-28, 1.5, w=9); bungalow(26, 1.5, w=9)
    box(0, 1.5, 0, 26, 14, 0.06, mat("#c8d6b4", rough=0.95), bevel=0.05)                  # an empty lot
    for k in range(13):                                                                    # a fence around it
        for side in (-1, 1): box(-13 + k * 2.15, 1.5 + side * 7, 0, 0.18, 0.18, 1.6, "steel", bevel=0)
    box(0, -5.5, 1.2, 26, 0.1, 0.12, "star", bevel=0); box(0, 8.5, 1.2, 26, 0.1, 0.12, "star", bevel=0)
    box(-6, -6.5, 0, 0.12, 0.12, 2.6, "steel", bevel=0); box(-6, -6.55, 2.2, 3.2, 0.06, 1.8, "navy", bevel=0.04)   # blank notice board
    crane(10, 3, 0, 18, 12, ang=math.radians(200), m=mat("#9aa3ad", rough=0.5))
    person(4, -8.5, "navy", 1.3)

def aro():
    base()
    W, D, F = 30, 14, 6
    box(0, 2, 0, W, D, F * 3, mat("lt6", rough=0.6), bevel=0.1)
    random.seed(4)
    for f in range(F):
        for c in range(8):
            aff = random.random() < 0.2
            box(-W / 2 + W * (c + 0.5) / 8, 2 - D / 2 - 0.04, 0.7 + f * 3, W / 8 * 0.55, 0.06, 1.7, mat("#7cc79a", rough=0.4, emit=0.5) if aff else mat("glass"), bevel=0.01)
    box(0, 2, F * 3, W + 0.4, D + 0.4, 0.4, "white", bevel=0.05)
    for x in (-24, 24): tree(x, -8, 0.1, 0.8)

def megaprojects():
    base(d=26)
    box(0, 9, -0.02, 84, 6, 0.1, mat("lake", rough=0.1, spec=0.6), bevel=0)                 # the river
    random.seed(8)
    for x, f in ((-26, 6), (-12, 9), (2, 5), (16, 11), (30, 7)):
        block(x, -1, 9, 9, f, random.choice(["lt6", "mid", "hi", "#8fa3b5"]), fh=2.4)
    crane(-19, 3, 0, 24, 14, ang=math.radians(-150), m=mat("star", rough=0.45))
    crane(23, 3, 0, 30, 14, ang=math.radians(-200), m=mat("star", rough=0.45))

def modes():
    base(d=26)
    bus(-32, -4)
    box(-12, -4, 0.02, 14, 0.15, 0.06, "steel", bevel=0); box(-12, -2.6, 0.02, 14, 0.15, 0.06, "steel", bevel=0)   # streetcar rails
    box(-12, -3.3, 0.3, 11, 2.5, 3.0, mat("#e9a23b", rough=0.4), bevel=0.4); box(-12, -4.57, 1.6, 9.6, 0.05, 0.9, "glassdk", bevel=0)
    box(-12, -3.3, 3.3, 0.1, 0.1, 2.2, "steel", bevel=0)
    el_track([(0, 2), (26, 2)], z=7.0, train=True, train_at=0.05, cars=1, stripe="star")
    box(33, 2, -0.02, 10, 8, 0.6, mat("#5b6470", rough=0.6), bevel=0.05)                    # subway entrance
    box(33, -1.6, 0, 6, 0.3, 3.4, "steel", bevel=0.05); box(33, 1, 3.2, 6.4, 6.4, 0.25, mat("glass", rough=0.2), bevel=0.05)
    box(33, -0.4, -0.5, 4, 3.0, 0.1, "ink", bevel=0)

def funding():
    base()
    coins(-20, -1, 30, "navy"); coins(-10, -1, 14, "lt6"); coins(0, -1, 10, "star")
    box(20, 2, 0.02, 30, 0.2, 0.1, "steel", bevel=0); box(20, 4.4, 0.02, 30, 0.2, 0.1, "steel", bevel=0)
    train(10, 3.2, 0.1, cars=2, stripe="lt6")

def nita():
    base(d=30)
    box(0, 0, 0, 12, 12, 0.6, "stone", bevel=0.1); box(0, 0, 0.6, 10, 10, 4.0, mat("lt6", rough=0.3, alpha=0.5), bevel=0.1)
    for a in range(4):
        ang = a * math.pi / 2 + math.pi / 4
        bus(math.cos(ang) * 14, math.sin(ang) * 10, rot=ang + math.pi / 2, L=9)
    box(0, 12, 0.02, 84, 0.2, 0.1, "steel", bevel=0); box(0, 14.2, 0.02, 84, 0.2, 0.1, "steel", bevel=0)
    train(-34, 13.1, 0.1, cars=2, stripe="star"); train(18, 13.1, 0.1, cars=1, stripe="navy")

def riders():
    base()
    random.seed(12)
    box(-6, 1, 0, 40, 6, 1.1, "stone", bevel=0.1)                                            # platform
    for x in (-24, 12): box(x, 3.4, 1.1, 0.3, 0.3, 3.6, "steel", bevel=0)
    box(-6, 3.4, 4.6, 40, 2.6, 0.25, mat("navy", rough=0.5), bevel=0.05)                       # canopy
    for k in range(26): person(-24 + random.random() * 36, -0.5 + random.random() * 2.5, h=0.95)
    train(-30, 6.3, 0.1, cars=3, stripe="star")

SCENES = {k: v for k, v in globals().items() if k in ("zoning", "illegal", "shortage", "rents", "prerogative", "aro", "megaprojects", "modes", "funding", "nita", "riders")}

def build(name, out, style="ink", w=1500, h=500):
    reset(); random.seed(1)
    SCENES[name]()
    rig(56, target=(0, 0, 2), elev=26, azim=-62, sun=(48, -30), sun_e=3.2 if style == "clay" else 2.2, world="#eef3f8", world_e=0.6 if style == "clay" else 1.1)
    bpy.context.scene.camera.data.ortho_scale = 100
    shadow_catcher(z=-1.2)
    if style == "ink": ink_style()
    render(os.path.abspath(out), w, h, samples=40)

if __name__ == "__main__":
    name, outdir = sys.argv[1], sys.argv[2]
    style = sys.argv[3] if len(sys.argv) > 3 else "ink"
    w, h = (int(sys.argv[4]), int(sys.argv[5])) if len(sys.argv) > 5 else (1500, 500)
    os.makedirs(outdir, exist_ok=True)
    for n in (SCENES if name == "all" else [name]): build(n, os.path.join(outdir, n + ".png"), style, w, h)
