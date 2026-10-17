"""Carga y guardado de los datos de SICH en archivos JSON.

Los datos se guardan en la carpeta datos/. Si un archivo falta o está
dañado (JSON corrupto), se vuelve a crear con los datos iniciales de prueba
y se avisa al usuario.
"""

import hashlib
import json
import os

CARPETA_PROYECTO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# La variable de entorno SICH_DATOS permite usar otra carpeta (la usa pruebas.py
# para no modificar los datos reales).
CARPETA_DATOS = os.environ.get("SICH_DATOS", os.path.join(CARPETA_PROYECTO, "datos"))

COLECCIONES = ["herramientas", "obras", "usuarios", "movimientos", "danos", "autorizaciones"]

FORMATO_FECHA = "%Y-%m-%d %H:%M"   # formato en que se guardan las fechas en JSON

ORIGEN_PRUEBA = "Dato de prueba precargado (el Módulo 1 - Catálogo está pendiente)"


def cifrar_contrasena(contrasena):
    """Devuelve el hash SHA-256 de una contraseña (no se guarda en texto plano)."""
    return hashlib.sha256(contrasena.encode("utf-8")).hexdigest()


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
    """Usuarios de prueba. Las contraseñas de prueba están en el README."""
    return [
        {"usuario": "jpivaral", "nombre": "Julián Pivaral", "rol": "bodega",
         "contrasena": cifrar_contrasena("bodega123"), "obra": ""},
        {"usuario": "ecifuentes", "nombre": "Ing. Esteban Cifuentes", "rol": "residente",
         "contrasena": cifrar_contrasena("residente123"), "obra": ""},
        {"usuario": "prodas", "nombre": "Ing. Pamela Rodas", "rol": "gerente",
         "contrasena": cifrar_contrasena("gerente123"), "obra": ""},
        {"usuario": "esantos", "nombre": "Erick Santos", "rol": "maestro",
         "contrasena": cifrar_contrasena("maestro123"), "obra": "EUC-022"},
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


def datos_iniciales():
    """Devuelve un diccionario nuevo con todas las colecciones de prueba."""
    return {
        "herramientas": herramientas_iniciales(),
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
    with open(ruta_archivo(coleccion), "w", encoding="utf-8") as archivo:
        json.dump(registros, archivo, ensure_ascii=False, indent=2)


def cargar_datos():
    """Carga todas las colecciones. Devuelve (datos, avisos).

    Si un archivo falta o está corrupto, se recrea con los datos iniciales
    y se agrega un aviso a la lista.
    """
    datos = {}
    avisos = []
    iniciales = datos_iniciales()
    for coleccion in COLECCIONES:
        try:
            with open(ruta_archivo(coleccion), "r", encoding="utf-8") as archivo:
                registros = json.load(archivo)
            if not isinstance(registros, list):
                raise ValueError("el archivo no contiene una lista")
            datos[coleccion] = registros
        except FileNotFoundError:
            datos[coleccion] = iniciales[coleccion]
            guardar_coleccion(coleccion, datos[coleccion])
            avisos.append("Aviso: no se encontró " + coleccion + ".json; "
                          "se creó con los datos iniciales de prueba.")
        except (json.JSONDecodeError, ValueError, UnicodeDecodeError):
            datos[coleccion] = iniciales[coleccion]
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
