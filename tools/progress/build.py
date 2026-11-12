"""Progress: the overview and one page per section, written as plain HTML into progress/.

  python3 tools/progress/build.py

Live numbers: Homes permitted comes from tracker/data.json, which the daily tracker job refreshes (that job runs this
script afterwards, so the pages follow the data). Everything else is a snapshot from the one-time analyses of
Nov. 9, 2026 (SNAP below, each with the date its data runs through) until those get their own daily jobs.
Homes per ward come from the 2020 Census blocks in bears/data/blocks.bin.
Every figure here was checked in the Nov. 9 review (Claude Docs "Shape Chicago - Progress review")."""
import json, math, os, re, struct, datetime as dt

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(ROOT, 'progress')
T = json.load(open(os.path.join(ROOT, 'tracker', 'data.json')))
WARDS = json.load(open(os.path.join(ROOT, 'wards.json')))
NAVY, MUTE, INK, INK2, RED = '#2b5da0', '#5a6069', '#1a1d21', '#3d434b', '#b3001e'
f = lambda n: f'{n:,.0f}'
MON = ['Jan.', 'Feb.', 'March', 'April', 'May', 'June', 'July', 'Aug.', 'Sept.', 'Oct.', 'Nov.', 'Dec.']
def day(iso, year=False):
    d = dt.date.fromisoformat(iso[:10]); return f'{MON[d.month - 1]} {d.day}' + (f', {d.year}' if year else '')
esc = lambda s: str(s).replace('&', '&amp;').replace('<', '&lt;').replace('"', '&quot;')

# yearly federal tables (HUD, Census, FHFA), cut to Chicago by tools/progress/data.py; cards that use them are left out if the file is missing
try: SRC = json.load(open(os.path.join(ROOT, 'progress', 'data', 'src.json')))
except Exception: SRC = {}

# ---------------------------------------------------------------- snapshot (Nov. 9, 2026 analyses)
SNAP = 'Nov. 9, 2026'
# homes in buildings with a demolition permit, by year: counted every morning by tools/tracker/teardowns.py (main) into
# tracker/teardowns.json; the fixed numbers below (through Nov. 6, 2026) are only the fallback when that file is missing
DEMO = dict(zip(range(2013, 2027), [1913, 1607, 1564, 1855, 1417, 1434, 1417, 856, 958, 875, 692, 665, 803, 677])); DEMO_THRU = '2026-11-06'
try:
    _td = json.load(open(os.path.join(ROOT, 'tracker', 'teardowns.json')))
    if _td.get('years', {}).get('2025'): DEMO = {int(y): int(n) for y, n in _td['years'].items()}; DEMO_THRU = _td['through']
except Exception: pass
ROOM_BIN = None   # filled from ROOM_FILLS below
# empty-lot room by ward, in wards.json order, as the five map classes (0 = under 500 ... 4 = 4,000+)
ROOM_CLASS = None
PROJ = [('The 78', 10000, 0, 'Under way', 'Fire stadium broke ground Mar. 3, 2026, to open for the 2028-29 season; no date yet for homes', 'Chicago Sun-Times', 'Mar. 3, 2026', 'https://chicago.suntimes.com/real-estate/2026/03/03/chicago-fire-football-club-breaks-ground-650-million-stadium-78'),
        ('Foundry Park', 3737, 0, 'Under way', 'Broke ground Oct. 21, 2026; phase one has 725+ homes. Council approved its $201.6M property-tax subsidy (TIF) in Sept. 2026', 'Chicago Sun-Times', 'Oct. 21, 2026', 'https://chicago.suntimes.com/real-estate/2026/10/21/foundry-park-developers-break-ground-3-billion-project'),
        ('1901 Project', 5000, 0, 'Under way', 'Construction began summer 2026 with a music hall due in 2028; no date yet for homes', 'Chicago Sun-Times', 'Sept. 18, 2026', 'https://chicago.suntimes.com/real-estate/2026/09/18/music-venue-expected-to-be-centerpiece-of-7-billion-development-project-near-united-center'),
        ('Bronzeville Lakefront', 6800, 0, 'Stalled', 'Partners left; the city gave the owners until June 15, 2026 to file a new infrastructure plan. No public update since', 'The Real Deal', 'May 28, 2026', 'https://therealdeal.com/chicago/2026/05/28/chicago-megadevelopment-owners-considering-project-merge/'),
        ('North Union', 2656, 649, 'Partly built', '920 N. Wells (238 homes) and 868 N. Wells (411) are finished; the next two buildings filed bigger plans in Oct. 2026, not yet approved', 'Chicago YIMBY', 'Oct. 30, 2026', 'https://chicagoyimby.com/2026/10/next-phases-of-north-union-receive-density-bump.html'),
        ('Cabrini-Green (Chicago Housing Authority)', 4080, 0, 'Planning', 'Final plan presented Oct. 2026: about 4,100 homes on 16 sites; rezoning comes next, no date yet for developers', 'Chicago YIMBY', 'Oct. 10, 2026', 'https://chicagoyimby.com/2026/10/city-presents-final-version-of-cabrini-now-framework-plan.html')]
BOND = 'https://www.chicago.gov/content/dam/city/sites/business-and-neighborhood-development-strategy/pdf/Housing-and-Economic-Development-Bond-Book-(Updated-2024.07.03).pdf'
RENT = dict(zip(range(2019, 2027), [1606, 1656, 1574, 1743, 1871, 1964, 2056, 2190]))          # Zillow ZORI, each January
CPI = {int(k): v for k, v in json.load(open(os.path.join(ROOT, 'budget', 'data', 'budget.json')))['cpi'].items()}   # CPI-U annual averages; 2026 = months published so far

# ---------------------------------------------------------------- live numbers
ytd, goal_, l12 = T['ytd'], T['goal'], T['last12']
Y = {y['year']: y for y in T['years']}
THRU = day(T['through']); UPDATED = day(T['updated'], True); TD_THRU = day(DEMO_THRU)
pct = round(100 * ytd['homes'] / ytd['needed_so_far']); vs = round(100 * (ytd['homes'] / ytd['prev'] - 1))
net26 = round((ytd['homes'] - DEMO[2026]) / 10) * 10
behind = ytd['homes'] < ytd['needed_so_far']

def ward_homes():
    """2020 Census homes per ward: block centers from the Bears data, placed in the 2023 wards."""
    B = open(os.path.join(ROOT, 'bears', 'data', 'blocks.bin'), 'rb').read(); n = struct.unpack('<I', B[:4])[0]; o = 4
    xs = struct.unpack('<%dh' % n, B[o:o + 2 * n]); o += 2 * n; ys = struct.unpack('<%dh' % n, B[o:o + 2 * n]); o += 4 * n
    ho = struct.unpack('<%dH' % n, B[o:o + 2 * n])
    lat0, lon0, K = 41.85, -87.65, 111319.49; kx = K * math.cos(math.radians(lat0))
    polys = []
    for w in WARDS:
        for p in w['polys']:
            r = p[0]; X = [c[0] for c in r]; Yc = [c[1] for c in r]; polys.append((w['ward'], r, min(X), max(X), min(Yc), max(Yc)))
    def inside(x, y, r):
        c = False; j = len(r) - 1
        for i in range(len(r)):
            xi, yi = r[i]; xj, yj = r[j]
            if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi) + xi: c = not c
            j = i
        return c
    out = {}
    for i in range(n):
        if not ho[i]: continue
        lon = lon0 + xs[i] * 10 / kx; lat = lat0 + ys[i] * 10 / K
        if not (-87.95 < lon < -87.5 and 41.62 < lat < 42.05): continue
        for w, r, a, b, c, d in polys:
            if a <= lon <= b and c <= lat <= d and inside(lon, lat, r): out[w] = out.get(w, 0) + ho[i]; break
    return out
WH = ward_homes()
WR = sorted(((w['ward'], w['last12'], WH[w['ward']], 1000 * w['last12'] / WH[w['ward']]) for w in T['wards']), key=lambda r: -r[3])
CITY = 1000 * sum(r[1] for r in WR) / sum(r[2] for r in WR); LOW = sum(1 for r in WR if r[3] < 1); ZERO = [r[0] for r in sorted(WR) if r[1] == 0]

# ---------------------------------------------------------------- pieces
SECTIONS = [('homes', 'Homes added'), ('zoning', 'After the zoning vote'), ('room', 'Room to grow'), ('affordable', 'Affordable'),
            ('rents', 'Rents and prices'), ('transit', 'Transit'), ('streets', 'Streets'), ('projects', 'Big projects')]
HATCH = lambda c, bg: f'repeating-linear-gradient(135deg, {c} 0 3px, {bg} 3px 6px)'
SEQ = ['#dbe6f3', '#b3c9e6', '#7fa3d1', '#4f7cb8', '#1f4d8f']

def bars(vals, labels, fmt=f, short=None, refs=(), partial=False, plabel='', top=None, caps=None, aria='', h=210, color=NAVY):
    """Vertical bars with the value on every bar. caps = a hatched cap on each bar (homes torn down); refs = dashed lines."""
    top = top or max(vals) * 1.12; n = len(vals); cols = ''
    for i, v in enumerate(vals):
        last = partial and i == n - 1
        solid = HATCH(color, '#9db9de') if last else color
        ht = lambda x: f'calc(var(--ch) * {x / top:.4f})'
        lab = f'<span class="bv"><span class="vl">{fmt(v)}</span><span class="vs">{(short or fmt)(v)}</span></span>'
        if caps: body = f'<i class="cap" style="height: {ht(caps[i])};"></i><i style="height: {ht(v - caps[i])}; background: {solid};"></i>'
        else: body = f'<i style="height: {ht(v)}; background: {solid}; border-radius: 3px 3px 0 0;"></i>'
        cols += f'<div class="bc">{lab}{body}</div>'
    rf = ''.join(f'<div class="ref" style="bottom: calc(var(--ch) * {v / top:.4f}); border-color: {c};"></div><span class="reft" style="bottom: calc(var(--ch) * {v / top:.4f} + 3px); color: {c};"><span class="vl">{t}</span><span class="vs">{ts}</span></span>' for v, t, ts, c in refs)
    labs = ''.join(f'<span>{l}</span>' for l in labels[:-1]) + f'<span>{labels[-1]}{"<br>" + plabel if partial and plabel else ""}</span>'
    return f'<div class="chart" role="img" aria-label="{esc(aria)}" style="--n: {n}; --ch: {h}px;"><div class="plot">{rf}{cols}</div><div class="xl">{labs}</div></div>'

def hbars(rows, unit='', maxv=None, w=62, me=None):
    m = maxv or max(abs(r[1]) for r in rows)
    return '<div class="hb">' + ''.join(f'<div{(" data-w=" + n[5:]) if n.startswith("Ward ") else ""}{" class=me" if n == me else ""} style="grid-template-columns: {w}px minmax(0, 1fr) auto;"><span>{esc(n)}</span><div class="tr"><i style="width: {max(1.5, 100 * abs(v) / m):.0f}%;"></i></div><b>{t}</b></div>' for n, v, t in rows) + '</div>'

def split(parts, labels=True):
    tot = sum(p[1] for p in parts)
    bar = '<div class="split" aria-hidden="true">' + ''.join(f'<i style="width: {100 * v / tot:.1f}%; background: {c};"></i>' for _, v, c, *_ in parts) + '</div>'
    key = '<div class="key">' + ''.join(f'<span><i style="background: {c};"></i>{esc(n)} · <b>{t[0] if t else f(v)}</b></span>' for n, v, c, *t in parts) + '</div>' if labels else ''
    return bar + key

