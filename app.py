"""SICH - versión web sencilla (Flask).

Usa exactamente las mismas funciones de lógica que la consola (sich/), por lo
que las reglas de negocio no se repiten aquí: esta capa solo lee el
formulario, llama a validar_xxx / registrar_xxx y muestra el resultado.

Ejecutar:  py -m pip install -r requirements.txt   y luego   py app.py
Abrir:     http://127.0.0.1:5000
"""

import os
import secrets
import time
from datetime import datetime, timedelta

from flask import Flask, flash, redirect, render_template, request, send_from_directory, \
    session, url_for

from sich import movimientos
from sich.autenticacion import MAXIMO_INTENTOS, MENSAJE_SIN_PERMISO, NOMBRES_ROL, \
    tiene_permiso, verificar_credenciales
from sich.busqueda import buscar_con_detalle
from sich.catalogo import descripcion_corta, nombre_obra, obras_activas, obtener_herramienta
from sich.consultas import detalle_herramienta, resumen_tablero
from sich.datos import cargar_datos, cifrar_contrasena, guardar_datos, usuarios_iniciales
from sich.menus import MENSAJE_PENDIENTE, MENU_PRINCIPAL, SUBMENUS, esta_implementada

app = Flask(__name__)

# Al publicar en internet (HTTPS) se define SICH_PUBLICO=1 (wsgi.py lo hace solo):
# la cookie solo viaja cifrada y las contraseñas de prueba dejan de funcionar.
PUBLICO = os.environ.get("SICH_PUBLICO", "") == "1"

# Clave secreta de la sesión. Publicado, si no se configuró SICH_CLAVE se inventa una al azar
# (nadie la conoce; solo hace que las sesiones se cierren si el servidor se reinicia).
if os.environ.get("SICH_CLAVE"):
    app.secret_key = os.environ["SICH_CLAVE"]
elif PUBLICO:
    app.secret_key = secrets.token_hex(32)
else:
    app.secret_key = "sich-grupo10-solo-pruebas"
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"        # la cookie no viaja desde otros sitios
app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 3600       # el navegador guarda CSS y JS por 1 hora
app.config["SESSION_COOKIE_SECURE"] = PUBLICO
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(hours=12)   # un turno de trabajo

VERSION_ESTATICOS = "4"          # cambiarla obliga al navegador a bajar el CSS/JS nuevo
FORMATO_WEB = "%Y-%m-%dT%H:%M"   # formato de <input type="datetime-local">
MINUTOS_BLOQUEO = 5              # espera después de 3 intentos fallidos de inicio de sesión
CARPETA_ESTATICA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")

# Contraseñas de prueba (están en el README): no se aceptan en la versión publicada.
CONTRASENAS_DE_PRUEBA = [u["contrasena"] for u in usuarios_iniciales()]

# Intentos fallidos por dirección IP: así borrar las cookies no da más intentos.
# Formato: {ip: [intentos, bloqueado_hasta]}
INTENTOS_POR_IP = {}


def aplicar_contrasenas_de_entorno():
    """Toma las contraseñas reales de variables de entorno secretas del hosting.

    Ejemplo: SICH_CONTRASENA_JPIVARAL=... cambia la contraseña de jpivaral. Sirve en
    hostings como Render, donde los archivos vuelven a los datos iniciales al reiniciarse:
    cada vez que arranca, SICH vuelve a aplicar las contraseñas. Así nunca se escriben en
    el código ni en GitHub. Devuelve cuántas contraseñas se aplicaron.
    """
    datos, avisos = cargar_datos()
    aplicadas = 0
    for usuario in datos["usuarios"]:
        contrasena = os.environ.get("SICH_CONTRASENA_" + usuario["usuario"].upper(), "")
        if contrasena != "":
            usuario["contrasena"] = cifrar_contrasena(contrasena)
            aplicadas = aplicadas + 1
    if aplicadas > 0:
        guardar_datos(datos)
    return aplicadas


aplicar_contrasenas_de_entorno()

PERSONAL = ["Erick Santos", "Luis Aguilar", "Julián Pivaral", "Ing. Esteban Cifuentes"]

