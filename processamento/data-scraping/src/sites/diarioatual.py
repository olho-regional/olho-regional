"""Handler for diarioatual.com — WordPress news site with flat permalinks.

100% text_too_short errors — all 839 errors are 2-segment WordPress attachment
pages (article-slug/gallery-image). URL patterns show photo gallery sub-pages:
  /14a-maratona-btt-rota-do-presunto-em-imagens/ (242 errors for one gallery!)
Real articles use single-segment flat permalinks.
NOTE: Requires CDX re-scan.
"""
from urllib.parse import urlparse

from .base import SKIP_SEGMENTS, BaseSiteHandler

_EXTRA_SKIP = {"category", "categoria", "tag", "author", "search"}


class DiarioAtualHandler(BaseSiteHandler):
    DOMAINS = ["diarioatual.com", "www.diarioatual.com"]
    NAME = "diarioatual"

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
