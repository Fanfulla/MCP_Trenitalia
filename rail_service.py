"""Provider-neutral, date-aware railway queries using free public sources."""

from __future__ import annotations

import asyncio
from datetime import date, datetime
from pathlib import Path
from typing import Any

from italo import get_train_status
from timetable import coverage_status, journeys_between, load_timetable, search_stations
from time_utils import now_rome, timestamp_to_iso
from viaggiatreno import lookup_train

PROVIDERS = ("trenitalia", "italo")
SOURCE_URLS = {
    "trenitalia": "https://www.cciss.it/nap/mmtis/public/catalog/Asset/1080596",
    "italo": "https://www.cciss.it/nap/mmtis/public/catalog/Asset/1814124",
}
LIVE_URLS = {
    "trenitalia": "http://www.viaggiatreno.it/",
    "italo": "https://italoinviaggio.italotreno.com/",
}
BOOKING_URLS = {
    "trenitalia": "https://www.trenitalia.com/it.html",
    "italo": "https://www.italotreno.com/it",
}


def optional_int(value: Any) -> int | None:
    if value is None or isinstance(value, bool) or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError, OverflowError):
        return None


def normalize_trenitalia_status(raw: dict, service_date: date) -> dict:
    """Retain source timestamps and unknown values without inventing telemetry."""
    last_seen = timestamp_to_iso(raw.get("oraUltimoRilevamento"))
    return {
        "provider": "trenitalia", "train_number": str(raw.get("numeroTreno", "")),
        "service_date": service_date.isoformat(), "status": "available" if raw else "not_found",
        "source_url": LIVE_URLS["trenitalia"], "observed_at": now_rome().isoformat(),
        "source_updated_at": last_seen, "delay_minutes": optional_int(raw.get("ritardo")),
        "origin": raw.get("origine"), "destination": raw.get("destinazione"),
        "last_reported_station": raw.get("stazioneUltimoRilevamento"),
        "arrived": raw.get("arrivato"), "not_departed": raw.get("nonPartito"),
        "disruptions": raw.get("anormalita"), "cancelled_stops": raw.get("fermateSoppresse"),
        "stops": [{
            "name": stop.get("stazione"), "id": stop.get("id"),
            "scheduled_arrival": timestamp_to_iso(stop.get("arrivo_teorico")),
            "scheduled_departure": timestamp_to_iso(stop.get("partenza_teorica")),
            "actual_arrival": timestamp_to_iso(stop.get("arrivoReale")),
            "actual_departure": timestamp_to_iso(stop.get("partenzaReale")),
            "delay_minutes": optional_int(stop.get("ritardo")),
            "arrival_platform": stop.get("binarioEffettivoArrivo") or stop.get("binarioProgrammatoArrivo"),
            "departure_platform": stop.get("binarioEffettivoPartenza") or stop.get("binarioProgrammatoPartenza"),
            "cancelled": stop.get("soppressa"),
        } for stop in raw.get("fermate", []) if isinstance(stop, dict)],
    }


