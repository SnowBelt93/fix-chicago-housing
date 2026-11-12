"""Federal, county and regional sources for Progress and the reports (step "sources" of tools/record/fetch.py; runs in
GitHub Actions). Each file is downloaded, then cut down to its Chicago rows and written to tools/raw/record/src/ as a
small CSV, so the raw downloads never go in git. peek.json keeps each file's sheet names and first rows, so the formats
can be read here without the downloads. Nothing with a person's name is kept: the tax-credit list drops its contact
and company columns.

  hud_place.csv       HUD Picture of Subsidized Households, the Chicago row of every year's place file (2012 on)
  hud_tract_<y>.csv   the same by census tract, Cook County
  safmr.csv           HUD Small Area Fair Market Rents by ZIP code, Chicago metro area ZIPs starting 606-608, each year
  fhfa_zip5.csv       FHFA yearly house price index by ZIP code, 606-608
  bps_places.csv      Census Building Permits Survey, homes permitted a year (2010 on): every place in the Chicago metro
                      area, plus the big cities Chicago gets compared with
  cook_rates_*.csv.gz Cook County Clerk tax rates by tax code and by agency
  lihtc_chicago.csv   HUD's tax-credit housing list, Chicago projects (address, homes, year opened; no contacts)
  rtams_*.csv.gz      RTA ridership tables
"""
import urllib.request, json, os, re, io, csv, gzip, zipfile, sys, time, datetime
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

def sheets(b, name):
    """Every sheet of an .xlsx or .xls file as (sheet name, row iterator of string lists)."""
    if name.lower().endswith('.xls'):
        import xlrd
        wb = xlrd.open_workbook(file_contents=b)
        for sh in wb.sheets(): yield sh.name, ([cell(c) for c in sh.row_values(r)] for r in range(sh.nrows))
    else:
        import openpyxl
        wb = openpyxl.load_workbook(io.BytesIO(b), read_only=True, data_only=True)
        for ws in wb.worksheets: yield ws.title, ([cell(c) for c in row] for row in ws.iter_rows(values_only=True))

def peek_rows(key, sheet, rows, n=6):
    PEEK.setdefault(key, {})[sheet] = [[c[:48] for c in r[:70]] for r in rows[:n]]

def cut(key, url, keep, head=3, need=None, peek_only=False):
    """Download a spreadsheet; return the header rows plus every row where some cell matches `keep` (and, if given, some
    cell matches `need`), per sheet."""
    b = get(url)
    if not b: PEEK[key] = {'missing': url}; return []
    out = []
    try:
        for sname, rows in sheets(b, url):
            first, hit, n = [], [], 0
            for r in rows:
                n += 1
                if len(first) < max(head, 6): first.append(r)
                if n <= head: continue
                if peek_only:
                    if n > 6: break
                    continue
                if any(keep.search(c) for c in r) and (need is None or any(need.search(c) for c in r)): hit.append(r)
            peek_rows(key, sname, first); PEEK[key][sname + ' #rows'] = n; PEEK[key][sname + ' #kept'] = len(hit)
            out.append((sname, first[:head], hit))
    except Exception as e: PEEK[key] = {'error': str(e)[:300]}
    print('cut', key, [(s, len(h)) for s, _, h in out], flush=True)
    return out

def save(name, rows, gz=False):
    p = os.path.join(OUT, name)
    f = gzip.open(p, 'wt', newline='') if gz else open(p, 'w', newline='')
    csv.writer(f).writerows(rows); f.close()
    print('saved', name, len(rows), flush=True)

HUD = 'https://www.huduser.gov/portal/datasets/pictures/files/'
ZIPS = re.compile(r'^60[6-8]\d\d$')

