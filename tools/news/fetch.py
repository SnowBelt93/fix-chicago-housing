"""Chicago planning and policy news feed for Shape Chicago (runs in GitHub Actions every few hours; the cloud workspace
can't reach these sites). Reads each outlet's public RSS feed, keeps only stories about Chicago planning, housing,
development, transit, the budget and city policy, and writes news/data/news.json: headline, link, outlet, date and topic
tags. No article text is stored or shown; every item links to the outlet."""
import urllib.request, urllib.parse, json, os, re, time, html, email.utils, datetime as dt
import xml.etree.ElementTree as ET
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(ROOT, 'news', 'data', 'news.json'); os.makedirs(os.path.dirname(OUT), exist_ok=True)
# outlet, Chicago-only outlet?, candidate feed URLs (first one that parses wins)
SOURCES = [
 ('Block Club Chicago', True, ['https://blockclubchicago.org/feed/']),
 ('Chicago Sun-Times', False, ['https://chicago.suntimes.com/rss/index.xml', 'https://chicago.suntimes.com/feed/', 'https://chicago.suntimes.com/arc/outboundfeeds/rss/?outputType=xml']),
 ('Chicago Tribune', False, ['https://www.chicagotribune.com/feed/', 'https://www.chicagotribune.com/news/feed/', 'https://www.chicagotribune.com/news/chicago/feed/', 'https://www.chicagotribune.com/business/real-estate/feed/', 'https://www.chicagotribune.com/arc/outboundfeeds/rss/?outputType=xml']),
 ('WBEZ', False, ['https://www.wbez.org/feed/', 'https://www.wbez.org/rss/index.xml', 'https://www.wbez.org/index.rss']),
 ('WTTW News', False, ['https://news.wttw.com/rss.xml', 'https://news.wttw.com/feed']),
 ("Crain's Chicago Business", False, ['https://www.chicagobusiness.com/rss', 'https://www.chicagobusiness.com/section/rss', 'https://www.chicagobusiness.com/feed']),
 ('Chicago Reader', False, ['https://chicagoreader.com/feed/']),
 ('Urbanize Chicago', True, ['https://chi.urbanize.city/rss.xml', 'https://chi.urbanize.city/feed', 'https://chi.urbanize.city/rss', 'https://urbanize.city/chi/rss.xml']),
 ('Chicago YIMBY', True, ['https://chicagoyimby.com/feed', 'https://chicagoyimby.com/feed/']),
 ('Streetsblog Chicago', True, ['https://chi.streetsblog.org/feed', 'https://chi.streetsblog.org/feed/']),
 ('The Real Deal', True, ['https://therealdeal.com/chicago/feed/', 'https://therealdeal.com/chicago/feed', 'https://therealdeal.com/feed/?region=chicago']),
 ('South Side Weekly', True, ['https://southsideweekly.com/feed/']),
 ('Capitol News Illinois', False, ['https://capitolnewsillinois.com/feed/']),
 ('Illinois Answers Project', False, ['https://illinoisanswers.org/feed/']),
 ('The Daily Line', True, ['https://www.thedailyline.com/feed', 'https://www.thedailyline.com/feed/']),
 ('Axios Chicago', False, ['https://api.axios.com/feed/local/chicago', 'https://www.axios.com/local/chicago/feed']),
 ('Chicago Magazine', False, ['https://www.chicagomag.com/feed/']),
 ('CBS Chicago', True, ['https://www.cbsnews.com/chicago/latest/rss/main', 'https://www.cbsnews.com/chicago/latest/rss/local-news']),
 ('NBC Chicago', True, ['https://www.nbcchicago.com/?rss=y', 'https://www.nbcchicago.com/news/local/?rss=y']),
 ('ABC7 Chicago', True, ['https://abc7chicago.com/feed/']),
 ('WGN News', True, ['https://wgntv.com/feed/', 'https://wgntv.com/news/feed/']),
 ('FOX 32 Chicago', True, ['https://www.fox32chicago.com/rss/category/news', 'https://www.fox32chicago.com/rss/category/local-news']),
 ('Chicago Business Journal', True, ['https://feeds.bizjournals.com/bizj_chicago']),
 ('Chicago Defender', True, ['https://chicagodefender.com/feed/']),
 ('Hyde Park Herald', True, ['https://www.hpherald.com/search/?f=rss&t=article&l=50&s=start_time&sd=desc']),
 ('The TRiiBE', True, ['https://thetriibe.com/feed/']),
 ('Chicago Cityscape', True, ['https://www.chicagocityscape.com/blog/feed', 'https://chicagocityscape.com/blog/?feed=rss2']),
 ('Bisnow Chicago', True, ['https://www.bisnow.com/rss/chicago']),
 ('Chicago Agent', True, ['https://chicagoagentmagazine.com/feed/']),
 ('Austin Weekly News', True, ['https://www.austinweeklynews.com/feed/']),
 ('Metropolitan Planning Council', True, ['https://metroplanning.org/feed/']),
 ('Better Government Association', False, ['https://www.bettergov.org/feed/']),
 ('Chicago Tribune', False, ['https://www.chicagotribune.com/arcio/rss/category/news/', 'https://www.chicagotribune.com/news/chicago/feed/']),
]
TOPICS = {
 'housing': r'\b(housing|new homes|apartments?\b|condos?\b|rents?\b|rental|renters|landlords?|tenants?|affordable|homeless|evictions?|ADUs?\b|coach houses?|two-flats?|three-flats?|CHA\b|single.stair|residential)',
 'development': r'\b(develop(er|ment)|construction|tower|high-rise|skyscraper|redevelop|megaproject|groundbreak|demolition|demolish|vacant lot|stadium|mixed-use|planned development|Plan Commission|landmark)',
 'zoning': r'\b(zoning|rezon|upzon|downzon|setback|parking minimum|by.right|aldermanic prerogative|Zoning Committee)',
 'transit': r'\b(CTA|Metra|\bPace\b|NITA|transit|bus(es)?\b|Red Line|Blue Line|Brown Line|Green Line|Orange Line|L train|bike lane|Divvy|streetscape|traffic|congestion)',
 'budget': r'\b(budget|property tax|pension|TIF|bond rating|revenue|deficit|head tax|tax levy|city finances|Corporate Fund|credit rating)',
 'policy': r'\b(City Council|alderperson|alderman|alder|ordinance|mayor Johnson|Johnson administration|ward\b|Planning and Development|DPD|Department of Housing|zoning board)',
}
STATEWIDE = {'Capitol News Illinois', 'Illinois Answers Project'}
NOT = r'\b(shooting|shot|gunman|homicide|murder|carjack|stabb|arrest|police chase|charged|Bears|Bulls|Cubs|White Sox|Blackhawks|Sky\b|Fire FC|concert|festival|film|movie|musician|actor|album|venue|restaurant|recipe|obituar|porn|sex|hentai|casino bonus|bingo|horoscope|crossword)'
CHI = r'\b(Chicago|Chicagoans?|Loop|South Side|West Side|North Side|Cook County|CTA|Metra|Johnson administration|City Council)\b'
# extra feeds read on top of each outlet's main feed: WordPress search feeds (?s=term&feed=rss2) reach further back on
# the topics we keep, since a main feed only holds the latest 10 to 20 stories
WP_TERMS = ['zoning', 'housing', 'development', 'apartments', 'CTA', 'budget', 'City Council', 'affordable']
EXTRA = [(name, base + '/?s=' + urllib.parse.quote_plus(t) + '&feed=rss2') for name, base in
         [('Block Club Chicago', 'https://blockclubchicago.org'), ('South Side Weekly', 'https://southsideweekly.com'), ('Chicago Defender', 'https://chicagodefender.com'), ('The TRiiBE', 'https://thetriibe.com'),
          ('Streetsblog Chicago', 'https://chi.streetsblog.org'), ('Chicago YIMBY', 'https://chicagoyimby.com')] for t in WP_TERMS]
