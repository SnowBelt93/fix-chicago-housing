"""Pension data for the Shape Chicago pensions tool (runs in GitHub Actions; the cloud workspace can't reach these hosts).
  ppd.csv.gz        Public Plans Data (Center for Retirement Research at Boston College): every plan-year, all variables,
                    kept only for Chicago's four city funds (MEABF, LABF, PABF, FABF)
  av/<name>.txt     actuarial valuation reports found on publicplansdata.org, as text (pdftotext)"""
import urllib.request, re, os, gzip, io, csv, time, subprocess, zipfile
OUT = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'raw', 'pensions'); os.makedirs(os.path.join(OUT, 'av'), exist_ok=True)
def get(url, tries=3):
    for t in range(tries):
        try: return urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 shapechicago'}), timeout=300).read()
        except Exception as e: print('retry', t, url, e, flush=True); time.sleep(6 * (t + 1))
    return None
page = get('https://publicplansdata.org/public-plans-database/download-full-data-set/') or b''
links = sorted(set(re.findall(rb'href="([^"]+\.(?:csv|zip|xlsx)[^"]*)"', page)))
print('links', links[:20], flush=True)
for l in links:
    u = l.decode()
    if not u.startswith('http'): u = 'https://publicplansdata.org' + u
    d = get(u)
    if not d: continue
    if u.endswith('.zip'):
        z = zipfile.ZipFile(io.BytesIO(d)); name = [n for n in z.namelist() if n.lower().endswith('.csv')]
        if not name: continue
        d = z.read(name[0])
    if not u.endswith(('.csv', '.zip')) and not d[:200].count(b','): continue
    text = d.decode('latin-1').splitlines()
    head = text[0].lower()
    if 'planname' not in head.replace('_', '') and 'plan_name' not in head and 'ppd_id' not in head: continue
    keep = [text[0]] + [r for r in text[1:] if re.search(r'chicago', r, re.I)]
    gzip.open(os.path.join(OUT, 'ppd.csv.gz'), 'wt').write('\n'.join(keep)); print('ppd rows', len(keep), u, flush=True); break
# valuation reports: publicplansdata keeps PDFs as IL_CHICAGOCITY-<FUND>_AV_<year>_<ppd id>.pdf
for fund, pid in [('PABF', 146), ('FABF', 206), ('MEABF', 145), ('LABF', 215), ('LABF', 147), ('MEABF', 144)]:
    for y in (2025, 2024, 2023):
        for suffix in ('', '_GASB67-68', '_GASB67'):
            u = f'https://publicplansdata.org/reports/IL_CHICAGOCITY-{fund}_AV_{y}_{pid}{suffix}.pdf'
            t = os.path.join(OUT, 'av', f'{fund}_{y}{suffix}.txt')
            if os.path.exists(t): continue
            try: d = urllib.request.urlopen(urllib.request.Request(u, headers={'User-Agent': 'Mozilla/5.0'}), timeout=120).read()
            except Exception: continue
            open('/tmp/a.pdf', 'wb').write(d); subprocess.run(['pdftotext', '-layout', '/tmp/a.pdf', t]); print('av', fund, y, suffix, os.path.getsize(t), flush=True)
