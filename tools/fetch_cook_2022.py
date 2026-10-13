"""Downloads Cook County's 2022 building footprints (with LiDAR heights) for the Chicago area into a compact file.
Run by .github/workflows/fetch-footprints.yml (the cloud workspace that builds the game can't reach the county's server).

Source: https://gis.cookcountyil.gov/traditional/rest/services/buildingFootprint_2022/MapServer/0
Output (gzip, little-endian): b"CK22", uint32 count, then per building:
  float32 height_ft, float32 area_sqft, uint16 npts, int32 lon0, int32 lat0 (micro-degrees), then (npts-1) x int16 (dlon, dlat)
  in micro-degrees relative to the first point. Outer ring only (largest part for multipolygons). Buildings under 200 sq ft are skipped."""
import gzip, json, struct, sys, time, urllib.parse, urllib.request

URL = "https://gis.cookcountyil.gov/traditional/rest/services/buildingFootprint_2022/MapServer/0/query"
BBOX = "-87.95,41.64,-87.52,42.03"   # Chicago plus a sliver of the inner suburbs; trimmed to the city later
out = sys.argv[1] if len(sys.argv) > 1 else "tools/raw/cook_bldg_2022.bin.gz"

def get(params, tries=6):
    url = URL + "?" + urllib.parse.urlencode(params)
    for t in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "fix-chicago-housing data prep"}), timeout=120) as r:
                d = json.loads(r.read())
            if "error" in d: raise RuntimeError(d["error"])
            return d
        except Exception as e:
            print("retry", t, e, flush=True); time.sleep(5 * (t + 1))
    raise SystemExit("gave up")

def ring_of(geom):
    if not geom: return None
    if geom["type"] == "Polygon": return geom["coordinates"][0]
    if geom["type"] == "MultiPolygon":
        best, ba = None, -1
        for poly in geom["coordinates"]:
            r = poly[0]; a = abs(sum(r[i][0] * r[i + 1][1] - r[i + 1][0] * r[i][1] for i in range(len(r) - 1)))
            if a > ba: best, ba = r, a
        return best
    return None

buf = bytearray(); n = 0; last = 0; skipped = 0; t0 = time.time()
while True:
    d = get({"where": f"OBJECTID > {last}", "geometry": BBOX, "geometryType": "esriGeometryEnvelope", "inSR": 4326,
             "spatialRel": "esriSpatialRelIntersects", "outFields": "OBJECTID,Height,Area_SQFT", "orderByFields": "OBJECTID ASC",
             "resultRecordCount": 2000, "outSR": 4326, "geometryPrecision": 6, "returnGeometry": "true", "f": "geojson"})
    feats = d.get("features", [])
    if not feats: break
    for f in feats:
        p = f.get("properties") or {}
        last = max(last, int(p.get("OBJECTID") or f.get("id") or last))
        area = float(p.get("Area_SQFT") or 0); h = float(p.get("Height") or 0)
        r = ring_of(f.get("geometry"))
        if area < 200 or not r or len(r) < 4: skipped += 1; continue
        if r[0] == r[-1]: r = r[:-1]
        r = r[:65535]
        lon0, lat0 = round(r[0][0] * 1e6), round(r[0][1] * 1e6)
        pts = []
        ok = True
        for x, y in r[1:]:
            dx, dy = round(x * 1e6) - lon0, round(y * 1e6) - lat0
            if abs(dx) > 32767 or abs(dy) > 32767: ok = False; break
            pts.append((dx, dy))
        if not ok: skipped += 1; continue
        buf += struct.pack("<ffHii", h, area, len(r), lon0, lat0)
        for dx, dy in pts: buf += struct.pack("<hh", dx, dy)
        n += 1
    print(f"{n} kept, {skipped} skipped, last OBJECTID {last}, {time.time() - t0:.0f}s", flush=True)
with gzip.open(out, "wb", compresslevel=9) as g:
    g.write(b"CK22" + struct.pack("<I", n) + bytes(buf))
print("wrote", out, n, "buildings")
