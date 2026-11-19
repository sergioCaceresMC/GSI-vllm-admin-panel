import json
import os
import shutil
import subprocess
import urllib.error
import urllib.request
from pathlib import Path

import psutil


def read_config():
    return json.loads(Path("/etc/vllm-admin/settings.json").read_text())


def write_config(payload):
    return subprocess.run(
        ["sudo", "-n", "/usr/local/sbin/vllm-save-config"],
        input=payload,
        capture_output=True,
        text=True,
        timeout=10,
    )


def systemctl(*args):
    return subprocess.run(
        ["sudo", "-n", "/usr/bin/systemctl", *args, "vllm.service"],
        capture_output=True,
        text=True,
        timeout=30,
    )


def health_ready():
    try:
        port = int(os.environ.get("VLLM_PORT", "8000"))
        if not 1 <= port <= 65535:
            return False
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/health", timeout=2) as response:
            return response.status == 200
    except (ValueError, OSError):
        return False


def read_metrics():
    cpu = psutil.cpu_percent(interval=None)
    memory = psutil.virtual_memory()

    gpu = None

    if shutil.which("nvidia-smi"):
        result = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=name,utilization.gpu,memory.used,memory.total,temperature.gpu",
                "--format=csv,noheader,nounits",
            ],
            capture_output=True,
            text=True,
            timeout=5,
        )

        if result.returncode == 0:
            values = result.stdout.strip().splitlines()[0].split(",")

            gpu = {
                "name": values[0].strip(),
                "utilization": float(values[1]),
                "memory_used": float(values[2]),
                "memory_total": float(values[3]),
                "temperature": float(values[4]),
            }

    return {
        "cpu": cpu,
        "ram": {
            "percent": memory.percent,
            "used_gb": round(memory.used / 1024**3, 2),
            "total_gb": round(memory.total / 1024**3, 2),
        },
        "gpu": gpu,
    }
