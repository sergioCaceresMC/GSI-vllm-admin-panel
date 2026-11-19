#!/usr/bin/env python3

"""Launch vLLM using the admin configuration."""

import json
import os
import shutil
from pathlib import Path

CONFIG_PATH = "/etc/vllm-admin/settings.json"


def main():
    executable = shutil.which(os.environ.get("VLLM_BIN", "vllm"))
    if executable is None:
        raise SystemExit("vLLM executable not found. Set VLLM_BIN or add vllm to PATH.")

    config = json.loads(Path(CONFIG_PATH).read_text())

    args = [
        executable,
        "serve",
        config["model"],

        "--host", os.environ.get("VLLM_HOST", "127.0.0.1"),
        "--port", "8000",

        "--served-model-name",
        config["served_model_name"],

        "--gpu-memory-utilization",
        str(config["gpu_memory_utilization"]),

        "--max-model-len",
        str(config["max_model_len"]),

        "--max-num-seqs",
        str(config["max_num_seqs"]),

        "--enforce-eager",
    ]

    os.execv(executable, args)


if __name__ == "__main__":
    main()
