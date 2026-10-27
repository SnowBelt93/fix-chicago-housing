#!/usr/bin/env python3
"""Download and compact the data the transit tool needs. Runs in GitHub Actions (the cloud workspace can't reach
these hosts). Writes small files to tools/raw/transit/:

  cta_routes.json, metra_routes.json   route id, short/long name, GTFS route_type, color
  cta_stops.csv.gz, metra_stops.csv.gz stop id, name, lat, lon, parent station, routes served, weekday departures
  cta_shapes.json.gz, metra_shapes.json.gz   one simplified polyline per route and direction (the most-used shape)
  blocks.csv.gz                        2020 Census blocks in Cook + collar counties: centroid, people, homes, jobs
  cta_bus_ridership.csv                average weekday boardings per bus route, latest full year
  sources.json                         what was downloaded, from where, when, and the service date used

Sources:
  CTA GTFS            https://www.transitchicago.com/downloads/sch_data/google_transit.zip
  Metra GTFS          https://schedules.metrarail.com/gtfs/schedule.zip
  Census 2020 blocks  https://www2.census.gov/geo/tiger/TIGER2020/TABBLOCK20/tl_2020_17_tabblock20.zip (POP20, HOUSING20)
  LEHD LODES 8 jobs   https://lehd.ces.census.gov/data/lodes/LODES8/il/wac/il_wac_S000_JT00_<year>.csv.gz
  CTA bus ridership   https://data.cityofchicago.org/resource/jyb9-n7fm.csv (daily boardings by route)
"""
import collections, csv, datetime as dt, gzip, io, json, math, os, sys, urllib.request, zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(ROOT, 'tools', 'raw', 'transit')
os.makedirs(OUT, exist_ok=True)
UA = {'User-Agent': 'Mozilla/5.0 (fixchicagohousing.com transit tool data fetch)'}
COUNTIES = {'031': 'Cook', '043': 'DuPage', '089': 'Kane', '097': 'Lake', '111': 'McHenry', '197': 'Will'}
SOURCES = {'fetched': dt.datetime.utcnow().strftime('%Y-%m-%dT%H:%MZ'), 'files': {}}


def get(url, tries=3):
    for i in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=600) as r:
                return r.read()
        except Exception as e:
            log('retry', url, repr(e))
            if i == tries - 1:
                raise


def rows(z, name):
    with z.open(name) as f:
        for r in csv.DictReader(io.TextIOWrapper(f, encoding='utf-8-sig')):
            yield {(k or '').strip(): (v or '').strip() for k, v in r.items()}


LOG = []
def log(*a):
    msg = ' '.join(str(x) for x in a)
    print(msg, file=sys.stderr); LOG.append(msg)


def service_ids(z, names):
    """Service ids running on a typical weekday: the first Wednesday at least 7 days into the feed."""
    cal = list(rows(z, 'calendar.txt')) if 'calendar.txt' in names else []
    cal = [r for r in cal if r.get('start_date') and r.get('end_date')]
    dates = list(rows(z, 'calendar_dates.txt')) if 'calendar_dates.txt' in names else []
    log('calendar rows', len(cal), 'calendar_dates rows', len(dates), 'cols', list((cal or dates or [{}])[0].keys()))
    starts = [r['start_date'] for r in cal] or [r['date'] for r in dates]
    start = dt.datetime.strptime(min(starts), '%Y%m%d').date()
    today = dt.date.today()
    d = max(start, today) + dt.timedelta(days=7)
    while d.weekday() != 2:
        d += dt.timedelta(days=1)
    ds = d.strftime('%Y%m%d')
    ids = {r['service_id'] for r in cal if r['wednesday'] == '1' and r['start_date'] <= ds <= r['end_date']}
    for r in dates:
        if r['date'] == ds:
            (ids.add if r['exception_type'] == '1' else ids.discard)(r['service_id'])
    if not ids:  # feed only covers dates before our pick: fall back to its last Wednesday
        ends = [r['end_date'] for r in cal] or [r['date'] for r in dates]
        d = dt.datetime.strptime(max(ends), '%Y%m%d').date()
        while d.weekday() != 2:
            d -= dt.timedelta(days=1)
        return service_ids_on(cal, dates, d.strftime('%Y%m%d')), d.strftime('%Y-%m-%d')
    return ids, d.strftime('%Y-%m-%d')


def service_ids_on(cal, dates, ds):
    ids = {r['service_id'] for r in cal if r['wednesday'] == '1' and r['start_date'] <= ds <= r['end_date']}
    for r in dates:
        if r['date'] == ds:
            (ids.add if r['exception_type'] == '1' else ids.discard)(r['service_id'])
    return ids


