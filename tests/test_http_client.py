import asyncio
import gzip
import unittest
from unittest.mock import patch

import httpx
import http_client as http


class HttpClientTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        await http.close_clients()

    async def asyncTearDown(self):
        await http.close_clients()

    def transport(self, handler):
        client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        factory = patch.object(http, "_make_client", return_value=client)
        factory.start()
        self.addCleanup(factory.stop)
        return client

    async def test_retries_transient_get_and_does_not_cache_failure(self):
        calls = []

        def handle(request):
            calls.append(request)
            return httpx.Response(503 if len(calls) < 3 else 200, json={"ok": True})

        self.transport(handle)
        self.assertEqual(await http.get_json("https://example.test/train"), {"ok": True})
        self.assertEqual(len(calls), 3)

    async def test_retry_limit_and_error_do_not_leak_html(self):
        calls = []

        def handle(request):
            calls.append(request)
            return httpx.Response(503, text="<html>private upstream failure</html>")

        self.transport(handle)
        with self.assertRaises(http.UpstreamError) as error:
            await http.get_json("https://example.test/train")
        self.assertEqual(len(calls), 3)
        self.assertEqual(error.exception.code, "unavailable")
        self.assertNotIn("private upstream", str(error.exception))

    async def test_cache_reuses_client_and_cannot_be_mutated_by_caller(self):
        calls = []

        def handle(request):
            calls.append(request)
            return httpx.Response(200, json={"stops": [{"name": "Roma"}]})

        client = self.transport(handle)
        first = await http.get_json("https://example.test/train")
        first["stops"][0]["name"] = "changed"
        self.assertEqual((await http.get_json("https://example.test/train"))["stops"][0]["name"], "Roma")
        self.assertEqual(len(calls), 1)
        self.assertFalse(client.is_closed)
        await http.close_clients()
        self.assertTrue(client.is_closed)

    async def test_cache_expiry_and_capacity_are_bounded(self):
        calls = []

        def handle(request):
            calls.append(str(request.url))
            return httpx.Response(200, json={"call": len(calls)})

        self.transport(handle)
        with patch.object(http, "MAX_CACHE_ENTRIES", 2), patch.object(http.time, "monotonic", return_value=100):
            await http.get_json("https://example.test/a", ttl=1)
            await http.get_json("https://example.test/b", ttl=1)
            await http.get_json("https://example.test/c", ttl=1)
            await http.get_json("https://example.test/a", ttl=1)
        self.assertEqual(len(calls), 4)
        with patch.object(http.time, "monotonic", return_value=102):
            await http.get_json("https://example.test/a", ttl=1)
        self.assertEqual(len(calls), 5)

    async def test_malformed_json_and_empty_http_are_different(self):
        self.transport(lambda request: httpx.Response(200, text="<html>maintenance</html>"))
        with self.assertRaises(http.UpstreamError) as error:
            await http.get_json("https://example.test/bad")
        self.assertEqual(error.exception.code, "malformed_payload")
        self.assertNotIn("maintenance", str(error.exception))
        await http.close_clients()
        self.transport(lambda request: httpx.Response(204))
        self.assertIsNone(await http.get_json("https://example.test/empty"))

    async def test_outbound_concurrency_is_bounded(self):
        active = peak = 0

        async def handle(request):
            nonlocal active, peak
            active += 1
            peak = max(peak, active)
            await asyncio.sleep(0.01)
            active -= 1
            return httpx.Response(200, json={"ok": True})

        self.transport(handle)
        with patch.object(http, "MAX_CONCURRENCY", 2):
            await asyncio.gather(*(http.get_json(f"https://example.test/{i}") for i in range(7)))
        self.assertLessEqual(peak, 2)

    async def test_compressed_responses_are_decoded_once_including_cache(self):
        self.transport(lambda request: httpx.Response(
            200, content=gzip.compress(b'{"train": 8908}'),
            headers={"Content-Encoding": "gzip"},
        ))
        self.assertEqual(await http.get_json("https://example.test/compressed"), {"train": 8908})
        self.assertEqual(await http.get_json("https://example.test/compressed"), {"train": 8908})


if __name__ == "__main__":
    unittest.main()
