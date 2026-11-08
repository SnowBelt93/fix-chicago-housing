#!/usr/bin/env python3
"""Builds bears/data/ for "Where Should the Bears Play?" from tools/raw/bears (fetch.py, run on main) plus data the
site already has (transit stations, Census blocks, the lake outline).

  bears/data/land.json    land big enough for a stadium: OpenStreetMap industrial, brownfield, rail yard, commercial,
                          retail, parking, racetrack, construction, port and greenfield areas, minus homes, parks, water,
                          cemeteries, schools, hospitals, golf courses and airports; pieces closer than ~30 m are joined
                          (streets between them), and only pieces of MIN_ACRES or more are kept.
                          {"min": acres, "parts": [[acres, kind, name, [ring, ...]], ...]}  rings as [[lon,lat],...]
  bears/data/places.json  hotels [lon,lat,rooms|0], parking lots [lon,lat,spaces] (spaces = tagged capacity, else lot
                          area / SQM_PER_SPACE), expressway exits [lon,lat,name], rail stations [lon,lat,name,kind,trains a
                          day both ways, lines]
  bears/data/blocks.bin   2020 Census blocks (Illinois 6 counties + Lake and Porter counties, Indiana): uint32 N, then
                          int16 x[N], int16 y[N] (10 m units east/north of ORIGIN), uint16 people[N], uint16 homes[N], uint16 jobs[N]
  bears/data/refs.json    four recent NFL stadium districts, in meters from each stadium's center, for "at real scale"
Usage: python3 tools/bears/build.py [path to tools/raw/bears]   (default: ../fch-main/tools/raw/bears, then tools/raw/bears)
"""
import csv, gzip, json, math, os, struct, sys
from shapely.geometry import Polygon, MultiPolygon, Point
from shapely.ops import unary_union
from shapely.validation import make_valid

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RAW = next((p for p in ([sys.argv[1]] if len(sys.argv) > 1 else []) + [os.path.join(os.path.dirname(ROOT), 'fch-main', 'tools', 'raw', 'bears'), os.path.join(ROOT, 'tools', 'raw', 'bears')] if os.path.exists(os.path.join(p, 'land.json.gz'))), None)
TRAW = next((p for p in [os.path.join(os.path.dirname(ROOT), 'fch-main', 'tools', 'raw', 'transit'), os.path.join(ROOT, 'tools', 'raw', 'transit')] if os.path.exists(os.path.join(p, 'blocks.csv.gz'))), None)
OUT = os.path.join(ROOT, 'bears', 'data')
os.makedirs(OUT, exist_ok=True)
ORIGIN = (41.85, -87.65)          # lat, lon
K = 111319.49
KX, KY = K * math.cos(math.radians(ORIGIN[0])), K
MIN_ACRES = 30                    # assumption: a domed stadium, its plazas and a little parking, with most fans arriving by transit
ACRE = 4046.86
JOIN_M = 15                       # close gaps up to 2 x 15 m (streets) between pieces of usable land
SQM_PER_SPACE = 30                # assumption: one surface parking space plus its share of aisles (about 325 sq ft)


def xy(lon, lat):
    return ((lon - ORIGIN[1]) * KX, (lat - ORIGIN[0]) * KY)


def ll(x, y):
    return [round(ORIGIN[1] + x / KX, 5), round(ORIGIN[0] + y / KY, 5)]


def poly(rings_outer, rings_inner=()):
    ps = []
    for r in rings_outer:
        if len(r) >= 4:
            try:
                p = Polygon([xy(*q) for q in r])
                ps.append(make_valid(p) if not p.is_valid else p)
            except Exception:
                pass
    g = unary_union(ps) if ps else None
    for r in rings_inner or ():
        if g is not None and len(r) >= 4:
            try:
                g = g.difference(make_valid(Polygon([xy(*q) for q in r])))
            except Exception:
                pass
    return g


