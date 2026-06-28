from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest

from tests.temp_helpers import select_temp_parent
from vpnsci_sustech import theme_clustering


REPO_ROOT = Path(__file__).resolve().parents[1]
TEMP_ROOT = Path(os.environ.get("VPNSCI_TEST_TMP", r"F:\AI playground\TempFiles"))
PAPER_SEARCH_PRO_THEME_CLUSTERING = REPO_ROOT / "tools" / "paper-search-pro" / "scripts" / "theme_clustering.py"


def load_paper_search_pro_theme_clustering():
    spec = importlib.util.spec_from_file_location("paper_search_pro_theme_clustering", PAPER_SEARCH_PRO_THEME_CLUSTERING)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


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

    def test_runtime_alias_keys_match_compact_index_mixed_cjk_latin_normalization(self) -> None:
        cases = {
            "H控制": "zh:h 控制",
            "H∞控制": "zh:h infinity 控制",
            "硝酸还原酶(NADPH)": "zh:硝酸还原酶 nadph",
        }

        for alias, expected_key in cases.items():
            self.assertEqual(theme_clustering._concept_alias_key(alias), expected_key)
            self.assertIn(expected_key, theme_clustering.THEME_CONCEPT_ALIAS_INDEX)

    def test_paper_search_pro_alias_keys_match_compact_index_mixed_cjk_latin_normalization(self) -> None:
        module = load_paper_search_pro_theme_clustering()
        cases = {
            "H控制": "zh:h 控制",
            "H∞控制": "zh:h infinity 控制",
            "硝酸还原酶(NADPH)": "zh:硝酸还原酶 nadph",
        }

        for alias, expected_key in cases.items():
            self.assertEqual(module._concept_alias_key(alias), expected_key)
            self.assertIn(expected_key, module.THEME_CONCEPT_ALIAS_INDEX)

    def test_runtime_text_fallback_extracts_mixed_cjk_latin_compact_aliases(self) -> None:
        cases = [
            ("H控制", "concept:h_control", "h 控制"),
            ("H∞控制", "concept:h_infinity_control", "h infinity 控制"),
            ("硝酸还原酶(NADPH)", "concept:nitrate_reductase_nadph", "硝酸还原酶 nadph"),
        ]

        for alias, expected_concept_id, expected_matched_alias in cases:
            papers = [
                {
                    "paper_id": str(index),
                    "title": f"{alias} 研究",
                    "abstract": f"{alias} 用于主题别名匹配，{alias} 是核心方法。",
                }
                for index in range(3)
            ]
            result = theme_clustering.build_text_themes(papers)
            themes = {
                theme.get("concept_id"): theme
                for theme in result["themes"]
                if theme.get("concept_id")
            }

            self.assertIn(expected_concept_id, themes)
            self.assertIn(expected_matched_alias, themes[expected_concept_id]["matched_aliases"]["zh"])

    def test_runtime_text_fallback_does_not_match_mixed_alias_inside_longer_latin_token(self) -> None:
        for alias in ("pH控制", "AH控制", "p-H控制", "p H控制"):
            papers = [
                {
                    "paper_id": str(index),
                    "title": f"{alias} 研究",
                    "abstract": f"{alias} 用于主题别名匹配，{alias} 是核心方法。",
                }
                for index in range(3)
            ]
            result = theme_clustering.build_text_themes(papers)
            concept_ids = {theme.get("concept_id") for theme in result["themes"]}

            self.assertNotIn("concept:h_control", concept_ids)

    def test_runtime_text_fallback_does_not_collapse_ascii_inside_chinese_punctuation_match(self) -> None:
        for alias in ("服务质量Q路由", "服务质量123路由"):
            papers = [
                {
                    "paper_id": str(index),
                    "title": f"{alias} 研究",
                    "abstract": f"{alias} 用于网络路径选择，{alias} 是核心方法。",
                }
                for index in range(3)
            ]
            result = theme_clustering.build_text_themes(papers)
            concept_ids = {theme.get("concept_id") for theme in result["themes"]}

            self.assertNotIn("concept:quality_of_service_routing", concept_ids)

    def test_runtime_text_fallback_matches_pure_chinese_alias_with_internal_punctuation(self) -> None:
        for alias in ("服务质量-路由", "服务质量/路由", "服务质量（路由）"):
            papers = [
                {
                    "paper_id": str(index),
                    "title": f"{alias} 研究",
                    "abstract": f"{alias} 用于网络路径选择，{alias} 是核心方法。",
                }
                for index in range(3)
            ]
            result = theme_clustering.build_text_themes(papers)
            concept_ids = {theme.get("concept_id") for theme in result["themes"]}

            self.assertIn("concept:quality_of_service_routing", concept_ids)

    def test_runtime_text_fallback_matches_greek_symbol_alias_with_internal_punctuation(self) -> None:
        for alias in ("μ-阿片受体", "μ 阿片受体"):
            papers = [
                {
                    "paper_id": str(index),
                    "title": f"{alias} 研究",
                    "abstract": f"{alias} 是药理学研究对象，{alias} 是核心主题。",
                }
                for index in range(3)
            ]
            result = theme_clustering.build_text_themes(papers)
            themes = {
                theme.get("concept_id"): theme
                for theme in result["themes"]
                if theme.get("concept_id")
            }

            self.assertIn("concept:receptor_opioid_mu", themes)
            self.assertIn("μ阿片受体", themes["concept:receptor_opioid_mu"]["matched_aliases"]["zh"])

    def test_paper_search_pro_text_fallback_extracts_mixed_cjk_latin_compact_aliases(self) -> None:
        module = load_paper_search_pro_theme_clustering()
        cases = [
            ("H控制", "concept:h_control", "h 控制"),
            ("H∞控制", "concept:h_infinity_control", "h infinity 控制"),
            ("硝酸还原酶(NADPH)", "concept:nitrate_reductase_nadph", "硝酸还原酶 nadph"),
        ]

        for alias, expected_concept_id, expected_matched_alias in cases:
            papers = [
                {
                    "paper_id": str(index),
                    "title": f"{alias} 研究",
                    "abstract": f"{alias} 用于主题别名匹配，{alias} 是核心方法。",
                }
                for index in range(3)
            ]
            result = module.build_text_themes(papers)
            themes = {
                theme.get("concept_id"): theme
                for theme in result["themes"]
                if theme.get("concept_id")
            }

            self.assertIn(expected_concept_id, themes)
            self.assertIn(expected_matched_alias, themes[expected_concept_id]["matched_aliases"]["zh"])

    def test_paper_search_pro_text_fallback_does_not_match_mixed_alias_inside_longer_latin_token(self) -> None:
        module = load_paper_search_pro_theme_clustering()
        for alias in ("pH控制", "AH控制", "p-H控制", "p H控制"):
            papers = [
                {
                    "paper_id": str(index),
                    "title": f"{alias} 研究",
                    "abstract": f"{alias} 用于主题别名匹配，{alias} 是核心方法。",
                }
                for index in range(3)
            ]
            result = module.build_text_themes(papers)
            concept_ids = {theme.get("concept_id") for theme in result["themes"]}

            self.assertNotIn("concept:h_control", concept_ids)

    def test_paper_search_pro_text_fallback_does_not_collapse_ascii_inside_chinese_punctuation_match(self) -> None:
        module = load_paper_search_pro_theme_clustering()
        for alias in ("服务质量Q路由", "服务质量123路由"):
            papers = [
                {
                    "paper_id": str(index),
                    "title": f"{alias} 研究",
                    "abstract": f"{alias} 用于网络路径选择，{alias} 是核心方法。",
                }
                for index in range(3)
            ]
            result = module.build_text_themes(papers)
            concept_ids = {theme.get("concept_id") for theme in result["themes"]}

            self.assertNotIn("concept:quality_of_service_routing", concept_ids)

    def test_paper_search_pro_text_fallback_matches_pure_chinese_alias_with_internal_punctuation(self) -> None:
        module = load_paper_search_pro_theme_clustering()
        for alias in ("服务质量-路由", "服务质量/路由", "服务质量（路由）"):
            papers = [
                {
                    "paper_id": str(index),
                    "title": f"{alias} 研究",
                    "abstract": f"{alias} 用于网络路径选择，{alias} 是核心方法。",
                }
                for index in range(3)
            ]
            result = module.build_text_themes(papers)
            concept_ids = {theme.get("concept_id") for theme in result["themes"]}

            self.assertIn("concept:quality_of_service_routing", concept_ids)

    def test_paper_search_pro_text_fallback_matches_greek_symbol_alias_with_internal_punctuation(self) -> None:
        module = load_paper_search_pro_theme_clustering()
        for alias in ("μ-阿片受体", "μ 阿片受体"):
            papers = [
                {
                    "paper_id": str(index),
                    "title": f"{alias} 研究",
                    "abstract": f"{alias} 是药理学研究对象，{alias} 是核心主题。",
                }
                for index in range(3)
            ]
            result = module.build_text_themes(papers)
            themes = {
                theme.get("concept_id"): theme
                for theme in result["themes"]
                if theme.get("concept_id")
            }

            self.assertIn("concept:receptor_opioid_mu", themes)
            self.assertIn("μ阿片受体", themes["concept:receptor_opioid_mu"]["matched_aliases"]["zh"])


if __name__ == "__main__":
    unittest.main()
