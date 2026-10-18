"""Turn the raw new-construction permits into housing projects, with each project's homes counted once.
Used by build.py (tracker data) and accuracy.py (checks).

Big buildings get several permits: foundation or caisson permits, partial superstructure, the full building permit,
then revisions, each with a new permit number and often the same unit count. So permits are grouped into projects:
same street address and building label ('BUILDING A'), within 5 years of the project's first permit. A project's
homes come from its full building permit (the latest one, since unit counts get revised); if it only has partial
permits so far, from the partial permit's stated unit count. Revisions never add homes. A project is dated by its
first full building permit (or its first permit if it has none), which matches the Census survey best (accuracy.py)."""
import csv, gzip, os, datetime
from units import classify, label

RAW = os.path.join(os.path.dirname(__file__), '..', 'raw', 'tracker')
DEAD = ('CANCELLED', 'REVOKED')

def addr(r):
    return ' '.join(x.strip().upper() for x in (r['street_number'], r['street_direction'], r['street_name']) if x.strip())

def load_permits(path=None):
    path = path or os.path.join(RAW, 'permits_nc.csv.gz')
    out = []
    for r in csv.DictReader(gzip.open(path, 'rt')):
        if r['permit_type'] != 'PERMIT - NEW CONSTRUCTION': continue
        homes, why = classify(r['work_description'])
        if why in ('not housing', 'garage only', 'empty'): continue
        try: d = datetime.date.fromisoformat(r['issue_date'][:10])
        except ValueError: continue
        try: lat, lon = float(r['latitude']), float(r['longitude'])
        except (ValueError, KeyError): lat = lon = None
        out.append(dict(id=r['id'], permit=r['permit_'], date=d, homes=homes, why=why, addr=addr(r), label=label(r['work_description']),
                        status=r.get('permit_status', ''), milestone=r.get('permit_milestone', ''), review=r.get('review_type', ''),
                        ward=r.get('ward', ''), ca=r.get('community_area', ''), lat=lat, lon=lon, cost=r.get('reported_cost', ''),
                        desc=' '.join(r['work_description'].split())))
    out.sort(key=lambda p: (p['date'], p['id']))
    return out

def is_full(p): return p['why'] not in ('partial permit', 'revision')

def projects(permits=None, date_by='full'):
    permits = permits if permits is not None else load_permits()
    groups, open_ = [], {}
    for p in permits:
        k = (p['addr'], p['label'])
        g = open_.get(k)
        if g is None or (p['date'] - g[0]['date']).days > 5 * 365:
            g = []; open_[k] = g; groups.append(g)
        g.append(p)
    out = []
    for g in groups:
        live = [p for p in g if p['status'] not in DEAD]
        full = [p for p in live if is_full(p) and p['homes']]
        part = [p for p in live if p['why'] == 'partial permit' and p['homes']]
        if full: homes, src = full[-1]['homes'], full[-1]
        elif part: homes, src = part[-1]['homes'], part[-1]
        else: homes, src = (None if any(p['homes'] is None and is_full(p) for p in live) else 0), (live or g)[-1]
        first_full = next((p for p in live if is_full(p)), None)
        dp = (first_full if (date_by == 'full' and first_full) else (live or g)[0])
        done = any('CERTIFICATE OF OCCUPANCY ISSUED' in p['milestone'] for p in g)
        expired = bool(live) and all(p['status'] == 'EXPIRED' for p in live)
        out.append(dict(addr=g[0]['addr'], label=g[0]['label'], date=dp['date'], year=dp['date'].year, homes=homes, src=src,
                        permits=g, partial_only=not full and bool(part), done=done, expired=expired,
                        ward=src['ward'], ca=src['ca'], lat=src['lat'], lon=src['lon']))
    return out
