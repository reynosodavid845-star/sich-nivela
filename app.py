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
from sich import consultas, cuentas, herramientas
from sich.consultas import detalle_herramienta, resumen_tablero
from sich.datos import cargar_datos, cifrar_contrasena, es_contrasena_de_demostracion, guardar_datos
from sich.menus import MENU_PRINCIPAL, SUBMENUS
from sich.validaciones import fecha_para_mostrar

app = Flask(__name__)
app.jinja_env.filters["fecha"] = fecha_para_mostrar   # {{ dato|fecha }} -> DD/MM/AAAA HH:MM

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
app.config["MAX_CONTENT_LENGTH"] = herramientas.MAXIMO_BYTES_FICHA + 1024 * 1024

VERSION_ESTATICOS = "7"          # cambiarla obliga al navegador a bajar el CSS/JS nuevo
FORMATO_WEB = "%Y-%m-%dT%H:%M"   # formato de <input type="datetime-local">
MINUTOS_BLOQUEO = 5              # espera después de 3 intentos fallidos de inicio de sesión
CARPETA_ESTATICA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")

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
if PUBLICO:
    # Si todavía no hay propietario, deja el código de configuración en el registro (Logs).
    cuentas.codigo_de_configuracion(cargar_datos()[0])

PERSONAL = ["Erick Santos", "Luis Aguilar", "Julián Pivaral", "Ing. Esteban Cifuentes"]

