const CACHE = 'wisemarket-v2'
const STATIC = [
  '/',
  '/index.html',
  '/manifest.json',
]

self.addEventListener('install', e => {
  e.waitUntil(
    caches.open(CACHE).then(c => c.addAll(STATIC))
  )
  self.skipWaiting()
})

self.addEventListener('activate', e => {
  e.waitUntil(
    caches.keys().then(keys =>
      Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k)))
    )
  )
  self.clients.claim()
})

self.addEventListener('fetch', e => {
  const url = new URL(e.request.url)

  // Network first for API calls
  if (url.pathname.startsWith('/api/') || url.port === '8000') {
    e.respondWith(
      fetch(e.request).catch(() =>
        new Response(JSON.stringify({ error: 'offline', message: 'No connection' }),
          { headers: { 'Content-Type': 'application/json' } })
      )
    )
    return
  }

  // Only GET requests can be cached
  if (e.request.method !== 'GET') return

  // Network first for pages, so a new deploy is picked up straight away
  // (a cached index.html would point to old, deleted asset files)
  if (e.request.mode === 'navigate') {
    e.respondWith(
      fetch(e.request).then(resp => {
        const clone = resp.clone()
        caches.open(CACHE).then(c => c.put('/index.html', clone))
        return resp
      }).catch(() => caches.match('/index.html'))
    )
    return
  }

  // Cache first for static assets (their file names change on every build)
  e.respondWith(
    caches.match(e.request).then(cached => {
      if (cached) return cached
      return fetch(e.request).then(resp => {
        if (resp.ok) {
          const clone = resp.clone()
          caches.open(CACHE).then(c => c.put(e.request, clone))
        }
        return resp
      }).catch(() => caches.match('/'))
    })
  )
})
