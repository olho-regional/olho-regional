import asyncio
import logging
from datetime import datetime, timezone

import httpx

from .article import fetch_and_extract
from .cdx_client import discover_arquivo, discover_wayback
from .dedup import deduplicate
from .progress import ProgressTracker
from .sitemap_client import discover_live_urls
from .sites.registry import get_handler
from .stats import compute_stats, print_stats
from .storage import append_jsonl, load_errored_urls, load_processed_urls, load_state, purge_quality_urls, read_jsonl, save_state
from .utils import RateLimiter, domain_from_url, get_data_dir, normalize_url

logger = logging.getLogger(__name__)

FLUSH_INTERVAL = 50  # Flush to disk every N articles
USER_AGENT = "olho-regional/1.0 (news-archive-research; +https://github.com/olho-regional/olho-regional)"


class TimeoutManager:
    """Adaptive timeout that decreases when a site has many consecutive timeouts."""

    def __init__(self, initial: float = 15.0, minimum: float = 5.0, threshold: int = 5):
        self._initial = initial
        self._minimum = minimum
        self._threshold = threshold
        self._consecutive_timeouts = 0
        self._current = initial

    def record_success(self):
        self._consecutive_timeouts = 0
        self._current = self._initial

    def record_timeout(self):
        self._consecutive_timeouts += 1
        if self._consecutive_timeouts >= self._threshold:
            self._current = self._minimum

    @property
    def timeout(self) -> float:
        return self._current


