"""Carga y guardado de los datos de SICH en archivos JSON.

Los datos se guardan en la carpeta datos/. Si un archivo falta o está
dañado (JSON corrupto), se vuelve a crear con los datos iniciales de prueba
y se avisa al usuario.
"""

import hashlib
import json
import os
import secrets

CARPETA_PROYECTO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# La variable de entorno SICH_DATOS permite usar otra carpeta (la usa pruebas.py
# para no modificar los datos reales).
CARPETA_DATOS = os.environ.get("SICH_DATOS", os.path.join(CARPETA_PROYECTO, "datos"))

COLECCIONES = ["herramientas", "obras", "usuarios", "movimientos", "danos", "autorizaciones"]

FORMATO_FECHA = "%Y-%m-%d %H:%M"   # formato en que se guardan las fechas en JSON

ORIGEN_PRUEBA = "Dato de demostración precargado"

ITERACIONES_CONTRASENA = 600000   # hace muy lento probar contraseñas robadas por fuerza bruta

# Contraseñas de demostración (están en el README). La versión publicada no las acepta.
CONTRASENAS_DEMOSTRACION = {
    "jpivaral": "bodega123",
    "ecifuentes": "residente123",
    "prodas": "gerente123",
    "esantos": "maestro123",
}

_cifradas_demostracion = {}   # se calculan una sola vez porque cifrar es lento a propósito


def calcular_huella(contrasena, sal, iteraciones):
    """Calcula la huella PBKDF2-SHA256 de una contraseña con su sal."""
    return hashlib.pbkdf2_hmac("sha256", contrasena.encode("utf-8"), bytes.fromhex(sal),
                               iteraciones).hex()


def cifrar_contrasena(contrasena):
    """Devuelve 'pbkdf2_sha256$iteraciones$sal$huella'. Cada contraseña lleva su propia sal
    al azar, así dos personas con la misma contraseña tienen huellas distintas."""
    sal = secrets.token_hex(16)
    huella = calcular_huella(contrasena, sal, ITERACIONES_CONTRASENA)
    return "pbkdf2_sha256$" + str(ITERACIONES_CONTRASENA) + "$" + sal + "$" + huella


def es_formato_antiguo(guardada):
    """True si la contraseña guardada usa el SHA-256 simple de versiones anteriores."""
    return not guardada.startswith("pbkdf2_sha256$")


def contrasena_correcta(contrasena, guardada):
    """Compara una contraseña escrita con la guardada (acepta también el formato antiguo)."""
    if es_formato_antiguo(guardada):
        calculada = hashlib.sha256(contrasena.encode("utf-8")).hexdigest()
        return secrets.compare_digest(calculada, guardada)
    partes = guardada.split("$")
    if len(partes) != 4:
        return False
    calculada = calcular_huella(contrasena, partes[2], int(partes[1]))
    return secrets.compare_digest(calculada, partes[3])


def es_contrasena_de_demostracion(contrasena):
    """True si es una de las contraseñas de demostración publicadas en el README."""
    return contrasena in CONTRASENAS_DEMOSTRACION.values()


def cifrada_de_demostracion(nombre_usuario):
    """Contraseña de demostración cifrada de un usuario."""
    if nombre_usuario not in _cifradas_demostracion:
        _cifradas_demostracion[nombre_usuario] = cifrar_contrasena(
            CONTRASENAS_DEMOSTRACION[nombre_usuario])
    return _cifradas_demostracion[nombre_usuario]


def crear_herramienta(codigo, nombre, categoria, marca, estado, apodos, motor_o_cable,
                      ubicacion="Bodega", responsable="", fecha_salida="",
                      devolucion_esperada="", observaciones=""):
    """Arma el diccionario de una herramienta de prueba."""
    return {
        "codigo": codigo,
        "nombre": nombre,
        "categoria": categoria,
        "marca": marca,
        "estado": estado,
        "apodos": apodos,
        "motor_o_cable": motor_o_cable,
        "ubicacion": ubicacion,
        "responsable": responsable,
        "fecha_salida": fecha_salida,
        "devolucion_esperada": devolucion_esperada,
        "observaciones": observaciones,
        "origen": ORIGEN_PRUEBA,
    }