# Botones grandes del inicio: lo más usado por cada rol, a un solo toque.
ACCESOS_RAPIDOS = [
    ("2.1", "Sacar herramienta a obra"),
    ("2.2", "Recibir herramienta en bodega"),
    ("2.3", "Trasladar entre obras"),
    ("2.6", "Autorizar que se quede en obra"),
    ("2.4", "Reportar daño"),
    ("2.5", "Registrar revisión"),
]


# ------------------------------------------------- seguridad de formularios

def token_formulario():
    """Token secreto de la sesión que deben traer todos los formularios POST."""
    if "token" not in session:
        session["token"] = secrets.token_hex(16)
    return session["token"]


@app.context_processor
def variables_comunes():
    """Variables disponibles en todas las plantillas."""
    return {"token": token_formulario(), "version": VERSION_ESTATICOS}


@app.before_request
def revisar_token():
    """Rechaza formularios que no vienen de SICH o que se reenviaron desde una página vieja."""
    enviado = request.form.get("token", "")
    if request.method == "POST" and (enviado == "" or enviado != session.get("token")):
        return render_template("mensaje.html", usuario=None, titulo="La página expiró",
                               mensaje="Esta página estuvo abierta mucho tiempo o se envió dos "
                                       "veces. No se guardó nada: vuelva a intentarlo.",
                               tipo="error"), 400
    return None


@app.errorhandler(404)
def pagina_no_encontrada(error):
    """Dirección que no existe: mensaje claro en vez de un error técnico."""
    return render_template("mensaje.html", usuario=None, titulo="Página no encontrada",
                           mensaje="Esa dirección no existe en SICH. Use el botón para volver "
                                   "al menú.", tipo="error"), 404


@app.errorhandler(500)
def error_interno(error):
    """Cualquier falla inesperada muestra un mensaje y permite seguir navegando."""
    return render_template("mensaje.html", usuario=None, titulo="Algo salió mal",
                           mensaje="Ocurrió un problema y no se guardó la operación. Vuelva al "
                                   "menú e inténtelo de nuevo.", tipo="error"), 500


# ---------------------------------------------------------------- utilidades

def ir_a_login():
    """Envía al inicio de sesión avisando por qué."""
    if request.path != "/":
        flash("Inicie sesión para continuar.", "aviso")
    return redirect(url_for("login"))

def usuario_actual(datos):
    """Devuelve el usuario con sesión iniciada, o None."""
    nombre = session.get("usuario")
    for usuario in datos["usuarios"]:
        if usuario["usuario"] == nombre:
            return usuario
    return None


def leer_fecha_web(texto):
    """Convierte el valor de un campo datetime-local a datetime (None si es inválido)."""
    try:
        return datetime.strptime(texto, FORMATO_WEB)
    except (ValueError, TypeError):
        return None


def fecha_web(fecha):
    """Convierte un datetime al formato de un campo datetime-local."""
    return fecha.strftime(FORMATO_WEB)


def pagina_mensaje(datos, usuario, titulo, mensaje, tipo="aviso"):
    """Muestra una página con un mensaje y el botón para volver al menú."""
    return render_template("mensaje.html", usuario=usuario, rol=NOMBRES_ROL[usuario["rol"]],
                           titulo=titulo, mensaje=mensaje, tipo=tipo)


def opciones_herramientas(herramientas, codigo_elegido, datos):
    """Lista (valor, texto) para un desplegable de herramientas."""
    opciones = []
    codigos = []
    for herramienta in herramientas:
        opciones.append((herramienta["codigo"], descripcion_corta(herramienta)))
        codigos.append(herramienta["codigo"])
    elegida = obtener_herramienta(datos, codigo_elegido or "")
    if elegida is not None and elegida["codigo"] not in codigos:
        opciones.insert(0, (elegida["codigo"], descripcion_corta(elegida)))
    return opciones


def opciones_obras(datos):
    """Lista (valor, texto) de obras activas para un desplegable."""
    opciones = []
    for obra in obras_activas(datos):
        opciones.append((obra["codigo"], obra["codigo"] + " - " + obra["nombre"]))
    return opciones


# ------------------------------------------------- formularios del Módulo 2