async def run_site(domain: str, config: dict, phase: str | None = None, limit: int | None = None,
                   skip_sources: set[str] | None = None, retry: bool = False,
                   shared_rate_limiters: dict | None = None, shared_clients: dict | None = None,
                   max_articles: int | None = None):
    """Run the full pipeline for a single site."""
    handler = get_handler(domain)
    data_dir = get_data_dir(config, domain)
    state = load_state(data_dir)

    logger.info(f"=== Starting pipeline for {domain} (handler: {handler.NAME}) ===")

    conc = config.get("concurrency", {})
    from_date = str(config.get("date_range", {}).get("from", 1996)) + "0101"
    to_date = str(config.get("date_range", {}).get("to", 2026)) + "1231"

    skip = skip_sources or set()

    # Phase A: Discovery
    if phase in (None, "cdx", "tasks"):
        await _phase_discovery(domain, config, data_dir, state, handler, from_date, to_date, conc, skip)

    if phase == "cdx":
        logger.info(f"CDX-only mode complete for {domain}")
        return

    # Phase B: Filter & Deduplicate
    # Only proceed if all discovery sources have completed
    arquivo_done = state.get("arquivo_cdx_done", False)
    wayback_done = state.get("wayback_cdx_done", False)
    sitemap_done = state.get("sitemap_done", False)
    all_discovery_done = arquivo_done and wayback_done and sitemap_done

    if not (arquivo_done or wayback_done or sitemap_done):
        logger.warning(f"Skipping {domain}: no discovery completed yet")
        return

    if not all_discovery_done:
        logger.warning(
            f"{domain}: discovery incomplete (arquivo={'done' if arquivo_done else 'pending'}, "
            f"wayback={'done' if wayback_done else 'pending'}, sitemap={'done' if sitemap_done else 'pending'})"
        )

    tasks_path = data_dir / "tasks.jsonl"
    full_dedup = not skip  # Only a complete dedup (no --skip-*) is authoritative
    has_raw_files = any((data_dir / f).exists() for f in ("cdx_arquivo.jsonl", "cdx_wayback.jsonl", "sitemap_urls.jsonl"))
    tasks_cached = tasks_path.exists() and tasks_path.stat().st_size > 0

    if tasks_cached and (full_dedup or not has_raw_files):
        # Reuse saved task list (always when raw files are gone, or when no skip flags)
        tasks = read_jsonl(tasks_path)
        logger.info(f"Loaded {len(tasks):,} tasks from saved task list")
    elif not has_raw_files and not tasks_cached:
        logger.warning(f"Skipping {domain}: no raw CDX files and no cached tasks")
        return
    else:
        arquivo_records = [] if "arquivo" in skip else read_jsonl(data_dir / "cdx_arquivo.jsonl")
        wayback_records = [] if "wayback" in skip else read_jsonl(data_dir / "cdx_wayback.jsonl")
        sitemap_records = read_jsonl(data_dir / "sitemap_urls.jsonl")

        logger.info(
            f"Loaded: arquivo={len(arquivo_records)}, wayback={len(wayback_records)}, "
            f"sitemap={len(sitemap_records)}"
        )

        tasks = deduplicate(arquivo_records, wayback_records, sitemap_records, handler)

        if full_dedup and all_discovery_done:
            # Save compact task list and clean up large discovery files
            # ONLY delete raw files when ALL discovery is confirmed complete
            tasks_path.unlink(missing_ok=True)
            append_jsonl(tasks_path, tasks)
            logger.info(f"Saved {len(tasks):,} tasks to {tasks_path.name}")

            for raw_file in ("cdx_arquivo.jsonl", "cdx_wayback.jsonl", "sitemap_urls.jsonl"):
                p = data_dir / raw_file
                if p.exists():
                    p.unlink()
                    logger.info(f"Deleted {raw_file} (no longer needed)")
        elif full_dedup:
            # Save tasks but keep raw files (discovery not fully complete)
            tasks_path.unlink(missing_ok=True)
            append_jsonl(tasks_path, tasks)
            logger.warning(
                f"Saved {len(tasks):,} tasks but keeping raw CDX files "
                f"(discovery incomplete — re-run to get full results)"
            )

    state["total_unique_articles"] = len(tasks)
    save_state(data_dir, state)

    if phase == "tasks":
        logger.info(f"Tasks-only mode complete for {domain}: {len(tasks):,} tasks")
        _print_stats(data_dir, domain)
        return

    # Subtract already-processed
    processed = load_processed_urls(data_dir)
    processed_normalized = {normalize_url(u) for u in processed}
    tasks = [t for t in tasks if normalize_url(t["url"]) not in processed_normalized]

    # Skip previously errored pages unless --retry
    if not retry:
        errored = load_errored_urls(data_dir)
        errored_normalized = {normalize_url(u) for u in errored}
        before = len(tasks)
        tasks = [t for t in tasks if normalize_url(t["url"]) not in errored_normalized]
        skipped = before - len(tasks)
        if skipped:
            logger.info(f"Skipping {skipped} previously errored pages (use --retry to retry them)")
    else:
        # Purge old error records for URLs we're about to retry
        retry_urls = {t["url"] for t in tasks}
        removed = purge_quality_urls(data_dir, retry_urls)
        if removed:
            logger.info(f"Purged {removed} old error records for retry")

    logger.info(f"Work queue: {len(tasks)} articles to fetch ({len(processed)} already done)")

    # --max-articles: cap total successful articles (existing + new)
    # Shuffle first so the sample preserves the original time distribution
    if max_articles is not None:
        existing_articles = len(processed)
        remaining_budget = max(0, max_articles - existing_articles)
        if remaining_budget == 0:
            logger.info(f"Already have {existing_articles:} articles (cap: {max_articles:,}) — nothing to fetch")
            _print_stats(data_dir, domain)
            return
        if len(tasks) > remaining_budget:
            import random
            random.shuffle(tasks)
            tasks = tasks[:remaining_budget]
            logger.info(f"Sampled {remaining_budget:,} tasks randomly (cap: {max_articles:,}, existing: {existing_articles:,})")

    if limit:
        tasks = tasks[:limit]
        logger.info(f"Limited to {limit} articles")

    if not tasks:
        logger.info("Nothing to fetch — all articles already processed")
        _print_stats(data_dir, domain)
        return

    # Phase C: Fetch & Extract
    await _phase_fetch(domain, config, data_dir, tasks, handler, conc,
                       shared_rate_limiters=shared_rate_limiters,
                       shared_clients=shared_clients,
                       max_articles=max_articles)

    # Print stats
    _print_stats(data_dir, domain)


