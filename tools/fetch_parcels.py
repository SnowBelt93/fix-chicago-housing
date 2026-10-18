"""Download Cook County Assessor parcel data for Chicago (runs in GitHub Actions; the cloud workspace can't reach
datacatalog.cookcountyil.gov). Used by tools/check_illegal.py to test the game's "illegal to build today" flags
against real lot sizes and apartment counts instead of estimates.
  tools/raw/cook_parcels_chi.csv.gz   Parcel Universe (nj4t-kc8j): pin, class, lat, lon, township, latest year
  tools/raw/cook_chars_chi.csv.gz     Single and Multi-Family Improvement Characteristics (x54s-btds), latest year:
                                      pin, class, land square feet, apartments, building square feet, year built, ...
  tools/raw/cook_chars_columns.json   that dataset's column list (for reference)"""
import urllib.request, urllib.parse, json, csv, io, gzip, time, os
OUT = os.path.join(os.path.dirname(__file__), 'raw'); os.makedirs(OUT, exist_ok=True)
B = 'https://datacatalog.cookcountyil.gov'
CHI_TWP = ['Hyde Park', 'Jefferson', 'Lake', 'Lake View', 'North Chicago', 'Rogers Park', 'South Chicago', 'West Chicago']
CHI_CODES = ['70', '71', '72', '73', '74', '75', '76', '77']

def get(url, tries=6):
    for t in range(tries):
        try: return urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': 'fixchicagohousing.com'}), timeout=300).read()
        except Exception as e: print('retry', t, e, flush=True); time.sleep(10 * (t + 1))
    raise SystemExit('failed ' + url)

def pull(ds, select, where, out):
    rows, header, off = [], None, 0
    while True:
        q = urllib.parse.urlencode({'$select': select, '$where': where, '$order': 'pin', '$limit': 50000, '$offset': off})
        r = list(csv.reader(io.StringIO(get(f'{B}/resource/{ds}.csv?{q}').decode('utf-8'))))
        if header is None: header = r[0]
        rows += r[1:]; print(ds, off, len(r) - 1, flush=True)
        if len(r) - 1 < 50000: break
        off += 50000
    with gzip.open(os.path.join(OUT, out), 'wt', newline='') as f:
        w = csv.writer(f); w.writerow(header); w.writerows(rows)
    print(out, len(rows))

# Parcel universe
yr = json.loads(get(f'{B}/resource/nj4t-kc8j.json?$select=max(year)%20as%20y'))[0]['y']
pull('nj4t-kc8j', 'pin,class,lat,lon,township_name,year', f"year={yr} AND township_name in(" + ','.join(f"'{t}'" for t in CHI_TWP) + ')', 'cook_parcels_chi.csv.gz')

# Characteristics: discover column names first
cols = json.loads(get(f'{B}/api/views/x54s-btds/columns.json'))
names = [c['fieldName'] for c in cols]
json.dump([{k: c.get(k) for k in ('fieldName', 'name', 'description')} for c in cols], open(os.path.join(OUT, 'cook_chars_columns.json'), 'w'), indent=1)
print('columns', names)
want = [n for n in names if n in ('pin', 'year', 'card', 'class', 'township_code', 'char_land_sf', 'char_apts', 'char_bldg_sf', 'char_yrblt',
                                    'char_type_resd', 'char_ncu', 'char_use', 'char_beds', 'char_rooms', 'char_cnst_qlty', 'char_ext_wall')]
yc = json.loads(get(f'{B}/resource/x54s-btds.json?$select=max(year)%20as%20y'))[0]['y']
where = f"year={yc}"
if 'township_code' in names: where += " AND township_code in(" + ','.join(f"'{c}'" for c in CHI_CODES) + ')'
pull('x54s-btds', ','.join(want), where, 'cook_chars_chi.csv.gz')
