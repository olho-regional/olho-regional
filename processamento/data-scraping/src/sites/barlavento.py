"""Handler for barlavento.pt — WordPress + Foxiz theme + Yoast SEO."""
import re
from urllib.parse import urlparse

from .base import BaseSiteHandler, SKIP_SEGMENTS

SKIP_PREFIXES = {
    "author", "category", "tag", "page", "wp-content", "wp-json",
    "wp-admin", "wp-login", "feed", "comments",
}


class BarlaventoHandler(BaseSiteHandler):
    DOMAINS = ["barlavento.pt", "www.barlavento.pt"]
    NAME = "barlavento"

    def is_article_url(self, url: str) -> bool:
        parsed = urlparse(url)
        path = parsed.path.strip("/").lower()

        if not path:
            return False

        # Skip static files
        if any(path.endswith(ext) for ext in (".jpg", ".png", ".gif", ".css", ".js", ".xml", ".json", ".pdf")):
            return False

        parts = path.split("/")

        # Skip known non-article prefixes
        if parts[0] in SKIP_PREFIXES:
            return False

        # Flat slug pattern: single segment with hyphens
        if len(parts) == 1 and len(parts[0]) > 10 and "-" in parts[0]:
            return True

        # Category/slug: 2 segments where slug has hyphens
        if len(parts) == 2 and len(parts[1]) > 10 and "-" in parts[1]:
            return True

        return False
