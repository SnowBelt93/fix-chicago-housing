"""Scenes for Shape Chicago's illustrations. Each function builds one scene with kit.py and returns (ortho_scale, target, cam kwargs)."""
import math, random
from kit import *

def ground(w, d, lake_x=None):
    """Diorama base: a soil layer with a ground slab on top; optional lake on the east edge."""
    box(0, 0, -3.2, w, d, 2.6, mat("earth", rough=0.95), bevel=0.25)
    gw = w if lake_x is None else (lake_x + w / 2)
    box(-w / 2 + gw / 2, 0, -0.6, gw, d, 0.6, mat("ground", rough=0.9), bevel=0.2)
    if lake_x is not None:
        lw = w / 2 - lake_x
        box(lake_x + lw / 2, 0, -0.75, lw, d, 0.5, mat("lake", rough=0.08, spec=0.6), bevel=0.15)
        box(lake_x + 0.6, 0, -0.6, 1.2, d, 0.75, "stone", bevel=0.08)     # seawall / lakefront path edge

def street(x, y, w, d, rot=0.0, lane=True):
    box(x, y, 0, w, d, 0.04, mat("street", rough=0.9), bevel=0, rot=rot)
    if lane:
        horiz = w > d
        n = int((w if horiz else d) / 4)
        for i in range(n):
            o = -((w if horiz else d) / 2) + 2 + i * 4
            if horiz: box(x + o, y, 0.04, 2.0, 0.18, 0.01, "white", bevel=0)
            else: box(x, y + o, 0.04, 0.18, 2.0, 0.01, "white", bevel=0)

def sidewalk(x, y, w, d):
    box(x, y, 0, w, d, 0.18, mat("curb", rough=0.85), bevel=0.04)

def dibs_chair(x, y, rot=0.3):
    """Chicago's winter tradition: a lawn chair holding a shoveled parking spot. Plus a cone, for emphasis."""
    c, s = math.cos(rot), math.sin(rot)
    box(x, y, 0.45, 0.8, 0.75, 0.08, mat("#3f8fc9", rough=0.5), bevel=0.02, rot=rot)                 # seat
    box(x - 0.36 * s * -1 + 0.36 * c * 0, y + 0.36 * c, 0.45, 0.8, 0.08, 0.85, mat("#3f8fc9", rough=0.5), bevel=0.02, rot=rot)  # back
    for dx, dy in ((-0.35, -0.3), (0.35, -0.3), (-0.35, 0.3), (0.35, 0.3)):
        box(x + dx * c - dy * s, y + dx * s + dy * c, 0, 0.06, 0.06, 0.48, "#cfd3d8", bevel=0)
    cyl(x + 1.1, y - 0.4, 0, 0.32, 0.8, mat("#f26b1d", rough=0.5), verts=16, r2=0.06, bevel=0)
    box(x + 1.1, y - 0.4, 0, 0.75, 0.75, 0.06, mat("#f26b1d", rough=0.5), bevel=0.02)

def water_tower(x, y, z, s=1.0):
    for dx, dy in ((-0.7, -0.7), (0.7, -0.7), (-0.7, 0.7), (0.7, 0.7)):
        box(x + dx * s, y + dy * s, z, 0.14 * s, 0.14 * s, 2.0 * s, "steel", bevel=0)
    cyl(x, y, z + 2.0 * s, 1.15 * s, 2.4 * s, mat("#9b6b4a", rough=0.8), verts=24, bevel=0.04)
    cyl(x, y, z + 4.4 * s, 1.25 * s, 1.0 * s, mat("#7a5238", rough=0.8), verts=24, r2=0.12 * s, bevel=0)

def star_flag(x, y, z, h=3.0):
    cyl(x, y, z, 0.06, h, "white", verts=8, bevel=0)
    box(x + 0.75, y, z + h - 0.9, 1.5, 0.05, 0.9, "white", bevel=0.01)
    # a six-point star as two stacked triangles
    import bpy
    for k in (0, 1):
        bpy.ops.mesh.primitive_cone_add(vertices=3, radius1=0.33, radius2=0, depth=0.06, location=(x + 0.75, y - 0.04, z + h - 0.45),
                                        rotation=(math.radians(90), math.radians(90 + 180 * k), 0))
        o = bpy.context.object; o.data.materials.append(mat("star", rough=0.5))

