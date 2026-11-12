"""Data for the lot tool's "Rules that apply here" and for the neighborhood "Does a building pencil?" check (runs in GitHub
Actions: the cloud workspace can't reach these hosts). Writes small files to tools/raw/lot/; nothing with a person's name,
email or phone is kept (every download drops columns that could hold them, and sales keep only PIN, date, price and class).

Steps (python3 tools/lot/fetch.py [steps]):
  catalog    Chicago Data Portal search for overlay datasets (landmarks, historic survey, ARO areas, demolition surcharge
             areas, enterprise zones, PMDs, industrial corridors, SSAs, ETOD) -> catalog.json (names, ids, columns)
  overlays   every catalog hit with a map shape -> ov_<id>.geojson.gz, person-like columns dropped
  districts  landmark district boundaries (a shapefile only) -> ov_landmark_districts.geojson.gz
  oz         federal Opportunity Zones: CDFI Fund tract list + Census 2010 tract shapes for Cook County -> oz_tracts.json
  flood      FEMA National Flood Hazard Layer zones inside Chicago's box -> flood.geojson.gz
  sales      Cook County Assessor sales in Chicago since 2019: PIN, date, price, class only -> sales.csv.gz
  acs        ACS 5-year table B25111 (median gross rent by year built) and B25031 (by bedrooms), Cook County tracts
  treasury   10-year Treasury yields, daily, this year and last -> treasury.csv
  hud        HUD Total Development Cost and Housing Cost Cap pages -> hud_links.json (file links) + the files' Chicago rows
"""
import urllib.request, urllib.parse, json, os, re, io, csv, gzip, zipfile, sys, time, datetime
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(os.path.dirname(HERE), 'raw', 'lot'); os.makedirs(os.path.join(OUT, 'hud'), exist_ok=True)
UA = {'User-Agent': 'Mozilla/5.0 (compatible; shapechicago-data/1.0)'}
LOG = {}
PERSON = re.compile(r'name|owner|buyer|seller|grantor|grantee|applicant|contact|email|phone|tel|agent|attorney|taxpayer|mail', re.I)
SAFE_NAMES = re.compile(r'^(district_name|landmark_name|name|zone_name|pmd_name|ssa_name|corridor_name|area_name|label|district|site_name)$', re.I)
BOX = (-87.95, 41.64, -87.52, 42.03)   # Chicago, west, south, east, north

def get(url, tries=3, timeout=300, data=None):
    last = None
    for t in range(tries):
        try: return urllib.request.urlopen(urllib.request.Request(url, headers=UA, data=data), timeout=timeout).read()
        except Exception as e: last = e; print('retry', t, url[:160], e, flush=True); time.sleep(6 * (t + 1))
    print('MISSING', url[:160], last, flush=True); return None
def jget(url, **k):
    b = get(url, **k)
    try: return json.loads(b) if b else None
    except Exception: return None
def save(name, obj): json.dump(obj, open(os.path.join(OUT, name), 'w'), indent=1)

QUERIES = ['landmark district', 'chicago landmarks', 'historic resources survey', 'affordable requirements ordinance', 'ARO',
           'demolition surcharge', 'pilsen', '606', 'enterprise zone', 'planned manufacturing district', 'industrial corridor',
           'special service area', 'transit served', 'ETOD', 'neighborhood opportunity fund', 'boundaries', 'opportunity zone',
           'low affordability community', 'residential parking', 'adu', 'coach house', 'additional dwelling unit']
WANT = re.compile(r'landmark|historic|affordable requirement|\baro\b|demolition|surcharge|pilsen|606|enterprise zone|planned manufacturing|'
                  r'industrial corridor|special service|transit[- ]served|etod|opportunity|low.?affordab|adu|coach|additional dwelling', re.I)

SKIP = re.compile(r'311|service request|deprecated|application|tabular|financial incentive|performance metric|balance sheet|historical', re.I)

