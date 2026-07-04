from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest

from tests.temp_helpers import select_temp_parent


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "tools" / "theme-lexicon" / "build_ambiguous_alias_candidates.py"
TEMP_ROOT = Path(os.environ.get("VPNSCI_TEST_TMP", r"F:\AI playground\TempFiles"))


def load_module():
    spec = importlib.util.spec_from_file_location("build_ambiguous_alias_candidates", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )


class AmbiguousAliasCandidateBuilderTests(unittest.TestCase):
    def setUp(self) -> None:
        temp_parent = select_temp_parent(TEMP_ROOT, REPO_ROOT / "tests", REPO_ROOT)
        self.tmp = tempfile.TemporaryDirectory(dir=temp_parent)
        self.root = Path(self.tmp.name)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def _write_inputs(self) -> tuple[Path, Path, Path, Path]:
        audit = self.root / "audit.json"
        audit.write_text(
            json.dumps(
                {
                    "items": [
                        {
                            "concept_id": "concept:cyber_attack",
                            "canonical_en": "Cyber Attack",
                            "domains": ["computer_science"],
                            "primary_bucket": "redirect_candidates",
                            "categories": ["collision_or_semantic_neighbor"],
                            "sample_zh_review_rows": [
                                {
                                    "alias": "网络攻击",
                                    "decision": "blocked",
                                    "reason": "alias collision blocked until context is available",
                                }
                            ],
                        },
                        {
                            "concept_id": "concept:network_attack",
                            "canonical_en": "Network Attack",
                            "domains": ["computer_science"],
                            "primary_bucket": "needs_decision_candidates",
                            "categories": ["collision_or_semantic_neighbor"],
                            "sample_zh_review_rows": [
                                {
                                    "alias": "网络攻击",
                                    "decision": "blocked",
                                    "reason": "alias collision blocked until context is available",
                                }
                            ],
                        },
                        {
                            "concept_id": "concept:paper_set",
                            "canonical_en": "Paper Set",
                            "domains": [],
                            "primary_bucket": "topic_label_candidates",
                            "categories": ["topic_label"],
                            "sample_zh_review_rows": [
                                {"alias": "文献集合", "decision": "blocked"}
                            ],
                        },
                    ]
                },
                ensure_ascii=False,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        review = self.root / "review_decisions.jsonl"
        write_jsonl(
            review,
            [
                {
                    "lang": "zh",
                    "alias": "网络攻击",
                    "concept_id": "concept:cyber_attack",
                    "decision": "blocked",
                    "reason": "alias collision blocked until context is available",
                },
                {
                    "lang": "zh",
                    "alias": "坏主题",
                    "concept_id": "concept:network_attack",
                    "decision": "reject",
                    "reason": "bad generated topic suffix",
                },
            ],
        )
        alias_index = self.root / "theme_concept_alias_index.json"
        alias_index.write_text(
            json.dumps(
                {
                    "schema_version": "theme_concept_alias_index.v1",
                    "build_status": "review_complete",
                    "normalization": "theme_concept_alias_normalization.v1",
                    "concepts": {
                        "concept:accepted": {
                            "concept_id": "concept:accepted",
                            "canonical": {"en": "Accepted Target", "zh": "确定目标"},
                            "domains": ["computer_science"],
                            "parents": [],
                            "specificity": 90,
                        }
                    },
                    "aliases": {"zh:确定目标": "concept:accepted"},
                },
                ensure_ascii=False,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        curation = self.root / "concept_curation_decisions.json"
        curation.write_text(
            json.dumps(
                {
                    "decisions": [
                        {
                            "concept_id": "concept:paper_set",
                            "decision": "display_only",
                            "category": "topic_label_phrase",
                            "decided_at": "2026-07-02",
                            "reviewer": "test",
                            "reason": "topic label only",
                        }
                    ]
                },
                ensure_ascii=False,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        return audit, review, alias_index, curation

    def test_builds_context_resolvable_candidate_index_without_polluting_runtime_aliases(self) -> None:
        module = load_module()
        audit, review, alias_index, curation = self._write_inputs()
        output = self.root / "theme_concept_ambiguous_alias_candidates.json"
        manifest = self.root / "theme_concept_ambiguous_alias_manifest.json"

        summary = module.build_ambiguous_alias_candidates(
            audit_path=audit,
            review_decisions_path=review,
            alias_index_path=alias_index,
            curation_decisions_path=curation,
            output_path=output,
            manifest_path=manifest,
        )

        self.assertEqual(summary["candidate_aliases"], 1)
        self.assertEqual(summary["candidate_concepts"], 2)
        self.assertEqual(summary["candidate_resolvable_concepts"], 2)

        payload = json.loads(output.read_text(encoding="utf-8"))
        self.assertEqual(payload["schema_version"], "theme_concept_ambiguous_alias_candidates.v1")
        self.assertEqual(sorted(payload["candidates"]), ["zh:网络攻击"])
        self.assertEqual(
            [candidate["concept_id"] for candidate in payload["candidates"]["zh:网络攻击"]],
            ["concept:cyber_attack", "concept:network_attack"],
        )
        self.assertTrue(
            all("needs_context" in candidate["risk_tags"] for candidate in payload["candidates"]["zh:网络攻击"])
        )

        written_manifest = json.loads(manifest.read_text(encoding="utf-8"))
        self.assertEqual(written_manifest["coverage"]["candidate_resolvable_concepts"], 2)
        self.assertEqual(written_manifest["risk_tag_counts"]["needs_context"], 2)

    def test_explicit_context_seeds_target_canonical_concepts_without_accepting_aliases(self) -> None:
        module = load_module()
        audit, review, alias_index, curation = self._write_inputs()
        context_seeds = self.root / "contextual_alias_resolution_seeds.json"
        context_seeds.write_text(
            json.dumps(
                {
                    "schema_version": "theme_concept_contextual_alias_seeds.v1",
                    "seeds": [
                        {
                            "alias": "AGC",
                            "target_concept_id": "concept:automatic_gain_control",
                            "source_concept_id": "concept:agc",
                            "canonical_en": "AGC",
                            "resolution_group": "agc",
                            "candidate_type": "explicit_context_alternative",
                            "risk_tags": ["acronym_or_short_label"],
                            "reason": "AGC is only safe when paper context supports automatic gain control.",
                        },
                        {
                            "alias": "Paper Set",
                            "target_concept_id": "concept:paper_set",
                            "source_concept_id": "concept:paper_set",
                            "resolution_group": "paper_set",
                            "reason": "excluded display-only concepts must not re-enter candidate runtime.",
                        }
                    ],
                },
                ensure_ascii=False,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        alias_payload = json.loads(alias_index.read_text(encoding="utf-8"))
        alias_payload["concepts"]["concept:automatic_gain_control"] = {
            "concept_id": "concept:automatic_gain_control",
            "canonical": {"en": "Automatic Gain Control", "zh": "自动增益控制"},
            "domains": ["computer_science"],
            "parents": [],
            "specificity": 82,
        }
        alias_payload["concepts"]["concept:agc"] = {
            "concept_id": "concept:agc",
            "canonical": {"en": "Agc", "zh": ""},
            "domains": ["computer_science"],
            "parents": [],
            "specificity": 40,
        }
        alias_payload["aliases"]["en:agc"] = "concept:agc"
        alias_index.write_text(json.dumps(alias_payload, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
        output = self.root / "theme_concept_ambiguous_alias_candidates.json"
        manifest = self.root / "theme_concept_ambiguous_alias_manifest.json"

        summary = module.build_ambiguous_alias_candidates(
            audit_path=audit,
            review_decisions_path=review,
            alias_index_path=alias_index,
            curation_decisions_path=curation,
            context_seeds_path=context_seeds,
            output_path=output,
            manifest_path=manifest,
        )

        self.assertEqual(summary["candidate_source_counts"]["explicit_context_seed"], 1)
        payload = json.loads(output.read_text(encoding="utf-8"))
        seeded = payload["candidates"]["en:agc"][0]
        self.assertEqual(seeded["concept_id"], "concept:automatic_gain_control")
        self.assertEqual(seeded["canonical"]["en"], "AGC")
        self.assertEqual(seeded["source_concept_id"], "concept:agc")
        self.assertEqual(seeded["resolution_group"], "agc")
        self.assertTrue(seeded["requires_context"])
        self.assertTrue(seeded["allow_deterministic_shadow"])
        self.assertIn("needs_context", seeded["risk_tags"])
        self.assertIn("explicit_context_seed", seeded["risk_tags"])


if __name__ == "__main__":
    unittest.main()
