# MCP Trenitalia

**Ciuff** is a free, self-hosted MCP server for Italian railway information. It combines official **Trenitalia and Italo timetables** with their public live-information services.

[ciuff.org](https://ciuff.org/) is the existing project website. The server works over stdio, Streamable HTTP or legacy SSE. It needs no paid API account, subscription, database or cloud service.

## Features

- Search stations and direct journeys across Trenitalia and Italo.
- Query Trenitalia train status, arrivals and departures.
- Query Italo train status and station boards.
- Report timetable coverage, sources and update timestamps.
- Keep future timetables separate from today's live information.
- Provide official ticket-site links. **Live prices, seat availability and booking are not implemented.**

Example questions:

> Which direct Trenitalia and Italo trains leave Roma Termini for Milano Centrale tomorrow after 08:00?
>
> What is the current status of Italo 8908?
>
> Do the downloaded timetables cover my travel date?

## Install

Requires Python 3.12 or newer. Dependencies are open source; network access is needed to download timetables and query live information.

```bash
git clone https://github.com/Fanfulla/MCP_Trenitalia.git
cd MCP_Trenitalia
python -m venv .venv
```

Activate the environment:

```powershell
# Windows PowerShell
.venv\Scripts\Activate.ps1
```

```bash
# macOS / Linux
source .venv/bin/activate
```

Then install and download current validated timetables:

```bash
python -m pip install -r requirements.txt
python update_data.py
```

With [uv](https://docs.astral.sh/uv/), `uv venv` and `uv pip install -r requirements.txt` are alternatives.

Timetable caches are created under `data/` and are not distributed in this repository. The first download can take a few minutes. Live tools can still run without the caches; schedule tools report missing or invalid coverage explicitly.

## Run and connect

```bash
# Local MCP client
python server.py

# Recommended HTTP transport: POST /mcp
python server.py --streamable-http

# Existing SSE clients: GET /sse and POST /messages/
python server.py --sse
```

`--http` remains an alias for **legacy SSE**, preserving the original runtime behavior. Older README versions incorrectly described that flag as Streamable HTTP.

Example stdio client configuration on Windows:

```json
{
  "mcpServers": {
    "MCP Trenitalia": {
      "command": "C:\\path\\to\\MCP_Trenitalia\\.venv\\Scripts\\python.exe",
      "args": ["C:\\path\\to\\MCP_Trenitalia\\server.py"]
    }
  }
}
```

On macOS/Linux, use absolute paths to `.venv/bin/python` and `server.py`. For HTTP clients, select the matching transport and connect to `http://127.0.0.1:8000/mcp` or `http://127.0.0.1:8000/sse`.

## Tools

The five original names and nested `params` input envelope remain available.

| Tool | Purpose |
|---|---|
| `trenitalia_cerca_stazione` | Local station lookup with Viaggiatreno fallback |
| `trenitalia_monitora_partenze` | Live Trenitalia departures |
| `trenitalia_monitora_arrivi` | Live Trenitalia arrivals |
| `trenitalia_traccia_treno` | Live Trenitalia train details with origin station |
| `trenitalia_orari_tra_stazioni` | Date-aware direct Trenitalia journeys and today's live enrichment |
| `ciuff_cerca_stazioni` | Station search across one or both operators |
| `ciuff_cerca_viaggi` | Direct scheduled journeys across one or both operators |
| `ciuff_stato_treno` | Public train status for an explicitly selected operator |
| `italo_tabellone` | Italo arrivals or departures by station name or Italo code |
| `ciuff_stato_fonti` | Local timetable coverage and provenance, not upstream uptime |
| `ciuff_link_biglietti` | Official purchase-site links, with prices explicitly unavailable |

The six new tools return MCP structured content. Example arguments for `ciuff_cerca_viaggi`:

```json
{
  "params": {
    "stazione_a": "Roma Termini",
    "stazione_b": "Milano Centrale",
    "data": "2026-09-28",
    "orario_da": "08:00",
    "operatore": "all",
    "limite": 10
  }
}
```

`operatore` accepts `all`, `trenitalia` or `italo` for station/journey searches. Train status requires a specific operator and `numero_treno`. `ciuff_stato_fonti` takes no arguments. Station IDs belong to their source; use names to search both operators. Ambiguous names return choices instead of selecting the first match.

## Sources and freshness

| Data | Source | Limits |
|---|---|---|
| Trenitalia schedules | [National NeTEx feed, CCISS](https://www.cciss.it/nap/mmtis/public/catalog/Asset/1080596) | Static schedules with service calendars and validity periods |
| Italo schedules | [NeTEx feed, CCISS](https://www.cciss.it/nap/mmtis/public/catalog/Dataset/1813935) | Direct rail services; combined itineraries are excluded |
| Trenitalia live information | [Viaggiatreno](http://www.viaggiatreno.it/) | Undocumented public endpoints, currently accessed over HTTP |
| Italo live information | [Italo In Viaggio](https://italoinviaggio.italotreno.com/) | Undocumented public endpoints, without a reliable service-date field |

Live verification on **2026-09-27** found:

- Trenitalia feed published on 2026-09-25, valid 2026-09-26 through 2026-12-12.
- Italo feed published on 2026-09-26, valid 2026-09-25 through 2027-02-02.
- Both feeds returned direct Roma Termini to Milano Centrale journeys.
- Both public live-information adapters returned data.

These are verification snapshots, not guarantees of continued upstream availability. Check `ciuff_stato_fonti` for your local feed dates.

```bash
# Refresh all, or just one provider
python update_data.py
python update_data.py --provider italo
python update_data.py --provider trenitalia
```

Refresh validates the feed before atomically replacing the previous cache. A failed refresh preserves the old file; expired coverage is still reported as expired. Running servers pick up cache changes without restarting. For unattended refresh, run the command daily with your operating-system scheduler. No scheduler or subscription is installed automatically.

```bash
# Check local timetable validity and the live Viaggiatreno and Italo endpoints
python check_sources.py
```

`check_sources.py` exercises the same parsers as the server: it fails when a live source stops responding or changes format, or when a local timetable is missing or expired, and warns when fewer than 21 days of validity remain. The repository runs it daily in the free [Source health](.github/workflows/sources.yml) GitHub Actions workflow after downloading both official feeds; a failure opens or updates a "Controllo fonti fallito" issue, which is closed automatically after recovery. GitHub pauses scheduled workflows in public repositories after 60 days without activity.

The parser supports the Italian-profile structures in the verified feeds, including UIC calendar bits, explicit date exceptions, boarding restrictions and overnight offsets. It is not a general NeTEx implementation. Unsupported calendars, unresolved references and ambiguous/nonexistent daylight-saving wall times fail closed. Searches cover direct trains, not transfers or historic telemetry.

Italo output distinguishes request time (`observed_at`) from the source update time. When the service date cannot be verified, `service_date` is null and `freshness` is `date_unverified`. Such delays are not attached to a dated scheduled journey. Missing delays remain null; they never mean "on time". Stale responses are labeled separately. Cancellation meanings are not guessed from undocumented numeric codes.

## Self-hosting

The server defaults to loopback. It includes a health endpoint, allowed-host checks, a per-peer request limit and an optional bearer token. Outbound requests use an in-process cache and connection pool, with bounded concurrency, response sizes and transient retries.

| Variable | Default | Purpose |
|---|---|---|
| `PORT` | `8000` | HTTP listen port |
| `MCP_HOST` | `127.0.0.1` | Bind address; use `0.0.0.0` to expose the service intentionally |
| `LOG_LEVEL` | `info` | Uvicorn log level |
| `MCP_ALLOWED_HOSTS` | `localhost,127.0.0.1,[::1]` | Comma-separated hostnames, without scheme or port |
| `MCP_RATE_LIMIT` | `60` | Requests per minute per connected peer, per process |
| `MCP_API_KEY` | unset | Optional token required as `Authorization: Bearer ...` |

Use TLS at your reverse proxy for remote access and add its hostname to `MCP_ALLOWED_HOSTS`. Forwarded client IP headers are not trusted: behind a proxy, the built-in limit applies to its address. Configure per-user limits at your proxy if needed. `/health` is token-exempt and reports process/local-cache status, not live upstream health. Requests with a missing or wrong token count towards the per-peer limit. The optional token is static access control, not OAuth.

The existing `Procfile` preserves legacy SSE. Configure `MCP_HOST` and `MCP_ALLOWED_HOSTS` for your host, or change the launch command to `python server.py --streamable-http`. The project requires no hosting subscription; operating a public host is your responsibility. The existing `web/` website remains separate.

## Development

```bash
python -m pip install -r requirements-dev.txt
python -m pytest -q
python -m compileall -q server.py models.py rail_service.py timetable.py build_timetable.py build_stazioni.py update_data.py check_sources.py viaggiatreno.py italo.py http_client.py http_app.py time_utils.py
```

Tests use local fixtures and mocked network transports. They cover calendars, midnight/DST, stale data, station ambiguity, retries, malformed responses, structured MCP output, HTTP limits and multi-client SSE cleanup. Live checks are separate from the offline suite. CI runs the offline tests on Windows and Linux; the daily source-health workflow runs the live checks.

The server uses the official [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk), not the separate `fastmcp` distribution. See [CHANGELOG.md](CHANGELOG.md) for migration notes.

## License

Project code is [MIT licensed](LICENSE). Upstream datasets and provider responses have their own terms and are **not** relicensed under MIT. Public availability does not establish redistribution rights. Downloaded timetable caches stay local; source metadata is in [data/sources.json](data/sources.json).

This independent project is unaffiliated with Trenitalia or Italo.
