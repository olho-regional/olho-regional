# Data Scraping — News Article Collector

Collects all news articles from **arquivo.pt**, **Wayback Machine**, and **live site sitemaps** for Portuguese regional newspapers listed in `jornais.csv`.

## Quick Start

```bash
pip install -r requirements.txt
cp .env.example .env  # add your proxy credentials

# Single site
python collect.py --site barlavento.pt

# All sites
python collect.py

# Check status
python collect.py status
```

## Pipeline Flow (per site)

Each site goes through three sequential phases. Progress is checkpointed in `data/<domain>/state.json`, so the pipeline is fully **resumable** — if interrupted, it picks up where it left off.

### Phase A: CDX Discovery

Queries archive indexes to find all captures of the site:

1. **arquivo.pt CDX** — queries `arquivo.pt/wayback/cdx` for all HTML captures. If the handler defines `CDX_PREFIXES`, uses targeted prefix queries (faster). Otherwise does a domain-wide scan.
2. **Wayback Machine CDX** — queries `web.archive.org/cdx/search/cdx` with `collapse=digest` to deduplicate by content hash. Uses `resumeKey` pagination.
3. **Live sitemaps** — fetches `sitemap.xml` from the live site for current article URLs.

Each source's raw results are saved to `cdx_arquivo.jsonl`, `cdx_wayback.jsonl`, and `sitemap_urls.jsonl`. You can run discovery alone with `--phase cdx`.

### Phase B: Filter & Deduplicate

1. Each URL is passed through the site handler's `is_article_url()` — rejects homepages, tag pages, static files, etc.
2. URLs are normalized (lowercase host, strip `www.`, trailing slash) and deduplicated across all three sources.
3. For each unique URL, the best fetch source is selected: **live > arquivo > wayback**.
4. The final task list is saved to `tasks.jsonl` and the raw CDX files are deleted (no longer needed).

### Phase C: Fetch & Extract

1. Article pages are downloaded from their assigned source (live site, arquivo.pt archive, or Wayback Machine).
2. Each source uses its own HTTP client and rate limiter. Wayback fetches go through a **rotating residential proxy** (configured in `config.yaml`) so each connection gets a different IP.
3. The site handler's `extract()` method parses the HTML → title, text, date, author, categories, etc.
4. Articles passing quality checks (text length, title present) are saved to `articles.jsonl`. Failures go to `quality.jsonl` with a reason code.
5. Results are flushed to disk every batch (200 tasks). On Ctrl+C, in-flight results are flushed before exit.

On resume, already-processed URLs (read from `articles.jsonl`) are skipped. Previously errored pages (in `quality.jsonl`) are also skipped by default — use `--retry` to retry them.

## Output Files

All output lives in `data/<domain>/`:

| File | Description |
|------|-------------|
| `articles.jsonl` | Extracted articles — the main output |
| `quality.jsonl` | Failed extractions with reason codes (`http_404`, `timeout`, `text_too_short`, `no_title`, etc.) |
| `tasks.jsonl` | Deduplicated fetch task list (URL + source + timestamp) |
| `state.json` | Checkpoint: which phases are done, record counts, oldest CDX cache |

## Commands

```bash
python collect.py                              # Full pipeline, all sites
python collect.py --site example.com           # Single site
python collect.py --phase cdx --site example.com  # CDX discovery only
python collect.py --phase tasks --site example.com # Discovery + dedup (no fetching)
python collect.py --limit 50 --site example.com   # Fetch only 50 articles (testing)
python collect.py --max-articles 50000             # Cap at 50k articles per site
python collect.py --skip-wayback               # Skip Wayback Machine entirely
python collect.py --skip-arquivo               # Skip arquivo.pt entirely
python collect.py --retry --site example.com   # Retry previously errored pages
python collect.py --parallel 4                 # Run 4 sites concurrently (shared rate limits)
python collect.py status                       # Summary table for all sites
python collect.py status --site example.com    # Detailed stats for one site
python collect.py diagnose --site example.com  # Full diagnostic report for a site
python collect.py oldest                       # Show oldest CDX record per site
python collect.py oldest --site example.com    # ...for a single site
python collect.py --reset example.com          # Delete all data for a site
python collect.py -v --site example.com        # Verbose logging
```

## Diagnose

`python collect.py diagnose --site <domain>` prints a comprehensive report to help decide if a site needs a custom handler or manual intervention. Includes:

- **Handler** — custom vs generic, CDX_PREFIXES defined
- **Files** — sizes and record counts in the data directory
- **Pipeline phase** — NOT STARTED / DISCOVERY DONE / TASKS READY / FETCHING / COMPLETE
- **Discovery stats** — records scanned vs saved per source (arquivo, wayback, sitemap)
- **Oldest captures** — earliest archived snapshot from each source
- **URL prefix map** — bar chart of URL path segments (helps choose `CDX_PREFIXES`)
- **Tasks breakdown** — Live/Arquivo/Wayback counts and percentages
- **Articles by year** — histogram with 2 random sample titles per year
- **Field completeness** — extraction rates for title, date, author, etc. (color-coded)
- **Text length** — median/p10/p90 + short article warnings
- **Errors** — top failure reasons with full sample URLs
- **Recommendations** — actionable suggestions (e.g. "custom handler needed", "CDX_PREFIXES missing")

