// Redline Router service worker — app-shell offline cache
const CACHE = 'redline-v181';
const SHELL = [
  './',
  './index.html',
  './manifest.webmanifest',
  './icon-192.png',
  './icon-512.png',
  'https://unpkg.com/leaflet@1.9.4/dist/leaflet.css',
  'https://unpkg.com/leaflet@1.9.4/dist/leaflet.js'
];
self.addEventListener('install', e => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(SHELL)).then(() => self.skipWaiting()));
});
self.addEventListener('activate', e => {
  e.waitUntil(caches.keys().then(ks => Promise.all(ks.filter(k => k !== CACHE).map(k => caches.delete(k)))).then(() => self.clients.claim()));
});
self.addEventListener('fetch', e => {
  const req = e.request;
  const url = req.url;
  // Never cache geocoding or map tiles — always go to network.
  if (url.includes('nominatim') || url.includes('basemaps.cartocdn') || url.includes('tile')) {
    e.respondWith(fetch(req).catch(() => new Response('', {status: 504})));
    return;
  }
  // App HTML shell: network-first so new deploys load on launch (no reinstall).
  // Falls back to cache when offline.
  if (req.mode === 'navigate' || url.endsWith('/') || url.endsWith('/index.html')) {
    e.respondWith(
      fetch(req).then(resp => {
        const copy = resp.clone();
        caches.open(CACHE).then(c => c.put('./index.html', copy)).catch(() => {});
        return resp;
      }).catch(() => caches.match('./index.html').then(h => h || caches.match('./')))
    );
    return;
  }
  // Other static assets (Leaflet, icons, manifest): cache-first.
  e.respondWith(
    caches.match(req).then(hit => hit || fetch(req).then(resp => {
      const copy = resp.clone();
      caches.open(CACHE).then(c => c.put(req, copy)).catch(() => {});
      return resp;
    }).catch(() => caches.match('./index.html')))
  );
});
