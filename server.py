#!/usr/bin/env python3
"""
Trenitalia MCP Server — server MCP per dati ferroviari in tempo reale.

Fornisce strumenti per:
- Cercare stazioni per nome e ottenerne l'ID Viaggiatreno
- Monitorare partenze e arrivi in una stazione
- Tracciare la posizione e il ritardo di un treno specifico

Sorgente dati: API non ufficiale Viaggiatreno (infomobilita.trenitalia.com)
Trasporto: stdio (default) oppure Streamable HTTP e SSE legacy (per deploy remoto)
"""

from __future__ import annotations

import json
from datetime import date, datetime
from pathlib import Path
from typing import Any

import httpx
from mcp.server import MCPServer
from mcp_types import ToolAnnotations
from http_client import UpstreamError, close_clients
from rail_service import RailService
from time_utils import ROME, now_rome, format_viaggiatreno_time
from timetable import station_key
from italo import get_station_board

from models import (
    CercaStazioneInput,
    MonitoraArriviInput,
    MonitoraPartenzeInput,
    TracciaTrenoInput,
)
from viaggiatreno import (
    _safe_int,
    _safe_str,
    cerca_stazione,
    get_andamento_treno,
    get_arrivi,
    get_partenze,
)

# ─── Dizionario locale stazioni ───────────────────────────────────────────────

_STAZIONI_FILE = Path(__file__).parent / "data" / "stazioni.json"

def _load_stazioni() -> dict[str, str]:
    """Carica il dizionario nome_stazione.upper() → ID Viaggiatreno da file JSON."""
    if _STAZIONI_FILE.exists():
        with open(_STAZIONI_FILE, encoding="utf-8") as f:
            return json.load(f)
    return {}

_STAZIONI: dict[str, str] = _load_stazioni()


def _cerca_locale(query: str) -> list[dict]:
    """
    Ricerca fuzzy sul dizionario locale (data/stazioni.json).
    Restituisce lista di {nome, id} con i match migliori.
    Strategia: exact → startswith → substring (tutte case-insensitive), poi nome
    normalizzato (es. 'Bologna Centrale' ↔ 'BOLOGNA C.LE').
    """
    q = query.strip().upper()
    chiave = station_key(query)
    esatti = []
    iniziano = []
    contengono = []
    simili = []

    for nome, sid in _STAZIONI.items():
        nome_up = nome.upper()
        if nome_up == q:
            esatti.append({"nome": nome.title(), "id": sid})
        elif nome_up.startswith(q):
            iniziano.append({"nome": nome.title(), "id": sid})
        elif q in nome_up:
            contengono.append({"nome": nome.title(), "id": sid})
        elif chiave and f" {chiave} " in f" {station_key(nome)} ":
            simili.append({"nome": nome.title(), "id": sid})

    return esatti + iniziano + contengono + simili


async def _resolve_stazione(ref: str) -> tuple[str, str] | str:
    """
    Risolve un riferimento stazione (nome in chiaro o ID) all'ID Viaggiatreno.

    Restituisce:
    - (id, nome_display)  se risolto univocamente
    - str                 messaggio di errore/disambiguazione da restituire all'utente

    Logica:
    - Se sembra già un ID (inizia con 'S' e ha solo cifre dopo) → restituisce direttamente
    - Altrimenti cerca nel dizionario locale con fuzzy match, poi su Viaggiatreno
      - 1 risultato → risolto
      - >1 risultati → chiede disambiguazione all'utente
      - 0 risultati → messaggio di errore
    """
    v = ref.strip()

    # Già un ID Viaggiatreno
    if v.upper().startswith("S") and v[1:].isdigit():
        return (v.upper(), next((name.title() for name, sid in _STAZIONI.items() if sid == v.upper()), v.upper()))

    risultati = _cerca_locale(v)
    if not risultati:
        try:
            risultati = await cerca_stazione(v)
        except (UpstreamError, ValueError):
            risultati = []
    chiave = station_key(v)
    esatti = [r for r in risultati if r["nome"].casefold() == v.casefold()] or [
        r for r in risultati if chiave and station_key(r["nome"]) == chiave]
    if esatti:
        risultati = esatti

    if len(risultati) == 1:
        return (risultati[0]["id"], risultati[0]["nome"])

    if len(risultati) > 1:
        opzioni = "\n".join(f"- **{r['nome']}** → `{r['id']}`" for r in risultati[:10])
        return (
            f"Il nome '{v}' corrisponde a più stazioni. Specifica quale:\n{opzioni}"
        )

    return (
        f"Stazione '{v}' non trovata nel dizionario locale né su Viaggiatreno. "
        "Usa il tool `trenitalia_cerca_stazione` per cercarla per nome."
    )


