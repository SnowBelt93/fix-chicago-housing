"""Builds the extra data layers from the open datasets in tools/raw/ (fetched by .github/workflows/fetch-data.yml).

Outputs (run from the repo root: python3 tools/prep_extra.py):
  b/extra.wasm   per-building byte, areas in meta.json order: ward number (bits 0-5, 0 = none)
                 | 128 if the building is within 1/4 mile of one of the busiest L stations (tower-eligible).
                 Layout: uint32 area count, then per area: uint32 num, uint32 N, N bytes.
  b/vacant.wasm  vacant parcels: uint32 nPrivate, uint32 nCity, then int32 (lon*1e6, lat*1e6) pairs, private first.
  wards.json     simplified 2023 ward outlines for the map.
  meta.json      adds "busy" (stations used for the Tower level), "vacantByArea" {num: [private, city]}, per-area "sf" and "type",
                 and "wardStats" {ward: [buildings, illegalToday]}.
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

M_LAT = 111132.954
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
    m_lon = M_LAT * np.cos(np.radians(lat0))
    return N, lon0 + cx / m_lon, lat0 + cy / M_LAT, fl

out = bytearray(struct.pack('<I', len(meta['areas'])))
ward_b = collections.Counter(); ward_ill = collections.Counter()
bl = np.array([[b['lon'], b['lat']] for b in busy])
tower_n = 0
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
    for i in range(N):
        wd = w[i] & 63
        if wd:
            ward_b[int(wd)] += 1
            if fl[i] & 64: ward_ill[int(wd)] += 1
    out += struct.pack('<II', a['num'], N) + w.tobytes()
open(os.path.join(ROOT, 'b', 'extra.wasm'), 'wb').write(out)
print('extra.wasm', len(out), 'bytes; tower-eligible buildings', tower_n, '; buildings with a ward', sum(ward_b.values()))

# ---- vacant parcels: privately owned (Cook County class 100, 2025) and city-owned (still owned by the city)
CHI = {'Hyde Park', 'Jefferson', 'Lake', 'Lake View', 'North Chicago', 'Rogers Park', 'South Chicago', 'West Chicago'}
priv = [(float(r['lon']), float(r['lat'])) for r in csv.DictReader(open(os.path.join(RAW, 'cook_vacant_2025.csv')))
        if r['township_name'] in CHI and r['lat'] and r['lon']]
city = [(float(r['longitude']), float(r['latitude'])) for r in csv.DictReader(open(os.path.join(RAW, 'city_owned_land.csv')))
        if r['property_status'] == 'Owned by City' and r.get('latitude') and r.get('longitude')]
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
