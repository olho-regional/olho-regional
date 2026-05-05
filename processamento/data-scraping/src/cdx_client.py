import asyncio
import json
import logging
from pathlib import Path

import httpx

from .utils import RateLimiter, retry_async

logger = logging.getLogger(__name__)

ARQUIVO_CDX_URL = "https://arquivo.pt/wayback/cdx"
WAYBACK_CDX_URL = "https://web.archive.org/cdx/search/cdx"


async def fetch_oldest_cdx(
    client: httpx.AsyncClient,
    domain: str,
    source: str,
) -> dict | None:
    """Fetch the oldest CDX record for a domain from arquivo or wayback.

    Returns {url, timestamp, source} or None if no records found.
    """
    if source == "arquivo":
        params = {
            "url": domain,
            "matchType": "domain",
            "output": "json",
            "limit": 1,
            "from": "19960101",
            "to": "20261231",
            "filter": ["=mime:text/html", "=status:200"],
        }
        resp = await _fetch_cdx(client, ARQUIVO_CDX_URL, params)
        if resp is None:
            return None
        batch = _parse_arquivo_response(resp, "arquivo")
        return batch[0] if batch else None

    elif source == "wayback":
        params = {
            "url": f"*.{domain}",
            "output": "json",
            "limit": 1,
            "from": "19960101",
            "to": "20261231",
            "filter": ["mimetype:text/html", "statuscode:200"],
            "fl": "urlkey,timestamp,original,mimetype,statuscode,digest,length",
        }
        resp = await _fetch_cdx(client, WAYBACK_CDX_URL, params)
        if resp is None:
            return None
        try:
            rows = resp.json()
        except Exception:
            return None
        if not rows or len(rows) <= 1:
            return None
        # rows[0] is header, rows[1] is first data row
        row = rows[1]
        if len(row) < 6:
            return None
        return {
            "url": row[2],
            "timestamp": row[1],
            "source": "wayback",
        }

    return None


async def discover_arquivo(
    client: httpx.AsyncClient,
    domain: str,
    rate_limiter: RateLimiter,
    from_date: str = "19960101",
    to_date: str = "20261231",
    page_limit: int = 10000,
    on_page: callable = None,
    start_offset: int = 0,
    url_prefixes: list[str] | None = None,
) -> int:
    """Discover all HTML captures from arquivo.pt CDX API.
    
    If url_prefixes is provided, makes targeted prefix queries (much faster
    for sites with known article URL patterns). Otherwise does a domain-wide scan.
    Returns total record count.
    """
    if url_prefixes:
        return await _discover_arquivo_prefixes(
            client, rate_limiter, from_date, to_date, page_limit, on_page, url_prefixes,
        )
    return await _discover_arquivo_domain(
        client, domain, rate_limiter, from_date, to_date, page_limit, on_page, start_offset,
    )


async def _discover_arquivo_prefixes(
    client, rate_limiter, from_date, to_date, page_limit, on_page, url_prefixes,
):
    """Query CDX for each URL prefix separately. Much more efficient for sites
    with known article URL patterns (avoids scanning millions of junk records)."""
    grand_total = 0
    prefix_page_limit = min(page_limit, 100000)
    for prefix in url_prefixes:
        offset = 0
        empty_pages = 0
        while True:
            params = {
                "url": prefix,
                "matchType": "prefix",
                "output": "json",
                "limit": prefix_page_limit,
                "offset": offset,
                "from": from_date,
                "to": to_date,
                "filter": ["=mime:text/html", "=status:200"],
            }

            async with rate_limiter:
                resp = await _fetch_cdx(client, ARQUIVO_CDX_URL, params)

            if resp is None:
                break

            batch = _parse_arquivo_response(resp, "arquivo")
            if not batch:
                break

            grand_total += len(batch)
            new_unique = 0
            if on_page:
                new_unique = on_page(batch, grand_total) or 0

            logger.debug(f"arquivo CDX prefix={prefix} offset={offset} got {len(batch)} ({new_unique} new unique, total: {grand_total})")

            # Early stop: if 5 consecutive pages yield 0 new URLs, skip rest of prefix
            if new_unique == 0:
                empty_pages += 1
                if empty_pages >= 5:
                    logger.info(f"arquivo CDX prefix={prefix}: no new URLs for {empty_pages} pages, skipping rest")
                    break
            else:
                empty_pages = 0

            if len(batch) < prefix_page_limit:
                break
            offset += prefix_page_limit

    return grand_total


