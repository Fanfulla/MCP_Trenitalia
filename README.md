# MCP Trenitalia

An **MCP (Model Context Protocol)** server for real-time Italian railway data (Trenitalia), built with [FastMCP](https://github.com/jlowin/fastmcp) and the unofficial **Viaggiatreno** API.

Lets LLMs like Claude answer questions about Italian trains in natural language: schedules, delays, departures, arrivals, live tracking.

🌐 **[ciuff.org](https://ciuff.org/)** — project landing page. *Ciuff* as in *ciuff ciuff* (the sound a train makes): the name is intentionally playful.

---

## Demo

Connect the server to **Claude Desktop**, **Claude Web**, or any MCP-compatible client (see setup sections below) and ask Claude in natural language.

Example queries:

> "Which trains run from Roma Tuscolana to Roma Aurelia this morning?"

> "Is Frecciarossa 9631 delayed?"

> "Show me the next departures from Milano Centrale"

> "What time does the train from Tuscolana to Aurelia leave tomorrow morning?"

---

## Features

5 available tools:

| Tool | Description |
|---|---|
| `trenitalia_cerca_stazione` | Find stations by name and return the Viaggiatreno ID |
| `trenitalia_monitora_partenze` | Real-time departure board for a station |
| `trenitalia_monitora_arrivi` | Real-time arrival board for a station |
| `trenitalia_traccia_treno` | Full telemetry for a single train (position, delay, stops) |
| `trenitalia_orari_tra_stazioni` | Schedules between two stations with live verification and real-time delays |

All tools accept plain names (e.g. `"Tuscolana"`, `"Roma Termini"`) as well as technical IDs (`"S08408"`).

---

## How it works

### Data sources

**Viaggiatreno (real-time)**
Trenitalia's unofficial API for live data: departures, arrivals, train position and delay.

**NeTEx (offline timetable)**
NeTEx Italian Profile file published by IT-RAP, containing 25,480 train journeys with stops and schedules. Used as the primary source for `orari_tra_stazioni`.

### Hybrid logic for `orari_tra_stazioni`

1. **NeTEx offline** — finds all journeys connecting station A to station B on the requested day, filtered by weekday and validity period
2. **Live cross-check** — for journeys departing within the next 90 minutes, verifies the train actually appears on the Viaggiatreno departure board (removes "ghost trains" present in NeTEx but not actually stopping at that station)
3. **Real-time delay enrichment** — enriches each journey with the current delay from Viaggiatreno, parallelised with `asyncio.gather`
4. **Viaggiatreno fallback** — if NeTEx returns no results (special services, cancellations, etc.), queries the live board directly and verifies stop-by-stop the actual route

---

## Tech stack

- **Python 3.12**
- **[mcp\[cli\] 1.26.0](https://github.com/modelcontextprotocol/python-sdk)** — FastMCP with SSE and streamable-http transport
- **[httpx](https://www.python-httpx.org/)** — async HTTP client for the Viaggiatreno API
- **[pydantic v2](https://docs.pydantic.dev/)** — tool input validation

---

## Project structure

```
server.py               # FastMCP server + 5 tools (entrypoint)
viaggiatreno.py         # httpx client for the Viaggiatreno API
models.py               # Pydantic v2 input models
data/
  stazioni.json         # Name → Viaggiatreno ID dictionary (1,610 stations)
  timetable.json.gz     # Compressed NeTEx timetable (25,480 journeys, ~1.1 MB)
build_stazioni.py       # Script to regenerate stazioni.json
build_timetable.py      # Script to regenerate timetable.json.gz
web/                    # Next.js landing page (ciuff.org)
```

---

## Local installation

### Prerequisites

- **Python 3.12+** — download from [python.org](https://www.python.org/downloads/)
- **Git** — download from [git-scm.com](https://git-scm.com/)

### 1. Clone the repo

```bash
git clone https://github.com/Fanfulla/MCP_Trenitalia.git
cd MCP_Trenitalia
```

### 2. Install dependencies

You can use **uv** (recommended, much faster) or the standard **pip**.

#### With uv (recommended)

[uv](https://docs.astral.sh/uv/) is a modern Python package manager, significantly faster than pip. To install it:

```bash
# macOS / Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows (PowerShell)
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

Then, inside the project folder:

```bash
uv venv && uv pip install -r requirements.txt
```

#### With pip (alternative)

If you prefer not to install uv, the standard pip works just fine:

```bash
python -m venv .venv

# macOS / Linux
source .venv/bin/activate

# Windows
.venv\Scripts\activate

pip install -r requirements.txt
```

---

## Running the server

```bash
# stdio mode — for Claude Desktop / Cursor / local IDEs
python server.py

# HTTP mode — for remote deploy or Claude Web
python server.py --http
```

In `--http` mode the server exposes the MCP endpoint at:
- `POST /mcp` (streamable-http transport)

Default port: `8000` (override with the `PORT` environment variable).

---

## Claude Desktop setup

Claude Desktop reads its configuration from a JSON file. Open or create `claude_desktop_config.json`:

- **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

Add the `mcpServers` section:

**macOS / Linux:**
```json
{
  "mcpServers": {
    "MCP Trenitalia": {
      "command": "/absolute/path/to/.venv/bin/python",
      "args": ["/absolute/path/to/server.py"]
    }
  }
}
```

**Windows:**
```json
{
  "mcpServers": {
    "MCP Trenitalia": {
      "command": "C:\\absolute\\path\\to\\.venv\\Scripts\\python.exe",
      "args": ["C:\\absolute\\path\\to\\server.py"]
    }
  }
}
```

> **Note**: use absolute paths. Restart Claude Desktop after saving the file.

---

## Deploy to Railway

The repo includes a ready-made `Procfile` for [Railway](https://railway.app/):

```
web: python server.py --http
```

Just connect the GitHub repo to a new Railway project — deploys are automatic. The `PORT` variable is injected automatically by Railway.

---

## Environment variables

| Variable | Default | Description |
|---|---|---|
| `PORT` | `8000` | HTTP server port |
| `MCP_HOST` | `0.0.0.0` | Binding host |
| `LOG_LEVEL` | `info` | Log level |

---

## Notes

- The Viaggiatreno API is unofficial and undocumented — the server handles all anomalous responses defensively
- The NeTEx file is valid for the period **2025-12-14 → 2026-06-13** — to update it, run `build_timetable.py` with a new NeTEx file
- Tools never raise exceptions to the client: on error they return a descriptive message in Italian

---

## License

[MIT](https://github.com/Fanfulla/MCP_Trenitalia?tab=MIT-1-ov-file) — Copyright (c) 2026 Fanfulla
