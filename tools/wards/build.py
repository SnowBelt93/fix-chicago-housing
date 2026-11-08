#!/usr/bin/env python3
"""Build wards/data/wards.json for the ward housing record (Shape Chicago /wards/).

Inputs (all from GitHub Actions downloads):
  tools/raw/wards/ord/<record>.json   every final zoning map amendment / planned development since 2013: title, status, date,
                                      and the first two pages of the ordinance (which say what district it changes from and to)
  tools/raw/wards/key_matters.json    citywide housing legislation with every alderperson's vote
  tools/raw/wards/ward_offices.csv    current alderpeople
  tools/raw/budget/votes.json         budget roll calls
  tools/raw/tracker/elms_text/        zoning narratives (planned homes), parsed with the permit tracker's own reader
  lot/data/a, lot/data/t              the lot tool's address index: house number -> parcel -> ward (2023 ward map)
  tracker/data.json                   homes permitted by ward
Per ward: the alderperson, how they voted on the key citywide housing laws and the last two budgets, and every zoning
change passed at an address in the ward (current boundaries), classed as allowing more homes per lot (up), fewer (down),
a planned development, or neither, with the homes the application planned when the narrative says."""
import json, os, re, glob, csv, collections, sys
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
from prep_zoning import mla                                  # minimum lot area per home by district (Title 17)
sys.path.insert(0, os.path.join(ROOT, 'tools', 'tracker'))
import build as tracker                                      # narrative_units: homes stated in a zoning narrative
RAW = os.path.join(ROOT, 'tools', 'raw')
OUT = os.path.join(ROOT, 'wards', 'data'); os.makedirs(OUT, exist_ok=True)

# ---- address -> ward through the lot tool's index
SH = {}; TL = {}
def shard(name): return re.sub(r'[^A-Z0-9]', '', re.sub(r'^[NSEW] ', '', name))[:2] or '_'
def tile(ix, iy):
    k = (ix, iy)
    if k not in TL:
        p = os.path.join(ROOT, 'lot', 'data', 't', f'{ix}_{iy}.json')
        TL[k] = json.load(open(p))['p'] if os.path.exists(p) else []
    return TL[k]
SUFX = {'AVENUE': 'AVE', 'STREET': 'ST', 'BOULEVARD': 'BLVD', 'ROAD': 'RD', 'DRIVE': 'DR', 'PLACE': 'PL', 'PARKWAY': 'PKWY', 'COURT': 'CT', 'TERRACE': 'TER', 'LANE': 'LN', 'HIGHWAY': 'HWY'}
def norm(st):
    st = re.sub(r'[^A-Z0-9 ]', ' ', st.upper()); w = st.split()
    if w and w[-1] in SUFX: w[-1] = SUFX[w[-1]]
    return ' '.join(w)
def ward_of(title):
    m = re.search(r'\bat\s+(\d{1,5})[A-Z]?(?:\s*-\s*\d{1,5}[A-Z]?)?(?:\s*(?:,|and|&)\s*\d{1,5}[A-Z]?(?:-\d{1,5})?)*\s+([NSEW]\.?\s+[A-Za-z0-9 .\']+?)(?:\s*[-–,;]|\s+and\b|\s*$)', title)
    if not m: return None, None
    num, st = int(m.group(1)), norm(m.group(2))
    d = SH.get(shard(st))
    if d is None:
        p = os.path.join(ROOT, 'lot', 'data', 'a', shard(st) + '.json'); d = SH[shard(st)] = json.load(open(p)) if os.path.exists(p) else {}
    L = d.get(st)
    if not L:   # try without the suffix, then any street with the same name
        base = re.sub(r' (AVE|ST|BLVD|RD|DR|PL|PKWY|CT|TER|LN|HWY)$', '', st)
        cands = [k for k in d if re.sub(r' (AVE|ST|BLVD|RD|DR|PL|PKWY|CT|TER|LN|HWY)$', '', k) == base]
        if len(cands) != 1: return None, st
        L = d[cands[0]]
    best = min(L, key=lambda r: (abs(r[0] - num) + (0 if (r[0] - num) % 2 == 0 else 50)))
    if abs(best[0] - num) > 150: return None, st
    p = tile(best[1], best[2])
    w = p[best[3]][10] if best[3] < len(p) else None
    return (int(w) if w else None), st

