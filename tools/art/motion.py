"""Clay motion samples (frames rendered one by one, then joined into an animated WebP by the caller).
    python3.11 tools/art/motion.py <rise|train|star> <outdir> [frames]
rise: a mid-rise going up floor by floor on a city lot (a loading picture for the maps).
train: an L train crossing on the elevated structure (loops).
star: the red six-point star turning like a coin (half a turn loops)."""
import sys, os, math, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy
from clay import *

def lot_scene():
    slab(40, 26); f = -13
    box(0, f + 2.6, 0, 39.5, 4.6, 0.05, mat(ASPHALT, rough=0.9), bevel=0.02)
    box(0, f + 5.2, 0, 39.5, 0.3, 0.2, mat("curb", rough=0.8), bevel=0.04)
    box(0, f + 7.4, 0, 39.5, 3.6, 0.16, mat("curb", rough=0.85), bevel=0.03)
    box(0, f + 18.4, 0, 39.5, 14.6, 0.08, mat(GRASS, rough=0.95), bevel=0.04)
    bungalow(-12.5, f + 11, D=10); flats(12.5, f + 11, floors=3, D=11)
    for x in (-17, 17): tree(x, f + 6.2, 0.8)
    return f + 11

def rise(i, n):
    y0 = lot_scene()
    steps = n - 4                                   # floors climb, then it sits finished for a few frames
    if i < steps:
        fl = 1 + int(6 * i / steps); frame_up(0, y0, 12, 11, fl, done=max(0, fl - 2))
        crane(7.5, y0 + 9, 0, 23, 13, ang=math.radians(200 + 4 * i), m=mat("star", rough=0.45))
        hardhat(-4, y0 - 1.5); hardhat(3.5, y0 - 1.2, "#e07a3f")
    else:
        midrise(0, y0, W=12, floors=6, D=11, seed=4, balconies=False); star(0, y0 + 5.5, 19.6, 1.2)
    rig(52, target=(0, 0, 9), elev=26, azim=-62, sun=(46, -28), sun_e=3.3, world="#eef3f8", world_e=0.62)

def hardhat(x, y, vest="#f2c53d"):
    person(x, y, vest, 1.0); sphere(x, y, 0.14 + 1.8 * PS[0], 0.23 * PS[0], mat("#f4f5f6", rough=0.4), sub=2, sz=0.7)

def train(i, n):
    slab(60, 16); box(0, -4, 0, 59.5, 5, 0.05, mat(ASPHALT, rough=0.9), bevel=0.02)
    box(0, 4.5, 0, 59.5, 6.5, 0.08, mat(GRASS, rough=0.95), bevel=0.04)
    el_track([(-30, 1.5), (30, 1.5)], z=7.0)
    x = -46 + 62 * i / n                            # two cars cross the frame; the last frame meets the first
    ltrain(x, 1.5, 7.9, cars=2, stripe="#8a5a36")
    for k in range(4): tree(-24 + k * 16, 6.5, 0.8)
    for k, c in enumerate(("#5f7d8c", "navy", "gold")): car(-18 + k * 15 + (i * 1.2) % 4, -5, c)
    rig(58, target=(0, 0, 6), elev=22, azim=-74, sun=(46, -28), sun_e=3.3, world="#eef3f8", world_e=0.62)

def spin(i, n):
    o = star(0, 0, 0, 2.2, thick=0.7, upright=True); o.location[2] = 2.3
    o.rotation_euler[2] = math.pi * i / n          # a coin-like turn: the star is symmetric, so half a turn loops
    rig(7, target=(0, 0, 2.2), elev=8, azim=-90, sun=(40, -30), sun_e=3.0, world="#eef3f8", world_e=0.7)

if __name__ == "__main__":
    which, out = sys.argv[1], sys.argv[2]; n = int(sys.argv[3]) if len(sys.argv) > 3 else 16
    os.makedirs(out, exist_ok=True)
    W, H = {"rise": (480, 360), "train": (560, 260), "star": (220, 220)}[which]
    for i in range(n):
        reset(); random.seed(1)
        {"rise": rise, "train": train, "star": spin}[which](i, n)
        shadow_catcher(z=-1.25 if which != "star" else -0.01)
        render(os.path.abspath(os.path.join(out, f"{which}_{i:02d}.png")), W, H, samples=18)