rail = RailService(Path(__file__).parent / "data", viaggiatreno_stations=_STAZIONI)


# ─── Inizializzazione ─────────────────────────────────────────────────────────

mcp = MCPServer(
    "trenitalia_mcp",
    version="0.2.0",
    instructions=(
        "Orari e stato dei treni Trenitalia e Italo da fonti pubbliche gratuite. "
        "Usa ciuff_cerca_viaggi per confrontare collegamenti diretti e ciuff_stato_fonti per la copertura. "
        "Le tariffe live non sono disponibili; ciuff_link_biglietti restituisce solo siti ufficiali. "
        "Flusso d'uso consigliato: 1) usa trenitalia_cerca_stazione per trovare l'ID stazione, "
        "2) usa trenitalia_monitora_partenze o trenitalia_monitora_arrivi per la bacheca, "
        "3) usa trenitalia_traccia_treno per dettagli su un singolo convoglio."
    ),
)


# ─── Utility di formattazione ─────────────────────────────────────────────────

def _orario_viaggiatreno() -> str:
    return format_viaggiatreno_time()


def _format_ritardo(ritardo: Any) -> str:
    """Converte il valore ritardo (int, str o None) in testo leggibile."""
    minuti = _safe_int(ritardo, default=-99)
    if minuti == -99:
        return "dato non disponibile"
    if minuti == 0:
        return "in orario"
    if minuti > 0:
        return f"{minuti} min di ritardo"
    return f"{abs(minuti)} min di anticipo"


def _format_binario(binario_programmato: Any, binario_effettivo: Any) -> str:
    """Mostra binario effettivo vs programmato se diversi."""
    prog = _safe_str(binario_programmato)
    eff = _safe_str(binario_effettivo)
    if not eff and not prog:
        return "non assegnato"
    if not eff:
        return f"bin. {prog}"
    if eff != prog and prog:
        return f"bin. {eff} (programmato: {prog})"
    return f"bin. {eff}"


_MESSAGGI_FONTE = {
    "unavailable": "i sistemi Viaggiatreno non rispondono o sono temporaneamente non disponibili. Riprova tra qualche istante.",
    "malformed_payload": "Viaggiatreno ha restituito una risposta in un formato inatteso. Riprova più tardi.",
    "response_too_large": "la risposta di Viaggiatreno supera il limite di dimensione consentito.",
    "date_mismatch": "Viaggiatreno non riporta questo treno in circolazione oggi dalla stazione di origine indicata. Verifica numero treno e stazione di origine.",
    "date_unverified": "Viaggiatreno non indica la data di circolazione del treno, quindi il dato non è verificabile.",
    "ambiguous": "più treni corrispondono al numero indicato. Specifica la stazione di origine.",
}


