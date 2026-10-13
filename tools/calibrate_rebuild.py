"""Calibrates the game's rebuild rate (REBUILD_OBS in index.html) from Chicago's own building permits.

For each small home (1-4 units, built before 2000) in the city's 2013 building footprints, it asks whether a
residential new-construction permit was issued on that lot in 2013-2025 (permit point within 5 m of the building).
It reports the 15-year rebuild rate on lots where today's zoning map already allows more homes, by neighborhood
demand factor, corrected for the share of known teardown-rebuilds (a residential wrecking permit plus new
construction at the same address) that the matching finds. It also compares lots that allow more with lots that
don't, within each demand band.

Inputs: tools/raw/permits_2013_on.csv.gz and tools/raw/zoning.geojson.gz (from .github/workflows/fetch-permits.yml),
b/*.wasm and meta.json. Run: python3 tools/calibrate_rebuild.py
Limitation: the zoning map is today's, so lots rezoned for a project during 2013-2025 count as "already allowed".
"""
import gzip, json, math, os, re, struct, csv, collections, sys
import numpy as np, shapely
from shapely.strtree import STRtree
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
ROOT = os.path.dirname(HERE)
from prep_zoning import mla
DECK = 111319.49
meta = json.load(open(f'{ROOT}/meta.json'))
# zoning
gj = json.load(gzip.open(f'{ROOT}/tools/raw/zoning.geojson.gz', 'rt'))
zg, zz = [], []
for f in gj['features']:
    if not f.get('geometry'): continue
    p = {k.lower(): v for k, v in (f.get('properties') or {}).items()}
    try: g = shapely.geometry.shape(f['geometry'])
    except Exception: continue
    if g.is_empty: continue
    zg.append(g); zz.append(p.get('zone_class'))
ztree = STRtree(zg); print('zoning polygons', len(zg))
# permits: residential new construction 2013-2025 with coordinates
RES_RE = re.compile(r'DWELLING|D\.\s?U\.?|\bDU\b|SINGLE[- ]FAMILY|RESIDEN|\bUNITS?\b|APARTMENT|TOWN ?HOUSE|ROW ?HOUSE|CONDO|\bFLAT\b|TWO[- ]FLAT|THREE[- ]FLAT|S\.F\.R|SFR|HOME')
NOT_RE = re.compile(r'\bTENT\b|STAGE|TRAILER|BLEACHER|CANOPY|SIGN\b|TEMPORARY|RETAIL|RESTAURANT|SCHOOL|CHURCH|WAREHOUSE|OFFICE BUILDING|PARKING (LOT|STRUCTURE)')
def units_in(desc):
    d = desc.upper()
    m = re.search(r'(\d+)\s*(?:-|\s)?\s*(?:D\.?\s?U\.?|DWELLING|RESIDENTIAL UNITS?|UNITS?|APARTMENTS?)', d)
    if m: return int(m.group(1))
    if re.search(r'SINGLE[- ]FAMILY|S\.F\.R|\bSFR\b|ONE[- ]FAMILY', d): return 1
    if re.search(r'TWO[- ]FLAT|2[- ]FLAT|TWO[- ]FAMILY|DUPLEX', d): return 2
    if re.search(r'THREE[- ]FLAT|3[- ]FLAT', d): return 3
    return None
P = []
for r in csv.DictReader(gzip.open(f'{ROOT}/tools/raw/permits_2013_on.csv.gz', 'rt')):
    if r['permit_type'] != 'PERMIT - NEW CONSTRUCTION': continue
    y = int(r['issue_date'][:4])
    if y > 2025: continue
    d = r['work_description'].upper()
    if not RES_RE.search(d) or NOT_RE.search(d): continue
    if not d.strip() or 'GARAGE' in d and not re.search(r'DWELLING|D\.\s?U|FAMILY|RESIDEN|UNIT|FLAT', d): continue
    try: lat, lon = float(r['latitude']), float(r['longitude'])
    except ValueError: continue
    P.append((lon, lat, y, units_in(d)))