def hero():
    """The real city, building by building: a slice of a lakefront neighborhood. Old two- and three-flats, the L with a
    train, a new mid-rise going up while a crane sets a little three-flat on its roof, and a dibs chair holding a spot."""
    random.seed(4)
    W, D = 64, 46
    ground(W, D, lake_x=22)
    # an east-west street across the front third, a north-south side street, the L alley
    street(-4, -9.5, 52, 8.5); sidewalk(-4, -3.9, 52, 1.6); sidewalk(-4, -14.6, 52, 1.8)
    box(-4, -4.95, 0, 52, 1.2, 0.2, mat("#bfd6ad", rough=0.95), bevel=0.04)   # parkway grass
    street(-13, 9.5, 8, 26); sidewalk(-17.9, 9.5, 1.8, 26); sidewalk(-8.1, 9.5, 1.8, 26)
    box(6.5, 9.5, 0, 5.5, 26, 0.05, mat("alley", rough=0.9), bevel=0)
    # lakefront path, trees, and the lake
    box(19.8, 0, 0, 3.0, D - 2, 0.12, mat("#e6e2d6", rough=0.9), bevel=0.05)
    for yy in (-19, -12, 1, 9, 17):
        tree(17.6, yy, 0, 0.9, random.choice(["tree", "tree2"]))
    for k in range(3):   # Chicago's limestone step revetment at the water's edge
        box(22.4 + k * 0.9, 0, -0.6 - k * 0.12, 0.9, D - 3, 0.62 - k * 0.12, mat("#e3dccb", rough=0.85), bevel=0.05)
    # back row of buildings along the north edge
    for i, (bx, fl, wl) in enumerate([(-28, 3, "grey"), (-20.6, 2, "brick"), (-4.0, 3, "buff")]):
        pass
    # a little park in the front strip
    box(-12, -19.5, 0, 36, 7.5, 0.16, mat("#cfe0c0", rough=0.95), bevel=0.06)
    for xx in (-27, -20, -13, -6, 1):
        tree(xx + random.uniform(-1, 1), -19.5 + random.uniform(-1.4, 1.4), 0.16, random.uniform(0.85, 1.1), random.choice(["tree", "tree2"]))
    box(-9.5, -17.6, 0.16, 2.2, 0.6, 0.45, mat("#8a6a4f", rough=0.7), bevel=0.05)   # bench
    # north-west block: a row of two- and three-flats facing the street
    walls = ["brick", "buff", "brick2", "grey", "brick", "buff"]
    for i in range(2):
        flat(-29 + i * 7.6, 3.2, 0.18, 7.0, 12, 2 + i, walls[i], faces=("-y", "-x") if i == 0 else ("-y",))
    water_tower(-21.4, 5.5, 0.18 + 3 * 3.2 + 1.05, 0.85)
    # between the side street and the L: more flats
    flat(-4.2, 3.2, 0.18, 7.0, 12, 3, walls[2], faces=("-y", "-x"))
    flat(2.6 - 0.4, 3.2, 0.18, 6.4, 12, 2, walls[3])
    flat(-3.4, 17.5, 0.18, 8.5, 10, 2, walls[4], faces=("-y", "-x"))
    # the L: a Red Line train on the steel structure in the alley
    el_track([(6.5, -24), (6.5, 24)], z=7.2, train="star", train_at=0.3, cars=2, stripe="star")
    # the new mid-rise (navy) and the crane setting a tiny three-flat on its roof
    mz = 0.18; mx, my = 14.0, 7.5
    box(mx, my, mz, 9.5, 17, 6 * 3.1, mat("navy", rough=0.55), bevel=0.12)
    for f in range(6):
        zz = mz + 0.5 + f * 3.1
        for c in range(4):
            box(mx - 4.75 - 0.03, my - 6.3 + c * 4.2, zz, 0.06, 2.2, 1.9, mat("glass", rough=0.12, spec=0.8), bevel=0.01)
        for c in range(2):
            box(mx - 2.4 + c * 4.8, my - 8.5 - 0.03, zz, 2.6, 0.06, 1.9, mat("glass", rough=0.12, spec=0.8), bevel=0.01)
    box(mx, my, mz + 18.6, 9.9, 17.4, 0.45, mat("navy2", rough=0.5), bevel=0.06)
    for dx in (-4.3, 4.3):
        for dy in (-8.0, 0, 8.0):
            box(mx + dx, my + dy, mz + 19.05, 0.3, 0.3, 3.0, "white", bevel=0.02)
    for dy in (-8.0, 8.0): box(mx, my + dy, mz + 21.9, 8.9, 0.3, 0.3, "white", bevel=0.02)
    for dx in (-4.3, 4.3): box(mx + dx, my, mz + 21.9, 0.3, 16.3, 0.3, "white", bevel=0.02)
    hx, hy = crane(11.5, 21.0, 0.05, 30, 21, ang=math.radians(-78), m=mat("star", rough=0.45), hook_box=(0, 0, 26.4, 0))
    box(hx, hy, 23.0, 3.0, 3.6, 3.3, "buff", bevel=0.06)
    box(hx, hy, 26.3, 3.2, 3.8, 0.25, "stone", bevel=0.02)
    for f in range(3):
        box(hx - 1.53, hy - 0.6, 23.3 + f * 1.05, 0.05, 1.0, 0.6, "glass", bevel=0.005)
        box(hx + 0.2, hy - 1.83, 23.3 + f * 1.05, 1.4, 0.05, 0.6, "glass", bevel=0.005)
    star_flag(11.5, 21.0, 0.05 + 30 + 3.3, h=2.4)
    # street life: cars and the dibs chair
    car(-26, -12.2, 0.04, 0, mat("#e6e8eb", rough=0.35, metal=0.3))
    car(-1, -6.9, 0.04, math.pi, mat("#2f3a46", rough=0.35, metal=0.3))
    car(13, -12.2, 0.04, 0, mat("#c9473a", rough=0.35, metal=0.3))
    dibs_chair(-17.5, -12.3, rot=0.2)
    return dict(ortho=93, target=(0, 4, 11.5), elev=31, azim=-118, sun=(38, -165))

