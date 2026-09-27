#!/usr/bin/env python3
"""Convert official Italian-profile NeTEx XML into a validated local cache."""

import argparse
import gzip
import json
import os
import re
import tempfile
import xml.etree.ElementTree as ET
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from timetable import MAX_OFFSET_DAYS, MAX_SERVICE_DAYS, load_timetable, validate_payload

NS = "{http://www.netex.org.uk/netex}"
MAX_XML_BYTES = 768 * 1024 * 1024
DAY_NAMES = {name: {number} for number, name in enumerate(
    ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")
)}
DAY_NAMES.update(Everyday=set(range(7)), Weekdays=set(range(5)), Weekend={5, 6})


def _text(element, path):
    return (element.findtext("/".join(NS + part for part in path.split("/"))) or "").strip()


def _boolean(element, path, default=True):
    value = _text(element, path)
    if not value:
        return default
    if value not in {"true", "false", "1", "0"}:
        raise ValueError(f"Invalid XML boolean: {path}")
    return value in {"true", "1"}


def _ref(element, path):
    found = element.find("/".join(NS + part for part in path.split("/")))
    return found.get("ref", "") if found is not None else ""


def _range(element, inherited=None):
    start, end = _text(element, "FromDate"), _text(element, "ToDate")
    if not start or not end:
        raise ValueError("Missing validity boundary")
    bounds = date.fromisoformat(start[:10]), date.fromisoformat(end[:10])
    if inherited:
        bounds = max(bounds[0], inherited[0]), min(bounds[1], inherited[1])
    if bounds[0] > bounds[1] or (bounds[1] - bounds[0]).days > MAX_SERVICE_DAYS:
        raise ValueError("Invalid or excessive validity range")
    return bounds


def _days(bounds):
    return {bounds[0] + timedelta(days=offset) for offset in range((bounds[1] - bounds[0]).days + 1)}


class BoundedXML:
    def __init__(self, stream, limit=MAX_XML_BYTES):
        self.stream, self.remaining, self.tail = stream, limit, b""

    def read(self, size=-1):
        data = self.stream.read(min(size if size >= 0 else 65536, self.remaining + 1))
        self.remaining -= len(data)
        if self.remaining < 0:
            raise ValueError("Uncompressed XML exceeds size limit")
        probe = (self.tail + data).upper()
        if b"\x00" in probe or b"<!DOCTYPE" in probe or b"<!ENTITY" in probe:
            raise ValueError("DTD and entity declarations are unsupported")
        self.tail = probe[-16:]
        return data


