"""Cambia la contraseña de un usuario de SICH (se guarda cifrada en datos/usuarios.json).

Uso:
    py cambiar_contrasena.py                      (pregunta usuario y contraseña)
    py cambiar_contrasena.py jpivaral             (pregunta solo la contraseña)

Antes de publicar SICH en internet hay que cambiar las 4 contraseñas de prueba,
porque están escritas en el README.
"""

import getpass
import sys

from sich.datos import cargar_datos, cifrar_contrasena, guardar_datos

MINIMO_CARACTERES = 8


def buscar_usuario(datos, nombre):
    """Devuelve el usuario con ese nombre, o None."""
    for usuario in datos["usuarios"]:
        if usuario["usuario"] == nombre.strip().lower():
            return usuario
    return None


def pedir_contrasena_nueva():
    """Pide la contraseña dos veces hasta que coincida y tenga el largo mínimo."""
    while True:
        primera = getpass.getpass("Contraseña nueva (mínimo " + str(MINIMO_CARACTERES)
                                  + " caracteres): ")
        if len(primera) < MINIMO_CARACTERES:
            print("Es muy corta. Use al menos", MINIMO_CARACTERES, "caracteres.")
            continue
        segunda = getpass.getpass("Repita la contraseña: ")
        if primera == segunda:
            return primera
        print("Las contraseñas no coinciden. Intente de nuevo.")


def main():
    datos, avisos = cargar_datos()
    for aviso in avisos:
        print(aviso)
    print("Usuarios:", ", ".join(u["usuario"] for u in datos["usuarios"]))
    if len(sys.argv) > 1:
        nombre = sys.argv[1]
    else:
        nombre = input("Usuario: ")
    usuario = buscar_usuario(datos, nombre)
    if usuario is None:
        print("No existe el usuario '" + nombre + "'.")
        return
    usuario["contrasena"] = cifrar_contrasena(pedir_contrasena_nueva())
    guardar_datos(datos)
    print("Contraseña de", usuario["usuario"], "actualizada.")


if __name__ == "__main__":
    try:
        main()
    except (KeyboardInterrupt, EOFError):
        print("\nCancelado. No se cambió nada.")
