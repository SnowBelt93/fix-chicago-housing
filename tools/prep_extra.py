"""Builds the extra data layers from the open datasets in tools/raw/ (fetched by .github/workflows/fetch-data.yml).

Outputs (run from the repo root: python3 tools/prep_extra.py):
  b/extra.wasm   per-building byte, areas in meta.json order: ward number (bits 0-5, 0 = none)
                 | 64 if the building is gone: the footprints are from 2013, and either a parcel that is vacant today
                   (Cook County class 100 in 2025, or city-owned land) sits inside it (small buildings only, not built 2000+),
                   or Cook County's 2022 footprints show it torn down or replaced (tools/raw/fresh_gone.json from prep_fresh.py)
                 | 128 if the building is within 1/4 mile of one of the busiest L stations (tower-eligible).
                 Layout: uint32 area count, then per area: uint32 num, uint32 N, N bytes.
  b/vacant.wasm  vacant parcels: uint32 nPrivate, uint32 nCity, then int32 (lon*1e6, lat*1e6) pairs, private first.
  b/land.wasm    land that's empty today, per area (areas in meta.json order): uint32 num, uint32 N, uint8 open[N]
                 (1 = this building is gone and nothing stands on its lot: vacant parcel or empty in the 2022 footprints),
                 pad to 4 bytes, uint32 k, then k privately owned vacant parcels (Cook County class 100, 2025) that aren't
                 under any building footprint: int16 x, int16 y (0.5 m units east/north of the area file's origin, deck scale),
                 uint8 flags (same bits as buildings: 1-2 L distance, 4 Metra, 16 corridor; 128 = within 1/4 mi of a busy L station),
                 uint8 ward; then pad to 4 bytes.
  wards.json     simplified 2023 ward outlines for the map.
  meta.json      adds "busy" (stations used for the Tower level), "vacantByArea" {num: [private, city]}, per-area "sf", "type"
                 and "gone" [buildings, homes] (on lots that are vacant today), and "wardStats" {ward: [buildings, illegalToday]}.
Building order is untouched (it is the random seed)."""
import json, struct, csv, os, collections
import numpy as np
import shapely
from shapely.geometry import shape, mapping
from shapely.strtree import STRtree

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, 'tools', 'raw')
meta = json.load(open(os.path.join(ROOT, 'meta.json')))

# ---- busiest L stations: 2025 average weekday entries (CTA), airports left out, threshold 4,000
coords = {}
for row in csv.reader(open(os.path.join(ROOT, 'tools', 'stations.csv'))):
    coords[row[0]] = (row[1], float(row[2]), float(row[3]))
rides = collections.defaultdict(list)
for r in csv.DictReader(open(os.path.join(RAW, 'cta_l_daily_2025.csv'))):
    if r['daytype'] == 'W': rides[r['station_id']].append(int(r['rides']))
busy = []
for sid, v in rides.items():
    avg = sum(v) / len(v)
    if sid in coords and avg >= 4000 and sid not in ('40890', '40930'):   # O'Hare and Midway airports
        name, lat, lon = coords[sid]
        busy.append({'name': name, 'lat': lat, 'lon': lon, 'rides': round(avg)})
busy.sort(key=lambda b: -b['rides'])
print(len(busy), 'busy stations:', ', '.join(b['name'] for b in busy))

# ---- wards
wf = json.load(open(os.path.join(RAW, 'wards2023.geojson')))['features']
wards = [(int(f['properties']['ward']), shape(f['geometry'])) for f in wf]
wtree = STRtree([g for _, g in wards])

# ---- parcels that are vacant today: privately owned (Cook County class 100, 2025) and city-owned (still owned by the city)
CHI = {'Hyde Park', 'Jefferson', 'Lake', 'Lake View', 'North Chicago', 'Rogers Park', 'South Chicago', 'West Chicago'}
priv = [(float(r['lon']), float(r['lat'])) for r in csv.DictReader(open(os.path.join(RAW, 'cook_vacant_2025.csv')))
        if r['township_name'] in CHI and r['lat'] and r['lon']]
