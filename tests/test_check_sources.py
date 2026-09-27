import os
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import AsyncMock, patch

import check_sources
from http_client import UpstreamError
from rail_service import RailService


def payload(provider, valid_to):
    return {"schema_version": 2, "provider": provider, "stations": [], "journeys": [],
            "metadata": {"valid_from": "2026-09-01", "valid_to": valid_to,
                         "source_url": "https://www.cciss.it/example", "publication_timestamp": "2026-09-26T09:00:00Z"}}


def service(trenitalia="2026-12-12", italo="2027-02-02"):
    datasets = {"trenitalia": payload("trenitalia", trenitalia)}
    if italo:
        datasets["italo"] = payload("italo", italo)
    return RailService(Path("data"), datasets=datasets)


class TimetableValidityTests(unittest.TestCase):
    def test_valid_timetables_produce_no_messages(self):
        self.assertEqual(check_sources.controlla_orari(service(), date(2026, 9, 27), 21), ([], []))

    def test_close_expiry_is_only_a_warning(self):
        errori, avvisi = check_sources.controlla_orari(service(), date(2026, 11, 30), 21)
        self.assertEqual(errori, [])
        self.assertEqual(avvisi, ["Orario trenitalia: valido fino al 2026-12-12 (restano 12 giorni)"])

    def test_expired_or_missing_timetables_are_errors(self):
        errori, _ = check_sources.controlla_orari(service(italo=None), date(2026, 12, 13), 21)
        self.assertEqual(errori, ["Orario trenitalia: expired per il 2026-12-13", "Orario italo: missing per il 2026-12-13"])


class LiveCheckTests(unittest.IsolatedAsyncioTestCase):
    async def test_viaggiatreno_check_follows_a_departing_train(self):
        with patch("check_sources.cerca_stazione", AsyncMock(return_value=[{"nome": "Roma Termini", "id": "S08409"}])), \
             patch("check_sources.get_partenze", AsyncMock(return_value=[
                 {"numeroTreno": 1, "codOrigine": "S00001"}, {"numeroTreno": 592, "codOrigine": "S08409"}])), \
             patch("check_sources.get_andamento_treno", AsyncMock(return_value={"fermate": [{}, {}]})) as andamento:
            messaggio = await check_sources.controlla_viaggiatreno()
        self.assertIn("treno 592 con 2 fermate", messaggio)
        andamento.assert_awaited_once_with("S08409", "592")

    async def test_viaggiatreno_format_change_is_detected(self):
        with patch("check_sources.cerca_stazione", AsyncMock(return_value=[{"nome": "Altro", "id": "S00001"}])):
            with self.assertRaisesRegex(RuntimeError, "Roma Termini"):
                await check_sources.controlla_viaggiatreno()

    async def test_italo_check_requires_board_and_train_stops(self):
        board = {"status": "ok", "trains": [{"train_number": "9981"}]}
        with patch("check_sources.get_station_board", AsyncMock(return_value=board)), \
             patch("check_sources.get_train_status", AsyncMock(return_value={"stops": [{}, {}, {}]})):
            self.assertIn("treno 9981 con 3 fermate", await check_sources.controlla_italo())
        with patch("check_sources.get_station_board", AsyncMock(return_value={"status": "no_results", "trains": []})):
            with self.assertRaisesRegex(RuntimeError, "no_results"):
                await check_sources.controlla_italo()

    async def test_upstream_failures_are_reported_per_source(self):
        with patch("check_sources.controlla_viaggiatreno", AsyncMock(side_effect=UpstreamError("unavailable", "x"))), \
             patch("check_sources.controlla_italo", AsyncMock(return_value="Italo: ok")):
            risultati = await check_sources.controlli_live()
        self.assertEqual(risultati[0][:2], ("Viaggiatreno", False))
        self.assertIn("unavailable", risultati[0][2])
        self.assertEqual(risultati[1], ("Italo", True, "Italo: ok"))


class MainTests(unittest.TestCase):
    def run_main(self, live, rail, *args):
        with tempfile.TemporaryDirectory() as tmp:
            summary = Path(tmp) / "summary.md"
            env = {"GITHUB_ACTIONS": "true", "GITHUB_STEP_SUMMARY": str(summary)}
            with patch.dict(os.environ, env), patch("check_sources.RailService", return_value=rail), \
                 patch("check_sources.controlli_live", AsyncMock(side_effect=live)) as controlli, \
                 patch("check_sources.time.sleep") as sleep, patch("builtins.print") as stampa:
                code = check_sources.main(list(args))
            output = "\n".join(str(call.args[0]) for call in stampa.call_args_list)
            return code, output, summary.read_text(encoding="utf-8"), controlli.await_count, sleep

    def test_healthy_sources_exit_zero_and_write_summary(self):
        code, output, summary, calls, sleep = self.run_main([[("Viaggiatreno", True, "V ok"), ("Italo", True, "I ok")]], service())
        self.assertEqual(code, 0)
        self.assertIn("OK V ok", summary)
        self.assertEqual(calls, 1)
        sleep.assert_not_called()

    def test_transient_live_failure_is_retried_once(self):
        fail, ok = [("Viaggiatreno", False, "V giù")], [("Viaggiatreno", True, "V ok")]
        code, _, _, calls, sleep = self.run_main([fail, ok], service(), "--retry-delay", "5")
        self.assertEqual((code, calls), (0, 2))
        sleep.assert_called_once_with(5.0)

    def test_persistent_failure_exits_one_with_error_annotation(self):
        fail = [("Italo", False, "Italo: RuntimeError: formato cambiato")]
        code, output, summary, calls, _ = self.run_main([fail, fail], service(), "--retry-delay", "1")
        self.assertEqual((code, calls), (1, 2))
        self.assertIn("::error::Italo: RuntimeError: formato cambiato", output)
        self.assertIn("ERRORE Italo", summary)

    def test_expiring_timetable_warns_without_failing(self):
        with patch("check_sources.now_rome") as now:
            now.return_value.date.return_value = date(2026, 11, 30)
            code, output, _, _, _ = self.run_main([[("Viaggiatreno", True, "V ok")]], service())
        self.assertEqual(code, 0)
        self.assertIn("::warning::Orario trenitalia", output)


if __name__ == "__main__":
    unittest.main()
