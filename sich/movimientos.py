"""Módulo 2 - Movimientos de herramientas (IMPLEMENTADO COMPLETO).

Cada funcionalidad tiene tres partes:
  - validar_xxx(...)   -> lista de errores (vacía si todo está bien).
  - registrar_xxx(...) -> aplica el cambio en los datos y devuelve (exito, mensaje).
  - proceso_xxx(...)   -> pide los datos en la consola, confirma y guarda.
La página web (app.py) usa las mismas funciones validar_xxx y registrar_xxx,
así las reglas de negocio están escritas una sola vez.
"""

from datetime import datetime, timedelta

from sich.autenticacion import MENSAJE_SIN_PERMISO, tiene_permiso
from sich.busqueda import seleccionar_herramienta
from sich.catalogo import descripcion_corta, nombre_obra, obras_activas, obtener_herramienta, \
    obtener_obra
from sich.datos import guardar_datos, siguiente_id
from sich.validaciones import confirmar, fecha_a_texto, fecha_para_mostrar, leer_fecha_hora, \
    leer_opcion, leer_texto_minimo, leer_texto_no_vacio, leer_texto_opcional, mostrar_titulo, \
    texto_a_fecha

# Horario normal de devolución (16:30 a 17:15), salvo que el residente autorice otro.
INICIO_DEVOLUCION = (16, 30)
FIN_DEVOLUCION = (17, 15)

# Palabras que obligan a revisar un equipo con motor o cable (memorando 14/02/2026).
PALABRAS_DE_REVISION = ["ruido", "golpe", "cable"]

ESTADOS_QUE_SE_REVISAN = ["dañada", "requiere revisión", "en reparación"]

MINIMO_DESCRIPCION_DANO = 5

MENSAJE_CANCELADO = "Operación cancelada. No se guardó ningún cambio."


# =====================================================================
# Funciones de apoyo
# =====================================================================

def momento_actual(ahora):
    """Devuelve 'ahora' si se recibió (pruebas); si no, la fecha y hora actual."""
    if ahora is None:
        return datetime.now().replace(second=0, microsecond=0)
    return ahora


def agregar_movimiento(datos, tipo, herramienta, obra_origen, obra_destino, responsable,
                       usuario, fecha_hora, observaciones, ahora, devolucion_esperada=""):
    """Agrega un movimiento al historial con id autoincremental y lo devuelve."""
    movimiento = {
        "id": siguiente_id(datos["movimientos"]),
        "tipo": tipo,
        "codigo": herramienta["codigo"],
        "obra_origen": obra_origen,
        "obra_destino": obra_destino,
        "responsable": responsable,
        "registrado_por": usuario["usuario"],
        "fecha_hora": fecha_a_texto(fecha_hora),
        "fecha_registro": fecha_a_texto(momento_actual(ahora)),
        "devolucion_esperada": devolucion_esperada,
        "observaciones": observaciones,
    }
    datos["movimientos"].append(movimiento)
    return movimiento


def autorizacion_vigente(datos, codigo, codigo_obra, momento):
    """Devuelve la autorización de permanencia vigente en 'momento', o None."""
    for autorizacion in datos["autorizaciones"]:
        if autorizacion["codigo"] == codigo and autorizacion["obra"] == codigo_obra:
            inicio = texto_a_fecha(autorizacion["fecha_inicio"])
            fin = texto_a_fecha(autorizacion["fecha_fin"])
            if inicio <= momento <= fin:
                return autorizacion
    return None


def esta_vencida(datos, herramienta, ahora=None):
    """True si la herramienta está en obra, pasó su devolución esperada y no tiene
    una autorización de permanencia vigente."""
    if herramienta["ubicacion"] == "Bodega" or herramienta["devolucion_esperada"] == "":
        return False
    momento = momento_actual(ahora)
    if texto_a_fecha(herramienta["devolucion_esperada"]) >= momento:
        return False
    vigente = autorizacion_vigente(datos, herramienta["codigo"], herramienta["ubicacion"], momento)
    return vigente is None


def intervalo_mantenimiento(herramienta):
    """Horas entre mantenimientos según la ficha técnica (0 = no tiene plan)."""
    return herramienta.get("mantenimiento_cada_horas", 0)


def horas_de_uso(herramienta, ahora=None):
    """Horas acumuladas desde el último mantenimiento, contando la salida en curso."""
    horas = herramienta.get("horas_uso", 0)
    if herramienta["ubicacion"] != "Bodega" and herramienta["fecha_salida"] != "":
        transcurrido = momento_actual(ahora) - texto_a_fecha(herramienta["fecha_salida"])
        horas = horas + max(transcurrido.total_seconds() / 3600, 0)
    return round(horas, 1)


def texto_horas(horas):
    """Convierte 12.0 en '12' y 12.5 en '12.5'."""
    return format(round(horas, 1), ".10g")


def texto_de_uso(herramienta, ahora=None):
    """Texto como '12 de 400 h'. Vacío si la herramienta no tiene plan."""
    intervalo = intervalo_mantenimiento(herramienta)
    if intervalo == 0:
        return ""
    return texto_horas(horas_de_uso(herramienta, ahora)) + " de " + str(intervalo) + " h"


def mantenimiento_vencido(herramienta, ahora=None):
    """True si la herramienta ya llegó a las horas que indica su ficha técnica."""
    intervalo = intervalo_mantenimiento(herramienta)
    return intervalo > 0 and horas_de_uso(herramienta, ahora) >= intervalo


def fuera_de_horario(fecha):
    """True si la hora queda fuera del horario de devolución 16:30 - 17:15."""
    hora = (fecha.hour, fecha.minute)
    return hora < INICIO_DEVOLUCION or hora > FIN_DEVOLUCION


def devolucion_por_defecto(fecha_salida):
    """Sugiere la devolución a las 17:00 del mismo día (o del siguiente si ya pasó)."""
    sugerida = fecha_salida.replace(hour=17, minute=0)
    if sugerida <= fecha_salida:
        sugerida = sugerida + timedelta(days=1)
    return sugerida


def motivo_bloqueo_salida(herramienta):
    """Explica por qué una herramienta no puede salir. Texto vacío = sí puede salir."""
    codigo = herramienta["codigo"]
    estado = herramienta["estado"]
    if estado == "asignada" or herramienta["ubicacion"] != "Bodega":
        return (codigo + " ya está asignada en la obra " + herramienta["ubicacion"]
                + " (responsable: " + herramienta["responsable"] + "). "
                "Registre primero la devolución o un traslado.")
    if estado == "dañada":
        return codigo + " está dañada: registre una revisión antes de sacarla."
    if estado == "requiere revisión":
        return (codigo + " requiere revisión (memorando 14/02/2026): "
                "registre una revisión antes de sacarla.")
    if estado == "en reparación":
        return (codigo + " está en reparación: no puede salir hasta que una revisión "
                "la declare apta.")
    if estado == "dada de baja":
        return codigo + " está dada de baja y no se debe usar."
    if mantenimiento_vencido(herramienta):
        return ("ALARMA DE MANTENIMIENTO: " + codigo + " llegó a " + texto_de_uso(herramienta)
                + ". No se puede entregar: mándela a mantenimiento y regístrelo en "
                  "2.8 Registrar mantenimiento.")
    return ""


