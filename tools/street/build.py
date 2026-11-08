#!/usr/bin/env python3
"""Data for "Redesign my street" → street/data/t/<ix>_<iy>.json (0.01° tiles keyed by each street piece's midpoint,
ix = floor((lon + 88) * 100), iy = floor((lat - 41) * 100)). Each tile: {"w": [[...], ...], "r": {route: [name, riders]}}, a way =
  [osm id, name, class, lanes, lanes forward, lanes backward, one-way, bike (0 none, 1 painted, 2 protected, 3 shared),
   sidewalks (0/1), speed limit mph | 0, bus lane (0/1), [crashes, injured, killed or badly hurt, hit a pedestrian, hit a cyclist],
   [CTA bus routes running along it], [x, y, x, y...]] with x, y in millionths of a degree from the tile corner.
Crashes: City of Chicago Traffic Crashes since 2021 (tools/raw/street/crashes.csv.gz), each given to the nearest street piece
within 25 m, preferring one with the same street name. Streets: OpenStreetMap (tools/raw/street/osm_streets.json.gz).
Bus routes: transit/data/net.json, a route counts on a piece when 3 points along it are within 15 m of the route."""
import csv, gzip, json, math, os, re, collections
import numpy as np
from shapely.geometry import LineString, Point
from shapely.strtree import STRtree
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RAW = os.path.join(ROOT, 'tools', 'raw', 'street'); OUT = os.path.join(ROOT, 'street', 'data', 't')
os.makedirs(OUT, exist_ok=True)
LAT0 = 41.85; KX = 111320 * math.cos(math.radians(LAT0)); KY = 110574
def xy(lon, lat): return ((lon + 87.65) * KX, (lat - LAT0) * KY)
CLS = {'trunk': 1, 'primary': 1, 'secondary': 2, 'tertiary': 3, 'residential': 4, 'unclassified': 4, 'living_street': 5}
def num(v):
    try: return int(float(str(v).split(';')[0]))
    except (ValueError, TypeError): return 0
def bike(t):
    vals = [t.get(k, '') for k in ('cycleway', 'cycleway:both', 'cycleway:left', 'cycleway:right')]
    if any(v in ('track', 'separate') for v in vals) or t.get('cycleway:both:separation'): return 2
    if any(v in ('lane', 'buffered_lane') for v in vals): return 1
    if any(v in ('shared_lane', 'share_busway') for v in vals): return 3
    return 0
ABBR = {'AVENUE': 'AVE', 'STREET': 'ST', 'BOULEVARD': 'BLVD', 'ROAD': 'RD', 'DRIVE': 'DR', 'PLACE': 'PL', 'PARKWAY': 'PKWY', 'COURT': 'CT', 'NORTH': 'N', 'SOUTH': 'S', 'EAST': 'E', 'WEST': 'W'}
def key(name):
    w = [ABBR.get(x, x) for x in re.sub(r'[^A-Z0-9 ]', '', (name or '').upper()).split()]
    w = [x for x in w if x not in ('N', 'S', 'E', 'W')]
    return ' '.join(w[:-1] if len(w) > 1 and w[-1] in ('AVE', 'ST', 'BLVD', 'RD', 'DR', 'PL', 'PKWY', 'CT') else w)

S = json.load(gzip.open(os.path.join(RAW, 'osm_streets.json.gz'), 'rt'))
lines = [LineString([xy(*p) for p in s['g']]) for s in S]
keys = [key(s['t'].get('name')) for s in S]
tree = STRtree(lines)
print('streets', len(S), flush=True)
stats = np.zeros((len(S), 5), np.int32)
n = hit = 0
for r in csv.DictReader(gzip.open(os.path.join(RAW, 'crashes.csv.gz'), 'rt')):
    try: lon, lat = float(r['longitude']), float(r['latitude'])
    except ValueError: continue
    if not (-88 < lon < -87.4 and 41.6 < lat < 42.1): continue
    n += 1
    p = Point(xy(lon, lat)); cand = tree.query(p.buffer(25))
    if not len(cand): continue
    k = key(r.get('street_name'))
    best = min(cand, key=lambda i: lines[i].distance(p) - (20 if keys[i] == k and k else 0))
    if lines[best].distance(p) > 25: continue
    hit += 1
    t = (r.get('first_crash_type') or '').upper()
    stats[best] += [1, num(r.get('injuries_total')), num(r.get('injuries_fatal')) + num(r.get('injuries_incapacitating')), 'PEDESTRIAN' in t, 'PEDALCYCLIST' in t]
print('crashes', n, 'placed', hit, flush=True)
net = json.load(open(os.path.join(ROOT, 'transit', 'data', 'net.json')))
segs, owner = [], []
for b in net['bus']:
    for path in b['paths']:
        for a, c in zip(path, path[1:]):
            segs.append(LineString([xy(*a[:2]), xy(*c[:2])])); owner.append(b['id'])
btree = STRtree(segs)
routes = {}
for b in net['bus']: routes[b['id']] = [b.get('short') or b['id'], b.get('name') or '', b.get('rides') or 0]
onway = []
for i, L in enumerate(lines):
    pts = [L.interpolate(f, normalized=True) for f in (0.2, 0.5, 0.8)]
    hits = None
    for p in pts:
        here = {owner[j] for j in btree.query(p.buffer(15))}
        hits = here if hits is None else hits & here
    onway.append(sorted(hits or []))
tiles = collections.defaultdict(lambda: {'w': [], 'r': {}})
for i, s in enumerate(S):
    t, g = s['t'], s['g']; mid = g[len(g) // 2]
    ix, iy = int(math.floor((mid[0] + 88) * 100)), int(math.floor((mid[1] - 41) * 100)); x0, y0 = ix / 100 - 88, iy / 100 + 41
    T = tiles[(ix, iy)]
    for rid in onway[i]: T['r'][rid] = routes.get(rid)
    sw = 1 if any(t.get(k) not in (None, 'no', 'none') for k in ('sidewalk', 'sidewalk:both', 'sidewalk:left', 'sidewalk:right')) or CLS.get(t.get('highway'), 4) <= 4 else 0
    T['w'].append([s['id'], t.get('name', ''), CLS.get(t.get('highway'), 4), num(t.get('lanes')), num(t.get('lanes:forward')), num(t.get('lanes:backward')),
                   1 if t.get('oneway') in ('yes', '1') else 0, bike(t), sw, num(t.get('maxspeed')), 1 if (t.get('lanes:bus') or t.get('bus:lanes') or t.get('busway')) else 0,
                   stats[i].tolist(), onway[i], [v for p in g for v in (round((p[0] - x0) * 1e6), round((p[1] - y0) * 1e6))]])
for (ix, iy), T in tiles.items(): json.dump(T, open(os.path.join(OUT, f'{ix}_{iy}.json'), 'w'), separators=(',', ':'))
print('tiles', len(tiles))
