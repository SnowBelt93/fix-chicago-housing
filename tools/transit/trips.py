#!/usr/bin/env python3
"""Commute trip model: real home-to-work trips (LODES), how riders weigh a transit trip, and transit vs. driving.

What riders feel (generalized minutes, "GC"):
  riding counts 1 per minute; walking (to the stop, between stops, from the stop) and waiting count WALK_W / WAIT_W per
  minute (Wardman et al. 2026, TR-A 207, meta-analysis of 606 studies: the old convention of 2 is too high, 1.75 or 1.5 fits the
  evidence); each boarding adds XFER_PEN minutes (Jara-Diaz et al. 2022: 13-18 minutes for the pure transfer penalty).
  Waits are half the midday headway (the same network as network.py: GTFS patterns, 1/2-mile walks, 400 m transfers).

Driving: straight-line distance x CIRCUITY at TomTom's 2025 Chicago morning-rush average speed (27.9 km/h), plus
TERMINAL minutes to park and walk. Shown on the page next to transit times; the choice model uses road distance instead,
so the data sets how much a longer drive pushes people to transit.

Choice (binary logit, transit vs. everything else) fitted to ACS 2019-23 commute shares by home tract (B08301: transit
riders / workers who don't work at home), with households without a car (B08201) as the other input:
  V = a + b_gc * GC + b_km * road km + b_nocar * share of the home zone's households without a car
(A downtown-job term was tried and came out near zero once transit times were in: dropped.)

Checks: today's network assigned to the trips (each trip enters the L where it first boards a train; the trip home
enters where the morning trip left the trains) vs. 2025 weekday L entries at 143 stations.

Writes:
  transit/data/trips.bin.gz commute trips for the page (format below)
  transit/data/model.json   adds "trip": weights, fitted coefficients, fit and check statistics
  tools/raw/transit/trips_check.json   station-by-station check

trips.bin (little-endian):
  header: uint32 nz (zones, network.json order), uint32 nh (home zones listed), uint32 np (pairs)
  uint16 home[nh], uint32 start[nh + 1]      pairs of home[i] are start[i] .. start[i+1]-1
  uint16 work[np]                            work zone of each pair
  uint16 n[np]                               workers on the pair (LODES 2022, all jobs)
  uint8  gc[np]                              today's transit GC in minutes (255 = no transit trip under 255)
  uint8  nocar[nz]                           share of households without a car in each zone, x 250
  uint8  drove[nz]                           share of commuters not on transit who go by car (ACS B08301), x 250
  uint8  place[nz]                           neighborhood or town of each zone: index into model.json trip.places
Pairs are kept where the home or the job is within KEEP_KM of the Loop and either a transit trip exists today or both
ends are within NEAR_KM (where a new line in the tool could give them one). The file is gzipped (trips.bin.gz).
"""
import collections, csv, gzip, json, math, os, struct, sys
import numpy as np
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import dijkstra
from scipy.optimize import minimize

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import network as NWK

ROOT, RAW, OUT = NWK.ROOT, NWK.RAW, NWK.OUT
WALK_W, WAIT_W, XFER_PEN = 1.75, 1.75, 15.0
GC_MAX = 254.0
CIRCUITY = 1.2           # road km per straight-line km (assumption)
DRIVE_KMH = 27.9         # TomTom Traffic Index 2025, Chicago, morning rush average speed
TERMINAL = 6.0           # minutes to park and walk at both ends (assumption)
KEEP_KM, NEAR_KM = 30.0, 20.0