def housing():
    """What can go up: one block face, lot by lot, from today's bungalow to a high-rise, in the tool's map colors,
    with a crane still working on the tallest one."""
    random.seed(7)
    ground(78, 30)
    street(0, -10.5, 78, 8); sidewalk(0, -5.6, 78, 1.8)
    box(0, -4.3, 0, 78, 0.9, 0.2, mat("#bfd6ad", rough=0.95), bevel=0.03)
    lots = [("grey", 1, 0), ("lt3", 3, 1), ("lt6", 4, 2), ("mid", 6, 3), ("hi", 12, 4)]
    x = -32
    widths = [8, 8.5, 10, 13, 15]
    for (col, fl, k), w in zip(lots, widths):
        d = 13 if k < 3 else 16
        y = 2.5 + (d - 13) / 2
        if k == 0:   # today's bungalow with a hip roof
            box(x + w / 2, y, 0.18, w - 1, 11, 4.0, "grey", bevel=0.06)
            box(x + w / 2, y, 4.18, w - 0.4, 11.6, 1.6, mat("roof", rough=0.85), bevel=0.6)
            windows(x + w / 2, y, 0.9, w - 1, 11, 2.6, 1, face="-y", glass="glass", cols=2, band=0.6)
            box(x + w / 2, y - 6.4, 0.18, 2.0, 1.6, 0.6, "stone", bevel=0.03)
        else:
            m = mat(col, rough=0.6)
            h = fl * 3.2
            box(x + w / 2, y, 0.18, w - 1, d, h, m, bevel=0.1)
            box(x + w / 2, y, 0.18 + h, w - 0.7, d + 0.3, 0.35, mat("white", rough=0.6), bevel=0.04)
            for f in range(fl):
                zz = 0.18 + 0.5 + f * 3.2
                n = max(2, int((w - 1) / 3.2))
                for c in range(n):
                    box(x + 0.5 + (w - 1) * (c + 0.5) / n, y - d / 2 - 0.03, zz, (w - 1) / n * 0.55, 0.06, 1.8, mat("#eaf5fb", rough=0.15, spec=0.8), bevel=0.01)
                for c in range(max(2, int(d / 3.4))):
                    box(x + w - 0.5 + 0.03, y - d / 2 + d * (c + 0.5) / max(2, int(d / 3.4)), zz, 0.06, 1.6, 1.8, mat("#eaf5fb", rough=0.15, spec=0.8), bevel=0.01)
        if k < 4: tree(x + w - 0.2, -4.3, 0.2, 0.75, random.choice(["tree", "tree2"]))
        x += w + 1.0
    # the crane on the high-rise: it's still going up
    crane(x + 2.5, 8, 0.05, 44, 16, ang=math.radians(-170), m=mat("star", rough=0.45))
    star_flag(x + 2.5, 8, 0.05 + 44 + 3.3, h=2.4)
    car(-20, -12.4, 0.04, 0, mat("#e6e8eb", rough=0.35, metal=0.3))
    car(8, -8.6, 0.04, math.pi, mat("#c9473a", rough=0.35, metal=0.3))
    return dict(ortho=124, target=(6, 4, 24), elev=34, azim=-112, sun=(40, -160))

def lot():
    """What can I build on my lot: a block face of old flats and a bungalow; one lot picked with a red pin, and the
    biggest building its zoning allows drawn over it as a glass ghost."""
    random.seed(11)
    ground(70, 30)
    street(0, -10.5, 70, 8); sidewalk(0, -5.6, 70, 1.8)
    box(0, -4.3, 0, 70, 0.9, 0.2, mat("#bfd6ad", rough=0.95), bevel=0.03)
    x = -33
    plan = [("brick", 2), ("buff", 3), ("grey", 0), ("brick2", 2), ("stone", 3), ("brick", 2), ("buff", 3)]
    for i, (col, fl) in enumerate(plan):
        w = 8.6
        if fl == 0:   # the picked lot: today's bungalow, the ghost of what's allowed, a pin
            box(x + w / 2, 2.5, 0.18, w - 1.2, 11, 4.0, "grey", bevel=0.06)
            box(x + w / 2, 2.5, 4.18, w - 0.6, 11.6, 1.6, mat("roof", rough=0.85), bevel=0.6)
            windows(x + w / 2, 2.5, 0.9, w - 1.2, 11, 2.6, 1, face="-y", glass="glass", cols=2, band=0.6)
            box(x + w / 2, 3.2, 0.18, w - 0.6, 14.5, 13.2, mat("#7fb0e0", rough=0.1, alpha=0.28, spec=0.7), bevel=0.08)
            for f in range(1, 4):
                box(x + w / 2, 3.2, 0.18 + f * 3.3, w - 0.5, 14.6, 0.08, mat("navy", rough=0.5), bevel=0)
            cyl(x + w / 2, -7.2, 0.2, 0.09, 5.2, "ink", verts=8, bevel=0)
            sphere(x + w / 2, -7.2, 5.9, 0.9, mat("star", rough=0.4))
            pick_x = x + w / 2
        else:
            flat(x + w / 2, 2.5, 0.18, w - 1.0, 11, fl, col, fh=3.2, cols=2, cornice="stone")
        if i in (1, 4): tree(x + w - 0.1, -4.3, 0.2, 0.75, random.choice(["tree", "tree2"]))
        x += w + 0.8
    car(14, -12.4, 0.04, 0, mat("#e6e8eb", rough=0.35, metal=0.3))
    return dict(ortho=74, target=(-1, 0, 2), elev=30, azim=-108, sun=(42, -150))

