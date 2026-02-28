-- Drop the contentless FTS5 table and recreate it as a regular FTS5 table.
-- content='' prevents row deletion; a regular FTS5 table stores its own copy
-- of text and supports clean rowid-based deletes and updates.

DROP TABLE IF EXISTS artifact_fts;

CREATE VIRTUAL TABLE artifact_fts USING fts5(
    artifact_id UNINDEXED,
    title,
    excerpt,
    summary,
    user_notes,
    tags,
    full_text
);
