"""Pruebas automáticas de SICH (casos CP del Módulo 2 y casos CN de navegación).

Cada caso ejecuta el programa de consola real (main.py) escribiendo las
entradas automáticamente, revisa los mensajes que aparecen y el estado de
los datos guardados. Las pruebas usan una carpeta temporal, así que NO
modifican los archivos de datos/.

Ejecutar:  py pruebas.py
Genera:    evidencias/CP-01.txt ... (transcripción de cada ejecución)
           evidencias/resultados_pruebas.json
"""

import builtins
import contextlib
import io
import json
import os
import sys
import tempfile
from datetime import datetime

# Carpeta temporal para los datos de prueba (antes de importar sich).
CARPETA_TEMPORAL = tempfile.mkdtemp(prefix="sich_pruebas_")
os.environ["SICH_DATOS"] = CARPETA_TEMPORAL

import main  # noqa: E402
from sich import datos as modulo_datos  # noqa: E402
from sich.catalogo import obtener_herramienta  # noqa: E402
from sich.movimientos import esta_vencida, motivo_bloqueo_salida, registrar_salida  # noqa: E402

CARPETA_EVIDENCIAS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "evidencias")

BODEGA = ["jpivaral", "bodega123"]
RESIDENTE = ["ecifuentes", "residente123"]
GERENTE = ["prodas", "gerente123"]
MAESTRO = ["esantos", "maestro123"]
VOLVER_Y_SALIR = ["", "0", "0"]   # Enter, regresar del submenú y salir


# ---------------------------------------------------------------- utilidades

def ejecutar_consola(entradas):
    """Ejecuta main.py con entradas simuladas. Devuelve la transcripción completa."""
    pendientes = list(entradas)
    salida = io.StringIO()
    input_original = builtins.input

    def entrada_simulada(mensaje=""):
        print(mensaje, end="")
        if len(pendientes) == 0:
            raise EOFError
        valor = pendientes.pop(0)
        if "Contraseña" in mensaje:
            print("*" * len(valor))   # no mostrar la contraseña en la evidencia
        else:
            print(valor)
        return valor

    builtins.input = entrada_simulada
    argumentos_originales = sys.argv
    sys.argv = ["main.py"]
    try:
        with contextlib.redirect_stdout(salida):
            main.main()
    finally:
        builtins.input = input_original
        sys.argv = argumentos_originales
    return salida.getvalue()


def herramienta_guardada(codigo):
    """Lee los datos guardados y devuelve la herramienta."""
    datos, avisos = modulo_datos.cargar_datos()
    return obtener_herramienta(datos, codigo)


def datos_guardados():
    """Lee todos los datos guardados."""
    datos, avisos = modulo_datos.cargar_datos()
    return datos


def estado_de(codigo):
    """Estado y ubicación guardados de una herramienta."""
    herramienta = herramienta_guardada(codigo)
    return herramienta["estado"], herramienta["ubicacion"]


# ------------------------------------------------------------------- casos

def preparar_json_corrupto():
    with open(modulo_datos.ruta_archivo("herramientas"), "w", encoding="utf-8") as archivo:
        archivo.write("{ esto no es JSON")


def preparar_json_faltante():
    os.remove(modulo_datos.ruta_archivo("movimientos"))


def verificar_logica_horario():
    """La función que usa la web rechaza una devolución fuera de horario sin residente."""
    datos = modulo_datos.datos_iniciales()
    usuario = datos["usuarios"][0]
    exito, mensaje = registrar_salida(datos, usuario, "ROT-01", "VN-014", "Luis Aguilar",
                                      datetime(2026, 10, 16, 6, 15), datetime(2026, 10, 16, 19, 0))
    return (not exito and "fuera del horario" in mensaje
            and obtener_herramienta(datos, "ROT-01")["estado"] == "disponible"), mensaje


