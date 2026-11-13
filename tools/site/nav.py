"""The site's header nav, defined once. Run `python3 tools/site/nav.py` after changing it: it rewrites the
<nav class="sc-nav"> in every page (with the right item marked as the current page), and tools/progress/build.py
imports nav_for() for the pages it writes. Phones get a single Menu button built from this same markup (shape/shape.js).

Top bar: Simulators ▾, Your address ▾, Progress ▾, Your ward, News, Learn (Kyle, Nov. 12, 2026).
"""
import os, re, sys

SIMS = [('/housing/', 'Housing'), ('/transit/', 'Transit'), ('/budget/', 'Budget'), ('/pensions/', 'Pensions'), ('/bears/', 'Bears stadium'),
        None, ('/plans/', 'Plans people made')]
# one address, three tools (they share the address through shape.js scSetAddr and show the same tab row)
ADDR = [('/lot/', 'Zoning and rules'), ('/grants/', 'Grants and help'), ('/deal/', 'Affordable deal check')]   # the same three names everywhere: menu, tabs, titles, footer
PROG = [('/progress/', 'Overview'), ('/progress/homes/', 'Homes'), ('/progress/zoning/', 'Zoning'), ('/progress/affordable/', 'Affordable'),
        ('/progress/rents/', 'Rents and prices'), ('/progress/transit/', 'Transit'), ('/progress/streets/', 'Streets'),
        ('/progress/capital/', 'City money'), ('/progress/projects/', 'Big projects'),
        None, ('/progress/springfield/', 'In Springfield'), ('/progress/decisions/', 'Decisions coming up')]
TOP = [('/wards/', 'Your ward'), ('/news/', 'News'), ('/learn/', 'Learn')]

# pages that sit under another item: they light up that item
ALIAS = {'/community/': '/plans/', '/tracker/': '/progress/homes/', '/progress/room/': '/progress/zoning/',
         '/history/': '/learn/'}
CHEV = '<svg viewBox="0 0 10 6" aria-hidden="true"><path d="M1 1l4 4 4-4"/></svg>'

def current(path):
    path = ALIAS.get(path, path)
    if path.startswith('/progress/decisions/'): path = '/progress/decisions/'
    return path

def menu(title, items, cur, label=None):
    here = any(it and it[0] == cur for it in items)
    links, alt = '', False
    for it in items:
        if it is None: alt = True; continue
        href, name = it
        links += f'<a href="{href}"' + (' class="sc-simalt"' if alt else '') + (' aria-current="page"' if href == cur else '') + f'>{name}</a>'
        alt = False
    btn = (label if (here and label) else title)
    return (f'<div class="sc-sims"><button type="button" class="sc-simbtn" aria-haspopup="true" aria-expanded="false"' + (' aria-current="page"' if here else '')
            + f' data-menu="{title}">{btn}{CHEV}</button><div class="sc-simmenu" role="menu" hidden><span class="sc-simhd">{title}</span>{links}</div></div>')

def nav_for(path):
    cur = current(path)
    sim_name = next((n for it in SIMS if it for h, n in [it] if h == cur), None)
    top = ''.join(f'<a href="{h}"' + (' aria-current="page"' if h == cur else '') + f'>{n}</a>' for h, n in TOP)
    return ('<nav class="sc-nav" aria-label="Shape Chicago tools">' + menu('Simulators', SIMS, cur, sim_name) + menu('Your address', ADDR, cur) + menu('Progress', PROG, cur)
            + top + '</nav>')

NAV_RE = re.compile(r'<nav class="sc-nav" aria-label="Shape Chicago tools">.*?</nav>', re.S)

def rewrite(root):
    n = 0
    for dp, dn, fn in os.walk(root):
        dn[:] = [d for d in dn if d not in ('node_modules', 'tools', '.git', 'progress')]   # progress pages come from build.py
        for f in fn:
            if not f.endswith('.html'): continue
            p = os.path.join(dp, f); s = open(p, encoding='utf-8').read()
            if not NAV_RE.search(s): continue
            rel = '/' + os.path.relpath(dp, root).replace(os.sep, '/') + '/'
            rel = '/' if rel == '/./' else rel
            t = NAV_RE.sub(lambda m: nav_for(rel), s, count=1)
            if t != s: open(p, 'w', encoding='utf-8').write(t); n += 1
    return n

if __name__ == '__main__':
    root = os.path.join(os.path.dirname(__file__), '..', '..')
    print(rewrite(os.path.abspath(root)), 'pages updated')
