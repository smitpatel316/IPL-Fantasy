/* IPL Fantasy service worker: offline-resilient app shell.
   - Navigations: network-first, fall back to the cached shell so the app
     opens after the first visit even when offline.
   - Same-origin hashed build assets (/_next/static/…) and icons: cache-first.
   - API calls go to the cross-origin FastAPI backend and are never
     intercepted here (cross-origin requests are left alone), so dynamic
     data can't be served stale or break. */
const SHELL_CACHE = "ipl-fantasy-shell-v1";
const STATIC_CACHE = "ipl-fantasy-static-v1";
const SHELL_URLS = ["/"];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(SHELL_CACHE).then((cache) => cache.addAll(SHELL_URLS)).then(() => self.skipWaiting())
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((keys) =>
        Promise.all(
          keys
            .filter((k) => k !== SHELL_CACHE && k !== STATIC_CACHE)
            .map((k) => caches.delete(k))
        )
      )
      .then(() => self.clients.claim())
  );
});

function isStaticAsset(url) {
  return (
    url.pathname.startsWith("/_next/static/") ||
    url.pathname.startsWith("/icons/") ||
    url.pathname === "/manifest.webmanifest"
  );
}

self.addEventListener("fetch", (event) => {
  const { request } = event;
  if (request.method !== "GET") return;
  const url = new URL(request.url);
  if (url.origin !== self.location.origin) return; // API + third-party: pass through

  if (isStaticAsset(url)) {
    // Cache-first: hashed build assets are immutable.
    event.respondWith(
      caches.open(STATIC_CACHE).then((cache) =>
        cache.match(request).then(
          (hit) =>
            hit ||
            fetch(request).then((res) => {
              if (res.ok) cache.put(request, res.clone());
              return res;
            })
        )
      )
    );
    return;
  }

  if (request.mode === "navigate") {
    // Network-first with shell fallback: page data is fetched client-side
    // from the backend, so the cached shell is the right offline experience.
    event.respondWith(
      fetch(request)
        .then((res) => {
          const copy = res.clone();
          caches.open(SHELL_CACHE).then((cache) => cache.put(request, copy));
          return res;
        })
        .catch(() =>
          caches.open(SHELL_CACHE).then((cache) =>
            cache.match(request).then((hit) => hit || cache.match("/"))
          )
        )
    );
  }
});
