"""Pruebas automáticas de la página web de SICH (necesita Flask).

Usa el cliente de pruebas de Flask: no abre el navegador ni modifica datos/,
porque trabaja sobre una carpeta temporal.

Ejecutar:  py pruebas_web.py
"""

import os
import re
import tempfile

os.environ["SICH_DATOS"] = tempfile.mkdtemp(prefix="sich_web_")

import app as aplicacion  # noqa: E402
from sich.datos import cargar_datos, reiniciar_datos  # noqa: E402
from sich.catalogo import obtener_herramienta  # noqa: E402


def texto_de(respuesta):
    """Texto visible de una respuesta HTML, sin etiquetas."""
    html = respuesta.get_data(as_text=True)
    return " ".join(re.sub(r"<[^>]+>", " ", html).split())


def token_de(respuesta):
    """Lee el token oculto del formulario."""
    encontrado = re.search(r'name="token" value="([0-9a-f]+)"', respuesta.get_data(as_text=True))
    return encontrado.group(1) if encontrado else ""


def nuevo_cliente(usuario=None, contrasena=None):
    """Cliente de navegador simulado, con sesión iniciada si se indica usuario."""
    cliente = aplicacion.app.test_client()
    if usuario is not None:
        token = token_de(cliente.get("/login"))
        cliente.post("/login", data={"usuario": usuario, "contrasena": contrasena, "token": token})
        cliente.get("/")   # como el navegador: abre el inicio y recibe un token nuevo
    return cliente


def enviar(cliente, ruta, datos):
    """Envía un formulario POST con el token de la sesión."""
    with cliente.session_transaction() as sesion:
        datos = dict(datos, token=sesion.get("token", ""))
    return cliente.post(ruta, data=datos)


def caso_busqueda_flexible():
    c = nuevo_cliente("jpivaral", "bodega123")
    ok = True
    for consulta, codigo in [("La BailaRina", "COM-01"), ("azul makita", "PUL-03"),
                             ("bailarna", "COM-02"), ("la extensión naranja", "EXT-02")]:
        ok = ok and codigo in texto_de(c.get("/buscar", query_string={"q": consulta}))
    ok = ok and "Estas herramientas se parecen" in texto_de(c.get("/buscar?q=bailarna"))
    return ok


def caso_login_sin_limite():
    c = aplicacion.app.test_client()
    t = token_de(c.get("/login"))
    fallidos = [c.post("/login", data={"usuario": "jpivaral", "contrasena": "mala", "token": t})
                for numero in range(6)]
    bueno = c.post("/login", data={"usuario": "jpivaral", "contrasena": "bodega123", "token": t},
                   follow_redirects=True)
    return (all("Usuario o contraseña incorrectos" in texto_de(r) for r in fallidos)
            and "Bienvenido(a), Julián" in texto_de(bueno))


def caso_sin_token():
    c = nuevo_cliente("jpivaral", "bodega123")
    r = c.post("/operacion/2.1", data={"paso": "guardar", "codigo": "COM-01"})
    return r.status_code == 400 and "La página expiró" in texto_de(r)


def caso_salida_completa():
    c = nuevo_cliente("jpivaral", "bodega123")
    datos = {"codigo": "COM-01", "codigo_obra": "VN-014", "responsable": "Erick Santos",
             "fecha_salida": "2026-10-16T06:15", "devolucion_esperada": "2026-10-16T17:00",
             "residente_autoriza": "", "observaciones": ""}
    confirmar = enviar(c, "/operacion/2.1", dict(datos, paso="revisar"))
    guardar = enviar(c, "/operacion/2.1", dict(datos, paso="guardar"))
    guardados, avisos = cargar_datos()
    return ("¿Confirmar operación?" in texto_de(confirmar)
            and "Operación exitosa" in texto_de(guardar)
            and obtener_herramienta(guardados, "COM-01")["estado"] == "asignada")


