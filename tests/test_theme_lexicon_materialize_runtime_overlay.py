from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest

from tests.temp_helpers import select_temp_parent


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "tools" / "theme-lexicon" / "materialize_runtime_overlay.py"
TEMP_ROOT = Path(os.environ.get("VPNSCI_TEST_TMP", r"F:\AI playground\TempFiles"))


def load_module():
    spec = importlib.util.spec_from_file_location("materialize_runtime_overlay", SCRIPT_PATH)
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


class MaterializeRuntimeOverlayTests(unittest.TestCase):
    def setUp(self) -> None:
        temp_parent = select_temp_parent(TEMP_ROOT, REPO_ROOT / "tests", REPO_ROOT)
        self.tmp = tempfile.TemporaryDirectory(dir=temp_parent)
        self.root = Path(self.tmp.name)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def _write_fixture(self) -> tuple[Path, Path]:
        concepts = self.root / "merged_en_concept_candidates.jsonl"
        review = self.root / "review_decisions.jsonl"
        write_jsonl(
            concepts,
            [
                {
                    "concept_id": "comm:channel_estimation",
                    "domains": ["communications"],
                    "parents": ["comm:wireless_communication"],
                    "specificity": 80,
                },
                {
                    "concept_id": "mesh:shock_waves",
                    "domains": ["medicine"],
                    "parents": [],
                    "specificity": 55,
                },
            ],
        )
        write_jsonl(
            review,
            [
                {"concept_id": "comm:channel_estimation", "alias": "Channel Estimation", "lang": "en", "decision": "accept"},
                {"concept_id": "comm:channel_estimation", "alias": "channel estimations", "lang": "en", "decision": "accept"},
                {"concept_id": "comm:channel_estimation", "alias": "信道估计", "lang": "zh", "decision": "accept"},
                {"concept_id": "mesh:shock_waves", "alias": "Shock Waves", "lang": "en", "decision": "accept"},
                {"concept_id": "mesh:shock_waves", "alias": "冲击波", "lang": "zh", "decision": "accept"},
                {"concept_id": "mesh:shock_waves", "alias": "休克波", "lang": "zh", "decision": "blocked"},
            ],
        )
        return concepts, review

    def test_writes_compact_index_and_manifest_without_legacy_full_by_default(self) -> None:
        module = load_module()
        concepts, review = self._write_fixture()
        index_a = self.root / "pkg" / "theme_concept_alias_index.json"
        index_b = self.root / "tool" / "theme_concept_alias_index.json"
        manifest_a = self.root / "pkg" / "theme_concept_alias_manifest.json"
        manifest_b = self.root / "tool" / "theme_concept_alias_manifest.json"

        summary = module.materialize_runtime_overlay(
            concepts_path=concepts,
            review_decisions_path=review,
            index_outputs=(index_a, index_b),
            manifest_outputs=(manifest_a, manifest_b),
        )

        self.assertEqual(summary["schema_version"], "theme_concept_aliases_materialize.v2")
        self.assertEqual(summary["build_status"], "review_complete")
        self.assertEqual(summary["legacy_full_outputs"], [])
        self.assertFalse((self.root / "pkg" / "theme_concept_aliases.json").exists())

        index = json.loads(index_a.read_text(encoding="utf-8"))
        self.assertEqual(index["schema_version"], "theme_concept_alias_index.v1")
        self.assertEqual(index["aliases"]["en:channel estimation"], "comm:channel_estimation")
        self.assertEqual(index["aliases"]["zh:信道估计"], "comm:channel_estimation")
        self.assertEqual(index["aliases"]["zh:冲击波"], "mesh:shock_waves")
        self.assertNotIn("zh:休克波", index["aliases"])
        self.assertEqual(index_a.read_bytes(), index_b.read_bytes())

        manifest = json.loads(manifest_a.read_text(encoding="utf-8"))
        self.assertEqual(manifest["schema_version"], "theme_concept_alias_manifest.v1")
        self.assertEqual(manifest["concepts"], 2)
        self.assertEqual(manifest["concepts_with_zh_alias"], 2)
        self.assertEqual(manifest["aliases"], {"en": 3, "zh": 2})
        self.assertIn("index", manifest["sha256"])
        self.assertEqual(manifest_a.read_bytes(), manifest_b.read_bytes())

    def test_can_emit_legacy_full_and_ignored_audit_when_explicitly_requested(self) -> None:
        module = load_module()
        concepts, review = self._write_fixture()
        index_path = self.root / "theme_concept_alias_index.json"
        manifest_path = self.root / "theme_concept_alias_manifest.json"
        legacy_path = self.root / "theme_concept_aliases.json"
        audit_path = self.root / "theme_concept_aliases.full.jsonl"

        summary = module.materialize_runtime_overlay(
            concepts_path=concepts,
            review_decisions_path=review,
            index_outputs=(index_path,),
            manifest_outputs=(manifest_path,),
            legacy_outputs=(legacy_path,),
            full_audit_output=audit_path,
        )

        self.assertTrue(legacy_path.exists())
        self.assertTrue(audit_path.exists())
        self.assertEqual(summary["legacy_full_outputs"], [str(legacy_path)])

    def test_runtime_singular_collision_preserves_legacy_first_target_without_skipping_concepts(self) -> None:
        module = load_module()
        concepts = self.root / "merged_en_concept_candidates.jsonl"
        review = self.root / "review_decisions.jsonl"
        index_path = self.root / "theme_concept_alias_index.json"
        manifest_path = self.root / "theme_concept_alias_manifest.json"
        write_jsonl(
            concepts,
            [
                {"concept_id": "concept:alpha_channel", "domains": [], "parents": [], "specificity": 10},
                {"concept_id": "concept:beta_channel", "domains": [], "parents": [], "specificity": 20},
            ],
        )
        write_jsonl(
            review,
            [
                {"concept_id": "concept:alpha_channel", "alias": "Channel Estimation", "lang": "en", "decision": "accept"},
                {"concept_id": "concept:beta_channel", "alias": "Channel Estimations", "lang": "en", "decision": "accept"},
            ],
        )

        summary = module.materialize_runtime_overlay(
            concepts_path=concepts,
            review_decisions_path=review,
            index_outputs=(index_path,),
            manifest_outputs=(manifest_path,),
        )

        self.assertEqual(summary["skipped_accepted_alias_conflicts"], 0)
        self.assertEqual(summary["concept_aliases"], 2)
        index = json.loads(index_path.read_text(encoding="utf-8"))
        self.assertEqual(index["aliases"]["en:channel estimation"], "concept:alpha_channel")


if __name__ == "__main__":
    unittest.main()
