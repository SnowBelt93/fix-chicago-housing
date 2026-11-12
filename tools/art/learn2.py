"""Learn page art, second pass: detailed clay street scenes, the "how many homes fit" lot exhibit, and Progress art.
    python3.11 tools/art/learn2.py <name|all|lots|a,b> <outdir> [scale]
Topic scenes render 1800x720 (5:2), lot_* 900x720 with one shared camera, progress 1600x760. No words in any picture."""
import sys, os, math, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy
from clay import *

LEVEL = {"rs3": "#cfd4da", "rt4": "#7ec8ec", "rm5": "#41b6e6", "rm6": "#2b5da0"}

def lot_mark(x, y, w, col, d=0.45): box(x, y, 0.1, w, d, 0.1, mat(col, rough=0.6), bevel=0.03)

def street_life(w, f, seed=1, trees=True, lamps=True, parked=True, skip=()):
    """Trees and lamps in the parkway, parked cars at the curb."""
    r = random.Random(seed); W = w - 6
    if trees:
        for k in range(int(W / 9) + 1):
            x = -W / 2 + k * 9 + r.random() * 1.5
            if not any(a <= x <= b for a, b in skip): tree(x, f + 7.0, 0.8 + r.random() * 0.25)
    if lamps:
        for x in (-W / 2 + 4, 0.5, W / 2 - 4): lamp(x, f + 6.6)
    if parked: cars(-W / 2 + 1, W / 2 - 3, f + 4.6, seed=seed)

def truck(x, y, col="#f4f5f6"):
    box(x - 1.0, y, 0.6, 6.0, 2.4, 2.9, mat(col, rough=0.5), bevel=0.1); box(x + 3.1, y, 0.5, 2.0, 2.3, 2.1, mat("navy", rough=0.4), bevel=0.25)
    box(x + 4.12, y, 1.5, 0.05, 1.9, 0.9, "glassdk", bevel=0.02)
    for dx in (-2.8, 2.9):
        for dy in (-1.1, 1.1):
            o = cyl(x + dx, y + dy, 0, 0.5, 0.3, mat("#1f2227", rough=0.8), verts=14); o.location = (x + dx, y + dy, 0.5); o.rotation_euler = (math.pi / 2, 0, 0)

def hardhat(x, y, vest="#f2c53d"):
    person(x, y, vest, 1.0); sphere(x, y, 0.14 + 1.8 * PS[0], 0.23 * PS[0], mat("#f4f5f6", rough=0.4), sub=2, sz=0.7)

# ---------- the eleven topics ----------
def zoning():
    by = street_base(88, 34); f = -17
    xs = (-33, -15, 5, 29)
    bungalow(xs[0], by, D=11); garage(xs[0], by + 14.6)
    flats(xs[1], by, floors=3, D=12, porch=True)
    sixflat(xs[2], by, D=12)
    midrise(xs[3], by, W=18, floors=5, D=13)
    for x, w, k in zip(xs, (13, 13, 18, 22), ("rs3", "rt4", "rm5", "rm6")): lot_mark(x, by - 3.3, w, LEVEL[k])
    for x in (-24, -5.5, 16.5): fence(x, by - 3.0, x, by + 12, h=1.2)
    for x in (-37.5, -28.5, -19.5, -10.5): shrub(x, by - 1.0)
    street_life(88, f, seed=4, skip=((2, 8), (22, 36)))
    hydrant(-22, f + 6.6); person(-30, f + 9.3); person(-12.5, f + 8.8); person(-11.6, f + 9.2, h=0.7); person(8, f + 9.4); person(24, f + 8.9); person(31, f + 9.5)

def illegal():
    by = street_base(88, 34); f = -17
    bungalow(-36, by, D=11)
    flats(-24, by, floors=2, wall="#b86b4f", D=11, brick_side="#a65a42", flip=True)
    flats(-11, by, floors=3, D=12)                                                     # the one today's rules would not allow
    cottage(2, by)
    sixflat(17, by, D=12, wall="#c9925a")                                              # and this one
    bungalow(33, by, D=11, brick="#b9855f", flip=True)
    red = mat("star", rough=0.4, alpha=0.2)
    for x, w, h in ((-11, 9.0, 12.6), (17, 15.6, 12.4)):
        box(x, by + 5.5, 0.05, w, 15.5, h, red, bevel=0.3)
        for dx in (-w / 2, w / 2):                                                     # red corner posts and a tape line, like a marked-off site
            for dy in (-2.2, 13.2): box(x + dx, by + dy, 0, 0.16, 0.16, 1.3, "star", bevel=0.02)
        box(x, by - 2.2, 1.05, w, 0.06, 0.16, "star", bevel=0); box(x, by - 2.2, 0.75, w, 0.06, 0.1, "white", bevel=0)
    for x in (-30, -17.5, -4.5, 8, 26): fence(x, by - 3.0, x, by + 11, h=1.1)
    street_life(88, f, seed=7)
    person(-10, f + 9.2); person(-8.8, f + 9.0); person(15, f + 9.3); person(-33, f + 9.1)