P = np.array([(a, b, c, -1 if u is None else u) for a, b, c, u in P], dtype=float)
print('residential new-construction permits 2013-2025 with coordinates:', len(P), 'with a unit count:', int((P[:, 3] >= 0).sum()))
ppts = shapely.points(P[:, 0], P[:, 1]); ptree = STRtree(ppts)
# buildings
import collections
addr = lambda r: (r['street_number'].strip(), r['street_direction'].strip(), r['street_name'].strip().upper())
wreck = collections.defaultdict(list); NC = []
for r in csv.DictReader(gzip.open(f'{ROOT}/tools/raw/permits_2013_on.csv.gz', 'rt')):
    y = int(r['issue_date'][:4])
    if 'WRECK' in r['permit_type'] and re.search(r'RESIDEN|DWELLING|FLAT|COTTAGE|HOUSE|D\.U', r['work_description'].upper()): wreck[addr(r)].append(y)
    elif r['permit_type'] == 'PERMIT - NEW CONSTRUCTION' and y <= 2025:
        d = r['work_description'].upper()
        if not RES_RE.search(d) or NOT_RE.search(d): continue
        if 'GARAGE' in d and not re.search(r'DWELLING|D\.\s?U|FAMILY|RESIDEN|UNIT|FLAT', d): continue
        try: NC.append((float(r['longitude']), float(r['latitude']), y, units_in(d), addr(r)))
        except ValueError: pass
teardown = np.array([any(abs(y - w) <= 3 for w in wreck.get(a_, [])) for lo, la, y, u, a_ in NC])
pts = shapely.points(np.array([(lo, la) for lo, la, *_ in NC])); pu = np.array([-1 if u is None else u for *_, u, a_ in [(x[0], x[1], x[2], x[3], x[4]) for x in NC]])
# all 2013 buildings (any kind) so a permit snaps to whatever was there, then keep small homes
B = []   # (area, demand, units, gain, small-eligible)
polys = []
for a in meta['areas']:
    num = a['num']; n13 = a.get('n13') or a['n']
    buf = open(f'{ROOT}/b/{num}.wasm', 'rb').read()
    N, V = struct.unpack_from('<II', buf, 0); lon0, lat0 = struct.unpack_from('<dd', buf, 8)
    q = np.frombuffer(buf, '<i2', 2 * V, 24).reshape(-1, 2).astype(float) * 0.5
    o = 24 + 4 * V
    nv = np.frombuffer(buf, np.uint8, N, o); fl = np.frombuffer(buf, np.uint8, N, o + 2 * N)
    po = o + 3 * N + ((3 * N) % 2)
    un = np.frombuffer(buf, '<u2', N, po); fp = np.frombuffer(buf, '<u2', N, po + 2 * N).astype(float) * 2
    starts = np.concatenate([[0], np.cumsum(nv.astype(np.int64))]).astype(np.int64)
    kx = DECK * math.cos(math.radians(lat0))
    for i in range(n13):
        p_ = q[starts[i]:starts[i + 1]]
        if len(p_) < 3: continue
        poly = shapely.Polygon(np.column_stack([lon0 + p_[:, 0] / kx, lat0 + p_[:, 1] / DECK]))
        polys.append(poly); B.append([num, a['demand'], int(un[i]), int(fl[i]), fp[i]])
