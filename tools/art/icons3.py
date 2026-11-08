"""Clay icons for the budget and pension tools: one small diorama per group of options.
    python3.11 tools/art/icons3.py <name|all|a,b> <outdir> [size]
Same tile, light and framing as icons2.py. No text in any icon."""
import sys, os, math, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy
from kit import *
from icons import tile, lawn, walk, pitched, T
from learn import person, bungalow, block, coins
import icons2

def stack(x, y, n, r=1.1, col="gold"):
    for k in range(n): cyl(x, y, k * 0.42, r, 0.38, mat(col, rough=0.3, metal=0.7), verts=24, bevel=0.03)

def columns_building(x, y, w=7.0, d=4.6, h=3.4, dome=False):
    """A generic civic building: steps, columns, a pediment or a dome. No seals or emblems."""
    box(x, y, 0, w + 1.0, d + 1.0, 0.35, "stone", bevel=0.05)
    box(x, y, 0.35, w + 0.5, d + 0.5, 0.3, "stone", bevel=0.05)
    box(x, y + 0.6, 0.65, w, d - 1.2, h, mat("stone", rough=0.7), bevel=0.05)
    n = 6
    for i in range(n):
        cyl(x - w / 2 + 0.5 + i * (w - 1.0) / (n - 1), y - d / 2 + 0.35, 0.65, 0.22, h, mat("white", rough=0.6), verts=12, bevel=0.02)
    box(x, y, 0.65 + h, w + 0.3, d + 0.2, 0.45, mat("stone", rough=0.7), bevel=0.05)
    if dome:
        cyl(x, y + 0.3, 1.1 + h, 1.7, 1.0, mat("stone", rough=0.7), verts=32, bevel=0.03)
        sphere(x, y + 0.3, 2.1 + h, 1.6, mat("#b9c6d3", rough=0.4, metal=0.3), sub=3, sz=0.85)
        cyl(x, y + 0.3, 3.4 + h, 0.12, 0.9, "steel", verts=8, bevel=0)
    else:
        pitched(x, y, 1.1 + h, w + 0.3, d + 0.2, 1.1, mat("stone", rough=0.7))

def car_at(x, y, rot, col):
    o = car(x, y, 0, rot, mat(col, rough=0.35, metal=0.3))
    for dx in (-1.3, 1.3):
        for dy in (-0.95, 0.95):
            c, s = math.cos(rot), math.sin(rot)
            cyl(x + dx * c - dy * s, y + dx * s + dy * c, 0.0, 0.38, 0.0001, "ink", verts=16, bevel=0)
    return o

# ---------- budget ----------
def b_property():
    tile(); lawn(0, 0.8, 9.4, 6.4); walk(0, -4.0, T, 1.4)
    bungalow(-1.2, 1.2, 5.0, 5.6, "brick")
    stack(3.2, -1.6, 6)

def b_sales():
    tile(); walk(0, -2.8, T, 3.6)
    box(-0.6, 1.6, 0, 7.6, 5.0, 4.2, mat("brick", rough=0.8), bevel=0.06)
    box(-0.6, 1.6, 4.2, 7.9, 5.2, 0.35, "stone", bevel=0.04)
    box(-0.6, -0.92, 0.3, 6.2, 0.1, 2.2, mat("#cfe7f5", rough=0.08, spec=0.6), bevel=0.02)
    box(-0.6, -1.6, 2.7, 7.0, 1.4, 0.16, mat("flag", rough=0.5), bevel=0.04)
    stack(3.4, -3.0, 4)

def b_biz():
    tile(); walk(0, -4.0, T, 1.4)
    block(-1.2, 1.0, 5.0, 5.0, 4, mat("navy", rough=0.6), fh=2.2)
    block(2.9, 1.6, 2.8, 3.6, 2, mat("grey", rough=0.7), fh=2.2)
    stack(3.4, -2.6, 3)