def herramientas_iniciales():
    """Catálogo de prueba tomado del Expediente-001."""
    return [
        crear_herramienta("COM-01", "Compactadora pequeña", "Compactación", "Wacker Neuson",
                          "disponible", ["bailarina", "rana", "bailarina chiquita"], True),
        crear_herramienta("COM-02", "Compactadora", "Compactación", "Wacker Neuson",
                          "requiere revisión", ["bailarina grande"], True,
                          observaciones="Regresó el viernes con ruido raro (Julián Pivaral)."),
        crear_herramienta("ROT-01", "Rotomartillo", "Perforación", "Bosch", "disponible",
                          ["roto"], True),
        crear_herramienta("ROT-02", "Rotomartillo", "Perforación", "Bosch", "asignada",
                          ["roto"], True, ubicacion="EUC-022", responsable="Erick Santos",
                          fecha_salida="2026-10-14 06:15", devolucion_esperada="2026-10-14 17:00"),
        crear_herramienta("ROT-03", "Rotomartillo", "Perforación", "DeWalt", "disponible",
                          ["roto"], True),
        crear_herramienta("MEZ-01", "Mezcladora grande", "Mezclado", "Honda", "asignada",
                          ["trompo", "mezcladora grande"], True, ubicacion="VN-014",
                          responsable="Luis Aguilar", fecha_salida="2026-10-16 06:15",
                          devolucion_esperada="2026-10-16 17:00"),
        crear_herramienta("MEZ-02", "Mezcladora pequeña", "Mezclado", "Honda", "disponible",
                          ["trompito"], True),
        crear_herramienta("MEZ-03", "Mezcladora pequeña", "Mezclado", "Honda", "disponible",
                          ["trompito"], True),
        crear_herramienta("VIB-01", "Vibrador de concreto", "Concreto", "Makita",
                          "requiere revisión", ["vibrador"], True,
                          observaciones="Tiene cinta en el cable (correo de Pamela Rodas)."),
        crear_herramienta("NIV-LAS-01", "Nivel láser", "Medición", "Bosch", "asignada",
                          ["nivel", "laser"], False, ubicacion="Z11-009",
                          responsable="Erick Santos", fecha_salida="2026-10-13 06:15",
                          devolucion_esperada="2026-10-13 17:00"),
        crear_herramienta("NIV-LAS-02", "Nivel láser", "Medición", "Bosch", "disponible",
                          ["nivel", "laser"], False),
        crear_herramienta("PUL-03", "Cortadora de block", "Corte", "Makita", "disponible",
                          ["cortadora de block", "pulidora grande", "la makita azul", "COR-01"],
                          True, observaciones="En la libreta azul aparece como COR-01 "
                                              "(alias heredado). No sale sin disco de repuesto."),
        crear_herramienta("EXT-01", "Extensión eléctrica 25 m", "Eléctrico", "Truper",
                          "disponible", ["extension", "extensión amarilla"], True),
        crear_herramienta("EXT-02", "Extensión eléctrica", "Eléctrico", "Truper",
                          "dada de baja", ["extensión naranja", "extension naranja"], True,
                          observaciones="Memorando 14/02/2026: no usar la extensión naranja."),
    ]


# Plan de demostración: código -> (ficha técnica, horas entre mantenimientos, horas ya usadas).
PLANES_DEMOSTRACION = {
    "COM-01": ("Ficha de demostración: cambio de aceite y filtro cada 400 horas.", 400, 0),
    "COM-02": ("Ficha de demostración: cambio de aceite y filtro cada 400 horas.", 400, 388),
    "ROT-01": ("Ficha de demostración: carbones y lubricación cada 300 horas.", 300, 120),
    "ROT-02": ("Ficha de demostración: carbones y lubricación cada 300 horas.", 300, 120),
    "ROT-03": ("Ficha de demostración: carbones y lubricación cada 300 horas.", 300, 10),
    "MEZ-01": ("Ficha de demostración: motor y transmisión cada 500 horas.", 500, 0),
    "MEZ-02": ("Ficha de demostración: motor y transmisión cada 250 horas.", 250, 230),
    "MEZ-03": ("Ficha de demostración: motor y transmisión cada 250 horas.", 250, 250),
    "VIB-01": ("Ficha de demostración: revisar eje y cable cada 200 horas.", 200, 60),
    "PUL-03": ("Ficha de demostración: escobillas y disco cada 300 horas.", 300, 40),
}


