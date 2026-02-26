"""
Webpage content plugin.

Fetches and archives web pages using Playwright (single browser session).
Mozilla readability.js extracts clean article content and metadata.
Takes a full-page screenshot and a viewport screenshot for the card thumbnail.
"""
from pathlib import Path

from core.plugins.base import ArtifactData, ContentPlugin, IngestionError

_PLUGIN_DIR = Path(__file__).parent
_READABILITY_JS = _PLUGIN_DIR / "readability.js"


class Plugin(ContentPlugin):
    plugin_id = "webpage"
    plugin_version = "1.0.0"
    url_patterns = ["*"]

    def ingest(self, source: str, artifact_id: str, temp_dir: Path, config: dict) -> ArtifactData:
        from playwright.sync_api import Error as PlaywrightError
        from playwright.sync_api import TimeoutError as PlaywrightTimeout
        from playwright.sync_api import sync_playwright

        temp_dir = Path(temp_dir)
        temp_dir.mkdir(parents=True, exist_ok=True)

        readability_src = _READABILITY_JS.read_text(encoding="utf-8")

        raw_html = ""
        article = None
        final_url = source
        files: dict[str, str] = {}

        try:
            with sync_playwright() as p:
                browser = p.chromium.launch()
                page = browser.new_page(viewport={"width": 1280, "height": 800})

                try:
                    page.goto(source, wait_until="networkidle", timeout=30_000)
                except PlaywrightTimeout:
                    # Heavy or slow pages — fall back to DOMContentLoaded
                    try:
                        page.goto(source, wait_until="domcontentloaded", timeout=30_000)
                    except (PlaywrightTimeout, PlaywrightError) as exc:
                        raise IngestionError(f"Page failed to load: {exc}") from exc

                final_url = page.url
                raw_html = page.content()

                # Inject readability.js as a script tag, then extract article
                page.add_script_tag(content=readability_src)
                article = page.evaluate("""
                    () => {
                        try {
                            const reader = new Readability(document.cloneNode(true));
                            return reader.parse();
                        } catch (e) {
                            return null;
                        }
                    }
                """)

                # Published date from common meta tags
                published = page.evaluate("""
                    () => {
                        const sel = [
                            'meta[property="article:published_time"]',
                            'meta[property="og:article:published_time"]',
                            'meta[name="date"]',
                            'meta[name="DC.date"]',
                        ].join(', ');
                        const el = document.querySelector(sel);
                        return el ? el.getAttribute('content') : null;
                    }
                """)

                # Viewport screenshot — always taken, required for the card thumbnail
                thumbnail_path = temp_dir / f"{artifact_id}_thumbnail.jpg"
                page.screenshot(
                    path=str(thumbnail_path),
                    full_page=False,
                    type="jpeg",
                    quality=85,
                )
                files["thumbnail"] = str(thumbnail_path)

                # Full-page screenshot — optional, controlled by save_screenshot setting
                if config.get("save_screenshot", True):
                    screenshot_path = temp_dir / f"{artifact_id}_screenshot.jpg"
                    page.screenshot(
                        path=str(screenshot_path),
                        full_page=True,
                        type="jpeg",
                        quality=85,
                    )
                    files["screenshot"] = str(screenshot_path)

                browser.close()

        except IngestionError:
            raise
        except Exception as exc:
            raise IngestionError(f"Unexpected error loading page: {exc}") from exc

        # --- Write archived files ---

        raw_html_path = temp_dir / f"{artifact_id}_raw_html.html"
        raw_html_path.write_text(raw_html, encoding="utf-8")
        files["raw_html"] = str(raw_html_path)

        # Extract content from readability result
        if article:
            title = (article.get("title") or "").strip() or source
            excerpt = (article.get("excerpt") or "").strip()
            readable_html = article.get("content") or ""
            readable_txt = article.get("textContent") or ""
            byline = (article.get("byline") or "").strip()
            site_name = (article.get("siteName") or "").strip()
            lang = (article.get("lang") or "").strip()
        else:
            # Readability couldn't parse — fall back to raw values
            title = source
            excerpt = ""
            readable_html = ""
            readable_txt = ""
            byline = ""
            site_name = ""
            lang = ""

        if readable_html:
            readable_html_path = temp_dir / f"{artifact_id}_readable_html.html"
            readable_html_path.write_text(readable_html, encoding="utf-8")
            files["readable_html"] = str(readable_html_path)

        if readable_txt:
            readable_txt_path = temp_dir / f"{artifact_id}_readable_txt.txt"
            readable_txt_path.write_text(readable_txt, encoding="utf-8")
            files["readable_txt"] = str(readable_txt_path)

        if config.get("save_markdown") and readable_html:
            try:
                from markdownify import markdownify
                markdown = markdownify(readable_html, heading_style="ATX")
                markdown_path = temp_dir / f"{artifact_id}_markdown.md"
                markdown_path.write_text(markdown, encoding="utf-8")
                files["markdown"] = str(markdown_path)
            except ImportError:
                pass

        # --- Build plugin_data ---

        word_count = len(readable_txt.split()) if readable_txt else 0
        plugin_data: dict = {
            "byline": byline,
            "site_name": site_name,
            "lang": lang,
            "word_count": word_count,
        }
        if published:
            plugin_data["published"] = published
        if final_url != source:
            plugin_data["canonical_url"] = final_url

        return ArtifactData(
            title=title,
            excerpt=excerpt,
            plugin_data=plugin_data,
            plugin_version=self.plugin_version,
            files=files,
            queue_tasks=["summarize", "embed"],
        )

    def get_fts_text(self, artifact: dict) -> str:
        content_path = artifact.get("content_path")
        if not content_path:
            return ""
        txt_file = Path(content_path) / "processed" / "readable.txt"
        if txt_file.exists():
            return txt_file.read_text(encoding="utf-8")
        return ""
