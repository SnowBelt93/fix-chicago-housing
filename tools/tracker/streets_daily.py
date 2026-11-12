"""Daily numbers for Progress → Streets and Progress → Affordable (run by the tracker workflow after fetch.py).

Writes two small files, keeping the last ones if a download fails:
  tracker/streets.json  traffic deaths (the city's reviewed Vision Zero list), people seriously hurt (police crash
                        reports), potholes filled and how long a repair takes, speed and red-light camera violations.
                        Each series is by year, plus this year to date and the same dates a year earlier.
  tracker/affordable.json  the city's Affordable Rental Housing Developments list: one row per building with only
                        [homes, property type, latitude, longitude] (no building names, addresses, phones or managers),
                        plus the date the city last changed the list. tools/progress/build.py counts it by ward.

Standard library only. `python3 tools/tracker/streets_daily.py --raw DIR` runs the same math on files saved earlier by
tools/record/fetch.py (vz_deaths, crashes_2018_21 + crashes_2022_on, potholes, speed_month, redlight_month, s6ha-ppgi)."""
import urllib.request, urllib.parse, csv, io, json, os, gzip, time, sys, datetime, collections, statistics
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
UA = {'User-Agent': 'fixchicagohousing.com tracker (github.com/SnowBelt93/fix-chicago-housing)'}
PORTAL = 'https://data.cityofchicago.org/resource/'

def soda(ds, select, where=None, group=None, order=None, limit=2000000):
    q = {'$select': select, '$limit': limit}
    if where: q['$where'] = where
    if group: q['$group'] = group
    if order: q['$order'] = order
    url = PORTAL + ds + '.csv?' + urllib.parse.urlencode(q)
    for t in range(4):
        try: return list(csv.DictReader(io.StringIO(urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=600).read().decode('utf-8'))))
        except Exception as e: print('retry', ds, t, e, flush=True); time.sleep(15 * (t + 1))
    raise RuntimeError('download failed: ' + ds)

def rawcsv(d, name):
    with gzip.open(os.path.join(d, name + '.csv.gz'), 'rt', encoding='utf-8') as fh: return list(csv.DictReader(fh))

def day(s): return datetime.date.fromisoformat(s[:10])
def num(s):
    try: return float(s or 0)
    except ValueError: return 0.0

def by_year(rows, date_key, val=None, thru=None):
    """Totals by year, plus this year to `thru` and last year to the same month and day."""
    Y = collections.Counter(); cur = prev = 0
    thru = thru or max(day(r[date_key]) for r in rows if r.get(date_key))
    last = thru.replace(year=thru.year - 1) if not (thru.month == 2 and thru.day == 29) else thru.replace(year=thru.year - 1, day=28)
    for r in rows:
        if not r.get(date_key): continue
        d = day(r[date_key]); v = num(r[val]) if val else 1
        if d > thru: continue
        Y[d.year] += v
        if d.year == thru.year: cur += v
        elif d.year == thru.year - 1 and d <= last: prev += v
    return {'years': {str(y): round(Y[y]) for y in sorted(Y)}, 'through': thru.isoformat(), 'ytd': round(cur), 'ytd_prev': round(prev)}

def streets(get):
    out = {}
    vz = get('vz_deaths')
    out['deaths'] = by_year([r for r in vz if r['crash_date'] >= '2019'], 'crash_date')
    cr, thru = get('crashes')
    out['serious'] = by_year([r for r in cr if r['crash_date'] >= '2019'], 'crash_date', 'injuries_incapacitating', thru)
    out['crash_deaths'] = by_year([r for r in cr if r['crash_date'] >= '2019'], 'crash_date', 'injuries_fatal', thru)
    ph = [r for r in get('potholes') if r.get('completion_date', '') >= '2019']
    out['potholes'] = by_year(ph, 'completion_date', 'number_of_potholes_filled_on_block')
    t = day(out['potholes']['through']); since = t - datetime.timedelta(days=365)
    waits = sorted((day(r['completion_date']) - day(r['request_date'])).days for r in ph
                   if r.get('request_date') and day(r['completion_date']) > since and day(r['completion_date']) >= day(r['request_date']))
    if waits:
        out['pothole_wait'] = {'median_days': statistics.median(waits), 'share_over_7_weeks': round(sum(w > 49 for w in waits) / len(waits), 3),
                               'p90_days': waits[int(0.9 * (len(waits) - 1))], 'repairs': len(waits), 'since': since.isoformat()}
    for k in ('speed', 'redlight'):
        rows = get(k + '_month')
        out[k] = {'years': {}}
        Y = collections.Counter(); last = ''
        for r in rows:
            v = num(r['violations']); Y[int(r['month'][:4])] += v
            if v > 0: last = max(last, r['month'][:7])
        out[k] = {'years': {str(y): round(Y[y]) for y in sorted(Y)}, 'through': last}
    return out