def budget():
    """Balance the Chicago Budget: a balance beam on a city block, a stack of coins on one pan and a little block of
    flats, a fire station and a bus on the other, level."""
    random.seed(5)
    ground(64, 34)
    sidewalk(0, -12, 64, 2.2)
    # the fulcrum and beam
    cyl(0, 0, 0.0, 2.2, 1.0, mat("steel", rough=0.4), verts=32)
    box(0, 0, 1.0, 1.6, 1.6, 12.0, mat("steel", rough=0.4), bevel=0.15)
    cyl(0, 0, 13.0, 1.0, 1.4, mat("star", rough=0.4), verts=24)
    box(0, 0, 13.6, 44, 1.2, 0.8, mat("navy", rough=0.45, metal=0.2), bevel=0.2)
    for sx in (-20, 20):
        for dy in (-0.4, 0.4):
            box(sx, dy, 6.6, 0.12, 0.12, 7.0, "ink", bevel=0)
        cyl(sx, 0, 5.9, 7.2, 0.7, mat("#d9dde2", rough=0.35, metal=0.4), verts=48)
    # left pan: stacks of coins
    for i, (dx, dy, n) in enumerate([(-2.2, -1.5, 9), (1.6, -1.8, 6), (-0.4, 2.0, 12), (2.8, 1.6, 4), (-3.4, 1.2, 3)]):
        for k in range(n):
            cyl(-20 + dx, dy, 6.6 + k * 0.62, 1.55, 0.56, mat("gold", rough=0.3, metal=0.75), verts=28, bevel=0.06)
    # right pan: a tiny city block
    flat(20 - 2.6, 0.4, 6.6, 3.6, 4.8, 3, "brick", fh=1.4, cols=2, cornice="stone")
    flat(20 + 1.6, 0.6, 6.6, 3.6, 4.8, 2, "buff", fh=1.4, cols=2, cornice="stone")
    box(20, -3.4, 6.6, 6.0, 1.9, 1.6, mat("#f4f5f6", rough=0.35), bevel=0.4)          # a bus
    box(20, -4.37, 7.5, 5.4, 0.05, 0.5, "glassdk", bevel=0)
    tree(20 + 4.6, 2.4, 6.6, 0.45)
    tree(-26, 9, 0, 0.9); tree(27, 10, 0, 0.8); tree(-9, -10, 0, 0.7)
    return dict(ortho=54, target=(0, -1, 7), elev=22, azim=-100, sun=(42, -150))

def pensions():
    """Pay Down Chicago's Pensions: four coin stacks, one per fund, each in an open frame with a flag-blue ring at 90%,
    on a little plaza in front of a row of flats."""
    random.seed(11)
    ground(70, 34)
    sidewalk(0, -12, 70, 2.2)
    for i, (x, fill) in enumerate([(-19.5, 0.27), (-6.5, 0.42), (6.5, 0.26), (19.5, 0.26)]):
        cyl(x, 0, 0.0, 4.0, 0.6, mat("navy", rough=0.45), verts=40)                           # base
        h = 14.0
        for a in range(4):                                                                     # frame posts
            import math
            px, py = x + 3.2 * math.cos(a * math.pi / 2 + .6), 3.2 * math.sin(a * math.pi / 2 + .6)
            box(px, py, 0.6, 0.22, 0.22, h, mat("steel", rough=0.4), bevel=0)
        cyl(x, 0, 0.6 + h, 3.5, 0.3, mat("steel", rough=0.4), verts=40)                        # rim
        cyl(x, 0, 0.6 + h * 0.9, 3.45, 0.28, mat("#41b6e6", rough=0.4), verts=40)              # the 90% ring
        n = max(1, int(h * fill / 0.6))
        for k in range(n):
            cyl(x, 0, 0.7 + k * 0.6, 2.8, 0.55, mat("gold", rough=0.3, metal=0.75), verts=40, bevel=0.05)
    for i, x in enumerate(range(-33, 36, 10)):
        flat(x, 12, 0.18, 8.6, 6, 2 + (i % 2), ["brick", "buff", "brick2", "grey"][i % 4])
    tree(-29, -6, 0, 0.8); tree(29, -6, 0, 0.7)
    return dict(ortho=66, target=(0, 0, 8), elev=18, azim=-96, sun=(42, -150))

