#!/usr/bin/env python3
"""Building footprints for the "Get the megaprojects built" policy, so the map can show the projects filled in.

Each megaproject's site is its planned-development (PD) area on Chicago's zoning map (tools/raw/zoning.geojson.gz,
Chicago Data Portal dj47-wfun), trimmed as noted in SITES. Inside it, the script lays out building footprints square to
the local street grid, around the buildings that stand there today (from b/<area>.wasm minus the "gone" bit in
b/extra.wasm), off street rights-of-way (b/streets.wasm) and out of parks (POS zoning). The game sets each footprint's
height at run time so the floor area holds the homes it counts (1,026 sq ft per home), so this file holds no home counts.
The layout is illustrative: the real site plans differ.

Output: meta.json "megaSites": {name: {"lon", "lat" (origin), "fp": [[x1, y1, ..., x4, y4], ...] in metres east/north of
the origin (deck.gl scale, 111,319.49 m per degree), nearest the site's middle first, "land": {area: [indices]}}}.
"land" lists empty lots (gone buildings with open lots) and vacant parcels (index N + j, as in b/land.wasm) inside the
site, plus any buildings the project replaces; the game takes them out of the zoning model while the policy is on, so
the same land isn't counted twice. Run after tools/prep_extra.py:  python3 tools/prep_mega.py
"""
import gzip, json, math, os, struct
import numpy as np, shapely
from shapely.geometry import shape, box, Polygon, LineString
from shapely.ops import unary_union
from shapely.prepared import prep
from shapely import affinity

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DECK = 111319.49
HALF = {1: 20, 2: 13, 3: 11, 4: 10}     # street half-widths in metres, as STREET_HALF in index.html
GAP = 18                                # metres between new buildings (about a street)
SIZES = [(44, 24), (28, 28), (20, 20)]   # footprints (metres): mid-rise slabs first, then tower-sized squares, then small ones in the gaps
MAX_FP = 90

# name, origin (the map pin), PD numbers, optional (x0, y0, x1, y1) box to keep (metres from the pin), optional boxes to leave
# empty, whether the project replaces the low buildings inside its "replace" box
SITES = [
    dict(n="The 78", lon=-87.6322, lat=41.8647, pd=[1434],
         keepout=[(-230, 70, -20, 300)]),          # the Fire stadium, along the river just south of Roosevelt Road (Wikipedia)
    dict(n="Foundry Park", lon=-87.660, lat=41.917, pd=[1439]),
    dict(n="1901 Project", lon=-87.6742, lat=41.8807, pd=[522]),
    dict(n="Bronzeville Lakefront", lon=-87.613, lat=41.843, pd=[1509]),
    dict(n="North Union", lon=-87.6345, lat=41.8995, pd=[1503],
         keep=(-115, -165, 8, 145),                 # JDL's 8.1 acres: Brown Line tracks to Wells, Chestnut to Oak (City of Chicago)
         replace=(-115, -165, 8, 145)),             # its one- to three-story commercial buildings
    dict(n="Cabrini-Green (CHA)", lon=-87.641, lat=41.902, pd=[1006, 1556], ords=["21079"],
         replace=(-140, -615, 100, -190)),          # the vacant rowhouses near Chicago Ave and Larrabee (CHA plan: 10 kept)
]

def load_meta():
    return json.load(open(os.path.join(ROOT, 'meta.json')))

def read_extra():
    ex = open(os.path.join(ROOT, 'b', 'extra.wasm'), 'rb').read()
    na = struct.unpack_from('<I', ex, 0)[0]; o = 4; out = {}
    for _ in range(na):
        num, N = struct.unpack_from('<II', ex, o); o += 8; out[num] = np.frombuffer(ex, np.uint8, N, o); o += N
    return out

def read_land():
    b = open(os.path.join(ROOT, 'b', 'land.wasm'), 'rb').read()
    na = struct.unpack_from('<I', b, 0)[0]; o = 4; out = {}
    for _ in range(na):
        num, N = struct.unpack_from('<II', b, o); o += 8
        op = np.frombuffer(b, np.uint8, N, o); o += N; o += (4 - o % 4) % 4
        k = struct.unpack_from('<I', b, o)[0]; o += 4
        xy = np.frombuffer(b, '<i2', 3 * k, o).reshape(-1, 3)[:, :2].astype(float) * 0.5 if k else np.zeros((0, 2))
        o += 6 * k; o += (4 - o % 4) % 4
        out[num] = (op, xy)
    return out

