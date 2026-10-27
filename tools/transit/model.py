#!/usr/bin/env python3
"""Fit the transit tool's ridership models from real Chicago data and write the browser's data files.

Inputs (tools/raw/transit, from fetch.py; tools/raw/cta_l_daily_2025.csv from the housing game's data fetch):
  blocks.csv.gz          2020 Census blocks: people, homes, jobs (LODES)
  cta_stops.csv.gz       stops and stations with routes and weekday departures (CTA GTFS)
  cta_routes.json        routes; cta_bus_ridership.csv  average 2025 weekday boardings per bus route

Models (log-linear, least squares):
  Rail station:  ln(weekday entries) ~ ln(people within 1/2 mile) + ln(jobs within 1/2 mile) + ln(weekday departures)
                 + terminal + transfer + ln(miles to the Loop)
  Bus route:     ln(weekday boardings per mile) ~ ln(people per mile within 1/4 mile of stops) + ln(jobs per mile ...)
                 + ln(weekday trips)

Prints fit statistics; writes transit/data/model.json (coefficients + stats) for the page.
"""
import collections, csv, gzip, json, math, os, sys
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RAW = os.path.join(ROOT, 'tools', 'raw', 'transit')
LOOP = (41.8819, -87.6278)  # State & Madison, the address grid's zero point
MI = 1609.34


def xy(lat, lon):
    return ((lon - LOOP[1]) * 111320 * math.cos(math.radians(41.85)), (lat - LOOP[0]) * 110574)