def transit():
    """Draw your own line: today's L on its steel structure with a Red Line train, and a new line in flag blue curving off
    from a new station, its own train already running."""
    random.seed(9)
    ground(80, 34)
    street(0, -8, 80, 8); sidewalk(0, -3.2, 80, 1.6); sidewalk(0, -12.8, 80, 1.6)
    for i, x in enumerate(range(-36, 34, 9)):
        if -6 < x < 8: continue
        flat(x, 6.5, 0.18, 8.0, 11, 2 + (i % 2), ["brick", "buff", "brick2", "grey"][i % 4])
    el_track([(-40, -1.0), (40, -1.0)], z=7.6, train="star", train_at=0.04, cars=3, stripe="star")
    # the station: a platform canopy over the structure
    box(2, -1.0, 9.3, 18, 6.4, 0.25, mat("steel", rough=0.6), bevel=0.04)
    box(2, -1.0, 12.0, 18.6, 7.2, 0.35, mat("navy", rough=0.5), bevel=0.06)
    for dx in (-8, 0, 8):
        for dy in (-2.9, 2.9): box(2 + dx, -1.0 + dy, 9.5, 0.25, 0.25, 2.5, "steel", bevel=0.02)
    # your new line: its own flag-blue structure starting at a new platform beside today's station (a transfer, not
    # under the L), then curving off toward the camera with its own train
    box(2, -8.8, 7.6, 16, 4.6, 0.85, mat("flag", rough=0.5), bevel=0.06)                 # new platform deck
    box(2, -8.8, 11.4, 16.6, 5.0, 0.3, mat("flag", rough=0.5), bevel=0.05)               # its canopy
    for dx in (-7, 0, 7):
        box(2 + dx, -8.8, 0, 0.8, 0.8, 7.6, mat("#e9eef2", rough=0.6), bevel=0.05)
        box(2 + dx, -10.8, 8.45, 0.22, 0.22, 2.95, "steel", bevel=0.02)
    box(2, -5.2, 8.3, 3.0, 2.6, 0.18, "steel", bevel=0.02)                                # walkway to the L platform
    P0, P1, P2 = (10, -8.8), (24, -8.8), (30, -24)
    bez = lambda t: ((1 - t) ** 2 * P0[0] + 2 * (1 - t) * t * P1[0] + t * t * P2[0], (1 - t) ** 2 * P0[1] + 2 * (1 - t) * t * P1[1] + t * t * P2[1])
    pts = [bez(i / 18) for i in range(19)]
    ribbon(pts, 4.6, 0.85, 7.6, mat("flag", rough=0.5))
    for i in range(3, len(pts), 3): box(pts[i][0], pts[i][1], 0, 0.8, 0.8, 7.6, mat("#e9eef2", rough=0.6), bevel=0.05)
    for t0 in (0.34, 0.62):   # two cars of your new train, bent to the curve
        car_pts = [bez(t0 + k * 0.022) for k in range(12)]
        ribbon(car_pts, 2.8, 3.0, 8.5, mat("#f4f8fb", rough=0.35, metal=0.2), name="car")
        win = [bez(t0 + 0.03 + k * 0.02) for k in range(10)]
        for side in (1.42, -1.42):
            sp = []
            for i, (x, y) in enumerate(win):
                a = win[max(0, i - 1)]; b = win[min(len(win) - 1, i + 1)]; tx, ty = b[0] - a[0], b[1] - a[1]; L = math.hypot(tx, ty) or 1
                sp.append((x - ty / L * side, y + tx / L * side))
            ribbon(sp, 0.08, 1.0, 9.95, "glassdk", name="win"); ribbon(sp, 0.08, 0.28, 9.25, mat("flag", rough=0.5), name="stripe")
    for xx in (-30, -18, 16, 28): tree(xx, -3.2 - 0.0, 0.18, 0.8, random.choice(["tree", "tree2"]))
    car(-24, -10, 0.04, 0, mat("#e6e8eb", rough=0.35, metal=0.3)); car(20, -6, 0.04, math.pi, mat("#2f3a46", rough=0.35, metal=0.3))
    return dict(ortho=74, target=(2, -4, 6.5), elev=27, azim=-104, sun=(40, -160))

