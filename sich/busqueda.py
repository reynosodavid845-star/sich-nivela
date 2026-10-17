"""Búsqueda de herramientas por código oficial, nombre o apodo (factor diferenciador).

La búsqueda se adapta a cómo habla el personal:
  - No distingue mayúsculas ni tildes: 'La BailaRína' = 'la bailarina'.
  - Ignora artículos y palabras de relleno: 'la makita azul' = 'makita azul'.
  - Busca palabra por palabra y en cualquier orden: 'azul makita' encuentra PUL-03.
  - Revisa código, nombre, apodos, marca y categoría.
  - Reconoce códigos sin guion: 'com02' = 'COM-02'.
  - Si no encuentra nada, tolera errores de escritura: 'bailarna' -> bailarina.
"""

import unicodedata
from difflib import SequenceMatcher

from sich.catalogo import descripcion_corta
from sich.validaciones import leer_opcion, leer_texto_no_vacio

# Palabras que no ayudan a distinguir una herramienta y se ignoran al buscar.
PALABRAS_IGNORADAS = ["el", "la", "los", "las", "un", "una", "unos", "unas", "de", "del", "al",
                      "y", "con", "para", "por", "en"]

# Qué tan parecida debe ser una palabra mal escrita (0 a 1) para aceptarla.
PARECIDO_MINIMO = 0.8


def normalizar(texto):
    """Pasa a minúsculas, quita tildes y espacios repetidos."""
    texto = unicodedata.normalize("NFD", texto.strip().lower())
    sin_tildes = ""
    for letra in texto:
        if unicodedata.category(letra) != "Mn":   # Mn = marca de tilde
            sin_tildes = sin_tildes + letra
    return " ".join(sin_tildes.split())


def normalizar_codigo(texto):
    """Normaliza un código quitando guiones y espacios: 'NIV-LAS-01' -> 'nivlas01'."""
    return normalizar(texto).replace("-", "").replace(" ", "")


def palabras_utiles(texto):
    """Separa el texto en palabras normalizadas, sin artículos ni palabras de relleno.

    Si el texto solo tenía palabras de relleno (ej. 'la'), se devuelven tal cual.
    """
    todas = normalizar(texto).split()
    utiles = []
    for palabra in todas:
        if palabra not in PALABRAS_IGNORADAS:
            utiles.append(palabra)
    if len(utiles) == 0:
        return todas
    return utiles


def palabras_de_herramienta(herramienta):
    """Todas las palabras con que se puede reconocer una herramienta."""
    textos = [herramienta["codigo"], herramienta["nombre"], herramienta.get("marca", ""),
              herramienta.get("categoria", "")] + herramienta["apodos"]
    palabras = []
    for texto in textos:
        for palabra in normalizar(texto).split():
            palabras.append(palabra)
            palabras.append(palabra.replace("-", ""))   # 'cor-01' y 'cor01'
    palabras.append(normalizar_codigo(herramienta["codigo"]))
    return palabras


def se_parecen(palabra_buscada, palabra_herramienta):
    """True si dos palabras son casi iguales (para tolerar errores de escritura)."""
    if len(palabra_buscada) < 4 or len(palabra_herramienta) < 4:
        return False
    parecido = SequenceMatcher(None, palabra_buscada, palabra_herramienta).ratio()
    return parecido >= PARECIDO_MINIMO


def palabra_coincide(palabra_buscada, palabras, aproximada):
    """True si la palabra buscada está dentro de alguna palabra de la herramienta
    (o, en modo aproximado, si se parece a alguna)."""
    sin_guion = palabra_buscada.replace("-", "")
    for palabra in palabras:
        if palabra_buscada in palabra or sin_guion in palabra:
            return True
        if aproximada and se_parecen(sin_guion, palabra):
            return True
    return False


def herramientas_que_coinciden(datos, palabras_buscadas, aproximada):
    """Herramientas en las que aparecen TODAS las palabras buscadas."""
    encontradas = []
    for herramienta in datos["herramientas"]:
        palabras = palabras_de_herramienta(herramienta)
        coinciden_todas = True
        for palabra_buscada in palabras_buscadas:
            if not palabra_coincide(palabra_buscada, palabras, aproximada):
                coinciden_todas = False
        if coinciden_todas:
            encontradas.append(herramienta)
    return encontradas


def buscar_con_detalle(datos, texto):
    """Busca herramientas y devuelve (lista, aproximada).

    1. Si el texto es exactamente un código oficial, devuelve solo esa herramienta.
    2. Si no, devuelve las herramientas que contienen todas las palabras buscadas.
    3. Si no hubo ninguna, repite tolerando errores de escritura (aproximada = True).
    Una lista vacía significa que no hubo coincidencias.
    """
    if normalizar(texto) == "":
        return [], False
    codigo_buscado = normalizar_codigo(texto)
    for herramienta in datos["herramientas"]:
        if normalizar_codigo(herramienta["codigo"]) == codigo_buscado:
            return [herramienta], False
    palabras_buscadas = palabras_utiles(texto)
    encontradas = herramientas_que_coinciden(datos, palabras_buscadas, False)
    if len(encontradas) > 0:
        return encontradas, False
    return herramientas_que_coinciden(datos, palabras_buscadas, True), True


def buscar_herramienta(datos, texto):
    """Devuelve la lista de herramientas que coinciden con el texto."""
    encontradas, aproximada = buscar_con_detalle(datos, texto)
    return encontradas


def elegir_de_lista(herramientas):
    """Muestra varias herramientas numeradas y pide elegir una (0 = buscar otra vez)."""
    print("\nSe encontraron", len(herramientas), "herramientas con ese nombre o apodo:")
    opciones = ["0"]
    numero = 1
    for herramienta in herramientas:
        print(" ", str(numero) + ".", descripcion_corta(herramienta))
        opciones.append(str(numero))
        numero = numero + 1
    eleccion = leer_opcion("Elija el número de la herramienta (0 = buscar otra vez): ", opciones)
    if eleccion == "0":
        return None
    return herramientas[int(eleccion) - 1]


def seleccionar_herramienta(datos):
    """Pide código, nombre o apodo hasta encontrar una herramienta.

    Escribir 0 cancela y devuelve None.
    """
    while True:
        texto = leer_texto_no_vacio("Escriba código, nombre o apodo (ej. bailarina) "
                                    "o 0 para cancelar: ")
        if texto == "0":
            return None
        encontradas, aproximada = buscar_con_detalle(datos, texto)
        if len(encontradas) == 0:
            print("No se encontró ninguna herramienta con '" + texto + "'. "
                  "Intente con otro código, nombre o apodo.")
            continue
        if aproximada:
            print("No hubo coincidencia exacta con '" + texto + "'; se muestran las parecidas.")
        if len(encontradas) == 1:
            print("Herramienta encontrada:", descripcion_corta(encontradas[0]))
            return encontradas[0]
        elegida = elegir_de_lista(encontradas)
        if elegida is not None:
            return elegida
