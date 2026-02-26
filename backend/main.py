from contextlib import asynccontextmanager

from fastapi import FastAPI

from core.db import get_connection, run_migrations


@asynccontextmanager
async def lifespan(app: FastAPI):
    conn = get_connection()
    run_migrations(conn)
    conn.close()
    yield


app = FastAPI(title="Pindrop", lifespan=lifespan)


@app.get("/health")
def health():
    return {"status": "ok"}
