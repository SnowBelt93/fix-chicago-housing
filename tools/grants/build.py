"""Data for the grants finder (/grants/) and the affordable deal check (/deal/), from downloads on main
(tools/lot/fetch.py steps hudlim, amen, places, acs2, geo2, treasury -> tools/raw/lot/, checked out at ../fch-main).
  python3 tools/grants/build.py [path to main's tools/raw/lot]
Writes grants/data/:
  limits.json    HUD FY2026 tax-credit (MTSP) 50% income limits for the Chicago area by household size, the median,
                 and the latest 10-year Treasury yield
  stations.json  [[name, lon, lat, "L" | "M"]] from meta.json
  amen.json      [[kind, lon, lat]]: supermarkets, health care, schools, parks (OpenStreetMap contributors)
  tracts.json    {"mfi", "t": {tract: {"pma": [share of households at or above the median, poverty rate], "rent": median gross rent}}}
                 pma = the tract plus every tract touching it (the city's Primary Market Area is "census tracts containing the
                 site and adjacent tracts")
  g/<ix>_<iy>.json  same 0.01° tiles as lot/data/t: {"f": [[kind, name, [[ring as int offsets in 1e-6 deg], …]], …]}
                 kinds: tr (census tract id), qct26 / qct27 (HUD Qualified Census Tracts), dda (HUD Small Area DDA by ZIP,
                 name = the years), tif (TIF district name)"""
import gzip, json, math, os, sys, csv, collections, datetime, io
from shapely.geometry import shape, box, Polygon
from shapely import make_valid
from shapely.strtree import STRtree
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RAW = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(ROOT), 'fch-main', 'tools', 'raw', 'lot')
OUT = os.path.join(ROOT, 'grants', 'data'); os.makedirs(os.path.join(OUT, 'g'), exist_ok=True)
def gz(n): return gzip.open(os.path.join(RAW, n), 'rt')
def dump(n, o): json.dump(o, open(os.path.join(OUT, n), 'w'), separators=(',', ':'), ensure_ascii=False)

# ---- income limits (MTSP FY2026, Cook County row) + Treasury
lim = None
for line in gz('hud/mtsp_MTSP-Data-FY26.xlsx.txt.gz'):
    c = line.rstrip('\n').split('|')
    if c[0] == 'MTSP2026' and c[1] == 'fips': head = c
    elif c[0] == 'MTSP2026' and len(c) > 20 and c[1].startswith('17031'): lim = dict(zip(head, c))
l50 = [int(lim[f'lim50_26p{i}']) for i in range(1, 9)]
rows = list(csv.DictReader(open(os.path.join(RAW, 'treasury.csv'))))
rows = [r for r in rows if r.get('10 Yr')]
last = max(rows, key=lambda r: datetime.datetime.strptime(r['Date'], '%m/%d/%Y'))
dump('limits.json', {'label': 'FY2026 income limits', 'area': lim['hud_area_name'], 'median': int(lim['median2026']), 'l50': l50,
                     'src': 'https://www.huduser.gov/portal/datasets/mtsp.html', 'ust10': float(last['10 Yr']),
                     'ust10date': datetime.datetime.strptime(last['Date'], '%m/%d/%Y').strftime('%b. %-d, %Y')})
print('limits', l50, lim['median2026'], 'UST', last['Date'], last['10 Yr'])

# ---- stations and amenities
meta = json.load(open(os.path.join(ROOT, 'meta.json')))
sta = [[s['name'], round(s['lon'], 5), round(s['lat'], 5), 'L'] for s in meta['stations']] + [[s['name'], round(s['lon'], 5), round(s['lat'], 5), 'M'] for s in meta['metra']]
dump('stations.json', sta)
amen = [a[:3] for a in json.load(gz('amen.json.gz'))]   # kind and point only: OSM names can be a doctor's own name
dump('amen.json', amen)
print('stations', len(sta), 'amenities', collections.Counter(a[0] for a in amen))

# ---- tracts: Housing Enhancement test inputs over the tract and its neighbors
def acs(tb):
    f = gz(f'acs_{tb}_2024.dat.gz'); head = f.readline().rstrip('\n').split('|'); out = {}
    for line in f:
        c = line.rstrip('\n').split('|'); d = dict(zip(head, c)); out[d['GEO_ID'][-11:]] = d
    return out
inc, pov, rent = acs('b19001'), acs('b17001'), acs('b25064')
MFI = int(lim['median2026'])
def above(d):
    v = lambda k: float(d.get(f'B19001_E0{k:02d}') or 0)
    tot = v(1)
    if not tot: return None, 0
    a = v(14) * (125000 - MFI) / 25000 if MFI < 125000 else 0
    return a + v(15) + v(16) + v(17), tot
