"""
Collection CRUD and artifact-collection relationship endpoints.
"""
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from ulid import ULID

from core.db import get_connection

router = APIRouter()


# ---------------------------------------------------------------------------
# Collection CRUD
# ---------------------------------------------------------------------------

@router.get("/collections")
def list_collections():
    conn = get_connection()
    try:
        rows = conn.execute(
            """
            SELECT c.id, c.name, c.description, c.created_at,
                   COUNT(ac.artifact_id) AS artifact_count
            FROM collection c
            LEFT JOIN artifact_collection ac ON ac.collection_id = c.id
            GROUP BY c.id
            ORDER BY c.name
            """
        ).fetchall()
        return [
            {
                "id": row["id"],
                "name": row["name"],
                "description": row["description"],
                "created_at": row["created_at"],
                "artifact_count": row["artifact_count"],
            }
            for row in rows
        ]
    finally:
        conn.close()


class CollectionCreate(BaseModel):
    name: str
    description: Optional[str] = None


@router.post("/collections", status_code=201)
def create_collection(body: CollectionCreate):
    conn = get_connection()
    try:
        coll_id = str(ULID())
        now = datetime.now(timezone.utc).isoformat()
        conn.execute(
            "INSERT INTO collection (id, name, description, created_at) VALUES (?, ?, ?, ?)",
            (coll_id, body.name, body.description, now),
        )
        conn.commit()
        return {
            "id": coll_id,
            "name": body.name,
            "description": body.description,
            "created_at": now,
            "artifact_count": 0,
        }
    finally:
        conn.close()


class CollectionUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None


@router.patch("/collections/{collection_id}")
def update_collection(collection_id: str, body: CollectionUpdate):
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT * FROM collection WHERE id = ?", (collection_id,)
        ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Collection not found")

        fields = body.model_dump(exclude_none=True)
        if not fields:
            raise HTTPException(status_code=400, detail="No fields to update")

        set_clauses = ", ".join(f"{k} = ?" for k in fields)
        conn.execute(
            f"UPDATE collection SET {set_clauses} WHERE id = ?",
            list(fields.values()) + [collection_id],
        )
        conn.commit()

        updated = conn.execute(
            "SELECT * FROM collection WHERE id = ?", (collection_id,)
        ).fetchone()
        return {
            "id": updated["id"],
            "name": updated["name"],
            "description": updated["description"],
            "created_at": updated["created_at"],
        }
    finally:
        conn.close()


@router.delete("/collections/{collection_id}", status_code=204)
def delete_collection(collection_id: str):
    conn = get_connection()
    try:
        if not conn.execute(
            "SELECT id FROM collection WHERE id = ?", (collection_id,)
        ).fetchone():
            raise HTTPException(status_code=404, detail="Collection not found")
        # artifact_collection rows cascade via FK ON DELETE CASCADE
        conn.execute("DELETE FROM collection WHERE id = ?", (collection_id,))
        conn.commit()
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Artifact-collection relations
# ---------------------------------------------------------------------------

@router.post("/artifacts/{artifact_id}/collections/{collection_id}", status_code=201)
def add_artifact_to_collection(artifact_id: str, collection_id: str):
    conn = get_connection()
    try:
        if not conn.execute(
            "SELECT id FROM artifact WHERE id = ?", (artifact_id,)
        ).fetchone():
            raise HTTPException(status_code=404, detail="Artifact not found")
        if not conn.execute(
            "SELECT id FROM collection WHERE id = ?", (collection_id,)
        ).fetchone():
            raise HTTPException(status_code=404, detail="Collection not found")

        existing = conn.execute(
            "SELECT 1 FROM artifact_collection WHERE artifact_id = ? AND collection_id = ?",
            (artifact_id, collection_id),
        ).fetchone()
        if existing:
            raise HTTPException(status_code=409, detail="Artifact already in this collection")

        # Determine next sort_order within this collection
        max_order = conn.execute(
            "SELECT MAX(sort_order) FROM artifact_collection WHERE collection_id = ?",
            (collection_id,),
        ).fetchone()[0]
        sort_order = (max_order or 0) + 1

        conn.execute(
            "INSERT INTO artifact_collection (artifact_id, collection_id, sort_order) VALUES (?, ?, ?)",
            (artifact_id, collection_id, sort_order),
        )
        conn.commit()
        return {"artifact_id": artifact_id, "collection_id": collection_id, "sort_order": sort_order}
    finally:
        conn.close()


@router.delete("/artifacts/{artifact_id}/collections/{collection_id}", status_code=204)
def remove_artifact_from_collection(artifact_id: str, collection_id: str):
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT 1 FROM artifact_collection WHERE artifact_id = ? AND collection_id = ?",
            (artifact_id, collection_id),
        ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Artifact is not in this collection")
        conn.execute(
            "DELETE FROM artifact_collection WHERE artifact_id = ? AND collection_id = ?",
            (artifact_id, collection_id),
        )
        conn.commit()
    finally:
        conn.close()
