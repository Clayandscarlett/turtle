const CACHE = 'saulteaux-art-preview-v3';
const CORE = [
  './', './index.html', './manifest.webmanifest', './sw.js',
  './assets/master/turtle-island-gba-style.png',
  './assets/characters/makwa-walk-sheet-gba.png',
  './assets/characters/eagle-prompt-sheet-gba.png',
  './assets/characters/eagle-flying-sheet-gba.png',
  './assets/objects/object-atlas-01-gba.png',
  './assets/objects/object-atlas-02-gba.png',
  './assets/objects/object-atlas-03-gba.png',
  './assets/objects/object-atlas-04-gba.png',
  './assets/water/ocean-wave-cycle-8frames-gba.png',
  './assets/worlds/world-01-shoreline-zoom.png',
  './assets/worlds/world-02-forest-zoom.png',
  './assets/worlds/world-03-meadow-zoom.png',
  './assets/worlds/world-04-wetland-zoom.png',
  './assets/worlds/world-05-berry-garden-zoom.png',
  './assets/worlds/world-06-home-craft-zoom.png',
  './assets/worlds/world-07-teaching-grove-zoom.png',
  './assets/water/frames/frame-00.png', './assets/water/frames/frame-01.png',
  './assets/water/frames/frame-02.png', './assets/water/frames/frame-03.png',
  './assets/water/frames/frame-04.png', './assets/water/frames/frame-05.png',
  './assets/water/frames/frame-06.png', './assets/water/frames/frame-07.png'
];
self.addEventListener('install', (event) => {
  event.waitUntil(caches.open(CACHE).then((cache) => cache.addAll(CORE)).then(() => self.skipWaiting()));
});
self.addEventListener('activate', (event) => {
  event.waitUntil(caches.keys().then((keys) => Promise.all(keys.filter((key) => key !== CACHE).map((key) => caches.delete(key)))).then(() => self.clients.claim()));
});
self.addEventListener('fetch', (event) => {
  event.respondWith(caches.match(event.request).then((cached) => cached || fetch(event.request).then((response) => {
    const copy = response.clone();
    caches.open(CACHE).then((cache) => cache.put(event.request, copy));
    return response;
  })));
});
