from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, field_validator

from . import application
from .application import OperationFailed


router = APIRouter(prefix="/api")


class VLLMConfig(BaseModel):
    model: str = Field(
        min_length=3,
        max_length=200,
        pattern=r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$",
    )

    served_model_name: str = Field(
        min_length=1,
        max_length=64,
        pattern=r"^[A-Za-z0-9_.-]+$",
    )

    gpu_memory_utilization: float = Field(gt=0, le=1)
    max_model_len: int = Field(ge=-1)
    max_num_seqs: int = Field(ge=1)
    auto_start: bool = False

    @field_validator("max_model_len")
    @classmethod
    def validate_max_model_len(cls, value: int) -> int:
        if value == 0:
            raise ValueError("Introduce un contexto positivo o -1 para el ajuste automático")
        return value


class AutoStartConfig(BaseModel):
    enabled: bool


async def operation_failed(_request: Request, exc: OperationFailed):
    return JSONResponse(status_code=500, content={"detail": str(exc)})


@router.get("/config")
def get_config():
    return application.get_config()


@router.put("/config")
def update_config(config: VLLMConfig):
    application.save_config(config.model_dump_json())
    return {"message": "Configuración guardada", "restart_required": True}


@router.get("/status")
def status():
    return application.get_status()


@router.post("/start")
def start():
    application.control_service("start")
    return {"message": "vLLM iniciado"}


@router.post("/stop")
def stop():
    application.control_service("stop")
    return {"message": "vLLM detenido"}


@router.post("/restart")
def restart():
    application.control_service("restart")
    return {"message": "vLLM reiniciado"}


@router.get("/metrics")
def metrics():
    return application.get_metrics()


@router.get("/autostart")
def get_autostart():
    return {"enabled": application.get_autostart()}


@router.put("/autostart")
def set_autostart(config: AutoStartConfig):
    application.set_autostart(config.enabled)
    return {"enabled": config.enabled, "message": "Inicio automático actualizado"}
