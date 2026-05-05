"""Handler for avozdeermesinde.com — classic ASP newspaper site.

Uses query-parameter URLs (noticia.asp?idEdicao=N&id=N&idSeccao=N&Action=noticia).
No sitemap, CDX archives only captured homepages. Discovery crawls all editions
and their section pages on the live site to find article links.
"""
import logging
import re
from urllib.parse import parse_qs, urljoin, urlparse

from bs4 import BeautifulSoup

from .base import BaseSiteHandler

logger = logging.getLogger(__name__)

BASE_URL = "https://www.avozdeermesinde.com"
# Title pattern: "Jornal A Voz de Ermesinde - DD-MM-YYYY - Section - Title"
TITLE_RE = re.compile(
    r"Jornal A Voz de Ermesinde\s*-\s*(\d{2})-(\d{2})-(\d{4})\s*-\s*(.+)",
)


class AVozDeErmesindeHandler(BaseSiteHandler):
    DOMAINS = ["avozdeermesinde.com", "www.avozdeermesinde.com"]
    NAME = "avozdeermesinde"

    # Skip CDX — archives only have homepage captures
    CDX_PREFIXES = ["https://www.avozdeermesinde.com/noticia.asp"]

    def is_article_url(self, url: str) -> bool:
        parsed = urlparse(url)
        path = parsed.path.lower().rstrip("/")
        if path.endswith("/noticia.asp") or path == "/noticia.asp" or path == "noticia.asp":
            qs = parse_qs(parsed.query)
            return "id" in qs and "Action" in qs
        return False

    async def discover_urls(self, client) -> list[dict]:
        """Crawl all editions and sections to discover article URLs."""
        all_urls = {}  # url_str -> record dict (dedup by URL)

        # Find the latest edition ID from the homepage
        max_edition = await self._find_max_edition(client)
        logger.info(f"avozdeermesinde: crawling editions 100..{max_edition}")

        for eid in range(100, max_edition + 1):
            try:
                articles = await self._crawl_edition(client, eid)
                for url in articles:
                    if url not in all_urls:
                        all_urls[url] = {"url": url, "source": "live"}
            except Exception as e:
                logger.debug(f"avozdeermesinde: edition {eid} error: {e}")

            if eid % 50 == 0:
                logger.info(f"avozdeermesinde: crawled editions up to {eid}, {len(all_urls)} unique articles so far")

        logger.info(f"avozdeermesinde: discovered {len(all_urls)} unique article URLs from {max_edition - 99} editions")
        return list(all_urls.values())

    async def _find_max_edition(self, client) -> int:
        """Find the latest edition ID from the archive page."""
        try:
            resp = await client.get(f"{BASE_URL}/jornal/arquivo.asp", timeout=15.0, follow_redirects=True)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.content, "html.parser")
                max_eid = 0
                for a in soup.find_all("a", href=True):
                    m = re.search(r"idEdicao=(\d+)", a["href"], re.IGNORECASE)
                    if m:
                        max_eid = max(max_eid, int(m.group(1)))
                if max_eid > 0:
                    return max_eid
        except Exception as e:
            logger.warning(f"avozdeermesinde: could not fetch archive page: {e}")
        return 445  # fallback

    async def _crawl_edition(self, client, eid: int) -> set[str]:
        """Crawl an edition's index page and all its section pages for article URLs."""
        articles = set()

        # Get edition index
        resp = await client.get(
            f"{BASE_URL}/index.asp?idEdicao={eid}",
            timeout=10.0, follow_redirects=True,
        )
        if resp.status_code != 200:
            return articles

        soup = BeautifulSoup(resp.content, "html.parser")

        # Collect article links from index page
        self._extract_article_links(soup, articles)

        # Find section links
        section_urls = set()
        for a in soup.find_all("a", href=True):
            if "Action=seccao" in a["href"]:
                href = a["href"]
                if not href.startswith("http"):
                    href = urljoin(BASE_URL + "/", href)
                section_urls.add(href)

        # Crawl each section
        for sec_url in section_urls:
            try:
                sec_resp = await client.get(sec_url, timeout=10.0, follow_redirects=True)
                if sec_resp.status_code == 200:
                    sec_soup = BeautifulSoup(sec_resp.content, "html.parser")
                    self._extract_article_links(sec_soup, articles)
            except Exception:
                pass

        return articles

    def _extract_article_links(self, soup: BeautifulSoup, out: set[str]):
        """Extract article URLs from a parsed page."""
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if "noticia.asp" in href and "id=" in href:
                if not href.startswith("http"):
                    href = urljoin(BASE_URL + "/", href)
                # Normalize: ensure https
                href = href.replace("http://www.avozdeermesinde.com",
                                    "https://www.avozdeermesinde.com")
                out.add(href)

    def extract(self, html: str, url: str) -> dict | None:
        soup = BeautifulSoup(html, "html.parser")

        # Title and date from <title> tag
        # Pattern: "Jornal A Voz de Ermesinde - DD-MM-YYYY - Section - Article Title"
        title = None
        date = None
        categories = []

        title_tag = soup.title.string if soup.title else None
        if title_tag:
            m = TITLE_RE.match(title_tag.strip())
            if m:
                day, month, year = m.group(1), m.group(2), m.group(3)
                date = f"{year}-{month}-{day}"
                rest = m.group(4)
                # rest = "Section - Article Title" or just "Article Title"
                parts = rest.split(" - ", 1)
                if len(parts) == 2:
                    categories = [parts[0].strip()]
                    title = parts[1].strip()
                else:
                    title = parts[0].strip()

        # Fallback: h1.titulo
        if not title:
            h1 = soup.find("h1", class_="titulo")
            if h1:
                title = h1.get_text(strip=True)

        if not title:
            return None

        # Category from section td or span.antetitulo
        if not categories:
            ante = soup.find("span", class_="antetitulo")
            if ante:
                cat = ante.get_text(strip=True)
                if cat:
                    categories = [cat]

        # Body text from span.texto elements
        text_parts = []
        for span in soup.find_all("span", class_="texto"):
            text = span.get_text(strip=True)
            if text:
                text_parts.append(text)

        body = "\n\n".join(text_parts)
        if not body:
            return None

        return {
            "url": url,
            "title": title,
            "date": date,
            "author": None,
            "text": body,
            "categories": categories,
            "source": "A Voz de Ermesinde",
        }