def campos_de_operacion(datos, id_opcion, valores):
    """Devuelve la lista de campos del formulario de una operación del Módulo 2."""
    ahora = movimientos.momento_actual(None)
    codigo = valores.get("codigo", "")
    if id_opcion == "2.1":
        return [
            {"nombre": "codigo", "etiqueta": "Herramienta", "tipo": "select",
             "opciones": opciones_herramientas(movimientos.herramientas_disponibles_en_bodega(datos),
                                               codigo, datos)},
            {"nombre": "codigo_obra", "etiqueta": "Obra de destino", "tipo": "select",
             "opciones": opciones_obras(datos)},
            {"nombre": "responsable", "etiqueta": "Responsable que la recibe", "tipo": "texto"},
            {"nombre": "fecha_salida", "etiqueta": "Fecha y hora de salida", "tipo": "fecha",
             "defecto": fecha_web(ahora)},
            {"nombre": "devolucion_esperada", "etiqueta": "Devolución esperada", "tipo": "fecha",
             "defecto": fecha_web(movimientos.devolucion_por_defecto(ahora)),
             "ayuda": "Horario normal de devolución: 16:30 a 17:15."},
            {"nombre": "residente_autoriza", "etiqueta": "Residente que autorizó otro horario",
             "tipo": "texto", "ayuda": "Solo si la devolución queda fuera de 16:30-17:15."},
            {"nombre": "observaciones", "etiqueta": "Observaciones (opcional)", "tipo": "texto"},
        ]
    if id_opcion == "2.2":
        return [
            {"nombre": "codigo", "etiqueta": "Herramienta que regresa", "tipo": "select",
             "opciones": opciones_herramientas(movimientos.herramientas_en_obra(datos), codigo, datos)},
            {"nombre": "fecha_devolucion", "etiqueta": "Fecha y hora de devolución",
             "tipo": "fecha", "defecto": fecha_web(ahora)},
            {"nombre": "estado_recibido", "etiqueta": "Estado en que se recibe", "tipo": "select",
             "opciones": [("bueno", "Bueno"), ("con daño", "Con daño")]},
            {"nombre": "observaciones", "etiqueta": "Observaciones (ej. ruido raro, golpe)",
             "tipo": "texto"},
        ]
    if id_opcion == "2.3":
        return [
            {"nombre": "codigo", "etiqueta": "Herramienta (la obra de origen es su ubicación actual)",
             "tipo": "select",
             "opciones": opciones_herramientas(movimientos.herramientas_en_obra(datos), codigo, datos)},
            {"nombre": "codigo_destino", "etiqueta": "Obra de destino", "tipo": "select",
             "opciones": opciones_obras(datos)},
            {"nombre": "responsable", "etiqueta": "Responsable en la obra de destino", "tipo": "texto"},
            {"nombre": "observaciones", "etiqueta": "Observaciones (opcional)", "tipo": "texto"},
        ]
    if id_opcion == "2.4":
        return [
            {"nombre": "codigo", "etiqueta": "Herramienta", "tipo": "select",
             "opciones": opciones_herramientas(datos["herramientas"], codigo, datos)},
            {"nombre": "descripcion", "etiqueta": "¿Qué le pasó? (mínimo 5 letras)", "tipo": "texto"},
            {"nombre": "fecha", "etiqueta": "Fecha y hora", "tipo": "fecha",
             "defecto": fecha_web(ahora)},
            {"nombre": "responsable", "etiqueta": "Quién reporta o tenía la herramienta",
             "tipo": "texto"},
        ]
    if id_opcion == "2.5":
        return [
            {"nombre": "codigo", "etiqueta": "Herramienta a revisar", "tipo": "select",
             "opciones": opciones_herramientas(movimientos.herramientas_por_revisar(datos),
                                               codigo, datos),
             "ayuda": "Equipos con motor o cable: revise golpes, ruido extraño y cable expuesto."},
            {"nombre": "resultado", "etiqueta": "Resultado", "tipo": "select",
             "opciones": [("apta", "Apta - puede salir"), ("no apta", "No apta - a reparación")]},
            {"nombre": "revisor", "etiqueta": "Quién revisó", "tipo": "texto"},
            {"nombre": "observaciones", "etiqueta": "Observaciones (opcional)", "tipo": "texto"},
        ]
    # 2.6 Autorizar permanencia
    return [
        {"nombre": "codigo", "etiqueta": "Herramienta que se queda en obra", "tipo": "select",
         "opciones": opciones_herramientas(movimientos.herramientas_en_obra(datos), codigo, datos)},
        {"nombre": "fecha_inicio", "etiqueta": "Desde", "tipo": "fecha", "defecto": fecha_web(ahora)},
        {"nombre": "fecha_fin", "etiqueta": "Hasta", "tipo": "fecha",
         "defecto": fecha_web((ahora + timedelta(days=1)).replace(hour=6, minute=15))},
        {"nombre": "seguridad", "etiqueta": "¿El sitio tiene seguridad (garita, guardián, bodega con llave)?",
         "tipo": "select", "opciones": [("si", "Sí, tiene seguridad"), ("no", "No")]},
        {"nombre": "observaciones", "etiqueta": "Observaciones (opcional)", "tipo": "texto"},
    ]


