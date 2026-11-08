from fit import fit, rect
import json, math
# screen pixels of Master-Plan.png (Plan Commission presentation, Sept 2025, via Chicago YIMBY) shown 1512 px wide, scrolled 155.5 px. North is to the left.
f = fit([((60, -24.5), (-87.63049, 41.86738)), ((60, 423), (-87.63345, 41.86733)), ((1127, -24.5), (-87.630266, 41.861916)), ((1127, 423), (-87.63345, 41.86195))])
B = [  # (footprint, stories): towers where the plan shows a tall block or a podium with a smaller block on top; heights illustrative
 ("Fire stadium", rect(388,95,718,400), 9),
 ("A1", rect(91,20,211,74), 12), ("A2", rect(91,143,134,206), 8), ("A3", rect(174,123,211,206), 16), ("A4", rect(111,234,211,271), 6),
 ("A5", rect(91,317,220,403), 20), ("A6", rect(237,320,357,403), 28), ("A7", rect(249,251,331,317), 14), ("A8", rect(249,111,349,206), 22),
 ("S1", rect(91,449,220,517), 32), ("S2", rect(249,449,383,543), 40), ("S3", rect(657,449,766,540), 36),
 ("C1", rect(813,84,886,308), 24), ("C2", rect(813,335,903,400), 14), ("C3", rect(907,84,964,138), 10), ("C4a", rect(990,84,1075,144), 18), ("C4b", rect(974,144,1031,220), 12),
 ("C5", rect(1053,157,1106,220), 8), ("C6", rect(923,275,990,381), 16), ("C7", rect(1012,242,1106,400), 30),
 ("D1", rect(1145,62,1223,127), 10), ("D2", rect(1149,146,1294,228), 20), ("D3", rect(1150,250,1236,395), 26), ("D4", [(1228,250),(1285,256),(1278,360),(1222,355)], 12),
 ("E1", rect(794,447,943,534), 45), ("E2", rect(977,447,1089,537), 38), ("E3", rect(1342,444,1460,521), 30),
]
kx = 111319.49 * math.cos(math.radians(41.864))
out = []
for n, p, st in B:
    ll = f(p); xs = [(x + 87.63) * kx for x, y in ll]; ys = [(y - 41.864) * 111319.49 for x, y in ll]
    a = abs(sum(xs[i] * ys[i - 1] - xs[i - 1] * ys[i] for i in range(len(xs)))) / 2
    out.append(dict(n=n, st=st, use="anchor" if n == "Fire stadium" else "res", ph=0 if n == "Fire stadium" else (1 if n[0] in "AS" else 2 if n[0] in "CE" else 3), p=ll, a=round(a)))
tot = sum(b["a"] * b["st"] for b in out if b["use"] == "res")
print("footprint m2", sum(b["a"] for b in out), "floor m2", tot, "homes at 1,026 sq ft (incl. 15% for halls and ground floors)", round(tot * 0.85 / (1026 * 0.0929)))
json.dump(out, open("the78.json", "w"))
