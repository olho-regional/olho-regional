#!/usr/bin/env python3
"""Fetch logos/favicons for all newspapers in jornais.csv.

Strategy per site:
  1. Check state.json — skip if logo_file already set and file exists
  2. Fetch homepage HTML, look for:
     a) <link rel="icon"> or <link rel="shortcut icon"> (high-res preferred)
     b) <link rel="apple-touch-icon"> (usually 180×180)
     c) <meta property="og:image"> (Open Graph logo)
     d) <link rel="icon" type="image/svg+xml"> (SVG logo)
  3. Fallback: try /favicon.ico directly
  4. Fallback: Google favicon API (t1.gstatic.com/faviconV2)
  5. Save to data/<domain>/logo.<ext>, update state.json

Usage:
  python3 fetch_logos.py                 # All sites
  python3 fetch_logos.py --site beira.pt # Single site
  python3 fetch_logos.py --dry-run       # Preview only
"""

import argparse
import json
import sys
import time
from pathlib import Path
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"

# Prefer larger icons; order matters
_LINK_SELECTORS = [
    ('link[rel="apple-touch-icon"]', "href"),
    ('link[rel="apple-touch-icon-precomposed"]', "href"),
    ('link[rel="icon"][sizes]', "href"),       # sized icons (pick largest)
    ('link[rel="icon"][type="image/svg+xml"]', "href"),
    ('link[rel="icon"]', "href"),
    ('link[rel="shortcut icon"]', "href"),
    ('meta[property="og:image"]', "content"),
]

TIMEOUT = httpx.Timeout(15.0, connect=10.0)
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/*,*/*;q=0.8",
}

# Map content-type to extension
_CT_EXT = {
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/jpg": ".jpg",
    "image/gif": ".gif",
    "image/svg+xml": ".svg",
    "image/x-icon": ".ico",
    "image/vnd.microsoft.icon": ".ico",
    "image/webp": ".webp",
    "image/avif": ".avif",
}


def _ext_from_url(url: str) -> str:
    """Guess extension from URL path."""
    path = urlparse(url).path.lower()
    for ext in (".png", ".jpg", ".jpeg", ".gif", ".svg", ".ico", ".webp", ".avif"):
        if path.endswith(ext):
            return ".jpg" if ext == ".jpeg" else ext
    return ""


def _ext_from_content_type(ct: str) -> str:
    """Get extension from Content-Type header."""
    ct = (ct or "").split(";")[0].strip().lower()
    return _CT_EXT.get(ct, "")


def _pick_best_icon_url(soup: BeautifulSoup, base_url: str) -> str | None:
    """Extract the best logo/icon URL from HTML."""
    candidates = []

    for selector, attr in _LINK_SELECTORS:
        for el in soup.select(selector):
            val = el.get(attr, "").strip()
            if not val:
                continue
            abs_url = urljoin(base_url, val)

            # Score by size hint and selector priority
            size = 0
            sizes_attr = el.get("sizes", "")
            if sizes_attr and "x" in sizes_attr.lower():
                try:
                    size = int(sizes_attr.lower().split("x")[0])
                except ValueError:
                    pass

            # Prefer apple-touch-icon (usually 180px), then sized icons, then others
            is_apple = "apple" in selector
            is_og = "og:image" in selector
            priority = 0
            if is_apple:
                priority = 300
            elif size > 0:
                priority = size
            elif is_og:
                priority = 50  # OG images can be huge banners, lower priority
            else:
                priority = 16  # generic favicon, low priority

            candidates.append((priority, abs_url))

    if not candidates:
        return None

    # Return highest-priority (largest) icon
    candidates.sort(key=lambda c: -c[0])
    return candidates[0][1]


def _download_image(client: httpx.Client, url: str) -> tuple[bytes, str] | None:
    """Download an image, return (bytes, extension) or None."""
    try:
        resp = client.get(url, follow_redirects=True, timeout=TIMEOUT)
        if resp.status_code != 200:
            return None
        ct = resp.headers.get("content-type", "")
        # Reject HTML responses (error pages)
        if "text/html" in ct.lower():
            return None
        data = resp.content
        if len(data) < 10:  # too small to be a real image
            return None
        ext = _ext_from_content_type(ct) or _ext_from_url(url) or ".ico"
        return data, ext
    except (httpx.HTTPError, Exception):
        return None


def _find_manual_logo(data_dir: Path) -> str | None:
    """Check if a logo file was manually placed in the data dir."""
    for ext in (".png", ".jpg", ".jpeg", ".ico", ".svg", ".webp", ".gif", ".avif"):
        candidate = data_dir / f"logo{ext}"
        if candidate.exists() and candidate.stat().st_size > 10:
            return f"logo{ext}"
    return None


