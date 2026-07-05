from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import re
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
        )

        self.assertEqual(alias_index["zh:网络药理学"]["concept_id"], "concept:network_pharmacology")
        self.assertEqual(alias_index["en:network pharmacology"]["specificity"], 70)

    def test_rejects_unsupported_compact_alias_index_schema_or_status(self) -> None:
        index_path = self.root / "theme_concept_alias_index.json"
        base_payload = {
            "schema_version": "theme_concept_alias_index.v1",
            "build_status": "review_complete",
            "normalization": "theme_concept_alias_normalization.v1",
            "concepts": {},
            "aliases": {},
        }

        for field, value, pattern in (
            ("schema_version", "theme_concept_alias_index.v0", "Unsupported theme concept alias index schema_version"),
            ("normalization", "theme_concept_alias_normalization.v0", "Unsupported theme concept alias normalization"),
            ("build_status", "partial_review_pending", "Theme concept alias index is not review_complete"),
        ):
            payload = dict(base_payload)
            payload[field] = value
            index_path.write_text(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, pattern):
                theme_clustering._load_theme_concept_aliases(index_path=index_path)

    def test_paper_search_pro_rejects_unsupported_compact_alias_index_schema_or_status(self) -> None:
        module = load_paper_search_pro_theme_clustering()
        index_path = self.root / "theme_concept_alias_index.json"
        base_payload = {
            "schema_version": "theme_concept_alias_index.v1",
            "build_status": "review_complete",
            "normalization": "theme_concept_alias_normalization.v1",
            "concepts": {},
            "aliases": {},
        }

        for field, value, pattern in (
            ("schema_version", "theme_concept_alias_index.v0", "Unsupported theme concept alias index schema_version"),
            ("normalization", "theme_concept_alias_normalization.v0", "Unsupported theme concept alias normalization"),
            ("build_status", "partial_review_pending", "Theme concept alias index is not review_complete"),
        ):
            payload = dict(base_payload)
            payload[field] = value
            index_path.write_text(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, pattern):
                module._load_theme_concept_aliases(index_path=index_path)

    def test_does_not_fall_back_to_legacy_full_overlay_when_index_missing(self) -> None:
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

        with self.assertRaisesRegex(FileNotFoundError, "compact alias index is required"):
            theme_clustering._load_theme_concept_aliases(index_path=self.root / "missing_index.json")

        module = load_paper_search_pro_theme_clustering()
        with self.assertRaisesRegex(FileNotFoundError, "compact alias index is required"):
            module._load_theme_concept_aliases(index_path=self.root / "missing_index.json")

        self.assertTrue(legacy_path.exists())

    def test_runtime_has_no_generated_topic_or_inflated_technology_aliases(self) -> None:
        payload = json.loads((REPO_ROOT / "vpnsci_sustech" / "data" / "theme_concept_alias_index.json").read_text(encoding="utf-8"))
        concepts = payload["concepts"]
        bad_topic: list[tuple[str, str, str]] = []
        bad_technology: list[tuple[str, str, str]] = []
        known_named_technologies = {"lora 技术", "lorawan 技术", "lte advanced 技术", "nosql 技术", "塑化技术"}

        for alias_key, concept_id in payload["aliases"].items():
            if not alias_key.startswith("zh:"):
                continue
            alias = alias_key[3:]
            canonical_en = str((concepts[str(concept_id)].get("canonical") or {}).get("en") or "")
            canonical_key = canonical_en.casefold()
            item = (str(concept_id), canonical_en, alias)
            if alias.endswith("主题") and not re.search(r"\b(as topic|topics?|subjects?|headings?)\b", canonical_key):
                bad_topic.append(item)
            concept_key = f"{concept_id} {canonical_key}"
            if (
                alias.endswith("技术")
                and alias not in known_named_technologies
                and not re.search(r"(technic|techniq|technolog|technical)", concept_key)
            ):
                bad_technology.append(item)

        self.assertEqual(bad_topic[:20], [])
        self.assertEqual(bad_technology[:20], [])

    def test_runtime_alias_keys_match_compact_index_mixed_cjk_latin_normalization(self) -> None:
        cases = {
            "H控制": "zh:h 控制",
            "H∞控制": "zh:h infinity 控制",
            "硝酸还原酶(NADPH)": "zh:硝酸还原酶 nadph",
            "C++语言": "zh:c++ 语言",
            "H+/K+交换ATP酶": "zh:h+ k+ 交换 atp 酶",
            "琥珀酸半醛脱氢酶(NADP+)": "zh:琥珀酸半醛脱氢酶 nadp+",
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
            "C++语言": "zh:c++ 语言",
            "H+/K+交换ATP酶": "zh:h+ k+ 交换 atp 酶",
            "琥珀酸半醛脱氢酶(NADP+)": "zh:琥珀酸半醛脱氢酶 nadp+",
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

    def test_runtime_text_fallback_preserves_plus_sign_semantics(self) -> None:
        bad_cases = [
            ("C语言", "concept:c"),
            ("H/K交换ATP酶", "concept:h_k_exchanging_atpase"),
            ("琥珀酸半醛脱氢酶(NADP)", "concept:succinate_semialdehyde_dehydrogenase_nadp"),
        ]

        for alias, forbidden_concept_id in bad_cases:
            papers = [
                {
                    "paper_id": str(index),
                    "title": f"{alias} 研究",
                    "abstract": f"{alias} 是本文反复出现的关键词，{alias} 不是带加号的主题。",
                }
                for index in range(3)
            ]
            result = theme_clustering.build_text_themes(papers)
            concept_ids = {theme.get("concept_id") for theme in result["themes"]}

            self.assertNotIn(forbidden_concept_id, concept_ids)

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

    def test_paper_search_pro_text_fallback_matches_package_redundancy_filter(self) -> None:
        module = load_paper_search_pro_theme_clustering()
        papers = [
            {
                "paper_id": str(index),
                "title": "无线传感器网络研究",
                "abstract": "无线传感器网络用于环境监测。",
            }
            for index in range(3)
        ]

        package_names = [theme["name"] for theme in theme_clustering.build_text_themes(papers)["themes"]]
        tool_names = [theme["name"] for theme in module.build_text_themes(papers)["themes"]]

        self.assertEqual(tool_names, package_names)

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

    def test_paper_search_pro_text_fallback_preserves_plus_sign_semantics(self) -> None:
        module = load_paper_search_pro_theme_clustering()
        bad_cases = [
            ("C语言", "concept:c"),
            ("H/K交换ATP酶", "concept:h_k_exchanging_atpase"),
            ("琥珀酸半醛脱氢酶(NADP)", "concept:succinate_semialdehyde_dehydrogenase_nadp"),
        ]

        for alias, forbidden_concept_id in bad_cases:
            papers = [
                {
                    "paper_id": str(index),
                    "title": f"{alias} 研究",
                    "abstract": f"{alias} 是本文反复出现的关键词，{alias} 不是带加号的主题。",
                }
                for index in range(3)
            ]
            result = module.build_text_themes(papers)
            concept_ids = {theme.get("concept_id") for theme in result["themes"]}

            self.assertNotIn(forbidden_concept_id, concept_ids)

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