def rdp(pts, eps):
    if len(pts) < 3:
        return pts
    a, b = pts[0], pts[-1]
    lat0 = math.radians(a[1])
    def xy(p): return ((p[0] - a[0]) * 111320 * math.cos(lat0), (p[1] - a[1]) * 110574)
    bx, by = xy(b)
    L = math.hypot(bx, by) or 1e-9
    i, dm = 0, -1
    for k in range(1, len(pts) - 1):
        px, py = xy(pts[k])
        d = abs(by * px - bx * py) / L if L > 1e-6 else math.hypot(px, py)
        if d > dm:
            i, dm = k, d
    if dm > eps:
        return rdp(pts[:i + 1], eps)[:-1] + rdp(pts[i:], eps)
    return [a, b]


def write_patterns(name, trips, trip_st):
    # Each route's weekday stop patterns: stop order, average scheduled minutes from the first stop,
    # trips a weekday and trips leaving the first stop 10am-3pm (midday headway). Patterns under 5% of a route's trips are dropped.
    pats = collections.defaultdict(lambda: {'n': 0, 'mid': 0, 'peak': 0, 'sum': None})
    for tid, sts in trip_st.items():
        sts.sort()
        rid, d = trips[tid][0], trips[tid][1]
        key = (rid, d, tuple(x[1] for x in sts))
        p = pats[key]
        t0 = sts[0][2]; rel = [x[2] - t0 for x in sts]
        p['sum'] = rel if p['sum'] is None else [a + b for a, b in zip(p['sum'], rel)]
        p['n'] += 1
        if 10 * 3600 <= t0 < 15 * 3600:
            p['mid'] += 1
        if 7 * 3600 <= t0 < 9 * 3600:
            p['peak'] += 1
    by_route = collections.Counter()
    for (rid, d, _), p in pats.items():
        by_route[rid] += p['n']
    out = collections.defaultdict(list)
    for (rid, d, seq), p in sorted(pats.items(), key=lambda kv: -kv[1]['n']):
        if p['n'] < 0.05 * by_route[rid] or len(seq) < 2:
            continue
        out[rid].append({'dir': d, 'stops': list(seq), 'min': [round(v / p['n'] / 60, 1) for v in p['sum']],
                         'trips': p['n'], 'mid': p['mid'], 'peak': p['peak']})
    with gzip.open(os.path.join(OUT, f'{name}_patterns.json.gz'), 'wt') as f:
        json.dump(out, f, separators=(',', ':'))
    log(name, 'patterns', sum(len(v) for v in out.values()), 'routes', len(out))


def gtfs(name, url):
    print('downloading', name, file=sys.stderr)
    blob = get(url)
    z = zipfile.ZipFile(io.BytesIO(blob))
    names = set(z.namelist())
    routes = {r['route_id']: r for r in rows(z, 'routes.txt')}
    sids, day = service_ids(z, names)
    trips = {}
    for t in rows(z, 'trips.txt'):
        trips[t['trip_id']] = (t['route_id'], t.get('direction_id', ''), t.get('shape_id', ''), t['service_id'] in sids)
    deps = collections.Counter()
    trip_st = collections.defaultdict(list)
    stop_routes = collections.defaultdict(set)
    shape_use = collections.Counter()
    route_trips = collections.Counter()
    for t, (rid, d, sh, on) in trips.items():
        if on:
            route_trips[rid] += 1
            if sh:
                shape_use[(rid, d, sh)] += 1
    for st in rows(z, 'stop_times.txt'):
        t = trips.get(st['trip_id'])
        if not t:
            continue
        stop_routes[st['stop_id']].add(t[0])
        if t[3]:
            deps[st['stop_id']] += 1
            tm = st.get('departure_time') or st.get('arrival_time') or ''
            if tm:
                h, m, sec = (int(x) for x in tm.split(':'))
                trip_st[st['trip_id']].append((int(st['stop_sequence']), st['stop_id'], h * 3600 + m * 60 + sec))
    write_patterns(name, trips, trip_st)
    stops = list(rows(z, 'stops.txt'))
    # roll child platforms up to their parent station too
    parent_routes = collections.defaultdict(set); parent_deps = collections.Counter()
    for s in stops:
        p = s.get('parent_station') or ''
        if p:
            parent_routes[p] |= stop_routes.get(s['stop_id'], set())
            parent_deps[p] += deps.get(s['stop_id'], 0)
    with gzip.open(os.path.join(OUT, f'{name}_stops.csv.gz'), 'wt', newline='') as f:
        w = csv.writer(f)
        w.writerow(['stop_id', 'name', 'lat', 'lon', 'location_type', 'parent', 'routes', 'weekday_departures'])
        for s in stops:
            sid = s['stop_id']
            rs = stop_routes.get(sid, set()) | parent_routes.get(sid, set())
            if not rs:
                continue
            w.writerow([sid, s['stop_name'], round(float(s['stop_lat']), 6), round(float(s['stop_lon']), 6),
                        s.get('location_type', '') or '0', s.get('parent_station', ''), ' '.join(sorted(rs)),
                        deps.get(sid, 0) + parent_deps.get(sid, 0)])
    rout = []
    for rid, r in routes.items():
        rout.append({'id': rid, 'short': r.get('route_short_name', ''), 'long': r.get('route_long_name', ''),
                     'type': int(r.get('route_type', 3) or 3), 'color': r.get('route_color', ''),
                     'weekday_trips': route_trips.get(rid, 0)})
    json.dump(rout, open(os.path.join(OUT, f'{name}_routes.json'), 'w'), indent=0)
    shapes = {}
    if 'shapes.txt' in names:
        # every shape used on the weekday (branches, expresses, short turns); build.py drops the duplicates
        want = {sh for (rid, d, sh), n in shape_use.items()}
        pts = collections.defaultdict(list)
        for r in rows(z, 'shapes.txt'):
            if r['shape_id'] in want:
                pts[r['shape_id']].append((int(r['shape_pt_sequence']), float(r['shape_pt_lon']), float(r['shape_pt_lat'])))
        for (rid, d, sh), n in sorted(shape_use.items(), key=lambda kv: -kv[1]):
            line = [(round(x, 6), round(y, 6)) for _, x, y in sorted(pts[sh])]
            if len(line) > 1:
                shapes.setdefault(rid, []).append({'dir': d, 'trips': n, 'pts': rdp(line, 4)})
    with gzip.open(os.path.join(OUT, f'{name}_shapes.json.gz'), 'wt') as f:
        json.dump(shapes, f, separators=(',', ':'))
    SOURCES['files'][name] = {'url': url, 'service_date': day, 'routes': len(rout), 'stops': len(stops),
                              'weekday_trips': sum(route_trips.values())}
    print(name, SOURCES['files'][name], file=sys.stderr)