def get(u):
    try: return urllib.request.urlopen(urllib.request.Request(u, headers={'User-Agent': 'Mozilla/5.0 (compatible; ShapeChicagoNews/1.0)'}), timeout=60).read()
    except Exception as e: print('  fail', u, str(e)[:80], flush=True); return None
def text(el, *names):
    for n in names:
        x = el.find(n)
        if x is not None and (x.text or x.get('href')): return (x.text or x.get('href') or '').strip()
    return ''
MRSS = '{http://search.yahoo.com/mrss/}'
def feed_img(it):
    """The picture the outlet attached to the story in its feed (media:content, media:thumbnail, an image enclosure,
    or the first <img> in the story body), if any."""
    for tag in (MRSS + 'content', MRSS + 'thumbnail'):
        for m in it.iter(tag):
            u = m.get('url') or ''
            if u and (m.get('medium') in (None, 'image') or re.search(r'\.(jpe?g|png|webp)', u, re.I)): return u
    for e in it.findall('enclosure'):
        if (e.get('type') or '').startswith('image') and e.get('url'): return e.get('url')
    body = text(it, '{http://purl.org/rss/1.0/modules/content/}encoded', 'description')
    m = re.search(r'<img[^>]+src=["\']([^"\']+)', body or '')
    return html.unescape(m.group(1)) if m else ''
