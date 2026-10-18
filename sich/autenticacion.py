"""Inicio de sesión y permisos por rol."""

from sich.datos import cifrar_contrasena
from sich.validaciones import confirmar, leer_texto_no_vacio, mostrar_titulo

MAXIMO_INTENTOS = 3
MENSAJE_SIN_PERMISO = "No tiene permisos para esta opción."

NOMBRES_ROL = {
    "bodega": "Encargado de bodega",
    "residente": "Residente de obra",
    "gerente": "Gerente de operaciones (solo consulta)",
    "maestro": "Maestro de obra / personal de campo",
    "propietario": "Propietario (administra las cuentas)",
}

# Opciones del menú que puede usar cada rol (según la Fase 2).
PERMISOS_POR_ROL = {
    "bodega": ["1.1", "1.2", "1.3", "2.1", "2.2", "2.4", "2.5",
               "3.1", "3.2", "3.3", "3.4", "3.5"],
    "residente": ["2.3", "2.4", "2.6", "3.1", "3.2", "3.3", "3.4", "3.5"],
    "gerente": ["3.1", "3.2", "3.3", "3.4", "3.5"],
    "maestro": ["2.4", "3.1", "3.4"],
    # El propietario puede usar todo y, además, administrar las cuentas (página web).
    "propietario": ["1.1", "1.2", "1.3", "2.1", "2.2", "2.3", "2.4", "2.5", "2.6",
                    "3.1", "3.2", "3.3", "3.4", "3.5"],
}


def verificar_credenciales(datos, nombre_usuario, contrasena):
    """Devuelve el usuario si las credenciales son correctas y la cuenta está activa."""
    contrasena_cifrada = cifrar_contrasena(contrasena)
    for usuario in datos["usuarios"]:
        if usuario["usuario"] == nombre_usuario.strip().lower() \
                and usuario["contrasena"] == contrasena_cifrada \
                and usuario.get("activo", True):
            return usuario
    return None


def iniciar_sesion(datos):
    """Pide usuario y contraseña (máximo 3 intentos). Devuelve el usuario o None."""
    intentos = 0
    while intentos < MAXIMO_INTENTOS:
        mostrar_titulo("SICH - INICIAR SESIÓN")
        nombre_usuario = leer_texto_no_vacio("Usuario: ")
        contrasena = leer_texto_no_vacio("Contraseña: ")
        usuario = verificar_credenciales(datos, nombre_usuario, contrasena)
        if usuario is not None:
            print("\nBienvenido(a),", usuario["nombre"], "-", NOMBRES_ROL[usuario["rol"]])
            return usuario
        intentos = intentos + 1
        print("\nUsuario o contraseña incorrectos.")
        restantes = MAXIMO_INTENTOS - intentos
        if restantes == 0:
            print("Se agotaron los", MAXIMO_INTENTOS, "intentos.")
            return None
        print("Le quedan", restantes, "intento(s).")
        if not confirmar("¿Desea intentar de nuevo?"):
            return None
    return None


def tiene_permiso(usuario, id_opcion):
    """Indica si el rol del usuario puede usar la opción (ej. '2.1')."""
    return id_opcion in PERMISOS_POR_ROL.get(usuario["rol"], [])


def obtener_menu_por_rol(usuario):
    """Devuelve la lista de opciones permitidas para el rol del usuario."""
    return PERMISOS_POR_ROL.get(usuario["rol"], [])
