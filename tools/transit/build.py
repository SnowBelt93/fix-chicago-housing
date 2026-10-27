#!/usr/bin/env python3
"""Write the transit tool's browser data (transit/data/) from tools/raw/transit (fetch.py) and the L ridership file.

Files:
  net.json     L, Metra and bus lines (lon/lat paths), L and Metra stations, bus stops (local meters), sources
  blocks.bin   2020 Census blocks with people and jobs, little-endian:
                 uint32 N, then int16 x[N], int16 y[N] (5 m units east/north of State & Madison),
                 uint16 people[N], uint16 jobs[N]
Local meters use the same flat projection as model.py and the page: x = dlon * 111320 * cos(41.85 deg), y = dlat * 110574.
Run model.py too (it writes model.json).
"""
import collections, csv, gzip, json, math, os, struct, sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RAW = os.path.join(ROOT, 'tools', 'raw', 'transit')
OUT = os.path.join(ROOT, 'transit', 'data')
LOOP = (41.8819, -87.6278)
KX, KY = 111320 * math.cos(math.radians(41.85)), 110574
# Metra station counts are fall 2018; scale to today by systemwide trips (NTD UPT 2024 / 2018, times 2025's +8%).
METRA_2018_UPT, METRA_2024_UPT, METRA_2025_GROWTH = 68446239, 35051943, 1.08
METRA_SCALE = METRA_2024_UPT / METRA_2018_UPT * METRA_2025_GROWTH


def xy(lat, lon):
    return ((lon - LOOP[1]) * KX, (lat - LOOP[0]) * KY)


def ll(p):
    return [round(p[0], 5), round(p[1], 5)]


def dist_to_path(pt, path_xy):
    best = 1e18
    px, py = pt
    for (ax, ay), (bx, by) in zip(path_xy, path_xy[1:]):
        dx, dy = bx - ax, by - ay
        L = dx * dx + dy * dy
        t = 0 if L == 0 else max(0, min(1, ((px - ax) * dx + (py - ay) * dy) / L))
        best = min(best, (px - ax - t * dx) ** 2 + (py - ay - t * dy) ** 2)
    return math.sqrt(best)


def distinct_paths(shapes, tol=40, min_new=400):
    """Keep each route's shapes that add something: a shape is dropped unless 400+ m of it runs more than
    40 m from the shapes already kept (drops opposite directions and short turns, keeps branches)."""
    kept, kept_xy = [], []
    for d in sorted(shapes, key=lambda d: (-d['trips'], -len(d['pts']))):
        pxy = [xy(p[1], p[0]) for p in d['pts']]
        if kept_xy:
            # length of this shape that runs somewhere the kept shapes don't (branches, expresses)
            new = sum(math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(pxy, pxy[1:])
                      if min(dist_to_path(((a[0] + b[0]) / 2, (a[1] + b[1]) / 2), k) for k in kept_xy) > tol)
            if new < min_new:
                continue
        kept.append([ll(p) for p in d['pts']]); kept_xy.append(pxy)
    return kept


def norm(s):
    return ''.join(ch for ch in s.lower().replace('street', 'st').replace('avenue', 'ave').replace('saint', 'st') if ch.isalnum())


# GTFS station name -> 2018 count name, where the names differ
METRA_NAMES = {
    'Oak Park': 'Oak Park (Marion Street)', 'Downers Grove': 'Main Street (Downers Grove)', 'Fairview Ave.': 'Fairview Avenue (Downers Grove)',
    'Stone Ave.': 'Stone Avenue (LaGrange)', 'BNWESTERN': 'Western Avenue (18th)', 'WESTERNAVE': 'Western Avenue (Grand)',
    'Orland Park 179th': '179th Street (Orland Park)', 'Orland Park 153rd': '153rd Street (Orland Park)', 'Orland Park 143rd': '143rd Street (Orland Park)',
    'Main St.': 'Main Street (Evanston)', 'Evanston (Davis St.)': 'Davis Street (Evanston)', 'Central St.': 'Central Street (Evanston)',
    'Lake-Cook': 'Lake Cook Road', 'Glen/N. Glenview': 'North Glenview', 'Mt. Prospect': 'Mount Prospect', 'Big Timber': 'Big Timber Road',
    'Prospect Hts': 'Prospect Heights', 'Tinley-80th': '80th Avenue (Tinley Park)', 'Kensington': 'Kensington (115th Street)',
    '59th St. (U. of Chicago)': '59th Street (University of Chicago)', '211th St.': '211th Street (Lincoln Highway)',
    '51st/53rd St. (Hyde Park)': '53rd Street (Hyde Park)', '147th St.': '147th Street (Sibley Boulevard)', 'Museum Campus/11th St.': 'Roosevelt Road',
    '91st St.': '91st Street (Chesterfield)', '111th St. (Pullman)': '111th Street', 'South Chicago (93rd)': '93rd Street (South Chicago)',
    'Blue Island-Vermont': 'Blue Island (Vermont Street)', '95th St.-Longwood': 'Longwood (95th Street)', '103rd St.-Washington Hts.': 'Washington Heights',
    'Ashland': 'Ashland Avenue', 'Racine': 'Racine Avenue', 'Pingree Road': 'Pingree Rd.', 'Chicago Union Station': 'Union Station',
    'Chicago OTC': 'Ogilvie Transportation Center', 'Franklin Pk': 'Franklin Park', 'Oak Lawn Patriot': 'Oak Lawn',
}


