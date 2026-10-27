#!/usr/bin/env python3
"""Midday transit network from CTA + Metra GTFS patterns, and jobs reachable by transit.

Network (the page uses the same rules in JS):
  - Walk at 3 mph (80.5 m a minute), straight line. Origins and destinations reach stops within 1/2 mile (805 m).
  - Transfers: walk between stops within 400 m.
  - Boarding wait = half the midday headway of that route and direction at that stop
    (trips leaving the first stop 10am-3pm, summed over the route's patterns; patterns with no midday trips are left out).
  - Riding: the pattern's average scheduled minutes between stops.
  - Zones: 800 m grid cells holding people or jobs (2020 Census blocks, LODES 2022 jobs), at their weighted center.
  Jobs within 45 minutes = jobs in zones whose center can be reached within 45 minutes door to door (walking alone counts).

Writes:
  transit/data/network.json   stops, patterns, zones (with today's jobs within 45 min) for the page
  tools/raw/transit/station_access.json   jobs within 45 min of each L station (for model.py)
"""
import collections, csv, gzip, json, math, os, sys
import numpy as np
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import dijkstra

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RAW = os.path.join(ROOT, 'tools', 'raw', 'transit')
OUT = os.path.join(ROOT, 'transit', 'data')
LOOP = (41.8819, -87.6278)
KX, KY = 111320 * math.cos(math.radians(41.85)), 110574
WALK = 80.5            # meters a minute (3 mph)
ACCESS_M, XFER_M, ZONE_M, CUTOFF = 805, 400, 800, 45
MID_MIN = 300          # 10am-3pm


def xy(lat, lon):
    return ((lon - LOOP[1]) * KX, (lat - LOOP[0]) * KY)


