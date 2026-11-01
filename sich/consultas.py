"""Módulo 3 - Consultas y seguimiento: buscar, disponibles, pendientes, por obra e historial.

Las funciones consultar_xxx solo leen los datos y devuelven listas; las usan la
consola (proceso_xxx) y la página web.
"""

from sich.busqueda import buscar_con_detalle, normalizar, seleccionar_herramienta
from sich.catalogo import nombre_obra, obras_activas, obtener_herramienta, obtener_obra
from sich.movimientos import autorizacion_vigente, esta_vencida, horas_de_uso, \
    intervalo_mantenimiento, mantenimiento_vencido, momento_actual, texto_de_uso
from sich.validaciones import confirmar, fecha_para_mostrar, leer_fecha_hora, leer_opcion, \
    leer_texto_no_vacio, leer_texto_opcional, mostrar_titulo, texto_a_fecha

NOMBRES_MOVIMIENTO = {
    "registro": "Registro en catálogo",
    "apodos": "Apodos asociados",
    "modificacion": "Modificación",
    "salida": "Salida",
    "recepcion": "Recepción en obra",
    "devolucion": "Devolución",
    "traslado": "Traslado",
    "daño": "Daño reportado",
    "revision": "Revisión",
    "mantenimiento": "Mantenimiento",
    "ficha": "Ficha técnica",
    "permanencia": "Permanencia autorizada",
}


def detalle_herramienta(datos, herramienta, ahora=None):
    """Devuelve una lista de (etiqueta, valor) con la información de una herramienta."""
    momento = momento_actual(ahora)
    lineas = [
        ("Código oficial", herramienta["codigo"]),
        ("Nombre", herramienta["nombre"]),
        ("También le dicen", ", ".join(herramienta["apodos"]) or "-"),
        ("Estado", herramienta["estado"]),
        ("Ubicación", nombre_obra(datos, herramienta["ubicacion"])),
        ("Responsable", herramienta["responsable"] or "-"),
        ("Devolución esperada", fecha_para_mostrar(herramienta["devolucion_esperada"])),
    ]
    if herramienta.get("recepcion_confirmada_por"):
        lineas.append(("Recibida en obra", herramienta["recepcion_confirmada_por"] + " el "
                       + fecha_para_mostrar(herramienta["recepcion_fecha"])))
    if esta_vencida(datos, herramienta, momento):
        lineas.append(("Aviso", "DEVOLUCIÓN VENCIDA"))
    vigente = autorizacion_vigente(datos, herramienta["codigo"], herramienta["ubicacion"], momento)
    if vigente is not None:
        lineas.append(("Permanencia autorizada", "hasta " + fecha_para_mostrar(vigente["fecha_fin"])
                       + " por " + vigente["residente"]))
    if intervalo_mantenimiento(herramienta) > 0:
        lineas.append(("Horas de uso", texto_de_uso(herramienta, momento)))
        if mantenimiento_vencido(herramienta, momento):
            lineas.append(("Alarma", "MANTENIMIENTO VENCIDO: no se puede entregar"))
    if herramienta.get("ultimo_mantenimiento"):
        lineas.append(("Último mantenimiento", fecha_para_mostrar(herramienta["ultimo_mantenimiento"])))
    if herramienta.get("ficha_tecnica"):
        lineas.append(("Ficha técnica", herramienta["ficha_tecnica"]))
    if herramienta["observaciones"] != "":
        lineas.append(("Observaciones", herramienta["observaciones"]))
    return lineas


def resumen_tablero(datos, ahora=None):
    """Cuenta herramientas para las 4 tarjetas del tablero web."""
    resumen = {"disponibles": 0, "asignadas": 0, "vencidas": 0, "danadas": 0, "mantenimiento": 0}
    for herramienta in datos["herramientas"]:
        por_mantener = mantenimiento_vencido(herramienta, ahora)
        if por_mantener and herramienta["estado"] != "dada de baja":
            resumen["mantenimiento"] = resumen["mantenimiento"] + 1
        if herramienta["estado"] == "disponible" and not por_mantener:
            resumen["disponibles"] = resumen["disponibles"] + 1
        if herramienta["estado"] == "asignada":
            resumen["asignadas"] = resumen["asignadas"] + 1
        if herramienta["estado"] in ["dañada", "requiere revisión", "en reparación"]:
            resumen["danadas"] = resumen["danadas"] + 1
        if esta_vencida(datos, herramienta, ahora):
            resumen["vencidas"] = resumen["vencidas"] + 1
    return resumen


