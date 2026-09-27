"""Read-only adapter for the endpoints used by the public Italo In Viaggio site.

Verified 2026-09-27 in the official train/station JavaScript chunks. These
endpoints have no published compatibility guarantee or service-date field.
"""

from __future__ import annotations

from html import unescape
from html.parser import HTMLParser
import json
import re
from urllib.parse import urlencode

from http_client import UpstreamError, decode_json, get_response, get_text

BASE_URL = "https://italoinviaggio.italotreno.com"


def _text(value) -> str | None:
    if value is None:
        return None
    if not isinstance(value, (str, int)) or isinstance(value, bool):
        raise UpstreamError("malformed_payload", BASE_URL)
    return unescape(re.sub(r"<[^>]*>", "", str(value))).strip()[:500] or None


def _station_name(value: str | None) -> str | None:
    if not value or value != value.lower():
        return value
    return " ".join(word.upper() if word == "av" else word.capitalize() for word in re.split(r"[-\s]+", value) if word)


def _minutes(value) -> int | None:
    if value is None or value == "":
        return None
    if isinstance(value, bool) or not re.fullmatch(r"-?\d{1,4}", str(value)):
        raise UpstreamError("malformed_payload", BASE_URL)
    return int(value)


def _clock(value) -> str | None:
    value = _text(value)
    if value is not None and not re.fullmatch(r"(?:[01]\d|2[0-3]):[0-5]\d", value):
        raise UpstreamError("malformed_payload", BASE_URL)
    return value


def _envelope(payload, response) -> dict:
    url = str(response.request.url)
    if not isinstance(payload, dict) or not isinstance(payload.get("IsEmpty"), bool):
        raise UpstreamError("malformed_payload", url)
    return {
        "provider": "italo", "service_date": None, "source_url": url,
        "observed_at": response.extensions["observed_at"],
        "last_update_time": _clock(payload.get("LastUpdate")),
        "freshness": "date_unverified",
    }


def _stop(raw: dict, *, passed: bool, first: bool = False, last: bool = False) -> dict:
    if not isinstance(raw, dict) or not raw.get("LocationCode") or not raw.get("LocationDescription"):
        raise UpstreamError("malformed_payload", BASE_URL)
    # The source uses 01:00 and 1901 dates as sentinels at journey endpoints.
    arrival = None if first else _clock(raw.get("ActualArrivalTime"))
    departure = None if last else _clock(raw.get("ActualDepartureTime"))
    return {
        "station_id": _text(raw["LocationCode"]), "station_name": _text(raw["LocationDescription"]),
        "scheduled_arrival": None if first else _clock(raw.get("EstimatedArrivalTime")),
        "scheduled_departure": None if last else _clock(raw.get("EstimatedDepartureTime")),
        "actual_arrival": arrival if passed else None, "actual_departure": departure if passed else None,
        "expected_arrival": None if passed else arrival, "expected_departure": None if passed else departure,
        "platform": _text(raw.get("ActualArrivalPlatform")), "passed": passed,
    }


async def get_train_status(numero_treno: str) -> dict:
    number = str(numero_treno).strip()
    if not re.fullmatch(r"\d{1,6}", number):
        raise ValueError("Train number must contain 1 to 6 digits")
    number = str(int(number))
    url = f"{BASE_URL}/api/RicercaTrenoService?{urlencode({'TrainNumber': number})}"
    response = await get_response(url)
    payload = decode_json(response)
    result = _envelope(payload, response)
    result.update(train_number=number, delay_minutes=None, status="not_found", origin=None, destination=None, stops=[])
    if payload["IsEmpty"]:
        return result
    schedule = payload.get("TrainSchedule")
    if not isinstance(schedule, dict) or str(schedule.get("TrainNumber")) != number:
        raise UpstreamError("malformed_payload", url)
    disruption = schedule.get("Distruption")
    if disruption is None:
        disruption = {}
    if not isinstance(disruption, dict):
        raise UpstreamError("malformed_payload", url)
    warning = disruption.get("Warning")
    if warning is not None and not isinstance(warning, bool):
        raise UpstreamError("malformed_payload", url)
    delay = _minutes(disruption.get("DelayAmount"))
    result.update(
        delay_minutes=None if warning else delay,
        status="stale" if warning else "unknown" if delay is None else "delayed" if delay > 0 else "early" if delay < 0 else "on_time",
        freshness="stale" if warning else "date_unverified",
        origin={"id": _text(schedule.get("DepartureStation")), "name": _text(schedule.get("DepartureStationDescription"))},
        destination={"id": _text(schedule.get("ArrivalStation")), "name": _text(schedule.get("ArrivalStationDescription"))},
    )
    if not all(result[side][key] for side in ("origin", "destination") for key in ("id", "name")):
        raise UpstreamError("malformed_payload", url)
    stopped, remaining = schedule.get("StazioniFerme"), schedule.get("StazioniNonFerme")
    if not isinstance(stopped, list) or not isinstance(remaining, list):
        raise UpstreamError("malformed_payload", url)
    stops = [_stop(schedule.get("StazionePartenza"), passed=bool(stopped), first=True)]
    for passed, rows in ((True, stopped), (False, remaining)):
        for row in rows:
            if not isinstance(row, dict):
                raise UpstreamError("malformed_payload", url)
            stops.append(_stop(row, passed=passed, last=row.get("LocationCode") == schedule.get("ArrivalStation")))
    result["stops"] = stops
    return result