async def _phase_discovery(domain, config, data_dir, state, handler, from_date, to_date, conc, skip=None):
    """Run CDX + sitemap discovery.

    (Order: Wayback first → auto-discover URL prefixes → Arquivo (prefix queries).
    This avoids the domain-wide Arquivo CDX scan which can scan hundreds of
    millions of duplicate records on sites with high homepage capture counts.
    """
    skip = skip or set()
    logger.info(f"Phase A: Discovery for {domain}")

    # Shared set so arquivo and wayback cross-dedup URLs
    seen_urls: set[str] = set()

    wayback_proxy = config.get("wayback_proxy")  # e.g. "socks5://127.0.0.1:1080"

    async with httpx.AsyncClient(http2=True, headers={"User-Agent": USER_AGENT}) as client:
        # Rate limiters — arquivo.pt CDX: 250 req/min limit (permanent ban if exceeded)
        arquivo_rl = RateLimiter(
            max_concurrent=conc.get("arquivo", 30),
            max_per_minute=conc.get("arquivo_cdx_max_per_minute", 120),
        )
        wayback_rl = RateLimiter(conc.get("wayback_cdx", 1), delay_ms=conc.get("wayback_cdx_delay_ms", 1500))

        # Sitemaps are independent, run concurrently with CDX
        sitemap_task = asyncio.create_task(_discover_sitemaps_with_save(client, domain, data_dir, state, handler))

        # 1. Wayback CDX first — uses collapse=digest server-side, efficient
        if "wayback" not in skip:
            wb_kwargs = {"http2": True, "headers": {"User-Agent": USER_AGENT}}
            if wayback_proxy:
                logger.info(f"Using proxy for Wayback: {wayback_proxy[0:15]}[...]")
                wb_kwargs["proxy"] = wayback_proxy
            try:
                async with httpx.AsyncClient(**wb_kwargs) as wb_client:
                    await _discover_wayback_with_save(wb_client, domain, wayback_rl, from_date, to_date, data_dir, state, handler, seen_urls)
            except Exception as e:
                logger.error(f"Discovery error (wayback): {e}")
        else:
            logger.info("Skipping Wayback Machine discovery (--skip-wayback)")

        # 2. Arquivo CDX — use auto-discovered prefixes from wayback URLs
        if "arquivo" not in skip:
            # Auto-discover URL prefixes from Wayback results if handler has none
            auto_prefixes = _auto_discover_prefixes(seen_urls, domain, handler)
            try:
                await _discover_arquivo_with_save(client, domain, arquivo_rl, from_date, to_date, data_dir, state, handler, seen_urls, auto_prefixes=auto_prefixes)
            except Exception as e:
                logger.error(f"Discovery error (arquivo): {e}")
        else:
            logger.info("Skipping arquivo.pt discovery (--skip-arquivo)")

        # Wait for sitemaps
        try:
            await sitemap_task
        except Exception as e:
            logger.error(f"Discovery error (sitemap): {e}")

    # Record URL path structure in state for manual CDX_PREFIXES selection
    state["url_prefix_map"] = _build_prefix_map(seen_urls)
    save_state(data_dir, state)


def _build_prefix_map(seen_urls: set[str]) -> dict[str, int]:
    """Build a map of first-path-segment → article count from discovered URLs."""
    from collections import Counter
    from urllib.parse import urlparse

    segment_counts: Counter[str] = Counter()
    root_count = 0
    for url in seen_urls:
        parts = [p for p in urlparse(url).path.strip("/").split("/") if p]
        if len(parts) >= 2:
            segment_counts[parts[0]] += 1
        elif len(parts) == 1:
            root_count += 1

    result = dict(segment_counts.most_common())
    if root_count:
        result["(root)"] = root_count
    return result