# =====================================================================
# 3.1 Buscar herramienta
# =====================================================================

def proceso_buscar_herramienta(datos, usuario):
    """Opción 3.1 en consola: busca por código, nombre o apodo y muestra el detalle."""
    mostrar_titulo("3.1 BUSCAR HERRAMIENTA")
    while True:
        texto = leer_texto_no_vacio("Escriba código, nombre o apodo (ej. bailarina): ")
        encontradas, aproximada = buscar_con_detalle(datos, texto)
        if len(encontradas) == 0:
            print("No se encontró ninguna herramienta con '" + texto + "'.")
        else:
            if aproximada:
                print("No hubo coincidencia exacta con '" + texto + "'; se muestran las parecidas.")
            print("\nResultados:", len(encontradas))
            for herramienta in encontradas:
                print()
                for etiqueta, valor in detalle_herramienta(datos, herramienta):
                    print("  " + etiqueta + ": " + valor)
        if not confirmar("\n¿Desea buscar otra herramienta?"):
            return


# =====================================================================
# 3.2 Consultar disponibles
# =====================================================================

def categorias(datos):
    """Lista ordenada de las categorías del catálogo."""
    lista = []
    for herramienta in datos["herramientas"]:
        if herramienta["categoria"] not in lista:
            lista.append(herramienta["categoria"])
    return sorted(lista)


def consultar_disponibles(datos, criterio=""):
    """Herramientas disponibles en Bodega, ordenadas por categoría y código.

    El criterio es opcional: una categoría, código, nombre o apodo.
    """
    if criterio.strip() == "":
        candidatas = datos["herramientas"]
    else:
        candidatas, aproximada = buscar_con_detalle(datos, criterio)
    lista = []
    for herramienta in candidatas:
        if herramienta["estado"] == "disponible" and herramienta["ubicacion"] == "Bodega" \
                and not mantenimiento_vencido(herramienta):
            lista.append(herramienta)
    return sorted(lista, key=lambda h: (normalizar(h["categoria"]), h["codigo"]))


def proceso_consultar_disponibles(datos, usuario):
    """Opción 3.2 en consola."""
    mostrar_titulo("3.2 CONSULTAR DISPONIBLES")
    print("Categorías:", ", ".join(categorias(datos)))
    criterio = leer_texto_opcional("Categoría, nombre o apodo (Enter = todas): ")
    disponibles = consultar_disponibles(datos, criterio)
    if len(disponibles) == 0:
        print("No hay herramientas disponibles con ese criterio.")
        return
    print("\nDisponibles en bodega:", len(disponibles))
    for herramienta in disponibles:
        print(" ", herramienta["categoria"].ljust(14), herramienta["codigo"].ljust(11),
              herramienta["nombre"], "-", herramienta["marca"])


# =====================================================================
# 3.3 Consultar devoluciones pendientes
# =====================================================================

