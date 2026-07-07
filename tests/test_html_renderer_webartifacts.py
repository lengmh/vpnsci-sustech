import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import skipUnless


ROOT = Path(__file__).resolve().parents[1]
PSP_ROOT = ROOT / "tools" / "paper-search-pro"
if str(PSP_ROOT) not in sys.path:
    sys.path.insert(0, str(PSP_ROOT))

from scripts.html_renderer_webartifacts import PREBUILT_BUNDLE, _build_report_data, render_html_webartifacts
from scripts.data_materialization import _build_theme_chart_payload, _build_themes
from scripts.discovery_curve import build_discovery_curve_payload
from scripts.theme_postprocess import THEME_POSTPROCESS_REQUEST_FILENAME, THEME_POSTPROCESS_RESULT_FILENAME
from scripts.types import UnifiedPaperEntity

try:
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.edge.options import Options
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.support.ui import WebDriverWait

    SELENIUM_AVAILABLE = True
except Exception:
    SELENIUM_AVAILABLE = False


class WritableTemporaryDirectory:
    def __enter__(self):
        self._base = Path(os.environ.get("VPN_SCI_TEST_TMP", "F:/AI playground/TempFiles"))
        self._base.mkdir(parents=True, exist_ok=True)
        self._tmp = tempfile.TemporaryDirectory(dir=self._base)
        return self._tmp.__enter__()

    def __exit__(self, exc_type, exc, tb):
        return self._tmp.__exit__(exc_type, exc, tb)


