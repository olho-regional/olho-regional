#!/usr/bin/env python3
"""News Collector — arquivo.pt + Wayback Machine + Live Sitemaps

Collects all news articles from archived and live sources
for newspapers listed in jornais.csv.

Usage:
    python collect.py                          # Full pipeline for all sites
    python collect.py --site osetubalense.com  # Single site
    python collect.py --phase cdx              # CDX discovery only
    python collect.py --reset osetubalense.com # Reset a site
    python collect.py --retry --site domain    # Retry previously errored pages
    python collect.py status                   # Show collection status
    python collect.py status --site domain     # Detailed status for one site
"""

import argparse
import asyncio
import logging
import shutil
import sys
from pathlib import Path

from src.pipeline import run_site
from src.status import show_status
from src.storage import load_state, save_state
from src.utils import load_config, parse_jornais_csv, get_data_dir
from src.cdx_client import fetch_oldest_cdx


def main():
    parser = argparse.ArgumentParser(description="News article collector from arquivo.pt, Wayback Machine, and live sites")
    parser.add_argument("command", nargs="?", default="collect", choices=["collect", "status", "oldest", "diagnose"],
                        help="Command to run (default: collect)")
    parser.add_argument("--site", type=str, help="Single site domain to process")
    parser.add_argument("--phase", type=str, choices=["cdx", "tasks", "fetch"], help="Run only a specific phase (cdx=discovery, tasks=dedup, fetch=download)")
    parser.add_argument("--reset", type=str, metavar="DOMAIN", help="Reset state for a site (clear data)")
    parser.add_argument("--config", type=str, default="config.yaml", help="Config file path")
    parser.add_argument("--limit", type=int, help="Max articles to fetch (for testing)")
    parser.add_argument("--skip-wayback", action="store_true", help="Skip Wayback Machine discovery and fetching")
    parser.add_argument("--skip-arquivo", action="store_true", help="Skip arquivo.pt discovery and fetching")
    parser.add_argument("--retry", action="store_true", help="Retry previously errored pages (default: skip them)")
    parser.add_argument("--max-articles", type=int, default=50_000, metavar="N", help="Cap successful articles per site (random sample to preserve time distribution, default: 50000)")
    parser.add_argument("--parallel", type=int, default=1, metavar="N", help="Run N sites concurrently (default: 1). Rate limits are shared across sites.")
    parser.add_argument("--no-wayback-proxy", action="store_true", help="Fetch Wayback pages directly without proxy (saves proxy quota, slower)")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose logging")
    args = parser.parse_args()

    # Setup logging
    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )
    # Reduce noise from httpx/httpcore
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("trafilatura").setLevel(logging.ERROR)
    logging.getLogger("hpack").setLevel(logging.WARNING)

    config = load_config(args.config)

    # Handle reset
    if args.reset:
        _reset_site(config, args.reset)
        return

    # Handle status
    if args.command == "status":
        show_status(config, site=args.site)
        return

    # Handle oldest
    if args.command == "oldest":
        sites = _get_sites(args.site)
        asyncio.run(_show_oldest(sites, config))
        return

    # Handle diagnose
    if args.command == "diagnose":
        if not args.site:
            print("diagnose requires --site <domain>", file=sys.stderr)
            sys.exit(1)
        from src.status import diagnose_site
        diagnose_site(config, args.site)
        return

    # Collect
    sites = _get_sites(args.site)
    if not sites:
        print("No sites to process", file=sys.stderr)
        sys.exit(1)

    skip_sources = set()
    if args.skip_wayback:
        skip_sources.add("wayback")
    if args.skip_arquivo:
        skip_sources.add("arquivo")

    if args.no_wayback_proxy:
        config.pop("wayback_proxy", None)
        # Reduce concurrency when going direct (avoid IP rate limits)
        config.setdefault("concurrency", {})
        config["concurrency"]["wayback_fetch"] = min(config["concurrency"].get("wayback_fetch", 50), 8)
        logging.getLogger(__name__).info("Wayback proxy disabled — using direct connection with reduced concurrency")

    asyncio.run(_run_all(sites, config, args.phase, args.limit, skip_sources, args.retry, args.parallel, args.max_articles))


