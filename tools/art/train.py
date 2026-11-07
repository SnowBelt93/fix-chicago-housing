"""The Easter egg train car for the transit map: one L car (stainless body, window band, two doors a side, a cab with a
lit brown route sign, rooftop units, two trucks), exported as a small glTF for three.js, plus a preview render.
    python3.11 tools/art/train.py transit/data/lcar.glb [preview.png]
Z is up, x runs along the car (cab end at +x), 1 unit = 1 m. A generic car, no agency logos or lettering."""
import sys, os, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy
from kit import *

L, W = 14.6, 2.84
Z0, Z1 = 1.05, 3.55        # body bottom and roof edge, above the rail

def car():
    steel = mat("#c3c9d0", rough=0.32, metal=0.55, spec=0.5)
    dark = mat("#2a3038", rough=0.5)
    glass = mat("#1c2733", rough=0.08, metal=0.1, spec=0.7)
    body = box(0, 0, Z0, L, W, Z1 - Z0, steel, bevel=0.12, name="body")
    roof = box(0, 0, Z1 - 0.15, L - 0.3, W - 0.25, 0.38, steel, bevel=0.17, name="roof")
    for x in (-3.6, 3.6): box(x, 0, Z1 + 0.15, 2.4, 1.7, 0.42, mat("#8d959e", rough=0.5, metal=0.3), bevel=0.06, name="hvac")
    box(0, 0, Z0 - 0.02, L - 0.6, W - 0.5, 0.3, dark, bevel=0.03, name="skirt")
    # window band on both sides, broken by the doors
    doors = (-3.4, 3.4)
    segs = [(-L / 2 + 0.9, doors[0] - 0.85), (doors[0] + 0.85, doors[1] - 0.85), (doors[1] + 0.85, L / 2 - 2.0)]
    for s in (-1, 1):
        y = s * (W / 2 + 0.012)
        for a, b in segs:
            box((a + b) / 2, y, 2.05, b - a, 0.03, 0.95, glass, bevel=0, name="win")
        for dx in doors:
            box(dx, y, Z0 + 0.12, 1.45, 0.035, 2.2, mat("#aab1b9", rough=0.3, metal=0.5), bevel=0, name="door")
            for k in (-0.36, 0.36): box(dx + k, s * (W / 2 + 0.03), 2.0, 0.55, 0.03, 0.95, glass, bevel=0, name="doorwin")
            box(dx, s * (W / 2 + 0.04), Z0 + 0.12, 0.03, 0.03, 2.2, dark, bevel=0, name="doorgap")
        box(L / 2 - 1.25, y, 2.05, 1.0, 0.03, 0.95, glass, bevel=0, name="cabwin")
    # cab end (+x): a big windshield, the lit brown route sign above it, two headlights
    xe = L / 2 + 0.012
    box(xe, 0, 1.95, 0.03, W - 0.55, 1.15, glass, bevel=0.01, name="windshield")
    box(xe + 0.01, 0, 3.12, 0.03, 1.5, 0.3, mat("#8a5a36", rough=0.4, emit=1.6), bevel=0.01, name="sign")
    for y in (-0.95, 0.95): box(xe + 0.01, y, 1.35, 0.03, 0.3, 0.16, mat("#fff6dc", rough=0.2, emit=4.0), bevel=0.01, name="lamp")
    box(xe + 0.15, 0, 1.0, 0.3, 0.5, 0.25, dark, bevel=0.03, name="coupler")
    # back end (-x): the door to the next car
    box(-L / 2 - 0.012, 0, Z0 + 0.15, 0.03, 0.85, 2.1, mat("#aab1b9", rough=0.3, metal=0.5), bevel=0.01, name="enddoor")
    box(-L / 2 - 0.02, 0, 2.05, 0.03, 0.55, 0.8, glass, bevel=0.01, name="enddoorwin")
    # trucks with wheels
    for x in (-L / 2 + 2.6, L / 2 - 2.6):
        box(x, 0, 0.35, 2.6, W - 0.7, 0.55, dark, bevel=0.05, name="truck")
        for wx in (-0.85, 0.85):
            for s in (-1, 1):
                o = cyl(x + wx, s * (W / 2 - 0.42), 0, 0.42, 0.14, mat("#4a5059", rough=0.4, metal=0.6), verts=12, bevel=0)
                o.rotation_euler = (math.radians(90), 0, 0); o.location.z = 0.42; o.location.y = s * (W / 2 - 0.42)

def export(path):
    for o in bpy.context.scene.objects:
        for m in o.modifiers:
            if m.type == "BEVEL": m.segments = 1

    for o in bpy.context.scene.objects: o.select_set(o.type == "MESH")
    bpy.ops.export_scene.gltf(filepath=path, export_format="GLB", use_selection=True, export_yup=False,
                              export_apply=True, export_lights=False, export_cameras=False)

if __name__ == "__main__":
    out = sys.argv[1]
    reset(); car()
    export(os.path.abspath(out))
    if len(sys.argv) > 2:
        # preview: a two-car pair on a bit of elevated deck
        rig(19, target=(0, 0, 1.6), elev=24, azim=-38, sun=(45, -60), sun_e=3.2, world="#eef3f8", world_e=0.8)
        box(0, 0, -0.5, 30, 5.2, 0.5, "steel", bevel=0.05)
        shadow_catcher(z=-0.5)
        render(os.path.abspath(sys.argv[2]), 1200, 700, samples=48)