def caso_reglas_compartidas():
    c = nuevo_cliente("jpivaral", "bodega123")
    r = enviar(c, "/operacion/2.1", {"paso": "revisar", "codigo": "COM-02", "codigo_obra": "VN-014",
                                        "responsable": "x", "fecha_salida": "2026-10-16T06:15",
                                        "devolucion_esperada": "2026-10-16T17:00"})
    return "COM-02 requiere revisión (memorando" in texto_de(r)


def caso_accesos_rapidos_por_rol():
    bodega = texto_de(nuevo_cliente("jpivaral", "bodega123").get("/"))
    residente = texto_de(nuevo_cliente("ecifuentes", "residente123").get("/"))
    gerente = texto_de(nuevo_cliente("prodas", "gerente123").get("/"))
    return ("Sacar herramienta a obra" in bodega and "Trasladar entre obras" not in bodega
            and "Trasladar entre obras" in residente and "Sacar herramienta a obra" not in gerente
            and "Ver devoluciones pendientes" in gerente)


def caso_paginas_de_error_y_sesion():
    c = aplicacion.app.test_client()
    sin_sesion = c.get("/operacion/2.1", follow_redirects=True)
    no_existe = nuevo_cliente("jpivaral", "bodega123").get("/no-existe")
    return ("Inicie sesión para continuar" in texto_de(sin_sesion)
            and no_existe.status_code == 404 and "Página no encontrada" in texto_de(no_existe))


def caso_ninguna_pendiente():
    """Ninguna opción de ningún menú queda pendiente; el permiso se sigue respetando."""
    from sich.menus import SUBMENUS
    c, texto = entrar("jpivaral", "bodega123")
    sin_pendientes = True
    for numero in SUBMENUS:
        pagina = texto_de(c.get("/menu/" + numero))
        sin_pendientes = sin_pendientes and "Pendiente" not in pagina.replace("Devoluciones pendientes", "")
        for id_opcion, nombre in SUBMENUS[numero][1]:
            r = c.get("/opcion/" + id_opcion, follow_redirects=True)
            sin_pendientes = sin_pendientes and r.status_code == 200
            sin_pendientes = sin_pendientes and "pendiente de implementación" not in texto_de(r)
    gerente, otro = entrar("prodas", "gerente123")
    return sin_pendientes and "No tiene permisos para esta opción" in texto_de(gerente.get("/opcion/2.1"))


def caso_codigo_bloqueado_por_ip():
    """El código de configuración sí tiene límite: borrar cookies no da más intentos."""
    for numero in range(3):
        c = aplicacion.app.test_client()
        c.post("/configurar", data={"codigo": "XXXX0000", "nombre": "x", "usuario": "x",
                                    "contrasena": "12345678", "repetida": "12345678",
                                    "token": token_de(c.get("/configurar"))})
    nuevo = aplicacion.app.test_client()
    return "Demasiados intentos" in texto_de(nuevo.get("/configurar"))


def caso_app_instalable():
    c = aplicacion.app.test_client()
    manifiesto = c.get("/manifest.webmanifest")
    sw = c.get("/sw.js")
    sin_red = c.get("/sin-conexion")
    instalar = c.get("/instalar")
    inicio = texto_de(c.get("/login")) + c.get("/login").get_data(as_text=True)
    return (manifiesto.status_code == 200 and "manifest+json" in manifiesto.content_type
            and manifiesto.get_json()["display"] == "standalone"
            and len(manifiesto.get_json()["icons"]) == 3
            and sw.status_code == 200 and "caches" in sw.get_data(as_text=True)
            and "Sin conexión a internet" in texto_de(sin_red)
            and "Agregar a inicio" in texto_de(instalar)
            and 'rel="manifest"' in inicio and "apple-touch-icon" in inicio
            and inicio.count("solo-navegador") == 2
            and "display-mode: standalone" in c.get("/static/estilos.css").get_data(as_text=True)
            and "solo-navegador" in c.get("/instalar").get_data(as_text=True)
            and c.get("/static/iconos/icono-512.png").status_code == 200)


