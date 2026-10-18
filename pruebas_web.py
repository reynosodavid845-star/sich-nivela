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


def caso_login_y_bloqueo():
    c = aplicacion.app.test_client()
    t = token_de(c.get("/login"))
    r1 = c.post("/login", data={"usuario": "jpivaral", "contrasena": "mala", "token": t})
    c.post("/login", data={"usuario": "jpivaral", "contrasena": "mala", "token": t})
    r3 = c.post("/login", data={"usuario": "jpivaral", "contrasena": "mala", "token": t})
    r4 = c.post("/login", data={"usuario": "jpivaral", "contrasena": "bodega123", "token": t})
    return ("Le quedan 2 intento(s)" in texto_de(r1) and "Se agotaron los 3 intentos" in texto_de(r3)
            and "Espere" in texto_de(r4))


def caso_sin_token():
    c = nuevo_cliente("jpivaral", "bodega123")
    r = c.post("/movimientos/2.1", data={"paso": "guardar", "codigo": "COM-01"})
    return r.status_code == 400 and "La página expiró" in texto_de(r)


def caso_salida_completa():
    c = nuevo_cliente("jpivaral", "bodega123")
    datos = {"codigo": "COM-01", "codigo_obra": "VN-014", "responsable": "Erick Santos",
             "fecha_salida": "2026-10-16T06:15", "devolucion_esperada": "2026-10-16T17:00",
             "residente_autoriza": "", "observaciones": ""}
    confirmar = enviar(c, "/movimientos/2.1", dict(datos, paso="revisar"))
    guardar = enviar(c, "/movimientos/2.1", dict(datos, paso="guardar"))
    guardados, avisos = cargar_datos()
    return ("¿Confirmar operación?" in texto_de(confirmar)
            and "Operación exitosa" in texto_de(guardar)
            and obtener_herramienta(guardados, "COM-01")["estado"] == "asignada")


def caso_reglas_compartidas():
    c = nuevo_cliente("jpivaral", "bodega123")
    r = enviar(c, "/movimientos/2.1", {"paso": "revisar", "codigo": "COM-02", "codigo_obra": "VN-014",
                                        "responsable": "x", "fecha_salida": "2026-10-16T06:15",
                                        "devolucion_esperada": "2026-10-16T17:00"})
    return "COM-02 requiere revisión (memorando" in texto_de(r)


def caso_accesos_rapidos_por_rol():
    bodega = texto_de(nuevo_cliente("jpivaral", "bodega123").get("/"))
    residente = texto_de(nuevo_cliente("ecifuentes", "residente123").get("/"))
    gerente = texto_de(nuevo_cliente("prodas", "gerente123").get("/"))
    return ("Sacar herramienta a obra" in bodega and "Trasladar entre obras" not in bodega
            and "Trasladar entre obras" in residente and "¿Qué necesita hacer?" not in gerente)


def caso_paginas_de_error_y_sesion():
    c = aplicacion.app.test_client()
    sin_sesion = c.get("/movimientos/2.1", follow_redirects=True)
    no_existe = nuevo_cliente("jpivaral", "bodega123").get("/no-existe")
    return ("Inicie sesión para continuar" in texto_de(sin_sesion)
            and no_existe.status_code == 404 and "Página no encontrada" in texto_de(no_existe))


def caso_pendiente_y_permiso():
    c = nuevo_cliente("prodas", "gerente123")
    return ("No tiene permisos para esta opción" in texto_de(c.get("/opcion/2.1"))
            and "Funcionalidad pendiente de implementación" in texto_de(c.get("/opcion/3.2")))


def caso_bloqueo_por_ip():
    """Borrar cookies (cliente nuevo) no da más intentos: el bloqueo es por IP."""
    for numero in range(3):
        c = aplicacion.app.test_client()
        c.post("/login", data={"usuario": "x", "contrasena": "y", "token": token_de(c.get("/login"))})
    nuevo = aplicacion.app.test_client()
    return "Espere" in texto_de(nuevo.get("/login"))


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
    ("W-02", "Inicio de sesión: 3 intentos y bloqueo de 5 minutos", caso_login_y_bloqueo),
    ("W-03", "Formulario sin token es rechazado", caso_sin_token),
    ("W-04", "Salida completa: revisar, confirmar y guardar", caso_salida_completa),
    ("W-05", "La web aplica las mismas reglas que la consola", caso_reglas_compartidas),
    ("W-06", "Accesos rápidos según el rol", caso_accesos_rapidos_por_rol),
    ("W-07", "Sesión vencida y página inexistente", caso_paginas_de_error_y_sesion),
    ("W-08", "Opción sin permiso y opción pendiente", caso_pendiente_y_permiso),
    ("W-09", "Bloqueo por IP aunque se borren las cookies", caso_bloqueo_por_ip),
    ("W-10", "App instalable: manifiesto, service worker, sin conexión, íconos", caso_app_instalable),
    ("W-11", "Versión publicada rechaza contraseñas de prueba", caso_modo_publico),
    ("W-12", "Contraseñas reales desde variables de entorno del hosting", caso_contrasenas_de_entorno),
    ("W-13", "Configurar el primer propietario con el código del servidor", caso_configurar_propietario),
    ("W-14", "El propietario crea cuentas; los demás no pueden", caso_crear_cuentas),
    ("W-15", "Restablecer contraseña y desactivar una cuenta", caso_restablecer_y_desactivar),
    ("W-16", "Cada usuario cambia su propia contraseña", caso_mi_contrasena),
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
