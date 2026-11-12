"""Monthly rides on CTA, Metra and Pace, from the federal National Transit Database (for Progress → Transit).
Runs daily after fetch.py; the federal table is refreshed about once a month, two months behind.
Downloads the "Complete Monthly Ridership" table (data.transportation.gov 8bui-9xvu) for the Chicago urban area and
writes tracker/transit.json: {"through": "YYYY-MM", "series": {"cta_bus": {"2019-01": rides, ...}, "cta_rail", "metra",
"pace_bus"}}. Rides are what the database calls unlinked passenger trips: every boarding counts.
Note for readers of the numbers: CTA changed how it counts in January 2025, so its 2025-on months are not comparable
with earlier years; a year-to-date change against the year before (2026 vs. 2025) compares like with like.
Standard library only. If the download fails, the last file is kept."""
import urllib.request, urllib.parse, csv, io, json, os, collections, time, sys
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
UA = {'User-Agent': 'fixchicagohousing.com tracker (github.com/SnowBelt93/fix-chicago-housing)'}
q = urllib.parse.urlencode({'$select': 'agency,mode,tos,date,upt', '$where': "upper(uza_name) like '%CHICAGO%' AND date >= '2019-01-01T00:00:00'", '$limit': 100000})
b = None
for t in range(4):
    try: b = urllib.request.urlopen(urllib.request.Request('https://data.transportation.gov/resource/8bui-9xvu.csv?' + q, headers=UA), timeout=300).read(); break
    except Exception as e: print('retry', t, e, flush=True); time.sleep(10 * (t + 1))
if not b: print('federal ridership: download failed, kept the last file'); sys.exit(0)
S = collections.defaultdict(lambda: collections.defaultdict(float))
def key(agency, mode):
    a = agency.upper()
    if a.startswith('CHICAGO TRANSIT AUTHORITY'): return {'MB': 'cta_bus', 'HR': 'cta_rail'}.get(mode)
    if 'NORTHEAST ILLINOIS REGIONAL COMMUTER' in a and mode == 'CR': return 'metra'
    if a.startswith('PACE') and mode == 'MB': return 'pace_bus'
for r in csv.DictReader(io.StringIO(b.decode('utf-8'))):
    k = key(r['agency'], r['mode'])
    if not k: continue
    try: S[k][r['date'][:7]] += float(r['upt'] or 0)
    except ValueError: pass
if len(S) < 4 or min(len(v) for v in S.values()) < 60: print('federal ridership: table looked short, kept the last file', {k: len(v) for k, v in S.items()}); sys.exit(0)
# the newest month every series has a real number for
months = sorted(set.intersection(*[set(m for m, v in s.items() if v > 0) for s in S.values()]))
out = {'through': months[-1], 'series': {k: {m: round(v) for m, v in sorted(s.items()) if m <= months[-1]} for k, s in S.items()}}
os.makedirs(os.path.join(ROOT, 'tracker'), exist_ok=True)
json.dump(out, open(os.path.join(ROOT, 'tracker', 'transit.json'), 'w'), separators=(',', ':'))
print('federal ridership through', out['through'], {k: round(sum(v for m, v in s.items() if m.startswith('2025')) / 1e6, 1) for k, s in out['series'].items()})
