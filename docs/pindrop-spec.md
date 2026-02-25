# Pindrop — Project Specification
**Version:** 0.3 (Draft)
**Status:** Pre-development
**Last Updated:** February 2026

---

## Vision

Pindrop is a self-hosted, open-source personal knowledge archive — an internet archaeology tool for collecting, preserving, and rediscovering the web content that matters to you. It captures bookmarks, pages, images, notes, and any other content type via a plugin system, enriches them with AI-generated summaries, tags, and semantic search, and surfaces them through a fluid, visual interface.

The core philosophy: your data is yours. Pindrop works without AI, without a subscription, and without an internet connection. AI is an enhancement layer, not a dependency. Every artifact you save is exportable, readable, and usable outside the application.

---

## Design Principles

**Modularity over monolith.** Every content type, auth strategy, ingestion source, and AI provider is a plugin. The core system is type-agnostic. New capabilities are added without touching existing code.

**Data sovereignty.** All content is stored locally. Export is a first-class feature, not an afterthought. Open formats wherever possible.

**Graceful degradation.** The full experience is available with AI. A complete and useful experience is available without it. Users choose their level of complexity.

**Zero new habits required.** Ingestion meets users where they already are — email, browser, Reddit saves, Twitter bookmarks. The system comes to the user.

**Built for others.** Opinionated enough to have a clear identity, configurable enough to serve different users and deployment contexts.

---

## The Interface

### Layout

A single-page application with three primary areas:

**Sidebar** — navigation, collections, tag browser, plugin status, settings access.

**Main grid** — a masonry card layout showing all artifacts. Each card is rendered by its content plugin, but always shows a thumbnail or type icon, title, short excerpt, and tags. The grid is the primary browsing surface.

**Search / chat bar** — persistent, at the top. Handles keyword search, filtered browsing, semantic search, and AI chat against your collection. One input, multiple modes.

### Card Interaction

Typing in the search bar filters the grid in real time. Cards animate smoothly — irrelevant cards exit, remaining cards reorder by relevance, sliding into place. Framer Motion handles this. The effect is the collection feeling alive rather than static.

Clicking a card expands it in place using a shared element transition — the card grows to fill the detail view, spatial context is preserved, the grid is dimly visible behind it. The detail view shows full archived content, multiple format tabs (text, markdown, PDF, screenshot depending on type and settings), AI summary, tags, related artifacts, and user notes. The plugin contributes a type-specific section for data unique to that content type.

### Drag and Drop Ingestion

Drag and drop is the primary, zero-configuration ingestion method. No plugins to configure, no new habits to form — drop something onto the grid and it's captured.

The entire main grid area is a drop target. When something is dragged over the window a subtle overlay appears. On drop, the system detects what was dropped and routes it automatically:

```
something dropped
  ├── URL string → domain extracted → content plugin router → best match
  ├── file → MIME type + extension → content plugin router
  │     ├── image/* → image plugin
  │     ├── application/pdf → pdf plugin
  │     ├── text/markdown, text/plain → document plugin
  │     ├── application/json → inspect structure → maybe chat export?
  │     └── unrecognized → generic file plugin, user can reassign
  └── browser link drag → extract URL → treat as URL drop
```

After a drop, a quick capture overlay appears confirming what was detected — "Webpage: example.com/article" or "PDF: filename.pdf" — with a single optional note field for capture-time context. Dismiss to skip, or add a line about why you saved it. This is the moment to capture intent. Then ingestion proceeds.

If the plugin router guesses the type wrong, the user can reassign from the detail view.

### Search and Chat

Search filters the card grid live. Semantic search runs in parallel with keyword search; results are scored and merged, cards reorder accordingly.

A slide-in chat panel handles natural language queries — "what did I save about selective layer training?" generates a response grounded in your artifacts, with cited cards that are clickable inline. If collection coverage is thin on a topic, external search results appear as visually distinct cards in the grid or as cited sources in the chat panel.

---

## Tech Stack

### Backend
**Python + FastAPI**

Python's content processing ecosystem (scraping, PDF extraction, image processing, Readability, AI/ML libraries) is more mature than Node equivalents and directly relevant to this use case. FastAPI provides async support, automatic API documentation, and clean type hints that make coding agent assistance more effective.

