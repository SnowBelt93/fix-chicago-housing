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

# 2b) Zoning narratives: for zoning matters introduced 2021 on, download the narrative/exhibit PDF once and keep the text
#     of its first pages (that's where Type 1 applications state the number of dwelling units). Cached per matter,
#     so each daily run only fetches new matters; capped by time so a backfill spreads over a few runs.
import subprocess, tempfile, re
TXT = os.path.join(OUT, 'elms_text'); os.makedirs(TXT, exist_ok=True)
t0 = time.time(); fetched = 0
CAP_MIN = float(os.environ.get('NARRATIVE_MINUTES', '38'))
cand = [m for m in matters if (m.get('introductionDate') or '') >= '2021-01-01' and m.get('recordNumber')]
cand.sort(key=lambda m: ((m.get('subStatus') or '').startswith('Passed'), m.get('introductionDate') or ''), reverse=True)
def pdf_text(b):
    """Text of the first pages: pdftotext for typed PDFs, OCR (tesseract) for scans."""
    with tempfile.TemporaryDirectory() as td:
        fp = os.path.join(td, 'a.pdf'); open(fp, 'wb').write(b)
        try: t = subprocess.run(['pdftotext', '-l', '4', '-layout', fp, '-'], capture_output=True, timeout=60).stdout.decode('utf-8', 'ignore')
        except Exception: t = ''
        if len(t.strip()) > 200: return t, 'text'
        try:
            subprocess.run(['pdftoppm', '-r', '170', '-f', '1', '-l', '3', '-gray', '-png', fp, os.path.join(td, 'p')], capture_output=True, timeout=120)
            out = []
            for img in sorted(f for f in os.listdir(td) if f.endswith('.png')):
                r = subprocess.run(['tesseract', os.path.join(td, img), '-', '--psm', '4'], capture_output=True, timeout=120)
                out.append(r.stdout.decode('utf-8', 'ignore'))
            return '\n'.join(out), 'ocr'
        except Exception as e:
            return '', 'fail'

for m in cand:
    if time.time() - t0 > CAP_MIN * 60: print('narratives: time cap reached'); break
    rec = re.sub(r'[^A-Za-z0-9-]', '_', m['recordNumber'])
    fn = os.path.join(TXT, rec + '.json')
    if os.path.exists(fn):
        old = json.load(open(fn))
        fresh = old.get('v') == 2
        # re-check matters still in progress once a week (attachments get added at committee)
        if fresh and (old.get('final') or (time.time() - old.get('checked', 0)) < 7 * 86400): continue
    try: full = ej('/matter/' + m['matterId'])
    except SystemExit: continue
    if not full: continue
    att = full.get('attachments') or []
    def score(a):
        n = ((a.get('fileName') or '') + ' ' + (a.get('attachmentType') or '')).lower()
        return (0 if 'final narrative' in n else 1 if 'narrative' in n else 2 if 'exhibit' in n else 3 if 'ordinance' in n or 'legislation' in n else 9)
    pick = sorted([a for a in att if a.get('path') and score(a) < 9], key=score)[:2]
    texts = []
    for a in pick:
        try:
            b = urllib.request.urlopen(urllib.request.Request(a['path'], headers=UA), timeout=120).read(80_000_000)
        except Exception as e:
            print('pdf fail', rec, e); continue
        t, how = pdf_text(b)
        texts.append({'file': a.get('fileName'), 'type': a.get('attachmentType'), 'how': how, 'text': t[:20000]})
        if score(a) <= 1 and len(t.strip()) > 200: break      # a readable narrative is enough
    rec_out = {'v': 2, 'recordNumber': m['recordNumber'], 'matterId': m['matterId'], 'checked': time.time(),
               'final': (full.get('status') or '').startswith('90'), 'status': full.get('status'), 'subStatus': full.get('subStatus'),
               'actions': [{'date': (a.get('actionDate') or '')[:10], 'name': a.get('actionName')} for a in full.get('actions') or []],
               'attachments': [{'file': a.get('fileName'), 'type': a.get('attachmentType')} for a in att], 'texts': texts}
    json.dump(rec_out, open(fn, 'w')); fetched += 1
    time.sleep(0.2)
print('narratives fetched this run', fetched, 'cached', len(os.listdir(TXT)))

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
