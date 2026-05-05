import json
import logging
import re
from urllib.parse import urlparse

import trafilatura
from bs4 import BeautifulSoup

from .base import BaseSiteHandler, AGENCY_PATTERNS

logger = logging.getLogger(__name__)

# Static pages to skip
SKIP_PATHS = {
    "/assinatura", "/contactos", "/estatuto-editorial", "/ficha-tecnica",
    "/ficha-tecnica-2", "/politica-de-privacidade", "/politica-de-privacidade-2",
    "/publicidade", "/declaracao-de-transparencia", "/capa",
}

# Known article sections
KNOWN_SECTIONS = {
    "ultimas", "local", "sociedade", "desporto", "opiniao", "empresas",
    "167o-aniversario-2", "dossie", "video", "regional", "stv", "extra",
    "litoral-alentejano", "uncategorized",
}

# Old URL format: /<section>/<YYYY>/<MM>/<DD>/<slug>/
OLD_FORMAT_RE = re.compile(r"^/([^/]+)/(\d{4})/(\d{2})/(\d{2})/([^/]+)/?$")

# New URL format: /<section>/<slug>/ or /<section>/<subsection>/<slug>/
# e.g., /local/setubal/some-slug/ or /desporto/some-slug/
NEW_FORMAT_RE = re.compile(r"^/([^/]+)/(?:([^/]+)/)?([^/]+)/?$")


