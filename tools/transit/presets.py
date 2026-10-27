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
                           'opYear': 22e6, 'riders': 8800, 'ridersNote': 'more weekday transit trips across the region in 2050 (CMAP model); CTA 2009: 10 million rides a year in 2030'},
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
    json.dump(P, open(os.path.join(OUT, 'presets.json'), 'w'), indent=0)


if __name__ == '__main__':
    main()