city = [(float(r['longitude']), float(r['latitude'])) for r in csv.DictReader(open(os.path.join(RAW, 'city_owned_land.csv')))
        if r['property_status'] == 'Owned by City' and r.get('latitude') and r.get('longitude')]
vac_all = np.array(priv + city)
FRESH = os.path.join(RAW, 'fresh_gone.json')
fresh_gone = json.load(open(FRESH)) if os.path.exists(FRESH) else {}
FOPEN = os.path.join(RAW, 'fresh_open.json')
fresh_open = json.load(open(FOPEN)) if os.path.exists(FOPEN) else {}

M_LAT = 111132.954          # real metres per degree of latitude here, for distances
DECK = 111319.49            # the scale the building files are stored in (deck.gl METER_OFFSETS)
def gone_in(num):
    """Indices of small pre-2000 buildings that contain a parcel point that is vacant today (demolished since the 2013 footprints)."""
    buf = open(os.path.join(ROOT, 'b', f'{num}.wasm'), 'rb').read()
    N, V = struct.unpack_from('<II', buf, 0)
    lon0, lat0 = struct.unpack_from('<dd', buf, 8)
    q = np.frombuffer(buf, dtype='<i2', count=2 * V, offset=24).astype(np.float64) * 0.5
    o = 24 + 4 * V
    nv = np.frombuffer(buf, dtype=np.uint8, count=N, offset=o).astype(np.int64)
    fl = np.frombuffer(buf, dtype=np.uint8, count=N, offset=o + 2 * N)
    po = o + 3 * N + ((3 * N) % 2)
    un = np.frombuffer(buf, dtype='<u2', count=N, offset=po)
    fp = np.frombuffer(buf, dtype='<u2', count=N, offset=po + 2 * N).astype(np.float64) * 2
    px = (vac_all[:, 0] - lon0) * DECK * np.cos(np.radians(lat0)); py = (vac_all[:, 1] - lat0) * DECK
    sel = (np.abs(px) < 20000) & (np.abs(py) < 20000)
    polys, s0 = [], 0
    for i in range(N):
        n = nv[i]; c = q[2 * s0:2 * (s0 + n)].reshape(-1, 2); s0 += n
        polys.append(shapely.Polygon(c) if n >= 3 else shapely.Polygon())
    tree = STRtree(polys)
    ip, ib = tree.query(shapely.points(px[sel], py[sel]), predicate='within')
    g = sorted(set(int(b) for b in ib if fp[b] < 6000 and not (fl[b] & 8)))
    covered = set(np.where(sel)[0][ip].tolist())   # parcel points that sit under some footprint
    return g, int(un[g].sum()) if g else 0, covered

def city_owned_in(num):
    """Buildings whose lot holds a city-owned parcel point (that land is the city's to sell, not open to private building)."""
    buf = open(os.path.join(ROOT, 'b', f'{num}.wasm'), 'rb').read()
    N, V = struct.unpack_from('<II', buf, 0); lon0, lat0 = struct.unpack_from('<dd', buf, 8)
    q = np.frombuffer(buf, dtype='<i2', count=2 * V, offset=24).astype(np.float64) * 0.5
    nv = np.frombuffer(buf, dtype=np.uint8, count=N, offset=24 + 4 * V).astype(np.int64)
    cp = np.array(city) if city else np.zeros((0, 2))
    px = (cp[:, 0] - lon0) * DECK * np.cos(np.radians(lat0)); py = (cp[:, 1] - lat0) * DECK
    sel = (np.abs(px) < 20000) & (np.abs(py) < 20000)
    polys, s0 = [], 0
    for i in range(N):
        n = nv[i]; c = q[2 * s0:2 * (s0 + n)].reshape(-1, 2); s0 += n
        polys.append(shapely.Polygon(c) if n >= 3 else shapely.Polygon())
    _, ib = STRtree(polys).query(shapely.points(px[sel], py[sel]), predicate='within')
    return set(int(b) for b in ib)

def units_of(num):
    buf = open(os.path.join(ROOT, 'b', f'{num}.wasm'), 'rb').read()
    N, V = struct.unpack_from('<II', buf, 0); o = 24 + 4 * V
    return np.frombuffer(buf, dtype='<u2', count=N, offset=o + 3 * N + ((3 * N) % 2))

