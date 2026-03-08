#!/usr/bin/env python3
"""
Script one-shot: costruisce data/stazioni.json
Legge i nomi ufficiali dal NeTEx, risolve l'ID Viaggiatreno per ciascuno
tramite cercaStazione, salva il dizionario nome→ID.

Uso: python build_stazioni.py
"""

import asyncio
import gzip
import json
import xml.etree.ElementTree as ET
from pathlib import Path

import httpx

NS = "http://www.netex.org.uk/netex"
NETEX_FILE = "IT-IT-TRENITALIA_L1.xml.gz"
OUT_FILE = Path("data/stazioni.json")
BASE_URL = "http://www.viaggiatreno.it/infomobilita/resteasy/viaggiatreno"
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; trenitalia-mcp/1.0)"}
DELAY = 0.15  # secondi tra chiamate per non sovraccaricare l'API


def load_netex_names() -> list[tuple[str, str]]:
    """Restituisce lista di (nome_ufficiale, private_code) per le stazioni rail."""
    print(f"Lettura {NETEX_FILE}...")
    with gzip.open(NETEX_FILE, "rb") as f:
        tree = ET.parse(f)
    root = tree.getroot()

    stazioni = []
    for sp in root.findall(f".//{{{NS}}}StopPlace"):
        tm = sp.find(f"{{{NS}}}TransportMode")
        # Includi rail e other (le grandi stazioni come Roma Termini e Milano Centrale
        # sono classificate "other" nel NeTEx). Escludi solo bus.
        if tm is not None and tm.text == "bus":
            continue
        name_el = sp.find(f"{{{NS}}}Name")
        pc_el = sp.find(f"{{{NS}}}PrivateCode")
        if name_el is not None and name_el.text:
            nome = name_el.text.strip()
            pc = pc_el.text.strip() if pc_el is not None else ""
            stazioni.append((nome, pc))

    print(f"  {len(stazioni)} stazioni ferroviarie trovate nel NeTEx")
    return stazioni


async def cerca_stazione_raw(client: httpx.AsyncClient, query: str) -> list[dict]:
    url = f"{BASE_URL}/cercaStazione/{query.strip()}"
    try:
        r = await client.get(url, timeout=10.0)
        r.raise_for_status()
        raw = r.text.strip()

        # Prova JSON
        try:
            data = r.json()
            if isinstance(data, list):
                risultati = []
                for item in data:
                    nome = str(item.get("nomeLungo") or item.get("nome") or "").strip()
                    id_st = str(item.get("id") or "").strip()
                    if nome and id_st:
                        risultati.append({"nome": nome.title(), "id": id_st})
                return risultati
        except Exception:
            pass

        # Fallback pipe-separated
        risultati = []
        for riga in raw.splitlines():
            riga = riga.strip()
            if "|" in riga:
                nome, id_st = riga.split("|", 1)
                risultati.append({"nome": nome.strip().title(), "id": id_st.strip()})
        return risultati

    except Exception as e:
        return []


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


async def build_mapping(stazioni: list[tuple[str, str]]) -> dict[str, str]:
    mapping: dict[str, str] = {}
    non_trovate: list[str] = []

    async with httpx.AsyncClient(headers=HEADERS, follow_redirects=True) as client:
        for i, (nome, _pc) in enumerate(stazioni):
            risultati = await cerca_stazione_raw(client, nome)
            station_id = find_best_match(nome, risultati)

            if station_id:
                mapping[nome.upper()] = station_id
                status = f"OK → {station_id}"
            else:
                non_trovate.append(nome)
                status = "NON TROVATA"

            print(f"  [{i+1:3d}/{len(stazioni)}] {nome:<35} {status}")
            await asyncio.sleep(DELAY)

    print(f"\n✓ Risolte: {len(mapping)}/{len(stazioni)}")
    if non_trovate:
        print(f"✗ Non trovate ({len(non_trovate)}):")
        for n in non_trovate:
            print(f"    - {n}")

    return mapping


def main():
    stazioni = load_netex_names()

    print("\nRisoluzione ID Viaggiatreno...")
    mapping = asyncio.run(build_mapping(stazioni))

    OUT_FILE.parent.mkdir(exist_ok=True)
    with open(OUT_FILE, "w", encoding="utf-8") as f:
        json.dump(mapping, f, ensure_ascii=False, indent=2, sort_keys=True)

    print(f"\nSalvato in {OUT_FILE} ({len(mapping)} stazioni)")


if __name__ == "__main__":
    main()
