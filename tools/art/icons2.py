"""The full Shape Chicago icon set in the clay look: one small diorama per housing policy and transit mode.
    python3.11 tools/art/icons2.py <name|all> <outdir> [size]
Adds to icons.py's six samples. No text in any icon (the page names them, so translations work)."""
import sys, os, math, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy
from kit import *
import icons
from icons import tile, lawn, walk, pitched, T
from learn import person, bus, train, block, coins, bungalow

def ribbon(x, y, z, w, m="star"): box(x, y, z, w, 0.12, 0.35, m, bevel=0.03)
def stopbar(x, y, w=6, rot=0.0):
    box(x - w / 2, y, 0, 0.35, 0.35, 1.4, "steel", bevel=0.03)
    for k in range(6): box(x - w / 2 + (k + 0.5) * w / 6, y, 1.2, w / 6, 0.22, 0.35, "star" if k % 2 == 0 else "white", bevel=0.02)

# housing policies
def build():
    tile(); lawn(0, 0.6, 9.4, 5.0); walk(0, -3.9, T, 1.4)
    flat(-2.3, 1.0, 0, 4.4, 5.0, 2, "brick", fh=2.0, cols=2, cornice="stone")
    flat(2.4, 1.0, 0, 4.4, 5.0, 3, "buff", fh=1.9, cols=2, cornice="stone")
def aro():
    tile(); walk(0, -3.8, T, 1.6)
    W, D, F = 6.4, 5.6, 7
    box(0, 0.6, 0, W, D, F * 1.05, mat("lt6", rough=0.6), bevel=0.1)
    random.seed(3)
    for f in range(F):
        for c in range(3):
            green = (f, c) in ((1, 0), (3, 2), (4, 1), (6, 0), (2, 2))
            box(-W / 2 + W * (c + 0.5) / 3, 0.6 - D / 2 - 0.04, 0.3 + f * 1.05, 1.1, 0.06, 0.6, mat("#6cc58d", rough=0.4, emit=0.9) if green else "glass", bevel=0.01)
            box(-W / 2 - 0.04, 0.6 - D / 2 + D * (c + 0.5) / 3, 0.3 + f * 1.05, 0.06, 1.1, 0.6, mat("#6cc58d", rough=0.4, emit=0.9) if green else "glass", bevel=0.01)
    box(0, 0.6, F * 1.05, W + 0.2, D + 0.2, 0.25, "white", bevel=0.04)
def permits():
    tile(); walk(0, -3.8, T, 1.6)
    block(0, 1.2, 6, 5, 3, "buff", fh=1.6)
    for side in (-1, 1):
        box(side * 2.6, -3.0, 0, 0.25, 0.25, 1.8, "steel", bevel=0.02)
        o = ribbon(side * 1.5, -3.0, 1.4, 2.0);
    sphere(0, -3.0, 1.55, 0.25, "star", sub=2)   # the cut
def mega():
    tile(); walk(0, -3.9, T, 1.4)
    block(-2.4, 0.8, 3.2, 3.2, 8, "mid", fh=1.0); block(1.4, 1.6, 3.0, 3.0, 11, "hi", fh=1.0); block(3.4, -1.2, 2.4, 2.4, 5, "lt6", fh=1.0)
    crane(-0.4, 3.6, 0, 13.5, 6, ang=math.radians(-150), m=mat("star", rough=0.45))
def vland():
    tile(); walk(0, -3.9, T, 1.4); lawn(0, 0.6, 9.4, 5.6)
    for x in (-1.6, 1.6):            # a new two-flat going up: posts and floors
        for y in (-1.4, 2.6): box(x, y, 0, 0.25, 0.25, 4.2, mat("#c89a62", rough=0.8), bevel=0.02)
    for z in (0, 2.0, 4.0): box(0, 0.6, z, 3.6, 4.4, 0.25, mat("#d9b98a", rough=0.8), bevel=0.03)
    box(0, 0.6, 0, 3.6, 4.4, 2.0, "brick", bevel=0.05)
    coins(3.4, -2.6, 5)
def pre():
    tile(); walk(0, -3.9, T, 1.4)
    bungalow(-3.0, 1.4, w=3.6, d=4.6); bungalow(3.1, 1.4, w=3.6, d=4.6)
    box(0, 0.8, 0, 2.6, 5.2, 0.05, mat("#c8d6b4", rough=0.95), bevel=0.03)
    stopbar(0.0, -2.2, w=3.4)
    person(1.9, -2.8, "navy", 1.4)