async def _run_all(sites: list[str], config: dict, phase: str | None, limit: int | None, skip_sources: set[str] | None = None, retry: bool = False, parallel: int = 1, max_articles: int | None = None):
    if parallel <= 1:
        for domain in sites:
            try:
                await run_site(domain, config, phase=phase, limit=limit, skip_sources=skip_sources, retry=retry, max_articles=max_articles)
            except KeyboardInterrupt:
                print("\nInterrupted by user")
                break
            except Exception as e:
                logging.getLogger(__name__).error(f"Failed to process {domain}: {e}", exc_info=True)
    else:
        from src.pipeline import run_sites_parallel
        await run_sites_parallel(sites, config, phase=phase, limit=limit, skip_sources=skip_sources, retry=retry, parallel=parallel, max_articles=max_articles)


def _get_sites(site_arg: str | None) -> list[str]:
    """Get list of domains to process."""
    if site_arg:
        return [site_arg]

    # Domains hosted on these platforms can't be meaningfully scraped
    SKIP_HOSTS = {"facebook.com", "www.facebook.com", "issuu.com", "www.issuu.com"}

    sites_csv = parse_jornais_csv()
    domains = []
    seen = set()
    for row in sites_csv:
        url = row.get("url", "")
        domain = url.replace("https://", "").replace("http://", "").rstrip("/")
        if domain.startswith("www."):
            domain = domain[4:]
        if not domain:
            continue
        # Use only the hostname, strip any URL path to avoid nested data dirs
        host = domain.split("/")[0]
        if host in SKIP_HOSTS:
            continue
        if host not in seen:
            seen.add(host)
            domains.append(host)
    return domains


def _reset_site(config: dict, domain: str):
    """Reset a site's data directory."""
    data_dir = Path(config.get("output_dir", "data")) / domain
    if not data_dir.exists():
        print(f"No data directory for {domain}")
        return

    confirm = input(f"Delete all data for {domain} in {data_dir}? [y/N] ")
    if confirm.lower() != "y":
        print("Cancelled")
        return

    shutil.rmtree(data_dir)
    print(f"Deleted {data_dir}")


def _format_ts(ts: str | None) -> str:
    """Format a CDX timestamp like '20010315120000' into '2001-03-15'."""
    if not ts or len(ts) < 8:
        return "-"
    return f"{ts[:4]}-{ts[4:6]}-{ts[6:8]}"


async def _show_oldest(sites: list[str], config: dict):
    """Query Arquivo.pt and Wayback Machine for the oldest CDX record per site."""
    import httpx
    from rich.console import Console
    from rich.table import Table

    USER_AGENT = "olho-regional/1.0 (news-archive-research; +https://github.com/msramalho/olho-regional)"
    console = Console()

    table = Table(title="Oldest CDX Record per Site")
    table.add_column("Site", style="bold", no_wrap=True)
    table.add_column("Arquivo.pt", justify="center")
    table.add_column("Arquivo URL", max_width=60)
    table.add_column("Wayback", justify="center")
    table.add_column("Wayback URL", max_width=60)

    wayback_proxy = config.get("wayback_proxy")
    wb_kwargs = {"http2": True, "headers": {"User-Agent": USER_AGENT}, "timeout": 30.0}
    if wayback_proxy:
        wb_kwargs["proxy"] = wayback_proxy

    async with (
        httpx.AsyncClient(http2=True, headers={"User-Agent": USER_AGENT}, timeout=30.0) as client,
        httpx.AsyncClient(**wb_kwargs) as wb_client,
    ):
        for domain in sites:
            data_dir = get_data_dir(config, domain)
            state = load_state(data_dir)
            cached = state.get("oldest_cdx")

            if cached:
                console.print(f"  {domain} (cached)", style="dim")
                arq = cached.get("arquivo")
                wb = cached.get("wayback")
            else:
                console.print(f"  Querying {domain}...", style="dim")
                try:
                    arq = await fetch_oldest_cdx(client, domain, "arquivo")
                except Exception as e:
                    logging.getLogger(__name__).debug(f"Arquivo CDX error for {domain}: {e}")
                    arq = None
                try:
                    wb = await fetch_oldest_cdx(wb_client, domain, "wayback")
                except Exception as e:
                    logging.getLogger(__name__).debug(f"Wayback CDX error for {domain}: {e}")
                    wb = None

                state["oldest_cdx"] = {"arquivo": arq, "wayback": wb}
                save_state(data_dir, state)

            arq_date = _format_ts(arq["timestamp"]) if arq else "-"
            arq_url = arq["url"] if arq else ""
            wb_date = _format_ts(wb["timestamp"]) if wb else "-"
            wb_url = wb["url"] if wb else ""

            table.add_row(domain, arq_date, arq_url, wb_date, wb_url)

    console.print(table)


if __name__ == "__main__":
    main()
