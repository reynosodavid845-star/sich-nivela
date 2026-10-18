"""Administración de cuentas de usuario (la usa el propietario desde la página web).

El propietario puede crear cuentas, restablecer contraseñas y desactivar o
reactivar cuentas. Cualquier usuario puede cambiar su propia contraseña.
Todas las funciones devuelven (exito, mensaje), igual que el Módulo 2.
"""

import os
import secrets

from sich.autenticacion import NOMBRES_ROL
from sich.datos import CARPETA_DATOS, cifrar_contrasena
from sich.catalogo import obras_activas

MINIMO_CONTRASENA = 8
LETRAS_PERMITIDAS = "abcdefghijklmnopqrstuvwxyz0123456789._-"
ARCHIVO_CODIGO = "codigo_configuracion.txt"


def buscar_usuario(datos, nombre_usuario):
    """Devuelve la cuenta con ese nombre de usuario, o None."""
    for usuario in datos["usuarios"]:
        if usuario["usuario"] == nombre_usuario.strip().lower():
            return usuario
    return None


def es_propietario(usuario):
    """True si la cuenta tiene el rol de propietario."""
    return usuario is not None and usuario["rol"] == "propietario"


def hay_propietario(datos):
    """True si existe al menos una cuenta de propietario activa."""
    for usuario in datos["usuarios"]:
        if usuario["rol"] == "propietario" and usuario.get("activo", True):
            return True
    return False


def error_en_nombre_usuario(datos, nombre_usuario):
    """Revisa un nombre de usuario nuevo. Devuelve el error o ''."""
    nombre = nombre_usuario.strip().lower()
    if len(nombre) < 3 or len(nombre) > 20:
        return "El usuario debe tener entre 3 y 20 caracteres."
    for letra in nombre:
        if letra not in LETRAS_PERMITIDAS:
            return "El usuario solo puede tener letras sin tilde, números, punto, guion o guion bajo."
    if buscar_usuario(datos, nombre) is not None:
        return "Ya existe una cuenta con el usuario '" + nombre + "'."
    return ""


def error_en_contrasena(contrasena, repetida):
    """Revisa una contraseña nueva. Devuelve el error o ''."""
    if len(contrasena) < MINIMO_CONTRASENA:
        return "La contraseña debe tener al menos " + str(MINIMO_CONTRASENA) + " caracteres."
    if contrasena != repetida:
        return "Las dos contraseñas no coinciden."
    return ""


def crear_usuario(datos, propietario, nombre_usuario, nombre, rol, contrasena, repetida,
                  obra=""):
    """El propietario crea una cuenta nueva. Devuelve (exito, mensaje)."""
    if not es_propietario(propietario):
        return False, "Solo el propietario puede crear cuentas."
    errores = []
    error = error_en_nombre_usuario(datos, nombre_usuario)
    if error != "":
        errores.append(error)
    if nombre.strip() == "":
        errores.append("Escriba el nombre de la persona.")
    if rol not in NOMBRES_ROL:
        errores.append("Elija un rol de la lista.")
    if rol == "maestro" and obra not in [o["codigo"] for o in obras_activas(datos)]:
        errores.append("Elija la obra del maestro.")
    error = error_en_contrasena(contrasena, repetida)
    if error != "":
        errores.append(error)
    if len(errores) > 0:
        return False, " ".join(errores)
    datos["usuarios"].append({
        "usuario": nombre_usuario.strip().lower(),
        "nombre": nombre.strip(),
        "rol": rol,
        "contrasena": cifrar_contrasena(contrasena),
        "obra": obra if rol == "maestro" else "",
        "activo": True,
        "creado_por": propietario["usuario"],
    })
    return True, ("Cuenta creada: " + nombre_usuario.strip().lower() + " ("
                  + NOMBRES_ROL[rol] + "). Entréguele su usuario y contraseña en privado.")


