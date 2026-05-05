import logging
import re
from urllib.parse import urlparse

import trafilatura
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

# Known wire agencies
AGENCY_PATTERNS = [
    (re.compile(r"\blusa\b", re.I), "Lusa"),
    (re.compile(r"\breuters\b", re.I), "Reuters"),
    (re.compile(r"\bafp\b", re.I), "AFP"),
    (re.compile(r"\befe\b", re.I), "EFE"),
]

# URL segments that indicate non-article pages
SKIP_SEGMENTS = {
    "wp-content", "wp-json", "wp-admin", "wp-login", "wp-includes",
    "feed", "author", "tag", "category", "page", "comments", "trackback",
    "xmlrpc.php", "wp-cron.php", "autor", "cdn-cgi"
}

DATE_IN_PATH_RE = re.compile(r"/(\d{4})/(\d{2})/(\d{2})/")


class BaseSiteHandler:
    """Generic site handler — works for most WordPress news sites."""

    DOMAINS: list[str] = []  # Override in subclasses
    NAME = "base"
    CDX_PREFIXES: list[str] = []  # URL prefixes for targeted CDX queries (if empty, uses domain-wide scan)

    def is_article_url(self, url: str) -> bool:
        """Return True if URL looks like an article page."""
        parsed = urlparse(url)
        path = parsed.path.lower()

        # Skip static files
        if any(path.endswith(ext) for ext in (".jpg", ".png", ".gif", ".css", ".js", ".xml", ".json", ".pdf", ".ico")):
            return False

        # Skip known non-article segments
        parts = [p for p in path.split("/") if p]
        if any(p in SKIP_SEGMENTS for p in parts):
            return False

        # Skip query-only pages
        if path in ("/", "") and not parsed.query:
            return False

        # Skip if just a homepage
        if len(parts) == 0:
            return False

        # Accept if date-in-path (WordPress standard)
        if DATE_IN_PATH_RE.search(path):
            return True

        # Accept long hyphenated slugs (common Portuguese news pattern)
        # Works for both /slug and /section/slug patterns
        slug = parts[-1]
        if len(slug) > 10 and "-" in slug:
            return True

        return False

    def extract(self, html: str, url: str) -> dict | None:
        """Extract article metadata from HTML.
        
        Returns article dict or None on failure.
        """
        # Use trafilatura for text extraction
        text = trafilatura.extract(
            html,
            include_comments=False,
            include_tables=False,
            favor_precision=True,
        )

        if not text:
            return None

        # Extract metadata
        metadata = trafilatura.extract_metadata(html)

        title = metadata.title if metadata else None
        author = metadata.author if metadata else None
        date = metadata.date if metadata else None
        categories = []
        if metadata and metadata.categories:
            categories = [c.strip() for c in metadata.categories if c.strip()]

        # Try to get better title from HTML
        if not title:
            title = self._extract_title_bs4(html)

        # Extract subtitle
        subtitle = self._extract_subtitle(html)

        # Extract section from URL
        section = self._extract_section(url)

        # Detect agency
        agency = self._detect_agency(author, html)

        # Clean author (remove agency from name)
        if author and agency:
            author = self._clean_author(author, agency)

        if not title:
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

    def build_archive_url(self, source: str, timestamp: str, url: str) -> str:
        if source == "arquivo":
            return f"https://arquivo.pt/noFrame/replay/{timestamp}id_/{url}"
        elif source == "wayback":
            return f"https://web.archive.org/web/{timestamp}id_/{url}"
        else:
            return url

    def _extract_title_bs4(self, html: str) -> str | None:
        try:
            soup = BeautifulSoup(html, "lxml")
            h1 = soup.find("h1")
            if h1:
                return h1.get_text(strip=True)
            title_tag = soup.find("title")
            if title_tag:
                return title_tag.get_text(strip=True)
        except Exception:
            pass
        return None

    def _extract_subtitle(self, html: str) -> str | None:
        try:
            soup = BeautifulSoup(html, "lxml")
            # Look for subtitle patterns: h2/h3/h4 near the article
            for tag in ("h4", "h3", "h2"):
                el = soup.find("article")
                if el:
                    sub = el.find(tag)
                    if sub:
                        text = sub.get_text(strip=True)
                        if 10 < len(text) < 500:
                            return text
            # Try excerpt/lead class patterns
            for cls in ("excerpt", "lead", "subtitle", "sub-title", "entry-subtitle"):
                el = soup.find(class_=re.compile(cls, re.I))
                if el:
                    text = el.get_text(strip=True)
                    if 10 < len(text) < 500:
                        return text
        except Exception:
            pass
        return None

    def _extract_section(self, url: str) -> str | None:
        parts = [p for p in urlparse(url).path.split("/") if p]
        if parts:
            return parts[0]
        return None

    def _detect_agency(self, author: str | None, html: str) -> str | None:
        text_to_check = author or ""
        for pattern, name in AGENCY_PATTERNS:
            if pattern.search(text_to_check):
                return name

        # Also check HTML for byline patterns
        try:
            soup = BeautifulSoup(html, "lxml")
            for a in soup.find_all("a", href=True):
                if "/author/" in a["href"]:
                    author_text = a.get_text(strip=True).lower()
                    for pattern, name in AGENCY_PATTERNS:
                        if pattern.search(author_text):
                            return name
        except Exception:
            pass

        return None

    def _clean_author(self, author: str, agency: str) -> str | None:
        """Remove agency name from author string."""
        cleaned = re.sub(rf"\b{re.escape(agency)}\b", "", author, flags=re.I).strip()
        # Remove leftover separators
        cleaned = re.sub(r"^[\s,/|–-]+|[\s,/|–-]+$", "", cleaned)
        return cleaned if cleaned else None
