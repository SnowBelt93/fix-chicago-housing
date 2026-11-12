"""Homes torn down, from the city's demolition permits (for Progress → Homes added). Runs daily after fetch.py.

How a permit becomes a count of homes:
  1. Permits for only a garage, shed, porch or the like are skipped (the description names nothing else).
  2. The permit's point is matched to a building in the city's 2013 footprints: the building it falls inside, else the
     nearest one within 12 m (permit points usually sit at the front of the lot). Each building counts once. A match is
     thrown out when the footprint is more than a story and a half taller than the building the permit describes
     (a "1 story masonry building" next to a tower is not the tower), or lists more than 16 homes per described story.
  3. Homes = the units the footprint data lists for that building. If it lists none and the permit calls the building a
     residence, 1 home is counted (2 if it says multi-unit or two-flat). A coach house counts 1. A plain "residence"
     (not multi-unit, flats, apartments or mixed use) matched to a footprint with more than 4 homes counts 1, since the
     match is probably the building next door. Permits that call the building commercial, industrial, a church or a
     school count 0.
  4. A residence permit with no 2013 building within 12 m (built later, or a point that is off) counts 1 home.
So this is homes in buildings that got a demolition permit, by the year of the permit: not every permit is carried out,
and the 2013 unit counts miss later conversions. Writes tracker/teardowns.json:
  {"through": "YYYY-MM-DD", "years": {"2013": homes, ...}, "permits": {...}, "est": {...} (homes from rules 3-4's guesses),
   "last12": homes in the 12 months to "through", "wards": {"1": homes this year and last, ...}}
Needs numpy and shapely. Inputs: tools/raw/tracker/permits_wreck.csv.gz, b/*.wasm, meta.json."""
import gzip, json, math, os, re, struct, csv, collections, datetime
import numpy as np, shapely
from shapely.strtree import STRtree
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(os.path.dirname(HERE))
DECK = 111319.49; KX = DECK * math.cos(math.radians(41.85)); NEAR = 12.0
meta = json.load(open(os.path.join(ROOT, 'meta.json')))
polys, U, ST = [], [], []
for a in meta['areas']:
    num = a['num']; n13 = a.get('n13') or a['n']
    buf = open(os.path.join(ROOT, 'b', f'{num}.wasm'), 'rb').read()
    N, V = struct.unpack_from('<II', buf, 0); lon0, lat0 = struct.unpack_from('<dd', buf, 8)
    q = np.frombuffer(buf, '<i2', 2 * V, 24).reshape(-1, 2).astype(float) * 0.5
    o = 24 + 4 * V; nv = np.frombuffer(buf, np.uint8, N, o); po = o + 3 * N + ((3 * N) % 2)
    un = np.frombuffer(buf, '<u2', N, po); sto = np.frombuffer(buf, np.uint8, N, o + N)
    st = np.concatenate([[0], np.cumsum(nv.astype(np.int64))]).astype(np.int64); kx = DECK * math.cos(math.radians(lat0))
    for i in range(n13):
        p_ = q[st[i]:st[i + 1]]
        if len(p_) < 3: continue
        polys.append(shapely.Polygon(np.column_stack([(lon0 + p_[:, 0] / kx) * KX, (lat0 + p_[:, 1] / DECK) * DECK]))); U.append(int(un[i])); ST.append(int(sto[i]))
polys = np.array(polys, dtype=object); U = np.array(U); ST = np.array(ST); tree = STRtree(polys)
print('2013 buildings', len(polys), 'homes', int(U.sum()))