def obras_iniciales():
    """Obras de prueba del expediente. 'Bodega' es la ubicación de inicio."""
    return [
        {"codigo": "Bodega", "nombre": "Bodega-oficina San Cristóbal, Mixco", "activa": True,
         "es_bodega": True, "origen": ORIGEN_PRUEBA},
        {"codigo": "VN-014", "nombre": "Villa Nueva - banqueta ingreso sur", "activa": True,
         "es_bodega": False, "origen": ORIGEN_PRUEBA},
        {"codigo": "EUC-022", "nombre": "Casa Eucaliptos - muro lateral", "activa": True,
         "es_bodega": False, "origen": ORIGEN_PRUEBA},
        {"codigo": "Z11-009", "nombre": "Zona 11 - reparación de drenaje", "activa": True,
         "es_bodega": False, "origen": ORIGEN_PRUEBA},
        {"codigo": "CIS-005", "nombre": "Cisterna colegio (obra terminada)", "activa": False,
         "es_bodega": False, "origen": ORIGEN_PRUEBA},
    ]


def usuarios_iniciales():
    """Usuarios de demostración. Las contraseñas están en el README."""
    return [
        {"usuario": "jpivaral", "nombre": "Julián Pivaral", "rol": "bodega",
         "contrasena": cifrada_de_demostracion("jpivaral"), "obra": ""},
        {"usuario": "ecifuentes", "nombre": "Ing. Esteban Cifuentes", "rol": "residente",
         "contrasena": cifrada_de_demostracion("ecifuentes"), "obra": ""},
        {"usuario": "prodas", "nombre": "Ing. Pamela Rodas", "rol": "gerente",
         "contrasena": cifrada_de_demostracion("prodas"), "obra": ""},
        {"usuario": "esantos", "nombre": "Erick Santos", "rol": "maestro",
         "contrasena": cifrada_de_demostracion("esantos"), "obra": "EUC-022"},
    ]


def movimientos_iniciales():
    """Historial de prueba: reproduce el caso de COM-02 y las salidas vigentes."""
    return [
        {"id": 1, "tipo": "salida", "codigo": "COM-02", "obra_origen": "Bodega",
         "obra_destino": "Z11-009", "responsable": "Erick Santos", "registrado_por": "jpivaral",
         "fecha_hora": "2026-06-19 06:15", "fecha_registro": "2026-06-19 07:02",
         "devolucion_esperada": "2026-06-19 17:00",
         "observaciones": "Registrada tarde: con base en una foto desde la puerta."},
        {"id": 2, "tipo": "devolucion", "codigo": "COM-02", "obra_origen": "Z11-009",
         "obra_destino": "Bodega", "responsable": "Erick Santos", "registrado_por": "jpivaral",
         "fecha_hora": "2026-06-26 16:50", "fecha_registro": "2026-06-26 16:55",
         "devolucion_esperada": "",
         "observaciones": "Estado recibido: bueno. Ruido raro en el motor. Queda en revisión."},
        {"id": 3, "tipo": "salida", "codigo": "NIV-LAS-01", "obra_origen": "Bodega",
         "obra_destino": "Z11-009", "responsable": "Erick Santos", "registrado_por": "jpivaral",
         "fecha_hora": "2026-10-13 06:15", "fecha_registro": "2026-10-13 06:10",
         "devolucion_esperada": "2026-10-13 17:00", "observaciones": ""},
        {"id": 4, "tipo": "permanencia", "codigo": "NIV-LAS-01", "obra_origen": "Z11-009",
         "obra_destino": "Z11-009", "responsable": "Ing. Esteban Cifuentes",
         "registrado_por": "ecifuentes", "fecha_hora": "2026-10-13 16:00",
         "fecha_registro": "2026-10-13 16:00", "devolucion_esperada": "",
         "observaciones": "Autorización 1: del 13/10/2026 17:00 al 31/12/2026 17:00. "
                          "El sitio tiene garita."},
        {"id": 5, "tipo": "salida", "codigo": "ROT-02", "obra_origen": "Bodega",
         "obra_destino": "EUC-022", "responsable": "Erick Santos", "registrado_por": "jpivaral",
         "fecha_hora": "2026-10-14 06:15", "fecha_registro": "2026-10-14 06:05",
         "devolucion_esperada": "2026-10-14 17:00", "observaciones": ""},
        {"id": 6, "tipo": "salida", "codigo": "MEZ-01", "obra_origen": "Bodega",
         "obra_destino": "VN-014", "responsable": "Luis Aguilar", "registrado_por": "jpivaral",
         "fecha_hora": "2026-10-16 06:15", "fecha_registro": "2026-10-16 06:00",
         "devolucion_esperada": "2026-10-16 17:00", "observaciones": ""},
    ]


