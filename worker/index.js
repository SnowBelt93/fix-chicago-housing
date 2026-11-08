// Shape Chicago API: anonymous plan gallery, "what other people chose", neighborhood stats, and private feedback.
// Static files are served by Workers Assets; only /api/* reaches this script.
// Nothing people type is ever shown on the site: plan titles are generated from the plan, and feedback is
// stored privately (read with GET /api/feedback?key=<FEEDBACK_KEY>, a secret set in the Worker's settings).

const BIT_KEYS = ["build","stair","adu","lots","pre","permits","mpls","camb","small","park","vac","social","comm","mega","down","pmin","mora","rentc","xfer","vland"];
const B32 = "0123456789abcdefghijklmnopqrstuv";
const CODE_RE = /^(?:(?:u4[0-9a-o]{39}[0-4][0-4][0-4][0-3][0-2][0-2][0-9a-v]{3}|u5[0-9a-o]{39}[0-5][0-4][0-4][0-3][0-2][0-2][0-9a-v]{4})[0-2][0-4]|u6[0-6]{77}[0-6][0-4][0-4][0-3][0-2][0-3][0-9a-v]{4}[0-4][0-4][0-3]{10})$/;
const COLS = "id, code, homes, grade, hood, likes, ts, rent, rentno, aff, nm";
const GRADES = new Set(["A+","A","B","C","D","F","–"]);

import { Resvg, initWasm } from "@resvg/resvg-wasm";
import RESVG_WASM from "@resvg/resvg-wasm/index_bg.wasm";
import { cardSvg } from "./card.js";
import FONT_400 from "./fonts-400.bin";
import FONT_600 from "./fonts-600.bin";
import FONT_700 from "./fonts-700.bin";

const json = (data, status = 200, extra = {}) => new Response(JSON.stringify(data), {status, headers: {"content-type": "application/json", "cache-control": "no-store", ...extra}});

export default {
  async fetch(req, env, ctx) {
    const url = new URL(req.url);
    // shared plan links: /p/<id> is a tiny page whose link preview shows that plan, then it opens the plan
    const pm = url.pathname.match(/^\/p\/([0-9a-f]{12})$/);
    if (pm) return planPage(pm[1], url, env);
    const im = url.pathname.match(/^\/api\/card\/([0-9a-f]{12})\.png$/);
    if (im) return cardImage(im[1], url, env, ctx);
    if (url.pathname === "/api/calendar.ics") return calendar(url, env);
    const wf = url.pathname.match(/^\/api\/ward\/(\d{1,2})\.xml$/);
    if (wf && +wf[1] >= 1 && +wf[1] <= 50) return wardFeed(+wf[1], url, env);
    if (!url.pathname.startsWith("/api/")) return env.ASSETS.fetch(req);
    if (url.pathname === "/api/feedback" && req.method === "GET" && (!env.FEEDBACK_KEY || url.searchParams.get("key") !== env.FEEDBACK_KEY)) return json({error: "not allowed"}, 403);
    const stub = env.COMMUNITY.get(env.COMMUNITY.idFromName("v1"));
    const ip = req.headers.get("cf-connecting-ip") || "0";
    const fwd = new Request(req.url, {method: req.method, headers: {"content-type": "application/json", "x-ip": ip}, body: req.method === "POST" ? await req.text() : undefined});
    return stub.fetch(fwd);
  },
};

