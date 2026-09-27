import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, patch
from zoneinfo import ZoneInfo

from rail_service import RailService


TODAY = datetime(2026, 9, 27, 10, 0, tzinfo=ZoneInfo('Europe/Rome'))
STATIONS = [{'id': 'roma', 'name': 'ROMA TERMINI'},
            {'id': 'milano', 'name': 'MILANO CENTRALE'}]


def payload(provider):
    return {'schema_version': 2, 'provider': provider, 'stations': STATIONS,
            'journeys': [], 'metadata': {'valid_from': '2026-09-01',
                'valid_to': '2026-12-12', 'source_url': 'https://www.cciss.it/example',
                'publication_timestamp': '2026-09-26T09:00:00Z'}}


def journey(day='2026-09-28'):
    return {'service_id': 'run1', 'service_date': day, 'train_number': '1234',
            'line': 'AV', 'origin': STATIONS[0], 'destination': STATIONS[1],
            'departure': day + 'T12:00:00+02:00', 'arrival': day + 'T15:00:00+02:00',
            'intermediate_stops': []}


class SearchSafetyTests(unittest.IsolatedAsyncioTestCase):
    def service(self, datasets=None):
        return RailService(Path('data'), datasets=datasets or {
            'trenitalia': payload('trenitalia'), 'italo': payload('italo')},
            viaggiatreno_stations={'ROMA TERMINI': 'S08409', 'MILANO CENTRALE': 'S01700'})

    @patch('rail_service.now_rome', return_value=TODAY)
    async def test_future_schedules_never_receive_today_live_data(self, _):
        with patch('rail_service.journeys_between', return_value=[journey()]), \
             patch('rail_service.lookup_train', new_callable=AsyncMock) as live, \
             patch('rail_service.get_train_status', new_callable=AsyncMock) as italo_live:
            result = await self.service().search_journeys('ROMA TERMINI', 'MILANO CENTRALE',
                '2026-09-28', '00:00', 'all', 10)
        self.assertEqual(result['status'], 'ok')
        self.assertEqual(len(result['journeys']), 2)
        self.assertTrue(all(j['live']['status'] == 'not_applicable' for j in result['journeys']))
        live.assert_not_awaited()
        italo_live.assert_not_awaited()

    @patch('rail_service.now_rome', return_value=TODAY)
    async def test_expired_feed_does_not_become_no_trains(self, _):
        expired = payload('trenitalia')
        expired['metadata']['valid_from'] = '2025-12-14'
        expired['metadata']['valid_to'] = '2026-06-13'
        result = await self.service({'trenitalia': expired}).search_journeys(
            'ROMA TERMINI', 'MILANO CENTRALE', '2026-09-28', '00:00', 'trenitalia', 10)
        self.assertEqual(result['status'], 'unavailable')
        self.assertEqual(result['sources']['trenitalia']['status'], 'expired')
        self.assertEqual(result['journeys'], [])

    async def test_ambiguous_station_requires_choice(self):
        data = payload('trenitalia')
        data['stations'] = STATIONS + [{'id': 'tiburtina', 'name': 'ROMA TIBURTINA'}]
        result = await self.service({'trenitalia': data}).search_journeys(
            'Roma', 'MILANO CENTRALE', '2026-09-28', '00:00', 'trenitalia', 10)
        self.assertEqual(result['status'], 'ambiguous')
        self.assertEqual(len(result['choices']), 2)

    async def test_existing_viaggiatreno_station_id_resolves_for_schedule(self):
        with patch('rail_service.journeys_between', return_value=[journey()]) as query:
            result = await self.service().search_journeys('S08409', 'S01700',
                '2026-09-28', '00:00', 'trenitalia', 10)
        self.assertEqual(result['status'], 'ok')
        self.assertEqual(query.call_args.args[1:3], ('roma', 'milano'))

    @patch('rail_service.now_rome', return_value=TODAY)
    async def test_one_unavailable_provider_keeps_other_provider_results(self, _):
        with patch('rail_service.journeys_between', return_value=[journey()]):
            result = await self.service({'italo': payload('italo')}).search_journeys(
                'ROMA TERMINI', 'MILANO CENTRALE', '2026-09-28', '00:00', 'all', 10)
        self.assertEqual(result['status'], 'partial')
        self.assertEqual(result['journeys'][0]['provider'], 'italo')

    @patch('rail_service.now_rome', return_value=TODAY)
    async def test_missing_delay_is_not_reported_as_on_time(self, _):
        with patch('rail_service.journeys_between', return_value=[journey('2026-09-27')]), \
             patch('rail_service.lookup_train', new_callable=AsyncMock,
                   return_value={'numeroTreno': 1234}):
            result = await self.service().search_journeys('ROMA TERMINI', 'MILANO CENTRALE',
                '2026-09-27', '00:00', 'trenitalia', 10)
        self.assertIsNone(result['journeys'][0]['live']['delay_minutes'])

    async def test_purchase_links_do_not_claim_available_fares(self):
        result = self.service().ticket_links('Roma Termini', 'Milano Centrale', '2026-09-28')
        self.assertEqual(result['status'], 'prices_unavailable')
        self.assertTrue(all(link['price'] is None for link in result['operators']))
        self.assertTrue(all(link['search_prefilled'] is False for link in result['operators']))


class TrenitaliaStatusTests(unittest.TestCase):
    def test_placeholder_last_station_becomes_null(self):
        from datetime import date
        from rail_service import normalize_trenitalia_status
        for value, expected in (('--', None), ('', None), (None, None), ('ROMA TIBURTINA', 'ROMA TIBURTINA')):
            with self.subTest(value=value):
                status = normalize_trenitalia_status({'numeroTreno': 1, 'stazioneUltimoRilevamento': value}, date(2026, 9, 27))
                self.assertEqual(status['last_reported_station'], expected)


if __name__ == '__main__':
    unittest.main()
