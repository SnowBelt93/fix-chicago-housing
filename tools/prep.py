import json, struct, sys, os, math, collections
import numpy as np
import shapefile
from pyproj import Transformer
from shapely.geometry import shape, Polygon, Point
from shapely.ops import transform as stransform, unary_union
from shapely.strtree import STRtree
from shapely import prepared

SCR = os.path.dirname(os.path.abspath(__file__))
OUT = sys.argv[1]
os.makedirs(os.path.join(OUT, 'b'), exist_ok=True)

to_sp = Transformer.from_crs('EPSG:4326', 'EPSG:3435', always_xy=True)
to_ll = Transformer.from_crs('EPSG:3435', 'EPSG:4326', always_xy=True)

# --- community areas
ca = json.load(open(os.path.join(SCR, 'dl/ca/ca.geojson')))
areas = []
for f in ca['features']:
    g_ll = shape(f['geometry'])
    g_sp = stransform(lambda x, y, z=None: to_sp.transform(x, y), g_ll)
    num = int(f['properties']['area_numbe'])
    name = f['properties']['community'].title()
    areas.append(dict(num=num, name=name, ll=g_ll, sp=g_sp))
areas.sort(key=lambda a: a['num'])
tree = STRtree([a['sp'] for a in areas])
prep = [prepared.prep(a['sp']) for a in areas]

# --- stations (keep only those inside the city)
city_sp = unary_union([a['sp'] for a in areas])
city_prep = prepared.prep(city_sp.buffer(200))
stations = []
for line in open(os.path.join(SCR, 'stations.csv')):
    sid, name, lat, lon = line.strip().split(',')
    x, y = to_sp.transform(float(lon), float(lat))
    if city_prep.contains(Point(x, y)):
        stations.append(dict(id=int(sid), name=name, lat=float(lat), lon=float(lon), x=x, y=y))
print('stations in city', len(stations))
st_xy = np.array([[s['x'], s['y']] for s in stations])

# --- Metra stations in the city (Cook County GIS via research)
metra = []
for line in open(os.path.join(SCR, 'metra.csv')):
    parts_ = line.strip().rsplit(',', 3)
    if len(parts_) != 4: continue
    name, lines_, lat, lon = parts_
    x, y = to_sp.transform(float(lon), float(lat))
    metra.append(dict(name=name, line=lines_, lat=float(lat), lon=float(lon), x=x, y=y))
mt_xy = np.array([[s['x'], s['y']] for s in metra])
print('metra', len(metra))

# --- commercial corridors from city street centerlines (class 2/3 segments of named streets)
CORR = {('ASHLAND','AVE'),('WESTERN','AVE'),('MILWAUKEE','AVE'),('HALSTED','ST'),('CLARK','ST'),('BROADWAY',None),('CICERO','AVE'),
        ('PULASKI','RD'),('COTTAGE GROVE','AVE'),('DR MARTIN LUTHER KING JR','DR'),('STONY ISLAND','AVE'),('ARCHER','AVE'),('CERMAK','RD'),
        ('26TH','ST'),('47TH','ST'),('55TH','ST'),('63RD','ST'),('71ST','ST'),('79TH','ST'),('87TH','ST'),('95TH','ST'),('103RD','ST'),('111TH','ST'),
        ('CHICAGO','AVE'),('NORTH','AVE'),('DIVISION','ST'),('GRAND','AVE'),('FULLERTON','AVE'),('BELMONT','AVE'),('IRVING PARK','RD'),
        ('LAWRENCE','AVE'),('DEVON','AVE'),('MADISON','ST'),('ROOSEVELT','RD'),('LINCOLN','AVE'),('KEDZIE','AVE'),('DAMEN','AVE'),('OGDEN','AVE')}
from shapely.geometry import LineString, MultiLineString
sc = json.load(open(os.path.join(SCR, 'dl/sc/data/Transportation.geojson')))
corr_lines_sp = []; corr_by_name = collections.defaultdict(list)
for f_ in sc['features']:
    pr = f_['properties']
    if pr.get('CLASS') not in ('2', '3'): continue
    key = (pr.get('STREET_NAM'), pr.get('STREET_TYP'))
    if key not in CORR: continue
    co = f_['geometry']['coordinates']
    if f_['geometry']['type'] != 'LineString' or len(co) < 2: continue
    xs, ys = to_sp.transform([c_[0] for c_ in co], [c_[1] for c_ in co])
    corr_lines_sp.append(LineString(list(zip(xs, ys))))
    corr_by_name[key[0]].append(co)
