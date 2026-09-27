import asyncio
import unittest
from unittest.mock import Mock, patch

import httpx
import http_client
from http_app import create_http_app


class SharedPoolLifetimeTests(unittest.IsolatedAsyncioTestCase):
    async def test_sse_disconnect_does_not_close_another_users_provider_request(self):
        from server import mcp
        await http_client.close_clients()
        ready, disconnected, started, release = [asyncio.Event() for _ in range(4)]
        app = create_http_app(mcp, Mock(sources=lambda: {}), legacy_sse=True)

        async def receive():
            await disconnected.wait()
            return {'type': 'http.disconnect'}

        async def send(message):
            if message['type'] == 'http.response.body' and b'event: endpoint' in message.get('body', b''):
                ready.set()

        async def upstream(request):
            started.set()
            await release.wait()
            return httpx.Response(503)

        scope = dict(type='http', asgi={'version': '3.0'}, http_version='1.1',
            method='GET', scheme='http', path='/sse', raw_path=b'/sse', query_string=b'',
            headers=[(b'host', b'localhost')], client=('127.0.0.1', 1234),
            server=('127.0.0.1', 8000), root_path='')
        client = httpx.AsyncClient(transport=httpx.MockTransport(upstream))
        try:
            async with app.router.lifespan_context(app):
                sse = asyncio.create_task(app(scope, receive, send))
                await asyncio.wait_for(ready.wait(), 5)
                with patch.object(http_client, '_make_client', return_value=client):
                    request = asyncio.create_task(http_client.get_json('https://provider.test/train'))
                    await asyncio.wait_for(started.wait(), 5)
                    disconnected.set()
                    await asyncio.wait_for(sse, 5)
                    closed_on_disconnect = client.is_closed
                    release.set()
                    outcome = (await asyncio.gather(request, return_exceptions=True))[0]
                self.assertFalse(closed_on_disconnect)
                self.assertIsInstance(outcome, http_client.UpstreamError)
            self.assertTrue(client.is_closed)
        finally:
            release.set()
            disconnected.set()
            await http_client.close_clients()
            await client.aclose()
