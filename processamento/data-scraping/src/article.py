import asyncio
import logging
from datetime import datetime, timezone

import httpx

from .sites.base import BaseSiteHandler
from .utils import content_hash, url_id, RateLimiter

logger = logging.getLogger(__name__)

# Transient errors worth retrying (HTTP/2 resets, connection drops)
_RETRYABLE_ERRORS = ("ConnectionTerminated", "RemoteProtocolError", "ConnectionReset", "Server disconnected")

# Signatures of bot-challenge / anti-bot / CAPTCHA pages archived by crawlers.
# Checked against HTML smaller than 15KB (real articles are larger).
_BOT_CHALLENGE_SIGNATURES = (
    "Please wait while your request is being verified",  # SAPO/openresty
    "Checking your browser before accessing",            # Cloudflare classic
    "Just a moment...",                                   # Cloudflare new
    "Enable JavaScript and cookies to continue",         # Cloudflare
    "Attention Required! | Cloudflare",                  # Cloudflare block
    "DDoS protection by",                                # Generic DDoS guard
    "Pardon Our Interruption",                           # Incapsula/Imperva
    "Access denied | ",                                  # Various WAFs
    "CAPTCHA"
)
_BOT_CHALLENGE_MAX_SIZE = 15_000  # Only check small pages (bot pages are typically < 5KB)


def _is_bot_challenge(html: str) -> bool:
    """Detect archived anti-bot / challenge pages."""
    if len(html) > _BOT_CHALLENGE_MAX_SIZE:
        return False
    return any(sig in html for sig in _BOT_CHALLENGE_SIGNATURES)


async def fetch_and_extract(
    client: httpx.AsyncClient,
    task: dict,
    handler: BaseSiteHandler,
    rate_limiter: RateLimiter,
    domain: str,
    config: dict,
) -> tuple[dict | None, dict | None]:
    """Fetch an article page and extract metadata.
    
    Returns (article_dict, None) on success,
            (None, quality_record) on failure.
    """
    url = task["url"]
    source = task["source"]
    timestamp = task.get("timestamp")

    # Build the fetch URL
    if source == "live":
        fetch_url = url
    else:
        fetch_url = handler.build_archive_url(source, timestamp, url)

    # Fetch the page with retry for transient connection errors
    html = None
    max_retries = 3
    for attempt in range(max_retries):
        try:
            async with rate_limiter:
                resp = await client.get(fetch_url, timeout=config.get("timeout_seconds", 15), follow_redirects=True)
            if resp.status_code != 200:
                return None, _quality_record(url, fetch_url, timestamp, domain, handler.NAME,
                                              f"http_{resp.status_code}")
            html = resp.text
            break
        except httpx.TimeoutException:
            return None, _quality_record(url, fetch_url, timestamp, domain, handler.NAME, "timeout")
        except Exception as e:
            err_str = str(e)
            if attempt < max_retries - 1 and any(s in err_str for s in _RETRYABLE_ERRORS):
                await asyncio.sleep(1 * (attempt + 1))
                continue
            return None, _quality_record(url, fetch_url, timestamp, domain, handler.NAME, f"fetch_error: {e}")

    if not html or len(html) < 100:
        return None, _quality_record(url, fetch_url, timestamp, domain, handler.NAME, "empty_response")

    # Detect archived bot-challenge / anti-bot pages (SAPO, Cloudflare, etc.)
    if _is_bot_challenge(html):
        return None, _quality_record(url, fetch_url, timestamp, domain, handler.NAME,
                                      "bot_challenge", html_length=len(html))

    # Extract article
    try:
        extracted = handler.extract(html, url)
    except Exception as e:
        logger.debug(f"Extraction error for {url}: {e}")
        return None, _quality_record(url, fetch_url, timestamp, domain, handler.NAME,
                                      f"extraction_failed:{e}", html_length=len(html))

    if extracted is None:
        return None, _quality_record(url, fetch_url, timestamp, domain, handler.NAME,
                                      f"extraction_failed:None", html_length=len(html))

    text = extracted.get("text", "")
    min_length = config.get("min_text_length", 100)
    if len(text) < min_length:
        return None, _quality_record(url, fetch_url, timestamp, domain, handler.NAME,
                                      "text_too_short", text_length=len(text))

    if not extracted.get("title"):
        return None, _quality_record(url, fetch_url, timestamp, domain, handler.NAME,
                                      "no_title", text_length=len(text))

    # Build article record
    now = datetime.now(timezone.utc).isoformat()
    article = {
        "id": url_id(url),
        "url": url,
        "title": extracted["title"],
        "subtitle": extracted.get("subtitle"),
        "text": text,
        "date": extracted.get("date"),
        "author": extracted.get("author"),
        "agency": extracted.get("agency"),
        "categories": extracted.get("categories", []),
        "section": extracted.get("section"),
        "source": source,
        "timestamp": timestamp,
        "archive_url": fetch_url if source != "live" else None,
        "domain": domain,
        "text_hash": content_hash(text),
        "text_length": len(text),
        "fetched_at": now,
        "extractor": handler.NAME,
    }

    return article, None


def _quality_record(
    url: str,
    archive_url: str,
    timestamp: str | None,
    domain: str,
    extractor: str,
    reason: str,
    text_length: int = 0,
    html_length: int = 0,
) -> dict:
    return {
        "url": url,
        "archive_url": archive_url,
        "timestamp": timestamp,
        "domain": domain,
        "reason": reason,
        "text_length": text_length,
        "html_length": html_length,
        "extractor": extractor,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
    }
