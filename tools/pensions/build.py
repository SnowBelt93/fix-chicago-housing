#!/usr/bin/env python3
"""Build pensions/data/pensions.json for the Shape Chicago pensions tool.
Starting point: each fund's December 31, 2024 figures from the City of Chicago 2024 ACFR, Required Supplementary
Information (schedules of changes in net pension liability; $ thousands): service cost, benefit payments, total pension
liability (TPL), employer and employee contributions, plan fiduciary net position (assets at market), covered payroll and
the GASB single discount rate. 2025 employer payments: 2025 appropriations (2026 Budget Overview). 2026 required payments:
2026 proposed (2026 Budget Overview), less the $120.2M advance split by fund.
Model, per fund per year: benefits = (2024 benefits / 2024 TPL) x TPL; normal cost and employee contributions are their
2024 share of payroll, payroll grows PAY_G; TPL(t+1) = TPL(1 + d + eps) + normal cost - benefits(1 + d)^0.5;
assets(t+1) = assets(1 + r) + (employer + employee - benefits)(1 + r)^0.5.
eps (extra liability growth) is calibrated per fund so that paying the 2026 required amount, growing with payroll, reaches
exactly 90% funded in the year state law sets (2055 police and fire, 2058 municipal and laborers). That makes the model
reproduce the legal schedule; every scenario on the page is a change from it."""
import json, os
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PAY_G = 0.03
F = {
 'MEABF': dict(name='Municipal employees', sc=344821, b=1141513, tpl=20205143, er24=1118398, ee=220416, fnp=5057271, pay=2600118, d=.0662, er25=1131.5e3, p26=1046.7e3, tgt=2058),
 'LABF':  dict(name='Laborers', sc=42336, b=183828, tpl=3127453, er24=147466, ee=24229, fnp=1260169, pay=252856, d=.0664, er25=158.5e3, p26=145.5e3, tgt=2058),
 'PABF':  dict(name='Police', sc=302649, b=1016120, tpl=18130036, er24=1011371, ee=121412, fnp=4325456, pay=1337507, d=.0666, er25=1142.5e3, p26=1106.3e3, tgt=2055),
 'FABF':  dict(name='Fire', sc=114995, b=434989, tpl=7487555, er24=472122, ee=53203, fnp=1774238, pay=529090, d=.0675, er25=474.0e3, p26=461.8e3, tgt=2055)}
ADV26 = 120.2e3; tot26 = sum(f['p26'] for f in F.values())
def sim(f, eps, er_of, r, y1):
    tpl, fnp, pay = f['tpl'], f['fnp'], f['pay']; k = f['b'] / f['tpl']
    for y in range(2025, y1 + 1):
        b = k * tpl; sc = f['sc'] / f['pay'] * pay; ee = f['ee'] / f['pay'] * pay; d = f['d']
        er = f['er25'] if y == 2025 else er_of(y)
        tpl = tpl * (1 + d + eps) + sc - b * (1 + d) ** .5
        fnp = fnp * (1 + r) + (er + ee - b) * (1 + r) ** .5
        pay *= 1 + PAY_G
    return tpl, fnp
for n, f in F.items():
    s26 = f['p26'] * (1 - ADV26 / tot26); f['s26'] = round(s26)
    lo, hi = -0.03, 0.05
    for _ in range(60):
        e = (lo + hi) / 2; tpl, fnp = sim(f, e, lambda y: s26 * (1 + PAY_G) ** (y - 2026), f['d'], f['tgt'])
        if fnp / tpl > .9: lo = e
        else: hi = e
    f['eps'] = round(e, 6); print(n, 'eps', round(e * 100, 3), '%')
out = {'payG': PAY_G, 'funds': F, 'forecast': {2026: 2843.2, 2027: 2941.7, 2028: 3002.1, 2029: 3029.7}, 'advance27': 364.0, 'npl25': 36.4,
       'note': 'ACFR 2024 RSI, $ thousands; forecast = 2027 Budget Forecast historic and projected pension contributions ($M, incl. advance payments)'}
os.makedirs(os.path.join(ROOT, 'pensions', 'data'), exist_ok=True)
json.dump(out, open(os.path.join(ROOT, 'pensions', 'data', 'pensions.json'), 'w'), indent=1)
