"""Handler for rodaviva.pt — news site with mixed CMS history.

66.6% extraction_failed:None from archive — non-article URL patterns:
  /xsitev2p/ (2,092 old CMS URLs with query-string actions)
  /application/ (980 static/framework files)
  /filemanager/ (27 admin uploads)
Fix: filter out non-article URL prefixes.
"""
from urllib.parse import urlparse

from .base import BaseSiteHandler

_SKIP_PREFIXES = (
    "/xsitev2p/",
    "/application/",
    "/filemanager/",
    "/css/",
)


class RodaVivaHandler(BaseSiteHandler):
    DOMAINS = ["rodaviva.pt", "www.rodaviva.pt"]
    NAME = "rodaviva"

    def is_article_url(self, url: str) -> bool:
        path = urlparse(url).path.lower()
        for prefix in _SKIP_PREFIXES:
            if path.startswith(prefix):
                return False
        return super().is_article_url(url)
