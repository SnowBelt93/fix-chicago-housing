#!/usr/bin/env python3
"""Data for "What can I build on my lot?" (lot/index.html): Chicago cut into 0.01° tiles, each a small JSON file
lot/data/t/<ix>_<iy>.json with ix = floor((lon + 88) * 100), iy = floor((lat - 41) * 100):
  zn  zoning class names used in the tile
  z   zoning districts clipped to the tile, simplified to ~1 m: [zone index, pd number, [x, y, x, y, ...] per ring...]
  b   buildings matched to a parcel: [footprint sq ft, stories (2013 data or LiDAR), homes (2013 data), flags, [x, y, ...]]
  p   parcels: [pin, x, y, assessor class, land sq ft | 0, homes | -1, year built | 0, building sq ft | 0,
                building index | -1, zone index | -1, ward, condo units (for a condo building) | 0, address | ""]
x, y are integer millionths of a degree from the tile's corner. Condo unit PINs are folded into one record per
building (first 10 digits of the PIN). Addresses come from tools/raw/cook_addr_chi.csv.gz when present, and the
street index for the search box is written to lot/data/streets.json + lot/data/a/<key>.json.
Needs tools/raw/zoning.geojson.gz, cook_parcels_chi.csv.gz, cook_chars_chi.csv.gz, wards2023.geojson, b/*.wasm
(optional: cook_addr_chi.csv.gz, cook_comm_chi.csv.gz)."""
import collections, csv, gzip, json, math, os, re, sys
import numpy as np
from shapely.geometry import shape, Point, Polygon, box as sbox
from shapely.strtree import STRtree
from shapely import prepared

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
from check_illegal import read_area, apts, SINGLE
RAW = os.path.join(ROOT, 'tools', 'raw')
OUT = os.path.join(ROOT, 'lot', 'data')
S = 1e6
def tkey(lon, lat): return int(math.floor((lon + 88) * 100)), int(math.floor((lat - 41) * 100))
def corner(ix, iy): return ix / 100 - 88, iy / 100 + 41

SUFFIX = {'AVE', 'ST', 'BLVD', 'PL', 'RD', 'DR', 'CT', 'PKWY', 'TER', 'LN', 'WAY', 'HWY', 'SQ', 'CIR', 'PLZ', 'EXPY', 'ROW', 'WALK'}
FIX = {'PKY': 'PKWY', 'DRIVE': 'DR', 'AV': 'AVE', 'BL': 'BLVD', 'TERR': 'TER', 'PKWAY': 'PKWY'}
def clean_addr(a):
    """'2150 N MILWAUKEE AVE 2ND F' -> '2150 N MILWAUKEE AVE': drop unit words after the street type."""
    t = [FIX.get(w, w) for w in re.sub(r'\s+', ' ', (a or '').upper()).strip().split(' ') if w]
    last = max((i for i, w in enumerate(t) if w in SUFFIX and i >= 2), default=None)
    if last is not None: t = t[:last + 1]
    else:
        while len(t) > 2 and (re.search(r'\d', t[-1]) or t[-1] in ('HSE', 'HOUSE', 'COMM', 'REAR', 'BSMT', 'GARDEN', 'LOT', 'F', 'FL', 'FLR', 'UNIT', 'APT', 'GAR', 'BLDG', 'A', 'B', 'C', 'D', 'E', 'G', 'R')): t.pop()
    return ' '.join(t)

