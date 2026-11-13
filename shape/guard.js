/* One way to write dates and numbers on every page (Nov. 12, 2026):
     scFmt.date("2026-11-12")      → "Nov. 12, 2026"   (AP months: March–July spelled out, Sept.)
     scFmt.date(d, {year:false})   → "Nov. 12";  {weekday:true} → "Thursday, Nov. 12, 2026" ("short" → "Thu., …")
     scFmt.month(d)                → "Nov. 2025"   (all dates are shown in Chicago time)
     scFmt.dateTime(d)             → "Nov. 12, 2026, 9:05 p.m."
     scFmt.money(882.4e6)          → "$882M"; 1.24e9 → "$1.2B"; 4.5e6 → "$4.5M"; 45000 → "$45,000"
     scFmt.num(3916)               → "3,916"
     scFmt.pct(0.334)              → "33%"   (pct(x, 1) keeps one decimal) */
window.scFmt = window.scFmt || (function(){
  const MON = ["Jan.", "Feb.", "March", "April", "May", "June", "July", "Aug.", "Sept.", "Oct.", "Nov.", "Dec."];
  const toD = d => d instanceof Date ? d : typeof d === "number" ? new Date(d) : /^\d{4}-\d{2}-\d{2}$/.test(d) ? new Date(d + "T12:00:00") : new Date(String(d).replace(/T(\d\d:\d\d)Z$/, "T$1:00Z"));
  const P = (d, o) => { const f = new Intl.DateTimeFormat("en-US", Object.assign({timeZone: "America/Chicago"}, o)); const r = {}; f.formatToParts(d).forEach(x => r[x.type] = x.value); return r; };
  const WD = {Mon: "Mon.", Tue: "Tue.", Wed: "Wed.", Thu: "Thu.", Fri: "Fri.", Sat: "Sat.", Sun: "Sun."};
  const date = (d, o) => { d = toD(d); if (isNaN(d)) return ""; o = o || {};
    const r = P(d, {year: "numeric", month: "numeric", day: "numeric", weekday: o.weekday === "short" ? "short" : "long"});
    const w = o.weekday ? (o.weekday === "short" ? WD[r.weekday] || r.weekday : r.weekday) + ", " : "";
    return w + MON[+r.month - 1] + " " + (+r.day) + (o.year === false ? "" : ", " + r.year); };
  const month = d => { d = toD(d); if (isNaN(d)) return ""; const r = P(d, {year: "numeric", month: "numeric"}); return MON[+r.month - 1] + " " + r.year; };
  const time = d => { d = toD(d); const r = P(d, {hour: "numeric", minute: "2-digit", hour12: true}); return (+r.hour) + (r.minute !== "00" ? ":" + r.minute : "") + " " + (r.dayPeriod === "AM" ? "a.m." : "p.m."); };
  const num = (n, dp) => n == null || isNaN(n) ? "–" : Number(n).toLocaleString("en-US", {maximumFractionDigits: dp || 0, minimumFractionDigits: dp || 0});
  const money = n => { if (n == null || isNaN(n)) return "–"; const s = n < 0 ? "−" : "", a = Math.abs(n);
    if (a >= 1e9) return s + "$" + (a / 1e9).toFixed(a >= 1e10 ? 0 : 1).replace(/\.0$/, "") + "B";
    if (a >= 1e6) return s + "$" + (a / 1e6).toFixed(a >= 1e7 ? 0 : 1).replace(/\.0$/, "") + "M";
    return s + "$" + num(a); };
  return {date, month, time, dateTime: d => date(d) + ", " + time(d), num, money, pct: (x, dp) => x == null || isNaN(x) ? "–" : (x * 100).toFixed(dp || 0) + "%", MON};
})();

/* Data guard, loaded first on every page that reads data files. If one of this site's data files (JSON, building files) fails to
   load, or a page chokes on one, the reader gets one plain note with a Refresh button instead of a blank or frozen page.
   Calls to /api/ (plans, endorsements) are optional extras, so their failures are left to each page. */
(function(){
  let shown = false;
  const own = u => { try { const x = new URL(u, location.href); return x.origin === location.origin && !/^\/api\//.test(x.pathname) && /\.(json|wasm|bin|xml)$/.test(x.pathname); } catch (e) { return false; } };
  function note(){
    if (shown) return; shown = true;
    const go = () => {
      const d = document.createElement("div"); d.className = "sc-dataerr"; d.setAttribute("role", "alert");
      d.innerHTML = '<span>Some of this page\'s data didn\'t load. Check your connection, then refresh.</span><button type="button">Refresh</button><button type="button" aria-label="Close">×</button>';
      d.style.cssText = "position:fixed;left:50%;bottom:16px;transform:translateX(-50%);z-index:99;display:flex;gap:10px;align-items:center;flex-wrap:wrap;justify-content:center;" +
        "max-width:calc(100vw - 24px);background:#fff;border:1px solid #d7dce2;border-radius:14px;box-shadow:0 10px 30px rgba(20,30,50,.18);padding:10px 12px 10px 16px;" +
        "font:14px/1.4 'Instrument Sans',system-ui,sans-serif;color:#1a1d21";
      const [, r, x] = d.children;
      r.style.cssText = "font:600 14px 'Instrument Sans',system-ui,sans-serif;background:#2b5da0;color:#fff;border:0;border-radius:999px;padding:9px 16px;min-height:40px;cursor:pointer";
      x.style.cssText = "font:20px/1 system-ui;background:none;border:0;color:#5a6069;min-width:40px;min-height:40px;cursor:pointer";
      r.onclick = () => location.reload(); x.onclick = () => d.remove();
      document.body.appendChild(d);
    };
    // wait a moment: if the page already explains the failure itself, don't add a second note
    const later = () => setTimeout(() => { if (!/didn.t load|couldn.t load/i.test(document.body.innerText)) go(); }, 1200);
    document.body ? later() : document.addEventListener("DOMContentLoaded", later);
  }
  const f = window.fetch;
  if (f) window.fetch = function(input){
    const u = typeof input === "string" ? input : input && input.url;
    const p = f.apply(this, arguments);
    // tiles (lot, rules, grants, street, address shards) are fetched by position and some simply don't exist: a 404 there is normal
    if (u && own(u)) p.then(r => { if (!r.ok && r.status !== 304 && !(r.status === 404 && /\/data\/(t|r|g|a)\//.test(u))) note(); }, e => { if (!e || e.name !== "AbortError") note(); });
    return p;
  };
  addEventListener("unhandledrejection", e => { const m = String(e.reason && e.reason.message || e.reason || ""); if (/JSON|Failed to fetch|NetworkError|Load failed/i.test(m)) note(); });
  // a map or chart library from the CDN that fails to load
  addEventListener("error", e => { const t = e.target; if (t && t.tagName === "SCRIPT" && t.src && !/cloudflareinsights/.test(t.src)) note(); }, true);
  window.scDataError = note;
})();