CASOS = [
    # ------------------------- 2.1 Registrar salida
    {"id": "CP-01", "funcionalidad": "2.1 Registrar salida",
     "condiciones": "COM-01 disponible en Bodega. Usuario jpivaral (bodega).",
     "entradas": BODEGA + ["2", "1", "bailarina", "1", "VN-014", "Erick Santos",
                           "16/10/2026 06:15", "16/10/2026 17:00", "Va en el picop gris", "S"]
                 + VOLVER_Y_SALIR,
     "esperado": "El apodo 'bailarina' muestra COM-01 y COM-02; se elige COM-01, se confirma y "
                 "queda ASIGNADA en VN-014 con mensaje de operación exitosa.",
     "textos": ["Se encontraron 2 herramientas", "¿Confirmar operación?",
                "Operación exitosa: salida registrada. COM-01"],
     "verificar": lambda: estado_de("COM-01") == ("asignada", "VN-014")},
    {"id": "CP-02", "funcionalidad": "2.1 Registrar salida",
     "condiciones": "COM-02 en estado 'requiere revisión' (ruido raro).",
     "entradas": BODEGA + ["2", "1", "COM-02"] + VOLVER_Y_SALIR,
     "esperado": "La salida se bloquea y explica que debe registrarse una revisión.",
     "textos": ["No se puede registrar la salida: COM-02 requiere revisión"],
     "verificar": lambda: estado_de("COM-02") == ("requiere revisión", "Bodega")},
    {"id": "CP-03", "funcionalidad": "2.1 Registrar salida",
     "condiciones": "EXT-02 'extensión naranja' dada de baja.",
     "entradas": BODEGA + ["2", "1", "extension naranja"] + VOLVER_Y_SALIR,
     "esperado": "Encuentra EXT-02 por su apodo sin tilde y bloquea la salida (dada de baja).",
     "textos": ["EXT-02 está dada de baja y no se debe usar"],
     "verificar": lambda: estado_de("EXT-02") == ("dada de baja", "Bodega")},
    {"id": "CP-04", "funcionalidad": "2.1 Registrar salida",
     "condiciones": "ROT-01 disponible. Obra CIS-005 inactiva.",
     "entradas": BODEGA + ["2", "1", "ABC-99", "rotomartillo", "1", "CIS-005", "XYZ-1", "EUC-022",
                           "", "Luis Aguilar", "32/13/2026 25:00", "16/10/2026 06:15",
                           "16/10/2026 05:00", "16/10/2026 19:00", "N", "16/10/2026 19:00", "S",
                           "Ing. Esteban Cifuentes", "", "S"] + VOLVER_Y_SALIR,
     "esperado": "Rechaza herramienta inexistente, obra inactiva, obra inexistente, responsable "
                 "vacío, fecha inválida y devolución antes de la salida; advierte el horario "
                 "fuera de 16:30-17:15 y lo acepta con el residente que autoriza.",
     "textos": ["No se encontró ninguna herramienta con 'ABC-99'", "no está activa",
                "La obra 'XYZ-1' no existe", "Este campo es obligatorio", "Fecha inválida",
                "debe ser posterior a la salida", "fuera del horario 16:30-17:15",
                "Operación exitosa: salida registrada. ROT-01"],
     "verificar": lambda: estado_de("ROT-01") == ("asignada", "EUC-022")},
    {"id": "CP-05", "funcionalidad": "2.1 Registrar salida",
     "condiciones": "COM-01 disponible.",
     "entradas": BODEGA + ["2", "1", "rana", "Z11-009", "Erick Santos", "16/10/2026 06:15",
                           "16/10/2026 17:00", "", "N"] + VOLVER_Y_SALIR,
     "esperado": "El usuario responde N en '¿Confirmar operación?': no se guarda nada.",
     "textos": ["Operación cancelada. No se guardó ningún cambio."],
     "verificar": lambda: estado_de("COM-01") == ("disponible", "Bodega")},
    # ------------------------- 2.2 Registrar devolución
    {"id": "CP-06", "funcionalidad": "2.2 Registrar devolución",
     "condiciones": "ROT-02 asignada en EUC-022, devolución esperada 14/10/2026 17:00 (vencida).",
     "entradas": BODEGA + ["2", "2", "ROT-02", "16/10/2026 16:45", "1", "", "S"] + VOLVER_Y_SALIR,
     "esperado": "Devolución registrada en buen estado, indica que llegó TARDE y ROT-02 queda "
                 "disponible en Bodega.",
     "textos": ["llegó TARDE", "está en Bodega con estado 'disponible'"],
     "verificar": lambda: estado_de("ROT-02") == ("disponible", "Bodega")},
    {"id": "CP-07", "funcionalidad": "2.2 Registrar devolución",
     "condiciones": "MEZ-02 está en Bodega (no tiene salida).",
     "entradas": BODEGA + ["2", "2", "MEZ-02"] + VOLVER_Y_SALIR,
     "esperado": "Rechaza la devolución porque la herramienta no tiene salida pendiente.",
     "textos": ["MEZ-02 está en bodega: no tiene una salida pendiente de devolución."],
     "verificar": lambda: estado_de("MEZ-02") == ("disponible", "Bodega")},
    {"id": "CP-08", "funcionalidad": "2.2 Registrar devolución",
     "condiciones": "MEZ-01 asignada en VN-014 desde 16/10/2026 06:15.",
     "entradas": BODEGA + ["2", "2", "trompo", "15/10/2026 08:00", "16/10/2026 16:40", "2",
                           "Manija quebrada", "S", "S", "Manija quebrada al descargar",
                           "16/10/2026 16:40", "Luis Aguilar", "S"] + VOLVER_Y_SALIR,
     "esperado": "Rechaza una fecha anterior a la salida; con 'con daño' la herramienta vuelve "
                 "a Bodega, ofrece reportar el daño y queda DAÑADA.",
     "textos": ["no puede ser anterior a la salida", "¿Desea reportar el daño ahora?",
                "quedó DAÑADA"],
     "verificar": lambda: estado_de("MEZ-01") == ("dañada", "Bodega")},
    {"id": "CP-09", "funcionalidad": "2.2 Registrar devolución",
     "condiciones": "ROT-02 (equipo con motor) asignada en EUC-022.",
     "entradas": BODEGA + ["2", "2", "ROT-02", "16/10/2026 16:50", "1", "Hace ruido raro", "S"]
                 + VOLVER_Y_SALIR,
     "esperado": "Aunque se recibe 'bueno', por el memorando (ruido) queda 'requiere revisión'.",
     "textos": ["estado 'requiere revisión'", "Debe registrar una revisión"],
     "verificar": lambda: estado_de("ROT-02") == ("requiere revisión", "Bodega")},
    # ------------------------- 2.3 Registrar traslado
    {"id": "CP-10", "funcionalidad": "2.3 Registrar traslado",
     "condiciones": "MEZ-01 asignada en VN-014. Usuario ecifuentes (residente).",
     "entradas": RESIDENTE + ["2", "3", "MEZ-01", "Z11-009", "Erick Santos", "", "S"]
                 + VOLVER_Y_SALIR,
     "esperado": "Muestra la obra de origen VN-014, registra el traslado a Z11-009 sin pasar "
                 "por bodega y cambia el responsable.",
     "textos": ["Obra de origen (ubicación actual): VN-014", "pasó de VN-014 a Z11-009"],
     "verificar": lambda: estado_de("MEZ-01") == ("asignada", "Z11-009")
                          and herramienta_guardada("MEZ-01")["responsable"] == "Erick Santos"},
    {"id": "CP-11", "funcionalidad": "2.3 Registrar traslado",
     "condiciones": "MEZ-01 asignada en VN-014.",
     "entradas": RESIDENTE + ["2", "3", "MEZ-01", "VN-014", "EUC-022", "Luis Aguilar", "", "N"]
                 + VOLVER_Y_SALIR,
     "esperado": "Rechaza el destino VN-014 (igual al origen); luego el usuario cancela.",
     "textos": ["debe ser distinta de la obra de origen (VN-014)", "Operación cancelada"],
     "verificar": lambda: estado_de("MEZ-01") == ("asignada", "VN-014")},
    {"id": "CP-12", "funcionalidad": "2.3 Registrar traslado",
     "condiciones": "Usuario jpivaral (bodega), sin permiso para traslados.",
     "entradas": BODEGA + ["2", "3"] + VOLVER_Y_SALIR,
     "esperado": "Muestra 'No tiene permisos para esta opción' y vuelve al submenú.",
     "textos": ["Registrar traslado  [sin permiso]", "No tiene permisos para esta opción."],
     "verificar": lambda: estado_de("MEZ-01") == ("asignada", "VN-014")},
    {"id": "CP-13", "funcionalidad": "2.3 Registrar traslado",
     "condiciones": "COM-01 está en Bodega.",
     "entradas": RESIDENTE + ["2", "3", "COM-01"] + VOLVER_Y_SALIR,
     "esperado": "Rechaza el traslado y sugiere usar 2.1 Registrar salida.",
     "textos": ["COM-01 está en bodega. Para enviarla a una obra use 2.1 Registrar salida."],
     "verificar": lambda: estado_de("COM-01") == ("disponible", "Bodega")},
    # ------------------------- 2.4 Reportar daño
    {"id": "CP-14", "funcionalidad": "2.4 Reportar daño",
     "condiciones": "PUL-03 disponible. Usuario esantos (maestro).",
     "entradas": MAESTRO + ["2", "4", "la makita azul", "Disco con fisura y cable pelado",
                            "16/10/2026 10:00", "Erick Santos", "S"] + VOLVER_Y_SALIR,
     "esperado": "Encuentra PUL-03 por apodo, registra el daño y la deja DAÑADA y bloqueada.",
     "textos": ["PUL-03 quedó DAÑADA"],
     "verificar": lambda: estado_de("PUL-03")[0] == "dañada"
                          and "dañada" in motivo_bloqueo_salida(herramienta_guardada("PUL-03"))},
    {"id": "CP-15", "funcionalidad": "2.4 Reportar daño",
     "condiciones": "PUL-03 disponible.",
     "entradas": MAESTRO + ["2", "4", "COR-01", "mal", "Se quebró el disco", "", "", "Erick Santos",
                            "N"] + VOLVER_Y_SALIR,
     "esperado": "Encuentra PUL-03 por el alias heredado COR-01; rechaza descripción de menos de "
                 "5 caracteres y responsable vacío; el usuario cancela.",
     "textos": ["Debe escribir al menos 5 caracteres", "Este campo es obligatorio",
                "Operación cancelada"],
     "verificar": lambda: estado_de("PUL-03")[0] == "disponible"},
    # ------------------------- 2.5 Registrar revisión
    {"id": "CP-16", "funcionalidad": "2.5 Registrar revisión",
     "condiciones": "COM-02 'requiere revisión' en Bodega.",
     "entradas": BODEGA + ["2", "5", "bailarina grande", "1", "Julián Pivaral",
                           "Motor sin ruido después de limpieza", "S"] + VOLVER_Y_SALIR,
     "esperado": "Resultado apta: COM-02 queda DISPONIBLE para salir.",
     "textos": ["memorando 14/02/2026", "COM-02 es APTA y queda DISPONIBLE"],
     "verificar": lambda: estado_de("COM-02") == ("disponible", "Bodega")},
    {"id": "CP-17", "funcionalidad": "2.5 Registrar revisión",
     "condiciones": "VIB-01 'requiere revisión' (cinta en el cable).",
     "entradas": BODEGA + ["2", "5", "vibrador", "2", "Julián Pivaral", "Cable expuesto", "S"]
                 + VOLVER_Y_SALIR,
     "esperado": "Resultado no apta: VIB-01 queda EN REPARACIÓN.",
     "textos": ["VIB-01 NO es apta y queda EN REPARACIÓN"],
     "verificar": lambda: estado_de("VIB-01") == ("en reparación", "Bodega")},
    {"id": "CP-18", "funcionalidad": "2.5 Registrar revisión",
     "condiciones": "MEZ-02 disponible (sin daño).",
     "entradas": BODEGA + ["2", "5", "MEZ-02"] + VOLVER_Y_SALIR,
     "esperado": "Rechaza la revisión: la herramienta no tiene daños ni revisión pendiente.",
     "textos": ["MEZ-02 está 'disponible': no tiene daños ni revisión pendiente."],
     "verificar": lambda: estado_de("MEZ-02") == ("disponible", "Bodega")},
    # ------------------------- 2.6 Autorizar permanencia
    {"id": "CP-19", "funcionalidad": "2.6 Autorizar permanencia en obra",
     "condiciones": "MEZ-01 asignada en VN-014, devolución esperada 16/10/2026 17:00.",
     "entradas": RESIDENTE + ["2", "6", "MEZ-01", "16/10/2026 17:00", "19/10/2026 06:15", "S",
                              "Cliente tiene garita", "S"] + VOLVER_Y_SALIR,
     "esperado": "Registra la autorización por escrito; el 17/10/2026 MEZ-01 NO aparece vencida.",
     "textos": ["registrada por escrito en SICH"],
     "verificar": lambda: len(datos_guardados()["autorizaciones"]) == 2
                          and not esta_vencida(datos_guardados(), herramienta_guardada("MEZ-01"),
                                               datetime(2026, 10, 17, 7, 0))},
    {"id": "CP-20", "funcionalidad": "2.6 Autorizar permanencia en obra",
     "condiciones": "ROT-02 asignada en EUC-022.",
     "entradas": RESIDENTE + ["2", "6", "ROT-02", "16/10/2026 17:00", "17/10/2026 06:15", "N"]
                 + VOLVER_Y_SALIR,
     "esperado": "El residente indica que el sitio NO tiene seguridad: la autorización se rechaza.",
     "textos": ["Autorización rechazada: el sitio debe tener seguridad"],
     "verificar": lambda: len(datos_guardados()["autorizaciones"]) == 1},
    {"id": "CP-21", "funcionalidad": "2.6 Autorizar permanencia en obra",
     "condiciones": "ROT-02 asignada en EUC-022.",
     "entradas": RESIDENTE + ["2", "6", "ROT-02", "16/10/2026 17:00", "15/10/2026 06:15",
                              "17/10/2026 06:15", "S", "", "N"] + VOLVER_Y_SALIR,
     "esperado": "Rechaza una fecha de fin anterior al inicio; luego el usuario cancela.",
     "textos": ["La fecha de fin debe ser posterior a la fecha de inicio.", "Operación cancelada"],
     "verificar": lambda: len(datos_guardados()["autorizaciones"]) == 1},
    {"id": "CP-22", "funcionalidad": "2.6 Autorizar permanencia en obra",
     "condiciones": "NIV-LAS-01 ya tiene la autorización 1 vigente hasta 31/12/2026.",
     "entradas": RESIDENTE + ["2", "6", "nivel", "1", "16/10/2026 17:00", "17/10/2026 06:15", "S",
                              "", "S"] + VOLVER_Y_SALIR,
     "esperado": "Detecta la autorización duplicada y no registra otra.",
     "textos": ["Ya existe la autorización 1 para NIV-LAS-01"],
     "verificar": lambda: len(datos_guardados()["autorizaciones"]) == 1},
    # ------------------------- 3.1 Buscar (usada por el módulo) y datos
    {"id": "CP-23", "funcionalidad": "3.1 Buscar herramienta (dependencia del módulo)",
     "condiciones": "Catálogo de prueba cargado. Usuario esantos (maestro).",
     "entradas": MAESTRO + ["3", "1", "Makita Azul", "S", "RANA", "S", "xyz", "N"] + VOLVER_Y_SALIR,
     "esperado": "Encuentra PUL-03 y COM-01 sin importar mayúsculas; 'xyz' no tiene resultados.",
     "textos": ["Código oficial: PUL-03", "Código oficial: COM-01",
                "No se encontró ninguna herramienta con 'xyz'"],
     "verificar": lambda: True},
    {"id": "CP-24", "funcionalidad": "Carga de datos (JSON corrupto)",
     "condiciones": "herramientas.json contiene texto que no es JSON.",
     "preparar": preparar_json_corrupto,
     "entradas": BODEGA + ["0"],
     "esperado": "Avisa que el archivo estaba dañado, lo recrea con los datos iniciales y el "
                 "programa sigue funcionando.",
     "textos": ["herramientas.json estaba dañado; se recreó"],
     "verificar": lambda: estado_de("COM-01") == ("disponible", "Bodega")},
    {"id": "CP-25", "funcionalidad": "Carga de datos (JSON faltante)",
     "condiciones": "Se borró movimientos.json.",
     "preparar": preparar_json_faltante,
     "entradas": BODEGA + ["0"],
     "esperado": "Avisa que no encontró el archivo y lo crea con los datos iniciales.",
     "textos": ["no se encontró movimientos.json"],
     "verificar": lambda: os.path.exists(modulo_datos.ruta_archivo("movimientos"))},
    # ------------------------- Navegación
    {"id": "CN-01", "funcionalidad": "Navegación: todos los submenús y regreso",
     "condiciones": "Usuario jpivaral.",
     "entradas": BODEGA + ["1", "0", "2", "0", "3", "0", "0"],
     "esperado": "Entra a los submenús 1, 2 y 3; con 0 regresa al menú principal y con 0 sale.",
     "textos": ["1. CATÁLOGO DE HERRAMIENTAS", "2. MOVIMIENTOS DE HERRAMIENTAS",
                "3. CONSULTAS Y SEGUIMIENTO", "Programa finalizado"],
     "verificar": lambda: True},
    {"id": "CN-02", "funcionalidad": "Navegación: opción inválida",
     "condiciones": "Usuario jpivaral.",
     "entradas": BODEGA + ["a", "", "7", "2", "9", "x", "0", "0"],
     "esperado": "Letras, vacío y números fuera de rango muestran 'Opción no válida, intente de "
                 "nuevo' y vuelven a pedir la opción sin cerrar el programa.",
     "textos": ["Opción no válida, intente de nuevo."],
     "minimo_repeticiones": ("Opción no válida, intente de nuevo.", 5),
     "verificar": lambda: True},
    {"id": "CN-03", "funcionalidad": "Navegación: opciones pendientes",
     "condiciones": "Usuario jpivaral.",
     "entradas": BODEGA + ["1", "1", "", "2", "", "3", "", "0", "3", "2", "", "3", "", "4", "",
                           "5", "", "0", "0"],
     "esperado": "1.1, 1.2, 1.3, 3.2, 3.3, 3.4 y 3.5 muestran 'Funcionalidad pendiente de "
                 "implementación' y regresan al submenú.",
     "textos": ["Funcionalidad pendiente de implementación"],
     "minimo_repeticiones": ("Funcionalidad pendiente de implementación", 7),
     "verificar": lambda: True},
    {"id": "CN-04", "funcionalidad": "Navegación: rol sin permiso",
     "condiciones": "Usuario prodas (gerente, solo consulta).",
     "entradas": GERENTE + ["2", "1", "", "6", "", "0", "1", "2", "", "0", "0"],
     "esperado": "Las opciones de movimientos y catálogo muestran 'No tiene permisos para esta "
                 "opción'.",
     "textos": ["No tiene permisos para esta opción."],
     "minimo_repeticiones": ("No tiene permisos para esta opción.", 3),
     "verificar": lambda: True},
    {"id": "CN-05", "funcionalidad": "Inicio de sesión: credenciales incorrectas y reintento",
     "condiciones": "Usuario jpivaral existe.",
     "entradas": ["jpivaral", "claveequivocada", "S", "jpivaral", "bodega123", "0"],
     "esperado": "Muestra 'Usuario o contraseña incorrectos', permite reintentar y entra.",
     "textos": ["Usuario o contraseña incorrectos.", "Le quedan 2 intento(s).",
                "Bienvenido(a), Julián Pivaral"],
     "verificar": lambda: True},
    {"id": "CN-06", "funcionalidad": "Inicio de sesión: 3 intentos fallidos",
     "condiciones": "Credenciales inexistentes.",
     "entradas": ["pedro", "1234", "S", "pedro", "1234", "S", "pedro", "1234"],
     "esperado": "Después del tercer intento fallido termina de forma controlada.",
     "textos": ["Se agotaron los 3 intentos.", "Programa finalizado."],
     "verificar": lambda: True},
    {"id": "CN-07", "funcionalidad": "Cerrar sesión, cambiar de usuario y salir",
     "condiciones": "Usuarios jpivaral y ecifuentes.",
     "entradas": BODEGA + ["9"] + RESIDENTE + ["0"],
     "esperado": "La opción 9 cierra la sesión y vuelve al inicio de sesión; la opción 0 sale.",
     "textos": ["Sesión cerrada.", "Bienvenido(a), Ing. Esteban Cifuentes",
                "Gracias por usar SICH. Programa finalizado."],
     "verificar": lambda: True},
    {"id": "CN-08", "funcionalidad": "Inicio de sesión: el usuario decide salir",
     "condiciones": "Credenciales incorrectas.",
     "entradas": ["jpivaral", "otra", "N"],
     "esperado": "Tras el error responde N a '¿Desea intentar de nuevo?' y el programa termina.",
     "textos": ["¿Desea intentar de nuevo?", "Programa finalizado."],
     "verificar": lambda: True},
]


