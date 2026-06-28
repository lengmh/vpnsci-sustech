from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest

from tests.temp_helpers import select_temp_parent


REPO_ROOT = Path(__file__).resolve().parents[1]
QUERY_SCRIPT_PATH = REPO_ROOT / "tools" / "theme-lexicon" / "query_alias_index.py"
SUMMARY_SCRIPT_PATH = REPO_ROOT / "tools" / "theme-lexicon" / "summarize_alias_runtime.py"
TEMP_ROOT = Path(os.environ.get("VPNSCI_TEST_TMP", r"F:\AI playground\TempFiles"))


def load_script(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


class QueryAliasIndexTests(unittest.TestCase):
    def setUp(self) -> None:
        temp_parent = select_temp_parent(TEMP_ROOT, REPO_ROOT / "tests", REPO_ROOT)
        self.tmp = tempfile.TemporaryDirectory(dir=temp_parent)
        self.root = Path(self.tmp.name)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def _write_index_and_manifest(self) -> tuple[Path, Path]:
        index_path = self.root / "theme_concept_alias_index.json"
        manifest_path = self.root / "theme_concept_alias_manifest.json"
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
        manifest_path.write_text(
            json.dumps(
                {
                    "schema_version": "theme_concept_alias_manifest.v1",
                    "build_status": "review_complete",
                    "concepts": 1,
                    "concepts_with_zh_alias": 1,
                    "aliases": {"en": 1, "zh": 1},
                },
                ensure_ascii=False,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        return index_path, manifest_path

    def test_query_alias_normalizes_plural_english_alias(self) -> None:
        module = load_script("query_alias_index", QUERY_SCRIPT_PATH)
        index_path, _ = self._write_index_and_manifest()

        result = module.query_alias_index(
            index_path=index_path,
            alias="Network Pharmacologies",
            lang="en",
        )

        self.assertEqual(result["matched"], True)
        self.assertEqual(result["alias_key"], "en:network pharmacology")
        self.assertEqual(result["concept"]["concept_id"], "concept:network_pharmacology")

    def test_chinese_alias_normalization_preserves_semantic_ascii_punctuation(self) -> None:
        module = load_script("query_alias_index", QUERY_SCRIPT_PATH)

        self.assertEqual(module.normalize_alias("C#语言"), "c# 语言")
        self.assertEqual(module.normalize_alias("c 语言"), "c 语言")
        self.assertEqual(module.normalize_alias("氯联苯(54%氯)"), "氯联苯 54% 氯")
        self.assertEqual(module.normalize_alias("氯联苯 54 氯"), "氯联苯 54 氯")
        self.assertEqual(module.normalize_alias("GM(1,1)灰色模型"), "gm 1,1 灰色模型")
        self.assertEqual(module.normalize_alias("gm 1 1 灰色模型"), "gm 1 1 灰色模型")

    def test_query_concept_id_returns_grouped_normalized_aliases(self) -> None:
        module = load_script("query_alias_index", QUERY_SCRIPT_PATH)
        index_path, _ = self._write_index_and_manifest()

        result = module.query_alias_index(
            index_path=index_path,
            concept_id="concept:network_pharmacology",
        )

        self.assertEqual(result["matched"], True)
        self.assertEqual(result["aliases"], {"en": ["network pharmacology"], "zh": ["网络药理学"]})

    def test_summarize_alias_runtime_prefers_manifest(self) -> None:
        module = load_script("summarize_alias_runtime", SUMMARY_SCRIPT_PATH)
        index_path, manifest_path = self._write_index_and_manifest()

        result = module.summarize_alias_runtime(manifest_path=manifest_path, index_path=index_path)

        self.assertEqual(result["source"], "manifest")
        self.assertEqual(result["concepts"], 1)


if __name__ == "__main__":
    unittest.main()
