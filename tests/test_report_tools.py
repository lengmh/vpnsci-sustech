import tempfile
import unittest
from pathlib import Path
from unittest import mock

from vpnsci_sustech.config import Config
from vpnsci_sustech import report_tools


class ReportToolsTests(unittest.TestCase):
    def test_default_report_command_uses_vpnsci_adapter(self):
        command = report_tools.default_report_command()
        self.assertIn("vpnsci_sustech.paper_search_pro_adapter", command)
        self.assertIn("{seed_json}", command)
        self.assertIn("{output_dir}", command)
        self.assertEqual(command, report_tools.default_seed_preview_command())

    def test_install_report_tool_copies_bundled_snapshot_and_writes_credentials(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            bundled = tmp_path / "bundled" / "paper-search-pro"
            bundled.mkdir(parents=True)
            (bundled / "SKILL.md").write_text("skill", encoding="utf-8")
            base = tmp_path / ".vpnsci-sustech"
            home = tmp_path / "home"
            cfg = Config(
                cache_dir=str(base / "cache"),
                email="user@example.com",
                openalex_api_key="openalex-key",
                semantic_scholar_api_key="s2-key",
            )

            with mock.patch.object(report_tools, "bundled_tool_root", return_value=bundled), \
                 mock.patch.object(report_tools, "DEFAULT_BASE_DIR", base), \
                 mock.patch.object(report_tools.Path, "home", return_value=home):
                result = report_tools.install_report_tool(cfg, force=True)

            self.assertTrue((base / "tools" / "paper-search-pro" / "SKILL.md").exists())
            self.assertTrue((home / ".paper-search-pro" / "config.yaml").exists())
            self.assertTrue(result.openalex_configured)
            self.assertTrue(result.semantic_scholar_configured)

    def test_ensure_report_tool_configured_can_avoid_persisting_supplied_config(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            bundled = tmp_path / "bundled" / "paper-search-pro"
            bundled.mkdir(parents=True)
            (bundled / "SKILL.md").write_text("skill", encoding="utf-8")
            base = tmp_path / ".vpnsci-sustech"
            home = tmp_path / "home"
            cfg = Config(cache_dir=str(base / "cache"))

            with mock.patch.object(report_tools, "bundled_tool_root", return_value=bundled), \
                 mock.patch.object(report_tools, "DEFAULT_BASE_DIR", base), \
                 mock.patch.object(report_tools.Path, "home", return_value=home):
                configured = report_tools.ensure_report_tool_configured(cfg, force=True, persist=False)

            self.assertEqual(configured.paper_search_pro_root, str(base / "tools" / "paper-search-pro"))
            self.assertFalse((base / "config.json").exists())


if __name__ == "__main__":
    unittest.main()
