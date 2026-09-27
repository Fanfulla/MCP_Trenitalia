import unittest
from unittest.mock import Mock

from mcp.server import MCPServer
from starlette.testclient import TestClient

from http_app import create_http_app


class PublicEndpointTests(unittest.TestCase):
    def make_app(self, **kwargs):
        server = MCPServer('test')
        @server.tool()
        def example() -> dict:
            return {'answer': 42}
        return create_http_app(server, Mock(sources=lambda: {}), **kwargs)

    def test_rejects_unapproved_host(self):
        with TestClient(self.make_app(), base_url='http://localhost') as client:
            response = client.get('/health', headers={'Host': 'attacker.example'})
        self.assertEqual(response.status_code, 400)

    def test_limits_requests_without_trusting_forwarded_ip(self):
        with TestClient(self.make_app(requests_per_minute=2), base_url='http://localhost') as client:
            # Health requests are excluded; arbitrary forwarded addresses cannot bypass quotas.
            first = client.post('/mcp', json={}, headers={'X-Forwarded-For': '192.0.2.1'})
            second = client.post('/mcp', json={}, headers={'X-Forwarded-For': '192.0.2.2'})
            third = client.post('/mcp', json={}, headers={'X-Forwarded-For': '192.0.2.3'})
            self.assertNotEqual(first.status_code, 429)
            self.assertNotEqual(second.status_code, 429)
            self.assertEqual(third.status_code, 429)
            self.assertEqual(client.get('/health').status_code, 200)

    def test_optional_access_token_is_required_for_mcp(self):
        with TestClient(self.make_app(api_key='local-test-secret'), base_url='http://localhost') as client:
            self.assertEqual(client.post('/mcp', json={}).status_code, 401)
            response = client.post('/mcp', json={}, headers={'Authorization': 'Bearer local-test-secret'})
            self.assertNotEqual(response.status_code, 401)

    def test_failed_authentication_counts_towards_rate_limit(self):
        with TestClient(self.make_app(api_key='local-test-secret', requests_per_minute=2), base_url='http://localhost') as client:
            self.assertEqual(client.post('/mcp', json={}).status_code, 401)
            self.assertEqual(client.post('/mcp', json={}, headers={'Authorization': 'Bearer wrong'}).status_code, 401)
            response = client.post('/mcp', json={}, headers={'Authorization': 'Bearer local-test-secret'})
            self.assertEqual(response.status_code, 429)
            self.assertEqual(response.headers['Retry-After'], '60')

    def test_current_protocol_lists_tools_over_http(self):
        with TestClient(self.make_app(), base_url='http://localhost') as client:
            response = client.post('/mcp', headers={'Accept': 'application/json, text/event-stream'},
                json={'jsonrpc': '2.0', 'id': 1, 'method': 'tools/list', 'params': {
                    '_meta': {'io.modelcontextprotocol/protocolVersion': '2026-07-28',
                              'io.modelcontextprotocol/clientCapabilities': {}}}})
            self.assertEqual(response.status_code, 200, response.text)
            self.assertEqual(response.json()['result']['tools'][0]['name'], 'example')



if __name__ == '__main__':
    unittest.main()
