import json
import os
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

fetcher_stub = types.ModuleType("vpnsci_sustech.fetcher")


class _StubPaperFetcher:
    def __init__(self, *args, **kwargs):
        pass

    def fetch(self, *args, **kwargs):
        raise NotImplementedError("PaperFetcher.fetch is not available in this test stub.")

    def fetch_from_search_hit(self, *args, **kwargs):
        raise NotImplementedError("PaperFetcher.fetch_from_search_hit is not available in this test stub.")

    def close(self):
        pass


fetcher_stub.PaperFetcher = _StubPaperFetcher
sys.modules.setdefault("vpnsci_sustech.fetcher", fetcher_stub)

sources_pkg = types.ModuleType("vpnsci_sustech.sources")
sources_pkg.__path__ = [str(Path(__file__).resolve().parents[1] / "vpnsci_sustech" / "sources")]
sys.modules.setdefault("vpnsci_sustech.sources", sources_pkg)

from vpnsci_sustech.paper_search_pro_adapter import (
    _load_seed,
    _reconcile_quality_profile_with_chart_signals,
    _write_materialized_data,
    render_report,
)
from vpnsci_sustech.theme_candidate_resolution import (
    THEME_CANDIDATE_RESOLUTION_REQUEST_FILENAME,
    THEME_CANDIDATE_RESOLUTION_RESULT_FILENAME,
)
from vpnsci_sustech.theme_postprocess import THEME_POSTPROCESS_REQUEST_FILENAME, THEME_POSTPROCESS_RESULT_FILENAME
from vpnsci_sustech.sources.search_cache import SearchSession
from vpnsci_sustech.sources.search_models import SearchHit
from vpnsci_sustech.theme_clustering import (
    THEME_GENERIC_LABELS_EN,
    THEME_LEXICON_EN_PATH,
    THEME_LEXICON_ZH_PATH,
    THEME_STOPWORDS_ZH,
    build_keyword_topic_themes,
    build_text_themes,
)


class WritableTemporaryDirectory:
    def __enter__(self):
        self._base = Path(os.environ.get("VPN_SCI_TEST_TMP", "F:/AI playground/TempFiles"))
        self._base.mkdir(parents=True, exist_ok=True)
        self._tmp = tempfile.TemporaryDirectory(dir=self._base)
        return self._tmp.__enter__()

    def __exit__(self, exc_type, exc, tb):
        return self._tmp.__exit__(exc_type, exc, tb)


