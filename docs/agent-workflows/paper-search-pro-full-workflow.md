# MCP Agent Workflow — paper-search-pro Full Report Handoff

## Purpose

This document defines how an MCP-capable Agent should handle `vpnsci-sustech` full report handoff results.

`vpnsci-sustech` can search papers and create a structured full-workflow handoff. The full upstream `paper-search-pro` workflow is Agent/Skill-oriented and may require parallel SubAgents. Therefore the MCP Python process does not run SubAgents by itself.

The MCP requirement stops at producing a complete, machine-readable handoff for a capable Agent/Codex session. MCP hosts are not required to expose SubAgent tools.

## Trigger

When an Agent calls:

```python
generate_search_report(search_session_id="search-...", mode="full")
```

and the tool returns:

```text
Status: handoff_required
```

or a `full-workflow-handoff/instructions.md` path, a capable Agent should continue automatically if the user originally requested a full report.

## Required Agent Behavior

If the user asked for a full/professional/HTML research report and the MCP result is `handoff_required`, the Agent should:

1. Read the handoff `instructions.md`.
2. Read `query_plan_context.json` and `seed.json`.
3. Locate the configured/bundled `paper-search-pro` root.
4. Follow upstream `paper-search-pro/SKILL.md` for the full workflow.
5. Use the seed session as prior evidence, not as the final-only result set.
6. Run source expansion and query planning according to the selected tier.
7. Before relevance classification, determine how many classifier SubAgents can be active at once.
8. Use parallel SubAgents for relevance classification if the host supports them.
9. Materialize renderer data with the expected schema, including PRISMA-S unwrapping rules below.
10. Materialize `query_display.actual_queries` from the executed query plan.
11. Render final HTML and export artifacts.
12. Return the local report link and open the HTML report if requested/supported.

## Dependency Policy

`vpnsci-sustech` does not vendor or install the full upstream `paper-search-pro` runtime dependencies automatically.

When an Agent continues a full handoff, it should verify the local `paper-search-pro` runtime before invoking upstream helper scripts. See [`docs/requirements.md`](../requirements.md) for the optional/full workflow dependencies.

If dependencies are missing:

- report the missing packages and failed step in the current conversation;
- do not label a seed-only preview as a full workflow;
- either continue through available `vpnsci-sustech` adapters when this still satisfies the user-requested tier, or report `full_workflow_runner_unavailable`.

### Runtime Responsibility Boundary

The full workflow is considered complete at the process level only when both layers do their job:

| Layer | Responsibility | Does it need SubAgents? |
|---|---|---|
| `vpnsci-sustech` MCP server | Standard search, Search Session persistence, full-mode handoff package | No |
| Agent/Codex session | Continue upstream `paper-search-pro` full workflow from handoff | Yes for the normal parallel classifier path |
| `paper-search-pro` Python helpers | Deterministic retrieval, KG merge, materialization, exports, PRISMA helper scripts | No |
| Classifier execution | Apply RCS rubric to batches | Normally yes; can be degraded to main-Agent serial only after explicit user choice |

Therefore, a host without SubAgent support is not an MCP failure. It is an Agent execution-environment limitation that must be surfaced with explicit options.

### Dependency and Degradation Matrix

| Missing / unavailable item | Affected step | Required handling | Allowed user-confirmed path |
|---|---|---|---|
| SubAgent / multi-agent tool unavailable | STEP 6 relevance classification | Ask the user before continuing | User chooses `seed_preview`, `seed_classified`, main-Agent serial classification, or stop/retry |
| SubAgent capacity lower than expected | STEP 6 relevance classification | Reduce `max_active_subagents`, dispatch in smaller waves, record wave size | Continue parallel with smaller waves |
| SubAgent spawn timeout / invalid output | STEP 6 relevance classification | Report failure code and failed batch; retry only when safe | Ask user before serial fallback, seed preview, or seed-classified |
| Full `paper-search-pro` Python dependency missing | Helper script that imports it | Report package and failed command | Install after user approval, skip optional enrichment when tier allows, or stop |
| Optional source API unavailable/rate-limited | Source expansion or enrichment | Record source failure and continue if tier permits | Continue with available sources; disclose reduced source coverage |
| CJK shell encoding unreliable | Query passing / rendering | Read query from UTF-8 JSON or argument file | Regenerate corrupted artifacts from UTF-8 handoff files |
| Topic metadata missing | HTML topic section | Use deterministic title+abstract fallback | Deterministic frequency fallback; optional Agent label postprocess only after raw themes exist, then re-render |
| PRISMA wrapper/data shape mismatch | HTML audit section | Unwrap `execution_log["prisma_s"]` for renderer | Patch `prisma_log.json` and `report_data.json["prisma_log"]`, then re-render |

