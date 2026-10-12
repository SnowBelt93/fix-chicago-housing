"""Build b/streets.wasm (street centerlines) and street labels for meta.json.
Source: City of Chicago street center lines (github.com/Chicago/osd-street-center-line), dl/sc/data/Transportation.geojson.
Usage: python3 prep_streets.py <project dir>
Binary (little-endian): uint32 nPaths, uint32 nVerts, float64 lon0, float64 lat0,
  uint8 class[nPaths] (1 expressway, 2 arterial, 3 collector, 4 local), pad to 4 bytes,
  uint32 start[nPaths+1] (vertex offsets), int16 xy[2*nVerts] in 2 m units east/north of origin."""
import json, os, sys, math, struct, collections
import numpy as np
from shapely.geometry import LineString, MultiLineString
from shapely.ops import linemerge

SCR = os.path.dirname(os.path.abspath(__file__)); OUT = sys.argv[1]
d = json.load(open(os.path.join(SCR, 'dl/sc/data/Transportation.geojson')))
LON0, LAT0 = -87.68, 41.84
KX = 111320.0 * math.cos(math.radians(LAT0)); KY = 110574.0
by = collections.defaultdict(list)
for f in d['features']:
    p = f['properties']; g = f['geometry']
    c = p.get('CLASS')
    if c not in ('1', '2', '3', '4') or not g or g['type'] != 'LineString': continue
    nm = ' '.join(x for x in (p.get('STREET_NAM'), p.get('STREET_TYP')) if x) or '?'
    by[(int(c), nm)].append(g['coordinates'])
paths, classes, labels = [], [], []
CORR3 = {'MILWAUKEE','CLARK','BROADWAY','DAMEN','LINCOLN','ARCHER','OGDEN','GRAND','DIVISION','HALSTED','ASHLAND','WESTERN','KEDZIE','CHICAGO','MADISON','DEVON','LAWRENCE','BELMONT','FULLERTON','CERMAK','ROOSEVELT'}
def tidy(nm):
    out = []
    for w in nm.split():
        w = w.title(); w = {'Expy': 'Expwy', 'Dr Martin Luther King Jr': 'King'}.get(w, w)
        out.append(w.replace('1St', '1st').replace('2Nd', '2nd').replace('3Rd', '3rd').replace('Th', 'th') if w[0].isdigit() else w)
    return ' '.join(out).replace('Dr Martin Luther King Jr Dr', 'King Dr').replace('Lake Shore Dr', 'DuSable Lake Shore Dr').replace('I190 Expwy', 'I-190').replace('I57 Expwy', 'I-57')
for (c, nm), segs in by.items():
    ml = linemerge(MultiLineString([LineString(s) for s in segs if len(s) >= 2]))
    geoms = list(ml.geoms) if ml.geom_type == 'MultiLineString' else [ml]
    for g in geoms:
        tol = 0.00002 if c == 4 else 0.00001
        g2 = g.simplify(tol)
        co = np.array(g2.coords)
        if len(co) < 2: continue
        paths.append(co); classes.append(c)
        if nm != '?' and 'EXPRESS' not in nm and (c in (1, 2) or (c == 3 and nm.split()[0] in CORR3)):
            xy = np.stack([(co[:, 0] - LON0) * KX, (co[:, 1] - LAT0) * KY], 1)
            seg = np.hypot(*np.diff(xy, axis=0).T); L = seg.sum()
            if L < 1500: continue
            cum = np.concatenate([[0], np.cumsum(seg)])
            step = 4500 if c == 2 else 6000
            for s in np.arange(step / 2, L, step):
                k = min(np.searchsorted(cum, s), len(seg)) - 1; k = max(k, 0)
                t = (s - cum[k]) / max(seg[k], 1e-9)
                px, py = xy[k] + (xy[k + 1] - xy[k]) * t
                ang = math.degrees(math.atan2(xy[k + 1][1] - xy[k][1], xy[k + 1][0] - xy[k][0]))
                if ang > 90: ang -= 180
                if ang < -90: ang += 180
                labels.append([round(LON0 + px / KX, 5), round(LAT0 + py / KY, 5), round(ang), tidy(nm), c])
allv = np.concatenate(paths)
q = np.round(np.stack([(allv[:, 0] - LON0) * KX, (allv[:, 1] - LAT0) * KY], 1) / 2).astype(np.int64)
assert q.min() > -32767 and q.max() < 32767, (q.min(), q.max())
starts = np.concatenate([[0], np.cumsum([len(p) for p in paths])]).astype('<u4')
with open(os.path.join(OUT, 'b', 'streets.wasm'), 'wb') as fh:
    fh.write(struct.pack('<IIdd', len(paths), len(allv), LON0, LAT0))
    cl = np.array(classes, dtype=np.uint8).tobytes(); fh.write(cl); fh.write(b'\0' * ((4 - len(cl) % 4) % 4))
    fh.write(starts.tobytes()); fh.write(q.astype('<i2').tobytes())
mp = os.path.join(OUT, 'meta.json'); meta = json.load(open(mp)); meta['streetLabels'] = labels
json.dump(meta, open(mp, 'w'), separators=(',', ':'))
print('paths', len(paths), 'verts', len(allv), 'labels', len(labels), 'bytes', os.path.getsize(os.path.join(OUT, 'b', 'streets.wasm')))
