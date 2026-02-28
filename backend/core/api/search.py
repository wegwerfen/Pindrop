"""
Full-text search endpoint (FTS5 / BM25).
"""
from fastapi import APIRouter, HTTPException

from core.db import get_connection

router = APIRouter()


@router.get("/search")
def search_artifacts(q: str, limit: int = 20, offset: int = 0):
    if not q.strip():
        raise HTTPException(status_code=400, detail="Search query cannot be empty")
    if limit > 200:
        limit = 200

    conn = get_connection()
    try:
        rows = conn.execute(
            """
            SELECT
                a.id, a.plugin_type, a.title, a.excerpt,
                a.thumbnail_path, a.captured_at, a.source_url, a.source_domain,
                a.is_archived, a.is_read, a.importance,
                bm25(artifact_fts) AS rank
            FROM artifact_fts
            JOIN artifact a ON a.id = artifact_fts.artifact_id
            WHERE artifact_fts MATCH ?
              AND a.is_archived = 0
            ORDER BY rank
            LIMIT ? OFFSET ?
            """,
            (q, limit, offset),
        ).fetchall()

        if not rows:
            return []

        artifact_ids = [r["id"] for r in rows]
        placeholders = ",".join("?" * len(artifact_ids))
        tag_rows = conn.execute(
            f"""
            SELECT at.artifact_id, t.id, t.name, t.color
            FROM artifact_tag at
            JOIN tag t ON t.id = at.tag_id
            WHERE at.artifact_id IN ({placeholders})
            ORDER BY t.name
            """,
            artifact_ids,
        ).fetchall()

        tags_by_id: dict[str, list] = {aid: [] for aid in artifact_ids}
        for tag_row in tag_rows:
            tags_by_id[tag_row["artifact_id"]].append({
                "id": tag_row["id"],
                "name": tag_row["name"],
                "color": tag_row["color"],
            })

        return [
            {
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
                "rank": row["rank"],
                "tags": tags_by_id[row["id"]],
            }
            for row in rows
        ]
    finally:
        conn.close()