def main():
    os.makedirs(os.path.join(OUT, 't'), exist_ok=True)
    meta = json.load(open(os.path.join(ROOT, 'meta.json')))
    # zoning
    gj = json.load(gzip.open(os.path.join(RAW, 'zoning.geojson.gz')))
    ZG, ZC, ZP = [], [], []
    for f in gj['features']:
        p = {k.lower(): v for k, v in (f.get('properties') or {}).items()}
        try: g = shape(f['geometry']).buffer(0)
        except Exception: continue
        if g.is_empty: continue
        ZG.append(g); ZC.append((p.get('zone_class') or '?').strip().upper()); ZP.append(int(float(p.get('pd_num') or 0)))
    ztree = STRtree(ZG); zprep = [prepared.prep(g) for g in ZG]
    print('zoning', len(ZG), flush=True)
    # wards
    W = json.load(open(os.path.join(RAW, 'wards2023.geojson')))
    WG = [shape(f['geometry']) for f in W['features']]
    WN = [int(float({k.lower(): v for k, v in f['properties'].items()}.get('ward'))) for f in W['features']]
    wtree = STRtree(WG); wprep = [prepared.prep(g) for g in WG]
    # parcels + characteristics
    P = {}
    for r in csv.DictReader(gzip.open(os.path.join(RAW, 'cook_parcels_chi.csv.gz'), 'rt')):
        try: P[r['pin'].zfill(14)] = [float(r['lon']), float(r['lat']), r['class']]
        except ValueError: pass
    C = collections.defaultdict(lambda: dict(land=0, apts=None, yr=0, bsf=0))
    for r in csv.DictReader(gzip.open(os.path.join(RAW, 'cook_chars_chi.csv.gz'), 'rt')):
        c = C[r['pin'].zfill(14)]
        try:
            v = float(r.get('char_land_sf') or 0)
            if v > 0 and not c['land']: c['land'] = v
        except ValueError: pass
        a = apts(r.get('char_apts'))
        if not a and (r.get('class') or '') in SINGLE: a = 1
        if a: c['apts'] = (c['apts'] or 0) + a
        try:
            y = int(float(r.get('char_yrblt') or 0))
            if y and (not c['yr'] or y < c['yr']): c['yr'] = y
        except ValueError: pass
        try: c['bsf'] += int(float(r.get('char_bldg_sf') or 0))
        except ValueError: pass
    comm = os.path.join(RAW, 'cook_comm_chi.csv.gz')
    if os.path.exists(comm):
        latest = {}
        for r in csv.DictReader(gzip.open(comm, 'rt')):
            k = r.get('keypin') or ''
            if k not in latest or (r.get('year') or '') > (latest[k].get('year') or ''): latest[k] = r
        n = 0
        for r in latest.values():
            try: land = float(r.get('landsf') or 0)
            except ValueError: land = 0
            pins = [re.sub(r'\D', '', x) for x in re.findall(r'\d{2}-?\d{2}-?\d{3}-?\d{3}-?\d{4}', r.get('pins') or r.get('keypin') or '')]
            key = re.sub(r'\D', '', r.get('keypin') or '')
            if not pins and key: pins = [key]
            if not pins: continue
            for x in pins:
                if land > 0 and not C[x]['land']: C[x]['land'] = land / len(pins); n += 1   # a multi-PIN property's land, split evenly
            try: units = int(float(r.get('tot_units') or 0))
            except ValueError: units = 0
            if units and key and C[key]['apts'] is None: C[key]['apts'] = units
            try:
                y = int(float(r.get('yearbuilt') or 0))
                if y and key and not C[key]['yr']: C[key]['yr'] = y
            except ValueError: pass
        print('commercial land added', n, flush=True)
    ADDR = {}
    ap = os.path.join(RAW, 'cook_addr_chi.csv.gz')
    if os.path.exists(ap):
        for r in csv.DictReader(gzip.open(ap, 'rt')):
            a = (r.get('prop_address_full') or '').strip().upper()
            if a: ADDR[r['pin'].zfill(14)] = clean_addr(a)
        print('addresses', len(ADDR), flush=True)
    # fold condo units into one record per building
    groups = collections.defaultdict(list)
    for pin, (lon, lat, cls) in P.items():
        if cls in ('299', '399'): groups[pin[:10]].append(pin)
    recs = {}
    for pin, (lon, lat, cls) in P.items():
        if cls in ('299', '399'): continue
        recs[pin] = dict(lon=lon, lat=lat, cls=cls, units=0)
    for k, pins in groups.items():
        lon = sum(P[p][0] for p in pins) / len(pins); lat = sum(P[p][1] for p in pins) / len(pins)
        a = next((ADDR[p] for p in pins if p in ADDR), '')
        recs[pins[0]] = dict(lon=lon, lat=lat, cls='299', units=len(pins), addr=a)
    print('lot records', len(recs), flush=True)
    pins = list(recs); pts = np.array([[recs[p]['lon'], recs[p]['lat']] for p in pins])
    # buildings: footprint containing the parcel point, else the nearest centroid within 12 m
    bld = {}           # (area, i) -> [fp, st, un, flags, poly]
    owner = {}         # pin -> (area, i)
    for a in meta['areas']:
        A = read_area(a['num'])
        lat0 = A['lat0']; kx = 111319.49 * math.cos(math.radians(lat0)); ky = 111319.49
        geoms = [Polygon(p) if len(p) >= 3 else Point(p[0]) for p in A['polys']]
        tree = STRtree(geoms)
        cent = np.array([[g.centroid.x, g.centroid.y] for g in geoms])
        lo, hi = cent.min(0) - 0.002, cent.max(0) + 0.002
        sel = np.where((pts[:, 0] > lo[0]) & (pts[:, 0] < hi[0]) & (pts[:, 1] > lo[1]) & (pts[:, 1] < hi[1]))[0]
        for j in sel:
            if pins[j] in owner: continue
            pt = Point(pts[j]); hit = None
            for k in tree.query(pt):
                if geoms[k].contains(pt): hit = int(k); break
            if hit is None:
                k = tree.nearest(pt)
                if k is not None and math.hypot((cent[k][0] - pts[j][0]) * kx, (cent[k][1] - pts[j][1]) * ky) < (30 if recs[pins[j]]['cls'] == '299' else 12): hit = int(k)
            if hit is None: continue
            gone = False
            owner[pins[j]] = (a['num'], hit)
            if (a['num'], hit) not in bld:
                bld[(a['num'], hit)] = [int(A['fp'][hit]), int(A['st'][hit]), int(A['un'][hit]), int(A['fl'][hit]), A['polys'][hit]]
        print('area', a['num'], len(owner), flush=True)
    # tiles
    tiles = collections.defaultdict(lambda: dict(zn=[], z=[], b=[], p=[], _b={}, _z={}))
    zcache = {}
    for j, pin in enumerate(pins):
        r = recs[pin]; lon, lat = r['lon'], r['lat']; ix, iy = tkey(lon, lat); T = tiles[(ix, iy)]; x0, y0 = corner(ix, iy)
        pt = Point(lon, lat)
        zi = -1
        for k in ztree.query(pt):
            if zprep[k].contains(pt): zi = int(k); break
        if zi >= 0:
            zc = ZC[zi]
            if zc not in T['zn']: T['zn'].append(zc)
            zix = T['zn'].index(zc)
        else: zix = -1
        ward = 0
        for k in wtree.query(pt):
            if wprep[k].contains(pt): ward = WN[k]; break
        bi = -1
        if pin in owner:
            key = owner[pin]
            if key not in T['_b']:
                fp, st, un, fl, poly = bld[key]
                T['_b'][key] = len(T['b'])
                T['b'].append([fp, st, un, fl, [v for q in poly for v in (round((q[0] - x0) * S), round((q[1] - y0) * S))]])
            bi = T['_b'][key]
        c = C.get(pin) or {}
        if r['cls'] == '299': c = {}
        addr = r.get('addr') or ADDR.get(pin, '')
        T['p'].append([pin, round((lon - x0) * S), round((lat - y0) * S), r['cls'], round(c.get('land') or 0),
                       -1 if c.get('apts') is None else c['apts'], c.get('yr') or 0, c.get('bsf') or 0, bi, zix, ward, r['units'], addr])
    # zoning polygons for drawing, clipped per tile
    for (ix, iy), T in tiles.items():
        x0, y0 = corner(ix, iy); bb = sbox(x0, y0, x0 + 0.01, y0 + 0.01)
        for k in ztree.query(bb):
            g = ZG[k].intersection(bb)
            if g.is_empty: continue
            g = g.simplify(0.00001)
            zc = ZC[k]
            if zc not in T['zn']: T['zn'].append(zc)
            polys = [g] if g.geom_type == 'Polygon' else [q for q in getattr(g, 'geoms', []) if q.geom_type == 'Polygon']
            for q in polys:
                rings = [list(q.exterior.coords)] + [list(i.coords) for i in q.interiors]
                T['z'].append([T['zn'].index(zc), ZP[k]] + [[v for c in ring for v in (round((c[0] - x0) * S), round((c[1] - y0) * S))] for ring in rings])
    n = 0
    for (ix, iy), T in tiles.items():
        T.pop('_b'); T.pop('_z')
        json.dump(T, open(os.path.join(OUT, 't', f'{ix}_{iy}.json'), 'w'), separators=(',', ':')); n += 1
    print('tiles', n)
    # street index for the search box: "N MILWAUKEE AVE" -> house numbers with their tile and record
    if ADDR:
        streets = collections.defaultdict(list)
        for (ix, iy), T in tiles.items():
            for k, p in enumerate(T['p']):
                m = re.match(r'^(\d+)[A-Z]?(?:-\d+)?\s+(.+)$', p[12] or '')
                if not m: continue
                streets[m.group(2)].append([int(m.group(1)), ix, iy, k])
        os.makedirs(os.path.join(OUT, 'a'), exist_ok=True)
        shards = collections.defaultdict(dict)
        def shard(name): return re.sub(r'[^A-Z0-9]', '', re.sub(r'^[NSEW] ', '', name))[:2] or '_'
        for name, L in streets.items():
            L.sort(); shards[shard(name)][name] = L
        for k, d in shards.items(): json.dump(d, open(os.path.join(OUT, 'a', f'{k}.json'), 'w'), separators=(',', ':'))
        json.dump(sorted([name, len(L)] for name, L in streets.items()), open(os.path.join(OUT, 'streets.json'), 'w'), separators=(',', ':'))   # with address counts, to rank suggestions
        print('streets', len(streets), 'shards', len(shards))

if __name__ == '__main__':
    main()
