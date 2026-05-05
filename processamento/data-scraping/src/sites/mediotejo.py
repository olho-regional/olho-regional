"""Handler for mediotejo.net — WordPress news site.

79.8% extraction_failed:None from archive — non-article URLs:
  /hashtags/ (1,687 errors), /joomsport_match/ (351), /category/ (20).
Fix: filter out non-article URL prefixes.
"""
from urllib.parse import urlparse

from .base import BaseSiteHandler

_SKIP_PREFIXES = (
    "/hashtags/",
    "/joomsport_match/",
    "/category/",
)


class MedioTejoHandler(BaseSiteHandler):
    DOMAINS = ["mediotejo.net", "www.mediotejo.net"]
    NAME = "mediotejo"

    def is_article_url(self, url: str) -> bool:
        path = urlparse(url).path.lower()
        for prefix in _SKIP_PREFIXES:
            if path.startswith(prefix):
                return False
        return super().is_article_url(url)
