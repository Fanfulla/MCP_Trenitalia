import gzip
import importlib
import importlib.util
import io
import json
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

import build_timetable


FIXTURE = Path(__file__).parent / "fixtures" / "netex_calendar.xml"


class TimetableTests(unittest.TestCase):
    def parse(self, xml=None):
        self.assertTrue(hasattr(build_timetable, "parse_netex"), "date-aware NeTEx parser is missing")
        return build_timetable.parse_netex(
            io.BytesIO(xml or FIXTURE.read_bytes()), provider="trenitalia",
            source_url="https://www.cciss.it/fixture", fetched_at="2026-10-21T00:00:00Z",
        )

    def module(self):
        self.assertIsNotNone(importlib.util.find_spec("timetable"), "timetable query module is missing")
        return importlib.import_module("timetable")

    def test_inherits_composite_validity_and_rejects_outside_coverage(self):
        payload = self.parse()
        self.assertEqual(payload["metadata"]["valid_from"], "2026-10-23")
        self.assertEqual(payload["metadata"]["valid_to"], "2026-10-27")
        tt = self.module()
        self.assertEqual(tt.coverage_status(payload, date(2026, 10, 22)), "not_yet_valid")
        self.assertEqual(tt.coverage_status(payload, date(2026, 10, 28)), "expired")
        self.assertEqual(tt.journeys_between(payload, "A", "C", date(2026, 10, 28)), [])

    def test_weekday_rule_explicit_addition_and_removal(self):
        payload, tt = self.parse(), self.module()
        self.assertEqual(len(tt.journeys_between(payload, "A", "C", date(2026, 10, 23))), 1)
        self.assertEqual(len(tt.journeys_between(payload, "A", "C", date(2026, 10, 24))), 1)
        self.assertEqual(tt.journeys_between(payload, "A", "C", date(2026, 10, 26)), [])

    def test_overnight_boarding_date_and_dst_offsets(self):
        results = self.module().journeys_between(self.parse(), "B", "C", date(2026, 10, 25))
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["departure"], "2026-10-25T00:30:00+02:00")
        self.assertEqual(results[0]["arrival"], "2026-10-25T03:10:00+01:00")
        self.assertEqual(results[0]["service_date"], "2026-10-24")

    def test_exact_ids_ambiguous_search_and_ordered_intermediate_stops(self):
        payload, tt = self.parse(), self.module()
        self.assertEqual([s["id"] for s in tt.search_stations(payload, "Roma")], ["A", "B"])
        self.assertEqual(tt.journeys_between(payload, "Roma", "C", date(2026, 10, 23)), [])
        result = tt.journeys_between(payload, "A", "C", date(2026, 10, 23))[0]
        self.assertEqual(result["intermediate_stops"], ["Roma Tiburtina"])
        self.assertEqual(result["train_number"], "999")

    def test_uic_bits_are_authoritative_and_multiple_daytypes_are_union(self):
        xml = FIXTURE.read_text().replace(
            '</dayTypes>', '<DayType id="uic"/></dayTypes>', 1
        ).replace('</operatingPeriods>', '<UicOperatingPeriod id="bits"><FromDate>2026-10-23</FromDate><ToDate>2026-10-27</ToDate><ValidDayBits>00101</ValidDayBits></UicOperatingPeriod></operatingPeriods>')
        xml = xml.replace('</dayTypeAssignments>', '<DayTypeAssignment><OperatingPeriodRef ref="bits"/><DayTypeRef ref="uic"/></DayTypeAssignment></dayTypeAssignments>')
        xml = xml.replace('<DayTypeRef ref="weekday"/></dayTypes>', '<DayTypeRef ref="weekday"/><DayTypeRef ref="uic"/></dayTypes>')
        payload, tt = self.parse(xml.encode()), self.module()
        self.assertEqual(len(tt.journeys_between(payload, "A", "C", date(2026, 10, 25))), 1)
        self.assertEqual(len(tt.journeys_between(payload, "A", "C", date(2026, 10, 27))), 1)

    def test_unknown_calendar_and_missing_validity_fail_closed(self):
        for xml in [
            FIXTURE.read_text().replace('ref="weekday"/></dayTypes>', 'ref="missing"/></dayTypes>'),
            FIXTURE.read_text().replace('<ValidBetween>', '<unused>').replace('</ValidBetween>', '</unused>'),
            FIXTURE.read_text().replace('Friday Monday', 'PublicHoliday'),
        ]:
            with self.subTest(xml=xml[-90:]), self.assertRaises(ValueError):
                self.parse(xml.encode())

    def test_invalid_uic_bits_and_unresolved_stop_fail_closed(self):
        xml = FIXTURE.read_text().replace('<OperatingPeriod id="period">', '<UicOperatingPeriod id="period">').replace('</OperatingPeriod>', '<ValidDayBits>10x</ValidDayBits></UicOperatingPeriod>')
        for candidate in [xml, FIXTURE.read_text().replace('ref="sb"/></StopPointInJourneyPattern>', 'ref="unknown"/></StopPointInJourneyPattern>')]:
            with self.assertRaises(ValueError):
                self.parse(candidate.encode())

    def test_after_filter_and_no_boarding_constraint(self):
        tt, payload = self.module(), self.parse()
        self.assertEqual(tt.journeys_between(payload, "B", "C", date(2026, 10, 24), after="00:31"), [])
        xml = FIXTURE.read_text().replace('<ScheduledStopPointRef ref="sb"/></StopPointInJourneyPattern>', '<ScheduledStopPointRef ref="sb"/><ForBoarding>false</ForBoarding></StopPointInJourneyPattern>')
        self.assertEqual(tt.journeys_between(self.parse(xml.encode()), "B", "C", date(2026, 10, 24)), [])

    def test_xml_boolean_zero_disallows_boarding_and_alighting(self):
        for flag, origin, destination in (("ForBoarding", "B", "C"), ("ForAlighting", "A", "B")):
            xml = FIXTURE.read_text().replace('<ScheduledStopPointRef ref="sb"/></StopPointInJourneyPattern>',
                f'<ScheduledStopPointRef ref="sb"/><{flag}>0</{flag}></StopPointInJourneyPattern>')
            with self.subTest(flag=flag):
                self.assertEqual(self.module().journeys_between(self.parse(xml.encode()),
                    origin, destination, date(2026, 10, 24)), [])

    def test_unknown_boarding_boolean_is_rejected(self):
        xml = FIXTURE.read_text().replace('<ScheduledStopPointRef ref="sb"/></StopPointInJourneyPattern>',
            '<ScheduledStopPointRef ref="sb"/><ForBoarding>maybe</ForBoarding></StopPointInJourneyPattern>')
        with self.assertRaises(ValueError):
            self.parse(xml.encode())

    def test_old_dataset_and_malformed_v2_are_rejected(self):
        tt = self.module()
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "data.gz"
            for payload in [[{"pf": "", "pt": ""}], {"schema_version": 2}]:
                path.write_bytes(gzip.compress(json.dumps(payload).encode()))
                with self.assertRaises(ValueError):
                    tt.load_timetable(path)

    def test_frame_validity_limits_inherited_service_dates(self):
        xml = FIXTURE.read_text().replace('<TimetableFrame>', '<TimetableFrame><ValidBetween><FromDate>2026-10-24</FromDate><ToDate>2026-10-27</ToDate></ValidBetween>')
        payload, tt = self.parse(xml.encode()), self.module()
        self.assertEqual(tt.journeys_between(payload, "A", "C", date(2026, 10, 23)), [])
        self.assertEqual(len(tt.journeys_between(payload, "A", "C", date(2026, 10, 24))), 1)

    def test_unresolved_validity_condition_and_duplicate_day_type_are_rejected(self):
        base = FIXTURE.read_text()
        for xml in [
            base.replace('<Name>999</Name>', '<Name>999</Name><validityConditions><AvailabilityConditionRef ref="unknown"/></validityConditions>'),
            base.replace('</dayTypes>', '<DayType id="weekday"/></dayTypes>', 1),
        ]:
            with self.assertRaises(ValueError):
                self.parse(xml.encode())

    def test_unknown_timezone_is_rejected(self):
        xml = FIXTURE.read_text().replace('<frames>', '<FrameDefaults><DefaultLocale><TimeZone>Europe/London</TimeZone></DefaultLocale></FrameDefaults><frames>')
        with self.assertRaises(ValueError):
            self.parse(xml.encode())

    def test_nonexistent_or_ambiguous_dst_departures_are_not_invented(self):
        tt = self.module()
        payload = self.parse()
        journey = payload["journeys"][0]
        journey["dates"] = ["2026-10-24"]
        journey["stops"][1]["departure"] = 86400 + 2 * 3600 + 30 * 60
        self.assertEqual(tt.journeys_between(payload, "B", "C", date(2026, 10, 25)), [])
        payload["metadata"].update(valid_from="2026-03-28", valid_to="2026-03-30")
        journey["dates"] = ["2026-03-28"]
        self.assertEqual(tt.journeys_between(payload, "B", "C", date(2026, 3, 29)), [])

    def test_extended_hour_times_do_not_count_day_offset_twice(self):
        xml = FIXTURE.read_text().replace('<ArrivalTime>00:25:00</ArrivalTime><ArrivalDayOffset>1</ArrivalDayOffset>', '<ArrivalTime>24:25:00</ArrivalTime>').replace('<DepartureTime>00:30:00</DepartureTime><DepartureDayOffset>1</DepartureDayOffset>', '<DepartureTime>24:30:00</DepartureTime>').replace('<ArrivalTime>03:10:00</ArrivalTime><ArrivalDayOffset>1</ArrivalDayOffset>', '<ArrivalTime>27:10:00</ArrivalTime>')
        results = self.module().journeys_between(self.parse(xml.encode()), "B", "C", date(2026, 10, 24))
        self.assertEqual(results[0]["departure"], "2026-10-24T00:30:00+02:00")
        self.assertEqual(results[0]["arrival"], "2026-10-24T03:10:00+02:00")

    def test_uncompressed_limit_and_dtd_are_rejected(self):
        with self.assertRaises(ValueError):
            build_timetable.BoundedXML(io.BytesIO(b"12345"), limit=4).read()
        malicious = b'<!DOCTYPE PublicationDelivery [<!ENTITY value "expanded">]>' + FIXTURE.read_bytes().split(b'?>', 1)[1]
        with self.assertRaises(ValueError):
            self.parse(malicious)

    def test_italo_publiccode_uses_single_train_number_only(self):
        base = FIXTURE.read_text()
        xml = base.replace('<PublicCode>999</PublicCode>', '<PublicCode>999_#2</PublicCode>')
        payload = build_timetable.parse_netex(io.BytesIO(xml.encode()), provider="italo", source_url="https://www.cciss.it/fixture")
        self.assertEqual(payload["journeys"][0]["train_number"], "999")
        xml = base.replace('<PublicCode>999</PublicCode>', '<PublicCode>999_123</PublicCode>')
        with self.assertRaises(ValueError):
            build_timetable.parse_netex(io.BytesIO(xml.encode()), provider="italo", source_url="https://www.cciss.it/fixture")

    def test_refresh_failure_preserves_previous_file(self):
        self.assertIsNotNone(importlib.util.find_spec("update_data"), "refresh CLI is missing")
        updater = importlib.import_module("update_data")
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "timetable.json.gz"
            path.write_bytes(b"previous")
            with patch.object(updater, "download", return_value=b"<broken>"), self.assertRaises(ValueError):
                updater.refresh_provider("italo", output=path)
            self.assertEqual(path.read_bytes(), b"previous")

    def test_successful_refresh_writes_valid_cache_and_network_failure_preserves_it(self):
        updater = importlib.import_module("update_data")
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "timetable.json.gz"
            with patch.object(updater, "download", return_value=gzip.compress(FIXTURE.read_bytes())):
                updater.refresh_provider("trenitalia", output=path)
            self.assertEqual(self.module().load_timetable(path)["provider"], "trenitalia")
            previous = path.read_bytes()
            with patch.object(updater, "download", side_effect=OSError("offline")), self.assertRaises(OSError):
                updater.refresh_provider("trenitalia", output=path)
            self.assertEqual(path.read_bytes(), previous)

    def test_refresh_rejects_unofficial_urls_and_oversized_downloads(self):
        updater = importlib.import_module("update_data")
        for url in ("http://www.cciss.it/feed", "https://example.org/feed", "https://user@www.cciss.it/feed"):
            with self.assertRaises(ValueError):
                updater.download(url)
        response = io.BytesIO(b"12345")
        response.headers, response.url = {}, "https://www.cciss.it/fixture"
        with patch.object(updater.urllib.request.OpenerDirector, "open", return_value=response), patch.object(updater, "MAX_DOWNLOAD_BYTES", 4), self.assertRaises(ValueError):
            updater.download(response.url)


if __name__ == "__main__":
    unittest.main()
