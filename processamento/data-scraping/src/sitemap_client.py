import logging
import xml.etree.ElementTree as ET

import httpx

logger = logging.getLogger(__name__)

SITEMAP_NS = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}


async def discover_live_urls(client: httpx.AsyncClient, domain: str) -> list[dict]:
    """Discover all article URLs from a site's sitemaps.
    
    Returns list of {url, lastmod} dicts.
    """
    sitemap_index_url = await _find_sitemap_index(client, domain)
    if not sitemap_index_url:
        logger.info(f"No sitemap found for {domain}")
        return []

    sitemap_urls = await _parse_sitemap_index(client, sitemap_index_url)
    if not sitemap_urls:
        # Maybe it's a flat sitemap, not an index
        urls = await _parse_sitemap(client, sitemap_index_url)
        return urls

    # Filter to post-sitemaps only (skip page-sitemap, category-sitemap, etc.)
    post_sitemaps = [u for u in sitemap_urls if "post-sitemap" in u]
    if not post_sitemaps:
        # No post-specific sitemaps, try all of them
        post_sitemaps = sitemap_urls

    logger.info(f"Found {len(post_sitemaps)} post-sitemap files for {domain}")

    all_urls = []
    for sm_url in post_sitemaps:
        urls = await _parse_sitemap(client, sm_url)
        all_urls.extend(urls)
        logger.debug(f"  {sm_url}: {len(urls)} URLs")

    logger.info(f"Total: {len(all_urls)} URLs from live sitemaps for {domain}")
    return all_urls


async def _find_sitemap_index(client: httpx.AsyncClient, domain: str) -> str | None:
    """Try to find the sitemap index URL for a domain."""
    # Try robots.txt first
    robots_url = f"https://{domain}/robots.txt"
    try:
        resp = await client.get(robots_url, timeout=15.0, follow_redirects=True)
        if resp.status_code == 200:
            for line in resp.text.splitlines():
                line = line.strip()
                if line.lower().startswith("sitemap:"):
                    url = line.split(":", 1)[1].strip()
                    logger.info(f"Found sitemap in robots.txt: {url}")
                    return url
    except Exception as e:
        logger.debug(f"Could not fetch robots.txt for {domain}: {e}")

    # Fall back to common sitemap URLs
    candidates = [
        f"https://{domain}/sitemap_index.xml",
        f"https://{domain}/sitemap.xml",
        f"https://{domain}/wp-sitemap.xml",
    ]
    for url in candidates:
        try:
            resp = await client.head(url, timeout=10.0, follow_redirects=True)
            if resp.status_code == 200:
                logger.info(f"Found sitemap at: {url}")
                return url
        except Exception:
            continue

    return None


async def _parse_sitemap_index(client: httpx.AsyncClient, url: str) -> list[str]:
    """Parse a sitemap index XML and return child sitemap URLs."""
    try:
        resp = await client.get(url, timeout=30.0, follow_redirects=True)
        if resp.status_code != 200:
            return []
        return _extract_sitemap_index_urls(resp.text)
    except Exception as e:
        logger.warning(f"Error parsing sitemap index {url}: {e}")
        return []


def _extract_sitemap_index_urls(xml_text: str) -> list[str]:
    """Extract sitemap URLs from a sitemap index XML string."""
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return []

    urls = []
    # Try with namespace
    for sitemap in root.findall("sm:sitemap", SITEMAP_NS):
        loc = sitemap.find("sm:loc", SITEMAP_NS)
        if loc is not None and loc.text:
            urls.append(loc.text.strip())

    # Try without namespace if nothing found
    if not urls:
        for sitemap in root.iter():
            if sitemap.tag.endswith("}sitemap") or sitemap.tag == "sitemap":
                for child in sitemap:
                    if child.tag.endswith("}loc") or child.tag == "loc":
                        if child.text:
                            urls.append(child.text.strip())

    return urls


async def _parse_sitemap(client: httpx.AsyncClient, url: str) -> list[dict]:
    """Parse a sitemap XML and return article URLs with lastmod."""
    try:
        resp = await client.get(url, timeout=30.0, follow_redirects=True)
        if resp.status_code != 200:
            return []
        return _extract_sitemap_urls(resp.text)
    except Exception as e:
        logger.warning(f"Error parsing sitemap {url}: {e}")
        return []


def _extract_sitemap_urls(xml_text: str) -> list[dict]:
    """Extract URLs and lastmod from a sitemap XML string."""
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return []

    results = []

    # Try with namespace
    for url_elem in root.findall("sm:url", SITEMAP_NS):
        loc = url_elem.find("sm:loc", SITEMAP_NS)
        lastmod = url_elem.find("sm:lastmod", SITEMAP_NS)
        if loc is not None and loc.text:
            results.append({
                "url": loc.text.strip(),
                "lastmod": lastmod.text.strip() if lastmod is not None and lastmod.text else None,
                "source": "live",
            })

    # Try without namespace if nothing found
    if not results:
        for url_elem in root.iter():
            if url_elem.tag.endswith("}url") or url_elem.tag == "url":
                loc_text = None
                lastmod_text = None
                for child in url_elem:
                    tag = child.tag.split("}")[-1] if "}" in child.tag else child.tag
                    if tag == "loc" and child.text:
                        loc_text = child.text.strip()
                    elif tag == "lastmod" and child.text:
                        lastmod_text = child.text.strip()
                if loc_text:
                    results.append({
                        "url": loc_text,
                        "lastmod": lastmod_text,
                        "source": "live",
                    })

    return results