The backend runs in a Python virtual environment (venv) to isolate dependencies from the host system. Plugin dependencies install into this same venv — each plugin ships a `requirements.txt` and the installer runs `pip install -r requirements.txt` when a plugin is added.

### Frontend
**Vite + React + Tailwind CSS + shadcn/ui**

Vite for fast builds and clean SPA architecture without framework overhead. React for broad ecosystem support and best-in-class coding agent output quality. Tailwind + shadcn/ui solves the CSS problem — pre-built, well-designed components that are owned (copied, not imported as a dependency), with utility classes instead of hand-written CSS. Framer Motion for card animations.

### Database
**SQLite** (core data + FTS5 + sqlite-vec for embeddings)

Self-hosted single-file database. No separate database server to run or maintain. Trivially portable and backupable. sqlite-vec keeps vector embeddings inside the same file. For future hosted/multi-user deployments, migration path to PostgreSQL + pgvector is clean.

### Filesystem
Archived content, images, thumbnails, and processed derivatives stored on the local filesystem. Database holds metadata and paths. Large content never goes in the database.

### AI Layer
Abstracted behind a provider interface. Built-in support for Ollama (local), OpenAI, and Anthropic APIs. Users choose their provider or run without AI entirely. AI is a processing plugin category, not a core dependency.

---

## Data Model

### Core Tables

```sql
CREATE TABLE artifact (
  id             TEXT PRIMARY KEY,   -- ULID
  plugin_type    TEXT NOT NULL,      -- which content plugin owns this

  source_url     TEXT,
  source_domain  TEXT,
  captured_at    TEXT NOT NULL,
  created_at     TEXT NOT NULL,
  updated_at     TEXT NOT NULL,

  content_path   TEXT,               -- filesystem root for this artifact

  title          TEXT NOT NULL,
  excerpt        TEXT,               -- short display text, plugin-generated
  thumbnail_path TEXT,

  summary        TEXT,               -- AI-generated, nullable
  embedding_id   TEXT,               -- reference into vector store

  user_notes     TEXT,               -- user's own notes
  is_read        INTEGER DEFAULT 0,
  is_archived    INTEGER DEFAULT 0,
  importance     INTEGER DEFAULT 0,

  plugin_data    TEXT,               -- JSON, owned by the content plugin
  plugin_version TEXT
);

CREATE TABLE tag (
  id    TEXT PRIMARY KEY,
  name  TEXT NOT NULL UNIQUE,
  color TEXT
);

CREATE TABLE artifact_tag (
  artifact_id TEXT REFERENCES artifact(id),
  tag_id      TEXT REFERENCES tag(id),
  source      TEXT,                  -- 'user', 'ai', 'plugin'
  PRIMARY KEY (artifact_id, tag_id)
);

CREATE TABLE collection (
  id          TEXT PRIMARY KEY,
  name        TEXT NOT NULL,
  description TEXT,
  created_at  TEXT NOT NULL
);

CREATE TABLE artifact_collection (
  artifact_id   TEXT REFERENCES artifact(id),
  collection_id TEXT REFERENCES collection(id),
  sort_order    INTEGER,
  PRIMARY KEY (artifact_id, collection_id)
);

CREATE TABLE processing_queue (
  id           TEXT PRIMARY KEY,
  artifact_id  TEXT REFERENCES artifact(id),
  task_type    TEXT NOT NULL,        -- 'summarize', 'embed', 'thumbnail', 'archive'
  status       TEXT DEFAULT 'pending',
  priority     INTEGER DEFAULT 5,
  attempts     INTEGER DEFAULT 0,
  error        TEXT,
  created_at   TEXT NOT NULL,
  completed_at TEXT
);

CREATE TABLE user (
  id           TEXT PRIMARY KEY,
  display_name TEXT,
  created_at   TEXT NOT NULL,
  is_admin     INTEGER DEFAULT 0,
  settings     TEXT                  -- JSON, user preferences
);

CREATE TABLE auth_data (
  user_id   TEXT REFERENCES user(id),
  plugin_id TEXT,
  data      TEXT,                    -- JSON, auth-plugin-specific
  PRIMARY KEY (user_id, plugin_id)
);

-- Full-text search virtual table
CREATE VIRTUAL TABLE artifact_fts USING fts5(
  artifact_id UNINDEXED,
  title,
  excerpt,
  summary,
  user_notes,
  tags,                              -- denormalized tag names
  full_text,                         -- clean extracted text content
  content=''
);
```