class OSetubalenseHandler(BaseSiteHandler):
    DOMAINS = ["osetubalense.com"]
    NAME = "osetubalense"
    CDX_PREFIXES = [f"osetubalense.com/{s}/" for s in [
        "ultimas", "local", "sociedade", "desporto", "opiniao", "empresas",
        "dossie", "video", "regional", "stv", "extra",
        "litoral-alentejano", "uncategorized",
    ]]

    def is_article_url(self, url: str) -> bool:
        parsed = urlparse(url)
        path = parsed.path

        # Skip static files
        if any(path.endswith(ext) for ext in (".jpg", ".png", ".gif", ".css", ".js", ".xml", ".json", ".pdf")):
            return False

        # Skip WordPress internals
        if any(seg in path for seg in ("/wp-content/", "/wp-json/", "/wp-admin/", "/wp-login", "/author/", "/page/")):
            return False

        # Skip query parameters that indicate non-articles
        if "?p=" in url or "?feed=" in url:
            return False

        # Skip known static pages
        clean_path = path.rstrip("/")
        if clean_path in SKIP_PATHS:
            return False

        # Skip homepage
        if clean_path in ("", "/"):
            return False

        # Old format with date in URL
        m = OLD_FORMAT_RE.match(path)
        if m:
            return True

        # New format: /<section>/<slug>/ or /<section>/<subsection>/<slug>/
        parts = [p for p in path.split("/") if p]
        if len(parts) >= 2:
            section = parts[0]
            slug = parts[-1]
            # Must have a real slug (contains hyphens, not just a number or short word)
            if len(slug) > 5 and "-" in slug:
                return True
            # Also accept if section is known and slug is long enough
            if section in KNOWN_SECTIONS and len(slug) > 3:
                return True

        return False

    def extract(self, html: str, url: str) -> dict | None:
        soup = BeautifulSoup(html, "lxml")

        # Title from h1
        title = None
        h1 = soup.find("h1", class_=re.compile(r"entry-title|post-title|article-title", re.I))
        if not h1:
            h1 = soup.find("h1")
        if h1:
            title = h1.get_text(strip=True)

        if not title:
            return None

        # Subtitle from h4 near the title/article
        subtitle = self._find_subtitle(soup)

        # Author from author link
        author, agency = self._find_author_and_agency(soup)

        # Date: try URL first (old format), then HTML metadata
        date = self._extract_date(url, soup)

        # Categories from breadcrumbs
        categories = self._find_categories(soup)

        # Section from URL
        section = self._extract_section_from_url(url)

        # Text via trafilatura
        text = trafilatura.extract(
            html,
            include_comments=False,
            include_tables=False,
            favor_precision=True,
        )

        if not text:
            # Fallback: try to extract from article body
            text = self._extract_text_fallback(soup)

        if not text:
            return None

        return {
            "title": title,
            "subtitle": subtitle,
            "text": text,
            "date": date,
            "author": author,
            "agency": agency,
            "categories": categories,
            "section": section,
        }

    def _find_subtitle(self, soup: BeautifulSoup) -> str | None:
        # Look for h4 right after the title in the article
        article = soup.find("article") or soup.find(class_=re.compile(r"post-content|entry-content|article", re.I))
        if article:
            for tag in ("h4", "h3", "h2"):
                el = article.find(tag)
                if el:
                    text = el.get_text(strip=True)
                    if 10 < len(text) < 500:
                        return text

        # Try common subtitle classes
        for cls in ("entry-subtitle", "subtitle", "lead", "excerpt"):
            el = soup.find(class_=re.compile(cls, re.I))
            if el:
                text = el.get_text(strip=True)
                if 10 < len(text) < 500:
                    return text

        return None

    def _find_author_and_agency(self, soup: BeautifulSoup) -> tuple[str | None, str | None]:
        author = None
        agency = None

        # Find author links (href contains /author/)
        for a in soup.find_all("a", href=True):
            if "/author/" in a["href"]:
                name = a.get_text(strip=True)
                if not name:
                    continue

                # Check if this is a wire agency
                href_lower = a["href"].lower()
                if "/author/lusa" in href_lower:
                    agency = "Lusa"
                    continue

                for pattern, agency_name in AGENCY_PATTERNS:
                    if pattern.search(name):
                        agency = agency_name
                        break
                else:
                    author = name
                break

        # If no author link, check meta tags
        if not author:
            meta = soup.find("meta", attrs={"name": "author"})
            if meta and meta.get("content"):
                author = meta["content"].strip()

        # Check for agency in text near byline
        if not agency:
            byline = soup.find(class_=re.compile(r"byline|author|meta-author", re.I))
            if byline:
                byline_text = byline.get_text()
                for pattern, agency_name in AGENCY_PATTERNS:
                    if pattern.search(byline_text):
                        agency = agency_name
                        break

        return author, agency

    def _extract_date(self, url: str, soup: BeautifulSoup) -> str | None:
        # Try old URL format first
        m = OLD_FORMAT_RE.match(urlparse(url).path)
        if m:
            return f"{m.group(2)}-{m.group(3)}-{m.group(4)}"

        # Try HTML metadata
        # <time> element
        time_el = soup.find("time", attrs={"datetime": True})
        if time_el:
            dt = time_el["datetime"][:10]
            if re.match(r"\d{4}-\d{2}-\d{2}", dt):
                return dt

        # <meta property="article:published_time">
        meta = soup.find("meta", attrs={"property": "article:published_time"})
        if meta and meta.get("content"):
            dt = meta["content"][:10]
            if re.match(r"\d{4}-\d{2}-\d{2}", dt):
                return dt

        # JSON-LD
        for script in soup.find_all("script", type="application/ld+json"):
            try:
                data = json.loads(script.string)
                if isinstance(data, list):
                    data = data[0] if data else {}
                dp = data.get("datePublished", "")
                if dp:
                    dt = dp[:10]
                    if re.match(r"\d{4}-\d{2}-\d{2}", dt):
                        return dt
            except Exception:
                continue

        return None

    def _find_categories(self, soup: BeautifulSoup) -> list[str]:
        categories = []

        # Breadcrumbs
        breadcrumb = soup.find(class_=re.compile(r"breadcrumb", re.I))
        if breadcrumb:
            for a in breadcrumb.find_all("a"):
                text = a.get_text(strip=True)
                if text and text.lower() not in ("início", "home", "inicio"):
                    categories.append(text)

        # Category links
        if not categories:
            for a in soup.find_all("a", rel="category tag"):
                text = a.get_text(strip=True)
                if text:
                    categories.append(text)

        # Entry-categories class
        if not categories:
            cat_div = soup.find(class_=re.compile(r"entry-categories|post-categories|cat-links", re.I))
            if cat_div:
                for a in cat_div.find_all("a"):
                    text = a.get_text(strip=True)
                    if text:
                        categories.append(text)

        return categories

    def _extract_section_from_url(self, url: str) -> str | None:
        parts = [p for p in urlparse(url).path.split("/") if p]
        if parts:
            return parts[0]
        return None

    def _extract_text_fallback(self, soup: BeautifulSoup) -> str | None:
        """Extract text from article body as fallback."""
        content = soup.find(class_=re.compile(r"entry-content|post-content|article-content", re.I))
        if content:
            # Remove scripts, styles, etc.
            for el in content.find_all(["script", "style", "nav", "aside", "footer"]):
                el.decompose()
            text = content.get_text(separator="\n", strip=True)
            if len(text) > 50:
                return text
        return None
