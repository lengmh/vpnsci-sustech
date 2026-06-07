# vpnsci-sustech docs

Project docs entry.

- [Release Notes](releases/README.md)
- [Requirements](requirements.md)

Note: root `README.md`, `FAQ.md`, and `CONTEXT.md` stay at repo root for now to avoid breaking existing entry points and tool references. Any migration into `docs/` should be planned separately.

Key Phase 3 notes:

- [Codex Full Workflow Automation Boundary](releases/2026-05-28-codex-full-workflow-automation.md)
- [Docs and Local MCP Refresh](releases/2026-05-29-docs-and-local-mcp-refresh.md)
- [Query Display Workflow](releases/2026-05-29-query-display-workflow.md)
- [2026-06-03 CNKI Mainline Session, Recovery, and Continuation](releases/2026-06-03-cnki-mainline-session-recovery-continuation.md)

## Agent Workflows

- [paper-search-pro Full Report Handoff](agent-workflows/paper-search-pro-full-workflow.md)
- [Seed Preview HTML Report Workflow](agent-workflows/seed-preview-html-report.md)

## Repo Maintainer Notes

- Report frontend source lives under:
  - `tools/paper-search-pro/assets/webartifacts_app/paper-report/`
- Recommended refresh shortcut after report frontend source changes:

  ```powershell
  pwsh -File scripts/refresh_report_frontend.ps1
  ```

This shortcut is for source-repo maintenance only. It refreshes build output,
repo `bundle.html`, and the user-local bundled runtime copy; it does not
regenerate reports or validate DOM by itself.
