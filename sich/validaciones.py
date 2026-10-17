"""Funciones para leer y validar datos escritos por el usuario en la consola,
y utilidades de fechas que comparten la consola y la página web."""

from datetime import datetime

from sich.datos import FORMATO_FECHA

FORMATO_PANTALLA = "%d/%m/%Y %H:%M"   # formato que escribe el usuario: 23/06/2026 06:15

MENSAJE_OPCION_INVALIDA = "Opción no válida, intente de nuevo."
MENSAJE_CAMPO_OBLIGATORIO = "Este campo es obligatorio. Escriba un valor."


# ---------- Utilidades de fechas ----------

def texto_a_fecha(texto):
    """Convierte 'AAAA-MM-DD HH:MM' (formato guardado) a datetime. Vacío -> None."""
    if texto == "" or texto is None:
        return None
    return datetime.strptime(texto, FORMATO_FECHA)


def fecha_a_texto(fecha):
    """Convierte un datetime al formato que se guarda en JSON."""
    return fecha.strftime(FORMATO_FECHA)


def fecha_para_mostrar(texto_guardado):
    """Convierte una fecha guardada al formato DD/MM/AAAA HH:MM. Vacío -> '-'."""
    if texto_guardado == "" or texto_guardado is None:
        return "-"
    return texto_a_fecha(texto_guardado).strftime(FORMATO_PANTALLA)


def interpretar_fecha_pantalla(texto):
    """Convierte 'DD/MM/AAAA HH:MM' a datetime. Devuelve None si es inválida."""
    try:
        return datetime.strptime(texto.strip(), FORMATO_PANTALLA)
    except ValueError:
        return None


# ---------- Lectura de datos en consola ----------

def leer_opcion(mensaje, opciones_validas):
    """Pide un número hasta que esté dentro de opciones_validas (lista de str).

    Si se escriben letras, nada o un número fuera de rango, muestra
    'Opción no válida, intente de nuevo' y vuelve a pedir.
    """
    while True:
        texto = input(mensaje).strip()
        try:
            numero = int(texto)
        except ValueError:
            print(MENSAJE_OPCION_INVALIDA)
            continue
        if str(numero) in opciones_validas:
            return str(numero)
        print(MENSAJE_OPCION_INVALIDA)


def leer_texto_no_vacio(mensaje):
    """Pide un texto hasta que no esté vacío."""
    while True:
        texto = input(mensaje).strip()
        if texto != "":
            return texto
        print(MENSAJE_CAMPO_OBLIGATORIO)


def leer_texto_minimo(mensaje, minimo):
    """Pide un texto con al menos 'minimo' caracteres."""
    while True:
        texto = leer_texto_no_vacio(mensaje)
        if len(texto) >= minimo:
            return texto
        print("Debe escribir al menos", minimo, "caracteres. Explique un poco más.")


def leer_texto_opcional(mensaje):
    """Pide un texto que puede quedar vacío."""
    return input(mensaje).strip()


def leer_fecha_hora(mensaje, valor_por_defecto):
    """Pide una fecha DD/MM/AAAA HH:MM. Enter vacío usa valor_por_defecto."""
    while True:
        texto = input(mensaje + " [Enter = " + valor_por_defecto.strftime(FORMATO_PANTALLA)
                      + "]: ").strip()
        if texto == "":
            return valor_por_defecto
        fecha = interpretar_fecha_pantalla(texto)
        if fecha is not None:
            return fecha
        print("Fecha inválida. Use el formato DD/MM/AAAA HH:MM (ej. 23/06/2026 06:15).")


def leer_opcion_de_lista(mensaje, valores_validos):
    """Pide un texto que esté en valores_validos (sin importar mayúsculas)."""
    while True:
        texto = input(mensaje).strip().lower()
        if texto in valores_validos:
            return texto
        print("Respuesta no válida. Escriba una de estas opciones:", ", ".join(valores_validos))


def confirmar(mensaje):
    """Pregunta S/N hasta recibir una respuesta válida. Devuelve True si es S."""
    while True:
        respuesta = input(mensaje + " (S/N): ").strip().upper()
        if respuesta == "S":
            return True
        if respuesta == "N":
            return False
        print("Responda S (sí) o N (no).")


def pausar():
    """Espera a que el usuario presione Enter para volver al menú."""
    input("\nPresione Enter para volver al menú...")


def mostrar_titulo(titulo):
    """Imprime un encabezado de pantalla."""
    print()
    print("=" * 60)
    print(" " + titulo)
    print("=" * 60)