def tracker():
    """What Chicago actually builds: a bar chart where every bar is a building, one per year (one floor per 600 homes
    permitted), the newest still going up under a crane. In front, a permit with the red star stamp."""
    random.seed(3)
    # homes permitted in Chicago, 2016 to 2026 so far, from the Permit Tracker (tracker/data.json): one floor per 600 homes
    vals = [9044, 8822, 6305, 6544, 3765, 5150, 7285, 4027, 3226, 3908, 3359]
    W = len(vals) * 5.0 + 10
    box(0, 0, -1.2, W, 16, 1.2, mat("ground", rough=0.9), bevel=0.3)
    x0 = -W / 2 + 5
    FH = 1.3
    glass = mat("#dff1fb", rough=0.12)
    for i, v in enumerate(vals):
        fl = max(1, int(round(v / 600))); x = x0 + i * 5.0
        last = i == len(vals) - 1
        built = fl - 2 if last else fl
        wall = mat("flag" if last else ("navy" if i % 2 == 0 else "navy2"), rough=0.6)
        box(x, 0, 0, 3.9, 3.9, 0.5, mat("stone", rough=0.8), bevel=0.05)                  # plinth
        box(x, 0, 0.5, 3.6, 3.6, built * FH, wall, bevel=0.07)                              # body
        for f in range(built):                                                              # a window band per floor
            z = 0.5 + f * FH + 0.38
            box(x, -1.82, z, 3.0, 0.06, 0.55, glass, bevel=0.01)
            box(x + 1.82, 0, z, 0.06, 3.0, 0.55, glass, bevel=0.01)
        top = 0.5 + built * FH
        if not last:
            box(x, 0, top, 3.7, 3.7, 0.35, mat("hi", rough=0.6), bevel=0.04)                 # parapet cap
            box(x + 0.6, 0.4, top + 0.35, 1.2, 1.0, 0.7, mat("grey", rough=0.7), bevel=0.05)   # rooftop box
        else:                                                                                # two floors still framed out
            for f in range(2):
                zf = top + f * FH
                box(x, 0, zf, 3.6, 3.6, 0.16, mat("stone", rough=0.8), bevel=0.02)
                for ox in (-1.6, 1.6):
                    for oy in (-1.6, 1.6): box(x + ox, oy, zf + 0.16, 0.22, 0.22, FH - 0.16, mat("stone", rough=0.8), bevel=0.02)
            last_top = top + 2 * FH
            xl = x
    # the crane beside the newest building: mast, a jib reaching over it, the counterweight sitting on the short back arm
    cx, cy, H = xl + 4.2, 1.6, last_top + 7.5
    st = mat("star", rough=0.45)
    box(cx, cy, 0, 1.4, 1.4, 0.4, mat("grey", rough=0.8), bevel=0.03)
    box(cx, cy, 0.4, 1.0, 1.0, H, st, bevel=0.03)
    for k in range(int(H / 1.6)): box(cx, cy, 0.4 + k * 1.6 + 0.8, 1.08, 1.08, 0.1, "white", bevel=0)
    box(cx, cy, 0.4 + H, 1.3, 1.3, 1.1, mat("white", rough=0.5), bevel=0.08)                  # cab
    box(cx - 2.0, cy, 0.4 + H + 1.1, 14.4, 0.7, 0.7, st, bevel=0.03)                          # jib + back arm, one piece
    box(cx + 4.4, cy, 0.4 + H + 1.8, 1.6, 1.0, 1.4, mat("grey", rough=0.7), bevel=0.06)        # counterweight, on the arm
    hx = cx - 4.6
    cyl(hx, cy, last_top + 2.6, 0.05, 0.4 + H + 1.1 - (last_top + 2.6), "ink", verts=6, bevel=0)
    box(hx, cy, last_top + 1.6, 1.8, 1.0, 1.0, mat("buff", rough=0.7), bevel=0.05)              # a load of brick on its way
    # the permit and its stamp
    box(-W / 2 + 9, -6.0, 0, 7, 5.2, 0.08, mat("white", rough=0.7), bevel=0.02, rot=math.radians(-8))
    for k in range(4): box(-W / 2 + 8.4, -5.0 - k * 0.9, 0.09, 4.6, 0.25, 0.02, mat("#c9ced4", rough=0.8), bevel=0, rot=math.radians(-8))
    cyl(-W / 2 + 11.2, -7.0, 0.09, 1.0, 0.03, mat("star", rough=0.6), verts=40, bevel=0)
    cyl(-W / 2 + 11.2, -7.0, 0.12, 0.72, 0.03, mat("white", rough=0.6), verts=40, bevel=0)
    return dict(ortho=72, target=(1, -3, 9), elev=24, azim=-110, sun=(40, -160))


def prism(ring, z, h, m, name="prism"):
    """Extrude one polygon ring (scene x, y) from z up by h."""
    import bmesh
    me = bpy.data.meshes.new(name); bm = bmesh.new()
    vs = [bm.verts.new((x, y, z)) for x, y in ring]
    try: f = bm.faces.new(vs)
    except ValueError: bm.free(); return None
    r = bmesh.ops.extrude_face_region(bm, geom=[f])
    for v in [e for e in r["geom"] if isinstance(e, bmesh.types.BMVert)]: v.co.z += h
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); bpy.context.scene.collection.objects.link(o)
    o.data.materials.append(m if not isinstance(m, str) else mat(m))
    mod = o.modifiers.new("bev", "BEVEL"); mod.width = 0.08; mod.segments = 2; mod.limit_method = "ANGLE"
    return o

def wards():
    """Ward housing records: all 50 wards as raised clay tiles, each as tall as the homes it permitted in the last 12
    months (Permit Tracker, tracker/data.json), the tallest marked with a red star. Seen from over the lake."""
    import json, os
    root = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
    W = json.load(open(os.path.join(root, "wards.json")))
    T = {w["ward"]: w for w in json.load(open(os.path.join(root, "tracker", "data.json")))["wards"]}
    lon0, lat0, k = -87.68, 41.84, 1.3        # 1.3 scene units per km
    kx, ky = 111.32 * math.cos(math.radians(lat0)) * k, 110.57 * k
    P = lambda lo, la: ((lo - lon0) * kx, (la - lat0) * ky)
    top = max(T[w]["last12"] for w in T)
    ramp = ["#86c6e8", "#56b0e0", "#3a96d2", "#2f74b8", "#2b5da0", "#1d4580"]
    best = max(T, key=lambda w: T[w]["last12"])
    box(-4, -1, -2.4, 56, 62, 1.8, mat("#dfe2da", rough=0.9), bevel=0.25)
    box(20, -1, -0.75, 8, 62, 0.5, mat("lake", rough=0.08, spec=0.6), bevel=0.15)    # the lake along the east edge
    for w in W:
        n = T.get(w["ward"], {}).get("last12", 0); f = (n / top) ** 0.6
        h = 0.4 + 10 * f; col = ramp[min(5, int(f * 5.99))]
        for poly in w["polys"]:
            ring = [P(*p) for p in poly[0]]
            if len(ring) > 3 and ring[0] == ring[-1]: ring = ring[:-1]
            # simplify: drop points closer than 0.15 units
            out = [ring[0]]
            for p in ring[1:]:
                if math.hypot(p[0] - out[-1][0], p[1] - out[-1][1]) > 0.15: out.append(p)
            if len(out) >= 3: prism(out, -0.6, h + 0.6, mat(col, rough=0.6), name="w%d" % w["ward"])
        if w["ward"] == best:
            bx, by = P(w["lon"], w["lat"])
            cyl(bx, by, h, 0.12, 3.2, "steel", verts=8, bevel=0)
            star_pin(bx, by, h + 3.2)
    return dict(ortho=74, target=(-5, -1, 1), elev=40, azim=-6, sun=(42, -40))

