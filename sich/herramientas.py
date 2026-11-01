"""Módulo 1 - Catálogo de herramientas: registrar, asociar apodos y modificar.

Igual que en el Módulo 2, cada funcionalidad tiene validar_xxx, registrar_xxx y
proceso_xxx. La página web usa las mismas funciones validar_xxx y registrar_xxx.
"""

import os

from sich.autenticacion import MENSAJE_SIN_PERMISO, tiene_permiso
from sich.busqueda import normalizar, normalizar_codigo, seleccionar_herramienta
from sich.catalogo import descripcion_corta, obtener_herramienta
from sich.datos import CARPETA_DATOS, guardar_datos
from sich.movimientos import MENSAJE_CANCELADO, agregar_movimiento, herramienta_o_error, \
    intervalo_mantenimiento, momento_actual, mostrar_resumen
from sich.validaciones import confirmar, leer_entero, leer_opcion, leer_texto_no_vacio, \
    leer_texto_opcional, mostrar_titulo

# Una herramienta nueva nunca nace "asignada": eso solo lo hace Registrar salida.
ESTADOS_INICIALES = ["disponible", "requiere revisión", "dañada", "en reparación", "dada de baja"]
LETRAS_CODIGO = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-"
MINIMO_APODO = 2
MAXIMO_APODO = 40
MAXIMO_HORAS_MANTENIMIENTO = 100000
CARPETA_FICHAS = "fichas"
MAXIMO_BYTES_FICHA = 5 * 1024 * 1024


def error_en_codigo_nuevo(datos, codigo):
    """Revisa un código oficial nuevo. Devuelve el error o ''."""
    limpio = codigo.strip().upper()
    if len(limpio) < 3 or len(limpio) > 15:
        return "El código debe tener entre 3 y 15 caracteres (ej. ROT-04)."
    for letra in limpio:
        if letra not in LETRAS_CODIGO:
            return "El código solo puede tener letras sin tilde, números y guiones (ej. ROT-04)."
    for herramienta in datos["herramientas"]:
        if normalizar_codigo(herramienta["codigo"]) == normalizar_codigo(limpio):
            return "Ya existe una herramienta con el código " + herramienta["codigo"] + "."
        for apodo in herramienta["apodos"]:
            if normalizar_codigo(apodo) == normalizar_codigo(limpio):
                return ("El código " + limpio + " ya se usa como apodo de "
                        + herramienta["codigo"] + ".")
    return ""


def errores_en_datos_generales(nombre, categoria, marca):
    """Revisa los campos obligatorios de una herramienta. Devuelve la lista de errores."""
    errores = []
    if nombre.strip() == "":
        errores.append("Escriba el nombre de la herramienta.")
    if categoria.strip() == "":
        errores.append("Escriba la categoría (ej. Perforación).")
    if marca.strip() == "":
        errores.append("Escriba la marca (si no se conoce, escriba Sin marca).")
    return errores


def error_en_intervalo(horas):
    """Revisa las horas entre mantenimientos (0 = no aplica). Devuelve el error o ''."""
    if not isinstance(horas, int) or horas < 0 or horas > MAXIMO_HORAS_MANTENIMIENTO:
        return ("Las horas de mantenimiento deben ser un número entero entre 0 y "
                + str(MAXIMO_HORAS_MANTENIMIENTO) + " (0 = no aplica).")
    return ""


def separar_apodos(texto):
    """Convierte 'rana, bailarina' en la lista ['rana', 'bailarina'], sin vacíos."""
    apodos = []
    for apodo in texto.split(","):
        if apodo.strip() != "":
            apodos.append(" ".join(apodo.split()))
    return apodos


# ---------------------------------------------------- archivo de la ficha técnica

def tipo_de_archivo_ficha(contenido):
    """Reconoce el archivo por sus primeros bytes. Devuelve 'pdf', 'jpg', 'png' o ''."""
    if contenido.startswith(b"%PDF-"):
        return "pdf"
    if contenido.startswith(b"\xff\xd8\xff"):
        return "jpg"
    if contenido.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    return ""


