from fit import fit, rect
import json, math
# Natural pixels of CHA's Cabrini NOW site map (Community Workshop #3, Dec 11, 2024; image Cabrini-Now-02.jpg via Chicago YIMBY), north up.
# Homes per building from the same deck's massing diagrams (Division, Larrabee, Rowhomes and Sedgwick sites). Stories = homes x 1,000 sq ft / footprint.
f = fit([((1778, 963), (-87.648086, 41.903643)), ((2703, 963), (-87.634474, 41.903857)), ((2105, 1621), (-87.642948, 41.896481)),
         ((2703, 1621), (-87.63421, 41.896586)), ((1778, 298), (-87.648286, 41.910927)), ((2105, 963), (-87.643216, 41.903716))])
M = 1.225   # m per pixel
B = [  # name, phase, homes, footprint (natural px); th = townhomes (3 stories)
 ("K1 (Chicago & Larrabee)", 1, 275, rect(2200,1563,2236,1605)), ("K2", 1, 165, rect(2268,1563,2305,1605)), ("K3 (Larrabee)", 1, 238, rect(2197,1440,2216,1552)),
 ("K5", 1, 49, rect(2238,1380,2266,1400)), ("K5 townhomes", 1, "th", rect(2238,1405,2266,1418)), ("K7", 1, 172, rect(2200,1280,2300,1298)), ("K7 townhomes", 1, "th", rect(2240,1302,2300,1314)),
 ("HJ", 1, 160, rect(2185,1176,2210,1252)), ("HJ townhomes", 1, "th", rect(2117,1178,2168,1192)),
 ("MN1 (Sedgwick)", 1, 172, rect(2366,1440,2384,1560)), ("R1", 1, 15, rect(2470,1416,2490,1431)),
 ("L4 (Oak & Sedgwick)", 2, 285, rect(2330,1272,2368,1318)), ("L1", 2, 165, rect(2398,1272,2456,1306)),
 ("L2 six-flats", 2, 96, rect(2335,1345,2455,1358)), ("L2 townhomes", 2, "th", rect(2335,1372,2455,1384)), ("L3 six-flats", 2, 48, rect(2322,1180,2352,1250)),
 ("A1.1 base", 2, 120, rect(1815,925,1878,952)), ("A1.1 tower (Halsted & Division)", 2, 265, rect(1815,890,1846,925)), ("A1.2", 2, 100, rect(1848,846,1878,876)),
 ("A2.1 south", 2, 160, rect(1892,925,1950,952)), ("A2.1 west", 2, 60, rect(1892,868,1906,912)), ("A2.1 east", 2, 60, rect(1936,868,1950,912)), ("A2.1 townhomes", 2, "th", rect(1910,866,1932,880)),
 ("A2.2 tower", 2, 185, rect(1898,842,1926,862)), ("A3", 2, 50, rect(1960,890,1971,950)),
 ("B1", 3, 90, rect(1982,612,1996,700)), ("B1 wing", 3, 50, rect(1999,612,2035,630)),
 ("D1 (Larrabee)", 3, 230, rect(2068,722,2088,862)), ("E1.1 eight-flats", 3, 50, rect(2118,622,2134,690)), ("E1.2", 3, 220, rect(2142,650,2168,740)),
 ("G1.1 (Division & Larrabee)", 3, 430, rect(2120,885,2170,950)), ("G1.2", 3, 125, rect(2190,905,2232,950)),
]
out, tot = [], 0
for n, ph, homes, p in B:
    a = abs((p[1][0] - p[0][0]) * (p[2][1] - p[1][1])) * M * M
    st = 3 if homes == "th" else max(3, round(homes * 92.9 / a))
    if homes != "th": tot += homes
    out.append(dict(n=n, ph=ph, st=st, use="res", p=f(p)))
    print(f"{n:32s} {homes!s:>4} homes  {a:6.0f} m2  {st} st")
print("homes", tot)
json.dump(out, open("cabrini.json", "w"))
