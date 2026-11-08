"""IRS income data for the city income tax option in Balance the Chicago Budget (runs in GitHub Actions; the cloud
workspace can't reach irs.gov or census.gov).
  zip_il.csv.gz      IRS SOI individual income by ZIP code (Illinois rows only), returns and AGI by AGI class
  state_t2.csv.gz    IRS SOI Historic Table 2 (every state, finer AGI classes incl. $1M+)
  zcta_place.txt.gz  Census 2020 ZCTA-to-place relationship file (which ZIP areas lie in Chicago, by land area)"""
import urllib.request, gzip, io, os, time, csv
OUT = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'raw', 'budget', 'irs'); os.makedirs(OUT, exist_ok=True)
def get(url, tries=4):
    for t in range(tries):
        try: return urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': 'shapechicago'}), timeout=600).read()
        except Exception as e: print('retry', t, url, e, flush=True); time.sleep(10 * (t + 1))
    return None
for yy in ('22', '21'):
    d = get(f'https://www.irs.gov/pub/irs-soi/{yy}zpallagi.csv')
    if d:
        rows = d.decode('latin-1').splitlines(); keep = [rows[0]] + [r for r in rows[1:] if r.split(',')[1].strip('"') == 'IL']
        gzip.open(os.path.join(OUT, 'zip_il.csv.gz'), 'wt').write('\n'.join(keep)); open(os.path.join(OUT, 'year.txt'), 'w').write('20' + yy)
        print('zip', yy, len(keep), flush=True); break
for yy in ('22', '21'):
    d = get(f'https://www.irs.gov/pub/irs-soi/{yy}in55cmcsv.csv')
    if d: gzip.open(os.path.join(OUT, 'state_t2.csv.gz'), 'wb').write(d); print('state', yy, len(d), flush=True); break
d = get('https://www2.census.gov/geo/docs/maps-data/data/rel2020/zcta520/tab20_zcta520_place20_natl.txt')
if d:
    rows = d.decode('utf-8-sig').splitlines(); keep = [rows[0]] + [r for r in rows[1:] if '1714000' in r]
    gzip.open(os.path.join(OUT, 'zcta_place.txt.gz'), 'wt').write('\n'.join(keep)); print('zcta', len(keep), flush=True)