def _handle_error(e: Exception, contesto: str = "") -> str:
    """Converte eccezioni di rete e della fonte dati in messaggi testuali per l'LLM."""
    prefisso = f"[{contesto}] " if contesto else ""
    if isinstance(e, UpstreamError):
        dettaglio = _MESSAGGI_FONTE.get(e.code, f"la fonte dati ha restituito un errore ({e.code}).")
        return f"{prefisso}Errore: {dettaglio}"
    if isinstance(e, ValueError):
        return f"{prefisso}Errore: parametro non valido ({e})."
    if isinstance(e, httpx.TimeoutException):
        return f"{prefisso}Errore: i sistemi telemetrici Viaggiatreno sono irraggiungibili (timeout). Riprova tra qualche istante."
    if isinstance(e, httpx.HTTPStatusError):
        code = e.response.status_code
        if code == 404:
            return f"{prefisso}Errore: risorsa non trovata (404). Verifica che l'ID stazione o il numero treno siano corretti."
        if code == 500:
            return f"{prefisso}Errore: server Viaggiatreno non disponibile (500). Riprova più tardi."
        return f"{prefisso}Errore HTTP {code} da Viaggiatreno."
    if isinstance(e, httpx.ConnectError):
        return f"{prefisso}Errore: impossibile connettersi a Viaggiatreno. Verifica la connessione di rete."
    return f"{prefisso}Errore imprevisto ({type(e).__name__}): {e}"


# ─── Tool 1: Cerca stazione ───────────────────────────────────────────────────

@mcp.tool(
    name="trenitalia_cerca_stazione",
    annotations=ToolAnnotations(**{
        "title": "Cerca Stazione Trenitalia",
        "read_only_hint": True,
        "destructive_hint": False,
        "idempotent_hint": True,
        "open_world_hint": True,
    }),
)
async def trenitalia_cerca_stazione(params: CercaStazioneInput) -> str:
    """Cerca stazioni ferroviarie italiane per nome e restituisce il loro ID Viaggiatreno.

    Questo strumento deve essere usato PRIMA degli altri quando l'utente non conosce
    l'ID numerico della stazione (es. 'S01700' per Milano C.le). Supporta ricerca
    parziale (es. 'Milano' restituisce tutte le stazioni milanesi).

    Args:
        params (CercaStazioneInput): Input contenente:
            - nome_stazione (str): Nome parziale o completo della stazione (es. 'Roma', 'Napoli C')

    Returns:
        str: Lista markdown delle stazioni trovate con ID, oppure messaggio di errore.

        Formato di successo:
        ## Stazioni trovate per "query"
        - **Nome Stazione** → ID: `S00000`

        Formato errore:
        "Errore: <descrizione>"

    Esempi d'uso:
        - "Cerca la stazione di Bologna" → nome_stazione="Bologna"
        - "Qual è l'ID di Firenze SMN?" → nome_stazione="Firenze"
        - Prima di monitorare partenze da Venezia → nome_stazione="Venezia"
    """
    try:
        # 1. Ricerca nel dizionario locale (offline, istantanea)
        risultati = _cerca_locale(params.nome_stazione)

        # 2. Se il dizionario locale non trova nulla, fallback all'API Viaggiatreno
        if not risultati:
            risultati = await cerca_stazione(params.nome_stazione)

        if not risultati:
            return (
                f"Nessuna stazione trovata per '{params.nome_stazione}'. "
                "Prova con il nome completo (es. 'Roma Termini', 'Milano Centrale')."
            )

        righe = [f'## Stazioni trovate per "{params.nome_stazione}"\n']
        for s in risultati[:20]:  # max 20 risultati
            righe.append(f"- **{s['nome']}** → ID: `{s['id']}`")

        if len(risultati) > 20:
            righe.append(f"\n_(mostrate 20 su {len(risultati)} — affina la ricerca per risultati più precisi)_")

        return "\n".join(righe)

    except Exception as e:
        return _handle_error(e, "cerca_stazione")


# ─── Tool 2: Monitora partenze ────────────────────────────────────────────────

