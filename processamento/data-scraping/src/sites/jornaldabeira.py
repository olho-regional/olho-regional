"""Handler for jornaldabeira.net — Joomla news site.

93.7% extraction_failed:None from archive — mix of non-article URLs
(/category/, /index.php/edicao/) and real articles where trafilatura
fails on old Joomla HTML layout.
Fix: filter obvious non-article URL patterns.
"""
from urllib.parse import urlparse

from .base import BaseSiteHandler

_SKIP_PREFIXES = (
    "/category/",
    "/index.php/edicao-digital",
    "/index.php/edicao/",
    "/revistas/",
)


class JornalDaBeiraHandler(BaseSiteHandler):
    DOMAINS = [
        "jornaldabeira.net",
        "www.jornaldabeira.net",
    ]
    NAME = "jornaldabeira"

    def is_article_url(self, url: str) -> bool:
        path = urlparse(url).path.lower()
        for prefix in _SKIP_PREFIXES:
            if path.startswith(prefix):
                return False
        return super().is_article_url(url)