def b_buy():
    tile(); walk(0, 0, T, T)
    for x, col, h in ((-2.4, "star", 3.0), (0.2, "flag", 3.6), (2.6, "gold", 2.6)):
        box(x, 0.2, 0, 2.2, 1.4, h, mat(col, rough=0.6), bevel=0.08)
        for dx in (-0.5, 0.5): box(x + dx, 0.2, h, 0.14, 0.14, 0.8, mat(col, rough=0.6), bevel=0.02)
        box(x, 0.2, h + 0.8, 1.14, 0.14, 0.14, mat(col, rough=0.6), bevel=0.02)
    box(1.0, -3.0, 0, 3.0, 1.4, 0.08, "white", bevel=0.02, rot=0.3)    # a ticket
    box(1.0, -3.0, 0.08, 0.1, 1.2, 0.02, "star", bevel=0, rot=0.3)

def b_drive():
    tile(); box(0, -1.6, 0, T, 4.6, 0.05, mat("street", rough=0.9), bevel=0)
    car_at(-1.2, -1.6, 0.0, "#2f3a46")
    box(3.0, 2.2, 0, 1.6, 1.2, 3.2, mat("star", rough=0.5), bevel=0.1)       # gas pump
    box(3.0, 1.58, 1.8, 1.0, 0.06, 0.8, mat("#dfeaf2", rough=0.1), bevel=0.01)
    cyl(2.1, 2.2, 1.0, 0.07, 1.4, "ink", verts=6, bevel=0)
    box(3.0, 2.2, 0, 2.4, 2.0, 0.2, "stone", bevel=0.04)

def b_savings():
    tile(); walk(0, 0, T, T)
    for i, n in enumerate((8, 5, 3)): stack(-2.8 + i * 2.8, 0.4 - i * 0.6, n)

def b_safety():
    tile(); box(0, -0.6, 0, T, 5.2, 0.05, mat("street", rough=0.9), bevel=0)
    box(-1.0, -1.6, 0.3, 6.4, 2.4, 2.6, mat("star", rough=0.45), bevel=0.2)   # fire engine
    box(-3.4, -1.6, 0.3, 1.6, 2.4, 3.3, mat("star", rough=0.45), bevel=0.2)
    box(0.2, -1.6, 2.95, 4.6, 0.8, 0.18, "white", bevel=0.03)
    for dx in (-3.2, -0.8, 1.6): cyl(-1.0 + dx + 1.0, -2.82, 0.55, 0.55, 0.3, "ink", verts=16, bevel=0).rotation_euler = (math.pi / 2, 0, 0)
    car_at(2.4, 2.4, 0.0, "#f4f6f8")
    box(2.4, 2.4, 1.6, 0.9, 0.5, 0.25, mat("flag", rough=0.4, emit=1.0), bevel=0.05)

def b_services():
    tile(); box(0, -1.2, 0, T, 4.6, 0.05, mat("street", rough=0.9), bevel=0)
    box(-0.4, -1.2, 0.35, 6.0, 2.5, 3.0, mat("navy", rough=0.5), bevel=0.2)    # garbage truck
    box(-3.8, -1.2, 0.35, 1.8, 2.5, 2.4, mat("white", rough=0.5), bevel=0.2)
    for dx in (-3.6, -0.6, 1.8): cyl(dx, -2.48, 0.55, 0.55, 0.3, "ink", verts=16, bevel=0).rotation_euler = (math.pi / 2, 0, 0)
    for x, col in ((2.4, "#2a6fb0"), (3.6, "#2e2e2e")):
        box(x, 2.6, 0, 1.0, 1.0, 1.5, mat(col, rough=0.5), bevel=0.08)

def b_civic():
    tile(); walk(0, -4.0, T, 1.4); columns_building(0, 0.6)

def b_people():
    tile(); walk(0, 0, T, T); columns_building(0, 2.2, w=6.0, d=3.6, h=2.6)
    for i, (x, y) in enumerate([(-2.6, -2.2), (-1.2, -2.8), (0.2, -2.3), (1.6, -2.9), (3.0, -2.2), (-0.5, -3.8), (2.2, -3.9)]):
        person(x, y)

