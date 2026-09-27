"""Validated, date-aware queries over local NeTEx timetable caches."""

import gzip
import json
import unicodedata
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

ROME = ZoneInfo("Europe/Rome")
MAX_CACHE_BYTES = 128 * 1024 * 1024
MAX_SERVICE_DAYS = 740
MAX_OFFSET_DAYS = 3


def coverage_status(payload: dict | None, on_date: date) -> str:
    if payload is None:
        return "missing"
    try:
        if payload["schema_version"] != 2:
            return "invalid"
        start = date.fromisoformat(payload["metadata"]["valid_from"])
        end = date.fromisoformat(payload["metadata"]["valid_to"])
        if start > end or (end - start).days > MAX_SERVICE_DAYS:
            return "invalid"
        if on_date < start:
            return "not_yet_valid"
        if on_date > end:
            return "expired"
        return "available"
    except (KeyError, TypeError, ValueError):
        return "invalid"


def validate_payload(payload: dict) -> dict:
    try:
        if coverage_status(payload, date.today()) == "invalid":
            raise ValueError("Unsupported timetable schema or validity")
        if payload["provider"] not in {"trenitalia", "italo"}:
            raise ValueError("Unknown timetable provider")
        metadata = payload["metadata"]
        for field in ("source_url", "publication_timestamp", "fetched_at"):
            if not isinstance(metadata[field], str) or not metadata[field]:
                raise ValueError(f"Missing metadata: {field}")
        datetime.fromisoformat(metadata["publication_timestamp"])
        datetime.fromisoformat(metadata["fetched_at"])
        stations = payload["stations"]
        ids = {station["id"] for station in stations}
        if not ids or len(ids) != len(stations) or any(
            not isinstance(s["id"], str) or not s["id"] or not isinstance(s["name"], str) or not s["name"]
            for s in stations
        ):
            raise ValueError("Invalid station identities")
        if not payload["journeys"]:
            raise ValueError("Empty timetable")
        journey_ids = set()
        for journey in payload["journeys"]:
            if not journey["id"] or journey["id"] in journey_ids:
                raise ValueError("Invalid or duplicate service identity")
            journey_ids.add(journey["id"])
            for field in ("train_number", "line"):
                if not isinstance(journey[field], str):
                    raise ValueError("Invalid service label")
            days = journey["dates"]
            if not isinstance(days, list) or not days or days != sorted(set(days)) or len(days) > MAX_SERVICE_DAYS + 1:
                raise ValueError("Invalid service calendar")
            if any(coverage_status(payload, date.fromisoformat(day)) != "available" for day in days):
                raise ValueError("Service calendar outside dataset validity")
            if len(journey["stops"]) < 2:
                raise ValueError("Insufficient stops")
            previous = -1
            for stop in journey["stops"]:
                if stop["id"] not in ids:
                    raise ValueError("Unresolved station")
                for flag in ("boarding", "alighting"):
                    if type(stop[flag]) is not bool:
                        raise ValueError("Invalid boarding/alighting rule")
                for field in ("arrival", "departure"):
                    value = stop[field]
                    if value is None:
                        continue
                    if type(value) is not int or not 0 <= value < (MAX_OFFSET_DAYS + 1) * 86400 or value < previous:
                        raise ValueError("Invalid or decreasing passing time")
                    previous = value
        return payload
    except (KeyError, TypeError, AttributeError) as exc:
        raise ValueError("Malformed timetable cache") from exc


def load_timetable(path: Path) -> dict:
    try:
        with gzip.open(path, "rb") as stream:
            data = stream.read(MAX_CACHE_BYTES + 1)
        if len(data) > MAX_CACHE_BYTES:
            raise ValueError("Timetable cache exceeds size limit")
        return validate_payload(json.loads(data))
    except (gzip.BadGzipFile, EOFError, json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise ValueError("Invalid compressed timetable cache") from exc


def _normalise(value: str) -> str:
    return " ".join("".join(c for c in unicodedata.normalize("NFKD", value.casefold()) if not unicodedata.combining(c)).split())


def search_stations(payload: dict, query: str) -> list[dict]:
    stations = payload.get("stations", [])
    exact_id = [station for station in stations if station["id"] == query.strip()]
    if exact_id:
        return exact_id
    query = _normalise(query)
    if not query:
        return []
    exact = [station for station in stations if _normalise(station["name"]) == query]
    matches = exact or [station for station in stations if query in _normalise(station["name"])]
    return sorted(matches, key=lambda station: (station["name"].casefold(), station["id"]))


def _local_time(service_day: date, seconds: int) -> datetime | None:
    local = datetime.combine(service_day, time()) + timedelta(seconds=seconds)
    first = local.replace(tzinfo=ROME, fold=0)
    second = local.replace(tzinfo=ROME, fold=1)
    # NeTEx supplies no fold here: ambiguous or nonexistent wall times fail closed.
    if first.utcoffset() != second.utcoffset():
        return None
    if first.astimezone(timezone.utc).astimezone(ROME).replace(tzinfo=None) != local:
        return None
    return first


def journeys_between(payload: dict, origin_id: str, destination_id: str, departure_date: date, after: str = "00:00") -> list[dict]:
    if coverage_status(payload, departure_date) != "available" or origin_id == destination_id:
        return []
    cutoff = time.fromisoformat(after)
    if cutoff.tzinfo:
        raise ValueError("after must be a local time")
    station_names = {station["id"]: station["name"] for station in payload["stations"]}
    if origin_id not in station_names or destination_id not in station_names:
        return []
    results = []
    for journey in payload["journeys"]:
        stops = journey["stops"]
        for index, origin in enumerate(stops[:-1]):
            if origin["id"] != origin_id or not origin["boarding"] or origin["departure"] is None:
                continue
            service_day = departure_date - timedelta(days=origin["departure"] // 86400)
            if service_day.isoformat() not in journey["dates"]:
                continue
            departure = _local_time(service_day, origin["departure"])
            if departure is None or departure.time() < cutoff:
                continue
            for end, destination in enumerate(stops[index + 1:], index + 1):
                if destination["id"] != destination_id or not destination["alighting"] or destination["arrival"] is None:
                    continue
                arrival = _local_time(service_day, destination["arrival"])
                if arrival is None or arrival.timestamp() <= departure.timestamp():
                    continue
                results.append({
                    "service_id": journey["id"], "service_date": service_day.isoformat(),
                    "train_number": journey["train_number"], "line": journey["line"],
                    "origin": {"id": origin_id, "name": station_names[origin_id]},
                    "destination": {"id": destination_id, "name": station_names[destination_id]},
                    "departure": departure.isoformat(), "arrival": arrival.isoformat(),
                    "intermediate_stops": [station_names[s["id"]] for s in stops[index + 1:end]],
                })
                break
    return sorted(results, key=lambda result: (result["departure"], result["arrival"], result["service_id"]))
