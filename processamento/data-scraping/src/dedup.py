import logging
from collections import defaultdict

from .utils import normalize_url

logger = logging.getLogger(__name__)


def deduplicate(
    arquivo_records: list[dict],
    wayback_records: list[dict],
    sitemap_records: list[dict],
    handler,
) -> list[dict]:
    """Merge and deduplicate records from all three sources.
    
    Returns a list of fetch tasks, each with:
      {url, timestamp, source, digest, fetch_url}
    
    Source priority: live > arquivo > wayback
    (unless handler.PREFER_ARCHIVE is True, then: arquivo > wayback > live)
    """
    prefer_archive = getattr(handler, "PREFER_ARCHIVE", False)
    archive_priority = getattr(handler, "ARCHIVE_PRIORITY", ("arquivo", "wayback"))
    # Group all records by normalized URL
    by_url: dict[str, list[dict]] = defaultdict(list)

    for rec in arquivo_records:
        norm = normalize_url(rec["url"])
        if handler.is_article_url(rec["url"]):
            by_url[norm].append(rec)

    for rec in wayback_records:
        norm = normalize_url(rec["url"])
        if handler.is_article_url(rec["url"]):
            by_url[norm].append(rec)

    # Sitemap URLs are already article URLs — pass through filter anyway for safety
    sitemap_urls = set()
    for rec in sitemap_records:
        norm = normalize_url(rec["url"])
        if handler.is_article_url(rec["url"]):
            sitemap_urls.add(norm)
            by_url[norm].append(rec)

    # For each unique URL, pick the best fetch source
    tasks = []
    for norm_url, records in by_url.items():
        task = _pick_best_record(norm_url, records, sitemap_urls, prefer_archive, archive_priority)
        if task:
            tasks.append(task)

    total_arquivo = sum(1 for r in tasks if r["source"] == "arquivo")
    total_wayback = sum(1 for r in tasks if r["source"] == "wayback")
    total_live = sum(1 for r in tasks if r["source"] == "live")
    logger.info(
        f"Deduplicated to {len(tasks)} unique articles "
        f"(live={total_live}, arquivo={total_arquivo}, wayback={total_wayback})"
    )

    return tasks


def _pick_best_record(norm_url: str, records: list[dict], sitemap_urls: set[str],
                      prefer_archive: bool = False,
                      archive_priority: tuple = ("arquivo", "wayback")) -> dict | None:
    """Pick the best source for fetching a URL.
    
    Priority: live > arquivo > wayback.
    If prefer_archive is True: arquivo > wayback (skip live entirely).
    For CDX records with same URL, prefer earliest timestamp per distinct digest.
    """
    # Collapse CDX records by digest
    by_digest: dict[str, list[dict]] = defaultdict(list)
    for rec in records:
        if rec.get("source") in ("arquivo", "wayback"):
            digest = rec.get("digest", "unknown")
            by_digest[digest].append(rec)

    # If URL is in live sitemaps and we don't prefer archive, use live
    if norm_url in sitemap_urls and not prefer_archive:
        # Find the live record
        for rec in records:
            if rec.get("source") == "live":
                return {
                    "url": rec["url"],
                    "timestamp": None,
                    "source": "live",
                    "digest": None,
                    "fetch_url": rec["url"],
                }

    if not by_digest:
        # No CDX records — fall back to live only if not preferring archive
        if not prefer_archive:
            for rec in records:
                if rec.get("source") == "live":
                    return {
                        "url": rec["url"],
                        "timestamp": None,
                        "source": "live",
                        "digest": None,
                        "fetch_url": rec["url"],
                    }
        return None

    # Pick one representative per digest (earliest timestamp)
    candidates = []
    for digest, recs in by_digest.items():
        recs.sort(key=lambda r: r.get("timestamp", ""))
        candidates.append(recs[0])

    # Pick the best candidate — use archive_priority ordering
    priority = {src: i for i, src in enumerate(archive_priority)}
    candidates.sort(key=lambda r: (priority.get(r["source"], 99), r.get("timestamp", "")))
    best = candidates[0]

    return {
        "url": best["url"],
        "timestamp": best["timestamp"],
        "source": best["source"],
        "digest": best.get("digest"),
        "fetch_url": None,  # Will be built by article.py
    }
