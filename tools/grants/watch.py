"""Weekly check of every program page the grants finder cites (grants/data/programs.json on shape-v1).
Downloads each link, strips tags and dates, and keeps a hash of the text in tools/raw/grants/watch.json. When a page's
text changes, its entry gets "changed": <date> so the program can be re-read and its `checked` date updated in
tools/grants/programs.py on shape-v1. Pages that fail to load get "error". Nothing else is stored (no page text)."""
import json, os, re, sys, hashlib, subprocess, datetime, urllib.request
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(ROOT, 'tools', 'raw', 'grants'); os.makedirs(OUT, exist_ok=True)
UA = {'User-Agent': 'Mozilla/5.0 (compatible; shapechicago-watch/1.0)'}
progs = json.loads(subprocess.check_output(['git', 'show', 'origin/shape-v1:grants/data/programs.json'], cwd=ROOT))['programs']
path = os.path.join(OUT, 'watch.json')
W = json.load(open(path)) if os.path.exists(path) else {}
today = datetime.date.today().isoformat()
urls = {}
for p in progs:
    for u in [p['link']] + [s[1] for s in p.get('src', [])]: urls.setdefault(u, set()).add(p['id'])
for u, ids in sorted(urls.items()):
    e = W.get(u, {}); e['ids'] = sorted(ids)
    try:
        b = urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=60).read()
        if u.lower().endswith('.pdf'): h = hashlib.sha256(b).hexdigest()[:16]
        else:
            t = re.sub(r'<script.*?</script>|<style.*?</style>', ' ', b.decode('utf-8', 'replace'), flags=re.S | re.I)
            t = re.sub(r'<[^>]+>', ' ', t); t = re.sub(r'\b(19|20)\d\d-\d\d-\d\d\b|\s+', ' ', t)
            h = hashlib.sha256(t.encode()).hexdigest()[:16]
        if e.get('hash') and e['hash'] != h: e['changed'] = today
        e['hash'] = h; e['ok'] = today; e.pop('error', None)
    except Exception as x:
        e['error'] = f'{today} {type(x).__name__}'
    W[u] = e
json.dump(W, open(path, 'w'), indent=1, sort_keys=True)
ch = [u for u, e in W.items() if e.get('changed') == today]
print(len(W), 'pages,', len(ch), 'changed today,', sum(1 for e in W.values() if 'error' in e), 'errors')
for u in ch: print('CHANGED', u, W[u]['ids'])
