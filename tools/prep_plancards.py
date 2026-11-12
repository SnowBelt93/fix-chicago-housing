"""Small SVG outlines of the 77 community areas for plan cards (plans/areas.json).
Projects lon/lat to a 1000-unit-tall box (equirectangular at Chicago's latitude), simplifies, and writes one path per area:
{"w": width, "h": 1000, "b": [west, south, east, north] (for placing other lon/lat points: x = (lon - west) * cos(mid latitude) * 1000 / (north - south), y = (north - lat) * 1000 / (north - south)), "areas": {"1": "M..Z", ...}, "L": [[x,y]...] L stations, "M": Metra stations in the box, "corr": corridor paths}. Run: python3 tools/prep_plancards.py"""
import json, math
from shapely.geometry import shape, box
from shapely.ops import unary_union
M = json.load(open("meta.json"))
feats = M["outlines"]["features"]
geoms = {f["properties"]["num"]: shape(f["geometry"]) for f in feats}
allg = unary_union(list(geoms.values()))
x0, y0, x1, y1 = allg.bounds
k = math.cos(math.radians((y0 + y1) / 2))
H = 1000.0; S = H / (y1 - y0); W = (x1 - x0) * k * S
def P(lon, lat): return ((lon - x0) * k * S, (y1 - lat) * S)
def path(g):
    out = []
    polys = [g] if g.geom_type == "Polygon" else list(g.geoms)
    for p in polys:
        for ring in [p.exterior]:
            pts = [P(*c) for c in ring.coords]
            if len(pts) < 4: continue
            out.append("M" + "L".join(f"{x:.0f} {y:.0f}" for x, y in pts[:-1]) + "Z")
    return "".join(out)
areas = {str(n): path(g.simplify(0.0012, preserve_topology=True)) for n, g in geoms.items()}
pt = lambda L: [[round(c) for c in P(o["lon"], o["lat"])] for o in L]
lines = []
for c in M["corridors"]:
    for pa in c["paths"]:
        q = [P(*xy) for xy in pa]
        lines.append("M" + "L".join(f"{x:.0f} {y:.0f}" for x, y in q))
json.dump({"w": round(W), "h": int(H), "b": [round(x0, 5), round(y0, 5), round(x1, 5), round(y1, 5)], "areas": areas, "L": pt(M["stations"]), "M": [p for p in pt(M["metra"]) if -5 <= p[0] <= W + 5 and -5 <= p[1] <= H + 5], "corr": "".join(lines)}, open("plans/areas.json", "w"), separators=(",", ":"))
print(round(W), sum(len(v) for v in areas.values()), "chars")