@mcp.tool(
    name="trenitalia_monitora_partenze",
    annotations=ToolAnnotations(**{
        "title": "Monitora Partenze da Stazione",
        "read_only_hint": True,
        "destructive_hint": False,
        "idempotent_hint": False,
        "open_world_hint": True,
    }),
)
async def trenitalia_monitora_partenze(params: MonitoraPartenzeInput) -> str:
    """Mostra la bacheca partenze in tempo reale di una stazione ferroviaria italiana.

    Recupera i prossimi treni in partenza con: numero treno, destinazione, orario
    programmato, ritardo attuale, binario (programmato ed effettivo), e stato fisico
    del convoglio (se è ancora in stazione o è già partito).

    Args:
        params (MonitoraPartenzeInput): Input contenente:
            - id_stazione (str): ID Viaggiatreno (es. 'S01700'). Usa trenitalia_cerca_stazione per trovarlo.
            - limite (Optional[int]): Quanti treni mostrare (default 10, max 30)

    Returns:
        str: Tabella markdown con le partenze, oppure messaggio di errore.

        Campi per ogni treno:
        - Numero e categoria (es. FR 9631, REG 2342)
        - Destinazione finale
        - Orario di partenza programmato
        - Ritardo in minuti (o "in orario")
        - Binario effettivo vs programmato
        - Stato: "IN STAZIONE" / "PARTITO" / "NON ANCORA IN STAZIONE"

    Esempi d'uso:
        - "Quando parte il prossimo treno da Milano?" → id_stazione="S01700"
        - "Ci sono ritardi a Roma Termini?" → id_stazione="S08409"
        - "Mostrami 20 partenze da Napoli Centrale" → id_stazione="S09218", limite=20
    """
    try:
        risolto = await _resolve_stazione(params.id_stazione)
        if isinstance(risolto, str):
            return risolto
        id_stazione, nome_display = risolto

        orario = _orario_viaggiatreno()
        treni = await get_partenze(id_stazione, orario)

        if not treni:
            return f"Nessuna partenza trovata per {nome_display} nell'orario corrente. La stazione potrebbe non essere attiva in questo momento."

        treni = treni[: params.limite]

        righe = [f"## 🚉 Partenze da {nome_display} (`{id_stazione}`)\n"]
        righe.append(f"_Aggiornato: {now_rome().strftime('%H:%M:%S')} — {len(treni)} treni mostrati_\n")

        for t in treni:
            try:
                categoria = _safe_str(t.get("categoriaDescrizione", "")).strip() or "TRENO"
                numero = _safe_str(t.get("numeroTreno", ""))
                destinazione = _safe_str(t.get("destinazione", "N/D")).title()
                orario_partenza = _safe_str(t.get("orarioPartenza", ""))
                ritardo = _format_ritardo(t.get("ritardo"))

                # Converti timestamp ms → ora leggibile
                if orario_partenza.isdigit():
                    ts = int(orario_partenza) / 1000
                    orario_partenza = datetime.fromtimestamp(ts, ROME).strftime("%H:%M")

                # Binario
                bin_prog = t.get("binarioProgrammatoPartenzaDescrizione") or t.get("binarioPartenza")
                bin_eff = t.get("binarioEffettivoPartenzaDescrizione")
                binario = _format_binario(bin_prog, bin_eff)

                # Stato fisico del convoglio
                non_partito = t.get("nonPartito", True)
                in_stazione = t.get("inStazione", False)
                if non_partito and in_stazione:
                    stato = "🟡 IN STAZIONE"
                elif non_partito:
                    stato = "⚪ NON ANCORA IN STAZIONE"
                else:
                    stato = "🟢 PARTITO"

                righe.append(
                    f"### {categoria} {numero} → {destinazione}\n"
                    f"- **Orario**: {orario_partenza}  |  **Stato**: {ritardo}\n"
                    f"- **Binario**: {binario}  |  **Treno**: {stato}\n"
                )
            except Exception:
                # Skip treni malformati senza crashare
                continue

        return "\n".join(righe)

    except Exception as e:
        return _handle_error(e, "monitora_partenze")


# ─── Tool 3: Monitora arrivi ──────────────────────────────────────────────────

