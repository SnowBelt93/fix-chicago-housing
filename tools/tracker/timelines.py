"""How long a housing permit takes: days from application to issued permit, for new buildings with homes.
Runs in the daily tracker job after fetch.py; writes tracker/timelines.json (copied to shape-v1 for Progress and the lot tool).

Counts only full new-construction permits whose description gives a number of homes (tools/tracker/units.py), not
foundation-only, partial or revision permits. Days = issue_date − application_start_date in the city's permit records.
Only permits issued from 2024 on: before the city's late-2023 records change, 22–46% of these permits show the
application on the same day as the permit, so the earlier dates measure something else and aren't compared.
It does not count design, zoning or financing time before someone applies.

Output: {"through": date, "since": "2024-01-01", "note": ...,
  "years": {"2024": {"1": {"n", "p25", "med", "p75"}, "2-4": {...}, "5-49": {...}, "50+": {...}, "all": {...}}, ...},
  "review": {"<review type>": {...}} for the last 12 months,
  "areas": {"<community area number>": {...}} for the last 24 months, areas with at least 8 permits}"""
import csv, gzip, json, os, sys, datetime as dt, collections, statistics
sys.path.insert(0, os.path.dirname(__file__))
import units
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SRC = os.path.join(ROOT, 'tools', 'raw', 'tracker', 'permits_nc.csv.gz')
SINCE = dt.date(2024, 1, 1)

def day(s):
    try: return dt.date.fromisoformat((s or '')[:10])
    except ValueError: return None
def band(h): return '1' if h == 1 else '2-4' if h <= 4 else '5-49' if h < 50 else '50+'
def stats(L):
    if not L: return None
    L = sorted(L); q = statistics.quantiles(L, n=4) if len(L) >= 4 else [L[0], statistics.median(L), L[-1]]
    return {'n': len(L), 'p25': round(q[0]), 'med': round(statistics.median(L)), 'p75': round(q[-1])}

def main():
    rows = []
    with gzip.open(SRC, 'rt') as fh:
        for r in csv.DictReader(fh):
            d = (r['work_description'] or '').upper()
            h, _ = units.classify(d)
            if not h or units.PARTIAL.search(d) or units.REVISION.search(d): continue
            a, i = day(r['application_start_date']), day(r['issue_date'])
            if not a or not i or i < SINCE or i < a: continue
            rows.append((i, (i - a).days, h, (r['review_type'] or '').strip().title(), (r['community_area'] or '').strip()))
    if len(rows) < 200: print('timelines: too few permits, kept the last file'); return
    thru = max(r[0] for r in rows)
    Y = collections.defaultdict(lambda: collections.defaultdict(list))
    for i, n, h, rv, ca in rows:
        Y[str(i.year)][band(h)].append(n); Y[str(i.year)]['all'].append(n)
    rev = collections.defaultdict(list); area = collections.defaultdict(list)
    for i, n, h, rv, ca in rows:
        if (thru - i).days <= 365 and rv: rev[rv].append(n)
        if (thru - i).days <= 730 and ca: area[str(int(float(ca)))].append(n)
    out = {'through': thru.isoformat(), 'since': SINCE.isoformat(),
           'years': {y: {b: stats(L) for b, L in v.items()} for y, v in sorted(Y.items())},
           'review': {k: stats(L) for k, L in sorted(rev.items(), key=lambda kv: -len(kv[1])) if len(L) >= 8},
           'areas': {k: stats(L) for k, L in area.items() if len(L) >= 8}}
    json.dump(out, open(os.path.join(ROOT, 'tracker', 'timelines.json'), 'w'), separators=(',', ':'))
    print('timelines through', out['through'], {y: v['all']['med'] for y, v in out['years'].items()}, len(out['areas']), 'areas')

if __name__ == '__main__':
    main()
