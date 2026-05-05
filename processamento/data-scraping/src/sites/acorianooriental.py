"""Handler for acorianooriental.pt — custom CMS (Bulma-based)."""
import re
from urllib.parse import urlparse

from bs4 import BeautifulSoup

from .base import BaseSiteHandler

# /noticia/{slug}-{id} or /artigo/{slug}-{id}
ARTICLE_RE = re.compile(r"^/(noticia|artigo)/[\w-]+-\d+$")


class AcorianoOrientalHandler(BaseSiteHandler):
    DOMAINS = ["acorianooriental.pt", "www.acorianooriental.pt"]
    NAME = "acorianooriental"
    CDX_PREFIXES = [
        "acorianooriental.pt/noticia/",
        "acorianooriental.pt/artigo/",
    ]

    def is_article_url(self, url: str) -> bool:
        path = urlparse(url).path.rstrip("/")
        return bool(ARTICLE_RE.match(path))

    def extract(self, html: str, url: str) -> dict | None:
        result = super().extract(html, url)
        if result is None:
            return None

        soup = BeautifulSoup(html, "lxml")

        # Author from JSON-LD or itemprop
        if not result.get("author"):
            author_el = soup.find(attrs={"itemprop": "author"})
            if author_el:
                result["author"] = author_el.get_text(strip=True)

        # Date from itemprop
        if not result.get("date"):
            time_el = soup.find("time", attrs={"itemprop": "datePublished"})
            if time_el and time_el.get("datetime"):
                result["date"] = time_el["datetime"][:10]

        # Section from URL
        path = urlparse(url).path.rstrip("/")
        if path.startswith("/noticia"):
            result["section"] = "noticia"
        elif path.startswith("/artigo"):
            result["section"] = "opiniao"

        return result
