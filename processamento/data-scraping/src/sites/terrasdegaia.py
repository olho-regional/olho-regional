"""Handler for terrasdegaia.pt — WordPress news site.

Live site returns HTTP 508 (Loop Detected) for 84.9% of fetches,
plus timeouts. Archive fetches have 11.3% bot_challenge (archived WAF pages).
Fix: PREFER_ARCHIVE avoids the live 508/timeout errors.
"""
from .base import BaseSiteHandler


class TerrasDeGaiaHandler(BaseSiteHandler):
    DOMAINS = ["terrasdegaia.pt", "www.terrasdegaia.pt"]
    NAME = "terrasdegaia"

    PREFER_ARCHIVE = True