### Plugin Registry Table

```sql
CREATE TABLE plugin_registry (
  id          TEXT PRIMARY KEY,      -- e.g. 'webpage', 'reddit', 'ollama'
  category    TEXT NOT NULL,         -- 'content', 'auth', 'ingestion', 'ai', 'storage', 'processing'
  version     TEXT NOT NULL,
  display_name TEXT NOT NULL,
  built_in    INTEGER DEFAULT 0,
  active      INTEGER DEFAULT 1,
  config      TEXT                   -- JSON, current config values
);
```

### plugin_data Examples

**Webpage plugin:**
```json
{
  "canonical_url": "https://example.com/article",
  "byline": "Author Name",
  "site_name": "Example Site",
  "lang": "en",
  "published": "2024-03-15",
  "word_count": 2400
}
```
`canonical_url` is only present if it differs from `source_url` (e.g. after redirects). Presence of archived files is determined by the artifact directory contents, not boolean flags.

**AI chat plugin:**
```json
{
  "platform": "claude",
  "model": "claude-sonnet-4-6",
  "message_count": 47,
  "participants": ["user", "assistant"],
  "turns": [
    { "role": "user", "content": "...", "timestamp": "..." },
    { "role": "assistant", "content": "...", "timestamp": "..." }
  ],
  "topic_summary": "Pindrop architecture discussion"
}
```

**Reddit plugin:**
```json
{
  "subreddit": "MachineLearning",
  "score": 1842,
  "comment_count": 94,
  "post_type": "link",
  "flair": "Research"
}
```

**YouTube plugin:**
```json
{
  "channel": "Computerphile",
  "duration_seconds": 847,
  "view_count": 284000,
  "transcript_available": true
}
```

**Image plugin:**
```json
{
  "image_count": 3,
  "images": [
    { "filename": "photo1.jpg", "width": 3024, "height": 4032, "exif": { "camera": "iPhone 15", "taken": "2024-03-15T14:22:00" } },
    { "filename": "photo2.jpg", "width": 3024, "height": 4032, "exif": {} },
    { "filename": "photo3.jpg", "width": 3024, "height": 4032, "exif": {} }
  ]
}
```
Single-image artifacts have `image_count: 1`. The card always shows `thumbnail` (first image). Album members are stored as `image_0`, `image_1`, etc. in the artifact directory.

---

## Filesystem Structure

```
data/
  users/
    {user_id}/                       -- 'default' for single-user instances
      artifacts/
        {artifact_id}/
          raw/                       -- original captured content, never modified
            original.html
            original.pdf
          processed/                 -- plugin-generated derivatives
            readable.html            -- Readability-extracted clean HTML
            readable.txt             -- plain text, feeds FTS index
            markdown.md              -- optional, if enabled in settings
          assets/                    -- images referenced by the page
            {hash}.webp
          screenshot.webp
          thumbnail.webp
          image_0.webp               -- image plugin: album members, in order
          image_1.webp

  system/
    temp/
      ingest/                        -- plugin working files during ingestion
        {artifact_id}_raw.html       -- named {artifact_id}_{role}.ext
        {artifact_id}_thumbnail.webp -- cleared after core moves to final location

    plugins/                         -- installed plugin packages
      built-in/
        content/
          webpage/
            plugin.json              -- manifest
            plugin.py                -- plugin implementation
            requirements.txt         -- python dependencies (playwright, etc.)
            readability.js           -- bundled mozilla readability
            frontend.json            -- frontend display configuration
          note/
          image/
          reddit/
        auth/
          single-user/
        ingestion/
          email/
          browser-extension/
        ai/
          ollama/
          openai/
          anthropic/
        processing/
          summarize/
          embed/
          thumbnail/
        storage/
          local-filesystem/
      installed/                     -- third-party plugins
    cache/
```

