/* Shape Chicago: follow your ward (no account; the ward number stays in this browser as "sc-follow").
   SCWard.get() / set(n) / clear(); SCWard.picker(el) draws the three ways to pick a ward (address, location, list);
   SCWard.summary(n, since) gathers that ward's news, rezonings, permits, meetings and alderperson from the site's own data files. */
(function(){
  const KEY = "sc-follow", SEEN = "sc-follow-seen";
  const get = () => { try { const n = +localStorage.getItem(KEY); return n >= 1 && n <= 50 ? n : 0; } catch (e) { return 0; } };
  const set = n => { try { localStorage.setItem(KEY, String(n)); localStorage.setItem("sc-ward", String(n)); } catch (e) {} document.dispatchEvent(new CustomEvent("sc-ward", {detail:n})); };
  const clear = () => { try { localStorage.removeItem(KEY); } catch (e) {} document.dispatchEvent(new CustomEvent("sc-ward", {detail:0})); };
  const esc = t => String(t == null ? "" : t).replace(/[&<>"]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
  const cache = {};
  const load = u => cache[u] || (cache[u] = fetch(u).then(r => { if (!r.ok) throw 0; return r.json(); }));

  // point in the ward outlines (wards.json: [{ward, polys:[[ring, holes...]]}])
  function inRing(x, y, R){ let c = false; for (let i = 0, j = R.length - 1; i < R.length; j = i++){ const [xi, yi] = R[i], [xj, yj] = R[j]; if ((yi > y) !== (yj > y) && x < (xj - xi) * (y - yi) / (yj - yi) + xi) c = !c; } return c; }
  async function wardAt(lon, lat){
    const W = await load("/wards.json");
    for (const w of W) for (const P of w.polys) if (inRing(lon, lat, P[0]) && !P.slice(1).some(h => inRing(lon, lat, h))) return w.ward;
    return 0;
  }
  // an address: the lot tool's index (lot/data: streets, then house numbers, then the parcel's ward)
  const ABBR = {AVENUE:"AVE", AV:"AVE", STREET:"ST", BOULEVARD:"BLVD", ROAD:"RD", PLACE:"PL", DRIVE:"DR", COURT:"CT", PARKWAY:"PKWY", TERRACE:"TER", NORTH:"N", SOUTH:"S", EAST:"E", WEST:"W"};
  const norm = s => s.toUpperCase().replace(/[.,#]/g, " ").replace(/\b(\d+)(ST|ND|RD|TH)\b/g, "$1").replace(/\s+/g, " ").trim().split(" ").map(w => ABBR[w] || w).join(" ");
  async function wardOfAddress(text){
    const m = norm(text).match(/^(\d+)\s+(.+)$/); if (!m) return {err:"Type a house number and street, like 2200 N Milwaukee."};
    const num = +m[1], words = m[2].split(" ");
    const L = (await load("/lot/data/streets.json").catch(() => [])).map(([s, c]) => ({s, c, n:s.replace(/\b(\d+)(ST|ND|RD|TH)\b/g, "$1")}));
    let best = null, bs = -1;
    for (const st of L){ const parts = st.n.split(" "); let ok = true, sc = 0; for (const w of words){ const i = parts.findIndex(p => p.startsWith(w)); if (i < 0){ ok = false; break; } sc += parts[i] === w ? 2 : 1; } if (ok){ const v = sc + Math.log10(st.c + 1) - st.n.length / 100; if (v > bs){ bs = v; best = st.s; } } }
    if (!best) return {err:"Couldn't find that street."};
    const sh = (best.replace(/^[NSEW] /, "").replace(/[^A-Z0-9]/g, "").slice(0, 2)) || "_";
    const R = (await load("/lot/data/a/" + sh + ".json").catch(() => ({})))[best]; if (!R || !R.length) return {err:"Couldn't find that street."};
    let r = R[0], bd = 1e9; for (const x of R){ const d = Math.abs(x[0] - num); if (d < bd){ bd = d; r = x; } }
    const T = await load("/lot/data/t/" + r[1] + "_" + r[2] + ".json").catch(() => null);
    const w = T && T.p[r[3]] ? +T.p[r[3]][10] : 0;
    return w ? {ward:w, addr:r[0] + " " + best} : {err:"Couldn't place that address in a ward."};
  }

  // the picker: address, location, or the list of 50
  async function picker(el, done){
    el.innerHTML = '<form class="wpick"><label class="wpaddr"><span>Your address</span><input type="text" name="a" placeholder="2200 N Milwaukee Ave" autocomplete="street-address"></label><button class="sc-btn primary" type="submit">Find my ward</button>'
      + '<button class="sc-btn" type="button" data-loc>Use my location</button><select aria-label="Or pick a ward"><option value="">Or pick from the list</option></select><p class="wmsg" aria-live="polite"></p></form>';
    const f = el.querySelector("form"), msg = el.querySelector(".wmsg"), sel = el.querySelector("select");
    load("/wards/data/wards.json").then(D => { sel.innerHTML += D.wards.map(w => '<option value="' + w.w + '">Ward ' + w.w + (w.ald && w.ald.name ? " · " + esc(w.ald.name.split(",").reverse().join(" ").trim()) : "") + '</option>').join(""); }).catch(() => { sel.innerHTML += Array.from({length:50}, (_, i) => '<option value="' + (i + 1) + '">Ward ' + (i + 1) + '</option>').join(""); });
    const pick = w => { set(w); done && done(w); };
    f.addEventListener("submit", async e => { e.preventDefault(); const v = f.a.value.trim(); if (!v) return; msg.textContent = "Looking it up…"; const r = await wardOfAddress(v).catch(() => ({err:"Couldn't look that up right now."})); if (r.err) msg.textContent = r.err; else pick(r.ward); });
    sel.addEventListener("change", () => { if (sel.value) pick(+sel.value); });
    el.querySelector("[data-loc]").addEventListener("click", () => {
      if (!navigator.geolocation){ msg.textContent = "Your browser can't share a location. Type your address instead."; return; }
      msg.textContent = "Finding you…";
      navigator.geolocation.getCurrentPosition(async p => { const w = await wardAt(p.coords.longitude, p.coords.latitude); if (w) pick(w); else msg.textContent = "That spot isn't inside a Chicago ward. Type your address instead."; },
        () => { msg.textContent = "Couldn't get your location. Type your address instead."; }, {timeout:10000, maximumAge:600000});
    });
  }

  // everything about one ward, newest first; "since" = the last time you looked (ISO), for the new counts
  async function summary(n, since){
    const [D, N, M, T] = await Promise.all([load("/wards/data/wards.json"), load("/news/data/news.json").catch(() => ({items:[]})), load("/wards/data/meetings.json").catch(() => ({meetings:[]})), load("/tracker/data.json").catch(() => null)]);
    const W = D.wards.find(w => w.w === n) || {};
    const news = (N.items || []).filter(i => (i.w || []).includes(n)).map(i => ({...i, exact: (i.wq || [])[(i.w || []).indexOf(n)] !== "area"}));
    const z = (W.z || []).slice().sort((a, b) => (b.d || "").localeCompare(a.d || ""));
    const now = Date.now() - 2 * 3600e3;
    const meet = (M.meetings || []).filter(x => Date.parse(x.d) >= now && !/cancel/i.test(x.st || ""));
    const zoningMeet = meet.find(x => /Zoning/.test(x.b)), council = meet.find(x => x.b === "City Council");
    const permits = T && T.projects ? T.projects.filter(p => +p.ward === n).sort((a, b) => (b.date || "").localeCompare(a.date || "")) : [];
    const day = since ? since.slice(0, 10) : "";
    const isNew = d => since && d && d > since;
    return {n, W, ald:W.ald || {}, news, z, permits, zoningMeet, council,
      fresh:{news: news.filter(i => isNew(i.d)).length, z: z.filter(x => day && x.d > day).length, homes: permits.filter(p => day && p.date > day).reduce((s, p) => s + (+p.homes || 0), 0)}};
  }
  const seen = () => { try { return localStorage.getItem(SEEN) || ""; } catch (e) { return ""; } };
  const markSeen = () => { try { localStorage.setItem(SEEN, new Date().toISOString().slice(0, 16) + "Z"); } catch (e) {} };

  window.SCWard = {get, set, clear, picker, summary, wardAt, wardOfAddress, seen, markSeen, esc};
})();