async def _discover_arquivo_domain(
    client, domain, rate_limiter, from_date, to_date, page_limit, on_page, start_offset,
):
    """Domain-wide CDX scan. Used when no URL prefixes are known."""
    total_count = start_offset
    offset = start_offset
    empty_pages = 0  # Track pages with 0 new unique URLs

    while True:
        params = {
            "url": domain,
            "matchType": "domain",
            "output": "json",
            "limit": page_limit,
            "offset": offset,
            "from": from_date,
            "to": to_date,
            "filter": ["=mime:text/html", "=status:200"],
        }

        async with rate_limiter:
            resp = await _fetch_cdx(client, ARQUIVO_CDX_URL, params)

        if resp is None:
            break

        batch = _parse_arquivo_response(resp, "arquivo")
        if not batch:
            break

        total_count += len(batch)
        new_unique = 0
        if on_page:
            new_unique = on_page(batch, total_count) or 0

        logger.debug(f"arquivo CDX offset={offset} got {len(batch)} records ({new_unique} new unique, total: {total_count})")

        # Early stop: if 20 consecutive pages (of 1000) yield 0 new URLs, stop scanning
        if new_unique == 0:
            empty_pages += 1
            if empty_pages >= 20:
                logger.info(
                    f"arquivo CDX domain={domain}: no new URLs for {empty_pages} consecutive pages "
                    f"({total_count:,} records scanned), stopping early"
                )
                break
        else:
            empty_pages = 0

        if len(batch) < page_limit:
            break
        offset += page_limit

    return total_count


def _parse_arquivo_response(resp, source: str) -> list[dict]:
    """Parse CDX JSONL response into record dicts."""
    text = resp.text.strip()
    if not text:
        return []
    batch = []
    for line in text.split("\n"):
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        record = {
            "url": obj.get("url", ""),
            "timestamp": obj.get("timestamp", ""),
            "digest": obj.get("digest", ""),
            "source": source,
        }
        if record["url"]:
            batch.append(record)
    return batch


async def discover_wayback(
    client: httpx.AsyncClient,
    domain: str,
    rate_limiter: RateLimiter,
    from_date: str = "19960101",
    to_date: str = "20261231",
    page_limit: int = 10000,
    on_page: callable = None,
) -> int:
    """Discover all HTML captures from Wayback Machine CDX API.
    
    Uses resumeKey pagination + collapse=digest.
    Returns total record count.
    """
    total_count = 0
    resume_key = None
    empty_pages = 0

    while True:
        params = {
            "url": domain,
            "matchType": "domain",
            "output": "json",
            "limit": page_limit,
            "from": from_date,
            "to": to_date,
            "filter": ["mimetype:text/html", "statuscode:200"],
            "collapse": "digest",
            "showResumeKey": "true",
            "fl": "urlkey,timestamp,original,mimetype,statuscode,digest,length",
        }
        if resume_key:
            params["resumeKey"] = resume_key

        async with rate_limiter:
            resp = await _fetch_cdx(client, WAYBACK_CDX_URL, params)

        if resp is None:
            break

        try:
            rows = resp.json()
        except Exception:
            logger.warning("Wayback CDX returned non-JSON response")
            break

        if not rows or len(rows) <= 1:
            break

        # First row is header
        header = rows[0]
        data_rows = rows[1:]

        # Check for resume key (last row with exactly 2 empty-ish elements)
        new_resume_key = None
        if data_rows and len(data_rows[-1]) <= 2:
            new_resume_key = data_rows[-1][0] if data_rows[-1] else None
            data_rows = data_rows[:-1]

        batch = []
        for row in data_rows:
            if len(row) < 6:
                continue
            record = {
                "url": row[2],  # original
                "timestamp": row[1],
                "digest": row[5],
                "source": "wayback",
            }
            batch.append(record)

        if batch:
            total_count += len(batch)
            new_unique = 0
            if on_page:
                new_unique = on_page(batch, total_count) or 0

            # Early stop: if 20 consecutive pages yield 0 new unique URLs, stop
            if new_unique == 0:
                empty_pages += 1
                if empty_pages >= 20:
                    logger.info(f"wayback CDX: no new URLs for {empty_pages} pages, stopping early at {total_count:,} records")
                    break
            else:
                empty_pages = 0

        logger.debug(f"wayback CDX got {len(batch)} records (total: {total_count})")

        if new_resume_key and new_resume_key != resume_key:
            resume_key = new_resume_key
        else:
            break

    return total_count


@retry_async(max_attempts=8, backoff_base=2.0)
async def _fetch_cdx(client: httpx.AsyncClient, url: str, params: dict) -> httpx.Response | None:
    try:
        resp = await client.get(url, params=params, timeout=httpx.Timeout(connect=15.0, read=120.0, write=15.0, pool=15.0))
        if resp.status_code == 200:
            return resp
        if resp.status_code == 429:
            # Rate limited — wait extra before retry
            retry_after = int(resp.headers.get("Retry-After", 30))
            logger.warning(f"CDX {url} rate limited (429), waiting {retry_after}s")
            await asyncio.sleep(retry_after)
            raise httpx.HTTPStatusError(
                f"CDX returned 429",
                request=resp.request,
                response=resp,
            )
        if resp.status_code in {500, 502, 503, 504}:
            raise httpx.HTTPStatusError(
                f"CDX returned {resp.status_code}",
                request=resp.request,
                response=resp,
            )
        logger.warning(f"CDX {url} returned {resp.status_code}")
        return None
    except httpx.TimeoutException:
        raise
    except httpx.HTTPStatusError:
        raise
    except Exception as e:
        logger.warning(f"CDX request error: {e}")
        raise