def shortage():
    by = street_base(88, 34); f = -17
    frame_up(-26, by - 1, 22, 13, 6, done=3)                                            # homes going up
    crane(-11.5, by + 9, 0, 24, 17, ang=math.radians(184), m=mat("star", rough=0.45))
    board_fence(-36, by - 2.4, -12, by - 2.4, h=2.0, col="#d9c3a0")
    hardhat(-33, f + 9.0); hardhat(-17, f + 9.4, "#e07a3f"); truck(-27, f + 4.4)
    midrise(3, by, W=16, floors=5, D=12, panel="#e4ddcf", seed=9)                      # the one building with a vacancy: the line is for it
    for k in range(20): person(4.6 + k * 1.75, f + 8.5 + (k % 2) * 0.6)
    for k in range(4): person(3.4 - k * 0.1, f + 9.6 + k * 1.5)                        # the line turns up the walk to the door
    paved(3, by - 1.6, 1.6, 3.4)
    bungalow(21, by, D=11); flats(31, by, floors=2, wall="#b86b4f", D=11, brick_side="#a65a42"); cottage(40, by, col="#c9b28f")
    for x in (26, 35.5): fence(x, by - 3.0, x, by + 11, h=1.1)
    street_life(88, f, seed=3, parked=False, skip=((-36, -10),)); cars(8, 40, f + 4.6, seed=5)

def rents():
    by = street_base(88, 34); f = -17
    # few homes, a crowd for each, a tall stack of rent · more homes, a shorter stack · many homes, the shortest
    flats(-34, by, floors=3, D=12)
    crowd(-39, -29, f + 8.2, f + 11.5, 13, seed=4); coins(-25.5, f + 7.6, 20, r=2.2)
    flats(-12, by, floors=3, D=12, wall="#b86b4f", brick_side="#a65a42"); sixflat(-1, by, D=12)
    crowd(-15, 5, f + 8.2, f + 11, 8, seed=6); coins(9.5, f + 7.6, 12, r=2.2)
    flats(18, by, floors=3, D=12, flip=True); midrise(31.5, by, W=17, floors=5, D=12, seed=2)
    crowd(16, 38, f + 8.2, f + 10.6, 5, seed=8); coins(41.6, f + 7.6, 6, r=2.2)
    for x in (-19.5, 13.5): box(x, 0, 0.02, 0.5, 33, 0.14, mat("curb", rough=0.8), bevel=0.05)   # three separate cases
    street_life(88, f, seed=11, lamps=False, parked=False, skip=((-28, -23), (7, 12), (40, 45)))

def prerogative():
    by = street_base(88, 34); f = -17
    flats(-33, by, floors=3, D=12); bungalow(-21, by, D=11)
    bungalow(26, by, D=11, flip=True, brick="#b9855f"); flats(37, by, floors=2, wall="#b86b4f", D=11, brick_side="#a65a42", flip=True)
    box(2, by + 5, 0.1, 30, 20, 0.05, mat("#cdbfa6", rough=0.95), bevel=0.05)             # the empty lot: bare dirt, weeds
    r = random.Random(9)
    for _ in range(26): shrub(-12 + r.random() * 28, by - 3.5 + r.random() * 17, 0.35 + r.random() * 0.5)
    for a, b in (((-13, by - 4.6), (-3.2, by - 4.6)), ((3.2, by - 4.6), (17, by - 4.6)), ((-13, by - 4.6), (-13, by + 15)), ((17, by - 4.6), (17, by + 15))):
        fence(a[0], a[1], b[0], b[1], h=2.2, col="steel", step=1.2)
    for sx in (-3.1, 3.1): box(sx, by - 4.6, 0, 0.3, 0.3, 3.4, "steel", bevel=0.02)         # the gate, shut, with one big lock
    for sx in (-1.55, 1.55): box(sx, by - 4.6, 0.25, 3.0, 0.1, 2.7, mat("#8a939c", rough=0.5, metal=0.4, alpha=0.8), bevel=0.02)
    gold = mat("gold", rough=0.35, metal=0.5); sil = mat("#c9ced3", rough=0.3, metal=0.7)
    box(0, by - 4.85, 0.7, 2.3, 0.5, 1.8, gold, bevel=0.16)
    for sx in (-0.68, 0.68): cyl(sx, by - 4.85, 2.5, 0.16, 1.0, sil, verts=12)
    box(0, by - 4.85, 3.42, 1.68, 0.32, 0.3, sil, bevel=0.1)
    box(0, by - 5.12, 1.3, 0.3, 0.06, 0.7, "ink", bevel=0.02); cyl(0, by - 5.1, 1.9, 0.26, 0.06, "ink", verts=14).rotation_euler = (math.pi / 2, 0, 0)
    # one person holds the key; the builders wait with their plans
    person(-7.6, f + 9.3, "navy", 1.3)
    o = cyl(-5.8, f + 9.1, 0, 0.75, 0.2, gold, verts=24); o.location = (-5.8, f + 9.1, 3.3); o.rotation_euler = (math.pi / 2, 0, 0)
    o = cyl(-5.8, f + 8.98, 0, 0.36, 0.06, "ground", verts=20); o.location = (-5.8, f + 8.98, 3.3); o.rotation_euler = (math.pi / 2, 0, 0)
    box(-5.8, f + 9.1, 0.5, 0.3, 0.2, 2.2, gold, bevel=0.06); box(-5.35, f + 9.1, 0.6, 0.75, 0.2, 0.28, gold, bevel=0.04); box(-5.42, f + 9.1, 1.15, 0.6, 0.2, 0.28, gold, bevel=0.04)
    for k, v in enumerate(("#f2c53d", "#e07a3f", "#f2c53d")): hardhat(5.5 + k * 1.7, f + 8.8 + (k % 2) * 0.6, v)
    box(11.5, f + 9.9, 1.0, 2.2, 0.12, 1.5, mat("#f4f5f6", rough=0.6), bevel=0.02)            # their plan, pinned up (blank)
    box(11.5, f + 9.82, 1.25, 1.2, 0.05, 0.9, mat("lt6", rough=0.6), bevel=0.01)
    for sx in (10.5, 12.5): box(sx, f + 10.0, 0.14, 0.1, 0.1, 1.0, "steel", bevel=0)
    street_life(88, f, seed=2, skip=((-9, 9),)); hydrant(12, f + 6.6)