def argumentos_de_operacion(datos, id_opcion, valores):
    """Convierte los valores del formulario en argumentos para validar_xxx."""
    codigo = valores.get("codigo", "")
    if id_opcion == "2.1":
        return {"codigo": codigo, "codigo_obra": valores.get("codigo_obra", ""),
                "responsable": valores.get("responsable", ""),
                "fecha_salida": leer_fecha_web(valores.get("fecha_salida")),
                "devolucion_esperada": leer_fecha_web(valores.get("devolucion_esperada")),
                "residente_autoriza": valores.get("residente_autoriza", "")}
    if id_opcion == "2.2":
        return {"codigo": codigo, "fecha_devolucion": leer_fecha_web(valores.get("fecha_devolucion")),
                "estado_recibido": valores.get("estado_recibido", "")}
    if id_opcion == "2.3":
        return {"codigo": codigo, "codigo_destino": valores.get("codigo_destino", ""),
                "responsable": valores.get("responsable", "")}
    if id_opcion == "2.4":
        return {"codigo": codigo, "descripcion": valores.get("descripcion", ""),
                "fecha": leer_fecha_web(valores.get("fecha")),
                "responsable": valores.get("responsable", "")}
    if id_opcion == "2.5":
        return {"codigo": codigo, "resultado": valores.get("resultado", ""),
                "revisor": valores.get("revisor", "")}
    herramienta = obtener_herramienta(datos, codigo)
    obra = ""
    if herramienta is not None:
        obra = herramienta["ubicacion"]
    return {"codigo": codigo, "codigo_obra": obra,
            "fecha_inicio": leer_fecha_web(valores.get("fecha_inicio")),
            "fecha_fin": leer_fecha_web(valores.get("fecha_fin")),
            "seguridad_confirmada": valores.get("seguridad") == "si"}


VALIDAR = {
    "2.1": movimientos.validar_salida, "2.2": movimientos.validar_devolucion,
    "2.3": movimientos.validar_traslado, "2.4": movimientos.validar_dano,
    "2.5": movimientos.validar_revision, "2.6": movimientos.validar_permanencia,
}
REGISTRAR = {
    "2.1": movimientos.registrar_salida, "2.2": movimientos.registrar_devolucion,
    "2.3": movimientos.registrar_traslado, "2.4": movimientos.registrar_dano,
    "2.5": movimientos.registrar_revision, "2.6": movimientos.registrar_permanencia,
}


def resumen_de_operacion(datos, id_opcion, campos, valores):
    """Lista (etiqueta, valor legible) para la pantalla de confirmación."""
    resumen = []
    for campo in campos:
        valor = valores.get(campo["nombre"], "")
        if campo["tipo"] == "select":
            for opcion_valor, opcion_texto in campo["opciones"]:
                if opcion_valor == valor:
                    valor = opcion_texto
        if campo["tipo"] == "fecha" and leer_fecha_web(valor) is not None:
            valor = leer_fecha_web(valor).strftime("%d/%m/%Y %H:%M")
        if valor != "":
            resumen.append((campo["etiqueta"], valor))
    herramienta = obtener_herramienta(datos, valores.get("codigo", ""))
    if id_opcion in ["2.3", "2.6"] and herramienta is not None:
        resumen.insert(1, ("Obra de origen / actual", nombre_obra(datos, herramienta["ubicacion"])))
    return resumen


# -------------------------------------------------------------------- rutas