tracts = json.load(gz('tracts.geojson.gz'))['features']
geo = {f['properties']['id']: make_valid(shape(f['geometry'])) for f in tracts}
ids = list(geo); tree = STRtree([geo[i] for i in ids])
T = {}
for i in ids:
    nb = [ids[j] for j in tree.query(geo[i].buffer(0.0003)) if geo[ids[j]].intersects(geo[i].buffer(0.0003))]
    A = H = P = PT = 0
    for t in nb:
        a, h = above(inc.get(t, {}))
        if a is not None: A += a; H += h
        p = pov.get(t, {}); PT += float(p.get('B17001_E001') or 0); P += float(p.get('B17001_E002') or 0)
    r = rent.get(i, {}).get('B25064_E001')
    try: r = int(float(r)) if r not in (None, '', '-666666666') and float(r) > 0 else None
    except ValueError: r = None
    T[i] = {'pma': [round(A / H, 3) if H else None, round(P / PT, 3) if PT else None], 'rent': r, 'n': len(nb)}
dump('tracts.json', {'mfi': MFI, 'src': 'ACS 2020-2024 5-year, tables B19001, B17001, B25064', 't': T})
he = sum(1 for v in T.values() if v['pma'][0] is not None and v['pma'][0] >= .5 and v['pma'][1] is not None and v['pma'][1] <= .2)
print('tracts', len(T), 'pass Housing Enhancement test', he)

# ---- QCTs, small area DDAs, TIF districts -> tiles
def qcts(name):
    s = set()
    for line in gz(f'hud/qct_{name}.txt.gz'):
        c = line.split(':', 1)[-1].strip().split(',')
        if len(c) >= 8 and c[3] == '17031': s.add(c[7])
    return s
Q26, Q27 = qcts('QCT2026CSV.zip'), qcts('QCT2027CSV.zip')
def sdda(year):
    s = set()
    for line in gz(f'hud/qct_{year}-DDAs-Data-Used-to-Designate.xlsx.txt.gz'):
        c = line.rstrip('\n').split('|')
        if len(c) > 14 and c[1].startswith('606') and c[-1].strip() in ('1', '1.0'): s.add(c[1])
    return s
D26, D27 = sdda(2026), sdda(2027)
print('QCTs 2026', len(Q26), '2027', len(Q27), 'SDDA ZIPs 2026', sorted(D26), '2027', sorted(D27))
feats = []
for i, g in geo.items():
    feats.append(('tr', i, g))
    if i in Q26: feats.append(('qct26', i, g))
    if i in Q27: feats.append(('qct27', i, g))
for f in json.load(gz('zcta.geojson.gz'))['features']:
    z = f['properties']['id']; yrs = [y for y, S in ((2026, D26), (2027, D27)) if z in S]
    if yrs: feats.append(('dda', z + ' (' + ' and '.join(map(str, yrs)) + ')', make_valid(shape(f['geometry']))))
for f in json.load(gz('pl_tif_eejr-xtfb.geojson.gz'))['features']:
    p = f['properties']
    if p.get('repealed_d'): continue
    if p.get('expiration') and p['expiration'][:10] < datetime.date.today().isoformat(): continue
    nm = (p.get('name') or '').strip() + (f" (expires {p['expiration'][:4]})" if p.get('expiration') else '')
    feats.append(('tif', nm, make_valid(shape(f['geometry']))))
TOL = {'tr': 0.00001, 'qct26': 0.00001, 'qct27': 0.00001, 'dda': 0.00002, 'tif': 0.00001}
tiles = collections.defaultdict(list)
tk = lambda lon, lat: (int(math.floor((lon + 88) * 100)), int(math.floor((lat - 41) * 100)))
for kind, nm, g in feats:
    g = g.simplify(TOL[kind], preserve_topology=True)
    x0, y0, x1, y1 = g.bounds; (a, b), (c, d) = tk(x0, y0), tk(x1, y1)
    for ix in range(a, c + 1):
        for iy in range(b, d + 1):
            tx, ty = ix / 100 - 88, iy / 100 + 41
            part = g.intersection(box(tx, ty, tx + .01, ty + .01))
            if part.is_empty: continue
            polys = [part] if isinstance(part, Polygon) else [q for q in getattr(part, 'geoms', []) if isinstance(q, Polygon)]
            rings = []
            for q in polys:
                for r in [q.exterior] + list(q.interiors):
                    pts = []
                    for x, y in list(r.coords)[:-1]: pts += [round((x - tx) * 1e6), round((y - ty) * 1e6)]
                    if len(pts) >= 6: rings.append(pts)
            if rings: tiles[(ix, iy)].append([kind, nm, rings])
gd = os.path.join(OUT, 'g')
for f in os.listdir(gd): os.remove(os.path.join(gd, f))
size = 0
have = {f[:-5] for f in os.listdir(os.path.join(ROOT, 'lot', 'data', 't'))}
for (ix, iy), L in tiles.items():
    if f'{ix}_{iy}' not in have: continue
    p = os.path.join(gd, f'{ix}_{iy}.json'); json.dump({'f': L}, open(p, 'w'), separators=(',', ':'), ensure_ascii=False); size += os.path.getsize(p)
print(len(tiles), 'tiles', round(size / 1e6, 1), 'MB')
