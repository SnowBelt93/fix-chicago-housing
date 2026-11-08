"""Data for "Chicago then and now" (runs in GitHub Actions). Writes under tools/raw/history/:
  ca_population.json  each community area's population by census year, read from the "Historical population" box
                      ({{US Census population}} template) on its Wikipedia page, which cites the U.S. Census
  habs.json           Library of Congress HABS/HAER/HALS records for Chicago (public domain): title (with the address),
                      date, record URL and image URLs, so old photos can be placed on the map"""
import urllib.request, urllib.parse, json, os, re, time
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(ROOT, 'tools', 'raw', 'history'); os.makedirs(OUT, exist_ok=True)
HDR = {'User-Agent': 'ShapeChicago/1.0 (github.com/SnowBelt93/fix-chicago-housing; civic education project)'}
def get(url, tries=4):
    for t in range(tries):
        try: return urllib.request.urlopen(urllib.request.Request(url, headers=HDR), timeout=120).read()
        except Exception as e: print('retry', t, url[:100], e, flush=True); time.sleep(5 * (t + 1))
    return None

meta = json.load(open(os.path.join(ROOT, 'meta.json')))
pops = {}
for a in meta['areas']:
    name = a['name']
    for title in (f"{name}, Chicago", name):
        u = 'https://en.wikipedia.org/w/api.php?' + urllib.parse.urlencode({'action': 'parse', 'page': title, 'prop': 'wikitext', 'format': 'json', 'redirects': 1})
        b = get(u)
        if not b: continue
        d = json.loads(b)
        wt = d.get('parse', {}).get('wikitext', {}).get('*', '')
        if 'US Census population' not in wt and 'Historical populations' not in wt: continue
        m = re.search(r'\{\{\s*(?:US Census population|Historical populations)(.*?)\}\}', wt, re.S)
        if not m: continue
        body = m.group(1)
        vals = {}
        for y, v in re.findall(r'\|\s*(1[89]\d0|20[0-2]0)\s*=\s*([\d,]+)', body): vals[int(y)] = int(v.replace(',', ''))
        if not vals:   # Historical populations style: | 1930 | 46,746 |
            for y, v in re.findall(r'\|\s*(1[89]\d0|20[0-2]0)\s*\|\s*([\d,]+)', body): vals[int(y)] = int(v.replace(',', ''))
        if vals:
            pops[a['num']] = {'name': name, 'page': d['parse'].get('title'), 'pop': vals}; break
    time.sleep(0.3)
print('areas with populations', len(pops), flush=True)
json.dump(pops, open(os.path.join(OUT, 'ca_population.json'), 'w'), indent=1)

items, page = [], 1
while page < 60:
    u = 'https://www.loc.gov/collections/historic-american-buildings-landscapes-and-engineering-records/?' + urllib.parse.urlencode({'fa': 'location_city:chicago', 'fo': 'json', 'c': 100, 'sp': page})
    b = get(u)
    if not b: break
    d = json.loads(b)
    for r in d.get('results', []):
        items.append({'title': r.get('title'), 'date': r.get('date'), 'url': r.get('url') or r.get('id'), 'images': r.get('image_url') or [],
                      'subjects': r.get('subject') or [], 'location': r.get('location') or []})
    print('loc page', page, len(d.get('results', [])), flush=True)
    if not d.get('pagination', {}).get('next'): break
    page += 1; time.sleep(1)
json.dump(items, open(os.path.join(OUT, 'habs.json'), 'w'))
print('habs items', len(items))
