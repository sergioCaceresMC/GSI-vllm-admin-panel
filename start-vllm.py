#!/usr/bin/env python3

"""Launch vLLM using the admin configuration."""

import json
import os
import shutil
from pathlib import Path

CONFIG_PATH = "/etc/vllm-admin/settings.json"


def main():
    try:
        port = int(os.environ.get("VLLM_PORT", "8000"))
    except ValueError:
        raise SystemExit("VLLM_PORT must be an integer between 1 and 65535.") from None
    if not 1 <= port <= 65535:
        raise SystemExit("VLLM_PORT must be an integer between 1 and 65535.")

    executable = shutil.which(os.environ.get("VLLM_BIN", "vllm"))
    if executable is None:
        raise SystemExit("vLLM executable not found. Set VLLM_BIN or add vllm to PATH.")

    config = json.loads(Path(CONFIG_PATH).read_text())
    tool_choice = config.get("enable_auto_tool_choice")
    if tool_choice is None:
        tool_call_parser = os.environ.get("VLLM_TOOL_CALL_PARSER")
        if tool_call_parser is None and config["model"] == "Qwen/Qwen3-1.7B":
            tool_call_parser = "hermes"
    else:
        tool_call_parser = config.get("tool_call_parser") if tool_choice else None
        if tool_choice and not tool_call_parser:
            raise SystemExit("tool_call_parser is required when enable_auto_tool_choice is true.")

    args = [
        executable,
        "serve",
        config["model"],

        "--host", os.environ.get("VLLM_HOST", "127.0.0.1"),
        "--port", str(port),

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

    if tool_call_parser:
        args.extend(["--enable-auto-tool-choice", "--tool-call-parser", tool_call_parser])

    os.execv(executable, args)


if __name__ == "__main__":
    main()
