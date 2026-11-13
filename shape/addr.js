/* Shape Chicago address search, shared by the grants finder and the deal check (the lot tool has its own copy).
   Uses the lot tool's address index (lot/data/streets.json, lot/data/a/<shard>.json) and its 0.01° tiles (lot/data/t),
   built by tools/prep_lots.py. Everything happens in the browser; nothing typed is sent anywhere.

   SCAddr.attach(input, list, onPick)  wires a text box and an empty element for suggestions.
   onPick(P) gets {lon, lat, label, ward, land, zone, cls, apts, year, bldgSqft, stories, tile, k}.
   SCAddr.rules(lon, lat) -> overlays at the point from lot/data/r (tools/lot/prep_rules.py): {kind: [[name, detail], …]}. */
(function(){
  const BASE = "/lot/data/";
  const ABBR = {AVENUE:"AVE", AV:"AVE", STREET:"ST", BOULEVARD:"BLVD", ROAD:"RD", PLACE:"PL", DRIVE:"DR", COURT:"CT", PARKWAY:"PKWY", TERRACE:"TER", LANE:"LN", HIGHWAY:"HWY",
    SQUARE:"SQ", NORTH:"N", SOUTH:"S", EAST:"E", WEST:"W", SAINT:"ST", CIRCLE:"CIR", PLAZA:"PLZ", EXPRESSWAY:"EXPY", WAY:"WAY"};
  const norm = s => s.toUpperCase().replace(/[.,#]/g, " ").replace(/\b(\d+)(ST|ND|RD|TH)\b/g, "$1").replace(/\s+/g, " ").trim().split(" ").map(w => ABBR[w] || w).join(" ");
  const title = s => (s || "").toLowerCase().replace(/\b([a-z])/g, c => c.toUpperCase()).replace(/\b(N|S|E|W)\b/gi, c => c.toUpperCase()).replace(/\b(\d+)(St|Nd|Rd|Th)\b/g, (m, a, b) => a + b.toLowerCase());
  const esc = s => String(s).replace(/[&<>"]/g, c => ({"&":"&amp;", "<":"&lt;", ">":"&gt;", '"':"&quot;"}[c]));
  let STREETS = null; const SH = new Map(), TILES = new Map(), RT = new Map();
  const tkey = (lon, lat) => [Math.floor((lon + 88) * 100), Math.floor((lat - 41) * 100)];
  const corner = (ix, iy) => [ix / 100 - 88, iy / 100 + 41];
  function streets(){
    if (!STREETS) STREETS = fetch(BASE + "streets.json").then(r => r.ok ? r.json() : []).catch(() => []).then(L => L.map(([s, c]) => ({s, c, n:s.replace(/\b(\d+)(ST|ND|RD|TH)\b/g, "$1")})));
    return STREETS;
  }
  function tile(ix, iy){
    const k = ix + "_" + iy;
    if (!TILES.has(k)) TILES.set(k, fetch(BASE + "t/" + k + ".json").then(r => r.ok ? r.json() : null).catch(() => null).then(T => { if (T){ T.ix = ix; T.iy = iy; } return T; }));
    return TILES.get(k);
  }
  function parcel(T, k, label){
    const p = T.p[k], [x0, y0] = corner(T.ix, T.iy);
    const [, x, y, cls, land, apts, year, bsf, bi, zi, ward, , addr] = p;
    const B = bi != null && bi >= 0 ? T.b[bi] : null;
    return {lon: x0 + x / 1e6, lat: y0 + y / 1e6, label: label || title(addr || ""), ward: ward || null, land: land || 0, zone: zi != null && zi >= 0 ? T.zn[zi] : null,
      cls: cls || "", apts: apts || 0, year: year || 0, bldgSqft: bsf || 0, stories: B ? (B[1] || 0) : 0, tile: T, k};
  }
  async function go(num, street, onPick, hint){
    const sh = (street.replace(/^[NSEW] /, "").replace(/[^A-Z0-9]/g, "").slice(0, 2)) || "_";
    if (!SH.has(sh)) SH.set(sh, fetch(BASE + "a/" + sh + ".json").then(r => r.ok ? r.json() : {}).catch(() => ({})));
    const L = (await SH.get(sh))[street];
    if (!L || !L.length){ hint && hint("Couldn't find that street."); return; }
    let best = L[0];
    if (num != null){ let bd = 1e9; for (const r of L){ const d = Math.abs(r[0] - num) + ((r[0] - num) % 2 ? 0.5 : 0); if (d < bd){ bd = d; best = r; } } }
    const T = await tile(best[1], best[2]);
    if (!T){ hint && hint("Couldn't load that address."); return; }
    const label = title((num != null ? best[0] + " " : "") + street);
    hint && hint(num != null && best[0] !== num ? `No record for ${num}; using ${best[0]}, the closest number on that street.` : "");
    onPick(parcel(T, best[3], label));
  }
  function attach(input, list, onPick, hint){
    let tm = 0;
    async function suggest(){
      const q = norm(input.value), m = q.match(/^(\d+)\s+(.+)$/);
      const words = (m ? m[2] : q).split(" ").filter(Boolean);
      if (!words.length || q.length < 2){ list.hidden = true; input.setAttribute("aria-expanded", "false"); return; }
      const L = await streets(), scored = [];
      for (const st of L){
        const parts = st.n.split(" "); let ok = true, sc = 0;
        for (const w of words){ const i = parts.findIndex(p => p.startsWith(w)); if (i < 0){ ok = false; break; } sc += parts[i] === w ? 2 : 1; }
        if (ok) scored.push([sc + Math.log10(st.c + 1) - st.n.length / 100, st.s]);
      }
      scored.sort((a, b) => b[0] - a[0]);
      const top = scored.slice(0, 6).map(x => x[1]);
      list.innerHTML = top.map((s, i) => `<button type="button" role="option" data-s="${esc(s)}" aria-selected="${i === 0}">${m ? m[1] + " " : ""}${esc(title(s))}</button>`).join("");
      list.hidden = !top.length; input.setAttribute("aria-expanded", String(!!top.length));
      list.querySelectorAll("button").forEach(b => b.onclick = () => { list.hidden = true; go(m ? +m[1] : null, b.dataset.s, onPick, hint); });
    }
    input.setAttribute("role", "combobox"); input.setAttribute("aria-autocomplete", "list"); input.setAttribute("aria-expanded", "false"); if (!input.getAttribute("aria-label") && !(input.labels && input.labels.length)) input.setAttribute("aria-label", "Chicago address"); list.setAttribute("role", "listbox"); list.hidden = true;
    input.addEventListener("input", () => { clearTimeout(tm); tm = setTimeout(suggest, 120); });
    input.addEventListener("focus", streets, {once:true});
    input.addEventListener("keydown", async e => {
      const bs = [...list.querySelectorAll("button")], i = bs.findIndex(b => b.getAttribute("aria-selected") === "true");
      if ((e.key === "ArrowDown" || e.key === "ArrowUp") && bs.length){ e.preventDefault(); const j = (i + (e.key === "ArrowDown" ? 1 : -1) + bs.length) % bs.length; bs.forEach((b, k) => b.setAttribute("aria-selected", k === j)); }
      if (e.key === "Enter"){
        e.preventDefault();
        if (!bs.length) await suggest();
        const b = list.querySelector('[aria-selected="true"]'), m = norm(input.value).match(/^(\d+)\s+(.+)$/);
        if (b){ list.hidden = true; go(m ? +m[1] : null, b.dataset.s, onPick, hint); }
      }
      if (e.key === "Escape") list.hidden = true;
    });
    document.addEventListener("click", e => { if (!list.contains(e.target) && e.target !== input) list.hidden = true; });
    return {pickText: async () => { await suggest(); const b = list.querySelector('[aria-selected="true"]'), m = norm(input.value).match(/^(\d+)\s+(.+)$/); if (b){ list.hidden = true; await go(m ? +m[1] : null, b.dataset.s, onPick, hint); } }};
  }
  function inRing(px, py, a){ let c = false; for (let i = 0, j = a.length - 2; i < a.length; j = i, i += 2){ const xi = a[i], yi = a[i + 1], xj = a[j], yj = a[j + 1]; if ((yi > py) !== (yj > py) && px < (xj - xi) * (py - yi) / (yj - yi) + xi) c = !c; } return c; }
  async function rules(lon, lat){
    const [ix, iy] = tkey(lon, lat), k = ix + "_" + iy;
    if (!RT.has(k)) RT.set(k, fetch(BASE + "r/" + k + ".json").then(r => r.ok ? r.json() : {f:[]}).catch(() => ({f:[]})));
    const R = await RT.get(k), x0 = ix / 100 - 88, y0 = iy / 100 + 41, px = (lon - x0) * 1e6, py = (lat - y0) * 1e6, F = {};
    for (const [kind, n, d, rings] of (R.f || [])){
      let c = false; for (const r of rings) if (inRing(px, py, r)) c = !c;
      if (c) (F[kind] = F[kind] || []).push([n, d]);
    }
    return F;
  }
  window.SCAddr = {attach, rules, title, esc, tkey};
})();