### Required User Prompt When SubAgents Are Unavailable

When the Agent detects that no SubAgent/multi-agent capability exists, it should ask a concise question before doing more full-workflow work:

```text
SubAgent/multi-agent execution is unavailable in this host.
Choose one:
1. Run seed_preview HTML report now — fastest, not full paper-search-pro; no formal RCS.
2. Run seed_classified seed-only RCS report — still not full paper-search-pro; classifies only the saved Search Session papers and performs no source expansion.
3. Continue with main-Agent serial classification — same full workflow scope, slower; final report will disclose no SubAgents were used.
4. Stop and retry later when SubAgents are available.
```

Do not infer this choice from the original full-report request. The user must
explicitly choose one of these alternatives. `seed_classified` must never be
described as a degraded full report; it is a seed-only classified alternative.

### Serial Fallback Implementation Boundary

Current repository truth: there is no standalone
`vpnsci_sustech.serial_full_report_runner` or Python-side serial-full runner.

If the user explicitly chooses main-Agent serial classification, the Agent must
continue the same full workflow scope from the handoff artifacts in the
conversation/session layer:

```text
seed SearchSession
-> query planning
-> source expansion / multi-query retrieval
-> dedup / KG
-> RCS classification by main Agent in batches
-> discovery curve / materialization
-> HTML report
```

This path is an execution-mode fallback for the full workflow, not a new report
mode and not a seed-only report. The final artifacts and response must record
the fallback reason, `rcs_execution_mode="main_agent_serial"`, completed
batches, budget/stop reason, and any missing full-workflow steps.

## Text Encoding Policy

All handoff inputs and generated artifacts must be UTF-8 without BOM.

Agents should avoid passing non-ASCII/CJK queries through shell command strings when the shell/codepage is uncertain. Prefer one of:

- read the query from `seed.json` / `query_plan_context.json`;
- write a UTF-8 JSON argument file and pass only the file path;
- in Python snippets, use Unicode escapes or load text from UTF-8 files.

If a generated artifact contains replacement text like `???`, treat that as an Agent execution/encoding bug and regenerate the affected artifacts from the UTF-8 handoff files. The current `vpnsci-sustech` handoff JSON files are UTF-8 and should preserve Chinese queries.

## Query Display in HTML

Full reports must show both:

- the user-facing query in the Hero H1;
- the actual executed source-specific search strings in a compact strip below H1.

Required renderer-facing metadata shape:

```json
{
  "query": "红外线测量",
  "user_query": "红外线测量",
  "display_query": "红外线测量",
  "query_display": {
    "user_query": "红外线测量",
    "primary": "红外线测量",
    "actual_queries": [
      {
        "source": "OpenAlex",
        "queries": [
          "infrared measurement",
          "infrared thermography measurement",
          "near-infrared spectroscopy measurement"
        ]
      },
      {
        "source": "Semantic Scholar",
        "queries": ["infrared measurement"]
      }
    ]
  }
}
```

Source labels should be human-readable (`OpenAlex`, `Semantic Scholar`, `CrossRef`, `PubMed`, `arXiv`, `seed`).

Display rules:

- H1 remains the user query only.
- The query strip uses hanging alignment: source badge left, query chips right.
- Do not hardcode `OR` / `AND` between chips. Each chip represents one executed query/strategy; Boolean syntax inside a query string is rendered literally.
- Omit a `seed` row when the seed query equals the H1 query.
- Keep the report's existing visual language: muted, small, subtle, wrapping chips.

Materialization rule:

- If `query_plan.json` is available, pass it to `scripts.data_materialization --query-plan`.
- When materializing classified full-workflow results, pass the RCS execution
  mode explicitly:
  - `--rcs-execution-mode subagent_parallel` for normal classifier SubAgents;
  - `--rcs-execution-mode main_agent_serial` only after explicit user-confirmed
    serial fallback.
- `parse_failed_uncertain` parser fallback records remain visible in the paper
  list but are marked `rcs_valid=false`, `rcs_source="parser_fallback"`, and do
  not enter RCS histograms or high/close relevance totals.
- If materialization already happened, patch `metadata.json` and `report_data.json["metadata"]` from the executed `query_plan.json` / `query_plan_list.json`, then re-render.
- Do not reconstruct Chinese query text from shell literals. Read UTF-8 JSON files.

Validation before final delivery:

- `metadata.query_display.actual_queries` is present when source-specific queries were executed;
- `report_data.json["metadata"]["query_display"]["actual_queries"]` matches `metadata.json`;
- hydrated HTML contains `.psp-query-strip` and the expected source labels;
- no visible `???` appears in the query or query strip.

## Recovery and sidecar notes

Agents continuing from `vpnsci-sustech` should be aware that report inputs may come from:

- standard Search Session;
- derived Search Session;
- download workflow sidecar recovery.

When the source is a download workflow sidecar:

- restored sessions should preserve `display_query` / `recovered_label` distinctly;
- the restored session provenance should not be mislabeled as live `source_execution`;
- if original query provenance is absent, prefer summary/recovered-summary wording rather than search wording.

Compatibility note: current source builds render the strip in React. If a runtime still ships an older pre-built `bundle.html`, `html_renderer_webartifacts.py` injects a small compatibility guard that reads `query_display.actual_queries` and inserts the strip after the Hero H1. Rebuilding `bundle.html` remains the preferred release path.

### Bundle / runtime refresh rule

When full-workflow or compatibility-path report UI code changes under:

- `tools/paper-search-pro/assets/webartifacts_app/paper-report/src/**`

the Agent should treat the report frontend as a three-layer artifact:

1. TS/React source
2. built `dist/assets/*`
3. pre-built single-file `bundle.html` plus the user-local runtime copy under `~/.vpnsci-sustech/tools/paper-search-pro`

Therefore:

- repo maintainers may use the shortcut:

  ```powershell
  pwsh -File scripts/refresh_report_frontend.ps1
  ```

  This is a source-repo maintenance helper, not a product CLI/MCP feature.

- `npm run build` is not enough by itself;
- `bundle.html` must be re-inlined from `dist/index.html`;
- MCP/CLI/report-bridge users must refresh the local runtime copy (for example via `vpnsci-sustech report-tools install --force`);
- then regenerate HTML and verify the visible DOM.

Do not diagnose all stale-report problems as "browser cache" or "MCP restart" by default. The more common failure is artifact drift between source, bundle, and local runtime copy.

## KG Field Completeness and Theme Fallback

Full reports may receive a seed KG that has titles, abstracts, identifiers, sources, and citations but lacks upstream `paper-search-pro` fields such as `keywords` and `topics`.

This is expected when expansion starts from `vpnsci-sustech` standard search metadata or when source adapters do not expose topic annotations.

Semantic Scholar Graph API search should not be treated as a source of paper-level `topics` or `keywords`: those fields are not supported by the S2 Graph API. S2 may provide `fieldsOfStudy` and `s2FieldsOfStudy`, but these are broad field-of-study categories and should only be used as weak theme metadata or fallback labels. Prefer richer topic sources when available:

- OpenAlex concepts/topics;
- PubMed MeSH terms / article keywords;
- CrossRef subjects, when present;
- arXiv categories, when present;
- title + abstract extraction fallback.

Agents must not leave the HTML topic/主题图景 section as a single meaningless `All papers` block when enough title/abstract text exists. Required fallback:

1. Try upstream `keywords` / `topics` clustering.
2. If missing or empty, derive rule-based topic groups from title + abstract.
   Chinese fallback uses the deterministic lexicon documented in
   `docs/agent-workflows/theme-lexicon-maintenance.md`.
