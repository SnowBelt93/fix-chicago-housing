"""Clay models of real Chicago buildings, one per zoning level in Fix Chicago Housing.
    python3.11 tools/art/icons4.py <name|all|a,b> <outdir> [size]
Each is modeled on a real building (simplified, no signs or logos):
  z_today  Chicago bungalow: Michael Faheny House, 3124 N. Kilbourn Ave. (brick, hipped roof, front dormer)
  z_3flat  Greystone three-flat on 24th Street in Chinatown (limestone front, full-height bay, stepped parapet)
  z_6flat  Lakeview six-flat (buff brick, two corner bays, arched stone entry with a balcony)
  z_mid    Emmett Street Apartments, 2614 N. Emmett St., Logan Square (gray panels, colored window accents)
  z_high   1611 W. Division, Wicker Park (11 stories, striped glass curtain wall, concrete core)
  z_tower  860-880 N. Lake Shore Drive (Mies van der Rohe, 26 stories, black steel mullions, open lobby)
  z_super  Marina City (65 stories, round tower with scalloped balconies, parking floors below)
The tile's edge carries the level's map color, so the pictures still match the map key."""
import sys, os, math, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy, bmesh
from kit import *
from icons import lawn, walk, pitched, T
import icons2

LEVEL = {"z_today": "#cfd4da", "z_3flat": "#a9dcf3", "z_6flat": "#41b6e6", "z_mid": "#2b5da0", "z_high": "#14335f", "z_tower": "#0f7c86", "z_super": "#2a2e36"}
CUR = {"k": "z_today"}

def tile(top="ground"):
    box(0, 0, -1.1, T, T, 0.8, mat(LEVEL[CUR["k"]], rough=0.8), bevel=0.35)       # the level's color on the tile's edge
    box(0, 0, -0.35, T, T, 0.35, mat(top, rough=0.9), bevel=0.25)

def hip(x, y, z, w, d, h, m):
    """Hipped roof over a w x d rectangle, ridge running along y."""
    me = bpy.data.meshes.new("hip"); bm = bmesh.new()
    r = max(0.0, (d - w) / 2)
    v = [bm.verts.new(p) for p in [(x - w / 2, y - d / 2, z), (x + w / 2, y - d / 2, z), (x + w / 2, y + d / 2, z), (x - w / 2, y + d / 2, z),
                                    (x, y - r, z + h), (x, y + r, z + h)]]
    for f in ((0, 1, 4), (1, 2, 5, 4), (2, 3, 5), (3, 0, 4, 5), (0, 3, 2, 1)): bm.faces.new([v[i] for i in f])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new("hip", me); bpy.context.scene.collection.objects.link(o); o.data.materials.append(m)
    return o

def pane(x, y, z, w, h, face="-y", glass="glassdk", frame="white", fw=0.08):
    """A window with a light frame on the -y or +x face (x, y = the face's surface point)."""
    if face == "-y":
        box(x, y - 0.03, z - fw, w + 2 * fw, 0.06, h + 2 * fw, frame, bevel=0.01); box(x, y - 0.07, z, w, 0.04, h, glass, bevel=0.005)
    else:
        box(x + 0.03, y, z - fw, 0.06, w + 2 * fw, h + 2 * fw, frame, bevel=0.01); box(x + 0.07, y, z, 0.04, w, h, glass, bevel=0.005)

