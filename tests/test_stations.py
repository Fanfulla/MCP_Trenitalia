import json
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

import build_stazioni
import server
from http_client import UpstreamError
from models import MonitoraPartenzeInput, TracciaTrenoInput
from rail_service import RailService
from timetable import search_stations, station_key


DIZIONARIO = {"BOLOGNA C.LE": "S05043", "BOLOGNA C.LE AV": "S05046", "BOLOGNA MAZZINI": "S05140",
              "FIRENZE S.MARIA NOVELLA": "S06421", "FIRENZE RIFREDI": "S06420", "ROMA TERMINI": "S08409"}


class StationKeyTests(unittest.TestCase):
    def test_natural_names_match_official_abbreviations(self):
        for naturale, ufficiale in (
            ("Bologna Centrale", "BOLOGNA C.LE"),
            ("Firenze Santa Maria Novella", "FIRENZE S.MARIA NOVELLA"),
            ("Firenze Santa Maria Novella", "Firenze S.M.Novella (Florence)"),
            ("Firenze SMN", "FIRENZE S.MARIA NOVELLA"),
            ("firenze s.m.n.", "FIRENZE S.MARIA NOVELLA"),
            ("Venezia Santa Lucia", "Venezia S.Lucia (Venice)"),
            ("Reggio Calabria Centrale", "REGGIO DI CALABRIA CENTRALE"),
            ("San Maurizio Canavese", "S. Maurizio Canavese"),
        ):
            with self.subTest(naturale=naturale, ufficiale=ufficiale):
                self.assertEqual(station_key(naturale), station_key(ufficiale))

    def test_distinct_stations_keep_distinct_keys(self):
        self.assertNotEqual(station_key("Bologna Centrale"), station_key("Bologna C.Le/Av"))
        self.assertNotEqual(station_key("Roma Termini"), station_key("Roma Tiburtina"))
        self.assertNotEqual(station_key("Santa Marinella"), station_key("Santa Maria Novella"))


class TimetableSearchTests(unittest.TestCase):
    PAYLOAD = {"stations": [
        {"id": "bo", "name": "BOLOGNA C.LE"}, {"id": "bm", "name": "Bologna Mazzini"},
        {"id": "fi", "name": "FIRENZE S.MARIA NOVELLA"}, {"id": "fr", "name": "FIRENZE RIFREDI"},
        {"id": "ve", "name": "VENEZIA S.LUCIA"}, {"id": "rm", "name": "ROMA TERMINI"},
        {"id": "rt", "name": "ROMA TIBURTINA"}]}

    def ids(self, query):
        return [station["id"] for station in search_stations(self.PAYLOAD, query)]

    def test_natural_names_resolve_to_single_station(self):
        self.assertEqual(self.ids("Bologna Centrale"), ["bo"])
        self.assertEqual(self.ids("Firenze Santa Maria Novella"), ["fi"])
        self.assertEqual(self.ids("Firenze SMN"), ["fi"])
        self.assertEqual(self.ids("Venezia Santa Lucia"), ["ve"])

    def test_partial_and_ambiguous_queries_are_unchanged(self):
        self.assertEqual(self.ids("Roma"), ["rm", "rt"])
        self.assertEqual(self.ids("Bologna"), ["bo", "bm"])
        self.assertEqual(self.ids("ROMA TERMINI"), ["rm"])
        self.assertEqual(self.ids("Firenze Santa"), ["fi"])
        self.assertEqual(self.ids("Pisa"), [])

    def test_italo_style_names_with_english_suffix(self):
        payload = {"stations": [{"id": "IT:FI", "name": "Firenze S.M.Novella (Florence)"},
                                {"id": "IT:VE", "name": "Venezia S.Lucia (Venice)"}]}
        self.assertEqual([s["id"] for s in search_stations(payload, "Firenze Santa Maria Novella")], ["IT:FI"])
        self.assertEqual([s["id"] for s in search_stations(payload, "Venice")], ["IT:VE"])