The `raw/` folder is the original artifact — untouched, permanent. The `processed/` folder is derived and can be regenerated. This separation supports future pipeline improvements without data loss.

`data/system/temp/ingest/` is a staging area used during ingestion. Plugins write working files here; the core moves them to the final artifact directory after persistence and clears the temp files.

---

## Repository Structure

```
Pindrop/
  backend/                           -- Python + FastAPI
    venv/                            -- gitignored, created on first setup
    core/                            -- core application code
    plugins/
      built-in/                      -- ships with the repository
        content/
          webpage/
          note/
          image/
          ...
        auth/
        ingestion/
        ai/
        processing/
        storage/
      installed/                     -- gitignored, third-party plugins added at runtime
    requirements.txt                 -- core backend dependencies

  frontend/                          -- Vite + React
    src/
      ...

  data/                              -- gitignored, all runtime data
  docs/
    pindrop-spec.md
```

The `backend/plugins/built-in/` directory is the source of truth for both backend logic and frontend display configs. The frontend build process reads `frontend.json` files from plugin directories to wire up the plugin registry at build time.

---

## Plugin System

### Plugin Categories

| Category | Purpose | Examples |
|---|---|---|
| content | Define pin types — ingest, normalize, display | webpage, note, image, reddit, youtube, pdf |
| auth | Handle identity and access control | single-user, local-multiuser, supertokens, oauth |
| ingestion | Capture pipelines from external sources | email, browser-extension, reddit-sync, twitter-sync |
| ai | Provide AI capabilities (summarize, embed, chat) | ollama, openai, anthropic |
| processing | Background queue tasks | summarize, embed, thumbnail, archive |
| storage | Where and how content is stored | local-filesystem, s3-compatible |

### Plugin Manifest (plugin.json)

Every plugin declares itself via a manifest. The core reads this without loading the plugin code.

```json
{
  "id": "reddit",
  "version": "1.0.0",
  "category": "content",
  "display_name": "Reddit",
  "description": "Save Reddit posts with metadata, scores, and comments",
  "author": "",
  "url_patterns": ["reddit.com/r/*/comments/*", "redd.it/*"],
  "has_frontend": true,
  "config_schema": {
    "save_comments": { "type": "boolean", "default": false, "label": "Save top comments" },
    "comment_depth": { "type": "integer", "default": 3, "label": "Comment depth" }
  },
  "dependencies": ["praw"]
}
```

The `config_schema` allows the settings UI to render configuration forms for any plugin without knowing its internals.

`dependencies` lists Python packages for documentation purposes. Plugins also ship a `requirements.txt`; the installer runs `pip install -r requirements.txt` into the backend venv when a plugin is added. `has_frontend` indicates the plugin includes a `frontend.json` defining its card and detail view presentation.

### Content Plugin Interface

A content plugin must implement:

```python
class ContentPlugin:
    plugin_id: str
    plugin_version: str
    url_patterns: list[str]

    def ingest(self, source: str, config: dict) -> ArtifactData:
        """
        Ingest content from source (URL or file path). Blocking — runs to
        completion before returning. Write working files to
        data/system/temp/ingest/ using {artifact_id}_{role}.ext naming.
        Core moves files to the final artifact directory after persistence
        and clears temp files.
        Raise IngestionError(message) on failure — core surfaces reason to user.
        """

    def can_handle(self, url: str) -> bool:
        """
        Optional runtime routing override for edge cases not covered by
        url_patterns (e.g. URL shorteners, content-type detection after
        redirect). Primary routing uses url_patterns from plugin.json.
        """

    def get_fts_text(self, artifact: Artifact) -> str:
        """Return the text to index for full-text search."""
```

`ArtifactData` is the normalized return contract:

