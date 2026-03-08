# PRD — Trenitalia MCP Server (SSE)

## 1. Contesto e obiettivo

Fornire un server MCP (Model Context Protocol) per dati ferroviari italiani in tempo reale,
esposto via trasporto **Server-Sent Events (SSE)** tramite `FastMCP` (SDK MCP ufficiale),
compatibile con qualsiasi client MCP che supporta `sse` transport (Claude Desktop, Cursor, client custom).

Sorgente dati: API non ufficiale **Viaggiatreno**
(`http://www.viaggiatreno.it/infomobilita/resteasy/viaggiatreno`).

---

## 2. Stato attuale (baseline)

| File | Ruolo |
|---|---|
| `server.py` | FastMCP server con 4 tool, trasporto stdio / streamable_http |
| `viaggiatreno.py` | Client httpx asincrono per le API Viaggiatreno |
| `models.py` | Modelli Pydantic v2 per validazione input tool |
| `requirements.txt` | `mcp[cli]`, `httpx`, `pydantic` |

Il server **funziona già** via stdio. Il PRD descrive la migrazione al trasporto SSE e
l'aggiunta di difensività sistematica sui tipi di dato dell'API.

---

## 3. Architettura target

```
Client MCP (Claude Desktop / Cursor)
        │  HTTP GET  /sse        (SSE stream — MCP events)
        │  HTTP POST /messages   (MCP request/response)
        ▼
FastMCP  mcp.run(transport="sse")   — Starlette app interna, uvicorn
        │
        ├── Tool: trenitalia_cerca_stazione
        ├── Tool: trenitalia_monitora_partenze
        ├── Tool: trenitalia_traccia_treno         ← tool principale
        └── (Tool: trenitalia_monitora_arrivi — mantenuto)

viaggiatreno.py  (client httpx asincrono — invariato)
models.py        (Pydantic v2 — invariato)
```

### 3.1 Pattern di avvio SSE (FastMCP nativo)

`FastMCP` versione 1.26.0 supporta nativamente `transport="sse"` tramite `mcp.run()`.
Non serve FastAPI: FastMCP costruisce internamente un'app Starlette con `SseServerTransport`.

- `GET /sse` → apre lo stream SSE (eventi MCP dal server al client)
- `POST /messages` → invia messaggi MCP dal client al server

Se in futuro si vogliono aggiungere endpoint REST custom (health, metrics), montare
`mcp.sse_app()` su un'app FastAPI esterna — ma non è nel scope attuale.

---

## 4. Tool principali

### 4.1 `trenitalia_cerca_stazione`

**Scopo**: Ricerca stazioni per nome, restituisce lista con ID Viaggiatreno.

**Input**: `nome_stazione: str` (2–100 char)

**Output**: Lista markdown `- **Nome** → ID: \`S00000\``

**Endpoint Viaggiatreno**: `GET /cercaStazione/{query}`

**Risposta API**: JSON array oppure testo pipe-separated (fallback). Entrambi gestiti.

**Uso**: Sempre come primo passo, prima degli altri tool.

---

### 4.2 `trenitalia_monitora_partenze`

**Scopo**: Bacheca partenze in tempo reale di una stazione.

**Input**:
- `id_stazione: str` (formato `S\d+`, es. `S01700`)
- `limite: int` (1–30, default 10)

**Output**: Tabella markdown con: categoria+numero treno, destinazione, orario programmato,
ritardo, binario effettivo vs programmato, stato fisico (IN STAZIONE / PARTITO / NON ANCORA).

**Endpoint Viaggiatreno**: `GET /partenze/{id_stazione}/{orario_url_encoded}`

**Timestamp**: il parametro orario è un datetime formattato come
`"Wed Dec 04 2024 10:30:00 GMT+0100"` e poi URL-encoded.

---

### 4.3 `trenitalia_traccia_treno` *(tool principale)*

**Scopo**: Telemetria completa di un singolo convoglio in tempo reale.

**Input**:
- `numero_treno: str` (solo cifre, 1–10 char)
- `id_stazione_origine: str` (formato `S\d+`)

**Output**: Report markdown con:
- Intestazione: categoria, numero, origine → destinazione
- Ultimo rilevamento GPS e ritardo attuale
- Tabella fermate: arr/part programmato + effettivo, ritardo, binario
- Sezione anomalie (`anormalita`) e fermate soppresse (`fermateSoppresse`)
- Flag arrivo a destinazione

**Endpoint Viaggiatreno**: `GET /andamentoTreno/{id_stazione_origine}/{numero_treno}`

**Nota**: numero_treno + id_stazione_origine formano la chiave univoca del convoglio.

---

### 4.4 `trenitalia_monitora_arrivi` *(mantenuto)*

Analogo a `monitora_partenze`, endpoint `GET /arrivi/{id_stazione}/{orario}`.

---

## 5. Normalizzazione e programmazione difensiva

L'API Viaggiatreno è **non documentata e instabile**. Le seguenti regole si applicano
in `viaggiatreno.py` e `server.py`:

### 5.1 Tipi inaffidabili

| Campo | Problema noto | Soluzione |
|---|---|---|
| `ritardo` | Può essere `int`, `str`, `null`, `""` | `_safe_int(v, default=-99)` |
| `orarioPartenza/Arrivo` | Timestamp in ms come `int` o `str` | `_safe_str` → `.isdigit()` → `int/1000` |
| `binario*` | Può essere `null`, `""`, assente | Fallback a campo alternativo + `_safe_str` |
| `nonPartito` / `inStazione` | `bool`, `0/1`, o assente | Accede con `.get()` + default |
| `fermate` | Può essere `null`, lista vuota, o assente | `dati.get("fermate") or []` |
| `anormalita` | `str`, `list[str]`, o `null` | `isinstance` check esplicito |
| `fermateSoppresse` | Lista di `dict` oppure lista di `str` | `isinstance(fs, dict)` check |

### 5.2 Regole generali

1. **Mai accedere direttamente** a campi con `[]` su dict provenienti da Viaggiatreno.
   Usare sempre `.get()` con default esplicito.
2. **`_safe_int` e `_safe_str`** sono i primitive di normalizzazione — non duplicarli.
3. Ogni singola fermata nel loop su `fermate` è wrappata in `try/except Exception: continue`
   per evitare che un record malformato rompa l'intera risposta.
4. Le risposte HTTP non-200 sollevano `raise_for_status()` e vengono catturate in
   `_handle_error()` con messaggi in italiano per l'LLM.
5. Timeout globale: 10 secondi per richiesta.
6. Il campo `categoriaDescrizione` può essere stringa vuota → fallback a `"TRENO"`.

### 5.3 Formato timestamp

I timestamp Viaggiatreno sono millisecondi UNIX come intero o stringa.
Conversione: `datetime.fromtimestamp(int(v) / 1000).strftime("%H:%M")`.
Valore `0` o stringa vuota → `"—"`.

---

## 6. Variabili d'ambiente

| Variabile | Default | Descrizione |
|---|---|---|
| `PORT` | `8000` | Porta su cui FastMCP / uvicorn ascolta |
| `MCP_HOST` | `0.0.0.0` | Host binding |
| `LOG_LEVEL` | `info` | Livello log uvicorn |

---

## 7. Gestione errori verso l'LLM

I tool **non sollevano eccezioni** verso il client MCP: catturano tutto e restituiscono
una stringa in italiano descrittiva. Mappatura in `_handle_error()`:

- `TimeoutException` → suggerisce di riprovare
- `HTTPStatusError 404` → ID stazione/treno errato
- `HTTPStatusError 500` → server Viaggiatreno down
- `ConnectError` → rete non disponibile
- Generico → tipo eccezione + messaggio raw

---

## 8. File NeTEx statico — `IT-IT-TRENITALIA_L1.xml.gz`

File compresso (~13 MB, ~488 MB decompresso) in formato **NeTEx Italian Profile**.
Pubblicato da IT-RAP il 2026-02-27, valido **2025-12-14 → 2026-06-13**.

Contenuto analizzato:

| Entità | Quantità |
|---|---|
| StopPlace totali | 1906 (791 ferroviari, 121 bus, 994 other) |
| Linee | 14 (13 ferroviarie + 1 bus) |
| VehicleJourneys (corse) | 25 480 |
| JourneyPatterns | 25 480 |
| ServiceLinks | 262 947 |

**Linee ferroviarie presenti**: Regionale, Regionale Veloce, Intercity, InterCityNotte,
Frecciarossa, Frecciargento, Frecciabianca, Eurocity, Euronight, Espresso, FrecciaLink,
sfm, Metropolitano.

**Struttura degli ID**: i `StopPlace` hanno un `PrivateCode` numerico (es. `830003010`)
diverso dall'ID `S\d+` usato da Viaggiatreno (es. `S01700`). Non esiste mappatura diretta
nel file — la ricerca stazione resta affidata all'endpoint `cercaStazione`.

**Uso attuale**: non caricato dal server. Utile come fonte offline per nomi stazione,
coordinate GPS, tipo di fermata. Eventuale uso futuro: ricerca locale alternativa a
`cercaStazione` oppure arricchimento con coordinate geografiche.

---

## 9. Test

- Test unitari su `_safe_int`, `_safe_str` con valori boundary (`null`, `""`, `"abc"`, `0`)
- Test di integrazione con mock httpx per `cerca_stazione` (risposta JSON + pipe-separated)
- Test end-to-end del server SSE con client MCP di test
- Fixture: risposta reale `andamentoTreno` salvata come JSON in `tests/fixtures/`

---

## 10. Non incluso nel progetto

- Autenticazione / API key (Viaggiatreno è pubblica)
- Caching persistente delle risposte (possibile TTL in-memory in futuro)
- FastAPI (non necessario: FastMCP gestisce SSE nativamente)
- Rate limiting (fuori scope per ora)