def to_ll(num):
    buf = open(os.path.join(ROOT, 'b', f'{num}.wasm'), 'rb').read()
    N, V = struct.unpack_from('<II', buf, 0)
    lon0, lat0 = struct.unpack_from('<dd', buf, 8)
    q = np.frombuffer(buf, dtype='<i2', count=2 * V, offset=24).astype(np.float64) * 0.5
    o = 24 + 4 * V
    nv = np.frombuffer(buf, dtype=np.uint8, count=N, offset=o).astype(np.int64)
    st = np.frombuffer(buf, dtype=np.uint8, count=N, offset=o + N)
    fl = np.frombuffer(buf, dtype=np.uint8, count=N, offset=o + 2 * N)
    starts = np.concatenate([[0], np.cumsum(nv)])[:-1]
    xs, ys = q[0::2], q[1::2]
    safe = np.maximum(nv, 1)
    cx = np.add.reduceat(xs, starts) / safe if N else xs
    cy = np.add.reduceat(ys, starts) / safe if N else ys
    return N, lon0 + cx / (DECK * np.cos(np.radians(lat0))), lat0 + cy / DECK, fl

out = bytearray(struct.pack('<I', len(meta['areas'])))
ward_b = collections.Counter(); ward_ill = collections.Counter()
bl = np.array([[b['lon'], b['lat']] for b in busy])
tower_n = 0; gone_n = 0; gone_u = 0; covered_all = set(); open_lots = {}
for a in meta['areas']:
    N, lon, lat, fl = to_ll(a['num'])
    pts = shapely.points(lon, lat)
    w = np.zeros(N, dtype=np.uint8)
    idx_pt, idx_poly = wtree.query(pts, predicate='within')
    for i, j in zip(idx_pt, idx_poly): w[i] = wards[j][0]
    # tower eligibility: within 402 m (1/4 mile) of a busy station
    dx = (lon[:, None] - bl[None, :, 0]) * M_LAT * np.cos(np.radians(41.88))
    dy = (lat[:, None] - bl[None, :, 1]) * M_LAT
    near = (np.sqrt(dx * dx + dy * dy) <= 402).any(axis=1)
    tower_n += int(near.sum())
    w = w | (near.astype(np.uint8) << 7)
    g, gu, cov = gone_in(a['num'])
    covered_all |= cov
    open_lots[a['num']] = sorted((set(g) | set(fresh_open.get(str(a['num']), []))) - city_owned_in(a['num']))   # nothing stands here today (city-owned lots stay with the city-lots policy)
    g = sorted(set(g) | set(fresh_gone.get(str(a['num']), [])))
    gu = int(sum(units_of(a['num'])[g])) if g else 0
    w[g] |= 64
    a['gone'] = [len(g), gu]; gone_n += len(g); gone_u += gu
    for i in range(N):
        wd = w[i] & 63
        if wd and not (w[i] & 64):
            ward_b[int(wd)] += 1
            if fl[i] & 64: ward_ill[int(wd)] += 1
    out += struct.pack('<II', a['num'], N) + w.tobytes()
open(os.path.join(ROOT, 'b', 'extra.wasm'), 'wb').write(out)
print('extra.wasm', len(out), 'bytes; tower-eligible buildings', tower_n, '; buildings with a ward', sum(ward_b.values()), '; gone (lot vacant today)', gone_n, 'buildings,', gone_u, 'homes')

# ---- vacant parcels (loaded above), counted per community area
cas = [(f['properties']['num'], shape(f['geometry'])) for f in meta['outlines']['features']]
ctree = STRtree([g for _, g in cas])
def by_area(pts):
    P = shapely.points(np.array(pts))
    ip, ia = ctree.query(P, predicate='within')
    keep = sorted(set(ip.tolist()))
    cnt = collections.Counter(cas[j][0] for j in ia)
    return [pts[i] for i in keep], cnt
priv, cp = by_area(priv)
city, cc = by_area(city)
vb = bytearray(struct.pack('<II', len(priv), len(city)))
for lo, la in priv + city: vb += struct.pack('<ii', round(lo * 1e6), round(la * 1e6))
open(os.path.join(ROOT, 'b', 'vacant.wasm'), 'wb').write(vb)
print('vacant parcels in the city: private', len(priv), 'city-owned', len(city))