def blocks():
    import shapefile  # pyshp
    url = 'https://www2.census.gov/geo/tiger/TIGER2020/TABBLOCK20/tl_2020_17_tabblock20.zip'
    print('downloading blocks', file=sys.stderr)
    z = zipfile.ZipFile(io.BytesIO(get(url)))
    base = [n[:-4] for n in z.namelist() if n.endswith('.shp')][0]
    r = shapefile.Reader(shp=io.BytesIO(z.read(base + '.shp')), dbf=io.BytesIO(z.read(base + '.dbf')),
                         shx=io.BytesIO(z.read(base + '.shx')))
    fields = [f[0] for f in r.fields[1:]]
    out = {}
    log('block fields', fields[:20])
    for rec in r.iterRecords():
        d = dict(zip(fields, rec))
        geoid, cty, lat, lon = d['GEOID20'], d['COUNTYFP20'], d['INTPTLAT20'], d['INTPTLON20']
        pop, hu, aland = d.get('POP20') or 0, d.get('HOUSING20') or 0, d.get('ALAND20') or 0
        if cty not in COUNTIES:
            continue
        out[geoid] = [round(float(lat), 6), round(float(lon), 6), int(pop), int(hu), int(aland), 0]
    year = None
    lodes_text, partial = None, False
    for y in (2023, 2022, 2021, 2020):
        local = os.path.join(OUT, f'il_wac_S000_JT00_{y}.csv.gz')   # downloaded by curl in the workflow (resumable)
        if os.path.exists(local) and os.path.getsize(local) > 100000:
            raw = open(local, 'rb').read()
            try:
                lodes_text = gzip.decompress(raw).decode('utf-8')
            except Exception:  # the server often cuts the file short: keep every complete row we got
                import zlib
                lodes_text = zlib.decompressobj(16 + zlib.MAX_WBITS).decompress(raw).decode('utf-8', 'ignore')
                lodes_text = lodes_text[:lodes_text.rfind('\n') + 1]
                partial = True
            year = y
            break
        log('no local LODES file for', y)
    jobs_total = 0
    last_geocode = None
    if year:
        for row in csv.DictReader(io.StringIO(lodes_text)):
            last_geocode = row['w_geocode']
            g = row['w_geocode']
            if g in out:
                out[g][5] = int(row['C000']); jobs_total += int(row['C000'])
    with gzip.open(os.path.join(OUT, 'blocks.csv.gz'), 'wt', newline='') as f:
        w = csv.writer(f)
        w.writerow(['geoid', 'lat', 'lon', 'people', 'homes', 'land_m2', 'jobs'])
        for g, v in out.items():
            if v[2] or v[3] or v[5]:
                w.writerow([g] + v)
    SOURCES['files']['blocks'] = {'url': url, 'jobs_url': f'LODES8 il_wac_S000_JT00_{year}', 'jobs_year': year,
                                  'blocks': len(out), 'people': sum(v[2] for v in out.values()),
                                  'people_city_county': sum(v[2] for g, v in out.items() if g[2:5] == '031'),
                                  'jobs': jobs_total, 'jobs_file_partial': partial,
                                  'jobs_last_block': last_geocode}
    print(SOURCES['files']['blocks'], file=sys.stderr)