def _auto_discover_prefixes(seen_urls: set[str], domain: str, handler) -> list[str]:
    """Extract URL path prefixes from discovered article URLs.

    Groups URLs by their first path segment and builds prefix URLs for
    any segment that has enough articles to be worth a targeted CDX query.
    Falls back to empty (domain-wide scan) if no clear patterns emerge.
    """
    # If handler already defines CDX_PREFIXES, don't auto-discover
    if getattr(handler, "CDX_PREFIXES", []):
        return []

    if not seen_urls:
        return []

    from collections import Counter
    from urllib.parse import urlparse

    segment_counts = Counter()
    for url in seen_urls:
        parsed = urlparse(url)
        parts = [p for p in parsed.path.strip("/").split("/") if p]
        if len(parts) >= 2:
            segment_counts[parts[0]] += 1

    # Build prefix URLs for segments with at least 3 articles
    prefixes = []
    schemes = ["https", "http"]
    hosts = [domain, f"www.{domain}"] if not domain.startswith("www.") else [domain, domain[4:]]
    for segment, count in segment_counts.most_common():
        if count < 3:
            continue
        for scheme in schemes:
            for host in hosts:
                prefixes.append(f"{scheme}://{host}/{segment}/")

    if prefixes:
        unique_segments = sum(1 for _, c in segment_counts.items() if c >= 3)
        logger.info(
            f"Auto-discovered {unique_segments} URL prefix(es) from {len(seen_urls)} Wayback URLs "
            f"→ {len(prefixes)} Arquivo CDX prefix queries"
        )
    else:
        logger.info(f"No URL prefixes discovered from {len(seen_urls)} Wayback URLs — will use domain-wide scan")

    return prefixes


async def _discover_arquivo_with_save(client, domain, rl, from_date, to_date, data_dir, state, handler=None, seen_urls=None, auto_prefixes=None):
    if state.get("arquivo_cdx_done"):
        logger.info("Arquivo CDX already done, skipping")
        return

    # Use targeted prefix queries: handler-defined first, then auto-discovered
    handler_prefixes = getattr(handler, "CDX_PREFIXES", []) if handler else []
    prefixes = handler_prefixes or auto_prefixes or []
    use_prefixes = bool(prefixes)

    if use_prefixes:
        source = "handler" if handler_prefixes else "auto-discovered"
        logger.info(f"Discovering arquivo.pt CDX for {domain} using {len(prefixes)} URL prefixes ({source})...")
    else:
        logger.info(f"Discovering arquivo.pt CDX for {domain} (domain-wide scan)...")

    path = data_dir / "cdx_arquivo.jsonl"
    url_filter = handler.is_article_url if handler else None
    if seen_urls is None:
        seen_urls = set()
    pages = [0]

    if use_prefixes:
        # Prefix mode: always start fresh, dedup by URL in-memory
        path.unlink(missing_ok=True)
        total = [0]
        saved = [0]

        def on_page(batch, total_so_far):
            pages[0] += 1
            filtered = [r for r in batch if url_filter(r["url"])] if url_filter else batch
            unique = []
            for r in filtered:
                norm = normalize_url(r["url"])
                if norm not in seen_urls:
                    seen_urls.add(norm)
                    unique.append(r)
            if unique:
                append_jsonl(path, unique)
            saved[0] += len(unique)
            total[0] = total_so_far
            state["arquivo_cdx_saved"] = saved[0]
            save_state(data_dir, state)
            if pages[0] % 10 == 0:
                logger.info(f"[arquivo CDX] {domain}: scanned {total[0]:,} records, {saved[0]:,} unique article URLs saved")
            return len(unique)  # Used by CDX client for early stopping

        await discover_arquivo(
            client, domain, rl, from_date, to_date,
            on_page=on_page, url_prefixes=prefixes,
        )
    else:
        # Domain-wide mode: filter with handler + dedup by URL
        resume_offset = state.get("arquivo_cdx_offset", 0)
        if resume_offset == 0:
            path.unlink(missing_ok=True)

        total = [resume_offset]
        saved = [state.get("arquivo_cdx_saved", 0)]
        # Load already-saved URLs for resume
        if resume_offset > 0 and path.exists():
            for rec in read_jsonl(path):
                seen_urls.add(normalize_url(rec["url"]))

        def on_page(batch, total_so_far):
            pages[0] += 1
            filtered = [r for r in batch if url_filter(r["url"])] if url_filter else batch
            unique = []
            for r in filtered:
                norm = normalize_url(r["url"])
                if norm not in seen_urls:
                    seen_urls.add(norm)
                    unique.append(r)
            if unique:
                append_jsonl(path, unique)
            saved[0] += len(unique)
            total[0] = total_so_far
            state["arquivo_cdx_offset"] = total_so_far
            state["arquivo_cdx_saved"] = saved[0]
            save_state(data_dir, state)
            if pages[0] % 10 == 0:
                logger.info(f"[arquivo CDX] {domain}: scanned {total[0]:,} records, {saved[0]:,} unique article URLs saved")
            return len(unique)  # Used by CDX client for early stopping

        await discover_arquivo(
            client, domain, rl, from_date, to_date,
            on_page=on_page, start_offset=resume_offset,
        )

    state["arquivo_cdx_done"] = True
    state["arquivo_cdx_count"] = total[0]
    logger.info(f"Arquivo CDX done: {total[0]:,} records scanned, {saved[0]:,} unique article URLs saved")