class RailServiceNaturalNameTests(unittest.IsolatedAsyncioTestCase):
    async def test_journey_search_accepts_natural_station_names(self):
        data = {"schema_version": 2, "provider": "trenitalia", "journeys": [],
                "stations": [{"id": "fi", "name": "FIRENZE S.MARIA NOVELLA"}, {"id": "bo", "name": "BOLOGNA C.LE"}],
                "metadata": {"valid_from": "2026-09-01", "valid_to": "2026-12-12",
                             "source_url": "https://www.cciss.it/example", "publication_timestamp": "2026-09-26T09:00:00Z"}}
        service = RailService(Path("data"), datasets={"trenitalia": data})
        with patch("rail_service.journeys_between", return_value=[]) as query:
            result = await service.search_journeys("Firenze Santa Maria Novella", "Bologna Centrale",
                                                   "2026-09-28", "08:00", "trenitalia", 5)
        self.assertEqual(result["choices"], [])
        self.assertEqual(query.call_args.args[1:3], ("fi", "bo"))


class LegacyResolutionTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        patcher = patch.dict(server._STAZIONI, DIZIONARIO, clear=True)
        patcher.start()
        self.addCleanup(patcher.stop)

    async def test_natural_name_prefers_main_station_over_av_platforms(self):
        with patch("server.cerca_stazione", new_callable=AsyncMock) as api:
            self.assertEqual(await server._resolve_stazione("Bologna Centrale"), ("S05043", "Bologna C.Le"))
            self.assertEqual(await server._resolve_stazione("Firenze Santa Maria Novella"),
                             ("S06421", "Firenze S.Maria Novella"))
        api.assert_not_awaited()

    async def test_generic_name_still_asks_for_disambiguation(self):
        risposta = await server._resolve_stazione("Bologna")
        self.assertIsInstance(risposta, str)
        self.assertIn("S05043", risposta)
        self.assertIn("S05046", risposta)

    async def test_station_ids_pass_through(self):
        self.assertEqual(await server._resolve_stazione("s08409"), ("S08409", "Roma Termini"))

    async def test_unknown_local_name_falls_back_to_viaggiatreno(self):
        api = AsyncMock(return_value=[{"nome": "Pisa Centrale", "id": "S06501"}])
        with patch("server.cerca_stazione", api):
            self.assertEqual(await server._resolve_stazione("Pisa Centrale"), ("S06501", "Pisa Centrale"))
        api.assert_awaited_once_with("Pisa Centrale")

    async def test_fallback_prefers_normalized_exact_name(self):
        api = AsyncMock(return_value=[{"nome": "Venezia S.Lucia", "id": "S02593"},
                                      {"nome": "Venezia Mestre", "id": "S02589"}])
        with patch("server.cerca_stazione", api):
            self.assertEqual(await server._resolve_stazione("Venezia Santa Lucia"), ("S02593", "Venezia S.Lucia"))

    async def test_fallback_failure_returns_message_instead_of_raising(self):
        api = AsyncMock(side_effect=UpstreamError("unavailable", "http://www.viaggiatreno.it/"))
        with patch("server.cerca_stazione", api):
            risposta = await server._resolve_stazione("Stazione Inesistente")
        self.assertIsInstance(risposta, str)
        self.assertIn("non trovata", risposta)


