"""Handler for diariodoalentejo.pt — custom ASP.NET CMS (Autarquia 360)."""
import re
from urllib.parse import urlparse

from .base import BaseSiteHandler

# /pt/noticias/{id}/{slug}.aspx, /pt/desporto/{id}/{slug}.aspx, /pt/etc/{id}/{slug}.aspx
ARTICLE_RE = re.compile(r"^/pt/(noticias|desporto|etc)/\d+/.+\.aspx$")


class DiarioDoAlentejoHandler(BaseSiteHandler):
    DOMAINS = ["diariodoalentejo.pt", "www.diariodoalentejo.pt"]
    NAME = "diariodoalentejo"
    CDX_PREFIXES = [
        "diariodoalentejo.pt/pt/noticias/",
        "diariodoalentejo.pt/pt/desporto/",
        "diariodoalentejo.pt/pt/etc/",
    ]

    def is_article_url(self, url: str) -> bool:
        path = urlparse(url).path.rstrip("/")
        return bool(ARTICLE_RE.match(path))

    def extract(self, html: str, url: str) -> dict | None:
        result = super().extract(html, url)
        if result is None:
            return None

        # Section from URL (/pt/noticias/... -> noticias)
        path = urlparse(url).path
        parts = [p for p in path.split("/") if p]
        if len(parts) >= 2:
            result["section"] = parts[1]

        # Date from page content: "06 de abril 2026 - 08:00"
        if not result.get("date"):
            import re as _re
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, "lxml")
            date_el = soup.find("span", class_="mod_dyn_datetime")
            if date_el:
                result["date"] = date_el.get_text(strip=True)

        return result