def validar_obra_destino(datos, codigo_obra):
    """Revisa que la obra exista, no sea la bodega y esté activa. Devuelve el error o ''."""
    obra = obtener_obra(datos, codigo_obra)
    if obra is None:
        return "La obra '" + codigo_obra + "' no existe. Elija una obra de la lista."
    if obra["es_bodega"]:
        return "La bodega no es una obra de destino. Elija una obra de la lista."
    if not obra["activa"]:
        return "La obra " + obra["codigo"] + " no está activa. Elija una obra de la lista."
    return ""


def herramientas_en_obra(datos):
    """Herramientas que están fuera de bodega (en alguna obra)."""
    lista = []
    for herramienta in datos["herramientas"]:
        if herramienta["ubicacion"] != "Bodega":
            lista.append(herramienta)
    return lista


def herramientas_disponibles_en_bodega(datos):
    """Herramientas disponibles en bodega (las únicas que pueden salir)."""
    lista = []
    for herramienta in datos["herramientas"]:
        if motivo_bloqueo_salida(herramienta) == "":
            lista.append(herramienta)
    return lista


def herramientas_por_revisar(datos):
    """Herramientas dañadas, en reparación o que requieren revisión."""
    lista = []
    for herramienta in datos["herramientas"]:
        if herramienta["estado"] in ESTADOS_QUE_SE_REVISAN:
            lista.append(herramienta)
    return lista


def requiere_revision_por_observacion(herramienta, observaciones):
    """True si un equipo con motor o cable vuelve con golpes, ruido o cable expuesto."""
    if not herramienta["motor_o_cable"]:
        return False
    texto = observaciones.lower()
    for palabra in PALABRAS_DE_REVISION:
        if palabra in texto:
            return True
    return False


def olvidar_recepcion(herramienta):
    """Borra la confirmación de recepción: la herramienta cambió de manos."""
    herramienta["recepcion_confirmada_por"] = ""
    herramienta["recepcion_fecha"] = ""


def mostrar_lista(titulo, herramientas):
    """Imprime una lista de herramientas, una por línea."""
    print(titulo)
    for herramienta in herramientas:
        print("  -", descripcion_corta(herramienta))


def mostrar_resumen(lineas):
    """Imprime el resumen de una operación antes de confirmarla."""
    print("\n--- Resumen de la operación ---")
    for etiqueta, valor in lineas:
        print(" ", etiqueta + ":", valor)
    print("-------------------------------")


def herramienta_o_error(datos, codigo, errores):
    """Busca la herramienta por código; si no existe agrega el error y devuelve None."""
    herramienta = obtener_herramienta(datos, codigo)
    if herramienta is None:
        errores.append("La herramienta '" + codigo + "' no existe en el catálogo.")
    return herramienta


# =====================================================================
# 2.1 Registrar salida
# =====================================================================

def validar_salida(datos, usuario, codigo, codigo_obra, responsable, fecha_salida,
                   devolucion_esperada, residente_autoriza=""):
    """Revisa todas las reglas de una salida. Devuelve la lista de errores."""
    if not tiene_permiso(usuario, "2.1"):
        return [MENSAJE_SIN_PERMISO]
    errores = []
    herramienta = herramienta_o_error(datos, codigo, errores)
    if herramienta is None:
        return errores
    motivo = motivo_bloqueo_salida(herramienta)
    if motivo != "":
        errores.append(motivo)
    error_obra = validar_obra_destino(datos, codigo_obra)
    if error_obra != "":
        errores.append(error_obra)
    if responsable.strip() == "":
        errores.append("Indique el responsable que recibe la herramienta.")
    if fecha_salida is None or devolucion_esperada is None:
        errores.append("Fecha inválida. Revise la fecha de salida y la de devolución.")
    elif devolucion_esperada <= fecha_salida:
        errores.append("La devolución esperada debe ser posterior a la salida ("
                       + fecha_salida.strftime("%d/%m/%Y %H:%M") + ").")
    elif fuera_de_horario(devolucion_esperada) and residente_autoriza.strip() == "":
        errores.append("La devolución esperada (" + devolucion_esperada.strftime("%H:%M")
                       + ") queda fuera del horario 16:30-17:15: indique el residente "
                         "que autorizó ese horario.")
    return errores


def registrar_salida(datos, usuario, codigo, codigo_obra, responsable, fecha_salida,
                     devolucion_esperada, residente_autoriza="", observaciones="", ahora=None):
    """Registra la salida: la herramienta queda 'asignada' en la obra. Devuelve (exito, mensaje)."""
    errores = validar_salida(datos, usuario, codigo, codigo_obra, responsable, fecha_salida,
                             devolucion_esperada, residente_autoriza)
    if len(errores) > 0:
        return False, " ".join(errores)
    herramienta = obtener_herramienta(datos, codigo)
    obra = obtener_obra(datos, codigo_obra)
    notas = observaciones.strip()
    if residente_autoriza.strip() != "":
        notas = (notas + " Horario de devolución autorizado por: "
                 + residente_autoriza.strip() + ".").strip()
    herramienta["estado"] = "asignada"
    herramienta["ubicacion"] = obra["codigo"]
    herramienta["responsable"] = responsable.strip()
    herramienta["fecha_salida"] = fecha_a_texto(fecha_salida)
    herramienta["devolucion_esperada"] = fecha_a_texto(devolucion_esperada)
    olvidar_recepcion(herramienta)
    agregar_movimiento(datos, "salida", herramienta, "Bodega", obra["codigo"],
                       responsable.strip(), usuario, fecha_salida, notas, ahora,
                       fecha_a_texto(devolucion_esperada))
    return True, ("Operación exitosa: salida registrada. " + herramienta["codigo"]
                  + " quedó ASIGNADA en " + nombre_obra(datos, obra["codigo"])
                  + ", responsable " + responsable.strip() + ", devolución esperada "
                  + devolucion_esperada.strftime("%d/%m/%Y %H:%M") + "."
                  + aviso_de_horas_en_salida(herramienta, fecha_salida, devolucion_esperada))


