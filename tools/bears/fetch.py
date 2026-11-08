#!/usr/bin/env python3
"""Downloads for "Where Should the Bears Play?" (Shape Chicago). Runs in GitHub Actions (the cloud workspace can't reach these hosts).

Writes tools/raw/bears/:
  land.json.gz      OpenStreetMap areas in the region: land that could take a stadium (industrial, brownfield, rail yards,
                    commercial/retail, big parking, racetracks, greenfield) and land that can't (homes, parks, water,
                    cemeteries, schools, hospitals). [[kind, tag, name, ring(s) as [[lon,lat]...]], ...]
  places.json.gz    hotels (with rooms when tagged), parking lots (capacity when tagged, else area), expressway exits,
                    stadiums and arenas: [[kind, name, lon, lat, extra], ...]
  refs.json.gz      four recent NFL stadium districts (stadium, parking, rail stations within ~1.4 km), for "at real scale"
  in_blocks.csv.gz  2020 Census blocks for Lake and Porter counties, Indiana: geoid, lat, lon, people, homes, land_m2, jobs
                    (Illinois blocks already come from tools/raw/transit/blocks.csv.gz)
Run: python3 tools/bears/fetch.py [land places refs blocks]
"""
import csv, datetime as dt, gzip, io, json, os, sys, time, urllib.parse, urllib.request, zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(ROOT, 'tools', 'raw', 'bears')
os.makedirs(OUT, exist_ok=True)
UA = {'User-Agent': 'ShapeChicago-data/1.0 (civic tool; github.com/SnowBelt93)'}
BBOX = '41.40,-88.35,42.25,-86.95'   # s,w,n,e: Chicago, the collar counties' inner ring, NW Indiana to Gary/Portage
HOSTS = ('https://overpass-api.de/api/interpreter', 'https://overpass.private.coffee/api/interpreter',
         'https://maps.mail.ru/osm/tools/overpass/api/interpreter')
LOG = []


def log(*a):
    s = ' '.join(str(x) for x in a); LOG.append(s); print(s, file=sys.stderr)


def get(url, tries=3):
    for i in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=600) as r:
                return r.read()
        except Exception as e:
            log('retry', url, repr(e)); time.sleep(5 * (i + 1))
    raise RuntimeError('failed ' + url)


def overpass(q):
    for host in HOSTS:
        for attempt in range(2):
            try:
                req = urllib.request.Request(host, data=urllib.parse.urlencode({'data': q}).encode(), headers=UA)
                with urllib.request.urlopen(req, timeout=900) as r:
                    d = json.load(r)
                log('overpass ok', host, len(d.get('elements', [])), 'elements'); return d
            except Exception as e:
                log('overpass failed', host, repr(e)); time.sleep(20)
    return None


def ring(g):
    return [[round(p['lon'], 6), round(p['lat'], 6)] for p in g]


def areas(d, classify):
    """ways and multipolygon relations with 'out geom' -> rows"""
    rows = []
    for el in (d or {}).get('elements', []):
        t = el.get('tags', {})
        k = classify(t)
        if not k:
            continue
        if el['type'] == 'way' and el.get('geometry') and len(el['geometry']) >= 4:
            rows.append([k[0], k[1], t.get('name', ''), [ring(el['geometry'])]])
        elif el['type'] == 'relation':
            outer = [ring(m['geometry']) for m in el.get('members', []) if m.get('role') == 'outer' and m.get('geometry')]
            inner = [ring(m['geometry']) for m in el.get('members', []) if m.get('role') == 'inner' and m.get('geometry')]
            if outer:
                rows.append([k[0], k[1], t.get('name', ''), outer, inner])
    return rows


GOOD = {('landuse', 'industrial'), ('landuse', 'brownfield'), ('landuse', 'railway'), ('landuse', 'commercial'),
        ('landuse', 'retail'), ('landuse', 'greenfield'), ('landuse', 'construction'), ('landuse', 'port'),
        ('landuse', 'landfill'), ('landuse', 'quarry'), ('landuse', 'farmland'), ('leisure', 'track'), ('leisure', 'stadium'),
        ('amenity', 'parking'), ('landuse', 'garages')}
BAD = {('landuse', 'residential'), ('leisure', 'park'), ('leisure', 'nature_reserve'), ('landuse', 'cemetery'),
       ('amenity', 'grave_yard'), ('natural', 'water'), ('natural', 'wetland'), ('landuse', 'forest'), ('natural', 'wood'),
       ('amenity', 'school'), ('amenity', 'university'), ('amenity', 'college'), ('amenity', 'hospital'),
       ('leisure', 'golf_course'), ('aeroway', 'aerodrome'), ('landuse', 'military'), ('boundary', 'protected_area')}