async def _discover_wayback_with_save(client, domain, rl, from_date, to_date, data_dir, state, handler=None, seen_urls=None):
    if seen_urls is None:
        seen_urls = set()

    if state.get("wayback_cdx_done"):
        logger.info("Wayback CDX already done, loading saved URLs for cross-dedup")
        path = data_dir / "cdx_wayback.jsonl"
        if path.exists():
            for rec in read_jsonl(path):
                seen_urls.add(normalize_url(rec["url"]))
            logger.info(f"Loaded {len(seen_urls)} Wayback URLs from cache")
        return

    logger.info(f"Discovering Wayback Machine CDX for {domain}...")
    path = data_dir / "cdx_wayback.jsonl"
    path.unlink(missing_ok=True)

    total = [0]
    saved = [0]
    pages = [0]
    url_filter = handler.is_article_url if handler else None

    def on_page(batch, total_so_far):
        pages[0] += 1
        filtered = [r for r in batch if url_filter(r["url"])] if url_filter else batch
        unique = []
        for r in filtered:
            norm = normalize_url(r["url"])
            if norm not in seen_urls:
                seen_urls.add(norm)
                unique.append(r)
        if unique:
            append_jsonl(path, unique)
        saved[0] += len(unique)
        total[0] = total_so_far
        state["wayback_cdx_saved"] = saved[0]
        state["wayback_cdx_scanned"] = total[0]
        save_state(data_dir, state)
        if pages[0] % 10 == 0:
            logger.info(f"[wayback CDX] {domain}: scanned {total[0]:,} records, {saved[0]:,} unique article URLs saved")
        return len(unique)  # Used by CDX client for early stopping

    await discover_wayback(client, domain, rl, from_date, to_date, on_page=on_page)
    state["wayback_cdx_done"] = True
    state["wayback_cdx_count"] = total[0]
    logger.info(f"Wayback CDX done: {total[0]:,} records scanned, {saved[0]:,} unique article URLs saved")


async def _discover_sitemaps_with_save(client, domain, data_dir, state, handler=None):
    if state.get("sitemap_done"):
        logger.info("Sitemap discovery already done, skipping")
        return

    # Use handler's custom discovery if available
    if handler and hasattr(handler, "discover_urls"):
        logger.info(f"Using custom discovery for {domain}...")
        records = await handler.discover_urls(client)
    else:
        logger.info(f"Discovering live sitemaps for {domain}...")
        records = await discover_live_urls(client, domain)
    path = data_dir / "sitemap_urls.jsonl"
    path.unlink(missing_ok=True)
    if records:
        append_jsonl(path, records)
    state["sitemap_done"] = True
    state["sitemap_count"] = len(records)
    logger.info(f"Sitemaps: {len(records)} URLs saved")