def aro():
    by = street_base(88, 34); f = -17
    midrise(-6, by, W=44, floors=6, D=13, panel="#e9e6df", aff=0.2, seed=21, balconies=False)
    flats(-37, by, floors=3, D=12); bungalow(26, by, D=11); cottage(36, by, col="#c9b28f", flip=True)
    for x in (31, ): fence(x, by - 3.0, x, by + 11, h=1.1)
    paved(-6, by - 1.6, 2.2, 3.4)
    crowd(-22, 10, f + 8.3, f + 10.2, 9, seed=5)
    street_life(88, f, seed=6)

def megaprojects():
    w, d = 104, 36; slab(w, d); f = -d / 2; W = w - 0.5
    box(0, f + 3.4, 0.02, W, 6.4, 0.04, mat("lake", rough=0.08, spec=0.7), bevel=0.02)       # the river
    box(0, f + 6.8, 0, W, 0.5, 0.9, mat("#b9b2a4", rough=0.9), bevel=0.05)                   # river wall
    box(0, f + 9.0, 0, W, 3.6, 0.2, mat("curb", rough=0.85), bevel=0.03)                     # riverwalk
    for k in range(13): tree(-W / 2 + 4 + k * 8, f + 8.6, 0.7)
    for k in range(int(W / 1.4)): box(-W / 2 + 0.7 + k * 1.4, f + 7.25, 0.2, 0.06, 0.06, 1.0, "steel", bevel=0)
    box(0, f + 7.25, 1.15, W, 0.06, 0.06, "steel", bevel=0)
    box(-41, f + 3.4, 0.25, 9, 3.0, 0.7, mat("#f4f5f6", rough=0.4), bevel=0.3); box(-42, f + 3.4, 0.95, 5, 2.4, 0.8, mat("navy", rough=0.4), bevel=0.2)   # a tour boat
    y0 = f + 13
    glass_tower(-36, y0, W=13, D=11, floors=11, FH=2.3, podium=1)                            # phase one: finished
    midrise(-17, y0, W=17, floors=6, D=12, panel="#e4ddcf", seed=4, col2="#9fb4c7")
    frame_up(4, y0, 15, 12, 10, FH=2.3, done=4, col="#c9d6e2")                                # phase two: going up
    crane(14.5, y0 + 6, 0, 30, 18, ang=math.radians(172), m=mat("star", rough=0.45))
    frame_up(24, y0, 13, 12, 4, FH=2.3)
    crane(33, y0 + 9, 0, 22, 15, ang=math.radians(200), m=mat("star", rough=0.45))
    box(42, y0 + 6, 0.1, 15, 15, 0.06, mat("#cdbfa6", rough=0.95), bevel=0.05)                # phase three: staked-out dirt
    for sx in (-6.5, 0, 6.5):
        for sy in (-6.5, 0, 6.5): box(42 + sx, y0 + 6 + sy, 0, 0.1, 0.1, 1.0, "star", bevel=0)
    coins(-48.5, f + 9.2, 9, r=1.3); coins(-45.4, f + 9.6, 5, r=1.3)                          # the public money that pays for streets and pipes
    track(-W / 2 + 0.5, W / 2 - 0.5, d / 2 - 2.2); commuter(-30, d / 2 - 2.2, 0.2, cars=2)
    hardhat(10, f + 10); hardhat(20, f + 11, "#e07a3f"); crowd(-40, -8, f + 8.6, f + 10.2, 8, seed=3)

