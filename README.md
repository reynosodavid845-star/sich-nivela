# SICH — Sistema de Control de Herramientas

**Proyecto Fase 3: Implementación de la solución**
Grupo No. 10 · Expediente-001 · Algoritmos y Programación Básica · Universidad del Valle de Guatemala
Empresa del caso: Nivela Obras Civiles, S.A.

**App publicada:** https://sich-nivela.onrender.com (instalable en celulares y tablets;
ver `/instalar`). Código: https://github.com/reynosodavid845-star/sich-nivela

Integrantes: Jaime Sebastián Duarte Tejada (26346), José Carlos Ipiña León (26284),
Julián Alejandro Flores Villatoro (26675), Jesús David Reynoso Beteta (261295).

---

## 1. Versión de Python

- Probado con **Python 3.12.14** en Windows 11. Funciona con Python 3.10 o superior.
- La versión de consola (`main.py`) usa **solo la biblioteca estándar**: no hay que instalar nada.
- La versión web (`app.py`) necesita **Flask** (única dependencia externa).

## 2. Cómo ejecutar

> **Windows:** use `py` en lugar de `python`. En muchas computadoras con Windows, el comando
> `python` no ejecuta Python: abre la Microsoft Store (es un "alias de ejecución de
> aplicaciones"). `py` es el lanzador oficial que se instala junto con Python.
> En macOS/Linux use `python3`.

Abra la terminal **dentro de la carpeta `Fase3_Grupo10_Expediente-001`** (en el Explorador de
archivos: clic derecho dentro de la carpeta → *Abrir en Terminal*).

### Versión principal: menú de consola (la que se evalúa)

```bash
py main.py
```

### Versión web (opcional, usa la misma lógica)

```bash
py -m pip install -r requirements.txt
py app.py
```

Deje esa terminal abierta (el servidor tiene que seguir corriendo) y abra
**http://127.0.0.1:5000** en el navegador. Para detenerla presione `Ctrl + C`.

Para abrirla desde un celular o tablet conectado a la **misma red Wi-Fi**, use `py app.py --red`
y en el celular abra `http://IP-DE-LA-COMPUTADORA:5000`.

**Publicarla en internet e instalarla como app** en Android, iPhone o tablet: siga
[PUBLICAR.md](PUBLICAR.md).
Si el navegador dice que no puede conectarse, revise que la terminal muestre
`Running on http://127.0.0.1:5000` y que no haya un error en rojo.

### Pruebas automáticas

```bash
py pruebas.py
```

Ejecuta los 26 casos del módulo (CP-01 … CP-26) y los 8 de navegación (CN-01 … CN-08) sobre
una **copia temporal** de los datos (no modifica `datos/`). Guarda la transcripción de cada
caso en `evidencias/` y el resumen en `evidencias/resultados_pruebas.json`.

```bash
py pruebas_web.py
```

Ejecuta las 11 pruebas de la página web (W-01 … W-11) con el cliente de pruebas de Flask, también
sobre una copia temporal. Guarda el resultado en `evidencias/pruebas_web.txt`.

## 3. Dependencias

| Paquete | Para qué | Instalación |
|---|---|---|
| (ninguno) | Menú de consola `main.py` y `pruebas.py` | — |
| Flask ≥ 3.0 | Página web `app.py` | `pip install -r requirements.txt` |

## 4. Archivos de datos

Están en la carpeta `datos/` en formato JSON:

| Archivo | Contenido |
|---|---|
| `herramientas.json` | Catálogo de prueba (código, nombre, categoría, marca, estado, apodos, ubicación, responsable, devolución esperada) |
| `obras.json` | Bodega y obras VN-014, EUC-022, Z11-009 (activas) y CIS-005 (inactiva, para probar) |
| `usuarios.json` | Usuarios de prueba (la contraseña se guarda cifrada con SHA-256) |
| `movimientos.json` | Historial: salidas, devoluciones, traslados, daños, revisiones y permanencias |
| `danos.json` | Reportes de daño |
| `autorizaciones.json` | Autorizaciones de permanencia en obra (por escrito) |

- Se cargan al iniciar y se guardan **después de cada operación confirmada**.
- Si un archivo **falta o está dañado**, el programa lo vuelve a crear con los datos iniciales
  y muestra un aviso (no se cierra).
- **Reiniciar los datos de prueba:** `py main.py --reiniciar` (o borre los archivos de `datos/`).

Todos los registros precargados tienen el campo `"origen": "Dato de prueba precargado (el Módulo 1 -
Catálogo está pendiente)"`. Se usan porque el Módulo 1 (Catálogo) se programará en la Fase 4;
no reemplazan ninguna lógica del Módulo 2.

## 5. Usuarios de prueba

| Usuario | Contraseña (solo prueba) | Rol | Puede usar |
|---|---|---|---|
| `jpivaral` | `bodega123` | Encargado de bodega (Julián Pivaral) | 1.x, 2.1, 2.2, 2.4, 2.5, 3.x |
| `ecifuentes` | `residente123` | Residente de obra (Ing. Esteban Cifuentes) | 2.3, 2.4, 2.6, 3.x |
| `prodas` | `gerente123` | Gerente de operaciones (Ing. Pamela Rodas) | 3.x (solo consulta) |
| `esantos` | `maestro123` | Maestro de obra (Erick Santos, obra EUC-022) | 2.4, 3.1, 3.4 |

Tiene **3 intentos** para iniciar sesión. Después de cada error puede reintentar (S) o salir (N).

## 6. Menú y estado de las funcionalidades

```
INICIAR SESIÓN → MENÚ PRINCIPAL
  1. Catálogo de herramientas   1.1 Registrar [pendiente] · 1.2 Asociar apodos [pendiente] · 1.3 Modificar [pendiente]
  2. Movimientos de herramientas (MÓDULO IMPLEMENTADO COMPLETO)
       2.1 Registrar salida · 2.2 Registrar devolución · 2.3 Registrar traslado
       2.4 Reportar daño · 2.5 Registrar revisión · 2.6 Autorizar permanencia en obra
  3. Consultas y seguimiento    3.1 Buscar herramienta [implementada]
       3.2 Disponibles · 3.3 Devoluciones pendientes · 3.4 Por obra · 3.5 Historial [pendientes]
  9. Cerrar sesión   0. Salir
```

- Opción inválida (letras, vacío o número fuera de rango): *"Opción no válida, intente de nuevo"*.
- Opción pendiente: *"Funcionalidad pendiente de implementación"* y vuelve al submenú.
- Opción sin permiso para el rol: *"No tiene permisos para esta opción"*.
- Después de cada operación: *"Presione Enter para volver al menú"*.
- Antes de guardar cualquier movimiento: resumen y *"¿Confirmar operación? (S/N)"*.

### Módulo implementado: 2. Movimientos de herramientas

| Opción | Qué hace | Reglas principales |
|---|---|---|
| 2.1 Registrar salida | La herramienta pasa de Bodega a una obra (estado `asignada`) | Solo sale si está `disponible` y en Bodega; obra existente y activa; responsable obligatorio; devolución posterior a la salida; fuera de 16:30–17:15 pide el residente que autorizó |
| 2.2 Registrar devolución | La herramienta vuelve a Bodega | Solo si está en una obra; fecha no anterior a la salida; indica si llegó tarde; `con daño` → `requiere revisión` y ofrece reportar el daño; equipo con motor/cable con "ruido", "golpe" o "cable" → `requiere revisión` (memorando 14/02/2026) |
| 2.3 Registrar traslado | Cambia la herramienta de una obra a otra sin pasar por bodega | Solo el residente; muestra la obra de origen (no se escribe); destino existente, activo y distinto del origen |
| 2.4 Reportar daño | Registra el daño y deja la herramienta `dañada` (bloqueada) | Descripción de al menos 5 caracteres; responsable obligatorio; no aplica a herramientas dadas de baja |
| 2.5 Registrar revisión | `apta` → `disponible`; `no apta` → `en reparación` | Solo herramientas dañadas, en reparación o que requieren revisión, y que estén en Bodega |
| 2.6 Autorizar permanencia | Deja por escrito que la herramienta puede quedarse en la obra | Solo el residente; herramienta asignada a esa obra; fin posterior al inicio; sin seguridad se rechaza; no permite autorizaciones que se crucen; mientras esté vigente no se marca como vencida |

La búsqueda (usada por todas las opciones) acepta **código, nombre o apodo** y se adapta a
cómo habla el personal:

- No importan mayúsculas ni tildes: `La BailaRína` = `bailarina`.
- Ignora artículos y palabras de relleno (`la`, `el`, `de`, `con`…): `la makita azul` = `makita azul`.
- Busca palabra por palabra y en cualquier orden: `azul makita` → PUL-03.
- Revisa también la marca y la categoría: `bosch` → rotomartillos y niveles Bosch.
- Reconoce códigos sin guion: `com02` → COM-02.
- Tolera errores de escritura y avisa que el resultado es aproximado: `bailarna`, `conpactadora`.

Ejemplos: `bailarina` → COM-01 y COM-02 (pide elegir), `COR-01` → PUL-03,
`la extensión naranja` → EXT-02.

### Página web (`app.py`)

- Tablero con 4 tarjetas (disponibles, asignadas, pendientes vencidas, dañadas/en revisión).
- **Accesos rápidos según el rol** ("Sacar herramienta a obra", "Recibir herramienta en bodega",
  "Trasladar entre obras"…), además del menú completo 1, 2, 3, 9 y 0.
- Barra de búsqueda siempre visible; en cada resultado aparecen solo los botones que el rol puede usar.
- Formularios cortos con valores por defecto, filtro para la lista de herramientas y el campo
  del residente solo cuando la devolución queda fuera de 16:30–17:15.
- Resumen y "¿Confirmar operación?" antes de guardar; protección contra doble toque.
- Seguridad básica: token en cada formulario, cookie de sesión `SameSite=Lax`, 3 intentos de
  inicio de sesión y luego 5 minutos de espera.
- Páginas de error claras (dirección inexistente, sesión vencida) que permiten seguir navegando.
- Móvil primero, letra grande, alto contraste, foco visible para teclado y estados con texto
  (no solo color).
- **Celulares y tablets:** áreas táctiles de 48 px, respeta la muesca del teléfono; en tablet
  usa 4 tarjetas por fila, menú en 2 columnas y resultados en 2 columnas en horizontal.
- **App instalable (PWA):** se instala desde Chrome (Android/computadora) o Safari (iPhone/iPad)
  con su ícono, abre a pantalla completa, tiene accesos directos (Buscar, Salida, Devolución) y
  muestra una pantalla clara si no hay internet. Instrucciones en `/instalar`.
- **Lista para publicar:** `wsgi.py`, contraseñas de prueba bloqueadas en la versión publicada,
  `cambiar_contrasena.py` y bloqueo de intentos por dirección IP. Ver [PUBLICAR.md](PUBLICAR.md).

## 7. Datos de prueba importantes

| Código | Situación inicial | Sirve para probar |
|---|---|---|
| COM-01 | disponible (apodos *bailarina*, *rana*) | salida válida, apodo ambiguo |
| COM-02 | requiere revisión (ruido raro) | salida bloqueada, revisión apta |
| ROT-02 | asignada en EUC-022, devolución 14/10/2026 17:00 (**vencida**) | devolución tardía |
| MEZ-01 | asignada en VN-014 (apodo *trompo*) | traslado, devolución con daño, permanencia |
| NIV-LAS-01 | asignada en Z11-009 con autorización vigente hasta 31/12/2026 | no aparece vencida, autorización duplicada |
| VIB-01 | requiere revisión (cinta en el cable) | revisión no apta |
| PUL-03 | disponible (*cortadora de block*, *pulidora grande*, *la makita azul*, *COR-01*) | reporte de daño por apodo |
| EXT-02 | dada de baja (*extensión naranja*) | salida bloqueada |
| CIS-005 | obra inactiva | obra no válida |

## 8. Cómo reproducir cada caso de prueba a mano

Antes de cada caso ejecute `py main.py --reiniciar`. Las entradas se escriben en orden;
"Enter" significa presionar Enter sin escribir nada.

| Caso | Usuario | Entradas |
|---|---|---|
| CP-01 | jpivaral | 2 → 1 → `bailarina` → 1 → `VN-014` → `Erick Santos` → `16/10/2026 06:15` → `16/10/2026 17:00` → Enter → S |
| CP-02 | jpivaral | 2 → 1 → `COM-02` |
| CP-03 | jpivaral | 2 → 1 → `extension naranja` |
| CP-04 | jpivaral | 2 → 1 → `ABC-99` → `rotomartillo` → 1 → `CIS-005` → `XYZ-1` → `EUC-022` → Enter → `Luis Aguilar` → `32/13/2026 25:00` → `16/10/2026 06:15` → `16/10/2026 05:00` → `16/10/2026 19:00` → N → `16/10/2026 19:00` → S → `Ing. Esteban Cifuentes` → Enter → S |
| CP-05 | jpivaral | 2 → 1 → `rana` → `Z11-009` → `Erick Santos` → `16/10/2026 06:15` → `16/10/2026 17:00` → Enter → N |
| CP-06 | jpivaral | 2 → 2 → `ROT-02` → `16/10/2026 16:45` → 1 → Enter → S |
| CP-07 | jpivaral | 2 → 2 → `MEZ-02` |
| CP-08 | jpivaral | 2 → 2 → `trompo` → `15/10/2026 08:00` → `16/10/2026 16:40` → 2 → `Manija quebrada` → S → S → `Manija quebrada al descargar` → `16/10/2026 16:40` → `Luis Aguilar` → S |
| CP-09 | jpivaral | 2 → 2 → `ROT-02` → `16/10/2026 16:50` → 1 → `Hace ruido raro` → S |
| CP-10 | ecifuentes | 2 → 3 → `MEZ-01` → `Z11-009` → `Erick Santos` → Enter → S |
| CP-11 | ecifuentes | 2 → 3 → `MEZ-01` → `VN-014` → `EUC-022` → `Luis Aguilar` → Enter → N |
| CP-12 | jpivaral | 2 → 3 |
| CP-13 | ecifuentes | 2 → 3 → `COM-01` |
| CP-14 | esantos | 2 → 4 → `la makita azul` → `Disco con fisura y cable pelado` → `16/10/2026 10:00` → `Erick Santos` → S |
| CP-15 | esantos | 2 → 4 → `COR-01` → `mal` → `Se quebró el disco` → Enter → Enter → `Erick Santos` → N |
| CP-16 | jpivaral | 2 → 5 → `bailarina grande` → 1 → `Julián Pivaral` → `Motor sin ruido después de limpieza` → S |
| CP-17 | jpivaral | 2 → 5 → `vibrador` → 2 → `Julián Pivaral` → `Cable expuesto` → S |
| CP-18 | jpivaral | 2 → 5 → `MEZ-02` |
| CP-19 | ecifuentes | 2 → 6 → `MEZ-01` → `16/10/2026 17:00` → `19/10/2026 06:15` → S → `Cliente tiene garita` → S |
| CP-20 | ecifuentes | 2 → 6 → `ROT-02` → `16/10/2026 17:00` → `17/10/2026 06:15` → N |
| CP-21 | ecifuentes | 2 → 6 → `ROT-02` → `16/10/2026 17:00` → `15/10/2026 06:15` → `17/10/2026 06:15` → S → Enter → N |
| CP-22 | ecifuentes | 2 → 6 → `nivel` → 1 → `16/10/2026 17:00` → `17/10/2026 06:15` → S → Enter → S |
| CP-23 | esantos | 3 → 1 → `Makita Azul` → S → `RANA` → S → `xyz` → N |
| CP-24 | jpivaral | Escriba texto inválido en `datos/herramientas.json` y ejecute `py main.py` |
| CP-25 | jpivaral | Borre `datos/movimientos.json` y ejecute `py main.py` |
| CP-26 | — | Lo ejecuta `py pruebas.py` llamando directamente a `registrar_salida()` |
| CN-01 | jpivaral | 1 → 0 → 2 → 0 → 3 → 0 → 0 |
| CN-02 | jpivaral | `a` → Enter → `7` → 2 → `9` → `x` → 0 → 0 |
| CN-03 | jpivaral | 1 → 1, 2, 3 → 0 → 3 → 2, 3, 4, 5 → 0 → 0 |
| CN-04 | prodas | 2 → 1 → Enter → 6 → Enter → 0 → 1 → 2 → Enter → 0 → 0 |
| CN-05 | — | `jpivaral` / `claveequivocada` → S → `jpivaral` / `bodega123` → 0 |
| CN-06 | — | `pedro` / `1234` tres veces (S entre intentos) |
| CN-07 | jpivaral | 9 → iniciar como `ecifuentes` → 0 |
| CN-08 | — | `jpivaral` / `otra` → N |

## 9. Estructura del proyecto

```
Fase3_Grupo10_Expediente-001/
├── main.py               Punto de entrada de consola (login → menú por rol)
├── app.py                Punto de entrada web (Flask) – usa las mismas funciones
├── pruebas.py            Casos de prueba automáticos de consola + evidencias
├── pruebas_web.py        Pruebas automáticas de la página web
├── wsgi.py               Entrada para el servidor en internet (PythonAnywhere)
├── cambiar_contrasena.py Cambia la contraseña de un usuario (obligatorio antes de publicar)
├── PUBLICAR.md           Guía para publicar e instalar la app en teléfonos y tablets
├── requirements.txt      Flask
├── sich/
│   ├── datos.py          Cargar/guardar JSON, datos iniciales de prueba
│   ├── validaciones.py   leer_opcion, leer_texto_no_vacio, leer_fecha_hora, confirmar…
│   ├── autenticacion.py  iniciar_sesion, permisos por rol
│   ├── busqueda.py       buscar_herramienta por código, nombre o apodo
│   ├── menus.py          Menú principal, submenús y opciones pendientes
│   ├── catalogo.py       Módulo 1 (pendiente; solo lecturas que usa el Módulo 2)
│   ├── movimientos.py    Módulo 2 — IMPLEMENTADO COMPLETO
│   └── consultas.py      Módulo 3 (3.1 implementada; 3.2–3.5 pendientes)
├── templates/, static/   Página web (HTML, estilos.css, sich.js, sw.js, manifest, íconos)
├── datos/                Archivos JSON de prueba
├── diagramas/            Código Mermaid de los diagramas de flujo
└── evidencias/           Transcripciones generadas por pruebas.py
```

## 10. Funcionalidades pendientes (Fase 4)

- Módulo 1: 1.1 Registrar herramienta, 1.2 Asociar apodos, 1.3 Modificar herramienta.
- Módulo 3: 3.2 Consultar disponibles, 3.3 Devoluciones pendientes, 3.4 Herramientas por obra,
  3.5 Historial.
- Confirmación de recepción por el maestro de obra.
