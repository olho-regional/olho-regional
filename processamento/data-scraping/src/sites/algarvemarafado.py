"""Handler for algarvemarafado.com — WordPress site behind SAPO/openresty anti-bot.

The live site returns HTTP 415 without browser headers, then a JS challenge
with browser headers.  All fetching must go through archives.
"""
from .base import BaseSiteHandler


class AlgarveMarafadoHandler(BaseSiteHandler):
    DOMAINS = ["algarvemarafado.com", "www.algarvemarafado.com"]
    NAME = "algarvemarafado"

    # Live site has SAPO anti-bot — archives only
    PREFER_ARCHIVE = True

    CDX_PREFIXES = [
        f"https://www.algarvemarafado.com/{y}/"
        for y in range(2015, 2027)
    ]