# Botones grandes del inicio: lo más usado por cada rol, a un solo toque.
ACCESOS_RAPIDOS = [
    ("2.1", "Sacar herramienta a obra"),
    ("2.2", "Recibir herramienta en bodega"),
    ("2.3", "Trasladar entre obras"),
    ("2.6", "Autorizar que se quede en obra"),
    ("2.4", "Reportar daño"),
    ("2.5", "Registrar revisión"),
    ("2.7", "Confirmar que llegó a la obra"),
    ("2.8", "Registrar mantenimiento"),
    ("3.3", "Ver devoluciones pendientes"),
    ("3.4", "Ver herramientas por obra"),
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


@app.errorhandler(413)
def archivo_muy_grande(error):
    """El archivo subido supera el máximo permitido."""
    return render_template("mensaje.html", usuario=None, titulo="Archivo muy grande",
                           mensaje="El archivo pesa más de 5 MB. Elija uno más liviano.",
                           tipo="error"), 413


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
        if usuario["usuario"] == nombre and usuario.get("activo", True):
            return usuario
    return None


def leer_fecha_web(texto):
    """Convierte el valor de un campo datetime-local a datetime (None si es inválido)."""
    try:
        return datetime.strptime(texto, FORMATO_WEB)
    except (ValueError, TypeError):
        return None


def leer_entero_web(texto):
    """Convierte el texto de un campo numérico a entero (None si es inválido)."""
    try:
        return int(str(texto).strip())
    except ValueError:
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


# --------------------------------------------- formularios de los Módulos 1 y 2

def campos_de_catalogo(datos, id_opcion, valores):
    """Campos de los formularios del Módulo 1."""
    codigo = valores.get("codigo", "")
    if id_opcion == "1.1":
        estados = []
        for estado in herramientas.ESTADOS_INICIALES:
            estados.append((estado, estado.capitalize()))
        return [
            {"nombre": "codigo", "etiqueta": "Código oficial (ej. ROT-04)", "tipo": "texto"},
            {"nombre": "nombre", "etiqueta": "Nombre (ej. Rotomartillo)", "tipo": "texto"},
            {"nombre": "categoria", "etiqueta": "Categoría", "tipo": "texto", "lista": "categorias"},
            {"nombre": "marca", "etiqueta": "Marca", "tipo": "texto",
             "ayuda": "Si no se conoce, escriba Sin marca."},
            {"nombre": "estado", "etiqueta": "Estado inicial", "tipo": "select", "opciones": estados},
            {"nombre": "motor_o_cable", "etiqueta": "¿Tiene motor o cable eléctrico?", "tipo": "select",
             "opciones": [("si", "Sí"), ("no", "No")]},
            {"nombre": "ficha_tecnica", "etiqueta": "Ficha técnica: resumen o referencia (opcional)",
             "tipo": "texto", "ayuda": "El PDF o la foto se sube en el paso siguiente."},
            {"nombre": "mantenimiento_cada_horas", "etiqueta": "Horas entre mantenimientos según la ficha",
             "tipo": "numero", "defecto": "0",
             "ayuda": "Ej.: 400. Empieza en 0 de 400 y suma horas con cada salida. 0 = no aplica."},
            {"nombre": "observaciones", "etiqueta": "Observaciones (opcional)", "tipo": "texto"},
        ]
    if id_opcion == "1.2":
        return [
            {"nombre": "codigo", "etiqueta": "Herramienta", "tipo": "select",
             "opciones": opciones_herramientas(datos["herramientas"], codigo, datos)},
            {"nombre": "apodos", "etiqueta": "Apodos nuevos, separados por coma", "tipo": "texto",
             "ayuda": "Ej.: rana, bailarina chiquita"},
        ]
    # 1.3 Modificar: primero se elige la herramienta y luego se muestran sus datos.
    herramienta = obtener_herramienta(datos, codigo)
    if herramienta is None:
        return [{"nombre": "codigo", "etiqueta": "¿Qué herramienta quiere modificar?", "tipo": "select",
                 "opciones": opciones_herramientas(datos["herramientas"], "", datos)}]
    estados = [(herramienta["estado"], "Conservar: " + herramienta["estado"])]
    for estado in herramientas.estados_permitidos_al_modificar(herramienta):
        estados.append((estado, "Cambiar a: " + estado))
    return [
        {"nombre": "codigo", "etiqueta": "Herramienta (el código no se cambia)", "tipo": "fijo",
         "texto": descripcion_corta(herramienta)},
        {"nombre": "nombre", "etiqueta": "Nombre", "tipo": "texto", "defecto": herramienta["nombre"]},
        {"nombre": "categoria", "etiqueta": "Categoría", "tipo": "texto", "lista": "categorias",
         "defecto": herramienta["categoria"]},
        {"nombre": "marca", "etiqueta": "Marca", "tipo": "texto", "defecto": herramienta["marca"]},
        {"nombre": "motor_o_cable", "etiqueta": "¿Tiene motor o cable eléctrico?", "tipo": "select",
         "opciones": [("si", "Sí"), ("no", "No")],
         "defecto": "si" if herramienta["motor_o_cable"] else "no"},
        {"nombre": "ficha_tecnica", "etiqueta": "Ficha técnica: resumen o referencia", "tipo": "texto",
         "defecto": herramienta.get("ficha_tecnica", "")},
        {"nombre": "mantenimiento_cada_horas", "etiqueta": "Horas entre mantenimientos según la ficha",
         "tipo": "numero", "defecto": str(movimientos.intervalo_mantenimiento(herramienta)),
         "ayuda": "Lleva " + movimientos.texto_horas(movimientos.horas_de_uso(herramienta))
                  + " h de uso. 0 = no aplica."},
        {"nombre": "observaciones", "etiqueta": "Observaciones", "tipo": "texto",
         "defecto": herramienta["observaciones"]},
        {"nombre": "estado", "etiqueta": "Estado", "tipo": "select", "opciones": estados,
         "defecto": herramienta["estado"],
         "ayuda": "Salidas, devoluciones, daños y revisiones cambian el estado desde su propia opción."},
    ]


def campos_de_operacion(datos, usuario, id_opcion, valores):
    """Devuelve la lista de campos del formulario de una operación."""
    if id_opcion.startswith("1."):
        return campos_de_catalogo(datos, id_opcion, valores)
    ahora = movimientos.momento_actual(None)
    codigo = valores.get("codigo", "")
    if id_opcion == "2.8":
        return [
            {"nombre": "codigo", "etiqueta": "Herramienta (el contador vuelve a 0)", "tipo": "select",
             "opciones": opciones_herramientas(movimientos.herramientas_para_mantenimiento(datos),
                                               codigo, datos)},
            {"nombre": "fecha", "etiqueta": "Fecha y hora del mantenimiento", "tipo": "fecha",
             "defecto": fecha_web(ahora)},
            {"nombre": "realizado_por", "etiqueta": "Quién hizo el mantenimiento", "tipo": "texto"},
            {"nombre": "observaciones", "etiqueta": "Observaciones (opcional)", "tipo": "texto"},
        ]
    if id_opcion == "2.7":
        return [
            {"nombre": "codigo", "etiqueta": "Herramienta que llegó a la obra", "tipo": "select",
             "opciones": opciones_herramientas(movimientos.herramientas_por_recibir(datos, usuario),
                                               codigo, datos)},
            {"nombre": "fecha", "etiqueta": "Fecha y hora de recepción", "tipo": "fecha",
             "defecto": fecha_web(ahora)},
            {"nombre": "observaciones", "etiqueta": "Observaciones (opcional)", "tipo": "texto",
             "ayuda": "Si llegó dañada, repórtelo también en 2.4 Reportar daño."},
        ]
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
    if id_opcion == "1.1":
        return {"codigo": codigo, "nombre": valores.get("nombre", ""),
                "categoria": valores.get("categoria", ""), "marca": valores.get("marca", ""),
                "estado": valores.get("estado", ""),
                "motor_o_cable": valores.get("motor_o_cable") == "si",
                "ficha_tecnica": valores.get("ficha_tecnica", ""),
                "mantenimiento_cada_horas": leer_entero_web(valores.get("mantenimiento_cada_horas", "0"))}
    if id_opcion == "1.2":
        return {"codigo": codigo, "texto_apodos": valores.get("apodos", "")}
    if id_opcion == "1.3":
        return {"codigo": codigo, "nombre": valores.get("nombre", ""),
                "categoria": valores.get("categoria", ""), "marca": valores.get("marca", ""),
                "motor_o_cable": valores.get("motor_o_cable") == "si",
                "observaciones": valores.get("observaciones", ""),
                "estado": valores.get("estado", ""),
                "ficha_tecnica": valores.get("ficha_tecnica", ""),
                "mantenimiento_cada_horas": leer_entero_web(valores.get("mantenimiento_cada_horas", "0"))}
    if id_opcion == "2.8":
        return {"codigo": codigo, "fecha": leer_fecha_web(valores.get("fecha")),
                "realizado_por": valores.get("realizado_por", "")}
    if id_opcion == "2.7":
        return {"codigo": codigo, "fecha": leer_fecha_web(valores.get("fecha"))}
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
    "1.1": herramientas.validar_registro, "1.2": herramientas.validar_apodos,
    "1.3": herramientas.validar_modificacion, "2.7": movimientos.validar_recepcion,
    "2.8": movimientos.validar_mantenimiento,
    "2.1": movimientos.validar_salida, "2.2": movimientos.validar_devolucion,
    "2.3": movimientos.validar_traslado, "2.4": movimientos.validar_dano,
    "2.5": movimientos.validar_revision, "2.6": movimientos.validar_permanencia,
}
REGISTRAR = {
    "1.1": herramientas.registrar_herramienta, "1.2": herramientas.registrar_apodos,
    "1.3": herramientas.registrar_modificacion, "2.7": movimientos.registrar_recepcion,
    "2.8": movimientos.registrar_mantenimiento,
    "2.1": movimientos.registrar_salida, "2.2": movimientos.registrar_devolucion,
    "2.3": movimientos.registrar_traslado, "2.4": movimientos.registrar_dano,
    "2.5": movimientos.registrar_revision, "2.6": movimientos.registrar_permanencia,
}