def read_area(num):
    b = open(os.path.join(ROOT, 'b', f'{num}.wasm'), 'rb').read()
    N, V = struct.unpack_from('<II', b, 0); lon0, lat0 = struct.unpack_from('<dd', b, 8)
    q = np.frombuffer(b, '<i2', 2 * V, 24).reshape(-1, 2).astype(float) * 0.5
    o = 24 + 4 * V
    nv = np.frombuffer(b, np.uint8, N, o); st = np.frombuffer(b, np.uint8, N, o + N); fl = np.frombuffer(b, np.uint8, N, o + 2 * N)
    po = o + 3 * N + ((3 * N) % 2)
    un = np.frombuffer(b, '<u2', N, po)
    starts = np.concatenate([[0], np.cumsum(nv.astype(np.int64))])
    return dict(N=N, lon0=lon0, lat0=lat0, q=q, starts=starts, st=st, fl=fl, un=un)

def read_streets():
    b = open(os.path.join(ROOT, 'b', 'streets.wasm'), 'rb').read()
    nP, nV = struct.unpack_from('<II', b, 0); lon0, lat0 = struct.unpack_from('<dd', b, 8)
    o = 24; cls = np.frombuffer(b, np.uint8, nP, o); o += nP; o += (4 - o % 4) % 4
    st = np.frombuffer(b, '<u4', nP + 1, o); o += 4 * (nP + 1)
    xy = np.frombuffer(b, '<i2', 2 * nV, o).reshape(-1, 2).astype(float) * 2
    kx = DECK * math.cos(math.radians(lat0))
    return cls, st, lon0 + xy[:, 0] / kx, lat0 + xy[:, 1] / DECK

def grid_angle(segs):
    """Most common street direction near the site (radians, in [-45°, 45°)): length-weighted 1° histogram, smoothed ±2°."""
    h = np.zeros(90)
    for (x1, y1, x2, y2) in segs:
        L = math.hypot(x2 - x1, y2 - y1)
        if L < 1: continue
        h[int(math.degrees(math.atan2(y2 - y1, x2 - x1)) % 90) % 90] += L
    sm = sum(np.roll(h, k) for k in range(-2, 3))
    d = int(np.argmax(sm))
    return math.radians(d if d < 45 else d - 90)

