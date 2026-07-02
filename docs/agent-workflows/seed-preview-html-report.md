# Seed Preview HTML Report Workflow

## Purpose

This workflow defines the reusable lightweight path for converting an existing `vpnsci-sustech` Search Session into an HTML report.

Seed preview is intentionally different from full `paper-search-pro`:

- it reuses an existing Search Session;
- it does not run full source expansion;
- it does not run classifier SubAgents;
- it does not produce formal RCS unless the user explicitly runs the separate
  `seed_classified` path described below;
- it does not create a full `execution_log.json`;
- it must still provide enough renderer data for visible topic and audit sections.

## Trigger

This workflow runs when report generation uses `mode="seed_preview"` or the default seed adapter:

```text
vpnsci_sustech.paper_search_pro_adapter
```

Current repository entrypoint truth:

- `vpnsci_sustech.paper_search_pro_adapter` is still the implemented light
  report bridge module.
- The intended future name is `vpnsci_sustech.light_report_bridge`.
- After that rename lands, new defaults and docs should point at
  `light_report_bridge`; the old `paper_search_pro_adapter` name should remain
  only as an import/CLI compatibility shim.

## Required Outputs

The materialized report directory must contain:

- `metadata.json`
- `paper_list.json`
- `chart_data.json`
- `prisma_log.json`
- `report_data.json`
- final `report.html` after rendering

`execution_log.json` is not produced by seed preview because that file is reserved for full PRISMA-S workflow audit wrappers.

## Topic Fallback

Seed preview cannot assume upstream KG fields such as `keywords` or `topics`.

Required behavior:

1. Build topic groups from available paper metadata, using only auditable theme
   signals:
   - existing `keywords` / `topics` when present;
   - otherwise `title` + `abstract` text.
2. Prefer deterministic clustering from existing `keywords` / `topics` first.
3. If structured theme metadata is missing or empty, use deterministic
   title+abstract frequency fallback.
4. Treat `venue` / `journal` / source metadata as provenance or noise-filter
   context, not as primary theme-label evidence.
5. Do not require LLM or SubAgent classification for seed preview.
6. Write `chart_data.theme_treemap` with:

   ```json
   {
     "themes": [
       {
        "name": "Machine Learning",
        "value": 12,
        "paper_ids": ["10.x/example"]
      }
    ],
    "total_papers": 30,
    "method": "seed_keywords_topics_frequency_fallback",
    "note": "..."
  }
   ```

7. Copy the same `chart_data` into `report_data.json["chart_data"]`.
8. Do not leave `theme_treemap` ambiguous: if title/abstract fallback has no
   reliable signal, keep the module visible and write an explicit low-signal
   status such as `insufficient_text_theme_signal` instead of inventing topics.
9. Theme names must come from the current paper set's existing `keywords` /
   `topics` or repeated text signals, not from a query-family-specific hardcoded
   taxonomy.
10. Chinese text fallback uses the maintained deterministic lexicon documented in
   `docs/agent-workflows/theme-lexicon-maintenance.md`; this lexicon is not a
   domain ontology.

Historical guardrail:

- Seed preview previously carried a query-family-specific infrared `THEME_RULES`
  taxonomy. That path is removed.
- Do not reintroduce fixed theme buckets for infrared or any other query family.
- Examples that use `红外线测量` / `infrared measurement` are query-display
  examples only; they are not a runtime theme taxonomy.

## Discovery Curve Boundary

Seed preview and recovery-compatible reports must not fabricate a full-workflow
discovery curve.

Allowed states:

1. **Enabled** only when there is real staged provenance / query-stage
   trajectory sufficient for the shared discovery-curve helper to estimate the
   curve.
2. **Disabled** when there is no staged evidence, weak recovery provenance, or
   too little sample signal. In this state numeric fields such as `tau`,
   `coverage_estimate`, confidence interval, and `estimated_total_relevant`
   should be `null`, and the HTML should keep the module visible with a clear
   placeholder/reason.

Forbidden:

- fixed default values such as `tau = 80.0`;
- two-point seed-only curves that imply full source expansion happened;
- coverage / CI / total-relevant estimates invented by renderer fallback;
- branches keyed to a historical session id, query text, fixture name, or fixed
  paper count.

Known current blocker: the implemented module still needs the planned
`light_report_bridge` / discovery-curve cleanup before this contract is fully
enforced in code.

## RCS Validity

`mode="seed_preview"` and recovery-compatible seed reports do not execute
formal relevance classification. The adapter may still carry a neutral raw
`rcs=5` value for renderer compatibility, but that value is scaffold only:

```json
{
  "rcs": 5,
  "rcs_valid": false,
  "rcs_source": "scaffold",
  "rcs_flag": "scaffold_neutral"
}
```

Renderer and statistics rules:

- scaffold RCS must not appear as a real paper score;
- scaffold RCS must not enter RCS histograms, high/close relevance counts, or
  tier allocation;
- paper cards/list rows should display `—` for invalid RCS;
- methods copy should say formal RCS classification was not executed.

`mode="seed_classified"` is the explicit seed-only alternative when the user
wants valid RCS for the saved Search Session papers without full source
expansion. It prepares a host-Agent classification request, applies the
returned JSON, and records:

```json
{
  "rcs_valid": true,
  "rcs_source": "seed_classifier",
  "rcs_scope": "seed_set",
  "rcs_execution_mode": "subagent_parallel"
}
```

If classification is done by the main Agent rather than classifier SubAgents,
the report must disclose `rcs_execution_mode="main_agent_serial"`.
`seed_classified` is not a full workflow fallback unless it is explicitly
presented as a seed-only classified alternative and the user chooses it.

## Agent-owned Theme Postprocess Contract

Quick reference:

- `docs/agent-workflows/theme-postprocess-contract.md`

Seed preview now distinguishes:

- `chart_data.raw_theme_treemap`
- `chart_data.theme_treemap`
- `chart_data.theme_candidate_resolution`
- `chart_data.theme_postprocess`

Required semantics:

1. `raw_theme_treemap` is the renderer-independent raw topic signal.
2. `theme_treemap` is the display-facing refined layer.
3. `theme_candidate_resolution` is a lightweight trace object describing whether
   no-hit / insufficient-hit ambiguous candidates were sent to the Host Agent
   and whether evidence-backed resolved candidates were applied.
4. `theme_postprocess` is a lightweight trace object describing whether an Agent-supplied refinement was applied.

### Default execution boundary

The default postprocess provider is **the current host Agent**, not a Python-side external API call.

That means:

- Python/materialization code may prepare a normalized request payload and validate/apply a result.
- The built-in seed/recovery mainline already exposes formal host-Agent request/apply entrypoints rather than relying on ad hoc compare scripts.
- This is not meant to remain seed-only forever; the same host-Agent coverage target also applies to the full-report theme-postprocess subchain.
- The Agent is responsible for the conservative “manual” label cleanup when that step is actually executed.
- If no Agent result is supplied, seed preview must fail open and keep `theme_treemap == raw_theme_treemap`.
- The Agent must not override `insufficient_text_theme_signal`; lexicon updates
  are a separate user-confirmed maintenance flow.
- Exception: when `theme_candidate_resolution_request.json` exists, the Host
  Agent should attempt candidate resolution. Resolved candidates with non-empty
  evidence are formal `theme_treemap` inputs for this report; unresolved
  candidates stay trace-only. This does not change deterministic alias runtime
  coverage.

### Agent request payload

When the host wants to run theme postprocess, Python should be able to expose a normalized request payload shaped like:

```json
{
  "report_mode": "seed_preview",
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

### Agent result payload

The Agent result must be shaped like:

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

- every raw `index` must appear exactly once across all groups;
- no out-of-range indices;
- no empty labels;
- no partial coverage.

### Allowed actions

The Agent may only:

- normalize incomplete labels;
- merge obviously synonymous themes;
- expand abbreviations then merge.

The Agent must not:

- recluster papers;
- invent unsupported new topics;
- delete evidence;
- change relevance / RCS / tier semantics.

### Trace expectations

`chart_data.theme_postprocess` should at least allow:

- `attempted`
- `applied`
- `reason`
- optional `merge_count`
- optional `model`

If no Agent postprocess result is supplied, the expected trace reason is:

- `agent_postprocess_not_supplied`

## Lightweight PRISMA-S Disclosure

Seed preview must generate a renderer-compatible, direct 16-key PRISMA-S disclosure so the HTML audit tab is not blank.

This is a lightweight disclosure, not a full PRISMA-S audit.

Required shape for `prisma_log.json` and `report_data.json["prisma_log"]`:

```json
{
  "1_database_information": {},
  "2_multi_database_searching": {},
  "...": {},
  "16_record_management": {},
  "_meta": {
    "mode": "seed_preview",
    "is_full_prisma_s": false,
    "note": "Lightweight disclosure only; full PRISMA-S requires mode=full."
  }
}
```

Minimum disclosure semantics:

- `1_database_information`: source list from `source_summary` or paper sources.
- `2_multi_database_searching`: `performed=true` only when multiple sources exist.
- `8_full_search_strategies`: user query, seed session query, and query variants.
- `9_limits_and_restrictions`: explicitly state seed-only limitations.
- `10_search_filters`: persisted Search Session filters, if any.
- `13_dates_of_searches`: generated timestamp and seed timestamp if available.
- `14_total_records`: seed paper count and source summary.
- `15_deduplication`: deduped Search Session count.
- `16_record_management`: search id, report mode, and expected output files.
- Non-performed steps should be explicit `performed=false` or `queried=false` with a clear seed-preview note.

Do not write `{ "seed": {...} }` as the only audit payload; the React audit tab expects top-level PRISMA-S canonical keys.

## Query Display

Seed preview HTML must keep the top title as the user's visible query and show the actual executed search strings directly below it when available.

Required metadata shape:

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
          "infrared thermography measurement"
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

Display rules:

- H1 shows only `metadata.query` / `query_display.user_query`.
- Render a small, low-contrast “实际检索 query” strip below H1.
- Use hanging alignment: source badge on the left, query chips on the right.
- Do not hardcode `OR` or `AND` between chips. Each chip is one executed query or strategy; if the query text itself contains Boolean syntax, render it as-is inside the chip.
- Omit the `seed` row when the seed query is identical to the H1 user query.
- Preserve the existing report visual style: small text, subtle borders, muted colors, wrapping chips.

### Query / title provenance rules

Seed preview materialization must distinguish:

- `original_query`
- `display_query`
- `recovered_label`

Required behavior:

- if `original_query` exists, title mode may be treated as search-like wording;
- if `original_query` is missing but `display_query` exists, prefer neutral summary wording;
- if only `recovered_label` exists, use explicit recovered-summary wording;
- never collapse inferred/recovered title text back into fake original query provenance.

## Validation

Seed preview implementation and agents that patch seed reports should verify:

- `chart_data.theme_treemap` either has positive themes or an explicit low-signal status;
- every rendered theme has `name`, positive integer `value`, and non-empty `paper_ids`;
- `prisma_log.json` has 16 top-level canonical PRISMA-S keys;
- `report_data.json["prisma_log"]` has the same direct 16-key payload;
- `report_data.json["chart_data"]["theme_treemap"]` matches `chart_data.json`;
- when actual query data exists, `metadata.query_display.actual_queries` is non-empty and the HTML renders `.psp-query-strip`;
- no `execution_log.json` is emitted or claimed for seed preview.

Compatibility note: current source builds render `.psp-query-strip` in React. If a deployed report still uses an older pre-built `bundle.html`, `html_renderer_webartifacts.py` injects a small runtime compatibility guard that reads the same `query_display.actual_queries` data and inserts the strip after the Hero H1. This guard is only a bridge until the bundle is rebuilt; the data contract above is still the source of truth.

## Frontend Bundle / Runtime Copy Refresh Boundary

The HTML renderer hydrates a **pre-built** single-file frontend artifact:

- repo source bundle:
  - `tools/paper-search-pro/assets/webartifacts_app/paper-report/bundle.html`
- local runtime copy used by MCP/CLI/report bridge:
  - `C:\Users\<user>\.vpnsci-sustech\tools\paper-search-pro\assets\webartifacts_app\paper-report\bundle.html`

This creates three distinct layers that can drift:

1. React/TS source (`src/**/*.tsx`, `src/lib/*.ts`)
2. built `dist/assets/*`
3. hydrated runtime bundle copy (`bundle.html` in repo and local runtime copy)

Required refresh rule after any React/TS report change:

Recommended shortcut for repo maintainers:

```powershell
pwsh -File scripts/refresh_report_frontend.ps1
```

This shortcut is for **source-repo maintenance only**. It is not a product CLI
feature and not an MCP tool. The manual source-of-truth steps remain below.

1. rebuild frontend assets:

   ```powershell
   cd tools/paper-search-pro/assets/webartifacts_app/paper-report
   npm run build
   ```

2. inline `dist/index.html` back into the single-file bundle:

   ```powershell
   $tmp = Join-Path $env:TEMP 'paper-report-inline-index.html'
   ((Get-Content 'dist/index.html' -Raw -Encoding utf8) -replace '/assets/', './assets/') |
     Set-Content -LiteralPath $tmp -Encoding utf8
   .\node_modules\.bin\html-inline.cmd -i $tmp -o 'bundle.html' -b 'dist'
   Remove-Item -LiteralPath $tmp -Force
   ```

3. refresh the local runtime copy when reports are generated through MCP/CLI/report bridge:

   ```powershell
   uv run python -m vpnsci_sustech.cli report-tools install --force
   ```

4. regenerate a representative report and verify the visible DOM, not just source files.

Important:

- `npm run build` alone only updates `dist/assets/*`; it does **not** refresh `bundle.html`.
- Refreshing the browser page alone does **not** help when the wrong `bundle.html` is already embedded in the generated report.
- Restarting a long-lived MCP host can still be necessary after refreshing the local runtime copy, but restart is a **last-mile refresh step**, not the main artifact-sync step.

Typical drift symptoms:

- TS/JS source looks correct, but generated HTML still renders old wording;
- `dist/assets/*.js` contains the new render path, but `bundle.html` does not;
- repo `bundle.html` is correct, but MCP/CLI-generated reports still use the old local runtime copy.

## Encoding

All JSON and HTML artifacts must be UTF-8 without BOM.

For Chinese queries, do not pass the query through an uncertain shell codepage. Prefer reading it from UTF-8 `seed.json`, `metadata.json`, or a UTF-8 JSON argument file. If the rendered query or query strip contains `???`, treat it as an encoding bug and regenerate from UTF-8 source files.

## User-Facing Report Link

After rendering, the tool should open the report in the default browser when the host supports it.

Final user-facing messages should include only:

- a Markdown link: `[打开 HTML 报告](file:///...)`;
- the local file path, e.g. `C:\Users\...\report.html`;
- a short Agent-code-editor note when relevant: if the HTML opens inside the editor, right-click the HTML file tab and choose “在资源管理器中显示/打开”, then open the original file in a browser.

Do not also print a separate bare `file://...` line. Some hosts display bare local URLs as text or open them inside the editor, which is confusing.

## Failure Policy

If seed preview cannot build topics or disclosure from available metadata:

- keep the report mode as `seed_preview`;
- show a clear note in the generated metadata or disclosure;
- do not label the report as full;
- do not fabricate full PRISMA-S execution evidence.

### Degraded chart policy

For thin metadata / CNKI subsets / `html_import` / weak recovery:

- discovery curve may enter `disabled`;
- citation analysis may enter `disabled`;
- topic analysis may enter `limited` or `disabled`;
- renderer-facing metadata should disclose whether the issue is:
  - `暂无数据` / missing data
  - `数据不够` / insufficient data

Do not keep legacy-looking charts alive with misleading estimates when execution trace or citation/year support is too weak.