# Estas opciones reciben las observaciones aparte (o no las usan) al registrar.
OPCIONES_SIN_OBSERVACIONES_EXTRA = ["1.2", "1.3", "2.4"]


def resumen_de_operacion(datos, id_opcion, campos, valores):
    """Lista (etiqueta, valor legible) para la pantalla de confirmación."""
    resumen = []
    for campo in campos:
        valor = valores.get(campo["nombre"], "")
        if campo["tipo"] == "fijo":
            valor = campo["texto"]
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
        if usuario is not None and PUBLICO \
                and es_contrasena_de_demostracion(request.form.get("contrasena", "")):
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
                           nombre_escrito=nombre_escrito,
                           falta_propietario=not cuentas.hay_propietario(datos))


# ------------------------------------------------- cuentas y propietario

@app.route("/configurar", methods=["GET", "POST"])
def configurar():
    """Crea la PRIMERA cuenta de propietario con el código de configuración del servidor."""
    datos, avisos = cargar_datos()
    if cuentas.hay_propietario(datos):
        flash("El propietario ya está configurado. Inicie sesión.", "aviso")
        return redirect(url_for("login"))
    cuentas.codigo_de_configuracion(datos)   # lo genera y lo escribe en el Log si no existe
    ip = ip_del_cliente()
    minutos = tiempo_de_bloqueo_restante(ip)
    error = ""
    valores = {}
    if request.method == "POST" and minutos == 0:
        valores = request.form.to_dict()
        contrasena = valores.get("contrasena", "")
        if PUBLICO and es_contrasena_de_demostracion(contrasena):
            error = "No use una contraseña de prueba."
        else:
            exito, mensaje = cuentas.crear_propietario_inicial(
                datos, valores.get("codigo", ""), valores.get("usuario", ""),
                valores.get("nombre", ""), contrasena, valores.get("repetida", ""))
            if exito:
                guardar_datos(datos)
                INTENTOS_POR_IP.pop(ip, None)
                session.clear()
                session.permanent = True
                session["usuario"] = valores["usuario"].strip().lower()
                flash(mensaje, "exito")
                return redirect(url_for("administrar_cuentas"))
            error = mensaje
            if "código" in mensaje:
                registrar_intento_fallido(ip)
                minutos = tiempo_de_bloqueo_restante(ip)
    valores.pop("contrasena", None)
    valores.pop("repetida", None)
    return render_template("configurar.html", usuario=None, titulo="Configurar propietario",
                           error=error, valores=valores, minutos_bloqueo=minutos)


