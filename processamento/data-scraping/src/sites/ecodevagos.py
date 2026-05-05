"""Handler for ecodevagos.pt — WordPress news site.

Live site returns HTTP 508 (Loop Detected) for 75.2% and timeouts for 4.2%.
Archive fetches have 20.5% HTTP 400 (likely arquivo replay issues on certain URLs).
Fix: PREFER_ARCHIVE avoids the live 508/timeout errors.
"""
from .base import BaseSiteHandler


class EcoDeVagosHandler(BaseSiteHandler):
    DOMAINS = ["ecodevagos.pt", "www.ecodevagos.pt"]
    NAME = "ecodevagos"

    PREFER_ARCHIVE = True