class Grid:
    def __init__(self, pts, cell):
        self.c, self.g = cell, collections.defaultdict(list)
        for i, (x, y) in enumerate(pts):
            self.g[(int(x // cell), int(y // cell))].append(i)
        self.pts = pts

    def near(self, x, y, r):
        c = self.c
        for i in range(int((x - r) // c), int((x + r) // c) + 1):
            for j in range(int((y - r) // c), int((y + r) // c) + 1):
                for k in self.g.get((i, j), ()):
                    px, py = self.pts[k]
                    d = math.hypot(px - x, py - y)
                    if d <= r:
                        yield k, d


def load_network():
    stops, sid = [], {}
    for name in ('cta', 'metra'):
        for r in csv.DictReader(gzip.open(os.path.join(RAW, f'{name}_stops.csv.gz'), 'rt')):
            if r['location_type'] not in ('', '0'):
                continue
            key = name + ':' + r['stop_id']
            sid[key] = len(stops)
            stops.append(xy(float(r['lat']), float(r['lon'])))
    routes = {}
    for name in ('cta', 'metra'):
        for r in json.load(open(os.path.join(RAW, f'{name}_routes.json'))):
            routes[name + ':' + r['id']] = 'metra' if name == 'metra' else ('L' if r['type'] == 1 else 'bus')
    pats = []
    for name in ('cta', 'metra'):
        for rid, plist in json.load(gzip.open(os.path.join(RAW, f'{name}_patterns.json.gz'), 'rt')).items():
            for p in plist:
                s = [sid.get(name + ':' + x) for x in p['stops']]
                keep = [i for i, v in enumerate(s) if v is not None]
                if len(keep) < 2:
                    continue
                pats.append({'r': name + ':' + rid, 'kind': routes.get(name + ':' + rid, 'bus'), 'dir': p['dir'],
                             's': [s[i] for i in keep], 'm': [p['min'][i] for i in keep], 'mid': p['mid']})
    # midday trips by (route, dir, stop) across patterns -> headway at that stop
    freq = collections.Counter()
    for p in pats:
        for s in p['s'][:-1]:
            freq[(p['r'], p['dir'], s)] += p['mid']
    for p in pats:
        # no midday trips: kept with a 9,999-minute headway (unusable today) so a Metra upgrade can bring it back
        p['hw'] = [9999] * len(p['s']) if p['mid'] <= 0 else [round(MID_MIN / max(freq[(p['r'], p['dir'], s)], p['mid']), 2) for s in p['s']]
    return stops, pats


def zones():
    cells = collections.defaultdict(lambda: [0.0, 0.0, 0, 0])
    for r in csv.DictReader(gzip.open(os.path.join(RAW, 'blocks.csv.gz'), 'rt')):
        p, j = int(r['people']), int(r['jobs'])
        if p + j == 0:
            continue
        x, y = xy(float(r['lat']), float(r['lon']))
        c = cells[(int(x // ZONE_M), int(y // ZONE_M))]
        w = p + j
        c[0] += x * w; c[1] += y * w; c[2] += p; c[3] += j
    Z = []
    for (cx, cy), (sx, sy, p, j) in cells.items():
        w = p + j
        Z.append((sx / w, sy / w, p, j))
    return Z


def build_graph(stops, pats, Z, extra_origins=()):
    """Nodes: stops | pattern positions | zone-out | zone-in | extra origins. Edge weights in minutes."""
    nS = len(stops)
    pos0, n = [], nS
    for p in pats:
        pos0.append(n); n += len(p['s'])
    zo, zi = n, n + len(Z); n += 2 * len(Z)
    eo = n; n += len(extra_origins)
    rows, cols, w = [], [], []
    def edge(a, b, c):
        rows.append(a); cols.append(b); w.append(max(c, 0.01))
    for p, b in zip(pats, pos0):
        for k, s in enumerate(p['s']):
            if k < len(p['s']) - 1:
                edge(s, b + k, p['hw'][k] / 2)                     # board: wait half the headway
                edge(b + k, b + k + 1, max(p['m'][k + 1] - p['m'][k], 0.2))   # ride
            if k > 0:
                edge(b + k, s, 0)                                   # get off
    sg = Grid(stops, 400)
    for a, (x, y) in enumerate(stops):
        for b, d in sg.near(x, y, XFER_M):
            if b != a:
                edge(a, b, d / WALK)                                # transfer walk
    for k, (x, y, _, _) in enumerate(Z):
        for s, d in sg.near(x, y, ACCESS_M):
            edge(zo + k, s, d / WALK); edge(s, zi + k, d / WALK)
    zg = Grid([(z[0], z[1]) for z in Z], 800)
    for k, (x, y, _, _) in enumerate(Z):
        for m, d in zg.near(x, y, ACCESS_M):
            edge(zo + k, zi + m, d / WALK)                          # walking alone
    for k, (x, y) in enumerate(extra_origins):
        for s, d in sg.near(x, y, ACCESS_M):
            edge(eo + k, s, d / WALK)
        for m, d in zg.near(x, y, ACCESS_M):
            edge(eo + k, zi + m, d / WALK)
    G = csr_matrix((w, (rows, cols)), shape=(n, n))
    return G, zo, zi, eo


def access(G, origins, zi, nz, jobs, cutoff=CUTOFF, batch=150):
    out = np.zeros(len(origins))
    for i in range(0, len(origins), batch):
        D = dijkstra(G, indices=origins[i:i + batch], limit=cutoff + 0.001)
        out[i:i + batch] = (D[:, zi:zi + nz] <= cutoff) @ jobs
        print(f'  access {i + batch}/{len(origins)}', file=sys.stderr, end='\r')
    print(file=sys.stderr)
    return out


def main():
    stops, pats = load_network()
    Z = zones()
    print('stops', len(stops), 'patterns', len(pats), 'zones', len(Z), file=sys.stderr)
    # L stations (parent) for the model
    lst = [r for r in csv.DictReader(gzip.open(os.path.join(RAW, 'cta_stops.csv.gz'), 'rt')) if r['location_type'] == '1']
    sxy = [xy(float(r['lat']), float(r['lon'])) for r in lst]
    G, zo, zi, eo = build_graph(stops, pats, Z, sxy)
    jobs = np.array([z[3] for z in Z], dtype=float)
    sg = Grid(stops, 400)
    served = [k for k, z in enumerate(Z) if any(True for _ in sg.near(z[0], z[1], ACCESS_M))]
    print('zones within 1/2 mile of a stop', len(served), file=sys.stderr)
    acc = np.zeros(len(Z))
    acc[served] = access(G, [zo + k for k in served], zi, len(Z), jobs)
    st_acc = access(G, list(range(eo, eo + len(sxy))), zi, len(Z), jobs)
    json.dump({r['stop_id']: int(a) for r, a in zip(lst, st_acc)}, open(os.path.join(RAW, 'station_access.json'), 'w'))
    tot = jobs.sum(); pop = np.array([z[2] for z in Z], dtype=float)
    print('people-weighted jobs within 45 min:', int((acc * pop).sum() / pop.sum()), 'of', int(tot), file=sys.stderr)
    net = {'walk': WALK, 'accessM': ACCESS_M, 'xferM': XFER_M, 'cutoff': CUTOFF, 'zoneM': ZONE_M,
           'stops': [[round(x), round(y)] for x, y in stops],
           'pats': [{'r': p['r'], 'k': p['kind'], 's': p['s'], 'm': p['m'], 'hw': p['hw']} for p in pats],
           'zones': {'x': [round(z[0]) for z in Z], 'y': [round(z[1]) for z in Z], 'pop': [z[2] for z in Z],
                     'jobs': [z[3] for z in Z], 'acc45': [int(a) for a in acc]}}
    json.dump(net, open(os.path.join(OUT, 'network.json'), 'w'), separators=(',', ':'))
    print('network.json', os.path.getsize(os.path.join(OUT, 'network.json')), file=sys.stderr)


if __name__ == '__main__':
    main()