def catalog():
    hits = {}
    for q in QUERIES:
        d = jget('https://api.us.socrata.com/api/catalog/v1?' + urllib.parse.urlencode({'domains': 'data.cityofchicago.org', 'q': q, 'limit': 40}))
        for r in (d or {}).get('results', []):
            res = r.get('resource', {}); i = res.get('id')
            if not i or i in hits: continue
            hits[i] = {'name': res.get('name'), 'type': res.get('type'), 'updated': res.get('updatedAt'), 'desc': (res.get('description') or '')[:300],
                       'cols': res.get('columns_field_name', [])[:60], 'want': bool(WANT.search(res.get('name') or '')) and not SKIP.search(res.get('name') or '') and res.get('type') in ('dataset', 'map')}
    save('catalog.json', hits); LOG['catalog'] = len(hits); print('catalog', len(hits), 'datasets,', sum(h['want'] for h in hits.values()), 'wanted')

def overlays():
    cat = json.load(open(os.path.join(OUT, 'catalog.json')))
    got = {}
    for i, h in cat.items():
        if not h['want']: continue
        b = get(f'https://data.cityofchicago.org/api/geospatial/{i}?method=export&format=GeoJSON', tries=2)
        if not b:
            b = get(f'https://data.cityofchicago.org/resource/{i}.geojson?$limit=50000', tries=2)
        if not b: got[i] = 'missing'; continue
        try: g = json.loads(b)
        except Exception: got[i] = 'not json'; continue
        feats = [f for f in g.get('features', []) if f.get('geometry')]
        if not feats: got[i] = 'no shapes'; continue
        for f in feats:
            f['properties'] = {k: v for k, v in (f.get('properties') or {}).items() if (SAFE_NAMES.match(k) or not PERSON.search(k)) and not re.search(r'architect|plate|vehicle', k, re.I)}
        with gzip.open(os.path.join(OUT, f'ov_{i}.geojson.gz'), 'wt') as fh: json.dump({'type': 'FeatureCollection', 'name': h['name'], 'features': feats}, fh)
        got[i] = {'name': h['name'], 'n': len(feats), 'props': sorted({k for f in feats[:50] for k in f['properties']})}
    save('overlays.json', got); LOG['overlays'] = got

def districts():
    """Landmark district boundaries are only published as a shapefile (t8pq-wu86)."""
    b = get('https://data.cityofchicago.org/download/t8pq-wu86/application%2Fzip', tries=2)
    if not b: LOG['districts'] = 'missing'; return
    import shapefile
    z = zipfile.ZipFile(io.BytesIO(b)); base = [n[:-4] for n in z.namelist() if n.lower().endswith('.shp')][0]
    prj = z.read(base + '.prj').decode('latin-1') if base + '.prj' in z.namelist() else ''
    r = shapefile.Reader(shp=io.BytesIO(z.read(base + '.shp')), dbf=io.BytesIO(z.read(base + '.dbf')))
    fields = [f[0] for f in r.fields[1:]]
    tf = None
    if 'GEOGCS' not in prj[:8]:
        from pyproj import CRS, Transformer
        tf = Transformer.from_crs(CRS.from_wkt(prj), 4326, always_xy=True)
    feats = []
    for sr in r.iterShapeRecords():
        pts = sr.shape.points; parts = list(sr.shape.parts) + [len(pts)]
        rings = [[list(tf.transform(x, y)) if tf else [x, y] for x, y in pts[a:b]] for a, b in zip(parts, parts[1:])]
        rings = [[[round(x, 6), round(y, 6)] for x, y in ring] for ring in rings]
        props = {k: (v.isoformat() if hasattr(v, 'isoformat') else v) for k, v in zip(fields, sr.record) if not PERSON.search(k) or SAFE_NAMES.match(k)}
        feats.append({'type': 'Feature', 'properties': props, 'geometry': {'type': 'Polygon', 'coordinates': rings}})
    with gzip.open(os.path.join(OUT, 'ov_landmark_districts.geojson.gz'), 'wt') as fh: json.dump({'type': 'FeatureCollection', 'name': 'Landmark Districts', 'features': feats}, fh)
    LOG['districts'] = {'n': len(feats), 'fields': fields, 'prj': prj[:120]}