def ejecutar_caso(caso):
    """Ejecuta un caso y devuelve el diccionario con su resultado."""
    modulo_datos.reiniciar_datos()
    if "preparar" in caso:
        caso["preparar"]()
    transcripcion = ejecutar_consola(caso["entradas"])
    faltantes = []
    for texto in caso["textos"]:
        if texto not in transcripcion:
            faltantes.append(texto)
    if "minimo_repeticiones" in caso:
        texto, minimo = caso["minimo_repeticiones"]
        if transcripcion.count(texto) < minimo:
            faltantes.append(texto + " (x" + str(minimo) + ")")
    datos_correctos = caso["verificar"]()
    satisfactorio = len(faltantes) == 0 and datos_correctos and "Traceback" not in transcripcion
    if satisfactorio:
        obtenido = "Se comportó como se esperaba: " + "; ".join(caso["textos"][-2:])
    else:
        obtenido = "Faltó: " + "; ".join(faltantes) + ". Datos correctos: " + str(datos_correctos)
    return {"id": caso["id"], "funcionalidad": caso["funcionalidad"],
            "condiciones": caso["condiciones"], "entradas": caso["entradas"],
            "esperado": caso["esperado"], "obtenido": obtenido,
            "estado": "Satisfactorio" if satisfactorio else "No satisfactorio",
            "evidencia": "evidencias/" + caso["id"] + ".txt", "transcripcion": transcripcion}


