/* Shape Chicago service worker: makes return visits fast by keeping the big map data on the device.
   - Map data (/b/*, /meta.json, /wards.json, /transit/data/*): served from the device right away, then quietly checked
     for a newer copy in the background, so the next visit gets any update. When meta.json or transit/data/net.json
     changes, that whole group is cleared first, so files from two different data builds never mix.
   - Pinned libraries (unpkg, Google Fonts files): kept, since their URLs never change.
   - Pages and the site's own scripts and styles: network first, with the saved copy as a fallback when offline.
   - /api/* and map tiles: never touched. */
const V = "v1";
const C_DATA = "sc-data-" + V, C_LIB = "sc-lib-" + V, C_PAGE = "sc-page-" + V, C_META = "sc-meta-" + V;

self.addEventListener("install", () => self.skipWaiting());
self.addEventListener("activate", e => e.waitUntil((async () => {
  const keep = new Set([C_DATA, C_LIB, C_PAGE, C_META]);
  for (const k of await caches.keys()) if (k.startsWith("sc-") && !keep.has(k)) await caches.delete(k);
  await self.clients.claim();
})()));

const isData = p => p.startsWith("/b/") || p === "/meta.json" || p === "/wards.json" || p.startsWith("/transit/data/");
const groupOf = p => p.startsWith("/transit/data/") ? "transit" : "city";
const ANCHOR = {"/meta.json": "city", "/transit/data/net.json": "transit"};

async function digest(buf){ const d = await crypto.subtle.digest("SHA-256", buf); return [...new Uint8Array(d)].slice(0, 8).map(b => b.toString(16).padStart(2, "0")).join(""); }

// an anchor file decides whether its group is still current: fetch it fresh, and if it changed, drop the group
async function anchor(req, group){
  const cache = await caches.open(C_DATA), meta = await caches.open(C_META);
  try {
    const res = await fetch(req, {cache: "no-cache"});
    if (!res.ok) throw new Error(res.status);
    const buf = await res.clone().arrayBuffer(), h = await digest(buf);
    const prev = await meta.match("/__hash/" + group), old = prev ? await prev.text() : null;
    if (old !== h){
      for (const k of await cache.keys()) if (groupOf(new URL(k.url).pathname) === group) await cache.delete(k);
      await meta.put("/__hash/" + group, new Response(h));
    }
    await cache.put(req, res.clone());
    return res;
  } catch (err) {
    const hit = await cache.match(req); if (hit) return hit;
    throw err;
  }
}

// stale-while-revalidate for the rest of the data
async function data(e, req){
  const cache = await caches.open(C_DATA), hit = await cache.match(req, {ignoreSearch: true});
  const fresh = fetch(req).then(res => { if (res.ok) cache.put(req, res.clone()); return res; });
  if (hit){ e.waitUntil(fresh.catch(() => {})); return hit; }
  return fresh;
}

async function lib(req){
  const cache = await caches.open(C_LIB), hit = await cache.match(req);
  if (hit) return hit;
  const res = await fetch(req);
  if (res.ok || res.type === "opaque") cache.put(req, res.clone());
  return res;
}

async function page(req){
  const cache = await caches.open(C_PAGE);
  try { const res = await fetch(req); if (res.ok) cache.put(req, res.clone()); return res; }
  catch (err) { const hit = await cache.match(req, {ignoreSearch: true}); if (hit) return hit; throw err; }
}

self.addEventListener("fetch", e => {
  const req = e.request; if (req.method !== "GET") return;
  const url = new URL(req.url);
  if (url.origin === self.location.origin){
    const p = url.pathname;
    if (p.startsWith("/api/") || p.startsWith("/p/")) return;
    if (ANCHOR[p]) return e.respondWith(anchor(req, ANCHOR[p]));
    if (isData(p)) return e.respondWith(data(e, req));
    if (req.mode === "navigate" || /\.(html|js|css)$/.test(p) || p.endsWith("/")) return e.respondWith(page(req));
    return;
  }
  if ((url.hostname === "unpkg.com" && /@\d/.test(url.pathname)) || url.hostname === "fonts.gstatic.com") return e.respondWith(lib(req));
});
