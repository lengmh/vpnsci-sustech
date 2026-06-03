# 2026-06-03 — CNKI Mainline Session, Recovery, and Continuation

## What changed

This update lands the mainline CNKI unification work through the session / report / recovery / continuation path:

- `SearchSession` now uses the v2-compatible view with:
  - `schema_version`
  - `origin`
  - `derivation`
  - `display_query`
  - `recovered_label`
- `SearchHit.hit_key` is now the stable persisted identity used by:
  - derived sessions
  - report recovery
  - session-hit continuation
- CNKI HTML import is now first-class `html_import` provenance, not a fake live search.
- batch CNKI downloads now emit a separate report-recovery sidecar under:

  ```text
  ~/.vpnsci-sustech/cache/download-workflows/
  ```

- sidecar recovery can restore a Search Session and regenerate reports later.
- unified session-hit continuation now supports CNKI hits through the same high-level fetch semantic as other sources.

## New user-facing entry points

### CLI

- `report-recover --sidecar ...`
- `fetch-hit <search_session_id> <hit_key>`

### MCP

- `generate_recovery_report(sidecar_path=...)`
- `fetch_search_hit(session_id=..., hit_key=...)`

## Recovery semantics

Current recovery ladder:

- **A**: download workflow sidecar
- **C**: weak local-file-only degraded recovery
- **B**: legacy report/materialized JSON compatibility recovery

Important: B is still supported, but it is not the preferred new recovery base.

## CNKI fetch boundary

This release also makes the current Phase 6 decision explicit:

- `fetch_paper(cnki_url)` is **not** promoted into the generic DOI/URL fetch kernel.
- CNKI detail URLs remain a controlled-source path.
- recommended CNKI full-text entry points are:
  - session-hit continuation
  - `cnki-download`
  - `cnki-batch-download`

## Why this boundary stays

CNKI has different operational constraints from ordinary publisher URLs:

- visible-browser gating
- possible manual captcha/login steps
- source-native artifact formats
- different provenance and recovery requirements

Merging that directly into the generic fetch kernel would increase site-specific complexity and weaken the model boundary between:

- direct DOI/URL fetch
- controlled-source continuation

## Known follow-up issues

This release is intentionally acceptable but not yet the final architectural endpoint in two places:

1. `cli.py` and `mcp_server.py` continue to grow as integration surfaces.
   - Core session / recovery / continuation semantics have already been extracted into dedicated modules.
   - However, the CLI and MCP entry layers still carry repeated parameter plumbing and user-facing glue.
   - A future cleanup should move more shared orchestration into service/helper modules so CLI and MCP remain thinner adapters.

2. The CNKI branch inside `fetch_from_search_hit(...)` is still concentrated in `fetcher.py`.
   - The current behavior is correct and keeps continuation unified at the session-hit level.
   - But if CNKI continuation grows further (artifact restoration, live browser continuation, richer metadata, more controlled-source branches), that branch may become too source-specific for the generic fetcher.
   - A future refactor may split this into a dedicated controlled-source continuation helper/adapter while preserving the same high-level continuation API.

## Verification

Representative coverage includes:

- session schema / hit identity compatibility
- CNKI report degradation policy
- sidecar persistence and lookup
- sidecar -> Search Session recovery
- CLI / MCP recovery report entry
- unified `fetch_from_search_hit(...)` continuation
- explicit CNKI URL rejection from the generic fetch kernel

The full targeted unittest suite passed after these changes.
