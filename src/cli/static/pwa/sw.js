/* SuperAI PWA service worker — cache shell only */
const CACHE = "superai-pwa-v1";
const ASSETS = ["/pwa/", "/pwa/index.html", "/pwa/manifest.webmanifest", "/pwa/icon.svg"];

self.addEventListener("install", (event) => {
  event.waitUntil(caches.open(CACHE).then((c) => c.addAll(ASSETS)).then(() => self.skipWaiting()));
});

self.addEventListener("activate", (event) => {
  event.waitUntil(self.clients.claim());
});

self.addEventListener("fetch", (event) => {
  const url = new URL(event.request.url);
  if (url.pathname.startsWith("/pwa/")) {
    event.respondWith(
      caches.match(event.request).then((hit) => hit || fetch(event.request))
    );
  }
});
