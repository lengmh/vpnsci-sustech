# Theme Lexicon Maintenance — Developer / Agent Contract

## Purpose

The report theme fallback uses a small Chinese lexicon to keep deterministic
title/abstract theme extraction from degrading into generic word-frequency
labels.

This lexicon is **not** a subject ontology and **not** a query-specific taxonomy.
It only supports rule-based extraction decisions such as:

- reject generic single terms;
- penalize connector / function words;
- identify phrase shapes that look like usable topic labels.

## Files

Keep these copies aligned:

- repo package copy:
  - `vpnsci_sustech/data/theme_lexicon.zh.json`
  - `vpnsci_sustech/data/theme_lexicon.en.json`
- bundled `paper-search-pro` runtime copy:
  - `tools/paper-search-pro/assets/theme_lexicon.zh.json`
  - `tools/paper-search-pro/assets/theme_lexicon.en.json`

The tool-local copy exists because bundled `paper-search-pro` scripts must be
able to run without importing `vpnsci_sustech.*`.

## Chinese lexicon sections

```json
{
  "generic_terms": [],
  "connector_terms": [],
  "theme_shape_suffixes": [],
  "noise_substrings": [],
  "fragment_prefixes": [],
  "embedded_suffix_connectors": []
}
```

Semantics:

- `generic_terms`: terms that should not become standalone themes.
- `connector_terms`: linking/function terms used for trimming and specificity penalties.
- `theme_shape_suffixes`: phrase endings that help identify a candidate as a
  topic-shaped label. These are label-shape hints, not a domain database.
- `noise_substrings`: venue/school/publication metadata noise.
- `fragment_prefixes`: likely broken n-gram starts.
- `embedded_suffix_connectors`: connectors after an internal suffix that make a
  long candidate look like a sentence fragment rather than a label.

## English lexicon sections

```json
{
  "token_stopwords": [],
  "generic_label_terms": []
}
```

Semantics:

- `token_stopwords`: token-level stopwords removed before candidate generation.
- `generic_label_terms`: terms rejected as standalone display themes. They may
  still appear inside more specific multi-word phrases when at least one token
  is not generic.

## Deterministic boundary

The production decision is:

```text
current paper text + lexicon + deterministic scoring/gate
```

The fallback must not depend on an Agent or LLM to decide whether a theme signal
is reliable. If deterministic scoring finds no reliable theme signal, it should
return:

```json
{
  "themes": [],
  "status": "insufficient_text_theme_signal"
}
```

The optional host-Agent postprocess may polish or merge display labels only after
raw themes exist. It must not invent new themes or override a low-signal gate.

## Example direction: concept alias overlay

If the observed problem is mixed Chinese/English synonyms, do not solve it by
adding more stopwords or by importing a broad subject taxonomy as the main
decision layer.

The intended direction is a reviewed **concept alias pipeline**. Runtime now uses
a compact alias index plus manifest:

```json
{
  "schema_version": "theme_concept_alias_index.v1",
  "concepts": {
    "comm:channel_estimation": {
      "concept_id": "comm:channel_estimation",
      "canonical": {"en": "Channel Estimation", "zh": "信道估计"},
      "domains": ["communications", "signal_processing"],
      "parents": [],
      "specificity": 80
    }
  },
  "aliases": {
    "en:channel estimation": "comm:channel_estimation",
    "en:csi estimation": "comm:channel_estimation",
    "zh:信道估计": "comm:channel_estimation"
  }
}
```

Host Agents should inspect `theme_concept_alias_manifest.json` or use
`tools/theme-lexicon/query_alias_index.py` / `summarize_alias_runtime.py`.
Do not open the legacy full `theme_concept_aliases.json` as a default working
surface; it may exist only for rollback or explicitly requested audit cleanup.

The alias overlay is alias-only. Stopwords, connectors, generic terms, and
fragment rules remain in `theme_lexicon.zh.json` / `theme_lexicon.en.json`.

Expected deterministic flow:

1. Extract candidate phrases from titles/abstracts.
2. Match candidates against `concept_aliases`.
3. Merge all matched aliases into the same `concept_id`.
   - Example: `无线通信`, `wireless communication`, and
     `wireless communications` should count as one concept.
4. Sort concept-level groups by merged paper coverage and specificity.
5. Send unmatched candidates through the normal balanced fallback path.
6. Keep raw candidates auditable; apply display quality gates separately.

External taxonomies such as IEEE Taxonomy, CSO, PhySH, MSC2020, arXiv
categories, or MeSH/UMLS may be used as references for canonical labels or
Agent-suggested maintenance, but they should not replace the accepted alias
overlay or silently become a bundled query-specific ontology.

## User-triggered lexicon update flow

Trigger phrase examples:

- `请基于这个 search session 检查主题词表`
- `检查这个报告的主题词表是否需要更新`
- `基于这次搜索结果建议 theme lexicon 更新`

Required flow:

1. Read the search/report artifacts:
   - `paper_list.json` or seed/session hits;
   - `chart_data.raw_theme_treemap` / `chart_data.theme_treemap`;
   - candidate bad labels or `insufficient_text_theme_signal` status.
2. Explain the observed problem with concrete labels and source titles/abstract snippets.
3. Propose lexicon changes as a diff-style list grouped by section.
4. State why each entry is generic/connector/shape/noise, and why it is not a
   query-specific topic injection.
5. If the problem is mixed-language synonyms, propose a
   reviewed alias-pipeline recommendation / compact alias-index update instead of a stopword diff.
6. Wait for explicit user confirmation before editing lexicon JSON.
7. Apply negative-lexicon updates to both package/tool lexicon copies; apply
   alias updates to the reviewed alias overlay.
8. Validate alias collisions before promotion.
9. Add or update a regression test using a small fixture.
10. Re-run targeted tests and regenerate the representative report if requested.

## Guardrails

Allowed:

- add broad Chinese academic/reporting noise terms;
- add connector/function words;
- add general topic-shape suffixes such as `机制` or `剂量学`;
- add small regression fixtures that preserve the observed failure.

Not allowed:

- add a fixed theme taxonomy for one user query;
- add all good candidate labels from one report as `theme_shape_suffixes`;
- silently rewrite report themes without changing deterministic inputs;
- let the Agent decide that low-signal themes are reliable.

## Review checklist

Before claiming a lexicon update is complete:

- package and tool-runtime lexicon copies are identical in relevant sections;
- no query-specific taxonomy was introduced;
- low-signal reports still keep the theme module visible but explicit;
- targeted tests pass with `uv run python -m unittest ...`;
- if HTML was regenerated through MCP/local runtime, the runtime copy was refreshed
  or the user was told to restart/reload the MCP session.
