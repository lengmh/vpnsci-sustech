# Release Note — 2026-05-28 Phase 3 Bridge Boundary Correction

## Summary

Clarified Phase 3 report-bridge semantics: **full `paper-search-pro` professional workflow** is not the same thing as the current **seed-only HTML preview**.

This note records the documentation/planning correction and the implementation landing for explicit report modes.

## Changed

- Updated `.idea/vpnsci-search-phases.md` with a dedicated boundary correction under Phase 3.3.
- Added a new execution plan:
  - `.idea/plans/2026-05-28-phase3-full-paper-search-pro-bridge-correction-plan.md`
- Added `docs/releases/` for reviewable release-note style project changes.

## Fixed / Clarified

- Phase 3 design always intended professional research to be handled by the full upstream `paper-search-pro` workflow.
- Current default bridge command runs `vpnsci_sustech.paper_search_pro_adapter`, which is seed-only preview:
  - reuses report renderer/assets
  - does not run five-source expansion
  - does not run upstream Skill recipe / SubAgent relevance grading
  - does not provide full RCS / PRISMA / export semantics
- Seed-only preview must be labeled as `seed_preview` / `vpnsci-seed-report`.
- Full report mode must not silently downgrade to seed-only preview.
- Full mode now returns a `handoff_required` job with a handoff package when only the seed adapter is configured.
- MCP output now includes explicit `Report Mode` and avoids claiming HTML generation for handoff-only full mode.
- Report UI should show query in two layers:
  - primary: user input query, e.g. `非接触体温测量`
  - secondary: actual expanded/split search queries, e.g. `non-contact body temperature measurement`, `infrared thermometry`
- Chinese user query should default to Chinese report language unless explicitly overridden.
- Full workflow handoff documentation now records two observed follow-up pitfalls:
  - Semantic Scholar search does not provide `topics` / `keywords`; use `fieldsOfStudy` / `s2FieldsOfStudy` only as weak fallback metadata and prefer OpenAlex/PubMed/arXiv/CrossRef or title+abstract extraction for topic groups.
  - HTML audit rendering requires direct PRISMA-S 16-key payloads in `prisma_log.json` and `report_data.json["prisma_log"]`; if reusing `execution_log.json`, unwrap `execution_log["prisma_s"]` before rendering.

## Verification

Implemented behavior is covered by focused unit tests. Full-suite verification is recorded in the task handoff/final response.

Recommended verification after implementation:

```powershell
python -m unittest tests.test_report_bridge tests.test_paper_search_pro_adapter tests.test_mcp_server
python -m unittest discover -s tests
```

## Next Steps

1. Configure or build a true full-workflow runner if direct upstream Skill/SubAgent execution becomes available.
2. Patch upstream renderer only if visible expanded-query UI is needed beyond materialized metadata.
3. Keep seed preview available for quick scan workflows.
