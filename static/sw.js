// SICH - service worker: permite instalar la app y muestra una pantalla
// clara cuando no hay internet. Los datos (herramientas, movimientos) NUNCA se
// guardan en el teléfono: siempre se piden al servidor para que estén al día.

var VERSION = 'sich-v4';
var ARCHIVOS_FIJOS = [
  '/sin-conexion',
  '/static/estilos.css?v=4',
  '/static/sich.js?v=4',
  '/static/iconos/icono-192.png',
  '/static/iconos/icono-512.png'
];

self.addEventListener('install', function (evento) {
  evento.waitUntil(
    caches.open(VERSION).then(function (cache) { return cache.addAll(ARCHIVOS_FIJOS); })
  );
  self.skipWaiting();
});

self.addEventListener('activate', function (evento) {
  // Borra las copias de versiones anteriores.
  evento.waitUntil(
    caches.keys().then(function (nombres) {
      return Promise.all(nombres.filter(function (n) { return n !== VERSION; })
        .map(function (n) { return caches.delete(n); }));
    })
  );
  self.clients.claim();
});

self.addEventListener('fetch', function (evento) {
  var pedido = evento.request;
  if (pedido.method !== 'GET') { return; }   // los formularios siempre van al servidor
  var url = new URL(pedido.url);
  if (url.origin !== self.location.origin) { return; }

  // Páginas: siempre del servidor; si no hay internet, la pantalla "Sin conexión".
  if (pedido.mode === 'navigate') {
    evento.respondWith(fetch(pedido).catch(function () {
      return caches.match('/sin-conexion');
    }));
    return;
  }

  // Estilos, script e íconos: primero la copia guardada (carga instantánea).
  if (url.pathname.indexOf('/static/') === 0) {
    evento.respondWith(caches.match(pedido).then(function (copia) {
      return copia || fetch(pedido).then(function (respuesta) {
        var duplicado = respuesta.clone();
        caches.open(VERSION).then(function (cache) { cache.put(pedido, duplicado); });
        return respuesta;
      });
    }));
  }
});
