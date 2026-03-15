# MCP Trenitalia

Server **MCP (Model Context Protocol)** per dati ferroviari italiani (Trenitalia) in tempo reale, costruito con [FastMCP](https://github.com/jlowin/fastmcp) e le API non ufficiali di **Viaggiatreno** (Trenitalia).

Permette a modelli LLM come Claude di rispondere a domande sui treni italiani in linguaggio naturale: orari, ritardi, partenze, arrivi, tracciamento in tempo reale.

🌐 **[ciuff.org](https://ciuff.org/)** — landing page del progetto. *Ciuff* come in *ciuff ciuff*: il nome è volutamente goliardico.

---

## Demo

Collega il server a **Claude Desktop**, **Claude Web** o qualsiasi client MCP compatibile (vedi sezioni sotto) e interroga Claude in linguaggio naturale.

Esempi di domande che puoi fare a Claude con questo server attivo:

> "Che treni passano da Roma Tuscolana verso Roma Aurelia stamattina?"

> "Il Frecciarossa 9631 è in ritardo?"

> "Mostrami le prossime partenze da Milano Centrale"

> "Domani mattina a che ora passa il treno da Tuscolana ad Aurelia?"

---

## Funzionalità

5 tool disponibili:

| Tool | Descrizione |
|---|---|
| `trenitalia_cerca_stazione` | Trova stazioni per nome e restituisce l'ID Viaggiatreno |
| `trenitalia_monitora_partenze` | Bacheca partenze in tempo reale da una stazione |
| `trenitalia_monitora_arrivi` | Bacheca arrivi in tempo reale in una stazione |
| `trenitalia_traccia_treno` | Telemetria completa di un singolo treno (posizione, ritardo, fermate) |
| `trenitalia_orari_tra_stazioni` | Orari tra due stazioni con verifica live e ritardo in tempo reale |

Tutti i tool accettano nomi in chiaro (es. `"Tuscolana"`, `"Roma Termini"`) oltre agli ID tecnici (`"S08408"`).

---

## Come funziona

### Fonti dati

**Viaggiatreno (real-time)**
API non ufficiale di Trenitalia per dati in tempo reale: partenze, arrivi, posizione e ritardo dei treni.

**NeTEx (orario teorico offline)**
File NeTEx Italian Profile pubblicato da IT-RAP, contenente 25.480 corse ferroviarie con fermate e orari. Viene usato come fonte primaria per il tool `orari_tra_stazioni`.

### Logica ibrida per `orari_tra_stazioni`

1. **NeTEx offline** — trova tutte le corse che collegano stazione A a stazione B nel giorno richiesto, filtrando per giorno della settimana e periodo di validità
2. **Cross-check live** — per le corse che partono entro i prossimi 90 minuti, verifica che il treno compaia nella bacheca partenze reale di Viaggiatreno (elimina i treni "fantasma" presenti in NeTEx ma che in realtà non fermano in quella stazione)
3. **Ritardo real-time** — arricchisce ogni corsa con il ritardo attuale da Viaggiatreno, in parallelo con `asyncio.gather`
4. **Fallback Viaggiatreno** — se NeTEx non trova risultati (treni straordinari, soppressi, ecc.), interroga direttamente la bacheca live e verifica fermata per fermata il percorso reale

---

## Stack tecnico

- **Python 3.12**
- **[mcp\[cli\] 1.26.0](https://github.com/modelcontextprotocol/python-sdk)** — FastMCP con trasporto SSE e streamable-http
- **[httpx](https://www.python-httpx.org/)** — client HTTP asincrono per le API Viaggiatreno
- **[pydantic v2](https://docs.pydantic.dev/)** — validazione input dei tool

---

## Struttura

```
server.py               # FastMCP server + 5 tool (entrypoint)
viaggiatreno.py         # Client httpx per API Viaggiatreno
models.py               # Pydantic v2 input models
data/
  stazioni.json         # Dizionario nome → ID Viaggiatreno (1610 stazioni)
  timetable.json.gz     # Orario NeTEx compresso (25.480 corse, ~1.1 MB)
build_stazioni.py       # Script per rigenerare stazioni.json
build_timetable.py      # Script per rigenerare timetable.json.gz
web/                    # Landing page Next.js (ciuff.org)
```

---

## Installazione locale

### Prerequisiti

- **Python 3.12+** — scaricabile da [python.org](https://www.python.org/downloads/)
- **Git** — scaricabile da [git-scm.com](https://git-scm.com/)

### 1. Clona il repo

```bash
git clone https://github.com/Fanfulla/MCP_Trenitalia.git
cd MCP_Trenitalia
```

### 2. Installa le dipendenze

Puoi usare **uv** (consigliato, più veloce) o il classico **pip**.

#### Con uv (consigliato)

[uv](https://docs.astral.sh/uv/) è un package manager Python moderno e molto più veloce di pip. Per installarlo:

```bash
# macOS / Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows (PowerShell)
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

Poi, nella cartella del progetto:

```bash
uv venv && uv pip install -r requirements.txt
```

#### Con pip (alternativa)

Se preferisci non installare uv, funziona anche con il pip standard incluso in Python:

```bash
python -m venv .venv

# macOS / Linux
source .venv/bin/activate

# Windows
.venv\Scripts\activate

pip install -r requirements.txt
```

---

## Avvio

```bash
# Modalità stdio — per Claude Desktop / Cursor / IDE
python server.py

# Modalità HTTP — per deploy remoto o Claude Web
python server.py --http
```

In modalità `--http` il server espone l'endpoint MCP su:
- `POST /mcp` (streamable-http, compatibile con Claude Web)

Porta default: `8000` (configurabile con variabile d'ambiente `PORT`).

---

## Configurazione Claude Desktop

Claude Desktop legge la configurazione da un file JSON. Apri o crea il file `claude_desktop_config.json`:

- **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

Aggiungi la sezione `mcpServers`:

**macOS / Linux:**
```json
{
  "mcpServers": {
    "MCP Trenitalia": {
      "command": "/percorso/assoluto/al/.venv/bin/python",
      "args": ["/percorso/assoluto/al/server.py"]
    }
  }
}
```

**Windows:**
```json
{
  "mcpServers": {
    "MCP Trenitalia": {
      "command": "C:\\percorso\\al\\.venv\\Scripts\\python.exe",
      "args": ["C:\\percorso\\al\\server.py"]
    }
  }
}
```

> **Nota**: usa percorsi assoluti. Dopo aver salvato il file, riavvia Claude Desktop.

---

## Deploy su Railway

Il repo include un `Procfile` pronto per [Railway](https://railway.app/):

```
web: python server.py --http
```

Basta collegare la repo GitHub a un nuovo progetto Railway — il deploy è automatico. La variabile `PORT` viene iniettata automaticamente da Railway.

---

## Variabili d'ambiente

| Variabile | Default | Descrizione |
|---|---|---|
| `PORT` | `8000` | Porta del server HTTP |
| `MCP_HOST` | `0.0.0.0` | Host binding |
| `LOG_LEVEL` | `info` | Livello log |

---

## Note

- L'API Viaggiatreno è non ufficiale e non documentata — il server gestisce in modo difensivo tutti i casi di risposta anomala
- Il file NeTEx è valido nel periodo **2025-12-14 → 2026-06-13** — per aggiornarlo eseguire `build_timetable.py` con il nuovo file NeTEx
- I tool non sollevano mai eccezioni verso il client: in caso di errore restituiscono un messaggio descrittivo in italiano

---

## Licenza

MIT — Copyright (c) 2026 Fanfulla
