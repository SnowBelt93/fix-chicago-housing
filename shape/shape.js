/* Shape Chicago shared behavior: smooth open/close for every <details> section (incl. ones added later).
   Skipped under prefers-reduced-motion. */
(function(){
  const reduce = matchMedia("(prefers-reduced-motion: reduce)");
  const EASE = "cubic-bezier(.2,.8,.2,1)", DUR = 260;
  function toggle(d){
    const sum = d.querySelector(":scope > summary");
    if (d._scAnim){ const old = d._scAnim; d._scAnim = null; old.cancel(); d.style.overflow = ""; }
    const start = d.getBoundingClientRect().height;
    d.style.overflow = "hidden";
    const opening = !d.open;
    if (opening) d.open = true;
    const end = opening ? d.getBoundingClientRect().height : sum.getBoundingClientRect().height;
    const a = d.animate({height:[start + "px", end + "px"]}, {duration:DUR, easing:EASE});
    d._scAnim = a;
    if (opening){ const kids = [...d.children].filter(k => k !== sum); kids.forEach(k => k.animate({opacity:[0, 1], transform:["translateY(-4px)", "none"]}, {duration:DUR, easing:EASE})); }
    // finish on a timer as well as onfinish: a busy page (the 3D map) can hold animation frames back
    clearTimeout(d._scT);
    const finish = () => { if (d._scAnim !== a) return; clearTimeout(d._scT); if (!opening) d.open = false; d.style.overflow = ""; d._scAnim = null; a.cancel(); };
    a.onfinish = finish; d._scT = setTimeout(finish, DUR + 60);
  }
  function wire(d){
    if (d._scWired) return; d._scWired = true;
    const sum = d.querySelector(":scope > summary"); if (!sum) return;
    sum.addEventListener("click", e => {
      if (reduce.matches || !d.animate) return;
      if (e.target !== sum && e.target.closest("a, input, select, button")) return;   // controls inside the summary keep their own click
      e.preventDefault(); toggle(d);
    });
  }
  const scan = () => document.querySelectorAll("details").forEach(wire);
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", scan); else scan();
  new MutationObserver(scan).observe(document.documentElement, {childList:true, subtree:true});
})();

/* Closing animates too: every <dialog> fades and drops slightly before it closes (Close buttons, backdrop taps, Escape),
   and scOut(el, then) does the same for floating cards that close by setting `hidden`. */
(function(){
  const reduce = matchMedia("(prefers-reduced-motion: reduce)");
  const OUT = [{opacity:1, transform:"none"}, {opacity:0, transform:"translateY(10px) scale(.97)"}];
  const close0 = HTMLDialogElement.prototype.close;
  HTMLDialogElement.prototype.close = function(rv){
    if (!this.open || reduce.matches || !this.animate || this._scClosing) return close0.apply(this, arguments);
    this._scClosing = true;
    const a = this.animate(OUT, {duration:170, easing:"cubic-bezier(.4,0,1,1)", fill:"forwards"});
    const done = () => { if (!this._scClosing) return; this._scClosing = false; close0.call(this, rv); a.cancel(); };
    a.finished.then(done, done); setTimeout(done, 400);
  };
  document.addEventListener("cancel", e => {
    const d = e.target; if (!(d instanceof HTMLDialogElement) || reduce.matches) return;
    e.preventDefault(); d.close();
  }, true);
  window.scOut = function(el, then){
    const fin = () => { if (then) then(); };
    if (!el || el.hidden || reduce.matches || !el.animate) return fin();
    const a = el.animate(OUT, {duration:170, easing:"cubic-bezier(.4,0,1,1)", fill:"forwards"});
    let ran = false; const done = () => { if (ran) return; ran = true; fin(); requestAnimationFrame(() => a.cancel()); };
    a.finished.then(done, done); setTimeout(done, 400);
  };
})();