class Grid:
    """Blocks bucketed into 200 m cells for fast walk-shed sums."""
    def __init__(self, pts, cell=200):
        self.cell, self.g = cell, collections.defaultdict(list)
        for p in pts:
            self.g[(int(p[0] // cell), int(p[1] // cell))].append(p)

    def near(self, x, y, r):
        c, out = self.cell, []
        for i in range(int((x - r) // c), int((x + r) // c) + 1):
            for j in range(int((y - r) // c), int((y + r) // c) + 1):
                for p in self.g.get((i, j), ()):
                    if (p[0] - x) ** 2 + (p[1] - y) ** 2 <= r * r:
                        out.append(p)
        return out


def load_blocks():
    pts = []
    for r in csv.DictReader(gzip.open(os.path.join(RAW, 'blocks.csv.gz'), 'rt')):
        x, y = xy(float(r['lat']), float(r['lon']))
        pts.append((x, y, int(r['people']), int(r['jobs']), int(r['homes']), r['geoid']))
    return pts


def fit(X, y, names):
    A = np.column_stack([np.ones(len(y))] + X)
    coef, *_ = np.linalg.lstsq(A, y, rcond=None)
    pred = A @ coef
    ss = ((y - y.mean()) ** 2).sum()
    r2 = 1 - ((y - pred) ** 2).sum() / ss
    resid = y - pred
    return dict(zip(['const'] + names, [round(float(c), 4) for c in coef])), round(float(r2), 3), float(np.median(np.abs(resid))), pred


def main():
    blocks = load_blocks()
    grid = Grid(blocks)
    print('blocks', len(blocks), 'people', sum(b[2] for b in blocks), 'jobs', sum(b[3] for b in blocks), file=sys.stderr)
    stops = list(csv.DictReader(gzip.open(os.path.join(RAW, 'cta_stops.csv.gz'), 'rt')))
    routes = {r['id']: r for r in json.load(open(os.path.join(RAW, 'cta_routes.json')))}
    rail_ids = {k for k, r in routes.items() if r['type'] == 1}

    # rail stations: parent stations (location_type 1) with 2025 weekday entries
    rides = collections.defaultdict(list)
    for r in csv.DictReader(open(os.path.join(ROOT, 'tools', 'raw', 'cta_l_daily_2025.csv'))):
        if r['daytype'] == 'W':
            rides[r['station_id']].append(float(r['rides']))
    st_rows = []
    cand = []
    for s in stops:
        if s['location_type'] != '1':
            continue
        rs = set(s['routes'].split()) & rail_ids
        if not rs:
            continue
        x, y = xy(float(s['lat']), float(s['lon']))
        cand.append(dict(id=s['stop_id'], name=s['name'], x=x, y=y, lines=len(rs), lineset=rs, deps=int(s['weekday_departures'])))
    # catchments: each block goes to its nearest station within 3/4 mile, so close-together stations split demand
    sgrid = Grid([(c['x'], c['y'], i) for i, c in enumerate(cand)], cell=400)
    for c in cand:
        c['pop'] = c['jobs'] = 0
    for b in blocks:
        near = sgrid.near(b[0], b[1], 0.75 * MI)
        if near:
            k = min(near, key=lambda p: (p[0] - b[0]) ** 2 + (p[1] - b[1]) ** 2)[2]
            cand[k]['pop'] += b[2]; cand[k]['jobs'] += b[3]
    busstops = [xy(float(s['lat']), float(s['lon'])) + (s['routes'],) for s in stops if s['location_type'] == '0']
    bgrid = Grid([(p[0], p[1], p[2]) for p in busstops], cell=200)
    line_jobs = collections.Counter()
    for c in cand:
        for l in c['lineset']:
            line_jobs[l] += c['jobs']
    for c in cand:
        rset = set()
        for p in bgrid.near(c['x'], c['y'], 0.25 * MI):
            rset |= set(p[2].split()) - rail_ids
        c['bus'] = len(rset)
        c['bustrips'] = sum(routes[r]['weekday_trips'] for r in rset if r in routes)
        c['acc'] = sum(line_jobs[l] for l in c['lineset'])
        if c['id'] in rides:
            c['rides'] = float(np.mean(rides[c['id']])); c['loop'] = math.hypot(c['x'], c['y']) / MI
            st_rows.append(c)
    acc = json.load(open(os.path.join(RAW, 'station_access.json')))
    for r in st_rows:
        r['acc45'] = acc.get(r['id'], 0)
    TERM = {'Howard', '95th/Dan Ryan', "O'Hare", 'Forest Park', 'Kimball', 'Linden', 'Dempster-Skokie', 'Harlem/Lake',
            'Ashland/63rd', 'Cottage Grove', 'Midway', '54th/Cermak'}
    for r in st_rows:
        base = r['name'].split(' (')[0]
        r['term'] = 1.0 if base in TERM else 0.0
        r['air'] = 1.0 if base in ("O'Hare", 'Midway') else 0.0
    SERVICE_E = float(os.environ.get('SERVICE_E', '0.5'))   # ridership change per 1% more trains (assumption; see sources.md)
    y = np.log([r['rides'] for r in st_rows]) - SERVICE_E * np.log([max(r['deps'], 1) for r in st_rows])
    X = [np.log([r['pop'] + 500 for r in st_rows]), np.log([r['jobs'] + 500 for r in st_rows]),
         np.array([r['term'] for r in st_rows]), np.array([r['air'] for r in st_rows]),
         np.array([1.0 if r['lines'] > 1 else 0.0 for r in st_rows]), np.log([r['loop'] + 1 for r in st_rows]),
         np.log([r['bustrips'] + 50 for r in st_rows]), np.log([r['acc45'] + 1000 for r in st_rows])]
    names = ['ln_pop', 'ln_jobs', 'terminal', 'airport', 'transfer', 'ln_loop_mi', 'ln_bus_trips', 'ln_jobs_45min']
    rail_coef, rail_r2, rail_mad, rail_pred = fit(X, y, names)
    print('RAIL stations', len(st_rows), 'R2', rail_r2, 'median abs log error', round(rail_mad, 3), rail_coef, file=sys.stderr)
    res = np.sort(y - rail_pred)
    rail_band = [round(float(res[int(len(res) * 0.2)]), 3), round(float(res[int(len(res) * 0.8)]), 3)]
    # leave-one-line-out: refit without each line's stations, predict that line's total
    for L in sorted(rail_ids):
        idx = [i for i, r in enumerate(st_rows) if L in r['lineset'] and len(r['lineset']) == 1]
        if len(idx) < 5:
            continue
        keep = [i for i in range(len(st_rows)) if i not in set(idx)]
        A = np.column_stack([np.ones(len(y))] + X)
        cf, *_ = np.linalg.lstsq(A[keep], y[keep], rcond=None)
        pr = np.exp(A[idx] @ cf + SERVICE_E * np.log([max(st_rows[i]['deps'], 1) for i in idx])).sum(); ac = sum(st_rows[i]['rides'] for i in idx)
        print(f'   line {L}: {len(idx)} own stations, actual {ac:,.0f}, predicted without it {pr:,.0f} ({pr / ac:.2f}x)', file=sys.stderr)
    # leave-one-station-out: how often does the real number fall inside the shown range?
    A = np.column_stack([np.ones(len(y))] + X); inside = 0; loo = {}
    for i in range(len(y)):
        keep = [k for k in range(len(y)) if k != i]
        cf, *_ = np.linalg.lstsq(A[keep], y[keep], rcond=None)
        res_i = y[i] - A[i] @ cf
        inside += rail_band[0] <= res_i <= rail_band[1]
        loo[st_rows[i]['name']] = (round(st_rows[i]['rides']), round(math.exp(A[i] @ cf + SERVICE_E * math.log(max(st_rows[i]['deps'], 1)))))
    rail_cover = round(inside / len(y), 3)
    print('   leave-one-out: actual inside the range for', inside, 'of', len(y), 'stations', file=sys.stderr)
    for k, v in loo.items():
        if k.startswith('Damen') or k.startswith('Washington/Wabash') or k.startswith('Morgan') or k.startswith('Cermak-McCormick'):
            print('   LOO', k, 'actual', v[0], 'predicted', v[1], file=sys.stderr)
    worst = sorted(zip(st_rows, rail_pred + SERVICE_E * np.log([max(r['deps'], 1) for r in st_rows])), key=lambda t: abs(math.log(t[0]['rides']) - t[1]), reverse=True)[:8]
    for r, p in worst:
        print('   off:', r['name'], round(r['rides']), 'pred', round(math.exp(p)), 'pop', r['pop'], 'jobs', r['jobs'], file=sys.stderr)

    # bus routes: stops served, weekday boardings 2025
    brides = {}
    for r in csv.DictReader(open(os.path.join(RAW, 'cta_bus_ridership.csv'))):
        brides[r['route']] = float(r['avg_rides'])
    route_stops = collections.defaultdict(list)
    for s in stops:
        if s['location_type'] == '0':
            for rid in s['routes'].split():
                if rid not in rail_ids:
                    route_stops[rid].append(xy(float(s['lat']), float(s['lon'])))
    shapes = json.load(gzip.open(os.path.join(RAW, 'cta_shapes.json.gz'), 'rt'))
    bus_rows = []
    for rid, pts in route_stops.items():
        r = routes.get(rid)
        if not r or r['short'] not in brides or rid not in shapes:
            continue
        sh = max(shapes[rid], key=lambda d: len(d['pts']))['pts']
        length = sum(math.hypot(*(np.subtract(xy(b[1], b[0]), xy(a[1], a[0])))) for a, b in zip(sh, sh[1:])) / MI
        if length < 1:
            continue
        seen, pop, jobs = set(), 0, 0
        for (x, y0) in pts:
            for b in grid.near(x, y0, 0.25 * MI):
                if b[5] not in seen:
                    seen.add(b[5]); pop += b[2]; jobs += b[3]
        bus_rows.append(dict(id=rid, short=r['short'], len=length, pop=pop, jobs=jobs, trips=r['weekday_trips'],
                             rides=brides[r['short']]))
    bus_rows = [b for b in bus_rows if b['trips'] > 0 and b['rides'] > 0]
    yb = np.log([b['rides'] / b['len'] for b in bus_rows])
    Xb = [np.log([b['pop'] / b['len'] + 100 for b in bus_rows]), np.log([b['jobs'] / b['len'] + 100 for b in bus_rows]),
          np.log([b['trips'] for b in bus_rows])]
    bus_coef, bus_r2, bus_mad, _ = fit(Xb, yb, ['ln_pop_per_mi', 'ln_jobs_per_mi', 'ln_trips'])
    ybs = yb - SERVICE_E * np.log([b['trips'] for b in bus_rows])
    bus_fixed, r2f, madf, predf = fit(Xb[:2], ybs, ['ln_pop_per_mi', 'ln_jobs_per_mi'])
    rb = np.sort(ybs - predf)
    print('BUS with fixed service effect', SERVICE_E, 'R2', r2f, 'mad', round(madf, 3), bus_fixed, file=sys.stderr)
    print('BUS routes', len(bus_rows), 'R2', bus_r2, 'median abs log error', round(bus_mad, 3), bus_coef, file=sys.stderr)

    out = dict(rail=dict(service_elasticity=SERVICE_E, coef=rail_coef, r2=rail_r2, band_20_80=rail_band, loo_inside_band=rail_cover, median_abs_log_error=round(rail_mad, 3), n=len(st_rows),
                         data='CTA L weekday entries 2025 (Chicago Data Portal), Census 2020 blocks, LODES jobs, CTA GTFS'),
               bus=dict(service_elasticity=SERVICE_E, coef=bus_fixed, r2=r2f, median_abs_log_error=round(madf, 3),
                        band_20_80=[round(float(rb[int(len(rb) * 0.2)]), 3), round(float(rb[int(len(rb) * 0.8)]), 3)],
                        free_fit=dict(coef=bus_coef, r2=bus_r2), n=len(bus_rows),
                        data='CTA bus weekday boardings 2025 (Chicago Data Portal), Census 2020 blocks, LODES jobs, CTA GTFS'))
    os.makedirs(os.path.join(ROOT, 'transit', 'data'), exist_ok=True)
    json.dump(out, open(os.path.join(ROOT, 'transit', 'data', 'model.json'), 'w'), indent=1)
    print(json.dumps(out, indent=1))


if __name__ == '__main__':
    main()