// City Hall meetings as a calendar people can subscribe to (Google, Apple, Outlook): from the daily wards/data/meetings.json
async function calendar(url, env){
  let M = [];
  try { M = (await (await env.ASSETS.fetch(new Request(url.origin + "/wards/data/meetings.json"))).json()).meetings || []; } catch (e) {}
  const esc = t => String(t || "").replace(/\\/g, "\\\\").replace(/;/g, "\\;").replace(/,/g, "\\,").replace(/\r?\n/g, "\\n");
  const stamp = d => d.toISOString().replace(/[-:]/g, "").replace(/\.\d{3}/, "");
  const fold = l => { let o = ""; while (l.length > 74){ o += l.slice(0, 74) + "\r\n "; l = l.slice(74); } return o + l; };
  const L = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//Shape Chicago//City Hall meetings//EN", "CALSCALE:GREGORIAN", "METHOD:PUBLISH",
    "X-WR-CALNAME:Chicago City Hall meetings", "X-WR-CALDESC:City Council and committee meetings from the City Clerk. Shared by Shape Chicago (not affiliated with the City of Chicago).",
    "REFRESH-INTERVAL;VALUE=DURATION:PT12H", "X-PUBLISHED-TTL:PT12H"];
  const now = Date.now(), made = stamp(new Date());
  for (const m of M){
    const t = Date.parse(m.d); if (!t || t < now - 30 * 864e5) continue;
    const desc = [m.c ? "Public comment sign-up deadline: " + m.c : "", m.ag ? "Agenda: " + m.ag : "", "Details: https://chicityclerkelms.chicago.gov/Meeting/?meetingId=" + m.id].filter(Boolean).join("\n");
    L.push("BEGIN:VEVENT", "UID:" + m.id + "@shapechicago", "DTSTAMP:" + made, "DTSTART:" + stamp(new Date(t)), "DTEND:" + stamp(new Date(t + 2 * 3600e3)),   // the Clerk lists start times only; 2 hours is a placeholder
      fold("SUMMARY:" + esc(m.b)), fold("LOCATION:" + esc(m.loc || "City Hall, 121 N. LaSalle St.")), fold("DESCRIPTION:" + esc(desc)),
      "URL:https://chicityclerkelms.chicago.gov/Meeting/?meetingId=" + m.id, "STATUS:" + (/cancel/i.test(m.st || "") ? "CANCELLED" : "CONFIRMED"), "END:VEVENT");
  }
  L.push("END:VCALENDAR");
  return new Response(L.join("\r\n") + "\r\n", {headers: {"content-type": "text/calendar; charset=utf-8", "cache-control": "public, max-age=3600", "content-disposition": "inline; filename=chicago-city-hall.ics"}});
}