def classify(t):
    for k, v in t.items():
        if (k, v) in BAD:
            return ('no', f'{k}={v}')
    for k, v in t.items():
        if (k, v) in GOOD:
            return ('ok', f'{k}={v}')
    return None


def land(max_tiles=99):
    """In tiles, so no single Overpass query runs long; tiles already saved by an earlier run are kept."""
    s_, w_, n_, e_ = (float(v) for v in BBOX.split(','))
    NT = 4
    path = os.path.join(OUT, 'land_tiles.json.gz')
    done = json.load(gzip.open(path, 'rt')) if os.path.exists(path) else {}
    good = sorted(k for k in GOOD if k[0] != 'amenity')
    order = sorted(((i, j) for i in range(NT) for j in range(NT)), key=lambda t: abs(t[0] - 2) + abs(t[1] - 2))   # the city first
    for i, j in order:
        if True:
            key = f'{i}_{j}'
            if key in done:
                continue
            bb = f'{s_ + (n_ - s_) * i / NT:.4f},{w_ + (e_ - w_) * j / NT:.4f},{s_ + (n_ - s_) * (i + 1) / NT:.4f},{w_ + (e_ - w_) * (j + 1) / NT:.4f}'
            part = ''.join(f'way["{k}"="{v}"]({bb});relation["{k}"="{v}"]({bb});' for k, v in good + sorted(BAD))
            part += f'way["amenity"="parking"]["parking"!="street_side"]["parking"!="lane"]({bb});relation["amenity"="parking"]({bb});'
            if max_tiles <= 0:
                break
            max_tiles -= 1
            d = overpass(f'[out:json][timeout:400][maxsize:1073741824];({part});out geom;')
            if d is None:
                log('land tile failed', key); continue
            done[key] = areas(d, classify); log('land tile', key, len(done[key]))
            json.dump(done, gzip.open(path, 'wt'), separators=(',', ':'))
            time.sleep(5)
    rows, seen = [], set()
    for k, rs in done.items():
        for r in rs:
            sig = (r[1], r[2], round(r[3][0][0][0], 5), round(r[3][0][0][1], 5), len(r[3][0]))
            if sig in seen:
                continue
            seen.add(sig); rows.append(r)
    log('land rows', len(rows), 'tiles', len(done), 'of', NT * NT)
    json.dump(rows, gzip.open(os.path.join(OUT, 'land.json.gz'), 'wt'), separators=(',', ':'))


def places():
    q = (f'[out:json][timeout:600];('
         f'nwr["tourism"~"^(hotel|motel)$"]({BBOX});'
         f'way["amenity"="parking"]({BBOX});relation["amenity"="parking"]({BBOX});'
         f'node["highway"="motorway_junction"]({BBOX});'
         f'nwr["leisure"="stadium"]({BBOX});nwr["amenity"="events_venue"]["building"]({BBOX});'
         f');out center tags;')
    d = overpass(q); out = []
    for el in (d or {}).get('elements', []):
        t = el.get('tags', {}); c = el.get('center') or ({'lat': el.get('lat'), 'lon': el.get('lon')} if 'lat' in el else None)
        if not c:
            continue
        lon, lat = round(c['lon'], 6), round(c['lat'], 6)
        if t.get('tourism') in ('hotel', 'motel'):
            out.append(['hotel', t.get('name', ''), lon, lat, t.get('rooms', '')])
        elif t.get('amenity') == 'parking':
            out.append(['parking', t.get('name', ''), lon, lat, {'cap': t.get('capacity', ''), 'type': t.get('parking', ''), 'access': t.get('access', ''), 'id': el['type'][0] + str(el['id'])}])
        elif t.get('highway') == 'motorway_junction':
            out.append(['exit', t.get('name', '') or t.get('ref', ''), lon, lat, t.get('ref', '')])
        elif t.get('leisure') == 'stadium' or t.get('amenity') == 'events_venue':
            out.append(['stadium', t.get('name', ''), lon, lat, t.get('capacity', '')])
    log('places', len(out))
    json.dump(out, gzip.open(os.path.join(OUT, 'places.json.gz'), 'wt'), separators=(',', ':'))


# Four recent NFL stadiums with very different settings: downtown + rail, a new mixed-use district, a suburban parking field, a riverfront site
REFS = [('Atlanta', 'Mercedes-Benz Stadium', 33.7554, -84.4008), ('Inglewood', 'SoFi Stadium', 33.9535, -118.3392),
        ('Orchard Park', 'Highmark Stadium (2026)', 42.7738, -78.7870), ('Nashville', 'Nissan Stadium (new)', 36.1665, -86.7713)]


