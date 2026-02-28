"""
Artifact CRUD endpoints and file serving.
"""
import shutil
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel

from core.db import get_connection
from core.ingestion import _ROLE_TO_PATH

router = APIRouter()

_SORT_MAP = {
    "captured_at_desc": "a.captured_at DESC",
    "captured_at_asc":  "a.captured_at ASC",
    "title_asc":        "a.title ASC",
    "importance_desc":  "a.importance DESC, a.captured_at DESC",
}


def _get_conn(request: Request) -> sqlite3.Connection:
    conn = get_connection()
    request.state.conn = conn
    return conn


def _fetch_tags_for_artifacts(conn: sqlite3.Connection, artifact_ids: list[str]) -> dict[str, list]:
    if not artifact_ids:
        return {}
    placeholders = ",".join("?" * len(artifact_ids))
    rows = conn.execute(
        f"""
        SELECT at.artifact_id, t.id, t.name, t.color
        FROM artifact_tag at
        JOIN tag t ON t.id = at.tag_id
        WHERE at.artifact_id IN ({placeholders})
        ORDER BY t.name
        """,
        artifact_ids,
    ).fetchall()
    result: dict[str, list] = {aid: [] for aid in artifact_ids}
    for row in rows:
        result[row["artifact_id"]].append({
            "id": row["id"],
            "name": row["name"],
            "color": row["color"],
        })
    return result


def _row_to_card(row: sqlite3.Row, tags: list) -> dict:
    return {
        "id": row["id"],
        "plugin_type": row["plugin_type"],
        "title": row["title"],
        "excerpt": row["excerpt"],
        "thumbnail_path": row["thumbnail_path"],
        "captured_at": row["captured_at"],
        "source_url": row["source_url"],
        "source_domain": row["source_domain"],
        "is_archived": bool(row["is_archived"]),
        "is_read": bool(row["is_read"]),
        "importance": row["importance"],
        "tags": tags,
    }


# ---------------------------------------------------------------------------
# List artifacts
# ---------------------------------------------------------------------------

@router.get("/artifacts")
def list_artifacts(
    request: Request,
    limit: int = 50,
    offset: int = 0,
    sort: str = "captured_at_desc",
    tag_id: Optional[str] = None,
    collection_id: Optional[str] = None,
    plugin_type: Optional[str] = None,
    domain: Optional[str] = None,
    is_archived: bool = False,
):
    if limit > 200:
        limit = 200

    order = _SORT_MAP.get(sort, "a.captured_at DESC")

    conn = get_connection()
    try:
        where_clauses = ["a.is_archived = ?"]
        params: list = [int(is_archived)]

        if plugin_type:
            where_clauses.append("a.plugin_type = ?")
            params.append(plugin_type)
        if domain:
            where_clauses.append("a.source_domain = ?")
            params.append(domain)
        if tag_id:
            where_clauses.append(
                "EXISTS (SELECT 1 FROM artifact_tag at WHERE at.artifact_id = a.id AND at.tag_id = ?)"
            )
            params.append(tag_id)
        if collection_id:
            where_clauses.append(
                "EXISTS (SELECT 1 FROM artifact_collection ac WHERE ac.artifact_id = a.id AND ac.collection_id = ?)"
            )
            params.append(collection_id)

        where_sql = " AND ".join(where_clauses)
        rows = conn.execute(
            f"SELECT * FROM artifact a WHERE {where_sql} ORDER BY {order} LIMIT ? OFFSET ?",
            params + [limit, offset],
        ).fetchall()

        artifact_ids = [r["id"] for r in rows]
        tags_by_id = _fetch_tags_for_artifacts(conn, artifact_ids)

        return [_row_to_card(row, tags_by_id[row["id"]]) for row in rows]
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Get artifact detail
# ---------------------------------------------------------------------------