def aviso_de_horas_en_salida(herramienta, fecha_salida, devolucion_esperada):
    """Avisa si con esta salida la herramienta llegaría a su mantenimiento."""
    intervalo = intervalo_mantenimiento(herramienta)
    if intervalo == 0:
        return ""
    previstas = (devolucion_esperada - fecha_salida).total_seconds() / 3600
    usadas = herramienta.get("horas_uso", 0)
    if usadas + previstas >= intervalo:
        return (" Aviso: lleva " + texto_horas(usadas) + " de " + str(intervalo)
                + " h y esta salida prevé " + texto_horas(previstas)
                + " h: llegará a su mantenimiento.")
    return ""


def pedir_obra_destino(datos):
    """Muestra las obras activas y pide una hasta que sea válida."""
    print("\nObras activas:")
    for obra in obras_activas(datos):
        print("  -", obra["codigo"], "-", obra["nombre"])
    while True:
        codigo_obra = leer_texto_no_vacio("Obra de destino (código, ej. VN-014): ")
        error = validar_obra_destino(datos, codigo_obra)
        if error == "":
            return obtener_obra(datos, codigo_obra)["codigo"]
        print(error)


def pedir_devolucion_esperada(fecha_salida):
    """Pide la devolución esperada; si queda fuera de horario pide al residente.

    Devuelve (fecha_devolucion, residente_que_autoriza).
    """
    while True:
        devolucion = leer_fecha_hora("Fecha y hora esperada de devolución",
                                     devolucion_por_defecto(fecha_salida))
        if devolucion <= fecha_salida:
            print("La devolución esperada debe ser posterior a la salida.")
            continue
        if not fuera_de_horario(devolucion):
            return devolucion, ""
        print("Advertencia: la devolución queda fuera del horario 16:30-17:15.")
        if confirmar("¿El residente autorizó este horario?"):
            residente = leer_texto_no_vacio("Nombre del residente que autorizó: ")
            return devolucion, residente
        print("Escriba otra fecha y hora de devolución.")


def proceso_registrar_salida(datos, usuario):
    """Opción 2.1 en consola."""
    mostrar_titulo("2.1 REGISTRAR SALIDA DE HERRAMIENTA")
    if len(herramientas_disponibles_en_bodega(datos)) == 0:
        print("No hay herramientas disponibles en bodega para sacar.")
        return
    herramienta = seleccionar_herramienta(datos)
    if herramienta is None:
        print(MENSAJE_CANCELADO)
        return
    motivo = motivo_bloqueo_salida(herramienta)
    if motivo != "":
        print("No se puede registrar la salida: " + motivo)
        return
    if intervalo_mantenimiento(herramienta) > 0:
        print("Horas de uso:", texto_de_uso(herramienta))
    codigo_obra = pedir_obra_destino(datos)
    responsable = leer_texto_no_vacio("Responsable que recibe la herramienta: ")
    fecha_salida = leer_fecha_hora("Fecha y hora de salida", momento_actual(None))
    devolucion, residente = pedir_devolucion_esperada(fecha_salida)
    observaciones = leer_texto_opcional("Observaciones (opcional, Enter para omitir): ")
    resumen = [("Herramienta", descripcion_corta(herramienta)),
               ("Obra de destino", nombre_obra(datos, codigo_obra)),
               ("Responsable", responsable),
               ("Salida", fecha_salida.strftime("%d/%m/%Y %H:%M")),
               ("Devolución esperada", devolucion.strftime("%d/%m/%Y %H:%M"))]
    if residente != "":
        resumen.append(("Horario autorizado por", residente))
    mostrar_resumen(resumen)
    if not confirmar("¿Confirmar operación?"):
        print(MENSAJE_CANCELADO)
        return
    exito, mensaje = registrar_salida(datos, usuario, herramienta["codigo"], codigo_obra,
                                      responsable, fecha_salida, devolucion, residente,
                                      observaciones)
    print("\n" + mensaje)
    if exito:
        guardar_datos(datos)


# =====================================================================
# 2.2 Registrar devolución
# =====================================================================

def validar_devolucion(datos, usuario, codigo, fecha_devolucion, estado_recibido):
    """Revisa las reglas de una devolución. Devuelve la lista de errores."""
    if not tiene_permiso(usuario, "2.2"):
        return [MENSAJE_SIN_PERMISO]
    errores = []
    herramienta = herramienta_o_error(datos, codigo, errores)
    if herramienta is None:
        return errores
    if herramienta["ubicacion"] == "Bodega":
        errores.append(herramienta["codigo"] + " está en bodega: no tiene una salida "
                                               "pendiente de devolución.")
        return errores
    if estado_recibido not in ["bueno", "con daño"]:
        errores.append("El estado recibido debe ser 'bueno' o 'con daño'.")
    if fecha_devolucion is None:
        errores.append("Fecha inválida. Use el formato DD/MM/AAAA HH:MM.")
    elif herramienta["fecha_salida"] != "" \
            and fecha_devolucion < texto_a_fecha(herramienta["fecha_salida"]):
        errores.append("La fecha de devolución no puede ser anterior a la salida ("
                       + fecha_para_mostrar(herramienta["fecha_salida"]) + ").")
    return errores


def llego_tarde(datos, herramienta, fecha_devolucion):
    """True si se devolvió después de lo esperado y sin autorización vigente."""
    if herramienta["devolucion_esperada"] == "":
        return False
    if fecha_devolucion <= texto_a_fecha(herramienta["devolucion_esperada"]):
        return False
    vigente = autorizacion_vigente(datos, herramienta["codigo"], herramienta["ubicacion"],
                                   fecha_devolucion)
    return vigente is None


def estado_despues_de_devolucion(herramienta, estado_recibido, observaciones):
    """Decide el estado con que queda la herramienta al volver a bodega."""
    if estado_recibido == "con daño":
        return "requiere revisión"
    if herramienta["estado"] == "dañada":
        return "dañada"
    if requiere_revision_por_observacion(herramienta, observaciones):
        return "requiere revisión"
    return "disponible"


