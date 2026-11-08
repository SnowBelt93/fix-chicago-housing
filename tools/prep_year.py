#!/usr/bin/env python3
"""Year built for every building in b/<area>.wasm, for "Chicago then and now" → b/year.wasm.
Each Cook County Assessor parcel point (tools/raw/cook_parcels_chi.csv.gz) is matched to the footprint containing it, else
the nearest footprint centroid within 12 m (30 m for condo buildings), as in prep_lots.py; a building's year is the
earliest year built among its parcels (residential characteristics, else commercial valuation data). 0 = unknown.
Format (little-endian): uint32 areas, then per area: uint32 area number, uint32 N, uint16 year[N], padded to 4 bytes."""
import collections, csv, gzip, json, math, os, re, struct, sys
import numpy as np
from shapely.geometry import Point, Polygon
from shapely.strtree import STRtree
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
from check_illegal import read_area
RAW = os.path.join(ROOT, 'tools', 'raw')

yr = {}
for r in csv.DictReader(gzip.open(os.path.join(RAW, 'cook_chars_chi.csv.gz'), 'rt')):
    try: y = int(float(r.get('char_yrblt') or 0))
    except ValueError: continue
    p = r['pin'].zfill(14)
    if 1830 < y < 2030 and (p not in yr or y < yr[p]): yr[p] = y
latest = {}
for r in csv.DictReader(gzip.open(os.path.join(RAW, 'cook_comm_chi.csv.gz'), 'rt')):
    k = r.get('keypin') or ''
    if k not in latest or (r.get('year') or '') > (latest[k].get('year') or ''): latest[k] = r
for r in latest.values():
    try: y = int(float(r.get('yearbuilt') or 0))
    except ValueError: continue
    if not (1830 < y < 2030): continue
    for x in re.findall(r'\d{2}-?\d{2}-?\d{3}-?\d{3}-?\d{4}', r.get('pins') or r.get('keypin') or ''):
        x = re.sub(r'\D', '', x)
        if x not in yr: yr[x] = y
print('parcels with a year', len(yr), flush=True)
P = []
for r in csv.DictReader(gzip.open(os.path.join(RAW, 'cook_parcels_chi.csv.gz'), 'rt')):
    p = r['pin'].zfill(14)
    y = yr.get(p) or yr.get(p[:10] + '0000')
    if not y: continue
    try: P.append((float(r['lon']), float(r['lat']), y, r['class'] in ('299', '399')))
    except ValueError: pass
pts = np.array([[a, b] for a, b, _, _ in P])
meta = json.load(open(os.path.join(ROOT, 'meta.json')))
out = [struct.pack('<I', len(meta['areas']))]
known = total = 0
for a in meta['areas']:
    A = read_area(a['num'])
    kx = 111319.49 * math.cos(math.radians(A['lat0'])); ky = 111319.49
    geoms = [Polygon(p) if len(p) >= 3 else Point(p[0]) for p in A['polys']]
    tree = STRtree(geoms); cent = np.array([[g.centroid.x, g.centroid.y] for g in geoms])
    lo, hi = cent.min(0) - 0.002, cent.max(0) + 0.002
    sel = np.where((pts[:, 0] > lo[0]) & (pts[:, 0] < hi[0]) & (pts[:, 1] > lo[1]) & (pts[:, 1] < hi[1]))[0]
    year = np.zeros(A['N'], np.uint16)
    for j in sel:
        lon, lat, y, condo = P[j]; pt = Point(lon, lat); hit = None
        for k in tree.query(pt):
            if geoms[k].contains(pt): hit = int(k); break
        if hit is None:
            k = tree.nearest(pt)
            if k is not None and math.hypot((cent[k][0] - lon) * kx, (cent[k][1] - lat) * ky) < (30 if condo else 12): hit = int(k)
        if hit is not None and (not year[hit] or y < year[hit]): year[hit] = y
    known += int((year > 0).sum()); total += A['N']
    out.append(struct.pack('<II', a['num'], A['N'])); b = year.tobytes(); out.append(b + b'\0' * ((4 - len(b) % 4) % 4))
open(os.path.join(ROOT, 'b', 'year.wasm'), 'wb').write(b''.join(out))
print('buildings with a year', known, 'of', total)
