from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest

from tests.temp_helpers import select_temp_parent


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "tools" / "theme-lexicon" / "apply_concept_curation_to_build.py"
TEMP_ROOT = Path(os.environ.get("VPNSCI_TEST_TMP", r"F:\AI playground\TempFiles"))


def load_module():
    spec = importlib.util.spec_from_file_location("apply_concept_curation_to_build", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows), encoding="utf-8")


class ApplyConceptCurationToBuildTests(unittest.TestCase):
    def setUp(self) -> None:
        temp_parent = select_temp_parent(TEMP_ROOT, REPO_ROOT / "tests", REPO_ROOT)
        self.tmp = tempfile.TemporaryDirectory(dir=temp_parent)
        self.root = Path(self.tmp.name)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def _write_concepts(self) -> Path:
        concepts = self.root / "merged_en_concept_candidates.jsonl"
        write_jsonl(
            concepts,
            [
                {
                    "concept_id": "concept:available_bit_rate",
                    "aliases": {"en": ["Available Bit Rate"], "zh": []},
                    "canonical": {"en": "available bit rate", "zh": None},
                    "domains": ["communications"],
                    "parents": ["concept:bit_rate"],
                    "source_refs": [{"source": "ieee", "label": "Available Bit Rate"}],
                    "specificity": 60,
                },
                {
                    "concept_id": "concept:available_bit_rate_abr",
                    "aliases": {"en": ["Available Bit Rate (ABR)", "ABR"], "zh": []},
                    "canonical": {"en": "Available Bit Rate (ABR)", "zh": None},
                    "domains": ["computer_science"],
                    "parents": ["concept:networking"],
                    "source_refs": [{"source": "cso", "label": "Available Bit Rate (ABR)"}],
                    "specificity": 82,
                },
                {
                    "concept_id": "concept:topic_label",
                    "aliases": {"en": ["Technology In Education And Health"], "zh": []},
                    "canonical": {"en": "Technology In Education And Health", "zh": None},
                    "domains": ["computer_science"],
                    "parents": [],
                    "source_refs": [],
                    "specificity": 20,
                },
                {
                    "concept_id": "concept:too_broad",
                    "aliases": {"en": ["General"], "zh": []},
                    "canonical": {"en": "General", "zh": None},
                    "domains": [],
                    "parents": [],
                    "source_refs": [],
                    "specificity": 1,
                },
            ],
        )
        return concepts

    def _write_overlay(self) -> Path:
        overlay = self.root / "concept_curation_overlay.json"
        overlay.write_text(
            json.dumps(
                {
                    "schema_version": "theme_concept_curation_overlay.v1",
                    "redirects": {"concept:available_bit_rate_abr": "concept:available_bit_rate"},
                    "canonical": ["concept:available_bit_rate"],
                    "canonical_overrides": {"concept:available_bit_rate": {"en": "Available Bit Rate"}},
                    "display_only": ["concept:topic_label"],
                    "suppressed": ["concept:too_broad"],
                    "counts": {"canonical": 1, "display_only": 1, "redirect": 1, "suppressed": 1},
                    "decisions": [],
                },
                ensure_ascii=False,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        return overlay

    def test_applies_curation_to_build_snapshot(self) -> None:
        module = load_module()
        concepts = self._write_concepts()
        overlay = self._write_overlay()
        output = self.root / "curated_en_concept_candidates.jsonl"
        manifest = self.root / "curated_en_concept_build_manifest.json"

        summary = module.apply_concept_curation_to_build(
            concepts_path=concepts,
            curation_overlay_path=overlay,
            output_path=output,
            manifest_path=manifest,
        )

        self.assertEqual(summary["input_concepts"], 4)
        self.assertEqual(summary["output_concepts"], 1)
        self.assertEqual(summary["redirected_concepts"], 1)
        self.assertEqual(summary["display_only_concepts"], 1)
        self.assertEqual(summary["suppressed_concepts"], 1)
        self.assertEqual(summary["canonical_concepts"], 1)

        rows = [json.loads(line) for line in output.read_text(encoding="utf-8").splitlines()]
        self.assertEqual([row["concept_id"] for row in rows], ["concept:available_bit_rate"])
        target = rows[0]
        self.assertEqual(target["canonical"]["en"], "Available Bit Rate")
        self.assertEqual(target["curation_canonical_override"], {"en": "Available Bit Rate"})
        self.assertEqual(target["aliases"]["en"], ["Available Bit Rate", "Available Bit Rate (ABR)", "ABR"])
        self.assertEqual(target["domains"], ["communications", "computer_science"])
        self.assertEqual(target["parents"], ["concept:bit_rate", "concept:networking"])
        self.assertEqual(target["specificity"], 82)
        self.assertEqual(
            target["source_refs"],
            [
                {"source": "ieee", "label": "Available Bit Rate"},
                {"source": "cso", "label": "Available Bit Rate (ABR)"},
            ],
        )

        written_manifest = json.loads(manifest.read_text(encoding="utf-8"))
        self.assertEqual(written_manifest["schema_version"], "theme_en_concept_build_curation.v1")
        self.assertEqual(written_manifest["retired_concepts"], 3)
        self.assertEqual(written_manifest["redirects"], {"concept:available_bit_rate_abr": "concept:available_bit_rate"})
        self.assertEqual(written_manifest["display_only"], ["concept:topic_label"])
        self.assertEqual(written_manifest["suppressed"], ["concept:too_broad"])
        self.assertEqual(written_manifest["canonical_overrides"], {"concept:available_bit_rate": {"en": "Available Bit Rate"}})

    def test_rejects_redirect_to_excluded_target(self) -> None:
        module = load_module()
        concepts = self._write_concepts()
        overlay = self.root / "bad_overlay.json"
        overlay.write_text(
            json.dumps(
                {
                    "schema_version": "theme_concept_curation_overlay.v1",
                    "redirects": {"concept:available_bit_rate_abr": "concept:too_broad"},
                    "canonical": [],
                    "canonical_overrides": {},
                    "display_only": [],
                    "suppressed": ["concept:too_broad"],
                },
                ensure_ascii=False,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )

        with self.assertRaisesRegex(ValueError, "redirect target is excluded"):
            module.apply_concept_curation_to_build(
                concepts_path=concepts,
                curation_overlay_path=overlay,
                output_path=self.root / "out.jsonl",
                manifest_path=None,
            )


if __name__ == "__main__":
    unittest.main()
