#!/usr/bin/env python3
"""Build budget/data/budget.json for Balance the Chicago Budget from the City's budget ordinance datasets
(tools/raw/budget/, downloaded by tools/budget/fetch.py in GitHub Actions).
  years    2011–2026 = the budget the City Council passed (Budget Ordinance); 2027 = the Mayor's proposal
           (Budget Recommendations). For each: total appropriations (all funds, local, grants), the Corporate Fund
           (the city's general operating fund, where the gap is), pension fund appropriations, debt-service fund
           appropriations, the police and fire departments' Corporate Fund budgets and budgeted positions.
  corp27   the 2027 proposed Corporate Fund by department, Finance General split into pensions, health care,
           settlements and other.
  rev      Corporate Fund revenue by source, 2024–2027 (only those years are published as data)."""
import csv, gzip, json, os, re, collections
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RAW = os.path.join(ROOT, 'tools', 'raw', 'budget')
OUT = os.path.join(ROOT, 'budget', 'data'); os.makedirs(OUT, exist_ok=True)
CAT = json.load(open(os.path.join(RAW, 'catalog.json')))

def ds(kind, year, rec=False):
    want = f"Budget - {year} Budget {'Recommendations' if rec else 'Ordinance'} - {kind}"
    for d in CAT:
        if d['name'] == want: return os.path.join(RAW, d['id'] + '.csv.gz')

def rows(path):
    for r in csv.DictReader(gzip.open(path, 'rt', encoding='utf-8-sig')):
        yield {k.upper().strip(): (v or '').strip() for k, v in r.items()}

def num(v):
    try: return float(v.replace(',', '').replace('$', '') or 0)
    except ValueError: return 0.0

def amount(r, year, rec):
    if rec: return num(r.get(f'{year} RECOMMENDATION', '0'))
    keys = [k for k in r if 'AMOUNT' in k or 'ORDINANCE' in k]
    return num(r[keys[-1]]) if keys else 0.0

def dept_of(r): return (r.get('DEPARTMENT DESCRIPTION') or r.get('DEPARTMENT') or '').upper()
def fund_of(r): return (r.get('FUND DESCRIPTION') or r.get('FUND NAME') or '').upper()
def fcode(r): return re.sub(r'^0+', '', r.get('FUND CODE') or '')

years = {}
for y in range(2011, 2028):
    rec = y == 2027
    p = ds('Appropriations', y, rec)
    if not p: continue
    t = collections.Counter()
    for r in rows(p):
        a = amount(r, y, rec); ft = (r.get('FUND TYPE') or '').upper(); fund = fund_of(r); dep = dept_of(r)
        t['total'] += a
        t['grants' if ft in ('GRANTS', 'CDBG') else 'local'] += a
        if fcode(r) == '100':
            t['corp'] += a
            if dep in ('CPD', 'POLICE') or dep.endswith('POLICE DEPARTMENT') or dep == 'DEPARTMENT OF POLICE': t['police'] += a
            if dep in ('CFD', 'FIRE') or dep.endswith('FIRE DEPARTMENT') or dep == 'DEPARTMENT OF FIRE': t['fire'] += a
        if re.search(r'ANNUITY|PENSION', fund) and ft not in ('GRANTS', 'CDBG'): t['pensions'] += a
        if re.search(r'BOND REDEMPTION|NOTE REDEMPTION|DEBT SERVICE|SALES TAX SECURITIZATION', fund): t['debtFunds'] += a
    pos = 0
    pp = ds('Positions and Salaries', y, rec)
    if pp:
        for r in rows(pp):
            if (r.get('BUDGETED UNIT') or '').upper().startswith('ANNUAL'): pos += num(r.get('TOTAL BUDGETED UNIT') or r.get('TOTAL BUDGETED UNITS') or '0')
    years[y] = {k: round(v) for k, v in t.items()}
    if pos: years[y]['positions'] = round(pos)
    print(y, {k: round(v / 1e6) for k, v in t.items()}, 'positions', round(pos))

# 2027 Corporate Fund by department, Finance General split by what it pays for
corp = collections.Counter(); fg = collections.Counter()
for r in rows(ds('Appropriations', 2027, True)):
    if fcode(r) != '100': continue
    a = amount(r, 2027, True); dep = r.get('DEPARTMENT DESCRIPTION') or ''
    if dep.upper() == 'FINANCE GENERAL':
        acct = (r.get('APPROPRIATION ACCOUNT DESCRIPTION') or '').upper()
        k = ('Pensions' if 'PENSION' in acct else
             'Employee health care and benefits' if re.search(r'HOSPITAL|HMO|DENTAL|VISION|MEDICARE|WORKERS|UNEMPLOYMENT|MEDICAL|LIFE INSURANCE|BENEFIT', acct) else
             'Settlements and judgments' if re.search(r'JUDGMENT|SETTLEMENT|CONSENT DECREE|LEGAL', acct) else
             'Debt payments' if re.search(r'BOND|DEBT|INTEREST|NOTE', acct) else
             'Raises not yet assigned to departments' if 'WAGE ADJUST' in acct else
             'Other citywide costs')
        fg[k] += a
    else: corp[dep] += a
