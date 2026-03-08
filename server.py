#!/usr/bin/env python3
"""
Trenitalia MCP Server — server FastMCP per dati ferroviari in tempo reale.

Fornisce strumenti per:
- Cercare stazioni per nome e ottenerne l'ID Viaggiatreno
- Monitorare partenze e arrivi in una stazione
- Tracciare la posizione e il ritardo di un treno specifico

Sorgente dati: API non ufficiale Viaggiatreno (infomobilita.trenitalia.com)
Trasporto: stdio (default) oppure streamable_http (per deploy remoto)
"""

from __future__ import annotations

import gzip
import json
from datetime import date, datetime
from pathlib import Path
from typing import Any
from urllib.parse import quote

import httpx
from mcp.server.fastmcp import FastMCP

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
    Strategia: exact → startswith → substring (tutte case-insensitive).
    """
    q = query.strip().upper()
    esatti = []
    iniziano = []
    contengono = []

    for nome, sid in _STAZIONI.items():
        nome_up = nome.upper()
        if nome_up == q:
            esatti.append({"nome": nome.title(), "id": sid})
        elif nome_up.startswith(q):
            iniziano.append({"nome": nome.title(), "id": sid})
        elif q in nome_up:
            contengono.append({"nome": nome.title(), "id": sid})

    return esatti + iniziano + contengono


def _resolve_stazione(ref: str) -> tuple[str, str] | str:
    """
    Risolve un riferimento stazione (nome in chiaro o ID) all'ID Viaggiatreno.

    Restituisce:
    - (id, nome_display)  se risolto univocamente
    - str                 messaggio di errore/disambiguazione da restituire all'utente

    Logica:
    - Se sembra già un ID (inizia con 'S' e ha solo cifre dopo) → restituisce direttamente
    - Altrimenti cerca nel dizionario locale con fuzzy match
      - 1 risultato → risolto
      - >1 risultati → chiede disambiguazione all'utente
      - 0 risultati → messaggio di errore
    """
    v = ref.strip()

    # Già un ID Viaggiatreno
    if v.upper().startswith("S") and v[1:].isdigit():
        return (v.upper(), v.upper())

    risultati = _cerca_locale(v)

    if len(risultati) == 1:
        return (risultati[0]["id"], risultati[0]["nome"])

    if len(risultati) > 1:
        opzioni = "\n".join(f"- **{r['nome']}** → `{r['id']}`" for r in risultati[:10])
        return (
            f"Il nome '{v}' corrisponde a più stazioni. Specifica quale:\n{opzioni}"
        )

    return (
        f"Stazione '{v}' non trovata nel dizionario locale. "
        "Usa il tool `trenitalia_cerca_stazione` per cercarla per nome."
    )


# ─── Timetable offline (NeTEx) ────────────────────────────────────────────────

_TIMETABLE_FILE = Path(__file__).parent / "data" / "timetable.json.gz"

_DAY_NAMES = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]

def _load_timetable() -> list[dict]:
    if _TIMETABLE_FILE.exists():
        with gzip.open(_TIMETABLE_FILE, "rt", encoding="utf-8") as f:
            return json.load(f)
    return []

_TIMETABLE: list[dict] = _load_timetable()


def _journeys_between(
    stazione_a: str,
    stazione_b: str,
    orario_da: str = "00:00",
    solo_oggi: bool = True,
) -> list[dict]:
    """
    Cerca nell'orario NeTEx tutte le corse che:
    - fermano a stazione_a E poi a stazione_b (in quell'ordine)
    - partono da stazione_a non prima di orario_da (HH:MM)
    - circolano oggi (se solo_oggi=True)

    Restituisce lista di dict:
      { numero, linea, dep_a, arr_b, fermate_intermedie }
    """
    oggi = date.today()
    oggi_weekday = oggi.weekday()  # 0=Mon, 6=Sun
    oggi_str = oggi.isoformat()

    a_up = stazione_a.strip().upper()
    b_up = stazione_b.strip().upper()

    risultati = []

    for j in _TIMETABLE:
        # Filtro giorno della settimana + periodo validità
        if solo_oggi:
            if oggi_weekday not in j.get("w", []):
                continue
            pf = j.get("pf", "")
            pt = j.get("pt", "")
            if pf and pt and not (pf <= oggi_str <= pt):
                continue

        stops = j["s"]  # [[nome, arrivo, partenza], ...]

        # Trova indice di stazione_a e stazione_b
        idx_a = next((i for i, s in enumerate(stops) if a_up in s[0]), -1)
        if idx_a == -1:
            continue

        idx_b = next((i for i, s in enumerate(stops) if i > idx_a and b_up in s[0]), -1)
        if idx_b == -1:
            continue

        dep_a = stops[idx_a][2] or stops[idx_a][1]  # partenza da A (o arrivo se no partenza)
        arr_b = stops[idx_b][1] or stops[idx_b][2]  # arrivo a B

        if dep_a < orario_da:
            continue

        # Fermate intermedie (escluse A e B)
        intermedie = [s[0].title() for s in stops[idx_a+1:idx_b]]

        risultati.append({
            "numero": j["n"],
            "linea": j["l"],
            "dep_a": dep_a,
            "arr_b": arr_b,
            "intermedie": intermedie,
        })

    risultati.sort(key=lambda x: x["dep_a"])
    return risultati


# ─── Inizializzazione ─────────────────────────────────────────────────────────

mcp = FastMCP(
    "trenitalia_mcp",
    instructions=(
        "Server MCP per dati ferroviari italiani in tempo reale via Viaggiatreno. "
        "Flusso d'uso consigliato: 1) usa trenitalia_cerca_stazione per trovare l'ID stazione, "
        "2) usa trenitalia_monitora_partenze o trenitalia_monitora_arrivi per la bacheca, "
        "3) usa trenitalia_traccia_treno per dettagli su un singolo convoglio."
    ),
)


# ─── Utility di formattazione ─────────────────────────────────────────────────

def _orario_viaggiatreno() -> str:
    """
    Restituisce il timestamp nel formato richiesto dall'API Viaggiatreno.
    Es: 'Wed Dec 04 2024 10:30:00 GMT+0100'
    URL-encoded: 'Wed%20Dec%2004%202024%2010%3A30%3A00%20GMT%2B0100'
    """
    now = datetime.now()
    # Formato che accetta Viaggiatreno
    raw = now.strftime("%a %b %d %Y %H:%M:%S GMT+0100")
    return quote(raw)


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


def _handle_error(e: Exception, contesto: str = "") -> str:
    """Converte eccezioni httpx in messaggi testuali per l'LLM."""
    prefisso = f"[{contesto}] " if contesto else ""
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
    annotations={
        "title": "Cerca Stazione Trenitalia",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
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
    annotations={
        "title": "Monitora Partenze da Stazione",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": True,
    },
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
        - "Ci sono ritardi a Roma Termini?" → id_stazione="S00219"
        - "Mostrami 20 partenze da Napoli" → id_stazione="S00785", limite=20
    """
    try:
        risolto = _resolve_stazione(params.id_stazione)
        if isinstance(risolto, str):
            return risolto
        id_stazione, nome_display = risolto

        orario = _orario_viaggiatreno()
        treni = await get_partenze(id_stazione, orario)

        if not treni:
            return f"Nessuna partenza trovata per {nome_display} nell'orario corrente. La stazione potrebbe non essere attiva in questo momento."

        treni = treni[: params.limite]

        righe = [f"## 🚉 Partenze da {nome_display} (`{id_stazione}`)\n"]
        righe.append(f"_Aggiornato: {datetime.now().strftime('%H:%M:%S')} — {len(treni)} treni mostrati_\n")

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
                    orario_partenza = datetime.fromtimestamp(ts).strftime("%H:%M")

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
    annotations={
        "title": "Monitora Arrivi in Stazione",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": True,
    },
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
        risolto = _resolve_stazione(params.id_stazione)
        if isinstance(risolto, str):
            return risolto
        id_stazione, nome_display = risolto

        orario = _orario_viaggiatreno()
        treni = await get_arrivi(id_stazione, orario)

        if not treni:
            return f"Nessun arrivo trovato per {nome_display} nell'orario corrente."

        treni = treni[: params.limite]

        righe = [f"## 🚉 Arrivi a {nome_display} (`{id_stazione}`)\n"]
        righe.append(f"_Aggiornato: {datetime.now().strftime('%H:%M:%S')} — {len(treni)} treni mostrati_\n")

        for t in treni:
            try:
                categoria = _safe_str(t.get("categoriaDescrizione", "")).strip() or "TRENO"
                numero = _safe_str(t.get("numeroTreno", ""))
                provenienza = _safe_str(t.get("origine", "N/D")).title()
                orario_arrivo = _safe_str(t.get("orarioArrivo", ""))
                ritardo = _format_ritardo(t.get("ritardo"))

                if orario_arrivo.isdigit():
                    ts = int(orario_arrivo) / 1000
                    orario_arrivo = datetime.fromtimestamp(ts).strftime("%H:%M")

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
    annotations={
        "title": "Traccia Treno in Tempo Reale",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": True,
    },
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
        risolto = _resolve_stazione(params.id_stazione_origine)
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
            f"**Ultimo rilevamento GPS**: {ultima_stazione}",
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
                            return datetime.fromtimestamp(int(v) / 1000).strftime("%H:%M")
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
    annotations={
        "title": "Orari Treni tra Due Stazioni",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": True,
    },
)
async def trenitalia_orari_tra_stazioni(params: OrariTraStazioniInput) -> str:
    """Trova tutti i treni che passano da una stazione A a una stazione B in una data ora.

    Usa l'orario teorico NeTEx (offline) per trovare le corse, poi arricchisce
    ciascun treno con ritardo real-time da Viaggiatreno (se disponibile).
    Risolve nomi in chiaro (es. 'Tuscolana', 'Ponte Galeria') automaticamente.

    Args:
        params (OrariTraStazioniInput):
            - stazione_a: stazione di salita (nome o ID)
            - stazione_b: stazione di discesa (nome o ID)
            - orario_da: orario minimo di partenza da A, formato HH:MM (default: ora attuale)
            - limite: max treni da mostrare (default 10)

    Returns:
        Tabella markdown con: numero treno, linea, partenza da A, arrivo a B,
        fermate intermedie, ritardo real-time (se disponibile).
    """
    try:
        # Risolvi nomi stazione → nome canonico NeTEx (UPPERCASE)
        def _resolve_name(ref: str) -> str | None:
            """Restituisce il nome NeTEx uppercase, o None se non risolto."""
            r = _cerca_locale(ref)
            if r:
                return r[0]["nome"].upper()
            return ref.strip().upper()

        nome_a = _resolve_name(params.stazione_a)
        nome_b = _resolve_name(params.stazione_b)

        orario_da = params.orario_da or datetime.now().strftime("%H:%M")

        corse = _journeys_between(nome_a, nome_b, orario_da=orario_da)

        if not corse:
            return (
                f"Nessun treno trovato da **{nome_a.title()}** a **{nome_b.title()}** "
                f"dopo le {orario_da} oggi.\n"
                "Verifica i nomi delle stazioni o prova con un orario precedente."
            )

        corse = corse[: params.limite]

        ms_oggi = str(int(datetime.now().replace(hour=0, minute=0, second=0, microsecond=0).timestamp() * 1000))
        _VT_BASE = "http://www.viaggiatreno.it/infomobilita/resteasy/viaggiatreno"
        _VT_HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; trenitalia-mcp/1.0)"}

        async def _fetch_ritardo(client: httpx.AsyncClient, numero: str) -> str:
            """Recupera il ritardo real-time per un numero treno. Restituisce stringa."""
            try:
                nr = await client.get(f"{_VT_BASE}/cercaNumeroTreno/{numero}")
                if nr.status_code != 200:
                    return "–"
                cod_orig = nr.json().get("codLocOrig", "")
                if not cod_orig:
                    return "–"
                at = await client.get(f"{_VT_BASE}/andamentoTreno/{cod_orig}/{numero}/{ms_oggi}")
                if at.status_code != 200:
                    return "–"
                return _format_ritardo(_safe_int(at.json().get("ritardo"), default=-99))
            except Exception:
                return "–"

        # Tutte le chiamate real-time in parallelo
        async with httpx.AsyncClient(timeout=httpx.Timeout(6.0), headers=_VT_HEADERS) as client:
            import asyncio as _asyncio
            ritardi = await _asyncio.gather(*[_fetch_ritardo(client, c["numero"]) for c in corse])

        righe = [
            f"## 🚆 Treni da **{nome_a.title()}** a **{nome_b.title()}**\n",
            f"_Orario teorico NeTEx + ritardo real-time Viaggiatreno — da {orario_da}_\n",
            "| Treno | Linea | Part. da A | Arr. a B | Ritardo | Fermate intermedie |",
            "|---|---|---|---|---|---|",
        ]

        for corsa, ritardo_str in zip(corse, ritardi):
            intermedie = ", ".join(corsa["intermedie"]) if corsa["intermedie"] else "–"
            righe.append(
                f"| **{corsa['numero']}** | {corsa['linea'] or '–'} "
                f"| {corsa['dep_a']} | {corsa['arr_b']} "
                f"| {ritardo_str} | {intermedie} |"
            )

        return "\n".join(righe)

    except Exception as e:
        return _handle_error(e, "orari_tra_stazioni")


# ─── Entrypoint ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys

    if "--http" in sys.argv:
        # Deploy remoto: avvia come server HTTP su porta 8000
        # Configurabile con variabile PORT
        import os
        port = int(os.environ.get("PORT", 8000))
        print(f"[trenitalia_mcp] Avvio in modalità SSE su porta {port}", file=sys.stderr)
        mcp.run(transport="sse", port=port)
    else:
        # Default: stdio (per Claude Desktop, Cursor, ecc.)
        mcp.run()