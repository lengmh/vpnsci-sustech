from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest

from tests.temp_helpers import select_temp_parent


REPO_ROOT = Path(__file__).resolve().parents[1]
TEMP_ROOT = Path(os.environ.get("VPNSCI_TEST_TMP", r"F:\AI playground\TempFiles"))


def load_script(name: str):
    script_path = REPO_ROOT / "tools" / "theme-lexicon" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, script_path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


class ThemeLexiconPollutionGuardTests(unittest.TestCase):
    def setUp(self) -> None:
        temp_parent = select_temp_parent(TEMP_ROOT, REPO_ROOT / "tests", REPO_ROOT)
        self.tmp = tempfile.TemporaryDirectory(dir=temp_parent)
        self.root = Path(self.tmp.name)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_build_en_concepts_skips_external_identifier_records_and_aliases(self) -> None:
        build_en_concepts = load_script("build_en_concepts")
        normalized = self.root / "normalized"
        output = self.root / "builds"
        write_jsonl(
            normalized / "cso_terms.jsonl",
            [
                {"source": "cso", "source_id": "cso:101833716", "label": "101833716", "aliases": [], "domains": ["computer_science"]},
                {"source": "cso", "source_id": "cso:m_02y_3vt", "label": "m.02y 3vt", "aliases": [], "domains": ["computer_science"]},
                {"source": "cso", "source_id": "cso:bad_literal", "label": "bad literal@en .", "aliases": [], "domains": ["computer_science"]},
                {"source": "cso", "source_id": "cso:valid", "label": "channel estimation", "aliases": ["101833716", "m.02y 3vt", "CSI estimation"], "domains": ["computer_science"]},
            ],
        )

        build_en_concepts.build_en_concepts(
            normalized_dir=normalized,
            output_dir=output,
            sources=[("cso", "02_cso_en_concepts.jsonl")],
        )

        concepts = read_jsonl(output / "merged_en_concept_candidates.jsonl")
        labels = json.dumps(concepts, ensure_ascii=False)
        self.assertIn("channel estimation", labels)
        self.assertIn("CSI estimation", labels)
        self.assertNotIn("101833716", labels)
        self.assertNotIn("m.02y 3vt", labels)
        self.assertNotIn("bad literal@en", labels)

    def test_validate_alias_overlay_rejects_identifier_aliases_and_uses_manifest_batches(self) -> None:
        validate_alias_overlay = load_script("validate_alias_overlay")
        candidates = self.root / "candidates"
        review = self.root / "review"
        active = candidates / "zh_alias_candidates.batch-001.jsonl"
        stale = candidates / "zh_alias_candidates.batch-999.jsonl"
        write_jsonl(
            active,
            [
                {
                    "concept_id": "concept:valid",
                    "canonical_en": "channel estimation",
                    "aliases_en": ["101833716", "m.02y 3vt", "bad literal@en .", "https://example.test/id"],
                    "domains": ["computer_science"],
                    "zh_alias_candidates": [{"alias": "信道估计"}],
                }
            ],
        )
        write_jsonl(
            stale,
            [
                {
                    "concept_id": "concept:stale",
                    "canonical_en": "999999",
                    "aliases_en": [],
                    "domains": ["computer_science"],
                    "zh_alias_candidates": [],
                }
            ],
        )
        (candidates / "zh_alias_candidate_manifest.json").write_text(
            json.dumps({"batches": [{"output": str(active)}]}, ensure_ascii=False),
            encoding="utf-8",
        )

        validate_alias_overlay.validate_alias_overlay(candidate_dir=candidates, output_dir=review, repo_root=REPO_ROOT)

        decisions = read_jsonl(review / "review_decisions.jsonl")
        by_alias = {row["alias"]: row["decision"] for row in decisions}
        self.assertEqual(by_alias["channel estimation"], "accept")
        self.assertEqual(by_alias["101833716"], "reject")
        self.assertEqual(by_alias["m.02y 3vt"], "reject")
        self.assertEqual(by_alias["bad literal@en ."], "reject")
        self.assertEqual(by_alias["https://example.test/id"], "reject")
        self.assertEqual(by_alias["信道估计"], "needs_review")
        self.assertNotIn("999999", by_alias)

    def test_validate_alias_overlay_keeps_biomedical_suffix_candidates_review_gated(self) -> None:
        validate_alias_overlay = load_script("validate_alias_overlay")
        candidates = self.root / "candidates"
        review = self.root / "review"
        active = candidates / "zh_alias_candidates.batch-001.jsonl"
        write_jsonl(
            active,
            [
                {
                    "concept_id": "concept:bradykinin_b1_receptor_antagonist",
                    "canonical_en": "Bradykinin B1 Receptor Antagonists",
                    "aliases_en": [],
                    "domains": ["biomedical", "chemicals_and_drugs"],
                    "zh_alias_candidates": [
                        {
                            "alias": "缓激肽B1受体拮抗剂",
                            "confidence": "medium",
                            "source": "agent_biomedical_named_class_suffix",
                            "status": "candidate",
                        }
                    ],
                }
            ],
        )
        (candidates / "zh_alias_candidate_manifest.json").write_text(
            json.dumps({"batches": [{"output": str(active)}]}, ensure_ascii=False),
            encoding="utf-8",
        )

        validate_alias_overlay.validate_alias_overlay(candidate_dir=candidates, output_dir=review, repo_root=REPO_ROOT)

        decisions = read_jsonl(review / "review_decisions.jsonl")
        row = next(item for item in decisions if item["alias"] == "缓激肽B1受体拮抗剂")
        self.assertEqual(row["decision"], "needs_review")
        self.assertEqual(row["review_tier"], "needs_review")

    def test_materialize_runtime_overlay_uses_only_accepted_aliases_and_no_local_paths(self) -> None:
        materialize_runtime_overlay = load_script("materialize_runtime_overlay")
        concepts = self.root / "merged_en_concept_candidates.jsonl"
        review = self.root / "review_decisions.jsonl"
        out1 = self.root / "runtime1.json"
        out2 = self.root / "runtime2.json"
        write_jsonl(
            concepts,
            [
                {
                    "concept_id": "concept:acute_abdomen",
                    "canonical": {"en": "Abdomen, Acute", "zh": None},
                    "aliases": {"en": ["Abdomen, Acute", "Acute Abdomen"], "zh": []},
                    "domains": ["biomedical"],
                    "parents": ["concept:abdomen"],
                    "specificity": 50,
                    "source_refs": [{"source": "mesh", "source_id": "mesh:D000006", "label": "Abdomen, Acute", "path": ["raw"]}],
                },
                {
                    "concept_id": "concept:wireless",
                    "canonical": {"en": "Wireless Communication", "zh": None},
                    "aliases": {"en": ["Wireless Communication"], "zh": []},
                    "domains": ["communications"],
                    "parents": [],
                    "specificity": 80,
                    "source_refs": [{"source": "ieee_taxonomy", "label": "Wireless Communication"}],
                },
                {
                    "concept_id": "concept:wireless_dup",
                    "canonical": {"en": "Wireless Communication", "zh": None},
                    "aliases": {"en": ["Wireless Communication"], "zh": []},
                    "domains": ["computer_science"],
                    "parents": [],
                    "specificity": 70,
                    "source_refs": [{"source": "cso", "label": "Wireless Communication"}],
                },
            ],
        )
        write_jsonl(
            review,
            [
                {"concept_id": "concept:acute_abdomen", "alias": "Abdomen, Acute", "lang": "en", "decision": "reject"},
                {"concept_id": "concept:acute_abdomen", "alias": "Acute Abdomen", "lang": "en", "decision": "accept"},
                {"concept_id": "concept:acute_abdomen", "alias": "急腹症", "lang": "zh", "decision": "accept"},
                {"concept_id": "concept:wireless", "alias": "wireless communication", "lang": "en", "decision": "accept"},
                {"concept_id": "concept:wireless_dup", "alias": "wireless communication", "lang": "en", "decision": "accept"},
                {"concept_id": "concept:wireless", "alias": "无线通信", "lang": "zh", "decision": "needs_review"},
            ],
        )

        summary = materialize_runtime_overlay.materialize_runtime_overlay(
            concepts_path=concepts,
            review_decisions_path=review,
            outputs=[out1, out2],
        )

        self.assertEqual(summary["skipped_accepted_alias_conflicts"], 1)
        self.assertEqual(out1.read_bytes(), out2.read_bytes())
        payload = json.loads(out1.read_text(encoding="utf-8"))
        self.assertNotIn("concept_source", payload)
        self.assertNotIn("review_decisions", payload)
        self.assertEqual(payload["skipped_accepted_alias_conflict_count"], 1)
        self.assertNotIn("skipped_accepted_alias_conflicts", payload)
        text = json.dumps(payload, ensure_ascii=False)
        self.assertNotIn(str(self.root), text)
        entries = {entry["concept_id"]: entry for entry in payload["concept_aliases"]}
        self.assertEqual(entries["concept:acute_abdomen"]["canonical"]["en"], "Acute Abdomen")
        self.assertEqual(entries["concept:acute_abdomen"]["canonical"]["zh"], "急腹症")
        self.assertNotIn("Abdomen, Acute", entries["concept:acute_abdomen"]["aliases"]["en"])
        self.assertNotIn("concept:wireless", entries)
        self.assertNotIn("concept:wireless_dup", entries)
        self.assertEqual(
            set(entries["concept:acute_abdomen"]["source_refs"][0]),
            {"source", "source_id", "label"},
        )

    def test_validate_alias_overlay_blocks_mixed_fallback_and_collision_aliases(self) -> None:
        validate_alias_overlay = load_script("validate_alias_overlay")
        candidates = self.root / "candidates"
        review = self.root / "review"
        active = candidates / "zh_alias_candidates.batch-001.jsonl"
        write_jsonl(
            active,
            [
                {
                    "concept_id": "concept:bad_mixed",
                    "canonical_en": "Unmapped Injury Scale",
                    "aliases_en": [],
                    "domains": ["biomedical"],
                    "zh_alias_candidates": [
                        {
                            "alias": "Unmapped损伤量表",
                            "confidence": "low",
                            "source": "agent_review_gated_mixed_fallback",
                        }
                    ],
                },
                {
                    "concept_id": "concept:collision_a",
                    "canonical_en": "Analytical Hierarchy Process",
                    "aliases_en": [],
                    "domains": ["computer_science"],
                    "zh_alias_candidates": [{"alias": "层次分析法", "source": "agent_exact_glossary"}],
                },
                {
                    "concept_id": "concept:collision_b",
                    "canonical_en": "Analytic Hierarchy Process",
                    "aliases_en": [],
                    "domains": ["computer_science"],
                    "zh_alias_candidates": [{"alias": "层次分析法", "source": "agent_exact_glossary"}],
                },
            ],
        )
        (candidates / "zh_alias_candidate_manifest.json").write_text(
            json.dumps({"batches": [{"output": str(active)}]}, ensure_ascii=False),
            encoding="utf-8",
        )

        validate_alias_overlay.validate_alias_overlay(candidate_dir=candidates, output_dir=review, repo_root=REPO_ROOT)

        decisions = read_jsonl(review / "review_decisions.jsonl")
        by_key = {(row["concept_id"], row["alias"]): row for row in decisions if row["lang"] == "zh"}
        self.assertEqual(by_key[("concept:bad_mixed", "Unmapped损伤量表")]["decision"], "blocked")
        self.assertIn("low-confidence mixed", by_key[("concept:bad_mixed", "Unmapped损伤量表")]["reason"])
        self.assertEqual(by_key[("concept:collision_a", "层次分析法")]["decision"], "blocked")
        self.assertEqual(by_key[("concept:collision_b", "层次分析法")]["decision"], "blocked")

    def test_validate_alias_overlay_blocks_english_heavy_chinese_candidates(self) -> None:
        validate_alias_overlay = load_script("validate_alias_overlay")
        candidates = self.root / "candidates"
        review = self.root / "review"
        active = candidates / "zh_alias_candidates.batch-001.jsonl"
        write_jsonl(
            active,
            [
                {
                    "concept_id": "concept:english_heavy",
                    "canonical_en": "Amplified Fragment Length Polymorphism Analysis",
                    "aliases_en": [],
                    "domains": ["biomedical"],
                    "zh_alias_candidates": [
                        {
                            "alias": "Amplified Fragment Length Polymorphism分析",
                            "confidence": "medium",
                            "source": "agent_mixed_class_suffix",
                        }
                    ],
                },
                {
                    "concept_id": "concept:acronym_ok",
                    "canonical_en": "Covid-19 Nucleic Acid Testing",
                    "aliases_en": [],
                    "domains": ["biomedical"],
                    "zh_alias_candidates": [
                        {
                            "alias": "COVID-19核酸测试",
                            "confidence": "medium",
                            "source": "agent_mixed_class_suffix",
                        }
                    ],
                },
            ],
        )
        (candidates / "zh_alias_candidate_manifest.json").write_text(
            json.dumps({"batches": [{"output": str(active)}]}, ensure_ascii=False),
            encoding="utf-8",
        )

        validate_alias_overlay.validate_alias_overlay(candidate_dir=candidates, output_dir=review, repo_root=REPO_ROOT)

        decisions = read_jsonl(review / "review_decisions.jsonl")
        by_key = {(row["concept_id"], row["alias"]): row for row in decisions if row["lang"] == "zh"}
        self.assertEqual(
            by_key[("concept:english_heavy", "Amplified Fragment Length Polymorphism分析")]["decision"],
            "blocked",
        )
        self.assertIn(
            "three or more ordinary English words",
            by_key[("concept:english_heavy", "Amplified Fragment Length Polymorphism分析")]["reason"],
        )
        self.assertEqual(by_key[("concept:acronym_ok", "COVID-19核酸测试")]["decision"], "needs_review")

    def test_validate_alias_overlay_blocks_single_ordinary_english_residue(self) -> None:
        validate_alias_overlay = load_script("validate_alias_overlay")
        candidates = self.root / "candidates"
        review = self.root / "review"
        active = candidates / "zh_alias_candidates.batch-001.jsonl"
        write_jsonl(
            active,
            [
                {
                    "concept_id": "concept:bad_one_word_residue",
                    "canonical_en": "Knapsack Problem",
                    "aliases_en": [],
                    "domains": ["computer_science"],
                    "zh_alias_candidates": [
                        {
                            "alias": "Knapsack问题",
                            "confidence": "medium",
                            "source": "agent_compositional_glossary",
                        }
                    ],
                },
                {
                    "concept_id": "concept:exact_proper_name_ok_for_review",
                    "canonical_en": "Petri Net",
                    "aliases_en": [],
                    "domains": ["computer_science"],
                    "zh_alias_candidates": [
                        {
                            "alias": "Petri网",
                            "confidence": "high",
                            "source": "agent_exact_glossary",
                        }
                    ],
                },
            ],
        )
        (candidates / "zh_alias_candidate_manifest.json").write_text(
            json.dumps({"batches": [{"output": str(active)}]}, ensure_ascii=False),
            encoding="utf-8",
        )

        validate_alias_overlay.validate_alias_overlay(candidate_dir=candidates, output_dir=review, repo_root=REPO_ROOT)

        decisions = read_jsonl(review / "review_decisions.jsonl")
        by_key = {(row["concept_id"], row["alias"]): row for row in decisions if row["lang"] == "zh"}
        self.assertEqual(by_key[("concept:bad_one_word_residue", "Knapsack问题")]["decision"], "blocked")
        self.assertIn(
            "ordinary untranslated English residue",
            by_key[("concept:bad_one_word_residue", "Knapsack问题")]["reason"],
        )
        self.assertEqual(by_key[("concept:exact_proper_name_ok_for_review", "Petri网")]["decision"], "needs_review")

    def test_fill_zh_alias_candidates_skips_non_exact_ordinary_english_residue(self) -> None:
        fill_zh_alias_candidates = load_script("fill_zh_alias_candidates")
        candidates = self.root / "candidates"
        active = candidates / "zh_alias_candidates.batch-001.jsonl"
        write_jsonl(
            active,
            [
                {
                    "concept_id": "concept:covariance_matrix_adaptation",
                    "canonical_en": "Covariance Matrix Adaptation",
                    "aliases_en": [],
                    "domains": ["computer_science"],
                    "source_refs": [{"source": "cso", "label": "Covariance Matrix Adaptation"}],
                    "max_zh_alias_candidates": 3,
                    "candidate_generation_status": "pending_host_agent",
                    "zh_alias_candidates": [],
                },
                {
                    "concept_id": "concept:petri_net",
                    "canonical_en": "Petri Net",
                    "aliases_en": [],
                    "domains": ["computer_science"],
                    "source_refs": [{"source": "cso", "label": "Petri Net"}],
                    "max_zh_alias_candidates": 3,
                    "candidate_generation_status": "pending_host_agent",
                    "zh_alias_candidates": [],
                },
            ],
        )
        (candidates / "zh_alias_candidate_manifest.json").write_text(
            json.dumps({"batches": [{"output": str(active)}]}, ensure_ascii=False),
            encoding="utf-8",
        )

        fill_zh_alias_candidates.fill_zh_alias_candidates(candidate_dir=candidates)

        rows = {row["concept_id"]: row for row in read_jsonl(active)}
        self.assertEqual(
            rows["concept:covariance_matrix_adaptation"]["zh_alias_candidates"][0]["alias"],
            "协方差矩阵适应",
        )
        self.assertEqual(rows["concept:petri_net"]["zh_alias_candidates"][0]["alias"], "Petri网")


if __name__ == "__main__":
    unittest.main()