polys = np.array(polys, dtype=object); B = np.array(B, dtype=float)
cen = shapely.centroid(polys)
zi, zp = ztree.query(cen, predicate='within'); zone = [None] * len(polys)
for b, z in zip(zi, zp): zone[b] = zz[z]
gain = np.full(len(polys), -99.0)
for i in range(len(polys)):
    lim = mla(zone[i])
    if lim is None: continue
    lot = min(40000, max(2000, B[i, 4] * 2)); allowed = 0 if lim == 0 else max(1, int(lot // lim))
    gain[i] = allowed - B[i, 2]
small = (B[:, 2] >= 1) & (B[:, 2] <= 4) & ((B[:, 3].astype(int) & 8) == 0) & (gain > -99)
tree = STRtree(polys); YRS = 13.0
for dist_m in (5,):
    pi, bi = tree.query_nearest(pts, max_distance=dist_m / DECK, return_distance=False, all_matches=False)
    first = {}
    for p_, b in zip(pi, bi):
        if p_ not in first: first[p_] = b
    recall = np.mean([p_ in first for p_ in np.where(teardown)[0]])
    reb = np.zeros(len(polys), bool); net = np.zeros(len(polys), bool)
    for p_, b in first.items():
        reb[b] = True
        if pu[p_] > B[b, 2]: net[b] = True
    m = small & (gain >= 1)
    def r15(k, n): return 1 - (1 - k / n) ** (15 / YRS)
    dsum = B[m, 1].sum()
    print(f"match within {dist_m} m: teardown recall {100*recall:.0f}%;  lots allowing more: {int(m.sum()):,};  net-gain rebuild {100*r15(net[m].sum(), m.sum()):.2f}%/15y, any {100*r15(reb[m].sum(), m.sum()):.2f}%/15y;"
          f"  per unit of demand (net) {100*net[m].sum()/YRS*15/dsum/recall:.2f}%, (any) {100*reb[m].sum()/YRS*15/dsum/recall:.2f}%  [recall-corrected]")
    if dist_m == 5:
        for lo, hi in [(0, 0.5), (0.5, 0.8), (0.8, 1.2), (1.2, 1.8), (1.8, 2.6)]:
            mm = m & (B[:, 1] >= lo) & (B[:, 1] < hi)
            if mm.sum(): print(f"     demand {lo}-{hi} (avg {B[mm,1].mean():.2f}): {int(mm.sum()):6,} lots, net-gain {100*r15(net[mm].sum(), mm.sum())/recall:.2f}%/15y, any rebuild {100*r15(reb[mm].sum(), mm.sum())/recall:.2f}%/15y (corrected); REBUILD_OBS uses the any-rebuild rate")
        # by period
        yrs = np.array([x[2] for x in NC])
        for y0, y1 in [(2013, 2019), (2020, 2025)]:
            rb = np.zeros(len(polys), bool)
            for p_, b in first.items():
                if y0 <= yrs[p_] <= y1: rb[b] = True
            n_ = m.sum(); k_ = rb[m].sum(); span = y1 - y0 + 1
            print(f"     {y0}-{y1}: any rebuild {100*(1-(1-k_/n_)**(15/span))/recall:.2f}%/15y on lots allowing more (corrected)")
        print("   within-demand comparison: lots where today's map allows more vs lots where it doesn't")
        mo = small & (gain >= 1); mn = small & (gain <= 0) & (gain > -99)
        for lo, hi in [(0, 0.5), (0.5, 0.8), (0.8, 1.2), (1.2, 1.8), (1.8, 2.6)]:
            a_ = mo & (B[:, 1] >= lo) & (B[:, 1] < hi); b_ = mn & (B[:, 1] >= lo) & (B[:, 1] < hi)
            ra = r15(reb[a_].sum(), max(1, a_.sum())) / recall; rb_ = r15(reb[b_].sum(), max(1, b_.sum())) / recall
            print(f"     demand {lo}-{hi}: allows more {int(a_.sum()):6,} lots {100*ra:.2f}%  |  doesn't {int(b_.sum()):6,} lots {100*rb_:.2f}%  ratio {ra/max(rb_,1e-9):.2f}")
        # any lot type: share of all small homes rebuilt (context)
        print(f"     all small pre-2000 homes: any rebuild {100*r15(reb[small].sum(), small.sum())/recall:.2f}%/15y corrected")