# ---- land that's empty today: open lots of gone buildings, and private vacant parcels not under any footprint
from shapely.ops import unary_union
TO_FT = 3.28084
def local(lon, lat, lon0, lat0):
    return (lon - lon0) * DECK * np.cos(np.radians(lat0)), (lat - lat0) * DECK
stations = np.array([[s_['lon'], s_['lat']] for s_ in meta['stations']]); metra = np.array([[s_['lon'], s_['lat']] for s_ in meta['metra']])
def dist_m(pts, ref):
    dx = (pts[:, None, 0] - ref[None, :, 0]) * M_LAT * np.cos(np.radians(41.84)); dy = (pts[:, None, 1] - ref[None, :, 1]) * M_LAT
    return np.sqrt(dx * dx + dy * dy).min(axis=1)
corr_lines = []
for c in meta['corridors']:
    for path in c['paths']:
        xy = [((lo + 87.68) * M_LAT * np.cos(np.radians(41.84)), (la - 41.84) * M_LAT) for lo, la in path]
        if len(xy) >= 2: corr_lines.append(shapely.LineString(xy))
corr_zone = unary_union(corr_lines).buffer(150 / TO_FT)
# the first len(priv_raw) entries of vac_all are the private parcels (same filter, same order)
n_priv_raw = len([1 for r in csv.DictReader(open(os.path.join(RAW, 'cook_vacant_2025.csv'))) if r['township_name'] in CHI and r['lat'] and r['lon']])
keep = np.array([i not in covered_all for i in range(n_priv_raw)])
# drop parcel points that sit in a street (right-of-way remnants and slivers): within a street's half-width of its centreline
# (b/streets.wasm, 2 m units; half-widths 20 m expressway, 13 arterial, 11 collector, 10 local; a 25x125 ft lot's centre is 14+ m away)
sb = open(os.path.join(ROOT, 'b', 'streets.wasm'), 'rb').read()
sP, sV = struct.unpack_from('<II', sb, 0); slon0, slat0 = struct.unpack_from('<dd', sb, 8)
scls = np.frombuffer(sb, dtype=np.uint8, count=sP, offset=24); so = 24 + sP; so += (-so) % 4
sst = np.frombuffer(sb, dtype=np.uint32, count=sP + 1, offset=so); so += 4 * (sP + 1)
sxy = np.frombuffer(sb, dtype=np.int16, count=2 * sV, offset=so).reshape(-1, 2).astype(np.float64) * 2
HALF_W = {1: 20, 2: 13, 3: 11, 4: 10}
s_lines = [shapely.LineString(sxy[sst[i]:sst[i + 1]]) for i in range(sP) if sst[i + 1] - sst[i] >= 2]
s_half = np.array([HALF_W.get(int(scls[i]), 10) for i in range(sP) if sst[i + 1] - sst[i] >= 2], dtype=np.float64)
s_tree = shapely.STRtree(s_lines)
cand = vac_all[:n_priv_raw]
sx = (cand[:, 0] - slon0) * DECK * np.cos(np.radians(slat0)); sy = (cand[:, 1] - slat0) * DECK
SP = shapely.points(np.column_stack([sx, sy]))
qi, qj = s_tree.query(SP, predicate='dwithin', distance=20)
in_street = np.zeros(n_priv_raw, dtype=bool)
if len(qi):
    d = shapely.distance(SP[qi], np.array(s_lines, dtype=object)[qj])
    hit = d < s_half[qj] - 1
    in_street[qi[hit]] = True
