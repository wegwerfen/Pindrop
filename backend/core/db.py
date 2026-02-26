import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

_MIGRATIONS_DIR = Path(__file__).parent / "migrations"

# Default settings written to the 'default' user record on first run.
# Global knobs that apply across plugins and the application.
DEFAULT_USER_SETTINGS: dict = {
    "storage": {
        "thumbnail_width": 400,
        "thumbnail_height": 300,
    },
    "ai": {
        "active_provider": None,
        "auto_summarize": False,
        "auto_tag": False,
        "auto_embed": False,
    },
    "ui": {
        "card_size": "medium",
        "default_sort": "captured_at_desc",
        "show_archived": False,
    },
}


def get_data_path() -> Path:
    raw = os.getenv("DATA_PATH", "./data")
    path = Path(raw)
    if not path.is_absolute():
        # Resolve relative to the backend directory (parent of core/)
        path = Path(__file__).parent.parent / path
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_connection() -> sqlite3.Connection:
    db_path = get_data_path() / "pindrop.db"
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.executescript("""
        PRAGMA journal_mode = WAL;
        PRAGMA foreign_keys = ON;
        PRAGMA synchronous = NORMAL;
        PRAGMA temp_store = MEMORY;
    """)
    return conn


def run_migrations(conn: sqlite3.Connection) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS _migrations (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            name       TEXT NOT NULL UNIQUE,
            applied_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
    """)
    conn.commit()

    applied = {
        row["name"]
        for row in conn.execute("SELECT name FROM _migrations").fetchall()
    }

    migration_files = sorted(_MIGRATIONS_DIR.glob("*.sql"))

    for migration_file in migration_files:
        name = migration_file.name
        if name in applied:
            continue
        sql = migration_file.read_text(encoding="utf-8")
        conn.executescript(sql)
        conn.execute(
            "INSERT INTO _migrations (name) VALUES (?)", (name,)
        )
        conn.commit()
        print(f"  applied migration: {name}")


def ensure_default_user(conn: sqlite3.Connection) -> None:
    """Create the 'default' user record with default settings if it doesn't exist."""
    existing = conn.execute("SELECT id FROM user WHERE id = 'default'").fetchone()
    if existing:
        return
    now = datetime.now(timezone.utc).isoformat()
    conn.execute(
        "INSERT INTO user (id, display_name, created_at, is_admin, settings) VALUES (?, ?, ?, ?, ?)",
        ("default", "Default User", now, 1, json.dumps(DEFAULT_USER_SETTINGS)),
    )
    conn.commit()
    print("  created default user")
