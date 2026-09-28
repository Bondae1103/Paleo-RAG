"""
Resilient HTTP client for biological database APIs with rate limiting, retries,
caching (disk/Redis), and NCBI etiquette headers.
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import time
from pathlib import Path
from typing import Any, Optional
from urllib.parse import urlparse

import httpx

from backend.config import Settings, get_settings
from backend.utils.error_types import (
    DatabaseAuthError,
    DatabaseClientError,
    DatabaseNotFoundError,
    DatabaseRateLimitError,
)

logger = logging.getLogger(__name__)


class DiskCache:
    """Persistent on-disk cache for biological API responses."""

    def __init__(self, cache_dir: str | Path = "./data/bio_cache") -> None:
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _get_path(self, key: str) -> Path:
        hashed = hashlib.sha256(key.encode("utf-8")).hexdigest()
        return self.cache_dir / f"{hashed}.json"

    def get(self, key: str) -> Optional[str]:
        p = self._get_path(key)
        if not p.exists():
            return None
        try:
            payload = json.loads(p.read_text(encoding="utf-8"))
            if payload.get("expires_at", 0) > time.time():
                return payload.get("data")
            p.unlink(missing_ok=True)
        except Exception as exc:
            logger.debug(f"Cache read error for {key}: {exc}")
        return None

    def set(self, key: str, value: str, ttl_seconds: int = 604800) -> None:
        p = self._get_path(key)
        try:
            payload = {
                "key": key,
                "expires_at": time.time() + ttl_seconds,
                "data": value,
            }
            p.write_text(json.dumps(payload), encoding="utf-8")
        except Exception as exc:
            logger.debug(f"Cache write error for {key}: {exc}")


class RateLimiter:
    """Per-host token rate limiter to respect NCBI and other DB policies."""

    def __init__(self) -> None:
        self._last_request_time: dict[str, float] = {}
        # Min interval in seconds between requests to the same host
        self._host_delays: dict[str, float] = {
            "eutils.ncbi.nlm.nih.gov": 0.35,  # ~2.8 req/sec without key
            "rest.uniprot.org": 0.1,
            "data.rcsb.org": 0.1,
            "string-db.org": 0.2,
            "rest.ensembl.org": 0.1,
            "rest.kegg.jp": 0.35,
        }

    def set_delay(self, host: str, delay_seconds: float) -> None:
        self._host_delays[host] = delay_seconds

    def wait(self, url: str) -> None:
        host = urlparse(url).netloc.lower()
        delay = self._host_delays.get(host, 0.05)
        last_time = self._last_request_time.get(host, 0.0)
        elapsed = time.time() - last_time
        if elapsed < delay:
            time.sleep(delay - elapsed)
        self._last_request_time[host] = time.time()


class BioHttpClient:
    """
    Centralized HTTP Client for external biological database integrations.
    Handles NCBI API credentials, per-host throttling, exponential backoff,
    and automatic caching.
    """

    def __init__(
        self,
        settings: Optional[Settings] = None,
        cache: Optional[Any] = None,
        timeout: float = 15.0,
    ) -> None:
        self.settings = settings or get_settings()
        self.timeout = timeout
        self.cache = cache or DiskCache(cache_dir=self.settings.bio_cache_dir)
        self.rate_limiter = RateLimiter()

        # Adjust NCBI rate limit if API key is provided
        if self.settings.ncbi_api_key:
            self.rate_limiter.set_delay("eutils.ncbi.nlm.nih.gov", 0.11)  # ~9 req/sec

        self._client = httpx.Client(
            timeout=self.timeout,
            headers={
                "User-Agent": (
                    f"PaleoRAG/1.0 (Phylogenetic Context Engine; "
                    f"mailto:{self.settings.ncbi_email})"
                ),
                "Accept": "application/json, text/plain, */*",
            },
            follow_redirects=True,
        )

    def _build_cache_key(self, method: str, url: str, params: Optional[dict[str, Any]] = None) -> str:
        param_str = json.dumps(params or {}, sort_keys=True)
        return f"{method.upper()}:{url}:{param_str}"

    def request(
        self,
        method: str,
        url: str,
        params: Optional[dict[str, Any]] = None,
        headers: Optional[dict[str, str]] = None,
        use_cache: bool = True,
        cache_ttl: Optional[int] = None,
        max_retries: int = 3,
    ) -> httpx.Response:
        params = dict(params or {})
        ttl = cache_ttl if cache_ttl is not None else self.settings.bio_cache_ttl_seconds

        # NCBI etiquette auto-injection
        if "ncbi.nlm.nih.gov" in url:
            if "email" not in params and self.settings.ncbi_email:
                params["email"] = self.settings.ncbi_email
            if "tool" not in params:
                params["tool"] = "PaleoRAG"
            if "api_key" not in params and self.settings.ncbi_api_key:
                params["api_key"] = self.settings.ncbi_api_key

        cache_key = self._build_cache_key(method, url, params)

        if use_cache and method.upper() == "GET":
            cached_data = self.cache.get(cache_key)
            if cached_data is not None:
                # Return a synthesized response from cache
                return httpx.Response(
                    status_code=200,
                    content=cached_data.encode("utf-8"),
                    request=httpx.Request(method, url),
                )

        backoff = 0.5
        response: Optional[httpx.Response] = None

        for attempt in range(max_retries + 1):
            self.rate_limiter.wait(url)
            try:
                response = self._client.request(
                    method=method,
                    url=url,
                    params=params,
                    headers=headers,
                )

                if response.status_code == 429:
                    if attempt < max_retries:
                        time.sleep(backoff)
                        backoff *= 2
                        continue
                    raise DatabaseRateLimitError(
                        message=f"Rate limit exceeded for {url}",
                        database=urlparse(url).netloc,
                        status_code=429,
                    )

                if response.status_code == 404:
                    raise DatabaseNotFoundError(
                        message=f"Resource not found at {url}",
                        database=urlparse(url).netloc,
                        status_code=404,
                    )

                if response.status_code in (401, 403):
                    raise DatabaseAuthError(
                        message=f"Authentication failed for {url}: {response.text}",
                        database=urlparse(url).netloc,
                        status_code=response.status_code,
                    )

                if response.status_code >= 500:
                    if attempt < max_retries:
                        time.sleep(backoff)
                        backoff *= 2
                        continue
                    raise DatabaseClientError(
                        message=f"Server error {response.status_code} from {url}",
                        database=urlparse(url).netloc,
                        status_code=response.status_code,
                    )

                # Successful response
                if use_cache and method.upper() == "GET" and response.status_code == 200:
                    self.cache.set(cache_key, response.text, ttl_seconds=ttl)

                return response

            except (httpx.ConnectError, httpx.ReadTimeout, httpx.ConnectTimeout) as exc:
                if attempt < max_retries:
                    time.sleep(backoff)
                    backoff *= 2
                    continue
                raise DatabaseClientError(
                    message=f"Network error querying {url}: {exc}",
                    database=urlparse(url).netloc,
                    details={"error": str(exc)},
                )

        if response is not None:
            return response
        raise DatabaseClientError(message=f"Failed to query {url}", database=urlparse(url).netloc)

    def get_json(
        self,
        url: str,
        params: Optional[dict[str, Any]] = None,
        headers: Optional[dict[str, str]] = None,
        use_cache: bool = True,
        cache_ttl: Optional[int] = None,
    ) -> Any:
        resp = self.request("GET", url, params=params, headers=headers, use_cache=use_cache, cache_ttl=cache_ttl)
        return resp.json()

    def get_text(
        self,
        url: str,
        params: Optional[dict[str, Any]] = None,
        headers: Optional[dict[str, str]] = None,
        use_cache: bool = True,
        cache_ttl: Optional[int] = None,
    ) -> str:
        resp = self.request("GET", url, params=params, headers=headers, use_cache=use_cache, cache_ttl=cache_ttl)
        return resp.text

    def close(self) -> None:
        self._client.close()


_global_bio_http_client: Optional[BioHttpClient] = None


def get_bio_http_client() -> BioHttpClient:
    global _global_bio_http_client
    if _global_bio_http_client is None:
        _global_bio_http_client = BioHttpClient()
    return _global_bio_http_client
