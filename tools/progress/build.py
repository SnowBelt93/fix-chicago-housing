"""Progress: the overview and one page per section, written as plain HTML into progress/.

  python3 tools/progress/build.py

Live numbers: Homes permitted comes from tracker/data.json, which the daily tracker job refreshes (that job runs this
script afterwards, so the pages follow the data). Everything else is a snapshot from the one-time analyses of
Nov. 9, 2026 (SNAP below, each with the date its data runs through) until those get their own daily jobs.
Homes per ward come from the 2020 Census blocks in bears/data/blocks.bin.
Every figure here was checked in the Nov. 9 review (Claude Docs "Shape Chicago - Progress review")."""
import json, math, os, re, struct, sys, collections, datetime as dt

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

# daily files from the tracker job on main (tools/tracker/streets_daily.py); the fixed numbers in streets() and affordable() are only the fallback
def _load(n):
    try: return json.load(open(os.path.join(ROOT, 'tracker', n + '.json')))
    except Exception: return None
STR = _load('streets'); AFF = _load('affordable'); TL = _load('timelines'); RN = _load('rents')
ZF = (T.get('zoning') or {}).get('follow')          # every zoning change passed since 2021 with a home count: [date, homes, first permit, homes permitted, homes finished]
try: WJ = json.load(open(os.path.join(ROOT, 'wards', 'data', 'wards.json')))
except Exception: WJ = None

# ---------------------------------------------------------------- snapshot (Nov. 9, 2026 analyses)
SNAP = 'Nov. 9, 2026'
TODAY = __import__('time').strftime('%Y-%m-%d')
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
        ('Bronzeville Lakefront', 6800, 0, 'Planning', 'On Nov. 12, 2026 the owners and Capri Investment Group pitched a $10 billion plan around a domed 75,000-seat Bears stadium, with 5,000+ homes on and near the site. An updated infrastructure plan is due to the city Dec. 14. The Bears declined to comment', 'Chicago Sun-Times', 'Nov. 12, 2026', 'https://chicago.suntimes.com/bears-stadium/2026/11/12/michael-reese-hospital-developers-10-billion-stadium-bears'),
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
SECTIONS = [('homes', 'Homes'), ('zoning', 'Zoning'), ('affordable', 'Affordable'),
            ('rents', 'Rents and prices'), ('transit', 'Transit'), ('streets', 'Streets'), ('capital', 'City money'), ('projects', 'Big projects'), ('springfield', 'In Springfield')]
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
    return '<div class="hb">' + ''.join(f'<div{(" data-w=" + n[5:]) if n.startswith("Ward ") else ""}{" class=me" if n == me else ""} style="grid-template-columns: minmax(0, {w}px) minmax(0, 1fr) auto;"><span>{esc(n)}</span><div class="tr"><i style="width: {max(1.5, 100 * abs(v) / m):.0f}%;"></i></div><b>{t}</b></div>' for n, v, t in rows) + '</div>'

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
EMB, PINFO = {}, {}   # embeddable cards (id -> section, title, html) and each section's dates and sources, for /embed/
def card(title, cap, body, cls='', emb=None):
    btn = f'<button type="button" class="embb" data-emb="{emb}" aria-label="Embed or link to this chart">Embed</button>' if emb else ''
    hd = f'<div class="hd">{btn}<h2>{title}</h2>' + (f'<p class="cap">{cap}</p>' if cap else '') + '</div>' if title else ''
    if emb: EMB[emb] = (emb.split('-')[0], title, f'<section class="card pad {cls}"><div class="hd"><h2>{title}</h2>' + (f'<p class="cap">{cap}</p>' if cap else '') + f'</div>{body}</section>')
    idat = f' id="{emb}"' if emb else ''
    return f'<section class="card pad {cls}"{idat}>{hd}{body}</section>'
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
HEADER = re.search(r'<header class="sc-head">.*?</header>', HEAD, flags=re.S).group(0)
sys.path.insert(0, os.path.join(ROOT, 'tools', 'site')); from nav import nav_for, NAV_RE   # the one nav definition
def header(slug):
    return NAV_RE.sub(lambda m: nav_for('/progress/' + (slug + '/' if slug else '')), HEADER, count=1)
def pills(slug):
    return ('<nav class="pills" aria-label="Progress sections"><a class="back" href="/progress/">‹ Progress</a>'
            + ''.join(f'<a href="/progress/{s}/"{" aria-current=page" if s == slug else ""}>{t}</a>' for s, t in SECTIONS) + '</nav>')