corr_zone = prepared.prep(unary_union(corr_lines_sp).buffer(150))   # ~ one lot deep on each side
print('corridor segments', len(corr_lines_sp))
OFFICE_AREAS = {'LOOP', 'NEAR NORTH SIDE', 'NEAR WEST SIDE', 'NEAR SOUTH SIDE'}

# --- buildings
r = shapefile.Reader(os.path.join(SCR, 'dl/bf/data/buildings'), encoding='latin-1')
fn = [f[0] for f in r.fields[1:]]
ix = {n: i for i, n in enumerate(fn)}
status = collections.Counter()
per_area = collections.defaultdict(list)
skipped = collections.Counter()
for i, sr in enumerate(r.iterShapeRecords()):
    rec = sr.record
    st = rec[ix['BLDG_STATU']]
    status[st] += 1
    if st not in ('ACTIVE',):
        skipped['status'] += 1; continue
    shp = sr.shape
    if not shp.points: skipped['nogeom'] += 1; continue
    parts = list(shp.parts) + [len(shp.points)]
    ring = shp.points[parts[0]:parts[1]]
    if len(ring) < 4: skipped['short'] += 1; continue
    try:
        poly = Polygon(ring)
    except Exception:
        skipped['bad'] += 1; continue
    if not poly.is_valid:
        poly = poly.buffer(0)
        if poly.geom_type != 'Polygon':
            if poly.geom_type == 'MultiPolygon': poly = max(poly.geoms, key=lambda p: p.area)
            else: skipped['bad'] += 1; continue
    area = poly.area
    stories = rec[ix['STORIES']] or rec[ix['NO_STORIES']] or 0
    try: stories = int(stories)
    except: stories = 0
    units = rec[ix['NO_OF_UNIT']] or 0
    try: units = int(units)
    except: units = 0
    yb = rec[ix['YEAR_BUILT']] or 0
    try: yb = int(yb)
    except: yb = 0
    # drop garages/sheds: tiny, one story, no homes
    if area < 250: skipped['tiny'] += 1; continue
    if units == 0 and stories <= 1 and area < 900: skipped['garage'] += 1; continue
    c = poly.centroid
    cand = tree.query(c)
    ai = None
    for k in cand:
        if prep[k].contains(c): ai = int(k); break
    if ai is None: skipped['outside'] += 1; continue
    # simplify geometry
    if area < 4000:
        g = poly.minimum_rotated_rectangle
    else:
        g = poly.simplify(2.0, preserve_topology=True)
        tol = 2.0
        while len(g.exterior.coords) > 41:
            tol *= 2; g = poly.simplify(tol, preserve_topology=True)
        if g.geom_type != 'Polygon' or g.is_empty: g = poly.minimum_rotated_rectangle
    if g.geom_type != 'Polygon' or g.is_empty: skipped['simp'] += 1; continue
    from shapely.geometry.polygon import orient
    g = orient(g, 1.0)  # CCW
    pts = list(g.exterior.coords)[:-1]
    d = np.min(np.hypot(st_xy[:, 0] - c.x, st_xy[:, 1] - c.y))
    tod = 2 if d <= 1320 else (1 if d <= 2640 else 0)
    if np.min(np.hypot(mt_xy[:, 0] - c.x, mt_xy[:, 1] - c.y)) <= 2640: tod |= 4      # within 1/2 mile of Metra
    if corr_zone.contains(c): tod |= 16                                                # on a commercial corridor
    if areas[ai]['name'].upper() in OFFICE_AREAS and units == 0 and stories >= 8 and (yb == 0 or yb < 1990): tod |= 32  # older downtown office/commercial tower
    # 128 = small commercial lot that could become housing: no homes, a real street address, not a named
    # landmark/institution or monument, and on a commercial corridor or within 1/4 mile of the L.
    # (Keeps park field houses, museums and Grant Park structures out of the redevelopment pool.)
    try: addr = int(rec[ix['F_ADD1']] or 0)
    except: addr = 0
    nm = str(rec[ix['BLDG_NAME1']] or '').strip(); ns = str(rec[ix['NON_STANDA']] or '').strip()
    if units == 0 and addr > 0 and rec[ix['ST_NAME1']] and not nm and not ns and ((tod & 16) or (tod & 3) == 2): tod |= 128
    per_area[ai].append((pts, min(max(stories, 0), 255), units, yb, area, tod))

print('status', status.most_common(8))
print('skipped', dict(skipped))

