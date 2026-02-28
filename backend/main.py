from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware

from core.api.artifacts import router as artifacts_router
from core.api.collections import router as collections_router
from core.api.search import router as search_router
from core.api.tags import router as tags_router
from core.db import get_connection, get_data_path, run_migrations
from core.ingestion import ingest_url
from core.plugins.base import IngestionError
from core.plugins.loader import PluginLoader
from core.plugins.router import ContentRouter


@asynccontextmanager
async def lifespan(app: FastAPI):
    conn = get_connection()
    run_migrations(conn)

    loader = PluginLoader(conn, get_data_path())
    loader.load_all()
    conn.close()

    app.state.plugins = loader
    app.state.router = ContentRouter(loader)

    yield


app = FastAPI(title="Pindrop", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(artifacts_router, prefix="/api")
app.include_router(tags_router, prefix="/api")
app.include_router(collections_router, prefix="/api")
app.include_router(search_router, prefix="/api")


@app.get("/health")
def health():
    return {"status": "ok"}


# --- Plugin endpoints ---

@app.get("/api/plugins")
def list_plugins(request: Request):
    loader: PluginLoader = request.app.state.plugins
    return [
        {
            "id": plugin_id,
            "category": manifest.get("category"),
            "version": manifest.get("version"),
            "display_name": manifest.get("display_name"),
            "description": manifest.get("description"),
            "has_frontend": manifest.get("has_frontend", False),
            "dependencies": manifest.get("dependencies", []),
        }
        for plugin_id, manifest in loader.all_manifests().items()
    ]


@app.get("/api/plugins/route")
def route_url(url: str, request: Request):
    """Debug: show which content plugin would handle a given URL."""
    router: ContentRouter = request.app.state.router
    plugin = router.route(url)
    if plugin is None:
        return {"url": url, "plugin": None}
    return {"url": url, "plugin": plugin.plugin_id}


# --- Ingest endpoint ---

@app.post("/api/ingest")
def ingest(url: str, request: Request):
    """
    Ingest a URL. Blocking — returns the full artifact record when complete.
    """
    conn = get_connection()
    try:
        artifact = ingest_url(
            url,
            conn,
            request.app.state.plugins,
            request.app.state.router,
        )
        return artifact
    except IngestionError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    finally:
        conn.close()


# --- Production static file serving ---
# Only activates when frontend/dist/ exists (i.e. after `npm run build`).
# In dev, Vite's proxy handles /api routing on port 5173.
_frontend_dist = Path(__file__).parent.parent / "frontend" / "dist"
if _frontend_dist.exists():
    from fastapi.staticfiles import StaticFiles
    app.mount("/", StaticFiles(directory=str(_frontend_dist), html=True), name="frontend")
