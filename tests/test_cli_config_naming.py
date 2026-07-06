import tempfile
import unittest
from pathlib import Path
from unittest import mock

from typer.testing import CliRunner

from vpnsci_sustech import cli


class CliConfigNamingTests(unittest.TestCase):
    def test_config_cmd_sets_filename_length_and_collision(self):
        runner = CliRunner()
        with tempfile.TemporaryDirectory(dir=Path("F:/AI playground/TempFiles")) as tmp:
            cfg = cli.Config(cache_dir=tmp)

            with mock.patch.object(cli.Config, "load", return_value=cfg), \
                 mock.patch.object(cli.Config, "save") as save_mock:
                result = runner.invoke(
                    cli.app,
                    [
                        "config-cmd",
                        "--paper-filename-max-length",
                        "96",
                        "--paper-filename-collision",
                        "increment",
                    ],
                )

        self.assertEqual(result.exit_code, 0, result.output)
        self.assertEqual(cfg.paper_filename_max_length, 96)
        self.assertEqual(cfg.paper_filename_collision, "increment")
        save_mock.assert_called_once()

    def test_config_cmd_rejects_invalid_filename_collision(self):
        runner = CliRunner()
        with tempfile.TemporaryDirectory(dir=Path("F:/AI playground/TempFiles")) as tmp:
            cfg = cli.Config(cache_dir=tmp)

            with mock.patch.object(cli.Config, "load", return_value=cfg), \
                 mock.patch.object(cli.Config, "save") as save_mock:
                result = runner.invoke(
                    cli.app,
                    [
                        "config-cmd",
                        "--paper-filename-collision",
                        "overwrite",
                    ],
                )

        self.assertNotEqual(result.exit_code, 0)
        self.assertIn("hash or increment", result.output)
        self.assertEqual(cfg.paper_filename_collision, "hash")
        save_mock.assert_not_called()

    def test_config_cmd_rejects_invalid_filename_policy(self):
        runner = CliRunner()
        with tempfile.TemporaryDirectory(dir=Path("F:/AI playground/TempFiles")) as tmp:
            cfg = cli.Config(cache_dir=tmp)

            with mock.patch.object(cli.Config, "load", return_value=cfg), \
                 mock.patch.object(cli.Config, "save") as save_mock:
                result = runner.invoke(
                    cli.app,
                    [
                        "config-cmd",
                        "--paper-filename-policy",
                        "title_only",
                    ],
                )

        self.assertNotEqual(result.exit_code, 0)
        self.assertIn("identifier", result.output)
        self.assertIn("title_author", result.output)
        self.assertIn("title_year_author", result.output)
        self.assertIn("custom", result.output)
        self.assertEqual(cfg.paper_filename_policy, "title_author")
        save_mock.assert_not_called()

    def test_config_cmd_rejects_non_positive_filename_max_length(self):
        runner = CliRunner()
        with tempfile.TemporaryDirectory(dir=Path("F:/AI playground/TempFiles")) as tmp:
            cfg = cli.Config(cache_dir=tmp)

            with mock.patch.object(cli.Config, "load", return_value=cfg), \
                 mock.patch.object(cli.Config, "save") as save_mock:
                result = runner.invoke(
                    cli.app,
                    [
                        "config-cmd",
                        "--paper-filename-max-length",
                        "-1",
                    ],
                )

        self.assertNotEqual(result.exit_code, 0)
        self.assertIn("positive integer", result.output)
        self.assertEqual(cfg.paper_filename_max_length, 180)
        save_mock.assert_not_called()

    def _report_tool_result(self, tmp: str):
        return cli.report_tools.ReportToolInstallResult(
            bundled_root=str(Path(tmp) / "bundled"),
            local_root=str(Path(tmp) / "local-runtime"),
            output_dir=str(Path(tmp) / "reports"),
            command="runtime default should not be printed as persisted command",
            installed=True,
            credentials_path=str(Path(tmp) / "config.yaml"),
            openalex_configured=False,
            semantic_scholar_configured=False,
            resource_source=cli.report_tools.PACKAGED_BUNDLED,
        )

    def test_report_tools_install_uses_configure_helper_and_prints_runtime_default(self):
        runner = CliRunner()
        with tempfile.TemporaryDirectory(dir=Path("F:/AI playground/TempFiles")) as tmp:
            cfg = cli.Config(cache_dir=tmp)
            result_obj = self._report_tool_result(tmp)

            with mock.patch.object(cli.Config, "load", return_value=cfg), \
                 mock.patch.object(cli.report_tools, "configure_report_tool", return_value=(cfg, result_obj)) as configure_mock:
                result = runner.invoke(cli.app, ["report-tools", "install", "--force"])

        self.assertEqual(result.exit_code, 0, result.output)
        configure_mock.assert_called_once_with(cfg, force=True)
        self.assertIn("Resource source:", result.output)
        self.assertIn(cli.report_tools.PACKAGED_BUNDLED, result.output)
        self.assertIn("Command:", result.output)
        self.assertIn("(runtime default)", result.output)

    def test_config_cmd_install_report_tools_uses_same_configure_helper(self):
        runner = CliRunner()
        with tempfile.TemporaryDirectory(dir=Path("F:/AI playground/TempFiles")) as tmp:
            cfg = cli.Config(cache_dir=tmp)
            result_obj = self._report_tool_result(tmp)

            with mock.patch.object(cli.Config, "load", return_value=cfg), \
                 mock.patch.object(cli.Config, "save") as save_mock, \
                 mock.patch.object(cli.report_tools, "configure_report_tool", return_value=(cfg, result_obj)) as configure_mock:
                result = runner.invoke(cli.app, ["config-cmd", "--install-report-tools"])

        self.assertEqual(result.exit_code, 0, result.output)
        configure_mock.assert_called_once_with(cfg, force=False)
        save_mock.assert_not_called()
        self.assertIn("paper-search-pro report tool installed and configured", result.output)
        self.assertIn("Resource source:", result.output)
        self.assertIn(cli.report_tools.PACKAGED_BUNDLED, result.output)

if __name__ == "__main__":
    unittest.main()
