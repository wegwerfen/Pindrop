-- Pindrop initial schema
-- Migration 0001

CREATE TABLE artifact (
    id             TEXT PRIMARY KEY,           -- ULID
    plugin_type    TEXT NOT NULL,              -- which content plugin owns this

    source_url     TEXT,
    source_domain  TEXT,
    captured_at    TEXT NOT NULL,              -- datetime('now') at save time
    created_at     TEXT NOT NULL,
    updated_at     TEXT NOT NULL,

    content_path   TEXT,                       -- filesystem root for this artifact

    title          TEXT NOT NULL,
    excerpt        TEXT,                       -- short display text, plugin-generated
    thumbnail_path TEXT,

    summary        TEXT,                       -- AI-generated, nullable
    embedding_id   TEXT,                       -- reference into vector store

    user_notes     TEXT,
    is_read        INTEGER NOT NULL DEFAULT 0,
    is_archived    INTEGER NOT NULL DEFAULT 0,
    importance     INTEGER NOT NULL DEFAULT 0,

    plugin_data    TEXT,                       -- JSON, owned by the content plugin
    plugin_version TEXT
);

CREATE TABLE tag (
    id    TEXT PRIMARY KEY,                    -- ULID
    name  TEXT NOT NULL UNIQUE,
    color TEXT
);

CREATE TABLE artifact_tag (
    artifact_id TEXT NOT NULL REFERENCES artifact(id) ON DELETE CASCADE,
    tag_id      TEXT NOT NULL REFERENCES tag(id) ON DELETE CASCADE,
    source      TEXT NOT NULL,                 -- 'user', 'ai', 'plugin'
    PRIMARY KEY (artifact_id, tag_id)
);

CREATE TABLE collection (
    id          TEXT PRIMARY KEY,              -- ULID
    name        TEXT NOT NULL,
    description TEXT,
    created_at  TEXT NOT NULL
);

CREATE TABLE artifact_collection (
    artifact_id   TEXT NOT NULL REFERENCES artifact(id) ON DELETE CASCADE,
    collection_id TEXT NOT NULL REFERENCES collection(id) ON DELETE CASCADE,
    sort_order    INTEGER,
    PRIMARY KEY (artifact_id, collection_id)
);

CREATE TABLE processing_queue (
    id           TEXT PRIMARY KEY,             -- ULID
    artifact_id  TEXT NOT NULL REFERENCES artifact(id) ON DELETE CASCADE,
    task_type    TEXT NOT NULL,                -- 'summarize', 'embed', 'thumbnail', 'archive'
    status       TEXT NOT NULL DEFAULT 'pending', -- 'pending', 'running', 'done', 'failed'
    priority     INTEGER NOT NULL DEFAULT 5,   -- lower number = higher priority
    attempts     INTEGER NOT NULL DEFAULT 0,
    error        TEXT,
    created_at   TEXT NOT NULL,
    completed_at TEXT
);

CREATE TABLE user (
    id           TEXT PRIMARY KEY,             -- ULID
    display_name TEXT,
    created_at   TEXT NOT NULL,
    is_admin     INTEGER NOT NULL DEFAULT 0,
    settings     TEXT                          -- JSON, user preferences
);

CREATE TABLE auth_data (
    user_id   TEXT NOT NULL REFERENCES user(id) ON DELETE CASCADE,
    plugin_id TEXT NOT NULL,
    data      TEXT,                            -- JSON, auth-plugin-specific
    PRIMARY KEY (user_id, plugin_id)
);

CREATE TABLE plugin_registry (
    id           TEXT PRIMARY KEY,             -- e.g. 'webpage', 'reddit', 'ollama'
    category     TEXT NOT NULL,                -- 'content', 'auth', 'ingestion', 'ai', 'storage', 'processing'
    version      TEXT NOT NULL,
    display_name TEXT NOT NULL,
    built_in     INTEGER NOT NULL DEFAULT 0,
    active       INTEGER NOT NULL DEFAULT 1,
    config       TEXT                          -- JSON, current config values
);

-- Full-text search virtual table (external content — we manage inserts/deletes)
CREATE VIRTUAL TABLE artifact_fts USING fts5(
    artifact_id UNINDEXED,
    title,
    excerpt,
    summary,
    user_notes,
    tags,           -- denormalized tag names
    full_text,      -- clean extracted text content
    content=''
);

-- Indexes for common query patterns
CREATE INDEX idx_artifact_plugin_type   ON artifact(plugin_type);
CREATE INDEX idx_artifact_source_domain ON artifact(source_domain);
CREATE INDEX idx_artifact_captured_at   ON artifact(captured_at DESC);
CREATE INDEX idx_artifact_is_archived   ON artifact(is_archived);

CREATE INDEX idx_artifact_tag_tag_id    ON artifact_tag(tag_id);

CREATE INDEX idx_processing_queue_status   ON processing_queue(status, priority ASC);
CREATE INDEX idx_processing_queue_artifact ON processing_queue(artifact_id);
