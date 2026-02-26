"""
Webpage content plugin — Phase 3 implementation.
Captures web pages via Playwright, extracts content via Mozilla readability.js,
takes full-page and viewport screenshots.
"""
from core.plugins.base import ArtifactData, ContentPlugin, IngestionError


class Plugin(ContentPlugin):
    plugin_id = "webpage"
    plugin_version = "1.0.0"
    url_patterns = ["*"]

    def ingest(self, source: str, config: dict) -> ArtifactData:
        raise IngestionError("Webpage plugin not yet implemented (Phase 3)")

    def get_fts_text(self, artifact: dict) -> str:
        plugin_data = artifact.get("plugin_data") or {}
        return plugin_data.get("readable_txt", "")
