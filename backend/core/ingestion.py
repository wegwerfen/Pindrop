"""
Core ingestion pipeline.

Orchestrates the flow from a source URL/file through a content plugin
to final artifact persistence: temp files → artifact directory → database.
"""
import json
import shutil
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

from ulid import ULID

from core.db import get_data_path
from core.plugins.base import ArtifactData, IngestionError
from core.plugins.loader import PluginLoader
from core.plugins.router import ContentRouter

# Maps ArtifactData.files role keys to (subdirectory, filename) within the artifact directory.
# Empty string subdirectory means artifact root.
_ROLE_TO_PATH: dict[str, tuple[str, str]] = {
    "raw_html":      ("raw",       "original.html"),
    "readable_html": ("processed", "readable.html"),
    "readable_txt":  ("processed", "readable.txt"),
    "markdown":      ("processed", "markdown.md"),
    "screenshot":    ("",          "screenshot.jpg"),
    "thumbnail":     ("",          "thumbnail.jpg"),
    "pdf":           ("raw",       "original.pdf"),
}


def ingest_url(
    url: str,
    conn: sqlite3.Connection,
    loader: PluginLoader,
    router: ContentRouter,
    user_id: str = "default",
) -> dict:
    """
    Full ingest pipeline for a URL. Blocking.

    Returns the persisted artifact record as a dict.
    Raises IngestionError if the URL cannot be handled or the plugin fails.
    """
    plugin = router.route(url)
    if plugin is None:
        raise IngestionError(f"No content plugin found for: {url}")

    artifact_id = str(ULID())
    data_path = get_data_path()

    temp_dir = data_path / "system" / "temp" / "ingest"
    temp_dir.mkdir(parents=True, exist_ok=True)

    # Build merged config: global user settings (base) + plugin-specific config (overrides)
    user_row = conn.execute(
        "SELECT settings FROM user WHERE id = ?", (user_id,)
    ).fetchone()
    global_settings: dict = json.loads(user_row["settings"]) if user_row and user_row["settings"] else {}

    plugin_row = conn.execute(
        "SELECT config FROM plugin_registry WHERE id = ?", (plugin.plugin_id,)
    ).fetchone()
    plugin_config: dict = json.loads(plugin_row["config"]) if plugin_row and plugin_row["config"] else {}

    # Flat merge: global settings first, then plugin-specific config on top.
    # Plugin config wins on key conflicts — allows per-plugin overrides of globals.
    config: dict = {**global_settings, **plugin_config}

    # --- Call the plugin (blocking) ---
    artifact_data: ArtifactData = plugin.ingest(url, artifact_id, temp_dir, config)

    # --- Move temp files to final artifact directory ---
    artifact_dir = data_path / "users" / user_id / "artifacts" / artifact_id
    (artifact_dir / "raw").mkdir(parents=True, exist_ok=True)
    (artifact_dir / "processed").mkdir(parents=True, exist_ok=True)

    thumbnail_path: str | None = None

    for role, temp_path_str in artifact_data.files.items():
        src = Path(temp_path_str)
        if not src.exists():
            continue

        if role.startswith("image_"):
            # image_0, image_1, ... → image_0.webp, image_1.webp, ...
            idx = role.split("_", 1)[1]
            dest = artifact_dir / f"image_{idx}.webp"
        elif role in _ROLE_TO_PATH:
            subdir, filename = _ROLE_TO_PATH[role]
            dest = artifact_dir / subdir / filename if subdir else artifact_dir / filename
        else:
            # Unknown role — place in processed/ preserving source filename
            dest = artifact_dir / "processed" / src.name

        shutil.move(str(src), str(dest))

        if role == "thumbnail":
            thumbnail_path = str(dest)

    # --- Write artifact record to database ---
    now = datetime.now(timezone.utc).isoformat()
    domain = urlparse(url).netloc.lower().removeprefix("www.")

    conn.execute(
        """
        INSERT INTO artifact (
            id, plugin_type, source_url, source_domain,
            captured_at, created_at, updated_at,
            content_path, title, excerpt, thumbnail_path,
            plugin_data, plugin_version
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            artifact_id,
            plugin.plugin_id,
            url,
            domain,
            now, now, now,
            str(artifact_dir),
            artifact_data.title,
            artifact_data.excerpt,
            thumbnail_path,
            json.dumps(artifact_data.plugin_data),
            artifact_data.plugin_version,
        ),
    )

    # --- Populate FTS index ---
    fts_text = plugin.get_fts_text({"content_path": str(artifact_dir)})
    conn.execute(
        """
        INSERT INTO artifact_fts(artifact_id, title, excerpt, summary, user_notes, tags, full_text)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (artifact_id, artifact_data.title, artifact_data.excerpt, None, None, None, fts_text),
    )

    # --- Queue AI processing tasks ---
    for task_type in artifact_data.queue_tasks:
        task_id = str(ULID())
        conn.execute(
            """
            INSERT INTO processing_queue (id, artifact_id, task_type, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (task_id, artifact_id, task_type, now),
        )

    conn.commit()

    return {
        "id": artifact_id,
        "plugin_type": plugin.plugin_id,
        "title": artifact_data.title,
        "excerpt": artifact_data.excerpt,
        "source_url": url,
        "source_domain": domain,
        "captured_at": now,
        "content_path": str(artifact_dir),
        "thumbnail_path": thumbnail_path,
        "plugin_data": artifact_data.plugin_data,
        "plugin_version": artifact_data.plugin_version,
        "queue_tasks": artifact_data.queue_tasks,
    }
