"""Data for the ward housing record (runs in GitHub Actions; the cloud workspace can't reach the City Clerk or the
data portal). Writes under tools/raw/wards/:
  key_search.json   eLMS search hits for citywide housing legislation (ADUs, parking, affordable requirements, ...)
  key_matters.json  full records (with every alderperson's vote) for the final ones among them
  ord/<record>.json for each zoning map amendment or planned development in tools/raw/tracker/elms_zoning.json.gz that
                    reached a final status: its sub-status (Passed, Failed, Placed on File...), sponsors, final date,
                    and the text of its ordinance's first two pages (which names the district it changes from and to).
                    Cached, newest first, capped at 40 minutes a run so the backfill spreads over several runs.
  ward_offices.csv  City of Chicago "Ward Offices" dataset (alderperson names and offices)"""
import urllib.request, urllib.parse, json, os, time, gzip, subprocess, tempfile
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(ROOT, 'tools', 'raw', 'wards'); os.makedirs(os.path.join(OUT, 'ord'), exist_ok=True)
E = 'https://api.chicityclerkelms.chicago.gov'
def get(url, tries=4, timeout=120):
    for t in range(tries):
        try: return urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': 'shapechicago'}), timeout=timeout).read()
        except Exception as e: print('retry', t, url[:120], e, flush=True); time.sleep(5 * (t + 1))
    return None
def ej(path, **params):
    b = get(E + path + ('?' + urllib.parse.urlencode(params) if params else ''))
    try: return json.loads(b) if b else None
    except Exception: return None

# 0) upcoming City Council and committee meetings (for the hearing calendar): the API's own description is saved, then
#    every meeting path is tried with a date filter; whatever answers is kept raw in meetings.json
import datetime as _dt
sw = get(E + '/swagger.json')
if sw: open(os.path.join(OUT, 'elms_swagger.json'), 'wb').write(sw)
meet = {}
try: paths = [k for k in json.loads(sw).get('paths', {}) if 'meeting' in k.lower() and '{' not in k] if sw else []
except Exception: paths = []
for path in paths or ['/meeting']:
    since = (_dt.date.today() - _dt.timedelta(days=21)).isoformat()
    for params in ({'filter': 'date ge %sT00:00:00Z' % since, 'top': '200', 'sort': 'date asc'},
                   {'filter': 'meetingDate ge %sT00:00:00Z' % since, 'top': '200', 'sort': 'meetingDate asc'}, {'top': '200'}):
        r = ej(path, **params)
        if r: meet[path + ' ' + json.dumps(params)] = r; break
json.dump(meet, open(os.path.join(OUT, 'meetings.json'), 'w'))
print('meetings', {k: len((v or {}).get('data') or v) if isinstance(v, (dict, list)) else 0 for k, v in meet.items()}, flush=True)

# 0b) alderpersons as the City Clerk lists them (name, ward, contact, official photo)
people = []
for skip in (0, 500):
    r = ej('/person', top='500', skip=skip)
    data = (r or {}).get('data') if isinstance(r, dict) else r
    if not data: break
    people += data
    if len(data) < 500: break
json.dump(people, open(os.path.join(OUT, 'persons.json'), 'w'))
print('persons', len(people), 'with photo', sum(1 for p in people if p.get('photo')), flush=True)

# 1) citywide housing legislation and its roll calls
TERMS = ['"Additional Dwelling Unit"', '"accessory dwelling"', '"coach house"', '"Connected Communities"', '"Bring Chicago Home"',
         '"Affordable Requirements Ordinance"', '"Cut the Tape"', '"single stair"', '"single-stair"', '"Missing Middle"', '"Green Social Housing"',
         '"Northwest Side Preservation"', '"Woodlawn"', '"demolition surcharge"', '"parking minimum"', '"Transit Served Location"',
         '"Equitable Transit-Oriented"', '"Cut the Red Tape"', '"housing"']