SHAPES = json.load(open(os.path.join(ROOT, 'shape', 'wardshapes.json')))   # the city's 2023 ward map snapped to one grid, so neighbors share exact borders
def wardmap(color_of, aria, info, w=300):
    """Ward map. info = {ward: text shown when the ward is tapped or hovered}."""
    q = SHAPES['q']; lon0, lon1, lat0, lat1 = -87.945, -87.52, 41.64, 42.03; k = math.cos(math.radians(41.85)); sc = w / ((lon1 - lon0) * k); h = round((lat1 - lat0) * sc)
    d = ''
    for wd, rings in SHAPES['wards'].items():
        path = ''.join('M' + ' '.join(f'{(r[i] * q - lon0) * k * sc:.1f},{(lat1 - r[i + 1] * q) * sc:.1f}' for i in range(0, len(r), 2)) + 'Z' for r in rings)
        d += f'<path d="{path}" fill="{color_of(int(wd))}" data-w="{wd}" data-t="{esc(info[int(wd)])}" tabindex="0" role="button" aria-label="Ward {wd}: {esc(info[int(wd)])}"/>'
    return (f'<svg class="wmap" viewBox="0 0 {w} {h}" role="group" aria-label="{esc(aria)}">{d}</svg>'
            '<p class="winfo" aria-live="polite">Tap or point at a ward to see its numbers.</p>')
def goal(title, text, label=None, url=None, none=False):
    """What the section is measured against: a city program with a target, or a plain 'no official target'."""
    link = f' <a href="{url}" target="_blank" rel="noopener">{label} ›</a>' if url else ''
    return f'<section class="card pad goalc"><span class="tag{" none" if none else ""}">{"No official target" if none else "The official goal"}</span><h2>{title}</h2><p class="sub">{text}{link}</p></section>'

def tiles(items, cols=4):
    return f'<section class="strip c{cols}">' + ''.join(f'<div class="card tile"><b>{b}</b><span>{s}</span></div>' for b, s in items) + '</section>'
def card(title, cap, body, cls=''):
    hd = f'<div class="hd"><h2>{title}</h2>' + (f'<p class="cap">{cap}</p>' if cap else '') + '</div>' if title else ''
    return f'<section class="card pad {cls}">{hd}{body}</section>'
def key(items): return '<div class="key">' + ''.join(f'<span><i style="background: {c};{x}"></i>{t}</span>' for t, c, x in items) + '</div>'
def meter(p): return f'<div class="meter" role="img" aria-label="{p} percent of the homes needed by now"><i style="width: {min(100, p)}%;"></i></div>'
def table(head, rows, right=(), cls=''):
    th = ''.join(f'<th{" class=n" if i in right else ""}>{h}</th>' for i, h in enumerate(head))
    tr = ''.join('<tr>' + ''.join(f'<td{" class=n" if i in right else ""} data-l="{esc(re.sub("<[^>]+>", "", head[i]))}">{c}</td>' for i, c in enumerate(r)) + '</tr>' for r in rows)
    return f'<div class="tw"><table class="{cls}"><thead><tr>{th}</tr></thead><tbody>{tr}</tbody></table></div>'

def spark(vals, partial=False, rng=None):
    m = max(vals); out = ''
    for i, v in enumerate(vals):
        last = i == len(vals) - 1
        bg = HATCH(NAVY, '#fff') if (partial and last) else (NAVY if last else '#c5d4ea')
        out += f'<i style="height: {max(6, round(100 * v / m))}%; background: {bg};"></i>'
    return f'<div class="spark" aria-hidden="true"><div>{out}</div><p><span>{rng[0]}</span><span>{rng[1]}</span></p></div>'
def minisplit(parts, cap):
    tot = sum(v for v, _ in parts)
    return '<div class="spark" aria-hidden="true"><div class="ms">' + ''.join(f'<i style="width: {100 * v / tot:.1f}%; background: {c};"></i>' for v, c in parts) + f'</div><p><span>{cap}</span></p></div>'

# ---------------------------------------------------------------- page shell
HEAD = open(os.path.join(ROOT, 'wards', 'index.html')).read()
HEADER = re.search(r'<header class="sc-head">.*?</header>', HEAD, flags=re.S).group(0).replace('<a href="/wards/" aria-current="page">', '<a href="/wards/">')
assert 'Progress<svg' in HEADER, 'the shared header needs the Progress menu'
def header(slug):
    h = HEADER.replace('aria-expanded="false">Progress<svg', 'aria-expanded="false" aria-current="page">Progress<svg')
    href = '/progress/' + (slug + '/' if slug else '')
    return h.replace(f'<a href="{href}">', f'<a href="{href}" aria-current="page">', 1)
def pills(slug):
    return ('<nav class="pills" aria-label="Progress sections"><a class="back" href="/progress/">‹ Progress</a>'
            + ''.join(f'<a href="/progress/{s}/"{" aria-current=page" if s == slug else ""}>{t}</a>' for s, t in SECTIONS) + '</nav>')
def page(slug, title, desc, main):
    path = '/progress/' + (slug + '/' if slug else '')
    return f'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{esc(title)} · Progress · Shape Chicago</title>
<meta name="description" content="{esc(desc)}">
<meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(desc)}">
<meta property="og:image" content="https://shape-chicago.hd9bt6x5mn.workers.dev/shape/art/og-progress.jpg">
<meta name="twitter:card" content="summary_large_image">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Instrument+Sans:wght@400;500;600;700&display=swap" rel="stylesheet">
<link rel="stylesheet" href="/shape/shape.css">
<link rel="stylesheet" href="/progress/progress.css">
</head>
<body class="pg">
{header(slug)}
<main>
{main}
</main>
<footer class="sc-foot" data-sc-foot>Not affiliated with the City of Chicago, CTA, Metra or Pace.</footer>
<script src="/shape/shape.js"></script>
<script>
/* "In N days" on the decisions coming up */
/* ward maps: point at or tap a ward (or a ward in the lists beside it) */
document.querySelectorAll(".mapr").forEach(box => {{
  const info = box.querySelector(".winfo"), svg = box.querySelector(".wmap"); if (!svg) return; let pinned = null;
  const show = w => {{ const p = svg.querySelector('path[data-w="' + w + '"]'); if (!p) return;
    svg.querySelectorAll("path.on").forEach(e => e.classList.remove("on")); box.querySelectorAll(".hb .on").forEach(e => e.classList.remove("on"));
    p.classList.add("on"); svg.appendChild(p); box.querySelectorAll('.hb [data-w="' + w + '"]').forEach(e => e.classList.add("on"));
    info.innerHTML = "<b>Ward " + w + "</b> · " + p.dataset.t + ' · <a href="/wards/#' + w + '">Ward ' + w + "’s record ›</a>"; }};
  const over = e => {{ const t = e.target.closest("[data-w]"); if (t && pinned === null) show(t.dataset.w); }};
  const pick = e => {{ const t = e.target.closest("[data-w]"); if (!t || e.target.closest("a")) return; pinned = t.dataset.w; show(pinned); }};
  box.addEventListener("pointerover", over); box.addEventListener("focusin", over); box.addEventListener("click", pick);
  box.addEventListener("keydown", e => {{ if (e.key === "Enter" || e.key === " ") {{ pick(e); if (e.target.matches("path")) e.preventDefault(); }} }});
}});
document.querySelectorAll("ol.dl li[data-date]").forEach((e, i, all) => {{ const past = new Date(e.dataset.date + "T23:59:59") < Date.now(), next = !past && (i === 0 || new Date(all[i - 1].dataset.date + "T23:59:59") < Date.now());
  e.classList.add(past ? "past" : next ? "next" : "later"); e.querySelector(".st").textContent = past ? "Date passed" : next ? "Next" : ""; }});
(function(){{ const sel = document.getElementById("zipSel"), out = document.getElementById("zipOut"); if (!sel) return;
  const D = JSON.parse(document.getElementById("zipData").textContent), usd = v => v == null ? "–" : "$" + v.toLocaleString("en-US"), BR = ["Studio", "One bedroom", "Two bedrooms", "Three bedrooms", "Four bedrooms"];
  const show = () => {{ const d = D[sel.value]; if (!d) return; const up = Math.round(100 * (d.r[2] / d.r19 - 1));
    out.innerHTML = '<div class="facts">' + d.r.map((v, i) => "<div><b>" + usd(v) + "</b><span>" + BR[i] + ", fiscal 2027</span></div>").join("") + "</div>"
      + '<p class="sub" style="margin-top:12px">A two-bedroom in ' + sel.value + " was figured at " + usd(d.r19) + " for fiscal 2019, so the figure is " + (up >= 0 ? "up " : "down ") + Math.abs(up) + "% in eight years."
      + (d.p == null ? " There is no house price index for this ZIP code." : " House prices there " + (d.p >= 0 ? "rose " : "fell ") + Math.abs(d.p) + "% from 2019 to 2025.") + "</p>"; }};
  sel.addEventListener("change", show); show(); }})();
