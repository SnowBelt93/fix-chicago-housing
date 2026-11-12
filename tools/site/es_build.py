"""Builds shape/es.json (the Spanish text shape.js swaps in when a reader picks Español) from the tables in tools/site/es/*.py.
Each table file defines T (exact text -> Spanish), H (inner HTML -> Spanish HTML), HR and R (regex patterns, applied in order).
Keys are the English exactly as it appears on the page, whitespace collapsed. Run: python3 tools/site/es_build.py"""
import json, os, glob, importlib.util, re
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import sys; sys.path.insert(0, os.path.join(ROOT, 'tools', 'site', 'es'))
T, H, R, HR, W = {}, {}, [], [], {}
for p in sorted(glob.glob(os.path.join(ROOT, 'tools', 'site', 'es', '*.py'))):
    spec = importlib.util.spec_from_file_location(os.path.basename(p)[:-3], p); m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    T.update(getattr(m, 'T', {})); H.update(getattr(m, 'H', {})); R += getattr(m, 'R', []); HR += getattr(m, 'HR', []); W.update(getattr(m, 'W', {}))
for a, b in R + HR: re.compile(a)
norm = lambda s: re.sub(r'\s+', ' ', s).strip()
out = {'t': {norm(k): v for k, v in T.items()}, 'h': {norm(k): v for k, v in H.items()}, 'r': R, 'hr': HR, 'w': W}
json.dump(out, open(os.path.join(ROOT, 'shape', 'es.json'), 'w'), ensure_ascii=False, separators=(',', ':'))
print('es.json:', len(out['t']), 'texts,', len(out['h']), 'html,', len(R) + len(HR), 'patterns')
