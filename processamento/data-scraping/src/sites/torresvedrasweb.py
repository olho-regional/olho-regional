"""Handler for torresvedrasweb.pt — WordPress news site with flat permalinks.

All 8,888 tasks are 2-segment WordPress attachment pages (article-slug/image-name).
Real articles use single-segment flat permalinks: torresvedrasweb.pt/<slug>/
Fix: accept single-segment slugs, reject 2-segment attachment URLs.
NOTE: Requires CDX re-scan — existing tasks/CDX only captured attachment pages.
"""
from urllib.parse import urlparse

from .base import SKIP_SEGMENTS, BaseSiteHandler

_EXTRA_SKIP = {"category", "categoria", "tag", "author", "author", "search", "abc"}


class TorresVedrasWebHandler(BaseSiteHandler):
    DOMAINS = ["torresvedrasweb.pt", "www.torresvedrasweb.pt"]
    NAME = "torresvedrasweb"

    def is_article_url(self, url: str) -> bool:
        parsed = urlparse(url)
        path = parsed.path.lower().strip("/")

        if not path:
            return False

        if any(path.endswith(ext) for ext in (".jpg", ".png", ".gif", ".css", ".js", ".xml", ".json", ".pdf", ".ico", ".html")):
            return False

        parts = [p for p in path.split("/") if p]

        if any(p in SKIP_SEGMENTS or p in _EXTRA_SKIP for p in parts):
            return False

        # Accept single-segment article slugs only
        if len(parts) == 1:
            slug = parts[0]
            return len(slug) > 15 and "-" in slug

        return False