@mcp.tool(
    name="trenitalia_monitora_arrivi",
    annotations=ToolAnnotations(**{
        "title": "Monitora Arrivi in Stazione",
        "read_only_hint": True,
        "destructive_hint": False,
        "idempotent_hint": False,
        "open_world_hint": True,
    }),
)
async def trenitalia_monitora_arrivi(params: MonitoraArriviInput) -> str:
    """Mostra la bacheca arrivi in tempo reale di una stazione ferroviaria italiana.

    Recupera i prossimi treni in arrivo con: numero treno, provenienza, orario
    programmato, ritardo attuale e binario di arrivo.

    Args:
        params (MonitoraArriviInput): Input contenente:
            - id_stazione (str): ID Viaggiatreno (es. 'S01700'). Usa trenitalia_cerca_stazione per trovarlo.
            - limite (Optional[int]): Quanti treni mostrare (default 10, max 30)

    Returns:
        str: Tabella markdown con gli arrivi, oppure messaggio di errore.

        Campi per ogni treno:
        - Numero e categoria del treno
        - Provenienza (stazione di origine)
        - Orario di arrivo programmato
        - Ritardo in minuti (o "in orario")
        - Binario di arrivo (effettivo vs programmato)

    Esempi d'uso:
        - "A che ora arriva il treno da Firenze a Bologna?" → id_stazione Bologna
        - "Quanti treni sono in ritardo in arrivo a Venezia?" → id_stazione Venezia
    """
    try:
        risolto = await _resolve_stazione(params.id_stazione)
        if isinstance(risolto, str):
            return risolto
        id_stazione, nome_display = risolto

        orario = _orario_viaggiatreno()
        treni = await get_arrivi(id_stazione, orario)

        if not treni:
            return f"Nessun arrivo trovato per {nome_display} nell'orario corrente."

        treni = treni[: params.limite]

        righe = [f"## 🚉 Arrivi a {nome_display} (`{id_stazione}`)\n"]
        righe.append(f"_Aggiornato: {now_rome().strftime('%H:%M:%S')} — {len(treni)} treni mostrati_\n")

        for t in treni:
            try:
                categoria = _safe_str(t.get("categoriaDescrizione", "")).strip() or "TRENO"
                numero = _safe_str(t.get("numeroTreno", ""))
                provenienza = _safe_str(t.get("origine", "N/D")).title()
                orario_arrivo = _safe_str(t.get("orarioArrivo", ""))
                ritardo = _format_ritardo(t.get("ritardo"))

                if orario_arrivo.isdigit():
                    ts = int(orario_arrivo) / 1000
                    orario_arrivo = datetime.fromtimestamp(ts, ROME).strftime("%H:%M")

                bin_prog = t.get("binarioProgrammatoArrivoDescrizione") or t.get("binarioArrivo")
                bin_eff = t.get("binarioEffettivoArrivoDescrizione")
                binario = _format_binario(bin_prog, bin_eff)

                righe.append(
                    f"### {categoria} {numero} da {provenienza}\n"
                    f"- **Orario arrivo**: {orario_arrivo}  |  **Stato**: {ritardo}\n"
                    f"- **Binario**: {binario}\n"
                )
            except Exception:
                continue

        return "\n".join(righe)

    except Exception as e:
        return _handle_error(e, "monitora_arrivi")


# ─── Tool 4: Traccia treno ────────────────────────────────────────────────────