def modes():
    w, d = 100, 30; slab(w, d); f = -d / 2; W = w - 0.5
    box(0, f + 4.2, 0, W, 8.0, 0.05, mat(ASPHALT, rough=0.9), bevel=0.02)
    for k in range(int(W / 5)): box(-W / 2 + 2.6 + k * 5, f + 4.2, 0.05, 2.2, 0.16, 0.02, "white", bevel=0)
    box(0, f + 8.4, 0, W, 0.3, 0.2, mat("curb", rough=0.8), bevel=0.04); box(0, f + 10.2, 0, W, 3.2, 0.16, mat("curb", rough=0.85), bevel=0.03)
    box(0, f + 21, 0, W, 17.6, 0.08, mat(GRASS, rough=0.95), bevel=0.04)
    # 1 a bus at its stop
    bus(-39, f + 6.4, "navy")
    box(-41, f + 10.6, 0.16, 4.4, 1.5, 0.08, "steel", bevel=0.02)
    for sx in (-2.1, 2.1): box(-41 + sx, f + 11.2, 0.16, 0.1, 0.1, 2.5, "steel", bevel=0)
    box(-41, f + 10.7, 2.66, 4.8, 1.9, 0.12, mat("navy", rough=0.5), bevel=0.04); box(-41, f + 11.25, 0.4, 4.3, 0.05, 2.0, mat("#9fc7e2", rough=0.1, alpha=0.5), bevel=0)
    person(-42, f + 10.3); person(-40.6, f + 10.5); person(-39.4, f + 10.2, h=0.7)
    # 2 a streetcar on rails in the street, under its wire
    for dy in (-0.75, 0.75): box(-14, f + 2.4 + dy, 0.05, 30, 0.14, 0.05, mat("steel", metal=0.5, rough=0.4), bevel=0)
    box(-15, f + 2.4, 0.3, 15, 2.5, 2.9, mat("#e9a23b", rough=0.4), bevel=0.4); box(-15, f + 2.4, 0.3, 15.05, 2.55, 0.7, mat("#f4ecd8", rough=0.5), bevel=0.2)
    for side in (-1, 1): box(-15, f + 2.4 + side * 1.27, 1.55, 13.4, 0.05, 1.0, "glassdk", bevel=0.01)
    for dx in (-5.6, 0, 5.6): box(-15 + dx, f + 1.11, 0.5, 1.2, 0.05, 2.2, mat("#2c4868", rough=0.2), bevel=0.01)
    box(-15, f + 2.4, 3.2, 5, 1.4, 0.25, mat("#c9ced3", rough=0.5), bevel=0.06); box(-15, f + 2.4, 3.45, 0.08, 0.08, 1.5, "steel", bevel=0); box(-15, f + 2.4, 4.95, 2.2, 0.06, 0.06, "steel", bevel=0)
    for x in (-29, -14, 1):
        box(x, f + 9.0, 0.16, 0.2, 0.2, 5.6, "steel", bevel=0.02); box(x, f + 5.6, 5.5, 0.08, 6.9, 0.08, "steel", bevel=0)
    box(-14, f + 2.4, 5.02, 30, 0.04, 0.04, "ink", bevel=0)
    # 3 the elevated L, with a station
    el_track([(4, f + 17), (40, f + 17)], z=7.0); ltrain(10.5, f + 17, 7.9, cars=2, stripe="star")
    el_station(20, f + 17, z=7.0, L=24)
    crowd(10, 30, f + 11.2, f + 14.0, 7, seed=4, z=8.2); person(33, f + 10.4); person(34.3, f + 10.0)
    # 4 a subway, shown in a cutaway under the street
    X0, X1 = 26, w / 2; cx, L = (X0 + X1) / 2, X1 - X0
    earth = mat("earth", rough=0.95); wall = mat("#d9d5cb", rough=0.8)
    box(cx, 0, -8.3, L, d, 0.9, earth, bevel=0.3)
    box(cx, 4.2, -7.4, L, d - 8.4, 6.2, earth, bevel=0.1)                                     # solid ground behind the tunnel
    box(cx, f + 8.25, -7.4, L - 0.2, 0.3, 6.2, wall, bevel=0.02)                              # tunnel back wall
    box(X0 + 0.15, f + 4.2, -7.4, 0.3, 8.0, 6.2, wall, bevel=0.02)
    box(cx, f + 4.2, -7.4, L - 0.2, 8.0, 0.3, mat("#8f8b84", rough=0.9), bevel=0.02)
    for k in range(5): box(X0 + 1.2 + k * (L - 2.4) / 4, f + 0.4, -7.1, 0.5, 0.5, 5.85, wall, bevel=0.04)
    for k in range(6): box(X0 + 2 + k * 3.6, f + 4.2, -1.5, 2.4, 0.3, 0.1, mat("#fff4d6", rough=0.4, emit=3.0), bevel=0.02)
    track(X0 + 0.4, X1 - 0.4, f + 3.2, z=-7.1, bed=False); lcar(cx + 1.5, f + 3.2, -6.95, stripe="navy")
    box(cx, f + 6.9, -7.1, L - 0.4, 2.2, 1.1, wall, bevel=0.04)                               # platform
    for k in range(5): person(X0 + 3 + k * 3.7, f + 6.6, z=-6.0)
    box(cx - 4, f + 10.4, 0.16, 5.0, 2.4, 0.9, mat("#3d434b", rough=0.5), bevel=0.05)          # the entrance up top: a stair going down, a rail, a lit globe
    box(cx - 4, f + 10.4, 0.5, 4.2, 1.7, 0.6, mat("#15171a", rough=0.9), bevel=0)
    cyl(cx - 7, f + 10.4, 0.16, 0.08, 3.2, "steel", verts=8, bevel=0); sphere(cx - 7, f + 10.4, 3.6, 0.42, mat("#bfe6ff", rough=0.3, emit=2.0), sub=2)
    for x in (-34, -30, -8, -3, 44): tree(x, f + 20 + (x % 4), 0.9)
    cottage(-37, f + 16, D=8); bungalow(-10, f + 16, D=9)
    crowd(-30, 2, f + 9.4, f + 11.2, 6, seed=8)
    for x in (-46, -20): flats(x, f + 16, floors=2 + (x == -20), D=10, wall="#d8d0bd" if x == -20 else "#b86b4f", brick_side=None if x == -20 else "#a65a42")