document.querySelectorAll("[data-until]").forEach(e => {{ const d = Math.ceil((new Date(e.dataset.until + "T12:00:00") - Date.now()) / 864e5); e.textContent = d > 1 ? "In " + d + " days" : d === 1 ? "Tomorrow" : d === 0 ? "Today" : "Passed"; }});
</script>
</body>
</html>
'''
def top(slug, name, h1, thru):
    return f'<div class="top"><p class="eyebrow"><a href="/progress/">Progress</a> <span aria-hidden="true">›</span> {name}</p><h1>{h1}</h1><p class="fine">{thru}</p></div>'
def bottom(slug, note, src):
    i = [s for s, _ in SECTIONS].index(slug); prv = SECTIONS[i - 1] if i else None; nxt = SECTIONS[i + 1] if i + 1 < len(SECTIONS) else None
    nav = '<nav class="pn" aria-label="More sections">' + (f'<a class="card" href="/progress/{prv[0]}/"><span>Previous</span><b>‹ {prv[1]}</b></a>' if prv else '<span></span>') + (f'<a class="card nx" href="/progress/{nxt[0]}/"><span>Next</span><b>{nxt[1]} ›</b></a>' if nxt else '') + '</nav>'
    return f'<p class="fine note">{note}</p>{nav}<p class="fine src"><b>Sources:</b> {src}</p>'

# ---------------------------------------------------------------- Homes permitted (live)
YEARS = list(range(2016, 2027))
def yearchart(net, h=210):
    vals = [ytd['homes'] if y == 2026 else Y[y]['homes'] for y in YEARS]
    return bars(vals, [str(y) if True else '' for y in YEARS], short=lambda v: f'{v / 1000:.1f}k', top=11000, partial=True, plabel='so far', h=h,
                caps=[DEMO[y] for y in YEARS] if net else None,
                refs=[(goal_['close'], f'{f(goal_["close"])} a year closes the gap by 2041', f'{f(goal_["close"])} closes the gap', RED), (goal_['hold'], f'{f(goal_["hold"])} keeps it from growing', f'{f(goal_["hold"])} holds it', MUTE)],
                aria=f'Homes permitted each year, 2016 to 2026: {f(Y[2016]["homes"])} in 2016, {f(Y[2025]["homes"])} in 2025 and {f(ytd["homes"])} so far in 2026. Every year is below the {f(goal_["close"])} a year needed.')
PACE = f'<span class="chip {"bad" if behind else "good"}">{"▼ Behind pace" if behind else "▲ On pace"}</span>'
def homes():
    d26 = round(DEMO[2026] / 10) * 10
    strip = ('<section class="strip c4 eq">'
             f'<div class="card tile"><b>{f(ytd["homes"])}</b><span>homes permitted this year, through {THRU}</span></div>'
             f'<div class="card tile"><b><i>−</i> about {f(d26)}</b><span>homes in buildings torn down (estimate, through {TD_THRU})</span></div>'
             f'<div class="card tile sum"><b><i>=</i> about {f(net26)}</b><span>net gain: homes permitted minus homes torn down</span></div>'
             f'<div class="card tile">{PACE}{meter(pct)}<span><b class="in">{pct}%</b> of the {f(ytd["needed_so_far"])} homes needed by {THRU} · <b class="in">{"▼" if vs < 0 else "▲"} {abs(vs)}%</b> permitted vs. this date last year</span></div></section>')
    n25 = round((Y[2025]['homes'] - DEMO[2025]) / 10) * 10
    c1 = card('Homes permitted each year, and what was left after teardowns', 'The whole bar is homes permitted. The hatched cap is homes in buildings that got a demolition permit that year; the solid part is the gain.',
              yearchart(True, 230) + key([('Net gain', NAVY, ''), ('Homes in buildings torn down (estimate)', HATCH('#8a9099', '#fff'), ' border: 1px solid #c9ced6; box-sizing: border-box;'), ('2026 so far', HATCH(NAVY, '#9db9de'), '')])
              + f'<p class="call">In 2025: <b>{f(Y[2025]["homes"])}</b> permitted − about <b>{f(round(DEMO[2025] / 100) * 100)}</b> torn down = about <b>{f(n25)}</b> more homes. Teardowns are down by {"more than half" if DEMO[2025] < 0.45 * DEMO[2013] else "about half" if DEMO[2025] < 0.6 * DEMO[2013] else "a third or more"} since 2013, when about {f(round(DEMO[2013] / 100) * 100)} homes were in torn-down buildings.</p>')
    lostc = ('<section class="card pad" id="lost"><div class="hd"><h2>Other ways homes are lost or gained</h2><p class="cap">These are not in the net figure above: the records only let us count part of each.</p></div><div class="facts">'
             '<div><b>At least 525</b><span>buildings lost homes in a renovation since 2019, at least 688 homes in all. 374 became single-family homes; 331 had been two-flats</span></div>'
             '<div><b>At least 281</b><span>buildings gained homes in a renovation since 2019, at least 379 homes</span></div>'
             '<div><b>3,767</b><span>homes and rooms are registered with the city as short-term rentals</span></div>'
             '<div><b>About 1 in 4</b><span>demolition permits mention fire damage, a court order or a vacant building</span></div></div></section>')
    rows = ''
    for y in range(2019, 2027):
        r = Y[y]; v = ytd['homes'] if y == 2026 else r['homes']; fi, ex = r['finished'], r['expired']; bu = max(0, v - fi - ex); p = lambda x: 100 * x / v
        rows += (f'<div><span class="y">{y}</span><div class="st"><i style="width: {p(fi):.1f}%; background: {NAVY};"></i><i style="width: {p(bu):.1f}%; background: #9db9de;"></i><i style="width: {p(ex):.1f}%; background: #c9ced6;"></i></div>'
                 f'<span class="v"><b>{round(p(fi))}%</b> finished<span class="vl"> of {f(v)}</span></span></div>')
    r21, r22, r24 = Y[2021], Y[2022], Y[2024]; exp = round(100 * (r21['expired'] + r22['expired']) / (r21['homes'] + r22['homes']))
    c2 = card('A permit is not a finished home', 'Of the homes permitted each year, how many are finished today.',
              f'<div class="fin" role="img" aria-label="Share of each year\'s permitted homes that are finished today, 2019 to 2026">{rows}</div>' + key([('Finished', NAVY, ''), ('Still under way', '#9db9de', ''), ('Permit expired', '#c9ced6', '')])
              + f'<p class="sub">Building takes years: <b>{round(100 * r22["finished"] / r22["homes"])}%</b> of the homes permitted in 2022 are done, and <b>{round(100 * r24["finished"] / r24["homes"])}%</b> of 2024’s. About {exp}% of the homes permitted in 2021 and 2022 had the permit expire before the city recorded them as finished.</p>')
    BIN = [(6, NAVY, '6 or more'), (3, '#5f8fcc', '3–6'), (1, '#a9c3e6', '1–3'), (0.0001, '#d9e4f4', 'Under 1'), (-1, '#eceef1', 'None')]
    rate = {r[0]: r[3] for r in WR}; col = lambda w: next(c for t, c, _ in BIN if rate[w] >= t)
    raw = sorted(WR, key=lambda r: -r[1])
    info = {r[0]: f'{f(r[1])} homes permitted in the last 12 months · {r[3]:.1f} for every 1,000 homes there' for r in WR}
    allw = table(['Ward', 'Homes permitted, last 12 months', 'Per 1,000 homes there', 'Homes in the ward (2020 Census)'], [[f'<a href="/wards/#{r[0]}">Ward {r[0]}</a>', f(r[1]), f'{r[3]:.1f}', f(r[2])] for r in raw], right=(1, 2, 3))
    c3 = card('Where the homes are going', 'Homes permitted in the last 12 months, by ward. Wards differ in size, so the map shows homes per 1,000 already there.',
              '<div class="mapr"><div class="mp">' + wardmap(col, 'Map of Chicago’s 50 wards shaded by homes permitted per 1,000 existing homes in the last 12 months. The highest rates are near downtown and on the Near West and Near Northwest sides.', info)
              + key([(t, c, '') for _, c, t in BIN]) + '</div><div class="lists"><div><h3>Most homes permitted</h3>' + hbars([(f'Ward {r[0]}', r[1], f(r[1])) for r in raw[:6]])
              + '</div><div><h3>Most for its size <span>(per 1,000 homes)</span></h3>' + hbars([(f'Ward {r[0]}', r[3], f'{r[3]:.0f}') for r in WR[:6]])
              + f'</div><p class="call"><b>{LOW} of 50 wards</b> permitted less than 1 new home for every 1,000 they have. {len(ZERO)} permitted none{" (Wards " + ", ".join(map(str, ZERO)) + ")" if ZERO else ""}. The city as a whole: <b>{CITY:.1f}</b> per 1,000.</p></div></div>'
              + f'<details class="all"><summary>All 50 wards</summary>{allw}</details>')
    c4 = ('<section class="strip c2"><div class="card tile row"><b>580</b><span>coach houses and basement homes have cleared the city’s first step since citywide rules began this spring. Cleared is not built.</span></div>'
          '<a class="card tile row go" href="/tracker/"><span><b class="t">Every project, ward and zoning approval</b>Search the full list by address or ward</span><em>Open ›</em></a></section>')
    g = goal('The city has not set a citywide target for new homes', f'The pace on this page is our own yardstick: Chicago’s share of the region’s housing shortage, closed by 2041 ({f(goal_["close"])} homes a year). The nearest official plan is the 2024–2028 Housing and Economic Development Bond, which projects 600 to 1,000 affordable rental homes, 750 homes on empty lots in neighborhoods and 600 or more mixed-income homes every five years from a new city fund.', 'The bond plan', BOND, none=True)
    note = ('The pace is the housing simulator’s goal, an estimate: Chicago’s share of the regional shortage, closed by 2041. Over 2010–2025 our permit total is within 1% of the Census permit survey; single years differ by 8% on average. '
            f'Torn-down homes are an estimate, counted every morning through the newest demolition permit ({TD_THRU}): each permit is matched to the building at its address in the city’s 2013 footprints (the one its point falls in, or the nearest within 12 m) to read how many homes it held. Permits for only a garage or porch are left out, and so are matches to a building much bigger than the one the permit describes. Looser or tighter matching moves a year’s figure by about a tenth. Most teardowns are followed by a new building, which the permit count includes. '
            'Renovation figures come from permits whose wording states the change (for example “convert from 3 units to 2”), leaving out permits that expired or were cancelled. We catch roughly half of the cuts and fewer of the additions, so both are floors, and neither is subtracted or added in the net figure. '
            'Homes per ward come from the 2020 Census. “Finished” means the city marked the permit complete or issued a certificate of occupancy. Coach house applications are counted from Mar. 31, 2026; the 2021–2025 pilot cleared 907.')
    peers = ''
    C = (SRC.get('bps') or {}).get('cities') or {}
    if 'Chicago' in C:
        rate = lambda c, y='2025': 1000 * C[c][y]['u'] / C[c][y]['pop']
        rk = sorted(C, key=lambda c: -rate(c)); pos = rk.index('Chicago') + 1; chi = C['Chicago']
        sub = (SRC['bps'].get('suburbs') or {}); st = sorted(sub.items(), key=lambda kv: -kv[1]['2025']['u'])[:6]
        peers = card('Chicago next to other big cities', 'Homes permitted in 2025 for every 1,000 residents, in Chicago and 12 of the other 14 largest U.S. cities.',
                     '<div class="pair"><div>' + hbars([(c, rate(c), f'{rate(c):.1f}') for c in rk], w=96, me='Chicago')
                     + f'</div><div><p class="call" style="margin-top:0">Chicago permitted <b>{rate("Chicago"):.1f}</b> homes per 1,000 residents in 2025, {"the fewest" if pos == len(rk) else f"number {pos}"} of these {len(rk)} cities. {rk[0]} permitted <b>{rate(rk[0]):.1f}</b>.</p>'
                     + '<h3>Chicago by itself</h3>' + table(['', '2015', '2019', '2022', '2025'], [['Homes permitted'] + [f(chi[str(y)]['u']) for y in (2015, 2019, 2022, 2025)]], right=(1, 2, 3, 4))
                     + '<h3>Suburbs that permitted the most in 2025</h3>' + hbars([(n, v['2025']['u'], f(v['2025']['u'])) for n, v in st], w=96) + '</div></div>')
        note += ' The city comparison uses the Census Building Permits Survey’s yearly place file and the population it carries for each place; Jacksonville, Indianapolis and Charlotte are filed under their county governments there and are left out. New York is its five boroughs added together. Suburbs are Illinois places of 25,000 or more people in the Chicago metro area.'
    h1 = f'So far this year: {f(ytd["homes"])} homes permitted, about {f(d26)} torn down, a net gain of about {f(net26)}.'
    return page('homes', 'Homes added', h1, top('homes', 'Homes added', h1, f'Permits through {THRU}, 2026, updated every morning · teardowns through {TD_THRU}') + strip + c1 + c2 + c3 + peers + lostc + c4 + g
                + bottom('homes', note, 'City of Chicago building permits (new construction, demolition and renovation); City of Chicago 2013 building footprints; Census Building Permits Survey; 2020 Census housing counts by block; City of Chicago ADU pre-approval applications and shared housing registrations.'))

# ---------------------------------------------------------------- the snapshot sections
def zoning():
    h1 = 'At least 46% of new homes went up on land the City Council had rezoned in the five years before. Counting big-site plans, it is about two-thirds.'
    st = tiles([('At least 46%', 'of the 69,927 homes permitted 2014–2025 were on land rezoned in the 5 years before'), ('56%', 'were in big-site plans (planned developments), which the Council approves one by one'),
                ('53% vs. 12%', 'homes in buildings of 5+ vs. 1–4 homes that were on recently rezoned land'), ('3 in 10', 'zoning changes for a new building had a building permit within a year; 4 in 10 within two')])
    ch = bars([31, 20, 12, 35, 45], ['2021', '2022', '2023', '2024', '2025'], fmt=lambda v: f'{v}%', top=60, h=190, aria='Share of zoning changes for a new building that had a building permit within 12 months, by the year the change passed: 31% for 2021, 20% for 2022, 12% for 2023, 35% for 2024 and 45% for 2025.')
    tb = table(['Year passed', 'Zoning changes for a new building', 'Permit within 12 months', 'Within 24 months', 'Homes permitted so far on those sites', 'Of those, finished'],
               [['2021', '42', '31%', '43%', '4,926', '4,142'], ['2022', '51', '20%', '35%', '2,073', '1,300'], ['2023', '57', '12%', '33%', '1,320', '374'], ['2024', '63', '35%', '46%', '1,327', '124'],
                ['2025', '71', '45%', '<span class="tbd">too early to tell</span>', '721', '28'], ['2026', '57', '<span class="tbd">too early to tell</span>', '<span class="tbd">too early to tell</span>', '97', '0']], right=(1, 2, 3, 4, 5), cls='stack')
    c1 = card('What followed each year’s votes', 'Zoning changes passed for a new residential building, by the year they passed: the share with a building permit within 12 months. Our copies of the applications start in 2021, so earlier years can’t be counted yet.', ch + tb)
    c2 = card('This Council term, since May 2023', '787 zoning changes sorted so far by what the new zoning allows on the lot.',
              split([('More homes per lot', 468, NAVY), ('Same', 217, '#9db9de'), ('Fewer', 72, '#c98a8a'), ('Big-site plans', 30, '#c9ced6')])
              + '<p class="sub">385 more, a third of the term’s total, aren’t sorted yet because the before-and-after zoning couldn’t be read from the paperwork. “More homes per lot” compares what the zoning allows, not what was proposed.</p>')
    c3 = card('Newest approvals', 'Passed by the City Council on Oct. 14, 2026.', hbars([('537–547 W Oak St', 78, '78 homes'), ('2648–2658 W Lawrence Ave', 37, '37 homes'), ('1745–1759 N Cicero Ave', 36, '36 homes'), ('3244–3250 W Bryn Mawr Ave', 30, '30 homes')], w=190)
              + '<p class="sub"><a href="/wards/">See every zoning change in your ward ›</a></p>')
    note = ('A zoning change is the Council changing what can be built on a lot. Why “at least”: the zoning map keeps only the latest change on each site, so earlier ones are lost and the true share is higher. '
            'The table counts the 341 zoning changes since 2021 (of 2,093) whose application clearly describes a new residential building and no conversion of an existing one. A permit counts if it is for new construction inside the rezoned area on the zoning map, or at the same address, on or after the vote. '
            'Among those that got a permit, half got it within 9 months. For 2025, the 12-month figure covers the 60 passed by early November 2025.')
    return page('zoning', 'After the zoning vote', h1, top('zoning', 'After the zoning vote', h1, f'Permits through Nov. 6, 2026 · zoning votes through Oct. 14 · checked {SNAP}') + st + c1 + '<section class="strip c2 cards">' + c2 + c3 + '</section>'
                + goal('The city has no target for how fast a rezoning turns into homes', 'Its Cut the Tape initiative, begun in 2024, is the program meant to speed approvals and permits. It reports steps taken, not a number to hit.', 'Cut the Tape', 'https://www.chicago.gov/city/en/depts/mayor/press_room/press_releases/2025/may/Cut-the-Tape-Year-of-Progress.html', none=True)
                + bottom('zoning', note, 'City Clerk legislation records and zoning applications; Chicago zoning map (the ordinance number and date on each district); City of Chicago building permits.'))

ROOM_FILLS = ['#7fa3d1', '#7fa3d1', '#1f4d8f', '#7fa3d1', '#4f7cb8', '#1f4d8f', '#4f7cb8', '#4f7cb8', '#1f4d8f', '#4f7cb8', '#7fa3d1', '#b3c9e6', '#b3c9e6', '#b3c9e6', '#4f7cb8', '#1f4d8f', '#1f4d8f', '#b3c9e6', '#b3c9e6', '#1f4d8f', '#4f7cb8', '#4f7cb8', '#b3c9e6', '#1f4d8f', '#7fa3d1', '#7fa3d1', '#1f4d8f', '#1f4d8f', '#4f7cb8', '#b3c9e6', '#dbe6f3', '#b3c9e6', '#dbe6f3', '#4f7cb8', '#dbe6f3', '#b3c9e6', '#4f7cb8', '#dbe6f3', '#b3c9e6', '#b3c9e6', '#b3c9e6', '#dbe6f3', '#b3c9e6', '#b3c9e6', '#b3c9e6', '#b3c9e6', '#b3c9e6', '#b3c9e6', '#7fa3d1', '#b3c9e6']
ROOM_BAND = dict(zip(SEQ, ['under 500', '500 to 1,000', '1,000 to 2,000', '2,000 to 4,000', 'more than 4,000']))
def room():
    h1 = 'Today’s zoning allows about 110,000 more homes on empty private lots outside downtown. Nearly everything else it allows would mean replacing a building.'
    fill = {w['ward']: ROOM_FILLS[i] for i, w in enumerate(WARDS)}
    lede = '<p class="lede">This counts homes per lot only. Height limits, parking rules and what is worth building all cut the real number, and at the pace lots are actually built on, most of this room stays unused.</p>'
    c1 = card('On paper, zoning outside downtown allows about 484,000 more homes', 'Where they would go:',
              split([('Empty lots', 110, NAVY, '110,000'), ('Lots with a shop or other building, no homes', 171, '#9db9de', '171,000'), ('Lots that already have homes', 203, '#d9e4f4', '203,000')])
              + '<p class="call">Only the first group could be built without replacing or adding to a building that stands there now.</p>')
    st = tiles([('33,327', 'empty private lots outside downtown'), ('1,525', 'homes of empty-lot room in the typical ward'), ('About 1 in 4', 'lots with homes hold more homes than today’s rules would let anyone build'), ('6 in 10', 'of those are over by one home, such as a two-flat on a single-family lot')])
    c2 = card('Room on empty lots, by ward', 'Homes today’s zoning allows on empty private lots.',
              '<div class="mapr"><div class="mp">' + wardmap(lambda w: fill[w], 'Map of Chicago’s 50 wards shaded by how many homes today’s zoning allows on empty lots. Most room is on the South and West sides.', {w: 'room for ' + ROOM_BAND[fill[w]] + ' homes on empty lots' for w in fill})
              + key([(t, c, '') for t, c in zip(['Under 500', '500–1,000', '1,000–2,000', '2,000–4,000', '4,000+'], SEQ)]) + '</div><div class="lists"><div><h3>Most room</h3>'
              + hbars([('Ward 28', 6979, '6,979'), ('Ward 20', 6948, '6,948'), ('Ward 16', 6557, '6,557'), ('Ward 27', 5334, '5,334'), ('Ward 24', 5201, '5,201')])
              + '</div><div><h3>Least room</h3>' + hbars([('Ward 31', 486, '486'), ('Ward 35', 428, '428'), ('Ward 33', 352, '352'), ('Ward 38', 334, '334'), ('Ward 42', 0, '0')], maxv=6979)
              + '</div><p class="call">Ward 42 shows no empty-lot room because nearly all of it is downtown zoning, which is counted apart.</p></div></div>')
    c3 = card('Downtown is counted apart, and roughly', '', '<p class="sub">Downtown zoning limits floor area, not homes per lot. Unused floor area there works out to somewhere between <b>46,000 and 80,000</b> more homes at 900 sq ft each. Building heights and lot sizes are missing for hundreds of downtown lots, so this is a rough range and those lots are left out.</p>')
    note = ('For each lot: the homes its zoning district allows (lot size ÷ the district’s minimum lot area per home) minus the homes there now. Lot sizes are the Cook County Assessor’s; 51,854 of the 110,000 are on lots with a measured size and the rest assume a standard 3,125 sq ft lot. '
            'City-owned and other tax-exempt land, railroads, planned developments, manufacturing districts and parks are left out. Two-flats that an exception allows in some single-family districts are counted as over.')
    return page('room', 'Room to grow', h1, top('room', 'Room to grow', h1, f'Zoning map and Assessor lots, 2026 · checked {SNAP}') + lede + c1 + st + c2 + c3 + goal('No city program sets a target for building on empty lots', 'This section is context for the others: it shows how much could be built without changing any zoning.', none=True)
                + bottom('room', note, 'Chicago zoning map; Chicago Zoning Ordinance §17-2-0303 and downtown floor-area rules; Cook County Assessor parcels and characteristics; City of Chicago building footprints.'))

AFF_WARD = {1: 490, 2: 202, 3: 3921, 4: 2390, 5: 436, 6: 382, 7: 280, 8: 308, 9: 885, 10: 257, 11: 287, 12: 30, 13: 87, 14: 239, 15: 196, 16: 766, 17: 308, 18: 250, 19: 0, 20: 1877, 21: 462, 22: 180, 23: 89, 24: 1063, 25: 359,
            26: 1212, 27: 3427, 28: 2051, 29: 480, 30: 0, 31: 412, 32: 344, 33: 187, 34: 242, 35: 199, 36: 175, 37: 133, 38: 131, 39: 477, 40: 110, 41: 85, 42: 34, 43: 68, 44: 333, 45: 208, 46: 1016, 47: 229, 48: 842, 49: 1178, 50: 233}   # homes on the city list (dated Dec. 30, 2024) by 2023 ward
def affordable():
    h1 = 'The city’s list shows 29,550 affordable rental homes in 598 buildings. It was last updated in December 2024.'
    st = tiles([('29,550', 'homes on the list, which the city says is not complete'), ('About 1 in 3', 'are for seniors (10,759 homes)'), ('156 buildings', 'with 1,727 homes are there because the city requires affordable homes in bigger new buildings (the ARO)'), ('Not counted', 'public housing (CHA) and rent vouchers')])
    BIN = [(2000, SEQ[4], '2,000 or more'), (1000, SEQ[3], '1,000–2,000'), (250, SEQ[2], '250–1,000'), (1, SEQ[1], 'Under 250'), (0, '#eceef1', 'None')]
    col = lambda w: next(c for t, c, _ in BIN if AFF_WARD[w] >= t)
    rk = sorted(AFF_WARD.items(), key=lambda r: -r[1])
    allw = table(['Ward', 'Homes on the city’s list'], [[f'<a href="/wards/#{w}">Ward {w}</a>', f(v)] for w, v in rk], right=(1,))
    c1 = card('Where the listed homes are', 'Homes on the city’s list, by ward.',
              '<div class="mapr"><div class="mp">' + wardmap(col, 'Map of Chicago’s 50 wards shaded by affordable rental homes on the city’s list. The most are on the Near South, Near West and West sides.', {w: f'{f(v)} homes on the city’s list' for w, v in AFF_WARD.items()})
              + key([(t, c, '') for _, c, t in BIN]) + '</div><div class="lists"><div><h3>Most homes on the list</h3>' + hbars([(f'Ward {w}', v, f(v)) for w, v in rk[:6]])
              + '</div><div><h3>Fewest</h3>' + hbars([(f'Ward {w}', v, f(v)) for w, v in rk[-6:]], maxv=rk[0][1])
              + '</div><p class="call">Wards 19 and 30 have no building on the list. That is not the same as no affordable housing.</p></div></div>'
              + f'<details class="all"><summary>All 50 wards</summary>{allw}</details>')
    c2 = card('Is the number growing?', '', '<p class="sub">The city’s list cannot say. It gives each building’s address and number of homes but not the year it opened, and the city has published one version of it, dated Dec. 30, 2024. Until it publishes another, there is no second point to compare.</p>')
    H = SRC.get('hud') or {}
    if '2025' in H:
        ys = sorted(int(y) for y in H); a, b = H[str(ys[0])], H[str(ys[-1])]; other = b['all'] - b.get('hcv', 0) - b.get('s8', 0) - b.get('ph', 0)
        ch = round(100 * (b['all'] / a['all'] - 1)); dv = b['hcv'] - a['hcv']; dp = b['ph'] - a['ph']
        c2 = card(f'Is the number growing? The federal count is {"up" if ch > 0 else "down"} {abs(ch)}% since {ys[0]}', f'Homes in Chicago with federal rent help each year: public housing, rent vouchers and federally subsidized buildings. This is HUD’s yearly count, a different list from the city’s above.',
                  bars([H[str(y)]['all'] for y in ys], [f'’{str(y)[2:]}' for y in ys], short=lambda v: f'{v / 1000:.0f}k', h=170,
                       aria=f'Homes with federal rent help in Chicago each year: {f(a["all"])} in {ys[0]} and {f(b["all"])} in {ys[-1]}.')
                  + f'<h3 style="margin-top:16px">What the {f(b["all"])} homes in {ys[-1]} are</h3>'
                  + split([('Rent vouchers', b['hcv'], NAVY), ('Subsidized private buildings (Section 8)', b['s8'], '#5f8fcc'), ('Public housing', b['ph'], '#9db9de'), ('Senior, disability and other programs', other, '#c9ced6')])
                  + f'<p class="call"><b>{f(a["all"])}</b> homes in {ys[0]}, <b>{f(b["all"])}</b> in {ys[-1]}: {"up" if ch > 0 else "down"} {abs(ch)}%. Rent vouchers {"rose" if dv > 0 else "fell"} by about {f(round(abs(dv) / 100) * 100)}; public housing {"rose" if dp > 0 else "fell"} by about {f(round(abs(dp) / 100) * 100)}.</p>'
                  + '<p class="sub">The city’s own list still cannot show growth: it has no opening dates and one published version (Dec. 30, 2024).</p>')
    g = goal('The 2024–2028 housing bond', 'The city’s Housing and Economic Development Bond plan projects 600 to 1,000 affordable rental homes built or preserved, and 600 or more mixed-income homes every five years from its new Green Social Housing fund. The city has not published a running count against those figures.', 'The bond plan', "https://www.chicago.gov/content/dam/city/sites/business-and-neighborhood-development-strategy/pdf/Housing-and-Economic-Development-Bond-Book-(Updated-2024.07.03).pdf")
    note = ('The list is the Department of Housing’s “Affordable Rental Housing Developments”: buildings the city financed, plus those built under its affordable requirements rule. The city describes it as among the thousands of homes it supports and provides it as a courtesy. '
            'Ward totals place each building by its map location on the 2023 ward map. '
            'The federal count is HUD’s “Picture of Subsidized Households” for Chicago: homes under contract or available in each federal program at the end of each year. A voucher counts as one home wherever it is used. It leaves out buildings financed only with tax credits or city money, so it overlaps the city’s list but is not the same thing.')
    return page('affordable', 'Affordable', h1, top('affordable', 'Affordable', h1, f'City list dated Dec. 30, 2024 · federal count through 2025 · checked {SNAP}') + st + c1 + c2 + g
                + bottom('affordable', note, 'City of Chicago Department of Housing, Affordable Rental Housing Developments (Chicago Data Portal, updated Dec. 30, 2024); 2023 ward boundaries; Housing and Economic Development Bond Book (July 2024); U.S. Department of Housing and Urban Development, Picture of Subsidized Households, 2014–2025.'))

def rents():
    h1 = 'The typical asking rent is $2,311, up 5.7% in a year.'
    ys = list(range(2019, 2027)); real = {y: RENT[y] * CPI[2026] / CPI[y] for y in ys}
    up = round(100 * (RENT[2026] / RENT[2019] - 1)); upr = round(100 * (real[2026] / real[2019] - 1))
    money = lambda v: f'${f(v)}'
    two = ('<div class="pair"><div><h3>As advertised</h3>' + bars([RENT[y] for y in ys], [f'’{str(y)[2:]}' for y in ys], fmt=money, short=lambda v: f'${v / 1000:.1f}k', top=2500, h=170, aria='Typical asking rent each January, 2019 to 2026, as advertised: $1,606 in 2019 rising to $2,190 in 2026.')
           + '</div><div><h3>In 2026 dollars</h3>' + bars([round(real[y]) for y in ys], [f'’{str(y)[2:]}' for y in ys], fmt=money, short=lambda v: f'${v / 1000:.1f}k', top=2500, h=170, color='#5f8fcc',
                                                         aria=f'Typical asking rent each January in 2026 dollars: ${f(real[2019])} in 2019, dipping in 2021 and reaching $2,190 in 2026.') + '</div></div>')
    c1 = card('Typical asking rent each January', 'The same rents twice: as advertised, and after taking out inflation.', two
              + f'<p class="call">Asking rents are up <b>{up}%</b> since January 2019. After inflation, they are up about <b>{upr}%</b>: most of the rise matched prices in general.</p>')
    st = tiles([('$2,311', 'asking rent for a home on the market, Sept. 2026 (Zillow)'), ('$1,440', 'what the typical renter pays, all renters (Census, 2024)'), ('31% vs. 26%', 'rise in asking rents vs. consumer prices, 2019 to 2025'), ('20% fewer', 'houses sold in 2025 than in 2019 (10,369 vs. 12,944)')])
    c2 = card('Sale prices', 'Median sale price in Chicago, not adjusted for inflation.', table(['', '2019', '2021', '2023', '2025', 'Since 2019'],
              [['House', '$230,000', '$295,000', '$284,900', '$320,000', '<b>+39%</b>'], ['Condo', '$260,000', '$288,000', '$280,000', '$329,000', '<b>+27%</b>'], ['2- to 6-flat', '$275,000', '$375,000', '$375,000', '$450,000', '<b>+64%</b>']], right=(1, 2, 3, 4, 5)))
    zc = ''
    SF = SRC.get('safmr') or {}; FH = SRC.get('fhfa') or {}
    Z = sorted(z for z, v in SF.items() if v.get('2027') and v.get('2019') and v['2027'][2] and v['2019'][2])
    if Z:
        two = lambda z, y='2027': SF[z][y][2]
        rk = sorted(Z, key=lambda z: -two(z)); med = sorted(two(z) for z in Z)[len(Z) // 2]
        capz = [z for z in Z if two(z) == two(rk[0])]; below = [z for z in rk if two(z) < two(rk[0])]
        zd = {z: {'r': SF[z]['2027'], 'r19': SF[z]['2019'][2], 'p': (round(100 * (FH[z]['2025'] / FH[z]['2019'] - 1)) if z in FH and '2025' in FH[z] and '2019' in FH[z] else None)} for z in Z}
        zc = card('Rent by ZIP code', 'What the federal government figures a modest home rents for in each Chicago ZIP code, utilities included. It sets these every year to size rent vouchers.',
                  '<div class="zipr"><label for="zipSel">ZIP code</label><select id="zipSel">' + ''.join(f'<option value="{z}"{" selected" if z == "60647" else ""}>{z}</option>' for z in Z) + '</select></div>'
                  + '<div id="zipOut" aria-live="polite"></div>'
                  + f'<script type="application/json" id="zipData">{json.dumps(zd, separators=(",", ":"))}</script>'
                  + '<div class="pair" style="margin-top:18px"><div><h3>Highest two-bedroom figures below the ceiling</h3>' + hbars([(z, two(z), f'${f(two(z))}') for z in below[:6]], w=58, maxv=two(rk[0]))
                  + '</div><div><h3>Lowest</h3>' + hbars([(z, two(z), f'${f(two(z))}') for z in rk[-6:]], w=58, maxv=two(rk[0])) + '</div></div>'
                  + f'<p class="call">The middle Chicago ZIP code’s two-bedroom figure is <b>${f(med)}</b> for fiscal 2027; the lowest is <b>${f(two(rk[-1]))}</b> ({rk[-1]}). <b>{len(capz)}</b> ZIP codes share the top figure, <b>${f(two(rk[0]))}</b>, because HUD caps a ZIP code at 150% of the area-wide figure: {", ".join(sorted(capz))}.</p>')
    note = ('ZIP code rents are HUD’s Small Area Fair Market Rents for fiscal 2027 and 2019: for each ZIP code, the rent plus utilities that 40% of recently rented standard homes come in under. HUD builds them from Census surveys a few years old plus a trend, so they trail the market; no ZIP code can be set above 150% of the metro area’s figure or below the state’s minimum (HUD, fiscal 2027 Small Area Fair Market Rent methodology). ZIP code price changes are the Federal Housing Finance Agency’s yearly house price index, which follows repeat sales and refinancings of the same homes and is published only where there are enough of them. '
            'Asking rent is Zillow’s Observed Rent Index for the city: rents advertised for homes on the market, all sizes, smoothed. It runs above what sitting tenants pay. The 2026-dollar figures use the national Consumer Price Index (yearly averages; 2026 is the average of the months published so far, so the last step is an estimate). '
            'Sale prices are the median of what sold that year, not the same homes. They come from the Cook County Assessor’s sales in Chicago, leaving out sales under $10,000, resales within a year, unusual deeds and multi-parcel sales.')
    return page('rents', 'Rents and prices', h1, top('rents', 'Rents and prices', h1, f'Rents through Sept. 2026 · sales through 2025 · checked {SNAP}') + st + c1 + zc + c2 + goal('No city program sets a target for rents or sale prices', 'Rents and prices are the result the other sections add up to, so this section is a readout, not a scorecard.', none=True)
                + bottom('rents', note, 'Zillow Observed Rent Index (city of Chicago); Census American Community Survey 2024; Cook County Assessor parcel sales; Bureau of Labor Statistics CPI-U; HUD Small Area Fair Market Rents, fiscal 2019 and 2027; Federal Housing Finance Agency house price index by ZIP code.'))

PMO = 'https://nita.illinois.gov/uploads/files/general/Transit-Funding/Improving-the-System/2026-06-Report-on-Project-Management-Oversight-1.pdf'
# name, budget, status, chip class, where it stands, due, source label, source date, url.  Budgets and percentages: NITA's June 2026 oversight report (budgets as of March 2026, status as of late May).
CTA_PROJ = [('Red Line Extension', '$5.75 billion', 'Under way', 'go', '5.5 miles and four new stations from 95th to 130th. Broke ground Apr. 24, 2026; 20% complete in June', 'In service 2030', 'CTA', 'Apr. 24, 2026', 'https://www.transitchicago.com/cta-celebrates-start-of-the-historic-red-line-extension-project-by-breaking-ground-at-the-future-michigan-avenue-station/'),
            ('Red and Purple Modernization, phase one', '$2.2 billion', 'Nearly done', 'good', 'Two miles of rebuilt track, four rebuilt stations and the bypass at Belmont. Builders reported the main work finished July 1, 2026', 'Final sign-off Nov. 2026 to April 2027', 'Construction Dive', 'July 6, 2026', 'https://www.constructiondive.com/news/fluor-walsh-substantial-completion-chicago-red-line/824503/'),
            ('State/Lake station rebuild', 'Not in the report', 'Under way', 'go', 'The Loop station closed Jan. 5, 2026 to be replaced by a new, fully accessible one. The city’s transportation department is building it', 'Opens 2029', 'CTA', 'Dec. 4, 2025', 'https://www.transitchicago.com/construction-to-begin-in-january-on-new-fully-accessible-statelake-cta-station/'),
            ('Blue Line Forest Park branch, phase one', '$126.7 million', 'Behind schedule', 'bad', 'Track and station work at Racine, Morgan and Hermitage. 80% complete in June', 'February 2027', 'NITA oversight report', 'June 2026', PMO),
            ('New 7000-series rail cars', '$713.7 million', 'Under way', 'go', '252 cars delivered and accepted by June', 'March 2027', 'NITA oversight report', 'June 2026', PMO),
            ('Elevators at more stations (All Stations Accessibility)', '$25.6 million to $88.7 million each', 'Mixed', '', 'Austin (Green Line) reopened fully accessible in Aug. 2026. Irving Park and Belmont (Blue) are in design; California (Blue) has to be bid again', '2028 to 2029', 'WTTW', 'Aug. 7, 2026', 'https://news.wttw.com/2026/08/07/officials-celebrate-completion-25m-project-improve-accessibility-cta-green-line-station'),
            ('Tap-to-pay fare system upgrade (Ventra)', '$127.2 million', 'Under way', 'go', 'The behind-the-scenes move to new systems was 90% done in June', 'December 2027', 'NITA oversight report', 'June 2026', PMO)]
NITA_SUM = 'https://nita.illinois.gov/uploads/files/general/NITA-Act-Summary-June-2026-Update.pdf'
NITA_DATES = [('2026-06-01', 'June 1, 2026', 'The law takes effect. The regional board approves a quarter-point sales tax increase'), ('2026-09-01', 'Sept. 1, 2026', 'New boards are seated at the regional agency (NITA), CTA, Metra and Pace'),
              ('2026-12-31', 'Dec. 31, 2026', 'The first regional budget under the new law must pass'), ('2027-07-01', 'July 1, 2027', 'Transit ambassadors start work on the system'),
              ('2027-12-31', 'Dec. 31, 2027', 'Service standards for buses and trains adopted'), ('2028-06-01', 'Mid-2028', 'Fare capping and income-based fares in place'),
              ('2030-02-01', 'Feb. 1, 2030', 'One fare system across CTA, Metra and Pace')]
def transit():
    h1 = 'CTA carried 70% of its 2019 rides in 2025, counted the same way. So far in 2026, rides are up 2.6%.'
    ys = list(range(2015, 2026))
    c1 = card('Rides on CTA, Metra and Pace, millions a year', 'Every year is counted the old way, so the years compare fairly.',
              bars([626, 605, 586, 571, 550, 231, 226, 285, 331, 367, 381], [f'’{str(y)[2:]}' for y in ys], h=190, aria='Rides on CTA, Metra and Pace in millions a year: 626 in 2015, 550 in 2019, 231 in 2020 and 381 in 2025.'))
    st = tiles([('70%', 'of 2019 rides on CTA in 2025: buses 78%, the L 62%'), ('62%', 'of 2019 rides on Metra: 37.9 million in 2025, up 8% in a year'), ('67%', 'of 2019 rides on Pace buses: 16.4 million in 2025'), ('▲ 2.6%', 'CTA rides, Jan.–Aug. 2026 vs. 2025: buses +1.9%, the L +3.7%')])
    rows = [[f'<b>{n}</b>', f'<span class="chip {c}">{stt}</span>', b, t, due, f'<a href="{u}" target="_blank" rel="noopener">{src}</a><br>{d}'] for n, b, stt, c, t, due, src, d, u in CTA_PROJ]
    c2 = card('CTA’s big projects', 'What is being built, what it costs and when it is due.', table(['Project', 'Status', 'Budget', 'Where it stands', 'Due', 'Source'], rows, cls='stack proj')
              + f'<p class="fine">Budgets, percentages and due dates are from the regional agency’s <a href="{PMO}" target="_blank" rel="noopener">June 2026 oversight report</a> unless the row links elsewhere. That report rates the Red Line Extension on schedule.</p>')
    li = ''.join(f'<li data-date="{iso}"><span class="when">{d}</span><span class="what">{t}</span><span class="st"></span></li>' for iso, d, t in NITA_DATES)
    c3 = card('The new transit law’s deadlines', 'In 2025 the state replaced the regional transit agency with a stronger one (NITA) and gave it new money. These are dates the law sets.',
              f'<ol class="dl">{li}</ol><p class="fine">Dates are from the agency’s <a href="{NITA_SUM}" target="_blank" rel="noopener">summary of the law (June 2026)</a>. A passed date means the deadline has gone by; we don’t yet track whether each was met. <a href="/learn/#nita">What the law changed ›</a></p>')
    c4 = card('What the agencies report', '', table(['', ''], [['More CTA service scheduled, 2025 vs. 2024', '<b>+14%</b>'], ['Rider growth on frequent bus routes', '<b>21%</b>'], ['Rider growth on other routes', '<b>11%</b>'], ['Door-to-door rides for riders with disabilities', '<b>6.2M</b>']], right=(1,), cls='plain')
              + '<p class="fine">Frequent routes come every 10 minutes or better; they were chosen because they were already busy. Door-to-door rides are 144% of 2019.</p>')
    g = goal('The 2025 transit law', 'There is no official ridership target. What the law does set is the list of deadlines above, plus a rule that fares and other income cover 25% of running costs from 2028 and 20% from 2029.', 'The agency’s summary', NITA_SUM)
    note = ('In 2025 CTA changed how it counts riders: new fareboxes and passenger counters, and rides the old system missed. That added 5.9% to its 2025 total (8.5% on buses, 2.4% on the L). '
            'On the new count 2025 was 338.0 million rides; on the old count, 319.2 million, which is the figure compared with 2019 here. The 2026 gain compares two years on the new count. '
            'Project budgets are as of March 2026 and status as of late May 2026, except where a row cites a later story.')
    return page('transit', 'Transit', h1, top('transit', 'Transit', h1, f'CTA rides through Aug. 2026 · Metra and Pace through 2025 · projects as of June to Aug. 2026 · checked {SNAP}') + st + c1 + c2 + '<section class="strip c2 cards">' + c3 + c4 + '</section>' + g
                + bottom('transit', note, 'CTA ridership restatement memo (Mar. 20, 2026); CTA annual ridership reports 2019 and 2025; CTA daily ridership (Chicago Data Portal); RTA regional ridership; NITA 2025 ridership release (Jan. 30, 2026); NITA Report on Project Management Oversight (June 2026); NITA Act summary (June 2026).'))

def streets():
    h1 = '82 people have died in traffic this year through Sept. 27, up from 71 by that date in 2025.'
    ys = [f'’{y}' for y in range(19, 27)]
    c1 = card('Traffic deaths each year', 'The city’s official count.', bars([120, 153, 186, 160, 136, 130, 100, 82], ys, partial=True, plabel='to Sept. 27', h=170, aria='Traffic deaths each year: 120 in 2019, a peak of 186 in 2021, 100 in 2025 and 82 through Sept. 27, 2026.'))
    c2 = card('People seriously hurt in crashes each year', 'From police crash reports.', bars([2376, 2241, 2377, 2287, 2225, 1931, 1710, 1497], ys, partial=True, plabel='to Nov. 6', short=lambda v: f'{v / 1000:.1f}k', h=170,
                                                                                         aria='People seriously hurt in crashes each year: 2,376 in 2019, 1,710 in 2025 and 1,497 through Nov. 6, 2026.'))
    st = tiles([('100 deaths', 'in all of 2025, the fewest since at least 2019. 36 were people walking'), ('1,497', 'people seriously hurt through Nov. 6 (1,485 by that date in 2025)'), ('6 days', 'for half of pothole requests to be fixed; 1 in 10 takes more than 7 weeks'), ('290,090', 'potholes filled through Nov. 6 (221,710 by that date in 2025)')])
    c3 = card('Speed camera violations, millions a year', 'Violations jumped in 2021, when cameras began recording drivers going 6 to 10 mph over the limit.',
              bars([0.86, 0.80, 3.08, 2.73, 2.29, 2.24, 2.44], ys[:-1], fmt=lambda v: f'{v:.2f}', h=170, aria='Speed camera violations in millions a year: under 1 million in 2019 and 2020, 3.08 million in 2021 and 2.44 million in 2025.')
              + '<p class="fine">Red-light cameras recorded 534,385 violations in 2025.</p>')
    note = ('Deaths are the city’s reviewed Vision Zero list, which is published about a month behind. Serious injuries come from police crash reports, which count a little differently (they show 84 deaths through Nov. 6, against 76 a year earlier). '
            'Pothole figures cover finished repairs only; open requests are not in the data, and counts follow the winter as much as the crews.')
    return page('streets', 'Streets', h1, top('streets', 'Streets', h1, f'Deaths through Sept. 27, 2026 · crashes and potholes through Nov. 6 · checked {SNAP}') + st + '<section class="strip c2 cards">' + c1 + c2 + '</section>' + c3
                + goal('Vision Zero: no traffic deaths or serious injuries by 2026', 'The city’s 2017 Vision Zero Action Plan set this year as its deadline to eliminate traffic deaths and serious injuries. Through Sept. 27, 82 people had died, and 1,497 had been seriously hurt through Nov. 6.', 'The action plan', 'https://www.chicago.gov/content/dam/city/sites/complete-streets/pdfs/17_0612%20VZ%20Action%20Plan_FOR%20WEB.pdf')
                + bottom('streets', note, 'City of Chicago Vision Zero traffic fatalities, traffic crashes, pothole repairs, and speed and red-light camera violations (Chicago Data Portal).'))

def projects():
    tot = sum(p[1] for p in PROJ); built = sum(p[2] for p in PROJ)
    h1 = f'Six big projects plan {f(tot)} homes. {f(built)} are built, all at North Union.'
    cls = {'Under way': 'go', 'Stalled': 'bad', 'Partly built': 'go', 'Planning': ''}
    rows = [[f'<b>{n}</b>', f'<span class="chip {cls[s]}">{s}</span>', f'{f(b)} of {f(h)}', t, f'<a href="{u}" target="_blank" rel="noopener">{src}</a><br>{d}'] for n, h, b, s, t, src, d, u in PROJ]
    c1 = card('', '', table(['Project', 'Status', 'Homes built so far', 'Where it stands', 'Source'], rows, right=(2,), cls='stack proj'))
    st = tiles([(f(tot), 'homes planned across the six projects'), (f(built), 'homes finished, in two buildings at North Union'), ('3 of 6', 'have broken ground: The 78, Foundry Park and the 1901 Project. None of the three has started on homes')], cols=3)
    note = f'Home counts are each project’s published plan. “Built so far” counts finished homes only. Each status comes from the dated news story linked with that project, checked {SNAP}.'
    return page('projects', 'Big projects', h1, top('projects', 'Big projects', h1, f'Each project checked on the date shown · checked {SNAP}') + st + c1 + goal('Each project has its own approved plan', 'There is no citywide target for these sites. The home counts here are what each plan, approved by the Plan Commission and City Council, says it will build.', none=True)
                + bottom('projects', note, 'Home counts: each project’s Plan Commission approval or published plan. Status: the dated story linked on each row. North Union homes built: Power Construction project pages.'))

# ---------------------------------------------------------------- overview
def overview():
    built = sum(p[2] for p in PROJ); tot = sum(p[1] for p in PROJ)
    SECS = [('zoning', '3 in 10', 'zoning changes for a new building get a permit within a year', spark([31, 20, 12, 35, 45], rng=('Passed 2021', '2025')), '45% for 2025’s votes, the most in five years'),
            ('room', '110,000', 'more homes allowed today on empty lots outside downtown', minisplit([(110, NAVY), (171, '#9db9de'), (203, '#d9e4f4')], 'Empty lots · shop lots · lots with homes'), 'About 484,000 on paper, mostly under standing buildings'),
            ('affordable', '29,550', 'homes on the city’s affordable rental list', minisplit([(10759, NAVY), (18791, '#d9e4f4')], 'For seniors · everyone else'), 'About 1 in 3 are for seniors · list dated Dec. 2024'),
            ('rents', '$2,311', 'typical asking rent, Sept. 2026', spark([RENT[y] for y in range(2019, 2027)], rng=('2019', '2026')), '▲ Up 5.7% in a year'),
            ('transit', '70%', 'of 2019’s CTA rides in 2025, counted the same way', spark([626, 605, 586, 571, 550, 231, 226, 285, 331, 367, 381], rng=('2015', '2025')), '▲ Up 2.6% in 2026 · 7 big projects tracked'),
            ('streets', '82 deaths', 'in traffic this year through Sept. 27', spark([120, 153, 186, 160, 136, 130, 100, 82], partial=True, rng=('2019', '2026 so far')), 'The city’s goal for 2026 was zero'),
            ('projects', f'{f(built)} of {f(tot)}', 'homes built in six big projects', minisplit([(built, NAVY), (tot - built, '#d9e4f4')], 'Built · planned'), '3 of the 6 have broken ground')]
    name = dict(SECTIONS)
    head = (f'<div class="otop"><div><h1>Progress</h1><p>What Chicago built, rezoned and ran, and where its big projects stand. Counted from public records and updated every day.</p></div><span class="upd">Updated {UPDATED}</span></div>')
    lead = (f'<a class="card lead" href="/progress/homes/"><div class="l"><span class="lab">Homes permitted in 2026</span><div class="n"><b>{f(ytd["homes"])}</b>{PACE}</div>'
            f'<p class="sub">Chicago needed <b>{f(ytd["needed_so_far"])}</b> by {THRU} to stay on pace to end its share of the housing shortage by 2041.</p>'
            f'<div class="m">{meter(pct)}<p class="fine"><span><b>{pct}%</b> of the pace</span><span>{f(ytd["needed_so_far"])} needed by now</span></p></div>'
            f'<div class="mini"><div><b>{"▼" if vs < 0 else "▲"} {abs(vs)}%</b><span>vs. this date last year ({f(ytd["prev"])})</span></div><div><b>About {f(net26)}</b><span>net gain after homes torn down</span></div></div>'
            f'<span class="go">Homes added ›</span></div><div class="r"><span class="cap">Homes permitted each year</span>{yearchart(False, 190)}</div></a>')
    def dec(href, mon, d, iso, title, what):
        return (f'<a class="card dec" href="{href}"><span class="dt"><span>{mon}</span><b>{d}</b></span><span class="tx"><b>{title}</b><span>{what}</span></span><span class="go" data-until="{iso}"></span></a>')
    decs = ('<section class="blk"><h2>Decisions coming up</h2><div class="strip c2">'
            + dec('/learn/#nita', 'DEC', '10', '2026-12-10', 'The first regional transit budget', '$5.04 billion · comments close Dec. 4')
            + dec('/budget/', 'DEC', '31', '2026-12-31', 'The 2027 city budget', '$882.4 million gap to close · try closing it yourself') + '</div></section>')
    cards = ''.join(f'<a class="card sec" href="/progress/{k}/"><span class="t">{name[k]}<span aria-hidden="true">›</span></span><span class="n{" sm" if len(n) > 9 else ""}">{n}</span><span class="d">{d}</span>{g}<span class="ch">{c}</span></a>' for k, n, d, g, c in SECS)
    grid = f'<section class="blk"><h2>Everything else we count</h2><div class="grid4">{cards}</div></section>'
    foot = '<p class="fine src">Each section lists its own sources and shows the date its data runs through. Homes permitted updates every morning; the other sections were last checked ' + SNAP + '.</p>'
    return page('', 'Progress', 'What Chicago built, rezoned and ran, and where its big projects stand, counted from public records.', head + lead + decs + grid + foot)

CSS = '''/* Progress pages (written by tools/progress/build.py) */
*{box-sizing:border-box}
html{background:var(--sc-page)}
body.pg{margin:0;background:var(--sc-page);font-family:var(--sc-font);color:var(--sc-ink);font-variant-numeric:tabular-nums;-webkit-font-smoothing:antialiased}
.pg .sc-head{position:sticky;top:0}
.pg main{max-width:var(--sc-w-wide);margin:0 auto;padding:22px 20px 56px;display:flex;flex-direction:column;gap:22px}
.pg a{color:var(--sc-navy)}
.pg .card{background:#fff;border:1px solid var(--sc-line);border-radius:18px;box-shadow:0 1px 2px rgba(20,30,50,.04)}
.pg a.card{text-decoration:none;color:var(--sc-ink);transition:transform .15s,border-color .15s,box-shadow .15s}
@media (hover:hover){ .pg a.card:hover{transform:translateY(-2px);border-color:var(--sc-navy);box-shadow:0 6px 18px rgba(43,93,160,.14)} }
.pg .pad{padding:22px 24px;display:flex;flex-direction:column;gap:14px;min-width:0}
.pg h1{margin:0;font-size:32px;line-height:1.2;letter-spacing:-.02em;font-weight:700;max-width:900px}
.pg h2{margin:0;font-size:18px;font-weight:600;letter-spacing:-.01em}
.pg h3{margin:0 0 10px;font-size:14.5px;font-weight:600}.pg h3 span{font-weight:400;color:var(--sc-mute)}
.pg .hd{display:flex;flex-direction:column;gap:4px}
.pg .cap{margin:0;font-size:13px;color:var(--sc-mute)}
.pg .sub{margin:0;font-size:14.5px;line-height:21px;color:var(--sc-ink2)}.pg .sub b,.pg .call b{color:var(--sc-ink)}
.pg .fine{margin:0;font-size:12.5px;line-height:18px;color:var(--sc-mute)}
.pg .lede{margin:0;font-size:15.5px;line-height:23px;color:var(--sc-ink2);max-width:860px}
.pg .call{margin:0;font-size:14.5px;line-height:21px;color:var(--sc-ink2);background:#f6f7f9;border-radius:12px;padding:12px 14px}
.pg .note{max-width:980px}.pg .src{max-width:980px}
.pg .eyebrow{margin:0;font-size:14px;font-weight:600;color:var(--sc-mute)}.pg .eyebrow a{color:var(--sc-navy);text-decoration:none}.pg .eyebrow a:hover{text-decoration:underline}
.pg .top{display:flex;flex-direction:column;gap:8px}
.pg .chip{display:inline-flex;align-items:center;gap:5px;border:1.5px solid var(--sc-line);color:var(--sc-ink2);border-radius:999px;padding:3px 11px;font-size:13px;font-weight:700;white-space:nowrap;align-self:flex-start}
.pg .chip.bad{border-color:#b3001e;color:#b3001e}.pg .chip.good{border-color:#1f7a45;color:#1f7a45}.pg .chip.go{border-color:var(--sc-navy);color:var(--sc-navy)}
.pg .meter{height:11px;background:#eef0f3;border-radius:6px;overflow:hidden}.pg .meter i{display:block;height:100%;background:var(--sc-navy);border-radius:6px}
.pg .key{display:flex;gap:6px 16px;flex-wrap:wrap;font-size:12.5px;color:var(--sc-ink2)}.pg .key i{display:inline-block;width:11px;height:11px;border-radius:3px;margin-right:6px;vertical-align:-1px}.pg .key b{color:var(--sc-ink)}
/* section pills */
.pg .pills{display:flex;gap:5px;align-items:center;flex-wrap:wrap}
.pg .pills a{padding:7px 11px;border-radius:18px;font-size:13px;font-weight:600;white-space:nowrap;text-decoration:none;color:var(--sc-ink);background:#fff;border:1px solid #d5d9de}
.pg .pills a.back{border:0;background:none;color:var(--sc-navy);padding:8px 6px}
.pg .pills a[aria-current]{color:#fff;background:var(--sc-navy);border-color:var(--sc-navy)}
/* stat tiles */
.pg .strip{display:grid;gap:12px}.pg .strip.c2{grid-template-columns:1fr 1fr}.pg .strip.c3{grid-template-columns:repeat(3,minmax(0,1fr))}.pg .strip.c4{grid-template-columns:repeat(4,minmax(0,1fr))}
.pg .strip.lead3{grid-template-columns:1.2fr 1fr 1fr}
.pg .tile{padding:16px 18px;display:flex;flex-direction:column;gap:6px;min-width:0}
.pg .tile > b{font-size:28px;font-weight:700;letter-spacing:-.025em;line-height:1.1}
.pg .tile span{font-size:14px;line-height:20px;color:var(--sc-ink2)}.pg .tile b.in{color:var(--sc-ink)}
.pg .tile.row{flex-direction:row;align-items:center;gap:14px}.pg .tile.row > b{flex:none}
.pg .tile.go{justify-content:space-between}.pg .tile.go b.t{display:block;font-size:15.5px;color:var(--sc-ink)}.pg .tile.go em{font-style:normal;font-weight:600;color:var(--sc-navy);white-space:nowrap}
/* bar charts */
.pg .chart{min-width:0;width:100%;max-width:calc(var(--n) * 150px);margin-inline:auto}   /* a chart with few bars sits centered instead of stretching */
.pg .plot{position:relative;height:calc(var(--ch) + 22px);border-bottom:1px solid #c9ced6;display:grid;grid-template-columns:repeat(var(--n),minmax(0,1fr));gap:12px;align-items:end}
.pg .bc{display:flex;flex-direction:column;justify-content:flex-end;height:100%;min-width:0;position:relative}
.pg .bc i{display:block}.pg .bc i.cap{background:repeating-linear-gradient(135deg,#8a9099 0 3px,#fff 3px 6px);border:1px solid #c9ced6;border-bottom:0;border-radius:3px 3px 0 0}
.pg .bv{align-self:center;margin-bottom:3px;font-size:12px;font-weight:600;white-space:nowrap;background:#fff;padding:0 3px;border-radius:3px;position:relative;z-index:1}
.pg .ref{position:absolute;left:0;right:0;border-top:1.5px dashed}
.pg .reft{position:absolute;right:0;font-size:12px;font-weight:600;background:rgba(255,255,255,.92);padding:0 0 0 6px}
.pg .xl{display:grid;grid-template-columns:repeat(var(--n),minmax(0,1fr));gap:12px;margin-top:6px}.pg .xl span{text-align:center;font-size:12.5px;line-height:15px;color:var(--sc-mute)}
.pg .vs{display:none}
.pg .narrow{max-width:560px}
.pg .pair{display:grid;grid-template-columns:1fr 1fr;gap:28px}
/* horizontal bars */
.pg .hb{display:flex;flex-direction:column;gap:8px}.pg .hb > div{display:grid;gap:10px;align-items:center;font-size:13.5px}
.pg .hb .tr{height:9px;background:#eef0f3;border-radius:5px}.pg .hb .tr i{display:block;height:100%;background:var(--sc-navy);border-radius:5px}.pg .hb b{text-align:right;white-space:nowrap}
.pg .split{display:flex;gap:2px;height:16px;border-radius:5px;overflow:hidden}
.pg .fin{display:flex;flex-direction:column;gap:9px}.pg .fin > div{display:grid;grid-template-columns:44px minmax(0,1fr) 150px;gap:10px;align-items:center}
.pg .fin .y{font-size:13.5px;font-weight:600}.pg .fin .st{display:flex;height:16px;border-radius:4px;overflow:hidden;gap:1px}.pg .fin .v{font-size:13px;color:var(--sc-ink2);white-space:nowrap}.pg .fin .v b{color:var(--sc-ink)}
.pg .dv{display:flex;flex-direction:column;gap:9px}.pg .dv > div{display:grid;grid-template-columns:96px minmax(0,1fr) 56px;gap:10px;align-items:center;font-size:13.5px}
.pg .dv .ax{position:relative;height:12px;background:linear-gradient(90deg,transparent calc(50% - .5px),#aab1bb calc(50% - .5px),#aab1bb calc(50% + .5px),transparent calc(50% + .5px))}
.pg .dv .ax i{position:absolute;top:1px;bottom:1px;border-radius:3px}.pg .dv .ax i.up{left:50%;background:var(--sc-navy)}.pg .dv .ax i.dn{right:50%;background:#c98a8a}.pg .dv b{text-align:right}
/* ward maps with lists */
.pg .mapr{display:flex;gap:36px;flex-wrap:wrap;align-items:flex-start}
.pg .mp{display:flex;flex-direction:column;gap:10px;flex:none;width:320px;max-width:100%}.pg .wmap{width:100%;height:auto;display:block}
.pg .lists{display:grid;grid-template-columns:1fr 1fr;gap:20px 28px;flex:1 1 380px;min-width:0;align-content:start}.pg .lists .call{grid-column:1/-1}
/* tables */
.pg .tw{overflow-x:auto}
.pg table{width:100%;border-collapse:collapse;font-size:14px}
.pg th{padding:8px 6px;font-size:12.5px;font-weight:600;color:var(--sc-mute);text-align:left;border-bottom:1px solid var(--sc-line);vertical-align:bottom}
.pg td{padding:10px 6px;border-bottom:1px solid #f1f2f4;vertical-align:top}.pg td.n,.pg th.n{text-align:right;white-space:nowrap}
.pg table.plain thead{display:none}.pg .tbd{color:var(--sc-mute);font-size:12.5px}
.pg table.proj td:last-child{color:var(--sc-mute);white-space:nowrap;font-size:13px}.pg table.proj td:last-child a{color:inherit}
/* ward map: hover and tap */
.pg .wmap path{stroke:#fff;stroke-width:.7;stroke-linejoin:round;cursor:pointer;outline:none}
.pg .wmap path.on,.pg .wmap path:focus-visible{stroke:#1a1d21;stroke-width:1.8}
.pg .winfo{margin:0;font-size:13px;line-height:18px;color:var(--sc-ink2);min-height:36px}.pg .winfo b{color:var(--sc-ink)}
.pg .hb > div.me span,.pg .hb > div.me b{font-weight:700}.pg .hb > div.me .tr i{background:var(--sc-ink)}
.pg .zipr{display:flex;flex-wrap:wrap;gap:10px 14px;align-items:center;margin:0 0 14px}.pg .zipr select{font:inherit;font-size:15px;min-height:40px;padding:0 12px;border-radius:12px;border:1px solid var(--sc-line2);background:#fff;color:var(--sc-ink)}
.pg .zipr label{font-weight:600;font-size:15px}
.pg .hb > div[data-w]{cursor:pointer;border-radius:6px;padding:2px 4px;margin:-2px -4px}.pg .hb > div.on{background:#eef3fb}
.pg details.all{border-top:1px solid var(--sc-line);padding-top:12px}.pg details.all summary{cursor:pointer;font-size:14px;font-weight:600;color:var(--sc-navy)}.pg details.all .tw{margin-top:10px;max-height:420px;overflow:auto}
/* the goal each section is measured against */
.pg .goalc{gap:8px}.pg .goalc .tag{align-self:flex-start;font-size:12px;font-weight:700;border-radius:999px;padding:3px 10px;background:var(--sc-navy);color:#fff}.pg .goalc .tag.none{background:#eef0f3;color:var(--sc-ink2)}.pg .goalc .sub{max-width:860px}
/* permitted - torn down = net */
.pg .eq .tile b i{font-style:normal;color:var(--sc-mute);font-weight:500;margin-right:4px}.pg .eq .tile.sum{border-color:var(--sc-navy)}
.pg .facts{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px}.pg .facts > div{background:#f6f7f9;border-radius:12px;padding:12px 14px;display:flex;flex-direction:column;gap:4px}.pg .facts b{font-size:20px;letter-spacing:-.02em}.pg .facts span{font-size:13.5px;line-height:19px;color:var(--sc-ink2)}
/* deadlines */
.pg ol.dl{list-style:none;margin:0;padding:0;display:flex;flex-direction:column}.pg ol.dl li{display:grid;grid-template-columns:104px minmax(0,1fr) auto;gap:10px;align-items:baseline;padding:9px 0;border-bottom:1px solid #f1f2f4;font-size:14px}
.pg ol.dl .when{font-weight:600;white-space:nowrap}.pg ol.dl .what{color:var(--sc-ink2)}.pg ol.dl .st{font-size:12px;font-weight:700;white-space:nowrap;color:var(--sc-mute)}
.pg ol.dl li.past .when,.pg ol.dl li.past .what{color:var(--sc-mute)}.pg ol.dl li.next .st{color:#fff;background:var(--sc-navy);border-radius:999px;padding:2px 9px}
/* previous / next */
.pg .pn{display:flex;justify-content:space-between;gap:12px}.pg .pn a{padding:12px 18px;min-width:220px}.pg .pn a span{display:block;font-size:12.5px;color:var(--sc-mute)}.pg .pn a b{font-size:15.5px}.pg .pn .nx{text-align:right;margin-left:auto}
/* overview */
.pg .otop{display:flex;align-items:flex-end;justify-content:space-between;gap:12px;flex-wrap:wrap;padding-top:10px}
.pg .otop h1{font-size:var(--sc-h1)}.pg .otop p{margin:8px 0 0;font-size:16px;line-height:1.45;color:var(--sc-ink2);max-width:620px}
.pg .upd{font-size:12.5px;color:var(--sc-mute);background:#fff;border:1px solid var(--sc-line);border-radius:999px;padding:5px 12px}
.pg .lead{padding:26px 28px;display:flex;gap:40px;flex-wrap:wrap}
.pg .lead .l{display:flex;flex-direction:column;gap:10px;flex:1 1 320px;min-width:0}.pg .lead .r{display:flex;flex-direction:column;gap:8px;flex:1.25 1 380px;min-width:0}
.pg .lab{font-size:14px;font-weight:600;color:var(--sc-ink2)}
.pg .lead .n{display:flex;align-items:center;gap:14px;flex-wrap:wrap}.pg .lead .n b{font-size:64px;font-weight:700;letter-spacing:-.03em;line-height:1}.pg .lead .n .chip{align-self:center}
.pg .lead .sub{max-width:430px}
.pg .lead .m{display:flex;flex-direction:column;gap:6px;margin-top:4px}.pg .lead .m p{display:flex;justify-content:space-between}.pg .lead .m b{color:var(--sc-ink)}
.pg .mini{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-top:6px}.pg .mini div{background:#f6f7f9;border-radius:12px;padding:10px 12px}.pg .mini b{font-size:17px;display:block}.pg .mini span{font-size:12.5px;color:var(--sc-mute)}
.pg .go{font-size:14px;font-weight:600;color:var(--sc-navy)}
.pg .blk{display:flex;flex-direction:column;gap:10px}
.pg .dec{display:flex;gap:14px;align-items:center;padding:14px 16px}
.pg .dec .dt{flex:none;width:54px;border:1px solid var(--sc-line);border-radius:12px;overflow:hidden;text-align:center}.pg .dec .dt span{display:block;background:#e4002b;color:#fff;font-size:11.5px;font-weight:700;padding:2px 0}.pg .dec .dt b{display:block;font-size:22px;line-height:32px}
.pg .dec .tx{flex:1;min-width:0}.pg .dec .tx b{display:block;font-size:15.5px}.pg .dec .tx span{font-size:13.5px;color:var(--sc-ink2)}.pg .dec .go{white-space:nowrap}
.pg .grid4{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:14px}
.pg .sec{display:flex;flex-direction:column;gap:8px;padding:18px 20px 16px;min-width:0}
.pg .sec .t{display:flex;justify-content:space-between;align-items:center;font-size:14px;font-weight:600;color:var(--sc-ink2)}.pg .sec .t span{color:#8a9099;font-size:17px}
.pg .sec .n{font-size:30px;font-weight:700;letter-spacing:-.025em;line-height:1.05}.pg .sec .n.sm{font-size:26px}
.pg .sec .d{font-size:13.5px;line-height:19px;color:var(--sc-ink2);min-height:38px}
.pg .sec .ch{font-size:13px;font-weight:600;border-top:1px solid #f1f2f4;padding-top:9px;margin-top:auto}
.pg .spark > div{display:flex;align-items:flex-end;gap:3px;height:34px}.pg .spark > div i{flex:1;border-radius:2px 2px 0 0}
.pg .spark > div.ms{align-items:center;gap:2px}.pg .spark > div.ms i{flex:none;height:10px;border-radius:0}.pg .spark > div.ms i:first-child{border-radius:5px 0 0 5px}.pg .spark > div.ms i:last-child{border-radius:0 5px 5px 0}
.pg .spark p{display:flex;justify-content:space-between;margin:3px 0 0;font-size:11px;color:var(--sc-mute)}
@media (max-width:1000px){ .pg .facts{grid-template-columns:1fr 1fr} .pg .grid4{grid-template-columns:repeat(2,minmax(0,1fr))} .pg .strip.c4{grid-template-columns:1fr 1fr} .pg .strip.lead3{grid-template-columns:1fr 1fr} .pg .strip.lead3 > :first-child{grid-column:1/-1} }
@media (max-width:760px){
  .pg main{padding:14px 12px 40px;gap:16px}
  .pg h1{font-size:23px}.pg .otop h1{font-size:28px}.pg .otop p{font-size:14.5px}
  .pg .pad{padding:16px 14px}
  .pg .pills{flex-wrap:nowrap;overflow-x:auto;margin:0 -12px;padding:0 12px;scrollbar-width:none}.pg .pills::-webkit-scrollbar{display:none}
  .pg .strip.c2,.pg .strip.c3,.pg .strip.lead3{grid-template-columns:1fr}.pg .strip.lead3 > :first-child{grid-column:auto}
  .pg .tile > b{font-size:24px}
  .pg .plot,.pg .xl{gap:5px}.pg .chart{--ch:160px !important}
  .pg .vl{display:none}.pg .vs{display:inline}.pg .bv{font-size:10.5px;padding:0 1px}.pg .xl span{font-size:10.5px}.pg .reft{font-size:11px}
  .pg .pair{grid-template-columns:1fr;gap:18px}
  .pg .fin > div{grid-template-columns:38px minmax(0,1fr) 96px}
  .pg .mapr{gap:18px}.pg .mp{margin:0 auto}.pg .lists{grid-template-columns:1fr}
  .pg .lead{padding:18px 16px;gap:22px}.pg .lead .n b{font-size:48px}
  .pg .grid4{gap:10px}.pg .sec{padding:14px 13px 12px}.pg .sec .n{font-size:21px}.pg .sec .n.sm{font-size:19px}.pg .sec .d{min-height:0}
  .pg .pn a{min-width:0;flex:1}
  .pg .key{font-size:12px}
  /* tables of projects and votes become one card per row */
  .pg table.stack thead{display:none}.pg table.stack,.pg table.stack tbody{display:block}
  .pg table.stack tr{display:grid;grid-template-columns:1fr 1fr;gap:4px 14px;padding:12px 0;border-bottom:1px solid var(--sc-line)}
  .pg table.stack td{display:block;border:0;padding:0;text-align:left !important;white-space:normal !important;font-size:13.5px}
  .pg table.stack td:first-child{grid-column:1/-1;font-size:15px;font-weight:600}
  .pg table.stack td:not(:first-child)::before{content:attr(data-l);display:block;font-size:11.5px;color:var(--sc-mute)}
  .pg table.proj td:nth-child(4),.pg table.proj td:last-child{grid-column:1/-1} .pg ol.dl li{grid-template-columns:86px minmax(0,1fr)} .pg ol.dl .st{grid-column:2}.pg table.proj td:nth-child(2)::before{content:none}
}
'''

MOVED = '<!doctype html><html lang="en"><head><meta charset="utf-8"><title>Homes added · Progress · Shape Chicago</title><meta http-equiv="refresh" content="0; url=/progress/homes/#lost"><link rel="canonical" href="/progress/homes/"></head><body><p><a href="/progress/homes/#lost">Homes lost is now part of Homes added.</a></p></body></html>\n'
def main():
    pages = {'': overview(), 'homes': homes(), 'zoning': zoning(), 'room': room(), 'lost': MOVED, 'affordable': affordable(), 'rents': rents(), 'transit': transit(), 'streets': streets(), 'projects': projects()}
    for slug, html in pages.items():
        d = os.path.join(OUT, slug); os.makedirs(d, exist_ok=True)
        open(os.path.join(d, 'index.html'), 'w').write(html)
    open(os.path.join(OUT, 'progress.css'), 'w').write(CSS)
    print('progress:', len(pages), 'pages;', f(ytd['homes']), 'homes through', THRU, f'({pct}% of pace)')

if __name__ == '__main__':
    main()