class _StationCatalogue(HTMLParser):
    def __init__(self):
        super().__init__()
        self.active = False
        self.parts = []

    def handle_starttag(self, tag, attrs):
        if tag == "span" and dict(attrs).get("data-ntv-name") == "station-to-url" and not self.parts:
            self.active = True

    def handle_endtag(self, tag):
        if tag == "span":
            self.active = False

    def handle_data(self, data):
        if self.active:
            self.parts.append(data)


async def get_station_board(station: str, kind: str = "departures") -> dict:
    if kind not in {"departures", "arrivals"}:
        raise ValueError("kind must be departures or arrivals")
    if not isinstance(station, str) or not station.strip() or len(station) > 120:
        raise ValueError("A station name or Italo live station code is required")
    page = await get_text(BASE_URL + "/", ttl=300)
    parser = _StationCatalogue()
    parser.feed(page)
    try:
        catalogue = json.loads("".join(parser.parts))
    except (ValueError, TypeError):
        raise UpstreamError("malformed_payload", BASE_URL) from None
    if not isinstance(catalogue, list) or any(not isinstance(item, dict) or not isinstance(item.get("code"), str) or not isinstance(item.get("urlCoding"), str) for item in catalogue):
        raise UpstreamError("malformed_payload", BASE_URL)
    query = station.strip().casefold().replace("-", " ")
    matches = [item for item in catalogue if query in {item["code"].casefold(), item["urlCoding"].casefold().replace("-", " ")}]
    if not matches:
        matches = [item for item in catalogue if item["urlCoding"].casefold().replace("-", " ").startswith(query) or query.startswith(item["urlCoding"].casefold().replace("-", " "))]
    matches = list({item["code"]: item for item in matches}.values())
    if not matches:
        return {"provider": "italo", "status": "not_found", "station": station, "kind": kind, "source_url": BASE_URL, "service_date": None, "trains": []}
    if len(matches) > 1:
        raise UpstreamError("ambiguous", BASE_URL, candidates=matches)
    selected = matches[0]
    url = f"{BASE_URL}/api/RicercaStazioneService?{urlencode({'CodiceStazione': selected['code'], 'NomeStazione': selected['urlCoding'].lower()})}"
    response = await get_response(url)
    payload = decode_json(response)
    result = _envelope(payload, response)
    result.update(station={"id": selected["code"], "name": _station_name(_text(payload.get("DescrizioneLocalita")) or selected["urlCoding"])}, kind=kind, status="no_results" if payload["IsEmpty"] else "ok", trains=[])
    if payload["IsEmpty"]:
        return result
    rows = payload.get("ListaTreniPartenza" if kind == "departures" else "ListaTreniArrivo")
    if not isinstance(rows, list):
        raise UpstreamError("malformed_payload", url)
    for row in rows:
        if not isinstance(row, dict) or not re.fullmatch(r"\d{1,6}", str(row.get("Numero", ""))):
            raise UpstreamError("malformed_payload", url)
        result["trains"].append({
            "train_number": str(row["Numero"]), "destination" if kind == "departures" else "origin": _text(row.get("DescrizioneLocalita")),
            "scheduled_time": _clock(row.get("OraPassaggio")), "expected_time": _clock(row.get("NuovoOrario")),
            "delay_minutes": _minutes(row.get("Ritardo")), "platform": _text(row.get("Binario")),
            "information": _text(row.get("Informazioni")),
        })
    return result