/* Keep the big map data on the device so return visits open fast (see /sw.js). */
if ("serviceWorker" in navigator && location.protocol === "https:" && !/claude|anthropic|usercontent/.test(location.hostname)){
  addEventListener("load", () => { navigator.serviceWorker.register("/sw.js").catch(() => {}); });
}
/* Header menus (Simulators, Progress): each button opens a list under it (fixed, so the scrolling tab bar can't clip it) */
(function(){
  function f(){
    const groups = [...document.querySelectorAll(".sc-sims")].map(g => ({b: g.querySelector(".sc-simbtn"), m: g.querySelector(".sc-simmenu")})).filter(g => g.b && g.m);
    if (!groups.length) return;
    const place = g => { const r = g.b.getBoundingClientRect(); g.m.style.top = (r.bottom + 6) + "px"; g.m.style.left = Math.max(8, Math.min(r.left, innerWidth - g.m.offsetWidth - 8)) + "px"; };
    const open = (g, on) => { if (on) groups.forEach(o => { if (o !== g && !o.m.hidden){ o.m.hidden = true; o.b.setAttribute("aria-expanded", false); } });
      g.m.hidden = !on; g.b.setAttribute("aria-expanded", on); if (on){ place(g); const a = g.m.querySelector('[aria-current="page"]') || g.m.querySelector("a"); a && a.focus({preventScroll:true}); } };
    for (const g of groups){
      g.b.addEventListener("click", e => { e.stopPropagation(); open(g, g.m.hidden); });
      g.m.addEventListener("keydown", e => { const L = [...g.m.querySelectorAll("a")], i = L.indexOf(document.activeElement);
        if (e.key === "ArrowDown"){ e.preventDefault(); L[(i + 1) % L.length].focus(); } if (e.key === "ArrowUp"){ e.preventDefault(); L[(i - 1 + L.length) % L.length].focus(); } });
    }
    document.addEventListener("click", e => groups.forEach(g => { if (!g.m.hidden && !g.m.contains(e.target)) open(g, false); }));
    document.addEventListener("keydown", e => { if (e.key === "Escape") groups.forEach(g => { if (!g.m.hidden){ open(g, false); g.b.focus(); } }); });
    const again = () => groups.forEach(g => { if (!g.m.hidden) place(g); });
    addEventListener("resize", again);
    const n = document.querySelector(".sc-nav"); n && n.addEventListener("scroll", again, {passive:true});
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", f); else f(); })();
/* Phones: one Menu button instead of the tab bar. The sheet is built from the same nav markup (tools/site/nav.py). */
(function(){
  function f(){
    const nav = document.querySelector(".sc-head .sc-nav"), head = document.querySelector(".sc-head"); if (!nav || !head || head.querySelector(".sc-menubtn")) return;
    const btn = document.createElement("button"); btn.type = "button"; btn.className = "sc-menubtn"; btn.setAttribute("aria-haspopup", "dialog");
    btn.innerHTML = '<svg viewBox="0 0 20 14" aria-hidden="true"><path d="M1 1h18M1 7h18M1 13h18"/></svg><span>Menu</span>';
    (head.querySelector(".sc-r") || head).appendChild(btn);
    const dlg = document.createElement("dialog"); dlg.className = "sc-menu"; dlg.setAttribute("aria-label", "Pages");
    let html = '<div class="sc-menu-top"><b>Shape Chicago</b><button type="button" class="sc-btn" data-close>Close</button></div>';
    nav.querySelectorAll(".sc-sims").forEach(g => {
      const t = g.querySelector(".sc-simhd"); html += '<h2>' + (t ? t.textContent : "") + '</h2><div class="sc-menu-g">';
      g.querySelectorAll(".sc-simmenu a").forEach(a => { html += '<a href="' + a.getAttribute("href") + '"' + (a.classList.contains("sc-simalt") ? ' class="alt"' : "") + (a.getAttribute("aria-current") ? ' aria-current="page"' : "") + '>' + a.textContent + '</a>'; });
      html += '</div>'; });
    html += '<div class="sc-menu-g sc-menu-more">'; nav.querySelectorAll(":scope > a").forEach(a => { html += '<a href="' + a.getAttribute("href") + '"' + (a.getAttribute("aria-current") ? ' aria-current="page"' : "") + '>' + a.textContent + '</a>'; }); html += '</div>';
    // language and feedback live here on phones, so the header keeps the name and one Menu button
    const LN = [["en", "English"], ["es", "Español"], ["zh", "中文"], ["pl", "Polski"]], cur = window.scLang || "en";
    html += '<div class="sc-menu-foot"><div class="sc-menu-lang" role="group" aria-label="Language">' + LN.map(([k, n]) => '<button type="button" translate="no" data-lang="' + k + '"' + (k === cur ? ' aria-pressed="true"' : ' aria-pressed="false"') + '>' + n + '</button>').join("") + '</div><button type="button" class="sc-btn sc-menu-fb">Send feedback</button></div>';
    dlg.innerHTML = html; document.body.appendChild(dlg);
    btn.addEventListener("click", () => { dlg.showModal(); const c = dlg.querySelector('[aria-current="page"]'); c && c.scrollIntoView({block:"center"}); });
    dlg.addEventListener("click", e => { if (e.target === dlg || e.target.closest("[data-close]")) dlg.close();
      const l = e.target.closest("[data-lang]"); if (l && l.dataset.lang !== (window.scLang || "en") && window.scSetLang) window.scSetLang(l.dataset.lang);
      if (e.target.closest(".sc-menu-fb") && window.scFeedback){ dlg.close(); window.scFeedback(); } });
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", f); else f(); })();
/* keep the current page's tab visible when the tab bar scrolls (phones) */
(function(){
  function edges(){ const n = document.querySelector(".sc-nav"); if (!n) return; const over = n.scrollWidth > n.clientWidth + 2;
    n.classList.toggle("more-r", over && n.scrollLeft + n.clientWidth < n.scrollWidth - 4); n.classList.toggle("more-l", over && n.scrollLeft > 4); }
  function f(){ const n = document.querySelector(".sc-nav"), a = n && n.querySelector('[aria-current="page"]'); if (!n) return;
    n.addEventListener("scroll", edges, {passive:true}); addEventListener("resize", edges);
    // only scroll when the current tab would be cut off, and then just enough to show it (so "Simulators" stays in view when it can)
    if (a && n.scrollWidth > n.clientWidth){ const L = a.offsetLeft - n.offsetLeft, R = L + a.offsetWidth; if (R > n.clientWidth - 8) n.scrollLeft = R - n.clientWidth + 16; } edges(); }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", f); else f(); })();

/* Support and local sponsors. Settings live in /shape/site.json (no code change needed to switch them on):
   - [data-support] elements become a "Chip in" button once support.url is set (else they link to /support/).
   - [data-ad="<slot>"] elements show one local sponsor for that slot (rotating by day), or a small
     "Your Chicago business here" card when ads.showHouse is true. No ad scripts, no tracking, no cookies:
     a sponsor is a plain link with rel="sponsored". */
(function(){
  let site = null, loading = null;
  const load = () => loading || (loading = fetch("/shape/site.json", {cache:"no-cache"}).then(r => r.ok ? r.json() : {}).catch(() => ({})).then(s => site = s || {}));
  const esc = s => String(s || "").replace(/[&<>"]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
  function adFor(slot){
    const ads = (site && site.ads) || {}, today = new Date().toISOString().slice(0, 10);
    const list = (ads.sponsors || []).filter(a => a.on !== false && (a.slots || []).includes(slot) && (!a.until || a.until >= today));
    if (list.length){ const day = Math.floor(Date.now() / 864e5); return list[day % list.length]; }
    return ads.showHouse ? "house" : null;
  }
  function render(){
    document.querySelectorAll("[data-ad]:not([data-ad-done])").forEach(el => {
      el.dataset.adDone = 1;
      const a = adFor(el.dataset.ad); if (!a){ el.remove(); return; }
      el.classList.add("sc-ad");
      if (a === "house"){
        el.innerHTML = `<span class="sc-ad-l">Local sponsor</span><a class="sc-ad-b" href="/advertise/"><img src="/shape/art/ad-house.webp" alt="" width="96" height="64" loading="lazy" onerror="this.remove()"><span><b>Your Chicago business here</b><span>One small card, seen by people who care where this city is headed. Chicago businesses only.</span></span></a>`;
      } else {
        el.innerHTML = `<span class="sc-ad-l">Local sponsor</span><a class="sc-ad-b" href="${esc(a.url)}" target="_blank" rel="sponsored noopener">${a.logo ? `<img src="${esc(a.logo)}" alt="" width="96" height="64" loading="lazy">` : ""}<span><b>${esc(a.name)}</b><span>${esc(a.line)}</span></span></a>`;
      }
    });
    document.querySelectorAll("[data-support]:not([data-support-done])").forEach(el => {
      el.dataset.supportDone = 1;
      const s = (site && site.support) || {}, ext = !!s.url;
      if (!ext && location.pathname.startsWith("/support")){ el.remove(); return; }
      el.innerHTML = `<a class="sc-btn sc-support" href="${ext ? esc(s.url) : "/support/"}"${ext ? ' target="_blank" rel="noopener"' : ""}><svg viewBox="0 0 24 24" aria-hidden="true"><path fill="currentColor" d="M12 21s-7.5-4.6-9.6-9.2C.9 8.4 3 4.5 6.7 4.5c2.1 0 3.6 1.1 5.3 3 1.7-1.9 3.2-3 5.3-3 3.7 0 5.8 3.9 4.3 7.3C19.5 16.4 12 21 12 21z"/></svg>${esc(s.label || "Chip in")}</a>`;
    });
  }
  window.scShowAds = () => load().then(render);
  const FOOT = [["Simulators", [["/housing/","Housing"],["/transit/","Transit"],["/budget/","Budget"],["/pensions/","Pensions"],["/bears/","Bears stadium"],["/plans/","Plans people made"]]],
    ["Your address", [["/lot/","Zoning and rules"],["/grants/","Grants and help"],["/deal/","Affordable deal check"]]],
    ["Follow along", [["/progress/","Progress"],["/wards/","Your ward"],["/news/","News"],["/learn/","Learn"]]],
    ["About", [["/about/","About this site"],["/press/","For reporters"],["/support/","Support"],["/privacy/","Privacy"],["/terms/","Terms"]]]];
  function footer(){
    /* the shared footer: <footer class="sc-foot" data-sc-foot>Not affiliated…</footer> keeps its line and gets the brand,
       four columns of page links, and a bottom row (feedback, languages, support) that later scripts fill (.sc-fextra) */
    document.querySelectorAll("footer[data-sc-foot]").forEach(el => {
      const line = el.textContent.trim() || "Not affiliated with the City of Chicago.";
      el.innerHTML = `<div class="sc-foot-in"><div class="sc-fbrand"><a class="sc-brand" href="/"><svg viewBox="0 0 24 24" aria-hidden="true"><path fill="#e4002b" d="M12 1 L14.4 7.84 L21.53 6.5 L16.8 12 L21.53 17.5 L14.4 16.16 L12 23 L9.6 16.16 L2.47 17.5 L7.2 12 L2.47 6.5 L9.6 7.84 Z"/></svg><span>Shape Chicago</span></a><p>${esc(line)}</p></div><nav aria-label="All pages">${FOOT.map(([h, L]) => `<div class="sc-fcol"><h2>${esc(h)}</h2>${L.map(([u, t]) => `<a href="${u}">${esc(t)}</a>`).join("")}</div>`).join("")}</nav><div class="sc-fextra"></div></div>`;
      el.removeAttribute("data-sc-foot");
    });
    const f = document.querySelector("footer");
    if (f && !f.querySelector('a[href="/support/"]') && !f.querySelector(".sc-foot-extra, .sc-fextra")){
      const p = document.createElement("p"); p.className = "sc-foot-extra";
      p.innerHTML = `<span data-support></span>`;
      (f.querySelector(".wrap, .fw") || f).appendChild(p);
    }
    if (document.querySelector("[data-ad], [data-support]")) window.scShowAds();
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", footer); else footer();
})();

/* A short first-visit intro for each tool: scIntro("budget", {title, body, art, go}) shows once per browser
   (localStorage sc-intro-<key>); scIntro(key, opts, true) shows it again (e.g. from an "About" link). */
window.scIntro = function(key, o, force){
  let seen = false; try { seen = localStorage.getItem("sc-intro-" + key) === "1"; } catch (e){}
  if (seen && !force) return;
  const d = document.createElement("dialog"); d.className = "sc-info sc-intro";
  d.innerHTML = `${o.art ? `<div class="sc-intro-art"><img src="${o.art}" alt=""></div>` : ""}<div class="sc-ibody"><h2>${o.title}</h2>${o.body}<div class="sc-intro-go"><button class="sc-btn primary" type="button">${o.go || "Let's go"}</button></div></div>`;
  document.body.appendChild(d);
  const done = () => { try { localStorage.setItem("sc-intro-" + key, "1"); } catch (e){} d.close(); };
  d.querySelector(".sc-intro-go button").onclick = done;
  d.addEventListener("close", () => { try { localStorage.setItem("sc-intro-" + key, "1"); } catch (e){} setTimeout(() => d.remove(), 300); });
  d.addEventListener("click", e => { if (e.target === d) done(); });
  const show = () => { try { d.showModal(); } catch (e){ d.setAttribute("open", ""); } };
  if (document.readyState === "complete") setTimeout(show, 250); else addEventListener("load", () => setTimeout(show, 250));
};

// Keyboard camera for every map page (same keys as the housing and transit tools): hold WASD or the arrows to glide,
// Q/E to spin, R/F to tilt, +/- to zoom. Not while typing, in the Simulators menu or with a pop-up open.
// cam = {get() -> {lng, lat, zoom, bearing, pitch, minZoom, maxZoom}, set(view), size() -> [w, h]}; scKeyCam.maplibre(map) makes one.
window.scKeyCam = function(cam){
  const KEYS = new Set(); let raf = 0, last = 0;
  const MAP = {w:"up", arrowup:"up", s:"down", arrowdown:"down", a:"left", arrowleft:"left", d:"right", arrowright:"right", q:"spinL", e:"spinR", r:"tiltU", f:"tiltD", "+":"zoomIn", "=":"zoomIn", "-":"zoomOut", "_":"zoomOut"};
  const loop = now => {
    const dt = Math.max(0, Math.min(0.05, (now - (last || now)) / 1000)); last = now;
    if (!KEYS.size){ raf = 0; last = 0; return; }
    const v = cam.get(), [w, h] = cam.size();
    let dx = 0, dy = 0; if (KEYS.has("left")) dx -= 1; if (KEYS.has("right")) dx += 1; if (KEYS.has("up")) dy -= 1; if (KEYS.has("down")) dy += 1;
    if (dx || dy){ const px = Math.min(w, h) * 0.9 * dt, mpp = 40075016 * Math.cos(v.lat * Math.PI / 180) / (512 * 2 ** v.zoom), b = v.bearing * Math.PI / 180;
      const east = (dx * Math.cos(b) - dy * Math.sin(b)) * px * mpp, north = (-dx * Math.sin(b) - dy * Math.cos(b)) * px * mpp;
      v.lng += east / (111320 * Math.cos(v.lat * Math.PI / 180)); v.lat += north / 110574; }
    if (KEYS.has("spinL")) v.bearing -= 60 * dt;
    if (KEYS.has("spinR")) v.bearing += 60 * dt;
    if (KEYS.has("tiltU")) v.pitch = Math.min(60, v.pitch + 40 * dt);
    if (KEYS.has("tiltD")) v.pitch = Math.max(0, v.pitch - 40 * dt);
    if (KEYS.has("zoomIn")) v.zoom = Math.min(v.maxZoom == null ? 20 : v.maxZoom, v.zoom + 1.2 * dt);
    if (KEYS.has("zoomOut")) v.zoom = Math.max(v.minZoom == null ? 0 : v.minZoom, v.zoom - 1.2 * dt);
    cam.set(v); raf = requestAnimationFrame(loop);
  };
  addEventListener("keydown", e => {
    if (e.metaKey || e.ctrlKey || e.altKey) return;
    const t = e.target, tag = (t.tagName || "").toLowerCase();
    if (tag === "input" || tag === "textarea" || tag === "select" || t.isContentEditable || document.querySelector("dialog[open]") || (t.closest && t.closest(".sc-simmenu"))) return;
    const a = MAP[(e.key || "").toLowerCase()]; if (!a) return;
    e.preventDefault(); KEYS.add(a); if (!raf) raf = requestAnimationFrame(loop);
  });
  addEventListener("keyup", e => { const a = MAP[(e.key || "").toLowerCase()]; if (a) KEYS.delete(a); });
  addEventListener("blur", () => KEYS.clear());
};
window.scKeyCam.maplibre = (map, flat) => { if (map.keyboard) map.keyboard.disable();   // flat: a top-down map (no spin or tilt)
  return {get:() => { const c = map.getCenter(); return {lng:c.lng, lat:c.lat, zoom:map.getZoom(), bearing:map.getBearing(), pitch:map.getPitch(), minZoom:map.getMinZoom(), maxZoom:map.getMaxZoom()}; },
    set:v => map.jumpTo(flat ? {center:[v.lng, v.lat], zoom:v.zoom} : {center:[v.lng, v.lat], zoom:v.zoom, bearing:v.bearing, pitch:v.pitch}),
    size:() => { const c = map.getCanvas(); return [c.clientWidth, c.clientHeight]; }}; };
// call once a page's map exists: works whether or not this file has loaded yet
window.scWhenReady = fn => { if (document.readyState === "loading") addEventListener("DOMContentLoaded", fn); else fn(); };

/* Feedback: a button in every header (and a link in every footer) opens one short form. The note is stored privately
   by the Worker (POST /api/feedback) with the page it came from; nothing typed is ever shown on the site. */
(function(){
  const ICON = '<svg viewBox="0 0 20 20" aria-hidden="true" width="17" height="17"><path d="M3.5 4.5h13a1 1 0 0 1 1 1v8a1 1 0 0 1-1 1H9l-4 3v-3H3.5a1 1 0 0 1-1-1v-8a1 1 0 0 1 1-1z" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round"/></svg>';
  let dlg;
  window.scFeedback = function(){
    if (!dlg){
      dlg = document.createElement("dialog"); dlg.className = "sc-info sc-fb";
      dlg.innerHTML = `<form class="sc-ibody" method="dialog"><button type="button" class="sc-btn sc-x" data-x>Close</button><h2>Send feedback</h2>
        <p>Something wrong, confusing or missing? Say what you'd change.</p>
        <label class="sc-fbl" for="scFbT">Your note</label><textarea id="scFbT" rows="5" maxlength="2000" placeholder="For example: the rent number on the housing page doesn't match the Sources tab."></textarea>
        <p class="sc-fbn">Notes are anonymous, so we can't reply. Please leave out names and contact details.</p>
        <p class="sc-fbm" role="status" aria-live="polite"></p>
        <div class="sc-fbr"><button type="submit" class="sc-btn sc-fbsend">Send</button></div></form>`;
      document.body.appendChild(dlg);
      const t = dlg.querySelector("textarea"), msg = dlg.querySelector(".sc-fbm"), send = dlg.querySelector(".sc-fbsend");
      dlg.querySelector("[data-x]").onclick = () => dlg.close();
      dlg.addEventListener("click", e => { if (e.target === dlg) dlg.close(); });
      dlg.querySelector("form").addEventListener("submit", async e => {
        e.preventDefault(); const text = t.value.trim();
        if (text.length < 3){ msg.textContent = "Write a few words first."; t.focus(); return; }
        send.disabled = true; msg.textContent = "Sending…";
        try {
          const r = await fetch("/api/feedback", {method:"POST", headers:{"content-type":"application/json"}, body:JSON.stringify({text, page: location.pathname.replace(/index\.html$/, "")})});
          if (r.status === 429) msg.textContent = "That's a lot of notes for one day. Try again tomorrow.";
          else if (!r.ok) throw 0;
          else { t.value = ""; msg.textContent = "Sent. Thank you."; setTimeout(() => { if (dlg.open) dlg.close(); msg.textContent = ""; }, 1400); }
        } catch (err){ msg.textContent = "That didn't send. Check your connection and try again."; }
        send.disabled = false;
      });
    }
    dlg.querySelector(".sc-fbm").textContent = ""; dlg.showModal(); dlg.querySelector("textarea").focus();
  };
  function add(){
    const r = document.querySelector(".sc-head .sc-r");
    if (r && !r.querySelector(".sc-fbbtn")){
      const b = document.createElement("button"); b.type = "button"; b.className = "sc-btn sc-fbbtn"; b.setAttribute("aria-label", "Send feedback");
      b.innerHTML = ICON + "<span>Feedback</span>"; b.onclick = window.scFeedback;
      const fan = r.querySelector(".sc-fan"); if (fan && fan.nextSibling) r.insertBefore(b, fan.nextSibling); else r.appendChild(b);
    }
    document.querySelectorAll("footer").forEach(f => { const n = f.querySelector(".sc-fextra") || f.querySelector("nav"); if (!n || n.querySelector(".sc-fblink")) return;
      const a = document.createElement("a"); a.href = "#feedback"; a.className = "sc-fblink"; a.textContent = "Feedback"; a.onclick = e => { e.preventDefault(); window.scFeedback(); }; n.appendChild(a); });
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", () => setTimeout(add, 0)); else setTimeout(add, 0);
})();

/* One look for every map. scMap.style(map) recolors the OpenFreeMap base map (or a page's plain fallback) to the shared
   land, water and park colors, so the housing, transit, lot, street and Bears maps read as one site. It only touches the base
   style's own background, water and green layers; a page's own layers are left alone. Call it right after the map loads.
   scMap.blank() is the plain base to start from where the tiles aren't available. */
window.scMap = {
  land: "#eef1f4", water: "#8cc4e8", green: "#cfe4c3",
  blank(extra){ return Object.assign({version:8, sources:{}, layers:[{id:"bg", type:"background", paint:{"background-color":"#eef1f4"}}]}, extra || {}); },
  style(map, opt){
    opt = opt || {};
    (map.getStyle().layers || []).forEach(l => { const id = l.id;
      try {
        if (l.type === "background") map.setPaintProperty(id, "background-color", scMap.land);
        else if (l.type === "fill" && /water/.test(id)) map.setPaintProperty(id, "fill-color", scMap.water);
        else if (l.type === "line" && /waterway|river|canal/.test(id)) map.setPaintProperty(id, "line-color", scMap.water);
        else if (l.type === "fill" && /park|wood|forest|grass|cemetery|golf|pitch|landcover/.test(id)) map.setPaintProperty(id, "fill-color", scMap.green);
        else if (opt.noBuildings && /building/.test(id)) map.setLayoutProperty(id, "visibility", "none");
      } catch (e) {}
    });
  }
};

/* Languages: English, Spanish, Chinese (Simplified) and Polish, Chicago's three most spoken languages after English (ACS).
   A reader picks one from the language button in the header (or ?lang=es|zh|pl in a link); it is remembered in this browser
   as sc-lang. Translations live in /shape/<lang>.json (built by tools/site/es_build.py), keyed by the English text, so pages
   stay one file each:
     t: {"English text": "translation"}                  a text node or attribute whose whole text matches
     h: {"English with <b>tags</b>": "…<b>…</b>"}        an element whose inner HTML matches (for sentences with links or bold)
     r: [["^(\\d[\\d,]*) homes$", "$1 viviendas"]]     patterns for text with numbers in it (hr: the same for inner HTML;
                                                         w: words a pattern can look up, written {{Nov}} in its replacement;
                                                         [[$1]] in a replacement translates that captured piece with t)
   Anything without a translation stays in English. New text added by a page later (a simulator's results, a pop-up) is
   translated as it appears. Elements marked translate="no" (names, addresses, codes) are left alone. */
(function(){
  const LANGS = {en: {n: "English", c: "EN", html: "en"}, es: {n: "Español", c: "ES", html: "es", offer: "Este sitio también está en español.", yes: "Leer en español", no: "No, gracias", part: "Esta página solo está traducida en parte. El resto sigue en inglés.", ok: "Entendido"},
    zh: {n: "中文", c: "中文", html: "zh-Hans", offer: "本网站也有中文版。", yes: "阅读中文版", no: "不用了", part: "本页面只翻译了一部分，其余仍为英文。", ok: "知道了"},
    pl: {n: "Polski", c: "PL", html: "pl", offer: "Ta strona jest też po polsku.", yes: "Czytaj po polsku", no: "Nie, dziękuję", part: "Ta strona jest przetłumaczona tylko częściowo. Reszta jest po angielsku.", ok: "Rozumiem"}};
  const KEY = "sc-lang", qs = new URLSearchParams(location.search).get("lang");
  let lang = "en"; try { if (LANGS[qs]) localStorage.setItem(KEY, qs); lang = localStorage.getItem(KEY) || "en"; } catch (e) { if (LANGS[qs]) lang = qs; }
  if (!LANGS[lang]) lang = "en";
  window.scLang = lang;
  window.scSetLang = l => { try { localStorage.setItem(KEY, l); } catch (e) {} const u = new URL(location.href); u.searchParams.delete("lang"); location.replace(u.toString()); };
  const norm = s => s.replace(/\s+/g, " ").trim();
  function button(){
    const r = document.querySelector(".sc-head .sc-r"); if (!r || r.querySelector(".sc-lang")) return;
    const w = document.createElement("div"); w.className = "sc-langw"; w.setAttribute("translate", "no");
    const b = document.createElement("button"); b.type = "button"; b.className = "sc-btn sc-lang"; b.textContent = LANGS[lang].c;
    b.setAttribute("aria-haspopup", "true"); b.setAttribute("aria-expanded", "false"); b.setAttribute("aria-label", "Language · Idioma · 语言 · Język");
    const m = document.createElement("div"); m.className = "sc-langmenu"; m.hidden = true;
    for (const [k, L] of Object.entries(LANGS)){ const o = document.createElement("button"); o.type = "button"; o.lang = L.html; o.textContent = L.n;
      if (k === lang) o.setAttribute("aria-current", "true"); o.onclick = () => k === lang ? close() : window.scSetLang(k); m.appendChild(o); }
    const close = () => { m.hidden = true; b.setAttribute("aria-expanded", "false"); };
    b.onclick = e => { e.stopPropagation(); m.hidden = !m.hidden; b.setAttribute("aria-expanded", String(!m.hidden)); if (!m.hidden) m.querySelector("button").focus(); };
    document.addEventListener("click", e => { if (!w.contains(e.target)) close(); });
    w.addEventListener("keydown", e => { if (e.key === "Escape"){ close(); b.focus(); } });
    w.append(b, m); const fb = r.querySelector(".sc-fbbtn, .sc-menubtn"); fb ? r.insertBefore(w, fb) : r.appendChild(w);
    document.querySelectorAll("footer").forEach(f => { const n = f.querySelector(".sc-fextra") || f.querySelector("nav"); if (!n || n.querySelector(".sc-langlink")) return;
      for (const [k, L] of Object.entries(LANGS)){ if (k === lang) continue;
        const a = document.createElement("a"); a.href = "?lang=" + k; a.className = "sc-langlink"; a.setAttribute("translate", "no"); a.textContent = L.n; a.lang = L.html; n.appendChild(a); } });
  }
  function offer(){   // one quiet offer for readers whose browser is set to Spanish, Chinese or Polish
    if (lang !== "en") return; let seen = null; try { seen = localStorage.getItem("sc-lang-offer"); } catch (e) {}
    const want = ((navigator.language || "").toLowerCase().match(/^(es|zh|pl)/) || [])[1];
    if (seen || !want || (want === "zh" && /^zh-(tw|hk|mo|hant)/i.test(navigator.language))) return;
    const L = LANGS[want], d = document.createElement("div"); d.className = "sc-langoffer"; d.lang = L.html; d.setAttribute("role", "region"); d.setAttribute("aria-label", L.n);
    d.innerHTML = '<span></span><button type="button" class="sc-btn primary"></button><button type="button" class="sc-btn"></button>';
    d.children[0].textContent = L.offer; d.children[1].textContent = L.yes; d.children[2].textContent = L.no;
    const done = () => { try { localStorage.setItem("sc-lang-offer", "1"); } catch (e) {} d.remove(); };
    d.children[1].onclick = () => { done(); window.scSetLang(want); }; d.children[2].onclick = done;
    document.body.appendChild(d);
  }
  // Pages translated in full; on any other page a reader in another language gets one short note (once per page per visit).
  const FULL = ["/", "/index.html", "/wards/", "/news/", "/press/", "/progress/", "/grants/", "/404.html", "/about/"];
  function partial(){
    if (lang === "en" || FULL.includes(location.pathname) || document.querySelector(".sc-err404")) return;
    const k = "sc-part-" + location.pathname; try { if (sessionStorage.getItem(k)) return; } catch (e) {}
    const L = LANGS[lang], d = document.createElement("div"); d.className = "sc-langoffer"; d.setAttribute("role", "status"); d.setAttribute("translate", "no");
    d.innerHTML = '<span></span><button type="button" class="sc-btn"></button>'; d.children[0].textContent = L.part; d.children[1].textContent = L.ok;
    d.children[1].onclick = () => { try { sessionStorage.setItem(k, "1"); } catch (e) {} d.remove(); };
    document.body.appendChild(d); setTimeout(() => d.isConnected && d.children[1].click(), 9000);
  }
  function go(){ button(); offer(); partial(); if (lang !== "en") translate(); }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", () => setTimeout(go, 0)); else setTimeout(go, 0);
  if (lang === "en") return;
  document.documentElement.lang = LANGS[lang].html; document.documentElement.classList.add("sc-" + lang, "sc-tr");
  let T = null, H = null, R = [], HR = [];
  const SKIP = "script,style,code,pre,textarea,[translate=no],.sc-lang,.sc-langlink";
  let W = {};   // words used inside patterns: "{{Nov}}" in a replacement becomes W.Nov (month and day names)
  let depth = 0;   // [[text]] in a replacement: translate that piece too (exact text, then patterns, at most 3 levels deep)
  const words = v => v.replace(/\{\{([^}]+)\}\}/g, (m, w) => W[w] != null ? W[w] : w).replace(/\[\[(.*?)\]\]/g, (m, w) => { if (!w.trim()) return w; if (depth > 2) return w; depth++; const t = tr(w); depth--; return t != null ? t : w; });
  function tr(s){ const k = norm(s); if (!k) return null; if (T[k] != null) return T[k];
    for (const [re, to] of R) if (re.test(k)) return words(k.replace(re, to)); return null; }
  function text(n){ const v = tr(n.nodeValue); if (v != null && v !== norm(n.nodeValue)){ const m = n.nodeValue.match(/^\s*/)[0], e = n.nodeValue.match(/\s*$/)[0]; n.nodeValue = m + v + e; } }
  function attrs(el){ for (const a of ["aria-label", "placeholder", "title", "alt", "data-t"]){ const v = el.getAttribute && el.getAttribute(a); if (v){ const t = tr(v); if (t != null) el.setAttribute(a, t); } } }
  function walk(root){
    if (root.nodeType === 3){ if (!root.parentElement || !root.parentElement.closest(SKIP)) text(root); return; }
    if (root.nodeType !== 1 || root.closest(SKIP)) return;
    const it = document.createTreeWalker(root, NodeFilter.SHOW_ELEMENT | NodeFilter.SHOW_TEXT, {acceptNode: n => n.nodeType === 1 && n.matches(SKIP) ? NodeFilter.FILTER_REJECT : NodeFilter.FILTER_ACCEPT});
    const todo = []; let n = root;
    do { todo.push(n); } while ((n = it.nextNode()));
    const done = new Set();
    for (const x of todo){
      if (x.nodeType === 1){
        attrs(x);
        if (H && x.childElementCount && x.childElementCount < 12){ const k = norm(x.innerHTML); let v = H[k];
          if (v == null) for (const [re, to] of HR) if (re.test(k)){ v = words(k.replace(re, to)); break; }
          if (v != null){ x.innerHTML = v; x.querySelectorAll("*").forEach(c => done.add(c)); x.childNodes.forEach(c => done.add(c)); done.add(x); continue; } }
      } else if (!done.has(x) && !(x.parentElement && done.has(x.parentElement))) text(x);
    }
  }
  function translate(){
    fetch("/shape/" + lang + ".json").then(r => r.json()).then(d => {
      T = d.t || {}; H = d.h || {}; R = (d.r || []).map(([a, b]) => [new RegExp(a), b]); HR = (d.hr || []).map(([a, b]) => [new RegExp(a), b]); W = d.w || {};
      if (document.title){ const t = tr(document.title); if (t) document.title = t; }
      walk(document.body);
      let q = new Set(), busy = false;
      new MutationObserver(ms => { for (const m of ms){ if (m.type === "characterData") q.add(m.target); else m.addedNodes.forEach(x => q.add(x)); }
        if (!busy){ busy = true; requestAnimationFrame(() => { busy = false; const L = [...q]; q = new Set(); L.forEach(x => x.isConnected && walk(x)); }); } })
        .observe(document.body, {childList: true, subtree: true, characterData: true});
    }).catch(() => {});
  }
})();

/* Cloudflare Web Analytics on every page: counts page views, no cookies, nothing personal. Off on claude.ai previews and local
   files. At launch, add the new domain under Cloudflare → Web Analytics and paste its token here if it differs. */
(function(){
  const CF_TOKEN = "1e9dc637635a4e7c8afaa420c1136085";
  if (!/^https?:$/.test(location.protocol) || /claude|anthropic|usercontent|localhost|127\.0\.0\.1/.test(location.hostname)) return;
  if (document.querySelector('script[src*="cloudflareinsights"]')) return;
  const b = document.createElement("script"); b.defer = true; b.src = "https://static.cloudflareinsights.com/beacon.min.js";
  b.setAttribute("data-cf-beacon", JSON.stringify({token: CF_TOKEN})); document.head.appendChild(b);
})();

/* "Your address": the lot tool, grants finder and deal check share one address. Any element with [data-atabs] becomes a tab row
   linking the three, each carrying ?q=<address>. Pages call window.scSetAddr(label) when someone picks an address; the address is
   kept in this browser (localStorage "sc-addr") so the next tab opens on it. */
(function(){
  const TABS = [["/lot/", "Zoning and rules", "Zoning"], ["/grants/", "Grants and help", "Grants"], ["/deal/", "Affordable deal check", "Deal check"]];   // long and phone labels
  const get = () => { try { return localStorage.getItem("sc-addr") || ""; } catch(e){ return ""; } };
  function draw(){
    const a = get();
    document.querySelectorAll("[data-atabs]").forEach(el => {
      const here = location.pathname.replace(/index\.html$/, "");
      el.innerHTML = `<span class="sc-athd">Your address${a ? ": <b translate=\"no\"></b>" : ""}</span><span class="sc-atl">` + TABS.map(([h, n, sh]) =>
        `<a href="${h}${a ? "?q=" + encodeURIComponent(a) : ""}"${here === h ? ' aria-current="page"' : ""}><span class="sc-atlong">${n}</span><span class="sc-atshort">${sh}</span></a>`).join("") + "</span>";
      const b = el.querySelector("b"); if (b) b.textContent = a;
    });
  }
  window.scSetAddr = label => { if (!label) return; try { localStorage.setItem("sc-addr", label); } catch(e){} draw(); };
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", draw); else draw();
  addEventListener("pageshow", draw);
})();

/* Skip link: the first Tab on any page jumps past the header to the page's content (main, or the tool panel on map pages). */
(function(){
  function add(){
    if (document.querySelector(".sc-skip")) return;
    const t = document.querySelector("main, #panel, aside#panel, .sheet, .panel, [role=main]"); if (!t) return;
    if (!t.id) t.id = "sc-main"; if (!t.hasAttribute("tabindex")) t.setAttribute("tabindex", "-1");
    const a = document.createElement("a"); a.className = "sc-skip"; a.href = "#" + t.id; a.textContent = "Skip to content";
    a.addEventListener("click", e => { e.preventDefault(); t.focus({preventScroll:false}); t.scrollIntoView({block:"start"}); });
    document.body.prepend(a);
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", add); else add();
})();

/* Narrow headers: on map pages the header carries Sources and Share too; when "Shape Chicago" would run under the buttons,
   keep only the star (class sc-tight on the header). */
(function(){
  function fit(){
    document.querySelectorAll(".sc-head").forEach(h => {
      const b = h.querySelector(".sc-brand span"), r = h.querySelector(".sc-r"); if (!b || !r) return;
      h.classList.remove("sc-tight");
      if (b.getBoundingClientRect().right > r.getBoundingClientRect().left - 6) h.classList.add("sc-tight");
    });
  }
  const go = () => { fit(); setTimeout(fit, 400); };
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", go); else go();
  addEventListener("resize", fit); addEventListener("load", fit);
})();

/* The page tabs must never be cut off. When the header's "Not affiliated…" line would squeeze them, it moves out of the
   header (html.sc-nofan) and the tool's own copy of the line (.sc-fanline, housing's credit, transit's panel) shows instead. */
(function(){
  function fit(){
    const h = document.querySelector(".sc-head"), n = h && h.querySelector(".sc-nav"); if (!n) return;
    document.documentElement.classList.remove("sc-nofan");
    if (n.scrollWidth > n.clientWidth + 2 && h.querySelector(".sc-fan")) document.documentElement.classList.add("sc-nofan");
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", fit); else fit();
  addEventListener("resize", fit); if (document.fonts) document.fonts.ready.then(fit);
})();


/* Clay motion on every page (Kyle, Nov. 12, 2026; samples at /preview/motion/). Off for people who turn motion off.
   - Waiting: any text that reads "Loading…" becomes the turning star (inline) or, for a page-sized wait (.empty, a hero),
     the mid-rise going up floor by floor. scLoading(text, "rise"|"train"|"star") returns the same markup for scripts.
   - Pop-in: clay pictures inside [data-popin] pop in one after another when they scroll into view.
   - A+ burst: scBurst(element) stamps clay stars out from an element (a balanced budget, a right answer).
   Housing keeps its own loader and confetti. */
(function(){
  const RM = matchMedia("(prefers-reduced-motion: reduce)").matches, A = "/shape/art/motion/";
  const SZ = {rise: [192, 142], train: [280, 130], star: [56, 53]};
  window.scLoading = (t, k) => { k = k || "star"; const [w, h] = SZ[k];
    const src = RM ? A + (k === "star" ? "star_still.png" : k + "_still.png") : A + k + ".webp";
    return k === "star" ? `<span class="sc-spinrow" role="status"><img class="sc-spin" src="${src}" alt="" width="28" height="27">${t}</span>`
      : `<div class="sc-loading" role="status"><img src="${src}" alt="" width="${w}" height="${h}"><span>${t}</span></div>`; };
  const RX = /^(Loading|Checking|Cargando|Comprobando|Wczytywanie|Ładowanie|Sprawdzanie|正在加载|加载中|正在检查).*(…|\.\.\.)$/;
  function up(root){
    if (!root.querySelectorAll) return;
    root.querySelectorAll("p,div,li,h1,span,b").forEach(el => {
      if (el.children.length || el.closest(".sc-loading,.sc-spinrow,#loading,.ldcard,.loading,[data-noload]")) return;
      const t = (el.textContent || "").trim(); if (!t || t.length > 90 || !RX.test(t)) return;
      const big = el.matches(".empty") || !!el.closest(".hero");
      el.innerHTML = window.scLoading(t, big ? "rise" : "star");
    });
  }
  function popin(root){
    (root.querySelectorAll ? root.querySelectorAll("[data-popin]:not(.sc-popready)") : []).forEach(c => {
      c.classList.add("sc-popready"); if (RM) { c.classList.add("sc-popgo"); return; }
      const io = new IntersectionObserver(es => es.forEach(e => { if (e.isIntersecting){ c.classList.add("sc-popgo"); io.disconnect(); } }), {threshold: .25});
      io.observe(c);
    });
  }
  window.scBurst = el => {
    if (RM || !el) return; const r = el.getBoundingClientRect(), box = document.createElement("div"); box.className = "sc-burst";
    box.style.left = (r.left + r.width / 2) + "px"; box.style.top = (r.top + r.height / 2) + "px";
    for (let k = 0; k < 14; k++){ const i = document.createElement("i"), a = k / 14 * Math.PI * 2 + Math.random() * .3, d = 70 + Math.random() * 60;
      i.style.cssText = `--x:${Math.cos(a) * d}px;--y:${Math.sin(a) * d * .8}px;--r:${(Math.random() - .5) * 540}deg;animation-delay:${Math.random() * .1}s`; box.appendChild(i); }
    document.body.appendChild(box); el.classList.remove("sc-stamp"); void el.offsetWidth; el.classList.add("sc-stamp"); setTimeout(() => box.remove(), 1400);
  };
  function go(){ up(document.body); popin(document.body);
    new MutationObserver(ms => ms.forEach(m => m.addedNodes.forEach(n => { if (n.nodeType === 1){ up(n.parentNode || n); popin(n);
      const g = n.matches && n.matches("b.good") ? n : n.querySelector && n.querySelector("b.good"); if (g && /^Right/.test(g.textContent)) window.scBurst(g); } }))).observe(document.body, {childList: true, subtree: true}); }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", go); else go();
})();