async def _phase_fetch(domain, config, data_dir, tasks, handler, conc,
                       shared_rate_limiters=None, shared_clients=None,
                       max_articles: int | None = None):
    """Fetch and extract all articles.
    
    When shared_rate_limiters and shared_clients are provided (parallel mode),
    uses those instead of creating new ones. This ensures rate limits are
    enforced globally across all parallel sites.
    """
    logger.info(f"Phase C: Fetching {len(tasks)} articles for {domain}")

    # Group tasks by source for rate limiting
    live_tasks = [t for t in tasks if t["source"] == "live"]
    arquivo_tasks = [t for t in tasks if t["source"] == "arquivo"]
    wayback_tasks = [t for t in tasks if t["source"] == "wayback"]

    logger.info(
        f"Tasks by source: live={len(live_tasks)}, arquivo={len(arquivo_tasks)}, "
        f"wayback={len(wayback_tasks)}"
    )

    owns_clients = shared_clients is None

    if shared_rate_limiters:
        rate_limiters = shared_rate_limiters
    else:
        wayback_fetch_conc = conc.get("wayback_fetch", 20)
        rate_limiters = {
            "live": RateLimiter(conc.get("live", 10)),
            "arquivo": RateLimiter(
                max_concurrent=conc.get("arquivo", 50),
                max_per_minute=conc.get("arquivo_fetch_max_per_minute", 3000),
            ),
            "wayback": RateLimiter(
                wayback_fetch_conc,
                delay_ms=conc.get("wayback_fetch_delay_ms", 0),
            ),
        }

    articles_path = data_dir / "articles.jsonl"
    quality_path = data_dir / "quality.jsonl"

    progress = ProgressTracker(domain, len(tasks))
    progress.start()

    article_buffer = []
    quality_buffer = []

    timeout_mgr = TimeoutManager(
        initial=config.get("timeout_seconds", 15),
        minimum=5.0,
        threshold=5,
    )

    wayback_proxy = config.get("wayback_proxy")
    wayback_fetch_conc = conc.get("wayback_fetch", 50)

    if owns_clients:
        wb_kwargs = {
            "http2": True,
            "headers": {"User-Agent": USER_AGENT},
            "limits": httpx.Limits(max_connections=wayback_fetch_conc + 10),
        }
        if wayback_proxy:
            logger.info(f"Using rotating proxy for Wayback fetches: {wayback_proxy[0:15]}[...] ({wayback_fetch_conc} concurrent)")
            wb_kwargs["proxy"] = wayback_proxy
        else:
            logger.warning("No wayback_proxy configured — Wayback fetches will use direct IP")
        client_ctx = httpx.AsyncClient(http2=True, headers={"User-Agent": USER_AGENT}, limits=httpx.Limits(max_connections=100))
        wb_client_ctx = httpx.AsyncClient(**wb_kwargs)
    else:
        client_ctx = None
        wb_client_ctx = None

    async def _run_fetch(client, wb_client):
        nonlocal article_buffer, quality_buffer

        clients = {
            "live": client,
            "arquivo": client,
            "wayback": wb_client,
        }

        all_tasks_ordered = live_tasks + arquivo_tasks + wayback_tasks
        sem = asyncio.Semaphore(80)
        success_count = 0
        # Track cap: existing articles + new successes
        existing_count = sum(1 for _ in open(data_dir / "articles.jsonl")) if (data_dir / "articles.jsonl").exists() else 0

        async def process_one(task):
            async with sem:
                rl = rate_limiters[task["source"]]
                src_client = clients[task["source"]]
                # Pass adaptive timeout
                task_config = {**config, "timeout_seconds": timeout_mgr.timeout}
                article, quality = await fetch_and_extract(
                    src_client, task, handler, rl, domain, task_config,
                )
                # Track timeouts for adaptive behavior
                if quality and quality.get("reason") == "timeout":
                    timeout_mgr.record_timeout()
                elif article:
                    timeout_mgr.record_success()
                return article, quality

        batch_size = 200
        interrupted = False
        for i in range(0, len(all_tasks_ordered), batch_size):
            batch = all_tasks_ordered[i:i + batch_size]
            coros = [process_one(t) for t in batch]
            try:
                results = await asyncio.gather(*coros, return_exceptions=True)
            except (KeyboardInterrupt, asyncio.CancelledError):
                logger.warning("Interrupted — flushing buffers to disk...")
                interrupted = True
                results = []

            for result in results:
                if isinstance(result, Exception):
                    logger.debug(f"Task exception: {result}")
                    progress.update(error=True)
                    continue

                article, quality = result
                if article:
                    article_buffer.append(article)
                    progress.update(success=True)
                    success_count += 1
                elif quality:
                    quality_buffer.append(quality)
                    progress.update(error=True)
                else:
                    progress.update(error=True)

            if article_buffer:
                append_jsonl(articles_path, article_buffer)
                article_buffer.clear()
            if quality_buffer:
                append_jsonl(quality_path, quality_buffer)
                quality_buffer.clear()

            if interrupted:
                break

            # Stop early if we've hit the article cap
            if max_articles is not None and (existing_count + success_count) >= max_articles:
                logger.info(f"Reached article cap ({max_articles:,}) — stopping early")
                break

    if owns_clients:
        async with client_ctx as client, wb_client_ctx as wb_client:
            await _run_fetch(client, wb_client)
    else:
        await _run_fetch(shared_clients["arquivo"], shared_clients["wayback"])

    # Flush remaining
    if article_buffer:
        append_jsonl(articles_path, article_buffer)
    if quality_buffer:
        append_jsonl(quality_path, quality_buffer)

    progress.finish()


