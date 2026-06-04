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
- `report-recover --report-json ... --prefer B`
- `fetch-hit <search_session_id> <hit_key>`

### MCP

- `generate_recovery_report(sidecar_path=...)`
- `generate_recovery_report(report_json=..., prefer="B")`
- `fetch_search_hit(session_id=..., hit_key=...)`

## Recovery semantics

Recovery semantics target:

- **A**: download workflow sidecar
- **C**: weak local-file-only degraded recovery
- **B**: legacy report/materialized JSON compatibility recovery

Current public recovery entry points in this release are:

- explicit A recovery from sidecar
- explicit B recovery from legacy `report_data.json`

The unified resolver is now shared by CLI/MCP, but its auto decision stays conservative:

- auto still prefers A when A exists
- A/B identity + freshness are compared and surfaced internally
- non-`report_data.json` legacy support is best understood as materialized-bundle reconstruction, not as equally strong standalone public single-file entry points
- C remains a degraded-recovery semantic, not a separate public recovery command path

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

This release is intentionally acceptable but not yet the final architectural endpoint in several places:

1. `cli.py` and `mcp_server.py` continue to grow as integration surfaces.
   - Core session / recovery / continuation semantics have already been extracted into dedicated modules.
   - However, the CLI and MCP entry layers still carry repeated parameter plumbing and user-facing glue.
   - A future cleanup should move more shared orchestration into service/helper modules so CLI and MCP remain thinner adapters.

2. The CNKI branch inside `fetch_from_search_hit(...)` is still concentrated in `fetcher.py`.
   - The current behavior is correct and keeps continuation unified at the session-hit level.
   - But if CNKI continuation grows further (artifact restoration, live browser continuation, richer metadata, more controlled-source branches), that branch may become too source-specific for the generic fetcher.
   - A future refactor may split this into a dedicated controlled-source continuation helper/adapter while preserving the same high-level continuation API.

3. Public CNKI batch-download entry points still do not expose enough provenance inputs to naturally produce a fully formal A-sidecar in normal user flows.
   - The producer is now honest: if key fields such as `root_session_id`, `source_session_id`, `derived_session_id`, `original_query`, or `actual_queries` are missing, the emitted sidecar is downgraded to `report_recovery_capability="degraded"` instead of pretending to be standard.
   - This avoids false green mainline behavior, but it also means today’s public `cnki-batch-download` path usually produces a truthful degraded A-sidecar unless upstream context is threaded in explicitly.
   - A future iteration may expose richer provenance plumbing at the public batch-download layer so standard A-sidecars can be produced directly from end-user flows.

4. A/B comparison is implemented, but the automatic resolver remains intentionally conservative.
   - Resolver logic now records identity/freshness comparison details when both A and B are present.
   - Auto mode still prefers A when A exists; it does not yet automatically switch to B based on those comparison signals.
   - This is deliberate for safety, but it means the project has not yet reached a stronger “best candidate wins automatically” recovery policy.

5. Recovery output in CLI/MCP is still minimal.
   - User-facing recovery responses now report the selected recovery kind, but they do not yet surface `report_recovery_capability` or `missing_fields`.
   - For incomplete sidecars this means users may not immediately see why a recovered session is degraded unless they inspect the sidecar JSON itself.

## Verification

Representative coverage includes:

- session schema / hit identity compatibility
- CNKI report degradation policy
- sidecar persistence and lookup
- sidecar -> Search Session recovery
- legacy `report_json` -> Search Session recovery
- CLI / MCP recovery report entry
- unified `fetch_from_search_hit(...)` continuation
- explicit CNKI URL rejection from the generic fetch kernel

The full targeted unittest suite passed after these changes.
