from __future__ import annotations

import json
import os
from pathlib import Path
import tempfile
import unittest

from tests.temp_helpers import select_temp_parent
from vpnsci_sustech import theme_clustering


REPO_ROOT = Path(__file__).resolve().parents[1]
TEMP_ROOT = Path(os.environ.get("VPNSCI_TEST_TMP", r"F:\AI playground\TempFiles"))


class ThemeClusteringCompactAliasIndexTests(unittest.TestCase):
    def setUp(self) -> None:
        temp_parent = select_temp_parent(TEMP_ROOT, REPO_ROOT / "tests", REPO_ROOT)
        self.tmp = tempfile.TemporaryDirectory(dir=temp_parent)
        self.root = Path(self.tmp.name)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_loads_compact_alias_index(self) -> None:
        index_path = self.root / "theme_concept_alias_index.json"
        concept = {
            "concept_id": "concept:network_pharmacology",
            "canonical": {"en": "Network Pharmacology", "zh": "网络药理学"},
            "domains": ["biomedical"],
            "parents": [],
            "specificity": 70,
        }
        index_path.write_text(
            json.dumps(
                {
                    "schema_version": "theme_concept_alias_index.v1",
                    "build_status": "review_complete",
                    "normalization": "theme_concept_alias_normalization.v1",
                    "concepts": {"concept:network_pharmacology": concept},
                    "aliases": {
                        "en:network pharmacology": "concept:network_pharmacology",
                        "zh:网络药理学": "concept:network_pharmacology",
                    },
                },
                ensure_ascii=False,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )

        alias_index = theme_clustering._load_theme_concept_aliases(
            index_path=index_path,
            legacy_path=self.root / "missing.json",
        )

        self.assertEqual(alias_index["zh:网络药理学"]["concept_id"], "concept:network_pharmacology")
        self.assertEqual(alias_index["en:network pharmacology"]["specificity"], 70)

    def test_falls_back_to_legacy_full_overlay_only_when_index_missing(self) -> None:
        legacy_path = self.root / "theme_concept_aliases.json"
        legacy_path.write_text(
            json.dumps(
                {
                    "schema_version": "theme_concept_aliases.v1",
                    "build_status": "review_complete",
                    "concept_aliases": [
                        {
                            "concept_id": "concept:channel_estimation",
                            "canonical": {"en": "Channel Estimation", "zh": "信道估计"},
                            "aliases": {"en": ["Channel Estimations"], "zh": ["信道估计"]},
                            "domains": ["communications"],
                            "parents": [],
                            "specificity": 80,
                        }
                    ],
                },
                ensure_ascii=False,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )

        alias_index = theme_clustering._load_theme_concept_aliases(
            index_path=self.root / "missing_index.json",
            legacy_path=legacy_path,
        )

        self.assertEqual(alias_index["en:channel estimation"]["concept_id"], "concept:channel_estimation")
        self.assertEqual(alias_index["zh:信道估计"]["concept_id"], "concept:channel_estimation")


if __name__ == "__main__":
    unittest.main()