def page(slug, title, desc, main):
    path = '/progress/' + (slug + '/' if slug else '')
    return f'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<link rel="icon" href="/shape/icon.svg" type="image/svg+xml"><link rel="icon" href="/favicon.ico" sizes="32x32"><link rel="apple-touch-icon" href="/shape/icon-180.png"><link rel="manifest" href="/site.webmanifest">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{esc(title) + ' · ' if slug else ''}Progress · Shape Chicago</title>
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
/* Embed: copy an iframe or a link for this chart */
document.querySelectorAll(".embb").forEach(b => b.addEventListener("click", () => {{
  const id = b.dataset.emb, card = b.closest(".card"), src = location.origin + "/embed/" + id + "/", h = Math.max(320, Math.round(card.offsetHeight + 70));
  let d = document.getElementById("embd"); if (!d) {{ d = document.createElement("dialog"); d.id = "embd"; d.className = "embd"; document.body.appendChild(d); }}
  const code = '<iframe src="' + src + '" title="' + card.querySelector("h2").textContent.replace(/"/g, "&quot;") + ' (Shape Chicago)" width="100%" height="' + h + '" style="border:0;max-width:820px" loading="lazy"></iframe>';
  d.innerHTML = '<h2>Embed this chart</h2><p>Free to use with credit to Shape Chicago. It updates itself when the numbers change.</p>'
    + '<label for="embc">Embed code</label><textarea id="embc" rows="4" readonly></textarea><label for="embl">Link to this chart</label><input id="embl" readonly>'
    + '<div class="row"><button type="button" class="sc-btn primary" id="embcp">Copy embed code</button><button type="button" class="sc-btn" id="emblc">Copy link</button><a class="sc-btn" href="' + src + '" target="_blank" rel="noopener">Preview</a><button type="button" class="sc-btn" id="embx">Close</button></div>'
    + '<p style="margin:14px 0 0;font-size:12.5px">More charts and how to cite them: <a href="/press/">For reporters ›</a></p>';
  d.querySelector("#embc").value = code; d.querySelector("#embl").value = location.origin + location.pathname + "#" + id;
  const cp = (t, btn) => navigator.clipboard.writeText(t).then(() => {{ const o = btn.textContent; btn.textContent = "Copied"; setTimeout(() => btn.textContent = o, 1400); }});
  d.querySelector("#embcp").onclick = e => cp(code, e.target); d.querySelector("#emblc").onclick = e => cp(d.querySelector("#embl").value, e.target); d.querySelector("#embx").onclick = () => d.close();
  d.showModal(); }}));
document.querySelectorAll("[data-until]").forEach(e => {{ const d = Math.ceil((new Date(e.dataset.until + "T12:00:00") - Date.now()) / 864e5); e.textContent = d > 1 ? "In " + d + " days" : d === 1 ? "Tomorrow" : d === 0 ? "Today" : "Passed"; }});
</script>
</body>
</html>
'''
ART = {k: os.path.exists(os.path.join(ROOT, 'shape', 'art', 'progress', k + '.webp')) for k in ('homes', 'zoning', 'affordable', 'rents', 'transit', 'streets', 'capital', 'projects', 'springfield', 'decisions')}
def art(slug):
    """The section's clay picture beside the headline (tools/art/learn2.py p_<slug>), or nothing."""
    if not ART.get(slug): return ''
    from PIL import Image
    w, h = Image.open(os.path.join(ROOT, 'shape', 'art', 'progress', slug + '.webp')).size
    return f'<img class="sc-pgart" src="/shape/art/progress/{slug}.webp" width="{w}" height="{h}" alt="" decoding="async">'
def top(slug, name, h1, thru):
    PINFO.setdefault(slug, {}).update(name=name, thru=thru)
    t = f'<p class="eyebrow"><a href="/progress/">Progress</a> <span aria-hidden="true">›</span> {name}</p><h1>{h1}</h1><p class="fine">{thru}</p>'
    a = art(slug)
    return f'<div class="top sc-pghead"><div>{t}</div>{a}</div>' if a else f'<div class="top">{t}</div>'
def bottom(slug, note, src):
    PINFO.setdefault(slug, {}).update(src=src)
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
              + f'<p class="call">In 2025: <b>{f(Y[2025]["homes"])}</b> permitted − about <b>{f(round(DEMO[2025] / 100) * 100)}</b> torn down = about <b>{f(n25)}</b> more homes. Teardowns are down by {"more than half" if DEMO[2025] < 0.45 * DEMO[2013] else "about half" if DEMO[2025] < 0.6 * DEMO[2013] else "a third or more"} since 2013, when about {f(round(DEMO[2013] / 100) * 100)} homes were in torn-down buildings.</p>', emb='homes-years')
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
              + f'<p class="sub">Building takes years: <b>{round(100 * r22["finished"] / r22["homes"])}%</b> of the homes permitted in 2022 are done, and <b>{round(100 * r24["finished"] / r24["homes"])}%</b> of 2024’s. About {exp}% of the homes permitted in 2021 and 2022 had the permit expire before the city recorded them as finished.</p>', emb='homes-finished')
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
              + f'<details class="all"><summary>All 50 wards</summary>{allw}</details>', emb='homes-wards')
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
    return page('homes', 'Homes', h1, top('homes', 'Homes', h1, f'Permits through {THRU}, 2026, updated every morning · teardowns through {TD_THRU}') + strip + c1 + c2 + c3 + timelines_card() + peers + lostc + c4 + g
                + bottom('homes', note, 'City of Chicago building permits (new construction, demolition and renovation); City of Chicago 2013 building footprints; Census Building Permits Survey; 2020 Census housing counts by block; City of Chicago ADU pre-approval applications and shared housing registrations.'))

def timelines_card():
    """How long a housing permit takes, from tracker/timelines.json (main's daily job)."""
    if not TL or not TL.get('years'): return ''
    ys = sorted(TL['years']); cur, prv = ys[-1], (ys[-2] if len(ys) > 1 else None)
    B = [('1', 'Single-family homes'), ('2-4', '2 to 4 homes'), ('5-49', '5 to 49 homes'), ('50+', '50 or more homes')]
    rows = []
    for k, lab in B:
        c = TL['years'][cur].get(k); p = TL['years'][prv].get(k) if prv else None
        if not c: continue
        rows.append((lab, c['med'], f"{c['med']} days" + (f" (was {p['med']} in {prv})" if p else ''), c))
    mx = max(r[1] for r in rows)
    hb = '<div class="hb">' + ''.join(f'<div style="grid-template-columns: minmax(0, 150px) minmax(0, 1fr) auto;"><span>{esc(l)}</span><div class="tr"><i style="width: {max(2, 100 * m / mx):.0f}%;"></i></div><b>{t}</b></div>' for l, m, t, c in rows) + '</div>'
    rv = TL.get('review') or {}
    rvn = {'Self Cert': 'Self-certified by an architect', 'Standard Plan Review': 'Standard city plan review', 'Direct Developer Services': 'Developer Services (large projects)', 'Traditional Developer Services': 'Developer Services (traditional)'}
    rvt = ''.join(f'<li><b>{v["med"]} days</b> {rvn.get(k, k)} <span>({v["n"]} permits)</span></li>' for k, v in rv.items())
    a = TL['years'][cur]['all']
    return card('How long a housing permit takes', f'Middle number of days from applying to getting the permit, new buildings with homes, {cur} through {day(TL["through"])}.', hb
                + (f'<h3 style="margin-top:14px">By how the plans were reviewed <span>(last 12 months)</span></h3><ul class="dot">{rvt}</ul>' if rvt else '')
                + f'<p class="sub">Half of all new home permits in {cur} took between {a["p25"]} and {a["p75"]} days. This counts only the city’s part, from application to permit: design, zoning changes and financing come before it. The city changed how it records application dates in late 2023, so earlier years aren’t compared.</p>', emb='homes-timelines')

# ---------------------------------------------------------------- the snapshot sections
def follow_rows():
    """Per year passed: zoning changes with a home count, share with a permit within 12 and 24 months, homes permitted so far, homes finished."""
    today = dt.date.fromisoformat(TODAY); out = []
    for y in range(2021, today.year + 1):
        R = [r for r in ZF if r[0][:4] == str(y)]
        if not R: continue
        def share(days):
            ripe = [r for r in R if dt.date.fromisoformat(r[0]) + dt.timedelta(days=days) <= today]
            if len(ripe) < max(5, len(R) // 2): return None, len(ripe)
            ok = sum(1 for r in ripe if r[2] and (dt.date.fromisoformat(r[2]) - dt.date.fromisoformat(r[0])).days <= days)
            return round(100 * ok / len(ripe)), len(ripe)
        out.append(dict(y=y, n=len(R), s12=share(365), s24=share(730), homes=sum(r[3] for r in R), fin=sum(r[4] for r in R), planned=sum(r[1] for r in R)))
    return out

def term_classes():
    """This Council term's zoning changes by what the new zoning allows, from the ward records (wards/data/wards.json)."""
    C = collections.Counter()
    for w in WJ['wards']:
        for z in w.get('z', []):
            if z.get('d', '') >= '2023-05-15': C[z.get('k') or 'none'] += 1
    return C

def zoning():
    if ZF: return zoning_live()
    h1 = 'At least 46% of new homes went up on land the City Council had rezoned in the five years before. Counting big-site plans, it is about two-thirds.'
    st = tiles([('At least 46%', 'of the 69,927 homes permitted 2014–2025 were on land rezoned in the 5 years before'), ('56%', 'were in big-site plans (planned developments), which the Council approves one by one'),
                ('53% vs. 12%', 'homes in buildings of 5+ vs. 1–4 homes that were on recently rezoned land'), ('3 in 10', 'zoning changes for a new building had a building permit within a year; 4 in 10 within two')])
    ch = bars([31, 20, 12, 35, 45], ['2021', '2022', '2023', '2024', '2025'], fmt=lambda v: f'{v}%', top=60, h=190, aria='Share of zoning changes for a new building that had a building permit within 12 months, by the year the change passed: 31% for 2021, 20% for 2022, 12% for 2023, 35% for 2024 and 45% for 2025.')
    tb = table(['Year passed', 'Zoning changes for a new building', 'Permit within 12 months', 'Within 24 months', 'Homes permitted so far on those sites', 'Of those, finished'],
               [['2021', '42', '31%', '43%', '4,926', '4,142'], ['2022', '51', '20%', '35%', '2,073', '1,300'], ['2023', '57', '12%', '33%', '1,320', '374'], ['2024', '63', '35%', '46%', '1,327', '124'],
                ['2025', '71', '45%', '<span class="tbd">too early to tell</span>', '721', '28'], ['2026', '57', '<span class="tbd">too early to tell</span>', '<span class="tbd">too early to tell</span>', '97', '0']], right=(1, 2, 3, 4, 5), cls='stack')
    c1 = card('What followed each year’s votes', 'Zoning changes passed for a new residential building, by the year they passed: the share with a building permit within 12 months. Our copies of the applications start in 2021, so earlier years can’t be counted yet.', ch + tb, emb='zoning-follow')
    c2 = card('This Council term, since May 2023', '787 zoning changes sorted so far by what the new zoning allows on the lot.',
              split([('More homes per lot', 468, NAVY), ('Same', 217, '#9db9de'), ('Fewer', 72, '#c98a8a'), ('Big-site plans', 30, '#c9ced6')])
              + '<p class="sub">385 more, a third of the term’s total, aren’t sorted yet because the before-and-after zoning couldn’t be read from the paperwork. “More homes per lot” compares what the zoning allows, not what was proposed.</p>')
    c3 = card('Newest approvals', 'Passed by the City Council on Oct. 14, 2026.', hbars([('537–547 W Oak St', 78, '78 homes'), ('2648–2658 W Lawrence Ave', 37, '37 homes'), ('1745–1759 N Cicero Ave', 36, '36 homes'), ('3244–3250 W Bryn Mawr Ave', 30, '30 homes')], w=190)
              + '<p class="sub"><a href="/wards/">See every zoning change in your ward ›</a></p>')
    note = ('A zoning change is the Council changing what can be built on a lot. Why “at least”: the zoning map keeps only the latest change on each site, so earlier ones are lost and the true share is higher. '
            'The table counts the 341 zoning changes since 2021 (of 2,093) whose application clearly describes a new residential building and no conversion of an existing one. A permit counts if it is for new construction inside the rezoned area on the zoning map, or at the same address, on or after the vote. '
            'Among those that got a permit, half got it within 9 months. For 2025, the 12-month figure covers the 60 passed by early November 2025.')
    rbody, rnote, rsrc = room_parts()
    return page('zoning', 'Zoning', h1, top('zoning', 'Zoning', h1, f'Permits through Nov. 6, 2026 · zoning votes through Oct. 14 · zoning map and Assessor lots, 2026 · checked {SNAP}') + st + c1 + '<section class="strip c2 cards">' + c2 + c3 + '</section>' + rbody
                + goal('The city has no target for how fast a rezoning turns into homes', 'Its Cut the Tape initiative, begun in 2024, is the program meant to speed approvals and permits. It reports steps taken, not a number to hit.', 'Cut the Tape', 'https://www.chicago.gov/city/en/depts/mayor/press_room/press_releases/2025/may/Cut-the-Tape-Year-of-Progress.html', none=True)
                + bottom('zoning', note + ' Room to grow: ' + rnote, 'City Clerk legislation records and zoning applications; Chicago zoning map (the ordinance number and date on each district); City of Chicago building permits. ' + rsrc))

def zoning_live():
    FR = follow_rows(); TBD = '<span class="tbd">too early to tell</span>'
    full = [r for r in FR if r['s12'][0] is not None]; lastfull = full[-1] if full else None
    h1 = (f'Of the zoning changes the City Council passed in {lastfull["y"]} for buildings with homes, {lastfull["s12"][0]}% had a building permit within a year.' if lastfull else 'How fast zoning changes turn into building permits.')
    st = tiles([('At least 46%', 'of the 69,927 homes permitted 2014–2025 were on land rezoned in the 5 years before (analysis of Nov. 9, 2026)'), ('56%', 'were in big-site plans (planned developments), which the Council approves one by one'),
                (f'{lastfull["s12"][0]}%' if lastfull else '–', f'of {lastfull["y"]}’s zoning changes for homes had a permit within a year' if lastfull else 'not enough data yet'),
                (f'{f(sum(r["homes"] for r in FR))}', f'homes permitted so far on sites rezoned since 2021, of {f(sum(r["planned"] for r in FR))} planned')])
    ch = bars([r['s12'][0] for r in full], [str(r['y']) for r in full], fmt=lambda v: f'{v}%', top=max(60, max([r['s12'][0] for r in full] + [0]) + 10), h=190,
              aria='Share of zoning changes for homes with a building permit within 12 months, by year passed: ' + ', '.join(f'{r["s12"][0]}% for {r["y"]}' for r in full) + '.') if full else ''
    pc = lambda t: TBD if t[0] is None else f'{t[0]}%'
    tb = table(['Year passed', 'Zoning changes with homes', 'Permit within 12 months', 'Within 24 months', 'Homes planned', 'Homes permitted so far', 'Of those, finished'],
               [[str(r['y']), f(r['n']), pc(r['s12']), pc(r['s24']), f(r['planned']), f(r['homes']), f(r['fin'])] for r in FR], right=(1, 2, 3, 4, 5, 6), cls='stack')
    c1 = card('What followed each year’s votes', 'Zoning changes the City Council passed whose application gives a number of homes, by the year they passed: the share with a building permit at the same address within 12 and 24 months. Our copies of the applications start in 2021. Updated every morning.', ch + tb, emb='zoning-follow')
    if WJ:
        C = term_classes(); tot = sum(C.values()); none = C.get('none', 0) + C.get('other', 0)
        c2 = card('This Council term, since May 15, 2023', f'{f(tot)} zoning changes, sorted by what the new zoning allows on the lot.',
                  split([('More homes per lot', C.get('up', 0), NAVY), ('Same', C.get('same', 0), '#9db9de'), ('Fewer', C.get('down', 0), '#c98a8a'), ('Big-site plans', C.get('pd', 0), '#c9ced6')])
                  + f'<p class="sub">{f(none)} more aren’t sorted yet because the before-and-after zoning couldn’t be read from the paperwork. “More homes per lot” compares what the zoning allows, not what was proposed.</p>')
    else: c2 = ''
    rec = (T.get('zoning') or {}).get('recent') or []
    lastd = rec[0]['final'] if rec else None
    newest = sorted([r for r in rec if r['final'] == lastd], key=lambda r: -r['homes'])[:5]
    c3 = card('Newest approvals', f'Passed by the City Council on {day(lastd, True)}.' if lastd else '', hbars([(esc(r['title'][:40]), r['homes'], f'{f(r["homes"])} homes') for r in newest], w=190)
              + '<p class="sub"><a href="/wards/">See every zoning change in your ward ›</a></p>') if newest else ''
    note = ('A zoning change is the Council changing what can be built on a lot. Why “at least” in the first figure: the zoning map keeps only the latest change on each site, so earlier ones are lost and the true share is higher; that figure and the 56% come from our Nov. 9, 2026 analysis of permits 2014–2025. '
            'The table counts zoning changes since 2021 whose application gives a number of homes. A permit counts if it is for new construction at the same street and a house number within 8 of the rezoned address, on the same side, within six years. '
            'A year shows a share only once at least half its zoning changes are 12 (or 24) months old; the share counts only those.')
    rbody, rnote, rsrc = room_parts()
    thru = dt.date.fromisoformat(T['through'][:10])
    return page('zoning', 'Zoning', h1, top('zoning', 'Zoning', h1, f'Permits through {THRU} · zoning votes through {day(lastd) if lastd else "–"} · updated every morning') + st + c1 + '<section class="strip c2 cards">' + c2 + c3 + '</section>' + rbody
                + goal('The city has no target for how fast a rezoning turns into homes', 'Its Cut the Tape initiative, begun in 2024, is the program meant to speed approvals and permits. It reports steps taken, not a number to hit.', 'Cut the Tape', 'https://www.chicago.gov/city/en/depts/mayor/press_room/press_releases/2025/may/Cut-the-Tape-Year-of-Progress.html', none=True)
                + bottom('zoning', note + ' Room to grow: ' + rnote, 'City Clerk legislation records and zoning applications; City of Chicago building permits; ward records on this site. ' + rsrc))

ROOM_FILLS = ['#7fa3d1', '#7fa3d1', '#1f4d8f', '#7fa3d1', '#4f7cb8', '#1f4d8f', '#4f7cb8', '#4f7cb8', '#1f4d8f', '#4f7cb8', '#7fa3d1', '#b3c9e6', '#b3c9e6', '#b3c9e6', '#4f7cb8', '#1f4d8f', '#1f4d8f', '#b3c9e6', '#b3c9e6', '#1f4d8f', '#4f7cb8', '#4f7cb8', '#b3c9e6', '#1f4d8f', '#7fa3d1', '#7fa3d1', '#1f4d8f', '#1f4d8f', '#4f7cb8', '#b3c9e6', '#dbe6f3', '#b3c9e6', '#dbe6f3', '#4f7cb8', '#dbe6f3', '#b3c9e6', '#4f7cb8', '#dbe6f3', '#b3c9e6', '#b3c9e6', '#b3c9e6', '#dbe6f3', '#b3c9e6', '#b3c9e6', '#b3c9e6', '#b3c9e6', '#b3c9e6', '#b3c9e6', '#7fa3d1', '#b3c9e6']
ROOM_BAND = dict(zip(SEQ, ['under 500', '500 to 1,000', '1,000 to 2,000', '2,000 to 4,000', 'more than 4,000']))
def room_parts():
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
    body = (f'<section class="blk sub2" id="room"><h2 class="h2big">Room to grow under today’s zoning</h2><p class="sub">{h1}</p></section>' + lede + c1 + st + c2 + c3)
    return body, note, 'Chicago zoning map; Chicago Zoning Ordinance §17-2-0303 and downtown floor-area rules; Cook County Assessor parcels and characteristics; City of Chicago building footprints.'

AFF_WARD = {1: 490, 2: 202, 3: 3921, 4: 2390, 5: 436, 6: 382, 7: 280, 8: 308, 9: 885, 10: 257, 11: 287, 12: 30, 13: 87, 14: 239, 15: 196, 16: 766, 17: 308, 18: 250, 19: 0, 20: 1877, 21: 462, 22: 180, 23: 89, 24: 1063, 25: 359,
            26: 1212, 27: 3427, 28: 2051, 29: 480, 30: 0, 31: 412, 32: 344, 33: 187, 34: 242, 35: 199, 36: 175, 37: 133, 38: 131, 39: 477, 40: 110, 41: 85, 42: 34, 43: 68, 44: 333, 45: 208, 46: 1016, 47: 229, 48: 842, 49: 1178, 50: 233}   # homes on the city list (dated Dec. 30, 2024) by 2023 ward
def in_ring(x, y, r):
    ins = False
    for i in range(len(r)):
        (x1, y1), (x2, y2) = r[i], r[(i + 1) % len(r)]
        if (y1 > y) != (y2 > y) and x < x1 + (y - y1) * (x2 - x1) / (y2 - y1): ins = not ins
    return ins
def ward_at(lon, lat):
    """Ward on the root wards.json (the city's 2023 map, simplified ward by ward); this matches the Nov. 9 count exactly."""
    for w in WARDS:
        for poly in w['polys']:
            if in_ring(lon, lat, poly[0]) and not any(in_ring(lon, lat, h) for h in poly[1:]): return w['ward']
def affordable():
    global AFF_WARD
    tot, nb, sen, aro_b, aro_h, upd = 29550, 598, 10759, 156, 1727, 'Dec. 30, 2024'
    if AFF and AFF.get('rows'):
        R = AFF['rows']; tot = sum(r[0] for r in R); nb = len(R)
        sen = sum(r[0] for r in R if 'senior' in r[1].lower() or '65+' in r[1]); aro = [r for r in R if r[1].strip().upper() == 'ARO']; aro_b, aro_h = len(aro), sum(r[0] for r in aro)
        if AFF.get('updated', '')[:4].isdigit(): upd = day(AFF['updated'], True)
        W = {w: 0 for w in range(1, 51)}
        for h, t, la, lo in R:
            w = ward_at(lo, la) if la else None
            if w: W[w] += h
        AFF_WARD = W
    h1 = f'The city’s list shows {f(tot)} affordable rental homes in {f(nb)} buildings. It was last updated {upd}.'
    st = tiles([(f(tot), 'homes on the list, which the city says is not complete'), (f'About 1 in {round(tot / sen)}' if sen else '–', f'are for seniors ({f(sen)} homes)'), (f'{f(aro_b)} buildings', f'with {f(aro_h)} homes are there because the city requires affordable homes in bigger new buildings (the ARO)'), ('Not counted', 'public housing (CHA) and rent vouchers')])
    BIN = [(2000, SEQ[4], '2,000 or more'), (1000, SEQ[3], '1,000–2,000'), (250, SEQ[2], '250–1,000'), (1, SEQ[1], 'Under 250'), (0, '#eceef1', 'None')]
    col = lambda w: next(c for t, c, _ in BIN if AFF_WARD[w] >= t)
    rk = sorted(AFF_WARD.items(), key=lambda r: -r[1])
    z = [w for w, v in sorted(AFF_WARD.items()) if v == 0]
    zw = (f'Ward {z[0]} has' if len(z) == 1 else 'Wards ' + ', '.join(map(str, z[:-1])) + f' and {z[-1]} have') if z else ''
    allw = table(['Ward', 'Homes on the city’s list'], [[f'<a href="/wards/#{w}">Ward {w}</a>', f(v)] for w, v in rk], right=(1,))
    c1 = card('Where the listed homes are', 'Homes on the city’s list, by ward.',
              '<div class="mapr"><div class="mp">' + wardmap(col, 'Map of Chicago’s 50 wards shaded by affordable rental homes on the city’s list. The most are on the Near South, Near West and West sides.', {w: f'{f(v)} homes on the city’s list' for w, v in AFF_WARD.items()})
              + key([(t, c, '') for _, c, t in BIN]) + '</div><div class="lists"><div><h3>Most homes on the list</h3>' + hbars([(f'Ward {w}', v, f(v)) for w, v in rk[:6]])
              + '</div><div><h3>Fewest</h3>' + hbars([(f'Ward {w}', v, f(v)) for w, v in rk[-6:]], maxv=rk[0][1])
              + '</div>' + (f'<p class="call">{zw} no building on the list. That is not the same as no affordable housing.</p>' if zw else '') + '</div></div>'
              + f'<details class="all"><summary>All 50 wards</summary>{allw}</details>', emb='affordable-wards')
    c2 = card('Is the number growing?', '', f'<p class="sub">The city’s list cannot say. It gives each building’s address and number of homes but not the year it opened, and the city keeps only its current version (last updated {upd}), so there is no older copy to compare. We check it every day and will show the change when it moves.</p>')
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
                  + f'<p class="sub">The city’s own list still cannot show growth: it has no opening dates and keeps only its current version (last updated {upd}).</p>')
    g = goal('The 2024–2028 housing bond', 'The city’s Housing and Economic Development Bond plan projects 600 to 1,000 affordable rental homes built or preserved, and 600 or more mixed-income homes every five years from its new Green Social Housing fund. The city has not published a running count against those figures.', 'The bond plan', "https://www.chicago.gov/content/dam/city/sites/business-and-neighborhood-development-strategy/pdf/Housing-and-Economic-Development-Bond-Book-(Updated-2024.07.03).pdf")
    note = ('The list is the Department of Housing’s “Affordable Rental Housing Developments”: buildings the city financed, plus those built under its affordable requirements rule. The city describes it as among the thousands of homes it supports and provides it as a courtesy. '
            'Ward totals place each building by its map location on the 2023 ward map. '
            'The federal count is HUD’s “Picture of Subsidized Households” for Chicago: homes under contract or available in each federal program at the end of each year. A voucher counts as one home wherever it is used. It leaves out buildings financed only with tax credits or city money, so it overlaps the city’s list but is not the same thing.')
    return page('affordable', 'Affordable', h1, top('affordable', 'Affordable', h1, f'City list last updated {upd} · federal count through 2025 · checked {day(TODAY, True) if AFF else SNAP}') + st + c1 + c2 + g
                + bottom('affordable', note, 'City of Chicago Department of Housing, Affordable Rental Housing Developments (Chicago Data Portal, updated ' + upd + '); 2023 ward boundaries; Housing and Economic Development Bond Book (July 2024); U.S. Department of Housing and Urban Development, Picture of Subsidized Households, 2014–2025.'))

def SALE_ROWS(SL):
    rows = []
    for k, lab in (('house', 'House'), ('condo', 'Condo'), ('flats', '2- to 6-flat')):
        m = SL['median'][k]; v = [m.get(y) for y in ('2019', '2021', '2023', '2025')]
        rows.append([lab] + [f'${f(x)}' if x else '–' for x in v] + ([f'<b>{"+" if v[3] >= v[0] else "−"}{abs(round(100 * (v[3] / v[0] - 1)))}%</b>'] if v[0] and v[3] else ['–']))
    return rows

def rents():
    R = dict(RENT); lat, latv, yoy = '2026-09', 2311, 5.7; SL = None
    if RN and RN.get('rent'):                                   # daily: Zillow's monthly series and the Assessor's sales (tools/tracker/rents_daily.py)
        S = RN['rent']['series']; ks = sorted(S); lat, latv = ks[-1], S[ks[-1]]
        prev = S.get(f'{int(lat[:4]) - 1}{lat[4:]}'); yoy = round(100 * (latv / prev - 1), 1) if prev else None
        for y in range(2019, int(lat[:4]) + 1):
            if f'{y}-01' in S: R[y] = S[f'{y}-01']
    if RN and RN.get('sales'): SL = RN['sales']
    latm = f'{MON[int(lat[5:]) - 1]} {lat[:4]}'
    h1 = f'The typical asking rent is ${f(latv)}' + (f', {"up" if yoy >= 0 else "down"} {abs(yoy)}% in a year.' if yoy is not None else '.')
    ys = [y for y in range(2019, 2027) if y in R]; real = {y: R[y] * CPI[2026] / CPI[y] for y in ys}
    up = round(100 * (R[2026] / R[2019] - 1)); upr = round(100 * (real[2026] / real[2019] - 1))
    money = lambda v: f'${f(v)}'
    two = ('<div class="pair"><div><h3>As advertised</h3>' + bars([R[y] for y in ys], [f'’{str(y)[2:]}' for y in ys], fmt=money, short=lambda v: f'${v / 1000:.1f}k', top=2500, h=170, aria='Typical asking rent each January, 2019 to 2026, as advertised: $1,606 in 2019 rising to $2,190 in 2026.')
           + '</div><div><h3>In 2026 dollars</h3>' + bars([round(real[y]) for y in ys], [f'’{str(y)[2:]}' for y in ys], fmt=money, short=lambda v: f'${v / 1000:.1f}k', top=2500, h=170, color='#5f8fcc',
                                                         aria=f'Typical asking rent each January in 2026 dollars: ${f(real[2019])} in 2019, dipping in 2021 and reaching ${f(R[ys[-1]])} in {ys[-1]}.') + '</div></div>')
    c1 = card('Typical asking rent each January', 'The same rents twice: as advertised, and after taking out inflation.', two
              + f'<p class="call">Asking rents are up <b>{up}%</b> since January 2019. After inflation, they are up about <b>{upr}%</b>: most of the rise matched prices in general.</p>')
    st = tiles([(f'${f(latv)}', f'asking rent for a home on the market, {latm} (Zillow)'), ('$1,440', 'what the typical renter pays, all renters (Census, 2024)'), ('31% vs. 26%', 'rise in asking rents vs. consumer prices, 2019 to 2025'), (lambda a, b: (f'{abs(round(100 * (a / b - 1)))}% {"fewer" if a < b else "more"}', f'houses sold in 2025 than in 2019 ({f(a)} vs. {f(b)})'))(SL['count']['house'].get('2025', 0), SL['count']['house'].get('2019', 1)) if SL and SL['count']['house'].get('2019') else ('20% fewer', 'houses sold in 2025 than in 2019 (10,369 vs. 12,944)')])
    c2 = card('Sale prices', 'Median sale price in Chicago, not adjusted for inflation.', table(['', '2019', '2021', '2023', '2025', 'Since 2019'],
              (SALE_ROWS(SL) if SL else [['House', '$230,000', '$295,000', '$284,900', '$320,000', '<b>+39%</b>'], ['Condo', '$260,000', '$288,000', '$280,000', '$329,000', '<b>+27%</b>'], ['2- to 6-flat', '$275,000', '$375,000', '$375,000', '$450,000', '<b>+64%</b>']]), right=(1, 2, 3, 4, 5)))
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
    return page('rents', 'Rents and prices', h1, top('rents', 'Rents and prices', h1, f'Rents through {latm} · sales through 2025 · ' + ('updated every morning' if RN else f'checked {SNAP}')) + st + c1 + zc + c2 + goal('No city program sets a target for rents or sale prices', 'Rents and prices are the result the other sections add up to, so this section is a readout, not a scorecard.', none=True)
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
    ytd_tile = ('▲ 2.6%', 'CTA rides, Jan.–Aug. 2026 vs. 2025: buses +1.9%, the L +3.7%'); live = ''; thru_live = 'CTA through Aug. 2026'
    try: TR = json.load(open(os.path.join(ROOT, 'tracker', 'transit.json')))
    except Exception: TR = None
    if TR and TR.get('series', {}).get('cta_bus'):
        # the federal monthly table: this year so far against the same months last year (both counted the same way)
        yr, mo = int(TR['through'][:4]), int(TR['through'][5:]); se = TR['series']
        span = f'Jan.–{MON[mo - 1]}' if mo > 1 else MON[0]
        ysum = lambda k, y: sum(v for m, v in se[k].items() if m[:4] == str(y) and int(m[5:]) <= mo)
        ch = lambda a, b: 100 * (a / b - 1) if b else 0
        arrow = lambda p: ('▲ ' if p >= 0 else '▼ ') + f'{abs(p):.1f}%'
        sign = lambda p: ('+' if p >= 0 else '−') + f'{abs(p):.1f}%'
        cta = [ysum('cta_bus', y) + ysum('cta_rail', y) for y in (yr - 1, yr)]
        rows = []
        for nm, ks in (('CTA buses', ['cta_bus']), ('CTA trains (the L)', ['cta_rail']), ('CTA, all', ['cta_bus', 'cta_rail']), ('Metra', ['metra']), ('Pace buses', ['pace_bus'])):
            a, b = sum(ysum(k, yr - 1) for k in ks), sum(ysum(k, yr) for k in ks)
            rows.append([f'<b>{nm}</b>' if nm == 'CTA, all' else nm, f'{a / 1e6:.1f}M', f'{b / 1e6:.1f}M', f'<b>{sign(ch(b, a))}</b>'])
        pc = ch(cta[1], cta[0])
        h1 = f'CTA carried 70% of its 2019 rides in 2025, counted the same way. So far in {yr}, rides are {"up" if pc >= 0 else "down"} {abs(pc):.1f}%.'
        ytd_tile = (arrow(pc), f'CTA rides, {span} {yr} vs. {yr - 1}: buses {sign(ch(ysum("cta_bus", yr), ysum("cta_bus", yr - 1)))}, the L {sign(ch(ysum("cta_rail", yr), ysum("cta_rail", yr - 1)))}')
        mons = [f'{yr}-{m:02d}' for m in range(1, mo + 1)]
        live = card(f'Rides so far this year, against the same months of {yr - 1}', f'{span} of each year, from the federal monthly count. It is refreshed about once a month and runs two months behind.',
                    table(['', f'{span} {yr - 1}', f'{span} {yr}', 'Change'], rows, right=(1, 2, 3))
                    + f'<h3 style="margin-top:16px">CTA rides each month of {yr}, millions</h3>'
                    + bars([round((se['cta_bus'].get(m, 0) + se['cta_rail'].get(m, 0)) / 1e6, 1) for m in mons], [MON[int(m[5:]) - 1].rstrip('.')[:3] for m in mons], fmt=lambda v: f'{v:.1f}', short=lambda v: f'{v:.0f}', h=150,
                           aria=f'CTA rides each month of {yr} in millions, {MON[0]} through {MON[mo - 1]}.'))
        thru_live = f'federal monthly count through {MON[mo - 1]} {yr}, checked every morning'
    ys = list(range(2015, 2026))
    c1 = card('Rides on CTA, Metra and Pace, millions a year', 'Every year is counted the old way, so the years compare fairly.',
              bars([626, 605, 586, 571, 550, 231, 226, 285, 331, 367, 381], [f'’{str(y)[2:]}' for y in ys], h=190, aria='Rides on CTA, Metra and Pace in millions a year: 626 in 2015, 550 in 2019, 231 in 2020 and 381 in 2025.'), emb='transit-rides')
    st = tiles([('70%', 'of 2019 rides on CTA in 2025: buses 78%, the L 62%'), ('62%', 'of 2019 rides on Metra: 37.9 million in 2025, up 8% in a year'), ('67%', 'of 2019 rides on Pace buses: 16.4 million in 2025'), ytd_tile])
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
    return page('transit', 'Transit', h1, top('transit', 'Transit', h1, f'Rides: {thru_live} · yearly totals through 2025 · projects as of June to Aug. 2026 · checked {SNAP}') + st + live + c1 + c2 + '<section class="strip c2 cards">' + c3 + c4 + '</section>' + g
                + bottom('transit', note + ' This year’s month-by-month rides come from the Federal Transit Administration’s National Transit Database, which counts every boarding; CTA changed how it counts in January 2025, so those months are compared only with the same months a year earlier.', 'Federal Transit Administration, National Transit Database, Complete Monthly Ridership; CTA ridership restatement memo (Mar. 20, 2026); CTA annual ridership reports 2019 and 2025; CTA daily ridership (Chicago Data Portal); RTA regional ridership; NITA 2025 ridership release (Jan. 30, 2026); NITA Report on Project Management Oversight (June 2026); NITA Act summary (June 2026).'))

STR0 = {'deaths': {'years': dict(zip(map(str, range(2019, 2027)), [120, 153, 186, 160, 136, 130, 100, 82])), 'through': '2026-09-27', 'ytd': 82, 'ytd_prev': 71},
        'serious': {'years': dict(zip(map(str, range(2019, 2027)), [2376, 2241, 2377, 2287, 2225, 1931, 1710, 1497])), 'through': '2026-11-06', 'ytd': 1497, 'ytd_prev': 1485},
        'crash_deaths': {'through': '2026-11-06', 'ytd': 84, 'ytd_prev': 76},
        'potholes': {'through': '2026-11-06', 'ytd': 290090, 'ytd_prev': 221710}, 'pothole_wait': {'median_days': 6, 'share_over_7_weeks': 0.1},
        'speed': {'years': dict(zip(map(str, range(2019, 2026)), [862596, 800594, 3077604, 2731585, 2288983, 2239667, 2444752]))}, 'redlight': {'years': {'2025': 534385}}}
def streets():
    D = STR if STR and STR.get('deaths') else STR0
    de, se, cd, ph, pw = D['deaths'], D['serious'], D.get('crash_deaths', {}), D['potholes'], D.get('pothole_wait', {})
    dthru, sthru, pthru = de['through'], se['through'], ph['through']; yr = dthru[:4]; full = str(int(yr) - 1)
    dys = [y for y in sorted(de['years']) if y >= '2019']; sys_ = [y for y in sorted(se['years']) if y >= '2019']
    up = lambda a, b: 'up from' if a > b else ('down from' if a < b else 'the same as')
    h1 = f'{f(de["ytd"])} people have died in traffic this year through {day(dthru)}, {up(de["ytd"], de["ytd_prev"])} {f(de["ytd_prev"])} by that date in {int(yr) - 1}.'
    c1 = card('Traffic deaths each year', 'The city’s official count.', bars([de['years'][y] for y in dys], [f'’{y[2:]}' for y in dys], partial=True, plabel=f'to {day(dthru)}', h=170,
              aria=f'Traffic deaths each year: {de["years"]["2019"]} in 2019, {de["years"].get("2021", 0)} in 2021, {de["years"].get(full, 0)} in {full} and {de["ytd"]} through {day(dthru, True)}.'), emb='streets-deaths')
    c2 = card('People seriously hurt in crashes each year', 'From police crash reports.', bars([se['years'][y] for y in sys_], [f'’{y[2:]}' for y in sys_], partial=True, plabel=f'to {day(sthru)}', short=lambda v: f'{v / 1000:.1f}k', h=170,
              aria=f'People seriously hurt in crashes each year: {f(se["years"]["2019"])} in 2019, {f(se["years"].get(full, 0))} in {full} and {f(se["ytd"])} through {day(sthru, True)}.'), emb='streets-injuries')
    walk = '. 36 were people walking' if full == '2025' else ''   # from the Nov. 9 read of the 2025 list
    fewest = full == min(dys[:-1], key=lambda y: de['years'][y])
    sh = pw.get('share_over_7_weeks', 0.1); one_in = round(1 / sh) if sh else 0
    st = tiles([(f'{f(de["years"].get(full, 0))} deaths', f'in all of {full}' + (', the fewest since at least 2019' if fewest else '') + walk),
                (f(se['ytd']), f'people seriously hurt through {day(sthru)} ({f(se["ytd_prev"])} by that date in {int(sthru[:4]) - 1})'),
                (f'{pw.get("median_days", 6):g} days', f'for half of pothole requests to be fixed; 1 in {one_in} takes more than 7 weeks'),
                (f(ph['ytd']), f'potholes filled through {day(pthru)} ({f(ph["ytd_prev"])} by that date in {int(pthru[:4]) - 1})')])
    sp = D['speed']['years']; sy = [y for y in sorted(sp) if '2019' <= y < sthru[:4]]; rl = D['redlight']['years']
    c3 = card('Speed camera violations, millions a year', 'Violations jumped in 2021, when cameras began recording drivers going 6 to 10 mph over the limit.',
              bars([round(sp[y] / 1e6, 2) for y in sy], [f'’{y[2:]}' for y in sy], fmt=lambda v: f'{v:.2f}', h=170,
                   aria=f'Speed camera violations in millions a year: under 1 million in 2019 and 2020, {sp["2021"] / 1e6:.2f} million in 2021 and {sp[sy[-1]] / 1e6:.2f} million in {sy[-1]}.')
              + (f'<p class="fine">Red-light cameras recorded {f(rl[sy[-1]])} violations in {sy[-1]}.</p>' if sy[-1] in rl else ''))
    note = ('Deaths are the city’s reviewed Vision Zero list, which is published about a month behind. Serious injuries come from police crash reports, which count a little differently '
            f'(they show {f(cd.get("ytd", 0))} deaths through {day(cd.get("through", sthru))}, against {f(cd.get("ytd_prev", 0))} a year earlier). '
            'Pothole figures cover finished repairs only; open requests are not in the data, and counts follow the winter as much as the crews. The repair time covers requests finished in the last 12 months.')
    chk = day(TODAY, True) if D is STR else SNAP
    return page('streets', 'Streets', h1, top('streets', 'Streets', h1, f'Deaths through {day(dthru, True)} · crashes through {day(sthru)} · potholes through {day(pthru)} · updated daily, checked {chk}') + st + '<section class="strip c2 cards">' + c1 + c2 + '</section>' + c3
                + goal('Vision Zero: no traffic deaths or serious injuries by 2026', f'The city’s 2017 Vision Zero Action Plan set 2026 as its deadline to eliminate traffic deaths and serious injuries. Through {day(dthru)}, {f(de["ytd"])} people had died this year, and {f(se["ytd"])} had been seriously hurt through {day(sthru)}.', 'The action plan', 'https://www.chicago.gov/content/dam/city/sites/complete-streets/pdfs/17_0612%20VZ%20Action%20Plan_FOR%20WEB.pdf')
                + bottom('streets', note, 'City of Chicago Vision Zero traffic fatalities, traffic crashes, pothole repairs, and speed and red-light camera violations (Chicago Data Portal).'))

def projects():
    tot = sum(p[1] for p in PROJ); built = sum(p[2] for p in PROJ)
    h1 = f'Six big projects plan {f(tot)} homes. {f(built)} are built, all at North Union.'
    cls = {'Under way': 'go', 'Stalled': 'bad', 'Partly built': 'go', 'Planning': ''}
    rows = [[f'<b>{n}</b>', f'<span class="chip {cls[s]}">{s}</span>', f'{f(b)} of {f(h)}', t, f'<a href="{u}" target="_blank" rel="noopener">{src}</a><br>{d}'] for n, h, b, s, t, src, d, u in PROJ]
    c1 = card('', '', table(['Project', 'Status', 'Homes built so far', 'Where it stands', 'Source'], rows, right=(2,), cls='stack proj'))
    st = tiles([(f(tot), 'homes planned across the six projects'), (f(built), 'homes finished, in two buildings at North Union'), ('3 of 6', 'have broken ground: The 78, Foundry Park and the 1901 Project. None of the three has started on homes')], cols=3)
    # the latest headlines that name each project, from the news feed (refreshed every few hours; this page rebuilds every morning)
    try: NW = json.load(open(os.path.join(ROOT, 'news', 'data', 'news.json')))['items']
    except Exception: NW = []
    KEYS = {'The 78': r'\bThe 78\b', 'Foundry Park': r'Foundry Park', '1901 Project': r'1901 Project|\b1901\b', 'Bronzeville Lakefront': r'Bronzeville Lakefront|Michael Reese',
            'North Union': r'North Union', 'Cabrini-Green': r'Cabrini'}
    news = []
    for n, *_ in PROJ:
        rx = re.compile(KEYS.get(n, re.escape(n)), re.I)
        hits = sorted([it for it in NW if rx.search(it.get('t', '') + ' ' + it.get('x', ''))], key=lambda it: it['d'], reverse=True)[:3]
        if hits: news.append(f'<div class="pnews"><h3>{esc(n)}</h3><ul class="dot">' + ''.join(f'<li><a href="{esc(it["u"])}" target="_blank" rel="noopener" translate="no">{esc(it["t"])}</a> <span class="fine">{esc(it["s"])}, {day(it["d"][:10], True)}</span></li>' for it in hits) + '</ul></div>')
    c2 = card('In the news lately', 'The newest headlines naming each project, from the Chicago outlets on our News page.', ''.join(news)) if news else ''
    note = f'Home counts are each project’s published plan. “Built so far” counts finished homes only. Each status comes from the dated news story linked with that project, checked {SNAP}; the news list updates every morning.'
    return page('projects', 'Big projects', h1, top('projects', 'Big projects', h1, f'Each project checked on the date shown · checked {SNAP} · news updated every morning') + st + c1 + c2 + goal('Each project has its own approved plan', 'There is no citywide target for these sites. The home counts here are what each plan, approved by the Plan Commission and City Council, says it will build.', none=True)
                + bottom('projects', note, 'Home counts: each project’s Plan Commission approval or published plan. Status: the dated story linked on each row. North Union homes built: Power Construction project pages.'))

# ---------------------------------------------------------------- capital spending (snapshot: the city's PDFs, read by hand)
# The five-year Capital Improvement Program, 2025–2029: program totals from the charts on pp. 6–22 (they add to $18.1B).
# Information technology isn't printed as a total; it is what's left of the pie ($175.5M), so it's labeled that way.
CIP_URL = 'https://www.chicago.gov/content/dam/city/depts/obm/supp_info/CIP/City%20of%20Chicago%202025-2029%20CIP.pdf'
CIP = [('O’Hare and Midway airports', 5980.4), ('Water system', 3673.3), ('Streets, bridges and transit', 3033.5), ('Sewers', 1893.0), ('Neighborhood streets, alleys and lights', 1447.3),
       ('Economic development', 816.5), ('City vehicles', 459.9), ('City buildings', 388.4), ('Information technology and other', 175.5), ('Lakefront and shoreline', 150.0), ('Public spaces (City Space)', 86.5)]
def kd(v): return f'${v / 1e6:.2f}M' if v >= 995e3 else f'${v / 1e3:.0f}K'
def capital():
    try: M = json.load(open(os.path.join(ROOT, 'wards', 'data', 'menu.json')))
    except Exception: M = None
    tot = sum(v for _, v in CIP)
    rows = [(n, v, f'${v / 1000:.1f}B' if v >= 1000 else f'${v:.0f}M') for n, v in CIP]
    c1 = card('The city’s five-year building plan, 2025–2029', f'${tot / 1000:.1f} billion by program. About 40% is borrowing repaid from airport, water and sewer revenue; the rest comes from city bonds, TIF, federal, state and other money.',
              hbars(rows, w=250) + f'<p class="fine">The plan is updated each year; this is the most recent one the city has published. Information technology isn’t printed as its own total; it’s the rest of the ${tot / 1000:.1f} billion.</p>')
    body = ''
    if M:
        R = M['rows']; com = sum(r[2] for r in R); bud = sum(r[1] for r in R); left = sum(r[5] for r in R); items = sum(r[12] for r in R)
        cats = [(c[1], sum(r[6 + i] for r in R)) for i, c in enumerate(M['cats'])]; cats.sort(key=lambda x: -x[1])
        c2 = card('Ward street money: what alderpeople picked', f'${com / 1e6:.1f} million committed of ${bud / 1e6:.0f} million for 2026, through Sept. 30. Every ward gets $1.5 million a year.',
                  hbars([(n, v, f'${v / 1e6:.1f}M') for n, v in cats], w=190))
        pct = {r[0]: r[2] / r[1] * 100 for r in R}
        BINS = [(99.5, '#1f4d8f', 'All of it'), (90, '#4f7cb8', '90–99%'), (70, '#9db9de', '70–89%'), (0, '#dbe6f3', 'Under 70%')]
        col = lambda w: next(c for t, c, _ in BINS if pct.get(w, 0) >= t)
        info = {r[0]: f'${r[2] / 1e6:.2f}M committed of $1.5M ({pct[r[0]]:.0f}%) · {r[12]} projects' for r in R}
        most = sorted(R, key=lambda r: -r[5])[:6]; side = sorted(R, key=lambda r: -r[7])[:6]
        c3 = card('Ward by ward', 'Share of each ward’s 2026 street money committed by Sept. 30.',
                  '<div class="mapr"><div class="mp">' + wardmap(col, 'Map of Chicago’s 50 wards shaded by the share of their 2026 street money committed by Sept. 30.', info) + key([(t, c, '') for _, c, t in BINS])
                  + '</div><div class="lists"><div><h3>Most money not yet committed <span>(incl. past years)</span></h3>' + hbars([(f'Ward {r[0]}', r[5], kd(r[5])) for r in most])
                  + '</div><div><h3>Most on sidewalks</h3>' + hbars([(f'Ward {r[0]}', r[7], kd(r[7])) for r in side])
                  + f'</div><p class="call"><b>{sum(1 for r in R if r[2] >= r[1] - 1)} of 50 wards</b> had committed all $1.5 million by Sept. 30. Each ward’s page lists what its money went to.</p></div></div>')
        body = c2 + c3
        tl = tiles([(f'${tot / 1000:.1f}B', 'in the city’s five-year building plan, 2025–2029'), ('$6.0B', 'of it for O’Hare and Midway airports'), (f'${com / 1e6:.1f}M', f'of ${bud / 1e6:.0f}M in ward street money committed by Sept. 30, 2026'), (f(items), 'ward street projects listed: repaving, sidewalks, speed humps, lights')])
    else:
        tl = tiles([(f'${tot / 1000:.1f}B', 'in the city’s five-year building plan, 2025–2029')], cols=1)
    h1 = f'Chicago plans ${tot / 1000:.1f} billion in building and repairs over five years. Each ward also gets $1.5 million a year for street projects its alderperson picks.'
    note = ('Program totals are the five-year plan’s own charts. Ward street money is the city’s third-quarter report: we read each project’s type and estimated cost and grouped the types. Our totals match each ward’s committed total except Ward 16, where the listed projects add up to $7,730 more. '
            'The plan lists what the city intends to spend, not what it spent.')
    g = goal('The plan is the city’s own list of intended projects', 'There is no outside target for capital spending. The five-year plan says what the city intends to build and how it expects to pay; the ward money has to be committed by each alderperson, and what isn’t committed carries over.', 'The 2025–2029 plan (PDF)', CIP_URL, none=True)
    return page('capital', 'City money', h1, top('capital', 'City money', h1, f'Five-year plan 2025–2029 · ward street money through Sept. 30, 2026 · checked Nov. 11, 2026') + tl + c1 + body + g
                + bottom('capital', note, f'{src("City of Chicago, 2025–2029 Capital Improvement Program", CIP_URL)} · {src("City of Chicago, 2026 Q3 Aldermanic Menu Report", M["url"]) if M else ""}'))

# ---------------------------------------------------------------- In Springfield (daily: tracker/bills.json from the bill job on main)
# Every House and Senate bill of the current General Assembly that touches Chicago's housing, transit, budget, pensions or
# property taxes (topic rules in tools/bills/fetch.py on main). WATCH gives a few bills a plain name; each was checked
# against the bill's own synopsis. Shell bills ("makes a technical change") are left out by the fetcher.
WATCH = {
    'SB2111': 'Became the 2025 transit law: the new regional transit agency and its funding, plus the People Over Parking Act',
    'HB5626': 'The BUILD Act: up to 4–8 homes on single-family lots by lot size, coach houses everywhere, single-stair buildings, no parking minimums for small homes',
    'HB1814': 'Middle housing (two- to four-flats and similar) allowed on residential lots over 5,000 sq ft in cities of 25,000 or more',
    'SB4060': 'Single-family homes allowed on lots as small as 2,500 sq ft',
    'SB4064': 'Parking caps: no more than 0.5 spaces per apartment or 1 per house required, and none for small homes or affordable projects',
    'SB4071': 'Coach houses (accessory dwelling units) allowed wherever single-family homes are, from 2027',
    'HB1813': 'Towns may not ban coach houses (accessory dwelling units)',
    'HB5223': 'Towns with zoning must adopt at least 5 of 14 listed housing strategies',
    'HB2754': 'Zoning votes: mayors get a vote, and some zoning changes need a simple majority instead of two-thirds',
    'HB2545': 'Appeals when a town turns down supportive housing for people with disabilities',
    'HB957': 'Tenants of buildings with 6 or more homes get a first chance to buy when the building is sold',
    'HB3269': 'A fee on monthly rents above $1,200 at landlords with more than 5 units, to help households buy homes',
    'SB3212': 'Shops, restaurants and other uses allowed by right within a mile of transit-oriented development',
}
TOPIC = {'housing': 'Housing and zoning', 'transit': 'Transit', 'budget': 'City budget and taxes', 'pensions': 'City pensions', 'property': 'Property taxes'}
VANDALIA = 'https://www.vandaliaradio.com/2026/10/19/163417/'
# the legislature's short titles are abbreviated capitals ("VEH CD-BICYCLES"); spell out the common pieces
ABBR = [(r'\bVEH CD\b', 'Vehicle Code'), (r'\bMUNI CD\b', 'Municipal Code'), (r'\bPEN CD\b', 'Pension Code'), (r'\bSCH CD\b', 'School Code'), (r'\bCIV PRO\b', 'Civil procedure'),
        (r'\bCRIM PRO\b', 'Criminal procedure'), (r'\bPROP TX\b', 'Property tax'), (r'\bLOC GOV\b', 'Local government'), (r'\bCHI\b', 'Chicago'), (r'\bMUNI\b', 'Municipal'),
        (r'\bCNTY\b', 'County'), (r'\bCOUNTIES CD\b', 'Counties Code'), (r'\bINC TX\b', 'Income tax'), (r'\bTRANS\b', 'Transportation'), (r'\bPROP\b', 'Property'), (r'\bDEV\b', 'Development')]
KEEP = {'IHDA', 'DCEO', 'EPA', 'DHS', 'DCFS', 'CTA', 'RTA', 'NITA', 'TIF', 'ADU', 'PHA', 'CMS', 'OSFM', 'SURS', 'TRS', 'IMRF', 'MWRD', 'II', 'IL', 'SW', 'DOT', 'IDOT', 'HUD', 'LLC'}
SMALL = {'and', 'or', 'of', 'the', 'to', 'in', 'on', 'for', 'by', 'at', 'a', 'an'}
def bill_title(t):
    for a, b in ABBR: t = re.sub(a, b, t)
    out = []
    for i, w in enumerate(re.split(r'(\s+|-|/|&)', t)):
        if not w.strip() or w in '-/&': out.append(' – ' if w == '-' else w); continue
        u = w.upper(); out.append(u if u in KEEP else w if not w.isupper() else (w.lower() if i and w.lower() in SMALL else w.capitalize()))
    return re.sub(r'\s+', ' ', ''.join(out)).strip()
def syn_clean(t): return re.sub(r'^(Reinserts|Replaces everything after the enacting clause with) the provisions of the (introduced|engrossed) bill with (the following )?changes\.\s*', '', t)
def act(a):
    m = re.search(r'Public Act[ .]*(\d+-\d+)', a)
    return f'Became Public Act {m.group(1)}' if m else a
def spr_card():
    try: L = json.load(open(os.path.join(ROOT, 'tracker', 'bills.json')))['bills']
    except Exception: L = []
    law = sum(1 for b in L if b['st'] == 6); moving = sum(1 for b in L if 3 <= b['st'] < 6 and b['lab'] != 'Vetoed')
    return (f(len(L)), 'bills in Springfield on Chicago’s housing, transit and money this session', minisplit([(law, NAVY), (moving, '#7fa3d1'), (max(0, len(L) - law - moving), '#d9e4f4')], 'Law · passed a chamber · still waiting'), f'{f(law)} became law; the session ends in January')
def springfield():
    try: B = json.load(open(os.path.join(ROOT, 'tracker', 'bills.json')))
    except Exception: B = None
    if not B or not B.get('bills'):
        h1 = 'Bills in Springfield that would change Chicago’s housing, transit and budget.'
        return page('springfield', 'In Springfield', h1, top('springfield', 'In Springfield', h1, 'The bill list is being gathered') + '<p class="sub">The first download of bill statuses hasn’t finished yet. Check back tomorrow.</p>' + bottom('springfield', '', ''))
    L = B['bills']; n = len(L)
    cnt = lambda st: sum(1 for b in L if b['st'] == st)
    law, sent, both, one, out, com = cnt(6), cnt(5) , cnt(4), cnt(3), cnt(2), cnt(1) + cnt(0)
    vet = sum(1 for b in L if b['lab'] == 'Vetoed'); sent -= vet
    made = B.get('made', '')
    h1 = f'{f(n)} bills in this session of the General Assembly would change Chicago’s housing, transit, budget, pensions or property taxes. {f(law)} have become law.'
    tl = tiles([(f(law), 'became law'), (f(sent + both), 'passed both chambers, waiting on the governor'), (f(one), 'passed one chamber'), (f(com + out), 'still in committee or waiting for a vote')])
    def row(b):
        name = WATCH.get(b['id']) or bill_title(b['t'])
        cls = 'good' if b['st'] == 6 else 'go' if b['st'] >= 3 else ''
        tags = ''.join(f'<span class="btag">{TOPIC[t]}</span>' for t in b['tp'])
        last = b['last']; when = day(last[0], True) if last[0] else ''
        hist = ''.join(f'<li><span>{day(d, True) if d else ""}</span> {esc(c)}: {esc(act(a))}</li>' for d, c, a in b['hist'])
        return (f'<li class="bill" data-tp="{" ".join(b["tp"])}" data-st="{b["st"]}"><div class="bh"><a class="bid" href="{b["url"]}" target="_blank" rel="noopener">{b["id"][:2]} {b["id"][2:]}</a>'
                f'<span class="chip {cls}">{esc(b["lab"])}</span>{tags}</div><b class="bt">{esc(name)}</b>'
                f'<p class="fine">Sponsor: {b["bych"]} {esc(b["by"])} · last action {when}: {esc(act(last[2]))}{" · rewritten by an amendment" if b.get("rewritten") else ""}</p>'
                f'<details><summary>What it does</summary><p class="sub">{esc(syn_clean(b["syn"]))}{"…" if len(b["syn"]) >= 900 else ""}</p>' + (f'<ol class="bhist">{hist}</ol>' if hist else '') + '</details></li>')
    order = sorted(L, key=lambda b: (-(b['id'] in WATCH), -b['st'], -int((b['last'][0] or '0').replace('-', ''))))
    filt = ('<div class="bfilt" role="group" aria-label="Show bills about"><button type="button" aria-pressed="true" data-t="">All</button>'
            + ''.join(f'<button type="button" aria-pressed="false" data-t="{k}">{v} <span>{sum(1 for b in L if k in b["tp"])}</span></button>' for k, v in TOPIC.items())
            + '</div><div class="bfilt" role="group" aria-label="Show bills that"><button type="button" aria-pressed="true" data-s="0">Any stage</button><button type="button" aria-pressed="false" data-s="3">Passed a chamber or more</button><button type="button" aria-pressed="false" data-s="6">Became law</button></div>')
    c1 = card('Every bill on these topics', f'Newest action first within each stage. Bill names are the legislature’s own short titles unless we give a plain one. Tap a number for the bill’s official page.',
              filt + f'<ol class="bills" id="bills">{"".join(row(b) for b in order)}</ol><p class="fine" id="bcount"></p><button type="button" class="sc-btn" id="bmore" hidden>Show 20 more</button>')
    g = goal('Bills die when the session ends', 'This General Assembly’s term ends in January 2027. Bills that haven’t passed both chambers by then have to be filed again and start over. The governor said in October that his housing plan may wait until the new session.', 'Vandalia Radio, Oct. 19, 2026', VANDALIA)
    note = ('A bill is listed if what it amends (the Illinois Compiled Statutes sections) or its synopsis is about zoning and housing, the transit agencies, Chicago’s taxes and budget, the four city pension funds, or property taxes in Cook County. '
            'Some listed bills only touch a topic in passing; bills that change only a title or make technical changes are left out. Stages come from each bill’s list of actions.')
    js = ('<script>(function(){const L=[...document.querySelectorAll("#bills .bill")],F=document.querySelectorAll(".bfilt button");let t="",s=0;'
          'let lim=20;const M=document.getElementById("bmore");const go=()=>{let n=0;L.forEach(e=>{const ok=(!t||e.dataset.tp.split(" ").includes(t))&&+e.dataset.st>=s;e.hidden=!ok||n>=lim;if(ok)n++;});document.getElementById("bcount").textContent="Showing "+Math.min(n,lim)+" of "+n+" bills";M.hidden=n<=lim;};M.addEventListener("click",()=>{lim+=20;go();});'
          'F.forEach(b=>b.addEventListener("click",()=>{const g=b.parentNode;g.querySelectorAll("button").forEach(x=>x.setAttribute("aria-pressed",String(x===b)));if("t" in b.dataset)t=b.dataset.t;else s=+b.dataset.s;lim=20;go();}));go();})();</script>')
    return page('springfield', 'In Springfield', h1, top('springfield', 'In Springfield', h1, f'Bill statuses from the Illinois General Assembly, updated every morning · last updated {day(made, True) if made else ""}') + tl + c1 + g
                + bottom('springfield', note, src('Illinois General Assembly bill status files', 'https://www.ilga.gov/ftp/legislation/104/BillStatus/')) + js)

# ---------------------------------------------------------------- decisions coming up
# Big votes with a date. Facts only: what's on the table, who decides, the dates, how to weigh in, sources. Each has a
# `checked` date: update the text and the date together when the story moves. A decision whose vote date has passed
# drops off the overview (DECISIONS, `vote`); its page keeps saying the vote date has passed until it's updated.
def src(t, u): return f'<a href="{u}" target="_blank" rel="noopener">{t}</a>'
CBS_BUDGET = 'https://www.cbsnews.com/chicago/news/chicago-city-council-mayor-budget-plan-2027-nonstarter/'
OV27 = 'https://www.chicago.gov/content/dam/city/depts/obm/2027_Budget/Budget_Recommendation/2027_Budget_Overview/2027_Budget_Overview%20(1).pdf'
FOX_BUDGET = 'https://www.fox32chicago.com/news/chicago-city-council-draws-budget-battle-lines-ahead-dec-30-deadline'
NITA_BUDGET = 'https://nita.illinois.gov/about-rta/press-releases/northern-illinois-transit-authoritys-first-regional-budget-proposal-expands-service-creates-jobs-and-improves-safety-across-six-counties'
NITA_COMMENT = 'https://nita.illinois.gov/transit-funding/2027-regional-transit-budget'
DECISIONS = [
  {'slug': 'city-budget-2027', 'vote': '2026-12-31', 'what': 'Deadline', 'mon': 'DEC', 'd': '31', 'checked': 'Nov. 12, 2026',
   'name': 'The 2027 city budget', 'card': '$882 million gap to close · the Council must pass a budget by year’s end',
   'h1': 'The City Council has until the end of the year to pass a 2027 budget that closes an $882 million gap.',
   'who': 'The Mayor proposes the budget and the City Council passes it. It takes 26 of the 50 alderpeople’s votes.',
   'tiles': [('$882M', 'gap in the $17.6 billion 2027 budget, between what the city expects to collect and to spend'), ('26 votes', 'needed in the City Council to pass a budget'), ('28', 'alderpeople signed a letter on Nov. 10 calling the Mayor’s plan a “non-starter”')],
   'sides': [('The Mayor’s plan', ['A new tax on big employers: $25 a month per worker at companies with 125 or more full-time workers, about $114 million a year', 'Raise the tax on leased equipment and cloud software from 15% to 20%, about $234 million a year', 'Put $75 million from the parking meter deal toward 2027 pension payments', 'Savings, one-time money and other fees for the rest (each one is in the budget simulator)']),
             ('What the 28 alderpeople wrote', ['No more than $300 million in new or higher taxes', 'No head tax and no lease tax increase (the lease tax went from 11% to 15% in the 2026 budget)', 'Collect more of the money people and businesses already owe the city', 'Close less of the gap with one-time money and borrowing (the plan counts on $480 million in police settlement borrowing)', 'The Council voted 44–6 to spend the $75 million on an extra pension payment this year instead'])],
   'dates': [('2026-10-31', 'October', 'The Mayor sends his 2027 budget to the City Council'), ('2026-11-10', 'Nov. 10', 'Department hearings end; 28 alderpeople send their letter; the Mayor writes back that he is open to changing the lease tax increase'),
             ('2026-12-09', 'Dec. 8–9', 'Next full City Council meetings (a final vote may come later)'), ('2026-12-31', 'Dec. 31', 'Deadline to pass a 2027 budget. Last year’s passed on Dec. 20')],
   'weigh': [('Email your alderperson', '/wards/', 'Find your ward, how to reach its office and the Council meetings coming up'), ('Try closing the gap yourself', '/budget/', 'Every tax, cut and one-time option, with what it costs you'), ('Follow the news', '/news/', 'Headlines on the budget from Chicago outlets, updated every few hours')],
   'sources': [src('CBS Chicago, Nov. 11, 2026', CBS_BUDGET), src('ABC7 Chicago, Nov. 10, 2026', 'https://abc7chicago.com/post/chicago-budget-news-city-council-coalition-says-mayor-brandon-johnsons-plan-corporate-head-tax-lacks-votes-pass/20031112/'), src('Chicago Sun-Times, Nov. 10, 2026', 'https://chicago.suntimes.com/city-hall/2026/11/10/city-council-aldermanic-opposition-letter-mayor-brandon-johnson-proposed-budget-revamp-demand'), src('City of Chicago, 2027 Budget Overview', OV27), src('FOX 32, Sept. 28, 2026', FOX_BUDGET)],
   'note': 'The gap, the head tax figure and the $17.6 billion total are from the city’s 2027 Budget Overview; CBS Chicago reported a newer Mayor’s office estimate of about $101 million for the head tax. The lease tax figure is the Mayor’s $46.8 million per point, as in the budget simulator.'},
  {'slug': 'transit-budget-2027', 'vote': '2026-12-10', 'what': 'Board vote', 'mon': 'DEC', 'd': '10', 'checked': 'Nov. 12, 2026',
   'name': 'The first regional transit budget', 'card': '$5.04 billion for CTA, Metra and Pace · comments close Dec. 4',
   'h1': 'The new regional transit agency votes Dec. 10 on its first budget: $5.04 billion to run CTA, Metra and Pace in 2027.',
   'who': 'The Northern Illinois Transit Authority (NITA), set up by the 2025 state transit law, writes one budget for CTA, Metra and Pace. Its board votes on it.',
   'tiles': [('$5.04B', 'to run CTA, Metra and Pace in 2027'), ('$1.3B', 'of that is new money from the 2025 transit law'), ('$9.73B', 'for repairs and new projects, 2027–2031'), ('No increase', 'in fares in 2027')],
   'sides': [('What the new money would add', ['More CTA routes in the Frequent Bus Network, and six more CTA bus routes running all night', 'Sunday service on some Pace routes', 'More Rock Island trains on Metra', 'Free transfers between CTA and Pace; reduced fares and student fares made permanent', 'Transit ambassadors (summer 2027) and a fare gate pilot']),
             ('Repairs and projects, 2027–2031', ['$3.29 billion for the Red Line Extension', 'More than 200 electric or hybrid buses for CTA and Pace', '$483 million for Metra rail cars', '$218 million for Pace buses', '$990 million of the five-year total is new money from the law'])],
   'dates': [('2026-11-02', 'Nov. 2', 'Proposed budget released'), ('2026-11-12', 'Nov. 12', 'Public hearing at the board meeting (comments from about 4 p.m. to 6 p.m.), 175 W. Jackson Blvd. and on Zoom; the six county boards also hear it in November'),
             ('2026-12-04', 'Dec. 4', 'Written comments close'), ('2026-12-10', 'Dec. 10', 'Board votes, 9 a.m.'), ('2026-12-31', 'Dec. 31', 'The law’s deadline for the first regional budget')],
   'weigh': [('Comment on the budget', NITA_COMMENT, 'NITA’s page with the full proposal and how to comment'), ('See what new service does', '/transit/', 'Switch on proposals and see riders, cost and trip times'), ('What the 2025 law changed', '/learn/#nita', 'One minute on the new agency and its money')],
   'sources': [src('NITA press release, Nov. 2026', NITA_BUDGET), src('NITA: 2027 regional transit budget', NITA_COMMENT)],
   'note': 'All figures are from NITA’s proposal. The board can change it before the vote.'},
]
def decision(D):
    li = ''.join(f'<li data-date="{iso}"><span class="when">{d}</span><span class="what">{t}</span><span class="st"></span></li>' for iso, d, t in D['dates'])
    sides = ''.join(f'<section class="card pad"><h2>{t}</h2><ul class="dot">' + ''.join(f'<li>{x}</li>' for x in L) + '</ul></section>' for t, L in D['sides'])
    weigh = ''.join(f'<a class="card wy" href="{u}"' + (' target="_blank" rel="noopener"' if u.startswith('http') else '') + f'><b>{t} ›</b><span>{x}</span></a>' for t, u, x in D['weigh'])
    body = (f'<div class="top sc-pghead"><div><p class="eyebrow"><a href="/progress/">Progress</a> <span aria-hidden="true">›</span> <a href="/progress/decisions/">Decisions</a></p><h1>{D["h1"]}</h1>'
            f'<p class="fine">{D["what"]}: <span data-until="{D["vote"]}"></span> · checked {D["checked"]}</p></div>{art("decisions")}</div>'
            + tiles(D['tiles'], cols=len(D['tiles']))
            + card('Who decides', '', f'<p class="sub">{D["who"]}</p>')
            + f'<div class="strip c2">{sides}</div>'
            + card('The dates', '', f'<ol class="dl">{li}</ol>')
            + f'<section class="blk"><h2>How to weigh in</h2><div class="strip c3">{weigh}</div></section>'
            + f'<p class="fine note">{D["note"]}</p><p class="fine src"><b>Sources:</b> {" · ".join(D["sources"])}</p>')
    return page('decisions/' + D['slug'], D['name'], D['h1'], body)
def decisions_index():
    cards = ''.join(f'<a class="card dec" href="/progress/decisions/{D["slug"]}/"><span class="dt"><span>{D["mon"]}</span><b>{D["d"]}</b></span><span class="tx"><b>{D["name"]}</b><span>{D["card"]}</span></span><span class="go" data-until="{D["vote"]}"></span></a>' for D in sorted(DECISIONS, key=lambda D: D['vote']))
    h1 = 'Votes coming up on Chicago’s money, homes and transit.'
    body = (f'<div class="top sc-pghead"><div><p class="eyebrow"><a href="/progress/">Progress</a> <span aria-hidden="true">›</span> Decisions</p><h1>{h1}</h1><p class="fine">Each page says what’s on the table, who decides, the dates and how to weigh in.</p></div>{art("decisions")}</div>'
            f'<div class="strip c2">{cards}</div><p class="fine note">Bills in Springfield have their own page: <a href="/progress/springfield/">In Springfield ›</a></p>')
    return page('decisions', 'Decisions coming up', h1, body)

# ---------------------------------------------------------------- overview
def overview():
    built = sum(p[2] for p in PROJ); tot = sum(p[1] for p in PROJ)
    SECS = [('zoning', '3 in 10', 'zoning changes for a new building get a permit within a year', spark([31, 20, 12, 35, 45], rng=('Passed 2021', '2025')), '45% for 2025’s votes, the most in five years'),
            ('affordable', '29,550', 'homes on the city’s affordable rental list', minisplit([(10759, NAVY), (18791, '#d9e4f4')], 'For seniors · everyone else'), 'About 1 in 3 are for seniors · list dated Dec. 2024'),
            ('rents', '$2,311', 'typical asking rent, Sept. 2026', spark([RENT[y] for y in range(2019, 2027)], rng=('2019', '2026')), '▲ Up 5.7% in a year'),
            ('transit', '70%', 'of 2019’s CTA rides in 2025, counted the same way', spark([626, 605, 586, 571, 550, 231, 226, 285, 331, 367, 381], rng=('2015', '2025')), '▲ Up 2.6% in 2026 · 7 big projects tracked'),
            ('streets', '82 deaths', 'in traffic this year through Sept. 27', spark([120, 153, 186, 160, 136, 130, 100, 82], partial=True, rng=('2019', '2026 so far')), 'The city’s goal for 2026 was zero'),
            ('projects', f'{f(built)} of {f(tot)}', 'homes built in six big projects', minisplit([(built, NAVY), (tot - built, '#d9e4f4')], 'Built · planned'), '3 of the 6 have broken ground'),
            ('springfield', *spr_card()),
            ('capital', '$18.1B', 'in the city’s five-year building plan, 2025–2029', minisplit([(5980, NAVY), (3673 + 1893, '#7fa3d1'), (3034 + 1447, '#b3c9e6'), (2024, '#d9e4f4')], 'Airports · water and sewers · streets · the rest'), 'Plus $1.5M a year per ward for street projects')]
    name = dict(SECTIONS)
    head = (f'<div class="otop"><div><h1>Progress</h1><p>What Chicago built, rezoned and ran, and where its big projects stand. Counted from public records and updated every day.</p></div><span class="upd">Updated {UPDATED}</span></div>')
    lead = (f'<a class="card lead" href="/progress/homes/"><div class="l"><span class="lab">Homes permitted in 2026</span><div class="n"><b>{f(ytd["homes"])}</b>{PACE}</div>'
            f'<p class="sub">Chicago needed <b>{f(ytd["needed_so_far"])}</b> by {THRU} to stay on pace to end its share of the housing shortage by 2041.</p>'
            f'<div class="m">{meter(pct)}<p class="fine"><span><b>{pct}%</b> of the pace</span><span>{f(ytd["needed_so_far"])} needed by now</span></p></div>'
            f'<div class="mini"><div><b>{"▼" if vs < 0 else "▲"} {abs(vs)}%</b><span>vs. this date last year ({f(ytd["prev"])})</span></div><div><b>About {f(net26)}</b><span>net gain after homes torn down</span></div></div>'
            f'<span class="go">Homes added ›</span></div><div class="r"><span class="cap">Homes permitted each year</span>{yearchart(False, 190)}</div></a>')
    def dec(href, mon, d, iso, title, what):
        return (f'<a class="card dec" href="{href}"><span class="dt"><span>{mon}</span><b>{d}</b></span><span class="tx"><b>{title}</b><span>{what}</span></span><span class="go" data-until="{iso}"></span></a>')
    up = sorted([D for D in DECISIONS if D['vote'] >= TODAY], key=lambda D: D['vote'])
    decs = ('<section class="blk"><h2>Decisions coming up <a class="more" href="/progress/decisions/">All ›</a></h2><div class="strip c2">'
            + ''.join(dec(f'/progress/decisions/{D["slug"]}/', D['mon'], D['d'], D['vote'], D['name'], D['card']) for D in up[:2]) + '</div></section>') if up else ''
    cards = ''.join(f'<a class="card sec" href="/progress/{k}/"><span class="t">{name[k]}<span aria-hidden="true">›</span></span><span class="n{" sm" if len(n) > 9 else ""}">{n}</span><span class="d">{d}</span>{g}<span class="ch">{c}</span></a>' for k, n, d, g, c in SECS)
    grid = f'<section class="blk"><h2>Everything else we count</h2><div class="grid4">{cards}</div></section>'
    foot = '<p class="fine src">Each section lists its own sources and shows the date its data runs through. Homes permitted updates every morning; the other sections were last checked ' + SNAP + '.</p>'
    return page('', 'Progress', 'What Chicago built, rezoned and ran, and where its big projects stand, counted from public records.', head + lead + decs + grid + foot)

# ---------------------------------------------------------------- Progress, next version (preview at /progress/preview/; Kyle asked to see it before it replaces the overview)
LAWS = [('2021-03-17', 'Demolition fee near the 606 and in Pilsen'), ('2021-04-21', 'Affordable housing rule raised (ARO)'), ('2022-07-20', 'More homes allowed near transit (ETOD)'),
        ('2025-05-21', 'Green Social Housing fund'), ('2025-10-08', 'Taller buildings on commercial streets'), ('2026-02-18', 'Coach houses in more areas')]
def lawchart():
    """Homes permitted each year since 2013, with the dates citywide housing laws passed marked on the timeline."""
    ys = list(range(2013, 2027)); vals = [ytd['homes'] if y == 2026 else Y[y]['homes'] for y in ys]
    W, H, L, R_, T_, B_ = 1000, 300, 46, 16, 64, 34; top = 12000
    xw = (W - L - R_) / len(ys); yv = lambda v: T_ + (H - T_ - B_) * (1 - v / top)
    g = ''.join(f'<line x1="{L}" x2="{W - R_}" y1="{yv(v):.1f}" y2="{yv(v):.1f}" stroke="#eceef1"/><text x="{L - 6}" y="{yv(v) + 4:.1f}" text-anchor="end" font-size="12" fill="#6a7079">{v // 1000}k</text>' for v in (0, 4000, 8000, 12000))
    for i, (y, v) in enumerate(zip(ys, vals)):
        x = L + i * xw + xw * 0.18; w = xw * 0.64; fill = HATCH(NAVY, '#fff') if y == 2026 else NAVY
        g += f'<rect x="{x:.1f}" y="{yv(v):.1f}" width="{w:.1f}" height="{yv(0) - yv(v):.1f}" rx="3" fill="{NAVY if y < 2026 else "url(#hp)"}"/>'
        g += f'<text x="{x + w / 2:.1f}" y="{H - 12}" text-anchor="middle" font-size="12" fill="#3d434b">{"’" + str(y)[2:]}</text>'
    rows = []
    for k, (iso, name) in enumerate(LAWS):
        yy, mm, dd = map(int, iso.split('-')); fx = L + (yy - 2013 + (mm - 1 + dd / 31) / 12) * xw
        lane = k % 2; ly = 12 + lane * 22
        g += f'<line x1="{fx:.1f}" x2="{fx:.1f}" y1="{ly + 6}" y2="{yv(0):.1f}" stroke="{RED}" stroke-width="1.4" stroke-dasharray="3 3"/><circle cx="{fx:.1f}" cy="{ly + 2}" r="8" fill="{RED}"/><text x="{fx:.1f}" y="{ly + 6}" text-anchor="middle" font-size="11" font-weight="700" fill="#fff">{k + 1}</text>'
        rows.append(f'<li><span class="lk">{k + 1}</span><span>{name}</span><span class="ld">{MON[mm - 1]} {yy}</span></li>')
    svg = (f'<svg class="lawsvg" viewBox="0 0 {W} {H}" role="img" aria-label="Homes permitted each year from 2013 to 2026, with the dates six citywide housing laws passed. Permits fell from 9,000–10,000 a year before 2020 to about 4,000 since.">'
           f'<defs><pattern id="hp" width="6" height="6" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><rect width="6" height="6" fill="#fff"/><rect width="3" height="6" fill="{NAVY}"/></pattern></defs>{g}</svg>')
    return '<div class="lawwrap">' + svg + '</div>' + f'<ol class="laws">{"".join(rows)}</ol>'
def funnel():
    """Rezonings for a new building → a permit within 12 and 24 months, by the year the Council passed them (the Zoning page's table)."""
    data = [(2021, 42, 31, 43), (2022, 51, 20, 35), (2023, 57, 12, 33), (2024, 63, 35, 46)]
    out = ''
    for y, n, p12, p24 in data:
        out += (f'<div class="fn"><span class="fy">{y}</span><div class="fb"><i style="width:100%;background:#d9e4f4"></i><i style="width:{p24}%;background:#7fa3d1"></i><i style="width:{p12}%;background:{NAVY}"></i></div>'
                f'<span class="fv"><b>{p12}%</b> in a year · <b>{p24}%</b> in two · of {n}</span></div>')
    return f'<div class="funnel">{out}</div>' + key([('Permit within 12 months', NAVY, ''), ('Within 24 months', '#7fa3d1', ''), ('No permit yet after 24 months', '#d9e4f4', '')])
def preview():
    hold, close, gap0, gr = goal_['hold'], goal_['close'], goal_['gap_now'], goal_['gap_growth']
    pace = l12['homes']; yrs = 2041 - int(T['through'][:4])
    if pace > hold: verdict = f'At the last 12 months’ pace, Chicago closes its share of the shortage in about {round(gap0 / (pace - hold))} years.'
    else: verdict = f'At the last 12 months’ pace, the gap doesn’t close: it grows from {f(gap0)} homes today to about {f(round((gap0 + yrs * (hold - pace)) / 1000) * 1000)} by 2041.'
    h1 = f'Chicago permitted {f(pace)} homes in the last 12 months. Closing its share of the shortage by 2041 takes {f(close)} a year.'
    # report card rows: what, now, a year earlier, the official goal, status, trend
    D = STR or STR0; de, se = D['deaths'], D['serious']
    TRS = json.load(open(os.path.join(ROOT, 'tracker', 'transit.json'))) if os.path.exists(os.path.join(ROOT, 'tracker', 'transit.json')) else None
    rows = []
    def chip(t, kind): return f'<span class="chip {kind}">{t}</span>'
    ys = list(range(2016, 2027))
    rows.append(('<a href="/progress/homes/">Homes permitted</a>', f'{f(pace)} <small>last 12 months</small>', f(Y[2025]['homes']) + ' <small>in 2025</small>', f'{f(close)} a year <small>(our estimate, not the city’s)</small>', chip('▼ Behind' if pace < close else '▲ On pace', 'bad' if pace < close else 'good'), spark([Y[y]['homes'] for y in ys[:-1]] + [ytd['homes']], partial=True, rng=('2016', '2026'))))
    n25, n24 = Y[2025]['homes'] - DEMO[2025], Y[2024]['homes'] - DEMO[2024]
    rows.append(('<a href="/progress/homes/#lost">Homes added after teardowns</a>', f'about {f(round(n25, -1))} <small>in 2025</small>', f'about {f(round(n24, -1))} <small>in 2024</small>', '<span class="tbd">no official target</span>', chip('▲ Up' if n25 > n24 else '▼ Down', 'good' if n25 > n24 else 'bad'), spark([Y[y]['homes'] - DEMO[y] for y in ys[:-1]], rng=('2016', '2025'))))
    if TL and len(TL.get('years', {})) >= 2:
        ty = sorted(TL['years']); tc, tp = TL['years'][ty[-1]]['all'], TL['years'][ty[-2]]['all']
        rows.append(('<a href="/progress/homes/#homes-timelines">Days from application to permit</a>', f'{tc["med"]} days <small>{ty[-1]}, middle permit</small>', f'{tp["med"]} days <small>{ty[-2]}</small>', '<span class="tbd">no official target</span>',
                     chip('▼ Faster' if tc['med'] < tp['med'] else '▲ Slower', 'good' if tc['med'] < tp['med'] else 'bad'), ''))
    rows.append(('<a href="/progress/zoning/">Rezonings built within a year</a>', '45% <small>of 2025’s</small>', '35% <small>of 2024’s</small>', '<span class="tbd">no official target</span>', chip('▲ Up', 'good'), spark([31, 20, 12, 35, 45], rng=('2021', '2025'))))
    if AFF and AFF.get('rows'):
        H = SRC.get('hud') or {}
        rows.append(('<a href="/progress/affordable/">Homes with federal rent help</a>', f(H['2025']['all']) + ' <small>in 2025</small>', f(H['2024']['all']) + ' <small>in 2024</small>', '<span class="tbd">no official target</span>',
                     chip('▼ Down' if H['2025']['all'] < H['2024']['all'] else '▲ Up', 'bad' if H['2025']['all'] < H['2024']['all'] else 'good'), spark([H[str(y)]['all'] for y in range(2014, 2026)], rng=('2014', '2025'))))
    real = {y: RENT[y] * CPI[2026] / CPI[y] for y in RENT}
    rows.append(('<a href="/progress/rents/">Typical asking rent</a>', f'${f(RENT[2026])} <small>Jan. 2026</small>', f'${f(RENT[2025])} <small>Jan. 2025</small>', '<span class="tbd">no official target</span>',
                 chip(f'▲ Up {round(100 * (RENT[2026] / RENT[2025] - 1))}%', 'bad'), spark([RENT[y] for y in range(2019, 2027)], rng=('2019', '2026'))))
    if TRS:
        ser = TRS['series']; thru = TRS['through']; yy, mm = int(thru[:4]), int(thru[5:7])
        tot = lambda y: sum(ser[k].get(f'{y}-{m:02d}', 0) for k in ('cta_bus', 'cta_rail') for m in range(1, mm + 1))
        a, b = tot(yy), tot(yy - 1)
        rows.append(('<a href="/progress/transit/">CTA rides</a>', f'{a / 1e6:.0f}M <small>{MON[0]}–{MON[mm - 1]} {yy}</small>', f'{b / 1e6:.0f}M <small>same months {yy - 1}</small>', '<span class="tbd">no official target</span>',
                     chip(f'{"▲ Up" if a >= b else "▼ Down"} {abs(round(100 * (a / b - 1), 1))}%', 'good' if a >= b else 'bad'), spark([sum(ser[k].get(f'{y}-{m:02d}', 0) for k in ('cta_bus', 'cta_rail') for m in range(1, mm + 1)) for y in range(2019, yy + 1)], partial=True, rng=('2019', str(yy)))))
    rows.append(('<a href="/progress/streets/">Traffic deaths</a>', f'{f(de["ytd"])} <small>through {day(de["through"])}</small>', f'{f(de["ytd_prev"])} <small>same dates last year</small>', 'zero <small>(Vision Zero, by 2026)</small>',
                 chip('▲ More' if de['ytd'] > de['ytd_prev'] else '▼ Fewer', 'bad' if de['ytd'] > de['ytd_prev'] else 'good'), spark([de['years'][str(y)] for y in range(2019, 2027)], partial=True, rng=('2019', '2026'))))
    card_rows = ''.join(f'<tr><th scope="row">{a}</th><td class="n">{b}</td><td class="n">{c}</td><td>{d}</td><td>{e}</td><td class="sp">{g}</td></tr>' for a, b, c, d, e, g in rows)
    rc = card('The scoreboard', 'Each line: where it stands now, a year earlier, the goal, and the trend. The city has an official goal only for traffic deaths; the homes goal is ours, from the housing simulator.',
              f'<div class="tw"><table class="rc"><thead><tr><th>What we count</th><th class="n">Now</th><th class="n">A year earlier</th><th>Goal</th><th>Direction</th><th>Trend</th></tr></thead><tbody>{card_rows}</tbody></table></div>')
    pace_c = card('At this pace', '', f'<p class="big">{verdict}</p><p class="sub">Holding the gap where it is takes {f(hold)} homes a year (the {f(goal_["built_anyway"])} built in a normal year plus the {f(gr)} a year the shortage grows); closing it by 2041 takes {f(close)}. The pace and the goal are the housing simulator’s, an estimate.</p>')
    laws = card('What happened after each law', 'Homes permitted each year, with the dates the City Council passed citywide housing laws. A chart like this shows timing, not cause: interest rates, the pandemic and costs moved at the same time.', lawchart())
    fun = card('From zoning vote to building permit', 'Zoning changes passed for a new residential building, by the year they passed: how many had a building permit within one and two years.', funnel() + '<p class="sub"><a href="/progress/zoning/">Every year and the finished homes ›</a></p>')
    nxt = card('Also coming with this version', '', '<ul class="dot"><li>A page for each of the 50 wards and 77 neighborhoods: homes permitted, rezonings, teardowns, affordable homes, crashes and transit, against the city.</li><li>“What changed this week” at the top, written automatically from the daily data.</li><li>A CSV download under each chart, next to Embed.</li></ul>')
    body = (f'<div class="top"><p class="eyebrow"><a href="/progress/">Progress</a> <span aria-hidden="true">›</span> Preview of the next version</p><h1>{h1}</h1><p class="fine">Updated {UPDATED} · a preview: the current Progress overview stays until you approve this one</p></div>'
            + pace_c + rc + laws + fun + nxt)
    return page('preview', 'Progress preview', h1, body)

CSS = '''/* Progress pages (written by tools/progress/build.py) */
*{box-sizing:border-box}
html{background:var(--sc-page)}
body.pg{margin:0;background:var(--sc-page);font-family:var(--sc-font);color:var(--sc-ink);font-variant-numeric:tabular-nums;-webkit-font-smoothing:antialiased}
.pg .sc-head{position:sticky;top:0}
.pg main{max-width:var(--sc-w-wide);margin:0 auto;padding:22px 20px 56px;display:flex;flex-direction:column;gap:22px}
.pg main a{color:var(--sc-navy)}
.pg .card{background:#fff;border:1px solid var(--sc-line);border-radius:18px;box-shadow:0 1px 2px rgba(20,30,50,.04)}
.pg a.card{text-decoration:none;color:var(--sc-ink);transition:transform .15s,border-color .15s,box-shadow .15s}
@media (hover:hover){ .pg a.card:hover{transform:translateY(-2px);border-color:var(--sc-navy);box-shadow:0 6px 18px rgba(43,93,160,.14)} }
.pg .pad{padding:22px 24px;display:flex;flex-direction:column;gap:14px;min-width:0}
.pg h1{margin:0;font-size:32px;line-height:1.2;letter-spacing:-.02em;font-weight:600;max-width:900px}
.pg h2{margin:0;font-size:18px;font-weight:600;letter-spacing:-.01em}
.pg h3{margin:0 0 10px;font-size:14.5px;font-weight:600}.pg h3 span{font-weight:400;color:var(--sc-mute)}
.pg .hd{display:flex;flex-direction:column;gap:4px}
/* preview: scoreboard, law chart, funnel */
.pg table.rc{width:100%;border-collapse:collapse;font-size:14.5px}.pg table.rc th,.pg table.rc td{padding:12px 10px;border-top:1px solid var(--sc-line);text-align:left;vertical-align:middle}
.pg table.rc thead th{border-top:0;font-size:12.5px;color:var(--sc-mute);font-weight:600}.pg table.rc tbody th{font-weight:600}.pg table.rc tbody th a{color:var(--sc-ink);text-decoration:none}.pg table.rc tbody th a:hover{color:var(--sc-navy);text-decoration:underline}
.pg table.rc td.n{text-align:right;white-space:nowrap;font-weight:600}.pg table.rc small{display:block;font-weight:400;color:var(--sc-mute);font-size:12px}.pg table.rc td.sp{width:150px}.pg table.rc .spark{margin:0}
@media (max-width:760px){ .pg table.rc thead{display:none}.pg table.rc tr{display:grid;grid-template-columns:1fr 1fr;gap:4px 12px;padding:12px 0;border-top:1px solid var(--sc-line)}.pg table.rc th,.pg table.rc td{border:0;padding:0}.pg table.rc tbody th{grid-column:1/-1}.pg table.rc td.n{text-align:left}.pg table.rc td.sp{grid-column:1/-1;width:auto} }
.pg .big{margin:0;font-size:22px;line-height:1.35;font-weight:600;letter-spacing:-.01em;max-width:860px}
.pg svg.lawsvg{width:100%;height:auto;display:block}.pg .lawwrap{overflow-x:auto}@media (max-width:640px){ .pg svg.lawsvg{min-width:620px} }
.pg ol.laws{list-style:none;margin:6px 0 0;padding:0;display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:6px 18px;font-size:13.5px}
.pg ol.laws li{display:flex;gap:8px;align-items:baseline}.pg .lk{flex:none;width:18px;height:18px;border-radius:50%;background:#b3001e;color:#fff;font-size:11px;font-weight:700;display:inline-grid;place-items:center}.pg .ld{margin-left:auto;color:var(--sc-mute);white-space:nowrap}
.pg .funnel{display:flex;flex-direction:column;gap:10px}.pg .fn{display:grid;grid-template-columns:48px minmax(0,1fr) auto;gap:12px;align-items:center;font-size:13.5px}
.pg .fb{position:relative;height:22px;border-radius:6px;overflow:hidden}.pg .fb i{position:absolute;left:0;top:0;bottom:0}.pg .fy{font-weight:600}.pg .fv{color:var(--sc-ink2);white-space:nowrap}
@media (max-width:640px){ .pg .fn{grid-template-columns:40px minmax(0,1fr)}.pg .fv{grid-column:2} }
/* embed button on a card, the embed dialog, and the embed pages (/embed/<id>/) */
.pg .hd .embb{order:2;align-self:flex-start;margin-top:4px;border:1px solid var(--sc-line);background:#fff;color:var(--sc-navy);font:600 12.5px var(--sc-font);border-radius:999px;padding:4px 11px;cursor:pointer}
@media (pointer:coarse){ .pg .hd .embb{min-height:34px;padding:6px 14px} }
@media (min-width:700px){ .pg .hd{position:relative;padding-right:84px} .pg .hd .embb{position:absolute;right:0;top:-2px;margin:0} }
.pg .hd .embb:hover{border-color:var(--sc-navy)}
dialog.embd{border:0;border-radius:18px;padding:22px 24px;max-width:min(560px,calc(100vw - 32px));width:100%;box-shadow:0 20px 60px rgba(20,30,50,.25);font-family:var(--sc-font);color:var(--sc-ink)}
dialog.embd::backdrop{background:rgba(20,30,50,.35)}
dialog.embd h2{margin:0 0 6px;font-size:18px;font-weight:600}dialog.embd p{margin:0 0 12px;font-size:14px;line-height:20px;color:var(--sc-ink2)}
dialog.embd label{display:block;font-size:13px;font-weight:600;margin:12px 0 6px}
dialog.embd textarea,dialog.embd input{width:100%;font:13px/1.4 ui-monospace,Menlo,monospace;border:1px solid var(--sc-line);border-radius:10px;padding:10px;resize:vertical;color:var(--sc-ink)}
dialog.embd .row{display:flex;gap:8px;flex-wrap:wrap;margin-top:14px}
body.emb{background:#fff}body.emb main{padding:0;gap:0;max-width:none}body.emb .card{border:0;box-shadow:none;border-radius:0}
body.emb .embf{margin:0;padding:10px 24px 14px;border-top:1px solid var(--sc-line);font-size:12px;line-height:17px;color:var(--sc-mute)}body.emb .embf a{color:var(--sc-navy);font-weight:600;text-decoration:none}
.pg .cap{margin:0;font-size:13px;color:var(--sc-mute)}
.pg .sub{margin:0;font-size:14.5px;line-height:21px;color:var(--sc-ink2)}.pg .sub b,.pg .call b{color:var(--sc-ink)}
.pg .fine{margin:0;font-size:12.5px;line-height:18px;color:var(--sc-mute)}
.pg .lede{margin:0;font-size:15.5px;line-height:23px;color:var(--sc-ink2);max-width:860px}
.pg .call{margin:0;font-size:14.5px;line-height:21px;color:var(--sc-ink2);background:#f6f7f9;border-radius:12px;padding:12px 14px}
.pg .note{max-width:980px}.pg .src{max-width:980px}
.pg .top.sc-pghead{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,360px);gap:28px;align-items:center}.pg .top.sc-pghead .sc-pgart{max-height:200px;width:auto;max-width:100%;justify-self:end}
@media (max-width:760px){.pg .top.sc-pghead{grid-template-columns:minmax(0,1fr);gap:4px}.pg .top.sc-pghead .sc-pgart{max-height:130px;justify-self:start}}
.pg .eyebrow{margin:0;font-size:14px;font-weight:600;color:var(--sc-mute)}.pg .eyebrow a{color:var(--sc-navy);text-decoration:underline;text-underline-offset:2px;text-decoration-color:rgba(43,93,160,.45)}.pg .eyebrow a:hover{text-decoration-color:currentColor}
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
.pg .hb > div > span{min-width:0;overflow-wrap:anywhere}
@media (max-width:420px){ .pg .hb > div{gap:8px;font-size:13px} }
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
.pg ol.bills{list-style:none;margin:0;padding:0;display:flex;flex-direction:column}
.pg li.bill{padding:14px 0;border-bottom:1px solid #f1f2f4;display:flex;flex-direction:column;gap:5px}.pg li.bill[hidden]{display:none}
.pg .bh{display:flex;flex-wrap:wrap;gap:6px 8px;align-items:center}.pg .bid{font-weight:700;font-size:14px;text-decoration:none;min-width:64px}
.pg .btag{font-size:12px;font-weight:600;color:var(--sc-ink2);background:#f1f3f6;border-radius:999px;padding:2px 9px}
.pg .bt{font-size:15.5px;font-weight:600;line-height:21px}
.pg li.bill details summary{cursor:pointer;font-size:13.5px;font-weight:600;color:var(--sc-navy)}.pg li.bill details .sub{margin-top:6px}
.pg ol.bhist{margin:8px 0 0;padding:0;list-style:none;font-size:13px;color:var(--sc-ink2);display:flex;flex-direction:column;gap:3px}.pg ol.bhist span{display:inline-block;min-width:96px;color:var(--sc-mute)}
.pg .bfilt{display:flex;flex-wrap:wrap;gap:6px;margin:0 0 4px}.pg .bfilt button{font:inherit;font-size:13.5px;font-weight:600;border:1px solid var(--sc-line2);background:#fff;color:var(--sc-ink2);border-radius:999px;padding:6px 12px;cursor:pointer;min-height:36px}
.pg .bfilt button span{font-weight:400;color:var(--sc-mute)}.pg .bfilt button[aria-pressed="true"]{background:var(--sc-navy);border-color:var(--sc-navy);color:#fff}.pg .bfilt button[aria-pressed="true"] span{color:#d9e4f4}
.pg [id]{scroll-margin-top:84px}
.pg .h2big{font-size:24px;line-height:1.25;letter-spacing:-.01em;margin:10px 0 0}.pg .sub2{margin-top:6px;padding-top:18px;border-top:1px solid var(--sc-line)}
.pg .blk h2 .more{font-size:14px;font-weight:600;margin-left:10px;text-decoration:none}
.pg ul.dot{margin:0;padding:0 0 0 18px;display:flex;flex-direction:column;gap:8px;font-size:14.5px;line-height:21px;color:var(--sc-ink2)}
.pg ul.dot li::marker{color:var(--sc-navy)}
.pg a.wy{display:flex;flex-direction:column;gap:4px;padding:16px 18px}.pg a.wy b{font-size:15.5px;color:var(--sc-navy)}.pg a.wy span{font-size:13.5px;color:var(--sc-ink2);line-height:19px}
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

MOVED_ROOM = '<!doctype html><html lang="en"><head><meta charset="utf-8"><title>Zoning · Progress · Shape Chicago</title><meta http-equiv="refresh" content="0; url=/progress/zoning/#room"><link rel="canonical" href="/progress/zoning/"></head><body><p><a href="/progress/zoning/#room">Room to grow is now part of Zoning.</a></p></body></html>\n'
MOVED = '<!doctype html><html lang="en"><head><meta charset="utf-8"><title>Homes added · Progress · Shape Chicago</title><meta http-equiv="refresh" content="0; url=/progress/homes/#lost"><link rel="canonical" href="/progress/homes/"></head><body><p><a href="/progress/homes/#lost">Homes lost is now part of Homes added.</a></p></body></html>\n'
SITE = 'https://shape-chicago.hd9bt6x5mn.workers.dev'   # launch to-do: the new domain
def write_embeds(pages):
    """/embed/<id>/: one card alone, for news sites to put in an iframe; /press/: the list, with how to cite."""
    script = re.search(r'<script>\n/\* "In N days".*?</script>', pages['homes'], re.S).group(0)
    E = os.path.join(ROOT, 'embed'); os.makedirs(E, exist_ok=True)
    rows = ''
    for eid, (sec, title, html) in EMB.items():
        P = PINFO.get(sec, {}); name = P.get('name', sec.title())
        thru = re.sub('<[^>]+>', '', P.get('thru', '')); src = P.get('src', '')
        doc = f'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(re.sub('<[^>]+>', '', title))} · Shape Chicago</title>
<meta name="robots" content="noindex"><link rel="canonical" href="/progress/{sec}/#{eid}"><base target="_blank">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Instrument+Sans:wght@400;500;600;700&display=swap" rel="stylesheet">
<link rel="stylesheet" href="/shape/shape.css"><link rel="stylesheet" href="/progress/progress.css">
</head>
<body class="pg emb">
<main>
{html}
<p class="embf"><a href="/progress/{sec}/#{eid}">Shape Chicago · Progress › {name}</a> · {esc(thru)}<br>Sources: {re.sub('<[^>]+>', '', src)} Not affiliated with the City of Chicago.</p>
</main>
{script}
<script>/* tell the page holding this iframe how tall it is (optional resize script on /press/) */
(function(){{ const send = () => parent.postMessage({{scEmbed: "{eid}", h: document.documentElement.scrollHeight}}, "*"); addEventListener("load", send); new ResizeObserver(send).observe(document.body); }})();</script>
</body>
</html>
'''
        os.makedirs(os.path.join(E, eid), exist_ok=True); open(os.path.join(E, eid, 'index.html'), 'w').write(doc)
        rows += (f'<li><div><b>{title}</b><span>Progress › {name}</span></div><span class="acts"><a class="sc-btn" href="/embed/{eid}/" target="_blank" rel="noopener">Preview</a>'
                 f'<button type="button" class="sc-btn primary" data-code="{esc(f"<iframe src=\"{SITE}/embed/{eid}/\" title=\"{re.sub("<[^>]+>", "", title)} (Shape Chicago)\" width=\"100%\" height=\"520\" style=\"border:0;max-width:820px\" loading=\"lazy\"></iframe>")}">Copy embed code</button></span></li>')
    return rows

def press(rows):
    hd = NAV_RE.sub(lambda m: nav_for('/press/'), HEADER, count=1)
    doc = f'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>For Reporters · Shape Chicago</title>
<meta name="description" content="Charts on Chicago housing, zoning, transit and streets that you can embed in a story, free with credit, plus how we count.">
<meta property="og:title" content="For reporters · Shape Chicago"><meta property="og:image" content="{SITE}/shape/art/og-progress.jpg"><meta name="twitter:card" content="summary_large_image">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Instrument+Sans:wght@400;500;600;700&display=swap" rel="stylesheet">
<link rel="stylesheet" href="/shape/shape.css"><link rel="stylesheet" href="/progress/progress.css">
<style>
.pg main{{max-width:880px}}
.pr ul{{list-style:none;margin:0;padding:0;display:flex;flex-direction:column}}
.pr li{{display:flex;gap:12px;align-items:center;justify-content:space-between;padding:12px 0;border-top:1px solid var(--sc-line)}}.pr li:first-child{{border-top:0}}
.pr li div{{display:flex;flex-direction:column;gap:2px;min-width:0}}.pr li b{{font-size:15px;font-weight:600}}.pr li div span{{font-size:13px;color:var(--sc-mute)}}
.pr .acts{{display:flex;gap:8px;flex:none}}
@media (max-width:620px){{ .pr li{{flex-direction:column;align-items:flex-start}} }}
.pr code{{font:13px ui-monospace,Menlo,monospace;background:#f3f5f7;border-radius:6px;padding:2px 6px}}
.pr pre{{margin:0;font:12.5px/1.5 ui-monospace,Menlo,monospace;background:#f3f5f7;border-radius:10px;padding:12px;white-space:pre-wrap;word-break:break-all}}
</style>
</head>
<body class="pg">
{hd}
<main class="pr">
<div class="top"><h1>For reporters</h1><p class="lede">Every chart below can go in your story. Each one updates itself when the city or the federal government publishes new numbers, and each lists its sources.</p></div>
<section class="card pad"><div class="hd"><h2>Using our charts and numbers</h2></div>
<p class="sub">Our charts, tables and the figures we calculate are free to use, quote and embed. Please credit <b>Shape Chicago</b> and link to the page the number came from. The underlying data belongs to the agencies that publish it; each chart names them.</p>
<p class="sub">Shape Chicago is a fan-made project. It is not affiliated with the City of Chicago, CTA, Metra or Pace, and it takes no side in elections. Estimates are labeled as estimates, and each section ends with how we count.</p>
<p class="sub">Spotted something wrong? <a href="#feedback" onclick="event.preventDefault(); window.scFeedback && window.scFeedback()">Send a correction</a>. We fix errors and say what changed.</p></section>
<section class="card pad"><div class="hd"><h2>Charts you can embed</h2><p class="cap">Paste the code into your story’s HTML. Every chart page on Progress also has an Embed button.</p></div><ul>{rows}</ul></section>
<section class="card pad"><div class="hd"><h2>Optional: let the chart set its own height</h2><p class="cap">Add this once to the page, after the iframes, if your site allows scripts.</p></div>
<pre>&lt;script&gt;addEventListener("message", e =&gt; {{ if (!e.data || !e.data.scEmbed) return; document.querySelectorAll('iframe[src*="/embed/' + e.data.scEmbed + '/"]').forEach(f =&gt; f.style.height = e.data.h + "px"); }});&lt;/script&gt;</pre></section>
<section class="card pad"><div class="hd"><h2>How the simulators work</h2></div>
<p class="sub">The housing, transit, budget and pensions simulators are estimates, not forecasts. Each lists its sources and every assumption it makes: open <b>Sources</b> in the header of any simulator. Plans that people share are on <a href="/plans/">Plans people made</a>, with a summary of the most common choices on <a href="/community/">What people picked</a>.</p></section>
</main>
<footer class="sc-foot" data-sc-foot>Not affiliated with the City of Chicago.</footer>
<script src="/shape/shape.js"></script>
<script>
document.querySelectorAll("[data-code]").forEach(b => b.addEventListener("click", () => navigator.clipboard.writeText(b.dataset.code.replace("{SITE}", location.origin)).then(() => {{ const o = b.textContent; b.textContent = "Copied"; setTimeout(() => b.textContent = o, 1400); }})));
</script>
</body>
</html>
'''
    os.makedirs(os.path.join(ROOT, 'press'), exist_ok=True); open(os.path.join(ROOT, 'press', 'index.html'), 'w').write(doc)

def main():
    pages = {'decisions': decisions_index(), **{'decisions/' + D['slug']: decision(D) for D in DECISIONS}, '': overview(), 'homes': homes(), 'zoning': zoning(), 'room': MOVED_ROOM, 'lost': MOVED, 'affordable': affordable(), 'rents': rents(), 'transit': transit(), 'streets': streets(), 'projects': projects(), 'capital': capital(), 'springfield': springfield(), 'preview': preview()}
    for slug, html in pages.items():
        d = os.path.join(OUT, slug); os.makedirs(d, exist_ok=True)
        open(os.path.join(d, 'index.html'), 'w').write(html)
    open(os.path.join(OUT, 'progress.css'), 'w').write(CSS)
    press(write_embeds(pages))
    print('progress:', len(pages), 'pages;', f(ytd['homes']), 'homes through', THRU, f'({pct}% of pace)')

if __name__ == '__main__':
    main()