## Resets & Re-running

**Full reset** — deletes the entire `data/<domain>/` directory:
```bash
python collect.py --reset example.com
```

**Re-run a single phase** — edit `data/<domain>/state.json` and set the relevant flag to `false`:
- `"arquivo_cdx_done": false` → re-runs arquivo CDX discovery
- `"wayback_cdx_done": false` → re-runs Wayback CDX discovery
- `"sitemap_done": false` → re-runs sitemap discovery

Then run `python collect.py --site example.com`. Only the reset phase re-runs; everything else is skipped.

**Re-run fetching** — delete `tasks.jsonl` to force re-deduplication from raw CDX files (you'll need to also reset CDX phases so the raw files are regenerated). Or simply delete `articles.jsonl` / `quality.jsonl` to re-fetch everything.

## Custom Site Handlers

The generic handler (`BaseSiteHandler`) uses trafilatura and works for most WordPress sites. Create a custom handler when extraction quality is poor — check with `python collect.py status --site <domain>`.

Create `src/sites/<name>.py`:

```python
from .base import BaseSiteHandler

class MyHandler(BaseSiteHandler):
    DOMAINS = ["example.com", "www.example.com"]
    NAME = "example"

    # Optional: targeted CDX prefixes (faster than domain-wide scan)
    CDX_PREFIXES = [
        "https://example.com/noticias/",
        "https://example.com/opiniao/",
    ]

    def is_article_url(self, url: str) -> bool:
        # Filter CDX URLs to only article pages
        ...

    def extract(self, html: str, url: str) -> dict | None:
        # Parse HTML → {"title", "text", "date", "author", ...}
        # Return None on failure
        ...
```

The handler is auto-discovered — no registration needed. It's matched to domains via the `DOMAINS` list.

Key methods:
- **`is_article_url(url)`** — called during CDX discovery to filter out non-article pages (homepages, tag pages, images, etc.). Critical for efficiency: a loose filter wastes fetch bandwidth; a tight filter misses articles.
- **`extract(html, url)`** — called during fetch phase. Returns a dict with `title`, `text`, `date`, `author`, `subtitle`, `categories`, `section`, or `None` on failure.
- **`CDX_PREFIXES`** — optional list of URL prefixes for targeted arquivo.pt CDX queries. Much faster than scanning all domain records when you know the article URL patterns.

## Configuration

Edit `config.yaml`:

| Setting | Description |
|---------|-------------|
| `date_range` | CDX query date range (default: 1996–2026) |
| `concurrency.arquivo` | Concurrent arquivo.pt connections (CDX + fetch) |
| `concurrency.arquivo_cdx_max_per_minute` | arquivo CDX rate cap (limit: 250, ban if exceeded) |
| `concurrency.arquivo_fetch_max_per_minute` | arquivo page download rate cap (limit: 4000, ban if exceeded) |
| `concurrency.wayback_cdx` | Concurrent Wayback CDX connections |
| `concurrency.wayback_fetch` | Concurrent Wayback page downloads (through proxy) |
| `timeout_seconds` | HTTP request timeout |
| `min_text_length` | Minimum extracted text length to accept an article |

## Logo Fetching

`fetch_logos.py` downloads logos/favicons for all sites in `jornais.csv`, saving them to `data/<domain>/logo.<ext>`.

```bash
python fetch_logos.py                 # All sites
python fetch_logos.py --site beira.pt # Single site
python fetch_logos.py --dry-run       # Preview only
```

**Strategy** (per site, in order):
1. Parse homepage HTML for `<link rel="apple-touch-icon">`, `<link rel="icon">`, `<meta property="og:image">`
2. Try `/favicon.ico` directly
3. Fall back to Google Favicon API (`t1.gstatic.com/faviconV2`)

The best icon is selected by size (apple-touch-icon preferred at 180px, then sized icons, then generic favicons).

**State management:**
- On success, sets `logo_file` in `state.json` (e.g. `"logo.png"`)
- On re-run, skips sites that already have `logo_file` pointing to an existing file
- **Wrong logo flow**: The QC dashboard can mark a logo as wrong — this deletes the file and sets `logo_wrong: true` in state.json. On next run, `fetch_logos.py` skips sites with `logo_wrong` set. However, if a user manually places a `logo.<ext>` file in the data directory, `fetch_logos.py` auto-detects it, clears the `logo_wrong` flag, and updates `logo_file`.

## Quality Control Dashboard

```bash
python quality-control/qc_server.py   # Opens at http://localhost:8066
```

Features:
- **Sites table** — overview of all sites with phase, article counts, success rates, logos
- **Site detail** — per-site analysis with field completeness, year distribution, text length stats, failure reasons, sample articles
- **Cross-site search** — search articles across all sites by URL, title, or text snippet
- **Quality analysis** — per-site duplicate text detection, empty/short text alerts, repeated title detection (lazy-loaded)
- **Wrong logo** — mark incorrect logos for re-fetching via the UI