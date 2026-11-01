# SICH — Sistema de Control de Herramientas

**Proyecto Fase 4: Validación y presentación de la solución**
Grupo No. 10 · Expediente-001 · Algoritmos y Programación Básica · Universidad del Valle de Guatemala
Empresa del caso: Nivela Obras Civiles, S.A.

Integrantes: Jaime Sebastián Duarte Tejada (26346), José Carlos Ipiña León (26284),
Julián Alejandro Flores Villatoro (26675), Jesús David Reynoso Beteta (261295).

SICH registra y consulta dónde está cada herramienta, quién la tiene, cuándo vuelve y en qué
estado está. Se puede buscar por código oficial, nombre o apodo: «bailarina», «la makita azul»
o «COR-01» encuentran la herramienta sin memorizar códigos.

---

## 1. Requisitos

- **Python 3.10 o superior** (probado con 3.13 y 3.14).
- **Consola** (`main.py`): solo la biblioteca estándar; no hay que instalar nada.
- **Página web** (`app.py`): necesita Flask.

## 2. Cómo ejecutar

Abra una terminal **dentro de esta carpeta**. En Windows use `py`; en macOS/Linux, `python3`.
En muchas computadoras con Windows, `python` abre la Microsoft Store en lugar de ejecutar Python.

**Menú de consola:**

```bash
py main.py
```

**Página web:**

```bash
py -m pip install -r requirements.txt
py app.py
```

Deje esa terminal abierta y entre a **http://127.0.0.1:5000**. Para detenerla: `Ctrl + C`.
Para abrirla desde un celular en la misma red Wi-Fi: `py app.py --red`.

**Pruebas automáticas** (usan una copia temporal; no modifican `datos/`):

```bash
py pruebas.py
```

```bash
py pruebas_web.py
```

Resultado esperado: 56 de 56 casos de consola y 22 de 22 pruebas web. `pruebas.py` deja la
transcripción de cada caso en `evidencias/`.

**Volver a los datos de demostración:** `py main.py --reiniciar`

## 3. Credenciales de demostración

Funcionan en la copia local. La versión publicada en internet las rechaza a propósito.

| Usuario | Contraseña | Rol | Puede usar |
|---|---|---|---|
| `jpivaral` | `bodega123` | Encargado de bodega | 1.1–1.3, 2.1, 2.2, 2.4, 2.5, 2.8, 3.1–3.6 |
| `ecifuentes` | `residente123` | Residente de obra | 2.3, 2.4, 2.6, 2.7, 3.1–3.6 |
| `prodas` | `gerente123` | Gerente de operaciones | 3.1–3.6 (solo consulta) |
| `esantos` | `maestro123` | Maestro de obra (obra EUC-022) | 2.4, 2.7, 3.1, 3.4 (solo su obra) |

**Cuenta de propietario (solo en la página web):** puede usar todo y además crear cuentas,
restablecer contraseñas y desactivar accesos. La primera vez, entre a **Configurar propietario**
desde la página de inicio de sesión. El código de configuración está en
`datos/codigo_configuracion.txt` (se crea al abrir esa página) o en los registros del servidor.

## 4. Funcionalidades

```
INICIAR SESIÓN → MENÚ PRINCIPAL
  1. Catálogo de herramientas
       1.1 Registrar herramienta · 1.2 Asociar apodos · 1.3 Modificar herramienta
  2. Movimientos de herramientas
       2.1 Registrar salida · 2.2 Registrar devolución · 2.3 Registrar traslado
       2.4 Reportar daño · 2.5 Registrar revisión · 2.6 Autorizar permanencia en obra
       2.7 Confirmar recepción en obra · 2.8 Registrar mantenimiento
  3. Consultas y seguimiento
       3.1 Buscar herramienta · 3.2 Consultar disponibles · 3.3 Devoluciones pendientes
       3.4 Herramientas por obra · 3.5 Historial de una herramienta
       3.6 Estado de mantenimiento
  9. Cerrar sesión   0. Salir
```

