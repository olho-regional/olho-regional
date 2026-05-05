"""Handler for centrotv.sapo.pt — WordPress news site on SAPO hosting.

Uses single-segment flat permalinks (centrotv.sapo.pt/<slug>/) which the base
handler rejects (requires 2+ segments).  The live site works fine — archives
contain SAPO anti-bot challenge pages, so live fetching is preferred.
"""
import re
from urllib.parse import urlparse

from .base import SKIP_SEGMENTS, BaseSiteHandler

# Segments that are definitely not articles
_EXTRA_SKIP = {"categoria", "tag", "author", "page", "search", "wp-sitemap.xml"}


class CentroTVHandler(BaseSiteHandler):
    DOMAINS = ["centrotv.sapo.pt", "www.centrotv.sapo.pt"]
    NAME = "centrotv"

    def is_article_url(self, url: str) -> bool:
        parsed = urlparse(url)
        path = parsed.path.lower().strip("/")

        if not path:
            return False

        # Skip static files
        if any(path.endswith(ext) for ext in (".jpg", ".png", ".gif", ".css", ".js", ".xml", ".json", ".pdf", ".ico")):
            return False

        parts = [p for p in path.split("/") if p]

        # Skip known non-article segments
        if any(p in SKIP_SEGMENTS or p in _EXTRA_SKIP for p in parts):
            return False

        # Accept single-segment article slugs (the site's permalink format)
        # Slugs are long and contain hyphens
        if len(parts) == 1:
            slug = parts[0]
            return len(slug) > 15 and "-" in slug

        # Also accept 2-segment paths (slug/attachment-id for galleries)
        if len(parts) == 2:
            slug = parts[0]
            return len(slug) > 15 and "-" in slug

        return False
