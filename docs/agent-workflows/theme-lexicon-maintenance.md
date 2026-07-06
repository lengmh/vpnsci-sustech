# Theme Lexicon Maintenance — Developer / Agent Contract

## Purpose

The report theme fallback has two deterministic maintenance surfaces:

1. a small negative/theme-shape lexicon that keeps title/abstract extraction from
   degrading into generic word-frequency labels;
2. a reviewed concept-alias runtime that merges equivalent Chinese/English
   labels into stable `concept_id` groups.

Neither surface is a query-specific taxonomy. The negative lexicon supports
rule-based extraction decisions such as:

- reject generic single terms;
- penalize connector / function words;
- identify phrase shapes that look like usable topic labels.

## Files

Keep these copies aligned:

Negative/theme-shape lexicon copies:

- repo package copy:
  - `vpnsci_sustech/data/theme_lexicon.zh.json`
  - `vpnsci_sustech/data/theme_lexicon.en.json`
- bundled `paper-search-pro` runtime copy:
  - `tools/paper-search-pro/assets/theme_lexicon.zh.json`
  - `tools/paper-search-pro/assets/theme_lexicon.en.json`

The tool-local copy exists because bundled `paper-search-pro` scripts must be
able to run without importing `vpnsci_sustech.*`.

Concept-alias runtime copies:

- repo package copy:
  - `vpnsci_sustech/data/theme_concept_alias_index.json`
  - `vpnsci_sustech/data/theme_concept_alias_manifest.json`
  - `vpnsci_sustech/data/theme_concept_ambiguous_alias_candidates.json`
  - `vpnsci_sustech/data/theme_concept_ambiguous_alias_manifest.json`
- bundled `paper-search-pro` runtime copy:
  - `tools/paper-search-pro/assets/theme_concept_alias_index.json`
  - `tools/paper-search-pro/assets/theme_concept_alias_manifest.json`
  - `tools/paper-search-pro/assets/theme_concept_ambiguous_alias_candidates.json`
  - `tools/paper-search-pro/assets/theme_concept_ambiguous_alias_manifest.json`

`theme_concept_alias_index.json` is the current deterministic runtime source of
truth. `theme_concept_alias_manifest.json` is the preferred audit surface for
counts, coverage, hashes, and conflict status.

The legacy full overlay files:

- `vpnsci_sustech/data/theme_concept_aliases.json`
- `tools/paper-search-pro/assets/theme_concept_aliases.json`

are retained only for rollback / explicit cleanup audit. Runtime loaders must
not silently fall back to them when the compact index is missing.

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

## Concept Alias Runtime

If the observed problem is mixed Chinese/English synonyms, do not solve it by
adding more stopwords or by importing a broad subject taxonomy as the main
decision layer.

The accepted direction is a reviewed **concept alias pipeline**. Runtime uses a
compact alias index plus manifest:

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

The deterministic alias runtime is alias-only. Stopwords, connectors, generic
terms, and fragment rules remain in `theme_lexicon.zh.json` /
`theme_lexicon.en.json`.

Expected deterministic flow:

1. Extract candidate phrases from titles/abstracts.
2. Match candidates against `theme_concept_alias_index.json`.
3. Merge all matched aliases into the same `concept_id`.
   - Example: `无线通信`, `wireless communication`, and
     `wireless communications` should count as one concept.
4. Sort concept-level groups by merged paper coverage and specificity.
5. Send unmatched candidates through the normal balanced fallback path.
6. Keep raw candidates auditable; apply display quality gates separately.

The compact index must have:

- `schema_version = theme_concept_alias_index.v1`;
- `normalization = theme_concept_alias_normalization.v1`;
- `build_status = review_complete`.

Unsupported schema/status is a hard error. Do not silently continue with stale
or partial runtime data.

## Ambiguous Candidate Layer

`theme_concept_ambiguous_alias_candidates.json` is a separate reviewed candidate
surface for report-local host-Agent resolution. It exists for aliases that are
too ambiguous to become deterministic runtime aliases but can sometimes be
resolved from the current report's title/abstract/query evidence.

Rules:

- ambiguous candidates do not increase deterministic runtime coverage;
- ambiguous candidates must not be promoted into accepted aliases without the
  normal alias review/materialization flow;
- host-Agent results may only choose a candidate `concept_id` already supplied
  in the request;
- resolved candidates affect only the current report's `theme_treemap`;
- unresolved candidates remain trace-only.

The ambiguous candidate files must have:

- `schema_version = theme_concept_ambiguous_alias_candidates.v1`;
- `normalization = theme_concept_alias_normalization.v1`;
- `build_status = review_complete`.

Unsupported schema/status is also a hard error.

External taxonomies such as IEEE Taxonomy, CSO, PhySH, MSC2020, arXiv
categories, or MeSH/UMLS may be used as references for canonical labels or
Agent-suggested maintenance, but they should not replace the accepted alias
runtime or silently become a bundled query-specific ontology.

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
5. If the problem is mixed-language synonyms, propose a reviewed
   alias-pipeline recommendation / compact alias-index update instead of a
   stopword diff. If the alias is genuinely ambiguous, propose an ambiguous
   candidate / context-seed update instead of a deterministic alias.
6. Wait for explicit user confirmation before editing lexicon JSON.
7. Apply negative-lexicon updates to both package/tool lexicon copies; apply
   alias updates through the reviewed alias pipeline, then materialize the
   compact runtime and manifest copies.
8. Validate alias collisions before promotion. Keep unresolved collisions
   blocked or ambiguous-candidate-only; do not auto-merge concepts.
9. Add or update a regression test using a small fixture.
10. Re-run targeted tests and regenerate the representative report if requested.

## Guardrails

Allowed:

- add broad Chinese academic/reporting noise terms;
- add connector/function words;
- add general topic-shape suffixes such as `机制` or `剂量学`;
- add small regression fixtures that preserve the observed failure.
- add exact/domain-aware aliases through reviewed alias decisions;
- add curation redirects / canonical display overrides when the target is
  evidence-backed and validation keeps conflicts at zero;
- add ambiguous candidate context seeds when the alias needs report-local
  evidence rather than global deterministic activation.

Not allowed:

- add a fixed theme taxonomy for one user query;
- add all good candidate labels from one report as `theme_shape_suffixes`;
- silently rewrite report themes without changing deterministic inputs;
- let the Agent decide that low-signal themes are reliable.
- make low-confidence compositional candidates accepted runtime aliases by
  blanket rule;
- auto-merge unresolved alias collisions;
- promote ambiguous candidate outputs into global runtime aliases without review.

## Review checklist

Before claiming a lexicon update is complete:

- package and tool-runtime lexicon copies are identical in relevant sections;
- package/tool compact alias index and manifest are byte-identical;
- package/tool ambiguous candidate index and manifest are byte-identical when
  that layer changes;
- compact alias index and ambiguous candidate files have supported schema,
  normalization, and `review_complete` status;
- `summarize_alias_runtime.py` reports zero accepted/runtime conflicts, zero
  runtime alias conflicts, and zero pollution-audit hits;
- no query-specific taxonomy was introduced;
- low-signal reports still keep the theme module visible but explicit;
- targeted tests pass with `uv run pytest ...`;
- if HTML was regenerated through MCP/local runtime, the runtime copy was refreshed
  or the user was told to restart/reload the MCP session.