groups = {'Police': ['Chicago Police Department', 'Office of Public Safety Administration', 'Civilian Office of Police Accountability', 'Police Board'],
          'Fire': ['Chicago Fire Department'], 'Streets and sanitation': ['Department of Streets and Sanitation'],
          'Family and support services': ['Department of Family and Support Services'], 'Fleet and facilities': ['Department of Fleet and Facility Management'],
          'Public health': ['Chicago Department of Public Health'], 'Emergency communications (911)': ['Office of Emergency Management and Communications']}
out = collections.Counter()
for dep, a in corp.items():
    g = next((k for k, v in groups.items() if dep in v), 'Other departments'); out[g] += a
for k, v in fg.items(): out[k] += v
corp27 = sorted(([k, round(v)] for k, v in out.items()), key=lambda x: -x[1])
print('corp27', [(k, round(v / 1e6)) for k, v in corp27])

# Corporate Fund revenue by source
rev = {}
for y in (2024, 2025, 2026, 2027):
    p = ds('Revenue', y, rec=(y == 2027))
    if not p: continue
    c = collections.Counter()
    for r in rows(p):
        if (r.get('FUND_NAME') or '').lower() != 'corporate fund': continue
        c[r.get('REVENUE_SOURCE') or r.get('REVENUE_CATEGORY')] += num(r.get('ESTIMATED_REVENUE') or '0')
    rev[y] = {k: round(v) for k, v in c.items() if v}
    print(y, 'corp revenue', round(sum(c.values()) / 1e6))
# City pension contributions, 2011–2023: the 2026 Budget Overview's "Pension Contributions - Historic and Projected"
# chart (required contributions, plus supplemental payments from 2023). 2024–2027: appropriations to the four pension
# funds in the budget data above.
HIST = {2011: 450.5e6, 2012: 476.3e6, 2013: 479.5e6, 2014: 478.3e6, 2015: 798.0e6, 2016: 848.5e6, 2017: 1029.0e6,
        2018: 1187.5e6, 2019: 1308.5e6, 2020: 1679.8e6, 2021: 1815.2e6, 2022: 2275.9e6, 2023: 2610.2e6}
for y in years:
    if y in HIST: years[y]['pensions'] = round(HIST[y])
# every department by year: Corporate Fund and all local funds (department number is the key; the newest name wins)
dept = collections.defaultdict(lambda: collections.defaultdict(lambda: [0, 0])); dname = {}
for y in range(2011, 2028):
    rec = y == 2027; p = ds('Appropriations', y, rec)
    if not p: continue
    for r in rows(p):
        num_ = re.sub(r'^0+', '', r.get('DEPARTMENT NUMBER') or r.get('DEPARTMENT CODE') or '') or '?'
        nm = (r.get('DEPARTMENT DESCRIPTION') or r.get('DEPARTMENT') or '').strip()
        if nm and (num_ not in dname or y >= dname[num_][0]): dname[num_] = (y, nm)
        if (r.get('FUND TYPE') or '').upper() in ('GRANTS', 'CDBG'): continue
        a = amount(r, y, rec); d = dept[num_][y]; d[1] += a
        if fcode(r) == '100': d[0] += a
depts = []
for k, ys in dept.items():
    if max(v[1] for v in ys.values()) < 5e6: continue
    depts.append({'id': k, 'name': dname[k][1], 'y': {y: [round(v[0]), round(v[1])] for y, v in sorted(ys.items())}})
depts.sort(key=lambda d: -(d['y'].get(2027, [0, 0])[1]))
print('departments', len(depts), [d['name'] for d in depts[:12]])
# average budgeted pay per Corporate Fund department, 2027 proposal
dpay = collections.defaultdict(lambda: [0.0, 0.0])
for r in rows(ds('Positions and Salaries', 2027, True)):
    if fcode(r) == '100' and (r.get('BUDGETED UNIT') or '').upper().startswith('ANNUAL'):
        k = re.sub(r'^0+', '', r.get('DEPARTMENT CODE') or ''); d = dpay[k]; d[0] += num(r.get('TOTAL BUDGETED AMOUNT') or '0'); d[1] += num(r.get('TOTAL BUDGETED UNIT') or '0')