def parse_netex(stream, *, provider: str, source_url: str, fetched_at: str | None = None) -> dict:
    stations, assignments, patterns, lines, day_types, periods, operating_days = {}, {}, {}, {}, {}, {}, {}
    calendar_assignments, raw_journeys = defaultdict(list), []
    publication, global_ranges = "", []
    targets = {"StopPlace", "PassengerStopAssignment", "ServiceJourneyPattern", "Line", "DayType", "DayTypeAssignment", "OperatingPeriod", "UicOperatingPeriod", "OperatingDay", "ServiceJourney", "ValidBetween"}
    stack, holding = [], None
    excluded_non_rail = excluded_combined_services = 0
    seen = defaultdict(set)
    try:
        for event, element in ET.iterparse(BoundedXML(stream), events=("start", "end")):
            tag = element.tag.removeprefix(NS)
            if event == "start":
                if tag in {"AvailabilityConditionRef", "ValidityConditionRef", "AvailabilityCondition", "ValidityCondition"}:
                    raise ValueError(f"Unsupported validity condition: {tag}")
                stack.append([element, stack[-1][1] if stack else None])
                if holding is None and tag in targets:
                    holding = len(stack)
                continue
            bounds = stack[-1][1]
            if tag == "PublicationTimestamp":
                publication = (element.text or "").strip()
            if tag == "TimeZone" and (element.text or "").strip() not in {"", "Europe/Rome"}:
                raise ValueError("Only Europe/Rome timetables are supported")
            if holding == len(stack):
                identity = element.get("id", "")
                if identity:
                    if identity in seen[tag]:
                        raise ValueError(f"Duplicate {tag} identity: {identity}")
                    seen[tag].add(identity)
                if tag == "ValidBetween":
                    bounds = _range(element, bounds)
                    if len(stack) > 1:
                        stack[-2][1] = bounds
                        if stack[-2][0].tag == NS + "CompositeFrame":
                            global_ranges.append(bounds)
                elif tag == "StopPlace":
                    name = _text(element, "Name")
                    if not identity or not name or identity in stations:
                        raise ValueError("Invalid or duplicated StopPlace")
                    stations[identity] = name
                elif tag == "PassengerStopAssignment":
                    point, place = _ref(element, "ScheduledStopPointRef"), _ref(element, "StopPlaceRef")
                    if point in assignments and assignments[point] != place:
                        raise ValueError("Conflicting stop assignment")
                    assignments[point] = place
                elif tag == "Line":
                    lines[identity] = {"name": _text(element, "Name"), "code": _text(element, "PublicCode"), "mode": _text(element, "TransportMode")}
                elif tag == "ServiceJourneyPattern":
                    points = []
                    for point in element.findall(NS + "pointsInSequence/" + NS + "StopPointInJourneyPattern"):
                        points.append({"point": point.get("id", ""), "order": int(point.get("order", "0")),
                                       "stop": _ref(point, "ScheduledStopPointRef"),
                                       "boarding": _boolean(point, "ForBoarding"), "alighting": _boolean(point, "ForAlighting")})
                    if len({p["order"] for p in points}) != len(points) or any(p["order"] < 1 for p in points):
                        raise ValueError("Invalid journey pattern order")
                    patterns[identity] = (sorted(points, key=lambda p: p["order"]), _ref(element, "RouteView/LineRef"))
                elif tag == "DayType":
                    own_validity = element.find(NS + "ValidBetween")
                    if own_validity is not None:
                        bounds = _range(own_validity, bounds)
                    words = [word for entry in element.findall(".//" + NS + "DaysOfWeek") for word in (entry.text or "").split()]
                    unknown = any(word not in DAY_NAMES for word in words) or any((entry.text or "").strip() for entry in element.findall(".//" + NS + "HolidayTypes"))
                    day_types[identity] = (set().union(*(DAY_NAMES.get(word, set()) for word in words)), bounds, unknown)
                elif tag in {"OperatingPeriod", "UicOperatingPeriod"}:
                    period_bounds = _range(element)
                    active = _days(period_bounds)
                    if tag == "UicOperatingPeriod":
                        bits = _text(element, "ValidDayBits")
                        if len(bits) != len(active) or set(bits) - {"0", "1"}:
                            raise ValueError(f"Invalid UIC calendar bits: {identity}")
                        active = {period_bounds[0] + timedelta(days=i) for i, bit in enumerate(bits) if bit == "1"}
                    if bounds:
                        active &= _days(bounds)
                    periods[identity] = (active, tag == "UicOperatingPeriod")
                elif tag == "OperatingDay":
                    operating_days[identity] = date.fromisoformat(_text(element, "CalendarDate")[:10])
                elif tag == "DayTypeAssignment":
                    available = _text(element, "isAvailable") or _text(element, "IsAvailable") or "true"
                    if available not in {"true", "false", "1", "0"}:
                        raise ValueError("Invalid calendar availability")
                    calendar_assignments[_ref(element, "DayTypeRef")].append({"period": _ref(element, "OperatingPeriodRef"),
                        "day": _ref(element, "OperatingDayRef"), "date": _text(element, "Date"), "available": available in {"true", "1"}, "bounds": bounds})
                elif tag == "ServiceJourney":
                    mode = _text(element, "TransportMode")
                    if mode and mode != "rail":
                        excluded_non_rail += 1
                    else:
                        passing = {}
                        for point in element.findall(NS + "passingTimes/" + NS + "TimetabledPassingTime"):
                            ref = _ref(point, "StopPointInJourneyPatternRef")
                            if not ref or ref in passing:
                                raise ValueError("Missing or duplicated passing-time reference")
                            passing[ref] = tuple(_text(point, field) for field in ("ArrivalTime", "ArrivalDayOffset", "DepartureTime", "DepartureDayOffset"))
                        own_validity = element.find(NS + "ValidBetween")
                        if own_validity is not None:
                            bounds = _range(own_validity, bounds)
                        raw_journeys.append({"id": identity, "name": _text(element, "Name"), "code": _text(element, "PublicCode"),
                            "pattern": _ref(element, "ServiceJourneyPatternRef"), "daytypes": [ref.get("ref", "") for ref in element.findall(NS + "dayTypes/" + NS + "DayTypeRef")],
                            "passing": passing, "bounds": bounds, "offset": int(_text(element, "DepartureDayOffset") or "0")})
                holding = None
            if holding is None:
                element.clear()
                if len(stack) > 1:
                    stack[-2][0].remove(element)
            stack.pop()
    except ET.ParseError as exc:
        raise ValueError("Invalid NeTEx XML") from exc
    if not global_ranges or not publication:
        raise ValueError("Missing publication timestamp or CompositeFrame validity")
    start, end = min(b[0] for b in global_ranges), max(b[1] for b in global_ranges)
    calendar_cache = {}

    def calendar(identity):
        if identity in calendar_cache:
            return calendar_cache[identity]
        if identity not in day_types:
            raise ValueError(f"Unknown day type: {identity}")
        weekdays, bounds, unknown = day_types[identity]
        if not bounds or unknown:
            raise ValueError(f"Unsupported day type: {identity}")
        additions, removals = set(), set()
        entries = calendar_assignments.get(identity, [])
        if not entries:
            if not weekdays:
                raise ValueError(f"Unspecified calendar: {identity}")
            additions = {day for day in _days(bounds) if day.weekday() in weekdays}
        for entry in entries:
            if sum(bool(entry[k]) for k in ("period", "day", "date")) != 1:
                raise ValueError("Unsupported day type assignment")
            if entry["date"]:
                active = {date.fromisoformat(entry["date"][:10])}
            elif entry["day"]:
                if entry["day"] not in operating_days:
                    raise ValueError("Unknown operating day")
                active = {operating_days[entry["day"]]}
            else:
                if entry["period"] not in periods:
                    raise ValueError("Unknown operating period")
                active, explicit = periods[entry["period"]]
                if not explicit:
                    if not weekdays:
                        raise ValueError("Period requires weekday rules")
                    active = {day for day in active if day.weekday() in weekdays}
            active = active & _days(bounds)
            if entry["bounds"]:
                active &= _days(entry["bounds"])
            (additions if entry["available"] else removals).update(active)
        calendar_cache[identity] = additions - removals
        return calendar_cache[identity]

    journeys = []
    for raw in raw_journeys:
        if not raw["bounds"] or not raw["daytypes"]:
            raise ValueError(f"Missing journey validity/calendar: {raw['id']}")
        active = set().union(*(calendar(ref) for ref in raw["daytypes"])) & _days(raw["bounds"])
        if not active:
            continue
        if raw["pattern"] not in patterns:
            raise ValueError("Unresolved journey pattern")
        points, line_ref = patterns[raw["pattern"]]
        line = lines.get(line_ref, {})
        if line.get("mode") not in {None, "", "rail"}:
            excluded_non_rail += 1
            continue
        number = raw["code"] or (line.get("code") if provider == "italo" else raw["name"]) or raw["name"]
        if provider == "italo":
            single_train = re.fullmatch(r"(\d+)(?:_#\d+)?", number)
            if single_train is None:
                excluded_combined_services += 1
                continue
            number = single_train.group(1)
        if set(raw["passing"]) != {point["point"] for point in points}:
            raise ValueError(f"Passing times do not match pattern: {raw['id']}")
        stops, previous = [], raw["offset"] * 86400
        for point in points:
            station = assignments.get(point["stop"])
            if station not in stations:
                raise ValueError("Unresolved stop identity")
            arr, arr_offset, dep, dep_offset = raw["passing"][point["point"]]
            values = []
            for clock, offset in ((arr, arr_offset), (dep, dep_offset)):
                if not clock:
                    values.append(None)
                    continue
                match = re.fullmatch(r"(\d{2}):([0-5]\d):([0-5]\d)", clock)
                if not match:
                    raise ValueError("Invalid passing time")
                hours, minutes, seconds = map(int, match.groups())
                value = hours * 3600 + minutes * 60 + seconds
                if offset:
                    value += int(offset) * 86400
                elif hours < 24:
                    value += previous // 86400 * 86400
                    if value < previous:
                        value += 86400
                if value < previous or value >= (MAX_OFFSET_DAYS + 1) * 86400:
                    raise ValueError(f"Invalid passing time order/offset: {raw['id']}")
                previous = value
                values.append(value)
            stops.append({"id": station, "arrival": values[0], "departure": values[1], "boarding": point["boarding"], "alighting": point["alighting"]})
        journeys.append({"id": raw["id"], "train_number": number, "line": line.get("name", ""), "dates": sorted(day.isoformat() for day in active), "stops": stops})
    used_stations = {stop["id"] for journey in journeys for stop in journey["stops"]}
    return validate_payload({"schema_version": 2, "provider": provider,
        "metadata": {"source_url": source_url, "publication_timestamp": publication, "valid_from": start.isoformat(), "valid_to": end.isoformat(),
                     "fetched_at": fetched_at or datetime.now(timezone.utc).isoformat(), "excluded_non_rail": excluded_non_rail,
                     "excluded_combined_services": excluded_combined_services},
        "stations": [{"id": identity, "name": stations[identity]} for identity in sorted(used_stations)], "journeys": journeys})


def write_timetable(payload: dict, output: Path) -> None:
    validate_payload(payload)
    output.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=output.name + ".", suffix=".tmp", dir=output.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(gzip.compress(json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8"), mtime=0))
            stream.flush()
            os.fsync(stream.fileno())
        load_timetable(Path(temporary))
        os.replace(temporary, output)
    finally:
        Path(temporary).unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("--provider", choices=("trenitalia", "italo"), required=True)
    parser.add_argument("--source-url", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    opener = gzip.open if args.input.suffix == ".gz" else open
    with opener(args.input, "rb") as stream:
        payload = parse_netex(stream, provider=args.provider, source_url=args.source_url)
    write_timetable(payload, args.output)
    print(f"{args.provider}: {len(payload['journeys'])} journeys saved to {args.output}")


if __name__ == "__main__":
    main()