// one ward's news and zoning changes as an Atom feed, for feed readers and RSS-to-email services
async function wardFeed(n, url, env){
  const get = async p => { try { return await (await env.ASSETS.fetch(new Request(url.origin + p))).json(); } catch (e) { return null; } };
  const [N, D] = await Promise.all([get("/news/data/news.json"), get("/wards/data/wards.json")]);
  const x = t => String(t == null ? "" : t).replace(/[&<>"]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
  const iso = d => { const t = Date.parse(String(d).length > 10 ? String(d).replace("Z", ":00Z") : d + "T12:00:00Z"); return new Date(t || Date.now()).toISOString(); };
  const E = [];
  for (const i of (N && N.items) || []) if ((i.w || []).includes(n))
    E.push({id: i.u, t: i.t, u: i.u, d: iso(i.d), s: (i.x ? i.x + " " : "") + "(" + i.s + ")"});
  const W = D && D.wards.find(w => w.w === n);
  const cut = new Date(Date.now() - 180 * 864e5).toISOString().slice(0, 10);
  for (const z of (W && W.z) || []) if (z.d >= cut){
    const what = z.k === "pd" ? "Planned development" : z.hf != null && z.ht != null ? (z.ht > z.hf ? "More homes allowed" : z.ht < z.hf ? "Fewer homes allowed" : "Same number of homes") : "Zoning change";
    E.push({id: "zoning:" + z.r, t: "Zoning change passed: " + z.a, u: url.origin + "/wards/#" + n, d: iso(z.d),
      s: what + (z.f && z.t ? ": " + z.f + " to " + z.t : "") + (z.hf != null && z.ht != null ? " (homes on a typical lot " + z.hf + " to " + z.ht + ")" : "") + ". Passed by City Council."});
  }
  E.sort((a, b) => b.d.localeCompare(a.d));
  const upd = (E[0] && E[0].d) || new Date().toISOString();
  const xml = '<?xml version="1.0" encoding="utf-8"?>\n<feed xmlns="http://www.w3.org/2005/Atom"><title>Ward ' + n + ' · Shape Chicago</title><subtitle>News and zoning changes in Chicago\'s Ward ' + n + '. Not affiliated with the City of Chicago.</subtitle>'
    + '<link rel="alternate" href="' + url.origin + '/wards/#' + n + '"/><link rel="self" href="' + url.href + '"/><id>' + url.origin + '/api/ward/' + n + '.xml</id><updated>' + upd + '</updated>'
    + E.slice(0, 60).map(e => '<entry><title>' + x(e.t) + '</title><link href="' + x(e.u) + '"/><id>' + x(e.id) + '</id><updated>' + e.d + '</updated><summary>' + x(e.s) + '</summary></entry>').join("") + '</feed>';
  return new Response(xml, {headers: {"content-type": "application/atom+xml; charset=utf-8", "cache-control": "public, max-age=1800"}});
}

function features(code){
  if (code[1] === "6"){   // u6: one character per area (towers allowed downtown), then the same fields, then policy scopes
    const f = {tod: +code[79], metra: +code[80], corr: +code[81], office: +code[82], str: +code[83], aro: +code[84], sub: +code[90], areas: 0};
    for (let i = 2; i < 79; i++) if (code[i] !== "0") f.areas++;
    const bits = B32.indexOf(code[85]) | (B32.indexOf(code[86]) << 5) | (B32.indexOf(code[87]) << 10) | (B32.indexOf(code[88]) << 15);
    BIT_KEYS.forEach((k, i) => { f[k] = bits & (1 << i) ? 1 : 0; });
    return f;
  }
  const v5 = code[1] === "5";   // u5 has a 4th on/off character
  const f = {tod: +code[41], metra: +code[42], corr: +code[43], office: +code[44], str: +code[45], aro: +code[46], sub: +code[v5 ? 52 : 51], areas: 0};
  for (let i = 2; i < 41; i++){ const v = parseInt(code[i], 25); if (Math.floor(v / 5)) f.areas++; if (v % 5) f.areas++; }
  const bits = B32.indexOf(code[47]) | (B32.indexOf(code[48]) << 5) | (B32.indexOf(code[49]) << 10) | (v5 ? B32.indexOf(code[50]) << 15 : 0);
  BIT_KEYS.forEach((k, i) => { f[k] = bits & (1 << i) ? 1 : 0; });
  return f;
}

async function hash(s){
  const d = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(s));
  return [...new Uint8Array(d)].slice(0, 12).map(b => b.toString(16).padStart(2, "0")).join("");
}

// ---------------- shared plan previews ----------------
const card = async (id, env) => {
  const r = await env.COMMUNITY.get(env.COMMUNITY.idFromName("v1")).fetch(new Request("https://do/api/card/" + id));
  return r.ok ? r.json() : null;
};
const esc = s => String(s).replace(/[&<>"]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
const fmt = n => Math.round(n).toLocaleString("en-US");
function cardText(c){
  const title = c.homes >= 1 ? "A plan for " + fmt(c.homes) + " new homes in Chicago by 2041" : "A plan for Chicago's housing";
  const goalWord = c.mode === 1 ? "hard mode goal" : c.mode === 2 ? "every-ward goal" : "goal";
  const desc = "Grade " + c.grade + " against a " + goalWord + " of " + fmt(c.goal) + " homes. Open it in Fix Chicago Housing, change it, and try to beat it.";
  return {title, desc};
}
async function planPage(id, url, env){
  const c = await card(id, env);
  const to = c ? "/housing/#" + c.code : "/housing/";
  if (!c) return Response.redirect(url.origin + to, 302);
  const {title, desc} = cardText(c), img = url.origin + "/api/card/" + id + ".png";
  const html = `<!doctype html><html lang="en"><head><meta charset="utf-8"><title>${esc(title)}</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="description" content="${esc(desc)}">
<meta property="og:title" content="${esc(title)}"><meta property="og:description" content="${esc(desc)}">
<meta property="og:type" content="website"><meta property="og:url" content="${esc(url.href)}">
<meta property="og:image" content="${img}"><meta property="og:image:width" content="1200"><meta property="og:image:height" content="630">
<meta name="twitter:card" content="summary_large_image"><meta name="robots" content="noindex">
<meta http-equiv="refresh" content="0;url=${esc(to)}"></head>
<body><script>location.replace(${JSON.stringify(to)})</script><a href="${esc(to)}">Open the plan</a></body></html>`;
  return new Response(html, {headers: {"content-type": "text/html; charset=utf-8", "cache-control": "public, max-age=300"}});
}
let wasmReady = null;
// Instrument Sans (SIL Open Font License), converted to TrueType for resvg, bundled with the Worker
const FONTS = [new Uint8Array(FONT_400), new Uint8Array(FONT_600), new Uint8Array(FONT_700)];
async function cardImage(id, url, env, ctx){
  const cache = caches.default, key = new Request(url.origin + "/api/card/" + id + ".png?r=2");
  const hit = await cache.match(key); if (hit) return hit;
  const c = await card(id, env);
  if (!c) return env.ASSETS.fetch(new Request(url.origin + "/shape/art/og-housing.jpg"));
  try {
    if (!wasmReady) wasmReady = initWasm(RESVG_WASM);
    await wasmReady;
    const art = await env.ASSETS.fetch(new Request(url.origin + "/shape/art/card-art.png"));
    let b64 = "";
    if (art.ok){ const u = new Uint8Array(await art.arrayBuffer()); let bin = ""; for (let i = 0; i < u.length; i += 0x8000) bin += String.fromCharCode.apply(null, u.subarray(i, i + 0x8000)); b64 = btoa(bin); }
    const svg = cardSvg(c, b64);
    const png = new Resvg(svg, {fitTo: {mode: "width", value: 1200}, font: {fontBuffers: FONTS, defaultFontFamily: "Instrument Sans", loadSystemFonts: false}}).render().asPng();
    const res = new Response(png, {headers: {"content-type": "image/png", "cache-control": "public, max-age=86400"}});
    ctx.waitUntil(cache.put(key, res.clone()));
    return res;
  } catch (e) {
    return env.ASSETS.fetch(new Request(url.origin + "/shape/art/og-housing.jpg"));
  }
}

export class Community {
  constructor(state, env){
    this.sql = state.storage.sql;
    this.sql.exec(`CREATE TABLE IF NOT EXISTS plans (id INTEGER PRIMARY KEY AUTOINCREMENT, code TEXT NOT NULL, homes INTEGER NOT NULL, grade TEXT NOT NULL,
      hood INTEGER NOT NULL DEFAULT 0, gallery INTEGER NOT NULL DEFAULT 0, likes INTEGER NOT NULL DEFAULT 0, who TEXT NOT NULL, ts INTEGER NOT NULL)`);
    this.sql.exec(`CREATE TABLE IF NOT EXISTS likes (plan INTEGER NOT NULL, who TEXT NOT NULL, PRIMARY KEY (plan, who))`);
    this.sql.exec(`CREATE INDEX IF NOT EXISTS plans_ts ON plans(ts)`);
    this.sql.exec(`CREATE TABLE IF NOT EXISTS feedback (id INTEGER PRIMARY KEY AUTOINCREMENT, text TEXT NOT NULL, page TEXT NOT NULL, who TEXT NOT NULL, ts INTEGER NOT NULL)`);
    this.sql.exec(`CREATE TABLE IF NOT EXISTS cards (id TEXT PRIMARY KEY, code TEXT NOT NULL, homes INTEGER NOT NULL, grade TEXT NOT NULL, goal INTEGER NOT NULL,
      rent INTEGER NOT NULL, rentno INTEGER NOT NULL, mode INTEGER NOT NULL, who TEXT NOT NULL, ts INTEGER NOT NULL)`);
    for (const c of ["rent INTEGER", "rentno INTEGER", "aff INTEGER", "nm INTEGER"]) try { this.sql.exec("ALTER TABLE plans ADD COLUMN " + c); } catch (e) {}   // added Nov 8; old rows stay null
    this.sql.exec(`CREATE TABLE IF NOT EXISTS meta (k TEXT PRIMARY KEY, v TEXT NOT NULL)`);
    this.sql.exec(`CREATE TABLE IF NOT EXISTS imports (old INTEGER PRIMARY KEY, id INTEGER NOT NULL, likes INTEGER NOT NULL)`);
    // "Where Should the Bears Play?": one pick per person a day; pins rounded to ~100 m; nothing typed is stored
    this.sql.exec(`CREATE TABLE IF NOT EXISTS bears (id INTEGER PRIMARY KEY, site TEXT NOT NULL, lon REAL NOT NULL, lat REAL NOT NULL, who TEXT NOT NULL, day TEXT NOT NULL, ts INTEGER NOT NULL)`);
    try { this.sql.exec("ALTER TABLE bears ADD COLUMN plan TEXT"); } catch (e) {}   // Nov 8: a pick can carry its site plan (pieces and positions only)
    this.env = env;
    this.cache = null;
  }

  // Plans posted on fixchicagohousing.com (the fix-chicago-housing Worker) are copied in, at most every 6 hours, until launch.
  // Imported plans keep their old endorsements; endorsements made here are added on top.
  async sync(){
    const last = +((this.sql.exec("SELECT v FROM meta WHERE k = 'sync'").toArray()[0] || {}).v || 0);
    if (Date.now() - last < 6 * 3600e3) return;
    this.sql.exec("INSERT OR REPLACE INTO meta (k, v) VALUES ('sync', ?)", String(Date.now()));
    const get = async q => {
      const u = "https://fixchicagohousing.com/api/gallery?" + q;
      try { const r = this.env.OLD ? await this.env.OLD.fetch(new Request(u)) : await fetch(u); return r.ok ? ((await r.json()).plans || []) : []; } catch (e) { return []; }
    };
    const seen = new Map();
    for (const q of ["sort=top", "sort=new"]) for (const P of await get(q)) seen.set(P.id, P);
    for (const P of seen.values()){
      const code = String(P.code || ""), grade = String(P.grade || ""), homes = Math.round(+P.homes), hood = Math.round(+P.hood || 0), likes = Math.max(0, Math.round(+P.likes || 0));
      if (!CODE_RE.test(code) || !GRADES.has(grade) || !(homes >= 0 && homes <= 3000000) || !(hood >= 0 && hood <= 77)) continue;
      const had = this.sql.exec("SELECT id FROM imports WHERE old = ?", P.id).toArray()[0];
      if (had){
        const local = this.sql.exec("SELECT COUNT(*) AS n FROM likes WHERE plan = ?", had.id).one().n;
        this.sql.exec("UPDATE plans SET likes = ? WHERE id = ?", likes + local, had.id); this.sql.exec("UPDATE imports SET likes = ? WHERE old = ?", likes, P.id);
      } else {
        const id = this.sql.exec("INSERT INTO plans (code, homes, grade, hood, gallery, likes, who, ts) VALUES (?, ?, ?, ?, 1, ?, 'import', ?) RETURNING id", code, homes, grade, hood, likes, Math.round(+P.ts) || Date.now()).one().id;
        this.sql.exec("INSERT INTO imports (old, id, likes) VALUES (?, ?, ?)", P.id, id, likes);
      }
    }
    this.cache = null;
  }

  async fetch(req){
    const url = new URL(req.url), path = url.pathname;
    const day = new Date().toISOString().slice(0, 10);
    const who = await hash((req.headers.get("x-ip") || "0") + "|" + day + "|fch");
    try {
      if (path === "/api/plan" && req.method === "POST") return this.addPlan(await req.json(), who);
      if (path === "/api/feedback" && req.method === "POST") return this.addFeedback(await req.json(), who);
      if (path === "/api/feedback" && req.method === "GET") return json({feedback: this.sql.exec("SELECT id, text, page, ts FROM feedback ORDER BY ts DESC LIMIT 500").toArray()});
      if (path === "/api/stats" && req.method === "GET") return this.stats(+url.searchParams.get("hood") || 0);
      if (path === "/api/gallery" && req.method === "GET"){ await this.sync(); return this.gallery(url.searchParams.get("sort") === "top" ? "top" : "new", +url.searchParams.get("hood") || 0, +url.searchParams.get("limit") || 30); }
      if (path === "/api/plans" && req.method === "GET"){   // a few plans by id (your own posted plans, for their endorsement counts)
        const ids = String(url.searchParams.get("ids") || "").split(",").map(Number).filter(n => n > 0).slice(0, 40);
        return json({plans: ids.length ? this.sql.exec(`SELECT ${COLS} FROM plans WHERE gallery = 1 AND id IN (${ids.join(",")})`).toArray() : []});
      }
      const pm = path.match(/^\/api\/plan\/(\d+)$/);
      if (pm && req.method === "GET"){ const r = this.sql.exec(`SELECT ${COLS} FROM plans WHERE gallery = 1 AND id = ?`, +pm[1]).toArray()[0]; return r ? json(r) : json({error: "not found"}, 404); }
      if (path === "/api/card" && req.method === "POST") return this.addCard(await req.json(), who);
      const cm = path.match(/^\/api\/card\/([0-9a-f]{12})$/);
      if (cm && req.method === "GET"){ const r = this.sql.exec("SELECT code, homes, grade, goal, rent, rentno, mode FROM cards WHERE id = ?", cm[1]).toArray()[0]; return r ? json(r) : json({error: "not found"}, 404); }
      if (path === "/api/bears/pick" && req.method === "POST") return this.bearsPick(await req.json(), who, day);
      if (path === "/api/bears/picks" && req.method === "GET") return this.bearsPicks();
      const m = path.match(/^\/api\/like\/(\d+)$/);
      if (m && req.method === "POST") return this.like(+m[1], who);
    } catch (e) { return json({error: "bad request"}, 400); }
    return json({error: "not found"}, 404);
  }

  bearsPick(b, who, day){
    const site = String(b.site || ""), lon = Math.round(+b.lon * 1000) / 1000, lat = Math.round(+b.lat * 1000) / 1000;
    if (!/^(hammond|arlington|southworks|lakefront|soldier|reese|pin)$/.test(site) || !(lon > -88.6 && lon < -86.8 && lat > 41.3 && lat < 42.4)) return json({error: "invalid"}, 400);
    if (this.sql.exec("SELECT 1 FROM bears WHERE who = ? AND day = ?", who, day).toArray().length) return json({error: "one a day"}, 429);
    let plan = b.plan == null ? null : String(b.plan);
    if (plan != null && (plan.length > 1500 || !/^[a-z]+~-?\d+,-?\d+,-?\d+~[a-z0-9,;-]*$/.test(plan) || plan.split("~")[0] !== site)) return json({error: "invalid plan"}, 400);
    this.sql.exec("INSERT INTO bears (site, lon, lat, who, day, ts, plan) VALUES (?, ?, ?, ?, ?, ?, ?)", site, lon, lat, who, day, Date.now(), plan);
    this.bearsCache = null;
    return json({ok: true});
  }
  bearsPicks(){
    if (this.bearsCache && Date.now() - this.bearsCache.t < 60e3) return json(this.bearsCache.d);
    const sites = {}; for (const r of this.sql.exec("SELECT site, COUNT(*) AS n FROM bears GROUP BY site").toArray()) sites[r.site] = r.n;
    const cells = this.sql.exec("SELECT ROUND(lon, 2) AS x, ROUND(lat, 2) AS y, COUNT(*) AS n FROM bears GROUP BY x, y").toArray().map(r => [r.x, r.y, r.n]);
    const plans = this.sql.exec("SELECT site, plan, ts FROM bears WHERE plan IS NOT NULL ORDER BY id DESC LIMIT 10").toArray().map(r => ({site: r.site, plan: r.plan, ts: r.ts}));
    const d = {sites, cells, plans}; this.bearsCache = {t: Date.now(), d};
    return json(d);
  }

  addPlan(b, who){
    const code = String(b.code || ""), homes = Math.round(+b.homes), grade = String(b.grade || ""), hood = Math.round(+b.hood || 0), gallery = b.gallery ? 1 : 0;
    if (!CODE_RE.test(code) || !(homes >= 0 && homes <= 3000000) || !GRADES.has(grade) || !(hood >= 0 && hood <= 77)) return json({error: "invalid plan"}, 400);
    const num = (v, lo, hi) => { v = Math.round(+v); return v >= lo && v <= hi ? v : null; };
    const rent = num(b.rent, 300, 20000), rentno = num(b.rentNo, 300, 20000), aff = num(b.aff, 0, 3000000), nm = num(b.nm, 0, 999);   // nm: index into the plan-name list in shape/plans.js
    const n = this.sql.exec("SELECT COUNT(*) AS n FROM plans WHERE who = ?", who).one().n;
    if (n >= 40) return json({error: "slow down"}, 429);
    // the same person re-running the same plan updates their row instead of stacking duplicates
    const dup = this.sql.exec("SELECT id, gallery FROM plans WHERE who = ? AND code = ?", who, code).toArray()[0];
    let id;
    if (dup){ this.sql.exec("UPDATE plans SET homes = ?, grade = ?, hood = ?, gallery = ?, rent = ?, rentno = ?, aff = ?, nm = COALESCE(?, nm), ts = ? WHERE id = ?", homes, grade, hood, dup.gallery || gallery, rent, rentno, aff, nm, Date.now(), dup.id); id = dup.id; }
    else id = this.sql.exec("INSERT INTO plans (code, homes, grade, hood, gallery, rent, rentno, aff, nm, who, ts) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?) RETURNING id", code, homes, grade, hood, gallery, rent, rentno, aff, nm, who, Date.now()).one().id;
    this.cache = null;
    return json({ok: true, id});
  }

  // a shared plan link: only the plan code and numbers are stored (no text, no image), and the preview image is drawn from them
  async addCard(b, who){
    const code = String(b.code || ""), homes = Math.round(+b.homes), grade = String(b.grade || ""), goal = Math.round(+b.goal), rent = Math.round(+b.rent), rentno = Math.round(+b.rentNo), mode = Math.round(+b.mode || 0);
    if (!CODE_RE.test(code) || !(homes >= -500000 && homes <= 3000000) || !GRADES.has(grade) || !(goal > 0 && goal < 2000000) || !(rent > 0 && rent < 20000) || !(rentno > 0 && rentno < 20000) || !(mode >= 0 && mode <= 2)) return json({error: "invalid"}, 400);
    const id = (await hash("card|" + code + "|" + homes + "|" + grade + "|" + goal)).slice(0, 12);
    if (!this.sql.exec("SELECT 1 FROM cards WHERE id = ?", id).toArray().length){
      if (this.sql.exec("SELECT COUNT(*) AS n FROM cards WHERE who = ?", who).one().n >= 60) return json({error: "slow down"}, 429);
      this.sql.exec("INSERT INTO cards (id, code, homes, grade, goal, rent, rentno, mode, who, ts) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", id, code, homes, grade, goal, rent, rentno, mode, who, Date.now());
    }
    return json({ok: true, id});
  }

  addFeedback(b, who){
    const text = String(b.text || "").trim().slice(0, 2000), page = String(b.page || "").replace(/[^a-z/-]/g, "").slice(0, 40);
    if (text.length < 3) return json({error: "empty"}, 400);
    if (this.sql.exec("SELECT COUNT(*) AS n FROM feedback WHERE who = ?", who).one().n >= 10) return json({error: "slow down"}, 429);
    this.sql.exec("INSERT INTO feedback (text, page, who, ts) VALUES (?, ?, ?, ?)", text, page, who, Date.now());
    return json({ok: true});
  }

  like(id, who){
    const row = this.sql.exec("SELECT id FROM plans WHERE id = ? AND gallery = 1", id).toArray()[0];
    if (!row) return json({error: "not found"}, 404);
    const had = this.sql.exec("SELECT 1 FROM likes WHERE plan = ? AND who = ?", id, who).toArray().length;
    if (!had){ this.sql.exec("INSERT INTO likes (plan, who) VALUES (?, ?)", id, who); this.sql.exec("UPDATE plans SET likes = likes + 1 WHERE id = ?", id); }
    return json({ok: true, likes: this.sql.exec("SELECT likes FROM plans WHERE id = ?", id).one().likes});
  }

  gallery(sort, hood, limit){
    const where = "gallery = 1" + (hood ? " AND hood = " + Math.round(hood) : "");
    const order = sort === "top" ? "likes DESC, homes DESC" : "ts DESC";
    const rows = this.sql.exec(`SELECT ${COLS} FROM plans WHERE ${where} ORDER BY ${order} LIMIT ${Math.max(1, Math.min(60, Math.round(limit) || 30))}`).toArray();
    return json({plans: rows});
  }

  stats(hood){
    const now = Date.now();
    if (!this.cache || now - this.cache.t > 60000){
      const rows = this.sql.exec("SELECT code, homes, hood FROM plans ORDER BY ts DESC LIMIT 20000").toArray();
      this.cache = {t: now, rows: rows.map(r => ({homes: r.homes, hood: r.hood, f: features(r.code)}))};
    }
    const summarize = (rows) => {
      const n = rows.length; if (!n) return {n: 0};
      const on = {}; BIT_KEYS.forEach(k => on[k] = rows.filter(r => r.f[k]).length / n);
      const lv = (k, m = 5) => [...Array(m).keys()].map(t => rows.filter(r => r.f[k] === t).length / n);
      const homes = rows.map(r => r.homes).sort((a, b) => a - b);
      return {n, avgHomes: Math.round(homes.reduce((a, b) => a + b, 0) / n), medianHomes: homes[Math.floor(n / 2)], policies: on,
        str: [0,1,2].map(t => rows.filter(r => r.f.str === t).length / n), aro: [0,1,2,3].map(t => rows.filter(r => r.f.aro === t).length / n),
        tod: lv("tod", 7), metra: lv("metra"), sub: lv("sub"), corr: lv("corr")};
    };
    const all = this.cache.rows;
    return json({all: summarize(all), hood: hood ? summarize(all.filter(r => r.hood === hood)) : null}, 200, {"cache-control": "public, max-age=60"});
  }
}
