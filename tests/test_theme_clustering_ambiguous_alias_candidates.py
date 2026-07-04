from __future__ import annotations

import json
from pathlib import Path
import unittest

from tests.test_theme_clustering_compact_alias_index import load_paper_search_pro_theme_clustering
from vpnsci_sustech import theme_clustering


class ThemeClusteringAmbiguousAliasCandidateTests(unittest.TestCase):
    def _candidate_layer(self) -> dict[str, list[dict]]:
        return {
            "zh:网络攻击": [
                {
                    "concept_id": "concept:cyber_attack",
                    "canonical": {"en": "Cyber Attack", "zh": ""},
                    "domains": ["computer_science"],
                    "parents": [],
                    "specificity": 80,
                    "candidate_type": "collision_alias",
                    "risk_tags": ["semantic_neighbor", "needs_context"],
                    "evidence_aliases": [{"lang": "zh", "alias": "网络攻击"}],
                    "source_concept_id": "concept:cyber_attack",
                    "target_hint": None,
                },
                {
                    "concept_id": "concept:network_attack",
                    "canonical": {"en": "Network Attack", "zh": ""},
                    "domains": ["computer_science"],
                    "parents": [],
                    "specificity": 82,
                    "candidate_type": "collision_alias",
                    "risk_tags": ["semantic_neighbor", "needs_context"],
                    "evidence_aliases": [{"lang": "zh", "alias": "网络攻击"}],
                    "source_concept_id": "concept:network_attack",
                    "target_hint": None,
                },
            ],
            "zh:确定目标": [
                {
                    "concept_id": "concept:ambiguous_duplicate",
                    "canonical": {"en": "Ambiguous Duplicate", "zh": ""},
                    "domains": [],
                    "parents": [],
                    "specificity": 10,
                    "candidate_type": "collision_alias",
                    "risk_tags": ["needs_context"],
                    "evidence_aliases": [{"lang": "zh", "alias": "确定目标"}],
                    "source_concept_id": "concept:ambiguous_duplicate",
                    "target_hint": None,
                }
            ],
        }

    def test_missing_candidate_index_loads_as_empty_layer(self) -> None:
        missing = Path(r"F:\AI playground\TempFiles\missing_theme_ambiguous_alias_candidates.json")

        self.assertEqual(theme_clustering._load_theme_ambiguous_alias_candidates(index_path=missing), {})

    def test_matches_ambiguous_alias_only_when_deterministic_alias_does_not_already_hit(self) -> None:
        deterministic = {
            "zh:确定目标": {
                "concept_id": "concept:accepted",
                "canonical": {"en": "Accepted Target", "zh": "确定目标"},
                "specificity": 90,
            }
        }
        paper = {
            "paper_id": "p1",
            "title": "网络攻击检测与确定目标识别",
            "abstract": "本文研究网络攻击流量与恶意软件行为。",
        }

        matches = theme_clustering._ambiguous_candidate_matches(
            paper,
            paper_id="p1",
            candidate_layer=self._candidate_layer(),
            deterministic_alias_index=deterministic,
        )

        self.assertEqual([match["alias_key"] for match in matches], ["zh:网络攻击"])
        self.assertEqual(matches[0]["surface"], "网络攻击")
        self.assertEqual(matches[0]["paper_ids"], ["p1"])
        self.assertEqual(len(matches[0]["candidates"]), 2)

    def test_explicit_context_seed_can_shadow_deterministic_alias_in_low_signal_resolution(self) -> None:
        deterministic = {
            "en:agc": {
                "concept_id": "concept:agc",
                "canonical": {"en": "Agc", "zh": ""},
                "specificity": 40,
            }
        }
        candidate_layer = {
            "en:agc": [
                {
                    "concept_id": "concept:automatic_gain_control",
                    "canonical": {"en": "Automatic Gain Control", "zh": "自动增益控制"},
                    "domains": ["computer_science"],
                    "parents": [],
                    "specificity": 82,
                    "candidate_type": "explicit_context_alternative",
                    "risk_tags": ["explicit_context_seed", "needs_context"],
                    "evidence_aliases": [{"lang": "en", "alias": "AGC"}],
                    "source_concept_id": "concept:agc",
                    "resolution_group": "agc",
                    "requires_context": True,
                    "allow_deterministic_shadow": True,
                }
            ]
        }
        paper = {
            "paper_id": "p1",
            "title": "AGC loop design for radio receivers",
            "abstract": "The automatic gain control loop stabilizes receiver amplitude.",
        }

        matches = theme_clustering._ambiguous_candidate_matches(
            paper,
            paper_id="p1",
            candidate_layer=candidate_layer,
            deterministic_alias_index=deterministic,
        )

        self.assertEqual([match["alias_key"] for match in matches], ["en:agc"])
        self.assertEqual(matches[0]["candidates"][0]["concept_id"], "concept:automatic_gain_control")

    def test_loads_candidate_index_from_compact_json_shape(self) -> None:
        path = Path(r"F:\AI playground\TempFiles\theme_ambiguous_alias_fixture.json")
        path.write_text(
            json.dumps(
                {
                    "schema_version": "theme_concept_ambiguous_alias_candidates.v1",
                    "build_status": "review_complete",
                    "normalization": "theme_concept_alias_normalization.v1",
                    "candidates": self._candidate_layer(),
                },
                ensure_ascii=False,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        try:
            loaded = theme_clustering._load_theme_ambiguous_alias_candidates(index_path=path)
        finally:
            path.unlink(missing_ok=True)

        self.assertIn("zh:网络攻击", loaded)
        self.assertEqual(loaded["zh:网络攻击"][0]["concept_id"], "concept:cyber_attack")

    def test_paper_search_pro_runtime_loads_missing_candidate_index_as_empty_layer(self) -> None:
        module = load_paper_search_pro_theme_clustering()
        missing = Path(r"F:\AI playground\TempFiles\missing_tool_theme_ambiguous_alias_candidates.json")

        self.assertEqual(module._load_theme_ambiguous_alias_candidates(index_path=missing), {})


if __name__ == "__main__":
    unittest.main()
