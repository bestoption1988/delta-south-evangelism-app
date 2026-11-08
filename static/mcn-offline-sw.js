/* MCN Delta South offline application cache.
 * Public pages and assets are cached for offline reading. Protected API writes,
 * payment routes and authenticated private responses are never cached here.
 */
const CACHE_VERSION = "mcn-delta-south-shell-v9";
const PAGE_CACHE = CACHE_VERSION + "-pages";
const ASSET_CACHE = CACHE_VERSION + "-assets";
const PUBLIC_ROUTES = [
  "/", "/devotional-centre", "/devotional-centre/english-hymns",
  "/devotional-centre/yoruba-hymns", "/devotional-centre/akokun",
  "/devotional-centre/bible-verses", "/devotional-centre/canticles",
  "/devotional-centre/communion", "/devotional-centre/yoruba-communion",
  "/devotional-centre/creeds", "/devotional-centre/holy-bible",
  "/devotional-centre/lectionary", "/media-library"
];
const BLOCKED = /(^|\/)(admin|login|logout|register|registration|member-registration|payment|checkout|dashboard|staff|member|profile|account|finance|giving|give|donate|donation|flutterwave|paystack|security|customer-care|settings|reports)(\/|$)/i;

self.addEventListener("install", event => {
  event.waitUntil((async () => {
    const cache = await caches.open(PAGE_CACHE);
    for (const path of PUBLIC_ROUTES) {
      try {
        const response = await fetch(path, { credentials: "same-origin" });
        if (response.ok && response.headers.get("content-type")?.includes("text/html")) {
          await cache.put(path, response.clone());
        }
      } catch (_) {}
    }
    await self.skipWaiting();
  })());
});

self.addEventListener("activate", event => {
  event.waitUntil((async () => {
    const keys = await caches.keys();
    await Promise.all(keys.filter(key => key.startsWith("mcn-delta-south-") &&
      key !== PAGE_CACHE && key !== ASSET_CACHE).map(key => caches.delete(key)));
    await self.clients.claim();
  })());
});

function safePage(url) {
  return url.origin === self.location.origin &&
    !BLOCKED.test(url.pathname) &&
    !url.pathname.startsWith("/api/") &&
    !url.pathname.startsWith("/static/uploads/private");
}

async function cachePage(url, pageCache, assetCache) {
  try {
    const response = await fetch(url.href, { credentials: "same-origin" });
    if (!response.ok) return [];
    const type = response.headers.get("content-type") || "";
    if (!type.includes("text/html")) return [];
    await pageCache.put(url.href, response.clone());
    const html = await response.clone().text();
    const links = [];
    const hrefPattern = /<a\b[^>]*\bhref\s*=\s*["']([^"']+)["']/gi;
    let match;
    while ((match = hrefPattern.exec(html)) !== null) {
      try {
        const target = new URL(match[1], url.href);
        if (safePage(target) && (target.pathname !== url.pathname || target.search !== url.search)) links.push(target);
      } catch (_) {}
    }
    const assetPattern = /(?:src|href)\s*=\s*["']([^"']+)["']/gi;
    while ((match = assetPattern.exec(html)) !== null) {
      try {
        const asset = new URL(match[1], url.href);
        const localAsset = asset.origin === self.location.origin;
        const approvedMediaHost = /(^|\.)supabase\.co$/i.test(asset.hostname) ||
          /(^|\.)supabase\.in$/i.test(asset.hostname);
        const supportedAsset = /\.(css|js|png|jpe?g|webp|gif|svg|woff2?|ttf|pdf|docx?|rtf|txt|xlsx?|pptx?|mp3|m4a|ogg|wav|mp4|webm)(\?|$)/i.test(asset.href) || asset.pathname.startsWith("/media-library/document/");
        if ((localAsset && supportedAsset) || (asset.protocol === "https:" && approvedMediaHost)) {
          const cached = await caches.match(asset.href);
          if (!cached) {
            try {
              const file = await fetch(asset.href, { mode: localAsset ? "same-origin" : "no-cors", credentials: localAsset ? "same-origin" : "omit" });
              if (file.ok || file.type === "opaque") await assetCache.put(asset.href, file.clone());
            } catch (_) {}
          }
        }
      } catch (_) {}
    }
    return links;
  } catch (_) {
    return [];
  }
}