def land():
    rows = json.load(gzip.open(os.path.join(RAW, 'land.json.gz'), 'rt'))
    ok, no, parking, names = [], [], [], []
    for row in rows:
        k, tag, name, outer = row[0], row[1], row[2], row[3]
        g = poly(outer, row[4] if len(row) > 4 else ())
        if g is None or g.is_empty:
            continue
        if k == 'ok':
            ok.append(g)
            if tag == 'amenity=parking':
                parking.append(g)
            if name and g.area > 20 * ACRE:
                names.append((g.area, name, tag, g))
        else:
            no.append(g)
    # Chicago: the city's zoning map is the authority. Manufacturing (M1-M3), planned manufacturing (PMD), C3 and
    # downtown service (DS) districts count as land that could take a stadium; residential (RS, RT, RM) and parks and
    # open space (POS) don't, whatever OpenStreetMap says.
    zp = os.path.join(ROOT, 'tools', 'raw', 'zoning.geojson.gz')
    if os.path.exists(zp):
        from shapely.geometry import shape as gshape
        nz = 0
        for f in json.load(gzip.open(zp, 'rt'))['features']:
            zc = (f['properties'].get('zone_class') or '').upper()
            try:
                g = gshape(f['geometry'])
                g = Polygon() if g.is_empty else g
                gx = poly([list(r.coords) for r in ([g] if g.geom_type == 'Polygon' else list(g.geoms)) for r in [r.exterior]])
            except Exception:
                continue
            if gx is None or gx.is_empty:
                continue
            if zc.startswith(('M1', 'M2', 'M3', 'PMD', 'C3', 'DS')):
                ok.append(gx); nz += 1
            elif zc.startswith(('RS', 'RT', 'RM', 'POS')):
                no.append(gx); nz += 1
        print('zoning districts used', nz, file=sys.stderr)
    print('ok', len(ok), 'no', len(no), file=sys.stderr)
    good = unary_union(ok).buffer(JOIN_M).buffer(-JOIN_M)
    bad = unary_union(no)
    use = good.difference(bad)
    parts = list(use.geoms) if hasattr(use, 'geoms') else [use]
    out = []
    names.sort(key=lambda t: -t[0])
    for p in parts:
        if p.geom_type != 'Polygon' or p.area < MIN_ACRES * ACRE:
            continue
        p = p.simplify(6, preserve_topology=True)
        nm, kind = '', ''
        for a, n, t, g in names:
            if g.intersects(p) and g.intersection(p).area > 0.3 * min(g.area, p.area):
                nm, kind = n, t; break
        rings = [[ll(*c) for c in p.exterior.coords]] + [[ll(*c) for c in r.coords] for r in p.interiors if Polygon(r).area > 2 * ACRE]
        out.append([round(p.area / ACRE, 1), kind, nm, rings])
    out.sort(key=lambda r: -r[0])
    print('usable parts', len(out), 'acres', round(sum(r[0] for r in out)), file=sys.stderr)
    json.dump({'min': MIN_ACRES, 'parts': out}, open(os.path.join(OUT, 'land.json'), 'w'), separators=(',', ':'))
    return parking


