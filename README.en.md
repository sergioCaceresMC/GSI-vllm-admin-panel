# vLLM Admin

[Español](README.md)

A FastAPI dashboard for administering a vLLM inference server on Linux. Use it to start, stop, and restart the engine, check readiness, monitor resources, save settings, and manage startup through systemd.

## Table of contents

- [Run the dashboard](#run-the-dashboard)
- [Usage](#usage)
  - [Access from another device on the same network](#access-from-another-device-on-the-same-network)
  - [Access the vLLM API from the office](#access-the-vllm-api-from-the-office)
  - [Direct dashboard access from a phone](#direct-dashboard-access-from-a-phone)
  - [Restrict access with UFW](#restrict-access-with-ufw)
- [Linux deployment with systemd](#linux-deployment-with-systemd)
  - [Accounts and permissions](#accounts-and-permissions)
  - [Install the vLLM engine](#install-the-vllm-engine)
  - [systemd units](#systemd-units)
  - [Service control and write permissions](#service-control-and-write-permissions)
  - [Change the inference port](#change-the-inference-port)
  - [Start and verify](#start-and-verify)
- [Verify](#verify)

## Run the dashboard

You need Python 3.10 or later and [uv](https://docs.astral.sh/uv/). From the repository root:

```sh
uv sync --locked
uv run uvicorn main:app --host 127.0.0.1 --port 8080
```

Open the dashboard at `http://127.0.0.1:8080`. The dashboard has no authentication. Keep it bound to loopback.

## Usage

On the machine running the dashboard, open `http://127.0.0.1:8080`. Select **Iniciar** (Start) to start vLLM and wait for **Modelo disponible** (Model ready). To save changes and apply them immediately, select **Guardar y reiniciar** (Save and restart).

### Access from another device on the same network

1. On the Linux server, list the IPv4 addresses of its active interfaces.

   ```sh
   ip -br -4 address show up
   ```

   Choose the address of the Ethernet or Wi-Fi interface connected to the same network as the other device. If it shows `192.168.1.42/24`, use `192.168.1.42`. Skip `lo`, VPN and container interfaces, and the network prefix length.
2. With the SSH server enabled, run this on the device you want to connect from. Replace `username` with your SSH login and the IP with the server's address.

   ```sh
   ssh -N -L 127.0.0.1:18080:127.0.0.1:8080 username@192.168.1.42
   ```

3. Keep the SSH connection open and visit `http://127.0.0.1:18080` in that device's browser. On a phone, use an SSH client with local port forwarding and set the local port to `18080` and the remote destination to `127.0.0.1:8080`.

If the tunnel fails to connect, check that SSH accepts connections from the local network and that both devices can reach each other. Some guest networks isolate devices. Keep the dashboard's port `8080` bound to loopback because the dashboard has no authentication.

### Access the vLLM API from the office

The examples use `203.0.113.182` and `203.0.113.128/25`, which are reserved for documentation. Replace them with the server IP and the authorized subnet provided by your network administrator. [RFC 5737](https://www.rfc-editor.org/info/rfc5737/)

When configured with `VLLM_HOST=0.0.0.0`, the engine listens on all IPv4 interfaces. Check API connectivity from another computer in the office.

```sh
curl -i http://203.0.113.182:8000/health
```

If it returns `200 OK`, configure your OpenAI-compatible client with the base URL `http://203.0.113.182:8000/v1`.

### Direct dashboard access from a phone

Use the SSH tunnel while the dashboard lacks authentication. Any device that can reach the dashboard port could control vLLM. Once access protection is in place, you can enable direct access by editing the unit with `sudo nano /etc/systemd/system/vllm-admin.service` and replacing `--host 127.0.0.1` with the IP assigned to the server.

```ini
ExecStart=/opt/vllm-admin/.venv/bin/uvicorn main:app --host 203.0.113.182 --port 8080
```

```sh
sudo systemctl daemon-reload
sudo systemctl restart vllm-admin.service
```

After reloading and restarting the service, open `http://203.0.113.182:8080` on a phone connected to the authorized network.

### Restrict access with UFW

If you use UFW, first verify it is active and check the existing rules.

```sh
sudo ufw status numbered
```

Allow API access from the office subnet with the port 8000 rule. Once the dashboard is protected, you can add the port 8080 rule.

```sh
sudo ufw allow from 203.0.113.128/25 to any port 8000 proto tcp
```

```sh
sudo ufw allow from 203.0.113.128/25 to any port 8080 proto tcp
```

These rules grant access. Review broader rules and the default incoming policy before treating access as restricted. If the server has a public IP, restrict it at the firewall even if the address is assigned within the office.

## Linux deployment with systemd

This example uses a fresh installation at `/opt/vllm-admin`, system Python 3.10 or later, and a trusted `uv` installation available on the `sudo` path. If you change the project directory, update both systemd units.

### Accounts and permissions

Create two non-interactive system accounts. `vllm-engine` runs inference and has a directory for its environment and model cache. `vllm-admin` runs the dashboard. The `vllm-config` group gives both units read access to the JSON file. Run these commands once to create the accounts.

```sh
sudo groupadd --system vllm-config
sudo useradd --system --user-group --no-create-home --shell /usr/sbin/nologin vllm-admin
sudo useradd --system --user-group --create-home --home-dir /var/lib/vllm \
  --shell /usr/sbin/nologin vllm-engine
sudo install -d -o root -g vllm-config -m 0750 /etc/vllm-admin
```

From a clean, trusted checkout, install the dashboard code and dependencies. Keep the installation directory, units, launcher, and helper under root control. The dashboard account only needs read and execute access to the code.

```sh
sudo install -d -o root -g root -m 0755 /opt/vllm-admin
sudo cp -R main.py start-vllm.py pyproject.toml uv.lock src static /opt/vllm-admin/
sudo uv --directory /opt/vllm-admin sync --locked --no-dev --python /usr/bin/python3
```

### Install the vLLM engine

Check GPU architecture, driver, supported Python version, and available memory before choosing vLLM. Use a separate environment to keep a compatible PyTorch and CUDA combination. Automatic detection selects the PyTorch backend. Verify hardware and model compatibility on startup. See the [official GPU installation guide](https://docs.vllm.ai/en/stable/getting_started/installation/gpu/).

Example for NVIDIA with a working driver and a vLLM release that supports Python 3.12. Adjust Python and pin the vLLM version to the combination you validate on your host.

```sh
nvidia-smi
sudo -H -u vllm-engine uv --directory /var/lib/vllm venv --python 3.12 .venv
sudo -H -u vllm-engine uv --directory /var/lib/vllm pip install \
  --python /var/lib/vllm/.venv/bin/python vllm --torch-backend=auto
```

Create `/etc/vllm-admin/settings.json` with a model compatible with your GPU. If the engine runs out of VRAM on startup, try a shorter context or fewer concurrent sequences. The launcher runs vLLM with `--enforce-eager`.

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

### systemd units

Save this unit as `/etc/systemd/system/vllm.service`. The engine defaults to `127.0.0.1:8000`. For remote access, configure `VLLM_HOST` to keep the dashboard's loopback check reachable and restrict network access to the engine.

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

Save this unit as `/etc/systemd/system/vllm-admin.service`. The dashboard has no authentication and listens on loopback. Use an SSH tunnel to reach it from another trusted machine.

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

### Service control and write permissions

Edit the rules with `sudo visudo -f /etc/sudoers.d/vllm-admin`. Each permission is scoped to one action on `vllm.service`.

```sudoers
vllm-admin ALL=(root) NOPASSWD: /usr/bin/systemctl start vllm.service, /usr/bin/systemctl stop vllm.service, /usr/bin/systemctl restart vllm.service
vllm-admin ALL=(root) NOPASSWD: /usr/bin/systemctl is-active vllm.service, /usr/bin/systemctl is-enabled vllm.service
vllm-admin ALL=(root) NOPASSWD: /usr/bin/systemctl enable vllm.service, /usr/bin/systemctl disable vllm.service
```

To enable **Guardar** (Save), install a trusted helper at `/usr/local/sbin/vllm-save-config`, owned and executable by root. The helper is provided separately. It must read JSON from standard input, validate the keys, types, and ranges defined in `src/vllm_admin/api.py`, and atomically replace the file from the same directory with owner `root:vllm-config` and mode `0640`. Invalid input must return an error and preserve the previous file. Add this rule after installation.

```sudoers
vllm-admin ALL=(root) NOPASSWD: /usr/local/sbin/vllm-save-config ""
```

### Change the inference port

If port `8000` is in use, choose a free port such as `8001`. Set `VLLM_PORT` in a file read by both the engine and the dashboard so the health check uses the same port.

Create `/etc/vllm-admin/vllm.env` with this line:

```ini
VLLM_PORT=8001
```

If your installed units lack `EnvironmentFile`, run `sudo systemctl edit vllm.service` and `sudo systemctl edit vllm-admin.service`. Add this block to each unit:

```ini
[Service]
EnvironmentFile=-/etc/vllm-admin/vllm.env
```

Apply the changes. Restarting the engine interrupts inference while the model reloads.

```sh
sudo systemctl daemon-reload
sudo systemctl restart vllm.service vllm-admin.service
curl -f http://127.0.0.1:8001/health
```

Use the new port in client base URLs (for example, `http://SERVER_IP:8001/v1`) and in the API firewall rule if you allow office access. The dashboard still uses port `8080`. If you run the dashboard without systemd, set `VLLM_PORT=8001` when starting Uvicorn.

### Start and verify

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

An active unit may still be loading the model. Check `/health` before sending an inference request. Restart the engine to apply saved settings. Systemd controls autostart and the `auto_start` field is retained for compatibility.

## Verify

```sh
uv run python -m unittest discover -s tests
curl -i http://127.0.0.1:8080/api/metrics
curl -i http://127.0.0.1:8000/health
```

The dashboard distinguishes a stopped unit, an active unit whose model is still unavailable, and a ready model.