def mpls():
    tile(); lawn(0, 0.6, 9.4, 5.0); walk(0, -3.9, T, 1.4)
    box(0, 1.0, 0, 6.6, 4.6, 3.4, mat("#e6dfcf", rough=0.85), bevel=0.06)
    pitched(0, 1.0, 3.4, 7.0, 5.0, 1.8, mat("roof", rough=0.8))
    for k in (-2.2, 0, 2.2): box(k, 1.0 - 2.33, 0.1, 0.9, 0.06, 1.7, "navy", bevel=0.01); box(k, -1.9, 0, 1.0, 0.8, 0.25, "stone", bevel=0.03)
def camb():
    tile(); lawn(0, 0.6, 9.4, 5.0); walk(0, -3.9, T, 1.4)
    bungalow(-3.4, 1.2, w=2.8, d=4.0); bungalow(3.4, 1.2, w=2.8, d=4.0)
    block(0, 1.0, 3.6, 4.4, 4, "lt6", fh=1.5)
def small():
    tile(); walk(0, -3.9, T, 1.4); lawn(0, 0.6, 9.4, 5.0)
    for i, c in enumerate(("brick", "buff", "grey", "brick2")):
        x = -3.3 + i * 2.2
        box(x, 1.0, 0, 2.0, 4.6, 4.2 + (i % 2) * 0.4, c, bevel=0.05); box(x, 1.0, 4.2 + (i % 2) * 0.4, 2.1, 4.7, 0.2, "stone", bevel=0.03)
        box(x, 1.0 - 2.31, 0.1, 0.7, 0.06, 1.4, "navy", bevel=0.01); box(x, 1.0 - 2.31, 2.3, 1.2, 0.06, 1.0, "glass", bevel=0.01)
def park():
    tile(top="street"); walk(0, -3.9, T, 1.4)
    for k in range(3): box(-3.6 + k * 1.6, 1.0, 0.03, 0.12, 4.4, 0.02, "white", bevel=0)
    car(-2.8, 1.0, 0, math.pi / 2, mat("#9aa3ad", rough=0.4, metal=0.3))
    block(2.6, 1.0, 4.2, 5.0, 4, "lt6", fh=1.5)
def comm():
    tile(); walk(0, -3.9, T, 1.6)
    box(0, 0.8, 0, 8.4, 5.0, 1.8, mat("#e8b04a", rough=0.6), bevel=0.06)
    box(0, 0.8 - 2.53, 0.2, 7.6, 0.06, 1.2, "glassdk", bevel=0.01)
    for f in range(3):
        box(0, 1.0, 1.8 + f * 1.5, 7.6, 4.4, 1.5, mat("lt6", rough=0.6), bevel=0.05)
        for c in range(4): box(-3.8 + 7.6 * (c + 0.5) / 4, 1.0 - 2.23, 2.2 + f * 1.5, 1.0, 0.06, 0.8, "glass", bevel=0.01)
    box(0, 1.0, 6.3, 7.8, 4.6, 0.25, "white", bevel=0.04)
def vac():
    tile(); lawn(0, 0.6, 9.4, 5.4); walk(0, -3.9, T, 1.4)
    flat(0, 1.0, 0, 5.4, 4.8, 2, "grey", fh=2.0, cols=2, cornice="stone", glass=mat("#2a3038", rough=0.6))
    for x in (-2.8, 2.8): tree(x, -2.6, 0, s=0.45, m="#9bb38a")
    box(2.6, -3.0, 0, 0.12, 0.12, 1.4, "steel", bevel=0); box(2.6, -3.05, 1.2, 1.2, 0.06, 0.8, "star", bevel=0.03)
def social():
    tile(); walk(0, -3.8, T, 1.6)
    block(0, 0.8, 6.4, 5.4, 5, "#7cbf96", fh=1.3)
    for x in (-2, 0, 2): sphere(x, 0.8, 6.8, 0.6, "tree", sub=2)     # a garden on the roof
    for x in (-3.6, 3.6): tree(x, -2.6, 0, s=0.5)
