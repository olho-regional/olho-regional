"""Handler for reconquista.pt — LVEngine custom CMS."""
import re
from urllib.parse import urlparse

from .base import BaseSiteHandler

# /articles/{slug}
ARTICLE_RE = re.compile(r"^/articles/[\w-]+$")


class ReconquistaHandler(BaseSiteHandler):
    DOMAINS = ["reconquista.pt", "www.reconquista.pt"]
    NAME = "reconquista"
    CDX_PREFIXES = [
        "reconquista.pt/articles/",
    ]

    def is_article_url(self, url: str) -> bool:
        path = urlparse(url).path.rstrip("/")
        return bool(ARTICLE_RE.match(path))

    def extract(self, html: str, url: str) -> dict | None:
        result = super().extract(html, url)
        if result is None:
            return None

        # Try to extract date from byline: "DD/MM/YYYY - HH:MM"
        if not result.get("date"):
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, "lxml")
            date_match = re.search(r"(\d{2})/(\d{2})/(\d{4})", soup.get_text())
            if date_match:
                d, m, y = date_match.groups()
                result["date"] = f"{y}-{m}-{d}"

        return result