def parse(b):
    root = ET.fromstring(b); ns = {'a': 'http://www.w3.org/2005/Atom'}; out = []
    for it in root.iter('item'):
        out.append((text(it, 'title'), text(it, 'link'), text(it, 'pubDate', '{http://purl.org/dc/elements/1.1/}date'), text(it, 'description'), [c.text or '' for c in it.findall('category')], feed_img(it)))
    for it in root.iter('{http://www.w3.org/2005/Atom}entry'):
        link = it.find('a:link', ns); out.append((text(it, '{http://www.w3.org/2005/Atom}title'), link.get('href') if link is not None else '', text(it, '{http://www.w3.org/2005/Atom}updated', '{http://www.w3.org/2005/Atom}published'), text(it, '{http://www.w3.org/2005/Atom}summary'), [], feed_img(it)))
    return out
def dek(desc):
    """The outlet's own short description of the story (its feed summary), cut to two or three sentences."""
    t = html.unescape(re.sub(r'<[^>]+>', ' ', desc or ''))
    t = re.sub(r'The post .*? appeared first on .*$', '', t, flags=re.S)
    t = re.sub(r'\s*(Continue reading|Read more|\[…\]|\[\.\.\.\]).*$', '', t, flags=re.S | re.I)
    t = re.sub(r'\s+', ' ', t).strip()
    if len(t) < 40: return ''
    parts = re.split(r'(?<=[.!?])\s+(?=[A-Z"“])', t); out = ''
    for p_ in parts[:3]:
        if len(out) + len(p_) > 330 and out: break
        out = (out + ' ' + p_).strip()
    if len(out) > 340: out = out[:330].rsplit(' ', 1)[0] + '…'
    return out
def when(s):
    try: return email.utils.parsedate_to_datetime(s).astimezone(dt.timezone.utc)
    except Exception:
        try: return dt.datetime.fromisoformat(s.replace('Z', '+00:00')).astimezone(dt.timezone.utc)
        except Exception: return None
old = []
if os.path.exists(OUT):
    try: old = json.load(open(OUT)).get('items', [])
    except Exception: old = []
