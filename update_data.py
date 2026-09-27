#!/usr/bin/env python3
"""Explicit free CCISS NeTEx refresh. Validated caches replace prior files atomically."""

import argparse
import gzip
import io
import json
import time
import urllib.request
from pathlib import Path
from urllib.parse import urlsplit

from build_timetable import parse_netex, write_timetable

DATA = Path(__file__).resolve().parent / "data"
MAX_DOWNLOAD_BYTES = 64 * 1024 * 1024
DOWNLOAD_SECONDS = 120


def _official_url(url):
    parsed = urlsplit(url)
    if parsed.scheme != "https" or parsed.hostname != "www.cciss.it" or parsed.port not in {None, 443} or parsed.username or parsed.password:
        raise ValueError("Only the official HTTPS CCISS source is allowed")
    return url


class OfficialRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, msg, headers, newurl):
        _official_url(newurl)
        return super().redirect_request(request, fp, code, msg, headers, newurl)


def download(url: str) -> bytes:
    _official_url(url)
    started, chunks, size = time.monotonic(), [], 0
    opener = urllib.request.build_opener(OfficialRedirect)
    request = urllib.request.Request(url)
    with opener.open(request, timeout=30) as response:
        _official_url(response.url)
        content_length = response.headers.get("Content-Length")
        if content_length and int(content_length) > MAX_DOWNLOAD_BYTES:
            raise ValueError("Download exceeds compressed size limit")
        while True:
            block = response.read1(65536)
            size += len(block)
            if size > MAX_DOWNLOAD_BYTES or time.monotonic() - started > DOWNLOAD_SECONDS:
                raise ValueError("Download exceeds size or time limit")
            if not block:
                break
            chunks.append(block)
    return b"".join(chunks)


def refresh_provider(provider: str, output: Path | None = None) -> dict:
    sources = json.loads((DATA / "sources.json").read_text(encoding="utf-8"))
    source = sources[provider]
    content = download(source["url"])
    compressed = io.BytesIO(content)
    stream = gzip.GzipFile(fileobj=compressed) if content[:2] == b"\x1f\x8b" else compressed
    with stream:
        payload = parse_netex(stream, provider=provider, source_url=source["url"])
    payload["metadata"].update({key: source[key] for key in ("catalog_url", "license", "license_note")})
    write_timetable(payload, output or DATA / source["filename"])
    return payload


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--provider", choices=("all", "trenitalia", "italo"), default="all")
    args = parser.parse_args()
    failed = False
    for provider in ("trenitalia", "italo") if args.provider == "all" else (args.provider,):
        try:
            payload = refresh_provider(provider)
            metadata = payload["metadata"]
            print(f"{provider}: {len(payload['journeys'])} journeys, {metadata['valid_from']}..{metadata['valid_to']}")
        except (OSError, ValueError, KeyError) as exc:
            failed = True
            print(f"{provider}: refresh failed; previous cache retained: {exc}")
    raise SystemExit(1 if failed else 0)


if __name__ == "__main__":
    main()