@app.route("/cuentas", methods=["GET", "POST"])
def administrar_cuentas():
    """Panel del propietario: crear cuentas, restablecer contraseñas, activar o desactivar."""
    datos, avisos = cargar_datos()
    usuario = usuario_actual(datos)
    if usuario is None:
        return ir_a_login()
    if not cuentas.es_propietario(usuario):
        return pagina_mensaje(datos, usuario, "Administrar cuentas",
                              "Solo el propietario puede administrar las cuentas.", "error")
    resultado = None
    valores = {}
    if request.method == "POST":
        accion = request.form.get("accion", "")
        objetivo = request.form.get("usuario", "")
        contrasena = request.form.get("contrasena", "")
        repetida = request.form.get("repetida", "")
        if contrasena != "" and PUBLICO and es_contrasena_de_demostracion(contrasena):
            resultado = (False, "No use una contraseña de prueba.")
        elif accion == "crear":
            valores = request.form.to_dict()
            resultado = cuentas.crear_usuario(datos, usuario, objetivo, request.form.get("nombre", ""),
                                              request.form.get("rol", ""), contrasena, repetida,
                                              request.form.get("obra", ""))
        elif accion == "restablecer":
            resultado = cuentas.restablecer_contrasena(datos, usuario, objetivo, contrasena, repetida)
        elif accion in ["activar", "desactivar"]:
            resultado = cuentas.cambiar_estado(datos, usuario, objetivo, accion == "activar")
        else:
            resultado = (False, "Opción no válida, intente de nuevo.")
        if resultado[0]:
            guardar_datos(datos)
            valores = {}
        valores.pop("contrasena", None)
        valores.pop("repetida", None)
    lista = sorted(datos["usuarios"], key=lambda u: (u["rol"] != "propietario", u["usuario"]))
    return render_template("cuentas.html", usuario=usuario, rol=NOMBRES_ROL[usuario["rol"]],
                           titulo="Administrar cuentas", cuentas=lista, roles=NOMBRES_ROL,
                           obras=opciones_obras(datos), resultado=resultado, valores=valores,
                           migas=[("Administrar cuentas", "")])


