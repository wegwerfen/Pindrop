import importlib.util
import json
import sqlite3
from pathlib import Path
from typing import Optional

from .base import ContentPlugin

# Built-in plugins ship with the repository, relative to this file
_BUILT_IN_DIR = Path(__file__).parent.parent.parent / "plugins" / "built-in"


class PluginLoader:
    def __init__(self, conn: sqlite3.Connection, data_path: Path):
        self._conn = conn
        self._data_path = data_path
        self._content_plugins: dict[str, ContentPlugin] = {}
        self._manifests: dict[str, dict] = {}

    def load_all(self) -> None:
        self._load_from_dir(_BUILT_IN_DIR, built_in=True)

        installed_dir = self._data_path / "system" / "plugins" / "installed"
        if installed_dir.exists():
            self._load_from_dir(installed_dir, built_in=False)

    def _load_from_dir(self, base_dir: Path, built_in: bool) -> None:
        if not base_dir.exists():
            return
        for manifest_path in sorted(base_dir.rglob("plugin.json")):
            try:
                self._load_plugin(manifest_path, built_in)
            except Exception as exc:
                print(f"  warning: failed to load plugin at {manifest_path}: {exc}")

    def _load_plugin(self, manifest_path: Path, built_in: bool) -> None:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        plugin_id = manifest["id"]
        category = manifest["category"]

        # Upsert into plugin_registry
        self._conn.execute(
            """
            INSERT INTO plugin_registry (id, category, version, display_name, built_in, active)
            VALUES (?, ?, ?, ?, ?, 1)
            ON CONFLICT(id) DO UPDATE SET
                version      = excluded.version,
                display_name = excluded.display_name,
                built_in     = excluded.built_in
            """,
            (plugin_id, category, manifest["version"], manifest["display_name"], 1 if built_in else 0),
        )
        self._conn.commit()
        self._manifests[plugin_id] = manifest

        # Dynamically load content plugin code
        if category == "content":
            plugin_py = manifest_path.parent / "plugin.py"
            if plugin_py.exists():
                spec = importlib.util.spec_from_file_location(
                    f"pindrop_plugin_{plugin_id}", plugin_py
                )
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                instance: ContentPlugin = module.Plugin()
                self._content_plugins[plugin_id] = instance
                print(f"  loaded content plugin: {plugin_id} v{manifest['version']}")

    # --- Accessors ---

    def get_content_plugin(self, plugin_id: str) -> Optional[ContentPlugin]:
        return self._content_plugins.get(plugin_id)

    def all_content_plugins(self) -> dict[str, ContentPlugin]:
        return dict(self._content_plugins)

    def manifest(self, plugin_id: str) -> Optional[dict]:
        return self._manifests.get(plugin_id)

    def all_manifests(self) -> dict[str, dict]:
        return dict(self._manifests)
