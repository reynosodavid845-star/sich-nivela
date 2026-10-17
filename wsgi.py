"""Punto de entrada para servidores de internet (PythonAnywhere, Render, etc.).

El servidor busca una variable llamada "application". Ver PUBLICAR.md.
"""

import os
import sys

CARPETA = os.path.dirname(os.path.abspath(__file__))
if CARPETA not in sys.path:
    sys.path.insert(0, CARPETA)

os.environ.setdefault("SICH_PUBLICO", "1")   # cookies solo por HTTPS y contraseñas de prueba bloqueadas

from app import app as application  # noqa: E402
