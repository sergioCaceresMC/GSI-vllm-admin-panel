from . import adapters


class OperationFailed(Exception):
    pass


def get_config():
    return adapters.read_config()


def save_config(payload):
    result = adapters.write_config(payload)
    if result.returncode != 0:
        raise OperationFailed(result.stderr.strip())


def get_status():
    running = adapters.systemctl("is-active").stdout.strip() == "active"
    ready = running and adapters.health_ready()

    state = "stopped"
    if running:
        state = "ready" if ready else "starting"

    return {"running": running, "ready": ready, "state": state}


def control_service(command):
    result = adapters.systemctl(command)
    if result.returncode != 0:
        raise OperationFailed(result.stderr)


def get_autostart():
    return adapters.systemctl("is-enabled").stdout.strip() == "enabled"


def set_autostart(enabled):
    command = "enable" if enabled else "disable"
    result = adapters.systemctl(command)
    if result.returncode != 0:
        raise OperationFailed(result.stderr.strip())


def get_metrics():
    return adapters.read_metrics()