def oz():
    """Opportunity Zones are 2010 census tracts. Try the CDFI Fund list, then Census 2010 tract shapes for Cook County."""
    tried = {}
    tracts = set()
    for u in ['https://www.cdfifund.gov/sites/cdfi/files/documents/designated-qozs.12.14.18.xlsx',
              'https://www.cdfifund.gov/sites/cdfi/files/2018-12/Designated%20QOZs.12.14.18.xlsx',
              'https://www.cdfifund.gov/Documents/Designated%20QOZs.12.14.18.xlsx']:
        b = get(u, tries=2); tried[u] = bool(b)
        if not b: continue
        try:
            import openpyxl
            wb = openpyxl.load_workbook(io.BytesIO(b), read_only=True)
            for ws in wb.worksheets:
                for row in ws.iter_rows(values_only=True):
                    for c in row:
                        s = str(c or '').strip()
                        if re.fullmatch(r'17031\d{6}', s): tracts.add(s)
        except Exception as e: tried[u] = str(e)
        if tracts: break
    # fallback: HUD's ArcGIS layer of Opportunity Zones
    if not tracts:
        for u in ['https://services.arcgis.com/VTyQ9soqVukalItT/arcgis/rest/services/Opportunity_Zones/FeatureServer/13/query?where=STATE%3D%2717%27+AND+COUNTY%3D%27031%27&outFields=GEOID10&f=json&returnGeometry=false',
                  'https://hudgis-hud.opendata.arcgis.com/api/search/v1/collections/all/items?q=opportunity%20zones&limit=5']:
            d = jget(u, tries=2); tried[u] = bool(d)
            for f in (d or {}).get('features', []) or []:
                g = (f.get('attributes') or {}).get('GEOID10');
                if g: tracts.add(str(g))
            if d and not tracts: tried[u] = json.dumps(d)[:600]
    shapes = {}
    b = get('https://www2.census.gov/geo/tiger/TIGER2010/TRACT/2010/tl_2010_17031_tract10.zip', tries=2)
    tried['tiger2010'] = bool(b)
    if b:
        try:
            import shapefile   # pyshp
            z = zipfile.ZipFile(io.BytesIO(b)); base = [n[:-4] for n in z.namelist() if n.endswith('.shp')][0]
            r = shapefile.Reader(shp=io.BytesIO(z.read(base + '.shp')), dbf=io.BytesIO(z.read(base + '.dbf')))
            fields = [f[0] for f in r.fields[1:]]
            for sr in r.iterShapeRecords():
                g = dict(zip(fields, sr.record)).get('GEOID10')
                if g in tracts or not tracts: shapes[g] = [[[round(x, 5), round(y, 5)] for x, y in sr.shape.points[a:b]] for a, b in zip(sr.shape.parts, list(sr.shape.parts[1:]) + [len(sr.shape.points)])]
        except Exception as e: tried['tiger_err'] = str(e)
    save('oz_tracts.json', {'tracts': sorted(tracts), 'shapes': shapes if tracts else {}, 'tried': tried})
    LOG['oz'] = {'tracts': len(tracts), 'shapes': len(shapes) if tracts else 0, 'tried': tried}

def flood():
    """FEMA NFHL layer 28 (flood hazard zones), paged by object id inside Chicago's box."""
    base = 'https://hazards.fema.gov/arcgis/rest/services/public/NFHL/MapServer/28/query'
    geom = json.dumps({'xmin': BOX[0], 'ymin': BOX[1], 'xmax': BOX[2], 'ymax': BOX[3], 'spatialReference': {'wkid': 4326}})
    q = {'where': "FLD_ZONE IN ('A','AE','AH','AO','VE')", 'geometry': geom, 'geometryType': 'esriGeometryEnvelope', 'inSR': 4326,
         'spatialRel': 'esriSpatialRelIntersects', 'outFields': 'FLD_ZONE,ZONE_SUBTY,SFHA_TF', 'outSR': 4326, 'f': 'geojson',
         'resultRecordCount': 500, 'geometryPrecision': 5}
    feats, off = [], 0
    while off < 20000:
        q['resultOffset'] = off
        d = jget(base + '?' + urllib.parse.urlencode(q), tries=2, timeout=120)
        if not d or 'features' not in d: LOG['flood_err'] = (json.dumps(d)[:400] if d else 'no reply'); break
        f = d['features']; feats += f
        if len(f) < 500: break
        off += 500
    if feats:
        with gzip.open(os.path.join(OUT, 'flood.geojson.gz'), 'wt') as fh: json.dump({'type': 'FeatureCollection', 'features': feats}, fh)
    LOG['flood'] = len(feats)

