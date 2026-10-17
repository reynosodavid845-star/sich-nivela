"""Módulo 1 - Catálogo de herramientas.

Las funcionalidades 1.1 Registrar, 1.2 Asociar apodos y 1.3 Modificar quedan
pendientes para la Fase 4. Aquí solo están las funciones de lectura que
necesita el Módulo 2 (obtener herramientas y obras de los datos de prueba).
"""

ESTADOS = ["disponible", "asignada", "dañada", "en reparación", "requiere revisión",
           "dada de baja"]


def obtener_herramienta(datos, codigo):
    """Busca una herramienta por su código oficial exacto. Devuelve None si no existe."""
    for herramienta in datos["herramientas"]:
        if herramienta["codigo"].upper() == codigo.strip().upper():
            return herramienta
    return None


def obtener_obra(datos, codigo):
    """Busca una obra por código (sin importar mayúsculas). Devuelve None si no existe."""
    for obra in datos["obras"]:
        if obra["codigo"].upper() == codigo.strip().upper():
            return obra
    return None


def obras_activas(datos):
    """Lista de obras activas (sin contar la bodega)."""
    lista = []
    for obra in datos["obras"]:
        if obra["activa"] and not obra["es_bodega"]:
            lista.append(obra)
    return lista


def nombre_obra(datos, codigo):
    """Devuelve 'CÓDIGO - nombre' de una obra, o el código si no existe."""
    obra = obtener_obra(datos, codigo)
    if obra is None:
        return codigo
    if obra["es_bodega"]:
        return "Bodega"
    return obra["codigo"] + " - " + obra["nombre"]


def descripcion_corta(herramienta):
    """Texto de una línea: código, nombre, apodos, estado y ubicación."""
    texto = herramienta["codigo"] + " - " + herramienta["nombre"]
    if len(herramienta["apodos"]) > 0:
        texto = texto + " (" + ", ".join(herramienta["apodos"]) + ")"
    return texto + " | " + herramienta["estado"].upper() + " | " + herramienta["ubicacion"]
