"""Build tracker/data.json for the public Chicago housing tracker (fixchicagohousing.com/tracker/).
Inputs come from tools/raw/tracker/ (fetch.py). Pure standard library, so it runs in GitHub Actions.

Pipeline stages, all from public data:
  zoning approved  City Clerk eLMS: zoning map amendments passed by City Council; homes from the application's
                   narrative when it states a dwelling-unit count (Type 1 applications and planned developments)
  permitted        Department of Buildings new-construction permits, grouped into projects (permits.py), homes
                   read from the description (units.py)
  finished         the permit's milestone is 'Complete' or 'Certificate of occupancy issued'"""
import json, os, re, gzip, csv, datetime, collections, sys
sys.path.insert(0, os.path.dirname(__file__))
from permits import load_permits, projects, RAW
import accuracy

ROOT = os.path.join(os.path.dirname(__file__), '..', '..')
OUT = os.path.join(ROOT, 'tracker'); os.makedirs(OUT, exist_ok=True)
TODAY = datetime.date.today()

# --- goal (same numbers as the game's normal mode; see index.html TARGETS / CLAUDE.md "Baseline") -------------
BUILT_ANYWAY = 4900          # homes Chicago approved in 2025 (TRD Data); the game's "built anyway" pace
CITY_GAP_NOW = 54141         # Chicago's share (32.7%) of Up for Growth's metro shortage
CITY_GAP_GROWTH = 2862       # Chicago's share of the metro shortage's yearly growth
GOAL_YEARS = 15              # 2026-2041
HOLD = BUILT_ANYWAY + CITY_GAP_GROWTH                         # pace that stops the gap growing
CLOSE = HOLD + round(CITY_GAP_NOW / GOAL_YEARS)               # pace that closes it by 2041

def stage_of(j):
    ms = [p['milestone'] for p in j['permits']]
    if any('CERTIFICATE OF OCCUPANCY ISSUED' in m for m in ms) or any(m == 'COMPLETE' and p['status'] == 'COMPLETE' for p, m in zip(j['permits'], ms)):
        return 'finished'
    if j['expired']: return 'expired'
    return 'building'

def area_names():
    m = json.load(open(os.path.join(ROOT, 'meta.json')))
    return {str(a['num']): a['name'] for a in m['areas']}

# --- zoning ---------------------------------------------------------------------------------------------------
SUFFIX = {'AVENUE': 'AVE', 'STREET': 'ST', 'PARKWAY': 'PKWY', 'BOULEVARD': 'BLVD', 'ROAD': 'RD', 'PLACE': 'PL', 'DRIVE': 'DR',
          'COURT': 'CT', 'TERRACE': 'TER', 'HIGHWAY': 'HWY', 'PLAZA': 'PLZ', 'LANE': 'LN', 'SQUARE': 'SQ'}
def norm_street(s):
    w = re.sub(r'[^A-Z0-9 ]', ' ', s.upper()).split()
    return ' '.join(SUFFIX.get(x, x) for x in w)

ADDR = re.compile(r'(\d{1,5})(?:\s*-\s*(\d{1,5}))?\s+([NSEW])\.?\s+([A-Za-z0-9 .\']+?)(?=\s*(?:,|;|\band\b|&|\s-\s|$|\())')
def zoning_addresses(title):
    t = title.split(' at ', 1)[1] if ' at ' in title else title
    t = re.split(r'\s+-\s+App', t)[0]
    out = []
    for m in ADDR.finditer(t):
        lo = int(m.group(1)); hi = int(m.group(2) or lo)
        if hi < lo:  # "2125-27" style
            hi = int(str(lo)[:len(str(lo)) - len(m.group(2))] + m.group(2))
        out.append((lo, max(lo, hi), m.group(3).upper(), norm_street(m.group(4))))
    return out