# share of each department's 2027 Corporate Fund money that pays people (accounts 0000-0099: salaries, overtime, etc.)
dper = collections.defaultdict(lambda: [0.0, 0.0])
for r in rows(ds('Appropriations', 2027, True)):
    if fcode(r) != '100': continue
    k = re.sub(r'^0+', '', r.get('DEPARTMENT NUMBER') or ''); a = amount(r, 2027, True); dper[k][1] += a
    if int(re.sub(r'\D', '', r.get('APPROPRIATION ACCOUNT') or '9999') or 9999) < 100: dper[k][0] += a
for d in depts:
    q = dper.get(d['id'])
    if q and q[1]: d['ps'] = round(q[0] / q[1], 3)
    pp = dpay.get(d['id'])
    if pp and pp[1]: d['pay'] = round(pp[0] / pp[1]); d['pos'] = round(pp[1])
# average budgeted pay of a full-time Corporate Fund position in the 2027 proposal (salary only, no benefits)
pay = n = 0
for r in rows(ds('Positions and Salaries', 2027, True)):
    if fcode(r) == '100' and (r.get('BUDGETED UNIT') or '').upper().startswith('ANNUAL'):
        u = num(r.get('TOTAL BUDGETED UNIT') or '0'); pay += num(r.get('TOTAL BUDGETED AMOUNT') or '0'); n += u
avgPay = round(pay / n) if n else None
print('avg corporate fund pay', avgPay, 'positions', n)
# CPI-U, U.S. city average, annual averages (BLS series CUUR0000SA0); 2026 is the average of the months published so far
CPI = {2011: 224.939, 2012: 229.594, 2013: 232.957, 2014: 236.736, 2015: 237.017, 2016: 240.007, 2017: 245.120, 2018: 251.107,
       2019: 255.657, 2020: 258.811, 2021: 270.970, 2022: 292.655, 2023: 304.702, 2024: 313.689, 2025: 321.943, 2026: 332.243}
json.dump({'years': years, 'corp27': corp27, 'rev': rev, 'avgPay': avgPay, 'cpi': CPI, 'depts': depts}, open(os.path.join(OUT, 'budget.json'), 'w'), separators=(',', ':'))

# ---- City income tax option: Chicago residents' income by slice (IRS SOI ZIP data + Historic Table 2 + Census ZCTA-place file)
def build_income():
    IRS = os.path.join(RAW, 'irs')
    if not os.path.exists(os.path.join(IRS, 'zip_il.csv.gz')): print('no IRS data'); return None
    year = open(os.path.join(IRS, 'year.txt')).read().strip()
    # share of each ZIP's land inside Chicago (2020 ZCTA-place relationship file)
    share = {}
    rr = csv.DictReader(gzip.open(os.path.join(IRS, 'zcta_place.txt.gz'), 'rt'), delimiter='|')
    for r in rr:
        if r.get('GEOID_PLACE_20') != '1714000' or not r.get('GEOID_ZCTA5_20'): continue
        z = r['GEOID_ZCTA5_20']; part = num(r.get('AREALAND_PART', '0')); whole = num(r.get('AREALAND_ZCTA5_20', '0'))
        if whole: share[z] = share.get(z, 0) + part / whole
    # ZIP rows: agi_stub 1..6 = $1-25k, 25-50k, 50-75k, 75-100k, 100-200k, 200k+; N1 returns, A00100 AGI ($1,000s)
    N = collections.Counter(); A = collections.Counter()
    for r in csv.DictReader(gzip.open(os.path.join(IRS, 'zip_il.csv.gz'), 'rt')):
        r = {k.strip().lower(): v for k, v in r.items()}
        z = r['zipcode'].zfill(5); w = share.get(z, 0)
        if w < 0.02: continue
        st = int(num(r['agi_stub'])); N[st] += w * num(r['n1']); A[st] += w * num(r['a00100']) * 1000
    # Illinois Historic Table 2: classes 200-500k, 500k-1M, 1M+ (to split Chicago's $200k+ class)
    il = collections.Counter(); iln = collections.Counter()
    for r in csv.DictReader(gzip.open(os.path.join(IRS, 'state_t2.csv.gz'), 'rt', encoding='latin-1')):
        r = {k.strip().upper(): v for k, v in r.items()}
        if r.get('STATE', '').strip() != 'IL': continue
        stb = int(num(r['AGI_STUB'])); il[stb] += num(r['A00100']) * 1000; iln[stb] += num(r['N1'])
    print('IL stubs', sorted(iln.items()))
    # state stubs (2022 layout): 8 = 200-500k, 9 = 500k-1M, 10 = 1M+
    il200 = sum(il[k] - iln[k] * 2e5 for k in (8, 9, 10)); il1m = il[10] - iln[10] * 1e6
    f1m = il1m / il200                                   # share of Illinois income above $200k that sits above $1M
    n1m_share = iln[10] / sum(iln[k] for k in (8, 9, 10))
    # classes c: 0 under 50k (stubs 1,2), 1 50-100k (3,4), 2 100-200k (5), 3 200k-1M, 4 1M+
    n = [N[1] + N[2], N[3] + N[4], N[5]]; a = [A[1] + A[2], A[3] + A[4], A[5]]
    above200 = A[6] - N[6] * 2e5; x1m = f1m * above200      # Chicago income above $1M (assumption: same share as Illinois)
    n1m = N[6] * n1m_share; a1m = n1m * 1e6 + x1m; n.append(N[6] - n1m); a.append(A[6] - a1m); n.append(n1m); a.append(a1m)
    lo = [0, 5e4, 1e5, 2e5, 1e6]; hi = [5e4, 1e5, 2e5, 1e6, float('inf')]
    m = []
    for c in range(5):
        row = []
        for k in range(5):
            if k < c: row.append(n[c] * (hi[k] - lo[k]))
            elif k == c: row.append(max(0, a[c] - n[c] * lo[k]))
            else: row.append(0)
        m.append([round(v) for v in row])
    reach = [sum(n[c] for c in range(k, 5)) for k in range(5)]   # returns with income reaching each slice
    print('income', year, 'returns', round(sum(n)), 'AGI $B', round(sum(a) / 1e9, 1), 'per slice $B', [round(sum(m[c][k] for c in range(5)) / 1e9, 2) for k in range(5)])
    return {'year': int(year), 'm': m, 'n': [round(x) for x in reach], 'classN': [round(x) for x in n], 'classA': [round(x) for x in a], 'f1m': round(f1m, 4)}
