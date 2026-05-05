"""Handler for correiodecaria.com — WordPress news site.

Live site returns HTTP 415 for 91.5% of fetches (same as airinformacao.pt pattern).
Archive fetches have 8.3% bot_challenge.
Fix: PREFER_ARCHIVE.
"""
from .base import BaseSiteHandler


class CorreioDeCáriaHandler(BaseSiteHandler):
    DOMAINS = ["correiodecaria.com", "www.correiodecaria.com"]
    NAME = "correiodecaria"

    PREFER_ARCHIVE = True
