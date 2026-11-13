"""Daily numbers for Progress → Rents and prices (run by the tracker workflow). Writes tracker/rents.json, keeping the
last file if a download fails.

  rent   Zillow Observed Rent Index for the city of Chicago (all homes, smoothed, seasonally adjusted), by month since 2015.
         Zillow publishes it free with credit to Zillow.
  sales  Cook County Assessor parcel sales in Chicago's eight townships since 2019 (dataset wvhk-k5uv): median price by
         year for houses, condos and 2- to 6-flats. Only price, date and class are read; sales under $10,000, multi-parcel
         sales and sales the Assessor flags (same property sold within a year, unusual deeds) are left out, as on the page.
Standard library only."""
import urllib.request, urllib.parse, csv, io, json, os, time, datetime, statistics, collections
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
UA = {'User-Agent': 'fixchicagohousing.com tracker (github.com/SnowBelt93/fix-chicago-housing)'}
ZORI = 'https://files.zillowstatic.com/research/public_csvs/zori/City_zori_uc_sfrcondomfr_sm_sa_month.csv'
ZORI2 = 'https://files.zillowstatic.com/research/public_csvs/zori/City_zori_uc_sfrcondomfr_sm_month.csv'
SALES = 'https://datacatalog.cookcountyil.gov/resource/wvhk-k5uv.json'
TOWNS = ('70', '71', '72', '73', '74', '75', '76', '77')
HOUSE = {'202', '203', '204', '205', '206', '207', '208', '209', '210', '234', '278', '295'}
CONDO = {'299'}
FLATS = {'211', '212'}

def get(url, timeout=600):
    for t in range(4):
        try: return urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout).read()
        except Exception as e: print('retry', url[:80], t, e, flush=True); time.sleep(15 * (t + 1))
    raise RuntimeError('download failed: ' + url)

def rent():
    for u in (ZORI, ZORI2):
        try: raw = get(u).decode('utf-8')
        except RuntimeError: continue
        for r in csv.DictReader(io.StringIO(raw)):
            if r.get('RegionName') == 'Chicago' and r.get('State') == 'IL':
                m = {k[:7]: round(float(v)) for k, v in r.items() if k[:2] in ('19', '20') and len(k) >= 7 and v}
                return {'series': {k: m[k] for k in sorted(m) if k >= '2015'}, 'source': u.rsplit('/', 1)[-1]}
    raise RuntimeError('Chicago not found in the Zillow file')

def sales():
    cols = 'pin,sale_date,sale_price,class,township_code,is_multisale,sale_filter_less_than_10k,sale_filter_same_sale_within_365,sale_filter_deed_type'
    where = "sale_date >= '2019-01-01T00:00:00' AND township_code in (" + ','.join(f"'{t}'" for t in TOWNS) + ')'
    rows, off = [], 0
    while True:
        q = {'$select': cols, '$where': where, '$limit': 50000, '$offset': off, '$order': 'sale_date'}
        d = json.loads(get(SALES + '?' + urllib.parse.urlencode(q)))
        rows += d; off += len(d)
        if len(d) < 50000: break
    tru = lambda v: str(v).lower() in ('true', '1')
    P = collections.defaultdict(list); last = ''
    for r in rows:
        try: price = float(r.get('sale_price') or 0)
        except ValueError: continue
        if price < 10000 or tru(r.get('is_multisale')) or tru(r.get('sale_filter_less_than_10k')) or tru(r.get('sale_filter_same_sale_within_365')) or tru(r.get('sale_filter_deed_type')): continue
        c = str(r.get('class', '')).replace('-', '')[:3]; kind = 'house' if c in HOUSE else 'condo' if c in CONDO else 'flats' if c in FLATS else None
        if not kind: continue
        y = r['sale_date'][:4]; P[(kind, y)].append(price); last = max(last, r['sale_date'][:10])
    med = {k: {} for k in ('house', 'condo', 'flats')}; n = {k: {} for k in med}
    for (k, y), v in P.items(): med[k][y] = round(statistics.median(v), -3); n[k][y] = len(v)
    return {'median': med, 'count': n, 'through': last}

if __name__ == '__main__':
    out = os.path.join(ROOT, 'tracker', 'rents.json')
    old = json.load(open(out)) if os.path.exists(out) else {}
    res = dict(old)
    for k, fn in (('rent', rent), ('sales', sales)):
        try: res[k] = fn(); print(k, 'ok', flush=True)
        except Exception as e: print(k, 'failed, keeping the last one:', e, flush=True)
    res['updated'] = datetime.date.today().isoformat()
    if 'rent' in res:
        s = res['rent']['series']; ks = sorted(s); print('rent latest', ks[-1], s[ks[-1]])
    if 'sales' in res: print('sales', {k: res['sales']['median'][k].get('2025') for k in res['sales']['median']}, res['sales']['through'])
    json.dump(res, open(out, 'w'), separators=(',', ':'))
