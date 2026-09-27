"""Small self-hosted HTTP boundary; no external gateway or paid service."""

from collections import OrderedDict, deque
from contextlib import asynccontextmanager
from hmac import compare_digest
import os
import time

from mcp.server.transport_security import TransportSecuritySettings
from starlette.middleware.trustedhost import TrustedHostMiddleware
from starlette.responses import JSONResponse
from http_client import close_clients


class RequestLimits:
    def __init__(self, app, *, limit: int, api_key: str):
        self.app = app
        self.limit = limit
        self.api_key = api_key
        self.windows = OrderedDict()

    async def __call__(self, scope, receive, send):
        if scope['type'] != 'http' or scope['path'] == '/health':
            return await self.app(scope, receive, send)
        peer = scope.get('client')
        address = peer[0] if peer else 'unknown'
        current = time.monotonic()
        # Evict only expired buckets. If saturated, reject new addresses rather than
        # evict active clients and allow repeated bursts by rotating addresses.
        while self.windows:
            _, bucket = next(iter(self.windows.items()))
            if bucket and bucket[-1] > current - 60:
                break
            self.windows.popitem(last=False)
        if address not in self.windows and len(self.windows) >= 4096:
            return await JSONResponse({'error': 'busy'}, status_code=503)(scope, receive, send)
        bucket = self.windows.setdefault(address, deque())
        self.windows.move_to_end(address)
        while bucket and bucket[0] <= current - 60:
            bucket.popleft()
        if len(bucket) >= self.limit:
            return await JSONResponse({'error': 'rate_limited'}, status_code=429,
                headers={'Retry-After': '60'})(scope, receive, send)
        bucket.append(current)
        headers = dict(scope.get('headers', []))
        if self.api_key and not compare_digest(headers.get(b'authorization', b''),
                                               f'Bearer {self.api_key}'.encode()):
            return await JSONResponse({'error': 'unauthorized'}, status_code=401)(scope, receive, send)
        return await self.app(scope, receive, send)


def create_http_app(server, rail, *, legacy_sse=False,
                    requests_per_minute=None, api_key=None, allowed_hosts=None):
    limit = requests_per_minute if requests_per_minute is not None else int(os.getenv('MCP_RATE_LIMIT', '60'))
    if limit < 1 or limit > 10000:
        raise ValueError('MCP_RATE_LIMIT must be between 1 and 10000')
    key = api_key if api_key is not None else os.getenv('MCP_API_KEY', '')
    hosts = allowed_hosts or [part.strip() for part in os.getenv(
        'MCP_ALLOWED_HOSTS', 'localhost,127.0.0.1,[::1]').split(',') if part.strip()]
    if not hosts or '*' in hosts:
        raise ValueError('Set explicit MCP_ALLOWED_HOSTS hostnames')
    # Both transport-level origin/host validation and the public HTTP host guard
    # use the configured hostnames. A local default never accepts arbitrary DNS.
    security = TransportSecuritySettings(enable_dns_rebinding_protection=True,
        allowed_hosts=[f'{host}:*' for host in hosts] + hosts,
        allowed_origins=[f'{scheme}://{host}:*' for host in hosts for scheme in ('http', 'https')]
                        + [f'{scheme}://{host}' for host in hosts for scheme in ('http', 'https')])
    if legacy_sse:
        app = server.sse_app(transport_security=security, max_request_body_size=1048576)
    else:
        app = server.streamable_http_app(stateless_http=True, json_response=True,
            transport_security=security, max_request_body_size=1048576)

    transport_lifespan = app.router.lifespan_context

    @asynccontextmanager
    async def application_lifespan(application):
        try:
            async with transport_lifespan(application) as state:
                yield state
        finally:
            # Shared pools belong to this process, never to an individual SSE client.
            await close_clients()

    app.router.lifespan_context = application_lifespan

    async def health(_request):
        statuses = {provider: value.get('status') for provider, value in rail.sources().items()}
        return JSONResponse({'status': 'ok', 'service': 'ciuff',
                             'schedules': statuses, 'upstream_health_checked': False})

    app.add_route('/health', health, methods=['GET'])
    app.add_middleware(RequestLimits, limit=limit, api_key=key)
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=hosts)
    return app
