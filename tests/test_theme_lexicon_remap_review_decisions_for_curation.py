from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest

from tests.temp_helpers import select_temp_parent


REPO_ROOT = Path(__file__).resolve().parents[1]
REMAP_SCRIPT_PATH = REPO_ROOT / "tools" / "theme-lexicon" / "remap_review_decisions_for_curation.py"
BUILD_SCRIPT_PATH = REPO_ROOT / "tools" / "theme-lexicon" / "apply_concept_curation_to_build.py"
MATERIALIZE_SCRIPT_PATH = REPO_ROOT / "tools" / "theme-lexicon" / "materialize_runtime_overlay.py"
TEMP_ROOT = Path(os.environ.get("VPNSCI_TEST_TMP", r"F:\AI playground\TempFiles"))


def load_script(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows), encoding="utf-8")


class RemapReviewDecisionsForCurationTests(unittest.TestCase):
    def setUp(self) -> None:
        temp_parent = select_temp_parent(TEMP_ROOT, REPO_ROOT / "tests", REPO_ROOT)
        self.tmp = tempfile.TemporaryDirectory(dir=temp_parent)
        self.root = Path(self.tmp.name)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def _write_overlay(self) -> Path:
        overlay = self.root / "concept_curation_overlay.json"
        overlay.write_text(
            json.dumps(
                {
                    "schema_version": "theme_concept_curation_overlay.v1",
                    "redirects": {"concept:source": "concept:target"},
                    "canonical": ["concept:target"],
                    "canonical_overrides": {"concept:target": {"en": "Target Concept"}},
                    "display_only": ["concept:topic_label"],
                    "suppressed": ["concept:noise"],
                },
                ensure_ascii=False,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        return overlay

    def test_remaps_redirect_sources_and_drops_excluded_rows(self) -> None:
        module = load_script("remap_review_decisions_for_curation", REMAP_SCRIPT_PATH)
        review = self.root / "review_decisions.jsonl"
        overlay = self._write_overlay()
        output = self.root / "review_decisions.curated.jsonl"
        manifest = self.root / "review_decisions.curated_manifest.json"
        write_jsonl(
            review,
            [
                {"concept_id": "concept:target", "alias": "Target Concept", "lang": "en", "decision": "accept"},
                {"concept_id": "concept:source", "alias": "Source Acronym", "lang": "en", "decision": "accept"},
                {"concept_id": "concept:source", "alias": "source acronym", "lang": "en", "decision": "accept"},
                {"concept_id": "concept:topic_label", "alias": "Topic Label", "lang": "en", "decision": "accept"},
                {"concept_id": "concept:noise", "alias": "Noise", "lang": "en", "decision": "blocked"},
            ],
        )

        summary = module.remap_review_decisions_for_curation(
            review_decisions_path=review,
            curation_overlay_path=overlay,
            output_path=output,
            manifest_path=manifest,
        )

        self.assertEqual(summary["input_rows"], 5)
        self.assertEqual(summary["output_rows"], 2)
        self.assertEqual(summary["remapped_rows"], 2)
        self.assertEqual(summary["dropped_excluded_rows"], 2)
        self.assertEqual(summary["deduplicated_rows"], 1)
        rows = [json.loads(line) for line in output.read_text(encoding="utf-8").splitlines()]
        self.assertEqual([row["concept_id"] for row in rows], ["concept:target", "concept:target"])
        self.assertIn("curation_source_concept_id", rows[1])
        self.assertNotIn("concept:topic_label", {row["concept_id"] for row in rows})
        self.assertEqual(json.loads(manifest.read_text(encoding="utf-8"))["schema_version"], "theme_review_decision_curation_remap.v1")

    def test_curated_build_with_remapped_reviews_preserves_alias_targets_without_overlay(self) -> None:
        build = load_script("apply_concept_curation_to_build", BUILD_SCRIPT_PATH)
        remap = load_script("remap_review_decisions_for_curation", REMAP_SCRIPT_PATH)
        materialize = load_script("materialize_runtime_overlay", MATERIALIZE_SCRIPT_PATH)
        concepts = self.root / "merged_en_concept_candidates.jsonl"
        review = self.root / "review_decisions.jsonl"
        overlay = self._write_overlay()
        write_jsonl(
            concepts,
            [
                {
                    "concept_id": "concept:target",
                    "aliases": {"en": ["Target Concept"], "zh": []},
                    "canonical": {"en": "target concept", "zh": None},
                    "domains": ["computer_science"],
                    "parents": [],
                    "source_refs": [],
                    "specificity": 60,
                },
                {
                    "concept_id": "concept:source",
                    "aliases": {"en": ["Source Acronym"], "zh": []},
                    "canonical": {"en": "Source Acronym", "zh": None},
                    "domains": ["engineering"],
                    "parents": [],
                    "source_refs": [],
                    "specificity": 80,
                },
                {
                    "concept_id": "concept:topic_label",
                    "aliases": {"en": ["Topic Label"], "zh": []},
                    "canonical": {"en": "Topic Label", "zh": None},
                    "domains": [],
                    "parents": [],
                    "source_refs": [],
                    "specificity": 10,
                },
                {
                    "concept_id": "concept:noise",
                    "aliases": {"en": ["Noise"], "zh": []},
                    "canonical": {"en": "Noise", "zh": None},
                    "domains": [],
                    "parents": [],
                    "source_refs": [],
                    "specificity": 1,
                },
            ],
        )
        write_jsonl(
            review,
            [
                {"concept_id": "concept:target", "alias": "Target Concept", "lang": "en", "decision": "accept"},
                {"concept_id": "concept:source", "alias": "Source Acronym", "lang": "en", "decision": "accept"},
                {"concept_id": "concept:topic_label", "alias": "Topic Label", "lang": "en", "decision": "accept"},
            ],
        )

        overlay_index = self.root / "overlay_index.json"
        overlay_manifest = self.root / "overlay_manifest.json"
        materialize.materialize_runtime_overlay(
            concepts_path=concepts,
            review_decisions_path=review,
            curation_overlay_path=overlay,
            index_outputs=(overlay_index,),
            manifest_outputs=(overlay_manifest,),
        )

        curated_concepts = self.root / "curated_en_concepts.jsonl"
        curated_review = self.root / "review_decisions.curated.jsonl"
        build.apply_concept_curation_to_build(
            concepts_path=concepts,
            curation_overlay_path=overlay,
            output_path=curated_concepts,
            manifest_path=None,
        )
        remap.remap_review_decisions_for_curation(
            review_decisions_path=review,
            curation_overlay_path=overlay,
            output_path=curated_review,
            manifest_path=None,
        )
        no_overlay_index = self.root / "no_overlay_index.json"
        no_overlay_manifest = self.root / "no_overlay_manifest.json"
        materialize.materialize_runtime_overlay(
            concepts_path=curated_concepts,
            review_decisions_path=curated_review,
            index_outputs=(no_overlay_index,),
            manifest_outputs=(no_overlay_manifest,),
        )

        overlay_payload = json.loads(overlay_index.read_text(encoding="utf-8"))
        no_overlay_payload = json.loads(no_overlay_index.read_text(encoding="utf-8"))
        self.assertEqual(overlay_payload["aliases"], no_overlay_payload["aliases"])
        self.assertEqual(set(overlay_payload["concepts"]), set(no_overlay_payload["concepts"]))
        self.assertEqual(no_overlay_payload["aliases"]["en:source acronym"], "concept:target")
        self.assertNotIn("concept:topic_label", no_overlay_payload["concepts"])
        self.assertEqual(no_overlay_payload["concepts"]["concept:target"]["canonical"]["en"], "Target Concept")


if __name__ == "__main__":
    unittest.main()
