/* Shape Chicago: plan cards for the plans people shared from the simulators (home page and /plans/): housing first, then
   transit, budget and pensions (SIMS, near the end).
   Reads a plan code (the same format as housing/index.html encodePlan/decodePlan) and draws a small map of what it rezones,
   the main choices as chips, the numbers, and an Endorse button. A plan's name and "by" name are what its sharer typed
   (checked by worker/names.js) or, if they kept the suggestion, one from NAMES.
   Map data: /plans/areas.json from tools/prep_plancards.py. */
(function(){
  const ALPHA = "0123456789abcdefghijklmno", B32 = "0123456789abcdefghijklmnopqrstuv";
  const BIT_KEYS = ["build","stair","adu","lots","pre","permits","mpls","camb","small","park","vac","social","comm","mega","down","pmin","mora","rentc","xfer","vland"];
  const TIER = ["Today", "3-flats", "6-flats", "Mid-rises", "High-rises", "Towers", "Supertalls"];
  const COLOR = [null, "#7ec8ec", "#41b6e6", "#2b5da0", "#14335f", "#0f7c86", "#161820"];
  const SHORT = {build:"BUILD Act", stair:"Single-stair buildings", adu:"Coach houses everywhere", lots:"Build on city lots", pre:"Rein in prerogative", permits:"Faster permits",
    mpls:"Minneapolis plan", camb:"4-story apartments everywhere", small:"Small-lot homes", park:"No parking minimums", comm:"Housing on commercial land",
    vac:"Empty-homes tax", social:"Triple the social housing fund", mega:"Megaprojects built", vland:"Build on vacant lots",
    down:"Downzoning", pmin:"Parking minimums back", mora:"Moratoriums", rentc:"Rent control on new buildings", xfer:"Mansion tax"};
  const CUT = new Set(["down", "pmin", "mora", "rentc", "xfer"]);
  const AREAS = ["", "Rogers Park", "West Ridge", "Uptown", "Lincoln Square", "North Center", "Lake View", "Lincoln Park", "Near North Side", "Edison Park", "Norwood Park", "Jefferson Park", "Forest Glen", "North Park", "Albany Park", "Portage Park", "Irving Park", "Dunning", "Montclare", "Belmont Cragin", "Hermosa", "Avondale", "Logan Square", "Humboldt Park", "West Town", "Austin", "West Garfield Park", "East Garfield Park", "Near West Side", "North Lawndale", "South Lawndale", "Lower West Side", "Loop", "Near South Side", "Armour Square", "Douglas", "Oakland", "Fuller Park", "Grand Boulevard", "Kenwood", "Washington Park", "Hyde Park", "Woodlawn", "South Shore", "Chatham", "Avalon Park", "South Chicago", "Burnside", "Calumet Heights", "Roseland", "Pullman", "South Deering", "East Side", "West Pullman", "Riverdale", "Hegewisch", "Garfield Ridge", "Archer Heights", "Brighton Park", "McKinley Park", "Bridgeport", "New City", "West Elsdon", "Gage Park", "Clearing", "West Lawn", "Chicago Lawn", "West Englewood", "Englewood", "Greater Grand Crossing", "Ashburn", "Auburn Gresham", "Beverly", "Washington Heights", "Mount Greenwood", "Morgan Park", "O'Hare", "Edgewater"];
  const STAR = "M12 1 L14.4 7.84 L21.53 6.5 L16.8 12 L21.53 17.5 L14.4 16.16 L12 23 L9.6 16.16 L2.47 17.5 L7.2 12 L2.47 6.5 L9.6 7.84 Z";
  const fmt = n => Number(n).toLocaleString("en-US");
  const esc = t => String(t == null ? "" : t).replace(/[&<>"]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));

  function blank(){ return {areas:{}, tod:0, metra:0, corr:0, office:0, str:0, aro:1, g:3, on:{}}; }
  function bitsOn(p, bits){ BIT_KEYS.forEach((k, i) => { if (bits & (1 << i)) p.on[k] = 1; }); }
  function areas39(str, p){ for (let i = 0; i < 39; i++){ const v = ALPHA.indexOf(str[i]), n = 1 + i * 2; if (Math.floor(v / 5)) p.areas[n] = Math.floor(v / 5); if (v % 5 && n + 1 <= 77) p.areas[n + 1] = v % 5; } }
  // the formats housing/index.html has written (u6 now; u5 and u4 from older plans)
  function decode(code){
    const s = String(code || ""); let m, p = blank();
    if ((m = s.match(/^u6([0-6]{77})([0-6])([0-4])([0-4])([0-3])([0-2])([0-3])([0-9a-v]{4})([0-4])/))){
      for (let i = 0; i < 77; i++) if (+m[1][i]) p.areas[i + 1] = +m[1][i];
      [p.tod, p.metra, p.corr, p.office, p.str, p.aro] = [m[2], m[3], m[4], m[5], m[6], m[7]].map(Number);
      bitsOn(p, B32.indexOf(m[8][0]) | (B32.indexOf(m[8][1]) << 5) | (B32.indexOf(m[8][2]) << 10) | (B32.indexOf(m[8][3]) << 15)); p.g = +m[9]; return p;
    }
    if ((m = s.match(/^u(5)([0-9a-o]{39})([0-5])([0-4])([0-4])([0-3])([0-2])([0-2])([0-9a-v]{4})([0-2])/) || s.match(/^u(4)([0-9a-o]{39})([0-4])([0-4])([0-4])([0-3])([0-2])([0-2])([0-9a-v]{3})([0-2])/))){
      areas39(m[2], p); [p.tod, p.metra, p.corr, p.office, p.str, p.aro] = [m[3], m[4], m[5], m[6], m[7], m[8]].map(Number);
      const b = m[9]; bitsOn(p, B32.indexOf(b[0]) | (B32.indexOf(b[1]) << 5) | (B32.indexOf(b[2]) << 10) | (b[3] ? B32.indexOf(b[3]) << 15 : 0)); p.g = +m[10]; return p;
    }
    return null;
  }
  const MODE = g => g === 4 ? "Every ward" : g < 3 ? "Hard mode" : "Normal";

  // the plan's choices, biggest first: [{t: text, kind: "zone"|"policy"|"cut"}]
  function choices(p){
    const out = [];
    if (p.tod && p.tod === p.metra) out.push({t: TIER[p.tod] + " near the L and Metra", kind:"zone"});
    else { if (p.tod) out.push({t: TIER[p.tod] + " near the L", kind:"zone"}); if (p.metra) out.push({t: TIER[p.metra] + " near Metra", kind:"zone"}); }
    if (p.corr) out.push({t: TIER[p.corr] + " on main streets", kind:"zone"});
    const ar = Object.keys(p.areas).filter(n => p.areas[n]).map(Number);
    if (ar.length) out.push({t: ar.length <= 2 ? "Rezones " + ar.map(n => AREAS[n]).join(" and ") : "Rezones " + ar.length + " neighborhoods", kind:"zone"});
    if (p.office) out.push({t: ["", "10%", "25%", "50%"][p.office] + " of old offices to homes", kind:"policy"});
    for (const k of BIT_KEYS) if (p.on[k] && !CUT.has(k)) out.push({t: SHORT[k], kind:"policy"});
    if (p.str) out.push({t: p.str === 2 ? "Tight short-term rental limits" : "Short-term rental limits", kind:"policy"});
    if (p.aro !== 1) out.push({t: p.aro === 3 ? "No affordable requirement" : (["10%", "", "30%"][p.aro]) + " affordable requirement", kind:"policy"});
    for (const k of BIT_KEYS) if (p.on[k] && CUT.has(k)) out.push({t: SHORT[k], kind:"cut"});
    return out;
  }
  // Suggested plan names (Chicago streets and Chicago-isms): the share box offers one, and a plan whose sharer kept the
  // suggestion stores its index as `nm`; plans shared before names existed get one from their id.
  // Append only: changing the order renames shared plans.
  const NAMES = ["Kedzie", "Milwaukee Avenue", "Halsted", "Ashland", "Western Avenue", "Cicero", "Pulaski", "Damen", "Clark Street", "Broadway",
    "Sheridan Road", "Archer Avenue", "Ogden", "Cermak", "Roosevelt Road", "Division Street", "Belmont", "Fullerton", "Diversey", "Lawrence Avenue",
    "Irving Park", "Devon Avenue", "Howard Street", "Wacker", "State Street", "LaSalle", "Lake Shore", "King Drive", "Stony Island", "Cottage Grove",
    "Garfield Boulevard", "63rd Street", "79th Street", "95th Street", "47th Street", "18th Street", "26th Street", "Harlem Avenue", "Central Park", "California Avenue",
    "Kostner", "Narragansett", "Elston", "Lincoln Avenue", "Grand Avenue", "Chicago Avenue", "North Avenue", "Madison Street", "Racine", "Wentworth",
    "Vincennes", "Commercial Avenue", "Jeffery", "Lake Park", "Wabash", "Dearborn", "Montrose", "Foster", "Touhy", "Addison",
    "Three-Flat", "Two-Flat", "Greystone", "Bungalow Belt", "Six-Flat", "Courtyard Building", "Coach House", "Garden Unit", "Back Porch", "Gangway",
    "Corner Store", "Big Shoulders", "Lakefront", "Riverwalk", "Prairie", "Elevated", "Loop", "Lake Effect", "Third Coast", "Second City",
    "Windy City", "Hawk", "Dibs", "Polar Vortex", "Hot Dog Stand", "Italian Beef", "Tavern Cut", "Brown Line", "Pink Line", "Blue Line",
    "Red Line", "Green Line", "Orange Line", "Purple Line", "Yellow Line", "Metra", "Bike Lane", "Block Party", "Street Festival", "Six Corners"];
  const hashN = s => { let h = 2166136261; for (const ch of String(s)) h = Math.imul(h ^ ch.charCodeAt(0), 16777619); return Math.abs(h); };
  // a plan's name: what its sharer typed (checked on the server), else one from NAMES
  const nameOf = P => P.title ? P.title : "The " + NAMES[P.nm != null && NAMES[P.nm] ? P.nm : hashN("p" + (P.id || P.code)) % NAMES.length] + " Plan";
  // what kind of plan it is, from its biggest moves
  function kind(p){
    const c = choices(p), z = c.filter(x => x.kind === "zone"), pol = c.filter(x => x.kind === "policy").length, ar = Object.values(p.areas).filter(Boolean);
    if (c.some(x => x.kind === "cut")) return {t:"Cuts housing", c:"cut"};
    if (!z.length) return {t:pol ? "Policies only" : "No changes", c:"pol"};
    if (c.length >= 18) return {t:"Everything at once", c:"all"};
    if (p.tod >= 5 || ar.some(t => t >= 5)) return {t:"Towers", c:"tall"};
    const mm = p.on.build || p.on.camb || p.on.mpls || p.on.small || p.on.adu;
    if (mm && Math.max(p.tod, p.corr, p.metra, ...ar, 0) <= 2) return {t:"Missing middle", c:"mm"};
    if (ar.length >= 3 && ar.length * 1 > (p.tod ? 3 : 0)) return {t:"Neighborhood by neighborhood", c:"hood"};
    if (p.corr >= 3 && p.corr >= p.tod) return {t:"Main streets", c:"main"};
    if (p.tod) return {t:"Transit-first", c:"tod"};
    return {t:"Mixed", c:"all"};
  }
  // one line under the name: the main zoning moves and how many policies
  function title(p){
    const c = choices(p), z = c.filter(x => x.kind === "zone").map(x => x.t), n = c.length - z.length;
    if (!c.length) return "No changes from today";
    const head = z.slice(0, 2).join(", ");
    return head ? head + (n ? ", " + n + (n === 1 ? " policy" : " policies") : "") : n + (n === 1 ? " policy" : " policies") + ", no rezoning";
  }

  let GEO = null;
  function geo(){ return GEO || (GEO = fetch("/plans/areas.json").then(r => r.json()).catch(() => null)); }
  // a small map: neighborhoods filled by their zoning, main streets and stations in their level's color
  function map(p, G, cls){
    if (!G) return '<div class="pmap empty"></div>';
    const big = cls === "big", rL = big ? 9 : 15, rM = big ? 8 : 13, sw = big ? 2 : 3;
    let h = '<svg class="' + (cls || "pmap") + '" viewBox="-10 -10 ' + (G.w + 20) + ' 1020" role="img" aria-label="Map of what the plan rezones">';
    for (const n in G.areas){ const t = p.areas[n] || 0; h += '<path d="' + G.areas[n] + '" fill="' + (t ? COLOR[t] : "#e7ebef") + '" stroke="#fff" stroke-width="3"/>'; }
    if (p.corr) h += '<path d="' + G.corr + '" fill="none" stroke="' + COLOR[p.corr] + '" stroke-width="' + (big ? 5 : 7) + '" stroke-linecap="round"/>';
    if (p.metra) for (const [x, y] of G.M) h += '<circle cx="' + x + '" cy="' + y + '" r="' + rM + '" fill="' + COLOR[p.metra] + '" stroke="#fff" stroke-width="' + sw + '"/>';
    for (const [x, y] of G.L) h += p.tod ? '<circle cx="' + x + '" cy="' + y + '" r="' + rL + '" fill="' + COLOR[Math.min(p.tod, 6)] + '" stroke="#fff" stroke-width="' + sw + '"/>' : '<circle cx="' + x + '" cy="' + y + '" r="5" fill="#9aa3ad"/>';
    return h + "</svg>";
  }

  // endorsements: one per plan per browser (the server also allows one per person per day)
  const LS = "fch-liked";
  const liked = () => { try { return new Set(JSON.parse(localStorage.getItem(LS) || "[]")); } catch (e) { return new Set(); } };
  async function endorse(id, btn){
    const L = liked(); if (L.has(id)) return;
    btn.disabled = true;
    try {
      const r = await fetch("/api/like/" + id, {method:"POST", headers:{"content-type":"application/json"}, body:"{}"});
      if (!r.ok) throw 0; const d = await r.json();
      L.add(id); try { localStorage.setItem(LS, JSON.stringify([...L])); } catch (e) {}
      btn.classList.add("on"); btn.querySelector("span").textContent = "Endorsed"; btn.querySelector("b").textContent = fmt(d.likes);
      btn.animate && !matchMedia("(prefers-reduced-motion: reduce)").matches && btn.animate([{transform:"scale(1)"}, {transform:"scale(1.08)"}, {transform:"scale(1)"}], {duration:260, easing:"ease-out"});
    } catch (e) { btn.disabled = false; }
  }
  function endorseBtn(P){
    const on = liked().has(P.id);
    const b = document.createElement("button"); b.type = "button"; b.className = "pend" + (on ? " on" : ""); b.disabled = on;
    b.setAttribute("aria-label", (on ? "You endorsed this plan. " : "Endorse this plan. ") + P.likes + " endorsements");
    b.innerHTML = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M7 11v9H4v-9zM7 11l4-8c1.6 0 2.6 1.2 2.3 2.8L12.8 9H19a2 2 0 0 1 2 2.3l-1.2 6.9A2 2 0 0 1 17.8 20H7"/></svg><span>' + (on ? "Endorsed" : "Endorse") + '</span><b>' + fmt(P.likes) + '</b>';
    b.addEventListener("click", e => { e.preventDefault(); e.stopPropagation(); endorse(P.id, b); });
    return b;
  }
  // "By Maria from Pilsen · today", "From a neighbor · 3 days ago"
  const who = (P, place) => (P.author ? "By " + esc(P.author) + (place ? " from " + esc(place) : "") : place ? "From " + esc(place) : "From a neighbor") + " · " + ago(P.ts);
  const ago = ts => { const d = (Date.now() - ts) / 864e5; return d < 1 ? "today" : d < 2 ? "yesterday" : d < 30 ? Math.floor(d) + " days ago" : new Date(ts).toLocaleDateString("en-US", {month:"short", day:"numeric", year: d > 300 ? "numeric" : undefined}); };

  // one card: map, grade, title, numbers, what it does, endorse
  function card(P, G, opt){
    opt = opt || {};
    const p = decode(P.code); if (!p) return null;
    const c = choices(p), a = document.createElement("a"), K = kind(p);
    a.className = "pcard"; a.href = "/plans/#" + P.id;
    const g = String(P.grade || "–"), cut = c.some(x => x.kind === "cut");
    const rent = P.rent && P.rentno ? (P.rent < P.rentno ? "$" + fmt(P.rentno - P.rent) + " less rent a month" : P.rent > P.rentno ? "$" + fmt(P.rent - P.rentno) + " more rent a month" : "Rent about the same") : "";
    a.innerHTML = '<div class="pmapw">' + map(p, G) + '<span class="pgr" data-g="' + esc(g) + '"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="' + STAR + '"/></svg><i>' + esc(g) + '</i></span>' + (p.g !== 3 ? '<span class="pmode' + (p.g < 3 ? " hard" : "") + '">' + MODE(p.g) + '</span>' : "") + '</div>'
      + '<div class="pbody"><span class="pkind k-' + K.c + '">' + K.t + '</span><b class="pt">' + esc(nameOf(P)) + '</b><span class="psum">' + esc(title(p)) + '</span><span class="pwho">' + who(P, P.hood && AREAS[P.hood] ? AREAS[P.hood] : "") + '</span>'
      + '<div class="pnums"><span><b>' + fmt(P.homes) + '</b> homes by 2041</span>' + (rent ? '<span>' + rent + ' by 2041</span>' : "") + '</div>'
      + '<ul class="pchips">' + c.slice(0, opt.all ? 99 : 5).map(x => '<li class="' + x.kind + '">' + esc(x.t) + '</li>').join("") + (!opt.all && c.length > 5 ? '<li class="more">+' + (c.length - 5) + ' more</li>' : "") + '</ul>'
      + (cut ? '<span class="pwarn">Includes policies that cut housing</span>' : "") + '<div class="pfoot"><span class="popen">See the plan</span></div></div>';
    a.querySelector(".pfoot").prepend(endorseBtn(P));
    return a;
  }

  // plans this browser posted (ids saved by the housing tool), with endorsements since the last look
  const MINE = "fch-my-plans", SEEN = "fch-my-plans-seen";
  function mine(){ try { return JSON.parse(localStorage.getItem(MINE) || "[]").filter(n => n > 0); } catch (e) { return []; } }
  async function myNews(){
    const ids = mine(); if (!ids.length) return null;
    try {
      const r = await fetch("/api/plans?ids=" + ids.join(",")); if (!r.ok) return null;
      const {plans} = await r.json(); let seen = {}; try { seen = JSON.parse(localStorage.getItem(SEEN) || "{}"); } catch (e) {}
      const out = plans.map(P => ({P, fresh: Math.max(0, P.likes - (seen[P.id] || 0))}));
      return {plans: out, mark(){ const s = {}; plans.forEach(P => s[P.id] = P.likes); try { localStorage.setItem(SEEN, JSON.stringify(s)); } catch (e) {} }};
    } catch (e) { return null; }
  }


  /* ---------- plans from the other simulators: transit, budget, pensions ----------
     The server keeps the plan code and a few numbers the simulator worked out when the plan was shared (P.stats), so a
     card never has to run a model. Names come from NAMES, like housing plans. */
  const money = v => { const a = Math.abs(v); return (v < 0 ? "−" : "") + "$" + (a >= 1e9 ? (a / 1e9).toFixed(a >= 1e10 ? 0 : 1) + "B" : a >= 1e6 ? Math.round(a / 1e6) + "M" : a >= 1e3 ? Math.round(a / 1e3) + "K" : Math.round(a)); };
  const mm = v => money(v * 1e6);                      // budget figures are in $ millions
  const plural = (n, one, many) => n + " " + (n === 1 ? one : many || one + "s");
  const METRA = {BNSF:"BNSF", HC:"Heritage Corridor", "MD-N":"Milwaukee North", "MD-W":"Milwaukee West", ME:"Metra Electric", NCS:"North Central", RI:"Rock Island", SWS:"SouthWest Service", "UP-N":"UP North", "UP-NW":"UP Northwest", "UP-W":"UP West"};
  const TMODE = {s:["Subway line", "Subway lines"], e:["Elevated line", "Elevated lines"], st:["Streetcar line", "Streetcar lines"], b:["Bus rapid transit line", "Bus rapid transit lines"], i:["New L station", "New L stations"], l:["Bus lane", "Bus lanes"]};
  const TCOL = ["#2b5da0", "#2b5da0", "#e07a3f", "#2e9d57", "#7a5ea8", "#c8102e"];   // subway, elevated, streetcar, BRT, Metra, bus lane
  // what a transit plan code holds (lines that are switched off don't count)
  function tparse(code){
    const o = {named:[], n:{}, metra:[], clean:[], fresh:false, rail:0, bus:0};
    for (const part of String(code || "").split("~")){
      if (!part || part[0] === "x") continue;
      if (/^C[01]{3}$/.test(part)){ if (part[1] === "1") o.clean.push("Electric buses"); if (part[2] === "1") o.clean.push("Electric Metra"); if (part[3] === "1") o.clean.push("Clean power grid"); continue; }
      if (part[0] === "F"){ o.fresh = true; continue; }
      if (part[0] === "M"){ const id = part.slice(1).split(".")[0]; o.metra.push((METRA[id] || id) + " all-day trains"); continue; }
      const k = part.startsWith("st") ? "st" : part[0]; if (!TMODE[k]) continue;
      if (k === "s" || k === "e" || k === "i") o.rail++; else o.bus++;
      let nm = ""; try { nm = decodeURIComponent(part.slice(part.lastIndexOf(".") + 1)); } catch (e) {}
      if (nm) o.named.push(nm); else o.n[k] = (o.n[k] || 0) + 1;
    }
    return o;
  }
  function pparse(code){
    const m = String(code || "").match(/^p2\.(\d)\.(\d+)\.(\d)\.(\d)\.(\d)\.(\d)\.(\d)$/); if (!m) return null;
    return {pay:+m[1], extra:+m[2], bond:+m[3], ret:+m[4], crash:m[5] === "1", by:+m[6], pool:+m[7]};
  }
  const SIMS = {
    transit: {
      label:"Transit", sim:"/transit/", simName:"the transit simulator", open: P => "/transit/#p=" + P.code,
      chips(P){ const t = tparse(P.code), c = [];
        t.named.forEach(n => c.push({t:n, kind:"zone"}));
        for (const k in t.n) c.push({t: t.n[k] === 1 ? TMODE[k][0] : t.n[k] + " " + TMODE[k][1].toLowerCase(), kind:"zone"});
        t.metra.forEach(n => c.push({t:n, kind:"zone"}));
        t.clean.forEach(n => c.push({t:n, kind:"policy"}));
        if (t.fresh) c.push({t:"Network redrawn from scratch", kind:"policy"});
        return c; },
      kind(P){ const t = tparse(P.code);
        if (t.fresh) return {t:"From scratch", c:"all"};
        const r = t.rail, b = t.bus, m = t.metra.length;
        if (!r && !b && !m) return {t:"Cleaner transit", c:"pol"};
        if (r && !b && !m) return {t:"Rail", c:"tod"}; if (b && !r && !m) return {t:"Buses", c:"mm"}; if (m && !r && !b) return {t:"Metra", c:"hood"};
        const has = [r && "rail", b && "bus", m && "Metra"].filter(Boolean), lbl = has.length === 3 ? "Rail, bus and Metra" : has.join(" and ");
        return {t:lbl[0].toUpperCase() + lbl.slice(1), c:"all"}; },
      sum(P){ const t = tparse(P.code), x = [];
        if (t.rail) x.push(plural(t.rail, "rail project")); if (t.bus) x.push(plural(t.bus, "bus project")); if (t.metra.length) x.push(plural(t.metra.length, "Metra upgrade"));
        if (t.clean.length) x.push("cleaner fleet"); return x.join(", ") || (t.fresh ? "A redrawn network" : "No lines yet"); },
      nums(P){ const s = P.stats || {}, o = [];
        if (s.riders != null) o.push([fmt(Math.round(s.riders)), "new transit trips a weekday"]);
        if (s.cap != null) o.push([money(s.cap), "to build"]);
        if (s.op != null) o.push([money(Math.abs(s.op)), s.op < 0 ? "saved a year to run" : "a year to run"]);
        if (s.cars != null) o.push([fmt(Math.round(s.cars)), "fewer car trips a day"]);
        return o; },
      art(P, G, big){
        if (!G || !G.b) return '<div class="pmap empty"></div>';
        const [x0, y0, x1, y1] = G.b, k = Math.cos((y0 + y1) / 2 * Math.PI / 180), S = 1000 / (y1 - y0), X = lon => (lon - x0) * k * S, Y = lat => (y1 - lat) * S;
        let h = '<svg class="' + (big ? "big" : "pmap") + '" viewBox="-10 -10 ' + (G.w + 20) + ' 1020" role="img" aria-label="Map of the plan\'s lines">';
        for (const n in G.areas) h += '<path d="' + G.areas[n] + '" fill="#e7ebef" stroke="#fff" stroke-width="3"/>';
        for (const [x, y] of G.L) h += '<circle cx="' + x + '" cy="' + y + '" r="' + (big ? 4 : 5) + '" fill="#aab2ba"/>';
        for (const L of (P.stats && P.stats.shape) || []){
          let d = ""; for (let i = 1; i + 1 < L.length; i += 2) d += (i === 1 ? "M" : "L") + X(L[i]).toFixed(0) + " " + Y(L[i + 1]).toFixed(0);
          const w = big ? 9 : 14;
          h += '<path d="' + d + '" fill="none" stroke="#fff" stroke-width="' + (w + 6) + '" stroke-linecap="round" stroke-linejoin="round"/><path d="' + d + '" fill="none" stroke="' + TCOL[L[0]] + '" stroke-width="' + w + '" stroke-linecap="round" stroke-linejoin="round"' + (L[0] === 0 ? ' stroke-dasharray="' + w * 2.2 + " " + w * 1.3 + '"' : "") + '/>';
        }
        return h + "</svg>"; },
      key: '<span><i style="background:#2b5da0"></i>Rail (subway dashed)</span><span><i style="background:#e07a3f"></i>Streetcar</span><span><i style="background:#2e9d57"></i>Bus rapid transit</span><span><i style="background:#7a5ea8"></i>Metra</span><span><i style="background:#c8102e"></i>Bus lane</span>',
    },
    budget: {
      label:"Budget", sim:"/budget/", simName:"the budget simulator", open: P => "/budget/#" + P.code,
      chips(P){ const s = P.stats || {}, c = [];
        if (s.rec > 0.05) c.push({t:"Lasting fixes " + mm(s.rec), kind:"zone"});
        if (s.one > 0.05) c.push({t:"One-time money " + mm(s.one), kind:"policy"});
        if (s.cost > 0.05) c.push({t:"Tax cuts and new spending " + mm(s.cost), kind:"more"});
        if (s.state > 0.05) c.push({t:"Needs Springfield or voters: " + mm(s.state), kind:"cut"});
        if (s.yes != null) c.push({t:"Council vote estimate " + s.yes + "–" + (50 - s.yes), kind:"more"});
        return c; },
      kind(P){ const s = P.stats || {};
        if (s.left > 0.05) return {t:"Still short", c:"cut"};
        if (s.state > 0.05) return {t:"Leans on Springfield", c:"main"};
        if (!(s.one > 0.05)) return {t:"No one-time money", c:"pol"};
        return {t:"Balanced", c:"tod"}; },
      sum(P){ const s = P.stats || {}; return s.need != null ? "Closes " + mm(Math.min(s.need, (s.rec || 0) + (s.one || 0))) + " of a " + mm(s.need) + " gap" : "A 2027 city budget"; },
      nums(P){ const s = P.stats || {}, o = [];
        if (s.left != null) o.push(s.left > 0.05 ? [mm(s.left), "still short"] : ["Balanced", "the 2027 budget"]);
        if (s.home != null) o.push([(s.home > 0 ? "+" : s.home < 0 ? "−" : "") + "$" + fmt(Math.abs(Math.round(s.home))), "a year for a typical homeowner"]);
        return o; },
      art(P, G, big){ const s = P.stats || {}, need = Math.max(1, s.need || 1), rec = Math.max(0, s.rec || 0), one = Math.max(0, s.one || 0), tot = Math.max(need, rec + one);
        const VW = big ? 600 : 320, W = VW - 40, a = W * rec / tot, b = W * one / tot, c = W * Math.max(0, need - rec - one) / tot, gx = 20 + W * need / tot;
        const seg = (x, w, fill, label, val) => w < 1 ? "" : '<rect x="' + (20 + x) + '" y="60" width="' + w + '" height="60" fill="' + fill + '"/>' + (w > 76 ? '<text x="' + (20 + x + w / 2) + '" y="86" text-anchor="middle" font-size="14" font-weight="600" fill="#fff">' + label + '</text><text x="' + (20 + x + w / 2) + '" y="106" text-anchor="middle" font-size="14" fill="#fff">' + val + '</text>' : "");
        return '<svg class="' + (big ? "big" : "pmap") + ' wide" viewBox="0 0 ' + VW + ' 170" role="img" aria-label="How the plan closes the budget gap"><text x="20" y="38" font-size="18" font-weight="600" fill="#1a1d21">' + mm(need) + ' to close</text>'
          + '<clipPath id="bc' + (big ? "b" : "") + P.id + '"><rect x="20" y="60" width="' + W + '" height="60" rx="12"/></clipPath><g clip-path="url(#bc' + (big ? "b" : "") + P.id + ')"><rect x="20" y="60" width="' + W + '" height="60" fill="#e7ebef"/>' + seg(0, a, "#2b5da0", "Lasting", mm(rec)) + seg(a, b, "#41b6e6", "One-time", mm(one)) + seg(a + b, c, "#e4002b", "Short", mm(need - rec - one)) + '</g>'
          + '<line x1="' + gx + '" x2="' + gx + '" y1="50" y2="130" stroke="#1a1d21" stroke-width="2"/><text x="' + Math.min(VW - 20, gx) + '" y="150" text-anchor="end" font-size="13" fill="#5a6069">the gap</text></svg>'; },
      key: '<span><i style="background:#2b5da0"></i>Lasting fixes</span><span><i style="background:#41b6e6"></i>One-time money</span><span><i style="background:#e4002b"></i>Still short</span>',
    },
    pensions: {
      label:"Pensions", sim:"/pensions/", simName:"the pensions simulator", open: P => "/pensions/#" + P.code,
      chips(P){ const o = pparse(P.code), c = []; if (!o) return c;
        c.push({t:["State law's payment schedule", "Pays the funds off fully", "Payments frozen at 2026"][o.pay] || "State law's payment schedule", kind:o.pay === 2 ? "cut" : "zone"});
        if (o.by) c.push({t:"90% funded by " + [0, 2050, 2045, 2040][o.by], kind:"zone"});
        if (o.extra) c.push({t:"+$" + fmt(o.extra) + "M extra a year", kind:"zone"});
        if (o.bond) c.push({t:["", "$5B", "$10B"][o.bond] + " pension bond", kind:"policy"});
        if (o.pool) c.push({t:"Pooled investing", kind:"policy"});
        if (o.ret !== 2) c.push({t:"Assumes " + ["4%", "5.5%", "", "8%"][o.ret] + " returns", kind:"more"});
        if (o.crash) c.push({t:"Tested against a 2028 crash", kind:"more"});
        return c; },
      kind(P){ const s = P.stats || {}, o = pparse(P.code) || {};
        if (s.broke) return {t:"A fund runs dry", c:"cut"};
        if (!s.y90) return {t:"Never reaches 90%", c:"cut"};
        if (o.bond) return {t:"Borrows to catch up", c:"main"};
        if (s.y90 < 2055) return {t:"Faster payoff", c:"tod"};
        return {t:"On the law's schedule", c:"pol"}; },
      sum(P){ const s = P.stats || {}; return s.broke ? "A fund runs out of money in " + s.broke : s.y90 ? "The four funds reach 90% funded in " + s.y90 : "The funds don't reach 90% by 2070"; },
      nums(P){ const s = P.stats || {}, o = [];
        o.push(s.y90 ? [String(s.y90), "90% funded"] : ["Never", "reaches 90%"]);
        if (s.cost != null) o.push([money(s.cost * 1000), "paid 2026–2060, today's dollars"]);
        if (s.cost != null && s.base != null && Math.abs(s.cost - s.base) > 5e5) o.push([money(Math.abs(s.cost - s.base) * 1000), s.cost < s.base ? "less than state law" : "more than state law"]);
        return o; },
      art(P, G, big){ const f = (P.stats && P.stats.fr) || [], n = f.length;
        if (n < 2) return '<div class="pmap empty"></div>';
        const VW = big ? 600 : 320, x0 = 24, x1 = VW - 24, X = i => x0 + i * ((x1 - x0) / (n - 1)), Y = v => 140 - Math.min(110, v) * 1.05;
        let d = "", pts = ""; f.forEach((v, i) => { d += (i ? "L" : "M") + X(i).toFixed(0) + " " + Y(v).toFixed(0); pts += '<circle cx="' + X(i).toFixed(0) + '" cy="' + Y(v).toFixed(0) + '" r="4" fill="#2b5da0"/>'; });
        return '<svg class="' + (big ? "big" : "pmap") + ' wide" viewBox="0 0 ' + VW + ' 172" role="img" aria-label="Share of what the funds owe that they hold, 2025 to ' + (2025 + (n - 1) * 5) + '">'
          + '<line x1="' + x0 + '" x2="' + x1 + '" y1="' + Y(90) + '" y2="' + Y(90) + '" stroke="#e4002b" stroke-width="2" stroke-dasharray="6 5"/><text x="' + x0 + '" y="' + (Y(90) - 8) + '" font-size="13" fill="#a0001b">90% funded</text>'
          + '<line x1="' + x0 + '" x2="' + x1 + '" y1="140" y2="140" stroke="#d5d9de" stroke-width="1.5"/><path d="' + d + 'L' + X(n - 1).toFixed(0) + ' 140L' + x0 + ' 140Z" fill="#2b5da0" opacity=".12"/><path d="' + d + '" fill="none" stroke="#2b5da0" stroke-width="3.5" stroke-linejoin="round" stroke-linecap="round"/>' + pts
          + '<text x="' + x0 + '" y="162" font-size="13" fill="#5a6069">2025: ' + f[0] + '%</text><text x="' + x1 + '" y="162" text-anchor="end" font-size="13" fill="#5a6069">' + (2025 + (n - 1) * 5) + ': ' + f[n - 1] + '%</text></svg>'; },
      key: '<span><i style="background:#2b5da0"></i>Share of what the funds owe that they hold</span>',
    },
  };
  const simName = P => P.title ? P.title : "The " + NAMES[P.nm != null && NAMES[P.nm] ? P.nm : hashN(P.kind + (P.id || P.code)) % NAMES.length] + " Plan";
  const SLS = "sc-sliked";
  const sliked = () => { try { return new Set(JSON.parse(localStorage.getItem(SLS) || "[]")); } catch (e) { return new Set(); } };
  function simEndorseBtn(P){
    const on = sliked().has(P.id);
    const b = document.createElement("button"); b.type = "button"; b.className = "pend" + (on ? " on" : ""); b.disabled = on;
    b.setAttribute("aria-label", (on ? "You endorsed this plan. " : "Endorse this plan. ") + P.likes + " endorsements");
    b.innerHTML = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M7 11v9H4v-9zM7 11l4-8c1.6 0 2.6 1.2 2.3 2.8L12.8 9H19a2 2 0 0 1 2 2.3l-1.2 6.9A2 2 0 0 1 17.8 20H7"/></svg><span>' + (on ? "Endorsed" : "Endorse") + '</span><b>' + fmt(P.likes) + '</b>';
    b.addEventListener("click", async e => { e.preventDefault(); e.stopPropagation();
      const L = sliked(); if (L.has(P.id)) return; b.disabled = true;
      try { const r = await fetch("/api/slike/" + P.id, {method:"POST", headers:{"content-type":"application/json"}, body:"{}"}); if (!r.ok) throw 0; const d = await r.json();
        L.add(P.id); try { localStorage.setItem(SLS, JSON.stringify([...L])); } catch (e2) {}
        b.classList.add("on"); b.querySelector("span").textContent = "Endorsed"; b.querySelector("b").textContent = fmt(d.likes);
      } catch (e2) { b.disabled = false; } });
    return b;
  }
  function simCard(P, G){
    const K = SIMS[P.kind]; if (!K) return null;
    const a = document.createElement("a"), kd = K.kind(P), c = K.chips(P), nums = K.nums(P);
    a.className = "pcard sim-" + P.kind; a.href = "/plans/#" + P.kind + "-" + P.id;
    a.innerHTML = '<div class="pmapw">' + K.art(P, G) + '<span class="pmode sim">' + K.label + '</span></div>'
      + '<div class="pbody"><span class="pkind k-' + kd.c + '">' + esc(kd.t) + '</span><b class="pt">' + esc(simName(P)) + '</b><span class="psum">' + esc(K.sum(P)) + '</span><span class="pwho">' + who(P, "") + '</span>'
      + '<div class="pnums">' + nums.slice(0, 2).map(n => '<span><b>' + esc(n[0]) + '</b> ' + esc(n[1]) + '</span>').join("") + '</div>'
      + '<ul class="pchips">' + c.slice(0, 5).map(x => '<li class="' + x.kind + '">' + esc(x.t) + '</li>').join("") + (c.length > 5 ? '<li class="more">+' + (c.length - 5) + ' more</li>' : "") + '</ul>'
      + '<div class="pfoot"><span class="popen">See the plan</span></div></div>';
    a.querySelector(".pfoot").prepend(simEndorseBtn(P));
    return a;
  }
  // Plans this browser shared keep a private token, so their sharer can delete them later: {"<kind>-<id>": token}
  const OWN = "sc-own";
  const owned = () => { try { return JSON.parse(localStorage.getItem(OWN) || "{}") || {}; } catch (e) { return {}; } };
  const ownTok = (kind, id) => owned()[kind + "-" + id] || null;
  function newTok(){ const a = new Uint8Array(16); crypto.getRandomValues(a); return [...a].map(x => x.toString(16).padStart(2, "0")).join(""); }
  function keepTok(kind, id, tok){ const o = owned(); o[kind + "-" + id] = tok; try { localStorage.setItem(OWN, JSON.stringify(o)); } catch (e) {} }
  function dropTok(kind, id){ const o = owned(); delete o[kind + "-" + id]; try { localStorage.setItem(OWN, JSON.stringify(o)); } catch (e) {} }

  // "Delete this plan": asks once more in place (no browser dialogs), then removes it from Plans people made
  function deleteBtn(kind, id, done){
    const w = document.createElement("span"); w.className = "pdel";
    const tok = ownTok(kind, id); if (!tok) return w;
    w.innerHTML = '<button type="button" class="pdelgo">Delete this plan</button><span class="pdelask" hidden>Delete it for good? <button type="button" class="pdelyes">Yes, delete</button><button type="button" class="pdelno">Keep it</button></span><span class="pdelmsg" role="status"></span>';
    const go = w.querySelector(".pdelgo"), ask = w.querySelector(".pdelask"), msg = w.querySelector(".pdelmsg");
    go.addEventListener("click", e => { e.preventDefault(); e.stopPropagation(); go.hidden = true; ask.hidden = false; w.querySelector(".pdelyes").focus(); });
    w.querySelector(".pdelno").addEventListener("click", e => { e.preventDefault(); e.stopPropagation(); ask.hidden = true; go.hidden = false; go.focus(); });
    w.querySelector(".pdelyes").addEventListener("click", async e => { e.preventDefault(); e.stopPropagation();
      msg.textContent = "Deleting…"; ask.hidden = true;
      try {
        const r = await fetch("/api/delete", {method:"POST", headers:{"content-type":"application/json"}, body:JSON.stringify({kind, id, tok})});
        if (r.status === 403){ dropTok(kind, id); msg.textContent = "This browser can't delete that plan."; return; }
        if (!r.ok) throw 0;
        dropTok(kind, id);
        if (kind === "housing") try { localStorage.setItem(MINE, JSON.stringify(mine().filter(n => n !== id))); } catch (e2) {}
        else try { localStorage.setItem(SMINE, JSON.stringify(JSON.parse(localStorage.getItem(SMINE) || "[]").filter(n => n !== id))); } catch (e2) {}
        msg.textContent = "Deleted. It's gone from Plans people made.";
        done && done();
      } catch (e2) { msg.textContent = "Couldn't reach the plan gallery. Try again in a bit."; ask.hidden = false; }
    });
    return w;
  }
  // "Report this name": three reports from different people hide a typed name
  function reportBtn(kind, P){
    const w = document.createElement("span"); w.className = "prep";
    if (!P.title && !P.author) return w;
    w.innerHTML = '<button type="button">Report this name</button><span role="status"></span>';
    const b = w.querySelector("button"), m = w.querySelector("span");
    b.addEventListener("click", async e => { e.preventDefault(); e.stopPropagation(); b.disabled = true;
      try { const r = await fetch("/api/report", {method:"POST", headers:{"content-type":"application/json"}, body:JSON.stringify({kind, id:P.id})}); if (!r.ok) throw 0;
        b.hidden = true; m.textContent = "Thanks. Names that several people report are hidden.";
      } catch (e2) { b.disabled = false; m.textContent = "Couldn't send that. Try again in a bit."; } });
    return w;
  }

  // The "share with neighbors" box every simulator shows: name the plan (or take a suggested one), an optional
  // "by" name, then post. kind "housing" posts get() (the housing tool's numbers) to /api/plan; the others post
  // {kind, code, stats} from get() to /api/splan. The server checks both names and says why it refused one.
  const SMINE = "sc-my-splans";
  function shareBox(host, kind, get, opt){
    opt = opt || {};
    let nm = Math.floor(Math.random() * NAMES.length);
    const sug = () => "The " + NAMES[nm] + " Plan";
    host.classList.add("pshare");
    host.innerHTML = '<label class="pshl"><span class="pshlt">Name your plan</span><input class="pshname" maxlength="60" autocomplete="off" spellcheck="true"></label>'
      + '<button type="button" class="pshalt">Suggest a name</button>'
      + '<label class="pshl"><span class="pshlt">Your name <i>(optional)</i></span><input class="pshby" maxlength="24" autocomplete="off" placeholder="A first name or nickname"></label>'
      + '<p class="pshfine">Don\'t use your full name. Names with swearing, insults, links or contact details are turned away.</p>'
      + '<button type="button" class="sc-btn primary pshgo">' + (opt.go || "Share it on Plans people made") + '</button><p class="pshmsg" role="status"></p><div class="pshafter"></div>';
    const nmIn = host.querySelector(".pshname"), byIn = host.querySelector(".pshby"), go = host.querySelector(".pshgo"), msg = host.querySelector(".pshmsg");
    nmIn.placeholder = sug(); nmIn.value = sug();
    host.querySelector(".pshalt").addEventListener("click", () => { nm = (nm + 1 + Math.floor(Math.random() * (NAMES.length - 1))) % NAMES.length; nmIn.value = sug(); nmIn.placeholder = sug(); nmIn.removeAttribute("aria-invalid"); });
    [nmIn, byIn].forEach(i => i.addEventListener("input", () => { i.removeAttribute("aria-invalid"); if (go.textContent === "Shared"){ go.textContent = opt.go || "Share it on Plans people made"; go.disabled = false; } }));
    go.addEventListener("click", async () => {
      const d = get(); if (!d || !d.code){ msg.textContent = "There's nothing to share yet. Make a change first."; return; }
      let title = nmIn.value.replace(/\s+/g, " ").trim(); const author = byIn.value.replace(/\s+/g, " ").trim();
      const listed = title === sug(); if (!title){ title = sug(); nmIn.value = title; }
      if (title.length < 3){ msg.textContent = "Give the plan a name of at least 3 characters."; nmIn.setAttribute("aria-invalid", "true"); nmIn.focus(); return; }
      if (author && author.length < 2){ msg.textContent = "Your name needs at least 2 characters, or leave it empty."; byIn.setAttribute("aria-invalid", "true"); byIn.focus(); return; }
      go.disabled = true; msg.textContent = "Sharing…";
      const tok = newTok(), names = {nm, title: listed ? "" : title, author, tok};
      const url = kind === "housing" ? "/api/plan" : "/api/splan";
      const body = kind === "housing" ? Object.assign({}, d, {gallery: 1}, names) : Object.assign({kind, code: d.code, stats: d.stats || {}}, names);
      try {
        const r = await fetch(url, {method:"POST", headers:{"content-type":"application/json"}, body:JSON.stringify(body)});
        if (r.status === 429){ msg.textContent = "That's a lot of plans for one day. Try again tomorrow."; go.disabled = false; return; }
        if (r.status === 400){ const j = await r.json().catch(() => ({}));
          if (j.error === "name"){ const el = j.field === "author" ? byIn : nmIn; el.setAttribute("aria-invalid", "true"); el.focus(); msg.textContent = j.why || "Try another name."; go.disabled = false; return; }
          throw 0; }
        if (!r.ok) throw 0; const j = await r.json();
        keepTok(kind, j.id, tok);
        const KEY = kind === "housing" ? MINE : SMINE;
        try { const ids = JSON.parse(localStorage.getItem(KEY) || "[]"); if (!ids.includes(j.id)) ids.push(j.id); localStorage.setItem(KEY, JSON.stringify(ids.slice(-40))); } catch (e) {}
        const href = "/plans/#" + (kind === "housing" ? "" : kind + "-") + j.id;
        msg.innerHTML = 'Shared as <b>' + esc(title) + '</b>' + (author ? ' by ' + esc(author) : "") + '. <a href="' + href + '">See it in Neighbors\' plans</a>';
        go.textContent = "Shared";
        const after = host.querySelector(".pshafter"); after.innerHTML = "";
        after.append(deleteBtn(kind, j.id, () => { go.textContent = opt.go || "Share it on Plans people made"; go.disabled = false; msg.textContent = ""; after.innerHTML = ""; }));
        opt.done && opt.done(j.id);
      } catch (e) { msg.textContent = "Couldn't reach the plan gallery. Try again in a bit."; go.disabled = false; }
    });
  }

  window.SCPlans = {decode, choices, title, kind, nameOf, NAMES, hashN, map, card, geo, endorseBtn, myNews, mine, AREAS, MODE, fmt, esc, ago, STAR,
    SIMS, simCard, simName, simEndorseBtn, shareBox, deleteBtn, reportBtn, ownTok, owned, tparse, pparse, money, BIT_KEYS, SHORT, CUT, TIER, COLOR, TCOL, METRA};

})();