def registrar_devolucion(datos, usuario, codigo, fecha_devolucion, estado_recibido,
                         observaciones="", ahora=None):
    """Registra la devolución: la herramienta vuelve a Bodega. Devuelve (exito, mensaje)."""
    errores = validar_devolucion(datos, usuario, codigo, fecha_devolucion, estado_recibido)
    if len(errores) > 0:
        return False, " ".join(errores)
    herramienta = obtener_herramienta(datos, codigo)
    obra_origen = herramienta["ubicacion"]
    tarde = llego_tarde(datos, herramienta, fecha_devolucion)
    esperada = fecha_para_mostrar(herramienta["devolucion_esperada"])
    nuevo_estado = estado_despues_de_devolucion(herramienta, estado_recibido, observaciones)
    horas_de_esta_salida = 0
    if herramienta["fecha_salida"] != "":
        transcurrido = fecha_devolucion - texto_a_fecha(herramienta["fecha_salida"])
        horas_de_esta_salida = round(transcurrido.total_seconds() / 3600, 1)
    horas_totales = round(herramienta.get("horas_uso", 0) + horas_de_esta_salida, 1)
    notas = "Estado recibido: " + estado_recibido + "."
    if observaciones.strip() != "":
        notas = notas + " " + observaciones.strip()
    notas = notas + " Uso: " + texto_horas(horas_de_esta_salida) + " h."
    if tarde:
        notas = notas + " Devolución tardía (se esperaba " + esperada + ")."
    agregar_movimiento(datos, "devolucion", herramienta, obra_origen, "Bodega",
                       herramienta["responsable"], usuario, fecha_devolucion, notas, ahora)
    herramienta["estado"] = nuevo_estado
    herramienta["horas_uso"] = horas_totales
    herramienta["ubicacion"] = "Bodega"
    herramienta["responsable"] = ""
    herramienta["fecha_salida"] = ""
    herramienta["devolucion_esperada"] = ""
    olvidar_recepcion(herramienta)
    mensaje = ("Operación exitosa: devolución registrada. " + herramienta["codigo"]
               + " está en Bodega con estado '" + nuevo_estado + "'.")
    if tarde:
        mensaje = mensaje + " La devolución llegó TARDE (se esperaba " + esperada + ")."
    else:
        mensaje = mensaje + " La devolución llegó a tiempo."
    if nuevo_estado == "requiere revisión":
        mensaje = mensaje + " Debe registrar una revisión antes de volver a sacarla."
    mensaje = mensaje + " Esta salida sumó " + texto_horas(horas_de_esta_salida) + " h"
    if intervalo_mantenimiento(herramienta) > 0:
        mensaje = mensaje + " (lleva " + texto_de_uso(herramienta) + ")"
    mensaje = mensaje + "."
    if mantenimiento_vencido(herramienta):
        mensaje = (mensaje + " ALARMA DE MANTENIMIENTO: no se puede volver a entregar hasta "
                             "registrar el mantenimiento.")
    return True, mensaje


def proceso_registrar_devolucion(datos, usuario):
    """Opción 2.2 en consola."""
    mostrar_titulo("2.2 REGISTRAR DEVOLUCIÓN")
    en_obra = herramientas_en_obra(datos)
    if len(en_obra) == 0:
        print("No hay herramientas en obra pendientes de devolución.")
        return
    mostrar_lista("Herramientas que están en obra:", en_obra)
    herramienta = seleccionar_herramienta(datos)
    if herramienta is None:
        print(MENSAJE_CANCELADO)
        return
    if herramienta["ubicacion"] == "Bodega":
        print(herramienta["codigo"], "está en bodega: no tiene una salida pendiente de devolución.")
        return
    print("Salió a", nombre_obra(datos, herramienta["ubicacion"]), "con",
          herramienta["responsable"], "el", fecha_para_mostrar(herramienta["fecha_salida"]))
    salida = texto_a_fecha(herramienta["fecha_salida"])
    while True:
        fecha = leer_fecha_hora("Fecha y hora de devolución", momento_actual(None))
        if salida is None or fecha >= salida:
            break
        print("La fecha de devolución no puede ser anterior a la salida ("
              + fecha_para_mostrar(herramienta["fecha_salida"]) + ").")
    print("Estado en que se recibe:  1. Bueno   2. Con daño")
    if leer_opcion("Elija 1 o 2: ", ["1", "2"]) == "1":
        estado_recibido = "bueno"
    else:
        estado_recibido = "con daño"
    observaciones = leer_texto_opcional("Observaciones (ej. ruido raro, golpe; Enter para omitir): ")
    mostrar_resumen([("Herramienta", descripcion_corta(herramienta)),
                     ("Regresa de", nombre_obra(datos, herramienta["ubicacion"])),
                     ("Fecha de devolución", fecha.strftime("%d/%m/%Y %H:%M")),
                     ("Estado recibido", estado_recibido),
                     ("Observaciones", observaciones or "-")])
    if not confirmar("¿Confirmar operación?"):
        print(MENSAJE_CANCELADO)
        return
    exito, mensaje = registrar_devolucion(datos, usuario, herramienta["codigo"], fecha,
                                          estado_recibido, observaciones)
    print("\n" + mensaje)
    if not exito:
        return
    guardar_datos(datos)
    if estado_recibido == "con daño" and confirmar("\n¿Desea reportar el daño ahora?"):
        capturar_dano(datos, usuario, herramienta)


# =====================================================================
# 2.3 Registrar traslado
# =====================================================================

def validar_traslado(datos, usuario, codigo, codigo_destino, responsable):
    """Revisa las reglas de un traslado entre obras. Devuelve la lista de errores."""
    if not tiene_permiso(usuario, "2.3"):
        return [MENSAJE_SIN_PERMISO]
    errores = []
    herramienta = herramienta_o_error(datos, codigo, errores)
    if herramienta is None:
        return errores
    error_herramienta = motivo_bloqueo_traslado(herramienta)
    if error_herramienta != "":
        return [error_herramienta]
    origen = herramienta["ubicacion"]
    error_obra = validar_obra_destino(datos, codigo_destino)
    if error_obra != "":
        errores.append(error_obra)
    elif obtener_obra(datos, codigo_destino)["codigo"] == origen:
        errores.append("La obra de destino debe ser distinta de la obra de origen ("
                       + origen + ").")
    if responsable.strip() == "":
        errores.append("Indique el responsable que recibe la herramienta en la obra de destino.")
    return errores


def motivo_bloqueo_traslado(herramienta):
    """Explica por qué no se puede trasladar. Texto vacío = sí se puede."""
    if herramienta["ubicacion"] == "Bodega":
        return (herramienta["codigo"] + " está en bodega. Para enviarla a una obra use "
                                        "2.1 Registrar salida.")
    if herramienta["estado"] != "asignada":
        return (herramienta["codigo"] + " está '" + herramienta["estado"]
                + "' y no puede trasladarse. Regístrela de vuelta en bodega.")
    return ""


def registrar_traslado(datos, usuario, codigo, codigo_destino, responsable, observaciones="",
                       ahora=None):
    """Registra el traslado directo entre obras. Devuelve (exito, mensaje)."""
    errores = validar_traslado(datos, usuario, codigo, codigo_destino, responsable)
    if len(errores) > 0:
        return False, " ".join(errores)
    herramienta = obtener_herramienta(datos, codigo)
    origen = herramienta["ubicacion"]
    destino = obtener_obra(datos, codigo_destino)["codigo"]
    agregar_movimiento(datos, "traslado", herramienta, origen, destino, responsable.strip(),
                       usuario, momento_actual(ahora),
                       ("Aprobado por " + usuario["nombre"] + ". " + observaciones.strip()).strip(),
                       ahora, herramienta["devolucion_esperada"])
    herramienta["ubicacion"] = destino
    herramienta["responsable"] = responsable.strip()
    olvidar_recepcion(herramienta)
    return True, ("Operación exitosa: traslado registrado. " + herramienta["codigo"]
                  + " pasó de " + origen + " a " + nombre_obra(datos, destino)
                  + ". Responsable: " + responsable.strip()
                  + ". Bodega puede ver la nueva ubicación en SICH.")