old = [o for o in old if not re.search(NOT, o['t'], re.I) and not (o['s'] in STATEWIDE and not re.search(CHI, o['t'])) and [k for k, rx in TOPICS.items() if re.search(rx, o['t'], re.I if k != 'transit' else 0)]]   # re-check kept items against the current rules
seen = {o['u'] for o in old}; items = list(old); status = {}
now = dt.datetime.now(dt.timezone.utc)
LOCAL = {n: l for n, l, _ in SOURCES}
jobs = [(name, urls) for name, local, urls in SOURCES] + [(name, [u]) for name, u in EXTRA]
for name, urls in jobs:
    local = LOCAL[name]
    got = None
    for u in urls:
        b = get(u)
        if not b: continue
        try: got = parse(b); break
        except Exception as e: print('  parse fail', u, str(e)[:60], flush=True)
    if got is not None: status[name] = max(status.get(name, 0), 0) + len(got)
    else: status.setdefault(name, -1)
    for title, link, date, desc, cats, img in got or []:
        title = html.unescape(re.sub(r'<[^>]+>', '', title)).strip(); d = when(date)
        if not title or not link or link in seen or not d or (now - d).days > 45: continue
        blob = title + ' ' + html.unescape(re.sub(r'<[^>]+>', ' ', desc or ''))[:600] + ' ' + ' '.join(cats)
        if re.search(NOT, title, re.I): continue
        tags = [k for k, rx in TOPICS.items() if re.search(rx, title, re.I if k != 'transit' else 0)]   # topics from the headline only
        if not tags: continue
        if name in STATEWIDE and not re.search(CHI, title): continue          # statewide outlets: Chicago must be in the headline
        if not local and not re.search(CHI, blob): continue
        seen.add(link); items.append({'t': title, 'u': link, 's': name, 'd': d.strftime('%Y-%m-%dT%H:%MZ'), 'g': tags, **({'i': img} if img.startswith('http') else {}), **({'x': dek(desc)} if dek(desc) else {})})
items = [i for i in items if (now - dt.datetime.fromisoformat(i['d'].replace('Z', '+00:00'))).days <= 45]
items.sort(key=lambda i: i['d'], reverse=True); items = items[:600]
# stories with no picture in the feed: read the share image the outlet sets for link previews (og:image), once per story;
# 'i': '' means we looked and found none. Only the image's address is kept; readers' browsers load it from the outlet.
tries = 0
for it in items:
    if ('i' in it and ('x' in it or it.get('xd'))) or tries >= 120: continue
    tries += 1; b = get(it['u']); it.setdefault('i', ''); it['xd'] = 1
    if not b: continue
    h = b[:200000].decode('utf-8', 'ignore')
    m = (re.search(r'<meta[^>]+property=["\']og:image(?::secure_url)?["\'][^>]+content=["\']([^"\']+)', h, re.I) or re.search(r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:image["\']', h, re.I)
         or re.search(r'<meta[^>]+name=["\']twitter:image["\'][^>]+content=["\']([^"\']+)', h, re.I))
    if m and m.group(1).startswith('http') and not it['i']: it['i'] = html.unescape(m.group(1))
    if 'x' not in it:
        m2 = re.search(r'<meta[^>]+(?:property|name)=["\'](?:og:description|description)["\'][^>]+content=["\']([^"\']+)', h, re.I) or re.search(r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+(?:property|name)=["\'](?:og:description|description)["\']', h, re.I)
        if m2 and dek(m2.group(1)): it['x'] = dek(m2.group(1))
print('images', sum(1 for i in items if i.get('i')), 'of', len(items), '; looked up', tries)
json.dump({'updated': now.strftime('%Y-%m-%dT%H:%MZ'), 'sources': status, 'items': items}, open(OUT, 'w'), separators=(',', ':'))
print('sources', status); print('items', len(items))
# an Atom feed of the same list, for feed readers (and RSS-to-email services later)
from xml.sax.saxutils import escape as xe
feed = ['<?xml version="1.0" encoding="utf-8"?>', '<feed xmlns="http://www.w3.org/2005/Atom">',
        '<title>Shape Chicago: Chicago planning news</title>', '<id>tag:shapechicago,2026:news</id>',
        '<updated>' + now.strftime('%Y-%m-%dT%H:%M:%SZ') + '</updated>', '<author><name>Shape Chicago</name></author>']
for i in items[:60]:
    feed.append('<entry><title>%s</title><link href="%s"/><id>%s</id><updated>%s:00Z</updated><summary>%s</summary></entry>' % (
        xe(i['t']), xe(i['u'], {'"': '&quot;'}), xe(i['u']), i['d'][:-1], xe(i['s'] + ' · ' + ', '.join(i['g']))))
feed.append('</feed>')
open(os.path.join(os.path.dirname(OUT), '..', 'feed.xml'), 'w').write('\n'.join(feed))
