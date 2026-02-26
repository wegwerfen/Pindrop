import fnmatch
from typing import Optional
from urllib.parse import urlparse

from .base import ContentPlugin
from .loader import PluginLoader


def _pattern_specificity(pattern: str) -> int:
    """
    Higher return value = more specific = checked first.
    Specificity is the number of literal (non-wildcard) characters.
    A pattern of pure '*' has 0 literal chars and is always checked last.
    """
    return len(pattern) - pattern.count("*")


class ContentRouter:
    def __init__(self, loader: PluginLoader):
        self._loader = loader
        # Build sorted route list: most specific patterns checked first
        routes: list[tuple[str, str]] = []
        for plugin_id, _ in loader.all_content_plugins().items():
            manifest = loader.manifest(plugin_id) or {}
            for pattern in manifest.get("url_patterns", []):
                routes.append((pattern, plugin_id))
        self._routes = sorted(routes, key=lambda r: _pattern_specificity(r[0]), reverse=True)

    def route(self, url: str) -> Optional[ContentPlugin]:
        """Return the content plugin that should handle this URL, or None."""
        normalized = self._normalize(url)

        # 1. Static pattern matching (most specific first)
        for pattern, plugin_id in self._routes:
            if fnmatch.fnmatch(normalized, pattern):
                plugin = self._loader.get_content_plugin(plugin_id)
                if plugin:
                    return plugin

        # 2. Fallback: ask each plugin's optional can_handle()
        for plugin in self._loader.all_content_plugins().values():
            if plugin.can_handle(url):
                return plugin

        return None

    @staticmethod
    def _normalize(url: str) -> str:
        """
        Strip scheme and leading www. for pattern matching.
        'https://www.reddit.com/r/ml/comments/abc' → 'reddit.com/r/ml/comments/abc'
        """
        parsed = urlparse(url)
        host = (parsed.netloc or "").lower().removeprefix("www.")
        return host + parsed.path
