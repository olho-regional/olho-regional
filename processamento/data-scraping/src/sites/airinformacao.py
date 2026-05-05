"""Handler for airinformacao.pt — WordPress news site.

Live site returns HTTP 415 (Unsupported Media Type) for 87.7% of fetches.
Fix: PREFER_ARCHIVE to redirect all fetches to arquivo/wayback.
"""
from .base import BaseSiteHandler


class AirInformacaoHandler(BaseSiteHandler):
    DOMAINS = ["airinformacao.pt", "www.airinformacao.pt"]
    NAME = "airinformacao"

    PREFER_ARCHIVE = True
