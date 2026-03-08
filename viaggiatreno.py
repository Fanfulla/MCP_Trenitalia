"""
Client asincrono per le API non ufficiali di Viaggiatreno (Trenitalia).
Gestisce tutte le chiamate HTTP con timeout, retry e defensive parsing.
"""

from typing import Any, Optional
import httpx

# ─── Costanti ────────────────────────────────────────────────────────────────

BASE_URL = "http://www.viaggiatreno.it/infomobilita/resteasy/viaggiatreno"
TIMEOUT_SECONDS = 10.0
HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; trenitalia-mcp/1.0)",
    "Accept": "application/json",
}


# ─── Client HTTP condiviso ────────────────────────────────────────────────────

def _make_client() -> httpx.AsyncClient:
    """Crea un client httpx configurato con timeout e headers standard."""
    return httpx.AsyncClient(
        timeout=httpx.Timeout(TIMEOUT_SECONDS),
        headers=HEADERS,
        follow_redirects=True,
    )


# ─── Helper: safe cast ────────────────────────────────────────────────────────

def _safe_int(value: Any, default: int = 0) -> int:
    """Converte in int in modo sicuro — Viaggiatreno a volte restituisce stringhe."""
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _safe_str(value: Any, default: str = "") -> str:
    """Normalizza un valore in stringa."""
    if value is None:
        return default
    return str(value).strip()


# ─── Funzioni API ─────────────────────────────────────────────────────────────

async def cerca_stazione(query: str) -> list[dict]:
    """
    Autocomplete: cerca stazioni per nome parziale.
    Endpoint: /cercaStazione/{query}
    Restituisce lista di dizionari {nomeLungo, id}.
    """
    url = f"{BASE_URL}/cercaStazione/{query.strip()}"
    async with _make_client() as client:
        response = await client.get(url)
        response.raise_for_status()
        raw = response.text.strip()
        risultati = []

        # Prova prima il formato JSON (array di oggetti)
        try:
            data = response.json()
            if isinstance(data, list):
                for item in data:
                    nome = _safe_str(item.get("nomeLungo") or item.get("nome"))
                    id_st = _safe_str(item.get("id"))
                    if nome and id_st:
                        risultati.append({"nome": nome.title(), "id": id_st})
                return risultati
        except Exception:
            pass

        # Fallback: formato testo pipe-separated "NOME STAZIONE|S00000\n..."
        for riga in raw.splitlines():
            riga = riga.strip()
            if "|" in riga:
                nome, id_stazione = riga.split("|", 1)
                risultati.append({
                    "nome": nome.strip().title(),
                    "id": id_stazione.strip(),
                })
        return risultati


async def get_partenze(id_stazione: str, orario: str) -> list[dict]:
    """
    Recupera le partenze da una stazione in un dato orario.
    Endpoint: /partenze/{id_stazione}/{orario}
    Formato orario atteso: 'Wed Dec 04 2024 10%3A30%3A00 GMT%2B0100'
    In pratica passiamo il timestamp URL-encoded oppure usiamo datetime ora.
    """
    url = f"{BASE_URL}/partenze/{id_stazione}/{orario}"
    async with _make_client() as client:
        response = await client.get(url)
        response.raise_for_status()
        data = response.json()
        return data if isinstance(data, list) else []


async def get_andamento_treno(id_stazione_origine: str, numero_treno: str) -> dict:
    """
    Recupera la telemetria in tempo reale di un treno.
    Endpoint: /andamentoTreno/{id_stazione_origine}/{numero_treno}
    """
    url = f"{BASE_URL}/andamentoTreno/{id_stazione_origine}/{numero_treno}"
    async with _make_client() as client:
        response = await client.get(url)
        response.raise_for_status()
        data = response.json()
        return data if isinstance(data, dict) else {}


async def get_arrivi(id_stazione: str, orario: str) -> list[dict]:
    """
    Recupera gli arrivi a una stazione in un dato orario.
    Endpoint: /arrivi/{id_stazione}/{orario}
    """
    url = f"{BASE_URL}/arrivi/{id_stazione}/{orario}"
    async with _make_client() as client:
        response = await client.get(url)
        response.raise_for_status()
        data = response.json()
        return data if isinstance(data, list) else []