def funding():
    w, d = 96, 30; slab(w, d); f = -d / 2; W = w - 0.5
    box(0, f + 3.0, 0, W, 5.6, 0.05, mat(ASPHALT, rough=0.9), bevel=0.02)
    box(0, f + 5.95, 0, W, 0.3, 0.2, mat("curb", rough=0.8), bevel=0.04); box(0, f + 8.6, 0, W, 5.0, 0.16, mat("curb", rough=0.85), bevel=0.03)
    box(0, f + 20.4, 0, W, 18.6, 0.08, mat(GRASS, rough=0.95), bevel=0.04)
    # three stacks pay for it: the biggest is Washington's, then the state's, then the city's own
    coins(-41, f + 8.6, 26, col="navy", r=2.0); coins(-34.5, f + 8.6, 12, col="lt6", r=2.0); coins(-28, f + 8.6, 7, col="star", r=2.0)
    # the line they buy: finished and running on the left, still being built on the right
    yy = f + 18
    el_track([(-22, yy), (14, yy)], z=7.0); ltrain(-18, yy, 7.9, cars=2, stripe="lt6")
    st = mat("steel", rough=0.6)
    for x in (23, 32, 41):                                                                    # bents waiting for their deck
        for side in (-2.1, 2.1): box(x, yy + side, 0, 0.45, 0.45, 7.0, st, bevel=0.03)
        box(x, yy, 6.4, 0.5, 5.0, 0.6, st, bevel=0.03)
    box(18.5, yy, 7.0, 9.0, 5.2, 0.9, st, bevel=0.06)
    hx, hy = crane(30, yy - 7.5, 0, 22, 15, ang=math.radians(78), m=mat("star", rough=0.45), hook_box=(0, 0, 11.0, 0.9))
    box(hx, hy, 11.0, 8.6, 1.0, 0.9, st, bevel=0.06, rot=0)                                    # a girder on the hook
    for x in (20, 26, 37): hardhat(x, f + 9.4, "#f2c53d" if x != 26 else "#e07a3f")
    truck(38, f + 3.2); board_fence(17, f + 11.4, 45, f + 11.4, h=1.4, col="#e07a3f")
    for x in (-44, -33, -22, -9, 4, 16, 27, 39): tree(x, f + 26 + (x % 3), 1.0)
    crowd(-46, -24, f + 6.6, f + 7.4, 5, seed=3)

def nita():
    w, d = 100, 34; slab(w, d); f = -d / 2; W = w - 0.5
    box(0, f + 9, 0, W, 17.6, 0.05, mat(ASPHALT, rough=0.9), bevel=0.02)                      # the bus plaza
    box(0, f + 19.6, 0, W, 3.4, 0.9, mat("curb", rough=0.85), bevel=0.04)                     # one long platform
    track(-W / 2 + 0.3, W / 2 - 0.3, f + 23.6, z=0.0); track(-W / 2 + 0.3, W / 2 - 0.3, f + 29.4, z=0.0)
    box(0, f + 26.5, 0, W, 2.0, 0.9, mat("curb", rough=0.85), bevel=0.04)
    ltrain(-36, f + 23.6, 0.25, cars=2, stripe="star")                                        # city rail
    commuter(2, f + 29.4, 0.25, cars=2, stripe="#e07a3f")                                     # suburban rail
    # one roof over all of it
    roof = mat("navy", rough=0.5)
    for x in range(-40, 41, 10):
        for y in (f + 13.2, f + 21.0): cyl(x, y, 0.05 if y < f + 18 else 0.9, 0.2, 7.0, mat("#eef0f1", rough=0.5), verts=12, bevel=0.02)
    box(0, f + 17.1, 7.0, 86, 10.4, 0.45, roof, bevel=0.1); box(0, f + 17.1, 7.45, 80, 6.0, 0.5, mat("#9fc7e2", rough=0.1, alpha=0.6, spec=0.7), bevel=0.1)
    box(0, f + 17.1, 0.05, 12, 4.0, 6.9, mat("#9fc7e2", rough=0.1, alpha=0.45, spec=0.7), bevel=0.05)   # glass hall in the middle
    box(0, f + 17.1, 7.9, 3.4, 3.4, 5.4, mat("#eef0f1", rough=0.6), bevel=0.08)                # clock tower (a blank face and two hands)
    o = cyl(0, f + 15.36, 11.4, 1.15, 0.08, mat("#ffffff", rough=0.4), verts=28, bevel=0); o.location = (0, f + 15.36, 11.6); o.rotation_euler = (math.pi / 2, 0, 0)
    box(0, f + 15.3, 11.6, 0.1, 0.05, 0.85, "ink", bevel=0); box(0.3, f + 15.3, 11.55, 0.62, 0.05, 0.1, "ink", bevel=0)
    star(0, f + 17.1, 14.15, 0.8)
    # three kinds of bus pull in to the same curb
    for x, stripe, body in ((-33, "navy", "#f4f5f6"), (-13, "#2e9d57", "#f4f5f6"), (13, "navy", "#f4f5f6"), (33, "#e07a3f", "#f4f5f6")):
        bus(x, f + 11.2, stripe, body=body)
    bus(-22, f + 4.0, "#2e9d57", flip=True); bus(24, f + 4.0, "navy", flip=True)
    crowd(-40, 40, f + 13.6, f + 15.2, 26, seed=4); crowd(-38, 38, f + 19.4, f + 20.8, 22, seed=9, z=1.04)

