#!/usr/bin/env python3
"""Trip model for Expand Chicago Transit: who would take transit, and who switches when a new line makes trips faster.

Data (tools/raw/transit, from fetch.py):
  od_zones.csv.gz        LODES 2022 home-to-work flows (all jobs), summed to the 800 m zones network.py uses
  acs_tracts_2023.csv    ACS 2019-2023 5-year: how workers get to work (B08301), households without a car (B08201), by tract
  blocks.csv.gz          2020 Census blocks (to place each zone in a tract)

Model (the page runs the same formulas in JS):
  1. Where people commute: destination choice, P(work zone d | home zone o) ∝ jobs_d · exp(−γ · car minutes o→d),
     γ fit to the LODES flows by maximum likelihood (a gravity model; the page can't ship millions of real flows).
  2. Transit or car: binary logit fit to ACS transit shares by tract, using the real LODES flows:
       U = a0 + a_t · (transit minutes − car minutes) + a_car · share of households with no car (home tract)
           + a_j · ln(jobs per sq mi at work: where parking is scarce and costly) + a_d · ln(people per sq mi at home)
     Transit minutes come from the midday network (walk, wait half the headway, ride, transfers), door to door.
     Car minutes: 5 minutes to park and walk + 1.3 × straight-line km at 30–45 km/h (assumption).
  3. Scale: commuters make 2 trips a day; all weekday transit trips (L entries + bus riders + Metra boardings, the tool's
     1.12M) ÷ the model's commute trips by transit = a factor for the trips that aren't commutes (assumption: other trips
     respond to a new line like commutes do).
  A new line's new riders = trips whose transit time falls × the change in transit's share. Nobody switches unless a
  trip gets faster.

Writes transit/data/trip.json (parameters, fit statistics, and per-zone workers, no-car share, density, gravity sums).
"""
import collections, csv, gzip, json, math, os, sys
import numpy as np
from scipy.optimize import minimize, minimize_scalar
from scipy.sparse.csgraph import dijkstra

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import network as NWK

RAW, OUT = NWK.RAW, NWK.OUT
ZONE_M = NWK.ZONE_M
CBD = (0, 0, 2400)       # downtown work zone: within 2.4 km (1.5 mi) of State & Madison (parking costs; assumption)
TMAX = 150.0             # transit minutes treated as "no usable trip"
WORK_SHARE = {'cook': 0.15, 'collar': 0.024}   # transit share by county of work (see the fit)
PER_MIN = -0.028         # utility per minute of transit time minus car time (NCHRP Report 716, typical home-based work value)


def car_min(d):          # d in meters, straight line
    km = 1.3 * d / 1000
    v = 30 + 15 * np.minimum(1, km / 30)    # km/h: city streets to expressways (assumption)
    return 5 + 60 * km / v