def carpeta_fichas():
    """Carpeta donde se guardan los archivos, junto a los datos."""
    return os.path.join(CARPETA_DATOS, CARPETA_FICHAS)


def guardar_archivo_ficha(datos, usuario, codigo, contenido, ahora=None):
    """Guarda el PDF o la imagen de la ficha técnica. Devuelve (exito, mensaje)."""
    if not tiene_permiso(usuario, "1.3"):
        return False, MENSAJE_SIN_PERMISO
    herramienta = obtener_herramienta(datos, codigo)
    if herramienta is None:
        return False, "La herramienta '" + codigo + "' no existe en el catálogo."
    if len(contenido) == 0:
        return False, "Elija un archivo."
    if len(contenido) > MAXIMO_BYTES_FICHA:
        return False, "El archivo pesa más de 5 MB."
    tipo = tipo_de_archivo_ficha(contenido)
    if tipo == "":
        return False, "El archivo debe ser PDF, JPG o PNG."
    os.makedirs(carpeta_fichas(), exist_ok=True)
    anterior = herramienta.get("ficha_archivo", "")
    nombre = normalizar_codigo(herramienta["codigo"]) + "." + tipo
    with open(os.path.join(carpeta_fichas(), nombre), "wb") as archivo:
        archivo.write(contenido)
    if anterior != "" and anterior != nombre:
        try:
            os.remove(os.path.join(carpeta_fichas(), anterior))
        except OSError:
            pass
    herramienta["ficha_archivo"] = nombre
    agregar_movimiento(datos, "ficha", herramienta, herramienta["ubicacion"], herramienta["ubicacion"],
                       usuario["nombre"], usuario, momento_actual(ahora),
                       "Archivo de ficha técnica guardado.", ahora)
    return True, "Operación exitosa: ficha técnica de " + herramienta["codigo"] + " guardada."


# =====================================================================
# 1.1 Registrar herramienta
# =====================================================================

def validar_registro(datos, usuario, codigo, nombre, categoria, marca, estado, motor_o_cable,
                     ficha_tecnica="", mantenimiento_cada_horas=0):
    """Revisa los datos de una herramienta nueva. Devuelve la lista de errores."""
    if not tiene_permiso(usuario, "1.1"):
        return [MENSAJE_SIN_PERMISO]
    errores = []
    error_codigo = error_en_codigo_nuevo(datos, codigo)
    if error_codigo != "":
        errores.append(error_codigo)
    errores = errores + errores_en_datos_generales(nombre, categoria, marca)
    if estado not in ESTADOS_INICIALES:
        errores.append("Elija un estado de la lista. Una herramienta nueva no puede estar "
                       "asignada: para eso use Registrar salida.")
    if motor_o_cable not in [True, False]:
        errores.append("Indique si el equipo tiene motor o cable.")
    error_horas = error_en_intervalo(mantenimiento_cada_horas)
    if error_horas != "":
        errores.append(error_horas)
    return errores