def danos_iniciales():
    """Daños de prueba registrados."""
    return [
        {"id": 1, "codigo": "COM-02", "descripcion": "Regresó con ruido raro en el motor.",
         "fecha": "2026-06-26 16:50", "responsable": "Julián Pivaral",
         "registrado_por": "jpivaral", "ubicacion": "Bodega"},
    ]


def autorizaciones_iniciales():
    """Autorizaciones de permanencia de prueba (NIV-LAS-01 queda en Z11-009)."""
    return [
        {"id": 1, "codigo": "NIV-LAS-01", "obra": "Z11-009", "fecha_inicio": "2026-10-13 17:00",
         "fecha_fin": "2026-12-31 17:00", "residente": "Ing. Esteban Cifuentes",
         "seguridad_confirmada": True, "registrado_por": "ecifuentes",
         "fecha_registro": "2026-10-13 16:00", "observaciones": "El sitio tiene garita."},
    ]


def herramientas_con_plan():
    """Catálogo de demostración con su ficha técnica y sus horas de uso."""
    herramientas = herramientas_iniciales()
    for herramienta in herramientas:
        ficha, intervalo, horas = PLANES_DEMOSTRACION.get(herramienta["codigo"], ("", 0, 0))
        herramienta["ficha_tecnica"] = ficha
        herramienta["ficha_archivo"] = ""
        herramienta["mantenimiento_cada_horas"] = intervalo
        herramienta["horas_uso"] = horas
        herramienta["ultimo_mantenimiento"] = ""
    return herramientas


def datos_iniciales():
    """Devuelve un diccionario nuevo con todas las colecciones de prueba."""
    return {
        "herramientas": herramientas_con_plan(),
        "obras": obras_iniciales(),
        "usuarios": usuarios_iniciales(),
        "movimientos": movimientos_iniciales(),
        "danos": danos_iniciales(),
        "autorizaciones": autorizaciones_iniciales(),
    }


def ruta_archivo(coleccion):
    """Ruta del archivo JSON de una colección."""
    return os.path.join(CARPETA_DATOS, coleccion + ".json")


def guardar_coleccion(coleccion, registros):
    """Escribe una colección en su archivo JSON."""
    os.makedirs(CARPETA_DATOS, exist_ok=True)
    temporal = ruta_archivo(coleccion) + ".tmp"
    with open(temporal, "w", encoding="utf-8") as archivo:
        json.dump(registros, archivo, ensure_ascii=False, indent=2)
    os.replace(temporal, ruta_archivo(coleccion))   # un corte a medias no daña el archivo


def cargar_datos():
    """Carga todas las colecciones. Devuelve (datos, avisos).

    Si un archivo falta o está corrupto, se recrea con los datos iniciales
    y se agrega un aviso a la lista.
    """
    datos = {}
    avisos = []
    for coleccion in COLECCIONES:
        try:
            with open(ruta_archivo(coleccion), "r", encoding="utf-8") as archivo:
                registros = json.load(archivo)
            if not isinstance(registros, list):
                raise ValueError("el archivo no contiene una lista")
            datos[coleccion] = registros
        except FileNotFoundError:
            datos[coleccion] = datos_iniciales()[coleccion]
            guardar_coleccion(coleccion, datos[coleccion])
            avisos.append("Aviso: no se encontró " + coleccion + ".json; "
                          "se creó con los datos iniciales de prueba.")
        except (json.JSONDecodeError, ValueError, UnicodeDecodeError):
            datos[coleccion] = datos_iniciales()[coleccion]
            guardar_coleccion(coleccion, datos[coleccion])
            avisos.append("Aviso: el archivo " + coleccion + ".json estaba dañado; "
                          "se recreó con los datos iniciales de prueba.")
    return datos, avisos


def guardar_datos(datos):
    """Guarda todas las colecciones en sus archivos JSON."""
    for coleccion in COLECCIONES:
        guardar_coleccion(coleccion, datos[coleccion])


def reiniciar_datos():
    """Sobrescribe los archivos JSON con los datos iniciales de prueba."""
    datos = datos_iniciales()
    guardar_datos(datos)
    return datos


def siguiente_id(registros):
    """Devuelve el siguiente id autoincremental de una lista de registros."""
    mayor = 0
    for registro in registros:
        if registro["id"] > mayor:
            mayor = registro["id"]
    return mayor + 1