@app.route("/mi-contrasena", methods=["GET", "POST"])
def mi_contrasena():
    """Cualquier usuario cambia su propia contraseña."""
    datos, avisos = cargar_datos()
    usuario = usuario_actual(datos)
    if usuario is None:
        return ir_a_login()
    resultado = None
    if request.method == "POST":
        nueva = request.form.get("nueva", "")
        if PUBLICO and es_contrasena_de_demostracion(nueva):
            resultado = (False, "No use una contraseña de prueba.")
        else:
            resultado = cuentas.cambiar_mi_contrasena(datos, usuario, request.form.get("actual", ""),
                                                      nueva, request.form.get("repetida", ""))
            if resultado[0]:
                guardar_datos(datos)
    return render_template("mi_contrasena.html", usuario=usuario, rol=NOMBRES_ROL[usuario["rol"]],
                           titulo="Mi contraseña", resultado=resultado,
                           migas=[("Mi contraseña", "")])


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
        if tiene_permiso(usuario, id_opcion):
            rapidos.append((id_opcion, texto))
    return render_template("inicio.html", usuario=usuario, rol=NOMBRES_ROL[usuario["rol"]],
                           resumen=resumen_tablero(datos), menu=MENU_PRINCIPAL[:3],
                           avisos=avisos, rapidos=rapidos,
                           es_propietario=cuentas.es_propietario(usuario),
                           ver_disponibles=tiene_permiso(usuario, "3.2"),
                           ver_pendientes=tiene_permiso(usuario, "3.3"),
                           ver_mantenimiento=tiene_permiso(usuario, "3.6"),
                           hoy=movimientos.momento_actual(None).strftime("%d/%m/%Y %H:%M"))


@app.route("/menu/<numero>")
def submenu(numero):
    """Submenú 1, 2 o 3 con la marca de permiso."""
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
                      "permiso": tiene_permiso(usuario, id_opcion)})
    return render_template("submenu.html", usuario=usuario, rol=NOMBRES_ROL[usuario["rol"]],
                           titulo=titulo, opciones=lista, migas=[(titulo, "")])


@app.route("/opcion/<id_opcion>")
def opcion(id_opcion):
    """Dirige a la funcionalidad, o avisa si no hay permiso."""
    datos, avisos = cargar_datos()
    usuario = usuario_actual(datos)
    if usuario is None:
        return ir_a_login()
    if not tiene_permiso(usuario, id_opcion):
        return pagina_mensaje(datos, usuario, "Opción " + id_opcion, MENSAJE_SIN_PERMISO, "error")
    if id_opcion == "3.1":
        return redirect(url_for("buscar"))
    if id_opcion.startswith("3."):
        return redirect(url_for("consulta", id_opcion=id_opcion, **request.args.to_dict()))
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
    if movimientos.motivo_bloqueo_recepcion(usuario, herramienta) == "":
        acciones.append(("2.7", "Confirmar que llegó"))
    if movimientos.motivo_bloqueo_mantenimiento(herramienta) == "":
        acciones.append(("2.8", "Registrar mantenimiento"))
    acciones.append(("3.5", "Ver historial"))
    acciones.append(("1.2", "Asociar apodos"))
    acciones.append(("1.3", "Modificar"))
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


