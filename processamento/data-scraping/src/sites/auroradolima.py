"""Handler for auroradolima.com — WordPress + GeneratePress + Rank Math."""
import re
from urllib.parse import urlparse

from .base import BaseSiteHandler, SKIP_SEGMENTS

SKIP_PREFIXES = {
    "author", "category", "tag", "page", "wp-content", "wp-json",
    "wp-admin", "wp-login", "feed", "comments", "loja", "produto",
    "minha-conta", "carrinho", "checkout",
}


class AuroraDoLimaHandler(BaseSiteHandler):
    DOMAINS = ["auroradolima.com", "www.auroradolima.com"]
    NAME = "auroradolima"
    CDX_PREFIXES = [
        "https://auroradolima.com/featured/",
        "https://www.auroradolima.com/featured/",
        "http://auroradolima.com/featured/",
        "http://www.auroradolima.com/featured/",
    ]

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

        # Flat slug pattern: single segment with hyphens (older WordPress URLs)
        if len(parts) == 1 and len(parts[0]) > 10 and "-" in parts[0]:
            return True

        # Category/slug pattern: /{category}/{slug}/
        if len(parts) == 2 and len(parts[1]) > 10 and "-" in parts[1]:
            return True

        # Deeper: /{cat}/{subcat}/{slug}/
        if len(parts) == 3 and len(parts[-1]) > 10 and "-" in parts[-1]:
            return True

        return False
