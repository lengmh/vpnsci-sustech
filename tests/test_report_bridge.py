import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from vpnsci_sustech.config import Config
from vpnsci_sustech.report_bridge import (
    ReportBridgeConfigError,
    apply_rcs_classification_and_render,
    apply_theme_postprocess_and_render,
    _render_command,
    generate_report_from_session,
    normalize_report_mode,
    path_to_file_url,
    start_report_from_session,
)
from vpnsci_sustech.sources.search_cache import SearchSession, save_session
from vpnsci_sustech.sources.search_models import SearchHit


def _command_value(command, *flags):
    for flag in flags:
        if flag in command:
            return command[command.index(flag) + 1]
    raise AssertionError(f"missing one of {flags!r} in command: {command!r}")


class ReportBridgeTests(unittest.TestCase):
    def test_report_mode_normalization_separates_full_and_seed_preview(self):
        self.assertEqual(normalize_report_mode("full"), "full")
        self.assertEqual(normalize_report_mode("professional"), "full")
        self.assertEqual(normalize_report_mode("seed_preview"), "seed_preview")
        self.assertEqual(normalize_report_mode("standard"), "seed_preview")
        self.assertEqual(normalize_report_mode("seed_classified"), "seed_classified")
        self.assertEqual(normalize_report_mode("seed-classified"), "seed_classified")

    def test_render_command_supports_paths_with_spaces_and_optional_quotes(self):
        seed = Path(r"F:\AI playground\TempFiles\seed.json")
        out = Path(r"F:\AI playground\TempFiles\reports")

        unquoted = _render_command(
            "python fake_runner.py --seed {seed_json} --output {output_dir} --mode {mode}",
            seed_json=seed,
            output_dir=out,
            session_id="search-test",
            mode="standard",
        )
        quoted = _render_command(
            'python fake_runner.py --seed "{seed_json}" --output "{output_dir}" --session {session_id}',
            seed_json=seed,
            output_dir=out,
            session_id="search-test",
            mode="standard",
        )

        self.assertEqual(unquoted[3], str(seed))
        self.assertEqual(unquoted[5], str(out))
        self.assertEqual(quoted[3], str(seed))
        self.assertEqual(quoted[5], str(out))
        self.assertEqual(quoted[7], "search-test")

    def test_unconfigured_bridge_raises_clear_config_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg = Config(cache_dir=tmp)
            session = SearchSession(
                session_id="search-test",
                query="graph neural network",
                filters={},
                hits=[SearchHit(title="Paper", doi="10.1000/a")],
            )
            save_session(session, Path(tmp))

            with mock.patch(
                "vpnsci_sustech.report_bridge.report_tools.ensure_report_tool_configured",
                side_effect=ReportBridgeConfigError("paper_search_pro_root is not configured"),
            ):
                with self.assertRaises(ReportBridgeConfigError):
                    generate_report_from_session("search-test", config=cfg)

    def test_empty_bridge_config_autoconfigures_bundled_tool(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "paper-search-pro"
            output_dir = Path(tmp) / "reports"
            root.mkdir()
            output_dir.mkdir()
            cfg = Config(cache_dir=tmp)
            configured = Config(
                cache_dir=tmp,
                paper_search_pro_root=str(root),
                paper_search_pro_command="python -m vpnsci_sustech.paper_search_pro_adapter --seed {seed_json} --output-dir {output_dir}",
                paper_search_pro_output_dir=str(output_dir),
            )
            session = SearchSession(
                session_id="search-test",
                query="graph neural network",
                filters={},
                hits=[SearchHit(title="Paper", doi="10.1000/a")],
            )
            save_session(session, Path(tmp))

            def fake_run(command, **kwargs):
                out_dir = Path(_command_value(command, "--output-dir", "--output"))
                out_dir.mkdir(parents=True, exist_ok=True)
                (out_dir / "report.html").write_text("<html>report</html>", encoding="utf-8")
                return mock.Mock(returncode=0, stdout="ok", stderr="")

            with mock.patch(
                "vpnsci_sustech.report_bridge.report_tools.ensure_report_tool_configured",
                return_value=configured,
            ), mock.patch("vpnsci_sustech.report_bridge.subprocess.run", side_effect=fake_run):
                result = generate_report_from_session("search-test", config=cfg)

            self.assertEqual(result.report_path, str(output_dir / "search-test" / "report.html"))
            self.assertEqual(result.file_url, path_to_file_url(output_dir / "search-test" / "report.html"))

    def test_bridge_writes_seed_package_to_session_output_and_returns_report_result(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "paper-search-pro"
            output_dir = Path(tmp) / "reports"
            root.mkdir()
            output_dir.mkdir()
            cfg = Config(
                cache_dir=tmp,
                paper_search_pro_root=str(root),
                paper_search_pro_command="python -m vpnsci_sustech.paper_search_pro_adapter --seed {seed_json} --output-dir {output_dir}",
                paper_search_pro_output_dir=str(output_dir),
            )
            session = SearchSession(
                session_id="search-test",
                query="graph neural network",
                filters={"limit": 5},
                hits=[SearchHit(title="Paper", doi="10.1000/a")],
                source_summary={"openalex": 1},
            )
            save_session(session, Path(tmp))

            def fake_run(command, **kwargs):
                out_dir = Path(_command_value(command, "--output-dir", "--output"))
                out_dir.mkdir(parents=True, exist_ok=True)
                (out_dir / "report.html").write_text("<html>report</html>", encoding="utf-8")
                return mock.Mock(returncode=0, stdout="ok", stderr="")

            with mock.patch("vpnsci_sustech.report_bridge.subprocess.run", side_effect=fake_run) as run_mock:
                result = generate_report_from_session("search-test", config=cfg)

            report_path = output_dir / "search-test" / "report.html"
            self.assertEqual(result.report_path, str(report_path))
            self.assertEqual(result.seed_session_id, "search-test")
            self.assertEqual(result.deduped_paper_count, 1)
            command = run_mock.call_args.args[0]
            seed_arg = command[command.index("--seed") + 1]
            self.assertEqual(seed_arg, str(output_dir / "search-test" / "search-test-seed.json"))
            self.assertEqual(command[command.index("--output-dir") + 1], str(output_dir / "search-test"))
            seed_data = json.loads(Path(seed_arg).read_text(encoding="utf-8"))
            self.assertEqual(seed_data["session_id"], "search-test")
            self.assertEqual(seed_data["hits"][0]["doi"], "10.1000/a")

    def test_generate_report_from_session_seed_classified_returns_rcs_request_without_rendering(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "paper-search-pro"
            output_dir = Path(tmp) / "reports"
            root.mkdir()
            cfg = Config(
                cache_dir=tmp,
                paper_search_pro_root=str(root),
                paper_search_pro_command="python -m vpnsci_sustech.paper_search_pro_adapter --seed {seed_json} --output-dir {output_dir}",
                paper_search_pro_output_dir=str(output_dir),
            )
            session = SearchSession(
                session_id="search-sync-seed-classified",
                query="graph neural network",
                filters={},
                hits=[SearchHit(title="Paper", doi="10.1000/a")],
                source_summary={"openalex": 1},
            )
            save_session(session, Path(tmp))

            with mock.patch("vpnsci_sustech.report_bridge.subprocess.run") as run_mock:
                result = generate_report_from_session(
                    "search-sync-seed-classified",
                    config=cfg,
                    mode="seed_classified",
                )

            run_mock.assert_not_called()
            self.assertEqual(result.status, "rcs_classification_required")
            self.assertEqual(result.report_mode, "seed_classified")
            self.assertTrue(result.rcs_classification_request_path.endswith("rcs_classification_request.json"))
            self.assertTrue(Path(result.rcs_classification_request_path).exists())
            self.assertEqual(result.failures, ["rcs_classification_pending"])

    def test_start_report_from_session_launches_background_process_without_waiting(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "paper-search-pro"
            output_dir = Path(tmp) / "reports"
            root.mkdir()
            cfg = Config(
                cache_dir=tmp,
                paper_search_pro_root=str(root),
                paper_search_pro_command="python -m vpnsci_sustech.paper_search_pro_adapter --seed {seed_json} --output-dir {output_dir}",
                paper_search_pro_output_dir=str(output_dir),
            )
            session = SearchSession(
                session_id="search-test",
                query="graph neural network",
                filters={"limit": 5},
                hits=[SearchHit(title="Paper", doi="10.1000/a")],
                source_summary={"openalex": 1},
            )
            save_session(session, Path(tmp))
            fake_process = mock.Mock(pid=12345)

            with mock.patch("vpnsci_sustech.report_bridge.subprocess.Popen", return_value=fake_process) as popen_mock, \
                 mock.patch("vpnsci_sustech.report_bridge.subprocess.run") as run_mock:
                job = start_report_from_session(
                    "search-test",
                    config=cfg,
                    mode="seed_preview",
                    display_query="非接触体温测量",
                    language="zh",
                    open_report=True,
                )

            self.assertEqual(job.seed_session_id, "search-test")
            self.assertEqual(job.report_mode, "seed_preview")
            self.assertEqual(job.pid, 12345)
            self.assertEqual(job.status, "started")
            self.assertEqual(job.report_path, str(output_dir / "search-test" / "report.html"))
            self.assertEqual(job.file_url, path_to_file_url(output_dir / "search-test" / "report.html"))
            self.assertEqual(job.log_path, str(output_dir / "search-test" / "report.log"))
            launched_command = popen_mock.call_args.args[0]
            launched_kwargs = popen_mock.call_args.kwargs
            self.assertEqual(launched_command[0], sys.executable)
            self.assertEqual(launched_command[launched_command.index("--seed") + 1], str(output_dir / "search-test" / "search-test-seed.json"))
            self.assertEqual(launched_command[launched_command.index("--output-dir") + 1], str(output_dir / "search-test"))
            self.assertIn("--display-query", launched_command)
            self.assertIn("非接触体温测量", launched_command)
            self.assertIn("--language", launched_command)
            self.assertIn("zh", launched_command)
            self.assertIn("--open-report", launched_command)
            self.assertIs(launched_kwargs["stdin"], subprocess.DEVNULL)
            self.assertTrue(launched_kwargs["close_fds"])
            run_mock.assert_not_called()

    def test_full_mode_with_builtin_seed_adapter_returns_handoff_without_launching_process(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "paper-search-pro"
            output_dir = Path(tmp) / "reports"
            root.mkdir()
            cfg = Config(
                cache_dir=tmp,
                paper_search_pro_root=str(root),
                paper_search_pro_command="python -m vpnsci_sustech.paper_search_pro_adapter --seed {seed_json} --output-dir {output_dir}",
                paper_search_pro_output_dir=str(output_dir),
            )
            session = SearchSession(
                session_id="search-test",
                query="infrared thermometry",
                filters={"limit": 5},
                hits=[SearchHit(title="Paper", doi="10.1000/a")],
                source_summary={"openalex": 1},
            )
            save_session(session, Path(tmp))

            with mock.patch("vpnsci_sustech.report_bridge.subprocess.Popen") as popen_mock:
                job = start_report_from_session(
                    "search-test",
                    config=cfg,
                    mode="full",
                    display_query="非接触体温测量",
                    language="zh",
                )

            popen_mock.assert_not_called()
            self.assertEqual(job.status, "handoff_required")
            self.assertEqual(job.report_mode, "full")
            self.assertEqual(job.report_path, "")
            self.assertEqual(job.file_url, "")
            self.assertTrue(job.handoff_path.endswith("instructions.md"))
            instructions = Path(job.handoff_path).read_text(encoding="utf-8")
            self.assertIn("Full paper-search-pro workflow", instructions)
            self.assertIn("非接触体温测量", instructions)
            self.assertIn("search-test", instructions)
            self.assertIn("multi_agent_v1.spawn_agent", instructions)
            self.assertIn("subagent_spawn_failed", instructions)
            self.assertIn("main-Agent serial classification", instructions)
            self.assertIn("run `seed_preview` HTML report", instructions)
            context = json.loads(
                (Path(job.handoff_path).parent / "query_plan_context.json").read_text(encoding="utf-8")
            )
            self.assertEqual(context["automation"]["runner"], "codex-session")
            self.assertTrue(context["automation"]["requires_multi_agent"])
            self.assertEqual(context["automation"]["subagent_tool"], "multi_agent_v1.spawn_agent")
            self.assertEqual(context["automation"]["fallback_allowed"], "explicit_user_choice_only")
            self.assertTrue(context["automation"]["fallback_prompt_required"])
            self.assertEqual(
                [item["id"] for item in context["automation"]["fallback_options"]],
                ["seed_preview", "seed_classified", "main_agent_serial", "stop"],
            )
            self.assertEqual(
                context["automation"]["subagent_failure_policy"],
                "ask_user_before_degraded_execution",
            )
            self.assertEqual(context["failure_reporting"]["report_channel"], "current_conversation")
            self.assertIn("subagent_spawn_failed", context["failure_reporting"]["failure_codes"])
            self.assertIn("subagent_timeout", context["failure_reporting"]["failure_codes"])
            self.assertIn("subagent_result_invalid", context["failure_reporting"]["failure_codes"])
            self.assertIn("full_workflow_step_failed", context["failure_reporting"]["failure_codes"])

    def test_full_handoff_marks_cnki_seed_source_and_fields(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "paper-search-pro"
            output_dir = Path(tmp) / "reports"
            root.mkdir()
            cfg = Config(
                cache_dir=tmp,
                paper_search_pro_root=str(root),
                paper_search_pro_command="python -m vpnsci_sustech.paper_search_pro_adapter --seed {seed_json} --output-dir {output_dir}",
                paper_search_pro_output_dir=str(output_dir),
            )
            session = SearchSession(
                session_id="search-cnki",
                query="钙钛矿 中国知网",
                filters={"backend": "cnki"},
                hits=[
                    SearchHit(
                        title="钙钛矿太阳能电池稳定性研究",
                        cnki_id="ABC123",
                        source_url="https://kns.cnki.net/kcms2/article/abstract?filename=ABC123",
                        download_format="caj",
                        local_file="F:/AI playground/TempFiles/source.caj",
                        result_type="journal",
                        source="cnki",
                        backend="cnki",
                        sources=["cnki"],
                    )
                ],
                source_summary={"cnki": 1},
            )
            save_session(session, Path(tmp))

            job = start_report_from_session(
                "search-cnki",
                config=cfg,
                mode="full",
                display_query="钙钛矿 中国知网",
                language="zh",
            )

            context = json.loads(
                (Path(job.handoff_path).parent / "query_plan_context.json").read_text(encoding="utf-8")
            )
            self.assertEqual(context["seed_source"], "cnki")
            self.assertTrue(context["cnki_fields"]["present"])
            self.assertEqual(context["cnki_fields"]["hit_count"], 1)
            self.assertEqual(context["cnki_fields"]["preserved_counts"]["cnki_id"], 1)
            self.assertIn("local_file", context["cnki_fields"]["fields"])

    def test_full_handoff_marks_mixed_seed_when_cnki_is_not_only_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "paper-search-pro"
            output_dir = Path(tmp) / "reports"
            root.mkdir()
            cfg = Config(
                cache_dir=tmp,
                paper_search_pro_root=str(root),
                paper_search_pro_command="python -m vpnsci_sustech.paper_search_pro_adapter --seed {seed_json} --output-dir {output_dir}",
                paper_search_pro_output_dir=str(output_dir),
            )
            session = SearchSession(
                session_id="search-mixed",
                query="钙钛矿",
                filters={},
                hits=[
                    SearchHit(
                        title="CNKI paper",
                        cnki_id="ABC123",
                        source="cnki",
                        backend="cnki",
                        sources=["cnki"],
                    ),
                    SearchHit(
                        title="OpenAlex paper",
                        doi="10.1234/example",
                        source="openalex",
                        backend="openalex",
                        sources=["openalex"],
                    ),
                ],
                source_summary={"cnki": 1, "openalex": 1},
            )
            save_session(session, Path(tmp))

            job = start_report_from_session(
                "search-mixed",
                config=cfg,
                mode="full",
                display_query="钙钛矿",
                language="zh",
            )

            context = json.loads(
                (Path(job.handoff_path).parent / "query_plan_context.json").read_text(encoding="utf-8")
            )
            self.assertEqual(context["seed_source"], "mixed")
            self.assertTrue(context["cnki_fields"]["present"])
            self.assertEqual(context["cnki_fields"]["hit_count"], 1)

    def test_non_adapter_command_is_not_given_adapter_specific_flags(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "paper-search-pro"
            output_dir = Path(tmp) / "reports"
            root.mkdir()
            cfg = Config(
                cache_dir=tmp,
                paper_search_pro_root=str(root),
                paper_search_pro_command="python external_runner.py --seed {seed_json} --output {output_dir}",
                paper_search_pro_output_dir=str(output_dir),
            )
            session = SearchSession(
                session_id="search-test",
                query="graph neural network",
                filters={},
                hits=[SearchHit(title="Paper", doi="10.1000/a")],
            )
            save_session(session, Path(tmp))

            with mock.patch("vpnsci_sustech.report_bridge.subprocess.Popen", return_value=mock.Mock(pid=123)) as popen_mock:
                start_report_from_session(
                    "search-test",
                    config=cfg,
                    display_query="图神经网络",
                    language="zh",
                    open_report=True,
                )

            launched_command = popen_mock.call_args.args[0]
            self.assertNotIn("--display-query", launched_command)
            self.assertNotIn("--language", launched_command)
            self.assertNotIn("--open-report", launched_command)

    def test_builtin_adapter_command_is_detected_when_launched_as_script(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "paper-search-pro"
            output_dir = Path(tmp) / "reports"
            root.mkdir()
            cfg = Config(
                cache_dir=tmp,
                paper_search_pro_root=str(root),
                paper_search_pro_command="python vpnsci_sustech/paper_search_pro_adapter.py --seed {seed_json} --output-dir {output_dir}",
                paper_search_pro_output_dir=str(output_dir),
            )
            session = SearchSession(
                session_id="search-test",
                query="graph neural network",
                filters={},
                hits=[SearchHit(title="Paper", doi="10.1000/a")],
            )
            save_session(session, Path(tmp))

            with mock.patch("vpnsci_sustech.report_bridge.subprocess.Popen", return_value=mock.Mock(pid=123)) as popen_mock:
                start_report_from_session(
                    "search-test",
                    config=cfg,
                    display_query="红外线测量",
                    language="zh",
                    open_report=True,
                )

            launched_command = popen_mock.call_args.args[0]
            self.assertIn("--display-query", launched_command)
            self.assertIn("红外线测量", launched_command)
            self.assertIn("--language", launched_command)
            self.assertIn("zh", launched_command)
            self.assertIn("--open-report", launched_command)

    def test_seed_preview_pending_theme_postprocess_returns_host_agent_handoff(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "paper-search-pro"
            output_dir = Path(tmp) / "reports"
            root.mkdir()
            cfg = Config(
                cache_dir=tmp,
                paper_search_pro_root=str(root),
                paper_search_pro_command="python -m vpnsci_sustech.paper_search_pro_adapter --seed {seed_json} --output-dir {output_dir}",
                paper_search_pro_output_dir=str(output_dir),
            )
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
            save_session(session, Path(tmp))

            with mock.patch("vpnsci_sustech.report_bridge.subprocess.Popen") as popen_mock:
                job = start_report_from_session(
                    "search-theme-postprocess",
                    config=cfg,
                    mode="seed_preview",
                    display_query="federated learning in hospitals",
                    language="en",
                )

            popen_mock.assert_not_called()
            self.assertEqual(job.status, "theme_postprocess_required")
            self.assertEqual(job.report_mode, "seed_preview")
            self.assertTrue(job.materialized_dir.endswith("materialized"))
            self.assertTrue(job.theme_postprocess_request_path.endswith("theme_postprocess_request.json"))
            self.assertTrue(job.theme_postprocess_result_path.endswith("theme_postprocess_result.json"))
            self.assertEqual(job.language, "en")
            self.assertEqual(job.user_query, "federated learning in hospitals")
            self.assertTrue(Path(job.theme_postprocess_request_path).exists())
            request_payload = json.loads(Path(job.theme_postprocess_request_path).read_text(encoding="utf-8"))
            self.assertEqual(request_payload["report_mode"], "seed_preview")
            self.assertTrue(request_payload["themes"])

    def test_seed_classified_returns_host_agent_rcs_classification_request(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "paper-search-pro"
            output_dir = Path(tmp) / "reports"
            root.mkdir()
            output_dir.mkdir()
            cfg = Config(
                cache_dir=tmp,
                paper_search_pro_root=str(root),
                paper_search_pro_command="python -m vpnsci_sustech.paper_search_pro_adapter --seed {seed_json} --output-dir {output_dir}",
                paper_search_pro_output_dir=str(output_dir),
            )
            session = SearchSession(
                session_id="search-seed-classified",
                query="graph neural network",
                filters={},
                hits=[
                    SearchHit(
                        title="Graph neural networks for molecular property prediction",
                        doi="10.1000/gnn",
                        abstract="A study of graph neural networks for molecular property prediction.",
                    )
                ],
                source_summary={"openalex": 1},
            )
            save_session(session, Path(tmp))

            with mock.patch("vpnsci_sustech.report_bridge.subprocess.Popen") as popen_mock:
                job = start_report_from_session(
                    "search-seed-classified",
                    config=cfg,
                    mode="seed_classified",
                    display_query="graph neural network",
                    language="en",
                )

            popen_mock.assert_not_called()
            self.assertEqual(job.status, "rcs_classification_required")
            self.assertEqual(job.report_mode, "seed_classified")
            self.assertTrue(job.materialized_dir.endswith("materialized"))
            self.assertTrue(job.rcs_classification_request_path.endswith("rcs_classification_request.json"))
            self.assertTrue(job.rcs_classification_result_path.endswith("rcs_classification_result.json"))
            request_payload = json.loads(Path(job.rcs_classification_request_path).read_text(encoding="utf-8"))
            self.assertEqual(request_payload["report_mode"], "seed_classified")
            self.assertEqual(request_payload["rcs_scope"], "seed_set")
            self.assertEqual(request_payload["classification_owner"], "host_agent")
            self.assertIn("rcs_rubric.md", request_payload["rubric_reference"])
            self.assertEqual(request_payload["expected_output_schema"]["required"], ["paper_id", "rcs", "reasoning"])
            self.assertEqual(request_payload["papers"][0]["paper_id"], "doi:10.1000/gnn")
            self.assertEqual(request_payload["papers"][0]["title"], "Graph neural networks for molecular property prediction")
            metadata = json.loads((Path(job.materialized_dir) / "metadata.json").read_text(encoding="utf-8"))
            self.assertEqual(metadata["report_mode"], "seed_classified")
            self.assertEqual(metadata["rcs_execution_mode"], "none")
            self.assertEqual(metadata["rcs_scope"], "none")

    def test_seed_classified_existing_rcs_result_can_continue_to_theme_postprocess(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "paper-search-pro"
            output_dir = Path(tmp) / "reports"
            root.mkdir()
            output_dir.mkdir()
            cfg = Config(
                cache_dir=tmp,
                paper_search_pro_root=str(root),
                paper_search_pro_command="python -m vpnsci_sustech.paper_search_pro_adapter --seed {seed_json} --output-dir {output_dir}",
                paper_search_pro_output_dir=str(output_dir),
            )
            session = SearchSession(
                session_id="search-seed-classified-theme",
                query="graph neural network",
                filters={},
                hits=[
                    SearchHit(
                        title="Graph neural networks for molecular property prediction",
                        doi="10.1000/gnn",
                        abstract="A study of graph neural networks for molecular property prediction.",
                    ),
                    SearchHit(
                        title="Molecular graph representation learning",
                        doi="10.1000/mol",
                        abstract="Graph representation learning for molecular property prediction.",
                    ),
                ],
                source_summary={"openalex": 2},
            )
            save_session(session, Path(tmp))

            start_report_from_session(
                "search-seed-classified-theme",
                config=cfg,
                mode="seed_classified",
                display_query="graph neural network",
                language="en",
            )
            with mock.patch(
                "vpnsci_sustech.report_bridge.render_html_webartifacts",
                side_effect=lambda materialized_data_dir, output_path, user_query, language, tool_root=None: output_path.write_text("<html>ok</html>", encoding="utf-8"),
            ):
                apply_rcs_classification_and_render(
                    "search-seed-classified-theme",
                    result_payload=[
                        {
                            "paper_id": "doi:10.1000/gnn",
                            "rcs": 8,
                            "reasoning": "Directly evaluates graph neural networks for molecular property prediction.",
                            "flag": None,
                        },
                        {
                            "paper_id": "doi:10.1000/mol",
                            "rcs": 6,
                            "reasoning": "Closely related graph representation learning for molecules.",
                            "flag": None,
                        },
                    ],
                    rcs_execution_mode="subagent_parallel",
                    config=cfg,
                    display_query="graph neural network",
                    language="en",
                    open_report=False,
                )

            with mock.patch("vpnsci_sustech.report_bridge.subprocess.Popen") as popen_mock:
                second = start_report_from_session(
                    "search-seed-classified-theme",
                    config=cfg,
                    mode="seed_classified",
                    display_query="graph neural network",
                    language="en",
                )

            popen_mock.assert_not_called()
            self.assertEqual(second.status, "theme_postprocess_required")
            self.assertEqual(second.report_mode, "seed_classified")
            materialized = Path(second.materialized_dir)
            papers = json.loads((materialized / "paper_list.json").read_text(encoding="utf-8"))
            metadata = json.loads((materialized / "metadata.json").read_text(encoding="utf-8"))
            self.assertTrue(all(paper["rcs_valid"] for paper in papers))
            self.assertEqual({paper["rcs_source"] for paper in papers}, {"seed_classifier"})
            self.assertEqual(metadata["rcs_scope"], "seed_set")
            self.assertEqual(metadata["rcs_valid_count"], 2)

    def test_seed_classified_existing_all_parser_fallback_result_is_not_reclassified(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "paper-search-pro"
            output_dir = Path(tmp) / "reports"
            root.mkdir()
            output_dir.mkdir()
            cfg = Config(
                cache_dir=tmp,
                paper_search_pro_root=str(root),
                paper_search_pro_command="python -m vpnsci_sustech.paper_search_pro_adapter --seed {seed_json} --output-dir {output_dir}",
                paper_search_pro_output_dir=str(output_dir),
            )
            session = SearchSession(
                session_id="search-seed-classified-parser-fallback",
                query="graph neural network",
                filters={},
                hits=[
                    SearchHit(
                        title="Malformed metadata paper",
                        doi="10.1000/malformed",
                        abstract="Graph neural network metadata is malformed.",
                    )
                ],
                source_summary={"openalex": 1},
            )
            save_session(session, Path(tmp))

            start_report_from_session(
                "search-seed-classified-parser-fallback",
                config=cfg,
                mode="seed_classified",
                display_query="graph neural network",
                language="en",
            )
            with mock.patch(
                "vpnsci_sustech.report_bridge.render_html_webartifacts",
                side_effect=lambda materialized_data_dir, output_path, user_query, language, tool_root=None: output_path.write_text("<html>ok</html>", encoding="utf-8"),
            ):
                applied = apply_rcs_classification_and_render(
                    "search-seed-classified-parser-fallback",
                    result_payload=[
                        {
                            "paper_id": "doi:10.1000/malformed",
                            "rcs": 5,
                            "reasoning": "Classifier output could not be trusted for this malformed record.",
                            "flag": "parse_failed_uncertain",
                        }
                    ],
                    rcs_execution_mode="main_agent_serial",
                    config=cfg,
                    display_query="graph neural network",
                    language="en",
                    open_report=False,
                )

            with mock.patch("vpnsci_sustech.report_bridge.subprocess.Popen", return_value=mock.Mock(pid=123)) as popen_mock:
                second = start_report_from_session(
                    "search-seed-classified-parser-fallback",
                    config=cfg,
                    mode="seed_classified",
                    display_query="graph neural network",
                    language="en",
                )

            self.assertNotEqual(second.status, "rcs_classification_required")
            materialized = Path(applied.materialized_dir)
            papers = json.loads((materialized / "paper_list.json").read_text(encoding="utf-8"))
            metadata = json.loads((materialized / "metadata.json").read_text(encoding="utf-8"))
            self.assertFalse(papers[0]["rcs_valid"])
            self.assertEqual(papers[0]["rcs_source"], "parser_fallback")
            self.assertEqual(metadata["rcs_execution_mode"], "main_agent_serial")
            self.assertEqual(metadata["rcs_valid_count"], 0)
            if second.status == "started":
                popen_mock.assert_called_once()

    def test_apply_seed_classified_rcs_result_updates_materialized_stats_and_renders(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "paper-search-pro"
            output_dir = Path(tmp) / "reports"
            root.mkdir()
            output_dir.mkdir()
            cfg = Config(
                cache_dir=tmp,
                paper_search_pro_root=str(root),
                paper_search_pro_command="python -m vpnsci_sustech.paper_search_pro_adapter --seed {seed_json} --output-dir {output_dir}",
                paper_search_pro_output_dir=str(output_dir),
            )
            session = SearchSession(
                session_id="search-seed-classified-apply",
                query="graph neural network",
                filters={},
                hits=[
                    SearchHit(
                        title="Graph neural networks for molecular property prediction",
                        doi="10.1000/gnn",
                        year=2024,
                        abstract="A study of graph neural networks for molecular property prediction.",
                    )
                ],
                source_summary={"openalex": 1},
            )
            save_session(session, Path(tmp))
            start_report_from_session(
                "search-seed-classified-apply",
                config=cfg,
                mode="seed_classified",
                display_query="graph neural network",
                language="en",
            )

            with mock.patch(
                "vpnsci_sustech.report_bridge.render_html_webartifacts",
                side_effect=lambda materialized_data_dir, output_path, user_query, language, tool_root=None: output_path.write_text("<html>ok</html>", encoding="utf-8"),
            ):
                result = apply_rcs_classification_and_render(
                    "search-seed-classified-apply",
                    result_payload=[
                        {
                            "paper_id": "doi:10.1000/gnn",
                            "rcs": 8,
                            "reasoning": "Directly evaluates graph neural networks for the requested domain.",
                            "flag": None,
                        }
                    ],
                    rcs_execution_mode="main_agent_serial",
                    config=cfg,
                    display_query="graph neural network",
                    language="en",
                    open_report=False,
                )

            self.assertEqual(result.status, "completed")
            self.assertEqual(result.report_mode, "seed_classified")
            self.assertTrue(Path(result.report_path).exists())
            materialized = Path(result.materialized_dir)
            papers = json.loads((materialized / "paper_list.json").read_text(encoding="utf-8"))
            metadata = json.loads((materialized / "metadata.json").read_text(encoding="utf-8"))
            chart_data = json.loads((materialized / "chart_data.json").read_text(encoding="utf-8"))

            self.assertEqual(papers[0]["rcs"], 8)
            self.assertTrue(papers[0]["rcs_valid"])
            self.assertEqual(papers[0]["rcs_source"], "seed_classifier")
            self.assertIsNone(papers[0]["rcs_flag"])
            self.assertEqual(metadata["rcs_execution_mode"], "main_agent_serial")
            self.assertEqual(metadata["rcs_scope"], "seed_set")
            self.assertEqual(metadata["rcs_valid_count"], 1)
            self.assertEqual(metadata["highly_relevant_count"], 1)
            self.assertEqual(metadata["closely_related_count"], 0)
            self.assertIn("seed", metadata["rcs_notice"].lower())
            self.assertEqual(chart_data["relevance_score"]["n"], 1)
            self.assertEqual(chart_data["relevance_score"]["bins"][8]["count"], 1)
            self.assertTrue((materialized / "rcs_classification_result.json").exists())

    def test_full_existing_materialized_pending_theme_postprocess_returns_host_agent_handoff(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "paper-search-pro"
            output_dir = Path(tmp) / "reports"
            session_dir = output_dir / "search-full-theme"
            materialized = session_dir / "materialized"
            root.mkdir()
            materialized.mkdir(parents=True, exist_ok=True)
            cfg = Config(
                cache_dir=tmp,
                paper_search_pro_root=str(root),
                paper_search_pro_command="python -m vpnsci_sustech.paper_search_pro_adapter --seed {seed_json} --output-dir {output_dir}",
                paper_search_pro_output_dir=str(output_dir),
            )
            session = SearchSession(
                session_id="search-full-theme",
                query="核物理治疗方法",
                filters={},
                hits=[SearchHit(title="seed paper", doi="10.1/seed")],
                source_summary={"openalex": 1},
            )
            save_session(session, Path(tmp))
            (materialized / "metadata.json").write_text(
                json.dumps({"query": "核物理治疗方法", "display_query": "核物理治疗方法", "language": "zh"}, ensure_ascii=False),
                encoding="utf-8",
            )
            (materialized / "paper_list.json").write_text(
                json.dumps(
                    [
                        {"paper_id": "10.1/a", "title": "Targeted radionuclide therapy review"},
                        {"paper_id": "10.1/b", "title": "Boron neutron capture therapy progress"},
                    ],
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            (materialized / "prisma_log.json").write_text(json.dumps({}, ensure_ascii=False), encoding="utf-8")
            chart_payload = {
                "raw_theme_treemap": {
                    "themes": [
                        {"name": "Targeted Radionuclide Therapy", "value": 2, "paper_ids": ["10.1/a"]},
                        {"name": "Boron Neutron Capture Therapy", "value": 2, "paper_ids": ["10.1/b"]},
                    ],
                    "total_papers": 2,
                },
                "theme_treemap": {
                    "themes": [
                        {"name": "Targeted Radionuclide Therapy", "value": 2, "paper_ids": ["10.1/a"]},
                        {"name": "Boron Neutron Capture Therapy", "value": 2, "paper_ids": ["10.1/b"]},
                    ],
                    "total_papers": 2,
                },
                "theme_postprocess": {"attempted": False, "applied": False, "reason": "agent_postprocess_not_supplied"},
            }
            (materialized / "chart_data.json").write_text(json.dumps(chart_payload, ensure_ascii=False), encoding="utf-8")
            (materialized / "report_data.json").write_text(
                json.dumps({"metadata": {"query": "核物理治疗方法"}, "chart_data": chart_payload, "paper_list": []}, ensure_ascii=False),
                encoding="utf-8",
            )

            with mock.patch("vpnsci_sustech.report_bridge.subprocess.Popen") as popen_mock:
                job = start_report_from_session(
                    "search-full-theme",
                    config=cfg,
                    mode="full",
                    display_query="核物理治疗方法",
                    language="zh",
                )

            popen_mock.assert_not_called()
            self.assertEqual(job.status, "theme_postprocess_required")
            self.assertEqual(job.report_mode, "full")
            self.assertTrue(job.theme_postprocess_request_path.endswith("theme_postprocess_request.json"))
            request_payload = json.loads(Path(job.theme_postprocess_request_path).read_text(encoding="utf-8"))
            self.assertEqual(request_payload["report_mode"], "full")
            self.assertEqual(job.language, "zh")

    def test_apply_theme_postprocess_and_render_full_updates_materialized_without_recomputing_algorithm(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "paper-search-pro"
            output_dir = Path(tmp) / "reports"
            session_dir = output_dir / "search-full-apply"
            materialized = session_dir / "materialized"
            root.mkdir()
            materialized.mkdir(parents=True, exist_ok=True)
            cfg = Config(
                cache_dir=tmp,
                paper_search_pro_root=str(root),
                paper_search_pro_command="python -m vpnsci_sustech.paper_search_pro_adapter --seed {seed_json} --output-dir {output_dir}",
                paper_search_pro_output_dir=str(output_dir),
            )
            session = SearchSession(
                session_id="search-full-apply",
                query="核物理治疗方法",
                filters={},
                hits=[SearchHit(title="seed paper", doi="10.1/seed")],
                source_summary={"openalex": 1},
            )
            save_session(session, Path(tmp))
            chart_payload = {
                "raw_theme_treemap": {
                    "themes": [
                        {"name": "Targeted Radionuclide Therapy", "value": 2, "paper_ids": ["10.1/a"]},
                        {"name": "Nuclear Medicine Therapy", "value": 2, "paper_ids": ["10.1/b"]},
                    ],
                    "total_papers": 2,
                },
                "theme_treemap": {
                    "themes": [
                        {"name": "Targeted Radionuclide Therapy", "value": 2, "paper_ids": ["10.1/a"]},
                        {"name": "Nuclear Medicine Therapy", "value": 2, "paper_ids": ["10.1/b"]},
                    ],
                    "total_papers": 2,
                },
                "theme_postprocess": {"attempted": False, "applied": False, "reason": "agent_postprocess_not_supplied"},
            }
            (materialized / "metadata.json").write_text(
                json.dumps({"query": "核物理治疗方法", "display_query": "核物理治疗方法", "language": "zh"}, ensure_ascii=False),
                encoding="utf-8",
            )
            (materialized / "paper_list.json").write_text(
                json.dumps(
                    [
                        {"paper_id": "10.1/a", "title": "Targeted radionuclide therapy review"},
                        {"paper_id": "10.1/b", "title": "Nuclear medicine therapy overview"},
                    ],
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            (materialized / "prisma_log.json").write_text(json.dumps({}, ensure_ascii=False), encoding="utf-8")
            (materialized / "chart_data.json").write_text(json.dumps(chart_payload, ensure_ascii=False), encoding="utf-8")
            (materialized / "report_data.json").write_text(
                json.dumps({"metadata": {"query": "核物理治疗方法"}, "chart_data": chart_payload, "paper_list": []}, ensure_ascii=False),
                encoding="utf-8",
            )

            with mock.patch(
                "vpnsci_sustech.report_bridge.render_html_webartifacts",
                side_effect=lambda materialized_data_dir, output_path, user_query, language, tool_root=None: output_path.write_text("<html>ok</html>", encoding="utf-8"),
            ):
                result = apply_theme_postprocess_and_render(
                    "search-full-apply",
                    result_payload={
                        "groups": [
                            {"label": "Targeted Radionuclide and Nuclear Medicine Therapy", "theme_indices": [0, 1]},
                        ]
                    },
                    config=cfg,
                    mode="full",
                    display_query="核物理治疗方法",
                    language="zh",
                    open_report=False,
                )

            self.assertEqual(result.report_mode, "full")
            self.assertEqual(result.status, "completed")
            updated_chart = json.loads((materialized / "chart_data.json").read_text(encoding="utf-8"))
            self.assertEqual(updated_chart["theme_postprocess"]["reason"], "applied")
            self.assertEqual(updated_chart["theme_postprocess"]["model"], "host-agent")
            theme_names = [theme["name"] for theme in updated_chart["theme_treemap"]["themes"]]
            self.assertEqual(theme_names, ["Targeted Radionuclide and Nuclear Medicine Therapy"])
            self.assertEqual(
                updated_chart["raw_theme_treemap"]["themes"][0]["name"],
                "Targeted Radionuclide Therapy",
            )
            self.assertTrue((materialized / "theme_postprocess_result.json").exists())


if __name__ == "__main__":
    unittest.main()