def zones_with_keys():
    cells, tract_pop = collections.OrderedDict(), collections.defaultdict(collections.Counter)
    for r in csv.DictReader(gzip.open(os.path.join(RAW, 'blocks.csv.gz'), 'rt')):
        p, j = int(r['people']), int(r['jobs'])
        if p + j == 0:
            continue
        x, y = NWK.xy(float(r['lat']), float(r['lon']))
        k = (int(x // ZONE_M), int(y // ZONE_M))
        c = cells.setdefault(k, [0.0, 0.0, 0, 0, 0])
        w = p + j
        c[0] += x * w; c[1] += y * w; c[2] += p; c[3] += j; c[4] += int(r['land_m2'])
        tract_pop[k][r['geoid'][:11]] += p + 0.01 * j
    keys = list(cells)
    Z = [(c[0] / (c[2] + c[3]), c[1] / (c[2] + c[3]), c[2], c[3]) for c in cells.values()]
    land = np.array([max(cells[k][4], 20000) for k in keys], dtype=float)
    tract = [tract_pop[k].most_common(1)[0][0] for k in keys]
    return keys, Z, land, tract


def main():
    keys, Z, land, tract = zones_with_keys()
    kidx = {k: i for i, k in enumerate(keys)}
    nz = len(Z)
    zx = np.array([z[0] for z in Z]); zy = np.array([z[1] for z in Z])
    pop = np.array([z[2] for z in Z], dtype=float); jobs = np.array([z[3] for z in Z], dtype=float)
    # check: same zones, same order as network.py (the page indexes zones by position)
    Zn = NWK.zones()
    assert len(Zn) == nz and all(abs(a[0] - b[0]) < 1e-6 and a[2] == b[2] for a, b in zip(Zn, Z)), 'zone order differs from network.py'

    # flows
    H, W_, N = [], [], []
    miss = 0
    for r in csv.DictReader(gzip.open(os.path.join(RAW, 'od_zones.csv.gz'), 'rt')):
        h, w = kidx.get((int(r['hx']), int(r['hy']))), kidx.get((int(r['wx']), int(r['wy'])))
        if h is None or w is None:
            miss += int(r['n']); continue
        H.append(h); W_.append(w); N.append(int(r['n']))
    H, W_, N = np.array(H), np.array(W_), np.array(N, dtype=float)
    print('flows', len(N), 'workers', int(N.sum()), 'unplaced', miss, file=sys.stderr)
    workers = np.bincount(H, weights=N, minlength=nz)

    # tract attributes
    acs = {r['tract']: r for r in csv.DictReader(open(os.path.join(RAW, 'acs_tracts_2023.csv')))}
    def tv(t, k):
        r = acs.get(t); return float(r[k]) if r else 0.0
    nocar = np.array([tv(t, 'no_car') / max(1.0, tv(t, 'households')) for t in tract])
    dens = pop / (land / 2.59e6)                                 # people per sq mi (land of the zone's blocks)
    lnd = np.log(dens + 100)
    cbd = (np.hypot(zx - CBD[0], zy - CBD[1]) <= CBD[2]).astype(float)   # only for the fit report
    lnj = np.log(jobs / (land / 2.59e6) + 100)                           # jobs per sq mi at the work zone

    # transit minutes for every flow, from the midday network (cached between runs: delete the cache if the network changes)
    cache = os.path.join(RAW, 'trip_times_cache.npz')
    if os.path.exists(cache):
        T = np.load(cache)['T']
    else:
        T = transit_times(Z, H, W_, N, nz)
        np.savez_compressed(cache, T=T)
    dist = np.hypot(zx[H] - zx[W_], zy[H] - zy[W_])
    C = car_min(dist)
    main2(Z, nz, zx, zy, pop, jobs, H, W_, N, T, C, workers, nocar, lnd, cbd, tract, acs, lnj)


def transit_times(Z, H, W_, N, nz):
    stops, pats = NWK.load_network()
    G, zo, zi, eo = NWK.build_graph(stops, pats, Z)
    T = np.full(len(N), TMAX)
    order = np.argsort(H, kind='stable'); Hs = H[order]
    origins = np.unique(H)
    B = 150
    for i in range(0, len(origins), B):
        ob = origins[i:i + B]
        D = dijkstra(G, indices=[zo + o for o in ob], limit=TMAX)[:, zi:zi + nz]
        for r, o in enumerate(ob):
            a, b = np.searchsorted(Hs, o), np.searchsorted(Hs, o, side='right')
            idx = order[a:b]
            T[idx] = np.minimum(D[r, W_[idx]], TMAX)
        print(f'  transit times {min(i + B, len(origins))}/{len(origins)}', file=sys.stderr, end='\r')
    print(file=sys.stderr)
    return T


def main2(Z, nz, zx, zy, pop, jobs, H, W_, N, T, C, workers, nocar, lnd, cbd, tract, acs, lnj):

    # 1. destination choice (gravity) on car minutes
    cz = None
    def S_of(g):   # Σ_d jobs_d exp(−g c_od) for every origin (in chunks)
        S = np.zeros(nz)
        for a in range(0, nz, 400):
            dd = np.hypot(zx[a:a + 400, None] - zx[None, :], zy[a:a + 400, None] - zy[None, :])
            S[a:a + 400] = (jobs[None, :] * np.exp(-g * car_min(dd))).sum(1)
        return S
    def nll(g):
        S = S_of(g)
        return -(N * (np.log(jobs[W_] + 1e-9) - g * C - np.log(S[H]))).sum() / N.sum()
    gcache = os.path.join(RAW, 'trip_gamma_cache.json')
    if os.path.exists(gcache):
        gamma = json.load(open(gcache))['gamma']
    else:
        res = minimize_scalar(nll, bounds=(0.01, 0.3), method='bounded', options={'xatol': 1e-4})
        gamma = float(res.x); json.dump({'gamma': gamma}, open(gcache, 'w'))
    S = S_of(gamma)
    mean_obs = (N * C).sum() / N.sum()
    print('gamma', round(gamma, 4), 'mean car minutes, observed', round(mean_obs, 1), file=sys.stderr)

    # 2. mode choice fit to ACS tract transit shares (commuters who leave home)
    tr_idx = {t: i for i, t in enumerate(sorted(set(tract)))}
    zt = np.array([tr_idx[t] for t in tract]); nt = len(tr_idx)
    obs_tr, obs_all = np.zeros(nt), np.zeros(nt)
    for t, i in tr_idx.items():
        r = acs.get(t)
        if r:
            com = float(r['workers']) - float(r['home'])
            obs_tr[i] = float(r['transit']); obs_all[i] = max(com, 0)
    have = obs_all > 0
    # the time coefficient is set from the literature, not fit: tract shares can't tell time apart from downtown jobs
    # (a free fit put almost all of it on the downtown term). NCHRP Report 716, home-based work mode choice: in-vehicle
    # time coefficients −0.019 to −0.044 per minute, typical −0.028 (here applied to door-to-door minutes; assumption)
    X = np.column_stack([np.ones(len(N)), nocar[H], lnj[W_], lnd[H]]); TD = PER_MIN * (T - C)
    ft = zt[H]
    def model_share(a):
        P = 1 / (1 + np.exp(-(X @ a + TD)))
        num = np.bincount(ft, weights=N * P, minlength=nt); den = np.bincount(ft, weights=N, minlength=nt)
        return num, den, P
    # home tracts alone can't tell where riders work (the fit drifts to "only dense job centers"), so it also matches the
    # transit share by county of work: CTPP via MPC (2016): over 30% of people working in Chicago, 5% in suburban Cook,
    # under 3% in the collar counties; scaled to today by the region's share now vs then (ACS 9.6% vs about 12%; assumption):
    # Cook ≈ 15%, collar ≈ 2.4%
    cw = np.array([t[2:5] for t in tract])[W_]; inCook = cw == '031'; Ncook, Ncol = N[inCook].sum(), N[~inCook].sum()
    def loss(a):
        num, den, P = model_share(a)
        p = np.clip(num / np.maximum(den, 1), 1e-6, 1 - 1e-6)
        home = -(obs_tr * np.log(p) + (obs_all - obs_tr) * np.log(1 - p))[have].sum() / obs_all[have].sum()
        sc, sl = (N * P)[inCook].sum() / Ncook, (N * P)[~inCook].sum() / Ncol
        return home + 0.02 * (np.log(sc / WORK_SHARE['cook']) ** 2 + np.log(max(sl, 1e-5) / WORK_SHARE['collar']) ** 2)
    fit = None
    for a0 in ([-5.0, 1.5, 0.5, 0.0], [-20.0, 3.0, 1.9, -0.4], [-30.0, 2.0, 2.5, -0.2]):
        f = minimize(loss, np.array(a0), method='L-BFGS-B', bounds=[(-40, 4), (0, 8), (0, 4), (-1.5, 1.5)])
        if fit is None or f.fun < fit.fun: fit = f
    a = fit.x
    num, den, P = model_share(a)
    ps = num / np.maximum(den, 1); os_ = obs_tr / np.maximum(obs_all, 1)
    w = obs_all * have
    r2 = 1 - (w * (ps - os_) ** 2).sum() / (w * (os_ - (w * os_).sum() / w.sum()) ** 2).sum()
    city = np.array([t[2:5] == '031' for t in sorted(tr_idx)])
    a = np.array([a[0], PER_MIN, a[1], a[2], a[3]])
    print('mode choice', dict(zip(['const', 'per_min', 'no_car', 'ln_jobs_density', 'ln_density'], np.round(a, 4))), 'tract R2', round(r2, 3), file=sys.stderr)
    print('transit share observed', round(obs_tr[have].sum() / obs_all[have].sum(), 4), 'model', round((N * P).sum() / N.sum(), 4), file=sys.stderr)
    dt = cbd[W_] > 0
    by_work = {'downtown': (N * P)[dt].sum() / N[dt].sum(), 'cook': (N * P)[cw == '031'].sum() / N[cw == '031'].sum(), 'collar': (N * P)[cw != '031'].sum() / N[cw != '031'].sum()}
    print('transit share by workplace', {k: round(float(v), 3) for k, v in by_work.items()}, file=sys.stderr)

    # gravity + logit (what the page computes) vs ACS, to check the page's version too
    # (for every home zone: Σ_d workers · P(d|o) · P(transit), with transit minutes from the same Dijkstra)
    # 3. scale: weekday transit trips per model commute-by-transit
    acs_home = sum(float(r['home']) for r in acs.values()); acs_work = sum(float(r['workers']) for r in acs.values())
    wfh = acs_home / acs_work
    commute_transit_trips = 2 * (N * P).sum() * (1 - wfh)
    TRIPS_TODAY = 1.12e6
    F = TRIPS_TODAY / commute_transit_trips
    print('WFH share', round(wfh, 3), 'model commute transit trips', int(commute_transit_trips), 'scale', round(F, 3), file=sys.stderr)

    out = {'note': 'Trip model fit by tools/transit/tripmodel.py; see its docstring.',
           'gamma': round(gamma, 5), 'mode': {k: round(float(v), 5) for k, v in zip(['const', 'per_min', 'no_car', 'ln_jobs_density', 'ln_density'], a)},
           'cbd': CBD, 'tmax': TMAX, 'wfh': round(wfh, 4), 'scale': round(F, 4), 'tripsToday': TRIPS_TODAY,
           'fit': {'tract_r2': round(float(r2), 3), 'tracts': int(have.sum()), 'flows': int(len(N)), 'workers': int(N.sum()),
                   'share_obs': round(float(obs_tr[have].sum() / obs_all[have].sum()), 4), 'share_model': round(float((N * P).sum() / N.sum()), 4),
                   'mean_car_min': round(float(mean_obs), 1), 'by_work': {k: round(float(v), 3) for k, v in by_work.items()},
                   'city_share_obs': round(float(obs_tr[have & city].sum() / obs_all[have & city].sum()), 4),
                   'city_share_model': round(float(num[have & city].sum() / den[have & city].sum()), 4)},
           'zones': {'workers': [int(round(v)) for v in workers], 'nocar': [round(float(v), 3) for v in nocar],
                     'lnd': [round(float(v), 3) for v in lnd], 'lnj': [round(float(v), 3) for v in lnj], 'S': [float('%.5g' % v) for v in S]}}
    json.dump(out, open(os.path.join(OUT, 'trip.json'), 'w'), separators=(',', ':'))
    print('trip.json', os.path.getsize(os.path.join(OUT, 'trip.json')), file=sys.stderr)


if __name__ == '__main__':
    main()