print('vacant parcel points inside a street right-of-way (dropped):', int((keep & in_street).sum()))
keep &= ~in_street
pp = vac_all[:n_priv_raw][keep]
P = shapely.points(pp)
ip, ia = ctree.query(P, predicate='within')
area_of = {}
for i, j in zip(ip.tolist(), ia.tolist()): area_of.setdefault(cas[j][0], []).append(i)
dl = dist_m(pp, stations); dm = dist_m(pp, metra); db = dist_m(pp, bl)
cx = (pp[:, 0] + 87.68) * M_LAT * np.cos(np.radians(41.84)); cy = (pp[:, 1] - 41.84) * M_LAT
on_corr = shapely.contains_xy(corr_zone, cx, cy)
pf = ((dl <= 402) * 2 + ((dl > 402) & (dl <= 805)) * 1 + (dm <= 805) * 4 + on_corr * 16 + (db <= 402) * 128).astype(np.uint8)
wi, wj = wtree.query(P, predicate='within'); pw = np.zeros(len(pp), dtype=np.uint8); pw[wi] = [wards[j][0] for j in wj]
lb = bytearray(struct.pack('<I', len(meta['areas']))); n_open = 0; n_parc = 0
for a in meta['areas']:
    num = a['num']; buf = open(os.path.join(ROOT, 'b', f'{num}.wasm'), 'rb').read()
    N = struct.unpack_from('<I', buf, 0)[0]; lon0, lat0 = struct.unpack_from('<dd', buf, 8)
    op = np.zeros(N, dtype=np.uint8); op[open_lots.get(num, [])] = 1; n_open += int(op.sum())
    lb += struct.pack('<II', num, N) + op.tobytes(); lb += b'\0' * ((-len(lb)) % 4)
    idx = area_of.get(num, []); k = len(idx); n_parc += k
    x, y = local(pp[idx, 0], pp[idx, 1], lon0, lat0) if k else (np.array([]), np.array([]))
    lb += struct.pack('<I', k)
    for t_ in range(k):
        lb += struct.pack('<hhBB', int(round(x[t_] * 2)), int(round(y[t_] * 2)), int(pf[idx[t_]]), int(pw[idx[t_]]))
    lb += b'\0' * ((-len(lb)) % 4)
    a['open'] = [int(op.sum()), k]
open(os.path.join(ROOT, 'b', 'land.wasm'), 'wb').write(lb)
print('land.wasm', len(lb), 'bytes; open lots of gone buildings', n_open, '; private vacant parcels not under a footprint', n_parc, 'of', n_priv_raw)

# ---- simplified ward outlines
wj = []
for wd, g in sorted(wards, key=lambda t: t[0]):
    s = g.simplify(0.00008, preserve_topology=True)
    geo = mapping(s)
    polys = geo['coordinates'] if geo['type'] == 'MultiPolygon' else [geo['coordinates']]
    wj.append({'ward': wd, 'polys': [[[[round(x, 5), round(y, 5)] for x, y in ring] for ring in poly] for poly in polys],
               'lon': round(g.representative_point().x, 5), 'lat': round(g.representative_point().y, 5)})
json.dump(wj, open(os.path.join(ROOT, 'wards.json'), 'w'), separators=(',', ':'))
print('wards.json', os.path.getsize(os.path.join(ROOT, 'wards.json')), 'bytes')

# ---- neighborhood types: 0 downtown core, 1 mixed (2-flats, 3-flats, main streets), 2 single-family (70%+ of residential buildings hold one home)
CORE = {8, 28, 32, 33}
for a in meta['areas']:
    buf = open(os.path.join(ROOT, 'b', f"{a['num']}.wasm"), 'rb').read()
    N, V = struct.unpack_from('<II', buf, 0); o = 24 + 4 * V
    un = np.frombuffer(buf, dtype='<u2', count=N, offset=o + 3 * N + ((3 * N) % 2))
    res = int((un >= 1).sum()); sf = int((un == 1).sum()) / max(1, res)
    a['sf'] = round(sf, 3)
    a['type'] = 0 if a['num'] in CORE else (2 if sf >= 0.7 else 1)
print('types:', collections.Counter(a['type'] for a in meta['areas']))

meta['busy'] = busy
meta['vacantByArea'] = {str(a['num']): [cp.get(a['num'], 0), cc.get(a['num'], 0)] for a in meta['areas']}
meta['wardStats'] = {str(w): [ward_b[w], ward_ill[w]] for w in range(1, 51)}
json.dump(meta, open(os.path.join(ROOT, 'meta.json'), 'w'), separators=(',', ':'))
print('meta.json updated')