3. Store the result in `chart_data.theme_treemap` with:
   - `themes[]` entries containing `name`, `value`, and `paper_ids`;
   - `total_papers`;
   - optional `method`, `status`, and `note` explaining the fallback.
4. Re-render HTML after patching `chart_data.json` and `report_data.json`.

For Chinese reports, the deterministic fallback should prefer readable Chinese
labels when title/abstract evidence supports them. If it only finds generic word
piles, write `status = "insufficient_text_theme_signal"` and keep the visible
module explicit rather than inventing labels.

### Agent-owned theme postprocess boundary

Quick reference:

- `docs/agent-workflows/theme-postprocess-contract.md`

When the workflow performs an optional label-refinement step after raw theme clustering, the default provider is the **current host Agent**, not a Python-side external API call.

Current repo truth:

- built-in `seed_preview` / recovery path already exposes formal host-Agent request/apply entrypoints for this postprocess step;
- `full` must reuse the same request/result/apply contract **and** is now in scope for the same automatic host-Agent postprocess coverage;
- this does **not** mean the whole full workflow loses its broader handoff semantics for expansion / classification / PRISMA-S orchestration.

This optional step may normalize or merge existing labels only. It must not
override the deterministic low-signal gate. If the lexicon needs improvement,
use the user-confirmed flow in
`docs/agent-workflows/theme-lexicon-maintenance.md`.

Recommended payload split:

- `chart_data.raw_theme_treemap` → raw deterministic clustering output
- `chart_data.theme_treemap` → display-facing refined result
- `chart_data.theme_postprocess` → lightweight trace

Recommended Agent request payload:

```json
{
  "report_mode": "full",
  "agent_guidance": "...",
  "themes": [
    {
      "index": 0,
      "name": "Machine Learning",
      "value": 12,
      "paper_ids": ["10.x/example"],
      "representative_titles": ["Paper title A", "Paper title B"]
    }
  ]
}
```

Required Agent result payload:

```json
{
  "groups": [
    {
      "label": "Machine Learning",
      "theme_indices": [0, 2]
    }
  ]
}
```

Validation rules:

- every raw theme index appears exactly once;
- no out-of-range indices;
- no empty labels;
- no partial coverage.

If the Agent does not provide a result, the workflow should fail open:

- keep `theme_treemap == raw_theme_treemap`
- record `theme_postprocess.reason = "agent_postprocess_not_supplied"`

Target handoff shape for the full-report theme-postprocess subchain:

```text
full materialization produces raw_theme_treemap
-> theme_postprocess_request.json written
-> host Agent reads request artifact or formal MCP request endpoint
-> host Agent returns validated result payload
-> Python applies refined theme_treemap
-> final full HTML rendered
```

In other words:

- `full` may still require a broader workflow handoff for upstream research steps;
- but once the theme-postprocess stage is reached, it should not stay permanently in an ad hoc/manual-only compare-script state.

## PRISMA-S Audit Data Shape

The full workflow has two related but different PRISMA-S artifacts. Agents must not confuse them:

1. `execution_log.json` is the complete audit wrapper:

   ```json
   {
     "prisma_s": {
       "1_database_information": {},
       "2_multi_database_searching": {}
     },
     "discovery_curve_snapshots": [],
     "agent_invocations": [],
     "errors": [],
     "stop_reason": null
   }
   ```

2. `prisma_log.json` and `report_data.json["prisma_log"]` are renderer-facing checklist payloads and must contain the 16 PRISMA-S items directly:

   ```json
   {
     "1_database_information": {},
     "2_multi_database_searching": {}
   }
   ```

If `execution_log.json` is produced before the final HTML render, the Agent must unwrap it before rendering:

```python
prisma_for_renderer = execution_log["prisma_s"]
```

Then write:

- `prisma_log.json = prisma_for_renderer`
- `report_data.json["prisma_log"] = prisma_for_renderer`

Do not write the full `execution_log.json` object into `prisma_log.json` or `report_data.json["prisma_log"]`. The React audit tab reads top-level keys such as `1_database_information` through `16_record_management`; if the renderer receives `{ "prisma_s": {...} }`, the visible "可复现性审计日志" section will be empty.

Required pre-render or post-render validation:

- `execution_log.json["prisma_s"]` exists when `execution_log.json` exists;
- `prisma_log.json` has 16 top-level canonical PRISMA-S keys;
- `report_data.json["prisma_log"]` has 16 top-level canonical PRISMA-S keys;
- hydrated `report.html` embeds `window.__REPORT_DATA__.prisma_log` with the same direct 16-key shape.

## SubAgent Concurrency Planning

Before launching classifier SubAgents, the Agent must determine the practical maximum active SubAgent count for the current host.

Recommended procedure:

1. Check host/tool documentation or known session limits.
2. If no explicit limit is known, start conservatively:
   - default wave size: 4;
   - maximum attempted wave size: 5, matching upstream `paper-search-pro` guidance;
   - reduce wave size if the host returns a thread/agent limit error.
3. Record the chosen `max_active_subagents` and batch launch plan in the workflow log.
4. Dispatch batches in waves:
   - launch at most `max_active_subagents` classifiers;
   - wait for completions needed to free capacity;
   - close completed agents when the host requires it;
   - launch the next wave.
5. If spawn fails because of capacity, retry once after closing completed agents.
6. If spawn still fails, report:
   - `failure code: subagent_spawn_failed`;
   - failed batch/step;
   - handoff path;
   - completed batches;
   - whether retry is safe.

The workflow must not silently switch to `seed_preview` or `seed_classified`
because SubAgents are unavailable.

If the host has no SubAgent capability, the Agent must ask the user before using
any fallback or seed-only alternative. The question should present these choices
clearly:

1. **Run `seed_preview` HTML report** — fast; uses the existing Search Session only; no full source expansion, full PRISMA-S audit, or formal RCS.
2. **Run `seed_classified` seed-only RCS report** — uses the existing Search Session only and asks the host Agent to classify that seed set; no source expansion or full PRISMA-S audit.
3. **Continue with main-Agent serial classification** — same full workflow scope, but slower and more context-intensive; must disclose that SubAgents were not used.
4. **Stop and retry later when SubAgents are available** — preserves upstream parallel workflow semantics.

Only run seed preview, seed-classified, or serial classification after the user
explicitly chooses that option. If the user chooses seed-classified, label it as
seed-only. If the user chooses serial classification, record the degraded
execution mode in workflow notes, PRISMA/disclosure notes, and final response.

## Failure Policy

The Agent must not silently switch to `mode="seed_preview"`,
`mode="seed_classified"`, or main-Agent serial classification.

If full workflow cannot continue, report the failure in the current conversation with:

- failure code;
- failed step;
- handoff path;
- output directory;
- completed steps;
- whether retry is safe;
- the explicit user choice needed to continue, when applicable.

Recommended failure codes:

- `subagent_spawn_failed`
- `subagent_timeout`
- `subagent_result_invalid`
- `full_workflow_step_failed`
- `full_workflow_runner_unavailable`

## User-Facing Report Link

When an HTML report is produced, open it in the default browser when supported.

Final user-facing messages should include:

- a Markdown link: `[打开 HTML 报告](file:///...)`;
- the local file path, e.g. `C:\Users\...\report.html`;
- a short Agent-code-editor note when relevant: if the HTML opens inside the editor, right-click the HTML file tab and choose “在资源管理器中显示/打开”, then open the original file in a browser.

Do not also print a separate bare `file://...` line. Some hosts display bare local URLs as text or open them inside the editor, which is confusing.

## Capability Mapping

| Capability | Owner |
|---|---|
| Standard metadata search | `vpnsci-sustech` MCP |
| Search session persistence | `vpnsci-sustech` MCP |
| Full workflow handoff package | `vpnsci-sustech` MCP |
| Codex `multi_agent_v1` SubAgents | Codex conversation layer |
| Full upstream `paper-search-pro` orchestration | Capable Agent / Codex session |
| Seed-only HTML preview | `vpnsci_sustech.paper_search_pro_adapter` |

## Non-Goals

- The MCP Python server should not claim direct access to Codex-only tools.
- Seed-only preview should not be labeled as full workflow.
- Ordinary `search_papers` should not automatically run full reports unless the query strongly requests a report/review workflow.
- MCP hosts are not required to provide SubAgent capability; they only need to return the handoff package for full mode.
