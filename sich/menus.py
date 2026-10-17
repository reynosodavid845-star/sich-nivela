"""Menú principal y submenús de SICH (consola).

La estructura de opciones (MENU_PRINCIPAL y SUBMENUS) también la usa la
página web, para que ambas versiones tengan exactamente las mismas opciones.
"""

from sich.autenticacion import MENSAJE_SIN_PERMISO, NOMBRES_ROL, tiene_permiso
from sich.consultas import proceso_buscar_herramienta
from sich.movimientos import proceso_autorizar_permanencia, proceso_registrar_devolucion, \
    proceso_registrar_revision, proceso_registrar_salida, proceso_registrar_traslado, \
    proceso_reportar_dano
from sich.validaciones import leer_opcion, mostrar_titulo, pausar

MENSAJE_PENDIENTE = "Funcionalidad pendiente de implementación"

MENU_PRINCIPAL = [
    ("1", "Catálogo de herramientas"),
    ("2", "Movimientos de herramientas"),
    ("3", "Consultas y seguimiento"),
    ("9", "Cerrar sesión"),
    ("0", "Salir"),
]

# Cada submenú: número -> (título, [(id_opcion, texto), ...])
SUBMENUS = {
    "1": ("1. CATÁLOGO DE HERRAMIENTAS", [
        ("1.1", "Registrar herramienta"),
        ("1.2", "Asociar apodos"),
        ("1.3", "Modificar herramienta"),
    ]),
    "2": ("2. MOVIMIENTOS DE HERRAMIENTAS", [
        ("2.1", "Registrar salida"),
        ("2.2", "Registrar devolución"),
        ("2.3", "Registrar traslado"),
        ("2.4", "Reportar daño"),
        ("2.5", "Registrar revisión"),
        ("2.6", "Autorizar permanencia en obra"),
    ]),
    "3": ("3. CONSULTAS Y SEGUIMIENTO", [
        ("3.1", "Buscar herramienta"),
        ("3.2", "Consultar disponibles"),
        ("3.3", "Devoluciones pendientes"),
        ("3.4", "Herramientas por obra"),
        ("3.5", "Historial de una herramienta"),
    ]),
}

# Opciones ya programadas. Las demás muestran MENSAJE_PENDIENTE.
FUNCIONES_IMPLEMENTADAS = {
    "2.1": proceso_registrar_salida,
    "2.2": proceso_registrar_devolucion,
    "2.3": proceso_registrar_traslado,
    "2.4": proceso_reportar_dano,
    "2.5": proceso_registrar_revision,
    "2.6": proceso_autorizar_permanencia,
    "3.1": proceso_buscar_herramienta,
}


def esta_implementada(id_opcion):
    """True si la opción ya está programada."""
    return id_opcion in FUNCIONES_IMPLEMENTADAS


def etiqueta_opcion(usuario, id_opcion, texto):
    """Texto de una opción con sus marcas de permiso y de pendiente."""
    etiqueta = texto
    if not tiene_permiso(usuario, id_opcion):
        etiqueta = etiqueta + "  [sin permiso]"
    elif not esta_implementada(id_opcion):
        etiqueta = etiqueta + "  [pendiente]"
    return etiqueta


def ejecutar_opcion(datos, usuario, id_opcion):
    """Revisa el permiso y ejecuta la opción, o avisa que está pendiente."""
    if not tiene_permiso(usuario, id_opcion):
        print("\n" + MENSAJE_SIN_PERMISO)
    elif not esta_implementada(id_opcion):
        print("\n" + MENSAJE_PENDIENTE)
    else:
        FUNCIONES_IMPLEMENTADAS[id_opcion](datos, usuario)
    pausar()


def mostrar_submenu(datos, usuario, numero_menu):
    """Muestra un submenú hasta que el usuario elija 0 (Regresar)."""
    titulo, opciones = SUBMENUS[numero_menu]
    while True:
        mostrar_titulo(titulo)
        validas = ["0"]
        for id_opcion, texto in opciones:
            numero = id_opcion.split(".")[1]
            print(" " + numero + ". " + etiqueta_opcion(usuario, id_opcion, texto))
            validas.append(numero)
        print(" 0. Regresar al menú principal")
        eleccion = leer_opcion("Elija una opción: ", validas)
        if eleccion == "0":
            return
        ejecutar_opcion(datos, usuario, numero_menu + "." + eleccion)


def menu_principal(datos, usuario):
    """Muestra el menú principal. Devuelve 'cerrar_sesion' o 'salir'."""
    while True:
        mostrar_titulo("SICH - MENÚ PRINCIPAL   (" + usuario["nombre"] + " - "
                       + NOMBRES_ROL[usuario["rol"]] + ")")
        validas = []
        for numero, texto in MENU_PRINCIPAL:
            print(" " + numero + ". " + texto)
            validas.append(numero)
        eleccion = leer_opcion("Elija una opción: ", validas)
        if eleccion == "9":
            print("\nSesión cerrada.")
            return "cerrar_sesion"
        if eleccion == "0":
            return "salir"
        mostrar_submenu(datos, usuario, eleccion)