def guardar_evidencia(resultado):
    """Escribe la transcripción de un caso en evidencias/ID.txt."""
    os.makedirs(CARPETA_EVIDENCIAS, exist_ok=True)
    ruta = os.path.join(CARPETA_EVIDENCIAS, resultado["id"] + ".txt")
    with open(ruta, "w", encoding="utf-8") as archivo:
        archivo.write("Caso " + resultado["id"] + " - " + resultado["funcionalidad"] + "\n")
        archivo.write("Ejecutado: " + datetime.now().strftime("%d/%m/%Y %H:%M") + "\n")
        archivo.write("-" * 70 + "\n")
        archivo.write(resultado["transcripcion"])


def main_pruebas():
    """Ejecuta todos los casos, imprime el resumen y guarda las evidencias."""
    resultados = []
    for caso in CASOS:
        resultado = ejecutar_caso(caso)
        guardar_evidencia(resultado)
        resultados.append(resultado)
        print(resultado["id"].ljust(6), resultado["estado"].ljust(17), resultado["funcionalidad"])
    ok_logica, mensaje = verificar_logica_horario()
    print("CP-26 ", ("Satisfactorio" if ok_logica else "No satisfactorio").ljust(17),
          "2.1 lógica usada por la web:", mensaje)
    resultados.append({"id": "CP-26", "funcionalidad": "2.1 Registrar salida (función usada por la web)",
                       "condiciones": "ROT-01 disponible. Se llama directamente a registrar_salida().",
                       "entradas": ["ROT-01", "VN-014", "Luis Aguilar", "16/10/2026 06:15",
                                    "16/10/2026 19:00", "residente vacío"],
                       "esperado": "La función rechaza la devolución fuera de horario sin residente "
                                   "y no cambia la herramienta.",
                       "obtenido": mensaje,
                       "estado": "Satisfactorio" if ok_logica else "No satisfactorio",
                       "evidencia": "Salida de python pruebas.py", "transcripcion": ""})
    total_ok = 0
    for resultado in resultados:
        if resultado["estado"] == "Satisfactorio":
            total_ok = total_ok + 1
    print("\nResultado:", total_ok, "de", len(resultados), "casos satisfactorios.")
    with open(os.path.join(CARPETA_EVIDENCIAS, "resultados_pruebas.json"), "w",
              encoding="utf-8") as archivo:
        json.dump(resultados, archivo, ensure_ascii=False, indent=2)
    return total_ok == len(resultados)


if __name__ == "__main__":
    main_pruebas()
