// SICH - ayudas de la página web. Si el navegador no ejecuta JavaScript, la página
// sigue funcionando igual: estas funciones solo hacen más cómodo el uso.

// Las mismas palabras de relleno que ignora busqueda.py.
var PALABRAS_IGNORADAS = ['el', 'la', 'los', 'las', 'un', 'una', 'unos', 'unas', 'de', 'del',
                          'al', 'y', 'con', 'para', 'por', 'en'];

// Quita tildes y pasa a minúsculas (igual que normalizar() en busqueda.py).
function normalizarTexto(texto) {
  return texto.normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase().trim();
}

// Filtra las opciones de un desplegable mientras se escribe (ej. "bailarina").
function prepararFiltros() {
  document.querySelectorAll('input.filtro').forEach(function (filtro) {
    var lista = document.getElementById(filtro.dataset.filtra);
    filtro.addEventListener('input', function () {
      var palabras = normalizarTexto(filtro.value).split(/\s+/).filter(function (p) {
        return PALABRAS_IGNORADAS.indexOf(p) === -1;
      });
      var primeraVisible = null;
      Array.from(lista.options).forEach(function (opcion) {
        var texto = normalizarTexto(opcion.textContent);
        var coincide = palabras.every(function (p) { return texto.indexOf(p) !== -1; });
        opcion.hidden = !coincide;
        if (coincide && primeraVisible === null) { primeraVisible = opcion; }
      });
      if (primeraVisible !== null && lista.selectedOptions[0].hidden) {
        primeraVisible.selected = true;
      }
    });
  });
}

// En "Registrar salida", el campo del residente solo aparece si la devolución
// queda fuera del horario normal de 16:30 a 17:15.
function prepararHorario() {
  var devolucion = document.getElementById('devolucion_esperada');
  var caja = document.getElementById('caja-residente_autoriza');
  var residente = document.getElementById('residente_autoriza');
  if (!devolucion || !caja) { return; }
  function revisar() {
    var hora = devolucion.value.slice(11, 16);
    var fuera = hora !== '' && (hora < '16:30' || hora > '17:15');
    caja.hidden = !fuera && residente.value === '';
    caja.classList.toggle('resaltado', fuera);
  }
  devolucion.addEventListener('input', revisar);
  revisar();
}

// Botón "Ver" para revisar la contraseña escrita.
function prepararVerContrasena() {
  document.querySelectorAll('[data-mostrar]').forEach(function (boton) {
    var campo = document.getElementById(boton.dataset.mostrar);
    boton.addEventListener('click', function () {
      var mostrar = campo.type === 'password';
      campo.type = mostrar ? 'text' : 'password';
      boton.textContent = mostrar ? 'Ocultar' : 'Ver';
      boton.setAttribute('aria-pressed', mostrar ? 'true' : 'false');
    });
  });
}

// Evita que un doble toque guarde dos veces el mismo movimiento.
function prepararEnvios() {
  document.querySelectorAll('form').forEach(function (formulario) {
    formulario.addEventListener('submit', function (evento) {
      if (formulario.dataset.enviado === 'si') { evento.preventDefault(); return; }
      formulario.dataset.enviado = 'si';
      var boton = evento.submitter;
      if (boton && boton.dataset.enviando) { boton.textContent = boton.dataset.enviando; }
    });
  });
}

// Lleva la vista a los errores para que se lean primero.
function enfocarErrores() {
  var errores = document.getElementById('errores');
  if (errores) { errores.focus(); }
}

// ---------- App instalable (PWA) ----------
var avisoDeInstalacion = null;   // el navegador lo entrega cuando la app se puede instalar

function yaEstaInstalada() {
  return window.matchMedia('(display-mode: standalone)').matches || window.navigator.standalone === true;
}

window.addEventListener('beforeinstallprompt', function (evento) {
  evento.preventDefault();
  avisoDeInstalacion = evento;
  ['boton-instalar', 'boton-instalar-grande'].forEach(function (id) {
    var boton = document.getElementById(id);
    if (boton) { boton.hidden = false; }
  });
});

window.addEventListener('appinstalled', function () {
  avisoDeInstalacion = null;
  ['boton-instalar', 'boton-instalar-grande'].forEach(function (id) {
    var boton = document.getElementById(id);
    if (boton) { boton.hidden = true; }
  });
  var aviso = document.getElementById('ya-instalada');
  if (aviso) { aviso.hidden = false; }
});

function prepararInstalacion() {
  ['boton-instalar', 'boton-instalar-grande'].forEach(function (id) {
    var boton = document.getElementById(id);
    if (!boton) { return; }
    if (avisoDeInstalacion) { boton.hidden = false; }
    boton.addEventListener('click', function () {
      if (!avisoDeInstalacion) { window.location.href = '/instalar'; return; }
      avisoDeInstalacion.prompt();
      avisoDeInstalacion = null;
    });
  });
  var aviso = document.getElementById('ya-instalada');
  if (aviso && yaEstaInstalada()) { aviso.hidden = false; }
  if ('serviceWorker' in navigator) {
    navigator.serviceWorker.register('/sw.js').catch(function () { /* sin PWA, la web funciona igual */ });
  }
}

document.addEventListener('DOMContentLoaded', function () {
  prepararInstalacion();
  prepararFiltros();
  prepararHorario();
  prepararVerContrasena();
  prepararEnvios();
  enfocarErrores();
});

// Si el usuario vuelve con el botón Atrás, se permite enviar de nuevo.
window.addEventListener('pageshow', function () {
  document.querySelectorAll('form').forEach(function (f) { f.dataset.enviado = ''; });
});
