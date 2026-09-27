#!/usr/bin/env python3
"""
Controllo gratuito delle fonti: validità degli orari NeTEx locali e API live non
documentate di Viaggiatreno e Italo, interrogate con gli stessi parser del server.

Uso: python check_sources.py [--min-days 21] [--retry-delay 60]
Esce con codice 1 se una fonte live non risponde o cambia formato, oppure se un
orario locale manca o è scaduto. Un orario vicino alla scadenza è solo un avviso.
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
import time
from datetime import date
from pathlib import Path

from http_client import close_clients
from italo import get_station_board, get_train_status
from rail_service import RailService
from time_utils import format_viaggiatreno_time, now_rome
from viaggiatreno import cerca_stazione, get_andamento_treno, get_partenze

DATA_DIR = Path(__file__).resolve().parent / "data"
ROMA_TERMINI = "S08409"
TENTATIVI_TRENO = 3


def controlla_orari(servizio: RailService, oggi: date, min_giorni: int) -> tuple[list[str], list[str]]:
    errori, avvisi = [], []
    for provider, info in servizio.sources(oggi).items():
        if info.get("status") != "available":
            errori.append(f"Orario {provider}: {info.get('status')} per il {oggi.isoformat()}")
            continue
        restano = (date.fromisoformat(info["valid_to"]) - oggi).days
        if restano < min_giorni:
            avvisi.append(f"Orario {provider}: valido fino al {info['valid_to']} (restano {restano} giorni)")
    return errori, avvisi


async def controlla_viaggiatreno() -> str:
    stazioni = await cerca_stazione("ROMA TERMINI")
    if not any(s["id"] == ROMA_TERMINI for s in stazioni):
        raise RuntimeError(f"cercaStazione non restituisce più Roma Termini ({ROMA_TERMINI})")
    treni = await get_partenze(ROMA_TERMINI, format_viaggiatreno_time())
    candidati = [t for t in treni if t.get("codOrigine") == ROMA_TERMINI][:TENTATIVI_TRENO]
    if not candidati:
        raise RuntimeError(f"bacheca partenze di Roma Termini senza treni in origine ({len(treni)} righe)")
    for treno in candidati:
        dati = await get_andamento_treno(ROMA_TERMINI, str(treno["numeroTreno"]))
        if isinstance(dati.get("fermate"), list) and dati["fermate"]:
            return f"Viaggiatreno: {len(treni)} partenze da Roma Termini, treno {treno['numeroTreno']} con {len(dati['fermate'])} fermate"
    raise RuntimeError("andamentoTreno non restituisce fermate per i treni in partenza da Roma Termini")


async def controlla_italo() -> str:
    tabellone = await get_station_board("Roma Termini")
    treni = tabellone.get("trains") or []
    if tabellone.get("status") != "ok" or not treni:
        raise RuntimeError(f"tabellone Italo di Roma Termini: stato {tabellone.get('status')}, {len(treni)} treni")
    for treno in treni[:TENTATIVI_TRENO]:
        stato = await get_train_status(treno["train_number"])
        if stato.get("stops"):
            return f"Italo: {len(treni)} partenze da Roma Termini, treno {treno['train_number']} con {len(stato['stops'])} fermate"
    raise RuntimeError("RicercaTrenoService non restituisce fermate per i treni del tabellone di Roma Termini")


async def controlli_live() -> list[tuple[str, bool, str]]:
    risultati = []
    try:
        for nome, controllo in (("Viaggiatreno", controlla_viaggiatreno), ("Italo", controlla_italo)):
            try:
                risultati.append((nome, True, await controllo()))
            except Exception as exc:
                dettaglio = getattr(exc, "code", None) or str(exc) or type(exc).__name__
                risultati.append((nome, False, f"{nome}: {type(exc).__name__}: {dettaglio}"))
    finally:
        await close_clients()
    return risultati


def _annotazione(livello: str, messaggio: str) -> None:
    if os.getenv("GITHUB_ACTIONS") == "true":
        print(f"::{livello}::{messaggio}")


def _riepilogo(righe: list[str]) -> None:
    percorso = os.getenv("GITHUB_STEP_SUMMARY")
    if percorso:
        with open(percorso, "a", encoding="utf-8") as f:
            f.write("## Controllo fonti\n\n" + "\n".join(f"- {riga}" for riga in righe) + "\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Controllo delle fonti orari e live.")
    parser.add_argument("--min-days", type=int, default=21, help="giorni minimi di validità residua prima dell'avviso")
    parser.add_argument("--retry-delay", type=float, default=60, help="secondi prima di ripetere i controlli live falliti")
    args = parser.parse_args(argv)

    oggi = now_rome().date()
    errori, avvisi = controlla_orari(RailService(DATA_DIR), oggi, args.min_days)
    risultati = asyncio.run(controlli_live())
    if not all(ok for _, ok, _ in risultati) and args.retry_delay > 0:
        print(f"Controlli live falliti, nuovo tentativo tra {args.retry_delay:.0f} s")
        time.sleep(args.retry_delay)
        risultati = asyncio.run(controlli_live())

    righe = []
    for _, ok, messaggio in risultati:
        if ok:
            righe.append(f"OK {messaggio}")
        else:
            errori.append(messaggio)
    for messaggio in avvisi:
        _annotazione("warning", messaggio)
        righe.append(f"AVVISO {messaggio}")
    for messaggio in errori:
        _annotazione("error", messaggio)
        righe.append(f"ERRORE {messaggio}")
    print("\n".join(righe))
    _riepilogo(righe)
    return 1 if errori else 0


if __name__ == "__main__":
    sys.exit(main())
