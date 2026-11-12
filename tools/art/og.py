"""Link-preview images (1200x630) for each Shape Chicago page: the page's render on the right, its name and one line on the left.
python3 tools/art/og.py <renders dir> <Instrument Sans .woff dir> [only these keys, comma-separated] → shape/art/og-*.jpg"""
import sys, os
from PIL import Image, ImageDraw, ImageFont

R, FD = sys.argv[1], sys.argv[2]
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "shape", "art")
font = lambda w, s: ImageFont.truetype(os.path.join(FD, f"instrument-sans-latin-{w}-normal.woff"), s)
INK, INK2, MUTE, FLAG, STAR = (26, 29, 33), (61, 67, 75), (90, 96, 105), (65, 182, 230), (228, 0, 43)
STARP = [(12, 1), (14.4, 7.84), (21.53, 6.5), (16.8, 12), (21.53, 17.5), (14.4, 16.16), (12, 23), (9.6, 16.16), (2.47, 17.5), (7.2, 12), (2.47, 6.5), (9.6, 7.84)]

PAGES = [
    ("home", "hero.png", "Everyone has a plan for Chicago. Test yours.", "Free simulations on the real city: housing, transit and what Chicago actually builds."),
    ("housing", "og_housing.png", "Fix Chicago Housing", "Rezone the real city, vote on real policies, and watch 15 years of building."),
    ("transit", "og_transit.png", "Expand Chicago Transit", "Switch on real proposals or draw your own line, and see riders, cost and cars off the road."),
    ("tracker", "og_tracker.png", "Chicago Permit Tracker", "Every new-home permit since 2006, updated daily from the city's own data."),
    ("progress", "progress.png", "Progress", "What Chicago built, rezoned and ran, counted from public records and updated daily."),
]
ONLY = set(sys.argv[3].split(",")) if len(sys.argv) > 3 else None

def wrap(d, text, f, width):
    lines, cur = [], ""
    for w in text.split():
        t = (cur + " " + w).strip()
        if d.textlength(t, font=f) <= width: cur = t
        else: lines.append(cur); cur = w
    lines.append(cur); return lines

for key, art, title, sub in PAGES:
    if ONLY and key not in ONLY: continue
    W, H = 1200, 630
    im = Image.new("RGB", (W, H), (244, 246, 242))
    g = Image.new("RGB", (1, H));
    for y in range(H):
        t = y / H; g.putpixel((0, y), tuple(int(a + (b - a) * t) for a, b in zip((248, 250, 247), (229, 235, 228))))
    im.paste(g.resize((W, H)))
    d = ImageDraw.Draw(im)
    d.rectangle([0, 0, W, 2], fill=FLAG); d.rectangle([0, 7, W, 8], fill=FLAG)
    # the render, right side
    a = Image.open(os.path.join(R, art)).convert("RGBA")
    if key == "home":
        a = a.resize((int(a.width * 0.66), int(a.height * 0.66)), Image.LANCZOS); im.paste(a, (W - a.width + 30, H - a.height + 26), a)
    else:
        k = {"housing": 0.66, "transit": 0.6, "tracker": 0.6, "progress": 0.56}[key]
        a = a.resize((int(a.width * k), int(a.height * k)), Image.LANCZOS)
        if key == "transit":   # its ground runs off both ends: trim the left and fade that edge into the background
            a = a.crop((int(a.width * 0.22), 0, a.width, a.height))
            ramp = Image.new("L", a.size, 255); px = ramp.load()
            for x in range(min(150, a.width)):
                v = int(255 * x / 150)
                for y in range(a.height): px[x, y] = v
            from PIL import ImageChops
            a.putalpha(ImageChops.multiply(a.getchannel("A"), ramp))
        im.paste(a, (W - a.width + 40, H - a.height - 20), a)
    # brand
    s = 1.6; ox, oy = 64, 50
    d.polygon([(ox + x * s, oy + y * s) for x, y in STARP], fill=STAR)
    d.text((ox + 48, oy + 2), "Shape Chicago", font=font(700, 30), fill=INK)
    # title and line
    tf = font(600, 62 if len(title) < 26 else 56)
    y = 150
    for ln in wrap(d, title, tf, 500 if key != "home" else 640):
        d.text((64, y), ln, font=tf, fill=INK); y += int(tf.size * 1.08)
    y += 18
    sf = font(400, 27)
    for ln in wrap(d, sub, sf, 440):
        d.text((64, y), ln, font=sf, fill=INK2); y += 38
    d.text((64, H - 56), "Not affiliated with the City of Chicago.", font=font(400, 20), fill=MUTE)
    out = os.path.join(OUT, f"og-{key}.jpg"); im.save(out, quality=88); print(out)
