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


if __name__ == "__main__":
    unittest.main()