def affordable(get):
    rows, updated = get('affordable')
    keep = []
    for r in rows:
        try: keep.append([int(num(r.get('units') or r.get('Units'))), (r.get('property_type') or r.get('Property Type') or '').strip(),
                          round(float(r.get('latitude') or r.get('Latitude')), 6), round(float(r.get('longitude') or r.get('Longitude')), 6)])
        except (TypeError, ValueError): keep.append([int(num(r.get('units') or r.get('Units'))), (r.get('property_type') or r.get('Property Type') or '').strip(), None, None])
    return {'updated': updated, 'columns': ['homes', 'type', 'lat', 'lon'], 'rows': keep}

def live(name):
    if name == 'vz_deaths': return soda('gzaz-isa6', 'crash_date', "crash_date >= '2019-01-01'")
    if name == 'crashes':
        rows = soda('85ca-t3if', 'crash_date,injuries_fatal,injuries_incapacitating', "crash_date >= '2019-01-01' AND (injuries_incapacitating > 0 OR injuries_fatal > 0)")
        thru = soda('85ca-t3if', 'max(crash_date) as m')[0]['m']
        return rows, day(thru)
    if name == 'potholes': return soda('wqdh-9gek', 'request_date,completion_date,number_of_potholes_filled_on_block', "completion_date >= '2019-01-01'")
    if name in ('speed_month', 'redlight_month'):
        return soda({'speed_month': 'hhkd-xvj4', 'redlight_month': 'spqx-js37'}[name], 'date_trunc_ym(violation_date) as month, sum(violations) as violations',
                    "violation_date >= '2019-01-01'", group='month', order='month')
    if name == 'affordable':
        rows = soda('s6ha-ppgi', 'property_type,units,latitude,longitude')
        meta = json.loads(urllib.request.urlopen(urllib.request.Request('https://data.cityofchicago.org/api/views/s6ha-ppgi.json', headers=UA), timeout=120).read())
        return rows, datetime.datetime.utcfromtimestamp(meta.get('rowsUpdatedAt') or meta.get('viewLastModified')).date().isoformat()

def from_raw(d):
    def get(name):
        if name == 'crashes':
            rows = rawcsv(d, 'crashes_2018_21') + rawcsv(d, 'crashes_2022_on')
            return [r for r in rows if num(r['injuries_incapacitating']) or num(r['injuries_fatal'])], max(day(r['crash_date']) for r in rows)
        if name == 'affordable': return rawcsv(d, 's6ha-ppgi'), 'saved copy'
        return rawcsv(d, name)
    return get

if __name__ == '__main__':
    get = from_raw(sys.argv[sys.argv.index('--raw') + 1]) if '--raw' in sys.argv else live
    outdir = sys.argv[sys.argv.index('--out') + 1] if '--out' in sys.argv else os.path.join(ROOT, 'tracker')
    os.makedirs(outdir, exist_ok=True)
    for fn, name in ((streets, 'streets'), (affordable, 'affordable')):
        try:
            res = fn(get)
            if name == 'affordable' and len(res['rows']) < 300: raise RuntimeError(f'list looked short ({len(res["rows"])} rows)')
            if name == 'streets' and len(res['deaths']['years']) < 5: raise RuntimeError('deaths looked short')
            json.dump(res, open(os.path.join(outdir, name + '.json'), 'w'), separators=(',', ':'))
            print(name, 'ok', {k: (v.get('through'), v.get('ytd'), v.get('ytd_prev')) for k, v in res.items() if isinstance(v, dict) and 'years' in v} if name == 'streets' else len(res['rows']))
        except Exception as e:
            print(name, 'failed; kept the last file:', e)