def fetch_logo(client: httpx.Client, domain: str, site_url: str, data_dir: Path, dry_run: bool) -> dict:
    """Fetch logo for a single site. Returns result dict."""
    state_path = data_dir / "state.json"
    state = {}
    if state_path.exists():
        state = json.loads(state_path.read_text())

    # Skip if already done
    existing = state.get("logo_file")
    if existing and (data_dir / existing).exists():
        return {"domain": domain, "status": "skipped", "file": existing}

    # Handle "wrong logo" flag
    if state.get("logo_wrong"):
        # Check if a logo file was manually placed (auto-recovery)
        manual = _find_manual_logo(data_dir)
        if manual:
            state["logo_file"] = manual
            state.pop("logo_wrong", None)
            state_path.write_text(json.dumps(state, ensure_ascii=False, indent=2))
            return {"domain": domain, "status": "recovered", "file": manual}
        # Otherwise skip — user marked it as wrong
        return {"domain": domain, "status": "skipped-wrong"}

    if dry_run:
        return {"domain": domain, "status": "dry-run"}

    # Ensure data dir exists
    data_dir.mkdir(parents=True, exist_ok=True)

    # Strategy 1: Parse homepage for icon links
    icon_url = None
    try:
        resp = client.get(site_url, follow_redirects=True, timeout=TIMEOUT, headers=HEADERS)
        if resp.status_code == 200 and "text/html" in resp.headers.get("content-type", ""):
            soup = BeautifulSoup(resp.text, "lxml")
            icon_url = _pick_best_icon_url(soup, str(resp.url))
    except (httpx.HTTPError, Exception):
        pass

    # Try downloading the discovered icon
    if icon_url:
        result = _download_image(client, icon_url)
        if result:
            data, ext = result
            fname = f"logo{ext}"
            if not dry_run:
                (data_dir / fname).write_bytes(data)
                state["logo_file"] = fname
                state_path.write_text(json.dumps(state, ensure_ascii=False, indent=2))
            return {"domain": domain, "status": "ok", "file": fname, "source": icon_url, "size": len(data)}

    # Strategy 2: Try /favicon.ico directly
    favicon_url = urljoin(site_url, "/favicon.ico")
    result = _download_image(client, favicon_url)
    if result:
        data, ext = result
        fname = f"logo{ext}"
        if not dry_run:
            (data_dir / fname).write_bytes(data)
            state["logo_file"] = fname
            state_path.write_text(json.dumps(state, ensure_ascii=False, indent=2))
        return {"domain": domain, "status": "ok", "file": fname, "source": favicon_url, "size": len(data)}

    # Strategy 3: Google Favicon API
    google_url = f"https://t1.gstatic.com/faviconV2?client=SOCIAL&type=FAVICON&fallback_opts=TYPE,SIZE,URL&url={site_url}&size=128"
    result = _download_image(client, google_url)
    if result:
        data, ext = result
        fname = f"logo{ext}"
        if not dry_run:
            (data_dir / fname).write_bytes(data)
            state["logo_file"] = fname
            state_path.write_text(json.dumps(state, ensure_ascii=False, indent=2))
        return {"domain": domain, "status": "ok", "file": fname, "source": "google-favicon-api", "size": len(data)}

    return {"domain": domain, "status": "failed", "reason": "no logo found from any source"}


def main():
    parser = argparse.ArgumentParser(description="Fetch logos for newspaper sites")
    parser.add_argument("--site", help="Process single domain")
    parser.add_argument("--dry-run", action="store_true", help="Preview without downloading")
    args = parser.parse_args()

    # Load sites from jornais.csv
    import csv
    sites = []
    with open(BASE_DIR / "jornais.csv", newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            url = row.get("url", "").strip().rstrip("/")
            if not url:
                continue
            parsed = urlparse(url)
            domain = parsed.hostname or ""
            if domain.startswith("www."):
                domain = domain[4:]
            if not domain:
                continue
            # Normalize URL to have scheme
            if not url.startswith("http"):
                url = "https://" + url
            sites.append({"domain": domain, "url": url, "nome": row.get("nome", "")})

    if args.site:
        sites = [s for s in sites if s["domain"] == args.site]
        if not sites:
            print(f"Site not found: {args.site}", file=sys.stderr)
            sys.exit(1)

    print(f"Processing {len(sites)} sites" + (" (dry run)" if args.dry_run else ""))
    print("-" * 70)

    stats = {"ok": 0, "skipped": 0, "failed": 0}
    failures = []

    with httpx.Client(http2=True, verify=False) as client:
        for i, site in enumerate(sites, 1):
            domain = site["domain"]
            data_dir = DATA_DIR / domain

            result = fetch_logo(client, domain, site["url"], data_dir, args.dry_run)
            status = result["status"]

            if status == "ok":
                stats["ok"] += 1
                print(f"  [{i:3d}/{len(sites)}] ✓ {domain:40s} {result['file']:15s} ({result['size']:,} bytes) from {result.get('source','')[:60]}")
            elif status == "skipped":
                stats["skipped"] += 1
                print(f"  [{i:3d}/{len(sites)}] – {domain:40s} already has {result['file']}")
            elif status == "skipped-wrong":
                stats["skipped"] += 1
                print(f"  [{i:3d}/{len(sites)}] ✕ {domain:40s} marked as wrong logo, skipping")
            elif status == "recovered":
                stats["ok"] += 1
                print(f"  [{i:3d}/{len(sites)}] ↺ {domain:40s} recovered manual logo: {result['file']}")
            elif status == "dry-run":
                print(f"  [{i:3d}/{len(sites)}] ? {domain:40s}")
            else:
                stats["failed"] += 1
                failures.append(result)
                print(f"  [{i:3d}/{len(sites)}] ✗ {domain:40s} {result.get('reason', 'unknown')}")

            # Small delay to be polite
            if status not in ("skipped", "dry-run"):
                time.sleep(0.3)

    print("-" * 70)
    print(f"Done: {stats['ok']} downloaded, {stats['skipped']} skipped, {stats['failed']} failed")

    if failures:
        print(f"\nFailed sites ({len(failures)}):")
        for f in failures:
            print(f"  {f['domain']}: {f.get('reason', 'unknown')}")


if __name__ == "__main__":
    main()
