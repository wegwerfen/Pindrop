import os
import sqlite3
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

_MIGRATIONS_DIR = Path(__file__).parent / "migrations"


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
