"""Roll calls on Chicago's recent budgets and tax votes, for "Would it pass?" in Balance the Chicago Budget (runs in
GitHub Actions; the cloud workspace can't reach the City Clerk's eLMS API). Writes tools/raw/budget/votes.json:
every final matter whose title matches the searches below, with its actions and each alderperson's vote."""
import urllib.request, urllib.parse, json, os, time
OUT = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'raw', 'budget'); os.makedirs(OUT, exist_ok=True)
E = 'https://api.chicityclerkelms.chicago.gov'
def ej(path, **params):
    u = E + path + ('?' + urllib.parse.urlencode(params) if params else '')
    for t in range(4):
        try: return json.loads(urllib.request.urlopen(urllib.request.Request(u, headers={'User-Agent': 'shapechicago'}), timeout=120).read())
        except Exception as e: print('retry', t, u[:120], e, flush=True); time.sleep(5 * (t + 1))
TERMS = ['"Annual Appropriation Ordinance Year 2026"', '"Annual Appropriation Ordinance Year 2025"', '"Annual Appropriation Ordinance Year 2024"',
         '"Annual Appropriation Ordinance Year 2027"', '"revenue ordinance"', '"Revenue Ordinance"', '"property tax levy"', '"Equitable Employer"',
         '"Personal Property Lease"', '"head tax"', '"Amusement Tax"', '"sports wagering"', '"Bring Chicago Home"', '"management ordinance"',
         '"Municipal Code amendments for budget"', '"2026 budget"', '"2025 budget"']
seen, out = set(), []
for term in TERMS:
    res = ej('/search', search=term, filter="introductionDate ge 2023-06-01T00:00:00Z", top='200', sort='introductionDate desc') or {}
    for m in res.get('data') or []:
        if m['matterId'] in seen or m.get('status') != '90-Final': continue
        seen.add(m['matterId'])
        r = ej('/matter/' + m['matterId'])
        if r and any(a.get('votes') for a in r.get('actions') or []):
            r.pop('attachments', None); r['_term'] = term; out.append(r); print('votes', r.get('recordNumber'), (r.get('title') or '')[:90], flush=True)
        time.sleep(0.25)
json.dump(out, open(os.path.join(OUT, 'votes.json'), 'w'))
print('matters with roll calls', len(out))
