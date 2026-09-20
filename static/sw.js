/**
 * KAI Student OS - Service Worker (v2.1)
 *
 * Security Architecture:
 * - STATIC ASSETS -> CacheStorage (for offline shell & fast loading)
 * - AUTHENTICATED APIs (/api/*, /auth/*, /files/*) -> NEVER stored in CacheStorage
 * - USER DATA (Tasks, Schedule) -> Handled via client-side user-keyed IndexedDB
 */

const CACHE_NAME = 'kai-student-os-v2.1';

const PRECACHE_ASSETS = [
  '/',
  '/index.html',
  '/login.html',
  '/manifest.json',
  '/static/app.js',
  '/static/styles.css',
  '/static/favicon.ico'
];

function isStaticAsset(url) {
  // Disallow any API or sensitive endpoints from ever entering CacheStorage
  if (
    url.pathname.startsWith('/api/') ||
    url.pathname.startsWith('/auth/') ||
    url.pathname.startsWith('/files/') ||
    url.pathname.startsWith('/docs') ||
    url.pathname.startsWith('/openapi.json')
  ) {
    return false;
  }

  // Allow static assets
  if (url.pathname.startsWith('/static/')) return true;
  if (
    url.pathname === '/' ||
    url.pathname === '/index.html' ||
    url.pathname === '/login.html' ||
    url.pathname === '/manifest.json' ||
    url.pathname === '/favicon.ico'
  ) {
    return true;
  }

  // Extensions
  if (/\.(?:css|js|json|png|jpg|jpeg|svg|ico|woff2|woff|ttf)$/i.test(url.pathname)) {
    return true;
  }

  return false;
}

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.addAll(PRECACHE_ASSETS).catch((err) => {
        console.warn('[SW] Pre-cache partial fail, continuing anyway:', err);
      });
    })
  );
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) => {
      return Promise.all(
        keys.map((k) => {
          if (k !== CACHE_NAME) {
            console.log('[SW] Deleting obsolete cache:', k);
            return caches.delete(k);
          }
        })
      );
    })
  );
  self.clients.claim();
});

self.addEventListener('fetch', (event) => {
  const url = new URL(event.request.url);

  // Authenticated APIs or non-GET requests: strictly bypass CacheStorage (network-only)
  if (!isStaticAsset(url) || event.request.method !== 'GET') {
    event.respondWith(fetch(event.request));
    return;
  }

  // Network-first for static assets with cache fallback
  event.respondWith(
    fetch(event.request)
      .then((networkResponse) => {
        if (networkResponse && networkResponse.status === 200) {
          const responseClone = networkResponse.clone();
          caches.open(CACHE_NAME).then((cache) => {
            cache.put(event.request, responseClone);
          });
        }
        return networkResponse;
      })
      .catch(() => {
        // Fallback to cache when offline
        return caches.match(event.request);
      })
  );
});