class ErrorMessageTests(unittest.IsolatedAsyncioTestCase):
    def test_upstream_errors_are_explained_in_italian(self):
        for code, frammento in (("unavailable", "non rispondono"), ("date_mismatch", "non riporta questo treno"),
                                ("malformed_payload", "formato inatteso"), ("nuovo_codice", "(nuovo_codice)")):
            with self.subTest(code=code):
                messaggio = server._handle_error(UpstreamError(code, "http://www.viaggiatreno.it/"), "test")
                self.assertTrue(messaggio.startswith("[test] Errore: "))
                self.assertIn(frammento, messaggio)
                self.assertNotIn("imprevisto", messaggio)

    async def test_tools_return_readable_message_when_source_fails(self):
        guasto = AsyncMock(side_effect=UpstreamError("unavailable", "http://www.viaggiatreno.it/"))
        with patch.dict(server._STAZIONI, DIZIONARIO, clear=True), patch("server.get_partenze", guasto):
            risposta = await server.trenitalia_monitora_partenze(MonitoraPartenzeInput(id_stazione="Roma Termini"))
        self.assertIn("Errore: i sistemi Viaggiatreno non rispondono", risposta)

    async def test_train_not_running_today_is_explained(self):
        guasto = AsyncMock(side_effect=UpstreamError("date_mismatch", "http://www.viaggiatreno.it/"))
        with patch.dict(server._STAZIONI, DIZIONARIO, clear=True), patch("server.get_andamento_treno", guasto):
            risposta = await server.trenitalia_traccia_treno(
                TracciaTrenoInput(numero_treno="9631", id_stazione_origine="S08409"))
        self.assertIn("non riporta questo treno in circolazione oggi", risposta)


class LegacyFormattingTests(unittest.IsolatedAsyncioTestCase):
    def test_av_platform_label_without_number_is_not_a_platform_change(self):
        self.assertEqual(server._format_binario("19 AV", " AV"), "bin. 19 AV")
        self.assertEqual(server._format_binario("19 AV", "18 AV"), "bin. 18 AV (programmato: 19 AV)")
        self.assertEqual(server._format_binario("3", "4"), "bin. 4 (programmato: 3)")
        self.assertEqual(server._format_binario("I", "II"), "bin. II (programmato: I)")
        self.assertEqual(server._format_binario(None, None), "non assegnato")

    async def test_placeholder_last_station_is_reported_as_unavailable(self):
        dati = {"numeroTreno": 9631, "categoria": "FR", "origine": "MILANO CENTRALE", "destinazione": "ROMA TERMINI",
                "ritardo": 0, "stazioneUltimoRilevamento": "--", "fermate": []}
        with patch.dict(server._STAZIONI, DIZIONARIO, clear=True), \
             patch("server.get_andamento_treno", AsyncMock(return_value=dati)):
            risposta = await server.trenitalia_traccia_treno(
                TracciaTrenoInput(numero_treno="9631", id_stazione_origine="S01700"))
        self.assertIn("**Ultima stazione rilevata**: dato non disponibile", risposta)