def caso_modo_publico():
    """Publicada: las contraseñas de prueba no sirven; una contraseña cambiada sí."""
    aplicacion.PUBLICO = True
    try:
        c = aplicacion.app.test_client()
        r = c.post("/login", data={"usuario": "jpivaral", "contrasena": "bodega123",
                                   "token": token_de(c.get("/login"))})
        rechazada = "contraseñas de prueba no funcionan" in texto_de(r)
        from sich.datos import cifrar_contrasena, guardar_datos
        datos, avisos = cargar_datos()
        datos["usuarios"][0]["contrasena"] = cifrar_contrasena("Clave-Segura-2026")
        guardar_datos(datos)
        c2 = aplicacion.app.test_client()
        r2 = c2.post("/login", data={"usuario": "jpivaral", "contrasena": "Clave-Segura-2026",
                                     "token": token_de(c2.get("/login"))}, follow_redirects=True)
        return rechazada and "Bienvenido(a), Julián Pivaral" in texto_de(r2)
    finally:
        aplicacion.PUBLICO = False


def caso_contrasenas_de_entorno():
    """En el hosting, SICH_CONTRASENA_<USUARIO> reemplaza la contraseña de prueba al arrancar."""
    os.environ["SICH_CONTRASENA_ECIFUENTES"] = "Residente-Real-2026"
    try:
        aplicadas = aplicacion.aplicar_contrasenas_de_entorno()
        c = aplicacion.app.test_client()
        vieja = c.post("/login", data={"usuario": "ecifuentes", "contrasena": "residente123",
                                       "token": token_de(c.get("/login"))})
        c2 = aplicacion.app.test_client()
        nueva = c2.post("/login", data={"usuario": "ecifuentes", "contrasena": "Residente-Real-2026",
                                        "token": token_de(c2.get("/login"))}, follow_redirects=True)
        return (aplicadas == 1 and "Usuario o contraseña incorrectos" in texto_de(vieja)
                and "Bienvenido(a), Ing. Esteban Cifuentes" in texto_de(nueva))
    finally:
        del os.environ["SICH_CONTRASENA_ECIFUENTES"]


def caso_catalogo_web():
    """Registrar, asociar apodos y modificar desde la página."""
    c, texto = entrar("jpivaral", "bodega123")
    nueva = {"codigo": "gen-01", "nombre": "Generador", "categoria": "Eléctrico", "marca": "Honda",
             "estado": "disponible", "motor_o_cable": "si", "observaciones": "",
             "ficha_tecnica": "Revisar cada 400 h", "mantenimiento_cada_horas": "400"}
    confirmar = enviar(c, "/operacion/1.1", dict(nueva, paso="revisar"))
    guardar = enviar(c, "/operacion/1.1", dict(nueva, paso="guardar"))
    duplicada = enviar(c, "/operacion/1.1", dict(nueva, paso="revisar"))
    apodos = enviar(c, "/operacion/1.2", {"codigo": "GEN-01", "apodos": "la planta", "paso": "guardar"})
    encontrada = "GEN-01" in texto_de(c.get("/buscar", query_string={"q": "la planta"}))
    elegir = enviar(c, "/operacion/1.3", {"codigo": "GEN-01", "paso": "elegir"})
    cambio = enviar(c, "/operacion/1.3", {"codigo": "GEN-01", "nombre": "Generador grande",
                                          "categoria": "Eléctrico", "marca": "Honda",
                                          "motor_o_cable": "si", "observaciones": "",
                                          "ficha_tecnica": "Revisar cada 400 h",
                                          "mantenimiento_cada_horas": "400",
                                          "estado": "disponible", "paso": "guardar"})
    datos, avisos = cargar_datos()
    return ("¿Confirmar operación?" in texto_de(confirmar) and "herramienta registrada" in texto_de(guardar)
            and "Ya existe una herramienta" in texto_de(duplicada)
            and "apodos asociados" in texto_de(apodos) and encontrada
            and 'value="Generador"' in elegir.get_data(as_text=True)
            and "GEN-01 actualizada" in texto_de(cambio)
            and obtener_herramienta(datos, "GEN-01")["nombre"] == "Generador grande")