def main():
    meta = load_meta(); EX = read_extra(); LAND = read_land()
    gj = json.load(gzip.open(os.path.join(ROOT, 'tools', 'raw', 'zoning.geojson.gz'), 'rt'))
    zones = []
    for f in gj['features']:
        if not f.get('geometry'): continue
        p = {k.lower(): v for k, v in (f.get('properties') or {}).items()}
        try: g = shape(f['geometry'])
        except Exception: continue
        if not g.is_valid: g = g.buffer(0)
        zones.append((g, p.get('zone_class') or '', str(p.get('pd_num') or '0'), str(p.get('ordinance') or '')))
    scls, sst, slon, slat = read_streets()
    out = {}
    for S in SITES:
        lon, lat = S['lon'], S['lat']; kx = DECK * math.cos(math.radians(lat))
        to_m = lambda g: affinity.affine_transform(g, [kx, 0, 0, DECK, -lon * kx, -lat * DECK])
        parts = [g for g, z, pd, o in zones if (pd in map(str, S['pd']) and z.startswith('PD')) or o in S.get('ords', [])]
        site = to_m(unary_union(parts))
        if S.get('keep'): site = site.intersection(box(*S['keep']))
        for k in S.get('keepout', []): site = site.difference(box(*k))
        parks = [to_m(g) for g, z, pd, o in zones if z.startswith('POS')]
        parks = [g for g in parks if g.intersects(site.buffer(50))]
        if parks: site = site.difference(unary_union(parks))
        replace = box(*S['replace']) if S.get('replace') else None
        region = site.union(replace) if replace is not None else site
        x0, y0, x1, y1 = region.bounds
        # streets: rights-of-way to stay off, and the grid direction
        roads, segs = [], []
        for p in range(len(scls)):
            a, b_ = sst[p], sst[p + 1]
            X = (slon[a:b_] - lon) * kx; Y = (slat[a:b_] - lat) * DECK
            if len(X) < 2: continue
            if X.max() < x0 - 600 or X.min() > x1 + 600 or Y.max() < y0 - 600 or Y.min() > y1 + 600: continue
            for i in range(len(X) - 1):
                if x0 - 150 < (X[i] + X[i + 1]) / 2 < x1 + 150 and y0 - 150 < (Y[i] + Y[i + 1]) / 2 < y1 + 150: segs.append((X[i], Y[i], X[i + 1], Y[i + 1]))
            if X.max() < x0 - 40 or X.min() > x1 + 40 or Y.max() < y0 - 40 or Y.min() > y1 + 40: continue
            roads.append(LineString(np.c_[X, Y]).buffer(HALF[int(scls[p])] - 2, cap_style=2))
        ang = grid_angle(segs)
        # buildings standing there today (or replaced), and empty land inside the site
        obst, land = [], {}
        for a in meta['areas']:
            if abs((a['lon'] - lon) * kx) > 7000 or abs((a['lat'] - lat) * DECK) > 7000: continue
            A = read_area(a['num']); E = EX[a['num']]; op, pxy = LAND[a['num']]
            akx = DECK * math.cos(math.radians(A['lat0']))
            for i in range(A['N']):
                p_ = A['q'][A['starts'][i]:A['starts'][i + 1]]
                if len(p_) < 3: continue
                X = (A['lon0'] + p_[:, 0] / akx - lon) * kx; Y = (A['lat0'] + p_[:, 1] / DECK - lat) * DECK
                if X.max() < x0 - 30 or X.min() > x1 + 30 or Y.max() < y0 - 30 or Y.min() > y1 + 30: continue
                poly = Polygon(np.c_[X, Y])
                if not poly.is_valid: poly = poly.buffer(0)
                gone = i < len(E) and (E[i] & 64)
                c = poly.representative_point()
                if gone:
                    if i < len(op) and op[i] and site.contains(c): land.setdefault(a['num'], []).append(i)
                    continue
                if replace is not None and replace.contains(c) and (A['st'][i] or 1) <= 3 and not (A['fl'][i] & 8):
                    land.setdefault(a['num'], []).append(i); continue
                obst.append(poly)
            for j, (px, py) in enumerate(pxy):
                X = (A['lon0'] + px / akx - lon) * kx; Y = (A['lat0'] + py / DECK - lat) * DECK
                if region.contains(shapely.Point(X, Y)): land.setdefault(a['num'], []).append(A['N'] + j)
        free = region
        if roads: free = free.difference(unary_union(roads))
        if obst: free = free.difference(unary_union(obst).buffer(8))
        # lay out footprints in the grid's frame, nearest the middle first
        rot = lambda g, s: affinity.rotate(g, s * ang, origin=(0, 0), use_radians=True)
        F = rot(free, -1); PF = prep(F)
        cx, cy = rot(region, -1).centroid.coords[0]
        bx0, by0, bx1, by1 = F.bounds
        pts = [(x, y) for x in np.arange(bx0, bx1, 3.0) for y in np.arange(by0, by1, 3.0)]
        pts.sort(key=lambda t: (t[0] - cx) ** 2 + (t[1] - cy) ** 2)
        placed, T = [], np.zeros((0, 4))           # T: boxes already taken, grown by the gap (they're all square to the grid here)
        for (w, d) in SIZES:                       # one pass per size, so slabs and towers get the open ground first
            for (x, y) in pts:
                for (ww, dd) in ((w, d), (d, w)):
                    a0, b0, a1, b1 = x - ww / 2, y - dd / 2, x + ww / 2, y + dd / 2
                    if len(T) and np.any((T[:, 0] < a1) & (T[:, 2] > a0) & (T[:, 1] < b1) & (T[:, 3] > b0)): continue
                    r = box(a0, b0, a1, b1)
                    if not PF.contains(r): continue
                    placed.append(r); T = np.vstack([T, [a0 - GAP, b0 - GAP, a1 + GAP, b1 + GAP]]); break
        placed.sort(key=lambda r: (r.centroid.x - cx) ** 2 + (r.centroid.y - cy) ** 2)   # built from the middle out
        placed = placed[:MAX_FP]
        fps = []
        for r in placed:
            g = rot(r, 1)
            c = list(g.exterior.coords)[:4]
            fps.append([round(v, 1) for xy in c for v in xy])
        area = sum(r.area for r in placed)
        out[S['n']] = {'lon': lon, 'lat': lat, 'fp': fps, 'land': {str(k): v for k, v in land.items()}}
        print(f"{S['n']:22s} site {site.area / 4047:5.1f} ac, free {free.area / 4047:5.1f} ac, grid {math.degrees(ang):5.1f}°, "
              f"{len(fps)} footprints, {area:,.0f} m² ({area / 4047:.1f} ac), land taken from zoning {sum(len(v) for v in land.values())}")
    meta['megaSites'] = out
    json.dump(meta, open(os.path.join(ROOT, 'meta.json'), 'w'), separators=(',', ':'))
    print('wrote meta.json megaSites')

if __name__ == '__main__':
    main()
