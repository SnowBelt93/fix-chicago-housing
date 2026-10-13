"""Brings the city's February 2013 building footprints up to date with Cook County's 2022 footprints (LiDAR heights).

Run from the repo root after tools/raw/cook_bldg_2022.bin.gz exists (see .github/workflows/fetch-footprints.yml):
    python3 tools/prep_fresh.py && python3 tools/prep_extra.py

What it does, per community area (building order is the random seed, so the 2013 buildings keep their indices):
  * 2013 buildings that 2022 doesn't show (under 30% of the footprint covered), or whose site is now mostly a
    different, newer building, or that are now far taller than their recorded stories, are listed as gone in
    tools/raw/fresh_gone.json; prep_extra.py turns that into the "gone" bit in b/extra.wasm (hidden, no homes, never rebuilt).
  * 2022 buildings that weren't there in 2013 are appended to the end of b/<area>.wasm as new buildings
    (flag 8 = built 2000+, so zoning never rebuilds them; stories from LiDAR height / 12 ft; units unknown = 0).
    Garage-sized structures (under 900 sq ft and under 20 ft tall) are skipped.
  * 2013 buildings with unknown stories (0) get stories from the matching 2022 LiDAR height.
Idempotent: meta.json keeps each area's 2013 counts (n13, v13) and the script always starts from those."""
import gzip, json, math, os, struct, collections
import numpy as np
import shapely
from shapely.geometry.polygon import orient
from shapely.strtree import STRtree

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, 'tools', 'raw')
DECK = 111319.49                       # metres per degree the building files are stored in (deck.gl METER_OFFSETS)
FT = 0.3048
meta = json.load(open(os.path.join(ROOT, 'meta.json')))
if meta.get('meterScale') != 'deck': raise SystemExit('run tools/rescale_meters.py first')

# ---- 2022 footprints
raw = gzip.open(os.path.join(RAW, 'cook_bldg_2022.bin.gz'), 'rb').read()
assert raw[:4] == b'CK22'
n22 = struct.unpack_from('<I', raw, 4)[0]; o = 8
H = np.empty(n22); AR = np.empty(n22); rings = []
for k in range(n22):
    h, a, npts, lon0, lat0 = struct.unpack_from('<ffHii', raw, o); o += 18
    d = np.frombuffer(raw, dtype='<i2', count=2 * (npts - 1), offset=o).reshape(-1, 2).astype(np.int64); o += 4 * (npts - 1)
    pts = np.vstack([[0, 0], d]) + [lon0, lat0]
    H[k] = h; AR[k] = a; rings.append(pts / 1e6)
print('2022 footprints read:', n22)
cen = np.array([r.mean(axis=0) for r in rings])

# ---- community areas: assign each 2022 building by its centroid
outl = {f['properties']['num']: shapely.geometry.shape(f['geometry']) for f in meta['outlines']['features']}
nums = list(outl); otree = STRtree([outl[k] for k in nums])
ip, ia = otree.query(shapely.points(cen), predicate='within')
area_of = np.full(n22, -1); area_of[ip] = np.array(nums)[ia]
print('2022 footprints inside the city:', int((area_of >= 0).sum()))

def stories(h_ft):
    """LiDAR roof height (highest point, so parapets and peaks count) to stories: ~13 ft a floor, less 4 ft of roof."""
    return int(min(255, max(1, round(max(h_ft - 4, 0) / 13))))

def read_area(num):
    buf = open(os.path.join(ROOT, 'b', f'{num}.wasm'), 'rb').read()
    N, V = struct.unpack_from('<II', buf, 0); lon0, lat0 = struct.unpack_from('<dd', buf, 8)
    q = np.frombuffer(buf, dtype='<i2', count=2 * V, offset=24).copy()
    o = 24 + 4 * V
    nv = np.frombuffer(buf, dtype=np.uint8, count=N, offset=o).copy()
    st = np.frombuffer(buf, dtype=np.uint8, count=N, offset=o + N).copy()
    fl = np.frombuffer(buf, dtype=np.uint8, count=N, offset=o + 2 * N).copy()
    po = o + 3 * N + ((3 * N) % 2)
    un = np.frombuffer(buf, dtype='<u2', count=N, offset=po).copy()
    fp = np.frombuffer(buf, dtype='<u2', count=N, offset=po + 2 * N).copy()
    return dict(N=N, V=V, lon0=lon0, lat0=lat0, q=q, nv=nv, st=st, fl=fl, un=un, fp=fp)