def caso_consultas_web():
    """Las consultas 3.2 a 3.5 muestran resultados reales."""
    c, texto = entrar("jpivaral", "bodega123")
    disponibles = texto_de(c.get("/consulta/3.2?criterio=perforacion"))
    pendientes = texto_de(c.get("/consulta/3.3"))
    vencidas = texto_de(c.get("/consulta/3.3?ver=vencidas"))
    por_obra = texto_de(c.get("/consulta/3.4?obra=VN-014"))
    historial = texto_de(c.get("/consulta/3.5?codigo=COM-02"))
    maestro, otro = entrar("esantos", "maestro123")
    obra_maestro = texto_de(maestro.get("/consulta/3.4?obra=VN-014"))
    return ("ROT-01" in disponibles and "COM-01" not in disponibles
            and "VENCIDA" in pendientes and "PERMANENCIA AUTORIZADA" in pendientes
            and "NIV-LAS-01" not in vencidas and "MEZ-01" in por_obra
            and "Daños (1)" in historial and "26/06/2026" in historial
            and "ROT-02" in obra_maestro and "MEZ-01" not in obra_maestro)


def caso_recepcion_web():
    """El maestro confirma lo de su obra, no lo de otra."""
    c, texto = entrar("esantos", "maestro123")
    otra = enviar(c, "/operacion/2.7", {"codigo": "MEZ-01", "fecha": "2026-10-16T07:00", "paso": "revisar"})
    propia = enviar(c, "/operacion/2.7", {"codigo": "ROT-02", "fecha": "2026-10-14T07:00",
                                          "observaciones": "", "paso": "guardar"})
    datos, avisos = cargar_datos()
    return ("solo puede confirmar las de su obra" in texto_de(otra)
            and "recepción confirmada" in texto_de(propia)
            and obtener_herramienta(datos, "ROT-02")["recepcion_confirmada_por"] == "Erick Santos")


def caso_contrasena_antigua():
    """Una contraseña guardada con el SHA-256 anterior sigue entrando y se actualiza sola."""
    import hashlib
    from sich.datos import guardar_datos
    datos, avisos = cargar_datos()
    datos["usuarios"][0]["contrasena"] = hashlib.sha256("Vieja-Clave-1".encode("utf-8")).hexdigest()
    guardar_datos(datos)
    c, texto = entrar("jpivaral", "Vieja-Clave-1")
    datos, avisos = cargar_datos()
    return ("Bienvenido(a), Julián" in texto
            and datos["usuarios"][0]["contrasena"].startswith("pbkdf2_sha256$")
            and "Vieja-Clave-1" not in datos["usuarios"][0]["contrasena"])


def caso_mantenimiento_web():
    """Las horas suman, la alarma bloquea la salida y el mantenimiento la libera."""
    c, texto = entrar("jpivaral", "bodega123")
    alarma_inicio = "Alarma de mantenimiento" in texto
    salida = {"codigo": "MEZ-03", "codigo_obra": "VN-014", "responsable": "Luis",
              "fecha_salida": "2026-10-31T07:00", "devolucion_esperada": "2026-10-31T17:00",
              "residente_autoriza": "", "observaciones": ""}
    bloqueada = enviar(c, "/operacion/2.1", dict(salida, paso="revisar"))
    estado = texto_de(c.get("/consulta/3.6"))
    mantenimiento = enviar(c, "/operacion/2.8", {"codigo": "MEZ-03", "fecha": "2026-10-31T10:00",
                                                 "realizado_por": "Taller", "observaciones": "",
                                                 "paso": "guardar"})
    libre = enviar(c, "/operacion/2.1", dict(salida, paso="guardar"))
    devolucion = enviar(c, "/operacion/2.2", {"codigo": "MEZ-03", "fecha_devolucion": "2026-10-31T19:00",
                                              "estado_recibido": "bueno", "observaciones": "",
                                              "paso": "guardar"})
    sin_sesion = aplicacion.app.test_client().get("/operacion/2.8")
    return (alarma_inicio and "ALARMA DE MANTENIMIENTO" in texto_de(bloqueada)
            and "VENCIDO" in estado and "ahora tiene 0 de 250 h" in texto_de(mantenimiento)
            and "salida registrada" in texto_de(libre)
            and "sumó 12 h (lleva 12 de 250 h)" in texto_de(devolucion)
            and sin_sesion.status_code == 302)