def zones_keyed():
    """Same zones as network.zones(), with their 800 m cell keys."""
    cells = collections.OrderedDict()
    for r in csv.DictReader(gzip.open(os.path.join(RAW, 'blocks.csv.gz'), 'rt')):
        p, j = int(r['people']), int(r['jobs'])
        if p + j == 0:
            continue
        x, y = NWK.xy(float(r['lat']), float(r['lon']))
        key = (int(x // NWK.ZONE_M), int(y // NWK.ZONE_M))
        c = cells.setdefault(key, [0.0, 0.0, 0, 0])
        w = p + j
        c[0] += x * w; c[1] += y * w; c[2] += p; c[3] += j
    keys, Z = [], []
    for k, (sx, sy, p, j) in cells.items():
        keys.append(k); Z.append((sx / (p + j), sy / (p + j), p, j))
    return keys, Z


def gen_graph(stops, pats, Z):
    """Generalized-cost graph. Nodes: stops | pattern positions | zone-out | zone-in. Also returns, per node, the L
    parent station a boarding there enters (for pattern positions of L patterns), else -1."""
    nS = len(stops)
    pos0, n = [], nS
    for p in pats:
        pos0.append(n); n += len(p['s'])
    zo, zi = n, n + len(Z); n += 2 * len(Z)
    rows, cols, w = [], [], []
    kindL = np.zeros(n, dtype=bool)
    def edge(a, b, c):
        rows.append(a); cols.append(b); w.append(max(c, 0.01))
    for p, b in zip(pats, pos0):
        for k, s in enumerate(p['s']):
            if p['kind'] == 'L':
                kindL[b + k] = True
            if k < len(p['s']) - 1:
                edge(s, b + k, WAIT_W * p['hw'][k] / 2 + XFER_PEN)
                edge(b + k, b + k + 1, max(p['m'][k + 1] - p['m'][k], 0.2))
            if k > 0:
                edge(b + k, s, 0)
    sg = NWK.Grid(stops, 400)
    for a, (x, y) in enumerate(stops):
        for b, d in sg.near(x, y, NWK.XFER_M):
            if b != a:
                edge(a, b, WALK_W * d / NWK.WALK)
    for k, (x, y, _, _) in enumerate(Z):
        for s, d in sg.near(x, y, NWK.ACCESS_M):
            edge(zo + k, s, WALK_W * d / NWK.WALK); edge(s, zi + k, WALK_W * d / NWK.WALK)
    G = csr_matrix((w, (rows, cols)), shape=(n, n))
    return G, zo, zi, nS, kindL


def l_parent_of_stop():
    """GTFS platform stop index (network order) -> L parent station id, for platforms of L stations."""
    out = {}
    i = 0
    for name in ('cta', 'metra'):
        for r in csv.DictReader(gzip.open(os.path.join(RAW, f'{name}_stops.csv.gz'), 'rt')):
            if r['location_type'] not in ('', '0'):
                continue
            if name == 'cta' and r.get('parent'):
                out[i] = r['parent']
            i += 1
    return out


def zone_places(ZX, ZY):
    """Chicago community area (point in polygon, from the housing game's meta.json) or, outside the city, the nearest
    Metra station's name within 8 km ("Suburbs" past that). Returns (names, uint8 index per zone)."""
    meta = json.load(open(os.path.join(ROOT, 'meta.json')))
    lon = NWK.LOOP[1] + ZX / NWK.KX; lat = NWK.LOOP[0] + ZY / NWK.KY
    names, idx = [], {}
    def nid(n):
        if n not in idx:
            idx[n] = len(names); names.append(n)
        return idx[n]
    out = np.full(len(ZX), 255, dtype=np.int32)
    for f in meta['outlines']['features']:
        polys = f['geometry']['coordinates'] if f['geometry']['type'] == 'MultiPolygon' else [f['geometry']['coordinates']]
        for poly in polys:
            ring = np.array(poly[0]); x0, y0 = ring[:, 0].min(), ring[:, 1].min(); x1, y1 = ring[:, 0].max(), ring[:, 1].max()
            cand = np.nonzero((lon >= x0) & (lon <= x1) & (lat >= y0) & (lat <= y1) & (out == 255))[0]
            if not len(cand):
                continue
            px, py = lon[cand], lat[cand]; inside = np.zeros(len(cand), bool)
            xs, ys = ring[:, 0], ring[:, 1]
            for a in range(len(ring) - 1):
                xa, ya, xb, yb = xs[a], ys[a], xs[a + 1], ys[a + 1]
                cross = ((ya > py) != (yb > py)) & (px < (xb - xa) * (py - ya) / np.where(yb == ya, 1e-12, yb - ya) + xa)
                inside ^= cross
            out[cand[inside]] = nid({'Ohare': "O'Hare"}.get(f['properties']['name'], f['properties']['name']))
    ms = [(r['name'], *NWK.xy(float(r['lat']), float(r['lon']))) for r in csv.DictReader(gzip.open(os.path.join(RAW, 'metra_stops.csv.gz'), 'rt'))]
    MX = np.array([m[1] for m in ms]); MY = np.array([m[2] for m in ms])
    sub = nid('Suburbs')
    for k in np.nonzero(out == 255)[0]:
        d = np.hypot(MX - ZX[k], MY - ZY[k]); j = int(d.argmin())
        out[k] = nid(ms[j][0]) if d[j] <= 8000 else sub
    assert len(names) < 255, len(names)
    return names, out


def drive_min(dkm):
    return TERMINAL + CIRCUITY * dkm / DRIVE_KMH * 60


def main():
    stops, pats = NWK.load_network()
    keys, Z = zones_keyed()
    net = json.load(open(os.path.join(OUT, 'network.json')))
    assert len(Z) == len(net['zones']['x']) and all(round(z[0]) == x for z, x in zip(Z[:500], net['zones']['x'][:500])), 'zone order differs from network.json'
    zidx = {k: i for i, k in enumerate(keys)}
    nz = len(Z)
    ZX = np.array([z[0] for z in Z]); ZY = np.array([z[1] for z in Z])

    # trips
    od = collections.defaultdict(list)
    lost = 0
    for r in csv.DictReader(gzip.open(os.path.join(RAW, 'od_zones.csv.gz'), 'rt')):
        h, wz = zidx.get((int(r['hx']), int(r['hy']))), zidx.get((int(r['wx']), int(r['wy'])))
        if h is None or wz is None:
            lost += int(r['n']); continue
        od[h].append((wz, int(r['n'])))
    homes = sorted(od)
    print('home zones', len(homes), 'pairs', sum(len(v) for v in od.values()), 'workers lost to zone match', lost, file=sys.stderr)

    G, zo, zi, nS, kindL = gen_graph(stops, pats, Z)
    parent = l_parent_of_stop()
    print('graph nodes', G.shape[0], file=sys.stderr)

    # all-pairs generalized cost from each home zone, plus where each trip first enters and last leaves the L
    H, W, N, GC, FIRST, LAST = [], [], [], [], [], []
    B = 100
    for i in range(0, len(homes), B):
        batch = homes[i:i + B]
        D, P = dijkstra(G, indices=[zo + h for h in batch], limit=GC_MAX, return_predecessors=True)
        rr, ws, ns, hh = [], [], [], []
        for r, h in enumerate(batch):
            rr += [r] * len(od[h]); hh += [h] * len(od[h])
            ws += [w for w, _ in od[h]]; ns += [n for _, n in od[h]]
        rr, ws, ns, hh = np.array(rr), np.array(ws), np.array(ns), np.array(hh)
        gc = D[rr, zi + ws]
        H.append(hh); W.append(ws); N.append(ns); GC.append(gc)
        # walk back from each destination: boarding edges are stop -> pattern position, alighting the reverse
        cur = zi + ws.copy(); first = np.full(len(ws), -1); last = np.full(len(ws), -1)
        alive = np.isfinite(gc)
        for _ in range(600):
            if not alive.any():
                break
            prev = np.where(alive, P[rr, cur], -9999)
            ok = alive & (prev >= 0)
            # alighting: cur a stop, prev an L pattern position -> leaves the L at cur (the first seen walking back = the last leg)
            alL = ok & (cur < nS) & (prev >= nS) & (prev < zo) & kindL[np.clip(prev, 0, len(kindL) - 1)]
            last = np.where(alL & (last < 0), cur, last)
            # boarding: prev a stop, cur an L pattern position -> enters at prev (keep overwriting: the earliest wins)
            bdL = ok & (prev < nS) & (cur >= nS) & (cur < zo) & kindL[np.clip(cur, 0, len(kindL) - 1)]
            first = np.where(bdL, prev, first)
            alive = ok & (prev != zo + hh)
            cur = np.where(alive, prev, cur)
        FIRST.append(first); LAST.append(last)
        print(f'  homes {i + len(batch)}/{len(homes)}', file=sys.stderr, end='\r')
    print(file=sys.stderr)
    H = np.concatenate(H); W = np.concatenate(W); N = np.concatenate(N).astype(float); GC = np.concatenate(GC)
    FIRST = np.concatenate(FIRST); LAST = np.concatenate(LAST)
    dkm = np.hypot(ZX[H] - ZX[W], ZY[H] - ZY[W]) / 1000
    gcc = np.minimum(np.where(np.isfinite(GC), GC, GC_MAX + 1), GC_MAX + 1)
    print('pairs', len(H), 'workers', int(N.sum()), 'with a transit trip under', GC_MAX, ':', round(N[np.isfinite(GC)].sum() / N.sum(), 3), file=sys.stderr)

    # home tract shares of each zone's residents (blocks -> zones)
    tz = collections.defaultdict(lambda: collections.Counter())
    for r in csv.DictReader(gzip.open(os.path.join(RAW, 'blocks.csv.gz'), 'rt')):
        p = int(r['people'])
        if not p:
            continue
        x, y = NWK.xy(float(r['lat']), float(r['lon']))
        k = zidx.get((int(x // NWK.ZONE_M), int(y // NWK.ZONE_M)))
        if k is not None:
            tz[k][r['geoid'][:11]] += p
    acs = {r['tract']: r for r in csv.DictReader(open(os.path.join(RAW, 'acs_tracts_2023.csv')))}
    nocar_z, drove_z = np.zeros(nz), np.zeros(nz)
    for k, c in tz.items():
        tot = sum(c.values()); s = d = dw = 0.0
        for t, p in c.items():
            a = acs.get(t)
            if a and int(a['households']) > 0:
                s += p / tot * int(a['no_car']) / int(a['households'])
            other = int(a['workers']) - int(a['home']) - int(a['transit']) if a else 0
            if other > 0:
                d += p * int(a['car']) / other; dw += p
        nocar_z[k] = s; drove_z[k] = d / dw if dw else 0.85
    places, place_z = zone_places(ZX, ZY)
    tracts = sorted({t for c in tz.values() for t in c if t in acs})
    tix = {t: i for i, t in enumerate(tracts)}
    # zone -> tract weights (residents)
    zt_rows, zt_cols, zt_w = [], [], []
    for k, c in tz.items():
        tot = sum(c.values())
        for t, p in c.items():
            if t in tix:
                zt_rows.append(tix[t]); zt_cols.append(k); zt_w.append(p / tot)
    ZT = csr_matrix((zt_w, (zt_rows, zt_cols)), shape=(len(tracts), nz))
    obs_t = np.array([int(acs[t]['transit']) for t in tracts], float)
    com_t = np.array([int(acs[t]['workers']) - int(acs[t]['home']) for t in tracts], float)
    use = com_t >= 100
    nocar = nocar_z[H]
    X = np.column_stack([np.ones(len(H)), gcc, CIRCUITY * dkm, nocar])
    Hz = H

    def predict(beta):
        v = X @ beta
        p = 1 / (1 + np.exp(-v))
        p = np.where(gcc > GC_MAX, 0.0, p)
        rid = np.bincount(Hz, weights=N * p, minlength=nz)
        wk = np.bincount(Hz, weights=N, minlength=nz)
        return p, ZT @ rid, ZT @ wk

    def nll(beta):
        _, r, w = predict(beta)
        s = np.clip(r / np.maximum(w, 1), 1e-6, 1 - 1e-6)
        sh = np.clip(obs_t / np.maximum(com_t, 1), 0, 1)
        return -(com_t[use] * (sh[use] * np.log(s[use]) + (1 - sh[use]) * np.log(1 - s[use]))).sum() / com_t[use].sum()

    b0 = np.array([0.0, -0.04, 0.02, 3.0])
    fit = minimize(nll, b0, method='Nelder-Mead', options={'maxiter': 6000, 'xatol': 1e-6, 'fatol': 1e-9})
    fit = minimize(nll, fit.x, method='BFGS')
    beta = fit.x
    p, r, w = predict(beta)
    s_pred = r / np.maximum(w, 1); s_obs = obs_t / np.maximum(com_t, 1)
    wts = com_t * use
    r2 = 1 - (wts * (s_obs - s_pred) ** 2).sum() / (wts * (s_obs - np.average(s_obs, weights=wts)) ** 2).sum()
    tot_pred = (N * p).sum() / N.sum()
    tot_obs = obs_t[use].sum() / com_t[use].sum()
    print('logit', dict(zip(['const', 'gc', 'road_km', 'no_car'], np.round(beta, 4))), 'R2 tracts', round(r2, 3),
          'transit share pred', round(tot_pred, 4), 'ACS', round(tot_obs, 4), file=sys.stderr)

    # check: L station entries from commutes vs. 2025 weekday entries
    rides = collections.defaultdict(list)
    for row in csv.DictReader(open(os.path.join(ROOT, 'tools', 'raw', 'cta_l_daily_2025.csv'))):
        if row['daytype'] == 'W':
            rides[row['station_id']].append(float(row['rides']))
    actual = {k: float(np.mean(v)) for k, v in rides.items()}
    ent = collections.Counter()
    riders = N * p
    for st, rr in ((FIRST, riders), (LAST, riders)):
        m = st >= 0
        for s_, v in zip(st[m], rr[m]):
            ps = parent.get(int(s_))
            if ps:
                ent[ps] += v
    common = [k for k in actual if ent.get(k, 0) > 0]
    a = np.array([actual[k] for k in common]); e = np.array([ent[k] for k in common])
    scale = a.sum() / e.sum()
    la, le = np.log(a), np.log(e * scale)
    r2s = 1 - ((la - le) ** 2).sum() / ((la - la.mean()) ** 2).sum()
    corr = float(np.corrcoef(la, np.log(e))[0, 1])
    med = float(np.median(np.abs(la - le)))
    print('stations', len(common), 'of', len(actual), 'commute entries', int(e.sum()), 'actual', int(a.sum()),
          'scale (all trips / commute trips)', round(scale, 3), 'log R2', round(r2s, 3), 'corr', round(corr, 3), 'median |log err|', round(med, 3), file=sys.stderr)
    json.dump({'stations': {k: [round(actual[k]), round(ent[k] * scale)] for k in common}}, open(os.path.join(RAW, 'trips_check.json'), 'w'))

    # browser file: pairs touching the area near the Loop
    rH, rW = np.hypot(ZX[H], ZY[H]), np.hypot(ZX[W], ZY[W])
    near = ((rH <= KEEP_KM * 1000) | (rW <= KEEP_KM * 1000)) & (np.isfinite(GC) | ((rH <= NEAR_KM * 1000) & (rW <= NEAR_KM * 1000)))
    kept = np.nonzero(near)[0]
    order = kept[np.lexsort((W[kept], H[kept]))]
    hs, starts = np.unique(H[order], return_index=True)
    starts = np.append(starts, len(order)).astype(np.uint32)
    gcb = np.minimum(np.where(np.isfinite(GC[order]), np.round(GC[order]), 255), 255).astype(np.uint8)
    nn = np.minimum(N[order], 65535).astype(np.uint16)
    body = (struct.pack('<III', nz, len(hs), len(order)) + hs.astype('<u2').tobytes() + starts.astype('<u4').tobytes()
            + W[order].astype('<u2').tobytes() + nn.astype('<u2').tobytes() + gcb.tobytes()
            + np.round(np.clip(nocar_z, 0, 1) * 250).astype(np.uint8).tobytes()
            + np.round(np.clip(drove_z, 0, 1) * 250).astype(np.uint8).tobytes() + place_z.astype(np.uint8).tobytes())
    with open(os.path.join(OUT, 'trips.bin.gz'), 'wb') as f:
        f.write(gzip.compress(body, compresslevel=9, mtime=0))
    print('trips.bin.gz', os.path.getsize(os.path.join(OUT, 'trips.bin.gz')), 'pairs', len(order), 'workers', int(N[order].sum()), file=sys.stderr)

    # zone share of households without a car, for the page (only zones that appear)
    mpath = os.path.join(OUT, 'model.json')
    M = json.load(open(mpath))
    M['trip'] = {
        'walkW': WALK_W, 'waitW': WAIT_W, 'xferPen': XFER_PEN, 'gcMax': GC_MAX,
        'drive': {'kmh': DRIVE_KMH, 'circuity': CIRCUITY, 'terminal': TERMINAL},
        'coef': dict(zip(['const', 'gc', 'road_km', 'no_car'], [round(float(x), 5) for x in beta])),
        'fit': {'tracts': int(use.sum()), 'r2_tract_share': round(float(r2), 3), 'share_pred': round(float(tot_pred), 4), 'share_acs': round(float(tot_obs), 4)},
        'check': {'stations': len(common), 'scale_all_trips': round(float(scale), 3), 'log_r2': round(float(r2s), 3),
                  'median_abs_log_error': round(med, 3), 'commute_entries': int(e.sum()), 'actual_entries': int(a.sum())},
        'kept': {'pairs': int(len(order)), 'workers': int(N[order].sum())},
        'places': places,
        'data': 'LODES 2022 home-to-work (all jobs), ACS 2019-23 B08301/B08201 by tract, CTA 2025 weekday L entries',
    }
    json.dump(M, open(mpath, 'w'), indent=1)


if __name__ == '__main__':
    main()