def restablecer_contrasena(datos, propietario, nombre_usuario, contrasena, repetida):
    """El propietario pone una contraseña nueva a cualquier cuenta."""
    if not es_propietario(propietario):
        return False, "Solo el propietario puede restablecer contraseñas."
    usuario = buscar_usuario(datos, nombre_usuario)
    if usuario is None:
        return False, "No existe la cuenta '" + nombre_usuario + "'."
    error = error_en_contrasena(contrasena, repetida)
    if error != "":
        return False, error
    usuario["contrasena"] = cifrar_contrasena(contrasena)
    return True, "Contraseña de " + usuario["usuario"] + " restablecida."


def cambiar_estado(datos, propietario, nombre_usuario, activo):
    """El propietario desactiva o reactiva una cuenta (no se borra su historial)."""
    if not es_propietario(propietario):
        return False, "Solo el propietario puede activar o desactivar cuentas."
    usuario = buscar_usuario(datos, nombre_usuario)
    if usuario is None:
        return False, "No existe la cuenta '" + nombre_usuario + "'."
    if usuario["usuario"] == propietario["usuario"] and not activo:
        return False, "No puede desactivar su propia cuenta."
    usuario["activo"] = activo
    if activo:
        return True, "Cuenta " + usuario["usuario"] + " activada: ya puede entrar."
    return True, "Cuenta " + usuario["usuario"] + " desactivada: ya no puede entrar."


def cambiar_mi_contrasena(datos, usuario, actual, nueva, repetida):
    """Cualquier usuario cambia su propia contraseña, sabiendo la actual."""
    if usuario["contrasena"] != cifrar_contrasena(actual):
        return False, "La contraseña actual no es correcta."
    error = error_en_contrasena(nueva, repetida)
    if error != "":
        return False, error
    usuario["contrasena"] = cifrar_contrasena(nueva)
    return True, "Su contraseña se cambió correctamente."


# ---------------------------------------------------- primer propietario

def ruta_codigo():
    """Archivo con el código de configuración (solo lo ve quien administra el servidor)."""
    return os.path.join(CARPETA_DATOS, ARCHIVO_CODIGO)


def codigo_de_configuracion(datos):
    """Devuelve el código para crear el primer propietario ('' si ya existe uno).

    La primera vez lo genera al azar, lo guarda en datos/codigo_configuracion.txt
    y lo escribe en el registro del servidor (Logs).
    """
    if hay_propietario(datos):
        return ""
    try:
        with open(ruta_codigo(), "r", encoding="utf-8") as archivo:
            codigo = archivo.read().strip()
        if codigo != "":
            return codigo
    except OSError:
        pass
    codigo = secrets.token_hex(4).upper()
    os.makedirs(CARPETA_DATOS, exist_ok=True)
    with open(ruta_codigo(), "w", encoding="utf-8") as archivo:
        archivo.write(codigo + "\n")
    print("SICH: codigo de configuracion del propietario: " + codigo, flush=True)
    return codigo


def crear_propietario_inicial(datos, codigo_escrito, nombre_usuario, nombre, contrasena,
                              repetida):
    """Crea la primera cuenta de propietario si el código es correcto."""
    if hay_propietario(datos):
        return False, "Ya existe un propietario. Pídale a él que le cree una cuenta."
    codigo = codigo_de_configuracion(datos)
    if not secrets.compare_digest(codigo_escrito.strip().upper(), codigo):
        return False, "El código de configuración no es correcto."
    errores = []
    error = error_en_nombre_usuario(datos, nombre_usuario)
    if error != "":
        errores.append(error)
    if nombre.strip() == "":
        errores.append("Escriba su nombre.")
    error = error_en_contrasena(contrasena, repetida)
    if error != "":
        errores.append(error)
    if len(errores) > 0:
        return False, " ".join(errores)
    datos["usuarios"].append({
        "usuario": nombre_usuario.strip().lower(),
        "nombre": nombre.strip(),
        "rol": "propietario",
        "contrasena": cifrar_contrasena(contrasena),
        "obra": "",
        "activo": True,
        "creado_por": "configuracion inicial",
    })
    try:
        os.remove(ruta_codigo())   # el código ya no sirve
    except OSError:
        pass
    return True, "Cuenta de propietario creada. Desde «Administrar cuentas» puede crear las demás."
