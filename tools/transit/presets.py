#!/usr/bin/env python3
"""Real proposals as presets for the transit tool -> transit/data/presets.json.

Stations are placed where the named streets cross in OpenStreetMap (tools/raw/transit/osm.json.gz, primary/secondary roads),
or at given coordinates where the station sits off the street grid. Official figures and sources come from the agencies;
each preset says what its ridership number counts.
"""
import gzip, json, math, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RAW = os.path.join(ROOT, 'tools', 'raw', 'transit')
OUT = os.path.join(ROOT, 'transit', 'data')
LOOP = (41.8819, -87.6278)
KX, KY = 111320 * math.cos(math.radians(41.85)), 110574
CMAP_RTP = 'https://cmap.illinois.gov/wp-content/uploads/2026-RTP-Regional-Capital-Projects-Benefits-Report-Appendix.pdf'


def xy(lat, lon):
    return ((lon - LOOP[1]) * KX, (lat - LOOP[0]) * KY)


def ll(x, y):
    return [round(LOOP[1] + x / KX, 6), round(LOOP[0] + y / KY, 6)]


osm = json.load(gzip.open(os.path.join(RAW, 'osm.json.gz'), 'rt'))
roads = [(nm, [xy(p[1], p[0]) for p in pts]) for nm, pts in osm.get('arterial', []) + osm.get('motorway', [])]


def core(name):
    n = name.lower()
    m = re.match(r'^(north|south|east|west|n|s|e|w)\.? (.+)$', n)
    if m and len(m.group(2).split()) >= 2:   # "West North Avenue" -> "north avenue", but "North Avenue" stays
        n = m.group(2)
    return n.replace('avenue', 'ave').replace('street', 'st').replace('road', 'rd').replace('boulevard', 'blvd').replace('drive', 'dr').strip()


def segs(name):
    c = core(name)
    out = []
    for nm, pts in roads:
        if core(nm) == c:
            out += list(zip(pts, pts[1:]))
    return out


def inter(a, b, c, d):
    r = (b[0] - a[0], b[1] - a[1]); q = (d[0] - c[0], d[1] - c[1]); den = r[0] * q[1] - r[1] * q[0]
    if abs(den) < 1e-9:
        return None
    t = ((c[0] - a[0]) * q[1] - (c[1] - a[1]) * q[0]) / den; u = ((c[0] - a[0]) * r[1] - (c[1] - a[1]) * r[0]) / den
    return (a[0] + t * r[0], a[1] + t * r[1]) if -0.02 <= t <= 1.02 and -0.02 <= u <= 1.02 else None


def crossing(main, cross, near=None):
    A, B = segs(main), segs(cross)
    hits = [p for s1 in A for s2 in B for p in [inter(*s1, *s2)] if p]
    if not hits:
        return None
    if near:
        nx, ny = xy(*near)
        hits.sort(key=lambda p: math.hypot(p[0] - nx, p[1] - ny))
    # divided roads cross twice: average hits within 60 m of the first
    h0 = hits[0]; grp = [p for p in hits if math.hypot(p[0] - h0[0], p[1] - h0[1]) < 60]
    return ll(sum(p[0] for p in grp) / len(grp), sum(p[1] for p in grp) / len(grp))


def along(main, crosses, near=None, extra=None):
    # main can be a list of names the street goes by (Garfield Boulevard / 55th Street).
    # Cross streets missing from the map's main-road layer are placed between their found neighbors
    # (by street number for numbered streets, else evenly); numbered streets past the last found one are extended
    # from the two nearest found numbered streets. extra = {cross: [lon, lat]} for spots set by hand.
    mains = main if isinstance(main, list) else [main]
    got = []
    for c in crosses:
        if extra and c in extra:
            got.append(extra[c]); continue
        got.append(next((q for m in mains for q in [crossing(m, c, near)] if q), None))
    num = lambda c: int(re.match(r'(\d+)', c).group(1)) if re.match(r'\d+', c) else None
    missing = [c for c, p in zip(crosses, got) if not p]
    for i, p in enumerate(got):
        if p:
            continue
        a = next((k for k in range(i - 1, -1, -1) if got[k]), None); b = next((k for k in range(i + 1, len(got)) if got[k]), None)
        if a is None or b is None:
            known = [k for k in range(len(got)) if got[k] and num(crosses[k]) is not None]
            if num(crosses[i]) is None or len(known) < 2:
                continue
            known.sort(key=lambda k: abs(k - i)); a, b = sorted(known[:2])
        na, nb, ni = num(crosses[a]), num(crosses[b]), num(crosses[i])
        t = (ni - na) / (nb - na) if None not in (na, nb, ni) and nb != na else (i - a) / (b - a)
        got[i] = [round(got[a][0] + t * (got[b][0] - got[a][0]), 6), round(got[a][1] + t * (got[b][1] - got[a][1]), 6)]
    if missing:
        print(f'  {mains[0]}: placed from neighbors:', missing, file=sys.stderr)
    return [p for p in got if p]



# ---- real alignments: routes along railroad rights-of-way (OpenStreetMap, tools/raw/transit/osm_rail.json.gz) and roads ----
import heapq
RAIL_WAYS = None
def rail_ways():
    global RAIL_WAYS
    if RAIL_WAYS is None:
        p = os.path.join(RAW, 'osm_rail.json.gz')
        g = json.load(gzip.open(p, 'rt')) if os.path.exists(p) else {'ways': {}}
        RAIL_WAYS = [(v[0], v[1], v[2], [xy(q[1], q[0]) for q in v[3]]) for v in g['ways'].values()]
    return RAIL_WAYS


