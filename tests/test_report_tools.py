import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from vpnsci_sustech.config import Config
from vpnsci_sustech import report_tools


def _write_runtime(root: Path) -> None:
    for relative in report_tools.REQUIRED_TOOL_SENTINELS:
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(relative, encoding="utf-8")


class ReportToolsTests(unittest.TestCase):
    def test_default_report_command_uses_vpnsci_adapter(self):
        command = report_tools.default_report_command()
        self.assertIn("vpnsci_sustech.light_report_bridge", command)
        self.assertIn("{seed_json}", command)
        self.assertIn("{output_dir}", command)
        self.assertEqual(command, report_tools.default_seed_preview_command())

    def test_resolve_bundled_tool_root_prefers_packaged_snapshot(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            packaged = tmp_path / "package" / "_bundled" / "paper-search-pro"
            repo = tmp_path / "repo" / "tools" / "paper-search-pro"
            _write_runtime(packaged)
            _write_runtime(repo)

            with mock.patch.object(report_tools, "packaged_tool_root", return_value=packaged), \
                 mock.patch.object(report_tools, "repo_checkout_tool_root", return_value=repo):
                resolved = report_tools.resolve_bundled_tool_root()

            self.assertEqual(resolved.root, packaged)
            self.assertEqual(resolved.source, report_tools.PACKAGED_BUNDLED)

    def test_resolve_bundled_tool_root_uses_repo_fallback_when_packaged_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            packaged = tmp_path / "package" / "_bundled" / "paper-search-pro"
            repo = tmp_path / "repo" / "tools" / "paper-search-pro"
            _write_runtime(repo)

            with mock.patch.object(report_tools, "packaged_tool_root", return_value=packaged), \
                 mock.patch.object(report_tools, "repo_checkout_tool_root", return_value=repo):
                resolved = report_tools.resolve_bundled_tool_root()

            self.assertEqual(resolved.root, repo)
            self.assertEqual(resolved.source, report_tools.REPO_TOOLS_FALLBACK)


    def test_resolve_bundled_tool_root_does_not_use_cwd_as_fallback(self):
        original_cwd = Path.cwd()
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            cwd_runtime = tmp_path / "cwd-runtime"
            _write_runtime(cwd_runtime)
            fake_module = tmp_path / "site-packages" / "vpnsci_sustech" / "report_tools.py"
            packaged = tmp_path / "missing-package" / "_bundled" / "paper-search-pro"

            try:
                os.chdir(cwd_runtime)
                with mock.patch.object(report_tools, "__file__", str(fake_module)), \
                     mock.patch.object(report_tools, "packaged_tool_root", return_value=packaged):
                    with self.assertRaises(FileNotFoundError):
                        report_tools.resolve_bundled_tool_root()
            finally:
                os.chdir(original_cwd)

    def test_install_report_tool_copies_bundled_snapshot_and_writes_credentials(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            bundled = tmp_path / "bundled" / "paper-search-pro"
            _write_runtime(bundled)
            base = tmp_path / ".vpnsci-sustech"
            home = tmp_path / "home"
            cfg = Config(
                cache_dir=str(base / "cache"),
                email="user@example.com",
                openalex_api_key="openalex-key",
                semantic_scholar_api_key="s2-key",
            )

            with mock.patch.object(report_tools, "resolve_bundled_tool_root", return_value=report_tools.ReportToolRuntime(bundled, report_tools.PACKAGED_BUNDLED)), \
                 mock.patch.object(report_tools, "DEFAULT_BASE_DIR", base), \
                 mock.patch.object(report_tools.Path, "home", return_value=home):
                result = report_tools.install_report_tool(cfg, force=True)

            self.assertTrue((base / "tools" / "paper-search-pro" / "SKILL.md").exists())
            self.assertTrue((home / ".paper-search-pro" / "config.yaml").exists())
            self.assertEqual(result.resource_source, report_tools.PACKAGED_BUNDLED)
            self.assertTrue(result.openalex_configured)
            self.assertTrue(result.semantic_scholar_configured)

    def test_ensure_report_tool_configured_can_avoid_persisting_supplied_config(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            bundled = tmp_path / "bundled" / "paper-search-pro"
            _write_runtime(bundled)
            base = tmp_path / ".vpnsci-sustech"
            home = tmp_path / "home"
            cfg = Config(cache_dir=str(base / "cache"))

            with mock.patch.object(report_tools, "resolve_bundled_tool_root", return_value=report_tools.ReportToolRuntime(bundled, report_tools.PACKAGED_BUNDLED)), \
                 mock.patch.object(report_tools, "DEFAULT_BASE_DIR", base), \
                 mock.patch.object(report_tools.Path, "home", return_value=home):
                configured = report_tools.ensure_report_tool_configured(cfg, force=True, persist=False)

            self.assertEqual(configured.paper_search_pro_root, str(base / "tools" / "paper-search-pro"))
            self.assertEqual(configured.paper_search_pro_command, "")
            self.assertFalse((base / "config.json").exists())


if __name__ == "__main__":
    unittest.main()