class HtmlRendererWebartifactsCompatTests(unittest.TestCase):
    def test_data_materialization_cli_exposes_serial_fallback_metadata_flags(self):
        env = dict(os.environ)
        env["PYTHONPATH"] = str(PSP_ROOT)
        completed = subprocess.run(
            [sys.executable, "-m", "scripts.data_materialization", "--help"],
            cwd=str(ROOT),
            env=env,
            capture_output=True,
            text=True,
            check=True,
        )

        self.assertIn("--stop-reason", completed.stdout)
        self.assertIn("--workflow-kind", completed.stdout)
        self.assertIn("--execution-mode", completed.stdout)
        self.assertIn("--execution-fallback-reason", completed.stdout)

    def test_discovery_curve_compacts_zero_yield_stages_before_fit(self):
        payload = build_discovery_curve_payload(
            [
                {"papers_evaluated": 2, "highly_relevant_count": 2},
                {"papers_evaluated": 2, "highly_relevant_count": 2},
                {"papers_evaluated": 5, "highly_relevant_count": 5},
                {"papers_evaluated": 8, "highly_relevant_count": 6},
            ],
            scope="seed_set",
        )

        self.assertEqual(payload["mode"], "enabled")
        self.assertEqual(payload["status"], "ok")
        self.assertEqual(
            [(point["papers_screened"], point["found"]) for point in payload["points"]],
            [(2, 2), (5, 5), (8, 6)],
        )

    def test_render_html_webartifacts_adds_compat_fields_for_full_like_payload(self):
        metadata = {
            "search_id": "serial-full-workflow-kernel-medical-therapy",
            "query": "核物理治疗方法",
            "tier": "standard",
            "papers_evaluated": 2,
            "papers_in_kg": 2,
            "highly_relevant_count": 2,
            "closely_related_count": 0,
            "coverage_estimate": 0.465,
            "coverage_ci": [0.385, 0.545],
            "generated_at": "2026-06-05T10:54:03.828207",
            "skill_version": "paper-search-pro/2.0",
            "execution_fallback_reason": "subagents_unavailable_user_chose_serial",
            "stop_reason": "budget_max_papers (180)",
            "user_query": "核物理治疗方法",
            "display_query": "核物理治疗方法",
            "query_display": {
                "user_query": "核物理治疗方法",
                "primary": "核物理治疗方法",
                "actual_queries": [
                    {
                        "source": "OpenAlex",
                        "queries": [
                            "核物理治疗方法",
                            "targeted radionuclide therapy radiopharmaceutical therapy cancer review",
                        ],
                    }
                ],
            },
        }
        paper_list = [
            {
                "paper_id": "10.1/a",
                "title": "Targeted Radionuclide Therapy",
                "authors_full": ["Alice A", "Bob B"],
                "year": 2020,
                "venue": "Journal A",
                "doi": "10.1/a",
                "doi_url": "https://doi.org/10.1/a",
                "abstract": "Core review",
                "tldr": None,
                "rcs": 9,
                "rcs_reasoning": "Core paper.",
                "rcs_flag": None,
                "citation_count": 120,
                "influential_citation_count": None,
                "discovery_path": "query: 核物理治疗方法",
                "sources": ["openalex"],
                "is_oa": True,
            },
            {
                "paper_id": "10.1/b",
                "title": "Particle Therapy Review",
                "authors_full": ["Carol C"],
                "year": 2021,
                "venue": "Journal B",
                "doi": "10.1/b",
                "doi_url": "https://doi.org/10.1/b",
                "abstract": "Second paper",
                "tldr": None,
                "rcs": 8,
                "rcs_reasoning": "Highly relevant.",
                "rcs_flag": None,
                "citation_count": 90,
                "influential_citation_count": None,
                "discovery_path": "query: 核物理治疗方法",
                "sources": ["openalex"],
                "is_oa": True,
            },
        ]
        chart_data = {
            "publication_year": {
                "bins": [
                    {"year": 2020, "total": 1, "highly_relevant": 1},
                    {"year": 2021, "total": 1, "highly_relevant": 1},
                ],
                "year_min": 2020,
                "year_max": 2021,
            },
            "relevance_score": {
                "bins": [{"rcs": i, "count": 0} for i in range(11)],
                "mean": 8.5,
                "ci_low": 8.0,
                "ci_high": 9.0,
                "n": 2,
            },
            "discovery_curve": {
                "points": [{"n": 2, "y": 2}],
                "tau": 24.3,
                "coverage_estimate": 0.465,
                "ci_low": 0.385,
                "ci_high": 0.545,
                "estimated_total_relevant": 4.3,
                "summary": "Estimated to have found about 2 relevant papers.",
            },
            "citation_network": {
                "nodes": [
                    {"id": "10.1/a", "year": 2020, "citation_count": 120, "rcs": 9, "title": "Targeted Radionuclide Therapy"},
                    {"id": "10.1/b", "year": 2021, "citation_count": 90, "rcs": 8, "title": "Particle Therapy Review"},
                ],
                "edges": [],
                "node_count": 2,
                "edge_count": 0,
            },
            "theme_treemap": {
                "themes": [
                    {"name": "Targeted Radionuclide Therapy", "value": 2, "paper_ids": ["10.1/a", "10.1/b"]}
                ],
                "total_papers": 2,
            },
        }
        prisma_log = {"1_database_information": {"databases": ["openalex"]}}

        with WritableTemporaryDirectory() as tmp:
            materialized = Path(tmp) / "materialized"
            materialized.mkdir(parents=True, exist_ok=True)
            (materialized / "metadata.json").write_text(
                json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            (materialized / "paper_list.json").write_text(
                json.dumps(paper_list, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            (materialized / "chart_data.json").write_text(
                json.dumps(chart_data, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            (materialized / "prisma_log.json").write_text(
                json.dumps(prisma_log, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            out = Path(tmp) / "report.html"
            render_html_webartifacts(
                materialized,
                out,
                user_query="核物理治疗方法",
                language="zh",
            )
            html = out.read_text(encoding="utf-8")
            match = re.search(
                r'window\.__REPORT_DATA__ = (\{.*?\});</script><script',
                html,
                re.S,
            )
            self.assertIsNotNone(match)
            report_data = json.loads(match.group(1))

        meta = report_data["metadata"]
        chart = report_data["chart_data"]

        self.assertEqual(meta["query"], "核物理治疗方法")
        self.assertEqual(meta["original_query"], "核物理治疗方法")
        self.assertEqual(meta["language"], "zh")
        self.assertEqual(meta["seed_source"], "openalex")
        self.assertEqual(meta["seed_session_query"], "核物理治疗方法")
        self.assertEqual(meta["seed_session_id"], "serial-full-workflow-kernel-medical-therapy")
        self.assertEqual(meta["total_papers"], 2)
        self.assertEqual(meta["coverage_label"], "compat estimate")
        self.assertEqual(meta["source_summary"], {"openalex": 2})
        self.assertEqual(meta["mode"], "vpnsci-compat-report")
        self.assertEqual(meta["report_mode"], "full")
        self.assertNotIn("quality_profile", meta)
        self.assertEqual(
            meta["query_display"]["actual_queries"],
            [
                {
                    "source": "OpenAlex",
                    "queries": [
                        "核物理治疗方法",
                        "targeted radionuclide therapy radiopharmaceutical therapy cancer review",
                    ],
                }
            ],
        )
        self.assertEqual(
            meta["actual_query_variants"],
            [
                {"type": "original", "query": "核物理治疗方法"},
                {
                    "type": "expanded",
                    "query": "targeted radionuclide therapy radiopharmaceutical therapy cancer review",
                },
            ],
        )
        self.assertEqual(
            meta["query_display"]["expanded"],
            meta["actual_query_variants"],
        )
        self.assertEqual(chart["year_counts"], {"2020": 1, "2021": 1})
        self.assertEqual(chart["source_summary"], {"openalex": 2})
        self.assertEqual(chart["total_papers"], 2)
        self.assertNotIn("citation_analysis", chart)
        self.assertNotIn("mode", chart["discovery_curve"])
        self.assertNotIn("status", chart["discovery_curve"])
        self.assertEqual(
            chart["theme_treemap"]["method"],
            "compat_renderer_fallback",
        )
        self.assertIn("Compatibility metadata", chart["theme_treemap"]["note"])

    def test_build_report_data_preserves_existing_seed_preview_compat_fields(self):
        metadata = {
            "query": "红外线测量",
            "original_query": "infrared thermography body temperature",
            "language": "zh",
            "seed_source": "openalex",
            "seed_session_query": "infrared thermography body temperature",
            "seed_session_id": "search-seed",
            "quality_profile": {"query_trace_level": "exact"},
            "report_mode": "seed_preview",
            "mode": "vpnsci-seed-report",
            "coverage_label": "seed preview estimate",
            "report_label_mode": "检索结果",
            "missing_fields": [],
            "insufficient_analysis_fields": [],
            "source_summary": {"openalex": 8},
            "total_papers": 8,
            "query_display": {
                "user_query": "红外线测量",
                "primary": "红外线测量",
                "expanded": [{"type": "original", "query": "infrared thermometry"}],
                "actual_queries": [{"source": "OpenAlex", "queries": ["infrared thermometry"]}],
            },
            "actual_query_variants": [{"type": "original", "query": "infrared thermometry"}],
        }
        chart_data = {
            "year_counts": {"2024": 2},
            "source_summary": {"openalex": 8},
            "total_papers": 8,
            "citation_analysis": {"mode": "enabled", "status": "ok", "reason": ""},
            "discovery_curve": {"mode": "enabled", "status": "ok"},
            "theme_treemap": {
                "themes": [{"name": "Medical Imaging", "value": 2, "paper_ids": ["10.1/a", "10.1/b"]}],
                "total_papers": 8,
                "method": "seed_keywords_topics_frequency_fallback",
                "note": "Seed preview topic fallback.",
            },
        }

        report_data = _build_report_data(
            metadata=metadata,
            paper_list=[],
            chart_data=chart_data,
            prisma_log_raw={},
            user_query="红外线测量",
        )

        meta = report_data["metadata"]
        chart = report_data["chart_data"]

        self.assertEqual(meta["mode"], "vpnsci-seed-report")
        self.assertEqual(meta["report_mode"], "seed_preview")
        self.assertEqual(meta["coverage_label"], "seed preview estimate")
        self.assertEqual(meta["seed_session_id"], "search-seed")
        self.assertEqual(meta["actual_query_variants"], [{"type": "original", "query": "infrared thermometry"}])
        self.assertEqual(meta["query_display"]["expanded"], [{"type": "original", "query": "infrared thermometry"}])
        self.assertEqual(chart["year_counts"], {"2024": 2})
        self.assertEqual(chart["citation_analysis"]["mode"], "enabled")
        self.assertEqual(chart["theme_treemap"]["method"], "seed_keywords_topics_frequency_fallback")

    def test_render_html_webartifacts_keeps_missing_actual_queries_missing(self):
        metadata = {
            "search_id": "weak-recovery-report",
            "query": "filtering coupler",
            "display_query": "filtering coupler",
            "seed_session_query": "filtering coupler",
            "report_mode": "full",
            "mode": "vpnsci-compat-report",
            "missing_fields": ["actual_queries", "citation_count"],
        }
        chart_data = {
            "publication_year": {
                "bins": [{"year": 2025, "total": 2, "highly_relevant": 0}],
            },
            "discovery_curve": {
                "coverage_estimate": None,
                "ci_low": None,
                "ci_high": None,
                "estimated_total_relevant": None,
            },
        }

        with WritableTemporaryDirectory() as tmp:
            materialized = Path(tmp) / "materialized"
            materialized.mkdir(parents=True, exist_ok=True)
            (materialized / "metadata.json").write_text(
                json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            (materialized / "paper_list.json").write_text(
                json.dumps([], ensure_ascii=False, indent=2), encoding="utf-8"
            )
            (materialized / "chart_data.json").write_text(
                json.dumps(chart_data, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            (materialized / "prisma_log.json").write_text(
                json.dumps({}, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            out = Path(tmp) / "report.html"
            render_html_webartifacts(
                materialized,
                out,
                user_query="filtering coupler",
                language="en",
            )
            html = out.read_text(encoding="utf-8")
            match = re.search(
                r'window\.__REPORT_DATA__ = (\{.*?\});</script><script',
                html,
                re.S,
            )
            self.assertIsNotNone(match)
            report_data = json.loads(match.group(1))

        meta = report_data["metadata"]
        chart = report_data["chart_data"]

        self.assertEqual(meta["query_display"]["actual_queries"], [])
        self.assertNotIn("expanded", meta["query_display"])
        self.assertNotIn("actual_query_variants", meta)
        self.assertNotIn("quality_profile", meta)
        self.assertNotIn("citation_analysis", chart)
        self.assertNotIn("mode", chart["discovery_curve"])
        self.assertNotIn("status", chart["discovery_curve"])

    def test_build_report_data_keeps_existing_shape_for_seed_preview_payload(self):
        report_data = _build_report_data(
            metadata={"query": "红外线测量", "mode": "vpnsci-seed-report"},
            paper_list=[],
            chart_data={"theme_treemap": {"themes": [], "total_papers": 0}},
            prisma_log_raw={},
            user_query="红外线测量",
            summary="当前文献集主要围绕红外线测量。",
        )
        self.assertEqual(report_data["metadata"]["query"], "红外线测量")
        self.assertEqual(report_data["metadata"]["summary"], "当前文献集主要围绕红外线测量。")
        self.assertEqual(report_data["summary"], "当前文献集主要围绕红外线测量。")
        self.assertEqual(report_data["metadata"]["mode"], "vpnsci-seed-report")

    def test_build_themes_uses_text_fallback_before_generic_group(self):
        themes = _build_themes(
            [
                UnifiedPaperEntity(
                    doi="10.1/a",
                    title="Machine learning for medical imaging",
                    abstract="Machine learning methods for image segmentation and medical diagnosis.",
                    venue="Journal A",
                ),
                UnifiedPaperEntity(
                    doi="10.1/b",
                    title="Image analysis for clinical imaging systems",
                    abstract="Image analysis workflow for clinical diagnosis support.",
                    venue="Journal B",
                ),
                UnifiedPaperEntity(
                    doi="10.1/c",
                    title="Optimization methods for machine learning systems",
                    abstract="Optimization for machine learning training and model selection.",
                    venue="Journal C",
                ),
            ]
        )

        self.assertEqual(themes["total_papers"], 3)
        self.assertEqual(themes["method"], "text_frequency_fallback")
        self.assertGreaterEqual(len(themes["themes"]), 2)
        theme_names = {theme["name"] for theme in themes["themes"]}
        self.assertNotIn("All papers", theme_names)
        self.assertNotIn("Paper Set", theme_names)
        self.assertIn("Machine Learning", theme_names)

    def test_build_themes_merges_cross_language_concept_aliases(self):
        themes = _build_themes(
            [
                UnifiedPaperEntity(
                    doi="10.1/a",
                    title="Wireless communication systems",
                    abstract="Wireless communications improve beamforming performance.",
                    venue="Journal A",
                ),
                UnifiedPaperEntity(
                    doi="10.1/b",
                    title="无线通信波束成形方法",
                    abstract="无线通信系统使用波束成形算法。",
                    venue="Journal B",
                ),
            ]
        )

        theme_names = {theme["name"] for theme in themes["themes"]}
        self.assertIn("Wireless Communication / 无线通信", theme_names)

    def test_build_themes_records_raw_theme_treemap_and_waiting_agent_postprocess_trace(self):
        with WritableTemporaryDirectory() as tmp:
            payload = _build_theme_chart_payload(
                [
                    UnifiedPaperEntity(
                        doi="10.1/a",
                        title="Federated learning for hospitals",
                        abstract="Federated learning for privacy preserving hospital prediction.",
                        venue="Journal A",
                    ),
                    UnifiedPaperEntity(
                        doi="10.1/b",
                        title="Hospital privacy and federated learning",
                        abstract="Hospital privacy in federated learning systems.",
                        venue="Journal B",
                    ),
                ],
                output_dir=Path(tmp),
            )

        self.assertIn("raw_theme_treemap", payload)
        self.assertIn("theme_treemap", payload)
        self.assertIn("theme_postprocess", payload)
        self.assertEqual(payload["raw_theme_treemap"], payload["theme_treemap"])
        self.assertEqual(payload["theme_postprocess"]["attempted"], False)
        self.assertEqual(payload["theme_postprocess"]["reason"], "agent_postprocess_not_supplied")

    def test_build_themes_applies_host_agent_result_when_present(self):
        with WritableTemporaryDirectory() as tmp:
            out_dir = Path(tmp)
            result_payload = {
                "groups": [
                    {"label": "Federated Learning", "theme_indices": [0, 1]},
                    {"label": "Privacy", "theme_indices": [2]},
                ]
            }
            (out_dir / THEME_POSTPROCESS_RESULT_FILENAME).write_text(
                json.dumps(result_payload, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            payload = _build_theme_chart_payload(
                [
                    UnifiedPaperEntity(
                        doi="10.1/a",
                        title="Federated learning for hospitals",
                        abstract="Federated learning for privacy preserving hospital prediction.",
                        venue="Journal A",
                    ),
                    UnifiedPaperEntity(
                        doi="10.1/b",
                        title="Hospital privacy and federated learning",
                        abstract="Hospital privacy in federated learning systems.",
                        venue="Journal B",
                    ),
                ],
                output_dir=out_dir,
            )

            self.assertEqual(payload["theme_postprocess"]["attempted"], True)
            self.assertEqual(payload["theme_postprocess"]["reason"], "applied")
            self.assertEqual(payload["theme_postprocess"]["model"], "host-agent")
            self.assertTrue((out_dir / THEME_POSTPROCESS_REQUEST_FILENAME).exists())

    def test_full_materialization_marks_valid_classifier_rcs_and_records_full_scope(self):
        from scripts.data_materialization import materialize

        with WritableTemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "materialized"
            kg = {
                "10.1/a": UnifiedPaperEntity(
                    doi="10.1/a",
                    title="Directly relevant seed expansion result",
                    year=2024,
                    rcs=6,
                    rcs_reasoning="Adjacent but useful.",
                    rcs_flag="no_abstract_uncertain",
                    citation_count=12,
                )
            }

            materialize(
                kg,
                output_dir,
                user_query="graph neural network",
                rcs_execution_mode="subagent_parallel",
            )

            papers = json.loads((output_dir / "paper_list.json").read_text(encoding="utf-8"))
            metadata = json.loads((output_dir / "metadata.json").read_text(encoding="utf-8"))
            chart_data = json.loads((output_dir / "chart_data.json").read_text(encoding="utf-8"))

        self.assertTrue(papers[0]["rcs_valid"])
        self.assertEqual(papers[0]["rcs_source"], "full_classifier")
        self.assertEqual(papers[0]["rcs_flag"], "no_abstract_uncertain")
        self.assertEqual(metadata["rcs_execution_mode"], "subagent_parallel")
        self.assertEqual(metadata["rcs_scope"], "full_workflow")
        self.assertEqual(metadata["rcs_valid_count"], 1)
        self.assertEqual(metadata["rcs_total_count"], 1)
        self.assertEqual(metadata["closely_related_count"], 1)
        self.assertEqual(chart_data["relevance_score"]["n"], 1)
        self.assertEqual(chart_data["relevance_score"]["bins"][6]["count"], 1)
        self.assertEqual(chart_data["discovery_curve"]["mode"], "disabled")
        self.assertIsNone(chart_data["discovery_curve"]["tau"])
        self.assertIsNone(chart_data["discovery_curve"]["coverage_estimate"])

    def test_full_materialization_marks_parser_fallback_rcs_invalid_and_excludes_stats(self):
        from scripts.data_materialization import materialize

        with WritableTemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "materialized"
            kg = {
                "10.1/a": UnifiedPaperEntity(
                    doi="10.1/a",
                    title="High relevance classified paper",
                    year=2024,
                    rcs=8,
                    rcs_reasoning="Direct match.",
                    citation_count=20,
                ),
                "10.1/b": UnifiedPaperEntity(
                    doi="10.1/b",
                    title="Parser fallback paper",
                    year=2025,
                    rcs=5,
                    rcs_reasoning="Parser fallback.",
                    rcs_flag="parse_failed_uncertain",
                    citation_count=30,
                ),
            }

            materialize(
                kg,
                output_dir,
                user_query="graph neural network",
                rcs_execution_mode="main_agent_serial",
                workflow_kind="full_workflow",
                execution_mode="main_agent_serial",
                execution_fallback_reason="subagents_unavailable_user_chose_serial",
                stop_reason="budget_max_papers (180)",
            )

            papers = json.loads((output_dir / "paper_list.json").read_text(encoding="utf-8"))
            metadata = json.loads((output_dir / "metadata.json").read_text(encoding="utf-8"))
            chart_data = json.loads((output_dir / "chart_data.json").read_text(encoding="utf-8"))

        by_id = {paper["paper_id"]: paper for paper in papers}
        self.assertTrue(by_id["10.1/a"]["rcs_valid"])
        self.assertEqual(by_id["10.1/a"]["rcs_source"], "full_classifier")
        self.assertFalse(by_id["10.1/b"]["rcs_valid"])
        self.assertEqual(by_id["10.1/b"]["rcs_source"], "parser_fallback")
        self.assertEqual(by_id["10.1/b"]["rcs_flag"], "parse_failed_uncertain")
        self.assertEqual(metadata["rcs_execution_mode"], "main_agent_serial")
        self.assertEqual(metadata["report_mode"], "full")
        self.assertEqual(metadata["workflow_kind"], "full_workflow")
        self.assertEqual(metadata["execution_mode"], "main_agent_serial")
        self.assertEqual(
            metadata["execution_fallback_reason"],
            "subagents_unavailable_user_chose_serial",
        )
        self.assertEqual(metadata["stop_reason"], "budget_max_papers (180)")
        self.assertEqual(metadata["rcs_scope"], "full_workflow")
        self.assertEqual(metadata["rcs_valid_count"], 1)
        self.assertEqual(metadata["rcs_total_count"], 2)
        self.assertEqual(metadata["highly_relevant_count"], 1)
        self.assertEqual(metadata["closely_related_count"], 0)
        self.assertEqual(chart_data["relevance_score"]["n"], 1)
        self.assertEqual(chart_data["relevance_score"]["bins"][8]["count"], 1)
        self.assertEqual(chart_data["relevance_score"]["bins"][5]["count"], 0)
        self.assertEqual(
            chart_data["publication_year"]["bins"],
            [
                {"year": 2024, "total": 1, "highly_relevant": 1},
                {"year": 2025, "total": 1, "highly_relevant": 0},
            ],
        )

    @skipUnless(SELENIUM_AVAILABLE, "selenium not available")
    def test_methods_reliability_card_seed_report_uses_bold_upgrade_and_excludes_methodology_title(self):
        metadata = {
            "search_id": "seed-report-reliability-card",
            "query": "红外线测量",
            "display_query": "红外线测量",
            "report_mode": "seed_preview",
            "mode": "vpnsci-seed-report",
            "papers_evaluated": 2,
            "papers_in_kg": 2,
        }
        chart_data = {
            "publication_year": {
                "bins": [{"year": 2025, "total": 2, "highly_relevant": 1}],
            },
            "relevance_score": {
                "bins": [{"rcs": i, "count": 0} for i in range(11)],
                "mean": 7.0,
                "ci_low": 6.5,
                "ci_high": 7.5,
                "n": 2,
            },
            "citation_network": {"nodes": [], "edges": [], "node_count": 0, "edge_count": 0},
            "theme_treemap": {
                "themes": [{"name": "Medical Imaging", "value": 2, "paper_ids": ["10.1/a", "10.1/b"]}],
                "total_papers": 2,
            },
        }
        papers = [
            {
                "paper_id": "10.1/a",
                "title": "Paper A",
                "authors_full": ["A"],
                "year": 2025,
                "venue": "Venue A",
                "abstract": "Abstract A",
                "rcs": 8,
                "citation_count": 0,
                "sources": ["openalex"],
            },
            {
                "paper_id": "10.1/b",
                "title": "Paper B",
                "authors_full": ["B"],
                "year": 2025,
                "venue": "Venue B",
                "abstract": "Abstract B",
                "rcs": 6,
                "citation_count": 0,
                "sources": ["openalex"],
            },
        ]

        with WritableTemporaryDirectory() as tmp:
            materialized = Path(tmp) / "materialized"
            materialized.mkdir(parents=True, exist_ok=True)
            (materialized / "metadata.json").write_text(
                json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            (materialized / "paper_list.json").write_text(
                json.dumps(papers, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            (materialized / "chart_data.json").write_text(
                json.dumps(chart_data, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            (materialized / "prisma_log.json").write_text(
                json.dumps({}, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            report = Path(tmp) / "report.html"
            render_html_webartifacts(
                materialized,
                report,
                user_query="红外线测量",
                language="zh",
            )

            opts = Options()
            opts.add_argument("--headless=new")
            opts.add_argument("--disable-gpu")
            opts.add_argument("--window-size=1600,1200")
            opts.add_argument("--allow-file-access-from-files")
            opts.add_argument("--disable-web-security")
            driver = webdriver.Edge(options=opts)
            try:
                driver.get(report.resolve().as_uri())
                wait = WebDriverWait(driver, 20)
                tab = wait.until(
                    EC.element_to_be_clickable(
                        (By.XPATH, "//*[self::button or self::a][contains(., 'Methods') or contains(., '方法')]")
                    )
                )
                tab.click()
                wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".rd-tab-methods")))
                first_section = driver.find_element(By.CSS_SELECTOR, ".rd-tab-methods > section")
                section_text = first_section.text
                section_html = first_section.get_attribute("innerHTML")
                self.assertIn("方法页可靠性声明", section_text)
                self.assertIn("如果希望得到更多可靠图表数据，请进行完整文献报告生成(full workflow)。", section_text)
                self.assertNotIn("这些数字是怎么算出来的", section_text)
                self.assertIn(
                    "<strong>如果希望得到更多可靠图表数据，请进行完整文献报告生成(full workflow)。</strong>",
                    section_html,
                )
            finally:
                driver.quit()

    @skipUnless(SELENIUM_AVAILABLE, "selenium not available")
    def test_methods_reliability_card_hidden_for_full_report_mode(self):
        metadata = {
            "search_id": "full-report-hide-card",
            "query": "full workflow query",
            "display_query": "full workflow query",
            "report_mode": "full",
            "mode": "vpnsci-compat-report",
            "papers_evaluated": 2,
            "papers_in_kg": 2,
        }
        chart_data = {
            "publication_year": {
                "bins": [{"year": 2025, "total": 2, "highly_relevant": 1}],
            },
            "relevance_score": {
                "bins": [{"rcs": i, "count": 0} for i in range(11)],
                "mean": 7.0,
                "ci_low": 6.5,
                "ci_high": 7.5,
                "n": 2,
            },
            "citation_network": {"nodes": [], "edges": [], "node_count": 0, "edge_count": 0},
            "theme_treemap": {"themes": [], "total_papers": 2},
        }
        papers = [
            {
                "paper_id": "10.1/a",
                "title": "Paper A",
                "authors_full": ["A"],
                "year": 2025,
                "venue": "Venue A",
                "abstract": "Abstract A",
                "rcs": 8,
                "citation_count": 0,
                "sources": ["openalex"],
            },
            {
                "paper_id": "10.1/b",
                "title": "Paper B",
                "authors_full": ["B"],
                "year": 2025,
                "venue": "Venue B",
                "abstract": "Abstract B",
                "rcs": 6,
                "citation_count": 0,
                "sources": ["openalex"],
            },
        ]

        with WritableTemporaryDirectory() as tmp:
            materialized = Path(tmp) / "materialized"
            materialized.mkdir(parents=True, exist_ok=True)
            (materialized / "metadata.json").write_text(
                json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            (materialized / "paper_list.json").write_text(
                json.dumps(papers, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            (materialized / "chart_data.json").write_text(
                json.dumps(chart_data, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            (materialized / "prisma_log.json").write_text(
                json.dumps({}, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            report = Path(tmp) / "report.html"
            render_html_webartifacts(
                materialized,
                report,
                user_query="full workflow query",
                language="en",
            )

            opts = Options()
            opts.add_argument("--headless=new")
            opts.add_argument("--disable-gpu")
            opts.add_argument("--window-size=1600,1200")
            opts.add_argument("--allow-file-access-from-files")
            opts.add_argument("--disable-web-security")
            driver = webdriver.Edge(options=opts)
            try:
                driver.get(report.resolve().as_uri())
                wait = WebDriverWait(driver, 20)
                tab = wait.until(
                    EC.element_to_be_clickable(
                        (By.XPATH, "//*[self::button or self::a][contains(., 'Methods') or contains(., '方法')]")
                    )
                )
                tab.click()
                wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".rd-tab-methods")))
                text = driver.find_element(By.CSS_SELECTOR, ".rd-tab-methods").text
                self.assertNotIn("Methods reliability statement", text)
                self.assertNotIn("方法页可靠性声明", text)
            finally:
                driver.quit()


if __name__ == "__main__":
    unittest.main()