def riders():
    w, d = 100, 34; slab(w, d); f = -d / 2; W = w - 0.5
    box(0, f + 3.0, 0, W, 5.6, 0.05, mat(ASPHALT, rough=0.9), bevel=0.02)
    for k in range(int(W / 5)): box(-W / 2 + 2.6 + k * 5, f + 0.7, 0.05, 2.2, 0.16, 0.02, "white", bevel=0)
    box(0, f + 5.95, 0, W, 0.3, 0.2, mat("curb", rough=0.8), bevel=0.04); box(0, f + 8.2, 0, W, 4.2, 0.16, mat("curb", rough=0.85), bevel=0.03)
    box(0, f + 22, 0, W, 23.4, 0.08, mat(GRASS, rough=0.95), bevel=0.04)
    yy = f + 14.5
    el_track([(-49.5, yy), (49.5, yy)], z=7.0)
    el_station(-27, yy, z=7.0, L=24); el_station(25, yy, z=7.0, L=24)
    ltrain(-38, yy, 7.9, cars=2, stripe="star")
    # left: a station with homes, shops and jobs all around it, and a full platform
    y0 = yy + 8.5
    midrise(-40, y0, W=15, floors=5, D=9, seed=2); midrise(-23, y0, W=16, floors=6, D=9, panel="#e4ddcf", seed=6); sixflat(-7, y0, D=9)
    crowd(-38, -16, yy - 5.3, yy - 3.4, 24, seed=3, z=8.2)                                      # a full platform
    crowd(-44, -4, f + 6.8, f + 9.8, 18, seed=5); bus(-12, f + 4.4, "navy")
    # right: a station among a few houses, and two people waiting
    bungalow(12, y0, D=9); cottage(24, y0); bungalow(37, y0, D=9, flip=True, brick="#b9855f"); garage(45.5, y0 + 3)
    for x in (18, 30.5, 42): tree(x, y0 + 1, 1.0)
    crowd(22, 28, yy - 5.3, yy - 3.4, 2, seed=1, z=8.2)
    person(30, f + 8.0); car(40, f + 4.6, "#c9ced3")
    box(0, 0, 0.02, 0.5, d - 1, 0.14, mat("curb", rough=0.8), bevel=0.05)

def history():
    """When did your block go up: one block face built across 130 years, oldest on the left; under each lot a band of the
    timeline in the map's blues (pale = old, navy = new), and a 2020s building still going up at the right end."""
    by = street_base(96, 34); f = -17
    cottage(-40, by, col="#b9a27f")                                                     # 1880s wood cottage
    flats(-28, by, floors=3, wall="#d8d0bd", D=13, porch=True)                          # 1900s greystone three-flat
    bungalow(-15, by, D=11)                                                             # 1920s bungalow
    sixflat(1, by, D=12, wall="#c9925a")                                                # 1920s courtyard-style six-flat
    midrise(20, by, W=16, floors=4, D=12, panel="#c9c3b6", accent=("#8a9aa6", "#8a9aa6", "#8a9aa6", "#8a9aa6"), shop=False, seed=2)   # 1960s
    frame_up(38, by, 13, 12, 5, done=3)                                                 # 2020s, going up
    crane(45, by + 9, 0, 20, 11, ang=math.radians(200), m=mat("star", rough=0.45))
    bands = ((-40, 9.5, "#e3ecf7"), (-28, 9.5, "#c6d8ee"), (-15, 12.5, "#9fbde2"), (1, 16.5, "#6f9ad0"), (20, 18.5, "#3f72b5"), (38, 15.5, "#1f4d8f"))
    for x, w, c in bands: box(x, by - 3.6, 0.1, w - 0.4, 1.5, 0.16, mat(c, rough=0.6), bevel=0.04)
    for x in (-34, -21.5, -7, 10.5, 30): fence(x, by - 3.0, x, by + 11.5, h=1.1)
    street_life(96, f, seed=11, skip=((33, 48),))
    person(-36, f + 9.2); person(-14, f + 9.0); person(-13.2, f + 9.3, h=0.7); person(6, f + 9.4); person(26, f + 8.9)
    hardhat(36, by - 1.6); hardhat(40, by - 1.2, "#e07a3f")

TOPICS = {k: globals()[k] for k in ("history", "zoning", "illegal", "shortage", "rents", "prerogative", "aro", "megaprojects", "modes", "funding", "nita", "riders")}

