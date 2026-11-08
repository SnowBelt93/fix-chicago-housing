#!/usr/bin/env python3
"""Megaproject buildings for the map, drawn from each project's published site plan.

Each <project>.py here holds the plan's buildings as pixels on a published plan image (source named at the top of the file)
and the street crossings used to place that image on the map (an affine fit; the script prints how far each crossing lands
from the street data, in metres). Stories come from the plan where it labels them (North Union), from published heights
and phases (Foundry Park, the 1901 Project's subarea limits, Bronzeville Lakefront's phase massing), from homes per
building (Cabrini NOW massing diagrams: stories = homes x 1,000 sq ft / footprint), or, where the plan shows footprints
but no heights (The 78), are set so the homes add up to the 10,000 the zoning allows. Use: res (homes), office/hotel
(no homes, drawn with their phase), anchor (non-housing building already under way, drawn from 2028), built (finished,
drawn from the start).

Writes meta.json megaSites[name].bld = [[x1, y1, ... in metres from the site origin], stories, use code, phase] where use
code 0 = homes, 1 = no homes, 2 = anchor, 3 = built. Keeps megaSites[name].land from tools/prep_mega.py and adds today's buildings standing where the plan puts a new one
(their centre inside it), which the game hides once the project starts.
Usage: python3 tools/mega/build.py   (python3 tools/mega/check.py draws every project over the street grid)
"""
import json, math, os, runpy, sys
import numpy as np
from shapely.geometry import Polygon, Point
from shapely.ops import unary_union
from shapely.prepared import prep
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(os.path.dirname(HERE))
DECK = 111319.49
FILES = {"The 78": "the78", "Foundry Park": "foundry", "1901 Project": "p1901", "Bronzeville Lakefront": "bronze",
         "North Union": "nunion", "Cabrini-Green (CHA)": "cabrini"}
USE = {"res": 0, "mix": 0, "office": 1, "hotel": 1, "hall": 1, "anchor": 2, "built": 3}
sys.path.insert(0, os.path.dirname(HERE)); from prep_mega import read_area
os.chdir(HERE)
meta = json.load(open(os.path.join(ROOT, 'meta.json')))
for name, mod in FILES.items():
    print(name); runpy.run_path(mod + '.py')
    B = json.load(open(mod + '.json'))
    S = meta['megaSites'][name]; kx = DECK * math.cos(math.radians(S['lat']))
    area = lambda p: abs(sum(p[i][0] * p[i - 1][1] - p[i - 1][0] * p[i][1] for i in range(len(p)))) / 2
    if name == "The 78":   # no published heights: scale the homes buildings so their floor area holds 10,000 homes at 1,026 sq ft
        res = [b for b in B if b['use'] == 'res']
        xy = lambda b: [((x - S['lon']) * kx, (y - S['lat']) * DECK) for x, y in b['p']]
        tot = sum(area(xy(b)) * b['st'] for b in res); k = 10000 * 1026 * 0.0929 / tot
        # big blocks become a 5-story podium plus a tower (about 30 x 32 m) on the corner nearest the river, holding the rest
        extra = []
        for b in res:
            P = xy(b); a = area(P); target = a * b['st'] * k
            if a > 2500 and target > a * 7:
                b['st'] = 5; x0 = min(x for x, y in P); y1 = max(y for x, y in P)
                tw = [(x0 + 3, y1 - 35), (x0 + 33, y1 - 35), (x0 + 33, y1 - 3), (x0 + 3, y1 - 3)]
                extra.append(dict(n=b['n'] + ' tower', use='res', ph=b['ph'], st=min(60, round(5 + (target - a * 5) / 960)),
                                  p=[(S['lon'] + x / kx, S['lat'] + y / DECK) for x, y in tw]))
            else: b['st'] = max(4, round(b['st'] * k))
        B += extra
        print('  heights x', round(k, 2), [b['st'] for b in B if b['use'] == 'res'])
    def ring(b):
        r = [[round(v, 1) for x, y in b['p'] for v in ((x - S['lon']) * kx, (y - S['lat']) * DECK)], b['st'], USE[b['use']], b.get('ph', 1)]
        # big mid-rise blocks get a courtyard, as Chicago's perimeter blocks do: an inner ring 16 m in from each side
        P = Polygon([(r[0][i], r[0][i + 1]) for i in range(0, len(r[0]), 2)])
        if b['use'] in ('res', 'mix') and b['st'] <= 16 and P.area > 3500 and P.minimum_rotated_rectangle.exterior is not None:
            m = P.minimum_rotated_rectangle; e = list(m.exterior.coords)
            sides = sorted(math.dist(e[i], e[i + 1]) for i in range(2))
            if sides[0] > 52:
                h = P.buffer(-16, join_style=2)
                if not h.is_empty and h.geom_type == 'Polygon': r.append([round(v, 1) for c in list(h.exterior.coords)[:-1] for v in c])
        return r
    S['bld'] = [ring(b) for b in B]
    S.pop('fp', None)
    # today's buildings under the plan's new buildings: hidden by the game once the project starts
    under = prep(unary_union([Polygon(b['p']).buffer(0) for b in B if b['use'] not in ('built',)]))
    for A in meta['areas']:
        if math.hypot((A['lon'] - S['lon']) * kx, (A['lat'] - S['lat']) * DECK) > 4000: continue
        R = read_area(A['num']); kxa = DECK * math.cos(math.radians(R['lat0'])); add = []
        for i in range(R['N']):
            v = R['q'][R['starts'][i]:R['starts'][i + 1]]
            if not len(v): continue
            cx, cy = v.mean(0)
            if under.contains(Point(R['lon0'] + cx / kxa, R['lat0'] + cy / DECK)): add.append(i)
        if add:
            L = set(S['land'].get(str(A['num']), [])) | set(add); S['land'][str(A['num'])] = sorted(L)
            print(f"  area {A['num']}: {len(add)} buildings under the plan")
    os.remove(mod + '.json')
json.dump(meta, open(os.path.join(ROOT, 'meta.json'), 'w'), separators=(',', ':'))
print('wrote meta.json megaSites[].bld')