def registrar_herramienta(datos, usuario, codigo, nombre, categoria, marca, estado,
                          motor_o_cable, ficha_tecnica="", mantenimiento_cada_horas=0,
                          observaciones="", ahora=None):
    """Agrega la herramienta al catálogo, en Bodega. Devuelve (exito, mensaje)."""
    errores = validar_registro(datos, usuario, codigo, nombre, categoria, marca, estado,
                               motor_o_cable, ficha_tecnica, mantenimiento_cada_horas)
    if len(errores) > 0:
        return False, " ".join(errores)
    herramienta = {
        "codigo": codigo.strip().upper(),
        "nombre": nombre.strip(),
        "categoria": categoria.strip(),
        "marca": marca.strip(),
        "estado": estado,
        "apodos": [],
        "motor_o_cable": motor_o_cable,
        "ubicacion": "Bodega",
        "responsable": "",
        "fecha_salida": "",
        "devolucion_esperada": "",
        "observaciones": observaciones.strip(),
        "ficha_tecnica": ficha_tecnica.strip(),
        "ficha_archivo": "",
        "mantenimiento_cada_horas": mantenimiento_cada_horas,
        "horas_uso": 0,
        "ultimo_mantenimiento": "",
        "origen": "Registrada en SICH por " + usuario["usuario"],
    }
    datos["herramientas"].append(herramienta)
    agregar_movimiento(datos, "registro", herramienta, "Bodega", "Bodega", usuario["nombre"],
                       usuario, momento_actual(ahora),
                       "Herramienta agregada al catálogo con estado " + estado + ".", ahora)
    plan = ""
    if mantenimiento_cada_horas > 0:
        plan = " Horas de uso: 0 de " + str(mantenimiento_cada_horas) + " h."
    return True, ("Operación exitosa: herramienta registrada. " + herramienta["codigo"] + " - "
                  + herramienta["nombre"] + " está en Bodega con estado '" + estado
                  + "'." + plan + " Puede asociarle apodos en 1.2.")


def pedir_motor_o_cable():
    """Pregunta si el equipo tiene motor o cable. Devuelve True o False."""
    return confirmar("¿Tiene motor o cable eléctrico?")


def proceso_registrar_herramienta(datos, usuario):
    """Opción 1.1 en consola."""
    mostrar_titulo("1.1 REGISTRAR HERRAMIENTA")
    while True:
        codigo = leer_texto_no_vacio("Código oficial (ej. ROT-04) o 0 para cancelar: ")
        if codigo == "0":
            print(MENSAJE_CANCELADO)
            return
        error = error_en_codigo_nuevo(datos, codigo)
        if error == "":
            break
        print(error)
    nombre = leer_texto_no_vacio("Nombre (ej. Rotomartillo): ")
    categoria = leer_texto_no_vacio("Categoría (ej. Perforación): ")
    marca = leer_texto_no_vacio("Marca (si no se conoce, escriba Sin marca): ")
    print("Estado inicial:")
    numero = 1
    validas = []
    for estado in ESTADOS_INICIALES:
        print(" ", str(numero) + ".", estado)
        validas.append(str(numero))
        numero = numero + 1
    estado = ESTADOS_INICIALES[int(leer_opcion("Elija el estado: ", validas)) - 1]
    motor_o_cable = pedir_motor_o_cable()
    ficha_tecnica = leer_texto_opcional("Ficha técnica: resumen o referencia (Enter para omitir): ")
    horas = leer_entero("Horas entre mantenimientos según la ficha (0 = no aplica): ", 0,
                        MAXIMO_HORAS_MANTENIMIENTO)
    observaciones = leer_texto_opcional("Observaciones (opcional, Enter para omitir): ")
    mostrar_resumen([("Código", codigo.strip().upper()), ("Nombre", nombre),
                     ("Categoría", categoria), ("Marca", marca), ("Estado", estado),
                     ("Motor o cable", "Sí" if motor_o_cable else "No"),
                     ("Ficha técnica", ficha_tecnica or "-"),
                     ("Mantenimiento", "cada " + str(horas) + " h" if horas > 0 else "no aplica"),
                     ("Ubicación", "Bodega")])
    if not confirmar("¿Confirmar operación?"):
        print(MENSAJE_CANCELADO)
        return
    exito, mensaje = registrar_herramienta(datos, usuario, codigo, nombre, categoria, marca,
                                           estado, motor_o_cable, ficha_tecnica, horas,
                                           observaciones)
    print("\n" + mensaje)
    if exito:
        guardar_datos(datos)


# =====================================================================
# 1.2 Asociar nombres alternativos
# =====================================================================

