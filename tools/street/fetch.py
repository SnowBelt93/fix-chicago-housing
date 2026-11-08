"""Data for "Redesign my street" (runs in GitHub Actions; the cloud workspace can't reach Overpass or the data portal).
  tools/raw/street/osm_streets.json.gz  every OpenStreetMap street in Chicago's bounding box with the tags that describe
                                        its layout (lanes, width, parking, bike lanes, sidewalks, speed, one-way, bus lanes)
  tools/raw/street/crashes.csv.gz       City of Chicago Traffic Crashes (85ca-t3if) since 2021: date, location, injuries,
                                        and whether a pedestrian or cyclist was involved"""
import urllib.request, urllib.parse, json, os, gzip, time, csv, io
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(ROOT, 'tools', 'raw', 'street'); os.makedirs(OUT, exist_ok=True)
HDR = {'User-Agent': 'shapechicago street tool (github.com/SnowBelt93/fix-chicago-housing)', 'Accept': '*/*'}
def get(url, data=None, tries=4, timeout=900):
    for t in range(tries):
        try:
            req = urllib.request.Request(url, data=data, headers=HDR)
            with urllib.request.urlopen(req, timeout=timeout) as r: return r.read()
        except Exception as e: print('retry', t, url[:100], e, flush=True); time.sleep(15 * (t + 1))
    return None

bbox = '41.64,-87.95,42.03,-87.52'
KEEP = ['highway', 'name', 'lanes', 'lanes:forward', 'lanes:backward', 'lanes:bus', 'busway', 'width', 'est_width', 'oneway', 'maxspeed',
        'sidewalk', 'sidewalk:both', 'sidewalk:left', 'sidewalk:right', 'parking:lane:both', 'parking:lane:left', 'parking:lane:right',
        'parking:both', 'parking:left', 'parking:right', 'cycleway', 'cycleway:both', 'cycleway:left', 'cycleway:right',
        'cycleway:both:separation', 'turn:lanes', 'surface', 'bus:lanes', 'hgv', 'tiger:name_base']
out = os.path.join(OUT, 'osm_streets.json.gz')
if not os.path.exists(out):
    q = f'[out:json][timeout:900];way["highway"~"^(primary|secondary|tertiary|residential|unclassified|living_street|trunk)$"]({bbox});out geom;'
    data = None
    for host in ('https://overpass-api.de/api/interpreter', 'https://overpass.private.coffee/api/interpreter', 'https://maps.mail.ru/osm/tools/overpass/api/interpreter'):
        b = get(host, data=urllib.parse.urlencode({'data': q}).encode(), tries=2)
        if b:
            try: data = json.loads(b); print('osm from', host, flush=True); break
            except Exception as e: print('bad json', host, e, flush=True)
    if data:
        rows = []
        for el in data.get('elements', []):
            t, g = el.get('tags', {}), el.get('geometry')
            if not g or len(g) < 2: continue
            rows.append({'id': el['id'], 't': {k: t[k] for k in KEEP if k in t}, 'g': [[round(p['lon'], 6), round(p['lat'], 6)] for p in g]})
        with gzip.open(out, 'wt') as f: json.dump(rows, f, separators=(',', ':'))
        print('streets', len(rows), flush=True)

cout = os.path.join(OUT, 'crashes.csv.gz')
if not os.path.exists(cout):
    rows, header, off = [], None, 0
    sel = 'crash_record_id,crash_date,latitude,longitude,injuries_total,injuries_fatal,injuries_incapacitating,first_crash_type,posted_speed_limit,street_name'
    while True:
        u = 'https://data.cityofchicago.org/resource/85ca-t3if.csv?' + urllib.parse.urlencode({'$select': sel, '$where': "crash_date >= '2021-01-01T00:00:00' AND latitude IS NOT NULL", '$order': 'crash_record_id', '$limit': 50000, '$offset': off})
        b = get(u, timeout=300)
        if not b: break
        r = list(csv.reader(io.StringIO(b.decode('utf-8'))))
        if header is None: header = r[0]
        rows += r[1:]; print('crashes', off, len(r) - 1, flush=True)
        if len(r) - 1 < 50000: break
        off += 50000
    if rows:
        with gzip.open(cout, 'wt', newline='') as f:
            w = csv.writer(f); w.writerow(header); w.writerows(rows)
        print('crashes total', len(rows))
