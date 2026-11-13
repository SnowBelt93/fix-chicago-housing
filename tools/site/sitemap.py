"""Writes /robots.txt and /sitemap.xml for every public page. Run after adding a page: python3 tools/site/sitemap.py
Launch to-do: set SITE to the new domain (tools/progress/build.py has its own SITE for embeds)."""
import os, datetime, subprocess
SITE = 'https://shape-chicago.hd9bt6x5mn.workers.dev'
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
SKIP = {'/feedback/', '/advertise/', '/progress/preview/', '/progress/lost/', '/progress/room/', '/street/'}
pages = []
for dp, dn, fn in os.walk(ROOT):
    dn[:] = sorted(d for d in dn if d not in ('node_modules', 'tools', '.git', 'embed', 'worker', 'shape', 'b'))
    if 'index.html' in fn:
        rel = '/' + os.path.relpath(dp, ROOT).replace(os.sep, '/') + '/'
        rel = '/' if rel == '/./' else rel
        if rel in SKIP: continue
        try: d = subprocess.run(['git', 'log', '-1', '--format=%cs', '--', os.path.join(dp, 'index.html')], cwd=ROOT, capture_output=True, text=True).stdout.strip()
        except Exception: d = ''
        pages.append((rel, d or datetime.date.today().isoformat()))
pages.sort()
xml = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
xml += [f'<url><loc>{SITE}{p}</loc><lastmod>{d}</lastmod></url>' for p, d in pages] + ['</urlset>']
open(os.path.join(ROOT, 'sitemap.xml'), 'w').write('\n'.join(xml) + '\n')
open(os.path.join(ROOT, 'robots.txt'), 'w').write(f'User-agent: *\nAllow: /\nDisallow: /api/\nDisallow: /feedback/\nDisallow: /embed/\n\nSitemap: {SITE}/sitemap.xml\n')
print(len(pages), 'pages in the sitemap')
