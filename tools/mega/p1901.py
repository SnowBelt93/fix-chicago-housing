from fit import fit, rect
import json
# screen pixels of the PD site plan, CPC presentation Jan 16, 2025, page 25 (chicago.gov). Subarea heights and phases from page 11.
f = fit([((615.5, 317.5), (-87.676638, 41.881323)), ((978.5, 317.5), (-87.671746, 41.881398)), ((1157.5, 317.5), (-87.669303, 41.88143)),
         ((615.5, 572.5), (-87.676581, 41.878751)), ((1157.5, 572.5), (-87.66922, 41.878849)), ((795.5, 226), (-87.674223, 41.882274)),
         ((1342.5, 317.5), (-87.666806, 41.881465)), ((615.5, 135), (-87.676683, 41.883149)), ((1342.5, 135), (-87.66686, 41.883305))])
B = [
 # A (2028): the music hall, then the hotel and receiving building around the arena; not housing
 dict(n="music hall", ph=0, st=6, use="anchor", p=rect(630,460,780,560)),
 # B and C (2031): north of Madison, Damen to Wood. C up to 310 ft, B up to 400 ft
 dict(n="C west block", ph=2, st=12, use="res", p=rect(630,240,700,305)),
 dict(n="C tower", ph=2, st=28, use="res", p=rect(718,240,758,282)),
 dict(n="C east slab", ph=2, st=10, use="res", p=rect(765,240,790,305)),
 dict(n="C north block", ph=2, st=8, use="res", p=rect(650,148,785,205)),
 dict(n="B podium", ph=2, st=4, use="mix", p=rect(810,245,880,305)),
 dict(n="B tower", ph=2, st=36, use="res", p=rect(828,252,866,290)),
 dict(n="B east block", ph=2, st=12, use="res", p=rect(895,240,970,305)),
 dict(n="B north block", ph=2, st=10, use="res", p=rect(810,148,965,210)),
 # D (2034): Wood to Paulina south of Madison, up to 485 ft
 dict(n="D block", ph=3, st=14, use="res", p=rect(985,330,1060,435)),
 dict(n="D tower", ph=3, st=44, use="res", p=rect(1078,332,1120,374)),
 dict(n="D slab", ph=3, st=10, use="res", p=rect(1078,392,1150,435)),
 dict(n="D south block", ph=3, st=12, use="res", p=rect(985,455,1100,568)),
 # E (2037): Wood to Ashland north of Madison, up to 660 ft
 dict(n="E block", ph=4, st=14, use="res", p=rect(985,240,1060,305)),
 dict(n="E tower", ph=4, st=60, use="res", p=rect(1078,238,1120,280)),
 dict(n="E slab", ph=4, st=10, use="res", p=rect(1125,250,1150,310)),
 dict(n="E Paulina tower", ph=4, st=40, use="res", p=rect(1172,240,1214,312)),
 dict(n="E Ashland block", ph=4, st=12, use="res", p=rect(1228,276,1335,315)),
 # F (2040): Hoyne to Damen, up to 220 ft
 dict(n="F north", ph=5, st=8, use="res", p=rect(510,242,600,308)),
 dict(n="F middle", ph=5, st=12, use="res", p=rect(530,325,600,440)),
 dict(n="F south", ph=5, st=10, use="res", p=rect(530,455,600,570)),
 dict(n="F tower", ph=5, st=20, use="res", p=rect(542,478,590,522)),
]
for b in B: b["p"] = f(b["p"])
json.dump(B, open("p1901.json", "w"))
