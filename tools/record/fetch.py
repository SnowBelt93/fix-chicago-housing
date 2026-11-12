"""Data for the Shape Chicago "record" page (runs in GitHub Actions; the cloud workspace can't reach these hosts).
Steps (commit message "[steps: a b]" picks some; default all):
  catalog  every dataset on the Chicago and Cook County data portals whose name matches a topic keyword, with columns,
           row counts and update dates -> tools/raw/record/catalog.json
  probe    snapshots of transit agency performance pages and other public data pages, plus every CSV/XLSX/PDF link
           found on them -> tools/raw/record/probe/<name>.html, probe.json
  catalog2 a few searches of the federal and Illinois data portals -> tools/raw/record/catalog_other.json
  get      downloads the datasets listed in tools/record/wanted.json ({"id": "...", "domain": "...", "where": "..."})
           -> tools/raw/record/<id>.csv.gz
  files    downloads the URLs listed in tools/record/files.json -> tools/raw/record/files/<name>
  sources  tools/record/sources.py: federal, county and RTA files cut down to their Chicago rows -> tools/raw/record/src/
  sources2 tools/record/sources2.py: federal monthly ridership, Pace and Metra by month, the tax-credit list (run by name)
"""
import urllib.request, urllib.parse, json, os, re, time, gzip, sys, subprocess
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(os.path.dirname(HERE), 'raw', 'record'); os.makedirs(OUT, exist_ok=True)
STEPS = set(sys.argv[1:]) or {'catalog', 'catalog2', 'probe', 'get', 'files', 'sources'}
UA = {'User-Agent': 'Mozilla/5.0 (compatible; shapechicago-data/1.0)'}
def get(url, tries=4, timeout=300):
    last = None
    for t in range(tries):
        try: return urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout).read()
        except Exception as e: last = e; print('retry', t, url, e, flush=True); time.sleep((45 if '503' in str(e) else 6) * (t + 1))
    raise RuntimeError(f'{url}: {last}')

TOPICS = ['housing', 'affordable', 'dwelling', 'additional dwelling unit', 'vacant', 'abandoned', 'demolition', 'building permits',
          'certificate of occupancy', 'zoning', 'building violations', 'inspections', 'rental', 'eviction', 'homeless',
          'cta', 'ridership', 'bus', 'train', 'divvy', 'bike', 'traffic crashes', 'speed camera', 'red light', 'traffic',
          '311', 'potholes', 'street lights', 'tif', 'budget', 'employees', 'salaries', 'payments', 'contracts', 'revenue',
          'property tax', 'assessor', 'sales', 'land', 'population', 'census', 'parking', 'streets', 'sidewalk', 'trees']
if 'catalog' in STEPS:
    found = {}
    for dom in ['data.cityofchicago.org', 'datacatalog.cookcountyil.gov']:
        for q in TOPICS:
            off = 0
            while off < 400:
                u = 'https://api.us.socrata.com/api/catalog/v1?' + urllib.parse.urlencode({'domains': dom, 'q': q, 'limit': 100, 'offset': off, 'only': 'dataset'})
                try: r = json.loads(get(u))
                except Exception as e: print('catalog fail', dom, q, e); break
                for x in r['results']:
                    res = x['resource']
                    found[res['id']] = {'id': res['id'], 'domain': dom, 'name': res['name'], 'desc': (res.get('description') or '')[:400],
                                        'updated': res.get('data_updated_at'), 'created': res.get('createdAt'),
                                        'columns': res.get('columns_field_name'), 'views': (res.get('page_views') or {}).get('page_views_total'),
                                        'category': (x.get('classification') or {}).get('domain_category')}
                off += 100
                if off >= r.get('resultSetSize', 0): break
        print(dom, sum(1 for d in found.values() if d['domain'] == dom), flush=True)
    # row counts for the city portal (cheap count(*) query)
    t0 = time.time()
    for d in found.values():
        if time.time() - t0 > 600 or d['domain'] != 'data.cityofchicago.org': d['rows'] = None; continue
        try:
            c = json.loads(get(f"https://{d['domain']}/resource/{d['id']}.json?$select=count(*)", tries=1, timeout=15))
            d['rows'] = int(list(c[0].values())[0])
        except Exception: d['rows'] = None
    json.dump(sorted(found.values(), key=lambda d: (d['domain'], d['name'])), open(os.path.join(OUT, 'catalog.json'), 'w'), indent=0)
    print('catalog', len(found), flush=True)