def proceso_registrar_traslado(datos, usuario):
    """Opción 2.3 en consola."""
    mostrar_titulo("2.3 REGISTRAR TRASLADO ENTRE OBRAS")
    en_obra = herramientas_en_obra(datos)
    if len(en_obra) == 0:
        print("No hay herramientas en obra para trasladar.")
        return
    mostrar_lista("Herramientas que están en obra:", en_obra)
    herramienta = seleccionar_herramienta(datos)
    if herramienta is None:
        print(MENSAJE_CANCELADO)
        return
    motivo = motivo_bloqueo_traslado(herramienta)
    if motivo != "":
        print("No se puede registrar el traslado: " + motivo)
        return
    origen = herramienta["ubicacion"]
    print("Obra de origen (ubicación actual):", nombre_obra(datos, origen))
    while True:
        destino = pedir_obra_destino(datos)
        if destino != origen:
            break
        print("La obra de destino debe ser distinta de la obra de origen (" + origen + ").")
    responsable = leer_texto_no_vacio("Responsable en la obra de destino: ")
    observaciones = leer_texto_opcional("Observaciones (opcional, Enter para omitir): ")
    mostrar_resumen([("Herramienta", descripcion_corta(herramienta)),
                     ("Obra de origen", nombre_obra(datos, origen)),
                     ("Obra de destino", nombre_obra(datos, destino)),
                     ("Responsable", responsable),
                     ("Aprueba", usuario["nombre"])])
    if not confirmar("¿Confirmar operación?"):
        print(MENSAJE_CANCELADO)
        return
    exito, mensaje = registrar_traslado(datos, usuario, herramienta["codigo"], destino,
                                        responsable, observaciones)
    print("\n" + mensaje)
    if exito:
        guardar_datos(datos)


# =====================================================================
# 2.4 Reportar daño
# =====================================================================

def validar_dano(datos, usuario, codigo, descripcion, fecha, responsable):
    """Revisa las reglas de un reporte de daño. Devuelve la lista de errores."""
    if not tiene_permiso(usuario, "2.4"):
        return [MENSAJE_SIN_PERMISO]
    errores = []
    herramienta = herramienta_o_error(datos, codigo, errores)
    if herramienta is None:
        return errores
    if herramienta["estado"] == "dada de baja":
        errores.append(herramienta["codigo"] + " está dada de baja; no se registran daños.")
    if len(descripcion.strip()) < MINIMO_DESCRIPCION_DANO:
        errores.append("La descripción del daño debe tener al menos "
                       + str(MINIMO_DESCRIPCION_DANO) + " caracteres.")
    if fecha is None:
        errores.append("Fecha inválida. Use el formato DD/MM/AAAA HH:MM.")
    if responsable.strip() == "":
        errores.append("Indique quién reporta o quién tenía la herramienta.")
    return errores


def registrar_dano(datos, usuario, codigo, descripcion, fecha, responsable, ahora=None):
    """Registra el daño: la herramienta queda 'dañada' y bloqueada. Devuelve (exito, mensaje)."""
    errores = validar_dano(datos, usuario, codigo, descripcion, fecha, responsable)
    if len(errores) > 0:
        return False, " ".join(errores)
    herramienta = obtener_herramienta(datos, codigo)
    dano = {
        "id": siguiente_id(datos["danos"]),
        "codigo": herramienta["codigo"],
        "descripcion": descripcion.strip(),
        "fecha": fecha_a_texto(fecha),
        "responsable": responsable.strip(),
        "registrado_por": usuario["usuario"],
        "ubicacion": herramienta["ubicacion"],
    }
    datos["danos"].append(dano)
    agregar_movimiento(datos, "daño", herramienta, herramienta["ubicacion"],
                       herramienta["ubicacion"], responsable.strip(), usuario, fecha,
                       "Daño " + str(dano["id"]) + ": " + descripcion.strip(), ahora)
    herramienta["estado"] = "dañada"
    return True, ("Operación exitosa: daño registrado (reporte " + str(dano["id"]) + "). "
                  + herramienta["codigo"] + " quedó DAÑADA y bloqueada para salir hasta que "
                                            "una revisión la declare apta.")


def capturar_dano(datos, usuario, herramienta):
    """Pide los datos del daño de una herramienta ya elegida, confirma y guarda."""
    descripcion = leer_texto_minimo("Describa el daño (mínimo 5 caracteres): ",
                                    MINIMO_DESCRIPCION_DANO)
    fecha = leer_fecha_hora("Fecha y hora del daño", momento_actual(None))
    responsable = leer_texto_no_vacio("Responsable (quién reporta o tenía la herramienta): ")
    mostrar_resumen([("Herramienta", descripcion_corta(herramienta)),
                     ("Daño", descripcion),
                     ("Fecha", fecha.strftime("%d/%m/%Y %H:%M")),
                     ("Responsable", responsable)])
    if not confirmar("¿Confirmar operación?"):
        print(MENSAJE_CANCELADO)
        return
    exito, mensaje = registrar_dano(datos, usuario, herramienta["codigo"], descripcion, fecha,
                                    responsable)
    print("\n" + mensaje)
    if exito:
        guardar_datos(datos)


def proceso_reportar_dano(datos, usuario):
    """Opción 2.4 en consola."""
    mostrar_titulo("2.4 REPORTAR DAÑO")
    herramienta = seleccionar_herramienta(datos)
    if herramienta is None:
        print(MENSAJE_CANCELADO)
        return
    if herramienta["estado"] == "dada de baja":
        print(herramienta["codigo"], "está dada de baja; no se registran daños.")
        return
    capturar_dano(datos, usuario, herramienta)


# =====================================================================
# 2.5 Registrar revisión
# =====================================================================

def validar_revision(datos, usuario, codigo, resultado, revisor):
    """Revisa las reglas de una revisión técnica. Devuelve la lista de errores."""
    if not tiene_permiso(usuario, "2.5"):
        return [MENSAJE_SIN_PERMISO]
    errores = []
    herramienta = herramienta_o_error(datos, codigo, errores)
    if herramienta is None:
        return errores
    error_herramienta = motivo_bloqueo_revision(herramienta)
    if error_herramienta != "":
        return [error_herramienta]
    if resultado not in ["apta", "no apta"]:
        errores.append("El resultado debe ser 'apta' o 'no apta'.")
    if revisor.strip() == "":
        errores.append("Indique el nombre de quien revisó el equipo.")
    return errores