def star_pin(x, y, z, s=1.0, rot=0.0):
    """A red six-point star standing on edge, facing the camera's side."""
    import bmesh
    me = bpy.data.meshes.new("star"); bm = bmesh.new()
    pts = []
    for i in range(12):
        r = (1.4 if i % 2 == 0 else 0.62) * s; a = math.pi / 2 + i * math.pi / 6
        pts.append((r * math.cos(a), r * math.sin(a)))
    f = bm.faces.new([bm.verts.new((0, px, py)) for px, py in pts])
    r = bmesh.ops.extrude_face_region(bm, geom=[f])
    for v in [e for e in r["geom"] if isinstance(e, bmesh.types.BMVert)]: v.co.x += 0.35 * s
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new("star", me); bpy.context.scene.collection.objects.link(o)
    o.location = (x, y, z + 1.4 * s); o.rotation_euler = (0, 0, rot); o.data.materials.append(mat("star", rough=0.45))
    mod = o.modifiers.new("bev", "BEVEL"); mod.width = 0.06; mod.segments = 2
    return o

def news_box(x, y, col, rot=0.0):
    """A street newspaper box: body on short legs, a slanted lid, a window with today's paper."""
    c, s = math.cos(rot), math.sin(rot)
    for dx in (-0.8, 0.8):
        box(x + dx * c, y + dx * s, 0.18, 0.12, 0.9, 0.5, "steel", bevel=0, rot=rot)
    box(x, y, 0.68, 2.0, 1.5, 2.3, mat(col, rough=0.45), bevel=0.12, rot=rot)
    box(x, y, 2.98, 2.1, 1.6, 0.25, mat(col, rough=0.45), bevel=0.1, rot=rot)
    box(x - 0.76 * s, y - 0.76 * c * 1.0 * (1 if True else 0) + 0.0, 1.55, 1.5, 0.06, 1.05, mat("#dfeaf2", rough=0.1), bevel=0.02, rot=rot)
    box(x - 0.8 * s, y - 0.8 * c, 1.62, 1.2, 0.04, 0.85, "white", bevel=0.01, rot=rot)                 # the paper
    for k in range(3): box(x - 0.83 * s, y - 0.83 * c, 2.25 - k * 0.14, 0.9, 0.02, 0.05, "ink", bevel=0, rot=rot)
    box(x + 0.55 * c - 0.78 * s, y + 0.55 * s - 0.78 * c, 1.1, 0.35, 0.08, 0.3, "steel", bevel=0.02, rot=rot)   # coin box

def news():
    """Chicago planning news: a row of street newspaper boxes in front of a brick flat and a new mid-rise."""
    random.seed(5)
    ground(34, 20)
    sidewalk(0, -3.5, 34, 5); street(0, -8.5, 34, 5)
    flat(-9, 5, 0.18, 9, 9, 3, "brick")
    flat(1, 5, 0.18, 8, 9, 2, "buff", cornice="stone")
    tower(11, 5, 0.18, 9, 9, 6, mat("navy", rough=0.6), faces=("-y", "+x"))
    for (x, col, r) in [(-6.5, "navy", 0.05), (-3.6, "flag", -0.04), (-0.7, "star", 0.03), (2.2, "white", -0.02)]:
        news_box(x, -3.4, col, r)
    tree(9, -3.2, 0.18, 0.8)
    return dict(ortho=30, target=(0, -1, 4), elev=20, azim=-100, sun=(40, -150))

def storefront():
    """'Your Chicago business here': a corner storefront with a flag-blue awning and a blank sign, a sandwich board out front."""
    ground(20, 14)
    sidewalk(0, -3.2, 20, 4)
    box(0, 2, 0.18, 12, 8, 7.4, mat("brick", rough=0.8), bevel=0.06)
    box(0, 2, 7.58, 12.3, 8.2, 0.5, "stone", bevel=0.05)
    windows(0, 2, 4.0, 12, 8, 3.2, 1, face="-y", glass="glass", cols=3)
    box(0, -2.04, 0.5, 10.4, 0.1, 2.6, mat("#cfe7f5", rough=0.08, spec=0.6), bevel=0.02)          # shop window
    box(-3.6, -2.08, 0.5, 1.6, 0.12, 2.9, mat("#e9eef2", rough=0.4), bevel=0.02)                   # door
    box(0, -2.25, 3.35, 9.0, 0.25, 0.85, mat("navy", rough=0.5), bevel=0.05)                        # the blank sign
    box(0, -2.9, 2.95, 11.2, 1.6, 0.18, mat("flag", rough=0.5), bevel=0.04, rot=0.0)                # awning
    for i in range(14): box(-5.2 + i * 0.8, -3.66, 2.7, 0.4, 0.06, 0.3, mat("white" if i % 2 else "flag", rough=0.5), bevel=0)
    # sandwich board
    box(3.6, -3.9, 0.18, 1.2, 0.08, 1.6, mat("ink", rough=0.6), bevel=0.02, rot=0.0).rotation_euler = (math.radians(14), 0, 0.2)
    box(3.6, -3.5, 0.18, 1.2, 0.08, 1.6, mat("ink", rough=0.6), bevel=0.02, rot=0.0).rotation_euler = (math.radians(-14), 0, 0.2)
    tree(-7.5, -3.4, 0.18, 0.7); flat(15, 2, 0.18, 8, 8, 2, "buff")
    return dict(ortho=18, target=(0, -1, 3.6), elev=14, azim=-104, sun=(40, -150))

