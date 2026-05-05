"""Handler for azoresacores.com — WordPress news site with flat permalinks.

99.7% extraction_failed:None from archive — URLs are 2-segment attachment pages
with zero-width spaces in path (e.g., /​​​​​​​article-slug/image-name/).
Real articles use single-segment flat permalinks.
NOTE: Requires CDX re-scan.
"""
from urllib.parse import urlparse

from .base import SKIP_SEGMENTS, BaseSiteHandler

_EXTRA_SKIP = {"category", "categoria", "tag", "author", "search"}


class AzoresAcoresHandler(BaseSiteHandler):
    DOMAINS = ["azoresacores.com", "www.azoresacores.com"]
    NAME = "azoresacores"

    def is_article_url(self, url: str) -> bool:
        parsed = urlparse(url)
        path = parsed.path.strip("/")

        # Remove zero-width spaces (common in this site's URLs)
        path = path.replace("\u200b", "")

        if not path:
            return False

        lower = path.lower()
        if any(lower.endswith(ext) for ext in (".jpg", ".png", ".gif", ".css", ".js", ".xml", ".json", ".pdf", ".ico")):
            return False

        parts = [p for p in lower.split("/") if p]

        if any(p in SKIP_SEGMENTS or p in _EXTRA_SKIP for p in parts):
            return False

        # Accept single-segment article slugs only
        if len(parts) == 1:
            slug = parts[0]
            return len(slug) > 15 and "-" in slug

        return False