def places(parking):
    P = json.load(gzip.open(os.path.join(RAW, 'places.json.gz'), 'rt'))
    hotels, lots, exits = [], [], []
    seen = set()
    for kind, name, lon, lat, extra in P:
        if kind == 'hotel':
            try: rooms = int(str(extra).split(';')[0])
            except Exception: rooms = 0
            hotels.append([lon, lat, rooms])
        elif kind == 'exit':
            key = (round(lon, 3), round(lat, 3))
            if key not in seen:
                seen.add(key); exits.append([lon, lat, name or extra or ''])
    # parking: polygons give area; tagged capacity wins where it exists
    cap = {}
    for kind, name, lon, lat, extra in P:
        if kind == 'parking' and isinstance(extra, dict):
            try: cap[(round(lon, 4), round(lat, 4))] = int(extra.get('cap') or 0)
            except Exception: pass
    for g in parking:
        if g.area < 400:
            continue
        c = g.representative_point()
        lon, lat = ll(c.x, c.y)
        spaces = int(g.area / SQM_PER_SPACE)
        lots.append([lon, lat, spaces])
    print('hotels', len(hotels), 'with rooms', sum(1 for h in hotels if h[2]), 'lots', len(lots), 'exits', len(exits), file=sys.stderr)
    # rail stations from the transit tool's data (daily departures both ways)
    N = json.load(open(os.path.join(ROOT, 'transit', 'data', 'net.json')))
    rail = []
    for s in N['lStations']:
        rail.append([s['ll'][0], s['ll'][1], s['name'], 'L', s.get('deps', 0), s.get('lines', [])])
    for s in N['metraStations']:
        rail.append([s['ll'][0], s['ll'][1], s['name'], 'Metra', s.get('deps', 0), s.get('lines', [])])
    ss_trips = {l['id']: l.get('trips', 0) for l in N['southShore']['lines']}
    for s in N['southShore']['stations']:
        rail.append([s['ll'][0], s['ll'][1], s['name'], 'South Shore', sum(ss_trips.get(l, 0) for l in s.get('lines', [])), s.get('lines', [])])
    json.dump({'hotels': hotels, 'lots': lots, 'exits': exits, 'rail': rail, 'sqmPerSpace': SQM_PER_SPACE},
              open(os.path.join(OUT, 'places.json'), 'w'), separators=(',', ':'))


def blocks():
    rows = []
    for path in (os.path.join(TRAW, 'blocks.csv.gz'), os.path.join(RAW, 'in_blocks.csv.gz')):
        if not os.path.exists(path):
            print('missing', path, file=sys.stderr); continue
        for r in csv.DictReader(gzip.open(path, 'rt')):
            x, y = xy(float(r['lon']), float(r['lat']))
            X, Y = round(x / 10), round(y / 10)
            if -32768 <= X <= 32767 and -32768 <= Y <= 32767:
                rows.append((X, Y, min(65535, int(r['people'])), min(65535, int(r['homes'])), min(65535, int(r['jobs'] or 0))))
    n = len(rows)
    with open(os.path.join(OUT, 'blocks.bin'), 'wb') as f:
        f.write(struct.pack('<I', n))
        for i in range(5):
            f.write(struct.pack('<%d%s' % (n, 'h' if i < 2 else 'H'), *[r[i] for r in rows]))
    print('blocks', n, 'people', sum(r[2] for r in rows), file=sys.stderr)


def refs():
    R = json.load(gzip.open(os.path.join(RAW, 'refs.json.gz'), 'rt'))
    out = []
    for d in R:
        lon0, lat0 = d['c']; kx = K * math.cos(math.radians(lat0))
        loc = lambda p: [round((p[0] - lon0) * kx), round((p[1] - lat0) * K)]
        els = []
        for e in d['els']:
            if 'r' in e:
                els.append({'t': e['t'], 'n': e.get('n', ''), 'r': [loc(p) for p in e['r']]})
            elif 'p' in e:
                els.append({'t': e['t'], 'n': e.get('n', ''), 'p': loc(e['p'])})
        out.append({'city': d['city'], 'name': d['name'], 'els': els})
    json.dump(out, open(os.path.join(OUT, 'refs.json'), 'w'), separators=(',', ':'))


if __name__ == '__main__':
    if not RAW:
        sys.exit('no tools/raw/bears yet (run fetch.py in Actions)')
    print('raw', RAW, 'transit', TRAW, file=sys.stderr)
    pk = land()
    places(pk)
    blocks()
    refs()
    json.dump({'origin': ORIGIN, 'k': K, 'minAcres': MIN_ACRES, 'sqmPerSpace': SQM_PER_SPACE}, open(os.path.join(OUT, 'meta.json'), 'w'))