def ip_del_cliente():
    """Dirección IP de quien visita.

    Publicada, la IP real la agrega el proxy del hosting al FINAL de X-Forwarded-For
    (lo que viene antes lo podría inventar el visitante). En la computadora local
    esa cabecera se ignora.
    """
    reenviada = request.headers.get("X-Forwarded-For", "")
    if PUBLICO and reenviada != "":
        return reenviada.split(",")[-1].strip()
    return request.remote_addr or "desconocida"


def tiempo_de_bloqueo_restante(ip):
    """Minutos que faltan para que esa IP pueda intentar de nuevo (0 = no está bloqueada)."""
    intentos, hasta = INTENTOS_POR_IP.get(ip, [0, 0])
    if hasta == 0:
        return 0
    if hasta <= time.time():   # el bloqueo ya pasó: se reinician los intentos
        INTENTOS_POR_IP.pop(ip, None)
        return 0
    return int((hasta - time.time()) // 60) + 1


def registrar_intento_fallido(ip):
    """Suma un intento fallido; al tercero bloquea la IP 5 minutos. Devuelve los intentos."""
    intentos, hasta = INTENTOS_POR_IP.get(ip, [0, 0])
    intentos = intentos + 1
    if intentos >= MAXIMO_INTENTOS:
        hasta = time.time() + MINUTOS_BLOQUEO * 60
    INTENTOS_POR_IP[ip] = [intentos, hasta]
    return intentos


@app.route("/login", methods=["GET", "POST"])
def login():
    """Inicio de sesión: 3 intentos por dirección IP y luego una espera de 5 minutos."""
    datos, avisos = cargar_datos()
    if usuario_actual(datos) is not None:
        return redirect(url_for("inicio"))
    error = ""
    nombre_escrito = ""
    ip = ip_del_cliente()
    minutos = tiempo_de_bloqueo_restante(ip)
    if request.method == "POST" and minutos == 0:
        nombre_escrito = request.form.get("usuario", "").strip()[:40]
        usuario = verificar_credenciales(datos, nombre_escrito, request.form.get("contrasena", ""))
        if usuario is not None and PUBLICO and usuario["contrasena"] in CONTRASENAS_DE_PRUEBA:
            error = ("Por seguridad, las contraseñas de prueba no funcionan en la versión "
                     "publicada. El administrador debe cambiarla con cambiar_contrasena.py.")
            return render_template("login.html", error=error, minutos_bloqueo=0, avisos=avisos,
                                   nombre_escrito=nombre_escrito)
        if usuario is not None:
            INTENTOS_POR_IP.pop(ip, None)
            session.clear()
            session.permanent = True
            session["usuario"] = usuario["usuario"]
            flash("Bienvenido(a), " + usuario["nombre"] + ".", "exito")
            return redirect(url_for("inicio"))
        intentos = registrar_intento_fallido(ip)
        if intentos >= MAXIMO_INTENTOS:
            minutos = MINUTOS_BLOQUEO
        else:
            error = ("Usuario o contraseña incorrectos. Le quedan "
                     + str(MAXIMO_INTENTOS - intentos) + " intento(s).")
    return render_template("login.html", error=error, minutos_bloqueo=minutos, avisos=avisos,
                           nombre_escrito=nombre_escrito)


# ------------------------------------------------- app instalable (PWA)

@app.route("/manifest.webmanifest")
def manifiesto():
    """Datos de la app (nombre, íconos, colores) para poder instalarla."""
    return send_from_directory(CARPETA_ESTATICA, "manifest.webmanifest",
                               mimetype="application/manifest+json")


@app.route("/sw.js")
def service_worker():
    """El service worker se sirve desde la raíz para que controle toda la app."""
    respuesta = send_from_directory(CARPETA_ESTATICA, "sw.js", mimetype="text/javascript")
    respuesta.headers["Cache-Control"] = "no-cache"
    return respuesta


@app.route("/sin-conexion")
def sin_conexion():
    """Pantalla que la app muestra cuando no hay internet."""
    return render_template("sin_conexion.html", usuario=None, titulo="Sin conexión")


@app.route("/instalar")
def instalar():
    """Instrucciones para instalar SICH en Android, iPhone y computadora."""
    datos, avisos = cargar_datos()
    usuario = usuario_actual(datos)
    rol = NOMBRES_ROL[usuario["rol"]] if usuario is not None else ""
    return render_template("instalar.html", usuario=usuario, rol=rol, titulo="Instalar la app",
                           migas=[("Instalar la app", "")])


@app.route("/salir")
def salir():
    """Opción 9 / 0: cierra la sesión."""
    session.clear()
    flash("Sesión cerrada. Puede entrar con otro usuario o cerrar esta pestaña.", "exito")
    return redirect(url_for("login"))


@app.route("/")
def inicio():
    """Tablero con las 4 tarjetas, accesos rápidos según el rol y el menú principal."""
    datos, avisos = cargar_datos()
    usuario = usuario_actual(datos)
    if usuario is None:
        return ir_a_login()
    rapidos = []
    for id_opcion, texto in ACCESOS_RAPIDOS:
        if tiene_permiso(usuario, id_opcion) and esta_implementada(id_opcion):
            rapidos.append((id_opcion, texto))
    return render_template("inicio.html", usuario=usuario, rol=NOMBRES_ROL[usuario["rol"]],
                           resumen=resumen_tablero(datos), menu=MENU_PRINCIPAL[:3],
                           avisos=avisos, rapidos=rapidos,
                           hoy=movimientos.momento_actual(None).strftime("%d/%m/%Y %H:%M"))


@app.route("/menu/<numero>")
def submenu(numero):
    """Submenú 1, 2 o 3 con las marcas de permiso y pendiente."""
    datos, avisos = cargar_datos()
    usuario = usuario_actual(datos)
    if usuario is None:
        return ir_a_login()
    if numero not in SUBMENUS:
        return pagina_mensaje(datos, usuario, "Menú", "Opción no válida, intente de nuevo.", "error")
    titulo, opciones = SUBMENUS[numero]
    lista = []
    for id_opcion, texto in opciones:
        lista.append({"id": id_opcion, "texto": texto,
                      "permiso": tiene_permiso(usuario, id_opcion),
                      "implementada": esta_implementada(id_opcion)})
    return render_template("submenu.html", usuario=usuario, rol=NOMBRES_ROL[usuario["rol"]],
                           titulo=titulo, opciones=lista, migas=[(titulo, "")])


@app.route("/opcion/<id_opcion>")
def opcion(id_opcion):
    """Dirige a la funcionalidad, o avisa si no hay permiso o si está pendiente."""
    datos, avisos = cargar_datos()
    usuario = usuario_actual(datos)
    if usuario is None:
        return ir_a_login()
    if not tiene_permiso(usuario, id_opcion):
        return pagina_mensaje(datos, usuario, "Opción " + id_opcion, MENSAJE_SIN_PERMISO, "error")
    if not esta_implementada(id_opcion):
        return pagina_mensaje(datos, usuario, "Opción " + id_opcion, MENSAJE_PENDIENTE)
    if id_opcion == "3.1":
        return redirect(url_for("buscar"))
    return redirect(url_for("operacion", id_opcion=id_opcion, **request.args.to_dict()))


def acciones_de_herramienta(usuario, herramienta):
    """Botones que tienen sentido para la herramienta y que el rol puede usar."""
    acciones = []
    if movimientos.motivo_bloqueo_salida(herramienta) == "":
        acciones.append(("2.1", "Sacar a obra"))
    if herramienta["ubicacion"] != "Bodega":
        acciones.append(("2.2", "Registrar devolución"))
    if movimientos.motivo_bloqueo_traslado(herramienta) == "":
        acciones.append(("2.3", "Trasladar"))
        acciones.append(("2.6", "Autorizar que se quede"))
    if herramienta["estado"] != "dada de baja":
        acciones.append(("2.4", "Reportar daño"))
    if movimientos.motivo_bloqueo_revision(herramienta) == "":
        acciones.append(("2.5", "Registrar revisión"))
    permitidas = []
    for id_opcion, texto_accion in acciones:
        if tiene_permiso(usuario, id_opcion):
            permitidas.append((id_opcion, texto_accion))
    return permitidas


@app.route("/buscar")
def buscar():
    """3.1 Buscar herramienta por código, nombre o apodo."""
    datos, avisos = cargar_datos()
    usuario = usuario_actual(datos)
    if usuario is None:
        return ir_a_login()
    texto = request.args.get("q", "").strip()[:60]
    resultados = []
    aproximada = False
    if texto != "":
        encontradas, aproximada = buscar_con_detalle(datos, texto)
        for herramienta in encontradas:
            resultados.append({"herramienta": herramienta,
                               "detalle": detalle_herramienta(datos, herramienta),
                               "vencida": movimientos.esta_vencida(datos, herramienta),
                               "acciones": acciones_de_herramienta(usuario, herramienta)})
    return render_template("buscar.html", usuario=usuario, rol=NOMBRES_ROL[usuario["rol"]],
                           texto=texto, resultados=resultados, aproximada=aproximada,
                           ejemplos=["bailarina", "la makita azul", "trompo", "COR-01"],
                           migas=[("3.1 Buscar herramienta", "")])


@app.route("/movimientos/<id_opcion>", methods=["GET", "POST"])
def operacion(id_opcion):
    """Formulario -> confirmación (¿Confirmar operación?) -> resultado."""
    datos, avisos = cargar_datos()
    usuario = usuario_actual(datos)
    if usuario is None:
        return ir_a_login()
    if id_opcion not in VALIDAR:
        return pagina_mensaje(datos, usuario, "Movimientos", "Opción no válida, intente de nuevo.",
                              "error")
    if not tiene_permiso(usuario, id_opcion):
        return pagina_mensaje(datos, usuario, "Opción " + id_opcion, MENSAJE_SIN_PERMISO, "error")
    titulo = ""
    for id_sub, texto in SUBMENUS["2"][1]:
        if id_sub == id_opcion:
            titulo = id_opcion + " " + texto
    migas = [(SUBMENUS["2"][0], url_for("submenu", numero="2")), (titulo, "")]
    if request.method == "GET":
        valores = request.args.to_dict()
    else:
        valores = request.form.to_dict()
    valores.pop("token", None)
    campos = campos_de_operacion(datos, id_opcion, valores)
    paso = valores.pop("paso", "")

    if paso == "cancelar":
        return pagina_mensaje(datos, usuario, titulo, movimientos.MENSAJE_CANCELADO)

    errores = []
    if paso in ["revisar", "guardar"]:
        argumentos = argumentos_de_operacion(datos, id_opcion, valores)
        errores = VALIDAR[id_opcion](datos, usuario, **argumentos)
        if len(errores) == 0 and paso == "revisar":
            return render_template("confirmar.html", usuario=usuario,
                                   rol=NOMBRES_ROL[usuario["rol"]], titulo=titulo,
                                   id_opcion=id_opcion, valores=valores, migas=migas,
                                   resumen=resumen_de_operacion(datos, id_opcion, campos, valores))
        if len(errores) == 0 and paso == "guardar":
            if id_opcion != "2.4":
                argumentos["observaciones"] = valores.get("observaciones", "")
            exito, mensaje = REGISTRAR[id_opcion](datos, usuario, **argumentos)
            if exito:
                guardar_datos(datos)
            ofrecer_dano = (id_opcion == "2.2" and exito
                            and valores.get("estado_recibido") == "con daño")
            return render_template("resultado.html", usuario=usuario,
                                   rol=NOMBRES_ROL[usuario["rol"]], titulo=titulo, exito=exito,
                                   mensaje=mensaje, id_opcion=id_opcion, migas=migas,
                                   codigo=valores.get("codigo", ""), ofrecer_dano=ofrecer_dano)

    for campo in campos:
        campo["valor"] = valores.get(campo["nombre"], campo.get("defecto", ""))
    return render_template("formulario.html", usuario=usuario, rol=NOMBRES_ROL[usuario["rol"]],
                           titulo=titulo, id_opcion=id_opcion, campos=campos, errores=errores,
                           personal=PERSONAL, migas=migas)


if __name__ == "__main__":
    # Para probar desde el celular en la misma red Wi-Fi:  py app.py --red
    import sys
    if "--red" in sys.argv:
        print("SICH web visible en la red local: abra http://<IP de esta computadora>:5000 "
              "en el celular (Ctrl + C para detener)")
        app.run(host="0.0.0.0", port=5000, debug=False)
    else:
        print("SICH web en http://127.0.0.1:5000  (Ctrl + C para detener)")
        app.run(host="127.0.0.1", port=5000, debug=False)
