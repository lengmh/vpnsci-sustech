# Release Note — 2026-05-28 Codex Full Workflow Automation Boundary

## Summary

Documented and implemented the automation boundary for running full upstream `paper-search-pro` workflow from `vpnsci-sustech` handoff packages in a Codex session with multi-agent enabled.

The important distinction:

- MCP / Python side creates a structured full-workflow handoff.
- Codex conversation side owns SubAgent orchestration through `multi_agent_v1`.
- If SubAgents cannot start or complete, the current conversation must report that failure; seed-only preview must not be silently substituted.

## Changed

- Added automation plan:
  - `.idea/plans/2026-05-28-codex-full-workflow-automation-plan.md`
- Phase 3 docs now describe Codex-session automation as the path for full `paper-search-pro` workflow.
- Full-mode handoff metadata is expected to advertise:
  - `runner=codex-session`
  - `requires_multi_agent=true`
  - `subagent_tool=multi_agent_v1.spawn_agent`
  - `fallback_allowed=false`
- Handoff instructions are expected to require in-conversation reporting for:
  - `subagent_spawn_failed`
  - `subagent_timeout`
  - `subagent_result_invalid`
  - `full_workflow_step_failed`

## Why

`paper-search-pro` full workflow is Agent/Skill-oriented. Its classifier step relies on parallel SubAgents. The local `vpnsci-sustech` MCP server runs as a Python process and cannot directly invoke Codex session tools. Therefore automation must happen in the Codex session after MCP creates the handoff package.

## Verification

Completed on 2026-05-28:

```powershell
python -m unittest tests.test_report_bridge tests.test_mcp_server tests.test_report_tools tests.test_paper_search_pro_adapter
# Ran 29 tests ? OK

python -m unittest discover -s tests
# Ran 137 tests ? OK

git diff --check
# exit 0

python -m py_compile vpnsci_sustech/report_bridge.py vpnsci_sustech/mcp_server.py vpnsci_sustech/cli.py
# exit 0
```

Live Codex session smoke:

- `multi_agent_v1.spawn_agent` started agent `019e6e94-4b1c-7500-ba92-27dd5cd31dbb`.
- `multi_agent_v1.wait_agent` returned `subagent_smoke_ok` without timeout.

## Known Limits

- This does not make the MCP server itself call `multi_agent_v1`; that is not available inside the MCP Python process.
- This does not duplicate the full upstream `paper-search-pro` 14-step workflow inside `vpnsci-sustech` standard search.
- Seed preview remains available only as explicit `mode="seed_preview"`.

## Follow-up Clarifications

- MCP hosts are not required to have SubAgent capability. Their responsibility is to return a complete full-workflow handoff package; Codex/Agent session layers decide whether and how to continue.
- Full upstream `paper-search-pro` helper scripts have optional runtime dependencies documented in `docs/requirements.md`.
- Agents must avoid CJK query corruption by reading UTF-8 handoff JSON or passing UTF-8 argument files instead of relying on shell codepages.
- When KG metadata lacks `keywords` / `topics`, Agents should populate `chart_data.theme_treemap` from title + abstract fallback clustering before rendering the final HTML.
- Before spawning classifier SubAgents, Agents should determine a safe `max_active_subagents` value and launch batches in capacity-aware waves.
- If SubAgents are unavailable, Agents must ask the user to choose between `seed_preview`, main-Agent serial classification, or stopping/retrying later; no degraded path may run silently.
- The full workflow docs now explicitly separate MCP responsibilities from Agent/Codex runtime dependencies and include a dependency/degradation matrix for SubAgents, Python helper dependencies, source API failures, CJK encoding, topic fallback, and PRISMA renderer shape.