| Opción | Qué hace | Reglas principales |
|---|---|---|
| 1.1 Registrar | Agrega una herramienta en Bodega, con su ficha técnica y sus horas entre mantenimientos | Código único (también sin guion) que no sea apodo de otra; nunca nace «asignada»; empieza en 0 horas |
| 1.2 Asociar apodos | Liga nombres cotidianos al código | Sin repetidos en la misma herramienta; avisa si otra herramienta usa el mismo apodo |
| 1.3 Modificar | Cambia nombre, categoría, marca, motor/cable, ficha, horas entre mantenimientos, observaciones | El código no cambia; solo permite dar de baja, o reactivar pasando por revisión |
| 2.1 Salida | De Bodega a una obra (`asignada`) | Solo si está `disponible`, en Bodega y sin mantenimiento vencido; obra activa; devolución posterior a la salida; fuera de 16:30–17:15 exige residente que autoriza |
| 2.2 Devolución | De la obra a Bodega y suma las horas de uso | Fecha no anterior a la salida; indica si llegó tarde; con daño o ruido/golpe/cable en equipos con motor queda en `requiere revisión` |
| 2.3 Traslado | De una obra a otra | Solo el residente; el origen sale de la ubicación actual; destino distinto |
| 2.4 Daño | Deja la herramienta `dañada` y bloqueada | Descripción de al menos 5 caracteres |
| 2.5 Revisión | `apta` → `disponible`; `no apta` → `en reparación` | Solo en Bodega y con daño o revisión pendiente |
| 2.6 Permanencia | Autorización escrita para quedarse en obra | Solo el residente; sitio con seguridad; sin cruces; mientras esté vigente no se marca vencida |
| 2.7 Recepción | Confirma quién recibió la herramienta en obra | El maestro solo en su obra; una sola vez por salida o traslado |
| 2.8 Mantenimiento | Vuelve el contador de horas a 0 y libera la herramienta | Solo en Bodega y con horas configuradas; queda en el historial |
| 3.1 Buscar | Por código, nombre, apodo, marca o categoría | Sin importar mayúsculas, tildes, artículos ni orden; tolera errores de escritura |
| 3.2 Disponibles | Lo que hay en Bodega listo para salir | Filtro opcional por categoría o texto |
| 3.3 Pendientes | Herramientas por devolver | De la más antigua a la más nueva; vencidas marcadas con su atraso |
| 3.4 Por obra | Equipos en una obra o en Bodega | El maestro solo consulta su obra |
| 3.5 Historial | Movimientos, daños y autorizaciones | En orden cronológico, con quién y cuándo registró |
| 3.6 Mantenimiento | Horas de uso de cada herramienta | De la más cercana a vencer a la más lejana; marca vencidas y próximas (desde 90%) |

En todas: las entradas inválidas muestran un mensaje y vuelven a pedir el dato; antes de guardar
se muestra un resumen y «¿Confirmar operación? (S/N)».

### Horas de uso y mantenimiento

Cada herramienta guarda las horas entre mantenimientos que indica su ficha técnica; 0 significa
que no aplica. Empieza en 0 y, al devolverla, suma el tiempo transcurrido desde la salida: de
7:00 a 19:00 son 12 horas, y se cuentan también las noches que pase en obra. Al llegar al límite,
SICH muestra la alarma y bloquea la salida hasta registrar el mantenimiento (2.8).

La ficha técnica tiene un resumen en texto y, en la página web, un archivo PDF, JPG o PNG de hasta 5 MB.

## 5. Datos

Están en `datos/` en formato JSON y se guardan después de cada operación confirmada:
`herramientas`, `obras`, `usuarios`, `movimientos`, `danos` y `autorizaciones`.

- La entrega incluye **datos de demostración** tomados del expediente.
- Si un archivo falta o está dañado, el programa lo recrea con esos datos y avisa; no se cierra.
- Las contraseñas no se guardan: se guarda una huella PBKDF2-SHA256 con sal, que no se puede revertir.
- Los archivos de fichas técnicas se guardan en `datos/fichas/`.
- La variable de entorno `SICH_DATOS` permite usar otra carpeta de datos.

| Para probar | Situación inicial |
|---|---|
| COM-01 | disponible (*bailarina*, *rana*) |
| COM-02 | requiere revisión por ruido raro; tiene historial y un daño |
| ROT-02 | asignada en EUC-022, devolución vencida; sin confirmar recepción |
| MEZ-01 | asignada en VN-014 (*trompo*) |
| NIV-LAS-01 | asignada en Z11-009 con permanencia autorizada hasta el 31/12/2026 |
| VIB-01 | requiere revisión (cinta en el cable) |
| PUL-03 | disponible (*cortadora de block*, *pulidora grande*, *la makita azul*, *COR-01*) |
| EXT-02 | dada de baja (*extensión naranja*) |
| MEZ-03 | 250 de 250 h: alarma de mantenimiento, no puede salir |
| MEZ-02 | 230 de 250 h: mantenimiento próximo |
| CIS-005 | obra inactiva |

## 6. Estructura

```
├── main.py               Consola: inicio de sesión → menú por rol
├── app.py                Página web (Flask); usa las mismas funciones de sich/
├── wsgi.py               Entrada para el servidor en internet
├── pruebas.py            Casos de consola y evidencias
├── pruebas_web.py        Pruebas de la página web
├── cambiar_contrasena.py Cambia una contraseña desde la terminal
├── PUBLICAR.md           Publicar en internet e instalar la app
├── requirements.txt      Dependencias
├── render.yaml           Configuración para Render
├── sich/
│   ├── datos.py          Cargar y guardar JSON, contraseñas, datos de demostración
│   ├── validaciones.py   Lectura y validación de entradas en consola
│   ├── autenticacion.py  Inicio de sesión y permisos por rol
│   ├── busqueda.py       Búsqueda por código, nombre o apodo
│   ├── catalogo.py       Lecturas de herramientas y obras
│   ├── herramientas.py   Módulo 1: registrar, asociar apodos, modificar
│   ├── movimientos.py    Módulo 2: salida, devolución, traslado, daño, revisión, permanencia, recepción
│   ├── consultas.py      Módulo 3: buscar, disponibles, pendientes, por obra, historial
│   ├── cuentas.py        Cuentas de usuario y propietario
│   └── menus.py          Menú principal y submenús de consola
├── templates/, static/   Página web e app instalable
└── datos/                Datos de demostración
```

## 7. Versión publicada e instalación en el teléfono

Vea [PUBLICAR.md](PUBLICAR.md). Sitio: https://proyectprog50.pythonanywhere.com —
Código: https://github.com/reynosodavid845-star/sich-nivela