```python
@dataclass
class ArtifactData:
    title: str
    excerpt: str                     # 2-3 sentence display text
    plugin_data: dict                # plugin-specific metadata (maps to plugin_data column)
    plugin_version: str

    # Temp file paths — role → absolute path in data/system/temp/ingest/
    # Named {artifact_id}_{role}.ext
    # Core reads these, moves to final artifact directory, deletes temp files
    files: dict[str, str]
    # Standard file roles:
    #   'raw_html'       — original fetched HTML
    #   'readable_html'  — Readability-extracted clean HTML
    #   'readable_txt'   — plain text, feeds FTS index
    #   'markdown'       — markdown conversion (if enabled in settings)
    #   'screenshot'     — full-page screenshot
    #   'thumbnail'      — viewport/cover image for card display
    #   'pdf'            — PDF file
    #   'image_0'..'image_N' — image/album members (image plugin), in order

    suggested_tags: list[str] = field(default_factory=list)
    queue_tasks: list[str] = field(default_factory=list)
    # task_type values to queue after core persistence:
    #   'summarize', 'embed'
    # (thumbnail, readability, screenshot done synchronously by the plugin)
```

The plugin never touches the main database or artifact directories. It writes working files to `data/system/temp/ingest/` and returns `ArtifactData`; the core handles all persistence and cleanup.

### Auth Plugin Interface

```python
class AuthPlugin:
    plugin_id: str

    def authenticate(self, request) -> AuthResult:
        """Validate request and return user_id or reject."""

    def get_middleware(self):
        """Return ASGI middleware for request authentication."""

    def create_user(self, details: dict) -> str:
        """Create a new user, return user_id."""

    def get_user(self, user_id: str) -> dict:
        """Return user record."""
```

The single-user auth plugin returns a hardcoded `default` user for every request. Multi-user plugins check credentials. The core never knows which is active.

### AI Plugin Interface

```python
class AIPlugin:
    plugin_id: str

    def summarize(self, text: str, context: dict) -> str:
        """Generate a summary of the provided text."""

    def embed(self, text: str) -> list[float]:
        """Return a vector embedding for semantic search."""

    def chat(self, messages: list[dict], context_artifacts: list) -> str:
        """Respond to a chat query grounded in provided artifacts."""
```

### Processing Plugin Interface

Processing plugins are queue task handlers:

```python
class ProcessingPlugin:
    plugin_id: str
    task_type: str

    def process(self, artifact_id: str, config: dict) -> ProcessingResult:
        """Execute processing task for the given artifact."""
```

### Frontend Plugin System

Content plugins define their frontend presentation through a `frontend.json` file alongside `plugin.json`. The core frontend reads this configuration and renders accordingly — most plugins require no custom React code.

#### frontend.json

```json
{
  "card": {
    "icon": "globe",
    "accent": "#4A90D9"
  },
  "detail": {
    "tabs": [
      { "label": "Article",    "role": "readable_html", "type": "html" },
      { "label": "Raw Text",   "role": "readable_txt",  "type": "text" },
      { "label": "Markdown",   "role": "markdown",      "type": "markdown", "editable": true },
      { "label": "Screenshot", "role": "screenshot",    "type": "image" },
      { "label": "PDF",        "role": "pdf",           "type": "pdf" }
    ],
    "metadata_fields": [
      { "label": "Author",    "key": "byline" },
      { "label": "Site",      "key": "site_name" },
      { "label": "Published", "key": "published" },
      { "label": "Words",     "key": "word_count" },
      { "label": "Language",  "key": "lang" }
    ]
  }
}
```

`tabs` maps to files stored in the artifact directory via the `role` key. Only tabs whose corresponding file exists are shown. `editable: true` enables an edit mode for text-based tab types. `metadata_fields` maps `plugin_data` keys to display labels in the right panel.

#### Detail View Layout

The detail view is shared chrome rendered by the core. Plugins declare their content; the core handles layout, tab switching, and interaction.

```
┌─────────────────────────────────────────────────────┐
│  [Tab 1] [Tab 2] [Tab 3] ...                         │  tab bar (from frontend.json tabs)
│                                    │                 │
│                                    │  Title          │
│   Main content area (3/4 width)    │  URL            │
│   Renders active tab content:      │  Captured       │
│     html | text | markdown         │  Tags           │
│     image | image_gallery          │  Notes          │
│     pdf | json                     │  ─────          │
│                                    │  [plugin fields]│
│                                    │  (1/4 width)    │
├─────────────────────────────────────────────────────┤
│  [Close]  [Archive]  [Delete]  [Export]              │  button bar (core)
└─────────────────────────────────────────────────────┘
```