def caso_ficha_tecnica_web():
    """Subir, reemplazar y abrir la ficha; se rechaza lo que no es PDF, JPG o PNG."""
    import io
    c, texto = entrar("jpivaral", "bodega123")
    pagina = c.get("/ficha/COM-01")
    token = token_de(pagina)

    def subir(contenido, nombre):
        return c.post("/ficha/COM-01", data={"token": token, "archivo": (io.BytesIO(contenido), nombre)},
                      content_type="multipart/form-data")

    falso = subir(b"<script>alert(1)</script>", "ficha.pdf")
    vacio = subir(b"", "vacio.pdf")
    grande = subir(b"%PDF-" + b"0" * (5 * 1024 * 1024), "grande.pdf")
    pdf = subir(b"%PDF-1.4 ficha", "ficha.pdf")
    abierto = c.get("/ficha/COM-01/archivo")
    png = subir(b"\x89PNG\r\n\x1a\n" + b"0" * 10, "foto.png")
    datos, avisos = cargar_datos()
    gerente, otro = entrar("prodas", "gerente123")
    puede_ver = gerente.get("/ficha/COM-01/archivo").status_code == 200
    no_edita = "Guardar archivo" not in texto_de(gerente.get("/ficha/COM-01"))
    with gerente.session_transaction() as sesion:
        token_gerente = sesion.get("token", "")
    no_sube = gerente.post("/ficha/COM-01", data={"token": token_gerente,
                                                  "archivo": (io.BytesIO(b"%PDF-1"), "x.pdf")},
                           content_type="multipart/form-data")
    anonimo = aplicacion.app.test_client().get("/ficha/COM-01/archivo").status_code
    return ("debe ser PDF, JPG o PNG" in texto_de(falso) and "Elija un archivo" in texto_de(vacio)
            and "más de 5 MB" in texto_de(grande) and "ficha técnica de COM-01 guardada" in texto_de(pdf)
            and abierto.data == b"%PDF-1.4 ficha"
            and "guardada" in texto_de(png)
            and obtener_herramienta(datos, "COM-01")["ficha_archivo"] == "com01.png"
            and puede_ver and no_edita and "No tiene permisos" in texto_de(no_sube) and anonimo == 302)


def entrar(usuario, contrasena):
    """Cliente con sesión iniciada; devuelve (cliente, texto de la página de llegada)."""
    c = aplicacion.app.test_client()
    r = c.post("/login", data={"usuario": usuario, "contrasena": contrasena,
                               "token": token_de(c.get("/login"))}, follow_redirects=True)
    return c, texto_de(r)


def crear_propietario_de_prueba():
    """Configura el primer propietario con el código del archivo. Devuelve el cliente."""
    from sich import cuentas
    c = aplicacion.app.test_client()
    pagina = c.get("/configurar")
    with open(cuentas.ruta_codigo(), encoding="utf-8") as archivo:
        codigo = archivo.read().strip()
    r = c.post("/configurar", data={"codigo": codigo, "nombre": "Dueño de Prueba", "usuario": "dueno",
                                    "contrasena": "Dueno-2026!", "repetida": "Dueno-2026!",
                                    "token": token_de(pagina)}, follow_redirects=True)
    return c, texto_de(r)


