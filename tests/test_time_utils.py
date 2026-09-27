import unittest
from datetime import datetime
from urllib.parse import unquote
from zoneinfo import ZoneInfo

from time_utils import format_viaggiatreno_time, timestamp_to_iso


class RailwayTimeTests(unittest.TestCase):
    def test_request_uses_rome_daylight_saving_offset(self):
        value = datetime(2026, 9, 27, 10, 30, tzinfo=ZoneInfo('UTC'))
        self.assertEqual(unquote(format_viaggiatreno_time(value)),
                         'Sun Sep 27 2026 12:30:00 GMT+0200')

    def test_request_uses_winter_offset(self):
        value = datetime(2026, 12, 27, 10, 30, tzinfo=ZoneInfo('UTC'))
        self.assertEqual(unquote(format_viaggiatreno_time(value)),
                         'Sun Dec 27 2026 11:30:00 GMT+0100')

    def test_millisecond_timestamp_has_explicit_rome_offset(self):
        value = datetime(2026, 9, 27, 23, 15, tzinfo=ZoneInfo('UTC'))
        self.assertEqual(timestamp_to_iso(int(value.timestamp() * 1000)),
                         '2026-09-28T01:15:00+02:00')

    def test_unknown_timestamp_stays_unknown(self):
        for value in (None, '', 'invalid', 0, -1):
            self.assertIsNone(timestamp_to_iso(value))


if __name__ == '__main__':
    unittest.main()
