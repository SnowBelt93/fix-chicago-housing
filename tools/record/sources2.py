"""Second pass of sources for Progress and the reports (step "sources2" of tools/record/fetch.py; runs in GitHub Actions).
Like sources.py: download, keep only what is about Chicago, write small files to tools/raw/record/src/, and note each
file's layout in peek2.json. Nothing with a person's name is kept.
  ntd_monthly_chicago.csv.gz  federal monthly transit ridership (National Transit Database), agencies in the Chicago area
  rtams_pace_monthly.csv.gz   Pace ridership by route and month (RTA)
  rtams_metra_line.csv.gz     Metra ridership by line and month (RTA)
  lihtc_chicago.csv           HUD's tax-credit housing list, Chicago projects (no contact or company columns)
peek2.json also lists what is inside Pace's schedule feed and the first lines of the city's aldermanic menu report."""
import urllib.request, urllib.parse, json, os, re, io, csv, gzip, zipfile, subprocess, time
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(os.path.dirname(HERE), 'raw', 'record', 'src'); os.makedirs(OUT, exist_ok=True)
UA = {'User-Agent': 'Mozilla/5.0 (compatible; shapechicago-data/1.0)'}
PEEK = {}
def get(url, tries=3, timeout=300):
    last = None
    for t in range(tries):
        try: return urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout).read()
        except Exception as e: last = e; print('retry', t, url, e, flush=True); time.sleep(8 * (t + 1))
    print('MISSING', url, last, flush=True); return None
def cell(v):
    if v is None: return ''
    if isinstance(v, float) and v == int(v): return str(int(v))
    return str(v).strip()
def xlsx_rows(b):
    import openpyxl
    wb = openpyxl.load_workbook(io.BytesIO(b), read_only=True, data_only=True)
    for ws in wb.worksheets: yield ws.title, ([cell(c) for c in row] for row in ws.iter_rows(values_only=True))
def save(name, rows):
    with gzip.open(os.path.join(OUT, name), 'wt', newline='') if name.endswith('.gz') else open(os.path.join(OUT, name), 'w', newline='') as f: csv.writer(f).writerows(rows)
    print('saved', name, len(rows), flush=True)

# 1) Federal monthly ridership. The table's column names are read first, then only the Chicago urban area is asked for.
for key, vid in (('ntd_monthly', '8bui-9xvu'), ('ntd_modal', '5ti2-5uiv')):
    try:
        cols = json.loads(get(f'https://data.transportation.gov/api/views/{vid}/columns.json') or b'[]')
        names = [c.get('fieldName') for c in cols]; PEEK[key] = {'columns': names}
        uza = next((n for n in names if n and re.search(r'uza.*name|urbanized.*name|uza_name', n)), None) or next((n for n in names if n and 'agency' in n and 'name' not in n and False), None)
        base = f'https://data.transportation.gov/resource/{vid}.csv?'
        q = {'$limit': 200000}
        if uza: q['$where'] = f"upper({uza}) like '%CHICAGO%'"
        else: q['$q'] = 'Chicago'
        b = get(base + urllib.parse.urlencode(q), timeout=900)
        if b:
            lines = b.decode('utf-8', 'replace').splitlines(); PEEK[key]['rows'] = len(lines) - 1; PEEK[key]['first'] = lines[:4]; PEEK[key]['filter'] = q.get('$where') or q.get('$q')
            if key == 'ntd_monthly' or len(b) < 30_000_000: gzip.open(os.path.join(OUT, key + '_chicago.csv.gz'), 'wb').write(b); print('saved', key, len(lines), flush=True)
    except Exception as e: PEEK[key] = {'error': str(e)[:300]}

# 2) RTA tables: Pace by route and month, Metra by line and month
b = get('https://rtams.org/sites/default/files/documents/2026-06/Pace_Monthly_Ridership_2003_2026.xlsx')
if b:
    try:
        rows = []
        for sname, rws in xlsx_rows(b):
            n = 0
            for r in rws:
                n += 1; rows.append([sname] + r)
                if n <= 4: PEEK.setdefault('rtams_pace', {}).setdefault(sname, []).append([c[:30] for c in r[:40]])
            PEEK['rtams_pace'][sname + ' #rows'] = n
        save('rtams_pace_monthly.csv.gz', rows)
    except Exception as e: PEEK['rtams_pace'] = {'error': str(e)[:300]}