MINOR = re.compile(r'GARAGE|SHED|PORCH|CANOPY|\bSIGN|TANK|FENCE|POOL|\bDECK|SILO|CHIMNEY|STACK|STAIR|TRAILER|KIOSK|BILLBOARD|ADDITION|\bWALL\b')
MAIN = re.compile(r'RESIDEN|DWELLING|HOUSE|FLAT|BUILDING|BLDG|FAMILY|APARTMENT|APT|STRUCTURE|S\.?F\.?R|COTTAGE|MULTI[- ]?(?:UNIT|FAMILY)|\bUNITS?\b|STORE|COMMERCIAL|CHURCH|SCHOOL|FACTORY|WAREHOUSE|INDUSTRIAL|MIXED')
ONLY = re.compile(r'GARAGES? ONLY|ONLY THE GARAGE|NO WORK TO|(?:REAR|FRONT) PORCH(?:ES)? ONLY|ADDITION ONLY|PARTIAL')
STORY = re.compile(r'(\d+)(\s*1/2|\.5)?\s*[- ]?(?:STORY|STORIES|STY)')
RES = re.compile(r'RESIDEN|DWELLING|HOUSE(?!\s*OF)|\bFLAT|S\.?F\.?R\b|FAMILY|COTTAGE|APARTMENT|\bAPT|MULTI[- ]?UNIT|COACH|BUNGALOW|MIXED[- ]USE')
MULTI = re.compile(r'MULTI|TWO[- ]?FLAT|2[- ]?FLAT|THREE[- ]?FLAT|3[- ]?FLAT|TWO[- ]FAMILY|APARTMENT|\bAPT')
PLURAL = re.compile(r'MULTI|FLAT|APARTMENT|\bAPT|MIXED|\bUNITS?\b|D\.?U\.?\b|FAMILY')
NONRES = re.compile(r'COMMERCIAL|COMMERICIAL|INDUSTRIAL|WAREHOUSE|FACTORY|CHURCH|SCHOOL|OFFICE|RETAIL|\bSTORE|GAS STATION|SERVICE STATION|\bBANK\b|RESTAURANT|HOSPITAL|MEDICAL|MANUFACTUR|HOTEL|MOTEL|THEAT|FIELD ?HOUSE|GREENHOUSE|WAREHOUSE|PUMP ?HOUSE|GUARD ?HOUSE|CAR ?WASH')
rows = sorted(csv.DictReader(gzip.open(os.path.join(ROOT, 'tools', 'raw', 'tracker', 'permits_wreck.csv.gz'), 'rt')), key=lambda r: r['issue_date'])
through = max(r['issue_date'][:10] for r in rows)
T = datetime.date.fromisoformat(through); yr0 = T.replace(year=T.year - 1)
homes, permits, est = collections.Counter(), collections.Counter(), collections.Counter()
wards, last12, used, skipped, skipped_tall = collections.Counter(), 0, set(), collections.Counter(), [0]
for r in rows:
    y = int(r['issue_date'][:4]); d = (r.get('work_description') or '').upper()
    if (MINOR.search(d) and not MAIN.search(d)) or ONLY.search(d): skipped['minor structure only'] += 1; continue
    res = bool(RES.search(d)); nonres = bool(NONRES.search(d)) and not res
    try: pt = shapely.Point(float(r['longitude']) * KX, float(r['latitude']) * DECK)
    except (ValueError, TypeError): skipped['no location'] += 1; continue
    idx = tree.query(pt, predicate='within'); j = None
    if len(idx): j = int(idx[0])
    else:
        k = tree.nearest(pt)
        if k is not None and shapely.distance(polys[k], pt) <= NEAR: j = int(k)
    m = STORY.search(d)
    if j is not None and m and (ST[j] > int(m.group(1)) + (0.5 if m.group(2) else 0) + 1.5 or U[j] > 16 * max(1, int(m.group(1)))): j = None; skipped_tall[0] += 1   # the footprint is a much bigger building than the one described
    if j is not None and j in used: skipped['same building again'] += 1; continue
    if j is not None: used.add(j)
    h = 0; guess = 0
    if nonres: h = 0
    elif 'COACH' in d: h = guess = 1
    elif j is not None and U[j] > 4 and res and not PLURAL.search(d): h = guess = 1
    elif j is not None and U[j] > 0: h = int(U[j])
    elif res: h = guess = 2 if MULTI.search(d) else 1
    if j is None and not res: skipped['no building nearby'] += 1; continue
    permits[y] += 1; homes[y] += h; est[y] += guess
    day = datetime.date.fromisoformat(r['issue_date'][:10])
    if day > yr0: last12 += h
    if y >= T.year - 1 and r.get('ward', '').strip().isdigit(): wards[int(r['ward'])] += h
out = {'through': through, 'years': {str(y): homes[y] for y in sorted(homes)}, 'permits': {str(y): permits[y] for y in sorted(permits)},
       'est': {str(y): est[y] for y in sorted(est)}, 'last12': last12, 'wards': {str(w): wards[w] for w in sorted(wards)}, 'skipped': dict(skipped), 'tallerFootprint': skipped_tall[0]}
os.makedirs(os.path.join(ROOT, 'tracker'), exist_ok=True)
json.dump(out, open(os.path.join(ROOT, 'tracker', 'teardowns.json'), 'w'), separators=(',', ':'))
print(json.dumps(out)[:900])