def jar():
    """Chip in: a tip jar of gold coins with a red star label, on a little block of sidewalk."""
    box(0, 0, -0.5, 9, 7, 0.5, mat("curb", rough=0.85), bevel=0.15)
    g = mat("#dceef8", rough=0.05, spec=0.8, alpha=0.28)
    cyl(0, 0, 0, 1.9, 4.2, g, verts=48, bevel=0.06)
    cyl(0, 0, 4.2, 1.6, 0.45, mat("#d7dbe0", rough=0.3, metal=0.6), verts=48, bevel=0.04)
    for k in range(9):
        a = k * 0.7; cyl(0.25 * math.cos(a), 0.25 * math.sin(a), 0.08 + k * 0.22, 1.35, 0.2, mat("gold", rough=0.3, metal=0.75), verts=36, bevel=0.03)
    for (x, y, z, rx) in [(2.6, -1.2, 0, 0), (3.1, 0.6, 0, 0), (2.8, -0.2, 0.21, 0)]:
        cyl(x, y, z, 0.7, 0.2, mat("gold", rough=0.3, metal=0.75), verts=32, bevel=0.03)
    star_pin(0, -2.0, 1.1, 0.7, rot=math.pi / 2)
    return dict(ortho=10, target=(0.4, 0, 2.1), elev=16, azim=-100, sun=(42, -140))

def stadium():
    """Where should the Bears play: a neutral domed stadium (no team colors or marks) on old industrial land, a train
    pulling into a station on one side and a big parking lot on the other, a red pin asking 'here?'."""
    random.seed(21)
    ground(84, 52)
    # the stadium: an oval bowl with ribs, a lighter roof dome
    bowl = cyl(0, 2, 0.0, 15, 7.5, mat("#e9edf1", rough=0.55), verts=64, bevel=0.15)
    bowl.scale = (1.0, 0.8, 1.0)
    ring = cyl(0, 2, 7.2, 15.6, 1.1, mat("navy", rough=0.45), verts=64, bevel=0.1); ring.scale = (1.0, 0.8, 1.0)
    for i in range(40):   # facade ribs
        a = i / 40 * 2 * math.pi
        box(15.15 * math.cos(a), 2 + 12.12 * math.sin(a), 0, 0.45, 0.45, 7.3, mat("#c9d1da", rough=0.5), bevel=0.04, rot=a)
    sphere(0, 2, 7.9, 14.4, mat("#f6f8fa", rough=0.25, spec=0.6), sub=4, sx=1.0, sy=0.8, sz=0.33)
    sphere(0, 2, 8.4, 7.5, mat("glass", rough=0.08), sub=4, sx=1.0, sy=0.8, sz=0.22)
    # plaza
    box(0, 2, -0.02, 38, 30, 0.08, mat("#dfe3e7", rough=0.8), bevel=0)
    # rail on the north side with a station and a train
    el_track([(-44, 22), (44, 22)], z=0.4, train="flag", train_at=0.62, cars=3, stripe="flag")
    box(-10, 22, 0.4, 16, 6.0, 1.0, mat("#d6dbe0", rough=0.6), bevel=0.05)
    box(-10, 22, 4.2, 16.6, 6.6, 0.3, mat("navy", rough=0.5), bevel=0.05)
    for dx in (-7, 0, 7):
        for dy in (-2.7, 2.7): box(-10 + dx, 22 + dy, 1.4, 0.25, 0.25, 2.8, "steel", bevel=0.02)
    # parking lot on the south-east with cars
    box(28, -12, -0.01, 24, 22, 0.05, mat("#8a9099", rough=0.9), bevel=0)
    cols = ["#e6e8eb", "#2f3a46", "#b9c0c8", "#7a8794", "#c8102e", "#41b6e6"]
    for r in range(5):
        for c in range(9):
            if random.random() < 0.82:
                car(18.5 + c * 2.4, -20 + r * 4.2, 0.04, math.pi / 2, mat(random.choice(cols), rough=0.35, metal=0.3))
    # old industrial sheds and a stack on the west edge
    box(-34, -8, 0, 12, 18, 5.5, mat("brick2", rough=0.85), bevel=0.1)
    box(-34, -8, 5.5, 12.4, 18.4, 0.5, mat("grey", rough=0.8), bevel=0.05)
    cyl(-30, 6, 0, 1.1, 16, mat("brick", rough=0.85), verts=20)
    # trees and a red pin
    for x, y in [(-18, -18), (-22, -14), (16, 16), (22, 14), (-4, -17), (4, -18)]: tree(x, y, 0.05, 0.9, random.choice(["tree", "tree2"]))
    star_pin(12, -6, 14.5, 1.3)
    return dict(ortho=100, target=(2, 1, 4), elev=32, azim=-55, sun=(46, -140))