def validar_apodos(datos, usuario, codigo, texto_apodos):
    """Revisa apodos separados por coma. Devuelve la lista de errores."""
    if not tiene_permiso(usuario, "1.2"):
        return [MENSAJE_SIN_PERMISO]
    errores = []
    herramienta = herramienta_o_error(datos, codigo, errores)
    if herramienta is None:
        return errores
    apodos = separar_apodos(texto_apodos)
    if len(apodos) == 0:
        return ["Escriba al menos un apodo. Si son varios, sepárelos con comas."]
    vistos = [normalizar(apodo) for apodo in herramienta["apodos"]]
    for apodo in apodos:
        if len(apodo) < MINIMO_APODO or len(apodo) > MAXIMO_APODO:
            errores.append("El apodo '" + apodo + "' debe tener entre " + str(MINIMO_APODO)
                           + " y " + str(MAXIMO_APODO) + " caracteres.")
        elif normalizar(apodo) in vistos:
            errores.append(herramienta["codigo"] + " ya tiene el apodo '" + apodo + "'.")
        else:
            otra = obtener_herramienta(datos, apodo)
            if otra is not None:
                errores.append("'" + apodo + "' es el código oficial de otra herramienta.")
        vistos.append(normalizar(apodo))
    return errores


def herramientas_con_apodo(datos, apodo, codigo_propio):
    """Códigos de OTRAS herramientas que ya usan ese apodo."""
    codigos = []
    for herramienta in datos["herramientas"]:
        if herramienta["codigo"] != codigo_propio:
            for existente in herramienta["apodos"]:
                if normalizar(existente) == normalizar(apodo):
                    codigos.append(herramienta["codigo"])
    return codigos


def registrar_apodos(datos, usuario, codigo, texto_apodos, ahora=None):
    """Liga los apodos al código oficial. Avisa si alguno queda ambiguo. Devuelve (exito, mensaje)."""
    errores = validar_apodos(datos, usuario, codigo, texto_apodos)
    if len(errores) > 0:
        return False, " ".join(errores)
    herramienta = obtener_herramienta(datos, codigo)
    apodos = separar_apodos(texto_apodos)
    avisos = ""
    for apodo in apodos:
        otras = herramientas_con_apodo(datos, apodo, herramienta["codigo"])
        if len(otras) > 0:
            avisos = (avisos + " Aviso: '" + apodo + "' también es apodo de " + ", ".join(otras)
                      + "; al buscarlo, SICH pedirá elegir.")
        herramienta["apodos"].append(apodo)
    agregar_movimiento(datos, "apodos", herramienta, herramienta["ubicacion"],
                       herramienta["ubicacion"], usuario["nombre"], usuario,
                       momento_actual(ahora), "Apodos agregados: " + ", ".join(apodos) + ".", ahora)
    return True, ("Operación exitosa: apodos asociados a " + herramienta["codigo"] + ". Ahora se "
                  "encuentra también como: " + ", ".join(herramienta["apodos"]) + "." + avisos)


def proceso_asociar_apodos(datos, usuario):
    """Opción 1.2 en consola."""
    mostrar_titulo("1.2 ASOCIAR APODOS")
    herramienta = seleccionar_herramienta(datos)
    if herramienta is None:
        print(MENSAJE_CANCELADO)
        return
    print("Apodos actuales:", ", ".join(herramienta["apodos"]) or "ninguno")
    while True:
        texto = leer_texto_no_vacio("Apodos nuevos, separados por coma (0 = cancelar): ")
        if texto == "0":
            print(MENSAJE_CANCELADO)
            return
        errores = validar_apodos(datos, usuario, herramienta["codigo"], texto)
        if len(errores) == 0:
            break
        print(" ".join(errores))
    mostrar_resumen([("Herramienta", descripcion_corta(herramienta)),
                     ("Apodos nuevos", ", ".join(separar_apodos(texto)))])
    if not confirmar("¿Confirmar operación?"):
        print(MENSAJE_CANCELADO)
        return
    exito, mensaje = registrar_apodos(datos, usuario, herramienta["codigo"], texto)
    print("\n" + mensaje)
    if exito:
        guardar_datos(datos)