# ---------- the lot exhibit: one standard 25 x 125 ft lot (7.6 x 38 m), four districts ----------
LOTW, LOTD = 7.6, 38.0
def lot_base(key):
    slab(11.0, 48.5); f = -24.25
    box(0, f + 1.6, 0, 10.6, 3.0, 0.05, mat(ASPHALT, rough=0.9), bevel=0.02)
    box(0, f + 3.25, 0, 10.6, 0.3, 0.2, mat("curb", rough=0.8), bevel=0.04)
    box(0, f + 4.3, 0, 10.6, 1.7, 0.14, mat(GRASS, rough=0.95), bevel=0.04); tree(-3.2, f + 4.3, 0.75); tree(3.6, f + 4.3, 0.7)
    box(0, f + 6.3, 0, 10.6, 2.2, 0.16, mat("curb", rough=0.85), bevel=0.03)
    y0 = f + 7.5                                                                              # the front lot line
    box(0, y0 + LOTD / 2, 0, LOTW, LOTD, 0.12, mat(GRASS, rough=0.95), bevel=0.04)             # the lot
    edge = mat(LEVEL[key], rough=0.6)
    for sx in (-LOTW / 2, LOTW / 2): box(sx, y0 + LOTD / 2, 0.06, 0.22, LOTD + 0.22, 0.16, edge, bevel=0.03)
    for sy in (0, LOTD): box(0, y0 + sy, 0.06, LOTW + 0.22, 0.22, 0.16, edge, bevel=0.03)
    box(0, f + 47.0, 0, 10.6, 2.6, 0.05, mat("alley", rough=0.9), bevel=0.02)
    return y0

def lot_rs3():
    y0 = lot_base("rs3"); by = y0 + 5.0
    bungalow(0, by, D=14); paved(1.9, y0 + 1.9, 1.3, 3.6)
    tree(-1.6, by + 18.5, 0.9); shrub(2.4, by + 16.5); shrub(2.9, by + 17.4, 0.8)
    box(-1.8, by + 15.6, 0.12, 2.6, 1.6, 0.5, mat("#9c7b5c", rough=0.9), bevel=0.03)             # back deck
    garage(0, y0 + LOTD - 3.6, w=6.2, d=6.4, door="+y")
    mailboxes(-2.6, y0 + 0.9, 1)

def lot_rt4():
    y0 = lot_base("rt4"); by = y0 + 4.6
    flats(0, by, floors=3, D=17, porch=True); paved(1.75, y0 + 1.6, 1.4, 3.0)
    tree(-1.9, by + 23.5, 0.8)
    garage(0, y0 + LOTD - 3.6, w=6.2, d=6.4, door="+y")
    mailboxes(-2.2, y0 + 0.9, 3)

def lot_rm5():
    y0 = lot_base("rm5"); by = y0 + 4.6
    flats(0, by, floors=3, D=23, wall="#d4a55c", trim="#ece4d2", porch=True)                    # three floors, two homes on each: front and back
    for f in range(3): box(3.22, by + 11.5, 1.0 + f * 3.1, 0.1, 0.5, 3.1, mat("#ece4d2", rough=0.7), bevel=0.02)   # the line between front and back homes
    box(3.25, by + 11.5, 0.1, 0.5, 1.6, 0.9, mat("#ece4d2", rough=0.7), bevel=0.03)             # side stoop for the back homes
    paved(1.75, y0 + 1.6, 1.4, 3.0); paved(3.5, by + 6, 0.6, 12)
    paved(0, y0 + LOTD - 3.0, LOTW - 0.6, 5.6, col="alley", h=0.14)                              # parking off the alley
    for k, c in enumerate(("#5f7d8c", "#e8e4d8")): rot_car(-1.8 + k * 3.4, y0 + LOTD - 3.1, c)
    mailboxes(-1.9, y0 + 0.9, 6)

def lot_rm6():
    y0 = lot_base("rm6"); by = y0 + 3.2
    midrise(0, by, W=6.6, floors=5, D=25, shop=False, panel="#dfe3e6", seed=8)                 # five floors, two homes on each
    box(3.32, by + 12.5, 0.6, 0.1, 0.5, 15.0, mat("#4a4f57", rough=0.6), bevel=0.02)
    paved(1.65, y0 + 1.6, 1.5, 3.2)
    paved(0, y0 + LOTD - 4.4, LOTW - 0.6, 8.4, col="alley", h=0.14)
    mailboxes(-1.45, y0 + 0.9, 10)
    for k, c in enumerate(("#c9ced3", "#2b5da0")): rot_car(-1.8 + k * 3.4, y0 + LOTD - 4.6, c)

def rot_car(x, y, col):
    """A parked car pointing down the lot (along y)."""
    box(x, y, 0.33, 1.8, 4.3, 0.62, mat(col, rough=0.35, spec=0.6), bevel=0.2); box(x, y - 0.25, 0.91, 1.6, 2.2, 0.56, mat("#4f6f8f", rough=0.15, spec=0.7), bevel=0.2)
    for dy in (-1.3, 1.3):
        for dx in (-0.86, 0.86):
            o = cyl(x + dx, y + dy, 0, 0.33, 0.22, mat("#1f2227", rough=0.8), verts=14); o.location = (x + dx, y + dy, 0.38); o.rotation_euler = (0, math.pi / 2, 0)

LOTS = {"lot_rm6": lot_rm6, "lot_rs3": lot_rs3, "lot_rt4": lot_rt4, "lot_rm5": lot_rm5}      # the tallest first: it sets the shared camera