#### Core Renderer Types

| Type | Description | Notes |
|---|---|---|
| `html` | Rendered HTML content | |
| `text` | Plain text, monospace | `editable: true` supported |
| `markdown` | Rendered markdown | `editable: true` supported |
| `json` | Syntax-highlighted JSON | `editable: true` supported |
| `image` | Single image | |
| `image_gallery` | One or more images | Navigation controls appear for > 1 image |
| `pdf` | PDF viewer | |

#### Custom Components (Escape Hatch)

For content types with fundamentally different interaction models, `frontend.json` can declare a custom component name:

```json
{
  "detail": {
    "custom_component": "MyPluginDetail"
  }
}
```

The plugin then ships a pre-compiled `frontend.js` bundle. The backend serves it as a static file; the frontend dynamically imports it on startup. Custom components may only use libraries already bundled in the core frontend (React, Tailwind CSS, shadcn/ui, Framer Motion) — no additional npm dependencies are permitted.

Built-in plugins with custom interaction models (e.g. `ai-chat`) have their detail components built directly into the core frontend rather than loading dynamically.

---

## Search Architecture

Search is layered. Each layer adds capability; none is required for the system to function.

**Layer 1 — Structured filtering** (always available)  
SQL queries against indexed columns: plugin_type, date range, source_domain, tag, collection, is_read, is_archived. Fast, precise, no configuration needed.

**Layer 2 — Full-text search** (always available, SQLite FTS5)  
Keyword search across title, excerpt, summary, user_notes, tags, and full cleaned text content. Relevance ranked. This is the default search path and is genuinely capable without AI.

**Layer 3 — Semantic search** (requires AI plugin)  
Vector similarity search using stored embeddings. Handles conceptual queries where keywords don't match. Runs in parallel with FTS; scores are normalized and merged. Pre-computed embeddings mean search itself is fast even though embedding generation is async.

**Layer 4 — AI chat** (requires AI plugin)  
Natural language queries generate responses grounded in your artifacts. Top semantic search results become the context window. Response cites specific artifacts as cards. External search results supplement when collection coverage is thin.

### Query Flow

```
user input
  ├── short / keyword-shaped  →  weight toward FTS
  ├── long / natural language  →  weight toward semantic + chat
  └── structured filter terms  →  apply as SQL constraints

FTS search  ────────┐
Semantic search  ───┼──→  score normalization  →  merged ranked results
Structured filters ─┘                                      ↓
                                              cards animate into order
```

---

## Ingestion Pipeline

```
source (drag & drop / email / browser extension / API / manual)
  ↓
type detection (MIME type, extension, URL pattern, or ingestion plugin)
  ↓
content plugin router (which plugin handles this URL/type?)
  ↓
[optional] capture overlay (confirm detected type, add capture-time note)
  ↓
UI shows spinner (card placeholder in grid)
  ↓
content plugin ingest() — blocking, runs to completion
  plugin writes working files to data/system/temp/ingest/
  ↓
core persistence
  moves temp files to final artifact directory
  writes artifact record to database
  queues AI processing tasks (summarize, embed)
  clears temp files
  ↓
artifact card appears in UI (fully populated)
  ↓
processing queue — async, runs in background
  summarize → embed → fts index
  card updates as enrichment completes
```

`ingest()` is blocking — the card does not appear until the plugin finishes. The UI shows a spinner in the drop zone during ingestion. For most content types this takes a few seconds; Playwright-based ingestion (webpage, screenshot) may take longer. AI enrichment is always async and fills in after the card is visible.

---

## User Settings

Settings are stored as JSON in the user record. The UI renders configuration forms from plugin config schemas automatically — no hardcoded settings UI per plugin.

Key global settings:

```json
{
  "storage": {
    "save_raw_html": true,
    "save_readable_html": true,
    "save_plain_text": true,
    "save_markdown": false,
    "save_screenshot": true,
    "save_assets": true,
    "thumbnail_width": 400,
    "thumbnail_height": 300
  },
  "ai": {
    "active_provider": "ollama",
    "auto_summarize": true,
    "auto_tag": true,
    "auto_embed": true
  },
  "ui": {
    "card_size": "medium",
    "default_sort": "captured_at_desc",
    "show_archived": false
  }
}
```