# ---- the district an ordinance changes from and to
def dist(s):
    s = s.upper().replace(' ', '').replace('—', '-').replace('–', '-')
    s = re.sub(r'(?<=[A-Z])L(?=-?\d)', '1', s)            # OCR: "Bl-1" -> "B1-1"
    s = s.replace('O', '0') if re.match(r'^[A-Z]{1,2}[0O]', s) else s
    m = re.match(r'^(RS|RT|RM|B|C|M|PMD|DX|DC|DR|DS|POS|T|PD)-?(\d(?:\.5)?)?(?:-(\d(?:\.5)?))?', s)
    if not m: return None
    a, b, c = m.groups()
    if a in ('RS', 'RT', 'RM'): return f'{a}-{b}' if b else a
    if a in ('B', 'C', 'M'): return f'{a}{b}-{c}' if b and c else (f'{a}{b}' if b else a)
    if a in ('DX', 'DC', 'DR', 'DS'): return f'{a}-{b or c}' if (b or c) else a
    return a
FROM = re.compile(r'changing\s+all\s*(?:of\s*)?(?:the|ofthe)\s+(.{1,90})', re.I)
TO = re.compile(r'\bto\s+(?:those|th0se)\s+(?:of|0f)\s+(?:an?|the)?\s*(.{1,90})', re.I)
TOK = re.compile(r'\b((?:RS|RT|RM|B|C|M|DX|DC|DR|DS|PMD|POS)\s?[-—–]?\s?[\dlIO](?:\.5)?(?:\s?[-—–]\s?[\dlIO](?:\.5)?)?|PD)\b')
def pick(seg):
    if re.match(r'\s*(?:Residential[- ]Business\s+|Institutional\s+|Business\s+|Manufacturing\s+|Waterway\s+|Transportation\s+)?Planned\s+Development', seg, re.I): return 'PD'
    m = TOK.search(seg[:40])
    return dist(m.group(1).replace('l', '1').replace('I', '1')) if m else None
NAR_FT = re.compile(r'\bFrom\s+(?:an?\s+|the\s+)?(\S{2,8})(?:\s+[A-Za-z(),\-]+){0,8}?\s+to\s+(?:an?\s+|the\s+)?(\S{2,8})', re.I)
NAR_TO = re.compile(r'Proposed\s+Zoning(?:\s+District)?\s*[:\-]?\s*§?\s*(.{1,40})', re.I)
NAR_FR = re.compile(r'(?:Existing|Current)\s+Zoning(?:\s+District)?\s*[:\-]?\s*(.{1,40})|(?:located|currently zoned|presently zoned|is zoned)\s+(?:in\s+)?(?:an?|the)?\s*(.{1,30})(?:zoning\s+)?district', re.I)
def change(text):
    t = re.sub(r'\s+', ' ', text or '')
    a, b = FROM.search(t), TO.search(t)
    fr, to = (pick(a.group(1)) if a else None), (pick(b.group(1)) if b else None)
    if not (fr and to):                       # zoning narratives: "From RS-3 to RM-4.5", "Proposed Zoning: B2-3", "located in an RS-3 district"
        for m in NAR_FT.finditer(t):
            f2, t2 = pick(m.group(1)), pick(m.group(2))
            if f2 and t2: fr, to = fr or f2, to or t2; break
    if not to:
        m = NAR_TO.search(t); to = pick(m.group(1)) if m else None
    if not fr:
        m = NAR_FR.search(t); fr = pick(m.group(1) or m.group(2)) if m else None
    return fr, to
def homes_allowed(d):        # homes per 10,000 sq ft of lot under a district, for up/down; None if not housing-by-density
    if not d: return None
    if d.startswith(('DX', 'DC', 'DR')):
        n = re.search(r'-(\d+(?:\.\d)?)', d); return float(n.group(1)) * 10000 / 900 if n else None
    if d.startswith(('M', 'PMD', 'POS', 'T', 'DS')) or re.match(r'^C3', d): return 0
    v = mla(d.replace('RM-6.5', 'RM-6.5'))
    return 10000 / v if v else None
def lot_homes(d):          # homes allowed on a typical 25 x 125 ft (3,125 sq ft) Chicago lot; None if unknown or a PD
    if not d or d == 'PD': return None
    h = homes_allowed(d)
    if h is None: return None
    if h == 0: return 0
    n = int(h * 3125 / 10000 + 1e-9)
    return max(1, n) if d.startswith(('R', 'B', 'C')) else n
def council_roll(r):        # the final City Council roll call on this matter, {normalized surname: vote}
    for act, date, body, vs in reversed(r.get('votes') or []):
        if body == 'City Council' and vs: return {re.sub(r'[^a-z]', '', (n or '').lower().split(',')[0]): v for n, v in vs}
    return None
def kind(f, to):
    if to == 'PD' or f == 'PD': return 'pd'
    a, b = homes_allowed(f), homes_allowed(to)
    if a is None or b is None: return 'other'
    if b > a * 1.01: return 'up'
    if b < a * 0.99: return 'down'
    return 'same'

