from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse

from services.gateway.db import init_db
from services.gateway.routes import router

STATIC_DIR = Path(__file__).parent / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="gateway", lifespan=lifespan)
app.include_router(router)


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "gateway"}


@app.get("/", include_in_schema=False)
def checkout_ui() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")
