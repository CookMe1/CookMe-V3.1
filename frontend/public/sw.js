// CookMe Service Worker for PWA, Share Target, and Offline Support

const CACHE_NAME = 'cookme-v2';
const STATIC_CACHE = 'cookme-static-v2';
const DYNAMIC_CACHE = 'cookme-dynamic-v2';

// Static assets to cache on install
const STATIC_ASSETS = [
  '/',
  '/manifest.json',
  '/icons/icon-192.png',
  '/icons/icon-512.png'
];

// API routes that should be cached
const CACHEABLE_API_ROUTES = [
  '/api/recipes/filters/options'
];

// Install event - cache static assets
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(STATIC_CACHE)
      .then(cache => {
        console.log('CookMe SW: Caching static assets');
        return cache.addAll(STATIC_ASSETS);
      })
      .then(() => self.skipWaiting())
      .catch(err => {
        console.log('CookMe SW: Cache failed, continuing anyway', err);
        return self.skipWaiting();
      })
  );
});

// Activate event - clean old caches
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys()
      .then(cacheNames => {
        return Promise.all(
          cacheNames
            .filter(name => name.startsWith('cookme-') && 
                          name !== STATIC_CACHE && 
                          name !== DYNAMIC_CACHE)
            .map(name => {
              console.log('CookMe SW: Removing old cache', name);
              return caches.delete(name);
            })
        );
      })
      .then(() => clients.claim())
  );
});

// Fetch event - network first with cache fallback
self.addEventListener('fetch', (event) => {
  const { request } = event;
  const url = new URL(request.url);
  
  // Skip non-GET requests
  if (request.method !== 'GET') {
    return;
  }
  
  // Skip chrome-extension and other non-http(s) URLs
  if (!url.protocol.startsWith('http')) {
    return;
  }
  
  // Handle navigation requests (HTML pages)
  if (request.mode === 'navigate') {
    event.respondWith(
      fetch(request)
        .then(response => {
          // Clone and cache successful navigations
          if (response.ok) {
            const responseClone = response.clone();
            caches.open(DYNAMIC_CACHE)
              .then(cache => cache.put(request, responseClone))
              .catch(() => {});
          }
          return response;
        })
        .catch(() => {
          // Fallback to cached version or root page
          return caches.match(request)
            .then(cached => cached || caches.match('/'));
        })
    );
    return;
  }
  
  // Handle static assets (images, scripts, styles)
  if (url.pathname.match(/\.(png|jpg|jpeg|gif|svg|ico|webp|js|css|woff|woff2)$/)) {
    event.respondWith(
      caches.match(request)
        .then(cached => {
          if (cached) {
            // Return cached version, but also fetch fresh in background
            fetch(request)
              .then(response => {
                if (response.ok) {
                  caches.open(STATIC_CACHE)
                    .then(cache => cache.put(request, response))
                    .catch(() => {});
                }
              })
              .catch(() => {});
            return cached;
          }
          
          // No cache - fetch and cache
          return fetch(request)
            .then(response => {
              if (response.ok) {
                const responseClone = response.clone();
                caches.open(STATIC_CACHE)
                  .then(cache => cache.put(request, responseClone))
                  .catch(() => {});
              }
              return response;
            });
        })
    );
    return;
  }
  
  // Handle API requests - network first
  if (url.pathname.startsWith('/api/')) {
    event.respondWith(
      fetch(request)
        .then(response => {
          // Cache successful GET requests for cacheable routes
          if (response.ok && CACHEABLE_API_ROUTES.some(route => url.pathname.includes(route))) {
            const responseClone = response.clone();
            caches.open(DYNAMIC_CACHE)
              .then(cache => cache.put(request, responseClone))
              .catch(() => {});
          }
          return response;
        })
        .catch(() => {
          // Try cache for cacheable routes
          return caches.match(request);
        })
    );
    return;
  }
  
  // Default: network first with cache fallback
  event.respondWith(
    fetch(request)
      .then(response => response)
      .catch(() => caches.match(request))
  );
});

// Handle messages from the app
self.addEventListener('message', (event) => {
  if (event.data && event.data.type === 'SKIP_WAITING') {
    self.skipWaiting();
  }
  
  if (event.data && event.data.type === 'CLEAR_CACHE') {
    caches.keys().then(names => {
      names.forEach(name => caches.delete(name));
    });
  }
});