@app.route("/operacion/<id_opcion>", methods=["GET", "POST"])
def operacion(id_opcion):
    """Formulario -> confirmación (¿Confirmar operación?) -> resultado."""
    datos, avisos = cargar_datos()
    usuario = usuario_actual(datos)
    if usuario is None:
        return ir_a_login()
    if id_opcion not in VALIDAR:
        return pagina_mensaje(datos, usuario, "Operación", "Opción no válida, intente de nuevo.",
                              "error")
    if not tiene_permiso(usuario, id_opcion):
        return pagina_mensaje(datos, usuario, "Opción " + id_opcion, MENSAJE_SIN_PERMISO, "error")
    numero_menu = id_opcion[0]
    titulo = ""
    for id_sub, texto in SUBMENUS[numero_menu][1]:
        if id_sub == id_opcion:
            titulo = id_opcion + " " + texto
    migas = [(SUBMENUS[numero_menu][0], url_for("submenu", numero=numero_menu)), (titulo, "")]
    if request.method == "GET":
        valores = request.args.to_dict()
    else:
        valores = request.form.to_dict()
    valores.pop("token", None)
    campos = campos_de_operacion(datos, usuario, id_opcion, valores)
    paso = valores.pop("paso", "")
    # En 1.3, sin una herramienta elegida el formulario solo pide elegirla.
    solo_elegir = id_opcion == "1.3" and obtener_herramienta(datos, valores.get("codigo", "")) is None

    if paso == "cancelar":
        return pagina_mensaje(datos, usuario, titulo, movimientos.MENSAJE_CANCELADO)

    errores = []
    if paso in ["revisar", "guardar"] and not solo_elegir:
        argumentos = argumentos_de_operacion(datos, id_opcion, valores)
        errores = VALIDAR[id_opcion](datos, usuario, **argumentos)
        if len(errores) == 0 and paso == "revisar":
            return render_template("confirmar.html", usuario=usuario,
                                   rol=NOMBRES_ROL[usuario["rol"]], titulo=titulo,
                                   id_opcion=id_opcion, valores=valores, migas=migas,
                                   resumen=resumen_de_operacion(datos, id_opcion, campos, valores))
        if len(errores) == 0 and paso == "guardar":
            if id_opcion not in OPCIONES_SIN_OBSERVACIONES_EXTRA:
                argumentos["observaciones"] = valores.get("observaciones", "")
            exito, mensaje = REGISTRAR[id_opcion](datos, usuario, **argumentos)
            if exito:
                guardar_datos(datos)
            ofrecer_dano = (id_opcion == "2.2" and exito
                            and valores.get("estado_recibido") == "con daño")
            return render_template("resultado.html", usuario=usuario,
                                   rol=NOMBRES_ROL[usuario["rol"]], titulo=titulo, exito=exito,
                                   mensaje=mensaje, id_opcion=id_opcion, migas=migas,
                                   codigo=valores.get("codigo", "").strip().upper(),
                                   ofrecer_dano=ofrecer_dano)

    for campo in campos:
        campo["valor"] = valores.get(campo["nombre"], campo.get("defecto", ""))
    return render_template("formulario.html", usuario=usuario, rol=NOMBRES_ROL[usuario["rol"]],
                           titulo=titulo, id_opcion=id_opcion, campos=campos, errores=errores,
                           personal=PERSONAL, migas=migas, numero_menu=numero_menu,
                           categorias=consultas.categorias(datos), solo_elegir=solo_elegir)


# ---------------------------------------------------------- ficha técnica

@app.route("/ficha/<codigo>", methods=["GET", "POST"])
def ficha(codigo):
    """Muestra la ficha técnica; bodega y propietario pueden subir el archivo."""
    datos, avisos = cargar_datos()
    usuario = usuario_actual(datos)
    if usuario is None:
        return ir_a_login()
    herramienta = obtener_herramienta(datos, codigo)
    if herramienta is None:
        return pagina_mensaje(datos, usuario, "Ficha técnica",
                              "La herramienta '" + codigo + "' no existe en el catálogo.", "error")
    resultado = None
    if request.method == "POST":
        archivo = request.files.get("archivo")
        contenido = archivo.read() if archivo is not None else b""
        resultado = herramientas.guardar_archivo_ficha(datos, usuario, herramienta["codigo"], contenido)
        if resultado[0]:
            guardar_datos(datos)
    return render_template("ficha.html", usuario=usuario, rol=NOMBRES_ROL[usuario["rol"]],
                           titulo="Ficha técnica", herramienta=herramienta, resultado=resultado,
                           uso=movimientos.texto_de_uso(herramienta),
                           puede_editar=tiene_permiso(usuario, "1.3"),
                           migas=[("Ficha técnica de " + herramienta["codigo"], "")])


