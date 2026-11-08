"""Tag each news story with the Chicago wards it's about, so people who follow a ward see its news.

Reads news/data/news.json (written by tools/news/fetch.py on main) and adds to each item:
  "w":  wards the story is about, best evidence first
  "wq": how each ward was found, same order: "w" says "Nth Ward" / "Ward N", "ald" names the alderperson,
        "addr" a street address found in the lot tool's address index (lot/data), "area" a neighborhood name
Run on the shape-v1 checkout (the news workflow does this after copying the feed over):
  python3 tools/news/wardtag.py
Needs: wards.json (ward outlines), meta.json (community-area outlines), wards/data/wards.json (alderpeople),
lot/data/a/*.json + lot/data/t/*.json (addresses -> parcels -> ward). Pure Python except shapely.
"""
import json, os, re, sys
from shapely.geometry import shape, Polygon, MultiPolygon, Point

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
P = lambda *a: os.path.join(ROOT, *a)

# ---- ward outlines and community areas -> wards (an area counts for a ward holding 15%+ of its land) ----
WARDS = {}
for w in json.load(open(P("wards.json"))):
    polys = [Polygon(r[0], r[1:]) for r in w["polys"]]
    WARDS[w["ward"]] = MultiPolygon(polys).buffer(0)
META = json.load(open(P("meta.json")))
AREA_WARDS = {}
for f in META["outlines"]["features"]:
    g = shape(f["geometry"]).buffer(0); n = f["properties"]["num"]
    share = sorted(((g.intersection(W).area / g.area, w) for w, W in WARDS.items()), reverse=True)
    AREA_WARDS[n] = [w for s, w in share if s >= 0.15] or [share[0][1]]
AREA_NAME = {f["properties"]["num"]: f["properties"]["name"] for f in META["outlines"]["features"]}

# community areas by name, plus the neighborhood names people actually use (-> community area numbers)
ALIAS = {
    "Pilsen": [31], "Little Village": [30], "La Villita": [30], "Wicker Park": [24], "Ukrainian Village": [24], "East Village": [24], "Noble Square": [24],
    "Bucktown": [22], "River North": [8], "Streeterville": [8], "Gold Coast": [8], "Magnificent Mile": [8], "Old Town": [7, 8], "Cabrini": [8],
    "West Loop": [28], "Fulton Market": [28], "Greektown": [28], "Little Italy": [28], "University Village": [28], "Illinois Medical District": [28],
    "South Loop": [32, 33], "Printer's Row": [32], "Printers Row": [32], "Prairie District": [33], "Motor Row": [33], "Chinatown": [34, 60],
    "Bronzeville": [35, 38], "Andersonville": [77], "Wrigleyville": [6], "Boystown": [6], "Northalsted": [6], "Roscoe Village": [5],
    "Ravenswood": [3, 4, 5], "Buena Park": [3], "Sheridan Park": [3], "Bowmanville": [4], "Budlong Woods": [4], "Albany Park": [14],
    "Avondale": [21], "Logan Square": [22], "Humboldt Park": [23], "Kelvyn Park": [20], "Belmont Cragin": [19], "Galewood": [25],
    "Garfield Park": [26, 27], "Back of the Yards": [61], "Canaryville": [61], "McKinley Park": [59], "Bridgeport": [60], "Brighton Park": [58],
    "Little Village": [30], "Marquette Park": [66], "Chicago Lawn": [66], "Englewood": [68, 67], "Woodlawn": [42], "Hyde Park": [41], "Kenwood": [39],
    "South Shore": [43], "Jackson Park": [41, 42], "Washington Park": [40], "Grand Crossing": [69], "Chatham": [44], "Avalon Park": [45],
    "South Chicago": [46], "Pullman": [50], "Roseland": [49], "Altgeld Gardens": [54], "Hegewisch": [55], "Beverly": [72], "Morgan Park": [75],
    "Mount Greenwood": [74], "Edison Park": [9], "Norwood Park": [10], "Jefferson Park": [11], "Portage Park": [15], "Irving Park": [16],
    "Old Irving Park": [16], "Six Corners": [15], "Mayfair": [14], "North Center": [5], "Lincoln Square": [4], "Uptown": [3], "Edgewater": [77],
    "Rogers Park": [1], "West Ridge": [2], "West Rogers Park": [2], "Lakeview": [6], "Lake View": [6], "Lincoln Park": [7], "Near North Side": [8],
    "Near West Side": [28], "Near South Side": [33], "The Loop": [32], "Lower West Side": [31], "Austin": [25], "North Lawndale": [29],
    "South Lawndale": [30], "Douglas": [35], "Oakland": [36], "Garfield Ridge": [56], "Archer Heights": [57], "Gage Park": [63],
    "West Lawn": [65], "West Elsdon": [62], "Clearing": [64], "Ashburn": [70], "Auburn Gresham": [71], "Washington Heights": [73],
    "West Pullman": [53], "Riverdale": [54], "East Side": [52], "South Deering": [51], "Calumet Heights": [48], "Burnside": [47],
    "Montclare": [18], "Dunning": [17], "Forest Glen": [12], "North Park": [13], "Sauganash": [12], "Hermosa": [20], "Fuller Park": [37],
    "Grand Boulevard": [38], "New City": [61], "Armour Square": [34], "Greater Grand Crossing": [69], "Lawndale": [29, 30],
}
for n, name in AREA_NAME.items():
    ALIAS.setdefault(name.title().replace("Ohare", "O'Hare").replace("Mckinley", "McKinley"), [n])
ALIAS.pop("Loop", None); ALIAS.pop("Austin", None)   # "the Loop" (L tracks) and Austin, Texas are too often something else; "The Loop" stays
ALIAS["Austin neighborhood"] = [25]
PLACE_RE = re.compile(r"\b(" + "|".join(re.escape(k) for k in sorted(ALIAS, key=len, reverse=True)) + r")\b")