inc = build_income()
if inc:
    d = json.load(open(os.path.join(OUT, 'budget.json'))); d['inc'] = inc
    json.dump(d, open(os.path.join(OUT, 'budget.json'), 'w'), separators=(',', ':'))

# ---- "Would it pass?": alderpeople grouped by their votes on the 2025 budget (Dec. 2024) and the 2026 budget (Dec. 2025)
def build_votes():
    vp = os.path.join(RAW, 'votes.json'); wp = os.path.join(ROOT, 'tools', 'raw', 'wards', 'ward_offices.csv')
    if not os.path.exists(vp): return None
    V = json.load(open(vp)); rec = {r['recordNumber']: r for r in V}
    def roll(num):
        r = rec.get(num); acts = [a for a in (r or {}).get('actions') or [] if a.get('votes')]
        return {v['voterName']: v['vote'] for v in acts[-1]['votes']} if acts else {}
    b26, b25 = roll('SO2025-0020516'), roll('SO2024-0013682')
    norm = lambda n: re.sub(r'[^a-z]', '', n.lower().split(',')[0])
    ward = {}
    if os.path.exists(wp):
        for r in csv.DictReader(open(wp, encoding='utf-8-sig')): ward[norm(r['ALDERMAN'])] = int(r['WARD'])
    mem = []
    for name, v26 in b26.items():
        v25 = b25.get(name)
        y26 = v26 == 'Yea' if v26 in ('Yea', 'Nay') else (v25 == 'Yea')
        y25 = (v25 == 'Yea') if v25 in ('Yea', 'Nay') else y26          # members new since 2024 take their 2026 vote
        g = 'A' if y25 and y26 else 'B' if y26 else 'C' if y25 else 'D'
        mem.append({'name': name, 'ward': ward.get(norm(name)), 'g': g, 'v25': v25, 'v26': v26})
    mem.sort(key=lambda m: m['ward'] or 99)
    cnt = collections.Counter(m['g'] for m in mem)
    print('vote groups', dict(cnt), 'members', len(mem), 'no ward', [m['name'] for m in mem if not m['ward']])
    E = 'https://chicityclerkelms.chicago.gov/Matter/?matterId='
    return {'members': mem, 'counts': dict(cnt), 'sources': [['2026 budget, Dec. 20, 2025 (30–18)', E + rec['SO2025-0020516']['matterId']],
            ['2025 budget, Dec. 16, 2024 (27–23)', E + rec['SO2024-0013682']['matterId']]]}
vt = build_votes()
if vt:
    d = json.load(open(os.path.join(OUT, 'budget.json'))); d['votes'] = vt
    json.dump(d, open(os.path.join(OUT, 'budget.json'), 'w'), separators=(',', ':'))
