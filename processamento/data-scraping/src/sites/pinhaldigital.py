"""Handler for pinhaldigital.com — Joomla 1.5 newspaper site.

The site uses table-based layout that trafilatura cannot extract from.
URL formats:
  /jornal/15/<id>-<date>.html (newer)
  /<YYYYMMDDhhmm>/<Category>/<slug>.html (older, date-prefix)
  /component/content/article/<id>-<date>.html (Joomla component)
  /<Category>/<slug>.html (category-based)

Non-article URLs to filter:
  /<Category>/Page-<N>.html (pagination)
  /Table/... (misc)
  /components/... (static Joomla assets)

Custom extract for the Joomla table layout:
  - td.contentheading → title
  - td.datetime → date
  - Second #principal > table → body text
"""
import re
from urllib.parse import urlparse

from bs4 import BeautifulSoup

from .base import BaseSiteHandler

_PAGINATION_RE = re.compile(r"/Page-\d+\.html$", re.I)


class PinhalDigitalHandler(BaseSiteHandler):
    DOMAINS = ["pinhaldigital.com", "www.pinhaldigital.com"]
    NAME = "pinhaldigital"

    def is_article_url(self, url: str) -> bool:
        path = urlparse(url).path

        # Skip pagination pages
        if _PAGINATION_RE.search(path):
            return False

        # Skip static assets
        lower = path.lower()
        if lower.startswith("/components/") or lower.startswith("/table/"):
            return False

        return super().is_article_url(url)

    def extract(self, html: str, url: str) -> dict | None:
        soup = BeautifulSoup(html, "lxml")

        # Try Joomla table layout first
        heading_td = soup.select_one("td.contentheading")
        if heading_td:
            return self._extract_joomla(soup, url)

        # Fallback to base trafilatura
        return super().extract(html, url)

    def _extract_joomla(self, soup: BeautifulSoup, url: str) -> dict | None:
        title = soup.select_one("td.contentheading")
        if not title:
            return None
        title_text = title.get_text(strip=True)
        if not title_text:
            return None

        # Date from datetime cell
        date = None
        dt_td = soup.select_one("td.datetime")
        if dt_td:
            date = self._parse_joomla_date(dt_td)

        # Body text from second table in #principal
        text = ""
        tables = soup.select("#principal > table")
        if len(tables) >= 2:
            body_td = tables[1].find("td")
            if body_td:
                paragraphs = []
                for p in body_td.find_all("p"):
                    p_text = p.get_text(strip=True)
                    if p_text:
                        paragraphs.append(p_text)
                if paragraphs:
                    text = "\n".join(paragraphs)
                else:
                    # Fallback: get all text from the cell
                    text = body_td.get_text("\n", strip=True)

        if not text:
            return None

        # Category from URL path or from the header table
        section = self._extract_section(url)

        # Author from metadata
        import trafilatura
        metadata = trafilatura.extract_metadata(str(soup))
        author = metadata.author if metadata else None

        return {
            "title": title_text,
            "subtitle": None,
            "text": text,
            "date": date or (metadata.date if metadata else None),
            "author": author,
            "agency": None,
            "categories": [],
            "section": section,
        }

    def _parse_joomla_date(self, dt_td) -> str | None:
        """Parse date from Joomla datetime cell like 'Qui09Jun2022'."""
        text = dt_td.get_text(strip=True)
        # Try to extract day/month/year from compressed format
        m = re.search(r"(\d{1,2})(\w{3})(\d{4})", text)
        if m:
            day, month_abbr, year = m.groups()
            months_pt = {
                "jan": "01", "fev": "02", "mar": "03", "abr": "04",
                "mai": "05", "jun": "06", "jul": "07", "ago": "08",
                "set": "09", "out": "10", "nov": "11", "dez": "12",
            }
            month = months_pt.get(month_abbr.lower())
            if month:
                return f"{year}-{month}-{day.zfill(2)}"
        return None
