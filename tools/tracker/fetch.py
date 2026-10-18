"""Download the raw data for the housing production tracker (runs in GitHub Actions; the cloud
workspace can't reach these hosts). Writes to tools/raw/tracker/:
  permits_nc.csv.gz    every 'PERMIT - NEW CONSTRUCTION' permit since 2006 (City of Chicago, ydr8-5enu), all columns
  elms_zoning.json.gz  City Clerk eLMS matters that match zoning map amendments / planned developments
  elms_sample.json     a few full matter records (actions, attachments) for inspection
  elms_facets.json     facet values (types, statuses) from the eLMS search endpoint
  bps_chicago.csv      Census Building Permits Survey, annual units authorized in Chicago city, 2006 on
Standard library only."""
import urllib.request, urllib.parse, json, csv, io, gzip, time, os, datetime, sys
OUT = os.path.join(os.path.dirname(__file__), '..', 'raw', 'tracker'); os.makedirs(OUT, exist_ok=True)
UA = {'User-Agent': 'fixchicagohousing.com tracker (github.com/SnowBelt93/fix-chicago-housing)'}

def get(url, tries=5, timeout=300):
    for t in range(tries):
        try:
            return urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout).read()
        except urllib.error.HTTPError as e:
            if e.code == 404: return None
            print('retry', t, url[:120], e, flush=True); time.sleep(5 * (t + 1))
        except Exception as e:
            print('retry', t, url[:120], e, flush=True); time.sleep(5 * (t + 1))
    raise SystemExit('failed: ' + url)

# 1) permits
base = 'https://data.cityofchicago.org/resource/ydr8-5enu.csv'
where = "permit_type='PERMIT - NEW CONSTRUCTION' AND issue_date >= '2006-01-01T00:00:00'"
rows, header, off = [], None, 0
while True:
    q = urllib.parse.urlencode({'$where': where, '$order': 'id', '$limit': 50000, '$offset': off})
    r = list(csv.reader(io.StringIO(get(base + '?' + q).decode('utf-8'))))
    if header is None: header = r[0]
    body = r[1:]; rows += body; print('permits', len(body), 'at', off, flush=True)
    if len(body) < 50000: break
    off += 50000
with gzip.open(os.path.join(OUT, 'permits_nc.csv.gz'), 'wt', newline='') as f:
    w = csv.writer(f); w.writerow(header); w.writerows(rows)
print('permits total', len(rows), 'columns', header)

# 2) City Clerk eLMS (Legislation API, beta): https://api.chicityclerkelms.chicago.gov/swagger.json
E = 'https://api.chicityclerkelms.chicago.gov'
def ej(path, **params):
    b = get(E + path + ('?' + urllib.parse.urlencode(params) if params else ''))
    return json.loads(b) if b else None
facets = ej('/search', top='1')
json.dump(facets, open(os.path.join(OUT, 'elms_facets.json'), 'w'), indent=1)
matters, seen = [], set()
for term in ['"Zoning Reclassification"', '"Residential-Business Planned Development"', '"Residential Planned Development"', '"Planned Development"']:
    skip = 0
    while True:
        res = ej('/search', search=term, filter="introductionDate ge 2013-01-01T00:00:00Z", top='500', skip=skip, sort='introductionDate desc')
        data = (res or {}).get('data') or []
        for m in data:
            if m.get('matterId') not in seen:
                seen.add(m.get('matterId')); m['_term'] = term; matters.append(m)
        print('elms', term, skip, len(data), (res or {}).get('meta'), flush=True)
        if len(data) < 500 or skip > 40000: break
        skip += 500; time.sleep(0.5)
with gzip.open(os.path.join(OUT, 'elms_zoning.json.gz'), 'wt') as f: json.dump(matters, f)
print('elms matters', len(matters))
sample = []
for m in matters[:8] + [m for m in matters if 'Planned' in (m.get('title') or '')][:4]:
    full = ej('/matter/' + m['matterId']); sample.append(full); time.sleep(0.3)
json.dump(sample, open(os.path.join(OUT, 'elms_sample.json'), 'w'), indent=1)

# 3) Census Building Permits Survey, place-level annual files (Midwest region)
out = []
for y in range(2006, datetime.date.today().year + 1):
    b = get(f'https://www2.census.gov/econ/bps/Place/Midwest%20Region/mw{y}a.txt', tries=3)
    if not b: print('bps missing', y); continue
    lines = b.decode('latin-1').splitlines()
    for ln in lines[:2]: hdr = ln
    for ln in lines:
        if 'Chicago' in ln and ln.split(',')[1:2] == ['17'] or ('Chicago city' in ln and ',17,' in ln):
            out.append([y] + ln.split(','))
    if y == 2006: open(os.path.join(OUT, 'bps_header.txt'), 'w').write('\n'.join(lines[:3]))
with open(os.path.join(OUT, 'bps_chicago.csv'), 'w', newline='') as f: csv.writer(f).writerows(out)
print('bps rows', len(out))
