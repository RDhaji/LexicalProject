/**
 * Lexical Explorer - Production PWA Service Worker (Milestone 14)
 * Compliance: ARCHITECTURE.md §1, ADR-006, ADR-007
 */

const CACHE_NAME = "lexical-explorer-v1.0.0";
const PRECACHE_ASSETS = [
  "/client/index.html",
  "/client/graph_renderer.js",
  "/client/worker.js",
  "/client/workspace_client.js",
  "https://cdnjs.cloudflare.com/ajax/libs/sql.js/1.12.0/sql-wasm.js",
  "https://cdnjs.cloudflare.com/ajax/libs/sql.js/1.12.0/sql-wasm.wasm"
];

self.addEventListener("install", (e) => {
  e.waitUntil(
    caches.open(CACHE_NAME).then(cache => {
      return cache.addAll(PRECACHE_ASSETS);
    }).then(() => self.skipWaiting())
  );
});

self.addEventListener("activate", (e) => {
  e.waitUntil(
    caches.keys().then(keys => {
      return Promise.all(
        keys.filter(k => k !== CACHE_NAME).map(k => caches.delete(k))
      );
    }).then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (e) => {
  const url = new URL(e.request.url);

  // Allow live streaming and SQLite byte-range requests
  if (url.pathname.endsWith(".db")) {
    e.respondWith(
      fetch(e.request).catch(() => {
        return caches.match(e.request);
      })
    );
    return;
  }

  // Cache-First for static UI shell assets
  e.respondWith(
    caches.match(e.request).then(cached => {
      if (cached) return cached;
      return fetch(e.request).then(response => {
        if (response.status === 200 && e.request.method === "GET") {
          const clone = response.clone();
          caches.open(CACHE_NAME).then(c => c.put(e.request, clone));
        }
        return response;
      });
    })
  );
});
