"""SICH - Sistema de Control de Herramientas (versión de consola).

Grupo No. 10 - Expediente-001 - Algoritmos y Programación Básica, UVG.
Ejecutar:  py main.py   (en macOS/Linux: python3 main.py)
Reiniciar los datos de prueba:  py main.py --reiniciar
"""

import sys

from sich.autenticacion import iniciar_sesion
from sich.datos import cargar_datos, reiniciar_datos
from sich.menus import menu_principal


def mostrar_bienvenida():
    """Muestra el nombre del sistema."""
    print("=" * 60)
    print(" SICH - Sistema de Control de Herramientas")
    print(" Nivela Obras Civiles, S.A.")
    print("=" * 60)


def ejecutar_sich():
    """Ciclo principal: cargar datos -> iniciar sesión -> menú por rol."""
    mostrar_bienvenida()
    datos, avisos = cargar_datos()
    for aviso in avisos:
        print(aviso)
    while True:
        usuario = iniciar_sesion(datos)
        if usuario is None:
            break
        resultado = menu_principal(datos, usuario)
        if resultado == "salir":
            break
    print("\nGracias por usar SICH. Programa finalizado.")


def main():
    """Punto de entrada. Atrapa la interrupción del teclado para salir sin errores."""
    if "--reiniciar" in sys.argv:
        reiniciar_datos()
        print("Datos de prueba reiniciados en la carpeta datos/.")
        return
    try:
        ejecutar_sich()
    except (KeyboardInterrupt, EOFError):
        print("\n\nPrograma finalizado por el usuario.")


if __name__ == "__main__":
    main()