def eltext(rec):
    p = os.path.join(RAW, 'tracker', 'elms_text', rec.replace('/', '_') + '.json')
    if not os.path.exists(p): return ''
    try:
        d = json.load(open(p)); texts = d.get('texts')
        if isinstance(texts, str): texts = eval(texts)
        return ' '.join(x.get('text', '') for x in texts or [])
    except Exception: return ''
# ---- planned homes from the permit tracker's narrative reader
def planned(rec):
    p = os.path.join(RAW, 'tracker', 'elms_text', rec.replace('/', '_') + '.json')
    if not os.path.exists(p): return None
    try:
        d = json.load(open(p)); texts = d.get('texts')
        if isinstance(texts, str): texts = eval(texts)  # older cache rows stored the list as a string
        return tracker.narrative_units([x.get('text', '') for x in texts or []])
    except Exception: return None

import gzip
MID = {m.get('recordNumber'): m.get('matterId') for m in json.load(gzip.open(os.path.join(RAW, 'tracker', 'elms_zoning.json.gz'), 'rt'))}
Z = []; miss = collections.Counter()
for f in glob.glob(os.path.join(RAW, 'wards', 'ord', '*.json')):
    r = json.load(open(f))
    if not (r.get('sub') or '').startswith(('Passed', 'Signed', 'Approved')): continue
    title = r.get('title') or ''
    w, st = ward_of(title)
    if not w: miss['no ward'] += 1; continue
    fr, to = change(r.get('text'))
    if not (fr and to):                        # newer matters: the ordinance text often lives in the tracker's OCR cache
        fr2, to2 = change(eltext(r['record'])); fr, to = fr or fr2, to or to2
    k = kind(fr, to) if (fr or to) else ('pd' if re.search(r'Planned Development|Residential[- ]Business', title, re.I) else 'other')
    addr = re.sub(r'^.*?\bat\s+', '', title); addr = re.sub(r'\s*-\s*App(?:lication)?\.? No\.?.*$', '', addr).strip()
    Z.append({'w': w, 'r': r['record'], 'm': MID.get(r['record']), 'd': (r.get('final') or '')[:10], 'a': addr[:80], 'f': fr, 't': to, 'k': k, 'h': planned(r['record']),
              'hf': lot_homes(fr), 'ht': lot_homes(to), 'sp': [x for x in (r.get('sponsors') or []) if x and 'Transmittal' not in x],
              'rc': council_roll(r)})
print('zoning changes placed', len(Z), dict(miss), collections.Counter(z['k'] for z in Z))

# ---- alderpeople and their votes
norm_name = lambda n: re.sub(r'[^a-z]', '', n.lower().split(',')[0])
ALD = {}
for r in csv.DictReader(open(os.path.join(RAW, 'wards', 'ward_offices.csv'), encoding='utf-8-sig')):
    ALD[int(r['WARD'])] = {'name': r['ALDERMAN'].strip(), 'email': r.get('EMAIL', '').strip(), 'phone': r.get('WARD PHONE', '').strip(), 'web': (r.get('WEBSITE') or '').strip()}
KEY = [  # citywide housing laws with contested or notable roll calls; "yes" says what a Yea vote did
 ('SO2022-2000', 'Homes near transit (ETOD)', 'More homes allowed near the L and busy bus routes, with less required parking.', 'more'),
 ('SO2025-0015560', 'Green Social Housing', 'Created a city-backed fund to build mixed-income homes the city keeps owning.', 'more'),
 ('SO2026-0022453', 'Coach houses in single-family areas', 'Let more single-family areas opt into backyard and basement apartments.', 'more'),
 ('O2025-0019672', 'Taller buildings on commercial streets', 'Allowed extra height in some B3 and C3 districts.', 'more'),
 ('SO2021-1226', 'Affordable Requirements Ordinance (2021)', 'Raised the share of affordable homes required in new buildings that need city help or a zoning change.', 'afford'),
 ('O2021-746', 'Demolition fee near the 606 and in Pilsen', 'Charged a fee to tear down homes in those areas, to slow teardowns of older, cheaper buildings.', 'fewer'),
]
KEYR = json.load(open(os.path.join(RAW, 'wards', 'key_matters.json')))
BUD = json.load(open(os.path.join(RAW, 'budget', 'votes.json')))
REC = {r['recordNumber']: r for r in KEYR + BUD}
def roll(rec):
    r = REC.get(rec); acts = [a for a in (r or {}).get('actions') or [] if a.get('votes')]
    if not acts: return {}, None, None
    a = acts[-1]; c = collections.Counter(v['vote'] for v in a['votes'])
    return {norm_name(v['voterName']): v['vote'] for v in a['votes']}, (a.get('actionDate') or '')[:10], f"{c.get('Yea', 0)}–{c.get('Nay', 0)}"