def sales():
    """Cook County Assessor Parcel Sales (wvhk-k5uv). Only PIN, date, price, class, township and the sale filters are
    asked for; the dataset's buyer and seller name columns are never requested."""
    meta = jget('https://datacatalog.cookcountyil.gov/api/views/wvhk-k5uv.json')
    cols = [c['fieldName'] for c in (meta or {}).get('columns', [])]
    LOG['sales_cols'] = cols
    keep = [c for c in cols if not PERSON.search(c) and re.search(r'^(pin|year|township_code|nbhd|class|sale_date|sale_price|sale_document_num|is_multisale|num_parcels_sale|sale_filter.*|sale_type|deed_type|sale_deed_type)$', c)]
    keep = [c for c in keep if c != 'sale_document_num']
    if 'pin' not in keep or 'sale_price' not in keep: LOG['sales'] = 'columns not found'; return
    town = 'township_code' if 'township_code' in keep else None
    where = "sale_date >= '2019-01-01T00:00:00'" + (" AND township_code in ('70','71','72','73','74','75','76','77')" if town else '')
    rows, off = [], 0
    while True:
        u = 'https://datacatalog.cookcountyil.gov/resource/wvhk-k5uv.json?' + urllib.parse.urlencode({'$select': ','.join(keep), '$where': where, '$limit': 50000, '$offset': off, '$order': 'sale_date'})
        d = jget(u, timeout=600)
        if d is None: LOG['sales_err'] = 'page failed at ' + str(off); break
        rows += d
        if len(d) < 50000: break
        off += 50000
    with gzip.open(os.path.join(OUT, 'sales.csv.gz'), 'wt', newline='') as fh:
        w = csv.writer(fh); w.writerow(keep)
        for r in rows: w.writerow([r.get(c, '') for c in keep])
    LOG['sales'] = {'rows': len(rows), 'cols': keep}

def acs():
    """ACS 2019-2023 table-based summary files (no API key needed): B25111 and B25031 for Cook County tracts."""
    got = {}
    for tb in ['b25111', 'b25031', 'b25034']:
        for yr in (2024, 2023):
            u = f'https://www2.census.gov/programs-surveys/acs/summary_file/{yr}/table-based-SF/data/5YRData/acsdt5y{yr}-{tb}.dat'
            b = get(u, tries=2, timeout=600)
            if not b: continue
            lines = b.decode('utf-8', 'replace').splitlines()
            head = lines[0]; keep = [l for l in lines[1:] if '|1400000US17031' in l or l.split('|')[0].startswith('1400000US17031')]
            with gzip.open(os.path.join(OUT, f'acs_{tb}_{yr}.dat.gz'), 'wt') as fh: fh.write(head + '\n' + '\n'.join(keep) + '\n')
            got[tb] = {'year': yr, 'rows': len(keep)}; break
    LOG['acs'] = got

def treasury():
    rows = []
    for y in (datetime.date.today().year - 1, datetime.date.today().year):
        u = f'https://home.treasury.gov/resource-center/data-chart-center/interest-rates/daily-treasury-rates.csv/{y}/all?type=daily_treasury_yield_curve&field_tdr_date_value={y}&page&_format=csv'
        b = get(u, tries=2)
        if b: rows += [l for i, l in enumerate(b.decode().splitlines()) if i or not rows]
    if rows: open(os.path.join(OUT, 'treasury.csv'), 'w').write('\n'.join(rows) + '\n')
    LOG['treasury'] = len(rows)