@app.route("/ficha/<codigo>/archivo")
def ficha_archivo(codigo):
    """Entrega el archivo de la ficha técnica a quien tiene sesión iniciada."""
    datos, avisos = cargar_datos()
    usuario = usuario_actual(datos)
    if usuario is None:
        return ir_a_login()
    herramienta = obtener_herramienta(datos, codigo)
    if herramienta is None or not herramienta.get("ficha_archivo"):
        return pagina_mensaje(datos, usuario, "Ficha técnica",
                              "Esta herramienta no tiene archivo de ficha técnica.", "error")
    return send_from_directory(herramientas.carpeta_fichas(), herramienta["ficha_archivo"])


# --------------------------------------------------------------- consultas

@app.route("/consulta/<id_opcion>")
def consulta(id_opcion):
    """Consultas 3.2 a 3.5: solo leen los datos y muestran el resultado."""
    datos, avisos = cargar_datos()
    usuario = usuario_actual(datos)
    if usuario is None:
        return ir_a_login()
    if id_opcion not in ["3.2", "3.3", "3.4", "3.5", "3.6"]:
        return pagina_mensaje(datos, usuario, "Consultas", "Opción no válida, intente de nuevo.",
                              "error")
    if not tiene_permiso(usuario, id_opcion):
        return pagina_mensaje(datos, usuario, "Opción " + id_opcion, MENSAJE_SIN_PERMISO, "error")
    titulo = ""
    for id_sub, texto in SUBMENUS["3"][1]:
        if id_sub == id_opcion:
            titulo = id_opcion + " " + texto
    comunes = {"usuario": usuario, "rol": NOMBRES_ROL[usuario["rol"]], "titulo": titulo,
               "migas": [(SUBMENUS["3"][0], url_for("submenu", numero="3")), (titulo, "")]}
    if id_opcion == "3.6":
        return render_template("mantenimiento.html", lista=consultas.consultar_mantenimiento(datos),
                               puede_registrar=tiene_permiso(usuario, "2.8"), **comunes)
    if id_opcion == "3.2":
        criterio = request.args.get("criterio", "").strip()[:60]
        return render_template("disponibles.html", criterio=criterio,
                               categorias=consultas.categorias(datos),
                               lista=consultas.consultar_disponibles(datos, criterio), **comunes)
    if id_opcion == "3.3":
        ver = request.args.get("ver", "todas")
        texto_hasta = request.args.get("hasta", "")
        hasta = leer_fecha_web(texto_hasta)
        error = "Fecha inválida. Elija una fecha de la lista." if texto_hasta != "" and hasta is None else ""
        return render_template("pendientes.html", ver=ver, texto_hasta=texto_hasta, error=error,
                               lista=consultas.consultar_pendientes(datos, ver == "vencidas", hasta),
                               **comunes)
    if id_opcion == "3.4":
        codigo_obra = request.args.get("obra", "")
        if usuario["rol"] == "maestro":
            codigo_obra = usuario.get("obra", "")
        error = ""
        lista = []
        if codigo_obra != "":
            error = consultas.error_en_consulta_por_obra(datos, usuario, codigo_obra)
            if error == "":
                lista = consultas.consultar_por_obra(datos, codigo_obra)
        return render_template("por_obra.html", codigo_obra=codigo_obra, error=error, lista=lista,
                               obras=opciones_obras(datos), es_maestro=usuario["rol"] == "maestro",
                               nombre=nombre_obra(datos, codigo_obra), **comunes)
    codigo = request.args.get("codigo", "")
    historial = consultas.consultar_historial(datos, codigo) if codigo != "" else None
    return render_template("historial.html", codigo=codigo, historial=historial,
                           nombres=consultas.NOMBRES_MOVIMIENTO,
                           opciones=opciones_herramientas(datos["herramientas"], "", datos),
                           **comunes)


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