votes = []
for rec, title, yes, eff in KEY + [('SO2025-0020516', "The Council's 2026 budget", "The Council's own budget, without the Mayor's head tax.", 'budget'), ('SO2024-0013682', "The Mayor's 2025 budget", 'The 2025 budget, with new taxes including a higher cloud tax.', 'budget')]:
    by, date, tally = roll(rec)
    if not by: print('no roll call', rec); continue
    votes.append({'rec': rec, 'id': REC[rec]['matterId'], 't': title, 'yes': yes, 'eff': eff, 'd': date, 'tally': tally, 'by': by})
# ---- permits by ward from the tracker
TR = json.load(open(os.path.join(ROOT, 'tracker', 'data.json')))
PW = {w['ward']: w for w in TR.get('wards', [])}
wards = []
for w in range(1, 51):
    a = ALD.get(w, {'name': '?'}); nm = norm_name(a['name'])
    zz = sorted([z for z in Z if z['w'] == w], key=lambda z: z['d'], reverse=True)
    zz = [dict(z) for z in zz]
    for z in zz:
        rc = z.pop('rc'); sp = z.pop('sp')
        if z['d'] >= '2023-05-15':      # this term: the current alderperson's own record on it
            z['v'] = (rc or {}).get(nm)
            z['by'] = any(norm_name(x) == nm for x in sp) or None
    term = [z for z in zz if z['d'] >= '2023-05-15']
    cnt = lambda L, k: sum(1 for z in L if z['k'] == k)
    wards.append({'w': w, 'ald': a, 'votes': [[v['rec'], v['by'].get(nm)] for v in votes],
                  'term': {k: cnt(term, k) for k in ('up', 'down', 'pd', 'same', 'other')}, 'termHomes': sum(z['h'] or 0 for z in term if z['k'] in ('up', 'pd')),
                  'all': {k: cnt(zz, k) for k in ('up', 'down', 'pd', 'same', 'other')}, 'permits': PW.get(w), 'z': zz[:60]})
json.dump({'votes': [{k: v[k] for k in ('rec', 'id', 't', 'yes', 'eff', 'd', 'tally')} for v in votes], 'wards': wards,
           'zoningSince': min(z['d'] for z in Z), 'trackerYears': TR.get('wardsYears') or 'last three full years and this year'},
          open(os.path.join(OUT, 'wards.json'), 'w'), separators=(',', ':'))
print('wrote', sum(len(w['z']) for w in wards), 'zoning rows;', 'term totals', collections.Counter({k: sum(w['term'][k] for w in wards) for k in ('up', 'down', 'pd', 'same', 'other')}))

# hearing calendar: City Council and committee meetings from the City Clerk (tools/raw/wards/meetings.json, saved by
# tools/wards/fetch.py) -> wards/data/meetings.json; the pages show the ones still ahead
def short_loc(l):
    l = (l or '').split(' - ')[0]
    if 'City Hall' in l and '121 North LaSalle' in l:
        room = 'Council Chamber' if 'Chamber' in l else re.sub(r'^Room\s*', '', l.split(',')[0]).strip()
        return 'City Hall, ' + (room if room == 'Council Chamber' else 'Room ' + room)
    return l
def note(c):
    t = re.split(r'\*|Written|Public Written|Direct Introduction', c or '')[0].strip()
    t = re.sub(r'\s*\n-\s*', ', ', t, count=1); t = re.sub(r'\s*\n-\s*', ', ', t); t = re.sub(r'\s+', ' ', t)
    if len(t) > 150: t = t[:150].rsplit(' ', 1)[0].rstrip(',') + '…'
    return t or None
mp = os.path.join(RAW, 'wards', 'meetings.json')
if os.path.exists(mp):
    raw = json.load(open(mp)); seen, out = set(), []
    for res in raw.values():
        for m in (res or {}).get('data') or []:
            if m.get('meetingId') in seen or not m.get('date'): continue
            seen.add(m['meetingId'])
            files = m.get('files') or []
            ag = next((f['path'] for f in files if (f.get('attachmentType') or '').lower() == 'agenda'), None)
            dl = re.search(r'Deadline:\s*(.+)$', m.get('comment') or '')
            out.append({'id': m['meetingId'], 'd': m['date'], 'b': m.get('body') or '', 's': m.get('bodyAbbreviation') or '',
                        'loc': short_loc(m.get('location')), 'ag': ag, 'v': ((m.get('videoLink') or [None])[0] if isinstance(m.get('videoLink'), list) else m.get('videoLink')) or None,
                        'c': dl.group(1).strip() if dl else None, 'st': m.get('status') or '',
                        'n': note(m.get('comment'))})
    out.sort(key=lambda m: m['d'])
    json.dump({'updated': max((m['d'] for m in out), default=None), 'meetings': out}, open(os.path.join(OUT, 'meetings.json'), 'w'), separators=(',', ':'))
    print('meetings', len(out))