def hud():
    """Find HUD's yearly Total Development Cost limits and Housing Cost Cap files, keep their Chicago rows."""
    links = {}
    for page in ['https://www.hud.gov/program_offices/public_indian_housing/programs/ph/capfund', 'https://www.hud.gov/hud-partners/public-indian-housing-capital-fund',
                 'https://www.hud.gov/program_offices/public_indian_housing/publications/notices', 'https://www.hudexchange.info/programs/home/home-per-unit-subsidy/',
                 'https://www.hud.gov/program_offices/comm_planning/home/limits', 'https://www.huduser.gov/portal/datasets/home-datasets/files/']:
        b = get(page, tries=2)
        if not b: links[page] = None; continue
        h = b.decode('utf-8', 'replace')
        links[page] = sorted({urllib.parse.urljoin(page, m) for m in re.findall(r'href="([^"]+\.(?:xlsx|xls|pdf|csv))"', h, re.I) if re.search(r'tdc|total.?dev|cost|subsidy|limit|hcc', m, re.I)})[:40]
    save('hud_links.json', links)
    keep = {}
    for page, L in links.items():
        for u in (L or []):
            if not re.search(r'\.(xlsx|xls|csv)$', u, re.I) or not re.search(r'tdc|total.?dev|subsid', u, re.I): continue
            b = get(u, tries=2)
            if not b: continue
            try:
                if u.lower().endswith('.csv'): text = b.decode('utf-8', 'replace').splitlines(); hit = [l for l in text[:3]] + [l for l in text if re.search(r'chicago|cook', l, re.I)]
                else:
                    import openpyxl
                    wb = openpyxl.load_workbook(io.BytesIO(b), read_only=True, data_only=True); hit = []
                    for ws in wb.worksheets:
                        for i, row in enumerate(ws.iter_rows(values_only=True)):
                            s = ['' if c is None else str(c) for c in row]
                            if i < 4 or any(re.search(r'chicago|cook', c, re.I) for c in s): hit.append(ws.title + '|' + '|'.join(s[:40]))
                keep[u] = hit[:200]
            except Exception as e: keep[u] = str(e)
    save('hud_rows.json', keep); LOG['hud'] = {k: (len(v) if isinstance(v, list) else v) for k, v in keep.items()}


# ---- affordable-housing deal check and grants finder (Nov 12, 2026) ----
def links(page, pat):
    b = get(page, tries=2)
    if not b: return []
    h = b.decode('utf-8', 'replace')
    return sorted({urllib.parse.urljoin(page, m) for m in re.findall(r'href="([^"]+)"', h) if re.search(pat, m, re.I)})

def chicago_rows(b, name, pat=r'chicago|cook|17031|\b606\d\d'):
    """Keep the header rows and the Chicago rows of a spreadsheet or CSV (as text lines)."""
    out = []
    try:
        if name.lower().endswith(('.xlsx', '.xls')):
            import openpyxl
            wb = openpyxl.load_workbook(io.BytesIO(b), read_only=True, data_only=True)
            for ws in wb.worksheets:
                for i, row in enumerate(ws.iter_rows(values_only=True)):
                    s = ['' if c is None else str(c) for c in row]
                    if i < 3 or any(re.search(pat, c, re.I) for c in s): out.append(ws.title + '|' + '|'.join(s[:120]))
        elif name.lower().endswith('.zip'):
            z = zipfile.ZipFile(io.BytesIO(b))
            for n in z.namelist():
                if n.lower().endswith(('.csv', '.txt', '.xlsx', '.xls')): out += [n + ':' + l for l in chicago_rows(z.read(n), n, pat)[:5000]]
        else:
            t = b.decode('utf-8', 'replace').splitlines()
            out = t[:3] + [l for l in t[3:] if re.search(pat, l, re.I)]
    except Exception as e: out = ['ERROR ' + repr(e)]
    return out

def hudlim():
    """HUD income limits, the tax-credit (MTSP) income and rent limits, QCTs and DDAs: Chicago rows only."""
    got = {}
    pages = {'mtsp': ('https://www.huduser.gov/portal/datasets/mtsp.html', r'(fy2?0?2[67]|il2[67]).*\.(xlsx|xls|csv|zip)$'),
             'il': ('https://www.huduser.gov/portal/datasets/il.html', r'(fy2?0?2[67]|il2[67]).*\.(xlsx|xls|csv|zip)$'),
             'qct': ('https://www.huduser.gov/portal/datasets/qct.html', r'(202[67]|2[67]).*\.(xlsx|xls|csv|zip)$'),
             'sadda': ('https://www.huduser.gov/portal/sadda/sadda_qct.html', r'\.(xlsx|xls|csv|zip)$')}
    for k, (page, pat) in pages.items():
        L = links(page, pat); got[k] = {'links': L[:40]}
        for u in L[:12]:
            b = get(u, tries=2, timeout=600)
            if not b: got[k][u] = 'missing'; continue
            rows = chicago_rows(b, u.split('?')[0])
            fn = k + '_' + re.sub(r'[^A-Za-z0-9._-]', '_', u.rsplit('/', 1)[-1])[:80] + '.txt.gz'
            with gzip.open(os.path.join(OUT, 'hud', fn), 'wt') as fh: fh.write('\n'.join(rows))
            got[k][u] = len(rows)
    save('hudlim.json', got); LOG['hudlim'] = {k: {u: v for u, v in d.items() if u != 'links'} for k, d in got.items()}

