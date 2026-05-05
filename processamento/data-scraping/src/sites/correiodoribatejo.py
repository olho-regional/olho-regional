"""Handler for correiodoribatejo.pt — WordPress news site.

60.3% extraction_failed:None from archive (non-article URLs: /etiqueta/, /categoria/).
27.6% bot_challenge from archive (Cloudflare pages cached in arquivo).
Fix: filter out non-article URL prefixes.
"""
from urllib.parse import urlparse

from .base import BaseSiteHandler

_SKIP_PREFIXES = (
    "/etiqueta/",
    "/categoria/",
)


class CorreioDoRibatejoHandler(BaseSiteHandler):
    DOMAINS = [
        "correiodoribatejo.pt",
        "www.correiodoribatejo.pt",
        "arquivo.correiodoribatejo.pt",
    ]
    NAME = "correiodoribatejo"

    def is_article_url(self, url: str) -> bool:
        path = urlparse(url).path.lower()
        for prefix in _SKIP_PREFIXES:
            if path.startswith(prefix):
                return False
        return super().is_article_url(url)