def main():
    os.makedirs(OUT, exist_ok=True)
    # blocks
    xs, ys, ps, js = [], [], [], []
    for r in csv.DictReader(gzip.open(os.path.join(RAW, 'blocks.csv.gz'), 'rt')):
        p, j = int(r['people']), int(r['jobs'])
        if p == 0 and j == 0:
            continue
        x, y = xy(float(r['lat']), float(r['lon']))
        xs.append(round(x / 5)); ys.append(round(y / 5)); ps.append(min(p, 65535)); js.append(min(j, 65535))
    n = len(xs)
    with open(os.path.join(OUT, 'blocks.bin'), 'wb') as f:
        f.write(struct.pack('<I', n))
        for arr, fmt in ((xs, 'h'), (ys, 'h'), (ps, 'H'), (js, 'H')):
            f.write(struct.pack(f'<{n}{fmt}', *arr))
    print('blocks', n, 'people', sum(ps), 'jobs', sum(js), file=sys.stderr)

    out = {'sources': json.load(open(os.path.join(RAW, 'sources.json'))), 'origin': LOOP, 'kx': KX, 'ky': KY}
    # CTA
    croutes = json.load(open(os.path.join(RAW, 'cta_routes.json')))
    cshapes = json.load(gzip.open(os.path.join(RAW, 'cta_shapes.json.gz'), 'rt'))
    cstops = list(csv.DictReader(gzip.open(os.path.join(RAW, 'cta_stops.csv.gz'), 'rt')))
    rail_ids = [r['id'] for r in croutes if r['type'] == 1]
    rides = collections.defaultdict(list)
    for r in csv.DictReader(open(os.path.join(ROOT, 'tools', 'raw', 'cta_l_daily_2025.csv'))):
        if r['daytype'] == 'W':
            rides[r['station_id']].append(float(r['rides']))
    out['lLines'] = [{'id': r['id'], 'name': r['long'], 'color': '#' + r['color'], 'trips': r['weekday_trips'],
                      'paths': distinct_paths(cshapes.get(r['id'], []))} for r in croutes if r['type'] == 1]
    out['lStations'] = []
    for s in cstops:
        if s['location_type'] != '1':
            continue
        ls = [l for l in s['routes'].split() if l in rail_ids]
        if not ls:
            continue
        rr = rides.get(s['stop_id'])
        out['lStations'].append({'id': s['stop_id'], 'name': s['name'], 'll': ll((float(s['lon']), float(s['lat']))),
                                 'lines': ls, 'deps': int(s['weekday_departures']),
                                 'rides': round(sum(rr) / len(rr)) if rr else None})
    # bus routes and stops
    brides = {r['route']: float(r['avg_rides']) for r in csv.DictReader(open(os.path.join(RAW, 'cta_bus_ridership.csv')))}
    bus = [r for r in croutes if r['type'] == 3 and r['weekday_trips'] > 0]
    bidx = {r['id']: i for i, r in enumerate(bus)}
    out['bus'] = [{'id': r['id'], 'short': r['short'], 'name': r['long'], 'trips': r['weekday_trips'],
                   'rides': round(brides[r['short']]) if r['short'] in brides else None,
                   'paths': distinct_paths(cshapes.get(r['id'], []))[:3]} for r in bus]
    sx, sy, sr = [], [], []
    for s in cstops:
        if s['location_type'] != '0':
            continue
        rs = [bidx[r] for r in s['routes'].split() if r in bidx]
        if not rs:
            continue
        x, y = xy(float(s['lat']), float(s['lon']))
        sx.append(round(x)); sy.append(round(y)); sr.append(rs)
    out['busStops'] = {'x': sx, 'y': sy, 'r': sr}
    # Metra
    mroutes = json.load(open(os.path.join(RAW, 'metra_routes.json')))
    mshapes = json.load(gzip.open(os.path.join(RAW, 'metra_shapes.json.gz'), 'rt'))
    mstops = list(csv.DictReader(gzip.open(os.path.join(RAW, 'metra_stops.csv.gz'), 'rt')))
    out['metraLines'] = [{'id': r['id'], 'name': r['long'], 'color': '#' + r['color'], 'trips': r['weekday_trips'],
                          'paths': distinct_paths(mshapes.get(r['id'], []))} for r in mroutes]
    counts = {}
    p = os.path.join(RAW, 'metra_station_counts.csv')
    if os.path.exists(p):
        for r in csv.DictReader(open(p, encoding='utf-8-sig')):
            r = {k.strip().upper(): v for k, v in r.items()}
            if r.get('YEAR', '').strip() == '2018':
                counts[norm(r['STATION'])] = counts.get(norm(r['STATION']), 0) + float(r['BOARDS'] or 0)
    matched = 0
    out['metraStations'] = []
    for s in mstops:
        if s['location_type'] not in ('', '0'):
            continue
        b18 = counts.get(norm(METRA_NAMES.get(s['stop_id'], METRA_NAMES.get(s['name'], s['name']))))
        matched += b18 is not None
        out['metraStations'].append({'id': s['stop_id'], 'name': s['name'], 'll': ll((float(s['lon']), float(s['lat']))),
                                     'lines': s['routes'].split(), 'deps': int(s['weekday_departures']),
                                     'boards2018': round(b18) if b18 is not None else None,
                                     'boards': round(b18 * METRA_SCALE) if b18 is not None else None})
    out['metraScale'] = round(METRA_SCALE, 4)
    # route miles (shared track counted once): sample every 100 m, skip points within 60 m of one already counted
    def route_mi(ids):
        seen, n = set(), 0
        for l in out['metraLines']:
            if l['id'] not in ids:
                continue
            for path in l['paths']:
                pxy, mine = [xy(p[1], p[0]) for p in path], set()
                for (ax, ay), (bx, by) in zip(pxy, pxy[1:]):
                    k = max(1, int(math.hypot(bx - ax, by - ay) // 100))
                    for t in range(k):
                        x, y = ax + (bx - ax) * t / k, ay + (by - ay) * t / k
                        cx, cy = int(x // 60), int(y // 60)
                        mine.add((cx, cy))
                        if not any((cx + i, cy + j) in seen for i in (-1, 0, 1) for j in (-1, 0, 1)):
                            n += 1   # this 100 m isn't on track already counted for another path
                seen |= mine
        return round(n * 100 / 1609.34, 1)
    ids = [l['id'] for l in out['metraLines']]
    out['metraRouteMi'] = {'diesel': route_mi([i for i in ids if i != 'ME']), 'electric': route_mi(['ME'])}
    print('metra route miles', out['metraRouteMi'], file=sys.stderr)
    print('metra stations', len(out['metraStations']), 'with 2018 counts', matched, 'of', len(counts), 'count names', file=sys.stderr)
    if counts:
        miss = [s['name'] for s in out['metraStations'] if s['boards2018'] is None]
        print('  unmatched:', miss[:40], file=sys.stderr)
    # Chicago outline + lake for the fallback basemap (from the housing game's meta.json)
    meta = json.load(open(os.path.join(ROOT, 'meta.json')))
    out['lake'] = meta.get('lake'); out['cityOutline'] = meta.get('cityOutline')
    json.dump(out, open(os.path.join(OUT, 'net.json'), 'w'), separators=(',', ':'))
    # construction cost index (FHWA NHCCI, annual average of quarters; the latest year uses its quarters so far) and CPI-U
    p = os.path.join(RAW, 'nhcci.csv')
    if os.path.exists(p):
        qs = collections.defaultdict(list); lastq = None
        for r in csv.DictReader(open(p)):
            y = int(r['quarter'].split()[0]); qs[y].append(float(r['NHCCI'])); lastq = r['quarter']
        ix = {y: round(sum(v) / len(v), 4) for y, v in qs.items()}
        cpi = {}
        pc = os.path.join(RAW, 'cpi.json')
        if os.path.exists(pc):
            m = collections.defaultdict(list); latest = None
            for d in json.load(open(pc))['Results']['series'][0]['data']:
                if d['period'].startswith('M') and d['period'] != 'M13' and d['value'] not in ('-', ''):
                    m[int(d['year'])].append(float(d['value']))
                    if d.get('latest') == 'true':
                        latest = (int(d['year']), d['periodName'])
            cpi = {y: round(sum(v) / len(v), 3) for y, v in m.items()}
        json.dump({'index': ix, 'first': min(ix), 'latest': max(ix), 'latestQuarter': lastq, 'cpi': cpi, 'cpiLatest': max(cpi) if cpi else None,
                   'source': 'FHWA National Highway Construction Cost Index (data.transportation.gov r94d-n4f9); BLS CPI-U (CUUR0000SA0)'},
                  open(os.path.join(OUT, 'costindex.json'), 'w'))
        print('cost index through', lastq, file=sys.stderr)
    # roads, rail corridors and rivers (OpenStreetMap) for snapping, crossing flags and the fallback basemap
    p = os.path.join(RAW, 'osm.json.gz')
    if os.path.exists(p):
        osm = json.load(gzip.open(p, 'rt'))
        geo = {}
        for k, items in osm.items():
            geo[k] = [[nm[:40], [c for q in pts for c in (round(xy(q[1], q[0])[0]), round(xy(q[1], q[0])[1]))]] for nm, pts in items]
        json.dump(geo, open(os.path.join(OUT, 'geo.json'), 'w'), separators=(',', ':'))
        print('geo.json', os.path.getsize(os.path.join(OUT, 'geo.json')), {k: len(v) for k, v in geo.items()}, file=sys.stderr)
    print('net.json', os.path.getsize(os.path.join(OUT, 'net.json')), 'bytes;', 'L', len(out['lStations']), 'bus', len(out['bus']),
          'stops', len(sx), file=sys.stderr)


if __name__ == '__main__':
    main()
