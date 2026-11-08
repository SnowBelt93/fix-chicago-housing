import json, sys, matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
from geo import streets
fig, axs = plt.subplots(2, 3, figsize=(21, 14))
for ax, nm in zip(axs.flat, ['foundry', 'the78', 'p1901', 'bronze', 'nunion', 'cabrini']):
    B = json.load(open(nm + '.json')); xs = [x for b in B for x, y in b['p']]; ys = [y for b in B for x, y in b['p']]
    pad = 0.0015; x0, x1, y0, y1 = min(xs) - pad, max(xs) + pad, min(ys) - pad, max(ys) + pad
    for k, g in streets(x0, y0, x1, y1).items():
        for l in (g.geoms if hasattr(g, 'geoms') else [g]):
            a, b = l.xy; ax.plot(a, b, color='#bbb', lw=1)
    for b in B:
        p = b['p'] + [b['p'][0]]; ax.fill([x for x, y in p], [y for x, y in p], color=plt.cm.viridis(min(1, b['st'] / 60)), alpha=.8)
        ax.text(sum(x for x, y in b['p']) / len(b['p']), sum(y for x, y in b['p']) / len(b['p']), str(b['st']), fontsize=7, ha='center')
    ax.set_xlim(x0, x1); ax.set_ylim(y0, y1); ax.set_aspect(1 / 0.745); ax.set_title(nm)
plt.tight_layout(); plt.savefig('check.png', dpi=60)
