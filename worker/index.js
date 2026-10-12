// Fix Chicago Housing community API: anonymous plan gallery, "what other players chose", and neighborhood stats.
// Static files are served by Workers Assets; only /api/* reaches this script.
// No free text is stored (titles are generated from the plan), so nothing needs moderation.

const BIT_KEYS = ["build","stair","adu","lots","pre","permits","mpls","camb","small","park","vac","social","comm","mega","down","pmin","mora","rentc","xfer"];
const B32 = "0123456789abcdefghijklmnopqrstuv";
const CODE_RE = /^(u4[0-9a-o]{39}[0-4][0-4][0-4][0-3][0-2][0-2][0-9a-v]{3}|u5[0-9a-o]{39}[0-4][0-4][0-4][0-3][0-2][0-2][0-9a-v]{4})[0-2][0-4]$/;
const GRADES = new Set(["A+","A","B","C","D","F","–"]);

const json = (data, status = 200, extra = {}) => new Response(JSON.stringify(data), {status, headers: {"content-type": "application/json", "cache-control": "no-store", ...extra}});

export default {
  async fetch(req, env) {
    const url = new URL(req.url);
    if (!url.pathname.startsWith("/api/")) return env.ASSETS.fetch(req);
    const stub = env.COMMUNITY.get(env.COMMUNITY.idFromName("v1"));
    const ip = req.headers.get("cf-connecting-ip") || "0";
    const fwd = new Request(req.url, {method: req.method, headers: {"content-type": "application/json", "x-ip": ip}, body: req.method === "POST" ? await req.text() : undefined});
    return stub.fetch(fwd);
  },
};

function features(code){
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

export class Community {
  constructor(state, env){
    this.sql = state.storage.sql;
    this.sql.exec(`CREATE TABLE IF NOT EXISTS plans (id INTEGER PRIMARY KEY AUTOINCREMENT, code TEXT NOT NULL, homes INTEGER NOT NULL, grade TEXT NOT NULL,
      hood INTEGER NOT NULL DEFAULT 0, gallery INTEGER NOT NULL DEFAULT 0, likes INTEGER NOT NULL DEFAULT 0, who TEXT NOT NULL, ts INTEGER NOT NULL)`);
    this.sql.exec(`CREATE TABLE IF NOT EXISTS likes (plan INTEGER NOT NULL, who TEXT NOT NULL, PRIMARY KEY (plan, who))`);
    this.sql.exec(`CREATE INDEX IF NOT EXISTS plans_ts ON plans(ts)`);
    this.cache = null;
  }

  async fetch(req){
    const url = new URL(req.url), path = url.pathname;
    const day = new Date().toISOString().slice(0, 10);
    const who = await hash((req.headers.get("x-ip") || "0") + "|" + day + "|fch");
    try {
      if (path === "/api/plan" && req.method === "POST") return this.addPlan(await req.json(), who);
      if (path === "/api/stats" && req.method === "GET") return this.stats(+url.searchParams.get("hood") || 0);
      if (path === "/api/gallery" && req.method === "GET") return this.gallery(url.searchParams.get("sort") === "top" ? "top" : "new", +url.searchParams.get("hood") || 0);
      const m = path.match(/^\/api\/like\/(\d+)$/);
      if (m && req.method === "POST") return this.like(+m[1], who);
    } catch (e) { return json({error: "bad request"}, 400); }
    return json({error: "not found"}, 404);
  }

  addPlan(b, who){
    const code = String(b.code || ""), homes = Math.round(+b.homes), grade = String(b.grade || ""), hood = Math.round(+b.hood || 0), gallery = b.gallery ? 1 : 0;
    if (!CODE_RE.test(code) || !(homes >= 0 && homes <= 3000000) || !GRADES.has(grade) || !(hood >= 0 && hood <= 77)) return json({error: "invalid plan"}, 400);
    const n = this.sql.exec("SELECT COUNT(*) AS n FROM plans WHERE who = ?", who).one().n;
    if (n >= 40) return json({error: "slow down"}, 429);
    // the same person re-running the same plan updates their row instead of stacking duplicates
    const dup = this.sql.exec("SELECT id, gallery FROM plans WHERE who = ? AND code = ?", who, code).toArray()[0];
    let id;
    if (dup){ this.sql.exec("UPDATE plans SET homes = ?, grade = ?, hood = ?, gallery = ?, ts = ? WHERE id = ?", homes, grade, hood, dup.gallery || gallery, Date.now(), dup.id); id = dup.id; }
    else id = this.sql.exec("INSERT INTO plans (code, homes, grade, hood, gallery, who, ts) VALUES (?, ?, ?, ?, ?, ?, ?) RETURNING id", code, homes, grade, hood, gallery, who, Date.now()).one().id;
    this.cache = null;
    return json({ok: true, id});
  }

  like(id, who){
    const row = this.sql.exec("SELECT id FROM plans WHERE id = ? AND gallery = 1", id).toArray()[0];
    if (!row) return json({error: "not found"}, 404);
    const had = this.sql.exec("SELECT 1 FROM likes WHERE plan = ? AND who = ?", id, who).toArray().length;
    if (!had){ this.sql.exec("INSERT INTO likes (plan, who) VALUES (?, ?)", id, who); this.sql.exec("UPDATE plans SET likes = likes + 1 WHERE id = ?", id); }
    return json({ok: true, likes: this.sql.exec("SELECT likes FROM plans WHERE id = ?", id).one().likes});
  }

  gallery(sort, hood){
    const where = "gallery = 1" + (hood ? " AND hood = " + hood : "");
    const order = sort === "top" ? "likes DESC, homes DESC" : "ts DESC";
    const rows = this.sql.exec(`SELECT id, code, homes, grade, hood, likes, ts FROM plans WHERE ${where} ORDER BY ${order} LIMIT 30`).toArray();
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
      const lv = (k) => [0,1,2,3,4].map(t => rows.filter(r => r.f[k] === t).length / n);
      const homes = rows.map(r => r.homes).sort((a, b) => a - b);
      return {n, avgHomes: Math.round(homes.reduce((a, b) => a + b, 0) / n), medianHomes: homes[Math.floor(n / 2)], policies: on,
        str: [0,1,2].map(t => rows.filter(r => r.f.str === t).length / n), aro: [0,1,2].map(t => rows.filter(r => r.f.aro === t).length / n),
        tod: lv("tod"), metra: lv("metra"), sub: lv("sub"), corr: lv("corr")};
    };
    const all = this.cache.rows;
    return json({all: summarize(all), hood: hood ? summarize(all.filter(r => r.hood === hood)) : null}, 200, {"cache-control": "public, max-age=60"});
  }
}