def motivo_bloqueo_revision(herramienta):
    """Explica por qué no se puede revisar. Texto vacío = sí se puede."""
    if herramienta["estado"] not in ESTADOS_QUE_SE_REVISAN:
        return (herramienta["codigo"] + " está '" + herramienta["estado"]
                + "': no tiene daños ni revisión pendiente.")
    if herramienta["ubicacion"] != "Bodega":
        return (herramienta["codigo"] + " está en la obra " + herramienta["ubicacion"]
                + ": registre primero la devolución para revisarla en bodega.")
    return ""


def registrar_revision(datos, usuario, codigo, resultado, revisor, observaciones="",
                       ahora=None):
    """Registra la revisión: apta -> disponible, no apta -> en reparación."""
    errores = validar_revision(datos, usuario, codigo, resultado, revisor)
    if len(errores) > 0:
        return False, " ".join(errores)
    herramienta = obtener_herramienta(datos, codigo)
    if resultado == "apta":
        nuevo_estado = "disponible"
    else:
        nuevo_estado = "en reparación"
    notas = ("Resultado: " + resultado + ". Estado anterior: " + herramienta["estado"]
             + ". " + observaciones.strip()).strip()
    agregar_movimiento(datos, "revision", herramienta, "Bodega", "Bodega", revisor.strip(),
                       usuario, momento_actual(ahora), notas, ahora)
    herramienta["estado"] = nuevo_estado
    if nuevo_estado == "disponible":
        return True, ("Operación exitosa: revisión registrada. " + herramienta["codigo"]
                      + " es APTA y queda DISPONIBLE para salir.")
    return True, ("Operación exitosa: revisión registrada. " + herramienta["codigo"]
                  + " NO es apta y queda EN REPARACIÓN (no puede salir).")


def proceso_registrar_revision(datos, usuario):
    """Opción 2.5 en consola."""
    mostrar_titulo("2.5 REGISTRAR REVISIÓN")
    por_revisar = herramientas_por_revisar(datos)
    if len(por_revisar) == 0:
        print("No hay herramientas que requieran revisión.")
        return
    mostrar_lista("Herramientas dañadas, en reparación o que requieren revisión:", por_revisar)
    herramienta = seleccionar_herramienta(datos)
    if herramienta is None:
        print(MENSAJE_CANCELADO)
        return
    motivo = motivo_bloqueo_revision(herramienta)
    if motivo != "":
        print("No se puede registrar la revisión: " + motivo)
        return
    if herramienta["motor_o_cable"]:
        print("Equipo con motor o cable: revise golpes, ruido extraño y cable expuesto "
              "(memorando 14/02/2026).")
    print("Resultado de la revisión:  1. Apta   2. No apta")
    if leer_opcion("Elija 1 o 2: ", ["1", "2"]) == "1":
        resultado = "apta"
    else:
        resultado = "no apta"
    revisor = leer_texto_no_vacio("Nombre de quien revisó: ")
    observaciones = leer_texto_opcional("Observaciones (opcional, Enter para omitir): ")
    mostrar_resumen([("Herramienta", descripcion_corta(herramienta)),
                     ("Resultado", resultado),
                     ("Revisor", revisor)])
    if not confirmar("¿Confirmar operación?"):
        print(MENSAJE_CANCELADO)
        return
    exito, mensaje = registrar_revision(datos, usuario, herramienta["codigo"], resultado,
                                        revisor, observaciones)
    print("\n" + mensaje)
    if exito:
        guardar_datos(datos)


# =====================================================================
# 2.6 Autorizar permanencia en obra
# =====================================================================

def autorizacion_que_se_cruza(datos, codigo, codigo_obra, inicio, fin):
    """Devuelve una autorización existente que se cruza con el período, o None."""
    for autorizacion in datos["autorizaciones"]:
        if autorizacion["codigo"] == codigo and autorizacion["obra"] == codigo_obra:
            otro_inicio = texto_a_fecha(autorizacion["fecha_inicio"])
            otro_fin = texto_a_fecha(autorizacion["fecha_fin"])
            if inicio <= otro_fin and fin >= otro_inicio:
                return autorizacion
    return None


def validar_permanencia(datos, usuario, codigo, codigo_obra, fecha_inicio, fecha_fin,
                        seguridad_confirmada):
    """Revisa las reglas de una autorización de permanencia. Devuelve la lista de errores."""
    if not tiene_permiso(usuario, "2.6"):
        return [MENSAJE_SIN_PERMISO]
    errores = []
    herramienta = herramienta_o_error(datos, codigo, errores)
    if herramienta is None:
        return errores
    if herramienta["estado"] != "asignada" or herramienta["ubicacion"] == "Bodega":
        return [herramienta["codigo"] + " no está asignada a ninguna obra; solo se autoriza "
                                        "la permanencia de herramientas que están en obra."]
    if herramienta["ubicacion"] != codigo_obra:
        return [herramienta["codigo"] + " no está asignada a la obra " + codigo_obra
                + " (está en " + herramienta["ubicacion"] + ")."]
    if fecha_inicio is None or fecha_fin is None:
        errores.append("Fecha inválida. Use el formato DD/MM/AAAA HH:MM.")
    elif fecha_fin <= fecha_inicio:
        errores.append("La fecha de fin debe ser posterior a la fecha de inicio.")
    else:
        repetida = autorizacion_que_se_cruza(datos, herramienta["codigo"], codigo_obra,
                                             fecha_inicio, fecha_fin)
        if repetida is not None:
            errores.append("Ya existe la autorización " + str(repetida["id"]) + " para "
                           + herramienta["codigo"] + " en " + codigo_obra + " hasta "
                           + fecha_para_mostrar(repetida["fecha_fin"]) + ".")
    if not seguridad_confirmada:
        errores.append("Autorización rechazada: el sitio debe tener seguridad para que la "
                       "herramienta se quede (memorando 14/02/2026).")
    return errores