def down():
    tile(); lawn(0, 0.6, 9.4, 5.0); walk(0, -3.9, T, 1.4)
    box(0, 1.0, 0, 5.0, 4.6, 7.2, mat("#bcd3ec", rough=0.2, alpha=0.3), bevel=0.08)
    bungalow(0, 1.0, w=4.4, d=4.2)
    for i in range(3): box(3.4, -1.6 - i * 0.0, 5.6 - i * 1.6, 0.25, 0.25, 1.0, "star", bevel=0.04)
    bpy.ops.mesh.primitive_cone_add(vertices=4, radius1=0.6, depth=0.8, location=(3.4, -1.6, 1.0), rotation=(math.pi, 0, 0)); bpy.context.object.data.materials.append(mat("star"))
def pmin():
    tile(top="street")
    for k in range(5): box(-3.6 + k * 1.8, 0.0, 0.03, 0.12, 4.0, 0.02, "white", bevel=0)
    for k in range(4): car(-2.7 + k * 1.8, 0.0, 0, math.pi / 2, mat(["#9aa3ad", "#c9473a", "#e6e8eb", "#2b5da0"][k], rough=0.4, metal=0.3))
    bungalow(0, 3.6, w=3.0, d=2.4)
def mora():
    tile(); walk(0, -3.9, T, 1.4); lawn(0, 0.8, 9.4, 5.0)
    for x in (-1.6, 1.6):
        for y in (-0.6, 2.4): box(x, y, 0, 0.25, 0.25, 2.4, mat("#c89a62", rough=0.8), bevel=0.02)
    box(0, 0.9, 0, 3.6, 3.4, 0.25, mat("#d9b98a", rough=0.8), bevel=0.03)
    stopbar(0, -2.6, w=6.0)
    cyl(3.6, 2.6, 0, 0.6, 0.15, "stone", verts=16); cyl(3.6, 2.6, 0.15, 0.55, 1.0, mat("glass", rough=0.1, alpha=0.6), verts=16, r2=0.05); cyl(3.6, 2.6, 1.15, 0.05, 1.0, mat("glass", rough=0.1, alpha=0.6), verts=16, r2=0.55); cyl(3.6, 2.6, 2.15, 0.6, 0.15, "stone", verts=16)
def rentc():
    tile(); walk(0, -3.9, T, 1.4)
    block(-1.0, 1.4, 5.6, 4.6, 4, "buff", fh=1.5)
    box(3.0, -2.4, 0.2, 2.2, 1.0, 2.0, mat("gold", rough=0.3, metal=0.7), bevel=0.25)        # a padlock
    bpy.ops.mesh.primitive_torus_add(major_radius=0.75, minor_radius=0.18, location=(3.0, -2.4, 2.4), rotation=(math.pi / 2, 0, 0))
    bpy.context.object.data.materials.append(mat("steel", rough=0.3, metal=0.8))
def xfer():
    tile(); lawn(0, 0.6, 9.4, 6.0); walk(0, -3.9, T, 1.4)
    box(0, 1.6, 0, 6.4, 3.6, 3.4, "stone", bevel=0.08); pitched(0, 1.6, 3.4, 6.8, 4.0, 1.6, mat("roof", rough=0.8))
    for x in (-2.2, -0.8, 0.8, 2.2): cyl(x, -0.3, 0, 0.22, 3.2, "white", verts=12, bevel=0.02)
    coins(-3.4, -2.6, 6); coins(-2.0, -2.9, 9); coins(3.4, -2.6, 4)

