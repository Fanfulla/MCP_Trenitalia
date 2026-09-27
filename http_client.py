"""Bounded, reusable HTTP transport for the free rail data providers."""

from __future__ import annotations

import asyncio
from collections import OrderedDict
from datetime import datetime, timezone
import time
from typing import Any

import httpx

MAX_CONCURRENCY = 8
MAX_CACHE_ENTRIES = 128
MAX_RESPONSE_BYTES = 2_000_000
_client: httpx.AsyncClient | None = None
_semaphore: asyncio.Semaphore | None = None
_cache: OrderedDict[str, tuple[float, httpx.Response]] = OrderedDict()


class UpstreamError(Exception):
    """Safe provider failure; response bodies never enter the public error."""

    def __init__(self, code: str, source_url: str, *, candidates: list | None = None):
        self.code = code
        self.source_url = source_url
        self.candidates = candidates or []
        super().__init__(f"Rail data source: {code}")


def _make_client() -> httpx.AsyncClient:
    return httpx.AsyncClient(
        timeout=httpx.Timeout(10.0),
        limits=httpx.Limits(max_connections=MAX_CONCURRENCY, max_keepalive_connections=MAX_CONCURRENCY),
        headers={"User-Agent": "Ciuff/2.0 (public rail information)", "Accept": "application/json, text/plain, */*"},
        follow_redirects=True,
    )


async def close_clients() -> None:
    """Call from the server lifespan after requests have finished."""
    global _client, _semaphore
    if _client is not None:
        await _client.aclose()
    _client = None
    _semaphore = None
    _cache.clear()


def _copy_response(response: httpx.Response) -> httpx.Response:
    return httpx.Response(
        response.status_code, content=response.content, headers=response.headers,
        request=response.request, extensions=dict(response.extensions),
    )


async def get_response(url: str, *, ttl: float = 15) -> httpx.Response:
    """GET only; at most three attempts and a short, count-bounded cache."""
    global _client, _semaphore
    cached = _cache.get(url)
    if cached and cached[0] > time.monotonic():
        _cache.move_to_end(url)
        return _copy_response(cached[1])
    _cache.pop(url, None)
    if _client is None:
        _client = _make_client()
        _semaphore = asyncio.Semaphore(MAX_CONCURRENCY)
    assert _semaphore is not None
    async with _semaphore:
        for attempt in range(3):
            retry_after = 0.2 * (2 ** attempt)
            try:
                async with _client.stream("GET", url) as response:
                    chunks = bytearray()
                    async for chunk in response.aiter_bytes():
                        chunks.extend(chunk)
                        if len(chunks) > MAX_RESPONSE_BYTES:
                            raise UpstreamError("response_too_large", url)
                    headers = dict(response.headers)
                    # aiter_bytes has already decompressed the wire payload.
                    headers.pop("content-encoding", None)
                    headers.pop("content-length", None)
                    response = httpx.Response(
                        response.status_code, content=bytes(chunks), headers=headers,
                        request=response.request,
                        extensions={"observed_at": datetime.now(timezone.utc).isoformat()},
                    )
                if response.status_code not in {429, 500, 502, 503, 504}:
                    if response.is_error:
                        raise UpstreamError("unavailable", url)
                    if ttl > 0:
                        _cache[url] = (time.monotonic() + min(ttl, 300), response)
                        while len(_cache) > MAX_CACHE_ENTRIES:
                            _cache.popitem(last=False)
                    return _copy_response(response)
                try:
                    retry_after = min(max(float(response.headers.get("Retry-After", retry_after)), 0), 2)
                except ValueError:
                    pass
            except httpx.DecodingError:
                raise UpstreamError("malformed_payload", url) from None
            except httpx.TransportError:
                pass
            if attempt < 2:
                await asyncio.sleep(retry_after)
    raise UpstreamError("unavailable", url)


def decode_json(response: httpx.Response) -> Any:
    if response.status_code == 204:
        return None
    try:
        return response.json()
    except (ValueError, UnicodeError):
        url = str(response.request.url)
        _cache.pop(url, None)
        raise UpstreamError("malformed_payload", url) from None


async def get_json(url: str, *, ttl: float = 15) -> Any:
    # JSON is decoded on every read, so callers cannot mutate cached values.
    return decode_json(await get_response(url, ttl=ttl))


async def get_text(url: str, *, ttl: float = 15) -> str:
    return (await get_response(url, ttl=ttl)).text
