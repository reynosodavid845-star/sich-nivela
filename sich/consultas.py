"""Módulo 3 - Consultas y seguimiento.

Implementado: 3.1 Buscar herramienta (lo necesita el Módulo 2 para elegir
herramientas por apodo). Pendientes para la Fase 4: 3.2 Disponibles,
3.3 Devoluciones pendientes, 3.4 Por obra y 3.5 Historial.
"""

from sich.busqueda import buscar_con_detalle
from sich.catalogo import nombre_obra
from sich.movimientos import autorizacion_vigente, esta_vencida, momento_actual
from sich.validaciones import confirmar, fecha_para_mostrar, leer_texto_no_vacio, mostrar_titulo


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
    if esta_vencida(datos, herramienta, momento):
        lineas.append(("Aviso", "DEVOLUCIÓN VENCIDA"))
    vigente = autorizacion_vigente(datos, herramienta["codigo"], herramienta["ubicacion"], momento)
    if vigente is not None:
        lineas.append(("Permanencia autorizada", "hasta " + fecha_para_mostrar(vigente["fecha_fin"])
                       + " por " + vigente["residente"]))
    if herramienta["observaciones"] != "":
        lineas.append(("Observaciones", herramienta["observaciones"]))
    return lineas


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


def resumen_tablero(datos, ahora=None):
    """Cuenta herramientas para las 4 tarjetas del tablero web."""
    resumen = {"disponibles": 0, "asignadas": 0, "vencidas": 0, "danadas": 0}
    for herramienta in datos["herramientas"]:
        if herramienta["estado"] == "disponible":
            resumen["disponibles"] = resumen["disponibles"] + 1
        if herramienta["estado"] == "asignada":
            resumen["asignadas"] = resumen["asignadas"] + 1
        if herramienta["estado"] in ["dañada", "requiere revisión", "en reparación"]:
            resumen["danadas"] = resumen["danadas"] + 1
        if esta_vencida(datos, herramienta, ahora):
            resumen["vencidas"] = resumen["vencidas"] + 1
    return resumen
