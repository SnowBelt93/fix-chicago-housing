from fit import fit, rect
import json
# screen pixels of the illustrative site plan, Bronzeville Lakefront CPC presentation (Feb 18, 2021 hearing), page 18, chicago.gov.
# Phases from pages 38 and 57 (phase 1: senior housing, ARC Innovation Center, Singer Pavilion by 31st St; data center at the north end; max 350 ft).
f = fit([((1067.5, 645), (-87.617299, 41.838422)), ((1067.5, 442), (-87.61739, 41.84207)), ((1067.5, 247), (-87.617482, 41.84569)), ((1137, 645), (-87.61561, 41.837898))])
Z = lambda x0, y0, x1, y1: rect(1060 + x0 / 2, 230 + y0 / 2, 1060 + x1 / 2, 230 + y1 / 2)
P = lambda pts: [(1060 + x / 2, 230 + y / 2) for x, y in pts]
B = [
 dict(n="senior housing", ph=1, st=6, use="res", p=Z(170,735,220,765)),
 dict(n="senior housing 2", ph=1, st=8, use="res", p=Z(225,720,280,750)),
 dict(n="31st St block", ph=1, st=6, use="res", p=Z(240,770,300,800)),
 dict(n="ARC Innovation Center", ph=1, st=6, use="office", p=P([(315,725),(445,690),(455,725),(325,760)])),
 dict(n="30th St west", ph=2, st=8, use="res", p=Z(170,590,245,630)),
 dict(n="30th St middle", ph=2, st=8, use="res", p=Z(205,655,265,690)),
 dict(n="Cottage block S", ph=2, st=12, use="res", p=Z(265,545,325,600)),
 dict(n="Lake Park block S", ph=2, st=12, use="res", p=Z(345,510,400,575)),
 dict(n="Vernon block", ph=2, st=10, use="res", p=Z(165,525,225,570)),
 dict(n="29th St west", ph=2, st=16, use="res", p=Z(165,450,210,495)),
 dict(n="29th St Cottage", ph=2, st=16, use="res", p=Z(235,430,285,485)),
 dict(n="Lake Park block N", ph=2, st=14, use="res", p=Z(320,410,375,475)),
 dict(n="park west", ph=3, st=14, use="res", p=Z(170,225,215,280)),
 dict(n="park west 2", ph=3, st=10, use="res", p=Z(190,290,235,340)),
 dict(n="27th St tower", ph=3, st=30, use="res", p=Z(250,205,320,320)),
 dict(n="King Dr block", ph=3, st=10, use="res", p=Z(40,55,105,135)),
 dict(n="data center", ph=3, st=5, use="office", p=P([(130,50),(250,50),(285,180),(160,188)])),
]
for b in B: b["p"] = f(b["p"])
json.dump(B, open("bronze.json", "w"))