def atraso_en_texto(esperada, momento):
    """Convierte el tiempo vencido en un texto como '2 d 3 h'."""
    segundos = int((momento - esperada).total_seconds())
    dias = segundos // 86400
    horas = (segundos % 86400) // 3600
    if dias > 0:
        return str(dias) + " d " + str(horas) + " h"
    return str(horas) + " h " + str((segundos % 3600) // 60) + " min"


def consultar_pendientes(datos, solo_vencidas=False, hasta=None, ahora=None):
    """Herramientas en obra por devolver, de la fecha esperada más antigua a la más nueva.

    Cada elemento trae: herramienta, esperada, vencida, atraso y autorizacion.
    Con 'hasta' (datetime) solo incluye las que se esperan hasta esa fecha.
    """
    momento = momento_actual(ahora)
    lista = []
    for herramienta in datos["herramientas"]:
        if herramienta["ubicacion"] == "Bodega" or herramienta["devolucion_esperada"] == "":
            continue
        esperada = texto_a_fecha(herramienta["devolucion_esperada"])
        vencida = esta_vencida(datos, herramienta, momento)
        if (solo_vencidas and not vencida) or (hasta is not None and esperada > hasta):
            continue
        lista.append({
            "herramienta": herramienta,
            "esperada": esperada,
            "vencida": vencida,
            "atraso": atraso_en_texto(esperada, momento) if vencida else "",
            "autorizacion": autorizacion_vigente(datos, herramienta["codigo"],
                                                 herramienta["ubicacion"], momento),
        })
    return sorted(lista, key=lambda p: p["esperada"])


def proceso_consultar_pendientes(datos, usuario):
    """Opción 3.3 en consola."""
    mostrar_titulo("3.3 DEVOLUCIONES PENDIENTES")
    print("Ver:  1. Todas   2. Solo vencidas   3. Hasta una fecha")
    eleccion = leer_opcion("Elija una opción: ", ["1", "2", "3"])
    hasta = None
    if eleccion == "3":
        hasta = leer_fecha_hora("Hasta qué fecha y hora", momento_actual(None))
    pendientes = consultar_pendientes(datos, eleccion == "2", hasta)
    if len(pendientes) == 0:
        print("No hay devoluciones pendientes con ese criterio.")
        return
    print("\nPendientes:", len(pendientes))
    for pendiente in pendientes:
        herramienta = pendiente["herramienta"]
        marca = ""
        if pendiente["vencida"]:
            marca = "  ** VENCIDA hace " + pendiente["atraso"] + " **"
        elif pendiente["autorizacion"] is not None:
            marca = "  (permanencia autorizada hasta "
            marca = marca + fecha_para_mostrar(pendiente["autorizacion"]["fecha_fin"]) + ")"
        print(" ", pendiente["esperada"].strftime("%d/%m/%Y %H:%M"), herramienta["codigo"].ljust(11),
              herramienta["ubicacion"].ljust(8), herramienta["responsable"] + marca)


# =====================================================================
# 3.4 Consultar herramientas por obra
# =====================================================================

def error_en_consulta_por_obra(datos, usuario, codigo_obra):
    """Revisa la obra pedida. El maestro solo consulta la suya. Devuelve el error o ''."""
    obra = obtener_obra(datos, codigo_obra)
    if obra is None:
        return "La obra '" + codigo_obra + "' no existe. Elija una obra de la lista."
    if usuario["rol"] == "maestro" and obra["codigo"] != usuario.get("obra"):
        return ("Usted solo puede consultar su obra ("
                + (usuario.get("obra") or "sin obra asignada") + ").")
    return ""


def consultar_por_obra(datos, codigo_obra, ahora=None):
    """Herramientas que están en esa obra (o en Bodega), ordenadas por código."""
    obra = obtener_obra(datos, codigo_obra)
    lista = []
    for herramienta in datos["herramientas"]:
        if obra is not None and herramienta["ubicacion"] == obra["codigo"]:
            lista.append({"herramienta": herramienta,
                          "vencida": esta_vencida(datos, herramienta, ahora)})
    return sorted(lista, key=lambda p: p["herramienta"]["codigo"])


def proceso_consultar_por_obra(datos, usuario):
    """Opción 3.4 en consola."""
    mostrar_titulo("3.4 HERRAMIENTAS POR OBRA")
    if usuario["rol"] == "maestro":
        codigo_obra = usuario.get("obra", "")
        print("Su obra:", nombre_obra(datos, codigo_obra))
    else:
        print("Obras activas:")
        for obra in obras_activas(datos):
            print("  -", obra["codigo"], "-", obra["nombre"])
        print("  - Bodega")
        codigo_obra = leer_texto_no_vacio("Código de la obra (ej. VN-014): ")
    error = error_en_consulta_por_obra(datos, usuario, codigo_obra)
    if error != "":
        print(error)
        return
    resultado = consultar_por_obra(datos, codigo_obra)
    if len(resultado) == 0:
        print("No hay herramientas en " + nombre_obra(datos, codigo_obra) + ".")
        return
    print("\nHerramientas en", nombre_obra(datos, codigo_obra) + ":", len(resultado))
    for elemento in resultado:
        herramienta = elemento["herramienta"]
        marca = "  ** VENCIDA **" if elemento["vencida"] else ""
        print(" ", herramienta["codigo"].ljust(11), herramienta["nombre"], "|", herramienta["estado"],
              "|", (herramienta["responsable"] or "-") + marca)


# =====================================================================
# 3.5 Consultar historial
# =====================================================================

def consultar_historial(datos, codigo):
    """Movimientos, daños y autorizaciones de una herramienta, en orden cronológico.

    Devuelve un diccionario, o None si la herramienta no existe.
    """
    herramienta = obtener_herramienta(datos, codigo)
    if herramienta is None:
        return None
    movimientos = []
    for movimiento in datos["movimientos"]:
        if movimiento["codigo"] == herramienta["codigo"]:
            movimientos.append(movimiento)
    danos = []
    for dano in datos["danos"]:
        if dano["codigo"] == herramienta["codigo"]:
            danos.append(dano)
    autorizaciones = []
    for autorizacion in datos["autorizaciones"]:
        if autorizacion["codigo"] == herramienta["codigo"]:
            autorizaciones.append(autorizacion)
    return {
        "herramienta": herramienta,
        "movimientos": sorted(movimientos, key=lambda m: (m["fecha_hora"], m["id"])),
        "danos": sorted(danos, key=lambda d: d["fecha"]),
        "autorizaciones": sorted(autorizaciones, key=lambda a: a["fecha_inicio"]),
    }


def proceso_consultar_historial(datos, usuario):
    """Opción 3.5 en consola."""
    mostrar_titulo("3.5 HISTORIAL DE UNA HERRAMIENTA")
    herramienta = seleccionar_herramienta(datos)
    if herramienta is None:
        print("Consulta cancelada.")
        return
    historial = consultar_historial(datos, herramienta["codigo"])
    print("\nHistorial de", herramienta["codigo"], "-", herramienta["nombre"])
    print("\nMovimientos:", len(historial["movimientos"]))
    for movimiento in historial["movimientos"]:
        print(" ", fecha_para_mostrar(movimiento["fecha_hora"]),
              NOMBRES_MOVIMIENTO.get(movimiento["tipo"], movimiento["tipo"]) + ":",
              movimiento["obra_origen"], "->", movimiento["obra_destino"], "|",
              movimiento["responsable"], "| registró", movimiento["registrado_por"], "el",
              fecha_para_mostrar(movimiento["fecha_registro"]))
        if movimiento["observaciones"] != "":
            print("      " + movimiento["observaciones"])
    print("\nDaños:", len(historial["danos"]))
    for dano in historial["danos"]:
        print(" ", fecha_para_mostrar(dano["fecha"]), dano["descripcion"], "|", dano["responsable"])
    print("\nAutorizaciones de permanencia:", len(historial["autorizaciones"]))
    for autorizacion in historial["autorizaciones"]:
        print(" ", autorizacion["obra"], "del", fecha_para_mostrar(autorizacion["fecha_inicio"]),
              "al", fecha_para_mostrar(autorizacion["fecha_fin"]), "|", autorizacion["residente"])


# =====================================================================
# 3.6 Estado de mantenimiento
# =====================================================================

PORCENTAJE_PROXIMO = 90   # desde aquí se avisa que el mantenimiento está cerca


def consultar_mantenimiento(datos, ahora=None):
    """Herramientas con plan de mantenimiento, de la más cercana a vencer a la más lejana."""
    momento = momento_actual(ahora)
    lista = []
    for herramienta in datos["herramientas"]:
        intervalo = intervalo_mantenimiento(herramienta)
        if intervalo == 0 or herramienta["estado"] == "dada de baja":
            continue
        horas = horas_de_uso(herramienta, momento)
        porcentaje = int(horas * 100 / intervalo)
        situacion = "al día"
        if horas >= intervalo:
            situacion = "vencido"
        elif porcentaje >= PORCENTAJE_PROXIMO:
            situacion = "próximo"
        lista.append({"herramienta": herramienta, "uso": texto_de_uso(herramienta, momento),
                      "porcentaje": porcentaje, "situacion": situacion})
    return sorted(lista, key=lambda m: m["porcentaje"], reverse=True)


def proceso_consultar_mantenimiento(datos, usuario):
    """Opción 3.6 en consola."""
    mostrar_titulo("3.6 ESTADO DE MANTENIMIENTO")
    lista = consultar_mantenimiento(datos)
    if len(lista) == 0:
        print("No hay herramientas con horas de mantenimiento configuradas.")
        return
    for elemento in lista:
        marca = ""
        if elemento["situacion"] == "vencido":
            marca = "  ** VENCIDO: NO SE PUEDE ENTREGAR **"
        elif elemento["situacion"] == "próximo":
            marca = "  (próximo)"
        print(" ", elemento["herramienta"]["codigo"].ljust(11), elemento["uso"].ljust(16),
              str(elemento["porcentaje"]) + "%" + marca)
