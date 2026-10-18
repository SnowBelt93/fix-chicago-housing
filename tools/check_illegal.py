#!/usr/bin/env python3
"""Check the game's "illegal to build today" flags (bit 64, set by prep_zoning.py from an ESTIMATED lot of
max(2 x footprint, 3,125 sq ft) and the 2013 home count) against Cook County Assessor data: each parcel's real
land square footage and, for 2-6 unit buildings, its real apartment count.

Matching: every Chicago parcel point (Parcel Universe, lat/lon near the parcel's center) is assigned to the building
whose footprint contains it, else to the nearest building centroid within 12 m. A building's real lot = sum of its
parcels' land square feet (from the characteristics file; parcels without it are left unknown).

Usage: python3 tools/check_illegal.py [--write]    (--write sets bit 64 from real lots where known)
Needs tools/raw/zoning.geojson.gz, cook_parcels_chi.csv.gz, cook_chars_chi.csv.gz (fetch_parcels.py)."""
import collections, csv, gzip, json, math, os, re, struct, sys
import numpy as np
from shapely.geometry import shape, Point, Polygon
from shapely.strtree import STRtree
from shapely import prepared

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
from prep_zoning import mla

SINGLE = {'202', '203', '204', '205', '206', '207', '208', '209', '210', '234', '278', '295'}
WORDS = {'ONE': 1, 'TWO': 2, 'THREE': 3, 'FOUR': 4, 'FIVE': 5, 'SIX': 6, 'NONE': 0}
def apts(v):
    v = (v or '').strip().upper()
    if v.isdigit(): return int(v)
    return WORDS.get(v)

def load_zoning():
    gj = json.load(gzip.open(os.path.join(ROOT, 'tools', 'raw', 'zoning.geojson.gz')))
    G, Z = [], []
    for f in gj['features']:
        if not f.get('geometry'): continue
        p = {k.lower(): v for k, v in (f.get('properties') or {}).items()}
        try: g = shape(f['geometry'])
        except Exception: continue
        if g.is_empty: continue
        G.append(g); Z.append(p.get('zone_class') or p.get('zoning'))
    return STRtree(G), [prepared.prep(g) for g in G], Z

def read_area(num):
    buf = open(os.path.join(ROOT, 'b', f'{num}.wasm'), 'rb').read()
    N, V = struct.unpack_from('<II', buf, 0); lon0, lat0 = struct.unpack_from('<dd', buf, 8)
    q = np.frombuffer(buf[24:24 + 4 * V], dtype='<i2').reshape(-1, 2).astype(float) * 0.5
    o = 24 + 4 * V
    nv = np.frombuffer(buf[o:o + N], np.uint8); o += N
    st = np.frombuffer(buf[o:o + N], np.uint8); o += N
    fl_off = o; fl = np.frombuffer(buf[o:o + N], np.uint8); o += N
    o += (N * 3) % 2
    un = np.frombuffer(buf[o:o + 2 * N], '<u2'); o += 2 * N
    fp = np.frombuffer(buf[o:o + 2 * N], '<u2').astype(float) * 2
    kx = 111319.49 * math.cos(math.radians(lat0)); ky = 111319.49
    polys, start = [], 0
    for i in range(N):
        k = int(nv[i]); pts = q[start:start + k]; start += k
        polys.append([(lon0 + x / kx, lat0 + y / ky) for x, y in pts])
    return dict(N=N, polys=polys, fl=fl, fl_off=fl_off, un=un, fp=fp, st=st, buf=buf, lat0=lat0)