hits, seen = [], set()
for term in TERMS:
    skip = 0
    while True:
        res = ej('/search', search=term, filter="introductionDate ge 2019-01-01T00:00:00Z", top='500', skip=skip, sort='introductionDate desc')
        data = (res or {}).get('data') or []
        for m in data:
            if m.get('matterId') in seen: continue
            if (m.get('type') or '') not in ('Ordinance', 'Resolution'): continue
            if 'Zoning Reclassification' in (m.get('title') or '') or 'Planned Development' in (m.get('title') or ''): continue
            seen.add(m['matterId']); m['_term'] = term; hits.append(m)
        print('search', term, skip, len(data), flush=True)
        if len(data) < 500 or skip >= 2000: break
        skip += 500; time.sleep(0.4)
json.dump(hits, open(os.path.join(OUT, 'key_search.json'), 'w'))
full = []
for m in hits:
    if m.get('status') != '90-Final' or m.get('filingSponsor') in (None, 'Misc. Transmittal'): pass
    if m.get('status') != '90-Final': continue
    r = ej('/matter/' + m['matterId'])
    if r and any(a.get('votes') for a in r.get('actions') or []):
        r.pop('attachments', None); full.append(r)
    time.sleep(0.25)
json.dump(full, open(os.path.join(OUT, 'key_matters.json'), 'w'))
print('key matters with roll calls', len(full), flush=True)

# 2) ward offices (alderpersons)
b = get('https://data.cityofchicago.org/api/views/htai-wnw4/rows.csv?accessType=DOWNLOAD')
if b: open(os.path.join(OUT, 'ward_offices.csv'), 'wb').write(b)

# 3) zoning ordinances' text and how each alderperson voted on them
def roll(r):
    """The City Council roll call on a matter: [[action, date, [[name, vote], ...]], ...] (empty when no roll call is recorded)."""
    out = []
    for a in r.get('actions') or []:
        if a.get('votes'): out.append([a.get('actionName'), a.get('actionDate'), a.get('actionByName'), [[v.get('voterName'), v.get('vote')] for v in a['votes']]])
    return out
Z = json.load(gzip.open(os.path.join(ROOT, 'tools', 'raw', 'tracker', 'elms_zoning.json.gz'), 'rt'))
Z = [m for m in Z if m.get('status') == '90-Final']
Z.sort(key=lambda m: m.get('introductionDate') or '', reverse=True)
t0 = time.time(); n = 0
for m in Z:
    if time.time() - t0 > 40 * 60: break
    path = os.path.join(OUT, 'ord', (m.get('recordNumber') or m['matterId']).replace('/', '_') + '.json')
    if os.path.exists(path): continue
    r = ej('/matter/' + m['matterId'])
    if not r: continue
    rec = {'record': r.get('recordNumber'), 'title': r.get('title'), 'sub': r.get('subStatus'), 'final': r.get('finalActionDate'),
           'intro': r.get('introductionDate'), 'sponsors': [s.get('sponsorName') for s in r.get('sponsors') or []],
           'actions': [[a.get('actionDate'), a.get('actionByName'), a.get('actionName')] for a in r.get('actions') or []], 'text': '',
           'votes': roll(r)}
    att = [a for a in r.get('attachments') or [] if (a.get('attachmentType') or '') == 'Legislation' or 'Ordinance' in (a.get('fileName') or '')]
    if att:
        pdf = get(att[0]['path'], tries=2, timeout=60)
        if pdf:
            with tempfile.NamedTemporaryFile(suffix='.pdf') as f:
                f.write(pdf); f.flush()
                try: rec['text'] = subprocess.run(['pdftotext', '-l', '2', '-layout', f.name, '-'], capture_output=True, timeout=60).stdout.decode('utf-8', 'ignore')[:6000]
                except Exception: pass
    json.dump(rec, open(path, 'w')); n += 1
    time.sleep(0.15)
print('ordinances fetched this run', n, 'of', len(Z), 'final matters', flush=True)
# records saved before roll calls were kept: add them (newest first, 30 minutes a run)
t1 = time.time(); k = 0
for m in Z:
    if time.time() - t1 > 30 * 60: break
    path = os.path.join(OUT, 'ord', (m.get('recordNumber') or m['matterId']).replace('/', '_') + '.json')
    if not os.path.exists(path): continue
    rec = json.load(open(path))
    if 'votes' in rec: continue
    r = ej('/matter/' + m['matterId'])
    if not r: continue
    rec['votes'] = roll(r); json.dump(rec, open(path, 'w')); k += 1
    time.sleep(0.1)
print('roll calls added this run', k, flush=True)
