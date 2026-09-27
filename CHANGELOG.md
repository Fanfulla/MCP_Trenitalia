# Changelog

## Unreleased

### Added

- Updated the existing website with Trenitalia and Italo content, GitHub and X links, and lightweight interactive controls.
- Added separately rendered Italian and English pages, localized metadata, matching FAQ structured data and a social preview image.
- Added served-page SEO checks and web build/lint/type checks to CI.

- Free Italo train status and station boards using endpoints verified against the official public site.
- Cross-operator station and direct-journey searches, source coverage and official ticket-site links.
- Structured MCP output for the six new tools.
- Validated CCISS NeTEx imports for both operators, with a bounded atomic refresh command.
- UIC calendars, explicit service-date exceptions, boarding restrictions and overnight offsets.
- Streamable HTTP via `--streamable-http`, host allowlists, request limits and an optional bearer token.
- Offline regression tests and Windows/Linux CI.

### Fixed

- Keep the mobile demo video in its native portrait aspect ratio at desktop, tablet and phone widths.
- The mobile menu now closes after choosing a section, on Escape and on outside taps. The browser theme color follows the selected theme.
- Raised light-theme secondary text contrast to WCAG AA and removed 9–10 px reading text.

- `BOLOGNA C.LE` pointed to the underground high-speed platforms (S05046) instead of Bologna Centrale (S05043), now also listed separately as `BOLOGNA C.LE AV`. Firenze S.M.N. and 53 other timetable stations were missing from the Viaggiatreno dictionary; six more names now use the station confirmed by its NeTEx code.
- Natural station names such as "Bologna Centrale", "Firenze Santa Maria Novella", "Firenze SMN" and "Venezia Santa Lucia" now match the abbreviated official names of both operators.
- The five original tools resolve stations missing from the local dictionary through Viaggiatreno search.
- Source failures are reported as specific Italian messages instead of "Errore imprevisto (UpstreamError)".
- Tool examples referenced the wrong Viaggiatreno IDs for Roma Termini and Napoli Centrale.
- Global NeTEx validity was lost during conversion, allowing the old June 2026 timetable to appear current.
- Future journeys could receive today's live delays and departure-board fallback.
- Fixed-offset and server-local time calculations now use `Europe/Rome`.
- Station ambiguity and source-specific IDs are handled explicitly.
- Missing live delays remain unknown instead of being interpreted as punctuality.
- HTTP requests reuse a bounded pool and cache, with limited transient retries and explicit source errors.
- Individual SSE disconnects no longer close the shared pool used by other clients.

### Changed

- Updated Next.js and React, removed unused animation code and deferred demo video downloads.
- Corrected the old translation of Trenitalia as generic "Italian trains" throughout the website.
- Inlined the website CSS, stopped prefetching the current and alternate-language pages and switched demo posters to WebP: no render-blocking requests, 15 instead of 20 requests and 13% less transfer on first load.
- Installation commands preselect macOS/Linux or Windows from the visitor's platform.

- `build_stazioni.py` now updates `data/stazioni.json` from the local Trenitalia timetable, keeps entries it cannot verify and accepts a NeTEx code only when Viaggiatreno confirms it with a compatible name.

- Migrated from official MCP Python SDK 1.26.0 to 2.2.0.
- Kept the five original tool names and nested `params` inputs. `--http` remains legacy SSE; `--sse` makes that choice explicit.
- HTTP binding defaults to loopback. Remote hosts must configure `MCP_HOST` and `MCP_ALLOWED_HOSTS`.
- Removed the bundled expired timetable. Run `python update_data.py` after installation to create local caches.
- Combined Italo itinerary entries are excluded from direct-train searches.
- README now describes actual transports, source limitations and free self-hosting.

### Limits

- No verified free source for live fares or seat availability is integrated. Ticket links are not price quotes or prefilled searches.
- Italo live responses have no reliable service date; results expose that limitation and are not merged into dated journeys.
- Unsupported calendars and ambiguous/nonexistent DST times fail closed.
- Dataset redistribution rights are not assumed. The code license does not cover upstream data.

### Verification snapshot: 2026-09-27

- Downloaded and parsed current official Trenitalia and Italo feeds.
- Queried live status from both operators and an Italo station board.
- Verified direct Roma Termini to Milano Centrale searches for both operators.
- Verified legacy tool registration and structured content through MCP SDK calls.
- Tested Streamable HTTP and multi-client SSE behavior in process.

## 2026-03-15

- Existing Trenitalia server: five MCP tools, local NeTEx timetable and Viaggiatreno integration.
- Existing ciuff.org project website and installation documentation.