if 'catalog2' in STEPS:   # federal and state portals: only what we search for
    out = []
    for dom, q in [('data.transportation.gov', 'monthly ridership'), ('data.transportation.gov', 'National Transit Database monthly'), ('data.illinois.gov', 'traffic'), ('data.illinois.gov', 'pension'), ('data.illinois.gov', 'housing')]:
        try:
            r = json.loads(get('https://api.us.socrata.com/api/catalog/v1?' + urllib.parse.urlencode({'domains': dom, 'q': q, 'limit': 40, 'only': 'dataset'}), tries=2))
            for x in r['results']:
                res = x['resource']; out.append({'id': res['id'], 'domain': dom, 'q': q, 'name': res['name'], 'updated': res.get('data_updated_at'), 'columns': res.get('columns_field_name')})
        except Exception as e: print('catalog2 fail', dom, q, e)
    json.dump(out, open(os.path.join(OUT, 'catalog_other.json'), 'w'), indent=0); print('catalog2', len(out), flush=True)

PROBE = {
    'cta_performance': 'https://www.transitchicago.com/performance/',
    'cta_ridership': 'https://www.transitchicago.com/ridership/',
    'cta_ridership_reports': 'https://www.transitchicago.com/ridership/#reports',
    'cta_meeting_moment': 'https://www.transitchicago.com/meetingthemoment/',
    'metra_performance': 'https://metra.com/performance-measures',
    'metra_ridership': 'https://metra.com/ridership-reports',
    'pace_performance': 'https://www.pacebus.com/performance-measures',
    'rta_dashboards': 'https://www.rtachicago.org/dashboards',
    'rtams_ridership': 'https://rtams.org/ridership',
    'rtams_system': 'https://rtams.org/dataset/system-ridership',
    'rtams_cta': 'https://www.rtams.org/dataset/cta-ridership',
    'rtams_metra': 'https://rtams.org/ridership/metra',
    'nita_datahub': 'https://datahub.nita.illinois.gov/ridership',
    'nita_datahub_metra': 'https://datahub.nita.illinois.gov/ridership/metra',
    'nita_board': 'https://nita.illinois.gov/meetings',
    'zillow_data': 'https://www.zillow.com/research/data/',
    'apartmentlist_data': 'https://www.apartmentlist.com/research/category/data-rent-estimates',
    'census_bps': 'https://www2.census.gov/econ/bps/Place/Midwest%20Region/',
    'chicago_aro_reports': 'https://www.chicago.gov/city/en/depts/doh/provdrs/developers/svcs/aro.html',
    'chicago_doh_reports': 'https://www.chicago.gov/city/en/depts/doh/provdrs/housing_resources/svcs/quarterly-reports.html',
    'chicago_pit': 'https://www.chicago.gov/city/en/depts/fss/supp_info/homeless-point-in-time-count.html',
    'cook_evictions': 'https://www.cookcountyclerkofcourt.org/',
    'lcbh_evictions': 'https://eviction.lcbh.org/',
    'ihda': 'https://www.ihda.org/about-ihda/data/',
    'cmap_data': 'https://datahub.cmap.illinois.gov/',
    'fta_ntd_monthly': 'https://www.transit.dot.gov/ntd/data-product/monthly-module-raw-data-release',
    # Nov. 2026: sources Kyle approved for Progress, the lot and street tools and the reports (pages are probed for their file links first)
    'fta_ntd_adjusted': 'https://www.transit.dot.gov/ntd/data-product/monthly-module-adjusted-data-release',
    'hud_picture': 'https://www.huduser.gov/portal/datasets/assthsg.html',
    'hud_lihtc': 'https://www.huduser.gov/portal/datasets/lihtc/property.html',
    'hud_safmr': 'https://www.huduser.gov/portal/datasets/fmr/smallarea/index.html',
    'fhfa_hpi': 'https://www.fhfa.gov/data/hpi/datasets?tab=additional-data',
    'pace_schedules': 'https://www.pacebus.com/route-and-schedule-data',
    'pace_developers': 'https://www.pacebus.com/developers',
    'chicago_menu': 'https://www.chicago.gov/city/en/depts/obm/provdrs/cap_improve/svcs/aldermanic-menu-program.html',
    'chicago_cip': 'https://www.chicago.gov/city/en/depts/obm/provdrs/cap_improve.html',
    'cook_clerk_rates': 'https://www.cookcountyclerkil.gov/property-taxes/tax-extension-and-rates',
    'ilga_ftp': 'https://www.ilga.gov/ftp/legislation/',
    'census_bps_south': 'https://www2.census.gov/econ/bps/Place/South%20Region/',
    'census_bps_west': 'https://www2.census.gov/econ/bps/Place/West%20Region/',
    'census_bps_northeast': 'https://www2.census.gov/econ/bps/Place/Northeast%20Region/',
    # second pass: the pages the first pass could not find
    'pace_gtfs': 'https://pacebus.com/route-timetable-data-services',
    'pace_gtfs_mdb': 'https://mobilitydatabase.org/feeds/gtfs/mdb-2347',
    'ntd_monthly_catalog': 'https://catalog.data.gov/dataset/complete-monthly-ridership-with-adjustments-and-estimates',
    'ntd_modal_catalog': 'https://catalog.data.gov/dataset/monthly-modal-time-series',
    'chicago_capital_pubs': 'https://www.chicago.gov/city/en/depts/obm/provdrs/budget/svcs/CapitalPublications.html',
    'rtams_datasets': 'https://rtams.org/datasets',
    'rtams_pace': 'https://rtams.org/dataset/pace-ridership',
    'rtams_metra_ds': 'https://rtams.org/dataset/metra-ridership',
    'ilga_home': 'https://www.ilga.gov/Legislation',
    'idot_traffic': 'https://idot.illinois.gov/transportation-system/network-overview/highway-system/illinois-travel-statistics.html',
}
if 'probe' in STEPS:
    PD = os.path.join(OUT, 'probe'); os.makedirs(PD, exist_ok=True)
    rep = {}
    for k, u in PROBE.items():
        try:
            b = get(u, tries=2, timeout=60); html = b.decode('utf-8', 'replace')
            open(os.path.join(PD, k + '.html'), 'w').write(html[:3_000_000])
            links = sorted(set(urllib.parse.urljoin(u, h) for h in re.findall(r'href=["\']([^"\']+)["\']', html, re.I)
                               if re.search(r'\.(csv|xlsx?|pdf|zip|json|txt|xml)(\?|$)|download|export|powerbi|tableau|arcgis|/$', h, re.I)))
            rep[k] = {'url': u, 'ok': True, 'bytes': len(b), 'links': links[:400]}
        except Exception as e:
            rep[k] = {'url': u, 'ok': False, 'err': str(e)[:300]}
        print(k, rep[k].get('ok'), rep[k].get('bytes'), len(rep[k].get('links', [])), flush=True)
    json.dump(rep, open(os.path.join(OUT, 'probe.json'), 'w'), indent=1)

