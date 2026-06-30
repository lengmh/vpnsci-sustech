from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import unittest


REPO_ROOT = Path(__file__).resolve().parents[1]
QUERY_SCRIPT_PATH = REPO_ROOT / "tools" / "theme-lexicon" / "query_alias_index.py"
REVIEWED_SOURCE_PATH = REPO_ROOT / "tools" / "theme-lexicon" / "reviewed_zh_exact_aliases.json"
RUNTIME_INDEX_PATH = REPO_ROOT / "vpnsci_sustech" / "data" / "theme_concept_alias_index.json"


def load_query_module():
    spec = importlib.util.spec_from_file_location("query_alias_index", QUERY_SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


class ThemeLexiconReviewedSourceAlignmentTests(unittest.TestCase):
    def test_reviewed_zh_exact_alias_source_matches_compact_runtime_targets(self) -> None:
        query_alias_index = load_query_module()
        reviewed = json.loads(REVIEWED_SOURCE_PATH.read_text(encoding="utf-8"))["aliases"]
        runtime = json.loads(RUNTIME_INDEX_PATH.read_text(encoding="utf-8"))
        runtime_aliases = runtime["aliases"]
        curation = runtime.get("curation") or {}
        redirects = curation.get("redirects") or {}
        suppressed = set(curation.get("suppressed") or [])
        display_only = set(curation.get("display_only") or [])
        alias_redirect_sources = curation.get("alias_redirect_sources") or {}
        failures: list[tuple[str, str, str, str | None]] = []

        for row in reviewed:
            concept_id = str(row.get("concept_id") or "").strip()
            alias = str(row.get("alias_zh") or row.get("alias") or "").strip()
            if not concept_id or not alias:
                continue
            alias_key = f"zh:{query_alias_index.normalize_alias(alias)}"
            target = runtime_aliases.get(alias_key)
            redirect_source = alias_redirect_sources.get(alias_key) or {}
            is_curated_redirect = (
                redirects.get(concept_id) == target
                and redirect_source.get("source_concept_id") == concept_id
                and redirect_source.get("target_concept_id") == target
            )
            is_curated_exclusion = concept_id in suppressed or concept_id in display_only
            if target != concept_id and not is_curated_redirect and not is_curated_exclusion:
                failures.append((concept_id, str(row.get("canonical_en") or ""), alias, target))

        self.assertEqual(failures[:50], [])


if __name__ == "__main__":
    unittest.main()