class BuildStazioniTests(unittest.IsolatedAsyncioTestCase):
    RISPOSTE = {
        "BOLOGNA C.LE": [{"nome": "Bologna C.Le/Av", "id": "S05046"}],
        "BOLOGNA": [{"nome": "Bologna Centrale", "id": "S05043"}, {"nome": "Bologna C.Le/Av", "id": "S05046"}],
        "TORINO PORTA SUSA": [{"nome": "Torino Porta Susa", "id": "S00035"}],
        "TORINO PORTA": [{"nome": "Torino Porta Nuova", "id": "S00219"}, {"nome": "Torino Porta Susa", "id": "S00035"}],
        "TORINO": [{"nome": "Torino Porta Nuova", "id": "S00219"}, {"nome": "Torino Porta Susa", "id": "S00035"}],
        "FIRENZE S.MARIA NOVELLA": [],
        "FIRENZE S.MARIA": [],
        "FIRENZE": [{"nome": "Firenze Santa Maria Novella", "id": "S06421"}, {"nome": "Firenze Rifredi", "id": "S06420"}],
        "VILLA CLAUDIA": [{"nome": "Anzio Colonia", "id": "S08713"}],
        "VILLA": [{"nome": "Anzio Colonia", "id": "S08713"}],
    }

    def setUp(self):
        self.api = AsyncMock(side_effect=lambda query: self.RISPOSTE.get(query, []))
        patcher = patch("build_stazioni._cerca", self.api)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_netex_code_extraction(self):
        self.assertEqual(build_stazioni.netex_code("IT::StopPlace:railTRENITALIA:830005043"), "S05043")
        self.assertEqual(build_stazioni.netex_code("IT::StopPlace:otherTRENITALIA:830006421"), "S06421")
        self.assertIsNone(build_stazioni.netex_code("IT::StopPlace:railTRENITALIA:790044700"))

    async def test_netex_code_confirmed_by_viaggiatreno_wins(self):
        self.assertEqual(await build_stazioni.risolvi("BOLOGNA C.LE", "S05043"), ("S05043", True))
        self.assertEqual(await build_stazioni.risolvi("FIRENZE S.MARIA NOVELLA", "S06421"), ("S06421", True))

    async def test_unconfirmed_code_keeps_name_match(self):
        self.assertEqual(await build_stazioni.risolvi("TORINO PORTA SUSA", "S00222"), ("S00035", False))

    async def test_incompatible_names_are_never_accepted(self):
        self.assertEqual(await build_stazioni.risolvi("VILLA CLAUDIA", "S08713"), (None, False))

    async def test_update_corrects_only_verified_entries_and_keeps_the_rest(self):
        stazioni = [
            {"id": "IT::StopPlace:railTRENITALIA:830005043", "name": "BOLOGNA C.LE"},
            {"id": "IT::StopPlace:otherTRENITALIA:830000222", "name": "TORINO PORTA SUSA"},
            {"id": "IT::StopPlace:otherTRENITALIA:830006421", "name": "FIRENZE S.MARIA NOVELLA"},
            {"id": "IT::StopPlace:otherTRENITALIA:830008409", "name": "ROMA TERMINI"},
            {"id": "IT::StopPlace:otherTRENITALIA:830008713", "name": "VILLA CLAUDIA"},
        ]
        esistenti = {"BOLOGNA C.LE": "S05046", "TORINO PORTA SUSA": "S00035", "ROMA TERMINI": "S08409", "BERN": "S11460"}
        mapping, report = await build_stazioni.aggiorna(stazioni, esistenti)
        self.assertEqual(mapping["BOLOGNA C.LE"], "S05043")
        self.assertEqual(mapping["BOLOGNA C.LE AV"], "S05046")
        self.assertEqual(mapping["TORINO PORTA SUSA"], "S00035")
        self.assertEqual(mapping["FIRENZE S.MARIA NOVELLA"], "S06421")
        self.assertEqual(mapping["BERN"], "S11460")
        self.assertNotIn("VILLA CLAUDIA", mapping)
        self.assertIn(("BOLOGNA C.LE", "S05046", "S05043"), report["corrette"])
        self.assertEqual(report["non_trovate"], ["VILLA CLAUDIA"])
        self.assertNotIn("ROMA TERMINI", [call.args[0] for call in self.api.await_args_list])


class StationDictionaryDataTests(unittest.TestCase):
    def test_main_stations_have_verified_viaggiatreno_ids(self):
        stazioni = json.loads((Path(__file__).parent.parent / "data" / "stazioni.json").read_text(encoding="utf-8"))
        for nome, station_id in {
            "BOLOGNA C.LE": "S05043", "BOLOGNA C.LE AV": "S05046", "FIRENZE S.MARIA NOVELLA": "S06421",
            "ROMA TERMINI": "S08409", "MILANO CENTRALE": "S01700", "NAPOLI CENTRALE": "S09218",
            "TORINO PORTA NUOVA": "S00219", "TORINO PORTA SUSA": "S00035", "VENEZIA S.LUCIA": "S02593",
        }.items():
            with self.subTest(nome=nome):
                self.assertEqual(stazioni.get(nome), station_id)


if __name__ == "__main__":
    unittest.main()
