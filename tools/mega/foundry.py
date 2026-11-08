from fit import fit, rect
f = fit([((764, 31), (-87.663146, 41.919866)), ((762.5, 556), (-87.66308, 41.917067)), ((1185, 556), (-87.660026, 41.917114)), ((506, 40), (-87.66503, 41.919843))])
# page pixels on the 1512-px-wide copy of the PD site plan (Chicago YIMBY, Jan 2026, image Foundry-Park-20.jpg)
B = [
 # phase one: four buildings around the two-acre square (Chicago YIMBY: hotel 11 st, 13 st, 8 st, 38-st tower on a podium)
 dict(n="tower podium", ph=1, st=4, use="mix", p=[(940,530),(940,500),(1015,420),(1122,530)]),
 dict(n="38-story tower", ph=1, st=38, use="res", p=rect(962,455,1012,505)),
 dict(n="hotel", ph=1, st=11, use="hotel", p=[(877,335),(902,317),(1000,402),(967,427)]),
 dict(n="13-story", ph=1, st=13, use="res", p=rect(787,372,830,477)),
 dict(n="8-story", ph=1, st=8, use="res", p=rect(790,490,917,530)),
 # later phases, north of Cortland
 dict(n="wedge", ph=2, st=14, use="res", p=[(787,188),(797,188),(885,282),(845,315),(812,347),(787,347)]),
 dict(n="north 1", ph=3, st=12, use="res", p=rect(677,47,737,182)),
 dict(n="north 2", ph=2, st=14, use="res", p=rect(677,212,737,325)),
 dict(n="north 3", ph=2, st=16, use="res", p=rect(675,390,737,530)),
 dict(n="townhomes Dickens", ph=3, st=3, use="res", p=rect(564,52,662,75)),
 dict(n="townhomes east", ph=3, st=3, use="res", p=rect(637,87,662,150)),
 dict(n="townhomes south", ph=3, st=3, use="res", p=rect(605,162,662,182)),
 dict(n="townhomes diagonal", ph=3, st=3, use="res", p=[(555,66),(568,62),(608,165),(595,172)]),
 dict(n="river homes", ph=3, st=3, use="res", p=[(463,95),(495,78),(612,330),(585,352)]),
 # south of Cortland: the point and west of the river
 dict(n="glass tower", ph=2, st=28, use="res", p=rect(690,587,732,702)),
 dict(n="Cortland mid-rise", ph=2, st=7, use="res", p=rect(787,582,897,622)),
 dict(n="curved condo east", ph=3, st=24, use="res", p=[(952,617),(1045,584),(1075,589),(1075,617),(962,649)]),
 dict(n="condo podium", ph=3, st=3, use="mix", p=rect(787,657,905,722)),
 dict(n="curved condo west", ph=3, st=22, use="res", p=[(815,692),(895,649),(910,657),(910,677),(830,722)]),
 dict(n="office east", ph=3, st=6, use="office", p=[(1092,582),(1177,582),(1180,592),(1117,649),(1092,622)]),
 dict(n="office south", ph=3, st=5, use="office", p=[(1130,677),(1205,612),(1235,644),(1160,729)]),
 dict(n="west tower", ph=2, st=30, use="res", p=[(387,687),(397,647),(480,640),(507,712),(445,729),(440,747),(402,742)]),
 dict(n="west office/parking", ph=3, st=6, use="office", p=[(405,827),(542,762),(585,857),(447,922)]),
]
for b in B: b["p"] = f(b["p"])
import json; json.dump(B, open("foundry.json", "w"))
