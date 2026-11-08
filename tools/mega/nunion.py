from fit import fit, rect
import json
# screen pixels of the site plan, North Union community presentation (Mar 24, 2021), page 12, chicago.gov. East is down, north is right.
# Stories as labeled on the plan; 920 N Wells (2023) and 868/878 N Wells (2024) are built (CTBUH), drawn from the start as built.
f = fit([((432.5, 662.5), (-87.634267, 41.898205)), ((815, 662.5), (-87.634323, 41.89977)), ((1005, 662.5), (-87.63435, 41.90053)),
         ((432.5, 392), (-87.635749, 41.898185)), ((627.5, 392), (-87.635773, 41.898966))])
B = [
 dict(n="920 N Wells (built 2023)", ph=0, st=19, use="built", p=rect(649,580,794,634)),
 dict(n="878 N Wells (built 2024)", ph=0, st=26, use="built", p=rect(461,582.5,599,634)),
 dict(n="909 N Franklin", ph=1, st=12, use="res", p=rect(649,416,750,469)),
 dict(n="215 W Walton", ph=1, st=6, use="res", p=rect(727.5,490,792.5,561)),
 dict(n="216 W Locust", ph=1, st=2, use="res", p=rect(650,489,715,561)),
 dict(n="232 W Chestnut", ph=1, st=5, use="res", p=rect(461,430,514,562.5)),
 dict(n="871 N Franklin", ph=1, st=4, use="res", p=rect(534,416,596,492.5)),
 dict(n="West Oak St row houses", ph=2, st=3, use="res", p=rect(844,495,977.5,529)),
 dict(n="205 W Oak podium", ph=2, st=4, use="res", p=rect(837.5,577.5,915,634)),
 dict(n="205 W Oak", ph=2, st=35, use="res", p=rect(917.5,580,977.5,630)),
 dict(n="312 W Walton podium", ph=2, st=5, use="res", p=rect(838,268,982,385)),
 dict(n="312 W Walton", ph=2, st=36, use="res", p=rect(848,312,972,360)),
 dict(n="Oak St podium", ph=3, st=5, use="res", p=rect(1030,268,1245,345)),
 dict(n="310 W Oak", ph=3, st=57, use="res", p=rect(1032,285,1115,355)),
 dict(n="300 W Oak", ph=3, st=65, use="res", p=rect(1152,318,1235,390)),
]
for b in B: b["p"] = f(b["p"])
json.dump(B, open("nunion.json", "w"))