meta = []
tot = 0; totv = 0
city_new = 0; city_n = 0
for ai, a in enumerate(areas):
    bl = per_area.get(ai, [])
    # origin = area centroid in lon/lat
    lon0, lat0 = a['ll'].centroid.x, a['ll'].centroid.y
    allpts = np.array([p for b in bl for p in b[0]], dtype=np.float64)
    lons, lats = to_ll.transform(allpts[:, 0], allpts[:, 1])
    kx = 111319.49 * math.cos(math.radians(lat0)); ky = 111319.49   # deck.gl METER_OFFSETS scale (Web Mercator sphere)
    mx = (np.array(lons) - lon0) * kx; my = (np.array(lats) - lat0) * ky
    q = np.round(np.stack([mx, my], 1) * 2).astype(np.int64)  # 0.5 m units
    assert q.min() > -32767 and q.max() < 32767, (a['name'], q.min(), q.max())
    N = len(bl); V = len(allpts)
    nv = np.array([len(b[0]) for b in bl], dtype=np.uint8)
    stories = np.array([b[1] for b in bl], dtype=np.uint8)
    units = np.array([min(b[2], 65535) for b in bl], dtype=np.uint16)
    fp = np.array([min(int(b[4] / 2), 65535) for b in bl], dtype=np.uint16)
    flags = np.zeros(N, dtype=np.uint8)
    for k, b in enumerate(bl):
        f = b[5]
        if b[3] >= 2000: f |= 8
        flags[k] = f
    with open(os.path.join(OUT, 'b', f'{a["num"]}.bin'), 'wb') as fh:
        fh.write(struct.pack('<IIdd', N, V, lon0, lat0))
        fh.write(q.astype('<i2').tobytes())
        fh.write(nv.tobytes()); fh.write(stories.tobytes()); fh.write(flags.tobytes())
        if (N * 3) % 2: fh.write(b'\0')
        fh.write(units.astype('<u2').tobytes()); fh.write(fp.astype('<u2').tobytes())
    yrs = [b[3] for b in bl if b[3] > 1800]
    new = sum(1 for y in yrs if y >= 1990)
    city_new += new; city_n += len(yrs)
    tall = sum(1 for b in bl if b[1] >= 4)
    meta.append(dict(num=a['num'], name=a['name'], lon=round(lon0, 5), lat=round(lat0, 5), n=N,
                     homes=int(units.sum()), newShare=(new / len(yrs)) if yrs else 0,
                     bytes=os.path.getsize(os.path.join(OUT, 'b', f'{a["num"]}.bin'))))
    tot += N; totv += V
cityShare = city_new / city_n
for m in meta:
    m['demand'] = round(min(2.5, max(0.3, m['newShare'] / cityShare)), 2)
    m['newShare'] = round(m['newShare'], 4)
print('buildings', tot, 'verts', totv, 'city new share', cityShare, 'homes', sum(m['homes'] for m in meta))

# outlines (lon/lat, simplified) for map + picking
feats = []
for a in areas:
    g = a['ll'].simplify(0.0002)
    feats.append(dict(type='Feature', properties=dict(num=a['num'], name=a['name']),
                      geometry=json.loads(json.dumps(g.__geo_interface__))))
def rnd(o):
    if isinstance(o, float): return round(o, 5)
    if isinstance(o, (list, tuple)): return [rnd(x) for x in o]
    if isinstance(o, dict): return {k: rnd(v) for k, v in o.items()}
    return o
from shapely.ops import linemerge
corr_out = []
for nm, segs in sorted(corr_by_name.items()):
    ml = linemerge(MultiLineString([LineString(s_) for s_ in segs]))
    geoms = list(ml.geoms) if ml.geom_type == 'MultiLineString' else [ml]
    paths = [[list(p_) for p_ in g_.simplify(0.0002).coords] for g_ in geoms if g_.length > 0.001]
    corr_out.append(dict(name=nm.title().replace('Dr Martin Luther King Jr', 'King Dr'), paths=paths))
json.dump(dict(areas=meta, stations=[dict(name=s['name'], lat=s['lat'], lon=s['lon']) for s in stations],
               metra=[dict(name=s['name'], line=s['line'], lat=s['lat'], lon=s['lon']) for s in metra],
               corridors=rnd(corr_out),
               outlines=rnd(dict(type='FeatureCollection', features=feats))),
          open(os.path.join(OUT, 'meta.json'), 'w'), separators=(',', ':'))
print('meta bytes', os.path.getsize(os.path.join(OUT, 'meta.json')))