# ---- alderpeople (full name, or Ald./Alderperson/Alderman + last name) ----
WD = json.load(open(P("wards", "data", "wards.json")))
ALD = []
for w in WD["wards"]:
    nm = (w.get("ald") or {}).get("name") or ""
    if "," not in nm: continue
    last, first = [x.strip() for x in nm.split(",", 1)]
    first = first.split()[0]
    ALD.append((re.compile(r"\b(?:" + re.escape(first) + r"\s+(?:[A-Z]\.\s+)?" + re.escape(last) + r"|(?:Ald\.|Alder(?:person|man|woman))\s+(?:[A-Z][\w.'-]+\s+)?" + re.escape(last) + r")\b"), w["w"]))

ORD = {1: "1st", 2: "2nd", 3: "3rd"}
WARD_RE = re.compile(r"\b(?:(\d{1,2})(?:st|nd|rd|th)\s+[Ww]ard|[Ww]ard\s+(\d{1,2}))\b")

# ---- addresses: "6124 North Sheridan Road", "4447 N. Ashland Ave", "the 2700 block of West Adams Street" ----
ABBR = {"AVENUE": "AVE", "AV": "AVE", "STREET": "ST", "BOULEVARD": "BLVD", "ROAD": "RD", "PLACE": "PL", "DRIVE": "DR", "COURT": "CT", "PARKWAY": "PKWY",
        "TERRACE": "TER", "NORTH": "N", "SOUTH": "S", "EAST": "E", "WEST": "W"}
ADDR_RE = re.compile(r"\b(\d{1,5})(?:-\d{1,5})?\s+(?:block of\s+)?(North|South|East|West|N\.?|S\.?|E\.?|W\.?)\s+((?:[A-Z][a-zA-Z'.]*|\d{1,3}(?:st|nd|rd|th))(?:\s+[A-Z][a-zA-Z'.]*){0,2}?)\s+(Avenue|Ave\.?|Street|St\.?|Boulevard|Blvd\.?|Road|Rd\.?|Drive|Dr\.?|Place|Pl\.?|Court|Ct\.?|Parkway|Pkwy\.?|Terrace)\b")
BLOCK_RE = re.compile(r"\b(\d{1,5})\s+block of\s+(North|South|East|West)\s+")
SHARDS, TILES = {}, {}
def shard(name):
    k = re.sub(r"[^A-Z0-9]", "", re.sub(r"^[NSEW] ", "", name))[:2] or "_"
    if k not in SHARDS:
        try: SHARDS[k] = json.load(open(P("lot", "data", "a", k + ".json")))
        except Exception: SHARDS[k] = {}
    return SHARDS[k]
def tile(x, y):
    if (x, y) not in TILES:
        try: TILES[(x, y)] = json.load(open(P("lot", "data", "t", f"{x}_{y}.json")))
        except Exception: TILES[(x, y)] = None
    return TILES[(x, y)]
def addr_ward(num, d, street, suf):
    d = d.rstrip(".").upper()[0]
    words = [ABBR.get(w, w) for w in re.sub(r"[.]", "", f"{street} {suf}").upper().split()]
    words = [re.sub(r"^(\d+)(ST|ND|RD|TH)$", r"\1", w) for w in words]
    name = d + " " + " ".join(words)
    L = shard(name).get(name)
    if not L:   # the index sometimes stores "102ND ST" style numbers
        name2 = d + " " + " ".join(re.sub(r"^(\d+)$", lambda m: m.group(1) + ORD.get(int(m.group(1)) % 10 if int(m.group(1)) % 100 not in (11, 12, 13) else 0, "th"), w) for w in words)
        L = shard(name2).get(name2)
    if not L: return None
    best = min(L, key=lambda r: abs(r[0] - num))
    if abs(best[0] - num) > 200: return None
    T = tile(best[1], best[2])
    if not T: return None
    try: return int(T["p"][best[3]][10]) or None
    except Exception: return None

def tag(item):
    text = " ".join(x for x in (item.get("t"), item.get("x")) if x)
    found = []   # (ward, how)
    add = lambda w, q: (w, q) if 1 <= w <= 50 and w not in [f[0] for f in found] and found.append((w, q)) else None
    for m in WARD_RE.finditer(text): add(int(m.group(1) or m.group(2)), "w")
    for rx, w in ALD:
        if rx.search(text): add(w, "ald")
    for m in ADDR_RE.finditer(text):
        try: w = addr_ward(int(m.group(1)), m.group(2), m.group(3), m.group(4))
        except Exception: w = None
        if w: add(w, "addr")
    areas = []
    for m in PLACE_RE.finditer(text):
        for a in ALIAS[m.group(1)]:
            if a not in areas: areas.append(a)
    if not found or all(q == "area" for _, q in found):
        for a in areas[:3]:
            for w in AREA_WARDS.get(a, []): add(w, "area")
    item.pop("w", None); item.pop("wq", None); item.pop("wa", None)
    if found: item["w"] = [w for w, _ in found][:8]; item["wq"] = [q for _, q in found][:8]
    if areas: item["wa"] = areas[:4]
    return item

if __name__ == "__main__":
    path = P("news", "data", "news.json")
    N = json.load(open(path))
    for it in N["items"]: tag(it)
    json.dump(N, open(path, "w"), ensure_ascii=False, separators=(",", ":"))
    n = sum(1 for it in N["items"] if it.get("w"))
    print(f"tagged {n} of {len(N['items'])} stories with wards", file=sys.stderr)
    if "-v" in sys.argv:
        for it in N["items"]: print(it.get("w"), it.get("wq"), it.get("wa"), "|", it["t"][:80])
