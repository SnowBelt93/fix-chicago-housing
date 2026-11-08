/* Shape Chicago: plan cards for housing plans people posted (home page and /plans/).
   Reads a plan code (the same format as housing/index.html encodePlan/decodePlan) and draws a small map of what it rezones,
   the main choices as chips, the numbers, and an Endorse button. Nothing people type is shown: titles come from the plan itself.
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
  // Plan names: the person who shares a plan picks one from this list (Chicago streets and Chicago-isms), so names are
  // memorable and nobody types anything. Index stored as `nm`; plans shared before names existed get one from their id.
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
  const nameOf = P => "The " + NAMES[P.nm != null && NAMES[P.nm] ? P.nm : hashN("p" + (P.id || P.code)) % NAMES.length] + " Plan";
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
      + '<div class="pbody"><span class="pkind k-' + K.c + '">' + K.t + '</span><b class="pt">' + esc(nameOf(P)) + '</b><span class="psum">' + esc(title(p)) + '</span><span class="pwho">' + (P.hood && AREAS[P.hood] ? "From " + esc(AREAS[P.hood]) : "From a neighbor") + ' · ' + ago(P.ts) + '</span>'
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

  window.SCPlans = {decode, choices, title, kind, nameOf, NAMES, hashN, map, card, geo, endorseBtn, myNews, mine, AREAS, MODE, fmt, esc, ago, STAR};
})();
