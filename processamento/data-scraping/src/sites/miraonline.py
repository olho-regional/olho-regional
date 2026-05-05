"""Handler for miraonline.pt — WordPress news site with flat permalinks.

82.6% extraction_failed:None from archive — 2-segment attachment pages
(article-slug/image-filename). Uses emoji prefixes in article slugs.
Real articles use single-segment flat permalinks.
NOTE: Requires CDX re-scan.
"""
from urllib.parse import urlparse

from .base import SKIP_SEGMENTS, BaseSiteHandler

_EXTRA_SKIP = {"category", "categoria", "tag", "author", "search"}


class MiraOnlineHandler(BaseSiteHandler):
    DOMAINS = ["miraonline.pt", "www.miraonline.pt"]
    NAME = "miraonline"

    def is_article_url(self, url: str) -> bool:
        parsed = urlparse(url)
        path = parsed.path.lower().strip("/")

        if not path:
            return False

        if any(path.endswith(ext) for ext in (".jpg", ".png", ".gif", ".css", ".js", ".xml", ".json", ".pdf", ".ico")):
            return False

        parts = [p for p in path.split("/") if p]

        if any(p in SKIP_SEGMENTS or p in _EXTRA_SKIP for p in parts):
            return False

        # Accept single-segment article slugs only
        if len(parts) == 1:
            slug = parts[0]
            return len(slug) > 15 and "-" in slug

        return False
