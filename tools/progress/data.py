"""Yearly federal and county tables for the Progress pages, cut down to one small file: progress/data/src.json.
Reads the Chicago rows that tools/record/sources.py (main, in GitHub Actions) wrote to tools/raw/record/src/:
    python3 tools/progress/data.py [path to main's tools/raw/record/src]     (default ../fch-main/tools/raw/record/src)
These sources change once a year, so this is run by hand when a new year is published, then tools/progress/build.py.
  hud    HUD "Picture of Subsidized Households", Chicago city, by year: homes under each federal program
  bps    Census Building Permits Survey: homes permitted by place, for Chicago, big cities and the largest suburbs
  safmr  HUD Small Area Fair Market Rents by ZIP code (606xx), by fiscal year and bedrooms
  fhfa   FHFA yearly house price index by ZIP code (606xx)"""
import csv, json, os, sys, collections
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(os.path.dirname(HERE))
SRC = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(ROOT), 'fch-main', 'tools', 'raw', 'record', 'src')
num = lambda v: (lambda x: None if x is None or x < 0 else x)(float(v) if str(v).strip().replace('.', '', 1).replace('-', '', 1).isdigit() else None)
out = {}

# ---- HUD: homes by program, by year. Each year's file has its own header row; program names changed a little.
PROG = {'Summary of All HUD Programs': 'all', 'Public Housing': 'ph', 'Housing Choice Vouchers': 'hcv', 'Mod Rehab': 'mod', 'Project Based Section 8': 's8', 'Section 8 NC/SR': 's8',
        'S236/BMIR': 'other', 'Section 236': 'other', 'Multi-Family Other': 'other', '202/PRAC': 'eld', '811/PRAC': 'dis', 'LIHTC': 'lihtc'}
hud, hdr = collections.defaultdict(dict), None
for r in csv.reader(open(os.path.join(SRC, 'hud_place.csv'))):
    if r[0] == 'year': hdr = [h.lower() for h in r[2:]]; continue
    if r[1] == 'HEADER': hdr = [h.lower() for h in r[2:]]; continue
    d = dict(zip(hdr, r[2:])); y = int(r[0]); k = PROG.get(d.get('program_label', '').strip())
    if not k or d.get('sub_program', '').strip() not in ('', 'NA', 'N/A'): continue
    u = num(d.get('total_units'))
    if u is None: continue
    hud[y][k] = hud[y].get(k, 0) + int(u)
    if k == 'all':
        occ = num(d.get('total_occupied')); po = num(d.get('pct_occupied')); ppl = num(d.get('people_total'))
        hud[y]['occ'] = int(occ) if occ else (round(u * po / 100) if po else None); hud[y]['people'] = int(ppl) if ppl else None
out['hud'] = {str(y): hud[y] for y in sorted(hud) if 'all' in hud[y]}

# ---- Census permits: homes permitted a year by place
B = list(csv.DictReader(open(os.path.join(SRC, 'bps_places.csv'))))
tot = lambda r: sum(int(r[k] or 0) for k in ('u1', 'u2', 'u34', 'u5'))
# Chicago and the other 14 largest U.S. cities (2020 Census). Jacksonville, Indianapolis and Charlotte are filed under
# their county governments in this survey, with no city population, so they are left out: 12 cities in all.
CITY = {('17', 'Chicago'): 'Chicago', ('36', 'New York'): 'New York', ('06', 'Los Angeles'): 'Los Angeles', ('48', 'Houston'): 'Houston', ('04', 'Phoenix'): 'Phoenix', ('42', 'Philadelphia'): 'Philadelphia',
        ('48', 'San Antonio'): 'San Antonio', ('06', 'San Diego'): 'San Diego', ('48', 'Dallas'): 'Dallas', ('06', 'San Jose'): 'San Jose', ('48', 'Austin'): 'Austin', ('48', 'Fort Worth'): 'Fort Worth', ('39', 'Columbus'): 'Columbus'}
BORO = {'Bronx', 'Brooklyn', 'Manhattan', 'Queens', 'Staten Island'}
import re
clean = lambda n: re.sub(r'\s+(city|town|village|borough|municipality|metropolitan government.*|\(balance\).*|consolidated.*|unified.*)$', '', n, flags=re.I).strip()
cities = collections.defaultdict(dict); burbs = collections.defaultdict(dict); seen = collections.Counter()
for r in B:
    y = r['year']; st = r['state']; nm = clean(r['name']); key = (st, nm)
    if st == '36' and nm in BORO: key = ('36', 'New York')
    pop = int(r['pop']) if r['pop'].strip().isdigit() else 0
    if key in CITY:
        c = cities[CITY[key]].setdefault(y, {'u': 0, 'pop': 0, 'm': 12}); c['u'] += tot(r); c['pop'] += pop; c['m'] = min(c['m'], int(r['months'] or 12))
    elif r['cbsa'] == '16980' and st == '17' and pop >= 25000:
        b_ = burbs[nm].setdefault(y, {'u': 0, 'pop': 0}); b_['u'] += tot(r); b_['pop'] += pop   # towns that straddle a county line are filed once per county
out['bps'] = {'cities': {k: v for k, v in cities.items() if '2025' in v and v['2025']['pop'] > 200000}, 'suburbs': {k: v for k, v in burbs.items() if '2025' in v and '2019' in v}}

# ---- HUD Small Area Fair Market Rents: [studio, 1, 2, 3, 4 bedrooms] by ZIP and fiscal year
saf, hdr = collections.defaultdict(dict), None
for r in csv.reader(open(os.path.join(SRC, 'safmr.csv'))):
    if r[1] == 'HEADER': hdr = [re.sub(r'\s+', ' ', h).strip().lower() for h in r[2:]]; continue
    z = r[2].strip()
    if not z.startswith('606'): continue
    v = []
    for b in range(5):
        i = next((i for i, h in enumerate(hdr) if re.fullmatch(rf'safmr[ _]{b}br', h)), None)
        v.append(int(float(r[2 + i].replace('$', '').replace(',', ''))) if i is not None and r[2 + i].strip() else None)
    saf[z][r[0]] = v
out['safmr'] = saf

# ---- FHFA house price index by ZIP: index values by year (the file's own base year)
fh = collections.defaultdict(dict)
for r in csv.reader(open(os.path.join(SRC, 'fhfa_zip5.csv'))):
    if len(r) > 3 and r[0].startswith('606') and r[1].isdigit() and int(r[1]) >= 2012 and r[3].strip():
        try: fh[r[0]][r[1]] = round(float(r[3]), 1)
        except ValueError: pass
out['fhfa'] = fh
os.makedirs(os.path.join(ROOT, 'progress', 'data'), exist_ok=True)
json.dump(out, open(os.path.join(ROOT, 'progress', 'data', 'src.json'), 'w'), separators=(',', ':'))
print('hud', {y: (v.get('all'), v.get('ph'), v.get('hcv'), v.get('s8')) for y, v in out['hud'].items()})
print('cities', {k: (v['2025']['u'], v['2025']['pop'], round(1000 * v['2025']['u'] / v['2025']['pop'], 1)) for k, v in sorted(out['bps']['cities'].items(), key=lambda kv: -kv[1]['2025']['u'] / kv[1]['2025']['pop'])})
print('suburbs', len(out['bps']['suburbs']), 'zips', len(saf), list(saf.items())[0], 'fhfa zips', len(fh))
print('bytes', os.path.getsize(os.path.join(ROOT, 'progress', 'data', 'src.json')))
