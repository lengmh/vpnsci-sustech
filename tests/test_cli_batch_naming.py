import tempfile
import unittest
from pathlib import Path
from unittest import mock

from typer.testing import CliRunner

from tests.temp_helpers import get_temp_parent
from vpnsci_sustech import cli
from vpnsci_sustech.models import Paper


class BatchCliNamingTests(unittest.TestCase):
    def test_batch_result_file_uses_title_author_default_for_json_output(self):
        runner = CliRunner()
        with tempfile.TemporaryDirectory(dir=get_temp_parent()) as tmp:
            input_file = Path(tmp) / "dois.txt"
            input_file.write_text("10.1234/example\n", encoding="utf-8")
            output_dir = Path(tmp) / "out"
            cfg = cli.Config(
                output_dir=str(output_dir), cache_dir=tmp,
                cookie_path=str(Path(tmp) / "cookies.json"),
                chrome_profile_dir=str(Path(tmp) / "chrome-profile"),
                carsi_cookie_dir=str(Path(tmp) / "carsi-cookies"),
            )
            paper = Paper(
                doi="10.1234/example",
                title="钙钛矿太阳能电池稳定性研究",
                authors=["张三"],
                full_text="full text",
            )

            with mock.patch.object(cli.Config, "load", return_value=cfg), \
                 mock.patch.object(cli.PaperFetcher, "fetch", return_value=paper), \
                 mock.patch.object(cli.PaperFetcher, "close", return_value=None):
                result = runner.invoke(cli.app, ["batch", str(input_file)])

            self.assertEqual(result.exit_code, 0, result.output)
            self.assertTrue((output_dir / "钙钛矿太阳能电池稳定性研究 - 张三.json").exists())
            self.assertFalse((output_dir / "10.1234_example.json").exists())

    def test_batch_result_file_uses_filename_policy_for_markdown_output(self):
        runner = CliRunner()
        with tempfile.TemporaryDirectory(dir=get_temp_parent()) as tmp:
            input_file = Path(tmp) / "dois.txt"
            input_file.write_text("10.1234/example\n", encoding="utf-8")
            output_dir = Path(tmp) / "out"
            cfg = cli.Config(
                output_dir=str(output_dir), cache_dir=tmp,
                cookie_path=str(Path(tmp) / "cookies.json"),
                chrome_profile_dir=str(Path(tmp) / "chrome-profile"),
                carsi_cookie_dir=str(Path(tmp) / "carsi-cookies"),
            )
            paper = Paper(
                doi="10.1234/example",
                title="钙钛矿太阳能电池稳定性研究",
                authors=["张三"],
                full_text="full text",
            )

            with mock.patch.object(cli.Config, "load", return_value=cfg), \
                 mock.patch.object(cli.PaperFetcher, "fetch", return_value=paper), \
                 mock.patch.object(cli.PaperFetcher, "close", return_value=None):
                result = runner.invoke(
                    cli.app,
                    [
                        "batch",
                        str(input_file),
                        "--format",
                        "markdown",
                        "--filename-policy",
                        "title_author",
                    ],
                )

            self.assertEqual(result.exit_code, 0, result.output)
            self.assertTrue((output_dir / "钙钛矿太阳能电池稳定性研究 - 张三.md").exists())
            self.assertFalse((output_dir / "10.1234_example.md").exists())


if __name__ == "__main__":
    unittest.main()
