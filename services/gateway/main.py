from contextlib import asynccontextmanager

from fastapi import FastAPI

from services.gateway.db import init_db
from services.gateway.routes import router


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="gateway", lifespan=lifespan)
app.include_router(router)


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "gateway"}
