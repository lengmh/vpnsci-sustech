import asyncio
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock
from types import SimpleNamespace

from vpnsci_sustech import mcp_server
from vpnsci_sustech.sources import cnki
from vpnsci_sustech.sources.semantic_scholar import SemanticScholarRateLimitError
from vpnsci_sustech.sources.publisher_search import SearchHit
from vpnsci_sustech.sources.search_cache import SearchSession


class _Config:
    semantic_scholar_api_key = "S2-KEY"
    openalex_api_key = ""
    cache_dir = ""


class MCPServerTests(unittest.TestCase):
    def test_search_papers_passes_configured_api_key(self):
        fake_session = SearchSession(
            session_id="search-empty",
            query="test query",
            filters={},
            hits=[],
        )
        with mock.patch.object(mcp_server.Config, "load", return_value=_Config()), mock.patch.object(
            mcp_server.standard_search, "search", return_value=fake_session
        ) as search_mock:
            result = asyncio.run(mcp_server.search_papers("test query"))

        self.assertEqual(result, "No results found.")
        self.assertEqual(search_mock.call_args.kwargs["config"].semantic_scholar_api_key, "S2-KEY")

    def test_search_papers_reports_rate_limit(self):
        fake_session = SearchSession(
            session_id="search-rate-limited",
            query="test query",
            filters={},
            hits=[],
            errors=[
                mcp_server.standard_search.SearchError(
                    source="semantic_scholar",
                    code="rate_limited",
                    message="Semantic Scholar returned HTTP 429",
                )
            ],
        )
        with mock.patch.object(mcp_server.Config, "load", return_value=_Config()), mock.patch.object(
            mcp_server.standard_search, "search", return_value=fake_session
        ):
            result = asyncio.run(mcp_server.search_papers("test query"))

        self.assertIn("rate_limited", result)
        self.assertIn("semantic_scholar", result)

    def test_search_papers_default_uses_standard_search_session(self):
        fake_session = SearchSession(
            session_id="search-abc123",
            query="graph neural network",
            filters={"limit": 5},
            hits=[
                SearchHit(
                    title="Graph Paper",
                    doi="10.1000/graph",
                    authors=["Alice", "Bob"],
                    year=2024,
                    journal="Journal",
                    citation_count=10,
                    source="openalex",
                    sources=["openalex"],
                )
            ],
            source_summary={"openalex": 1},
            upgrade_suggested=True,
            decision_reasons=["result_count>=5", "doi_or_url_count>=3", "no_severe_errors"],
        )
        with mock.patch.object(mcp_server.standard_search, "search", return_value=fake_session) as search_mock:
            result = asyncio.run(mcp_server.search_papers("graph neural network", limit=5))

        self.assertIn("Found 1 results", result)
        self.assertIn("Search Session: `search-abc123`", result)
        self.assertIn("Source Summary", result)
        self.assertIn("Graph Paper", result)
        self.assertIn("专业调研", result)
        search_mock.assert_called_once()

    def test_search_papers_strong_trigger_starts_report_bridge_after_seed_search(self):
        fake_session = SearchSession(
            session_id="search-pro",
            query="请生成图神经网络文献综述",
            filters={"limit": 5},
            hits=[SearchHit(title="Graph Paper", doi="10.1000/graph")],
            source_summary={"openalex": 1},
        )
        fake_job = mcp_server.report_bridge.ReportJob(
            report_path="F:/AI playground/TempFiles/report.html",
            seed_session_id="search-pro",
            status="started",
            report_mode="seed_preview",
            pid=12345,
            log_path="F:/AI playground/TempFiles/report.log",
            expanded_sources=["openalex"],
            deduped_paper_count=1,
        )
        with mock.patch.object(mcp_server.standard_search, "search", return_value=fake_session) as search_mock, \
             mock.patch.object(mcp_server.report_bridge, "start_report_from_session", return_value=fake_job) as report_mock, \
             mock.patch.object(mcp_server.report_bridge, "generate_report_from_session") as sync_mock:
            result = asyncio.run(mcp_server.search_papers("请生成图神经网络文献综述", limit=5))

        self.assertIn("专业调研", result)
        self.assertIn("启动", result)
        self.assertIn("report.html", result)
        search_mock.assert_called_once()
        report_mock.assert_called_once()
        self.assertEqual(report_mock.call_args.kwargs["display_query"], "请生成图神经网络文献综述")
        self.assertEqual(report_mock.call_args.kwargs["language"], "zh")
        self.assertEqual(report_mock.call_args.kwargs["mode"], "full")
        self.assertTrue(report_mock.call_args.kwargs["open_report"])
        sync_mock.assert_not_called()

    def test_search_papers_strong_trigger_config_error_keeps_seed_results(self):
        fake_session = SearchSession(
            session_id="search-pro",
            query="请生成图神经网络文献综述",
            filters={"limit": 5},
            hits=[SearchHit(title="Graph Paper", doi="10.1000/graph")],
            source_summary={"openalex": 1},
        )
        with mock.patch.object(mcp_server.standard_search, "search", return_value=fake_session), \
             mock.patch.object(
                 mcp_server.report_bridge,
                 "start_report_from_session",
                 side_effect=mcp_server.report_bridge.ReportBridgeConfigError("paper_search_pro_command is not configured"),
             ):
            result = asyncio.run(mcp_server.search_papers("请生成图神经网络文献综述", limit=5))

        self.assertIn("报告桥接尚未配置", result)
        self.assertIn("search-pro", result)
        self.assertIn("Graph Paper", result)

    def test_search_papers_explicit_backend_still_uses_publisher_search(self):
        fake_hits = [
            SearchHit(
                title="IEEE Paper",
                doi="10.1109/example",
                url="https://ieeexplore.ieee.org/document/1/",
                source="ieee",
            )
        ]
        with mock.patch.object(mcp_server.publisher_search, "search", return_value=fake_hits) as publisher_mock, \
             mock.patch.object(mcp_server.standard_search, "search") as standard_mock:
            result = asyncio.run(mcp_server.search_papers("ieee paper", limit=3, backend="ieee"))

        self.assertIn("IEEE Paper", result)
        publisher_mock.assert_called_once()
        standard_mock.assert_not_called()

    def test_search_papers_can_route_to_sciencedirect_backend(self):
        fake_hits = [
            SearchHit(
                title="SD Title",
                doi="10.1016/example",
                url="https://www.sciencedirect.com/science/article/pii/S123",
                pdf_url="https://www.sciencedirect.com/science/article/pii/S123/pdfft",
                journal="Journal",
                year=2024,
                authors=["Alice", "Bob"],
            )
        ]
        with mock.patch.object(mcp_server.publisher_search, "search", return_value=fake_hits) as search_mock:
            result = asyncio.run(mcp_server.search_papers("filtering antenna", limit=5, backend="sciencedirect"))

        self.assertIn("SD Title", result)
        self.assertIn("10.1016/example", result)
        self.assertEqual(search_mock.call_args.kwargs["backend"], "sciencedirect")
        self.assertEqual(search_mock.call_args.kwargs["limit"], 5)

    def test_search_papers_can_route_to_ieee_backend(self):
        fake_hits = [
            SearchHit(
                title="Network Anomaly Detection Using a Graph Neural Network",
                doi="10.1109/ICNC57223.2023.10074111",
                url="https://ieeexplore.ieee.org/document/10074111/",
                pdf_url="https://ieeexplore.ieee.org/stamp/stamp.jsp?tp=&arnumber=10074111",
                journal="2023 International Conference on Computing, Networking and Communications (ICNC)",
                year=2023,
                authors=["Patrice Kisanga", "Isaac Woungang"],
                citation_count=35,
                abstract="Contrary to the many traditional network security approaches.",
            )
        ]
        with mock.patch.object(mcp_server.publisher_search, "search", return_value=fake_hits) as search_mock:
            result = asyncio.run(mcp_server.search_papers("graph neural network", limit=5, backend="ieee"))

        self.assertIn("Network Anomaly Detection", result)
        self.assertIn("10.1109/ICNC57223.2023.10074111", result)
        self.assertIn("PDF URL", result)
        self.assertEqual(search_mock.call_args.kwargs["backend"], "ieee")

    def test_search_papers_reports_blocked_publisher_backend(self):
        with mock.patch.object(
            mcp_server.publisher_search,
            "search",
            side_effect=mcp_server.publisher_search.PublisherSearchBlockedError("wiley blocked"),
        ):
            result = asyncio.run(mcp_server.search_papers("lasso", backend="wiley"))

        self.assertIn("publisher-native", result)
        self.assertIn("blocked", result.lower())
        self.assertNotIn("No results found", result)

    def test_search_papers_cnki_backend_uses_explicit_cnki_session_when_available(self):
        fake_session = SearchSession(
            session_id="search-cnki",
            query="钙钛矿",
            filters={"backend": "cnki", "limit": 3},
            hits=[
                SearchHit(
                    title="知网论文",
                    authors=["张三"],
                    year=2024,
                    journal="中文期刊",
                    cnki_id="ABC123",
                    source_url="https://kns.cnki.net/kcms2/article/abstract?filename=ABC123",
                    backend="cnki",
                    source="cnki",
                    sources=["cnki"],
                )
            ],
            source_summary={"cnki": 1},
        )

        with mock.patch.object(mcp_server.cnki, "search_cnki", return_value=fake_session) as cnki_mock:
            result = asyncio.run(mcp_server.search_papers("钙钛矿", limit=3, backend="cnki"))

        self.assertIn("Search Session: `search-cnki`", result)
        self.assertIn("知网论文", result)
        self.assertIn("ABC123", result)
        cnki_mock.assert_called_once()

    def test_search_papers_cnki_backend_reports_manual_login_required(self):
        fake_session = SearchSession(
            session_id="search-cnki-blocked",
            query="钙钛矿",
            filters={"backend": "cnki"},
            hits=[],
            errors=[
                mcp_server.standard_search.SearchError(
                    source="cnki",
                    code="manual_login_required",
                    message="CNKI requires manual browser login.",
                )
            ],
            source_summary={"cnki": 0},
        )

        with mock.patch.object(mcp_server.cnki, "search_cnki", return_value=fake_session):
            result = asyncio.run(mcp_server.search_papers("钙钛矿", backend="cnki"))

        self.assertIn("manual_login_required", result)
        self.assertIn("cnki", result.lower())

    def test_generate_search_report_starts_background_job(self):
        fake = mcp_server.report_bridge.ReportJob(
            report_path="F:/AI playground/TempFiles/report.html",
            file_url="file:///F:/AI%20playground/TempFiles/report.html",
            seed_session_id="search-test",
            status="started",
            report_mode="seed_preview",
            pid=12345,
            log_path="F:/AI playground/TempFiles/report.log",
            expanded_sources=["openalex"],
            deduped_paper_count=12,
        )
        with mock.patch.object(mcp_server.report_bridge, "start_report_from_session", return_value=fake) as report_mock, \
             mock.patch.object(mcp_server.report_bridge, "generate_report_from_session") as sync_mock:
            result = asyncio.run(
                mcp_server.generate_search_report(
                    "search-test",
                    mode="seed_preview",
                    display_query="红外线测量",
                    language="zh",
                    open_report=True,
                )
            )

        self.assertIn("已启动", result)
        self.assertIn("Report Mode: `seed_preview`", result)
        self.assertIn("not the full paper-search-pro workflow", result)
        self.assertIn("[打开 HTML 报告]", result)
        self.assertIn("file:///F:/AI%20playground/TempFiles/report.html", result)
        self.assertIn("report.html", result)
        self.assertIn("report.log", result)
        self.assertIn("search-test", result)
        self.assertIn("12", result)
        self.assertEqual(report_mock.call_args.kwargs["display_query"], "红外线测量")
        self.assertEqual(report_mock.call_args.kwargs["language"], "zh")
        self.assertEqual(report_mock.call_args.kwargs["mode"], "seed_preview")
        self.assertTrue(report_mock.call_args.kwargs["open_report"])
        sync_mock.assert_not_called()

    def test_generate_search_report_full_handoff_does_not_claim_html_started(self):
        fake = mcp_server.report_bridge.ReportJob(
            report_path="",
            file_url="",
            seed_session_id="search-test",
            status="handoff_required",
            report_mode="full",
            handoff_path="F:/AI playground/TempFiles/handoff/instructions.md",
            expanded_sources=["openalex"],
            deduped_paper_count=12,
        )
        with mock.patch.object(mcp_server.report_bridge, "start_report_from_session", return_value=fake):
            result = asyncio.run(
                mcp_server.generate_search_report(
                    "search-test",
                    mode="full",
                    display_query="非接触体温测量",
                )
            )

        self.assertIn("Report Mode: `full`", result)
        self.assertIn("handoff_required", result)
        self.assertIn("Handoff", result)
        self.assertIn("instructions.md", result)
        self.assertIn("Codex", result)
        self.assertIn("multi_agent", result)
        self.assertIn("SubAgent", result)
        self.assertIn("不会静默退回 seed_preview", result)
        self.assertNotIn("已启动", result)

    def test_generate_search_report_theme_postprocess_required_returns_host_agent_message(self):
        fake = mcp_server.report_bridge.ReportJob(
            report_path="",
            file_url="",
            seed_session_id="search-theme",
            status="theme_postprocess_required",
            report_mode="seed_preview",
            materialized_dir="F:/AI playground/TempFiles/materialized",
            theme_postprocess_request_path="F:/AI playground/TempFiles/materialized/theme_postprocess_request.json",
            theme_postprocess_result_path="F:/AI playground/TempFiles/materialized/theme_postprocess_result.json",
            user_query="联邦学习 医院",
            language="zh",
            deduped_paper_count=12,
        )
        with mock.patch.object(mcp_server.report_bridge, "start_report_from_session", return_value=fake):
            result = asyncio.run(
                mcp_server.generate_search_report(
                    "search-theme",
                    mode="seed_preview",
                    display_query="联邦学习 医院",
                    language="zh",
                )
            )

        self.assertIn("theme_postprocess_required", result)
        self.assertIn("host Agent", result)
        self.assertIn("theme_postprocess_request.json", result)
        self.assertIn("theme_postprocess_result.json", result)
        self.assertNotIn("已启动", result)

    def test_generate_search_report_rcs_classification_required_returns_host_agent_message(self):
        fake = mcp_server.report_bridge.ReportJob(
            report_path="",
            file_url="",
            seed_session_id="search-rcs",
            status="rcs_classification_required",
            report_mode="seed_classified",
            materialized_dir="F:/AI playground/TempFiles/materialized",
            rcs_classification_request_path="F:/AI playground/TempFiles/materialized/rcs_classification_request.json",
            rcs_classification_result_path="F:/AI playground/TempFiles/materialized/rcs_classification_result.json",
            user_query="graph neural network",
            language="en",
            deduped_paper_count=12,
        )
        with mock.patch.object(mcp_server.report_bridge, "start_report_from_session", return_value=fake):
            result = asyncio.run(
                mcp_server.generate_search_report(
                    "search-rcs",
                    mode="seed_classified",
                    display_query="graph neural network",
                    language="en",
                )
            )

        self.assertIn("rcs_classification_required", result)
        self.assertIn("seed_classified", result)
        self.assertIn("host Agent", result)
        self.assertIn("rcs_classification_request.json", result)
        self.assertIn("rcs_classification_result.json", result)
        self.assertNotIn("已启动", result)

    def test_get_theme_postprocess_request_returns_payload_json(self):
        fake = mcp_server.report_bridge.ReportJob(
            report_path="",
            file_url="",
            seed_session_id="search-theme",
            status="theme_postprocess_required",
            report_mode="seed_preview",
            materialized_dir="F:/AI playground/TempFiles/materialized",
            theme_postprocess_request_path="F:/AI playground/TempFiles/materialized/theme_postprocess_request.json",
            theme_postprocess_result_path="F:/AI playground/TempFiles/materialized/theme_postprocess_result.json",
            user_query="联邦学习 医院",
            language="zh",
            deduped_paper_count=12,
        )
        request_payload = {
            "report_mode": "seed_preview",
            "themes": [{"index": 0, "name": "Federated Learning", "value": 2, "paper_ids": ["10.1/a"]}],
        }
        with tempfile.TemporaryDirectory() as tmp:
            materialized = Path(tmp) / "materialized"
            materialized.mkdir(parents=True, exist_ok=True)
            request_path = materialized / "theme_postprocess_request.json"
            request_path.write_text(json.dumps(request_payload, ensure_ascii=False), encoding="utf-8")
            fake.theme_postprocess_request_path = str(request_path)
            fake.theme_postprocess_result_path = str(materialized / "theme_postprocess_result.json")
            fake.materialized_dir = str(materialized)
            with mock.patch.object(mcp_server.report_bridge, "start_report_from_session", return_value=fake):
                result = asyncio.run(
                    mcp_server.get_theme_postprocess_request(
                        "search-theme",
                        mode="seed_preview",
                        display_query="联邦学习 医院",
                        language="zh",
                    )
                )

        payload = json.loads(result)
        self.assertEqual(payload["search_session_id"], "search-theme")
        self.assertEqual(payload["status"], "theme_postprocess_required")
        self.assertEqual(payload["payload"]["report_mode"], "seed_preview")
        self.assertEqual(payload["payload"]["themes"][0]["name"], "Federated Learning")

    def test_get_rcs_classification_request_returns_payload_json(self):
        fake = mcp_server.report_bridge.ReportJob(
            report_path="",
            file_url="",
            seed_session_id="search-rcs",
            status="rcs_classification_required",
            report_mode="seed_classified",
            materialized_dir="F:/AI playground/TempFiles/materialized",
            rcs_classification_request_path="F:/AI playground/TempFiles/materialized/rcs_classification_request.json",
            rcs_classification_result_path="F:/AI playground/TempFiles/materialized/rcs_classification_result.json",
            user_query="graph neural network",
            language="en",
            deduped_paper_count=12,
        )
        request_payload = {
            "report_mode": "seed_classified",
            "rcs_scope": "seed_set",
            "papers": [{"paper_id": "doi:10.1/a", "title": "Paper A"}],
        }
        with tempfile.TemporaryDirectory() as tmp:
            materialized = Path(tmp) / "materialized"
            materialized.mkdir(parents=True, exist_ok=True)
            request_path = materialized / "rcs_classification_request.json"
            request_path.write_text(json.dumps(request_payload, ensure_ascii=False), encoding="utf-8")
            fake.rcs_classification_request_path = str(request_path)
            fake.rcs_classification_result_path = str(materialized / "rcs_classification_result.json")
            fake.materialized_dir = str(materialized)
            with mock.patch.object(mcp_server.report_bridge, "start_report_from_session", return_value=fake):
                result = asyncio.run(
                    mcp_server.get_rcs_classification_request(
                        "search-rcs",
                        display_query="graph neural network",
                        language="en",
                    )
                )

        payload = json.loads(result)
        self.assertEqual(payload["search_session_id"], "search-rcs")
        self.assertEqual(payload["status"], "rcs_classification_required")
        self.assertEqual(payload["payload"]["report_mode"], "seed_classified")
        self.assertEqual(payload["payload"]["papers"][0]["paper_id"], "doi:10.1/a")

    def test_apply_theme_postprocess_result_returns_rendered_report_message(self):
        fake = mcp_server.report_bridge.ReportResult(
            report_path="F:/AI playground/TempFiles/report.html",
            file_url="file:///F:/AI%20playground/TempFiles/report.html",
            seed_session_id="search-theme",
            report_mode="seed_preview",
            status="completed",
            materialized_dir="F:/AI playground/TempFiles/materialized",
            theme_postprocess_request_path="F:/AI playground/TempFiles/materialized/theme_postprocess_request.json",
            theme_postprocess_result_path="F:/AI playground/TempFiles/materialized/theme_postprocess_result.json",
        )
        with mock.patch.object(mcp_server.report_bridge, "apply_theme_postprocess_and_render", return_value=fake):
            result = asyncio.run(
                mcp_server.apply_theme_postprocess_result(
                    "search-theme",
                    json.dumps({"groups": [{"label": "Federated Learning", "theme_indices": [0]}]}, ensure_ascii=False),
                    mode="seed_preview",
                    display_query="联邦学习 医院",
                    language="zh",
                    open_report=False,
                )
            )

        self.assertIn("已写回并完成渲染", result)
        self.assertIn("report.html", result)
        self.assertIn("theme_postprocess_result.json", result)

    def test_apply_rcs_classification_result_returns_rendered_report_message(self):
        fake = mcp_server.report_bridge.ReportResult(
            report_path="F:/AI playground/TempFiles/report.html",
            file_url="file:///F:/AI%20playground/TempFiles/report.html",
            seed_session_id="search-rcs",
            report_mode="seed_classified",
            status="completed",
            materialized_dir="F:/AI playground/TempFiles/materialized",
            rcs_classification_request_path="F:/AI playground/TempFiles/materialized/rcs_classification_request.json",
            rcs_classification_result_path="F:/AI playground/TempFiles/materialized/rcs_classification_result.json",
        )
        with mock.patch.object(mcp_server.report_bridge, "apply_rcs_classification_and_render", return_value=fake):
            result = asyncio.run(
                mcp_server.apply_rcs_classification_result(
                    "search-rcs",
                    json.dumps(
                        [{"paper_id": "doi:10.1/a", "rcs": 8, "reasoning": "Relevant.", "flag": None}],
                        ensure_ascii=False,
                    ),
                    rcs_execution_mode="main_agent_serial",
                    display_query="graph neural network",
                    language="en",
                    open_report=False,
                )
            )

        self.assertIn("RCS 分类结果已写回并完成渲染", result)
        self.assertIn("seed_classified", result)
        self.assertIn("report.html", result)
        self.assertIn("rcs_classification_result.json", result)

    def test_generate_search_report_full_theme_postprocess_required_returns_host_agent_message(self):
        fake = mcp_server.report_bridge.ReportJob(
            report_path="",
            file_url="",
            seed_session_id="search-full-theme",
            status="theme_postprocess_required",
            report_mode="full",
            materialized_dir="F:/AI playground/TempFiles/materialized",
            theme_postprocess_request_path="F:/AI playground/TempFiles/materialized/theme_postprocess_request.json",
            theme_postprocess_result_path="F:/AI playground/TempFiles/materialized/theme_postprocess_result.json",
            user_query="核物理治疗方法",
            language="zh",
            deduped_paper_count=50,
        )
        with mock.patch.object(mcp_server.report_bridge, "start_report_from_session", return_value=fake):
            result = asyncio.run(
                mcp_server.generate_search_report(
                    "search-full-theme",
                    mode="full",
                    display_query="核物理治疗方法",
                    language="zh",
                )
            )

        self.assertIn("theme_postprocess_required", result)
        self.assertIn("Report Mode: `full`", result)
        self.assertIn("host Agent", result)
        self.assertNotIn("已启动", result)

    def test_get_theme_postprocess_request_supports_full_mode(self):
        fake = mcp_server.report_bridge.ReportJob(
            report_path="",
            file_url="",
            seed_session_id="search-full-theme",
            status="theme_postprocess_required",
            report_mode="full",
            materialized_dir="F:/AI playground/TempFiles/materialized",
            theme_postprocess_request_path="F:/AI playground/TempFiles/materialized/theme_postprocess_request.json",
            theme_postprocess_result_path="F:/AI playground/TempFiles/materialized/theme_postprocess_result.json",
            user_query="核物理治疗方法",
            language="zh",
            deduped_paper_count=50,
        )
        request_payload = {
            "report_mode": "full",
            "themes": [{"index": 0, "name": "Targeted Radionuclide Therapy", "value": 10, "paper_ids": ["10.1/a"]}],
        }
        with tempfile.TemporaryDirectory() as tmp:
            materialized = Path(tmp) / "materialized"
            materialized.mkdir(parents=True, exist_ok=True)
            request_path = materialized / "theme_postprocess_request.json"
            request_path.write_text(json.dumps(request_payload, ensure_ascii=False), encoding="utf-8")
            fake.theme_postprocess_request_path = str(request_path)
            fake.theme_postprocess_result_path = str(materialized / "theme_postprocess_result.json")
            fake.materialized_dir = str(materialized)
            with mock.patch.object(mcp_server.report_bridge, "start_report_from_session", return_value=fake):
                result = asyncio.run(
                    mcp_server.get_theme_postprocess_request(
                        "search-full-theme",
                        mode="full",
                        display_query="核物理治疗方法",
                        language="zh",
                    )
                )

        payload = json.loads(result)
        self.assertEqual(payload["status"], "theme_postprocess_required")
        self.assertEqual(payload["report_mode"], "full")
        self.assertEqual(payload["payload"]["report_mode"], "full")

    def test_generate_search_report_accepts_query_title_alias_and_infers_chinese(self):
        fake = mcp_server.report_bridge.ReportJob(
            report_path="F:/AI playground/TempFiles/report.html",
            file_url="file:///F:/AI%20playground/TempFiles/report.html",
            seed_session_id="search-test",
            status="started",
            report_mode="seed_preview",
            pid=12345,
            log_path="F:/AI playground/TempFiles/report.log",
            expanded_sources=["openalex"],
            deduped_paper_count=12,
        )
        with mock.patch.object(mcp_server.report_bridge, "start_report_from_session", return_value=fake) as report_mock:
            asyncio.run(
                mcp_server.generate_search_report(
                    "search-test",
                    query_title="红外线测量",
                )
            )

        self.assertEqual(report_mock.call_args.kwargs["display_query"], "红外线测量")
        self.assertEqual(report_mock.call_args.kwargs["language"], "zh")

    def test_search_cnki_from_html_persists_html_import_origin(self):
        html = """
        <table class="result-table-list">
          <tr>
            <td class="name"><a href="/kcms2/article/abstract?filename=ABC123&dbcode=CJFD">题名一</a></td>
            <td class="author">张三</td>
            <td class="source">期刊一</td>
            <td class="date">2024</td>
          </tr>
        </table>
        """
        with tempfile.TemporaryDirectory() as tmp:
            config = SimpleNamespace(cache_dir=tmp)
            with mock.patch.object(mcp_server.Config, "load", return_value=config):
                result = asyncio.run(
                    mcp_server.search_cnki_from_html(
                        query="钙钛矿",
                        html=html,
                        limit=1,
                    )
                )

            self.assertIn("Search Session:", result)
            session_id = result.split("Search Session: `", 1)[1].split("`", 1)[0]
            session_path = Path(tmp) / "search" / "sessions" / f"{session_id}.json"
            data = json.loads(session_path.read_text(encoding="utf-8"))
            self.assertEqual(data["origin"]["kind"], "html_import")
            self.assertEqual(data["origin"]["engine"], "cnki")

    def test_generate_search_report_config_error_is_clear(self):
        with mock.patch.object(
            mcp_server.report_bridge,
            "start_report_from_session",
            side_effect=mcp_server.report_bridge.ReportBridgeConfigError("paper_search_pro_command is not configured"),
        ):
            result = asyncio.run(mcp_server.generate_search_report("search-test"))

        self.assertIn("报告桥接尚未配置", result)
        self.assertIn("paper_search_pro_command", result)

    def test_fetch_paper_allows_sciencedirect_when_fetcher_can_handle_it(self):
        fake_paper = SimpleNamespace(
            full_text="body",
            abstract="abs",
            to_json=lambda: "{}",
            to_text=lambda: "body",
            to_markdown=lambda include_pdf_path=True: "# ok",
            title="SD",
            url="https://www.sciencedirect.com/science/article/pii/S0169433221006001",
        )
        with mock.patch.object(mcp_server, "_get_fetcher", return_value=SimpleNamespace(fetch=lambda identifier, **kwargs: fake_paper)):
            result = asyncio.run(mcp_server.fetch_paper("https://www.sciencedirect.com/science/article/pii/S0169433221006001"))

        self.assertEqual(result, "# ok")

    def test_fetch_paper_passes_filename_policy_to_fetcher(self):
        fake_paper = SimpleNamespace(
            full_text="body",
            abstract="abs",
            to_json=lambda: "{}",
            to_text=lambda: "body",
            to_markdown=lambda include_pdf_path=True: "# renamed",
            title="Renamed",
            url="https://example.test/paper",
        )
        fake_fetcher = SimpleNamespace(fetch=mock.Mock(return_value=fake_paper))
        with mock.patch.object(mcp_server, "_get_fetcher", return_value=fake_fetcher):
            result = asyncio.run(
                mcp_server.fetch_paper(
                    "10.1234/example",
                    filename_policy="title_author",
                    filename_template="{title} - {first_author}",
                )
            )

        self.assertEqual(result, "# renamed")
        fake_fetcher.fetch.assert_called_once_with(
            "10.1234/example",
            filename_policy="title_author",
            filename_template="{title} - {first_author}",
        )

    def test_fetch_search_hit_continues_cnki_hit_via_unified_entry(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = SimpleNamespace(cache_dir=tmp)
            session = cnki.search_cnki_from_html(
                "钙钛矿",
                """
                <table class="result-table-list">
                  <tr>
                    <td class="name"><a href="/kcms2/article/abstract?filename=ABC123&dbcode=CJFD">题名一</a></td>
                    <td class="author">张三</td>
                    <td class="source">期刊一</td>
                    <td class="date">2024</td>
                  </tr>
                </table>
                """,
                limit=1,
                cache_dir=tmp,
            )
            fake_paper = SimpleNamespace(
                title="题名一",
                source="cnki",
                to_json=lambda: "{}",
                to_text=lambda: "题名一",
                to_markdown=lambda include_pdf_path=True: "# 题名一",
                full_text="body",
                abstract="",
            )
            fake_fetcher = SimpleNamespace(fetch_from_search_hit=mock.Mock(return_value=fake_paper))
            with mock.patch.object(mcp_server.Config, "load", return_value=config), \
                 mock.patch.object(mcp_server, "_get_fetcher", return_value=fake_fetcher):
                result = asyncio.run(
                    mcp_server.fetch_search_hit(
                        session_id=session.session_id,
                        hit_key="cnki:ABC123",
                    )
                )

            self.assertEqual(result, "# 题名一")
            self.assertEqual(fake_fetcher.fetch_from_search_hit.call_args.args[0].hit_key, "cnki:ABC123")

    def test_fetch_paper_ask_rename_accepts_elicited_policy(self):
        fake_paper = SimpleNamespace(
            full_text="body",
            abstract="",
            to_json=lambda: "{}",
            to_text=lambda: "body",
            to_markdown=lambda include_pdf_path=True: "# ok",
            title="Paper",
            url="",
        )
        fake_fetcher = SimpleNamespace(fetch=mock.Mock(return_value=fake_paper))

        class _Ctx:
            async def elicit(self, message, schema):
                self.message = message
                self.schema = schema
                return SimpleNamespace(action="accept", data=SimpleNamespace(policy="title_year_author"))

        ctx = _Ctx()
        with mock.patch.object(mcp_server, "_get_fetcher", return_value=fake_fetcher):
            result = asyncio.run(mcp_server.fetch_paper("10.1234/example", ask_rename=True, ctx=ctx))

        self.assertEqual(result, "# ok")
        self.assertIn("命名策略", ctx.message)
        self.assertEqual(
            fake_fetcher.fetch.call_args.kwargs["filename_policy"],
            "title_year_author",
        )

    def test_fetch_paper_ask_rename_decline_falls_back_to_config(self):
        fake_paper = SimpleNamespace(
            full_text="body",
            abstract="",
            to_json=lambda: "{}",
            to_text=lambda: "body",
            to_markdown=lambda include_pdf_path=True: "# ok",
            title="Paper",
            url="",
        )
        fake_fetcher = SimpleNamespace(fetch=mock.Mock(return_value=fake_paper))

        class _Ctx:
            async def elicit(self, message, schema):
                return SimpleNamespace(action="decline", data=None)

        with mock.patch.object(mcp_server, "_get_fetcher", return_value=fake_fetcher), \
             mock.patch.object(mcp_server.Config, "load", return_value=SimpleNamespace(paper_filename_policy="identifier")):
            asyncio.run(mcp_server.fetch_paper("10.1234/example", ask_rename=True, ctx=_Ctx()))

        self.assertEqual(fake_fetcher.fetch.call_args.kwargs["filename_policy"], "")

    def test_fetch_paper_ask_rename_cancel_falls_back_to_config(self):
        fake_paper = SimpleNamespace(
            full_text="body",
            abstract="",
            to_json=lambda: "{}",
            to_text=lambda: "body",
            to_markdown=lambda include_pdf_path=True: "# ok",
            title="Paper",
            url="",
        )
        fake_fetcher = SimpleNamespace(fetch=mock.Mock(return_value=fake_paper))

        class _Ctx:
            async def elicit(self, message, schema):
                return SimpleNamespace(action="cancel", data=None)

        with mock.patch.object(mcp_server, "_get_fetcher", return_value=fake_fetcher):
            asyncio.run(mcp_server.fetch_paper("10.1234/example", ask_rename=True, ctx=_Ctx()))

        self.assertEqual(fake_fetcher.fetch.call_args.kwargs["filename_policy"], "")

    def test_fetch_paper_config_ask_rename_uses_elicitation_without_explicit_flag(self):
        fake_paper = SimpleNamespace(
            full_text="body",
            abstract="",
            to_json=lambda: "{}",
            to_text=lambda: "body",
            to_markdown=lambda include_pdf_path=True: "# ok",
            title="Paper",
            url="",
        )
        fake_fetcher = SimpleNamespace(fetch=mock.Mock(return_value=fake_paper))

        class _Ctx:
            async def elicit(self, message, schema):
                self.message = message
                return SimpleNamespace(action="accept", data=SimpleNamespace(policy="title_author"))

        ctx = _Ctx()
        config = SimpleNamespace(paper_filename_policy="identifier", paper_filename_ask=True)
        with mock.patch.object(mcp_server, "_get_fetcher", return_value=fake_fetcher), \
             mock.patch.object(mcp_server.Config, "load", return_value=config):
            asyncio.run(mcp_server.fetch_paper("10.1234/example", ctx=ctx))

        self.assertIn("paper_filename_ask=false", ctx.message)
        self.assertEqual(fake_fetcher.fetch.call_args.kwargs["filename_policy"], "title_author")

    def test_fetch_paper_config_ask_false_does_not_elicit(self):
        fake_paper = SimpleNamespace(
            full_text="body",
            abstract="",
            to_json=lambda: "{}",
            to_text=lambda: "body",
            to_markdown=lambda include_pdf_path=True: "# ok",
            title="Paper",
            url="",
        )
        fake_fetcher = SimpleNamespace(fetch=mock.Mock(return_value=fake_paper))

        class _Ctx:
            async def elicit(self, message, schema):
                raise AssertionError("should not elicit")

        config = SimpleNamespace(paper_filename_policy="identifier", paper_filename_ask=False)
        with mock.patch.object(mcp_server, "_get_fetcher", return_value=fake_fetcher), \
             mock.patch.object(mcp_server.Config, "load", return_value=config):
            asyncio.run(mcp_server.fetch_paper("10.1234/example", ctx=_Ctx()))

        self.assertEqual(fake_fetcher.fetch.call_args.kwargs["filename_policy"], "")

    def test_download_cnki_artifact_materializes_local_file_without_network(self):
        with tempfile.TemporaryDirectory(dir=Path("F:/AI playground/TempFiles")) as tmp:
            source = Path(tmp) / "source.caj"
            source.write_bytes(b"caj-content")
            config = SimpleNamespace(
                output_dir=str(Path(tmp) / "out"),
                cache_dir=tmp,
                paper_filename_policy="title_author",
                paper_filename_template="{title} - {first_author}",
                paper_filename_max_length=180,
                paper_filename_collision="hash",
            )

            with mock.patch.object(mcp_server.Config, "load", return_value=config):
                result = asyncio.run(
                    mcp_server.download_cnki_artifact(
                        local_file=str(source),
                        title="钙钛矿太阳能电池稳定性研究",
                        first_author="张三",
                        cnki_id="ABC123",
                        source_url="https://kns.cnki.net/download?filename=ABC123",
                    )
                )

            self.assertIn("CNKI artifact saved", result)
            self.assertIn("text_extracted=false", result)
            self.assertIn("钙钛矿太阳能电池稳定性研究 - 张三.caj", result)

    def test_download_cnki_artifact_accepts_filename_policy_override(self):
        with tempfile.TemporaryDirectory(dir=Path("F:/AI playground/TempFiles")) as tmp:
            source = Path(tmp) / "source.caj"
            source.write_bytes(b"caj-content")
            config = SimpleNamespace(
                output_dir=str(Path(tmp) / "out"),
                cache_dir=tmp,
                paper_filename_policy="identifier",
                paper_filename_template="{title} - {first_author}",
                paper_filename_max_length=180,
                paper_filename_collision="hash",
                cnki_convert_caj_to_pdf=False,
                cnki_caj_converter_command="",
            )

            with mock.patch.object(mcp_server.Config, "load", return_value=config):
                result = asyncio.run(
                    mcp_server.download_cnki_artifact(
                        local_file=str(source),
                        title="CNKI Source",
                        first_author="Li",
                        cnki_id="XYZ",
                        filename_policy="title_author",
                    )
                )

            self.assertIn("CNKI Source - Li.caj", result)
            self.assertNotIn("XYZ.caj", result)

    def test_download_cnki_artifact_refuses_live_url_without_local_file(self):
        result = asyncio.run(
            mcp_server.download_cnki_artifact(
                detail_url="https://kns.cnki.net/kcms2/article/abstract?filename=ABC123",
                title="题名",
            )
        )

        self.assertIn("requires", result)
        self.assertIn("local_file", result)

    def test_download_cnki_artifact_live_requires_confirmation(self):
        result = asyncio.run(
            mcp_server.download_cnki_artifact(
                detail_url="https://kns.cnki.net/kcms2/article/abstract?filename=ABC123",
                title="题名",
                live=True,
            )
        )

        self.assertIn("confirmation_required", result)

    def test_download_cnki_artifact_live_warns_that_manual_captcha_may_be_required(self):
        config = SimpleNamespace(
            output_dir="out",
            cache_dir="cache",
            paper_filename_policy="identifier",
            paper_filename_template="",
            paper_filename_max_length=180,
            paper_filename_collision="hash",
        )
        fake_artifact = SimpleNamespace(
            path="out/paper.pdf",
            format="pdf",
            kind="full_text_pdf",
            text_extracted=True,
            note="",
        )
        with mock.patch.object(mcp_server.Config, "load", return_value=config), \
             mock.patch("vpnsci_sustech.mcp_server.cnki.CNKIClient.download_cnki_artifact", return_value=fake_artifact):
            result = asyncio.run(
                mcp_server.download_cnki_artifact(
                    detail_url="https://kns.cnki.net/kcms2/article/abstract?filename=ABC123",
                    live=True,
                    confirm_live_access=True,
                )
            )

        self.assertIn("manual captcha", result.lower())
        self.assertIn("visible browser", result.lower())

    def test_download_cnki_batch_artifacts_passes_throttle_and_resume_options(self):
        config = SimpleNamespace(
            output_dir="out",
            cache_dir="cache",
            paper_filename_policy="identifier",
            paper_filename_template="",
            paper_filename_max_length=180,
            paper_filename_collision="hash",
        )
        fake_result = mcp_server.cnki.CNKIBatchResult(
            status="completed",
            state_path=Path("cache/cnki/batch/state.json"),
            sidecar_path=Path("cache/download-workflows/download-abc.json"),
            entries=[],
            succeeded=2,
            failed=0,
            pending=0,
            stopped_reason="",
        )
        with mock.patch.object(mcp_server.Config, "load", return_value=config), \
             mock.patch("vpnsci_sustech.mcp_server.cnki.CNKIClient.download_cnki_batch", return_value=fake_result) as batch_mock:
            result = asyncio.run(
                mcp_server.download_cnki_batch_artifacts(
                    items=[
                        {
                            "detail_url": "https://kns.cnki.net/kcms2/article/abstract?filename=ABC1",
                            "title": "A",
                            "first_author": "Li",
                            "cnki_id": "ABC1",
                        },
                        {
                            "detail_url": "https://kns.cnki.net/kcms2/article/abstract?filename=ABC2",
                            "title": "B",
                            "first_author": "Wang",
                            "cnki_id": "ABC2",
                        },
                    ],
                    live=True,
                    confirm_live_access=True,
                    min_interval_seconds=1,
                    cooldown_every=2,
                    cooldown_seconds=5,
                    max_consecutive_failures=1,
                    state_file="cache/cnki/batch/state.json",
                    resume=True,
                )
            )

        self.assertIn("CNKI batch download", result)
        self.assertIn("completed", result)
        self.assertIn("download-abc.json", result)
        called_items = batch_mock.call_args.args[0]
        self.assertEqual(len(called_items), 2)
        self.assertEqual(called_items[0].cnki_id, "ABC1")
        self.assertEqual(batch_mock.call_args.kwargs["min_interval_seconds"], 1.0)
        self.assertEqual(batch_mock.call_args.kwargs["cooldown_every"], 2)
        self.assertTrue(batch_mock.call_args.kwargs["resume"])

    def test_generate_recovery_report_restores_sidecar_session(self):
        with tempfile.TemporaryDirectory() as tmp:
            sidecar_path = Path(tmp) / "download-workflows" / "download-abc.json"
            sidecar_path.parent.mkdir(parents=True, exist_ok=True)
            sidecar_path.write_text(
                json.dumps(
                    {
                        "workflow_id": "download-abc",
                        "root_session_id": "search-root",
                        "source_session_id": "search-root",
                        "display_query": "CNKI 下载结果集合",
                        "recovered_label": "CNKI 下载结果集合",
                        "items": [
                            {
                                "hit_key": "cnki:ABC123",
                                "title": "知网论文",
                                "source": "cnki",
                                "source_url": "https://kns.cnki.net/kcms2/article/abstract?filename=ABC123",
                                "local_file": "F:/AI playground/TempFiles/知网论文.caj",
                                "download_format": "caj",
                                "result_type": "downloaded_caj",
                            }
                        ],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            fake = mcp_server.report_bridge.ReportJob(
                report_path="F:/AI playground/TempFiles/report.html",
                file_url="file:///F:/AI%20playground/TempFiles/report.html",
                seed_session_id="search-restored",
                status="started",
                report_mode="seed_preview",
                pid=12345,
                log_path="F:/AI playground/TempFiles/report.log",
                expanded_sources=["cnki"],
                deduped_paper_count=1,
            )
            with mock.patch.object(mcp_server.Config, "load", return_value=SimpleNamespace(cache_dir=tmp)), \
                 mock.patch.object(mcp_server.report_bridge, "start_report_from_session", return_value=fake):
                result = asyncio.run(
                    mcp_server.generate_recovery_report(
                        sidecar_path=str(sidecar_path),
                        mode="seed_preview",
                    )
                )

            self.assertIn("search-restored", result)
            self.assertIn("CNKI 下载结果集合", result)

    def test_generate_recovery_report_rejects_seed_classified_mode(self):
        with tempfile.TemporaryDirectory() as tmp:
            sidecar_path = Path(tmp) / "download-workflows" / "download-abc.json"
            sidecar_path.parent.mkdir(parents=True, exist_ok=True)
            sidecar_path.write_text(
                json.dumps(
                    {
                        "workflow_id": "download-abc",
                        "root_session_id": "search-root",
                        "source_session_id": "search-root",
                        "display_query": "CNKI 下载结果集合",
                        "items": [
                            {
                                "hit_key": "cnki:ABC123",
                                "title": "知网论文",
                            }
                        ],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            with mock.patch.object(mcp_server.Config, "load", return_value=SimpleNamespace(cache_dir=tmp)), \
                 mock.patch.object(mcp_server.report_bridge, "start_report_from_session") as report_mock:
                result = asyncio.run(
                    mcp_server.generate_recovery_report(
                        sidecar_path=str(sidecar_path),
                        mode="seed_classified",
                    )
                )

            report_mock.assert_not_called()
            self.assertIn("Recovery reports do not run formal RCS classification", result)

    def test_generate_recovery_report_can_use_explicit_legacy_report_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            report_json = Path(tmp) / "materialized" / "report_data.json"
            report_json.parent.mkdir(parents=True, exist_ok=True)
            report_json.write_text(
                json.dumps(
                    {
                        "metadata": {
                            "query": "恢复后的展示标题",
                            "original_query": "原始检索词",
                            "display_query": "恢复后的展示标题",
                            "generated_at": "2026-06-04T04:00:00+00:00",
                            "seed_session_id": "search-legacy",
                            "source_summary": {"cnki": 1},
                            "seed_source": "cnki",
                            "quality_profile": {"query_trace_level": "imported"},
                        },
                        "paper_list": [
                            {
                                "paper_id": "cnki:ABC123",
                                "title": "知网论文",
                                "authors": ["张三"],
                                "source": "cnki",
                                "source_url": "https://kns.cnki.net/kcms2/article/abstract?filename=ABC123",
                                "cnki_id": "ABC123",
                            }
                        ],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            fake = mcp_server.report_bridge.ReportJob(
                report_path="F:/AI playground/TempFiles/report.html",
                file_url="file:///F:/AI%20playground/TempFiles/report.html",
                seed_session_id="search-restored",
                status="started",
                report_mode="seed_preview",
                pid=12345,
                log_path="F:/AI playground/TempFiles/report.log",
                expanded_sources=["cnki"],
                deduped_paper_count=1,
            )
            with mock.patch.object(mcp_server.Config, "load", return_value=SimpleNamespace(cache_dir=tmp)), \
                 mock.patch.object(mcp_server.report_bridge, "start_report_from_session", return_value=fake):
                result = asyncio.run(
                    mcp_server.generate_recovery_report(
                        report_json=str(report_json),
                        prefer="B",
                        mode="seed_preview",
                    )
                )

            self.assertIn("Recovery Kind: `B`", result)
            self.assertIn("恢复后的展示标题", result)

    def test_cnki_visible_smoke_defaults_to_dry_run(self):
        result = asyncio.run(
            mcp_server.cnki_visible_smoke(
                query="钙钛矿",
                limit=99,
            )
        )

        self.assertIn("dry_run", result)
        self.assertIn("Dry Run: true", result)
        self.assertIn("Limit: 3", result)

    def test_cnki_visible_smoke_requires_confirmation_for_live(self):
        result = asyncio.run(
            mcp_server.cnki_visible_smoke(
                detail_url="https://kns.cnki.net/kcms2/article/abstract?filename=ABC123",
                dry_run=False,
                confirm_live_access=False,
            )
        )

        self.assertIn("confirmation_required", result)
        self.assertIn("明确确认", result)

    def test_get_cnki_paper_detail_from_html(self):
        html = """
        <html><body>
          <h1 class="title">CNKI Detail</h1>
          <div class="author">Zhang; Li</div>
          <div class="sourinfo">Journal 2024</div>
          <div id="ChDivSummary">Abstract text</div>
        </body></html>
        """

        result = asyncio.run(
            mcp_server.get_cnki_paper_detail(
                url_or_id="https://kns.cnki.net/kcms2/article/abstract?filename=ABC123",
                html=html,
            )
        )

        self.assertIn("# CNKI Detail", result)
        self.assertIn("Abstract text", result)

    def test_get_cnki_paper_detail_without_html_is_gated(self):
        result = asyncio.run(mcp_server.get_cnki_paper_detail(url_or_id="ABC123"))

        self.assertIn("live_access_not_enabled", result)
        self.assertIn("不会直接访问 CNKI", result)

    def test_search_cnki_from_html_parses_and_saves_session(self):
        html = """
        <table class="result-table-list">
          <tr>
            <td class="name"><a href="/kcms2/article/abstract?filename=ABC123&dbcode=CJFD">题名一</a></td>
            <td class="author">张三</td>
            <td class="source">期刊一</td>
            <td class="date">2024</td>
          </tr>
        </table>
        """
        with tempfile.TemporaryDirectory(dir=Path("F:/AI playground/TempFiles")) as tmp:
            with mock.patch.object(mcp_server.Config, "load", return_value=SimpleNamespace(cache_dir=tmp)):
                result = asyncio.run(
                    mcp_server.search_cnki_from_html(
                        "钙钛矿",
                        html=html,
                        limit=1,
                    )
                )

        self.assertIn("Search Session:", result)
        self.assertIn("题名一", result)
        self.assertIn("CNKI ID:** ABC123", result)

    def test_search_cnki_from_html_without_html_is_gated(self):
        result = asyncio.run(mcp_server.search_cnki_from_html("钙钛矿"))

        self.assertIn("live_access_not_enabled", result)
        self.assertIn("不会直接访问 CNKI", result)
