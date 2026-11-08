import json, os, math, sys
from shapely.geometry import LineString, MultiLineString
from shapely.ops import unary_union, nearest_points
T = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'street', 'data', 't')
def streets(lon0, lat0, lon1, lat1):
    out = {}
    for ix in range(int((lon0 + 88) * 100) - 1, int((lon1 + 88) * 100) + 2):
        for iy in range(int((lat0 - 41) * 100) - 1, int((lat1 - 41) * 100) + 2):
            f = f'{T}/{ix}_{iy}.json'
            if not os.path.exists(f): continue
            x0, y0 = ix / 100 - 88, iy / 100 + 41
            for w in json.load(open(f))['w']:
                c = w[-1]; pts = [(x0 + c[i] / 1e6, y0 + c[i + 1] / 1e6) for i in range(0, len(c), 2)]
                if len(pts) > 1: out.setdefault(w[1], []).append(LineString(pts))
    return {k: unary_union(v) for k, v in out.items()}
def cross(S, a, b):
    A = [v for k, v in S.items() if (" "+a.lower()) in (" "+k.lower())]; B = [v for k, v in S.items() if (" "+b.lower()) in (" "+k.lower())]
    if not A or not B: return None
    A, B = unary_union(A), unary_union(B); i = A.intersection(B)
    if not i.is_empty: return (i.centroid.x, i.centroid.y), 0
    p, q = nearest_points(A, B); return (p.x, p.y), round(p.distance(q) * 111000)
if __name__ == '__main__':
    lon0, lat0, lon1, lat1 = map(float, sys.argv[1:5]); S = streets(lon0, lat0, lon1, lat1)
    if len(sys.argv) == 5: print(sorted(S)); sys.exit()
    for pr in sys.argv[5:]:
        a, b = pr.split('/'); print(pr, cross(S, a, b))