def bus_ridership():
    year = dt.date.today().year - 1
    url = ('https://data.cityofchicago.org/resource/jyb9-n7fm.csv?$select=route,avg(rides)%20as%20avg_rides,count(*)%20as%20days'
           f"&$where=daytype='W'%20AND%20date%20between%20'{year}-01-01T00:00:00'%20and%20'{year}-12-31T23:59:59'"
           '&$group=route&$limit=5000')
    try:
        data = get(url)
    except Exception as e:
        print('bus ridership failed', e, file=sys.stderr)
        return
    open(os.path.join(OUT, 'cta_bus_ridership.csv'), 'wb').write(data)
    SOURCES['files']['bus_ridership'] = {'url': 'https://data.cityofchicago.org/d/jyb9-n7fm', 'year': year, 'daytype': 'weekday'}


def metra_counts():
    # Metra's newest station-level weekday boarding counts are the fall 2018 survey (RTAMS / Illinois data hub).
    url = ('https://datahub.nita.illinois.gov/sites/default/files/documents/2024-07/'
           'Metra_Ridership_by_Station_Boarding_Alighting%20Survey_1979_2018.csv')
    data = get(url)
    open(os.path.join(OUT, 'metra_station_counts.csv'), 'wb').write(data)
    SOURCES['files']['metra_counts'] = {'url': url, 'bytes': len(data),
                                        'page': 'https://datahub.nita.illinois.gov/media/resources/metra-ridership-station-boarding-alighting-survey-1979-2018'}
    log('metra counts', len(data))


def ntd_energy():
    # NTD fuel and energy use by agency and mode (Metra 50118, CTA 50066): diesel gallons, propulsion kWh
    found = False
    for url in ["https://data.transportation.gov/resource/8ehq-7his.csv?$where=ntd_id%20in('50118','50066','10118','10066')&$limit=5000",
                "https://data.transportation.gov/api/views/8ehq-7his/rows.csv?accessType=DOWNLOAD"]:
        try:
            data = get(url)
        except Exception as e:
            log('ntd energy failed', url, repr(e)); continue
        if b'50118' not in data:
            log('ntd energy: no Metra rows in', url, len(data)); continue
        if len(data) > 5_000_000:   # whole dataset: keep only our agencies' rows plus the header
            lines = data.splitlines(); data = b'\n'.join([lines[0]] + [l for l in lines[1:] if b'50118' in l or b'50066' in l])
        open(os.path.join(OUT, 'ntd_energy.csv'), 'wb').write(data)
        SOURCES['files']['ntd_energy'] = {'url': url, 'page': 'https://data.transportation.gov/d/8ehq-7his', 'bytes': len(data)}
        log('ntd energy', url, len(data)); found = True; break
    if not found:
        try:
            u = 'https://www.transit.dot.gov/sites/fta.dot.gov/files/2025-10/2024%20Energy%20Consumption_250812.xlsx'
            data = get(u); open(os.path.join(OUT, 'ntd_energy_2024.xlsx'), 'wb').write(data)
            SOURCES['files']['ntd_energy'] = {'url': u, 'bytes': len(data)}; log('ntd energy xlsx', len(data))
        except Exception as e:
            log('ntd energy xlsx failed', repr(e))


if __name__ == '__main__':
    steps = sys.argv[1:] or ['cta', 'metra', 'blocks', 'bus', 'metracounts', 'energy']
    for s in steps:
        try:
            if s == 'cta':
                gtfs('cta', 'https://www.transitchicago.com/downloads/sch_data/google_transit.zip')
            elif s == 'metra':
                gtfs('metra', 'https://schedules.metrarail.com/gtfs/schedule.zip')
            elif s == 'blocks':
                blocks()
            elif s == 'bus':
                bus_ridership()
            elif s == 'metracounts':
                metra_counts()
            elif s == 'energy':
                ntd_energy()
        except Exception as e:
            import traceback; log('STEP FAILED', s, traceback.format_exc())
            SOURCES['files'][s + '_error'] = repr(e)
    old = {}
    p = os.path.join(OUT, 'sources.json')
    if os.path.exists(p):
        old = json.load(open(p)).get('files', {})
    for st in steps:
        old.pop(st + '_error', None)
    old.update(SOURCES['files'])
    SOURCES['files'] = old
    json.dump(SOURCES, open(p, 'w'), indent=1)
    open(os.path.join(OUT, 'fetch_log.txt'), 'w').write('\n'.join(LOG) + '\n')
