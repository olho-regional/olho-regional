"""Handler for beira.pt — large regional news site.

Live site returns HTTP 503 for most URLs (74K+ errors).
Many non-article URLs in CDX: /portal/etiquetas/ (tags), /diretorio/ (directory),
/kids/, and community association subpages.
Fix: PREFER_ARCHIVE + stricter URL filtering.
"""
from urllib.parse import urlparse

from .base import BaseSiteHandler

# Non-article path prefixes on beira.pt
_SKIP_PREFIXES = (
    "/portal/etiquetas/",
    "/diretorio/",
    "/kids/",
    "/agenda-de-eventos/",
    "/associacoes.",  # subdomain-style paths like /assfornotelheiro/
)


class BeiraHandler(BaseSiteHandler):
    DOMAINS = ["beira.pt", "www.beira.pt", "associacoes.beira.pt"]
    NAME = "beira"

    PREFER_ARCHIVE = True

    def is_article_url(self, url: str) -> bool:
        parsed = urlparse(url)
        path = parsed.path.lower()

        # Skip beira-specific non-article sections
        for prefix in _SKIP_PREFIXES:
            if path.startswith(prefix):
                return False

        # Must be under /portal/noticias/ or /portal/ with article-like slug
        # Allow base heuristics for the rest
        return super().is_article_url(url)
