#!/usr/bin/env python3
"""history/data/pop.json (community area populations by census year) and history/data/photos.json (Library of Congress
HABS photos placed by the street address in their title, using the lot tool's address index lot/data/a/*.json and
lot/data/t/*.json). Run tools/history/fetch.py (Actions) and tools/prep_lots.py first."""
import json, os, re
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RAW = os.path.join(ROOT, 'tools', 'raw', 'history'); OUT = os.path.join(ROOT, 'history', 'data'); os.makedirs(OUT, exist_ok=True)
json.dump(json.load(open(os.path.join(RAW, 'ca_population.json'))), open(os.path.join(OUT, 'pop.json'), 'w'), separators=(',', ':'))
DIR = {'NORTH': 'N', 'SOUTH': 'S', 'EAST': 'E', 'WEST': 'W', 'N.': 'N', 'S.': 'S', 'E.': 'E', 'W.': 'W'}
SUF = {'STREET': 'ST', 'AVENUE': 'AVE', 'BOULEVARD': 'BLVD', 'DRIVE': 'DR', 'PLACE': 'PL', 'ROAD': 'RD', 'COURT': 'CT', 'PARKWAY': 'PKWY'}
shards, tiles, out = {}, {}, []
for it in json.load(open(os.path.join(RAW, 'habs.json'))):
    t = it.get('title') or ''
    m = re.search(r'\b(\d{2,5})(?:-\d+)?\s+(North|South|East|West|N\.|S\.|E\.|W\.)\s+([A-Za-z0-9 .\']+?)\s+(Street|Avenue|Boulevard|Drive|Place|Road|Court|Parkway)\b', t)
    if not m: continue
    num = int(m.group(1)); street = f"{DIR[m.group(2).upper()]} {m.group(3).upper().replace('.', '')} {SUF[m.group(4).upper()]}"
    key = re.sub(r'[^A-Z0-9]', '', re.sub(r'^[NSEW] ', '', street))[:2]
    if key not in shards:
        p = os.path.join(ROOT, 'lot', 'data', 'a', key + '.json'); shards[key] = json.load(open(p)) if os.path.exists(p) else {}
    L = shards[key].get(street)
    if not L: continue
    best = min(L, key=lambda r: abs(r[0] - num))
    if abs(best[0] - num) > 60: continue
    tk = f'{best[1]}_{best[2]}'
    if tk not in tiles: tiles[tk] = json.load(open(os.path.join(ROOT, 'lot', 'data', 't', tk + '.json')))
    p = tiles[tk]['p'][best[3]]
    lon, lat = best[1] / 100 - 88 + p[1] / 1e6, best[2] / 100 + 41 + p[2] / 1e6
    imgs = [u.split('#')[0] for u in it.get('images') or []]
    img = next((u for u in imgs if u.endswith('pr.jpg')), imgs[-1] if imgs else '')
    out.append({'p': [round(lon, 6), round(lat, 6)], 't': t.replace(', Chicago, Cook County, IL', ''), 'date': it.get('date') or '', 'u': it.get('url'), 'img': img})
json.dump(out, open(os.path.join(OUT, 'photos.json'), 'w'), separators=(',', ':'))
print('photos placed', len(out))
