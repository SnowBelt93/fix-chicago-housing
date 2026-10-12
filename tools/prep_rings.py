"""Merge the half-mile circles around stations into single shapes (so overlapping circles read as one zone).
Writes meta.json ringL (L), ringM (Metra), ringLM (both) as lists of polygons [[outer ring], [hole], ...] in lon/lat."""
import json, sys, os
from pyproj import Transformer
from shapely.geometry import Point, mapping
from shapely.ops import unary_union
mp = os.path.join(sys.argv[1], 'meta.json'); m = json.load(open(mp))
to_sp = Transformer.from_crs('EPSG:4326', 'EPSG:3435', always_xy=True); to_ll = Transformer.from_crs('EPSG:3435', 'EPSG:4326', always_xy=True)
def ring(pts):
    u = unary_union([Point(*to_sp.transform(p['lon'], p['lat'])).buffer(2640, 32) for p in pts]).simplify(15)
    polys = list(u.geoms) if u.geom_type == 'MultiPolygon' else [u]
    out = []
    for g in polys:
        rings = [g.exterior] + list(g.interiors)
        out.append([[[round(x, 5), round(y, 5)] for x, y in zip(*to_ll.transform(*r.xy))] for r in rings])
    return out
m['ringL'] = ring(m['stations']); m['ringM'] = ring(m['metra']); m['ringLM'] = ring(m['stations'] + m['metra'])
json.dump(m, open(mp, 'w'), separators=(',', ':'))
print({k: len(m[k]) for k in ('ringL', 'ringM', 'ringLM')}, os.path.getsize(mp))
