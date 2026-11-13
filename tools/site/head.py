"""Puts the same icon and manifest links in every page's <head> (idempotent). Run after adding a page:
  python3 tools/site/head.py
tools/progress/build.py writes the same links into the pages it makes (ICONS there)."""
import os, re
ICONS = ('<link rel="icon" href="/shape/icon.svg" type="image/svg+xml"><link rel="icon" href="/favicon.ico" sizes="32x32">'
         '<link rel="apple-touch-icon" href="/shape/icon-180.png"><link rel="manifest" href="/site.webmanifest">')
def run(root):
    n = 0
    for dp, dn, fn in os.walk(root):
        dn[:] = [d for d in dn if d not in ('node_modules', 'tools', '.git', 'progress', 'embed')]
        for f in fn:
            if not f.endswith('.html'): continue
            p = os.path.join(dp, f); s = open(p, encoding='utf-8').read()
            if 'rel="manifest"' in s or '<head>' not in s: continue
            s = re.sub(r'(<meta charset="utf-8">)', r'\1\n' + ICONS, s, count=1)
            open(p, 'w', encoding='utf-8').write(s); n += 1
    return n
if __name__ == '__main__':
    print(run(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))), 'pages')