def caso_configurar_propietario():
    from sich import cuentas
    c = aplicacion.app.test_client()
    aviso = "Configúrela aquí" in texto_de(c.get("/login"))
    pagina = c.get("/configurar")
    malo = c.post("/configurar", data={"codigo": "XXXX0000", "nombre": "Intruso", "usuario": "intruso",
                                       "contrasena": "12345678", "repetida": "12345678",
                                       "token": token_de(pagina)})
    rechazado = "código de configuración no es correcto" in texto_de(malo)
    cliente, texto = crear_propietario_de_prueba()
    creado = "Administrar cuentas" in texto and "Cuenta de propietario creada" in texto
    sin_codigo = not os.path.exists(cuentas.ruta_codigo())
    cerrado = "ya está configurado" in texto_de(aplicacion.app.test_client().get("/configurar",
                                                                                 follow_redirects=True))
    return aviso and rechazado and creado and sin_codigo and cerrado


def caso_crear_cuentas():
    dueno, texto = crear_propietario_de_prueba()
    pagina = dueno.get("/cuentas")
    r = dueno.post("/cuentas", data={"accion": "crear", "nombre": "Amigo Uno", "usuario": "amigo1",
                                     "rol": "gerente", "obra": "", "contrasena": "Amigo-Uno-1",
                                     "repetida": "Amigo-Uno-1", "token": token_de(pagina)})
    creada = "Cuenta creada: amigo1" in texto_de(r)
    repetida = dueno.post("/cuentas", data={"accion": "crear", "nombre": "Otro", "usuario": "amigo1",
                                            "rol": "gerente", "contrasena": "Amigo-Uno-1",
                                            "repetida": "Amigo-Uno-1", "token": token_de(pagina)})
    duplicado = "Ya existe una cuenta" in texto_de(repetida)
    amigo, bienvenida = entrar("amigo1", "Amigo-Uno-1")
    puede_entrar = "Bienvenido(a), Amigo Uno" in bienvenida
    bloqueado = "Solo el propietario" in texto_de(amigo.get("/cuentas"))
    return creada and duplicado and puede_entrar and bloqueado


def caso_restablecer_y_desactivar():
    dueno, texto = crear_propietario_de_prueba()
    pagina = dueno.get("/cuentas")
    r1 = dueno.post("/cuentas", data={"accion": "restablecer", "usuario": "jpivaral",
                                      "contrasena": "Nueva-Bodega-9", "repetida": "Nueva-Bodega-9",
                                      "token": token_de(pagina)})
    julian, bienvenida = entrar("jpivaral", "Nueva-Bodega-9")
    restablecida = "restablecida" in texto_de(r1) and "Bienvenido(a), Julián" in bienvenida
    r2 = dueno.post("/cuentas", data={"accion": "desactivar", "usuario": "jpivaral",
                                      "token": token_de(pagina)})
    desactivada = "desactivada" in texto_de(r2)
    sesion_cerrada = "Usuario Contraseña Ver Entrar" in texto_de(julian.get("/", follow_redirects=True))
    c, intento = entrar("jpivaral", "Nueva-Bodega-9")
    no_entra = "incorrectos" in intento
    propia = dueno.post("/cuentas", data={"accion": "desactivar", "usuario": "dueno",
                                          "token": token_de(pagina)})
    no_se_bloquea = "No puede desactivar su propia cuenta" in texto_de(propia)
    return restablecida and desactivada and sesion_cerrada and no_entra and no_se_bloquea


