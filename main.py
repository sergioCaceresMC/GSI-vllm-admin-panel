from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from vllm_admin.api import operation_failed, router
from vllm_admin.application import OperationFailed


STATIC_DIR = Path(__file__).resolve().parent / "static"

app = FastAPI(title="vLLM Admin")
app.include_router(router)
app.add_exception_handler(OperationFailed, operation_failed)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/")
def index():
    return FileResponse(STATIC_DIR / "index.html")
