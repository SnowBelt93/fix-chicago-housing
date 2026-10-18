"""Accuracy checks for the tracker's home counts.
  1. Yearly totals vs. the Census Building Permits Survey (BPS) for Chicago city, by building size.
  2. A random sample of housing permits written to tools/tracker/sample.csv for a hand check
     (the checker fills in 'hand_homes' without seeing the parser's answer; score with --score).
Run: python3 tools/tracker/accuracy.py [--sample N] [--score]"""
import csv, os, sys, random, collections, json
sys.path.insert(0, os.path.dirname(__file__))
from permits import load_permits, projects, RAW

HERE = os.path.dirname(__file__)

def bps():
    out = {}
    for r in csv.reader(open(os.path.join(RAW, 'bps_chicago.csv'))):
        try: i = r.index('Chicago')
        except ValueError: continue
        v = [int(x) if x.strip().isdigit() else 0 for x in r[i + 1:]]
        out[int(r[0])] = (v[1], v[4], v[7], v[10])
    return out

def size(h): return 0 if h == 1 else 1 if h == 2 else 2 if h <= 4 else 3

def yearly(J, first=2010, last=2025):
    B = bps(); Y = collections.defaultdict(lambda: [0, 0, 0, 0])
    for j in J:
        if j['homes']: Y[j['year']][size(j['homes'])] += j['homes']
    rows = []
    for y in range(first, last + 1):
        if y not in B: continue
        rows.append(dict(year=y, ours=Y[y], census=list(B[y]), ours_total=sum(Y[y]), census_total=sum(B[y])))
    return rows

def summary(rows):
    o = sum(r['ours_total'] for r in rows); c = sum(r['census_total'] for r in rows)
    errs = [abs(r['ours_total'] - r['census_total']) / r['census_total'] for r in rows]
    small_o = sum(sum(r['ours'][:3]) for r in rows); small_c = sum(sum(r['census'][:3]) for r in rows)
    return dict(years=f"{rows[0]['year']}-{rows[-1]['year']}", ours=o, census=c, ratio=round(o / c, 3),
                mean_abs_year_error=round(sum(errs) / len(errs), 3), median_abs_year_error=round(sorted(errs)[len(errs) // 2], 3),
                small_ratio=round(small_o / small_c, 3), big_ratio=round((o - small_o) / (c - small_c), 3))

def sample(P, n=200, seed=7):
    """Stratified: half small buildings (1-4 homes or unknown), half 5+, issued 2015 on, from every permit kind."""
    random.seed(seed)
    pool = [p for p in P if p['date'].year >= 2015]
    small = [p for p in pool if p['homes'] is None or p['homes'] <= 4]
    big = [p for p in pool if p['homes'] is not None and p['homes'] >= 5]
    pick = random.sample(small, n // 2) + random.sample(big, n - n // 2)
    random.shuffle(pick)
    with open(os.path.join(HERE, 'sample.csv'), 'w', newline='') as f:
        w = csv.writer(f); w.writerow(['id', 'date', 'description', 'hand_homes', 'hand_kind', 'note'])
        for p in pick: w.writerow([p['id'], p['date'], p['desc'], '', '', ''])
    json.dump({p['id']: [p['homes'], p['why']] for p in pick}, open(os.path.join(HERE, 'sample_parser.json'), 'w'))
    print('wrote', len(pick), 'permits to sample.csv')

def score():
    par = json.load(open(os.path.join(HERE, 'sample_parser.json')))
    rows = list(csv.DictReader(open(os.path.join(HERE, 'sample_checked.csv'))))
    ok = tot = 0; kinds = collections.Counter(); miss = []
    hand_sum = par_sum = 0
    for r in rows:
        h = r['hand_homes'].strip(); hk = r['hand_kind'].strip().lower()
        ph, pk = par[r['id']]
        hh = None if h in ('', '?', 'unknown') else int(h)
        # what each side would add to the count: partial permits and revisions add 0
        hand_add = 0 if hk in ('partial', 'revision', 'not housing') or hh is None else hh
        par_add = 0 if pk in ('partial permit', 'revision') or ph is None else ph
        hand_sum += hand_add; par_sum += par_add
        tot += 1; good = hand_add == par_add and (hk == 'partial') == (pk == 'partial permit') and (hk == 'revision') == (pk == 'revision')
        ok += good
        if not good: miss.append((r['id'], r['description'][:110], (hh, hk), (ph, pk)))
    print(f'exact match {ok}/{tot} = {ok / tot:.1%}; homes counted by hand {hand_sum}, by parser {par_sum} ({par_sum / max(1, hand_sum):.3f})')
    for m in miss: print('  MISS', m)
    return dict(n=tot, exact=ok, hand_homes=hand_sum, parser_homes=par_sum, misses=len(miss))

if __name__ == '__main__':
    P = load_permits()
    if '--score' in sys.argv: score(); sys.exit()
    if '--sample' in sys.argv: sample(P, int(sys.argv[sys.argv.index('--sample') + 1])); sys.exit()
    J = projects(P, 'first'); rows = yearly(J)
    for r in rows: print(r['year'], r['ours'], r['ours_total'], r['census'], r['census_total'], f"{r['ours_total'] / r['census_total']:.2f}")
    print(summary(rows))
