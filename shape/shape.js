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
/* keep the current page's tab visible when the tab bar scrolls (phones) */
(function(){ function f(){ const n = document.querySelector(".sc-nav"), a = n && n.querySelector('[aria-current="page"]'); if (!a || n.scrollWidth <= n.clientWidth) return; n.scrollLeft = a.offsetLeft - n.offsetLeft - (n.clientWidth - a.offsetWidth) / 2; }
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
  function footer(){
    const f = document.querySelector("footer");
    if (f && !f.querySelector('a[href="/support/"]') && !f.querySelector(".sc-foot-extra")){
      const p = document.createElement("p"); p.className = "sc-foot-extra";
      p.innerHTML = `<span data-support></span> <a href="/advertise/">Advertise with us</a>`;
      (f.querySelector(".wrap, .fw") || f).appendChild(p);
    }
    if (document.querySelector("[data-ad], [data-support]")) window.scShowAds();
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", footer); else footer();
})();