def write_area(num, d):
    N, V = len(d['nv']), len(d['q']) // 2
    with open(os.path.join(ROOT, 'b', f'{num}.wasm'), 'wb') as fh:
        fh.write(struct.pack('<IIdd', N, V, d['lon0'], d['lat0']))
        fh.write(d['q'].astype('<i2').tobytes())
        fh.write(d['nv'].astype(np.uint8).tobytes()); fh.write(d['st'].astype(np.uint8).tobytes()); fh.write(d['fl'].astype(np.uint8).tobytes())
        if (N * 3) % 2: fh.write(b'\0')
        fh.write(d['un'].astype('<u2').tobytes()); fh.write(d['fp'].astype('<u2').tobytes())

gone_all = {}; stats = collections.Counter(); DIAG = collections.defaultdict(list)
for a in meta['areas']:
    num = a['num']; d = read_area(num)
    n13 = a.setdefault('n13', d['N']); v13 = a.setdefault('v13', d['V'])
    # start from the 2013 buildings only
    for k in ('nv', 'st', 'fl', 'un', 'fp'): d[k] = d[k][:n13]
    d['q'] = d['q'][:2 * v13]
    kx = DECK * math.cos(math.radians(d['lat0'])); ky = DECK
    # 2013 polygons in metres
    xy = d['q'].astype(np.float64).reshape(-1, 2) * 0.5
    starts = np.concatenate([[0], np.cumsum(d['nv'].astype(np.int64))])
    B = [shapely.Polygon(xy[starts[i]:starts[i + 1]]) if d['nv'][i] >= 3 else shapely.Polygon() for i in range(n13)]
    B = np.array([b if b.is_valid else b.buffer(0) for b in B], dtype=object)
    bx0, by0 = xy.min(axis=0) - 300; bx1, by1 = xy.max(axis=0) + 300
    # nearby 2022 polygons in the same metres
    lx = (cen[:, 0] - d['lon0']) * kx; ly = (cen[:, 1] - d['lat0']) * ky
    near = np.where((lx > bx0) & (lx < bx1) & (ly > by0) & (ly < by1))[0]
    F = []
    for k in near:
        r = rings[k]; p = shapely.Polygon(np.column_stack([(r[:, 0] - d['lon0']) * kx, (r[:, 1] - d['lat0']) * ky]))
        F.append(p if p.is_valid else p.buffer(0))
    F = np.array(F, dtype=object)
    Fa = shapely.area(F); Ba = shapely.area(B)
    # overlaps
    ftree = STRtree(F)
    bi, fi = ftree.query(B, predicate='intersects')
    inter = shapely.area(shapely.intersection(B[bi], F[fi])) if len(bi) else np.array([])
    covB = np.bincount(bi, weights=inter, minlength=n13) / np.maximum(Ba, 1e-9)
    covF = np.bincount(fi, weights=inter, minlength=len(F)) / np.maximum(Fa, 1e-9)
    # garages and sheds (LiDAR max height can catch overhanging trees, so the height test is loose)
    garage = (AR[near] < 500) | ((AR[near] < 1000) & (H[near] < 30))
    # a 2022 building is new only if it barely overlaps any 2013 building (bigger outlines of the same
    # building, e.g. with porches or merged row houses, overlap a lot and stay matched)
    newF = (covF < 0.2) & ~garage
    # how much of each 2013 building is covered by new 2022 buildings
    newcov = np.bincount(bi, weights=inter * newF[fi], minlength=n13) / np.maximum(Ba, 1e-9)
    # best-matching 2022 building for each 2013 building (largest overlap)
    best = np.full(n13, -1); bestA = np.zeros(n13)
    for b_, f_, v in zip(bi, fi, inter):
        if v > bestA[b_]: bestA[b_] = v; best[b_] = f_
    gone = []; taller = set()
    for i in range(n13):
        if Ba[i] <= 0: continue
        if d['st'][i] >= 10: continue   # towers aren't torn down in a decade; a gap here means the 2022 data is missing them (e.g. Lake Point Tower)
        if covB[i] < 0.3: gone.append(i); stats['gone_missing'] += 1; continue
        if newcov[i] >= 0.5 * covB[i]:
            gone.append(i); stats['gone_replaced'] += 1
            f = best[i]; DIAG['repl'].append((Ba[i], Fa[f] if f >= 0 else 0, covB[i], newcov[i])); continue
        f = best[i]
        if f >= 0 and d['st'][i] >= 1:
            iou = bestA[i] / max(Ba[i] + Fa[f] - bestA[i], 1e-9)
            DIAG['tall'].append((iou, H[near[f]], d['st'][i], Ba[i]))
        # rebuilt taller: a different outline (IoU under 0.5) that is much taller than the recorded stories,
        # and the 2022 building doesn't also cover other 2013 buildings
        # (low-rise only: towers aren't rebuilt in a decade, and their LiDAR height includes spires and antennas)
        if f >= 0 and 1 <= d['st'][i] <= 6 and not garage[f] and H[near[f]] > d['st'][i] * 13 + 18:
            iou = bestA[i] / max(Ba[i] + Fa[f] - bestA[i], 1e-9)
            others = (covF[f] * Fa[f] - bestA[i]) / max(Fa[f], 1e-9)
            if iou < 0.5 and others < 0.2:
                gone.append(i); taller.add(int(f)); stats['gone_taller'] += 1; continue
        if f >= 0 and d['st'][i] == 0 and covB[i] >= 0.5 and H[near[f]] > 0 and bestA[i] / max(Ba[i] + Fa[f] - bestA[i], 1e-9) >= 0.4:
            d['st'][i] = stories(H[near[f]]); stats['stories_filled'] += 1
    gone_all[str(num)] = gone
    # new buildings to append: new footprints whose centroid is in this area, plus rebuilt-taller ones
    add = [j for j in range(len(F)) if (newF[j] or j in taller) and area_of[near[j]] == num]
    for j in add: DIAG['add'].append((AR[near[j]], H[near[j]], covF[j]))
    nv_new, st_new, fp_new, q_new = [], [], [], []
    for j in add:
        g = F[j]
        if g.geom_type == 'MultiPolygon': g = max(g.geoms, key=lambda p: p.area)
        if g.geom_type != 'Polygon' or g.is_empty: continue
        if AR[near[j]] < 4000: g = g.minimum_rotated_rectangle
        else:
            tol = 1.0; g2 = g.simplify(tol, preserve_topology=True)
            while len(g2.exterior.coords) > 41: tol *= 2; g2 = g.simplify(tol, preserve_topology=True)
            g = g2 if g2.geom_type == 'Polygon' and not g2.is_empty else g.minimum_rotated_rectangle
        if g.geom_type != 'Polygon' or g.is_empty: continue
        pts = np.array(orient(g, 1.0).exterior.coords)[:-1]
        if len(pts) < 3 or len(pts) > 255: continue
        qq = np.round(pts * 2)
        if np.abs(qq).max() > 32767: continue
        q_new.append(qq.astype(np.int64)); nv_new.append(len(pts))
        st_new.append(stories(H[near[j]])); fp_new.append(min(65535, int(AR[near[j]] / 2)))
    stats['added'] += len(nv_new)
    if nv_new:
        d['q'] = np.concatenate([d['q'].astype(np.int64), np.concatenate(q_new).reshape(-1)])
        d['nv'] = np.concatenate([d['nv'], np.array(nv_new, dtype=np.uint8)])
        d['st'] = np.concatenate([d['st'], np.array(st_new, dtype=np.uint8)])
        d['fl'] = np.concatenate([d['fl'], np.full(len(nv_new), 8, dtype=np.uint8)])
        d['un'] = np.concatenate([d['un'], np.zeros(len(nv_new), dtype=np.uint16)])
        d['fp'] = np.concatenate([d['fp'], np.array(fp_new, dtype=np.uint16)])
    write_area(num, d)
    a['n'] = len(d['nv']); a['new22'] = len(nv_new); a['gone22'] = len(gone)
    print(f"{a['name']}: {len(gone)} gone, {len(nv_new)} added, {stats['stories_filled']} stories filled so far", flush=True)

json.dump(gone_all, open(os.path.join(RAW, 'fresh_gone.json'), 'w'), separators=(',', ':'))
json.dump(meta, open(os.path.join(ROOT, 'meta.json'), 'w'), separators=(',', ':'))
print(dict(stats))
if os.environ.get('DIAG'): np.savez(os.environ['DIAG'], **{k: np.array(v) for k, v in DIAG.items()})   # optional diagnostics
