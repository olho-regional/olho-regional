import asyncio
import csv
import hashlib
import os
import time
from pathlib import Path
from urllib.parse import urlparse, urlunparse

import yaml


_BASE_DIR = Path(__file__).resolve().parent.parent


def _load_dotenv():
    """Load .env file from project root into os.environ."""
    env_path = _BASE_DIR / ".env"
    if not env_path.exists():
        return
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            key, _, value = line.partition("=")
            if key and _ == "=":
                os.environ.setdefault(key.strip(), value.strip())


def load_config(path: str = "config.yaml") -> dict:
    _load_dotenv()
    with open(_BASE_DIR / path) as f:
        config = yaml.safe_load(f)
    # Inject secrets from environment
    if os.environ.get("WAYBACK_PROXY"):
        config["wayback_proxy"] = os.environ["WAYBACK_PROXY"]
    return config


def parse_jornais_csv(path: str = "jornais.csv") -> list[dict]:
    with open(_BASE_DIR / path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def normalize_url(url: str) -> str:
    """Normalize URL for dedup: lowercase host, strip www., strip trailing slash, strip fragment,
    strip WordPress internal query params."""
    p = urlparse(url)
    host = p.hostname or ""
    if host.startswith("www."):
        host = host[4:]
    path = p.path.rstrip("/") or "/"
    # Strip junk query params (WP cron, cache busters, tracking)
    query = p.query
    if query:
        from urllib.parse import parse_qs, urlencode
        params = parse_qs(query, keep_blank_values=True)
        for junk in ("doing_wp_cron", "utm_source", "utm_medium", "utm_campaign",
                      "utm_term", "utm_content", "fbclid", "gclid", "replytocom"):
            params.pop(junk, None)
        query = urlencode(params, doseq=True)
    return urlunparse(("https", host, path, "", query, ""))


def content_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def url_id(url: str) -> str:
    return hashlib.sha256(normalize_url(url).encode("utf-8")).hexdigest()


class RateLimiter:
    """Rate limiter with concurrency cap and per-minute rate enforcement."""

    def __init__(self, max_concurrent: int, max_per_minute: int = 0, delay_ms: int = 0):
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.delay = delay_ms / 1000.0
        # Per-minute rate limiting via minimum interval between request starts
        if max_per_minute > 0:
            self._min_interval = 60.0 / max_per_minute
        else:
            self._min_interval = 0
        self._last_request_time = 0.0
        self._rate_lock = asyncio.Lock()

    async def acquire(self):
        await self.semaphore.acquire()
        if self.delay > 0:
            await asyncio.sleep(self.delay)
        if self._min_interval > 0:
            async with self._rate_lock:
                now = time.monotonic()
                wait = self._min_interval - (now - self._last_request_time)
                if wait > 0:
                    await asyncio.sleep(wait)
                self._last_request_time = time.monotonic()

    def release(self):
        self.semaphore.release()

    async def __aenter__(self):
        await self.acquire()
        return self

    async def __aexit__(self, *args):
        self.release()


def retry_async(max_attempts: int = 5, backoff_base: float = 2.0, retryable_statuses: set | None = None):
    """Decorator for async functions with exponential backoff retry."""
    if retryable_statuses is None:
        retryable_statuses = {429, 500, 502, 503, 504}

    def decorator(func):
        async def wrapper(*args, **kwargs):
            last_exc = None
            for attempt in range(max_attempts):
                try:
                    result = await func(*args, **kwargs)
                    # If result is an httpx.Response, check status
                    if hasattr(result, "status_code") and result.status_code in retryable_statuses:
                        if attempt < max_attempts - 1:
                            wait = backoff_base ** attempt
                            await asyncio.sleep(wait)
                            continue
                    return result
                except Exception as e:
                    last_exc = e
                    if attempt < max_attempts - 1:
                        wait = backoff_base ** attempt
                        await asyncio.sleep(wait)
            raise last_exc
        return wrapper
    return decorator


def domain_from_url(url: str) -> str:
    host = urlparse(url).hostname or ""
    if host.startswith("www."):
        host = host[4:]
    return host


def get_data_dir(config: dict, domain: str) -> Path:
    base = _BASE_DIR / config.get("output_dir", "data")
    d = base / domain
    d.mkdir(parents=True, exist_ok=True)
    return d
