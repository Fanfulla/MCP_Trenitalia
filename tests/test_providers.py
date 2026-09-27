import copy
from datetime import date
import json
from pathlib import Path
import unittest
from unittest.mock import patch

import httpx
import http_client as http
import italo
import viaggiatreno as vt

FIXTURES = Path(__file__).parent / "fixtures"


class ProviderTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        await http.close_clients()

    async def asyncTearDown(self):
        await http.close_clients()

    def transport(self, handler):
        client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        factory = patch.object(http, "_make_client", return_value=client)
        factory.start()
        self.addCleanup(factory.stop)

    async def test_station_search_quotes_path_and_rejects_bad_objects(self):
        requests = []

        def handle(request):
            requests.append(request)
            return httpx.Response(200, json=[{"nomeLungo": "ROMA TERMINI", "id": "S08409"}])

        self.transport(handle)
        self.assertEqual(await vt.cerca_stazione(" Roma/? "), [{"nome": "Roma Termini", "id": "S08409"}])
        self.assertTrue(requests[0].url.raw_path.endswith(b"/Roma%2F%3F"))
        await http.close_clients()
        self.transport(lambda request: httpx.Response(200, json=["not a station"]))
        with self.assertRaises(http.UpstreamError):
            await vt.cerca_stazione("Roma")

    async def test_station_text_format_and_empty_result(self):
        self.transport(lambda request: httpx.Response(200, text="ROMA TERMINI|S08409\n"))
        self.assertEqual(await vt.cerca_stazione("Roma"), [{"nome": "Roma Termini", "id": "S08409"}])
        await http.close_clients()
        self.transport(lambda request: httpx.Response(200, json=[]))
        self.assertEqual(await vt.cerca_stazione("unknown"), [])

    async def test_board_rejects_object_and_preserves_encoded_time(self):
        requests = []

        def handle(request):
            requests.append(request)
            return httpx.Response(200, json={"error": "maintenance"})

        self.transport(handle)
        with self.assertRaises(http.UpstreamError):
            await vt.get_partenze("S08409", "Sun%20Sep%2027%202026%2012%3A00%3A00%20GMT%2B0200")
        self.assertIn(b"12%3A00%3A00", requests[0].url.raw_path)
        self.assertNotIn(b"%253A", requests[0].url.raw_path)

    async def test_train_status_uses_rome_midnight_across_dst(self):
        paths = []

        def handle(request):
            paths.append(request.url.path)
            day = "2026-09-27" if request.url.path.endswith("1790460000000") else "2026-01-01"
            return httpx.Response(200, json={"numeroTreno": 9413, "dataPartenza": day + " 00:00:00.0", "ritardo": 0})

        self.transport(handle)
        await vt.get_andamento_treno("S02593", "9413", date(2026, 9, 27))
        await vt.get_andamento_treno("S02593", "9413", date(2026, 1, 1))
        self.assertTrue(paths[0].endswith("/S02593/9413/1790460000000"))
        self.assertTrue(paths[1].endswith("/S02593/9413/1767222000000"))

    async def test_lookup_follows_official_number_lookup_and_service_date(self):
        paths = []

        def handle(request):
            paths.append(request.url.path)
            if "/cercaNumeroTrenoTrenoAutocomplete/" in request.url.path:
                return httpx.Response(200, text="9413 - VENEZIA S.LUCIA - 27/09/26|9413-S02593-1790460000000\n")
            return httpx.Response(200, json={"numeroTreno": 9413, "dataPartenza": "2026-09-27 00:00:00.0", "origine": "VENEZIA S.LUCIA", "ritardo": -5})

        self.transport(handle)
        result = await vt.lookup_train("9413", date(2026, 9, 27))
        self.assertEqual(result["ritardo"], -5)
        self.assertEqual(len(paths), 2)
        self.assertTrue(paths[1].endswith("/S02593/9413/1790460000000"))

    async def test_lookup_is_exact_and_reports_ambiguity(self):
        self.transport(lambda request: httpx.Response(200, text=(
            "9413 - A|9413-S02593-1790460000000\n"
            "9413 - B|9413-S08409-1790460000000\n"
            "19413 - C|19413-S00001-1790460000000\n"
        )))
        with self.assertRaises(http.UpstreamError) as error:
            await vt.lookup_train("9413", date(2026, 9, 27))
        self.assertEqual(error.exception.code, "ambiguous")
        self.assertEqual(len(error.exception.candidates), 2)

    async def test_lookup_no_service_on_requested_day_is_not_upstream_failure(self):
        self.transport(lambda request: httpx.Response(204))
        self.assertEqual(await vt.lookup_train("9413", date(2026, 9, 28)), {})

    async def test_dated_status_rejects_wrong_or_unknown_response_date(self):
        for reported in ("2026-09-26 00:00:00.0", None):
            await http.close_clients()
            self.transport(lambda request: httpx.Response(200, json={
                "numeroTreno": 9413, "dataPartenza": reported, "ritardo": 0,
            }))
            with self.assertRaises(http.UpstreamError):
                await vt.get_andamento_treno("S02593", "9413", date(2026, 9, 27))

    async def test_italo_normalizes_real_payload_without_inventing_service_date(self):
        payload = json.loads((FIXTURES / "italo_train.json").read_text(encoding="utf-8-sig"))
        payload["TrainSchedule"]["Distruption"]["Warning"] = False
        self.transport(lambda request: httpx.Response(200, json=payload))
        result = await italo.get_train_status("8908")
        self.assertEqual(result["provider"], "italo")
        self.assertEqual(result["train_number"], "8908")
        self.assertEqual(result["origin"], {"id": "NAC", "name": "Napoli"})
        self.assertEqual(result["delay_minutes"], 11)
        self.assertIsNone(result["service_date"])
        self.assertEqual(result["freshness"], "date_unverified")
        self.assertEqual(result["status"], "delayed")
        self.assertEqual(len(result["stops"]), 9)
        self.assertIsNone(result["stops"][0]["scheduled_arrival"])
        self.assertIsNone(result["stops"][-1]["scheduled_departure"])
        self.assertIsNone(result["stops"][-1]["actual_arrival"])
        self.assertEqual(result["stops"][-1]["expected_arrival"], "14:06")
        self.assertNotIn("1901", json.dumps(result))

    async def test_italo_missing_delay_remains_unknown_and_warning_marks_stale(self):
        original = json.loads((FIXTURES / "italo_train.json").read_text(encoding="utf-8-sig"))
        payload = copy.deepcopy(original)
        payload["TrainSchedule"]["Distruption"] = {}
        self.transport(lambda request: httpx.Response(200, json=payload))
        result = await italo.get_train_status("8908")
        self.assertIsNone(result["delay_minutes"])
        self.assertEqual(result["status"], "unknown")
        await http.close_clients()
        original["TrainSchedule"]["Distruption"]["Warning"] = True
        self.transport(lambda request: httpx.Response(200, json=original))
        result = await italo.get_train_status("8908")
        self.assertEqual(result["status"], "stale")
        self.assertIsNone(result["delay_minutes"])

    async def test_italo_empty_and_malformed_payloads_are_distinct(self):
        self.transport(lambda request: httpx.Response(200, json={"IsEmpty": True, "LastUpdate": None, "TrainSchedule": None}))
        self.assertEqual((await italo.get_train_status("99999"))["status"], "not_found")
        await http.close_clients()
        self.transport(lambda request: httpx.Response(200, json={"IsEmpty": False, "TrainSchedule": None}))
        with self.assertRaises(http.UpstreamError):
            await italo.get_train_status("99999")

    async def test_italo_board_resolves_official_station_catalogue(self):
        payload = json.loads((FIXTURES / "italo_station.json").read_text(encoding="utf-8-sig"))
        paths = []

        def handle(request):
            paths.append(str(request.url))
            if request.url.path == "/":
                return httpx.Response(200, text='<span data-ntv-name="station-to-url" data-ntv-type="Json">[{"code":"BC_","urlCoding":"bologna"}]</span>')
            return httpx.Response(200, json=payload)

        self.transport(handle)
        result = await italo.get_station_board("Bologna", "departures")
        self.assertEqual(result["station"]["id"], "BC_")
        self.assertEqual(result["trains"][0]["train_number"], "8908")
        self.assertEqual(result["trains"][0]["delay_minutes"], 10)
        self.assertIsNone(result["service_date"])
        self.assertIn("CodiceStazione=BC_", paths[1])


if __name__ == "__main__":
    unittest.main()
