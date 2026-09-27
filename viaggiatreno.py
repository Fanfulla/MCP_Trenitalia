"""Free public Viaggiatreno endpoints, without a supported public API contract."""

from __future__ import annotations

from datetime import date, datetime, time
import json
import re
from typing import Any
from urllib.parse import quote, unquote
from zoneinfo import ZoneInfo

from http_client import UpstreamError, get_json, get_text

# HTTPS was not reachable in live verification; this is the public site's URL.
BASE_URL = "http://www.viaggiatreno.it/infomobilita/resteasy/viaggiatreno"
ROME = ZoneInfo("Europe/Rome")


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError, OverflowError):
        return default


def _safe_str(value: Any, default: str = "") -> str:
    return default if value is None else str(value).strip()


def _path(value: str) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > 160:
        raise ValueError("A nonempty path value of at most 160 characters is required")
    return quote(value.strip(), safe="")


def _number(value: str) -> str:
    value = str(value).strip()
    if not re.fullmatch(r"\d{1,6}", value):
        raise ValueError("Train number must contain 1 to 6 digits")
    return str(int(value))


def _service_day(value: date | None) -> date:
    if value is None:
        return datetime.now(ROME).date()
    if not isinstance(value, date) or isinstance(value, datetime):
        raise ValueError("service_date must be a date")
    return value


async def cerca_stazione(query: str) -> list[dict]:
    url = f"{BASE_URL}/cercaStazione/{_path(query)}"
    text = (await get_text(url, ttl=300)).strip()
    if not text:
        return []
    try:
        data = json.loads(text)
    except ValueError:
        data = []
        for line in text.splitlines():
            name, separator, station_id = line.strip().partition("|")
            if not separator or not name or not re.fullmatch(r"S\d{5}", station_id.strip()):
                raise UpstreamError("malformed_payload", url) from None
            data.append({"nomeLungo": name, "id": station_id.strip()})
    if not isinstance(data, list):
        raise UpstreamError("malformed_payload", url)
    results = []
    for item in data:
        if not isinstance(item, dict):
            raise UpstreamError("malformed_payload", url)
        name = _safe_str(item.get("nomeLungo") or item.get("nome"))
        station_id = _safe_str(item.get("id"))
        if not name or not re.fullmatch(r"S\d{5}", station_id):
            raise UpstreamError("malformed_payload", url)
        results.append({"nome": name.title(), "id": station_id})
    return results


async def _board(kind: str, station_id: str, encoded_time: str) -> list[dict]:
    url = f"{BASE_URL}/{kind}/{_path(station_id)}/{_path(unquote(encoded_time))}"
    data = await get_json(url)
    if data is None:
        return []
    if not isinstance(data, list) or any(not isinstance(item, dict) or "numeroTreno" not in item for item in data):
        raise UpstreamError("malformed_payload", url)
    return data


async def get_partenze(id_stazione: str, orario: str) -> list[dict]:
    return await _board("partenze", id_stazione, orario)


async def get_arrivi(id_stazione: str, orario: str) -> list[dict]:
    return await _board("arrivi", id_stazione, orario)


async def get_andamento_treno(id_stazione_origine: str, numero_treno: str, service_date: date | None = None) -> dict:
    day = _service_day(service_date)
    millis = int(datetime.combine(day, time.min, ROME).timestamp() * 1000)
    url = f"{BASE_URL}/andamentoTreno/{_path(id_stazione_origine)}/{_number(numero_treno)}/{millis}"
    data = await get_json(url)
    if data is None or data == {}:
        return {}
    if not isinstance(data, dict) or "numeroTreno" not in data:
        raise UpstreamError("malformed_payload", url)
    reported_date = data.get("dataPartenza")
    if not isinstance(reported_date, str):
        raise UpstreamError("date_unverified", url)
    try:
        reported_day = date.fromisoformat(reported_date[:10])
    except ValueError:
        raise UpstreamError("malformed_payload", url) from None
    if reported_day != day:
        raise UpstreamError("date_mismatch", url)
    if str(data["numeroTreno"]).lstrip("0") != _number(numero_treno):
        raise UpstreamError("malformed_payload", url)
    return data


async def lookup_train(number: str, service_date: date | None = None) -> dict:
    """Resolve exact number and service day before requesting raw live status."""
    number, day = _number(number), _service_day(service_date)
    url = f"{BASE_URL}/cercaNumeroTrenoTrenoAutocomplete/{number}"
    text = (await get_text(url)).strip()
    candidates = {}
    for line in text.splitlines():
        label, separator, key = line.partition("|")
        match = re.fullmatch(r"(\d+)-(S\d{5})-(\d+)", key.strip())
        if not separator or not match:
            raise UpstreamError("malformed_payload", url)
        train_number, origin, millis = match.groups()
        try:
            candidate_day = datetime.fromtimestamp(int(millis) / 1000, ROME).date()
        except (ValueError, OverflowError, OSError):
            raise UpstreamError("malformed_payload", url) from None
        if str(int(train_number)) == number and candidate_day == day:
            candidates[(origin, millis)] = {"number": number, "origin_id": origin, "service_date": day.isoformat(), "label": label.strip()}
    if len(candidates) > 1:
        raise UpstreamError("ambiguous", url, candidates=list(candidates.values()))
    if not candidates:
        return {}
    origin, _ = next(iter(candidates))
    return await get_andamento_treno(origin, number, day)
