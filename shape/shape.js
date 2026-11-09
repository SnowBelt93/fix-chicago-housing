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
/* Simulators menu: the button opens a list under it (fixed, so the scrolling tab bar can't clip it) */
(function(){
  function f(){
    const b = document.querySelector(".sc-simbtn"), m = document.querySelector(".sc-simmenu"); if (!b || !m) return;
    const place = () => { const r = b.getBoundingClientRect(); m.style.top = (r.bottom + 6) + "px"; m.style.left = Math.max(8, Math.min(r.left, innerWidth - m.offsetWidth - 8)) + "px"; };
    const open = on => { m.hidden = !on; b.setAttribute("aria-expanded", on); if (on){ place(); const a = m.querySelector('[aria-current="page"]') || m.querySelector("a"); a && a.focus({preventScroll:true}); } };
    b.addEventListener("click", e => { e.stopPropagation(); open(m.hidden); });
    document.addEventListener("click", e => { if (!m.hidden && !m.contains(e.target)) open(false); });
    document.addEventListener("keydown", e => { if (e.key === "Escape" && !m.hidden){ open(false); b.focus(); } });
    m.addEventListener("keydown", e => { const L = [...m.querySelectorAll("a")], i = L.indexOf(document.activeElement);
      if (e.key === "ArrowDown"){ e.preventDefault(); L[(i + 1) % L.length].focus(); } if (e.key === "ArrowUp"){ e.preventDefault(); L[(i - 1 + L.length) % L.length].focus(); } });
    addEventListener("resize", () => { if (!m.hidden) place(); });
    const n = document.querySelector(".sc-nav"); n && n.addEventListener("scroll", () => { if (!m.hidden) place(); }, {passive:true});
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
  const FOOT = [["/housing/","Housing"],["/transit/","Transit"],["/budget/","Budget"],["/pensions/","Pensions"],["/lot/","Your lot"],["/bears/","Bears stadium"],["/plans/","Neighbors' plans"],["/wards/","Wards"],["/tracker/","Permit tracker"],["/news/","News"],["/learn/","Learn"],["/support/","Support"],["/privacy/","Privacy"],["/terms/","Terms"]];
  function footer(){
    /* the shared footer: <footer class="sc-foot" data-sc-foot>Not affiliated…</footer> keeps its line and gets the brand and page links */
    document.querySelectorAll("footer[data-sc-foot]").forEach(el => {
      const line = el.textContent.trim() || "Not affiliated with the City of Chicago.";
      el.innerHTML = `<div class="sc-foot-in"><a class="sc-brand" href="/"><svg viewBox="0 0 24 24" aria-hidden="true"><path fill="#e4002b" d="M12 1 L14.4 7.84 L21.53 6.5 L16.8 12 L21.53 17.5 L14.4 16.16 L12 23 L9.6 16.16 L2.47 17.5 L7.2 12 L2.47 6.5 L9.6 7.84 Z"/></svg><span>Shape Chicago</span></a><span>${esc(line)}</span><nav aria-label="All pages">${FOOT.map(([h, t]) => `<a href="${h}">${esc(t)}</a>`).join("")}</nav></div>`;
      el.removeAttribute("data-sc-foot");
    });
    const f = document.querySelector("footer");
    if (f && !f.querySelector('a[href="/support/"]') && !f.querySelector(".sc-foot-extra")){
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