---

## Built-in Plugins (v1 Targets)

### Content
- **webpage** — fetch and archive via Playwright (single browser session); Mozilla readability.js extracts clean text, readable HTML, and metadata (title, byline, excerpt, site name, language); full-page and viewport screenshots; produces raw HTML, readable HTML, plain text, optional markdown, full-page screenshot, and thumbnail
- **note** — plain text and markdown notes, locally created
- **image** — single image or small album (1–N images); EXIF extraction per image; card shows first image as thumbnail with count indicator for albums
- **pdf** — upload or URL, text extraction, page thumbnail
- **document** — structured files (markdown, Word, code files); format detection, text extraction for FTS, appropriate rendering. Covers generated outputs, exports, and local files without a source URL
- **ai-chat** — archive conversations from Claude, ChatGPT, and other AI platforms; preserves turn structure, renders as transcript, fully searchable across platforms

### Auth
- **single-user** — no authentication, localhost-appropriate default

### Ingestion
- **email** — dedicated receive address, parse URLs and body text as capture-time notes
- **browser-extension** — one-click save from browser, push to API

### AI
- **ollama** — local model inference, zero ongoing cost
- **openai** — API-based, higher quality, usage cost
- **anthropic** — API-based alternative

### Processing
- **summarize** — generate artifact summary from clean text
- **embed** — generate and store vector embedding
- **thumbnail** — generate or extract thumbnail image

### Storage
- **local-filesystem** — default, stores under data/users/{user_id}/

---

## Roadmap

### Phase 1 — Core Foundation
- SQLite schema and migrations
- FastAPI backend with plugin registry and loader
- Content plugin interface + webpage plugin (first reference implementation)
- Filesystem structure and storage plugin
- Single-user auth plugin
- Basic REST API (CRUD for artifacts, tags, collections)
- Vite + React frontend scaffold with Tailwind + shadcn
- Card grid with masonry layout
- **Drag and drop ingestion** — primary capture method, works at launch, type detection via MIME/extension, capture-time note overlay
- Detail view with shared element transition (Framer Motion)

### Phase 2 — Search and Processing
- FTS5 integration and indexing pipeline
- Processing queue (async background tasks)
- Summarize and thumbnail processing plugins
- Search bar with live card filtering and animation
- Ollama AI plugin + embed processing plugin
- Semantic search + score merging

### Phase 3 — Ingestion
- Email ingestion plugin
- Browser extension
- Reddit sync ingestion plugin
- Manual API ingestion endpoint (for scripts and automation)

### Phase 4 — Chat and External Search
- AI chat panel (slide-in)
- Chat grounded in artifact context with card citations
- External search result integration

### Phase 5 — Additional Content Types and Auth
- PDF content plugin
- Image content plugin
- Note content plugin
- Document content plugin (markdown, Word, code files, generated outputs)
- Local multi-user auth plugin
- YouTube plugin (stretch)
- Reddit post content plugin
- **AI chat archive plugin** — ingest and archive conversations from Claude, ChatGPT, and other platforms; batch import via platform export files (ChatGPT JSON export etc.); browser extension capture for platforms without export; transcript detail view; semantic search across all archived AI conversations

### Phase 6 — Community and Polish
- Plugin packaging and installation from external sources
- Plugin developer documentation
- Export tooling (full archive as portable zip)
- Import from Raindrop, Pocket, browser bookmarks

---

## Open Questions

- **Vector store** — sqlite-vec (preferred, single-file story) vs ChromaDB (more capable but separate process). Decide when Phase 2 begins.
- **Card expansion animation** — shared element transition vs slide-in panel. Prototype both before committing.
- **External search integration** — which provider(s), how to handle rate limits, whether to make it a plugin.
- **Plugin distribution** — how third-party plugins are discovered, vetted, installed. A registry? GitHub topic tag? Later concern.
- **Multi-user migration path** — how to handle reassigning artifacts from the default user when enabling multi-user auth. Needs a migration tool.

---

*This document is the living spec for Pindrop. Update it as decisions are made and the design evolves. It is the primary context document for coding agent sessions.*
