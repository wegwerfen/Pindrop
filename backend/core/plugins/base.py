from abc import ABC, abstractmethod
from dataclasses import dataclass, field


class IngestionError(Exception):
    """Raised by a content plugin when ingestion fails. Message is shown to the user."""


@dataclass
class ArtifactData:
    title: str
    excerpt: str                         # 2-3 sentence display text
    plugin_data: dict                    # plugin-specific metadata (plugin_data column)
    plugin_version: str

    # Temp file paths — role → absolute path in data/system/temp/ingest/
    # Named {artifact_id}_{role}.ext
    # Core moves these to the final artifact directory after persistence
    files: dict[str, str] = field(default_factory=dict)

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
    # task_type values to queue after core persistence: 'summarize', 'embed'


class ContentPlugin(ABC):
    plugin_id: str
    plugin_version: str
    url_patterns: list[str]

    @abstractmethod
    def ingest(self, source: str, config: dict) -> ArtifactData:
        """
        Ingest content from source (URL or file path). Blocking — runs to
        completion before returning. Write working files to
        data/system/temp/ingest/ using {artifact_id}_{role}.ext naming.
        Raise IngestionError(message) on failure.
        """

    def can_handle(self, url: str) -> bool:
        """
        Optional runtime routing override for edge cases not covered by
        url_patterns (e.g. URL shorteners, content-type detection after redirect).
        Primary routing uses url_patterns from plugin.json.
        """
        return False

    @abstractmethod
    def get_fts_text(self, artifact: dict) -> str:
        """Return the text to index for full-text search."""