def main():
    write = '--write' in sys.argv
    meta = json.load(open(os.path.join(ROOT, 'meta.json')))
    ztree, zprep, zones = load_zoning()
    # parcels and characteristics
    P = {}
    for r in csv.DictReader(gzip.open(os.path.join(ROOT, 'tools', 'raw', 'cook_parcels_chi.csv.gz'), 'rt')):
        try: P[r['pin'].zfill(14)] = (float(r['lon']), float(r['lat']), r['class'])
        except ValueError: pass
    C = collections.defaultdict(lambda: dict(land=None, apts=None, cls=None, cards=0))
    for r in csv.DictReader(gzip.open(os.path.join(ROOT, 'tools', 'raw', 'cook_chars_chi.csv.gz'), 'rt')):
        c = C[r['pin'].zfill(14)]; c['cards'] += 1; c['cls'] = r.get('class')
        try:
            v = float(r.get('char_land_sf') or 0)
            if v > 0 and not c['land']: c['land'] = v
        except ValueError: pass
        a = apts(r.get('char_apts'))
        if not a and (r.get('class') or '') in SINGLE: a = 1          # single-family classes report no apartments
        if a: c['apts'] = (c['apts'] or 0) + a
    print('parcels with location', len(P), '| with characteristics', len(C))
    pins = list(P); pts = np.array([P[p][:2] for p in pins])
    res = collections.Counter(); byzone = collections.defaultdict(collections.Counter); lot_err = []
    examples = collections.defaultdict(list)
    for a in meta['areas']:
        A = read_area(a['num'])
        lat0 = A['lat0']; kx = 111319.49 * math.cos(math.radians(lat0)); ky = 111319.49
        geoms = [Polygon(p) if len(p) >= 3 else Point(p[0]) for p in A['polys']]
        tree = STRtree(geoms)
        cent = np.array([[g.centroid.x, g.centroid.y] for g in geoms])
        lo, hi = cent.min(0) - 0.002, cent.max(0) + 0.002
        sel = np.where((pts[:, 0] > lo[0]) & (pts[:, 0] < hi[0]) & (pts[:, 1] > lo[1]) & (pts[:, 1] < hi[1]))[0]
        owner = collections.defaultdict(list)
        for j in sel:
            pt = Point(pts[j]); hit = None
            for k in tree.query(pt):
                if geoms[k].contains(pt): hit = int(k); break
            if hit is None:
                k = tree.nearest(pt)
                if k is not None:
                    d = math.hypot((cent[k][0] - pts[j][0]) * kx, (cent[k][1] - pts[j][1]) * ky)
                    if d < 12: hit = int(k)
            if hit is not None: owner[hit].append(pins[j])
        buf = bytearray(A['buf']) if write else None
        for i in range(A['N']):
            un = int(A['un'][i]); was = bool(A['fl'][i] & 64)
            c0 = geoms[i].centroid
            zone = None
            for k in ztree.query(c0):
                if zprep[k].contains(c0): zone = zones[k]; break
            limit = mla(zone)
            if limit is None or (un < 2 and not was): continue
            ps = owner.get(i, [])
            land = [C[p]['land'] for p in ps if p in C and C[p]['land']]
            real_lot = sum(land) if land else None
            ap = [C[p]['apts'] for p in ps if p in C and C[p]['apts']]
            real_units = sum(ap) if ap and len(ap) == len([p for p in ps if p in C]) else None
            est_lot = max(A['fp'][i] * 2, 3125)
            if real_lot: lot_err.append(est_lot / real_lot)
            units = real_units or un
            def ill(lot, u): return u >= 2 and u > (0 if limit == 0 else max(1, int(lot // limit)))
            now = ill(real_lot, units) if real_lot else None
            key = ('no real lot' if now is None else 'stays illegal' if was and now else 'actually legal' if was and not now
                   else 'newly illegal' if now else 'legal both')
            res[key] += 1; byzone[re.sub(r'-.*', '', (zone or '?'))][key] += 1
            if len(examples[key]) < 6 and real_lot: examples[key].append((a['name'], zone, un, real_units, round(est_lot), round(real_lot)))
            if write and now is not None:
                if now: buf[A['fl_off'] + i] |= 64
                else: buf[A['fl_off'] + i] &= ~64 & 0xFF
        if write: open(os.path.join(ROOT, 'b', f"{a['num']}.wasm"), 'wb').write(buf)
    print(dict(res))
    flagged = res['stays illegal'] + res['actually legal']
    if flagged: print(f"of flagged buildings with a real lot: {res['stays illegal'] / flagged:.1%} stay illegal, {res['actually legal'] / flagged:.1%} are actually legal")
    if res['legal both'] + res['newly illegal']: print(f"of unflagged multi-home buildings with a real lot: {res['newly illegal'] / (res['legal both'] + res['newly illegal']):.1%} are actually illegal")
    if lot_err:
        e = sorted(lot_err); print('estimated / real lot: median', round(e[len(e) // 2], 2), 'p25', round(e[len(e) // 4], 2), 'p75', round(e[3 * len(e) // 4], 2))
    for z, c in sorted(byzone.items(), key=lambda kv: -sum(kv[1].values()))[:12]: print(' ', z, dict(c))
    for k, v in examples.items(): print(k, v)

if __name__ == '__main__':
    main()