@mcp.tool(
    name="trenitalia_traccia_treno",
    annotations=ToolAnnotations(**{
        "title": "Traccia Treno in Tempo Reale",
        "read_only_hint": True,
        "destructive_hint": False,
        "idempotent_hint": False,
        "open_world_hint": True,
    }),
)
async def trenitalia_traccia_treno(params: TracciaTrenoInput) -> str:
    """Traccia la posizione e il ritardo di un treno specifico in tempo reale.

    Recupera la telemetria completa del convoglio: ultima stazione rilevata, ritardo
    accumulato, fermate già effettuate vs rimanenti, fermate soppresse e anomalie
    di linea segnalate da Trenitalia.

    Args:
        params (TracciaTrenoInput): Input contenente:
            - numero_treno (str): Numero treno (es. '9631', '2342'). Solo cifre.
            - id_stazione_origine (str): ID della stazione di partenza del treno (es. 'S01700').
              Necessario perché Viaggiatreno usa numero+origine come chiave univoca.

    Returns:
        str: Report markdown dettagliato sul treno, oppure messaggio di errore.

        Struttura del report:
        - Intestazione: numero, categoria, origine → destinazione
        - Situazione attuale: ultima stazione rilevata, ritardo corrente
        - Fermate: lista con orario programmato, effettivo e ritardo per ogni fermata
        - Anomalie: fermate soppresse e messaggi di anormalità
        - Stato finale: se il treno è arrivato a destinazione

    Esempi d'uso:
        - "Dov'è il Frecciarossa 9631?" → numero_treno="9631", id_stazione_origine="S01700"
        - "Il treno 2342 è in ritardo?" → numero_treno="2342", id_stazione_origine=<stazione origine>
        - "A che binario arriverà il mio treno?" → usa questo tool e guarda l'ultima fermata
    """
    try:
        risolto = await _resolve_stazione(params.id_stazione_origine)
        if isinstance(risolto, str):
            return risolto
        id_stazione_origine, _ = risolto

        dati = await get_andamento_treno(id_stazione_origine, params.numero_treno)

        if not dati:
            return (
                f"Nessun dato disponibile per il treno {params.numero_treno} "
                f"dalla stazione {id_stazione_origine}. "
                "Verifica che il numero treno e la stazione di origine siano corretti, "
                "e che il treno sia in circolazione oggi."
            )

        # ── Dati di testa ──────────────────────────────────────────────────
        categoria = _safe_str(dati.get("categoria", "")).strip() or "TRENO"
        numero = _safe_str(dati.get("numeroTreno", params.numero_treno))
        origine = _safe_str(dati.get("origine", "N/D")).title()
        destinazione = _safe_str(dati.get("destinazione", "N/D")).title()
        ritardo_attuale = _format_ritardo(dati.get("ritardo"))
        ultima_stazione = _safe_str(dati.get("stazioneUltimoRilevamento", "")).title() or "dato non disponibile"
        arrivato = dati.get("arrivato", False)

        righe = [
            f"## 🚆 {categoria} {numero}: {origine} → {destinazione}\n",
            f"**Ultima stazione rilevata**: {ultima_stazione}",
            f"**Ritardo attuale**: {ritardo_attuale}",
            f"**Stato**: {'✅ ARRIVATO a destinazione' if arrivato else '🔄 IN VIAGGIO'}\n",
        ]

        # ── Anomalie di linea ──────────────────────────────────────────────
        anormalita = dati.get("anormalita")
        if anormalita:
            righe.append("### ⚠️ Anomalie segnalate")
            if isinstance(anormalita, list):
                for a in anormalita:
                    righe.append(f"- {_safe_str(a)}")
            else:
                righe.append(f"- {_safe_str(anormalita)}")
            righe.append("")

        # ── Fermate soppresse ──────────────────────────────────────────────
        fermate_soppresse = dati.get("fermateSoppresse") or []
        if fermate_soppresse and isinstance(fermate_soppresse, list):
            righe.append("### ❌ Fermate soppresse")
            for fs in fermate_soppresse:
                nome_fs = _safe_str(fs.get("stazione", fs) if isinstance(fs, dict) else fs).title()
                righe.append(f"- {nome_fs}")
            righe.append("")

        # ── Fermate ───────────────────────────────────────────────────────
        fermate = dati.get("fermate") or []
        if fermate and isinstance(fermate, list):
            righe.append("### 🗺️ Fermate del percorso\n")
            righe.append("| Stazione | Arr. Prog. | Arr. Eff. | Part. Prog. | Part. Eff. | Ritardo | Binario |")
            righe.append("|---|---|---|---|---|---|---|")

            for f in fermate:
                try:
                    nome_f = _safe_str(f.get("stazione", "")).title()
                    ritardo_f = _format_ritardo(f.get("ritardo"))

                    def _ts_to_hm(ts_val: Any) -> str:
                        v = _safe_str(ts_val)
                        if v.isdigit() and int(v) > 0:
                            return datetime.fromtimestamp(int(v) / 1000, ROME).strftime("%H:%M")
                        return "—"

                    arr_prog = _ts_to_hm(f.get("arrivo_teorico"))
                    arr_eff = _ts_to_hm(f.get("arrivoReale"))
                    part_prog = _ts_to_hm(f.get("partenza_teorica"))
                    part_eff = _ts_to_hm(f.get("partenzaReale"))

                    bin_arr_prog = f.get("binarioProgrammatoArrivo")
                    bin_arr_eff = f.get("binarioEffettivoArrivo")
                    bin_part_prog = f.get("binarioProgrammatoPartenza")
                    bin_part_eff = f.get("binarioEffettivoPartenza")

                    # Mostra il binario più rilevante per questa fermata
                    binario_f = _format_binario(
                        bin_arr_prog or bin_part_prog,
                        bin_arr_eff or bin_part_eff,
                    )

                    soppressa = f.get("soppressa", False)
                    flag = " *(soppressa)*" if soppressa else ""

                    righe.append(
                        f"| {nome_f}{flag} | {arr_prog} | {arr_eff} | {part_prog} | {part_eff} | {ritardo_f} | {binario_f} |"
                    )
                except Exception:
                    continue

        return "\n".join(righe)

    except Exception as e:
        return _handle_error(e, "traccia_treno")