def refs():
    out = []
    for city, nm, lat, lon in REFS:
        q = (f'[out:json][timeout:300];('
             f'nwr["leisure"="stadium"](around:900,{lat},{lon});'
             f'way["building"]["building"~"stadium|yes|construction"](around:350,{lat},{lon});'
             f'way["amenity"="parking"](around:1400,{lat},{lon});relation["amenity"="parking"](around:1400,{lat},{lon});'
             f'nwr["railway"~"^(station|halt)$"](around:1400,{lat},{lon});nwr["public_transport"="station"](around:1400,{lat},{lon});'
             f');out geom;')
        d = overpass(q)
        els = []
        for el in (d or {}).get('elements', []):
            t = el.get('tags', {})
            if el['type'] == 'node':
                els.append({'t': 'station', 'n': t.get('name', ''), 'p': [el['lon'], el['lat']]}); continue
            g = el.get('geometry') or []
            kind = 'stadium' if t.get('leisure') == 'stadium' else 'parking' if t.get('amenity') == 'parking' else 'station' if t.get('railway') or t.get('public_transport') else 'building'
            if el['type'] == 'relation':
                g = [p for m in el.get('members', []) if m.get('role') == 'outer' for p in (m.get('geometry') or [])]
            if len(g) >= 3:
                els.append({'t': kind, 'n': t.get('name', ''), 'r': ring(g), 'cap': t.get('capacity', ''), 'lv': t.get('building:levels', '')})
        out.append({'city': city, 'name': nm, 'c': [lon, lat], 'els': els})
        log('ref', nm, len(els)); time.sleep(10)
    json.dump(out, gzip.open(os.path.join(OUT, 'refs.json.gz'), 'wt'), separators=(',', ':'))


def blocks():
    import shapefile  # pyshp
    url = 'https://www2.census.gov/geo/tiger/TIGER2020/TABBLOCK20/tl_2020_18_tabblock20.zip'
    z = zipfile.ZipFile(io.BytesIO(get(url)))
    base = [n[:-4] for n in z.namelist() if n.endswith('.shp')][0]
    r = shapefile.Reader(shp=io.BytesIO(z.read(base + '.shp')), dbf=io.BytesIO(z.read(base + '.dbf')), shx=io.BytesIO(z.read(base + '.shx')))
    fields = [f[0] for f in r.fields[1:]]; out = {}
    for rec in r.iterRecords():
        d = dict(zip(fields, rec))
        if d['COUNTYFP20'] not in ('089', '127'):
            continue
        out[d['GEOID20']] = [round(float(d['INTPTLAT20']), 6), round(float(d['INTPTLON20']), 6), int(d.get('POP20') or 0), int(d.get('HOUSING20') or 0), int(d.get('ALAND20') or 0), 0]
    year = None
    for y in (2022, 2021, 2023):
        local = os.path.join(OUT, f'in_wac_S000_JT00_{y}.csv.gz')
        if os.path.exists(local) and os.path.getsize(local) > 10000:
            try:
                for row in csv.DictReader(io.StringIO(gzip.decompress(open(local, 'rb').read()).decode())):
                    if row['w_geocode'] in out:
                        out[row['w_geocode']][5] = int(row['C000'])
                year = y; break
            except Exception as e:
                log('wac read failed', y, repr(e))
    with gzip.open(os.path.join(OUT, 'in_blocks.csv.gz'), 'wt', newline='') as f:
        w = csv.writer(f); w.writerow(['geoid', 'lat', 'lon', 'people', 'homes', 'land_m2', 'jobs'])
        for g, v in out.items():
            if v[2] or v[3] or v[5]:
                w.writerow([g] + v)
    log('indiana blocks', len(out), 'people', sum(v[2] for v in out.values()), 'jobs year', year)
    for y in (2021, 2022, 2023):
        p = os.path.join(OUT, f'in_wac_S000_JT00_{y}.csv.gz')
        if os.path.exists(p):
            os.remove(p)


if __name__ == '__main__':
    steps = sys.argv[1:] or ['blocks', 'places', 'refs', 'land']
    for s in steps:
        try:
            if s.startswith('land') and s[4:].isdigit():
                land(int(s[4:])); continue
            globals()[s]()
        except Exception as e:
            log('step failed', s, repr(e))
    log('done', dt.datetime.utcnow().strftime('%Y-%m-%dT%H:%MZ'))
    open(os.path.join(OUT, 'fetch_log.txt'), 'a').write('\n'.join(LOG) + '\n')