# 1) HUD Picture of Subsidized Households: Chicago by year, and Cook County tracts for the newest year and 2019
rows = []
for y in range(2012, 2026):
    f = f'PLACE_{y}_2020census.xlsx' if y >= 2023 else f'PLACE_{y}.xlsx'
    for sname, head, hit in cut(f'hud_place_{y}', HUD + f, re.compile(r'^Chicago( city.*)?$|^1714000$|^XX17XX14000$'), head=1):
        if not rows and head: rows.append(['year', 'sheet'] + head[0])
        elif head and rows and head[0] != rows[0][2:]: rows.append([y, 'HEADER'] + head[0])   # columns changed that year
        rows += [[y, sname] + r for r in hit]
save('hud_place.csv', rows)
for y, f in ((2025, 'TRACT_AK_MN_2025_2020census.xlsx'), (2019, 'TRACT_AK_MN_2019.xlsx')):
    rows = []
    for sname, head, hit in cut(f'hud_tract_{y}', HUD + f, re.compile(r'^(XX)?17(XX)?031'), head=1):
        rows += head + hit
    save(f'hud_tract_{y}.csv', rows)
cut('hud_project_2025', HUD + 'PROJECT_2025_2020census.xlsx', re.compile('^$'), peek_only=True)

# 2) HUD Small Area Fair Market Rents, Chicago ZIPs
rows = []
for y, f in ((2019, 'fmr2019/fy2019_safmrs_rev.xlsx'), (2020, 'fmr2020/fy2020_safmrs_rev.xlsx'), (2021, 'fmr2021/fy2021_safmrs_revised.xlsx'),
             (2022, 'fmr2022/fy2022_safmrs_revised.xlsx'), (2023, 'fmr2023/fy2023_safmrs_revised.xlsx'), (2024, 'fmr2024/fy2024_safmrs_revised.xlsx'),
             (2025, 'fmr2025/fy2025_safmrs.xlsx'), (2026, 'fmr2026/fy2026_safmrs_revised.xlsx'), (2027, 'fmr2027/FY27_safmrs.xlsx')):
    for sname, head, hit in cut(f'safmr_{y}', 'https://www.huduser.gov/portal/datasets/fmr/' + f, ZIPS, head=1, need=re.compile('Chicago')):
        rows.append([y, 'HEADER'] + (head[0] if head else [])); rows += [[y, sname] + r for r in hit]
save('safmr.csv', rows)

# 3) FHFA house price index by ZIP code
rows = []
for sname, head, hit in cut('fhfa_zip5', 'https://www.fhfa.gov/hpi/download/annual/hpi_at_zip5.xlsx', ZIPS, head=8):
    rows += head + hit
save('fhfa_zip5.csv', rows)

# 4) Census Building Permits Survey: the Chicago metro area's places and the big cities, 2010 on
PEERS = {'36': ['New York', 'Bronx', 'Brooklyn', 'Manhattan', 'Queens', 'Staten Island'], '06': ['Los Angeles', 'San Diego', 'San Francisco', 'San Jose'],
         '48': ['Houston', 'San Antonio', 'Dallas', 'Austin', 'Fort Worth'], '04': ['Phoenix'], '42': ['Philadelphia'], '12': ['Jacksonville', 'Miami'],
         '39': ['Columbus'], '18': ['Indianapolis'], '27': ['Minneapolis', 'St. Paul', 'Saint Paul'], '53': ['Seattle'], '08': ['Denver'], '25': ['Boston'],
         '11': ['Washington'], '47': ['Nashville'], '26': ['Detroit'], '55': ['Milwaukee'], '13': ['Atlanta'], '37': ['Charlotte', 'Raleigh'], '41': ['Portland']}
