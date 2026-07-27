const CACHE_NAME = 'tatawaw-saulteaux-v4-standalone';
const ASSETS = [
  './index.html',
  './saulteaux-game-shell.html',
  './saulteaux-300-word-roster.csv',
  './manifest.webmanifest',
  './saulteaux-preview/assets/master/turtle-island-gba-style.png',
  './saulteaux-preview/assets/characters/makwa-walk-sheet-gba.png',
  './saulteaux-preview/assets/characters/eagle-flying-sheet-gba.png',
  './saulteaux-preview/assets/characters/eagle-prompt-sheet-gba.png',
  './saulteaux-preview/assets/objects/object-atlas-01-gba.png',
  './saulteaux-preview/assets/objects/object-atlas-02-gba.png',
  './saulteaux-preview/assets/objects/object-atlas-03-gba.png',
  './saulteaux-preview/assets/objects/object-atlas-04-gba.png',
  './saulteaux-preview/assets/water/frames/frame-00.png',
  './saulteaux-preview/assets/water/frames/frame-01.png',
  './saulteaux-preview/assets/water/frames/frame-02.png',
  './saulteaux-preview/assets/water/frames/frame-03.png',
  './saulteaux-preview/assets/water/frames/frame-04.png',
  './saulteaux-preview/assets/water/frames/frame-05.png',
  './saulteaux-preview/assets/water/frames/frame-06.png',
  './saulteaux-preview/assets/water/frames/frame-07.png'
];
self.addEventListener('install', event => {
  event.waitUntil(caches.open(CACHE_NAME).then(cache => cache.addAll(ASSETS)).then(() => self.skipWaiting()));
});
self.addEventListener('activate', event => {
  event.waitUntil(caches.keys().then(keys => Promise.all(keys.filter(key => key !== CACHE_NAME).map(key => caches.delete(key)))).then(() => self.clients.claim()));
});
self.addEventListener('fetch', event => {
  if (event.request.method !== 'GET') return;
  event.respondWith(caches.match(event.request).then(cached => cached || fetch(event.request).then(response => {
    const copy = response.clone(); caches.open(CACHE_NAME).then(cache => cache.put(event.request, copy)); return response;
  }).catch(() => caches.match('./saulteaux-game-shell.html'))));
});
