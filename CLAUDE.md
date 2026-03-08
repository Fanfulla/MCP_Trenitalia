# CLAUDE.md — Trenitalia MCP Server

## Perché esiste questo progetto
Server MCP in Python che espone dati ferroviari italiani in tempo reale (Trenitalia / Viaggiatreno)
a modelli LLM tramite trasporto **SSE nativo di FastMCP**. Vedi `docs/PRD.md` per le specifiche funzionali complete.

---

## Stack obbligatorio
- **mcp[cli] v1.26.0** — `FastMCP` con `transport="sse"` nativo (no FastAPI richiesta)
- **httpx** — client async per le API Viaggiatreno (già in `viaggiatreno.py`)
- **pydantic v2** — validazione input tool (già in `models.py`)
- Gestione dipendenze: **uv** (preferito) oppure pip

Non aggiungere FastAPI a meno di necessità esplicita (endpoint REST custom).
Non usare `transport="streamable_http"`: usare `transport="sse"`.

---

## Struttura file
```
server.py               # FastMCP server + 5 tool (entrypoint)
viaggiatreno.py         # Client httpx per API Viaggiatreno (non modificare senza motivo)
models.py               # Pydantic input models (non modificare senza motivo)
data/stazioni.json      # Dizionario nome→ID Viaggiatreno (1610 stazioni)
data/timetable.json.gz  # Orario NeTEx completo (25.480 corse, ~1.1 MB)
build_stazioni.py       # Script one-shot per rigenerare stazioni.json
build_timetable.py      # Script one-shot per rigenerare timetable.json.gz
docs/PRD.md             # Specifiche funzionali complete — leggere prima di modificare i tool
```

---

## Comandi essenziali

```bash
# Setup (prima volta)
uv venv && uv pip install -r requirements.txt

# Avviare il server in modalità SSE (deploy remoto / sviluppo HTTP)
python server.py --http

# Avviare il server in modalità stdio (Claude Desktop / Cursor)
python server.py

# Rigenerare il dizionario stazioni (dopo aggiornamento NeTEx)
python build_stazioni.py

# Rigenerare il timetable NeTEx
python build_timetable.py

# Test
python -m pytest tests/ -v
```

---

## Variabili d'ambiente
- `PORT` — porta SSE (default: `8000`)
- `MCP_HOST` — host binding (default: `0.0.0.0`)
- `LOG_LEVEL` — livello log (default: `info`)

---

## Endpoint MCP SSE (modalità `--http`)
- `GET /sse` — apre lo stream SSE (server → client)
- `POST /messages` — invia messaggi MCP (client → server)

---

## I 5 tool disponibili

| Tool | Fonte dati | Descrizione |
|---|---|---|
| `trenitalia_cerca_stazione` | dizionario locale + API | Risolve nome → ID stazione |
| `trenitalia_monitora_partenze` | Viaggiatreno real-time | Bacheca partenze stazione |
| `trenitalia_monitora_arrivi` | Viaggiatreno real-time | Bacheca arrivi stazione |
| `trenitalia_traccia_treno` | Viaggiatreno real-time | Telemetria singolo treno |
| `trenitalia_orari_tra_stazioni` | NeTEx offline + Viaggiatreno | Orari A→B con ritardo live |

Tutti i tool accettano nomi in chiaro (es. `"Tuscolana"`) oltre agli ID (`"S08408"`).
La risoluzione avviene via `_cerca_locale()` → fuzzy match su `data/stazioni.json`.

---

## Regole architetturali

**API Viaggiatreno è instabile** — programmazione difensiva obbligatoria:
- Usare sempre `.get()` con default su dict provenienti da Viaggiatreno
- `_safe_int` e `_safe_str` in `viaggiatreno.py` sono i primitive di normalizzazione
- Ogni loop su fermate/treni va wrappato in `try/except Exception: continue`
- I tool **non sollevano mai** eccezioni verso il client — restituiscono stringa di errore in italiano
- Le chiamate real-time multiple vanno parallelizzate con `asyncio.gather`

**Flusso d'uso dei tool** (in ordine consigliato):
1. Se non conosci l'ID → `trenitalia_cerca_stazione`
2. Bacheca stazione → `trenitalia_monitora_partenze` / `trenitalia_monitora_arrivi`
3. Orari tra due stazioni (anche storici/futuri) → `trenitalia_orari_tra_stazioni`
4. Dettaglio singolo treno → `trenitalia_traccia_treno`

---

## Stile codice
- Async-first: tutte le funzioni che toccano rete sono `async def`
- Output dei tool: sempre stringhe Markdown in italiano
- Nessun `print()` — usare `logging` o `stderr` per debug
- Nomi variabili e commenti in italiano (coerenza col codebase esistente)
- Niente docstring ridondanti su funzioni il cui nome è già autoesplicativo
