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

For ambiguous concept coverage, the same report families also share
`theme_candidate_resolution_request.json` / `theme_candidate_resolution_result.json`.
That step runs before label postprocess and only when deterministic treemap
signal is missing or insufficient.

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
- `chart_data.theme_candidate_resolution`
- `chart_data.theme_postprocess`

Semantics:

- `raw_theme_treemap`: raw deterministic theme signal
- `theme_treemap`: refined display layer; may include evidence-backed
  host-resolved ambiguous candidates
- `theme_candidate_resolution`: trace of whether ambiguous candidates were
  requested/applied
- `theme_postprocess`: trace of whether an Agent refinement was applied

---

## Ambiguous Candidate Resolution

This is a formal treemap input path, not a shadow audit path.

Trigger it only when deterministic `raw_theme_treemap` / `theme_treemap` has
no hit or insufficient hit. Do not call it when deterministic themes are already
good enough.

Request artifact:

```text
theme_candidate_resolution_request.json
```

Result artifact:

```text
theme_candidate_resolution_result.json
```

Host Agent rules:

- resolve only with direct evidence from display query, title, abstract, or keywords;
- return `unresolved` when evidence is weak or missing;
- never rewrite deterministic alias runtime;
- never globally merge concepts;
- resolved candidates enter only this report's `theme_treemap`.
- explicit context seeds may include `allow_deterministic_shadow = true`; that only
  means low-signal candidate resolution can reconsider an otherwise deterministic
  surface, not that the alias becomes globally ambiguous.

Resolved result items must include:

- `decision = "resolved"`
- `alias_key`
- `concept_id` from the request candidate list
- `paper_ids` subset of the request paper ids for that alias
- non-empty `evidence`

Unresolved or invalid items remain trace-only and do not enter the main treemap.

Candidate entries may include `source_concept_id`, `target_hint`,
`resolution_group`, `requires_context`, `allow_deterministic_shadow`, and
`evidence_aliases`. The Host Agent must choose a `concept_id` from the request
candidate list, normally the `target_concept_id` already materialized as
`concept_id`, rather than inventing a new concept or globally merging sources.

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
-> if no-hit / insufficient-hit: build ambiguous candidate resolution request
-> Agent resolves candidates with evidence, or returns unresolved
-> Python applies resolved candidates into theme_treemap
-> build normalized request payload
-> Agent performs one conservative label cleanup pass
-> validate result payload
-> apply refined theme_treemap
-> write theme_postprocess trace
-> re-render report
```

The formal host-Agent handoff target for all three report families is:

```text
start_report_from_session(...)
-> status = theme_postprocess_required
-> host Agent reads request artifact or get_theme_postprocess_request(...)
-> host Agent writes normalized result
-> apply_theme_postprocess_result(...)
-> final HTML rendered
```

Current rollout truth:

- built-in `seed_preview` / recovery already use this direction as the formal mainline;
- `full` is also now in scope for the same automatic host-Agent coverage and should no longer be documented as “contract-only forever”.

---

## Current non-goals

This contract does not require:

- BERTopic
- minimum cluster size rules
- external provider wiring
- host-wide callback framework
- any change to discovery / coverage / RCS logic