def registrar_permanencia(datos, usuario, codigo, codigo_obra, fecha_inicio, fecha_fin,
                          seguridad_confirmada, observaciones="", ahora=None):
    """Registra por escrito la autorización de permanencia. Devuelve (exito, mensaje)."""
    errores = validar_permanencia(datos, usuario, codigo, codigo_obra, fecha_inicio, fecha_fin,
                                  seguridad_confirmada)
    if len(errores) > 0:
        return False, " ".join(errores)
    herramienta = obtener_herramienta(datos, codigo)
    autorizacion = {
        "id": siguiente_id(datos["autorizaciones"]),
        "codigo": herramienta["codigo"],
        "obra": codigo_obra,
        "fecha_inicio": fecha_a_texto(fecha_inicio),
        "fecha_fin": fecha_a_texto(fecha_fin),
        "residente": usuario["nombre"],
        "seguridad_confirmada": True,
        "registrado_por": usuario["usuario"],
        "fecha_registro": fecha_a_texto(momento_actual(ahora)),
        "observaciones": observaciones.strip(),
    }
    datos["autorizaciones"].append(autorizacion)
    periodo = (fecha_inicio.strftime("%d/%m/%Y %H:%M") + " al "
               + fecha_fin.strftime("%d/%m/%Y %H:%M"))
    agregar_movimiento(datos, "permanencia", herramienta, codigo_obra, codigo_obra,
                       usuario["nombre"], usuario, fecha_inicio,
                       ("Autorización " + str(autorizacion["id"]) + ": del " + periodo + ". "
                        + observaciones.strip()).strip(), ahora)
    return True, ("Operación exitosa: autorización " + str(autorizacion["id"])
                  + " registrada por escrito en SICH. " + herramienta["codigo"]
                  + " puede quedarse en " + codigo_obra + " del " + periodo
                  + ". Mientras esté vigente no se marcará como pendiente vencida.")


def proceso_autorizar_permanencia(datos, usuario):
    """Opción 2.6 en consola."""
    mostrar_titulo("2.6 AUTORIZAR PERMANENCIA EN OBRA")
    en_obra = herramientas_en_obra(datos)
    if len(en_obra) == 0:
        print("No hay herramientas asignadas en obras.")
        return
    mostrar_lista("Herramientas que están en obra:", en_obra)
    herramienta = seleccionar_herramienta(datos)
    if herramienta is None:
        print(MENSAJE_CANCELADO)
        return
    if herramienta["estado"] != "asignada" or herramienta["ubicacion"] == "Bodega":
        print("No se puede autorizar: " + herramienta["codigo"] + " no está asignada a "
              "ninguna obra.")
        return
    codigo_obra = herramienta["ubicacion"]
    print("Obra donde se quedará:", nombre_obra(datos, codigo_obra))
    inicio = leer_fecha_hora("Inicio de la permanencia", momento_actual(None))
    while True:
        fin_sugerido = (inicio + timedelta(days=1)).replace(hour=6, minute=15)
        fin = leer_fecha_hora("Fin de la permanencia", fin_sugerido)
        if fin > inicio:
            break
        print("La fecha de fin debe ser posterior a la fecha de inicio.")
    if not confirmar("¿Confirma que el sitio tiene seguridad (garita, guardián o bodega con llave)?"):
        print("Autorización rechazada: el sitio debe tener seguridad para que la herramienta "
              "se quede (memorando 14/02/2026). No se guardó ningún cambio.")
        return
    observaciones = leer_texto_opcional("Observaciones (opcional, Enter para omitir): ")
    mostrar_resumen([("Herramienta", descripcion_corta(herramienta)),
                     ("Obra", nombre_obra(datos, codigo_obra)),
                     ("Período", inicio.strftime("%d/%m/%Y %H:%M") + " al "
                      + fin.strftime("%d/%m/%Y %H:%M")),
                     ("Residente que autoriza", usuario["nombre"]),
                     ("Seguridad confirmada", "Sí")])
    if not confirmar("¿Confirmar operación?"):
        print(MENSAJE_CANCELADO)
        return
    exito, mensaje = registrar_permanencia(datos, usuario, herramienta["codigo"], codigo_obra,
                                           inicio, fin, True, observaciones)
    print("\n" + mensaje)
    if exito:
        guardar_datos(datos)


# =====================================================================
# 2.7 Confirmar recepción en obra
# =====================================================================

def herramientas_por_recibir(datos, usuario):
    """Herramientas asignadas sin confirmar. El maestro solo ve las de su obra."""
    lista = []
    for herramienta in herramientas_en_obra(datos):
        if herramienta["estado"] == "asignada" and not herramienta.get("recepcion_confirmada_por"):
            if usuario["rol"] != "maestro" or herramienta["ubicacion"] == usuario.get("obra"):
                lista.append(herramienta)
    return lista


def motivo_bloqueo_recepcion(usuario, herramienta):
    """Explica por qué no se puede confirmar. Texto vacío = sí se puede."""
    codigo = herramienta["codigo"]
    if herramienta["estado"] != "asignada" or herramienta["ubicacion"] == "Bodega":
        return codigo + " no está asignada a ninguna obra: no hay nada que recibir."
    if usuario["rol"] == "maestro" and herramienta["ubicacion"] != usuario.get("obra"):
        return (codigo + " está en la obra " + herramienta["ubicacion"]
                + ". Usted solo puede confirmar las de su obra ("
                + (usuario.get("obra") or "sin obra asignada") + ").")
    if herramienta.get("recepcion_confirmada_por"):
        return (codigo + " ya fue recibida por " + herramienta["recepcion_confirmada_por"]
                + " el " + fecha_para_mostrar(herramienta["recepcion_fecha"]) + ".")
    return ""


def validar_recepcion(datos, usuario, codigo, fecha):
    """Revisa las reglas de la confirmación de recepción. Devuelve la lista de errores."""
    if not tiene_permiso(usuario, "2.7"):
        return [MENSAJE_SIN_PERMISO]
    errores = []
    herramienta = herramienta_o_error(datos, codigo, errores)
    if herramienta is None:
        return errores
    motivo = motivo_bloqueo_recepcion(usuario, herramienta)
    if motivo != "":
        return [motivo]
    if fecha is None:
        errores.append("Fecha inválida. Use el formato DD/MM/AAAA HH:MM.")
    elif herramienta["fecha_salida"] != "" and fecha < texto_a_fecha(herramienta["fecha_salida"]):
        errores.append("La recepción no puede ser anterior a la salida ("
                       + fecha_para_mostrar(herramienta["fecha_salida"]) + ").")
    return errores


def registrar_recepcion(datos, usuario, codigo, fecha, observaciones="", ahora=None):
    """Deja constancia de quién recibió la herramienta en obra. Devuelve (exito, mensaje)."""
    errores = validar_recepcion(datos, usuario, codigo, fecha)
    if len(errores) > 0:
        return False, " ".join(errores)
    herramienta = obtener_herramienta(datos, codigo)
    herramienta["recepcion_confirmada_por"] = usuario["nombre"]
    herramienta["recepcion_fecha"] = fecha_a_texto(fecha)
    agregar_movimiento(datos, "recepcion", herramienta, herramienta["ubicacion"],
                       herramienta["ubicacion"], usuario["nombre"], usuario, fecha,
                       observaciones.strip(), ahora)
    return True, ("Operación exitosa: recepción confirmada. " + herramienta["codigo"] + " fue "
                  "recibida en " + herramienta["ubicacion"] + " por " + usuario["nombre"] + ".")


