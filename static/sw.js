const CACHE="mcn-delta-south-stage19-1-v3";
const ASSETS=[
  "/static/app.css?v=20261009-call-controls",
  "/static/app.js?v=20261010-member-linking"
];

self.addEventListener("install", event => {
  event.waitUntil(
    caches.open(CACHE)
      .then(cache => cache.addAll(ASSETS))
      .then(() => self.skipWaiting())
  );
});

self.addEventListener("activate", event => {
  event.waitUntil(
    caches.keys()
      .then(keys => Promise.all(
        keys.filter(key => key.startsWith("mcn-delta-south-stage") && key !== CACHE)
          .map(key => caches.delete(key))
      ))
      .then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", event => {
  const request = event.request;
  const url = new URL(request.url);

  if (
    request.method !== "GET" ||
    url.origin !== self.location.origin ||
    url.pathname.startsWith("/api/") ||
    url.pathname === "/" ||
    url.pathname === "/member-dashboard" ||
    url.pathname === "/login" ||
    url.pathname === "/logout" ||
    url.pathname === "/change-password"
  ) {
    return;
  }

  if (url.pathname !== "/static/app.js" &&
      url.pathname !== "/static/app.css") {
    return;
  }

  event.respondWith(
    fetch(request, { cache: "no-cache" })
      .then(response => {
        if (response.ok) {
          const copy = response.clone();
          caches.open(CACHE).then(cache => cache.put(request, copy));
        }
        return response;
      })
      .catch(async () => {
        const cached = await caches.match(request);
        if (cached) return cached;
        return new Response("Application resource unavailable. Please reconnect and reload.", {
          status: 503,
          headers: { "Content-Type": "text/plain; charset=utf-8" }
        });
      })
  );
});