def amen():
    """Places the city's tax-credit plan counts as amenities (full-service grocery, health care, schools, parks), from
    OpenStreetMap (ODbL: credit OpenStreetMap contributors). Only the kind, a name of the business or place and the point."""
    s, w, n, e = 41.64, -87.95, 42.03, -87.52
    q = f"""[out:json][timeout:600];(
      nwr["shop"="supermarket"]({s},{w},{n},{e});
      nwr["amenity"~"^(hospital|clinic|doctors|pharmacy)$"]({s},{w},{n},{e});
      nwr["healthcare"~"^(hospital|clinic|doctor|pharmacy|centre)$"]({s},{w},{n},{e});
      nwr["amenity"="school"]({s},{w},{n},{e});
      nwr["leisure"="park"]({s},{w},{n},{e}););out center tags;"""
    d = None
    for host in ('https://overpass-api.de/api/interpreter', 'https://overpass.kumi.systems/api/interpreter'):
        d = jget(host, data=urllib.parse.urlencode({'data': q}).encode(), timeout=900)
        if d: break
    pts = []
    for el in (d or {}).get('elements', []):
        t = el.get('tags', {}); c = el.get('center') or el
        if 'lat' not in c: continue
        k = ('grocery' if t.get('shop') == 'supermarket' else 'school' if t.get('amenity') == 'school' else 'park' if t.get('leisure') == 'park'
             else 'health')
        pts.append([k, round(c['lon'], 5), round(c['lat'], 5), (t.get('name') or '')[:60]])
    with gzip.open(os.path.join(OUT, 'amen.json.gz'), 'wt') as fh: json.dump(pts, fh)
    LOG['amen'] = {k: sum(1 for p in pts if p[0] == k) for k in ('grocery', 'health', 'school', 'park')}

def places():
    """City layers the deal check needs: TIF districts, Neighborhood Opportunity Fund areas, parks, schools."""
    want = {'tif': (['tax increment financing district', 'tif boundaries'], r'tax increment|\btif\b'),
            'nof': (['neighborhood opportunity fund'], r'opportunity fund'),
            'cps': (['school locations'], r'school.*location|location.*school'),
            'parks': (['park district parks', 'parks - shapefiles'], r'^parks|park.*boundar')}
    got = {}
    for k, (qs, pat) in want.items():
        hits = {}
        for q in qs:
            d = jget('https://api.us.socrata.com/api/catalog/v1?' + urllib.parse.urlencode({'domains': 'data.cityofchicago.org', 'q': q, 'limit': 20}))
            for r in (d or {}).get('results', []):
                res = r.get('resource', {})
                if re.search(pat, res.get('name') or '', re.I) and not re.search(r'deprecated|historical|tabular|\b19\d\d\b|201\d', res.get('name') or '', re.I):
                    hits[res['id']] = {'name': res['name'], 'type': res.get('type'), 'updated': res.get('updatedAt'), 'cols': res.get('columns_field_name', [])[:40]}
        got[k] = hits
        for i, h in list(hits.items())[:3]:
            b = get(f'https://data.cityofchicago.org/api/geospatial/{i}?method=export&format=GeoJSON', tries=2) or get(f'https://data.cityofchicago.org/resource/{i}.geojson?$limit=50000', tries=2)
            try: g = json.loads(b) if b else None
            except Exception: g = None
            feats = [f for f in (g or {}).get('features', []) if f.get('geometry')]
            if not feats: h['got'] = 0; continue
            for f in feats: f['properties'] = {a: v for a, v in (f.get('properties') or {}).items() if not PERSON.search(a) or SAFE_NAMES.match(a)}
            with gzip.open(os.path.join(OUT, f'pl_{k}_{i}.geojson.gz'), 'wt') as fh: json.dump({'type': 'FeatureCollection', 'name': h['name'], 'features': feats}, fh)
            h['got'] = len(feats)
    save('places.json', got); LOG['places'] = {k: {i: h.get('got') for i, h in v.items()} for k, v in got.items()}