def bay(x, y0, z, w, h, depth, m):
    """A three-sided angled bay projecting toward -y from the wall at y0: one solid trapezoid prism."""
    a = w * 0.55 / 2
    me = bpy.data.meshes.new("bay"); bm = bmesh.new()
    pts = [(x - w / 2, y0 + 0.05), (x - a, y0 - depth), (x + a, y0 - depth), (x + w / 2, y0 + 0.05)]
    vb = [bm.verts.new((px, py, z)) for px, py in pts]; vt = [bm.verts.new((px, py, z + h)) for px, py in pts]
    bm.faces.new(list(reversed(vb))); bm.faces.new(vt)
    for i in range(4):
        j = (i + 1) % 4; bm.faces.new((vb[i], vb[j], vt[j], vt[i]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new("bay", me); bpy.context.scene.collection.objects.link(o); o.data.materials.append(m)
    mod = o.modifiers.new("bev", "BEVEL"); mod.width = 0.03; mod.segments = 2; mod.limit_method = "ANGLE"
    return o

def bay_side_windows(x, y0, z, w, depth, hgt, floors, fh):
    """Narrow windows on the bay's two angled sides."""
    a = w * 0.55 / 2
    for sgn in (-1, 1):
        cx, cy = x + sgn * (a + w / 2) / 2, y0 - depth / 2
        ang = math.atan2(depth, (w / 2 - a)) * sgn
        for f in range(floors):
            box(cx + sgn * 0.0, cy - 0.06, z + f * fh, 0.45, 0.05, hgt, "glassdk", bevel=0.005, rot=ang)

# ---------- the seven buildings ----------
def today():   # Chicago bungalow, 3124 N. Kilbourn Ave.
    tile(); lawn(0, -2.0, 9.4, 3.6); walk(0, -4.3, T, 1.0); walk(2.3, -2.6, 1.2, 2.6)
    brick = mat("#a65a42", rough=0.85); stone = mat("#e8e2d6", rough=0.7)
    box(0, 1.2, 0, 6.6, 8.6, 0.9, stone, bevel=0.04)                        # raised basement
    box(0, 1.2, 0.9, 6.6, 8.6, 2.9, brick, bevel=0.05)
    box(0, 1.2 - 4.32, 1.5, 6.62, 0.06, 0.14, stone, bevel=0.01)             # stone sill band
    hip(0, 1.2, 3.8, 7.4, 9.4, 2.0, mat("#6f6b66", rough=0.9))
    box(-0.2, -2.4, 3.6, 2.6, 2.0, 1.6, mat("#eef0f1", rough=0.6), bevel=0.05) # front dormer
    pitched(-0.2, -2.4, 5.2, 3.0, 2.3, 0.9, mat("#6f6b66", rough=0.9))
    for dx in (-0.7, 0.3): pane(-0.2 + dx, -3.41, 4.0, 0.7, 0.9)
    for dx in (-2.3, -1.4, -0.5): pane(dx, -3.11, 1.6, 0.75, 1.4)            # the three front windows
    box(1.9, -3.12, 0.9, 1.5, 0.1, 2.3, stone, bevel=0.02)                   # door surround
    box(1.9, -3.2, 0.95, 1.0, 0.06, 1.9, mat("#2a2e36", rough=0.5), bevel=0.01)
    for k in range(4): box(1.9, -3.5 - k * 0.32, 0.9 - (k + 1) * 0.22, 1.5, 0.34, 0.22, stone, bevel=0.01)   # steps
    for sx in (1.0, 2.8): box(sx, -3.9, 0, 0.3, 1.4, 1.0, brick, bevel=0.03)
    box(2.4, 3.6, 3.6, 0.6, 0.6, 2.4, brick, bevel=0.03)                     # chimney
    shrub(-1.4, -3.6); shrub(-2.6, -3.5)

def shrub(x, y, s=1.0): sphere(x, y, 0.45 * s, 0.6 * s, mat("#6b9159", rough=0.9), sub=2, sz=0.75)

def threeflat():   # greystone three-flat, 24th Street, Chinatown
    tile(); walk(0, -3.9, T, 2.0); lawn(0, -2.3, 9.4, 1.2)
    stone = mat("#d8d0bd", rough=0.8); trim = mat("#efe9dc", rough=0.7)
    W, D, H = 6.0, 8.0, 3 * 2.6
    box(0, 1.2, 0, W, D, 1.0, mat("#c9c0aa", rough=0.85), bevel=0.04)
    box(0, 1.2, 1.0, W, D, H, stone, bevel=0.04)
    bay(-1.3, 1.2 - D / 2, 1.0, 3.0, H + 0.4, 0.9, stone)                     # full-height angled bay on the left
    bay_side_windows(-1.3, 1.2 - D / 2, 1.6, 3.0, 0.9, 1.5, 3, 2.6)
    for f in range(3):
        z = 1.0 + f * 2.6 + 0.6
        pane(-1.3, 1.2 - D / 2 - 0.91, z, 0.75, 1.5); pane(1.6, 1.2 - D / 2 - 0.01, z, 0.75, 1.5)
        box(0, 1.2 - D / 2 - 0.05, z - 0.2, W, 0.12, 0.1, trim, bevel=0)     # stone sill course
        for c in range(3): pane(W / 2 + 0.01, 1.2 - D / 2 + 1.5 + c * 2.2, z, 0.9, 1.5, face="+x")
    box(0, 1.2, 1.0 + H, W + 0.3, D + 0.2, 0.5, trim, bevel=0.05)           # cornice
    box(-0.2, 1.2 - D / 2 + 0.2, 1.5 + H, 2.2, 0.4, 0.7, trim, bevel=0.04)  # stepped center of the parapet
    box(-0.2, 1.2 - D / 2 + 0.2, 2.2 + H, 1.0, 0.4, 0.35, trim, bevel=0.04)
    box(1.6, 1.2 - D / 2 - 0.06, 1.0, 1.3, 0.12, 2.4, trim, bevel=0.02); box(1.6, 1.2 - D / 2 - 0.12, 1.05, 0.9, 0.06, 2.0, mat("#5b3a26", rough=0.6), bevel=0.01)
    for k in range(4): box(1.6, 1.2 - D / 2 - 0.4 - k * 0.32, 1.0 - (k + 1) * 0.25, 1.4, 0.34, 0.25, trim, bevel=0.01)
    for k in range(9): box(-2.8 + k * 0.3, -2.95, 0, 0.05, 0.05, 0.9, "ink", bevel=0)   # iron fence
    box(-1.6, -2.95, 0.85, 2.5, 0.05, 0.05, "ink", bevel=0)

def sixflat():   # Lakeview six-flat
    tile(); walk(0, -4.0, T, 1.8); lawn(0, -2.5, 9.4, 1.2); walk(0, -2.5, 1.4, 1.2)
    brick = mat("#d4a55c", rough=0.85); stone = mat("#ece4d2", rough=0.7)
    W, D, FH = 9.0, 7.6, 2.4
    box(0, 1.4, 0, W, D, 0.9, stone, bevel=0.04)
    box(0, 1.4, 0.9, W, D, 3 * FH, brick, bevel=0.04)
    for sx in (-3.0, 3.0): bay(sx, 1.4 - D / 2, 0.9, 2.8, 3 * FH, 0.8, brick); bay_side_windows(sx, 1.4 - D / 2, 1.4, 2.8, 0.8, 1.3, 3, FH)
    for f in range(3):
        z = 0.9 + f * FH + 0.5
        for sx in (-3.0, 3.0): pane(sx, 1.4 - D / 2 - 0.81, z, 0.7, 1.3)
        for sx in (-1.1, 1.1): pane(sx, 1.4 - D / 2 - 0.01, z, 0.6, 1.3)
        box(0, 1.4 - D / 2 - 0.04, z - 0.25, W, 0.1, 0.12, stone, bevel=0)    # limestone belt courses
        for c in range(3): pane(W / 2 + 0.01, 1.4 - D / 2 + 1.4 + c * 2.2, z, 0.8, 1.3, face="+x")
    box(0, 1.4 - D / 2 - 0.1, 0.9, 1.8, 0.2, 2.5, stone, bevel=0.03)         # stone entry with an arch
    cyl(0, 1.4 - D / 2 - 0.12, 2.5, 0.55, 0.04, mat("#2a2e36", rough=0.5), verts=24, bevel=0).rotation_euler = (math.pi / 2, 0, 0)
    box(0, 1.4 - D / 2 - 0.14, 0.95, 1.0, 0.06, 1.7, mat("#2a2e36", rough=0.5), bevel=0.01)
    box(0, 1.4 - D / 2 - 0.4, 3.35, 2.0, 0.7, 0.18, stone, bevel=0.03)        # balcony over the door
    for k in range(7): box(-0.9 + k * 0.3, 1.4 - D / 2 - 0.72, 3.53, 0.08, 0.08, 0.45, stone, bevel=0)
    box(0, 1.4, 0.9 + 3 * FH, W + 0.4, D + 0.3, 0.45, stone, bevel=0.05)      # cornice
    for k in range(3): box(0, 1.4 - D / 2 - 0.9 - k * 0.3, 0.9 - (k + 1) * 0.3, 1.8, 0.32, 0.3, stone, bevel=0.01)

def midrise():   # Emmett Street Apartments, Logan Square
    tile(); walk(0, -3.4, T, 3.2)
    panel = mat("#d7dadd", rough=0.6); base = mat("#4a4f57", rough=0.6)
    W, D, FH = 9.6, 6.0, 1.15
    box(0, 1.6, 0, W, D, 1.4, base, bevel=0.04)
    box(-1.4, 1.6, 1.4, W - 2.8, D, 6 * FH, panel, bevel=0.04)                 # main block, six floors over the base
    box(3.4, 1.9, 1.4, 2.8, D - 0.6, 5 * FH, mat("#c4c8cc", rough=0.6), bevel=0.04)   # lower wing steps down
    accents = ["#2f86c9", "#f0a43a", "#f2c53d", "#41b6e6"]
    random.seed(5)
    for f in range(6):
        z = 1.4 + f * FH + 0.25
        for c in range(6):
            x = -4.6 + c * 1.15
            pane(x, 1.6 - D / 2, z, 0.5, 0.7, frame="#2a2e36", fw=0.04)
            if random.random() < 0.45: box(x + 0.42, 1.6 - D / 2 - 0.04, z, 0.28, 0.06, 0.7, mat(random.choice(accents), rough=0.5), bevel=0.01)
        for c in range(4): pane(-1.4 + (W - 2.8) / 2 + 0.01, 1.6 - D / 2 + 0.8 + c * 1.4, z, 0.5, 0.7, face="+x", frame="#2a2e36", fw=0.04)
    for f in range(5):
        for c in range(2): pane(3.0 + c * 1.1, 1.9 - (D - 0.6) / 2, 1.4 + f * FH + 0.25, 0.5, 0.7, frame="#2a2e36", fw=0.04)
    box(0, 1.6 - D / 2 - 0.03, 0.2, W - 0.6, 0.06, 1.0, mat("#9fc7e2", rough=0.1, spec=0.6), bevel=0.01)   # glass at street level

def highrise():   # 1611 W. Division, Wicker Park
    tile(); walk(0, -3.6, T, 2.8)
    S, FH, N = 6.4, 1.0, 11
    box(0, 1.0, 0, S, S, N * FH, mat("#3a3f47", rough=0.5), bevel=0.05)
    random.seed(11)
    for face in ("-y", "+x"):
        for f in range(N):
            x = -S / 2 + 0.1
            while x < S / 2 - 0.2:
                w = random.choice([0.25, 0.35, 0.5, 0.7])
                w = min(w, S / 2 - 0.1 - x)
                g = random.random() < 0.62
                col = mat("#8fb6d4", rough=0.08, spec=0.7) if g else mat("#2e3238", rough=0.5)
                if face == "-y": box(x + w / 2, 1.0 - S / 2 - 0.03, f * FH + 0.05, w - 0.03, 0.05, FH - 0.08, col, bevel=0)
                else: box(S / 2 + 0.03, 1.0 - S / 2 + x + S / 2 + w / 2, f * FH + 0.05, 0.05, w - 0.03, FH - 0.08, col, bevel=0)
                x += w
    box(-S / 2 - 0.9, 2.2, 0, 1.8, 3.0, N * FH + 1.0, mat("#b9bcbf", rough=0.8), bevel=0.04)   # the gray concrete core
    box(0, 1.0, N * FH, S - 0.4, S - 0.4, 0.4, mat("#2e3238", rough=0.5), bevel=0.03)

def tower():   # 860-880 N. Lake Shore Drive
    tile(); walk(0, -3.8, T, 2.4)
    W, D, FH, N = 4.6, 3.0, 0.62, 26
    steel = mat("#1f2227", rough=0.45, metal=0.3); glass = mat("#5b6f82", rough=0.1, spec=0.7)
    for c in range(-2, 3):                                                   # open ground floor on columns
        for sy in (-D / 2, D / 2): box(c * W / 4, 1.0 + sy, 0, 0.18, 0.18, 1.3, steel, bevel=0.01)
    box(0, 1.0, 0, W - 1.0, D - 0.8, 1.3, glass, bevel=0.02)                 # glass lobby, set back
    box(0, 1.0, 1.3, W, D, N * FH, glass, bevel=0.02)
    for k in range(17): box(-W / 2 + k * W / 16, 1.0 - D / 2 - 0.06, 1.3, 0.05, 0.12, N * FH, steel, bevel=0)   # I-beam mullions
    for k in range(11): box(W / 2 + 0.06, 1.0 - D / 2 + k * D / 10, 1.3, 0.12, 0.05, N * FH, steel, bevel=0)
    for f in range(0, N + 1, 1): box(0, 1.0 - D / 2 - 0.02, 1.3 + f * FH - 0.04, W + 0.02, 0.06, 0.08, steel, bevel=0)
    for sx in (-W / 2, W / 2): box(sx, 1.0 - D / 2, 1.3, 0.2, 0.2, N * FH, steel, bevel=0.01)
    box(0, 1.0, 1.3 + N * FH, W + 0.1, D + 0.1, 0.35, steel, bevel=0.02)

def supertall():   # Marina City
    tile(); walk(0, 0, T, T)
    conc = mat("#e6e3dc", rough=0.8)
    R, FH = 2.0, 0.62
    cyl(0, 0.6, 0, R * 1.3, 0.6, conc, verts=40, bevel=0.03)                     # base
    cyl(0, 0.6, 0.6, R * 0.95, 13 * FH, mat("#4a4f56", rough=0.8), verts=40, bevel=0)   # parking floors: open ramps
    for f in range(13):
        cyl(0, 0.6, 0.6 + f * FH, R * 1.08, 0.1, conc, verts=40, bevel=0)
        for k in range(0, 16, 3):
            a = k / 16 * 2 * math.pi + f * 0.2
            box(math.cos(a) * R * 1.0, 0.6 + math.sin(a) * R * 1.0, 0.6 + f * FH + 0.07, 0.42, 0.18, 0.12, mat(random.choice(["#c0392b", "#2f6da3", "#e8e2d6", "#3a3f47"]), rough=0.5), bevel=0.03, rot=a + math.pi / 2)
    z0 = 0.6 + 13 * FH
    cyl(0, 0.6, z0, R * 1.18, 0.25, conc, verts=40, bevel=0.02)
    for f in range(28):
        z = z0 + 0.25 + f * FH
        cyl(0, 0.6, z, R * 0.86, FH, mat("#2c3540", rough=0.1, spec=0.6), verts=32, bevel=0)
        for k in range(16):                                                  # scalloped balconies: the "corncob"
            a = k / 16 * 2 * math.pi
            cyl(math.cos(a) * R * 0.88, 0.6 + math.sin(a) * R * 0.88, z, 0.42, 0.1, conc, verts=12, bevel=0.02)
        cyl(0, 0.6, z, R * 0.88, 0.1, conc, verts=40, bevel=0)
    cyl(0, 0.6, z0 + 0.25 + 28 * FH, R * 1.1, 0.3, conc, verts=40, bevel=0.03)

ICONS = {"z_today": today, "z_3flat": threeflat, "z_6flat": sixflat, "z_mid": midrise, "z_high": highrise, "z_tower": tower, "z_super": supertall}

if __name__ == "__main__":
    name, outdir = sys.argv[1], sys.argv[2]; size = int(sys.argv[3]) if len(sys.argv) > 3 else 240
    os.makedirs(outdir, exist_ok=True)
    def wrap(k):
        def f(): CUR["k"] = k; ICONS[k]()
        return f
    icons2.ICONS = {k: wrap(k) for k in ICONS}
    for n in (ICONS if name == "all" else name.split(",")): icons2.render_icon(n, os.path.join(outdir, n + ".png"), size)
