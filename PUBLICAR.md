# Publicar SICH en internet e instalarlo en celulares y tablets

SICH es una **app web instalable (PWA)**: se publica una sola vez en internet y cada persona la
instala desde el navegador de su teléfono o tablet, sin tienda de aplicaciones. Para instalarla
hace falta HTTPS, y el hosting recomendado lo incluye.

## Opción A: GitHub + Render (gratis, se publica directo desde Git)

El código vive en GitHub y Render lo publica solo cada vez que se hace `git push`.
La dirección queda así: `https://sich-nivela.onrender.com` (o parecida).

**Advertencia:** en el plan gratuito de Render, los archivos vuelven a los datos de prueba cada
vez que el servicio se reinicia o se vuelve a publicar, y se "duerme" tras 15 minutos sin uso
(la primera visita tarda cerca de un minuto en despertar). Sirve para demostrar la app; para
conservar los movimientos registrados de forma permanente use la opción B (PythonAnywhere).

1. **Subir el código a GitHub.** Cree un repositorio vacío (sin README) en https://github.com/new
   y, en esta carpeta, ejecute:

   ```bash
   git remote add origin https://github.com/SU-USUARIO/sich-nivela.git
   git push -u origin main
   ```

   Windows abrirá una ventana para iniciar sesión en GitHub la primera vez.
2. **Crear el servicio en Render.** Entre a https://dashboard.render.com con **GitHub**, elija
   **New → Blueprint** y seleccione el repositorio. Render lee `render.yaml` y prepara todo.
3. **Escribir las contraseñas reales.** Render pedirá `SICH_CONTRASENA_JPIVARAL`,
   `SICH_CONTRASENA_ECIFUENTES`, `SICH_CONTRASENA_PRODAS` y `SICH_CONTRASENA_ESANTOS`. Escriba
   una contraseña distinta, de 8 caracteres o más, para cada usuario. Quedan guardadas como
   secretos en Render (no en GitHub), y SICH las vuelve a aplicar cada vez que arranca.
4. Presione **Apply**, espere a que diga **Live** y abra la dirección que muestra Render.
5. Para actualizar la app más adelante basta con `git commit` y `git push`.

## Opción B: PythonAnywhere (gratis, conserva los datos)

Se recomienda porque es gratis, no pide tarjeta, ya trae Flask, da HTTPS y **guarda los archivos
JSON de forma permanente**. Otros hosting gratuitos borran los archivos cada vez que se reinician,
y ahí se perderían los movimientos registrados.

La dirección queda así: `https://SU-USUARIO.pythonanywhere.com`

### 1. Crear la cuenta

1. Entre a https://www.pythonanywhere.com y elija **Pricing & signup → Create a Beginner account**.
2. El nombre de usuario será parte de la dirección (por ejemplo `sichnivela`).

### 2. Subir el proyecto

1. En la pestaña **Files**, suba `Fase3_Grupo10_Expediente-001.zip` con **Upload a file**.
2. Abra **Consoles → Bash** y escriba:

```bash
unzip Fase3_Grupo10_Expediente-001.zip
cd Fase3_Grupo10_Expediente-001
python3 pruebas.py
```

Debe terminar con `34 de 34 casos satisfactorios`.

### 3. Cambiar las contraseñas de prueba (obligatorio)

Las contraseñas de prueba (`bodega123`, etc.) están escritas en el README, así que **la versión
publicada las rechaza**. Hay que poner contraseñas nuevas, de 8 caracteres o más, a cada usuario:

```bash
python3 cambiar_contrasena.py jpivaral
python3 cambiar_contrasena.py ecifuentes
python3 cambiar_contrasena.py prodas
python3 cambiar_contrasena.py esantos
```

Entregue cada contraseña solo a su dueño.

### 4. Crear la aplicación web

1. Pestaña **Web → Add a new web app → Next → Manual configuration → Python 3.10** (o la más nueva).
2. En la sección **Code**, abra el archivo **WSGI configuration file**, borre todo su contenido y
   pegue esto, cambiando `SU-USUARIO` y la clave:

```python
import os
import sys

sys.path.insert(0, "/home/SU-USUARIO/Fase3_Grupo10_Expediente-001")
os.environ["SICH_CLAVE"] = "escriba-aqui-un-texto-largo-y-al-azar-de-40-letras"

from wsgi import application
```

3. En **Static files** agregue: URL `/static/` y Directory
   `/home/SU-USUARIO/Fase3_Grupo10_Expediente-001/static`.
4. En **Security** active **Force HTTPS**.
5. Presione el botón verde **Reload**.
6. Abra `https://SU-USUARIO.pythonanywhere.com` y entre con un usuario y su contraseña nueva.

> La cuenta gratuita pide entrar cada 3 meses y presionar **Run until 3 months from today** en
> la pestaña Web para que la app siga en línea.

### 5. Instalar en cada teléfono o tablet

Abra la dirección en el teléfono y entre a **¿Cómo instalar SICH en el teléfono?** (al pie de cada
página) o directamente a `/instalar`:

- **Android (Chrome):** botón **Instalar SICH ahora**, o menú ⋮ → **Instalar app**.
- **iPhone / iPad (Safari):** **Compartir → Agregar a inicio**.
- **Computadora (Chrome / Edge):** ícono de instalar en la barra de direcciones.

## Probar en el celular sin publicar (misma red Wi-Fi)

```bash
py app.py --red
```

En el celular abra `http://IP-DE-LA-COMPUTADORA:5000`. Para ver la IP en Windows use `ipconfig`
(*Dirección IPv4*). Windows puede pedir permiso en el firewall. Así se puede usar y probar el
diseño, pero **el botón de instalar no aparece** sin HTTPS; para instalarla hay que publicarla.

## Seguridad de la versión publicada

| Medida | Qué hace |
|---|---|
| `SICH_PUBLICO=1` (lo pone `wsgi.py`) | La cookie de sesión solo viaja por HTTPS y se rechazan las contraseñas de prueba |
| `SICH_CLAVE` | Clave secreta de las sesiones; si no se define, se crea una al azar en cada arranque |
| 3 intentos por dirección IP | Luego hay que esperar 5 minutos, aunque se borren las cookies |
| Token en cada formulario | Evita que otra página envíe formularios en nombre del usuario |
| Contraseñas cifradas (SHA-256) | `usuarios.json` no guarda las contraseñas en texto |
| Sesión de 12 horas | Un turno de trabajo; después hay que volver a entrar |

**Respaldos:** los datos están en la carpeta `datos/`. Descárguela de vez en cuando desde la
pestaña **Files** de PythonAnywhere.