async function cacheEntireApp() {
  const pageCache = await caches.open(PAGE_CACHE);
  const assetCache = await caches.open(ASSET_CACHE);
  const queue = PUBLIC_ROUTES.map(path => new URL(path, self.location.origin));
  const visited = new Set();
  let count = 0;
  while (queue.length && visited.size < 4000) {
    const batch = [];
    while (queue.length && batch.length < 6 && visited.size < 4000) {
      const candidate = queue.shift();
      if (!candidate || visited.has(candidate.href) || !safePage(candidate)) continue;
      visited.add(candidate.href);
      batch.push(candidate);
    }
    if (!batch.length) continue;
    const discoveredPages = await Promise.all(batch.map(url => cachePage(url, pageCache, assetCache)));
    count += batch.length;
    for (const discovered of discoveredPages) {
      for (const next of discovered) {
        if (!visited.has(next.href) && queue.length < 4000) queue.push(next);
      }
    }
  }
  return count;
}

self.addEventListener("message", event => {
  if (event.data?.type === "CACHE_MCN_APP") {
    event.waitUntil(cacheEntireApp().then(count => {
      event.ports?.[0]?.postMessage({ ok: true, pages: count });
    }).catch(() => event.ports?.[0]?.postMessage({ ok: false })));
  }
});

self.addEventListener("fetch", event => {
  const request = event.request;
  if (request.method !== "GET") return;
  const url = new URL(request.url);

  if (url.origin !== self.location.origin) {
    if (url.protocol === "https:" && (/\.supabase\\.(co|in)$/i.test(url.hostname))) {
      event.respondWith((async () => {
        const cache = await caches.open(ASSET_CACHE);
        const cached = await cache.match(request);
        try {
          const live = await fetch(request);
          if (live.ok || live.type === "opaque") await cache.put(request, live.clone());
          return live;
        } catch (_) {
          return cached || Response.error();
        }
      })());
    }
    return;
  }

  if (request.mode === "navigate") {
    if (!safePage(url)) {
      event.respondWith(fetch(request));
      return;
    }
    event.respondWith((async () => {
      const cache = await caches.open(PAGE_CACHE);
      try {
        const live = await fetch(request);
        if (live.ok && live.headers.get("content-type")?.includes("text/html")) {
          await cache.put(request, live.clone());
        }
        return live;
      } catch (_) {
        return (await cache.match(request)) ||
          (await cache.match(url.pathname + url.search)) ||
          (await cache.match("/")) ||
          new Response("<h2>MCN Delta South</h2><p>This page has not yet been saved for offline use. Reconnect and choose Save app offline.</p>", {
            status: 200, headers: { "Content-Type": "text/html; charset=utf-8" }
          });
      }
    })());
    return;
  }

  if (url.pathname.startsWith("/api/") &&
      !url.pathname.startsWith("/api/offline/") &&
      !url.pathname.startsWith("/api/public/")) return;

  event.respondWith((async () => {
    const cache = await caches.open(ASSET_CACHE);
    const cached = await cache.match(request);
    if (cached) return cached;
    try {
      const live = await fetch(request);
      if (live.ok && (url.pathname.startsWith("/static/") ||
          url.pathname.startsWith("/api/offline/") ||
          url.pathname.startsWith("/api/public/") || url.pathname.startsWith("/media-library/document/") || url.pathname.startsWith("/devotional-centre/holy-bible/books") || url.pathname.startsWith("/devotional-centre/holy-bible/chapter"))) {
        await cache.put(request, live.clone());
      }
      return live;
    } catch (_) {
      return cached || Response.error();
    }
  })());
});
