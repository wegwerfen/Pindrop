"""
Tag CRUD and artifact-tag relationship endpoints.
"""
import sqlite3
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from ulid import ULID

from core.db import get_connection

router = APIRouter()


# ---------------------------------------------------------------------------
# Tag CRUD
# ---------------------------------------------------------------------------

@router.get("/tags")
def list_tags():
    conn = get_connection()
    try:
        rows = conn.execute(
            """
            SELECT t.id, t.name, t.color,
                   COUNT(at.artifact_id) AS artifact_count
            FROM tag t
            LEFT JOIN artifact_tag at ON at.tag_id = t.id
            GROUP BY t.id
            ORDER BY t.name
            """
        ).fetchall()
        return [
            {
                "id": row["id"],
                "name": row["name"],
                "color": row["color"],
                "artifact_count": row["artifact_count"],
            }
            for row in rows
        ]
    finally:
        conn.close()


class TagCreate(BaseModel):
    name: str
    color: Optional[str] = None


@router.post("/tags", status_code=201)
def create_tag(body: TagCreate):
    conn = get_connection()
    try:
        existing = conn.execute(
            "SELECT id FROM tag WHERE name = ?", (body.name,)
        ).fetchone()
        if existing:
            raise HTTPException(status_code=409, detail=f"Tag '{body.name}' already exists")

        tag_id = str(ULID())
        conn.execute(
            "INSERT INTO tag (id, name, color) VALUES (?, ?, ?)",
            (tag_id, body.name, body.color),
        )
        conn.commit()
        return {"id": tag_id, "name": body.name, "color": body.color, "artifact_count": 0}
    finally:
        conn.close()


class TagUpdate(BaseModel):
    name: Optional[str] = None
    color: Optional[str] = None


@router.patch("/tags/{tag_id}")
def update_tag(tag_id: str, body: TagUpdate):
    conn = get_connection()
    try:
        row = conn.execute("SELECT * FROM tag WHERE id = ?", (tag_id,)).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Tag not found")

        fields = body.model_dump(exclude_none=True)
        if not fields:
            raise HTTPException(status_code=400, detail="No fields to update")

        if "name" in fields:
            conflict = conn.execute(
                "SELECT id FROM tag WHERE name = ? AND id != ?", (fields["name"], tag_id)
            ).fetchone()
            if conflict:
                raise HTTPException(status_code=409, detail=f"Tag '{fields['name']}' already exists")

        set_clauses = ", ".join(f"{k} = ?" for k in fields)
        conn.execute(
            f"UPDATE tag SET {set_clauses} WHERE id = ?",
            list(fields.values()) + [tag_id],
        )
        conn.commit()

        updated = conn.execute("SELECT * FROM tag WHERE id = ?", (tag_id,)).fetchone()
        return {"id": updated["id"], "name": updated["name"], "color": updated["color"]}
    finally:
        conn.close()


@router.delete("/tags/{tag_id}", status_code=204)
def delete_tag(tag_id: str):
    conn = get_connection()
    try:
        row = conn.execute("SELECT id FROM tag WHERE id = ?", (tag_id,)).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Tag not found")
        # artifact_tag rows cascade via FK ON DELETE CASCADE
        conn.execute("DELETE FROM tag WHERE id = ?", (tag_id,))
        conn.commit()
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Artifact-tag relations
# ---------------------------------------------------------------------------

class ArtifactTagAdd(BaseModel):
    tag_id: str


@router.post("/artifacts/{artifact_id}/tags", status_code=201)
def add_tag_to_artifact(artifact_id: str, body: ArtifactTagAdd):
    conn = get_connection()
    try:
        if not conn.execute("SELECT id FROM artifact WHERE id = ?", (artifact_id,)).fetchone():
            raise HTTPException(status_code=404, detail="Artifact not found")
        if not conn.execute("SELECT id FROM tag WHERE id = ?", (body.tag_id,)).fetchone():
            raise HTTPException(status_code=404, detail="Tag not found")

        existing = conn.execute(
            "SELECT 1 FROM artifact_tag WHERE artifact_id = ? AND tag_id = ?",
            (artifact_id, body.tag_id),
        ).fetchone()
        if existing:
            raise HTTPException(status_code=409, detail="Artifact already has this tag")

        conn.execute(
            "INSERT INTO artifact_tag (artifact_id, tag_id, source) VALUES (?, ?, ?)",
            (artifact_id, body.tag_id, "user"),
        )
        conn.commit()
        return {"artifact_id": artifact_id, "tag_id": body.tag_id}
    finally:
        conn.close()


@router.delete("/artifacts/{artifact_id}/tags/{tag_id}", status_code=204)
def remove_tag_from_artifact(artifact_id: str, tag_id: str):
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT 1 FROM artifact_tag WHERE artifact_id = ? AND tag_id = ?",
            (artifact_id, tag_id),
        ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Artifact does not have this tag")
        conn.execute(
            "DELETE FROM artifact_tag WHERE artifact_id = ? AND tag_id = ?",
            (artifact_id, tag_id),
        )
        conn.commit()
    finally:
        conn.close()
