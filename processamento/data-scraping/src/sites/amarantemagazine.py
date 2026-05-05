"""Handler for amarantemagazine.sapo.pt — WordPress site behind SAPO anti-bot.

The live site returns a JS challenge page that cannot be bypassed without a
browser.  All fetching must go through arquivo.pt or Wayback Machine archives.
"""
import re
from urllib.parse import urlparse

from bs4 import BeautifulSoup

from .base import BaseSiteHandler

SKIP_PREFIXES = {
    "author", "categoria", "tag", "page", "wp-content", "wp-json",
    "wp-admin", "wp-login", "feed", "comments", "wp-includes",
    ".well-known",
}

ARTICLE_SECTIONS = {
    "sociedade", "sociedade-e-cultura", "cultura-e-lazer", "desporto",
    "gente", "opiniao", "empresas", "estorias", "sitiosesabores",
    "videos",
}


class AmaranteMagazineHandler(BaseSiteHandler):
    DOMAINS = ["amarantemagazine.sapo.pt"]
    NAME = "amarantemagazine"

    # Live site has SAPO anti-bot JS challenge — archives only
    PREFER_ARCHIVE = True
    # arquivo.pt often captured the bot challenge page, wayback has better copies
    ARCHIVE_PRIORITY = ("wayback", "arquivo")

    CDX_PREFIXES = [
        "https://amarantemagazine.sapo.pt/sociedade/",
        "https://amarantemagazine.sapo.pt/sociedade-e-cultura/",
        "https://amarantemagazine.sapo.pt/cultura-e-lazer/",
        "https://amarantemagazine.sapo.pt/desporto/",
        "https://amarantemagazine.sapo.pt/gente/",
        "https://amarantemagazine.sapo.pt/opiniao/",
        "https://amarantemagazine.sapo.pt/empresas/",
        "https://amarantemagazine.sapo.pt/estorias/",
        "https://amarantemagazine.sapo.pt/sitiosesabores/",
        "https://amarantemagazine.sapo.pt/videos/",
    ]

    def is_article_url(self, url: str) -> bool:
        parsed = urlparse(url)
        path = parsed.path.strip("/").lower()

        if not path:
            return False

        if any(path.endswith(ext) for ext in (".jpg", ".png", ".gif", ".css", ".js", ".xml", ".json", ".pdf", ".ico", ".txt")):
            return False

        parts = path.split("/")

        if parts[0] in SKIP_PREFIXES:
            return False

        # Must start with a known section
        if parts[0] not in ARTICLE_SECTIONS:
            return False

        # Exactly section/slug pattern (reject sub-paths like /section/slug/footer-config)
        if len(parts) == 2:
            slug = parts[1]
            if len(slug) > 10 and "-" in slug:
                return True

        return False

    def extract(self, html: str, url: str) -> dict | None:
        soup = BeautifulSoup(html, "lxml")

        # Title
        title = None
        h1 = soup.find("h1", class_="entry-title")
        if not h1:
            h1 = soup.find("h1")
        if h1:
            title = h1.get_text(strip=True)

        if not title:
            og = soup.find("meta", property="og:title")
            if og:
                title = og.get("content", "").strip()

        if not title:
            return None

        # Text from entry-content
        text = None
        content = soup.find(class_="entry-content")
        if content:
            # Remove share buttons, related posts, ads
            for tag in content.find_all(class_=re.compile(r"sharedaddy|jp-relatedposts|adsbygoogle|share", re.I)):
                tag.decompose()
            paragraphs = [p.get_text(strip=True) for p in content.find_all("p") if p.get_text(strip=True)]
            text = "\n".join(paragraphs)

        if not text:
            # Fallback to trafilatura
            import trafilatura
            text = trafilatura.extract(html, include_comments=False, favor_precision=True)

        if not text:
            return None

        # Date
        date = None
        time_el = soup.find("time", class_="entry-date")
        if time_el and time_el.get("datetime"):
            date = time_el["datetime"][:10]
        if not date:
            meta = soup.find("meta", property="article:published_time")
            if meta:
                date = meta.get("content", "")[:10]

        # Author
        author = None
        byline = soup.find("span", class_="byline")
        if byline:
            a = byline.find("a")
            if a:
                author = a.get_text(strip=True)
        if not author:
            author_span = soup.find("span", class_="author-title")
            if author_span:
                author = author_span.get_text(strip=True)
        # Drop generic site name as author
        if author and author.upper() == "AMARANTE MAGAZINE":
            author = None

        # Categories from article classes
        categories = []
        article = soup.find("article")
        if article:
            for cls in article.get("class", []):
                if cls.startswith("category-"):
                    cat = cls.replace("category-", "").replace("-", " ").title()
                    categories.append(cat)

        # Subtitle / excerpt
        subtitle = None
        og_desc = soup.find("meta", property="og:description")
        if og_desc:
            desc = og_desc.get("content", "").strip()
            if desc and desc not in text[:len(desc) + 20]:
                subtitle = desc

        section = self._extract_section(url)

        return {
            "title": title,
            "subtitle": subtitle,
            "text": text,
            "date": date,
            "author": author,
            "agency": self._detect_agency(author, html),
            "categories": categories,
            "section": section,
        }