# ─── Tool 5: Orari tra stazioni (NeTEx + real-time) ──────────────────────────

from models import OrariTraStazioniInput  # noqa: E402 — import locale

@mcp.tool(
    name="trenitalia_orari_tra_stazioni",
    annotations=ToolAnnotations(**{
        "title": "Orari Treni tra Due Stazioni",
        "read_only_hint": True,
        "destructive_hint": False,
        "idempotent_hint": False,
        "open_world_hint": True,
    }),
)
async def trenitalia_orari_tra_stazioni(params: OrariTraStazioniInput) -> str:
    """Cerca collegamenti diretti Trenitalia per data; ritardi solo per la corsa odierna."""
    result = await rail.search_journeys(params.stazione_a, params.stazione_b,
        params.data, params.orario_da, "trenitalia", params.limite)
    if result["choices"]:
        choices = "\n".join(f"- {s['name']} (`{s['id']}`)" for s in result["choices"])
        return "Specifica la stazione:\n" + choices
    if not result["journeys"]:
        if result["status"] == "unavailable":
            return (f"Orario non disponibile per {result['date']}. "
                    + " ".join(result["warnings"])
                    + " Esegui python update_data.py per aggiornare i dati.")
        return f"Nessun collegamento diretto trovato per {result['date']} dalle {result['after']}. " + " ".join(result["warnings"])
    rows = [f"## Treni da {params.stazione_a} a {params.stazione_b}",
        f"Orario programmato del {result['date']} dalle {result['after']} (Europe/Rome).",
        "| Treno | Partenza | Arrivo | Ritardo live | Fermate intermedie |",
        "|---|---|---|---|---|"]
    for item in result["journeys"]:
        departure = datetime.fromisoformat(item["departure"]).strftime("%d/%m %H:%M")
        arrival = datetime.fromisoformat(item["arrival"]).strftime("%d/%m %H:%M")
        delay = _format_ritardo(item["live"].get("delay_minutes"))
        rows.append(f"| {item['train_number']} | {departure} | {arrival} | {delay} | {', '.join(item['intermediate_stops']) or '-'} |")
    rows.extend(result["warnings"])
    rows.append("Fonte orari: NAP CCISS. I dati live non disponibili non indicano puntualità.")
    return "\n".join(rows)