# =====================================================================
# 1.3 Modificar herramienta
# =====================================================================

def estados_permitidos_al_modificar(herramienta):
    """Estados a los que se puede pasar desde aquí (además de conservar el actual).

    Los demás cambios tienen su propio proceso con reglas: salida, devolución, daño y revisión.
    """
    if herramienta["estado"] == "dada de baja":
        return ["requiere revisión"]   # volver a usarla exige revisarla antes
    if herramienta["ubicacion"] == "Bodega":
        return ["dada de baja"]
    return []


def validar_modificacion(datos, usuario, codigo, nombre, categoria, marca, motor_o_cable,
                         observaciones, estado, ficha_tecnica, mantenimiento_cada_horas):
    """Revisa los datos nuevos. Devuelve la lista de errores."""
    if not tiene_permiso(usuario, "1.3"):
        return [MENSAJE_SIN_PERMISO]
    errores = []
    herramienta = herramienta_o_error(datos, codigo, errores)
    if herramienta is None:
        return errores
    errores = errores + errores_en_datos_generales(nombre, categoria, marca)
    error_horas = error_en_intervalo(mantenimiento_cada_horas)
    if error_horas != "":
        errores.append(error_horas)
    if estado != herramienta["estado"] and estado not in estados_permitidos_al_modificar(herramienta):
        errores.append("Desde aquí " + herramienta["codigo"] + " no puede pasar de '"
                       + herramienta["estado"] + "' a '" + estado + "'. Use el movimiento "
                       "correspondiente (salida, devolución, daño o revisión).")
    if len(errores) == 0 and len(cambios_de_herramienta(herramienta, nombre, categoria, marca,
                                                        motor_o_cable, observaciones, estado,
                                                        ficha_tecnica,
                                                        mantenimiento_cada_horas)) == 0:
        errores.append("No cambió ningún dato.")
    return errores


def cambios_de_herramienta(herramienta, nombre, categoria, marca, motor_o_cable, observaciones,
                           estado, ficha_tecnica, mantenimiento_cada_horas):
    """Lista de textos 'campo: antes -> ahora' con lo que cambiaría."""
    nuevos = [("nombre", nombre.strip()), ("categoria", categoria.strip()),
              ("marca", marca.strip()), ("motor_o_cable", motor_o_cable),
              ("observaciones", observaciones.strip()), ("estado", estado),
              ("ficha_tecnica", ficha_tecnica.strip()),
              ("mantenimiento_cada_horas", mantenimiento_cada_horas)]
    cambios = []
    for campo, valor in nuevos:
        actual = herramienta.get(campo, 0 if campo == "mantenimiento_cada_horas" else "")
        if actual != valor:
            cambios.append(campo + ": " + str(actual) + " -> " + str(valor))
    return cambios


def registrar_modificacion(datos, usuario, codigo, nombre, categoria, marca, motor_o_cable,
                           observaciones, estado, ficha_tecnica, mantenimiento_cada_horas,
                           ahora=None):
    """Actualiza la herramienta y deja constancia en el historial. Devuelve (exito, mensaje)."""
    errores = validar_modificacion(datos, usuario, codigo, nombre, categoria, marca,
                                   motor_o_cable, observaciones, estado, ficha_tecnica,
                                   mantenimiento_cada_horas)
    if len(errores) > 0:
        return False, " ".join(errores)
    herramienta = obtener_herramienta(datos, codigo)
    cambios = cambios_de_herramienta(herramienta, nombre, categoria, marca, motor_o_cable,
                                     observaciones, estado, ficha_tecnica,
                                     mantenimiento_cada_horas)
    herramienta["nombre"] = nombre.strip()
    herramienta["categoria"] = categoria.strip()
    herramienta["marca"] = marca.strip()
    herramienta["motor_o_cable"] = motor_o_cable
    herramienta["observaciones"] = observaciones.strip()
    herramienta["estado"] = estado
    herramienta["ficha_tecnica"] = ficha_tecnica.strip()
    herramienta["mantenimiento_cada_horas"] = mantenimiento_cada_horas
    agregar_movimiento(datos, "modificacion", herramienta, herramienta["ubicacion"],
                       herramienta["ubicacion"], usuario["nombre"], usuario,
                       momento_actual(ahora), "; ".join(cambios), ahora)
    return True, ("Operación exitosa: " + herramienta["codigo"] + " actualizada. Cambios: "
                  + "; ".join(cambios) + ".")