rows = [['year', 'state', 'county', 'cbsa', 'pop', 'months', 'name', 'b1', 'u1', 'b2', 'u2', 'b34', 'u34', 'b5', 'u5']]
for y in range(2010, datetime.date.today().year):
    for reg, pre in (('Midwest', 'mw'), ('Northeast', 'ne'), ('South', 'so'), ('West', 'we')):
        b = get(f'https://www2.census.gov/econ/bps/Place/{reg}%20Region/{pre}{y}a.txt', tries=2)
        if not b: continue
        lines = b.decode('latin-1').splitlines()
        if y == 2025 and pre == 'mw': PEEK['bps_header'] = lines[:3]
        for r in csv.reader(lines[2:]):
            if len(r) < 29: continue
            st, name, cbsa = r[1].strip().zfill(2), r[16].strip(), r[9].strip()
            if cbsa == '16980' or any(name == p or name.startswith(p + ' ') for p in PEERS.get(st, [])):
                v = [x.strip() for x in r[17:29]]
                rows.append([y, st, r[3].strip(), cbsa, r[7].strip(), r[15].strip(), name, v[0], v[1], v[3], v[4], v[6], v[7], v[9], v[10]])
save('bps_places.csv', rows)

# 5) Cook County Clerk tax rates, tax year 2025 (and 2023 for comparison)
for key, u in (('cook_rates_taxcode_2025', 'https://www.cookcountyclerkil.gov/sites/default/files/2026-09/2025-tax-code-agency-rates.xlsx'),
               ('cook_rates_agency_2025', 'https://www.cookcountyclerkil.gov/sites/default/files/2026-08/2025-agency-rate-report-tables-updated.xlsx'),
               ('cook_rates_agency_2023', 'https://www.cookcountyclerkil.gov/sites/default/files/2024-06/2023%20Agency%20Rate%20Report.xlsx')):
    rows = []
    for sname, head, hit in cut(key, u, re.compile('.'), head=0):
        rows += [[sname] + r for r in hit]
    if rows: save(key + '.csv.gz', rows[:400000], gz=True)

# 6) HUD's tax-credit (LIHTC) list: Chicago projects, without the contact and company columns
b = get('https://www.huduser.gov/lihtc/lihtcpub.zip', timeout=600)
if b:
    try:
        z = zipfile.ZipFile(io.BytesIO(b)); PEEK['lihtc'] = {'files': [(i.filename, i.file_size) for i in z.infolist()]}
        for i in z.infolist():
            if i.filename.lower().endswith('.csv'):
                rd = csv.DictReader(io.TextIOWrapper(z.open(i), encoding='latin-1'))
                keep = [c for c in rd.fieldnames if not re.match(r'(?i)^(contact|company|co_|trgt_|mgmt|owner)', c)]
                PEEK['lihtc']['columns'] = rd.fieldnames
                rows = [keep] + [[r[c] for c in keep] for r in rd if (r.get('PROJ_CTY') or '').strip().upper() == 'CHICAGO' and (r.get('PROJ_ST') or '').strip().upper() == 'IL']
                save('lihtc_chicago.csv', rows)
    except Exception as e: PEEK['lihtc'] = {'error': str(e)[:300]}

# 7) RTA ridership tables
for key, u in (('rtams_system_annual', 'https://rtams.org/sites/default/files/documents/2026-03/Annual_System_Ridership_Figures_0.csv'),
               ('rtams_cta_rail_station', 'https://www.rtams.org/sites/default/files/documents/2026-08/CTA_Average_Rail_Station_Ridership_1999_2026.csv')):
    b = get(u)
    if b:
        PEEK[key] = b.decode('latin-1').splitlines()[:5]
        gzip.open(os.path.join(OUT, key + '.csv.gz'), 'wb').write(b); print('saved', key, len(b), flush=True)
rows = []
for sname, head, hit in cut('rtams_cta_bus', 'https://www.rtams.org/sites/default/files/documents/2026-08/CTA_Average_Bus_Ridership_1999_2026.xlsx', re.compile('.'), head=0):
    rows += [[sname] + r for r in hit]
if rows: save('rtams_cta_bus.csv.gz', rows, gz=True)

json.dump(PEEK, open(os.path.join(OUT, 'peek.json'), 'w'), indent=1)
print('sources done', len(PEEK), flush=True)
