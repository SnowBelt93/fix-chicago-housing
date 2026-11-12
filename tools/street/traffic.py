#!/usr/bin/env python3
"""How busy each main street is, for "Redesign my street" → street/data/traffic.json.
Source: City of Chicago "Average Daily Traffic Counts" (data portal gc7y-n4xa): vehicles a day on about 2,500 one-direction
street segments, counted by the city's traffic and speed cameras (downloaded on main by tools/record/fetch.py).
    python3 tools/street/traffic.py [path to adt.csv.gz]      (default ../fch-main/tools/raw/record/adt.csv.gz)
For each segment: the median day over the last 12 months of counts (at least 30 days). The two directions of the same
stretch are put together. Lanes come from the nearest OpenStreetMap piece of the same street (street/data/t tiles).
Output: {"from", "through", "segs": [[street, from, to, lon0, lat0, lon1, lat1, total a day, [[direction, a day], ...], lanes (0 unknown), one-way 0/1]]}"""
import csv, gzip, json, math, os, sys, glob, statistics, collections, datetime
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SRC = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(ROOT), 'fch-main', 'tools', 'raw', 'record', 'adt.csv.gz')
iso = lambda t: (lambda m, d, y: f'{y}-{m}-{d}')(*t.split('/'))
rows = list(csv.DictReader(gzip.open(SRC, 'rt')))
through = max(iso(r['timestamp']) for r in rows); T = datetime.date.fromisoformat(through); start = T.replace(year=T.year - 1).isoformat()
days, meta = collections.defaultdict(list), {}
for r in rows:
    d = iso(r['timestamp'])
    if d <= start: continue
    try: days[r['segmentid']].append(int(r['vehiclecount']))
    except ValueError: continue
    meta[r['segmentid']] = r
# OpenStreetMap pieces, to read lanes: a coarse grid of piece midpoints by street name
KX = 111320 * math.cos(math.radians(41.85)); KY = 110574
grid = collections.defaultdict(list)
for f in glob.glob(os.path.join(ROOT, 'street', 'data', 't', '*.json')):
    ix, iy = (int(v) for v in os.path.basename(f)[:-5].split('_')); Tl = json.load(open(f)); x0, y0 = ix / 100 - 88, iy / 100 + 41
    for w in Tl['w']:
        if w[2] > 3 or not w[1]: continue
        p = w[13]; n = len(p) // 2
        for k in range(n):
            lon, lat = x0 + p[2 * k] / 1e6, y0 + p[2 * k + 1] / 1e6
            grid[(round(lon * 200), round(lat * 200))].append((lon, lat, w[1].upper(), w[3], w[6]))
def lanes_at(lon, lat, name):
    if not name.strip(): return (0, 0)
    key = name.upper().split()[0]; best = None; bd = 60.0
    gx, gy = round(lon * 200), round(lat * 200)
    for dx in (-1, 0, 1):
        for dy in (-1, 0, 1):
            for (x, y, nm, ln, ow) in grid.get((gx + dx, gy + dy), ()):
                if key not in nm: continue
                d = math.hypot((x - lon) * KX, (y - lat) * KY)
                if d < bd: bd = d; best = (ln, ow)
    return best or (0, 0)
groups = collections.defaultdict(dict)
for sid, v in days.items():
    if len(v) < 30: continue
    m = meta[sid]; key = (m['roadname'].strip(), frozenset((m['fromsegment'].strip(), m['tosegment'].strip())))
    groups[key][m['direction'].strip()] = (round(statistics.median(v)), m)
ORDER = {'NB': 0, 'EB': 0, 'Northeast': 0, 'Northwest': 0, 'SB': 1, 'WB': 1, 'Southwest': 1, 'Southeast': 1}
NAME = {'NB': 'Northbound', 'SB': 'Southbound', 'EB': 'Eastbound', 'WB': 'Westbound', 'Northeast': 'Northeast-bound', 'Northwest': 'Northwest-bound', 'Southeast': 'Southeast-bound', 'Southwest': 'Southwest-bound'}
title = lambda s: ' '.join(w if w[:1].isdigit() else w.capitalize() for w in s.lower().split()).replace(' Ave', ' Ave').strip()
import re
street = lambda s: title(s) + (' St' if re.fullmatch(r'\d+(st|nd|rd|th)', s.strip(), re.I) else '')   # the city lists numbered streets as "35TH"
segs = []
for (road, ends), dirs in groups.items():
    if not road: continue
    ds = sorted(dirs.items(), key=lambda kv: ORDER.get(kv[0], 2)); m = ds[0][1][1]
    try: lon0, lat0, lon1, lat1 = float(m['startlon']), float(m['startlat']), float(m['endlon']), float(m['endlat'])
    except ValueError: continue
    ln, ow = lanes_at((lon0 + lon1) / 2, (lat0 + lat1) / 2, road)
    segs.append([street(road), title(m['fromsegment']), title(m['tosegment']), round(lon0, 5), round(lat0, 5), round(lon1, 5), round(lat1, 5),
                 sum(c for _, (c, _) in ds), [[NAME.get(d, d), c] for d, (c, _) in ds], ln, ow])
segs.sort(key=lambda s: (s[0], s[4], s[3]))
json.dump({'from': start, 'through': through, 'segs': segs}, open(os.path.join(ROOT, 'street', 'data', 'traffic.json'), 'w'), separators=(',', ':'))
two = [s for s in segs if len(s[8]) == 2]; four = [s for s in two if s[9] >= 4]
print('stretches', len(segs), 'with both directions', len(two), 'with lanes known', sum(1 for s in segs if s[9]), '4+ lanes', len(four))
print('4+ lanes: under 15,000 a day', sum(1 for s in four if s[7] < 15000), '15-20k', sum(1 for s in four if 15000 <= s[7] < 20000), '20k+', sum(1 for s in four if s[7] >= 20000))
print('bytes', os.path.getsize(os.path.join(ROOT, 'street', 'data', 'traffic.json')), segs[:2])
