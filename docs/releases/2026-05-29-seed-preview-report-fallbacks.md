# Release Note — 2026-05-29 Seed Preview Report Fallbacks

## Summary

Seed-only HTML reports now materialize reusable fallback data for two sections that were previously blank or under-specified:

- topic landscape / `theme_treemap`;
- reproducibility audit / lightweight PRISMA-S disclosure.

## Changed

- Added `docs/agent-workflows/seed-preview-html-report.md`.
- Seed preview report materialization now writes `report_data.json` alongside sibling renderer files.
- Seed preview chart data now includes deterministic topic groups derived from title, abstract, and venue.
- Seed preview `prisma_log.json` now uses the same direct 16-key PRISMA-S shape expected by the HTML audit tab.

## Clarified

- Seed preview still does not run the full upstream `paper-search-pro` workflow.
- Seed preview still does not emit full `execution_log.json`.
- The seed disclosure marks `_meta.is_full_prisma_s=false`.
- Topic fallback is rule-based and lightweight; full reports can still use richer KG topics, PubMed MeSH, OpenAlex concepts, or LLM-assisted clustering.

## Verification

Recommended checks:

```powershell
python -m unittest tests.test_paper_search_pro_adapter
python -m unittest tests.test_report_bridge tests.test_mcp_server tests.test_report_tools tests.test_paper_search_pro_adapter
git diff --check
```