def leer_con_valor_actual(etiqueta, actual):
    """Pide un dato; Enter conserva el valor actual."""
    texto = leer_texto_opcional(etiqueta + " [Enter = " + (actual or "sin dato") + "]: ")
    if texto == "":
        return actual
    return texto


def pedir_estado_al_modificar(herramienta):
    """Ofrece conservar el estado o los cambios permitidos. Devuelve el estado elegido."""
    permitidos = estados_permitidos_al_modificar(herramienta)
    if len(permitidos) == 0:
        return herramienta["estado"]
    print("Estado:  1. Conservar '" + herramienta["estado"] + "'")
    validas = ["1"]
    numero = 2
    for estado in permitidos:
        print("         " + str(numero) + ". Cambiar a '" + estado + "'")
        validas.append(str(numero))
        numero = numero + 1
    eleccion = int(leer_opcion("Elija el estado: ", validas))
    if eleccion == 1:
        return herramienta["estado"]
    return permitidos[eleccion - 2]


def proceso_modificar_herramienta(datos, usuario):
    """Opción 1.3 en consola."""
    mostrar_titulo("1.3 MODIFICAR HERRAMIENTA")
    herramienta = seleccionar_herramienta(datos)
    if herramienta is None:
        print(MENSAJE_CANCELADO)
        return
    print("El código oficial no se cambia porque identifica todo el historial.")
    nombre = leer_con_valor_actual("Nombre", herramienta["nombre"])
    categoria = leer_con_valor_actual("Categoría", herramienta["categoria"])
    marca = leer_con_valor_actual("Marca", herramienta["marca"])
    print("Motor o cable: actualmente", "Sí" if herramienta["motor_o_cable"] else "No")
    motor_o_cable = pedir_motor_o_cable()
    ficha_tecnica = leer_con_valor_actual("Ficha técnica", herramienta.get("ficha_tecnica", ""))
    actual = intervalo_mantenimiento(herramienta)
    horas = leer_entero("Horas entre mantenimientos, 0 = no aplica [Enter = " + str(actual) + "]: ",
                        0, MAXIMO_HORAS_MANTENIMIENTO, actual)
    observaciones = leer_con_valor_actual("Observaciones", herramienta["observaciones"])
    estado = pedir_estado_al_modificar(herramienta)
    errores = validar_modificacion(datos, usuario, herramienta["codigo"], nombre, categoria, marca,
                                   motor_o_cable, observaciones, estado, ficha_tecnica, horas)
    if len(errores) > 0:
        print(" ".join(errores))
        return
    cambios = cambios_de_herramienta(herramienta, nombre, categoria, marca, motor_o_cable,
                                     observaciones, estado, ficha_tecnica, horas)
    mostrar_resumen([("Herramienta", descripcion_corta(herramienta)),
                     ("Cambios", "; ".join(cambios))])
    if not confirmar("¿Confirmar operación?"):
        print(MENSAJE_CANCELADO)
        return
    exito, mensaje = registrar_modificacion(datos, usuario, herramienta["codigo"], nombre, categoria,
                                            marca, motor_o_cable, observaciones, estado,
                                            ficha_tecnica, horas)
    print("\n" + mensaje)
    if exito:
        guardar_datos(datos)