class RailService:
    def __init__(self, data_dir: Path, *, datasets: dict | None = None,
                 viaggiatreno_stations: dict[str, str] | None = None):
        self.data_dir = data_dir
        self._overrides = datasets
        self._loaded: dict[str, tuple[tuple[int, int], dict]] = {}
        self.viaggiatreno_stations = viaggiatreno_stations or {}

    def _dataset(self, provider: str) -> tuple[dict, str | None]:
        if self._overrides is not None:
            data = self._overrides.get(provider)
            return (data, None) if data else ({}, "missing")
        filename = "timetable.json.gz" if provider == "trenitalia" else "timetable_italo.json.gz"
        path = self.data_dir / filename
        try:
            stat = path.stat()
            stamp = (stat.st_mtime_ns, stat.st_size)
            cached = self._loaded.get(provider)
            if cached and cached[0] == stamp:
                return cached[1], None
            data = load_timetable(path)
            if data.get("provider") != provider:
                raise ValueError("Provider mismatch")
            self._loaded[provider] = (stamp, data)
            return data, None
        except FileNotFoundError:
            return {}, "missing"
        except (ValueError, OSError, EOFError, TypeError, KeyError):
            return {}, "invalid"

    @staticmethod
    def _providers(provider: str) -> tuple[str, ...]:
        if provider == "all":
            return PROVIDERS
        if provider not in PROVIDERS:
            raise ValueError("Operatore non valido: trenitalia, italo oppure all.")
        return (provider,)

    def sources(self, on_date: date | None = None) -> dict:
        requested = on_date or now_rome().date()
        result = {}
        for provider in PROVIDERS:
            payload, error = self._dataset(provider)
            result[provider] = {**payload.get("metadata", {}),
                "status": error or coverage_status(payload, requested),
                "catalog_url": SOURCE_URLS[provider]}
        return result

    def _station_matches(self, data: dict, reference: str, provider: str) -> list[dict]:
        query = reference.strip()
        stations = data.get("stations", [])
        by_id = [s for s in stations if s["id"] == query]
        if by_id:
            return by_id
        if provider == "trenitalia" and query.upper().startswith("S") and query[1:].isdigit():
            names = [name for name, sid in self.viaggiatreno_stations.items() if sid == query.upper()]
            if not names:
                return []
            query = names[0]
        exact = [s for s in stations if s["name"].casefold() == query.casefold()]
        if exact:
            return exact
        return search_stations(data, query)

    def stations(self, query: str, provider: str = "all", limit: int = 20) -> dict:
        matches = []
        sources = self.sources()
        for name in self._providers(provider):
            data, error = self._dataset(name)
            if error:
                continue
            for station in self._station_matches(data, query, name):
                matches.append({**station, "provider": name,
                    "viaggiatreno_id": self.viaggiatreno_stations.get(station["name"].upper()) if name == "trenitalia" else None})
        return {"status": "ok" if matches else "no_results", "stations": matches[:limit],
                "truncated": len(matches) > limit, "sources": sources}

    async def search_journeys(self, origin: str, destination: str, on_date: str | None = None,
                              after: str | None = None, provider: str = "all", limit: int = 10) -> dict:
        today = now_rome().date()
        requested = date.fromisoformat(on_date) if on_date else today
        after = after or (now_rome().strftime("%H:%M") if requested == today else "00:00")
        selected = self._providers(provider)
        sources = {p: s for p, s in self.sources(requested).items() if p in selected}
        results, warnings, choices = [], [], []
        available = 0
        for name in selected:
            data, error = self._dataset(name)
            if error or sources[name]["status"] != "available":
                warnings.append(f"{name}: orario {sources[name]['status']} per {requested.isoformat()}.")
                continue
            available += 1
            start = self._station_matches(data, origin, name)
            end = self._station_matches(data, destination, name)
            if len(start) > 1 or len(end) > 1:
                choices.extend([{**s, "provider": name, "field": field}
                    for field, values in (("origin", start), ("destination", end))
                    if len(values) > 1 for s in values[:20]])
                continue
            if not start or not end:
                warnings.append(f"{name}: stazione non presente nell'orario; specifica un nome o ID del provider.")
                continue
            for item in journeys_between(data, start[0]["id"], end[0]["id"], requested, after):
                results.append({**item, "provider": name, "data_type": "scheduled",
                    "source_url": sources[name].get("source_url") or SOURCE_URLS[name],
                    "price": None, "price_status": "unavailable", "booking_url": BOOKING_URLS[name],
                    "live": {"status": "not_applicable", "delay_minutes": None}})
        results.sort(key=lambda item: datetime.fromisoformat(item["departure"]).timestamp())
        truncated = len(results) > limit
        results = results[:limit]

        async def enrich(item: dict) -> None:
            # Scheduled data for another service day must never receive today's delay.
            if requested != today or item.get("service_date") != today.isoformat():
                return
            number = item["train_number"]
            if not number.isdigit():
                item["live"]["status"] = "unsupported_train_identifier"
                return
            try:
                if item["provider"] == "trenitalia":
                    raw = await lookup_train(number, service_date=today)
                    live = normalize_trenitalia_status(raw, today)
                else:
                    live = await get_train_status(number)
                    if live.get("service_date") != today.isoformat():
                        item["live"] = {"status": "date_unverified", "delay_minutes": None,
                            "source_url": LIVE_URLS["italo"], "observed_at": live.get("observed_at")}
                        return
                item["live"] = live
            except Exception as exc:
                item["live"] = {"status": "unavailable", "delay_minutes": None,
                                "error_code": getattr(exc, "code", "upstream_unavailable"),
                                "source_url": LIVE_URLS[item["provider"]]}

        await asyncio.gather(*(enrich(item) for item in results))
        status = "ok" if results else "no_results"
        if not available:
            status = "unavailable"
        elif choices:
            status = "partial" if results else "ambiguous"
        elif results and warnings:
            status = "partial"
        return {"status": status, "date": requested.isoformat(), "after": after,
                "timezone": "Europe/Rome", "journeys": results, "sources": sources,
                "warnings": warnings, "choices": choices, "truncated": truncated,
                "observed_at": now_rome().isoformat(), "direct_services_only": True}

    async def train_status(self, provider: str, number: str) -> dict:
        self._providers(provider)
        if provider == "all":
            raise ValueError("Specifica l'operatore del treno.")
        try:
            if provider == "italo":
                return await get_train_status(number)
            day = now_rome().date()
            return normalize_trenitalia_status(await lookup_train(number, service_date=day), day)
        except Exception as exc:
            return {"status": "unavailable", "provider": provider, "train_number": number,
                    "delay_minutes": None, "source_url": LIVE_URLS[provider],
                    "error_code": getattr(exc, "code", "upstream_unavailable"),
                    "observed_at": now_rome().isoformat()}

    def ticket_links(self, origin: str, destination: str, on_date: str) -> dict:
        return {"status": "prices_unavailable", "origin": origin, "destination": destination,
                "date": on_date, "message": "Nessuna fonte gratuita di tariffe live verificata. Cerca prezzi e disponibilità sui siti ufficiali.",
                "operators": [{"provider": p, "url": url, "price": None,
                               "search_prefilled": False} for p, url in BOOKING_URLS.items()]}