b = get('https://rtams.org/sites/default/files/documents/2026-08/Metra_Monthly_Ridership_by_Line_2003_2026.csv')
if b:
    PEEK['rtams_metra_line'] = b.decode('latin-1').splitlines()[:5]
    gzip.open(os.path.join(OUT, 'rtams_metra_line.csv.gz'), 'wb').write(b); print('saved metra line', len(b), flush=True)

# 3) Pace's schedule feed: what is in it (the feed itself is used by the transit tool's own download, not kept here)
b = get('https://pacebus.com/sites/default/files/2026-10/GTFS.zip', timeout=600)
if b:
    try:
        z = zipfile.ZipFile(io.BytesIO(b)); PEEK['pace_gtfs'] = {'bytes': len(b), 'files': {}}
        for i in z.infolist():
            raw = z.read(i).decode('utf-8', 'replace').splitlines()
            PEEK['pace_gtfs']['files'][i.filename] = {'lines': len(raw), 'head': raw[:3]}
    except Exception as e: PEEK['pace_gtfs'] = {'error': str(e)[:300]}

# 4) HUD's tax-credit list: Chicago projects only, and never the contact or company columns
b = get('https://www.huduser.gov/lihtc/lihtcpub.zip', timeout=900)
if b:
    try:
        z = zipfile.ZipFile(io.BytesIO(b)); x = z.read('LIHTCPUB.xlsx')
        for sname, rws in xlsx_rows(x):
            hdr = None; keep = []; out = []
            for r in rws:
                if hdr is None:
                    hdr = [h.upper() for h in r]; keep = [i for i, h in enumerate(hdr) if h and not re.match(r'(CONTACT|COMPANY|CO_|MGMT|OWNER)', h)]
                    PEEK['lihtc'] = {'sheet': sname, 'columns': hdr, 'dropped': [h for h in hdr if h and re.match(r'(CONTACT|COMPANY|CO_|MGMT|OWNER)', h)]}
                    ci, si = hdr.index('PROJ_CTY'), hdr.index('PROJ_ST'); out.append([hdr[i] for i in keep]); continue
                if len(r) > max(ci, si) and r[ci].strip().upper() == 'CHICAGO' and r[si].strip().upper() == 'IL': out.append([r[i] if i < len(r) else '' for i in keep])
            save('lihtc_chicago.csv', out); PEEK['lihtc']['rows'] = len(out) - 1
            break
    except Exception as e: PEEK['lihtc'] = {'error': str(e)[:300]}

# 5) The city's aldermanic menu report: how the newest one is laid out (first lines of its text)
for key, u in (('menu_2026_q3', 'https://www.chicago.gov/content/dam/city/depts/obm/2027_Operations/CAPITAL/Aldermanic_Menu/Q3_2026_Aldermanic_Menu_Report.pdf'),
               ('cip_2025_2029', 'https://www.chicago.gov/content/dam/city/depts/obm/supp_info/CIP/City%20of%20Chicago%202025-2029%20CIP.pdf')):
    b = get(u, timeout=600)
    if not b: PEEK[key] = {'missing': u}; continue
    try:
        open('/tmp/x.pdf', 'wb').write(b); subprocess.run(['pdftotext', '-layout', '/tmp/x.pdf', '/tmp/x.txt'], check=True)
        t = open('/tmp/x.txt', errors='replace').read(); pages = t.split('\f')
        PEEK[key] = {'bytes': len(b), 'pages': len(pages), 'chars': len(t), 'page1': pages[0].splitlines()[:60], 'page3': (pages[2].splitlines()[:70] if len(pages) > 2 else []), 'page10': (pages[9].splitlines()[:70] if len(pages) > 9 else [])}
    except Exception as e: PEEK[key] = {'error': str(e)[:300]}

json.dump(PEEK, open(os.path.join(OUT, 'peek2.json'), 'w'), indent=1)
print('sources2 done', list(PEEK), flush=True)