def acs2():
    """ACS 5-year tables for the city's market-area tests: household income brackets (B19001), poverty (B17001),
    median household income (B19013), median gross rent (B25064), median home value (B25077). Cook County tracts."""
    got = {}
    for tb in ['b19001', 'b17001', 'b19013', 'b25064', 'b25077', 'b11001']:
        for yr in (2024, 2019):
            u = f'https://www2.census.gov/programs-surveys/acs/summary_file/{yr}/table-based-SF/data/5YRData/acsdt5y{yr}-{tb}.dat'
            b = get(u, tries=2, timeout=600)
            if not b: got[f'{tb}_{yr}'] = 'missing'; continue
            lines = b.decode('utf-8', 'replace').splitlines()
            keep = [l for l in lines[1:] if '1400000US17031' in l.split('|')[0]]
            with gzip.open(os.path.join(OUT, f'acs_{tb}_{yr}.dat.gz'), 'wt') as fh: fh.write(lines[0] + '\n' + '\n'.join(keep) + '\n')
            got[f'{tb}_{yr}'] = len(keep)
    LOG['acs2'] = got

def geo2():
    """Census tract (2024 cartographic, Cook County) and ZIP code area (2020 ZCTA, 606xx) outlines: only the ID and shape."""
    import shapefile
    got = {}
    for name, url, keep, idf in [('tracts', 'https://www2.census.gov/geo/tiger/GENZ2024/shp/cb_2024_17_tract_500k.zip', lambda g: g.startswith('17031'), 'GEOID'),
                                 ('zcta', 'https://www2.census.gov/geo/tiger/GENZ2020/shp/cb_2020_us_zcta520_500k.zip', lambda g: g.startswith('606'), 'ZCTA5CE20')]:
        b = get(url, tries=2, timeout=900)
        if not b: got[name] = 'missing'; continue
        z = zipfile.ZipFile(io.BytesIO(b)); base = [n[:-4] for n in z.namelist() if n.endswith('.shp')][0]
        r = shapefile.Reader(shp=io.BytesIO(z.read(base + '.shp')), dbf=io.BytesIO(z.read(base + '.dbf')))
        fields = [f[0] for f in r.fields[1:]]; feats = []
        for sr in r.iterShapeRecords():
            g = str(dict(zip(fields, sr.record)).get(idf) or '')
            if not keep(g): continue
            pts = sr.shape.points; parts = list(sr.shape.parts) + [len(pts)]
            rings = [[[round(x, 5), round(y, 5)] for x, y in pts[a:b]] for a, b in zip(parts, parts[1:])]
            feats.append({'type': 'Feature', 'properties': {'id': g}, 'geometry': {'type': 'Polygon', 'coordinates': rings}})
        with gzip.open(os.path.join(OUT, f'{name}.geojson.gz'), 'wt') as fh: json.dump({'type': 'FeatureCollection', 'features': feats}, fh)
        got[name] = len(feats)
    LOG['geo2'] = got

STEPS = {'catalog': catalog, 'overlays': overlays, 'districts': districts, 'oz': oz, 'flood': flood, 'sales': sales, 'acs': acs, 'treasury': treasury, 'hud': hud, 'hudlim': hudlim, 'amen': amen, 'places': places, 'acs2': acs2, 'geo2': geo2}
if __name__ == '__main__':
    todo = sys.argv[1:] or list(STEPS)
    for s in todo:
        t = time.time()
        try: STEPS[s]()
        except Exception as e: LOG[s + '_crash'] = repr(e); print('step', s, 'failed', e, flush=True)
        print('step', s, round(time.time() - t), 's', flush=True)
    old = {}
    try: old = json.load(open(os.path.join(OUT, 'log.json')))
    except Exception: pass
    old.update(LOG); old['ran'] = datetime.datetime.utcnow().isoformat(timespec='seconds')
    save('log.json', old)
