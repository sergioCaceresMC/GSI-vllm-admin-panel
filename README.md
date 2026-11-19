# vLLM Admin

[English](README.en.md)

Panel web FastAPI para administrar un servidor de inferencia vLLM en Linux. Permite iniciar, detener y reiniciar el motor, consultar su disponibilidad, supervisar recursos, guardar parámetros y gestionar el arranque automático con systemd.

## Índice

- [Ejecutar el panel](#ejecutar-el-panel)
- [Modo de uso](#modo-de-uso)
  - [Acceder desde otro dispositivo de la misma red](#acceder-desde-otro-dispositivo-de-la-misma-red)
  - [Acceder a la API de vLLM desde la oficina](#acceder-a-la-api-de-vllm-desde-la-oficina)
  - [Acceso directo al panel desde el teléfono](#acceso-directo-al-panel-desde-el-teléfono)
  - [Restringir el acceso con UFW](#restringir-el-acceso-con-ufw)
- [Despliegue en Linux con systemd](#despliegue-en-linux-con-systemd)
  - [Cuentas y permisos](#cuentas-y-permisos)
  - [Instalación del motor vLLM](#instalación-del-motor-vllm)
  - [Unidades de systemd](#unidades-de-systemd)
  - [Permisos de operación y escritura](#permisos-de-operación-y-escritura)
  - [Llamadas automáticas a herramientas](#llamadas-automáticas-a-herramientas)
  - [Cambiar el puerto de inferencia](#cambiar-el-puerto-de-inferencia)
  - [Arranque y verificación](#arranque-y-verificación)
- [Verificar](#verificar)

## Ejecutar el panel

Necesitas Python 3.10 o posterior y [uv](https://docs.astral.sh/uv/). Desde la raíz del repositorio:

```sh
uv sync --locked
uv run uvicorn main:app --host 127.0.0.1 --port 8080
```

Abre el panel en `http://127.0.0.1:8080`. El panel carece de autenticación. Mantén la escucha en loopback.

## Modo de uso

En la máquina que ejecuta el panel, abre `http://127.0.0.1:8080`. Usa **Iniciar** para arrancar vLLM y espera a que el panel muestre **Modelo disponible**. Para guardar cambios y aplicarlos en el acto, usa **Guardar y reiniciar**.

### Acceder desde otro dispositivo de la misma red

1. En el servidor Linux, lista las direcciones IPv4 de sus interfaces.

   ```sh
   ip -br -4 address show up
   ```

   Elige la dirección de la interfaz Ethernet o Wi‑Fi conectada a la misma red que el otro dispositivo. Si aparece `192.168.1.42/24`, usa `192.168.1.42`. Omite `lo`, las interfaces VPN o de contenedores y el sufijo de red.
2. Con el servidor SSH habilitado, ejecuta esto en el dispositivo desde el que quieres acceder. Sustituye `usuario` por tu cuenta de acceso SSH y la IP por la del servidor.

   ```sh
   ssh -N -L 127.0.0.1:18080:127.0.0.1:8080 usuario@192.168.1.42
   ```

3. Deja abierta la conexión SSH y abre `http://127.0.0.1:18080` en el navegador de ese dispositivo. En un móvil, usa un cliente SSH con reenvío de puertos locales y configura el puerto local `18080` y el destino remoto `127.0.0.1:8080`.

Si el túnel no conecta, comprueba que SSH acepta conexiones desde la red local y que ambos dispositivos pueden comunicarse. Algunas redes de invitados aíslan los dispositivos. Mantén el puerto `8080` del panel en loopback, ya que el panel carece de autenticación.

### Acceder a la API de vLLM desde la oficina

Los ejemplos usan `203.0.113.182` y `203.0.113.128/25`, direcciones reservadas para documentación. Sustitúyelas por la IP del servidor y la subred autorizada que indique el administrador de la red. [RFC 5737](https://www.rfc-editor.org/info/rfc5737/)

Si el motor está configurado con `VLLM_HOST=0.0.0.0`, escucha en todas las interfaces IPv4. Desde otro ordenador de la oficina, comprueba que puedes alcanzar la API.

```sh
curl -i http://203.0.113.182:8000/health
```

Si devuelve `200 OK`, configura el cliente compatible con OpenAI con la URL base `http://203.0.113.182:8000/v1`.

### Acceso directo al panel desde el teléfono

Usa el túnel SSH mientras el panel carezca de autenticación. Cualquier dispositivo que alcance el puerto del panel podría controlar vLLM. Para habilitar acceso directo únicamente después de incorporar protección de acceso, edita la unidad con `sudo nano /etc/systemd/system/vllm-admin.service` y cambia `--host 127.0.0.1` por la IP asignada al servidor.

```ini
ExecStart=/opt/vllm-admin/.venv/bin/uvicorn main:app --host 203.0.113.182 --port 8080
```

```sh
sudo systemctl daemon-reload
sudo systemctl restart vllm-admin.service
```

Después de recargar y reiniciar el servicio, abre `http://203.0.113.182:8080` desde el teléfono conectado a la red autorizada.

### Restringir el acceso con UFW

Si usas UFW, revisa primero que esté activo y comprueba las reglas existentes.

```sh
sudo ufw status numbered
```

Para permitir el acceso a la API desde la subred de la oficina, añade la regla del puerto 8000. Tras proteger el panel, puedes añadir la regla del puerto 8080.

```sh
sudo ufw allow from 203.0.113.128/25 to any port 8000 proto tcp
```

```sh
sudo ufw allow from 203.0.113.128/25 to any port 8080 proto tcp
```

Estas reglas añaden permisos. Revisa las reglas más amplias y la política de entrada antes de considerar restringido el acceso. Si la IP de tu servidor es pública, limita el acceso en el firewall aunque esté asignada dentro de la oficina.

## Despliegue en Linux con systemd

El ejemplo usa una instalación nueva en `/opt/vllm-admin`, Python del sistema 3.10 o posterior y una instalación de `uv` de confianza disponible en el `PATH` de `sudo`. Si cambias el directorio del proyecto, actualiza ambas unidades de systemd.

### Cuentas y permisos

Crea dos cuentas de sistema sin acceso interactivo. `vllm-engine` ejecuta la inferencia y dispone de un directorio para el entorno y la caché del modelo. `vllm-admin` ejecuta el panel. El grupo `vllm-config` da a ambas unidades acceso de lectura al JSON. Ejecuta estos comandos una vez para crear las cuentas.

```sh
sudo groupadd --system vllm-config
sudo useradd --system --user-group --no-create-home --shell /usr/sbin/nologin vllm-admin
sudo useradd --system --user-group --create-home --home-dir /var/lib/vllm \
  --shell /usr/sbin/nologin vllm-engine
sudo install -d -o root -g vllm-config -m 0750 /etc/vllm-admin
```

Desde un checkout limpio y de confianza, instala el código y las dependencias del panel. Mantén el directorio de instalación, la unidad, el lanzador y el helper bajo control de root. La cuenta del panel solo necesita lectura y ejecución sobre el código.

```sh
sudo install -d -o root -g root -m 0755 /opt/vllm-admin
sudo cp -R main.py start-vllm.py pyproject.toml uv.lock src static /opt/vllm-admin/
sudo uv --directory /opt/vllm-admin sync --locked --no-dev --python /usr/bin/python3
```

### Instalación del motor vLLM

Comprueba la arquitectura de la GPU, el controlador, la versión de Python admitida y la memoria disponible antes de elegir una versión de vLLM. Usa un entorno independiente para conservar la combinación compatible de PyTorch y CUDA. La detección automática selecciona el backend de PyTorch. La compatibilidad del hardware y del modelo se comprueba al arrancar. Consulta la [guía oficial de instalación con GPU](https://docs.vllm.ai/en/stable/getting_started/installation/gpu/).

Ejemplo para NVIDIA con un controlador operativo y una versión de vLLM compatible con Python 3.12. Ajusta la versión de Python y fija la versión de vLLM según la combinación que valides en tu equipo.

```sh
nvidia-smi
sudo -H -u vllm-engine uv --directory /var/lib/vllm venv --python 3.12 .venv
sudo -H -u vllm-engine uv --directory /var/lib/vllm pip install \
  --python /var/lib/vllm/.venv/bin/python vllm --torch-backend=auto
```

Crea `/etc/vllm-admin/settings.json` con un modelo compatible con tu GPU. Si el motor agota la VRAM al arrancar, prueba con un contexto más corto o menos secuencias simultáneas. El lanzador ejecuta vLLM con `--enforce-eager`.

```json
{
  "model": "Qwen/Qwen3-1.7B",
  "served_model_name": "qwen-local",
  "gpu_memory_utilization": 0.8,
  "max_model_len": 2048,
  "max_num_seqs": 2,
  "auto_start": false
}
```

```sh
sudo chown root:vllm-config /etc/vllm-admin/settings.json
sudo chmod 0640 /etc/vllm-admin/settings.json
```

### Unidades de systemd

Guarda esta unidad en `/etc/systemd/system/vllm.service`. El motor escucha por defecto en `127.0.0.1:8000`. Si necesitas acceso remoto, configura `VLLM_HOST` para una interfaz que permita conservar la comprobación del panel en loopback y restringe el acceso de red al motor.

```ini
[Unit]
Description=vLLM inference engine
After=network.target

[Service]
Type=simple
EnvironmentFile=-/etc/vllm-admin/vllm.env
User=vllm-engine
Group=vllm-engine
SupplementaryGroups=vllm-config
WorkingDirectory=/var/lib/vllm
Environment=HOME=/var/lib/vllm
Environment=VLLM_BIN=/var/lib/vllm/.venv/bin/vllm
ExecStart=/usr/bin/python3 /opt/vllm-admin/start-vllm.py
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

Guarda esta unidad en `/etc/systemd/system/vllm-admin.service`. El panel carece de autenticación y escucha en loopback. Puedes acceder desde otro equipo de confianza mediante un túnel SSH.

```ini
[Unit]
Description=vLLM administration panel
After=network.target

[Service]
Type=simple
EnvironmentFile=-/etc/vllm-admin/vllm.env
User=vllm-admin
Group=vllm-admin
SupplementaryGroups=vllm-config
WorkingDirectory=/opt/vllm-admin
ExecStart=/opt/vllm-admin/.venv/bin/uvicorn main:app --host 127.0.0.1 --port 8080
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

### Permisos de operación y escritura

Edita las reglas con `sudo visudo -f /etc/sudoers.d/vllm-admin`. Cada permiso se limita a una acción concreta sobre `vllm.service`.

```sudoers
vllm-admin ALL=(root) NOPASSWD: /usr/bin/systemctl start vllm.service, /usr/bin/systemctl stop vllm.service, /usr/bin/systemctl restart vllm.service
vllm-admin ALL=(root) NOPASSWD: /usr/bin/systemctl is-active vllm.service, /usr/bin/systemctl is-enabled vllm.service
vllm-admin ALL=(root) NOPASSWD: /usr/bin/systemctl enable vllm.service, /usr/bin/systemctl disable vllm.service
```

Para habilitar **Guardar**, instala el helper del repositorio. Actualízalo también en instalaciones existentes para que el guardado use los mismos límites que el panel.

```bash
sudo install -o root -g root -m 0755 scripts/vllm-save-config /usr/local/sbin/vllm-save-config
```

El helper valida la entrada y reemplaza el archivo de forma atómica, conservando su propietario, grupo y permisos. Si el archivo aún no existe, usa `root:vllm-config` y modo `0640`. El contexto admite enteros positivos o `-1` para ajuste automático. vLLM comprueba si el contexto y la concurrencia solicitados son viables al iniciar. Añade esta regla una vez instalado.

```sudoers
vllm-admin ALL=(root) NOPASSWD: /usr/local/sbin/vllm-save-config ""
```

### Llamadas automáticas a herramientas

En **Configuración de vLLM**, elige el modo de **Llamadas automáticas a herramientas**:

- **Activadas** usa el analizador indicado en el panel. Para `Qwen/Qwen3-1.7B` usa `hermes`. Para el formato XML de `LiquidAI/LFM3-1.7B`, prueba `qwen3_coder` y verifica una llamada con ese modelo.
- **Desactivadas** deshabilita la selección automática de herramientas, aunque systemd defina `VLLM_TOOL_CALL_PARSER`.
- **Predeterminado del servidor** sigue usando `VLLM_TOOL_CALL_PARSER` si está definido. Si no lo está, el lanzador activa `hermes` para `Qwen/Qwen3-1.7B`. Los archivos de configuración antiguos usan este modo.

En una instalación existente, actualiza primero el helper y el panel desde el directorio del repositorio:

```bash
sudo install -o root -g root -m 0755 scripts/vllm-save-config /usr/local/sbin/vllm-save-config
sudo systemctl restart vllm-admin.service
```

Pulsa **Guardar y reiniciar** para aplicar el modo en vLLM. Para comprobar la activación, pide al modelo que invoque una herramienta desde un cliente que envíe `tool_choice: "auto"`. En la respuesta de la API, la llamada aparece en `choices[0].message.tool_calls`.

### Cambiar el puerto de inferencia

Si el puerto `8000` está ocupado, elige uno libre, por ejemplo `8001`. Define `VLLM_PORT` en un archivo que lean tanto el motor como el panel para que la comprobación de salud use el mismo puerto.

Crea `/etc/vllm-admin/vllm.env` con esta línea:

```ini
VLLM_PORT=8001
```

Si ya tienes unidades instaladas que no incluyen `EnvironmentFile`, ejecuta `sudo systemctl edit vllm.service` y `sudo systemctl edit vllm-admin.service`. Añade este bloque a cada unidad:

```ini
[Service]
EnvironmentFile=-/etc/vllm-admin/vllm.env
```

Aplica los cambios. Reiniciar el motor interrumpe la inferencia mientras se vuelve a cargar el modelo.

```sh
sudo systemctl daemon-reload
sudo systemctl restart vllm.service vllm-admin.service
curl -f http://127.0.0.1:8001/health
```

Usa el nuevo puerto en la URL base de los clientes (por ejemplo, `http://IP_DEL_SERVIDOR:8001/v1`) y en la regla de firewall de la API si das acceso desde la oficina. El panel sigue en el puerto `8080`. Si ejecutas el panel sin systemd, pásale también `VLLM_PORT=8001` al iniciar Uvicorn.

### Arranque y verificación

```sh
sudo systemctl daemon-reload
sudo systemctl enable --now vllm-admin.service
sudo systemctl start vllm.service
```

```sh
systemctl status vllm-admin.service vllm.service
sudo journalctl -u vllm-admin.service -u vllm.service -n 80
curl -f http://127.0.0.1:8080/api/status
curl -f http://127.0.0.1:8000/health
curl -f http://127.0.0.1:8000/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{"model":"qwen-local","messages":[{"role":"user","content":"Hello"}],"max_tokens":32}'
```

Una unidad activa aún puede estar cargando el modelo. Comprueba `/health` antes de enviar una petición de inferencia. Guardar cambios requiere reiniciar el motor para aplicarlos. Systemd determina el arranque automático y el campo `auto_start` se conserva por compatibilidad.

## Verificar

```sh
uv run python -m unittest discover -s tests
curl -i http://127.0.0.1:8080/api/metrics
curl -i http://127.0.0.1:8000/health
```

El panel distingue entre una unidad detenida, una unidad activa cuyo modelo todavía no responde y un modelo listo.