W2N = {w: i for i, w in enumerate('ZERO ONE TWO THREE FOUR FIVE SIX SEVEN EIGHT NINE TEN ELEVEN TWELVE THIRTEEN FOURTEEN FIFTEEN SIXTEEN SEVENTEEN EIGHTEEN NINETEEN'.split())}
W2N.update({'TWENTY': 20, 'THIRTY': 30, 'FORTY': 40, 'FIFTY': 50, 'SIXTY': 60, 'SEVENTY': 70, 'EIGHTY': 80, 'NINETY': 90})
UNITW = r'(?:NEW\s+)?(?:(?:RESIDENTIAL|DWELLING|RENTAL|APARTMENT|AFFORDABLE|MARKET[- ]RATE|SENIOR|CONDO(?:MINIUM)?|EFFICIENCY|TOWNHOUSE|TOWNHOME)\s+)*(?:DWELLING\s+UNITS?|RESIDENTIAL\s+UNITS?|UNITS|D\.\s?U\.?S?|DUS|APARTMENTS|TOWNHOMES|TOWNHOUSES)\b'
NUMP = r'(?:[A-Z]+(?:[- ][A-Z]+)?\s+)?\(?(\d{1,4})\)?'          # "twenty-six (26)" or "26"
TIERS = [
    # 1. stated totals
    re.compile(r'TOTAL\s+OF\s+' + NUMP + r'\s+' + UNITW),
    re.compile(r'(?:A\s+)?TOTAL\s+(?:NUMBER\s+)?OF\s+(?:RESIDENTIAL\s+|DWELLING\s+)*UNITS?\s*(?:IS|WILL BE|OF|:|-)?\s*\(?(\d{1,4})'),
    # 2. table rows: "Residential Dwelling Units: 26", "Number of Units 32", "# of Units 16 16 32" (last number = whole site)
    re.compile(r'(?:NUMBER|NO\.?|#)\s+OF\s+(?:RESIDENTIAL\s+|DWELLING\s+|PROPOSED\s+)*(?:DWELLING\s+)?UNITS?\s*[:\-]?\s*((?:\d{1,4}\s+){0,3}\d{1,4})\b'),
    re.compile(r'(?:RESIDENTIAL\s+)?DWELLING\s+UNITS?\s*[:\-]\s*(\d{1,4})\b'),
    # 3. "nine (9) dwelling units", "26 residential units"
    re.compile(NUMP + r'\s+' + UNITW),
    # 4. "a four-unit building", "five detached single-family homes"
    re.compile(r'\b(\d{1,3}|' + '|'.join(sorted(W2N, key=len, reverse=True)) + r')[- ](?:DWELLING[- ])?UNIT\s+(?:RESIDENTIAL\s+|APARTMENT\s+|MULTI-?FAMILY\s+|MASONRY\s+)*(?:BUILDING|DEVELOPMENT|PROJECT)'),
    re.compile(r'\b(\d{1,3}|' + '|'.join(sorted(W2N, key=len, reverse=True)) + r')\s+(?:\(\d+\)\s+)?(?:NEW\s+)?(?:DETACHED\s+|ATTACHED\s+)?SINGLE[- ]FAMILY\s+(?:HOMES|HOUSES|RESIDENCES|DWELLINGS)'),
]
NO_UNITS = re.compile(r'DWELLING UNITS?\s*[:\-]\s*(?:N/?A|NONE|0)\b|NO (?:DWELLING|RESIDENTIAL) UNITS')
EXIST = re.compile(r'(?:EXISTING|CURRENTLY|PRESENTLY|IMPROVED WITH|CONTAINS)[^.]{0,80}$')
def narrative_units(texts):
    """Homes the zoning application proposes, read from the narrative (OCR'd if scanned); None if not stated.
    Checks stated totals first, then table rows, then plain "N dwelling units" phrases (skipping ones about existing buildings)."""
    for t in sorted(texts, key=lambda t: 0 if 'NARRATIVE' in (t.get('file') or '').upper() else 1):
        txt = ' '.join(t.get('text', '').upper().replace('\u2019', "'").split())
        if not txt: continue
        for k, pat in enumerate(TIERS):
            ns = []
            for m in pat.finditer(txt):
                if k == 4 and EXIST.search(txt[max(0, m.start() - 120):m.start()]): continue
                v = [int(x) for x in re.findall(r'\d+', m.group(1))] or ([W2N[m.group(1)]] if m.group(1) in W2N else [])
                n = v[-1] if v else None
                if n and 0 < n < 3000 and not 1900 <= n <= 2100: ns.append(n)
            if ns:
                if k == 4:   # efficiency units listed separately from dwelling units: add them
                    eff = [int(x) for x in re.findall(r'\(?(\d{1,4})\)?\s+EFFICIENCY\s+UNITS', txt)]
                    du = [n for n in ns if n not in eff]
                    if eff and du and max(du) - max(eff) not in du: return max(du) + max(eff)
                return max(ns) if k in (2, 4, 5, 6) else ns[0]
        if NO_UNITS.search(txt): return 0
    return None