from models import CercaStazioniInput, CercaViaggiInput, StatoTrenoInput, TabelloneItaloInput

READ_ONLY = ToolAnnotations(read_only_hint=True, destructive_hint=False,
                            idempotent_hint=True, open_world_hint=True)


@mcp.tool(annotations=READ_ONLY, structured_output=True)
async def ciuff_cerca_stazioni(params: CercaStazioniInput) -> dict[str, Any]:
    """Cerca stazioni Trenitalia/Italo. Gli ID sono specifici dell'operatore."""
    return rail.stations(params.query, params.operatore, params.limite)


@mcp.tool(annotations=READ_ONLY, structured_output=True)
async def ciuff_cerca_viaggi(params: CercaViaggiInput) -> dict[str, Any]:
    """Confronta collegamenti diretti programmati Trenitalia e Italo per data. Nessun prezzo live."""
    return await rail.search_journeys(params.stazione_a, params.stazione_b,
        params.data, params.orario_da, params.operatore, params.limite)


@mcp.tool(annotations=READ_ONLY, structured_output=True)
async def ciuff_stato_treno(params: StatoTrenoInput) -> dict[str, Any]:
    """Consulta lo stato pubblico del treno, con fonte e limiti sulla data del rilevamento."""
    return await rail.train_status(params.operatore, params.numero_treno)


@mcp.tool(annotations=READ_ONLY, structured_output=True)
async def italo_tabellone(params: TabelloneItaloInput) -> dict[str, Any]:
    """Tabellone pubblico Italo. La data del servizio può non essere fornita dalla fonte."""
    try:
        return await get_station_board(params.stazione, kind=params.tipo)
    except Exception as exc:
        return {"status": "unavailable", "provider": "italo",
                "error_code": getattr(exc, "code", "upstream_unavailable"),
                "source_url": "https://italoinviaggio.italotreno.com/"}


@mcp.tool(annotations=READ_ONLY, structured_output=True)
async def ciuff_stato_fonti() -> dict[str, Any]:
    """Mostra validità e provenienza degli orari locali; non effettua un controllo live dei provider."""
    return {"sources": rail.sources(), "observed_at": now_rome().isoformat(),
            "live_health_checked": False, "refresh_command": "python update_data.py"}


@mcp.tool(annotations=READ_ONLY, structured_output=True)
async def ciuff_link_biglietti(params: OrariTraStazioniInput) -> dict[str, Any]:
    """Fornisce i siti ufficiali per prezzi e biglietti; nessuna tariffa o disponibilità è verificata."""
    return rail.ticket_links(params.stazione_a, params.stazione_b,
                             params.data or now_rome().date().isoformat())


if __name__ == "__main__":
    import argparse
    import os
    import uvicorn
    from http_app import create_http_app

    parser = argparse.ArgumentParser(description="Ciuff: free Italian railway MCP")
    transports = parser.add_mutually_exclusive_group()
    transports.add_argument("--http", action="store_true", help="Legacy SSE (backward compatible)")
    transports.add_argument("--sse", action="store_true", help="Legacy SSE")
    transports.add_argument("--streamable-http", action="store_true", help="Streamable HTTP at /mcp")
    args = parser.parse_args()
    if args.http or args.sse or args.streamable_http:
        host = os.environ.get("MCP_HOST", "127.0.0.1")
        app = create_http_app(mcp, rail, legacy_sse=args.http or args.sse)
        uvicorn.run(app, host=host, port=int(os.environ.get("PORT", "8000")),
                    log_level=os.environ.get("LOG_LEVEL", "info").lower(), proxy_headers=False)
    else:
        import asyncio

        async def run_stdio():
            try:
                await mcp.run_stdio_async()
            finally:
                await close_clients()

        asyncio.run(run_stdio())