def proceso_confirmar_recepcion(datos, usuario):
    """Opción 2.7 en consola."""
    mostrar_titulo("2.7 CONFIRMAR RECEPCIÓN EN OBRA")
    por_recibir = herramientas_por_recibir(datos, usuario)
    if len(por_recibir) == 0:
        print("No hay herramientas pendientes de confirmar.")
        return
    mostrar_lista("Herramientas por confirmar:", por_recibir)
    herramienta = seleccionar_herramienta(datos)
    if herramienta is None:
        print(MENSAJE_CANCELADO)
        return
    motivo = motivo_bloqueo_recepcion(usuario, herramienta)
    if motivo != "":
        print("No se puede confirmar: " + motivo)
        return
    salida = texto_a_fecha(herramienta["fecha_salida"])
    while True:
        fecha = leer_fecha_hora("Fecha y hora de recepción", momento_actual(None))
        if salida is None or fecha >= salida:
            break
        print("La recepción no puede ser anterior a la salida ("
              + fecha_para_mostrar(herramienta["fecha_salida"]) + ").")
    observaciones = leer_texto_opcional("Observaciones (opcional, Enter para omitir): ")
    mostrar_resumen([("Herramienta", descripcion_corta(herramienta)),
                     ("Obra", nombre_obra(datos, herramienta["ubicacion"])),
                     ("Fecha de recepción", fecha.strftime("%d/%m/%Y %H:%M")),
                     ("Recibe", usuario["nombre"])])
    if not confirmar("¿Confirmar operación?"):
        print(MENSAJE_CANCELADO)
        return
    exito, mensaje = registrar_recepcion(datos, usuario, herramienta["codigo"], fecha, observaciones)
    print("\n" + mensaje)
    if exito:
        guardar_datos(datos)


# =====================================================================
# 2.8 Registrar mantenimiento
# =====================================================================

def herramientas_para_mantenimiento(datos):
    """Herramientas en Bodega con plan de mantenimiento; primero las más cercanas a vencer."""
    lista = []
    for herramienta in datos["herramientas"]:
        if motivo_bloqueo_mantenimiento(herramienta) == "":
            lista.append(herramienta)
    return sorted(lista, key=lambda h: h.get("horas_uso", 0) / intervalo_mantenimiento(h),
                  reverse=True)


def motivo_bloqueo_mantenimiento(herramienta):
    """Explica por qué no se puede registrar. Texto vacío = sí se puede."""
    codigo = herramienta["codigo"]
    if intervalo_mantenimiento(herramienta) == 0:
        return (codigo + " no tiene horas de mantenimiento configuradas. Agréguelas en "
                         "1.3 Modificar herramienta según su ficha técnica.")
    if herramienta["estado"] == "dada de baja":
        return codigo + " está dada de baja."
    if herramienta["ubicacion"] != "Bodega":
        return (codigo + " está en la obra " + herramienta["ubicacion"]
                + ": registre primero la devolución.")
    return ""


def validar_mantenimiento(datos, usuario, codigo, fecha, realizado_por):
    """Revisa las reglas del mantenimiento. Devuelve la lista de errores."""
    if not tiene_permiso(usuario, "2.8"):
        return [MENSAJE_SIN_PERMISO]
    errores = []
    herramienta = herramienta_o_error(datos, codigo, errores)
    if herramienta is None:
        return errores
    motivo = motivo_bloqueo_mantenimiento(herramienta)
    if motivo != "":
        return [motivo]
    if fecha is None:
        errores.append("Fecha inválida. Use el formato DD/MM/AAAA HH:MM.")
    if realizado_por.strip() == "":
        errores.append("Indique quién hizo el mantenimiento.")
    return errores


def registrar_mantenimiento(datos, usuario, codigo, fecha, realizado_por, observaciones="",
                            ahora=None):
    """Registra el mantenimiento y pone el contador en 0. Devuelve (exito, mensaje)."""
    errores = validar_mantenimiento(datos, usuario, codigo, fecha, realizado_por)
    if len(errores) > 0:
        return False, " ".join(errores)
    herramienta = obtener_herramienta(datos, codigo)
    uso_anterior = texto_de_uso(herramienta)
    agregar_movimiento(datos, "mantenimiento", herramienta, "Bodega", "Bodega", realizado_por.strip(),
                       usuario, fecha, ("Tenía " + uso_anterior + ". " + observaciones.strip()).strip(),
                       ahora)
    herramienta["horas_uso"] = 0
    herramienta["ultimo_mantenimiento"] = fecha_a_texto(fecha)
    return True, ("Operación exitosa: mantenimiento registrado. " + herramienta["codigo"]
                  + " tenía " + uso_anterior + " y ahora tiene " + texto_de_uso(herramienta) + ".")


def proceso_registrar_mantenimiento(datos, usuario):
    """Opción 2.8 en consola."""
    mostrar_titulo("2.8 REGISTRAR MANTENIMIENTO")
    candidatas = herramientas_para_mantenimiento(datos)
    if len(candidatas) == 0:
        print("No hay herramientas en bodega con horas de mantenimiento configuradas.")
        return
    print("Herramientas con plan de mantenimiento:")
    for herramienta in candidatas:
        print("  -", herramienta["codigo"], "-", herramienta["nombre"], "|", texto_de_uso(herramienta))
    herramienta = seleccionar_herramienta(datos)
    if herramienta is None:
        print(MENSAJE_CANCELADO)
        return
    motivo = motivo_bloqueo_mantenimiento(herramienta)
    if motivo != "":
        print("No se puede registrar: " + motivo)
        return
    fecha = leer_fecha_hora("Fecha y hora del mantenimiento", momento_actual(None))
    realizado_por = leer_texto_no_vacio("Quién hizo el mantenimiento: ")
    observaciones = leer_texto_opcional("Observaciones (opcional, Enter para omitir): ")
    mostrar_resumen([("Herramienta", descripcion_corta(herramienta)),
                     ("Horas actuales", texto_de_uso(herramienta) + " (vuelven a 0)"),
                     ("Fecha", fecha.strftime("%d/%m/%Y %H:%M")),
                     ("Realizado por", realizado_por)])
    if not confirmar("¿Confirmar operación?"):
        print(MENSAJE_CANCELADO)
        return
    exito, mensaje = registrar_mantenimiento(datos, usuario, herramienta["codigo"], fecha,
                                             realizado_por, observaciones)
    print("\n" + mensaje)
    if exito:
        guardar_datos(datos)