def load_zoning():
    M = json.load(gzip.open(os.path.join(RAW, 'elms_zoning.json.gz')))
    tdir = os.path.join(RAW, 'elms_text')
    out = []
    for m in M:
        title = m.get('title') or ''
        if not title.lower().startswith(('zoning reclassification', 'amendment of statements', 'residential-business planned', 'residential planned')) and 'Planned Development' not in title:
            continue
        sub = m.get('subStatus') or ''
        passed = sub.startswith('Passed')
        fin = (m.get('finalActionDate') or '')[:10]
        intro = (m.get('introductionDate') or '')[:10]
        rec = re.sub(r'[^A-Za-z0-9-]', '_', m.get('recordNumber') or '')
        texts = []
        fn = os.path.join(tdir, rec + '.json')
        if os.path.exists(fn):
            try: texts = json.load(open(fn)).get('texts') or []
            except Exception: texts = []
        app = re.search(r'App(?:lication)? No\.?\s*([0-9A-Z]+)', title)
        out.append(dict(rec=m.get('recordNumber'), mid=m.get('matterId'), title=title, intro=intro, final=fin, passed=passed, status=m.get('status'), sub=sub,
                        app=app.group(1) if app else '', type1=bool(app and app.group(1).endswith('T1')), pd='Planned Development' in title,
                        addrs=zoning_addresses(title), homes=narrative_units(texts) if texts else None, have_text=bool(texts)))
    return out

def link_zoning(Z, J):
    """Match each passed zoning change to permit projects at the same address issued after it was introduced."""
    idx = collections.defaultdict(list)
    for j in J:
        m = re.match(r'(\d+)\s+([NSEW])\s+(.+)', j['addr'])
        if m: idx[(m.group(2), norm_street(m.group(3)))].append((int(m.group(1)), j))
    for z in Z:
        z['projects'] = []
        if not z['intro']: continue
        d0 = datetime.date.fromisoformat(z['intro'])
        for lo, hi, dr, st in z['addrs']:
            for n, j in idx.get((dr, st), []):
                if lo - 8 <= n <= hi + 8 and n % 2 == lo % 2 and d0 <= j['date'] <= d0 + datetime.timedelta(days=6 * 365) and j['homes']:
                    if j not in z['projects']: z['projects'].append(j)
    return Z

