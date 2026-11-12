"""Recent sale prices near each lot, as neighborhood medians only: lot/data/sales.json. No single sale, address or name is
published; every figure is a median of at least MIN sales within RADIUS meters of the tile's center.
Inputs: Cook County Assessor sales (main's tools/raw/lot/sales.csv.gz: PIN, date, price, class, filters; no names) and the
lot tool's own tiles (lot/data/t) for each parcel's location, land area and zoning.
  python3 tools/lot/prep_sales.py [path to main's tools/raw/lot]

Output: {"since": {...}, "r": RADIUS, "t": {"<ix>_<iy>": {"h": [n, median], "f": [n, median], "c": [n, median],
          "l": [n, median $ per sq ft of land, median $ per home allowed or 0]}}}
  h houses (classes 202-210, 234, 278, 295)   f two- to six-flats (211, 212)   c condos (299)   l vacant land (100)
Sales kept: one parcel, not flagged by the Assessor (under $10k, a deed type that isn't a market sale, a repeat within a
year), price at least $10,000. Buildings since 2024; vacant land since 2021 (it sells less often)."""
import csv, gzip, json, math, os, sys, statistics, collections, glob, datetime
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
from prep_zoning import mla
RAW = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(ROOT), 'fch-main', 'tools', 'raw', 'lot')
RADIUS, MIN = 800, 8
SINCE = {'h': '2024-01-01', 'f': '2024-01-01', 'c': '2024-01-01', 'l': '2021-01-01'}
GROUP = {**{c: 'h' for c in ('202', '203', '204', '205', '206', '207', '208', '209', '210', '234', '278', '295')}, '211': 'f', '212': 'f', '299': 'c', '100': 'l'}
KX, KY = 111319.49 * math.cos(math.radians(41.85)), 111319.49

# every parcel's location, land and homes allowed, keyed by the first 10 digits of the PIN (condo units share them)
loc = {}
for p in glob.glob(os.path.join(ROOT, 'lot', 'data', 't', '*.json')):
    T = json.load(open(p)); ix, iy = map(int, os.path.basename(p)[:-5].split('_')); x0, y0 = ix / 100 - 88, iy / 100 + 41
    for r in T.get('p', []):
        pin, x, y, cls, land, zi = r[0], r[1], r[2], r[3], r[4], r[9]
        if not pin: continue
        z = T['zn'][zi] if zi is not None and zi >= 0 else None
        m = mla(z) if z else None
        homes = max(1, int(land // m)) if (land and m) else 0
        loc[str(pin)[:10]] = (x0 + x / 1e6, y0 + y / 1e6, land or 0, homes)
print(len(loc), 'parcels located')

pts = collections.defaultdict(list)   # group -> [(lon, lat, price, land, homes)]
skip = collections.Counter()
for r in csv.DictReader(gzip.open(os.path.join(RAW, 'sales.csv.gz'), 'rt')):
    g = GROUP.get(r['class'])
    if not g: continue
    if r['sale_date'][:10] < SINCE[g]: continue
    if r['is_multisale'] == 'True' or r['sale_filter_less_than_10k'] == 'True' or r['sale_filter_deed_type'] == 'True' or r['sale_filter_same_sale_within_365'] == 'True':
        skip['filtered'] += 1; continue
    try: price = float(r['sale_price'])
    except ValueError: continue
    if price < 10000: skip['cheap'] += 1; continue
    L = loc.get(r['pin'][:10])
    if not L: skip['unlocated'] += 1; continue
    pts[g].append((L[0], L[1], price, L[2], L[3]))
print({g: len(v) for g, v in pts.items()}, dict(skip))

# a coarse grid for neighbor lookups
cell = {}
for g, L in pts.items():
    G = collections.defaultdict(list)
    for q in L: G[(int(q[0] * KX // RADIUS), int(q[1] * KY // RADIUS))].append(q)
    cell[g] = G
def near(g, lon, lat):
    cx, cy = int(lon * KX // RADIUS), int(lat * KY // RADIUS); out = []
    for dx in (-1, 0, 1):
        for dy in (-1, 0, 1):
            for q in cell[g].get((cx + dx, cy + dy), []):
                if math.hypot((q[0] - lon) * KX, (q[1] - lat) * KY) <= RADIUS: out.append(q)
    return out
def r1k(v): return int(round(v / 1000) * 1000)

tiles = {}
for p in glob.glob(os.path.join(ROOT, 'lot', 'data', 't', '*.json')):
    k = os.path.basename(p)[:-5]; ix, iy = map(int, k.split('_')); lon, lat = ix / 100 - 88 + 0.005, iy / 100 + 41 + 0.005
    o = {}
    for g in ('h', 'f', 'c'):
        q = near(g, lon, lat)
        if len(q) >= MIN: o[g] = [len(q), r1k(statistics.median(x[2] for x in q))]
    q = [x for x in near('l', lon, lat) if x[3] >= 1000]
    if len(q) >= MIN:
        per = [x[2] / x[4] for x in q if x[4]]
        o['l'] = [len(q), round(statistics.median(x[2] / x[3] for x in q)), r1k(statistics.median(per)) if len(per) >= MIN else 0]
    if o: tiles[k] = o
json.dump({'made': datetime.date.today().isoformat(), 'since': SINCE, 'r': RADIUS, 'min': MIN, 't': tiles}, open(os.path.join(ROOT, 'lot', 'data', 'sales.json'), 'w'), separators=(',', ':'))
print(len(tiles), 'tiles with at least one median', os.path.getsize(os.path.join(ROOT, 'lot', 'data', 'sales.json')) // 1000, 'KB')
