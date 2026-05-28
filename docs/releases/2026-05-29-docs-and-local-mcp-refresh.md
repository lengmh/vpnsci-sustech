# Release Note — 2026-05-29 Docs and Local MCP Refresh

## Summary

Updated user-facing documentation for the current search/report modes and refreshed the local MCP/report-tool runtime from the repository source.

## Changed

- Root `README.md` now describes report modes in user-facing terms:
  - standard search;
  - `seed_preview` quick HTML report;
  - `full` professional research report.
- Root `FAQ.md` now clarifies that seed preview includes topic landscape and lightweight PRISMA-S disclosure, while full mode remains the complete professional workflow.
- Technical execution details stay in `docs/agent-workflows/` and `docs/requirements.md` instead of the root README.
- Report messages now prefer a Markdown HTML link plus local path, and include an Agent-code-editor hint for opening the original file through Explorer when the editor captures `file://` links.

## Clarified

- `seed_preview` is a complete quick-report path, not a full professional research workflow.
- If full mode needs parallel classification but the current Agent environment does not provide it, the user must choose between quick preview, main-Agent serial classification, or retrying later.
- Local report runtime files and credentials remain under the user's local configuration/cache directories.

## Verification

Recommended checks:

```powershell
python -m unittest tests.test_report_bridge tests.test_mcp_server tests.test_report_tools tests.test_paper_search_pro_adapter
python -m py_compile vpnsci_sustech/report_bridge.py vpnsci_sustech/mcp_server.py vpnsci_sustech/paper_search_pro_adapter.py
python -m vpnsci_sustech.mcp_server
git diff --check
```