def _print_stats(data_dir, domain):
    articles = read_jsonl(data_dir / "articles.jsonl")
    quality = read_jsonl(data_dir / "quality.jsonl")
    state = load_state(data_dir)
    stats = compute_stats(articles, quality, state, domain)
    print_stats(stats)


async def run_sites_parallel(sites: list[str], config: dict, phase: str | None = None,
                             limit: int | None = None, skip_sources: set[str] | None = None,
                             retry: bool = False, parallel: int = 3,
                             max_articles: int | None = None):
    """Run multiple sites concurrently with shared rate limiters.

    Rate limiters for arquivo.pt (CDX + fetch) and Wayback are created once
    and shared across all concurrent sites, so the global rate limits are
    never exceeded regardless of --parallel N.
    """
    conc = config.get("concurrency", {})
    wayback_proxy = config.get("wayback_proxy")
    wayback_fetch_conc = conc.get("wayback_fetch", 50)

    # Shared rate limiters — one per API endpoint, shared across all sites
    shared_rate_limiters = {
        "live": RateLimiter(conc.get("live", 10)),
        "arquivo": RateLimiter(
            max_concurrent=conc.get("arquivo", 50),
            max_per_minute=conc.get("arquivo_fetch_max_per_minute", 3000),
        ),
        "wayback": RateLimiter(
            wayback_fetch_conc,
            delay_ms=conc.get("wayback_fetch_delay_ms", 0),
        ),
    }

    # Shared HTTP clients
    wb_kwargs = {
        "http2": True,
        "headers": {"User-Agent": USER_AGENT},
        "limits": httpx.Limits(max_connections=wayback_fetch_conc + 10),
    }
    if wayback_proxy:
        wb_kwargs["proxy"] = wayback_proxy

    async with (
        httpx.AsyncClient(http2=True, headers={"User-Agent": USER_AGENT},
                          limits=httpx.Limits(max_connections=200)) as client,
        httpx.AsyncClient(**wb_kwargs) as wb_client,
    ):
        shared_clients = {"arquivo": client, "wayback": wb_client}

        sem = asyncio.Semaphore(parallel)

        async def run_one(domain):
            async with sem:
                try:
                    await run_site(
                        domain, config, phase=phase, limit=limit,
                        skip_sources=skip_sources, retry=retry,
                        shared_rate_limiters=shared_rate_limiters,
                        shared_clients=shared_clients,
                        max_articles=max_articles,
                    )
                except Exception as e:
                    logger.error(f"Failed to process {domain}: {e}", exc_info=True)

        # Launch all sites but semaphore limits concurrency to N
        await asyncio.gather(*[run_one(d) for d in sites])
