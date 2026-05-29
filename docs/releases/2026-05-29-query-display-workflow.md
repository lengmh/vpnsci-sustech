# Release Note — 2026-05-29 Query Display Workflow

## Summary

HTML reports now have a reusable query display path: the Hero title keeps the user's query, and a compact strip below it shows the actual source-specific search queries used by the workflow.

## Changed

- Added renderer metadata support for `query_display.actual_queries`.
- Added a Hero query strip with source badges and wrapping query chips across the Swiss, Editorial, and Document report tops.
- Seed preview materialization now emits actual query groups from Search Session query variants.
- Full `paper-search-pro` materialization can receive `--query-plan` and persist source-specific actual queries into report metadata.
- PRISMA-S logging now accepts both list-style query plans and object-style plans with `strategies`.
- The HTML renderer has a compatibility guard for older pre-built bundles; rebuilt React bundles render the same strip natively.

## Workflow Rules

- H1 shows the user query only.
- The actual query strip omits duplicate seed text when it equals the user query.
- Query chips do not imply `OR` or `AND`; Boolean syntax is shown only when present in the original query text.
- Query text must be read from UTF-8 JSON artifacts or UTF-8 argument files for CJK safety.

## Verification

Recommended checks:

```powershell
@'
from pathlib import Path
for path in [
    "vpnsci_sustech/paper_search_pro_adapter.py",
    "tools/paper-search-pro/scripts/data_materialization.py",
    "tools/paper-search-pro/scripts/prisma_s_logger.py",
    "tools/paper-search-pro/scripts/html_renderer_webartifacts.py",
]:
    compile(Path(path).read_text(encoding="utf-8"), path, "exec")
'@ | python -

python -m unittest tests.test_paper_search_pro_adapter

# Optional when updating the React bundle source:
cd tools/paper-search-pro/assets/webartifacts_app/paper-report
pnpm install
pnpm run build
```

If local Python cannot write `__pycache__` in the repository, use the `compile(...)`
smoke check above instead of `python -m py_compile`; it validates syntax without
creating bytecode files.
