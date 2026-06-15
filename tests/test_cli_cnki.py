import tempfile
import unittest
from pathlib import Path
from unittest import mock
import json

from typer.testing import CliRunner

from vpnsci_sustech import cli
from vpnsci_sustech.models import Paper
from vpnsci_sustech.sources import cnki
from vpnsci_sustech.sources.search_cache import load_session


class CnkiCliTests(unittest.TestCase):
    def test_cnki_download_materializes_local_file_without_network(self):
        runner = CliRunner()
        with tempfile.TemporaryDirectory(dir=Path("F:/AI playground/TempFiles")) as tmp:
            source = Path(tmp) / "source.cajx"
            source.write_bytes(b"cajx-content")
            config = cli.Config(
                output_dir=str(Path(tmp) / "out"),
                cache_dir=tmp,
                paper_filename_policy="title_author",
            )

            with mock.patch.object(cli.Config, "load", return_value=config):
                result = runner.invoke(
                    cli.app,
                    [
                        "cnki-download",
                        "--local-file",
                        str(source),
                        "--title",
                        "CNKI Source",
                        "--first-author",
                        "Li",
                        "--cnki-id",
                        "XYZ",
                    ],
                )

        self.assertEqual(result.exit_code, 0, result.output)
        self.assertIn("CNKI artifact saved", result.output)
        self.assertIn("text_extracted=false", result.output)
        self.assertIn("CNKI Source - Li.cajx", result.output)

    def test_cnki_download_filename_policy_overrides_config(self):
        runner = CliRunner()
        with tempfile.TemporaryDirectory(dir=Path("F:/AI playground/TempFiles")) as tmp:
            source = Path(tmp) / "source.caj"
            source.write_bytes(b"caj-content")
            config = cli.Config(
                output_dir=str(Path(tmp) / "out"),
                cache_dir=tmp,
                paper_filename_policy="identifier",
            )

            with mock.patch.object(cli.Config, "load", return_value=config):
                result = runner.invoke(
                    cli.app,
                    [
                        "cnki-download",
                        "--local-file",
                        str(source),
                        "--title",
                        "CNKI Source",
                        "--first-author",
                        "Li",
                        "--cnki-id",
                        "XYZ",
                        "--filename-policy",
                        "title_author",
                    ],
                )

        self.assertEqual(result.exit_code, 0, result.output)
        self.assertIn("CNKI Source - Li.caj", result.output)
        self.assertNotIn("XYZ.caj", result.output)

    def test_cnki_download_refuses_live_url_without_local_file(self):
        runner = CliRunner()

        result = runner.invoke(
            cli.app,
            [
                "cnki-download",
                "--detail-url",
                "https://kns.cnki.net/kcms2/article/abstract?filename=ABC123",
                "--title",
                "CNKI Paper",
            ],
        )

        self.assertNotEqual(result.exit_code, 0)
        self.assertIn("requires --live", result.output)

    def test_cnki_download_live_requires_confirmation(self):
        runner = CliRunner()

        result = runner.invoke(
            cli.app,
            [
                "cnki-download",
                "--detail-url",
                "https://kns.cnki.net/kcms2/article/abstract?filename=ABC123",
                "--live",
            ],
        )

        self.assertEqual(result.exit_code, 1)
        self.assertIn("confirmation_required", result.output)

    def test_cnki_download_live_warns_that_manual_captcha_may_be_required(self):
        runner = CliRunner()
        with tempfile.TemporaryDirectory(dir=Path("F:/AI playground/TempFiles")) as tmp:
            config = cli.Config(output_dir=str(Path(tmp) / "out"), cache_dir=tmp)
            fake_artifact = mock.Mock(
                path="out/paper.pdf",
                format="pdf",
                kind="full_text_pdf",
                text_extracted=True,
                note="",
            )

            with mock.patch.object(cli.Config, "load", return_value=config), \
                 mock.patch("vpnsci_sustech.cli.cnki.CNKIClient.download_cnki_artifact", return_value=fake_artifact):
                result = runner.invoke(
                    cli.app,
                    [
                        "cnki-download",
                        "--detail-url",
                        "https://kns.cnki.net/kcms2/article/abstract?filename=ABC123",
                        "--live",
                        "--confirm-live-access",
                    ],
                )

        self.assertEqual(result.exit_code, 0, result.output)
        self.assertIn("manual captcha", result.output.lower())
        self.assertIn("visible browser", result.output.lower())

    def test_cnki_batch_download_uses_throttle_and_resume_state(self):
        runner = CliRunner()
        with tempfile.TemporaryDirectory(dir=Path("F:/AI playground/TempFiles")) as tmp:
            input_file = Path(tmp) / "cnki-batch.jsonl"
            input_file.write_text(
                "\n".join(
                    [
                        '{"detail_url":"https://kns.cnki.net/kcms2/article/abstract?filename=ABC1","title":"A","first_author":"Li","cnki_id":"ABC1"}',
                        '{"detail_url":"https://kns.cnki.net/kcms2/article/abstract?filename=ABC2","title":"B","first_author":"Wang","cnki_id":"ABC2"}',
                    ]
                ),
                encoding="utf-8",
            )
            state_file = Path(tmp) / "batch-state.json"
            config = cli.Config(output_dir=str(Path(tmp) / "out"), cache_dir=tmp)
            fake_result = cnki.CNKIBatchResult(
                status="completed",
                state_path=state_file,
                sidecar_path=Path(tmp) / "download-workflows" / "download-abc.json",
                entries=[],
                succeeded=2,
                failed=0,
                pending=0,
                stopped_reason="",
            )

            with mock.patch.object(cli.Config, "load", return_value=config), \
                 mock.patch("vpnsci_sustech.cli.cnki.CNKIClient.download_cnki_batch", return_value=fake_result) as batch_mock:
                result = runner.invoke(
                    cli.app,
                    [
                        "cnki-batch-download",
                        str(input_file),
                        "--live",
                        "--confirm-live-access",
                        "--min-interval",
                        "1",
                        "--cooldown-every",
                        "2",
                        "--cooldown-seconds",
                        "5",
                        "--max-consecutive-failures",
                        "1",
                        "--state-file",
                        str(state_file),
                        "--resume",
                    ],
                )

        self.assertEqual(result.exit_code, 0, result.output)
        self.assertIn("CNKI batch download", result.output)
        self.assertIn("completed", result.output)
        self.assertIn("download-abc.json", result.output)
        called_items = batch_mock.call_args.args[0]
        self.assertEqual(len(called_items), 2)
        self.assertEqual(called_items[0].cnki_id, "ABC1")
        self.assertTrue(batch_mock.call_args.kwargs["resume"])
        self.assertEqual(batch_mock.call_args.kwargs["min_interval_seconds"], 1.0)
        self.assertEqual(batch_mock.call_args.kwargs["cooldown_every"], 2)

    def test_report_recover_from_sidecar_restores_session_and_starts_report(self):
        runner = CliRunner()
        with tempfile.TemporaryDirectory(dir=Path("F:/AI playground/TempFiles")) as tmp:
            cache_dir = Path(tmp)
            sidecar_dir = cache_dir / "download-workflows"
            sidecar_dir.mkdir(parents=True, exist_ok=True)
            sidecar_path = sidecar_dir / "download-abc.json"
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
                                "authors": ["张三"],
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
            config = cli.Config(cache_dir=tmp)
            fake_job = mock.Mock(
                status="started",
                seed_session_id="search-restored",
                report_path="F:/AI playground/TempFiles/report.html",
                deduped_paper_count=1,
            )

            with mock.patch.object(cli.Config, "load", return_value=config), \
                 mock.patch("vpnsci_sustech.cli.report_bridge.start_report_from_session", return_value=fake_job):
                result = runner.invoke(cli.app, ["report-recover", "--sidecar", str(sidecar_path), "--mode", "seed_preview"])

            self.assertEqual(result.exit_code, 0, result.output)
            self.assertIn("Restored Session", result.output)
            self.assertIn("search-restored", result.output)

    def test_report_recover_can_use_explicit_legacy_report_json(self):
        runner = CliRunner()
        with tempfile.TemporaryDirectory(dir=Path("F:/AI playground/TempFiles")) as tmp:
            materialized = Path(tmp) / "materialized"
            materialized.mkdir(parents=True, exist_ok=True)
            report_json = materialized / "report_data.json"
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
            config = cli.Config(cache_dir=tmp)
            fake_job = mock.Mock(
                status="started",
                seed_session_id="search-restored",
                report_path="F:/AI playground/TempFiles/report.html",
                deduped_paper_count=1,
            )

            with mock.patch.object(cli.Config, "load", return_value=config), \
                 mock.patch("vpnsci_sustech.cli.report_bridge.start_report_from_session", return_value=fake_job):
                result = runner.invoke(
                    cli.app,
                    [
                        "report-recover",
                        "--report-json",
                        str(report_json),
                        "--prefer",
                        "B",
                        "--mode",
                        "seed_preview",
                    ],
                )

            self.assertEqual(result.exit_code, 0, result.output)
            self.assertIn("Recovery Kind: B", result.output)
            self.assertIn("恢复后的展示标题", result.output)

    def test_report_seed_classified_status_tells_user_rcs_classification_is_required(self):
        runner = CliRunner()
        with tempfile.TemporaryDirectory(dir=Path("F:/AI playground/TempFiles")) as tmp:
            config = cli.Config(cache_dir=tmp)
            fake_job = mock.Mock(
                status="rcs_classification_required",
                seed_session_id="search-seed-classified",
                report_path="",
                deduped_paper_count=1,
                materialized_dir=str(Path(tmp) / "materialized"),
                rcs_classification_request_path=str(Path(tmp) / "materialized" / "rcs_classification_request.json"),
                rcs_classification_result_path=str(Path(tmp) / "materialized" / "rcs_classification_result.json"),
            )

            with mock.patch.object(cli.Config, "load", return_value=config), \
                 mock.patch("vpnsci_sustech.cli.report_bridge.start_report_from_session", return_value=fake_job):
                result = runner.invoke(cli.app, ["report", "search-seed-classified", "--mode", "seed_classified"])

            self.assertEqual(result.exit_code, 0, result.output)
            self.assertIn("RCS", result.output)
            self.assertIn("rcs_classification_request.json", result.output)
            self.assertIn("rcs_classification_result.json", result.output)
            self.assertNotIn("专业调研报告已生成", result.output)

    def test_search_backend_cnki_saves_gated_session_without_network(self):
        runner = CliRunner()
        with tempfile.TemporaryDirectory(dir=Path("F:/AI playground/TempFiles")) as tmp:
            config = cli.Config(cache_dir=tmp)
            with mock.patch.object(cli.Config, "load", return_value=config):
                result = runner.invoke(cli.app, ["search", "钙钛矿", "--backend", "cnki"])

            self.assertEqual(result.exit_code, 0, result.output)
            self.assertIn("Search Session:", result.output)
            self.assertIn("live_access_not_enabled", result.output)
            session_id = ""
            for line in result.output.splitlines():
                if "Search Session:" in line:
                    session_id = line.split("Search Session:", 1)[1].strip()
                    break
            self.assertTrue(session_id)
            session = load_session(session_id, Path(tmp))
            self.assertEqual(session.source_summary, {"cnki": 0})
            self.assertEqual(session.errors[0].code, "live_access_not_enabled")

    def test_fetch_hit_can_continue_from_cnki_session_hit(self):
        runner = CliRunner()
        with tempfile.TemporaryDirectory(dir=Path("F:/AI playground/TempFiles")) as tmp:
            config = cli.Config(cache_dir=tmp)
            session = load_session(
                cnki.search_cnki_from_html(
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
                ).session_id,
                Path(tmp),
            )
            fake_paper = Paper(title="题名一", source="cnki")
            with mock.patch.object(cli.Config, "load", return_value=config), \
                 mock.patch("vpnsci_sustech.cli.PaperFetcher.fetch_from_search_hit", return_value=fake_paper):
                result = runner.invoke(cli.app, ["fetch-hit", session.session_id, "cnki:ABC123"])

            self.assertEqual(result.exit_code, 0, result.output)
            self.assertIn("题名一", result.output)

    def test_cnki_smoke_defaults_to_dry_run(self):
        runner = CliRunner()

        result = runner.invoke(
            cli.app,
            [
                "cnki-smoke",
                "--query",
                "钙钛矿",
                "--limit",
                "99",
            ],
        )

        self.assertEqual(result.exit_code, 0, result.output)
        self.assertIn("CNKI visible-browser smoke", result.output)
        self.assertIn("Dry Run: true", result.output)
        self.assertIn("Limit: 3", result.output)

    def test_cnki_smoke_live_requires_confirmation(self):
        runner = CliRunner()

        result = runner.invoke(
            cli.app,
            [
                "cnki-smoke",
                "--detail-url",
                "https://kns.cnki.net/kcms2/article/abstract?filename=ABC123",
                "--live",
            ],
        )

        self.assertEqual(result.exit_code, 1)
        self.assertIn("confirmation_required", result.output)

    def test_cnki_detail_parses_html_file_without_network(self):
        runner = CliRunner()
        with tempfile.TemporaryDirectory(dir=Path("F:/AI playground/TempFiles")) as tmp:
            html_file = Path(tmp) / "detail.html"
            html_file.write_text(
                """
                <html><body>
                  <h1 class="title">CNKI Detail</h1>
                  <div class="author">Zhang; Li</div>
                  <div class="sourinfo">Journal 2024</div>
                  <div id="ChDivSummary">Abstract text</div>
                </body></html>
                """,
                encoding="utf-8",
            )

            result = runner.invoke(
                cli.app,
                [
                    "cnki-detail",
                    "--url-or-id",
                    "https://kns.cnki.net/kcms2/article/abstract?filename=ABC123",
                    "--html-file",
                    str(html_file),
                ],
            )

        self.assertEqual(result.exit_code, 0, result.output)
        self.assertIn("CNKI Detail", result.output)
        self.assertIn("Abstract text", result.output)

    def test_cnki_detail_without_html_is_gated(self):
        runner = CliRunner()

        result = runner.invoke(cli.app, ["cnki-detail", "--url-or-id", "ABC123"])

        self.assertEqual(result.exit_code, 1)
        self.assertIn("live_access_not_enabled", result.output)

    def test_cnki_search_html_parses_file_without_network(self):
        runner = CliRunner()
        with tempfile.TemporaryDirectory(dir=Path("F:/AI playground/TempFiles")) as tmp:
            html_file = Path(tmp) / "search.html"
            html_file.write_text(
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
                encoding="utf-8",
            )
            config = cli.Config(cache_dir=tmp)

            with mock.patch.object(cli.Config, "load", return_value=config):
                result = runner.invoke(
                    cli.app,
                    [
                        "cnki-search-html",
                        "--query",
                        "钙钛矿",
                        "--html-file",
                        str(html_file),
                        "--limit",
                        "1",
                    ],
                )

                session_id = ""
                for line in result.output.splitlines():
                    if "Search Session:" in line:
                        session_id = line.split("Search Session:", 1)[1].strip()
                        break
                self.assertTrue(session_id)
                data = json.loads((Path(tmp) / "search" / "sessions" / f"{session_id}.json").read_text(encoding="utf-8"))

        self.assertEqual(result.exit_code, 0, result.output)
        self.assertIn("CNKI search HTML parsed", result.output)
        self.assertIn("Search Session:", result.output)
        self.assertIn("题名一", result.output)
        self.assertEqual(data["origin"]["kind"], "html_import")


if __name__ == "__main__":
    unittest.main()
