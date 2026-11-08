"""Download what the "What can I build on my lot?" tool needs that the parcel fetch doesn't have (runs in GitHub
Actions; the cloud workspace can't reach datacatalog.cookcountyil.gov):
  tools/raw/cook_addr_chi.csv.gz   Assessor Parcel Addresses (3723-97qp), latest year, Chicago: pin, property address, zip
  tools/raw/cook_comm_chi.csv.gz   Assessor Commercial Valuation Data (csik-bsws), latest year: pins and land square
                                   feet for commercial and big apartment parcels (not in the residential characteristics)
  tools/raw/cook_comm_columns.json that dataset's column list"""
import urllib.request, urllib.parse, json, csv, io, gzip, time, os, sys
OUT = os.path.join(os.path.dirname(__file__), 'raw'); os.makedirs(OUT, exist_ok=True)
B = 'https://datacatalog.cookcountyil.gov'

def get(url, tries=6):
    for t in range(tries):
        try: return urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': 'fixchicagohousing.com'}), timeout=300).read()
        except Exception as e: print('retry', t, e, flush=True); time.sleep(10 * (t + 1))
    raise RuntimeError('failed ' + url)

def pull(ds, select, where, out, order='pin'):
    rows, header, off = [], None, 0
    while True:
        q = urllib.parse.urlencode({'$select': select, '$where': where, '$order': order, '$limit': 50000, '$offset': off})
        r = list(csv.reader(io.StringIO(get(f'{B}/resource/{ds}.csv?{q}').decode('utf-8'))))
        if header is None: header = r[0]
        rows += r[1:]; print(ds, off, len(r) - 1, flush=True)
        if len(r) - 1 < 50000: break
        off += 50000
    with gzip.open(os.path.join(OUT, out), 'wt', newline='') as f:
        w = csv.writer(f); w.writerow(header); w.writerows(rows)
    print(out, len(rows), flush=True)

def cols(ds):
    c = json.loads(get(f'{B}/api/views/{ds}/columns.json'))
    return [x['fieldName'] for x in c], c

# 1. addresses
names, _ = cols('3723-97qp'); print('addr columns', names, flush=True)
yr = json.loads(get(f'{B}/resource/3723-97qp.json?$select=max(year)%20as%20y'))[0]['y']
want = [n for n in ('pin', 'prop_address_full', 'prop_address_city_name', 'prop_address_zipcode_1') if n in names]
pull('3723-97qp', ','.join(want), f"year={yr} AND upper(prop_address_city_name)='CHICAGO'", 'cook_addr_chi.csv.gz')

# 2. commercial land area (best effort: the column names are discovered, and a failure doesn't stop step 1's file)
try:
    names, raw = cols('csik-bsws')
    json.dump([{k: c.get(k) for k in ('fieldName', 'name', 'description')} for c in raw], open(os.path.join(OUT, 'cook_comm_columns.json'), 'w'), indent=1)
    print('comm columns', names, flush=True)
    pinc = next(n for n in names if n in ('keypin', 'pins', 'pin'))
    land = [n for n in names if 'land' in n and ('sf' in n or 'sq' in n)]
    extra = [n for n in names if n in ('pins', 'keypin', 'year', 'class', 'classes', 'tot_units', 'apts', 'units', 'yearbuilt', 'year_built', 'bldgsf', 'property_type_use', 'township')]
    sel = list(dict.fromkeys([pinc] + extra + land))
    ycol = 'year' if 'year' in names else None
    where = '1=1'
    if ycol:
        y = json.loads(get(f'{B}/resource/csik-bsws.json?$select=max(year)%20as%20y'))[0]['y']; where = f"year={y}"
    pull('csik-bsws', ','.join(sel), where, 'cook_comm_chi.csv.gz', order=pinc)
except Exception as e:
    print('commercial step failed:', e, file=sys.stderr)