# ---------- Progress: the same block at three stages, and a yardstick ----------
def progress():
    w, d = 62, 26; slab(w, d); f = -d / 2; W = w - 0.5
    box(0, f + 2.2, 0, W, 4.0, 0.05, mat(ASPHALT, rough=0.9), bevel=0.02); box(0, f + 4.35, 0, W, 0.3, 0.2, mat("curb", rough=0.8), bevel=0.04)
    box(0, f + 6.6, 0, W, 4.2, 0.16, mat("curb", rough=0.85), bevel=0.03); box(0, f + 17.2, 0, W, 17.0, 0.08, mat(GRASS, rough=0.95), bevel=0.04)
    y0 = f + 10.5
    box(-21, y0 + 6, 0.1, 15, 13, 0.06, mat("#cdbfa6", rough=0.95), bevel=0.05)                  # staked out
    for sx in (-6.5, 6.5):
        for sy in (-5.5, 5.5): box(-21 + sx, y0 + 6 + sy, 0, 0.12, 0.12, 1.2, "star", bevel=0)
    hardhat(-22, y0 + 3); hardhat(-19.5, y0 + 4.2, "#e07a3f")
    frame_up(-1, y0, 15, 12, 6, done=2)                                                         # going up
    crane(9, y0 + 9, 0, 25, 14, ang=math.radians(190), m=mat("star", rough=0.45))
    midrise(20, y0, W=15, floors=6, D=12, seed=4); star(20, y0 + 6, 26.2, 1.5)                    # done
    cyl(20, y0 + 6, 22.6, 0.07, 2.4, "steel", verts=8, bevel=0)
    # the yardstick laid along the street, filled in navy up to a red marker a bit past halfway
    yy = f + 2.2
    box(0, yy, 0.05, 56, 3.0, 0.7, mat("#f7f8f5", rough=0.5), bevel=0.12)
    box(-28 + 16.5, yy, 0.75, 33, 3.0, 0.06, mat("navy", rough=0.5), bevel=0.02)
    for k in range(57):
        h = 1.9 if k % 10 == 0 else 1.3 if k % 5 == 0 else 0.7
        box(-28 + k, yy - 1.5 + h / 2 + 0.1, 0.81 if k <= 33 else 0.75, 0.16, h, 0.03, "white" if k <= 33 else "ink", bevel=0)
    box(5, yy, 0.05, 0.7, 3.5, 2.6, mat("star", rough=0.45), bevel=0.12)
    for x in (-29, -11, 10, 29): tree(x, f + 22, 1.0)
    crowd(-26, 26, f + 5.4, f + 7.6, 9, seed=6)

def build(name, out, k=1.0, samples=44):
    reset(); random.seed(1); PS[0] = 1.45 if name in TOPICS or name == "progress" else 1.0
    if name in TOPICS:
        TOPICS[name](); w, h = int(1800 * k), int(720 * k)
        rig(60, target=(0, 0, 2), elev=25, azim=-73, sun=(46, -28), sun_e=3.3, world="#eef3f8", world_e=0.62)
        fit(bpy.context.scene.camera, w / h, margin=1.04)
    elif name in LOTS:
        LOTS[name](); w, h = int(900 * k), int(720 * k)
        rig(50, target=(0, 0, 4), elev=30, azim=-40, sun=(50, -12), sun_e=3.4, world="#eef3f8", world_e=0.6)
        cam = bpy.context.scene.camera
        if "cam" not in LOTCAM: LOTCAM["cam"] = fit(cam, w / h, margin=1.04)
        cam.data.ortho_scale, cam.data.shift_x, cam.data.shift_y = LOTCAM["cam"]
    else:
        progress(); w, h = int(1600 * k), int(760 * k)
        rig(60, target=(0, 0, 3), elev=27, azim=-62, sun=(48, -25), sun_e=3.3, world="#eef3f8", world_e=0.62)
        fit(bpy.context.scene.camera, w / h, margin=1.04)
    if name == "modes":                                                                     # two shadow planes: the street's, and a lower one under the subway cutaway
        for cx_, z_ in ((-174, -1.25), (226, -8.3)):
            bpy.ops.mesh.primitive_plane_add(size=400, location=(cx_, 0, z_)); bpy.context.object.is_shadow_catcher = True
    else: shadow_catcher(z=-1.25)
    render(os.path.abspath(out), w, h, samples=samples)
LOTCAM = {}

if __name__ == "__main__":
    name, outdir = sys.argv[1], sys.argv[2]; k = float(sys.argv[3]) if len(sys.argv) > 3 else 1.0
    os.makedirs(outdir, exist_ok=True)
    names = list(TOPICS) + list(LOTS) + ["progress"] if name == "all" else list(LOTS) if name == "lots" else name.split(",")
    if any(n in LOTS for n in names) and "lot_rm6" not in names: names = ["lot_rm6"] + names   # the shared camera comes from the tallest
    for n in names:
        if n == "lot_rm6" and name not in ("all", "lots") and "lot_rm6" not in name.split(","):
            reset(); LOTS[n](); rig(50, target=(0, 0, 4), elev=30, azim=-40); LOTCAM["cam"] = fit(bpy.context.scene.camera, 900 / 720, margin=1.04); continue
        build(n, os.path.join(outdir, n + ".png"), k)