# transit modes
def subway():
    """A cutaway: street on top, the tunnel below with a train, stairs going down to it."""
    dk = mat("#3a424c", rough=0.7); earth = mat("earth", rough=0.95)
    box(0, 1.0, -4.6, T, T - 2.0, 4.25, earth, bevel=0.3)               # ground behind the tunnel
    box(0, -4.0, -4.6, T, 2.0, 0.5, earth, bevel=0.15)                    # tunnel floor (front edge)
    box(0, -2.0, -4.6, T, 6.0, 0.5, dk, bevel=0.05)
    box(0, -2.0, -1.05, T, 6.0, 0.7, earth, bevel=0.15)                    # the street slab over the tunnel
    box(0, 0, -0.35, T, T, 0.35, mat("street", rough=0.9), bevel=0.25)
    walk(0, 3.4, T, 3.2)
    box(0, -2.0, -4.1, T - 0.2, 0.05, 2.6, dk, bevel=0)                  # the tunnel's back wall
    for y in (-3.9, -2.7): box(0, y, -4.1, T - 0.4, 0.12, 0.1, "steel", bevel=0)
    box(0, -3.3, -4.0, T - 0.6, 2.4, 2.4, mat("#d7dbe0", rough=0.35, metal=0.4), bevel=0.3)   # the train
    box(0, -4.52, -2.85, T - 1.2, 0.05, 0.75, "glassdk", bevel=0.01)
    box(0, -4.53, -3.4, T - 0.6, 0.05, 0.18, "star", bevel=0.01)
    for x in (-3.2, 0, 3.2): box(x, -4.54, -3.85, 0.9, 0.05, 1.6, "glassdk", bevel=0.01)
    # the entrance: stairs down through the sidewalk, rails and a navy sign post
    for k in range(5): box(-2.6, 2.4 + k * 0.45, -0.3 - (4 - k) * 0.28, 1.8, 0.45, 0.28, "#9aa1a9", bevel=0.01)
    for side in (-1, 1): box(-2.6 + side * 1.0, 3.3, 0.1, 0.12, 2.4, 0.9, "steel", bevel=0.02)
    box(-2.6, 2.15, 0.1, 2.1, 0.12, 0.9, "steel", bevel=0.02)
    cyl(-0.9, 2.2, 0.1, 0.12, 3.2, "steel", verts=8, bevel=0)
    box(-0.9, 2.2, 2.6, 1.6, 0.18, 0.9, "navy", bevel=0.05); box(-0.9, 2.1, 2.85, 1.0, 0.05, 0.4, "white", bevel=0.01)
    tree(3.4, 3.6, 0.1, 0.55); person(1.4, 3.0, "star", 1.0); person(-2.6, 3.6, "gold", 0.9)
    for o in bpy.data.objects:                          # lift it so the shadow floor sits under the tunnel
        if o.type == "MESH": o.location.z += 3.55
def train():
    """Home tile for the transit simulator: one big L car on a short elevated deck, front toward the viewer."""
    tile(); walk(0, -3.9, T, 1.4)
    z = 3.0
    box(0, 0.6, z, T + 0.2, 3.6, 0.55, "steel", bevel=0.05)                                    # deck
    for x in (-3.6, 3.6):
        for y in (-0.9, 2.1): box(x, y, 0, 0.4, 0.4, z, "steel", bevel=0.03)                  # columns
        box(x, 0.6, z - 0.45, 0.45, 3.6, 0.45, "steel", bevel=0.03)                           # cross beams
    for y in (-0.15, 1.35): box(0, y, z + 0.55, T + 0.2, 0.14, 0.12, "#8a9099", bevel=0)      # rails
    silver = mat("#dfe3e8", rough=0.3, metal=0.45)
    box(0.6, 0.6, z + 0.75, 7.6, 2.5, 2.7, silver, bevel=0.45)                                # the car
    box(0.6, -0.66, z + 1.95, 6.8, 0.05, 0.85, "glassdk", bevel=0.01)                         # side windows
    box(0.6, -0.67, z + 1.45, 7.62, 0.05, 0.26, mat("#41b6e6", rough=0.4), bevel=0.01)        # flag-blue stripe
    box(4.42, 0.6, z + 1.95, 0.05, 1.7, 0.95, "glassdk", bevel=0.01)                          # front window
    for y in (-0.15, 1.35): box(4.43, y, z + 1.15, 0.05, 0.32, 0.22, mat("#fff6c8", rough=0.2, emit=1.5), bevel=0.01)   # headlights
    box(4.43, 0.6, z + 2.98, 0.05, 1.1, 0.28, mat("#41b6e6", rough=0.4, emit=0.6), bevel=0.01)   # destination sign
    for x in (-1.8, 3.0): box(x, -0.66, z + 0.85, 1.1, 0.05, 1.9, mat("#b9c0c8", rough=0.4), bevel=0.01)   # doors
    tree(-3.8, -3.6, 0.1, 0.5); person(2.4, -3.8, "star", 0.9)