# --- build ------------------------------------------------------------------------------------------------------
def main():
    P = load_permits(); J = projects(P, 'first')
    names = area_names()
    for j in J: j['stage'] = stage_of(j)
    last = max(p['date'] for p in P)
    years = []
    B = accuracy.bps()
    for y in range(2010, last.year + 1):
        js = [j for j in J if j['year'] == y and j['homes']]
        row = dict(year=y, homes=sum(j['homes'] for j in js), small=sum(j['homes'] for j in js if j['homes'] <= 4),
                   big=sum(j['homes'] for j in js if j['homes'] >= 5), projects=len(js),
                   finished=sum(j['homes'] for j in js if j['stage'] == 'finished'), expired=sum(j['homes'] for j in js if j['stage'] == 'expired'),
                   census=sum(B[y]) if y in B else None)
        years.append(row)
    # year to date vs same date last year
    def ytd(y, upto):
        return sum(j['homes'] for j in J if j['homes'] and j['year'] == y and (j['date'].month, j['date'].day) <= (upto.month, upto.day))
    ytd_now = ytd(last.year, last); ytd_prev = ytd(last.year - 1, last)
    day_of_year = (last - datetime.date(last.year, 1, 1)).days + 1
    # last 12 months
    since = last - datetime.timedelta(days=365)
    recent12 = [j for j in J if j['homes'] and j['date'] > since]
    # wards & community areas, last 3 full years + this year
    y0 = last.year - 3
    W = collections.defaultdict(lambda: dict(homes=0, projects=0, big=0, last12=0))
    C = collections.defaultdict(lambda: dict(homes=0, projects=0, last12=0))
    for j in J:
        if not j['homes'] or j['year'] < y0: continue
        w = W[j['ward'] or '?']; w['homes'] += j['homes']; w['projects'] += 1; w['big'] += j['homes'] >= 5
        c = C[j['ca'] or '?']; c['homes'] += j['homes']; c['projects'] += 1
        if j['date'] > since: w['last12'] += j['homes']; c['last12'] += j['homes']
    wards = sorted(({'ward': int(k), **v} for k, v in W.items() if k.isdigit()), key=lambda r: r['ward'])
    areas = sorted(({'num': int(k), 'name': names.get(k, k), **v} for k, v in C.items() if k.isdigit()), key=lambda r: r['num'])
    # projects list (5+ homes, last 3 years) and map points (2019 on)
    def short(desc):
        d = re.sub(r'^\W*(?:DIRECT DEVELOPER SERVICES|DDS|SPR|SC|SELF[- ]CERT(?:IFICATION)?)\W*(?:2019 C[BR]+C\W*)?', '', desc, flags=re.I)
        d = re.sub(r'^\W*(?:2019 C[BR]+C|CBC 2019)\W*', '', d, flags=re.I)
        return d[:140].capitalize()
    plist = [dict(date=str(j['date']), addr=j['addr'].title(), homes=j['homes'], ward=j['ward'], ca=names.get(j['ca'], ''), stage=j['stage'],
                  partial=j['partial_only'], permit=j['src']['permit'], what=short(j['src']['desc']))
             for j in sorted(J, key=lambda j: j['date'], reverse=True) if j['homes'] and j['homes'] >= 5 and j['year'] >= y0]
    pts = [[round(j['lon'], 5), round(j['lat'], 5), j['homes'], j['year'], {'finished': 0, 'building': 1, 'expired': 2}[j['stage']]]
           for j in J if j['homes'] and j['lon'] and j['year'] >= 2019]
    # zoning
    Z = link_zoning(load_zoning(), J)
    zy = collections.defaultdict(lambda: dict(introduced=0, passed=0, t1=0, homes=0, with_count=0, permitted_homes=0))
    for z in Z:
        if z['intro']: zy[int(z['intro'][:4])]['introduced'] += 1
        if z['passed'] and z['final']:
            r = zy[int(z['final'][:4])]; r['passed'] += 1; r['t1'] += z['type1']
            if z['homes']:
                r['homes'] += z['homes']; r['with_count'] += 1
                r['permitted_homes'] += min(z['homes'], sum(j['homes'] for j in z['projects']))
    zyears = [{'year': y, **zy[y]} for y in sorted(zy) if y >= 2013]
    texted = [z for z in Z if z['have_text'] and z['passed']]
    zrecent = [dict(rec=z['rec'], mid=z['mid'], final=z['final'], title=re.sub(r'\s*-\s*App(?:lication)? No\.?.*$', '', re.sub(r'^Zoning Reclassification Map No\. [0-9A-Z-]+ at ', '', z['title']))[:110], homes=z['homes'],
                    permitted=sum(j['homes'] for j in z['projects']) or 0, first_permit=str(min(j['date'] for j in z['projects'])) if z['projects'] else None)
               for z in sorted(Z, key=lambda z: z['final'] or '', reverse=True) if z['passed'] and z['homes'] and z['final'] >= str(last.year - 2)]
    # time from zoning approval to first permit, for matched projects
    lags = sorted((min(j['date'] for j in z['projects']) - datetime.date.fromisoformat(z['final'])).days
                  for z in Z if z['passed'] and z['final'] and z['projects'] and z['homes'])
    lags = [d for d in lags if d >= -60]
    # accuracy
    acc_rows = accuracy.yearly(J, 2010, max(B))
    acc = dict(census=accuracy.summary(acc_rows), census_rows=[dict(year=r['year'], ours=r['ours_total'], census=r['census_total']) for r in acc_rows])
    for name, fn in (('tuning', 'sample_checked.csv'), ('tuning2', 'sample2_checked.csv'), ('holdout', 'sample3_checked.csv')):
        try: acc[name] = score(fn)
        except FileNotFoundError: pass
    try:
        H = json.load(open(os.path.join(os.path.dirname(__file__), 'zsample_checked.json')))
        zok = zh = zp = 0
        for h in H:
            fn = os.path.join(RAW, 'elms_text', re.sub(r'[^A-Za-z0-9-]', '_', h['record']) + '.json')
            pp = narrative_units(json.load(open(fn))['texts']) if os.path.exists(fn) else None
            zok += (h['hand_homes'] or None) == (pp or None); zh += h['hand_homes'] or 0; zp += pp or 0
        acc['zoning'] = dict(n=len(H), exact=zok, hand_homes=zh, parser_homes=zp)
    except FileNotFoundError: pass
    unknown = sum(1 for p in P if p['homes'] is None and p['why'] == 'housing, no count' and p['date'].year >= last.year - 3)
    data = dict(updated=str(TODAY), through=str(last), goal=dict(hold=HOLD, close=CLOSE, built_anyway=BUILT_ANYWAY, gap_now=CITY_GAP_NOW, gap_growth=CITY_GAP_GROWTH),
                ytd=dict(year=last.year, homes=ytd_now, prev=ytd_prev, days=day_of_year, needed_so_far=round(CLOSE * day_of_year / 365)),
                last12=dict(homes=sum(j['homes'] for j in recent12), projects=len(recent12), big=sum(j['homes'] for j in recent12 if j['homes'] >= 5)),
                years=years, wards=wards, areas=areas, projects=plist, points=pts,
                zoning=dict(years=zyears, recent=zrecent[:150], with_text=len(texted), lag_days_median=lags[len(lags) // 2] if lags else None, lag_n=len(lags)),
                accuracy=acc, unknown_recent=unknown, geo=geo())
    json.dump(data, open(os.path.join(OUT, 'data.json'), 'w'), separators=(',', ':'))
    print('tracker/data.json', os.path.getsize(os.path.join(OUT, 'data.json')), 'bytes; through', last, '; ytd', ytd_now, 'vs', ytd_prev, '; zoning with text', len(texted))

def geo():
    m = json.load(open(os.path.join(ROOT, 'meta.json')))
    out = []
    for f in m['outlines']['features']:
        g = f['geometry']; rings = g['coordinates'] if g['type'] == 'Polygon' else [p[0] for p in g['coordinates']]
        out.append([f['properties']['num'], [[[round(x, 4), round(y, 4)] for x, y in r] for r in rings[:1]]])
    return out

def score(fn):
    from units import classify
    rows = list(csv.DictReader(open(os.path.join(os.path.dirname(__file__), fn))))
    ok = hand = par = 0
    for r in rows:
        h = r['hand_homes'].strip(); hk = r['hand_kind'].strip().lower()
        ph, pk = classify(r['description'])
        hh = None if h in ('', '?', 'unknown') else int(h)
        ha = 0 if hk in ('partial', 'revision', 'not housing') or hh is None else hh
        pa = 0 if pk in ('partial permit', 'revision') or ph is None else ph
        hand += ha; par += pa; ok += ha == pa
    return dict(n=len(rows), exact=ok, hand_homes=hand, parser_homes=par)

if __name__ == '__main__':
    main()
