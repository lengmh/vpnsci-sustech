from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest

from tests.temp_helpers import select_temp_parent


REPO_ROOT = Path(__file__).resolve().parents[1]
MATERIALIZE_SCRIPT_PATH = REPO_ROOT / "tools" / "theme-lexicon" / "materialize_runtime_overlay.py"
VALIDATE_SCRIPT_PATH = REPO_ROOT / "tools" / "theme-lexicon" / "validate_alias_overlay.py"
BLOCK_SCRIPT_PATH = REPO_ROOT / "tools" / "theme-lexicon" / "block_accepted_alias_conflicts.py"
APPLY_SCRIPT_PATH = REPO_ROOT / "tools" / "theme-lexicon" / "apply_zh_review_recommendations.py"
QUERY_SCRIPT_PATH = REPO_ROOT / "tools" / "theme-lexicon" / "query_alias_index.py"
TEMP_ROOT = Path(os.environ.get("VPNSCI_TEST_TMP", r"F:\AI playground\TempFiles"))


def load_script(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
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


class ParentheticalAcronymNormalizationTests(unittest.TestCase):
    def setUp(self) -> None:
        temp_parent = select_temp_parent(TEMP_ROOT, REPO_ROOT / "tests", REPO_ROOT)
        self.tmp = tempfile.TemporaryDirectory(dir=temp_parent)
        self.root = Path(self.tmp.name)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def _write_fixture(self) -> tuple[Path, Path, Path, Path]:
        candidate_dir = self.root / "candidates"
        review_dir = self.root / "review"
        concepts_path = self.root / "merged_en_concept_candidates.jsonl"
        write_jsonl(
            candidate_dir / "zh_alias_candidates.batch-001.jsonl",
            [
                {
                    "concept_id": "concept:nitrate_reductase_nadph",
                    "canonical_en": "Nitrate Reductase (nadph)",
                    "aliases_en": [],
                    "domains": ["biomedical", "chemicals_and_drugs"],
                    "source_refs": [{"source": "cso", "label": "Nitrate Reductase (nadph)"}],
                    "max_zh_alias_candidates": 3,
                    "candidate_generation_status": "pending_host_agent",
                    "zh_alias_candidates": [
                        {"alias": "硝酸还原酶(NADPH)", "source": "agent_exact_glossary", "confidence": "high"},
                    ],
                },
                {
                    "concept_id": "concept:nitrate_reductase_nad_p_h",
                    "canonical_en": "Nitrate Reductase (nad(p)h)",
                    "aliases_en": [],
                    "domains": ["biomedical", "chemicals_and_drugs"],
                    "source_refs": [{"source": "cso", "label": "Nitrate Reductase (nad(p)h)"}],
                    "max_zh_alias_candidates": 3,
                    "candidate_generation_status": "pending_host_agent",
                    "zh_alias_candidates": [
                        {"alias": "硝酸还原酶(NAD(P)H)", "source": "agent_exact_glossary", "confidence": "high"},
                    ],
                },
            ],
        )
        write_jsonl(
            concepts_path,
            [
                {
                    "concept_id": "concept:nitrate_reductase_nadph",
                    "domains": ["biomedical", "chemicals_and_drugs"],
                    "parents": [],
                    "specificity": 87,
                },
                {
                    "concept_id": "concept:nitrate_reductase_nad_p_h",
                    "domains": ["biomedical", "chemicals_and_drugs"],
                    "parents": [],
                    "specificity": 100,
                },
            ],
        )
        return candidate_dir, review_dir, concepts_path, self.root
    def _write_infinity_fixture(self) -> tuple[Path, Path, Path]:
        candidate_dir = self.root / "candidates"
        review_dir = self.root / "review"
        concepts_path = self.root / "merged_en_concept_candidates.jsonl"
        write_jsonl(
            candidate_dir / "zh_alias_candidates.batch-001.jsonl",
            [
                {
                    "concept_id": "concept:h_control",
                    "canonical_en": "H Control",
                    "aliases_en": [],
                    "domains": ["computer_science"],
                    "source_refs": [{"source": "cso", "label": "H Control"}],
                    "max_zh_alias_candidates": 3,
                    "candidate_generation_status": "pending_host_agent",
                    "zh_alias_candidates": [
                        {"alias": "H控制", "source": "agent_exact_glossary", "confidence": "high"},
                    ],
                },
                {
                    "concept_id": "concept:h_infinity_control",
                    "canonical_en": "H Infinity Control",
                    "aliases_en": [],
                    "domains": ["mathematics"],
                    "source_refs": [{"source": "cso", "label": "H Infinity Control"}],
                    "max_zh_alias_candidates": 3,
                    "candidate_generation_status": "pending_host_agent",
                    "zh_alias_candidates": [
                        {"alias": "H∞控制", "source": "agent_exact_glossary", "confidence": "high"},
                    ],
                },
            ],
        )
        write_jsonl(
            concepts_path,
            [
                {
                    "concept_id": "concept:h_control",
                    "domains": ["computer_science"],
                    "parents": [],
                    "specificity": 80,
                },
                {
                    "concept_id": "concept:h_infinity_control",
                    "domains": ["mathematics"],
                    "parents": [],
                    "specificity": 90,
                },
            ],
        )
        return candidate_dir, review_dir, concepts_path

    def test_parenthetical_acronyms_survive_full_pipeline_without_collision(self) -> None:
        validate = load_script("validate_alias_overlay", VALIDATE_SCRIPT_PATH)
        apply = load_script("apply_zh_review_recommendations", APPLY_SCRIPT_PATH)
        block = load_script("block_accepted_alias_conflicts", BLOCK_SCRIPT_PATH)
        materialize = load_script("materialize_runtime_overlay", MATERIALIZE_SCRIPT_PATH)
        query = load_script("query_alias_index", QUERY_SCRIPT_PATH)

        candidate_dir, review_dir, concepts_path, _ = self._write_fixture()
        index_path = self.root / "theme_concept_alias_index.json"
        manifest_path = self.root / "theme_concept_alias_manifest.json"
        recommendations_path = review_dir / "zh_review_recommendations.json"
        review_decisions_path = review_dir / "review_decisions.jsonl"

        validate_summary = validate.validate_alias_overlay(candidate_dir=candidate_dir, output_dir=review_dir, repo_root=REPO_ROOT)
        self.assertEqual(validate_summary["alias_conflicts"], 0)
        self.assertEqual(validate_summary["review_decisions"], 4)
        rows = read_jsonl(review_decisions_path)
        self.assertEqual([row["decision"] for row in rows if row["lang"] == "zh"], ["needs_review", "needs_review"])
        self.assertEqual([row["decision"] for row in rows if row["lang"] == "en"], ["accept", "accept"])
        recommendations_path.write_text(
            json.dumps(
                {
                    "recommendations": [
                        {
                            "concept_id": "concept:nitrate_reductase_nadph",
                            "alias": "硝酸还原酶(NADPH)",
                            "lang": "zh",
                            "recommendation": "accept",
                            "reason": "NADPH-specific alias should stay distinct from NAD(P)H",
                            "merge_duplicate_concepts": False,
                        },
                        {
                            "concept_id": "concept:nitrate_reductase_nad_p_h",
                            "alias": "硝酸还原酶(NAD(P)H)",
                            "lang": "zh",
                            "recommendation": "accept",
                            "reason": "Parenthetical acronym alias should stay distinct from NADPH",
                            "merge_duplicate_concepts": False,
                        },
                    ]
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

        apply_summary = apply.apply_zh_review_recommendations(
            review_decisions_path=review_decisions_path,
            recommendations_path=recommendations_path,
        )
        self.assertEqual(apply_summary["accept"], 2)
        rows = read_jsonl(review_decisions_path)
        self.assertEqual([row["decision"] for row in rows if row["lang"] == "zh"], ["accept", "accept"])

        block_summary = block.block_accepted_alias_conflicts(review_decisions_path=review_decisions_path)
        self.assertEqual(block_summary["accepted_conflict_groups"], 0)
        self.assertEqual(block_summary["blocked"], 0)

        materialize_summary = materialize.materialize_runtime_overlay(
            concepts_path=concepts_path,
            review_decisions_path=review_decisions_path,
            index_outputs=(index_path,),
            manifest_outputs=(manifest_path,),
        )
        self.assertEqual(materialize_summary["build_status"], "review_complete")
        self.assertEqual(materialize_summary["concept_aliases"], 2)

        index = json.loads(index_path.read_text(encoding="utf-8"))
        self.assertEqual(index["aliases"]["zh:硝酸还原酶 nadph"], "concept:nitrate_reductase_nadph")
        self.assertEqual(index["aliases"]["zh:硝酸还原酶 nad p h"], "concept:nitrate_reductase_nad_p_h")

        result_nadph = query.query_alias_index(index_path=index_path, alias="硝酸还原酶(NADPH)", lang="zh")
        result_nadph_plain = query.query_alias_index(index_path=index_path, alias="硝酸还原酶NADPH", lang="zh")
        result_nadp_h = query.query_alias_index(index_path=index_path, alias="硝酸还原酶(NAD(P)H)", lang="zh")

        self.assertEqual(result_nadph["concept_id"], "concept:nitrate_reductase_nadph")
        self.assertEqual(result_nadph_plain["concept_id"], "concept:nitrate_reductase_nadph")
        self.assertEqual(result_nadp_h["concept_id"], "concept:nitrate_reductase_nad_p_h")
        self.assertNotEqual(result_nadph["alias_key"], result_nadp_h["alias_key"])

    def test_infinity_symbol_survives_full_pipeline_without_h_control_collision(self) -> None:
        validate = load_script("validate_alias_overlay", VALIDATE_SCRIPT_PATH)
        apply = load_script("apply_zh_review_recommendations", APPLY_SCRIPT_PATH)
        block = load_script("block_accepted_alias_conflicts", BLOCK_SCRIPT_PATH)
        materialize = load_script("materialize_runtime_overlay", MATERIALIZE_SCRIPT_PATH)
        query = load_script("query_alias_index", QUERY_SCRIPT_PATH)

        candidate_dir, review_dir, concepts_path = self._write_infinity_fixture()
        index_path = self.root / "theme_concept_alias_index.json"
        manifest_path = self.root / "theme_concept_alias_manifest.json"
        recommendations_path = review_dir / "zh_review_recommendations.json"
        review_decisions_path = review_dir / "review_decisions.jsonl"

        validate_summary = validate.validate_alias_overlay(candidate_dir=candidate_dir, output_dir=review_dir, repo_root=REPO_ROOT)
        self.assertEqual(validate_summary["alias_conflicts"], 0)
        rows = read_jsonl(review_decisions_path)
        self.assertEqual([row["decision"] for row in rows if row["lang"] == "zh"], ["needs_review", "needs_review"])

        recommendations_path.write_text(
            json.dumps(
                {
                    "recommendations": [
                        {
                            "concept_id": "concept:h_control",
                            "alias": "H控制",
                            "lang": "zh",
                            "recommendation": "accept",
                            "reason": "CJK/Latin boundary normalization keeps H control distinct",
                            "merge_duplicate_concepts": False,
                        },
                        {
                            "concept_id": "concept:h_infinity_control",
                            "alias": "H∞控制",
                            "lang": "zh",
                            "recommendation": "accept",
                            "reason": "Infinity symbol normalization keeps H∞ control distinct",
                            "merge_duplicate_concepts": False,
                        },
                    ]
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

        apply_summary = apply.apply_zh_review_recommendations(
            review_decisions_path=review_decisions_path,
            recommendations_path=recommendations_path,
        )
        self.assertEqual(apply_summary["accept"], 2)
        block_summary = block.block_accepted_alias_conflicts(review_decisions_path=review_decisions_path)
        self.assertEqual(block_summary["accepted_conflict_groups"], 0)
        self.assertEqual(block_summary["blocked"], 0)

        materialize_summary = materialize.materialize_runtime_overlay(
            concepts_path=concepts_path,
            review_decisions_path=review_decisions_path,
            index_outputs=(index_path,),
            manifest_outputs=(manifest_path,),
        )
        self.assertEqual(materialize_summary["build_status"], "review_complete")
        self.assertEqual(materialize_summary["concept_aliases"], 2)

        index = json.loads(index_path.read_text(encoding="utf-8"))
        self.assertEqual(index["aliases"]["zh:h 控制"], "concept:h_control")
        self.assertEqual(index["aliases"]["zh:h infinity 控制"], "concept:h_infinity_control")

        result_h = query.query_alias_index(index_path=index_path, alias="H控制", lang="zh")
        result_h_infinity = query.query_alias_index(index_path=index_path, alias="H∞控制", lang="zh")
        self.assertEqual(result_h["concept_id"], "concept:h_control")
        self.assertEqual(result_h_infinity["concept_id"], "concept:h_infinity_control")
        self.assertNotEqual(result_h["alias_key"], result_h_infinity["alias_key"])
if __name__ == "__main__":
    unittest.main()