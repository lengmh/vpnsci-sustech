# Seed Preview HTML Report Workflow

## Purpose

This workflow defines the reusable lightweight path for converting an existing `vpnsci-sustech` Search Session into an HTML report.

Seed preview is intentionally different from full `paper-search-pro`:

- it reuses an existing Search Session;
- it does not run full source expansion;
- it does not run classifier SubAgents;
- it does not create a full `execution_log.json`;
- it must still provide enough renderer data for visible topic and audit sections.

## Trigger

This workflow runs when report generation uses `mode="seed_preview"` or the default seed adapter:

```text
vpnsci_sustech.paper_search_pro_adapter
```

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

1. Build topic groups from available paper metadata:
   - title;
   - abstract;
   - venue/journal;
   - source metadata if useful.
2. Use deterministic rule-based fallback first. Do not require LLM or SubAgent classification for seed preview.
3. Write `chart_data.theme_treemap` with:

   ```json
   {
     "themes": [
       {
         "name": "非接触测温/热筛查",
         "value": 12,
         "paper_ids": ["10.x/example"]
       }
     ],
     "total_papers": 30,
     "method": "seed_title_abstract_rule_fallback",
     "note": "..."
   }
   ```

4. Copy the same `chart_data` into `report_data.json["chart_data"]`.
5. Do not leave `theme_treemap.themes` empty when papers have title/abstract text.

Recommended baseline categories for infrared-style queries:

- `非接触测温/热筛查`
- `红外热成像/热像仪`
- `传感器/光谱/仪器`
- `遥感/环境红外`
- `材料/器件红外`
- `医学/生物应用`
- `红外测量综合`
- `其他相关研究`

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

## Validation

Seed preview implementation and agents that patch seed reports should verify:

- `chart_data.theme_treemap.themes` is non-empty for non-empty paper sets with text;
- every theme has `name`, positive integer `value`, and non-empty `paper_ids`;
- `prisma_log.json` has 16 top-level canonical PRISMA-S keys;
- `report_data.json["prisma_log"]` has the same direct 16-key payload;
- `report_data.json["chart_data"]["theme_treemap"]` matches `chart_data.json`;
- no `execution_log.json` is emitted or claimed for seed preview.

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