def elevated():
    tile()
    el_track([(-5.2, 0.4), (5.2, 0.4)], z=4.2, train=True, train_at=0.02, cars=1, stripe="star")
    walk(0, -3.9, T, 1.4)
def streetcar():
    tile(top="street"); walk(0, -4.2, T, 1.2); walk(0, 4.2, T, 1.2)
    for y in (-0.6, 0.6): box(0, y, 0.02, T, 0.15, 0.05, "steel", bevel=0)
    box(0, 0, 0.3, 8.0, 2.4, 2.6, mat("#e9a23b", rough=0.4), bevel=0.4); box(0, -1.22, 1.5, 7.0, 0.05, 0.9, "glassdk", bevel=0)
    box(0, 0, 2.9, 0.12, 0.12, 2.0, "steel", bevel=0); box(0, 0, 4.9, T, 0.06, 0.06, "ink", bevel=0)
def brt():
    tile(top="street"); walk(0, -4.2, T, 1.2)
    box(0, -1.4, 0.0, T, 3.0, 0.03, mat("#c0392b", rough=0.8), bevel=0)
    bus(-0.6, -1.4, L=8.6)
    box(0, 2.4, 0, 6.8, 2.2, 0.5, "stone", bevel=0.05); box(0, 2.6, 0.5, 6.4, 0.15, 2.4, mat("glass", rough=0.1, alpha=0.5), bevel=0.02)
    box(0, 2.4, 2.9, 7.0, 2.6, 0.2, "navy", bevel=0.05)
    person(1.4, 2.0, h=1.0); person(-1.8, 2.1, h=1.0)
def infill():
    tile()
    el_track([(-5.2, 0.4), (5.2, 0.4)], z=4.2)
    box(0, -2.4, 4.2, 5.0, 1.6, 0.4, mat("lt6", rough=0.5), bevel=0.05)                 # the new platform
    box(0, -2.4, 6.3, 5.2, 1.8, 0.2, "navy", bevel=0.05)
    for x in (-2.2, 2.2): box(x, -2.9, 4.6, 0.15, 0.15, 1.7, "steel", bevel=0)
    box(-3.4, -2.6, 0, 1.2, 1.2, 4.2, mat("lt6", rough=0.5), bevel=0.05)                # stair tower
    person(0.8, -2.4, "star", 0.9); person(-0.6, -2.3, "gold", 0.9)
    walk(0, -3.9, T, 1.4)
def metra():
    tile(); box(0, 0.2, 0, T, 4.0, 0.4, mat("#b7aa94", rough=0.95), bevel=0.06)
    for y in (-0.4, 0.8): box(0, y, 0.4, T, 0.15, 0.08, "steel", bevel=0)
    box(-0.2, 0.2, 0.6, 9.4, 3.0, 4.2, mat("#cfd5dc", rough=0.3, metal=0.5), bevel=0.4)   # a double-deck car
    for z in (1.4, 3.1): box(-0.2, -1.32, z, 8.4, 0.05, 0.75, "glassdk", bevel=0)
    box(-0.2, -1.33, 0.9, 9.4, 0.05, 0.12, "star", bevel=0)
    walk(0, -3.9, T, 1.4)

ICONS = dict(icons.ICONS)
ICONS.update({k: v for k, v in globals().items() if k in ("build", "aro", "permits", "mega", "vland", "pre", "mpls", "camb", "small", "park", "comm", "vac",
              "social", "down", "pmin", "mora", "rentc", "xfer", "subway", "train", "elevated", "streetcar", "brt", "infill", "metra")})

def render_icon(name, out, size=256):
    reset(); random.seed(7)
    ICONS[name]()
    rig(17.5, target=(0, 0, 1.3), elev=33, azim=-52, sun=(50, -25), sun_e=3.4, world="#eef3f8", world_e=0.55)
    from learn import fit
    fit(bpy.context.scene.camera, 1.0, margin=1.04)
    shadow_catcher(z=-1.1)
    render(os.path.abspath(out), size, size, samples=40)

if __name__ == "__main__":
    name, outdir = sys.argv[1], sys.argv[2]; size = int(sys.argv[3]) if len(sys.argv) > 3 else 256
    os.makedirs(outdir, exist_ok=True)
    for n in (ICONS if name == "all" else name.split(",")): render_icon(n, os.path.join(outdir, n + ".png"), size)
