"""Overlays for the lot tool's "Rules that apply here": lot/data/r/<ix>_<iy>.json, the same 0.01° tiles as lot/data/t.
Reads the downloads on main (tools/lot/fetch.py -> tools/raw/lot/, checked out at ../fch-main). Run by hand after a fetch:
  python3 tools/lot/prep_rules.py [path to main's tools/raw/lot]

Tile file: {"x0": west lon, "y0": south lat, "f": [[kind, name, detail, [[ring], …]], …]} with rings as flat lists of
integer offsets from the tile corner in 1e-6 degrees. Kinds:
  ld  Chicago Landmark District          (Commission on Chicago Landmarks; permits for exterior work need its review)
  il  individual Chicago Landmark        detail = designation date
  hr  Chicago Historic Resources Survey   detail = "Red" or "Orange" (demolition permits wait up to 90 days)
  nr  National Register of Historic Places
  ssa Special Service Area                detail = SSA number
  oz  federal Opportunity Zone (2018 designation, census tract)
  fl  FEMA special flood hazard area     detail = zone (A, AE, AH, AO)
Nothing here names a private person: the landmark files' architect column is dropped at download and again here."""
import gzip, json, math, os, sys, collections
from shapely.geometry import shape, box, Polygon, MultiPolygon, mapping
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RAW = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(ROOT), 'fch-main', 'tools', 'raw', 'lot')
OUT = os.path.join(ROOT, 'lot', 'data', 'r'); os.makedirs(OUT, exist_ok=True)
def tkey(lon, lat): return int(math.floor((lon + 88) * 100)), int(math.floor((lat - 41) * 100))
def load(n):
    p = os.path.join(RAW, n)
    return json.load(gzip.open(p)) if os.path.exists(p) else None
def date(s): return (s or '')[:10]

feats = []   # (kind, name, detail, shapely geometry)
g = load('ov_landmark_districts.geojson.gz')
for f in (g or {}).get('features', []):
    p = f['properties']; nm = p.get('NAME') or p.get('name') or p.get('DISTRICT') or p.get('district_name') or p.get('DIST_NAME') or 'Landmark district'
    feats.append(('ld', str(nm).title() if str(nm).isupper() else str(nm), date(str(p.get('DESIGNATED') or p.get('date') or '')), shape(f['geometry'])))
g = load('ov_uct4-hrvh.geojson.gz')
for f in (g or {}).get('features', []):
    p = f['properties']; feats.append(('il', p.get('name') or 'Chicago Landmark', date(p.get('landmark')), shape(f['geometry'])))
g = load('ov_2u8t-236p.geojson.gz')
for f in (g or {}).get('features', []):
    p = f['properties']
    if str(p.get('demolished') or '').strip().lower() in ('y', 'yes', 'true', '1'): continue
    if p.get('color') in ('Red', 'Orange'): feats.append(('hr', '', p['color'], shape(f['geometry'])))
g = load('ov_bqx3-yhry.geojson.gz')
for f in (g or {}).get('features', []):
    p = f['properties']; feats.append(('nr', p.get('name') or 'National Register', 'district' if p.get('individual') != 'I' else 'individual', shape(f['geometry'])))
g = load('ov_cmr6-dn8c.geojson.gz')
for f in (g or {}).get('features', []):
    p = f['properties']
    if (p.get('status') or 'Active') == 'Active': feats.append(('ssa', p.get('name') or '', (p.get('ref_no') or '').replace('SSA#', ''), shape(f['geometry'])))
oz = json.load(open(os.path.join(RAW, 'oz_tracts.json'))) if os.path.exists(os.path.join(RAW, 'oz_tracts.json')) else {}
for t, rings in (oz.get('shapes') or {}).items():
    if t in set(oz.get('tracts', [])):
        try: feats.append(('oz', '', t, Polygon(rings[0], rings[1:]).buffer(0)))
        except Exception: pass
g = load('flood.geojson.gz')
for f in (g or {}).get('features', []):
    z = f['properties'].get('FLD_ZONE')
    if z in ('A', 'AE', 'AH', 'AO', 'VE'): feats.append(('fl', '', z, shape(f['geometry']).buffer(0)))
print(collections.Counter(k for k, *_ in feats))

TOL = {'hr': 0.000004, 'il': 0.000004, 'nr': 0.000006, 'ld': 0.00001, 'ssa': 0.00002, 'oz': 0.00002, 'fl': 0.00001}
tiles = collections.defaultdict(list)
for kind, nm, det, geo in feats:
    if geo.is_empty: continue
    geo = geo.simplify(TOL[kind], preserve_topology=True)
    x0, y0, x1, y1 = geo.bounds
    (a, b), (c, d) = tkey(x0, y0), tkey(x1, y1)
    for ix in range(a, c + 1):
        for iy in range(b, d + 1):
            tx, ty = ix / 100 - 88, iy / 100 + 41
            part = geo.intersection(box(tx, ty, tx + 0.01, ty + 0.01)) if (a, b) != (c, d) else geo
            if part.is_empty: continue
            polys = [part] if isinstance(part, Polygon) else [q for q in getattr(part, 'geoms', []) if isinstance(q, Polygon)]
            rings = []
            for q in polys:
                for r in [q.exterior] + list(q.interiors):
                    pts = []
                    for x, y in list(r.coords)[:-1]: pts += [round((x - tx) * 1e6), round((y - ty) * 1e6)]
                    if len(pts) >= 6: rings.append(pts)
            if rings: tiles[(ix, iy)].append([kind, nm, det, rings])
for f in os.listdir(OUT): os.remove(os.path.join(OUT, f))
size = 0
for (ix, iy), L in tiles.items():
    p = os.path.join(OUT, f'{ix}_{iy}.json')
    json.dump({'x0': round(ix / 100 - 88, 2), 'y0': round(iy / 100 + 41, 2), 'f': L}, open(p, 'w'), separators=(',', ':'), ensure_ascii=False)
    size += os.path.getsize(p)
print(len(tiles), 'tiles,', round(size / 1e6, 1), 'MB')
