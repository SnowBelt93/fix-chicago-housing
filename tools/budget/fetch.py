"""Download City of Chicago budget data for "Balance the Chicago Budget" (runs in GitHub Actions; the cloud workspace
can't reach the data portal). Finds every "Budget Ordinance" appropriations, revenue and positions dataset on the
Chicago Data Portal through the Socrata catalog API and saves each as CSV under tools/raw/budget/, plus catalog.json
(dataset ids, names, update dates) so the build script knows which year each file is."""
import urllib.request, urllib.parse, json, os, re, time, gzip, subprocess
OUT = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'raw', 'budget'); os.makedirs(OUT, exist_ok=True)
def get(url, tries=5):
    for t in range(tries):
        try: return urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': 'shapechicago'}), timeout=300).read()
        except Exception as e: print('retry', t, url, e, flush=True); time.sleep(8 * (t + 1))
    raise RuntimeError(url)
found = {}
for q in ['budget ordinance appropriations', 'budget ordinance revenue', 'budget ordinance positions and salaries', 'budget recommendations appropriations', 'budget revenue']:
    off = 0
    while True:
        u = 'https://api.us.socrata.com/api/catalog/v1?' + urllib.parse.urlencode({'domains': 'data.cityofchicago.org', 'q': q, 'limit': 100, 'offset': off, 'only': 'dataset'})
        r = json.loads(get(u))
        for x in r['results']:
            res = x['resource']; name = res['name']
            if not re.search(r'budget', name, re.I): continue
            found[res['id']] = {'id': res['id'], 'name': name, 'updated': res.get('data_updated_at'), 'columns': res.get('columns_field_name')}
        off += 100
        if off >= r.get('resultSetSize', 0) or off > 500: break
print(len(found), 'budget datasets', flush=True)
json.dump(sorted(found.values(), key=lambda d: d['name']), open(os.path.join(OUT, 'catalog.json'), 'w'), indent=1)
for d in found.values():
    if not re.search(r'appropriation|revenue|position', d['name'], re.I): continue
    path = os.path.join(OUT, d['id'] + '.csv.gz')
    if os.path.exists(path): continue
    try:
        data = get(f"https://data.cityofchicago.org/api/views/{d['id']}/rows.csv?accessType=DOWNLOAD")
        gzip.open(path, 'wb').write(data); print(d['id'], d['name'], len(data), flush=True)
    except Exception as e: print('skip', d['id'], e, flush=True)

# Budget documents (the city's PDFs can't be read from the cloud workspace either): saved as text with pdftotext
DOCS = {
  'overview_2027': 'https://www.chicago.gov/content/dam/city/depts/obm/2027_Budget/Budget_Recommendation/2027_Budget_Overview/2027_Budget_Overview%20(1).pdf',
  'forecast_2027': 'https://www.chicago.gov/content/dam/city/depts/obm/2027_Budget/Budget_Forecast/2027_Chicago_Budget_Forecast.pdf',
  'cofa_forecast_2027': 'https://www.chicago.gov/content/dam/city/depts/COFA/AnnualBudgetForcast/COFA_FY2027%20Budget%20Forecast%20Review%20and%20Analysis_Final.pdf',
  'overview_2026': 'https://news.wttw.com/sites/default/files/article/file-attachments/2026%20City%20of%20Chicago%20Budget%20Overview.pdf',
  'forecast_2026': 'https://www.chicago.gov/content/dam/city/depts/obm/supp_info/2026Budget/2026%20Budget%20Forecast%20Book.pdf',
  'forecast_2025': 'https://chicago.gov/content/dam/city/depts/obm/supp_info/2025Budget/2025-Chicago-Budget-Forecast.pdf',
  'forecast_2024': 'https://www.chicago.gov/content/dam/city/depts/obm/supp_info/2024Budget/2024-Chicago-Budget-Forecast.pdf',
  'cofa_gap_explainer': 'https://www.chicago.gov/content/dam/city/depts/COFA/OnePagers/Budget%20gap%20explainer_COFA.pdf',
  'cofa_proposed_2024': 'https://www.chicago.gov/content/dam/city/depts/COFA/ProposedBudget/FiscalYear2024_COFA_AnalysisOfMayorsProposedBudget.pdf',
  'civicfed_roadmap_2025': 'https://civicfed.org/sites/default/files/2024-10/City%20of%20Chicago%20FY2025%20Roadmap_2.pdf',
  'budgit_2026': 'https://budgitusblog.budgit.org/wp-content/uploads/2026/05/Citizens-Guide-to-Chicagos-2026-Budget.pdf',
}
DD = os.path.join(OUT, 'docs'); os.makedirs(DD, exist_ok=True)
for k, u in DOCS.items():
    t = os.path.join(DD, k + '.txt')
    if os.path.exists(t): continue
    try:
        pdf = get(u); open('/tmp/x.pdf', 'wb').write(pdf)
        subprocess.run(['pdftotext', '-layout', '/tmp/x.pdf', t], check=True); print('doc', k, os.path.getsize(t), flush=True)
    except Exception as e: print('doc skip', k, e, flush=True)
