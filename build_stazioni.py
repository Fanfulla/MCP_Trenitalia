#!/usr/bin/env python3
"""
Script one-shot: aggiorna data/stazioni.json (nome stazione NeTEx → ID Viaggiatreno).

Legge le stazioni dall'orario Trenitalia locale (data/timetable.json.gz, creato da
update_data.py) e risolve l'ID Viaggiatreno tramite cercaStazione. L'ID NeTEx contiene
un codice numerico che spesso coincide con l'ID Viaggiatreno: viene preferito solo se
Viaggiatreno restituisce una stazione con quel codice e un nome compatibile. Le voci
esistenti che non si possono verificare restano invariate.

Uso: python build_stazioni.py
"""

from __future__ import annotations

import asyncio
import json
import re
import sys
from pathlib import Path

from http_client import close_clients
from timetable import load_timetable, station_key
from viaggiatreno import cerca_stazione

DATA_DIR = Path(__file__).parent / "data"
TIMETABLE_FILE = DATA_DIR / "timetable.json.gz"
OUT_FILE = DATA_DIR / "stazioni.json"
DELAY = 0.15  # secondi tra chiamate per non sovraccaricare l'API

STAZIONI_EXTRA = {"BOLOGNA C.LE AV": "S05046"}


def netex_code(station_id: str) -> str | None:
    match = re.search(r":83\d{2}(\d{5})$", station_id)
    return f"S{match.group(1)}" if match else None


def compatibili(nome_netex: str, nome_viaggiatreno: str) -> bool:
    a, b = station_key(nome_netex), station_key(nome_viaggiatreno)
    return bool(a and b) and (a == b or f" {a} " in f" {b} " or f" {b} " in f" {a} ")


def varianti(nome: str) -> list[str]:
    parole = nome.split()
    risultato = []
    for fine in range(len(parole), 0, -1):
        query = " ".join(parole[:fine])
        if len(query) >= 3 and query not in risultato:
            risultato.append(query)
    return risultato


def find_best_match(nome_query: str, risultati: list[dict]) -> str | None:
    """
    Trova l'ID migliore tra i risultati:
    1. Match esatto (case-insensitive)
    2. Primo risultato se c'è un solo risultato
    3. Primo risultato il cui nome contiene il nome query come substring
    """
    q = nome_query.strip().lower()

    for r in risultati:
        if r["nome"].lower() == q:
            return r["id"]

    if len(risultati) == 1:
        return risultati[0]["id"]

    for r in risultati:
        if q in r["nome"].lower() or r["nome"].lower() in q:
            return r["id"]

    return None


async def _cerca(query: str) -> list[dict]:
    try:
        return await cerca_stazione(query)
    except Exception:
        return []
    finally:
        await asyncio.sleep(DELAY)


async def risolvi(nome: str, codice: str | None) -> tuple[str | None, bool]:
    primi: list[dict] | None = None
    for query in varianti(nome):
        risultati = await _cerca(query)
        if primi is None:
            primi = risultati
        if codice and any(r["id"] == codice and compatibili(nome, r["nome"]) for r in risultati):
            return codice, True
        if not codice:
            break
    primi = primi or []
    scelto = find_best_match(nome, primi)
    if scelto and any(r["id"] == scelto and compatibili(nome, r["nome"]) for r in primi):
        return scelto, False
    return None, False


async def aggiorna(stazioni: list[dict], esistenti: dict[str, str]) -> tuple[dict[str, str], dict[str, list]]:
    mapping = dict(esistenti)
    report: dict[str, list] = {"aggiunte": [], "corrette": [], "non_trovate": []}
    for indice, stazione in enumerate(stazioni, 1):
        nome, codice = stazione["name"].strip(), netex_code(stazione["id"])
        chiave = nome.upper()
        attuale = esistenti.get(chiave)
        if attuale and (attuale == codice or codice is None):
            continue
        station_id, confermato = await risolvi(nome, codice)
        if station_id and attuale is None:
            mapping[chiave] = station_id
            report["aggiunte"].append((chiave, station_id))
        elif station_id and confermato and station_id != attuale:
            mapping[chiave] = station_id
            report["corrette"].append((chiave, attuale, station_id))
        elif not station_id and attuale is None:
            report["non_trovate"].append(chiave)
        print(f"  [{indice:4d}/{len(stazioni)}] {chiave:<40} {mapping.get(chiave, 'NON TROVATA')}")
    for chiave, station_id in STAZIONI_EXTRA.items():
        if chiave not in mapping:
            report["aggiunte"].append((chiave, station_id))
        elif mapping[chiave] != station_id:
            report["corrette"].append((chiave, mapping[chiave], station_id))
        mapping[chiave] = station_id
    return mapping, report


async def _main_async(stazioni: list[dict], esistenti: dict[str, str]):
    try:
        return await aggiorna(stazioni, esistenti)
    finally:
        await close_clients()


def main():
    if not TIMETABLE_FILE.exists():
        sys.exit("Orario Trenitalia assente: esegui prima python update_data.py --provider trenitalia")
    stazioni = load_timetable(TIMETABLE_FILE)["stations"]
    esistenti = json.loads(OUT_FILE.read_text(encoding="utf-8")) if OUT_FILE.exists() else {}
    print(f"{len(stazioni)} stazioni nell'orario, {len(esistenti)} nel dizionario attuale")

    mapping, report = asyncio.run(_main_async(stazioni, esistenti))

    OUT_FILE.parent.mkdir(exist_ok=True)
    with open(OUT_FILE, "w", encoding="utf-8") as f:
        json.dump(mapping, f, ensure_ascii=False, indent=2, sort_keys=True)

    print(f"\nAggiunte: {len(report['aggiunte'])}  Corrette: {len(report['corrette'])}  "
          f"Non trovate: {len(report['non_trovate'])}")
    for chiave, prima, dopo in report["corrette"]:
        print(f"  corretta {chiave}: {prima} → {dopo}")
    print(f"Salvato in {OUT_FILE} ({len(mapping)} stazioni)")


if __name__ == "__main__":
    main()
