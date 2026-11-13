"""Builds the translation files shape.js swaps in when a reader picks a language: shape/es.json, shape/zh.json, shape/pl.json.
  tools/site/es/*.py     Spanish tables: T (exact text -> Spanish), H (inner HTML), R / HR (patterns), W (month/day words)
  tools/site/zhpl/*.py   Chinese (Simplified) and Polish together: T = {English: (Chinese, Polish)}, H the same,
                         R / HR = [[pattern, Chinese replacement, Polish replacement]], W = {word: (Chinese, Polish)}
Keys are the English exactly as it appears on the page, whitespace collapsed. Run: python3 tools/site/es_build.py"""
import json, os, glob, importlib.util, re, sys
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, 'tools', 'site'))
norm = lambda s: re.sub(r'\s+', ' ', s).strip()
def load(d):
    sys.path.insert(0, d)
    for k in list(sys.modules):
        if k in ('core', 'home', 'wards', 'progress', 'about', 'grants', 'misc'): del sys.modules[k]
    mods = []
    for p in sorted(glob.glob(os.path.join(d, '*.py'))):
        spec = importlib.util.spec_from_file_location(os.path.basename(p)[:-3], p); m = importlib.util.module_from_spec(spec); sys.modules[spec.name] = m; spec.loader.exec_module(m); mods.append(m)
    sys.path.remove(d); return mods
def write(lang, T, H, R, HR, W):
    for a, b in R + HR: re.compile(a)
    out = {'t': {norm(k): v for k, v in T.items()}, 'h': {norm(k): v for k, v in H.items()}, 'r': R, 'hr': HR, 'w': W}
    json.dump(out, open(os.path.join(ROOT, 'shape', lang + '.json'), 'w'), ensure_ascii=False, separators=(',', ':'))
    print(lang + '.json:', len(out['t']), 'texts,', len(out['h']), 'html,', len(R) + len(HR), 'patterns')
# Spanish
T, H, R, HR, W = {}, {}, [], [], {}
for m in load(os.path.join(ROOT, 'tools', 'site', 'es')):
    T.update(getattr(m, 'T', {})); H.update(getattr(m, 'H', {})); R += getattr(m, 'R', []); HR += getattr(m, 'HR', []); W.update(getattr(m, 'W', {}))
# tools/site/all/*.py: all three languages in one table per page: T = {English: (Spanish, Chinese, Polish)}, H the same,
# R / HR = [[pattern, Spanish, Chinese, Polish]]. Files are named x_<page>.py so their module names never clash.
ALL = load(os.path.join(ROOT, 'tools', 'site', 'all')) if os.path.isdir(os.path.join(ROOT, 'tools', 'site', 'all')) else []
for m in ALL:
    T.update({k: v[0] for k, v in getattr(m, 'T', {}).items()}); H.update({k: v[0] for k, v in getattr(m, 'H', {}).items()})
    R += [[a, x[0]] for a, *x in getattr(m, 'R', [])]; HR += [[a, x[0]] for a, *x in getattr(m, 'HR', [])]
write('es', T, H, R, HR, W)
# Chinese and Polish
mods = load(os.path.join(ROOT, 'tools', 'site', 'zhpl'))
if mods:
    for i, lang in enumerate(('zh', 'pl')):
        T, H, R, HR, W = {}, {}, [], [], {}
        for m in ALL:
            T.update({k: v[i + 1] for k, v in getattr(m, 'T', {}).items()}); H.update({k: v[i + 1] for k, v in getattr(m, 'H', {}).items()})
            R += [[a, x[i + 1]] for a, *x in getattr(m, 'R', [])]; HR += [[a, x[i + 1]] for a, *x in getattr(m, 'HR', [])]
        for m in mods:
            T.update({k: v[i] for k, v in getattr(m, 'T', {}).items()}); H.update({k: v[i] for k, v in getattr(m, 'H', {}).items()})
            R += [[a, x[i]] for a, *x in getattr(m, 'R', [])]; HR += [[a, x[i]] for a, *x in getattr(m, 'HR', [])]; W.update({k: v[i] for k, v in getattr(m, 'W', {}).items()})
        write(lang, T, H, R, HR, W)