if 'get' in STEPS and os.path.exists(os.path.join(HERE, 'wanted.json')):
    for w in json.load(open(os.path.join(HERE, 'wanted.json'))):
        path = os.path.join(OUT, w.get('save_as', w['id']) + '.csv.gz')
        if os.path.exists(path) and not w.get('refresh'): continue
        q = {'accessType': 'DOWNLOAD'}
        url = f"https://{w.get('domain', 'data.cityofchicago.org')}/api/views/{w['id']}/rows.csv?accessType=DOWNLOAD"
        if w.get('where') or w.get('select') or w.get('group'):
            p = {'$limit': 5000000}
            if w.get('where'): p['$where'] = w['where']
            if w.get('select'): p['$select'] = w['select']
            if w.get('group'): p['$group'] = w['group']
            url = f"https://{w.get('domain', 'data.cityofchicago.org')}/resource/{w['id']}.csv?" + urllib.parse.urlencode(p)
        try:
            data = get(url, tries=6, timeout=1800)
            if w.get('drop'):  # remove columns we never keep (e.g. people's names)
                import csv, io
                rows = list(csv.DictReader(io.StringIO(data.decode('utf-8'))))
                keep = [k for k in (rows[0].keys() if rows else []) if k.lower() not in {d.lower() for d in w['drop']}]
                b = io.StringIO(); cw = csv.DictWriter(b, keep); cw.writeheader()
                for r in rows: cw.writerow({k: r[k] for k in keep})
                data = b.getvalue().encode('utf-8')
            gzip.open(path, 'wb').write(data); print('got', w['id'], w.get('name', ''), len(data), flush=True)
        except Exception as e: print('skip', w['id'], e, flush=True)

if 'files' in STEPS and os.path.exists(os.path.join(HERE, 'files.json')):
    FD = os.path.join(OUT, 'files'); os.makedirs(FD, exist_ok=True)
    for name, u in json.load(open(os.path.join(HERE, 'files.json'))).items():
        p = os.path.join(FD, name)
        if os.path.exists(p) or os.path.exists(p + '.txt'): continue
        try:
            b = get(u, tries=2, timeout=300)
            if name.endswith('.pdf'):
                open('/tmp/x.pdf', 'wb').write(b); subprocess.run(['pdftotext', '-layout', '/tmp/x.pdf', p + '.txt'], check=True)
            else: open(p, 'wb').write(b)
            print('file', name, len(b), flush=True)
        except Exception as e: print('file skip', name, e, flush=True)

if 'sources' in STEPS:
    import runpy; runpy.run_path(os.path.join(HERE, 'sources.py'), run_name='__main__')
if 'sources2' in STEPS:
    import runpy; runpy.run_path(os.path.join(HERE, 'sources2.py'), run_name='__main__')
