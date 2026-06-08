# Theme Postprocess Contract — Developer Quick Reference

## Purpose

This document is the shortest source-of-truth summary for the report-theme postprocess contract.

Use it when:

- an Agent wants to refine report theme labels;
- a developer needs the request/result payload shape quickly;
- someone is patching `chart_data.json` / `report_data.json` manually for report re-render.

This contract is shared across:

- `seed_preview`
- `full`
- `recovery`

---

## Default execution boundary

The default provider is **the current host Agent**.

That means:

- Python/materializer **does not** default to calling an external LLM API directly.
- Python/materializer only:
  - builds the normalized request payload;
  - validates the Agent result;
  - applies the refined result;
  - writes trace metadata.
- The host Agent:
  - reads the request payload;
  - performs one conservative manual / host-local label cleanup pass;
  - returns one normalized result payload.

---

## Payload split

The renderer-facing payload keeps three layers:

- `chart_data.raw_theme_treemap`
- `chart_data.theme_treemap`
- `chart_data.theme_postprocess`

Semantics:

- `raw_theme_treemap`: raw deterministic theme signal
- `theme_treemap`: refined display layer
- `theme_postprocess`: trace of whether an Agent refinement was applied

---

## Agent request payload

```json
{
  "report_mode": "seed_preview",
  "agent_guidance": "...",
  "themes": [
    {
      "index": 0,
      "name": "治疗方法",
      "value": 4,
      "paper_ids": ["10.x/example"],
      "representative_titles": ["Title A", "Title B"]
    }
  ]
}
```

### Request rules

- `index` is the stable raw-theme index.
- `representative_titles` is lightweight context only.
- The Agent may use the request for label cleanup only.
- The request payload itself is **not** the final HTML payload.

---

## Agent result payload

```json
{
  "groups": [
    {
      "label": "治疗方法",
      "theme_indices": [0, 2]
    }
  ]
}
```

### Result validation rules

- every raw theme index must appear **exactly once**
- no out-of-range indices
- no empty labels
- no partial coverage

If validation fails:

- keep `theme_treemap == raw_theme_treemap`
- set `theme_postprocess.applied = false`
- set `theme_postprocess.reason = "invalid_mapping"`

---

## Allowed actions

The Agent may only:

- normalize incomplete labels
- merge obviously synonymous themes
- expand abbreviations, then merge if still obviously equivalent

The Agent must not:

- recluster papers
- invent unsupported new topics
- delete evidence
- change relevance / RCS / tier semantics

---

## Skip gate

Do not run the Agent postprocess if any of these is true:

1. `raw_theme_treemap.themes < 2`
2. all theme `value <= 1`
3. no usable `representative_titles`

Recommended trace reasons:

- `skipped_insufficient_themes`
- `skipped_noninformative_values`
- `skipped_missing_titles`

---

## Trace object

`chart_data.theme_postprocess` should support:

```json
{
  "attempted": true,
  "applied": true,
  "reason": "applied",
  "merge_count": 1,
  "model": "host-agent-manual"
}
```

Minimum fields:

- `attempted`
- `applied`
- `reason`

Optional fields:

- `merge_count`
- `model`

---

## Fail-open rule

If the Agent result is absent, skipped, invalid, or not executed:

- do **not** block report generation
- keep `theme_treemap == raw_theme_treemap`
- record the trace reason

Recommended “no result supplied yet” reason:

- `agent_postprocess_not_supplied`

---

## Minimal integration flow

```text
raw_theme_treemap generated
-> build normalized request payload
-> Agent performs one conservative label cleanup pass
-> validate result payload
-> apply refined theme_treemap
-> write theme_postprocess trace
-> re-render report
```

---

## Current non-goals

This contract does not require:

- BERTopic
- minimum cluster size rules
- external provider wiring
- host-wide callback framework
- any change to discovery / coverage / RCS logic