class PaperSearchProAdapterTests(unittest.TestCase):
    def test_text_theme_fallback_ignores_venue_metadata_terms(self):
        themes = build_text_themes(
            [
                {
                    "paper_id": "a",
                    "title": "Millimeter wave filter design",
                    "abstract": "",
                    "venue": "Proceedings of the Fifteenth National Millimeter Wave Conference",
                },
                {
                    "paper_id": "b",
                    "title": "Millimeter wave coupler synthesis",
                    "abstract": "",
                    "venue": "Proceedings of the Fifteenth National Millimeter Wave Conference",
                },
            ]
        )

        theme_names = {theme["name"] for theme in themes["themes"]}
        self.assertIn("Millimeter Wave", theme_names)
        self.assertTrue(all("Conference" not in name for name in theme_names))
        self.assertTrue(all("Proceedings" not in name for name in theme_names))

    def test_text_theme_fallback_ignores_school_and_proceedings_terms_in_title_only_recovery(self):
        themes = build_text_themes(
            [
                {
                    "paper_id": "a",
                    "title": "北京邮电大学 硕士学位论文 毫米波滤波器设计",
                    "abstract": "",
                },
                {
                    "paper_id": "b",
                    "title": "第十五届全国毫米波亚毫米波学术会议论文集 毫米波耦合器综合",
                    "abstract": "",
                },
            ]
        )

        theme_names = {theme["name"] for theme in themes["themes"]}
        self.assertIn("毫米波", theme_names)
        banned = ("大学", "学位", "论文集", "会议")
        self.assertTrue(all(all(token not in name for token in banned) for name in theme_names))

    def test_keyword_topic_clustering_ignores_school_and_proceedings_noise_terms(self):
        themes = build_keyword_topic_themes(
            [
                {
                    "paper_id": "a",
                    "keywords": ["毫米波滤波器", "北京邮电大学", "Proceedings of ICNC"],
                    "topics": [],
                },
                {
                    "paper_id": "b",
                    "keywords": ["毫米波滤波器", "硕士学位论文", "Conference on RF"],
                    "topics": [],
                },
            ],
            min_papers=1,
        )

        theme_names = {theme["name"] for theme in themes["themes"]}
        self.assertIn("毫米波滤波器", theme_names)
        banned = ("大学", "学位", "论文集", "会议", "Conference", "Proceedings", "University")
        self.assertTrue(all(all(token not in name for token in banned) for name in theme_names))

    def test_chinese_theme_fallback_uses_external_lexicon_file(self):
        self.assertTrue(THEME_LEXICON_ZH_PATH.exists())
        payload = json.loads(THEME_LEXICON_ZH_PATH.read_text(encoding="utf-8"))

        self.assertIn("generic_terms", payload)
        self.assertIn("connector_terms", payload)
        self.assertIn("theme_shape_suffixes", payload)
        self.assertIn("患者", payload["generic_terms"])
        self.assertIn("通过", payload["connector_terms"])
        self.assertIn("剂量学", payload["theme_shape_suffixes"])
        self.assertIn("患者", THEME_STOPWORDS_ZH)

    def test_english_theme_fallback_uses_external_generic_label_lexicon(self):
        self.assertTrue(THEME_LEXICON_EN_PATH.exists())
        payload = json.loads(THEME_LEXICON_EN_PATH.read_text(encoding="utf-8"))

        self.assertIn("generic_label_terms", payload)
        self.assertIn("treatment", payload["generic_label_terms"])
        self.assertIn("which", payload["token_stopwords"])
        self.assertIn("treatment", THEME_GENERIC_LABELS_EN)

        themes = build_text_themes(
            [
                {
                    "paper_id": "a",
                    "title": "Treatment protocol for disease",
                    "abstract": "Patients receive drug treatment through a protocol which reports mechanism.",
                },
                {
                    "paper_id": "b",
                    "title": "Disease treatment mechanism",
                    "abstract": "Drug treatment and patient disease mechanisms are discussed.",
                },
                {
                    "paper_id": "c",
                    "title": "Patient drug treatment",
                    "abstract": "The purpose is treatment of disease through drug protocol.",
                },
            ]
        )

        self.assertEqual(themes["themes"], [])
        self.assertEqual(themes["status"], "insufficient_text_theme_signal")

    def test_text_theme_fallback_marks_low_signal_for_repeated_narrative_fragments_plus_singleton_phrase(self):
        themes = build_text_themes(
            [
                {
                    "paper_id": "a",
                    "title": "治疗协议研究",
                    "abstract": "进一步描述了该协议过程中治疗疾病的方法。",
                },
                {
                    "paper_id": "b",
                    "title": "疾病治疗过程分析",
                    "abstract": "进一步提供了该协议过程中患者药物治疗描述。",
                },
                {
                    "paper_id": "c",
                    "title": "低频超声电导药物透入治疗",
                    "abstract": "进一步提供了过程中相互作用和治疗方案。",
                },
            ]
        )

        self.assertEqual(themes["themes"], [])
        self.assertEqual(themes["status"], "insufficient_text_theme_signal")

    def test_reconcile_quality_profile_with_chart_signals_promotes_disabled_topic_mode_to_limited(self):
        profile = {"topic_analysis_mode": "disabled"}
        chart_data = {
            "theme_treemap": {
                "themes": [{"name": "Federated Learning", "value": 2, "paper_ids": ["a", "b"]}],
            }
        }

        reconciled = _reconcile_quality_profile_with_chart_signals(profile, chart_data)

        self.assertIsNot(reconciled, profile)
        self.assertEqual(reconciled["topic_analysis_mode"], "limited")

    def test_reconcile_quality_profile_with_chart_signals_keeps_disabled_without_effective_themes(self):
        profile = {"topic_analysis_mode": "disabled"}
        chart_data = {
            "theme_treemap": {
                "themes": [{"name": "Paper Set", "value": 0, "paper_ids": []}],
            }
        }

        reconciled = _reconcile_quality_profile_with_chart_signals(profile, chart_data)

        self.assertEqual(reconciled["topic_analysis_mode"], "disabled")

    def test_materialized_data_uses_display_query_language_and_coverage_metadata(self):
        with WritableTemporaryDirectory() as tmp:
            output_dir = Path(tmp)
            session = SearchSession(
                session_id="search-test",
                query="infrared thermography body temperature",
                filters={},
                origin={"engine": "openalex", "kind": "source_execution"},
                hits=[
                    SearchHit(
                        title="High systematic review for fever detection",
                        doi="10.1/high",
                        year=2025,
                        citation_count=5,
                        query_variant="infrared thermometry",
                        query_variant_type="translated_keywords",
                        query_variants=["translated_keywords:infrared thermometry"],
                    ),
                    SearchHit(
                        title="Close",
                        doi="10.1/close",
                        year=2024,
                        citation_count=3,
                        query_variant="non-contact body temperature measurement",
                        query_variant_type="translated_keywords",
                    ),
                    SearchHit(title="Other", doi="10.1/other", year=2023, citation_count=1),
                    SearchHit(title="Other 2", doi="10.1/other2", year=2022, citation_count=1),
                    SearchHit(title="Other 3", doi="10.1/other3", year=2021, citation_count=1),
                    SearchHit(title="Other 4", doi="10.1/other4", year=2020, citation_count=1),
                    SearchHit(title="Other 5", doi="10.1/other5", year=2019, citation_count=1),
                    SearchHit(title="Other 6", doi="10.1/other6", year=2018, citation_count=1),
                ],
                source_summary={"openalex": 8},
            )

            materialized = _write_materialized_data(
                session,
                output_dir,
                display_query="红外线测量",
                language="zh",
            )

            metadata = json.loads((materialized / "metadata.json").read_text(encoding="utf-8"))
            chart_data = json.loads((materialized / "chart_data.json").read_text(encoding="utf-8"))
            papers = json.loads((materialized / "paper_list.json").read_text(encoding="utf-8"))

            self.assertEqual(metadata["query"], "红外线测量")
            self.assertEqual(metadata["language"], "zh")
            self.assertEqual(metadata["mode"], "vpnsci-seed-report")
            self.assertEqual(metadata["report_mode"], "seed_preview")
            self.assertEqual(metadata["user_query"], "红外线测量")
            self.assertEqual(metadata["display_query"], "红外线测量")
            self.assertEqual(metadata["seed_session_query"], "infrared thermography body temperature")
            self.assertEqual(metadata["coverage_label"], "seed preview estimate")
            self.assertEqual(metadata["query_display"]["primary"], "红外线测量")
            self.assertIn(
                {"type": "translated_keywords", "query": "infrared thermometry"},
                metadata["query_display"]["expanded"],
            )
            self.assertEqual(
                metadata["query_display"]["actual_queries"],
                [
                    {
                        "source": "OpenAlex",
                        "queries": [
                            "infrared thermometry",
                            "non-contact body temperature measurement",
                        ],
                    }
                ],
            )
            self.assertIn(
                {"type": "translated_keywords", "query": "non-contact body temperature measurement"},
                metadata["actual_query_variants"],
            )
            self.assertEqual(metadata["search_id"], "search-test")
            self.assertEqual(metadata["papers_evaluated"], 8)
            self.assertEqual(metadata["papers_in_kg"], 8)
            self.assertIn("coverage_estimate", metadata)
            self.assertIn("coverage_ci", metadata)
            self.assertIn("discovery_curve", chart_data)
            self.assertIn("publication_year", chart_data)
            self.assertIn("relevance_score", chart_data)
            self.assertEqual(
                chart_data["discovery_curve"]["points"][-1],
                {"papers_screened": 8, "found": 0},
            )
            self.assertIn("summary", chart_data["discovery_curve"])
            self.assertEqual(papers[0]["rcs"], 5)
            self.assertEqual(papers[0]["discovery_path"], "query: 红外线测量")

    def test_seed_preview_marks_scaffold_rcs_invalid_and_excludes_it_from_rcs_stats(self):
        with WritableTemporaryDirectory() as tmp:
            session = SearchSession(
                session_id="search-rcs-scaffold",
                query="graph neural network",
                filters={},
                origin={"engine": "openalex", "kind": "source_execution"},
                hits=[
                    SearchHit(title="Graph neural networks for molecules", doi="10.1/a", year=2024),
                    SearchHit(title="Graph representation learning", doi="10.1/b", year=2023),
                ],
                source_summary={"openalex": 2},
            )

            materialized = _write_materialized_data(
                session,
                Path(tmp),
                display_query="graph neural network",
                language="en",
            )

            metadata = json.loads((materialized / "metadata.json").read_text(encoding="utf-8"))
            chart_data = json.loads((materialized / "chart_data.json").read_text(encoding="utf-8"))
            papers = json.loads((materialized / "paper_list.json").read_text(encoding="utf-8"))

            self.assertTrue(papers)
            for paper in papers:
                self.assertEqual(paper["rcs"], 5)
                self.assertFalse(paper["rcs_valid"])
                self.assertEqual(paper["rcs_source"], "scaffold")
                self.assertEqual(paper["rcs_flag"], "scaffold_neutral")
                self.assertIn("formal RCS classification was not executed", paper["rcs_reasoning"])

            self.assertEqual(metadata["rcs_execution_mode"], "none")
            self.assertEqual(metadata["rcs_scope"], "none")
            self.assertEqual(metadata["rcs_valid_count"], 0)
            self.assertEqual(metadata["rcs_total_count"], 2)
            self.assertEqual(metadata["highly_relevant_count"], 0)
            self.assertEqual(metadata["closely_related_count"], 0)
            self.assertIn("unavailable", metadata["rcs_notice"].lower())
            self.assertEqual(chart_data["relevance_score"]["bins"], [])
            self.assertIsNone(chart_data["relevance_score"]["mean"])
            self.assertEqual(chart_data["relevance_score"]["n"], 0)

    def test_parse_failed_uncertain_rcs_result_is_invalid_and_excluded_from_stats(self):
        with WritableTemporaryDirectory() as tmp:
            session = SearchSession(
                session_id="search-rcs-parser-fallback",
                query="graph neural network",
                filters={},
                hits=[
                    SearchHit(title="Malformed metadata paper", doi="10.1/malformed", year=2024),
                ],
                source_summary={"openalex": 1},
            )

            materialized = _write_materialized_data(
                session,
                Path(tmp),
                display_query="graph neural network",
                language="en",
                report_mode="seed_classified",
                rcs_classification_result=[
                    {
                        "paper_id": "10.1/malformed",
                        "rcs": 5,
                        "reasoning": "The classifier output could not be trusted for this malformed record.",
                        "flag": "parse_failed_uncertain",
                    }
                ],
                rcs_execution_mode="main_agent_serial",
            )

            metadata = json.loads((materialized / "metadata.json").read_text(encoding="utf-8"))
            chart_data = json.loads((materialized / "chart_data.json").read_text(encoding="utf-8"))
            papers = json.loads((materialized / "paper_list.json").read_text(encoding="utf-8"))

            self.assertEqual(papers[0]["rcs"], 5)
            self.assertFalse(papers[0]["rcs_valid"])
            self.assertEqual(papers[0]["rcs_source"], "parser_fallback")
            self.assertEqual(papers[0]["rcs_flag"], "parse_failed_uncertain")
            self.assertEqual(metadata["rcs_execution_mode"], "main_agent_serial")
            self.assertEqual(metadata["rcs_scope"], "none")
            self.assertEqual(metadata["rcs_valid_count"], 0)
            self.assertEqual(metadata["highly_relevant_count"], 0)
            self.assertEqual(metadata["closely_related_count"], 0)
            self.assertEqual(chart_data["relevance_score"]["bins"], [])
            self.assertEqual(chart_data["relevance_score"]["n"], 0)

    def test_seed_preview_generates_generic_theme_fallback_from_title_and_abstract(self):
        with WritableTemporaryDirectory() as tmp:
            session = SearchSession(
                session_id="search-test",
                query="machine learning for medical imaging",
                filters={},
                hits=[
                    SearchHit(
                        title="Deep learning for medical image segmentation",
                        doi="10.1/seg",
                        abstract="Medical image segmentation with deep learning and neural network methods.",
                    ),
                    SearchHit(
                        title="Machine learning approaches to MRI image classification",
                        doi="10.1/mri",
                        abstract="MRI image classification with machine learning models.",
                    ),
                    SearchHit(
                        title="Optimization methods for machine learning systems",
                        doi="10.1/opt",
                        abstract="Optimization for machine learning training and model selection.",
                    ),
                ],
                source_summary={"openalex": 2, "semantic_scholar": 1},
            )

            materialized = _write_materialized_data(
                session,
                Path(tmp),
                display_query="machine learning for medical imaging",
                language="en",
            )

            chart_data = json.loads((materialized / "chart_data.json").read_text(encoding="utf-8"))
            report_data = json.loads((materialized / "report_data.json").read_text(encoding="utf-8"))

            treemap = chart_data["theme_treemap"]
            self.assertEqual(treemap["total_papers"], 3)
            self.assertEqual(treemap["method"], "seed_text_frequency_fallback")
            self.assertGreaterEqual(len(treemap["themes"]), 2)
            theme_names = {theme["name"] for theme in treemap["themes"]}
            self.assertNotIn("非接触测温/热筛查", theme_names)
            self.assertNotIn("红外热成像/热像仪", theme_names)
            self.assertIn("Machine Learning", theme_names)
            self.assertIn("Image", theme_names)
            for theme in treemap["themes"]:
                self.assertIsInstance(theme["value"], int)
                self.assertGreater(theme["value"], 0)
                self.assertTrue(theme["paper_ids"])
            self.assertEqual(report_data["chart_data"]["theme_treemap"], treemap)

    def test_seed_preview_text_theme_fallback_prefers_domain_phrases_over_generic_chinese_terms(self):
        with WritableTemporaryDirectory() as tmp:
            session = SearchSession(
                session_id="search-cn-medical",
                query="核物理治疗方法",
                filters={},
                hits=[
                    SearchHit(
                        title="靶向放射性核素治疗在肿瘤精准治疗中的应用",
                        doi="10.1/a",
                        abstract="靶向放射性核素治疗用于肿瘤患者精准治疗，讨论剂量学和放射生物学。",
                    ),
                    SearchHit(
                        title="硼中子俘获治疗的剂量学和放射生物学进展",
                        doi="10.1/b",
                        abstract="硼中子俘获治疗结合剂量学评估和放射生物学机制，用于恶性肿瘤治疗。",
                    ),
                    SearchHit(
                        title="α粒子治疗和核医学治疗的临床应用",
                        doi="10.1/c",
                        abstract="α粒子治疗、核医学治疗和靶向放射性核素治疗是精准肿瘤治疗方向。",
                    ),
                ],
                source_summary={"openalex": 3},
            )

            materialized = _write_materialized_data(
                session,
                Path(tmp),
                display_query="核物理治疗方法",
                language="zh",
            )

            chart_data = json.loads((materialized / "chart_data.json").read_text(encoding="utf-8"))
            treemap = chart_data["theme_treemap"]
            theme_names = {theme["name"] for theme in treemap["themes"]}

            self.assertEqual(treemap["method"], "seed_text_frequency_fallback")
            self.assertIn("靶向放射性核素治疗", theme_names)
            bnct = next(
                theme for theme in treemap["themes"]
                if theme.get("concept_id") == "concept:boron_neutron_capture_therapy"
            )
            self.assertEqual(bnct["method"], "concept_alias_text_fallback")
            self.assertEqual(bnct["matched_aliases"], {"zh": ["硼中子俘获治疗"]})
            self.assertNotIn("治疗", theme_names)
            self.assertNotIn("进行", theme_names)
            self.assertNotIn("通过", theme_names)
            self.assertNotIn("患者", theme_names)

    def test_seed_preview_text_theme_fallback_marks_low_signal_when_only_generic_chinese_terms_remain(self):
        themes = build_text_themes(
            [
                {
                    "paper_id": "a",
                    "title": "治疗方法研究",
                    "abstract": "患者通过药物进行治疗，目的在于改善疾病作用。",
                },
                {
                    "paper_id": "b",
                    "title": "疾病治疗分析",
                    "abstract": "患者通过方法进行治疗，药物作用和疾病结果。",
                },
                {
                    "paper_id": "c",
                    "title": "药物作用研究",
                    "abstract": "通过治疗方法分析患者疾病和药物作用。",
                },
            ]
        )

        self.assertEqual(themes["themes"], [])
        self.assertEqual(themes["method"], "text_frequency_fallback")
        self.assertEqual(themes["status"], "insufficient_text_theme_signal")

    def test_seed_preview_raw_theme_treemap_keeps_low_signal_audit_candidates(self):
        with WritableTemporaryDirectory() as tmp:
            session = SearchSession(
                session_id="search-low-signal-themes",
                query="generic treatment methods",
                filters={},
                hits=[
                    SearchHit(title="治疗方法研究", doi="10.1/a", abstract="患者通过药物进行治疗，目的在于改善疾病作用。"),
                    SearchHit(title="疾病治疗分析", doi="10.1/b", abstract="患者通过方法进行治疗，药物作用和疾病结果。"),
                ],
                source_summary={"openalex": 2},
            )

            materialized = _write_materialized_data(session, Path(tmp), language="zh")

            chart_data = json.loads((materialized / "chart_data.json").read_text(encoding="utf-8"))
            raw = chart_data["raw_theme_treemap"]
            display = chart_data["theme_treemap"]
            self.assertGreater(len(raw["themes"]), 0)
            self.assertEqual(raw["status"], "low_signal_candidates")
            self.assertEqual(display["themes"], [])
            self.assertEqual(display["status"], "insufficient_text_theme_signal")

    def test_text_theme_fallback_merges_cross_language_concept_aliases(self):
        themes = build_text_themes(
            [
                {
                    "paper_id": "a",
                    "title": "Wireless communication systems",
                    "abstract": "Wireless communications improve beamforming performance.",
                },
                {
                    "paper_id": "b",
                    "title": "无线通信波束成形方法",
                    "abstract": "无线通信系统使用波束成形算法。",
                },
            ]
        )

        theme_names = {theme["name"] for theme in themes["themes"]}
        self.assertIn("Wireless Communication / 无线通信", theme_names)
        self.assertNotIn("Wireless Communication", theme_names)
        self.assertNotIn("无线通信", theme_names)
        wireless = next(theme for theme in themes["themes"] if theme["name"] == "Wireless Communication / 无线通信")
        self.assertEqual(wireless["value"], 2)
        self.assertEqual(set(wireless["paper_ids"]), {"a", "b"})
        self.assertEqual(wireless["method"], "concept_alias_text_fallback")

    def test_text_theme_fallback_preserves_accepted_chinese_alias_phrases(self):
        themes = build_text_themes(
            [
                {
                    "paper_id": "a",
                    "title": "主从系统同步控制",
                    "abstract": "主从系统用于复杂网络同步。",
                },
                {
                    "paper_id": "b",
                    "title": "复杂网络中的主从系统设计",
                    "abstract": "主从系统控制提高同步稳定性。",
                },
            ]
        )

        theme_names = {theme["name"] for theme in themes["themes"]}
        self.assertIn("Master-slave Systems / 主从系统", theme_names)
        self.assertNotIn("主从系", theme_names)
        master_slave = next(
            theme for theme in themes["themes"]
            if theme["name"] == "Master-slave Systems / 主从系统"
        )
        self.assertEqual(master_slave["concept_id"], "concept:master_slave_system")
        self.assertEqual(master_slave["value"], 2)
        self.assertEqual(set(master_slave["paper_ids"]), {"a", "b"})
        self.assertEqual(master_slave["matched_aliases"], {"zh": ["主从系统"]})
        self.assertEqual(master_slave["method"], "concept_alias_text_fallback")

    def test_seed_preview_prefers_keywords_frequency_clustering_before_text_fallback(self):
        with WritableTemporaryDirectory() as tmp:
            session = SearchSession(
                session_id="search-test",
                query="general healthcare query",
                filters={},
                hits=[
                    SearchHit(
                        title="Paper A",
                        doi="10.1/a",
                        abstract="Mixed abstract without repeated useful title terms.",
                        keywords=["federated learning", "privacy"],
                    ),
                    SearchHit(
                        title="Paper B",
                        doi="10.1/b",
                        abstract="Another abstract without repeated useful title terms.",
                        keywords=["federated learning", "hospital ai"],
                    ),
                    SearchHit(
                        title="Paper C",
                        doi="10.1/c",
                        abstract="Third abstract without repeated useful title terms.",
                        keywords=["privacy"],
                    ),
                ],
                source_summary={"openalex": 3},
            )

            materialized = _write_materialized_data(
                session,
                Path(tmp),
                display_query="general healthcare query",
                language="en",
            )

            chart_data = json.loads((materialized / "chart_data.json").read_text(encoding="utf-8"))
            treemap = chart_data["theme_treemap"]
            theme_names = {theme["name"] for theme in treemap["themes"]}

            self.assertEqual(treemap["method"], "seed_keywords_topics_frequency_fallback")
            self.assertIn("Federated Learning", theme_names)
            self.assertIn("Privacy", theme_names)

    def test_seed_preview_generates_lightweight_prisma_s_disclosure(self):
        with WritableTemporaryDirectory() as tmp:
            session = SearchSession(
                session_id="search-test",
                query="infrared thermography",
                filters={},
                hits=[
                    SearchHit(
                        title="Infrared thermography",
                        doi="10.1/a",
                        source="openalex",
                        query_variant="infrared thermography",
                        query_variant_type="original",
                    ),
                    SearchHit(
                        title="Non-contact body temperature",
                        doi="10.1/b",
                        source="semantic_scholar",
                        query_variant="non-contact body temperature",
                        query_variant_type="expanded",
                    ),
                ],
                source_summary={"openalex": 1, "semantic_scholar": 1},
            )

            materialized = _write_materialized_data(session, Path(tmp))

            prisma_log = json.loads((materialized / "prisma_log.json").read_text(encoding="utf-8"))
            report_data = json.loads((materialized / "report_data.json").read_text(encoding="utf-8"))
            canonical_keys = [key for key in prisma_log if key[:1].isdigit()]

            self.assertEqual(len(canonical_keys), 16)
            self.assertNotIn("prisma_s", prisma_log)
            self.assertFalse(prisma_log["_meta"]["is_full_prisma_s"])
            self.assertEqual(prisma_log["_meta"]["mode"], "seed_preview")
            self.assertEqual(prisma_log["1_database_information"]["databases"], ["openalex", "semantic_scholar"])
            self.assertTrue(prisma_log["2_multi_database_searching"]["performed"])
            self.assertEqual(prisma_log["14_total_records"]["records"], 2)
            self.assertEqual(prisma_log["15_deduplication"]["deduped_records"], 2)
            self.assertIn(
                {"type": "expanded", "query": "non-contact body temperature"},
                prisma_log["8_full_search_strategies"]["query_variants"],
            )
            self.assertEqual(report_data["prisma_log"], prisma_log)
            self.assertFalse((materialized / "execution_log.json").exists())

    def test_materialized_data_infers_chinese_language_from_display_query(self):
        with WritableTemporaryDirectory() as tmp:
            session = SearchSession(
                session_id="search-test",
                query="infrared",
                filters={},
                hits=[SearchHit(title="Paper", doi="10.1/a")],
            )

            materialized = _write_materialized_data(
                session,
                Path(tmp),
                display_query="非接触体温测量",
            )

            metadata = json.loads((materialized / "metadata.json").read_text(encoding="utf-8"))
            self.assertEqual(metadata["language"], "zh")

    def test_actual_query_groups_can_fall_back_to_session_filters(self):
        with WritableTemporaryDirectory() as tmp:
            session = SearchSession(
                session_id="search-test",
                query="红外线测量",
                filters={
                    "query_variants": [
                        {"query": "红外线测量", "variant_type": "original"},
                        {"query": "infrared measurement", "variant_type": "translated_keywords"},
                    ]
                },
                hits=[SearchHit(title="Paper", doi="10.1/a")],
            )

            materialized = _write_materialized_data(
                session,
                Path(tmp),
                display_query="红外线测量",
                language="zh",
            )

            metadata = json.loads((materialized / "metadata.json").read_text(encoding="utf-8"))
            self.assertEqual(
                metadata["query_display"]["actual_queries"],
                [{"source": "seed", "queries": ["infrared measurement"]}],
            )

    def test_actual_query_groups_can_use_source_summary_with_filter_variants(self):
        with WritableTemporaryDirectory() as tmp:
            session = SearchSession(
                session_id="search-test",
                query="红外线测量",
                filters={
                    "query_variants": [
                        {"query": "红外线测量", "variant_type": "original"},
                        {"query": "infrared measurement", "variant_type": "translated_keywords"},
                    ]
                },
                hits=[SearchHit(title="Paper", doi="10.1/a")],
                source_summary={"openalex": 1},
            )

            materialized = _write_materialized_data(
                session,
                Path(tmp),
                display_query="different visible query",
                language="en",
            )

            metadata = json.loads((materialized / "metadata.json").read_text(encoding="utf-8"))
            self.assertEqual(
                metadata["query_display"]["actual_queries"],
                [{"source": "OpenAlex", "queries": ["红外线测量", "infrared measurement"]}],
            )

    def test_actual_query_groups_preserve_all_variants_for_merged_multisource_hits(self):
        with WritableTemporaryDirectory() as tmp:
            session = SearchSession(
                session_id="search-test",
                query="红外线测量",
                filters={
                    "query_variants": [
                        {"query": "红外线测量", "variant_type": "original"},
                        {"query": "infrared measurement", "variant_type": "translated_keywords"},
                    ]
                },
                hits=[
                    SearchHit(
                        title="Merged paper",
                        doi="10.1/merged",
                        query_variant="红外线测量",
                        query_variant_type="original",
                        query_variants=[
                            "original:红外线测量",
                            "translated_keywords:infrared measurement",
                        ],
                        sources=["openalex", "semantic_scholar"],
                    )
                ],
                source_summary={"openalex": 1, "semantic_scholar": 1},
            )

            materialized = _write_materialized_data(
                session,
                Path(tmp),
                display_query="红外线测量",
                language="zh",
            )

            metadata = json.loads((materialized / "metadata.json").read_text(encoding="utf-8"))
            self.assertEqual(
                metadata["query_display"]["actual_queries"],
                [
                    {"source": "OpenAlex", "queries": ["红外线测量", "infrared measurement"]},
                    {"source": "Semantic Scholar", "queries": ["红外线测量", "infrared measurement"]},
                ],
            )

    def test_materialized_data_uses_persisted_hit_key_for_paper_identity(self):
        with WritableTemporaryDirectory() as tmp:
            session = SearchSession(
                session_id="search-test",
                query="infrared",
                filters={},
                hits=[
                    SearchHit(
                        title="Paper",
                        doi="10.1/a",
                        hit_key="doi:10.1/a",
                    )
                ],
            )

            materialized = _write_materialized_data(
                session,
                Path(tmp),
                display_query="infrared",
            )

            papers = json.loads((materialized / "paper_list.json").read_text(encoding="utf-8"))
            self.assertEqual(papers[0]["id"], "doi:10.1/a")
            self.assertEqual(papers[0]["paper_id"], "doi:10.1/a")

    def test_seed_preview_degrades_discovery_and_citation_for_thin_cnki_html_import_subset(self):
        with WritableTemporaryDirectory() as tmp:
            session = SearchSession(
                session_id="search-cnki-thin",
                query="钙钛矿",
                display_query="钙钛矿结果集合",
                filters={"backend": "cnki"},
                origin={"engine": "cnki", "kind": "html_import"},
                hits=[
                    SearchHit(title="题名一", cnki_id="A1", hit_key="cnki:A1", year=2024, source="cnki", sources=["cnki"]),
                    SearchHit(title="题名二", cnki_id="A2", hit_key="cnki:A2", year=2023, source="cnki", sources=["cnki"]),
                    SearchHit(title="题名三", cnki_id="A3", hit_key="cnki:A3", year=2022, source="cnki", sources=["cnki"]),
                    SearchHit(title="题名四", cnki_id="A4", hit_key="cnki:A4", year=2021, source="cnki", sources=["cnki"]),
                    SearchHit(title="题名五", cnki_id="A5", hit_key="cnki:A5", year=2020, source="cnki", sources=["cnki"]),
                    SearchHit(title="题名六", cnki_id="A6", hit_key="cnki:A6", year=2019, source="cnki", sources=["cnki"]),
                ],
                source_summary={"cnki": 6},
            )

            materialized = _write_materialized_data(
                session,
                Path(tmp),
                display_query="钙钛矿结果集合",
                language="zh",
            )

            metadata = json.loads((materialized / "metadata.json").read_text(encoding="utf-8"))
            chart_data = json.loads((materialized / "chart_data.json").read_text(encoding="utf-8"))

            self.assertEqual(metadata["query"], "钙钛矿结果集合")
            self.assertEqual(metadata["original_query"], "钙钛矿")
            self.assertEqual(metadata["display_query"], "钙钛矿结果集合")
            self.assertEqual(metadata["query_display"]["primary"], "钙钛矿结果集合")
            self.assertEqual(metadata["quality_profile"]["query_trace_level"], "imported")
            self.assertEqual(metadata["quality_profile"]["audit_level"], "limited")
            self.assertEqual(metadata["quality_profile"]["title_mode"], "search")
            self.assertEqual(metadata["quality_profile"]["query_strip_mode"], "hidden")
            self.assertEqual(metadata["quality_profile"]["discovery_curve_mode"], "disabled")
            self.assertEqual(metadata["quality_profile"]["citation_analysis_mode"], "disabled")
            self.assertEqual(chart_data["discovery_curve"]["mode"], "disabled")
            self.assertEqual(chart_data["discovery_curve"]["status"], "missing_data")
            self.assertIn("执行轨迹", chart_data["discovery_curve"]["reason"])
            self.assertIsNone(chart_data["discovery_curve"]["coverage_estimate"])
            self.assertEqual(metadata["coverage_ci"], [None, None])
            self.assertIsNone(metadata["coverage_estimate"])
            self.assertEqual(chart_data["citation_analysis"]["mode"], "disabled")
            self.assertEqual(chart_data["citation_analysis"]["status"], "insufficient_data")

    def test_recovered_label_without_original_query_uses_recovered_summary_wording(self):
        with WritableTemporaryDirectory() as tmp:
            session = SearchSession(
                session_id="search-recovered",
                query="",
                display_query="",
                recovered_label="CNKI 下载结果集合",
                origin={"engine": "cnki", "kind": "weak_recovery"},
                filters={},
                hits=[SearchHit(title="题名一", cnki_id="A1", hit_key="cnki:A1")],
                source_summary={"cnki": 1},
            )

            materialized = _write_materialized_data(
                session,
                Path(tmp),
                language="zh",
            )

            metadata = json.loads((materialized / "metadata.json").read_text(encoding="utf-8"))
            self.assertEqual(metadata["query"], "CNKI 下载结果集合")
            self.assertEqual(metadata["original_query"], "")
            self.assertEqual(metadata["display_query"], "")
            self.assertEqual(metadata["recovered_label"], "CNKI 下载结果集合")
            self.assertEqual(metadata["quality_profile"]["title_mode"], "recovered_summary")
            self.assertEqual(metadata["report_label_mode"], "恢复总结")

    def test_title_only_weak_recovery_with_theme_treemap_signal_is_limited_not_disabled(self):
        with WritableTemporaryDirectory() as tmp:
            session = SearchSession(
                session_id="search-weak-topic",
                query="",
                display_query="",
                recovered_label="本地文件结果集合",
                origin={"engine": "cnki", "kind": "weak_recovery", "report_recovery_capability": "degraded"},
                filters={"recovered_from": "local_files"},
                hits=[
                    SearchHit(title="Federated learning in hospital systems", local_file="a.pdf", source="local_file", sources=["local_file"]),
                    SearchHit(title="Hospital privacy in federated learning", local_file="b.pdf", source="local_file", sources=["local_file"]),
                    SearchHit(title="Clinical federated learning deployment", local_file="c.pdf", source="local_file", sources=["local_file"]),
                ],
                source_summary={"local_file": 3},
            )

            materialized = _write_materialized_data(
                session,
                Path(tmp),
                language="en",
            )

            metadata = json.loads((materialized / "metadata.json").read_text(encoding="utf-8"))
            chart_data = json.loads((materialized / "chart_data.json").read_text(encoding="utf-8"))
            treemap = chart_data["theme_treemap"]

            self.assertEqual(treemap["method"], "seed_text_frequency_fallback")
            self.assertTrue(treemap["themes"])
            self.assertEqual(metadata["quality_profile"]["topic_analysis_mode"], "limited")

    def test_local_file_recovery_reconstructs_prefixed_display_title_from_theme_signal(self):
        with WritableTemporaryDirectory() as tmp:
            session = SearchSession(
                session_id="search-local-display",
                query="",
                display_query="",
                recovered_label="Recovered local files",
                origin={"engine": "cnki", "kind": "weak_recovery", "report_recovery_capability": "degraded"},
                filters={"recovered_from": "local_files"},
                hits=[
                    SearchHit(title="Federated learning in hospital systems", local_file="a.pdf", source="local_file", sources=["local_file"]),
                    SearchHit(title="Hospital privacy in federated learning", local_file="b.pdf", source="local_file", sources=["local_file"]),
                    SearchHit(title="Clinical federated learning deployment", local_file="c.pdf", source="local_file", sources=["local_file"]),
                ],
                source_summary={"local_file": 3},
            )

            materialized = _write_materialized_data(
                session,
                Path(tmp),
                language="zh",
            )

            metadata = json.loads((materialized / "metadata.json").read_text(encoding="utf-8"))
            report_data = json.loads((materialized / "report_data.json").read_text(encoding="utf-8"))

            self.assertEqual(metadata["original_query"], "")
            self.assertEqual(metadata["recovered_label"], "Recovered local files")
            self.assertEqual(metadata["display_query"], "Federated Learning / Hospital")
            self.assertEqual(metadata["display_title"], "[本地文件恢复]：Federated Learning / Hospital")
            self.assertEqual(metadata["query"], "[本地文件恢复]：Federated Learning / Hospital")
            self.assertEqual(metadata["query_display"]["primary"], "[本地文件恢复]：Federated Learning / Hospital")
            self.assertEqual(metadata["display_query_source"], "theme_treemap")
            self.assertEqual(metadata["recovery_kind"], "C")
            self.assertIn("Federated Learning / Hospital", metadata["summary"])
            self.assertEqual(report_data["summary"], metadata["summary"])

    def test_legacy_report_recovery_keeps_history_prefix_even_when_trace_is_weak(self):
        with WritableTemporaryDirectory() as tmp:
            session = SearchSession(
                session_id="search-legacy-display",
                query="",
                display_query="历史标题",
                recovered_label="",
                origin={"engine": "cnki", "kind": "weak_recovery", "report_recovery_capability": "compatible"},
                filters={"recovered_from": "legacy_report_json"},
                hits=[
                    SearchHit(title="历史报告论文", source="cnki", sources=["cnki"]),
                ],
                source_summary={"cnki": 1},
            )

            materialized = _write_materialized_data(
                session,
                Path(tmp),
                language="zh",
            )

            metadata = json.loads((materialized / "metadata.json").read_text(encoding="utf-8"))

            self.assertEqual(metadata["recovery_kind"], "B")
            self.assertEqual(metadata["display_query"], "历史标题")
            self.assertEqual(metadata["display_title"], "[历史报告恢复]：历史标题")
            self.assertEqual(metadata["query"], "[历史报告恢复]：历史标题")

    def test_download_sidecar_display_prefix_does_not_pollute_actual_query_groups(self):
        with WritableTemporaryDirectory() as tmp:
            session = SearchSession(
                session_id="search-download-display",
                query="滤波耦合器",
                display_query="滤波耦合器结果集合",
                recovered_label="",
                origin={"engine": "cnki", "kind": "download_sidecar", "report_recovery_capability": "standard"},
                filters={
                    "recovered_from": "download_sidecar",
                    "query_variants": [
                        {"type": "original", "query": "滤波耦合器"},
                    ],
                },
                hits=[
                    SearchHit(title=f"滤波耦合器文献{i}", cnki_id=f"A{i}", hit_key=f"cnki:A{i}", year=2024 - i, citation_count=10, source="cnki", sources=["cnki"])
                    for i in range(1, 9)
                ],
                source_summary={"cnki": 8},
            )

            materialized = _write_materialized_data(
                session,
                Path(tmp),
                language="zh",
            )

            metadata = json.loads((materialized / "metadata.json").read_text(encoding="utf-8"))

            self.assertEqual(metadata["display_query"], "滤波耦合器结果集合")
            self.assertEqual(metadata["display_title"], "[下载记录恢复]：滤波耦合器结果集合")
            self.assertEqual(metadata["query"], "[下载记录恢复]：滤波耦合器结果集合")
            flattened_queries = [
                query
                for group in metadata["query_display"]["actual_queries"]
                for query in group.get("queries", [])
            ]
            self.assertIn("滤波耦合器", flattened_queries)
            self.assertTrue(all("[下载记录恢复]" not in query for query in flattened_queries))

    def test_seed_preview_records_raw_theme_treemap_and_waiting_agent_postprocess_trace(self):
        with WritableTemporaryDirectory() as tmp:
            session = SearchSession(
                session_id="search-theme-postprocess",
                query="federated learning in hospitals",
                filters={},
                hits=[
                    SearchHit(
                        title="Federated learning for hospital prediction",
                        doi="10.1/a",
                        abstract="Federated learning improves hospital prediction systems.",
                    ),
                    SearchHit(
                        title="Hospital privacy with federated learning",
                        doi="10.1/b",
                        abstract="Privacy preserving federated learning for hospital data.",
                    ),
                ],
                source_summary={"openalex": 2},
            )

            materialized = _write_materialized_data(
                session,
                Path(tmp),
                display_query="federated learning in hospitals",
                language="en",
            )

            chart_data = json.loads((materialized / "chart_data.json").read_text(encoding="utf-8"))
            report_data = json.loads((materialized / "report_data.json").read_text(encoding="utf-8"))

            self.assertIn("raw_theme_treemap", chart_data)
            self.assertIn("theme_postprocess", chart_data)
            self.assertEqual(chart_data["raw_theme_treemap"], chart_data["theme_treemap"])
            self.assertEqual(chart_data["theme_postprocess"]["attempted"], False)
            self.assertEqual(chart_data["theme_postprocess"]["reason"], "agent_postprocess_not_supplied")
            self.assertEqual(report_data["chart_data"]["theme_postprocess"], chart_data["theme_postprocess"])
            self.assertTrue((materialized / THEME_POSTPROCESS_REQUEST_FILENAME).exists())

    def test_seed_preview_applies_host_agent_theme_postprocess_result_when_present(self):
        with WritableTemporaryDirectory() as tmp:
            output_dir = Path(tmp)
            session = SearchSession(
                session_id="search-theme-postprocess-apply",
                query="federated learning in hospitals",
                filters={},
                hits=[
                    SearchHit(
                        title="Federated learning for hospital prediction",
                        doi="10.1/a",
                        abstract="Federated learning improves hospital prediction systems.",
                    ),
                    SearchHit(
                        title="Hospital privacy with federated learning",
                        doi="10.1/b",
                        abstract="Privacy preserving federated learning for hospital data.",
                    ),
                ],
                source_summary={"openalex": 2},
            )

            bootstrap = _write_materialized_data(
                session,
                output_dir,
                display_query="federated learning in hospitals",
                language="en",
            )
            result_payload = {
                "groups": [
                    {"label": "Federated Learning", "theme_indices": [0]},
                    {"label": "Hospital Privacy", "theme_indices": [1]},
                ]
            }
            (bootstrap / THEME_POSTPROCESS_RESULT_FILENAME).write_text(
                json.dumps(result_payload, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

            materialized = _write_materialized_data(
                session,
                output_dir,
                display_query="federated learning in hospitals",
                language="en",
            )

            chart_data = json.loads((materialized / "chart_data.json").read_text(encoding="utf-8"))
            self.assertEqual(chart_data["theme_postprocess"]["attempted"], True)
            self.assertEqual(chart_data["theme_postprocess"]["reason"], "applied")
            self.assertEqual(chart_data["theme_postprocess"]["model"], "host-agent")
            theme_names = {theme["name"] for theme in chart_data["theme_treemap"]["themes"]}
            self.assertIn("Federated Learning", theme_names)

    def test_seed_preview_writes_candidate_resolution_request_for_low_signal_ambiguous_aliases(self):
        with WritableTemporaryDirectory() as tmp:
            session = SearchSession(
                session_id="search-theme-candidate-resolution",
                query="网络攻击检测",
                filters={},
                hits=[
                    SearchHit(title="网络攻击检测综述", doi="10.1/a", abstract="恶意软件和入侵检测研究。"),
                    SearchHit(title="网络攻击防御系统", doi="10.1/b", abstract="安全流量分析和攻击识别。"),
                    SearchHit(title="无关论文", doi="10.1/c", abstract="低信号文本。"),
                ],
                source_summary={"openalex": 3},
            )
            candidate_match = {
                "alias_key": "zh:网络攻击",
                "surface": "网络攻击",
                "paper_ids": ["doi:10.1/a"],
                "candidates": [
                    {
                        "concept_id": "concept:cyber_attack",
                        "canonical": {"en": "Cyber Attack", "zh": ""},
                        "domains": ["computer_science"],
                        "parents": [],
                        "specificity": 80,
                        "risk_tags": ["needs_context"],
                    }
                ],
            }

            with mock.patch(
                "vpnsci_sustech.theme_candidate_resolution._ambiguous_candidate_matches",
                return_value=[candidate_match],
            ):
                materialized = _write_materialized_data(
                    session,
                    Path(tmp),
                    display_query="网络攻击检测",
                    language="zh",
                )

            chart_data = json.loads((materialized / "chart_data.json").read_text(encoding="utf-8"))

            self.assertTrue((materialized / THEME_CANDIDATE_RESOLUTION_REQUEST_FILENAME).exists())
            self.assertEqual(chart_data["theme_candidate_resolution"]["attempted"], False)
            self.assertEqual(chart_data["theme_candidate_resolution"]["reason"], "agent_resolution_not_supplied")
            self.assertEqual(chart_data["theme_treemap"]["themes"], [])
            request = json.loads((materialized / THEME_CANDIDATE_RESOLUTION_REQUEST_FILENAME).read_text(encoding="utf-8"))
            self.assertEqual(request["candidate_aliases"][0]["alias_key"], "zh:网络攻击")

    def test_seed_preview_applies_candidate_resolution_result_when_present(self):
        with WritableTemporaryDirectory() as tmp:
            output_dir = Path(tmp)
            session = SearchSession(
                session_id="search-theme-candidate-apply",
                query="网络攻击检测",
                filters={},
                hits=[
                    SearchHit(title="网络攻击检测综述", doi="10.1/a", abstract="恶意软件和入侵检测研究。"),
                    SearchHit(title="网络攻击防御系统", doi="10.1/b", abstract="安全流量分析和攻击识别。"),
                    SearchHit(title="无关论文", doi="10.1/c", abstract="低信号文本。"),
                ],
                source_summary={"openalex": 3},
            )
            candidate_match = {
                "alias_key": "zh:网络攻击",
                "surface": "网络攻击",
                "paper_ids": ["doi:10.1/a"],
                "candidates": [
                    {
                        "concept_id": "concept:cyber_attack",
                        "canonical": {"en": "Cyber Attack", "zh": "网络攻击"},
                        "domains": ["computer_science"],
                        "parents": [],
                        "specificity": 80,
                        "risk_tags": ["needs_context"],
                    }
                ],
            }
            with mock.patch(
                "vpnsci_sustech.theme_candidate_resolution._ambiguous_candidate_matches",
                return_value=[candidate_match],
            ):
                bootstrap = _write_materialized_data(
                    session,
                    output_dir,
                    display_query="网络攻击检测",
                    language="zh",
                )
            (bootstrap / THEME_CANDIDATE_RESOLUTION_RESULT_FILENAME).write_text(
                json.dumps(
                    {
                        "schema_version": "theme_candidate_resolution_result.v1",
                        "decisions": [
                            {
                                "decision": "resolved",
                                "alias_key": "zh:网络攻击",
                                "concept_id": "concept:cyber_attack",
                                "paper_ids": ["doi:10.1/a"],
                                "evidence": ["title directly mentions 网络攻击检测"],
                            }
                        ],
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )

            with mock.patch(
                "vpnsci_sustech.theme_candidate_resolution._ambiguous_candidate_matches",
                return_value=[candidate_match],
            ):
                materialized = _write_materialized_data(
                    session,
                    output_dir,
                    display_query="网络攻击检测",
                    language="zh",
                )

            chart_data = json.loads((materialized / "chart_data.json").read_text(encoding="utf-8"))
            themes = chart_data["theme_treemap"]["themes"]

            self.assertEqual(chart_data["theme_candidate_resolution"]["attempted"], True)
            self.assertEqual(chart_data["theme_candidate_resolution"]["reason"], "applied")
            resolved = {theme.get("concept_id"): theme for theme in themes}
            self.assertEqual(resolved["concept:cyber_attack"]["source"], "ambiguous_candidate_resolution")

    def test_download_sidecar_with_formal_query_trace_keeps_standard_like_method_modes(self):
        with WritableTemporaryDirectory() as tmp:
            session = SearchSession(
                session_id="search-recovered-a",
                query="滤波耦合器",
                display_query="滤波耦合器结果集合",
                recovered_label="",
                origin={"engine": "cnki", "kind": "download_sidecar", "report_recovery_capability": "standard"},
                filters={
                    "query_variants": [
                        {"type": "original", "query": "滤波耦合器"},
                    ]
                },
                hits=[
                    SearchHit(title=f"题名{i}", cnki_id=f"A{i}", hit_key=f"cnki:A{i}", year=2024 - i, citation_count=10, source="cnki", sources=["cnki"])
                    for i in range(1, 9)
                ],
                source_summary={"cnki": 8},
            )

            materialized = _write_materialized_data(
                session,
                Path(tmp),
                language="zh",
            )

            metadata = json.loads((materialized / "metadata.json").read_text(encoding="utf-8"))
            chart_data = json.loads((materialized / "chart_data.json").read_text(encoding="utf-8"))
            self.assertEqual(metadata["quality_profile"]["audit_level"], "full")
            self.assertEqual(metadata["quality_profile"]["query_strip_mode"], "actual_queries")
            self.assertEqual(metadata["quality_profile"]["discovery_curve_mode"], "enabled")
            self.assertEqual(chart_data["discovery_curve"]["mode"], "enabled")

    def test_render_report_can_open_report_after_rendering(self):
        with WritableTemporaryDirectory() as tmp:
            base = Path(tmp)
            seed = base / "seed.json"
            output_dir = base / "report"
            session = SearchSession(
                session_id="search-test",
                query="infrared",
                filters={},
                hits=[SearchHit(title="Paper", doi="10.1/a")],
            )
            from dataclasses import asdict

            seed.write_text(json.dumps(asdict(session), ensure_ascii=False), encoding="utf-8")

            with mock.patch(
                "vpnsci_sustech.paper_search_pro_adapter.render_html_webartifacts",
                side_effect=lambda materialized_data_dir, output_path, **kwargs: output_path.write_text(
                    "<html></html>", encoding="utf-8"
                )
                or output_path,
            ), mock.patch("vpnsci_sustech.paper_search_pro_adapter.webbrowser.open") as open_mock:
                report = render_report(seed, output_dir, display_query="红外线测量", language="zh", open_report=True)

            self.assertEqual(report, output_dir / "report.html")
            open_mock.assert_called_once()


if __name__ == "__main__":
    unittest.main()
