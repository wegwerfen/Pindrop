from contextlib import asynccontextmanager

from fastapi import FastAPI, Request

from core.db import get_connection, get_data_path, run_migrations
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


@app.get("/health")
def health():
    return {"status": "ok"}


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
    """Debug endpoint: show which content plugin would handle a given URL."""
    router: ContentRouter = request.app.state.router
    plugin = router.route(url)
    if plugin is None:
        return {"url": url, "plugin": None}
    return {"url": url, "plugin": plugin.plugin_id}