RAIL_COST = {'construction': 0.8, 'rail': 1.0, 'subway': 1.0, 'light_rail': 1.0, 'abandoned': 1.0, 'disused': 1.0, 'razed': 1.1}
USE_COST = {'yard': 2.5, 'siding': 2.0, 'spur': 1.3, 'industrial': 1.2, 'crossover': 1.5}


def make_graph(lines, bridge=60, far=None):
    # lines: (points x/y, cost factor). Shared vertices (within 3 m) join; a line's loose end also joins the nearest
    # vertex of another line within `bridge` m (OpenStreetMap leaves gaps where abandoned track was pulled up), at 3x cost.
    ids, X, Y, adj = {}, [], [], []
    def node(p):
        k = (round(p[0] / 3), round(p[1] / 3))
        if k not in ids:
            ids[k] = len(X); X.append(p[0]); Y.append(p[1]); adj.append([])
        return ids[k]
    ends, owner = [], {}
    far = far or set()   # lines whose loose ends may join another line up to 150 m away (abandoned track with pieces missing)
    for li, (pts, f) in enumerate(lines):
        dense = []   # vertices every 25 m or closer, so a loose end can join the middle of a long straight piece
        for a, b in zip(pts, pts[1:]):
            k = max(1, int(math.hypot(b[0] - a[0], b[1] - a[1]) // 25))
            dense += [(a[0] + (b[0] - a[0]) * j / k, a[1] + (b[1] - a[1]) * j / k) for j in range(k)]
        pts = dense + list(pts[-1:])
        prev = None
        for p in pts:
            n = node(p); owner.setdefault(n, li)
            if prev is not None and prev != n:
                d = math.hypot(X[n] - X[prev], Y[n] - Y[prev]) * f; adj[n].append((prev, d)); adj[prev].append((n, d))
            prev = n
        if len(pts) > 1:
            ends += [(node(pts[0]), li), (node(pts[-1]), li)]
    G = {'X': X, 'Y': Y, 'adj': adj, 'cell': 100, 'grid': {}}
    for i, (x, y) in enumerate(zip(X, Y)):
        G['grid'].setdefault((int(x // 100), int(y // 100)), []).append(i)
    for n, li in ends:
        if len(adj[n]) > 1:
            continue
        r = 150 if li in far else bridge
        best, bd = None, r
        for j in g_near_all(G, (X[n], Y[n]), r):
            if owner.get(j) != li:
                d = math.hypot(X[j] - X[n], Y[j] - Y[n])
                if d < bd:
                    best, bd = j, d
        if best is not None:
            adj[n].append((best, bd * 3)); adj[best].append((n, bd * 3))
    return G


def g_near_all(G, p, r):
    c = G['cell']
    for a in range(int((p[0] - r) // c), int((p[0] + r) // c) + 1):
        for b in range(int((p[1] - r) // c), int((p[1] + r) // c) + 1):
            yield from G['grid'].get((a, b), [])


def g_nearest(G, p, r=400):
    best, bd = None, r
    for i in g_near_all(G, p, r):
        d = math.hypot(G['X'][i] - p[0], G['Y'][i] - p[1])
        if d < bd:
            best, bd = i, d
    return best


def g_route(G, a, b):
    # cheapest path between the network points nearest a and b (x/y), or None
    s, t = g_nearest(G, a), g_nearest(G, b)
    if s is None or t is None:
        return None
    X, Y, adj = G['X'], G['Y'], G['adj']
    h = lambda i: 0.8 * math.hypot(X[i] - X[t], Y[i] - Y[t])
    dist, prev, pq = {s: 0}, {}, [(h(s), s)]
    while pq:
        f, u = heapq.heappop(pq)
        if u == t:
            break
        if f - h(u) > dist[u] + 1e-6:
            continue
        for v, w in adj[u]:
            nd = dist[u] + w
            if nd < dist.get(v, 1e18):
                dist[v] = nd; prev[v] = u; heapq.heappush(pq, (nd + h(v), v))
    if t not in dist:
        return None
    path, u = [], t
    while True:
        path.append((X[u], Y[u]))
        if u == s:
            break
        u = prev[u]
    return path[::-1]


RAIL_G = {}
def rail_graph(cta=True):
    # cta=False leaves out CTA tracks, so a new line can't borrow the Red Line's tracks to reach a far station
    if cta not in RAIL_G:
        W = [w for w in rail_ways() if cta or w[0] not in ('subway', 'light_rail')]
        RAIL_G[cta] = make_graph([(pts, RAIL_COST.get(k, 1.2) * USE_COST.get(u, 1.0)) for k, u, nm, pts in W],
                                 far={i for i, w in enumerate(W) if w[0] in ('abandoned', 'disused', 'razed')})
    return RAIL_G[cta]


def route_ll(G, pts):
    # route through a list of [lon, lat] waypoints; a waypoint given as ('straight', [lon, lat]) is reached in a straight line
    out = []
    for i in range(1, len(pts)):
        a, b = pts[i - 1], pts[i]
        if isinstance(a, tuple): a = a[1]
        if isinstance(b, tuple):
            leg = [xy(a[1], a[0]), xy(b[1][1], b[1][0])]
        else:
            leg = g_route(G, xy(a[1], a[0]), xy(b[1], b[0]))
            if leg is None:
                raise SystemExit(f'no route {a} -> {b}')
        out = chain(out, leg)
    return despur(out)


def despur(path, near=60, loop=150):
    # cut out-and-back detours (a route that runs down a siding to turn around): where the path comes back within
    # `near` m of an earlier point after more than `loop` m, drop the part in between
    out, i = [], 0
    while i < len(path):
        out.append(path[i]); run, cut = 0, None
        for j in range(i + 1, len(path)):
            run += math.hypot(path[j][0] - path[j - 1][0], path[j][1] - path[j - 1][1])
            if run > loop and math.hypot(path[j][0] - path[i][0], path[j][1] - path[i][1]) < near:
                cut = j
        i = cut if cut else i + 1
    return out


def rail_lines(test):
    return [pts for kind, use, nm, pts in rail_ways() if test(kind, use, nm)]


def road_lines(name):
    c = core(name)
    return [pts for nm, pts in roads if core(nm) == c]


def thin(pts, tol=4):
    # Ramer-Douglas-Peucker in meters
    if len(pts) < 3:
        return list(pts)
    a, b = pts[0], pts[-1]; dx, dy = b[0] - a[0], b[1] - a[1]; L = math.hypot(dx, dy) or 1e-9
    i, dm = max(((i, abs(dy * (p[0] - a[0]) - dx * (p[1] - a[1])) / L) for i, p in enumerate(pts[1:-1], 1)), key=lambda t: t[1])
    if dm > tol:
        return thin(pts[:i + 1], tol)[:-1] + thin(pts[i:], tol)
    return [a, b]


def shape_ll(path):
    return [ll(*p) for p in thin(path)]


def on_shape(path, p):
    # nearest point on a path to p (x/y)
    best, bd = path[0], 1e18
    for a, b in zip(path, path[1:]):
        dx, dy = b[0] - a[0], b[1] - a[1]; L2 = dx * dx + dy * dy
        t = 0 if not L2 else max(0, min(1, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / L2))
        q = (a[0] + t * dx, a[1] + t * dy); d = math.hypot(q[0] - p[0], q[1] - p[1])
        if d < bd:
            best, bd = q, d
    return best, bd


def chain(*legs):
    # legs: lists of x/y points; joins them, dropping repeated joints
    out = []
    for leg in legs:
        if not leg:
            continue
        if out and math.hypot(out[-1][0] - leg[0][0], out[-1][1] - leg[0][1]) < 1:
            leg = leg[1:]
        out += list(leg)
    return out


def street_on(path, street, near=None):
    # where a route crosses a named street (nearest to `near`, lat/lon), as [lon, lat]
    hits = [q for a, b in zip(path, path[1:]) for c, d in segs(street) for q in [inter(a, b, c, d)] if q]
    if not hits:
        return None
    if near:
        nx, ny = xy(*near); hits.sort(key=lambda q: math.hypot(q[0] - nx, q[1] - ny))
    return ll(*hits[0])


def snap(path, lonlat):
    q, d = on_shape(path, xy(lonlat[1], lonlat[0]))
    return ll(*q)


def path_len(path):
    return sum(math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(path, path[1:]))


def sub_path(path, a, b):
    # the part of a path between the points nearest a and b (x/y)
    def where(p):
        best, bd, bi, bq = 0, 1e18, 0, path[0]
        for i, (u, v) in enumerate(zip(path, path[1:])):
            dx, dy = v[0] - u[0], v[1] - u[1]; L2 = dx * dx + dy * dy
            t = 0 if not L2 else max(0, min(1, ((p[0] - u[0]) * dx + (p[1] - u[1]) * dy) / L2))
            q = (u[0] + t * dx, u[1] + t * dy); d = math.hypot(q[0] - p[0], q[1] - p[1])
            if d < bd:
                bd, bi, bq = d, i, q
        return bi, bq
    (i, qa), (j, qb) = where(a), where(b)
    if (i, path_len([path[i], qa])) > (j, path_len([path[j], qb])):
        (i, qa), (j, qb) = (j, qb), (i, qa)
    return [qa] + list(path[i + 1:j + 1]) + [qb]


def road_route(name_test, a, b):
    G = make_graph([(pts, 1.0) for nm, pts in roads if name_test(nm)], bridge=40)
    r = g_route(G, a, b)
    straight = math.hypot(b[0] - a[0], b[1] - a[1])
    return r if r and path_len(r) < 1.3 * straight + 200 else None   # a detour means the street map has a gap: go straight


def align(P):
    """Each rail proposal follows its real right-of-way: shape = the whole path drawn, buildShape = the part that is new
    structure (when the line reuses existing CTA track), buildMi = its length in miles. Stations sit on the path."""
    byid = {p['id']: p for p in P}
    mi = lambda path: round(path_len(path) / 1609.34, 2)
    # Red Line Extension: the alignment under construction (OpenStreetMap "construction" track), from 95th to the 130th terminal
    G = rail_graph(True)
    r = route_ll(G, [[-87.62434, 41.72238], [-87.5935, 41.6560]])
    st = [[-87.62434, 41.72238], street_on(r, '103rd Street', (41.7068, -87.636)), street_on(r, '111th Street', (41.6922, -87.636)),
          snap(r, byid['rle']['pts'][3]), street_on(r, '130th Street', (41.6595, -87.598))]
    st[4] = st[4] or snap(r, [-87.5975, 41.6585])
    r = sub_path(r, xy(st[0][1], st[0][0]), xy(st[-1][1], st[-1][0]))
    byid['rle'].update(pts=st, shape=shape_ll(r))
    byid['rle']['approx'] = 'Follows the route under construction. Station spots: 103rd, 111th, Michigan near 116th and 130th, as CTA gives them.'
    # Orange Line to Ford City: CTA's 2009 preferred route, south from Midway along the Belt Railway (Kenton Line), across the
    # Clearing Yard, then down the east side of Cicero to 76th
    r = route_ll(G, [[-87.73788, 41.78661], [-87.7371, 41.7709], ('straight', [-87.7402, 41.7650]), ('straight', [-87.7417, 41.7555])])
    byid['orange'].update(pts=[[-87.73788, 41.78661], ll(*r[-1])], shape=shape_ll(r))
    byid['orange']['approx'] = 'Follows CTA’s 2009 preferred route: along the Belt Railway south of Midway, over the Clearing Yard, to a station at 76th and Cicero.'
    byid['orange']['status'] = 'Studied 2009 (elevated along the Belt Railway, one station at Ford City); CTA isn’t studying it now'
    # Yellow Line to Old Orchard: CTA's preferred route, north on the old Union Pacific right-of-way, then along the Edens to a
    # station south of Old Orchard Road
    r1 = route_ll(G, [[-87.75192, 42.03895], ('straight', [-87.7525, 42.0410]), [-87.7579, 42.0561]])
    ed = xy(42.0610, -87.7552)   # on the Edens, about 150 m south of Old Orchard Road
    r2 = road_route(lambda nm: 'I 94' in nm, r1[-1], ed) or [r1[-1], ed]
    r = chain(r1, r2)
    byid['yellow'].update(pts=[[-87.75192, 42.03895], ll(*r[-1])], shape=shape_ll(r))
    byid['yellow']['approx'] = 'Follows CTA’s preferred route: the old Union Pacific right-of-way north of Dempster, then along the Edens to a station south of Old Orchard Road.'
    # Green Line to Jackson Park: over 63rd Street, where the old line ran
    j = byid['greenjp']; r = road_route(lambda nm: core(nm) == core('63rd Street'), xy(j['pts'][0][1], j['pts'][0][0]), xy(j['pts'][-1][1], j['pts'][-1][0]))
    if r:
        j.update(pts=[j['pts'][0]] + [snap(r, q) for q in j['pts'][1:]], shape=shape_ll(r))
    # Mid-City Transitway: the rail corridor a quarter mile east of Cicero from Jefferson Park, the Belt Railway east near 75th,
    # then southeast to the Dan Ryan, meeting the Red Line between 87th and 91st (Tribune 2002)
    G2 = rail_graph(False)
    r = route_ll(G2, [[-87.7613, 41.9708], [-87.7436, 41.9576], [-87.743, 41.93], [-87.741, 41.88], [-87.739, 41.80], [-87.70, 41.757], [-87.66, 41.757], [-87.6280, 41.7320]])
    # last stretch: leave the railroad where it crosses 87th Street and run over 87th to the Red Line's 87th Street station
    # in the Dan Ryan, where riders transfer
    red = xy(41.73537, -87.62472)
    x87 = street_on(r, '87th Street', (41.736, -87.635))
    if x87:
        p87 = xy(x87[1], x87[0])
        r = sub_path(r, r[0], p87)
        r = chain(r, road_route(lambda nm: core(nm) == core('87th Street'), p87, (red[0], p87[1])) or [p87, (red[0], p87[1])], [red])
    mc = byid['midcity']; old = mc['pts']
    st = [[-87.7613, 41.9708]] + [snap(r, q) for q in old] + [ll(*r[-1])]
    gap = lambda a, b: math.hypot(*(u - v for u, v in zip(xy(a[1], a[0]), xy(b[1], b[0]))))
    keep = [st[0]]
    for q in st[1:-1]:   # stations at least 600 m apart; the Red Line transfer always stays
        if gap(q, keep[-1]) > 600:
            keep.append(q)
    if len(keep) > 1 and gap(keep[-1], st[-1]) < 600:
        keep.pop()
    keep.append(st[-1])
    mc.update(pts=keep, shape=shape_ll(r))
    mc['approx'] = 'Route follows the rail corridors the 2002 plan named (old Crosstown corridor, Belt Railway) and ends at the Red Line’s 87th Street station (the 2002 plan said between 87th and 91st); stations are approximate. No current plan exists.'
    # Circle Line, southern half (CTA's 2009 preferred route): the Pink Line's tracks from Ashland/Lake to 18th, then about a mile
    # of new track to the Orange Line at Ashland (drawn over Paulina, Cermak and Ashland; CTA didn't publish the exact path)
    pink = route_ll(G, [[-87.66697, 41.88532], [-87.6691, 41.8579]])
    turn = min(pink, key=lambda q: q[1])   # the Pink Line's tracks turn west a little south of 18th; leave them there
    pink = sub_path(pink, pink[0], turn)
    cer = crossing('Paulina Street', 'Cermak Road', (41.8524, -87.6690))
    cer = xy(cer[1], cer[0]) if cer else (turn[0], xy(41.8524, -87.669)[1])
    ash = crossing('Ashland Avenue', 'Cermak Road', (41.8524, -87.6664)); ash = xy(ash[1], ash[0])
    orng = xy(41.83923, -87.66532)
    tail = road_route(lambda nm: core(nm) == core('Ashland Avenue'), ash, orng) or [ash, (ash[0], orng[1] + 60), orng]
    new = chain([turn, (turn[0], cer[1]), ash], tail)
    r = chain(pink, new)
    def on_lat(lat):
        for a, b in zip(r, r[1:]):
            y = xy(lat, 0)[1]
            if (a[1] - y) * (b[1] - y) <= 0 and a[1] != b[1]:
                t = (y - a[1]) / (b[1] - a[1]); return ll(a[0] + t * (b[0] - a[0]), y)
    st = [[-87.66697, 41.88532], on_lat(41.8753), on_lat(41.8670), on_lat(41.8579), ll(*ash), ll(*orng)]
    c = byid['circle']
    c.update(name='Circle Line (southern half)', pts=st, shape=shape_ll(r), buildShape=shape_ll(new), buildMi=mi(new))
    c['approx'] = 'CTA’s 2009 preferred route: the Pink Line’s tracks from Ashland/Lake to 18th, with new stations at Congress (Blue Line) and Roosevelt, then about a mile of new elevated track to Cermak/Blue Island and the Orange Line at Ashland. CTA didn’t publish the new track’s exact path; it’s drawn over streets. Trains would continue on the Orange Line’s tracks into the Loop.'
    c['status'] = 'Studied 2006–09 (this is the first phase); CTA isn’t studying it now. CMAP: “costly for the level of benefits”'
    for k in ('rle', 'orange', 'yellow', 'greenjp', 'midcity', 'circle'):
        p = byid[k]; print(f"  {k}: {len(p['pts'])} stations, {mi([xy(q[1], q[0]) for q in p['shape']])} mi drawn"
                           + (f", {p['buildMi']} mi new" if 'buildMi' in p else ''), file=sys.stderr)

ASHLAND_X = ['Irving Park Road', 'Addison Street', 'Roscoe Street', 'Belmont Avenue', 'Diversey Parkway', 'Fullerton Avenue', 'Cortland Street',
             'North Avenue', 'Division Street', 'Chicago Avenue', 'Grand Avenue', 'Lake Street', 'Madison Street', 'Jackson Boulevard', 'Harrison Street',
             'Polk Street', 'Roosevelt Road', '18th Street', 'Blue Island Avenue', '31st Street', '35th Street', 'Pershing Road', '43rd Street',
             '47th Street', '51st Street', 'Garfield Boulevard', '59th Street', '63rd Street', '69th Street', '74th Street', '79th Street',
             '83rd Street', '87th Street', '91st Street', '95th Street']
WESTERN_X = ['Howard Street', 'Touhy Avenue', 'Devon Avenue', 'Peterson Avenue', 'Bryn Mawr Avenue', 'Foster Avenue', 'Lawrence Avenue', 'Montrose Avenue',
             'Irving Park Road', 'Addison Street', 'Belmont Avenue', 'Diversey Avenue', 'Fullerton Avenue', 'Armitage Avenue', 'North Avenue', 'Division Street',
             'Chicago Avenue', 'Grand Avenue', 'Lake Street', 'Madison Street', 'Jackson Boulevard', 'Roosevelt Road', 'Cermak Road', '31st Street',
             '35th Street', 'Pershing Road', '47th Street', '55th Street', '63rd Street', '71st Street', '79th Street']
PULASKI_X = ['Peterson Avenue', 'Foster Avenue', 'Lawrence Avenue', 'Montrose Avenue', 'Irving Park Road', 'Addison Street', 'Belmont Avenue',
             'Diversey Avenue', 'Fullerton Avenue', 'Armitage Avenue', 'North Avenue', 'Division Street', 'Chicago Avenue', 'Lake Street', 'Madison Street',
             'Roosevelt Road', 'Cermak Road', '31st Street', '47th Street', 'Archer Avenue', '55th Street']


def main():
    P = []
    # CTA Red Line Extension: stations near Eggleston at 103rd and 111th, Michigan near 116th, 130th near Altgeld Gardens (CTA 2026 boards)
    rle = [[-87.62434, 41.72238]]   # 95th/Dan Ryan (the Red Line's end today)
    for cross, nearpt in [('103rd Street', (41.7068, -87.6340)), ('111th Street', (41.6922, -87.6340))]:
        p = crossing('Halsted Street', cross, nearpt)   # cross street located, then moved to Eggleston (about 400 W)
        rle.append([-87.6340, p[1]] if p else [-87.6340, nearpt[0]])   # Eggleston Ave, about 430 W
    p = crossing('Michigan Avenue', '115th Street', (41.6851, -87.6213))
    rle.append([p[0], round(p[1] - 0.0018, 6)] if p else [-87.6213, 41.6833])   # near 116th
    rle.append([-87.6094, 41.6595])   # 130th near Altgeld Gardens
    P.append({'id': 'rle', 'group': 'rail', 'name': 'Red Line Extension', 'mode': 'elevated', 'head': 5, 'pts': rle, 'extends': True,
              'gap': 'CTA\u2019s forecast counts every trip that uses the extension, including bus riders whose routes would be moved to the new stations, park-and-ride at 130th, and the return trip that starts downtown. This tool counts people entering the four new stations with today\u2019s buses, so it comes out much lower.', 'status': 'Under construction, opening 2030–31',
              'approx': 'Station spots are approximate (CTA gives cross streets only).',
              'official': {'cost': 5.75e9, 'costYear': 2025, 'yoe': True, 'costNote': 'year-of-spending dollars through 2031, full funding agreement (FTA)',
                           'riders': 36400, 'ridersNote': 'daily linked trips, 2019 forecast year (41,500 in 2040)',
                           'federal': 0.343, 'opens': '2030–31'},
              'sources': [['FTA funding agreement profile, 2025', 'https://www.transit.dot.gov/sites/fta.dot.gov/files/2025-01/IL-Chicago-Red-Line-Extension-FFGA-Profile-FY26-01-16-2025_0.pdf'],
                          ['FTA engineering profile, 2023 (ridership)', 'https://www.transit.dot.gov/sites/fta.dot.gov/files/2023-08/IL-Chicago-Red-Line-Extension-Project-Engineering-Profile.pdf'],
                          ['CTA station boards, 2026', 'https://lapi.transitchicago.com/assets/1/6/REF_20260116_RLE-Fall-Station-Meeting-Boards_Rev01.pdf']]})
    P.append({'id': 'ashland', 'group': 'bus', 'name': 'Ashland Avenue BRT', 'mode': 'brt', 'head': 5, 'pts': along('Ashland Avenue', ASHLAND_X, (41.85, -87.6667)),
              'status': 'Shelved by CTA; in CMAP’s 2026 regional plan',
              'official': {'cost': 166e6, 'costYear': 2025, 'costNote': '2025 dollars, CMAP 2026 plan (CTA’s 2013 estimate: $160M)',
                           'riders': 13600, 'ridersNote': 'more weekday transit trips across the region in 2050 (CMAP model); CTA 2013: up to 29% more riders on the corridor (29–41% in its modeling)'},
              'sources': [['CMAP 2026 plan benefits report', CMAP_RTP], ['CTA Ashland BRT handout (stops)', 'https://lapi.transitchicago.com/assets/1/6/Ashland_BRT_EA_Handout_-_text_document.pdf'],
                          ['Streetsblog, 2013', 'https://chi.streetsblog.org/2013/04/19/cta-officials-share-details-of-the-plan-for-gold-standard-brt-on-ashland/']]})
    P.append({'id': 'western', 'group': 'bus', 'name': 'Western Avenue bus priority', 'mode': 'brt', 'head': 5, 'pts': along('Western Avenue', WESTERN_X, (41.87, -87.6866)),
              'status': 'In CMAP’s 2026 regional plan', 'approx': 'Extent follows today’s #49 bus; CMAP doesn’t give stop locations.',
              'official': {'cost': 339e6, 'costYear': 2025, 'costNote': '2025 dollars, CMAP 2026 plan',
                           'riders': 22700, 'ridersNote': 'more weekday transit trips across the region in 2050 (CMAP model), the most of any project'},
              'sources': [['CMAP 2026 plan benefits report', CMAP_RTP]]})
    P.append({'id': 'pulaski', 'group': 'bus', 'name': 'Pulaski Road bus priority', 'mode': 'brt', 'head': 5, 'pts': along('Pulaski Road', PULASKI_X, (41.87, -87.7259)),
              'status': 'In CMAP’s 2026 regional plan', 'approx': 'Extent follows today’s #53 bus; CMAP doesn’t give stop locations.',
              'official': {'cost': 323e6, 'costYear': 2025, 'costNote': '2025 dollars, CMAP 2026 plan',
                           'riders': 17700, 'ridersNote': 'more weekday transit trips across the region in 2050 (CMAP model)'},
              'sources': [['CMAP 2026 plan benefits report', CMAP_RTP]]})
    # Mid-City Transitway: Jefferson Park south along the rail corridor a quarter mile east of Cicero, then east along the Belt Railway to the Dan Ryan
    mc = along('Cicero Avenue', ['Montrose Avenue', 'Irving Park Road', 'Belmont Avenue', 'Fullerton Avenue', 'North Avenue', 'Chicago Avenue', 'Lake Street',
                                  'Roosevelt Road', 'Cermak Road', '31st Street', '47th Street', '55th Street', '63rd Street', '71st Street', '79th Street'], (41.85, -87.7454))
    mc = [[round(p[0] + 400 / KX, 6), p[1]] for p in mc]   # a quarter mile east of Cicero
    mc = mc[:-1]   # drop 79th: the line turns east near 75th
    mc += [[-87.7215, 41.7575], [-87.7025, 41.7565], [-87.6838, 41.7550], [-87.6640, 41.7495], [-87.6440, 41.7400], [-87.6262, 41.7357]]   # east along the Belt Railway near 75th, meeting the Red Line between 87th and 91st
    P.append({'id': 'midcity', 'group': 'rail', 'name': 'Mid-City Transitway', 'mode': 'elevated', 'head': 7.5, 'pts': mc, 'status': 'Idea only: a "visionary" project in CMAP’s 2026 plan',
              'approx': 'Alignment and stations are approximate, from a 2002 description; no current plan exists.',
              'official': {'cost': None, 'costNote': 'no current estimate ("at least $1 billion" in 2002)', 'opYear': 21.9e6, 'riders': 11000,
                           'ridersNote': 'more weekday transit trips across the region in 2050 (CMAP model); 2002 claim: 94,000 riders a day'},
              'sources': [['CMAP 2026 plan benefits report', CMAP_RTP], ['Chicago Tribune, 2002 (via chicago-l.org)', 'https://chicago-l.org/articles/mid-city02.html']]})
    P.append({'id': 'ri', 'group': 'metra', 'name': 'Rock Island all-day trains', 'metra': 'RI', 'head': 20, 'status': 'CMAP’s plan funds track and yard work on the Rock Island',
              'approx': 'CMAP’s project adds a third track, new signals and a bigger 47th Street yard; the preset shows trains every 20 minutes.',
              'official': {'cost': 810e6, 'costYear': 2025, 'costNote': '2025 dollars, CMAP 2026 plan (Rock Island improvements)', 'riders': 8500,
                           'ridersNote': 'more weekday transit trips across the region in 2050 (CMAP model)'},
              'sources': [['CMAP 2026 plan benefits report', CMAP_RTP]]})
    P.append({'id': 'me', 'group': 'metra', 'name': 'Metra Electric improvements', 'metra': 'ME', 'head': 15, 'status': 'In CMAP’s 2026 regional plan; trains every 20 minutes midday since June 2026',
              'approx': 'The preset shows trains every 15 minutes.',
              'official': {'cost': 1140e6, 'costYear': 2025, 'costNote': '2025 dollars, CMAP 2026 plan', 'riders': 7000,
                           'ridersNote': 'more weekday transit trips across the region in 2050 (CMAP model)'},
              'sources': [['CMAP 2026 plan benefits report', CMAP_RTP],
                          ['NBC Chicago, June 2026', 'https://www.nbcchicago.com/traffic/transit/new-metra-electric-line-schedule-with-increased-service-going-into-effect/3948484/']]})
    # ---- more CTA rail (CMAP 2026 plan; alignments from CTA's 2009 studies or the old line) ----
    oc = crossing('Cicero Avenue', '76th Street', (41.7555, -87.7417)) or [-87.7417, 41.7555]
    P.append({'id': 'orange', 'group': 'rail', 'name': 'Orange Line to Ford City', 'mode': 'elevated', 'head': 7.5, 'extends': True,
              'pts': [[-87.73788, 41.78661], oc], 'status': 'Studied 2009 (elevated on Cicero, one station at Ford City); CTA isn’t studying it now',
              'approx': 'Station at 76th and Cicero, as in CTA’s 2009 preferred route.',
              'official': {'cost': 445e6, 'costYear': 2025, 'costNote': '2025 dollars, CMAP 2026 plan (“visionary” list)', 'riders': 700,
                           'ridersNote': 'more weekday transit trips across the region in 2050 (CMAP model)'},
              'sources': [['CMAP 2026 plan benefits report', CMAP_RTP], ['CTA Orange Line extension study', 'https://transitchicago.com/orangeeis']]})
    yo = crossing('Skokie Boulevard', 'Old Orchard Road', (42.0590, -87.7440)) or [-87.7440, 42.0590]
    P.append({'id': 'yellow', 'group': 'rail', 'name': 'Yellow Line to Old Orchard', 'mode': 'elevated', 'head': 10, 'extends': True,
              'pts': [[-87.75192, 42.03895], yo], 'status': 'Studied 2009–12 (one station at Old Orchard); CTA isn’t studying it now',
              'approx': 'Station near Old Orchard Road and Skokie Boulevard.',
              'official': {'cost': 263e6, 'costYear': 2025, 'costNote': '2025 dollars, CMAP 2026 plan (“visionary” list)', 'riders': 2300,
                           'ridersNote': 'more weekday transit trips across the region in 2050 (CMAP model)'},
              'sources': [['CMAP 2026 plan benefits report', CMAP_RTP], ['CTA Yellow Line extension study', 'https://transitchicago.com/YellowEIS']]})
    P.append({'id': 'greenjp', 'group': 'rail', 'name': 'Green Line back to Jackson Park', 'mode': 'elevated', 'head': 10, 'extends': True,
              'pts': [[-87.60586, 41.78031], [-87.5978, 41.7802], [-87.5917, 41.7802], [-87.5866, 41.7803]],
              'status': 'Idea only: a “visionary” project in CMAP’s 2026 plan (the old branch east of Cottage Grove closed in 1982)',
              'approx': 'Stations at University, Dorchester and Stony Island, where the old line stopped.',
              'official': {'cost': None, 'costNote': 'no estimate', 'riders': 3400, 'ridersNote': 'more weekday transit trips across the region in 2050 (CMAP model)'},
              'sources': [['CMAP 2026 plan benefits report', CMAP_RTP], ['chicago-l.org: Jackson Park branch', 'https://www.chicago-l.org/operations/lines/southside.html']]})
    cl = [[-87.64918, 41.91065]] + along('Ashland Avenue', ['North Avenue', 'Division Street', 'Chicago Avenue'], (41.90, -87.6676)) + [[-87.66697, 41.88527], [-87.67393, 41.87571]] \
        + along('Ashland Avenue', ['Roosevelt Road'], (41.867, -87.6664)) + [crossing('Blue Island Avenue', 'Cermak Road', (41.852, -87.6600)) or [-87.6600, 41.8524], [-87.66532, 41.83923]]
    P.append({'id': 'circle', 'group': 'rail', 'name': 'Circle Line', 'mode': 'elevated', 'head': 7.5, 'pts': cl,
              'status': 'Studied 2006–09; CTA isn’t studying it now. CMAP: “costly for the level of benefits”',
              'approx': 'Stations are approximate: CMAP describes a line along Ashland from North/Clybourn to the Orange Line; CTA’s study mixed new subway, elevated and the Pink Line’s tracks.',
              'official': {'cost': 1.1e9, 'costYear': 2009, 'yoe': True, 'costNote': 'year-of-spending dollars, CTA 2009, for the southern phases only; CMAP gives no cost',
                           'opYear': 22e6, 'riders': 8800, 'ridersNote': 'more weekday transit trips across the region in 2050 for CMAP’s full line up Ashland to North/Clybourn (CMAP model); CTA 2009: 10 million rides a year in 2030'},
              'sources': [['CMAP 2026 plan benefits report', CMAP_RTP], ['CTA Circle Line study boards', 'https://lapi.transitchicago.com/assets/1/6/Circle_Line_Screen_3_Boards_text_Format.txt'],
                          ['CMAP unconstrained projects', 'https://cmap.illinois.gov/recommendation/unconstrained-project/']]})
    # ---- more bus priority corridors (CTA/CDOT Better Streets for Buses extents) ----
    BSB = ['CTA Better Streets for Buses', 'https://transitchicago.com/betterstreetsforbuses/']
    gar = along(['55th Street', 'Garfield Boulevard'], ['Cicero Avenue', 'Pulaski Road', 'Kedzie Avenue', 'California Avenue', 'Western Avenue', 'Damen Avenue',
                 'Ashland Avenue', 'Racine Avenue', 'Halsted Street', 'State Street', 'Martin Luther King Drive', 'Cottage Grove Avenue', 'Ellis Avenue',
                 'Woodlawn Avenue', 'Lake Park Avenue'], (41.794, -87.66), {'Ellis Avenue': [-87.6013, 41.7950], 'Woodlawn Avenue': [-87.5966, 41.7951]})
    P.append({'id': 'garfield', 'group': 'bus', 'name': '55th/Garfield bus priority', 'mode': 'brt', 'head': 6, 'pts': gar,
              'status': 'Studied by CTA and CDOT (Better Streets for Buses); in CMAP’s 2026 plan', 'approx': 'Cicero to Hyde Park, as studied; CMAP doesn’t give stop locations.',
              'official': {'cost': 150e6, 'costYear': 2025, 'costNote': '2025 dollars, CMAP 2026 plan', 'riders': 3200, 'ridersNote': 'more weekday transit trips across the region in 2050 (CMAP model)'},
              'sources': [['CMAP 2026 plan benefits report', CMAP_RTP], BSB]})
    c0 = crossing('Fullerton Avenue', 'Cicero Avenue', (41.925, -87.7465))
    mi_lon = 1609.3 / KX
    ful_w = {nm: [round(c0[0] - (no - 4800) / 800 * mi_lon, 6), c0[1]] for nm, no in [('Narragansett Avenue', 6400), ('Central Avenue', 5600), ('Laramie Avenue', 5200)]}
    ful = along('Fullerton Avenue', ['Narragansett Avenue', 'Central Avenue', 'Laramie Avenue', 'Cicero Avenue', 'Kostner Avenue', 'Pulaski Road', 'Kedzie Avenue',
                                     'California Avenue', 'Western Avenue', 'Damen Avenue', 'Ashland Avenue', 'Racine Avenue', 'Halsted Street'], (41.925, -87.70), ful_w)
    P.append({'id': 'fullerton', 'group': 'bus', 'name': 'Fullerton bus priority', 'mode': 'brt', 'head': 8, 'pts': ful,
              'status': 'Studied by CTA and CDOT (Better Streets for Buses); in CMAP’s 2026 plan', 'approx': 'Near Grand Avenue to Halsted, as studied; CMAP doesn’t give stop locations.',
              'official': {'cost': 145e6, 'costYear': 2025, 'costNote': '2025 dollars, CMAP 2026 plan', 'riders': 4600, 'ridersNote': 'more weekday transit trips across the region in 2050 (CMAP model)'},
              'sources': [['CMAP 2026 plan benefits report', CMAP_RTP], BSB]})
    cg = along('Cottage Grove Avenue', ['35th Street', 'Pershing Road', '43rd Street', '47th Street', '51st Street', '55th Street', '63rd Street', '67th Street',
                                        '71st Street', '75th Street', '79th Street', '83rd Street', '87th Street', '95th Street', '103rd Street', '111th Street', '115th Street'], (41.75, -87.6055))
    P.append({'id': 'cottage', 'group': 'bus', 'name': 'Cottage Grove bus priority', 'mode': 'brt', 'head': 8, 'pts': cg,
              'status': 'Studied by CTA and CDOT (Better Streets for Buses); in CMAP’s 2026 plan', 'approx': '35th to 115th, as studied; CMAP doesn’t give stop locations.',
              'official': {'cost': 181e6, 'costYear': 2025, 'costNote': '2025 dollars, CMAP 2026 plan', 'riders': 2600, 'ridersNote': 'more weekday transit trips across the region in 2050 (CMAP model)'},
              'sources': [['CMAP 2026 plan benefits report', CMAP_RTP], BSB]})
    # ---- Metra: CMAP's line projects, shown as all-day trains ----
    NETPLAN = ['Sun-Times: Metra’s draft network plan, Oct. 2026', 'https://chicago.suntimes.com/transportation/2026/10/16/metra-shares-dream-plan-to-offer-trains-every-15-30-minutes']
    for mid, name, head, cost, riders, what in [
            ('BNSF', 'BNSF all-day trains', 20, 328e6, 9000, 'CMAP’s BNSF project (including a new Eola Road station)'),
            ('UP-N', 'UP North all-day trains', 20, 1174e6, 7400, 'CMAP’s UP North project (including a Peterson/Ridge station)'),
            ('UP-W', 'UP West all-day trains', 20, 471e6, 7500, 'CMAP’s UP West project'),
            ('UP-NW', 'UP Northwest all-day trains', 20, 859e6, 9600, 'CMAP’s UP Northwest project, which also extends the line 1.6 miles to Johnsburg (not drawn)'),
            ('MD-W', 'Milwaukee West all-day trains', 30, 769e6, 5100, 'CMAP’s Milwaukee West project'),
            ('MD-N', 'Milwaukee North all-day trains', 30, 832e6, 2100, 'CMAP’s Milwaukee North project'),
            ('SWS', 'SouthWest Service all-day trains', 30, 776e6, 2900, 'CMAP’s SouthWest Service project')]:
        P.append({'id': 'm-' + mid.lower(), 'group': 'metra', 'name': name, 'metra': mid, 'head': head, 'status': 'Line upgrades in CMAP’s 2026 regional plan',
                  'approx': f'{what} adds track, signals or stations; the preset shows trains every {head} minutes all day. Metra’s October 2026 draft network plan aims for trains every 15–30 minutes on every line, for about $9 billion.',
                  'official': {'cost': cost, 'costYear': 2025, 'costNote': '2025 dollars, CMAP 2026 plan', 'riders': riders,
                               'ridersNote': 'more weekday transit trips across the region in 2050 (CMAP model)'},
                  'sources': [['CMAP 2026 plan benefits report', CMAP_RTP], NETPLAN]})
    for p in P:
        if 'pts' in p:
            print(p['id'], len(p['pts']), 'stations', file=sys.stderr)
    align(P)
    json.dump(P, open(os.path.join(OUT, 'presets.json'), 'w'), indent=0)


if __name__ == '__main__':
    main()