def caso_mi_contrasena():
    c, bienvenida = entrar("esantos", "maestro123")
    pagina = c.get("/mi-contrasena")
    mala = c.post("/mi-contrasena", data={"actual": "otra-cosa", "nueva": "Maestro-Nuevo-1",
                                          "repetida": "Maestro-Nuevo-1", "token": token_de(pagina)})
    buena = c.post("/mi-contrasena", data={"actual": "maestro123", "nueva": "Maestro-Nuevo-1",
                                           "repetida": "Maestro-Nuevo-1", "token": token_de(pagina)})
    c2, otra = entrar("esantos", "Maestro-Nuevo-1")
    return ("no es correcta" in texto_de(mala) and "se cambió correctamente" in texto_de(buena)
            and "Bienvenido(a), Erick Santos" in otra)


CASOS = [
    ("W-01", "Búsqueda flexible (mayúsculas, artículos, orden, errores de escritura)", caso_busqueda_flexible),
    ("W-02", "Inicio de sesión sin límite de intentos", caso_login_sin_limite),
    ("W-03", "Formulario sin token es rechazado", caso_sin_token),
    ("W-04", "Salida completa: revisar, confirmar y guardar", caso_salida_completa),
    ("W-05", "La web aplica las mismas reglas que la consola", caso_reglas_compartidas),
    ("W-06", "Accesos rápidos según el rol", caso_accesos_rapidos_por_rol),
    ("W-07", "Sesión vencida y página inexistente", caso_paginas_de_error_y_sesion),
    ("W-08", "Ninguna opción queda pendiente y se respetan los permisos", caso_ninguna_pendiente),
    ("W-09", "Código de configuración: límite por IP aunque se borren las cookies", caso_codigo_bloqueado_por_ip),
    ("W-10", "App instalable: manifiesto, service worker, sin conexión, íconos", caso_app_instalable),
    ("W-11", "Versión publicada rechaza contraseñas de prueba", caso_modo_publico),
    ("W-12", "Contraseñas reales desde variables de entorno del hosting", caso_contrasenas_de_entorno),
    ("W-13", "Configurar el primer propietario con el código del servidor", caso_configurar_propietario),
    ("W-14", "El propietario crea cuentas; los demás no pueden", caso_crear_cuentas),
    ("W-15", "Restablecer contraseña y desactivar una cuenta", caso_restablecer_y_desactivar),
    ("W-16", "Cada usuario cambia su propia contraseña", caso_mi_contrasena),
    ("W-17", "Catálogo: registrar, asociar apodos y modificar", caso_catalogo_web),
    ("W-18", "Consultas 3.2 a 3.5 con resultados reales", caso_consultas_web),
    ("W-19", "Confirmar recepción: solo la obra del maestro", caso_recepcion_web),
    ("W-20", "Contraseña antigua entra y se actualiza a PBKDF2", caso_contrasena_antigua),
    ("W-21", "Horas de uso, alarma y registro de mantenimiento", caso_mantenimiento_web),
    ("W-22", "Ficha técnica: subir, reemplazar, abrir y permisos", caso_ficha_tecnica_web),
]


if __name__ == "__main__":
    aprobados = 0
    lineas = []
    for identificador, descripcion, funcion in CASOS:
        reiniciar_datos()
        aplicacion.INTENTOS_POR_IP.clear()
        from sich import cuentas as modulo_cuentas
        if os.path.exists(modulo_cuentas.ruta_codigo()):
            os.remove(modulo_cuentas.ruta_codigo())
        resultado = funcion()
        if resultado:
            aprobados = aprobados + 1
        lineas.append(identificador + " " + ("Satisfactorio   " if resultado else "No satisfactorio")
                      + " " + descripcion)
        print(lineas[-1])
    lineas.append("")
    lineas.append("Resultado: " + str(aprobados) + " de " + str(len(CASOS))
                  + " pruebas web satisfactorias.")
    print(lineas[-1])
    carpeta = os.path.join(os.path.dirname(os.path.abspath(__file__)), "evidencias")
    os.makedirs(carpeta, exist_ok=True)
    with open(os.path.join(carpeta, "pruebas_web.txt"), "w", encoding="utf-8") as archivo:
        archivo.write("> py pruebas_web.py\n" + "\n".join(lineas) + "\n")
