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


def along(main, crosses, near=None):
    # cross streets missing from the map's main-road layer are placed between their found neighbors
    # (by street number for numbered streets, else evenly)
    got = [crossing(main, c, near) for c in crosses]
    num = lambda c: int(re.match(r'(\d+)', c).group(1)) if re.match(r'\d+', c) else None
    missing = [c for c, p in zip(crosses, got) if not p]
    for i, p in enumerate(got):
        if p:
            continue
        a = next((k for k in range(i - 1, -1, -1) if got[k]), None); b = next((k for k in range(i + 1, len(got)) if got[k]), None)
        if a is None or b is None:
            continue
        na, nb, ni = num(crosses[a]), num(crosses[b]), num(crosses[i])
        t = (ni - na) / (nb - na) if None not in (na, nb, ni) and nb != na else (i - a) / (b - a)
        got[i] = [round(got[a][0] + t * (got[b][0] - got[a][0]), 6), round(got[a][1] + t * (got[b][1] - got[a][1]), 6)]
    if missing:
        print(f'  {main}: placed between neighbors:', missing, file=sys.stderr)
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
    P.append({'id': 'rle', 'name': 'Red Line Extension', 'mode': 'elevated', 'head': 5, 'pts': rle, 'extends': True,
              'gap': 'CTA\u2019s forecast counts every trip that uses the extension, including bus riders whose routes would be moved to the new stations, park-and-ride at 130th, and the return trip that starts downtown. This tool counts people entering the four new stations with today\u2019s buses, so it comes out much lower.', 'status': 'Under construction, opening 2030–31',
              'approx': 'Station spots are approximate (CTA gives cross streets only).',
              'official': {'cost': 5.75e9, 'costYear': 2025, 'yoe': True, 'costNote': 'year-of-spending dollars through 2031, full funding agreement (FTA)',
                           'riders': 36400, 'ridersNote': 'daily linked trips, 2019 forecast year (41,500 in 2040)',
                           'federal': 0.343, 'opens': '2030–31'},
              'sources': [['FTA funding agreement profile, 2025', 'https://www.transit.dot.gov/sites/fta.dot.gov/files/2025-01/IL-Chicago-Red-Line-Extension-FFGA-Profile-FY26-01-16-2025_0.pdf'],
                          ['FTA engineering profile, 2023 (ridership)', 'https://www.transit.dot.gov/sites/fta.dot.gov/files/2023-08/IL-Chicago-Red-Line-Extension-Project-Engineering-Profile.pdf'],
                          ['CTA station boards, 2026', 'https://lapi.transitchicago.com/assets/1/6/REF_20260116_RLE-Fall-Station-Meeting-Boards_Rev01.pdf']]})
    P.append({'id': 'ashland', 'name': 'Ashland Avenue BRT', 'mode': 'brt', 'head': 5, 'pts': along('Ashland Avenue', ASHLAND_X, (41.85, -87.6667)),
              'status': 'Shelved by CTA; in CMAP’s 2026 regional plan',
              'official': {'cost': 166e6, 'costYear': 2025, 'costNote': '2025 dollars, CMAP 2026 plan (CTA’s 2013 estimate: $160M)',
                           'riders': 13600, 'ridersNote': 'more weekday transit trips across the region in 2050 (CMAP model); CTA 2013: up to 29% more riders on the corridor (29–41% in its modeling)'},
              'sources': [['CMAP 2026 plan benefits report', CMAP_RTP], ['CTA Ashland BRT handout (stops)', 'https://lapi.transitchicago.com/assets/1/6/Ashland_BRT_EA_Handout_-_text_document.pdf'],
                          ['Streetsblog, 2013', 'https://chi.streetsblog.org/2013/04/19/cta-officials-share-details-of-the-plan-for-gold-standard-brt-on-ashland/']]})
    P.append({'id': 'western', 'name': 'Western Avenue bus priority', 'mode': 'brt', 'head': 5, 'pts': along('Western Avenue', WESTERN_X, (41.87, -87.6866)),
              'status': 'In CMAP’s 2026 regional plan', 'approx': 'Extent follows today’s #49 bus; CMAP doesn’t give stop locations.',
              'official': {'cost': 339e6, 'costYear': 2025, 'costNote': '2025 dollars, CMAP 2026 plan',
                           'riders': 22700, 'ridersNote': 'more weekday transit trips across the region in 2050 (CMAP model), the most of any project'},
              'sources': [['CMAP 2026 plan benefits report', CMAP_RTP]]})
    P.append({'id': 'pulaski', 'name': 'Pulaski Road bus priority', 'mode': 'brt', 'head': 5, 'pts': along('Pulaski Road', PULASKI_X, (41.87, -87.7259)),
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
    P.append({'id': 'midcity', 'name': 'Mid-City Transitway', 'mode': 'elevated', 'head': 7.5, 'pts': mc, 'status': 'Idea only: a "visionary" project in CMAP’s 2026 plan',
              'approx': 'Alignment and stations are approximate, from a 2002 description; no current plan exists.',
              'official': {'cost': None, 'costNote': 'no current estimate ("at least $1 billion" in 2002)', 'opYear': 21.9e6, 'riders': 11000,
                           'ridersNote': 'more weekday transit trips across the region in 2050 (CMAP model); 2002 claim: 94,000 riders a day'},
              'sources': [['CMAP 2026 plan benefits report', CMAP_RTP], ['Chicago Tribune, 2002 (via chicago-l.org)', 'https://chicago-l.org/articles/mid-city02.html']]})
    P.append({'id': 'ri', 'name': 'Rock Island all-day trains', 'metra': 'RI', 'head': 20, 'status': 'CMAP’s plan funds track and yard work on the Rock Island',
              'approx': 'CMAP’s project adds a third track, new signals and a bigger 47th Street yard; the preset shows trains every 20 minutes.',
              'official': {'cost': 810e6, 'costYear': 2025, 'costNote': '2025 dollars, CMAP 2026 plan (Rock Island improvements)', 'riders': 8500,
                           'ridersNote': 'more weekday transit trips across the region in 2050 (CMAP model)'},
              'sources': [['CMAP 2026 plan benefits report', CMAP_RTP]]})
    P.append({'id': 'me', 'name': 'Metra Electric improvements', 'metra': 'ME', 'head': 15, 'status': 'In CMAP’s 2026 regional plan; trains every 20 minutes midday since June 2026',
              'approx': 'The preset shows trains every 15 minutes.',
              'official': {'cost': 1140e6, 'costYear': 2025, 'costNote': '2025 dollars, CMAP 2026 plan', 'riders': 7000,
                           'ridersNote': 'more weekday transit trips across the region in 2050 (CMAP model)'},
              'sources': [['CMAP 2026 plan benefits report', CMAP_RTP],
                          ['NBC Chicago, June 2026', 'https://www.nbcchicago.com/traffic/transit/new-metra-electric-line-schedule-with-increased-service-going-into-effect/3948484/']]})
    for p in P:
        if 'pts' in p:
            print(p['id'], len(p['pts']), 'stations', file=sys.stderr)
    json.dump(P, open(os.path.join(OUT, 'presets.json'), 'w'), indent=0)


if __name__ == '__main__':
    main()
