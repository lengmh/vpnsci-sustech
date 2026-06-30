from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest

from tests.temp_helpers import select_temp_parent


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "tools" / "theme-lexicon" / "apply_concept_curation.py"
TEMP_ROOT = Path(os.environ.get("VPNSCI_TEST_TMP", r"F:\AI playground\TempFiles"))


def load_module():
    spec = importlib.util.spec_from_file_location("apply_concept_curation", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


class ConceptCurationTests(unittest.TestCase):
    def setUp(self) -> None:
        temp_parent = select_temp_parent(TEMP_ROOT, REPO_ROOT / "tests", REPO_ROOT)
        self.tmp = tempfile.TemporaryDirectory(dir=temp_parent)
        self.root = Path(self.tmp.name)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def _write_index(self) -> Path:
        index_path = self.root / "theme_concept_alias_index.json"
        index_path.write_text(
            json.dumps(
                {
                    "schema_version": "theme_concept_alias_index.v1",
                    "build_status": "review_complete",
                    "concepts": {
                        "concept:accelerometer": {
                            "concept_id": "concept:accelerometer",
                            "canonical": {"en": "Accelerometers", "zh": "加速度计"},
                        },
                        "concept:accelerometer__2": {
                            "concept_id": "concept:accelerometer__2",
                            "canonical": {"en": "Accelerometer", "zh": ""},
                        },
                        "concept:accelerometer__3": {
                            "concept_id": "concept:accelerometer__3",
                            "canonical": {"en": "Acceleration Sensor", "zh": ""},
                        },
                        "concept:abstract__2": {
                            "concept_id": "concept:abstract__2",
                            "canonical": {"en": "Abstract", "zh": ""},
                        },
                        "concept:blockchain_technology_in_education_and_learning": {
                            "concept_id": "concept:blockchain_technology_in_education_and_learning",
                            "canonical": {"en": "Blockchain Technology In Education And Learning", "zh": ""},
                        },
                    },
                    "aliases": {},
                },
                ensure_ascii=False,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        return index_path

    def _write_decisions(self, decisions: list[dict]) -> Path:
        curation_path = self.root / "concept_curation_decisions.json"
        curation_path.write_text(
            json.dumps(
                {
                    "schema_version": "theme_concept_curation_decisions.v1",
                    "decisions": decisions,
                },
                ensure_ascii=False,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        return curation_path

    def test_validates_and_writes_normalized_curation_overlay(self) -> None:
        module = load_module()
        index_path = self._write_index()
        decisions_path = self._write_decisions(
            [
                {
                    "concept_id": "concept:accelerometer__2",
                    "decision": "redirect",
                    "target_concept_id": "concept:accelerometer",
                    "category": "plural_or_source_variant",
                    "reason": "singular source variant of canonical accelerometers concept",
                    "reviewer": "main-agent",
                    "decided_at": "2026-06-30",
                },
                {
                    "concept_id": "concept:abstract__2",
                    "decision": "suppressed",
                    "category": "broad_or_noise",
                    "reason": "publication label is too broad for search/treemap target",
                    "reviewer": "main-agent",
                    "decided_at": "2026-06-30",
                },
                {
                    "concept_id": "concept:blockchain_technology_in_education_and_learning",
                    "decision": "display_only",
                    "category": "topic_label_phrase",
                    "topic_label_disposition": "display_only",
                    "reason": "useful display phrase but not a search alias",
                    "reviewer": "main-agent",
                    "decided_at": "2026-06-30",
                },
            ]
        )
        output_path = self.root / "concept_curation_overlay.json"

        summary = module.apply_concept_curation(
            index_path=index_path,
            curation_decisions_path=decisions_path,
            output_path=output_path,
        )

        self.assertEqual(summary["counts"], {"display_only": 1, "redirect": 1, "suppressed": 1})
        self.assertEqual(summary["active_decisions"], 3)
        overlay = json.loads(output_path.read_text(encoding="utf-8"))
        self.assertEqual(overlay["schema_version"], "theme_concept_curation_overlay.v1")
        self.assertEqual(
            overlay["redirects"],
            {"concept:accelerometer__2": "concept:accelerometer"},
        )
        self.assertEqual(overlay["suppressed"], ["concept:abstract__2"])
        self.assertEqual(overlay["display_only"], ["concept:blockchain_technology_in_education_and_learning"])

    def test_rejects_unknown_decision(self) -> None:
        module = load_module()
        index_path = self._write_index()
        decisions_path = self._write_decisions(
            [
                {
                    "concept_id": "concept:abstract__2",
                    "decision": "delete",
                    "category": "broad_or_noise",
                    "reason": "unsupported",
                    "reviewer": "main-agent",
                    "decided_at": "2026-06-30",
                }
            ]
        )

        with self.assertRaisesRegex(ValueError, "Unsupported curation decision"):
            module.apply_concept_curation(index_path=index_path, curation_decisions_path=decisions_path)

    def test_rejects_redirect_to_missing_or_self_target(self) -> None:
        module = load_module()
        index_path = self._write_index()
        missing_target_path = self._write_decisions(
            [
                {
                    "concept_id": "concept:accelerometer__2",
                    "decision": "redirect",
                    "target_concept_id": "concept:missing",
                    "category": "plural_or_source_variant",
                    "reason": "missing target",
                    "reviewer": "main-agent",
                    "decided_at": "2026-06-30",
                }
            ]
        )
        with self.assertRaisesRegex(ValueError, "redirect target does not exist"):
            module.apply_concept_curation(index_path=index_path, curation_decisions_path=missing_target_path)

        self_target_path = self._write_decisions(
            [
                {
                    "concept_id": "concept:accelerometer__2",
                    "decision": "redirect",
                    "target_concept_id": "concept:accelerometer__2",
                    "category": "plural_or_source_variant",
                    "reason": "self target",
                    "reviewer": "main-agent",
                    "decided_at": "2026-06-30",
                }
            ]
        )
        with self.assertRaisesRegex(ValueError, "cannot redirect to itself"):
            module.apply_concept_curation(index_path=index_path, curation_decisions_path=self_target_path)

    def test_rejects_redirect_to_suppressed_target_and_redirect_cycle(self) -> None:
        module = load_module()
        index_path = self._write_index()
        suppressed_target_path = self._write_decisions(
            [
                {
                    "concept_id": "concept:abstract__2",
                    "decision": "suppressed",
                    "category": "broad_or_noise",
                    "reason": "too broad",
                    "reviewer": "main-agent",
                    "decided_at": "2026-06-30",
                },
                {
                    "concept_id": "concept:accelerometer__2",
                    "decision": "redirect",
                    "target_concept_id": "concept:abstract__2",
                    "category": "plural_or_source_variant",
                    "reason": "bad target",
                    "reviewer": "main-agent",
                    "decided_at": "2026-06-30",
                },
            ]
        )
        with self.assertRaisesRegex(ValueError, "redirect target is suppressed"):
            module.apply_concept_curation(index_path=index_path, curation_decisions_path=suppressed_target_path)

        cycle_path = self._write_decisions(
            [
                {
                    "concept_id": "concept:accelerometer",
                    "decision": "redirect",
                    "target_concept_id": "concept:accelerometer__2",
                    "category": "plural_or_source_variant",
                    "reason": "cycle part one",
                    "reviewer": "main-agent",
                    "decided_at": "2026-06-30",
                },
                {
                    "concept_id": "concept:accelerometer__2",
                    "decision": "redirect",
                    "target_concept_id": "concept:accelerometer",
                    "category": "plural_or_source_variant",
                    "reason": "cycle part two",
                    "reviewer": "main-agent",
                    "decided_at": "2026-06-30",
                },
            ]
        )
        with self.assertRaisesRegex(ValueError, "redirect cycle"):
            module.apply_concept_curation(index_path=index_path, curation_decisions_path=cycle_path)

    def test_rejects_redirect_chain_target(self) -> None:
        module = load_module()
        index_path = self._write_index()
        decisions_path = self._write_decisions(
            [
                {
                    "concept_id": "concept:accelerometer__3",
                    "decision": "redirect",
                    "target_concept_id": "concept:accelerometer__2",
                    "category": "plural_or_source_variant",
                    "reason": "intermediate redirect target",
                    "reviewer": "main-agent",
                    "decided_at": "2026-06-30",
                },
                {
                    "concept_id": "concept:accelerometer__2",
                    "decision": "redirect",
                    "target_concept_id": "concept:accelerometer",
                    "category": "plural_or_source_variant",
                    "reason": "canonical redirect target",
                    "reviewer": "main-agent",
                    "decided_at": "2026-06-30",
                },
            ]
        )

        with self.assertRaisesRegex(ValueError, "redirect target is also redirected"):
            module.apply_concept_curation(index_path=index_path, curation_decisions_path=decisions_path)

    def test_rejects_duplicate_active_decision_for_same_concept(self) -> None:
        module = load_module()
        index_path = self._write_index()
        decisions_path = self._write_decisions(
            [
                {
                    "concept_id": "concept:abstract__2",
                    "decision": "suppressed",
                    "category": "broad_or_noise",
                    "reason": "too broad",
                    "reviewer": "main-agent",
                    "decided_at": "2026-06-30",
                },
                {
                    "concept_id": "concept:abstract__2",
                    "decision": "display_only",
                    "category": "topic_label_phrase",
                    "topic_label_disposition": "display_only",
                    "reason": "conflicting active decision",
                    "reviewer": "main-agent",
                    "decided_at": "2026-06-30",
                },
            ]
        )

        with self.assertRaisesRegex(ValueError, "multiple active curation decisions"):
            module.apply_concept_curation(index_path=index_path, curation_decisions_path=decisions_path)


if __name__ == "__main__":
    unittest.main()