@router.get("/artifacts/{artifact_id}")
def get_artifact(artifact_id: str):
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT * FROM artifact WHERE id = ?", (artifact_id,)
        ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Artifact not found")

        tags = conn.execute(
            """
            SELECT t.id, t.name, t.color, at.source
            FROM artifact_tag at
            JOIN tag t ON t.id = at.tag_id
            WHERE at.artifact_id = ?
            ORDER BY t.name
            """,
            (artifact_id,),
        ).fetchall()

        collections = conn.execute(
            """
            SELECT c.id, c.name
            FROM artifact_collection ac
            JOIN collection c ON c.id = ac.collection_id
            WHERE ac.artifact_id = ?
            ORDER BY c.name
            """,
            (artifact_id,),
        ).fetchall()

        import json
        return {
            "id": row["id"],
            "plugin_type": row["plugin_type"],
            "source_url": row["source_url"],
            "source_domain": row["source_domain"],
            "captured_at": row["captured_at"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
            "content_path": row["content_path"],
            "title": row["title"],
            "excerpt": row["excerpt"],
            "thumbnail_path": row["thumbnail_path"],
            "summary": row["summary"],
            "user_notes": row["user_notes"],
            "is_read": bool(row["is_read"]),
            "is_archived": bool(row["is_archived"]),
            "importance": row["importance"],
            "plugin_data": json.loads(row["plugin_data"]) if row["plugin_data"] else {},
            "plugin_version": row["plugin_version"],
            "tags": [{"id": t["id"], "name": t["name"], "color": t["color"], "source": t["source"]} for t in tags],
            "collections": [{"id": c["id"], "name": c["name"]} for c in collections],
        }
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Update artifact
# ---------------------------------------------------------------------------

class ArtifactUpdate(BaseModel):
    title: Optional[str] = None
    user_notes: Optional[str] = None
    is_read: Optional[bool] = None
    is_archived: Optional[bool] = None
    importance: Optional[int] = None


@router.patch("/artifacts/{artifact_id}")
def update_artifact(artifact_id: str, body: ArtifactUpdate):
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT * FROM artifact WHERE id = ?", (artifact_id,)
        ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Artifact not found")

        fields: dict = body.model_dump(exclude_none=True)
        if not fields:
            raise HTTPException(status_code=400, detail="No fields to update")

        now = datetime.now(timezone.utc).isoformat()
        set_clauses = ", ".join(f"{k} = ?" for k in fields)
        values = list(fields.values()) + [now, artifact_id]
        conn.execute(
            f"UPDATE artifact SET {set_clauses}, updated_at = ? WHERE id = ?",
            values,
        )

        # Re-sync FTS if text fields changed
        if "title" in fields or "user_notes" in fields:
            fts_row = conn.execute(
                "SELECT rowid FROM artifact_fts WHERE artifact_id = ?", (artifact_id,)
            ).fetchone()
            new_title = fields.get("title", row["title"])
            new_notes = fields.get("user_notes", row["user_notes"])
            if fts_row:
                conn.execute("DELETE FROM artifact_fts WHERE rowid = ?", (fts_row[0],))
            conn.execute(
                """
                INSERT INTO artifact_fts(artifact_id, title, excerpt, summary, user_notes, tags, full_text)
                SELECT id, ?, excerpt, summary, ?, NULL, NULL FROM artifact WHERE id = ?
                """,
                (new_title, new_notes, artifact_id),
            )

        conn.commit()
        return get_artifact(artifact_id)
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Delete artifact
# ---------------------------------------------------------------------------

@router.delete("/artifacts/{artifact_id}", status_code=204)
def delete_artifact(artifact_id: str):
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT content_path FROM artifact WHERE id = ?", (artifact_id,)
        ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Artifact not found")

        content_path = row["content_path"]

        # Remove FTS row
        fts_row = conn.execute(
            "SELECT rowid FROM artifact_fts WHERE artifact_id = ?", (artifact_id,)
        ).fetchone()
        if fts_row:
            conn.execute("DELETE FROM artifact_fts WHERE rowid = ?", (fts_row[0],))

        # Remove DB row (cascades to artifact_tag, artifact_collection, processing_queue)
        conn.execute("DELETE FROM artifact WHERE id = ?", (artifact_id,))
        conn.commit()

        # Remove files from disk
        if content_path:
            shutil.rmtree(content_path, ignore_errors=True)
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Serve artifact file
# ---------------------------------------------------------------------------

@router.get("/artifacts/{artifact_id}/files/{role}")
def get_artifact_file(artifact_id: str, role: str):
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT content_path FROM artifact WHERE id = ?", (artifact_id,)
        ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Artifact not found")
    finally:
        conn.close()

    artifact_dir = Path(row["content_path"])

    if role in _ROLE_TO_PATH:
        subdir, filename = _ROLE_TO_PATH[role]
        file_path = artifact_dir / subdir / filename if subdir else artifact_dir / filename
    elif role.startswith("image_"):
        idx = role.split("_", 1)[1]
        file_path = artifact_dir / f"image_{idx}.webp"
    else:
        raise HTTPException(status_code=400, detail=f"Unknown file role: {role}")

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")

    return FileResponse(str(file_path))
