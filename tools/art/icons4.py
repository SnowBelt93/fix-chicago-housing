"""Clay icons for the housing tool's zoning levels: one building type per tile, in the map's level colors.
    python3.11 tools/art/icons4.py <name|all|a,b> <outdir> [size]
Same tile and light as icons2.py. The camera is framed to each building so tall ones still read at small sizes."""
import sys, os, math, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy
from kit import *
from icons import tile, lawn, walk, pitched, T
import icons2

C = {"t1": "#a9dcf3", "t2": "#41b6e6", "t3": "#2b5da0", "t4": "#14335f", "t5": "#0f7c86", "t6": "#2a2e36"}

def lot(): tile(); lawn(0, 1.2, 9.4, 6.8); walk(0, -4.0, T, 1.4)

def punched(x, y, z, w, d, floors, fh, cols, glass="glass"):
    for f in range(floors):
        for c in range(cols):
            box(x - w / 2 + w * (c + 0.5) / cols, y - d / 2 - 0.04, z + f * fh + fh * 0.28, w / cols * 0.5, 0.06, fh * 0.5, glass, bevel=0.01)
    side = max(2, int(d / 1.6))
    for f in range(floors):
        for c in range(side):
            box(x + w / 2 + 0.04, y - d / 2 + d * (c + 0.5) / side, z + f * fh + fh * 0.28, 0.06, d / side * 0.5, fh * 0.5, glass, bevel=0.01)

def today():        # a bungalow: what most lots hold
    lot(); box(0, 0.6, 0, 5.2, 6.2, 2.6, mat("#d9cdb8", rough=0.8), bevel=0.06)
    pitched(0, 0.6, 2.6, 5.8, 6.6, 1.8, mat("roof", rough=0.8))
    box(-1.2, -2.54, 0.7, 1.2, 0.06, 1.1, "glass", bevel=0.01); box(1.2, -2.54, 0.7, 1.2, 0.06, 1.1, "glass", bevel=0.01)
    box(0, -3.0, 0, 1.6, 0.9, 0.5, "stone", bevel=0.03)

def threeflat():
    lot(); flat(0, 0.8, 0, 5.6, 6.6, 3, mat(C["t1"], rough=0.7), fh=2.0, cols=2, cornice="white")

def sixflat():
    lot(); box(0, 0.8, 0, 8.4, 6.8, 8.4, mat(C["t2"], rough=0.7), bevel=0.06)
    box(0, 0.8, 8.4, 8.7, 7.0, 0.4, "white", bevel=0.04)
    punched(0, 0.8, 0.3, 8.4, 6.8, 4, 2.0, 4)
    box(0, -2.7, 0, 1.8, 0.5, 2.0, mat("#e9eef2", rough=0.4), bevel=0.03)

def midrise():
    tile(); walk(0, -4.0, T, 1.4)
    box(0, 0.6, 0, 9.2, 7.4, 1.8, mat("#cfe7f5", rough=0.1, spec=0.6), bevel=0.05)          # shops at the base
    box(0, 0.6, 1.8, 9.2, 7.4, 6 * 1.6 - 1.8, mat(C["t3"], rough=0.65), bevel=0.06)
    box(0, 0.6, 9.6, 9.5, 7.6, 0.35, "white", bevel=0.04)
    punched(0, 0.6, 1.9, 9.2, 7.4, 5, 1.55, 5)

def highrise():
    tile(); walk(0, -4.0, T, 1.4)
    box(0, 0.6, 0, 8.6, 7.0, 2.4, mat(C["t3"], rough=0.65), bevel=0.06)                       # podium
    box(0, 1.0, 2.4, 6.4, 5.4, 12 * 1.25, mat(C["t4"], rough=0.6), bevel=0.06)
    box(0, 1.0, 2.4 + 15, 6.6, 5.6, 0.35, "white", bevel=0.04)
    punched(0, 1.0, 2.6, 6.4, 5.4, 11, 1.3, 4, glass="#9fc9e6")

def tower():
    tile(); walk(0, -4.0, T, 1.4)
    box(0, 0.6, 0, 9.0, 7.6, 3.0, mat(C["t3"], rough=0.65), bevel=0.06)
    box(0, 1.0, 3.0, 5.4, 5.0, 26, mat(C["t5"], rough=0.55), bevel=0.06)
    for f in range(0, 26, 2): box(0, 1.0 - 2.53, 3.4 + f, 5.0, 0.06, 1.2, "#bfe3ee", bevel=0.01)
    for f in range(0, 26, 2): box(2.73, 1.0, 3.4 + f, 0.06, 4.6, 1.2, "#bfe3ee", bevel=0.01)
    box(0, 1.0, 29, 3.6, 3.2, 1.4, mat(C["t5"], rough=0.55), bevel=0.05)

def supertall():
    tile(); walk(0, -4.0, T, 1.4)
    box(0, 0.6, 0, 9.2, 7.8, 3.2, mat(C["t3"], rough=0.65), bevel=0.06)
    box(0, 1.0, 3.2, 5.6, 5.2, 22, mat(C["t6"], rough=0.45, metal=0.2), bevel=0.06)
    box(0, 1.0, 25.2, 4.4, 4.0, 14, mat(C["t6"], rough=0.45, metal=0.2), bevel=0.06)          # setback
    box(0, 1.0, 39.2, 3.0, 2.6, 6, mat(C["t6"], rough=0.45, metal=0.2), bevel=0.05)
    cyl(0, 1.0, 45.2, 0.12, 4.0, "steel", verts=8, bevel=0)
    for z0, h, w, d in ((3.6, 21, 5.6, 5.2), (25.6, 13, 4.4, 4.0), (39.6, 5, 3.0, 2.6)):
        for f in range(0, int(h), 2):
            box(0, 1.0 - d / 2 - 0.03, z0 + f, w - 0.4, 0.06, 1.1, "#8fb3cc", bevel=0.01)
            box(w / 2 + 0.03, 1.0, z0 + f, 0.06, d - 0.4, 1.1, "#8fb3cc", bevel=0.01)

ICONS = {"z_today": today, "z_3flat": threeflat, "z_6flat": sixflat, "z_mid": midrise, "z_high": highrise, "z_tower": tower, "z_super": supertall}

if __name__ == "__main__":
    name, outdir = sys.argv[1], sys.argv[2]; size = int(sys.argv[3]) if len(sys.argv) > 3 else 192
    os.makedirs(outdir, exist_ok=True)
    icons2.ICONS = ICONS
    for n in (ICONS if name == "all" else name.split(",")): icons2.render_icon(n, os.path.join(outdir, n + ".png"), size)
