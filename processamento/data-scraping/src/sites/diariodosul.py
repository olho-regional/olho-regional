"""Handler for diariodosul.pt — WordPress + Yoast SEO."""
import re
from urllib.parse import urlparse

from .base import BaseSiteHandler, DATE_IN_PATH_RE, SKIP_SEGMENTS


class DiarioDoSulHandler(BaseSiteHandler):
    DOMAINS = ["diariodosul.pt", "www.diariodosul.pt"]
    NAME = "diariodosul"
    CDX_PREFIXES = [f"diariodosul.pt/{y}/" for y in range(2000, 2027)]

    def is_article_url(self, url: str) -> bool:
        parsed = urlparse(url)
        path = parsed.path.strip("/").lower()

        if not path:
            return False

        # Skip static files
        if any(path.endswith(ext) for ext in (".jpg", ".png", ".gif", ".css", ".js", ".xml", ".json", ".pdf")):
            return False

        parts = path.split("/")

        # Skip known non-article segments
        if any(p in SKIP_SEGMENTS for p in parts):
            return False

        # Skip non-article prefixes
        if parts[0] in ("author", "category", "tag", "page"):
            return False

        # Standard /YYYY/MM/DD/slug/ pattern
        if DATE_IN_PATH_RE.search(parsed.path):
            return True

        return False
