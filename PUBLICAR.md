# Publicar SICH en internet e instalarlo en celulares y tablets

SICH es una **app web instalable (PWA)**: se publica una vez y cada persona la instala desde el
navegador de su teléfono o tablet, sin tienda de aplicaciones. Instalarla requiere HTTPS.

## Opción recomendada: PythonAnywhere (gratis, conserva los datos)

Es gratis, no pide tarjeta, ya trae Flask, da HTTPS y **guarda los archivos JSON de forma
permanente**. La dirección queda así: `https://SU-USUARIO.pythonanywhere.com`

### 1. Bajar el código

Cree una cuenta **Beginner** en https://www.pythonanywhere.com, confirme su correo y abra
**Consoles → Bash**:

```bash
git clone https://github.com/reynosodavid845-star/sich-nivela.git
cd sich-nivela
python3 pruebas.py | tail -1
```

Debe terminar con `56 de 56 casos satisfactorios`.

### 2. Crear la aplicación web

1. Pestaña **Web → Add a new web app → Next → Manual configuration → Python 3.13**.
2. En **Code**, abra el **WSGI configuration file**, borre su contenido y pegue esto, cambiando
   `SU-USUARIO` y la clave:

```python
import os
import sys

sys.path.insert(0, "/home/SU-USUARIO/sich-nivela")
os.environ["SICH_DATOS"] = "/home/SU-USUARIO/sich-datos"
os.environ["SICH_CLAVE"] = "escriba-aqui-un-texto-largo-y-al-azar-de-40-letras"

from wsgi import application
```

Los datos quedan fuera del repositorio (`sich-datos`), así actualizar el código no los toca.

3. En **Static files** agregue la URL `/static/` y el directorio
   `/home/SU-USUARIO/sich-nivela/static`.
4. En **Security** active **Force HTTPS** y presione el botón verde **Reload**.

> La cuenta gratuita pide entrar una vez al mes y presionar **Run until 1 month from today**
> en la pestaña Web para que la app siga en línea. PythonAnywhere avisa por correo una semana antes.

### 3. Crear la cuenta de propietario

Las contraseñas de demostración no funcionan en la versión publicada.

1. Abra el sitio y toque **Configúrela aquí**.
2. El código está en la pestaña **Files**: `sich-datos/codigo_configuracion.txt`.
3. Cree su cuenta; ese código deja de servir y esa página se cierra.
4. Desde **Administrar cuentas**, restablezca las contraseñas de los usuarios o cree cuentas nuevas.

### 4. Actualizar a una versión nueva

En **Consoles → Bash**:

```bash
cd ~/sich-nivela
git pull
touch /var/www/su-usuario_pythonanywhere_com_wsgi.py
```

**Respaldos:** descargue de vez en cuando `sich-datos` desde la pestaña **Files**.

## Opción alterna: Render (se publica desde GitHub, pero borra los datos)

En el plan gratuito, los archivos vuelven a los datos de demostración cada vez que el servicio se
reinicia, y se duerme tras 15 minutos sin uso. Sirve solo para mostrar la app.

Entre a https://dashboard.render.com, elija **New → Blueprint** y seleccione el repositorio.
Render lee `render.yaml` y pide las contraseñas `SICH_CONTRASENA_...`, que se guardan como secretos.

## Instalar en cada teléfono o tablet

Abra la dirección en el teléfono y toque **¿Cómo instalar SICH en el teléfono?**, al pie de la página:

- **Android (Chrome):** botón **Instalar SICH ahora**, o menú ⋮ → **Instalar app**.
- **iPhone / iPad (Safari):** **Compartir → Agregar a inicio**.
- **Computadora (Chrome / Edge):** ícono de instalar en la barra de direcciones.

## Seguridad de la versión publicada

| Medida | Qué hace |
|---|---|
| `SICH_PUBLICO=1` (lo pone `wsgi.py`) | La cookie de sesión solo viaja por HTTPS y se rechazan las contraseñas de demostración |
| `SICH_CLAVE` | Clave secreta de las sesiones; si no se define, se crea una al azar en cada arranque |
| Inicio de sesión sin límite de intentos | Nadie queda bloqueado; por eso cada cuenta necesita una contraseña larga y difícil |
| 3 intentos del código de configuración | Luego hay que esperar 5 minutos, aunque se borren las cookies |
| Token en cada formulario | Evita que otra página envíe formularios en nombre del usuario |
| PBKDF2-SHA256 con sal | `usuarios.json` guarda una huella que no se puede revertir, distinta para cada contraseña |
| Sesión de 12 horas | Un turno de trabajo; después hay que volver a entrar |
