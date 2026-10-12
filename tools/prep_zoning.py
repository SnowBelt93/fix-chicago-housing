#!/usr/bin/env python3
"""
Flag buildings that would be "illegal to build today" under Chicago zoning.

Run this on a machine with normal internet access (the cloud session that built the game
couldn't reach the Chicago Data Portal). It:
  1. downloads the city's current zoning districts (Chicago Data Portal, dataset dj47-wfun),
  2. finds the zoning district under each building in b/*.wasm,
  3. sets flag bit 64 on buildings that hold more homes than their district allows
     on their (estimated) lot, and writes the .wasm files back in place.
The game shows a "Show buildings that would be illegal to build today" button automatically
once any building carries bit 64.

Usage:  pip install shapely numpy
        python3 tools/prep_zoning.py            # run from the folder that has index.html, meta.json and b/

Rules (Chicago Zoning Ordinance, Title 17; see SPEC.md for sources):
  minimum lot area per dwelling unit (MLA), in sq ft
  RS-1 6250, RS-2 5000, RS-3 2500, RT-3.5 1250, RT-4/RT-4A 1000, RM-4.5 700, RM-5/RM-5.5 400, RM-6/RM-6.5 300
  B/C districts by suffix: -1 2500, -1.5 1350, -2 1000, -3 400, -5 200 ; C3 allows no housing
  A detached house is allowed on any existing lot of record, so every lot allows at least 1 home.
  Lot area is estimated as 2x the building footprint, but never less than a standard
  Chicago lot (25 x 125 = 3,125 sq ft), since small buildings cover well under half their lot.
  Downtown (D*), Planned Developments (PD), manufacturing (M*), parks (POS) and transportation (T)
  districts are skipped. The RS-3 two-flat exception (60% of the block face already multi-unit) is ignored,
  so a few RS-3 two-flats get flagged that could qualify for it.
"""
import collections, json, math, os, re, struct, sys, urllib.request
import numpy as np
from shapely.geometry import shape, Point
from shapely.strtree import STRtree
from shapely import prepared

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# 7cve-jgbp is now only a map view (its export comes back empty); dj47-wfun is the dataset behind it.
URL = "https://data.cityofchicago.org/resource/dj47-wfun.geojson?$limit=100000"
CACHE = os.path.join(ROOT, "tools", "zoning.geojson")

RES = {"RS-1": 6250, "RS-2": 5000, "RS-3": 2500, "RT-3.5": 1250, "RT-4": 1000, "RT-4A": 1000,
       "RM-4.5": 700, "RM-5": 400, "RM-5.5": 400, "RM-6": 300, "RM-6.5": 300}
SUFFIX = {"1": 2500, "1.5": 1350, "2": 1000, "3": 400, "5": 200}

def mla(zone):
    z = (zone or "").strip().upper()
    z = re.sub(r"^RM-?(\d)-?(\.5)?$", r"RM-\1\2", z)   # the city's data has a few typos: RM4.5, RM5.5, RM4-.5
    if z in RES: return RES[z]
    m = re.match(r"^(B[123]|C[12])-(1\.5|1|2|3|5)$", z)
    if m: return SUFFIX[m.group(2)]
    if re.match(r"^C3-", z): return 0          # no housing allowed at all
    return None                                 # D*, PD, M*, POS, T, etc.: skip

def main():
    if not os.path.exists(CACHE):
        print("downloading zoning districts…")
        urllib.request.urlretrieve(URL, CACHE)
    gj = json.load(open(CACHE))
    geoms, zones = [], []
    for f in gj["features"]:
        if not f.get("geometry"): continue
        props = {k.lower(): v for k, v in (f.get("properties") or {}).items()}
        z = props.get("zone_class") or props.get("zoning") or props.get("zone")
        try: g = shape(f["geometry"])
        except Exception: continue
        if g.is_empty: continue
        geoms.append(g); zones.append(z)
    print(len(geoms), "zoning polygons")
    tree = STRtree(geoms); preps = [prepared.prep(g) for g in geoms]

    meta = json.load(open(os.path.join(ROOT, "meta.json")))
    flagged = total = 0
    seen = collections.Counter()                 # buildings per zoning class, for the summary
    for a in meta["areas"]:
        path = os.path.join(ROOT, "b", f"{a['num']}.wasm")
        buf = bytearray(open(path, "rb").read())
        N, V = struct.unpack_from("<II", buf, 0)
        lon0, lat0 = struct.unpack_from("<dd", buf, 8)
        q = np.frombuffer(bytes(buf[24:24 + 4 * V]), dtype="<i2").reshape(-1, 2).astype(float) * 0.5
        o = 24 + 4 * V
        nv = np.frombuffer(bytes(buf[o:o + N]), np.uint8); o += N
        o += N                                   # stories
        fl_off = o; o += N
        o += (N * 3) % 2
        un = np.frombuffer(bytes(buf[o:o + 2 * N]), "<u2"); o += 2 * N
        fp = np.frombuffer(bytes(buf[o:o + 2 * N]), "<u2").astype(float) * 2
        kx = 111320.0 * math.cos(math.radians(lat0)); ky = 110574.0
        start = 0
        for i in range(N):
            k_ = int(nv[i]); pts = q[start:start + k_]; start += k_
            cx, cy = pts[:, 0].mean(), pts[:, 1].mean()
            p = Point(lon0 + cx / kx, lat0 + cy / ky)
            zone = None
            for k in tree.query(p):
                if preps[k].contains(p): zone = zones[k]; break
            limit = mla(zone)
            seen[zone] += 1
            illegal = False
            if limit is not None and un[i] >= 2:
                lot = max(fp[i] * 2, 3125)                                     # fp is the footprint; lot ≈ 2 x footprint, at least a standard lot
                allowed = 0 if limit == 0 else max(1, int(lot // limit))
                illegal = un[i] > allowed
            if illegal: buf[fl_off + i] |= 64; flagged += 1
            else: buf[fl_off + i] &= ~64 & 0xFF
            total += 1
        open(path, "wb").write(buf)
        print(a["name"], "done")
    fam = lambda z: "no district found" if z is None else re.match(r"[A-Z]+", z.strip().upper() or "?").group(0)
    for label, keep in (("parsed", True), ("skipped", False)):
        rows = collections.Counter()
        for z, n in seen.items():
            if (mla(z) is not None) == keep: rows[z if keep else fam(z)] += n
        print(f"{label}: {sum(rows.values()):,} buildings")
        for z, n in rows.most_common(): print(f"  {z:<18}{n:>9,}")
    print(f"flagged {flagged:,} of {total:,} buildings as illegal to build today")

if __name__ == "__main__":
    main()
