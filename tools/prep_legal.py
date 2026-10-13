#!/usr/bin/env python3
"""How many homes today's zoning already allows on each lot, so the game credits a plan only for homes above that.

For every building in b/<area>.wasm and every empty parcel in b/land.wasm, it finds the zoning district under the
building's centroid (or the parcel point) in tools/raw/zoning.geojson.gz (Chicago Data Portal dj47-wfun, fetched by
.github/workflows/fetch-permits.yml) and estimates the homes allowed on the lot:

  residential, business and commercial districts: lot / minimum lot area per home (tools/prep_zoning.py), at least 1
      (a house is allowed on any existing lot of record); C3 allows no homes
  downtown DX-n, DC-n and DR-n: floor area ratio n x lot / 900 sq ft per home (the same convention as the game's
      Tower level)
  everything else (planned developments, DS, manufacturing, parks, transportation): 0, so nothing is subtracted

The lot is estimated the way the game does it: 2x the building footprint, kept between 2,000 and 40,000 sq ft;
an empty parcel is one standard 3,125 sq ft lot.

Output b/legal.wasm (little-endian): uint32 nAreas, then per area in meta.json order:
  uint32 num, uint32 count (= buildings N + empty parcels k), uint8 legal[count] (homes allowed, capped at 254),
  padded to 4 bytes.
Run after tools/prep_extra.py (it reads b/land.wasm):  python3 tools/prep_legal.py
"""
import gzip, json, math, os, re, struct, sys, collections
import numpy as np, shapely
from shapely.strtree import STRtree

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
ROOT = os.path.dirname(HERE)
from prep_zoning import mla

DECK = 111319.49           # metres per degree on deck.gl's sphere (meta.json "meterScale": "deck")
SQFT_PER_HOME_D = 900      # downtown districts: floor area per home, as for the Tower level
VAC_LOT = 3125
D_RE = re.compile(r"^D[XRC]-(\d+(?:\.\d+)?)$")

def lot_of(fp_sqft):
    return min(40000.0, max(2000.0, fp_sqft * 2))

def legal(zone, lot):
    z = (zone or "").strip().upper()
    m = mla(z)
    if m is None:
        d = D_RE.match(z)
        return int(float(d.group(1)) * lot // SQFT_PER_HOME_D) if d else 0
    if m == 0: return 0
    return max(1, int(lot // m))

def main():
    meta = json.load(open(os.path.join(ROOT, 'meta.json')))
    gj = json.load(gzip.open(os.path.join(ROOT, 'tools', 'raw', 'zoning.geojson.gz'), 'rt'))
    zg, zz = [], []
    for f in gj['features']:
        if not f.get('geometry'): continue
        p = {k.lower(): v for k, v in (f.get('properties') or {}).items()}
        try: g = shapely.geometry.shape(f['geometry'])
        except Exception: continue
        if g.is_empty: continue
        zg.append(g); zz.append(p.get('zone_class'))
    tree = STRtree(zg)
    print(len(zg), 'zoning polygons')

    # empty parcels per area from b/land.wasm
    land = open(os.path.join(ROOT, 'b', 'land.wasm'), 'rb').read()
    parcels = {}
    na = struct.unpack_from('<I', land, 0)[0]; o = 4
    for _ in range(na):
        num, N = struct.unpack_from('<II', land, o); o += 8 + N; o += (4 - o % 4) % 4
        k = struct.unpack_from('<I', land, o)[0]; o += 4
        xy = np.frombuffer(land, '<i2', 3 * k, o).reshape(-1, 3)[:, :2].astype(float) * 0.5 if k else np.zeros((0, 2))
        parcels[num] = xy; o += 6 * k; o += (4 - o % 4) % 4

    out = bytearray(struct.pack('<I', len(meta['areas'])))
    tot = collections.Counter(); byclass = collections.Counter()
    for a in meta['areas']:
        num = a['num']
        buf = open(os.path.join(ROOT, 'b', f'{num}.wasm'), 'rb').read()
        N, V = struct.unpack_from('<II', buf, 0); lon0, lat0 = struct.unpack_from('<dd', buf, 8)
        q = np.frombuffer(buf, '<i2', 2 * V, 24).reshape(-1, 2).astype(float) * 0.5
        o = 24 + 4 * V
        nv = np.frombuffer(buf, np.uint8, N, o)
        po = o + 3 * N + ((3 * N) % 2)
        un = np.frombuffer(buf, '<u2', N, po); fp = np.frombuffer(buf, '<u2', N, po + 2 * N).astype(float) * 2
        kx = DECK * math.cos(math.radians(lat0))
        starts = np.concatenate([[0], np.cumsum(nv.astype(np.int64))]).astype(np.int64)
        pts = []
        for i in range(N):
            p_ = q[starts[i]:starts[i + 1]]
            if len(p_) >= 3:
                c = shapely.centroid(shapely.Polygon(p_))
                x, y = c.x, c.y
            elif len(p_): x, y = p_[:, 0].mean(), p_[:, 1].mean()
            else: x = y = 0.0
            pts.append((lon0 + x / kx, lat0 + y / DECK))
        xy = parcels.get(num, np.zeros((0, 2)))
        for x, y in xy: pts.append((lon0 + x / kx, lat0 + y / DECK))
        P = shapely.points(np.array(pts))
        pi, zi = tree.query(P, predicate='within')
        zone = [None] * len(pts)
        for p_, z in zip(pi, zi):
            if zone[p_] is None: zone[p_] = zz[z]
        L = np.zeros(len(pts), np.uint8)
        for i in range(len(pts)):
            lot = lot_of(fp[i]) if i < N else VAC_LOT
            v = legal(zone[i], lot)
            L[i] = min(254, v)
            if i < N and 1 <= un[i] <= 4:
                tot['small'] += 1
                if v > un[i]: tot['small_allows_more'] += 1
                byclass[re.sub(r'-.*', '', (zone[i] or 'none').upper())] += 1
        out += struct.pack('<II', num, len(pts)) + L.tobytes()
        out += b'\0' * ((4 - len(out) % 4) % 4)
        tot['n'] += N; tot['k'] += len(xy)
    open(os.path.join(ROOT, 'b', 'legal.wasm'), 'wb').write(out)
    print(f"buildings {tot['n']:,}, empty parcels {tot['k']:,}; small homes (1-4 units) {tot['small']:,}, "
          f"of which today's zoning allows more homes on {tot['small_allows_more']:,} ({100*tot['small_allows_more']/max(1,tot['small']):.0f}%)")
    print('small homes by district family:', byclass.most_common(12))
    print('wrote b/legal.wasm', len(out), 'bytes')

if __name__ == '__main__':
    main()
