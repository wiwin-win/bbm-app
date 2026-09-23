/* Service worker: simpan shell aplikasi supaya /m tetap terbuka tanpa sinyal. */
const CACHE = "bbm-v3";
const SHELL = [
  "/m", "/login", "/static/gaya-hp.css", "/static/xlsx.js",
  "/static/logo.png", "/static/icon-192.png",
  "/manifest.webmanifest"
];

self.addEventListener("install", e => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(SHELL).catch(() => {})));
  self.skipWaiting();
});
self.addEventListener("activate", e => {
  e.waitUntil(caches.keys().then(ks => Promise.all(
    ks.filter(k => k !== CACHE).map(k => caches.delete(k)))));
  self.clients.claim();
});
self.addEventListener("fetch", e => {
  const u = new URL(e.request.url);
  if (e.request.method !== "GET") return;
  if (u.pathname.startsWith("/api/") || u.pathname.startsWith("/unduh/")) return;  // selalu dari server
  e.respondWith(
    fetch(e.request).then(r => {
      if (r.ok && (u.pathname === "/m" || u.pathname === "/" || u.pathname.startsWith("/static/"))) {
        const copy = r.clone();
        caches.open(CACHE).then(c => c.put(e.request, copy)).catch(() => {});
      }
      return r;
    }).catch(() => caches.match(e.request))
  );
});