def b_state():
    tile(); walk(0, -4.0, T, 1.4); columns_building(0, 0.8, w=7.0, d=4.6, h=2.6, dome=True)

def b_spend():
    tile(); box(0, -1.4, 0, T, 4.6, 0.05, mat("street", rough=0.9), bevel=0)
    from learn import bus
    bus(-0.6, -1.4, 0.0, L=7.0)
    walk(0, 2.6, T, 3.4)
    tree(-3, 2.8, 0.1, 0.8); tree(1, 2.8, 0.1, 0.7)
    cyl(3.6, 2.4, 0.1, 0.1, 3.4, "steel", verts=8, bevel=0); box(3.0, 2.4, 3.4, 1.4, 0.3, 0.2, "steel", bevel=0.03)

# ---------- pensions ----------
def p_pay():
    tile(); walk(0, 0, T, T)
    cyl(0, 0, 0, 3.0, 0.4, mat("navy", rough=0.45), verts=40)
    for a in range(4):
        box(2.4 * math.cos(a * math.pi / 2 + .6), 2.4 * math.sin(a * math.pi / 2 + .6), 0.4, 0.18, 0.18, 5.4, "steel", bevel=0)
    cyl(0, 0, 0.4 + 5.4 * 0.9, 2.6, 0.24, mat("flag", rough=0.4), verts=40)
    for k in range(6): cyl(0, 0, 0.5 + k * 0.45, 2.0, 0.4, mat("gold", rough=0.3, metal=0.75), verts=36, bevel=0.04)

def p_extra():
    tile(); walk(0, 0, T, T)
    stack(-1.2, 0.6, 7); stack(1.6, -0.8, 3)
    box(1.6, -0.8, 2.6, 1.8, 0.5, 0.5, "green", bevel=0.08); box(1.6, -0.8, 2.25, 0.5, 0.5, 1.2, "green", bevel=0.08)

def p_bond():
    tile(); walk(0, 0, T, T)
    cyl(-0.6, -0.4, 0.9 - 3.2, 0.9, 6.4, mat("#f3ead6", rough=0.7), verts=24, bevel=0.05).rotation_euler = (0, math.pi / 2, 0.5)
    cyl(-0.6, -0.4, 0.9 - 0.3, 1.0, 0.6, mat("star", rough=0.5), verts=24, bevel=0.03).rotation_euler = (0, math.pi / 2, 0.5)
    stack(2.6, 2.6, 4)

def p_returns():
    tile(); walk(0, 0, T, T)
    for i, h in enumerate((1.4, 2.4, 2.0, 3.6, 4.8)):
        box(-3.2 + i * 1.6, 0.4, 0, 1.1, 1.6, h, mat("navy" if i < 4 else "flag", rough=0.55), bevel=0.06)

def p_cut():
    tile(); walk(0, -4.0, T, 1.4)
    columns_building(0, 0.8, w=6.4, d=4.4, h=3.0)
    box(-3.0, -3.6, 0, 1.0, 0.7, 0.9, "stone", bevel=0.04)

ICONS = {"b_property": b_property, "b_sales": b_sales, "b_biz": b_biz, "b_buy": b_buy, "b_drive": b_drive, "b_savings": b_savings,
         "b_safety": b_safety, "b_services": b_services, "b_civic": b_civic, "b_people": b_people, "b_state": b_state, "b_spend": b_spend,
         "p_pay": p_pay, "p_extra": p_extra, "p_bond": p_bond, "p_returns": p_returns, "p_cut": p_cut}

if __name__ == "__main__":
    name, outdir = sys.argv[1], sys.argv[2]; size = int(sys.argv[3]) if len(sys.argv) > 3 else 192
    os.makedirs(outdir, exist_ok=True)
    icons2.ICONS = ICONS
    for n in (ICONS if name == "all" else name.split(",")): icons2.render_icon(n, os.path.join(outdir, n + ".png"), size)
